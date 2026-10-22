# Odin product implementation plan

**Status: local implementation underway; live gates remain open.** Based on the supplied *Odin Product
Design* discussion and the repository baseline at `899df14`. This plan
does not record new ADRs, close issues or change the existing I0–I7 gates.
The [decisions](../DECISIONS.md), [I/O contract](ODIN-IO-CONTRACT.md),
[blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md) and
[roadmap](../ROADMAP.md) retain their authority.

Build a dependable **“resume my work” experience first**: show what changed,
preserve outstanding obligations, prepare the decisions that need the
operator, and identify stale or unavailable evidence. Then connect that
continuity layer to Fable → Astra coordination and, after Saga's gates,
bounded worker execution. Give memory explicit status, time and provenance
before investing in a more elaborate compactor.

Execution is recorded in [product implementation status](../PRODUCT-IMPLEMENTATION-STATUS.md).
The prototype baseline is preserved at `47e074e`; ADR-023 records the local
continuity/memory scope. The starting-point comparison below describes the
original planning baseline, not the current file inventory. Component tests
do not complete the live work packages.

The first useful release should reduce repeated context and unnecessary
interruptions. A sophisticated model hierarchy is an experiment within that
product, not its acceptance criterion.

## Starting point and reuse

There are two distinct baselines. Reconcile them before estimating the
remaining implementation effort.

| Baseline | Evidence available | Consequence |
|---|---|---|
| This checkout at `899df14` | Documentation scaffold, metadata schemas and documentation validator; ADR-001 to ADR-015 | No runtime implementation or runtime tests can be claimed here. Start with I0 if no later work is integrated. |
| Referenced `96c6/odin` checkout | Uncommitted Python service, Go contract validator, synthetic fixtures, coordination/chirality components and implementation status; local ADR-020 to ADR-022 and X-15 | Candidate implementation to review and integrate. Its reported 79 Python tests and other checks are synthetic evidence, not reproduced results of this planning task or proof of full I1/I2 completion. |

The newer status file explicitly leaves full Appendix B compatibility,
real harnesses, authenticated host transport, live dispatch, audio and Herdr
process integration unfinished. Native children are disabled in its tool
boundary. The implementation is therefore more than a design sketch, but
it is not an operational Fable/Astra chain awaiting a single switch.

Prefer a reviewed integration of useful prototype work over recreating it.
Pin a commit or a complete snapshot of its changes: its base commit alone
does not identify the implementation. Reconcile ADR-020/021/022 and X-15
with the target branch rather than silently treating sibling-worktree
decisions as current here. Preserve existing identifiers and reserved
conditional ADR-016 to ADR-019.

The discussion's correction about Past determines the memory scope:
**apply transferable design ideas to Odin**. Hosted Past adoption, its
plugin, commercial pricing and vendor benchmarks are not dependencies or
success criteria for this plan.

## Product behavior and responsibility

Fable, Astra, Opus and Sol below are the discussion's experimental model
allocations. Pin requested and resolved model/provider identities, effort,
harness versions and capability profiles when configuring a trial. These
labels do not establish availability, comparative quality or new deployable
names.

| Component or role | Owns | Enforced boundary |
|---|---|---|
| Fable portfolio coordinator | Operator continuity, priorities, clarification, prepared decisions, authorized portfolio summaries | Requests work through service tools; does not become a second project planning owner or receive service credentials. |
| Astra project planning owner | A scoped plan, assignments, integration and continuation within authority | One active owner per project; feature sessions have bounded assignments and cannot independently own the same commitment. |
| Opus/Sol workers | Bounded implementation assignments and evidence-bearing returns | Execution with external effects goes through Saga. A harness child is not a substitute for a Saga worker. |
| Independent reviewer positions | Required assessment against the same evidence pack | Separate from authors and conversational synthesis; deterministic service combination, with unresolved dissent sent to the operator. |
| Odin service | Records, ownership, admission, scheduling, budgets, command intake and recovery | Code checks authority before tools and again before dispatch. SQLite is authoritative; human-readable views are projections. |
| Workstation daemon and session host | Local sessions, capture, host status and surface adapters | Acts on service commands; offline bindings remain unavailable until reconciled. |
| Saga | Worker admission, approval, execution limits and authoritative run evidence | Only its published, pinned API is consumed; Odin's mirror stays read-only. |

Keep Fable involved at goal formation, meaningful milestones, scope changes
and escalations. Astra continues authorized independent work while a
decision waits. Required review remains separate from both hierarchy and
optional chirality.

## Decisions and prerequisites

Prepare concrete ADR changes and enforcement evidence during the work
packages below. Operator choices gate the affected capability, not unrelated
fixture work. No timeout or unanswered question grants permission.

| Decision or dependency | Recommended proposal | Required before |
|---|---|---|
| Baseline and portfolio scope | Integrate reviewed prototype components; reconcile ADR-020/021/022 and X-15. Define Fable's authorized portfolio projection above one owner per project. | Treating the prototype or its portfolio design as the selected implementation baseline |
| Earlier product slices and adapter sequence | Permit a local continuity/decision view during I1/I2 preparation. Bring a narrow Codex integration forward after the first Claude harness path, retaining the ADR-015 Pi control unless separately amended. | Claiming an early live Fable/Astra chain or an early human view as an approved sequence change; full second-adapter exit currently remains I5 |
| X-11 storage topology | Review the prototype's one-WAL-file-per-namespace choice; document writer processes, Unix ownership, spool recovery and failure domains. | I1 storage implementation; production isolation remains a separate check |
| X-12 credentials and billing | Dedicated Odin credential lineage, protected host store, one refresher, explicit service reference and spending mode; no development-login fallback. | Any real local model session |
| X-13 data policy | An explicit matrix of project data classes, permitted providers, transcript retention and audio handling. | Cross-provider context, a second-provider reviewer, live chirality or voice leaving backlog |
| X-10 and memory semantics | Define bounded compactor context; propose statement status, authority/scope rules, temporal meaning, retention and correction behavior. | New semantic memory schemas and real compactor integration; resolve reuse terms before incorporating third-party material |
| X-15 from the newer prototype | Specify shared reservations, count/depth limits, usage attribution, crash reconciliation and confirmed stop per adapter. | Native child dispatch; required limits without an enforcement mechanism cause refusal |
| X-7 and Saga producer gaps | Resolve guidance verdict meaning and published wire/identity contracts at their owner. Hold ambiguous guidance meanwhile. | Review/guidance schemas affected by X-7 and live guidance publication |
| Saga Phase B and source-review gates | Obtain producer evidence for the CLI boundary and Appendix B; pin the supported contract and recheck compatibility. | I3, any live delegated run, live Saga submission or deployment cutover |
| X-1 and documentation handoff | Reconcile phase wording with Saga and complete the ownership review in the owning repositories. | Calling the exception jointly approved or the documentation handoff complete |

Herdr inspection remains I3 and full management I4 unless explicitly
amended. Voice remains optional. Peer imports and consolidation still need
G-9/G-10 and X-14; desktop input remains I7 with its own authority decision.
None is required to prove the initial local continuity slice.

## Delivery sequence

The following are plan work packages, not replacements for I0–I7. Each can
be split into small changes with the stated exit evidence. Engineering owns
implementation and checks; the operator owns policy choices; Saga and peer
maintainers own their published interfaces. Dates should be assigned after
baseline reconciliation and the first adapter probe.

| Package | Deliverable | Depends on | Existing increment relationship |
|---|---|---|---|
| PLAN-01 | Reconciled implementation baseline and capability inventory | None | Establishes what remains of I0/I1; adopts no completion claims by test count |
| PLAN-02 | Durable records and minimal continuity view | PLAN-01; X-11 for storage | I0 contracts first, then I1 core; early product-view placement is proposed |
| PLAN-03 | Source provenance, temporal status, freshness and invalidation | PLAN-02; memory semantic decision | Extends I1/I2 preparation; does not move live retrieval from I6 |
| PLAN-04 | Resume briefing and operator decision queue | PLAN-02; PLAN-03 before declaring freshness reliable | Early useful slice; not full I2/I4 exit |
| PLAN-05 | Real session host and typed Fable/Astra handoff | PLAN-04, portfolio/sequence decisions, X-12/X-13 | First Claude harness path in I2; narrow earlier Codex path needs amendment |
| PLAN-06 | One governed project through Saga | PLAN-05 and Saga Phase B/source-review gates | I3, including scoped migration and shadow evidence |
| PLAN-07 | Controlled memory, orchestration and attention evaluation | Fixtures can begin after PLAN-03; real trials need their launch gates | I2 compactor checks, I5 comparison, I6 repeat, Phase G report stay distinct |
| PLAN-08 | Workspace, voice and other optional integrations | Relevant prior packages and peer/operator gates | I4–I7 as currently recorded |

The primary path is PLAN-01 → PLAN-02 → PLAN-03/04 → PLAN-05 → PLAN-06.
Once interfaces are stable, fixture design, adapter probes and experiment
instrumentation can proceed independently. Do not make full compaction,
Herdr control or voice prerequisites for demonstrating continuity.

### PLAN-01 Reconcile and preserve the useful prototype

1. Inventory the newer checkout's tracked and untracked changes without
   overwriting them. Select a reviewable integration boundary for contracts,
   service core and coordination; preserve source revisions and provenance.
2. Reconcile documentation and ADR differences. Keep unresolved producer
   semantics explicit, including the fake's incomplete Appendix B coverage.
3. Reproduce checks from the selected baseline using its pinned dependencies.
   In the prototype, `make check` covers documentation, shared Go/Python
   fixtures and runtime tests; it does not exist in this scaffold.
4. Add a capability inventory with **usable now / fixture-tested / planned /
   blocked**, evidence revision, blocker and next action. A fake run is always
   labelled fake-backend evidence.

**Exit:** one identified baseline, reproducible checks, reviewed local
decisions, and a gap list separating implementation, operator and producer
work. If integration is unavailable, implement I0 then I1 from the existing
contract instead; do not assume the later modules exist.

### PLAN-02 Establish durable continuity

Complete the unaffected I0 schemas and shared Go/Python valid/invalid
fixtures first. Defer X-7-sensitive Review/guidance schemas. Then build or
reuse the transactional core: namespace writers, revision checks, inbox and
cursors, outbox, stable operation IDs, explicit unknown outcomes, scheduler,
direct stop and regenerated views.

Commitments, assignments, pending requests, accepted decisions and ownership
are structured service records. Persist checkpoints continuously; a polite
end-of-session ritual must not be necessary for recovery. The minimal local
view lists each project's objective, owner, progress, unresolved commitments,
next decision, dependency and next trigger. Read these directly from records
before adding model-written narrative.

**Exit:** a synthetic three-document workflow survives process death before
and after commit, duplicate intake, stale writes and a lost fake submission
receipt. Recovery preserves obligations, one logical effect and unknown
outcomes. A corrupt or deleted view regenerates from state. This supplies
scoped local evidence for AC-01/02/03/27; it does not close all of I1.

### PLAN-03 Make remembered information inspectable

Implement the proposed data model in the next section using additive schema
migrations and shared cross-language fixtures for new contract shapes.
Start with deterministic imports of accepted decisions and service records;
use model extraction only for statements requiring interpretation.

Add per-source freshness policies, source-to-derived dependency tracking,
permission-aware retrieval and durable invalidation. A source correction,
access change or redaction must make affected output ineligible immediately,
even if regeneration is delayed. Build a synthetic history containing old
imports, contradictory reports, abandoned proposals and delayed processing.

**Exit:** every displayed claim has exact supporting source revisions and
scope. Import time cannot override authority or effective time. Stale and
unavailable sources are distinguishable, access revocation survives caches,
and redaction stays pending until each required destination confirms it.

### PLAN-04 Deliver resume and prepared decisions

Implement a single recorded command path for a resume request and decision
responses. Initially expose a deterministic CLI/text view, with a bounded
model rendering added through PLAN-05. This avoids making an operator
surface integration a prerequisite for proving the records.

A resume briefing contains changes since the operator's last acknowledged
view, active and blocked projects, outstanding decisions, stale or unavailable
integrations, and a recommended next action. Track delivery and acknowledgement
separately so a lost response does not advance “last seen.” Apply a byte/token
budget by session class; mandatory obligations come from records and remain
enumerable even when narrative detail is omitted.

Each decision item includes the question, recommendation, relevant evidence,
prepared artifact, exact action/scope that answering would authorize,
remaining blockers, urgency and linked commitments. A revision-bound response
must be revalidated if scope, evidence or the proposed action changes.
Expiring a request never closes its underlying commitment. Dedupe repeated
requests; notify on meaningful changes under the existing attention policy.

**Exit:** after abrupt service/session loss, the operator can resume without
restating the goal, find every unresolved obligation, understand what a
response authorizes and see any evidence gap. Independent authorized work
continues while a decision is pending. Prove this with synthetic inputs before
any real-history pilot or cutover under I/O contract §14.

### PLAN-05 Connect sessions without weakening service control

Build or complete the workstation daemon's authenticated outbound connection,
stable host identity, heartbeat, environment probe, durable capture spool and
credential reference. Implement the Claude Code Agent SDK adapter first.
Probe start/resume, interruption, transcripts, permission relay, profiles,
model/effort resolution and budget enforcement on the exact installed version.
Refuse a session class when its required capability cannot be demonstrated.

After the sequence decision, test Codex app-server as the discussion's
candidate Astra transport. Verify its actual supported interface before
pinning it. Keep the first adapters concrete; extract shared abstraction only
after a second implementation demonstrates what is shared. Preserve the
fixture-only Pi control required by ADR-015 unless explicitly revised.

Use a typed handoff containing project, commitment and assignment identities;
original requirements and acceptance criteria; artifact/source revisions;
ownership generation; permitted actions/tools; grant and budget references;
deadline; decisions, dependencies and expected evidence. A worker return
contains artifacts, checks and results, unresolved issues and usage. It is
eligible for verification, not automatically accepted completion.

The service rechecks current owner, assignment revision, grant scope/expiry,
revocation, stop state and budget immediately before dispatch. A recorded
receipt proves historical acceptance only. Incident intervention uses a
named, time-limited grant, and credentials are resolved outside model context.
Expansion of an incident's scope returns to the operator.

**Exit:** a bounded assignment and its briefing survive session replacement;
duplicate handoffs, late returns, ownership transfer, revoked grants and an
offline/reconnecting host produce correct holds. A planning session cannot
reach service credentials or worker/desktop tools. Real session evidence is
reported separately from fake-backend workflow evidence. Complete the existing
I2 compactor and lifecycle checks before claiming I2 exit.

### PLAN-06 Run one project through Saga

After Phase B evidence and the producer pin are available, implement Saga
compatibility checks and the real adapter for admission, approved submissions,
cursor consumption, operation lookup, stop and reconciliation. Validate the
operator identity and hash-bound approval path; configure the required
independent reviewer positions and protected signer. Hold unresolved guidance
under X-7. AC-29 remains a Saga-side check.

Execute the inherited three-document demonstration on one scoped project.
Separate worker termination, verification and integration acceptance. Inject
lost receipts, stale approvals, revoked authority, service/host death and stop
while a result is uncertain. Perform the scoped import and shadow/cutover
steps in I/O contract §14; keep real histories and runtime state outside the
repository. Establish backup/restore and disable/reconcile procedures before
cutover, without reviving a second editable task store.

**Exit:** one authorized project completes with inspectable artifacts and
independent evidence; CLI and Odin face the same refusal rules. Restart and
stop work across the service, host and Saga boundary, with unknown outcomes
visible. Passing local or fake checks cannot substitute for this report.

### PLAN-07 Evaluate usefulness and optional reasoning

Instrument the first synthetic continuity flow, then run a small operator
pilot after the required real-session, migration and deployment gates. Record
a baseline before changing the memory or model arrangement. Set workload,
acceptance thresholds, spending limits and run count before measurement;
choose sample size after a variance pilot rather than treating a few sessions
as a model ranking.

Keep three experiments separate:

| Experiment | Controlled comparison | Decision it informs |
|---|---|---|
| Semantic memory | Same rolling summary/retrieval baseline, with and without typed status, time, provenance and freshness; then ablate costly additions | Which additions reduce unsupported/stale claims and corrections |
| Compactor | ADR-003: rolling summary plus structured notes versus the summary tree, with identical frozen fixture retrieval, authoritative commitments and downstream configuration | Whether the tree earns its complexity; repeat with equal real adapters after I6 |
| Model arrangement | Single planning owner, added solo effort, repeated same-model samples and Fable/Astra hierarchy; separately add selective chirality | Whether coordination or independent advice improves accepted outcomes at comparable total resources |

Use paired repeated trials with held-out task lineages and independently
assessed outcomes. Pin prompts, models, effort, tools, permissions, source
revisions, retention and accounting. Count failed attempts, synthesis, repair,
review, compaction and retrieval; missing usage remains unknown. Keep required
review in every live comparison.

Chirality is optional advice for a named consequential question: two isolated
initial responses to the same versioned evidence pack, each with evidence,
assumptions, objections, recommendation and what would change it. Permit at
most one targeted follow-up, then preserve unresolved disagreement. Reserve
the combined budget before launch and reconcile delayed usage. Synthesis
cannot turn required reviewer dissent into approval.

**Exit:** report accepted outcomes, cost per accepted task, total spend,
elapsed time, operator effort and failures. Retain only additions that improve
the chosen workload against their controls. A failed experiment can remove
chirality, a hierarchy or the summary tree without losing canonical records.

### PLAN-08 Add integrations when the core earns daily use

Implement Herdr read-only inspection at I3 and lifecycle/workspace management
at I4 against a confirmed, pinned interface. Bind every visible session to
service identities. Pane text, terminal input and lifecycle observations
cannot establish authorization or assignment completion; direct operator
interaction must enter the recorded command path.

After X-13, test dictation as input, then separately evaluate spoken replies,
cancellation and interruption. Determine installed-version support and data
flow during the spike. Keep voice-origin provenance and recognition uncertainty;
do not use voice as an approval or grant channel in this plan.

Retain I6 placement and producer gates for capture/archive retrieval, braid,
evaluators and preservation. Treat corrections as proposed improvements:
classify fact, preference, procedure or authority; identify scope; attach a
regression case; review where required; then make a versioned update. Inferred
preferences cannot expand authority. Desktop control and repository
consolidation remain separate gated projects.

## Proposed memory records and processing

These are design candidates for PLAN-03, not schemas already present in this
checkout. Use validated JSON/YAML at machine boundaries and SQLite records
internally. Extend existing canonical records where appropriate rather than
creating another task or approval store.

| Record or projection | Minimum information | Meaning |
|---|---|---|
| Source revision | Stable source/project identity, revision and digest, producer identity, source locator/span, permissions revision, event/effective time when known, observation time, retrieval time and ingest sequence | Exact evidence and its age; unknown times remain unknown. Re-reading a cache only updates retrieval metadata. |
| Derived statement | Kind, explicit status, attributed speaker, project/scope, authority reference, supporting source revisions/spans, effective interval, recorded time, extraction configuration | Distinguishes observations, claims, preferences, proposals and reports. An extracted “decision” must reference an accepted decision record to be treated as authoritative. |
| Statement relationship | Corrects, supersedes, disputes or retracts; both identities, scope and supporting evidence | A later import or speculative comment cannot silently replace an accepted decision. Preserve competing claims when authority is unresolved. |
| Derivation dependency | Source/statement/summary edges, exact input revisions, transformation configuration, output revision and inherited access restrictions | Identifies what must be invalidated or rebuilt and explains why Odin believes a claim. |
| Processing state | Per-producer capture cursor, contiguous processed cursor, gaps, failed source identities, pending invalidations and policy revision | Shows coverage without pretending different producers have one global event order. |
| Freshness policy | Source class, authoritative refresh method, allowed age or revision check, consequence class, refresh/warn/hold action | Historical decisions and live worker status use different policies; freshness never confers authority. |
| Briefing cache | Project/portfolio scope, audience and permissions revision, source dependency set, coverage, created/expiry times and configuration | A disposable bounded projection. Revalidate access and dependencies on read. |

Keep canonical commitments and accepted decisions separate from derived
statements. Reading a remembered rule never creates a grant; a worker's claim
that tests passed remains a report until authoritative evidence supports it.
Scope and authority determine supersession before recency is considered.
Record both when information applies and when Odin learned it, so a query
can distinguish “known then” from “applicable then, learned later.”

The processing path is capture → validate/dedupe → durable source revision →
deterministic projection or bounded extraction → dependency recording →
briefing/retrieval. Source text is untrusted data throughout. Extraction has
no authority tools; malformed output is rejected, with bounded retries and
visible failed processing. Commit a derived revision and its dependencies
together so restart cannot expose an unexplained claim.

Use three context layers: a compact standing briefing from authoritative
records, structured views of decisions/preferences/conflicting claims, and
task-specific source excerpts retrieved within a budget. The summary tree
remains a candidate for narrative continuity. Recent unprocessed sources may
be supplied as clearly marked raw evidence within a bounded allowance; a
watermark gap is never described as “nothing relevant found.”

Portfolio views contain only authorized project summaries and references.
Derived content requires access to every contributing restricted source;
do not broaden access by summarizing or moving it into a portfolio cache.
Permission checks apply during retrieval and again when serving cached
content. A project rename changes its label, not its stable identity.

For correction, append the source/statement relationship and invalidate
affected derivations transitively. For redaction, apply the existing
tombstone and per-destination propagation protocol, including exports and
backup policy. Audit entries retain identities and actions without retaining
redacted content. Regeneration and deletion retries are idempotent and their
outstanding work survives restart.

## Enforcement and acceptance backlog

These plan-local checks must become executable regression cases with the
owning package. They supplement existing AC identifiers; allocate any new
AC identifiers only after reconciling the newer checkout's AC-42–AC-50.

| Check | Scenario and required evidence | Owner |
|---|---|---|
| PLAN-C01 | Crash before/after each durable handoff or checkpoint, replay intake and lose a receipt; retain obligations and one logical effect, with uncertain outcomes explicit. | PLAN-02/05/06; existing AC-01/02/04/27 |
| PLAN-C02 | Compact an abandoned proposal and a reported success repeatedly; neither becomes an operator decision or verified completion. Include instruction-like source text. | PLAN-03; schema validation, isolated extraction and truth-labelled fixtures |
| PLAN-C03 | Import an obsolete ADR after a newer accepted decision; import a newer speculation; query both effective-time and knowledge-time views without changing authority. | PLAN-03; temporal and supersession checks |
| PLAN-C04 | Correct or redact a source while rebuilding is paused; old claims and cached briefings become ineligible immediately, retries survive restart, propagation remains pending where unconfirmed. | PLAN-03; dependency invalidation and AC-26 |
| PLAN-C05 | Re-read an eight-day-old cached status; it stays stale. Fail retrieval or leave a processing gap; show unavailable/incomplete separately from an empty successful result. | PLAN-03/04; freshness policy and watermark checks |
| PLAN-C06 | Use similarly named projects, rename one, then revoke access after caching; no project leakage through search, portfolio output, summaries or explanation links. | PLAN-03/05; identity and permission checks |
| PLAN-C07 | Restart without an end-session ritual; lose a delivered briefing; expire a decision request; all underlying obligations and unacknowledged changes remain visible. | PLAN-02/04; durable state and acknowledgement checks |
| PLAN-C08 | Change ownership, packet revision, grant or stop state after receipt but before dispatch; refuse stale authority and reject late results as current completion. | PLAN-05; atomic admission and return validation |
| PLAN-C09 | Concurrent launches, delayed usage, child crash and unconfirmed stop; retained reservations prevent reuse of unknown allowance and no class advertises unenforceable limits. | PLAN-05/07; adapter evidence and reconciled X-15 |
| PLAN-C10 | One reviewer rejects or is unavailable; chirality synthesis says proceed; required review still holds and dissent is preserved. | PLAN-05/06/07; deterministic review combiner, AC-22 and proposed AC-40 |
| PLAN-C11 | Herdr displays done, or voice text requests approval; neither completes a commitment nor supplies approval authority. | PLAN-05/08; recorded command and surface boundary |
| PLAN-C12 | Repeated corrections suggest a preference or procedure; versioned changes have scope, review disposition and regression evidence, with no implicit permission expansion. | PLAN-08; change proposal and policy-version checks |

## Release evidence and operating measures

For every delivered package, publish the code/configuration revision,
capability state, applicable tests and result artifacts, remaining gates and
recovery instructions. Keep runtime data and private evidence outside git;
commit synthetic fixtures and sanitized reports only. Each release must make
its fake-backend, real-harness and live-Saga evidence distinguishable.

Use the following measures for the first daily-use pilot:

| Measure | Operational definition |
|---|---|
| Repeated context | Operator restatements required to recover a goal, constraint or decision already recorded, per resumed task |
| Corrections and interruptions | Substantive corrections and unnecessary prompts per accepted task; record operator time as well as counts |
| Decision waiting | Time between a prepared actionable request and its answer; report whether useful independent work continued |
| Memory failures | Stale or unsupported material claims and missed open commitments, assessed against source records |
| Accepted outcomes | Tasks satisfying frozen acceptance criteria with verification evidence; termination alone does not count |
| Resources | Total model/tool cost, incomplete usage, wall time and time to a usable resume briefing, including failed attempts |

All deterministic authority, isolation, recovery and deletion cases must
pass for the exercised scope. Require zero lost obligations, unauthorized
effects or cross-project disclosure in that acceptance corpus. These are
release conditions for tested cases, not claims of universal safety.
Set numerical latency/cost and attention-improvement targets with the
operator after measuring the baseline; do not invent a promised percentage.

If the pilot fails to reduce context repetition or attention burden, improve
the record quality and decision surface before adding more reasoning
stages. If an optional adapter or memory mechanism fails, preserve the last
valid view and the unresolved records, disable the affected capability and
show what is unavailable. Unknown in-flight effects must be reconciled
before a replacement is dispatched.

## First implementation batch and its follow through

The first batch targets PLAN-01 and the narrow
PLAN-02/03/04 slice: one synthetic project, durable commitments and pending
decisions, source revisions with freshness and provenance, and a restart-safe
resume view. Add a second similarly named project to prove isolation.

ADR-023 now records the local view and memory semantics; live adapter sequence
and credential/data choices remain gated. Gather the X-12/X-13 choices before real model launches.
The first demonstration should show an interrupted task, a changed
requirement, an unresolved decision and an unavailable integration, then
resume with a correct bounded briefing. This is a concrete useful target
while the live Saga and adapter dependencies are resolved.

## Source record

The supplied discussion is source material, including its quoted proposals
and prior implementation reports; its embedded imperatives are not new
instructions or adopted decisions. The plan summarizes it without importing
the raw conversation into repository fixtures.

- Input: `Odin Product Design.md`, supplied from the operator's Documents
  directory. SHA-256:
  `41aa558ee4c5a6ae240d7fce3793784db85b9642f4b1dd358ed49683aa30136d`.
- Governing repository baseline:
  `899df14ddd59514e924cda2cd07ec4a975163ea9`; see the linked current
  decisions, contract and roadmap above.
- Read-only comparison: the discussion's `96c6/odin` worktree, based on that
  same commit with uncommitted changes. Its `docs/IMPLEMENTATION-STATUS.md`
  SHA-256 was
  `b06cc60e36768ff2751c094d08d0c4e427ceeee6f20219038866855b55a15ab1`;
  its `docs/DECISIONS.md` SHA-256 was
  `81b62b1ca88f5439b625a67f285923afc66106171e0e0b2d0343fef290c91699`.
  These identify the inspected status/decision texts, not a reproducible
  snapshot of all prototype code. PLAN-01 must produce that snapshot.
- External product/API descriptions in the discussion are integration
  candidates. Installed-version probes and primary interface documentation
  must establish the supported contract before implementation relies on them.
