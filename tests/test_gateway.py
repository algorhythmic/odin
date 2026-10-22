"""Recorded local command-path checks against the real service store and fake backend."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from odin.contracts import identifier
from odin.coordination import Actor
from odin.gateway import Gateway, GatewayContext
from odin.service import Service, fixture_record
from odin.store import Conflict, now


def later(hours=1):
    return (
        (datetime.now(timezone.utc) + timedelta(hours=hours))
        .isoformat()
        .replace("+00:00", "Z")
    )


class GatewayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Path(self.temp.name))
        self.gateway = Gateway(self.service)
        self.operator = GatewayContext("terminal", Actor("operator", "operator-1"))
        self.voice = GatewayContext("voice", self.operator.actor)
        self.fable = GatewayContext("harness", Actor("coordinator", "Fable"))
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
            self.service.store.create(record)
        self.astra = GatewayContext(
            "harness",
            Actor("planner", "Astra", self.session["id"], self.session["incarnation"]),
        )
        self.grant = {
            "schema_version": 1,
            "id": identifier(),
            "issuer": self.operator.actor.subject,
            "subject_role": "coordinator",
            "subject": "Fable",
            "project": self.project["id"],
            "actions": ["handoff", "portfolio"],
            "resources": [self.project["id"], "shared-budget:fixture"],
            "issued_at": now(),
            "expires_at": later(),
            "authority_ref": "operator-command:fixture",
        }
        self.gateway.budget.create("shared-budget:fixture", 120, 6, 0)
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
            "model_config_rev": self.gateway.config.config_rev,
            "issued_at": now(),
        }

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def command(self, action, payload, context=None, operation_id=None):
        command = {
            "schema_version": 1,
            "operation_id": operation_id or identifier(),
            "action": action,
            "payload": payload,
        }
        return self.gateway.submit(command, context=context or self.operator)

    def grant_and_handoff(self):
        self.command("grant", self.grant)
        self.command("handoff", self.packet, self.fable)
        self.command(
            "accept_handoff",
            {"handoff_operation": self.packet["operation_id"]},
            self.astra,
        )

    def test_status_poll_does_not_grow_history_and_stays_current(self):
        def counts():
            return tuple(self.service.store.db.execute(
                "SELECT (SELECT COUNT(*) FROM history), "
                "(SELECT COUNT(*) FROM gateway_commands)"
            ).fetchone())

        operation = identifier()
        before = counts()
        for context in (self.operator, self.voice):
            for _ in range(5):
                self.assertFalse(self.command("status", {}, context)["result"]["stopped"])
        self.assertFalse(self.command("status", {}, operation_id=operation)["result"]["stopped"])
        self.assertEqual(counts(), before)

        self.command("stop", {"reason": "synthetic poll check"})
        after_stop = counts()
        self.assertGreater(after_stop[0], before[0])
        self.assertEqual(after_stop[1], before[1] + 1)
        self.assertTrue(self.command("status", {}, operation_id=operation)["result"]["stopped"])
        self.assertEqual(counts(), after_stop)
        for context in (
            self.fable,
            GatewayContext("terminal", self.operator.actor, (self.project["id"],)),
        ):
            with self.subTest(context=context), self.assertRaises(PermissionError):
                self.command("status", {}, context)

    def test_nested_rollback_removes_command_receipt_record_and_history(self):
        store = self.service.store
        before = store.db.execute("SELECT count(*) FROM history").fetchone()[0]
        operation = identifier()
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with store.transaction():
                self.command("grant", self.grant, operation_id=operation)
                self.assertIsNotNone(
                    store.db.execute(
                        "SELECT 1 FROM coordination_grants WHERE id=?",
                        (self.grant["id"],),
                    ).fetchone()
                )
                raise RuntimeError("abort")
        self.assertIsNone(
            store.db.execute(
                "SELECT 1 FROM coordination_grants WHERE id=?", (self.grant["id"],)
            ).fetchone()
        )
        self.assertIsNone(
            store.db.execute(
                "SELECT 1 FROM gateway_commands WHERE id=?", (operation,)
            ).fetchone()
        )
        self.assertEqual(
            store.db.execute("SELECT count(*) FROM history").fetchone()[0], before
        )
        self.command("grant", self.grant, operation_id=operation)

    def test_idempotent_restart_replay_and_actor_context_conflict(self):
        operation = identifier()
        command = {
            "schema_version": 1,
            "operation_id": operation,
            "action": "grant",
            "payload": self.grant,
        }
        first = self.gateway.submit(command, context=self.operator)
        self.assertEqual(
            first, self.gateway.submit(copy.deepcopy(command), context=self.operator)
        )
        self.service.close()
        self.service = Service(Path(self.temp.name))
        self.gateway = Gateway(self.service)
        self.assertEqual(first, self.gateway.submit(command, context=self.operator))
        with self.assertRaises(Conflict):
            self.gateway.submit(command, context=self.voice)
        with self.assertRaises(Conflict):
            self.gateway.submit(
                command | {"payload": self.grant | {"expires_at": later(2)}},
                context=self.operator,
            )
        self.assertEqual(
            self.service.store.db.execute(
                "SELECT count(*) FROM coordination_grants"
            ).fetchone()[0],
            1,
        )

    def test_operator_grant_voice_refusal_messages_and_direct_stop(self):
        with self.assertRaises(PermissionError):
            self.command("grant", self.grant, self.fable)
        with self.assertRaises(PermissionError):
            self.command("grant", self.grant, self.voice)
        text = self.command(
            "message",
            {"project": self.project["id"], "text": "text input"},
            self.operator,
        )
        voice = self.command(
            "message",
            {"project": self.project["id"], "text": "voice input"},
            self.voice,
        )
        self.assertEqual(text["result"]["status"], voice["result"]["status"])
        with self.assertRaises(PermissionError):
            self.command("stop", {"reason": "model attempt"}, self.fable)
        result = self.command("stop", {"reason": "operator voice stop"}, self.voice)
        self.assertTrue(result["result"]["local_stopped"])
        self.assertTrue(self.service.store.stopped())
        self.assertEqual(
            self.command("status", {}, self.operator)["result"]["stopped"],
            self.command("status", {}, self.voice)["result"]["stopped"],
        )

    def test_handoff_requires_config_and_budget_and_grant_remains_current(self):
        self.command("grant", self.grant)
        with self.assertRaises(Conflict):
            self.command(
                "handoff", self.packet | {"model_config_rev": "stale"}, self.fable
            )
        with self.assertRaises(Conflict):
            self.command("handoff", self.packet | {"budget_ref": "missing"}, self.fable)
        self.gateway.budget.create("shared-budget:other", 120, 6, 0)
        with self.assertRaises(PermissionError):
            self.command(
                "handoff",
                self.packet | {"budget_ref": "shared-budget:other"},
                self.fable,
            )
        self.command("handoff", self.packet, self.fable)
        with self.assertRaises(Conflict):
            self.command(
                "session_intent",
                {"handoff_operation": self.packet["operation_id"], "role": "sol"},
                self.astra,
            )
        self.command(
            "accept_handoff",
            {"handoff_operation": self.packet["operation_id"]},
            self.astra,
        )
        with self.assertRaises(Conflict):
            self.command(
                "session_intent",
                {"handoff_operation": self.packet["operation_id"], "role": "fable"},
                self.astra,
            )
        intent = self.command(
            "session_intent",
            {"handoff_operation": self.packet["operation_id"], "role": "sol"},
            self.astra,
        )["result"]
        self.assertEqual(intent["execution_path"], "saga_api")
        self.assertFalse(intent["live_enabled"])
        opus = self.command(
            "session_intent",
            {"handoff_operation": self.packet["operation_id"], "role": "opus"},
            self.astra,
        )["result"]
        self.assertEqual(opus["execution_path"], "saga_api")
        self.command("revoke", {"grant_id": self.grant["id"]})
        with self.assertRaises(PermissionError):
            self.command(
                "session_intent",
                {"handoff_operation": self.packet["operation_id"], "role": "opus"},
                self.astra,
            )
        result = {
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
                    "criterion": c["id"],
                    "refs": [{"ref": "artifact:proof", "digest": "0" * 64}],
                }
                for c in self.commitment["criteria"]
            ],
            "artifact_refs": [],
            "repository_revision": "repo:proof",
            "reported_at": now(),
        }
        self.assertFalse(
            self.command("report", result, self.astra)["result"][
                "eligible_for_checking"
            ]
        )

    def test_expired_grant_blocks_new_intent_and_result_checking(self):
        self.grant_and_handoff()
        with patch("odin.coordination.now", return_value=later(2)):
            with self.assertRaises(PermissionError):
                self.command(
                    "session_intent",
                    {"handoff_operation": self.packet["operation_id"], "role": "sol"},
                    self.astra,
                )
            result = {
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
                        "criterion": c["id"],
                        "refs": [{"ref": "artifact:proof", "digest": "0" * 64}],
                    }
                    for c in self.commitment["criteria"]
                ],
                "artifact_refs": [],
                "repository_revision": "repo:proof",
                "reported_at": now(),
            }
            self.assertFalse(
                self.command("report", result, self.astra)["result"][
                    "eligible_for_checking"
                ]
            )

    def test_expired_handoff_blocks_intent_and_consultation_source(self):
        self.grant_and_handoff()
        with patch("odin.gateway.now", return_value=later(2)):
            with self.assertRaises(Conflict):
                self.command(
                    "session_intent",
                    {"handoff_operation": self.packet["operation_id"], "role": "opus"},
                    self.astra,
                )
            from odin.store import digest

            self.assertIsNone(
                self.gateway.current_source(
                    {
                        "handoff_operation": self.packet["operation_id"],
                        "handoff_digest": digest(self.packet),
                    }
                )
            )

    def test_consultation_deadline_cannot_outlive_handoff(self):
        self.grant_and_handoff()
        from odin.store import digest

        source = self.gateway.current_source(
            {
                "handoff_operation": self.packet["operation_id"],
                "handoff_digest": digest(self.packet),
            }
        )
        config = json.loads(
            (
                Path(__file__).resolve().parents[1] / "fixtures/chirality-config.json"
            ).read_text()
        )
        for branch in config["branches"]:
            role = self.gateway.config.data["roles"][branch["role"]]
            branch.update(
                provider=role["provider"],
                harness=role["harness"],
                harness_version=role["harness_version"],
                requested_model=role["model"],
                effort=role["effort"],
                config_revision=self.gateway.config.config_rev,
            )
        config["deadline_at"] = later(2)
        packet = {
            "schema_version": 1,
            "revision": 1,
            "question": "Fixture question",
            "evidence": ["fixture:handoff"],
            "target": None,
            "source": source,
        }
        with self.assertRaises(Conflict):
            self.command(
                "consult_start",
                {
                    "consultation_id": "deadline-fixture",
                    "config": config,
                    "packet": packet,
                    "budget_id": self.packet["budget_ref"],
                },
                self.astra,
            )

    def test_layout_done_is_visibility_only_and_stale_incarnation_refused(self):
        binding = {
            "schema_version": 1,
            "project": self.project["id"],
            "session": self.session["id"],
            "incarnation": self.session["incarnation"],
            "host": "host-fixture",
            "server_incarnation": "server-1",
            "workspace": "workspace",
            "tab": "tab",
            "pane": "pane",
            "evidence_mode": "fixture",
        }
        self.command("layout_bind", binding)
        observation = {
            "schema_version": 1,
            "session": self.session["id"],
            "incarnation": self.session["incarnation"],
            "host": "host-fixture",
            "server_incarnation": "server-1",
            "pane": "pane",
            "state": "done",
            "evidence_mode": "fixture",
        }
        self.assertEqual(
            self.command("layout_observe", observation)["result"]["authority"],
            "visibility_only",
        )
        self.assertEqual(
            self.service.store.get(self.assignment["id"])["state"],
            self.assignment["state"],
        )
        with self.assertRaises(Conflict):
            self.command(
                "layout_observe", observation | {"server_incarnation": "server-2"}
            )
        with self.assertRaises(Conflict):
            self.command(
                "layout_bind",
                binding | {"incarnation": self.session["incarnation"] + 1},
            )
        self.service.replace_fixture_session(self.session["id"])
        with self.assertRaises(Conflict):
            self.command("layout_observe", observation)

    def test_consultant_branch_isolation_and_owner_only_status(self):
        self.grant_and_handoff()
        source_row = self.service.store.db.execute(
            "SELECT digest FROM coordination_handoffs WHERE id=?",
            (self.packet["operation_id"],),
        ).fetchone()
        source = self.gateway.current_source(
            {
                "handoff_operation": self.packet["operation_id"],
                "handoff_digest": source_row[0],
            }
        )
        self.assertIsNotNone(source)
        config = json.loads(
            (
                Path(__file__).resolve().parents[1] / "fixtures/chirality-config.json"
            ).read_text()
        )
        for branch in config["branches"]:
            role = self.gateway.config.data["roles"][branch["role"]]
            branch.update(
                provider=role["provider"],
                harness=role["harness"],
                harness_version=role["harness_version"],
                requested_model=role["model"],
                effort=role["effort"],
                config_revision=self.gateway.config.config_rev,
            )
        config["deadline_at"] = self.packet["deadline"]
        consultation_id = "gateway-consultation"
        packet = {
            "schema_version": 1,
            "revision": 1,
            "question": "Check the fixture handoff",
            "evidence": ["fixture:handoff"],
            "target": None,
            "source": source,
        }
        start = self.command(
            "consult_start",
            {
                "consultation_id": consultation_id,
                "config": config,
                "packet": packet,
                "budget_id": self.packet["budget_ref"],
            },
            self.fable,
        )
        self.assertEqual(start["result"]["state"], "collecting")
        status = self.command(
            "consult_status", {"consultation_id": consultation_id}, self.fable
        )["result"]
        self.assertEqual(status["id"], consultation_id)
        fable_actor = GatewayContext(
            "adapter",
            Actor("consultant", "fable", "chirality:gateway-consultation:1:fable", 1),
        )
        astra_actor = GatewayContext(
            "adapter",
            Actor("consultant", "astra", "chirality:gateway-consultation:1:astra", 1),
        )
        with self.assertRaises(PermissionError):
            self.command(
                "consult_status", {"consultation_id": consultation_id}, fable_actor
            )
        response = {
            "schema_version": 1,
            "consultation_id": consultation_id,
            "invocation_id": fable_actor.actor.session,
            "round": 1,
            "role": "fable",
            "requested_model": config["branches"][0]["requested_model"],
            "resolved_model": config["branches"][0]["requested_model"],
            "requested_provider": config["branches"][0]["provider"],
            "requested_harness": config["branches"][0]["harness"],
            "requested_harness_version": config["branches"][0]["harness_version"],
            "requested_effort": config["branches"][0]["effort"],
            "requested_config_revision": config["branches"][0]["config_revision"],
            "resolved_provider": config["branches"][0]["provider"],
            "resolved_harness": config["branches"][0]["harness"],
            "resolved_harness_version": config["branches"][0]["harness_version"],
            "resolved_effort": config["branches"][0]["effort"],
            "packet_revision": 1,
            "packet_digest": start["result"]["packet_digest"],
            "status": "complete",
            "recommendation": "inspect",
            "evidence": ["fixture:handoff"],
            "assumptions": [],
            "objections": ["check independent evidence"],
            "actual_microusd": 3,
        }
        with self.assertRaises(PermissionError):
            self.command(
                "consult_response",
                {
                    "consultation_id": consultation_id,
                    "response": response | {"role": "astra"},
                },
                fable_actor,
            )
        with self.assertRaises(PermissionError):
            self.command(
                "consult_response",
                {"consultation_id": consultation_id, "response": response},
                astra_actor,
            )
        self.command(
            "consult_response",
            {"consultation_id": consultation_id, "response": response},
            fable_actor,
        )
        self.assertEqual(
            len(
                self.command(
                    "consult_status", {"consultation_id": consultation_id}, self.fable
                )["result"]["responses"]
            ),
            1,
        )
        self.command("consult_close", {"consultation_id": consultation_id}, self.fable)
        self.command("stop", {"reason": "fixture stop before delayed usage"})
        usage = {
            "consultation_id": consultation_id,
            "invocation_id": astra_actor.actor.session,
            "round": 1,
            "role": "astra",
            "actual_microusd": 4,
        }
        with self.assertRaises(PermissionError):
            self.command("consult_usage", usage, fable_actor)
        with self.assertRaises(PermissionError):
            self.command(
                "consult_usage", usage | {"invocation_id": "spoofed"}, astra_actor
            )
        recorded = self.command("consult_usage", usage, astra_actor)
        self.assertEqual(recorded["result"]["status"], "usage_recorded")
        row = self.service.store.db.execute(
            "SELECT state,actual FROM reservations WHERE id=?",
            (astra_actor.actor.session,),
        ).fetchone()
        self.assertEqual(tuple(row), ("settled", 4))

    def test_isolated_consultant_cannot_use_operator_or_owner_paths(self):
        consultant = GatewayContext(
            "adapter", Actor("consultant", "fable", "fake-session", 1)
        )
        for action, payload in [
            ("status", {}),
            ("portfolio", {"projects": [self.project["id"]], "grant_ids": {}}),
            ("grant", self.grant),
            ("layout_observe", {"schema_version": 1}),
        ]:
            with self.subTest(action=action), self.assertRaises(PermissionError):
                self.command(action, payload, consultant)


if __name__ == "__main__":
    unittest.main()
