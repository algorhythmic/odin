"""Detached one-turn runner for a local delegation session.

The service spawns this process with a spool directory containing `spec.json`.
It executes exactly one harness turn, forwards interrupt signals, enforces the
wall-clock limit and writes `result.json` atomically. It never opens Odin's
store: the service ingests the spool. Standard library only.
"""

import json
import os
import signal
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
        )
        _write_json(
            directory / "started.json",
            {
                "schema_version": 1,
                "runner_pid": os.getpid(),
                "harness_pid": process.pid,
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
        "permission_denials": parsed.get("permission_denials"),
        "parse_error": parsed.get("parse_error"),
        "error_summary": ("; ".join(parsed["errors"])[:2048] or None)
        if parsed.get("errors")
        else None,
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
