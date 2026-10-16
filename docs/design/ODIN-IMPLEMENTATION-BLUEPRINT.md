# Odin implementation blueprint

Date: 2026-10-14. Status: implementation reference synthesized from the
operator's architecture discussion and the local working trees of that day.
This documents intended work, not a deployed integration or a passing evaluation.
Adapted for the Odin repository from the text captured in extraction snapshot
`2026-10-14-14fdab3` ([frozen original](../history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md));
the adaptation changes authority, links and provenance. The increment placement
in §7 was then corrected to D15's phases (source review B2; recorded in
[`REVIEW-RESOLUTIONS.md`](../provenance/REVIEW-RESOLUTIONS.md)).

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

## 3. Component ownership

| Component | Owns | Does not establish |
|---|---|---|
| Odin service | Commitments, priorities, scheduling, session records, routing, memory, review coordination | Permission to bypass an execution backend |
| Agent harness | Reasoning and tools within a session | Durable cross-session project completion by itself |
| Saga | Delegation authority, run admission, isolated execution, limits, run/evidence ledger, recovery | Odin's working memory or the desktop workspace layout |
| Mimir | Evidence-based critique and authenticated review verdicts | Operator authorization |
| System One evaluator | Bounded semantic judgments | Approval, completion proof, or permission to remove a gate |
| Herdr | Terminal layout, session visibility, supported agent/terminal controls | Assignment completion or Saga admission |
| Heimdall | Native task continuity; proposed external-work views and desktop bindings | Authority over Odin/Saga records merely displayed there |
| Skald | Independent source-conversation archive and operator transcript views | Accepted work state or generated lessons |
| Braid | Scoped, budgeted retrieval over consumer-managed datasets | Truth, authorization, or ownership inferred from similarity |
| WCU | Desktop observations, guarded input, outcome evidence | Model planning or unqualified task success |
| dotprivate | Selected private project material and publication receipts when implemented | Live database backup or proof that work was accepted |

Bragi remains the model-driven lessons compiler; Eir remains the reviewed
maintenance agent. Skald does not replace Bragi, and Odin's availability must
not be required for Saga's out-of-band recovery.

## 4. Minimum service records and invariants

The following are conceptual records to turn into versioned schemas. Their
names are not existing API methods. Reuse the I/O contract's message fields
where possible rather than introducing a second incompatible event envelope.

| Record | Minimum information |
|---|---|
| Project / source document | Stable project ID, source locator, immutable version/digest, associations |
| Commitment | Objective, acceptance criteria, owner/generation, revision, dependencies, open decisions, next trigger, evidence refs, delegation ref |
| Assignment | Commitment/revision, exact input artifacts, scope, output contract, owner, limits, backend, status |
| Session binding | Assignment, harness/provider, native session ID, process incarnation, host, capabilities, optional explicit Herdr binding |
| Event | Stable event ID, producer identity, kind, scope, source sequence where available, received time, causation/correlation IDs, payload/ref |
| Human request | Request ID, assignment, question/options, proposal digest if applicable, intended recipient, expiry, state, response ref |
| Effect / outbox entry | Idempotency key, destination, payload digest, attempt state, receipt, reconciliation information |
| Review | Artifact lineage, evidence packet digest, review type, reviewer identity, findings/verdict, usage |
| Evaluator result | Config/model version, evidence refs, result/status, routing consequence, usage, later assessed outcome |

Do not use a title, cwd, branch name, or pane ID as a universal project/session
identity. Preserve source-native identities and explicit mappings. A re-created
session gets a new binding while retaining its assignment lineage.

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

Terminal and Telegram are clients of one recorded command path. The terminal
workspace exposes projects, sessions, pending decisions, evidence, and budgets;
Telegram supports asynchronous questions, corrections, summaries, and approvals.
Skald and Heimdall add complementary views without becoming separate Odins.

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
| Provider failure / missing observation | Record coverage gap and use the defined fallback |

Every human request shows its source, assignment, necessary evidence, requested
decision, and effect. Preserve the distinction between clarification, permission
to run a harness tool, approval of a plan, and Saga authorization. A natural
language response interpreted by a model does not manufacture a hash-bound grant.
Cross-channel replies resolve one request; late or conflicting replies cannot
approve a replacement artifact. Local session permission dialogs require an
adapter-supported relay or deliberate operator interaction, not synthesized Enter.

Two explicit operations are required: **adopt into supervision** binds an
existing session with granted control; **take control** suspends automated input
until a recorded return handoff. Viewing a session is not taking it over.

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
patches, and working-principle changes. Run mechanical checks first. Supply
original requirements, exact artifacts, relevant contracts, deterministic results,
and lineage verdicts; exclude Odin's conversational reasoning. One review and at
most one corrective re-review precede escalation. Separate reviewer credentials
from the planner's accessible tools. Sharing a host is not security isolation.

Mimir is configurable, but a run whose policy requires review cannot proceed
merely because the reviewer is disabled or unavailable. Record evidence gaps.
Compare review against an equivalent extra verification budget, including harm
from unnecessary changes and escalations.

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
No fifth hook or per-turn tier classifier is added. Jev does not generate
summaries, guidance or plans, and does not choose worker models.

## 7. Implementation sequence

Map these increments to D15/ROADMAP; they do not replace that sequence. The
phase each increment belongs to is the I/O contract's §13. Optional integrations
can be developed against fixtures in an earlier increment, but that work is
non-production, is labelled as fixture work, and does not delay the core proof.

| Increment | Phase (D15) | Deliverable | Exit evidence |
|---|---|---|---|
| I0: contracts and fixtures | B (non-production) | Record schemas, capability matrix, synthetic three-document fixture, ownership mapping | Duplicate/stale/unknown cases have explicit semantics; no peer API is invented as implemented |
| I1: service foundation | B (non-production) | Transactional state, event intake/cursors, outbox, scheduling, direct stop, CLI | Restart/replay produces one logical action and retains unknown outcomes |
| I2: first harness | C (non-production) | Claude Code adapter and integration package; briefing/zoom; session lifecycle | One bounded assignment survives replacement of its session; unsupported operations are explicit |
| I3: governed project | C (requires Phase B exit) | Saga Phase B boundary, operator channel, selective Mimir, verification; read-only Herdr inspection (overview, attachable sessions where supported) | One real project passes admission and finishes with evidence; CLI and Odin face the same refusal rules |
| I4: parallel workspace | D | Second project, full Herdr adapter with explicit bindings, scoped planning owners, adopt and takeover | Projects remain separate, bindings are explicit, no pane state is mistaken for completion |
| I5: portability and context | E | Second harness adapter; controlled memory comparison with identical fixture retrieval; Heimdall external views | Capability differences and unavailable-peer behavior pass the acceptance scenarios; memory evidence labelled fixture-based |
| I6: optional optimizations and integrations | F | Braid `recall`; Skald source enrollment, archiver and history (`archive` scope); repeat memory comparison with live retrieval; shadow evaluator, controlled activation; selected preservation contract | Routing benefit measured; publication receipts distinguish local and remote state; archive coverage gaps visible; integrated memory evidence recorded |
| I7: desktop workflow | G, by operator decision | WCU worker, shared seat broker, human takeover, bounded textual classifier experiment | No cooperating agents input concurrently; uncertain effects reconcile; end-to-end outcomes measured |

Under Odin's sequencing interpretation (D15; X-1, still awaiting producer
reconciliation), I0–I2 may use a fake Saga backend for development (it implements the I/O
contract's Appendix B and is never presented as Saga); that work is
non-production and establishes no production readiness. I3, every production
delegated run and every live Saga submission require Phase B's exit criterion and
minimum enforcement. A backend without Saga must state its own limits and must
not advertise Saga guarantees; it is not a bypass for a Saga-managed delegation.
The full three-workstream ecosystem demonstration follows the one-project proof.

The roadmap also proposes a small Codex adapter experiment after I2 to test
portability before broad peer integrations. It is fixture-only, not an added
gate or a change to the locked sequence; full second-adapter delivery remains
I5. X-1's cross-repository sequencing question remains open.

## 8. Source basis

Primary basis: the operator's architecture conversation and local documents read
on 2026-10-14. When this document was written, Saga's decision and design files
were uncommitted. They were later committed, and this repository's copies were
captured clean from Saga commit `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada`.
See the [extraction wrapper](../history/saga-extraction/README.md) and
[`EXTRACTION-MANIFEST.json`](../provenance/EXTRACTION-MANIFEST.json). The
integration plan lists companion source baselines and gaps as observed that day.

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
