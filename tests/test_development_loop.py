"""Synthetic evaluator/executive evidence, never live model acceptance."""

import copy
import tempfile
import unittest
from pathlib import Path

from jsonschema.exceptions import ValidationError
from odin.contracts import canonical, identifier, strict_loads
from odin.development_loop import DevelopmentLoop, normalize_result
from odin.store import Conflict, Store
from test_memory import P, Q, project

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "22222222-2222-4222-8222-222222222222"


def verdict(decision="continue", revision="1"):
    return {
        "decision": decision,
        "assessment": "Synthetic independent assessment",
        "findings": ["A bounded local observation"],
        "next_prompt": "Run the next bounded challenge"
        if decision == "continue"
        else "",
        "evidence_refs": [
            {"ref": "fixture:result", "revision": revision, "digest": "a" * 64}
        ],
    }


class DevelopmentLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.store = Store(self.directory)
        self.store.create(project(P, "Development"))
        self.store.create(project(Q, "Other"))
        self.loops = DevelopmentLoop(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def start(self, **kwargs):
        return self.loops.start(
            P, "Exercise a synthetic feature", SESSION, identifier(), **kwargs
        )

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

    def ready(self, stage, *, prompt_id=None):
        self.loops.claim(
            stage["loop_id"], stage["id"], SESSION, identifier(), prompt_id=prompt_id
        )
        return self.loops.ready(
            stage["loop_id"],
            stage["id"],
            SESSION,
            {
                "repository_revision": "synthetic-commit",
                "summary": "Fixture test passed",
            },
            identifier(),
            prompt_id=prompt_id,
        )

    def finish(self, stage, *, prompt_id=None):
        ready = self.ready(stage, prompt_id=prompt_id)
        text = "Synthetic completed response\n" + ready["completion_marker"]
        return self.loops.capture_stop(SESSION, text, identifier(), prompt_id=prompt_id)

    def test_persistent_two_way_loop_with_exact_packet_and_final_response(self):
        started = self.start()
        self.assertEqual(started["loop"]["status"], "evaluator_pending")
        self.assertEqual(self.loops.pending_evaluators(P), [started["job"]])
        result = self.evaluate(started["job"])
        self.assertEqual(self.loops.pending_stages(P, SESSION), [result["stage"]])
        captured = self.finish(result["stage"], prompt_id="prompt-one")
        self.assertTrue(captured["captured"])
        self.assertIn(
            "Synthetic completed response",
            captured["job"]["packet"]["executive_final_text"],
        )
        self.assertEqual(
            captured["job"]["packet"]["evidence"]["summary"], "Fixture test passed"
        )
        packet = copy.deepcopy(captured["job"])
        self.store.close()
        self.store = Store(self.directory)
        self.loops = DevelopmentLoop(self.store)
        self.assertEqual(self.loops.pending_evaluators(P), [packet])
        result = self.evaluate(packet, verdict("complete", "2"))
        self.assertEqual(result["loop"]["status"], "complete")
        self.assertIsNone(result["stage"])
        self.assertEqual(self.loops.pending_stages(P, SESSION), [])
        self.assertEqual(self.store.records("Commitment"), [])
        self.assertEqual(len(self.start()["loop"]["id"]), 26)

    def test_stable_replay_and_exclusive_project_loop(self):
        op = identifier()
        first = self.loops.start(P, "Goal", SESSION, op)
        self.assertEqual(first, self.loops.start(P, "Goal", SESSION, op))
        with self.assertRaises(Conflict):
            self.loops.start(P, "Changed", SESSION, op)
        with self.assertRaises(Conflict):
            self.start()
        self.loops.start(Q, "Other project", OTHER_SESSION, identifier())
        self.assertEqual(len(self.loops.pending_evaluators()), 2)
        self.assertEqual(self.loops.pending_stages(Q, SESSION), [])

    def test_invalid_native_identity_and_evidence_budget(self):
        with self.assertRaises(Conflict):
            self.loops.start(P, "Goal", "not-a-uuid", identifier())
        with self.assertRaises(Conflict):
            self.start(evidence_packet=[])
        with self.assertRaises(Conflict):
            self.start(evidence_packet={"body": "α" * 33000})
        with self.assertRaises(ValidationError):
            self.start(max_rounds=0)
        self.assertEqual(self.loops.for_project(P), [])

    def test_final_hook_requires_claim_ready_exact_footer_session_and_prompt(self):
        stage = self.evaluate(self.start()["job"])["stage"]
        with self.assertRaises(Conflict):
            self.loops.ready(stage["loop_id"], stage["id"], SESSION, {}, identifier())
        ready = self.ready(stage, prompt_id="native-prompt")
        text = "Final answer\n" + ready["completion_marker"]
        for session, final, kwargs in (
            (OTHER_SESSION, text, {"prompt_id": "native-prompt"}),
            (SESSION, text + "\nUnrelated text", {"prompt_id": "native-prompt"}),
            (SESSION, text, {"prompt_id": "other-prompt"}),
            (SESSION, text, {"prompt_id": "native-prompt", "stop_hook_active": True}),
            (
                SESSION,
                text,
                {"prompt_id": "native-prompt", "hook_event_name": "Notification"},
            ),
        ):
            self.assertFalse(
                self.loops.capture_stop(session, final, identifier(), **kwargs)[
                    "captured"
                ]
            )
        for kwargs in (
            {"background_tasks": [{"running": True}]},
            {"session_crons": {"active": 1}},
        ):
            with self.assertRaises(Conflict):
                self.loops.capture_stop(
                    SESSION, text, identifier(), prompt_id="native-prompt", **kwargs
                )
        first = self.loops.capture_stop(
            SESSION, text, identifier(), prompt_id="native-prompt"
        )
        repeated = self.loops.capture_stop(
            SESSION, text, identifier(), prompt_id="native-prompt"
        )
        self.assertTrue(first["captured"])
        self.assertTrue(repeated["duplicate"])
        superseded = self.loops.capture_stop(
            SESSION,
            "Earlier background answer\n" + ready["completion_marker"],
            identifier(),
            prompt_id="native-prompt",
            background_tasks=["pending"],
        )
        self.assertTrue(superseded["superseded"])
        self.assertEqual(len(self.loops.pending_evaluators()), 1)
        with self.assertRaises(Conflict):
            self.loops.capture_stop(
                SESSION,
                "Different answer\n" + ready["completion_marker"],
                identifier(),
                prompt_id="native-prompt",
            )

    def test_pause_preserves_ready_marker_resume_and_stop_cancels_effects(self):
        stage = self.evaluate(self.start()["job"])["stage"]
        ready = self.ready(stage)
        loop_id = stage["loop_id"]
        self.loops.control(
            loop_id, "pause", identifier(), expected_revision=ready["loop"]["revision"]
        )
        text = "Result\n" + ready["completion_marker"]
        completion_op = identifier()
        with self.assertRaises(Conflict):
            self.loops.capture_stop(SESSION, text, completion_op)
        with self.assertRaises(Conflict):
            self.loops.control(loop_id, "resume", identifier(), expected_revision=1)
        self.loops.control(loop_id, "resume", identifier())
        captured = self.loops.capture_stop(SESSION, text, completion_op)
        self.assertTrue(captured["captured"])
        stopped = self.loops.control(loop_id, "stop", identifier())
        self.assertTrue(stopped["external_process_stop_required"])
        self.assertEqual(stopped["loop"]["status"], "stopped")
        self.assertEqual(self.loops.pending_evaluators(), [])
        with self.assertRaises(Conflict):
            self.loops.mark_evaluator_started(
                loop_id,
                captured["job"]["id"],
                captured["job"]["packet_digest"],
                identifier(),
            )

    def test_paused_evaluator_result_is_retryable_without_losing_it(self):
        job = self.start()["job"]
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        self.loops.control(job["loop_id"], "pause", identifier())
        operation = identifier()
        with self.assertRaises(Conflict):
            self.loops.accept_evaluation(
                job["loop_id"], job["id"], job["packet_digest"], verdict(), operation
            )
        self.loops.control(job["loop_id"], "resume", identifier())
        result = self.loops.accept_evaluation(
            job["loop_id"], job["id"], job["packet_digest"], verdict(), operation
        )
        self.assertEqual(result["loop"]["status"], "executive_pending")

    def test_stale_packet_and_result_rejected_without_transition(self):
        job = self.start()["job"]
        with self.assertRaises(Conflict):
            self.loops.mark_evaluator_started(
                job["loop_id"], job["id"], "b" * 64, identifier()
            )
        first = self.evaluate(job)
        captured = self.finish(first["stage"])
        with self.assertRaises(Conflict):
            self.loops.accept_evaluation(
                job["loop_id"], job["id"], job["packet_digest"], verdict(), identifier()
            )
        self.assertEqual(self.loops.pending_evaluators(), [captured["job"]])

    def test_unknown_evaluator_never_redispatched_without_observation(self):
        job = self.start()["job"]
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        result = self.loops.fail_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            outcome="unknown",
            reason="dispatch receipt lost",
        )
        self.assertEqual(result["loop"]["status"], "unknown")
        self.assertEqual(self.loops.pending_evaluators(), [])
        with self.assertRaises(Conflict):
            self.loops.accept_evaluation(
                job["loop_id"], job["id"], job["packet_digest"], verdict(), identifier()
            )
        reconciled = self.loops.reconcile_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            observed="not_started",
        )
        self.assertEqual(reconciled["job"]["id"], job["id"])
        self.assertEqual(self.loops.pending_evaluators(), [job])
        self.loops.mark_evaluator_started(
            job["loop_id"], job["id"], job["packet_digest"], identifier()
        )
        lost = self.loops.fail_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            outcome="lost",
            reason="process exited without outcome",
        )
        self.assertEqual(lost["loop"]["status"], "needs_operator")

    def test_stop_failure_requires_reconciliation_of_ready_stage(self):
        stage = self.evaluate(self.start()["job"])["stage"]
        ready = self.ready(stage)
        text = "Interrupted final\n" + ready["completion_marker"]
        result = self.loops.capture_stop(
            SESSION, "", identifier(), hook_event_name="StopFailure"
        )
        self.assertFalse(result["captured"])
        self.assertEqual(result["loop"]["status"], "unknown")
        self.assertEqual(self.loops.pending_evaluators(), [])
        self.loops.reconcile_execution(
            stage["loop_id"], stage["id"], SESSION, identifier(), observed="running"
        )
        self.assertTrue(
            self.loops.capture_stop(SESSION, text, identifier())["captured"]
        )

    def test_execution_unknown_and_confirmed_loss(self):
        stage = self.evaluate(self.start()["job"])["stage"]
        self.loops.mark_execution_unknown(
            stage["loop_id"],
            stage["id"],
            SESSION,
            identifier(),
            reason="channel connection lost before claim",
        )
        self.assertEqual(self.loops.pending_stages(P, SESSION), [])
        with self.assertRaises(Conflict):
            self.loops.reconcile_execution(
                stage["loop_id"], stage["id"], SESSION, identifier(), observed="running"
            )
        self.loops.reconcile_execution(
            stage["loop_id"], stage["id"], SESSION, identifier(), observed="not_started"
        )
        self.assertEqual(self.loops.pending_stages(P, SESSION)[0]["id"], stage["id"])
        self.ready(stage)
        self.loops.mark_execution_unknown(
            stage["loop_id"],
            stage["id"],
            SESSION,
            identifier(),
            reason="session vanished",
        )
        lost = self.loops.reconcile_execution(
            stage["loop_id"], stage["id"], SESSION, identifier(), observed="lost"
        )
        self.assertEqual(lost["loop"]["status"], "needs_operator")

    def test_round_and_repeated_evidence_limits_escalate(self):
        for config, expected in (
            ({"max_rounds": 1}, "round limit"),
            ({"no_progress_limit": 1}, "without progress"),
        ):
            first = self.evaluate(self.start(**config)["job"])
            finished = self.finish(first["stage"])
            result = self.evaluate(finished["job"])
            self.assertEqual(result["loop"]["status"], "needs_operator")
            self.assertIn(expected, result["loop"]["reason"])
            self.assertIsNone(result["stage"])
            self.loops.control(result["loop"]["id"], "stop", identifier())

    def test_result_is_closed_normalized_and_size_bounded(self):
        result = verdict()
        result["assessment"] = "  Assessment  "
        result["evidence_refs"] *= 2
        normalized = normalize_result(result, self.store.contracts)
        self.assertEqual(normalized["assessment"], "Assessment")
        self.assertEqual(len(normalized["evidence_refs"]), 1)
        for bad in (
            verdict() | {"approved": True},
            verdict() | {"decision": "APPROVE"},
        ):
            with self.assertRaises(ValidationError):
                normalize_result(bad, self.store.contracts)
        for bad in (
            verdict() | {"next_prompt": ""},
            verdict("complete") | {"next_prompt": "do more"},
            verdict() | {"next_prompt": "α" * 6001},
            verdict() | {"findings": ["x" * 4000] * 20},
        ):
            with self.assertRaises(Conflict):
                normalize_result(bad, self.store.contracts)

    def test_transactions_rollback_and_audit_does_not_duplicate_final_text(self):
        with self.assertRaises(RuntimeError), self.store.transaction():
            self.start()
            raise RuntimeError("rollback caller")
        self.assertEqual(self.loops.for_project(P), [])
        self.finish(self.evaluate(self.start()["job"])["stage"])
        events = [
            strict_loads(row[0])
            for row in self.store.db.execute("SELECT body FROM history")
        ]
        loop_events = [e for e in events if e["kind"] == "development_loop.command"]
        self.assertGreater(len(loop_events), 3)
        self.assertNotIn("Synthetic completed response", canonical(loop_events))
        self.assertTrue(all("result_digest" in e["payload"] for e in loop_events))


if __name__ == "__main__":
    unittest.main()
