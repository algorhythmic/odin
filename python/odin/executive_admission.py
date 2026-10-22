"""Local Bash admission paths for the delegated executive's hook (ODIN-ADR-034).

Two paths decide without calling the service, so a stopped service can still be
diagnosed: an entirely read-only command from a fixed allowlist, and an
operator-registered script whose current SHA-256 matches its registration.
Both inspect the literal command text before the shell runs it. They are a
workflow boundary, not OS isolation: an allowed program still runs with the
operator's authority, and a registered script does whatever its bytes do.
Anything that matches neither path goes to the permit path or is refused.
"""
import hashlib
import os
import re
import stat
from pathlib import Path

from .contracts import Contracts, canonical, strict_loads
from .store import digest, now

SCRIPTS_FILE = "registered-scripts.json"
AUDIT_FILE = "intervention-audit.jsonl"
MAX_SCRIPTS = 64
MAX_SCRIPT_BYTES = 16 * 1024 * 1024
LAUNCHER = "run"

# Refused anywhere in a read-only command, quoted or not.
READ_ONLY_FORBIDDEN = (";", "&", "`", "$(", "<", ">", "\n")
# Refused anywhere in a registered-script command; redirections are parsed.
SCRIPT_FORBIDDEN = (";", "`", "$(", "|", "\n")
# Unquoted characters that expand, group or comment in the shell.
UNQUOTED_REFUSED = set("$()*?[]{}#!`;")

GIT_READ = {"status", "log", "diff", "show", "rev-parse", "rev-list", "merge-base",
            "ls-files", "cat-file", "blame", "describe", "cherry", "shortlog",
            "grep", "for-each-ref"}
GIT_DENIED_LONG = ("output", "output-directory", "ext-diff", "open-files-in-pager")
GIT_REFLOG_WRITES = {"expire", "delete", "drop"}
BRANCH_FLAGS = {"-a", "--all", "-r", "--remotes", "-l", "--list", "-v", "-vv",
                "--verbose", "--show-current", "--no-color", "--no-column",
                "-i", "--ignore-case", "--omit-empty"}
BRANCH_VALUED = {"contains", "no-contains", "merged", "no-merged", "points-at",
                 "sort", "format", "color", "column", "abbrev"}
FIND_DENIED = {"-exec", "-execdir", "-delete", "-ok", "-okdir", "-fls"}
SYSTEMCTL_READ = {"status", "show", "is-active", "is-enabled", "list-units", "cat"}
JOURNALCTL_DENIED_LONG = ("follow", "vacuum-size", "vacuum-files", "vacuum-time",
                          "rotate", "flush", "sync", "relinquish-var",
                          "smart-relinquish-var", "setup-keys", "update-catalog",
                          "cursor-file")
LAUNCHER_STATUS = {"status", "executive-status", "development-status",
                   "usage-status", "context-status"}
LAUNCHER_FLAGS = {"--project", "--loop", "--stage", "--native-session"}
LAUNCHER_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
BASH_KEYS = {"command", "description", "timeout", "run_in_background", "dangerouslyDisableSandbox"}
# Programs that run other code given as arguments or input: shells, language
# interpreters, package runners and command wrappers. A version suffix such as
# python3.14 or perl5.40 matches the base name.
INTERPRETER_NAME = re.compile(
    r"(?:sh|bash|rbash|zsh|fish|dash|ash|ksh|mksh|oksh|csh|tcsh|nu|elvish|xonsh|busybox|toybox"
    r"|python|pypy|ipython|node|nodejs|perl|ruby|irb|php|lua|luajit|tclsh|wish|expect"
    r"|awk|gawk|mawk|nawk|rscript|julia|guile|racket|java|jshell|pwsh"
    r"|env|uv|uvx|pipx|npx|npm|pnpm|pnpx|yarn|deno|bun|bunx|mise|asdf|pyenv|rbenv|nodenv"
    r"|xargs|nice|nohup|timeout|stdbuf|setsid|sudo|doas|su|pkexec|runuser|chroot|flock"
    r"|strace|ltrace|unshare|nsenter|systemd-run|watch)"
    r"(?:[0-9][0-9.]*[a-z]?)?")
INTERPRETER_DIRS = ("/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin")


class Refused(ValueError):
    pass


def _tokens(command):
    """Split shell text into words and unquoted operators, refusing expansions.

    Words are returned as strings after quote removal; operators as tuples
    ``("op", text, fd)``. A digit-only unquoted word directly before ``<`` or
    ``>`` becomes the operator's file descriptor, as in the shell.
    """
    if any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in command):
        raise Refused("control_character")
    tokens, word, quoted, active = [], [], False, False
    i = 0

    def finish():
        nonlocal word, quoted, active
        if active:
            tokens.append(("word", "".join(word), quoted))
        word, quoted, active = [], False, False

    while i < len(command):
        char = command[i]
        if char in " \t":
            finish()
        elif char == "'":
            end = command.find("'", i + 1)
            if end < 0:
                raise Refused("unterminated_quote")
            word.append(command[i + 1:end]); quoted = active = True
            i = end
        elif char == '"':
            i += 1
            while i < len(command) and command[i] != '"':
                if command[i] in "$`":
                    raise Refused("expansion")
                if command[i] == "\\" and i + 1 < len(command) and command[i + 1] in '"\\':
                    i += 1
                word.append(command[i]); i += 1
            if i >= len(command):
                raise Refused("unterminated_quote")
            quoted = active = True
        elif char == "\\":
            if i + 1 >= len(command):
                raise Refused("trailing_escape")
            i += 1
            word.append(command[i]); quoted = active = True
        elif char in "|&<>":
            fd = None
            if (active and not quoted and word and "".join(word).isdigit() and char in "<>"):
                fd = "".join(word)
                word, active = [], False
            finish()
            text = char
            if char == ">" and command[i + 1:i + 2] in (">", "&"):
                text += command[i + 1]; i += 1
            elif char in "|&" and command[i + 1:i + 2] == char:
                text += char; i += 1
            tokens.append(("op", text, fd))
        elif char in UNQUOTED_REFUSED:
            raise Refused("unquoted_shell_syntax")
        else:
            word.append(char); active = True
        i += 1
    finish()
    return tokens


def _long(arg):
    return arg[2:].split("=", 1)[0] if arg.startswith("--") else None


def _abbreviates(arg, names):
    """True when a GNU-style long option equals or abbreviates a denied name."""
    name = _long(arg)
    return bool(name) and any(full.startswith(name) for full in names)


def _short(arg, letters):
    """True when a short-option cluster such as ``-nf`` contains a denied letter."""
    return (arg.startswith("-") and not arg.startswith("--") and
            any(letter in arg[1:] for letter in letters))


def _git(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            i += 2
        elif args[i] in ("--no-pager", "-P"):
            i += 1
        else:
            return False
    if i >= len(args):
        return False
    sub, rest = args[i], args[i + 1:]
    if any(_abbreviates(a, GIT_DENIED_LONG) for a in rest):
        return False
    if sub == "grep" and any(_short(a, "O") for a in rest):
        return False
    if sub in GIT_READ:
        return True
    if sub in ("worktree", "stash"):
        return rest[:1] == ["list"]
    if sub == "remote":
        return rest in ([], ["-v"], ["--verbose"])
    if sub == "reflog":
        return not any(a in GIT_REFLOG_WRITES for a in rest)
    if sub == "branch":
        listing = any(a in ("-l", "--list") for a in rest)
        for arg in rest:
            if arg in BRANCH_FLAGS:
                continue
            if "=" in arg and _long(arg) in BRANCH_VALUED:
                continue
            if listing and not arg.startswith("-"):
                continue
            return False
        return True
    return False


def _uniq(args):
    operands = 0
    for arg in args:
        if re.fullmatch(r"-[cduizD]+|-[fsw]\d+", arg):
            continue
        if arg == "-" or not arg.startswith("-"):
            operands += 1
            continue
        return False
    # A second operand is uniq's output file.
    return operands <= 1


def _systemctl(args):
    if args[:1] != ["--user"] or len(args) < 2 or args[1] not in SYSTEMCTL_READ:
        return False
    # -H/-M reach other hosts or machines through other programs.
    return not any(_abbreviates(a, ("host", "machine")) or _short(a, "HM") for a in args[2:])


def _journalctl(args):
    if args[:1] != ["--user"]:
        return False
    return not any(_abbreviates(a, JOURNALCTL_DENIED_LONG) or _short(a, "f") for a in args[1:])


def _launcher(args):
    if not args or args[0] not in LAUNCHER_STATUS:
        return False
    rest = args[1:]
    while rest:
        flag, _, value = rest[0].partition("=")
        if flag not in LAUNCHER_FLAGS:
            return False
        if value:
            rest = rest[1:]
        elif len(rest) > 1:
            value, rest = rest[1], rest[2:]
        else:
            return False
        if not LAUNCHER_VALUE.fullmatch(value):
            return False
    return True


RULES = {
    "git": _git,
    "find": lambda a: not any(x in FIND_DENIED or x.startswith("-fprint") for x in a),
    "grep": lambda a: not any(_abbreviates(x, ("pre",)) for x in a),
    "rg": lambda a: not any(_abbreviates(x, ("pre", "pre-glob", "hostname-bin", "search-zip")) or
                            _short(x, "z") for x in a),
    "sort": lambda a: not any(_abbreviates(x, ("output", "compress-program")) or _short(x, "o") for x in a),
    "tail": lambda a: not any(_abbreviates(x, ("follow", "retry")) or _short(x, "fF") for x in a),
    "date": lambda a: not any(_abbreviates(x, ("set",)) or _short(x, "s") for x in a),
    "uniq": _uniq,
    "systemctl": _systemctl,
    "journalctl": _journalctl,
}
for _name in ("ls", "cat", "head", "wc", "stat", "du", "df", "jq", "cut", "ps",
              "pgrep", "uptime", "id", "whoami", "which", "pwd"):
    RULES[_name] = lambda a: True


def _safe_file(value, *, owned=False):
    """Absolute, normalized regular file with no symlink in any component."""
    if (not isinstance(value, str) or not os.path.isabs(value) or "\x00" in value or
            os.path.normpath(value) != value or value.startswith("//")):
        return False
    path = Path(value)
    try:
        if any(part.is_symlink() for part in (path, *path.parents)):
            return False
        info = path.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode):
        return False
    return not owned or (info.st_uid == os.getuid() and not info.st_mode & 0o022)


def _bash_inputs(inputs, *, background):
    if not isinstance(inputs, dict) or not set(inputs) <= BASH_KEYS:
        return None
    command = inputs.get("command")
    if not isinstance(command, str) or not command.strip() or len(command) > 16384:
        return None
    # Identity checks: 0 and 1 compare equal to False and True.
    if inputs.get("dangerouslyDisableSandbox", False) is not False:
        return None
    flag = inputs.get("run_in_background", False)
    if flag is not False and not (background and flag is True):
        return None
    return command


def _inside(path, roots):
    """True when the real path equals or lies inside one of the real roots."""
    real = Path(os.path.realpath(path))
    return any(real == root or real.is_relative_to(root) for root in roots)


def _git_directory(args, cwd):
    """The directory git starts in after its ``-C`` options, or None."""
    directory, i = cwd, 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            value = args[i + 1]
            directory = value if os.path.isabs(value) else (
                os.path.join(directory, value) if directory else None)
            i += 2
        else:
            i += 1
    return directory if directory and os.path.isabs(directory) else None


def read_only(inputs, *, state, cwd=None, memory=None):
    """True only for a foreground Bash command made entirely of allowed segments.

    ``memory`` is the real path of the configured memory directory. The
    executive writes there without a permit, so git never starts inside it:
    a planted git configuration could name a program for git to run.
    """
    command = _bash_inputs(inputs, background=False)
    if command is None or any(mark in command for mark in READ_ONLY_FORBIDDEN):
        return False
    try:
        tokens = _tokens(command)
    except Refused:
        return False
    launcher = str(Path(state).parent / LAUNCHER)
    segments, current = [], []
    for token in tokens:
        if token[0] == "op":
            if token[1] != "|":
                return False
            segments.append(current); current = []
        else:
            current.append(token[1])
    segments.append(current)
    for words in segments:
        if not words:
            return False
        if words[0] == launcher:
            if not (_safe_file(launcher, owned=True) and _launcher(words[1:])):
                return False
            continue
        rule = RULES.get(words[0])
        if rule is None or not rule(words[1:]):
            return False
        if words[0] == "git" and memory is not None:
            directory = _git_directory(words[1:], cwd)
            if directory is None or _inside(directory, [Path(memory)]):
                return False
    return True


def _absolute_target(value, protected):
    """An absolute redirection target that cannot rewrite Odin's admission inputs.

    A script must not write to itself or another registered script (bash reads
    a script as it runs), to the state directory with the registry and audit,
    or into any ``.git`` path, and no existing component may be a symlink.
    """
    if (not isinstance(value, str) or not value.startswith("/") or "\x00" in value or
            ".." in value.split("/") or ".git" in value.lower().split("/")):
        return False
    path = Path(value)
    if any(part.is_symlink() for part in (path, *path.parents)):
        return False
    real = Path(os.path.realpath(value))
    return not any(real == root or (root.is_dir() and real.is_relative_to(root)) for root in protected)


def registered_script(inputs, *, scripts, state=None):
    """True for a registered script path whose current hash matches, with plain
    arguments and optional redirections to absolute paths or ``2>&1``."""
    if not scripts:
        return False
    command = _bash_inputs(inputs, background=True)
    if command is None or any(mark in command for mark in SCRIPT_FORBIDDEN):
        return False
    try:
        tokens = _tokens(command)
    except Refused:
        return False
    if not tokens or tokens[0][0] != "word":
        return False
    path = tokens[0][1]
    expected = next((s["sha256"] for s in scripts if s["path"] == path), None)
    # An interpreter registered before this check existed is refused here too.
    if expected is None or not _safe_file(path) or interpreter(path):
        return False
    protected = [Path(os.path.realpath(s["path"])) for s in scripts]
    if state is not None:
        protected.append(Path(os.path.realpath(state)))
    i = 1
    while i < len(tokens):
        kind, text, extra = tokens[i]
        if kind == "word":
            i += 1
            continue
        target = tokens[i + 1] if i + 1 < len(tokens) else None
        if target is None or target[0] != "word":
            return False
        if text == ">&":
            if extra != "2" or target[1] != "1":
                return False
        elif text in (">", ">>"):
            if extra not in (None, "1", "2") or not _absolute_target(target[1], protected):
                return False
        elif text == "<":
            if extra not in (None, "0") or not _absolute_target(target[1], protected):
                return False
        else:
            return False
        i += 2
    return script_digest(path) == expected


def script_digest(path):
    """SHA-256 of the file at ``path``, or None when it cannot be read safely."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SCRIPT_BYTES:
            return None
        hasher = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None
    finally:
        os.close(fd)


def interpreter_name(name):
    """True when a file name is an interpreter's, ignoring case, a version
    suffix, a ``-cli`` suffix and a JavaScript or ``.exe`` extension."""
    name = name.lower()
    for suffix in (".exe", ".js", ".mjs", ".cjs", "-cli"):
        name = name.removesuffix(suffix)
    return bool(INTERPRETER_NAME.fullmatch(name))


def _interpreter_files():
    """Real paths of interpreter-named entries on PATH and the standard directories."""
    directories = [d for d in os.environ.get("PATH", "").split(os.pathsep) if os.path.isabs(d)]
    directories += [*INTERPRETER_DIRS, os.path.expanduser("~/.local/bin")]
    found = set()
    for directory in dict.fromkeys(directories):
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue
        for entry in entries:
            if interpreter_name(entry.name):
                found.add(os.path.realpath(entry.path))
    return found


def interpreter(path):
    """True when ``path`` is an interpreter or shell rather than a script.

    It matches the basename of the path and of its resolved real path, then
    the file's identity (same inode, or same size and SHA-256) against the
    interpreter-named programs on PATH and in the standard directories. That
    covers a renamed copy of an ELF interpreter and a shebang wrapper such as
    ``npx-cli.js``. A script whose shebang names an interpreter is a script.
    A copy of an interpreter found on neither is not detected.
    """
    real = os.path.realpath(path)
    if interpreter_name(os.path.basename(path)) or interpreter_name(os.path.basename(real)):
        return True
    try:
        info = os.stat(real)
    except OSError:
        return False
    sha256 = None
    for candidate in _interpreter_files():
        try:
            other = os.stat(candidate)
        except OSError:
            continue
        if (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino):
            return True
        if stat.S_ISREG(other.st_mode) and other.st_size == info.st_size:
            sha256 = sha256 or script_digest(real)
            if sha256 is not None and script_digest(candidate) == sha256:
                return True
    return False


def registered_interpreter(inputs, *, scripts):
    """True when a Bash command starts with a registered path that is an interpreter."""
    command = inputs.get("command") if isinstance(inputs, dict) else None
    if not scripts or not isinstance(command, str):
        return False
    try:
        tokens = _tokens(command)
    except Refused:
        return False
    if not tokens or tokens[0][0] != "word":
        return False
    return any(s["path"] == tokens[0][1] for s in scripts) and interpreter(tokens[0][1])


def script_path(value):
    """Validate an operator script path for registration; raises ValueError."""
    if isinstance(value, str) and os.path.isabs(value) and interpreter(value):
        raise ValueError("script_is_interpreter")
    if not _safe_file(value):
        raise ValueError("registered_script_invalid")
    return value


def registered_scripts(state):
    """Validated registrations, or None when absent or unreadable (no exception)."""
    path = Path(state) / "executive-pilot" / SCRIPTS_FILE
    try:
        if path.is_symlink() or not path.is_file():
            return None
        value = strict_loads(path.read_bytes()[:65537])
        Contracts().validate("executive-registered-scripts", value)
        return value["scripts"]
    except Exception:  # absent, unreadable or invalid: no registered scripts
        return None


def audit(state, kind, tool, inputs):
    """Append one content-free admission record; raises OSError when it cannot."""
    record = {"schema_version": 1, "time": now(), "path": kind, "tool": tool,
              "input_digest": input_digest(tool, inputs)}
    Contracts().validate("executive-intervention-audit", record)
    base = Path(state) / "executive-pilot"
    if base.is_symlink() or not base.is_dir():
        raise OSError("audit_directory_unavailable")
    fd = os.open(base / AUDIT_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise OSError("audit_file_not_private")
        os.write(fd, (canonical(record) + "\n").encode())
    finally:
        os.close(fd)


def input_digest(tool, inputs):
    """Digest of the executable input; the native description label is ignored."""
    return digest({"tool": tool, "input": {k: v for k, v in inputs.items() if k != "description"}})
