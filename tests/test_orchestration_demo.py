"""Exercise the public CLI against synthetic persistent local state."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.contracts import Contracts, strict_loads
from odin.gateway import Gateway
from odin.service import Service


class OrchestrationDemoTest(unittest.TestCase):
    def test_cli_workflow_preserves_authority_and_unknown_cost_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "odin",
                    "--state",
                    directory,
                    "orchestration-demo",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output = strict_loads(result.stdout)
            Contracts().validate("orchestration-demo", output)
            self.assertEqual(output["advice_state"], "escalated")
            self.assertTrue(output["disagreement_preserved"])
            self.assertEqual(output["assignment_state"], "drafted")
            self.assertEqual(output["unknown_cost_reservations"], 1)
            self.assertGreater(output["receipt_count"], 10)
            with Service(Path(directory)) as service:
                service.recover()
                gateway = Gateway(service)
                self.assertTrue(service.store.stopped())
                consultation = gateway.chirality.status(output["consultation"])
                self.assertEqual(consultation["round"], 2)
                self.assertEqual(len(consultation["syntheses"]), 2)
                self.assertEqual(service.backend.resources("run"), [])
                row = service.store.db.execute(
                    "SELECT body FROM coordination_handoffs WHERE id=?",
                    (output["handoff"],),
                ).fetchone()
                handoff = strict_loads(row[0])
                self.assertEqual(
                    service.store.get(handoff["assignment"])["state"], "drafted"
                )


if __name__ == "__main__":
    unittest.main()
