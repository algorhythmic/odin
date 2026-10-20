"""Repository evidence enters only through the operator's recorded path."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from odin.contracts import identifier, strict_loads
from odin.coordination import Actor
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.repository_memory import prepare
from odin.service import Service


class RepositoryGatewayTests(unittest.TestCase):
    def test_authorized_import_scope_receipt_and_exact_executive_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = base / "repository"
            repo.mkdir()
            source = "# Synthetic review source\nExplicit evidence, not authority.\n"
            (repo / "README.md").write_text(source)
            for args in (
                ["init", "--quiet"],
                ["add", "README.md"],
                [
                    "-c",
                    "user.name=Synthetic test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "Synthetic repository fixture",
                ],
            ):
                subprocess.run(
                    ["git", "-C", str(repo), *args], check=True, capture_output=True
                )
            state = base / "state"
            project = prepare_project(state)
            other = prepare_project(state)
            payload = prepare(repo, project)[0]
            command = {
                "schema_version": 1,
                "operation_id": identifier(),
                "action": "repository_import",
                "payload": payload,
            }
            with Service(state) as service:
                gateway = Gateway(service)
                with self.assertRaises(PermissionError):
                    submit_executive(gateway, {"command": command}, project)
                for context in (
                    GatewayContext("voice", Actor("operator", "local-operator")),
                    GatewayContext(
                        "terminal", Actor("operator", "local-operator"), (other,)
                    ),
                ):
                    with self.assertRaises(PermissionError):
                        gateway.submit(command, context=context)
                operator = GatewayContext(
                    "terminal", Actor("operator", "local-operator")
                )
                result = gateway.submit(command, context=operator)
                self.assertEqual(result, gateway.submit(command, context=operator))
                self.assertTrue(result["result"]["complete"])
                history = "".join(
                    row[0]
                    for row in service.store.db.execute("SELECT body FROM history")
                )
                self.assertNotIn("Explicit evidence, not authority.", history)
                sources = gateway.memory.snapshot(project, "fable-executive")["sources"]
                ref = next(
                    item
                    for item in sources
                    if item["source_class"] == "repository_committed_text"
                )
                read = {
                    "schema_version": 1,
                    "operation_id": identifier(),
                    "action": "memory_source_read",
                    "payload": {
                        "project": project,
                        "source_id": ref["id"],
                        "revision": ref["revision"],
                    },
                }
                evidence = submit_executive(gateway, {"command": read}, project)
                self.assertEqual(evidence["result"]["source"]["content"], source)
                stored = service.store.db.execute(
                    "SELECT result FROM gateway_commands WHERE id=?",
                    (read["operation_id"],),
                ).fetchone()[0]
                self.assertEqual(
                    strict_loads(stored)["result"], {"projection_not_cached": True}
                )


if __name__ == "__main__":
    unittest.main()
