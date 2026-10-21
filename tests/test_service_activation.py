"""Service-only activation with a fake unit controller: no real systemctl."""

import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin import executive_runtime as runtime
from odin import service_activation as activation


def git(repository, *argv):
    return subprocess.run(["git", "-C", str(repository), *argv], check=True,
                          capture_output=True, text=True).stdout.strip()


class FakeUnit:
    unit = activation.UNIT

    def __init__(self, state, repository, *, pid=4100, report=True, revision=None,
                 fail=False):
        self.state, self.repository, self.pid = state, repository, pid
        self.report, self.revision, self.fail = report, revision, fail
        self.restarts = 0

    def main_pid(self):
        return self.pid

    def restart(self):
        self.restarts += 1
        if self.fail:
            raise subprocess.CalledProcessError(1, ["systemctl"])
        self.pid += 1
        if self.report:
            # Stands in for `serve` reporting its own revision once bound.
            activation.record_service_revision(self.state, repository=self.repository,
                                               pid=self.pid)
            if self.revision:
                path = Path(self.state) / activation.REVISION_FILE
                value = json.loads(path.read_text())
                value["revision"] = self.revision
                path.unlink()
                runtime._write(path, "service-revision", value)


class ServiceActivationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.state = root / "state"
        self.state.mkdir(mode=0o700)
        self.repository = root / "canonical"
        self.repository.mkdir()
        git(self.repository, "init", "-q", "-b", "integration")
        git(self.repository, "config", "user.email", "test@example.invalid")
        git(self.repository, "config", "user.name", "Test")
        (self.repository / "file.txt").write_text("one\n")
        git(self.repository, "add", "file.txt")
        git(self.repository, "commit", "-q", "-m", "one")
        self.previous = git(self.repository, "rev-parse", "HEAD")
        (self.repository / "file.txt").write_text("two\n")
        git(self.repository, "commit", "-q", "-am", "two")
        self.head = git(self.repository, "rev-parse", "HEAD")
        self.db = sqlite3.connect(self.state / "odin_history.sqlite3")
        self.addCleanup(self.db.close)
        self.db.executescript("""
            CREATE TABLE delegation_turns (id TEXT PRIMARY KEY, session TEXT NOT NULL,
              assignment TEXT NOT NULL, project TEXT NOT NULL, seq INTEGER NOT NULL,
              state TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE executive_interventions (id TEXT PRIMARY KEY, project TEXT NOT NULL,
              session TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE development_loop_stages (id TEXT PRIMARY KEY, loop_id TEXT NOT NULL,
              body TEXT NOT NULL);
        """)
        self.db.commit()

    def unit(self, **changes):
        unit = FakeUnit(self.state, self.repository, **changes)
        value = {"version": 1, "pid": unit.pid, "revision": self.previous,
                 "clean": True, "started_at": "2026-10-21T00:00:00Z"}
        runtime._write(self.state / activation.REVISION_FILE, "service-revision", value)
        return unit

    def activate(self, unit, **changes):
        arguments = {"repository": self.repository, "branch": "integration",
                     "head": self.head, "controller": unit,
                     "reachable": lambda state: True}
        arguments.update(changes)
        return activation.activate(self.state, **arguments)

    def assertRefused(self, record, unit, reason):
        self.assertEqual((record["outcome"], record["reason"]), ("refused", reason))
        self.assertEqual(unit.restarts, 0)
        self.assertEqual(activation.last_activation(self.state), record)

    def test_quiescent_reviewed_head_restarts_only_the_unit_and_confirms_revision(self):
        unit = self.unit()
        record = self.activate(unit)
        self.assertEqual((record["outcome"], record["reason"]), ("activated", None))
        self.assertEqual(unit.restarts, 1)
        self.assertEqual(record["previous_revision"], self.previous)
        self.assertEqual(record["running_revision"], self.head)
        self.assertEqual((record["previous_pid"], record["running_pid"]), (4100, 4101))
        self.assertTrue(record["quiescence"]["quiescent"])
        self.assertIsNotNone(record["finished_at"])
        path = self.state / "executive-pilot" / activation.ACTIVATIONS / f"{record['id']}.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(activation.last_activation(self.state), record)

    def test_active_work_refuses_without_acting(self):
        future = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        cases = [
            ("INSERT INTO delegation_turns VALUES ('T1','S1','A1','P',1,'running','{}')",
             "not_quiescent_delegated_turns"),
            ("INSERT INTO delegation_turns VALUES ('T2','S1','A1','P',2,'queued','{}')",
             "not_quiescent_delegated_turns"),
            (("INSERT INTO executive_interventions VALUES ('I1','P','S',"
              f"'{json.dumps({'id': 'I1', 'state': 'active', 'expires_at': future, 'permits': []})}')"),
             "not_quiescent_live_interventions"),
            (("INSERT INTO development_loop_stages VALUES ('G1','L1',"
              f"'{json.dumps({'id': 'G1', 'state': 'claimed'})}')"),
             "not_quiescent_claimed_loop_stages"),
        ]
        for statement, reason in cases:
            with self.subTest(reason=reason):
                self.db.execute("DELETE FROM delegation_turns")
                self.db.execute("DELETE FROM executive_interventions")
                self.db.execute("DELETE FROM development_loop_stages")
                self.db.execute(statement)
                self.db.commit()
                unit = self.unit()
                record = self.activate(unit)
                self.assertRefused(record, unit, reason)
                self.assertFalse(record["quiescence"]["quiescent"])

    def test_finished_work_is_quiescent(self):
        past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        self.db.execute("INSERT INTO delegation_turns VALUES ('T1','S1','A1','P',1,'succeeded','{}')")
        self.db.execute("INSERT INTO executive_interventions VALUES ('I1','P','S',?)",
                        (json.dumps({"id": "I1", "state": "active", "expires_at": past,
                                     "permits": [{"state": "consumed"}]}),))
        self.db.execute("INSERT INTO development_loop_stages VALUES ('G1','L1',?)",
                        (json.dumps({"id": "G1", "state": "completed"}),))
        self.db.commit()
        self.assertEqual(activation.quiescence(self.state)["quiescent"], True)

    def test_checkout_preconditions_refuse_without_acting(self):
        unit = self.unit()
        self.assertRefused(self.activate(unit, head=self.previous), unit, "checkout_wrong_head")
        self.assertRefused(self.activate(unit, branch="main"), unit, "checkout_wrong_branch")
        (self.repository / "file.txt").write_text("dirty\n")
        self.assertRefused(self.activate(unit), unit, "checkout_not_clean")
        git(self.repository, "checkout", "-q", "file.txt")
        git(self.repository, "checkout", "-q", "--detach")
        self.assertRefused(self.activate(unit), unit, "checkout_detached_or_unreadable")

    def test_stopped_unit_is_refused(self):
        unit = self.unit()
        unit.pid = 0
        self.assertRefused(self.activate(unit), unit, "unit_not_running")

    def test_concurrent_activation_is_refused(self):
        unit = self.unit()
        directory = activation._directory(self.state)
        with runtime._lease(directory / "activation.lock"):
            self.assertRefused(self.activate(unit), unit, "activation_in_progress")

    def test_restart_failure_and_wrong_revision_are_recorded_failures(self):
        record = self.activate(self.unit(fail=True))
        self.assertEqual((record["outcome"], record["reason"]), ("failed", "restart_failed"))
        record = self.activate(self.unit(revision=self.previous))
        self.assertEqual((record["outcome"], record["reason"]), ("failed", "revision_mismatch"))
        self.assertEqual(record["running_revision"], self.previous)

    def test_unreported_or_unreachable_service_times_out(self):
        ticks = iter(range(0, 1000, 5))
        for unit, reachable in ((self.unit(report=False), lambda state: True),
                                (self.unit(), lambda state: False)):
            with self.subTest(report=unit.report):
                record = self.activate(unit, reachable=reachable, timeout=20,
                                       clock=lambda: next(ticks), sleep=lambda seconds: None)
                self.assertEqual((record["outcome"], record["reason"]),
                                 ("failed", "service_unreachable_or_unreported"))
                self.assertEqual(unit.restarts, 1)

    def test_systemd_controller_only_addresses_the_service_user_unit(self):
        calls = []

        def run(argv, **options):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="4242\n")

        unit = activation.SystemdUserUnit(run=run)
        self.assertEqual(unit.main_pid(), 4242)
        unit.restart()
        self.assertEqual(calls, [
            ["systemctl", "--user", "show", "--property=MainPID", "--value",
             "odin-executive-pilot-service"],
            ["systemctl", "--user", "restart", "odin-executive-pilot-service"],
        ])

    def test_service_reports_its_checkout_revision(self):
        value = activation.record_service_revision(self.state, repository=self.repository)
        self.assertEqual((value["pid"], value["revision"], value["clean"]),
                         (os.getpid(), self.head, True))
        self.assertEqual(activation.service_revision(self.state), value)
        mode = (self.state / activation.REVISION_FILE).stat().st_mode
        self.assertEqual(stat.S_IMODE(mode), 0o600)

    def test_executive_status_exposes_last_activation_and_running_revision(self):
        runtime.prepare(self.state, config_dir=self.state.parent / "credentials",
                        project="01K00000000000000000000001",
                        claude_binary=sys.executable, python_executable=sys.executable)
        unit = self.unit()
        observed = runtime.status(self.state)
        self.assertEqual(observed["last_service_activation"], None)
        self.assertEqual(observed["service_revision"]["revision"], self.previous)
        record = self.activate(unit, head=self.previous)
        observed = runtime.status(self.state)
        self.assertEqual(observed["last_service_activation"], record)


if __name__ == "__main__":
    unittest.main()
