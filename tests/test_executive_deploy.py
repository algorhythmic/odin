"""Runtime deploy requests, refusals and the drain (ODIN-ADR-039, items 5 and 6).

Synthetic evidence: an in-process service gateway and a synthetic git
repository standing in for the canonical checkout.
"""
import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import test_delegation
import test_development_evaluator
from odin import deploy_copies as copies
from odin import executive_supervision as supervision
from odin.contracts import Contracts, identifier, strict_loads
from odin.development_evaluator import configure
from odin.service_activation import record_service_revision
from test_deploy_copies import git, synthetic_repository
from test_development_evaluator import P
from test_executive_supervisor import Base


class DeployBase(Base):
    def setUp(self):
        super().setUp()
        self.repository = self.temp / "repo"
        self.revisions = synthetic_repository(self.repository, commits=3)
        self.head = self.revisions[-1]
        self.addCleanup(self._writable)

    def _writable(self):
        import os
        for directory, _names, _files in os.walk(self.temp):
            os.chmod(directory, 0o700)

    def configure(self, **options):
        return copies.configure(self.state, repository=self.repository, branch="integration", **options)

    def deploy(self, head=None, operation=None):
        return self.bridge.call("odin_runtime_deploy", {"head": head or self.head,
                                                        "operation_id": operation or identifier()})

    def refused(self, result, code):
        self.assertTrue(result["isError"], result)
        self.assertIn(code, result["content"][0]["text"])

    def deploys(self):
        return supervision.status(self.service.store, self.project)["deploys"]


class DeployRequestTests(DeployBase):
    def test_not_configured(self):
        self.refused(self.deploy(), "deploy_not_configured")

    def test_request_records_head_previous_and_deadline(self):
        self.configure(drain_timeout_seconds=600)
        record_service_revision(self.state)
        operation = identifier()
        request = self.ok(self.deploy(operation=operation))["request"]
        self.assertEqual((request["state"], request["requested_head"]), ("pending", self.head))
        self.assertIsNotNone(request["drain_deadline"])
        # The previous revision is current's target, else the service's own report.
        self.assertEqual(request["previous_revision"],
                         strict_loads((self.state / "service-revision.json").read_text())["revision"])
        Contracts().validate("executive-deploy", strict_loads(self.service.store.db.execute(
            "SELECT body FROM executive_deploys").fetchone()[0]))
        again = self.ok(self.deploy(operation=operation))["request"]
        self.assertEqual(again["id"], request["id"])
        self.refused(self.deploy(), "deploy_request_pending")
        self.assertIn("executive.deploy_requested", self.history("executive.deploy_"))

    def test_only_the_clean_integration_head(self):
        self.configure()
        self.refused(self.deploy(head=self.revisions[0]), "deploy_head_not_integration_head")
        (self.repository / "python" / "marker.txt").write_text("dirty\n")
        self.refused(self.deploy(), "deploy_tree_dirty")
        git(self.repository, "checkout", "-q", "--", ".")
        git(self.repository, "checkout", "-q", "-b", "elsewhere")
        self.refused(self.deploy(), "deploy_checkout_not_on_integration_branch")
        git(self.repository, "checkout", "-q", "integration")
        self.ok(self.deploy())

    def test_head_already_current(self):
        self.configure()
        copies.prepare(self.state, head=self.head)
        self.refused(self.deploy(), "deploy_head_already_current")

    def test_restart_and_deploy_exclude_each_other(self):
        self.configure()
        self.ok(self.request())
        self.refused(self.deploy(), "restart_request_pending")
        self.client.transition(self.requests()[0]["id"], "cancelled")
        self.ok(self.deploy())
        self.refused(self.request(), "deploy_request_pending")

    def test_unsafe_states_refuse(self):
        self.configure()
        with patch.object(supervision, "unsafe_reason", return_value="loop_stage_active"):
            self.refused(self.deploy(), "loop_stage_active")

    def test_transitions_are_operator_only_and_recheck_the_head(self):
        self.configure()
        request = self.ok(self.deploy())["request"]
        with self.assertRaises(OSError) as caught:
            self.client._command("runtime_deploy_transition", {"request_id": request["id"], "state": "deployed"})
        self.assertEqual(str(caught.exception), "deploy_transition_invalid")
        self.client._command("runtime_deploy_transition", {"request_id": request["id"], "state": "draining"})
        # A merge after the request: the deploying step refuses the old head.
        (self.repository / "python" / "marker.txt").write_text("next\n")
        git(self.repository, "commit", "-qam", "next")
        moved = self.client._command("runtime_deploy_transition",
                                     {"request_id": request["id"], "state": "deploying"})["request"]
        self.assertEqual((moved["state"], moved["code"]), ("failed", "deploy_head_not_integration_head"))
        notices = supervision.pending_notices(self.service.store, self.project)
        self.assertEqual([(n["kind"], n["outcome"]) for n in notices], [("runtime_deploy", "failed")])
        self.assertIn("deploy of", supervision.render_notice(self.service.store, notices[0]))


class DrainTests(DeployBase):
    def setUp(self):
        super().setUp()
        self.configure(drain_timeout_seconds=600)

    def test_drain_follows_the_request(self):
        store = self.service.store
        self.assertFalse(supervision.draining(store))
        request = self.ok(self.deploy())["request"]
        self.assertTrue(supervision.draining(store))
        view = self.client.status()["drain"]
        self.assertTrue(view["active"])
        self.assertTrue(view["drained"])
        self.client._command("runtime_deploy_transition", {"request_id": request["id"], "state": "cancelled"})
        self.assertFalse(supervision.draining(store))

    def test_drain_waits_for_running_work_not_queued_work(self):
        store = self.service.store
        self.assertTrue(self._has("delegation_turns"))
        columns = [row[1] for row in store.db.execute("PRAGMA table_info(delegation_turns)")]
        def turn(identity, state):
            values = {name: "x" for name in columns} | {"id": identity, "state": state}
            store.db.execute(f"INSERT INTO delegation_turns({','.join(columns)}) VALUES({','.join('?' * len(columns))})",
                             [values[name] for name in columns])
        turn("turn-running", "running")
        turn("turn-queued", "queued")
        self.ok(self.deploy())
        view = self.client.status()["drain"]
        self.assertEqual(view["waiting_for"]["delegated_turns"], ["turn-running"])
        self.assertEqual(view["queued_turns_held"], 1)
        self.assertFalse(view["drained"])
        store.db.execute("UPDATE delegation_turns SET state='returned' WHERE id='turn-running'")
        self.assertTrue(self.client.status()["drain"]["drained"])

    def _has(self, table):
        return self.service.store.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone() is not None

    def test_deadline_ends_the_drain_and_fails_the_request(self):
        store = self.service.store
        request = self.ok(self.deploy())["request"]
        body = strict_loads(store.db.execute("SELECT body FROM executive_deploys").fetchone()[0])
        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        store.db.execute("UPDATE executive_deploys SET body=?", (json.dumps(body | {"drain_deadline": past}),))
        # Even with no supervisor the service stops draining at the deadline.
        self.assertFalse(supervision.draining(store))
        # The next deploy action records the timeout, with a notice, and may proceed.
        self.ok(self.deploy())
        first = next(d for d in self.deploys() if d["id"] == request["id"])
        self.assertEqual((first["state"], first["code"]), ("failed", "drain_timeout"))
        self.assertIn("executive.deploy_failed", self.history("executive.deploy_"))


def drain_record(store, project, state="pending", seconds=600):
    """A deploy record written directly, as the service would hold it."""
    stamp = datetime.now(UTC)
    item = {"schema_version": 1, "id": identifier(), "kind": "deploy", "project": project,
            "session_id": "00000000-0000-4000-8000-000000000000", "requested_head": "a" * 40,
            "previous_revision": None,
            "requested_at": stamp.isoformat().replace("+00:00", "Z"),
            "updated_at": stamp.isoformat().replace("+00:00", "Z"),
            "drain_deadline": (stamp + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z"),
            "state": state, "code": None, "timings": {}, "activation_id": None,
            "rollback_activation_id": None, "pending_outcome": None,
            "clean_exit_observed": None, "exit_code": None}
    with store.transaction():
        supervision._save(store, item)
    return item


class DelegationDrainTests(unittest.TestCase):
    """Item 6: queued delegated turns stay queued; running turns are not touched."""

    setUp = test_delegation.DelegationCycleTests.setUp
    open_session = test_delegation.DelegationCycleTests.open_session
    assign = test_delegation.DelegationCycleTests.assign

    def test_queued_turn_waits_for_the_drain(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session)
        item = drain_record(h.service.store, h.project)
        self.assertEqual(h.gateway.delegation.launch_pending(), [])
        self.assertEqual(h.assignment_state(assigned["assignment"])["turns"][0]["state"], "queued")
        with h.service.store.transaction():
            supervision._save(h.service.store, item | {"state": "cancelled"})
        self.assertEqual(h.gateway.delegation.launch_pending(), [assigned["turn"]])

    def test_restarting_executive_no_longer_drains(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session)
        drain_record(h.service.store, h.project, state="restarting_executive")
        self.assertEqual(h.gateway.delegation.launch_pending(), [assigned["turn"]])

    def test_expired_drain_releases_queued_work(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session)
        drain_record(h.service.store, h.project, seconds=-1)
        self.assertEqual(h.gateway.delegation.launch_pending(), [assigned["turn"]])


class EvaluatorDrainTests(unittest.TestCase):
    """Item 6: a pending evaluator job is held, not started, during a drain."""

    setUp = test_development_evaluator.DevelopmentEvaluatorTests.setUp
    tearDown = test_development_evaluator.DevelopmentEvaluatorTests.tearDown
    runner = test_development_evaluator.DevelopmentEvaluatorTests.runner
    start = test_development_evaluator.DevelopmentEvaluatorTests.start
    wait = test_development_evaluator.DevelopmentEvaluatorTests.wait
    count = test_development_evaluator.DevelopmentEvaluatorTests.count

    def test_pending_job_is_held_then_started(self):
        configure(self.state, self.config)
        job, runner = self.start(), self.runner()
        item = drain_record(self.store, P)
        result = runner.tick()
        self.assertEqual((result["started"], result["held"]), ([], [job["id"]]))
        self.assertEqual(self.loop.job(job["id"])["state"], "pending")
        self.assertEqual(self.count(), 0)
        with self.store.transaction():
            supervision._save(self.store, item | {"state": "failed", "code": "drain_timeout"})
        self.assertEqual(runner.tick()["started"], [job["id"]])
        self.wait(runner, lambda: self.loop.job(job["id"])["state"] == "completed")

