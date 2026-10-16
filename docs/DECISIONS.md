# Odin — decision record

> **Status:** candidate live record for the documentation handoff of
> extraction snapshot `2026-10-14-14fdab3`. The handoff is **not yet
> recorded**; the D14 gate is under independent review. The source
> contract review returned CHANGES_REQUIRED; its corrections are applied
> and resolved against existing decisions, and its re-review is pending
> (§6, [`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md)).
> Until it is
> recorded in both repositories, the joint record frozen at
> [`history/saga-extraction/2026-10-14-14fdab3/docs/DECISIONS.md`](history/saga-extraction/2026-10-14-14fdab3/docs/DECISIONS.md)
> (Saga commit `14fdab3`) and Saga's live record remain authoritative,
> and this file must agree with them (D14.7), except for explicit
> operator decisions recorded in Odin's ADRs. These apply to Odin only;
> they do not amend Saga-owned interfaces or close the handoff.
>
> **Authority within Odin.** This record wins over the
> [I/O contract](design/ODIN-IO-CONTRACT.md), which wins over the
> [implementation blueprint](design/ODIN-IMPLEMENTATION-BLUEPRINT.md),
> which wins over the [roadmap](ROADMAP.md). The
> [acceptance scenarios](design/ODIN-ACCEPTANCE-SCENARIOS.md) must agree
> with the record and the contract; a conflict is an issue to resolve
> before a scenario is claimed to pass. Interfaces owned by a producer
> (Saga, Herdr, heimdall, skald, braid, WCU, dotprivate) are governed by
> that producer's pinned contract ([`contracts/`](contracts/README.md)),
> not by this file. Research and historical snapshots are evidence, not
> policy.
>
> **Identifiers.** Inherited decisions keep their legacy identity:
> `SAGA-2026-10-Dn`, written `Dn` for short in all Odin documents.
> [`provenance/DECISION-MAP.md`](provenance/DECISION-MAP.md) resolves
> every `Dn` and its clauses (`D7.4`, `D24.8a`) to an owner, a location
> and a status. New Odin decisions are `ODIN-ADR-nnn` (§4), with their
> scope and inherited-clause relationship recorded explicitly.
>
> **Status values** (unchanged from the source): **locked** (build
> against it), **default** (locked unless the operator objects),
> **hypothesis** (build the first version against it; it must pass the
> stated evaluation to stay), **open** (the operator must choose).

## How this record carries inherited decisions

Each `Dn` below has one heading. Where Odin owns the decision, its
text is carried **verbatim** from the frozen record (relative links
retargeted to resolve in this repository), followed by
ownership notes for any clause another project owns. Where Saga owns
the decision, this record states only Odin's consumer obligations and
points to the pinned Saga contract; Saga's own wording stays in Saga.
Split decisions show only Odin's clauses, with the remainder listed by
clause number. Cross-references such as "(D17)" inside carried text
resolve through the decision map; "CLAUDE.md auth boundaries" inside
carried text refers to the Saga developer instructions captured in the
snapshot, whose Odin equivalent is [`../AGENTS.md`](../AGENTS.md).

## 1. Product statement

> Odin turns agent sessions into persistent, supervised work across
> projects, using the harness the operator already prefers. (D19.1)

> **Odin** is a personal agent for running long-term technical
> projects. It maintains context across interruptions, coordinates
> specialist workers, and brings back evidence and decisions within
> authority you explicitly delegate. (D0.1)

## 2. Inherited decisions

### SAGA-2026-10-D0 — Product scope and promise (locked; split)

Odin's clauses (D0.1, D0.3, D0.4a, D0.5, D0.6) and the shared rules
(D0.7, D0.8), verbatim:

> **Odin** is a personal agent for running long-term technical
> projects. It maintains context across interruptions, coordinates
> specialist workers, and brings back evidence and decisions within
> authority you explicitly delegate.

The initial audience is one technically capable individual managing
several software, research or infrastructure projects who is willing
to operate a local service. General life administration (email,
purchases, calendars) is out of scope; adding it is a product decision
with its own authority boundaries (D2), not a feature. Desktop control
for technical work is an optional later capability under D21, never
part of the initial product.

What Odin can be trusted to own over time, and how that trust is
established, is the differentiation: operator-controlled
infrastructure, explicit delegation (D17), verifiable outcomes (D5),
inspectable history (D4, D7), and reviewed changes to its own working
methods (D9, D11). Persistence, memory, proactivity, parallel workers,
chat access, learning and a separate reviewer are table stakes and are
not claimed as differentiators.

Deployment is described accurately everywhere: locally operated state
and execution, hosted inference (Anthropic for Odin's turns and the
workers; optionally hosted or local decision models). The billing
promise is subscription-first with bounded, explicitly configured API
spending (D24), never "no API costs".

Ownership notes: Saga's product statement (D0.2) and the enforcement
boundary any new connector needs (D0.4b, via D2) are Saga's.

### SAGA-2026-10-D1 — Products and boundary (locked; split)

Odin's product row (D1.1), verbatim from the source table's "What it
is" and "What it owns" cells:

> A supervisory layer over an agent harness: an **Odin service**
> (commitments, memory, queued events, wake policy, budgets, session
> records, scheduler, outbox, adapters) plus a **harness integration
> package** (the tools, hooks, skills and instructions that make a
> Claude Code session operate as Odin). Hosts Odin, Mimir review
> sessions and one-shot subagents.

> Persistent commitments and project memory; event intake and
> attention; session lifecycle (start, resume, retire, reconstruct);
> delegation coordination and reconciliation of results; selective
> review coordination; outcome verification against evidence; proposing
> changes to its own working methods. Reasoning and tool execution
> *within* a session belong to the harness.

Odin's obligations: Odin reaches Saga only through tools backed by the
independently running Saga service (D1.3). It submits with a stable
request id, resumes from Saga's cursor and never relaunches workers on
its own restart, so that a lost connection does not lose a run,
restarting Odin does not restart workers, and a retried submission does
not launch a duplicate (D1.4b; I/O contract §9; AC-01, AC-03).

Ownership notes: Saga's product row (D1.2) and the run-durability
guarantees themselves (D1.4a) are Saga's.

### SAGA-2026-10-D2 — Enforcement lives in Saga, as two guarantees (locked; Saga)

Owner: Saga. Normative interface: the pinned Saga contract. Odin's
consumer obligations:

- Submit every run with the digests and bindings Saga requires for run
  admission (approved PRD, launch configuration, the Mimir verdict
  bound to the request id where review is required, the operator
  authorization bound to the hash of what was shown); treat Saga's
  refusal as authoritative. `stage_run` is local feedback only (D2.1).
  Concretely (I/O contract §6, review findings B3, B6): the request id
  is a ULID preallocated by `stage_run` before any review or approval
  and reused by the submission and every retry; the submission carries
  it with `prd_digest`, `launch_config_digest`, the verdict id and the
  approval id, and the verdict and approval must cover the request id
  and both digests. A restart mints a new request id and renews those
  bindings. The binding envelope and canonical encoding are open at
  Saga; no binding is weakened while they are.
- Keep the Saga token, the reviewer key and the Telegram token in the
  service, out of every session and tool process; Odin's command and
  file tools run in an isolated planner workspace with redacted results
  and are not offered where that isolation is unavailable (D2.4b, D24.3;
  I/O contract §7; review finding B7). This is a design requirement,
  not an implemented property.
- Never offer an agent a connector that can act outside the container
  before its enforcement boundary exists; admission never implies
  authority (D2.3).
- Hold Mimir's reviewer identity key in the service and never expose it
  to Odin's turns (D2.4b). Sharing a process with Mimir is an
  operational convenience, not a security boundary; a separate process
  with the same contract is available when the operator wants a second
  failure domain (D2.5).
- Implement the Odin-side stop operations, pause the planner and
  disable schedules (timers and evaluators), as direct service
  operations; carry the operator's `/stop <delegation>` and the global
  kill switch to Saga's stop operation and report acknowledged and
  uncertain outcomes (D2.6, D2.7; I/O contract §10; AC-10, AC-27). See
  issue X-2.

### SAGA-2026-10-D3 — Two pluggability contracts (locked; split)

Owner of both contracts: Saga. Odin is the first client of the
orchestrator contract (D3.1, D3.2) and consumes it only through the
pinned copy. Odin's obligation: deliver a worker's structured request
for operator input (request id, assignment, decision needed, options,
what answering authorizes) directly to the operator's queue with those
fields preserved (D3.4b, D20.9; I/O contract §4, §10; AC-07).

### SAGA-2026-10-D4 — Ledgers (locked; Saga)

Owner: Saga (D4.1). Odin's obligations, from the source: "Odin's chat
log is Odin's memory and is never consulted to decide whether a run was
approved or completed. Odin rebuilds its picture after a restart by
replaying the cursor from the last sequence it logged." (D4.2, D4.3;
I/O contract §9.)

### SAGA-2026-10-D5 — Completion semantics (locked; Saga)

Owner: Saga (D5.1–D5.4). Odin's obligations: treat `accepted` and
`started` as claims until evidence agrees (D5.3; I/O contract §5);
map Saga's run states to Odin's lifecycle handler without collapsing
assignment, session and run lifecycles; never treat `idle`, a finished
tool call, a workspace "done" or a worker's own report as `verified`
(D5.5; blueprint §4; AC-13, AC-14); measure false completion reports
under D18 (D5.4).

### SAGA-2026-10-D6 — Side effects (locked; shared rule)

Shared rule, verbatim; each service owns its own implementation. Odin's
is the outbox and recovery protocol in I/O contract §9.

At-least-once with an idempotency key per action; destination
deduplication where possible; an explicit `unknown` outcome recorded
after a crash between action and record; reconciliation on restart.
No component claims exactly-once.

### SAGA-2026-10-D7 — Runtime and memory (runtime: locked; memory implementation: hypothesis)

**Runtime.**

> Odin builds on Claude Code's execution harness through supported
> interfaces. Odin owns persistent memory, commitments, scheduling,
> delegation and review coordination; Claude Code owns execution within
> each session. OptChat is an evaluated memory implementation, adapted
> to that boundary. A custom Messages API runtime is considered only
> when measured requirements cannot be met through the existing
> harness.

Concretely: the Odin service starts, resumes and retires Claude Code
sessions through the Agent SDK (sessions, hooks, MCP, subagents,
plugins, a per-session budget), authenticated per the adapter's launch
configuration (D24): the default for planning sessions is an API key
from the Console organization linked to the Max plan, so planning never
competes with the workers for plan limits and the included credits
cover it; a subscription login lineage is a supported alternative.
Two loops: the service's **outer loop**
(ordinary code) decides when to engage a session, with what briefing,
and which outstanding responsibility to revisit; the harness's **inner
loop** decides how to investigate and complete the current assignment.
Sessions are resumed while their working context remains useful and
replaced by a fresh session with an Odin briefing at boundaries
(delegation change, project switch, a context grown past a threshold,
a restart). The runtime adapter is kept narrow so a second harness can
be added (D19); one implementation is built and validated first.
Interactive-only harness behaviours (channels, plugin monitors,
teammates) are not relied on; the service supplies its own Telegram
adapter and event intake.

**Memory.** The memory interface and these requirements are locked:

- recover earlier decisions and their sources;
- recognize superseded facts (the latest word wins, with provenance);
- retain unresolved commitments until closed;
- keep unrelated projects separated;
- support correction, export, and intentional deletion under an explicit
  retention policy;
- stay within measured operating cost (D18 measures).

**UniiChat's ideas** (append-only log, 512-byte summary tree, bounded
hierarchical view, `zoom` to source; Victor Taelin's design, adopted
with attribution) are the first implementation, **adapted to the
runtime boundary**: the service maintains the log and tree from the
session transcripts and events; at session start it renders a bounded
briefing (the view) into the session; during the session `zoom` and
`recall` are tools; between sessions the service keeps compacting.
What is not promised: a fresh model call per message, OptChat's exact
prompt layout, its cache economics, or a constant total context size,
because the harness owns the working conversation. The implementation
stays only if it beats a simpler baseline (rolling summary plus
structured notes plus `recall`) on the D18 memory measures at
comparable cost. "Nothing is lost" describes retained bytes, not
guaranteed recall; the evaluation tests recall.

**Commitments are not memory.** A summary tree is for recall; an
unresolved obligation must not disappear because it was poorly
summarized. The durable model of the work lives in the Odin service as
commitment records (objective, acceptance criteria, owner and
delegated assignments, dependencies and pending decisions, evidence so
far, next trigger or review date, the delegation it runs under and its
budget), referencing Saga runs and D17 delegations. Saga keeps
authority and execution state; Odin keeps commitments and memory.

**Retention.** The append-only rule has one sanctioned exception:
redaction. A redaction record replaces a message's text with a
tombstone in the log, rebuilds the affected tree nodes and view lines
(a cache miss is accepted), purges derived indexes and the archiver's
copy, and is itself logged with who ordered it and when. Backups follow
the same retention policy.

Ownership notes: the planning-session authentication default is
confirmed or changed under open question §5.12a. UniiChat is Victor
Taelin's design; the gist shows no license (open question §5.5).
ODIN-ADR-001 settles Odin's own license, not third-party reuse rights.
ODIN-ADR-003 supplies the baseline and staged evaluation protocol for D7.10;
production retention defaults remain open.

### SAGA-2026-10-D8 — Mimir: selective, evidence-based, measured (default)

- **When.** Review where mistakes multiply: a decomposition before
  workers start, a change to a shared interface or contract, guidance
  that materially changes a worker's approach, an Eir patch that changes
  system behaviour, a principle change. Routine operations (status
  reads, notifications, bookkeeping, operations already covered by an
  approved plan) use mechanical checks, not model review.
- **Mechanical first.** Byte-identical contract quoting, dependency
  cycles, approval and artifact hashes, declared secrets, git workflow
  presence are code checks whose results are given to Mimir as
  evidence. Mimir investigates what code cannot resolve: semantic
  coupling between "independent" streams, sufficiency of success
  criteria, guidance against the operator's original intent.
- **Evidence, not narrative.** Each request carries the operator's
  requirements, the exact artifacts, the relevant contracts, the
  deterministic check results, and the prior verdicts for the same
  artifact lineage, attached by the harness. Mimir never sees Odin's
  conversational reasoning. Mimir keeps no perpetual working memory;
  its chat log is an archive.
- **Bounded and actionable.** Each finding names its evidence, its
  consequence and the minimal correction. Verdicts: `APPROVE_UNCHANGED`
  (preferred when no concrete improvement exists), `APPROVE`, `FLAG`,
  `REJECT`, `INSUFFICIENT_EVIDENCE`. One review and at most one
  corrective re-review per artifact; then the operator decides.
- **Model per review type.** Sonnet by default; an equally capable
  model for decomposition and architectural judgments if evaluation
  shows the cheaper one misses. "Cheap" is earned, not assumed; Opus
  and Sonnet share a family and their errors are not independent.
- **Budget.** Review spend and interrupt-class turns have hard daily
  caps separate from wake turns.
- **Measured.** Odin alone, Odin with an equivalent extra verification
  budget, and Odin plus Mimir are compared on frozen pre-review
  artifacts with independently assessed outcomes: defects prevented,
  good plans degraded, unnecessary escalations, cost, time to verified
  completion. A high rate of changed plans is not success.

Ownership notes: Saga verifies the reviewer key and records verdicts
(D2.4a). The model per review type is open (§5.2).

### SAGA-2026-10-D9 — Decision models: bounded judgments, never authority (locked)

> System One models provide bounded semantic judgments through an
> optional Odin tool and approved harness evaluators. Application code
> owns their consequences. Persistent evaluators require versioned
> configuration, workload-specific evaluation, reversible activation and
> baseline fallback. Their outputs cannot satisfy Saga approval
> requirements or waive required Mimir review.

- **`decide(state, questions)`**: an advisory turn tool over a provider
  abstraction (Jev's managed API, OpenAI's Decisions beta, a local
  open-weight decider on the VM). Returns judgments, probabilities,
  model identity, evidence references, and an explicit unavailable or
  invalid status. It cannot execute what it chose.
- **Evaluators**: harness-owned, versioned decisions such as
  `journal_attention_v1`, with fixed questions, input projection,
  thresholds, fallback and permitted effects, invoked at a small
  registry of supported hook locations: journal attention, compaction
  fidelity, recall reranking, Mimir topic suggestion. Not supported:
  anything in Saga's enforcement path, planning, decomposition, patch
  approval, or operator messages (they are parsed in code and never pass
  through an evaluator; an earlier "operator-intent" hook, also named in
  the blueprint, is withdrawn).
- **`propose_decider(config)`**: Odin may propose an evaluator; approval
  (Mimir review, hash-bound operator approval) binds the complete
  configuration; activation requires replay against logged decisions
  and a shadow period; any change revalidates; rollback is one command.
- **Safety rules.** Deterministic mandatory-event checks run before any
  semantic filter. Operator messages, corrections, revocations, stops
  and critical lifecycle events bypass learned routing. Explicitly
  typed messages (a worker's structured request for operator input, an
  approval response, a stop) are routed by their type and never
  classified; no classifier can conclude that an approval requirement
  is satisfied or can be skipped. Decision models interpret messages
  whose significance is otherwise unclear, nothing else. Routine entries
  deferred by an evaluator have a maximum deferral time and are
  digested, never dropped. Confidence values are not measured
  correctness; thresholds are tuned per workload and pinned to a model
  version. Sensitivity follows content through transformations:
  anything derived from operator messages or specification content
  goes only to the local provider, in questions and candidate
  descriptions as well as state.
- **First experiment.** A journal-attention evaluator in shadow mode
  against the existing Haiku triage path, measuring missed actionable
  events, unnecessary escalations, intervention delay, total model cost
  and maintenance effort. The inference cost is negligible; the real
  costs are extra Odin continuations and missed events.

Ownership notes: Saga enforces approval requirements independently of
anything an evaluator returns (D2.1).

### SAGA-2026-10-D10 — The standalone tools stay separate (locked)

| Tool | Role in the Odin plan | When |
|---|---|---|
| braid | Backend for the optional `recall` tool over lessons, wikis, contracts, imported history, worker journals across projects; child process over its stdio protocol; never indexes the chat log | after Odin v1 |
| skald | Optional archiver of Odin's and Mimir's chat logs via a provider adapter and the per-line `chat` id; must honour redaction (D7) | after the log format stabilizes |
| muninn | Optional `recall` scope over curated knowledge; its ADR-007 claim on typed journals is superseded (the chat log is canonical) | when the operator reactivates it |
| wayland-computer-use | A harness-independent desktop capability (two MCP servers, shared skills; observation and guarded input, no model decisions), usable only by a dedicated computer-use worker under a delegation that names desktop authority, through the seat lease and app-scoped boundary in D21; never reachable from planning sessions or container workers | after Phase F, by operator decision |
| standalone heimdall | Not an authority for approvals or task state. Optionally connected later as a human-facing continuity surface (overview, checkpoints, desktop bindings, review interface) that references Odin's commitment record as the one authoritative record (D20) | after D20's first configuration works; needs a release and green CI |

Nothing rolls into Odin. The harness core stays generic; Saga-specific
tools come from the Saga client library; everything else is an adapter.

Ownership notes: each tool's capabilities, releases and contracts are
owned by its project; Odin records what it requests and consumes in
the [ecosystem integration plan](design/ODIN-ECOSYSTEM-INTEGRATION.md)
and pins nothing until the peer publishes a contract
([`contracts/`](contracts/README.md)). The wayland-computer-use row is
as revised by D21. The Saga client library is a Saga deliverable.
muninn's future is open (§5.4). "Never indexes the chat log" in the
braid row is read as the source record's own §2 wording, "braid still
never indexes Odin's active chat"; the `archive` scope is read-only
retrieval through skald over archived, explicitly published
conversations (issue X-4, review finding N7). The reading approves no
peer capability: skald retrieval is open (§5.11) and the braid and
skald work is proposed (EC-06, EC-07).

### SAGA-2026-10-D11 — Eir: controlled improvement, loop closed (locked; Saga)

Owner: Saga (D11.1a, D11.2, D11.3). Odin's parts: Odin owns the loop
that decides that work needs different guidance (D11.1b); Eir's
failures reach Odin as `host` events and Odin files maintenance
requests only through Saga's task request, as D3 lists it in the Saga
API (D11.4; I/O contract §4, §10, Appendix B B-16; review finding N9); Mimir reviews Eir patches that change
system behaviour (D8). Saga's out-of-band recovery path must not depend
on Odin's availability (blueprint §3).

### SAGA-2026-10-D12 — Bragi (locked; Saga)

Owner: Saga (D12.1). Odin owns the import endpoint through which Bragi
publishes lessons (`append_note`, D12.2) and the history projections
Bragi reads (D12.3; I/O contract §9, §10).

### SAGA-2026-10-D13 — Naming (locked; split)

The rule is shared (D13.1), verbatim:

> Norse names only for agents that carry a persona and make
> judgments. Every deterministic component, directory, image, topic and
> tool gets a plain functional name, prefixed `saga-` when it is a
> deliverable. Never reuse a name used by one of the operator's standalone
> repos. Mythological places and metaphors appear only in Odin's identity
> paragraph.

Odin's entries: Odin and Mimir keep their names (D13.2a); "evaluator"
is a versioned, harness-owned decision (D13.8); "the Saga adapter in
Odin" is Odin's half of the former Ratatoskr (D13.4b); `containers/odin/`
and the `saga-odin` image move to the `odin` repository at code
extraction (D13.6, issue X-5). Odin uses Saga's terms worker, run,
stream, delegation, Saga launcher and Saga events (D13.3, D13.4a).
The removed metaphors (D13.7), the reduced banned-synonym list (D13.9)
and the rule that legacy names remain in history and code until each
rename lands (D13.10) apply to Odin. Saga's renames (D13.2b, D13.5) are
Saga's.

### SAGA-2026-10-D14 — Repositories (locked; split)

Shared, verbatim:

`saga` and `odin`; the standalone repos stay where they are. Three
changes with different completion criteria, per
[`design/ODIN-REPOSITORY-EXTRACTION.md`](history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-REPOSITORY-EXTRACTION.md):
a **documentation handoff** may create the `odin` repository earlier
than Phase C as a documentation-first scaffold (the Odin design
documents, a frozen snapshot of this record with a provenance map that
preserves D-numbers, and a pinned copy of Saga's contract once
`saga/docs/contracts/SAGA-SERVICE.md` exists); **code extraction**
enters that repository in the blueprint's increments; **deployment
cutover** still depends on Saga Phase B. The handoff gate: the contract
has held for one review cycle, Saga's producer contract is extracted at
Saga, and the decision map is written. Until the handoff is recorded,
this repository remains the document owner.

State in this checkout: this is the documentation-first scaffold D14.3
permits; no further amendment is needed for it. The handoff gate
(D14.6) is not yet satisfied: the review cycle is in progress, Saga's
producer contract is pinned as `0.1.1-draft` at producer commit
`a84f9ac28a6b4de651fccc057d33a335472f9773`, and the decision map is a
candidate. The pinned bytes match the canonical draft; its target API
is unimplemented. Pin bookkeeping is complete, but no final independent
review or formal handoff is claimed. "This repository" in the carried
text means Saga (D14.7).

### SAGA-2026-10-D15 — Development direction and sequencing (locked; split)

Odin's phases and gates; the full table is in the frozen record and
the mapping to Odin increments is in the [roadmap](ROADMAP.md).

- **C (Odin):** "Odin v1 in the `odin` repo: the Odin service
  (commitments, memory with the D7 first implementation, event queue,
  wake policy, budgets, session records, scheduler, outbox) and the
  Claude Code integration package (tools, hooks, skills) over the Agent
  SDK with a narrow runtime adapter; Telegram adapter with hash-bound
  approvals; Saga client tools; Mimir review sessions under D8;
  migration import; shadow mode; cutover." Exit: "Odin runs one project
  end to end without tmux, meeting Saga's boundary on its first live
  submission; an interrupted session is replaced without losing the
  outstanding assignment." (D15.C)
- **D (Odin part):** second project, adopt-into-supervision and
  take-control, ownership rules exercised (D15.Db).
- **E (Odin part):** a second Odin harness adapter (Codex app-server or
  Pi RPC) with its capability matrix; Odin runs one assignment through
  it (D15.Eb).
- **F (Odin part):** `recall` on braid; `decide`; the first evaluator in
  shadow mode; skald archiver; observability (D15.Fa).
- **G:** the D18 evaluation and demonstration; measured results
  published in the repo (D15.G).
- **Ordering (shared):** "Phase B precedes C because Odin v1 is built
  against the API, and because the first live project must meet the
  boundary D0 promises." (D15.8)

**Odin-side sequencing interpretation; producer reconciliation pending**
(source review B2, issue X-1). Saga's live D15 does not contain this
clarification, and its developer instructions still prohibit starting
Phase C before Phase B's API and minimum enforcement. This is a proposed
reconciliation of that wording with the source blueprint, not an amendment
approved in Saga. D14.4 has code
extraction enter in the blueprint's increments; the source blueprint
(§7) lets I0 to I2 use a fake Saga backend; the source extraction plan
(§1) says a fake backend establishes no production readiness. Read with
D15.8: I0 to I2 are non-production development against fixtures and a
fake backend and may proceed while Phase B is in progress. I3, every
live delegated run, every live Saga submission, deployment cutover
(D14.5) and the Phase C exit require Phase B's exit criterion and
minimum enforcement. Peer integrations follow D15's phases: read-only
Herdr inspection in I3 (D20's first configuration), the full Herdr
adapter with adopt and take-control in I4 (D15.Db), the second harness
adapter in I5 (D15.Eb), braid `recall` and skald enrollment and archive
in I6 (D15.Fa, D10). Earlier work on any of them is fixture work only.
The mapping is in I/O contract §13 and the [roadmap](ROADMAP.md). The
interpretation remains open at X-1 until reconciled in the two repositories.

Saga's phases A, B and its parts of D, E and F (D15.A, D15.B, D15.Da,
D15.Ea, D15.Fb) are Saga's and appear in Odin's roadmap as dependencies.

### SAGA-2026-10-D16 — Documentation (locked; mostly historical)

Saga's documentation actions (D16.1) are Saga's and complete. Odin's
part: the Odin design documents and the harness research move to this
repository's `docs/design/` and `docs/research/` (D16.2). The source row
names "Odin I/O contract (v4)"; the captured contract is v7. The
existing runtime personas stay in Saga until cutover (D16.3); Odin's
personas are derived at code extraction
([`provenance/LEGACY-REQUIREMENTS.md`](provenance/LEGACY-REQUIREMENTS.md)).

### SAGA-2026-10-D17 — Delegation records (locked; Saga)

Owner: Saga (D17.1, D17.3, D17.4b, D17.5). Odin's obligations: maintain
priorities inside a delegation and propose changes to it through
`ask_operator`, never by writing it (D17.2); reference the delegation
from every commitment, which Odin remembers as an unresolved commitment
(D17.4a; I/O contract §2, §6).

### SAGA-2026-10-D18 — Evaluation and the first demonstration (locked; split)

**Comparative experiment.** Odin plus Saga against an existing personal
agent plus Saga (Hermes, on an API key, sandboxed) on a small set of
representative delegations, measuring:

| Measure | Establishes |
|---|---|
| Verified outcomes per operator hour | Whether delegation saves attention |
| False completion reports | Whether evidence handling is credible |
| Recovery after restart or worker failure | Whether persistence is operational |
| Missed commitments and stale decisions | Whether memory supports ongoing responsibility |
| Unauthorized or duplicate effects | Whether the authority boundary holds |
| Total cost, including review, compaction and evaluators | Whether the custom design is economical |

The memory hypothesis (D7) and the Mimir policy (D8) are judged on the
same runs. Saga remains valuable if another agent wins the comparison.

Every Odin feature (memory implementation, Mimir, evaluators, `recall`)
is switchable, and the baselines include the native harness alone and
the native harness given an equivalent additional budget, so the
measured claim is specifically that Odin's supervision improves
continuity and outcomes.

**First demonstration.** A sustained responsibility, in this shape:

1. The operator gives Odin three specification documents. Odin records
   their versions, identifies the intended outcomes, and determines
   whether they are three independent projects or coupled parts of one
   (shared dependencies and interfaces).
2. Odin proposes assignments and acceptance criteria; Mimir reviews
   boundaries, dependencies, missing requirements and verification;
   worker count follows the decomposition and the delegation's budget;
   after operator approval the approved artifacts are the basis for
   execution.
3. Odin requests execution through the selected backend (D23): Saga for
   isolated workers, enforced limits, durable run records and recovery.
4. The workspace opens through structured interfaces: Odin's workspace
   adapter creates groups and panes through Herdr's API and launches or
   exposes the supported sessions, with the task-continuity and archive
   surfaces alongside. Computer use is reserved for application
   interactions without a suitable API (D21).
5. Three visibility surfaces show different truths: the workspace shows
   which sessions run, block or await interaction; the task-continuity
   surface shows accepted objectives, checkpoints, dependencies,
   decisions and outstanding work; the archive shows what the agents
   and operator actually said, with provenance.
6. Workers report through Odin's service; most delivery is code (D20).
   Routine progress advances recorded observations without waking the
   planning model; a structured request for operator input goes to the
   operator's queue; ambiguous free text may be classified.
7. Decisions and verified results update the work records; the archive
   preserves the conversations; Odin retains the context for future
   supervision; a selected project package is preserved (D22).

Scenarios the demonstration must include, because they show the
contribution that individually capable sessions cannot make:

- A requirement changes mid-flight: the operator revises document two;
  Odin identifies the affected assignments, pauses incompatible work,
  requests targeted review, and updates the plan without restarting
  unrelated streams.
- A worker disappears after producing an artifact: Odin reconciles the
  existing output and evidence before replacing the session, avoiding
  duplicate implementation or publication.
- The operator takes over a blocked session: the workspace exposes it,
  automated prompting pauses, the correction is recorded, supervision
  resumes with an explicit handoff.
- All workers finish but integration fails: Odin keeps the overall
  commitment open, creates the missing integration assignment, and
  shows why individual completion did not satisfy the project.
- Preservation or retrieval is unavailable: local work continues with
  visible coverage limits; pending exports retry later without claiming
  remote durability.

Ownership notes: "Saga remains valuable if another agent wins the
comparison" is Saga's (D18.3). Saga supplies the runs and ledger
evidence the comparison measures. The first delegation is open (§5.7).

### SAGA-2026-10-D19 — Odin as a supervisory layer over a chosen harness (locked)

> Odin turns agent sessions into persistent, supervised work across
> projects, using the harness the operator already prefers.

What Odin contributes, in order of importance:

| Capability | Contribution |
|---|---|
| Persistent commitments | Objectives, unresolved decisions, dependencies and follow-ups tracked independently of sessions (D7) |
| Long-term memory | Decisions with sources, corrections and superseded facts, relevant context prepared for a session (D7) |
| Attention management | Events routed, routine updates batched, follow-ups scheduled, exceptions escalated (contract §3, D9) |
| Session continuity | Sessions started, resumed, retired and reconstructed from durable state (D7) |
| Delegation coordination | Bounded assignments, dependency tracking, reconciliation of results against the larger objective (D17) |
| Selective review | Mimir at decision points where errors propagate, with evidence and bounded rounds (D8) |
| Outcome verification | Completion claims connected to acceptance criteria and evidence (D5) |
| Controlled improvement | Evaluated, reversible changes to guidance, memory practice and routing (D9, D11) |
| Comparative evaluation | Whether the supervision improves results, per harness and per feature (D18) |

Mimir and the decision models are optional improvements to this
lifecycle; Odin must remain useful with both disabled.

**Adapters.** Harnesses differ in their controls over sessions,
context, tools and interruption. Odin publishes a capability matrix per
adapter (start, resume, inject mid-turn, interrupt, hooks, budget,
subagents, transcript access) rather than implying identical behaviour.
The adapter translates assignments, events and results; it does not
reimplement the harness's planning, compaction, subagents or tool
selection. Claude Code (Agent SDK) is the first adapter; a second
(Codex app-server or Pi RPC) is added early enough to test whether the
boundary is real, and no universal adapter framework is built before
two implementations show what differs.

**Restrained initial product:** the commitment and project-state
service; the Claude Code adapter with explicit session and event
handling; memory retrieval and session briefings; scheduling,
attention routing and operator escalation; evidence-based completion
tracking; then Mimir and evaluators as switchable features. Two
different statements, both true: as a *product*, Odin is modular and
can supervise work without Saga (the local backend, D23, for work
without external effects); as the *first supported deployment*, Saga
with its Phase B minimum enforcement is required before Odin's first
live project (D15), because that is where the D0 promise is kept.

Note: "contract §3" in the carried table refers to an earlier contract
numbering; routing is now I/O contract §4 (review finding N4, §6).

### SAGA-2026-10-D20 — Topology and operator interfaces (locked)

Three layers, kept distinct: the **interface** the operator uses, the
**service** that maintains continuity, and the **agent sessions** that
reason.

**One Odin service** owns the queues, adapters, memory access, budgets,
session records and scheduling. **Several planning sessions**, one
active owner per project or bounded responsibility, each with its own
briefing and context. **Many worker sessions** (implementation,
research, testing, integration) executing bounded assignments in
parallel. Mimir review sessions are created when required. Routine
status events are handled by code and evaluators; they do not all
trigger a planning turn. Another planning owner is added only for a
genuinely separable responsibility (independent subsystems with
established interfaces) or when measured decision latency shows the
current owner is a bottleneck, never because the worker count grew.
Separate service instances are for different operators or isolated
environments, a later scaling step.

**Ownership rules when more than one planner exists:** each assignment
has one owner; every shared interface has a designated decision owner;
a project-state change carries the revision it was based on and is
rejected if stale; budget and concurrency limits apply across all
sessions; ownership transfer is recorded so a resumed old session
cannot issue stale guidance.

**Two operator interfaces, one command path.** At the desk, the
terminal workspace (Herdr) shows an overview (needs attention, open
commitments, approvals, budgets, evidence) and, per project, the Odin
conversation and each worker's terminal, so the operator talks to Odin
about goals and opens a worker to inspect or intervene. Away, Telegram
reaches the same service and the same records: summaries, corrections,
approvals of specific proposals, pausing a delegation. Both enter the
same recorded command path; an approval is bound to its exact proposal
whichever channel gave it; a Telegram conversation never creates a
second Odin with divergent memory; stop is a direct service operation
that works when the model is unresponsive.

**Adapter modes and inspection.** Native integration (Odin drives a
harness through its SDK or structured protocol; the workspace shows the
client, event stream and logs, and an interactive view only where the
harness supports it) is distinct from interactive terminal integration
(Odin launches or adopts an agent through a workspace adapter and the
operator sees the actual terminal). An SDK-driven Claude Code session
is not automatically an attachable pane; what inspection and takeover
each adapter supports is tested and published in its capability matrix
(D19). The workspace's "done" (ready for input) and "wait" do not
establish completion; Odin correlates results by assignment id and
evidence.

**Two explicit operations.** *Adopt into supervision*: select an
existing session, associate a project and assignment, grant the
permitted control; opening a terminal in a repository never silently
gives Odin ownership. *Take control*: Odin pauses automated prompting
for that session while the operator works and records a handoff when
control returns, so terminal input, Telegram instructions and Odin
guidance cannot race.

**Service path versus model path.** Passing through Odin's service is
the fast, durable coordination path; passing through Odin's model is
the expensive one. Most events need no inference:

| Incoming event | Handling |
|---|---|
| Worker heartbeat or progress event | Record; update the display and the ledger |
| Structured request for operator input | Deliver directly to the operator's queue, preserving request id, assignment, decision, options and what answering authorizes; the answer returns to that exact request; the planner joins only when the answer changes the wider plan |
| Approval response | Validate identity, proposal binding, expiry and current state in code |
| Stop or revocation | Apply directly through the control interface |
| Ambiguous free-text update | Optional decision-model classification (D9) |
| Conflicting requirements, changed scope, failed strategy, verdicts, exceptions | Wake the project's planning session |

**Ownership bridge with standalone heimdall.** The skald–heimdall
amendment assigns accepted task state to heimdall; this record makes
Odin authoritative for its commitments. Resolution, per workstream:
Odin-managed work appears in heimdall as an externally owned
projection; heimdall-managed work keeps its current owner; edits route
to the owner; no second editable copy of the same task exists. That
bridge is new work and is scheduled with the D20 workspace integration.

**First configuration:** one Odin service, one project-scoped planning
session, a small worker pool, the terminal workspace for inspection,
Telegram for remote interaction; then a second project to test context
separation and scheduling before any further supervisory layer.
Herdr's own automation API was not reviewed in this record; its
capabilities are confirmed when the adapter is built.

Ownership notes: heimdall owns its side of the ownership bridge
(ecosystem plan §5, EC-05); Herdr's automation API is unreviewed
(§5.8).

### SAGA-2026-10-D21 — Desktop capability and computer-use work (default)

> wayland-computer-use remains a harness-independent desktop capability.
> Odin coordinates desktop assignments and continuity. Optional decision
> models interpret bounded textual evidence, while the capability's
> deterministic guards and outcome checks retain their existing roles.

| Component | Responsibility |
|---|---|
| wayland-computer-use | Observe the desktop, execute guarded input, return readback and execution evidence; no model decisions |
| the agent harness of a computer-use worker | Interpret screenshots, plan interactions, call the tools; a Claude Code session today, another compatible harness later |
| Odin | Maintain the assignment, schedule desktop access, preserve progress, handle interruptions and escalation; never reasons about individual clicks |
| decision models, optionally | Classify textual observations (dialog state: progress, completion, recoverable error, unexpected interruption), rank applicable procedures, judge relevance of changed accessibility text, compare an application message with a narrowly defined expected outcome |
| Mimir, selectively | Review consequential plans or changes to reusable procedures |

**Authority and safety.** A desktop assignment exists only under a
delegation that names desktop authority (D17) and is scoped to named
applications and windows; terminal emulators and anything that reaches
the VM are excluded by default, because a desktop session can otherwise
route around Saga's launcher. An **exclusive desktop-control lease**,
enforced at a shared broker or tool boundary across cooperating clients
(a prompt note is insufficient), gives one agent input on a desktop seat
at a time, queues other desktop assignments, suspends automated input on
human takeover, requires fresh observations when an assignment resumes,
and reconciles any uncertain action before a retry. The capability's own
guards (screenshot freshness, window re-check, pixel check, no automatic
retries, time budgets) remain in force because the human and other
processes can still change the desktop.

**Decision models in this workflow.** Exact text matches, focus checks,
frame freshness, target identity and saved-content verification stay in
code. A classifier never turns an unknown state into permission to
proceed, and a suggested control is not a valid way to activate it
(coordinates, focus and permission are the capability's checks). The
integration lives in a reusable computer-use workflow component callable
by workers, not inside the capability's input primitives, so the MCP
servers stay usable without hosted inference. The data policy follows
the content: desktop text can carry operator messages or specification
content, which go only to the local provider (D9). First experiment:
one application workflow with useful accessibility text and variable
status messages (an export), with and without classification, measuring
verified completion, incorrect continuation, recovery effort, model
turns, latency and total cost; the existing local benchmarks exclude
model and approval time and cannot establish the benefit.

Not in the initial product (D0); scheduled after Phase F by operator
decision.

Ownership notes: wayland-computer-use owns its observation, input and
guards (D21.2a, D21.5); the seat-lease boundary is shared work (EC-10);
the delegation field naming desktop authority is in Saga's delegation
record. Desktop authority is open (§5.9).

### SAGA-2026-10-D22 — Preservation (locked in shape; integration scheduled)

The unit of preservation is a **selected project package**, not a
blanket sync: the source specifications and their versions, the
approved plans and acceptance criteria, the relevant `AGENTS.md` and
`CLAUDE.md` versions, selected evidence, and portable transcript
exports with original record identities. Project source code keeps its
normal repository history. The archive (skald) owns full-archive
backups; live databases and disposable retrieval indexes stay outside
git synchronization. Dotprivate carries the package, and the
integration distinguishes "copied locally", "committed" and "confirmed
on the remote"; it never reports remote durability it has not
confirmed. Copies imported from the package are never presented as
independent corroborating evidence of what they copy. Dotprivate's
selected-files contract is still a proposal in its repo and its current
broad sync is not that implementation, so this integration is scheduled
(Phase F), not assumed.

Ownership notes: skald owns full-archive backups; dotprivate owns its
selected-files contract and publication (EC-08); Odin owns the package
selection and the honest reporting of its state. Open (§5.10).

### SAGA-2026-10-D23 — Execution backends (locked)

Odin requests execution through an explicit backend with a published
capability matrix. **Saga** is the default and the only backend for
work with external effects (pushes to shared branches, publication,
deployments) or needing isolation, enforced limits, durable run records
and recovery. A **local session backend** (a harness session on the
operator's machine exposed through the workspace) may run lightweight
work without external effects (research, drafting, review of
artifacts) under a delegation that permits it, with its missing
guarantees stated: no isolation, no limits beyond the session budget,
and run records kept only by Odin's service. The workspace hosts and
exposes sessions; it never substitutes for Saga's guarantees. Desktop
input is a third backend under D21.

Ownership notes: Saga's guarantees are provided and defined by Saga;
Odin owns the backend choice and must not advertise Saga guarantees for
another backend.

### SAGA-2026-10-D24 — Authentication and billing as adapter configuration (locked; split)

The statement is shared (D24.1), verbatim:

> Odin supports the operator's existing authenticated agent runtimes.
> Runtime choice, authentication method and billing policy are explicit
> configuration, independent of Odin's supervisory features.

Odin's clauses, for its own session classes (planner, reviewer,
subagents, compactor, triage, decision models):

- Each runtime adapter's launch configuration states, per session
  class, the account and billing mode (`subscription`, `api` or
  `local`), a credential reference, refresh ownership, quota behaviour
  and account separation (D24.2a).
- The credential reference points to a protected credential source held
  by the service; secrets never appear in prompts, the history, the
  briefing or exports (D24.3).
- Refresh ownership for Odin's credentials follows the harness's
  supported mechanism, with one refresher per lineage (D24.4a); Codex
  app-server's externally managed token mode stays experimental, not
  foundational, for any Codex adapter (D24.4c).
- Quota behaviour: queue or pause when the selected account reaches its
  limit; switching to paid API usage only through an explicitly
  configured fallback; the `now` block and the overview show the state
  (D24.5).
- The operator's development login and the managed agents' login stay
  separate; Odin's planning sessions and the workers may use different
  modes (D24.6).
- Defaults: planning sessions on `api` (included credits; keeps planning
  off the workers' plan limits) (D24.8a). The source heads D24 locked,
  but its §5 question 12 asks the operator to confirm this default, so
  it is recorded as **default, pending operator confirmation** (§5.12a,
  review finding N8); the billing re-test that bears on it has not run,
  and nothing here claims its outcome. The compactor,
  triage subagents and decision models on their own configured path
  (D24.8c).
- Promise: "subscription-first with bounded, configured API spending.
  Multiple sessions still draw down the account's allowance; nothing
  here claims 'no API costs'." (D24.10)

Saga's clauses: per-worker-image configuration (D24.2b), worker
credential lineages and their refresh (D24.4b, D24.7), the worker
subscription default (D24.8b), and the shadow-period shared volume
(D24.9). Odin depends on them only through the pinned Saga contract.

## 3. Inherited open decisions (source §5)

The original question numbers are preserved. Items 3 and 5 are partly
settled by the operator-directed corrections below; the remaining questions
stay open. The decision map assigns each an owner.

1. **Is Saga active again?** Braid's roadmap recorded "Saga is deferred
   by user direction" in September; Phase B assumes it is not. Blocks
   Phase B and therefore I3.
2. **Opus 5.5 or Sonnet 5.5** as Odin's default turn model, and the
   model for decomposition reviews (D8).
3. **Memory evaluation and retention:** ODIN-ADR-003 sets the comparison
   baseline and an I5 fixture-retrieval protocol; freeze run parameters
   before measurement. Retention defaults remain open.
4. **Muninn's future**: a `recall` scope, Bragi's second destination
   later, or retirement.
5. **Licenses:** the operator selected Apache-2.0 as the project default,
   with MIT for dotprivate (ODIN-ADR-001). Odin now carries its license.
   Third-party UniiChat reuse terms and attribution remain unresolved;
   the original blanket claim that the standalone repositories have no
   licenses is stale. Peer repositories govern their own published terms.
6. **Credits and seats**: claim the Max API credits; decide on a second
   seat once the fleet runs again.
7. **The first delegation** for the D18 demonstration.
8. **Herdr's automation API**: confirm its session, prompt, read, wait,
   attach and takeover capabilities per adapter when the D20 workspace
   integration is built; it was not reviewed in the source record.
9. **Desktop authority**: whether any delegation should name it in the
   first year (D21), and which applications would be in scope.
10. **Dotprivate's selected-files contract** (D22): confirm it is the
    intended mechanism and when its implementation lands.
11. **Skald retrieval** (I/O contract §6, the `archive` scope of
    `recall`; the source cites an older "contract §5"): the archived-conversation scope
    depends on skald's retrieval or MCP work, which its status file
    lists as unfinished.
12. **Billing modes** (D24): confirm `api` as the default for planning
    sessions (Odin), and per-worker token provisioning once the re-test
    confirms `setup-token` (Saga).

Source §4 (the landscape read as three questions) is carried in the
decision map (§4.a–§4.c); its Odin rows are: build on Claude Code
through the Agent SDK, with Codex CLI as the candidate second adapter,
braid for retrieval, a System One provider for judgments, Pi as a
design reference and possible adapter, and the Messages API only if
measured requirements force a custom runtime; compete on delegated
authority, verifiable outcomes, inspectable history and reviewed
self-change.

## 4. Odin decisions (ODIN-ADR)

These records implement the operator's requested corrections on 2026-10-14.
They govern Odin's work; they neither close D14's handoff nor change a
producer's interface. Inherited text and identities remain intact.

### ODIN-ADR-001 — Project license

- **Status:** locked; records the operator's earlier instruction to default
  to Apache-2.0, with MIT for dotprivate.
- **Context:** the extracted license question incorrectly treated the
  operator's choice and third-party reuse permission as one open question.
- **Decision:** license Odin's original contributions under Apache-2.0 and
  include the canonical license text. Preserve third-party notices and terms;
  neither the root license nor this ADR relicenses retained source material.
- **Consequences:** the own-project choice is settled. Resolve permission
  and attribution for UniiChat material before incorporating or publishing
  that material. No license change is made in a peer repository here.
- **Inherited relationship:** resolves Odin's portion of source §5.5;
  leaves D7.9's attribution/reuse obligation and third-party question open.

### ODIN-ADR-002 — Journal attention without an unconditional planner wake

- **Status:** locked design correction; not implemented.
- **Context:** the journal triage path woke the planner for every report,
  eliminating its intended attention-cost benefit.
- **Decision:** coalesce eligible journal entries by project within a bounded
  window and record a typed result with covered source ids: `no_attention`,
  `attention_required`, `uncertain`, `unavailable`, or `invalid`.
  `no_attention` is logged without an immediate planner wake;
  `attention_required` queues a bounded report and coalesced wake. An uncertain,
  unavailable or invalid triage result queues the original evidence for a
  coalesced planner wake. No successful report is required to release that
  fallback. Optional evaluator failures use the ordinary triage baseline;
  if that also fails, the planner fallback applies.
- **Consequences:** a no-attention result defers attention, never deletes an
  event or resolves a commitment. Deferred evidence enters a bounded digest
  by the maximum age (default six hours from original intake, not reset by
  reclassification). If no planning turn consumes it sooner, schedule one
  batched wake at the deadline. Budget pauses retain and visibly mark overdue
  work; do not bypass hard caps or pretend delivery occurred. Mandatory
  events bypass triage and evaluators. Direct operator requests never wait
  for a model. High-risk projects can use direct planner evaluation.
- **Inherited relationship:** operationalizes D9's optional routing and D20's
  deterministic outer loop; supersedes the extracted I/O contract §4/§5
  rule that every journal triage report wakes the planner. D9's bounded
  deferral, mandatory-event bypass and shadow-before-activation rules stand.

### ODIN-ADR-003 — Memory comparison before retrieval integration

- **Status:** default evaluation configuration; not a measured result.
- **Context:** I5 evaluates memory before I6 implements Braid `recall` and
  Skald integration; comparing unequal retrieval access would confound it.
- **Decision:** compare rolling summary plus structured notes against
  OptChat/UniiChat memory at I5 with the same frozen fixture retriever in
  both arms. Pin corpus and source revisions, scope filters, query-to-result
  mapping, byte limits, harness/model, task set, retention setting and total
  budget before running. Both arms receive the same retrieval access; for a
  given query they receive identical ordered results. Record actual queries,
  consumed bytes and all memory/retrieval costs. Authoritative commitments
  are identical in both arms and are not replaced by summaries.
- **Consequences:** I5 evidence is a controlled memory comparison, not proof
  of live `recall`, Braid or Skald integration. Repeat the comparison with
  both arms using the same real adapters after I6; disclose corpus or
  configuration changes. The final D18 evaluation remains in Phase G.
  Production retention defaults remain open; run-specific settings must be
  frozen before evaluation.
- **Inherited relationship:** sets the baseline requested by source §5.3
  and supplies the protocol for D7.10 and D18. It does not move D10/D15's
  retrieval integrations out of I6 or claim the memory hypothesis is proven.

### ODIN-ADR-004 — Narrow attention classification and session-class routing

- **Status:** default design, following the operator's routing review;
  evaluator activation still requires D9's evidence and approval.
- **Context:** worker prose, operator routing and model selection have
  different failure costs. The existing journal-attention hook already
  covers the first experiment; no fifth hook is added.
- **Decision:** retain D9's four hook locations and operator exclusion.
  Bind operator input to an explicit project/session or ask for a target;
  no classifier silently selects one. For eligible worker prose, defer
  only when `P(routine)` meets a workload-validated threshold and code
  finds no mandatory event, missing coverage or conflicting typed state.
  Otherwise use ADR-002's baseline fallback. Choose the threshold for
  missed-action and delay limits, not aggregate accuracy or a vendor's
  confidence number. Shadow results compare with Haiku and independently
  assessed outcomes; agreement with Haiku is not ground truth.
- **Consequences:** send a bounded extract plus run, iteration and status
  metadata; retain source references and mark omissions. D9's local-only
  rule follows sensitive content into extracts and questions. Code chooses
  model/effort from session class, event kind and assignment requirements,
  keeping them stable during a session. Ambiguous class selection uses the
  configured more capable class within budget or queues/escalates; it does
  not silently downshift. A future advisory complexity Score needs a new
  proposal supported by measured routing ambiguity. Jev cannot compact,
  draft guidance or decompose work; worker-model selection stays with
  Odin's planning and launch policy, with Mimir where D8 requires it.
- **Inherited relationship:** operationalizes D9.3–D9.6, D20.8–D20.9 and
  ADR-002; preserves D7's harness boundary and D24's launch configuration.
  No enforcement or approval requirement is delegated to a classifier.
  Checks: AC-33 and AC-36; I/O contract §5–§6.

### ODIN-ADR-005 — Compactor effort and request-size discipline

- **Status:** default experiment configuration, not a measured optimum.
- **Context:** the supplied gist review reports `xhigh` in the original
  setup, but Odin's
  separate compactor has different prompts and cache behavior. Anthropic's
  default for Haiku 5.5 is `medium`; its guidance supports testing `high`
  for fidelity-sensitive instructions, not mandating it for compaction.
- **Decision:** start the compactor experiment at `high` and compare
  `medium`, `high` and `xhigh` on the same scoped corpus. Select the least
  costly configuration meeting predeclared fidelity/latency requirements;
  evaluate triage separately. Pin model, effort, thinking mode, output
  allowance and prompt revision. Validate nonempty visible text and byte
  length; bounded failure recovery retains the source and last valid view.
  Jev may assess a candidate's fidelity, never write its replacement.
- **Consequences:** target Haiku requests below 100,000 input tokens with
  configured headroom, using model-specific counts of the whole request.
  Bound raw leaf inputs as well as merges. Use the 16 KB summary-view end
  of the briefing range for triage, fetching further evidence within budget.
  Log actual usage, cache behavior and threshold crossings where observable;
  missing adapter telemetry is a coverage gap, not zero cost. The reported
  gist cache fix has now been inspected at revision `3c190e0` (2026-10-15;
  [inspection](provenance/OPTCHAT-CACHE-REVIEW.md)); implementation regression
  checks remain required before reuse. Its replay cache rate is not an
  Odin estimate. Compactor context scope remains open at X-10.
- **Inherited relationship:** supplies experimental defaults for D7.9–D7.10
  and D18, without changing the memory hypothesis or claiming transferred
  cache economics. Checks: AC-34–AC-35; I/O contract §8/§12. Provider facts
  and source links are recorded there; deployment defaults remain subject
  to the evaluation.

## 5. Issues raised by the extraction

Each issue stays open unless its entry records the evidence that
resolved it. X-1, X-2, X-5, X-6, X-8 and X-10 are open. X-3, X-4 and X-9 are
resolved as recorded readings of existing decisions; X-7 is resolved
only as far as fail-closed handling. Every resolution is subject to the
re-review and to the operator.

- **X-1 — Phase C start versus fake-backend increments.** The Saga
  developer instructions say "Do not start C before B's API and minimum
  enforcement exist". The blueprint (§7), carried by D14.4, allows I0–I2
  against a fake Saga backend, and the I/O contract (§13) places I0–I1
  beside Phase B and I2–I3 in Phase C. **Open: producer reconciliation
  pending.** Odin's interpretation under D15 (review finding B2): I0, I1 and I2 are
  non-production work against fixtures and a fake backend; I3, any live
  delegated run, any live Saga submission, deployment cutover and the
  Phase C exit wait for Phase B's exit. Evidence: D14.4, source
  blueprint §7, source extraction plan §1, D15.8. Saga's live record
  does not carry this clarification. Record agreement in both repositories
  before describing the sequencing exception as jointly approved. This
  documentation correction does not amend Saga's record.
- **X-2 — Stop operations.** The extraction plan lists D2 as Saga-owned,
  but two of D2's four stop operations (pause planner, disable
  schedules) act on Odin's state. The map keeps the definition with
  Saga and records Odin's implementation as a consumer obligation.
  Confirm, or move those clauses to an Odin decision (review gap G2).
- **X-3 — Pinned Saga contract.** `contracts/saga/2026-10-14-14fdab3/SAGA-SERVICE.md`
  is pinned as a draft (`0.1.1-draft`, target API unimplemented; its
  producer commit is `a84f9ac28a6b4de651fccc057d33a335472f9773`, recorded
  in `SNAPSHOT.json`; pinned bytes match the canonical draft).
  **Resolved as a document check, not a handoff approval:** Appendix
  B of the I/O contract now records, per capability, what Saga's
  canonical `0.1.1-draft` provides and what is a gap (no delegation read
  operation; no published admission schema; wire details Saga still has
  open). The check compares documents only and must be repeated when
  the producer bytes are repinned. Gaps are resolved at the producer,
  never by editing the pinned copy.
- **X-4 — Archived-conversation retrieval.** D10.1 and the I/O contract
  say braid never indexes the chat log; the ecosystem plan (§7) proposes
  optional retrieval over explicitly published archived conversations.
  **Resolved as a reading** (review finding N7): the source record's §2
  says "braid still never indexes Odin's active chat" and adopts "an
  archived-conversation retrieval scope through skald with original
  record identities"; the v7 `recall` row says the same. So the
  exclusion is the active chat, and the `archive` scope is read-only.
  The reading approves no peer capability: skald retrieval (§5.11) and
  the braid and skald work (EC-06, EC-07) remain open and proposed, and
  the scope is enabled no earlier than I6.
- **X-5 — Odin naming.** D13 defines the `saga-` prefix for Saga
  deliverables but no prefix for Odin's; the new names for the
  `saga-odin` container and image are undecided. Use plain functional
  names until decided.
- **X-6 — Shadow-period bridge.** The I/O contract (§10, §14) relies on a
  shadow-period file and MQTT bridge whose code (Saga events, the
  launcher's file interface, Mimir's file adapter) lives in Saga today.
  Which repository owns that bridge during the shadow period is decided
  at code extraction.
- **X-7 — `APPROVE_UNCHANGED` on guidance.** The I/O contract's
  `publish_guidance` requires "an approved `guidance` verdict or
  `APPROVE_UNCHANGED` semantics". Under D8.4 `APPROVE_UNCHANGED` approves
  a draft as is; in the legacy guidance flow it meant "the worker is on
  track; publish nothing" (legacy triage L-OP-10). Decide which applies
  to guidance review before the review schemas are written (I0); see
  also review finding B4. **Resolved only as far as fail-closed
  handling:** the phrase "or `APPROVE_UNCHANGED` semantics" is withdrawn
  (Saga cannot check it); no verdict string by itself authorizes
  publishing guidance, so `APPROVE_UNCHANGED` alone never does; guidance
  whose class or verdict mapping is unresolved is held, never sent (I/O
  contract §6; Saga contract GD-3). **Still open:** the semantic choice
  between the two readings, that is, which guidance-review results
  authorize publication (Saga contract GAP-08).
- **X-8 — Eir webhook failures.** The legacy persona surfaced every Eir
  webhook failure because a failed pipeline removes the merge gate
  silently; I/O contract §4 logs these failures as `host` lines and
  wakes only for credential expiry or limits. Decide whether such a
  failure must wake the planner or notify the operator (legacy triage
  L-OP-12).
- **X-9 — Increment placement of peer integrations.** The blueprint
  places skald enrollment in I4 and the braid and skald history adapter
  in I5. D15 and I/O contract §13 place `recall` on braid and the skald
  archiver in Phase F (I6). The blueprint puts the Herdr adapter in I4,
  while the contract puts Herdr inspection in Phase C (I2/I3).
  **Resolved within Odin's documents** under D15 (X-1's cross-repository
  sequencing interpretation remains open): D15 and
  D10 govern, so braid and skald runtime work is I6, read-only Herdr
  inspection is I3 and the full Herdr adapter with takeover is I4; the
  blueprint (§7), the I/O contract (§13) and the roadmap now agree.

- **X-10 — Context supplied to the independent compactor.** The inspected
  gist uses preceding context to resolve references; Odin keeps a separate,
  tool-less compactor but does not specify its context projection. Define
  a bounded, source-attributed context policy before I2, with no future
  messages or cross-project leakage. Compare input-only and contextual
  summaries under ADR-005's fidelity/budget checks, including ambiguous
  references. The cache inspection does not decide the size or authorize
  sharing planner tools/prefixes. See
  [OPTCHAT-CACHE-REVIEW.md](provenance/OPTCHAT-CACHE-REVIEW.md).

## 6. Outstanding review findings

The source contract review, [`provenance/SOURCE-REVIEW.md`](provenance/SOURCE-REVIEW.md),
returned **CHANGES_REQUIRED**. Its final disposition is recorded in
[`provenance/HANDOFF.md`](provenance/HANDOFF.md) after an independent
re-review. The corrections below are applied to the live documents
against existing decisions; the table records the original source-review
dispositions, separate from the later Odin ADRs in §4. None describes
implemented behaviour. X-1 still needs producer reconciliation. Each
resolution, with its evidence and what stays open, is in
[`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md).

| Finding | Subject | State in this checkout |
|---|---|---|
| B1 | Three different authority orders | Corrected: decisions, then contract, then blueprint, then roadmap, in every Odin entry document |
| B2 | Phase-to-increment mappings disagree | Odin's mappings agree internally (X-9); I/O contract §13 separates Saga gates and Odin increments. X-1 remains open: Saga has not recorded the fake-backend sequencing interpretation |
| B3 | Run admission does not bind the launch configuration | Corrected in `submit_run` and B-02: request id, `prd_digest`, `launch_config_digest`, verdict and approval all bound; envelope and encoding open at Saga |
| B4 | Every guidance requires a verdict, contradicting D8 | Corrected in `publish_guidance`: routine guidance gets mechanical checks, material guidance its required D8 review, unresolved guidance is held; X-7's semantic choice open |
| B5 | Odin's outbox publishes to MQTT across the Saga boundary | Corrected: Saga owns revisions and reconciliation; Odin reconciles through the API (`superseded` in B-13); AC-28 split with Saga's CT-18; `emit_event` local, B-14 withdrawn |
| B6 | Submission request id minted in two places; non-ULID example | Corrected: `stage_run` preallocates the ULID before review; reused by submission and retries; a restart mints a new id and renews bindings; example replaced |
| B7 | `shell` can expose credentials to Odin's turns | Corrected as a design requirement: isolated planner workspace, no credential reachable, results redacted before logging, fail closed (I/O contract §7). Not implemented; check due in I0/I2 |
| N1 | D14 amendment instruction stale in the plan; gate not met while changes are required | D14 already permits the scaffold; the gate stays unmet until the re-review |
| N2 | Stale "untracked/uncommitted" provenance | Addressed in Odin's copies |
| N3 | D16 names contract v4 | Recorded in D16 and the decision map; source unchanged |
| N4 | Old contract section numbers in the decision record | Annotated where carried (D19 note, §3 item 11, decision map) |
| N5 | Acceptance range AC-01–26 and Appendix D omissions | Addressed in Odin's I/O contract |
| N6 | Effect states in §2 omit `held`, `cancelled_stale`, `superseded` | Corrected in I/O contract §2 |
| N7 | braid "never indexes the chat log" versus archive scope | Corrected as a reading (X-4): active-chat exclusion; read-only archive scope; peer capabilities still proposed |
| N8 | D24 locked while the `api` default is still "proposed" | Corrected: recorded as default, pending operator confirmation, in D24, the map and the I/O contract; billing re-test open |
| N9 | Eir requests take three different routes | Corrected: Saga's task request (B-16) only; X-8 stays open |
| N10 | Peer contracts and sibling links | Addressed: peer inventory in [`contracts/README.md`](contracts/README.md); peer sources are cited as non-required text |
| N11 | `limit-paused` versus `limit_paused`; WebFetch missing from the planner's network column; legacy paths | Corrected: spelling note in Appendix C (wire spelling Saga's, INC-08); WebFetch added; legacy paths labelled in §6 |
| G1–G7 | Operator identity; stop split (X-2); restart and review cost; Saga's validator; planner answers; unconfirmed integrations; unsettled defaults | Open implementation gates with owners and milestones in the [roadmap](ROADMAP.md#implementation-gates-from-the-source-review); Saga carries its parts as IG-1 to IG-7 |
