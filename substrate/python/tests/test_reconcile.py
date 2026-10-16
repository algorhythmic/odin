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
        ("superseded", "superseded", False, {}),
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


@pytest.mark.parametrize("state", ["queued", "in_flight", "unknown"])
def test_session_host_offline_keeps_state(state) -> None:
    assert effects.reconcile(effect("session_host", "session_host:start", state=state), None, "host_offline") == {
        "outcome": "reconciled",
        "state_after": state,
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


def test_dispatch_order() -> None:
    queued = effect("surface_declared", "surface:prompt", state="queued")
    shadow = {"mode": "shadow"}
    assert effects.dispatch(queued, shadow, True) == {"outcome": "dispatch_disabled"}
    assert effects.dispatch(queued, shadow, False) == {"outcome": "dispatch_refused_shadow"}
    assert effects.dispatch(effect(*SAGA), None, False) == {"outcome": "invalid_dispatch_input"}
    assert effects.dispatch(queued, {"mode": "live"}, False) == {"outcome": "dispatched", "state_after": "in_flight"}


def test_revalidate_first_failure_wins() -> None:
    ctx = {
        "current_generation": 3,
        "delegation_revoked": True,
        "assignment_state": "cancelled",
        "approval_expired": True,
        "host_state": None,
    }
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
