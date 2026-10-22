"""Native executive auto-compaction setup without a model or login."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin import executive_runtime as runtime


class ExecutiveContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.state = root / "state"
        self.profile = root / "login"
        self.manifest = runtime.prepare(
            self.state, config_dir=self.profile,
            project="01K00000000000000000000001",
            claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass

    def test_staged_setting_applies_on_next_launch_and_preserves_session_and_hooks(self):
        runtime.enable_development_loop(self.state)
        with runtime._owned_runtime(self.state):
            pass
        before = runtime.status(self.state)["configuration"]
        base = self.state / "executive-pilot"
        hook = (base / f"settings-development-loop-{before['native_session_id']}.json").read_bytes()
        result = runtime.configure_context(self.state, auto_compact_window_tokens=200000)
        self.assertTrue(result["pending_activation"])
        self.assertEqual(result["native_session_id"], before["native_session_id"])
        status = runtime.status(self.state)
        self.assertIsNone(status["configured_auto_compact_window_tokens"])
        self.assertEqual(status["pending_auto_compact_window_tokens"], 200000)
        spec = runtime.launch_spec(self.state, resume=True)
        self.assertEqual(spec["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "200000")
        self.assertEqual(spec["argv"][spec["argv"].index("--resume") + 1], before["native_session_id"])
        self.assertIn("--dangerously-load-development-channels", spec["argv"])
        with runtime._owned_runtime(self.state):
            pass
        after = runtime.status(self.state)["configuration"]
        self.assertEqual(after["auto_compact_window_tokens"], 200000)
        self.assertEqual(after["native_session_id"], before["native_session_id"])
        self.assertEqual(after["config_dir"], before["config_dir"])
        self.assertEqual((base / f"settings-development-loop-{before['native_session_id']}.json").read_bytes(), hook)

    def test_one_launch_override_does_not_rewrite_manifest(self):
        runtime.configure_context(self.state, auto_compact_window_tokens=200000)
        base = self.state / "executive-pilot"
        before = (base / "manifest.json").read_bytes()
        spec = runtime.launch_spec(self.state, resume=True, auto_compact_window_tokens=300000)
        self.assertEqual(spec["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "300000")
        self.assertEqual((base / "manifest.json").read_bytes(), before)
        self.assertEqual(runtime.status(self.state)["pending_auto_compact_window_tokens"], 200000)

    def test_invalid_window_rejected_and_existing_legacy_behavior_retained(self):
        for value in (True, "200000", 99999, 1000001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                runtime.configure_context(self.state, auto_compact_window_tokens=value)
        self.assertIsNone(runtime.status(self.state)["configured_auto_compact_window_tokens"])
        with patch.dict("os.environ", {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "180000"}):
            # Without an explicit option the v3 profile still inherits the
            # operator environment, as it did before this feature.
            self.assertEqual(runtime.launch_spec(self.state)["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "180000")

    def test_start_override_is_recorded_without_changing_configured_window(self):
        class Terminal:
            def isatty(self):
                return True

        captured = []

        def foreground(spec, _locks):
            captured.append(spec)
            return 0

        with (patch.object(runtime.sys, "stdin", Terminal()),
              patch.object(runtime.sys, "stdout", Terminal()),
              patch.object(runtime, "probe", return_value={"missing_flags": []}),
              patch.object(runtime, "_foreground", side_effect=foreground)):
            self.assertEqual(runtime.start(self.state, auto_compact_window_tokens=300000), 0)
        self.assertEqual(captured[0]["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "300000")
        status = runtime.status(self.state)
        self.assertEqual(status["last_launch"]["auto_compact_window_tokens"], 300000)
        self.assertIsNone(status["configured_auto_compact_window_tokens"])


if __name__ == "__main__":
    unittest.main()
