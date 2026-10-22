"""Synthetic native delegation profile checks; no model is invoked."""

import tempfile
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from jsonschema import ValidationError

from odin.contracts import Contracts, identifier
from odin.delegation import Delegation, DelegationRefused
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

    def _assert_disallowed_turns(self, opened, names):
        session = opened["session"]["id"]
        self.assertEqual(opened["options"]["disallowed_tools"], names)
        first = self._spec(session)["argv"]
        # An observed native session is what selects --resume, rather than
        # merely reopening the Odin session after a service restart.
        earlier = {"id": identifier(), "state": "returned",
                   "result": {"native_session_id": opened["session"]["native_session_id"]}}
        with patch.object(self.h.gateway.delegation, "_turns", return_value=[earlier]):
            resumed = self._spec(session)["argv"]
        for argv, marker in ((first, "--session-id"), (resumed, "--resume")):
            self.assertIn(marker, argv)
            if names:
                self.assertEqual(argv.count("--disallowedTools"), 1)
                index = argv.index(marker)
                self.assertEqual(argv[index - 2:index], ["--disallowedTools", ",".join(names)])
            else:
                self.assertNotIn("--disallowedTools", argv)

    def test_disallowed_tools_default_off_on_start_and_resume(self):
        self.assertNotIn("default_disallowed_tools",
                         self.h.gateway.delegation.config["harnesses"]["claude-code"])
        self._assert_disallowed_turns(self._open(), [])

    def test_legacy_options_without_disallowed_tools_launch_start_and_resume(self):
        opened = self._open(subagent_model="haiku")
        session = opened["session"]["id"]
        options = self.h.gateway.delegation._options(session)
        del options["disallowed_tools"]
        with self.h.service.store.db:
            self.h.service.store.db.execute(
                "UPDATE delegation_sessions SET options=? WHERE id=?",
                (json.dumps(options), session),
            )
        self.h.restart()
        resumed = self.h.call("delegation_session", {"action": "resume", "session_id": session})
        self.assertNotIn("disallowed_tools", resumed["options"])
        first = self._spec(session)
        earlier = {"id": identifier(), "state": "returned",
                   "result": {"native_session_id": opened["session"]["native_session_id"]}}
        with patch.object(self.h.gateway.delegation, "_turns", return_value=[earlier]):
            second = self._spec(session)
        for spec, marker in ((first, "--session-id"), (second, "--resume")):
            with self.subTest(marker=marker):
                self.assertIn(marker, spec["argv"])
                self.assertNotIn("--disallowedTools", spec["argv"])
                directory = self.h.root / spec["turn"]
                directory.mkdir(mode=0o700)
                (directory / "spec.json").write_text(json.dumps(spec))
                self.assertEqual(run(directory), 0)
                result = json.loads((directory / "result.json").read_text())
                self.assertEqual(result["exit_code"], 0)
                self.assertFalse(result["is_error"])
                self.assertEqual(result["native_session_id"], opened["session"]["native_session_id"])

    def test_disallowed_tools_default_survives_restart_and_applies_to_every_turn(self):
        names = ["Agent", "Bash"]
        self.h.write_config(claude_disallowed_tools=names)
        self.h.restart()
        opened = self._open()
        self._assert_disallowed_turns(opened, names)
        # Session options remain pinned even if the operator changes defaults.
        self.h.write_config(claude_disallowed_tools=["Task"])
        self.h.restart()
        session = opened["session"]["id"]
        resumed = self.h.call("delegation_session", {"action": "resume", "session_id": session})
        self._assert_disallowed_turns(resumed, names)
        status = self.h.call("delegation_status", {"session_id": session})["sessions"][0]
        self.assertEqual(status["options"]["disallowed_tools"], names)

    def test_disallowed_tools_session_override(self):
        self.h.gateway.delegation.config["harnesses"]["claude-code"]["default_disallowed_tools"] = ["Agent"]
        self._assert_disallowed_turns(self._open(disallowed_tools=["Task", "Bash"]), ["Task", "Bash"])

    def test_disallowed_tools_empty_session_override_disables_default(self):
        self.h.gateway.delegation.config["harnesses"]["claude-code"]["default_disallowed_tools"] = ["Agent"]
        self._assert_disallowed_turns(self._open(disallowed_tools=[]), [])

    def test_disallowed_tools_accepts_sixteen_names_and_sixty_four_characters(self):
        names = ["A" * 64] + ["Tool_" + str(i) for i in range(15)]
        self._assert_disallowed_turns(self._open(disallowed_tools=names), names)

    def test_disallowed_tools_invalid_payload_and_defaults_are_refused(self):
        delegation = self.h.gateway.delegation
        harness = delegation.config["harnesses"]["claude-code"]
        base = {"action": "create", "harness": "claude-code",
                "workspace": str(self.h.workspace), "briefing": "Synthetic"}
        invalid = [["Bash(git *)"], ["-x"], [""], ["A" * 65], ["A B"],
                   ["A,B"], ["A\n"], ["é"], ["Agent", "Agent"], [1], [{}],
                   "Agent", {}, None, ["Tool" + str(i) for i in range(17)]]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(DelegationRefused, "^invalid_disallowed_tools$"):
                    delegation.open_session(base | {"disallowed_tools": value},
                        project=self.h.project, actor="synthetic", operation=identifier())
                with self.assertRaises(ValidationError):
                    Contracts().validate_definition("executive-tool-input", "odin_delegation_session",
                        base | {"operation_id": identifier(), "disallowed_tools": value})
                harness["default_disallowed_tools"] = value
                try:
                    with self.assertRaises(ValidationError):
                        Contracts().validate("delegation-config", delegation.config)
                    # A valid session override must not hide a bad config default.
                    with self.assertRaisesRegex(DelegationRefused, "^invalid_disallowed_tools$"):
                        delegation.open_session(base | {"disallowed_tools": []},
                            project=self.h.project, actor="synthetic", operation=identifier())
                finally:
                    harness.pop("default_disallowed_tools")

    def test_disallowed_tools_codex_payload_and_config_are_refused(self):
        for value in (["Agent"], []):
            with self.subTest(value=value):
                with self.assertRaisesRegex(DelegationRefused, "^claude_options_unsupported_by_harness$"):
                    self._open(harness="codex", disallowed_tools=value)
        config = deepcopy(self.h.gateway.delegation.config)
        config["harnesses"]["codex"]["default_disallowed_tools"] = []
        with self.assertRaises(ValidationError):
            Contracts().validate("delegation-config", config)

    def test_disallowed_native_workers_omit_delegation_briefing(self):
        opened = self._open(subagent_model="haiku", disallowed_tools=["Agent"])
        session = opened["session"]["id"]
        options = self.h.gateway.delegation._options(session)
        for names in (["Agent"], ["Task"], ["Bash"], []):
            with self.subTest(names=names), patch.object(self.h.gateway.delegation, "_options",
                                                       return_value=options | {"disallowed_tools": names}):
                argv = self._spec(session)["argv"]
                briefing = argv[argv.index("--append-system-prompt") + 1]
                self.assertEqual("Delegate bounded implementation" in briefing,
                                 not bool({"Agent", "Task"}.intersection(names)))

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
