"""In-memory inbox: intake with dedupe, processing and replay (schemas README §4.3, §4.4).

AC-01 and I/O contract §9: every inbound event is deduplicated by its
producer's dedupe key and sequence before it is recorded; recovery replays
the events still ``received``, control commands first (§9 step 3). This is
a model of the semantics only; it is not a store (X-11 is open).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .envelope import PROCESSED, RECEIVED, stream
from .kinds import KindCatalogue

ACCEPTED = "accepted"
DUPLICATE_DEDUPE_KEY = "duplicate_dedupe_key"
DUPLICATE_SEQUENCE = "duplicate_sequence"
OUTCOME_PROCESSED = "processed"
ALREADY_PROCESSED = "already_processed"
UNKNOWN_EVENT = "unknown_event"
REPLAYED = "replayed"


class Inbox:
    """Events in received order, with a cursor and a dedupe set per (namespace, producer) pair."""

    def __init__(self, kinds: KindCatalogue) -> None:
        self._kinds = kinds
        self._events: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self._cursors: dict[tuple[str, str], int | None] = {}
        self._seen: dict[tuple[str, str], set[str]] = {}
        self.duplicates_counted = 0

    @classmethod
    def from_events(cls, events: Iterable[Mapping[str, Any]], kinds: KindCatalogue) -> Inbox:
        """An inbox holding ``events`` as given, in array order, each with its own ``state`` (schemas README §4.4)."""
        inbox = cls(kinds)
        for event in events:
            inbox._insert(dict(event))
        return inbox

    def _insert(self, event: dict[str, Any]) -> None:
        if event["id"] in self._by_id:
            raise ValueError(f"event id {event['id']!r} is already in the inbox")
        self._events.append(event)
        self._by_id[event["id"]] = event

    def cursor(self, namespace: str, producer: str) -> int | None:
        """The last accepted ``source_seq`` of the pair, or ``None``."""
        return self._cursors.get((namespace, producer))

    def intake(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Intake one envelope (schemas README §4.3).

        In order: a dedupe key already seen for the pair is
        ``duplicate_dedupe_key``; a ``source_seq`` at or below the pair's
        cursor is ``duplicate_sequence``; otherwise ``accepted``, inserted as
        ``received``. Duplicates are counted and not recorded. The result
        carries the pair's ``cursor_after`` and the running
        ``duplicates_counted``.
        """
        if event["kind"] not in self._kinds:
            raise ValueError(f"intake of uncatalogued kind {event['kind']!r}")
        pair = stream(event)
        seen = self._seen.setdefault(pair, set())
        cursor = self._cursors.get(pair)
        seq = event.get("source_seq")
        if event["dedupe_key"] in seen:
            outcome = DUPLICATE_DEDUPE_KEY
        elif seq is not None and cursor is not None and seq <= cursor:
            outcome = DUPLICATE_SEQUENCE
        else:
            outcome = ACCEPTED
        if outcome == ACCEPTED:
            self._insert({**event, "state": RECEIVED})
            seen.add(event["dedupe_key"])
            if seq is not None:
                self._cursors[pair] = seq
        else:
            self.duplicates_counted += 1
        return {
            "outcome": outcome,
            "cursor_after": self._cursors.get(pair),
            "duplicates_counted": self.duplicates_counted,
        }

    def process(self, event_id: str) -> dict[str, Any]:
        """``received`` → ``processed``; idempotent on a processed event; ``unknown_event`` otherwise (schemas README §4.4)."""
        event = self._by_id.get(event_id)
        if event is None:
            return {"outcome": UNKNOWN_EVENT}
        if event["state"] == PROCESSED:
            return {"outcome": ALREADY_PROCESSED}
        event["state"] = PROCESSED
        return {"outcome": OUTCOME_PROCESSED}

    def replay(self) -> dict[str, Any]:
        """Ids of the events still ``received``: control kinds first, each group in received order (I/O contract §9 step 3)."""
        pending = [e for e in self._events if e["state"] == RECEIVED]
        control = [e["id"] for e in pending if self._kinds.is_control(e["kind"])]
        rest = [e["id"] for e in pending if not self._kinds.is_control(e["kind"])]
        return {"outcome": REPLAYED, "replay_order": control + rest}

    def events(self) -> tuple[dict[str, Any], ...]:
        """The inbox in received order (copies)."""
        return tuple(dict(e) for e in self._events)
