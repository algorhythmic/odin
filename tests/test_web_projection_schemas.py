"""Draft schemas for the Odin web app projection, checked against the synthetic prototype.

The schemas describe the shapes the prototype uses (ODIN-ADR-037; see
docs/design/WEB-APP-PROJECTION.md). They are not an accepted contract. No
service, credential or network is involved.
"""

import copy
import math
import unittest
from pathlib import Path

from odin.contracts import Contracts, strict_loads

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "fixtures"
SCHEMAS = ROOT / "schemas"

FIXTURE_SCHEMAS = {
    "default-snapshot.json": "web-projection-snapshot",
    "default-details.json": "web-projection-details-fixture",
    "default-events.json": "web-projection-events-fixture",
}

PROJECTION_SCHEMAS = {
    "web-projection-snapshot",
    "web-projection-session-detail",
    "web-projection-details-fixture",
    "web-projection-event",
    "web-projection-events-fixture",
}

# default-events.json in delivery order: (position, event_id) for every event
# the event schema must reject. Schema-valid referential cases are listed below.
SCHEMA_INVALID_EVENTS = [
    (6, "evt-bad-2"),   # unknown event type
    (7, "evt-bad-3"),   # non-integer revision
    (8, "evt-bad-4"),   # session.started without a session record
    (10, "evt-bad-6"),  # lifecycle "paused", first delivery
    (11, "evt-bad-7"),  # no session_id
    (12, "evt-bad-8"),  # numeric session id
]
SCHEMA_VALID_EVENTS = [
    (5, "evt-bad-1"),   # session not in the snapshot (referential)
    (9, "evt-bad-5"),   # session already exists (referential)
    (13, "evt-bad-9"),  # project not in the snapshot (referential)
    (14, "evt-bad-6"),  # corrected re-delivery under the same id
]


class ProjectionSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contracts = Contracts()

    def load(self, name):
        return strict_loads((FIXTURES / name).read_text())

    def schema_file(self, name):
        return strict_loads((SCHEMAS / f"{name}.schema.json").read_text())

    def validator(self, name):
        return self.contracts.validators[name]

    def snapshot_with_session(self, **changes):
        snapshot = self.load("default-snapshot.json")
        snapshot["sessions"][0].update(changes)
        return snapshot

    def test_fixtures_are_mapped_and_valid(self):
        names = sorted(path.name for path in FIXTURES.glob("*.json"))
        self.assertEqual(names, sorted(FIXTURE_SCHEMAS), "fixture file without a schema mapping")
        for name, schema in FIXTURE_SCHEMAS.items():
            with self.subTest(fixture=name):
                self.contracts.validate(schema, self.load(name))

    def test_session_detail_pages_match_loader(self):
        snapshot = self.load("default-snapshot.json")
        details = self.load("default-details.json")
        size = details["page_size"]
        checked = 0
        pages_by_session = {}
        for session in snapshot["sessions"]:
            sid = session["id"]
            # loadSessionDetail uses `||`: an empty stored list is still truthy in JS, so
            # membership decides here, not truthiness.
            if sid in details["transcripts"]:
                items = details["transcripts"][sid]
            else:
                items = [{"seq": 1, "at": session["observed_at"], "speaker": sid,
                          "text": f"Synthetic transcript entry for {sid}."}]
            pages = max(1, math.ceil(len(items) / size))
            pages_by_session[sid] = pages
            evidence = details["evidence"].get(sid, [])
            for page in range(1, pages + 1):
                response = {
                    "session_id": sid,
                    "page": page,
                    "pages": pages,
                    "page_size": size,
                    "transcript": items[(page - 1) * size: page * size],
                    "evidence": evidence,
                }
                with self.subTest(session=sid, page=page):
                    self.contracts.validate("web-projection-session-detail", response)
                    self.assertLessEqual(page, pages)
                checked += 1
        self.assertEqual(pages_by_session["ses-worker-a2"], 2)
        self.assertEqual(checked, sum(pages_by_session.values()))
        self.assertGreaterEqual(checked, len(snapshot["sessions"]))

    def test_event_partition_by_position(self):
        events = self.load("default-events.json")["events"]
        self.assertEqual(len(events), 16)
        event_schema = self.validator("web-projection-event")
        invalid = [(i, e["event_id"]) for i, e in enumerate(events) if not event_schema.is_valid(e)]
        self.assertEqual(invalid, SCHEMA_INVALID_EVENTS)
        for position, event_id in SCHEMA_VALID_EVENTS:
            self.assertEqual(events[position]["event_id"], event_id)
            self.assertTrue(event_schema.is_valid(events[position]), event_id)

    def test_snapshot_rejects_extra_top_level_key(self):
        schema = self.validator("web-projection-snapshot")
        snapshot = self.load("default-snapshot.json")
        self.assertTrue(schema.is_valid(snapshot))
        snapshot["unexpected"] = True
        self.assertFalse(schema.is_valid(snapshot))

    def test_session_requires_parent_session_id(self):
        schema = self.validator("web-projection-snapshot")
        snapshot = self.load("default-snapshot.json")
        del snapshot["sessions"][0]["parent_session_id"]
        self.assertFalse(schema.is_valid(snapshot))
        self.assertTrue(schema.is_valid(self.snapshot_with_session(parent_session_id="ses-x")))

    def test_tokens_counters_and_basis_are_paired(self):
        schema = self.validator("web-projection-snapshot")

        def tokens(u=None, cr=None, cw=None, o=None, basis="unknown", drop=None):
            record = {"uncached_input": u, "cache_read": cr,
                      "cache_write": cw, "output": o, "basis": basis}
            for key in drop or ():
                del record[key]
            return record

        cases = [
            (tokens(), True),                                        # all null, unknown
            (tokens(u=9000, cr=120000, cw=21000, o=12200, basis="measured"), True),
            (tokens(u=8100, cr=64000, cw=5900, o=4700, basis="estimate"), True),
            (tokens(u=0, cr=0, cw=0, o=0, basis="measured"), True),  # zero is a count, not unknown
            (tokens(basis="measured"), False),                       # null counters mean unknown
            (tokens(u=9000, cr=120000, cw=21000, o=12200), False),   # known counters must not say unknown
            (tokens(u=9000, cr=None, cw=21000, o=12200, basis="measured"), False),  # half-null
            (tokens(u=-1, cr=120000, cw=21000, o=12200, basis="measured"), False),  # negative
            (tokens(u=1.5, cr=120000, cw=21000, o=12200, basis="measured"), False),  # non-integer
            (tokens(u=9000, cr=120000, cw=21000, o=12200, basis="measured", drop=("output",)), False),  # missing field
        ]
        for tokens_record, expected in cases:
            with self.subTest(tokens=tokens_record):
                self.assertEqual(schema.is_valid(self.snapshot_with_session(tokens=tokens_record)), expected)

    def test_lifecycle_is_closed(self):
        schema = self.validator("web-projection-snapshot")
        self.assertFalse(schema.is_valid(self.snapshot_with_session(lifecycle="paused")))
        self.assertTrue(schema.is_valid(self.snapshot_with_session(lifecycle="host_offline")))

    def test_detail_definitions_are_identical(self):
        detail = self.schema_file("web-projection-session-detail")
        fixture = self.schema_file("web-projection-details-fixture")
        for name in ("transcript_item", "evidence"):
            with self.subTest(definition=name):
                self.assertEqual(detail["$defs"][name], fixture["$defs"][name])

    def test_event_session_definition_matches_snapshot(self):
        snapshot = self.schema_file("web-projection-snapshot")
        event = self.schema_file("web-projection-event")
        self.assertEqual(event["$defs"]["session"], snapshot["$defs"]["session"])

    def test_projection_schemas_are_marked_draft(self):
        names = {path.name.removesuffix(".schema.json") for path in SCHEMAS.glob("web-projection-*.schema.json")}
        self.assertEqual(names, PROJECTION_SCHEMAS)
        for name in sorted(names):
            with self.subTest(schema=name):
                document = self.schema_file(name)
                self.assertTrue(document.get("$comment", "").startswith("DRAFT"))
                self.assertTrue(document.get("title"))


if __name__ == "__main__":
    unittest.main()
