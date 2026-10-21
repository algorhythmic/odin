import io
import os
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator
from odin.contracts import ROOT, canonical, strict_loads
from odin.executive_mcp import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    ExecutiveBridge,
    MCPServer,
    SocketGateway,
    ToolFailure,
)

PROJECT = "01K7M000000000000000000001"
OPERATION = "01K7M000000000000000000002"


def initialize(version="2025-06-18"):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "synthetic-client", "version": "1"},
        },
    }


def request(name, arguments=None, request_id=2):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


def receipt(command):
    return {
        "schema_version": 1,
        "operation_id": command["operation_id"],
        "label": "fake-backend evidence",
        "result": {"synthetic": True},
    }


class ExecutiveMCPTests(unittest.TestCase):
    def setUp(self):
        self.gateway = Mock(side_effect=receipt)
        self.bridge = ExecutiveBridge(PROJECT, self.gateway)
        self.server = MCPServer(self.bridge)
        self.server.handle(initialize())
        self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def test_initialization_negotiation_and_notification_boundary(self):
        server = MCPServer(self.bridge)
        self.assertEqual(server.handle(request("odin_resume"))["error"]["code"], -32000)
        result = server.handle(initialize("future-version"))["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["capabilities"], {"tools": {"listChanged": False}})
        self.assertEqual(server.handle(request("odin_resume"))["error"]["code"], -32000)
        server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertFalse(server.handle(request("odin_resume"))["result"]["isError"])
        self.assertEqual(server.handle(initialize())["error"]["code"], -32600)

    def test_tools_are_closed_scoped_and_do_not_include_operator_effects(self):
        result = self.server.handle(
            {"jsonrpc": "2.0", "id": "tools", "method": "tools/list"}
        )
        tools = result["result"]["tools"]
        self.assertEqual(
            {tool["name"] for tool in tools},
            {
                "odin_resume",
                "odin_memory_snapshot",
                "odin_read_evidence",
                "odin_report",
                "odin_reports",
                "odin_usage_status",
                "odin_context_status",
                "odin_delegation_session",
                "odin_delegation_assign",
                "odin_delegation_followup",
                "odin_delegation_status",
                "odin_delegation_result",
                "odin_delegation_close",
            },
        )
        for tool in tools:
            Draft202012Validator.check_schema(tool["inputSchema"])
            self.assertFalse(tool["inputSchema"]["additionalProperties"])
            self.assertFalse(
                {"project", "actor", "surface", "grant"}
                & tool["inputSchema"]["properties"].keys()
            )
        for name in (
            "odin_report",
            "odin_delegation_session",
            "odin_delegation_assign",
            "odin_delegation_followup",
            "odin_delegation_close",
        ):
            self.assertFalse(
                next(tool for tool in tools if tool["name"] == name)["annotations"][
                    "readOnlyHint"
                ]
            )
        for name in ("odin_delegation_status", "odin_delegation_result"):
            self.assertTrue(
                next(tool for tool in tools if tool["name"] == name)["annotations"][
                    "readOnlyHint"
                ]
            )

    def test_fixed_project_and_new_read_operation_each_time(self):
        self.server.handle(request("odin_resume"))
        self.server.handle(request("odin_resume"))
        first, second = [item.args[0] for item in self.gateway.call_args_list]
        self.assertEqual(first["payload"], {"project": PROJECT})
        self.assertNotEqual(first["operation_id"], second["operation_id"])
        self.assertEqual(first["action"], "resume")
        self.assertEqual(
            set(first), {"schema_version", "operation_id", "action", "payload"}
        )

    def test_all_tool_actions_and_bounded_arguments(self):
        cases = [
            ("odin_resume", {"detail_bytes": 0, "obligation_limit": 1}, "resume"),
            (
                "odin_memory_snapshot",
                {"limit": 2, "max_bytes": 2048},
                "memory_snapshot",
            ),
            (
                "odin_read_evidence",
                {"source_id": "fixture-source", "revision": 2},
                "memory_source_read",
            ),
            ("odin_reports", {"limit": 20}, "executive_reports"),
        ]
        for name, arguments, action in cases:
            with self.subTest(name=name):
                result = self.server.handle(request(name, arguments))["result"]
                self.assertFalse(result["isError"])
                command = self.gateway.call_args.args[0]
                self.assertEqual(command["action"], action)
                self.assertEqual(command["payload"], arguments | {"project": PROJECT})

    def test_spoofed_scope_authority_oversize_and_non_json_integers_refused(self):
        invalid = [
            ("odin_resume", {"project": "foreign-project"}),
            ("odin_resume", {"actor": {"role": "operator"}}),
            ("odin_resume", {"surface": "terminal"}),
            ("odin_resume", {"decision_limit": True}),
            ("odin_resume", {"obligation_limit": 33}),
            ("odin_resume", {"obligation_page_token": "bad"}),
            ("odin_memory_snapshot", {"max_bytes": 65537}),
            ("odin_memory_snapshot", {"at": {"known": None}}),
            ("odin_read_evidence", {"source_id": "secret", "revision": 0}),
            ("odin_read_evidence", {"source_id": "a" * 513, "revision": 1}),
            ("odin_reports", {"limit": 21}),
            (
                "odin_report",
                {"operation_id": OPERATION, "kind": "verified", "summary": "done"},
            ),
            (
                "odin_report",
                {
                    "operation_id": OPERATION + "\n",
                    "kind": "proposal",
                    "summary": "invalid ID",
                },
            ),
            (
                "odin_report",
                {"operation_id": OPERATION, "kind": "proposal", "summary": "x" * 8001},
            ),
            ("odin_report", {"kind": "proposal", "summary": "missing stable identity"}),
            ("answer_decision", {"response": "approved"}),
        ]
        for name, arguments in invalid:
            with self.subTest(name=name, arguments=str(arguments)[:100]):
                result = self.server.handle(request(name, arguments))
                self.assertEqual(result["error"]["code"], -32602)
        self.gateway.assert_not_called()

    def test_report_preserves_write_identity_without_accepting_actor(self):
        arguments = {
            "operation_id": OPERATION,
            "kind": "proposal",
            "summary": "Try a shorter briefing.",
        }
        for _ in range(2):
            result = self.server.handle(request("odin_report", arguments))["result"]
            self.assertFalse(result["isError"])
        for item in self.gateway.call_args_list:
            command = item.args[0]
            self.assertEqual(command["operation_id"], OPERATION)
            self.assertEqual(
                command["payload"],
                {
                    "project": PROJECT,
                    "kind": "proposal",
                    "summary": arguments["summary"],
                },
            )

    def test_report_transport_unknown_does_not_retry_or_leak_errors(self):
        self.gateway.side_effect = OSError("sensitive path /private/credential")
        arguments = {
            "operation_id": OPERATION,
            "kind": "reported_progress",
            "summary": "Testing.",
        }
        result = self.server.handle(request("odin_report", arguments))["result"]
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("same operation_id", text)
        self.assertNotIn("credential", text)
        self.gateway.assert_called_once()

    def test_access_denial_stale_or_foreign_evidence_have_no_data_leak(self):
        responses = [
            {"error": "PermissionError", "detail": "/secret/path"},
            {"error": "Conflict"},
        ]
        outcomes = []
        for response in responses:
            self.gateway.side_effect = None
            self.gateway.return_value = response
            outcomes.append(
                self.server.handle(
                    request(
                        "odin_read_evidence", {"source_id": "foreign", "revision": 1}
                    )
                )["result"]
            )
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertTrue(outcomes[0]["isError"])
        self.assertNotIn("secret", canonical(outcomes))

    def test_invalid_or_over_budget_service_receipt_never_forwarded(self):
        wrong = receipt({"operation_id": OPERATION})
        huge = lambda command: (
            receipt(command) | {"result": {"body": "x" * MAX_RESPONSE_BYTES}}
        )
        for side_effect in (lambda command: wrong, huge):
            self.gateway.side_effect = side_effect
            result = self.server.handle(request("odin_resume"))["result"]
            self.assertTrue(result["isError"])
            self.assertLess(len(canonical(result)), 300)

    def test_tool_notifications_cannot_mutate(self):
        message = request(
            "odin_report",
            {"operation_id": OPERATION, "kind": "proposal", "summary": "ignored"},
        )
        del message["id"]
        self.assertIsNone(self.server.handle(message))
        self.gateway.assert_not_called()

    def test_invalid_json_rpc_batches_ids_and_params(self):
        cases = [
            [],
            {"jsonrpc": "1.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "ping", "id": True},
        ]
        for message in cases:
            self.assertEqual(self.server.handle(message)["error"]["code"], -32600)
        self.assertEqual(
            self.server.handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": []}
            )["error"]["code"],
            -32602,
        )
        self.assertEqual(
            self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})[
                "error"
            ]["code"],
            -32601,
        )

    def test_stdio_frames_parse_errors_and_oversize_stop(self):
        malformed = [
            b'{"id":1,"id":2}\n',
            b'{"x":NaN}\n',
            b"\xff\n",
            b'{"id":"\\ud800"}\n',
        ]
        for frame in malformed:
            with self.subTest(frame=frame):
                outgoing = io.BytesIO()
                self.server.serve(io.BytesIO(frame), outgoing)
                response = strict_loads(outgoing.getvalue())
                self.assertEqual(response["error"]["code"], -32700)
        outgoing = io.BytesIO()
        valid_after = (canonical(request("odin_resume")) + "\n").encode()
        self.server.serve(
            io.BytesIO(b"x" * (MAX_REQUEST_BYTES + 1) + b"\n" + valid_after), outgoing
        )
        self.assertEqual(len(outgoing.getvalue().splitlines()), 1)
        self.gateway.assert_not_called()

    def test_native_subprocess_stdout_contains_only_mcp(self):
        with tempfile.TemporaryDirectory() as state:
            frames = [
                initialize(),
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            ]
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "odin.executive_mcp",
                    "--state",
                    state,
                    "--project",
                    PROJECT,
                ],
                input="".join(canonical(frame) + "\n" for frame in frames),
                text=True,
                capture_output=True,
                env=os.environ | {"PYTHONPATH": str(ROOT / "python")},
                check=True,
                timeout=10,
            )
        responses = [strict_loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([response["id"] for response in responses], [1, 2])
        self.assertEqual(len(responses[1]["result"]["tools"]), 13)
        self.assertEqual(completed.stderr, "")


class ExecutiveSocketTests(unittest.TestCase):
    def test_operator_socket_is_never_used_and_transport_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = SocketGateway(directory)
            client = Mock()
            client.__enter__ = Mock(return_value=client)
            client.__exit__ = Mock(return_value=False)
            stream = io.BytesIO(
                (canonical(receipt({"operation_id": OPERATION})) + "\n").encode()
            )
            client.makefile.return_value = stream
            client.getsockopt.return_value = struct.pack(
                "3i", os.getpid(), os.getuid(), os.getgid()
            )
            endpoint = Mock(st_mode=stat.S_IFSOCK | 0o600, st_uid=os.getuid())
            command = {"operation_id": OPERATION}
            with (
                patch.object(Path, "lstat", return_value=endpoint),
                patch.object(socket, "socket", return_value=client),
            ):
                result = gateway(command)
            self.assertEqual(result["operation_id"], OPERATION)
            client.connect.assert_called_once_with(
                str(Path(directory) / "executive.sock")
            )
            wire = strict_loads(client.sendall.call_args.args[0])
            self.assertEqual(wire, {"command": command})

    def test_wrong_peer_or_unbounded_response_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = SocketGateway(directory)
            endpoint = Mock(st_mode=stat.S_IFSOCK | 0o600, st_uid=os.getuid())
            cases = [
                (os.getuid() + 1, b"{}\n"),
                (os.getuid(), b"{}"),
                (os.getuid(), b"x" * (MAX_RESPONSE_BYTES + 1) + b"\n"),
                (os.getuid(), b'{"bad":1,"bad":2}\n'),
            ]
            for uid, raw in cases:
                with self.subTest(uid=uid, size=len(raw)):
                    client = Mock()
                    client.__enter__ = Mock(return_value=client)
                    client.__exit__ = Mock(return_value=False)
                    client.makefile.return_value = io.BytesIO(raw)
                    client.getsockopt.return_value = struct.pack(
                        "3i", os.getpid(), uid, os.getgid()
                    )
                    with (
                        patch.object(Path, "lstat", return_value=endpoint),
                        patch.object(socket, "socket", return_value=client),
                        self.assertRaises(ToolFailure),
                    ):
                        gateway({"operation_id": OPERATION})
                    if uid != os.getuid():
                        client.sendall.assert_not_called()

    def test_public_symlink_and_non_socket_endpoints_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "executive.sock"
            path.write_text("not a socket")
            gateway = SocketGateway(directory)
            with (
                self.assertRaises(ToolFailure),
                patch.object(socket, "socket") as client,
            ):
                gateway({})
            client.assert_not_called()
            path.unlink()
            path.symlink_to(Path(directory) / "service.sock")
            with (
                self.assertRaises(ToolFailure),
                patch.object(socket, "socket") as client,
            ):
                gateway({})
            client.assert_not_called()
            path.unlink()
            os.chmod(directory, 0o755)
            with (
                self.assertRaises(ToolFailure),
                patch.object(socket, "socket") as client,
            ):
                gateway({})
            client.assert_not_called()

    def test_repository_state_and_invalid_project_refused(self):
        with self.assertRaises(ValueError):
            SocketGateway(ROOT / "state")
        for project in (None, "other", PROJECT + "/path"):
            with self.subTest(project=project), self.assertRaises(ValueError):
                ExecutiveBridge(project, Mock())


if __name__ == "__main__":
    unittest.main()
