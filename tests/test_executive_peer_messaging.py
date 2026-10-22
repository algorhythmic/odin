"""Session-scoped native peer configuration, without native model calls."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin import executive_runtime as runtime
from odin.native_peer import peer_name


class ExecutivePeerMessagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.state, self.login = root / "state", root / "login"
        runtime.prepare(self.state, config_dir=self.login,
                        project="01K00000000000000000000001",
                        claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass

    def test_staging_preserves_identity_live_settings_and_pending_context(self):
        runtime.enable_development_loop(self.state)
        with runtime._owned_runtime(self.state):
            pass
        before = runtime.status(self.state)["configuration"]
        hook = self.state / "executive-pilot" / f"settings-development-loop-{before['native_session_id']}.json"
        original = hook.read_bytes()
        runtime.configure_context(self.state, auto_compact_window_tokens=200000)
        result = runtime.configure_peer_messaging(self.state, enabled=True)
        self.assertTrue(result["pending_activation"])
        self.assertFalse(runtime.status(self.state)["native_peer_messaging_configured"])
        self.assertEqual(hook.read_bytes(), original)
        spec = runtime.launch_spec(self.state, resume=True)
        argv = spec["argv"]
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertEqual(settings["crossSessionInbound"], "accept")
        self.assertEqual(settings["hooks"], json.loads(original)["hooks"])
        self.assertEqual(argv[argv.index("--name") + 1], peer_name(before["native_session_id"], "executive"))
        self.assertEqual(argv[argv.index("--resume") + 1], before["native_session_id"])
        self.assertEqual(spec["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "200000")
        self.assertFalse((self.login / "settings.json").exists())
        with runtime._owned_runtime(self.state):
            pass
        status = runtime.status(self.state)
        self.assertTrue(status["native_peer_messaging_configured"])
        self.assertFalse(status["pending_activation_requires_resume"])
        self.assertEqual(status["native_peer_delivery"], "unverified")
        self.assertEqual(status["configuration"]["native_session_id"], before["native_session_id"])
        self.assertEqual(hook.read_bytes(), original)

    def test_no_loop_needed_and_disabling_removes_override_without_refusing_peers(self):
        old = runtime.launch_spec(self.state)["argv"]
        self.assertNotIn("--settings", old)
        runtime.configure_peer_messaging(self.state, enabled=True)
        with runtime._owned_runtime(self.state):
            pass
        argv = runtime.launch_spec(self.state)["argv"]
        self.assertEqual(json.loads(argv[argv.index("--settings") + 1]), {"crossSessionInbound": "accept"})
        runtime.configure_peer_messaging(self.state, enabled=False)
        self.assertNotIn("--settings", runtime.launch_spec(self.state)["argv"])
        self.assertNotIn("--name", runtime.launch_spec(self.state)["argv"])
        with runtime._owned_runtime(self.state):
            pass
        self.assertFalse(runtime.status(self.state)["native_peer_messaging_configured"])

    def test_cancel_pending_opt_in_and_reject_non_boolean(self):
        runtime.configure_peer_messaging(self.state, enabled=True)
        result = runtime.configure_peer_messaging(self.state, enabled=False)
        self.assertFalse(result["pending_activation"])
        for value in ("accept", 1, None):
            with self.assertRaises(ValueError):
                runtime.configure_peer_messaging(self.state, enabled=value)

    def test_name_survives_resume_and_changes_with_native_identity(self):
        sid = runtime.status(self.state)["configuration"]["native_session_id"]
        self.assertEqual(peer_name(sid, "executive"), peer_name(sid, "executive"))
        self.assertNotEqual(peer_name(sid, "executive"), peer_name(sid, "worker"))
        self.assertNotEqual(peer_name(sid, "worker"), peer_name("11111111-1111-4111-8111-111111111111", "worker"))
        with self.assertRaises(ValueError):
            peer_name("ambiguous-display-name", "worker")

    def test_probe_capture_uses_regular_file_and_retains_flags_after_pipe_boundary(self):
        script = "import os,stat; assert stat.S_ISREG(os.fstat(1).st_mode); os.write(1, b'x'*22000+b' --name --remote-control')"
        text = runtime._probe_output([sys.executable, "-c", script], cwd=self.state, env=None)
        self.assertEqual(len(text), 22000 + len(" --name --remote-control"))
        self.assertTrue(text.endswith(" --name --remote-control"))
        with self.assertRaisesRegex(ValueError, "128 KiB"):
            runtime._probe_output([sys.executable, "-c", "import os; os.write(1,b'x'*131073)"], cwd=self.state, env=None)

    def test_disabling_loop_preserves_other_pending_options(self):
        runtime.enable_development_loop(self.state)
        with runtime._owned_runtime(self.state):
            pass
        runtime.configure_context(self.state, auto_compact_window_tokens=200000)
        runtime.configure_peer_messaging(self.state, enabled=True)
        runtime.enable_development_loop(self.state, enabled=False)
        spec = runtime.launch_spec(self.state)
        self.assertNotIn("--dangerously-load-development-channels", spec["argv"])
        self.assertEqual(spec["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "200000")
        self.assertEqual(json.loads(spec["argv"][spec["argv"].index("--settings") + 1]), {"crossSessionInbound": "accept"})
        with runtime._owned_runtime(self.state):
            pass
        self.assertFalse(runtime.status(self.state)["development_loop_enabled"])
        self.assertTrue(runtime.status(self.state)["native_peer_messaging_configured"])

    def test_probe_requires_native_messaging_version_not_only_old_flags(self):
        runtime.configure_peer_messaging(self.state, enabled=True)
        help_text = " ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS) + " --name --settings"
        for version, supported in [("2.1.223", False), ("unknown", False), ("2.1.224", True), ("2.1.303", True)]:
            with self.subTest(version=version), patch.object(runtime, "_probe_output", side_effect=[version, help_text]):
                self.assertEqual(not runtime.probe(self.state)["missing_flags"], supported)


if __name__ == "__main__":
    unittest.main()
