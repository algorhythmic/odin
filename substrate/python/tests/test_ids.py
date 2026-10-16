"""ULID validation and minting (schemas README §2, common $defs ``ulid``)."""

from __future__ import annotations

from odin_substrate import ids, schemas


def test_mint_is_valid_and_sortable() -> None:
    a = ids.mint(timestamp_ms=1_700_000_000_000)
    b = ids.mint(timestamp_ms=1_700_000_000_001)
    assert ids.is_valid(a) and ids.is_valid(b)
    assert a < b
    assert ids.timestamp_ms(a) == 1_700_000_000_000


def test_mint_deterministic_parts() -> None:
    assert ids.mint(timestamp_ms=0, randomness=bytes(10)) == "0" * 26
    top = ids.mint(timestamp_ms=(1 << 48) - 1, randomness=b"\xff" * 10)
    assert top == "7" + "Z" * 25


def test_mint_now_matches_schema() -> None:
    validator = schemas.load().validator("common.schema.json#/$defs/ulid")
    for _ in range(50):
        assert validator.is_valid(ids.mint())


def test_is_valid_rejects() -> None:
    good = "01JAEV00000000000000000001"
    assert ids.is_valid(good)
    for bad in (good + "\n", good.lower(), good[:-1], good + "0", "01JAEV0000000000000000000I", 1, None):
        assert not ids.is_valid(bad), bad
