"""Staged executive model change; no native process or model call."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin import executive_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


class ExecutiveModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.state = root / "state"
        runtime.prepare(self.state, config_dir=root / "login",
                        project="01K00000000000000000000001",
                        claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass

    def argv(self):
        return runtime.launch_spec(self.state, resume=True)["argv"]

    def test_model_is_staged_then_applied_on_resume_with_same_session(self):
        before = runtime.status(self.state)
        self.assertEqual(before["configured_model"], runtime.DEFAULT_MODEL)
        staged = runtime.configure_model(self.state, model="claude-opus-5-5")
        self.assertTrue(staged["pending_activation"])
        self.assertEqual(staged["configured_model"], runtime.DEFAULT_MODEL)
        current = runtime.status(self.state)
        self.assertEqual(current["configured_model"], runtime.DEFAULT_MODEL)
        self.assertEqual(current["pending_model"], "claude-opus-5-5")
        argv = self.argv()
        self.assertEqual(argv[argv.index("--model") + 1], "claude-opus-5-5")
        session = before["configuration"]["native_session_id"]
        self.assertEqual(argv[argv.index("--resume") + 1], session)
        with runtime._owned_runtime(self.state):
            pass
        after = runtime.status(self.state)
        self.assertEqual(after["configured_model"], "claude-opus-5-5")
        self.assertIsNone(after["pending_model"])
        self.assertEqual(after["configuration"]["native_session_id"], session)

    def test_staging_the_current_model_cancels_and_merges_with_other_staging(self):
        runtime.configure_model(self.state, model="claude-opus-5-5")
        cancelled = runtime.configure_model(self.state, model=runtime.DEFAULT_MODEL)
        self.assertFalse(cancelled["pending_activation"])
        self.assertIsNone(runtime.status(self.state)["pending_model"])
        runtime.configure_execution_role(self.state, implementation_mode="delegated")
        runtime.configure_model(self.state, model="claude-opus-5-5")
        current = runtime.status(self.state)
        self.assertEqual(current["pending_model"], "claude-opus-5-5")
        self.assertEqual(current["pending_implementation_mode"], "delegated")

    def test_invalid_model_and_older_profile_are_refused(self):
        for model in ("gpt-6", "claude-", "Claude-opus", "claude-opus 5", "", None):
            with self.subTest(model=model), self.assertRaises(ValueError):
                runtime.configure_model(self.state, model=model)
        self.assertIsNone(runtime.status(self.state)["pending_model"])
        older = Path(tempfile.mkdtemp(dir=self.state.parent)) / "state"
        runtime.prepare(older, config_dir=self.state.parent / "login-older",
                        project="01K00000000000000000000002",
                        claude_binary=sys.executable, python_executable=sys.executable)
        with self.assertRaises(PermissionError):
            runtime.configure_model(older, model="claude-opus-5-5")

    def test_cli_stages_the_model(self):
        completed = subprocess.run(
            [sys.executable, "-m", "odin", "--state", str(self.state),
             "executive-configure-model", "--model", "claude-opus-5-5"],
            cwd=ROOT, env={"PYTHONPATH": str(ROOT / "python")},
            capture_output=True, text=True, check=False, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"requested_model":"claude-opus-5-5"', completed.stdout)
        missing = subprocess.run(
            [sys.executable, "-m", "odin", "--state", str(self.state),
             "executive-configure-model"],
            cwd=ROOT, env={"PYTHONPATH": str(ROOT / "python")},
            capture_output=True, text=True, check=False, timeout=60)
        self.assertEqual(missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
