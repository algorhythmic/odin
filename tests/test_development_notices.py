"""Synthetic notices, acknowledgement and deadline attention; no live loop or model."""

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta

from odin.contracts import canonical, identifier
from odin.coordination import Actor
from odin.development_loop import MARKER, DevelopmentLoop, normalize_deadlines
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict, Store
from test_memory import P, project

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "22222222-2222-4222-8222-222222222222"


def verdict(decision="continue", prompt="Run the next bounded challenge"):
    return {
        "decision": decision,
        "assessment": "Synthetic independent assessment",
        "findings": ["A bounded local observation"],
        "next_prompt": prompt if decision == "continue" else "",
        "evidence_refs": [
            {"ref": "fixture:result", "revision": "1", "digest": "a" * 64}
        ],
    }


def later(stamp, seconds):
    base = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    return (base + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class NoticeControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.addCleanup(self.store.close)
        self.store.create(project(P, "Development"))
        self.loops = DevelopmentLoop(self.store)

    def start(self, **kwargs):
        return self.loops.start(P, "Exercise notices", SESSION, identifier(), **kwargs)

    def evaluate(self, job, result=None):
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        return self.loops.accept_evaluation(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            result or verdict(),
            identifier(),
        )

    def finish(self, stage):
        self.loops.claim(stage["loop_id"], stage["id"], SESSION, identifier())
        ready = self.loops.ready(
            stage["loop_id"], stage["id"], SESSION, {"r": 1}, identifier()
        )
        return self.loops.capture_stop(
            SESSION, "Done\n" + ready["completion_marker"], identifier()
        )

    def test_completion_notice_is_atomic_deterministic_and_available_after_end(self):
        started = self.start()
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        result = self.evaluate(captured["job"], verdict("complete"))
        loop = result["loop"]
        self.assertEqual(loop["status"], "complete")
        notices = self.loops.pending_notices(P, SESSION)
        self.assertEqual(len(notices), 1)
        notice = notices[0]
        self.assertEqual(notice["kind"], "completion")
        self.assertEqual(
            notice["transition"],
            {
                "from": "evaluator_running",
                "to": "complete",
                "loop_revision": loop["revision"],
            },
        )
        self.assertEqual(notice["loop_id"], loop["id"])
        self.assertEqual(notice["session_id"], SESSION)
        self.assertEqual(notice["job_id"], loop["current_job"])
        self.assertEqual(notice["stage_id"], stage["id"])
        self.assertEqual(notice["stage_state"], "completed")
        self.assertEqual(notice["assessment"], "Synthetic independent assessment")
        self.assertEqual(notice["decision"], "complete")
        self.assertIsNone(MARKER.search(canonical(notice)))
        self.assertEqual(notice["state"], "pending")
        self.assertIsNone(notice["first_offered_at"])
        self.store.contracts.validate("development-loop-notice", notice)
        # The loop is terminal, yet its notice stays deliverable; and the
        # deterministic identity means a repeated transition cannot duplicate it.
        self.assertFalse(self.loops.pending_stages(P, SESSION))
        again = self.loops.accept_evaluation(
            loop["id"],
            loop["current_job"],
            captured["job"]["packet_digest"],
            verdict("complete"),
            identifier(),
        )
        self.assertEqual(again["loop"]["revision"], loop["revision"])
        self.assertEqual(len(self.loops.notices(loop["id"])), 1)
        events = [
            row
            for row in self.store.db.execute("SELECT body FROM history")
            if '"development_loop.notice"' in row[0]
        ]
        self.assertEqual(len(events), 1)

    def test_intervention_failure_and_stop_notices(self):
        started = self.start(max_rounds=1)
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        result = self.evaluate(captured["job"])  # round limit reached
        self.assertEqual(result["loop"]["status"], "needs_operator")
        kinds = [n["kind"] for n in self.loops.notices(result["loop"]["id"])]
        self.assertEqual(kinds, ["intervention"])
        intervention = self.loops.notices(result["loop"]["id"])[0]
        self.assertIn("operator decision or reconciliation", intervention["attention"])
        self.loops.control(result["loop"]["id"], "stop", identifier())
        kinds = sorted(n["kind"] for n in self.loops.notices(result["loop"]["id"]))
        self.assertEqual(kinds, ["intervention", "stopped"])
        stopped = next(
            n
            for n in self.loops.notices(result["loop"]["id"])
            if n["kind"] == "stopped"
        )
        self.assertIn("were not terminated by this", stopped["attention"])
        # A lost evaluator is a failure notice on a fresh loop.
        self.store.close()
        self.store = Store(self.temp.name)
        self.loops = DevelopmentLoop(self.store)
        started = self.loops.start(P, "Second", SESSION, identifier())
        job = started["job"]
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        failed = self.loops.fail_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            outcome="lost",
            reason="runner died",
        )
        notice = self.loops.notices(failed["loop"]["id"])[0]
        self.assertEqual(notice["kind"], "failure")
        self.assertIn("runner died", notice["summary"])
        pending = self.loops.pending_notices(P, SESSION)
        self.assertEqual(
            [n["kind"] for n in pending], ["intervention", "stopped", "failure"]
        )

    def test_acknowledgement_is_scoped_idempotent_and_powerless(self):
        started = self.start()
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        loop = self.evaluate(captured["job"], verdict("complete"))["loop"]
        notice = self.loops.pending_notices(P, SESSION)[0]
        with self.assertRaises(Conflict):
            self.loops.acknowledge(
                notice["id"], P, OTHER_SESSION, identifier(), actor="fable-executive"
            )
        with self.assertRaises(Conflict):
            self.loops.acknowledge(
                notice["id"],
                "01K7M000000000000000000009",
                SESSION,
                identifier(),
                actor="fable-executive",
            )
        operation = identifier()
        first = self.loops.acknowledge(
            notice["id"], P, SESSION, operation, actor="fable-executive"
        )
        self.assertEqual(first["notice"]["state"], "acknowledged")
        self.assertEqual(
            first["notice"]["acknowledgement_authority"],
            "model_attributed_not_operator_approval",
        )
        self.assertEqual(
            first,
            self.loops.acknowledge(
                notice["id"], P, SESSION, operation, actor="fable-executive"
            ),
        )
        second = self.loops.acknowledge(
            notice["id"], P, SESSION, identifier(), actor="fable-executive"
        )
        self.assertEqual(
            second["notice"]["acknowledged_at"], first["notice"]["acknowledged_at"]
        )
        self.assertEqual(self.loops.pending_notices(P, SESSION), [])
        self.assertEqual(self.loops.get(loop["id"])["status"], "complete")
        self.assertEqual(self.loops.get(loop["id"])["revision"], loop["revision"])
        self.assertEqual(
            self.loops.notice_counts(loop["id"]),
            {"pending": 0, "acknowledged": 1, "unoffered": 0},
        )

    def test_offer_is_recorded_once_and_polls_write_nothing(self):
        started = self.start()
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        self.evaluate(captured["job"], verdict("complete"))
        notice = self.loops.pending_notices(P, SESSION)[0]
        self.assertEqual(
            self.loops.mark_offered([notice["id"]], at="2026-01-01T00:00:00.000000Z"),
            [notice["id"]],
        )
        self.assertEqual(self.loops.mark_offered([notice["id"]]), [])
        self.assertEqual(
            self.loops.notice(notice["id"])["first_offered_at"],
            "2026-01-01T00:00:00.000000Z",
        )

    def test_deadlines_are_normalized_and_disabled_by_default(self):
        self.assertEqual(
            normalize_deadlines(None),
            {
                k: None
                for k in (
                    "offer_seconds",
                    "claim_seconds",
                    "ready_seconds",
                    "evaluator_seconds",
                )
            },
        )
        with self.assertRaises(Conflict):
            normalize_deadlines({"offer_seconds": 0})
        with self.assertRaises(Conflict):
            normalize_deadlines({"bogus": 1})
        with self.assertRaises(Conflict):
            normalize_deadlines({"offer_seconds": True})
        loop = self.start()["loop"]
        self.assertIsNone(loop["attention"])
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 10**6), force=True),
            [],
        )

    def test_unanswered_offer_raises_attention_once_without_changing_the_loop(self):
        started = self.start(deadlines={"offer_seconds": 60})
        stage = self.evaluate(started["job"])["stage"]
        loop = self.loops.get(stage["loop_id"])
        self.assertEqual(loop["status"], "executive_pending")
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 60), force=True), []
        )
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], -600), force=True),
            [],
        )  # clock moved back
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 61), force=True),
            [loop["id"]],
        )
        observed = self.loops.get(loop["id"])
        self.assertEqual(
            observed["status"], "executive_pending"
        )  # no redispatch, no new round
        self.assertEqual(observed["revision"], loop["revision"])
        self.assertEqual(observed["current_stage"], stage["id"])
        self.assertEqual(observed["attention"]["observed"], "offer_unanswered")
        self.assertEqual(observed["attention"]["elapsed_seconds"], 61)
        self.assertEqual(observed["attention"]["deadline_seconds"], 60)
        stalled = self.loops.notice(observed["attention"]["notice_id"])
        self.assertEqual(stalled["kind"], "stalled")
        self.assertEqual(stalled["observed"], "offer_unanswered")
        self.assertIn("does not prove work did not start", stalled["attention"])
        # Repeated checks observe nothing new: no second notice, no history growth.
        before = self.store.db.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        for seconds in (62, 600, 86400):
            self.assertEqual(
                self.loops.check_attention(
                    at=later(loop["updated_at"], seconds), force=True
                ),
                [],
            )
        self.assertEqual(
            self.store.db.execute("SELECT COUNT(*) FROM history").fetchone()[0], before
        )
        self.assertEqual(len(self.loops.notices(loop["id"])), 1)
        # The stage is still claimable: a late claim proceeds and clears attention.
        self.assertEqual(self.loops.pending_stages(P, SESSION)[0]["id"], stage["id"])
        claimed = self.loops.claim(loop["id"], stage["id"], SESSION, identifier())
        self.assertIsNone(claimed["loop"]["attention"])
        self.assertEqual(claimed["loop"]["status"], "executive_claimed")
        self.assertEqual(
            self.loops.notice(stalled["id"])["state"], "pending"
        )  # still deliverable history

    def test_claimed_ready_and_evaluator_stalls_are_observed_separately(self):
        started = self.start(
            deadlines={
                "claim_seconds": 10,
                "ready_seconds": 20,
                "evaluator_seconds": 30,
            }
        )
        job = started["job"]
        self.assertEqual(
            self.loops.check_attention(
                at=later(started["loop"]["updated_at"], 31), force=True
            ),
            [started["loop"]["id"]],
        )
        self.assertEqual(
            self.loops.get(job["loop_id"])["attention"]["observed"], "evaluator_stalled"
        )
        stage = self.evaluate(job)["stage"]
        loop = self.loops.get(stage["loop_id"])
        self.assertIsNone(loop["attention"])
        claimed = self.loops.claim(loop["id"], stage["id"], SESSION, identifier())[
            "loop"
        ]
        self.assertEqual(
            self.loops.check_attention(at=later(claimed["updated_at"], 11), force=True),
            [loop["id"]],
        )
        self.assertEqual(
            self.loops.get(loop["id"])["attention"]["observed"], "claimed_stalled"
        )
        ready = self.loops.ready(
            loop["id"], stage["id"], SESSION, {"r": 1}, identifier()
        )
        self.assertIsNone(ready["loop"]["attention"])
        self.assertEqual(
            self.loops.check_attention(
                at=later(ready["loop"]["updated_at"], 21), force=True
            ),
            [loop["id"]],
        )
        self.assertEqual(
            self.loops.get(loop["id"])["attention"]["observed"], "ready_uncaptured"
        )
        # A late capture still completes the stage; existing protections remain.
        captured = self.loops.capture_stop(
            SESSION, "Late\n" + ready["completion_marker"], identifier()
        )
        self.assertTrue(captured["captured"])
        self.assertIsNone(captured["loop"]["attention"])
        kinds = [n["observed"] for n in self.loops.notices(loop["id"])]
        self.assertEqual(
            sorted(kinds), ["claimed_stalled", "evaluator_stalled", "ready_uncaptured"]
        )

    def test_pause_suspends_and_resume_restarts_timing(self):
        started = self.start(deadlines={"offer_seconds": 10})
        stage = self.evaluate(started["job"])["stage"]
        loop = self.loops.get(stage["loop_id"])
        self.loops.control(loop["id"], "pause", identifier())
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 10**5), force=True),
            [],
        )
        resumed = self.loops.control(loop["id"], "resume", identifier())["loop"]
        self.assertEqual(
            self.loops.check_attention(at=later(resumed["updated_at"], 5), force=True),
            [],
        )
        self.assertEqual(
            self.loops.check_attention(at=later(resumed["updated_at"], 11), force=True),
            [loop["id"]],
        )
        # Unknown and intervention-bound loops are never timed.
        held = self.loops.mark_execution_unknown(
            loop["id"],
            stage["id"],
            SESSION,
            identifier(),
            reason="operator saw an interrupt",
        )
        self.assertIsNone(held["loop"]["attention"])
        self.assertEqual(
            self.loops.check_attention(
                at=later(held["loop"]["updated_at"], 10**5), force=True
            ),
            [],
        )

    def test_deadline_edits_are_not_transitions(self):
        started = self.start(deadlines={"offer_seconds": 10})
        stage = self.evaluate(started["job"])["stage"]
        loop = self.loops.get(stage["loop_id"])
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 11), force=True),
            [loop["id"]],
        )
        stalled_first = self.loops.get(loop["id"])["attention"]["notice_id"]
        # Changing an unrelated deadline keeps status, revision, timing, attention and delivery identity.
        changed = self.loops.set_deadlines(
            loop["id"],
            {"offer_seconds": 10, "claim_seconds": 5},
            identifier(),
            expected_revision=loop["revision"],
        )["loop"]
        self.assertEqual(
            (changed["status"], changed["revision"], changed["updated_at"]),
            (loop["status"], loop["revision"], loop["updated_at"]),
        )
        self.assertEqual(changed["attention"]["notice_id"], stalled_first)
        self.assertEqual(len(self.loops.notices(loop["id"])), 1)
        # Changing the governing deadline clears the observation; a later re-observation
        # under the new limit gets its own notice, and repeated checks still write nothing.
        changed = self.loops.set_deadlines(
            loop["id"],
            {"offer_seconds": 20},
            identifier(),
            expected_revision=loop["revision"],
        )["loop"]
        self.assertIsNone(changed["attention"])
        self.assertEqual(changed["revision"], loop["revision"])
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 15), force=True), []
        )
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 21), force=True),
            [loop["id"]],
        )
        self.assertNotEqual(
            self.loops.get(loop["id"])["attention"]["notice_id"], stalled_first
        )
        self.assertEqual(len(self.loops.notices(loop["id"])), 2)
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 22), force=True), []
        )
        # An intervention-bound loop gains no spurious notice from a deadline edit.
        self.loops.control(loop["id"], "stop", identifier())
        self.store.close()
        self.store = Store(self.temp.name)
        self.loops = DevelopmentLoop(self.store)
        started = self.loops.start(P, "Second", SESSION, identifier(), max_rounds=1)
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        held = self.evaluate(captured["job"])["loop"]
        self.assertEqual(held["status"], "needs_operator")
        self.loops.set_deadlines(held["id"], {"offer_seconds": 5}, identifier())
        self.assertEqual(
            [n["kind"] for n in self.loops.notices(held["id"])], ["intervention"]
        )
        with self.assertRaises(Conflict):
            self.loops.set_deadlines(
                held["id"],
                {"offer_seconds": 5},
                identifier(),
                expected_revision=held["revision"] + 1,
            )
        self.loops.control(held["id"], "stop", identifier())
        with self.assertRaises(Conflict):
            self.loops.set_deadlines(held["id"], {"offer_seconds": 5}, identifier())

    def test_quoted_completion_footer_is_redacted_and_never_blocks_delivery(self):
        started = self.start()
        stage = self.evaluate(started["job"])["stage"]
        captured = self.finish(stage)
        marker = self.loops.stage(stage["id"])["completion_marker"]
        quoting = verdict("complete")
        quoting["assessment"] = "The response ended with " + marker + " as required."
        loop = self.evaluate(captured["job"], quoting)["loop"]
        notice = self.loops.pending_notices(P, SESSION)[0]
        self.assertIsNone(MARKER.search(canonical(notice)))
        self.assertIn("[completion footer redacted]", notice["assessment"])
        self.assertIn("[completion footer redacted]", notice["summary"])
        self.assertEqual(
            loop["reason"], quoting["assessment"]
        )  # the loop record itself is unchanged

    def test_records_without_deadline_fields_remain_valid_and_untimed(self):
        loop = self.start()["loop"]
        with self.store.transaction():
            body = self.loops.get(loop["id"])
            body.pop("deadlines")
            body.pop("attention")
            self.store.contracts.validate("development-loop", body)
            self.store.db.execute(
                "UPDATE development_loops SET body=? WHERE id=?",
                (canonical(body), loop["id"]),
            )
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 10**6), force=True),
            [],
        )
        stage = self.evaluate(self.loops.job(loop["current_job"]))["stage"]
        self.assertEqual(stage["state"], "pending")

    def test_tick_throttle_without_controlled_clock(self):
        self.start(deadlines={"evaluator_seconds": 1})
        self.assertEqual(
            self.loops.check_attention(), []
        )  # first real-clock check runs, nothing elapsed
        self.assertEqual(self.loops.check_attention(), [])  # throttled


class NoticeGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = prepare_project(self.temp.name)
        self.other = prepare_project(self.temp.name)
        self.service = Service(self.temp.name)
        self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.session = str(uuid.uuid4())
        self.operator = GatewayContext("terminal", Actor("operator", "test"))

    def command(self, action, payload, operation=None):
        return {
            "schema_version": 1,
            "operation_id": operation or identifier(),
            "action": action,
            "payload": {"project": self.project} | payload,
        }

    def send(self, action, payload, operation=None, *, executive=False):
        command = self.command(action, payload, operation)
        if executive:
            return submit_executive(self.gateway, {"command": command}, self.project)[
                "result"
            ]
        return self.gateway.submit(command, context=self.operator)["result"]

    def complete_a_loop(self, **start):
        result = self.send(
            "loop_start", {"goal": "Notice test", "session_id": self.session} | start
        )
        loop_id, job = result["loop"]["id"], result["job"]
        core = self.gateway.development_loop
        core.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], identifier()
        )
        stage = core.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], verdict(), identifier()
        )["stage"]
        self.send(
            "loop_claim",
            {"loop_id": loop_id, "stage_id": stage["id"], "session_id": self.session},
            executive=True,
        )
        ready = self.send(
            "loop_ready",
            {
                "loop_id": loop_id,
                "stage_id": stage["id"],
                "session_id": self.session,
                "evidence_packet": {"r": 1},
            },
            executive=True,
        )
        captured = self.send(
            "loop_capture",
            {
                "session_id": self.session,
                "hook_event_name": "Stop",
                "last_assistant_message": "Done\n" + ready["completion_marker"],
            },
            executive=True,
        )
        job = core.job(captured["job"]["id"])
        core.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], identifier()
        )
        core.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], verdict("complete"), identifier()
        )
        return loop_id, ready["completion_marker"]

    def test_inbox_delivers_notice_without_assignment_and_ack_stops_it(self):
        loop_id, marker = self.complete_a_loop()
        inbox = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual([m["kind"] for m in inbox["messages"]], ["notice"])
        notice = inbox["messages"][0]
        self.assertEqual(notice["message_id"], notice["notice_id"])
        self.assertIn("NOTICE, not an assignment", notice["content"])
        self.assertIn("Do not call odin_loop_claim", notice["content"])
        self.assertNotIn(marker, notice["content"])
        self.assertIsNone(MARKER.search(notice["content"]))
        self.assertIn("nothing in this notice is operator approval", notice["content"])
        # A reply to the notice is not a stage completion and creates nothing.
        captured = self.send(
            "loop_capture",
            {
                "session_id": self.session,
                "hook_event_name": "Stop",
                "last_assistant_message": "I read the notice: "
                + notice["content"][:200],
            },
            executive=True,
        )
        self.assertFalse(captured["captured"])
        # Same identity on every poll until acknowledged; first offer recorded once.
        again = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual(again["messages"][0]["message_id"], notice["message_id"])
        offered = self.gateway.development_loop.notice(notice["notice_id"])[
            "first_offered_at"
        ]
        self.assertIsNotNone(offered)
        self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual(
            self.gateway.development_loop.notice(notice["notice_id"])[
                "first_offered_at"
            ],
            offered,
        )
        status = self.send("loop_status", {"loop_id": loop_id}, executive=True)[
            "loops"
        ][0]
        self.assertEqual(status["notices"]["pending"], 1)
        self.assertEqual(
            status["notices"]["delivery"], "at_least_once_until_acknowledged"
        )
        self.assertEqual(status["work"]["waiting"], "none")
        operation = identifier()
        acked = self.send(
            "loop_ack",
            {"session_id": self.session, "notice_id": notice["notice_id"]},
            operation,
            executive=True,
        )
        self.assertEqual(acked["notice"]["state"], "acknowledged")
        self.assertEqual(acked["notice"]["acknowledged_by"], "fable-executive")
        self.assertEqual(
            acked,
            self.send(
                "loop_ack",
                {"session_id": self.session, "notice_id": notice["notice_id"]},
                operation,
                executive=True,
            ),
        )
        self.assertEqual(
            self.send(
                "loop_inbox",
                {"session_id": self.session, "accept": ["assignment", "notice"]},
                executive=True,
            )["messages"],
            [],
        )
        self.assertEqual(
            self.gateway.development_loop.get(loop_id)["status"], "complete"
        )

    def test_bridge_without_notice_acceptance_receives_assignments_only(self):
        self.complete_a_loop()
        legacy = self.send("loop_inbox", {"session_id": self.session}, executive=True)
        self.assertEqual(legacy["messages"], [])
        current = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual([m["kind"] for m in current["messages"]], ["notice"])
        # The legacy poll did not count as an offer.
        self.assertIsNotNone(
            self.gateway.development_loop.notice(current["messages"][0]["notice_id"])[
                "first_offered_at"
            ]
        )
        with self.assertRaises(Exception):
            self.send(
                "loop_inbox",
                {"session_id": self.session, "accept": ["bulletin"]},
                executive=True,
            )

    def test_inbox_delivers_despite_a_quoted_footer_and_labels_operator_acks(self):
        result = self.send(
            "loop_start", {"goal": "Footer test", "session_id": self.session}
        )
        loop_id, job = result["loop"]["id"], result["job"]
        core = self.gateway.development_loop
        core.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], identifier()
        )
        stage = core.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], verdict(), identifier()
        )["stage"]
        self.send(
            "loop_claim",
            {"loop_id": loop_id, "stage_id": stage["id"], "session_id": self.session},
            executive=True,
        )
        ready = self.send(
            "loop_ready",
            {
                "loop_id": loop_id,
                "stage_id": stage["id"],
                "session_id": self.session,
                "evidence_packet": {"r": 1},
            },
            executive=True,
        )
        captured = self.send(
            "loop_capture",
            {
                "session_id": self.session,
                "hook_event_name": "Stop",
                "last_assistant_message": "Done\n" + ready["completion_marker"],
            },
            executive=True,
        )
        job = core.job(captured["job"]["id"])
        core.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], identifier()
        )
        quoting = verdict("complete")
        quoting["assessment"] = "Final text ended with " + ready["completion_marker"]
        core.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], quoting, identifier()
        )
        second = self.send("loop_start", {"goal": "Next", "session_id": self.session})
        job = second["job"]
        core.mark_evaluator_started(
            second["loop"]["id"], job["id"], job["packet_digest"], identifier()
        )
        core.accept_evaluation(
            second["loop"]["id"],
            job["id"],
            job["packet_digest"],
            verdict(),
            identifier(),
        )
        inbox = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual(
            [m["kind"] for m in inbox["messages"]], ["assignment", "notice"]
        )
        self.assertNotIn(ready["completion_marker"], inbox["messages"][1]["content"])
        self.assertIsNone(MARKER.search(inbox["messages"][1]["content"]))
        # An operator poll over the socket is not an offer to the executive, and an
        # operator acknowledgement is labelled by role, never as approval.
        core.control(second["loop"]["id"], "stop", identifier())
        fresh = self.send(
            "loop_start", {"goal": "Third", "session_id": str(uuid.uuid4())}
        )
        core.control(fresh["loop"]["id"], "stop", identifier())
        operator_view = self.send(
            "loop_inbox",
            {
                "session_id": fresh["loop"]["session_id"],
                "accept": ["assignment", "notice"],
            },
        )
        stop_notice = operator_view["messages"][0]
        self.assertIsNone(core.notice(stop_notice["notice_id"])["first_offered_at"])
        acked = self.send(
            "loop_ack",
            {
                "session_id": fresh["loop"]["session_id"],
                "notice_id": stop_notice["notice_id"],
            },
        )
        self.assertEqual(
            acked["notice"]["acknowledgement_authority"],
            "operator_terminal_acknowledgement_not_approval",
        )

    def test_notice_scope_is_checked_before_any_replay(self):
        self.complete_a_loop()
        notice = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )["messages"][0]
        operation = identifier()
        self.send(
            "loop_ack",
            {"session_id": self.session, "notice_id": notice["notice_id"]},
            operation,
            executive=True,
        )
        foreign = {
            "schema_version": 1,
            "operation_id": operation,
            "action": "loop_ack",
            "payload": {
                "project": self.other,
                "session_id": self.session,
                "notice_id": notice["notice_id"],
            },
        }
        with self.assertRaises(PermissionError):
            submit_executive(self.gateway, {"command": foreign}, self.other)
        with self.assertRaises(PermissionError):
            self.send(
                "loop_ack",
                {"session_id": str(uuid.uuid4()), "notice_id": notice["notice_id"]},
                executive=True,
            )
        # Another session's inbox never sees this session's notice.
        self.assertEqual(
            self.send(
                "loop_inbox",
                {"session_id": str(uuid.uuid4()), "accept": ["assignment", "notice"]},
                executive=True,
            )["messages"],
            [],
        )

    def test_notices_and_assignments_share_the_inbox_without_starvation(self):
        self.complete_a_loop()
        # A second loop for the same session now offers an assignment.
        result = self.send("loop_start", {"goal": "Second", "session_id": self.session})
        core = self.gateway.development_loop
        job = result["job"]
        core.mark_evaluator_started(
            result["loop"]["id"], job["id"], job["packet_digest"], identifier()
        )
        core.accept_evaluation(
            result["loop"]["id"],
            job["id"],
            job["packet_digest"],
            verdict(),
            identifier(),
        )
        kinds = [
            m["kind"]
            for m in self.send(
                "loop_inbox",
                {"session_id": self.session, "accept": ["assignment", "notice"]},
                executive=True,
            )["messages"]
        ]
        self.assertEqual(kinds, ["assignment", "notice"])

    def test_operator_deadlines_control_and_attention_in_status(self):
        result = self.send(
            "loop_start",
            {
                "goal": "Deadline test",
                "session_id": self.session,
                "deadlines": {"evaluator_seconds": 30},
            },
        )
        loop = result["loop"]
        self.assertEqual(loop["deadlines"]["evaluator_seconds"], 30)
        with self.assertRaises(ValueError):
            self.send("loop_control", {"loop_id": loop["id"], "action": "deadlines"})
        with self.assertRaises(ValueError):
            self.send(
                "loop_control",
                {
                    "loop_id": loop["id"],
                    "action": "pause",
                    "deadlines": {"offer_seconds": 1},
                },
            )
        changed = self.send(
            "loop_control",
            {
                "loop_id": loop["id"],
                "action": "deadlines",
                "deadlines": {"evaluator_seconds": 5, "offer_seconds": 7},
            },
        )
        self.assertEqual(changed["loop"]["deadlines"]["evaluator_seconds"], 5)
        with self.assertRaises(PermissionError):
            self.send(
                "loop_control",
                {
                    "loop_id": loop["id"],
                    "action": "deadlines",
                    "deadlines": {"offer_seconds": 1},
                },
                executive=True,
            )
        core = self.gateway.development_loop
        core.check_attention(at=later(changed["loop"]["updated_at"], 6), force=True)
        status = self.send("loop_status", {"loop_id": loop["id"]})["loops"][0]
        self.assertEqual(status["work"]["waiting"], "pending")
        self.assertEqual(status["work"]["deadline_key"], "evaluator_seconds")
        self.assertEqual(status["work"]["attention"]["observed"], "evaluator_stalled")
        self.assertEqual(status["notices"]["pending"], 1)
        self.assertEqual(status["notices"]["latest"][0]["kind"], "stalled")
        inbox = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual(inbox["messages"][0]["kind"], "notice")
        self.assertIn("evaluator_stalled", inbox["messages"][0]["content"])
        # Attention is observation only: the evaluator job is still pending and dispatchable.
        self.assertEqual(core.get(loop["id"])["status"], "evaluator_pending")
        self.assertEqual(len(core.pending_evaluators(self.project)), 1)
        # Stop is a controller transition; it does not claim to kill running work.
        stopped = self.send("loop_control", {"loop_id": loop["id"], "action": "stop"})
        self.assertTrue(stopped["external_process_stop_required"])
        kinds = sorted(n["kind"] for n in core.notices(loop["id"]))
        self.assertEqual(kinds, ["stalled", "stopped"])


if __name__ == "__main__":
    unittest.main()
