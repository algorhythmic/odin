"""Authority and retry checks at the service's development-loop boundary."""

import tempfile
import unittest
import uuid

from odin.contracts import canonical, identifier
from odin.coordination import Actor
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict


class DevelopmentGatewayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = prepare_project(self.temp.name)
        self.other = prepare_project(self.temp.name)
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        self.session = str(uuid.uuid4())
        self.operator = GatewayContext("terminal", Actor("operator", "test"))

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def command(self, action, payload, operation=None):
        return {"schema_version": 1, "operation_id": operation or identifier(),
                "action": action, "payload": {"project": self.project} | payload}

    def send(self, action, payload, operation=None, *, executive=False):
        command = self.command(action, payload, operation)
        if executive:
            return submit_executive(self.gateway, {"command": command}, self.project)["result"]
        return self.gateway.submit(command, context=self.operator)["result"]

    def start(self):
        result = self.send("loop_start", {"goal": "Test recovery", "session_id": self.session})
        self.loop = result["loop"]["id"]
        job = result["job"]
        core = self.gateway.development_loop
        core.mark_evaluator_started(self.loop, job["id"], job["packet_digest"], identifier())
        evaluated = core.accept_evaluation(
            self.loop, job["id"], job["packet_digest"],
            {"decision": "continue", "assessment": "First experiment",
             "findings": [], "next_prompt": "Run a bounded test.", "evidence_refs": []},
            identifier(),
        )
        self.stage = evaluated["stage"]["id"]
        return {"loop_id": self.loop, "stage_id": self.stage, "session_id": self.session}

    def test_automatic_inbox_requires_claim_and_exact_completion(self):
        ids = self.start()
        inbox = {"session_id": self.session}
        first = self.send("loop_inbox", inbox, executive=True)
        second = self.send("loop_inbox", inbox, executive=True)
        self.assertEqual(first, second)
        self.assertEqual(first["messages"][0]["stage_id"], self.stage)
        self.assertIn("odin_loop_claim", first["messages"][0]["content"])
        operation = identifier()
        claimed = self.send("loop_claim", ids, operation, executive=True)
        self.assertEqual(claimed, self.send("loop_claim", ids, operation, executive=True))
        self.assertEqual(self.send("loop_inbox", inbox, executive=True), {"messages": []})
        ready = self.send("loop_ready", ids | {"evidence_packet": {"revision": "test-only"}},
                          executive=True)
        unrelated = self.send("loop_capture", {
            "session_id": self.session, "hook_event_name": "Stop",
            "last_assistant_message": "An unrelated conversation",
        }, executive=True)
        self.assertFalse(unrelated["captured"])
        capture = {"session_id": self.session, "hook_event_name": "Stop",
                   "last_assistant_message": "The test passed.\n" + ready["completion_marker"]}
        operation = identifier()
        result = self.send("loop_capture", capture, operation, executive=True)
        self.assertTrue(result["captured"])
        self.assertEqual(result, self.send("loop_capture", capture, operation, executive=True))
        job = self.gateway.development_loop.job(result["job"]["id"])
        self.assertEqual(job["packet"]["executive_final_text"], capture["last_assistant_message"])
        self.assertEqual(job["packet"]["evidence"], {"revision": "test-only"})

    def test_project_scope_checked_before_cached_receipt(self):
        ids = self.start()
        operation = identifier()
        self.send("loop_claim", ids, operation, executive=True)
        for action, payload in [
            ("loop_status", {"loop_id": self.loop}),
            ("loop_claim", ids),
            ("loop_capture", {"session_id": self.session, "hook_event_name": "Stop"}),
        ]:
            with self.subTest(action=action), self.assertRaises(PermissionError):
                command = self.command(action, payload | {"project": self.other}, operation)
                submit_executive(self.gateway, {"command": command}, self.other)
        with self.assertRaises(PermissionError):
            self.send("loop_claim", ids | {"session_id": str(uuid.uuid4())}, executive=True)

    def test_model_cannot_control_start_reconcile_or_hold(self):
        for action in ("loop_start", "loop_control", "loop_hold", "loop_reconcile"):
            with self.subTest(action=action), self.assertRaises(PermissionError):
                self.send(action, {}, executive=True)
        context = GatewayContext("terminal", Actor("operator", "restricted"), (self.other,))
        with self.assertRaises(PermissionError):
            self.gateway.submit(
                self.command("loop_start", {"goal": "Test", "session_id": self.session}),
                context=context,
            )

    def test_cached_claim_cannot_restart_paused_or_stopped_work(self):
        ids = self.start()
        operation = identifier()
        self.send("loop_claim", ids, operation, executive=True)
        view = self.send("resume", {}, executive=True)
        self.assertEqual(view["development_loops"][0]["id"], self.loop)
        for action in ("pause", "stop"):
            self.send("loop_control", {"loop_id": self.loop, "action": action})
            with self.assertRaises(Conflict):
                self.send("loop_claim", ids, operation, executive=True)

    def test_terminal_stage_capture_is_still_project_scoped(self):
        ids = self.start()
        self.send("loop_claim", ids, executive=True)
        ready = self.send("loop_ready", ids | {"evidence_packet": {}}, executive=True)
        payload = {"session_id": self.session, "hook_event_name": "Stop",
                   "last_assistant_message": ready["completion_marker"]}
        self.send("loop_capture", payload, executive=True)
        self.send("loop_control", {"loop_id": self.loop, "action": "stop"})
        with self.assertRaises(PermissionError):
            submit_executive(self.gateway, {"command": self.command(
                "loop_capture", payload | {"project": self.other}
            )}, self.other)

    def test_reconciled_unstarted_stage_has_fresh_delivery_identity(self):
        ids = self.start()
        inbox = {"session_id": self.session}
        first = self.send("loop_inbox", inbox, executive=True)["messages"][0]
        operation = identifier()
        self.send("loop_claim", ids, operation, executive=True)
        self.send("loop_hold", {"loop_id": self.loop, "stage_id": self.stage,
                                "reason": "Test interruption"})
        self.send("loop_reconcile", {
            "loop_id": self.loop, "stage_id": self.stage,
            "target": "executive", "observed": "not_started",
        })
        second = self.send("loop_inbox", inbox, executive=True)["messages"][0]
        self.assertEqual(first["stage_id"], second["stage_id"])
        self.assertNotEqual(first["message_id"], second["message_id"])
        with self.assertRaises(Conflict):
            self.send("loop_claim", ids, operation, executive=True)
        self.send("loop_claim", ids, executive=True)

    def test_internal_inbox_poll_does_not_grow_idle_history(self):
        self.start()
        before = tuple(self.service.store.db.execute(
            "SELECT (SELECT COUNT(*) FROM history), "
            "(SELECT COUNT(*) FROM gateway_commands)"
        ).fetchone())
        for _ in range(10):
            self.send("loop_inbox", {"session_id": self.session}, executive=True)
        after = tuple(self.service.store.db.execute(
            "SELECT (SELECT COUNT(*) FROM history), "
            "(SELECT COUNT(*) FROM gateway_commands)"
        ).fetchone())
        self.assertEqual(before, after)
        with self.assertRaises(PermissionError):
            self.gateway.submit(
                self.command("loop_inbox", {"session_id": self.session}),
                context=GatewayContext("voice", Actor("operator", "test")),
            )

    def test_paused_completion_keeps_same_operation_retryable(self):
        ids = self.start()
        self.send("loop_claim", ids, executive=True)
        ready = self.send("loop_ready", ids | {"evidence_packet": {}}, executive=True)
        control = {"loop_id": self.loop, "action": "pause"}
        self.send("loop_control", control)
        operation = identifier()
        payload = {"session_id": self.session, "hook_event_name": "Stop",
                   "last_assistant_message": "Done\n" + ready["completion_marker"]}
        with self.assertRaises(Conflict):
            self.send("loop_capture", payload, operation, executive=True)
        self.assertIsNone(self.service.store.db.execute(
            "SELECT id FROM gateway_commands WHERE id=?", (operation,)
        ).fetchone())
        self.send("loop_control", control | {"action": "resume"})
        self.assertTrue(self.send("loop_capture", payload, operation, executive=True)["captured"])

    def test_stop_prevents_dispatch_but_preserves_completion(self):
        ids = self.start()
        self.send("loop_claim", ids, executive=True)
        ready = self.send("loop_ready", ids | {"evidence_packet": {}}, executive=True)
        self.gateway.submit(
            {"schema_version": 1, "operation_id": identifier(),
             "action": "stop", "payload": {"reason": "test stop"}},
            context=self.operator,
        )
        self.assertEqual(self.send("loop_inbox", {"session_id": self.session}, executive=True),
                         {"messages": []})
        captured = self.send("loop_capture", {
            "session_id": self.session, "hook_event_name": "Stop",
            "last_assistant_message": ready["completion_marker"],
        }, executive=True)
        self.assertTrue(captured["captured"])
        view = self.send("loop_status", {"loop_id": self.loop}, executive=True)
        self.assertTrue(view["service_stopped"])
        self.assertEqual(view["loops"][0]["status"], "evaluator_pending")

    def test_audit_records_digest_instead_of_conversation(self):
        ids = self.start()
        self.send("loop_claim", ids, executive=True)
        ready = self.send("loop_ready", ids | {"evidence_packet": {}}, executive=True)
        unique_text = "Only the private stage should contain this final response."
        self.send("loop_capture", {
            "session_id": self.session, "hook_event_name": "Stop",
            "last_assistant_message": unique_text + "\n" + ready["completion_marker"],
        }, executive=True)
        rows = self.service.store.db.execute("SELECT body FROM history").fetchall()
        self.assertNotIn(unique_text, canonical([tuple(row) for row in rows]))


if __name__ == "__main__":
    unittest.main()
