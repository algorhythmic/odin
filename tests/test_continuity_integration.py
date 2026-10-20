"""Synthetic local continuity integration; fake-backend component evidence."""

import selectors
import signal
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from odin.contracts import canonical, identifier, strict_loads
from odin.coordination import Actor
from odin.gateway import Gateway, GatewayContext
from odin.integration_demo import PRINCIPAL, SOURCE_ID, SOURCE_REF, run
from odin.service import Service
from odin.store import Conflict, Store


class ContinuityIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name)
        try:
            cls.result = run(cls.path)
        except BaseException:
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_restart_keeps_obligation_and_unacknowledged_delivery(self):
        view = self.result["machine_view"]
        self.assertEqual(view["acknowledged_seq"], 0)
        self.assertGreater(len(view["changes"]) + view["changes_omitted"], 0)
        self.assertEqual(view["commitment_count"], 1)
        commitment = view["commitments"][0]
        with Store(self.path) as store:
            persisted = store.get(commitment["id"])
            self.assertEqual(commitment["rev"], persisted["rev"])
            self.assertEqual(commitment["state"], persisted["state"])
            self.assertEqual(persisted["state"], "blocked")
            self.assertEqual(
                commitment["checkpoints"][0]["summary"],
                persisted["checkpoints"][-1]["summary"],
            )
            recorder = store.get(persisted["checkpoints"][-1]["recorded_by"])
            self.assertEqual(recorder["record_type"], "PlanningSession")
            self.assertEqual(recorder["project"], persisted["project"])
            delivery = store.db.execute(
                "SELECT acknowledged FROM continuity_deliveries WHERE id=?",
                (self.result["delivery"]["delivery_id"],),
            ).fetchone()
            self.assertIsNotNone(delivery)
            self.assertEqual(delivery[0], 0)
            self.assertFalse(any(c["met"] for c in persisted["criteria"]))

    def test_outage_and_recovery_do_not_revive_stale_decision(self):
        stages = self.result["stages"]
        self.assertEqual(stages["unknown"]["coverage"]["availability"], "incomplete")
        self.assertEqual(
            stages["unknown"]["coverage"]["coverage"][0]["availability"], "unknown"
        )
        self.assertEqual(stages["available"]["coverage"]["availability"], "available")
        self.assertEqual(stages["outage"]["coverage"]["availability"], "unavailable")
        self.assertEqual(stages["recovered"]["coverage"]["availability"], "available")
        old_request = self.result["invalidated_decision_id"]
        self.assertEqual(stages["available"]["unavailable_decisions"], [])
        for stage in ("outage", "recovered", "restarted"):
            self.assertIn(old_request, stages[stage]["unavailable_decisions"])
            self.assertEqual(stages[stage]["commitments"][0]["state"], "blocked")
        current_request = self.result["current_decision_id"]
        decisions = {
            d["request"]["id"]: d for d in self.result["machine_view"]["decisions"]
        }
        self.assertNotEqual(old_request, current_request)
        self.assertFalse(decisions[current_request]["prepared"].get("unavailable"))
        self.assertEqual(decisions[current_request]["request"]["state"], "open")
        self.assertEqual(
            decisions[current_request]["prepared"]["memory_revision"],
            self.result["machine_view"]["memory"]["dependency_revision"],
        )

    def test_human_and_bounded_machine_views_agree(self):
        view = self.result["machine_view"]
        human = self.result["human_briefing"]
        self.assertIn(view["project"]["name"], human)
        self.assertIn("Open commitments: 1; pending decisions: 2.", human)
        for commitment in view["commitments"]:
            self.assertIn(commitment["objective"], human)
            self.assertIn(
                f"[{commitment['state']}, revision {commitment['rev']}]", human
            )
            self.assertIn(commitment["checkpoints"][0]["summary"], human)
        self.assertIn("Source coverage: available.", human)
        self.assertIn(view["recommended_next_action"], human)
        self.assertIn(SOURCE_REF, human)
        self.assertEqual(len(view["commitments"]), 1)
        self.assertEqual(len(view["decisions"]), 2)
        self.assertGreater(view["changes_omitted"], 0)
        self.assertIn(f"{view['changes_omitted']} omitted", human)
        self.assertLessEqual(
            sum(len(canonical(change).encode()) for change in view["changes"]),
            view["detail_bytes"],
        )
        self.assertLessEqual(
            len(canonical(self.result["attributed_memory"]).encode()), 4096
        )
        self.assertNotIn("Unrelated private", canonical(view) + human)

    def test_report_evidence_resolves_exact_revision_without_claiming_verification(
        self,
    ):
        exact = self.result["exact_evidence"]
        historical = self.result["historical_evidence"]
        self.assertEqual(exact["source"]["id"], SOURCE_ID)
        self.assertEqual(exact["source"]["revision"], 2)
        self.assertEqual(exact["revision_status"], "current")
        self.assertFalse(exact["historical"])
        self.assertEqual(historical["source"]["revision"], 1)
        self.assertEqual(historical["current_revision"], 2)
        self.assertEqual(historical["revision_status"], "superseded")
        self.assertTrue(historical["historical"])
        self.assertNotEqual(exact["source"]["content"], historical["source"]["content"])
        self.assertEqual(
            exact["source"]["digest"],
            sha256(exact["source"]["content"].encode()).hexdigest(),
        )
        report = self.result["attributed_memory"]["statements"][0]
        self.assertEqual(report["status"], "reported")
        self.assertEqual(report["speaker"], "synthetic-worker")
        self.assertEqual(
            report["source_refs"], [{"id": SOURCE_ID, "revision": 2, "span": None}]
        )
        self.assertIsNone(report["authority_ref"])
        self.assertFalse(any(c["met"] for c in self.result["commitment_criteria"]))

    def test_scoped_command_denial_and_uncached_reads_survive_restart(self):
        project = self.result["machine_view"]["project"]["id"]
        with Service(self.path) as service:
            gateway = Gateway(service)
            context = GatewayContext(
                "terminal", Actor("operator", PRINCIPAL), (project,)
            )
            other = next(
                p["id"] for p in service.store.records("Project") if p["id"] != project
            )
            for action, payload, error in (
                ("resume", {"project": other}, PermissionError),
                (
                    "memory_source_read",
                    {
                        "project": project,
                        "source_id": "synthetic-private-session",
                        "revision": 1,
                    },
                    Conflict,
                ),
            ):
                with self.assertRaises(error):
                    gateway.submit(
                        {
                            "schema_version": 1,
                            "operation_id": identifier(),
                            "action": action,
                            "payload": payload,
                        },
                        context=context,
                    )
            history = [
                strict_loads(row[0])
                for row in service.store.db.execute("SELECT body FROM history")
            ]
            commands = [
                item["payload"]["command"]
                for item in history
                if item["kind"] == "gateway.command"
            ]
            reads = [c for c in commands if c["action"] == "memory_source_read"]
            self.assertEqual(len(reads), 2)
            self.assertTrue(
                {"resume", "prepare_decision", "view_delivery", "memory_snapshot"}
                <= {c["action"] for c in commands}
            )
            for command in reads:
                stored = strict_loads(
                    service.store.db.execute(
                        "SELECT result FROM gateway_commands WHERE id=?",
                        (command["operation_id"],),
                    ).fetchone()[0]
                )
                self.assertEqual(stored["result"], {"projection_not_cached": True})
            self.assertNotIn(
                self.result["exact_evidence"]["source"]["content"], canonical(history)
            )


class ContinuityIntegrationCliTest(unittest.TestCase):
    def test_demo_can_be_served_and_inspected_through_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, "-m", "odin", "--state", directory]
            created = subprocess.run(
                command + ["integration-demo"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(created.returncode, 0, created.stderr + created.stdout)
            demo = strict_loads(created.stdout)
            project = demo["machine_view"]["project"]["id"]
            server = subprocess.Popen(
                command + ["serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(server.stdout, selectors.EVENT_READ)
                    self.assertTrue(
                        selector.select(timeout=10), "fixture CLI did not become ready"
                    )
                ready = server.stdout.readline()
                self.assertIn("Fixture service ready", ready)
                evidence = subprocess.run(
                    command
                    + [
                        "evidence",
                        "--project",
                        project,
                        "--source",
                        SOURCE_ID,
                        "--revision",
                        "2",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(
                    evidence.returncode, 0, evidence.stderr + evidence.stdout
                )
                read = strict_loads(evidence.stdout)
                self.assertEqual(read["label"], "fake-backend evidence")
                self.assertEqual(read["result"]["revision_status"], "current")
                self.assertEqual(
                    read["result"]["source"], demo["exact_evidence"]["source"]
                )
                self.assertEqual(
                    read["result"]["source"]["readers"], ["local-operator"]
                )
                resumed = subprocess.run(
                    command + ["resume", "--project", project],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(resumed.returncode, 0, resumed.stderr + resumed.stdout)
                view = strict_loads(resumed.stdout)["result"]
                self.assertEqual(view["principal"], "local-operator")
                self.assertEqual(view["project"]["id"], project)
                self.assertEqual(view["commitment_count"], 1)
                self.assertEqual(view["commitments"][0]["state"], "blocked")
                self.assertEqual(
                    view["commitments"], demo["machine_view"]["commitments"]
                )
                self.assertEqual(view["memory"]["source_count"], 1)
                self.assertNotIn("Unrelated private", canonical(view))
            finally:
                if server.poll() is None:
                    server.send_signal(signal.SIGINT)
                try:
                    _, error = server.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate(timeout=10)
                    raise
                self.assertEqual(server.returncode, 0, error)


if __name__ == "__main__":
    unittest.main()
