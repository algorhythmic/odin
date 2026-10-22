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
AC-33 to AC-36 specify ODIN-ADR-004–005; local checks cover parts of AC-36, not a full harness scenario.

**Update of 2026-10-16.** ODIN-ADR-006 to 015 apply
([decision record](../DECISIONS.md) §4). The live range is AC-01 to
AC-41; AC-37 to AC-41 are proposed runtime scenarios for ODIN-ADR-006,
007, 009, 010 and 013. Local component checks cover parts of AC-37 and
AC-41, while full scenario exits remain open. DC-01 to DC-08 are
unchanged. AC-20 is withdrawn and keeps its identifier; AC-19, AC-22,
AC-24 and AC-25 are re-scoped in place. The §1 review and visibility
rows, the §3 comparisons and the §4 release scopes follow the same ADRs.

**Model-orchestration and portfolio update, 2026-10-16.** ADR-020 adds the
comparison protocol and proposed AC-42–AC-44. ADR-022 adds the typed
portfolio, handoff and incident-grant protocol; its local fake-backend checks
are component evidence only.

**Human-view update, 2026-10-21.** ODIN-ADR-037 adds proposed AC-51–AC-57 for
ancestry, navigation, updates, reconnect, command results, accessibility and
desktop packaging. Synthetic prototype checks are component evidence only.
The live range is AC-01 to AC-57.

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
| AC-38 | The one-time heimdall import runs twice on the same heimdall database; afterwards a task edit is attempted on the heimdall side | One set of commitments, each carrying its heimdall identity and revision as provenance, and one import receipt; the second run adds nothing. The later heimdall-side edit is refused by enforceable retirement under EC-13/G-10 and never changes a commitment. An edit that succeeds on the source side but is ignored by Odin does not pass: migration remains incomplete. *Checks:* ODIN-ADR-007; replaces AC-20. *First exercised:* I4, on a synthetic heimdall database; real data enters only through the scoped migration (I/O contract §14) |
| AC-39 | Attention prompts exceed a per-surface or per-day cap, overlap in subject, fall in quiet hours and repeat within the cooldown; the operator overrides one; repeat in shadow mode | Caps, coalescing, quiet hours and cooldown are enforced in code, not by prompt. Every prompt has a response record (done, snooze, dismiss, override with reason; expiry is recorded too); an override without a reason is not accepted. In shadow mode prompts are logged and never sent. *Checks:* ODIN-ADR-010, with AC-23. *First exercised:* shadow logging from I4 with the human view; exit from shadow in I6 |
| AC-40 | A required review goes to two reviewer positions; replay all result-pair categories in I/O contract §10, including `FLAG`/`FLAG`, `FLAG`/`APPROVE`, `FLAG`/`APPROVE_UNCHANGED`, a `FLAG` paired with a negative result, matching approvals, mixed approving results, persistent disagreement, and one position unavailable | Both positions receive the same deterministic evidence pack and see neither Odin's reasoning nor each other's findings. Any `REJECT` or `INSUFFICIENT_EVIDENCE` escalates; every pair containing `FLAG` escalates under Saga ADM-7, including matching flags. Only matching approving pairs are logged without an operator message. A mixed `APPROVE`/`APPROVE_UNCHANGED` pair remains pending with no signed combined verdict until I0 defines its mapping. Disagreement after the single re-review escalates. An unavailable position never waives required review (AC-22). The combined verdict uses the format Saga verifies; Saga accepting per-position verdicts would be a contract change (B-10). `FLAG` admission and guidance-result semantics stay open under GAP-08/X-7. *Checks:* ODIN-ADR-013. *First exercised:* I3 |
| AC-41 | Capture runs while the workstation cannot reach the service; the link returns; the same records are delivered again | Records, gaps and the checkpoint wait in the local spool and are appended to the transcript namespace as one atomic batch on reconnect; duplicates are deduplicated by (record key, source revision); gaps remain visible (AC-18). *Checks:* ODIN-ADR-006. *First exercised:* I2, on synthetic capture fixtures; live capture remains I6 |
| AC-42 | A read-only `work` child attempts an edit, a side-effect tool, a service-credential read or a native/default child path with broader permissions; repeat with separate conversation but shared files | The effective profile denies the operation before execution across every enabled child path; a prompt or separate conversation is insufficient. Record conversation/process/filesystem boundaries independently. The service refuses the class on an adapter that cannot enforce it. *Checks:* I/O contract §7/§11, D19.4, D24.3. *First exercised:* I2 synthetic fixtures; repeat on the Pi control and later adapters |
| AC-43 | A child reaches its turn limit with partial output, returns an artifact path after failure, or reports after the assignment revision/parent ownership changes; repeat with a duplicate return | Transport completion, a path and fluent text never establish acceptance. Preserve status and evidence tied to the exact assignment/revision and session; stale or duplicate results cannot close current work. Retain useful artifacts for reconciliation, and keep the overall commitment open when integration checks fail. An unknown outcome is not blindly retried. *Checks:* D5/D6, I/O contract §2/§5/§9/§11; AC-02/AC-04/AC-14. *First exercised:* I2 with synthetic child results/fake Saga; live Saga evidence repeated at I3 |
| AC-44 | Concurrent children compete for the last shared budget allowance; usage is delayed/missing, a nested spawn is attempted, or the parent crashes/stops before child acknowledgements | Under the X-15 design, admission cannot allocate the same remaining allowance twice; configured count/depth and budget limits apply across every enabled child path. Record in-flight and unknown usage and unconfirmed stops; reconcile before redispatch. Never claim a hard dollar cap from a turn limit or delayed spend check alone. Direct stop stays available. *Checks:* AC-23, I/O contract §11, X-15. *First exercised:* I2 after X-15 is resolved, fake-backend evidence only |

| AC-45 | The portfolio coordinator issues a request for two projects, and one handoff carries a stale source revision or an ambiguous owner | Each project retains one accountable planning owner and separate commitment scope. Typed packets bind source and assignment revisions, objective, authority, dependencies, acceptance checks and budget; stale or ambiguous packets are held, and receiving one never grants execution authority or closes a commitment. *Checks:* ADR-022, D5/D7/D19. *First exercised:* I1 local fake-backend protocol; full runtime exit later |
| AC-46 | An incident grant is requested for one project/action, then used outside scope, after expiry, after revocation, and through a voice transcript | Only the operator's identity-bound recorded approval grants the exact action until expiry. Each exercise is recorded; out-of-scope, expired, revoked and voice-only attempts fail closed. Saga admission, required review and direct stop still apply. *Checks:* ADR-022, D2/D24. *First exercised:* I1 local fake-backend protocol; live identity/Saga repeat at I3 |
| AC-47 | A bounded chirality consultation sees uncertain or conflicting evidence and suggests an action | The response records source references, uncertainty, exact configuration and bounded use; it is read-only advice. No approval, route, edit, submission or completion follows from the suggestion. Missing or stale evidence is visible to the planning owner. *Checks:* ADR-022, ADR-020. *First exercised:* I1 local fake-backend protocol; model behavior remains unmeasured |
| AC-48 | Herdr displays a handoff or incident state, an adapter goes offline or returns unknown, and a voice input requests an approval | The display is regenerated from service records and cannot create authority. Lifecycle state and capability checks block unsupported session classes; unknown outcomes remain pending reconciliation. Voice is recorded with provenance but never supplies approval. *Checks:* ADR-022, ADR-009/010, AC-10. *First exercised:* I2 fixtures; live transports and data policy remain gated |

| AC-49 | A process restarts after storing a handoff; the source context changes while the receiver is offline; the packet is replayed | The durable packet and provenance survive restart. Intake compares the pinned source and assignment revisions, holds stale packets, and preserves the original evidence and dissent; replay never creates a second owner or silently refreshes authority. *Checks:* ADR-022, D5/D7, AC-45. *First exercised:* I1 local fake-backend protocol |
| AC-50 | Chirality is skipped, invoked within its configured budget, then returns dissent or an over-budget/unsupported response; repeat with a different exact model or harness path | Selection follows recorded deterministic eligibility; absence is explicit. The advisory response keeps its dissent, evidence, uncertainty, usage and exact requested/resolved configuration. Resource limits stop or refuse consultation without promoting advice to authority. Different model and harness conditions remain separately labelled for ADR-020 comparisons. *Checks:* ADR-022/020, AC-47. *First exercised:* I1 local fake-backend protocol; actual model comparison remains Phase G |

| AC-51 | A project's sessions include several roots, an imported session with no known parent, a nested child, two reviewer positions started by different sessions, a resumed session and a new attempt of the same assignment | The tree's edges are exactly the recorded ancestry; ownership, review, delegation and run association appear only as typed relationships. The imported session stays a root; nothing is inferred from timing, layout or transcript text. Resumption and the new attempt follow the lifecycle identity rules and are labelled differently. *Checks:* ODIN-ADR-037, ADR-013, I/O contract §10 web surface. *First exercised:* synthetic prototype; then I0 projection fixtures and I1/I2 fake backend |
| AC-52 | The operator selects a session, copies its link, reloads, opens the link in another window, then opens a link to a missing or inaccessible record | The detail panel shows that session's assignment, transcript, evidence and related run; the link restores the same project, session and selection after reload. A missing record gives a not-found response and an inaccessible one an access refusal from the service, each with a way back. *Checks:* ODIN-ADR-037. *First exercised:* synthetic prototype for routing; access refusal at service read integration |
| AC-53 | Updates arrive while a session is selected and its transcript is scrolled; a host goes offline; an observation ages; a cost is unknown or estimated; a session ends without verification | Selection and reading position are kept. `host_offline`, stale data, transcript gaps, unknown and estimated costs stay visible as text; unknown cost is never zero and parent aggregates are not counted twice. A session ending never marks its run verified. *Checks:* ODIN-ADR-037, D5, D20.6, ADR-036 accounting. *First exercised:* I1/I2 fake backend; static states in the synthetic prototype |
| AC-54 | The update stream drops, events are missed and some are redelivered; later the cursor expires | Reconnect resumes from the last cursor and applies missed events once, with no duplicate nodes or activity entries. An expired cursor is reported and the client replaces its state with a consistent fresh snapshot. Stale state is indicated while disconnected. *Checks:* ODIN-ADR-037, I/O contract §9 duplicate handling. *First exercised:* I1/I2 fake backend |
| AC-55 | The operator sends a conversation message, a lifecycle action, an unsupported action, a repeated submission, an approval for a proposal that then changes, and stop while the backend connection is lost | Each enabled command creates its service record and the UI shows the actual acknowledgement, rejection or uncertainty; a queued request is never shown as acknowledged. A repeat with the same idempotency key returns the original result. Unsupported actions are explained. Approval controls show and submit the request id, revision and proposal digest; a changed proposal invalidates the old approval context. Stop reports acknowledged and uncertain outcomes separately. *Checks:* ODIN-ADR-037, ADR-010, D20.5, AC-06, AC-10, AC-30. *First exercised:* operator command integration against the fake backend; live at I3 |
| AC-56 | A keyboard-only user, a narrow phone layout, an unauthenticated or unauthorized request, and a transcript containing markup, scripts and links | The tree has an equivalent list navigable by keyboard, and state is conveyed by text as well as colour. Narrow layouts keep conversation and decision actions usable. Unauthenticated or unauthorized access is refused by the service; transcript markup is shown as text and executes nothing; no model credential reaches browser code or frontend storage. A large synthetic tree stays usable with collapsed branches and paginated details against a recorded dataset size and performance target. *Checks:* ODIN-ADR-037. *First exercised:* synthetic prototype for keyboard, layout and rendering; service read integration for access |
| AC-57 | On Omarchy the operator starts the launcher, works, closes the window, reopens it, and also opens the same address in an ordinary browser | The launcher opens a dedicated Chromium app window with its own identity. Closing it stops no session and loses no work; reopening restores usable navigation and deep links and reconnects. The ordinary browser reaches the same records. *Checks:* ODIN-ADR-037, ADR-009. *First exercised:* desktop delivery; needs manual desktop evidence |

AC-37 to AC-57 remain proposed full runtime scenarios. Local component
evidence does not establish real child confinement, provider budget enforcement
or live Saga behavior. *Checks* names the rule a scenario enforces and *First exercised*
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

### Model and delegation comparison protocol

ODIN-ADR-020 applies to D18 and the early adapter control. The supplied
research is indexed in the
[review](../provenance/MODEL-ORCHESTRATION-REVIEW.md); it provides candidates
and failure cases, not production defaults.

1. **Qualify the condition.** Pin available exact models, harness/adapter
   versions, tools, permissions, data policy and billing mode. Separate
   local read-only children from Saga execution and reviewer positions.
   Unsupported configurations are reported as such. A worker family in a
   catalog is not proof of a directed pairing; an alias must have an
   observed resolution or remain unknown.
2. **Freeze the assignment first.** Use identical task packets containing
   objective, authoritative source versions, acceptance checks, dependencies,
   allowed scope, budget and expected evidence. Hold the lead, harness,
   tools and context fixed while changing a child model. Separately vary
   the lead with a fixed child pool, and the harness with fixed models
   where supported. Changing all three is a system comparison, not an
   isolated model effect. Evaluate fresh versus resumed children separately
   if that capability is supported; reuse is not assumed to be cheaper.
3. **Then measure complete episodes.** Include the lead's decomposition,
   dispatch, integration, checking, repair and stopping. Stratify tasks by
   independent versus tightly dependent work, task type and context length.
   Include cases where no delegation is useful, plus the three-document
   integration fixture. Do not force a worker per document or an arbitrary
   fan-out. Compare the controls in the table before attributing benefit to
   heterogeneity; a same-model sampling arm includes its selection cost.
4. **Control resources explicitly.** Operational defaults, whole-episode
   dollar caps and deadlines are distinct experiments. Record actual
   usage, cache behavior, infrastructure, timeouts, concurrency, depth and
   stopping limits. Equal effort names or token counts across providers
   are not equal compute. Fix resource policy and counterbalance trial
   order; separate transport/infrastructure failures in diagnosis while
   retaining them in end-to-end outcomes and cost.
5. **Use independent outcomes.** Prefer executable or final-state checks.
   For semantic assessment, freeze a task-specific rubric, blind model
   identities, randomize answer order and calibrate the grader against
   human judgments, checking family preference. The planner and required
   reviewer positions are not their own success oracle. Report false
   acceptance, false rejection, good-plan degradation and correlated
   reviewer misses. Offline controls never waive live approval/review.
6. **Repeat and preserve failures.** Split tuning from held-out task
   lineages; use paired repeated trials with sample sizes and uncertainty.
   A 20–30 task pilot can reveal failures and estimate variance but cannot
   confidently rank close systems; size further work for the useful effect.
   Do not condition the main result on only successful delegated tasks.
   Publish unsuccessful cases and capability/telemetry gaps with successes.

These comparisons do not add a production advisor tool, learned router,
framework or new hook. Required cross-provider permissions and credentials
remain prerequisites, including X-13 for review. Early I2/Pi results are
labelled fake-backend evidence; canned responses establish no model-quality
result, and actual model trials on synthetic tasks establish only the
measured workload's results. Neither establishes live Saga recovery or its
guarantees. Full portability remains I5 and the final comparative report
Phase G.

### Primary measures

Verified outcomes per operator hour; missed commitments; false completion;
unauthorized or duplicate effects; recovery success/time; intervention delay;
unnecessary escalation; total operating cost; time to verified completion.

For each condition report attempted and accepted task counts, all-episode
cost (including unsuccessful attempts), unconditional mean cost, cost per
accepted task, p50/p95 elapsed time and deadline success. Cost per accepted
task is total cost divided by accepted count; zero accepts makes the ratio
undefined. Missing prices/usage make full cost unknown: report the known
subtotal and coverage, not zero or a claimed saving. Include lead, children,
review, compaction, evaluators, tools, retries and repair without double
counting parent-inclusive totals; state the allocation rule for background
cost. Repricing an identical token log is illustrative accounting, not
evidence that another model would behave the same.

Measure elapsed time from original submission to verified completion,
including queueing, joins, synthesis and repair. Completion-latency
percentiles describe completed trials and must show their denominator;
report time-to-failure/cutoff and deadline misses for the rest rather than
silently dropping them. Summed child durations are a separate utilization
measure. Also report spawn/reuse/consultation counts, root-versus-child
usage, regression and intervention rates, and unnecessary delegation.
Attribute failures to decomposition/dependency errors, missing or stale
context, execution, transport, incorrect acceptance/rejection, premature
stopping or unresolved cause, retaining evidence for the attribution.

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
