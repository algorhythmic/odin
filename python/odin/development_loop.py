"""Durable local development evaluator/executive coordination.

Only the trusted service writes this state. Transports perform external work
outside these transactions and correlate outcomes with the persisted packet or
completion marker. These records confer no Saga or verification guarantees.
"""

from __future__ import annotations

import re
import secrets
import time
import uuid
from datetime import datetime

from .contracts import ALPHABET, canonical, identifier, strict_loads
from .execution_receipt import validate_references
from .store import Conflict, Refused, digest, now

FINAL = {"complete", "stopped"}
# Loop statuses that end the loop or need the operator produce a durable notice.
NOTICE_TRANSITIONS = {
    "complete": "completion",
    "stopped": "stopped",
    "needs_operator": "intervention",
    "unknown": "intervention",
}
NOTICE_KINDS = ("completion", "failure", "intervention", "stopped", "stalled")
# Which configured deadline bounds each waiting state; absent statuses never
# raise attention (paused, unknown, needs_operator, terminal).
ATTENTION_RULES = {
    "executive_pending": ("offer_seconds", "offer_unanswered"),
    "executive_claimed": ("claim_seconds", "claimed_stalled"),
    "executive_ready": ("ready_seconds", "ready_uncaptured"),
    "evaluator_pending": ("evaluator_seconds", "evaluator_stalled"),
    "evaluator_running": ("evaluator_seconds", "evaluator_stalled"),
}
DEADLINE_KEYS = ("offer_seconds", "claim_seconds", "ready_seconds", "evaluator_seconds")
ATTENTION_CHECK_INTERVAL = 5.0
NOTICE_SUMMARY_BYTES = 2000
# An evaluator attempt that can no longer spawn processes, and the SQL for a
# dispatched job's latest started attempt and whether that attempt's recorded
# process groups have been observed empty (``evaluator-quiet:<job>:<n>``).
FINISHED_EVALUATOR_STATES = ("completed", "cancelled", "lost")
EVALUATOR_ATTEMPT = (
    "(SELECT MAX(CAST(substr(r.operation,length(j.id)+18) AS INTEGER)) "
    "FROM development_loop_receipts r WHERE r.operation>='evaluator-start:'||j.id||':' "
    "AND r.operation<'evaluator-start:'||j.id||';')"
)
EVALUATOR_UNOBSERVED = (
    "NOT EXISTS (SELECT 1 FROM development_loop_receipts q "
    "WHERE q.operation='evaluator-quiet:'||j.id||':'||" + EVALUATOR_ATTEMPT + ")"
)


def _ulid_from_digest(value):
    number = int(digest(value)[:32], 16)
    result = ""
    for _ in range(26):
        result = ALPHABET[number & 31] + result
        number >>= 5
    return result


def _redact(text):
    """Strip any completion footer quoted in model text before it is persisted."""
    return MARKER.sub("[completion footer redacted]", text or "")


def clip_bytes(text, limit, suffix=" […]"):
    """Bound ``text`` to ``limit`` UTF-8 bytes on a character boundary."""
    if limit <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    tail = suffix.encode("utf-8")
    if len(tail) > limit:
        return encoded[:limit].decode("utf-8", errors="ignore")
    keep = max(0, limit - len(tail))
    return encoded[:keep].decode("utf-8", errors="ignore") + suffix


def _parse(stamp):
    return datetime.strptime(
        stamp, "%Y-%m-%dT%H:%M:%S.%fZ" if "." in stamp else "%Y-%m-%dT%H:%M:%SZ"
    )


def normalize_deadlines(value):
    """Operator-supplied deadlines: each key a positive integer or null (disabled)."""
    if value is None:
        return {key: None for key in DEADLINE_KEYS}
    if not isinstance(value, dict) or set(value) - set(DEADLINE_KEYS):
        raise Conflict("unknown development deadline key")
    result = {}
    for key in DEADLINE_KEYS:
        item = value.get(key)
        if item is not None and (type(item) is not int or not 1 <= item <= 604800):
            raise Conflict(
                "development deadlines are positive seconds up to one week or null"
            )
        result[key] = item
    return result


MARKER = re.compile(
    r"<!-- odin-development-complete:([0-7][0-9A-HJKMNP-TV-Z]{25}):([0-9a-f]{32}) -->"
)


def normalize_result(result, contracts):
    """Strict model-output validation; no extra fields or decision coercions."""
    contracts.validate("development-loop-result", result)
    value = strict_loads(canonical(result))
    value["assessment"] = value["assessment"].strip()
    value["next_prompt"] = value["next_prompt"].strip()
    value["findings"] = [finding.strip() for finding in value["findings"]]
    if not value["assessment"] or any(not finding for finding in value["findings"]):
        raise Conflict("empty evaluator assessment or finding")
    if value["decision"] == "continue" and not value["next_prompt"]:
        raise Conflict("continue requires a next prompt")
    if value["decision"] != "continue" and value["next_prompt"]:
        raise Conflict("terminal evaluation must not dispatch a next prompt")
    refs = {}
    for ref in value["evidence_refs"]:
        if not ref["ref"].strip() or not ref["revision"].strip():
            raise Conflict("empty evidence reference")
        key = (ref["ref"], ref["revision"])
        if key in refs and refs[key]["digest"] != ref["digest"]:
            raise Conflict("conflicting evaluator evidence reference")
        refs[key] = ref
    value["evidence_refs"] = [refs[key] for key in sorted(refs)]
    if len(value["next_prompt"].encode()) > 12000:
        raise Conflict("next prompt exceeds channel notification budget")
    if len(canonical(value).encode()) > 65536:
        raise Conflict("evaluator result exceeds 64 KiB")
    return value


class DevelopmentLoop:
    def __init__(self, store):
        store._core()
        self.store = store
        with store.transaction():
            for statement in (
                "CREATE TABLE IF NOT EXISTS development_loops(id TEXT PRIMARY KEY,project TEXT NOT NULL,active INTEGER NOT NULL,body TEXT NOT NULL)",
                "CREATE UNIQUE INDEX IF NOT EXISTS development_loop_active_project ON development_loops(project) WHERE active=1",
                "CREATE TABLE IF NOT EXISTS development_loop_jobs(id TEXT PRIMARY KEY,loop_id TEXT NOT NULL,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS development_loop_stages(id TEXT PRIMARY KEY,loop_id TEXT NOT NULL,body TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS development_loop_receipts(operation TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,result TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS development_loop_notices(id TEXT PRIMARY KEY,loop_id TEXT NOT NULL,project TEXT NOT NULL,session_id TEXT NOT NULL,state TEXT NOT NULL,body TEXT NOT NULL)",
            ):
                store.db.execute(statement)
        self._attention_checked = 0.0

    def _mutate(self, operation, kind, arguments, callback):
        if (
            not isinstance(operation, str)
            or not operation.strip()
            or len(operation) > 128
        ):
            raise Conflict("stable operation ID required")
        fingerprint = digest({"kind": kind, "arguments": arguments})
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT fingerprint,result FROM development_loop_receipts WHERE operation=?",
                (operation,),
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise Conflict(
                        "development operation ID reused with changed arguments"
                    )
                return strict_loads(row[1])
            result = callback()
            self.store.db.execute(
                "INSERT INTO development_loop_receipts VALUES(?,?,?)",
                (operation, fingerprint, canonical(result)),
            )
            self.store._history(
                "development_loop.command",
                {
                    "operation_id": operation,
                    "kind": kind,
                    "arguments_digest": fingerprint,
                    "result_digest": digest(result),
                    "loop_id": result.get("loop", {}).get("id"),
                    "state": result.get("loop", {}).get("status"),
                    "job_id": result.get("job", {}).get("id"),
                    "stage_id": result.get("stage", {}).get("id")
                    if result.get("stage")
                    else None,
                },
            )
            return result

    def _row(self, table, identity):
        row = self.store.db.execute(
            f"SELECT body FROM {table} WHERE id=?", (identity,)
        ).fetchone()
        if row is None:
            raise Conflict("development loop identity unavailable")
        return strict_loads(row[0])

    def get(self, loop_id):
        return self._row("development_loops", loop_id)

    def for_project(self, project):
        rows = self.store.db.execute(
            "SELECT body FROM development_loops WHERE project=? ORDER BY rowid DESC",
            (project,),
        )
        return [strict_loads(row[0]) for row in rows]

    def job(self, job_id):
        return self._row("development_loop_jobs", job_id)

    def stage(self, stage_id):
        return self._row("development_loop_stages", stage_id)

    def _save_loop(self, loop):
        self.store.contracts.validate("development-loop", loop)
        self.store.db.execute(
            "INSERT INTO development_loops VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET active=excluded.active,body=excluded.body",
            (
                loop["id"],
                loop["project"],
                int(loop["status"] not in FINAL),
                canonical(loop),
            ),
        )

    def _save_job(self, job):
        self.store.contracts.validate("development-loop-job", job)
        self.store.contracts.validate("development-loop-packet", job["packet"])
        if digest(job["packet"]) != job["packet_digest"]:
            raise Conflict("evaluator packet digest changed")
        if job["result"] is not None:
            self.store.contracts.validate("development-loop-result", job["result"])
        self.store.db.execute(
            "INSERT INTO development_loop_jobs VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
            (job["id"], job["loop_id"], canonical(job)),
        )

    def _save_stage(self, stage):
        self.store.contracts.validate("development-loop-stage", stage)
        self.store.db.execute(
            "INSERT INTO development_loop_stages VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
            (stage["id"], stage["loop_id"], canonical(stage)),
        )

    def _advance(self, loop, status, reason=None):
        previous = loop["status"]
        loop.update(
            status=status,
            reason=reason,
            revision=loop["revision"] + 1,
            updated_at=now(),
            attention=None,  # Any real transition supersedes a stall observation.
        )
        self._save_loop(loop)
        kind = NOTICE_TRANSITIONS.get(status)
        if kind is not None:
            # Same transaction as the durable outcome; the id is a function of
            # the transition, so a replayed or repeated transition cannot create
            # a second notice.
            if kind == "intervention" and loop["current_job"]:
                job = self.job(loop["current_job"])
                if job["state"] in {"lost", "blocked"}:
                    kind = "failure"
            self._notice(loop, kind, previous=previous)

    # -- notices --------------------------------------------------------------

    def _notice(
        self, loop, kind, *, previous, observed=None, deadline=None, since=None
    ):
        # Transition notices are a function of the transition; a stalled notice
        # is a function of the persisted observation (including when it was
        # made), so distinct observations never share an identity while the
        # same persisted observation is never written twice.
        notice_id = _ulid_from_digest(
            {
                "loop": loop["id"],
                "kind": kind,
                "status": loop["status"],
                "revision": loop["revision"],
                "observed": observed,
                "deadline": deadline,
                "since": since,
            }
        )
        assessment = None
        decision = None
        if loop["current_job"]:
            job = self.job(loop["current_job"])
            if job["result"]:
                assessment = clip_bytes(
                    _redact(job["result"]["assessment"]), NOTICE_SUMMARY_BYTES
                )
                decision = job["result"]["decision"]
        stage_state = None
        if loop["current_stage"]:
            stage_state = self.stage(loop["current_stage"])["state"]
        if kind == "completion":
            attention = "none; the loop ended by evaluator decision"
        elif kind == "stopped":
            attention = "operator stopped the loop; running native tools or delegated jobs were not terminated by this"
        elif kind == "stalled":
            attention = (
                f"{observed}: no transition for longer than the configured deadline; elapsed time "
                "does not prove work did not start and authorizes no redispatch, new round, "
                "process termination or session replacement"
            )
        elif kind == "failure":
            attention = (
                "evaluator job lost or blocked; operator reconciliation required"
            )
        else:
            attention = "operator decision or reconciliation required before the loop can continue"
        summary = clip_bytes(
            f"Development loop {loop['id']} {kind}: status {loop['status']} (from {previous}) "
            f"at round {loop['round']} of {loop['max_rounds']}, revision {loop['revision']}."
            + (f" Reason: {_redact(loop['reason'])}" if loop.get("reason") else ""),
            NOTICE_SUMMARY_BYTES,
        )
        notice = {
            "schema_version": 1,
            "id": notice_id,
            "kind": kind,
            "loop_id": loop["id"],
            "project": loop["project"],
            "session_id": loop["session_id"],
            "round": loop["round"],
            "stage_id": loop["current_stage"],
            "stage_state": stage_state,
            "job_id": loop["current_job"],
            "transition": {
                "from": previous,
                "to": loop["status"],
                "loop_revision": loop["revision"],
            },
            "observed": observed,
            "summary": summary,
            "assessment": assessment,
            "decision": decision,
            "attention": attention,
            "status_reference": {"tool": "odin_loop_status", "loop_id": loop["id"]},
            "created_at": now(),
            "state": "pending",
            "first_offered_at": None,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "acknowledgement_operation": None,
            "acknowledgement_authority": None,
        }
        self.store.contracts.validate("development-loop-notice", notice)
        inserted = self.store.db.execute(
            "INSERT INTO development_loop_notices VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
            (
                notice_id,
                loop["id"],
                loop["project"],
                loop["session_id"],
                "pending",
                canonical(notice),
            ),
        ).rowcount
        if inserted:
            self.store._history(
                "development_loop.notice",
                {
                    "notice_id": notice_id,
                    "loop_id": loop["id"],
                    "kind": kind,
                    "status": loop["status"],
                    "loop_revision": loop["revision"],
                },
            )
        return notice_id

    def notice(self, notice_id):
        return self._row("development_loop_notices", notice_id)

    def notices(self, loop_id, limit=64):
        rows = self.store.db.execute(
            "SELECT body FROM development_loop_notices WHERE loop_id=? ORDER BY rowid DESC LIMIT ?",
            (loop_id, limit),
        )
        return [strict_loads(row[0]) for row in rows]

    def pending_notices(self, project, session_id, limit=8):
        """Unacknowledged notices for this project and native session, oldest first.

        Loop status does not filter them: an ended or intervention-bound loop
        still has its notice delivered until acknowledged.
        """
        rows = self.store.db.execute(
            "SELECT body FROM development_loop_notices WHERE project=? AND session_id=? "
            "AND state='pending' ORDER BY rowid LIMIT ?",
            (project, session_id, limit),
        )
        return [strict_loads(row[0]) for row in rows]

    def mark_offered(self, notice_ids, at=None):
        """Record the first channel offer only; later polls write nothing."""
        stamp = at or now()
        changed = []
        with self.store.transaction():
            for notice_id in notice_ids:
                notice = self.notice(notice_id)
                if notice["first_offered_at"] is None:
                    notice["first_offered_at"] = stamp
                    self._save_notice(notice)
                    changed.append(notice_id)
        return changed

    def _save_notice(self, notice):
        self.store.contracts.validate("development-loop-notice", notice)
        self.store.db.execute(
            "UPDATE development_loop_notices SET state=?,body=? WHERE id=?",
            (notice["state"], canonical(notice), notice["id"]),
        )

    def acknowledge(self, notice_id, project, session_id, operation_id, *, actor):
        """Model-attributed acknowledgement: stops re-delivery, grants nothing else."""
        arguments = {
            "notice_id": notice_id,
            "project": project,
            "session_id": session_id,
            "actor": actor,
        }

        def apply():
            notice = self.notice(notice_id)
            if notice["project"] != project or notice["session_id"] != session_id:
                raise Conflict("notice belongs to another project or native session")
            if notice["state"] != "acknowledged":
                notice.update(
                    state="acknowledged",
                    acknowledged_at=now(),
                    acknowledged_by=actor,
                    acknowledgement_operation=operation_id,
                    acknowledgement_authority=(
                        "model_attributed_not_operator_approval"
                        if actor == "fable-executive"
                        else "operator_terminal_acknowledgement_not_approval"
                    ),
                )
                self._save_notice(notice)
            return {
                "notice": {
                    key: notice[key]
                    for key in (
                        "id",
                        "kind",
                        "loop_id",
                        "stage_id",
                        "state",
                        "acknowledged_at",
                        "acknowledged_by",
                        "acknowledgement_authority",
                    )
                },
                "loop": self.get(notice["loop_id"]),
            }

        return self._mutate(operation_id, "notice_acknowledged", arguments, apply)

    def notice_counts(self, loop_id):
        counts = {"pending": 0, "acknowledged": 0, "unoffered": 0}
        for state, total in self.store.db.execute(
            "SELECT state, COUNT(*) FROM development_loop_notices WHERE loop_id=? GROUP BY state",
            (loop_id,),
        ):
            counts[state] = total
        counts["unoffered"] = self.store.db.execute(
            "SELECT COUNT(*) FROM development_loop_notices WHERE loop_id=? AND state='pending' "
            "AND json_extract(body, '$.first_offered_at') IS NULL",
            (loop_id,),
        ).fetchone()[0]
        return counts

    # -- deadlines and attention ------------------------------------------------

    def set_deadlines(
        self, loop_id, deadlines, operation_id, *, expected_revision=None
    ):
        normalized = normalize_deadlines(deadlines)
        arguments = {
            "loop_id": loop_id,
            "deadlines": normalized,
            "expected_revision": expected_revision,
        }

        def apply():
            loop = self.get(loop_id)
            if expected_revision is not None and loop["revision"] != expected_revision:
                raise Conflict("stale development loop revision")
            if loop["status"] in FINAL:
                raise Conflict("development loop is terminal")
            # A configuration edit is not a transition: status, revision,
            # updated_at and reason stay, so delivery identities, cached
            # receipts and timing are untouched. Only an observation that was
            # made under the deadline being changed is cleared.
            previous = loop.get("deadlines") or normalize_deadlines(None)
            rule = ATTENTION_RULES.get(loop["status"])
            if (
                rule
                and loop.get("attention")
                and previous.get(rule[0]) != normalized.get(rule[0])
            ):
                loop["attention"] = None
            loop["deadlines"] = normalized
            self._save_loop(loop)
            return {"loop": loop}

        return self._mutate(operation_id, "deadlines", arguments, apply)

    def check_attention(self, at=None, *, force=False):
        """Observe waiting loops against their deadlines; never dispatch anything.

        Attention is a bounded observation stored on the loop without changing
        its status or revision, plus one `stalled` notice per (loop, status,
        revision). Repeated checks with no new observation write nothing. A
        clock that moved backwards yields a negative elapsed time and raises no
        attention. Paused, unknown, intervention-bound and terminal loops are
        not checked. Late claims, results and captures proceed normally and
        clear the observation through their own transition.
        """
        monotonic = time.monotonic()
        if (
            not force
            and at is None
            and monotonic - self._attention_checked < ATTENTION_CHECK_INTERVAL
        ):
            return []
        self._attention_checked = monotonic
        stamp = at or now()
        changed = []
        for row in self.store.db.execute(
            "SELECT body FROM development_loops WHERE active=1"
        ).fetchall():
            loop = strict_loads(row[0])
            rule = ATTENTION_RULES.get(loop["status"])
            if rule is None or loop.get("attention") is not None:
                continue
            limit = (loop.get("deadlines") or {}).get(rule[0])
            if limit is None:
                continue
            try:
                elapsed = (_parse(stamp) - _parse(loop["updated_at"])).total_seconds()
            except ValueError:
                continue
            if elapsed <= limit:
                continue
            observed = rule[1]
            with self.store.transaction():
                current = self.get(loop["id"])
                if current["revision"] != loop["revision"] or current.get("attention"):
                    continue
                current["attention"] = {
                    "state": "attention",
                    "observed": observed,
                    "status": current["status"],
                    "since": stamp,
                    "loop_revision": current["revision"],
                    "elapsed_seconds": int(elapsed),
                    "deadline_seconds": limit,
                    "notice_id": None,
                }
                current["attention"]["notice_id"] = self._notice(
                    current,
                    "stalled",
                    previous=current["status"],
                    observed=observed,
                    deadline=limit,
                    since=stamp,
                )
                self._save_loop(current)
                self.store._history(
                    "development_loop.attention",
                    {
                        "loop_id": current["id"],
                        "observed": observed,
                        "status": current["status"],
                        "loop_revision": current["revision"],
                        "elapsed_seconds": int(elapsed),
                    },
                )
                changed.append(current["id"])
        return changed

    @staticmethod
    def _evidence(packet):
        if not isinstance(packet, dict) or len(canonical(packet).encode()) > 65536:
            raise Conflict("evidence packet must be an object within 64 KiB")
        return strict_loads(canonical(packet))

    # Receipt validation reads retained files outside the store; it is
    # injectable so synthetic tests can observe or replace it. It runs before a
    # transaction opens, its outcome is bounded, and it is recorded with the
    # evidence rather than raised: a validation failure is never success.
    validate_receipts = staticmethod(validate_references)

    def _receipt_validation(self, evidence, loop_id, stage_id, not_before=None):
        legacy = {
            "status": "legacy_no_receipt",
            "receipts": [],
            "problems": [],
            "commands_succeeded": None,
        }
        try:
            result = self.validate_receipts(
                evidence,
                expected={"loop_id": loop_id, "stage_id": stage_id},
                not_before=not_before,
            )
            result = {
                "status": result["status"],
                "receipts": result["receipts"][:16],
                "problems": [str(p)[:1400] for p in result["problems"]][:256],
                "commands_succeeded": result.get("commands_succeeded"),
            }
            if len(canonical(result).encode()) > 65536:
                result = result | {
                    "status": "invalid"
                    if result["status"].startswith("validated")
                    else result["status"],
                    "receipts": [],
                    "problems": [
                        "receipt validation detail exceeded 64 KiB; see retained receipts"
                    ],
                }
            self.store.contracts.validate_definition(
                "execution-receipt", "validation", result
            )
        except Exception as error:  # noqa: BLE001 - validation failure is evidence, not a crash
            result = legacy | {
                "status": "invalid",
                "problems": [
                    f"receipt validation failed: {type(error).__name__}: {error}"[:1400]
                ],
            }
        return result

    def _queue_evaluator(
        self,
        loop,
        evidence,
        final_text="",
        previous=None,
        receipt_validation=None,
        operator_response=None,
    ):
        packet = {
            "schema_version": 1,
            "loop_id": loop["id"],
            "project": loop["project"],
            "session_id": loop["session_id"],
            "round": loop["round"],
            "loop_revision": loop["revision"],
            "goal": loop["goal"],
            "executive_final_text": final_text,
            "evidence": self._evidence(evidence),
            "previous_assessment": previous,
            # Re-validated at capture time: artifacts may have changed since ready.
            "receipt_validation": receipt_validation
            or {
                "status": "legacy_no_receipt",
                "receipts": [],
                "problems": [],
                "commands_succeeded": None,
            },
        }
        if operator_response is not None:
            packet["operator_response"] = operator_response
        job = {
            "schema_version": 1,
            "id": identifier(),
            "loop_id": loop["id"],
            "project": loop["project"],
            "state": "pending",
            "packet": packet,
            "packet_digest": digest(packet),
            "result": None,
            "failure_reason": None,
            "created_at": now(),
        }
        self._save_job(job)
        loop["current_job"] = job["id"]
        self._save_loop(loop)
        return job

    def start(
        self,
        project,
        goal,
        session_id,
        operation_id,
        *,
        evidence_packet=None,
        max_rounds=12,
        no_progress_limit=3,
        deadlines=None,
        delegation_profile=None,
    ):
        try:
            if (
                not isinstance(session_id, str)
                or str(uuid.UUID(session_id)) != session_id
            ):
                raise ValueError("noncanonical UUID")
        except (ValueError, AttributeError) as error:
            raise Conflict("canonical native session UUID required") from error
        evidence = self._evidence({} if evidence_packet is None else evidence_packet)
        deadlines = normalize_deadlines(deadlines)
        arguments = {
            "project": project,
            "goal": goal,
            "session_id": session_id,
            "evidence": evidence,
            "max_rounds": max_rounds,
            "no_progress_limit": no_progress_limit,
            "deadlines": deadlines,
            "delegation_profile": delegation_profile,
        }

        def apply():
            if self.store.get(project)["record_type"] != "Project":
                raise Conflict("development loop requires a project")
            if any(loop["status"] not in FINAL for loop in self.for_project(project)):
                raise Conflict("project already has an active development loop")
            if any(
                strict_loads(row[0])["session_id"] == session_id
                for row in self.store.db.execute(
                    "SELECT body FROM development_loops WHERE active=1"
                )
            ):
                raise Conflict("native session already has an active development loop")
            stamp = now()
            loop = {
                "schema_version": 1,
                "id": identifier(),
                "project": project,
                "session_id": session_id,
                "previous_session_ids": [],
                "goal": goal,
                "status": "evaluator_pending",
                "revision": 1,
                "round": 0,
                "max_rounds": max_rounds,
                "no_progress_limit": no_progress_limit,
                "no_progress_count": 0,
                "last_evidence_digest": None,
                "current_job": None,
                "current_stage": None,
                "paused_from": None,
                "reason": None,
                "created_at": stamp,
                "updated_at": stamp,
                "deadlines": deadlines,
                "attention": None,
                "delegation_profile": delegation_profile,
            }
            self._save_loop(loop)
            job = self._queue_evaluator(loop, evidence)
            return {"loop": loop, "job": job}

        return self._mutate(operation_id, "start", arguments, apply)

    def pending_evaluators(self, project=None):
        result = []
        for row in self.store.db.execute(
            "SELECT body FROM development_loop_jobs ORDER BY rowid"
        ):
            job = strict_loads(row[0])
            loop = self.get(job["loop_id"])
            if (
                job["state"] == "pending"
                and loop["status"] == "evaluator_pending"
                and loop["current_job"] == job["id"]
                and (project is None or job["project"] == project)
            ):
                result.append(job)
        return result

    def _correlate_job(self, loop_id, job_id, packet_digest):
        loop, job = self.get(loop_id), self.job(job_id)
        if (
            job["loop_id"] != loop_id
            or job["packet_digest"] != packet_digest
            or loop["current_job"] != job_id
        ):
            raise Conflict("stale evaluator job or evidence packet")
        return loop, job

    def mark_evaluator_started(self, loop_id, job_id, packet_digest, operation_id):
        arguments = {
            "loop_id": loop_id,
            "job_id": job_id,
            "packet_digest": packet_digest,
        }

        def apply():
            loop, job = self._correlate_job(loop_id, job_id, packet_digest)
            if loop["status"] != "evaluator_pending" or job["state"] != "pending":
                raise Conflict("evaluator job is not dispatchable")
            job["state"] = "running"
            self._save_job(job)
            self._advance(loop, "evaluator_running")
            return {"loop": loop, "job": job}

        return self._mutate(operation_id, "evaluator_started", arguments, apply)

    def mark_evaluator_quiet(self, job_id, packet_digest, attempt):
        """Record that a finished attempt's recorded process groups were empty.

        Written by the evaluator scheduler after one process-table observation
        found no member of the runner or harness groups recorded for the
        attempt and no process naming its spool. An empty process group cannot
        regain members, so the restart gate stops reading that attempt's
        groups. It changes no loop or job state; a later attempt needs its own
        observation.
        """
        arguments = {"job_id": job_id, "packet_digest": packet_digest, "attempt": attempt}

        def apply():
            job = self.job(job_id)
            if job["packet_digest"] != packet_digest:
                raise Conflict("stale evaluator job or evidence packet")
            if job["state"] not in FINISHED_EVALUATOR_STATES:
                raise Conflict("evaluator job is not finished")
            prefix = f"evaluator-start:{job_id}:"
            started = [
                int(row[0][len(prefix):])
                for row in self.store.db.execute(
                    "SELECT operation FROM development_loop_receipts "
                    "WHERE operation>=? AND operation<?",
                    (prefix, f"evaluator-start:{job_id};"),
                )
                if row[0][len(prefix):].isdigit()
            ]
            if not started or max(started) != attempt:
                raise Conflict("evaluator attempt is not the latest started attempt")
            return {"job_id": job_id, "attempt": attempt, "state": job["state"]}

        return self._mutate(
            f"evaluator-quiet:{job_id}:{attempt}", "evaluator_quiet", arguments, apply
        )

    def accept_evaluation(self, loop_id, job_id, packet_digest, result, operation_id):
        normalized = normalize_result(result, self.store.contracts)
        arguments = {
            "loop_id": loop_id,
            "job_id": job_id,
            "packet_digest": packet_digest,
            "result": normalized,
        }

        def apply():
            loop, job = self._correlate_job(loop_id, job_id, packet_digest)
            if job["state"] == "completed" and job["result"] == normalized:
                return {
                    "loop": loop,
                    "job": job,
                    "stage": self.stage(loop["current_stage"])
                    if loop["current_stage"]
                    else None,
                }
            if loop["status"] != "evaluator_running" or job["state"] != "running":
                raise Conflict("evaluator result is not current and running")
            job.update(state="completed", result=normalized)
            self._save_job(job)
            evidence_key = digest(normalized["evidence_refs"])
            if loop["round"]:
                loop["no_progress_count"] = (
                    loop["no_progress_count"] + 1
                    if evidence_key == loop["last_evidence_digest"]
                    else 0
                )
            loop["last_evidence_digest"] = evidence_key
            decision = normalized["decision"]
            stage = None
            if decision != "continue":
                self._advance(loop, decision, normalized["assessment"][:4096])
            elif loop["round"] >= loop["max_rounds"]:
                self._advance(loop, "needs_operator", "development round limit reached")
            elif loop["no_progress_count"] >= loop["no_progress_limit"]:
                self._advance(
                    loop,
                    "needs_operator",
                    "evaluator evidence repeated without progress",
                )
            else:
                loop["round"] += 1
                stage = {
                    "schema_version": 1,
                    "id": identifier(),
                    "loop_id": loop_id,
                    "project": loop["project"],
                    "session_id": loop["session_id"],
                    "round": loop["round"],
                    "state": "pending",
                    "prompt": normalized["next_prompt"],
                    "source_job": job_id,
                    "source_packet_digest": packet_digest,
                    "evidence": None,
                    "completion_marker": None,
                    "final_digest": None,
                    "final_text": None,
                    "prompt_id": None,
                    "unknown_from": None,
                    "created_at": now(),
                }
                self._save_stage(stage)
                loop["current_stage"] = stage["id"]
                self._advance(loop, "executive_pending")
            return {"loop": loop, "job": job, "stage": stage}

        return self._mutate(operation_id, "evaluation_result", arguments, apply)

    def pending_stages(self, project, session_id):
        result = []
        for loop in self.for_project(project):
            if (
                loop["session_id"] == session_id
                and loop["status"] == "executive_pending"
            ):
                stage = self.stage(loop["current_stage"])
                if stage["state"] == "pending":
                    result.append(stage)
        return result

    def _correlate_stage(self, loop_id, stage_id, session_id):
        loop, stage = self.get(loop_id), self.stage(stage_id)
        if (
            stage["loop_id"] != loop_id
            or loop["current_stage"] != stage_id
            or stage["session_id"] != session_id
            or loop["session_id"] != session_id
        ):
            raise Conflict("stale development stage or wrong native session")
        return loop, stage

    def claim(self, loop_id, stage_id, session_id, operation_id, *, prompt_id=None):
        arguments = {
            "loop_id": loop_id,
            "stage_id": stage_id,
            "session_id": session_id,
            "prompt_id": prompt_id,
        }

        def apply():
            loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
            if stage["prompt_id"] is not None and prompt_id != stage["prompt_id"]:
                raise Conflict("development stage belongs to a different prompt")
            if loop["status"] == "executive_claimed" and stage["state"] == "claimed":
                return {"loop": loop, "stage": stage}
            if loop["status"] != "executive_pending" or stage["state"] != "pending":
                raise Conflict("development stage is not claimable")
            stage.update(state="claimed", prompt_id=prompt_id)
            self._save_stage(stage)
            self._advance(loop, "executive_claimed")
            return {"loop": loop, "stage": stage}

        return self._mutate(operation_id, "claim", arguments, apply)

    def ready(
        self,
        loop_id,
        stage_id,
        session_id,
        evidence_packet,
        operation_id,
        *,
        prompt_id=None,
    ):
        evidence = self._evidence(evidence_packet)
        from .development_delegation import require_return

        loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
        returned = require_return(self.store, loop, stage)
        if returned:
            evidence = evidence | {"delegation": returned}
        arguments = {
            "loop_id": loop_id,
            "stage_id": stage_id,
            "session_id": session_id,
            "evidence": evidence,
            "prompt_id": prompt_id,
        }
        # File reads happen before the write transaction; the stage's creation
        # time bounds how old a receipt may be.
        try:
            not_before = self.stage(stage_id)["created_at"]
        except Conflict:
            not_before = None
        validation = self._receipt_validation(evidence, loop_id, stage_id, not_before)

        def apply():
            loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
            if stage["prompt_id"] is not None and prompt_id != stage["prompt_id"]:
                raise Conflict("development stage belongs to a different prompt")
            if loop["status"] == "executive_ready" and stage["state"] == "ready":
                if stage["evidence"] != evidence:
                    raise Conflict("ready stage evidence is immutable")
            else:
                if loop["status"] != "executive_claimed" or stage["state"] != "claimed":
                    raise Conflict("claim development stage before ready")
                stage.update(
                    state="ready",
                    evidence=evidence,
                    prompt_id=prompt_id,
                    completion_marker=f"<!-- odin-development-complete:{stage_id}:{secrets.token_hex(16)} -->",
                    receipt_validation=validation,
                )
                self._save_stage(stage)
                self._advance(loop, "executive_ready")
            return {
                "loop": loop,
                "stage": stage,
                "completion_marker": stage["completion_marker"],
                "receipt_validation": stage.get(
                    "receipt_validation",
                    {
                        "status": "legacy_no_receipt",
                        "receipts": [],
                        "problems": [],
                        "commands_succeeded": None,
                    },
                ),
            }

        return self._mutate(operation_id, "ready", arguments, apply)

    def capture_stop(
        self,
        session_id,
        final_text,
        operation_id,
        *,
        prompt_id=None,
        hook_event_name="Stop",
        stop_hook_active=False,
        background_tasks=None,
        session_crons=None,
    ):
        if stop_hook_active:
            return {"captured": False, "reason": "recursive stop hook ignored"}
        if hook_event_name not in {"Stop", "StopFailure"}:
            return {"captured": False, "reason": "unsupported completion hook"}
        if not isinstance(final_text, str) or len(final_text.encode()) > 262144:
            raise Conflict("final response exceeds capture budget")
        if hook_event_name == "StopFailure":
            return self._capture_failure(
                session_id, final_text, operation_id, prompt_id=prompt_id
            )
        footer = final_text.rstrip().split("\n")[-1]
        match = MARKER.fullmatch(footer)
        if match is None:
            return {"captured": False, "reason": "no development completion footer"}
        arguments = {
            "session_id": session_id,
            "final_text": final_text,
            "prompt_id": prompt_id,
            "hook_event_name": hook_event_name,
        }
        validation = None
        try:
            known = self.stage(match[1])
        except Conflict:
            known = None
        if known is not None and known["state"] == "ready":
            validation = self._receipt_validation(
                known["evidence"], known["loop_id"], known["id"], known["created_at"]
            )

        def apply():
            try:
                stage = self.stage(match[1])
            except Conflict:
                return {"captured": False, "reason": "unknown development stage"}
            if (
                stage["session_id"] != session_id
                or stage["completion_marker"] != footer
            ):
                return {
                    "captured": False,
                    "reason": "native session or completion footer mismatch",
                }
            if stage["prompt_id"] is not None and prompt_id != stage["prompt_id"]:
                return {"captured": False, "reason": "native prompt mismatch"}
            loop = self.get(stage["loop_id"])
            final_digest = digest(final_text)
            if stage["state"] == "completed":
                if background_tasks or session_crons:
                    return {
                        "captured": False,
                        "superseded": True,
                        "reason": "background observation superseded by completed stage",
                    }
                if stage["final_digest"] != final_digest:
                    raise Conflict(
                        "completion footer reused for different final response"
                    )
                return {
                    "captured": True,
                    "loop": loop,
                    "stage": stage,
                    "duplicate": True,
                }
            if loop["status"] == "paused" and stage["state"] == "ready":
                raise Conflict("development loop paused; retain completion for retry")
            if background_tasks or session_crons:
                raise Conflict("pending background work; retain completion for retry")
            if (
                loop["status"] != "executive_ready"
                or stage["state"] != "ready"
                or loop["current_stage"] != stage["id"]
            ):
                return {"captured": False, "reason": "development stage is not ready"}
            previous = self.job(stage["source_job"])["result"]
            stage.update(
                state="completed",
                final_text=final_text,
                final_digest=final_digest,
                prompt_id=prompt_id,
            )
            self._save_stage(stage)
            self._advance(loop, "evaluator_pending")
            job = self._queue_evaluator(
                loop,
                stage["evidence"],
                final_text,
                previous,
                receipt_validation=validation,
            )
            return {
                "captured": True,
                "loop": loop,
                "stage": stage,
                "job": job,
                "duplicate": False,
            }

        return self._mutate(operation_id, "capture_stop", arguments, apply)

    def _capture_failure(self, session_id, final_text, operation_id, *, prompt_id):
        # StopFailure often has no assistant final response or footer. It cannot
        # complete a stage; conservatively hold the active native session instead.
        arguments = {
            "session_id": session_id,
            "final_text": final_text,
            "prompt_id": prompt_id,
        }

        def apply():
            for row in self.store.db.execute(
                "SELECT body FROM development_loops WHERE active=1"
            ):
                loop = strict_loads(row[0])
                if loop["session_id"] != session_id or not loop["current_stage"]:
                    continue
                stage = self.stage(loop["current_stage"])
                if stage["state"] not in {"claimed", "ready"}:
                    continue
                if stage["prompt_id"] is not None and stage["prompt_id"] != prompt_id:
                    continue
                if loop["status"] not in {
                    "executive_claimed",
                    "executive_ready",
                    "paused",
                }:
                    continue
                stage.update(unknown_from=stage["state"], state="unknown")
                self._save_stage(stage)
                target = "paused" if loop["status"] == "paused" else "unknown"
                if target == "paused":
                    loop["paused_from"] = "unknown"
                self._advance(
                    loop,
                    target,
                    "native executive StopFailure; reconcile before continuing",
                )
                return {
                    "captured": False,
                    "held": True,
                    "reason": "native executive StopFailure",
                    "loop": loop,
                    "stage": stage,
                }
            return {
                "captured": False,
                "held": False,
                "reason": "no correlated active native stage",
            }

        return self._mutate(operation_id, "capture_failure", arguments, apply)

    def continue_after_intervention(
        self,
        loop_id,
        response,
        operation_id,
        *,
        expected_revision,
        evidence_packet=None,
    ):
        """Re-evaluate an answered intervention without replaying executive work.

        The gateway supplies operator authority. This transition only answers a
        completed evaluator's needs_operator decision; execution uncertainty and
        failed evaluators require their existing reconciliation paths.
        """
        if (
            not isinstance(response, str)
            or not response.strip()
            or len(response.encode()) > 12000
        ):
            raise Conflict(
                "operator response must be nonblank within 12000 UTF-8 bytes"
            )
        if type(expected_revision) is not int or expected_revision < 1:
            raise Conflict("positive expected development loop revision required")
        evidence = self._evidence({} if evidence_packet is None else evidence_packet)
        arguments = {
            "loop_id": loop_id,
            "expected_revision": expected_revision,
            "response": response,
            "evidence": evidence,
        }

        def apply():
            loop = self.get(loop_id)
            if loop["revision"] != expected_revision:
                raise Conflict("stale development loop revision")
            if loop["status"] != "needs_operator":
                raise Conflict("only an evaluator intervention can continue")
            if loop["round"] >= loop["max_rounds"]:
                raise Conflict("development round limit reached")
            if not loop["current_job"]:
                raise Conflict("completed evaluator intervention required")
            source = self.job(loop["current_job"])
            if (
                source["loop_id"] != loop_id
                or source["state"] != "completed"
                or source["result"] is None
                or source["result"]["decision"] != "needs_operator"
            ):
                raise Conflict("completed evaluator intervention required")
            if any(
                strict_loads(row[0])["state"] != "completed"
                for row in self.store.db.execute(
                    "SELECT body FROM development_loop_stages WHERE loop_id=?",
                    (loop_id,),
                )
            ):
                raise Conflict("outstanding executive stage must be reconciled")
            intervention = {
                "operation_id": operation_id,
                "source_job": source["id"],
                "source_packet_digest": source["packet_digest"],
                "response": response,
                "evidence": evidence,
            }
            self._advance(loop, "evaluator_pending")
            packet = source["packet"]
            job = self._queue_evaluator(
                loop,
                packet["evidence"],
                packet["executive_final_text"],
                source["result"],
                packet.get("receipt_validation"),
                operator_response=intervention,
            )
            return {"loop": loop, "job": job}

        return self._mutate(operation_id, "operator_continue", arguments, apply)

    def control(self, loop_id, action, operation_id, *, expected_revision=None):
        if action not in {"pause", "resume", "stop"}:
            raise Conflict("unknown development control")
        arguments = {
            "loop_id": loop_id,
            "action": action,
            "expected_revision": expected_revision,
        }

        def apply():
            loop = self.get(loop_id)
            if expected_revision is not None and loop["revision"] != expected_revision:
                raise Conflict("stale development loop revision")
            if loop["status"] in FINAL:
                if action == "stop" and loop["status"] == "stopped":
                    return {"loop": loop, "external_process_stop_required": True}
                raise Conflict("development loop is terminal")
            if action == "pause":
                if loop["status"] != "paused":
                    loop["paused_from"] = loop["status"]
                    self._advance(loop, "paused", "operator paused development loop")
            elif action == "resume":
                if loop["status"] != "paused":
                    raise Conflict("only a paused development loop can resume")
                target = loop["paused_from"]
                loop["paused_from"] = None
                self._advance(loop, target)
            else:
                if loop["current_job"]:
                    job = self.job(loop["current_job"])
                    if job["state"] in {
                        "pending",
                        "running",
                        "unknown",
                        "lost",
                        "blocked",
                    }:
                        job["state"] = "cancelled"
                        self._save_job(job)
                if loop["current_stage"]:
                    stage = self.stage(loop["current_stage"])
                    if stage["state"] != "completed":
                        stage["state"] = "cancelled"
                        self._save_stage(stage)
                loop["paused_from"] = None
                self._advance(loop, "stopped", "operator stopped development loop")
            return {"loop": loop, "external_process_stop_required": action == "stop"}

        return self._mutate(operation_id, "control", arguments, apply)

    def handover(
        self,
        loop_id,
        from_session,
        to_session,
        reason,
        operation_id,
        *,
        expected_revision,
        actor,
    ):
        """Operator transfer of a loop's native-session ownership, in one commit.

        Only the operator gateway supplies the authority; this method checks the
        record. A claimed, ready or unknown executive stage is never moved: its
        native process may still hold it, so the operator reconciles or stops
        first. A handover grants no rounds, resumes no paused loop and answers
        no needs_operator.
        """
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise Conflict("explicit handover reason required")
        if type(expected_revision) is not int or expected_revision < 1:
            raise Conflict("positive expected development loop revision required")
        try:
            if (
                not isinstance(to_session, str)
                or str(uuid.UUID(to_session)) != to_session
            ):
                raise ValueError("noncanonical UUID")
        except (ValueError, AttributeError) as error:
            raise Conflict("canonical native session UUID required") from error
        arguments = {
            "loop_id": loop_id,
            "from_session": from_session,
            "to_session": to_session,
            "expected_revision": expected_revision,
            "reason": reason,
            "actor": actor,
        }

        def apply():
            loop = self.get(loop_id)
            if loop["status"] in FINAL:
                raise Refused("loop_terminal")
            if loop["revision"] != expected_revision:
                raise Refused("stale_loop_revision")
            if loop["session_id"] != from_session:
                raise Refused("handover_source_mismatch")
            if to_session == from_session:
                raise Refused("handover_same_session")
            if any(
                strict_loads(row[0])["session_id"] == to_session
                for row in self.store.db.execute(
                    "SELECT body FROM development_loops WHERE active=1 AND id<>?",
                    (loop_id,),
                )
            ):
                raise Refused("target_session_has_active_loop")
            # A stage the old native process may still be running is never
            # moved; reconcile it first (loop_hold + loop_reconcile) or stop.
            in_progress = {"executive_claimed", "executive_ready", "unknown"}
            if loop["status"] in in_progress or (
                loop["status"] == "paused" and loop["paused_from"] in in_progress
            ):
                raise Refused("executive_stage_in_progress")
            # History is the authority for prior owners; the bounded list is
            # a convenience view, oldest first.
            loop["previous_session_ids"] = (
                (loop.get("previous_session_ids") or []) + [from_session]
            )[-16:]
            loop.update(session_id=to_session, revision=loop["revision"] + 1, updated_at=now())
            self._save_loop(loop)
            stage = None
            if loop["current_stage"]:
                candidate = self.stage(loop["current_stage"])
                if candidate["state"] == "pending":
                    # Re-addressed, never re-created: the new revision makes the
                    # successor's delivery identity fresh and the old offer stale.
                    candidate["session_id"] = to_session
                    self._save_stage(candidate)
                    stage = candidate
            notices = []
            for row in self.store.db.execute(
                "SELECT body FROM development_loop_notices "
                "WHERE loop_id=? AND state='pending' ORDER BY rowid",
                (loop_id,),
            ):
                notice = strict_loads(row[0])
                notice.update(session_id=to_session, first_offered_at=None)
                self.store.contracts.validate("development-loop-notice", notice)
                self.store.db.execute(
                    "UPDATE development_loop_notices SET session_id=?,body=? WHERE id=?",
                    (to_session, canonical(notice), notice["id"]),
                )
                notices.append(notice["id"])
            self.store._history(
                "development_loop.handed_over",
                {
                    "loop_id": loop_id,
                    "project": loop["project"],
                    "from_session": from_session,
                    "to_session": to_session,
                    "revision": loop["revision"],
                    "actor": actor,
                    "reason": reason,
                },
            )
            return {"loop": loop, "stage": stage, "reoffered_notices": notices}

        return self._mutate(operation_id, "handover", arguments, apply)

    def predecessor_session(self, session_id, project):
        """The session that most recently handed a loop in ``project`` to
        ``session_id``.

        The recorded ``development_loop.handed_over`` history events are the
        authority, not the loop's ``previous_session_ids`` view.
        """
        row = self.store.db.execute(
            "SELECT body FROM history "
            "WHERE json_extract(body,'$.kind')='development_loop.handed_over' "
            "AND json_extract(body,'$.payload.to_session')=? "
            "AND json_extract(body,'$.payload.project')=? "
            "ORDER BY seq DESC LIMIT 1",
            (session_id, project),
        ).fetchone()
        return strict_loads(row[0])["payload"]["from_session"] if row else None

    def configure_delegation(
        self, loop_id, stage_id, session_id, profile, operation_id, *, expected_revision
    ):
        """Opt a paused, untouched executive stage into required delegation.

        The current stage and executive claim remain intact. The profile only
        affects future delegation admission and ready checks after resume.
        """
        if type(expected_revision) is not int or expected_revision < 1:
            raise Conflict("expected development loop revision required")
        arguments = {
            "loop_id": loop_id,
            "stage_id": stage_id,
            "session_id": session_id,
            "delegation_profile": profile,
            "expected_revision": expected_revision,
        }

        def apply():
            from .development_delegation import binding

            loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
            if loop["revision"] != expected_revision:
                raise Conflict("stale development loop revision")
            if loop["status"] != "paused" or loop["paused_from"] not in {
                "executive_pending", "executive_claimed"
            }:
                raise Conflict("pause an unfinished executive stage before configuring delegation")
            if stage["state"] != {
                "executive_pending": "pending", "executive_claimed": "claimed"
            }[loop["paused_from"]]:
                raise Conflict("paused stage state does not match its executive phase")
            if loop.get("delegation_profile") is not None:
                raise Conflict("existing delegation profile cannot be replaced")
            if binding(self.store, stage_id) is not None:
                raise Conflict("stage already has a delegated assignment")
            if any(stage.get(key) is not None for key in (
                "evidence", "completion_marker", "final_digest", "final_text", "receipt_validation"
            )):
                raise Conflict("stage already has completion evidence")
            if self.store.db.execute(
                "SELECT 1 FROM delegation_turns WHERE project=? "
                "AND state IN ('queued','launching','running','interrupting') LIMIT 1",
                (loop["project"],),
            ).fetchone():
                raise Conflict("project has an active delegated turn")
            if self.store.db.execute(
                "SELECT 1 FROM delegation_turns WHERE project=? AND state='lost' LIMIT 1",
                (loop["project"],),
            ).fetchone():
                raise Conflict("project has a lost delegated turn with unknown native outcome")
            if self.store.db.execute(
                "SELECT 1 FROM development_loop_jobs AS j "
                "JOIN development_loops AS l ON l.id=j.loop_id WHERE l.project=? "
                "AND json_extract(j.body,'$.state') IN ('pending','running','unknown','lost') LIMIT 1",
                (loop["project"],),
            ).fetchone():
                raise Conflict("project has an active or unresolved evaluator job")
            loop["delegation_profile"] = profile
            loop["revision"] += 1
            loop["updated_at"] = now()
            self._save_loop(loop)
            self.store._history("development_loop.delegation_configured", {
                "loop_id": loop_id,
                "stage_id": stage_id,
                "session_id": session_id,
                "revision": loop["revision"],
                "delegation_profile": profile,
            })
            return {"loop": loop, "stage": stage}

        return self._mutate(operation_id, "configure_delegation", arguments, apply)

    def fail_pending_evaluator(
        self, loop_id, job_id, packet_digest, operation_id, *, reason
    ):
        """Record preparation refusal without implying a model process started."""
        if not isinstance(reason, str) or not reason or len(reason) > 4096:
            raise Conflict("explicit evaluator preparation failure required")
        arguments = {
            "loop_id": loop_id,
            "job_id": job_id,
            "packet_digest": packet_digest,
            "reason": reason,
        }

        def apply():
            loop, job = self._correlate_job(loop_id, job_id, packet_digest)
            if loop["status"] != "evaluator_pending" or job["state"] != "pending":
                raise Conflict(
                    "only a pending evaluator can be blocked before dispatch"
                )
            job.update(state="blocked", failure_reason=reason)
            self._save_job(job)
            self._advance(loop, "needs_operator", reason)
            return {"loop": loop, "job": job, "model_started": False}

        return self._mutate(
            operation_id, "evaluator_preparation_failed", arguments, apply
        )

    def fail_evaluator(
        self, loop_id, job_id, packet_digest, operation_id, *, outcome, reason
    ):
        if (
            outcome not in {"lost", "unknown"}
            or not isinstance(reason, str)
            or not reason
            or len(reason) > 4096
        ):
            raise Conflict("explicit evaluator loss or unknown outcome required")
        arguments = {
            "loop_id": loop_id,
            "job_id": job_id,
            "packet_digest": packet_digest,
            "outcome": outcome,
            "reason": reason,
        }

        def apply():
            loop, job = self._correlate_job(loop_id, job_id, packet_digest)
            if loop["status"] != "evaluator_running" or job["state"] != "running":
                raise Conflict("only a running evaluator can become lost or unknown")
            job.update(state=outcome, failure_reason=reason)
            self._save_job(job)
            self._advance(
                loop, "unknown" if outcome == "unknown" else "needs_operator", reason
            )
            return {"loop": loop, "job": job}

        return self._mutate(operation_id, "evaluator_failed", arguments, apply)

    def reconcile_evaluator(
        self, loop_id, job_id, packet_digest, operation_id, *, observed
    ):
        """Trusted runner supplies observation; unknown is never blindly retried."""
        if observed not in {"running", "not_started", "lost"}:
            raise Conflict("explicit evaluator process observation required")
        arguments = {
            "loop_id": loop_id,
            "job_id": job_id,
            "packet_digest": packet_digest,
            "observed": observed,
        }

        def apply():
            loop, job = self._correlate_job(loop_id, job_id, packet_digest)
            if loop["status"] != "unknown" or job["state"] != "unknown":
                raise Conflict("only an unknown evaluator can be reconciled")
            job["state"] = {
                "running": "running",
                "not_started": "pending",
                "lost": "lost",
            }[observed]
            job["failure_reason"] = (
                None if observed != "lost" else "evaluator process confirmed lost"
            )
            self._save_job(job)
            self._advance(
                loop,
                {
                    "running": "evaluator_running",
                    "not_started": "evaluator_pending",
                    "lost": "needs_operator",
                }[observed],
                job["failure_reason"],
            )
            return {"loop": loop, "job": job}

        return self._mutate(operation_id, "evaluator_reconciled", arguments, apply)

    def mark_execution_unknown(
        self, loop_id, stage_id, session_id, operation_id, *, reason
    ):
        if not isinstance(reason, str) or not reason or len(reason) > 4096:
            raise Conflict("explicit execution uncertainty reason required")
        arguments = {
            "loop_id": loop_id,
            "stage_id": stage_id,
            "session_id": session_id,
            "reason": reason,
        }

        def apply():
            loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
            if loop["status"] not in {
                "executive_pending",
                "executive_claimed",
                "executive_ready",
            }:
                raise Conflict("executive stage is not active")
            stage.update(unknown_from=stage["state"], state="unknown")
            self._save_stage(stage)
            self._advance(loop, "unknown", reason)
            return {"loop": loop, "stage": stage}

        return self._mutate(operation_id, "execution_unknown", arguments, apply)

    def reconcile_execution(
        self, loop_id, stage_id, session_id, operation_id, *, observed
    ):
        """Restore a stage only after a trusted native-session observation."""
        if observed not in {"running", "not_started", "lost"}:
            raise Conflict("explicit native session observation required")
        arguments = {
            "loop_id": loop_id,
            "stage_id": stage_id,
            "session_id": session_id,
            "observed": observed,
        }

        def apply():
            loop, stage = self._correlate_stage(loop_id, stage_id, session_id)
            if loop["status"] != "unknown" or stage["state"] != "unknown":
                raise Conflict("only unknown execution can be reconciled")
            if observed == "lost":
                self._advance(
                    loop, "needs_operator", "native executive stage confirmed lost"
                )
            else:
                prior = stage["unknown_from"]
                if observed == "running" and prior == "pending":
                    raise Conflict("native execution has not claimed the pending stage")
                stage["state"] = "pending" if observed == "not_started" else prior
                stage["unknown_from"] = None
                if observed == "not_started":
                    stage.update(completion_marker=None, evidence=None, prompt_id=None)
                self._save_stage(stage)
                self._advance(
                    loop,
                    {
                        "pending": "executive_pending",
                        "claimed": "executive_claimed",
                        "ready": "executive_ready",
                    }[stage["state"]],
                )
            return {"loop": loop, "stage": stage}

        return self._mutate(operation_id, "execution_reconciled", arguments, apply)
