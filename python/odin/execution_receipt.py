"""Structured execution receipts: attributed local evidence of one command run.

A receipt is derived from repository and process observations made by this
module around a command it executed itself. It is not Saga verification,
canonical acceptance or required review, and it does not prove that the host
was uncompromised or unshared. The executive principal that runs the command
can also write the file by hand, so a receipt is self-attested evidence whose
validation establishes internal consistency and binding, never authorship.
Its trust limits are documented in docs/DEVELOPMENT-LOOP.md ("Execution
receipts").

Privacy scope: the receipt records argv verbatim, the resolved executable,
repository identity (branch, commit, diff digests, bounded path lists) and the
command's stdout/stderr as retained artifacts. It never records environment
variables, credential files, ignored files or file contents of the worktree.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import signal
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from .contracts import DEPLOYMENT, ROOT, Contracts, canonical, identifier, strict_loads

SCHEMA = "execution-receipt"
SCHEMA_VERSION = 1
RECEIPT_NAME = "receipt.json"
MAX_RECEIPT_BYTES = 262144
MAX_ARTIFACT_HASH_BYTES = 64 * 1024 * 1024
MAX_VALIDATION_HASH_BUDGET = 256 * 1024 * 1024
MAX_LISTED_PATHS = 256
MAX_UNTRACKED_HASHED_BYTES = 8 * 1024 * 1024
MAX_PROBLEM_BYTES = 1400
MAX_PROBLEMS = 256
MAX_REFERENCES = 16
GIT_TIMEOUT = 60
GIT_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "LC_ALL": "C",
    "HOME": "/nonexistent",
}
OUTCOMES = ("valid", "uncertain", "invalid", "missing", "mismatched")
EVIDENCE_STATUSES = (
    "validated",
    "validated_unobserved",
    "uncertain",
    "invalid",
    "missing",
    "mismatched",
    "legacy_no_receipt",
)
SUMMARY_KEYS = (
    "outcome",
    "path",
    "sha256",
    "receipt_id",
    "binding",
    "collector_revision",
    "collector_matches_validator",
    "observed",
    "observed_before",
    "observed_after",
    "before_reason",
    "after_reason",
    "root",
    "cwd",
    "head",
    "branch",
    "detached",
    "clean_before",
    "clean",
    "worktree_identity",
    "argv_head",
    "argv_digest",
    "started_at",
    "exit_status",
    "succeeded",
    "uncertainty",
    "changed_during_run",
    "problems",
)


class ReceiptError(ValueError):
    pass


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _clip(text, limit=200):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


_read = os.read  # patched by tests to simulate growth during inspection


def _inspect_file(path, *, limit, private=False, keep=False):
    """Bounded inspection of one regular file via one descriptor.

    Returns ``{"status", "size", "bytes", "sha256", "data"}``. ``status`` is
    ``ok``, ``unreadable``, ``not_regular`` (FIFO, socket, device, directory;
    never read, so a FIFO without a writer cannot block), ``not_private``,
    ``too_large`` (initial size or actual bytes beyond ``limit``) or
    ``changed`` (size or mtime differed after the read, or the path no longer
    names the inspected inode). ``data`` holds the exact bytes that were
    hashed when ``keep`` is set, so callers parse what they checked instead of
    reopening the path. The inspection is point-in-time, not a snapshot; a
    hung filesystem can still block the open or read.
    """
    result = {
        "status": "unreadable",
        "size": None,
        "bytes": 0,
        "sha256": None,
        "data": None,
    }
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOCTTY
    try:
        fd = os.open(path, flags)
    except OSError:
        return result
    try:
        info = os.fstat(fd)
        result["size"] = info.st_size
        if not stat.S_ISREG(info.st_mode):
            return result | {"status": "not_regular"}
        if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            return result | {"status": "not_private"}
        if info.st_size > limit:
            return result | {"status": "too_large"}
        digest = hashlib.sha256()
        chunks = []
        total = 0
        while chunk := _read(fd, min(1 << 16, limit + 1 - total)):
            total += len(chunk)
            if total > limit:
                return result | {"status": "too_large", "bytes": total}
            digest.update(chunk)
            if keep:
                chunks.append(chunk)
        after = os.fstat(fd)
        try:
            named = os.lstat(path)
            replaced = (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino)
        except OSError:
            replaced = True
        if (
            total != info.st_size
            or (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns)
            or replaced
        ):
            return result | {"status": "changed", "bytes": total}
        return result | {
            "status": "ok",
            "bytes": total,
            "sha256": digest.hexdigest(),
            "data": b"".join(chunks) if keep else None,
        }
    except OSError:
        return result
    finally:
        os.close(fd)


def _sha256_file(path, *, limit=MAX_ARTIFACT_HASH_BYTES, private=False):
    """(sha256 or None, initial size) for callers that only need a digest."""
    inspected = _inspect_file(path, limit=limit, private=private)
    return inspected["sha256"], inspected["size"]


def _timestamp(value):
    return datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%S.%fZ" if "." in value else "%Y-%m-%dT%H:%M:%SZ"
    )


def _git(root, *arguments, binary=False, ok=(0,)):
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        timeout=GIT_TIMEOUT,
        check=False,
        env=GIT_ENV,
    )
    if completed.returncode not in ok:
        raise ReceiptError(
            f"git {arguments[0]} failed ({completed.returncode}): "
            + _clip(completed.stderr.decode("utf-8", "replace").strip())
        )
    if binary:
        return completed.returncode, completed.stdout
    return completed.returncode, completed.stdout.decode("utf-8", "replace")


def _name_status(raw):
    """Parse ``git diff --name-status -z``; renames and copies carry ``from``."""
    fields = raw.split("\0")
    entries = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        if status[0] in "RC":
            entries.append(
                {"status": status, "from": fields[index + 1], "path": fields[index + 2]}
            )
            index += 3
        else:
            entries.append({"status": status, "path": fields[index + 1]})
            index += 2
    return entries


def observe_repository(path):
    """Point-in-time git observation; a failure is an explicit non-observation.

    Returns ``{"observed": False, "reason": ...}`` when the path is not a git
    worktree or git is unavailable. A missing observation never asserts a clean
    tree. Untracked identity hashes the content of up to MAX_LISTED_PATHS
    untracked files that are each at most MAX_UNTRACKED_HASHED_BYTES; ignored
    files are never read or listed, and file contents are never recorded.
    """
    path = Path(path)
    try:
        _, toplevel = _git(path, "rev-parse", "--show-toplevel")
        root = Path(toplevel.strip()).resolve()
        _, head = _git(root, "rev-parse", "HEAD")
        head = head.strip()
        _, subject = _git(root, "log", "-1", "--format=%s", "HEAD")
        code, branch = _git(
            root, "symbolic-ref", "--quiet", "--short", "HEAD", ok=(0, 1)
        )
        branch = branch.strip() if code == 0 else None  # 1 means detached; others raise
        _, staged_raw = _git(
            root, "diff", "--cached", "--binary", "--no-ext-diff", "HEAD", binary=True
        )
        _, unstaged_raw = _git(root, "diff", "--binary", "--no-ext-diff", binary=True)
        _, staged_names = _git(root, "diff", "--cached", "--name-status", "-z", "HEAD")
        _, unstaged_names = _git(root, "diff", "--name-status", "-z")
        _, untracked_raw = _git(
            root, "ls-files", "--others", "--exclude-standard", "-z"
        )
        staged = _name_status(staged_names)
        unstaged = _name_status(unstaged_names)
        untracked_all = [item for item in untracked_raw.split("\0") if item]
    except (
        ReceiptError,
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
        IndexError,
    ) as error:
        return {
            "observed": False,
            "reason": _clip(f"{type(error).__name__}: {error}", 300),
            "observed_at": _now(),
        }
    untracked = []
    untracked_identity = hashlib.sha256()
    coverage = "complete"
    for relative in sorted(untracked_all)[:MAX_LISTED_PATHS]:
        file_digest, size = _sha256_file(
            root / relative, limit=MAX_UNTRACKED_HASHED_BYTES
        )
        if file_digest is None:
            coverage = "partial"
        untracked.append({"path": relative, "sha256": file_digest, "bytes": size})
        untracked_identity.update(canonical([relative, size, file_digest]).encode())
    if len(untracked_all) > MAX_LISTED_PATHS:
        coverage = "partial"
    staged_digest = hashlib.sha256(staged_raw).hexdigest()
    unstaged_digest = hashlib.sha256(unstaged_raw).hexdigest()
    untracked_digest = untracked_identity.hexdigest()
    worktree_identity = hashlib.sha256(
        canonical(
            {
                "head": head,
                "staged": staged_digest,
                "unstaged": unstaged_digest,
                "untracked": untracked_digest,
                "untracked_coverage": coverage,
            }
        ).encode()
    ).hexdigest()
    return {
        "observed": True,
        "observed_at": _now(),
        "root": str(root),
        "head": head,
        "head_subject": subject.rstrip("\n")[:200],
        "head_subject_is_branch_evidence": False,
        "branch": branch,
        "detached": branch is None,
        "staged": staged[:MAX_LISTED_PATHS],
        "unstaged": unstaged[:MAX_LISTED_PATHS],
        "untracked": untracked,
        "untracked_total": len(untracked_all),
        "untracked_coverage": coverage,
        "staged_digest": staged_digest,
        "unstaged_digest": unstaged_digest,
        "untracked_digest": untracked_digest,
        "worktree_identity": worktree_identity,
        "clean": not staged
        and not unstaged
        and not untracked_all
        and coverage == "complete",
        "coverage_note": (
            "staged/unstaged compared against HEAD by git diff; untracked limited to "
            f"{MAX_LISTED_PATHS} non-ignored files of at most {MAX_UNTRACKED_HASHED_BYTES} bytes; "
            "ignored files, submodule contents and file contents are not recorded"
        ),
    }


def module_source_sha256():
    digest, _size = _sha256_file(Path(__file__).resolve())
    return digest


def _collector():
    """Identity of the code that produced the receipt (self-reported)."""
    try:
        if DEPLOYMENT is not None:
            # A deployed copy (ODIN-ADR-039) has no git metadata.
            odin_revision, dirty = DEPLOYMENT["revision"], None
        else:
            _, odin_revision = _git(ROOT, "rev-parse", "HEAD")
            _, porcelain = _git(ROOT, "status", "--porcelain", "--untracked-files=no")
            odin_revision, dirty = odin_revision.strip(), bool(porcelain.strip())
    except (ReceiptError, OSError, subprocess.TimeoutExpired):
        odin_revision, dirty = None, None
    return {
        "module": "odin.execution_receipt",
        "schema_version": SCHEMA_VERSION,
        "source_sha256": module_source_sha256(),
        "odin_root": str(ROOT),
        "odin_revision": odin_revision,
        "odin_tracked_files_modified": dirty,
    }


def _resolve_executable(argv, cwd):
    program = argv[0]
    if "/" in program:
        resolved = (Path(cwd) / program).resolve()
        found = str(resolved) if resolved.exists() else None
    else:
        found = shutil.which(program)
        found = str(Path(found).resolve()) if found else None
    interpreter = None
    if found and Path(found).name.startswith(("python", "pypy")):
        try:
            version = subprocess.run(
                [found, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={"PATH": GIT_ENV["PATH"]},
            )
            interpreter = {
                "path": found,
                "version": (version.stdout or version.stderr).strip()[:120] or None,
            }
        except (OSError, subprocess.TimeoutExpired):
            interpreter = {"path": found, "version": None}
    return found, interpreter


def _private_directory(path):
    path = Path(path).resolve()
    if path == ROOT or ROOT in path.parents:
        raise PermissionError("receipts must be retained outside the repository")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise PermissionError(
            "receipt directory must be private and owned by this user"
        )
    return path


def _open_fresh(path):
    return os.fdopen(
        os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        ),
        "wb",
    )


def _write_private(path, data):
    temporary = path.with_name(path.name + "." + identifier() + ".tmp")
    with _open_fresh(temporary) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def run(
    argv, *, out, cwd=None, repository=None, binding=None, label=None, timeout=3600
):
    """Execute ``argv`` and derive a receipt from observations; never from claims.

    ``out`` is a private directory outside the repository that receives
    ``stdout.log``, ``stderr.log`` and ``receipt.json``; it must not already
    hold those files. ``binding`` may carry ``loop_id``, ``stage_id``,
    ``run_id`` and ``session_id``. The wrapper's own result is the receipt; a
    nonzero command exit is recorded, not raised. The command runs in its own
    session so a timeout kills its whole process group.
    """
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(a, str) for a in argv)
    ):
        raise ReceiptError("argv must be a non-empty list of strings")
    out = _private_directory(out)
    cwd = str(Path(cwd or os.getcwd()).resolve())
    repository = str(Path(repository or cwd).resolve())
    binding = dict(binding or {})
    binding.setdefault("run_id", identifier())
    stdout_path, stderr_path = out / "stdout.log", out / "stderr.log"
    before = observe_repository(repository)
    executable, interpreter = _resolve_executable(argv, cwd)
    started_at = _now()
    exit_status, uncertainty, signal_number, timed_out = None, None, None, False
    with _open_fresh(stdout_path) as stdout, _open_fresh(stderr_path) as stderr:
        try:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
        except OSError as error:
            uncertainty = _clip(f"spawn failed: {type(error).__name__}: {error}", 300)
        else:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                uncertainty = (
                    f"command exceeded {timeout} s; its process group was killed; "
                    "outcome unknown and retained output may be incomplete"
                )
            if timed_out:
                pass  # The exit status after SIGKILL is not the command's outcome.
            elif process.returncode is not None and process.returncode < 0:
                signal_number = -process.returncode
                if uncertainty is None:
                    uncertainty = f"command terminated by signal {signal_number}"
            elif process.returncode is not None:
                exit_status = process.returncode
    finished_at = _now()
    # Preserve the actual timestamps even when the wall clock reverses. Do not
    # invent a duration or lose the command's evidence to schema validation:
    # the validator will conservatively reject the reversed chronology.
    elapsed = (_timestamp(finished_at) - _timestamp(started_at)).total_seconds()
    duration = round(elapsed, 3) if elapsed >= 0 else None
    if duration is None:
        uncertainty = _clip(
            "wall clock moved backwards during command; elapsed duration unavailable"
            + (f"; {uncertainty}" if uncertainty else ""),
            300,
        )
    after = observe_repository(repository)
    artifacts = []
    for name, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        file_digest, size = _sha256_file(path, private=True)
        artifacts.append(
            {"name": name, "path": str(path), "sha256": file_digest, "bytes": size}
        )
    changed = (
        before.get("worktree_identity") != after.get("worktree_identity")
        if before.get("observed") and after.get("observed")
        else None
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "kind": "execution_receipt",
        "receipt_id": identifier(),
        "label": label,
        "binding": binding,
        "collector": _collector(),
        "command": {
            "argv": argv,
            "executable": executable,
            "interpreter": interpreter,
            "cwd": cwd,
            "timeout_seconds": timeout,
        },
        "execution": {
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            "exit_status": exit_status,
            "succeeded": exit_status == 0,
            "timed_out": timed_out,
            "signal": signal_number,
            "uncertainty": uncertainty,
        },
        "repository": {
            "path": repository,
            "before": before,
            "after": after,
            "changed_during_run": changed,
        },
        "artifacts": artifacts,
        "limits": {
            "attribution": "self-attested by the executing user; same uid as the "
            "collector; no independent witness or registry",
            "concurrency": "observations and file inspections are point-in-time, not "
            "snapshots; concurrent writers between before/after observations are detected "
            "only if the identity differs; a size, mtime or path change during an "
            "inspection is reported; non-regular files are never read",
            "environment": "environment variables and credential files are not recorded",
            "outputs": "stdout/stderr retained verbatim; pass no secrets on argv or output",
        },
    }
    Contracts().validate(SCHEMA, receipt)
    _write_private(out / RECEIPT_NAME, (canonical(receipt) + "\n").encode())
    return receipt


def reference(path):
    """Compact typed reference to a retained receipt file."""
    path = Path(path)
    file_digest, _size = _sha256_file(path, limit=MAX_RECEIPT_BYTES, private=True)
    if file_digest is None:
        raise ReceiptError("receipt file is missing, not private, or too large")
    return {
        "kind": "execution_receipt",
        "path": str(path.resolve()),
        "sha256": file_digest,
    }


def _refused(outcome, path, problem):
    return {
        "outcome": outcome,
        "path": str(path),
        "sha256": None,
        "observed": None,
        "observed_before": None,
        "observed_after": None,
        "problems": [_clip(problem, MAX_PROBLEM_BYTES)],
        "checks": [],
    }


EMPTY_DIFF_DIGEST = hashlib.sha256(b"").hexdigest()


def _observation_contradictions(label, observation):
    """Recompute every derived field an observation claims; list disagreements."""
    problems = []
    if not observation.get("observed"):
        return problems
    untracked = observation["untracked"]
    recomputed = hashlib.sha256()
    for entry in untracked:
        recomputed.update(
            canonical([entry["path"], entry["bytes"], entry["sha256"]]).encode()
        )
    if recomputed.hexdigest() != observation["untracked_digest"]:
        problems.append(
            f"contradictory: {label} untracked_digest does not derive from its list"
        )
    if [entry["path"] for entry in untracked] != sorted(
        entry["path"] for entry in untracked
    ):
        problems.append(
            f"contradictory: {label} untracked list is not in collector order"
        )
    if len(untracked) != min(observation["untracked_total"], MAX_LISTED_PATHS):
        problems.append(
            f"contradictory: {label} untracked list length disagrees with its total"
        )
    coverage = (
        "partial"
        if observation["untracked_total"] > MAX_LISTED_PATHS
        or any(entry["sha256"] is None for entry in untracked)
        else "complete"
    )
    if coverage != observation["untracked_coverage"]:
        problems.append(
            f"contradictory: {label} untracked_coverage disagrees with its list"
        )
    for section in ("staged", "unstaged"):
        empty = observation[f"{section}_digest"] == EMPTY_DIFF_DIGEST
        if bool(observation[section]) == empty:
            problems.append(
                f"contradictory: {label} {section} list disagrees with its diff digest"
            )
    identity = hashlib.sha256(
        canonical(
            {
                "head": observation["head"],
                "staged": observation["staged_digest"],
                "unstaged": observation["unstaged_digest"],
                "untracked": observation["untracked_digest"],
                "untracked_coverage": observation["untracked_coverage"],
            }
        ).encode()
    ).hexdigest()
    if identity != observation["worktree_identity"]:
        problems.append(
            f"contradictory: {label} worktree_identity does not derive from its digests"
        )
    clean = (
        not observation["staged"]
        and not observation["unstaged"]
        and observation["untracked_total"] == 0
        and observation["untracked_coverage"] == "complete"
    )
    if clean != observation["clean"]:
        problems.append(
            f"contradictory: {label} clean flag disagrees with its listed changes"
        )
    if observation["detached"] != (observation["branch"] is None):
        problems.append(
            f"contradictory: {label} detached flag disagrees with its branch"
        )
    return problems


def _consistency(receipt):
    """Internal contradictions make a receipt invalid; uncertainty stays explicit."""
    problems = []
    execution = receipt["execution"]
    if execution["succeeded"] != (execution["exit_status"] == 0):
        problems.append("contradictory: succeeded disagrees with exit_status")
    if execution["exit_status"] is None and not (
        execution["timed_out"]
        or execution["signal"] is not None
        or execution["uncertainty"]
    ):
        problems.append(
            "contradictory: exit_status is null without timeout, signal or uncertainty"
        )
    if execution["exit_status"] is not None and execution["signal"] is not None:
        problems.append("contradictory: both exit_status and signal are set")
    if execution["timed_out"] and execution["exit_status"] is not None:
        problems.append("contradictory: timed_out with an exit_status")
    if execution["timed_out"] and not execution["uncertainty"]:
        problems.append("contradictory: timed_out without recorded uncertainty")
    try:
        started = _timestamp(execution["started_at"])
        finished = _timestamp(execution["finished_at"])
    except ValueError:
        problems.append("malformed: execution timestamps are not parseable")
        started = finished = None
    else:
        if finished < started:
            problems.append("contradictory: finished_at precedes started_at")
        elapsed = (finished - started).total_seconds()
        if execution["duration_seconds"] is None:
            if elapsed >= 0:
                problems.append(
                    "contradictory: duration_seconds unavailable without reversed execution timestamps"
                )
            if not execution["uncertainty"]:
                problems.append(
                    "contradictory: unavailable duration_seconds without recorded uncertainty"
                )
        elif abs(execution["duration_seconds"] - elapsed) > 2.0:
            problems.append(
                "contradictory: duration_seconds disagrees with the timestamps"
            )
    names = [artifact["name"] for artifact in receipt["artifacts"]]
    for required in ("stdout", "stderr"):
        if names.count(required) != 1:
            problems.append(
                f"contradictory: exactly one {required} artifact is required"
            )
    for artifact in receipt["artifacts"]:
        if not Path(artifact["path"]).is_absolute():
            problems.append(
                f"contradictory: artifact path is not absolute: {artifact['name']}"
            )
    repository = receipt["repository"]
    before, after = repository["before"], repository["after"]
    problems += _observation_contradictions("before", before)
    problems += _observation_contradictions("after", after)
    for label, observation in (("before", before), ("after", after)):
        if observation.get("observed"):
            root, target = Path(observation["root"]), Path(repository["path"])
            if target != root and root not in target.parents:
                problems.append(
                    f"contradictory: {label} root does not contain the repository path"
                )
    if before.get("observed") and after.get("observed"):
        if before["root"] != after["root"]:
            problems.append(
                "contradictory: before/after observations name different roots"
            )
        expected = before["worktree_identity"] != after["worktree_identity"]
        if (
            repository["changed_during_run"] is None
            or repository["changed_during_run"] != expected
        ):
            problems.append(
                "contradictory: changed_during_run disagrees with the two observations"
            )
    elif repository["changed_during_run"] is not None:
        problems.append(
            "contradictory: changed_during_run set without both observations"
        )
    if started is not None:
        try:
            for label, observation, bound, late in (
                ("before", before, started, True),
                ("after", after, finished, False),
            ):
                observed_at = _timestamp(observation["observed_at"])
                if late and observation.get("observed") and observed_at > bound:
                    problems.append(
                        "contradictory: before observation is later than the command start"
                    )
                if not late and observation.get("observed") and observed_at < bound:
                    problems.append(
                        "contradictory: after observation is earlier than the command end"
                    )
        except ValueError:
            problems.append("malformed: observation timestamps are not parseable")
    return problems


def validate(
    path, expected=None, *, declared_sha256=None, not_before=None, hash_budget=None
):
    """Deterministic validation of one receipt file; outcome is never a claim.

    Outcomes, in precedence order: ``invalid`` (unreadable, non-private, over
    size, schema violation, internally contradictory, an artifact beyond the
    inspection limit or the hashing budget), ``mismatched`` on a declared-digest
    mismatch (reported alone), ``missing`` (a referenced artifact absent),
    ``mismatched`` (artifact bytes, any ``expected`` identity, a run that
    changed the worktree, or a receipt older than ``not_before`` differs),
    ``uncertain`` (exactly one repository observation available, so an
    unchanged tree is not established), ``valid``. The receipt is parsed from
    the exact bounded bytes whose digest was checked. An ``expected`` or
    claimed ``clean`` is compared with the derived value: it can only be met
    by a receipt with both observations and no change during the run.
    """
    path = Path(path)
    try:
        info = path.lstat()
    except OSError:
        return _refused("missing", path, "receipt file missing")
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        return _refused(
            "invalid", path, "receipt must be a private regular file owned by this user"
        )
    inspected = _inspect_file(path, limit=MAX_RECEIPT_BYTES, private=True, keep=True)
    if inspected["status"] != "ok":
        return _refused(
            "invalid",
            path,
            f"receipt {inspected['status'].replace('_', ' ')} during inspection",
        )
    actual_digest = inspected["sha256"]
    if declared_sha256 is not None and declared_sha256 != actual_digest:
        result = _refused(
            "mismatched",
            path,
            "receipt bytes differ from the declared reference digest",
        )
        result["sha256"] = actual_digest
        result["checks"] = ["reference_digest"]
        return result
    try:
        receipt = strict_loads(inspected["data"].decode("utf-8"))
        Contracts().validate(SCHEMA, receipt)
    except Exception as error:  # noqa: BLE001 - every parse/schema failure is "invalid"
        return _refused(
            "invalid", path, f"{type(error).__name__}: {str(error).splitlines()[0]}"
        )
    checks = ["schema"] + (["reference_digest"] if declared_sha256 is not None else [])
    contradictions = _consistency(receipt)
    checks.append("consistency")
    if contradictions:
        return _finish(path, receipt, actual_digest, "invalid", contradictions, checks)
    problems = []
    missing = False
    budget = (
        hash_budget
        if hash_budget is not None
        else {"remaining": MAX_VALIDATION_HASH_BUDGET}
    )
    for artifact in receipt["artifacts"]:
        artifact_path = Path(artifact["path"])
        try:
            artifact_info = artifact_path.lstat()
        except OSError:
            problems.append(f"artifact missing: {artifact['name']}")
            missing = True
            continue
        if (
            not stat.S_ISREG(artifact_info.st_mode)
            or artifact_info.st_uid != os.getuid()
            or artifact_info.st_mode & 0o077
        ):
            problems.append(f"artifact not a private regular file: {artifact['name']}")
            continue
        limit = min(MAX_ARTIFACT_HASH_BYTES, budget["remaining"])
        if artifact_info.st_size > limit:
            problems.append(
                f"artifact beyond the inspection limit or hashing budget: {artifact['name']}"
            )
            return _finish(path, receipt, actual_digest, "invalid", problems, checks)
        current = _inspect_file(artifact_path, limit=limit, private=True)
        budget["remaining"] = max(0, budget["remaining"] - (current["bytes"] or 0))
        if current["status"] == "too_large":
            problems.append(
                f"artifact beyond the inspection limit or hashing budget: {artifact['name']}"
            )
            return _finish(path, receipt, actual_digest, "invalid", problems, checks)
        if current["status"] == "changed":
            problems.append(f"artifact changed during inspection: {artifact['name']}")
        elif current["status"] != "ok":
            problems.append(
                f"artifact {current['status'].replace('_', ' ')}: {artifact['name']}"
            )
        elif (
            current["sha256"] != artifact["sha256"]
            or current["bytes"] != artifact["bytes"]
        ):
            problems.append(f"artifact bytes changed: {artifact['name']}")
    checks.append("artifacts")
    execution, repository = receipt["execution"], receipt["repository"]
    before, after = repository["before"], repository["after"]
    both = bool(before.get("observed")) and bool(after.get("observed"))
    for key, value in (expected or {}).items():
        if key in ("exit_status", "succeeded"):
            observed = execution[key]
        elif key in ("loop_id", "stage_id", "run_id", "session_id"):
            observed = receipt["binding"].get(key)
        elif key == "clean":
            if not (both and repository["changed_during_run"] is False):
                problems.append(
                    "expected clean cannot be checked: unchanged tree not established"
                )
                continue
            observed = before["clean"]
        elif before.get("observed"):
            observed = before.get(key)
        else:
            problems.append(
                f"expected {key} cannot be checked: repository not observed"
            )
            continue
        if observed != value:
            problems.append(
                f"expected {key}={_clip(repr(value))} but receipt records {_clip(repr(observed))}"
            )
    if expected:
        checks.append("expected_identity")
    if repository.get("changed_during_run"):
        problems.append(
            "worktree changed during the run; the receipt does not describe the observed tree"
        )
        checks.append("worktree_changed_during_run")
    if not_before is not None:
        checks.append("not_before")
        try:
            predates = _timestamp(execution["started_at"]) < _timestamp(not_before)
        except ValueError:
            predates = True
        if predates:
            problems.append(
                f"receipt started at {execution['started_at']} predates {not_before}"
            )
    uncertain = bool(before.get("observed")) != bool(after.get("observed"))
    if uncertain:
        side, reason = (
            ("post-run", after.get("reason"))
            if before.get("observed")
            else ("pre-run", before.get("reason"))
        )
        problems.append(
            f"uncertain: {side} repository observation unavailable ({_clip(reason or 'no reason', 120)}); "
            "an unchanged tree is not established"
        )
        checks.append("observation_pair")
    if any(not problem.startswith("uncertain:") for problem in problems):
        outcome = "missing" if missing else "mismatched"
    elif uncertain:
        outcome = "uncertain"
    else:
        outcome = "valid"
    return _finish(path, receipt, actual_digest, outcome, problems, checks)


def _finish(path, receipt, actual_digest, outcome, problems, checks):
    before, after = receipt["repository"]["before"], receipt["repository"]["after"]
    observed_before, observed_after = (
        bool(before.get("observed")),
        bool(after.get("observed")),
    )
    both = observed_before and observed_after
    # An invalid (contradictory) receipt supports no observed or derived claim;
    # only its identity, binding and problems are reported.
    usable = outcome != "invalid"
    unchanged = (
        usable and both and receipt["repository"].get("changed_during_run") is False
    )
    argv = receipt["command"]["argv"]
    return {
        "outcome": outcome,
        "path": str(path),
        "sha256": actual_digest,
        "receipt_id": receipt["receipt_id"],
        "binding": receipt["binding"],
        "collector_revision": receipt["collector"]["odin_revision"],
        "collector_matches_validator": receipt["collector"]["source_sha256"]
        == module_source_sha256(),
        "observed": both if usable else None,
        "observed_before": observed_before if usable else None,
        "observed_after": observed_after if usable else None,
        "before_reason": None
        if observed_before or not usable
        else before.get("reason"),
        "after_reason": None if observed_after or not usable else after.get("reason"),
        "root": before.get("root") if usable and observed_before else None,
        "cwd": receipt["command"]["cwd"],
        "head": before.get("head") if usable and observed_before else None,
        "branch": before.get("branch") if usable and observed_before else None,
        "detached": before.get("detached") if usable and observed_before else None,
        "clean_before": before.get("clean") if usable and observed_before else None,
        # Only an observed, unchanged run supports "clean": a missing post-run
        # observation never establishes an unchanged committed tree.
        "clean": before.get("clean") if unchanged else None,
        "worktree_identity": before.get("worktree_identity")
        if usable and observed_before
        else None,
        "argv_head": _clip(" ".join(argv), 160),
        "argv_digest": hashlib.sha256(canonical(argv).encode()).hexdigest(),
        "started_at": receipt["execution"]["started_at"] if usable else None,
        "exit_status": receipt["execution"]["exit_status"] if usable else None,
        "succeeded": receipt["execution"]["succeeded"] if usable else None,
        "uncertainty": receipt["execution"]["uncertainty"] if usable else None,
        "changed_during_run": receipt["repository"].get("changed_during_run")
        if usable
        else None,
        "problems": [
            _clip(problem, MAX_PROBLEM_BYTES) for problem in problems[:MAX_PROBLEMS]
        ],
        "checks": checks,
    }


def validate_references(
    evidence, *, expected=None, claims_key="claims", not_before=None
):
    """Validate every receipt reference in an evidence object; legacy is distinct.

    ``evidence["receipts"]`` is the typed list of references. Absent means
    ``legacy_no_receipt``: the evidence predates receipts or offers none; it is
    not validated and not a failure. ``evidence[claims_key]`` (optional object)
    holds structured claims about the run (``head``, ``branch``, ``detached``,
    ``clean``, ``exit_status``, ``succeeded``) compared against every receipt.
    Status precedence: ``invalid`` > ``missing`` > ``mismatched`` >
    ``uncertain`` > ``validated_unobserved`` > ``validated``. ``validated``
    requires every receipt valid with both repository observations present.
    ``commands_succeeded`` is true only when every receipt is not invalid and
    records a successful exit; an invalid receipt yields null.
    """
    empty = {"receipts": [], "problems": [], "commands_succeeded": None}
    if not isinstance(evidence, dict) or "receipts" not in evidence:
        return {"status": "legacy_no_receipt"} | empty
    contracts = Contracts()
    references = evidence["receipts"]
    try:
        contracts.validate_definition(SCHEMA, "references", references)
    except Exception as error:  # noqa: BLE001 - malformed references are reportable, not fatal
        problem = _clip(
            f"receipt references malformed: {str(error).splitlines()[0]}",
            MAX_PROBLEM_BYTES,
        )
        return {"status": "invalid"} | empty | {"problems": [problem]}
    claims = evidence.get(claims_key)
    if claims is not None and not isinstance(claims, dict):
        return (
            {"status": "invalid"} | empty | {"problems": ["claims must be an object"]}
        )
    merged = dict(expected or {})
    for key in ("head", "branch", "detached", "clean", "exit_status", "succeeded"):
        if claims and key in claims:
            merged[key] = claims[key]
    budget = {"remaining": MAX_VALIDATION_HASH_BUDGET}
    results = [
        validate(
            item["path"],
            merged or None,
            declared_sha256=item["sha256"],
            not_before=not_before,
            hash_budget=budget,
        )
        for item in references[:MAX_REFERENCES]
    ]
    outcomes = {result["outcome"] for result in results}
    if not results:
        status = "missing"
    elif "invalid" in outcomes:
        status = "invalid"
    elif "missing" in outcomes:
        status = "missing"
    elif "mismatched" in outcomes:
        status = "mismatched"
    elif "uncertain" in outcomes:
        status = "uncertain"
    elif all(r["observed"] for r in results):
        status = "validated"
    else:
        status = "validated_unobserved"
    problems = [
        _clip(f"{result['path']}: {problem}", MAX_PROBLEM_BYTES)
        for result in results
        for problem in result["problems"]
    ]
    if not results:
        problems.append("receipts list is empty")
    if "invalid" in outcomes or not results:
        commands_succeeded = None
    else:
        commands_succeeded = all(r.get("succeeded") is True for r in results)
    return {
        "status": status,
        "receipts": [
            {key: result.get(key) for key in SUMMARY_KEYS} for result in results
        ],
        "problems": problems[:MAX_PROBLEMS],
        "commands_succeeded": commands_succeeded,
    }


def dispatch_argv(argv):
    """Return the receipt sub-argv when ``argv`` names a receipt action first.

    Only ``[--state X] receipt-run|receipt-validate ...`` dispatches; any other
    leading option means the main parser owns the arguments.
    """
    index = 2 if argv[:1] == ["--state"] else 0
    if len(argv) > index and argv[index] in ("receipt-run", "receipt-validate"):
        return [argv[index].removeprefix("receipt-")] + argv[index + 1 :]
    return None


def main(argv=None):
    """``receipt-run`` and ``receipt-validate`` entry points used by ``odin``."""
    import argparse

    parser = argparse.ArgumentParser(prog="odin receipt")
    sub = parser.add_subparsers(dest="action", required=True)
    runner = sub.add_parser("run", help="execute a command and retain its receipt")
    runner.add_argument(
        "--out", required=True, help="fresh private directory outside the repository"
    )
    runner.add_argument("--cwd", help="execution directory (default: current)")
    runner.add_argument("--repository", help="repository to observe (default: cwd)")
    runner.add_argument("--loop", help="development loop ULID to bind")
    runner.add_argument("--stage", help="development stage ULID to bind")
    runner.add_argument("--label", help="short human label")
    runner.add_argument("--timeout", type=int, default=3600)
    runner.add_argument("command", nargs=argparse.REMAINDER, help="-- argv to execute")
    checker = sub.add_parser("validate", help="validate a retained receipt")
    checker.add_argument("--receipt", required=True)
    checker.add_argument("--expect", help="JSON object of expected identity fields")
    checker.add_argument("--sha256", help="declared receipt digest from a reference")
    args = parser.parse_args(argv)
    if args.action == "run":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            parser.error("receipt run requires a command after --")
        binding = {
            k: v for k, v in (("loop_id", args.loop), ("stage_id", args.stage)) if v
        }
        receipt = run(
            command,
            out=args.out,
            cwd=args.cwd,
            repository=args.repository,
            binding=binding,
            label=args.label,
            timeout=args.timeout,
        )
        before = receipt["repository"]["before"]
        summary = {
            "receipt": reference(Path(args.out) / RECEIPT_NAME),
            "exit_status": receipt["execution"]["exit_status"],
            "succeeded": receipt["execution"]["succeeded"],
            "uncertainty": receipt["execution"]["uncertainty"],
            "observed": bool(before.get("observed"))
            and bool(receipt["repository"]["after"].get("observed")),
            "observed_before": bool(before.get("observed")),
            "observed_after": bool(receipt["repository"]["after"].get("observed")),
            "head": before.get("head"),
            "branch": before.get("branch"),
            "detached": before.get("detached"),
            "clean_before": before.get("clean"),
            "clean": before.get("clean")
            if receipt["repository"]["changed_during_run"] is False
            else None,
            "changed_during_run": receipt["repository"]["changed_during_run"],
        }
        contradictions = _consistency(receipt)
        if contradictions:
            # A real command may finish across a backward wall-clock step.
            # Retain its raw outcome in the receipt, but use the validator's
            # redaction rules for the CLI's public summary as well.
            invalid = _finish(
                Path(args.out) / RECEIPT_NAME,
                receipt,
                summary["receipt"]["sha256"],
                "invalid",
                contradictions,
                ["consistency"],
            )
            summary.update({key: invalid[key] for key in summary if key != "receipt"})
            summary.update(outcome="invalid", problems=invalid["problems"])
        print(canonical(summary))
        # The wrapper reports the command's own status; success is never implied.
        return 0 if receipt["execution"]["succeeded"] else 1
    expected = strict_loads(args.expect) if args.expect else None
    result = validate(args.receipt, expected, declared_sha256=args.sha256)
    print(canonical(result))
    return 0 if result["outcome"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
