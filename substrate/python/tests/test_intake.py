"""Intake dedupe, processing and replay (schemas README §4.3, §4.4; AC-01, AC-27, I/O contract §9)."""

from __future__ import annotations

import pytest

from odin_substrate import intake, schemas

_counter = iter(range(1, 10_000))


def event(namespace="odin_history", producer="saga", seq=None, key=None, kind="run.state.started", state="received"):
    n = next(_counter)
    return {
        "id": f"01JAEV{n:020d}",
        "envelope": 1,
        "namespace": namespace,
        "producer": producer,
        "kind": kind,
        "scope": {},
        "source_seq": seq,
        "received_at": "2026-10-16T09:00:00Z",
        "causation": None,
        "correlation": None,
        "payload": {},
        "payload_ref": None,
        "dedupe_key": key or f"hash:{n}",
        "wake": "none",
        "state": state,
    }


@pytest.fixture
def inbox() -> intake.Inbox:
    return intake.Inbox(schemas.load().kinds)


def test_dedupe_key_checked_before_sequence(inbox) -> None:
    assert inbox.intake(event(seq=5, key="saga:5"))["outcome"] == "accepted"
    # Same key and a stale sequence: the dedupe key wins.
    assert inbox.intake(event(seq=4, key="saga:5")) == {
        "outcome": "duplicate_dedupe_key",
        "cursor_after": 5,
        "duplicates_counted": 1,
    }
    assert inbox.intake(event(seq=5, key="saga:5b")) == {
        "outcome": "duplicate_sequence",
        "cursor_after": 5,
        "duplicates_counted": 2,
    }
    assert len(inbox.events()) == 1


def test_event_without_sequence_keeps_cursor(inbox) -> None:
    inbox.intake(event(seq=7))
    assert inbox.intake(event(seq=None)) == {"outcome": "accepted", "cursor_after": 7, "duplicates_counted": 0}
    assert inbox.intake(event(seq=9))["cursor_after"] == 9  # sequences may skip


def test_state_is_per_namespace_and_producer(inbox) -> None:
    inbox.intake(event(seq=3, key="k"))
    assert inbox.intake(event(producer="bragi", seq=3, key="k"))["outcome"] == "accepted"
    assert inbox.intake(event(namespace="surface_events", seq=3, key="k"))["outcome"] == "accepted"
    assert inbox.cursor("odin_history", "saga") == 3
    assert inbox.cursor("execution_ledger", "saga") is None


def test_accepted_event_is_received(inbox) -> None:
    inbox.intake(event(state="processed"))
    assert [e["state"] for e in inbox.events()] == ["received"]


def test_unknown_kind_is_refused(inbox) -> None:
    with pytest.raises(ValueError):
        inbox.intake(event(kind="run.state"))


def test_process_and_replay_control_first() -> None:
    kinds = schemas.load().kinds
    plain = event()
    ret = event(kind="operator.command.return", producer="operator:terminal")
    done = event(kind="operator.command.stop", state="processed")
    take = event(kind="operator.command.take", producer="operator:terminal")
    inbox = intake.Inbox.from_events([plain, ret, done, take], kinds)
    assert inbox.replay() == {"outcome": "replayed", "replay_order": [ret["id"], take["id"], plain["id"]]}
    assert inbox.process(ret["id"]) == {"outcome": "processed"}
    assert inbox.process(ret["id"]) == {"outcome": "already_processed"}
    assert inbox.process(done["id"]) == {"outcome": "already_processed"}
    assert inbox.process("01JAEV99999999999999999999") == {"outcome": "unknown_event"}
    assert inbox.replay()["replay_order"] == [take["id"], plain["id"]]


def test_control_kinds_are_the_five_direct_commands() -> None:
    assert schemas.load().kinds.control_kinds == {
        f"operator.command.{c}" for c in ("stop", "pause", "revoke", "take", "return")
    }
