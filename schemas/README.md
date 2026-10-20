# Local runtime contracts

These Draft 2020-12 schemas describe Odin-owned records and explicitly
synthetic development protocols. They do not define Saga or any peer's
wire API. ODIN-ADR-021 records the local conventions. Native build files
(`go.mod`, `go.sum`, Python requirements and the Makefile) use their tools'
formats instead of JSON schemas.

`records.schema.json` contains 12 unaffected Odin-owned record types from the
[I/O contract](../docs/design/ODIN-IO-CONTRACT.md#appendix-a--record-schemas).
The Review and guidance schemas remain gated on X-7 and are absent.
Records use `schema_version`, `record_type`, `rev`, canonical ULIDs and UTC
timestamps ending in `Z`. Producer IDs are opaque references. A schema
checks shape and local invariants; it cannot prove that a referenced
receipt is authoritative. Trusted lifecycle code performs that check.

`event.schema.json` distinguishes the four namespaces and requires either
an inline payload or a payload reference. The execution mirror requires
Saga attribution and a producer sequence. Unknown event kinds remain
valid and route conservatively; they do not gain authority.

The Go and Python validators run the same `fixtures/contracts.json` and
`fixtures/transitions.json`. The transition fixtures define duplicate
identity conflicts, revision comparison, and effect reconciliation:
only an authoritative absence lookup on an idempotent destination can
make an authorized unknown effect eligible for retry. Pending, expired
and irreducibly unknown outcomes stay unknown. The local service uses
these rules; Go currently supplies contract validation, not a second
service implementation.

The other schemas validate fixture commands, host results, capture batches,
profiles, capabilities, evaluation episodes and reports. The
`delegation-config`, `delegation-turn` and `delegation-result` schemas
describe the operator configuration, service turn records and detached
runner results of ADR-027's local delegation sessions (a result's
`lineage` block records the credential-lease outcome and content-free
credential-file fingerprints); the
`executive-tool-input` definitions bound each bridge tool's arguments. Fixture protocols
have no live transport. Schemas are loaded once per process; restart after
editing them. Incompatible future state changes need an explicit migration;
the current database version is 1.

## Task-record mapping for I0

Source: the dated [heimdall inventory, §B.5](../docs/research/consolidation-2026-10/inventory-go-repos.md#b5-task-core-record-types-mapped-to-odin-commitments).
This is a mapping specification, not a producer contract, import command
or retirement of heimdall. A real importer still waits for G-10 and I4.

| Source record/field | Odin destination and rule |
|---|---|
| `TaskRecord.task.id`, `revision` | New commitment ULID; original identity/revision in `provenance`, with source `heimdall` and an import receipt. Odin `rev` starts at 1; source revisions never overwrite it. |
| `Contract.objective`, `Task.title` | Commitment `objective`; retain the source contract locator/digest with import evidence. |
| `Task.done`, `Contract.acceptance`, `Check` | Named commitment `criteria`; preserve the check description and original check specification in import evidence. Import does not mark criteria met. Unsupported checks remain unmet with an explicit gap. |
| `Task.status`, `Step.status`, `TaskRecord.completed`, `Workflow` | Workflow-specific source state retained with import evidence. `done` is not Saga verification and cannot close an Odin commitment. A migration must resolve each workflow mapping before importing. |
| `Step`, `TaskDependency` | Child commitments and `dependencies`, resolved through the import identity map. Keep pinned prerequisite revisions in import evidence; missing targets block the import. |
| `Checkpoint` | `checkpoints`: source id, timestamp, summary and evidence references. `actor` is source attribution, never a planning-session owner. Import waits until an Odin recording owner can supply `recorded_by`. Original fields stay in import evidence. A checkpoint supplies no independent corroboration. |
| `Decision` | `decisions`: original text as `choice`, source actor as `decided_by`, timestamp and evidence. Do not invent a rationale/question; the migration must explicitly represent missing source fields before accepting a record. `supersedes` remains in import evidence. |
| Pending decision `ProgressProposal` | `open_decisions`, preserving source identity/text and attribution. An accepted proposal does not grant execution authority. |
| `Resource`, `Evidence`, `ArtifactVersion`, `PreservationReceipt`, `ProgressReview` | Source-attributed evidence references with locators/digests and provenance; never silently promoted into verified acceptance. |
| `Task.resume_by`, `Step.due`, `Timer` | `next_trigger` after migration policy review; importing does not arm a timer. |
| `Grant`, observed agent, workspace `SessionBinding` | No delegation, ownership or credential is imported. New Odin ownership and Saga delegation must be established separately. Preserve eligible source attribution only, excluding credentials/token hashes. |
| Effort estimates, importance, impact, unsupported workflow fields | Preserve in the scoped import evidence; no automatic budget, authority, routing or priority inference. |

The destination schema deliberately requires complete task-decision fields
and planning-owner identities. Missing source information is a migration
decision, not permission for the importer to fabricate it. The mapping
therefore exposes these gaps before any real-history import is implemented.
