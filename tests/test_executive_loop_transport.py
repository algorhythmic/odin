"""Synthetic protocol/launcher/hook evidence; no model or active session used."""

import io
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from odin import executive_loop_hook as hook
from odin import executive_runtime as runtime
from odin.contracts import ROOT, canonical, strict_loads
from odin.executive_mcp import ExecutiveBridge, MCPServer, ToolFailure

PROJECT = "01K7M000000000000000000001"
LOOP = "01K7M000000000000000000002"
STAGE = "01K7M000000000000000000003"
MESSAGE = "01K7M000000000000000000004"
NOTICE = "01K7M000000000000000000005"
SESSION = "11111111-1111-4111-8111-111111111111"
PROMPT = "bb676593-6951-4da7-9066-cc7a2f048b33"


def receipt(command, result=None):
    return {
        "schema_version": 1,
        "operation_id": command["operation_id"],
        "label": "fake-backend evidence",
        "result": {} if result is None else result,
    }


def initialize(server):
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "synthetic", "version": "1"},
            },
        }
    )
    server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return response["result"]


class ChannelTests(unittest.TestCase):
    def message(self, **changes):
        return {
            "message_id": MESSAGE,
            "loop_id": LOOP,
            "stage_id": STAGE,
            "content": "Inspect the synthetic stage, then claim before acting.",
        } | changes

    def bridge(self, messages):
        gateway = Mock(side_effect=lambda command: receipt(command, {"messages": messages}))
        return ExecutiveBridge(
            PROJECT, gateway, development_loop=True, session_id=SESSION
        ), gateway

    def test_channel_requires_explicit_session_bound_enablement(self):
        plain = MCPServer(ExecutiveBridge(PROJECT, Mock()))
        self.assertNotIn("experimental", initialize(plain)["capabilities"])
        self.assertEqual(plain.channel_notifications(), [])
        for session in (None, "invalid", "12C959F5-9F11-4C51-AEC8-92FB995B88B4"):
            with self.assertRaises(ValueError):
                ExecutiveBridge(PROJECT, Mock(), development_loop=True, session_id=session)
        with self.assertRaisesRegex(ValueError, "not enabled"):
            plain.bridge.call("odin_loop_claim", {})

    def test_notification_is_not_acknowledged_and_reconnect_replays_identity(self):
        bridge, gateway = self.bridge([self.message()])
        server = MCPServer(bridge)
        self.assertEqual(server.channel_notifications(), [])
        gateway.assert_not_called()
        self.assertEqual(
            initialize(server)["capabilities"]["experimental"], {"claude/channel": {}}
        )
        emitted = server.channel_notifications()
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["method"], "notifications/claude/channel")
        self.assertEqual(emitted[0]["params"]["meta"]["message_id"], MESSAGE)
        self.assertEqual(server.channel_notifications(), [])
        self.assertEqual(gateway.call_args.args[0]["action"], "loop_inbox")
        self.assertEqual(
            gateway.call_args.args[0]["payload"],
            {"project": PROJECT, "session_id": SESSION},
        )
        resumed = MCPServer(bridge)
        initialize(resumed)
        self.assertEqual(resumed.channel_notifications(), emitted)
        self.assertTrue(all(call.args[0]["action"] == "loop_inbox" for call in gateway.call_args_list))

    def notice(self, **changes):
        return {
            "kind": "notice",
            "message_id": NOTICE,
            "notice_id": NOTICE,
            "loop_id": LOOP,
            "stage_id": None,
            "content": "NOTICE, not an assignment. Development loop ended.",
        } | changes

    def test_notice_events_are_marked_replayed_until_acknowledged_and_never_claimable(self):
        messages = [self.message(), self.notice()]
        bridge, gateway = self.bridge(messages)
        server = MCPServer(bridge)
        initialize(server)
        emitted = server.channel_notifications()
        self.assertEqual([n["params"]["meta"]["kind"] for n in emitted], ["assignment", "notice"])
        self.assertEqual(emitted[1]["params"]["meta"]["notice_id"], NOTICE)
        self.assertIsNone(emitted[1]["params"]["meta"]["stage_id"])
        self.assertEqual(server.channel_notifications(), [])  # same connection: no repeat
        resumed = MCPServer(bridge)
        initialize(resumed)
        self.assertEqual(resumed.channel_notifications(), emitted)  # reconnect replays both
        # Once the service stops offering the notice, nothing replays it.
        messages.pop()
        fresh = MCPServer(bridge)
        initialize(fresh)
        self.assertEqual([n["params"]["meta"]["kind"] for n in fresh.channel_notifications()], ["assignment"])
        # Malformed notices are refused without marking anything emitted.
        for bad in (
            self.notice(notice_id=STAGE),  # notice id must equal message id
            self.notice(notice_id=None),
            self.notice(kind="bulletin"),
            self.message(stage_id=None),  # assignments need a stage
        ):
            with self.subTest(bad=bad):
                broken, _ = self.bridge([bad])
                server = MCPServer(broken)
                initialize(server)
                with self.assertRaises(ToolFailure):
                    server.channel_notifications()
                self.assertEqual(server.emitted, set())
        # The acknowledgement tool is bound to the session and carries the operation id.
        self.assertFalse(bridge.call("odin_loop_ack", {"operation_id": MESSAGE, "notice_id": NOTICE})["isError"])
        command = gateway.call_args.args[0]
        self.assertEqual(command["action"], "loop_ack")
        self.assertEqual(command["payload"], {"project": PROJECT, "session_id": SESSION, "notice_id": NOTICE})
        self.assertEqual(command["operation_id"], MESSAGE)
        self.assertIn("never claim, execute", bridge.tools()[-1]["description"])
        self.assertIn("meta.kind=notice", initialize(MCPServer(bridge))["instructions"])

    def test_loop_tools_bind_scope_and_preserve_mutation_identity(self):
        bridge, gateway = self.bridge([])
        self.assertTrue(
            {"odin_loop_claim", "odin_loop_ready", "odin_loop_status", "odin_loop_ack"}
            <= {tool["name"] for tool in bridge.tools()}
        )
        arguments = {"operation_id": MESSAGE, "loop_id": LOOP, "stage_id": STAGE}
        for name, supplied in (
            ("odin_loop_claim", arguments),
            ("odin_loop_ready", arguments | {"evidence_packet": {"revision": "synthetic"}}),
            ("odin_loop_status", {"loop_id": LOOP}),
        ):
            self.assertFalse(bridge.call(name, supplied)["isError"])
            command = gateway.call_args.args[0]
            self.assertEqual(command["payload"]["project"], PROJECT)
            self.assertEqual(command["payload"]["session_id"], SESSION)
            if name != "odin_loop_status":
                self.assertEqual(command["operation_id"], MESSAGE)
            self.assertNotIn("operation_id", command["payload"])
        from jsonschema import ValidationError
        for forged in (
            {"project": LOOP}, {"session_id": PROMPT}, {"actor": "operator"}
        ):
            with self.assertRaises(ValidationError):
                bridge.call("odin_loop_claim", arguments | forged)

    def test_invalid_or_oversize_inbox_is_rejected_without_marking_emitted(self):
        for messages in (
            [self.message(content="x" * 16385)],
            [self.message(message_id="wrong")],
            [self.message(loop_id="wrong")],
            [self.message(content="")],
            [self.message()] * 17,
        ):
            with self.subTest(messages=len(messages)):
                bridge, _ = self.bridge(messages)
                server = MCPServer(bridge)
                initialize(server)
                with self.assertRaises(ToolFailure):
                    server.channel_notifications()
                self.assertEqual(server.emitted, set())

    def test_outage_keeps_event_eligible_and_wrong_receipt_is_rejected(self):
        bridge, gateway = self.bridge([self.message()])
        server = MCPServer(bridge)
        initialize(server)
        gateway.side_effect = ToolFailure("offline")
        with self.assertRaises(ToolFailure):
            server.channel_notifications()
        self.assertEqual(server.emitted, set())
        gateway.side_effect = lambda command: receipt(
            command | {"operation_id": MESSAGE}, {"messages": [self.message()]}
        )
        with self.assertRaises(ToolFailure):
            server.channel_notifications()
        self.assertEqual(server.emitted, set())
        gateway.side_effect = lambda command: receipt(command, {"messages": [self.message()]})
        self.assertEqual(len(server.channel_notifications()), 1)

    def test_stdout_contains_serialized_rpc_and_channel_frames(self):
        bridge, _ = self.bridge([self.message()])
        server = MCPServer(bridge)
        incoming_read, incoming_write = os.pipe()
        outgoing_read, outgoing_write = os.pipe()
        errors = []

        def run():
            try:
                with os.fdopen(incoming_read, "rb") as incoming, os.fdopen(outgoing_write, "wb") as outgoing:
                    server.serve(incoming, outgoing)
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        with os.fdopen(incoming_write, "wb", buffering=0) as incoming, os.fdopen(outgoing_read, "rb") as outgoing:
            incoming.write(
                (canonical({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "synthetic", "version": "1"}},
                }) + "\n").encode()
            )
            self.assertEqual(strict_loads(outgoing.readline().decode())["id"], 1)
            incoming.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            incoming.write(b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
            frames = [strict_loads(outgoing.readline().decode()) for _ in range(2)]
            self.assertEqual({frame.get("id") for frame in frames}, {2, None})
            self.assertEqual(
                next(frame for frame in frames if "id" not in frame)["params"]["meta"]["stage_id"],
                STAGE,
            )
        thread.join(timeout=4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])


class CompletionHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name)

    def event(self, **changes):
        return {
            "session_id": SESSION,
            "prompt_id": PROMPT,
            "hook_event_name": "Stop",
            "last_assistant_message": "Synthetic response\nODIN-COMPLETION-MARKER",
            "background_tasks": [],
            "session_crons": [],
            "stop_hook_active": False,
        } | changes

    def command(self, **changes):
        return hook.capture_command(self.event(**changes), project=PROJECT, session_id=SESSION)

    def test_extra_native_fields_are_ignored_without_losing_exact_final_text(self):
        command = self.command(scratchpad_dir="/ignored", new_native_field={"future": True})
        self.assertEqual(command, self.command())
        self.assertEqual(command["payload"]["last_assistant_message"], self.event()["last_assistant_message"])
        self.assertNotIn("scratchpad_dir", command["payload"])
        self.assertEqual(command["operation_id"], self.command()["operation_id"])

    def test_subagents_and_unrelated_events_never_capture_and_wrong_session_refused(self):
        for changes in (
            {"hook_event_name": "SubagentStop"},
            {"agent_id": "synthetic-child"},
            {"hook_event_name": "UserPromptSubmit"},
        ):
            self.assertIsNone(self.command(**changes))
        with self.assertRaises(PermissionError):
            self.command(session_id="22222222-2222-4222-8222-222222222222")

    def test_stop_failure_and_background_work_are_preserved(self):
        tasks = [{"id": "task1", "type": "subagent", "status": "running"}]
        self.assertEqual(self.command(background_tasks=tasks)["payload"]["background_tasks"], tasks)
        failed = self.command(hook_event_name="StopFailure", error="rate_limit", error_details="synthetic")
        self.assertEqual(failed["payload"]["error"], "rate_limit")
        self.assertNotEqual(failed["operation_id"], self.command()["operation_id"])

    def test_oversize_capture_is_rejected_never_truncated(self):
        with self.assertRaises(ValueError):
            self.command(last_assistant_message="🌍" * 65537)
        large = "🌍" * 20000
        self.assertEqual(
            self.command(last_assistant_message=large)["payload"]["last_assistant_message"], large
        )

    def test_spool_is_private_idempotent_and_survives_service_outage(self):
        command = self.command()
        path = hook.spool_capture(self.state, command)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(hook.spool_capture(self.state, command), path)
        offline = Mock(side_effect=ToolFailure("offline"))
        self.assertFalse(hook.deliver_capture(path, offline))
        self.assertTrue(path.exists())
        self.assertEqual(strict_loads(path.read_text()), command)
        delivered = []

        def submit(value):
            delivered.append(value)
            return receipt(value)

        result = hook.drain_spool(self.state, submit=submit, project=PROJECT)
        self.assertEqual(result, {"delivered": 1, "pending": 0, "invalid": 0})
        self.assertEqual(delivered, [command])
        self.assertFalse(path.exists())
        self.assertEqual(hook.drain_spool(self.state, submit=submit)["delivered"], 0)

    def test_uncertain_receipt_retains_same_operation_and_wrong_project_is_not_drained(self):
        command = self.command()
        path = hook.spool_capture(self.state, command)
        wrong = Mock(return_value=receipt(command | {"operation_id": LOOP}))
        self.assertFalse(hook.deliver_capture(path, wrong))
        refusal = Mock(return_value={"error": "denied"})
        self.assertFalse(hook.deliver_capture(path, refusal))
        submit = Mock(side_effect=receipt)
        result = hook.drain_spool(self.state, submit=submit, project=LOOP)
        self.assertEqual(result["pending"], 1)
        submit.assert_not_called()
        self.assertTrue(path.exists())

    def test_spool_rejects_symlink_and_public_directory(self):
        other = self.state / "other"
        other.mkdir(mode=0o700)
        (self.state / hook.SPOOL_NAME).symlink_to(other)
        with self.assertRaises(PermissionError):
            hook.spool_capture(self.state, self.command())
        (self.state / hook.SPOOL_NAME).unlink()
        (self.state / hook.SPOOL_NAME).mkdir(mode=0o755)
        (self.state / hook.SPOOL_NAME).chmod(0o755)  # deliberately public; umask-independent
        with self.assertRaises(PermissionError):
            hook.spool_capture(self.state, self.command())

    def test_invalid_pending_captures_do_not_starve_later_valid_completion(self):
        path = hook.spool_capture(self.state, self.command())
        os.utime(path, ns=(2, 2))
        for number in range(4):
            broken = path.parent / f"invalid-{number}.json"
            broken.write_text("{}")
            broken.chmod(0o600)
            os.utime(broken, ns=(1, 1))
        submit = Mock(side_effect=receipt)
        for _ in range(3):
            hook.drain_spool(self.state, submit=submit, project=PROJECT, limit=2)
        submit.assert_called_once_with(self.command())
        self.assertFalse(path.exists())
        self.assertEqual(len(list(path.parent.glob("invalid-*.json"))), 4)

    def test_native_hook_subprocess_roundtrip_and_replayed_payload(self):
        address = self.state / "executive.sock"
        captured = []
        errors = []
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(address))
        address.chmod(0o600)
        listener.listen(2)
        listener.settimeout(5)

        def server():
            try:
                for _ in range(2):
                    connection, _ = listener.accept()
                    with connection, connection.makefile("rb") as stream:
                        command = strict_loads(stream.readline().decode())["command"]
                        captured.append(command)
                        connection.sendall((canonical(receipt(command)) + "\n").encode())
            except Exception as error:
                errors.append(error)
            finally:
                listener.close()

        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        long_text = "Synthetic final response exceeds the MCP tool budget.\n" * 2000
        for _ in range(2):
            completed = subprocess.run(
                [sys.executable, "-m", "odin.executive_loop_hook", "--state", str(self.state),
                 "--project", PROJECT, "--session-id", SESSION],
                input=canonical(self.event(
                    scratchpad_dir="/future-field", last_assistant_message=long_text
                )).encode(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=os.environ | {"PYTHONPATH": str(ROOT / "python")},
                timeout=5,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, b"")
        worker.join(timeout=5)
        self.assertEqual(errors, [])
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[0], captured[1])
        self.assertEqual(captured[0]["payload"]["last_assistant_message"], long_text)
        self.assertEqual(list((self.state / hook.SPOOL_NAME).glob("*.json")), [])


class LoopRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.manifest = runtime.prepare(
            self.state, config_dir=self.root / "credentials", project=PROJECT,
            claude_binary=sys.executable, python_executable=sys.executable,
        )

    def activate(self):
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0),
        ):
            runtime.start(self.state, resume=True)

    def v3(self):
        runtime.enable_development(self.state)
        self.activate()

    def test_explicit_enablement_stages_without_changing_active_files_or_session(self):
        with self.assertRaises(PermissionError):
            runtime.enable_development_loop(self.state)
        self.v3()
        before, base = runtime._load(self.state)
        original_mcp = (base / "mcp.json").read_bytes()
        with runtime._lease(base / "runtime.lock"):
            staged = runtime.enable_development_loop(self.state)
        self.assertTrue(staged["pending_activation"])
        self.assertEqual(runtime._load(self.state)[0], before)
        self.assertEqual((base / "mcp.json").read_bytes(), original_mcp)
        spec = runtime.launch_spec(self.state, resume=True)
        self.assertEqual(spec["argv"][spec["argv"].index("--dangerously-load-development-channels") + 1], "server:odin")
        self.assertEqual(spec["argv"][spec["argv"].index("--resume") + 1], before["native_session_id"])
        prepared_mcp = json.loads(Path(spec["argv"][spec["argv"].index("--mcp-config") + 1]).read_text())
        self.assertEqual(prepared_mcp["mcpServers"]["odin"]["args"][-3:], ["--development-loop", "--session-id", before["native_session_id"]])
        settings = json.loads(Path(spec["argv"][spec["argv"].index("--settings") + 1]).read_text())
        self.assertEqual(set(settings), {"hooks"})
        self.assertEqual(set(settings["hooks"]), {"Stop", "StopFailure"})
        self.activate()
        current, _ = runtime._load(self.state)
        self.assertTrue(current["development_loop"])
        self.assertEqual(current["native_session_id"], self.manifest["native_session_id"])

    def test_interrupted_activation_keeps_old_config_loadable_and_retryable(self):
        self.v3()
        runtime.enable_development_loop(self.state)
        original_write = runtime._write

        def fail(path, name, value):
            if path.name == "manifest.json":
                raise OSError("synthetic interrupted activation")
            original_write(path, name, value)

        with patch.object(runtime, "_write", side_effect=fail), self.assertRaises(OSError):
            self.activate()
        self.assertNotIn("development_loop", runtime._load(self.state)[0])
        self.activate()
        self.assertTrue(runtime._load(self.state)[0]["development_loop"])

    def test_disable_is_staged_and_rotation_rebinds_hooks_to_new_identity(self):
        self.v3()
        runtime.enable_development_loop(self.state)
        self.activate()
        old = runtime._load(self.state)[0]
        rotated = runtime.new_session(self.state)
        new, base = runtime._load(self.state)
        self.assertNotEqual(old["native_session_id"], rotated["native_session_id"])
        self.assertEqual(runtime._loop_settings(new)["hooks"]["Stop"][0]["hooks"][0]["args"][-1], new["native_session_id"])
        runtime.enable_development_loop(self.state, enabled=False)
        self.assertTrue(runtime._load(self.state)[0]["development_loop"])
        self.assertNotIn("--dangerously-load-development-channels", runtime.launch_spec(self.state, resume=True)["argv"])
        self.activate()
        self.assertNotIn("development_loop", runtime._load(self.state)[0])


if __name__ == "__main__":
    unittest.main()
