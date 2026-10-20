"""One ADR-027 delegation cycle through the real `serve` process and MCP bridge.

The service and the stdio bridge run as separate subprocesses against a private
temporary state directory. The harness binaries are the synthetic scripts from
``test_delegation``; no model, credential, network or peer feed is used. This
exercises the bridge-to-gateway payload contract (operation identity on the
command envelope versus the tool payload) that component tests cannot see.
"""

import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from odin.contracts import ROOT, canonical, identifier, strict_loads
from odin.delegation import default_config, write_config
from odin.executive_service import prepare_project
from test_delegation import FAKE_CLAUDE, FAKE_CODEX, _script

POLL_INTERVAL = 0.3
POLL_TIMEOUT = 20


class DelegationIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.state = root / "state"
        self.state.mkdir(mode=0o700)
        self.workspace_root = root / "workspaces"
        self.workspace_root.mkdir(mode=0o700)
        self.workspace = self.workspace_root / "one"
        self.workspace.mkdir(mode=0o700)
        config_dir = root / "claude-login"
        config_dir.mkdir(mode=0o700)
        (config_dir / ".credentials.json").write_text("{}")
        (config_dir / ".credentials.json").chmod(0o600)
        codex_home = root / "codex-home"
        codex_home.mkdir(mode=0o700)
        write_config(
            self.state,
            default_config(
                claude_config_dir=config_dir,
                workspace_roots=[self.workspace_root],
                claude_binary=_script(root / "fake-claude", FAKE_CLAUDE),
                codex_binary=_script(root / "fake-codex", FAKE_CODEX),
                codex_home=codex_home,
                turn_timeout_seconds=30,
            ),
        )
        self.project = prepare_project(self.state)
        self.environment = os.environ | {"PYTHONPATH": str(ROOT / "python")}

    # -- process helpers ---------------------------------------------------

    def start_service(self):
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "odin",
                "--state",
                str(self.state),
                "serve",
                "--executive-project",
                self.project,
            ],
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(15):
                process.kill()
                process.communicate()
                self.fail("service did not become ready")
        ready = process.stdout.readline()
        if not ready.startswith("Fixture service ready:"):
            process.kill()
            _, errors = process.communicate()
            self.fail("service startup failed: " + errors)
        enabled = process.stdout.readline()
        if not enabled.startswith("Delegation enabled for harnesses:"):
            process.kill()
            _, errors = process.communicate()
            self.fail("delegation was not enabled: " + enabled + errors)
        self.assertEqual(
            enabled.strip(), "Delegation enabled for harnesses: claude-code, codex"
        )
        return process

    def stop_service(self, process):
        if process.poll() is not None:
            _, errors = process.communicate()
            self.fail("service exited early: " + errors)
        process.send_signal(signal.SIGINT)
        try:
            _, errors = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        self.assertEqual(process.returncode, 0, errors)
        self.assertEqual(errors, "")
        self.assertFalse((self.state / "executive.sock").exists())

    def call(self, name, arguments):
        """One bridge process: initialize, initialized, tools/call."""
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "synthetic-test", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        ]
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "odin.executive_mcp",
                "--state",
                str(self.state),
                "--project",
                self.project,
            ],
            env=self.environment,
            input="".join(canonical(item) + "\n" for item in requests),
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        responses = [strict_loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 2, completed.stdout)
        self.assertEqual(responses[1]["id"], 2)
        return responses[1]["result"]

    def result(self, name, arguments):
        """The service result of a successful tool call."""
        response = self.call(name, arguments)
        self.assertFalse(response["isError"], response["content"][0]["text"])
        receipt = strict_loads(response["content"][0]["text"])
        if "operation_id" in arguments:
            self.assertEqual(receipt["operation_id"], arguments["operation_id"])
        return receipt["result"]

    def refusal(self, name, arguments):
        """The fixed refusal code of a refused tool call."""
        response = self.call(name, arguments)
        self.assertTrue(response["isError"], response["content"][0]["text"])
        text = response["content"][0]["text"]
        prefix = "Executive service refused the request: "
        self.assertTrue(text.startswith(prefix), text)
        self.assertTrue(text.endswith("."), text)
        return text[len(prefix) : -1]

    def turn_view(self, assignment, index):
        """The indexed turn of an assignment as the status tool reports it."""
        view = self.result("odin_delegation_status", {"assignment_id": assignment})
        self.assertTrue(view["enabled"])
        turns = view["sessions"][0]["assignments"][0]["turns"]
        return turns[index] if len(turns) > index else None

    def wait_returned(self, assignment, index):
        """Poll the status tool until the indexed turn has returned."""
        deadline = time.monotonic() + POLL_TIMEOUT
        turn = None
        while time.monotonic() < deadline:
            turn = self.turn_view(assignment, index)
            if turn is not None and turn["state"] == "returned":
                return turn
            if turn is not None and turn["state"] in ("failed", "lost", "interrupted"):
                self.fail("turn ended without returning: " + canonical(turn))
            time.sleep(POLL_INTERVAL)
        self.fail("turn did not return in time: " + canonical(turn))

    # -- the cycle ---------------------------------------------------------

    def test_full_cycle_through_serve_and_bridge(self):
        service = self.start_service()
        try:
            self.run_cycle()
        finally:
            self.stop_service(service)

    def run_cycle(self):
        create_operation = identifier()
        create = {
            "operation_id": create_operation,
            "action": "create",
            "harness": "claude-code",
            "workspace": str(self.workspace),
            "briefing": "You are a synthetic worker.",
            "model": "fake-model",
            "budget_usd": 5,
        }
        opened = self.result("odin_delegation_session", create)
        session = opened["session"]["id"]
        native = opened["session"]["native_session_id"]
        self.assertEqual(opened["session"]["state"], "idle")
        self.assertEqual(opened["session"]["adapter"], "claude-code-print")
        self.assertTrue(native)
        self.assertEqual(opened["binding"]["state"], "active")

        # Replaying the identical command returns the recorded receipt.
        replayed = self.result("odin_delegation_session", create)
        self.assertEqual(replayed["session"]["id"], session)
        # A second session for the same project is refused through the bridge.
        self.assertEqual(
            self.refusal(
                "odin_delegation_session", create | {"operation_id": identifier()}
            ),
            "project_already_has_active_session",
        )
        # A workspace outside the configured roots is refused.
        self.assertEqual(
            self.refusal(
                "odin_delegation_session",
                create
                | {
                    "operation_id": identifier(),
                    "workspace": self.temporary.name,
                },
            ),
            "workspace_outside_configured_roots",
        )

        assigned = self.result(
            "odin_delegation_assign",
            {
                "operation_id": identifier(),
                "session_id": session,
                "objective": "Synthetic objective",
                "criteria": [{"id": "c1", "text": "worker reports"}],
                "scope": "synthetic scope",
                "output_contract": "final text",
                "instructions": "do the thing",
                "limits": {"iterations": 3, "budget_usd": 0.5},
            },
        )
        assignment = assigned["assignment"]
        self.assertEqual(assigned["session"], session)
        self.assertEqual(assigned["state"], "dispatched")
        resume = self.result("odin_resume", {})
        self.assertEqual(
            [c["id"] for c in resume["commitments"]], [assigned["commitment"]]
        )

        first = self.wait_returned(assignment, 0)
        self.assertEqual(first["id"], assigned["turn"])
        self.assertEqual(first["kind"], "assignment")
        self.assertEqual(first["result"]["native_session_id"], native)
        self.assertIsNone(first["failure"])
        returned = self.result("odin_delegation_result", {"turn_id": assigned["turn"]})
        self.assertTrue(returned["available"])
        self.assertEqual(returned["state"], "returned")
        self.assertEqual(returned["session"], session)
        self.assertEqual(returned["assignment"], assignment)
        self.assertIn("worker says: ", returned["final_text"])
        self.assertIn("do the thing", returned["final_text"])
        self.assertEqual(returned["report"]["native_session_id"], native)
        self.assertEqual(returned["verification"], "unverified worker report")
        spec = strict_loads(Path(returned["transcript_paths"]["spec.json"]).read_text())
        self.assertEqual(spec["argv"][spec["argv"].index("--session-id") + 1], native)
        self.assertEqual(spec["cwd"], str(self.workspace))
        self.assertIn(
            self.state / "delegations" / session / assigned["turn"],
            [Path(p).parent for p in returned["transcript_paths"].values()],
        )
        # The session is idle again once the turn has returned.
        status = self.result("odin_delegation_status", {"session_id": session})
        self.assertEqual(status["sessions"][0]["session"]["state"], "idle")
        self.assertEqual(status["sessions"][0]["turn_count"], 1)
        self.assertEqual(status["sessions"][0]["assignments"][0]["state"], "active")
        self.assertEqual(
            status["sessions"][0]["assignments"][0]["commitment_state"], "open"
        )

        # Acceptance before the follow-up would be premature only by policy;
        # here we check the acceptance evidence rule through the bridge first.
        self.assertEqual(
            self.refusal(
                "odin_delegation_close",
                {
                    "operation_id": identifier(),
                    "assignment_id": assignment,
                    "disposition": "accepted",
                    "evidence": {"other": ["turn:" + assigned["turn"]]},
                },
            ),
            "acceptance_evidence_incomplete",
        )

        followed = self.result(
            "odin_delegation_followup",
            {
                "operation_id": identifier(),
                "session_id": session,
                "assignment_id": assignment,
                "message": "and more",
            },
        )
        self.assertEqual(followed["assignment"], assignment)
        self.assertEqual(followed["launch"], "queued_until_service_tick")
        second = self.wait_returned(assignment, 1)
        self.assertEqual(second["id"], followed["turn"])
        self.assertEqual(second["kind"], "followup")
        self.assertEqual(second["result"]["native_session_id"], native)
        self.assertFalse(second["native_session_mismatch"])
        returned = self.result("odin_delegation_result", {"turn_id": followed["turn"]})
        self.assertIn("worker says: ", returned["final_text"])
        self.assertIn("and more", returned["final_text"])
        self.assertEqual(returned["report"]["native_session_id"], native)
        spec = strict_loads(Path(returned["transcript_paths"]["spec.json"]).read_text())
        self.assertEqual(spec["argv"][spec["argv"].index("--resume") + 1], native)
        self.assertNotIn("--session-id", spec["argv"])
        # The assignment-wide result view reports the latest finished turn.
        latest = self.result("odin_delegation_result", {"assignment_id": assignment})
        self.assertEqual(latest["turn"], followed["turn"])

        close_operation = identifier()
        close = {
            "operation_id": close_operation,
            "assignment_id": assignment,
            "disposition": "accepted",
            "evidence": {
                "c1": ["turn:" + assigned["turn"], "turn:" + followed["turn"]]
            },
            "reason": "executive inspected both reports",
        }
        closed = self.result("odin_delegation_close", close)
        self.assertEqual(closed["assignment"], assignment)
        self.assertEqual(closed["commitment"], assigned["commitment"])
        self.assertEqual(closed["assignment_state"], "completed")
        self.assertEqual(closed["commitment_state"], "closed")
        self.assertEqual(closed["acceptance"], "executive_attributed_not_saga_verified")
        # Replaying the close returns the same receipt; a fresh operation is refused.
        self.assertEqual(self.result("odin_delegation_close", close), closed)
        self.assertEqual(
            self.refusal(
                "odin_delegation_close", close | {"operation_id": identifier()}
            ),
            "assignment_closed",
        )
        resume = self.result("odin_resume", {})
        self.assertEqual(resume["commitments"], [])
        status = self.result("odin_delegation_status", {"assignment_id": assignment})
        view = status["sessions"][0]["assignments"][0]
        self.assertEqual(view["state"], "completed")
        self.assertEqual(view["commitment_state"], "closed")
        self.assertEqual(view["criteria"], [{"id": "c1", "met": True}])
        self.assertEqual([t["state"] for t in view["turns"]], ["returned", "returned"])

        stopped = self.result(
            "odin_delegation_session",
            {
                "operation_id": identifier(),
                "action": "stop",
                "session_id": session,
                "reason": "cycle complete",
            },
        )
        self.assertEqual(stopped["session"]["id"], session)
        self.assertEqual(stopped["session"]["state"], "retired")
        self.assertEqual(
            self.refusal(
                "odin_delegation_session",
                {
                    "operation_id": identifier(),
                    "action": "resume",
                    "session_id": session,
                },
            ),
            "session_retired",
        )


if __name__ == "__main__":
    unittest.main()
