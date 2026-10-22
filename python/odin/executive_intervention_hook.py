"""Fail-closed native hook; no tool input, command text or result is logged.

A call is admitted on one of three paths: a read-only Bash diagnostic or an
operator-registered script, both decided locally without the service, or an
exact Odin permit. Write/Edit inside a configured memory directory are also
admitted locally. Every other call is refused.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from .contracts import ROOT, canonical, identifier, strict_loads
from .executive_mcp import SocketGateway, ToolFailure
from .contracts import Contracts
from .executive_admission import (audit, read_only, registered_interpreter, registered_script,
                                  registered_scripts)
from .executive_intervention import TOOLS, _live, normalized
from .store import digest

MEMORY_FILE = "memory-directory.json"
CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")
REFUSAL = (
    "Odin executive mode: this call matched none of the three admission paths. "
    "(1) Read-only diagnostics, admitted without a permit: one foreground Bash command, "
    "or a | pipe of them, from the allowlist (git read subcommands such as status/log/diff/show, "
    "ls, cat, head, tail, wc, stat, du, df, find without -exec/-delete, grep/rg without --pre, "
    "jq, sort, uniq, cut, ps, pgrep, date, id, which, pwd, systemctl --user status/show/cat, "
    "journalctl --user without -f, and the pilot launcher's status actions); no ; & ` $( < > "
    "or newlines anywhere, and no unquoted globs, braces or $. "
    "(2) An operator-registered script (never an interpreter), called by its absolute path, with plain arguments and "
    "optional redirections to absolute paths or 2>&1; background is allowed. "
    "(3) An exact permit from odin_intervention_begin (up to 32 calls, 3600 s, optional uses and "
    "background), only while delegated work is idle. Write/Edit inside the configured memory "
    "directory need no permit. Otherwise delegate implementation. If an admitted call is "
    "uncertain, inspect odin_intervention_status; do not retry blindly."
)
REASONS = {"read_only": "Read-only diagnostic allowlist.",
           "registered_script": "Operator-registered script with matching SHA-256.",
           "memory_directory": "Configured executive memory directory."}


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
    # Read-only git must never find a configuration the executive wrote.
    if any(part.lower() == ".git" for part in target.parts):
        return False
    if any(os.path.islink(part) for part in (target, *target.parents)):
        return False
    if target.exists() and not target.is_file():
        return False
    parent = Path(os.path.realpath(target.parent))
    real = Path(os.path.realpath(directory))
    inside = Path(os.path.realpath(target))
    return (target.parent.is_dir() and parent.is_relative_to(real) and
            inside != real and inside.is_relative_to(real))


def _memory_root(memory, state):
    try:
        return os.path.realpath(memory_directory(memory, state=state)) if memory is not None else None
    except ValueError:
        return None


def local_path(tool, inputs, *, state, cwd=None, memory=None, scripts=None):
    """Admission path decided without the service, or None."""
    if tool == "Bash":
        if read_only(inputs, state=state, cwd=cwd, memory=_memory_root(memory, state)):
            return "read_only"
        if registered_script(inputs, scripts=scripts, state=state):
            return "registered_script"
        return None
    if _memory_write(tool, inputs, memory=memory, state=state):
        return "memory_directory"
    return None


def handle(event, *, state, project, session, gateway=None, memory=None, scripts=None):
    if (not isinstance(event, dict) or event.get("session_id") != session or
        event.get("tool_name") not in TOOLS or
        event.get("hook_event_name") not in {"PreToolUse", "PostToolUse", "PostToolUseFailure"} or
        not isinstance(event.get("tool_use_id"), str) or not event["tool_use_id"] or
        not isinstance(event.get("cwd"), str) or
        not isinstance(event.get("tool_input"), dict)):
        raise ValueError("invalid_intervention_hook")
    pre = event["hook_event_name"] == "PreToolUse"
    kind = local_path(event["tool_name"], event["tool_input"], state=state, cwd=event["cwd"],
                      memory=memory, scripts=scripts)
    if kind is not None:
        # Local paths never call the service, so a stopped service can be diagnosed.
        if pre:
            audit(state, kind, event["tool_name"], event["tool_input"])
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                    "permissionDecision": "allow", "permissionDecisionReason": REASONS[kind]}}
        return {}
    wanted = digest(normalized(event["tool_name"], event["tool_input"]))
    operation = identifier()
    try:
        response = (gateway or SocketGateway(state, timeout=3))({
            "schema_version": 1, "operation_id": operation,
            "action": "intervention_authorize" if pre else "intervention_finish",
            "payload": {"project": project, "session_id": session,
                        "cwd": event["cwd"], "tool_use_id": event["tool_use_id"],
                        "tool": event["tool_name"], "input": event["tool_input"]}})
    except ToolFailure as error:
        raise ValueError("intervention_service_unreachable" if str(error) == "Executive service unavailable."
                         else "intervention_service_response_invalid") from None
    if not isinstance(response, dict):
        raise ValueError("intervention_service_response_invalid")
    if "error" in response:
        # The service answered and refused: relay its fixed code, never its text.
        if event["tool_name"] == "Bash" and registered_interpreter(event["tool_input"], scripts=scripts):
            raise ValueError("script_is_interpreter")
        detail = response.get("detail")
        raise ValueError(detail if isinstance(detail, str) and CODE.fullmatch(detail)
                         else "intervention_not_admitted")
    Contracts().validate("gateway-receipt", response)
    if response["operation_id"] != operation:
        raise ValueError("intervention_receipt_identity_mismatch")
    result = response["result"]
    item = result.get("intervention") if isinstance(result, dict) else None
    if not isinstance(item, dict):
        raise ValueError("intervention_permit_not_confirmed")
    Contracts().validate("executive-intervention", item)
    # A background permit is closed at launch, so both events confirm "launched".
    matches = [permit for permit in item["permits"]
               if permit["tool_use_id"] == event["tool_use_id"] and
               permit["tool"] == event["tool_name"] and
               permit["input_digest"] == wanted and
               permit["state"] == ("launched" if permit.get("background") else
                                   "admitted" if pre else "finished")]
    if item["project"] != project or item["session_id"] != session or len(matches) != 1:
        raise ValueError("intervention_permit_not_confirmed")
    if pre:
        # Launching the last background permit closes the window in the same
        # admission, so that response confirms an unexpired, closed window.
        unexpired = datetime.fromisoformat(item["expires_at"]) > datetime.now(timezone.utc)
        live = _live(item) and result.get("mode") == "intervention"
        if not unexpired or not (live or (matches[0].get("background") and item["state"] == "closed")):
            raise ValueError("intervention_permit_not_confirmed")
    if pre:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "allow", "permissionDecisionReason": "Recorded single-use Odin intervention permit."}}
    return {}


def refusal(error):
    """The fixed refusal text, plus the error code when it is a bare code."""
    code = str(error)
    return REFUSAL + (f" Code: {code}." if CODE.fullmatch(code) else "")


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
                        memory=configured_memory(args.state), scripts=registered_scripts(args.state))
        print(canonical(output))
        return 0
    except Exception as error:
        print(refusal(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
