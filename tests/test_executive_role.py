"""Staged delegation-first executive role; no native process or model call."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin import executive_runtime as runtime


class ExecutiveRoleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.state = root / "state"
        self.login = root / "login"
        runtime.prepare(self.state, config_dir=self.login,
                        project="01K00000000000000000000001",
                        claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass

    def test_delegated_role_merges_pending_context_peer_and_loop(self):
        runtime.enable_development_loop(self.state)
        with runtime._owned_runtime(self.state):
            pass
        before = runtime.status(self.state)["configuration"]
        hook = self.state / "executive-pilot" / f"settings-development-loop-{before['native_session_id']}.json"
        original_hook = hook.read_bytes()
        runtime.configure_context(self.state, auto_compact_window_tokens=200000)
        runtime.configure_peer_messaging(self.state, enabled=True)
        staged = runtime.configure_execution_role(self.state, implementation_mode="delegated")
        self.assertTrue(staged["pending_activation"])
        self.assertEqual(runtime.status(self.state)["implementation_mode_configured"], "direct")
        self.assertEqual(runtime.status(self.state)["pending_implementation_mode"], "delegated")
        self.assertEqual(hook.read_bytes(), original_hook)
        argv = runtime.launch_spec(self.state, resume=True)["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "default")
        self.assertEqual(argv[argv.index("--disallowedTools") + 1],
                         ",".join(runtime.INTERVENTION_DISALLOWED_TOOLS))
        denied = set(argv[argv.index("--disallowedTools") + 1].split(","))
        self.assertTrue({"Monitor", "Workflow"}.issubset(denied))
        self.assertNotIn("REPL", denied)
        self.assertEqual(argv[argv.index("--resume") + 1], before["native_session_id"])
        self.assertIn("--name", argv)
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertIn("hooks", settings)
        self.assertEqual(settings["crossSessionInbound"], "accept")
        prompt = argv[argv.index("--append-system-prompt") + 1]
        self.assertIn("separate resumable Claude Code Opus project orchestrator", prompt)
        self.assertIn("Haiku subagents", prompt)
        self.assertNotIn("edit code and documentation, execute commands", prompt)
        with runtime._owned_runtime(self.state):
            pass
        current = runtime.status(self.state)
        self.assertEqual(current["implementation_mode_configured"], "delegated")
        self.assertFalse(current["pending_activation_requires_resume"])
        self.assertEqual(current["configuration"]["native_session_id"], before["native_session_id"])
        self.assertEqual(current["configuration"]["auto_compact_window_tokens"], 200000)
        self.assertTrue(current["configuration"]["native_peer_messaging"])
        self.assertTrue(current["configuration"]["development_loop"])
        self.assertEqual(hook.read_bytes(), original_hook)

    def test_explicit_direct_rollback_and_legacy_default(self):
        initial = runtime.launch_spec(self.state)["argv"]
        self.assertNotIn("--disallowedTools", initial)
        self.assertIn("edit code and documentation, execute commands",
                      initial[initial.index("--append-system-prompt") + 1])
        runtime.configure_execution_role(self.state, implementation_mode="delegated")
        cancelled = runtime.configure_execution_role(self.state, implementation_mode="direct")
        self.assertFalse(cancelled["pending_activation"])
        self.assertNotIn("--disallowedTools", runtime.launch_spec(self.state)["argv"])
        runtime.configure_execution_role(self.state, implementation_mode="delegated")
        with runtime._owned_runtime(self.state):
            pass
        rollback = runtime.configure_execution_role(self.state, implementation_mode="direct")
        self.assertTrue(rollback["pending_activation"])
        self.assertEqual(runtime.status(self.state)["implementation_mode_configured"], "delegated")
        self.assertEqual(runtime.status(self.state)["pending_implementation_mode"], "direct")
        self.assertNotIn("--disallowedTools", runtime.launch_spec(self.state)["argv"])
        with runtime._owned_runtime(self.state):
            pass
        self.assertEqual(runtime.status(self.state)["implementation_mode_configured"], "direct")

    def test_intervention_requires_fail_closed_hook_support(self):
        runtime.configure_execution_role(self.state, implementation_mode="delegated")
        with patch.object(runtime, "_probe_output", side_effect=[
            "2.1.294 (Claude Code)",
            " ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS) + " --disallowedTools --settings",
        ]):
            self.assertIn("blocking-hook-failure>=2.1.295", runtime.probe(self.state)["missing_flags"])

    def test_profile_version_and_capability_guard(self):
        with self.assertRaises(ValueError):
            runtime.configure_execution_role(self.state, implementation_mode="invalid")
        root = self.state.parent
        older = root / "older-state"
        runtime.prepare(older, config_dir=root / "older-login",
                        project="01K00000000000000000000002",
                        claude_binary=sys.executable, python_executable=sys.executable)
        with self.assertRaises(PermissionError):
            runtime.configure_execution_role(older, implementation_mode="delegated")
        with patch.object(runtime, "_probe_output", side_effect=[
            "2.1.303 (Claude Code)",
            " ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS),
        ]):
            runtime.configure_execution_role(self.state, implementation_mode="delegated")
            self.assertIn("--disallowedTools", runtime.probe(self.state)["missing_flags"])
        with patch.object(runtime, "_probe_output", side_effect=[
            "2.1.303 (Claude Code)",
            " ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS) + " --disallowedTools",
        ]):
            self.assertNotIn("--disallowedTools", runtime.probe(self.state)["missing_flags"])


if __name__ == "__main__":
    unittest.main()
