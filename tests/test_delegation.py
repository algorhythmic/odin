"""Local delegation sessions: synthetic harness binaries, real detached runners.

No model, credential or network is used. The fake harness scripts imitate the
`claude -p --output-format json` and `codex exec --json` output shapes only.
"""

import os
import signal
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from odin.contracts import canonical, identifier, strict_loads
from odin.delegation import (
    CAPABILITIES,
    DelegationRefused,
    default_config,
    write_config,
)
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway
from odin.service import Service

FAKE_CLAUDE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys, time
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("9.9.9 (fake claude)"); sys.exit(0)
    def opt(name):
        return argv[argv.index(name) + 1] if name in argv else None
    prompt = opt("-p")
    session = opt("--session-id") or opt("--resume")
    if "SLEEP" in prompt:
        time.sleep(float(prompt.split("SLEEP")[1].split()[0]))
    if "CRASH" in prompt:
        sys.exit(3)
    if "REFRESH" in prompt:  # imitate a credential refresh by the harness
        open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], ".credentials.json"), "w").write('{"refreshed": true}')
    if "NOJSON" in prompt:
        print("not json"); sys.exit(0)
    body = {
        "session_id": session, "result": "worker says: " + prompt,
        "total_cost_usd": 0.0125, "num_turns": 2, "is_error": False,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "permission_denials": [],
        "mode": opt("--permission-mode"), "model": opt("--model"),
        "max_turns": opt("--max-turns"), "budget": opt("--max-budget-usd"),
        "system": opt("--append-system-prompt"),
        "config_dir": os.environ.get("CLAUDE_CONFIG_DIR"), "cwd": os.getcwd(),
    }
    print(json.dumps(body))
    """
)

FAKE_CODEX = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, sys
    argv = sys.argv[1:]
    if argv == ["--version"]:
        print("codex-cli 0.0.0-fake"); sys.exit(0)
    resume = argv[1] == "resume"
    thread = argv[2] if resume else "11111111-2222-4333-8444-555555555555"
    prompt = argv[-1]
    out = argv[argv.index("-o") + 1] if "-o" in argv else None
    print(json.dumps({"type": "thread.started", "thread_id": thread}))
    print(json.dumps({"type": "turn.started"}))
    text = "codex says: " + prompt[-40:]
    if "FAIL" in prompt:
        print(json.dumps({"type": "turn.failed", "error": "synthetic provider failure"}))
        sys.exit(1)
    print(json.dumps({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": text}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 3}}))
    if out:
        open(out, "w").write(text)
    """
)


def _alive(pid):
    try:
        with open(f"/proc/{pid}/stat") as handle:
            return handle.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def _script(path, body):
    path.write_text(body)
    path.chmod(0o700)
    return path


class DelegationHarness:
    """One isolated state directory with a configured fake harness pair."""

    def __init__(self, root):
        self.root = Path(root)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.workspace_root = self.root / "workspaces"
        self.workspace_root.mkdir(mode=0o700)
        self.workspace = self.workspace_root / "one"
        self.workspace.mkdir(mode=0o700)
        self.config_dir = self.root / "claude-login"
        self.config_dir.mkdir(mode=0o700)
        (self.config_dir / ".credentials.json").write_text("{}")
        (self.config_dir / ".credentials.json").chmod(0o600)
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir(mode=0o700)
        self.claude = _script(self.root / "fake-claude", FAKE_CLAUDE)
        self.codex = _script(self.root / "fake-codex", FAKE_CODEX)
        self.write_config()
        self.project = prepare_project(self.state)
        self.service = None
        self.gateway = None
        self.open()

    def write_config(self, **extra):
        write_config(
            self.state,
            default_config(
                claude_config_dir=self.config_dir,
                workspace_roots=[self.workspace_root],
                claude_binary=self.claude,
                codex_binary=self.codex,
                codex_home=self.codex_home,
                turn_timeout_seconds=30,
                **extra,
            ),
        )

    def open(self):
        from odin.delegation import load_config

        self.service = Service(self.state)
        self.service.recover()
        self.gateway = Gateway(self.service, delegation_config=load_config(self.state))

    def close(self):
        if self.service is not None:
            self.service.close()
            self.service = None

    def restart(self):
        self.close()
        self.open()

    def call(self, action, arguments, operation=None, *, project=None, scope=None):
        operation = operation or arguments.get("operation_id") or identifier()
        arguments = dict(arguments) | {"project": project or self.project}
        if action in (
            "delegation_session",
            "delegation_assign",
            "delegation_followup",
            "delegation_close",
        ):
            arguments.setdefault("operation_id", operation)
        request = {
            "command": {
                "schema_version": 1,
                "operation_id": operation,
                "action": action,
                "payload": arguments,
            }
        }
        return submit_executive(
            self.gateway, request, scope or project or self.project
        )["result"]

    def wait(self, predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.gateway.delegation.tick()
            value = predicate()
            if value:
                return value
            time.sleep(0.1)
        raise AssertionError("timed out waiting for delegation state")

    def assignment_state(self, assignment):
        view = self.call("delegation_status", {"assignment_id": assignment})
        return next(s for s in view["sessions"] if s["assignments"])["assignments"][0]


class DelegationCycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.harness = DelegationHarness(self.temporary.name)
        self.addCleanup(self.harness.close)

    def open_session(self, harness="claude-code", **extra):
        return self.harness.call(
            "delegation_session",
            {
                "action": "create",
                "harness": harness,
                "workspace": str(self.harness.workspace),
                "briefing": "You are a synthetic worker.",
                "model": "fake-model",
                "budget_usd": 5,
            }
            | extra,
        )

    def assign(self, session, instructions="do the thing", **extra):
        return self.harness.call(
            "delegation_assign",
            {
                "session_id": session,
                "objective": "Synthetic objective",
                "criteria": [{"id": "c1", "text": "worker reports"}],
                "scope": "synthetic scope",
                "output_contract": "final text",
                "instructions": instructions,
                "limits": {"iterations": 3, "budget_usd": 0.5},
            }
            | extra,
        )

    def test_full_cycle_persists_resumes_and_closes(self):
        h = self.harness
        opened = self.open_session()
        session = opened["session"]["id"]
        self.assertEqual(opened["session"]["state"], "idle")
        self.assertEqual(opened["session"]["adapter"], "claude-code-print")
        self.assertTrue(opened["session"]["native_session_id"])
        self.assertEqual(opened["binding"]["state"], "active")
        self.assertEqual(
            h.service.store.get(h.project)["interface_decision_owner"], session
        )
        assigned = self.assign(session)
        self.assertEqual(assigned["state"], "dispatched")
        self.assertEqual(assigned["limit_enforcement"]["budget"], "harness_option")
        commitment = h.service.store.get(assigned["commitment"])
        self.assertEqual(commitment["state"], "open")
        self.assertEqual(commitment["owner"], session)
        # The resume view shows the delegated work as an open obligation.
        resume = h.call("resume", {})
        self.assertEqual(
            [c["id"] for c in resume["commitments"]], [assigned["commitment"]]
        )
        self.assertEqual(resume["assignments"][0]["state"], "dispatched")

        launched = h.gateway.delegation.launch_pending()
        self.assertEqual(launched, [assigned["turn"]])
        self.assertEqual(h.service.store.get(session)["state"], "active")
        self.assertEqual(h.service.store.get(assigned["assignment"])["state"], "active")
        state = h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])
                if h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "returned"
                else None
            )
        )
        turn = state["turns"][0]
        self.assertEqual(turn["result"]["cost_usd"], 0.0125)
        self.assertEqual(
            turn["result"]["native_session_id"], opened["session"]["native_session_id"]
        )
        self.assertEqual(h.service.store.get(session)["state"], "idle")
        self.assertEqual(state["state"], "active")  # Return never completes work.
        self.assertEqual(state["commitment_state"], "open")
        # The resume view now carries the outstanding delegated return itself.
        resume = h.call("resume", {})
        self.assertEqual(resume["delegation"]["running_turn_count"], 0)
        self.assertEqual([s["id"] for s in resume["delegation"]["sessions"]], [session])
        self.assertEqual(
            resume["delegation"]["awaiting_executive"],
            [
                {
                    "assignment": assigned["assignment"],
                    "commitment": assigned["commitment"],
                    "session": session,
                    "turn": turn["id"],
                    "state": "returned",
                    "finished_at": turn["finished_at"],
                    "failure": None,
                }
            ],
        )
        self.assertEqual(resume["recommended_next_action"], "review a delegated return")

        result = h.call("delegation_result", {"assignment_id": assigned["assignment"]})
        self.assertTrue(result["available"])
        self.assertIn("worker says: do the thing", result["final_text"])
        spec = strict_loads(Path(result["transcript_paths"]["spec.json"]).read_text())
        argv = spec["argv"]
        self.assertEqual(
            argv[argv.index("--session-id") + 1], opened["session"]["native_session_id"]
        )
        self.assertEqual(argv[argv.index("--max-turns") + 1], "3")
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "0.5")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(spec["env"], {"CLAUDE_CONFIG_DIR": str(h.config_dir)})
        self.assertEqual(spec["cwd"], str(h.workspace))
        stdout = strict_loads(
            Path(result["transcript_paths"]["stdout.log"]).read_text()
        )
        self.assertEqual(stdout["config_dir"], str(h.config_dir))
        self.assertEqual(stdout["system"], "You are a synthetic worker.")

        # Restart the service: records, turns and the session survive.
        h.restart()
        view = h.call("delegation_status", {"session_id": session})["sessions"][0]
        self.assertEqual(view["turn_count"], 1)
        self.assertEqual(view["session"]["state"], "idle")
        self.assertEqual(view["cost_usd_known"], 0.0125)
        # Follow-up resumes the same native conversation.
        followed = h.call(
            "delegation_followup",
            {
                "session_id": session,
                "assignment_id": assigned["assignment"],
                "message": "and more",
            },
        )
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][1]["state"]
                == "returned"
            )
        )
        spec = strict_loads(
            (
                h.state / "delegations" / session / followed["turn"] / "spec.json"
            ).read_text()
        )
        self.assertEqual(
            spec["argv"][spec["argv"].index("--resume") + 1],
            opened["session"]["native_session_id"],
        )
        self.assertNotIn("--session-id", spec["argv"])

        # Acceptance is explicit, attributed and requires evidence per criterion.
        with self.assertRaises(DelegationRefused):
            h.call(
                "delegation_close",
                {
                    "assignment_id": assigned["assignment"],
                    "disposition": "accepted",
                    "evidence": {},
                },
            )
        closed = h.call(
            "delegation_close",
            {
                "assignment_id": assigned["assignment"],
                "disposition": "accepted",
                "evidence": {"c1": ["turn:" + assigned["turn"]]},
                "reason": "executive inspected the report",
            },
        )
        self.assertEqual(closed["commitment_state"], "closed")
        self.assertEqual(closed["acceptance"], "executive_attributed_not_saga_verified")
        commitment = h.service.store.get(assigned["commitment"])
        self.assertEqual(commitment["state"], "closed")
        self.assertTrue(commitment["criteria"][0]["met"])
        self.assertEqual(h.call("resume", {})["commitments"], [])
        kinds = [
            strict_loads(row[0])["kind"]
            for row in h.service.store.db.execute(
                "SELECT body FROM history ORDER BY seq"
            )
        ]
        for kind in (
            "delegation.session",
            "delegation.assigned",
            "delegation.turn",
            "delegation.result",
            "delegation.closed",
        ):
            self.assertIn(kind, kinds)

    def test_one_active_session_per_project_and_stop_retires(self):
        h = self.harness
        first = self.open_session()["session"]["id"]
        with self.assertRaises(DelegationRefused) as refused:
            self.open_session()
        self.assertEqual(str(refused.exception), "project_already_has_active_session")
        assigned = self.assign(first, "SLEEP 8 then finish")
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "running"
            )
        )
        stopped = h.call(
            "delegation_session",
            {"action": "stop", "session_id": first, "reason": "operator"},
        )
        self.assertIn(stopped["session"]["state"], ("retiring", "retired"))
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                in ("interrupted", "failed")
            )
        )
        self.assertEqual(h.service.store.get(first)["state"], "retired")
        self.assertIsNone(h.service.store.get(h.project)["interface_decision_owner"])
        with self.assertRaises(DelegationRefused) as refused:
            h.call("delegation_session", {"action": "resume", "session_id": first})
        self.assertEqual(str(refused.exception), "session_retired")
        # A replacement session adopts the still-open commitment.
        second = self.open_session()
        self.assertEqual(second["adopted_commitments"], [assigned["commitment"]])
        commitment = h.service.store.get(assigned["commitment"])
        self.assertEqual(commitment["owner"], second["session"]["id"])
        self.assertEqual(commitment["ownership_generation"], 2)
        self.assertEqual(
            h.service.store.get(assigned["assignment"])["owner"],
            second["session"]["id"],
        )

    def test_restart_mid_turn_requires_resume_and_lost_runner_is_explicit(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session, "SLEEP 3 then finish")
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "running"
            )
        )
        h.restart()  # store.recover retires active planning sessions
        self.assertEqual(h.service.store.get(session)["state"], "retiring")
        with self.assertRaises(DelegationRefused) as refused:
            h.call("delegation_session", {"action": "resume", "session_id": session})
        self.assertEqual(str(refused.exception), "turn_still_running")
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "returned"
            )
        )
        # The detached runner finished across the restart; session may now resume.
        self.assertEqual(h.service.store.get(session)["state"], "retired")
        # Retired by recovery: open a successor, which adopts the commitment.
        successor = self.open_session()
        self.assertEqual(successor["adopted_commitments"], [assigned["commitment"]])

        # A runner killed without a result is reported as lost, never retried.
        lost = self.assign(successor["session"]["id"], "SLEEP 30 never finishes")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(lost["assignment"])["turns"][0]["state"] == "running"
                and h.assignment_state(lost["assignment"])
            )
        )
        runner = state["turns"][0]["runner"]
        os.kill(runner["pid"], signal.SIGKILL)
        state = h.wait(
            lambda: (
                h.assignment_state(lost["assignment"])["turns"][0]["state"] == "lost"
                and h.assignment_state(lost["assignment"])
            )
        )
        self.assertIn("native outcome unknown", state["turns"][0]["failure"])
        self.assertIn("harness process signalled", state["turns"][0]["failure"])
        h.wait(lambda: not _alive(runner["harness_pid"]))
        self.assertEqual(h.gateway.delegation.launch_pending(), [])
        self.assertEqual(
            h.service.store.get(successor["session"]["id"])["state"], "idle"
        )
        result = h.call("delegation_result", {"assignment_id": lost["assignment"]})
        self.assertEqual(result["state"], "lost")
        self.assertIsNone(result["report"])

    def test_stop_while_idle_retires_immediately(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        stopped = h.call(
            "delegation_session",
            {"action": "stop", "session_id": session, "reason": "done"},
        )
        self.assertEqual(stopped["session"]["state"], "retired")
        self.assertIsNone(h.service.store.get(h.project)["interface_decision_owner"])
        self.assertEqual(self.open_session("codex")["session"]["harness"], "codex")

    def test_resume_after_idle_restart_bumps_incarnation_and_binding(self):
        h = self.harness
        opened = self.open_session()
        session = opened["session"]["id"]
        h.restart()
        resumed = h.call(
            "delegation_session", {"action": "resume", "session_id": session}
        )
        self.assertEqual(resumed["session"]["incarnation"], 2)
        self.assertEqual(resumed["binding"]["incarnation"], 2)
        bindings = [
            b
            for b in h.service.store.records("SessionBinding")
            if b["subject"]["id"] == session
        ]
        self.assertEqual([b["state"] for b in bindings], ["invalidated", "active"])
        self.assertEqual(bindings[1]["predecessor"], bindings[0]["id"])

    def test_codex_adapter_shape_and_unenforced_limits(self):
        h = self.harness
        opened = self.open_session("codex", model="fake-codex-model")
        session = opened["session"]["id"]
        self.assertIsNone(opened["session"]["native_session_id"])
        self.assertIsNone(opened["binding"])
        self.assertEqual(CAPABILITIES["codex"]["budget"], "unavailable")
        with self.assertRaises(DelegationRefused) as refused:
            self.assign(session)
        self.assertEqual(str(refused.exception), "limits_not_enforceable_on_harness")
        assigned = self.assign(session, allow_unenforced_limits=True)
        self.assertEqual(assigned["limit_enforcement"]["budget"], "unavailable")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "returned"
                and h.assignment_state(assigned["assignment"])
            )
        )
        self.assertEqual(
            state["turns"][0]["result"]["native_session_id"],
            "11111111-2222-4333-8444-555555555555",
        )
        self.assertIsNone(state["turns"][0]["result"]["cost_usd"])
        record = h.service.store.get(session)
        self.assertEqual(
            record["native_session_id"], "11111111-2222-4333-8444-555555555555"
        )
        view = h.call("delegation_status", {"session_id": session})["sessions"][0]
        self.assertEqual(view["binding"]["state"], "active")
        self.assertEqual(view["turns_with_unknown_cost"], 1)
        followed = h.call(
            "delegation_followup",
            {
                "session_id": session,
                "assignment_id": assigned["assignment"],
                "message": "again",
            },
        )
        h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][1]["state"]
                == "returned"
            )
        )
        spec = strict_loads(
            (
                h.state / "delegations" / session / followed["turn"] / "spec.json"
            ).read_text()
        )
        self.assertEqual(
            spec["argv"][1:4],
            ["exec", "resume", "11111111-2222-4333-8444-555555555555"],
        )
        first_spec = strict_loads(
            (
                h.state / "delegations" / session / assigned["turn"] / "spec.json"
            ).read_text()
        )
        self.assertIn("-C", first_spec["argv"])
        self.assertIn(str(h.workspace), first_spec["argv"])
        self.assertTrue(
            first_spec["argv"][-1].startswith("You are a synthetic worker.")
        )

    def test_failures_are_explicit_not_empty_success(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        crashed = self.assign(session, "CRASH now")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(crashed["assignment"])["turns"][0]["state"]
                == "failed"
                and h.assignment_state(crashed["assignment"])
            )
        )
        self.assertEqual(state["turns"][0]["result"]["exit_code"], 3)
        self.assertTrue(state["turns"][0]["result"]["is_error"])
        result = h.call("delegation_result", {"assignment_id": crashed["assignment"]})
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["report"]["parse_error"], "empty stdout")
        h.call(
            "delegation_followup",
            {
                "session_id": session,
                "assignment_id": crashed["assignment"],
                "message": "NOJSON",
            },
        )
        state = h.wait(
            lambda: (
                h.assignment_state(crashed["assignment"])["turns"][1]["state"]
                == "failed"
                and h.assignment_state(crashed["assignment"])
            )
        )
        self.assertIn("not a JSON", state["turns"][1]["result"]["parse_error"])
        cancelled = h.call(
            "delegation_close",
            {
                "assignment_id": crashed["assignment"],
                "disposition": "cancelled",
                "reason": "worker failed",
            },
        )
        self.assertEqual(cancelled["commitment_state"], "abandoned")

    def test_scope_configuration_and_argument_refusals(self):
        h = self.harness
        h.close()
        other = prepare_project(h.state)
        h.open()
        with self.assertRaises(PermissionError):
            h.call("delegation_status", {}, scope=other)
        self.assertEqual(h.call("delegation_status", {}, project=other)["sessions"], [])
        for arguments, code in (
            (
                {
                    "action": "create",
                    "harness": "claude-code",
                    "workspace": "/nonexistent/x",
                    "briefing": "b",
                },
                "workspace_missing",
            ),
            (
                {
                    "action": "create",
                    "harness": "claude-code",
                    "workspace": str(h.root),
                    "briefing": "b",
                },
                "workspace_outside_configured_roots",
            ),
            ({"action": "resume", "session_id": identifier()}, "unknown_session"),
        ):
            with (
                self.subTest(code=code),
                self.assertRaises(DelegationRefused) as refused,
            ):
                h.call("delegation_session", arguments)
            self.assertEqual(str(refused.exception), code)
        with self.assertRaises(Exception):
            h.call(
                "delegation_session",
                {
                    "action": "create",
                    "harness": "claude-code",
                    "workspace": "relative",
                    "briefing": "b",
                },
            )
        unconfigured = Gateway(h.service, delegation_config=None)
        operation = identifier()
        with self.assertRaises(DelegationRefused) as refused:
            submit_executive(
                unconfigured,
                {
                    "command": {
                        "schema_version": 1,
                        "operation_id": operation,
                        "action": "delegation_session",
                        "payload": {
                            "project": h.project,
                            "operation_id": operation,
                            "action": "create",
                            "harness": "claude-code",
                            "workspace": str(h.workspace),
                            "briefing": "b",
                        },
                    }
                },
                h.project,
            )
        self.assertEqual(str(refused.exception), "delegation_not_configured")
        self.assertFalse(
            submit_executive(
                unconfigured,
                {
                    "command": {
                        "schema_version": 1,
                        "operation_id": identifier(),
                        "action": "delegation_status",
                        "payload": {"project": h.project},
                    }
                },
                h.project,
            )["result"]["enabled"]
        )

    def test_bridge_path_carries_operation_id_on_the_envelope_only(self):
        from odin.executive_mcp import ExecutiveBridge

        h = self.harness

        def socket_handler(command):
            # Mirror the serve handler: bounded error dict with a refusal code.
            try:
                return submit_executive(h.gateway, {"command": command}, h.project)
            except Exception as error:
                result = {
                    "error": type(error).__name__,
                    "label": "fake-backend evidence",
                }
                if isinstance(error, DelegationRefused):
                    result["detail"] = str(error)
                return result

        bridge = ExecutiveBridge(h.project, socket_handler)
        arguments = {
            "operation_id": identifier(),
            "action": "create",
            "harness": "claude-code",
            "workspace": str(h.workspace),
            "briefing": "bridge briefing",
            "model": "fake-model",
        }
        result = bridge.call("odin_delegation_session", arguments)
        self.assertFalse(result["isError"], result)
        session = strict_loads(result["content"][0]["text"])["result"]["session"]["id"]
        # Replay through the bridge is idempotent and refusals carry a code.
        self.assertEqual(result, bridge.call("odin_delegation_session", arguments))
        refused = bridge.call(
            "odin_delegation_session",
            arguments | {"operation_id": identifier()},
        )
        self.assertTrue(refused["isError"])
        self.assertIn(
            "project_already_has_active_session", refused["content"][0]["text"]
        )
        status = bridge.call("odin_delegation_status", {"session_id": session})
        self.assertFalse(status["isError"])

    def test_retiring_session_strands_no_queued_turn(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        running = self.assign(session, "SLEEP 3 running")
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(running["assignment"])["turns"][0]["state"]
                == "running"
            )
        )
        second = self.assign(session, "second queued")
        self.assertEqual(
            h.assignment_state(second["assignment"])["turns"][0]["state"], "queued"
        )
        h.restart()  # recovery marks the active session retiring
        h.wait(
            lambda: (
                h.assignment_state(running["assignment"])["turns"][0]["state"]
                == "returned"
            )
        )
        self.assertEqual(h.service.store.get(session)["state"], "retired")
        self.assertEqual(
            h.assignment_state(second["assignment"])["turns"][0]["state"], "interrupted"
        )
        cancelled = h.call(
            "delegation_close",
            {
                "assignment_id": second["assignment"],
                "disposition": "cancelled",
                "reason": "stranded",
            },
        )
        self.assertEqual(cancelled["commitment_state"], "abandoned")

    def test_cancel_with_only_queued_turn_is_allowed(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session, "never launched")
        cancelled = h.call(
            "delegation_close",
            {
                "assignment_id": assigned["assignment"],
                "disposition": "cancelled",
                "reason": "changed mind",
            },
        )
        self.assertEqual(cancelled["assignment_state"], "cancelled")
        self.assertEqual(
            h.assignment_state(assigned["assignment"])["turns"][0]["state"],
            "interrupted",
        )
        self.assertEqual(h.gateway.delegation.launch_pending(), [])

    def test_failed_first_turn_rotates_native_session_then_resumes(self):
        h = self.harness
        opened = self.open_session()
        session = opened["session"]["id"]
        first_native = opened["session"]["native_session_id"]
        crashed = self.assign(session, "CRASH early")
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(crashed["assignment"])["turns"][0]["state"]
                == "failed"
            )
        )
        retry = h.call(
            "delegation_followup",
            {
                "session_id": session,
                "assignment_id": crashed["assignment"],
                "message": "try again",
            },
        )
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(crashed["assignment"])["turns"][1]["state"]
                == "returned"
            )
        )
        rotated = h.service.store.get(session)["native_session_id"]
        self.assertNotEqual(rotated, first_native)
        spec = strict_loads(
            (
                h.state / "delegations" / session / retry["turn"] / "spec.json"
            ).read_text()
        )
        self.assertEqual(spec["argv"][spec["argv"].index("--session-id") + 1], rotated)
        bindings = [
            b
            for b in h.service.store.records("SessionBinding")
            if b["subject"]["id"] == session
        ]
        self.assertEqual([b["state"] for b in bindings], ["invalidated", "active"])
        third = h.call(
            "delegation_followup",
            {
                "session_id": session,
                "assignment_id": crashed["assignment"],
                "message": "continue",
            },
        )
        h.gateway.delegation.launch_pending()
        h.wait(
            lambda: (
                h.assignment_state(crashed["assignment"])["turns"][2]["state"]
                == "returned"
            )
        )
        spec = strict_loads(
            (
                h.state / "delegations" / session / third["turn"] / "spec.json"
            ).read_text()
        )
        self.assertEqual(spec["argv"][spec["argv"].index("--resume") + 1], rotated)

    def test_overdue_runner_is_killed_and_marked_lost(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session, "SLEEP 60 stuck")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "running"
                and h.assignment_state(assigned["assignment"])
            )
        )
        runner = state["turns"][0]["runner"]
        os.kill(runner["pid"], signal.SIGSTOP)  # a stuck runner never reports
        turn = h.gateway.delegation._turn(assigned["turn"])
        with h.service.store.transaction():
            h.gateway.delegation._save_turn(
                turn
                | {"runner": turn["runner"] | {"launched_at": "2020-01-01T00:00:00Z"}}
            )
        state = h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "lost"
                and h.assignment_state(assigned["assignment"])
            )
        )
        self.assertIn("deadline exceeded", state["turns"][0]["failure"])
        h.wait(lambda: not _alive(runner["pid"]) and not _alive(runner["harness_pid"]))
        self.assertEqual(h.service.store.get(session)["state"], "idle")

    def test_codex_failure_summary_and_unreadable_result(self):
        h = self.harness
        session = self.open_session("codex", model="fake-codex-model")["session"]["id"]
        failed = self.assign(session, "please FAIL", allow_unenforced_limits=True)
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(failed["assignment"])["turns"][0]["state"]
                == "failed"
                and h.assignment_state(failed["assignment"])
            )
        )
        self.assertEqual(
            state["turns"][0]["result"]["error_summary"], "synthetic provider failure"
        )
        path = h.state / "delegations" / session / failed["turn"] / "result.json"
        path.write_text("{not json")
        result = h.call("delegation_result", {"assignment_id": failed["assignment"]})
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "result_unreadable")

    def test_operator_stop_halts_new_launches(self):
        h = self.harness
        session = self.open_session()["session"]["id"]
        assigned = self.assign(session, "after stop")
        h.service.store.stop("operator requested stop")
        h.gateway.delegation.tick()
        self.assertEqual(
            h.assignment_state(assigned["assignment"])["turns"][0]["state"], "queued"
        )

    def test_default_config_requires_a_harness(self):
        with self.assertRaises(ValueError):
            default_config(
                claude_config_dir=None,
                workspace_roots=[self.harness.workspace_root],
                codex_binary="/nonexistent/codex",
            )

    def test_runner_enforces_the_lineage_lease(self):
        """The runner takes the executive's lineage flock; busy means refused."""
        import fcntl

        h = self.harness
        session = self.open_session()["session"]["id"]
        self.assertEqual(
            h.call("delegation_status", {"session_id": session})["sessions"][0][
                "options"
            ]["lineage"],
            {"policy": "exclusive", "shared_with": None, "lease_enforced": True},
        )
        lock = os.open(
            h.config_dir / ".odin-lineage.lock", os.O_CREAT | os.O_RDWR, 0o600
        )
        self.addCleanup(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # another owner holds it
        refused = self.assign(session, "would refresh")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(refused["assignment"])
                if h.assignment_state(refused["assignment"])["turns"][0]["state"]
                in ("failed", "returned")
                else None
            )
        )
        turn = state["turns"][0]
        self.assertEqual(turn["state"], "failed")
        self.assertIn("lineage lease", turn["failure"])
        self.assertEqual(turn["result"]["exit_code"], None)  # no harness ran
        self.assertEqual(turn["result"]["lineage"]["lease"], "busy")
        self.assertTrue(turn["result"]["lineage"]["refused"])
        self.assertFalse(
            (h.state / "delegations" / session / turn["id"] / "started.json").exists()
        )
        fcntl.flock(lock, fcntl.LOCK_UN)
        before = (h.config_dir / ".credentials.json").stat().st_mtime_ns
        refreshed = self.assign(session, "REFRESH the token")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(refreshed["assignment"])
                if h.assignment_state(refreshed["assignment"])["turns"][0]["state"]
                == "returned"
                else None
            )
        )
        lineage = state["turns"][0]["result"]["lineage"]
        self.assertEqual(lineage["lease"], "acquired")
        self.assertFalse(lineage["refused"])
        self.assertTrue(lineage["credential_changed"])
        self.assertEqual(lineage["credential_before"]["mtime_ns"], before)
        self.assertNotEqual(
            lineage["credential_before"]["sha256"],
            lineage["credential_after"]["sha256"],
        )
        self.assertNotIn("refreshed", canonical(lineage))  # digest only, no content
        quiet = self.assign(session, "no refresh")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(quiet["assignment"])
                if h.assignment_state(quiet["assignment"])["turns"][0]["state"]
                == "returned"
                else None
            )
        )
        self.assertFalse(state["turns"][0]["result"]["lineage"]["credential_changed"])

    def test_shared_executive_lineage_requires_explicit_acceptance(self):
        import fcntl

        h = self.harness
        pilot = h.state / "executive-pilot"
        pilot.mkdir(mode=0o700)
        (pilot / "manifest.json").write_text(
            canonical({"version": 3, "config_dir": str(h.config_dir)}) + "\n"
        )
        with self.assertRaises(DelegationRefused) as refused:
            self.open_session()
        self.assertEqual(str(refused.exception), "lineage_shared_requires_acceptance")
        h.write_config(lineage_policy="shared_accepted")
        h.restart()
        opened = self.open_session()
        session = opened["session"]["id"]
        view = h.call("delegation_status", {"session_id": session})["sessions"][0]
        self.assertEqual(
            view["options"]["lineage"],
            {
                "policy": "shared_accepted",
                "shared_with": "executive",
                "lease_enforced": True,
            },
        )
        lock = os.open(
            h.config_dir / ".odin-lineage.lock", os.O_CREAT | os.O_RDWR, 0o600
        )
        self.addCleanup(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # the executive owns it
        assigned = self.assign(session, "runs on a shared lineage")
        h.gateway.delegation.launch_pending()
        state = h.wait(
            lambda: (
                h.assignment_state(assigned["assignment"])
                if h.assignment_state(assigned["assignment"])["turns"][0]["state"]
                == "returned"
                else None
            )
        )
        lineage = state["turns"][0]["result"]["lineage"]
        self.assertEqual(lineage["lease"], "busy")  # recorded, accepted, not owned
        self.assertEqual(lineage["shared_with"], "executive")
        self.assertFalse(lineage["refused"])

    def test_codex_without_codex_home_is_the_operator_lineage(self):
        h = self.harness
        config = strict_loads((h.state / "delegation.json").read_text())
        config["harnesses"]["codex"]["codex_home"] = None
        write_config(h.state, config)
        h.restart()
        with self.assertRaises(DelegationRefused) as refused:
            self.open_session(harness="codex")
        self.assertEqual(str(refused.exception), "lineage_shared_requires_acceptance")
        config["lineage_policy"] = "shared_accepted"
        write_config(h.state, config)
        h.restart()
        opened = self.open_session(harness="codex")
        view = h.call("delegation_status", {"session_id": opened["session"]["id"]})
        self.assertEqual(
            view["sessions"][0]["options"]["lineage"],
            {
                "policy": "shared_accepted",
                "shared_with": "operator-codex-login",
                "lease_enforced": False,
            },
        )

    def test_replayed_operation_returns_receipt_without_second_session(self):
        h = self.harness
        operation = identifier()
        first = self.open_session(operation_id=operation)
        second = self.open_session(operation_id=operation)
        self.assertEqual(first, second)
        sessions = [
            r
            for r in h.service.store.records("PlanningSession")
            if r["project"] == h.project
        ]
        self.assertEqual(len(sessions), 1)


if __name__ == "__main__":
    unittest.main()
