"""Structured execution receipts: attributed local evidence of one command run.

A receipt is derived from repository and process observations made by this
module around a command it executed itself. It is not Saga verification,
canonical acceptance or required review, and it does not prove that the host
was uncompromised or unshared. Its trust limits are documented in
docs/DEVELOPMENT-LOOP.md ("Execution receipts").

Privacy scope: the receipt records argv verbatim, the resolved executable,
repository identity (branch, commit, diff digests, bounded path lists) and the
command's stdout/stderr as retained artifacts. It never records environment
variables, credential files, ignored files or file contents of the worktree.
"""

from __future__ import annotations

import hashlib
import os
import shutil
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
MAX_LISTED_PATHS = 256
MAX_UNTRACKED_HASHED_BYTES = 8 * 1024 * 1024
GIT_TIMEOUT = 60
OUTCOMES = ("valid", "invalid", "missing", "mismatched")
EVIDENCE_STATUSES = (
    "validated",
    "invalid",
    "missing",
    "mismatched",
    "legacy_no_receipt",
)


class ReceiptError(ValueError):
    pass


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256_file(path, *, limit=MAX_ARTIFACT_HASH_BYTES):
    """Digest of a private regular file through one descriptor; None if unreadable."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None, None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            return None, info.st_size
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1 << 16):
            digest.update(chunk)
        return digest.hexdigest(), info.st_size
    except OSError:
        return None, None
    finally:
        os.close(fd)


def _git(root, *arguments, binary=False):
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        timeout=GIT_TIMEOUT,
        check=False,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LC_ALL": "C",
            "HOME": "/nonexistent",
        },
    )
    if completed.returncode != 0:
        raise ReceiptError(
            f"git {arguments[0]} failed: {completed.stderr.decode('utf-8', 'replace').strip()[:200]}"
        )
    return completed.stdout if binary else completed.stdout.decode("utf-8", "replace")


def _name_status(text):
    entries = []
    for line in text.splitlines():
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        entries.append({"status": status.strip(), "path": path})
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
        root = Path(_git(path, "rev-parse", "--show-toplevel").strip()).resolve()
        head = _git(root, "rev-parse", "HEAD").strip()
        subject = _git(root, "log", "-1", "--format=%s", "HEAD").rstrip("\n")
        symbolic = subprocess.run(
            ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=False,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LC_ALL": "C",
                "HOME": "/nonexistent",
            },
        )
        branch = symbolic.stdout.strip() if symbolic.returncode == 0 else None
        staged_raw = _git(
            root, "diff", "--cached", "--binary", "--no-ext-diff", "HEAD", binary=True
        )
        unstaged_raw = _git(root, "diff", "--binary", "--no-ext-diff", binary=True)
        staged = _name_status(_git(root, "diff", "--cached", "--name-status", "HEAD"))
        unstaged = _name_status(_git(root, "diff", "--name-status"))
        untracked_all = [
            line
            for line in _git(
                root, "ls-files", "--others", "--exclude-standard"
            ).splitlines()
            if line
        ]
    except (ReceiptError, OSError, subprocess.TimeoutExpired, ValueError) as error:
        return {
            "observed": False,
            "reason": f"{type(error).__name__}: {error}"[:300],
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
        "head_subject": subject[:200],
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


def _collector():
    """Identity of the code that produced the receipt."""
    source = Path(__file__).resolve()
    source_digest, _ = _sha256_file(source)
    try:
        odin_revision = _git(ROOT, "rev-parse", "HEAD").strip()
        dirty = bool(
            _git(ROOT, "status", "--porcelain", "--untracked-files=no").strip()
        )
    except (ReceiptError, OSError, subprocess.TimeoutExpired):
        odin_revision, dirty = None, None
    return {
        "module": "odin.execution_receipt",
        "schema_version": SCHEMA_VERSION,
        "source_sha256": source_digest,
        "odin_root": str(ROOT),
        "odin_revision": odin_revision,
        "odin_tracked_files_modified": dirty,
    }


def _resolve_executable(argv, cwd):
    program = argv[0]
    candidate = Path(program)
    if "/" in program:
        resolved = (Path(cwd) / candidate).resolve()
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
            )
            interpreter = {
                "path": found,
                "version": (version.stdout or version.stderr).strip()[:120] or None,
            }
        except (OSError, subprocess.TimeoutExpired):
            interpreter = {"path": found, "version": None}
    return found, interpreter


def _private_directory(path):
    path = Path(path).absolute()
    if path == ROOT or ROOT in path.parents:
        raise PermissionError("receipts must be retained outside the repository")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise PermissionError(
            "receipt directory must be private and owned by this user"
        )
    return path


def _write_private(path, data):
    temporary = path.with_name(path.name + "." + identifier() + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def run(
    argv, *, out, cwd=None, repository=None, binding=None, label=None, timeout=3600
):
    """Execute ``argv`` and derive a receipt from observations; never from claims.

    ``out`` is a private directory outside the repository that receives
    ``stdout.log``, ``stderr.log`` and ``receipt.json``. ``binding`` may carry
    ``loop_id``, ``stage_id``, ``run_id`` and ``session_id``; it identifies the
    development stage the receipt is evidence for. The wrapper's own result is
    the receipt; a nonzero command exit is recorded, not raised.
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
    with (
        os.fdopen(
            os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb"
        ) as stdout,
        os.fdopen(
            os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb"
        ) as stderr,
    ):
        try:
            process = subprocess.Popen(
                argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr
            )
        except OSError as error:
            uncertainty = f"spawn failed: {type(error).__name__}: {error}"[:300]
        else:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
                uncertainty = (
                    f"command exceeded {timeout} s and was killed; outcome unknown"
                )
            if process.returncode is not None and process.returncode < 0:
                signal_number = -process.returncode
                if uncertainty is None:
                    uncertainty = f"command terminated by signal {signal_number}"
            elif process.returncode is not None:
                exit_status = process.returncode
    finished_at = _now()
    after = observe_repository(repository)
    artifacts = []
    for name, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        file_digest, size = _sha256_file(path)
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
            "duration_seconds": round(time.monotonic() - started_monotonic, 3),
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
            "attribution": "local; same uid as the collector; no independent witness",
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
    file_digest, _size = _sha256_file(path, limit=MAX_RECEIPT_BYTES)
    if file_digest is None:
        raise ReceiptError("receipt file is missing, not private, or too large")
    return {
        "kind": "execution_receipt",
        "path": str(path.resolve()),
        "sha256": file_digest,
    }


def validate(path, expected=None, *, declared_sha256=None):
    """Deterministic validation of one receipt file; outcome is never a claim.

    Outcomes: ``missing`` (receipt or a referenced artifact absent), ``invalid``
    (unreadable, non-private, schema violation), ``mismatched`` (artifact bytes,
    declared receipt digest or any ``expected`` identity differs), ``valid``.
    ``expected`` may contain ``root``, ``head``, ``branch``, ``detached``,
    ``clean``, ``exit_status``, ``succeeded``, ``loop_id``, ``stage_id``.
    """
    path = Path(path)
    problems, checks = [], []
    try:
        info = path.lstat()
    except OSError:
        return {
            "outcome": "missing",
            "path": str(path),
            "problems": ["receipt file missing"],
            "checks": [],
        }
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        return {
            "outcome": "invalid",
            "path": str(path),
            "problems": ["receipt must be a private regular file owned by this user"],
            "checks": [],
        }
    if info.st_size > MAX_RECEIPT_BYTES:
        return {
            "outcome": "invalid",
            "path": str(path),
            "problems": ["receipt exceeds size limit"],
            "checks": [],
        }
    actual_digest, _ = _sha256_file(path, limit=MAX_RECEIPT_BYTES)
    try:
        receipt = strict_loads(path.read_text())
        Contracts().validate(SCHEMA, receipt)
    except Exception as error:  # noqa: BLE001 - every parse/schema failure is "invalid"
        return {
            "outcome": "invalid",
            "path": str(path),
            "problems": [f"{type(error).__name__}: {str(error).splitlines()[0][:200]}"],
            "checks": [],
        }
    checks.append("schema")
    if declared_sha256 is not None:
        if declared_sha256 != actual_digest:
            problems.append("receipt bytes differ from the declared reference digest")
        checks.append("reference_digest")
    missing = False
    for artifact in receipt["artifacts"]:
        current, size = _sha256_file(artifact["path"])
        if current is None:
            if not Path(artifact["path"]).exists():
                problems.append(f"artifact missing: {artifact['name']}")
                missing = True
            else:
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
                f"expected {key}={value!r} but receipt records {observed!r}"
            )
    if expected:
        checks.append("expected_identity")
    if receipt["repository"].get("changed_during_run"):
        checks.append("worktree_changed_during_run")
    outcome = "valid" if not problems else ("missing" if missing else "mismatched")
    return {
        "outcome": outcome,
        "path": str(path),
        "sha256": actual_digest,
        "receipt_id": receipt["receipt_id"],
        "binding": receipt["binding"],
        "head": before.get("head") if before.get("observed") else None,
        "branch": before.get("branch") if before.get("observed") else None,
        "detached": before.get("detached") if before.get("observed") else None,
        "clean": before.get("clean") if before.get("observed") else None,
        "worktree_identity": before.get("worktree_identity")
        if before.get("observed")
        else None,
        "exit_status": execution["exit_status"],
        "succeeded": execution["succeeded"],
        "uncertainty": execution["uncertainty"],
        "changed_during_run": receipt["repository"].get("changed_during_run"),
        "problems": problems,
        "checks": checks,
    }


def validate_references(evidence, *, expected=None, claims_key="claims"):
    """Validate every receipt reference in an evidence object; legacy is distinct.

    ``evidence["receipts"]`` is the typed list of references. Absent means
    ``legacy_no_receipt``: the evidence predates receipts or offers none; it is
    not validated and not a failure. ``evidence[claims_key]`` (optional object)
    holds structured claims about the run (``head``, ``branch``, ``detached``,
    ``clean``, ``exit_status``, ``succeeded``) that are compared against every
    receipt; any disagreement is ``mismatched``.
    """
    if not isinstance(evidence, dict) or "receipts" not in evidence:
        return {"status": "legacy_no_receipt", "receipts": [], "problems": []}
    contracts = Contracts()
    references = evidence["receipts"]
    try:
        contracts.validate_definition(SCHEMA, "references", references)
    except Exception as error:  # noqa: BLE001 - malformed references are reportable, not fatal
        return {
            "status": "invalid",
            "receipts": [],
            "problems": [
                f"receipt references malformed: {str(error).splitlines()[0][:200]}"
            ],
        }
    claims = evidence.get(claims_key)
    if claims is not None and not isinstance(claims, dict):
        return {
            "status": "invalid",
            "receipts": [],
            "problems": ["claims must be an object"],
        }
    merged = dict(expected or {})
    for key in ("head", "branch", "detached", "clean", "exit_status", "succeeded"):
        if claims and key in claims:
            merged[key] = claims[key]
    results = [
        validate(item["path"], merged or None, declared_sha256=item["sha256"])
        for item in references
    ]
    outcomes = {result["outcome"] for result in results}
    if not results:
        status = "missing"
    elif outcomes == {"valid"}:
        status = "validated"
    elif "invalid" in outcomes:
        status = "invalid"
    elif "missing" in outcomes:
        status = "missing"
    else:
        status = "mismatched"
    problems = [
        f"{result['path']}: {problem}"
        for result in results
        for problem in result["problems"]
    ]
    if not results:
        problems.append("receipts list is empty")
    return {
        "status": status,
        "receipts": [
            {
                key: result.get(key)
                for key in (
                    "outcome",
                    "path",
                    "sha256",
                    "receipt_id",
                    "binding",
                    "head",
                    "branch",
                    "detached",
                    "clean",
                    "exit_status",
                    "succeeded",
                    "uncertainty",
                    "changed_during_run",
                    "problems",
                )
            }
            for result in results
        ],
        "problems": problems,
    }


def main(argv=None):
    """``receipt-run`` and ``receipt-validate`` entry points used by ``odin``."""
    import argparse

    parser = argparse.ArgumentParser(prog="odin receipt")
    sub = parser.add_subparsers(dest="action", required=True)
    runner = sub.add_parser("run", help="execute a command and retain its receipt")
    runner.add_argument(
        "--out", required=True, help="private directory outside the repository"
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
        summary = {
            "receipt": reference(Path(args.out) / RECEIPT_NAME),
            "exit_status": receipt["execution"]["exit_status"],
            "succeeded": receipt["execution"]["succeeded"],
            "uncertainty": receipt["execution"]["uncertainty"],
            "head": receipt["repository"]["before"].get("head"),
            "branch": receipt["repository"]["before"].get("branch"),
            "detached": receipt["repository"]["before"].get("detached"),
            "clean": receipt["repository"]["before"].get("clean"),
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
