"""Python implementation of the I0 event-substrate contract.

I0 (ODIN-ADR-008) is non-production and fixture-only: the versioned event
envelope and its namespaces, the record schemas, the heimdall-to-commitment
mapping, and the fixture set whose expected outcomes this package
reproduces. The contract is ``substrate/schemas`` (its README is the
semantics contract this package cites as "schemas README §n"). No peer API,
service, store or backend is implemented here; the physical store layout is
open (X-11).
"""

__all__ = [
    "conformance",
    "effects",
    "envelope",
    "ids",
    "intake",
    "kinds",
    "migration",
    "namespaces",
    "records",
    "schemas",
]
