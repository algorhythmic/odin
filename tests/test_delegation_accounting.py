"""Session cost accounting: claude-code turns report inclusive native-session cost.

A `claude -p --resume` turn reports the cost of the whole resumed native
session, so the session total must count each turn's delta, not the raw sum.
No model, credential or network is used; turns are inserted directly.
"""

import tempfile
import unittest

from odin.contracts import identifier
from test_delegation import DelegationHarness

STAMP = "2026-10-21T10:00:00Z"


class SessionCostAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.harness = DelegationHarness(self.temporary.name)
        self.addCleanup(self.harness.close)
        self.delegation = self.harness.gateway.delegation

    def open_session(self, harness):
        return self.harness.call(
            "delegation_session",
            {
                "action": "create",
                "harness": harness,
                "workspace": str(self.harness.workspace),
                "briefing": "You are a synthetic worker.",
                "model": "fake-model",
                "budget_usd": 5,
            },
        )["session"]["id"]

    def returned_turn(self, session_id, seq, native_session_id, cost_usd, *, turn_id=None):
        """Store one returned turn with a schema-valid body and the real result summary."""
        raw = {
            "exit_code": 0,
            "started_at": STAMP,
            "finished_at": STAMP,
            "timed_out": False,
            "interrupted": False,
            "is_error": False,
            "cost_usd": cost_usd,
            "native_session_id": native_session_id,
            "final_text": "synthetic",
        }
        turn = {
            "schema_version": 1,
            "id": turn_id or identifier(),
            "operation_id": identifier(),
            "actor": "synthetic-test",
            "session": session_id,
            "assignment": identifier(),
            "project": self.harness.project,
            "seq": seq,
            "kind": "assignment" if seq == 1 else "followup",
            "state": "returned",
            "prompt_digest": "0" * 64,
            "prompt_bytes": 1,
            "created_at": STAMP,
            "finished_at": STAMP,
            "runner": None,
            "result": self.delegation._result_summary(raw),
        }
        self.delegation._save_turn(turn)
        return turn

    def view(self, session_id=None):
        session_id = session_id or self.session_id
        return self.delegation._session_view(
            self.harness.service.store.get(session_id),
            self.delegation._options(session_id),
        )

    def test_resumed_native_session_is_not_double_counted(self):
        self.session_id = self.open_session("claude-code")
        # Turn 2's inclusive figure (0.80) already contains turn 1's 0.50.
        self.returned_turn(self.session_id, 1, "native-A", 0.50)
        self.returned_turn(self.session_id, 2, "native-A", 0.80)
        view = self.view()
        self.assertEqual(view["cost_usd_known"], 0.80)  # not 1.30
        self.assertEqual(view["turns_with_unknown_cost"], 0)
        self.assertEqual(view["cost_accounting"], "per_turn_delta_of_inclusive_native_session_cost")

    def test_first_turn_of_rotated_native_session_counts_as_its_own_delta(self):
        self.session_id = self.open_session("claude-code")
        self.returned_turn(self.session_id, 1, "native-A", 0.5)
        self.returned_turn(self.session_id, 2, "native-B", 0.2)
        self.returned_turn(self.session_id, 3, "native-B", 0.3)
        self.assertEqual(self.view()["cost_usd_known"], 0.8)

    def test_unknown_middle_turn_keeps_its_baseline(self):
        self.session_id = self.open_session("claude-code")
        first = self.returned_turn(self.session_id, 1, "native-A", 0.5)
        middle = self.returned_turn(self.session_id, 2, "native-A", None)
        last = self.returned_turn(self.session_id, 3, "native-A", 0.9)
        view = self.view()
        self.assertEqual(view["cost_usd_known"], 0.9)
        self.assertEqual(view["turns_with_unknown_cost"], 1)
        deltas = self._deltas()
        self.assertEqual(deltas[first["id"]], 0.5)
        self.assertIsNone(deltas[middle["id"]])
        self.assertEqual(deltas[last["id"]], 0.4)

    def test_turns_are_ordered_by_seq_not_by_id(self):
        self.session_id = self.open_session("claude-code")
        # The later-created turn carries the earlier seq, so id order is wrong.
        high_id, low_id = sorted([identifier(), identifier()])
        self.returned_turn(self.session_id, 2, "native-A", 0.8, turn_id=low_id)
        self.returned_turn(self.session_id, 1, "native-A", 0.5, turn_id=high_id)
        self.assertEqual(self.view()["cost_usd_known"], 0.8)

    def test_counter_reset_counts_the_reported_cost(self):
        self.session_id = self.open_session("claude-code")
        self.returned_turn(self.session_id, 1, "native-A", 0.8)
        self.returned_turn(self.session_id, 2, "native-A", 0.3)
        self.assertEqual(self.view()["cost_usd_known"], 1.1)

    def test_codex_turn_costs_are_summed_as_reported(self):
        codex_session = self.open_session("codex")
        self.returned_turn(codex_session, 1, "thread-1", 0.5)
        self.returned_turn(codex_session, 2, "thread-1", 0.8)
        view = self.view(codex_session)
        self.assertEqual(view["cost_usd_known"], 1.3)
        self.assertEqual(view["cost_accounting"], "per_turn_reported_cost")

    def _deltas(self):
        from odin.delegation import _cost_deltas

        turns = self.delegation._turns(session=self.session_id)
        return _cost_deltas("claude-code", turns)


if __name__ == "__main__":
    unittest.main()
