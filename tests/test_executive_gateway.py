"""Executive pilot writes remain reported facts, never operator authority."""

import tempfile
import unittest

from odin.contracts import identifier
from odin.coordination import Actor
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict


class ExecutiveGatewayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = prepare_project(self.temp.name)
        self.other = prepare_project(self.temp.name)
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def request(self, action, payload, operation=None):
        return {
            "command": {
                "schema_version": 1,
                "operation_id": operation or identifier(),
                "action": action,
                "payload": payload,
            }
        }

    def send(self, action, payload, operation=None):
        return submit_executive(
            self.gateway, self.request(action, payload, operation), self.project
        )["result"]

    def test_empty_project_and_scoped_read(self):
        view = self.send("resume", {"project": self.project})
        self.assertEqual(view["project"]["id"], self.project)
        self.assertEqual(view["commitment_count"], 0)
        self.assertEqual(self.service.store.get(self.project)["sources"], [])
        with self.assertRaises(PermissionError):
            self.send("resume", {"project": self.other})

    def test_no_operator_actions_or_message_identity_spoofing(self):
        for action in (
            "stop",
            "grant",
            "answer_decision",
            "session_intent",
            "message",
            "portfolio",
        ):
            with self.subTest(action=action), self.assertRaises(PermissionError):
                self.send(action, {"project": self.project})
        request = self.request("resume", {"project": self.project})
        request["surface"] = "terminal"
        with self.assertRaises(PermissionError):
            submit_executive(self.gateway, request, self.project)
        with self.assertRaises(PermissionError):
            self.gateway.submit(
                self.request("resume", {"project": self.project})["command"],
                context=GatewayContext(
                    "harness", Actor("coordinator", "Fable"), (self.project,)
                ),
            )

    def test_report_is_inert_idempotent_and_survives_restart(self):
        operation = identifier()
        payload = {
            "project": self.project,
            "kind": "proposal",
            "summary": "Test shorter briefings.",
        }
        before = self.service.store.records()
        first = self.send("executive_report", payload, operation)
        self.assertEqual(first, self.send("executive_report", payload, operation))
        self.assertFalse(first["report"]["applied"])
        self.assertEqual(first["report"]["verification"], "unverified")
        self.assertEqual(first["report"]["actor"], "fable-executive")
        self.assertEqual(before, self.service.store.records())
        with self.assertRaises(Conflict):
            self.send("executive_report", payload | {"summary": "Changed"}, operation)
        self.service.close()
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        reports = self.send("executive_reports", {"project": self.project})["reports"]
        self.assertEqual(reports, [first["report"]])

    def test_scope_rechecked_before_cached_report(self):
        operation = identifier()
        request = self.request(
            "executive_report",
            {
                "project": self.project,
                "kind": "reported_progress",
                "summary": "Observed a test.",
            },
            operation,
        )
        submit_executive(self.gateway, request, self.project)
        with self.assertRaises(PermissionError):
            submit_executive(self.gateway, request, self.other)

    def test_limits_and_stopped_service_refuse_new_reports(self):
        for limit in (True, 0, 21):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.send(
                    "executive_reports", {"project": self.project, "limit": limit}
                )
        self.gateway.submit(
            self.request("stop", {"reason": "pilot test"})["command"],
            context=GatewayContext("terminal", Actor("operator", "local-operator")),
        )
        with self.assertRaises(Conflict):
            self.send(
                "executive_report",
                {"project": self.project, "kind": "proposal", "summary": "Later"},
            )


if __name__ == "__main__":
    unittest.main()
