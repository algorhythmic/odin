"""Synthetic notices, acknowledgement and deadline attention; no live loop or model."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from odin.contracts import canonical, identifier
from odin.coordination import Actor
from odin.development_evaluator import SCHEMA as EVALUATOR_SCHEMA, EvaluatorRunner, _write
from odin.development_gateway import UNRESOLVED_DETAIL, _processes
from odin.executive_projection import MAX_COMPACT_BYTES, project_receipt
from odin.development_loop import MARKER, DevelopmentLoop, clip_bytes, normalize_deadlines
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict, Store
from test_development_evaluator import NATIVE
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


class ByteClipTests(unittest.TestCase):
    def test_tiny_budgets_never_exceed_limit(self):
        for limit in range(0, 12):
            self.assertLessEqual(len(clip_bytes("😀😀😀", limit).encode("utf-8")), limit)
            self.assertLessEqual(len(clip_bytes("😀😀😀", limit, suffix="").encode("utf-8")), limit)


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


class NoticeRecoveryTests(unittest.TestCase):
    """Identity collisions, restart recovery and downgrade limits; controlled clock."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.addCleanup(lambda: self.store.close())
        self.store.create(project(P, "Development"))
        self.loops = DevelopmentLoop(self.store)

    def reopen(self):
        self.store.close()
        self.store = Store(self.temp.name)
        self.loops = DevelopmentLoop(self.store)

    def offered_stage(self, **deadlines):
        started = self.loops.start(
            P, "Recovery", SESSION, identifier(), deadlines=deadlines
        )
        job = started["job"]
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        stage = self.loops.accept_evaluation(
            job["loop_id"], job["id"], job["packet_digest"], verdict(), identifier()
        )["stage"]
        return self.loops.get(stage["loop_id"]), stage

    def test_distinct_observations_have_distinct_identities_and_same_observation_once(
        self,
    ):
        loop, stage = self.offered_stage(offer_seconds=60)
        base = loop["updated_at"]
        self.assertEqual(
            self.loops.check_attention(at=later(base, 61), force=True), [loop["id"]]
        )
        first = self.loops.get(loop["id"])["attention"]["notice_id"]
        self.loops.acknowledge(first, P, SESSION, identifier(), actor="fable-executive")
        # Same persisted observation: repeated checks and a restart write nothing.
        self.assertEqual(self.loops.check_attention(at=later(base, 62), force=True), [])
        self.reopen()
        self.assertEqual(
            self.loops.check_attention(at=later(base, 600), force=True), []
        )
        self.assertEqual(self.loops.get(loop["id"])["attention"]["notice_id"], first)
        self.assertEqual(len(self.loops.notices(loop["id"])), 1)
        # Tighten, observe, then revert to the original deadline: the revert is a
        # new observation with its own identity, even though loop, status,
        # revision, observation and deadline all match the acknowledged notice.
        self.loops.set_deadlines(loop["id"], {"offer_seconds": 30}, identifier())
        self.assertEqual(
            self.loops.check_attention(at=later(base, 700), force=True), [loop["id"]]
        )
        second = self.loops.get(loop["id"])["attention"]["notice_id"]
        self.loops.acknowledge(
            second, P, SESSION, identifier(), actor="fable-executive"
        )
        self.loops.set_deadlines(loop["id"], {"offer_seconds": 60}, identifier())
        self.assertIsNone(self.loops.get(loop["id"])["attention"])
        self.assertEqual(
            self.loops.check_attention(at=later(base, 800), force=True), [loop["id"]]
        )
        third = self.loops.get(loop["id"])["attention"]["notice_id"]
        self.assertEqual(len({first, second, third}), 3)
        pending = [n["id"] for n in self.loops.pending_notices(P, SESSION)]
        self.assertEqual(pending, [third])  # the reverted observation is delivered
        self.assertEqual(
            self.loops.get(loop["id"])["revision"], loop["revision"]
        )  # never a transition
        self.assertEqual(
            self.loops.pending_stages(P, SESSION)[0]["id"], stage["id"]
        )  # never redispatched
        # Disable, then re-enable: nothing while disabled, a fresh identity after.
        self.loops.set_deadlines(loop["id"], {"offer_seconds": None}, identifier())
        self.assertIsNone(self.loops.get(loop["id"])["attention"])
        self.assertEqual(
            self.loops.check_attention(at=later(base, 10**6), force=True), []
        )
        self.loops.set_deadlines(loop["id"], {"offer_seconds": 60}, identifier())
        self.assertEqual(
            self.loops.check_attention(at=later(base, 10**6 + 1), force=True),
            [loop["id"]],
        )
        fourth = self.loops.get(loop["id"])["attention"]["notice_id"]
        self.assertNotIn(fourth, {first, second, third})
        self.assertEqual(len(self.loops.notices(loop["id"])), 4)
        # A late legitimate transition clears attention without touching notices.
        claimed = self.loops.claim(loop["id"], stage["id"], SESSION, identifier())[
            "loop"
        ]
        self.assertIsNone(claimed["attention"])
        self.assertEqual(len(self.loops.notices(loop["id"])), 4)
        self.assertEqual(self.loops.notice(fourth)["state"], "pending")

    def test_restart_preserves_notices_acknowledgements_and_attention(self):
        loop, stage = self.offered_stage(offer_seconds=5)
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 6), force=True),
            [loop["id"]],
        )
        stalled = self.loops.get(loop["id"])["attention"]["notice_id"]
        self.loops.mark_offered([stalled])
        other = self.loops.start  # noqa: F841 - readability: no second loop is started
        self.reopen()
        restored = self.loops.get(loop["id"])
        self.assertEqual(restored["attention"]["notice_id"], stalled)
        self.assertEqual(restored["deadlines"]["offer_seconds"], 5)
        self.assertEqual(
            [n["id"] for n in self.loops.pending_notices(P, SESSION)], [stalled]
        )
        self.assertIsNotNone(self.loops.notice(stalled)["first_offered_at"])
        acked = self.loops.acknowledge(
            stalled, P, SESSION, identifier(), actor="fable-executive"
        )
        self.reopen()
        self.assertEqual(self.loops.notice(stalled)["state"], "acknowledged")
        self.assertEqual(
            self.loops.notice(stalled)["acknowledged_at"],
            acked["notice"]["acknowledged_at"],
        )
        self.assertEqual(self.loops.pending_notices(P, SESSION), [])
        # Forward recovery on the same code keeps the stage claimable and quiet.
        self.assertEqual(
            self.loops.check_attention(at=later(loop["updated_at"], 10**5), force=True),
            [],
        )
        self.assertEqual(self.loops.pending_stages(P, SESSION)[0]["id"], stage["id"])

    def test_records_written_by_this_code_are_rejected_by_the_pre_notice_schema(self):
        """Documents why a downgrade below ODIN-ADR-030 is unsupported after new writes."""
        import copy

        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError

        loop, _ = self.offered_stage()
        schema = copy.deepcopy(
            self.store.contracts.validators["development-loop"].schema
        )
        new_keys = ("deadlines", "attention", "delegation_profile")
        for key in new_keys:
            schema["properties"].pop(key)
        # The 972a92d shape: exactly these properties, additionalProperties false.
        self.assertEqual(
            sorted(schema["properties"]),
            [
                "created_at",
                "current_job",
                "current_stage",
                "goal",
                "id",
                "last_evidence_digest",
                "max_rounds",
                "no_progress_count",
                "no_progress_limit",
                "paused_from",
                "project",
                "reason",
                "revision",
                "round",
                "schema_version",
                "session_id",
                "status",
                "updated_at",
            ],
        )
        self.assertIs(schema.get("additionalProperties"), False)
        closed = Draft202012Validator(schema)
        with self.assertRaises(ValidationError):
            closed.validate(self.loops.get(loop["id"]))
        legacy = {
            k: v
            for k, v in self.loops.get(loop["id"]).items()
            if k not in new_keys
        }
        closed.validate(
            legacy
        )  # a record never touched by new code stays readable by old code
        # Each of the three new keys is individually fatal to the old schema.
        for key in new_keys:
            with self.assertRaises(ValidationError):
                closed.validate(legacy | {key: None})


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

    def test_oversized_multibyte_narratives_stay_within_the_channel_byte_budget(self):
        from unittest.mock import Mock

        from odin.development_gateway import NOTICE_CONTENT_BYTES, render_notice
        from odin.executive_mcp import ExecutiveBridge, MCPServer

        result = self.send(
            "loop_start",
            {"goal": "Byte budget", "session_id": self.session, "max_rounds": 1},
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
        # 2000 four-byte characters: schema-valid, 8000 bytes, and a quoted footer.
        # Round limit -> needs_operator with the fixed reason "development round limit
        # reached"; this assessment is carried in the notice's assessment narrative.
        huge = verdict()
        huge["assessment"] = "\U0001f600" * 1990 + " " + ready["completion_marker"]
        core.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], huge, identifier()
        )
        self.assertEqual(core.get(loop_id)["status"], "needs_operator")
        notice = core.pending_notices(self.project, self.session)[0]
        self.assertLessEqual(len(notice["assessment"].encode("utf-8")), 2000)
        self.assertLessEqual(len(notice["summary"].encode("utf-8")), 2000)
        # A notice persisted under the old character-based limit is bounded on delivery too.
        legacy = dict(notice)
        legacy["assessment"] = "\U0001f600" * 2000
        legacy["summary"] = "\U0001f600" * 2000
        with self.gateway.store.transaction():
            core._save_notice(legacy)
        rendered = render_notice(core.notice(notice["id"]), "needs_operator")
        self.assertLessEqual(len(rendered.encode("utf-8")), NOTICE_CONTENT_BYTES)
        rendered.encode("utf-8")  # valid encoding, no split surrogates
        for essential in (
            "NOTICE, not an assignment",
            "odin_loop_ack notice_id=" + notice["id"],
            "What needs attention",
            "Inspect odin_loop_status",
        ):
            self.assertIn(essential, rendered)
        self.assertIsNone(MARKER.search(rendered))
        self.assertNotIn(ready["completion_marker"], rendered)
        # Mixed delivery through the real gateway, then through the real bridge validator.
        # The intervention loop is stopped (a second pending notice) so a new
        # loop can offer an assignment beside both notices.
        self.send("loop_control", {"loop_id": loop_id, "action": "stop"})
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
            [m["kind"] for m in inbox["messages"]], ["assignment", "notice", "notice"]
        )
        self.assertTrue(
            all(len(m["content"].encode("utf-8")) <= 16384 for m in inbox["messages"])
        )
        gateway = Mock(
            side_effect=lambda command: {
                "schema_version": 1,
                "operation_id": command["operation_id"],
                "label": "fake-backend evidence",
                "result": inbox,
            }
        )
        bridge = ExecutiveBridge(
            self.project, gateway, development_loop=True, session_id=self.session
        )
        self.assertEqual(
            [m["kind"] for m in bridge.loop_inbox()], ["assignment", "notice", "notice"]
        )
        server = MCPServer(bridge)
        server.ready = True
        emitted = server.channel_notifications()
        self.assertEqual(
            [n["params"]["meta"]["kind"] for n in emitted], ["assignment", "notice", "notice"]
        )
        self.assertEqual(server.channel_notifications(), [])
        again = MCPServer(bridge)
        again.ready = True
        self.assertEqual(
            again.channel_notifications(), emitted
        )  # reconnect replays both
        acked = self.send(
            "loop_ack",
            {"session_id": self.session, "notice_id": notice["id"]},
            executive=True,
        )
        self.assertEqual(acked["notice"]["state"], "acknowledged")
        after = self.send(
            "loop_inbox",
            {"session_id": self.session, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual([m["kind"] for m in after["messages"]], ["assignment", "notice"])
        self.assertNotIn(notice["id"], [m["message_id"] for m in after["messages"]])

    def test_status_reports_quiescence_for_a_restart_gate(self):
        result = self.send(
            "loop_start", {"goal": "Quiescence", "session_id": self.session}
        )
        status = self.send("loop_status", {"loop_id": result["loop"]["id"]})
        quiet = status["quiescence"]
        self.assertEqual(quiet["loops"][0]["status"], "evaluator_pending")
        self.assertTrue(quiet["loops"][0]["quiescent"])
        self.assertEqual(quiet["spooled_captures"], 0)
        self.assertTrue(quiet["restart_quiescent"])
        with patch("odin.development_gateway.os.scandir", side_effect=PermissionError):
            unreadable = self.send("loop_status", {"loop_id": result["loop"]["id"]})["quiescence"]
        self.assertFalse(unreadable["restart_quiescent"])
        self.assertEqual(unreadable["spooled_captures"], 1)
        core = self.gateway.development_loop
        job = result["job"]
        core.mark_evaluator_started(
            result["loop"]["id"], job["id"], job["packet_digest"], identifier()
        )
        quiet = self.send("loop_status", {"loop_id": result["loop"]["id"]})[
            "quiescence"
        ]
        self.assertFalse(quiet["loops"][0]["quiescent"])
        self.assertFalse(quiet["restart_quiescent"])
        spool = Path(self.temp.name) / "executive-loop-spool"
        spool.mkdir(mode=0o700)
        (spool / "pending.json").write_text("{}")
        self.assertEqual(
            self.send("loop_status", {"loop_id": result["loop"]["id"]})["quiescence"][
                "spooled_captures"
            ],
            1,
        )

    def dispatch_evaluator(self, loop_id, job):
        """Record an isolated launch the way EvaluatorRunner does; no model runs."""
        directory = Path(self.temp.name) / "development-evaluator" / job["id"]
        directory.mkdir(mode=0o700, parents=True)
        os.chmod(directory.parent, 0o700)
        dispatch = {
            "schema_version": 1,
            "job_id": job["id"],
            "packet_digest": job["packet_digest"],
            "spec_digest": "b" * 64,
            "attempt": 1,
            "state": "reserved",
            "runner_pid": None,
            "runner_start": None,
            "created_at": "2026-10-21T00:00:00.000000Z",
        }
        _write(directory / "dispatch.json", dispatch, EVALUATOR_SCHEMA, definition="dispatch")
        self.gateway.development_loop.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], f"evaluator-start:{job['id']}:1"
        )
        return directory, dispatch

    def sleeper(self, *argv):
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)", *argv],
            start_new_session=True,
        )
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process

    def gate(self, loop_id, project=None):
        payload = {"loop_id": loop_id} | ({"project": project} if project else {})
        return self.send("loop_status", payload)["quiescence"]

    def test_quiet_service_reads_quiescent_with_scope_and_no_lock(self):
        result = self.send("loop_start", {"goal": "Quiet", "session_id": self.session})
        before = self.gateway.development_loop.get(result["loop"]["id"])
        quiet = self.gate(result["loop"]["id"])
        self.assertTrue(quiet["restart_quiescent"])
        self.assertEqual(quiet["scope"], "service")
        for key in (
            "loops_not_quiescent_other_projects", "spooled_captures", "delegated_turns_running",
            "delegated_turns_lost", "evaluator_executions_outstanding",
            "evaluator_executions_unresolved",
        ):
            self.assertEqual(quiet[key], 0, key)
        self.assertEqual(quiet["unresolved"], [])
        self.assertIn("not a lock", quiet["observation"])
        self.assertEqual(self.gateway.development_loop.get(result["loop"]["id"]), before)
        # An unobservable process table alone is not evidence of anything here:
        # no job was ever dispatched.
        with patch("odin.development_gateway._processes", return_value=None):
            self.assertTrue(self.gate(result["loop"]["id"])["restart_quiescent"])
        named = subprocess.Popen(
            [sys.executable, "-c",
             "import ctypes, sys, time; ctypes.CDLL(None).prctl(15, b'\\xff\\xfeodin', 0, 0, 0); "
             "sys.stdout.write('ready\\n'); sys.stdout.flush(); time.sleep(120)"],
            stdout=subprocess.PIPE, start_new_session=True,
        )
        self.addCleanup(named.stdout.close)
        self.addCleanup(named.wait)
        self.addCleanup(named.kill)
        self.assertEqual(named.stdout.readline(), b"ready\n")
        self.assertEqual(Path(f"/proc/{named.pid}/comm").read_bytes()[:2], b"\xff\xfe")
        self.assertIsNotNone(_processes(Path(self.temp.name)))

    def test_stopped_loop_with_running_evaluator_is_not_quiescent(self):
        result = self.send("loop_start", {"goal": "Stop", "session_id": self.session})
        loop_id, job = result["loop"]["id"], result["job"]
        directory, dispatch = self.dispatch_evaluator(loop_id, job)
        runner = self.sleeper(str(directory))
        dispatch.update(state="spawned", runner_pid=runner.pid)
        _write(directory / "dispatch.json", dispatch, EVALUATOR_SCHEMA, definition="dispatch")
        stopped = self.send("loop_control", {"loop_id": loop_id, "action": "stop"})
        self.assertTrue(stopped["external_process_stop_required"])
        self.assertEqual(self.gateway.development_loop.job(job["id"])["state"], "cancelled")
        gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["evaluator_executions_outstanding"], 1)
        self.assertEqual(gate["unresolved"][0]["id"], job["id"])
        # The executive's compact status view keeps the whole closed gate.
        status = self.send("loop_status", {"loop_id": loop_id})
        compact = project_receipt("odin_loop_status", {"result": status})
        self.assertEqual(compact["result"]["projection"]["view"], "compact")
        self.assertEqual(compact["result"]["quiescence"], status["quiescence"])
        self.assertIsNone(runner.poll())  # status observes; it never signals
        self.assertFalse((directory / "stop.json").exists())  # nor requests a stop
        self.assertEqual(self.gateway.development_loop.job(job["id"])["state"], "cancelled")
        # A harness that outlives its runner keeps its recorded group busy
        # even though its arguments do not name the spool.
        runner.kill()
        runner.wait()
        harness = self.sleeper()
        _write(
            directory / "started.json",
            {"schema_version": 1, "runner_pid": runner.pid, "harness_pid": harness.pid,
             "harness_start": "1", "started_at": "2026-10-21T00:00:01.000000Z"},
            EVALUATOR_SCHEMA, definition="started",
        )
        self.assertEqual(self.gate(loop_id)["evaluator_executions_outstanding"], 1)
        harness.kill()
        harness.wait()
        gate = self.gate(loop_id)
        self.assertEqual(gate["evaluator_executions_outstanding"], 0)
        self.assertEqual(gate["evaluator_executions_unresolved"], 0)
        self.assertTrue(gate["restart_quiescent"])
        with patch("odin.development_gateway._processes", return_value=None):
            gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["evaluator_executions_unresolved"], 1)
        self.assertEqual(gate["unresolved"][0]["reason"], "process table unavailable")
        with patch("odin.development_gateway.RECORD_LIMIT", 0):
            gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["unresolved"][0]["reason"], "inspection bound exceeded")

    def test_completed_job_needs_its_recorded_groups_and_spool_observed(self):
        result = self.send("loop_start", {"goal": "Done", "session_id": self.session})
        loop_id, job = result["loop"]["id"], result["job"]
        directory, _ = self.dispatch_evaluator(loop_id, job)
        self.gateway.development_loop.accept_evaluation(
            loop_id, job["id"], job["packet_digest"], verdict(), identifier()
        )
        # Completion alone establishes nothing: a completed runner recorded
        # its harness in started.json before its result.
        gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["unresolved"][0]["reason"], "dispatch evidence missing or unreadable")
        exited = subprocess.Popen([sys.executable, "-c", ""], start_new_session=True)
        exited.wait()
        started = {"schema_version": 1, "runner_pid": exited.pid, "harness_pid": exited.pid,
                   "started_at": "2026-10-21T00:00:00.000000Z", "harness_start": None}
        _write(directory / "started.json", started, EVALUATOR_SCHEMA, definition="started")
        self.assertTrue(self.gate(loop_id)["restart_quiescent"])
        # Unobserved completed jobs stay inside the inspection bound.
        with patch("odin.development_gateway.RECORD_LIMIT", 0):
            gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["unresolved"][0]["reason"], "inspection bound exceeded")
        loop = self.gateway.development_loop
        with self.assertRaises(Conflict):  # only the latest started attempt
            loop.mark_evaluator_quiet(job["id"], job["packet_digest"], 2)
        loop.mark_evaluator_quiet(job["id"], job["packet_digest"], 1)
        with patch("odin.development_gateway.RECORD_LIMIT", 0):
            self.assertTrue(self.gate(loop_id)["restart_quiescent"])
        (directory / "started.json").unlink()  # an observed attempt is not reread
        self.assertTrue(self.gate(loop_id)["restart_quiescent"])
        # A process naming the spool still counts after the observation.
        lingering = self.sleeper(str(directory / "packet.json"))
        gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["evaluator_executions_outstanding"], 1)
        self.assertEqual(gate["unresolved"][0]["reason"], "process names its spool")
        self.assertEqual(gate["unresolved"][0]["id"], job["id"])
        lingering.kill()
        lingering.wait()
        self.assertTrue(self.gate(loop_id)["restart_quiescent"])
        stray = self.sleeper(str(directory.parent / ("x" * 4096) / "file"))
        gate = self.gate(loop_id)
        self.assertEqual(gate["evaluator_executions_outstanding"], 1)
        self.assertIsNone(gate["unresolved"][0]["id"])  # unvalidated names are not echoed
        stray.kill()
        stray.wait()

    def test_mark_evaluator_quiet_requires_a_finished_started_attempt(self):
        result = self.send("loop_start", {"goal": "Busy", "session_id": self.session})
        job, loop = result["job"], self.gateway.development_loop
        with self.assertRaises(Conflict):  # never started
            loop.mark_evaluator_quiet(job["id"], job["packet_digest"], 1)
        self.dispatch_evaluator(result["loop"]["id"], job)
        with self.assertRaises(Conflict):  # running
            loop.mark_evaluator_quiet(job["id"], job["packet_digest"], 1)
        with self.assertRaises(Conflict):
            loop.mark_evaluator_quiet(job["id"], "c" * 64, 1)

    def test_completed_evaluator_descendant_in_its_harness_group_keeps_gate_closed(self):
        """A real runner and harness complete successfully; a descendant stays
        in the recorded harness group with no spool argument."""
        native = tempfile.TemporaryDirectory()
        self.addCleanup(native.cleanup)
        root = Path(native.name)
        (root / "workspace").mkdir()
        (root / "profile").mkdir(mode=0o700)
        binary = root / "native-fixture"
        binary.write_text(NATIVE)
        binary.chmod(0o700)
        config = {"schema_version": 1, "enabled": True, "harness": "codex",
                  "binary": str(binary), "workspace": str(root / "workspace"),
                  "config_dir": str(root / "profile"), "model": "descendant",
                  "timeout_seconds": 30}
        result = self.send("loop_start", {"goal": "Descendant", "session_id": self.session})
        loop_id, job = result["loop"]["id"], result["job"]
        state = Path(self.temp.name)
        runner = EvaluatorRunner(self.gateway.development_loop, state, config)
        self.addCleanup(lambda: [child.kill() or child.wait() for child in runner._children])
        self.assertEqual(runner.tick()["started"], [job["id"]])
        deadline = time.monotonic() + 15
        while self.gateway.development_loop.job(job["id"])["state"] != "completed" or runner._children:
            self.assertLess(time.monotonic(), deadline, "synthetic evaluator did not complete")
            runner.tick()
            time.sleep(0.03)
        pid = int((root / "workspace" / "descendant.pid").read_text())

        def kill_descendant():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.addCleanup(kill_descendant)
        directory = state / "development-evaluator" / job["id"]
        started = json.loads((directory / "started.json").read_text())
        harness = started["harness_pid"]
        deadline = time.monotonic() + 5
        while Path(f"/proc/{harness}").exists():  # the runner reaped its harness
            self.assertLess(time.monotonic(), deadline, "harness did not exit")
            time.sleep(0.03)
        self.assertEqual(os.getpgid(pid), harness)
        argv = Path(f"/proc/{pid}/cmdline").read_bytes()
        self.assertNotIn(str(state).encode(), argv)
        for _ in range(3):
            self.assertEqual(runner.tick()["observed"], [])
        gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["evaluator_executions_outstanding"], 1)
        self.assertEqual(gate["unresolved"][0], {
            "kind": "evaluator_job", "id": job["id"],
            "reason": "recorded process group live; job completed"})
        # Service-wide: another project's status sees the same execution.
        other = self.send("loop_start", {"project": self.other, "goal": "Other",
                                         "session_id": str(uuid.uuid4())})
        elsewhere = self.gate(other["loop"]["id"], project=self.other)
        self.assertFalse(elsewhere["restart_quiescent"])
        self.assertEqual(elsewhere["evaluator_executions_outstanding"], 1)
        self.send("loop_control", {"project": self.other, "loop_id": other["loop"]["id"],
                                   "action": "stop"})
        # Missing or unreadable group evidence stays unresolved, and the
        # scheduler records nothing from it, even once the group is empty.
        kill_descendant()
        deadline = time.monotonic() + 5
        while Path(f"/proc/{pid}").exists() and Path(f"/proc/{pid}/stat").read_bytes().rsplit(b")", 1)[1].split()[0] != b"Z":
            self.assertLess(time.monotonic(), deadline, "descendant did not exit")
            time.sleep(0.03)
        saved = (directory / "started.json").read_bytes()
        (directory / "started.json").unlink()
        self.assertEqual(runner.tick()["observed"], [])
        gate = self.gate(loop_id)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate["evaluator_executions_unresolved"], 1)
        self.assertEqual(gate["unresolved"][0]["reason"], "dispatch evidence missing or unreadable")
        (directory / "started.json").write_bytes(saved)
        os.chmod(directory / "started.json", 0o644)
        self.assertEqual(runner.tick()["observed"], [])
        self.assertEqual(self.gate(loop_id)["evaluator_executions_unresolved"], 1)
        os.chmod(directory / "started.json", 0o600)
        # Observed absent by the read-only status; the record is the scheduler's.
        gate = self.gate(loop_id)
        self.assertTrue(gate["restart_quiescent"], gate)
        quiet = f"evaluator-quiet:{job['id']}:1"
        receipts = "SELECT COUNT(*) FROM development_loop_receipts WHERE operation=?"
        self.assertEqual(self.gateway.store.db.execute(receipts, (quiet,)).fetchone()[0], 0)
        self.assertEqual(runner.tick()["observed"], [job["id"]])
        self.assertEqual(self.gateway.store.db.execute(receipts, (quiet,)).fetchone()[0], 1)
        self.assertEqual(runner.tick()["observed"], [])
        self.assertTrue(self.gate(loop_id)["restart_quiescent"])

    def test_stopped_loop_with_unresolved_evaluator_evidence_is_not_quiescent(self):
        result = self.send("loop_start", {"goal": "Unknown", "session_id": self.session})
        loop_id, job = result["loop"]["id"], result["job"]
        directory, _ = self.dispatch_evaluator(loop_id, job)
        # Reserved with no runner identity: only the spool argument can show it.
        reserved = self.sleeper(str(directory))
        self.send("loop_control", {"loop_id": loop_id, "action": "stop"})
        self.assertEqual(self.gate(loop_id)["evaluator_executions_outstanding"], 1)
        reserved.kill()
        reserved.wait()
        self.assertTrue(self.gate(loop_id)["restart_quiescent"])
        os.chmod(directory / "dispatch.json", 0o644)
        unreadable = self.gate(loop_id)
        self.assertFalse(unreadable["restart_quiescent"])
        self.assertEqual(unreadable["evaluator_executions_unresolved"], 1)
        (directory / "dispatch.json").unlink()
        missing = self.gate(loop_id)
        self.assertFalse(missing["restart_quiescent"])
        self.assertEqual(
            missing["unresolved"][0]["reason"], "dispatch evidence missing or unreadable"
        )

    def test_compact_status_keeps_a_maximal_unresolved_gate(self):
        result = self.send("loop_start", {"goal": "Many", "session_id": self.session})
        status = self.send("loop_status", {"loop_id": result["loop"]["id"]})
        entry = {"kind": "delegated_turn_lost", "id": "7" * 26,
                 "reason": "native outcome unknown; recorded processes unknown"}
        status["quiescence"] |= {"unresolved": [entry] * UNRESOLVED_DETAIL,
                                 "delegated_turns_lost": 9007199254740991,
                                 "restart_quiescent": False}
        compact = project_receipt("odin_loop_status", {"result": status})
        self.assertEqual(compact["result"]["quiescence"], status["quiescence"])
        self.assertLessEqual(len(canonical(compact).encode()), MAX_COMPACT_BYTES)
        status["loops"] *= 400  # past the compact budget: the overflow branch
        compact = project_receipt("odin_loop_status", {"result": status})["result"]
        self.assertTrue(compact["projection"]["incomplete_for_action"])
        self.assertEqual(
            compact["quiescence"],
            {key: value for key, value in status["quiescence"].items()
             if key not in {"loops", "unresolved"}} | {"detail_omitted": True},
        )
        self.assertFalse(compact["quiescence"]["restart_quiescent"])

    def test_restart_gate_is_service_wide(self):
        own = self.send("loop_start", {"goal": "Own", "session_id": self.session})
        other = self.send(
            "loop_start", {"project": self.other, "goal": "Other", "session_id": str(uuid.uuid4())}
        )
        self.assertTrue(self.gate(own["loop"]["id"])["restart_quiescent"])
        job = other["job"]
        self.gateway.development_loop.mark_evaluator_started(
            other["loop"]["id"], job["id"], job["packet_digest"], identifier()
        )
        gate = self.gate(own["loop"]["id"])
        self.assertEqual([item["loop_id"] for item in gate["loops"]], [own["loop"]["id"]])
        self.assertTrue(gate["loops"][0]["quiescent"])
        self.assertEqual(gate["loops_not_quiescent_other_projects"], 1)
        self.assertFalse(gate["restart_quiescent"])
        self.assertEqual(gate, self.gate(own["loop"]["id"]))
        self.send("loop_control", {"project": self.other, "loop_id": other["loop"]["id"], "action": "stop"})
        self.assertTrue(self.gate(own["loop"]["id"])["restart_quiescent"])
        third = self.send(
            "loop_start", {"project": self.other, "goal": "Third", "session_id": str(uuid.uuid4())}
        )
        directory, _ = self.dispatch_evaluator(third["loop"]["id"], third["job"])
        runner = self.sleeper(str(directory))
        self.send("loop_control", {"project": self.other, "loop_id": third["loop"]["id"], "action": "stop"})
        gate = self.gate(own["loop"]["id"])
        self.assertEqual(gate["loops_not_quiescent_other_projects"], 0)
        self.assertEqual(gate["evaluator_executions_outstanding"], 1)
        self.assertFalse(gate["restart_quiescent"])
        runner.kill()
        runner.wait()
        self.assertTrue(self.gate(own["loop"]["id"])["restart_quiescent"])

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
