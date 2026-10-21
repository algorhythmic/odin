"""Opt-in, metadata-only Claude Code status line capture for one native session.

The output is a private, native-shaped snapshot. Its mtime is the last changed
observation, not a heartbeat: unchanged rerenders do not refresh its age.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import stat
import sys
import uuid
from pathlib import Path

from jsonschema.exceptions import ValidationError

from .contracts import Contracts, canonical, strict_loads

MAX_INPUT_BYTES = 65536
MAX_COUNTER = 9007199254740991
PROJECT_ID = re.compile(r"[0-7][0-9A-HJKMNP-TV-Z]{25}\Z")


def _object(value, name):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"invalid {name}")
    return value


def _count(value):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise ValueError("invalid status counter")
    return value


def _percentage(value):
    if value is None:
        return None
    if type(value) not in (int, float) or not 0 <= value <= 100:
        raise ValueError("invalid status percentage")
    return value


def sanitize(native, *, session_id, project):
    """Return only context and quota fields for the requested native UUID."""
    if not isinstance(native, dict):
        raise ValueError("status input must be an object")
    if not isinstance(project, str) or not PROJECT_ID.fullmatch(project):
        raise ValueError("invalid project")
    if not isinstance(session_id, str) or str(uuid.UUID(session_id)) != session_id:
        raise ValueError("invalid native session ID")
    if native.get("session_id") != session_id:
        return None
    context = _object(native.get("context_window"), "context window")
    raw_usage = context.get("current_usage")
    usage = None
    if raw_usage is not None:
        source = _object(raw_usage, "current usage")
        usage = {key: _count(source.get(key)) for key in
                 ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
    rates = _object(native.get("rate_limits"), "rate limits")
    windows = {}
    for name in ("five_hour", "seven_day"):
        source = _object(rates.get(name), name)
        windows[name] = {"used_percentage": _percentage(source.get("used_percentage")),
                         "resets_at": _count(source.get("resets_at"))}
    snapshot = {"session_id": session_id,
                "context_window": {"context_window_size": _count(context.get("context_window_size")),
                                   "current_usage": usage},
                "rate_limits": windows}
    Contracts().validate("usage-statusline-snapshot", snapshot)
    return snapshot


def _private_directory(path):
    directory = path.parent
    if not directory.is_absolute() or not path.is_absolute():
        raise ValueError("output path must be absolute")
    if not directory.exists():
        directory.mkdir(mode=0o700)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or
            stat.S_IMODE(info.st_mode) != 0o700 or directory.resolve() != directory):
        raise ValueError("output directory must be private and non-symlinked")
    return directory


def _existing(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > MAX_INPUT_BYTES):
            raise ValueError("existing output is not a private bounded file")
        return os.read(fd, MAX_INPUT_BYTES + 1)
    finally:
        os.close(fd)


def write_snapshot(output, snapshot):
    path = Path(output)
    directory = _private_directory(path)
    data = (canonical(snapshot) + "\n").encode("utf-8")
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("status snapshot exceeds bound")
    if _existing(path) == data:
        return False
    temporary = directory / ("." + path.name + "." + secrets.token_hex(8) + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck the target before replacing it; never accept a foreign or
        # broadly readable file that appeared after the first inspection.
        _existing(path)
        os.replace(temporary, path)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def status_text(snapshot):
    context = snapshot["context_window"]
    usage = context["current_usage"]
    parts = []
    if usage is not None and all(usage[key] is not None for key in usage):
        parts.append("context " + str(sum(usage.values())) + "/" +
                     (str(context["context_window_size"]) if context["context_window_size"] is not None else "--"))
    else:
        parts.append("context --")
    for name, label in (("five_hour", "5h"), ("seven_day", "7d")):
        value = snapshot["rate_limits"][name]["used_percentage"]
        parts.append(label + " " + (f"{value:g}%" if value is not None else "--"))
    return "Odin " + " | ".join(parts)


def main(argv=None, *, stdin=None, stdout=None, stderr=None):
    parser = argparse.ArgumentParser(description="Capture one private Claude status-line sample")
    parser.add_argument("--output", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args(argv)
    source = stdin or sys.stdin.buffer
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    try:
        raw = source.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("status input exceeds bound")
        snapshot = sanitize(strict_loads(raw.decode("utf-8")),
                            session_id=args.session_id, project=args.project)
        if snapshot is None:
            print("Odin status unavailable", file=output_stream)
            return 0
        write_snapshot(args.output, snapshot)
        print(status_text(snapshot), file=output_stream)
        return 0
    except (OSError, UnicodeError, ValueError, ValidationError) as error:
        print("Odin status capture unavailable: " + type(error).__name__, file=error_stream)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
