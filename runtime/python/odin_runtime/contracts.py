"""Pure I0 checks; callers must make state changes atomically in later increments."""

from __future__ import annotations

from typing import Literal

MAX_SAFE_INTEGER = 2**53 - 1


def classify_intake(last_sequence: int | None, incoming_sequence: int | None, dedupe_seen: bool) -> Literal["new", "duplicate"]:
    """Classify one event without assuming producer sequences are dense."""
    if last_sequence is not None and (type(last_sequence) is not int or not 0 <= last_sequence <= MAX_SAFE_INTEGER):
        raise ValueError("last_sequence must be a safe nonnegative integer or None")
    if incoming_sequence is not None and (type(incoming_sequence) is not int or not 0 <= incoming_sequence <= MAX_SAFE_INTEGER):
        raise ValueError("incoming_sequence must be a safe nonnegative integer or None")
    if type(dedupe_seen) is not bool:
        raise ValueError("dedupe_seen must be boolean")
    if dedupe_seen or (last_sequence is not None and incoming_sequence is not None and incoming_sequence <= last_sequence):
        return "duplicate"
    return "new"


def check_revision(expected: int, actual: int) -> Literal["ok", "stale_revision"]:
    """A dependent write may proceed only against its exact current revision."""
    if (type(expected) is not int or type(actual) is not int
            or not 1 <= expected <= MAX_SAFE_INTEGER or not 1 <= actual <= MAX_SAFE_INTEGER):
        raise ValueError("revisions must be positive safe integers")
    return "ok" if expected == actual else "stale_revision"


def check_ownership(expected_generation: int, actual_generation: int) -> Literal["ok", "stale_owner"]:
    """A session's captured ownership generation must still be current."""
    if (type(expected_generation) is not int or type(actual_generation) is not int
            or not 1 <= expected_generation <= MAX_SAFE_INTEGER
            or not 1 <= actual_generation <= MAX_SAFE_INTEGER):
        raise ValueError("ownership generations must be positive safe integers")
    return "ok" if expected_generation == actual_generation else "stale_owner"


def reconcile_operation(status: str) -> tuple[str, str]:
    """Return (effect state, next action) for a Saga operation lookup.

    A retry decision is only made for confirmed absence within retention.
    The caller still has to revalidate authority and reuse the operation ID.
    """
    outcomes = {
        "completed": ("delivered", "none"),
        "pending": ("unknown", "wait"),
        "failed": ("failed", "none"),
        "superseded": ("superseded", "none"),
        "absent": ("unknown", "retry_after_revalidation"),
        "unknown_expired": ("unknown", "surface_to_operator"),
    }
    try:
        return outcomes[status]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown operation status: {status!r}") from exc
