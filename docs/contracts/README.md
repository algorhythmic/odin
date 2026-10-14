# Pinned producer contracts

Odin consumes interfaces that other projects own. This directory holds
**pinned, read-only consumer copies** of those producers' contracts, so
this checkout can be read and built against without a sibling
repository. A pinned copy is evidence of what the producer published at
a recorded point; it is never the place a producer capability is
created or changed.

## Rules

1. **The producer owns the contract.** Changes originate in the
   producer's repository. Never edit a pinned copy to add, fix or
   reinterpret a capability; record the gap and raise it with the
   producer.
2. **Pin by snapshot.** Each copy lives at `<producer>/<snapshot-id>/`
   with its producer path, producer commit (when available) and SHA-256
   digest recorded below and in the copy's receipt. Older snapshots stay
   in place until nothing references them.
3. **Update procedure.** When the producer publishes a change: copy the
   new version into a new snapshot directory; record its provenance;
   update the references in the [I/O contract](../design/ODIN-IO-CONTRACT.md)
   and the adapter's compatibility checks **together**; note the change
   in the [roadmap](../ROADMAP.md) or a new `ODIN-ADR` if it changes an
   Odin decision.
4. **Odin states requirements, not interfaces.** The capabilities Odin
   needs are in the I/O contract (Saga: Appendix B). A difference
   between a requirement and the pinned contract is a compatibility gap
   to resolve at the producer.
5. **Status is the producer's.** Do not label a proposed schema or
   endpoint as implemented or tested unless the pinned copy says so with
   evidence.

## Inventory

| Producer | Pinned path | Producer source | Commit / digest | Status |
|---|---|---|---|---|
| Saga | [`saga/2026-10-14-14fdab3/SAGA-SERVICE.md`](saga/2026-10-14-14fdab3/SAGA-SERVICE.md) with [`SNAPSHOT.json`](saga/2026-10-14-14fdab3/SNAPSHOT.json) | `saga:docs/contracts/SAGA-SERVICE.md` | base `14fdab3`; producer commit `a84f9ac28a6b4de651fccc057d33a335472f9773`; digest in `SNAPSHOT.json` | **Pinned draft** (`0.1.1-draft`; documentation review candidate; target API unimplemented, per its metadata). The snapshot name identifies the extraction handoff, not the commit that first contains the contract. The pinned bytes match the corrected canonical `0.1.1-draft`; Appendix B was checked against that canonical text at document level, gaps recorded per capability (`DECISIONS.md` issue X-3) |
| Herdr | — | — | — | Unavailable: automation API not reviewed (open §5.8); installed 0.8.2 observed |
| heimdall | — | — | — | Proposed: external-work projection (EC-05) does not exist |
| skald | — | — | — | Proposed: Odin provider, retrieval and exports unfinished (EC-04, EC-06) |
| braid | — | — | — | Observed library and subprocess contracts; Odin consumer not built (EC-07) |
| wayland-computer-use | — | — | — | Observed MCP servers; shared seat lease is a proposal (EC-10) |
| dotprivate | — | — | — | Proposed: selected-files contract unimplemented (EC-08) |

Observations are from the [ecosystem integration plan](../design/ODIN-ECOSYSTEM-INTEGRATION.md)
§1 (2026-10-14) and were not re-verified during extraction.

## Saga contract expectations

Per the extraction plan §5, the Saga contract is expected to cover the
run, delegation and evidence API; identities and authorization;
request and response semantics; the event cursor; idempotency; stop
semantics; verification responsibilities; and the worker transport
boundary, with known gaps stated. An endpoint list alone is not a
complete executable contract. Each pinned copy is checked against the
I/O contract's Appendix B (B-00 to B-17), whose last column records the
result and every gap (`DECISIONS.md` issue X-3); repeat the check
whenever a new snapshot is pinned.
