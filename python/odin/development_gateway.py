"""Project-scoped service commands for the local development loop.

Model messages can claim work and report evidence. Only the operator command
path can start, control or reconcile the loop. Evaluation is attributed model
judgment and never edits canonical commitment completion or Saga records.
"""

import os
from pathlib import Path

from .contracts import ALPHABET, canonical, strict_loads
from .development_loop import (
    ATTENTION_RULES,
    DEADLINE_KEYS,
    EVALUATOR_UNOBSERVED,
    MARKER,
    clip_bytes,
)
from .store import AccessRefused, Conflict, digest

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
    "loop_handover",
}
ACTIONS = EXECUTIVE_ACTIONS | OPERATOR_ACTIONS


# Matches the bridge's loop inbox bound (executive_mcp.ExecutiveBridge.loop_inbox).
INBOX_LIMIT = 16

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
        # Delegation notices are project-scoped: the delegation does not know
        # which native executive session will read them.
        delegated = gateway.delegation.notice(payload["notice_id"])
        if delegated is not None:
            if delegated["project"] != payload.get("project"):
                raise PermissionError("notice belongs to another project")
            return
        limit = gateway.limit_notices.notice(payload["notice_id"])
        if limit is not None:
            if limit["project"] != payload.get("project"):
                raise PermissionError("notice belongs to another project")
            return
        notice = gateway.development_loop.notice(payload["notice_id"])
        if notice["project"] != payload.get("project"):
            raise PermissionError("notice belongs to another project")
        if notice["session_id"] != payload.get("session_id"):
            # Same project: the code tells a rotated executive why, never whose.
            raise AccessRefused("notice_owned_by_other_session")
    elif "loop_id" in payload:
        loop = gateway.development_loop.get(payload["loop_id"])
        expected = payload.get("project")
        if expected is None and action == "loop_handover":
            # The operator addresses one loop by identity; a restricted scope
            # with no project was already denied before this check.
            expected = loop["project"]
        if loop["project"] != expected:
            raise PermissionError("development loop belongs to another project")
        if "session_id" in payload and payload["session_id"] != loop["session_id"]:
            raise AccessRefused("loop_owned_by_other_session")
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


PROCESS_LIMIT = 65536
RECORD_LIMIT = 1024
UNRESOLVED_DETAIL = 16
LOCK_NOTE = (
    "an observation, not a lock: dispatch, delegation and capture continue "
    "after this reading; read it immediately before replacing the service"
)


def _processes(state):
    """Index live non-zombie processes, or return None if unobservable.

    Returns the set of their process groups and the arguments that name a path
    under the state directory. Read-only. Processes of other users may be
    hidden; Odin's runners and harnesses run as this user, so an unreadable
    process of this user makes the whole table unobservable.
    """
    groups, references = set(), []
    root = str(state).encode() + b"/"
    try:
        with os.scandir("/proc") as entries:
            for inspected, entry in enumerate(entries, 1):
                if inspected > PROCESS_LIMIT:
                    return None
                if not entry.name.isdigit():
                    continue
                try:
                    # Bytes: a process name need not be valid UTF-8.
                    fields = Path(entry.path, "stat").read_bytes().rsplit(b")", 1)[1].split()
                    argv = Path(entry.path, "cmdline").read_bytes().split(b"\0")
                except (FileNotFoundError, ProcessLookupError):
                    continue  # Exited while scanning.
                except PermissionError:
                    try:
                        if entry.stat().st_uid != os.getuid():
                            continue
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                    return None
                if fields[0] != b"Z":
                    groups.add(int(fields[2]))
                    references += [arg for arg in argv if arg.startswith(root)]
    except (OSError, IndexError, ValueError):
        return None
    return groups, references


def _present(processes, groups, directory):
    """A recorded process group still has members or a process names the spool."""
    live, references = processes
    prefix = str(directory).encode()
    return bool(live & groups) or any(
        arg == prefix or arg.startswith(prefix + b"/") for arg in references
    )


def _harness_recorded_or_required(job, directory):
    """Whether started.json must be read for the job's harness group.

    A completed runner wrote it before its result, and a runner that opened
    the harness's output may have started the harness. A dangling link counts
    as present, so its reading fails as unresolved.
    """
    return job["state"] == "completed" or any(
        os.path.lexists(directory / name) for name in ("started.json", "stdout.log")
    )


def _evaluator_executions(gateway, state, processes):
    """Classify every dispatched evaluator job by process evidence, read-only.

    A job without an evaluator-start receipt was never spawned: the reservation
    and the durable start precede any process. A process naming a job's spool
    keeps that job outstanding whatever its state. Completion is not group
    termination: a harness can exit leaving a descendant in its recorded group.
    So every dispatched job, completed or not, stays outstanding while a
    recorded runner or harness process group has members, and unresolved while
    its dispatch evidence (and, once completed, its started.json) or the
    process table cannot be read, until the scheduler has recorded that
    attempt's groups observed empty (``evaluator-quiet``).
    """
    from jsonschema.exceptions import ValidationError

    from .development_evaluator import ID, SCHEMA, _private_directory, _read

    outstanding, unresolved, details = 0, 0, []
    root = state / "development-evaluator"
    prefix = str(root).encode() + b"/"
    named = set()
    if processes is not None:
        for arg in processes[1]:
            if arg.startswith(prefix):
                named.add(arg[len(prefix):].split(b"/", 1)[0].decode(errors="replace"))
    for job_id in sorted(named):
        outstanding += 1
        details.append(
            {
                "kind": "evaluator_job",
                "id": job_id if ID.fullmatch(job_id) else None,
                "reason": "process names its spool",
            }
        )
    dispatched = (
        "FROM development_loop_jobs j WHERE EXISTS (SELECT 1 FROM development_loop_receipts r "
        "WHERE r.operation>='evaluator-start:'||j.id||':' AND r.operation<'evaluator-start:'||j.id||';')"
    )
    if processes is None:
        count = gateway.store.db.execute("SELECT COUNT(*) " + dispatched).fetchone()[0]
        if count:
            details.append({"kind": "evaluator_job", "id": None, "reason": "process table unavailable"})
        return 0, count, details
    rows = gateway.store.db.execute(
        "SELECT body " + dispatched + " AND " + EVALUATOR_UNOBSERVED + " ORDER BY j.rowid LIMIT ?",
        (RECORD_LIMIT + 1,),
    ).fetchall()
    if len(rows) > RECORD_LIMIT:
        rows = rows[:RECORD_LIMIT]
        unresolved += 1
        details.append({"kind": "evaluator_job", "id": None, "reason": "inspection bound exceeded"})
    for row in rows:
        try:
            job = strict_loads(row[0])
            if not ID.fullmatch(job["id"]):
                raise ValueError("invalid evaluator job identity")
        except (ValueError, KeyError, TypeError):
            unresolved += 1
            details.append({"kind": "evaluator_job", "id": None, "reason": "job record unreadable"})
            continue
        if job["id"] in named:
            continue
        try:
            directory = _private_directory(root / job["id"])
            dispatch = _read(directory / "dispatch.json", SCHEMA, definition="dispatch")
            if (
                dispatch["job_id"] != job["id"]
                or dispatch["packet_digest"] != job["packet_digest"]
            ):
                raise Conflict("evaluator spool job/packet binding mismatch")
            groups = {dispatch["runner_pid"]}
            if _harness_recorded_or_required(job, directory):
                started = _read(directory / "started.json", SCHEMA, definition="started")
                groups |= {started["runner_pid"], started["harness_pid"]}
        except (OSError, ValueError, KeyError, TypeError, ValidationError, Conflict):
            unresolved += 1
            details.append(
                {"kind": "evaluator_job", "id": job["id"], "reason": "dispatch evidence missing or unreadable"}
            )
            continue
        if processes[0] & (groups - {None}):
            outstanding += 1
            details.append(
                {"kind": "evaluator_job", "id": job["id"], "reason": f"recorded process group live; job {job['state']}"}
            )
    return outstanding, unresolved, details


def _lost_turns(gateway, state, processes):
    """Lost turns stay unresolved: no supported path establishes their outcome.

    As with configure_delegation, a lost record is never erased or relabelled
    and retirement of its session does not resolve it. The process observation
    is reported for the supervisor; it does not clear the gate.
    """
    rows = gateway.store.db.execute(
        "SELECT body FROM delegation_turns WHERE state='lost' ORDER BY rowid LIMIT ?",
        (UNRESOLVED_DETAIL,),
    ).fetchall()
    total = gateway.store.db.execute(
        "SELECT COUNT(*) FROM delegation_turns WHERE state='lost'"
    ).fetchone()[0]
    details = []
    for row in rows:
        try:
            turn = strict_loads(row[0])
            runner = turn.get("runner") or {}
            directory = state / "delegations" / turn["session"] / turn["id"]
        except (ValueError, KeyError, TypeError, AttributeError):
            details.append({"kind": "delegated_turn_lost", "id": None, "reason": "turn record unreadable"})
            continue
        groups = {runner.get("pid"), runner.get("harness_pid")} - {None}
        if processes is None:
            observed = "unknown"
        elif _present(processes, groups, directory):
            observed = "present"
        elif runner.get("pid") is None or runner.get("harness_pid") is None:
            observed = "unknown"  # An unrecorded harness group cannot be observed.
        else:
            observed = "absent"
        details.append(
            {
                "kind": "delegated_turn_lost",
                "id": turn["id"],
                "reason": "native outcome unknown; recorded processes " + observed,
            }
        )
    return total, details


def quiescence(gateway, project=None):
    """Durable and process facts a supervisor needs before replacing the service.

    The gate is service-wide: every loop, evaluator job, delegated turn and
    the capture spool count whatever the requested project; per-loop detail is
    listed for that project. Unreadable or missing evidence is never absence.
    This observes only: it signals, reconciles or redispatches nothing, and it
    cannot see whether the native conversation is mid-turn, which the
    supervisor checks separately.
    """
    controller = gateway.development_loop
    loops, elsewhere = [], 0
    for row in gateway.store.db.execute(
        "SELECT body FROM development_loops WHERE active=1"
    ).fetchall():
        loop = strict_loads(row[0])
        job = controller.job(loop["current_job"]) if loop["current_job"] else None
        stage = (
            controller.stage(loop["current_stage"]) if loop["current_stage"] else None
        )
        quiet = (
            loop["status"] not in {"evaluator_running", "unknown"}
            and (job is None or job["state"] not in {"running", "unknown"})
            and (stage is None or stage["state"] != "unknown")
        )
        if project is not None and loop["project"] != project:
            elsewhere += not quiet
            continue
        loops.append(
            {
                "loop_id": loop["id"],
                "status": loop["status"],
                "evaluator_job_state": job["state"] if job else None,
                "executive_stage_state": stage["state"] if stage else None,
                "quiescent": quiet,
            }
        )
    store_path = getattr(gateway.store, "path", None)
    state = Path(store_path).parent if store_path else None
    spool = state / "executive-loop-spool" if state else None
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
    running_turns, lost_turns, details = 0, 0, []
    outstanding, unresolved = 0, 0
    if state is None:
        unresolved, details = 1, [{"kind": "state", "id": None, "reason": "state directory unknown"}]
    else:
        candidates = gateway.store.db.execute(
            "SELECT 1 FROM development_loop_receipts WHERE operation>='evaluator-start:' "
            "AND operation<'evaluator-start;' LIMIT 1"
        ).fetchone()
        if delegation is not None and not candidates:
            candidates = gateway.store.db.execute(
                "SELECT 1 FROM delegation_turns WHERE state='lost' LIMIT 1"
            ).fetchone()
        processes = _processes(state) if candidates else (set(), [])
        if delegation is not None:
            running_turns = gateway.store.db.execute(
                "SELECT COUNT(*) FROM delegation_turns WHERE state IN (?,?,?,?)",
                ("queued", "launching", "running", "interrupting"),
            ).fetchone()[0]
            lost_turns, details = _lost_turns(gateway, state, processes)
        outstanding, unresolved, evaluator_details = _evaluator_executions(
            gateway, state, processes
        )
        details += evaluator_details
    return {
        "scope": "service",
        "loops": loops,
        "loops_not_quiescent_other_projects": elsewhere,
        "spooled_captures": spooled,
        "delegated_turns_running": running_turns,
        "delegated_turns_lost": lost_turns,
        "evaluator_executions_outstanding": outstanding,
        "evaluator_executions_unresolved": unresolved,
        "unresolved": details[:UNRESOLVED_DETAIL],
        "restart_quiescent": all(item["quiescent"] for item in loops)
        and elsewhere == 0
        and spooled == 0
        and running_turns == 0
        and lost_turns == 0
        and outstanding == 0
        and unresolved == 0,
        "native_conversation": "not observable here; the supervisor confirms the executive turn is idle",
        "observation": LOCK_NOTE,
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
    if payload.get("project") is not None:
        gateway.coordination._project(payload["project"])
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
                + ("This stage requires separate orchestration. After claiming, create or reuse a matching odin_delegation_session, call odin_loop_delegate, inspect the concise implementation return and record odin_delegation_close acceptance before ready. You retain the executive-only claim, ready, loop commands and final completion footer; the orchestrator receives the stage prompt as a task reference. Requested profile: " + canonical(loop["delegation_profile"]) + "\n\n" if loop.get("delegation_profile") else "")
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
        # Delegation turn notices (ODIN-ADR-027) share the channel and the
        # acknowledgement path; they carry no loop or stage and are never
        # claimable.
        # The bridge rejects an inbox above INBOX_LIMIT items, so delegation
        # notices only take the slots assignments and loop notices left.
        room = min(8, INBOX_LIMIT - len(messages))
        delegated = (
            gateway.delegation.pending_notices(payload["project"], limit=room)
            if "notice" in accept and room > 0
            else []
        )
        for notice in delegated:
            messages.append(
                {
                    "kind": "notice",
                    "message_id": notice["id"],
                    "notice_id": notice["id"],
                    "loop_id": None,
                    "stage_id": None,
                    "content": gateway.delegation.render_notice(notice),
                }
            )
        if delegated and context.actor.subject == "fable-executive":
            gateway.delegation.mark_offered([notice["id"] for notice in delegated])
        # Account limit band notices (ODIN-ADR-031 amendment) take the slots left.
        room = min(4, INBOX_LIMIT - len(messages))
        limits = (
            gateway.limit_notices.pending(payload["project"], limit=room)
            if "notice" in accept and room > 0
            else []
        )
        for notice in limits:
            messages.append(
                {
                    "kind": "notice",
                    "message_id": notice["id"],
                    "notice_id": notice["id"],
                    "loop_id": None,
                    "stage_id": None,
                    "content": gateway.limit_notices.render(notice),
                }
            )
        if limits and context.actor.subject == "fable-executive":
            gateway.limit_notices.mark_offered([notice["id"] for notice in limits])
        return {"messages": messages}
    if action == "loop_ack":
        if gateway.delegation.notice(payload["notice_id"]) is not None:
            return gateway.delegation.acknowledge_notice(
                payload["notice_id"], payload["project"], actor=context.actor.subject
            )
        if gateway.limit_notices.notice(payload["notice_id"]) is not None:
            return gateway.limit_notices.acknowledge(
                payload["notice_id"], payload["project"], actor=context.actor.subject
            )
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
    if action == "loop_handover":
        return controller.handover(
            loop["id"],
            payload["from_session"],
            payload["to_session"],
            payload["reason"],
            operation,
            expected_revision=payload["expected_revision"],
            actor=context.actor.subject,
        )
    if action == "loop_continue":
        return controller.continue_after_intervention(
            loop["id"],
            payload["response"],
            operation,
            expected_revision=payload["expected_revision"],
            evidence_packet=payload.get("evidence_packet"),
        )
    if action == "loop_control":
        if payload["action"] == "configure_delegation":
            if "deadlines" in payload:
                raise ValueError("deadlines belong to the deadlines control only")
            return controller.configure_delegation(
                loop["id"], payload["stage_id"], payload["session_id"],
                payload["delegation_profile"], operation,
                expected_revision=payload["expected_revision"],
            )
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
