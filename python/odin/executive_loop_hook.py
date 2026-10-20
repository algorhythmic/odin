"""Capture native executive completion without starting another model process.

The hook writes a private, durable command before attempting service delivery.
Its deterministic operation ID survives retries and service outages. Only a
matching receipt removes the spool entry; a successful stop is not verification.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
import time
import uuid
from pathlib import Path

from jsonschema import ValidationError

from .contracts import ALPHABET, ROOT, Contracts, canonical, strict_loads
from .executive_mcp import PROJECT_ID, SocketGateway, ToolFailure

MAX_HOOK_BYTES = 1024 * 1024
MAX_CAPTURE_BYTES = 1024 * 1024
MAX_FINAL_BYTES = 262144
SPOOL_NAME = "executive-loop-spool"
CAPTURE_SCHEMA = "executive-pilot-loop-capture"
HOOK_EVENTS = frozenset({"Stop", "StopFailure"})
OPTIONAL_FIELDS = (
    "prompt_id",
    "last_assistant_message",
    "background_tasks",
    "session_crons",
    "stop_hook_active",
    "error",
    "error_details",
)


def _private_directory(path, *, create=False):
    path = Path(path).absolute()
    if path != path.resolve() or path == ROOT or ROOT in path.parents:
        raise PermissionError("loop spool must be outside the repository")
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("loop spool must be private and owned by this user")
    return path


def _read_capture(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError("loop capture must be a private regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_CAPTURE_BYTES + 1)
    if len(raw) > MAX_CAPTURE_BYTES:
        raise ValueError("loop capture exceeds the transport budget")
    command = strict_loads(raw.decode("utf-8"))
    Contracts().validate(CAPTURE_SCHEMA, command)
    if command["operation_id"] != _operation_id(command["payload"]):
        raise ValueError("loop capture identity mismatch")
    return command


def _operation_id(payload):
    value = int.from_bytes(
        hashlib.sha256(("odin-loop-capture-v1:" + canonical(payload)).encode()).digest()[:16],
        "big",
    )
    result = ""
    for _ in range(26):
        result = ALPHABET[value & 31] + result
        value >>= 5
    return result


def capture_command(event, *, project, session_id):
    """Normalize known fields, ignoring forward-compatible native hook fields."""
    if not isinstance(event, dict):
        raise ValueError("hook event must be an object")
    if event.get("hook_event_name") not in HOOK_EVENTS or event.get("agent_id"):
        return None
    if not PROJECT_ID.fullmatch(project) or str(uuid.UUID(session_id)) != session_id:
        raise ValueError("invalid launch binding")
    if event.get("session_id") != session_id:
        raise PermissionError("hook session differs from the launch binding")
    payload = {
        "project": project,
        "session_id": session_id,
        "hook_event_name": event["hook_event_name"],
    }
    payload.update({key: event[key] for key in OPTIONAL_FIELDS if key in event})
    final_text = payload.get("last_assistant_message", "")
    if isinstance(final_text, str) and len(final_text.encode()) > MAX_FINAL_BYTES:
        raise ValueError("final response exceeds the capture budget")
    command = {
        "schema_version": 1,
        "operation_id": _operation_id(payload),
        "action": "loop_capture",
        "payload": payload,
    }
    Contracts().validate(CAPTURE_SCHEMA, command)
    # The actual gateway envelope adds bytes. Never truncate the final response.
    if len((canonical({"command": command}) + "\n").encode()) > MAX_CAPTURE_BYTES:
        raise ValueError("hook capture exceeds the transport budget")
    return command


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def spool_capture(state, command):
    """Atomically retain one immutable command, even across uncertain delivery."""
    Contracts().validate(CAPTURE_SCHEMA, command)
    if command["operation_id"] != _operation_id(command["payload"]):
        raise ValueError("loop capture identity mismatch")
    state = _private_directory(state)
    directory = _private_directory(state / SPOOL_NAME, create=True)
    _sync_directory(state)
    path = directory / (command["operation_id"] + ".json")
    temporary = directory / ("." + str(uuid.uuid4()) + ".tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write((canonical(command) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Atomic no-replace publication makes concurrent identical callbacks
            # harmless without overwriting an older uncertain result.
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            if _read_capture(path) != command:
                raise ValueError("loop capture operation conflict") from None
        _sync_directory(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def deliver_capture(path, gateway):
    try:
        command = _read_capture(path)
    except FileNotFoundError:
        # Another service/hook drain may have reconciled this same operation.
        return False
    try:
        receipt = gateway(command)
        Contracts().validate("gateway-receipt", receipt)
        if receipt["operation_id"] != command["operation_id"]:
            return False
    except (ToolFailure, OSError, ValueError, ValidationError):
        return False
    path.unlink(missing_ok=True)
    _sync_directory(path.parent)
    return True


def drain_spool(state, submit=None, *, limit=16, project=None):
    """Replay bounded pending commands; caller may supply an in-process gateway."""
    if type(limit) is not int or not 1 <= limit <= 128:
        raise ValueError("invalid loop spool drain bound")
    state = _private_directory(state)
    directory = state / SPOOL_NAME
    if not directory.exists():
        return {"delivered": 0, "pending": 0, "invalid": 0}
    directory = _private_directory(directory)
    gateway = submit or SocketGateway(state, timeout=2, max_request_bytes=MAX_CAPTURE_BYTES)
    delivered = invalid = 0
    # Retry order is persisted in metadata, never in the immutable command.
    # A permanently invalid/refused item must not starve later completions.
    candidates = []
    for path in directory.glob("*.json"):
        try:
            candidates.append((path.lstat().st_mtime_ns, path.name, path))
        except FileNotFoundError:
            continue
    paths = [item[2] for item in sorted(candidates)]
    retry_stamp = max(time.time_ns(), max((item[0] for item in candidates), default=0)) + 1
    for path in paths[:limit]:
        accepted = False
        try:
            if project is not None and _read_capture(path)["payload"]["project"] != project:
                continue
            accepted = bool(deliver_capture(path, gateway))
            delivered += accepted
        except (ValueError, PermissionError, ValidationError):
            invalid += 1
        except FileNotFoundError:
            pass
        finally:
            if not accepted:
                try:
                    # Do not follow even a corrupt symlink spool entry.
                    os.utime(path, ns=(retry_stamp, retry_stamp), follow_symlinks=False)
                    retry_stamp += 1
                except OSError:
                    pass
    return {"delivered": delivered, "pending": len(paths) - delivered, "invalid": invalid}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(MAX_HOOK_BYTES + 1)
        if len(raw) > MAX_HOOK_BYTES:
            raise ValueError("native hook input exceeds the capture budget")
        event = strict_loads(raw.decode("utf-8"))
        command = capture_command(event, project=args.project, session_id=args.session_id)
        if command is not None:
            path = spool_capture(args.state, command)
            deliver_capture(
                path, SocketGateway(args.state, timeout=2, max_request_bytes=MAX_CAPTURE_BYTES)
            )
    except Exception:
        # Keep hook errors fixed and free of transcript, paths and credentials.
        print("Odin completion capture failed; inspect the local loop status.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
