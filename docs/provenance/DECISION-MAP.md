# Decision provenance map

Status: candidate, written for the documentation handoff of extraction
snapshot `2026-10-14-14fdab3`; part of the D14 handoff gate, which is
awaiting independent re-review. The handoff is **not yet recorded**.

This map resolves every inherited decision reference. Findings of the
source review ([`SOURCE-REVIEW.md`](SOURCE-REVIEW.md)) are tracked in
[`DECISIONS.md`](../DECISIONS.md) §6 and resolved, with evidence, in
[`REVIEW-RESOLUTIONS.md`](REVIEW-RESOLUTIONS.md). Mapping a clause
resolves none of them. The source is the
joint Saga and Odin decision record frozen at
[`../history/saga-extraction/2026-10-14-14fdab3/docs/DECISIONS.md`](../history/saga-extraction/2026-10-14-14fdab3/docs/DECISIONS.md)
(Saga commit `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada`, record "v2,
2026-10-14"). The procedure is in the
[extraction plan](../history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-REPOSITORY-EXTRACTION.md) §4.

## How to read this map

- **Identifiers.** The legacy decision `Dn` is `SAGA-2026-10-Dn`. A bare
  `Dn` in any Odin document means `SAGA-2026-10-Dn` and resolves here;
  nothing is renumbered. Clause numbers (`D7.4`, `D24.8b`) are assigned
  by this map, in source order, so split decisions can be mapped
  clause by clause; they do not appear in the source. They are local to
  Odin: Saga's map labels its clauses with letters (`D2.a`, `D24.d`) for
  its own use. Only the decision-level `SAGA-2026-10-Dn` is shared, so
  cross-reference the two maps by decision and content, never by
  suffix; for example Odin's `D24.8a` and Saga's `D24.d` are the same
  planning-session default. Neither map renumbers the other. New
  decisions use `ODIN-ADR-nnn` (Odin) or `SAGA-ADR-nnn` (Saga). Odin's
  records are mapped at the end of this document and in DECISIONS.md §4.
- **Owner.** The repository whose live record carries the normative
  text after the handoff is recorded. `Shared rule` means the clause
  applies to both services and each owns its own implementation and
  wording; there is no joint editable master. A peer name (Herdr,
  heimdall, skald, braid, WCU, dotprivate) means that project owns the
  capability; Odin documents only what it requests and consumes.
  `Operator` means an unresolved choice that only the operator can make.
- **Until the handoff is recorded**, the frozen Saga record and Saga's
  live record remain authoritative (D14.7); this map designates owners,
  it does not transfer them.
- **Status** is copied from the source: locked, default, hypothesis or
  open. `historical` marks text with no continuing obligation
  (rationale, completed Saga documentation actions). Moving a clause
  does not change its status, approve a proposal, or close a question.
  One status is recorded more precisely than its heading: D24.8a,
  *default, pending operator confirmation*, because the source's own
  §5 question 12 leaves it to the operator (review finding N8).
- **Odin location** is where Odin carries the clause:
  [`DECISIONS.md`](../DECISIONS.md) (by `Dn` heading), the
  [I/O contract](../design/ODIN-IO-CONTRACT.md) (`IO §n`), the
  [blueprint](../design/ODIN-IMPLEMENTATION-BLUEPRINT.md) (`BP §n`), the
  [ecosystem plan](../design/ODIN-ECOSYSTEM-INTEGRATION.md) (`EI §n`),
  the [acceptance scenarios](../design/ODIN-ACCEPTANCE-SCENARIOS.md)
  (`AS §n`), the [roadmap](../ROADMAP.md) or the pinned Saga contract
  ([`contracts/README.md`](../contracts/README.md)). `—` means Odin
  holds no normative copy.

## Record sections outside D0–D24

| Clause | Source | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|---|
| H.0 | header | Record authority over `saga-spec.md`, `ARCHITECTURE.md`, `GENERALIZATION.md`, personas, design docs; status vocabulary | Shared rule | DECISIONS.md header | locked | Odin's authority order is set by the extraction plan §4 (decisions, contract, blueprint, roadmap); Saga-only documents are not part of Odin |
| §0 | §0 | The two directives and the summary answer | — | DECISIONS.md D0, D19 restate the operative parts | historical | Summary of D0–D24; not separately normative |
| §1.a | §1 | Evaluation of the architecture proposal; adopted items D1–D6, D11, D13 | — | — | historical | Rationale only |
| §1.b | §1 | Standalone heimdall rejected as authority for accepted task direction; role given to delegation records | Saga (D17) / Odin (D20 bridge) | DECISIONS.md D10, D20 | locked | — |
| §1.c | §1 | Bragi destination consolidation with muninn deferred until muninn is active | Saga / Operator | DECISIONS.md open questions (§5.4) | open | — |
| §1.d | §1 | Saga not packaged primarily as an MCP server; local API with client library, MCP optional adapter | Saga | pinned Saga contract | locked | — |
| §2 | §2 | Evaluation of the three rounds of feedback | — | — | historical | Each adopted point is restated in the decision it produced. Retained qualifications: named competing products unverified; SDK compatibility with interactive-only behaviours not assumed (D7.7); Herdr's automation API not reviewed (§5.8); April billing comments stay until re-test (Saga) |
| §4.a | §4 | Components to build on: Agent SDK, Codex CLI (second worker, candidate second Odin adapter), braid, a System One provider, Pi, Messages API only if forced | Odin (Odin's harness choices); Saga (worker runtimes) | DECISIONS.md §3 (closing paragraph) | locked | — |
| §4.b | §4 | Competing products: Odin competes on delegated authority, verifiable outcomes, inspectable history and reviewed self-change | Odin | DECISIONS.md D0, §3 | locked | Hosted products named in feedback unverified |
| §4.c | §4 | Saga clients: Odin first, CLI second, existing agent third; worker harnesses by worker contract | Saga | — | locked | — |

## D0–D24

### SAGA-2026-10-D0 — Product scope and promise (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D0.1 | Odin's product statement: personal agent for long-term technical projects, context across interruptions, coordinates specialist workers, evidence and decisions within explicitly delegated authority | Odin | DECISIONS.md D0; README | locked | — |
| D0.2 | Saga's product statement | Saga | DECISIONS.md D0 (context only) | locked | — |
| D0.3 | Initial audience: one technically capable individual managing several projects, willing to operate a local service | Odin | DECISIONS.md D0; BP §2 | locked | Saga may state its own audience |
| D0.4a | General life administration out of scope; adding it is a product decision, not a feature | Odin | DECISIONS.md D0; BP §2 | locked | — |
| D0.4b | Such a connector needs its own authority boundary (D2) | Saga | — (see D2.3) | locked | — |
| D0.5 | Desktop control is an optional later capability under D21, never initial product | Odin | DECISIONS.md D0, D21 | locked | — |
| D0.6 | Differentiation: operator-controlled infrastructure, explicit delegation, verifiable outcomes, inspectable history, reviewed changes to working methods; table stakes not claimed | Odin | DECISIONS.md D0 | locked | — |
| D0.7 | Accurate deployment description: locally operated state and execution, hosted inference | Shared rule | DECISIONS.md D0; README | locked | Each repo owns its own wording |
| D0.8 | Billing promise: subscription-first with bounded, explicitly configured API spending; never "no API costs" | Shared rule | DECISIONS.md D0, D24 | locked | — |

### SAGA-2026-10-D1 — Products and boundary (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D1.1 | Odin product row: service plus harness integration package; hosts Odin, Mimir review sessions, subagents; owns commitments, memory, event intake, session lifecycle, delegation coordination, review coordination, outcome verification, proposing changes to its methods; in-session reasoning belongs to the harness | Odin | DECISIONS.md D1; BP §3 | locked | — |
| D1.2 | Saga product row: governed execution service; owns runs, workers, images and hooks, policy, events, delegation records, Bragi, Eir | Saga | DECISIONS.md D1 (context) | locked | — |
| D1.3 | Odin reaches Saga only through tools backed by the independently running Saga service | Odin (consumer obligation) | DECISIONS.md D1; IO §1, §10 | locked | — |
| D1.4a | Run durability: lost connection loses no run; Odin restart does not restart workers; retried submission does not duplicate | Saga | pinned Saga contract | locked | — |
| D1.4b | Odin's side of D1.4: stable request id as idempotency key, cursor resumption, no relaunch on restart | Odin | IO §9; AC-01, AC-03 | locked | — |

### SAGA-2026-10-D2 — Enforcement lives in Saga, as two guarantees (locked; Saga)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D2.1 | Run admission: Saga validates launch configuration, approved artifacts by hash, Mimir verdict bound to request id, operator authorization bound to the shown hash, delegation limits | Saga | DECISIONS.md D2 (obligations); IO §6 `stage_run`, `submit_run`; IO Appendix B B-02 | locked | Odin obligation: submit the request id preallocated by `stage_run` with `prd_digest`, `launch_config_digest`, verdict and approval covering all three (review B3, B6); `stage_run` is feedback only. Envelope and encoding open at Saga (GAP-04, GAP-07) |
| D2.2 | Action authority, first release: repository-scoped push, no other secrets unless named, firewall egress | Saga | IO §7 implementation-worker profile (context) | locked | — |
| D2.3 | Any connector acting outside the container needs its own enforcement boundary first; admission never implies authority | Saga | DECISIONS.md D2 (obligation) | locked | Odin obligation: never offer such a connector to an agent before its boundary exists |
| D2.4a | Saga verifies the reviewer identity key on every verdict | Saga | pinned Saga contract | locked | — |
| D2.4b | The reviewer key is held by the harness side and never exposed to Odin's turns | Odin | IO §7 reviewer profile, tool execution isolation, §10 Mimir | locked | Command and file tools isolated and redacted, fail closed (review B7; design only) |
| D2.5 | Mimir reviews quality; Saga enforces authority; a shared process is convenience, not a security boundary; a separate process is available | Odin (Mimir deployment) | DECISIONS.md D2, D8; BP §6 | locked | ODIN-ADR-013 reads "Mimir" as the reviewer positions and takes the separate-process option for the signer; clause unchanged |
| D2.6 | Four stop operations, each an API call and an operator command: pause planner, stop runs, disable schedules, revoke authority | Saga (definition of record) | DECISIONS.md D2 (obligations); IO §10 operator; AC-10 | locked | Pause planner and disable schedules act on Odin's state; Odin implements them as consumer obligations. See issue X-2 in DECISIONS.md |
| D2.7 | `/stop <delegation>` performs all four and reports; a global kill switch does it for everything | Saga (stop operation); Odin (operator command and report) | IO §10 operator; AC-10, AC-27 | locked | Lost backend connection reported as uncertain, never success |

### SAGA-2026-10-D3 — Two pluggability contracts (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D3.1 | Orchestrator contract = the Saga API: submit, read status/results/evidence, guidance, cancel, resumable event cursor, review and maintenance requests, delegation reads and proposals | Saga (producer) | pinned Saga contract; IO Appendix B (required capabilities) | locked | Odin consumes; never edits the pinned copy |
| D3.2 | Client order: Odin first, a CLI second, an existing agent third (D18) | Saga | — | locked | — |
| D3.3 | Worker contract per image: PRD, iteration, status and journal, hooks, guidance, push; Claude Code first, Codex CLI second | Saga | — | locked | — |
| D3.4a | Workers raise a structured request for operator input with request id, assignment, decision, options, what answering authorizes | Saga | pinned Saga contract | locked | — |
| D3.4b | Odin delivers such requests to the operator queue preserving those fields (D20.9) | Odin | IO §4, §10 workers; AC-07 | locked | — |

### SAGA-2026-10-D4 — Ledgers (locked; Saga)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D4.1 | Saga's run ledger is the authoritative record of delegations, submissions, approvals, states, limits, evidence and events, with a monotonic event sequence | Saga | pinned Saga contract | locked | — |
| D4.2 | Odin's chat log is Odin's memory and is never consulted to decide whether a run was approved or completed | Odin (consumer obligation) | DECISIONS.md D4; IO §1, §5 | locked | — |
| D4.3 | After restart Odin replays the cursor from the last sequence it logged | Odin (consumer obligation) | IO §9 recovery; AC-03 | locked | — |

### SAGA-2026-10-D5 — Completion semantics (locked; Saga)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D5.1 | Run states `submitted` → `accepted` → `queued` → `started` → `terminated` → `verified` or `failed` → `closed`; side states `cancelled`, `limit-paused` | Saga | pinned Saga contract; IO Appendix C (Odin event kinds) | locked | — |
| D5.2 | `depends_on` waits on `verified` | Saga | — | locked | Odin's lifecycle handler releases its own dependencies on `verified` (IO §4) |
| D5.3 | The launcher's `approved` becomes `accepted`/`started` and never means success | Saga | IO §5 (treat as claims) | locked | — |
| D5.4 | A false completion report is a defect of the evidence rules, tracked as a D18 measure | Saga (evidence rules); Odin (measure) | AS §3; DECISIONS.md D18 | locked | — |
| D5.5 | Odin keeps assignment and session lifecycle separate from run states; idle, a finished tool call or "done" is not `verified` | Odin (consumer obligation) | BP §4; IO §4; AC-13, AC-14 | locked | Derived from D5 in the blueprint |

### SAGA-2026-10-D6 — Side effects (locked; shared rule)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D6.1 | At-least-once delivery with an idempotency key per action | Shared rule | IO §9 outbox | locked | Each service owns its own delivery and recovery implementation |
| D6.2 | Destination deduplication where possible | Shared rule | IO §9 destination table | locked | — |
| D6.3 | Explicit `unknown` outcome after a crash between action and record | Shared rule | IO §9; AC-02 | locked | — |
| D6.4 | Reconciliation on restart | Shared rule | IO §9 recovery | locked | — |
| D6.5 | No component claims exactly-once | Shared rule | IO §9; BP §4 | locked | — |

### SAGA-2026-10-D7 — Runtime and memory (runtime locked; memory implementation hypothesis; Odin)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D7.1 | Runtime statement: build on Claude Code through supported interfaces; Odin owns memory, commitments, scheduling, delegation and review coordination; custom Messages API runtime only on measured unmet requirements | Odin | DECISIONS.md D7 | locked | Reverses the first record version's custom-runtime choice (§2) |
| D7.2 | The service starts, resumes and retires sessions through the Agent SDK | Odin | IO §5, §11 | locked | ODIN-ADR-009 permits a service-commanded workstation host; ADR-024/026 permit native executive invocation and development. Full SDK/host delivery remains open |
| D7.3 | Authentication per adapter launch configuration (D24); default planning credential an API key from the linked Console organization; subscription lineage supported | Odin | IO §11 | locked (runtime); default per D24.8a | Default confirmation is open (§5.12) |
| D7.4 | Two loops: service outer loop in ordinary code, harness inner loop | Odin | IO §1; BP §2 | locked | — |
| D7.5 | Resume while context is useful; replace with a fresh briefed session at boundaries | Odin | IO §5 | locked | — |
| D7.6 | Narrow runtime adapter so a second harness can be added (D19); one implementation built and validated first | Odin | IO §11; BP §2 | locked | ODIN-ADR-015 places a fixture-only Pi RPC control after I2; full second adapter stays I5 |
| D7.7 | Interactive-only behaviours (channels, plugin monitors, teammates) not relied on; the service supplies its own Telegram adapter and event intake | Odin | IO §11 | locked | ADR-024 permits Remote Control conversation; ADR-026 permits native development tools/integrations/agents; ADR-028 adds an opt-in development channel and completion hook. None turns model-relayed text into authenticated Odin operator commands |
| D7.8 | Memory interface and six requirements | Odin | IO §8 | locked | — |
| D7.9 | UniiChat ideas adapted to the runtime boundary; not promised: fresh call per message, exact prompt layout, cache economics, constant context | Odin | IO §8, §11 | hypothesis | Victor Taelin's design; gist shows no license (§5.5) |
| D7.10 | Implementation stays only if it beats the simpler baseline on D18 memory measures at comparable cost; "nothing is lost" means retained bytes | Odin | IO §8; AS §3 | hypothesis | ODIN-ADR-003 sets rolling summary plus notes and identical fixture retrieval at I5; repeat with live retrieval after I6. No outcome claimed |
| D7.11 | Commitments are not memory; commitment record contents; Saga keeps authority and execution state, Odin keeps commitments and memory | Odin | IO §2; BP §4 | locked | — |
| D7.12 | Retention: redaction as the one exception to append-only; propagation; logged; backups follow policy | Odin | IO §8; AC-26 | locked | Retention defaults open (§5.3) |

### SAGA-2026-10-D8 — Mimir: selective, evidence-based, measured (default; Odin)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D8.1 | When: review where mistakes multiply; routine operations get mechanical checks | Odin | DECISIONS.md D8; BP §6; IO §6 `publish_guidance` | default | Replaces "review every project-shaping decision" (§2). Guidance: routine gets mechanical checks, material its required review, unresolved held (review B4); which results authorize publication open (issue X-7) |
| D8.2 | Mechanical checks first; results given to Mimir as evidence | Odin | IO §10 Mimir | default | — |
| D8.3 | Evidence, not narrative; no exposure to Odin's reasoning; no perpetual reviewer memory; prior verdicts attached deterministically | Odin | IO §10 Mimir | default | Replaces the earlier "precedent view" mode (§2). ODIN-ADR-013 supersedes the single-reviewer reading: two positions, same evidence pack, no view of each other's findings |
| D8.4 | Bounded, actionable findings; five verdicts including `INSUFFICIENT_EVIDENCE`; one review and at most one re-review | Odin | IO §10 Mimir | default | ODIN-ADR-013 keeps the verdict set and bounded rounds; every `FLAG` pair escalates under Saga ADM-7, as do negative results and persistent disagreement. Mixed approving-result serialization awaits I0 |
| D8.5 | Model per review type; Sonnet default; "cheap" earned by evaluation | Odin | IO §10 Mimir | default | Model choice open (§5.2). **Superseded for Odin by ODIN-ADR-013** (hypothesis): two reviewer positions on different model families; model per position open (§5.2) |
| D8.6 | Hard daily caps on review spend and interrupt-class turns | Odin | IO §4 caps | default | — |
| D8.7 | Measured comparison: Odin alone, Odin with equivalent verification budget, Odin plus Mimir | Odin | AS §3 | default | — |

### SAGA-2026-10-D9 — Decision models: bounded judgments, never authority (locked; Odin)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D9.1 | Statement: bounded judgments through an optional tool and approved evaluators; outputs cannot satisfy Saga approval requirements or waive required Mimir review | Odin | DECISIONS.md D9 | locked | Saga enforces approvals regardless (D2.1) |
| D9.2 | `decide(state, questions)`: advisory, provider abstraction, explicit unavailable/invalid status, cannot execute | Odin | IO §6 | locked | — |
| D9.3 | Evaluators: versioned, fixed configuration, registry of hook locations; unsupported locations; operator-intent hook withdrawn | Odin | IO §6 evaluators | locked | The operator-intent hook remains withdrawn. ADR-028 permits next-test and stage planning only for the independent development evaluator; ordinary service-event hooks remain fixed |
| D9.4 | `propose_decider(config)`: approval binds full configuration; replay and shadow before activation; revalidation; one-command rollback | Odin | IO §6 | locked | Renamed from `install_decider` (§2). ADR-028 permits direct opt-in activation of the operator-requested development loop; ordinary evaluator activation and required reviews remain unchanged |
| D9.5 | Safety rules: mandatory checks first; bypass for operator and control messages; typed messages never classified; maximum deferral; confidence is not correctness; sensitivity follows content to the local provider | Odin | IO §4, §6; BP §6 | locked | ODIN-ADR-002 specifies typed triage, bounded digest and visible overdue state under caps; bypass rules unchanged |
| D9.6 | First experiment: journal-attention evaluator in shadow mode against Haiku triage | Odin | IO §6; ROADMAP Phase F | locked | ODIN-ADR-002 clarifies the baseline triage path; shadow output cannot suppress its wakes |

### SAGA-2026-10-D10 — The standalone tools stay separate (locked; Odin consumer, peers own capabilities)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D10.1 | braid: backend for optional `recall`; child process over stdio; never indexes the chat log; after Odin v1 | Odin (consumer); braid (capability) | IO §6 `recall`; EI §7 | locked | Read as "never indexes Odin's active chat" (source §2); `archive` scope read-only through skald (issue X-4, review N7). Braid and skald capabilities still proposed (EC-06, EC-07); I6. **Amended by ODIN-ADR-006**: braid runs as an in-process library over published, scoped namespace data; exclusion of the active chat unchanged |
| D10.2 | skald: optional archiver of Odin's and Mimir's logs via provider adapter and per-line `chat` id; honours redaction | Odin (consumer); skald (capability) | IO §3, §8; EI §6 | locked | **Amended by ODIN-ADR-006**: capture module writes Odin's transcript namespace; skald's archive kept as standalone sink; redaction honoured across namespaces |
| D10.3 | muninn: optional `recall` scope; its ADR-007 claim on typed journals superseded (chat log canonical) | Odin (consumer); muninn | IO §6 | locked | muninn's future open (§5.4) |
| D10.4 | wayland-computer-use: harness-independent desktop capability for a dedicated computer-use worker under D21 | Odin (consumer); WCU (capability) | DECISIONS.md D21; EI §8 | locked | Row as revised by D21 in the source. **Amended by ODIN-ADR-011**: guarded input runs as a gated process of the workstation daemon under a dedicated uid; isolation from planners unchanged; disabled until §5.9 |
| D10.5 | Standalone heimdall: never an authority; optional human-facing continuity surface referencing Odin's commitments; needs a release and green CI | Odin (consumer); heimdall | EI §5 | locked | **Amended by ODIN-ADR-007**: heimdall's task layer retired by import, not connected as a continuity surface; sensors move to the workstation daemon (ODIN-ADR-009) |
| D10.6 | Nothing rolls into Odin; harness core stays generic; Saga-specific tools from the Saga client library; everything else is an adapter | Odin | DECISIONS.md D10 | locked | Client library is a Saga deliverable. Unchanged. Repository consolidation (ODIN-ADR-018) is a proposal pending Saga-side decisions (X-14) |

### SAGA-2026-10-D11 — Eir (locked; Saga, Odin owns its interfaces)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D11.1a | Three loops: Saga retries delivery, reconciles worker state, enforces timeouts; Eir changes code, prompts or configuration through reviewed patches | Saga | — | locked | — |
| D11.1b | Odin's loop: deciding that work needs different guidance | Odin | IO §6 `publish_guidance` | locked | — |
| D11.2 | Complete loop: failure → change → regression check → approval → deployment → measured outcome → rollback; merged PR is a proposal; ledger records the outcome measure | Saga | — | locked | — |
| D11.3 | Eir runs as a Saga task with an operator-invoked path outside Saga's failure domain; the operator is the merge gate | Saga | — | locked | Odin's availability must not be required for this path (BP §3) |
| D11.4 | Odin's interfaces to Eir: failures arrive as `host` events; Odin files maintenance requests; Mimir reviews behaviour-changing Eir patches (D8.1) | Odin | IO §4, §10 Eir; Appendix B B-16 | locked | Requests go only through Saga's task request (D3.1; review N9); webhook-failure routing open (issue X-8) |

### SAGA-2026-10-D12 — Bragi (locked; Saga, Odin owns its interfaces)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D12.1 | Bragi is a model-driven compiler in the Saga repo with the listed inputs and outputs | Saga | — | locked | — |
| D12.2 | Bragi publishes lessons to Odin through the import endpoint | Saga (publisher); Odin (import endpoint) | IO §10 Bragi (`append_note`) | locked | — |
| D12.3 | Odin's history projections are readable inputs for Bragi | Odin | IO §9 projections | locked | — |

### SAGA-2026-10-D13 — Naming (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D13.1 | Rule: Norse names only for persona-bearing, judging agents; functional names for everything deterministic; never reuse a standalone repo's name; myth only in Odin's identity paragraph | Shared rule | AGENTS.md; DECISIONS.md D13 | locked | The `saga-` deliverable prefix is Saga's; no Odin prefix is defined (issue X-5) |
| D13.2a | Odin and Mimir keep their names | Odin | AGENTS.md terminology | locked | Mimir names the reviewer role; one persona or two for the positions is open with X-5 (ODIN-ADR-013) |
| D13.2b | Eir and Bragi keep their names; Bragi loses the "skald" epithet | Saga | — | locked | — |
| D13.3 | worker, run, stream, delegation | Saga (API terms) | AGENTS.md terminology | locked | Odin uses Saga's terms |
| D13.4a | Saga launcher, Saga events | Saga | AGENTS.md terminology | locked | — |
| D13.4b | "the Saga adapter in Odin" | Odin | IO §10 | locked | — |
| D13.5 | Saga renames: keepalive, `worker-hooks/`, `containers/worker-claude/`, `saga/runs/…` topics, launch directories to the API, `commands/` deleted | Saga | — | locked | — |
| D13.6 | `containers/odin/`, image `saga-odin` moves to the `odin` repo | Odin | ROADMAP (code extraction) | locked | Not yet moved; its new name is undecided (issue X-5) |
| D13.7 | Removed metaphors: Huginn and Muninn as journal metaphor; Nidavellir, Midgard, Yggdrasil, Hliðskjálf, Svartalfheim | Shared rule | LEGACY-REQUIREMENTS.md (persona derivation) | locked | Legacy persona still uses them |
| D13.8 | "evaluator" | Odin | AGENTS.md terminology | locked | — |
| D13.9 | Banned synonyms reduced to alternative agent names: overseer, navigator, critic, judge, master | Shared rule | AGENTS.md | locked | — |
| D13.10 | Legacy names remain in history and code until each rename lands | Shared rule | AGENTS.md | locked | — |

### SAGA-2026-10-D14 — Repositories (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D14.1 | Two repositories, `saga` and `odin`; the standalone repos stay where they are | Shared rule | README; DECISIONS.md D14 | locked | Unchanged here. A shared repository needs Saga's record (X-14); ODIN-ADR-018 is not recorded |
| D14.2 | Three changes with different completion criteria: documentation handoff, code extraction, deployment cutover | Shared rule | DECISIONS.md D14; ROADMAP | locked | — |
| D14.3 | The documentation handoff may create `odin` earlier than Phase C as a documentation-first scaffold: design documents, frozen record snapshot, provenance map preserving D-numbers, pinned Saga contract once it exists | Odin | this checkout | locked | Already permits this scaffold; no further amendment needed |
| D14.4 | Code extraction enters in the blueprint's increments | Odin | BP §7; ROADMAP | locked | — |
| D14.5 | Deployment cutover still depends on Saga Phase B | Odin (gate); Saga (provider) | ROADMAP; BP §7 | locked | — |
| D14.6 | Handoff gate: contract held for one review cycle; Saga's producer contract extracted at Saga; decision map written | Shared rule | DECISIONS.md D14; docs/README.md | locked | Gate **not yet satisfied**: final independent review pending (source review CHANGES_REQUIRED). Draft pin bookkeeping complete: producer commit `a84f9ac28a6b4de651fccc057d33a335472f9773` recorded and bytes match canonical draft; target API unimplemented; this map remains a candidate |
| D14.7 | Until the handoff is recorded, Saga remains the document owner | Saga | README; DECISIONS.md header | locked | Lapses only when the handoff is recorded in both repositories |

### SAGA-2026-10-D15 — Development direction and sequencing (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D15.A | Phase A: record, documentation, credits claimed, billing re-test recorded, Saga confirmed active; exit operator sign-off on §5 | Saga | ROADMAP (external dependency) | locked | Documentation handoff is the Odin-side Phase A item |
| D15.B | Phase B: Saga service v1 and minimum enforcement; CLI exit criterion | Saga | ROADMAP gate for I3; IO §13 | locked | — |
| D15.C | Phase C: Odin v1 in the `odin` repo; exit: one project end to end without tmux, meeting Saga's boundary on first live submission; interrupted session replaced without losing the assignment | Odin | ROADMAP; IO §13 | locked | ODIN-ADR-008 reorders I0/I1 content under D14.4; no phase change |
| D15.Da | Phase D: richer Saga policy (TTL, budgets, presence gate, connector boundaries, evidence rules for `verified`) | Saga | ROADMAP (dependency) | locked | — |
| D15.Db | Phase D Odin work: second project, adopt-into-supervision, take-control, ownership rules | Odin | ROADMAP; IO §13 | locked | Listed in the Saga roadmap and contract §13, not in the D15 table row |
| D15.Ea | Phase E: worker contract document, Codex and Pi worker images | Saga | ROADMAP (dependency) | locked | — |
| D15.Eb | Phase E: second Odin harness adapter with capability matrix; Odin runs one assignment through it | Odin | ROADMAP; IO §11, §13 | locked | ODIN-ADR-015 adds a fixture-only Pi control after I2; Phase E delivery unchanged |
| D15.Fa | Phase F: `recall` on braid, `decide`, first evaluator in shadow, skald archiver, observability | Odin | ROADMAP; IO §13 | locked | — |
| D15.Fb | Phase F: Bragi on the new inputs | Saga | — | locked | — |
| D15.G | Phase G: the D18 evaluation and demonstration; results published in the repo | Odin (Odin comparison); Saga (participant) | ROADMAP; AS §3–4 | locked | — |
| D15.8 | B precedes C: Odin v1 is built against the API and its first live project must meet the D0 boundary | Shared rule | DECISIONS.md D15 (Odin-side interpretation); IO §13; ROADMAP; BP §7 | locked | X-1 open: allowing I0–I2 alongside Phase B is Odin's interpretation of source blueprint §7, not recorded in Saga. I3, live runs/submissions, cutover and Phase C exit remain gated on Phase B. Peer placement internally reconciled (X-9); producer sequencing agreement pending |

### SAGA-2026-10-D16 — Documentation (locked; historical except design ownership)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D16.1 | Saga README, CLAUDE.md, docs index, ROADMAP rewritten; supersession banners; public README draft superseded | Saga | — | historical | Marked done in Saga's Phase A roadmap |
| D16.2 | `docs/design/`: Odin I/O contract, harness landscape, research notes | Odin (Odin design and research after handoff) | docs/design/, docs/research/ | locked | The source names "v4"; the captured contract is v7 (stale reference in source) |
| D16.3 | Personas unchanged until Phase C | Saga (existing runtime personas) | LEGACY-REQUIREMENTS.md | locked | Odin derives new personas at code extraction (extraction plan §7) |

### SAGA-2026-10-D17 — Delegation records (locked; Saga)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D17.1 | Delegation is a first-class, versioned object in Saga's ledger: outcome, scope, authority, limits, evidence, escalation, expiry, stop | Saga | pinned Saga contract; IO §2 (Odin reads) | locked | — |
| D17.2 | Odin maintains priorities inside a delegation and proposes changes through `ask_operator` | Odin (consumer obligation) | IO §6 delegation tools | locked | — |
| D17.3 | Saga enforces accepted constraints and scopes every run, limit and stop to a delegation | Saga | — | locked | — |
| D17.4a | A delegation is what Odin remembers as an unresolved commitment | Odin | IO §2 commitment `delegation` ref | locked | — |
| D17.4b | Bragi's periodic review reports on the delegation | Saga | — | locked | — |
| D17.5 | Extends the project wiki and contracts rather than adding a service | Saga | — | locked | — |

### SAGA-2026-10-D18 — Evaluation and the first demonstration (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D18.1 | Comparative experiment: Odin plus Saga against an existing agent plus Saga (Hermes, API key, sandboxed), six measures | Odin (design and report) | AS §3; ROADMAP Phase G | locked | Saga supplies runs and ledger evidence |
| D18.2 | D7 memory hypothesis and D8 Mimir policy judged on the same runs | Odin | AS §3 | locked | — |
| D18.3 | Saga remains valuable if another agent wins | Saga | — | locked | — |
| D18.4 | Every Odin feature switchable; baselines include the native harness alone and with equivalent extra budget | Odin | AS §3 | locked | — |
| D18.5 | First demonstration: the seven-step sustained responsibility | Odin | AS §1 | locked | First delegation open (§5.7). ODIN-ADR-012: step 7 reads "preserved by the chosen carrier" |
| D18.6 | Five required demonstration scenarios | Odin | AS §1–2 (AC-15, AC-03/AC-02, AC-11, AC-14, AC-19/AC-24) | locked | — |

### SAGA-2026-10-D19 — Odin as a supervisory layer over a chosen harness (locked; Odin)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D19.1 | Statement: persistent, supervised work across projects using the harness the operator prefers | Odin | DECISIONS.md D19; README | locked | — |
| D19.2 | Capability contributions in order of importance | Odin | DECISIONS.md D19; BP §2 | locked | — |
| D19.3 | Mimir and decision models are optional; Odin must remain useful with both disabled | Odin | DECISIONS.md D19 | locked | A disabled reviewer never waives required review (AC-22) |
| D19.4 | Adapters publish capability matrices; translate, never reimplement the harness | Odin | IO §11 | locked | — |
| D19.5 | Claude Code first; second adapter (Codex app-server or Pi RPC) early; no universal framework before two | Odin | IO §11; ROADMAP Phase E | locked | Satisfied early by ODIN-ADR-015's fixture-only control |
| D19.6 | Restrained initial product | Odin | DECISIONS.md D19; ROADMAP | locked | — |
| D19.7 | Product is modular and may run without Saga (local backend, D23) for work without external effects; first supported deployment requires Saga Phase B | Odin | DECISIONS.md D19, D23; BP §7 | locked | ADR-026 permits the native development executive without Saga or a managed backend; the supported managed deployment still requires Saga Phase B |

### SAGA-2026-10-D20 — Topology and operator interfaces (locked; Odin, peer bridges)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D20.1 | Three layers: interface, service, agent sessions | Odin | DECISIONS.md D20 | locked | ODIN-ADR-009 clarifies: the service layer includes a workstation daemon acting on the service's command |
| D20.2 | One service; several planning sessions, one owner per project; many worker sessions; Mimir sessions on demand; routine events handled by code | Odin | IO §2, §4; BP §2 | locked | ODIN-ADR-009: sessions may be hosted on the workstation; records and ownership stay in the one service |
| D20.3 | Another planning owner only for separable responsibility or measured bottleneck; separate service instances later | Odin | BP §2 | locked | — |
| D20.4 | Ownership rules for multiple planners | Odin | IO §2; AC-04, AC-16 | locked | — |
| D20.5 | Two operator interfaces, one command path; approvals bound to the proposal whatever the channel; stop works when the model is unresponsive | Odin | IO §10 operator; AC-05, AC-06, AC-10 | locked | **Superseded in part by ODIN-ADR-010**: operator surfaces are adapters on one service API (workspace, Telegram, summoned terminal, bar, notifications, voice later); one command path, binding and stop rules unchanged |
| D20.6 | Native vs interactive terminal integration; capabilities tested and published; workspace "done"/"wait" do not establish completion | Odin | IO §11; EI §4; AC-13 | locked | Herdr API not reviewed (§5.8) |
| D20.7 | Adopt into supervision; take control | Odin | IO §10 operator; AC-11 | locked | — |
| D20.8 | Service path vs model path; handling table | Odin | IO §4 | locked | ODIN-ADR-002 replaces unconditional journal-report wake with typed outcomes and bounded digest. **Amended by ODIN-ADR-010**: workstation observations and capture lifecycle as state-only/log-only sources; attention prompt as a typed outbound effect with caps |
| D20.9 | Structured requests go directly to the operator queue; planner joins only when the answer changes the plan | Odin | IO §4, §10; AC-07 | locked | — |
| D20.10 | Ownership bridge with standalone heimdall: projection, edits route to owner, no second editable copy; new work scheduled with the workspace integration | Odin + heimdall | EI §5; EC-05 | locked | Heimdall's side is heimdall's to adopt. **Superseded for Odin by ODIN-ADR-007**: no bridge; heimdall's task layer imported once and retired. Heimdall's side is heimdall's to record (EC-13) |
| D20.11 | First configuration; then a second project before any further supervisory layer | Odin | ROADMAP; IO §13 | locked | — |

### SAGA-2026-10-D21 — Desktop capability and computer-use work (default; Odin coordination, WCU capability)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D21.1 | Statement: WCU harness-independent; Odin coordinates; decision models interpret bounded text; guards keep their roles | Odin | DECISIONS.md D21 | default | Revises the D10 WCU row (source) |
| D21.2a | WCU responsibility: observe, guarded input, readback, no model decisions | WCU | EI §8 | default | — |
| D21.2b | Computer-use worker's harness interprets screenshots and plans interactions | Odin (assignment) | EI §8 | default | — |
| D21.2c | Odin maintains assignment, schedules desktop access, preserves progress; never reasons about individual clicks | Odin | DECISIONS.md D21 | default | — |
| D21.2d | Decision models and Mimir roles in the workflow | Odin | DECISIONS.md D21 | default | — |
| D21.3 | Desktop assignment only under a delegation naming desktop authority; scoped to named apps; terminals and VM access excluded by default | Odin (assignment rule); Saga (delegation field) | DECISIONS.md D21; IO §7 | default | — |
| D21.4 | Exclusive desktop-control lease enforced at a shared broker or tool boundary | Odin + WCU | EI §8; EC-10; DC-01, DC-02 | default | ODIN-ADR-011 implements the lease in one gated process of the workstation daemon; device-wide exclusivity unverified |
| D21.5 | Capability guards remain in force | WCU | EI §8; DC-03 | default | — |
| D21.6 | Decision-model rules in the workflow component; data to the local provider; first experiment | Odin | EI §8; EC-11; DC-05–DC-07 | default | — |
| D21.7 | Not in the initial product; after Phase F by operator decision | Odin / Operator | ROADMAP; BP §7 I7 | default | Desktop authority open (§5.9) |

### SAGA-2026-10-D22 — Preservation (locked in shape; integration scheduled)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D22.1 | Unit of preservation is a selected project package with the listed contents; project code keeps its own history | Odin | DECISIONS.md D22; EI §9 | locked (shape) | — |
| D22.2 | skald owns full-archive backups; live databases and indexes stay outside git synchronization | skald (backups); Odin (exclusion rule) | EI §9 | locked (shape) | ODIN-ADR-012: full-archive backup ownership moves with the capture module's standalone sink |
| D22.3 | dotprivate carries the package; copied, committed and confirmed-on-remote distinguished; no unconfirmed remote durability | dotprivate (capability); Odin (reporting) | EI §9; AC-24, AC-25 | locked (shape) | **Superseded for Odin by ODIN-ADR-012**: Odin writes the package and runs git with three-state receipts; dotprivate off Odin's path |
| D22.4 | Imported copies are never independent corroboration | Odin | IO §6 `recall`; AC-17 | locked | — |
| D22.5 | dotprivate's selected-files contract is a proposal; integration scheduled (Phase F), not assumed | dotprivate / Odin | ROADMAP; EC-08 | scheduled | Open (§5.10). **Superseded for Odin by ODIN-ADR-012**: EC-08/EC-09 withdrawn (ids kept); the contract remains dotprivate's own question (§5.10) |

### SAGA-2026-10-D23 — Execution backends (locked; Odin, Saga guarantees remain Saga's)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D23.1 | Execution through an explicit backend with a published capability matrix | Odin | IO §2 assignment `backend` | locked | ADR-026 exempts ordinary native executive development from managed backend routing; this supplies no Saga guarantees |
| D23.2 | Saga is the default and the only backend for external effects or needing isolation, limits, durable run records and recovery | Odin (routing rule) | DECISIONS.md D23; BP §7 | locked | ADR-026 exempts operator-directed native development from this Odin routing rule; Saga guarantees and API admission remain Saga-owned |
| D23.3 | Local session backend for work without external effects, with stated missing guarantees | Odin | DECISIONS.md D23; ROADMAP Phase F | locked | ADR-026 permits direct native development beyond research/drafting in version 3; no managed isolation, limits or recovery are claimed |
| D23.4 | The workspace never substitutes for Saga's guarantees; desktop input is a third backend (D21) | Odin | EI §3, §4 | locked | — |

### SAGA-2026-10-D24 — Authentication and billing as adapter configuration (locked; split)

| Clause | Content | Owner | Odin location | Status | Supersession / notes |
|---|---|---|---|---|---|
| D24.1 | Statement: runtime choice, authentication and billing are explicit configuration, independent of supervisory features | Shared rule | DECISIONS.md D24 | locked | — |
| D24.2a | Launch configuration elements for Odin's session classes (planner, reviewer, subagent, compactor, triage, decision models) | Odin | IO §11; Appendix A `PlanningSession.auth` | locked | ODIN-ADR-013 adds a per-position entry |
| D24.2b | Launch configuration elements per worker image | Saga | — | locked | — |
| D24.3 | Credential reference to a protected source; secrets never in prompts, history, briefing or exports | Odin (its sessions); Saga (secret store, workers) | IO §7, §11; AGENTS.md | locked | ADR-009 supplies managed workstation credential placement. ADR-026 retains the dedicated login but waives Odin environment/process isolation for version 3; secrets remain excluded from committed source, prompts and reports |
| D24.4a | Refresh ownership for Odin's planner credentials | Odin | IO §11 | locked | — |
| D24.4b | Refresh ownership for worker lineages (Claude `setup-token` or per-lineage login; Codex `auth.json` per worker) | Saga | — | locked | — |
| D24.4c | Codex app-server externally managed token mode stays experimental, not foundational | Odin (a Codex adapter) | IO §11 | locked | — |
| D24.5 | Quota behaviour: queue or pause at the limit; paid fallback only when configured; shown in `now` and the overview | Odin (its sessions and display); Saga (worker launches) | IO §5 `now`, §11; AC-23 | locked | — |
| D24.6 | Account separation: development login vs managed agents; planning and workers may use different modes | Shared rule | AGENTS.md; IO §11 | locked | — |
| D24.7 | Credential lineages: establish, persist in Saga's secret store, single refresher, retire; launcher injects; no shared writable credential directory after the shadow period | Saga | — | locked | — |
| D24.8a | Default: planning sessions on `api` (included credits) | Odin | DECISIONS.md D24; IO §11, §15 | default, pending operator confirmation | Source heading says locked; source §5 q12 asks for confirmation and the source contract said "proposed" (review N8). Saga's map records the same status as `D24.d`. Billing re-test open |
| D24.8b | Default: Claude workers on `subscription` through the unmodified binary | Saga | — | locked | — |
| D24.8c | Compactor, triage subagents and decision models on their own configured path | Odin | IO §11 | locked | — |
| D24.9 | The shared writable volume is the shadow-period mechanism only; keepalive does not establish refresh ownership | Saga | — | locked | — |
| D24.10 | Promise: subscription-first with bounded, configured API spending | Shared rule | DECISIONS.md D0, D24 | locked | — |

## §5 — Open decisions for the operator

Original question identities are preserved. Items §5.3 and §5.5 are partly
settled by the operator-directed Odin ADRs; moving a question alone does
not answer it.

| Item | Question | Owner | Odin location | Notes |
|---|---|---|---|---|
| §5.1 | Is Saga active again? | Saga / Operator | ROADMAP gates; IO §14 step 2 | Blocks Phase B and therefore I3 |
| §5.2 | Opus 5.5 or Sonnet 5.5 as Odin's default turn model; model for decomposition reviews | Odin / Operator | IO §15 | — |
| §5.3 | Memory baseline for the D7 evaluation; retention defaults | Odin / Operator | ODIN-ADR-003; IO §8, §15 | Comparison baseline and fixture protocol set; freeze run parameters before measurement; production retention defaults open |
| §5.4 | muninn: a `recall` scope, Bragi's second destination, or retirement | Odin + Saga / Operator | IO §15 | — |
| §5.5 | Own-project license choice and third-party reuse terms | Shared / Operator | ODIN-ADR-001; README; LICENSE | Apache-2.0 default, MIT for dotprivate; Odin license added. UniiChat reuse/attribution remains open; no blanket claim about absent peer licenses |
| §5.6 | Claim the Max API credits; a second seat | Operator | ROADMAP (dependency) | Planning sessions' default `api` mode depends on the credits. "Seat" here is the subscription seat; reviewer roles are "positions" (ODIN-ADR-013) |
| §5.7 | The first delegation for the D18 demonstration | Odin / Operator | ROADMAP Phase G | — |
| §5.8 | Herdr's automation API capabilities per adapter | Odin / Operator | EI §4; EC-03 | — |
| §5.9 | Desktop authority in the first year and its applications | Odin / Operator | DECISIONS.md D21 | ODIN-ADR-011 places the gated input process; nothing enabled until decided |
| §5.10 | dotprivate's selected-files contract | dotprivate / Operator | EI §9; EC-08 | ODIN-ADR-012 removes dotprivate from Odin's path; the question is dotprivate's |
| §5.11 | skald retrieval for the archive scope | skald / Operator | EI §6; EC-06 | — |
| §5.12a | `api` as the default for planning sessions | Odin / Operator | IO §11, §15 | — |
| §5.12b | Per-worker token provisioning once the re-test confirms `setup-token` | Saga / Operator | — | — |

## Supersessions recorded by the extraction

| Superseded text | Replaced by | Reason |
|---|---|---|
| I/O contract v7 header: "where it conflicts, the blueprint's statement of intent and the decision record win" | Odin authority order: decisions, operational contract, blueprint, roadmap | Extraction plan §4 |
| Blueprint §1 reading order (blueprint first, decision record fourth) | Same Odin authority order | Extraction plan §4 |
| I/O contract Appendix B (Saga API) and §10 worker transport (per-run MQTT relay, broker ACL, topics) | Pinned Saga contract plus Odin's required-capabilities appendix and consumer obligations | Extraction plan §3, §5; the producer owns its interface |
| "Saga's decision/design files are uncommitted" and "this file was untracked" statements | Extraction provenance (clean capture at `14fdab3`) | Source captured clean; see the history wrapper |

| v7 `submit_run(request_id, prd_digest, verdict_id, approval_hash)`; `stage_run` "assigns the request id"; the non-ULID example | `stage_run` preallocates a ULID request id before review; `submit_run` binds it with both digests, verdict and approval | D2.1 governs (review B3, B6) |
| v7 `publish_guidance` "requires an approved `guidance` verdict or `APPROVE_UNCHANGED` semantics" | Routine and material classes; no verdict string alone authorizes; unresolved guidance held | D8.1 governs (review B4; issue X-7 still open on semantics) |
| v7 outbox MQTT row and `emit_event` to `saga/events/<kind>` | Saga reconciles guidance and reports `superseded` through the API; `emit_event` local; B-14 withdrawn | D1.3 governs (review B5) |
| v7 `shell(cmd)` "inside Odin's environment" | Isolated planner workspace, redacted results, fail closed | D2.4b, D24.3 govern (review B7) |
| v7 Eir backlog via `write_file` and the Gitea outbox row | Saga's task request (B-16) | D3.1 governs (review N9) |
| Blueprint §7 placement of Herdr (I4), skald enrollment (I4), braid and skald history (I5) | Herdr read-only inspection I3, adapter I4; braid and skald I6 | D15, D10, D20 govern (review B2) |

These are corrections of design documents to existing decisions,
recorded in [`REVIEW-RESOLUTIONS.md`](REVIEW-RESOLUTIONS.md). No
decision clause has been superseded on its merits by this extraction.

## Odin decisions after bootstrap

These operator-directed decisions are distinct from the original extraction
dispositions above. ADR-001 to 005 (2026-10-14) correct and configure;
ADR-006 to 015 (2026-10-16) are the first to supersede or amend inherited
clauses Odin owns. None amends Saga-owned contracts or records the
formal handoff. See [DECISIONS.md §4](../DECISIONS.md#4-odin-decisions-odin-adr).

| Decision | Status | Inherited relationship | Operational locations |
|---|---|---|---|
| ODIN-ADR-001 | locked | Resolves Odin's source §5.5 license choice; retains D7.9 third-party attribution/reuse question | README, LICENSE, source question §5.5 above |
| ODIN-ADR-002 | locked design correction | Operationalizes D9.5–D9.6 and D20.8; supersedes extracted IO §4/§5 unconditional journal-triage wake, without weakening mandatory-event or maximum-age rules | IO §4–§5, BP §5–§6, AC-31–AC-32 |
| ODIN-ADR-003 | default evaluation configuration | Sets source §5.3 baseline/protocol for D7.10 and D18; retention defaults remain open; D10/D15 integration order unchanged | IO §8/§13, BP §6–§7, ROADMAP I5/I6, AS §3 |
| ODIN-ADR-004 | default design; activation still gated | Refines D9.3–D9.6, D20.8–D20.9 and ADR-002; retains four hooks/operator exclusion; code selects stable session classes under D7/D24 | IO §5–§6, BP §6, ROADMAP I6, AC-33/AC-36 |
| ODIN-ADR-005 | default experiment configuration | Adds trial settings and failure/request-budget checks for D7.9–D7.10 and D18; cache-fix source inspected at `3c190e0`, runtime regressions pending; compactor context scope open (X-10); no transferred cache claims or proven effort optimum | IO §8/§12, BP §6, ROADMAP I2/I3, AC-34–AC-35, AS §3; OPTCHAT-CACHE-REVIEW.md |
| ODIN-ADR-006 | default design | Amends D10.1 and D10.2 delivery modes; preserves D4, D6.5, D7.11–D7.12, D22.2, X-4 reading; execution ledger mirrored read-only, never written by Odin | IO §1, §3, §9, Appendix A; EI preamble; X-11; proposed AC-41 |
| ODIN-ADR-007 | locked direction; migration not designed | Supersedes D20.10 for Odin; amends D10.5; consistent with §1.b, D7.11; EC-05 and AC-20 withdrawn (ids kept); source-side edit refusal required for retirement under EC-13/G-10 | IO §2, §14, Appendix A; BP §3; EI §5; EC-13; proposed AC-38 |
| ODIN-ADR-008 | locked sequencing | Within D14.4 and D15; restates X-9; no phase or gate change | BP §7; IO §13; ROADMAP I0/I1; README; AGENTS.md §1 |
| ODIN-ADR-009 | default design | Clarifies D7.2, D20.1–D20.2; amends D24.3 for Odin's classes; preserves D24.4a, D24.6, D23.3 | IO §2, §5, §7, §11, Appendix A; BP §2; X-12; proposed AC-37 |
| ODIN-ADR-010 | default design; voice backlog | Supersedes D20.5 "two interfaces" in part; amends D20.8; redefines L-PU-1; preserves D9.3, D9.5, D20.9, D20.11, ADR-002/004 | IO §3, §4, §6, Appendix C; BP §5; LEGACY-REQUIREMENTS L-PU-1, L-VT; X-13; proposed AC-39 |
| ODIN-ADR-011 | default; disabled until §5.9 | Amends D10.4 placement; implements D21.4; preserves D0.5, D2.3, D21.5–D21.7, D23.4 | EI §8; EC-10, EC-16; ROADMAP I7; DC-01–DC-08 |
| ODIN-ADR-012 | locked direction; carrier undecided | Supersedes D22.3 and D22.5 for Odin; preserves D22.1, D22.2 (ownership moves with capture), D22.4; EC-08/EC-09 withdrawn (ids kept) | EI §9; ROADMAP Phase F; AC-24/AC-25 retargeted |
| ODIN-ADR-013 | hypothesis | Supersedes D8.5 and the single-reviewer reading of D8.3–D8.4; keeps D8.1–D8.2, D8.6–D8.7; D2.5 unchanged (its "Mimir" reads as the reviewer positions; separate-process option taken); D19.3 kept; FLAG pairs escalate under Saga ADM-7 | IO §10 review; BP §6; AS §3; D24.2a; X-13; AC-22 re-scoped; proposed AC-40 |
| ODIN-ADR-014 | default; evidence only | Amends ODIN-ADR-004; keeps four hooks, no silent downshift, no learned router; I0 defines the workload-class configuration schema | IO §5, Appendix A; AS §3 |
| ODIN-ADR-015 | locked experiment placement; fixture-only | Amends D15.Eb timing for a control only; honours D7.6; satisfies D19.5; replaces the roadmap's Codex proposal | ROADMAP Phase C; IO §11, §13; BP §7 |
| ODIN-ADR-024 | operator-authorized bounded pilot; launch restrictions superseded by ADR-026 for version 3 | Amends D7.2 invocation and D7.7 transport only for native Fable executive conversation; retains service record authority, credential separation and worker/producer gates | [Executive pilot](../EXECUTIVE-PILOT.md), AGENTS.md §1/§4 |
| ODIN-ADR-025 | operator-authorized pilot extension; native restriction superseded by ADR-026 for version 3 | Refines ADR-024's tool boundary and ADR-023's synthetic-memory scope for read-only checkout access and operator-selected committed repository evidence | [Executive pilot](../EXECUTIVE-PILOT.md), AGENTS.md §1 |
| ODIN-ADR-026 | operator-authorized native development profile | Supersedes ADR-024/025 launch and proposal-only restrictions and ADR-022/023 native-child restrictions for version 3; amends Odin-owned D7.2/D7.7, D19.7/D23.1–D23.3 routing and D24.3 process isolation; preserves Saga producer authority and MCP record semantics | [Executive pilot](../EXECUTIVE-PILOT.md), IO §7/§11, AGENTS.md §1/§4/§5/§6 |
| ODIN-ADR-027 | operator-authorized local delegation path | Amends ADR-024's no-delegated-execution bridge rule for the version 3 executive's local-backend sessions; applies D23.3, D7.11 and D19.4; does not deliver ADR-009's managed session host, X-15 child dispatch, ADR-015 or I5 | [Executive pilot](../EXECUTIVE-PILOT.md), IO §2/§11, AGENTS.md §1 |
| ODIN-ADR-028 | operator-authorized development evaluator and loop | Extends ADR-026 and D7.7 transport; amends D9.3 planning/decomposition exclusion and D9.4 activation only for the configured development loop; preserves required Mimir review, Saga authority and direct operator control | [Development loop](../DEVELOPMENT-LOOP.md), AGENTS.md §1/§4 |
| ODIN-ADR-031 | operator-authorized local experiment | Refines ADR-027/028 routing and ADR-005 context work; adds observed accounting and future-admission controls, preserves D7 authority and all producer/review boundaries | [Usage and routing](../USAGE-AND-ROUTING.md) |
| ODIN-ADR-032 | operator-authorized local experiment | Extends Odin-owned D7.7 and ADR-026/027/028 native development transport with opt-in peer messaging; preserves D6 recovery, D7 commitment authority, D24 and producer boundaries | [Native peer messaging](../NATIVE-PEER-MESSAGING.md) |
| ODIN-ADR-033 | operator-authorized executive delegation | Amends ADR-026 direct implementation for the selected executive role and ADR-031 existing-loop routing; preserves D7 authority, bounds, identity and all producer/review guarantees | [Usage and routing](../USAGE-AND-ROUTING.md) |
| ODIN-ADR-030 | operator-authorized visibility and attention | Adds durable notices, model-attributed acknowledgement and deadline attention to ADR-028's loop; preserves D9.5 operator routing, controller/native-process distinction and every review boundary | [Development loop](../DEVELOPMENT-LOOP.md#notices-and-attention), `schemas/development-loop-notice.schema.json` |
| ODIN-ADR-029 | operator-authorized evidence format | Adds structured execution receipts and their validation to ADR-028's evidence workflow; preserves D7.11 commitment truth, D19.4 capability statements and every Saga/review boundary | [Development loop](../DEVELOPMENT-LOOP.md#execution-receipts), `schemas/execution-receipt.schema.json` |

ODIN-ADR-015 replaces the earlier Codex adapter proposal in ROADMAP Phase C
with a fixture-only Pi RPC control; full second-adapter delivery remains I5.

## Local product implementation

ODIN-ADR-023 records the operator-requested local continuity and memory slice.
It operationalizes D6/D7/D18 and ADR-009/010/020/022, with a local view during
I1/I2 preparation. It does not supersede the full I4 view/import, I5 memory
comparison, I6 retrieval, producer contracts or live launch gates. See
[execution status](../PRODUCT-IMPLEMENTATION-STATUS.md) and
[ADR-023](../DECISIONS.md#odin-adr-023--local-continuity-and-attributed-memory).

ODIN-ADR-024 adds a bounded live conversation path beyond ADR-023's synthetic
scope: native Claude Code with Remote Control and a project-bound MCP bridge.
Native messages are conversation, not authenticated Odin operator commands.
The service's reports stay unverified and unapplied. The full SDK, daemon,
worker execution, peer feeds and production acceptance remain open; see the
[pilot runbook](../EXECUTIVE-PILOT.md) and
[ADR-024](../DECISIONS.md#odin-adr-024--native-fable-executive-conversation-pilot).

ODIN-ADR-025 adds two evidence paths to that pilot: explicitly enabled native
read tools for current checkout files, and operator-imported, revision-pinned
repository sources in the persistent local store. It does not enable edits,
worker execution or autonomous application of improvements. See
[ADR-025](../DECISIONS.md#odin-adr-025--executive-repository-evidence-access).

ODIN-ADR-026 makes version 3 the operator-authorized development extension:
normal native tools and agents, permission bypass, real checkout/HOME and
inherited environment. The earlier pilot restrictions remain only for
versions 1 and 2. Native development work does not depend on fake Saga or a
service-managed worker, while MCP reports, exact evidence and Saga's own
interfaces retain their semantics. See
[ADR-026](../DECISIONS.md#odin-adr-026--native-executive-development-access).

ODIN-ADR-027 adds the executive's delegation path on the D23.3 local backend:
one accountable planning session per project, commitments and local
assignments owned by it, detached non-interactive Claude Code or Codex turns,
explicit executive acceptance and recovery after restart. It states its
missing guarantees and leaves the managed session host, child dispatch and
second-adapter gates open. See
[ADR-027](../DECISIONS.md#odin-adr-027--executive-delegation-sessions-on-the-local-backend).

ODIN-ADR-028 adds an independent development evaluator and a deterministic
development loop controller. It returns tests through an opt-in channel to
the existing native executive and captures final responses through a native
hook, with durable round identity and operator pause/stop. Evaluator judgment
is separate from executive work and from Mimir's required-review role.
Configuration and local tests do not prove channel availability or a live
autonomous loop; see [the runbook](../DEVELOPMENT-LOOP.md) and
[ADR-028](../DECISIONS.md#odin-adr-028--independent-development-evaluator-and-feedback-loop).

ODIN-ADR-029 makes command execution evidence a versioned, schema-validated
receipt collected from repository and process observations, validated
deterministically by the loop controller and inspected independently by the
evaluator. A receipt is attributed local evidence with documented coverage,
privacy and concurrency limits; see
[ADR-029](../DECISIONS.md#odin-adr-029--structured-execution-receipts-as-attributed-local-evidence).

ODIN-ADR-030 adds durable completion, failure, intervention, stop and stall
notices to the development loop, delivered at least once through the existing
channel until the executive acknowledges them, plus optional per-loop
deadlines whose attention observations never redispatch or terminate work; see
[ADR-030](../DECISIONS.md#odin-adr-030--durable-loop-notices-and-conservative-attention).

## Clauses superseded or amended by Odin ADRs

The extraction superseded no clause on its merits. The operator's
consolidation direction of 2026-10-16 and bounded pilot of 2026-10-19 did,
for clauses Odin owns. The carried
text in `DECISIONS.md` stays verbatim with an ownership note; the rows above
carry the same supersession in their last column.

| Clause | Effect | By |
|---|---|---|
| D7.2 invocation; D7.7 interactive-only exclusion | amended for native conversation and development executive profiles | ODIN-ADR-024/026 |
| D19.7; D23.1–D23.3 Odin routing; D24.3 Odin process isolation | amended for version 3 native development only; Saga guarantees unchanged | ODIN-ADR-026 |
| ADR-024/025 restricted launch and proposal-only rules; ADR-022/023 native-child restriction | superseded for version 3 native development only | ODIN-ADR-026 |
| ADR-024 bridge rule excluding delegated execution | amended for the version 3 executive's local-backend delegation sessions only | ODIN-ADR-027 |
| D9.3 planning/decomposition exclusion; D9.4 replay/shadow activation | amended only for the operator-configured development evaluator and loop | ODIN-ADR-028 |
| D8.5; single-reviewer reading of D8.3–D8.4 | superseded (hypothesis) | ODIN-ADR-013 |
| D10.1, D10.2 delivery modes | amended | ODIN-ADR-006 |
| D10.4 placement | amended | ODIN-ADR-011 |
| D10.5 | amended | ODIN-ADR-007 |
| D20.5 "two operator interfaces" | superseded in part | ODIN-ADR-010 |
| D20.8 handling table | amended | ODIN-ADR-010 |
| D20.10 | superseded for Odin | ODIN-ADR-007 |
| D22.3, D22.5 | superseded for Odin | ODIN-ADR-012 |
| D24.3 (Odin's classes) | amended | ODIN-ADR-009 |
| D15.Eb timing | amended (control only; D7.6 honoured) | ODIN-ADR-015 |
| I0/I1 content under D14.4 | reordered | ODIN-ADR-008 |
| ODIN-ADR-004 | amended | ODIN-ADR-014 |

**Not in effect, not recorded:** ODIN-ADR-016 to 019 (execution backend
placement, Bragi and Eir hosting, repository consolidation, deliverable names)
are drafts in `design/CONSOLIDATION-PLAN.md` and
`research/consolidation-2026-10/decision-record-impact.md`. They wait on
decisions recorded in Saga's repository (issue X-14). D1.2, D2, D3.3, D4,
D10.6, D11, D12.1, D13.1, D14.1, D14.7, D15.B and D17 stand as carried.
