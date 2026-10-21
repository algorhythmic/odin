"""Fail-closed native hook; no tool input, command text or result is logged."""
import argparse
import os
import sys
from pathlib import Path
from .contracts import ROOT, canonical, identifier, strict_loads
from .executive_mcp import SocketGateway
from .contracts import Contracts
from .executive_intervention import TOOLS, _live, normalized
from .store import digest

MEMORY_FILE = "memory-directory.json"


def _unsafe(value):
    return (not isinstance(value, str) or not os.path.isabs(value) or
            "\x00" in value or ".." in value.split("/"))


def memory_directory(value, *, state):
    """Validate a configured executive memory directory; raises ValueError."""
    if _unsafe(value):
        raise ValueError("memory_directory_invalid")
    path = Path(value)
    if any(os.path.islink(part) for part in (path, *path.parents)) or not path.is_dir():
        raise ValueError("memory_directory_invalid")
    real = Path(os.path.realpath(path))
    for other in (Path(os.path.realpath(ROOT)), Path(os.path.realpath(state))):
        if real == other or real.is_relative_to(other) or other.is_relative_to(real):
            raise ValueError("memory_directory_invalid")
    return path


def configured_memory(state):
    """Raw configured value, or None when absent or unreadable (no exception)."""
    path = Path(state) / "executive-pilot" / MEMORY_FILE
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return strict_loads(path.read_bytes()[:4097])["memory_directory"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _memory_write(tool, inputs, *, memory, state):
    """True only for Write/Edit whose real target lies strictly inside the configured directory."""
    if tool not in ("Write", "Edit") or memory is None:
        return False
    try:
        directory = memory_directory(memory, state=state)
    except ValueError:
        return False
    value = inputs.get("file_path")
    if _unsafe(value):
        return False
    target = Path(value)
    if any(os.path.islink(part) for part in (target, *target.parents)):
        return False
    if target.exists() and not target.is_file():
        return False
    parent = Path(os.path.realpath(target.parent))
    real = Path(os.path.realpath(directory))
    inside = Path(os.path.realpath(target))
    return (target.parent.is_dir() and parent.is_relative_to(real) and
            inside != real and inside.is_relative_to(real))


def handle(event, *, state, project, session, gateway=None, memory=None):
    if (not isinstance(event, dict) or event.get("session_id") != session or
        event.get("tool_name") not in TOOLS or
        event.get("hook_event_name") not in {"PreToolUse", "PostToolUse", "PostToolUseFailure"} or
        not isinstance(event.get("tool_use_id"), str) or not event["tool_use_id"] or
        not isinstance(event.get("cwd"), str) or
        not isinstance(event.get("tool_input"), dict)):
        raise ValueError("invalid_intervention_hook")
    pre = event["hook_event_name"] == "PreToolUse"
    if _memory_write(event["tool_name"], event["tool_input"], memory=memory, state=state):
        if pre:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                    "permissionDecision": "allow", "permissionDecisionReason": "Configured executive memory directory."}}
        return {}
    wanted = digest(normalized(event["tool_name"], event["tool_input"]))
    operation = identifier()
    response = (gateway or SocketGateway(state, timeout=3))({
        "schema_version": 1, "operation_id": operation,
        "action": "intervention_authorize" if pre else "intervention_finish",
        "payload": {"project": project, "session_id": session,
                    "cwd": event["cwd"], "tool_use_id": event["tool_use_id"],
                    "tool": event["tool_name"], "input": event["tool_input"]}})
    if not isinstance(response, dict) or "error" in response:
        raise ValueError("intervention_admission_unavailable")
    Contracts().validate("gateway-receipt", response)
    if response["operation_id"] != operation:
        raise ValueError("intervention_receipt_identity_mismatch")
    result = response["result"]
    item = result.get("intervention") if isinstance(result, dict) else None
    if not isinstance(item, dict):
        raise ValueError("intervention_permit_not_confirmed")
    Contracts().validate("executive-intervention", item)
    matches = [permit for permit in item["permits"]
               if permit["tool_use_id"] == event["tool_use_id"] and
               permit["tool"] == event["tool_name"] and
               permit["input_digest"] == wanted and
               permit["state"] == ("admitted" if pre else "finished")]
    if (item["project"] != project or item["session_id"] != session or
            len(matches) != 1 or (pre and (not _live(item) or result.get("mode") != "intervention"))):
        raise ValueError("intervention_permit_not_confirmed")
    if pre:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "allow", "permissionDecisionReason": "Recorded single-use Odin intervention permit."}}
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("hook_input_limit")
        output = handle(strict_loads(raw), state=args.state, project=args.project, session=args.session_id,
                        memory=configured_memory(args.state))
        print(canonical(output))
        return 0
    except Exception:
        print("Odin executive mode: delegate implementation, or use odin_intervention_begin for exact bounded tool calls after delegated work is idle. If an admitted call is uncertain, inspect odin_intervention_status; do not retry blindly.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
