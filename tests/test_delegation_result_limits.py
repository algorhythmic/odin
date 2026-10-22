"""Delegation.result() size limits and refusals, on the synthetic fake harness.

No model, credential or network is used.
"""

import tempfile
import unittest

from jsonschema import ValidationError
from odin.contracts import canonical, identifier, strict_loads
from odin.delegation import DelegationRefused
from test_delegation import DelegationHarness

DEFAULT_LIMIT = 65536


class DelegationResultLimitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.h = DelegationHarness(self.temporary.name)
        self.addCleanup(self.h.close)
        self.session = self.h.call(
            "delegation_session",
            {
                "action": "create",
                "harness": "claude-code",
                "workspace": str(self.h.workspace),
                "briefing": "You are a synthetic worker.",
                "model": "fake-model",
                "budget_usd": 5,
            },
        )["session"]["id"]

    def run_turn(self, instructions, wait_for="returned"):
        h = self.h
        assigned = h.call(
            "delegation_assign",
            {
                "session_id": self.session,
                "objective": "Synthetic objective",
                "criteria": [{"id": "c1", "text": "worker reports"}],
                "scope": "synthetic scope",
                "output_contract": "final text",
                "instructions": instructions,
                "limits": {"iterations": 3, "budget_usd": 0.5},
            },
        )
        h.gateway.delegation.launch_pending()
        if wait_for:
            h.wait(
                lambda: (
                    h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                    == wait_for
                )
            )
        return assigned

    def result(self, **payload):
        return self.h.gateway.delegation.result(payload, project=self.h.project)

    def finished(self, instructions):
        """Run a turn and return (assigned, final_text, its UTF-8 byte length)."""
        assigned = self.run_turn(instructions)
        full = self.h.call("delegation_result", {"turn_id": assigned["turn"]})
        self.assertTrue(full["available"])
        text = full["final_text"]
        return assigned, text, len(text.encode("utf-8"))

    def set_final_text(self, assigned, text):
        path = (
            self.h.state
            / "delegations"
            / self.session
            / assigned["turn"]
            / "result.json"
        )
        body = strict_loads(path.read_text())
        path.write_text(canonical(body | {"final_text": text}))

    def test_default_limit_is_65536_bytes(self):
        assigned = self.run_turn("hi")
        # 21845 three-byte characters are 65535 bytes; the default limit is bytes.
        self.set_final_text(assigned, "\u20ac" * 21845 + "a")
        at_limit = self.h.call("delegation_result", {"turn_id": assigned["turn"]})
        self.assertTrue(at_limit["available"])
        self.assertEqual(len(at_limit["final_text"].encode()), DEFAULT_LIMIT)
        self.set_final_text(assigned, "\u20ac" * 21845 + "ab")
        over = self.h.call("delegation_result", {"turn_id": assigned["turn"]})
        self.assertFalse(over["available"])
        self.assertEqual(over["reason"], "final_text_exceeds_max_bytes")
        self.assertEqual(over["final_text_bytes"], DEFAULT_LIMIT + 1)
        self.assertNotIn("final_text", over)
        # 65537 characters would not fit either; the count is bytes, not characters.
        self.set_final_text(assigned, "x" * (DEFAULT_LIMIT + 1))
        self.assertFalse(
            self.h.call("delegation_result", {"turn_id": assigned["turn"]})["available"]
        )

    def test_oversize_multibyte_text_reports_bytes_and_leaks_nothing(self):
        assigned = self.run_turn("é" * 3000)
        prefix = len(b"worker says: ")
        # Each é is two UTF-8 bytes, so bytes differ from characters.
        full = self.result(turn_id=assigned["turn"])
        self.assertTrue(full["available"])
        text = full["final_text"]
        size = len(text.encode("utf-8"))
        self.assertGreater(size, len(text))
        self.assertEqual(size, prefix + 6000)

        refused = self.result(turn_id=assigned["turn"], max_bytes=size - 1)
        self.assertFalse(refused["available"])
        self.assertEqual(refused["reason"], "final_text_exceeds_max_bytes")
        self.assertEqual(refused["final_text_bytes"], size)
        self.assertNotEqual(refused["final_text_bytes"], len(text))
        self.assertIn("result.json", refused["transcript_paths"])
        self.assertIn("stdout.log", refused["transcript_paths"])
        self.assertNotIn("final_text", refused)
        self.assertNotIn("é" * 10, repr(refused))

    def test_text_exactly_at_the_limit_is_returned_in_full(self):
        assigned, text, size = self.finished("é" * 1500)
        at_limit = self.result(turn_id=assigned["turn"], max_bytes=size)
        self.assertTrue(at_limit["available"])
        self.assertEqual(at_limit["final_text"], text)
        over = self.result(turn_id=assigned["turn"], max_bytes=size - 1)
        self.assertFalse(over["available"])
        self.assertEqual(over["final_text_bytes"], size)

    def test_small_limit_with_short_text_and_assignment_lookup(self):
        assigned = self.run_turn("hi")
        result = self.h.call(
            "delegation_result",
            {"assignment_id": assigned["assignment"], "max_bytes": 2048},
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["final_text"], "worker says: hi")
        self.assertEqual(
            self.result(turn_id=assigned["turn"], max_bytes=1)["reason"],
            "final_text_exceeds_max_bytes",
        )

    def test_corrupt_result_file_is_unreadable(self):
        assigned = self.run_turn("hi")
        path = (
            self.h.state
            / "delegations"
            / self.session
            / assigned["turn"]
            / "result.json"
        )
        path.write_text("{not json")
        result = self.result(turn_id=assigned["turn"])
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "result_unreadable")
        self.assertNotIn("final_text", result)
        self.assertIn("result.json", result["transcript_paths"])
        # A non-UTF-8 file is unreadable too.
        path.write_bytes(b"\xff\xfe\x00")
        result = self.result(turn_id=assigned["turn"])
        self.assertEqual(result["reason"], "result_unreadable")

    def test_unfinished_turn_is_refused(self):
        assigned = self.run_turn("SLEEP 3 then finish", wait_for=None)
        with self.assertRaises(DelegationRefused) as refused:
            self.result(turn_id=assigned["turn"])
        self.assertEqual(str(refused.exception), "turn_not_finished")
        with self.assertRaises(DelegationRefused) as refused:
            self.result(assignment_id=assigned["assignment"])
        self.assertEqual(str(refused.exception), "no_finished_turn")
        # Let the runner finish so no detached process outlives the test.
        self.h.wait(
            lambda: (
                self.h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "returned"
            )
        )

    def test_turn_or_assignment_is_required(self):
        with self.assertRaises(DelegationRefused) as refused:
            self.result()
        self.assertEqual(str(refused.exception), "turn_or_assignment_required")
        # The tool schema rejects it before it reaches Delegation.result().
        with self.assertRaises(ValidationError):
            self.h.call("delegation_result", {})

    def test_out_of_range_max_bytes_is_rejected_by_the_tool_schema(self):
        assigned = self.run_turn("hi")
        for bad in (0, 2047, DEFAULT_LIMIT + 1, "4096", 4096.5):
            with self.subTest(max_bytes=bad), self.assertRaises(ValidationError):
                self.h.call(
                    "delegation_result",
                    {"turn_id": assigned["turn"], "max_bytes": bad},
                )
        for good in (2048, DEFAULT_LIMIT):
            result = self.h.call(
                "delegation_result", {"turn_id": assigned["turn"], "max_bytes": good}
            )
            self.assertTrue(result["available"])

    def test_unknown_turn_is_refused(self):
        with self.assertRaises(Exception) as refused:
            self.result(turn_id=identifier())
        self.assertTrue(str(refused.exception))


if __name__ == "__main__":
    unittest.main()
