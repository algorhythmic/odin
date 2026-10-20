"""Native Claude Code executive pilot, separate from the gated SDK adapter.

Only preparation and local launch policy are verified here. A successful
process launch does not prove login, Remote Control, model identity or a
service-enforced budget. The native UI owns those observations for this pilot.
"""

from __future__ import annotations

import fcntl
import os
import pwd
import shutil
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from .contracts import ROOT, Contracts, canonical, strict_loads

DEFAULT_MODEL = "claude-fable-5-1"
MCP_TOOLS = (
    "odin_resume",
    "odin_memory_snapshot",
    "odin_read_evidence",
    "odin_report",
    "odin_reports",
)
ALLOWED_TOOLS = [f"mcp__odin__{name}" for name in MCP_TOOLS]
DENIED_TOOLS = [
    "Bash",
    "PowerShell",
    "REPL",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Agent",
    "Task",
    "Skill",
    "NotebookEdit",
    "ToolSearch",
    "EnterWorktree",
    "ExitWorktree",
]
REQUIRED_FLAGS = (
    "--remote-control",
    "--restricted",
    "--tools",
    "--strict-mcp-config",
    "--mcp-config",
    "--settings",
    "--setting-sources",
    "--session-id",
    "--resume",
    "--permission-mode",
    "--disable-slash-commands",
    "--no-chrome",
    "--model",
    "--effort",
    "--system-prompt",
    "--system-prompt-snapshot",
)


def _private_directory(value, *, create=False):
    path = Path(value).expanduser().absolute()
    if path != path.resolve():
        raise PermissionError("pilot directories must not traverse symlinks")
    if path == ROOT or ROOT.is_relative_to(path) or path.is_relative_to(ROOT):
        raise PermissionError(
            "pilot state and credentials must be outside the repository"
        )
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise PermissionError(
            "pilot directory must be owned by this user with mode 0700"
        )
    return path


def _private_file(path):
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise PermissionError(
            "pilot files must be private regular files owned by this user"
        )


def _executable(value):
    path = Path(value).expanduser().absolute()
    info = path.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise PermissionError(
            "executable must be a regular executable without shared write access"
        )
    # Preserve a virtualenv's original executable path: resolving its symlink
    # would select the base Python and discard its installed dependencies.
    return str(path)


def _profile(value, *, create=False):
    path = Path(value).expanduser().absolute()
    real_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    for home in {real_home, Path.home()}:
        default = home / ".claude"
        if path == home or path == default or path.is_relative_to(default):
            raise PermissionError(
                "a dedicated Claude configuration directory is required"
            )
    path = _private_directory(path, create=create)
    credential = path / ".credentials.json"
    if credential.exists() or credential.is_symlink():
        _private_file(credential)  # Metadata only. Never read or copy credentials.
    return path


def _write(path, name, value):
    Contracts().validate(name, value)
    temporary = path.with_name(path.name + ".new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(canonical(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path, name):
    _private_file(path)
    with path.open() as handle:
        value = strict_loads(handle.read(65537))
    Contracts().validate(name, value)
    return value


def _settings(enable_mcp):
    return {
        "permissions": {
            "allow": ALLOWED_TOOLS if enable_mcp else [],
            "deny": DENIED_TOOLS,
            "defaultMode": "dontAsk",
            "disableBypassPermissionsMode": "disable",
        },
        "disableAllHooks": True,
        "autoMemoryEnabled": False,
        "enabledPlugins": {},
    }


def _mcp(manifest):
    if not manifest["enable_mcp"]:
        return {"mcpServers": {}}
    return {
        "mcpServers": {
            "odin": {
                "type": "stdio",
                "command": manifest["python_executable"],
                "args": [
                    "-m",
                    "odin.executive_mcp",
                    "--state",
                    manifest["state"],
                    "--project",
                    manifest["project"],
                ],
                "env": {"PYTHONPATH": str(ROOT / "python"), "PYTHONNOUSERSITE": "1"},
            }
        }
    }


def prepare(
    state,
    *,
    config_dir,
    project,
    model=DEFAULT_MODEL,
    effort="high",
    claude_binary=None,
    python_executable=None,
    remote_name="Odin executive",
    enable_mcp=True,
):
    """Prepare private runtime files. Does not authenticate or invoke a model."""
    state = _private_directory(state, create=True)
    base = _private_directory(state / "executive-pilot", create=True)
    profile = Path(config_dir).expanduser().absolute()
    if (
        profile == state
        or profile == base
        or profile.is_relative_to(base / "workspace")
    ):
        raise PermissionError(
            "credential directory must be separate from the pilot workspace"
        )
    profile = _profile(profile, create=True)
    binary = claude_binary or shutil.which("claude")
    if binary is None:
        raise FileNotFoundError("Claude Code is not installed")
    manifest = {
        "version": 1,
        "state": str(state),
        "config_dir": str(profile),
        "project": project,
        "model": model,
        "effort": effort,
        "remote_name": remote_name,
        "enable_mcp": enable_mcp,
        "claude_binary": _executable(binary),
        "python_executable": _executable(python_executable or sys.executable),
        "native_session_id": str(uuid.uuid4()),
    }
    Contracts().validate("executive-pilot", manifest)
    with _lease(base / "prepare.lock"):
        if (base / "manifest.json").exists():
            existing = _read(base / "manifest.json", "executive-pilot")
            manifest["native_session_id"] = existing["native_session_id"]
            if existing != manifest:
                raise ValueError(
                    "pilot already prepared with a different configuration"
                )
            _load(state)
            return existing
        for name in ("workspace", "home"):
            _private_directory(base / name, create=True)
        _write(
            base / "settings.json", "executive-pilot-settings", _settings(enable_mcp)
        )
        _write(base / "mcp.json", "executive-pilot-mcp", _mcp(manifest))
        _write(base / "manifest.json", "executive-pilot", manifest)
    return manifest


def _load(state):
    state = _private_directory(state)
    base = _private_directory(state / "executive-pilot")
    manifest = _read(base / "manifest.json", "executive-pilot")
    if manifest["state"] != str(state):
        raise PermissionError("pilot state identity changed")
    profile = _profile(manifest["config_dir"])
    if (
        profile == state
        or profile == base
        or profile.is_relative_to(base / "workspace")
    ):
        raise PermissionError("credential directory overlaps the pilot workspace")
    for name in ("workspace", "home"):
        _private_directory(base / name)
    _executable(manifest["claude_binary"])
    _executable(manifest["python_executable"])
    if _read(base / "settings.json", "executive-pilot-settings") != _settings(
        manifest["enable_mcp"]
    ):
        raise PermissionError("prepared settings differ from the narrow pilot policy")
    if _read(base / "mcp.json", "executive-pilot-mcp") != _mcp(manifest):
        raise PermissionError(
            "prepared MCP configuration differs from the scoped bridge"
        )
    return manifest, base


def _environment(manifest, base):
    # An allowlist prevents API keys, provider overrides, shell loaders,
    # developer SDK settings and unrelated service credentials from leaking.
    return {
        "HOME": str(base / "home"),
        "CLAUDE_CONFIG_DIR": manifest["config_dir"],
        "PATH": os.pathsep.join(
            (str(Path(manifest["claude_binary"]).parent), "/usr/bin", "/bin")
        ),
        "LANG": "C.UTF-8",
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "USER": pwd.getpwuid(os.getuid()).pw_name,
        "LOGNAME": pwd.getpwuid(os.getuid()).pw_name,
    }


def _prompt(project):
    return (
        "You are Odin's executive agent in a native Claude Code pilot. Fable is the "
        "requested model; native model selection is not independently verified here. "
        "Communicate clearly with the human operator. Your only "
        f"Odin project scope is {project}. Read its current resume and memory before "
        "making claims about work. Use exact evidence reads for factual verification. "
        "Persist useful progress summaries and improvement proposals through odin_report "
        "with a stable operation_id; read odin_reports before repeating a report. Distinguish "
        "observed activity, reported progress, inferred progress and verified results. "
        "A proposal is not approval. Reports do not change commitments or checkpoints. "
        "Do not claim that conversation messages are automatically imported into Odin. "
        "Do not claim workers ran, tests passed, permissions changed, or improvement "
        "was applied without exact supporting evidence. Worker execution, native child "
        "agents, automatic code changes and live Saga delegation are unavailable here. "
        "Discuss self-improvements as bounded proposals with evidence and a test plan. "
        "Remote chat does not grant service authority. Report unavailable sources explicitly."
    )


def launch_spec(state, *, resume=False):
    """Return exact argv/cwd/environment without connecting or starting Claude."""
    manifest, base = _load(state)
    return _launch_spec(manifest, base, resume=resume)


def _launch_spec(manifest, base, *, resume=False):
    argv = [
        manifest["claude_binary"],
        "--remote-control",
        manifest["remote_name"],
        "--model",
        manifest["model"],
        "--effort",
        manifest["effort"],
        "--restricted",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--setting-sources",
        "",
        "--settings",
        str(base / "settings.json"),
        "--strict-mcp-config",
        "--mcp-config",
        str(base / "mcp.json"),
        "--disable-slash-commands",
        "--no-chrome",
        "--system-prompt",
        _prompt(manifest["project"]),
        "--system-prompt-snapshot",
        "off",
        "--resume" if resume else "--session-id",
        manifest["native_session_id"],
    ]
    if manifest["enable_mcp"]:
        argv.extend(["--allowedTools", ",".join(ALLOWED_TOOLS)])
    return {
        "argv": argv,
        "cwd": str(base / "workspace"),
        "env": _environment(manifest, base),
    }


def login_spec(state):
    """Use exactly the same isolated HOME and credential lineage as the pilot."""
    manifest, base = _load(state)
    return {
        "argv": [manifest["claude_binary"], "auth", "login", "--claudeai"],
        "cwd": str(base / "workspace"),
        "env": _environment(manifest, base),
    }


@contextmanager
def _lease(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        _private_file(path)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise _LeaseBusy(
                "pilot or credential lineage already has an active owner"
            ) from None
        yield fd
    finally:
        os.close(fd)


class _LeaseBusy(PermissionError):
    pass


@contextmanager
def _owned_runtime(state):
    state = _private_directory(state)
    base = _private_directory(state / "executive-pilot")
    with _lease(base / "runtime.lock") as runtime_lock:
        # A concurrent rotation can finish while we are entering the lock.
        # Read identity only after ownership is acquired, then use this same
        # snapshot for the launch request and its journal.
        manifest, base = _load(state)
        with _lease(
            Path(manifest["config_dir"]) / ".odin-lineage.lock"
        ) as credential_lock:
            yield manifest, base, runtime_lock, credential_lock


def _socket_ready(state, project):
    from .executive_mcp import ExecutiveBridge, SocketGateway

    result = ExecutiveBridge(project, SocketGateway(state, timeout=2)).call(
        "odin_resume", {}
    )
    if result["isError"]:
        raise PermissionError("scoped executive service is unavailable")


def probe(state):
    """Read-only CLI help/version probe; no authentication or model request."""
    manifest, base = _load(state)
    environment = _environment(manifest, base)
    results = []
    for flag in ("--version", "--help"):
        result = subprocess.run(
            [manifest["claude_binary"], flag],
            cwd=base / "workspace",
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        results.append(result.stdout)
    missing = [flag for flag in REQUIRED_FLAGS if flag not in results[1]]
    return {
        "version": results[0].strip()[:200],
        "missing_flags": missing,
        "model_verified": False,
        "remote_control_verified": False,
    }


def _foreground(spec, locks):
    with subprocess.Popen(
        spec["argv"], cwd=spec["cwd"], env=spec["env"], pass_fds=tuple(locks)
    ) as process:
        while True:
            try:
                return process.wait()
            except KeyboardInterrupt:
                # The foreground process receives Ctrl+C too. Let Claude handle
                # its native interrupt/exit flow while retaining the lineage lease.
                continue


def start(state, *, resume=False):
    """Run a foreground pilot. Its native UI reports login/model/RC outcomes."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PermissionError("start the executive pilot in a foreground terminal")
    with _owned_runtime(state) as (manifest, base, runtime_lock, credential_lock):
        if manifest["enable_mcp"]:
            _socket_ready(manifest["state"], manifest["project"])
        capability = probe(state)
        if capability["missing_flags"]:
            raise PermissionError("installed Claude Code lacks required pilot flags")
        receipt = base / "launch.json"
        if receipt.exists() and not resume:
            raise PermissionError("a prior launch was attempted; use explicit resume")
        _write(
            receipt,
            "executive-pilot-launch",
            {
                "version": 1,
                "native_session_id": manifest["native_session_id"],
                "state": "launch_requested",
                "resume": resume,
                "exit_code": None,
            },
        )
        result = _foreground(
            _launch_spec(manifest, base, resume=resume), (runtime_lock, credential_lock)
        )
        _write(
            receipt,
            "executive-pilot-launch",
            {
                "version": 1,
                "native_session_id": manifest["native_session_id"],
                "state": "process_exited",
                "resume": resume,
                "exit_code": result,
            },
        )
        return result


def login(state):
    """Foreground native login; the operator completes the OAuth flow."""
    manifest, _base = _load(state)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PermissionError("complete the dedicated login in a foreground terminal")
    with _lease(Path(manifest["config_dir"]) / ".odin-lineage.lock") as credential_lock:
        return _foreground(login_spec(state), (credential_lock,))


def new_session(state):
    """Explicit recovery after an uncertain/failed native start; preserve history.

    This never infers whether Claude created a conversation. It retains the
    old UUID/launch observation and requires both ownership leases to be free.
    """
    with _owned_runtime(state) as (manifest, base, _runtime_lock, _credential_lock):
        previous = manifest["native_session_id"]
        receipt = base / "launch.json"
        observation = (
            _read(receipt, "executive-pilot-launch")
            if receipt.exists()
            else {
                "version": 1,
                "native_session_id": previous,
                "state": "not_launched",
                "resume": False,
                "exit_code": None,
            }
        )
        _write(base / f"launch-{previous}.json", "executive-pilot-launch", observation)
        manifest["native_session_id"] = str(uuid.uuid4())
        _write(base / "manifest.json", "executive-pilot", manifest)
        receipt.unlink(missing_ok=True)
    return {
        "previous_native_session_id": previous,
        "native_session_id": manifest["native_session_id"],
        "native_history_preserved": True,
    }


def status(state):
    manifest, base = _load(state)
    running = False
    if (base / "runtime.lock").exists():
        try:
            with _lease(base / "runtime.lock"):
                pass
        except _LeaseBusy:
            running = True
    receipt = None
    if (base / "launch.json").exists():
        receipt = _read(base / "launch.json", "executive-pilot-launch")
    return {
        "mode": "native-claude-code-executive-pilot",
        "configuration": manifest,
        "process_lease_held": running,
        "last_launch": receipt,
        "credential_file_present": (
            Path(manifest["config_dir"]) / ".credentials.json"
        ).exists(),
        "authentication": "unverified",
        "model": "requested_not_verified",
        "remote_control": "requested_not_verified",
        "sdk_adapter_enabled": False,
        "delegated_execution_enabled": False,
        "service_budget_enforced": False,
    }
