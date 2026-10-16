"""Strict decoding and error pointers (schemas README §4.1)."""

from __future__ import annotations

import pytest

from odin_substrate import schemas


def test_duplicate_keys_report_pointers() -> None:
    text = '{"a": 1, "a": 2, "b": {"c~/": [ {"x": 1, "x": 1} ], "c~/": 0}}'
    with pytest.raises(schemas.DuplicateKeyError) as info:
        schemas.loads_strict(text)
    assert info.value.pointers == ["/a", "/b/c~0~1"]


def test_nested_duplicate_inside_array() -> None:
    with pytest.raises(schemas.DuplicateKeyError) as info:
        schemas.loads_strict('[{"k": 1}, {"k": 1, "k": 2}]')
    assert info.value.pointers == ["/1/k"]


def test_plain_document_round_trips() -> None:
    value = schemas.loads_strict(b'{"a": [1, {"b": null}], "c": "\xc3\xa9"}')
    assert value == {"a": [1, {"b": None}], "c": "é"}
    assert type(value) is dict and type(value["a"][1]) is dict


@pytest.mark.parametrize("text", ["NaN", '{"a": Infinity}', "{", b"\xff"])
def test_non_json_is_refused(text) -> None:
    with pytest.raises(schemas.StrictDecodeError):
        schemas.loads_strict(text)


def test_duplicate_key_is_schema_invalid_before_validation() -> None:
    # The duplicate is reported alone; the unknown key is not reached.
    result = schemas.load().validate_text('{"kind": "a", "kind": "b", "nope": 1}', schemas.ENVELOPE_SCHEMA)
    assert result == {"outcome": "schema_invalid", "errors": ["/kind"]}


def test_unknown_and_missing_keys_point_at_the_key() -> None:
    s = schemas.load()
    event = s.load("fixtures/schema/envelope-valid.json")
    event["scope"]["a/b"] = "x"
    del event["state"]
    assert s.validate_instance(event, schemas.ENVELOPE_SCHEMA) == {
        "outcome": "schema_invalid",
        "errors": ["/scope/a~1b", "/state"],
    }


def test_any_of_reports_its_own_location() -> None:
    s = schemas.load()
    event = s.load("fixtures/schema/envelope-valid.json")
    event["payload"] = None
    event["payload_ref"] = None
    assert s.validate_instance(event, schemas.ENVELOPE_SCHEMA) == {"outcome": "schema_invalid", "errors": [""]}


def test_unknown_kind_only_after_schema_valid() -> None:
    s = schemas.load()
    event = s.load("fixtures/schema/envelope-valid.json")
    event["kind"] = "run.state"
    assert s.validate_instance(event, schemas.ENVELOPE_SCHEMA) == {"outcome": "unknown_kind"}
    event["wake"] = "loud"
    assert s.validate_instance(event, schemas.ENVELOPE_SCHEMA) == {"outcome": "schema_invalid", "errors": ["/wake"]}
