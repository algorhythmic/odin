"""ODIN-ADR-036 workstream sessions: identity, refusals, ownership, lineage limit."""

import tempfile
import unittest

from odin.delegation import DelegationRefused
from test_delegation import DelegationHarness


class WorkstreamSessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.harness = DelegationHarness(self.temporary.name)
        self.addCleanup(self.harness.close)

    def workspace(self, name):
        path = self.harness.workspace_root / name
        path.mkdir(mode=0o700, exist_ok=True)
        return str(path)

    def open_session(self, workspace=None, **extra):
        return self.harness.call(
            "delegation_session",
            {
                "action": "create",
                "harness": "claude-code",
                "workspace": workspace or str(self.harness.workspace),
                "briefing": "You are a synthetic worker.",
                "model": "fake-model",
            }
            | extra,
        )

    def refused(self, code, **arguments):
        with self.assertRaises(DelegationRefused) as raised:
            self.open_session(**arguments)
        self.assertEqual(str(raised.exception), code)

    def assign(self, session, instructions="do the thing"):
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
            },
        )

    def owner(self):
        return self.harness.service.store.get(self.harness.project)["interface_decision_owner"]

    def test_legacy_owner_and_workstreams_coexist_with_typed_refusals(self):
        legacy = self.open_session()
        self.assertEqual((legacy["workstream"], legacy["role"]), (None, "integration_owner"))
        self.assertEqual(self.owner(), legacy["session"]["id"])
        # Legacy against legacy keeps the original refusal code.
        self.refused("project_already_has_active_session", workspace=self.workspace("x"))
        self.refused("workstream_label_required", workspace=self.workspace("x"), role="workstream")
        self.refused("project_already_has_integration_owner", workspace=self.workspace("x"),
                     workstream="integration", role="integration_owner")
        self.refused("workspace_in_use_by_active_session", workstream="docs")
        docs = self.open_session(self.workspace("docs"), workstream="docs")
        self.assertEqual((docs["workstream"], docs["role"]), ("docs", "workstream"))
        self.assertEqual(docs["options"]["workstream"], "docs")
        self.refused("workstream_already_has_active_session", workspace=self.workspace("x"),
                     workstream="docs")
        tests = self.open_session(self.workspace("tests"), workstream="tests", role="workstream")
        # Workstream sessions never take the project's planning ownership.
        self.assertEqual(self.owner(), legacy["session"]["id"])
        status = self.harness.call("delegation_status", {})
        aggregate = status["project_aggregate"]
        self.assertEqual(aggregate["integration_owner"], legacy["session"]["id"])
        self.assertEqual(
            [(row["workstream"], row["role"], row["legacy"]) for row in aggregate["active_sessions"]],
            [(None, "integration_owner", True), ("docs", "workstream", False),
             ("tests", "workstream", False)],
        )
        self.assertEqual(aggregate["max_concurrent_turns_per_lineage"], 1)
        self.assertEqual(aggregate["cost_label"], "attributed_not_verified")
        # Stopping a workstream session leaves the owner in place.
        self.harness.call("delegation_session", {"action": "stop", "session_id": tests["session"]["id"]})
        self.assertEqual(self.owner(), legacy["session"]["id"])
        with self.assertRaises(DelegationRefused) as raised:
            self.harness.call("delegation_session", {"action": "resume",
                                                     "session_id": docs["session"]["id"],
                                                     "workstream": "other"})
        self.assertEqual(str(raised.exception), "session_identity_fixed_at_create")

    def test_resume_keeps_the_owner_rule(self):
        h = self.harness
        docs = self.open_session(self.workspace("docs"), workstream="docs")["session"]["id"]
        self.assertIsNone(self.owner())
        resumed = h.call("delegation_session", {"action": "resume", "session_id": docs})
        self.assertEqual(resumed["role"], "workstream")
        self.assertIsNone(self.owner())
        legacy = self.open_session()["session"]["id"]
        h.call("delegation_session", {"action": "resume", "session_id": legacy})
        self.assertEqual(self.owner(), legacy)
        h.call("delegation_session", {"action": "resume", "session_id": docs})
        self.assertEqual(self.owner(), legacy)

    def test_adoption_is_restricted_to_the_same_workstream(self):
        h = self.harness
        first = self.open_session(self.workspace("a1"), workstream="alpha")["session"]["id"]
        assigned = self.assign(first)
        h.call("delegation_session", {"action": "stop", "session_id": first})
        self.assertEqual(h.service.store.get(first)["state"], "retired")
        other = self.open_session(self.workspace("b1"), workstream="beta")
        self.assertEqual(other["adopted_commitments"], [])
        legacy = self.open_session()
        self.assertEqual(legacy["adopted_commitments"], [])
        same = self.open_session(self.workspace("a2"), workstream="alpha")
        self.assertEqual(same["adopted_commitments"], [assigned["commitment"]])
        self.assertEqual(h.service.store.get(assigned["commitment"])["owner"], same["session"]["id"])

    def test_workstream_briefing_carries_the_integration_rule(self):
        h = self.harness
        session = self.open_session(self.workspace("w"), workstream="w")["session"]["id"]
        self.assign(session)
        h.gateway.delegation.launch_pending()
        spec = next((h.state / "delegations" / session).glob("*/spec.json")).read_text()
        self.assertIn("Never fast-forward", spec)
        self.assertIn("merge-ready head", spec)
        h.wait(lambda: h.call("delegation_status", {})["project_aggregate"]["lineages"][0]["running"] == 0)

    def test_default_lineage_limit_interleaves_sessions(self):
        h = self.harness
        owner = self.open_session()["session"]["id"]
        docs = self.open_session(self.workspace("docs"), workstream="docs")["session"]["id"]
        first = self.assign(owner, "SLEEP 2 then finish")
        second = self.assign(docs, "SLEEP 0.1 then finish")
        self.assertEqual(len(h.gateway.delegation.launch_pending()), 1)
        lineage = h.call("delegation_status", {})["project_aggregate"]["lineages"][0]
        self.assertEqual((lineage["harnesses"], lineage["running"], lineage["queued"]),
                         (["claude-code"], 1, 1))
        self.assertEqual(h.gateway.delegation.launch_pending(), [])
        for assigned in (first, second):
            h.wait(lambda a=assigned: h.assignment_state(a["assignment"])["turns"][0]["state"]
                   == "returned", timeout=30)

    def test_raised_lineage_limit_launches_across_sessions(self):
        h = self.harness
        h.close()
        h.write_config(max_concurrent_turns_per_lineage=2)
        h.open()
        owner = self.open_session()["session"]["id"]
        docs = self.open_session(self.workspace("docs"), workstream="docs")["session"]["id"]
        first = self.assign(owner, "SLEEP 1 then finish")
        second = self.assign(docs, "SLEEP 1 then finish")
        self.assertEqual(len(h.gateway.delegation.launch_pending()), 2)
        # One running turn per session still holds.
        self.assign(owner, "queued behind the first")
        self.assertEqual(h.gateway.delegation.launch_pending(), [])
        for assigned in (first, second):
            h.wait(lambda a=assigned: h.assignment_state(a["assignment"])["turns"][0]["state"]
                   in ("returned", "failed"), timeout=30)


if __name__ == "__main__":
    unittest.main()
