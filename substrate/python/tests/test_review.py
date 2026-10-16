"""Review combination of two reviewer positions (schemas README §4.6; §10 review, ODIN-ADR-013, AC-22, AC-40)."""

from __future__ import annotations

import pytest

from odin_substrate import records


def pos(name: str, result: str | None) -> dict:
    verdict = None if result is None else {"result": result, "checklist": {}, "findings": []}
    return {"position": name, "verdict": verdict}


@pytest.mark.parametrize(
    ("round_", "a", "b", "expected"),
    [
        (1, "APPROVE", "APPROVE", {"outcome": "approved", "verdict_result": "APPROVE"}),
        (1, "APPROVE_UNCHANGED", "APPROVE_UNCHANGED", {"outcome": "approved", "verdict_result": "APPROVE_UNCHANGED"}),
        (2, "APPROVE_UNCHANGED", "APPROVE", {"outcome": "approved", "verdict_result": "APPROVE"}),
        (1, "APPROVE", "REJECT", {"outcome": "escalated"}),
        (1, "INSUFFICIENT_EVIDENCE", "FLAG", {"outcome": "escalated"}),
        (1, None, "REJECT", {"outcome": "escalated"}),
        (1, "INSUFFICIENT_EVIDENCE", None, {"outcome": "escalated"}),
        (1, None, "APPROVE", {"outcome": "pending"}),
        (1, "FLAG", None, {"outcome": "pending"}),
        (2, None, None, {"outcome": "pending"}),
        (1, "APPROVE", "FLAG", {"outcome": "re_review"}),
        (2, "APPROVE", "FLAG", {"outcome": "escalated"}),
        (1, "FLAG", "FLAG", {"outcome": "escalated"}),
        (2, "FLAG", "FLAG", {"outcome": "escalated"}),
    ],
)
def test_combine_rules(round_, a, b, expected) -> None:
    assert records.combine([pos("a", a), pos("b", b)], round_) == expected


@pytest.mark.parametrize(
    ("positions", "round_"),
    [
        ([], 1),
        ([pos("a", "APPROVE")], 1),
        ([pos("a", "APPROVE"), pos("b", "APPROVE"), pos("b", "APPROVE")], 1),
        ([pos("a", "APPROVE"), pos("a", "APPROVE")], 1),
        ([{"verdict": None}, pos("b", "APPROVE")], 1),
        ([pos("a", "APPROVE"), pos("b", "APPROVE")], 3),
        ([pos("a", "APPROVE"), pos("b", "MAYBE")], 1),
    ],
)
def test_combine_refuses_other_than_a_and_b(positions, round_) -> None:
    with pytest.raises(ValueError):
        records.combine(positions, round_)


def test_combine_accepts_b_before_a() -> None:
    assert records.combine([pos("b", "APPROVE"), pos("a", "APPROVE")], 1)["outcome"] == "approved"
