"""Project-scoped service commands for the local development loop.

Model messages can claim work and report evidence. Only the operator command
path can start, control or reconcile the loop. Evaluation is attributed model
judgment and never edits canonical commitment completion or Saga records.
"""

from .contracts import ALPHABET, canonical, strict_loads
from .development_loop import ATTENTION_RULES, DEADLINE_KEYS, MARKER
from .store import Conflict, digest

EXECUTIVE_ACTIONS = {
    "loop_status", "loop_inbox", "loop_claim", "loop_ready", "loop_capture", "loop_ack",
}
NOTICE_HEADER = (
    "NOTICE, not an assignment. Development loop {loop_id} is now {status} "
    "({kind}, round {round}). Do not call odin_loop_claim or odin_loop_ready for this "
    "message and do not execute or re-execute any stage because of it. Acknowledge it with "
    "odin_loop_ack notice_id={notice_id} and a stable operation_id so it stops being "
    "offered; acknowledgement records only that you saw it and grants no authority.\n\n"
)
OPERATOR_ACTIONS = {
    "loop_start", "loop_control", "loop_reconcile", "loop_hold", "loop_continue",
}
ACTIONS = EXECUTIVE_ACTIONS | OPERATOR_ACTIONS


def check_scope(gateway, action, payload):
    """Check current ownership before returning even an idempotent receipt."""
    if action == "loop_capture":
        final = payload.get("last_assistant_message", "")
        if isinstance(final, str):
            marker = MARKER.fullmatch(final.rstrip().split("\n")[-1])
            if marker:
                row = gateway.store.db.execute(
                    "SELECT body FROM development_loop_stages WHERE id=?",
                    (marker.group(1),),
                ).fetchone()
                if row and strict_loads(row[0])["project"] != payload.get("project"):
                    raise PermissionError("completion stage belongs to another project")
        # No active loop is an ordinary native Stop; it must not create work.
        for row in gateway.store.db.execute(
            "SELECT body FROM development_loops WHERE active=1"
        ):
            loop = strict_loads(row[0])
            if (
                loop["session_id"] == payload.get("session_id")
                and loop["project"] != payload.get("project")
            ):
                raise PermissionError("completion project differs from native session")
    elif action == "loop_ack":
        notice = gateway.development_loop.notice(payload["notice_id"])
        if notice["project"] != payload.get("project"):
            raise PermissionError("notice belongs to another project")
        if notice["session_id"] != payload.get("session_id"):
            raise PermissionError("notice belongs to another native session")
    elif "loop_id" in payload:
        loop = gateway.development_loop.get(payload["loop_id"])
        if loop["project"] != payload.get("project"):
            raise PermissionError("development loop belongs to another project")
        if "session_id" in payload and payload["session_id"] != loop["session_id"]:
            raise PermissionError("development loop belongs to another native session")
        if action in {"loop_claim", "loop_ready"}:
            # A recorded acknowledgement is historical evidence. It must never
            # revive permission to execute after pause, stop or supersession.
            gateway.coordination._live()
            allowed = (
                {"executive_pending", "executive_claimed"} if action == "loop_claim"
                else {"executive_claimed", "executive_ready"}
            )
            if loop["status"] not in allowed or loop["current_stage"] != payload.get("stage_id"):
                raise Conflict("development acknowledgement is no longer executable")


def summary(controller, loop):
    result = dict(loop)
    if loop["current_stage"]:
        stage = controller.stage(loop["current_stage"])
        result["executive_stage"] = {
            key: stage[key] for key in (
                "id", "state", "round", "source_packet_digest", "final_digest",
            )
        }
        if stage["completion_marker"]:
            # Allows reconciliation if the ready response was lost.
            result["executive_stage"]["completion_marker"] = stage["completion_marker"]
    if loop["current_job"]:
        job = controller.job(loop["current_job"])
        result["evaluator_job"] = {
            key: job[key] for key in ("id", "state", "packet_digest", "failure_reason")
        }
        if job["result"]:
            result["evaluation"] = job["result"]
    # Work and waiting state for the operator and the executive: what is
    # pending, running or unknown, which deadline applies, and whether notices
    # are still being offered. Delivery is at-least-once; "offered" means the
    # inbox returned it at least once, not that anyone read it.
    status = loop["status"]
    waiting = {
        "evaluator_pending": "pending", "executive_pending": "pending",
        "evaluator_running": "running", "executive_claimed": "running",
        "executive_ready": "running", "unknown": "unknown",
    }.get(status, "none")
    rule = ATTENTION_RULES.get(status)
    deadlines = loop.get("deadlines") or {key: None for key in DEADLINE_KEYS}
    result["work"] = {
        "waiting": waiting,
        "deadline_key": rule[0] if rule else None,
        "deadline_seconds": deadlines.get(rule[0]) if rule else None,
        "since": loop["updated_at"],
        "attention": loop.get("attention"),
        "deadlines": deadlines,
    }
    counts = controller.notice_counts(loop["id"])
    result["notices"] = counts | {
        "delivery": "at_least_once_until_acknowledged",
        "latest": [
            {key: notice[key] for key in (
                "id", "kind", "state", "observed", "created_at", "first_offered_at", "acknowledged_at",
            )}
            for notice in controller.notices(loop["id"], limit=4)
        ],
    }
    return result


def delivery_id(stage, revision):
    """Stable while pending, fresh after explicit recovery or pause/resume."""
    value = int(digest({"stage": stage["id"], "loop_revision": revision})[:32], 16)
    result = ""
    for _ in range(26):
        result = ALPHABET[value & 31] + result
        value >>= 5
    return result


def dispatch(gateway, action, payload, context, operation):
    controller = gateway.development_loop
    if context.actor.subject != "fable-executive":
        gateway._operator(context)
    elif action not in EXECUTIVE_ACTIONS:
        raise PermissionError("operator development command required")
    gateway.coordination._project(payload.get("project"))
    if action == "loop_capture":
        gateway.store.contracts.validate(
            "executive-pilot-loop-capture",
            {"schema_version": 1, "operation_id": operation,
             "action": action, "payload": payload},
        )
    else:
        gateway.store.contracts.validate_definition(
            "development-loop-command", action, payload
        )
    check_scope(gateway, action, payload)
    if action in {"loop_start", "loop_claim", "loop_ready", "loop_reconcile", "loop_continue"}:
        gateway.coordination._live()
    if action == "loop_control" and payload["action"] == "resume":
        gateway.coordination._live()
    if action == "loop_start":
        if not payload["goal"].strip():
            raise ValueError("development goal must not be blank")
        return controller.start(**payload, operation_id=operation)
    if action == "loop_status":
        loops = (
            [controller.get(payload["loop_id"])] if "loop_id" in payload
            else controller.for_project(payload["project"])[:16]
        )
        if "session_id" in payload:
            loops = [loop for loop in loops if loop["session_id"] == payload["session_id"]]
        views = []
        for loop in loops:
            item = summary(controller, loop)
            if len(canonical(views + [item]).encode()) > 480000:
                break
            views.append(item)
        return {
            "loops": views,
            "more_available": len(views) < len(loops) or (
                "loop_id" not in payload and len(loops) == 16
            ),
            "evaluator_configured": gateway.evaluator_configured,
            "service_stopped": gateway.store.stopped(),
            "evidence_kind": "local_development_evaluation",
            "verification": "model_attributed_not_canonical_acceptance",
        }
    if action == "loop_inbox":
        if gateway.store.stopped():
            return {"messages": []}
        messages = []
        # Assignments and notices are bounded separately so neither starves
        # the other; both are scoped to this project and native session.
        for stage in controller.pending_stages(**payload)[:8]:
            content = (
                f"Development loop {stage['loop_id']}, stage {stage['id']}.\n"
                "Before doing this assignment, call odin_loop_claim with these "
                "exact loop_id and stage_id and a stable operation_id. If the claim "
                "fails, inspect odin_loop_status and do not execute stale work.\n\n"
                + stage["prompt"]
                + "\n\nWhen finished, call odin_loop_ready with the same identities, "
                "a new stable operation_id and an evidence_packet containing exact "
                "revisions, artifact references and test results. Include its returned "
                "completion_marker as the last line of your final response. Keep "
                "observations, reports, inference and verified evidence distinct."
            )
            if len(content.encode()) > 16384:
                raise Conflict("development assignment exceeds channel budget")
            messages.append({
                "kind": "assignment",
                "message_id": delivery_id(
                    stage, controller.get(stage["loop_id"])["revision"]
                ),
                "loop_id": stage["loop_id"],
                "stage_id": stage["id"], "content": content,
            })
        notices = controller.pending_notices(payload["project"], payload["session_id"], limit=8)
        for notice in notices:
            loop = controller.get(notice["loop_id"])
            lines = [
                NOTICE_HEADER.format(
                    loop_id=notice["loop_id"], status=loop["status"], kind=notice["kind"],
                    round=notice["round"], notice_id=notice["id"],
                ),
                notice["summary"],
                "\nWhat needs attention: " + notice["attention"],
            ]
            if notice["assessment"]:
                lines.append("\nEvaluator assessment: " + notice["assessment"])
            if notice["stage_id"]:
                lines.append(f"\nRelated stage {notice['stage_id']} ({notice['stage_state']}); related evaluator job {notice['job_id']}.")
            lines.append(
                "\nInspect odin_loop_status for the full state. Operator-only actions "
                "(continue, pause, resume, stop, reconcile) go through the operator command "
                "path; nothing in this notice is operator approval."
            )
            content = "".join(lines)
            if MARKER.search(content):
                raise Conflict("notice content must not carry a completion footer")
            messages.append({
                "kind": "notice",
                "message_id": notice["id"],
                "notice_id": notice["id"],
                "loop_id": notice["loop_id"],
                "stage_id": notice["stage_id"],
                "content": content[:16384],
            })
        if notices:
            controller.mark_offered([notice["id"] for notice in notices])
        return {"messages": messages}
    if action == "loop_ack":
        return controller.acknowledge(
            payload["notice_id"], payload["project"], payload["session_id"], operation,
            actor=context.actor.subject,
        )
    if action in {"loop_claim", "loop_ready"}:
        arguments = {key: value for key, value in payload.items() if key != "project"}
        method = controller.claim if action == "loop_claim" else controller.ready
        result = method(**arguments, operation_id=operation)
        # The source packet is available to the evaluator; do not repeat an
        # arbitrarily large evidence bundle in every executive acknowledgement.
        answer = {"loop": summary(controller, result["loop"]),
                  "stage": {"id": result["stage"]["id"], "state": result["stage"]["state"]}}
        if "completion_marker" in result:
            answer["completion_marker"] = result["completion_marker"]
        if "receipt_validation" in result:
            # Compact so the executive can correct a mismatch before finishing;
            # the full per-receipt detail stays on the stage and in the packet.
            validation = result["receipt_validation"]
            answer["receipt_validation"] = {
                "status": validation["status"],
                "commands_succeeded": validation.get("commands_succeeded"),
                "receipts": [
                    {key: item.get(key) for key in (
                        "path", "outcome", "observed", "observed_before", "observed_after",
                        "before_reason", "after_reason", "head", "branch", "detached",
                        "clean_before", "clean",
                        "exit_status", "succeeded", "changed_during_run", "uncertainty",
                    )}
                    for item in validation["receipts"]
                ][:16],
                "problems": [problem[:400] for problem in validation["problems"]][:32],
            }
        return answer
    if action == "loop_capture":
        result = controller.capture_stop(
            payload["session_id"], payload.get("last_assistant_message", ""),
            operation, **{key: payload[key] for key in (
                "prompt_id", "hook_event_name", "stop_hook_active",
                "background_tasks", "session_crons",
            ) if key in payload},
        )
        # Persist full content once in the controller; receipts carry identities.
        return {
            key: ({"id": value["id"]} if key in {"loop", "stage", "job"} else value)
            for key, value in result.items()
        }
    loop = controller.get(payload["loop_id"])
    if action == "loop_continue":
        return controller.continue_after_intervention(
            loop["id"], payload["response"], operation,
            expected_revision=payload["expected_revision"],
            evidence_packet=payload.get("evidence_packet"),
        )
    if action == "loop_control":
        if payload["action"] == "deadlines":
            if "deadlines" not in payload:
                raise ValueError("deadlines control requires a deadlines object")
            return controller.set_deadlines(
                loop["id"], payload["deadlines"], operation,
                expected_revision=payload.get("expected_revision"),
            )
        if "deadlines" in payload:
            raise ValueError("deadlines belong to the deadlines control only")
        return controller.control(
            loop["id"], payload["action"], operation,
            expected_revision=payload.get("expected_revision"),
        )
    if action == "loop_hold":
        return controller.mark_execution_unknown(
            loop["id"], payload["stage_id"], loop["session_id"], operation,
            reason=payload["reason"],
        )
    if action == "loop_reconcile":
        if payload["target"] == "evaluator":
            if "job_id" not in payload or "stage_id" in payload:
                raise ValueError("evaluator reconciliation requires only job_id")
            job = controller.job(payload["job_id"])
            return controller.reconcile_evaluator(
                loop["id"], job["id"], job["packet_digest"], operation,
                observed=payload["observed"],
            )
        if "stage_id" not in payload or "job_id" in payload:
            raise ValueError("executive reconciliation requires only stage_id")
        return controller.reconcile_execution(
            loop["id"], payload["stage_id"], loop["session_id"], operation,
            observed=payload["observed"],
        )
    raise ValueError("unknown development action")
