"""Synthetic continuity and decision tests; no live model or Saga access."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from odin.continuity import Continuity
from odin.memory import Memory
from odin.service import fixture_record
from odin.store import Conflict, Store, digest


def future(hours=1):
    return (
        (datetime.now(timezone.utc) + timedelta(hours=hours))
        .isoformat()
        .replace("+00:00", "Z")
    )


class ContinuityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.co = Continuity(self.store, allow_fixture_evidence=True)
        self.project = fixture_record("Project", name="Atlas")
        self.other = fixture_record("Project", name="Atlas Archive")
        self.commitment = fixture_record(
            "Commitment",
            project=self.project["id"],
            objective="Revise interface",
            next_trigger=future(),
        )
        self.other_commitment = fixture_record(
            "Commitment", project=self.other["id"], objective="Private archive"
        )
        for record in (
            self.project,
            self.other,
            self.commitment,
            self.other_commitment,
        ):
            self.store.create(record)
        self.scope = [self.project["id"]]

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def item(self):
        return {
            "schema_version": 1,
            "project": self.project["id"],
            "dedupe_key": "interface-choice:1",
            "recipient": "operator-1",
            "kind": "clarification",
            "question": "Choose the interface?",
            "options": ["A", "B"],
            "recommendation": "A",
            "evidence": [{"ref": "fixture:requirements", "revision": "2"}],
            "artifact": {"ref": "artifact:proposal", "digest": "a" * 64},
            "authorization": {
                "action": "revise interface",
                "scope": [self.project["id"]],
            },
            "blockers": ["operator choice"],
            "urgency": "routine",
            "commitments": [
                {"id": self.commitment["id"], "rev": self.commitment["rev"]}
            ],
            "record_refs": [],
            "memory_revision": None,
            "authority_revision": "policy:1",
            "expires_at": future(),
        }

    def prepare_choices(self, count, memory_revision=None):
        choices = {}
        for index in range(count):
            commitment = fixture_record(
                "Commitment", project=self.project["id"], objective=f"Choice {index}"
            )
            self.store.create(commitment)
            item = self.item() | {
                "dedupe_key": f"choice:{index}",
                "commitments": [{"id": commitment["id"], "rev": commitment["rev"]}],
                "memory_revision": memory_revision,
            }
            request = self.co.prepare_decision(
                item, principal="operator-1", permitted_projects=self.scope
            )
            choices[request["id"]] = item
        return choices

    def test_restart_lost_delivery_and_expiry_preserve_obligation(self):
        item = self.item()
        request = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(
            request["id"],
            self.co.prepare_decision(
                item, principal="operator-1", permitted_projects=self.scope
            )["id"],
        )
        before = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        delivery = self.co.record_delivery(
            before, principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(
            self.co.record_delivery(
                before,
                principal="operator-1",
                permitted_projects=self.scope,
                delivery_id=delivery,
            ),
            delivery,
        )
        self.assertEqual(
            self.co.resume(
                self.project["id"],
                principal="operator-1",
                permitted_projects=self.scope,
            )["acknowledged_seq"],
            0,
        )
        self.store.close()
        self.store = Store(Path(self.temp.name))
        self.co = Continuity(self.store, allow_fixture_evidence=True)
        resumed = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(len(resumed["commitments"]), 1)
        self.assertEqual(resumed["decisions"][0]["request"]["id"], request["id"])
        self.assertEqual(resumed["acknowledged_seq"], 0)
        self.co.expire_decision(request["id"], at=future(2))
        after = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(after["decisions"][0]["request"]["state"], "expired")
        self.assertEqual(after["commitments"][0]["state"], "open")
        self.co.acknowledge(
            delivery, principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(
            self.co.resume(
                self.project["id"],
                principal="operator-1",
                permitted_projects=self.scope,
            )["acknowledged_seq"],
            before["history_seq"],
        )

    def test_response_is_revision_bound_and_no_authority_grant(self):
        item = self.item()
        req = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        kwargs = dict(
            response="A",
            expected_rev=1,
            evidence_digest=digest(item["evidence"]),
            authority_revision="policy:1",
            principal="operator-1",
            permitted_projects=self.scope,
        )
        with self.assertRaises(PermissionError):
            self.co.respond_decision(req["id"], channel="voice", **kwargs)
        with self.assertRaises(Conflict):
            self.co.respond_decision(
                req["id"], **(kwargs | {"authority_revision": "policy:2"})
            )
        with self.assertRaises(Conflict):
            self.co.respond_decision(
                req["id"], **(kwargs | {"evidence_digest": "0" * 64})
            )
        answered = self.co.respond_decision(req["id"], **kwargs)
        self.assertEqual(answered["state"], "answered")
        self.assertEqual(self.store.get(self.commitment["id"])["state"], "open")
        self.assertEqual(self.store.get(self.commitment["id"])["decisions"], [])

    def test_scope_stale_record_and_bounded_enumeration(self):
        with self.assertRaises(PermissionError):
            self.co.resume(
                self.other["id"], principal="operator-1", permitted_projects=self.scope
            )
        with self.assertRaises(PermissionError):
            self.co.prepare_decision(
                self.item() | {"recipient": "operator-2"},
                principal="operator-1",
                permitted_projects=self.scope,
            )
        stale = self.item()
        self.store.update(
            self.commitment["id"], {"state": "blocked"}, self.commitment["rev"]
        )
        with self.assertRaises(Conflict):
            self.co.prepare_decision(
                stale, principal="operator-1", permitted_projects=self.scope
            )
        view = self.co.resume(
            self.project["id"],
            principal="operator-1",
            permitted_projects=self.scope,
            detail_bytes=0,
        )
        self.assertEqual(view["changes"], [])
        self.assertGreater(view["changes_omitted"], 0)
        self.assertEqual(
            [c["id"] for c in view["commitments"]], [self.commitment["id"]]
        )
        self.assertEqual(view["blockers"], [self.commitment["id"]])
        self.assertEqual(view["memory"]["availability"], "unavailable")

    def test_changed_record_invalidates_prepared_answer(self):
        item = self.item()
        req = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        current = self.store.get(self.commitment["id"])
        self.store.update(
            current["id"], {"objective": "Changed requirement"}, current["rev"]
        )
        view = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertTrue(view["decisions"][0]["prepared"]["unavailable"])
        self.assertEqual(view["decisions"][0]["request"]["options"], [])
        self.assertEqual(
            view["recommended_next_action"], "reissue an unavailable decision request"
        )
        with self.assertRaises(Conflict):
            self.co.respond_decision(
                req["id"],
                response="A",
                expected_rev=1,
                evidence_digest=digest(item["evidence"]),
                authority_revision="policy:1",
                principal="operator-1",
                permitted_projects=self.scope,
            )

    def test_bound_record_change_hides_prepared_wording(self):
        item = self.item() | {
            "record_refs": [{"id": self.project["id"], "rev": self.project["rev"]}]
        }
        self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        self.store.update(
            self.project["id"], {"name": "Revised Atlas"}, self.project["rev"]
        )
        view = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertTrue(view["decisions"][0]["prepared"]["unavailable"])
        self.assertNotIn("question", view["decisions"][0]["prepared"])
        self.assertEqual(view["decisions"][0]["request"]["options"], [])

    def test_expiry_hides_choices_before_expiration_sweep(self):
        item = self.item()
        request = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        with patch("odin.continuity.now", return_value=future(2)):
            view = self.co.resume(
                self.project["id"],
                principal="operator-1",
                permitted_projects=self.scope,
            )
            self.assertTrue(view["decisions"][0]["prepared"]["unavailable"])
            self.assertEqual(view["decisions"][0]["request"]["options"], [])
            self.assertEqual(
                view["recommended_next_action"], "reissue an expired decision request"
            )
            with self.assertRaisesRegex(Conflict, "request expired"):
                self.co.respond_decision(
                    request["id"],
                    response="A",
                    expected_rev=1,
                    evidence_digest=digest(item["evidence"]),
                    authority_revision="policy:1",
                    principal="operator-1",
                    permitted_projects=self.scope,
                )
        self.assertEqual(self.store.get(request["id"])["state"], "open")
        self.assertEqual(self.store.get(self.commitment["id"])["state"], "open")

    def test_decision_pages_bind_scope_offset_and_current_records(self):
        choices = self.prepare_choices(3)
        common = {
            "project": self.project["id"],
            "principal": "operator-1",
            "permitted_projects": self.scope,
            "decision_limit": 1,
        }
        first = self.co.resume(**common)
        continuation = common | {
            "decision_offset": first["next_decision_offset"],
            "decision_page_token": first["next_decision_page_token"],
        }
        second = self.co.resume(**continuation)
        self.assertNotEqual(
            first["decisions"][0]["request"]["id"],
            second["decisions"][0]["request"]["id"],
        )
        for changed in (
            {"decision_page_token": None},
            {"decision_page_token": "forged"},
            {"decision_offset": 2},
            {"principal": "operator-2"},
            {"project": self.other["id"], "permitted_projects": [self.other["id"]]},
        ):
            with self.subTest(changed=changed), self.assertRaises(Conflict):
                self.co.resume(**(continuation | changed))
        with self.assertRaises(ValueError):
            self.co.resume(
                **common, decision_page_token=first["next_decision_page_token"]
            )
        request = first["decisions"][0]["request"]
        self.co.respond_decision(
            request["id"],
            response="A",
            expected_rev=request["rev"],
            evidence_digest=digest(choices[request["id"]]["evidence"]),
            authority_revision="policy:1",
            principal="operator-1",
            permitted_projects=self.scope,
        )
        with self.assertRaisesRegex(Conflict, "decision page token"):
            self.co.resume(**continuation)
        refreshed = self.co.resume(**common)
        self.assertEqual(refreshed["decision_count"], 2)
        self.assertNotEqual(refreshed["decisions"][0]["request"]["id"], request["id"])

    def test_decision_pages_invalidate_after_memory_change(self):
        memory = Memory(self.store)
        self.co = Continuity(self.store, memory, allow_fixture_evidence=True)
        self.prepare_choices(2, memory.dependency_revision(self.project["id"]))
        common = {
            "project": self.project["id"],
            "principal": "operator-1",
            "permitted_projects": self.scope,
            "decision_limit": 1,
        }
        first = self.co.resume(**common)
        memory.processing(self.project["id"], "fixture-capture", availability="unknown")
        with self.assertRaisesRegex(Conflict, "decision page token"):
            self.co.resume(
                **common,
                decision_offset=first["next_decision_offset"],
                decision_page_token=first["next_decision_page_token"],
            )

    def test_forged_delivery_and_paged_obligations(self):
        for index in range(35):
            self.store.create(
                fixture_record(
                    "Commitment",
                    project=self.project["id"],
                    objective=f"Additional obligation {index}",
                )
            )
        first = self.co.resume(
            self.project["id"],
            principal="operator-1",
            permitted_projects=self.scope,
            obligation_limit=32,
        )
        self.assertEqual(first["commitment_count"], 36)
        self.assertEqual(len(first["commitments"]), 32)
        self.assertEqual(first["next_obligation_offset"], 32)
        second = self.co.resume(
            self.project["id"],
            principal="operator-1",
            permitted_projects=self.scope,
            obligation_offset=32,
            obligation_page_token=first["next_obligation_page_token"],
        )
        self.assertEqual(len(second["commitments"]), 4)
        with self.assertRaises(Conflict):
            self.co.record_delivery(
                first | {"history_seq": 10**9},
                principal="operator-1",
                permitted_projects=self.scope,
            )

    def test_cross_project_evidence_and_duplicates(self):
        item = self.item()
        item["record_refs"] = [{"id": self.other["id"], "rev": self.other["rev"]}]
        with self.assertRaises(PermissionError):
            self.co.prepare_decision(
                item, principal="operator-1", permitted_projects=self.scope
            )
        item["record_refs"] = []
        item["commitments"] *= 2
        with self.assertRaises(Conflict):
            self.co.prepare_decision(
                item, principal="operator-1", permitted_projects=self.scope
            )

    def test_omitted_change_cannot_be_acknowledged(self):
        brief = self.co.resume(
            self.project["id"],
            principal="operator-1",
            permitted_projects=self.scope,
            detail_bytes=0,
        )
        self.assertGreater(brief["changes_omitted"], 0)
        delivery = self.co.record_delivery(
            brief, principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(
            self.co.acknowledge(
                delivery, principal="operator-1", permitted_projects=self.scope
            ),
            brief["acknowledgeable_seq"],
        )
        self.assertLess(brief["acknowledgeable_seq"], brief["history_seq"])

    def test_memory_revision_invalidates_answer_and_delivery(self):
        class MemoryStub:
            revision = 1

            def dependency_revision(self, project):
                return self.revision

            def snapshot(self, project, principal):
                return {
                    "availability": "unavailable",
                    "dependency_revision": self.revision,
                    "truncated": False,
                    "sources": [],
                    "statements": [],
                    "freshness": [],
                    "coverage": [],
                }

        memory = MemoryStub()
        self.co = Continuity(self.store, memory, allow_fixture_evidence=True)
        item = self.item() | {"memory_revision": 1}
        req = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        brief = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        delivery = self.co.record_delivery(
            brief, principal="operator-1", permitted_projects=self.scope
        )
        memory.revision = 2
        with self.assertRaises(Conflict):
            self.co.acknowledge(
                delivery, principal="operator-1", permitted_projects=self.scope
            )
        with self.assertRaises(Conflict):
            self.co.respond_decision(
                req["id"],
                response="A",
                expected_rev=1,
                evidence_digest=digest(item["evidence"]),
                authority_revision="policy:1",
                principal="operator-1",
                permitted_projects=self.scope,
            )

    def test_evidence_resolver_and_scope_are_revalidated(self):
        self.co = Continuity(self.store)
        with self.assertRaises(Conflict):
            self.co.prepare_decision(
                self.item(), principal="operator-1", permitted_projects=self.scope
            )
        linked = self.item()
        linked["evidence"] = [
            {
                "ref": "record:" + self.commitment["id"],
                "revision": str(self.commitment["rev"]),
            }
        ]
        with self.assertRaises(Conflict):
            self.co.prepare_decision(
                linked, principal="operator-1", permitted_projects=self.scope
            )
        item = self.item()
        item["authorization"]["scope"] = [self.other["id"]]
        with self.assertRaises(PermissionError):
            self.co.prepare_decision(
                item, principal="operator-1", permitted_projects=self.scope
            )
        state = {
            "revision": "2",
            "digest": "a" * 64,
            "project": self.project["id"],
            "readers": ["operator-1"],
        }

        def resolve(ref, *, project, principal):
            return state.copy()

        self.co = Continuity(self.store, evidence_resolver=resolve)
        item = self.item()
        item["evidence"] = [{"ref": "source:requirements", "revision": "2"}]
        item["artifact"]["ref"] = "source:proposal"
        request = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        state["digest"] = "b" * 64
        with self.assertRaises(Conflict):
            self.co.respond_decision(
                request["id"],
                response="A",
                expected_rev=1,
                evidence_digest=digest(item["evidence"]),
                authority_revision="policy:1",
                principal="operator-1",
                permitted_projects=self.scope,
            )
        state["digest"] = "a" * 64
        state["readers"] = ["someone-else"]
        with self.assertRaises(PermissionError):
            self.co.respond_decision(
                request["id"],
                response="A",
                expected_rev=1,
                evidence_digest=digest(item["evidence"]),
                authority_revision="policy:1",
                principal="operator-1",
                permitted_projects=self.scope,
            )

    def test_project_change_invalidates_delivery_but_bookkeeping_does_not(self):
        brief = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.store.update(
            self.other_commitment["id"],
            {"objective": "Other changed"},
            self.other_commitment["rev"],
        )
        delivery = self.co.record_delivery(
            brief, principal="operator-1", permitted_projects=self.scope
        )
        self.assertIsInstance(delivery, str)
        stale = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.store.update(
            self.commitment["id"],
            {"objective": "Changed after issue"},
            self.commitment["rev"],
        )
        with self.assertRaises(Conflict):
            self.co.record_delivery(
                stale, principal="operator-1", permitted_projects=self.scope
            )

    def test_pagination_refuses_shifted_active_set(self):
        for index in range(2):
            self.store.create(
                fixture_record(
                    "Commitment",
                    project=self.project["id"],
                    objective=f"Additional {index}",
                )
            )
        first = self.co.resume(
            self.project["id"],
            principal="operator-1",
            permitted_projects=self.scope,
            obligation_limit=1,
        )
        first_record = self.store.get(first["commitments"][0]["id"])
        self.store.update(
            first_record["id"], {"state": "abandoned"}, first_record["rev"]
        )
        with self.assertRaises(Conflict):
            self.co.resume(
                self.project["id"],
                principal="operator-1",
                permitted_projects=self.scope,
                obligation_limit=1,
                obligation_offset=first["next_obligation_offset"],
                obligation_page_token=first["next_obligation_page_token"],
            )

    def test_answer_clears_open_link_and_expiry_recommends_reissue(self):
        item = self.item()
        request = self.co.prepare_decision(
            item, principal="operator-1", permitted_projects=self.scope
        )
        self.co.expire_decision(request["id"], at=future(2))
        expired = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(
            expired["recommended_next_action"], "reissue an expired decision request"
        )
        fresh = self.item() | {"dedupe_key": "interface-choice:2"}
        fresh["commitments"] = [
            {
                "id": self.commitment["id"],
                "rev": self.store.get(self.commitment["id"])["rev"],
            }
        ]
        request2 = self.co.prepare_decision(
            fresh, principal="operator-1", permitted_projects=self.scope
        )
        self.co.respond_decision(
            request2["id"],
            response="A",
            expected_rev=1,
            evidence_digest=digest(fresh["evidence"]),
            authority_revision="policy:1",
            principal="operator-1",
            permitted_projects=self.scope,
        )
        after = self.co.resume(
            self.project["id"], principal="operator-1", permitted_projects=self.scope
        )
        self.assertEqual(after["commitments"][0]["open_decision_count"], 1)
        self.assertNotIn(
            request2["id"],
            [d["id"] for d in self.store.get(self.commitment["id"])["open_decisions"]],
        )


if __name__ == "__main__":
    unittest.main()
