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
from odin.delegation import Delegation, DelegationRefused, SESSION_LIFECYCLE_FIELDS
from odin.delegation_runner import run
from odin.executive_mcp import ExecutiveBridge
from odin.executive_service import submit_executive
from odin.gateway import error_result
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

    def _assert_creation_only_options_refused(self, action):
        delegation = self.h.gateway.delegation
        for harness in ("claude-code", "codex"):
            pinned = ({"disallowed_tools": ["Task"], "subagent_model": "haiku",
                       "subagent_model_force": True} if harness == "claude-code" else {})
            session = self._open(harness=harness, **pinned)["session"]["id"]
            for field, value in (("disallowed_tools", ["Agent"]),
                                 ("disallowed_tools", []),
                                 ("subagent_model", "opus"),
                                 ("subagent_model_force", True),
                                 ("subagent_model_force", False)):
                for direct in (False, True):
                    with self.subTest(action=action, harness=harness, field=field,
                                      value=value, direct=direct):
                        options = deepcopy(delegation._options(session))
                        before = deepcopy(self.h.service.store.get(session))
                        bindings = deepcopy(self.h.service.store.records("SessionBinding"))
                        payload = {"action": action, "session_id": session, field: value}
                        with patch.object(delegation, "reconcile") as reconcile:
                            with self.assertRaisesRegex(
                                    DelegationRefused, "^session_options_fixed_at_create$"):
                                if direct:
                                    getattr(delegation, action + "_session")(
                                        payload, project=self.h.project, actor="synthetic",
                                        operation=identifier())
                                else:
                                    self.h.call("delegation_session", payload)
                            reconcile.assert_not_called()
                        self.assertEqual(delegation._options(session), options)
                        self.assertEqual(self.h.service.store.get(session), before)
                        self.assertEqual(self.h.service.store.records("SessionBinding"), bindings)
                        resumed = self.h.call("delegation_session", {
                            "action": "resume", "session_id": session})
                        self.assertEqual(resumed["options"], options)
                        self.assertEqual(resumed["session"]["state"], "idle")
                        self.assertEqual(resumed["session"]["incarnation"], before["incarnation"] + 1)
            self.h.call("delegation_session", {"action": "stop", "session_id": session})

    def test_creation_only_options_resume_are_refused_without_mutation(self):
        self._assert_creation_only_options_refused("resume")

    def test_creation_only_options_stop_are_refused_without_mutation(self):
        self._assert_creation_only_options_refused("stop")

    def test_schema_fields_are_allowlisted_or_refused_on_both_lifecycle_actions(self):
        properties = Contracts().validators["executive-tool-input"].schema[
            "$defs"]["odin_delegation_session"]["properties"]
        values = {
            "harness": "codex", "workspace": str(self.h.workspace),
            "briefing": "Replacement briefing", "model": "replacement-model",
            "effort": "high", "permission_mode": "plan", "sandbox": "read-only",
            "budget_usd": 0, "subagent_model": "opus", "subagent_model_force": False,
            "disallowed_tools": [], "auto_compact_window_tokens": 100000,
            "native_peer_messaging": False, "workstream": "other", "role": "workstream",
        }
        self.assertEqual(SESSION_LIFECYCLE_FIELDS,
                         {"operation_id", "action", "session_id", "reason"})
        self.assertEqual(set(values), set(properties) - SESSION_LIFECYCLE_FIELDS)
        delegation = self.h.gateway.delegation
        for field in properties:
            if field in SESSION_LIFECYCLE_FIELDS:
                continue
            code = ("session_identity_fixed_at_create" if field in {"workstream", "role"}
                    else "session_options_fixed_at_create")
            for harness in ("claude-code", "codex"):
                for action in ("resume", "stop"):
                    for direct in (False, True):
                        with self.subTest(field=field, harness=harness, action=action, direct=direct):
                            session = self._open(harness=harness)["session"]["id"]
                            before = deepcopy(self.h.service.store.get(session))
                            options = deepcopy(delegation._options(session))
                            bindings = deepcopy(self.h.service.store.records("SessionBinding"))
                            payload = {"operation_id": identifier(), "action": action,
                                       "session_id": session, field: values[field]}
                            Contracts().validate_definition(
                                "executive-tool-input", "odin_delegation_session", payload)
                            try:
                                with patch.object(delegation, "reconcile") as reconcile:
                                    with self.assertRaisesRegex(DelegationRefused, "^" + code + "$"):
                                        if direct:
                                            getattr(delegation, action + "_session")(
                                                payload, project=self.h.project, actor="synthetic",
                                                operation=payload["operation_id"])
                                        else:
                                            self.h.call("delegation_session", payload)
                                    reconcile.assert_not_called()
                                self.assertEqual(self.h.service.store.get(session), before)
                                self.assertEqual(delegation._options(session), options)
                                self.assertEqual(self.h.service.store.records("SessionBinding"), bindings)
                            finally:
                                self.h.call("delegation_session", {"action": "stop", "session_id": session})

    def test_codex_sandbox_resume_refused_without_changing_incarnation_or_options(self):
        opened = self._open(harness="codex", sandbox="danger-full-access")
        session = opened["session"]["id"]
        before = deepcopy(self.h.service.store.get(session))
        self.assertEqual(opened["options"]["sandbox"], "danger-full-access")
        with self.assertRaisesRegex(DelegationRefused, "^session_options_fixed_at_create$"):
            self.h.call("delegation_session", {
                "action": "resume", "session_id": session, "sandbox": "read-only"})
        self.assertEqual(self.h.service.store.get(session), before)
        self.assertEqual(self.h.gateway.delegation._options(session), opened["options"])

    def test_workstream_stop_refusal_precedes_signalling(self):
        delegation = self.h.gateway.delegation
        session = self._open(workstream="original")["session"]["id"]
        before = deepcopy(self.h.service.store.get(session))
        running = {"id": identifier(), "session": session, "state": "running",
                   "seq": 1, "runner": {"pid": 424242}}
        with patch.object(delegation, "_turns", return_value=[running]), \
                patch("odin.delegation._runner_alive", return_value=True), \
                patch("odin.delegation.os.kill") as kill, \
                patch.object(delegation, "_save_turn") as save_turn, \
                patch.object(delegation, "reconcile") as reconcile:
            with self.assertRaisesRegex(DelegationRefused, "^session_identity_fixed_at_create$"):
                self.h.call("delegation_session", {
                    "action": "stop", "session_id": session, "workstream": "different"})
            kill.assert_not_called()
            save_turn.assert_not_called()
            reconcile.assert_not_called()
            self.assertEqual(self.h.service.store.get(session), before)
            # Control: the same running turn is signalled by an allowed stop.
            self.h.call("delegation_session", {"action": "stop", "session_id": session})
            kill.assert_called_once()
            save_turn.assert_called_once()

    def test_unknown_lifecycle_field_is_refused_on_direct_calls(self):
        delegation = self.h.gateway.delegation
        properties = Contracts().validators["executive-tool-input"].schema[
            "$defs"]["odin_delegation_session"]["properties"]
        self.assertNotIn("future_creation_option", properties)
        for action in ("resume", "stop"):
            with self.subTest(action=action):
                session = self._open()["session"]["id"]
                before = deepcopy(self.h.service.store.get(session))
                try:
                    with patch.object(delegation, "reconcile") as reconcile:
                        with self.assertRaisesRegex(DelegationRefused, "^session_options_fixed_at_create$"):
                            getattr(delegation, action + "_session")(
                                {"session_id": session, "future_creation_option": False},
                                project=self.h.project, actor="synthetic", operation=identifier())
                        reconcile.assert_not_called()
                    self.assertEqual(self.h.service.store.get(session), before)
                finally:
                    self.h.call("delegation_session", {"action": "stop", "session_id": session})

    def test_lifecycle_allowlisted_fields_succeed_through_gateway_and_direct_calls(self):
        delegation = self.h.gateway.delegation
        for direct in (False, True):
            for harness in ("claude-code", "codex"):
                session = self._open(harness=harness)["session"]["id"]
                for action in ("resume", "stop"):
                    with self.subTest(direct=direct, harness=harness, action=action):
                        payload = {"operation_id": identifier(), "action": action,
                                   "session_id": session, "reason": "Synthetic lifecycle reason"}
                        if direct:
                            result = getattr(delegation, action + "_session")(
                                payload, project=self.h.project, actor="synthetic",
                                operation=payload["operation_id"])
                        else:
                            result = self.h.call("delegation_session", payload)
                        self.assertEqual(result["session"]["state"],
                                         "idle" if action == "resume" else "retired")
                        self.assertEqual(result["session"]["incarnation"], 2)

    def test_lifecycle_identity_and_unknown_session_refusal_precedence(self):
        delegation = self.h.gateway.delegation
        session = self._open()["session"]["id"]
        self.h.call("delegation_session", {"action": "stop", "session_id": session})
        for action in ("resume", "stop"):
            method = getattr(delegation, action + "_session")
            for field in ("workstream", "role"):
                for extra, code in (({field: "workstream"}, "session_identity_fixed_at_create"),
                                    ({field: "workstream", "model": "opus"},
                                     "session_options_fixed_at_create")):
                    with self.subTest(action=action, extra=extra):
                        with self.assertRaisesRegex(DelegationRefused, "^" + code + "$"):
                            method({"session_id": session} | extra, project=self.h.project,
                                   actor="synthetic", operation=identifier())
                        with self.assertRaisesRegex(DelegationRefused, "^unknown_session$"):
                            method({"session_id": identifier()} | extra, project=self.h.project,
                                   actor="synthetic", operation=identifier())

    def test_all_schema_creation_fields_and_unknown_null_are_absent_on_direct_calls(self):
        properties = Contracts().validators["executive-tool-input"].schema[
            "$defs"]["odin_delegation_session"]["properties"]
        nulls = {field: None for field in set(properties) - SESSION_LIFECYCLE_FIELDS}
        nulls["future_creation_option"] = None
        session = self._open()["session"]["id"]
        for action in ("resume", "stop"):
            with self.subTest(action=action):
                result = getattr(self.h.gateway.delegation, action + "_session")(
                    {"session_id": session} | nulls, project=self.h.project,
                    actor="synthetic", operation=identifier())
                self.assertEqual(result["session"]["state"], "idle" if action == "resume" else "retired")

    def test_creation_only_options_stop_refusal_precedes_signalling(self):
        delegation = self.h.gateway.delegation
        session = self._open()["session"]["id"]
        running = {"id": identifier(), "session": session, "state": "running",
                   "seq": 1, "runner": {"pid": 424242}}
        with patch.object(delegation, "_turns", return_value=[running]), \
                patch("odin.delegation._runner_alive", return_value=True), \
                patch("odin.delegation.os.kill") as kill, \
                patch.object(delegation, "_save_turn") as save_turn:
            with self.assertRaisesRegex(DelegationRefused, "^session_options_fixed_at_create$"):
                delegation.stop_session(
                    {"session_id": session, "disallowed_tools": ["Agent"]},
                    project=self.h.project, actor="synthetic", operation=identifier())
            kill.assert_not_called()
            save_turn.assert_not_called()
            # Control: without the field the same stop signals the runner.
            delegation.stop_session({"session_id": session}, project=self.h.project,
                                    actor="synthetic", operation=identifier())
            kill.assert_called_once()

    def test_creation_only_options_refusal_precedence(self):
        delegation = self.h.gateway.delegation
        session = self._open()["session"]["id"]
        with self.assertRaisesRegex(DelegationRefused, "^session_options_fixed_at_create$"):
            delegation.resume_session(
                {"session_id": session, "workstream": "other", "subagent_model": "opus"},
                project=self.h.project, actor="synthetic", operation=identifier())
        with self.assertRaisesRegex(DelegationRefused, "^unknown_session$"):
            delegation.resume_session(
                {"session_id": identifier(), "subagent_model": "opus"},
                project=self.h.project, actor="synthetic", operation=identifier())
        self.h.call("delegation_session", {"action": "stop", "session_id": session})
        retired = self.h.service.store.get(session)
        self.assertEqual(retired["state"], "retired")
        for action in ("resume", "stop"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(DelegationRefused, "^session_options_fixed_at_create$"):
                    getattr(delegation, action + "_session")(
                        {"session_id": session, "subagent_model_force": True},
                        project=self.h.project, actor="synthetic", operation=identifier())
                self.assertEqual(self.h.service.store.get(session), retired)

    def test_creation_only_options_refusal_reaches_mcp(self):
        def socket_handler(command):
            try:
                return submit_executive(self.h.gateway, {"command": command}, self.h.project)
            except DelegationRefused as error:
                return error_result(error, "fake-backend evidence")

        bridge = ExecutiveBridge(self.h.project, socket_handler)
        session = self._open()["session"]["id"]
        for action in ("resume", "stop"):
            with self.subTest(action=action):
                result = bridge.call("odin_delegation_session", {
                    "operation_id": identifier(), "action": action,
                    "session_id": session, "disallowed_tools": ["Agent"]})
                self.assertTrue(result["isError"], result)
                self.assertEqual(result["content"][0]["text"],
                                 "Executive service refused the request: session_options_fixed_at_create.")

    def test_creation_only_options_null_is_absent_for_direct_lifecycle_calls(self):
        # Like workstream/role, None is absent at the lifecycle boundary.
        # The public schema continues to reject null rather than widening create.
        delegation = self.h.gateway.delegation
        nulls = {"disallowed_tools": None, "subagent_model": None, "subagent_model_force": None}
        for harness in ("claude-code", "codex"):
            session = self._open(harness=harness)["session"]["id"]
            options = deepcopy(delegation._options(session))
            for action in ("resume", "stop"):
                for field in nulls:
                    with self.subTest(harness=harness, action=action, field=field):
                        with self.assertRaises(ValidationError):
                            self.h.call("delegation_session", {
                                "action": action, "session_id": session, field: None})
                result = getattr(delegation, action + "_session")(
                    {"session_id": session} | nulls, project=self.h.project,
                    actor="synthetic", operation=identifier())
                self.assertEqual(result["options"], options)
                self.assertEqual(delegation._options(session), options)
                self.assertEqual(result["session"]["state"], "idle" if action == "resume" else "retired")

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
