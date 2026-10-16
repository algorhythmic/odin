# Substrate schemas: the I0 contract

This directory is the contract layer of increment I0
([ODIN-ADR-008](../../docs/DECISIONS.md#odin-adr-008--i0-narrowed-to-the-event-log-and-record-schemas)):
the versioned event envelope and its namespaces, the record schemas, the
mapping from heimdall's record types to the commitment record, and one
fixture set with expected outcomes. Both the Go and the Python
implementation validate the same fixtures against these files and must
produce exactly the outcomes recorded in `fixtures/cases.json`.

I0 is non-production and fixture-only. No peer API is implemented here,
no service, store, fake backend or Saga client exists, and nothing here
carries Saga's guarantees. The physical store layout is open (X-11) and
is decided before I1. The schemas describe records; they do not say
where or how records are stored.

Governing documents: [decision record §4](../../docs/DECISIONS.md#4-odin-decisions-odin-adr)
(ODIN-ADR-006, 007, 009, 010, 013, 014), the
[I/O contract](../../docs/design/ODIN-IO-CONTRACT.md) §1 to §4, §9,
[Appendix A](../../docs/design/ODIN-IO-CONTRACT.md#appendix-a--record-schemas) and
[Appendix C](../../docs/design/ODIN-IO-CONTRACT.md#appendix-c--event-kinds-and-wake-classes),
and the [implementation blueprint](../../docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md) §4 and §7.
Where this file and those documents disagree, the documents win and
this file is wrong.

## 1. Files

| File | Content |
|---|---|
| `common.schema.json` | `$defs` shared by every schema: `ulid`, `ts`, `digest`, `rev`, `evidence_ref`, `ref`, `src`, `namespace`, `wake_class`, `subject_ref`, `record_ref`, `usage`, and `*_or_null` variants |
| `envelope.schema.json` | The event envelope, version 1 (the Event record of §2 and Appendix A, as stored in the inbox) |
| `namespaces.json`, `namespaces.schema.json` | The four namespaces with their single writer, content and authority (§1; ODIN-ADR-006) |
| `kinds.json`, `kinds.schema.json` | The 51 event kinds of Appendix C with default wake class, conditionality, handling and the `control` flag |
| `records/<record>.schema.json` | One schema per record: `project`, `commitment`, `assignment`, `planning_session`, `session_binding`, `environment`, `human_request`, `approval`, `review`, `evaluator_result`, `session_class_decision`, `attention_prompt`, `effect`, `message` (the Event record is `envelope.schema.json`) |
| `migrations/heimdall-to-commitment.json` (+ `.schema.json`) | The mapping from heimdall's record types to the commitment record; see [`migrations/README.md`](migrations/README.md) |
| `fixtures/cases.json`, `fixtures/cases.schema.json` | The case index with expected outcomes |
| `fixtures/inputs.schema.json` | The input format of every operation, one `$defs` entry per operation name |
| `fixtures/<group>/<slug>.json` | One input file per case |
| `embed.go` | Go package `schemas`: `var FS embed.FS` holding all of the above |

## 2. Schema conventions

- Every schema is JSON Schema 2020-12 with `$schema`, a `$id` of the
  form `https://odin.invalid/substrate/schemas/<path>`, a `title` and a
  `description` quoting its governing section. The `$id`s are
  non-resolvable placeholders: both loaders register every file locally
  under its `$id` and never fetch. Cross-file references are relative
  (`../common.schema.json#/$defs/ulid`), so they resolve against the
  `$id` and also against a file path.
- Strict JSON: every object has `additionalProperties: false` and a
  `required` list naming every field Appendix A shows. Nullable fields
  are `"type": ["<t>", "null"]` (or `anyOf` with `null` for a `$ref`).
  Every record has `id`, `rev`, `created_at` and `updated_at`, except the
  Event (which has `received_at`) and the Message (its §3 fields only).
- Three objects are deliberately open because no document fixes their
  keys: the envelope `payload`, an Effect's `receipt`, and a verdict's
  `checklist`. `usage` is closed, with the optional keys §12 names
  (`input_tokens`, `output_tokens`, `cache_read_tokens`,
  `cache_write_tokens`, `latency_ms`, `retries`, `cost_usd`) plus
  `unavailable`.
- Cross-field rules that JSON Schema can state are in the schemas as
  `if`/`then`: a Review's combination and verdict rules, an
  AttentionPrompt's response and shadow-mode rules, an Effect's
  `dispatch_blocked_by` when `held` and `guidance_rev` only on
  `saga:guidance`. Rules that need arithmetic or other records
  (Message `size`, revisions, ownership) are semantic checks (§4).
- **Pattern dialect.** Every `pattern` starts with `^`, ends with `$`,
  contains no other `$`, and uses only the common subset of RE2 and
  Python `re` (explicit classes such as `[0-9]` and `[!-~]`; no `\d`,
  `\s`, `\w`, lookaround or backreferences). `$` means end of string. Go's
  RE2 already behaves so; Python's `re` also lets `$` match before a final
  newline, so the Python implementation must compensate, for example by
  overriding the `pattern` keyword to replace the final `$` with `\Z`.
  With the `jsonschema` package, register the extended validator class for
  the 2020-12 metaschema (`jsonschema.validators.validates("draft2020-12")`),
  otherwise schemas reached through `$ref`, which declare `$schema`, are
  validated by the stock class. The fixture
  `schema/envelope-id-trailing-newline` probes this.
- Integers are written without a fraction or exponent. No fixture uses
  `1.0` for an integer, and I0 fixes no behaviour for it.

## 3. Fixture format

`fixtures/cases.json` is an array of cases, validated by
`fixtures/cases.schema.json`:

```json
{ "id": "<group>/<slug>", "group": "intake", "operation": "intake_sequence",
  "input": "fixtures/intake/same-dedupe-key-twice.json",
  "expected": { "steps": [ ... ] }, "cites": ["AC-01", "I/O contract §9"],
  "note": "one sentence" }
```

- `id` is stable and never renumbered; its prefix is the `group`.
  Groups: `schema`, `envelope`, `namespace`, `intake`, `replay`,
  `revision`, `review`, `effects`, `revalidate`, `migration`.
- `input` and `schema` are paths relative to this directory
  (`substrate/schemas/`), which is also the root of the Go `FS`.
- `schema` is present exactly when `operation` is `validate`: the input
  document is validated against that schema file.
- For every other operation the input file validates against
  `fixtures/inputs.schema.json#/$defs/<operation>`. Implementations
  should check this before running the operation; a failure there is a
  defect in the fixture, not a case outcome.
- `expected` is either a result object `{ "outcome": ..., ...keys }`
  or, for sequence operations (`intake_sequence`, `inbox_sequence`),
  `{ "steps": [ result, ... ] }` with one result per step.

**Results file.** Each implementation writes one JSON object mapping
every case id to its result, with keys sorted, 2-space indentation and
a trailing newline:

```json
{ "intake/same-dedupe-key-twice": { "steps": [ ... ] },
  "schema/project-valid": { "outcome": "schema_valid" } }
```

A result carries `outcome` and only the extra keys its operation
defines in §4; keys that do not apply are omitted, never `null`
(`cursor_after` is the one key whose value may be `null`).
`scripts/compare_conformance.py` compares each result exactly with
`expected` and the two implementations with each other.

## 4. Semantics contract

Outcome strings and result keys are exact. Each operation below names
its input (see `fixtures/inputs.schema.json`) and its result.

### 4.1 Strict decoding and schema validation (`validate`)

Input: any JSON document, plus the case's `schema`. Steps, in order:

1. **Decode strictly.** A document with a duplicate key anywhere is
   rejected without schema validation: `schema_invalid` with `errors`
   listing the JSON pointer of each duplicated key (for example `/kind`).
2. **Validate** against the schema. On failure: `schema_invalid` with
   `errors`, the sorted, de-duplicated list of JSON pointers (RFC 6901;
   the document root is `""`; `~` and `/` in a key are escaped as `~0`
   and `~1`). Sorting is by code point. The pointers are computed from
   the validator's error tree as follows:
   - an unknown key (`additionalProperties`): the pointer of the
     unknown key itself, for example `/scope/repo`;
   - a missing required key: the pointer of the missing key, for
     example `/rev`;
   - a failure of `anyOf`, `oneOf`, `not` or `contains` (including
     `minContains`/`maxContains`): the location of the value that
     keyword applies to; its sub-errors are not reported;
   - every other failure: the location of the failing value (descend
     through `$ref`, `allOf`, `properties`, `items` and `if`/`then` to
     the leaf errors).

   With Python `jsonschema`, this is the set over `iter_errors()` (whose
   errors are already flattened that way) with the two key rules
   applied. With Go `santhosh-tekuri/jsonschema/v6`, walk
   `ValidationError.Causes`, stopping at `kind.AdditionalProperties`,
   `kind.Required`, `kind.AnyOf`, `kind.OneOf`, `kind.Not`,
   `kind.Contains`, `kind.MinContains` and `kind.MaxContains`, and taking
   the `InstanceLocation` of every other leaf.
   The comparison is of the pointer set, never of messages.
3. **Catalogue check**, only for a schema-valid document validated
   against `envelope.schema.json`: a `kind` not in `kinds.json` is
   `unknown_kind`. A `namespace` outside the catalogue is already a schema
   failure (the schema enumerates the four namespaces).
4. Otherwise `schema_valid`.

Result keys: `outcome`; `errors` only with `schema_invalid`.

### 4.2 Namespace writer check (`append`, `amend`, `delete`)

Input: `{ "log": [event...], "writer": "<component>", "event": {...} }`.
The target namespace is `event.namespace`; `log` is what was appended
before and is not otherwise consulted.

- `amend` and `delete`, in any namespace and by any component, the
  namespace's own writer included: `append_only_violation`. Redaction is
  a tombstone message operation (§8), not an event amendment, and is out
  of I0 scope.
- `append`: if `writer` differs from the catalogue's `writer` for the
  namespace, `namespace_writer_mismatch` and nothing is appended. Then,
  for a namespace whose catalogue entry has `read_only: true` (the
  execution-ledger mirror, written by `saga_adapter`), an event whose
  `source_seq` is `null` is `mirror_requires_source_seq`: the mirror is
  filled only from Saga's cursor. Otherwise `accepted`.

The writer check runs before the `source_seq` check. Result keys:
`outcome` only.

### 4.3 Intake and dedupe (`intake_sequence`; AC-01, §9)

Input: `{ "events": [event...] }`, applied in array order to an empty
inbox. State is kept per **(namespace, producer)** pair: a `cursor` (the
last accepted `source_seq`, initially `null`) and the set of seen
`dedupe_key`s. Both are per pair, so the same dedupe key or sequence
under another producer or another namespace is independent. For each
event, in this order:

1. its `dedupe_key` is already in the pair's set: `duplicate_dedupe_key`;
2. it has a `source_seq`, the cursor is not `null`, and
   `source_seq <= cursor`: `duplicate_sequence`;
3. otherwise `accepted`: the event is inserted with `state: received`,
   its key is added to the set, and the cursor becomes its `source_seq`
   if it has one (an event without a sequence leaves the cursor as it
   was). Sequences may skip values.

A duplicate is a no-op that is counted and not recorded. Each step's
result is `{ "outcome", "cursor_after", "duplicates_counted" }`, where
`cursor_after` is the cursor of that event's pair after the step and
`duplicates_counted` is the running total of duplicates in the whole
case. Intake inputs are schema-valid envelopes with known kinds.

### 4.4 Processing and replay (`replay`, `inbox_sequence`; AC-27, §9 step 3)

The inbox is the input's `events` array in **received order** (array
order; not id order and not `received_at` order), each with its `state`.

- `process(event_id)`: an event in `received` becomes `processed`,
  outcome `processed`; an event already `processed` gives
  `already_processed` (an idempotent no-op); an id not in the inbox gives
  `unknown_event`.
- `replay()`: outcome `replayed` with `replay_order`, the ids of every
  event still `received`: first those whose kind has `control: true` in
  `kinds.json`, in received order, then all others, in received order.

`replay` input: `{ "events": [...] }`; result
`{ "outcome": "replayed", "replay_order": [...] }`.
`inbox_sequence` input: `{ "events": [...], "steps": [{ "op": "process",
"event_id": ... } | { "op": "replay" }] }`; result `{ "steps": [...] }`,
one result per step (`{ "outcome" }` for `process`; the replay result
above for `replay`).

The control kinds are the five direct commands
`operator.command.{stop,pause,revoke,take,return}`. §9 step 3 names stop,
revoke, take-control, ownership transfer and operator corrections.
Ownership transfer is the `commitment.transfer` operation and a
correction is detected in code on an `operator.message`; neither is an
inbound kind, and none is invented. Pause and return are included
because Appendix C classes all five commands as direct, and keeping them
in one ordered batch preserves their relative order: a `return` received
before a `take` must still be applied before it
(`replay/control-relative-order-kept`).

### 4.5 Revisions, ownership and operations (§2, §9)

- `check_revision`, input `{ "record_rev", "expected_revision"? }`:
  `expected_revision` missing or `null` gives `expected_revision_required`;
  equal to `record_rev` gives `ok`; any other value (lower or higher)
  gives `stale_revision` (the 409; nothing changes).
- `check_owner`, input `{ "session": PlanningSession, "commitment":
  Commitment }`: `stale_owner` if the session's `state` is `retired`, or
  if its `ownership_generation` differs from the commitment's; otherwise
  `ok`. A `retiring` session at the current generation is `ok`.
- `commitment_transfer`, input `{ "commitment", "new_owner",
  "expected_revision"?, "effects": [Effect...] }`: first `check_revision`
  against `commitment.rev` (a failure returns that outcome alone). Then
  outcome `transferred` with `generation_after` (the commitment's
  generation + 1), `rev_after` (its `rev` + 1) and `held_effects`: the
  ids, sorted by code point, of every effect in `effects` whose `state` is
  `queued` or `held` and whose `owner_generation` is not `null` and is
  lower than `generation_after`. Those effects become `held` with
  `dispatch_blocked_by = "ownership_transfer:<commitment id>"` and are
  revalidated later (§4.7); effects in other states, or with a `null`
  `owner_generation`, are untouched.
- `operation_reuse`, input `{ "existing": Effect, "incoming": Effect }`
  with the same `operation_id`: a different `payload_digest` gives
  `operation_conflict` (the 409); the same gives `operation_idempotent`.
- `check_message_size`, input a Message: `size` equal to the UTF-8 byte
  length of `text` gives `ok`; otherwise `size_mismatch`.

Result keys: `outcome`; plus `generation_after`, `rev_after` and
`held_effects` with `transferred`.

### 4.6 Review combination (`combine`; §10 review, ODIN-ADR-013, AC-22, AC-40)

Input: `{ "round": 1 | 2, "positions": [position a, position b] }`. With
each position's result being its `verdict.result`, or none when its
`verdict` is `null`, the first matching rule decides:

1. any position without a verdict (unanswered, or unavailable with
   `usage.unavailable: true`): `pending`. An unavailable position never
   waives review, and pending comes before escalation.
2. any `REJECT` or `INSUFFICIENT_EVIDENCE`: `escalated`.
3. both results in {`APPROVE`, `APPROVE_UNCHANGED`}: `approved`, with
   `verdict_result` `APPROVE_UNCHANGED` when both are
   `APPROVE_UNCHANGED`, otherwise `APPROVE`.
4. otherwise (a `FLAG` with an approval, or two `FLAG`s): `re_review` in
   round 1, `escalated` in round 2.

Result keys: `outcome`; `verdict_result` only with `approved`. The Review
record schema enforces the matching record rules: `combination` is
`null` while any position's verdict is `null`; `null` and `escalated`
combinations have a `null` combined verdict; `approved` requires both
positions and the combined verdict to approve.

### 4.7 Effects: restart, reconciliation, dispatch, revalidation (AC-02, AC-27, §9)

**`restart`**, input `{ "effects": [...] }`: every `in_flight` effect
becomes `unknown`. Result `{ "outcome": "restarted", "marked_unknown":
[ids sorted by code point] }`.

**`reconcile`**, input `{ "effect", "lookup": string | null,
"host_state": "host_offline" | "host_returned" | null }`. `lookup` is the
destination's answer. By the effect's `destination_capability`:

| Capability | Accepted effect states | Rule |
|---|---|---|
| `idempotent_by_key` (Saga) | `unknown`; `host_state` must be `null` | `completed` → `delivered`, retry false; `pending` → `unknown`, retry false (wait); `failed` → `failed`, retry false; `superseded` → `superseded`, retry false, never re-sent; `absent` → `queued`, retry true (same operation id); `unknown_expired` → `unknown`, retry false, `surface_to_operator: true` |
| `irreducibly_unknown` (Telegram) | `unknown`; `lookup` and `host_state` must be `null` | operation (the part after `:`) `notify` → `unknown`, retry false, `note: "may have been sent"`; `request` or `approval` → `queued`, retry true, `same_request_id: true` |
| `surface_declared` (attention prompts, other surfaces) | `unknown`; `lookup` and `host_state` must be `null` | `unknown`, retry false, `counts_against_caps: true` |
| `session_host` | `queued`, `in_flight`, `unknown` | `host_offline` (with `lookup` `null`): state unchanged, retry false, `held_for_host: true`. `host_returned` with the host's report as `lookup`: `completed` → `delivered`, retry false; `absent` → `queued`, retry true |

Anything else (an unknown capability, a lookup value outside the row, a
lookup where none exists, a missing `host_state` for a session host, an
effect in a state the row does not accept, a Telegram operation other
than `notify`, `request` or `approval`) gives
`invalid_reconciliation_input`. A valid reconciliation gives outcome
`reconciled` with `state_after` and `retry_allowed`, plus
`surface_to_operator`, `note`, `same_request_id`, `counts_against_caps`
or `held_for_host` exactly where the table names them.

**`dispatch`**, input `{ "effect", "prompt": AttentionPrompt | null,
"recovery_in_progress": bool }`, checked in this order:
`recovery_in_progress` → `dispatch_disabled` (nothing leaves the service
until recovery step 8); a prompt in `shadow` mode →
`dispatch_refused_shadow` (a shadow prompt is never dispatched); an
effect not in `queued` → `invalid_dispatch_input`; otherwise
`dispatched` with `state_after: "in_flight"`.

**`revalidate`**, input `{ "effect", "context": { "current_generation",
"delegation_revoked", "assignment_state", "approval_expired",
"host_state" } }`. Only `queued` and `held` effects are revalidated;
any other state gives `invalid_revalidation_input`. The checks run in
this order and the first failure decides `cancelled_stale` with
`reason`:

1. `owner_generation`: the effect's `owner_generation` is not `null` and
   is lower than `current_generation`;
2. `delegation_revoked`: `delegation_revoked` is true;
3. `assignment_state`: `assignment_state` is `cancelled`, `completed` or
   `failed` (`null` when the effect has no assignment);
4. `approval_expired`: `approval_expired` is true.

If all pass, the outcome is `queued`: a `held` effect leaves `held` only
to `queued` or `cancelled_stale`. `host_state` is recorded for context
and not consulted in I0; session-host commands are held by the
reconciliation rule above. Result keys: `outcome`; `reason` only with
`cancelled_stale`.

### 4.8 Migration mapping (`check_mapping_coverage`)

Input: a mapping document valid against
`migrations/heimdall-to-commitment.schema.json`. The commitment fields
are the top-level `properties` of `records/commitment.schema.json`. A
row covers the field named by its `commitment_field` up to the first
`.` (`provenance.native_rev` covers `provenance`); rows whose
`commitment_field` is `null` cover nothing. `uncovered` is the sorted
list of fields no row covers. Outcome `mapping_complete` when it is
empty, otherwise `mapping_incomplete`. Result keys: `outcome`,
`uncovered` (always present).

### 4.9 Outcome index

| Operation | Outcomes |
|---|---|
| `validate` | `schema_valid`, `schema_invalid`, `unknown_kind` |
| `append`, `amend`, `delete` | `accepted`, `namespace_writer_mismatch`, `mirror_requires_source_seq`, `append_only_violation` |
| `intake_sequence` (per step) | `accepted`, `duplicate_dedupe_key`, `duplicate_sequence` |
| `replay`, `inbox_sequence` | `replayed`, `processed`, `already_processed`, `unknown_event` |
| `check_revision` | `ok`, `stale_revision`, `expected_revision_required` |
| `check_owner` | `ok`, `stale_owner` |
| `commitment_transfer` | `transferred`, `stale_revision`, `expected_revision_required` |
| `operation_reuse` | `operation_conflict`, `operation_idempotent` |
| `check_message_size` | `ok`, `size_mismatch` |
| `combine` | `approved`, `escalated`, `pending`, `re_review` |
| `restart` | `restarted` |
| `reconcile` | `reconciled`, `invalid_reconciliation_input` |
| `dispatch` | `dispatched`, `dispatch_disabled`, `dispatch_refused_shadow`, `invalid_dispatch_input` |
| `revalidate` | `queued`, `cancelled_stale`, `invalid_revalidation_input` |
| `check_mapping_coverage` | `mapping_complete`, `mapping_incomplete` |

## 5. Catalogue notes

- **Namespaces.** `odin_history` is written by `service`,
  `transcript_archive` by `capture_module`, `surface_events` by
  `workstation_sensors`, and `execution_ledger` by `saga_adapter`. The
  last is `read_only`: a mirror filled only through Saga's API and
  cursor; the adapter applies, never authors or amends; Saga's store
  stays authoritative and decides (D4). The mirror decides nothing.
- **Kinds.** `default_wake` is the class assigned at intake: §4's four
  (`interrupt`, `wake`, `log`, `state`) or `none`, meaning the event is
  handled in code with no planner turn by default (direct control path,
  approval validation, lifecycle handler, operator-queue delivery,
  journal triage before its typed outcome). A consequence of that code
  handling, such as the lifecycle handler's `decision_required` wake, is
  a separate wake decision. `conditional: true` marks kinds whose wake
  depends on content or a typed rule.
- `run.state.limit_paused` is Odin's spelling; Saga's wire spelling is
  fixed by its schema (pinned contract INC-08).
- Appendix A's Event example uses the kind `run.state`, which is not an
  Appendix C kind; the catalogue follows Appendix C, so `run.state` is
  `unknown_kind` (`envelope/unknown-kind`).
- `dedupe_key` formats (`saga:<seq>`, `telegram:<chat>:<message>`,
  `hash:<sha256>` and so on) follow the §4 table per producer; the
  implementations treat the key as opaque.
- Effect destinations are `<target>:<operation>`, for example
  `saga:run.submit`, `saga:guidance`, `telegram:notify`,
  `telegram:request`, `telegram:approval`, `surface:prompt`,
  `session_host:start`. `saga:guidance` is the only destination that
  carries `guidance_rev`.

## 6. Checks

From the repository root, once the Go and Python implementations exist:

```bash
go test ./...
python3 -m pytest substrate/python/tests
python3 scripts/compare_conformance.py substrate/schemas/fixtures/cases.json <go results> <python results>
```

A pass is I0 fixture-only evidence. It exercises no service, store,
backend or peer API.
