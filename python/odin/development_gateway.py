"""Project-scoped service commands for the local development loop.

Model messages can claim work and report evidence. Only the operator command
path can start, control or reconcile the loop. Evaluation is attributed model
judgment and never edits canonical commitment completion or Saga records.
"""

from .contracts import ALPHABET, canonical, strict_loads
from .development_loop import MARKER
from .store import Conflict, digest

EXECUTIVE_ACTIONS = {
    "loop_status", "loop_inbox", "loop_claim", "loop_ready", "loop_capture",
}
OPERATOR_ACTIONS = {
    "loop_start", "loop_control", "loop_reconcile", "loop_hold",
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
    if action in {"loop_start", "loop_claim", "loop_ready", "loop_reconcile"}:
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
        for stage in controller.pending_stages(**payload)[:16]:
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
                "message_id": delivery_id(
                    stage, controller.get(stage["loop_id"])["revision"]
                ),
                "loop_id": stage["loop_id"],
                "stage_id": stage["id"], "content": content,
            })
        return {"messages": messages}
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
                        "path", "outcome", "observed", "head", "branch", "detached", "clean",
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
    if action == "loop_control":
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
