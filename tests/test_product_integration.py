"""Exercise the product slice through the recorded service command path."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from odin.contracts import ROOT, identifier
from odin.coordination import Actor
from odin.gateway import Gateway, GatewayContext
from odin.service import Service, fixture_record
from odin.store import Conflict, digest, now


class ProductIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Path(self.temp.name))
        self.gateway = Gateway(self.service)
        self.project = fixture_record("Project", name="Atlas")
        self.other = fixture_record("Project", name="Atlas Archive")
        self.commitment = fixture_record("Commitment", project=self.project["id"])
        for item in (self.project, self.other, self.commitment):
            self.service.store.create(item)
        self.context = GatewayContext(
            "terminal", Actor("operator", "operator-1"), (self.project["id"],)
        )

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def command(self, action, payload):
        return {
            "schema_version": 1,
            "operation_id": identifier(),
            "action": action,
            "payload": payload,
        }

    def submit(self, action, payload, context=None):
        return self.gateway.submit(
            self.command(action, payload), context=context or self.context
        )["result"]

    def test_resume_delivery_ack_and_restart_use_recorded_path(self):
        command = self.command("resume", {"project": self.project["id"]})
        view = self.gateway.submit(command, context=self.context)["result"]
        with self.assertRaises(Conflict):
            self.gateway.submit(command, context=self.context)
        delivery = self.submit("view_delivery", {"briefing": view})["delivery_id"]
        self.assertEqual(
            self.submit("resume", {"project": self.project["id"]})["acknowledged_seq"],
            0,
        )
        self.service.close()
        self.service = Service(Path(self.temp.name))
        self.gateway = Gateway(self.service)
        self.submit("view_ack", {"delivery_id": delivery})
        current = self.submit("resume", {"project": self.project["id"]})
        self.assertEqual(current["acknowledged_seq"], view["acknowledgeable_seq"])
        self.assertEqual(current["commitment_count"], 1)
        with self.assertRaises(PermissionError):
            self.submit("resume", {"project": self.other["id"]})

    def test_source_projection_is_not_cached_or_replayed_after_revocation(self):
        content = "synthetic_private_detail_7bdb"
        self.gateway.memory.add_source(
            {
                "id": "source",
                "project": self.project["id"],
                "revision": 1,
                "digest": hashlib.sha256(content.encode()).hexdigest(),
                "producer": "fixture",
                "source_class": "status",
                "locator": "fixture:source",
                "span": None,
                "readers": ["operator-1"],
                "permissions_revision": 1,
                "event_at": now(),
                "effective_at": None,
                "observed_at": now(),
                "retrieved_at": now(),
                "ingest_seq": 1,
                "content": content,
            }
        )
        self.gateway.memory.add_statement(
            {
                "id": "statement",
                "project": self.project["id"],
                "kind": "report",
                "status": "reported",
                "text": content,
                "speaker": "fixture-worker",
                "source_refs": [{"id": "source", "revision": 1, "span": None}],
                "statement_refs": [],
                "recorded_at": now(),
                "effective_from": None,
                "effective_to": None,
                "authority_ref": None,
                "extraction_config": "fixture:1",
            }
        )
        request = self.command("memory_snapshot", {"project": self.project["id"]})
        first = self.gateway.submit(request, context=self.context)
        self.assertIn(content, json.dumps(first))
        stored = self.service.store.db.execute(
            "SELECT result FROM gateway_commands WHERE id=?", (request["operation_id"],)
        ).fetchone()[0]
        self.assertNotIn(content, stored)
        self.gateway.memory.redact("source", 1, ["archive"])
        with self.assertRaises(Conflict):
            self.gateway.submit(request, context=self.context)
        current = self.submit("memory_snapshot", {"project": self.project["id"]})
        self.assertNotIn(content, json.dumps(current))
        self.gateway.memory.purge_local_storage()
        self.assertEqual(
            [
                r["state"]
                for r in self.gateway.memory.redaction_receipts("source", 1)
                if r["destination"] == "archive"
            ],
            ["pending"],
        )

    def test_prepared_answer_uses_service_policy_and_current_evidence(self):
        item = {
            "schema_version": 1,
            "project": self.project["id"],
            "dedupe_key": "choice",
            "recipient": "caller-cannot-select-principal",
            "kind": "clarification",
            "question": "Choose next step?",
            "options": ["continue", "revise"],
            "recommendation": "continue",
            "evidence": [{"ref": "record:" + self.project["id"], "revision": "1"}],
            "artifact": {
                "ref": "record:" + self.project["id"],
                "digest": digest(self.project),
            },
            "authorization": {"action": "record answer", "scope": [self.project["id"]]},
            "blockers": [],
            "urgency": "routine",
            "commitments": [{"id": self.commitment["id"], "rev": 1}],
            "record_refs": [],
            "memory_revision": 0,
            "authority_revision": "untrusted-old-policy",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        prepared = self.submit("prepare_decision", {"decision": item})
        self.assertEqual(prepared["recipient"], "operator-1")
        answer = {
            "request_id": prepared["id"],
            "response": "continue",
            "expected_rev": 1,
            "evidence_digest": digest(item["evidence"]),
        }
        original = self.gateway.config.data["config_rev"]
        self.gateway.config.data["config_rev"] = "changed-policy"
        with self.assertRaises(Conflict):
            self.submit("answer_decision", answer)
        self.gateway.config.data["config_rev"] = original
        with self.assertRaises(PermissionError):
            self.submit(
                "answer_decision",
                answer,
                GatewayContext("voice", self.context.actor, self.context.projects),
            )
        result = self.submit("answer_decision", answer)
        self.assertEqual(result["state"], "answered")
        commitment = self.service.store.get(self.commitment["id"])
        self.assertEqual(commitment["state"], "open")
        self.assertEqual(commitment["open_decisions"], [])
        self.assertEqual(commitment["decisions"], [])

    def test_prepared_receipt_cannot_replay_after_scope_revocation(self):
        item = {
            "schema_version": 1,
            "project": self.project["id"],
            "dedupe_key": "private-choice",
            "recipient": "operator-1",
            "kind": "clarification",
            "question": "Private question?",
            "options": ["continue"],
            "recommendation": "continue",
            "evidence": [{"ref": "record:" + self.project["id"], "revision": "1"}],
            "artifact": {
                "ref": "record:" + self.project["id"],
                "digest": digest(self.project),
            },
            "authorization": {"action": "record answer", "scope": [self.project["id"]]},
            "blockers": [],
            "urgency": "routine",
            "commitments": [{"id": self.commitment["id"], "rev": 1}],
            "record_refs": [],
            "memory_revision": 0,
            "authority_revision": "old-policy",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        command = self.command("prepare_decision", {"decision": item})
        first = self.gateway.submit(command, context=self.context)
        self.assertEqual(first["result"]["question"], "Private question?")
        revoked = GatewayContext("terminal", self.context.actor, ())
        with self.assertRaises(PermissionError):
            self.gateway.submit(command, context=revoked)
        with self.assertRaises(PermissionError):
            self.submit("status", {}, revoked)

    def test_gateway_can_page_all_obligations_with_revision_token(self):
        for index in range(34):
            self.service.store.create(
                fixture_record(
                    "Commitment",
                    project=self.project["id"],
                    objective=f"Additional {index}",
                )
            )
        first = self.submit(
            "resume", {"project": self.project["id"], "obligation_limit": 32}
        )
        second = self.submit(
            "resume",
            {
                "project": self.project["id"],
                "obligation_offset": first["next_obligation_offset"],
                "obligation_page_token": first["next_obligation_page_token"],
            },
        )
        self.assertEqual(len(first["commitments"]) + len(second["commitments"]), 35)

    def test_redaction_scrubs_prepared_view_receipts_and_active_files(self):
        secret = "SOURCE_BOUND_PRIVATE_CHOICE_7DBF" * 4
        source = {
            "id": "private-source",
            "project": self.project["id"],
            "revision": 1,
            "digest": hashlib.sha256(secret.encode()).hexdigest(),
            "producer": "fixture",
            "source_class": "status",
            "locator": "fixture:private",
            "span": None,
            "readers": ["operator-1"],
            "permissions_revision": 1,
            "event_at": now(),
            "effective_at": None,
            "observed_at": now(),
            "retrieved_at": now(),
            "ingest_seq": 1,
            "content": secret,
        }
        self.gateway.memory.add_source(source)
        item = {
            "schema_version": 1,
            "project": self.project["id"],
            "dedupe_key": "private",
            "recipient": "operator-1",
            "kind": "clarification",
            "question": secret,
            "options": ["continue", "revise"],
            "recommendation": secret,
            "evidence": [{"ref": "record:" + self.project["id"], "revision": "1"}],
            "artifact": {
                "ref": "record:" + self.project["id"],
                "digest": digest(self.project),
            },
            "authorization": {"action": "record answer", "scope": [self.project["id"]]},
            "blockers": [],
            "urgency": "routine",
            "commitments": [{"id": self.commitment["id"], "rev": 1}],
            "record_refs": [],
            "memory_revision": self.gateway.memory.dependency_revision(
                self.project["id"]
            ),
            "authority_revision": "old-policy",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        command = self.command("prepare_decision", {"decision": item})
        prepared = self.gateway.submit(command, context=self.context)["result"]
        self.assertEqual(prepared["question"], secret)
        before = self.submit("resume", {"project": self.project["id"]})
        self.assertIn(secret, json.dumps(before))
        self.gateway.memory.redact("private-source", 1, ["backup"])
        with self.assertRaises(Conflict):
            self.gateway.submit(command, context=self.context)
        after = self.submit("resume", {"project": self.project["id"]})
        self.assertNotIn(secret, json.dumps(after))
        self.assertEqual(self.service.store.get(prepared["id"])["state"], "cancelled")
        self.assertEqual(self.service.store.get(self.commitment["id"])["state"], "open")
        self.assertTrue(self.gateway.memory.purge_local_storage())
        files = [self.service.store.path, Path(str(self.service.store.path) + "-wal")]
        self.assertFalse(
            any(secret.encode() in path.read_bytes() for path in files if path.exists())
        )
        receipts = self.gateway.memory.redaction_receipts("private-source", 1)
        self.assertEqual(
            {r["destination"]: r["state"] for r in receipts},
            {"backup": "pending", "local_storage": "confirmed"},
        )

    def test_legacy_decision_history_keeps_local_purge_pending(self):
        secret = "LEGACY_DECISION_TEXT_8B31"
        self.gateway.memory.add_source(
            {
                "id": "legacy-source",
                "project": self.project["id"],
                "revision": 1,
                "digest": hashlib.sha256(secret.encode()).hexdigest(),
                "producer": "fixture",
                "source_class": "status",
                "locator": "fixture:legacy",
                "span": None,
                "readers": ["operator-1"],
                "permissions_revision": 1,
                "event_at": now(),
                "effective_at": None,
                "observed_at": now(),
                "retrieved_at": now(),
                "ingest_seq": 1,
                "content": secret,
            }
        )
        item = {
            "schema_version": 1,
            "project": self.project["id"],
            "dedupe_key": "legacy",
            "recipient": "operator-1",
            "kind": "clarification",
            "question": secret,
            "options": ["A"],
            "recommendation": "A",
            "evidence": [{"ref": "record:" + self.project["id"], "revision": "1"}],
            "artifact": {
                "ref": "record:" + self.project["id"],
                "digest": digest(self.project),
            },
            "authorization": {"action": "record answer", "scope": [self.project["id"]]},
            "blockers": [],
            "urgency": "routine",
            "commitments": [{"id": self.commitment["id"], "rev": 1}],
            "record_refs": [],
            "memory_revision": self.gateway.memory.dependency_revision(
                self.project["id"]
            ),
            "authority_revision": "old-policy",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z"),
        }
        request = self.submit("prepare_decision", {"decision": item})
        # Simulate a request created by the earlier implementation, which
        # persisted full question text in append-only record history.
        self.service.store.update(request["id"], {"question": secret}, 1)
        self.gateway.memory.redact("legacy-source", 1, ["backup"])
        self.assertFalse(self.gateway.memory.purge_local_storage())
        receipts = {
            r["destination"]: r["state"]
            for r in self.gateway.memory.redaction_receipts("legacy-source", 1)
        }
        self.assertEqual(receipts["legacy_history"], "pending")
        self.assertEqual(receipts["local_storage"], "pending")

    def test_public_cli_inventory_and_restart_demo(self):
        env = os.environ | {"PYTHONPATH": str(ROOT / "python")}
        inventory = subprocess.run(
            [sys.executable, "-m", "odin", "capabilities"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        states = {
            c["id"]: c["state"] for c in json.loads(inventory.stdout)["capabilities"]
        }
        self.assertEqual(states["live_saga"], "blocked")
        state = Path(self.temp.name) / "demo"
        result = subprocess.run(
            [sys.executable, "-m", "odin", "--state", str(state), "continuity-demo"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(result.stdout)
        self.assertTrue(report["other_project_excluded"])
        self.assertGreater(report["unacknowledged_changes"], 0)
        self.assertEqual(
            report["decision"]["question"], "Accept the changed interface requirement?"
        )


if __name__ == "__main__":
    unittest.main()
