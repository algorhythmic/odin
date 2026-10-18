# Odin implementation blueprint

Date: 2026-10-14. Status: implementation reference synthesized from the
operator's architecture discussion and the local working trees of that day.
This documents intended work, not a deployed integration or a passing evaluation.
Adapted for the Odin repository from the text captured in extraction snapshot
`2026-10-14-14fdab3` ([frozen original](../history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md));
the adaptation changes authority, links and provenance. The increment placement
in §7 was then corrected to D15's phases (source review B2; recorded in
[`REVIEW-RESOLUTIONS.md`](../provenance/REVIEW-RESOLUTIONS.md)). Sections 2 to 8
were updated on 2026-10-16 for ODIN-ADR-006 to 015
([decision record §4](../DECISIONS.md#4-odin-decisions-odin-adr)).

## 1. Reading order and authority

Odin's authority order (extraction plan §4) replaces this section's earlier
order, which placed this document first and the decision record fourth:

1. [DECISIONS.md](../DECISIONS.md): authoritative decisions, particularly
   D2–D9 and D17–D21; inherited `Dn` references resolve through the
   [decision map](../provenance/DECISION-MAP.md).
2. [ODIN-IO-CONTRACT.md](ODIN-IO-CONTRACT.md): the operational contract and
   detailed design.
3. This document: product boundary, service design, and build sequence.
4. [ROADMAP.md](../ROADMAP.md): progress and dependency gates.

Alongside them: the [ecosystem integration plan](ODIN-ECOSYSTEM-INTEGRATION.md)
(proposed changes in Saga, Herdr, Heimdall, Skald, Braid, WCU, and dotprivate)
and the [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md) (the
demonstration, failure cases, and comparative evaluation), which must agree with
the decisions and the contract. Producer interfaces are governed by their pinned
producer contracts ([`../contracts/`](../contracts/README.md)).

These references operationalize the conversation. They do not silently amend
another repository's contracts. Proposed peer interfaces below require versioned
implementation in their owning repositories. Where current documents disagree,
the integration plan identifies the conflict and a proposed resolution. The
decision record continues to win until explicitly amended.

## 2. Product and operating model

> Odin turns agent sessions into persistent, supervised work across projects,
> using the harness the operator already prefers.

Odin is a supervisory layer, or meta-harness: an independently running service
plus an integration package for each supported harness. It adds commitments,
memory, attention management, session continuity, delegation coordination,
selective review, and evidence-based completion. It reuses the harness's inner
reasoning/tool loop, compaction, skills, plugins, and local subagents.

The first runtime adapter uses Claude Code through the Agent SDK. A second
adapter tests portability early; do not build a universal runtime framework
before two implementations establish what is common. A custom Messages API
runtime is justified only by measured unmet requirements. Billing, credentials,
installed versions, and supported plugin behavior need deployment verification;
this reference makes no subscription-credit or pricing guarantee.

Initial audience: an individual supervising technical projects. General email,
banking, purchases, and life administration are outside the initial scope.
Desktop work is an optional later capability for explicitly delegated technical
tasks. The full ecosystem demonstration is a destination, not an Odin v1 dependency.

### Two loops

- **Service loop, ordinary code:** receive events, persist state, schedule work,
  deliver messages, enforce local scheduling/budget rules, and reconcile effects.
- **Harness loop, model-driven:** investigate an assignment, plan, use tools,
  and return evidence, questions, or proposals.

A message passing through the Odin service need not invoke Odin's model.
Neither Jev nor an orchestration model is required for ordinary transport.

### Topology

Start with one Odin service, one active planning owner per project, and a small
pool of workers. Separate project sessions keep working context scoped. Mimir
uses bounded review sessions. Independent projects can progress concurrently.

Increase planning parallelism only for separable responsibilities or measured
decision latency. Every assignment has one owner; shared interfaces have a
designated decision owner. Use revision checks and ownership generations so a
resumed obsolete session cannot issue current guidance. Service replication is
later work; it requires exclusive ownership and shared-budget coordination,
not independent daemons competing over the same queue.

The Odin service runs on the homelab and is always on; Odin's records,
budgets and event substrate live there. A **workstation daemon** on the
operator's machine hosts local sessions, sensors, transcript capture and
surface adapters, and acts only on the service's command (ODIN-ADR-009).
Its **session host** dials out to the service, registers a stable host
identity and heartbeat, and starts, resumes, interrupts and retires SDK and
RPC harness sessions; session records, ownership generations and budgets
stay in the service. A binding whose host is unreachable becomes
`host_offline`: its sessions are unavailable, not failed, nothing is
retried until the host returns, and resume reconciles before any new turn.
Each host publishes an Environment record from a deterministic probe, and
the service refuses a session class whose required capabilities that
record lacks. Herdr is driven through its CLI, locally by the daemon or
over SSH with `herdr --machine` where no daemon runs; the SSH key and the
Herdr target stay in the service. Nothing the host runs carries Saga's
guarantees (D23.3). Operator surfaces are adapters on one service API
(§5, ODIN-ADR-010).

## 3. Component ownership

| Component | Owns | Does not establish |
|---|---|---|
| Odin service | Commitments, priorities, scheduling, session records, routing, memory, review coordination | Permission to bypass an execution backend |
| Workstation daemon (session host) | On the operator's machine and only on the service's command: the session host, the environment probe, surface sensors, the capture module and surface adapters (ODIN-ADR-009) | Session records, ownership generations or budgets; authority from an observation; Saga's guarantees for anything it runs (D23.3) |
| Agent harness | Reasoning and tools within a session | Durable cross-session project completion by itself |
| Saga | Delegation authority, run admission, isolated execution, limits, run/evidence ledger, recovery | Odin's working memory or the desktop workspace layout |
| Mimir | Evidence-based critique by two reviewer positions with service-run consensus (hypothesis, ODIN-ADR-013) | Operator authorization; settlement of a disagreement, which goes to the operator |
| Reviewer signer | The reviewer identity key, held in the service by a signer component that no session or planner tool can reach, run as a separate process under D2.5's option (ODIN-ADR-013); records the combined verdict in the format Saga verifies (D2.4b) | Review judgment, operator authorization, or Saga's acceptance of per-position verdicts (B-10) |
| System One evaluator | Bounded semantic judgments | Approval, completion proof, or permission to remove a gate |
| Herdr | Terminal layout, session visibility, supported agent/terminal controls | Assignment completion or Saga admission |
| Heimdall | Standalone native task continuity until its task, checkpoint and decision layer is retired by a one-time import into commitments, with no bridge (ODIN-ADR-007); its surface sensors move to the workstation daemon | Authority over Odin or Saga records; a second editable task store after the import |
| Skald | Transcript capture library, used by the capture module of the workstation daemon, writing the transcript-archive namespace through a local spool (ODIN-ADR-006); its own archive remains a standalone sink, useful without Odin | Accepted work state or generated lessons |
| Braid | Scoped, budgeted retrieval as an in-process library over published, scoped namespace data in its own per-dataset files; never the active chat (X-4) | Truth, authorization, or ownership inferred from similarity |
| WCU | Desktop observations and outcome evidence; guarded input as a gated process of the workstation daemon under its own Unix user, holding the seat lease, disabled until desktop authority is decided (ODIN-ADR-011) | Model planning, unqualified task success, or device-wide exclusivity before the compositor restriction is verified |
| dotprivate | The operator's own private-material tool, off Odin's dependency path; Odin writes the selected package to its own export directory and runs git with its own receipts (ODIN-ADR-012) | Live database backup, proof that work was accepted, or an Odin interface |

Bragi remains the model-driven lessons compiler; Eir remains the reviewed
maintenance agent. Skald does not replace Bragi, and Odin's availability must
not be required for Saga's out-of-band recovery. Saga remains a separate
product with its own repository (D14.1); the consolidation plan's placement
of Saga in a shared repository, and any transfer of Bragi or Eir, are
proposals that wait on Saga-side decisions (X-14).

## 4. Minimum service records and invariants

The following are conceptual records to turn into versioned schemas. Their
names are not existing API methods. Reuse the I/O contract's message fields
where possible rather than introducing a second incompatible event envelope.

| Record | Minimum information |
|---|---|
| Project / source document | Stable project ID, source locator, immutable version/digest, associations |
| Commitment | Objective, acceptance criteria, owner/generation, revision, dependencies, open decisions, next trigger, evidence refs, delegation ref, checkpoints, task decisions, import provenance where imported (ODIN-ADR-007) |
| Assignment | Commitment/revision, exact input artifacts, scope, output contract, owner, limits, backend, status |
| Session binding | Assignment, harness/provider, native session ID, process incarnation, host, capabilities, optional explicit Herdr binding, `host_offline` state (ODIN-ADR-009) |
| Event | Stable event ID, namespace, producer identity, kind, scope, source sequence where available, received time, causation/correlation IDs, payload/ref |
| Human request | Request ID, assignment, question/options, proposal digest if applicable, intended recipient, expiry, state, response ref |
| Effect / outbox entry | Idempotency key, destination, payload digest, attempt state, receipt, reconciliation information |
| Review | Artifact lineage, evidence packet digest, review type, the two reviewer positions (each with identity, harness, model and family, verdict, findings, usage), the combined verdict and combination outcome, rounds, usage (ODIN-ADR-013) |
| Evaluator result | Config/model version, evidence refs, result/status, routing consequence, usage, later assessed outcome |
| Environment | Host identity, probe time, harness and Herdr versions, sandbox and isolation support, available surfaces and sensors, credential lineages present (never their secrets) (ODIN-ADR-009) |
| Session-class decision | Chosen class, rejected candidate classes with deterministic reasons, inputs used, configuration revision; never changes routing at run time (ODIN-ADR-014) |

Do not use a title, cwd, branch name, or pane ID as a universal project/session
identity. Preserve source-native identities and explicit mappings. A re-created
session gets a new binding while retaining its assignment lineage.

These records and the history they belong to live in one append-only event
substrate with namespaces (Odin history, transcript archive, workstation
surface events), each written by exactly one component under its own
retention and redaction rules (ODIN-ADR-006). An execution-ledger namespace
is reserved as a read-only mirror of Saga's store, filled only through
Saga's API and event cursor; it decides nothing, and Saga's store stays
authoritative (D4). Store topology and failure domains are open (X-11).

Commit event consumption and the source cursor together. A duplicate delivery
must not create a second assignment, review, notification, or run. Events from
different producers have no implied total causal order merely because their
timestamps sort. Saga's ledger sequence remains its own authoritative order.

Effects are at-least-once with destination deduplication where available. If a
process dies after dispatch but before recording a receipt, retain `unknown`
and reconcile before retrying. Replay rebuilds state without replaying effects.
No component claims exactly-once delivery.

Keep assignment/session lifecycle separate from the D5 run state machine.
`idle`, a finished tool call, or a worker's "done" message does not make a run
`verified`. A project can remain open after all current runs are verified if
integration criteria or commitments remain unsatisfied.

## 5. Operator interaction and message routing

Operator surfaces are adapters on one service API, and every one enters the
same recorded command path (ODIN-ADR-010): the terminal workspace, Telegram (on
the homelab, so approvals and stop work when the workstation is off), a
summoned terminal conversation, a status bar, desktop notifications with typed
actions, and later voice. Herdr and Telegram remain the first configuration;
the other surfaces are not part of the restrained initial product (D19.6). The
terminal workspace exposes projects, sessions, pending decisions, evidence, and
budgets; Telegram supports asynchronous questions, corrections, summaries, and
approvals. One human view shows commitments, runs and transcripts with their
owners attributed. No surface becomes a separate Odin, and no harness gateway
faces the operator directly.

Use typed events before semantic classification:

| Input | Default service behavior |
|---|---|
| Heartbeat / routine progress | Persist, update projections, include in bounded digest |
| Explicit human-input request | Deliver to the operator queue without a planning turn |
| Approval response | Validate principal, exact proposal binding, expiry, revision, and outstanding request in code |
| Stop / revoke / correction | Priority handling; bypass learned routing |
| Ambiguous worker prose | Optional approved evaluator; uncertainty follows baseline handling |
| Eligible routine journal entries | Coalesced triage: `no_attention` logs without immediate planner wake; attention or triage failure wakes; bounded digest preserves deferred evidence (I/O contract §5, ODIN-ADR-002) |
| Scope change / dependency conflict / strategic failure | Engage the responsible planning session |
| Workstation observation (focus, idle, surfaces) / capture lifecycle (session started, ended, gap) | State-only or log-only by default; never authority; wakes a planner only through a typed rule. Raw observation content stays with the local provider (D9.5); frontier sessions receive derived signals only |
| Provider failure / missing observation | Record coverage gap and use the defined fallback |

Every human request shows its source, assignment, necessary evidence, requested
decision, and effect. Preserve the distinction between clarification, permission
to run a harness tool, approval of a plan, and Saga authorization. A natural
language response interpreted by a model does not manufacture a hash-bound grant.
Cross-channel replies resolve one request; late or conflicting replies cannot
approve a replacement artifact. Local session permission dialogs require an
adapter-supported relay or deliberate operator interaction, not synthesized Enter.

An **attention prompt** is a typed outbound effect: an operator-facing proposal
with its evidence reference and a mandatory response (done, snooze, dismiss, or
override with reason) that is itself a record. Prompts carry per-surface and
per-day caps, coalescing, quiet hours, a cooldown and expiry, and leave shadow
mode only when logged outcomes support the caps. Ranking is recomputed in code
on every event; only a change that survives a hysteresis window is surfaced,
and prompts about a focused session wait for that session's boundary. A message
queued to an Odin-run session uses the adapter's supported injection, never a
synthesized keystroke or guidance to a Saga run.

Voice comes later, after its data-policy decision (X-13). It may carry
questions, clarification answers and stop, never an approval: an approval is
accepted only on a surface that shows the request id and proposal digest
(AC-06, AC-30).

Two explicit operations are required: **adopt into supervision** binds an
existing session with granted control; **take control** suspends automated input
and attention prompts to that session until a recorded return handoff. Viewing
a session is not taking it over.

Expose stop without requiring inference. Preserve D2's distinct operations:
pause planner, cancel runs, disable schedules, and revoke authority. The combined
delegation/global stop reports acknowledged and uncertain outcomes. On a lost
backend connection, do not claim remote cancellation succeeded.

## 6. Memory, critique, and decision models

### Memory

Keep authoritative obligations outside lossy summaries. OptChat/UniiChat is the
first evaluated implementation of bounded summaries and source expansion, not a
requirement to replace Claude Code's context loop. Render a briefing at session
start; expose `zoom` and optional `recall`; resume or replace sessions at explicit
boundaries. Do not promise the original cache layout or constant total context.

At I5, compare against rolling summary plus structured notes with identical
frozen fixture retrieval available to both arms (ODIN-ADR-003). Pin the
corpus, query-to-result mapping, scopes, byte limits, harness/model and run
budget before evaluation. Keep authoritative commitments identical and count
all memory/retrieval costs. This tests memory, not live peer integration.
After I6, repeat using the same real retrieval adapters in both arms;
disclose configuration changes. Final D18 evaluation remains in Phase G.

Preserve routed events durably, but select their relevance for planning context.
Skald archives full native conversations independently; Odin records references
and selected content instead of blindly injecting all worker transcripts.
Summary provenance must reach original evidence. Corrections and supersession
remain visible. Redaction propagates through summaries, indexes, archive copies,
and preservation destinations under an explicit policy; failed propagation stays
pending and cannot be reported as completed deletion.

Compactor effort starts experimentally at `high`, compared with `medium`
and `xhigh`; triage is evaluated separately (ODIN-ADR-005). Empty or invalid
summaries never replace valid nodes. Whole-request token accounting covers
raw leaves, merged nodes and harness overhead; byte-bounded summaries alone
do not prove a small prompt. The Haiku-specific budget and measured cache
policy are in I/O contract §8/§12; AC-34–AC-35 cover failures.

### Mimir

Review decompositions, shared contracts, material guidance changes, Eir behavior
patches, and working-principle changes. Run mechanical checks first. Required
review is then performed by two reviewer positions, on frontier models of
different families where the adapters allow it (ODIN-ADR-013, a hypothesis).
Each position receives the same deterministic evidence pack: original
requirements, exact artifacts, relevant contracts, deterministic results, and
lineage verdicts. It sees neither Odin's conversational reasoning nor the other
position's findings. One review and at most one corrective re-review precede
escalation. Service code combines the verdicts: approval requires both positions
to approve; any `REJECT` or `INSUFFICIENT_EVIDENCE`, or a disagreement that
survives the corrective re-review, goes to the operator with both positions and
their evidence. Any pair containing `FLAG` also escalates under Saga ADM-7;
the action-level table is in I/O contract §10. `APPROVE_UNCHANGED` is a
first-class outcome. Only matching approving pairs pass into the log without
an operator message; mixed `APPROVE`/`APPROVE_UNCHANGED` stays pending with
no signed combined verdict until its I0 schema mapping is defined. Roles are assigned per
project: one planning owner and one standing reviewer position, which may swap
between projects. The reviewer signer records the combined verdict under the
reviewer identity key, in the format Saga verifies; Saga accepting per-position
verdicts would be a Saga contract change (B-10). Separate reviewer credentials
from the planner's accessible tools. Sharing a host is not security isolation.
Caps apply per position and in total (D8.6). Sending evidence packs to a second
provider waits on its data-policy decision (X-13).

Mimir is configurable, but a run whose policy requires review cannot proceed
merely because the reviewer is disabled or unavailable, and an unavailable
position never waives required review. Record evidence gaps. Compare the
two-position protocol against single review and an equivalent extra
verification budget, including harm from unnecessary changes and escalations;
it stays only if it wins on D8's measures, and it stays switchable (D19.3).

### System One

Expose advisory `decide`; use named, versioned evaluators for persistent routing.
`propose_decider` binds model version, questions, input projection, thresholds,
fallback, and permitted effects to replay/shadow evidence and required approval.
Do not use a general agent-written question as an automatically installed hook.

First evaluator: journal attention in shadow mode. Mandatory events bypass it;
routine deferral has a maximum age. An activated evaluator's `no_attention`
outcome follows the same logged, bounded-digest path as journal triage;
it does not trigger a planner turn merely by returning a report. Provider
failures return to ordinary triage, whose uncertainty or failure queues a
planner wake with the original evidence (I/O contract §5). Shadow results
never suppress baseline wakes. Include triage, evaluator and digest costs
when measuring savings.
Confidence is not observed correctness. A new provider/model/question needs
revalidation. Hosted inputs are allowlisted; D9's local-only restriction follows
operator/specification content into summaries, questions, and candidates too.

Jev is not Mimir, an approval engine, or a transport. For desktop work its current
documented text-only interface can classify accessibility/DOM/readback evidence;
vision and coordinate grounding remain with capable models and WCU's guards.

ODIN-ADR-004 keeps the first experiment at the existing journal-attention
hook. Defer only on a validated routine probability with adequate evidence
and no contradictory typed state; otherwise take the baseline path. Haiku
agreement is not ground truth. Operator target bindings remain explicit;
session class, model and effort are selected in code, stable across resumes.
The validated workload-class configuration belongs to I/O contract §5 and
its schema and fixtures are I0 work. Its classes are distinct from tool
capability profiles and service/process roles; the examples define no model
default or fixed enum.
Each code-made selection records the chosen class, the rejected candidate
classes with their deterministic reasons, the inputs and the configuration
revision (ODIN-ADR-014), so that an independent outcome assessment can judge it
later; the record never changes routing at run time.
No fifth hook or per-turn tier classifier is added. Jev does not generate
summaries, guidance or plans, and does not choose worker models.

## 7. Implementation sequence

Map these increments to D15/ROADMAP; they do not replace that sequence. The
phase each increment belongs to is the I/O contract's §13. Optional integrations
can be developed against fixtures in an earlier increment, but that work is
non-production, is labelled as fixture work, and does not delay the core proof.

| Increment | Phase (D15) | Deliverable | Exit evidence |
|---|---|---|---|
| I0: contracts and fixtures | B (non-production) | Versioned event envelope and namespaces (EC-01, ODIN-ADR-006); record schemas with the ODIN-ADR-007, 009, 013 and 014 changes, workload-class configuration schema, and the mapping from heimdall's record types; fixtures for the duplicate, stale and unknown cases, validated by the Go and the Python implementation against the same set (ODIN-ADR-008). Envelope and unaffected schemas can start while X-7 remains open | Both implementations validate the same fixtures; duplicate/stale/unknown cases have explicit semantics; X-7 is resolved before Review/guidance schemas are written; no peer API is invented as implemented |
| I1: service foundation | B (non-production) | Transactional state, event intake/cursors, outbox, scheduling, direct stop, CLI; moved from I0: capability matrix, fake Saga backend, synthetic three-document fixture, ownership mapping | Restart/replay produces one logical action and retains unknown outcomes; the execution-ledger mirror stays read-only (X-11) |
| I2: first harness | C (non-production) | Claude Code adapter and integration package; briefing/zoom; session lifecycle; capability profiles with the planner tool-isolation check; workstation daemon v0: session host, environment probe, `host_offline`, compositor and Herdr observers, capture module with a local durable spool | One bounded assignment survives replacement of its session; unsupported operations are explicit; an offline host leaves its sessions unavailable, not failed, and resume reconciles first (proposed AC-37); captured batches append atomically per checkpoint with gaps visible (proposed AC-41) |
| I3: governed project | C (requires Phase B exit) | Saga Phase B boundary, operator channel, selective Mimir, verification; read-only Herdr inspection (overview, attachable sessions where supported) | One real project passes admission and finishes with evidence; CLI and Odin face the same refusal rules |
| I4: parallel workspace | D | Second project, full Herdr adapter with explicit bindings, scoped planning owners, adopt and takeover; one-time import of heimdall's task layer into commitments; human view v0 | Projects remain separate, bindings are explicit, no pane state is mistaken for completion; the import is idempotent with a receipt, and source-side edits are enforceably refused under EC-13/G-10 (proposed AC-38) |
| I5: portability and context | E | Second harness adapter; controlled memory comparison with identical fixture retrieval | Capability differences and unavailable-peer behavior pass the acceptance scenarios; memory evidence labelled fixture-based |
| I6: optional optimizations and integrations | F | Braid `recall` as an in-process library; the capture module, built on skald's capture library, as the transcript-namespace module (source enrollment, archive ingestion) and history (`archive` scope); repeat memory comparison with live retrieval; shadow evaluator, controlled activation; attention prompts out of shadow on outcome evidence; Odin's own package export with receipts (ODIN-ADR-012) | Routing benefit measured; export receipts distinguish copied locally, committed and confirmed on the remote; archive coverage gaps visible; integrated memory evidence recorded |
| I7: desktop workflow | G, by operator decision | Guarded desktop input as a gated process of the workstation daemon holding the seat lease (EC-10's shared seat broker; ODIN-ADR-011); dedicated desktop worker; human takeover; bounded textual classifier experiment | No cooperating agents input concurrently; uncertain effects reconcile; end-to-end outcomes measured |

Under Odin's sequencing interpretation (D15; X-1, still awaiting producer
reconciliation), I0 uses fixtures; I1–I2 may use a fake Saga backend for development (it implements the I/O
contract's Appendix B and is never presented as Saga); that work is
non-production and establishes no production readiness. I3, every production
delegated run and every live Saga submission require Phase B's exit criterion and
minimum enforcement (D15.8). A backend without Saga must state its own limits and must
not advertise Saga guarantees; it is not a bypass for a Saga-managed delegation.
The full three-workstream ecosystem demonstration follows the one-project proof.

ODIN-ADR-008 narrowed I0 and moved its other items to I1 and I2; nothing was
dropped and the phase mapping is unchanged. X-11 is decided before I1. In I2
the workstation daemon is non-production: its local sessions use the
credential lineage decided under X-12, never the operator's development login;
the Herdr observer and the capture module are fixture work there (live Herdr
inspection stays I3, skald enrollment and archive ingestion stay I6); and code
imported from heimdall or skald waits on the roadmap's gates G-9 and G-10.
Heimdall's import (I4), capture and braid as modules (I6) and the move of
WCU's guarded input (I7) also wait on G-10.

After I2's exit, a minimal Pi RPC adapter runs the same bounded assignment and
session replacement against the fake backend, as a control for the Claude Code
adapter, and publishes its capability matrix and gaps (ODIN-ADR-015). It is
non-production and fixture-only, not an added gate or a change to the locked
sequence, and its evidence is labelled fake-backend. Claude models through Pi
use an API key, never the subscription or Pi's Anthropic OAuth path. No common
adapter framework is extracted until both adapters exist; full second-adapter
delivery and Phase E's exit remain I5. X-1's cross-repository sequencing
question remains open.

**Evaluation and subagent checks** (ODIN-ADR-020). I1 defines validated
evaluation metadata and the extended child capability matrix (I/O
contract §11); it does not widen I0. I2 checks profile inheritance across
native child paths, partial/stale result handling and observational class
records (AC-42–AC-43, AC-36). Shared cap and child lifecycle enforcement
must be designed under X-15 before child dispatch, then checked by
AC-44/AC-23. The Pi control repeats relevant checks with its exact runtime
and extension set. Acceptance §3 separates models from harnesses, advice
from execution and whole-task cost from root savings; its final
comparisons remain Phase G. No new framework, model default or learned
router is selected. These are pending implementation tasks, not runtime
evidence.

The [consolidation plan](CONSOLIDATION-PLAN.md) is a proposal. Its phases P0 to
P7 map onto these increments and do not replace them; where it places an item
differently, this table governs. Its repository consolidation and its
Saga-side parts wait on X-14.

## 8. Source basis

Primary basis: the operator's architecture conversation and local documents read
on 2026-10-14. When this document was written, Saga's decision and design files
were uncommitted. They were later committed, and this repository's copies were
captured clean from Saga commit `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada`.
See the [extraction wrapper](../history/saga-extraction/README.md) and
[`EXTRACTION-MANIFEST.json`](../provenance/EXTRACTION-MANIFEST.json). The
integration plan lists companion source baselines and gaps as observed that day.

The 2026-10-16 changes rest on the operator's consolidation direction of that
day, recorded as ODIN-ADR-006 to 015, and on four dated investigation reports
read from the operator's local checkouts without building or running anything
([`consolidation-2026-10/`](../research/consolidation-2026-10/README.md)): the
inventory of the standalone Go repositories, the inventory of Saga,
wayland-computer-use and dotprivate, the decision-record analysis, and the
monorepo mechanics report. They are evidence, not policy.

External capability references checked during the discussion; they were not
rechecked during extraction. Revalidate the installed versions when building
adapters:

- [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
  [sessions](https://code.claude.com/docs/en/agent-sdk/sessions),
  [plugins](https://code.claude.com/docs/en/agent-sdk/plugins).
- [Herdr automation](https://herdr.dev/docs/agent-automation/).
- [System One routing guide](https://systemonemodels.org/use-cases/real-time-and-agents/agent-routing-and-skill-selection/),
  [TypeSafe primitives](https://docs.typesafe.ai/primitives),
  [confidence](https://docs.typesafe.ai/confidence),
  [models](https://docs.typesafe.ai/models),
  [documented Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).
