"""The event-kind catalogue, ``kinds.json`` (schemas README §5; I/O contract Appendix C).

Each kind carries its default wake class, whether the wake is conditional,
its handling, and the ``control`` flag that marks the direct commands
recovery replays first (I/O contract §9 step 3; schemas README §4.4).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Kind:
    """One catalogue entry (``kinds.schema.json``)."""

    kind: str
    default_wake: str
    conditional: bool
    handling: str
    control: bool
    source: str


class KindCatalogue:
    """The kinds of ``kinds.json``; the catalogue is the ``unknown_kind`` check (schemas README §4.1 step 3)."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self.version: int = data["version"]
        self._kinds: dict[str, Kind] = {}
        for entry in data["kinds"]:
            kind = Kind(
                kind=entry["kind"],
                default_wake=entry["default_wake"],
                conditional=entry["conditional"],
                handling=entry["handling"],
                control=entry["control"],
                source=entry["source"],
            )
            if kind.kind in self._kinds:
                raise ValueError(f"kinds.json lists {kind.kind!r} twice")
            self._kinds[kind.kind] = kind
        self.control_kinds: frozenset[str] = frozenset(
            k.kind for k in self._kinds.values() if k.control
        )

    def __contains__(self, kind: object) -> bool:
        return kind in self._kinds

    def __iter__(self) -> Iterator[Kind]:
        return iter(self._kinds.values())

    def __len__(self) -> int:
        return len(self._kinds)

    def get(self, kind: str) -> Kind | None:
        """Return the entry for ``kind``, or ``None`` when it is not catalogued."""
        return self._kinds.get(kind)

    def is_control(self, kind: str) -> bool:
        """Return whether ``kind`` is a control command replayed first (I/O contract §9 step 3)."""
        return kind in self.control_kinds
