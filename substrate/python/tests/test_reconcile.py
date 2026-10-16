"""Restart, reconciliation, dispatch and revalidation of effects (schemas README §4.7; AC-02, AC-27)."""

from __future__ import annotations

import pytest

from odin_substrate import effects


def effect(capability: str, destination: str, state: str = "unknown", **extra) -> dict:
    return {
        "id": "01JAEF00000000000000000001",
        "destination": destination,
        "destination_capability": capability,
        "state": state,
        "owner_generation": 2,
        **extra,
    }


SAGA = ("idempotent_by_key", "saga:run.submit")


@pytest.mark.parametrize(
    ("lookup", "state_after", "retry", "extra"),
    [
        ("completed", "delivered", False, {}),
        ("pending", "unknown", False, {}),
        ("failed", "failed", False, {}),
        ("absent", "queued", True, {}),
        ("unknown_expired", "unknown", False, {"surface_to_operator": True}),
    ],
)
def test_idempotent_by_key(lookup, state_after, retry, extra) -> None:
    assert effects.reconcile(effect(*SAGA), lookup, None) == {
        "outcome": "reconciled",
        "state_after": state_after,
        "retry_allowed": retry,
        **extra,
    }


def test_superseded_is_guidance_only() -> None:
    guidance = effect("idempotent_by_key", "saga:guidance")
    assert effects.reconcile(guidance, "superseded", None) == {
        "outcome": "reconciled",
        "state_after": "superseded",
        "retry_allowed": False,
    }
    assert effects.reconcile(effect(*SAGA), "superseded", None) == {"outcome": "invalid_reconciliation_input"}


@pytest.mark.parametrize(
    ("args"),
    [
        (effect(*SAGA), None, None),
        (effect(*SAGA), "bogus", None),
        (effect(*SAGA), "completed", "host_offline"),
        (effect(*SAGA, state="queued"), "completed", None),
        (effect("irreducibly_unknown", "telegram:notify"), "completed", None),
        (effect("irreducibly_unknown", "telegram:edit"), None, None),
        (effect("surface_declared", "surface:prompt"), "absent", None),
        (effect("session_host", "session_host:start", state="queued"), None, None),
        (effect("session_host", "session_host:start", state="queued"), "completed", "host_offline"),
        (effect("session_host", "session_host:start"), "pending", "host_returned"),
        (effect("session_host", "session_host:start", state="delivered"), None, "host_offline"),
        (effect("teleport", "teleport:send"), None, None),
    ],
)
def test_invalid_inputs(args) -> None:
    assert effects.reconcile(*args) == {"outcome": "invalid_reconciliation_input"}


def test_telegram_and_surface() -> None:
    assert effects.reconcile(effect("irreducibly_unknown", "telegram:notify"), None, None)["note"] == "may have been sent"
    assert effects.reconcile(effect("irreducibly_unknown", "telegram:approval"), None, None) == {
        "outcome": "reconciled",
        "state_after": "queued",
        "retry_allowed": True,
        "same_request_id": True,
    }
    assert effects.reconcile(effect("surface_declared", "surface:prompt"), None, None)["counts_against_caps"] is True


@pytest.mark.parametrize(
    ("state", "state_after"), [("queued", "queued"), ("in_flight", "unknown"), ("unknown", "unknown")]
)
def test_session_host_offline_holds(state, state_after) -> None:
    assert effects.reconcile(effect("session_host", "session_host:start", state=state), None, "host_offline") == {
        "outcome": "reconciled",
        "state_after": state_after,
        "retry_allowed": False,
        "held_for_host": True,
    }


def test_restart_marks_in_flight_unknown_without_mutating() -> None:
    items = [
        effect(*SAGA, state="in_flight", id="01JAEF00000000000000000003"),
        effect(*SAGA, state="queued", id="01JAEF00000000000000000002"),
        effect(*SAGA, state="in_flight", id="01JAEF00000000000000000001"),
    ]
    result, updated = effects.restart(items)
    assert result == {"outcome": "restarted", "marked_unknown": ["01JAEF00000000000000000001", "01JAEF00000000000000000003"]}
    assert [e["state"] for e in updated] == ["unknown", "queued", "unknown"]
    assert items[0]["state"] == "in_flight"


def context(**overrides) -> dict:
    return {
        "current_generation": 2,
        "delegation_revoked": False,
        "assignment_state": "active",
        "approval_expired": False,
        "dispatch_blocker_active": False,
        "host_state": None,
        **overrides,
    }


def test_dispatch_order() -> None:
    queued = effect("surface_declared", "surface:prompt", state="queued")
    shadow = {"mode": "shadow"}
    stale = context(current_generation=3, delegation_revoked=True)
    assert effects.dispatch(queued, shadow, True, stale) == {"outcome": "dispatch_disabled"}
    assert effects.dispatch(queued, shadow, False, stale) == {"outcome": "dispatch_refused_shadow"}
    assert effects.dispatch(effect(*SAGA), None, False, stale) == {"outcome": "invalid_dispatch_input"}
    assert effects.dispatch(queued, {"mode": "live"}, False, context()) == {"outcome": "dispatched", "state_after": "in_flight"}
    # The blocker flag concerns held effects only.
    assert effects.dispatch(queued, None, False, context(dispatch_blocker_active=True))["outcome"] == "dispatched"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"current_generation": 3, "delegation_revoked": True}, "owner_generation"),
        ({"delegation_revoked": True, "approval_expired": True}, "delegation_revoked"),
        ({"assignment_state": "cancelled"}, "assignment_state"),
        ({"approval_expired": True}, "approval_expired"),
    ],
)
def test_dispatch_revalidates_authority(overrides, reason) -> None:
    queued = effect(*SAGA, state="queued")
    assert effects.dispatch(queued, None, False, context(**overrides)) == {"outcome": "cancelled_stale", "reason": reason}


def test_revalidate_first_failure_wins() -> None:
    ctx = context(current_generation=3, delegation_revoked=True, assignment_state="cancelled", approval_expired=True)
    held = effect(*SAGA, state="held")
    assert effects.revalidate(held, ctx) == {"outcome": "cancelled_stale", "reason": "owner_generation"}
    ctx["current_generation"] = 2
    assert effects.revalidate(held, ctx)["reason"] == "delegation_revoked"
    ctx["delegation_revoked"] = False
    assert effects.revalidate(held, ctx)["reason"] == "assignment_state"
    ctx["assignment_state"] = None
    assert effects.revalidate(held, ctx)["reason"] == "approval_expired"
    ctx["approval_expired"] = False
    assert effects.revalidate(held, ctx) == {"outcome": "queued"}
    assert effects.revalidate(effect(*SAGA), ctx) == {"outcome": "invalid_revalidation_input"}


def test_revalidate_keeps_held_while_blocker_applies() -> None:
    held = effect(*SAGA, state="held", dispatch_blocked_by="take_control:01JAPS00000000000000000001")
    blocked = context(dispatch_blocker_active=True)
    assert effects.revalidate(held, blocked) == {"outcome": "held"}
    # The blocker is decided before the stale checks.
    assert effects.revalidate(held, context(current_generation=3, dispatch_blocker_active=True)) == {"outcome": "held"}
    assert effects.revalidate(held, context()) == {"outcome": "queued"}
    assert effects.revalidate(effect(*SAGA, state="queued"), blocked) == {"outcome": "queued"}
    assert effects.revalidate(effect(*SAGA, state="in_flight"), blocked) == {"outcome": "invalid_revalidation_input"}
