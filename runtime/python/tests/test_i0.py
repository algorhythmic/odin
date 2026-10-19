from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from odin_runtime import (SchemaValidator, StrictJSONError, check_ownership,
                          check_revision, classify_intake, load_json_strict,
                          reconcile_operation)
from odin_runtime.validation import valid_ulid, valid_utc_timestamp


class ContractChecks(unittest.TestCase):
    def test_intake_accepts_non_dense_sequence_and_deduplicates(self) -> None:
        self.assertEqual(classify_intake(4, 100, False), "new")
        self.assertEqual(classify_intake(100, 100, False), "duplicate")
        self.assertEqual(classify_intake(100, 99, False), "duplicate")
        self.assertEqual(classify_intake(None, None, True), "duplicate")
        self.assertEqual(classify_intake(None, None, False), "new")

    def test_revision_and_owner_are_exact(self) -> None:
        self.assertEqual(check_revision(3, 3), "ok")
        self.assertEqual(check_revision(2, 3), "stale_revision")
        self.assertEqual(check_ownership(2, 2), "ok")
        self.assertEqual(check_ownership(1, 2), "stale_owner")
        with self.assertRaises(ValueError):
            check_revision(True, 1)
        with self.assertRaises(ValueError):
            check_revision(2**53, 1)
        with self.assertRaises(ValueError):
            check_ownership(1, 2**53)
        with self.assertRaises(ValueError):
            classify_intake(0, 2**53, False)

    def test_unknown_expired_and_superseded_are_never_retried(self) -> None:
        self.assertEqual(reconcile_operation("unknown_expired"), ("unknown", "surface_to_operator"))
        self.assertEqual(reconcile_operation("superseded"), ("superseded", "none"))
        self.assertEqual(reconcile_operation("absent"), ("unknown", "retry_after_revalidation"))
        self.assertEqual(reconcile_operation("pending"), ("unknown", "wait"))


class SchemaChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="odin-python-i0-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.schemas = self.root / "schemas"
        self.schemas.mkdir()
        common = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://odin.invalid/schemas/v1/common.schema.json",
            "$defs": {"id": {"type": "string", "format": "ulid"}},
        }
        record = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://odin.invalid/schemas/v1/record.schema.json",
            "type": "object", "required": ["id", "at"],
            "properties": {"id": {"$ref": "common.schema.json#/$defs/id"},
                           "at": {"type": "string", "format": "date-time"}},
            "additionalProperties": False,
        }
        (self.schemas / "common.schema.json").write_text(json.dumps(common))
        (self.schemas / "record.schema.json").write_text(json.dumps(record))

    def test_strict_json_rejects_duplicate_keys_numeric_loss_and_bad_unicode(self) -> None:
        path = self.root / "payload.json"
        for content in ('{"id":1,"id":2}', '{"x":NaN}', '{"x":Infinity}',
                        '{"x":1e999}', '{"x":9007199254740993}',
                        '{"x":9007199254740993.0}',
                        '{"x":1.0000000000000001}', '{"x":1e-9999}',
                        '{"x":"\\ud800"}', '{"\\ud800":"key"}'):
            path.write_text(content)
            with self.assertRaises(StrictJSONError):
                load_json_strict(path)
        path.write_bytes(b'{"x":"\xff"}')
        with self.assertRaises(StrictJSONError):
            load_json_strict(path)
        path.write_text('{"x":9007199254740991}')
        self.assertEqual(load_json_strict(path), {"x": 9007199254740991})
        path.write_text('{"budget_usd":0.1,"emoji":"\\ud83d\\ude00"}')
        self.assertEqual(load_json_strict(path), {"budget_usd": 0.1, "emoji": "😀"})

    def test_local_reference_and_format_assertions(self) -> None:
        validator = SchemaValidator(self.schemas)
        good = {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAV", "at": "2026-10-16T01:02:03.123Z"}
        self.assertTrue(validator.validate("record.schema.json", good))
        self.assertFalse(validator.validate("record.schema.json", {**good, "id": "0" * 26}))
        self.assertFalse(validator.validate("record.schema.json", {**good, "at": "2026-02-30T01:02:03Z"}))
        self.assertFalse(validator.validate("record.schema.json", {**good, "at": "2026-10-16T01:02:03+00:00"}))
        self.assertFalse(valid_ulid("8" + good["id"][1:]))
        self.assertFalse(valid_utc_timestamp("2026-10-16T01:02:03-07:00"))

    def test_remote_reference_is_rejected_before_validation(self) -> None:
        remote = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "properties": {"id": {"$ref": "https://example.com/schema.json"}}}
        (self.schemas / "remote.schema.json").write_text(json.dumps(remote))
        with self.assertRaisesRegex(ValueError, "nonlocal schema reference"):
            SchemaValidator(self.schemas)


if __name__ == "__main__":
    unittest.main()
