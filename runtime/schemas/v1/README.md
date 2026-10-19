# I0 schema scope and source mapping

These Draft 2020-12 schemas define Odin-owned record shapes and the version 1
inbox envelope. They do not implement the service, storage transactions,
namespace writer enforcement, Saga admission, or a heimdall migration. `Event`
contains exactly one of `payload` and `payload_ref`; a reference points to
content held by its owner. `execution_ledger` is reserved for a read-only mirror
fed by Saga's API cursor. The substrate must enforce one writer per namespace
and atomic history/record/cursor commits in I1; accepting an event with this
schema does not grant a producer write authority. Source-native Saga IDs,
harness session IDs and heimdall IDs are nonempty opaque strings in references;
Odin-minted record and event IDs are ULIDs. `common.schema.json` uses `ulid`
and `date-time` format assertions plus lexical patterns for UTC `Z` timestamps.
Validators must reject invalid calendar times and invalid ULID encodings, including the nil ULID. Numeric fields are capped at the interoperable JSON integer boundary (2^53−1); parsers must reject nonfinite numbers.

The import mapping below is normative for Odin's target fields under
ODIN-ADR-007. It identifies native *record types*, not unverified heimdall
field names or an implemented peer reader. The migration must establish
which source fields supply each target value, refuse incomplete inputs, and
record its source-side retirement under EC-13/G-10 before AC-38 can pass.

| Native record type | Odin target | Required transformation and provenance |
|---|---|---|
| Task | One `Commitment` in the owning project | Preserve the native task identity and revision in `Commitment.provenance`; store the shared import receipt. Map the accepted objective and acceptance criteria to `objective` and `criteria`; carry unresolved choices in `open_decisions`, source evidence references in `evidence`, and the next actionable condition in `next_trigger`. Assign an Odin planning-session `owner` and `ownership_generation`; do not infer them from heimdall. Resolve the applicable Saga delegation as an opaque reference. |
| Checkpoint | An element of that task's `Commitment.checkpoints` | Retain the checkpoint time, summary, and evidence references. Set `recorded_by` to the importing Odin planning session and preserve this checkpoint's own native identity and revision in its `provenance` with the shared receipt. The checkpoint is imported history, not independent corroboration. |
| Task decision | An element of `Commitment.decisions` if resolved, otherwise `open_decisions` | A resolved decision carries its question, choice, rationale, deciding principal, time, and evidence references. Preserve its own native identity and revision in `decisions[].provenance` and the shared receipt. An unresolved decision remains an `open_decisions` entry and must retain native provenance; it must not be invented as resolved. |

`Commitment.provenance` is null for Odin-native work. Imported entries in
`checkpoints` and `decisions` carry their own provenance; later Odin-authored
entries may omit it. An import replay with the same native identity and
revision yields the same logical commitment and one receipt. Any later edit
attempt in heimdall must be refused. Ignoring an edit after it succeeds in the
source does not complete retirement. The exact source-field adapter and
transactional idempotence check are later implementation work, and no peer
repository is changed here.

`cases.schema.json` validates the structural fixture manifest. The separate
`semantics.schema.json` validates the shared state-transition case manifest;
Go and Python validators must produce the same results for both. Schema
validation cannot establish dense message indexes, computed text byte size,
foreign-key existence, deduplication across events, stale-owner/refusal
behavior, external effect reconciliation, or actual single-writer isolation.

Additional structural guards in v1: a Saga assignment may be drafted before
`stage_run`, but approved/dispatched/active/completed Saga assignments carry
its preallocated `request_id`; active/completed ones also carry Saga's opaque
`run` id. Local/desktop assignments cannot carry either Saga binding. A held
outbox effect names its blocker, and a delivered effect carries a receipt.
Session and Environment credential fields accept only `secret:<handle>`
references, with an ASCII alphanumeric first handle character followed by
ASCII alphanumerics, dot, underscore, slash or hyphen. This grammar is not
proof of secret-store resolution or access rights. Attention prompts enforce
the response kind appropriate to their state, and satisfied/closed
commitments structurally mark every criterion met with evidence. The service
must still verify evidence, authorization, caps, expiry and state transitions.
