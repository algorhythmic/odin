"""Operator CLI coverage with a real local service and no native model calls."""

import io
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from odin import __main__ as cli
from odin import executive_runtime as runtime
from odin.contracts import ROOT, canonical, identifier, strict_loads
from odin.executive_service import prepare_project
from odin.development_loop import DevelopmentLoop
from odin.store import Store

SESSION = "11111111-1111-4111-8111-111111111111"


class DevelopmentCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.project = prepare_project(self.state)
        self.environment = os.environ | {"PYTHONPATH": str(ROOT / "python")}
        self.service = None
        self.addCleanup(self.stop_service)
        self.request = self.root / "start.json"
        self.payload = {
            "project": self.project,
            "session_id": SESSION,
            "goal": "Exercise the operator CLI using synthetic evidence.",
            "evidence_packet": {"fixture": "no live model"},
            "max_rounds": 2,
        }
        self.request.write_text(canonical(self.payload))

    def run_cli(self, *arguments, expected=0):
        completed = subprocess.run(
            [sys.executable, "-m", "odin", "--state", str(self.state), *arguments],
            env=self.environment, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(
            completed.returncode, expected, completed.stdout + completed.stderr
        )
        return completed

    def result(self, *arguments):
        completed = self.run_cli(*arguments)
        self.assertEqual(completed.stderr, "")
        receipt = strict_loads(completed.stdout)
        self.assertNotIn("error", receipt)
        return receipt

    def start_service(self):
        self.service = subprocess.Popen(
            [sys.executable, "-m", "odin", "--state", str(self.state), "serve"],
            env=self.environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=0,
        )
        with selectors.DefaultSelector() as selector:
            selector.register(self.service.stdout, selectors.EVENT_READ)
            if not selector.select(15):
                self.fail("synthetic service did not become ready")
        first = self.service.stdout.readline().decode()
        if not first.startswith("Fixture service ready:"):
            self.service.kill()
            _, errors = self.service.communicate()
            self.service = None
            self.fail("synthetic service startup failed: " + first + errors.decode())

    def stop_service(self):
        if self.service is None:
            return
        process, self.service = self.service, None
        process.send_signal(signal.SIGTERM)
        try:
            _, errors = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        self.assertEqual(process.returncode, 0, errors.decode())
        self.assertEqual(errors, b"")

    def test_usage_metadata_commands_use_the_running_service(self):
        self.start_service()
        source = self.root / 'usage.jsonl'
        source.write_text(canonical({
            'type': 'assistant', 'sessionId': SESSION,
            'timestamp': '2026-10-20T01:00:00Z',
            'message': {'id': 'synthetic-request', 'model': 'haiku',
                        'content': 'not retained', 'usage': {
                            'input_tokens': 3, 'cache_read_input_tokens': 2,
                            'cache_creation_input_tokens': 0, 'output_tokens': 1}}
        }) + '\n')
        args = ('usage-collect', '--project', self.project, '--usage-provider', 'claude',
                '--native-session', SESSION, '--source-file', str(source))
        self.assertEqual(self.result(*args)['result']['outcomes'], {'inserted': 1})
        self.assertEqual(self.result(*args)['result']['outcomes'], {'duplicate': 1})
        self.request.write_text(canonical({'project': self.project, 'policy': {
            'mode': 'hold', 'limits': {'max_requests': 1}}}))
        self.result('usage-configure', '--request', str(self.request))
        status = self.result('usage-status', '--project', self.project)['result']
        self.assertEqual(status['usage']['request_count'], 1)
        self.assertEqual(status['admission']['decision'], 'hold')
        self.assertIn('requests:threshold', status['admission']['reasons'])
        checkpoint = {'revision': 1, 'branch': 'codex/synthetic', 'worktree': str(self.root),
            'artifact_refs': [], 'open_obligations': [], 'pending_reviews': [],
            'operation_ids': [], 'next_action': 'review evidence', 'summary': 'synthetic'}
        self.request.write_text(canonical({'project': self.project, 'session_id': SESSION,
                                          'checkpoint': checkpoint}))
        self.result('context-checkpoint', '--request', str(self.request))
        view = self.result('context-status', '--project', self.project, '--native-session', SESSION)
        self.assertEqual(view['result']['checkpoint']['next_action'], 'review evidence')

    def start_loop(self, operation_id=None):
        arguments = ["development-start", "--request", str(self.request)]
        if operation_id:
            arguments.extend(["--operation-id", operation_id])
        return self.result(*arguments)

    def status(self, loop_id=None):
        arguments = ["development-status", "--project", self.project]
        if loop_id:
            arguments.extend(["--loop", loop_id])
        return self.result(*arguments)["result"]

    def test_configure_writes_private_validated_configuration_without_launch(self):
        workspace = self.root / "workspace"
        profile = self.root / "evaluator-profile"
        workspace.mkdir(mode=0o700)
        profile.mkdir(mode=0o700)
        config = {
            "schema_version": 1,
            "enabled": False,
            "harness": "codex",
            "binary": sys.executable,
            "workspace": str(workspace),
            "config_dir": str(profile),
            "model": "synthetic-no-model-call",
            "timeout_seconds": 30,
        }
        request = self.root / "config.json"
        request.write_text(canonical(config))
        result = self.result("development-configure", "--request", str(request))
        path = self.state / "development-evaluator.json"
        self.assertEqual(result["written"], str(path))
        self.assertIn("restart serve", result["activation"])
        self.assertEqual(strict_loads(path.read_text()), config)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertFalse((self.state / "development-evaluator").exists())
        self.start_service()
        status = self.status()
        self.assertFalse(status["evaluator_configured"])
        self.assertEqual(status["loops"], [])

    def test_start_status_control_and_repeated_operation_identity(self):
        self.start_service()
        operation_id = identifier()
        first = self.start_loop(operation_id)
        self.assertEqual(first["operation_id"], operation_id)
        self.assertEqual(first, self.start_loop(operation_id))
        loop_id = first["result"]["loop"]["id"]
        status = self.status(loop_id)
        self.assertEqual(len(status["loops"]), 1)
        self.assertEqual(status["loops"][0]["status"], "evaluator_pending")
        self.assertFalse(status["evaluator_configured"])
        self.assertEqual(
            status["verification"], "model_attributed_not_canonical_acceptance"
        )
        for action, expected in (
            ("pause", "paused"), ("resume", "evaluator_pending"), ("stop", "stopped")
        ):
            arguments = [
                "development-control", "--project", self.project,
                "--loop", loop_id, "--control", action,
                "--operation-id", identifier(),
            ]
            changed = self.result(*arguments)
            self.assertEqual(changed["result"]["loop"]["status"], expected)
            self.assertEqual(changed, self.result(*arguments))
            self.assertEqual(self.status(loop_id)["loops"][0]["status"], expected)
        self.assertEqual(len(self.status()["loops"]), 1)

    def test_lost_start_reply_preserves_generated_identity_for_identical_retry(self):
        self.start_service()
        original = cli._socket_command
        applied = []

        def lose_reply(address, message):
            # The real service commits first; only its reply is deliberately lost.
            receipt = original(address, message)
            applied.append((message, receipt))
            raise OSError("synthetic transport loss after committed operation")

        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", [
                "odin", "--state", str(self.state), "development-start",
                "--request", str(self.request),
            ]),
            patch.object(cli, "_socket_command", side_effect=lose_reply),
            redirect_stdout(output),
            redirect_stderr(errors),
            self.assertRaises(SystemExit) as stopped,
        ):
            cli.main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(len(applied), 1)
        match = re.search(r"--operation-id ([0-7][0-9A-HJKMNP-TV-Z]{25})", errors.getvalue())
        self.assertIsNotNone(match, errors.getvalue())
        operation_id = match.group(1)
        self.assertEqual(operation_id, applied[0][0]["command"]["operation_id"])
        retried = self.start_loop(operation_id)
        self.assertEqual(retried, applied[0][1])
        self.assertEqual(len(self.status()["loops"]), 1)

        # An operation identity cannot silently authorize changed arguments.
        self.request.write_text(canonical(self.payload | {"goal": "Different work"}))
        conflict = self.run_cli(
            "development-start", "--request", str(self.request),
            "--operation-id", operation_id, expected=1,
        )
        self.assertIn("error", strict_loads(conflict.stdout))
        self.assertEqual(len(self.status()["loops"]), 1)

    def test_unavailable_service_reports_explicit_operation_id(self):
        operation_id = identifier()
        failed = self.run_cli(
            "development-status", "--project", self.project,
            "--operation-id", operation_id, expected=2,
        )
        self.assertEqual(failed.stdout, "")
        self.assertIn("outcome unavailable", failed.stderr)
        self.assertIn("--operation-id " + operation_id, failed.stderr)
        self.assertNotIn("Traceback", failed.stderr)

    def test_continue_after_committed_reply_loss_and_service_restart(self):
        # A completed evaluator explicitly asks for intervention. No native
        # model runs in this test; the actual CLI/service path handles the reply.
        with Store(self.state) as store:
            loops = DevelopmentLoop(store)
            initial = loops.start(
                self.project, "Retain the bounded objective", SESSION, identifier(),
                max_rounds=2,
            )
            loop_id, job = initial["loop"]["id"], initial["job"]
            loops.mark_evaluator_started(
                loop_id, job["id"], job["packet_digest"], identifier()
            )
            held = loops.accept_evaluation(
                loop_id, job["id"], job["packet_digest"],
                {"decision": "needs_operator", "assessment": "Reload required",
                 "findings": [], "next_prompt": "", "evidence_refs": []},
                identifier(),
            )
        request = self.root / "continue.json"
        payload = {
            "project": self.project, "loop_id": loop_id,
            "expected_revision": held["loop"]["revision"],
            "response": "The synthetic service has been reloaded.",
            "evidence_packet": {"synthetic": True},
        }
        request.write_text(canonical(payload))
        self.start_service()
        original = cli._socket_command
        applied = []

        def lose_reply(address, message):
            receipt = original(address, message)
            applied.append((message, receipt))
            raise OSError("synthetic lost continuation reply after commit")

        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", [
                "odin", "--state", str(self.state), "development-continue",
                "--request", str(request),
            ]),
            patch.object(cli, "_socket_command", side_effect=lose_reply),
            redirect_stdout(output), redirect_stderr(errors),
            self.assertRaises(SystemExit) as stopped,
        ):
            cli.main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(len(applied), 1)
        self.assertNotIn("error", applied[0][1])
        match = re.search(r"--operation-id ([0-7][0-9A-HJKMNP-TV-Z]{25})", errors.getvalue())
        self.assertIsNotNone(match, errors.getvalue())
        operation = match.group(1)
        self.assertEqual(applied[0][0]["command"]["action"], "loop_continue")
        self.stop_service()
        self.start_service()
        repeated = self.result(
            "development-continue", "--request", str(request),
            "--operation-id", operation,
        )
        self.assertEqual(repeated, applied[0][1])
        loop = self.status(loop_id)["loops"][0]
        self.assertEqual(loop["status"], "evaluator_pending")
        self.assertEqual(loop["round"], 0)
        self.assertEqual(loop["max_rounds"], 2)
        self.assertNotEqual(loop["current_job"], job["id"])
        self.assertEqual(repeated["result"]["job"]["packet"]["operator_response"]["response"], payload["response"])
        request.write_text(canonical(payload | {"response": "Different intervention"}))
        refused = self.run_cli(
            "development-continue", "--request", str(request),
            "--operation-id", operation, expected=1,
        )
        self.assertIn("error", strict_loads(refused.stdout))
        self.assertEqual(self.status(loop_id)["loops"][0]["current_job"], loop["current_job"])

    def test_required_arguments_fail_before_service_access(self):
        for arguments in (
            ["development-configure"],
            ["development-start"],
            ["development-continue"],
            ["development-status"],
            ["development-control", "--project", self.project],
            ["development-control", "--project", self.project, "--loop", identifier()],
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments, expected=2)
                self.assertIn("requires" if arguments[0] != "development-status" else "require", result.stderr)
                self.assertNotIn("outcome unavailable", result.stderr)

    def test_channel_enable_cli_stages_same_native_session_and_unrestricted_profile(self):
        original = runtime.prepare(
            self.state, config_dir=self.root / "executive-profile",
            project=self.project, claude_binary=sys.executable,
            python_executable=sys.executable,
        )
        rejected = self.run_cli("executive-enable-development-loop", expected=2)
        self.assertIn("active v3 MCP profile", rejected.stderr)
        runtime.enable_development(self.state)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0) as foreground,
        ):
            runtime.start(self.state, resume=True)
        foreground.assert_called_once()
        before, _ = runtime._load(self.state)
        staged = self.result("executive-enable-development-loop")
        self.assertTrue(staged["pending_activation"])
        self.assertEqual(staged["native_session_id"], original["native_session_id"])
        self.assertEqual(runtime._load(self.state)[0], before)
        spec = runtime.launch_spec(self.state, resume=True)
        argv = spec["argv"]
        self.assertEqual(argv[argv.index("--resume") + 1], original["native_session_id"])
        self.assertEqual(argv[argv.index("--tools") + 1], "default")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "bypassPermissions")
        self.assertEqual(
            argv[argv.index("--dangerously-load-development-channels") + 1], "server:odin"
        )
        settings = strict_loads(Path(argv[argv.index("--settings") + 1]).read_text())
        self.assertEqual(set(settings), {"hooks"})
        self.assertEqual(set(settings["hooks"]), {"Stop", "StopFailure"})
        self.assertEqual(spec["cwd"], str(ROOT))
        self.assertEqual(spec["env"]["HOME"], os.environ["HOME"])
        for flag in (
            "--restricted", "--allowedTools", "--disallowedTools",
            "--setting-sources", "--strict-mcp-config", "--print", "--fork-session",
        ):
            self.assertNotIn(flag, argv)

        # Public help can check additive settings, but not the hidden channel
        # switch, account policy or actual notification delivery.
        for help_text, missing in (
            (" ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS), ["--settings"]),
            (" ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS) + " --settings", []),
        ):
            outputs = [
                subprocess.CompletedProcess([], 0, stdout="synthetic CLI\n"),
                subprocess.CompletedProcess([], 0, stdout=help_text),
            ]
            with patch.object(runtime.subprocess, "run", side_effect=outputs):
                self.assertEqual(runtime.probe(self.state)["missing_flags"], missing)


if __name__ == "__main__":
    unittest.main()
