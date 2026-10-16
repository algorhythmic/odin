"""Effects: restart, reconciliation, dispatch and revalidation (AC-02, AC-27, I/O contract §9; schemas README §4.7).

Effects are at-least-once with stable operation ids and an explicit
``unknown`` state; reconciliation decides, per destination capability,
what may be retried. Nothing here claims exactly-once, and nothing is sent:
these functions compute outcomes over Effect records (plain dicts).
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

RESTARTED = "restarted"
RECONCILED = "reconciled"
INVALID_RECONCILIATION_INPUT = "invalid_reconciliation_input"
DISPATCHED = "dispatched"
DISPATCH_DISABLED = "dispatch_disabled"
DISPATCH_REFUSED_SHADOW = "dispatch_refused_shadow"
INVALID_DISPATCH_INPUT = "invalid_dispatch_input"
QUEUED = "queued"
CANCELLED_STALE = "cancelled_stale"
INVALID_REVALIDATION_INPUT = "invalid_revalidation_input"

_INVALID_RECONCILIATION = {"outcome": INVALID_RECONCILIATION_INPUT}

# idempotent_by_key (Saga): lookup -> (state_after, retry_allowed, extra keys).
_IDEMPOTENT_BY_KEY: dict[str, tuple[str, bool, dict[str, Any]]] = {
    "completed": ("delivered", False, {}),
    "pending": ("unknown", False, {}),
    "failed": ("failed", False, {}),
    "superseded": ("superseded", False, {}),
    "absent": ("queued", True, {}),
    "unknown_expired": ("unknown", False, {"surface_to_operator": True}),
}

# irreducibly_unknown (Telegram): operation -> (state_after, retry_allowed, extra keys).
_IRREDUCIBLY_UNKNOWN: dict[str, tuple[str, bool, dict[str, Any]]] = {
    "notify": ("unknown", False, {"note": "may have been sent"}),
    "request": ("queued", True, {"same_request_id": True}),
    "approval": ("queued", True, {"same_request_id": True}),
}

# session_host after host_returned: the host's report -> (state_after, retry_allowed).
_HOST_RETURNED: dict[str, tuple[str, bool]] = {
    "completed": ("delivered", False),
    "absent": ("queued", True),
}

_TERMINAL_ASSIGNMENT_STATES = frozenset({"cancelled", "completed", "failed"})


def _reconciled(state_after: str, retry: bool, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"outcome": RECONCILED, "state_after": state_after, "retry_allowed": retry, **(extra or {})}


def restart(effects: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Service restart: every ``in_flight`` effect becomes ``unknown`` (I/O contract §9; schemas README §4.7).

    Returns the result ``{"outcome": "restarted", "marked_unknown": [sorted ids]}``
    and updated copies of the effects.
    """
    marked: list[str] = []
    updated: list[dict[str, Any]] = []
    for effect in effects:
        effect = copy.deepcopy(dict(effect))
        if effect["state"] == "in_flight":
            effect["state"] = "unknown"
            marked.append(effect["id"])
        updated.append(effect)
    return {"outcome": RESTARTED, "marked_unknown": sorted(marked)}, updated


def reconcile(effect: Mapping[str, Any], lookup: str | None, host_state: str | None) -> dict[str, Any]:
    """Reconcile an effect against its destination's answer (AC-02; I/O contract §9 outbox table; schemas README §4.7).

    The rule depends on ``destination_capability``; any input outside the
    rule's row is ``invalid_reconciliation_input``. A valid reconciliation
    is ``reconciled`` with ``state_after``, ``retry_allowed`` and only the
    extra keys its row names.
    """
    capability = effect.get("destination_capability")
    state = effect.get("state")
    if capability == "idempotent_by_key":
        if state != "unknown" or host_state is not None or lookup not in _IDEMPOTENT_BY_KEY:
            return dict(_INVALID_RECONCILIATION)
        return _reconciled(*_IDEMPOTENT_BY_KEY[lookup])
    if capability == "irreducibly_unknown":
        if state != "unknown" or lookup is not None or host_state is not None:
            return dict(_INVALID_RECONCILIATION)
        _, _, operation = effect["destination"].partition(":")
        if operation not in _IRREDUCIBLY_UNKNOWN:
            return dict(_INVALID_RECONCILIATION)
        return _reconciled(*_IRREDUCIBLY_UNKNOWN[operation])
    if capability == "surface_declared":
        if state != "unknown" or lookup is not None or host_state is not None:
            return dict(_INVALID_RECONCILIATION)
        return _reconciled("unknown", False, {"counts_against_caps": True})
    if capability == "session_host":
        if state not in ("queued", "in_flight", "unknown"):
            return dict(_INVALID_RECONCILIATION)
        if host_state == "host_offline" and lookup is None:
            return _reconciled(state, False, {"held_for_host": True})
        if host_state == "host_returned" and lookup in _HOST_RETURNED:
            return _reconciled(*_HOST_RETURNED[lookup])
        return dict(_INVALID_RECONCILIATION)
    return dict(_INVALID_RECONCILIATION)


def dispatch(
    effect: Mapping[str, Any], prompt: Mapping[str, Any] | None, recovery_in_progress: bool
) -> dict[str, Any]:
    """Dispatch decision (I/O contract §9 steps 4 and 8, ODIN-ADR-010; schemas README §4.7).

    In order: during recovery ``dispatch_disabled``; a shadow-mode
    attention prompt ``dispatch_refused_shadow``; an effect not ``queued``
    ``invalid_dispatch_input``; otherwise ``dispatched`` to ``in_flight``.
    """
    if recovery_in_progress:
        return {"outcome": DISPATCH_DISABLED}
    if prompt is not None and prompt.get("mode") == "shadow":
        return {"outcome": DISPATCH_REFUSED_SHADOW}
    if effect.get("state") != "queued":
        return {"outcome": INVALID_DISPATCH_INPUT}
    return {"outcome": DISPATCHED, "state_after": "in_flight"}


def revalidate(effect: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    """Revalidation before dispatch (AC-27; I/O contract §9 step 4; schemas README §4.7).

    Only ``queued`` and ``held`` effects are revalidated. The first failing
    check, in the order owner generation, delegation revoked, assignment
    state, approval expired, gives ``cancelled_stale`` with that ``reason``;
    otherwise ``queued``. ``host_state`` is not consulted in I0.
    """
    if effect.get("state") not in ("queued", "held"):
        return {"outcome": INVALID_REVALIDATION_INPUT}
    generation = effect.get("owner_generation")
    if generation is not None and generation < context["current_generation"]:
        reason = "owner_generation"
    elif context["delegation_revoked"]:
        reason = "delegation_revoked"
    elif context["assignment_state"] in _TERMINAL_ASSIGNMENT_STATES:
        reason = "assignment_state"
    elif context["approval_expired"]:
        reason = "approval_expired"
    else:
        return {"outcome": QUEUED}
    return {"outcome": CANCELLED_STALE, "reason": reason}
