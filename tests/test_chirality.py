import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.budgets import Budget
from odin.chirality import Chirality
from odin.store import Conflict, Store, digest

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text())


class ChiralityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.budget = Budget(self.store)
        self.config = fixture("chirality-config.json")
        self.packet = fixture("chirality-packet.json")
        self.budget.create("consult", 120, 6, 0)
        self.protocol = Chirality(self.store, self.budget)
        self.source = copy.deepcopy(self.packet["source"])

    def current(self, pinned):
        return copy.deepcopy(self.source)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def restart(self):
        self.store.close()
        self.store = Store(Path(self.tmp.name))
        self.budget = Budget(self.store)
        self.protocol = Chirality(self.store, self.budget)

    def response(
        self, role, recommendation, *, status="complete", cost=5, round_number=1
    ):
        packet = self.protocol.status("consultation")["packets"][round_number - 1]
        return {
            "schema_version": 1,
            "consultation_id": "consultation",
            "invocation_id": f"chirality:consultation:{round_number}:{role}",
            "round": round_number,
            "role": role,
            "requested_provider": "fixture-provider",
            "requested_harness": "fixture-harness",
            "requested_harness_version": "1",
            "requested_effort": None if role == "fable" else "bounded",
            "requested_config_revision": "fixture-model-roles-v1",
            "resolved_provider": "fixture-provider",
            "resolved_harness": "fixture-harness",
            "resolved_harness_version": "1",
            "resolved_effort": None if role == "fable" else "bounded",
            "requested_model": role + "-fixture",
            "resolved_model": role + "-fixture",
            "packet_revision": packet["packet"]["revision"],
            "packet_digest": packet["digest"],
            "status": status,
            "recommendation": recommendation,
            "evidence": ["synthetic evidence"],
            "assumptions": ["synthetic assumption"],
            "objections": ["synthetic objection"],
            "actual_microusd": cost,
        }

    def test_disabled_default_and_atomic_total_admission(self):
        disabled = copy.deepcopy(self.config)
        disabled["enabled"] = False
        with self.assertRaises(Conflict):
            self.protocol.start(
                "consultation",
                disabled,
                self.packet,
                "consult",
                context_current=self.current,
            )
        self.store.db.execute("UPDATE budgets SET cap=119 WHERE id='consult'")
        with self.assertRaises(Conflict):
            self.protocol.start(
                "consultation",
                self.config,
                self.packet,
                "consult",
                context_current=self.current,
            )
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM reservations").fetchone()[0], 0
        )

    def test_independent_packet_dissent_idempotency_restart(self):
        first = self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.assertEqual(first["packets"][0]["digest"], digest(self.packet))
        self.assertEqual(
            self.protocol.start(
                "consultation",
                self.config,
                self.packet,
                "consult",
                context_current=self.current,
            )["id"],
            "consultation",
        )
        self.protocol.respond(
            "consultation",
            self.response("fable", "proceed"),
            context_current=self.current,
        )
        self.restart()
        astra = self.response("astra", "hold")
        self.protocol.respond("consultation", astra, context_current=self.current)
        self.protocol.respond("consultation", astra, context_current=self.current)
        with self.assertRaises(Conflict):
            self.protocol.respond(
                "consultation",
                astra | {"recommendation": "altered"},
                context_current=self.current,
            )
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "followup_available")
        synthesis = state["syntheses"][0]
        self.assertFalse(synthesis["agreement"])
        self.assertEqual(
            [p["recommendation"] for p in synthesis["positions"]], ["proceed", "hold"]
        )
        self.assertEqual([p["role"] for p in synthesis["dissent"]], ["fable", "astra"])
        self.assertEqual(
            [p["role"] for p in synthesis["unresolved"]], ["fable", "astra"]
        )
        self.assertEqual(synthesis["authority"], "advice_only")
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            10,
        )

    def test_stale_bounds_followup_and_round_cap(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        bad = self.response("fable", "x") | {"packet_digest": "0" * 64}
        with self.assertRaises(Conflict):
            self.protocol.respond("consultation", bad, context_current=self.current)
        with self.assertRaises(ValueError):
            self.protocol.respond(
                "consultation",
                self.response("fable", "x" * 301),
                context_current=self.current,
            )
        self.protocol.respond(
            "consultation", self.response("fable", "go"), context_current=self.current
        )
        self.protocol.respond(
            "consultation", self.response("astra", "wait"), context_current=self.current
        )
        self.protocol.close_round("consultation", context_current=self.current)
        revised = self.packet | {
            "revision": 2,
            "target": "Resolve the fixture evidence disagreement",
        }
        self.protocol.followup("consultation", revised, context_current=self.current)
        with self.assertRaises(Conflict):
            self.protocol.respond(
                "consultation",
                self.response("fable", "go", round_number=1)
                | {"role": "astra", "requested_model": "astra-fixture"},
                context_current=self.current,
            )
        self.protocol.respond(
            "consultation",
            self.response("fable", "go", round_number=2),
            context_current=self.current,
        )
        self.protocol.respond(
            "consultation",
            self.response("astra", "wait", round_number=2),
            context_current=self.current,
        )
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "escalated")
        self.assertEqual(len(state["syntheses"]), 2)
        with self.assertRaises(Conflict):
            self.protocol.followup(
                "consultation", revised | {"revision": 3}, context_current=self.current
            )

    def test_partial_unknown_timeout_and_parent_stop(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.protocol.respond(
            "consultation",
            self.response("fable", "draft", status="partial", cost=None),
            context_current=self.current,
        )
        self.store.stop("synthetic parent stop")
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "escalated")
        self.assertEqual(state["syntheses"][0]["positions"][1]["status"], "unknown")
        self.assertEqual(
            self.store.db.execute(
                "SELECT count(*) FROM reservations WHERE state='unknown'"
            ).fetchone()[0],
            2,
        )
        self.assertEqual(
            self.store.db.execute(
                "SELECT count(*) FROM reservations WHERE state='settled'"
            ).fetchone()[0],
            4,
        )
        self.restart()
        self.assertEqual(self.protocol.status("consultation")["state"], "escalated")

    def test_fixture_examples_timeout_and_between_round_termination(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        for example in fixture("chirality-responses.json")["examples"]:
            self.store.contracts.validate("chirality-response", example)
            self.protocol.respond("consultation", example, context_current=self.current)
        state = self.protocol.close_round(
            "consultation", 3, context_current=self.current
        )
        self.assertEqual(state["state"], "followup_available")
        self.store.stop("synthetic")
        state = self.protocol.terminate_between_rounds("consultation")
        self.assertEqual(state["state"], "escalated")
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            15,
        )
        with self.assertRaises(Conflict):
            self.protocol.followup(
                "consultation",
                self.packet | {"revision": 2, "target": "synthetic"},
                context_current=self.current,
            )

    def test_timeout_cost_is_recorded_without_claiming_consensus(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.protocol.respond(
            "consultation", self.response("fable", "go"), context_current=self.current
        )
        self.protocol.respond(
            "consultation",
            self.response("astra", "", status="timeout", cost=7),
            context_current=self.current,
        )
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "escalated")
        self.assertFalse(state["syntheses"][0]["agreement"])
        self.assertEqual(state["syntheses"][0]["positions"][1]["status"], "timeout")
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            12,
        )

    def test_cross_consultation_replay_and_unapproved_execution_path(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.budget.create("consult2", 120, 6, 0)
        self.protocol.start(
            "other", self.config, self.packet, "consult2", context_current=self.current
        )
        response = self.response("fable", "go")
        with self.assertRaises(Conflict):
            self.protocol.respond("other", response, context_current=self.current)
        with self.assertRaises(Conflict):
            self.protocol.respond(
                "consultation",
                response | {"resolved_harness": "other-harness"},
                context_current=self.current,
            )
        with self.assertRaises(Conflict):
            self.protocol.respond(
                "consultation",
                response | {"requested_config_revision": "wrong-config"},
                context_current=self.current,
            )
        with self.assertRaises(Conflict):
            self.protocol.respond(
                "consultation",
                response | {"resolved_model": "unapproved-model"},
                context_current=self.current,
            )
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            0,
        )

    def test_stale_context_is_held_with_actual_cost_and_cannot_converge(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.source["assignment_revision"] = 2
        stale = self.response("fable", "go", cost=7)
        state = self.protocol.respond(
            "consultation", stale, context_current=self.current
        )
        self.assertEqual(state["held_responses"][0]["reason"], "stale_source_context")
        self.protocol.respond("consultation", stale, context_current=self.current)
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "escalated")
        self.assertEqual(state["syntheses"][0]["positions"][0]["status"], "unknown")
        self.assertEqual(state["held_responses"][0]["response"]["actual_microusd"], 7)
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            7,
        )
        self.restart()
        self.assertEqual(len(self.protocol.status("consultation")["held_responses"]), 1)

    def test_same_recommendation_with_objection_is_not_agreement(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        fable = self.response("fable", "go")
        astra = self.response("astra", "go")
        astra["objections"] = []
        self.protocol.respond("consultation", fable, context_current=self.current)
        self.protocol.respond("consultation", astra, context_current=self.current)
        synthesis = self.protocol.close_round(
            "consultation", context_current=self.current
        )["syntheses"][0]
        self.assertFalse(synthesis["agreement"])
        self.assertEqual(
            synthesis["unresolved"],
            [{"role": "fable", "objection": "synthetic objection"}],
        )

    def test_context_moves_after_responses_before_close(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        for role in ("fable", "astra"):
            response = self.response(role, "go")
            response["objections"] = []
            self.protocol.respond(
                "consultation", response, context_current=self.current
            )
        self.source["source_revision"] = 2
        state = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(state["state"], "escalated")
        self.assertFalse(state["syntheses"][0]["agreement"])
        self.assertIn("stale_source_context", state["syntheses"][0]["closure_reasons"])
        self.assertEqual(len(state["responses"]), 2)

    def test_expired_deadline_refuses_start_and_escalates_close(self):
        expired = copy.deepcopy(self.config)
        expired["deadline_at"] = "2000-01-01T00:00:00Z"
        with self.assertRaises(Conflict):
            self.protocol.start(
                "consultation",
                expired,
                self.packet,
                "consult",
                context_current=self.current,
            )
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        for role in ("fable", "astra"):
            response = self.response(role, "go")
            response["objections"] = []
            self.protocol.respond(
                "consultation", response, context_current=self.current
            )
        with patch.object(Chirality, "_expired", return_value=True):
            state = self.protocol.close_round(
                "consultation", context_current=self.current
            )
        self.assertEqual(state["state"], "escalated")
        self.assertIn("deadline_expired", state["syntheses"][0]["closure_reasons"])

    def test_late_usage_reconciles_unknown_without_reopening_conclusion(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        self.protocol.respond(
            "consultation", self.response("fable", "go"), context_current=self.current
        )
        closed = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(closed["state"], "escalated")
        self.assertEqual(closed["syntheses"][0]["positions"][1]["status"], "unknown")
        late = self.response("astra", "go", cost=9)
        state = self.protocol.record_late(
            "consultation", late, context_current=self.current
        )
        self.assertEqual(state["state"], "escalated")
        self.assertEqual(state["syntheses"], closed["syntheses"])
        self.assertEqual(state["late_responses"][0], late)
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            14,
        )
        self.protocol.record_late("consultation", late, context_current=self.current)
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            14,
        )
        with self.assertRaises(Conflict):
            self.protocol.record_late(
                "consultation",
                late | {"actual_microusd": 10},
                context_current=self.current,
            )

    def test_unknown_harness_version_remains_explicit_null(self):
        config = copy.deepcopy(self.config)
        config["branches"][0]["harness_version"] = None
        self.protocol.start(
            "consultation", config, self.packet, "consult", context_current=self.current
        )
        response = self.response("fable", "go")
        response["requested_harness_version"] = None
        response["resolved_harness_version"] = None
        self.protocol.respond("consultation", response, context_current=self.current)
        self.assertIsNone(
            self.protocol.status("consultation")["responses"][0][
                "resolved_harness_version"
            ]
        )

    def test_reconcile_completed_unknown_usage_after_stale_lineage(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        response = self.response("fable", "go", cost=None)
        response["objections"] = []
        other = self.response("astra", "go", cost=5)
        other["objections"] = []
        self.protocol.respond("consultation", response, context_current=self.current)
        self.protocol.respond("consultation", other, context_current=self.current)
        before = self.protocol.close_round("consultation", context_current=self.current)
        self.assertEqual(before["state"], "advice_ready")
        self.source["assignment_revision"] = 2
        self.restart()
        after = self.protocol.reconcile_usage(
            "consultation", response["invocation_id"], 7
        )
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["syntheses"], before["syntheses"])
        self.assertEqual(after["responses"], before["responses"])
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            12,
        )
        self.protocol.reconcile_usage("consultation", response["invocation_id"], 7)
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            12,
        )
        with self.assertRaises(Conflict):
            self.protocol.reconcile_usage("consultation", response["invocation_id"], 8)
        with self.assertRaises(Conflict):
            self.protocol.reconcile_usage(
                "consultation", "chirality:consultation:1:unknown", 1
            )
        with self.assertRaises(ValueError):
            self.protocol.reconcile_usage("consultation", response["invocation_id"], -1)
        with self.assertRaises(Conflict):
            self.protocol.reconcile_usage("consultation", other["invocation_id"], 5)

    def test_reconcile_late_response_with_unknown_usage(self):
        self.protocol.start(
            "consultation",
            self.config,
            self.packet,
            "consult",
            context_current=self.current,
        )
        closed = self.protocol.close_round("consultation", context_current=self.current)
        late = self.response("fable", "go", cost=None)
        self.protocol.record_late("consultation", late, context_current=self.current)
        self.source["source_revision"] = 2
        after = self.protocol.reconcile_usage("consultation", late["invocation_id"], 13)
        self.assertEqual(after["syntheses"], closed["syntheses"])
        self.assertIsNone(after["late_responses"][0]["actual_microusd"])
        self.assertEqual(
            self.store.db.execute(
                "SELECT spent FROM budgets WHERE id='consult'"
            ).fetchone()[0],
            13,
        )
        self.assertEqual(
            self.store.db.execute(
                "SELECT state,actual FROM reservations WHERE id=?",
                (late["invocation_id"],),
            ).fetchone()[:],
            ("settled", 13),
        )


if __name__ == "__main__":
    unittest.main()
