import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from odin.contracts import ROOT, Contracts
from odin.harness import (
    CapabilityRefusal,
    ClaudeAgentSDKAdapter,
    ClaudeSDKClientSession,
    build_denied_sdk_options,
)
from odin.session_host import SessionHost
from odin.store import Conflict, digest


def command(action="start", operation="op-1"):
    return {
        "schema_version": 1,
        "operation_id": operation,
        "action": action,
        "host": "host-1",
        "session": "session-1",
        "generation": 1,
        "assignment": "assignment-1",
        "assignment_revision": 2,
        "ownership_generation": 3,
        "profile": "planner",
        "grant_id": "grant-1",
        "budget_ref": "budget-1",
        "credential_ref": "odin-harness:lineage-1",
        "data_policy_ref": "policy-1",
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z"),
        "required_capabilities": ["start"],
    }


def authority_for(command_value, **overrides):
    return {
        **{
            key: command_value[key]
            for key in (
                "session",
                "generation",
                "assignment",
                "assignment_revision",
                "ownership_generation",
                "grant_id",
                "budget_ref",
                "credential_ref",
                "data_policy_ref",
            )
        },
        "stopped": False,
        "grant_active": True,
        "budget_available": True,
        "credential_ready": True,
        "data_policy_allowed": True,
        "command_digest": digest(command_value),
        "grant_action": command_value["action"],
        "grant_resource": command_value["assignment"],
        **overrides,
    }


class MockSDKTransport:
    def __init__(self):
        self.accepted = {}
        self.calls = 0
        self.lose_receipt = False
        self.capabilities_seen = []

    def require(self, names):
        # Fixture protocol only; this is not a live SDK capability probe.
        self.capabilities_seen.append(set(names))
        return True

    def execute(self, action, item):
        self.calls += 1
        state = {
            "start": "active",
            "resume": "active",
            "interrupt": "idle",
            "retire": "retired",
        }[action]
        observation = {
            "schema_version": 1,
            "operation_id": item["operation_id"],
            "state": state,
            "native_session_id": "native-1",
            "evidence": [],
            "usage_state": "unknown",
        }
        self.accepted[item["operation_id"]] = observation
        if self.lose_receipt:
            raise ConnectionError("receipt lost after mock acceptance")
        return observation

    def lookup(self, operation_id):
        return self.accepted.get(operation_id)

    def observe_session(self, session, operation_id):
        if session != "session-1":
            return None
        return self.accepted.get(operation_id)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "host.sqlite3"
        self.transport = MockSDKTransport()
        self.host = SessionHost(self.path, self.transport, host_id="host-1")
        self.item = command()
        self.current = authority_for(self.item)

    def tearDown(self):
        self.host.close()
        self.tmp.cleanup()

    def auth(self, _):
        return self.current

    def test_duplicate_restart_and_conflicting_identity(self):
        first = self.host.command(self.item, authority=self.auth)
        self.assertEqual(first["state"], "active")
        self.host.close()
        self.host = SessionHost(self.path, self.transport, host_id="host-1")
        replay = self.host.command(self.item, authority=self.auth)
        self.assertEqual(replay["state"], first["state"])
        self.assertTrue(replay["historical"])
        self.assertEqual(self.transport.calls, 1)
        with self.assertRaises(Conflict):
            self.host.command(self.item | {"generation": 2}, authority=self.auth)

    def test_stale_owner_grant_stop_and_budget_refuse_before_transport(self):
        for change in (
            {"ownership_generation": 4},
            {"grant_active": False},
            {"stopped": True},
            {"budget_available": False},
            {"credential_ready": False},
            {"data_policy_allowed": False},
        ):
            self.current = authority_for(self.item, **change)
            with self.assertRaises(PermissionError):
                self.host.command(self.item, authority=self.auth)
        self.assertEqual(self.transport.calls, 0)

    def test_unknown_receipt_reconciles_after_restart_without_redispatch(self):
        self.transport.lose_receipt = True
        with self.assertRaises(ConnectionError):
            self.host.command(self.item, authority=self.auth)
        self.assertEqual(self.host.lookup("op-1")["state"], "unknown")
        self.host.close()
        self.host = SessionHost(self.path, self.transport, host_id="host-1")
        self.host.host_offline()
        with self.assertRaises(ConnectionError):
            self.host.reconcile("op-1", authority=self.auth)
        self.host.host_online()
        self.assertEqual(
            self.host.reconcile("op-1", authority=self.auth)["state"], "active"
        )
        self.assertEqual(self.transport.calls, 1)

    def test_absent_lookup_stays_unknown_and_stale_authority_holds(self):
        self.transport.lose_receipt = True
        with self.assertRaises(ConnectionError):
            self.host.command(self.item, authority=self.auth)
        self.transport.accepted.clear()
        self.current = authority_for(self.item, grant_active=False)
        with self.assertRaises(PermissionError):
            self.host.reconcile("op-1", authority=self.auth)
        self.assertEqual(self.host.lookup("op-1")["state"], "unknown")

    def test_accepted_lookup_after_revocation_is_held(self):
        self.transport.lose_receipt = True
        with self.assertRaises(ConnectionError):
            self.host.command(self.item, authority=self.auth)
        self.current = authority_for(self.item, grant_active=False)
        result = self.host.reconcile("op-1", authority=self.auth)
        self.assertEqual(result["state"], "held")
        self.assertEqual(result["observation"]["state"], "active")
        self.assertEqual(self.transport.calls, 1)

    def test_offline_binding_requires_reconciliation_and_stop_can_interrupt(self):
        self.host.command(self.item, authority=self.auth)
        self.host.host_offline()
        self.host.host_online()
        resume = command("resume", "op-2")
        self.current = authority_for(resume)
        with self.assertRaises(Conflict):
            self.host.command(resume, authority=self.auth)
        self.current = authority_for(self.item)
        self.assertEqual(
            self.host.reconcile_binding("session-1", authority=self.auth), "active"
        )
        # Direct control stays available after service stop, with current
        # identity checks and an explicitly issued new operation.
        interrupt = command("interrupt", "op-3")
        self.current = authority_for(interrupt, stopped=True, grant_active=False)
        self.assertEqual(
            self.host.command(interrupt, authority=self.auth)["state"], "idle"
        )

    def test_late_partial_and_unknown_usage_are_not_accepted(self):
        self.host.command(self.item, authority=self.auth)
        base = self.transport.accepted["op-1"]
        self.assertFalse(
            self.host.eligible_return(self.item, base, authority=self.auth)
        )
        done = base | {"state": "idle", "evidence": ["artifact-1"]}
        self.assertFalse(
            self.host.eligible_return(self.item, done, authority=self.auth)
        )
        done = done | {"usage_state": "known"}
        self.current = authority_for(self.item, ownership_generation=4)
        self.assertFalse(
            self.host.eligible_return(self.item, done, authority=self.auth)
        )
        self.current = authority_for(self.item)
        self.host._record(self.item, done)
        self.assertTrue(self.host.eligible_return(self.item, done, authority=self.auth))

    def test_adapter_never_claims_mock_as_live_capability(self):
        adapter = ClaudeAgentSDKAdapter(lambda _: self.transport, verified={"start"})
        self.assertEqual(adapter.probe()["supported_live"], [])
        with self.assertRaises(CapabilityRefusal):
            adapter.execute("start", self.item)
        with self.assertRaises(CapabilityRefusal):
            adapter.execute(
                "start", self.item | {"required_capabilities": ["profile_enforcement"]}
            )
        with self.assertRaises(CapabilityRefusal):
            adapter.execute("start", self.item | {"profile": "subagent"})

    def test_sdk_options_disable_inherited_settings_tools_and_children(self):
        sdk = SimpleNamespace(
            ClaudeAgentOptions=lambda **options: options,
            PermissionResultDeny=lambda **fields: fields,
        )
        options = build_denied_sdk_options(
            sdk, model="exact-model-id", effort="medium", resume="native-session"
        )
        self.assertEqual(options["setting_sources"], [])
        self.assertEqual(options["tools"], [])
        self.assertEqual(options["agents"], {})
        self.assertEqual(options["permission_mode"], "dontAsk")
        self.assertEqual(options["resume"], "native-session")
        import asyncio

        refusal = asyncio.run(options["can_use_tool"]("Bash", {}, None))
        self.assertIn("no verified live tool authority", refusal["message"])

    def test_harness_structural_fixtures(self):
        cases = json.loads((ROOT / "fixtures/harness-contracts.json").read_text())[
            "cases"
        ]
        validators = Contracts().validators
        for case in cases:
            with self.subTest(case["name"]):
                self.assertEqual(
                    validators[case["schema"]].is_valid(case["value"]), case["valid"]
                )

    def test_sdk_client_lifecycle_against_protocol_mock(self):
        import asyncio

        class Client:
            def __init__(self, options):
                self.options = options
                self.events = []

            async def connect(self):
                self.events.append("connect")

            async def query(self, prompt):
                self.events.append(("query", prompt))

            async def receive_response(self):
                yield {"type": "result", "session_id": "native-1"}

            async def interrupt(self):
                self.events.append("interrupt")

            async def disconnect(self):
                self.events.append("disconnect")

        sdk = SimpleNamespace(
            ClaudeAgentOptions=lambda **options: options,
            PermissionResultDeny=lambda **fields: fields,
            ClaudeSDKClient=Client,
        )

        async def exercise():
            refused = ClaudeSDKClientSession(
                sdk, model="exact-model-id", effort="medium"
            )
            with self.assertRaises(CapabilityRefusal):
                await refused.open()
            session = ClaudeSDKClientSession(
                sdk,
                model="exact-model-id",
                effort="medium",
                native_session_id="native-1",
                protocol_test=True,
            )
            await session.open()
            client = session.client
            self.assertEqual(client.options["resume"], "native-1")
            self.assertEqual(
                await session.query("prepared briefing"),
                [{"type": "result", "session_id": "native-1"}],
            )
            await session.interrupt()
            await session.close()
            self.assertEqual(
                client.events,
                ["connect", ("query", "prepared briefing"), "interrupt", "disconnect"],
            )

        asyncio.run(exercise())

    def test_restart_requires_fresh_binding_observation(self):
        self.host.command(self.item, authority=self.auth)
        self.host.close()
        self.host = SessionHost(self.path, self.transport, host_id="host-1")
        self.assertEqual(
            self.host.db.execute("SELECT state FROM bindings").fetchone()[0],
            "host_offline",
        )
        resume = command("resume", "op-2")
        self.current = authority_for(resume)
        with self.assertRaises(Conflict):
            self.host.command(resume, authority=self.auth)
        self.current = authority_for(self.item)
        self.assertEqual(
            self.host.reconcile_binding("session-1", authority=self.auth), "active"
        )

    def test_exact_command_and_grant_scope_bound(self):
        for change in (
            {"profile": "reviewer"},
            {"required_capabilities": ["start", "native_children"]},
            {"action": "resume"},
        ):
            with self.assertRaises(PermissionError):
                self.host.command(self.item | change, authority=self.auth)
        self.current = authority_for(self.item, grant_resource="unrelated")
        with self.assertRaises(PermissionError):
            self.host.command(self.item, authority=self.auth)
        self.current = authority_for(self.item)
        self.host.command(self.item, authority=self.auth)
        self.assertIn("profile_enforcement", self.transport.capabilities_seen[0])
        self.assertIn("credential_isolation", self.transport.capabilities_seen[0])

    def test_unknown_start_reserves_session_and_writer(self):
        self.transport.lose_receipt = True
        with self.assertRaises(ConnectionError):
            self.host.command(self.item, authority=self.auth)
        with self.assertRaises(Conflict):
            SessionHost(self.path, MockSDKTransport(), host_id="host-1")
        competing = command("start", "op-2")
        self.current = authority_for(competing)
        with self.assertRaises(Conflict):
            self.host.command(competing, authority=self.auth)
        self.assertEqual(self.transport.calls, 1)

    def test_unknown_stop_never_frees_session(self):
        self.host.command(self.item, authority=self.auth)
        stop = command("interrupt", "op-stop")
        self.current = authority_for(stop, stopped=True, grant_active=False)
        self.transport.lose_receipt = True
        with self.assertRaises(ConnectionError):
            self.host.command(stop, authority=self.auth)
        self.assertEqual(
            self.host.db.execute("SELECT state FROM bindings").fetchone()[0],
            "stop_unknown",
        )
        self.assertEqual(
            self.host.reconcile_binding("session-1", authority=self.auth),
            "stop_unknown",
        )
        resume = command("resume", "op-resume")
        self.current = authority_for(resume)
        with self.assertRaises(Conflict):
            self.host.command(resume, authority=self.auth)
        self.current = authority_for(stop, stopped=True, grant_active=False)
        self.assertEqual(
            self.host.reconcile("op-stop", authority=self.auth)["state"], "idle"
        )

    def test_retire_cannot_reconcile_as_active(self):
        self.host.command(self.item, authority=self.auth)
        retire = command("retire", "op-retire")
        self.current = authority_for(retire)
        self.host.command(retire, authority=self.auth)
        self.host.host_offline()
        self.host.host_online()
        self.transport.accepted["op-retire"] = self.transport.accepted["op-retire"] | {
            "state": "active"
        }
        with self.assertRaises(Conflict):
            self.host.reconcile_binding("session-1", authority=self.auth)


if __name__ == "__main__":
    unittest.main()
