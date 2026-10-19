"""Fixture-only durable coordination checks; no backend or model call."""

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from odin.contracts import identifier
from odin.coordination import Actor, Coordination
from odin.service import fixture_record
from odin.store import Conflict, Store, now


def later(hours=1):
    return (
        (datetime.now(timezone.utc) + timedelta(hours=hours))
        .isoformat()
        .replace("+00:00", "Z")
    )


class CoordinationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.co = Coordination(self.store)
        self.operator = Actor("operator", "operator-1")
        self.fable = Actor("coordinator", "Fable")
        self.project = fixture_record("Project", interface_decision_owner=None)
        self.session = fixture_record(
            "PlanningSession", project=self.project["id"], state="active"
        )
        self.project["interface_decision_owner"] = self.session["id"]
        self.commitment = fixture_record(
            "Commitment", project=self.project["id"], owner=self.session["id"]
        )
        self.assignment = fixture_record(
            "Assignment", commitment=self.commitment["id"], owner=self.session["id"]
        )
        for record in (self.project, self.session, self.commitment, self.assignment):
            self.store.create(record)
        self.astra = Actor(
            "planner", "Astra", self.session["id"], self.session["incarnation"]
        )
        self.grant = {
            "schema_version": 1,
            "id": identifier(),
            "issuer": self.operator.subject,
            "subject_role": "coordinator",
            "subject": "Fable",
            "project": self.project["id"],
            "actions": ["handoff", "portfolio"],
            "resources": [self.project["id"]],
            "issued_at": now(),
            "expires_at": later(),
            "authority_ref": "operator-command:synthetic",
        }
        self.co.grant(self.grant, actor=self.operator)
        self.packet = {
            "schema_version": 1,
            "operation_id": identifier(),
            "project": self.project["id"],
            "project_rev": self.project["rev"],
            "commitment": self.commitment["id"],
            "commitment_rev": self.commitment["rev"],
            "assignment": self.assignment["id"],
            "assignment_rev": self.assignment["rev"],
            "ownership_generation": self.commitment["ownership_generation"],
            "from_subject": "Fable",
            "to_subject": "Astra",
            "to_session": self.session["id"],
            "to_incarnation": self.session["incarnation"],
            "requirements": {
                "objective": self.commitment["objective"],
                "criteria": [
                    {"id": c["id"], "text": c["text"]}
                    for c in self.commitment["criteria"]
                ],
            },
            "evidence_refs": [],
            "artifact_refs": [],
            "repository_revision": "repo:abc123",
            "grant_id": self.grant["id"],
            "budget_ref": "shared-budget:fixture",
            "deadline": later(),
            "model_config_rev": "models:1",
            "issued_at": now(),
        }
        self.result = {
            "schema_version": 1,
            "report_id": identifier(),
            "operation_id": self.packet["operation_id"],
            "project": self.project["id"],
            "commitment": self.commitment["id"],
            "assignment": self.assignment["id"],
            "session": self.session["id"],
            "incarnation": self.session["incarnation"],
            "status": "complete",
            "evidence": [
                {
                    "criterion": "synthetic",
                    "refs": [{"ref": "artifact:proof", "digest": "0" * 64}],
                }
            ],
            "artifact_refs": [],
            "repository_revision": "repo:def456",
            "reported_at": now(),
        }

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def dispatch(self):
        self.assertTrue(self.co.handoff(self.packet, actor=self.fable))
        self.assertTrue(
            self.co.accept_handoff(self.packet["operation_id"], actor=self.astra)
        )

    def test_restart_replay_and_portfolio(self):
        self.dispatch()
        self.store.close()
        self.store = Store(Path(self.temp.name))
        self.co = Coordination(self.store)
        self.assertFalse(self.co.handoff(self.packet, actor=self.fable))
        self.assertFalse(
            self.co.accept_handoff(self.packet["operation_id"], actor=self.astra)
        )
        self.assertTrue(self.co.report(self.result, actor=self.astra))
        self.assertFalse(self.co.report(self.result, actor=self.astra))
        self.assertEqual(self.store.get(self.assignment["id"])["state"], "drafted")
        p = self.co.portfolio(
            [self.project["id"]],
            actor=self.fable,
            grant_ids={self.project["id"]: self.grant["id"]},
        )[0]
        self.assertEqual(p["planning_owner"], self.session["id"])
        self.assertEqual(p["handoffs"], [self.packet["operation_id"]])

    def test_partial_and_conflicting_replay(self):
        self.dispatch()
        partial = self.result | {"status": "partial", "evidence": []}
        self.assertFalse(self.co.report(partial, actor=self.astra))
        with self.assertRaises(Conflict):
            self.co.report(self.result, actor=self.astra)
        self.assertTrue(
            self.co.report(self.result | {"report_id": identifier()}, actor=self.astra)
        )
        changed = self.packet | {"budget_ref": "other"}
        with self.assertRaises(Conflict):
            self.co.handoff(changed, actor=self.fable)

    def test_stale_revision_and_ownership(self):
        self.store.update(
            self.commitment["id"], {"state": "blocked"}, self.commitment["rev"]
        )
        with self.assertRaises(Conflict):
            self.co.handoff(self.packet, actor=self.fable)
        current = self.store.get(self.commitment["id"])
        self.packet["commitment_rev"] = current["rev"]
        self.co.handoff(self.packet, actor=self.fable)
        self.co.accept_handoff(self.packet["operation_id"], actor=self.astra)
        other = fixture_record(
            "PlanningSession", project=self.project["id"], state="active"
        )
        self.store.create(other)
        self.store.transfer(self.commitment["id"], other["id"], current["rev"])
        self.assertFalse(self.co.report(self.result, actor=self.astra))

    def test_grant_scope_expiry_revocation_and_actor(self):
        with self.assertRaises(PermissionError):
            self.co.grant(self.grant | {"id": identifier()}, actor=self.fable)
        with self.assertRaises(PermissionError):
            self.co.handoff(self.packet, actor=Actor("coordinator", "wrong"))
        with self.assertRaises(PermissionError):
            self.co.authorize_action(
                self.grant["id"], "incident", self.project["id"], actor=self.fable
            )
        self.co.revoke(self.grant["id"], actor=self.operator)
        with self.assertRaises(PermissionError):
            self.co.handoff(self.packet, actor=self.fable)

    def test_incident_grant_is_resource_scoped(self):
        incident = self.grant | {
            "id": identifier(),
            "actions": ["incident"],
            "resources": ["incident:synthetic"],
        }
        self.co.grant(incident, actor=self.operator)
        self.assertTrue(
            self.co.authorize_action(
                incident["id"], "incident", "incident:synthetic", actor=self.fable
            )
        )
        with self.assertRaises(PermissionError):
            self.co.authorize_action(
                incident["id"], "incident", "incident:other", actor=self.fable
            )
        self.co.revoke(incident["id"], actor=self.operator)
        with self.assertRaises(PermissionError):
            self.co.authorize_action(
                incident["id"], "incident", "incident:synthetic", actor=self.fable
            )
        expired = copy.deepcopy(self.grant)
        expired["id"] = identifier()
        expired["issued_at"] = later(-2)
        expired["expires_at"] = later(-1)
        self.co.grant(expired, actor=self.operator)
        self.packet["grant_id"] = expired["id"]
        with self.assertRaises(PermissionError):
            self.co.handoff(self.packet, actor=self.fable)

    def test_future_grant_and_late_report_are_ineligible(self):
        future = self.grant | {
            "id": identifier(),
            "issued_at": later(1),
            "expires_at": later(2),
        }
        self.co.grant(future, actor=self.operator)
        with self.assertRaises(PermissionError):
            self.co.authorize_action(
                future["id"], "handoff", self.project["id"], actor=self.fable
            )
        self.dispatch()
        with patch("odin.coordination.now", return_value=later(2)):
            self.assertFalse(self.co.report(self.result, actor=self.astra))

    def test_stop_and_revocation_retain_ineligible_returns(self):
        self.dispatch()
        self.co.revoke(self.grant["id"], actor=self.operator)
        self.assertFalse(self.co.report(self.result, actor=self.astra))
        self.assertEqual(
            len(list(self.store.db.execute("SELECT id FROM coordination_reports"))), 1
        )
        self.store.stop("fixture stop")
        self.assertFalse(
            self.co.report(self.result | {"report_id": identifier()}, actor=self.astra)
        )
        self.assertEqual(
            len(list(self.store.db.execute("SELECT id FROM coordination_reports"))), 2
        )

    def test_exact_criterion_evidence_and_terminal_assignment(self):
        self.dispatch()
        duplicate = self.result | {"evidence": self.result["evidence"] * 2}
        self.assertFalse(self.co.report(duplicate, actor=self.astra))
        unknown = self.result | {
            "report_id": identifier(),
            "evidence": self.result["evidence"]
            + [
                {
                    "criterion": "unknown",
                    "refs": [{"ref": "artifact:extra", "digest": "1" * 64}],
                }
            ],
        }
        self.assertFalse(self.co.report(unknown, actor=self.astra))
        self.store.update(
            self.assignment["id"], {"state": "cancelled"}, self.assignment["rev"]
        )
        self.assertFalse(
            self.co.report(self.result | {"report_id": identifier()}, actor=self.astra)
        )

    def test_session_binding_stop_and_isolation(self):
        self.dispatch()
        with self.assertRaises(PermissionError):
            self.co.report(
                self.result, actor=Actor("planner", "Astra", self.session["id"], 2)
            )
        other = fixture_record("Project")
        self.store.create(other)
        with self.assertRaises(PermissionError):
            self.co.portfolio(
                [other["id"]],
                actor=self.fable,
                grant_ids={other["id"]: self.grant["id"]},
            )
        self.store.stop("fixture stop")
        with self.assertRaises(Conflict):
            self.co.authorize_action(
                self.grant["id"], "handoff", self.project["id"], actor=self.fable
            )


if __name__ == "__main__":
    unittest.main()
