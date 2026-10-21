# Odin — decision record

> **Status:** candidate live record for the documentation handoff of
> extraction snapshot `2026-10-14-14fdab3`. The handoff is **not yet
> recorded**; the independent D14 re-review remains pending. The source
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
> **2026-10-16.** §4 now records ODIN-ADR-006 to 015, the first Odin
> ADRs that supersede or amend inherited clauses Odin owns (D8, D10,
> D20, D22, and Odin-side clauses of D7, D15, D24). Each names the
> clause it changes; the carried text stays verbatim with an ownership
> note. Saga-owned clauses are not touched; the consolidation's
> Saga-side parts are tracked as issue X-14 and remain proposals in
> [`design/CONSOLIDATION-PLAN.md`](design/CONSOLIDATION-PLAN.md).
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

Ownership notes (2026-10-16): ODIN-ADR-009 clarifies D7.2 (the service may start a session through a workstation session host it commands; the SDK call still originates from Odin-controlled code); ODIN-ADR-015 honours D7.6 by starting its fixture-only Pi RPC control only after the Claude Code adapter is validated at I2. D7.1, D7.4 to D7.5 and D7.7 to D7.12 are unchanged.

Ownership note (2026-10-19): ODIN-ADR-024 amends D7.2 and D7.7 for a
bounded executive conversation pilot using native interactive Claude Code
and Remote Control. D7.4's two loops and D7.11's commitment authority
remain unchanged. The pilot's conversation is not an authenticated Odin
operator-command adapter or the full SDK/session-host implementation.

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

Ownership notes (2026-10-16): ODIN-ADR-013 supersedes D8.5 and the single-reviewer reading of D8.3 to D8.4 with two reviewer positions and a service-run consensus, as a hypothesis judged on D8.7's measures. The bounded rounds, evidence rule, caps and measurement stand. Saga's verdict format and reviewer-key verification (D2.4a, B-10) are unchanged.

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

Ownership note (2026-10-20): ODIN-ADR-028 adds the operator-authorized
development evaluator and development loop controller. It amends D9.3's
exclusion of planning/decomposition and D9.4's replay/shadow activation
sequence only for this bounded development loop. Required Mimir review,
Saga approval and direct operator stop remain independent. The evaluator
does not classify operator messages into new authority.

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

Ownership notes (2026-10-16): ODIN-ADR-006 amends the delivery modes in D10.1 (braid as a library over published, scoped data) and D10.2 (capture as a module writing to Odin's transcript namespace, with skald's archive kept as a standalone sink); ODIN-ADR-007 amends D10.5 (heimdall's task layer is retired by import instead of bridged); ODIN-ADR-011 amends the placement in D10.4 (guarded input as a gated process of the workstation daemon under D21). The exclusion rules in each row stand. D10's title and D10.6 are unchanged until the Saga-side decisions in X-14 exist; the repository consolidation is a proposal (ODIN-ADR-018, not recorded). The capture, sensor and input code reaches Odin's deployables only after the peer-side decisions (G-10) and, for any shared repository, the Saga-side ones (G-9).

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

Ownership notes (2026-10-16): under D13.2a the Mimir name continues to designate the reviewer role; whether the two reviewer positions of ODIN-ADR-013 are one persona or two is open with X-5. The repository and deliverable names the consolidation plan would need are Saga-side and operator questions (X-14, X-5); nothing here reuses a standalone repository's name for a new component.

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
D15.8: I0 uses fixtures, while I1 to I2 use fixtures and a fake
backend; all are non-production and may proceed while Phase B is in
progress. I3, every
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

Ownership notes (2026-10-16): ODIN-ADR-008 reorders work within I0 and I1 under D14.4 without changing a phase or gate; ODIN-ADR-015 places a fixture-only Pi RPC control after I2 without moving D15.Eb's full second adapter from Phase E. The phases, gates and D15.8 are unchanged; X-1 stays open.

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

Ownership notes (2026-10-16): ODIN-ADR-012 reads D18.5's step 7 as "preserved by the chosen carrier"; ODIN-ADR-013 adds the reviewer-position arm (against single review and an equal extra verification budget) and ODIN-ADR-014 the session-class oracle evaluation to the measurements under D18.2 and D18.4.

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

Ownership notes (2026-10-16): ODIN-ADR-015 satisfies D19.5's "early enough" with a fixture-only Pi RPC control after I2; ODIN-ADR-013 keeps D19.3 (review stays switchable and a disabled position never waives required review).

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

Ownership notes (2026-10-16): ODIN-ADR-007 supersedes D20.10 (the heimdall ownership bridge) for Odin; ODIN-ADR-010 supersedes the "two operator interfaces" clause of D20.5 while keeping its one-command-path, binding and stop rules, and amends D20.8's handling table with new inbound sources and the attention-prompt effect; ODIN-ADR-009 clarifies D20.1 and D20.2 with the workstation daemon and session host. D20.3, D20.4, D20.6, D20.7, D20.9 and D20.11 are unchanged.

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

Ownership notes (2026-10-16): ODIN-ADR-011 implements D21.4's lease at a single boundary, a gated process of the workstation daemon, and preserves D21.5 and D21.7. Desktop authority (§5.9) remains open; nothing is enabled by it.

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

Ownership notes (2026-10-16): ODIN-ADR-012 supersedes D22.3's "Dotprivate carries the package" and D22.5 for Odin: Odin produces the package and runs git itself; dotprivate is no longer on Odin's dependency path. D22.1, D22.4 and the three-state reporting rule stand; D22.2's full-archive backup ownership moves with the capture module to the transcript namespace's standalone sink.

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
another backend. ODIN-ADR-026 amends D23.1–D23.3 for the operator's native
executive development profile: direct development work does not require
Saga or an Odin-managed backend and does not receive Saga guarantees.

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

Ownership notes (2026-10-16): ODIN-ADR-009 amends D24.3 for Odin's session classes only: a workstation session host holds a local model credential in a protected store the service references, with one refresher per lineage, never the development login (D24.6). ODIN-ADR-013 adds a per-position entry to D24.2a's launch configuration. D24.4a and D24.8a are unchanged.

## 3. Inherited open decisions (source §5)

The original question numbers are preserved. Items 3 and 5 are partly
settled by the operator-directed corrections below; the remaining questions
stay open. The decision map assigns each an owner.

1. **Is Saga active again?** Braid's roadmap recorded "Saga is deferred
   by user direction" in September; Phase B assumes it is not. Blocks
   Phase B and therefore I3.
   The consolidation's Saga-side decisions (X-14) are recorded in Saga's
   repository whether or not it is active.
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
    intended mechanism and when its implementation lands. ODIN-ADR-012
    takes dotprivate off Odin's dependency path; the question is now
    dotprivate's own, with heimdall and skald as its named consumers.
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

These records implement the operator's requested corrections on 2026-10-14
(ADR-001 to 005) and the operator's consolidation direction of 2026-10-16
(ADR-006 to 015; evidence in
[`research/consolidation-2026-10/`](research/consolidation-2026-10/README.md),
plan in [`design/CONSOLIDATION-PLAN.md`](design/CONSOLIDATION-PLAN.md)).
They govern Odin's work; they neither close D14's handoff nor change a
producer's interface. Inherited text and identities remain intact; where
an ADR supersedes an Odin-owned inherited clause, the carried text stays
verbatim and an ownership note under that decision points here. The
conditional ADRs the plan drafts for Saga-owned clauses (016 to 019) are
**not recorded**; they wait on X-14.

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
  The workload-class configuration is specified in I/O contract §5; I0
  defines its validated schema and fixture representation. These classes
  are distinct from capability profiles and process roles.
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

### ODIN-ADR-006 — One event substrate with namespaces

- **Status:** default design; not implemented.
- **Context:** Odin's history, the transcript archive (skald) and the
  workstation surface events (standalone heimdall) would otherwise live
  in three stores with three identity schemes, and the research that
  motivated the consolidation found every one of the operator's tools had
  reinvented the append-only event store. The I/O contract's one
  transactional core (§9) and D4's ledger split must both survive.
- **Decision:** Odin keeps one append-only event substrate with named
  namespaces: Odin history, transcript archive, workstation surface
  events. Each namespace has exactly one writing component, its own
  retention and redaction rules, and revisioned records, inbox, outbox
  and cursors that commit in the same transaction as the history they
  belong to. Retrieval (braid) runs as an in-process library over
  published, scoped namespace data in its own per-dataset files and never
  indexes Odin's active chat. An execution-ledger namespace is reserved
  as a read-only mirror of the execution backend's own store, filled only
  through the backend's API and event cursor; the backend's store stays
  authoritative and is never written by Odin.
- **Consequences:** §9 intake, processing, outbox and recovery semantics
  are unchanged (AC-01 to AC-03, AC-27). JSONL files and `view.json`
  remain projections. Redaction propagates across namespaces with
  per-destination pending state (AC-26). Capture gaps stay visible
  (AC-18). Store topology, single-writer enforcement by process ownership
  and failure domains are open at X-11. Capture runs on the workstation
  and the substrate on the homelab, so the capture module keeps a local
  durable spool and appends one atomic batch per checkpoint (proposed
  scenario AC-41). Skald's own archive remains a standalone sink so the
  capture binary stays useful without Odin.
- **Inherited relationship:** amends D10.1's delivery mode ("child
  process over its stdio protocol" becomes a library) and D10.2's ("via a
  provider adapter" becomes a capture module writing the transcript
  namespace) for Odin. Preserves D4.1 and D4.2 (the ledger is Saga's; the
  mirror decides nothing), D6.5, D7.11 and D7.12, D22.2's exclusion of
  live databases from git synchronization, and the X-4 reading. Amends
  I/O contract §1, §3, §9 and Appendix A; supersedes the ecosystem plan's
  preamble sentence that Odin "does not merge their databases" for the
  transcript and surface-event namespaces only.
- **Must not claim:** that the execution ledger is an Odin record or that
  Odin's history decides approval or completion (D4.2); exactly-once
  (D6.5); that a shared store is a security boundary; that braid or skald
  runtime integration moved earlier than I6 unless an ADR moves it.

### ODIN-ADR-007 — The commitment record is the single task authority

- **Status:** locked direction for Odin; migration not designed.
- **Context:** D20.10 planned a projection bridge because standalone
  heimdall and its skald amendment assign accepted task state to
  heimdall. Two authorities, even bridged, need a projection API, a
  command relay and stale-revision handling (EC-05) that add nothing once
  heimdall's task layer is retired. The code inventory found heimdall's
  task records lack owner, assignment and budget fields and that its
  ranked planner was never built.
- **Decision:** Odin's commitment record is the only editable record of
  task state, checkpoints and task decisions for work run through these
  tools. Standalone heimdall's task, checkpoint and decision layer is
  retired by a one-time import, not bridged: each native record is
  imported with its original identity and revision as provenance and a
  receipt, and later heimdall-side edits are refused. Delegations,
  approvals, verdicts and run states remain the execution backend's
  records (D4, D17); the commitment record references them and never
  copies their authority. Heimdall's remaining value to Odin is its
  surface sensors, which ODIN-ADR-009 places in the workstation daemon.
- **Consequences:** Commitment (I/O contract §2, Appendix A) gains
  checkpoint and task-decision fields; the mapping from heimdall's record
  types is kept with the schemas. The import is a migration step (§14)
  with an idempotent receipt (proposed scenario AC-38). EC-05 and AC-20
  are withdrawn; their identifiers stay in the text. I5 loses "heimdall
  external views". One human view shows commitments, runs and transcripts
  with their owners attributed. Peer-side retirement is heimdall's to
  record (EC-13).
  An ignored edit is not evidence that the source task layer was retired;
  migration acceptance requires enforceable refusal on the heimdall side
  under EC-13 and G-10.
- **Inherited relationship:** supersedes D20.10 for Odin. Amends D10.5's
  "optionally connected later as a human-facing continuity surface" and
  its release and CI condition. Consistent with D10.5's "one authoritative
  record", §1.b and D7.11.
- **Must not claim:** that heimdall's record or the skald–heimdall
  amendment has changed (that needs a decision recorded in those
  repositories); authority over delegations or approvals (D17, D2.1);
  that imported checkpoints corroborate anything independently (D22.4).

### ODIN-ADR-008 — I0 narrowed to the event log and record schemas

- **Status:** locked sequencing within Odin; no phase change.
- **Context:** I0 bundled schemas, the event envelope, the capability
  matrix, the fake backend, the three-document fixture, the ownership
  mapping and the planner isolation check. The substrate and the record
  schemas are the shared prerequisite for everything else, and the
  operator wants runtime code to exist before the next design pass.
- **Decision:** I0 delivers the versioned event envelope and namespaces
  (EC-01, ODIN-ADR-006), the record schemas of I/O contract §2 and
  Appendix A with the changes in ODIN-ADR-007, 009, 013 and 014, and
  fixtures for the duplicate, stale and unknown cases, validated by both
  the Go and the Python implementation against the same fixture set. The
  adapter capability matrix, the fake Saga backend, the synthetic
  three-document fixture and the ownership mapping move to I1. The
  planner tool-isolation check moves with the profile schemas and must
  still pass before I2 claims the planner profile.
- **Clarification:** envelope and unaffected record-schema work can begin
  in I0. Resolve X-7 before writing the Review/guidance schemas;
  fail-closed handling does not answer the open semantic choice.
- **Consequences:** blueprint §7, I/O contract §13 row B, the roadmap's I0
  and I1 entries, README and AGENTS.md §1 change together. I0's exit keeps
  "no peer API is invented as implemented". Every displaced item is named
  in its new increment.
- **Inherited relationship:** within D14.4 (increments govern code
  extraction) and D15 (the phase mapping is unchanged). X-9 is restated,
  not reopened.
- **Must not claim:** any phase or gate change; resolution of X-1; that
  any displaced item was dropped.

### ODIN-ADR-009 — Workstation daemon and session host

- **Status:** default design; not implemented.
- **Context:** the Agent SDK runs a harness as a child of the process that
  calls it, so a service on the homelab cannot by itself run a session on
  the workstation. Native sessions the operator wants to watch or take
  over, Herdr control, desktop sensors, transcript capture and the human
  surfaces all live on the operator's machine, while records and authority
  live in the homelab service. Session bindings already carry `host` and
  `incarnation` (I/O contract §2) but have no offline state or
  environment evidence.
- **Decision:** A workstation daemon runs on the operator's machine. Its
  session host dials out to the Odin service, registers a stable host
  identity and heartbeat, and starts, resumes, interrupts and retires SDK
  and RPC harness sessions only on the service's command; session
  records, ownership generations and budgets stay in the service. A
  binding whose host is unreachable becomes `host_offline`: its sessions
  count as unavailable, not failed, nothing is retried until the host
  returns, and resume reconciles before any new turn (proposed scenario
  AC-37). Each host publishes an Environment record from a deterministic
  probe (harness and Herdr versions, sandbox and isolation support,
  available surfaces and sensors, credential lineages present); the
  service refuses session classes whose required capabilities the record
  lacks and says so in `now`. Herdr is driven through its CLI, locally by
  the daemon or over SSH with `herdr --machine` where no daemon runs; the
  SSH key and the Herdr target live in the service, never in a session.
  The daemon also hosts the surface sensors retired from heimdall's task
  layer (ODIN-ADR-007), the capture module (ODIN-ADR-006) and the operator
  surface adapters (ODIN-ADR-010); guarded desktop input is a separate
  gated process (ODIN-ADR-011). Sensors and capture remain buildable as a
  standalone binary with a local store.
- **Consequences:** I/O contract §7 isolation must be provided on the
  workstation or the planner class is refused there. The model credential
  for local sessions lives in a protected store on the host, referenced
  by the service, with one refresher per lineage; it is never the
  operator's development login (X-12). Stop works with the host offline
  and reports uncertain local outcomes (AC-10). The session-host protocol
  is Odin's own deliverable, not a peer item. Herdr's automation API
  remains unreviewed (§3 item 8) until the adapter is built against the
  installed version.
- **Inherited relationship:** clarifies D7.2 and D20.1 to D20.2. Amends
  D24.3 for Odin's session classes only. Preserves D24.4a, D24.6, D20.6 to
  D20.7 and D23.3's stated missing guarantees.
- **Must not claim:** Saga's guarantees for anything the host runs
  (D23.3); that sensor observations are authority; that Herdr's API has
  been reviewed; that development-login use is permitted.

### ODIN-ADR-010 — Operator surfaces, new inbound sources and attention prompts

- **Status:** default design; voice is backlog until its data-policy
  decision (X-13).
- **Context:** D20.5 names two interfaces, the Herdr workspace and
  Telegram. The operator works across a workstation, a laptop and a
  phone, is already short of attention, and wants Odin to use workstation
  observations and transcript lifecycle to reprioritise and prompt them
  without another window. The legacy "nudge" (L-PU-1) was a synthesized
  keystroke into a TUI; that mechanism is gone.
- **Decision:** Operator surfaces are adapters on one service API, and
  every one of them enters the same recorded command path: the terminal
  workspace, Telegram (on the homelab, so approvals and stop work when
  the workstation is off), a summoned terminal conversation, a status
  bar, desktop notifications with typed actions, and later voice.
  Heimdall-derived observations (focus, idle, surfaces) and capture
  lifecycle events (session started, ended, gap) are typed inbound
  sources, recorded as state-only or log-only by default, never
  authority, and they wake a planner only through typed rules. Raw
  observation content is operator-derived and stays with the local
  provider under D9.5; frontier sessions receive derived signals only.
  An **attention prompt** is a typed outbound effect, an operator-facing
  proposal with its evidence reference and a mandatory response (done,
  snooze, dismiss, override with reason) that is itself a record; it
  carries per-surface and per-day caps, coalescing, quiet hours, a
  cooldown and expiry, and it leaves shadow mode only when logged
  outcomes support the caps. A message queued to an Odin-run session uses
  the adapter's supported injection and is never a synthesized keystroke
  or guidance to a Saga run. Ranking is recomputed in code on every
  event; only a change that survives a hysteresis window is surfaced, and
  observations of a focused session defer non-critical prompts to that
  session's boundary.
- **Consequences:** an approval is accepted only on a surface that shows
  the request id and proposal digest (AC-06, AC-30); voice may carry
  questions, clarification answers and stop, never an approval, until a
  hash-binding mechanism exists. No evaluator handles operator input
  (D9.3). Take control suspends prompts to that session (AC-11). Caps are
  logged as in §4 (AC-23). New rows enter I/O contract §3 `src`, §4,
  Appendix C and the outbox destination table; a proposed scenario AC-39
  checks caps and the response record. The single gateway is also what
  makes the running log complete: no harness gateway may face the
  operator directly under Odin (D20.5's "never a second Odin").
- **Inherited relationship:** supersedes D20.5's "two operator
  interfaces" while retaining its one-command-path, binding and stop
  rules. Amends D20.8. Preserves D20.9, D20.11 (Herdr and Telegram remain
  the first configuration), D9.5, ODIN-ADR-002 and ODIN-ADR-004's four
  hooks. Redefines L-PU-1's "nudge": the legacy mechanism is superseded,
  the requirement is carried as the attention prompt.
- **Must not claim:** voice approvals; a fifth evaluator hook; that
  observations change commitments; that the extra surfaces are part of
  the restrained initial product (D19.6).

### ODIN-ADR-011 — Desktop input as a gated capability of the workstation daemon

- **Status:** default (as D21); disabled until the operator decides §3
  item 9.
- **Context:** D21.4 requires an exclusive desktop-control lease enforced
  "at a shared broker or tool boundary across cooperating clients". The
  code inventory found wayland-computer-use has no lease, grant or caller
  identity, that approval is left to each MCP client, and that no single
  process holds input on the workstation today (pointer buttons through a
  root `ydotoold`, keys through the compositor's virtual keyboard, focus
  through Hyprland IPC, all reachable by every process of the operator's
  user).
- **Decision:** Guarded desktop input runs as its own process within the
  workstation daemon, under a dedicated Unix user that alone owns the
  input socket. That process is the only holder of the seat lease for
  every cooperating client and checks lease, grant scope, target and
  expiry on admission and again before every input segment. It is
  disabled until a delegation naming desktop authority exists and the
  operator has decided §3 item 9. When enabled it serves only a dedicated
  desktop worker, never a planning session, the session host or a
  container worker. The capability's own guards (frame expiry, pinned
  target, pixel and focus checks, no replay, budgets) stay in force, and
  its observation and input MCP servers remain usable without hosted
  inference through thin shims that carry the caller's session identity.
  Whether the compositor can deny the virtual-keyboard protocol and
  dispatcher IPC to other clients is unverified; until it is, the lease
  binds cooperating clients only, as the ecosystem plan already states.
- **Consequences:** EC-10's shared seat broker becomes this process.
  DC-01 to DC-08 apply unchanged. Enabling it is I7 work by operator
  decision. The wayland-computer-use repository keeps its Codex plugin,
  evaluations and reports standalone; its 12 unpushed local commits are
  pushed before any import so the public copy and the daemon's contract
  hash agree. Peer-side recording is WCU's (EC-16).
- **Inherited relationship:** amends D10.4's placement and preserves its
  isolation rule. Implements D21.4. Preserves D0.5, D2.3, D21.1, D21.5 to
  D21.7 and D23.4.
- **Must not claim:** that desktop authority is granted; inclusion in the
  initial product; Saga admission for desktop work; that a classifier can
  override a guard (DC-03); device-wide exclusivity before the compositor
  restriction is verified.

### ODIN-ADR-012 — Preservation without dotprivate on Odin's dependency path

- **Status:** locked direction; carrier undecided.
- **Context:** D22.3 names dotprivate as the carrier, but its
  selected-files contract is an unimplemented proposal whose named
  consumers are heimdall and skald, not Odin (EC-08), and the operator
  wants it off Odin's path. Plain git with receipts gives Odin the
  properties it would have borrowed.
- **Decision:** Odin does not depend on dotprivate. Odin writes the
  selected project package (D22.1) atomically to its own export
  directory, stages only the package path, applies its own secret and
  personal-data screen, and records receipts that distinguish "copied
  locally", "committed" and "confirmed on the remote", reconciling an
  uncertain push by observing the ref before any retry. The export
  directory never sits inside a dotprivate-managed `.private` clone,
  whose background sync would race it. The operator may still ingest the
  export with dotprivate by hand; that is dotprivate's feature, not an
  Odin interface.
- **Consequences:** EC-08 and EC-09 are withdrawn from Odin's plan (ids
  kept). AC-24 and AC-25 are retargeted to Odin's own receipts. §3 item 10
  becomes dotprivate's own question. Full-archive backup ownership
  (D22.2) moves with the capture module to the transcript namespace's
  standalone sink. D18.5 step 7 reads "preserved by the chosen carrier".
- **Inherited relationship:** supersedes D22.3's "Dotprivate carries the
  package" and D22.5 for Odin. Preserves D22.1, D22.4 and the three-state
  rule.
- **Must not claim:** remote durability not observed on the ref; any
  change to dotprivate's contract or license (ODIN-ADR-001); that AC-24 or
  AC-25 pass.

### ODIN-ADR-013 — Two reviewer positions with service-run consensus

- **Status:** **hypothesis.** It stays only if it beats single review and
  an equivalent extra verification budget on D8.7's measures.
- **Context:** D8.5 records that Opus and Sonnet share a family and their
  errors are not independent. The operator's original vision has two
  frontier models reach consensus on major decisions before execution,
  with the operator signing off on major tasks. The field evidence in the
  research notes says consensus by conversation converges cheaply and
  that the orchestrators which survived kept judgment inside bounded
  turns, so consensus is run as a protocol by the service, not as a chat.
  "Position" is used because "seat" already means the desktop seat lease
  (D21.4) and the subscription seat (§3 item 6).
- **Decision:** Required review is performed by two reviewer positions on
  frontier models of different families where the adapters allow it.
  Each position receives the same deterministic evidence pack and sees
  neither Odin's conversational reasoning nor the other position's
  findings. Service code combines the verdicts by the action-level
  pair rule in I/O contract §10: both positions must approve for an
  approving outcome; any `FLAG` goes to the operator under Saga ADM-7,
  as does any `REJECT` or `INSUFFICIENT_EVIDENCE`. A disagreement that
  survives the single permitted corrective re-review goes to the
  operator with both positions and their evidence (proposed AC-40).
  Mixed `APPROVE`/`APPROVE_UNCHANGED` serialization remains for the I0
  review schema; no combined verdict is submitted until it is defined.
  "No change needed" (`APPROVE_UNCHANGED`) is a
  first-class outcome. The combined verdict is recorded under the
  reviewer identity key, which the service holds in a signer component
  that no session or planner tool can reach (D2.4b), in the verdict
  format Saga verifies; running that signer as a separate process is the
  option D2.5 already offers and is the default deployment here. Roles are assigned per project: one planning owner and one
  standing reviewer position, and they may swap between projects.
  Disagreement is the protocol's most valuable output; matching approving
  results pass into the log without an operator message.
- **Consequences:** D24.2a launch configuration gains a per-position
  entry. Sending evidence packs to a second provider needs a data-policy
  decision (X-13). Caps are per position and total (D8.6). AC-22 is
  re-scoped: an unavailable position never waives required review. D18.2
  measures the consensus arm against single review and the equal-budget
  baseline. Consensus stays switchable (D19.3). The Mimir name continues
  to designate the reviewer role; whether one persona or two is a naming
  question under D13.2a.
- **Inherited relationship:** supersedes D8.5 and the single-reviewer
  reading of D8.3 to D8.4; keeps the bounded rounds, the evidence rule,
  D8.1's triggers, D8.2's mechanical-first rule and D8.6 to D8.7. D2.5 is
  unchanged: its "Mimir" reads as the reviewer positions and its
  separate-process option is taken. §3 item 2 stays open for the model
  per position.
- **Must not claim:** that the backend accepts per-position verdicts (that
  is a Saga contract change, B-10); that a decision model settles
  disagreement (D9.1); waiver when a position is unavailable; a resolution
  of X-7; independence of errors before measurement.

### ODIN-ADR-014 — Session-class decisions recorded for later evaluation

- **Status:** default; evidence only. Amends ODIN-ADR-004.
- **Context:** ODIN-ADR-004 makes code choose session classes but keeps no
  record of the rejected alternatives, so the choices cannot later be
  judged against an independent task-level oracle of the kind router
  evaluations use. The I/O contract already records a routing
  consequence and a later assessed outcome for evaluator results, but not
  for class selection.
- **Decision:** Each code-made session-class selection records the chosen
  class, the rejected candidate classes with their deterministic reasons,
  the inputs used and the configuration revision, so that an independent
  outcome assessment can evaluate the choice later (D18, §3 item 2). The
  record never changes routing at run time. Changing routing on the basis
  of these records requires D9.4's review, replay and shadow period, and
  a learned model-tier router remains off.
- **Consequences:** the records live in the Odin-history namespace
  (ODIN-ADR-006), subject to D9.5's sensitivity rule and D7.12's
  redaction. New classes (reviewer positions; Bragi and Eir only if a
  Saga-side decision transfers them) belong in the workload-class
  configuration specified in I/O contract §5. Its validated schema and
  fixtures are I0 work; this does not add a class or set a model default.
  The D18 evaluation of class defaults uses the same harness,
  fixed prompts, tools and graders, the best and cheapest single-class
  baselines, and the task-level oracle as a reference.
- **Inherited relationship:** amends ODIN-ADR-004; keeps its four hooks,
  "no silent downshift" and "no learned model-tier router".
- **Must not claim:** that a learned router or an oracle exists; a fifth
  hook.

### ODIN-ADR-015 — Early Pi RPC adapter as a fixture-only control

- **Status:** locked experiment placement; fixture-only.
- **Context:** D19.5 wants the second adapter "early enough to test whether
  the boundary is real". The operator's motivation names complete control
  as a goal; Claude Code through the SDK is a closed binary whose billing
  and policy changed three times in 2026, and Pi's loop is open source.
  The roadmap's Codex experiment after I2 is a proposal, not an ADR.
- **Decision:** After I2's exit, a minimal Pi RPC adapter runs the same
  bounded assignment and session replacement against the fake backend, as
  a control for the Claude Code adapter, and publishes its capability
  matrix and gaps. It is non-production and fixture-only. The full second
  adapter and Phase E's exit remain I5. No common adapter framework is
  extracted until both adapters exist. Claude models through Pi use an
  API key, never the subscription and never Pi's Anthropic OAuth path
  (AGENTS.md §6; D24).
- **Consequences:** replaces the roadmap's Codex proposal, or the two run
  side by side if both are wanted. Odin's D0.7 wording changes only if Pi
  runs other providers' models in production. Evidence is labelled
  fake-backend.
- **Inherited relationship:** amends D15.Eb's timing for an early control
  only. Honours D7.6 by starting after the Claude Code adapter is
  validated at I2. Satisfies D19.5.
- **Must not claim:** Phase E's exit; any live run before Phase B; X-1
  resolution; proven portability.

### ODIN-ADR-020 — Model and delegation evaluation protocol

- **Date and status:** 2026-10-16; default evaluation specification.
  Local metadata/accounting checks are implemented; comparative trials and
  actual harness checks remain unimplemented. Records the application of the operator-supplied
  orchestration research; it is not a measured result or a model choice.
- **Context:** Configured mixed-model routes and author observations do
  not establish comparative quality. Consultation, executable work,
  harness changes, extra inference and selective reporting can each
  explain apparent gains. The [review](provenance/MODEL-ORCHESTRATION-REVIEW.md)
  records source checks and what is not adopted.
- **Decision:** Evaluate a configuration as its task, ownership pattern,
  exact requested and resolved model identities, harness/adapter/provider
  path, context/tools, permissions and resource policy. Separate bounded
  advice, read-only `work` subagents, reviewer positions and Saga execution.
  Freeze delegation packets for worker comparisons before measuring
  adaptive whole episodes. Compare solo operation, additional solo effort,
  same-model delegation, repeated same-model samples and a fixed workflow
  before crediting model diversity. Hold the harness fixed for model
  comparisons and models fixed for harness comparisons where supported;
  disclose unmatched capabilities as confounds.
- **Measurement:** Verified end-to-end success is primary. Count all
  attempts, including failures, retries, repair, review, compaction,
  evaluators and tools. Report cost per accepted task, total/unconditional
  cost, elapsed-time distributions, deadline success, operator time and
  failure attribution. Pin prices and billing modes; unknown usage stays
  unknown, and repricing is not a rerun. Use paired repeated trials,
  held-out task lineages and independently assessed outcomes. Operational
  defaults, dollar caps and deadlines are separate conditions. A small
  pilot diagnoses failures and variance, not a universal ranking.
- **Checks and placement:** Acceptance §3 specifies the protocol. I1
  defines validated evaluation metadata and extends the adapter capability
  matrix; I2 checks read-only child confinement and partial/stale returns
  (proposed AC-42–AC-43), AC-36's observational class records, and child
  cap/stop behavior after X-15 is resolved (proposed AC-44). The Pi control
  uses the same protocol after I2. Live repeats require I3/Saga Phase B;
  the D18 comparative report remains Phase G. Missing telemetry or an
  unsupported condition is reported, never filled with an assumed zero.
- **Inherited relationship:** operationalizes D18.1, D18.2, D18.4 and
  D19.4; adds detail to the evaluations in ADR-013/014/015 without
  superseding them or any inherited clause. I0 remains ADR-008's narrow
  schema increment. The current session-class policy and two-loop
  architecture stand; learned model-tier routing remains off.
- **Must not claim:** a best model pair, independent reviewer errors,
  framework adoption, production advisor/peer-handoff support, Saga
  guarantees from local children, new producer capabilities, a resolved
  data/billing policy, or a completed runtime evaluation. Proposed
  comparisons never remove required review from live work.

### ODIN-ADR-021 — Local implementation storage and contract conventions

- **Date/status:** 2026-10-16; default implementation choice under the
  operator's instruction to complete local development while leaving live
  credentials undecided. No live deployment or producer change is authorized.
- **Decision:** Use one SQLite WAL file per namespace. A nonblocking OS
  file lock admits one writing process per namespace; each component opens
  only its own namespace. Odin records, inbox, cursor, outbox and history
  commit together inside the Odin-history database. There is no atomic
  transaction across namespaces: capture uses its durable spool, and mirror
  updates commit with their producer cursor. A gap or conflicting mirror
  sequence stops ingestion for reconciliation, never authors a correction.
  Separate files isolate storage transactions, not processes or Unix users.
  Production file ownership and sandbox enforcement remain I2 deployment
  checks. Local code runs no untrusted session or external effect.
- **Contract conventions:** Runtime JSON Schemas use Draft 2020-12, closed
  record objects, `schema_version: 1`, `record_type`, and Appendix A's `rev`
  spelling for revision. UTC timestamps use `Z`; IDs are canonical ULIDs.
  Producer-native identities remain opaque references. The 12 unaffected Odin-owned
  record shapes and the event envelope are validated independently in Go
  and Python. Saga delegation/run schemas are not invented here. Local
  deterministic JSON digests are explicitly not Saga's unresolved canonical
  wire digest. JSON/YAML runtime data uses schemas; native language build
  manifests and dependency lockfiles use their standard tool formats.
- **Checks:** namespace-writer lock, transaction rollback, duplicate intake,
  stale revisions, unknown effect recovery and mirror cursor tests in the
  local suite. Cross-language schema fixtures include gated Review rejection,
  unbound approval, invalid dates/IDs, partial/unknown effect evidence and
  unknown fields. These establish only their tested local behavior.
- **Relationship:** implements X-11's local physical layout and D6/D7/D19
  without superseding a clause. X-11 remains open for production process
  ownership/failure-domain validation. X-7, X-12, X-13 and X-14 stay open;
  unresolved guidance publication and live transports are disabled. See
  [implementation status](IMPLEMENTATION-STATUS.md) for local evidence
  and the remaining full-I1/I2 work.

### ODIN-ADR-022 — Experimental portfolio coordination and scoped orchestration

- **Date/status:** 2026-10-16; operator-authorized local experimental design. The fake-backend prototype may record and check the protocol. No live model route, second production adapter, delegated run or credential distribution is authorized by this ADR.
- **Decision:** For a portfolio of software, research or infrastructure projects, a configured Fable coordinator may identify priorities and request work. Each project keeps one Astra planning owner with explicit assignment and commitment records. Opus or Sol workers receive bounded Saga delegations only through the service and Saga adapter. A bounded chirality consultation returns read-only, source-attributed advice with confidence and uncertainty; it cannot approve, route, edit, submit or complete work. The service owns admission, state, budgets, stop, approval and reconciliation. Model names here are configured experimental roles, not claims about a provider, model quality or an available harness.
- **Handoff:** Every coordinator-to-owner, owner-to-worker and consultation return has a versioned typed packet: source IDs and revisions, project/assignment/commitment identity, objective, scope, accepted decisions, dependencies, checks, evidence references, authority, deadline and budget. Receiving a packet does not transfer authority or establish completion. Stale, missing or ambiguous context is held for reconciliation; source material stays retrievable. The one project planning owner remains accountable for integration.
- **Incident authority:** The operator may approve a time-bound, project- and action-scoped incident grant through the recorded command path. The service validates principal, exact scope, expiry and revocation at use and logs each exercise. Grants confer no blanket model credentials and no bypass of Saga, required review or direct stop. A model request, voice transcript or Herdr view does not itself grant authority.
- **Surfaces and adapters:** Herdr's layout may display portfolio, project, handoff and incident state, but it is a view of the service's records. Adapter lifecycle is a structured capability and status contract (start, resume, interrupt, retire, observation, error/unknown), checked before class admission; it does not create a universal framework. Voice becomes a recorded operator input through the same identity and command path, with transcription provenance and confirmation where the command requires it; voice never supplies approval. Explore a second adapter only as a controlled fixture after the first harness path and the ADR-015 Pi control gates, preserving D19's no-framework rule.
- **Evaluation and limits:** Store exact requested and resolved model/harness/provider versions, profile, tools, packet revision, resource policy and outcomes. Apply ADR-020's paired controls and complete episode accounting; configuration examples are not empirical rankings. Local fake-backend tests establish only protocol behavior. X-7, X-12, X-13, X-15, X-1 and Saga Phase B remain open. No live external effect or cross-provider data transfer follows from this decision.
- **Inherited relationship:** Amends Odin's D10/D19 single-project planning scope only to allow a portfolio coordinator above independent project owners; it does not amend Saga-owned interfaces. It refines D5–D8 and ADR-009/010/014/020 for packet, authority, surface and evaluation checks. It supersedes any Odin reading of D19 that every project must share one planning session; each project still has one accountable planning owner. This is not a replacement for Odin's service loop or Saga's worker boundary.

### ODIN-ADR-023 — Local continuity and attributed memory

- **Status:** local implementation defaults under the operator's request to
  implement the product plan with GPT-6-Sol subagents. These choices authorize
  synthetic development, not live credentials, provider disclosure or cutover.
- **Baseline:** integrate the reviewed source prototype as local commit
  `47e074e`, with the file inventory in
  [the integration receipt](provenance/PROTOTYPE-INTEGRATION.md).
  ADR-020/021/022 retain their local experimental scope. No producer contract
  or frozen extraction source changes.
- **Continuity:** build a deterministic resume and prepared-decision view
  during I1/I2 preparation. Canonical commitments and HumanRequest records
  remain authoritative; delivery and explicit acknowledgement are separate.
  Project scope, evidence revisions, current service policy and view
  dependencies are checked in code. An answer records a response and does
  not itself grant authority or close its commitment. Numeric page offsets
  require a matching revision token so a changing project cannot skip work.
  Canonical request history uses generic prompts and stable choice handles;
  prepared wording is a removable projection, revalidated before display.
- **Memory:** add attributed source revisions, statements, relationships,
  reader restrictions, processing coverage and freshness policy in the
  service's namespace. Service-stamped learning time is distinct from source
  observation/effective time. Reported success and proposals retain their
  status; accepted decision statements must reference the matching canonical
  decision. Unresolved competing claims remain visible. A correction,
  permission change or tombstone invalidates dependent views before rebuild.
  A local redaction receipt stays pending until SQLite cleanup confirms it;
  external destination confirmations remain independent. No model extractor,
  summary tree or external deletion executor is established by this work.
  Prepared questions depend conservatively on the project's memory revision;
  redaction invalidates them while retaining their commitments. Legacy history
  with full question text requires separate migration and stays pending.
- **Session boundary:** a local workstation journal reserves operation and
  session identity before dispatch, rechecks current service authority,
  preserves unknown starts/stops, and requires observation after reconnect.
  The Claude Agent SDK options/lifecycle binding is tested with protocol mocks
  only. The actual SDK, dedicated credential store, authenticated daemon,
  tool isolation and limits remain launch prerequisites. Native children and
  live transports stay disabled. Earlier production Codex integration is
  still a proposal; ADR-015 and I5 sequencing stand.
- **Evidence and improvement:** offline experiments keep semantic-memory,
  compactor and orchestration comparisons separate; inferred preferences or
  proposed procedure text never install authority. Local update proposals
  require scoped evidence, reviewed disposition and regression receipts.
- **Checks:** the product plan's PLAN-C01–PLAN-C12 map to local regression
  suites in the [execution status](PRODUCT-IMPLEMENTATION-STATUS.md).
  Existing full AC scenarios are not marked complete by component tests.
- **Inherited relationship:** operationalizes Odin's D6/D7/D18 and
  ADR-009/010/020/022. Adds an early local view alongside I1/I2 without
  superseding I4's human view/import or I5/I6's memory comparisons and real
  retrieval. The detailed compactor context, reuse, retention and live-data
  choices under X-10 remain open. X-1, X-7, X-11 production isolation,
  X-12/X-13/X-15, Saga Phase B and the handoff are not closed.

### ODIN-ADR-024 — Native Fable executive conversation pilot

Current scope note: ADR-026 supersedes this decision's restricted launch and
proposal-only improvement rules for native development profile version 3.
The following records the original versions 1 and 2 and the unchanged MCP
record semantics.

- **Date/status:** 2026-10-19; operator-authorized bounded implementation.
  The operator requested subagent implementation toward Fable in the Claude
  Code harness, communicating through existing remote channels such as
  Remote Control, followed by functionality testing and improvement loops.
  This authorizes the pilot and its preparation; it does not certify a
  working login, model entitlement, remote connection or production runtime.
- **Decision:** allow an Odin-prepared native interactive Claude Code
  session requesting `claude-fable-5-1`, with `--remote-control`, for
  executive conversation. The pilot uses the unmodified harness and its
  native conversation/resume behavior. The full SDK adapter and managed
  workstation lifecycle remain separate deliverables. The service remains
  the writer of Odin records; the model receives a scoped MCP bridge.
- **Operator and model authority:** the bridge binds `fable-executive` as a
  coordinator to an explicit project scope. It permits continuity and exact
  evidence reads, plus unverified progress reports and improvement proposals.
  It exposes no grants, approvals, verified completion, delegated execution,
  review/apply operations or native child dispatch. Remote Control carries
  human conversation within Claude Code; it is not an authenticated Odin
  operator command path. A model's paraphrase of an operator message remains
  model-reported content. Privileged commands keep the service's existing
  recorded operator path and required checks.
- **Launch boundary:** use a dedicated protected Odin Claude configuration
  and subscription login lineage, with one launch owner. Never copy or fall
  back to the development login. Restrict the launch to the explicit bridge
  and tools; isolate runtime state from the repository and sanitize inherited
  configuration. Show requested model and process state separately from
  observed model and Remote Control readiness. A CLI process starting does
  not prove that the requested model or remote connection is working. Login,
  workspace trust, pairing and any provider billing consent stay native
  operator interactions; the launcher must not synthesize acceptance.
- **Improvement:** initially collect attributed, unapplied reports/proposals
  and use them to choose bounded experiments. Such text is not installed as
  instructions or policy. Applying a correction requires the existing
  evidence/review/regression path; authority changes are excluded from that
  path. Automatic repository mutation or self-deployment is not part of
  this pilot.
- **Evidence and checks:** the [pilot runbook](EXECUTIVE-PILOT.md) separates
  synthetic launch/MCP checks from live acceptance. The local service still
  uses the fake Saga backend and labels its results accordingly. A live
  Fable conversation establishes only the observed conversation behavior,
  not Saga guarantees or full I2/I3 acceptance. Record remote message/reply,
  scope refusal, durable report readback, stop and resume independently.
- **Inherited relationship:** narrowly amends Odin-owned D7.2's SDK-only
  invocation and D7.7's interactive-only exclusion for this pilot. It
  refines ADR-009's eventual placement and ADR-022/023's previous synthetic
  scope by permitting this bounded live conversation. D7.1, D7.4–D7.6,
  D7.11–D7.12, D20.5's authoritative command rules, D24.6's credential
  separation, Saga's D1/D4/D23 boundaries and the ADR-015 second-adapter
  sequence stand. Remote Control selects D7.3's supported subscription
  alternative for this pilot; it does not change the general planning
  credential default. X-1, X-7, X-11 production isolation, X-12, X-13,
  X-15, Saga Phase B and the cross-repository handoff remain open.

### ODIN-ADR-025 — Executive repository evidence access

Current scope note: ADR-026 supersedes the native read-only boundary for
profile version 3. Committed snapshot evidence and its provenance semantics
remain available in every profile.

- **Date/status:** 2026-10-19; operator-authorized pilot extension. The
  operator supplied the active executive's diagnosis that its MCP-only
  manifest and empty memory prevented document/implementation reconciliation,
  and requested native read tools and/or repository ingestion. This decision
  authorizes those evidence paths, not automatic policy or code changes.
- **Native reads:** an explicit profile upgrade may expose Claude Code's
  `Read`, `Glob` and `Grep` for the Odin checkout. Preserve the native session
  identity, dedicated login and project binding; change the prepared profile
  only while its session and credential ownership locks are free. Use
  restricted mode, an explicit repository directory, no shell or edit tools,
  and read exclusions for credentials, runtime state and private paths.
  Claude's permission controls are not an OS sandbox. In particular, search
  exclusions are best effort and require live boundary checks; construction
  tests do not prove filesystem isolation. Current-file reads identify their
  path and are distinct from revision-pinned Odin evidence.
- **Committed evidence:** the operator may import a bounded selection of
  first-party repository documentation, code, schemas and tests from one
  explicit Git root's `HEAD`. Read Git objects, not untracked files or working
  tree edits. Exclude hidden/private paths, symlinks, submodules, frozen
  history, pinned peer contracts and dated research. Keep the exact commit,
  path, chunk boundaries and content digest with the source. The local service
  remains the sole writer, validates scoped operator commands and exposes
  these sources only to the bound executive and local operator.
- **Discovery and freshness:** publish a bounded catalog with exact source
  IDs and revisions, visible through the existing memory tools. Preserve
  partial import status until all ordered batches finish. Replaying the same
  snapshot is idempotent. A completed snapshot describes selected committed
  files at capture time; it neither monitors later changes nor proves that
  code behavior matches the documents. No statements, approvals or verified
  results are inferred from repository text.
- **Persistence and improvement:** clarify that the compatibility label
  `fake-backend evidence` refers to the fake Saga execution backend. Local
  memory and reports are persisted in SQLite; reports stay unverified and
  proposals unapplied. Repository access does not turn model-relayed text into
  an operator command, authorize delegation or install a proposed procedure.
- **Checks:** profile/lock/session identity regressions, import selection and
  scope checks, exact revision reads, replay and restart persistence checks
  accompany this extension. The [pilot runbook](EXECUTIVE-PILOT.md) keeps
  synthetic evidence separate from native tool visibility and actual read
  observations. This adds no completed full acceptance scenario.
- **Inherited relationship:** refines ADR-024's explicit-tool launch boundary
  and ADR-023's synthetic-memory scope for this operator-selected repository
  evidence. It does not supersede D7's service authority, D24's credential
  separation, I4's task migration, I5/I6's memory/retrieval work or Saga's
  D1/D4/D23 boundaries. Production isolation, X-12/X-13/X-15, live Saga and
  the cross-repository handoff remain open.

### ODIN-ADR-026 — Native executive development access

- **Date/status:** 2026-10-19; operator-authorized implementation. After the
  initial executive could not investigate its filesystem, the operator
  explicitly requested removal of the current runtime's imposed restrictions
  and limitations so that it can self-improve. That instruction authorizes
  this development profile; no additional approval or proposal-only stage is
  introduced by this decision.
- **Decision:** add native profile version 3, selected with
  `executive-enable-development`. Launch the unmodified Claude Code harness
  with its normal native tool set and system prompt, `bypassPermissions`, the
  actual Odin checkout as cwd, the real HOME and inherited operator
  environment. Append brief Odin context instead of replacing the harness
  prompt. Do not apply Odin tool/path allowlists, restricted-directory mode,
  MCP-only configuration, environment sanitization or disabling of hooks,
  plugins, skills, native memory, discovery, browser tools or native agents.
  Do not load the former generated restriction settings or require an Odin
  service socket before launching native development. An unavailable service
  makes its MCP operations unavailable without blocking the native tools.
  Available integrations still depend on what the harness and operator
  environment provide; configuring access does not install missing tools.
- **Development authority:** the executive may inspect files, edit code and
  configuration, run commands and tests, and use native agents to perform
  operator-directed development and self-improvement. These actions are
  ordinary native development work and do not wait for fake Saga, a proposal
  disposition or the unfinished managed worker path. Instructions and
  approval choices supplied by the operator still apply. The profile removes
  Odin's runtime restrictions; it is not OS isolation or a claim of authority
  over unrelated producer infrastructure.
- **Continuity and activation:** retain the dedicated `CLAUDE_CONFIG_DIR`,
  credential lineage, project binding, native session UUID and local records.
  Selection writes a validated pending profile without interrupting a
  running session or launching a second owner of its credentials. An
  explicit exit and `executive-start --resume-session` normally activates it
  as the next owned runtime operation under the existing ownership locks.
  Status distinguishes current configuration
  from pending development access; tests cover that staged transition. A retained dedicated login is continuity configuration, not an
  assertion that the unrestricted process cannot reach other local files.
- **Odin records and Saga:** preserve the additional scoped Odin MCP bridge.
  Its model reports remain unverified and its proposals remain unapplied
  records; native edits do not retroactively change their meaning or become
  Saga-verified results. The local SQLite store persists independently of
  the fake Saga execution backend. Native development work bypasses that
  backend, not Saga's own API admission or ledger. Saga-owned interfaces,
  identities, approvals, hosts, stores and guarantees are unchanged. The
  full managed SDK/daemon/worker path and peer integration are not delivered
  by this exception.
- **Inherited relationship:** supersedes ADR-024's restricted launch and
  proposal-only improvement rules, ADR-025's native read-only boundary, and
  ADR-022/023's prohibition on native children for this development profile.
  Amends Odin-owned D7.2/D7.7 invocation/interactive restrictions and
  D19.7/D23.1–D23.3 routing rules so native development execution does not
  require an Odin-managed backend. The I/O contract §6–§7 planner-only tool,
  filesystem and environment isolation rules and §11 managed-child gates do
  not apply to this profile. D24.3's Odin process-isolation requirement is
  likewise waived here; keeping secrets out of committed source, prompts
  and reports remains required. Dedicated login identity and single refresh
  ownership under D24.4a/D24.6 are retained. None of these changes amends
  Saga-owned interfaces or grants their guarantees to native development.
- **Checks and evidence:** launch/schema regressions check normal native
  tools, permission mode, real cwd/HOME, inherited environment, absence of
  the former disable flags, identity preservation and deferred activation.
  The [pilot guide](EXECUTIVE-PILOT.md) requires observed native tool use
  after resume before reporting it as live. OS permissions, harness/provider
  policy, account limits and installed capabilities remain actual properties
  of the environment, not restrictions Odin can remove. Production gates
  and the cross-repository handoff remain open.

### ODIN-ADR-027 — Executive delegation sessions on the local backend

- **Date/status:** 2026-10-20; operator-authorized implementation. The
  operator asked the version 3 executive to prioritize the missing
  executive-to-project delegation path: an Odin tool that creates or resumes
  an accountable project orchestration session, assigns work, inspects
  progress, sends follow-ups and collects results, demonstrated with actual
  sessions, persistence and recovery, with Claude Code and Codex support
  reported separately.
- **Decision:** add six scoped bridge tools (`odin_delegation_session`,
  `odin_delegation_assign`, `odin_delegation_followup`,
  `odin_delegation_status`, `odin_delegation_result`,
  `odin_delegation_close`) and the matching recorded gateway actions. A
  session is a canonical `PlanningSession` on the D23.3 local backend with a
  `SessionBinding` and host `Environment` record; at most one is active per
  project and it becomes the project's planning owner. Assigning work creates
  an open `Commitment` with acceptance criteria owned by that session and a
  `backend: local` `Assignment`. Each assignment or follow-up is one
  non-interactive harness turn (`claude -p --session-id/--resume` or
  `codex exec`/`codex exec resume`) run by a detached runner that writes a
  spool the service ingests; the service stays the only writer of Odin
  records. Enablement requires an explicit operator configuration file
  (`delegation-configure`) naming the harness binaries, the worker credential
  configuration and allowed workspace roots; without it every delegation tool
  refuses.
- **Semantics:** a returned turn is an unverified worker report. Only
  `odin_delegation_close` with evidence for every criterion completes the
  assignment and closes the commitment, recorded as executive-attributed
  acceptance, never as Saga verification. Cancellation abandons the
  commitment. Budget and iteration limits are passed as harness options where
  the harness offers them (Claude Code) and must be explicitly allowed as
  unenforced otherwise (Codex); Odin records requested limits and reported
  usage but enforces no ceiling. Stop signals the running turn and retires the
  session with the remote outcome marked unconfirmed until the runner reports.
  A service restart retires an active session; an explicit resume starts a
  new incarnation and binding, and a runner that exits without a result is
  recorded as `lost`, never retried. A replacement session adopts open
  commitments left by a retired one with a new ownership generation.
- **Guidance to the executive:** use native subagents for quick bounded work
  whose result is integrated in the same conversation; use delegation
  sessions for work that must persist as a project commitment, run detached
  in a resumable harness session, survive the conversation or a service
  restart, or be collected and accepted later.
- **Inherited relationship:** extends ADR-026's development exemption to the
  bridge: it amends ADR-024's rule that the scoped bridge exposes no
  delegated execution, for this local-backend path only. It applies D23.3
  (local backend with stated missing guarantees), D7.11 (commitments carry
  owner and assignments) and D19.4's capability statement per adapter. It does
  not deliver the managed SDK/daemon session host (ADR-009, I2), service-
  managed child dispatch (X-15), the ADR-015 Pi control or the I5 second
  production adapter; the Codex path here is a local non-interactive worker
  adapter, not that second adapter. Worker credentials follow the configured
  Claude configuration directory and Codex home. Refresh ownership is
  enforced with the executive runtime's own `.odin-lineage.lock` lease
  (D24.4a, one refresher per lineage): the runner must hold it for the
  worker's lineage while a harness runs, a busy lease refuses the turn
  under the default `exclusive` policy, and a session on the executive's
  own login or the operator's `~/.codex` login is refused unless the
  operator configures `lineage_policy: shared_accepted`; every turn result
  records the lease outcome and a content-free credential-file fingerprint
  before and after the run (2026-10-20 amendment). Sharing the executive's
  dedicated login lineage with worker processes under `shared_accepted` is
  an interim operator choice under open X-12, not a resolution of it.
  Saga-owned interfaces, approvals and guarantees are unchanged.
- **Checks and evidence:** `tests/test_delegation.py` exercises the cycle
  with synthetic harness binaries and real detached runners: open, assign,
  launch, return, follow-up resume, restart, incarnation, stop/interrupt,
  lost runner, failure visibility, unenforced-limit refusal, scope and
  replay. Live receipts for actual Claude Code and Codex sessions belong in
  the operator's private evidence directory, labelled as local-backend
  evidence.

### ODIN-ADR-028 — Independent development evaluator and feedback loop

- **Date/status:** 2026-10-20; operator-authorized implementation. The
  operator requested an independent evaluator that designs the next tests,
  assigns them to the existing interactive Fable executive, receives its
  final response and evidence automatically, then chooses the next stage.
  The executive may use its authorized native tools, subagents and code
  changes under ADR-026. The objective is an autonomous development loop
  without manual copying between conversations, not only a code review.
- **Roles:** call the judgment role the **development evaluator** and the
  deterministic module the **development loop controller**. The evaluator
  assesses functionality, operator experience, evidence quality, reliability
  and development progress, then chooses a bounded next test, completion or
  a reason to pause. It receives the configured evidence pack separately
  from the executive's working conversation. Independence means a distinct
  evaluation invocation with its own inputs and recorded identity; it does
  not imply independent credential or OS isolation. It is not Mimir and
  cannot replace required reviewer positions or provide Saga approval.
- **Transport:** add an explicitly enabled custom MCP channel to the
  executive bridge and a native Stop completion hook. Send each round to
  the existing native session, retaining its session ID, Remote Control and
  dedicated Claude login. Activate the added channel/hook on one explicit
  native restart/resume. Do not launch another Claude process on that
  credential lineage to drive the loop. Channel connection, permitted
  notification delivery, executive acknowledgement and completion capture
  are separate observations. Tool visibility alone proves none of the latter.
  Unchanged channel-inbox polling is an authenticated, project/session-scoped
  transport read and creates no durable command or receipt per poll.
  Stage creation, claims, completion and every controller transition remain
  recorded; this exception does not turn a notification into authority.
- **Control and persistence:** the controller validates the fixed loop
  configuration and records scope, session, round, delivery and evaluation
  identities. It owns durable state transitions, duplicate detection,
  stale-result refusal, pause/stop and finite round bounds. A
  model chooses the next test within those bounds; it does not alter them.
  A lost delivery, interrupted turn, service restart or incomplete completion
  capture must retain an explicit pending/unknown outcome until reconciled.
  Never interpret process exit, a Stop event, or the word "done" as proof
  that a test passed. Automatic retries retain the same operation identity;
  uncertain work is not silently replaced with a fresh round.
  A completed evaluator `needs_operator` decision accepts an operator-only,
  revision-checked response once executive work is inactive and round budget
  remains. The controller retains that response with the original evidence
  in a fresh evaluator job at the same round; completed records, configured
  bounds and progress counters remain unchanged. This continuation is not a
  reset, a delivery reconciliation or authority to expand the objective.
  Core, gateway and CLI restart/retry tests enforce these conditions.
- **Evidence return:** the completion path returns the main executive's
  final response and bounded, attributed evidence references for the active
  round. It must distinguish an evaluator's task from unrelated operator
  conversation, reject another session or stale round, and preserve missing
  or unavailable evidence. Native subagent/background work is not complete
  merely because the main agent stopped responding. The evaluator receives
  the actual supported evidence pack, not an unlabelled claim that all
  transcripts, artifacts or tests were independently verified. Runtime
  conversations and artifacts remain outside committed source.
- **Authority and development:** the operator's configured objective grants
  the existing native development scope; the evaluator can select actions
  inside it without a new manual approval on every round. Its output cannot
  enlarge that scope, grant credentials, change Saga admission, suppress
  operator controls, or satisfy a required review. Native edits and test
  execution retain ADR-026's authority and missing isolation guarantees.
  Ordinary reports, canonical commitments and Saga ledger results retain
  their existing meanings. The controller's round bound limits automated
  continuation, not the cost or native tool usage of a single turn.
  The initial controller also stops continuation after the configured
  number of consecutive repeated evidence-reference sets; this is a
  stall signal, not a semantic proof of progress or a wall-clock deadline.
- **Activation and checks:** opt in with schema-validated local configuration
  and explicit transport activation. Invalid output, unavailable transport,
  absent evidence or an exhausted bound must be visible without inventing
  success. The [development-loop runbook](DEVELOPMENT-LOOP.md) states the
  local tests and live acceptance separately. A passing synthetic channel,
  hook or evaluator binary is not proof of a live unattended loop. Actual
  acceptance requires at least two automatically connected rounds in the
  intended session, real evidence return, and tested pause/stop/recovery.
- **Inherited relationship:** extends ADR-026's native development scope and
  D7.7's interactive transport exception. Amends Odin-owned D9.3 and D9.4
  only to permit this explicitly requested development evaluator and its
  direct opt-in activation; ordinary service-event evaluators retain their
  registered hooks and evaluation/activation rules. D9.1's non-authority,
  D9.5's direct operator/control routing, D6's at-least-once reconciliation,
  D7.11's commitment truth and D24's retained refresh ownership stand. No
  producer contract, Saga guarantee, Mimir review requirement, managed
  session-host gate, X-12/X-15 disposition or handoff is closed.

### ODIN-ADR-029 — Structured execution receipts as attributed local evidence

- **Date/status:** 2026-10-20; operator-authorized implementation under the
  ADR-028 development loop's first implementation objective. The evaluator
  observed that executive evidence was prose plus an unrestricted JSON
  object, and that a merge-commit subject naming the wrong branch had been
  reported as branch identity.
- **Decision:** Odin records command execution evidence as a versioned,
  schema-validated **execution receipt** (`execution-receipt` schema,
  `odin.execution_receipt`, `receipt-run`/`receipt-validate` commands).
  The collector executes the supplied command itself and derives every
  field from repository and process observations: repository root and cwd,
  actual branch or explicit detached HEAD, commit, staged/unstaged/untracked
  identity digests observed before and after the run, argv, resolved
  executable and interpreter, timestamps, exit status or explicit
  uncertainty, retained output artifacts with byte digests, and the
  collector's own source digest and Odin revision. Commit subjects are
  recorded as text and explicitly marked as not branch evidence.
- **Evidence workflow:** development-loop evidence may reference receipts
  with compact typed references and structured claims. The controller
  validates them deterministically at ready and at completion capture and
  records `validated`, `validated_unobserved`, `uncertain`, `mismatched`,
  `missing`, `invalid` or `legacy_no_receipt` with the stage and in the
  evaluator packet. Only `validated` is a passing check (and
  `commands_succeeded` is reported separately from validity); failures and
  uncertainty are recorded, never raised as success, and receipt-less
  evidence is labelled legacy rather than rejected. The evaluator is instructed to read retained receipts itself,
  compare executive prose with observed fields and recompute artifact
  digests; a JSON success flag is not evidence.
- **Trust limits:** a receipt is attributed local execution evidence. The
  collector and the command run as the same user; observations are
  point-in-time; untracked coverage is bounded and ignored files are
  excluded; environment and credentials are never recorded, while argv and
  output are retained verbatim in private storage outside the checkout.
  A receipt is self-attested: the executive principal could write one by
  hand, and validation establishes consistency, binding and timing, not
  authorship (a controller-side registry is the recorded follow-up). A valid
  receipt of a failing command is evidence of failure; `commands_succeeded`
  is reported separately from validity. Receipts confer no Saga
  verification, canonical acceptance, isolation or required-review outcome
  (D7.11, D19.4, ADR-026/028 unchanged).
- **Checks:** `tests/test_execution_receipt.py` covers success, failure,
  timeout, the wrong-branch merge subject, detached HEAD, dirty-tree
  identity and privacy, modification during the run, tampered/missing
  artifacts and edited receipts, wrong revision/worktree/stage attribution,
  unobserved repositories, environment exclusion, reference validation
  outcomes and the ready/capture path into the evaluator packet; the
  service/bridge integration test carries a receipted round, run inside a
  synthetic git repository, through the real channel. An independent review
  of the first revision (2026-10-20) found twelve issues, including an
  unbounded problem string that could raise out of `ready`, timeout leaving
  grandchildren writing after hashing, rename and non-ASCII path parsing,
  and the self-attestation gap; all but the registry were resolved in the
  follow-up commit with tests. The evaluator's second-round assessment
  found three further material gaps (contradictory fields accepted, a failed
  post-run observation summarised as clean, blocking and unbounded file
  inspection); the corrective commit adds recomputed consistency checks, the
  `uncertain` outcome for a single available observation, and bounded
  non-blocking inspection bound to the parsed bytes. A second independent
  review of that correction found that list-derived digests and coverage
  were still not recomputed and that a timed-out run could carry an exit
  status; the follow-up recomputes every derived field, treats those as
  contradictions, reports no observed field for an invalid receipt and
  bounds the validation summaries in the schemas. Live receipts for
  actual stages are retained privately and are themselves subject to the
  evaluator's independent inspection.
  A clock-reversal regression preserves completed command evidence with
  original timestamps, a null duration and explicit uncertainty. Reversed
  chronology remains invalid and observed summary fields remain redacted;
  the collector's CLI status still reports command success or failure.
  Regression tests cover successful and failing commands across a backward
  clock step and refusal of contradictory null-duration claims.

### ODIN-ADR-030 — Durable loop notices and conservative attention

- **Date/status:** 2026-10-21; operator-authorized implementation under the
  ADR-028 development loop's second objective (operator visibility and
  stalled-work handling).
- **Decision:** the development loop controller writes a durable **notice**
  in the same transaction as every completion, intervention, failure or stop
  transition, and one `stalled` notice per attention observation. Notices
  are scoped to project and native session, correlated to loop, stage, job
  and transition, carry a bounded summary, the evaluator's assessment and
  what needs attention, and are offered through the existing executive
  channel as events distinct from assignments (`meta.kind`). They remain
  deliverable after the loop ends. Delivery is at least once; the executive
  acknowledges a notice with `odin_loop_ack`, which is recorded as
  model-attributed and grants no authority. Notices never carry a completion
  footer and never ask for a stage to be claimed or executed.
- **Attention:** per-loop deadlines (offer, claim, ready, evaluator), disabled
  unless configured by the operator, bound each waiting state. Exceeding one
  records an attention observation and a `stalled` notice without changing
  the loop's status or revision: no redispatch, new round, process
  termination or session replacement follows from elapsed time, pending work
  stays claimable, and any real transition clears the observation. Paused,
  unknown, intervention-bound and terminal loops are not timed; a backward
  clock raises no attention; repeated checks write nothing new.
- **Boundaries:** controller pause and stop remain controller transitions and
  make no claim about running native tools or delegated jobs; operator
  controls stay on the operator command path (D9.5); model text or
  acknowledgement never becomes operator approval; authenticated routing of
  operator decisions from a chat surface remains future work. Existing loop
  records without deadline fields stay valid and untimed.
- **Checks:** `tests/test_development_notices.py` (controller and gateway,
  controlled clock), transport tests for notice events, replay and
  acknowledgement, and the service/bridge integration scenario (stalled
  notice from the live tick, completion and stop notices, reconnect replay,
  wrong-session refusal, unrelated replies not captured, operator deadline
  control). These are synthetic; live acceptance requires an observed
  activation of the service and bridge.

## 5. Issues raised by the extraction

Each issue stays open unless its entry records the evidence that
resolved it. X-1, X-2, X-5, X-6, X-8, X-10, X-11, X-12, X-13, X-14 and X-15 are open. X-3, X-4 and X-9 are
resolved as recorded readings of existing decisions; X-7 is resolved
only as far as fail-closed handling. Every resolution is subject to the
re-review and to the operator.

- **X-1 — Phase C start versus fake-backend increments.** The Saga
  developer instructions say "Do not start C before B's API and minimum
  enforcement exist". The blueprint (§7), carried by D14.4, allows I0–I2
  against a fake Saga backend, and the I/O contract (§13) places I0–I1
  beside Phase B and I2–I3 in Phase C. **Open: producer reconciliation
  pending.** Odin's interpretation under D15 (review finding B2): I0, I1 and I2 are
  non-production work against fixtures in I0 and a fake backend in
  I1–I2; I3, any live
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
  open). B-12 also identifies a worker-event delivery gap against EV-4:
  status and evidence reads do not promise cursor notifications for
  journals, per-iteration status, plateau signals or alerts. The check
  compares documents only and must be repeated when
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

- **X-11 — Substrate store topology and failure domains.** ODIN-ADR-006
  fixes the namespace and single-writer rules but not the physical
  layout: one SQLite file with namespaces or one per namespace, how
  single-writer is enforced by process ownership, how the execution-ledger
  mirror is fed and what happens when the backend's cursor and the mirror
  disagree, and which failures take which namespaces down. Decide before
  I1; the fake-backend scenarios must exercise the mirror's read-only
  property.
- **X-12 — Credential lineage for workstation sessions.** ODIN-ADR-009
  needs a model credential on the operator's machine for Odin's local
  sessions, next to the development login that AGENTS.md §6 and D24.6 keep
  separate. Decide the lineage (a second subscription login, or an API
  key), its protected store, its single refresher, and how the service
  references it (D24.3) before I2's workstation work.
- **X-13 — Data policy for voice and for a second review provider.**
  Voice transcripts are operator content, so under D9.5 transcription
  stays with the local provider unless the operator decides otherwise
  (L-VT-2); ODIN-ADR-013 sends evidence packs, which can carry
  specification content, to a second model family. Decide both before
  voice leaves backlog and before the second position runs on a
  non-Anthropic provider.
- **X-14 — Saga-side decisions the consolidation requires.** The
  consolidation plan's conditional parts touch clauses Saga owns and
  cannot be recorded here: the execution backend sharing a repository and
  release train with Odin as a separate process with its own store
  (D14.1, D14.7, D1.2); workers reporting to the backend's own intake,
  replacing MQTT for Saga's use (D3.3, D13.4a, D15.B, contract MQ-1);
  Bragi and Eir transferring to Odin session and assignment classes with
  Eir's operator-invoked path outside both failure domains (D11, D12.1,
  D17.4b); the repository names and prefix (D13.1); and the D14 handoff.
  The operator records these in Saga's repository; Saga publishes a new
  contract version; Odin repins it and rechecks Appendix B (X-3). Only
  then are ODIN-ADR-016 to 019 recorded. Until then the plan's
  description of a shared repository is a proposal and D10.6, D14.1 and
  D14.7 stand as carried.

- **X-15 — Shared limits and lifecycle of harness subagents.** D8's
  review caps, I/O contract §5's session caps and AC-23 require enforcement, but the
  adapter contract does not yet define how concurrent native children
  share a cap. Before I2 enables child dispatch, specify Odin-side
  admission/reservations, attribution without double counting parent
  totals, in-flight usage, missing telemetry, release/reconciliation after
  crash, child count/depth limits and stop propagation. A next-request
  spend check or a per-child turn limit is not proof of an aggregate hard
  dollar ceiling. For each advertised limit, identify its enforcing
  component and adapter evidence; refuse a session class whose required
  limit cannot be enforced. Define how an unconfirmed child stop remains
  visible and prevents unsafe redispatch (AC-10/AC-37). Proposed AC-44
  supplies adversarial cases. This is Odin's local harness boundary;
  Saga-owned worker limits and its pinned API are unchanged. No mechanism
  or numerical limit is settled by this issue.

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
| B7 | `shell` can expose credentials to Odin's turns | Corrected as a design requirement: isolated planner workspace, no credential reachable, results redacted before logging, fail closed (I/O contract §7). Not implemented; check due in I1/I2 (the isolation check moved with the profile schemas under ODIN-ADR-008) |
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
