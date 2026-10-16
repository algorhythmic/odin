"""The event envelope, version 1 (I/O contract §2 Event, Appendix A; schemas README §1, §4.1).

Envelopes are plain dicts shaped by ``envelope.schema.json``. Validation is
the schema plus the catalogue check: a schema-valid envelope whose ``kind``
is not in ``kinds.json`` is ``unknown_kind``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import schemas

ENVELOPE_VERSION = 1
SCHEMA = schemas.ENVELOPE_SCHEMA

RECEIVED = "received"
PROCESSED = "processed"


def validate(event: Any, schema_set: schemas.SchemaSet | None = None) -> dict[str, Any]:
    """Validate a decoded envelope (schemas README §4.1 steps 2 to 4)."""
    return (schema_set or schemas.load()).validate_instance(event, SCHEMA)


def stream(event: Mapping[str, Any]) -> tuple[str, str]:
    """The (namespace, producer) pair that owns an event's cursor and dedupe set (schemas README §4.3)."""
    return event["namespace"], event["producer"]
