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

**Update of 2026-10-16.** ODIN-ADR-006 to 015 apply
([decision record](../DECISIONS.md) §4). The live range is AC-01 to
AC-41; AC-37 to AC-41 are proposed runtime scenarios for ODIN-ADR-006,
007, 009, 010 and 013, not implemented or executed. DC-01 to DC-08 are
unchanged. AC-20 is withdrawn and keeps its identifier; AC-19, AC-22,
AC-24 and AC-25 are re-scoped in place. The §1 review and visibility
rows, the §3 comparisons and the §4 release scopes follow the same ADRs.

**Where each check runs.** Odin owns these scenarios except AC-29, which is a
producer-side check at Saga: Odin's acceptance report cites Saga's result
against the pinned Saga contract and does not test Saga's internals. AC-28 is
split the same way: Saga's revision rule and its publication are checked at
Saga (pinned contract CT-18); Odin's part reconciles through the Saga API
only. Scenarios
that touch Saga (for example AC-01, AC-02, AC-03, AC-10, AC-27, AC-28, AC-30)
run first against the fake Saga backend (the I/O contract's Appendix B) and
count for a live deployment only when repeated against Saga after Phase B.
Peer scenarios (AC-12, AC-13, AC-17 to AC-19, AC-21, AC-38, AC-41, DC-01 to
DC-08) need the peer's interface; until it exists, run them against fakes and
label the missing integration. AC-20 is withdrawn; AC-24 and AC-25 now check
Odin's own package export (ODIN-ADR-012) and need no peer.

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
| Review | Mechanical checks precede independent critique by two reviewer positions where required (ODIN-ADR-013) | Evidence packet, each position's verdict, the service-combined authenticated verdict, any bounded re-review |
| Authorization | Operator approves the exact proposal through the shared command path | Request, principal, proposal digest, expiry and authority receipt |
| Execution | Saga admits runs within the delegation; waiting dependencies remain queued | Run IDs, event sequences, refusal/acceptance and limit evidence |
| Workspace | Herdr exposes supported sessions by workstream; overview remains available | Explicit identity bindings and capability labels |
| Visibility | One human view shows commitments (Odin), runs (Saga) and transcripts (capture module), each attributed to its owner; no heimdall projection (ODIN-ADR-007) | Source coverage, owner attribution, project associations, source revision/freshness |
| Human decision | B's explicit request reaches the operator without an unnecessary planning turn | Request/correlation IDs, delivery and response receipts |
| Reconciliation | Apply the answer to the correct assignment; wake the planner only if it changes the larger plan | Revision change and routing explanation |
| Verification | Individual run evidence and the final integration criteria determine completion | Exact artifacts, test/evaluator results and closure record |
| Preservation | Export the selected package, preserved by the chosen carrier (ODIN-ADR-012), and distinguish local retention from confirmed publication | Manifest, local/commit/remote receipts or explicit pending state |

Display existing work alongside new work without reassigning it by cwd or title.
Opening a view or a legacy TUI is not enough: demonstrate actual capture
enrollment, bindings, and attributed state, or visibly label the missing
integration. Native heimdall work appears only as imported commitments (AC-38).

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
| AC-19 | Skald, Heimdall, or Braid is unavailable. Re-scoped by ODIN-ADR-006 and 007: the capture module, a workstation-daemon sensor or the retrieval library is unavailable | Core work continues with explicit visibility/retrieval limits; mandatory context remains available. No task state is lost or hidden, because commitments never live in a sensor or in heimdall; the human view labels the missing source as unavailable |
| AC-20 | Imported Heimdall projection is stale | **Withdrawn by ODIN-ADR-007; identifier retained; replaced by AC-38.** No projection exists to check. Former result, kept for traceability: Display source revision/age; commands revalidate at owner; native tasks remain usable |
| AC-21 | Braid returns a superseded or forbidden-workstream candidate | Scope excludes unauthorized content; supersession is honored; accepted current state wins |
| AC-22 | Mimir unavailable for a required review. Re-scoped by ODIN-ADR-013: one or both required reviewer positions are unavailable | Work waits/escalates according to policy; neither an unavailable reviewer position nor an optional-feature flag waives the requirement. Approval needs both positions to approve, so one position's approval alone never yields an approved verdict |
| AC-23 | API/model budget reaches its limit | No new disallowed turns; interrupts/reviews respect their own hard caps; direct stop remains available |
| AC-24 | Push acknowledgement is lost. Retargeted by ODIN-ADR-012 from dotprivate to Odin's own package export | Reconcile intended commit on intended remote/ref by observing the ref before any retry; the receipt stays "committed" until then; no false "confirmed on the remote" state or duplicate commit |
| AC-25 | Preservation runs beside unrelated staged edits. Retargeted by ODIN-ADR-012 to Odin's own package export | Only the package path is staged and committed; unrelated index/worktree state is retained; receipts distinguish "copied locally", "committed" and "confirmed on the remote"; an export directory inside a dotprivate-managed `.private` clone is refused |
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
| AC-37 | The workstation daemon disconnects while one of its sessions holds an assignment; the operator issues a direct stop before it returns; then it reconnects | The host's bindings become `host_offline`; their sessions count as unavailable, not failed; nothing is retried while the host is away. Direct stop still works and reports the local outcome as uncertain. On return, reconciliation precedes any new turn. *Checks:* ODIN-ADR-009, with AC-10. *First exercised:* I2, fake backend |
| AC-38 | The one-time heimdall import runs twice on the same heimdall database; afterwards a task is edited on the heimdall side | One set of commitments, each carrying its heimdall identity and revision as provenance, and one import receipt; the second run adds nothing. The later heimdall-side edit is refused, or, where heimdall cannot refuse, ignored with a visible record; it never changes a commitment. *Checks:* ODIN-ADR-007; replaces AC-20. *First exercised:* I4, on a synthetic heimdall database; real data enters only through the scoped migration (I/O contract §14) |
| AC-39 | Attention prompts exceed a per-surface or per-day cap, overlap in subject, fall in quiet hours and repeat within the cooldown; the operator overrides one; repeat in shadow mode | Caps, coalescing, quiet hours and cooldown are enforced in code, not by prompt. Every prompt has a response record (done, snooze, dismiss, override with reason; expiry is recorded too); an override without a reason is not accepted. In shadow mode prompts are logged and never sent. *Checks:* ODIN-ADR-010, with AC-23. *First exercised:* shadow logging from I4 with the human view; exit from shadow in I6 |
| AC-40 | A required review goes to two reviewer positions; replay with one `REJECT`, with one `INSUFFICIENT_EVIDENCE`, with a disagreement that survives the single corrective re-review, and with one position unavailable | Both positions receive the same deterministic evidence pack and see neither Odin's reasoning nor each other's findings. Service code combines the verdicts: approval only when both approve; any `REJECT` or `INSUFFICIENT_EVIDENCE`, or disagreement after the single re-review, escalates to the operator with both positions and their evidence; agreement is logged without an operator message. An unavailable position never waives required review (AC-22). The combined verdict uses the format Saga already verifies; Saga accepting per-position verdicts would be a contract change (B-10) and is not checked here. *Checks:* ODIN-ADR-013. *First exercised:* I3 |
| AC-41 | Capture runs while the workstation cannot reach the service; the link returns; the same records are delivered again | Records, gaps and the checkpoint wait in the local spool and are appended to the transcript namespace as one atomic batch on reconnect; duplicates are deduplicated by (record key, source revision); gaps remain visible (AC-18). *Checks:* ODIN-ADR-006. *First exercised:* I2, on synthetic capture fixtures; live capture remains I6 |

AC-37 to AC-41 are proposed runtime scenarios; none is implemented or
executed. *Checks* names the rule a scenario enforces and *First exercised*
the increment where it first runs, against fakes unless stated.

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
| Single review vs two-position consensus vs single review with an equal extra verification budget (ODIN-ADR-013) | Does consensus prevent more defects than one reviewer or the same budget spent on verification, without degrading good plans or flooding the operator with escalations? |
| Code-selected session classes vs the best and the cheapest single-class baselines, with a task-level oracle as reference (ODIN-ADR-014) | Do the class defaults earn their cost against always using one class? |
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

**Reviewer-position and session-class evaluations (ODIN-ADR-013–014).**
Both belong to the D18 comparison. The consensus arm, single review and the
equal-budget baseline review the same frozen pre-review artifacts with the
same evidence packs and independent outcome assessment, on D8.7's measures.
ODIN-ADR-013 is a hypothesis: it stays only if the consensus arm beats both
alternatives. Report disagreements, escalations and per-position cost
separately, and do not assume independent errors before they are measured.
For session classes, use the same harness, fixed prompts, tools and graders,
the best and the cheapest single-class baselines, and a task-level oracle as
a reference, judged from the recorded class decisions and their rejected
alternatives. The records never change routing at run time; changing a
default on their basis needs D9.4's review, replay and shadow period, and a
learned model-tier router stays off. Neither the oracle nor this evaluation
exists yet.

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

- **Core proof:** I1–I3 in the blueprint (I0 supplies fixture evidence only), one project, lifecycle/restart/approval/
  verification scenarios, including direct stop. I0 delivers only the event log
  and record schemas with their duplicate, stale and unknown fixtures; the
  capability matrix, fake backend, three-document fixture and ownership mapping
  arrive in I1 (ODIN-ADR-008). Workstation sessions add AC-37 and AC-41 in I2;
  required review adds AC-40 in I3.
  Peer TUIs and Jev are optional.
  Results against the fake backend (I1–I2) are development evidence; the core
  proof requires I3 against Saga after Phase B.
- **Adapter control:** after I2's exit, the fixture-only Pi RPC control runs the
  same bounded assignment and session replacement against the fake backend and
  publishes its capability matrix and gaps (ODIN-ADR-015). Its results are
  fake-backend evidence and count toward neither the core proof nor Phase E's
  exit, which stays with the full second adapter in I5.
- **Parallel work proof:** I4, two or more projects, binding/takeover/ownership
  scenarios, one unresolved operator decision. The one-time heimdall import
  (AC-38) runs here on a synthetic database. Scoped archive capture joins
  with skald enrollment in I6; before that it is fixture work.
- **Ecosystem demonstration:** the full three-document walkthrough with one
  human view attributing commitments, runs and transcripts to their owners, and
  history retrieval; selection-based preservation through Odin's own package
  export with three-state receipts (ODIN-ADR-012; AC-24, AC-25), with no
  dotprivate prerequisite.
- **Memory evidence:** distinguish the I5 controlled fixture comparison from
  the repeated live-retrieval comparison after I6 and the final Phase G
  evaluation. Report each configuration and its limitations separately.
- **Desktop proof:** I7 and DC-01–08; no inference from headless fixture timings
  to complete model-driven performance.

Publish an acceptance report naming the configuration, observed results, failures,
unsupported capabilities, and remaining work. Never turn this checklist into a
claim of delivery merely because a document, adapter stub, or TUI exists.
