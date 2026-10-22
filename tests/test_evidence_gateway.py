"""Exact local evidence reads through the recorded operator command path."""

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from jsonschema import ValidationError
from odin.__main__ import main
from odin.contracts import canonical, identifier
from odin.coordination import Actor
from odin.gateway import Gateway, GatewayContext
from odin.service import Service, fixture_record
from odin.store import Conflict, now


class EvidenceGatewayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Path(self.temp.name))
        self.gateway = Gateway(self.service)
        self.project = fixture_record("Project", name="Synthetic evidence project")
        self.other = fixture_record("Project", name="Other project")
        for record in (self.project, self.other):
            self.service.store.create(record)
        self.context = GatewayContext(
            "terminal", Actor("operator", "operator-1"), (self.project["id"],)
        )
        self.source = self.add_source(1, "Synthetic source at revision one")
        self.payload = {
            "project": self.project["id"],
            "source_id": "local-source",
            "revision": 1,
        }

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def add_source(self, revision, content):
        instant = now()
        source = {
            "id": "local-source",
            "project": self.project["id"],
            "revision": revision,
            "digest": hashlib.sha256(content.encode()).hexdigest(),
            "producer": "synthetic-source",
            "source_class": "status",
            "locator": "fixture:local-source",
            "span": None,
            "readers": ["operator-1"],
            "permissions_revision": revision,
            "event_at": instant,
            "effective_at": None,
            "observed_at": instant,
            "retrieved_at": instant,
            "ingest_seq": revision,
            "content": content,
        }
        self.gateway.memory.add_source(source)
        return source

    def command(self, payload=None):
        return {
            "schema_version": 1,
            "operation_id": identifier(),
            "action": "memory_source_read",
            "payload": payload or self.payload,
        }

    def test_exact_revision_is_not_cached_and_revocation_blocks_new_reads(self):
        self.add_source(2, "Synthetic source corrected at revision two")
        command = self.command()
        receipt = self.gateway.submit(command, context=self.context)
        evidence = receipt["result"]
        self.assertEqual(evidence["source"], self.source)
        self.assertEqual(evidence["current_revision"], 2)
        self.assertEqual(evidence["revision_status"], "superseded")
        self.assertEqual(receipt["label"], "fake-backend evidence")
        stored = self.service.store.db.execute(
            "SELECT result FROM gateway_commands WHERE id=?", (command["operation_id"],)
        ).fetchone()[0]
        self.assertEqual(json.loads(stored)["result"], {"projection_not_cached": True})
        self.assertNotIn(self.source["content"], stored)
        with self.assertRaises(Conflict):
            self.gateway.submit(command, context=self.context)
        self.gateway.memory.change_access("local-source", [], 3, 3)
        with self.assertRaisesRegex(Conflict, "source unavailable"):
            self.gateway.submit(self.command(), context=self.context)
        with self.assertRaises(Conflict):
            self.gateway.submit(command, context=self.context)

    def test_current_project_scope_checked_even_for_old_receipt(self):
        command = self.command()
        self.gateway.submit(command, context=self.context)
        revoked = GatewayContext("terminal", self.context.actor, ())
        with self.assertRaises(PermissionError):
            self.gateway.submit(command, context=revoked)
        with self.assertRaises(PermissionError):
            self.gateway.submit(
                self.command(self.payload | {"project": self.other["id"]}),
                context=self.context,
            )

    def test_forged_identity_bad_revision_and_untrusted_surfaces_are_rejected(self):
        before = self.service.store.db.execute(
            "SELECT COUNT(*) FROM gateway_commands"
        ).fetchone()[0]
        for change in (
            {"principal": "operator-1"},
            {"revision": True},
            {"revision": 0},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.gateway.submit(
                    self.command(self.payload | change), context=self.context
                )
        for context in (
            GatewayContext("voice", self.context.actor, self.context.projects),
            GatewayContext(
                "harness", Actor("planner", "operator-1"), self.context.projects
            ),
        ):
            with self.subTest(context=context), self.assertRaises(PermissionError):
                self.gateway.submit(self.command(), context=context)
        after = self.service.store.db.execute(
            "SELECT COUNT(*) FROM gateway_commands"
        ).fetchone()[0]
        self.assertEqual(before, after)


class EvidenceCliTest(unittest.TestCase):
    def test_cli_sends_exact_identity_and_revision_without_caller_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            response = {"result": {"source": {"revision": 7}}}
            transport = MagicMock()
            client = transport.return_value.__enter__.return_value
            client.makefile.return_value.__enter__.return_value = io.BytesIO(
                (canonical(response) + "\n").encode()
            )
            argv = [
                "odin",
                "--state",
                directory,
                "evidence",
                "--project",
                "project-a",
                "--source",
                "source-a",
                "--revision",
                "7",
                "--max-bytes",
                "4096",
            ]
            with (
                patch("sys.argv", argv),
                patch("socket.socket", transport),
                redirect_stdout(io.StringIO()) as output,
            ):
                main()
            wire = json.loads(client.sendall.call_args.args[0])
            self.assertEqual(wire["surface"], "terminal")
            self.assertEqual(wire["command"]["action"], "memory_source_read")
            self.assertEqual(
                wire["command"]["payload"],
                {
                    "project": "project-a",
                    "source_id": "source-a",
                    "revision": 7,
                    "max_bytes": 4096,
                },
            )
            self.assertEqual(json.loads(output.getvalue()), response)


if __name__ == "__main__":
    unittest.main()
