"""Explicit bounded native usage collection through the service command path."""
from pathlib import Path
from datetime import datetime, timezone
import os
import stat

from .contracts import Contracts, canonical, identifier, strict_loads
from .development_loop import _ulid_from_digest
from .usage import normalize_claude_status, usage_from_claude_jsonl, usage_from_codex_jsonl


def _json_file(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("regular JSON source required")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > limit or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("JSON source exceeded bound or changed during read")
    return strict_loads(raw), datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


def run(args, address, send, parser):
    action = args.action.replace("-", "_")
    payloads = []
    if action == "usage_collect":
        if not all((args.project, args.source_file, args.native_session, args.usage_provider)):
            parser.error("usage-collect requires --project, --source-file, --native-session and --usage-provider")
        if args.usage_provider == "claude-status":
            # Status-line input is intentionally a separate snapshot, never a request.
            status, sampled_at = _json_file(args.source_file, 65536)
            sample = normalize_claude_status(status, project_id=args.project,
                session_id=args.native_session, agent_id=args.agent_id, account_id=args.account_id,
                observed_at=sampled_at)
            collected = {"observations": [sample]}
        else:
            collector = usage_from_claude_jsonl if args.usage_provider == "claude" else usage_from_codex_jsonl
            collected = collector(args.source_file, project_id=args.project,
                session_id=args.native_session, agent_id=args.agent_id,
                loop_id=args.loop, stage_id=args.stage, max_bytes=args.max_bytes,
                **({"usage_semantics": args.usage_semantics} if args.usage_provider == "codex" else {}))
        items = collected["observations"]
        for index in range(0, max(1, len(items)), 128):
            payload = {"project": args.project, "source_id": str(Path(args.source_file).absolute()),
                       "observations": items[index:index + 128]}
            if "coverage" in collected and index + 128 >= len(items):
                payload["coverage"] = collected["coverage"]
            payloads.append(payload)
        action = "usage_import"
    elif action in {"usage_import", "usage_configure", "context_checkpoint"}:
        if not args.request:
            parser.error(args.action + " requires --request payload JSON")
        payload, _ = _json_file(args.request, 480000)
        payloads = [payload]
    else:
        if not args.project:
            parser.error(args.action + " requires --project")
        payload = {"project": args.project}
        if action == "usage_status":
            payload.update({k: v for k, v in {"loop_id": args.loop, "stage_id": args.stage, "session_id": args.native_session}.items() if v})
        elif args.native_session:
            payload["session_id"] = args.native_session
        payloads = [payload]
    for index, payload in enumerate(payloads):
        Contracts().validate_definition("usage-command", action, payload)
        operation = args.operation_id or identifier()
        if len(payloads) > 1:
            operation = _ulid_from_digest({"operation": args.operation_id or payloads, "batch": index})
        command = {"schema_version": 1, "operation_id": operation, "action": action, "payload": payload}
        try:
            response = send(address, {"surface": "terminal", "command": command})
        except (OSError, ValueError):
            parser.exit(2, "odin: usage command outcome unavailable; reconcile status or retry the exact payload with --operation-id " + operation + "\n")
        print(canonical(response))
        if "error" in response:
            return 1
    return 0
