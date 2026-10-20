"""Real local service and MCP processes; no model, credentials or peer feeds."""

import os
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.contracts import ROOT, canonical, identifier, strict_loads
from odin.executive_service import prepare_project


class ExecutiveIntegrationTest(unittest.TestCase):
    def test_stdio_report_restart_and_scope_enforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            project = prepare_project(directory)
            other = prepare_project(directory)
            environment = os.environ | {"PYTHONPATH": str(ROOT / "python")}

            def start_service():
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "odin",
                        "--state",
                        directory,
                        "serve",
                        "--executive-project",
                        project,
                    ],
                    env=environment,
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
                return process

            def stop_service(process):
                process.send_signal(signal.SIGINT)
                try:
                    _, errors = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    raise
                self.assertEqual(process.returncode, 0, errors)
                self.assertFalse(Path(directory, "executive.sock").exists())

            def call(name, arguments, scope=project):
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
                        directory,
                        "--project",
                        scope,
                    ],
                    env=environment,
                    input="".join(canonical(item) + "\n" for item in requests),
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=True,
                )
                responses = [
                    strict_loads(line) for line in completed.stdout.splitlines()
                ]
                self.assertEqual(len(responses), 2)
                return responses[1]["result"]

            service = start_service()
            operation = identifier()
            try:
                self.assertFalse(call("odin_resume", {})["isError"])
                self.assertTrue(call("odin_resume", {}, other)["isError"])
                payload = {
                    "operation_id": operation,
                    "kind": "proposal",
                    "summary": "Synthetic improvement proposal",
                }
                first = call("odin_report", payload)
                self.assertFalse(first["isError"])
                self.assertEqual(first, call("odin_report", payload))
            finally:
                stop_service(service)
            service = start_service()
            try:
                result = call("odin_reports", {"limit": 20})
                self.assertFalse(result["isError"])
                reports = strict_loads(result["content"][0]["text"])["result"][
                    "reports"
                ]
                self.assertEqual([report["id"] for report in reports], [operation])
                self.assertFalse(reports[0]["applied"])
            finally:
                stop_service(service)


if __name__ == "__main__":
    unittest.main()
