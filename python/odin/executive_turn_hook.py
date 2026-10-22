"""Native turn markers for the executive supervisor (ODIN-ADR-039).

Claude Code runs this command hook on SessionStart, UserPromptSubmit, Stop,
StopFailure and SessionEnd when the executive was launched by
``executive-supervise``. It replaces one private marker file with the latest
event, the native session and a sequence number, and never blocks or prints a
decision: a marker it cannot write leaves the supervisor waiting, never
stopping. No prompt text, final response or tool input is retained.
"""
import argparse
import os
import stat
import sys
import uuid
from pathlib import Path

from .contracts import Contracts, canonical, strict_loads
from .store import now

MARKER_FILE = "turn-marker.json"
EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "StopFailure", "SessionEnd")
# Bounded labels copied from the native event; anything else is dropped.
LABEL_FIELDS = {"SessionStart": "source", "SessionEnd": "reason"}


def marker_path(state):
    return Path(state) / "executive-pilot" / MARKER_FILE


def read_marker(state):
    """The validated marker, or None when absent or unusable (no exception)."""
    path = marker_path(state)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            return None
        value = strict_loads(os.read(fd, 4097))
        Contracts().validate("executive-turn-marker", value)
        return value
    except Exception:  # noqa: BLE001 - an unusable marker is no idle evidence
        return None
    finally:
        os.close(fd)


def _count(value):
    if isinstance(value, list):
        return len(value)
    if type(value) is int and value >= 0:
        return value
    return None


def record(event, *, state, session):
    """Replace the marker with this event; raises on invalid input."""
    if not isinstance(event, dict) or event.get("hook_event_name") not in EVENTS:
        raise ValueError("turn_marker_event_invalid")
    if event.get("session_id") != session or str(uuid.UUID(session)) != session:
        raise ValueError("turn_marker_session_mismatch")
    if event.get("agent_id"):
        return None  # A subagent's stop is not the executive's turn end.
    previous = read_marker(state)
    name = event["hook_event_name"]
    label = event.get(LABEL_FIELDS.get(name, ""), None)
    marker = {
        "schema_version": 1, "session_id": session, "event": name, "at": now(),
        "sequence": (previous["sequence"] + 1) if previous and previous["session_id"] == session else 1,
        "label": label if isinstance(label, str) and len(label) <= 64 and label.isidentifier() else None,
        "background_tasks": _count(event.get("background_tasks")),
    }
    Contracts().validate("executive-turn-marker", marker)
    base = Path(state) / "executive-pilot"
    if base.is_symlink() or not base.is_dir():
        raise OSError("turn_marker_directory_unavailable")
    temporary = base / f".{MARKER_FILE}.{os.getpid()}"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, (canonical(marker) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, marker_path(state))
    return marker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(1048577)
        record(strict_loads(raw[:1048576]), state=args.state, session=args.session_id)
    except Exception as error:  # noqa: BLE001 - never block the native session
        print(f"odin turn marker not recorded: {type(error).__name__}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
