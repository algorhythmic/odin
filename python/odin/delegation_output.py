"""Parse non-interactive harness output into one bounded, attributed result.

Standard library only: the detached runner imports this without the service's
schema dependencies. A parsed result is a worker report. It never establishes
acceptance, verification or Saga's run outcome.
"""

import json
import math

MAX_FINAL_TEXT = 262144
TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MODEL_TOKEN_KEYS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")


def _cost(value):
    if type(value) not in (int, float) or not 0 <= value <= 1000000:
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except OverflowError:
        return None


def _counters(value, keys):
    if not isinstance(value, dict):
        return None
    found = {key: value[key] for key in keys if type(value.get(key)) is int and 0 <= value[key] <= 9007199254740991}
    return found or None


def _model_usage(value):
    if not isinstance(value, dict):
        return None
    result = {}
    for model, counters in list(value.items())[:32]:
        if not isinstance(model, str) or not 1 <= len(model) <= 128:
            continue
        item = _counters(counters, MODEL_TOKEN_KEYS)
        item = item or {}
        cost = counters.get("costUSD")
        cost = _cost(cost)
        if cost is not None:
            item["costUSD"] = cost
        if item:
            result[model] = item
    return result or None


def _text(value):
    if isinstance(value, str):
        return value[:MAX_FINAL_TEXT]
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)[:MAX_FINAL_TEXT]
    return ""


def parse_claude_json(stdout):
    """`claude -p --output-format json` prints one JSON object on stdout."""
    stdout = stdout.strip()
    if not stdout:
        return {"parse_error": "empty stdout"}
    candidates = [stdout]
    # Tolerate leading diagnostics: use the last complete JSON object line.
    lines = [line for line in stdout.splitlines() if line.strip()]
    if lines and lines[-1] != stdout:
        candidates.append(lines[-1])
    for candidate in candidates:
        try:
            body = json.loads(candidate)
        except ValueError:
            continue
        if not isinstance(body, dict):
            continue
        usage = _counters(body.get("usage"), TOKEN_KEYS)
        model_usage = _model_usage(body.get("modelUsage"))
        cost = body.get("total_cost_usd")
        return {
            "native_session_id": body.get("session_id")
            if isinstance(body.get("session_id"), str) and body.get("session_id")
            else None,
            "final_text": _text(body.get("result")),
            "is_error": body.get("is_error") is True,
            "stop_reason": body.get("stop_reason")
            if isinstance(body.get("stop_reason"), str)
            else None,
            "turns": body.get("num_turns")
            if type(body.get("num_turns")) is int and 0 <= body["num_turns"] <= 9007199254740991
            else None,
            "cost_usd": _cost(cost),
            "usage": usage,
            "usage_scope": "inclusive_aggregate" if usage or model_usage else None,
            "model_usage": model_usage,
            "observed_model": body.get("model") if isinstance(body.get("model"), str) and 0 < len(body["model"]) <= 128 else None,
            "permission_denials": len(body.get("permission_denials") or [])
            if isinstance(body.get("permission_denials"), list)
            else None,
            "parse_error": None,
        }
    return {"parse_error": "stdout is not a JSON result object"}


def parse_codex_jsonl(stdout, last_message=None):
    """`codex exec --json` prints newline-delimited events."""
    thread = None
    usage = None
    messages = []
    errors = []
    parsed_any = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if not isinstance(item, dict):
            continue
        parsed_any = True
        kind = item.get("type")
        if kind == "thread.started" and isinstance(item.get("thread_id"), str):
            thread = item["thread_id"]
        elif kind == "turn.completed" and isinstance(item.get("usage"), dict):
            usage = _counters(item["usage"], (
                "input_tokens", "output_tokens", "cached_input_tokens",
                "reasoning_output_tokens",
            ))
        elif kind == "item.completed":
            body = item.get("item")
            if isinstance(body, dict) and body.get("type") == "agent_message":
                messages.append(str(body.get("text", "")))
        elif kind in ("turn.failed", "error"):
            errors.append(str(item.get("error") or item.get("message") or kind))
    final = (
        last_message
        if isinstance(last_message, str) and last_message
        else ("\n\n".join(messages))
    )
    if not parsed_any and not final:
        return {"parse_error": "no codex events or final message found"}
    return {
        "native_session_id": thread,
        "final_text": final[:MAX_FINAL_TEXT],
        "is_error": bool(errors),
        "stop_reason": "error" if errors else "end_turn",
        "turns": None,
        "cost_usd": None,
        "usage": usage,
        "usage_scope": "inclusive_aggregate" if usage else None,
        "model_usage": None,
        "observed_model": None,
        "permission_denials": None,
        "parse_error": None,
        "errors": errors[:8],
    }


def parse_codex_text(stdout, last_message=None):
    """`codex exec resume` without JSON events: the final message file wins."""
    final = (
        last_message
        if isinstance(last_message, str) and last_message
        else (stdout.strip())
    )
    if not final:
        return {"parse_error": "empty codex output"}
    return {
        "native_session_id": None,
        "final_text": final[:MAX_FINAL_TEXT],
        "is_error": False,
        "stop_reason": "end_turn",
        "turns": None,
        "cost_usd": None,
        "usage": None,
        "permission_denials": None,
        "parse_error": None,
    }
