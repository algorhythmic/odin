"""Real service/channel/hook round trip using a synthetic evaluator executable.

No model, account, desktop or live runtime is involved. The executive driver
stands in for native Claude processing a channel event; it never manually
forwards evaluator results or calls the service tick.
"""

import os
import re
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
from odin.execution_receipt import RECEIPT_NAME, reference, run
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
    validation = packet["receipt_validation"]
    if round_number == 1:
        # A contradictory receipt (nonzero exit marked succeeded) must be invalid and
        # can never be summarised as success.
        assert validation["status"] == "invalid", validation
        assert validation["commands_succeeded"] is None, validation
        assert validation["receipts"][0]["succeeded"] is None, validation
        assert any("succeeded disagrees" in p for p in validation["problems"]), validation
    elif round_number == 2:
        # The command removed the repository metadata: post-run observation failed.
        assert validation["status"] == "uncertain", validation
        assert validation["receipts"][0]["observed_before"] is True, validation
        assert validation["receipts"][0]["observed_after"] is False, validation
        assert validation["receipts"][0]["clean"] is None, validation
    else:
        # The evaluator independently re-reads the retained receipt and its artifact.
        assert validation["status"] == "validated", validation
        receipt_ref = packet["evidence"]["receipts"][0]
        raw = Path(receipt_ref["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == receipt_ref["sha256"]
        receipt = json.loads(raw)
        assert receipt["binding"]["stage_id"] == validation["receipts"][0]["binding"]["stage_id"]
        assert receipt["repository"]["before"]["branch"] == "synthetic-branch"
        assert validation["receipts"][0]["head"] == receipt["repository"]["before"]["head"]
        assert validation["commands_succeeded"] is True
        stdout = [a for a in receipt["artifacts"] if a["name"] == "stdout"][0]
        assert hashlib.sha256(Path(stdout["path"]).read_bytes()).hexdigest() == stdout["sha256"]
        assert Path(stdout["path"]).read_text() == "receipted stage 3\n"
        assert receipt["execution"]["exit_status"] == 0
result = {
    "decision": "complete" if round_number == 3 else "continue",
    "assessment": f"Independent synthetic assessment after round {round_number}",
    "findings": ["Synthetic evidence read by evaluator executable"],
    "next_prompt": "" if round_number == 3 else f"Execute synthetic stage {round_number + 1}",
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
        scenario = []
        for round_number, notification in ((1, first), (2, None), (3, None)):
            if notification is None:
                notification = self.bridge.notification()
            self.assertIn(f"Execute synthetic stage {round_number}", notification["content"])
            self.assertEqual(notification["meta"]["kind"], "assignment")
            stage_id = notification["meta"]["stage_id"]
            if round_number == 2:
                # Set a one-second offer deadline through the operator control now
                # that the offer is pending, then leave it unanswered: the service's
                # own tick (real clock, ~6 s) raises attention and offers a stalled
                # notice over the channel without redispatching anything.
                timed = self.operator("loop_control", {
                    "project": self.project, "loop_id": loop_id, "action": "deadlines",
                    "deadlines": {"offer_seconds": 1},
                })
                self.assertEqual(timed["loop"]["deadlines"]["offer_seconds"], 1)
                self.assertEqual(timed["loop"]["status"], "executive_pending")
                deadline = time.monotonic() + 30
                stalled = None
                while time.monotonic() < deadline:
                    frame = self.bridge.read(timeout=max(0.1, deadline - time.monotonic()))
                    if frame.get("method") == "notifications/claude/channel" and frame["params"]["meta"]["kind"] == "notice":
                        stalled = frame["params"]
                        break
                self.assertIsNotNone(stalled, "stalled notice never arrived")
                self.assertIn("offer_unanswered", stalled["content"])
                self.assertIn("does not prove work did not start", stalled["content"])
                self.assertIsNone(re.search(r"odin-development-complete:", stalled["content"]))
                status = self.bridge.result("odin_loop_status", {"loop_id": loop_id})["loops"][0]
                self.assertEqual(status["status"], "executive_pending")
                self.assertEqual(status["work"]["attention"]["observed"], "offer_unanswered")
                self.assertEqual(status["executive_stage"]["id"], stage_id)
                self.assertEqual(status["notices"]["pending"], 1)
                scenario.append({"step": "stalled_notice", "meta": stalled["meta"], "status_work": status["work"]})
                # A reply to the notice is not a completion and is never captured.
                self.hook("Acknowledged the stall notice.\n" + stalled["content"][:120],
                          prompt_id="unrelated-reply")
                self.assertEqual(list((self.state / "executive-loop-spool").glob("*.json")), [])
                unchanged = self.bridge.result("odin_loop_status", {"loop_id": loop_id})["loops"][0]
                self.assertEqual((unchanged["status"], unchanged["revision"]), (status["status"], status["revision"]))
                # Acknowledge it; the loop is untouched and the late claim proceeds.
                ack_operation = identifier()
                acked = self.bridge.result("odin_loop_ack", {"operation_id": ack_operation, "notice_id": stalled["meta"]["notice_id"]})
                self.assertEqual(acked["notice"]["state"], "acknowledged")
                self.assertEqual(acked, self.bridge.result("odin_loop_ack", {"operation_id": ack_operation, "notice_id": stalled["meta"]["notice_id"]}))
                untimed = self.operator("loop_control", {
                    "project": self.project, "loop_id": loop_id, "action": "deadlines",
                    "deadlines": {"offer_seconds": None},
                })
                self.assertIsNone(untimed["loop"]["deadlines"]["offer_seconds"])
                self.assertEqual(untimed["loop"]["revision"], timed["loop"]["revision"])
            claim_args = {
                "operation_id": identifier(), "loop_id": loop_id, "stage_id": stage_id,
            }
            claimed = self.bridge.result("odin_loop_claim", claim_args)
            self.assertEqual(claimed, self.bridge.result("odin_loop_claim", claim_args))
            self.assertEqual(claimed["stage"]["state"], "claimed")
            evidence_packet = {
                "repository_revision": f"synthetic-revision-{round_number}",
                "test_result": "synthetic test passed",
            }
            if round_number in (1, 2, 3):
                # Every round retains a real receipted command run inside a
                # synthetic git repository, bound to this stage. Round one is
                # edited into a contradiction, round two destroys the repository
                # metadata so the post-run observation fails, round three is sound.
                repo = Path(self.temp.name) / f"synthetic-repo-{round_number}"
                repo.mkdir(mode=0o700)
                git_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent",
                           "GIT_AUTHOR_NAME": "Synthetic", "GIT_AUTHOR_EMAIL": "s@example.invalid",
                           "GIT_COMMITTER_NAME": "Synthetic", "GIT_COMMITTER_EMAIL": "s@example.invalid"}
                for arguments in (["init", "--quiet", "-b", "synthetic-branch"], ["commit", "--quiet", "--allow-empty", "-m", "root"]):
                    subprocess.run(["git", "-C", str(repo), *arguments], check=True, capture_output=True, env=git_env)
                head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                                      capture_output=True, text=True, env=git_env).stdout.strip()
                out = Path(self.temp.name) / "receipts" / stage_id
                script = {
                    1: "raise SystemExit(5)",
                    2: "import shutil; shutil.rmtree('.git')",
                    3: "print('receipted stage 3')",
                }[round_number]
                receipt = run(
                    [sys.executable, "-c", script], out=out, cwd=str(repo),
                    binding={"loop_id": loop_id, "stage_id": stage_id},
                )
                if round_number == 1:
                    body = strict_loads((out / RECEIPT_NAME).read_text())
                    body["execution"]["succeeded"] = True  # the contradiction
                    (out / RECEIPT_NAME).write_text(canonical(body) + "\n")
                evidence_packet["receipts"] = [reference(out / RECEIPT_NAME)]
                evidence_packet["claims"] = (
                    {"exit_status": 0, "head": head, "branch": "synthetic-branch", "clean": True}
                    if round_number == 3 else {"succeeded": True}
                )
                self.assertTrue(receipt["repository"]["before"]["observed"])
                self.assertEqual(receipt["repository"]["after"]["observed"], round_number != 2)
            ready = self.bridge.result("odin_loop_ready", {
                "operation_id": identifier(), "loop_id": loop_id, "stage_id": stage_id,
                "evidence_packet": evidence_packet,
            })
            expected_status = {1: "invalid", 2: "uncertain", 3: "validated"}[round_number]
            self.assertEqual(ready["receipt_validation"]["status"], expected_status, canonical(ready))
            summary = ready["receipt_validation"]["receipts"][0]
            if round_number == 3:
                self.assertEqual((summary["branch"], summary["head"], summary["succeeded"]), ("synthetic-branch", head, True))
                self.assertTrue(ready["receipt_validation"]["commands_succeeded"])
            elif round_number == 1:
                # A contradictory receipt can never be summarised as success.
                self.assertIsNone(summary["succeeded"])
                self.assertIsNone(summary["clean"])
                self.assertIsNone(ready["receipt_validation"]["commands_succeeded"])
            else:
                # The command itself succeeded, but a missing post-run observation
                # never establishes a clean, unchanged tree.
                self.assertFalse(summary["observed_after"])
                self.assertTrue(summary["after_reason"])
                self.assertIsNone(summary["clean"])
                self.assertTrue(summary["clean_before"])
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
        self.assertEqual(loop["round"], 3)
        self.assertEqual(list((self.state / "executive-loop-spool").glob("*.json")), [])
        # The completed loop offers a completion notice: no assignment, no footer,
        # same identity across a bridge reconnect, gone once acknowledged.
        completion = self.bridge.notification()
        self.assertEqual(completion["meta"]["kind"], "notice")
        self.assertIn("completion", completion["content"])
        self.assertIn("NOTICE, not an assignment", completion["content"])
        self.assertIsNone(re.search(r"odin-development-complete:", completion["content"]))
        self.assertIn("Independent synthetic assessment after round 3", completion["content"])
        self.bridge.close()
        self.bridge = BridgeClient(self.state, self.project, self.environment)
        replayed = self.bridge.notification()
        self.assertEqual(replayed["meta"]["message_id"], completion["meta"]["message_id"])
        self.hook("Thanks for the notice.", prompt_id="human-chat")
        self.assertEqual(list((self.state / "executive-loop-spool").glob("*.json")), [])
        self.assertEqual(self.bridge.result("odin_loop_status", {"loop_id": loop_id})["loops"][0]["status"], "complete")
        foreign = BridgeClient(self.state, self.project, self.environment, OTHER_SESSION)
        try:
            refused = foreign.call("odin_loop_ack", {"operation_id": identifier(), "notice_id": completion["meta"]["notice_id"]})
            self.assertTrue(refused["isError"])
        finally:
            foreign.close()
        acked = self.bridge.result("odin_loop_ack", {"operation_id": identifier(), "notice_id": completion["meta"]["notice_id"]})
        self.assertEqual(acked["notice"]["kind"], "completion")
        status = self.bridge.result("odin_loop_status", {"loop_id": loop_id})["loops"][0]
        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["notices"]["pending"], 0)
        self.assertEqual(status["notices"]["acknowledged"], 2)
        scenario.append({"step": "completion_notice", "meta": completion["meta"], "notices": status["notices"]})
        self.bridge.close()
        self.bridge = BridgeClient(self.state, self.project, self.environment)
        self.assertEqual(self.bridge.events, [])
        # Operator control of a finished loop and a fresh loop's deadlines go
        # through the socket path; stop never claims to kill native work.
        with self.assertRaises(AssertionError):
            self.operator("loop_control", {"project": self.project, "loop_id": loop_id, "action": "pause"})
        second = self.operator("loop_start", {
            "project": self.project, "session_id": SESSION, "goal": "Second synthetic loop",
            "max_rounds": 1, "deadlines": {"evaluator_seconds": 3600},
        })
        adjusted = self.operator("loop_control", {
            "project": self.project, "loop_id": second["loop"]["id"], "action": "deadlines",
            "deadlines": {"evaluator_seconds": 7200, "offer_seconds": 60},
        })
        self.assertEqual(adjusted["loop"]["deadlines"]["offer_seconds"], 60)
        stopped = self.operator("loop_control", {"project": self.project, "loop_id": second["loop"]["id"], "action": "stop"})
        self.assertTrue(stopped["external_process_stop_required"])
        stop_notice = self.bridge.notification()
        self.assertEqual(stop_notice["meta"]["kind"], "notice")
        self.assertIn("stopped", stop_notice["content"])
        self.assertIn("were not terminated by this", stop_notice["content"])
        scenario.append({"step": "stop_notice", "meta": stop_notice["meta"]})
        retained = Path(self.temp.name) / "scenario-output.json"
        retained.write_text(canonical(scenario) + "\n")
        # When ODIN_SCENARIO_RETAIN names a private directory outside the
        # checkout, keep the exact scenario output there as stage evidence.
        keep = os.environ.get("ODIN_SCENARIO_RETAIN")
        if keep and Path(keep).is_absolute() and ROOT not in Path(keep).resolve().parents:
            target = Path(keep) / "integration-scenario-output.json"
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write(canonical(scenario) + "\n")
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
            self.assertEqual(len(jobs), 4)
            packets = {job["packet"]["round"]: job["packet"] for job in jobs}
            self.assertEqual(packets[1]["executive_final_text"], completed_texts[0])
            self.assertEqual(packets[2]["executive_final_text"], completed_texts[1])
            self.assertEqual(packets[3]["executive_final_text"], completed_texts[2])
            self.assertEqual(packets[1]["receipt_validation"]["status"], "invalid")
            self.assertEqual(packets[2]["receipt_validation"]["status"], "uncertain")
            self.assertEqual(packets[3]["receipt_validation"]["status"], "validated")
            self.assertTrue(all(job["state"] == "completed" for job in jobs))


if __name__ == "__main__":
    unittest.main()
