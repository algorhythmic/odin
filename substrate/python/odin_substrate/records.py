"""Revision, ownership, operation and message checks; review combination (schemas README §4.5, §4.6).

Records are plain dicts shaped by ``records/*.schema.json`` (I/O contract
§2, Appendix A). The functions here are pure: they return results (and,
where a write happens, updated copies) and never mutate their inputs.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

OK = "ok"
STALE_REVISION = "stale_revision"
EXPECTED_REVISION_REQUIRED = "expected_revision_required"
STALE_OWNER = "stale_owner"
TRANSFERRED = "transferred"
OPERATION_CONFLICT = "operation_conflict"
OPERATION_IDEMPOTENT = "operation_idempotent"
SIZE_MISMATCH = "size_mismatch"

APPROVED = "approved"
ESCALATED = "escalated"
PENDING = "pending"
RE_REVIEW = "re_review"

APPROVING = frozenset({"APPROVE", "APPROVE_UNCHANGED"})
ESCALATING = frozenset({"REJECT", "INSUFFICIENT_EVIDENCE"})

_MISSING = object()


def check_revision(record_rev: int, expected_revision: int | None | object = _MISSING) -> dict[str, Any]:
    """Optimistic concurrency check (I/O contract §2; schemas README §4.5).

    ``expected_revision`` missing or ``None`` is ``expected_revision_required``;
    equal to ``record_rev`` is ``ok``; any other value is ``stale_revision``
    (the 409; nothing changes).
    """
    if expected_revision is _MISSING or expected_revision is None:
        return {"outcome": EXPECTED_REVISION_REQUIRED}
    if expected_revision == record_rev:
        return {"outcome": OK}
    return {"outcome": STALE_REVISION}


def check_owner(session: Mapping[str, Any], commitment: Mapping[str, Any]) -> dict[str, Any]:
    """Ownership check of a planning session against a commitment (I/O contract §2, §9; schemas README §4.5).

    A ``retired`` session, or one whose ``ownership_generation`` differs
    from the commitment's, is ``stale_owner``; a ``retiring`` session at the
    current generation is ``ok``.
    """
    if session["state"] == "retired":
        return {"outcome": STALE_OWNER}
    if session["ownership_generation"] != commitment["ownership_generation"]:
        return {"outcome": STALE_OWNER}
    return {"outcome": OK}


@dataclass
class Transfer:
    """The result of :func:`commitment_transfer` and, when transferred, the updated records."""

    result: dict[str, Any]
    commitment: dict[str, Any] | None = None
    effects: list[dict[str, Any]] = field(default_factory=list)


def commitment_transfer(
    commitment: Mapping[str, Any],
    new_owner: str,
    effects: Iterable[Mapping[str, Any]],
    expected_revision: int | None | object = _MISSING,
    now: str | None = None,
) -> Transfer:
    """Ownership transfer of a commitment (I/O contract §2, §9; schemas README §4.5).

    First the revision check against ``commitment["rev"]``; a failure is
    returned alone. Otherwise the generation and ``rev`` each go up by one,
    the owner becomes ``new_owner``, and every ``queued`` or ``held`` effect
    whose non-null ``owner_generation`` is below the new generation becomes
    ``held`` with ``dispatch_blocked_by = "ownership_transfer:<commitment id>"``
    (revalidated later, §4.7). ``now``, when given, becomes ``updated_at``.
    """
    revision = check_revision(commitment["rev"], expected_revision)
    if revision["outcome"] != OK:
        return Transfer(result=revision)
    generation_after = commitment["ownership_generation"] + 1
    rev_after = commitment["rev"] + 1
    updated = copy.deepcopy(dict(commitment))
    updated.update(owner=new_owner, ownership_generation=generation_after, rev=rev_after)
    if now is not None:
        updated["updated_at"] = now
    blocker = f"ownership_transfer:{commitment['id']}"
    held: list[str] = []
    out_effects: list[dict[str, Any]] = []
    for effect in effects:
        effect = copy.deepcopy(dict(effect))
        generation = effect.get("owner_generation")
        if effect["state"] in ("queued", "held") and generation is not None and generation < generation_after:
            effect["state"] = "held"
            effect["dispatch_blocked_by"] = blocker
            held.append(effect["id"])
        out_effects.append(effect)
    result = {
        "outcome": TRANSFERRED,
        "generation_after": generation_after,
        "rev_after": rev_after,
        "held_effects": sorted(held),
    }
    return Transfer(result=result, commitment=updated, effects=out_effects)


def operation_reuse(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse of an operation id (I/O contract §9; schemas README §4.5).

    A different ``payload_digest`` under the same ``operation_id`` is
    ``operation_conflict`` (the 409); the same digest is
    ``operation_idempotent``.
    """
    if existing["operation_id"] != incoming["operation_id"]:
        raise ValueError("operation_reuse compares effects with the same operation_id")
    if existing["payload_digest"] != incoming["payload_digest"]:
        return {"outcome": OPERATION_CONFLICT}
    return {"outcome": OPERATION_IDEMPOTENT}


def check_message_size(message: Mapping[str, Any]) -> dict[str, Any]:
    """A Message's ``size`` must equal the UTF-8 byte length of its ``text`` (I/O contract §3; schemas README §4.5)."""
    if message["size"] == len(message["text"].encode("utf-8")):
        return {"outcome": OK}
    return {"outcome": SIZE_MISMATCH}


def _position_result(position: Mapping[str, Any]) -> str | None:
    verdict = position.get("verdict")
    return None if verdict is None else verdict["result"]


def combine(positions: Sequence[Mapping[str, Any]], round: int) -> dict[str, Any]:
    """Combine two reviewer positions (§10 review, ODIN-ADR-013, AC-22, AC-40; schemas README §4.6).

    First matching rule: any position without a verdict (including an
    unavailable one) is ``pending``; any ``REJECT`` or
    ``INSUFFICIENT_EVIDENCE`` is ``escalated``; both approving is
    ``approved`` with ``verdict_result`` ``APPROVE_UNCHANGED`` only when both
    are unchanged; otherwise ``re_review`` in round 1 and ``escalated`` in
    round 2.
    """
    if len(positions) != 2:
        raise ValueError("a review combines exactly two positions")
    if round not in (1, 2):
        raise ValueError("a review has round 1 or 2")
    results = [_position_result(p) for p in positions]
    if any(r is None for r in results):
        return {"outcome": PENDING}
    if any(r in ESCALATING for r in results):
        return {"outcome": ESCALATED}
    if all(r in APPROVING for r in results):
        unchanged = all(r == "APPROVE_UNCHANGED" for r in results)
        return {"outcome": APPROVED, "verdict_result": "APPROVE_UNCHANGED" if unchanged else "APPROVE"}
    return {"outcome": RE_REVIEW if round == 1 else ESCALATED}
