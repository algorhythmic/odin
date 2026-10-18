"""Deterministic service policy. A model result cannot create authority."""

from .contracts import Contracts


def route(item):
    kind = item["kind"]
    if kind.startswith("operator.command."):
        return "direct"
    if kind in ("operator.message", "review.verdict"):
        return "interrupt"
    if kind in ("run.request", "operator.approval"):
        return "operator_queue"
    if kind.startswith("surface.") or kind in ("lesson.published", "review.position"):
        return "log"
    if kind.startswith("run.state."):
        return (
            "wake"
            if kind.rsplit(".", 1)[1] in ("failed", "cancelled", "limit_paused")
            else "lifecycle"
        )
    if kind == "run.status.transition" or kind.startswith("run.plateau."):
        return "wake"
    if kind == "run.journal":
        return "triage"
    if kind == "work.report":
        value = item.get("payload", {})
        if (
            value.get("type") == "journal_triage"
            and value.get("status") == "no_attention"
            and value.get("complete_coverage") is True
        ):
            return "digest"
        return "wake"
    if kind.startswith("host."):
        return "host"
    return "wake"  # Unknown significance is never silently suppressed.


def combine_review(positions, round_number):
    if round_number not in (1, 2):
        raise ValueError("review round limit")
    if len(positions) != 2 or {p["position"] for p in positions} != {"a", "b"}:
        raise ValueError("two distinct reviewer positions required")
    results = [
        p.get("verdict", {}).get("result") if p.get("verdict") else None
        for p in positions
    ]
    approving = {"APPROVE", "APPROVE_UNCHANGED"}
    if all(result in approving for result in results):
        return {
            "combination": "approved",
            "result": "APPROVE_UNCHANGED"
            if len(set(results)) == 1 and results[0] == "APPROVE_UNCHANGED"
            else "APPROVE",
        }
    # Never infer a waiver or use a decision model to settle disagreement.
    return {"combination": "escalated", "result": None}


def require_capabilities(matrix, required, *, allow_fixture=False):
    Contracts().validate("capabilities", matrix)
    if matrix["mode"] == "fixture" and not allow_fixture:
        raise PermissionError("fixture adapter cannot satisfy a live session class")
    missing = sorted(c for c in required if not matrix["capabilities"].get(c, False))
    if missing:
        raise PermissionError("missing capabilities: " + ", ".join(missing))


def session_class(requirements, candidates, matrix, budget_microusd):
    Contracts().validate("capabilities", matrix)
    rejected = []
    chosen = None
    if len({c["name"] for c in candidates}) != len(candidates):
        raise ValueError("duplicate class")
    for candidate in candidates:
        missing = set(requirements) - set(candidate["supports"])
        if missing:
            reason = "missing_requirements:" + ",".join(sorted(missing))
        elif candidate["cost_bound_microusd"] > budget_microusd:
            reason = "budget"
        elif any(
            not matrix["capabilities"].get(c, False) for c in candidate["capabilities"]
        ):
            reason = "missing_capability"
        elif chosen is not None:
            reason = "lower_configured_priority"
        else:
            chosen = candidate["name"]
            continue
        rejected.append({"class": candidate["name"], "reason": reason})
    return chosen, rejected


def account(condition, episodes):
    for episode in episodes:
        Contracts().validate("evaluation-episode", episode)
        if episode["condition"] != condition:
            raise ValueError("mixed comparison conditions")
        parts = episode["cost_components"]
        operations = [p["operation"] for p in parts]
        if len(operations) != len(set(operations)):
            raise ValueError("duplicate cost component")
        covered = set(operations)
        for part in parts:
            children = set(part["includes_operations"])
            if covered & children:
                raise ValueError("overlapping usage coverage")
            covered.update(children)
            if part["cost_microusd"] is None and not part["missing_reason"]:
                raise ValueError("missing cost needs a reason")
        measured = (
            sum(p["cost_microusd"] for p in parts)
            if parts and all(p["cost_microusd"] is not None for p in parts)
            else None
        )
        if measured != episode["cost_microusd"]:
            raise ValueError("episode total does not reconcile")
        if episode["accepted"] and (
            episode["result_status"] != "complete" or not episode["acceptance_evidence"]
        ):
            raise ValueError("acceptance requires independent evidence")
    if len({e["episode_id"] for e in episodes}) != len(episodes):
        raise ValueError("duplicate episode")
    accepted = sum(e["accepted"] for e in episodes)
    known = sum(e["cost_microusd"] or 0 for e in episodes)
    missing = sum(e["cost_microusd"] is None for e in episodes)
    result = {
        "schema_version": 1,
        "label": "fake-backend evidence",
        "condition": condition,
        "attempted": len(episodes),
        "accepted": accepted,
        "known_cost_microusd": known,
        "missing_cost_episodes": missing,
        "cost_per_accepted_microusd": known / accepted
        if accepted and not missing
        else None,
        "elapsed_seconds": [e["elapsed_seconds"] for e in episodes],
        "failures": [
            e.get("failure") or "unresolved" for e in episodes if not e["accepted"]
        ],
    }
    Contracts().validate("evaluation", result)
    return result
