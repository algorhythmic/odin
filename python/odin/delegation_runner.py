"""Detached one-turn runner for a local delegation session.

The service spawns this process with a spool directory containing `spec.json`.
It executes exactly one harness turn, forwards interrupt signals, enforces the
wall-clock limit and writes `result.json` atomically. It never opens Odin's
store: the service ingests the spool. Standard library only.
"""

import fcntl
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .delegation_output import parse_claude_json, parse_codex_jsonl, parse_codex_text

GRACE_SECONDS = 15
STDERR_TAIL = 4096


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_text(path, limit=None):
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if limit is not None:
        data = data[-limit:]
    return data.decode("utf-8", errors="replace")


FINGERPRINT_MAX_BYTES = 1 << 20


def _credential_fingerprint(path):
    """Metadata and digest of a credential file; never its contents.

    Reads through one descriptor (no symlinks, regular file, own uid, bounded
    size) so a worker cannot point the record at another file.
    """
    if not path:
        return None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_size > FINGERPRINT_MAX_BYTES
        ):
            return None
        digest = hashlib.sha256()
        while chunk := os.read(fd, 65536):
            digest.update(chunk)
    except OSError:
        return None
    finally:
        os.close(fd)
    return {
        "mtime_ns": info.st_mtime_ns,
        "size": info.st_size,
        "sha256": digest.hexdigest(),
    }


def _acquire_lineage(lineage):
    """Try to own the credential lineage lease (same lock the executive uses).

    "unavailable" means the lock file cannot be trusted (symlink, foreign
    owner, loose mode, replaced after locking); it is never treated as owned.
    """
    lock = (lineage or {}).get("lock")
    if not lock:
        return None, "not_applicable"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError:
        return None, "unavailable"
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None, "busy"
    except OSError:
        os.close(fd)
        return None, "unavailable"
    try:
        held = os.fstat(fd)
        current = os.stat(lock, follow_symlinks=False)
    except OSError:
        os.close(fd)
        return None, "unavailable"
    if (
        not stat.S_ISREG(held.st_mode)
        or held.st_uid != os.getuid()
        or held.st_mode & 0o077
        or (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)
    ):
        os.close(fd)
        return None, "unavailable"
    return fd, "acquired"


def _process_start(pid):
    """Linux process-start identity for orphan reconciliation, never PID alone."""
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def _refused_result(spec, started_at, lineage):
    return {
        "schema_version": 1,
        "turn": spec["turn"],
        "harness": spec["harness"],
        "exit_code": None,
        "started_at": started_at,
        "finished_at": _now(),
        "timed_out": False,
        "interrupted": False,
        "stdout_bytes": 0,
        "stderr_tail": "",
        "native_session_id": None,
        "final_text": "",
        "is_error": True,
        "stop_reason": None,
        "turns": None,
        "cost_usd": None,
        "usage": None,
        "usage_scope": None,
        "model_usage": None,
        "observed_model": None,
        "permission_denials": None,
        "parse_error": None,
        "error_summary": (
            "credential lineage lease is held by another owner; turn refused "
            "under lineage policy exclusive (no harness process started)"
            if lineage["lease"] == "busy"
            else "credential lineage lease file cannot be trusted (missing "
            "directory, symlink, foreign owner or loose mode); turn refused "
            "(no harness process started)"
        ),
        "lineage": lineage,
    }


def run(directory):
    directory = Path(directory)
    spec = json.loads((directory / "spec.json").read_text())
    stdout_path = directory / "stdout.log"
    stderr_path = directory / "stderr.log"
    result_path = directory / "result.json"
    if result_path.exists():
        return 0  # Idempotent: a finished turn is never executed twice.
    try:
        lock_fd = os.open(
            directory / "runner.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
    except FileExistsError:
        return 0  # Another runner already owns this turn; never run it twice.
    os.close(lock_fd)
    environment = os.environ | {str(k): str(v) for k, v in spec.get("env", {}).items()}
    started_at = _now()
    interrupted = {"value": False}
    timed_out = False
    process = None
    lineage_spec = spec.get("lineage") or {}
    lease_fd, lease = _acquire_lineage(lineage_spec)
    lineage = {
        "policy": lineage_spec.get("policy", "exclusive"),
        "shared_with": lineage_spec.get("shared_with"),
        "lease": lease,
        "refused": False,
        "credential_before": None,
        "credential_after": None,
        "credential_changed": None,
    }
    if lease == "unavailable" or (
        lease == "busy" and lineage["policy"] != "shared_accepted"
    ):
        # Accepted sharing can bypass contention, never an untrusted lease.
        # Nothing is read before this ownership check.
        lineage["refused"] = True
        _write_json(result_path, _refused_result(spec, started_at, lineage))
        return 0
    lineage["credential_before"] = _credential_fingerprint(
        lineage_spec.get("credential_file")
    )

    def forward(signum, _frame):
        interrupted["value"] = True
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass

    # Handlers before spawn: a stop that lands early still reaches the harness.
    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    with (
        os.fdopen(
            os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "ab"
        ) as stdout,
        os.fdopen(
            os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "ab"
        ) as stderr,
    ):
        process = subprocess.Popen(
            spec["argv"],
            cwd=spec["cwd"],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
            pass_fds=(lease_fd,) if lease_fd is not None else (),
        )
        _write_json(
            directory / "started.json",
            {
                "schema_version": 1,
                "runner_pid": os.getpid(),
                "harness_pid": process.pid,
                "harness_start": _process_start(process.pid),
                "started_at": started_at,
            },
        )

        if interrupted["value"]:
            forward(signal.SIGTERM, None)
        deadline = time.monotonic() + float(spec.get("timeout_seconds", 1800))
        grace_until = None
        while True:
            try:
                process.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                pass
            now = time.monotonic()
            if interrupted["value"] or now > deadline:
                if now > deadline and not interrupted["value"]:
                    timed_out = True
                    interrupted["value"] = True
                    try:
                        os.killpg(process.pid, signal.SIGINT)
                    except ProcessLookupError:
                        pass
                if grace_until is None:
                    grace_until = now + GRACE_SECONDS
                elif now > grace_until:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    break
    if lease_fd is not None:
        os.close(lease_fd)  # Releases the flock; held for the whole harness run.
    lineage["credential_after"] = _credential_fingerprint(
        lineage_spec.get("credential_file")
    )
    lineage["credential_changed"] = (
        lineage["credential_before"] != lineage["credential_after"]
        if lineage["credential_before"] is not None
        or lineage["credential_after"] is not None
        else None
    )
    exit_code = process.returncode
    stdout_text = _read_text(stdout_path)
    last_message = None
    if spec.get("last_message_file"):
        last_message = _read_text(Path(spec["last_message_file"])) or None
    harness = spec["harness"]
    if harness == "claude-code":
        parsed = parse_claude_json(stdout_text)
    elif spec.get("output_format") == "jsonl":
        parsed = parse_codex_jsonl(stdout_text, last_message)
    else:
        parsed = parse_codex_text(stdout_text, last_message)
    result = {
        "schema_version": 1,
        "turn": spec["turn"],
        "harness": harness,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": _now(),
        "timed_out": timed_out,
        "interrupted": interrupted["value"] and not timed_out,
        "stdout_bytes": len(stdout_text.encode("utf-8", errors="replace")),
        "stderr_tail": _read_text(stderr_path, STDERR_TAIL),
        "native_session_id": parsed.get("native_session_id"),
        "final_text": parsed.get("final_text", ""),
        "is_error": bool(parsed.get("is_error", False)) or exit_code != 0,
        "stop_reason": parsed.get("stop_reason"),
        "turns": parsed.get("turns"),
        "cost_usd": parsed.get("cost_usd"),
        "usage": parsed.get("usage"),
        "usage_scope": parsed.get("usage_scope"),
        "model_usage": parsed.get("model_usage"),
        "observed_model": parsed.get("observed_model"),
        "permission_denials": parsed.get("permission_denials"),
        "parse_error": parsed.get("parse_error"),
        "error_summary": ("; ".join(parsed["errors"])[:2048] or None)
        if parsed.get("errors")
        else None,
        "lineage": lineage,
    }
    _write_json(result_path, result)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m odin.delegation_runner TURN_DIRECTORY", file=sys.stderr)
        return 2
    return run(argv[0])


if __name__ == "__main__":
    sys.exit(main())
