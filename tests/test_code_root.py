"""Code root versus repository root (ODIN-ADR-039).

A deployed copy runs Odin's code from outside the executive's checkout. Its
marker names the repository; the manifest's repository_root stays the
canonical checkout. Without a marker both roots are the same, as before.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin import contracts
from odin import executive_runtime as runtime
from odin.contracts import (
    DEPLOYMENT_FILE,
    REPOSITORY_ROOT,
    ROOT,
    Contracts,
    deployment,
    strict_loads,
)
from odin.executive_service import prepare_project

REVISION = "0123456789abcdef0123456789abcdef01234567"


def copy_code(target, repository, revision=REVISION):
    """A synthetic deployed copy of this working tree with its marker."""
    target.mkdir(parents=True)
    for name in ("python", "schemas", "fixtures"):
        shutil.copytree(ROOT / name, target / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    marker = {"schema_version": 1, "revision": revision, "repository": str(repository),
              "exported_at": "2026-10-22T10:00:00Z"}
    (target / DEPLOYMENT_FILE).write_text(json.dumps(marker))
    return marker


class CodeRootTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.state = self.temp / "state"
        self.project = prepare_project(self.state)
        runtime.prepare(self.state, config_dir=self.temp / "login", project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)

    def run_from(self, code, *argv, script=None):
        environment = os.environ | {"PYTHONPATH": str(code / "python"), "PYTHONNOUSERSITE": "1"}
        command = [sys.executable, "-c", script] if script else [
            sys.executable, "-m", "odin", "--state", str(self.state), *argv]
        return subprocess.run(command, capture_output=True, text=True, timeout=60,
                              env=environment, cwd=self.temp, check=False)

    def test_without_a_marker_both_roots_are_the_checkout(self):
        self.assertIsNone(contracts.DEPLOYMENT)
        self.assertEqual(REPOSITORY_ROOT, ROOT)
        self.assertIsNone(deployment(ROOT))
        self.assertEqual(runtime._load(self.state)[0].get("repository_root", str(ROOT)), str(ROOT))

    def test_marker_matches_its_schema(self):
        marker = copy_code(self.temp / "copy", ROOT)
        Contracts().validate("odin-deployment", marker)
        self.assertEqual(deployment(self.temp / "copy"), marker)

    def test_deployed_copy_serves_the_canonical_repository(self):
        code = self.temp / "deploy" / REVISION
        copy_code(code, ROOT)
        # Staging from the copy records the checkout, never the copy, as the cwd.
        staged = self.run_from(code, "executive-enable-development")
        self.assertEqual(staged.returncode, 0, staged.stderr)
        self.assertEqual(strict_loads(staged.stdout)["repository_root"], str(ROOT))
        with runtime._owned_runtime(self.state):
            pass
        status = self.run_from(code, "executive-status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(strict_loads(status.stdout)["configuration"]["repository_root"], str(ROOT))
        probe = self.run_from(code, script=(
            "import json, sys\n"
            "from odin import executive_runtime as r\n"
            "from odin.service_activation import code_revision\n"
            f"spec = r.launch_spec({str(self.state)!r}, resume=True, supervised=True)\n"
            "a = spec['argv']; settings = json.loads(a[a.index('--settings') + 1])\n"
            "hook = settings['hooks']['Stop'][-1]['hooks'][0]['args'][0]\n"
            "print(json.dumps({'cwd': spec['cwd'], 'hook': hook, 'revision': code_revision()[0],\n"
            "                  'clean': code_revision()[1]}))\n"))
        self.assertEqual(probe.returncode, 0, probe.stderr)
        observed = json.loads(probe.stdout)
        # The session works in the checkout; its hooks import the copy that launched it.
        self.assertEqual(observed["cwd"], str(ROOT))
        self.assertEqual(observed["hook"], f"PYTHONPATH={code / 'python'}")
        self.assertEqual((observed["revision"], observed["clean"]), (REVISION, None))

    def test_launch_cwd_and_transcript_follow_the_repository_from_a_copy(self):
        # Telemetry derives the transcript directory from the launch cwd; from a
        # deployed copy both must still be the checkout named by the manifest.
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass
        code = self.temp / "deploy" / REVISION
        copy_code(code, ROOT)
        probe = self.run_from(code, script=(
            "import json\n"
            "from odin import executive_runtime as r\n"
            "from odin.usage_watch import claude_project_dir\n"
            f"m, base = r._load({str(self.state)!r})\n"
            f"session, transcript = r.current_transcript({str(self.state)!r})\n"
            "spec = r.launch_spec(" + repr(str(self.state)) + ", resume=True)\n"
            "print(json.dumps({'cwd': r._launch_cwd(m, base), 'spec_cwd': spec['cwd'],\n"
            "                  'transcript': str(transcript),\n"
            "                  'expected': str(claude_project_dir(m['config_dir'], m['repository_root']))}))\n"))
        self.assertEqual(probe.returncode, 0, probe.stderr)
        observed = json.loads(probe.stdout)
        self.assertEqual(observed["cwd"], str(ROOT))
        self.assertEqual(observed["spec_cwd"], str(ROOT))
        self.assertTrue(observed["transcript"].startswith(observed["expected"]))
        self.assertNotIn(str(code), observed["transcript"])

    def test_copy_of_another_repository_is_refused(self):
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass
        code = self.temp / "other"
        copy_code(code, self.temp / "elsewhere")
        refused = self.run_from(code, "executive-status")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("pilot repository scope differs", refused.stderr)

    def test_prepared_files_follow_the_launching_code(self):
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass
        runtime.enable_development_loop(self.state)
        with runtime._owned_runtime(self.state):
            pass
        manifest, base = runtime._load(self.state)
        mcp_path = runtime._mcp_path(manifest, base)
        loop_path = runtime._loop_settings_path(manifest, base)
        # A real deployed copy of this repository: the tolerated code location.
        copy_code(self.temp / "old" / REVISION, ROOT)
        old = str(self.temp / "old" / REVISION / "python")
        mcp = runtime._read(mcp_path, "executive-pilot-mcp")
        mcp["mcpServers"]["odin"]["env"]["PYTHONPATH"] = old
        runtime._write(mcp_path, "executive-pilot-mcp", mcp)
        hooks = runtime._read(loop_path, "executive-pilot-loop-settings")
        for groups in hooks["hooks"].values():
            groups[0]["hooks"][0]["args"][0] = "PYTHONPATH=" + old
        runtime._write(loop_path, "executive-pilot-loop-settings", hooks)
        # Only the code path differs: accepted, then rewritten at the next launch.
        runtime._load(self.state)
        with runtime._owned_runtime(self.state):
            pass
        self.assertEqual(runtime._read(mcp_path, "executive-pilot-mcp"), runtime._mcp(manifest))
        self.assertEqual(runtime._read(loop_path, "executive-pilot-loop-settings"),
                         runtime._loop_settings(manifest))
        # An arbitrary code location is not tolerated.
        mcp = runtime._read(mcp_path, "executive-pilot-mcp")
        mcp["mcpServers"]["odin"]["env"]["PYTHONPATH"] = "/somewhere/else/python"
        runtime._write(mcp_path, "executive-pilot-mcp", mcp)
        with self.assertRaises(PermissionError):
            runtime._load(self.state)
        runtime._write(mcp_path, "executive-pilot-mcp", runtime._mcp(manifest))
        # Any other difference is still refused.
        mcp = runtime._read(mcp_path, "executive-pilot-mcp")
        mcp["mcpServers"]["odin"]["args"][3] = "/tmp/another-state"
        runtime._write(mcp_path, "executive-pilot-mcp", mcp)
        with self.assertRaises(PermissionError):
            runtime._load(self.state)

    def test_current_symlink_pins_hooks_and_later_imports(self):
        deploy = self.temp / "deploy"
        first, second = "1" * 40, "2" * 40
        copy_code(deploy / first, ROOT, first)
        copy_code(deploy / second, ROOT, second)
        os.symlink(first, deploy / "current")
        staged = self.run_from(deploy / "current", "executive-enable-development")
        self.assertEqual(staged.returncode, 0, staged.stderr)
        with runtime._owned_runtime(self.state):
            pass
        probe = self.run_from(deploy / "current", script=(
            "import json, os\n"
            "import odin\n"
            "from odin import executive_runtime as r\n"
            f"spec = r.launch_spec({str(self.state)!r}, resume=True, supervised=True)\n"
            "a = spec['argv']; settings = json.loads(a[a.index('--settings') + 1])\n"
            "hook = settings['hooks']['Stop'][-1]['hooks'][0]['args'][0]\n"
            f"os.replace({str(deploy / 'next')!r}, {str(deploy / 'current')!r})\n"
            "import odin.deploy_copies as later\n"
            "print(json.dumps({'hook': hook, 'path': odin.__path__, 'later': later.__file__}))\n"))
        # Prepare the switch the script performs once it has imported Odin.
        self.assertEqual(probe.returncode, 1)  # deploy/next does not exist yet
        os.symlink(second, deploy / "next")
        probe = self.run_from(deploy / "current", script=probe.args[2])
        self.assertEqual(probe.returncode, 0, probe.stderr)
        observed = json.loads(probe.stdout)
        # Hooks name the revision directory, not current; a module imported
        # after current moved still comes from the launching revision.
        self.assertEqual(observed["hook"], f"PYTHONPATH={deploy / first / 'python'}")
        self.assertEqual(observed["path"], [str(deploy / first / "python" / "odin")])
        self.assertTrue(observed["later"].startswith(str(deploy / first)))
        self.assertEqual(os.readlink(deploy / "current"), second)

    def test_invalid_marker_fails_loudly(self):
        code = self.temp / "bad"
        copy_code(code, ROOT)
        (code / DEPLOYMENT_FILE).write_text(json.dumps({"schema_version": 1, "revision": "x",
                                                         "repository": "relative",
                                                         "exported_at": "now"}))
        failed = self.run_from(code, "executive-status")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("invalid deployment marker", failed.stderr)

    def test_state_inside_the_repository_is_refused_from_a_copy(self):
        code = self.temp / "copy"
        copy_code(code, ROOT)
        refused = subprocess.run(
            [sys.executable, "-m", "odin", "--state", str(ROOT / "tmp-state-never-created"), "executive-status"],
            capture_output=True, text=True, timeout=60, check=False,
            env=os.environ | {"PYTHONPATH": str(code / "python")})
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("outside the repository", refused.stderr)
        self.assertFalse((ROOT / "tmp-state-never-created").exists())


if __name__ == "__main__":
    unittest.main()
