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
import time
from datetime import UTC, datetime
from pathlib import Path

from .contracts import ROOT, Contracts, canonical, identifier, strict_loads

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
OUTCOMES = ("valid", "invalid", "missing", "mismatched")
EVIDENCE_STATUSES = (
    "validated",
    "validated_unobserved",
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
    "root",
    "cwd",
    "head",
    "branch",
    "detached",
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


def _sha256_file(path, *, limit=MAX_ARTIFACT_HASH_BYTES, private=False):
    """Digest of a regular file through one descriptor; (None, size) if refused.

    ``private`` additionally requires ownership by this user and no group or
    world permission bits, the rule for retained artifacts.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None, None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            return None, info.st_size
        if private and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            return None, info.st_size
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1 << 16):
            digest.update(chunk)
        return digest.hexdigest(), info.st_size
    except OSError:
        return None, None
    finally:
        os.close(fd)


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
    started_at, started_monotonic = _now(), time.monotonic()
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
            if process.returncode is not None and process.returncode < 0:
                signal_number = -process.returncode
                if uncertainty is None:
                    uncertainty = f"command terminated by signal {signal_number}"
            elif process.returncode is not None:
                exit_status = process.returncode
    duration = round(time.monotonic() - started_monotonic, 3)
    finished_at = _now()
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
            "concurrency": "observations are point-in-time; concurrent writers between "
            "before/after observations are detected only if the identity differs",
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
        "problems": [_clip(problem, MAX_PROBLEM_BYTES)],
        "checks": [],
    }


def validate(
    path, expected=None, *, declared_sha256=None, not_before=None, hash_budget=None
):
    """Deterministic validation of one receipt file; outcome is never a claim.

    Outcomes: ``missing`` (receipt or a referenced artifact absent), ``invalid``
    (unreadable, non-private, schema violation, budget exceeded), ``mismatched``
    (declared receipt digest, artifact bytes, any ``expected`` identity, a run
    that changed the worktree, or a receipt that predates ``not_before``
    differs), ``valid``. ``expected`` may contain ``root``, ``head``,
    ``branch``, ``detached``, ``clean``, ``exit_status``, ``succeeded``,
    ``loop_id``, ``stage_id``. A declared-digest mismatch is reported alone and
    the file's identity fields are not echoed. ``hash_budget`` is a mutable
    ``{"remaining": int}`` shared across receipts of one validation.
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
    if info.st_size > MAX_RECEIPT_BYTES:
        return _refused("invalid", path, "receipt exceeds size limit")
    actual_digest, _size = _sha256_file(path, limit=MAX_RECEIPT_BYTES, private=True)
    if actual_digest is None:
        return _refused("invalid", path, "receipt unreadable")
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
        receipt = strict_loads(path.read_bytes().decode("utf-8"))
        Contracts().validate(SCHEMA, receipt)
    except Exception as error:  # noqa: BLE001 - every parse/schema failure is "invalid"
        return _refused(
            "invalid", path, f"{type(error).__name__}: {str(error).splitlines()[0]}"
        )
    checks = ["schema"] + (["reference_digest"] if declared_sha256 is not None else [])
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
        if artifact_info.st_size > budget["remaining"]:
            problems.append(f"artifact hashing budget exceeded at: {artifact['name']}")
            return _finish(path, receipt, actual_digest, "invalid", problems, checks)
        budget["remaining"] -= artifact_info.st_size
        current, size = _sha256_file(artifact_path, private=True)
        if current is None:
            problems.append(f"artifact unreadable or too large: {artifact['name']}")
        elif current != artifact["sha256"] or size != artifact["bytes"]:
            problems.append(f"artifact bytes changed: {artifact['name']}")
    checks.append("artifacts")
    execution, before = receipt["execution"], receipt["repository"]["before"]
    for key, value in (expected or {}).items():
        if key in ("exit_status", "succeeded"):
            observed = execution[key]
        elif key in ("loop_id", "stage_id", "run_id", "session_id"):
            observed = receipt["binding"].get(key)
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
    if receipt["repository"].get("changed_during_run"):
        problems.append(
            "worktree changed during the run; the receipt does not describe the observed tree"
        )
        checks.append("worktree_changed_during_run")
    if not_before is not None:
        checks.append("not_before")
        if execution["started_at"] < not_before:
            problems.append(
                f"receipt started at {execution['started_at']} predates {not_before}"
            )
    outcome = "valid" if not problems else ("missing" if missing else "mismatched")
    return _finish(path, receipt, actual_digest, outcome, problems, checks)


def _finish(path, receipt, actual_digest, outcome, problems, checks):
    before = receipt["repository"]["before"]
    observed = bool(before.get("observed"))
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
        "observed": observed,
        "root": before.get("root") if observed else None,
        "cwd": receipt["command"]["cwd"],
        "head": before.get("head") if observed else None,
        "branch": before.get("branch") if observed else None,
        "detached": before.get("detached") if observed else None,
        "clean": before.get("clean") if observed else None,
        "worktree_identity": before.get("worktree_identity") if observed else None,
        "argv_head": _clip(" ".join(argv), 160),
        "argv_digest": hashlib.sha256(canonical(argv).encode()).hexdigest(),
        "started_at": receipt["execution"]["started_at"],
        "exit_status": receipt["execution"]["exit_status"],
        "succeeded": receipt["execution"]["succeeded"],
        "uncertainty": receipt["execution"]["uncertainty"],
        "changed_during_run": receipt["repository"].get("changed_during_run"),
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
    ``validated`` requires every receipt to be valid and to carry an observed
    repository; ``validated_unobserved`` means the files are consistent but no
    repository identity was observed. ``commands_succeeded`` is reported
    separately so a valid receipt of a failing command is never read as success.
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
    elif outcomes == {"valid"}:
        status = (
            "validated"
            if all(r["observed"] for r in results)
            else "validated_unobserved"
        )
    elif "invalid" in outcomes:
        status = "invalid"
    elif "missing" in outcomes:
        status = "missing"
    else:
        status = "mismatched"
    problems = [
        _clip(f"{result['path']}: {problem}", MAX_PROBLEM_BYTES)
        for result in results
        for problem in result["problems"]
    ]
    if not results:
        problems.append("receipts list is empty")
    return {
        "status": status,
        "receipts": [
            {key: result.get(key) for key in SUMMARY_KEYS} for result in results
        ],
        "problems": problems[:MAX_PROBLEMS],
        "commands_succeeded": all(r.get("succeeded") is True for r in results)
        if results
        else None,
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
            "observed": bool(before.get("observed")),
            "head": before.get("head"),
            "branch": before.get("branch"),
            "detached": before.get("detached"),
            "clean": before.get("clean"),
            "changed_during_run": receipt["repository"]["changed_during_run"],
        }
        print(canonical(summary))
        # The wrapper reports the command's own status; success is never implied.
        return 0 if receipt["execution"]["succeeded"] else 1
    expected = strict_loads(args.expect) if args.expect else None
    result = validate(args.receipt, expected, declared_sha256=args.sha256)
    print(canonical(result))
    return 0 if result["outcome"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
