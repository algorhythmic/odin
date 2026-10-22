# Odin web app browser projection (DRAFT)

Status: DRAFT proposal from the webapp workstream (passes 2 and 3). Not
adopted. The integration owner and the executive decide adoption under
W3; until then the shapes below are a working proposal and the fixtures
under web/fixtures/ are synthetic.

Date: 2026-10-22 (pass 2 draft; pass 3 adds the draft JSON Schemas in
section 8; pass 4 replaces cost with token usage under
[WEB-APP-PASS-4-BRIEF.md](WEB-APP-PASS-4-BRIEF.md) item 2).
Context: [WEB-APP-HANDOFF.md](WEB-APP-HANDOFF.md),
[WEB-APP-WORKPLAN.md](WEB-APP-WORKPLAN.md) (package W3) and
[ODIN-ADR-037](../DECISIONS.md#odin-adr-037--web-app-as-the-primary-human-view-with-an-agent-tree).

## 1. Scope

This note proposes the read projection the browser consumes from the
service: a snapshot, a per-session details response and an update
stream. The browser is a client. It holds no authoritative records and
does not change lifecycle state. The projection reports records as they
are and does not repair them. Transport, commands and the authoritative
record schemas are out of scope.

## 2. Snapshot

Schema: `odin.web.projection.snapshot/v0-draft`.

| Field | Type | Meaning |
|---|---|---|
| schema | string | Schema identifier above. |
| synthetic | boolean | `true` for fixture data. A live service emits `false`. |
| dataset | string | Dataset name: `default` for the fixture files, `large` for the generated set. |
| revision | integer | Increases monotonically per projection. Scope is open (section 9). |
| cursor | string | Opaque resume position. Clients store it and never parse it. |
| generated_at | string | RFC 3339 UTC time the snapshot was built. |
| projects | array | `id`, `name`, `summary`, `host`. |
| commitments | array | `id`, `project_id`, `title`, `status`, `owner`. |
| assignments | array | `id`, `project_id`, `commitment_id`, `owner_session_id`, `summary`, `progress`. |
| runs | array | `id`, `project_id`, `assignment_id` (may be null), `session_id`, `outcome`, `summary`. |
| sessions | array | Session records (section 2.1). |
| relationships | array | `id`, `type`, `from`, `to`. Types: `review`, `delegation`, `run_association`, `assignment_owner`. |
| decisions | array | `id`, `project_id`, `kind`, `status`, `requested_by`, `title`, `proposal` (`id`, `revision`, `digest`). |
| conversations | object | Keyed by project id. Entries: `at`, `speaker`, `text`. |
| activity | object | Keyed by project id. Entries: `id`, `at`, `kind`, `session_id`, `text`. |

### 2.1 Session record

Fields of each entry in `sessions`. Optional fields appear only where
the record has them.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable session id. |
| `project_id` | string | Owning project. |
| `parent_session_id` | string or null | Recorded ancestry parent. `null` makes a root (section 5). |
| `provenance` | string | `recorded` or `imported`. |
| `role` | string | Free-text role, for example `worker` or `reviewer`. |
| `assignment_id` | string or null | Assignment the session serves. |
| `model` | string or null | Model when known. |
| `lifecycle` | string | Activity: `running`, `idle`, `waiting_for_input`, `ended`, `retired`, `host_offline`. |
| `needs_operator_input` | boolean | Whether the operator must act. |
| `observed_at` | string | RFC 3339 time of the last observation. |
| `stale` | boolean | Observation is old or unconfirmed. |
| `tokens` | object | `{uncached_input, cache_read, cache_write, output, basis}`. Section 7. |
| `elapsed_s` | integer or null | Elapsed seconds, when known. |
| `budget` | object or null | `{basis, limit_tokens}`. Fixture basis: `requested`. |
| `attempt` | integer | Optional. Attempt number in a series. |
| `attempt_of` | string or null | Optional. Fixture stores an assignment id (section 9). |
| `previous_attempt` | string or null | Optional. Earlier attempt's session id. May be unavailable. |
| `resumption` | object | Optional. `{count, resumed_from_host_session, resumed_at}`. |

## 3. Session details

Schema: `odin.web.projection.session-details/v0-draft`.

`default-details.json` bundles `transcripts` and `evidence`, keyed by
session id, with `page_size` 20 (so `ses-worker-a2` has two pages). The browser loads details for one
selected session, one page at a time. Opening the tree never loads the
transcripts or evidence of the whole tree.

Per-session response (proposal): `session_id`; `page` and `pages`
(1-based, `pages` = `ceil(items / page_size)`); `page_size`, set by the
service; `transcript`, the page's transcript items in `seq` order; and
`evidence`. The synthetic loader (`web/src/fixtures/synthetic.js`)
returns exactly this shape; the draft schema is
`schemas/web-projection-session-detail.schema.json`.

Transcript items are one of two kinds.

- Entry: `{seq, at, speaker, text}`. `seq` is a per-session integer,
  ascending and unique.
- Gap: `{kind: "gap", from_seq, to_seq, reason}`. Sequence numbers
  `from_seq` to `to_seq` inclusive are unavailable. The view shows a
  gap marker, never silence. A gap counts as one item when paging.

Evidence entries are `{id, label, source, owner}`. `source` names where
the evidence came from; `owner` is the session that produced it.
Evidence is not a verified outcome (section 7).

Transcript `text` is untrusted data. The fixture's `seq` 2 holds raw
markup and `javascript:` links; the view renders them as text.

## 4. Update events

Schema: `odin.web.projection.event/v0-draft`.

| Field | Type | Meaning |
|---|---|---|
| `event_id` | string | Globally unique. Idempotency key. |
| `revision` | integer | Snapshot revision after this event is applied. |
| `cursor` | string | Resume position after this event. Opaque. |
| `at` | string | RFC 3339 time of the change. |
| `type` | string | One of the types below. |
| `payload` | object | Depends on `type`. |

Event types used by the prototype:

| `type` | `payload` |
|---|---|
| `session.lifecycle_changed` | `{session_id, lifecycle, needs_operator_input?, observed_at, stale?}` |
| `session.started` | `{session: <full session record>}` |
| `session.usage_updated` | `{session_id, tokens}` |
| `session.retired` | `{session_id, observed_at}` |

Client rules, checked in this order:

1. **duplicate**: `event_id` already seen. No change.
2. **rejected** (prototype): `revision` is not an integer, or `type`
   is not one listed above.
3. **gap**: `revision` > current + 1. Events were missed. Stop applying
   and fetch a fresh snapshot.
4. **stale**: new `event_id` and `revision` <= current. Ignore and
   report it.
5. **rejected** (prototype):
   - `session.started` without a session record, with an `id` or
     `project_id` that is not a non-empty string, for a project the
     snapshot does not hold, with a `lifecycle` outside the documented
     set (section 2), or for an id already present;
   - any other type whose `session_id` is missing or not in the
     snapshot;
   - `session.lifecycle_changed` with a `lifecycle` outside the
     documented set;
   - `session.usage_updated` whose `tokens` record fails the section 7
     shape: a counter missing, the counters half-null, a counter
     non-integer or negative, or `basis` disagreeing with the counters.
6. **applied**: `revision` = current + 1. Apply the payload, set
   current to `revision` and store `cursor`.

A rejected event changes nothing and its id is not remembered, so a
corrected re-delivery under the same id can still apply. The rules are
implemented in `web/src/events.js` and unit-tested with Node's built-in
runner (`web/tests-unit/events.test.js`, `npm run test:unit`).

The fixture file `web/fixtures/default-events.json` (schema
`odin.web.projection.events/v0-draft`) wraps an ordered `events` list
of such events, plus `base_revision`, the snapshot revision they
follow.

Expired cursor: the service answers a resume request with a fresh
snapshot. The client replaces its records and keeps selection, expanded
state and reading position by id. If the selected id is absent, the
view shows a not-found response and does not move the selection.

The transport is not chosen here. W4 records it.

## 5. Ancestry

- Tree edges come only from `parent_session_id`.
- `relationships` are overlays. They draw as typed links or badges,
  never as tree edges. A reviewer is never drawn as started by the
  worker it reviews.
- The projection never guesses. It does not infer ancestry from timing,
  layout or transcript wording, and it does not re-parent records.

| Case | Placement | Label | Fixture |
|---|---|---|---|
| Parent null, `provenance` `recorded` | Root | none | `ses-exec-01`, `ses-pin-exec` |
| Parent null, `provenance` `imported` | Root | "Imported — parent unknown" | `ses-imported-01` |
| Parent named, not in this project view | Root | "Parent not in this project view" | `ses-pin-audit` (parent `ses-pin-archived`) |
| Parent chain loops, including self-parent | Root, one per loop member | "Parent cycle in records" | `ses-mal-cycle-a`, `ses-mal-cycle-b`, `ses-mal-self` |
| Descendant of a loop member, not on the loop | Child of that member | none | `ses-mal-cycle-child` |

A loop is found by walking `parent_session_id`. If the walk returns to a
session already on it, every session on the loop is a labelled root.
Sessions below a loop member attach to it normally. The projection
reports these records and does not repair them.

## 6. Lifecycle identity

- **Resumption** is the same session: same id, plus
  `resumption: {count, resumed_from_host_session, resumed_at}`. The view
  adds no node; history shows the resumption. Fixture: `ses-docs-01`.
- **New attempt** is a distinct session: its own id, plus `attempt`,
  `attempt_of` and `previous_attempt`. Fixture: `ses-worker-a1`
  (attempt 1, run `failed`) and `ses-worker-a2` (attempt 2,
  `previous_attempt` `ses-worker-a1`).

`previous_attempt` may name a session that is not available. Fixture:
`ses-mal-attempt` names `ses-mal-gone`. The client shows a not-found
response for that link and does not guess a replacement.

## 7. Token usage and outcomes

Token usage covers the session's own turns, in four counters:
`uncached_input`, `cache_read`, `cache_write` and `output`, each a
non-negative integer or `null`. A `basis` of `measured`, `estimate` or
`unknown` records where the figures came from. The four counters are all
integers or all `null`, and `basis` is `unknown` exactly when they are
null. A half-known record is malformed: `session.usage_updated` events
carrying one are rejected (section 4), and the view reports a half-known
stored record as unknown, never as a partial sum.

The **headline figure** is `uncached_input` + `cache_write` + `output`.
Cache reads are excluded: they dominate long sessions and would swamp the
figure operators compare at a glance. The detail panel shows the four-way
split, cache reads included, with the headline labelled "Headline (excl.
cache reads)".

| `tokens` | Shown as |
|---|---|
| `basis` `measured`, integer counters | `48.2k tok` |
| `basis` `estimate`, integer counters | `est. 18.7k tok` |
| counters null, `basis` `unknown` | `unknown`. Never `0 tok`. |

Compact form: below 1,000 the integer itself (`850 tok`), below a million
one decimal on thousands (`48.2k tok`), then one decimal on millions
(`1.2M tok`).

Branch totals (a session and its descendants) and the project's header
total:

- Each session's own headline tokens are summed once. A parent's
  aggregate is never added to its children's.
- Append ` + unknown (n)` to the known sum, where n is the number of
  sessions in the summed set — the branch, or the project's sessions for
  the header total — whose own tokens are unknown.
- A set with no known tokens shows `unknown (n)` and no figure.
- If an estimate is in the sum, the total is marked `est.`.

A budget is `{limit_tokens, basis}`; the fixture basis is `requested` and
the values are arbitrary synthetic numbers, not real limits. The view
labels it, for example `2.0M tok (requested)`, and never enforces it.

Fixture examples: the `ses-pin-audit` branch shows `unknown (2)`. The
`ses-worker-a2` branch shows `est. 18.7k tok + unknown (1)`, with unknown
child `ses-helper-01`. The `proj-odin-webapp` header total shows
`est. 131.6k tok + unknown (3)`.

Outcomes are separate from activity. Ending or retiring a session does
not mark its run verified. Only a recorded run outcome of `verified`
shows "Verified". Other outcomes (`failed`, `unverified`, `unknown`)
show as recorded. `ses-worker-a2` is `ended` with run `unverified`.
`ses-helper-01` is `retired` with run `unknown`.

## 8. Shared fixtures

These are the candidate shared fixtures. A service could later emit
them unchanged.

| File | Content |
|---|---|
| `web/fixtures/default-snapshot.json` | Snapshot: 4 projects, 20 sessions, 8 relationships. Roots, nested children, reviewers, a resumption, attempts, an imported root, `host_offline`, unknown token usage, malformed ancestry. Token counters and budgets are arbitrary synthetic values. |
| `web/fixtures/default-details.json` | Transcript for `ses-worker-a2` only (34 entries, two pages, with a gap and raw markup) and evidence for `ses-worker-a1` and `ses-worker-a2`. Other sessions get a one-line generated placeholder transcript. |
| `web/fixtures/default-events.json` | Sixteen deliveries: `evt-001` to `evt-004` (state change, new child, usage update, retirement); `evt-002` delivered twice (duplicate); `evt-bad-1` to `evt-bad-9`, each rejected for one reason in rule 5 or rule 2 (unknown session, unknown type, non-integer revision, no session record, existing id, unknown lifecycle, no `session_id`, numeric id, unknown project); `evt-bad-6` re-delivered corrected, which applies at revision 5; and `evt-005` at revision 9 (gap). |
| `web/src/fixtures/large.js` | Seeded generator (seed 20261022) for the W2c set: 2,000 sessions, 40 roots, depth 8, 20 transcript pages of 50 entries per session. Generated at load time; no large file is committed. |

Draft JSON Schemas (2020-12) describe these shapes as the prototype
uses them. Each carries a `$comment` starting `DRAFT`; none is an
accepted contract, and none lives under `docs/contracts/`.

| Schema | Validates |
|---|---|
| `schemas/web-projection-snapshot.schema.json` | `default-snapshot.json` |
| `schemas/web-projection-session-detail.schema.json` | One per-session detail page (section 3) |
| `schemas/web-projection-details-fixture.schema.json` | `default-details.json` |
| `schemas/web-projection-event.schema.json` | One well-formed update event (section 4) |
| `schemas/web-projection-events-fixture.schema.json` | `default-events.json` as a delivery log, malformed deliveries included |

`tests/test_web_projection_schemas.py` validates every
`web/fixtures/*.json` file with the repository's Python contract
validator (`odin.contracts.Contracts`), builds every detail page the
synthetic loader would serve and validates it, and checks which
fixture events the strict event schema rejects. Referential faults
(unknown session, existing id, unknown project) are client rules, not
schema rules. The Go contract suite compiles these schemas with the
others; there is no Go fixture test and no service code.

## 9. Open questions for adoption

- Cursor expiry window: how long a cursor stays resumable before the
  service returns a fresh snapshot.
- Revision scope: per project or global. The gap rule depends on it.
- Redaction of transcript text: whether the service redacts before
  projection, and how gaps report it.
- Access-filtered snapshots: whether a snapshot can be filtered per
  caller, and how a hidden parent appears.
- `attempt_of`: the fixture stores an assignment id. Confirm whether it
  should name a session or an assignment.
- `session.started` for an id already present: upsert or reject.
- Event dedupe memory: how long `event_id` values are remembered.
- Schema naming and versioning: check the `/v0-draft` suffix against
  ODIN-ADR-008 (I0 record and event schemas) and ODIN-ADR-021
  (contract conventions) before adoption.
