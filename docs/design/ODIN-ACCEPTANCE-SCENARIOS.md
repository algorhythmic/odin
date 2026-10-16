# Odin acceptance scenarios and evaluation

Date: 2026-10-14. Status: proposed acceptance specification; no results are
claimed. Read with the [blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md) and
[ecosystem integration plan](ODIN-ECOSYSTEM-INTEGRATION.md). These scenarios
must agree with the [decision record](../DECISIONS.md) and the
[I/O contract](ODIN-IO-CONTRACT.md); a conflict is an issue to resolve before a
scenario is claimed to pass. Adapted for the Odin repository from extraction
snapshot `2026-10-14-14fdab3`
([frozen original](../history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-ACCEPTANCE-SCENARIOS.md));
identifiers AC-01 to AC-30 and DC-01 to DC-08 are unchanged. AC-31 and
AC-32 are added for ODIN-ADR-002. AC-28 and the
release scopes in §4 were corrected for the source review (B2, B5;
[`REVIEW-RESOLUTIONS.md`](../provenance/REVIEW-RESOLUTIONS.md)).
AC-33 to AC-36 specify ODIN-ADR-004–005; they are not executed tests.

**Where each check runs.** Odin owns these scenarios except AC-29, which is a
producer-side check at Saga: Odin's acceptance report cites Saga's result
against the pinned Saga contract and does not test Saga's internals. AC-28 is
split the same way: Saga's revision rule and its publication are checked at
Saga (pinned contract CT-18); Odin's part reconciles through the Saga API
only. Scenarios
that touch Saga (for example AC-01, AC-02, AC-03, AC-10, AC-27, AC-28, AC-30)
run first against the fake Saga backend (the I/O contract's Appendix B) and
count for a live deployment only when repeated against Saga after Phase B.
Peer scenarios (AC-12, AC-13, AC-17 to AC-21, AC-24, AC-25, DC-01 to DC-08)
need the peer's interface; until it exists, run them against fakes and label
the missing integration.

## 1. Demonstration: three documents to supervised work

The operator supplies three documents describing separate workstreams. Use
synthetic documents first, then one explicitly scoped real project before the
full demonstration. The fixture deliberately includes a shared interface,
an unresolved operator choice, and a final integration criterion.

| Document | Illustrative workstream | Deliberate coordination requirement |
|---|---|---|
| A: ingestion service | Parse an agreed input format and produce versioned records | Owns the shared record schema |
| B: operator interface | Display and filter those records | Depends on the approved schema; requires one product decision |
| C: reporting/export | Export a report and retain the result | Must use the same schema and pass an end-to-end integration check |

Do not assume three documents require three planners or exactly three workers.
The expected decomposition follows dependencies, scope and limits. The optional
desktop variant exercises an app export; the initial version can use CLI/API
operations without WCU.

### Walkthrough and observable evidence

| Step | Expected behavior | Evidence to retain |
|---|---|---|
| Intake | Register exact source versions; establish projects/commitments and ambiguities | Document digests, source refs, commitment revisions |
| Context | Supply mandatory current requirements; retrieve supplementary material if available | Briefing provenance, retrieval scope/source/index revisions |
| Plan | Propose bounded assignments, dependencies, owners and acceptance criteria | Versioned plan and artifact manifest |
| Review | Mechanical checks precede independent Mimir critique where required | Evidence packet, authenticated verdict, any bounded re-review |
| Authorization | Operator approves the exact proposal through the shared command path | Request, principal, proposal digest, expiry and authority receipt |
| Execution | Saga admits runs within the delegation; waiting dependencies remain queued | Run IDs, event sequences, refusal/acceptance and limit evidence |
| Workspace | Herdr exposes supported sessions by workstream; overview remains available | Explicit identity bindings and capability labels |
| Visibility | Skald shows configured source conversations; Heimdall shows native work and, once implemented, attributed external projections | Source coverage, project associations, imported revision/freshness |
| Human decision | B's explicit request reaches the operator without an unnecessary planning turn | Request/correlation IDs, delivery and response receipts |
| Reconciliation | Apply the answer to the correct assignment; wake the planner only if it changes the larger plan | Revision change and routing explanation |
| Verification | Individual run evidence and the final integration criteria determine completion | Exact artifacts, test/evaluator results and closure record |
| Preservation | Export selected material and distinguish local retention from confirmed publication | Manifest, local/commit/remote receipts or explicit pending state |

Display existing work alongside new work without reassigning it by cwd or title.
Opening Skald/Heimdall is not enough: demonstrate actual source enrollment,
bindings, and attributed state, or visibly label the missing integration.

## 2. Fault and interaction scenarios

Run these against synthetic fixtures and controllable fake backends first.
Use injected failures at named boundaries rather than destructive experiments
on the operator's active sessions. Repeat relevant scenarios against each real
adapter before claiming its capability.

| ID | Trigger | Required result |
|---|---|---|
| AC-01 | Deliver the same launch/message twice | One logical assignment/run/effect; duplicate recognized |
| AC-02 | Kill Odin after dispatch but before its receipt commits | Outcome remains unknown; reconciliation prevents blind duplicate dispatch |
| AC-03 | Restart Odin while workers continue | Resume ledger cursor; rebuild commitments; do not relaunch surviving workers |
| AC-04 | Replace a planning session | Fresh briefing restores unresolved commitments and sources; obsolete session cannot steer current ownership |
| AC-05 | Reply from Telegram after terminal already answered | One request resolution; no duplicated approval or conflicting silent overwrite |
| AC-06 | Modify the plan after its approval request | Old response cannot approve new content; new proposal binding required |
| AC-07 | Worker asks a structured question | Direct operator routing; evidence and options preserved; no Jev/planner call needed for delivery |
| AC-08 | Worker reports ambiguous routine prose | Evaluator may classify; uncertainty uses baseline; deferred events remain visible and bounded in age |
| AC-09 | Classifier times out, returns malformed data, or disagrees | Explicit unavailable/invalid/uncertain result; no removed gate or fabricated certainty |
| AC-10 | Operator stops a delegation while inference is hung | Direct control path pauses planner, cancels runs, disables schedules and revokes authority; unconfirmed backend effects remain explicit |
| AC-11 | Operator takes over a terminal session | Automated prompting stops for that session; return requires a recorded handoff and current-state reconciliation |
| AC-12 | Pane moves or another agent replaces its occupant | Binding is refreshed/re-established explicitly; stale target cannot receive guidance |
| AC-13 | Herdr reports `done` but tests failed | Assignment/project not marked verified; readiness is distinct from completion |
| AC-14 | All workers finish but combined system fails | Project stays open; evidence points to an integration assignment or revised plan |
| AC-15 | Document A changes after B and C start | Identify affected lineage; pause/review incompatible work; unrelated work continues |
| AC-16 | Two projects share a repository and similar titles | Separate identities, context scopes and bindings; no accidental cross-project reassignment |
| AC-17 | Native transcript and private export contain the same event | One origin/revision lineage; not two independent supporting sources |
| AC-18 | Source transcript disappears or has malformed/partial records | Archive retains captured bytes; coverage gap is visible; no claim of complete history |
| AC-19 | Skald, Heimdall, or Braid is unavailable | Core work continues with explicit visibility/retrieval limits; mandatory context remains available |
| AC-20 | Imported Heimdall projection is stale | Display source revision/age; commands revalidate at owner; native tasks remain usable |
| AC-21 | Braid returns a superseded or forbidden-workstream candidate | Scope excludes unauthorized content; supersession is honored; accepted current state wins |
| AC-22 | Mimir unavailable for a required review | Work waits/escalates according to policy; optional-feature flag does not waive the requirement |
| AC-23 | API/model budget reaches its limit | No new disallowed turns; interrupts/reviews respect their own hard caps; direct stop remains available |
| AC-24 | Push acknowledgement is lost | Reconcile intended commit on intended remote/ref; no false remote-confirmed state or duplicate commit |
| AC-25 | Preservation runs beside unrelated staged edits | Only selected files are committed; unrelated index/worktree state is retained |
| AC-26 | Redaction affects a record used in summaries and exports | Rebuild/purge derived state; track each destination; incomplete historical deletion is reported honestly |
| AC-27 | A stop, revocation or take-control arrives, then Odin crashes before processing it, with effects queued or unknown | On recovery, dispatch stays disabled; the control message is applied first; the queued effects are revalidated and cancelled or held; nothing is sent under the old authority |
| AC-28 | Guidance A's receipt is lost, guidance B is later delivered to the same run, then Odin reconciles A | Odin reconciles A only through Saga's operation lookup and event cursor, never by reading the broker; Saga reports A `superseded` because B's newer `guidance_rev` was delivered first; Odin marks A `superseded` and never resends it; B remains in place. Saga never replacing a newer revision with an older one is the Saga-side check (pinned contract CT-18) |
| AC-29 | A worker publishes on its run's `answers/` or `guidance` topic | The broker rejects it under the direction-specific ACL; the attempt is visible in Saga's logs; no answer or guidance record changes (Saga-side check; the transport named here is v7's proposal and Saga's pinned contract governs it) |
| AC-30 | An approval request expires and is reissued for unchanged content; the operator answers the new one | The answer resolves against the new request id and revision and is applied; it is not discarded as a duplicate of the expired request; the proposal digest still binds the content |
| AC-31 | Routine journal batches yield `no_attention`, `attention_required`, uncertain, unavailable or malformed triage; inject a mandatory event during triage | No-attention evidence and typed result persist without an immediate planner wake; attention queues a bounded coalesced wake; uncertain/failed/invalid triage queues original evidence for the planner without waiting for a successful report. Mandatory events bypass both triage and evaluator; shadow evaluator output cannot suppress the baseline. Missing source coverage is invalid, not silent success |
| AC-32 | A no-attention batch approaches its maximum age while no planner turns occur; restart, reclassify, then repeat under a budget pause | Original intake deadline survives restart and reclassification. A bounded digest schedules one batched wake by the default six-hour deadline; an earlier consuming turn prevents a redundant wake. Under a hard cap, retain the digest and expose overdue attention without claiming delivery or bypassing the cap. New batches cannot indefinitely postpone older evidence; consumption is recorded and original evidence remains reachable |
| AC-33 | A journal says all is well or instructs the router to ignore failures while a typed test-regression transition arrives; also replay with swapped option order and truncated evidence | Typed regression wakes regardless of evaluator output; no hosted request includes D9-protected content. Shadow results cannot alter baseline routing. Missing evidence/conflicting signals cannot qualify for deferral; record option-order sensitivity, Haiku disagreement and independently assessed outcomes |
| AC-34 | Compactor returns only thinking, empty text, refusal, truncated text, or a multibyte summary over 512 UTF-8 bytes; repeat until retry budget ends | No failed candidate becomes a valid node; original source and last valid view remain accessible; bounded retries stop and expose backlog/coverage limits. Validate both initial leaf summaries and merged nodes, with output allowance including thinking |
| AC-35 | Whole Haiku request crosses the configured headroom or 100,000-token boundary through tool history, cached input or an oversized raw leaf; repeat without adapter token telemetry | Direct-call preflight splits/defer inputs or applies a recorded configured exception; safe harness rotation preserves commitments. All observed threshold crossings are flagged; cached inputs count. Missing telemetry is explicit, never reported as zero usage or a proven hard limit; mandatory context is not silently discarded |
| AC-36 | Operator message lacks a project binding; a wake has conflicting session-class requirements; classifier suggests an approval, stop, model switch or new target | Operator target ambiguity returns to the shared command path without semantic routing. Code selects the configured capable class within budget or queues/escalates; no silent downshift or mid-session model change. Classifier output grants no authority; identity/request binding and direct stop checks still apply |

### Optional desktop cases

| ID | Trigger | Required result |
|---|---|---|
| DC-01 | Two workers request input on one seat | Only one valid input lease; second waits; separate MCP hosts cannot bypass shared enforcement |
| DC-02 | Human takes control or lease expires | No new automated input segments; resume requires fresh observation and ownership |
| DC-03 | Target/focus/frame changes before input | Existing WCU guards reject or stop; classifier score cannot override |
| DC-04 | Input submitted but result is uncertain | Preserve partial/unknown receipt; observe/reconcile before retry |
| DC-05 | UI says "saved" but artifact content differs | Exact saved-artifact check determines the outcome; semantic label is insufficient |
| DC-06 | Accessibility is missing or partial | Escalate to capable visual inspection; do not invent controls, OCR, or coordinates |
| DC-07 | Desktop text contains embedded instructions or restricted content | Treat it as untrusted data; it grants no authority and obeys provider data restrictions |
| DC-08 | Herdr layout needs updating | Use the structured workspace adapter; do not route terminal launch through desktop input |

## 3. Evidence and measurement

One evaluation run should record:

- Source-document and accepted-plan digests, initial state and task lineage.
- Repository commits plus dirty-tree snapshots/digests; installed tool, harness,
  model and adapter versions; declared capabilities and enabled features.
- Assignment/session/run mappings and chronological events with source identity.
- Routing decisions, human requests, verdicts, approvals and their exact bindings.
- Start/end time, model usage, evaluator/review/compaction cost, worker resources,
  operator interventions, and verification evidence.
- Missing observations, unavailable peers, unresolved effects, and preservation
  coverage. A transcript alone does not establish that an action happened.

Use trace identifiers to connect service, harness, Saga, review, retrieval and
desktop events. Counters must separate transport deliveries from model turns.
Record reviewer and human time as well as token usage. Do not infer provider
charges from serialized bytes or WCU screenshot dimensions.

### Comparative configurations

| Comparison | Question |
|---|---|
| Native harness vs Odin over that harness | Does supervision improve sustained completion and reduce intervention? |
| Native harness with equal extra budget vs Odin | Is the benefit more than additional inference spend? |
| Odin memory baseline vs OptChat/UniiChat | Does hierarchical memory improve recall, supersession and unresolved-commitment handling at comparable cost? |
| Odin without Mimir vs equivalent verification budget vs Mimir | Which defects are prevented, and which good plans are degraded? |
| Baseline routing vs shadow evaluator vs activated evaluator | Does attention cost fall without unacceptable missed requests or delay? |
| Existing WCU workflow vs textual decision-model workflow | Does verified task completion improve after model, approval and recovery costs? |
| Odin on first and second harness | Which outcomes depend on the adapter's missing capabilities? |

Keep execution/authority rules comparable across conditions. Where a required
review cannot ethically/operationally be removed from a live deployment, use
offline replay or a synthetic policy instead of bypassing the production gate.
Evaluate Mimir on frozen pre-review artifacts with independent outcome assessment.
Split retrieval/routing examples by artifact or conversation lineage so copies
do not leak between tuning and held-out evaluation.

**Memory comparison protocol (ODIN-ADR-003).** At I5 the baseline is rolling
summary plus structured notes, compared with OptChat/UniiChat memory. Both
arms use the same frozen fixture retriever, with pinned corpus/source
revisions, scope filters, query-to-result mapping and byte limits; the same
query returns the same ordered results. Freeze tasks, harness/model,
retention settings and total budget before measurement, and retain identical
authoritative commitments in both arms. Record actual queries, consumed
bytes and all compaction, summarization and retrieval costs. Reject a
comparison with unequal retrieval access; label fixture results as a
controlled memory comparison, not proof of live Braid/Skald integration.
After I6, repeat with the same live retrieval adapters in both arms and
disclose changed corpora or configuration. Phase G retains the final D18
comparison; production retention defaults remain a separate open question.

**Attention and compaction experiments (ODIN-ADR-004–005).** Pin evaluator
projection, options, order, threshold and model version before activation.
Report Haiku disagreement separately from independently assessed errors;
test injected prose, missing coverage and mandatory-event conflicts. Prefer
conservative deferral based on actionable-event false negatives and delay,
not a universal confidence cutoff. Include fallback and digest costs.

For compaction, compare `medium`, `high` and `xhigh` on identical synthetic
fleet/journal fixtures first, then explicitly scoped real migration data.
Set fidelity/latency limits before measurement; assess lost or changed ids,
numbers, negation, supersession, open commitments, empty/invalid replies,
retries and total cost. Jev's fidelity score is supporting evidence, not the
sole assessor. Select the least costly passing configuration and retain the
model, effort, thinking mode, output allowance and prompt revision. Triage
has its own workload and effort evaluation. Check a pinned gist revision
and its reported cache fix before code reuse; do not claim transferred
cache performance from the original replay.

### Primary measures

Verified outcomes per operator hour; missed commitments; false completion;
unauthorized or duplicate effects; recovery success/time; intervention delay;
unnecessary escalation; total operating cost; time to verified completion.

For attention classifiers, report actionable-event false negatives separately
from aggregate accuracy. For memory, test original evidence recovery, corrections,
superseded facts, project separation and intentional deletion. A high rate of
rewritten plans, fewer images, or a cheaper classifier call is not itself success.

Deterministic invariants above must pass before the associated integration is
enabled. Set workload-specific quality/latency thresholds before inspecting
evaluation results; record sample sizes and uncertainty. No universal worker
count, confidence threshold, or claimed performance gain is established here.

## 4. Release evidence by scope

- **Core proof:** I1–I3 in the blueprint, one project, lifecycle/restart/approval/
  verification scenarios, including direct stop. Peer TUIs and Jev are optional.
  Results against the fake backend (I1–I2) are development evidence; the core
  proof requires I3 against Saga after Phase B.
- **Parallel work proof:** I4, two or more projects, binding/takeover/ownership
  scenarios, one unresolved operator decision. Scoped archive capture joins
  with skald enrollment in I6; before that it is fixture work.
- **Ecosystem demonstration:** the full three-document walkthrough with actual
  attributed views and history retrieval; selection-based preservation only after
  dotprivate's release contract exists.
- **Memory evidence:** distinguish the I5 controlled fixture comparison from
  the repeated live-retrieval comparison after I6 and the final Phase G
  evaluation. Report each configuration and its limitations separately.
- **Desktop proof:** I7 and DC-01–08; no inference from headless fixture timings
  to complete model-driven performance.

Publish an acceptance report naming the configuration, observed results, failures,
unsupported capabilities, and remaining work. Never turn this checklist into a
claim of delivery merely because a document, adapter stub, or TUI exists.
