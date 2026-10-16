"""``pattern``'s final ``$`` means end of string (schemas README §2, "Pattern dialect")."""

from __future__ import annotations

import jsonschema.validators
import pytest

from odin_substrate import schemas

ULID = "01JAEV00000000000000000001"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("^a$", r"^a\Z"),
        (r"^a\$", r"^a\$"),
        (r"^a\\$", r"^a\\\Z"),
        ("^a", "^a"),
    ],
)
def test_anchor_end(pattern: str, expected: str) -> None:
    assert schemas.anchor_end(pattern) == expected


def test_trailing_newline_rejected_directly() -> None:
    validator = schemas.Validator({"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"})
    assert validator.is_valid(ULID)
    assert not validator.is_valid(ULID + "\n")


def test_trailing_newline_rejected_through_ref() -> None:
    s = schemas.load()
    assert s.errors(ULID + "\n", "common.schema.json#/$defs/ulid") == [""]
    event = s.load("fixtures/schema/envelope-valid.json")
    event["id"] = ULID + "\n"
    event["causation"] = ULID + "\n"
    assert s.validate_instance(event, schemas.ENVELOPE_SCHEMA)["errors"] == ["/causation", "/id"]


def test_registered_for_the_2020_12_metaschema() -> None:
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    assert jsonschema.validators.validator_for(schema) is schemas.Validator
