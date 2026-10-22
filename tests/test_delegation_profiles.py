"""Synthetic native delegation profile checks; no model is invoked."""

import tempfile
import json
import sys
import unittest
from pathlib import Path

from odin.contracts import Contracts, identifier
from odin.delegation import Delegation
from odin.delegation_runner import run
from tests.test_delegation import DelegationHarness


class DelegationProfileTests(unittest.TestCase):
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

    def test_claude_native_profile_is_explicit_and_survives_restart(self):
        opened = self._open(subagent_model="haiku", subagent_model_force=True,
                            auto_compact_window_tokens=200000)
        session = opened["session"]["id"]
        self.assertEqual(opened["options"]["model"], "opus")
        self.assertEqual(opened["options"]["subagent_model"], "haiku")
        self.assertTrue(opened["options"]["subagent_model_force"])
        self.assertEqual(opened["fork_subagent"], "disabled_requested_not_verified")
        first = self._spec(session)
        self.assertEqual(first["argv"][first["argv"].index("--model") + 1], "opus")
        self.assertIn("Delegate bounded implementation", first["argv"][first["argv"].index("--append-system-prompt") + 1])
        self.assertEqual(first["env"], {
            "CLAUDE_CONFIG_DIR": str(self.h.config_dir),
            "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
            "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1",
            "CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL": "haiku",
            "CLAUDE_CODE_FORK_SUBAGENT": "0",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000",
        })
        self.h.restart()
        resumed = self.h.call("delegation_session", {"action": "resume", "session_id": session})
        self.assertEqual(resumed["options"], opened["options"])
        self.assertEqual(resumed["fork_subagent"], "disabled_requested_not_verified")
        status = self.h.call("delegation_status", {"session_id": session})["sessions"][0]
        self.assertEqual(status["fork_subagent"], "disabled_requested_not_verified")
        second = self._spec(session)
        self.assertEqual(second["env"], first["env"])

    def test_subagent_model_without_force_sets_only_the_model_variable(self):
        opened = self._open(subagent_model="haiku", subagent_model_force=False)
        self.assertNotIn("fork_subagent", opened)
        spec = self._spec(opened["session"]["id"])
        self.assertEqual(spec["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "haiku")
        for key in ("CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
                    "CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL",
                    "CLAUDE_CODE_FORK_SUBAGENT"):
            self.assertNotIn(key, spec["env"])

    def test_unsupported_harness_and_invalid_force_are_refused(self):
        # Direct lifecycle validation also protects any caller that bypasses
        # the public command schema.
        delegation = self.h.gateway.delegation
        payload = {"harness": "codex", "workspace": str(self.h.workspace),
                   "briefing": "Synthetic", "subagent_model": "haiku"}
        with self.assertRaisesRegex(Exception, "claude_options_unsupported_by_harness"):
            delegation.open_session(payload, project=self.h.project,
                                    actor="synthetic", operation=identifier())
        payload["harness"] = "claude-code"
        payload["subagent_model"] = None
        payload["subagent_model_force"] = True
        with self.assertRaisesRegex(Exception, "subagent_model_required_for_force"):
            delegation.open_session(payload, project=self.h.project,
                                    actor="synthetic", operation=identifier())
        payload["subagent_model"] = "haiku"
        delegation.versions["claude-code"] = "2.1.256 (synthetic)"
        with self.assertRaisesRegex(Exception, "subagent_model_force_unsupported_by_claude_version"):
            delegation.open_session(payload, project=self.h.project,
                                    actor="synthetic", operation=identifier())

    def test_result_summary_keeps_observed_usage_distinct_from_requested_options(self):
        result = {"exit_code": 0, "started_at": "2026-01-01T00:00:00Z",
                  "finished_at": "2026-01-01T00:00:01Z", "timed_out": False,
                  "interrupted": False, "is_error": False, "final_text": "synthetic",
                  "usage": {"input_tokens": 15},
                  "usage_scope": "inclusive_aggregate",
                  "model_usage": {"claude-opus-5-5": {"inputTokens": 10},
                                  "claude-haiku-5-5": {"inputTokens": 5}},
                  "observed_model": "claude-opus-5-5"}
        summary = Delegation._result_summary(result)
        for key in ("usage", "usage_scope", "model_usage", "observed_model"):
            self.assertEqual(summary[key], result[key])

    def test_runner_retains_claude_model_usage(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            body = {"result": "synthetic", "model": "claude-opus-5-5",
                    "usage": {"input_tokens": 15},
                    "modelUsage": {"claude-opus-5-5": {"inputTokens": 10},
                                   "claude-haiku-5-5": {"inputTokens": 5}}}
            spec = {"turn": identifier(), "harness": "claude-code",
                    "argv": [sys.executable, "-c", "import json; print(json.dumps(" + repr(body) + "))"],
                    "cwd": root, "env": {}, "timeout_seconds": 30}
            (directory / "spec.json").write_text(json.dumps(spec))
            self.assertEqual(run(directory), 0)
            result = json.loads((directory / "result.json").read_text())
            Contracts().validate("delegation-result", result)
            self.assertEqual(result["usage_scope"], "inclusive_aggregate")
            self.assertEqual(result["model_usage"], body["modelUsage"])
            self.assertEqual(result["observed_model"], "claude-opus-5-5")


if __name__ == "__main__":
    unittest.main()
