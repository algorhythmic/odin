"""Small, explicitly lossy views of executive bridge receipts.

The gateway receipt remains authoritative. This module only changes what the
native executive sees in a tool response; scoped detail calls remain available.
"""

from .contracts import canonical


MAX_COMPACT_BYTES = 16384
TARGETS = frozenset({
    "odin_delegation_status", "odin_loop_status", "odin_loop_claim", "odin_loop_ready",
})


def _pick(source, keys):
    return {key: source[key] for key in keys if key in source}


def _clip(value, limit=400):
    if not isinstance(value, str):
        return value
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value
    preview = raw[:limit].decode("utf-8", "ignore")
    return {"preview": preview,
            "omitted_utf8_bytes": len(raw) - len(preview.encode("utf-8"))}


def _turn(turn):
    result = turn.get("result") or {}
    answer = _pick(turn, ("id", "seq", "kind", "state", "created_at", "finished_at",
                          "native_session_mismatch"))
    answer["failure"] = _clip(turn.get("failure"))
    if result:
        answer["result"] = _pick(result, ("native_session_id", "observed_model",
                                           "cost_usd", "exit_code", "status", "timed_out",
                                           "interrupted", "is_error",
                                           "permission_denials"))
        if result.get("stop_reason"):
            answer["result"]["stop_reason"] = _clip(result["stop_reason"])
        elif "stop_reason" in result:
            answer["result"]["stop_reason"] = result["stop_reason"]
        for key in ("error", "error_summary", "parse_error"):
            if result.get(key):
                answer["result"][key] = _clip(result[key])
    return answer


def _assignment(item):
    answer = _pick(item, ("id", "rev", "state", "commitment", "commitment_state",
                          "criteria", "limits"))
    answer["objective"] = _clip(item.get("objective"), 240)
    turns = item.get("turns") or []
    # Keep all unresolved turns and the four latest terminal returns. Earlier
    # successful turns are available through a scoped detail call.
    unresolved = [turn for turn in turns if turn.get("state") not in
                  {"returned", "accepted", "completed", "cancelled"}]
    latest = turns[-4:]
    chosen = {turn.get("id") for turn in unresolved + latest}
    answer["turns"] = [_turn(turn) for turn in turns if turn.get("id") in chosen]
    answer["omitted_turn_count"] = len(turns) - len(answer["turns"])
    return answer


def _delegation(result, *, assignment_id=None):
    if "sessions" not in result:
        return result
    answer = _pick(result, ("enabled", "reason", "project", "verification"))
    answer["sessions"] = []
    omitted_assignments = 0
    for item in result["sessions"]:
        session = _pick(item, ("session", "options", "native_peer_name",
                               "native_peer_transport", "binding", "native_session_observed",
                               "turn_count", "running_turns", "cost_usd_known",
                               "turns_with_unknown_cost", "adopted_commitments"))
        assignments = item.get("assignments") or []
        active = [a for a in assignments if assignment_id or a.get("state") not in
                  {"completed", "cancelled", "accepted"}]
        session["assignments"] = [_assignment(a) for a in active]
        session["omitted_terminal_assignment_count"] = len(assignments) - len(active)
        omitted_assignments += len(assignments) - len(active)
        answer["sessions"].append(session)
    answer["projection"] = {
        "view": "compact", "omitted_terminal_assignments": omitted_assignments,
        "detail": "Call odin_delegation_status with view=detail and session_id or assignment_id; call odin_delegation_result for full worker output.",
    }
    return answer


def _loop(item):
    keys = ("id", "revision", "project", "session_id", "status", "round", "max_rounds",
            "current_stage", "current_job", "paused_from", "updated_at",
            "attention", "no_progress_count", "no_progress_limit",
            "executive_stage", "evaluator_job", "work", "notices", "delegation",
            "admission", "delegation_profile")
    answer = _pick(item, keys)
    for key in ("reason", "goal", "failure_reason"):
        if item.get(key):
            answer[key] = _clip(item[key])
    if isinstance(item.get("evaluation"), dict):
        evaluation = item["evaluation"]
        answer["evaluation"] = _pick(evaluation, ("decision", "status", "next_stage"))
        if evaluation.get("assessment"):
            answer["evaluation"]["assessment"] = _clip(evaluation["assessment"])
        answer["evaluation"]["omitted_fields"] = len(evaluation) - len(answer["evaluation"])
    answer["omitted_loop_fields"] = len(item) - len(answer)
    return answer


def _loop_result(name, result):
    if name == "odin_loop_status" and "loops" in result:
        answer = _pick(result, ("more_available", "quiescence", "evaluator_configured",
                                "service_stopped", "evidence_kind", "verification"))
        answer["loops"] = [_loop(item) for item in result["loops"]]
    elif "loop" in result:
        answer = {key: value for key, value in result.items() if key != "loop"}
        answer["loop"] = _loop(result["loop"])
    else:
        return result
    answer["projection"] = {
        "view": "compact", "detail": "Repeat the matching tool with view=detail and the same scoped IDs; for a write, reuse the same operation_id and arguments.",
    }
    return answer


def project_receipt(name, receipt, *, view="compact", arguments=None):
    """Return a bounded display receipt without changing the service receipt."""
    if view == "detail" or name not in TARGETS:
        return receipt
    result = receipt["result"]
    projected = (_delegation(result, assignment_id=(arguments or {}).get("assignment_id"))
                 if name == "odin_delegation_status"
                 else _loop_result(name, result))
    if projected is result:
        return receipt
    answer = receipt | {"result": projected}
    if len(canonical(answer).encode("utf-8")) <= MAX_COMPACT_BYTES:
        return answer
    # Never silently truncate active work: provide the exact scope and an
    # explicit incomplete marker. The executive must use the detail path.
    if name == "odin_delegation_status":
        scopes = [_pick(s.get("session", {}), ("id", "rev", "state"))
                  for s in result.get("sessions", [])]
        counts = {"sessions": len(scopes),
                  "assignments": sum(len(s.get("assignments", [])) for s in result.get("sessions", [])),
                  "unresolved_turns": sum(1 for s in result.get("sessions", [])
                                          for a in s.get("assignments", [])
                                          for t in a.get("turns", [])
                                          if t.get("state") not in {"returned", "accepted", "completed", "cancelled"})}
    else:
        loops = result.get("loops", [result["loop"]] if "loop" in result else [])
        scopes = [_pick(loop, ("id", "revision", "status", "round", "max_rounds",
                               "current_stage", "current_job", "executive_stage",
                               "attention", "no_progress_count", "no_progress_limit"))
                  for loop in loops]
        counts = {"loops": len(loops)}
    detail = ("Repeat this write with the same operation_id and arguments plus view=detail; "
              "then inspect a scoped odin_loop_status call."
              if name in {"odin_loop_claim", "odin_loop_ready"} else
              "Call the matching status tool with view=detail and a scoped ID; do not infer that omitted work is complete.")
    overflow = {"view": "compact", "incomplete_for_action": True,
                "reason": "compact_response_budget_exceeded",
                "counts": counts, "scopes": scopes, "detail": detail}
    minimal_result = {"projection": overflow}
    if isinstance(result.get("quiescence"), dict):
        # The restart gate's verdict and counters survive the overflow; only
        # its per-loop list and unresolved detail are omitted.
        minimal_result["quiescence"] = {
            key: value for key, value in result["quiescence"].items()
            if key not in {"loops", "unresolved"}
        } | {"detail_omitted": True}
    if name in {"odin_loop_claim", "odin_loop_ready"}:
        # A write acknowledgement must retain its stage identity and receipt
        # outcome even when explanatory detail exceeds the display budget.
        minimal_result.update(_pick(result, ("stage", "completion_marker", "held")))
        if "loop" in result:
            minimal_result["loop"] = _pick(result["loop"],
                                           ("id", "revision", "status", "round", "max_rounds",
                                            "current_stage", "session_id"))
        if isinstance(result.get("receipt_validation"), dict):
            validation = result["receipt_validation"]
            minimal_result["receipt_validation"] = {
                **_pick(validation, ("status", "commands_succeeded")),
                "receipt_count": len(validation.get("receipts", [])),
                "problem_count": len(validation.get("problems", [])),
                "detail_omitted": True,
            }
    minimal = receipt | {"result": minimal_result}
    if len(canonical(minimal).encode("utf-8")) > MAX_COMPACT_BYTES:
        overflow.pop("scopes")
        overflow["scope_ids_omitted"] = True
    return minimal
