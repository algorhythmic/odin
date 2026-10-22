"""Executive restart requests and the executive-supervise supervisor (ODIN-ADR-039).

The supervisor runs the ordinary start path against a synthetic Claude Code
binary (tests/fake_claude.py) and an in-process service gateway. This is
synthetic evidence; native clean exit, idle markers and the startup
confirmation are live acceptance.
"""
import fcntl
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from odin import executive_runtime as runtime
from odin import executive_supervision as supervision
from odin.contracts import ROOT, Contracts, identifier, strict_loads
from odin.coordination import Actor
from odin.executive_mcp import ExecutiveBridge
from odin.executive_service import prepare_project, submit_executive
from odin.executive_supervisor import (
    JOURNAL_FILE,
    LEASE_FILE,
    Supervisor,
    SupervisorRefused,
)
from odin.executive_turn_hook import read_marker, record
from odin.gateway import Gateway, GatewayContext, error_result
from odin.service import Service

OPERATOR = GatewayContext("terminal", Actor("operator", "local-operator"))


class GatewayClient:
    """The supervisor's service client, over an in-process gateway."""

    def __init__(self, test):
        self.test = test
        self.events = []
        self.on_status = None

    def _command(self, action, payload):
        command = {"schema_version": 1, "operation_id": identifier(), "action": action,
                   "payload": {"project": self.test.project} | payload}
        try:
            response = self.test.gateway.submit(command, context=OPERATOR)
        except Exception as error:  # noqa: BLE001 - mirrors the socket server
            response = error_result(error, "synthetic")
        if "error" in response:
            raise OSError(response.get("detail") or "service_refused")
        return response["result"]

    def status(self):
        if self.on_status:
            self.on_status()
        return self._command("executive_restart_status", {})

    def transition(self, request_id, state, **fields):
        return self._command("executive_restart_transition",
                             {"request_id": request_id, "state": state} | fields)["request"]

    def event(self, kind, **fields):
        self.events.append(kind)
        return self._command("executive_supervisor_event", {"kind": kind} | fields)


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.state = self.temp / "state"
        self.project = prepare_project(self.state)
        fake = self.temp / "claude"
        fake.write_text(f"#!{sys.executable}\n" + (ROOT / "tests" / "fake_claude.py").read_text())
        fake.chmod(0o700)
        self.log = self.temp / "launches.jsonl"
        self.plan = self.temp / "plan.json"
        runtime.prepare(self.state, config_dir=self.temp / "login", project=self.project,
                        claude_binary=str(fake), python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state):
            pass
        runtime.configure_execution_role(self.state, implementation_mode="delegated")
        with runtime._owned_runtime(self.state):
            pass
        self.manifest = runtime._load(self.state)[0]
        self.native = self.manifest["native_session_id"]
        self.service = Service(self.state)
        self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.bridge = ExecutiveBridge(self.project, self.send, development_loop=True, session_id=self.native)
        self.client = GatewayClient(self)
        self.quiet = open(os.devnull, "w")  # noqa: SIM115 - closed by cleanup
        self.addCleanup(self.quiet.close)
        environment = patch.dict(os.environ, {"FAKE_CLAUDE_LOG": str(self.log),
                                              "FAKE_CLAUDE_PLAN": str(self.plan),
                                              "FAKE_CLAUDE_MAX_SECONDS": "15",
                                              "PYTHONPATH": str(ROOT / "python")})
        environment.start()
        self.addCleanup(environment.stop)

    def send(self, command):
        try:
            return submit_executive(self.gateway, {"command": command}, self.project)
        except Exception as error:  # noqa: BLE001 - the socket server's mapping
            return error_result(error, "synthetic")

    def request(self, reason="load staged changes", operation=None):
        result = self.bridge.call("odin_executive_restart",
                                  {"reason": reason, "operation_id": operation or identifier()})
        return result

    def ok(self, result):
        self.assertFalse(result["isError"], result)
        return strict_loads(result["content"][0]["text"])["result"]

    def supervisor(self, plans, **options):
        self.plan.write_text(json.dumps(plans))
        defaults = {"client": self.client, "quiet_seconds": 0.3, "stop_timeout": 5,
                    "startup_window": 3, "poll_seconds": 0.05, "status_seconds": 0.05,
                    "sleep": lambda s: time.sleep(min(s, 0.05)), "output": self.quiet}
        return Supervisor(self.state, **(defaults | options))

    def launches(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def requests(self):
        return supervision.status(self.service.store, self.project)["requests"]

    def history(self, prefix):
        rows = self.service.store.db.execute("SELECT body FROM history").fetchall()
        return [strict_loads(row[0])["kind"] for row in rows
                if strict_loads(row[0])["kind"].startswith(prefix)]


class RestartRequestTests(Base):
    def test_request_is_recorded_and_idempotent(self):
        operation = identifier()
        first = self.ok(self.request(operation=operation))
        self.assertEqual(first["request"]["state"], "pending")
        self.assertEqual(first["request"]["session_id"], self.native)
        again = self.ok(self.request(operation=operation))
        self.assertEqual(again["request"]["id"], first["request"]["id"])
        self.assertEqual(len(self.requests()), 1)
        Contracts().validate("executive-restart", strict_loads(self.service.store.db.execute(
            "SELECT body FROM executive_restarts").fetchone()[0]))

    def test_one_open_request_at_a_time(self):
        self.ok(self.request())
        refused = self.request(reason="another")
        self.assertTrue(refused["isError"])
        self.assertIn("restart_request_pending", refused["content"][0]["text"])

    def test_unknown_intervention_outcome_refuses(self):
        self.ok(self.bridge.call("odin_intervention_begin", {
            "operation_id": identifier(), "purpose": "synthetic", "ttl_seconds": 60,
            "calls": [{"tool": "Bash", "input": {"command": "make check"}}]}))
        from odin.executive_intervention_hook import handle
        handle({"hook_event_name": "PreToolUse", "session_id": self.native, "tool_name": "Bash",
                "tool_use_id": "t1", "cwd": self.manifest["repository_root"],
                "tool_input": {"command": "make check"}},
               state=self.state, project=self.project, session=self.native, gateway=self.send)
        refused = self.request()
        self.assertIn("intervention_outcome_unknown", refused["content"][0]["text"])

    def test_claimed_or_ready_stage_refuses(self):
        for status in ("executive_claimed", "executive_ready"):
            self.service.store.db.execute(
                "CREATE TABLE IF NOT EXISTS development_loops(id TEXT PRIMARY KEY,project TEXT NOT NULL,"
                "active INTEGER NOT NULL,body TEXT NOT NULL)")
            self.service.store.db.execute("DELETE FROM development_loops")
            self.service.store.db.execute("INSERT INTO development_loops VALUES(?,?,1,?)", (
                identifier(), self.project, json.dumps({"status": status})))
            with self.subTest(status=status):
                refused = self.request()
                self.assertIn("loop_stage_active", refused["content"][0]["text"])
        self.service.store.db.execute("UPDATE development_loops SET body=?",
                                      (json.dumps({"status": "evaluator_running"}),))
        self.ok(self.request())

    def test_delegated_turns_do_not_block(self):
        with patch("odin.executive_intervention._busy", return_value=True):
            self.ok(self.request())

    def test_other_session_refused(self):
        bridge = ExecutiveBridge(self.project, self.send, development_loop=True,
                                 session_id="00000000-0000-4000-8000-000000000000")
        refused = bridge.call("odin_executive_restart", {"reason": "x", "operation_id": identifier()})
        self.assertIn("restart_session_not_current", refused["content"][0]["text"])

    def test_transitions_are_operator_only_and_ordered(self):
        request = self.ok(self.request())["request"]
        executive = GatewayContext("harness", Actor("coordinator", "fable-executive"), (self.project,))
        with self.assertRaises(PermissionError):
            self.gateway.submit({"schema_version": 1, "operation_id": identifier(),
                                 "action": "executive_restart_transition",
                                 "payload": {"project": self.project, "request_id": request["id"],
                                             "state": "stopping"}}, context=executive)
        with self.assertRaises(OSError) as caught:
            self.client.transition(request["id"], "restarted")
        self.assertEqual(str(caught.exception), "restart_transition_invalid")
        self.assertEqual(self.client.transition(request["id"], "stopping")["state"], "stopping")

    def test_unsafe_at_stop_time_refuses_the_request_with_a_notice(self):
        request = self.ok(self.request())["request"]
        with patch.object(supervision, "unsafe_reason", return_value="loop_stage_active"):
            moved = self.client.transition(request["id"], "stopping")
        self.assertEqual((moved["state"], moved["code"]), ("refused", "loop_stage_active"))
        notices = supervision.pending_notices(self.service.store, self.project)
        self.assertEqual([n["outcome"] for n in notices], ["refused"])


class TurnMarkerTests(Base):
    def test_marker_is_private_content_free_and_sequenced(self):
        record({"hook_event_name": "UserPromptSubmit", "session_id": self.native, "prompt": "secret-prompt"},
               state=self.state, session=self.native)
        marker = record({"hook_event_name": "Stop", "session_id": self.native,
                         "last_assistant_message": "secret-final", "background_tasks": [{"id": "a"}]},
                        state=self.state, session=self.native)
        path = self.state / "executive-pilot" / "turn-marker.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        raw = path.read_text()
        self.assertNotIn("secret", raw)
        self.assertEqual((marker["sequence"], marker["background_tasks"]), (2, 1))
        self.assertEqual(read_marker(self.state)["event"], "Stop")
        # A subagent's stop and another session are not the executive's turn end.
        self.assertIsNone(record({"hook_event_name": "Stop", "session_id": self.native, "agent_id": "x"},
                                 state=self.state, session=self.native))
        with self.assertRaises(ValueError):
            record({"hook_event_name": "Stop", "session_id": identifier()}, state=self.state, session=self.native)

    def test_supervised_launch_adds_only_marker_hooks(self):
        plain = runtime.launch_spec(self.state, resume=True)["argv"]
        supervised = runtime.launch_spec(self.state, resume=True, supervised=True)["argv"]
        self.assertEqual(len(plain), len(supervised))
        index = plain.index("--settings")
        self.assertEqual(plain[:index], supervised[:index])
        settings = json.loads(supervised[index + 1])
        Contracts().validate("executive-supervised-settings", settings)
        for event in ("SessionStart", "UserPromptSubmit", "Stop", "StopFailure", "SessionEnd"):
            self.assertIn("odin.executive_turn_hook", json.dumps(settings["hooks"][event]))
        for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            self.assertEqual(settings["hooks"][event], json.loads(plain[index + 1])["hooks"][event])


class SupervisorTests(Base):
    def test_request_idle_clean_stop_and_resume_with_staged_changes(self):
        # The executive asks mid-turn and the operator has staged a model change.
        def mid_turn():
            marker = read_marker(self.state)
            if marker and marker["event"] == "UserPromptSubmit" and not self.requests():
                self.ok(self.request())
                runtime.configure_model(self.state, model="claude-sonnet-5-5")
        self.client.on_status = mid_turn
        code = self.supervisor([[["start"], ["turn", 0.4], ["wait"]],
                                [["start"], ["sleep", 0.5], ["exit", 0]]]).run()
        self.assertEqual(code, 0)
        first, second = self.launches()
        self.assertEqual(first[first.index("--model") + 1], self.manifest["model"])
        self.assertEqual(second[second.index("--model") + 1], "claude-sonnet-5-5")
        # The first launch creates the session; the relaunch resumes the same one.
        self.assertEqual(first[first.index("--session-id") + 1], self.native)
        self.assertEqual(second[second.index("--resume") + 1], self.native)
        (request,) = self.requests()
        self.assertEqual(request["state"], "restarted")
        self.assertTrue(request["clean_exit_observed"])
        self.assertEqual(request["exit_code"], 143)
        self.assertEqual(set(request["timings"]), {"wait_idle_seconds", "stop_seconds", "relaunch_seconds"})
        self.assertEqual(self.history("executive.restart_"),
                         ["executive.restart_requested", "executive.restart_stopping",
                          "executive.restart_relaunching", "executive.restart_restarted"])
        # The executive gets a notice through the channel after the resume.
        inbox = self.gateway.submit({"schema_version": 1, "operation_id": identifier(), "action": "loop_inbox",
                                     "payload": {"project": self.project, "session_id": self.native,
                                                 "accept": ["assignment", "notice"]}},
                                    context=GatewayContext("harness", Actor("coordinator", "fable-executive"),
                                                           (self.project,)))
        (message,) = inbox["result"]["messages"]
        self.assertIn("restarted by the supervisor", message["content"])
        self.ok(self.bridge.call("odin_loop_ack", {"notice_id": message["notice_id"], "operation_id": identifier()}))
        self.assertEqual(supervision.pending_notices(self.service.store, self.project), [])
        self.assertEqual(self.client.events, ["supervision_started", "supervision_ended"])

    def test_waits_for_idle_and_never_stops_mid_turn(self):
        def mid_turn():
            marker = read_marker(self.state)
            if marker and marker["event"] == "UserPromptSubmit" and not self.requests():
                self.ok(self.request())
        self.client.on_status = mid_turn
        code = self.supervisor([[["start"], ["turn", 1.0], ["wait"]],
                                [["start"], ["exit", 0]]]).run()
        self.assertEqual(code, 0)
        (request,) = self.requests()
        # Requested at the turn's start, signalled only after its Stop marker
        # and the quiet window.
        self.assertGreaterEqual(request["timings"]["wait_idle_seconds"], 1.0)
        self.assertEqual(request["exit_code"], 143)

    def test_request_pending_at_supervisor_start(self):
        self.ok(self.request())
        code = self.supervisor([[["start"], ["sleep", 0.3], ["exit", 0]]]).run()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.launches()), 1)
        (request,) = self.requests()
        self.assertEqual(request["state"], "restarted")
        self.assertEqual(self.history("executive.restart_"),
                         ["executive.restart_requested", "executive.restart_stopping",
                          "executive.restart_relaunching", "executive.restart_restarted"])

    def test_operator_exit_without_request_ends_supervision(self):
        code = self.supervisor([[["start"], ["turn", 0.1], ["exit", 0]]]).run()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.launches()), 1)
        self.assertEqual(self.client.events, ["supervision_started", "supervision_ended"])
        journal = [json.loads(line)["kind"] for line in
                   (self.state / "executive-pilot" / JOURNAL_FILE).read_text().splitlines()]
        self.assertIn("operator_exit", journal)

    def test_crash_backoff_and_cap(self):
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            time.sleep(min(seconds, 0.02))
        code = self.supervisor([[["exit", 3]]], sleep=sleep).run()
        self.assertEqual(code, 3)
        self.assertEqual(len(self.launches()), 4)
        self.assertEqual([s for s in sleeps if s >= 10], [10, 30, 90])
        self.assertEqual(self.client.events.count("crash"), 4)
        self.assertEqual(self.client.events[-1], "crash_limit")
        self.assertIn("executive.supervisor_crash_limit", self.history("executive.supervisor_"))

    def test_crash_window_forgets_old_crashes(self):
        clock = [1000.0]
        def sleep(seconds):
            clock[0] += seconds if seconds >= 10 else 700
            time.sleep(0.01)
        # Crashes 700 s apart never reach the cap; the fifth launch exits cleanly.
        plans = [[["exit", 1]]] * 5 + [[["exit", 0]]]
        code = self.supervisor(plans, sleep=sleep, clock=lambda: clock[0]).run()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.launches()), 6)

    def test_lease_allows_one_supervisor(self):
        lease = self.state / "executive-pilot" / LEASE_FILE
        fd = os.open(lease, os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(SupervisorRefused) as caught:
            self.supervisor([[["exit", 0]]]).run()
        self.assertEqual(str(caught.exception), "supervisor_already_running")
        self.assertEqual(self.launches(), [])

    def test_refused_at_stop_time_keeps_the_session(self):
        def mid_turn():
            marker = read_marker(self.state)
            if marker and marker["event"] == "UserPromptSubmit" and not self.requests():
                self.ok(self.request())
        self.client.on_status = mid_turn
        with patch.object(supervision, "unsafe_reason", side_effect=lambda store, project: (
                "loop_stage_active" if store.db.execute(
                    "SELECT COUNT(*) FROM executive_restarts").fetchone()[0] else None)):
            code = self.supervisor([[["start"], ["turn", 0.2], ["sleep", 1.5], ["exit", 0]]]).run()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.launches()), 1)
        (request,) = self.requests()
        self.assertEqual((request["state"], request["code"]), ("refused", "loop_stage_active"))

    def test_stop_timeout_never_kills(self):
        def mid_turn():
            marker = read_marker(self.state)
            if marker and marker["event"] == "UserPromptSubmit" and not self.requests():
                self.ok(self.request())
        self.client.on_status = mid_turn
        code = self.supervisor([[["ignore_term"], ["start"], ["turn", 0.2], ["sleep", 2.0], ["exit", 0]]],
                               stop_timeout=0.5).run()
        # The child ran to its own exit status; nothing killed it.
        self.assertEqual(code, 0)
        (request,) = self.requests()
        self.assertEqual((request["state"], request["code"]), ("failed", "stop_timeout"))

    def test_relaunch_that_never_starts_waits_for_the_operator(self):
        self.ok(self.request())
        output = tempfile.TemporaryFile("w+")  # noqa: SIM115 - closed by cleanup
        self.addCleanup(output.close)
        code = self.supervisor([[["sleep", 0.6], ["exit", 0]]], startup_window=0.2, output=output).run()
        self.assertEqual(code, 0)
        self.assertIn("awaiting_operator_confirmation", self.client.events)
        output.seek(0)
        self.assertIn("never answers it", output.read())
        (request,) = self.requests()
        self.assertEqual((request["state"], request["code"]), ("failed", "relaunch_exited"))

    def test_development_profile_required(self):
        manifest_path = self.state / "executive-pilot" / "manifest.json"
        manifest = strict_loads(manifest_path.read_text())
        with (patch("odin.executive_runtime._load", return_value=(manifest | {"version": 2},
                                                                  manifest_path.parent)),
              self.assertRaises(SupervisorRefused) as caught):
            Supervisor(self.state, client=self.client)
        self.assertEqual(str(caught.exception), "supervisor_requires_development_profile")


if __name__ == "__main__":
    unittest.main()
