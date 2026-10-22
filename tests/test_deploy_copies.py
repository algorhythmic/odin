"""Pinned deploy copies and the `current` switch (ODIN-ADR-039, item 7)."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError
from odin import deploy_copies as copies
from odin import executive_runtime as runtime
from odin.contracts import DEPLOYMENT_FILE, ROOT, Contracts, deployment, strict_loads
from odin.executive_service import prepare_project


def git(repository, *argv):
    return subprocess.run(["git", "-C", str(repository), *argv], capture_output=True, text=True,
                          check=True, env=os.environ | {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                                                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}).stdout.strip()


def synthetic_repository(path, commits=1, branch="integration"):
    """A small git repository; returns the commit ids in order."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", branch)
    revisions = []
    for index in range(commits):
        (path / "python").mkdir(exist_ok=True)
        (path / "python" / "marker.txt").write_text(f"synthetic {index}\n")
        (path / "run.sh").write_text("#!/bin/sh\n"); (path / "run.sh").chmod(0o755)
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", f"commit {index}")
        revisions.append(git(path, "rev-parse", "HEAD"))
    return revisions


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self._cleanup, temp)
        self.temp = Path(temp.name)
        self.repository = self.temp / "repo"
        self.revisions = synthetic_repository(self.repository, commits=4)
        self.root = self.temp / "deploy"

    @staticmethod
    def _cleanup(temp):
        # Copies are read-only; make them removable.
        for directory, _names, _files in os.walk(temp.name):
            os.chmod(directory, 0o700)
        temp.cleanup()


class CopyTests(Base):
    def test_export_is_read_only_marked_and_idempotent(self):
        revision = self.revisions[0]
        target = copies.export(self.root, self.repository, revision)
        self.assertEqual(target, self.root / revision)
        marker = deployment(target)
        Contracts().validate("odin-deployment", marker)
        self.assertEqual((marker["revision"], marker["repository"]), (revision, str(self.repository)))
        self.assertEqual((target / "python" / "marker.txt").read_text(), "synthetic 0\n")
        self.assertFalse(stat.S_IMODE((target / "python" / "marker.txt").stat().st_mode) & 0o222)
        self.assertTrue(os.access(target / "run.sh", os.X_OK))
        self.assertFalse(stat.S_IMODE(target.stat().st_mode) & 0o222)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(copies.export(self.root, self.repository, revision), target)
        self.assertEqual([p.name for p in self.root.iterdir()], [revision])

    def test_export_refusals_leave_nothing_behind(self):
        for revision, code in [("abc", "deploy_revision_invalid"),
                               ("f" * 40, "deploy_export_failed")]:
            with self.subTest(revision=revision), self.assertRaises(copies.DeployError) as caught:
                copies.export(self.root, self.repository, revision)
            self.assertEqual(str(caught.exception), code)
        self.assertEqual(list(self.root.iterdir()), [])
        copies.export(self.root, self.repository, self.revisions[0])
        with self.assertRaises(copies.DeployError) as caught:
            copies.export(self.root, self.temp / "elsewhere", self.revisions[0])
        self.assertEqual(str(caught.exception), "deploy_copy_mismatch")

    def test_committed_marker_name_is_refused(self):
        # A link out of the tree is refused by the archive filter; an in-tree
        # link or file of the marker's name is refused before the marker is written.
        for target, code in [("/tmp/elsewhere-marker", "deploy_export_unsafe"),
                             ("python/marker.txt", "deploy_marker_invalid")]:
            marker = self.repository / DEPLOYMENT_FILE
            marker.unlink(missing_ok=True)
            marker.symlink_to(target)
            git(self.repository, "add", "-A")
            git(self.repository, "commit", "-q", "-m", "plant")
            with self.subTest(target=target), self.assertRaises(copies.DeployError) as caught:
                copies.export(self.root, self.repository, git(self.repository, "rev-parse", "HEAD"))
            self.assertEqual(str(caught.exception), code)
        self.assertFalse(Path("/tmp/elsewhere-marker").exists())
        self.assertEqual((self.repository / "python" / "marker.txt").read_text(), "synthetic 3\n")
        self.assertEqual([p.name for p in self.root.iterdir()], [])

    def test_root_must_be_private(self):
        loose = self.temp / "loose"; loose.mkdir(mode=0o755); loose.chmod(0o755)
        with self.assertRaises(copies.DeployError):
            copies.export(loose, self.repository, self.revisions[0])
        os.symlink(self.root.parent, self.temp / "link")
        with self.assertRaises(copies.DeployError):
            copies.private_root(str(self.temp / "link" / "deploy"))

    def test_switch_is_atomic_and_reports_the_previous_revision(self):
        first, second = self.revisions[:2]
        for revision in (first, second):
            copies.export(self.root, self.repository, revision)
        self.assertIsNone(copies.current_revision(self.root))
        self.assertIsNone(copies.switch(self.root, first))
        self.assertEqual(copies.switch(self.root, second), first)
        self.assertEqual(os.readlink(self.root / "current"), second)
        self.assertEqual((self.root / "current" / "python" / "marker.txt").read_text(), "synthetic 1\n")
        self.assertEqual(copies.switch(self.root, first), second)  # rollback
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".")], [])
        with self.assertRaises(copies.DeployError):
            copies.switch(self.root, self.revisions[3])

    def test_prune_keeps_current_and_the_rollback_target(self):
        for revision in self.revisions:
            copies.export(self.root, self.repository, revision)
        copies.switch(self.root, self.revisions[0])
        removed = copies.prune(self.root, 1, protect=[self.revisions[1]])
        self.assertEqual(sorted(removed), sorted(self.revisions[2:3]))
        self.assertEqual(sorted(copies.copies(self.root)),
                         sorted([self.revisions[0], self.revisions[1], self.revisions[3]]))


class ConfigurationTests(Base):
    def setUp(self):
        super().setUp()
        self.state = self.temp / "state"
        self.project = prepare_project(self.state)
        runtime.prepare(self.state, config_dir=self.temp / "login", project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)

    def test_configure_and_prepare(self):
        value = copies.configure(self.state, repository=self.repository, branch="integration")
        Contracts().validate("executive-deploy-config", value)
        self.assertEqual(value["deploy_root"], str(self.temp / "deploy"))
        self.assertEqual(copies.read_config(self.state), value)
        result = copies.prepare(self.state, head=self.revisions[-1])
        self.assertEqual((result["current"], result["previous"], result["restarted"]),
                         (self.revisions[-1], None, False))
        self.assertEqual(copies.current_revision(self.temp / "deploy"), self.revisions[-1])
        # Only the clean integration head, as for a deploy.
        with self.assertRaises(copies.DeployError) as caught:
            copies.prepare(self.state, head=self.revisions[1])
        self.assertEqual(str(caught.exception), "deploy_head_not_integration_head")
        (self.repository / "python" / "marker.txt").write_text("dirty\n")
        with self.assertRaises(copies.DeployError) as caught:
            copies.prepare(self.state, head=self.revisions[-1])
        self.assertEqual(str(caught.exception), "deploy_tree_dirty")

    def test_configuration_refusals(self):
        for kwargs in [{"repository": self.temp / "missing"},
                       {"deploy_root": str(self.repository / "deploy")},
                       {"deploy_root": str(self.state / "deploy")}]:
            arguments = {"repository": self.repository, "branch": "integration"} | kwargs
            with self.subTest(kwargs=kwargs), self.assertRaises(copies.DeployError):
                copies.configure(self.state, **arguments)
        with self.assertRaises(ValidationError):
            copies.configure(self.state, repository=self.repository, branch="integration", keep=0)
        with self.assertRaises(copies.DeployError) as caught:
            copies.prepare(self.state, head=self.revisions[0])
        self.assertEqual(str(caught.exception), "deploy_not_configured")

    def test_operator_cli(self):
        def run(*argv):
            return subprocess.run([sys.executable, "-m", "odin", "--state", str(self.state), *argv],
                                  capture_output=True, text=True, timeout=60, check=False,
                                  env=os.environ | {"PYTHONPATH": str(ROOT / "python")})
        done = run("executive-configure-deploy", "--repository", str(self.repository),
                   "--branch", "integration", "--keep", "2")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(strict_loads(done.stdout)["keep"], 2)
        prepared = run("executive-deploy-prepare", "--head", self.revisions[-1])
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["current"], self.revisions[-1])
        self.assertTrue((self.temp / "deploy" / self.revisions[-1] / DEPLOYMENT_FILE).exists())
        refused = run("executive-deploy-prepare", "--head", "f" * 40)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("deploy_head_not_integration_head", refused.stderr)


if __name__ == "__main__":
    unittest.main()
