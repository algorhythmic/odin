"""Namespaces and their single writer (ODIN-ADR-006; I/O contract §1; schemas README §4.2, §5).

Each namespace of the event substrate has exactly one writing component.
The execution-ledger namespace is a read-only mirror of Saga's store: it is
filled only from Saga's cursor, so an append there needs a ``source_seq``.
Every namespace is append-only: amending or deleting an appended event is
refused in all of them.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

ACCEPTED = "accepted"
NAMESPACE_WRITER_MISMATCH = "namespace_writer_mismatch"
MIRROR_REQUIRES_SOURCE_SEQ = "mirror_requires_source_seq"
APPEND_ONLY_VIOLATION = "append_only_violation"


@dataclass(frozen=True)
class Namespace:
    """One catalogue entry (``namespaces.schema.json``)."""

    name: str
    writer: str
    read_only: bool
    content: str
    authority: str
    source: str


class NamespaceCatalogue:
    """The four namespaces of ``namespaces.json`` (I/O contract §1; ODIN-ADR-006)."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self.version: int = data["version"]
        self._namespaces: dict[str, Namespace] = {}
        for entry in data["namespaces"]:
            ns = Namespace(
                name=entry["name"],
                writer=entry["writer"],
                read_only=entry["read_only"],
                content=entry["content"],
                authority=entry["authority"],
                source=entry["source"],
            )
            if ns.name in self._namespaces:
                raise ValueError(f"namespaces.json lists {ns.name!r} twice")
            self._namespaces[ns.name] = ns

    def __contains__(self, name: object) -> bool:
        return name in self._namespaces

    def __iter__(self) -> Iterator[Namespace]:
        return iter(self._namespaces.values())

    def __len__(self) -> int:
        return len(self._namespaces)

    def __getitem__(self, name: str) -> Namespace:
        try:
            return self._namespaces[name]
        except KeyError:
            raise KeyError(f"namespace {name!r} is not in namespaces.json") from None

    def check_append(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Writer check for an append (schemas README §4.2).

        The target namespace is ``event["namespace"]``. A writer other than
        the catalogue's is ``namespace_writer_mismatch``; then a read-only
        (mirror) namespace refuses an event without ``source_seq`` with
        ``mirror_requires_source_seq``; otherwise ``accepted``.
        """
        ns = self[event["namespace"]]
        if writer != ns.writer:
            return {"outcome": NAMESPACE_WRITER_MISMATCH}
        if ns.read_only and event.get("source_seq") is None:
            return {"outcome": MIRROR_REQUIRES_SOURCE_SEQ}
        return {"outcome": ACCEPTED}

    def check_amend(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Amending an appended event is refused in every namespace, by every writer (schemas README §4.2)."""
        self[event["namespace"]]
        return {"outcome": APPEND_ONLY_VIOLATION}

    def check_delete(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Deleting an appended event is refused in every namespace, by every writer (schemas README §4.2)."""
        self[event["namespace"]]
        return {"outcome": APPEND_ONLY_VIOLATION}


class NamespaceLog:
    """In-memory append-only log per namespace (schemas README §4.2).

    A model of the semantics only: the physical store layout is open (X-11)
    and nothing here is a store. Events are kept in append order per
    namespace; there is no way to amend or delete one.
    """

    def __init__(self, catalogue: NamespaceCatalogue) -> None:
        self._catalogue = catalogue
        self._events: dict[str, list[dict[str, Any]]] = {ns.name: [] for ns in catalogue}

    def append(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Append ``event`` when the writer check passes; otherwise append nothing."""
        result = self._catalogue.check_append(writer, event)
        if result["outcome"] == ACCEPTED:
            self._events[event["namespace"]].append(dict(event))
        return result

    def amend(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Always ``append_only_violation``; the log is unchanged."""
        return self._catalogue.check_amend(writer, event)

    def delete(self, writer: str, event: Mapping[str, Any]) -> dict[str, Any]:
        """Always ``append_only_violation``; the log is unchanged."""
        return self._catalogue.check_delete(writer, event)

    def events(self, namespace: str) -> tuple[dict[str, Any], ...]:
        """The events appended to ``namespace``, in append order (copies)."""
        return tuple(dict(e) for e in self._events[self._catalogue[namespace].name])
