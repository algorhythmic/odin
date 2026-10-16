"""Coverage check of the heimdall-to-commitment mapping (ODIN-ADR-007; schemas README §4.8).

The mapping is kept with the schemas; the import itself is I4 after G-10
(I/O contract §14 step 6; AC-38) and is not implemented here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import schemas

MAPPING_COMPLETE = "mapping_complete"
MAPPING_INCOMPLETE = "mapping_incomplete"
COMMITMENT_SCHEMA = "records/commitment.schema.json"


def commitment_fields(commitment_schema: Mapping[str, Any]) -> list[str]:
    """The commitment fields: the top-level ``properties`` of the commitment schema (schemas README §4.8)."""
    return list(commitment_schema["properties"])


def check_mapping_coverage(
    mapping: Mapping[str, Any], commitment_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Which commitment fields no mapping row covers (schemas README §4.8).

    A row covers its ``commitment_field`` up to the first ``.``; a ``null``
    field covers nothing. The mapping's own ``commitment_fields`` list is
    not consulted: the schema is the source of the field set.
    """
    if commitment_schema is None:
        commitment_schema = schemas.load().documents[COMMITMENT_SCHEMA]
    covered = {
        row["commitment_field"].split(".", 1)[0]
        for row in mapping["rows"]
        if row["commitment_field"] is not None
    }
    uncovered = sorted(f for f in commitment_fields(commitment_schema) if f not in covered)
    return {"outcome": MAPPING_COMPLETE if not uncovered else MAPPING_INCOMPLETE, "uncovered": uncovered}
