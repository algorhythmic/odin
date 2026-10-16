# Event substrate

The event substrate is Odin's one append-only store with named
namespaces: Odin history, the transcript archive, the workstation
surface events, and a read-only mirror of Saga's execution ledger. Each
namespace has exactly one writing component; records, inbox, outbox and
cursors commit in the same transaction as the history they belong to
([ODIN-ADR-006](../docs/DECISIONS.md#odin-adr-006--one-event-substrate-with-namespaces);
[I/O contract §1](../docs/design/ODIN-IO-CONTRACT.md#1-architecture-in-one-page) and
[§9](../docs/design/ODIN-IO-CONTRACT.md#9-durability-and-recovery-protocol)).

## What I0 delivers

Increment I0 ([ODIN-ADR-008](../docs/DECISIONS.md#odin-adr-008--i0-narrowed-to-the-event-log-and-record-schemas))
is the contract layer the rest is built against:

1. the versioned event envelope and its namespaces;
2. the record schemas of I/O contract §2 and Appendix A, with the
   changes of ODIN-ADR-007 (commitment checkpoints, task decisions,
   import provenance), 009 (`host_offline`, Environment), 013 (reviewer
   positions) and 014 (session-class decisions), plus the §3 Message
   row, and the mapping from heimdall's record types to the commitment
   record;
3. fixtures for the duplicate, stale and unknown cases with explicit
   semantics, validated by a Go and a Python implementation against the
   same fixture set.

The contract lives in [`schemas/`](schemas/README.md): JSON Schema
2020-12 files, the namespace and kind catalogues, the mapping, the
fixtures and the semantics every implementation must follow. The
schemas and the semantics README are the single source of truth for the
two implementations; the documents in `docs/` win over them. The Go
packages and the Python package `odin_substrate` (under
`substrate/python/`) implement them.

## What it is not

I0 is non-production and fixture-only. No peer API is implemented: there
is no Saga client, no fake Saga backend, no service loop, no intake from
real producers, no outbox dispatch, no capability matrix, no
workstation daemon and no adapter. Nothing here carries Saga's
guarantees. The physical store layout, including whether SQLite holds
one file or one per namespace, is open (X-11) and decided before I1; the
I0 event log is an in-memory model of the semantics, not a store.

## Running the checks

From the repository root:

```bash
python3 scripts/validate_docs.py         # documentation integrity
go test ./...                            # Go: every fixture case
python3 -m pytest substrate/python/tests # Python: every fixture case
python3 scripts/compare_conformance.py substrate/schemas/fixtures/cases.json <go results> <python results>
```

The compare script exits non-zero when a case is missing from either
results file or differs from its expected outcome or between the two
implementations. A pass is I0 fixture-only evidence.
