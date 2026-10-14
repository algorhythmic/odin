# Saga and Odin — decision record

> **Date:** 2026-10-14 (v2, same day). **Author:** dev Claude at the
> operator's direction, after the harness landscape review
> ([`design/HARNESS-LANDSCAPE-2026-10.md`](design/HARNESS-LANDSCAPE-2026-10.md)),
> the Odin I/O contract ([`design/ODIN-IO-CONTRACT.md`](design/ODIN-IO-CONTRACT.md)),
> the reviews of the operator's standalone repos
> ([`design/harness-research-2026-10/`](design/harness-research-2026-10/README.md)),
> the operator's architecture proposal (§1) and three rounds of critical
> feedback on positioning, Mimir and the decision-model tool (§2).
>
> **Authority:** where this record conflicts with `saga-spec.md`,
> `ARCHITECTURE.md`, `GENERALIZATION.md`, the personas, or any design
> document, this record wins until the operator changes it. Each
> decision carries a status: **locked** (build against it), **default**
> (locked unless the operator objects), **hypothesis** (build the first
> version against it, but it must pass the stated evaluation to stay),
> or **open** (operator must choose).

## 0. The two directives, and the answer

1. Clean up naming, design and development direction for Saga, make
   the hard architecture and use-case decisions against the tool
   ecosystem and Odin's direction, and consolidate the documentation.
2. Lock the design for Odin's extraction, the decision-model tool, the
   OptChat (UniiChat) memory implementation, and whether the operator's
   standalone tools roll into Odin or stay separate.

**Odin is a personal agent for running long-term technical projects
under explicitly delegated authority, built as a supervisory layer over
Claude Code's execution harness; Saga is the execution service that
makes that delegation durable, bounded and verifiable; the standalone
tools stay separate and plug in through Odin's tools; Norse names are
kept only for agents; UniiChat's memory ideas are the first
implementation, adapted to the harness boundary, not Odin's identity;
Mimir reviews where mistakes multiply and is measured; System One
models judge, never authorize.**

## 1. Evaluation of the architecture proposal

The proposal argued: Odin is a harness whose primary agent is an
orchestrator; Saga is a governed execution runtime that accepts external
orchestrators; Odin reaches Saga only through tools backed by an
independently running service; mandatory enforcement moves to Saga's
execution boundary; Saga's ledger is separate from Odin's chat log;
completion needs distinct states; side effects need destination
deduplication; Eir runs three loops with an out-of-band path; the newer
repos are reused; Saga's launcher is renamed.

**Adopted:** all of the above (D1 to D6, D11, D13), for the reasons
recorded with each decision. The two that corrected the earlier
contract are enforcement location (the gate belongs outside the agent's
trust boundary, Saga's own founding principle) and the ledger split
(approvals and completion cannot depend on a compressed narrative).

**Modified or rejected:** standalone heimdall as the authority for
"accepted task direction" (rejected for now: desktop tool, unreleased,
CI red, explicitly rejects Saga coupling; D17 gives that role to
delegation records inside Saga); consolidating Bragi's destination with
muninn (deferred until muninn is active); packaging Saga primarily as an
MCP server (the API is a local service with a client library; MCP is an
optional adapter for other clients).

## 2. Evaluation of the critical feedback

Three pieces of feedback followed the first version of this record.
What they changed:

**Positioning and architecture.** Adopted: an explicit product promise
and audience (D0); an ongoing responsibility as a first-class, versioned
object that outlives both the chat and the runs (D17); the distinction
between run admission and action authority, with an authenticated
reviewer identity so Odin cannot manufacture its own approval (D2);
minimum enforcement before Odin's first live project rather than after
(D15); precise stop semantics (D2); memory as a stable interface with a
replaceable algorithm, durable requirements, a retention policy, and an
evaluation against a simpler baseline (D7); a comparative evaluation of
Odin plus Saga against an existing agent plus Saga, and a sustained
responsibility as the first demonstration (D18); Eir's loop completed
through regression check, measured outcome and rollback (D11); accurate
deployment language ("locally operated state and execution with hosted
inference", not "self-hosted"). Also adopted: the landscape is read as
three separate questions (components to build on, products competing
for the operator's attention, systems that can become Saga clients),
recorded in §4. Qualified: the named competing products (Dots, Muse,
Grok Bot, Instinct) were not verified here; the argument that
persistence, memory, proactivity, parallel workers, chat access,
learning and a separate reviewer are no longer distinguishing on their
own stands regardless.

**Mimir.** Adopted: review where mistakes multiply, not every
project-shaping decision; mechanical checks before model review
(byte-identical contracts, dependency cycles, approval hashes); the
reviewer gets original evidence, and "blind" means no exposure to
Odin's reasoning, not absence of facts; bounded, actionable findings
with an `INSUFFICIENT_EVIDENCE` outcome; one review and at most one
re-review before escalation; no perpetual reviewer memory (prior
findings are attached deterministically, which replaces the earlier
"precedent view" mode); the reviewer model chosen per review type with
"cheap" earned by evaluation; a hard aggregate cap on review spend and
on interrupt-class turns; measurement of whether criticism helped (D8).
Embedding Mimir in Odin's harness is an operational choice, not a
security boundary, and is recorded as such.

**Design philosophy (runtime and the supervisory layer).** Adopted,
and it reverses the first version's runtime choice: Odin builds on
Claude Code's execution harness through supported interfaces (the
Agent SDK) rather than on a custom Messages API loop; Odin owns what
spans sessions (commitments, memory, event intake, wake policy, session
lifecycle, delegation, review coordination) and Claude Code owns
execution within a session; UniiChat's memory ideas are kept and its
exact inference layout is not promised; a custom runtime is considered
only when measured requirements cannot be met through the harness
(D7). The reasons: the case for extracting Odin and the case for giving
it a new execution harness are separate decisions and the first version
coupled them; improvements in Claude Code's harness then accrue to Odin
while development concentrates on the differentiating layer; the
original Saga already followed this pattern; and it mirrors the field
evidence that the orchestrator's outer loop should be ordinary code.
Also adopted: Odin as a "bring your own agent harness" supervisory
layer with explicit per-adapter capability matrices, a durable model of
the work (commitments) kept separate from memory, a restrained initial
product, and a second harness adapter early enough to test the
boundary (D19). Qualified: the SDK's compatibility with specific
interactive-only behaviours (channels, plugin monitors, teammates) is
not assumed; Odin's service supplies its own Telegram adapter and event
intake, so none of those are required.

**Topology, operator interfaces and desktop capability.** Adopted:
one Odin service with several project-scoped planning sessions and
many worker sessions, not one conversation for everything and not a
daemon per worker; one planning owner per project, more only for
separable responsibilities or a measured bottleneck, with explicit
ownership rules; two operator interfaces (a terminal workspace for
active work, Telegram for asynchronous interaction) entering one
recorded command path with approvals bound to proposals regardless of
channel and stop available as a direct service operation; "adopt into
supervision" and "take control" as explicit operations; per-adapter
inspection and takeover capabilities tested rather than assumed (D20).
Also adopted, revising D10: wayland-computer-use becomes an optional,
harness-independent desktop capability for a dedicated computer-use
worker under a delegation that names desktop authority, coordinated by
an exclusive seat lease enforced at a broker, with decision models
limited to bounded textual evidence inside a reusable workflow
component (D21). Qualified: Herdr's agent-automation API was not
reviewed here, and its "done" and "wait" semantics are taken from the
reviewer; standalone heimdall remains outside authority and becomes at
most an optional human-facing continuity surface with Odin's commitment
record as the one authoritative record.

**Demonstration workflow, routing and preservation.** Adopted: the
seven-step end-to-end workflow and five failure scenarios as the shape
of the D18 demonstration; the distinction between passing through
Odin's *service* and passing through Odin's *model*, with an explicit
handling table in which most events need no inference (D20); workers'
structured requests for operator input delivered directly to the
operator's queue with their request id and options, the planner joining
only when the answer changes the plan (D3, D20); the message record
separated from the planning context, so routine worker output stays
inspectable in Saga's ledger and the archive without entering the
summary tree (contract §1); an archived-conversation retrieval scope
through skald with original record identities, while braid still never
indexes Odin's active chat (contract §5); an explicit ownership bridge
for the conflict between Odin's commitments and the skald–heimdall
amendment's assignment of accepted task state (D20); a selected project
package, not a blanket sync, as the preservation unit through
dotprivate, with "copied", "committed" and "confirmed on the remote"
distinguished (D22); and execution backends made explicit, with Saga
the governed default and a local session backend allowed only for work
without external effects (D23). Qualified: dotprivate's selected-files
contract and skald's retrieval are still proposed or unfinished in
their repos, so both integrations are scheduled, not assumed.

**Authentication and billing.** Adopted: runtime choice, authentication
method and billing policy are explicit per-adapter configuration,
independent of Odin's supervisory features (D24). The API-key-only
wording for Odin's sessions was a deployment preference presented as an
architectural requirement; Anthropic's 2026-10-07 guidance says the
Agent SDK and `claude -p` still draw on subscription limits when logged
in, and the included credits are a separate API-key path. "Sign in once,
supervise many sessions" remains available; the promise is
"subscription-first, with bounded, explicitly configured API spending",
not "no API costs". Also adopted: refresh ownership as a stated part of
each adapter's launch configuration, replacing "mount one writable
credential directory everywhere" as the default; quota behaviour
(queue or pause at the account's limit, paid API fallback only when
configured); the existing separation between the operator's
development login and the managed agents' login; Codex's documented
auth-cache transfer as the equivalent provisioning path for Codex
workers. Qualified: the April script comments claiming that `claude -p`
or the OAuth environment variable force API billing stay as historical
findings until the re-test, and are not edited before it.

**Decision models.** Adopted: an advisory `decide` tool plus
harness-owned, versioned evaluators with fixed configuration;
`install_decider` renamed `propose_decider`, binding the full
configuration (model version, questions, input projection, thresholds,
fallback, permitted effects) with replay and shadow evaluation before
activation and revalidation on any change; a small registry of
supported hook locations rather than arbitrary hooks; routine entries
get a maximum deferral; operator interrupts, corrections, revocations
and critical lifecycle events bypass learned routing; sensitivity
follows content through transformations; confidence is not measured
correctness; the first experiment is a journal-attention evaluator in
shadow mode against the existing triage path (D9).

## 3. Decisions

### D0 — Product scope and promise (locked)

> **Odin** is a personal agent for running long-term technical
> projects. It maintains context across interruptions, coordinates
> specialist workers, and brings back evidence and decisions within
> authority you explicitly delegate.

> **Saga** executes delegated agent work with durable state, enforced
> permissions, resource limits and recorded outcomes.

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

### D1 — Products and boundary (locked)

| Product | Repo | What it is | What it owns |
|---|---|---|---|
| **Odin** | `odin` | A supervisory layer over an agent harness: an **Odin service** (commitments, memory, queued events, wake policy, budgets, session records, scheduler, outbox, adapters) plus a **harness integration package** (the tools, hooks, skills and instructions that make a Claude Code session operate as Odin). Hosts Odin, Mimir review sessions and one-shot subagents. | Persistent commitments and project memory; event intake and attention; session lifecycle (start, resume, retire, reconstruct); delegation coordination and reconciliation of results; selective review coordination; outcome verification against evidence; proposing changes to its own working methods. Reasoning and tool execution *within* a session belong to the harness. |
| **Saga** | `saga` | A governed execution service: starts workers in isolated environments, keeps the run ledger and the delegation records, enforces admission and action authority, limits and approvals, survives failures, exposes an API any orchestrator can use. | Runs, workers, images and hooks, policy, events, delegation records, Bragi, Eir. |

Odin reaches Saga only through tools backed by the independently
running Saga service. A lost connection does not lose a run; restarting
Odin does not restart workers; a retried submission does not launch a
duplicate.

### D2 — Enforcement lives in Saga, as two guarantees (locked)

**Run admission.** Which workload may start, with which resources and
limits. Saga validates for every client: the launch configuration
against schema and allowlists; the exact approved artifacts by hash
(PRD, launch configuration, the Mimir verdict bound to the request id
where review is required, the operator authorization bound to the hash
of what was shown); the delegation record's limits (D17): concurrent
runs, container TTL, budget, operator-presence gate.

**Action authority.** Which external changes an admitted workload may
make. For the first release: repository-scoped credentials (push to the
stream branch of the named repo only), no other secrets unless the
delegation names them, network egress as the firewall allows. Any
future connector that can act outside the container (email, purchases,
calendar writes, deployments, desktop input under D21) requires its own
enforcement boundary before it is offered to any agent; admission never
implies authority.

**Reviewer identity.** Verdicts are written to Saga's ledger only under
Mimir's identity key, which the harness holds and never exposes to
Odin's turns; Saga verifies the key. Mimir reviews quality and
reasoning; Saga enforces authority. Sharing a process is an
operational convenience, not a security boundary; when the operator
wants a second failure domain, Mimir runs as a separate process with
the same contract.

**Stop semantics.** Four distinct operations, each an API call and an
operator command: pause the planner (no new turns except operator
messages), stop runs (cancel workers of a delegation or project),
disable schedules (timers and evaluators), revoke authority (the
delegation's permissions, so nothing can be resubmitted). One operator
command, `/stop <delegation>`, performs all four and reports what it
stopped; a global kill switch does it for everything.

### D3 — Two pluggability contracts (locked)

- **Orchestrator contract** = the Saga API: submit a run and get a
  durable run id; read status, results and evidence; send guidance;
  cancel; consume events from a resumable cursor; request a review or a
  maintenance task; read and propose changes to delegation records.
  Odin is the first client; a CLI is the second (proves the API);
  an existing agent is the third (D18).
- **Worker contract** = per image: read the PRD, iterate until a
  completion signal or cap, write status and journal after each
  iteration, run the post-iteration hook, read guidance before each
  iteration, push the stream branch; when blocked on a decision, raise
  a structured request for operator input carrying a request id, the
  assignment, the decision needed, the options and what answering
  authorizes, then continue other work or stop cleanly. Claude Code
  first; Codex CLI second.

### D4 — Ledgers (locked)

Saga's run ledger (SQLite in the Saga service) is the authoritative
record of delegations, submissions, approvals, states, limits, evidence
and events, with a monotonically increasing event sequence. Odin's chat
log is Odin's memory and is never consulted to decide whether a run was
approved or completed. Odin rebuilds its picture after a restart by
replaying the cursor from the last sequence it logged.

### D5 — Completion semantics (locked)

Run states: `submitted` → `accepted` → `queued` → `started` →
`terminated` (exit code and reason) → `verified` or `failed` (judged
from evidence: success criteria, tests, pushed branch, and where
configured a verdict) → `closed`; `cancelled` and `limit-paused` are
side states. `depends_on` waits on `verified`. The launcher's `approved`
becomes `accepted`/`started` and never means success. A false
completion report is a defect of the evidence rules, tracked as a
measure (D18).

### D6 — Side effects (locked)

At-least-once with an idempotency key per action; destination
deduplication where possible; an explicit `unknown` outcome recorded
after a crash between action and record; reconciliation on restart.
No component claims exactly-once.

### D7 — Runtime and memory (runtime: locked; memory implementation: hypothesis)

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

### D8 — Mimir: selective, evidence-based, measured (default)

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

### D9 — Decision models: bounded judgments, never authority (locked)

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

### D10 — The standalone tools stay separate (locked)

| Tool | Role in the Odin plan | When |
|---|---|---|
| braid | Backend for the optional `recall` tool over lessons, wikis, contracts, imported history, worker journals across projects; child process over its stdio protocol; never indexes the chat log | after Odin v1 |
| skald | Optional archiver of Odin's and Mimir's chat logs via a provider adapter and the per-line `chat` id; must honour redaction (D7) | after the log format stabilizes |
| muninn | Optional `recall` scope over curated knowledge; its ADR-007 claim on typed journals is superseded (the chat log is canonical) | when the operator reactivates it |
| wayland-computer-use | A harness-independent desktop capability (two MCP servers, shared skills; observation and guarded input, no model decisions), usable only by a dedicated computer-use worker under a delegation that names desktop authority, through the seat lease and app-scoped boundary in D21; never reachable from planning sessions or container workers | after Phase F, by operator decision |
| standalone heimdall | Not an authority for approvals or task state. Optionally connected later as a human-facing continuity surface (overview, checkpoints, desktop bindings, review interface) that references Odin's commitment record as the one authoritative record (D20) | after D20's first configuration works; needs a release and green CI |

Nothing rolls into Odin. The harness core stays generic; Saga-specific
tools come from the Saga client library; everything else is an adapter.

### D11 — Eir: controlled improvement, loop closed (locked)

Three loops with distinct owners: the Saga service retries delivery,
reconciles worker state and enforces timeouts; Odin decides that work
needs different guidance; Eir changes code, prompts or configuration
through reviewed patches. The loop is only complete as: observed
failure → proposed change → regression check → approval → deployment →
measured outcome → rollback if needed. A merged PR is a proposed
improvement, not an improved behaviour; the ledger records the outcome
measure each change was meant to move. Eir normally runs as a Saga
task and keeps an operator-invoked path outside Saga's failure domain.
The merge gate remains the operator.

### D12 — Bragi (locked)

A model-driven compiler in the Saga repo. Inputs: Odin's and Mimir's
chat logs, Saga's ledger and delegation records, project wikis and
worker workspaces. Outputs: the vault, the lessons store, the
guidance-effectiveness table, the weekly review a delegation asks for.
Publishes lessons to Odin through the harness's import endpoint.

### D13 — Naming (locked)

**Rule.** Norse names only for agents that carry a persona and make
judgments. Every deterministic component, directory, image, topic and
tool gets a plain functional name, prefixed `saga-` when it is a
deliverable. Never reuse a name used by one of the operator's standalone
repos. Mythological places and metaphors appear only in Odin's identity
paragraph.

| Today | New name | Notes |
|---|---|---|
| Saga | Saga | the execution service and its repo |
| Odin, Mimir, Eir, Bragi | unchanged | agents; Bragi loses the "skald" epithet |
| dvergr, dvergar | **worker, workers** | |
| instance (container id) | **run** | one execution attempt of a stream by a worker |
| work stream | stream | |
| (new) | **delegation** | an ongoing responsibility the operator has delegated (D17) |
| Heimdall (`heimdall.py`) | **the Saga launcher** (`saga/launcher/`) | "Heimdall" is a standalone repo |
| Ratatoskr (`ratatoskr.py`) | **Saga events** (`saga/events/`) plus the Saga adapter in Odin | |
| keepalive | saga-keepalive | |
| `dvergr-hooks/` | `worker-hooks/` | |
| `containers/dvergr/`, image `saga-dvergr` | `containers/worker-claude/`, image `saga-worker-claude` | one directory per worker harness |
| `containers/odin/`, image `saga-odin` | moves to the `odin` repo | |
| MQTT `dvergr/{project}/{instance}/…` | `saga/runs/{project}/{run}/…` | renamed when Saga events v1 lands |
| `launch-requests/`, `launch-results/`, `commands/` | the Saga API | `commands/` is deleted |
| Huginn and Muninn (journal metaphor) | removed | muninn is a standalone repo |
| Nidavellir, Midgard, Yggdrasil, Hliðskjálf, Svartalfheim | removed | |
| (new) | **evaluator** | a versioned, harness-owned decision (D9) |

The banned-synonym list in `CLAUDE.md` shrinks to alternative agent
names (overseer, navigator, critic, judge, master). Legacy names remain
in `docs/history/` and in code until each rename lands.

### D14 — Repositories (locked)

`saga` and `odin`; the standalone repos stay where they are. Three
changes with different completion criteria, per
[`design/ODIN-REPOSITORY-EXTRACTION.md`](design/ODIN-REPOSITORY-EXTRACTION.md):
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

### D15 — Development direction and sequencing (locked)

| Phase | Deliverable | Exit criterion |
|---|---|---|
| **A** (now) | This record; docs consolidated (D16); credits claimed; billing re-test recorded in `CLAUDE.md`; Saga confirmed active | Operator sign-off on §5 |
| **B** | Saga service v1: run ledger and delegation records (D17); local API with client library; facade over the existing launcher and MQTT; the D5 state machine; launcher defects fixed; `commands/` deleted; D13 renames applied. **Minimum enforcement included:** approval and verdict binding by hash at submission, reviewer-identity verification, cancellation, the concurrency cap, the stop operations and the kill switch | A run can be submitted, watched by cursor, guided, stopped and cancelled from a CLI, and the CLI is refused for the same reasons Odin would be; `/stop` stops a whole delegation and reports |
| **C** | Odin v1 in the `odin` repo: the Odin service (commitments, memory with the D7 first implementation, event queue, wake policy, budgets, session records, scheduler, outbox) and the Claude Code integration package (tools, hooks, skills) over the Agent SDK with a narrow runtime adapter; Telegram adapter with hash-bound approvals; Saga client tools; Mimir review sessions under D8; migration import; shadow mode; cutover | Odin runs one project end to end without tmux, meeting Saga's boundary on its first live submission; an interrupted session is replaced without losing the outstanding assignment |
| **D** | Richer policy in Saga: TTL, per-run and per-day budget, operator-presence gate, action-authority boundaries for any new connector; evidence rules for `verified` per project type | A second client (the CLI) and Odin encounter identical policy; false completion reports measured |
| **E** | Worker contract document; Codex CLI worker image; a Pi image for API-key or local models; a second Odin harness adapter (Codex app-server or Pi RPC) with its capability matrix (D19) | A Codex run completes under the same hooks and ledger; Odin runs one assignment through the second adapter |
| **F** | `recall` on braid; `decide`; the first evaluator in shadow mode; skald archiver; Bragi on the new inputs; observability | — |
| **G** | The D18 evaluation and demonstration | Measured results published in the repo |

Phase B precedes C because Odin v1 is built against the API, and because
the first live project must meet the boundary D0 promises.

### D16 — Documentation (locked)

| Document | Action |
|---|---|
| `README.md` | Rewritten: positioning (D0), two products, current state, new names |
| `CLAUDE.md` | Rewritten: terminology with legacy mapping, constraints corrected and marked for re-test, phase plan |
| `docs/README.md`, `docs/ROADMAP.md` | Rewritten |
| `docs/DECISIONS.md` | This record |
| `docs/design/` | Odin I/O contract (v4), harness landscape assessment, research notes |
| `docs/saga-spec.md`, `ARCHITECTURE.md`, `GENERALIZATION.md` | Supersession banners |
| `docs/history/PUBLIC-README-DRAFT.md` | Superseded |
| Personas | Unchanged until Phase C |

### D17 — Delegation records (locked)

An ongoing responsibility is a first-class, versioned object in Saga's
ledger, above projects and runs:

| Field | Content |
|---|---|
| `outcome` and `scope` | What the operator wants kept true, and over which repositories, projects or services |
| `authority` | Permitted resources and actions: repositories and branches, secrets by name, worker images, network allowances, connectors (none in the first release) |
| `limits` | Budget (money, runs, container hours), concurrency, review cadence |
| `evidence` | What counts as success for a run and for the delegation's periodic review |
| `escalation`, `expiry`, `stop` | When to ask the operator, when the delegation lapses, what `/stop` stops |

Odin maintains priorities inside a delegation and proposes changes to
it through `ask_operator`; Saga enforces the accepted constraints (D2)
and scopes every run, limit and stop to a delegation. A delegation is
what Odin remembers as an unresolved commitment (D7) and what Bragi's
periodic review reports on. This extends the existing project wiki and
contracts rather than adding a service.

### D18 — Evaluation and the first demonstration (locked)

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

### D19 — Odin as a supervisory layer over a chosen harness (locked)

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

### D20 — Topology and operator interfaces (locked)

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

### D21 — Desktop capability and computer-use work (default)

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

### D22 — Preservation (locked in shape; integration scheduled)

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

### D23 — Execution backends (locked)

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

### D24 — Authentication and billing as adapter configuration (locked)

> Odin supports the operator's existing authenticated agent runtimes.
> Runtime choice, authentication method and billing policy are explicit
> configuration, independent of Odin's supervisory features.

Each runtime adapter's launch configuration states, per session class
and per worker image:

| Element | Content |
|---|---|
| Account and billing mode | `subscription` (the operator's own login, drawing on plan limits), `api` (a key from the Console organization linked to the plan, drawing on included credits then purchased credits), or `local` (a local model) |
| Credential reference | A reference to a protected credential source held by the service or by Saga's secret store; secrets never appear in prompts, the history, the briefing or exports |
| Refresh ownership | Which process renews the credential and how other processes receive updates; the harness's supported mechanism is preferred (Claude Code: a per-lineage login or a one-year `setup-token`, one refresher per lineage; Codex: its managed login, one `auth.json` lineage per worker refreshed in place, never one copy shared by concurrent containers; app-server's externally managed token mode stays experimental, not foundational) |
| Quota behaviour | Queue or pause when the selected account reaches its limit; switching to paid API usage only through an explicitly configured fallback; the `now` block and the overview show the state |
| Account separation | The operator's development login and the managed agents' login stay separate (CLAUDE.md auth boundaries); Odin's planning sessions and the workers may use different modes |

**Lineages.** A credential lineage is one login or one issued token
with its own refresh history. Copying one login file into several
containers does not create independent lineages: refresh tokens are
single-use, so the first container to refresh invalidates the others'
copies, and restoring a stale copy later re-introduces the failure
(the same hazards OpenAI documents for concurrent token rotation and
restored stale credentials). A lineage is **established** by a separate
login or `setup-token` per worker lineage, **persisted** in Saga's
secret store under the assignment it serves so a replacement worker for
the same assignment inherits it rather than minting a new one,
**refreshed** by exactly one owner (the worker's own harness for an
in-place refreshing file; the service for tokens it issues), and
**retired** when the assignment closes or the delegation expires or is
revoked. The launcher injects the lineage at `docker run`; nothing
mounts a shared writable credentials directory once the shadow period
ends.

Defaults: planning sessions on `api` (included credits; keeps planning
off the workers' plan limits); Claude workers on `subscription` through
the unmodified binary (permitted by Anthropic's hosting clause); the
compactor, triage subagents and decision models on their own configured
path. The shared writable credentials volume is the shadow-period
mechanism, not the architectural default; the keepalive process alone
does not establish refresh ownership among concurrent workers.

Promise: subscription-first with bounded, configured API spending.
Multiple sessions still draw down the account's allowance; nothing here
claims "no API costs".

## 4. The landscape, read as three questions

| Question | Answer in this record |
|---|---|
| Which components to build on | Claude Code through the Agent SDK as Odin's execution harness and as the first worker runtime; Codex CLI as the second worker runtime and candidate second Odin adapter; braid for retrieval; a System One provider for judgments; Pi as a worker runtime for API-key or local models and as design reference; the Messages API only if measured requirements force a custom runtime |
| Which products compete for the operator's attention | Personal agents with persistence, memory, proactivity, delegation and chat access (Hermes among open source; the hosted personal agents the feedback names, unverified here). Odin competes on delegated authority, verifiable outcomes, inspectable history and reviewed self-change, not on those features |
| Which systems can become Saga clients | Any orchestrator that speaks the Saga API: Odin first, a CLI second, an existing agent third (D18); worker harnesses by the worker contract |

## 5. Open decisions for the operator

1. **Is Saga active again?** Braid's roadmap recorded "Saga is deferred
   by user direction" in September; Phase B assumes it is not.
2. **Opus 5.5 or Sonnet 5.5** as Odin's default turn model, and the
   model for decomposition reviews (D8).
3. **The memory baseline** for the D7 evaluation (rolling summary plus
   notes plus `recall` is proposed) and the retention policy's defaults.
4. **Muninn's future**: a `recall` scope, Bragi's second destination
   later, or retirement.
5. **Licenses**: the UniiChat gist shows none; the five standalone repos
   show none. Settle before anything goes public.
6. **Credits and seats**: claim the Max API credits; decide on a second
   seat once the fleet runs again.
7. **The first delegation** for the D18 demonstration.
8. **Herdr's automation API**: confirm its session, prompt, read, wait,
   attach and takeover capabilities per adapter when the D20 workspace
   integration is built; it was not reviewed in this record.
9. **Desktop authority**: whether any delegation should name it in the
   first year (D21), and which applications would be in scope.
10. **Dotprivate's selected-files contract** (D22): confirm it is the
    intended mechanism and when its implementation lands.
11. **Skald retrieval** (contract §5): the archived-conversation scope
    depends on skald's retrieval or MCP work, which its status file
    lists as unfinished.
12. **Billing modes** (D24): confirm `api` as the default for planning
    sessions, and per-worker token provisioning once the re-test
    confirms `setup-token`.
