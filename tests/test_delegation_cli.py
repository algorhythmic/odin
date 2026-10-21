"""End-to-end tests for the delegation-configure CLI action."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.contracts import ROOT, strict_loads
from odin.delegation import load_config
from test_delegation import FAKE_CLAUDE, _script


class DelegationConfigureCliTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.state = self.root / "state"
        self.workspaces = self.root / "workspaces"
        self.workspaces.mkdir(mode=0o700)
        self.config_dir = self.root / "claude-login"
        self.config_dir.mkdir(mode=0o700)
        self.bin = self.root / "bin"
        self.bin.mkdir(mode=0o700)
        self.claude = _script(self.bin / "claude", FAKE_CLAUDE)

    def run_cli(self, *arguments, path=None):
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in ("PATH", "PYTHONPATH")
        }
        env["PATH"] = str(self.bin) if path is None else path
        env["PYTHONPATH"] = str(ROOT / "python")
        return subprocess.run(
            [sys.executable, "-m", "odin", "delegation-configure", *arguments],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )

    def base(self, *extra):
        return ["--state", str(self.state), *extra]

    def test_success_writes_private_loadable_config(self):
        result = self.run_cli(
            *self.base(
                "--claude-config",
                str(self.config_dir),
                "--workspace-root",
                str(self.workspaces),
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = strict_loads(result.stdout)
        path = self.state / "delegation.json"
        self.assertEqual(output["written"], str(path))
        self.assertEqual(output["harnesses"], ["claude-code"])
        self.assertEqual(output["workspace_roots"], [str(self.workspaces)])
        self.assertIn("restart serve", output["activation"])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        config = load_config(self.state)
        self.assertEqual(config["workspace_roots"], [str(self.workspaces)])
        harness = config["harnesses"]["claude-code"]
        self.assertEqual(harness["binary"], str(self.claude))
        self.assertEqual(harness["config_dir"], str(self.config_dir))

    def test_lineage_policy_flag_is_written_and_defaults_to_exclusive(self):
        arguments = [
            "--claude-config",
            str(self.config_dir),
            "--workspace-root",
            str(self.workspaces),
        ]
        path = self.state / "delegation.json"

        result = self.run_cli(*self.base(*arguments))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(strict_loads(path.read_text())["lineage_policy"], "exclusive")

        result = self.run_cli(
            *self.base(*arguments, "--lineage-policy", "shared_accepted")
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            strict_loads(path.read_text())["lineage_policy"], "shared_accepted"
        )

    def test_lineage_turn_limit_defaults_to_one_and_needs_accepted_sharing(self):
        arguments = ["--claude-config", str(self.config_dir),
                     "--workspace-root", str(self.workspaces)]
        path = self.state / "delegation.json"
        result = self.run_cli(*self.base(*arguments))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(strict_loads(path.read_text())["max_concurrent_turns_per_lineage"], 1)
        result = self.run_cli(*self.base(*arguments, "--max-concurrent-turns-per-lineage", "2"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires lineage_policy shared_accepted", result.stderr)
        self.assertEqual(strict_loads(path.read_text())["max_concurrent_turns_per_lineage"], 1)
        result = self.run_cli(*self.base(*arguments, "--max-concurrent-turns-per-lineage", "9"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("between 1 and 8", result.stderr)
        result = self.run_cli(*self.base(*arguments, "--lineage-policy", "shared_accepted",
                                         "--max-concurrent-turns-per-lineage", "2"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(strict_loads(path.read_text())["max_concurrent_turns_per_lineage"], 2)

    def test_missing_workspace_root_is_a_usage_error(self):
        result = self.run_cli(*self.base("--claude-config", str(self.config_dir)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires at least one --workspace-root", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.state / "delegation.json").exists())

    def test_workspace_root_equal_to_checkout_is_refused(self):
        result = self.run_cli(
            *self.base(
                "--claude-config",
                str(self.config_dir),
                "--workspace-root",
                str(ROOT),
            )
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "odin: workspace roots must not contain or be the checkout", result.stderr
        )
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.state / "delegation.json").exists())

    def test_workspace_root_containing_checkout_is_refused(self):
        result = self.run_cli(
            *self.base(
                "--claude-config",
                str(self.config_dir),
                "--workspace-root",
                str(ROOT.parent),
            )
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith("odin: "), result.stderr)
        self.assertIn("must not contain or be the checkout", result.stderr)
        self.assertFalse((self.state / "delegation.json").exists())

    def test_no_harness_available_is_refused(self):
        result = self.run_cli(
            *self.base("--workspace-root", str(self.workspaces)),
            path=str(self.root / "empty"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("odin: no delegation harness configured", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.state / "delegation.json").exists())


if __name__ == "__main__":
    unittest.main()
