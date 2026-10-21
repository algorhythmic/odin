"""Project-scoped service commands for the local development loop.

Model messages can claim work and report evidence. Only the operator command
path can start, control or reconcile the loop. Evaluation is attributed model
judgment and never edits canonical commitment completion or Saga records.
"""

import os
from pathlib import Path

from .contracts import ALPHABET, canonical, strict_loads
from .development_loop import ATTENTION_RULES, DEADLINE_KEYS, MARKER, clip_bytes
from .store import Conflict, digest

EXECUTIVE_ACTIONS = {
    "loop_status", "loop_inbox", "loop_claim", "loop_ready", "loop_capture", "loop_ack", "loop_delegate",
}
NOTICE_HEADER = (
    "NOTICE, not an assignment. Development loop {loop_id} became {status} "
    "({kind}, round {round}; currently {current}). Do not call odin_loop_claim or odin_loop_ready for this "
    "message and do not execute or re-execute any stage because of it. Acknowledge it with "
    "odin_loop_ack notice_id={notice_id} and a stable operation_id so it stops being "
    "offered; acknowledgement records only that you saw it and grants no authority.\n\n"
)
OPERATOR_ACTIONS = {
    "loop_start",
    "loop_control",
    "loop_reconcile",
    "loop_hold",
    "loop_continue",
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
            if loop["session_id"] == payload.get("session_id") and loop[
                "project"
            ] != payload.get("project"):
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
        if action in {"loop_claim", "loop_ready", "loop_delegate"}:
            # A recorded acknowledgement is historical evidence. It must never
            # revive permission to execute after pause, stop or supersession.
            gateway.coordination._live()
            allowed = (
                {"executive_pending", "executive_claimed"}
                if action == "loop_claim"
                else {"executive_claimed", "executive_ready"}
            )
            if loop["status"] not in allowed or loop["current_stage"] != payload.get(
                "stage_id"
            ):
                raise Conflict("development acknowledgement is no longer executable")


def summary(controller, loop):
    result = dict(loop)
    if loop["current_stage"]:
        stage = controller.stage(loop["current_stage"])
        result["executive_stage"] = {
            key: stage[key]
            for key in (
                "id",
                "state",
                "round",
                "source_packet_digest",
                "final_digest",
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
        "evaluator_pending": "pending",
        "executive_pending": "pending",
        "evaluator_running": "running",
        "executive_claimed": "running",
        "executive_ready": "running",
        "unknown": "unknown",
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
            {
                key: notice[key]
                for key in (
                    "id",
                    "kind",
                    "state",
                    "observed",
                    "created_at",
                    "first_offered_at",
                    "acknowledged_at",
                )
            }
            for notice in controller.notices(loop["id"], limit=4)
        ],
    }
    return result


NOTICE_CONTENT_BYTES = 16384
NOTICE_NARRATIVE_BYTES = 2000


def render_notice(notice, current_status):
    """Render one notice within the channel's UTF-8 byte budget.

    Redaction happens before any clipping. The identity header, attention,
    related identities and status guidance are essential and kept whole; the
    summary and the evaluator assessment share whatever budget remains and
    are clipped on character boundaries. Notices persisted under earlier
    character-based limits are bounded here too.
    """

    def redact(text):
        return MARKER.sub("[completion footer redacted]", text or "")

    header = NOTICE_HEADER.format(
        loop_id=notice["loop_id"],
        status=notice["transition"]["to"],
        kind=notice["kind"],
        round=notice["round"],
        notice_id=notice["id"],
        current=current_status,
    )
    attention = "\nWhat needs attention: " + clip_bytes(
        redact(notice["attention"]), NOTICE_NARRATIVE_BYTES
    )
    related = (
        f"\nRelated stage {notice['stage_id']} ({notice['stage_state']}); "
        f"related evaluator job {notice['job_id']}."
        if notice["stage_id"]
        else ""
    )
    guidance = (
        "\nInspect odin_loop_status for the full state. Operator-only actions "
        "(continue, pause, resume, stop, reconcile) go through the operator command "
        "path; nothing in this notice is operator approval."
    )
    essential = sum(
        len(part.encode("utf-8")) for part in (header, attention, related, guidance)
    )
    budget = max(0, NOTICE_CONTENT_BYTES - essential)
    summary = clip_bytes(
        redact(notice["summary"]), min(NOTICE_NARRATIVE_BYTES * 2, budget)
    )
    budget -= len(summary.encode("utf-8"))
    assessment = ""
    if notice["assessment"]:
        label = "\nEvaluator assessment: "
        room = budget - len(label.encode("utf-8"))
        if room > 32:
            assessment = label + clip_bytes(redact(notice["assessment"]), room)
    content = header + summary + attention + assessment + related + guidance
    # A completion footer cannot be assembled from clipped fragments, but the
    # invariant is cheap to assert on the final bytes.
    content = MARKER.sub("[completion footer redacted]", content)
    return clip_bytes(content, NOTICE_CONTENT_BYTES, suffix="")


def quiescence(gateway, project=None):
    """Durable facts a supervisor needs before replacing the service process.

    A loop is quiescent when no evaluator job is running or unknown and no
    executive stage is unknown; the capture spool must be empty and no
    delegated turn may be running. This observes state; it does not know
    whether the native conversation is mid-turn, which the supervisor
    checks separately.
    """
    controller = gateway.development_loop
    loops = []
    for row in gateway.store.db.execute(
        "SELECT body FROM development_loops WHERE active=1"
    ).fetchall():
        loop = strict_loads(row[0])
        if project is not None and loop["project"] != project:
            continue
        job = controller.job(loop["current_job"]) if loop["current_job"] else None
        stage = (
            controller.stage(loop["current_stage"]) if loop["current_stage"] else None
        )
        loops.append(
            {
                "loop_id": loop["id"],
                "status": loop["status"],
                "evaluator_job_state": job["state"] if job else None,
                "executive_stage_state": stage["state"] if stage else None,
                "quiescent": loop["status"] not in {"evaluator_running", "unknown"}
                and (job is None or job["state"] not in {"running", "unknown"})
                and (stage is None or stage["state"] != "unknown"),
            }
        )
    store_path = getattr(gateway.store, "path", None)
    spool = Path(store_path).parent / "executive-loop-spool" if store_path else None
    # Presence is sufficient to veto a restart. Bound directory inspection;
    # unreadable or unexpectedly large spools are unsafe, not empty.
    spooled = 0
    if spool is not None:
        try:
            with os.scandir(spool) as entries:
                for inspected, entry in enumerate(entries, 1):
                    if entry.name.endswith(".json") or inspected >= 1024:
                        spooled = 1
                        break
        except FileNotFoundError:
            pass
        except OSError:
            spooled = 1
    delegation = getattr(gateway, "delegation", None)
    running_turns = 0
    if delegation is not None:
        running_turns = gateway.store.db.execute(
            "SELECT COUNT(*) FROM delegation_turns WHERE state IN (?,?,?,?)",
            ("queued", "launching", "running", "interrupting"),
        ).fetchone()[0]
    return {
        "loops": loops,
        "spooled_captures": spooled,
        "delegated_turns_running": running_turns,
        "restart_quiescent": all(item["quiescent"] for item in loops)
        and spooled == 0
        and running_turns == 0,
        "native_conversation": "not observable here; the supervisor confirms the executive turn is idle",
    }


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
            {
                "schema_version": 1,
                "operation_id": operation,
                "action": action,
                "payload": payload,
            },
        )
    else:
        gateway.store.contracts.validate_definition(
            "development-loop-command", action, payload
        )
    check_scope(gateway, action, payload)
    if action in {"loop_start", "loop_claim", "loop_ready", "loop_reconcile", "loop_continue", "loop_delegate"}:
        gateway.coordination._live()
    if action == "loop_control" and payload["action"] == "resume":
        gateway.coordination._live()
    if action == "loop_start":
        if not payload["goal"].strip():
            raise ValueError("development goal must not be blank")
        return controller.start(**payload, operation_id=operation)
    if action == "loop_delegate":
        from .development_delegation import assign
        return assign(gateway, payload, operation, context.actor.subject)
    if action == "loop_status":
        loops = (
            [controller.get(payload["loop_id"])]
            if "loop_id" in payload
            else controller.for_project(payload["project"])[:16]
        )
        if "session_id" in payload:
            loops = [
                loop for loop in loops if loop["session_id"] == payload["session_id"]
            ]
        views = []
        for loop in loops:
            item = summary(controller, loop)
            item["admission"] = gateway.usage_policy.check(loop["project"], purpose="development_status", loop_id=loop["id"], session_id=loop["session_id"])
            from .development_delegation import binding
            item["delegation"] = binding(gateway.store, loop["current_stage"]) if loop["current_stage"] else None
            if len(canonical(views + [item]).encode()) > 480000:
                break
            views.append(item)
        return {
            "loops": views,
            "more_available": len(views) < len(loops)
            or ("loop_id" not in payload and len(loops) == 16),
            "quiescence": quiescence(gateway, payload["project"]),
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
        accept = set(payload.get("accept") or ["assignment"])
        for stage in controller.pending_stages(
            payload["project"], payload["session_id"]
        )[:8]:
            if "assignment" not in accept:
                break
            loop = controller.get(stage["loop_id"])
            admission = gateway.usage_policy.check(loop["project"], purpose="executive_stage", loop_id=loop["id"], stage_id=stage["id"], session_id=loop["session_id"])
            if admission["decision"] == "hold":
                continue
            content = (
                f"Development loop {stage['loop_id']}, stage {stage['id']}.\n"
                "Before doing this assignment, call odin_loop_claim with these "
                "exact loop_id and stage_id and a stable operation_id. If the claim "
                "fails, inspect odin_loop_status and do not execute stale work.\n\n"
                + ("This stage requires separate orchestration. After claiming, create or reuse a matching odin_delegation_session, call odin_loop_delegate, inspect the return and record odin_delegation_close acceptance before ready. Requested profile: " + canonical(loop["delegation_profile"]) + "\n\n" if loop.get("delegation_profile") else "")
                + stage["prompt"]
                + "\n\nWhen finished, call odin_loop_ready with the same identities, "
                "a new stable operation_id and an evidence_packet containing exact "
                "revisions, artifact references and test results. Include its returned "
                "completion_marker as the last line of your final response. Keep "
                "observations, reports, inference and verified evidence distinct."
            )
            if len(content.encode()) > 16384:
                raise Conflict("development assignment exceeds channel budget")
            messages.append(
                {
                    "kind": "assignment",
                    "message_id": delivery_id(
                        stage, controller.get(stage["loop_id"])["revision"]
                    ),
                    "loop_id": stage["loop_id"],
                    "stage_id": stage["id"],
                    "content": content,
                }
            )
        # A bridge that predates notices never declared acceptance and keeps
        # receiving assignments only, so service and bridge can be reloaded
        # in either order.
        notices = (
            controller.pending_notices(
                payload["project"], payload["session_id"], limit=8
            )
            if "notice" in accept
            else []
        )
        for notice in notices:
            loop = controller.get(notice["loop_id"])
            messages.append(
                {
                    "kind": "notice",
                    "message_id": notice["id"],
                    "notice_id": notice["id"],
                    "loop_id": notice["loop_id"],
                    "stage_id": notice["stage_id"],
                    "content": render_notice(notice, loop["status"]),
                }
            )
        if notices and context.actor.subject == "fable-executive":
            # Only the executive's own poll counts as an offer to it.
            controller.mark_offered([notice["id"] for notice in notices])
        return {"messages": messages}
    if action == "loop_ack":
        return controller.acknowledge(
            payload["notice_id"],
            payload["project"],
            payload["session_id"],
            operation,
            actor=context.actor.subject,
        )
    if action in {"loop_claim", "loop_ready"}:
        arguments = {key: value for key, value in payload.items() if key != "project"}
        if action == "loop_claim":
            decision = gateway.usage_policy.check(payload["project"], purpose="executive_stage", loop_id=payload["loop_id"], stage_id=payload["stage_id"], session_id=payload["session_id"])
            if decision["decision"] == "hold":
                return {"admission": decision, "held": True, "loop": summary(controller, controller.get(payload["loop_id"]))}
        method = controller.claim if action == "loop_claim" else controller.ready
        result = method(**arguments, operation_id=operation)
        # The source packet is available to the evaluator; do not repeat an
        # arbitrarily large evidence bundle in every executive acknowledgement.
        answer = {
            "loop": summary(controller, result["loop"]),
            "stage": {"id": result["stage"]["id"], "state": result["stage"]["state"]},
        }
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
                    {
                        key: item.get(key)
                        for key in (
                            "path",
                            "outcome",
                            "observed",
                            "observed_before",
                            "observed_after",
                            "before_reason",
                            "after_reason",
                            "head",
                            "branch",
                            "detached",
                            "clean_before",
                            "clean",
                            "exit_status",
                            "succeeded",
                            "changed_during_run",
                            "uncertainty",
                        )
                    }
                    for item in validation["receipts"]
                ][:16],
                "problems": [problem[:400] for problem in validation["problems"]][:32],
            }
        return answer
    if action == "loop_capture":
        result = controller.capture_stop(
            payload["session_id"],
            payload.get("last_assistant_message", ""),
            operation,
            **{
                key: payload[key]
                for key in (
                    "prompt_id",
                    "hook_event_name",
                    "stop_hook_active",
                    "background_tasks",
                    "session_crons",
                )
                if key in payload
            },
        )
        # Persist full content once in the controller; receipts carry identities.
        return {
            key: ({"id": value["id"]} if key in {"loop", "stage", "job"} else value)
            for key, value in result.items()
        }
    loop = controller.get(payload["loop_id"])
    if action == "loop_continue":
        return controller.continue_after_intervention(
            loop["id"],
            payload["response"],
            operation,
            expected_revision=payload["expected_revision"],
            evidence_packet=payload.get("evidence_packet"),
        )
    if action == "loop_control":
        if payload["action"] == "deadlines":
            if "deadlines" not in payload:
                raise ValueError("deadlines control requires a deadlines object")
            return controller.set_deadlines(
                loop["id"],
                payload["deadlines"],
                operation,
                expected_revision=payload.get("expected_revision"),
            )
        if "deadlines" in payload:
            raise ValueError("deadlines belong to the deadlines control only")
        return controller.control(
            loop["id"],
            payload["action"],
            operation,
            expected_revision=payload.get("expected_revision"),
        )
    if action == "loop_hold":
        return controller.mark_execution_unknown(
            loop["id"],
            payload["stage_id"],
            loop["session_id"],
            operation,
            reason=payload["reason"],
        )
    if action == "loop_reconcile":
        if payload["target"] == "evaluator":
            if "job_id" not in payload or "stage_id" in payload:
                raise ValueError("evaluator reconciliation requires only job_id")
            job = controller.job(payload["job_id"])
            return controller.reconcile_evaluator(
                loop["id"],
                job["id"],
                job["packet_digest"],
                operation,
                observed=payload["observed"],
            )
        if "stage_id" not in payload or "job_id" in payload:
            raise ValueError("executive reconciliation requires only stage_id")
        return controller.reconcile_execution(
            loop["id"],
            payload["stage_id"],
            loop["session_id"],
            operation,
            observed=payload["observed"],
        )
    raise ValueError("unknown development action")
