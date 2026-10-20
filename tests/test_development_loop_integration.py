"""Real service/channel/hook round trip using a synthetic evaluator executable.

No model, account, desktop or live runtime is involved. The executive driver
stands in for native Claude processing a channel event; it never manually
forwards evaluator results or calls the service tick.
"""

import os
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from odin.contracts import ROOT, canonical, identifier, strict_loads
from odin.executive_service import prepare_project
from odin.service import Service
from odin.development_loop import DevelopmentLoop

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "22222222-2222-4222-8222-222222222222"

FAKE_EVALUATOR = r'''
import hashlib
import json
import re
import sys
from pathlib import Path

arguments = sys.argv[1:]
if "--version" in arguments:
    print("codex-cli 0.0.0-synthetic")
    raise SystemExit(0)
prompt = arguments[-1]
match = re.search(r"(/[^\s\"']*/packet\.json)", prompt)
if match is None:
    raise SystemExit("synthetic evaluator did not receive an exact packet path")
packet = json.loads(Path(match.group(1)).read_text())
round_number = packet["round"]
if round_number:
    assert packet["evidence"]["repository_revision"] == f"synthetic-revision-{round_number}"
    assert f"Synthetic stage {round_number} finished" in packet["executive_final_text"]
result = {
    "decision": "complete" if round_number == 2 else "continue",
    "assessment": f"Independent synthetic assessment after round {round_number}",
    "findings": ["Synthetic evidence read by evaluator executable"],
    "next_prompt": "" if round_number == 2 else f"Execute synthetic stage {round_number + 1}",
    "evidence_refs": [{
        "ref": "fixture:result",
        "revision": str(round_number),
        "digest": hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest(),
    }],
}
encoded = json.dumps(result)
Path(arguments[arguments.index("-o") + 1]).write_text(encoded)
print(json.dumps({"type": "thread.started", "thread_id": "synthetic-evaluator-thread"}))
print(json.dumps({"type": "item.completed", "item": {
    "type": "agent_message", "text": encoded,
}}))
print(json.dumps({"type": "turn.completed", "usage": {
    "input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 10,
}}))
'''


class BridgeClient:
    """Bounded JSONL reader that retains notifications interleaved with replies."""

    def __init__(self, state, project, environment, session_id=SESSION):
        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "odin.executive_mcp",
                "--state", str(state), "--project", project,
                "--development-loop", "--session-id", session_id,
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, bufsize=0,
        )
        self.buffer = bytearray()
        self.events = []
        self.request_id = 0
        initialized = self.request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "synthetic-executive", "version": "1"},
        })
        if initialized["capabilities"].get("experimental") != {"claude/channel": {}}:
            raise AssertionError("channel capability was not advertised")
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, message):
        self.process.stdin.write((canonical(message) + "\n").encode())
        self.process.stdin.flush()

    def read(self, timeout=20):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                if not selector.select(max(0, deadline - time.monotonic())):
                    raise AssertionError("timed out waiting for channel or RPC frame")
                chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise AssertionError("executive MCP exited before returning a frame")
            self.buffer.extend(chunk)
            if len(self.buffer) > 1048576:
                raise AssertionError("unbounded MCP output")
        line, _, remainder = self.buffer.partition(b"\n")
        self.buffer = bytearray(remainder)
        return strict_loads(line.decode())

    def request(self, method, params):
        self.request_id += 1
        current = self.request_id
        self.send({"jsonrpc": "2.0", "id": current, "method": method, "params": params})
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            frame = self.read(deadline - time.monotonic())
            if "id" not in frame:
                self.events.append(frame)
                continue
            if frame.get("id") != current or "error" in frame:
                raise AssertionError("unexpected MCP response: " + canonical(frame))
            return frame["result"]
        raise AssertionError("RPC deadline expired")

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def result(self, name, arguments):
        response = self.call(name, arguments)
        if response["isError"]:
            raise AssertionError(response["content"][0]["text"])
        receipt = strict_loads(response["content"][0]["text"])
        if "operation_id" in arguments and receipt["operation_id"] != arguments["operation_id"]:
            raise AssertionError("mutating tool replaced its stable operation identity")
        return receipt["result"]

    def notification(self):
        frame = self.events.pop(0) if self.events else self.read()
        if frame.get("method") != "notifications/claude/channel":
            raise AssertionError("expected channel notification: " + canonical(frame))
        return frame["params"]

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.stdin = None
        try:
            _, errors = self.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            _, errors = self.process.communicate()
            raise AssertionError("MCP bridge did not stop on EOF")
        if self.process.returncode != 0 or errors:
            raise AssertionError("MCP bridge failed: " + errors.decode())


class DevelopmentLoopIntegrationTests(unittest.TestCase):
    def setUp(self):
        from odin.development_evaluator import configure

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.state = root / "state"
        self.state.mkdir(mode=0o700)
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        config_dir = root / "evaluator-login"
        config_dir.mkdir(mode=0o700)
        executable = root / "synthetic-evaluator"
        executable.write_text("#!" + sys.executable + "\n" + FAKE_EVALUATOR)
        executable.chmod(0o700)
        configure(self.state, {
            "schema_version": 1,
            "enabled": True,
            "harness": "codex",
            "binary": str(executable),
            "workspace": str(workspace),
            "config_dir": str(config_dir),
            "model": "synthetic-evaluator",
            "timeout_seconds": 30,
        })
        self.project = prepare_project(self.state)
        self.environment = os.environ | {"PYTHONPATH": str(ROOT / "python")}
        self.service = None
        self.bridge = None
        self.addCleanup(self.cleanup_processes)

    def cleanup_processes(self):
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None
        if self.service is not None:
            self.stop_service()

    def start_service(self):
        self.service = subprocess.Popen(
            [sys.executable, "-m", "odin", "--state", str(self.state),
             "serve", "--executive-project", self.project],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.environment, bufsize=0,
        )
        with selectors.DefaultSelector() as selector:
            selector.register(self.service.stdout, selectors.EVENT_READ)
            if not selector.select(15):
                self.fail("development service did not become ready")
        first = self.service.stdout.readline().decode()
        if not first.startswith("Fixture service ready:"):
            self.service.kill()
            _, errors = self.service.communicate()
            self.service = None
            self.fail("service startup failed: " + first + errors.decode())

    def stop_service(self):
        process = self.service
        self.service = None
        process.send_signal(signal.SIGTERM)
        try:
            _, errors = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        self.assertEqual(process.returncode, 0, errors.decode())
        self.assertEqual(errors, b"")
        self.assertFalse((self.state / "executive.sock").exists())

    def operator(self, action, payload):
        command = {
            "schema_version": 1, "operation_id": identifier(),
            "action": action, "payload": payload,
        }
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(str(self.state / "service.sock"))
            client.sendall((canonical({"surface": "terminal", "command": command}) + "\n").encode())
            with client.makefile("rb") as stream:
                receipt = strict_loads(stream.readline(1048577))
        self.assertNotIn("error", receipt, canonical(receipt))
        self.assertEqual(receipt["operation_id"], command["operation_id"])
        return receipt["result"]

    def hook(self, final_text, *, prompt_id):
        event = {
            "session_id": SESSION, "prompt_id": prompt_id,
            "hook_event_name": "Stop", "stop_hook_active": False,
            "last_assistant_message": final_text, "background_tasks": [], "session_crons": [],
            "scratchpad_dir": "/synthetic/native-field-ignored",
        }
        completed = subprocess.run(
            [sys.executable, "-m", "odin.executive_loop_hook",
             "--state", str(self.state), "--project", self.project, "--session-id", SESSION],
            env=self.environment, input=canonical(event).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, b"")
        self.assertEqual(completed.stderr, b"")

    def test_two_stages_without_message_relay_and_with_completion_outage(self):
        self.start_service()
        self.bridge = BridgeClient(self.state, self.project, self.environment)
        tools = self.bridge.request("tools/list", {})["tools"]
        self.assertTrue(
            {"odin_loop_claim", "odin_loop_ready", "odin_loop_status"}
            <= {item["name"] for item in tools}
        )
        started = self.operator("loop_start", {
            "project": self.project, "session_id": SESSION,
            "goal": "Demonstrate two synthetic autonomous development stages.",
            "max_rounds": 4, "no_progress_limit": 3,
            "evidence_packet": {"baseline": "synthetic fixture"},
        })
        loop_id = started["loop"]["id"]
        first = self.bridge.notification()
        self.assertEqual(first["meta"]["loop_id"], loop_id)
        self.assertIn("Execute synthetic stage 1", first["content"])

        # A broken MCP connection re-delivers the same stable message identity.
        self.bridge.close()
        self.bridge = BridgeClient(self.state, self.project, self.environment)
        self.assertEqual(self.bridge.notification(), first)

        foreign = BridgeClient(self.state, self.project, self.environment, OTHER_SESSION)
        try:
            response = foreign.call("odin_loop_claim", {
                "operation_id": identifier(), "loop_id": loop_id,
                "stage_id": first["meta"]["stage_id"],
            })
            self.assertTrue(response["isError"])
        finally:
            foreign.close()

        completed_texts = []
        for round_number, notification in ((1, first), (2, None)):
            if notification is None:
                notification = self.bridge.notification()
            self.assertIn(f"Execute synthetic stage {round_number}", notification["content"])
            stage_id = notification["meta"]["stage_id"]
            claim_args = {
                "operation_id": identifier(), "loop_id": loop_id, "stage_id": stage_id,
            }
            claimed = self.bridge.result("odin_loop_claim", claim_args)
            self.assertEqual(claimed, self.bridge.result("odin_loop_claim", claim_args))
            self.assertEqual(claimed["stage"]["state"], "claimed")
            ready = self.bridge.result("odin_loop_ready", {
                "operation_id": identifier(), "loop_id": loop_id, "stage_id": stage_id,
                "evidence_packet": {
                    "repository_revision": f"synthetic-revision-{round_number}",
                    "test_result": "synthetic test passed",
                },
            })
            final_text = f"Synthetic stage {round_number} finished.\n" + ready["completion_marker"]
            completed_texts.append(final_text)
            if round_number == 1:
                # No service or driver calls can relay this completion now.
                self.stop_service()
                self.hook(final_text, prompt_id=f"synthetic-prompt-{round_number}")
                spooled = list((self.state / "executive-loop-spool").glob("*.json"))
                self.assertEqual(len(spooled), 1)
                saved = strict_loads(spooled[0].read_text())
                self.assertEqual(saved["payload"]["last_assistant_message"], final_text)
                self.start_service()
            else:
                self.hook(final_text, prompt_id=f"synthetic-prompt-{round_number}")

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            status = self.bridge.result("odin_loop_status", {"loop_id": loop_id})
            loop = status["loops"][0]
            if loop["status"] == "complete":
                break
            self.assertNotIn(loop["status"], {"needs_operator", "unknown", "stopped"}, canonical(status))
            time.sleep(0.1)
        else:
            self.fail("loop never completed: " + canonical(status))
        self.assertEqual(loop["round"], 2)
        self.assertEqual(list((self.state / "executive-loop-spool").glob("*.json")), [])
        self.bridge.close()
        self.bridge = None
        self.stop_service()

        # Independently inspect the persisted packets after all processes exit.
        with Service(self.state) as service:
            loops = DevelopmentLoop(service.store)
            self.assertEqual(loops.get(loop_id)["status"], "complete")
            jobs = [
                strict_loads(row[0])
                for row in service.store.db.execute(
                    "SELECT body FROM development_loop_jobs WHERE loop_id=?", (loop_id,)
                )
            ]
            self.assertEqual(len(jobs), 3)
            packets = {job["packet"]["round"]: job["packet"] for job in jobs}
            self.assertEqual(packets[1]["executive_final_text"], completed_texts[0])
            self.assertEqual(packets[2]["executive_final_text"], completed_texts[1])
            self.assertTrue(all(job["state"] == "completed" for job in jobs))


if __name__ == "__main__":
    unittest.main()
