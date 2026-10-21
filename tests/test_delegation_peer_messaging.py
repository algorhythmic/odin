"""Synthetic checks for opt-in Claude native peer messaging; no model runs."""

import tempfile
import unittest

from odin.contracts import identifier
from odin.native_peer import peer_name
from tests.test_delegation import DelegationHarness


class DelegationPeerMessagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.h = DelegationHarness(temporary.name)
        self.addCleanup(self.h.close)

    def _open(self, harness="claude-code", **options):
        return self.h.call("delegation_session", {
            "action": "create", "harness": harness,
            "workspace": str(self.h.workspace), "briefing": "Synthetic project instruction.",
            "model": "opus", "budget_usd": 5,
        } | options)

    def _spec(self, session_id):
        delegation = self.h.gateway.delegation
        session = self.h.service.store.get(session_id)
        assignment = {"limits": {"iterations": 2, "budget_usd": 0.5}}
        turn = {"id": identifier()}
        return delegation._spec(session, assignment, turn, "Synthetic task")

    def test_opt_in_launch_and_status_are_requested_not_observed(self):
        opened = self._open(native_peer_messaging=True)
        session_id = opened["session"]["id"]
        native_id = opened["session"]["native_session_id"]
        name = peer_name(native_id, "worker")
        self.assertTrue(opened["options"]["native_peer_messaging"])
        self.assertEqual(opened["native_peer_name"], name)
        self.assertEqual(opened["native_peer_transport"], "requested_unverified")
        self.assertFalse(opened["native_session_observed"])
        self.assertFalse(opened["capabilities"]["inject_mid_turn"])
        first = self._spec(session_id)
        argv = first["argv"]
        self.assertEqual(argv[argv.index("--settings") + 1],
                         '{"crossSessionInbound":"accept"}')
        self.assertEqual(argv[argv.index("--name") + 1], name)
        self.assertEqual(argv[argv.index("--session-id") + 1], native_id)
        self.assertIn(name, argv[argv.index("--append-system-prompt") + 1])
        self.assertIn("SendMessage", argv[argv.index("--append-system-prompt") + 1])
        self.assertNotIn("crossSessionInbound", first["env"])
        self.h.restart()
        resumed = self.h.call("delegation_session", {
            "action": "resume", "session_id": session_id,
        })
        self.assertEqual(resumed["options"], opened["options"])
        self.assertEqual(resumed["native_peer_name"], name)
        self.assertEqual(self._spec(session_id)["argv"], argv)

    def test_default_launch_does_not_expose_peer_address_or_settings(self):
        opened = self._open()
        self.assertFalse(opened["options"]["native_peer_messaging"])
        self.assertIsNone(opened["native_peer_name"])
        self.assertEqual(opened["native_peer_transport"], "disabled")
        argv = self._spec(opened["session"]["id"])["argv"]
        self.assertNotIn("--settings", argv)
        self.assertNotIn("--name", argv)

    def test_opt_in_config_default_is_persisted_on_session_creation(self):
        self.h.write_config(claude_native_peer_messaging=True)
        self.h.restart()
        opened = self._open()
        self.assertTrue(opened["options"]["native_peer_messaging"])
        self.assertEqual(opened["native_peer_transport"], "requested_unverified")
        self.assertIn("--settings", self._spec(opened["session"]["id"])["argv"])

    def test_codex_and_unsupported_claude_version_refused(self):
        with self.assertRaisesRegex(Exception, "claude_options_unsupported_by_harness"):
            self._open(harness="codex", native_peer_messaging=True)
        self.h.gateway.delegation.versions["claude-code"] = "2.1.223"
        with self.assertRaisesRegex(Exception, "native_peer_messaging_unsupported_by_claude_version"):
            self._open(native_peer_messaging=True)
        self.h.gateway.delegation.versions["claude-code"] = "unknown"
        with self.assertRaisesRegex(Exception, "native_peer_messaging_unsupported_by_claude_version"):
            self._open(native_peer_messaging=True)


if __name__ == "__main__":
    unittest.main()
