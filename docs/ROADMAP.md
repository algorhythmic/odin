# Odin roadmap

The [product implementation status](PRODUCT-IMPLEMENTATION-STATUS.md)
tracks the ADR-023 local continuity, memory and session-boundary slice.
It supplies additional component evidence; full I2/I3 exits and the
producer/operator gates below remain open.

Progress against the inherited sequence. The phases (A to G) and their
exit criteria are decided in D15; the increments (I0 to I7) are the
[blueprint's](design/ODIN-IMPLEMENTATION-BLUEPRINT.md) §7; the
phase-to-increment mapping is the
[I/O contract's](design/ODIN-IO-CONTRACT.md) §13. This file tracks them
and does not change their order. Where it conflicts with those
documents, they win ([`DECISIONS.md`](DECISIONS.md) authority order).
Old phase numbers from legacy feature documents are not commitments
([`provenance/LEGACY-REQUIREMENTS.md`](provenance/LEGACY-REQUIREMENTS.md)).

I0 is partially implemented: the unaffected record schemas and event
envelope, shared synthetic fixtures, independent Go/Python validators and
pure duplicate/stale/unknown checks are in [`runtime/`](../runtime/README.md).
I0's full exit remains open, including X-7 and the Review/guidance schemas.
I1 has a local fake-backend service foundation, with full Appendix B compatibility
still open. Some I2 components have local prototypes; I2–I7 exits are incomplete.
Checked items below are documentation or local component evidence only. See
[implementation status](IMPLEMENTATION-STATUS.md) for runnable checks and limits.

## Where to start

**First task: I0, contracts and fixtures:** the versioned event
envelope and namespaces and the record schemas, validated by both the
Go and the Python implementation against the same fixture set
(ODIN-ADR-008). The envelope and unaffected record schemas may begin now
without the consolidation decisions G-9 and G-10. **X-7 must be resolved
before writing the Review/guidance schemas in I0** (`DECISIONS.md` §5);
the fail-closed guidance rule does not close that semantic question or
remove its deadline. I0 is not complete until its review-schema dependency
and shared-fixture exit are met. ADR-021 chooses a local X-11 layout; production process and failure-domain checks remain open. Then I1
(service foundation) and I2
(first harness), both non-production, against a fake Saga backend that
implements the I/O contract's Appendix B and is never presented as
Saga. **I3, any live delegated run and any live Saga
submission wait for Saga Phase B's exit criterion and minimum
enforcement.** Allowing I0–I2 alongside Phase B is Odin's interpretation
of the source blueprint, recorded under D15 in `DECISIONS.md`. Saga has
not recorded it; X-1 remains open for reconciliation with Saga's stricter
phase wording (review finding B2). It is not a jointly approved exception.

## Dependency gates

| Gate | Owner | Blocks | State |
|---|---|---|---|
| G-1 Documentation handoff recorded (D14.6: contract held one review cycle, Saga producer contract extracted, decision map written) | Saga + Odin | Odin becoming the document owner | Source review returned CHANGES_REQUIRED ([findings](provenance/SOURCE-REVIEW.md)); corrections applied ([resolutions](provenance/REVIEW-RESOLUTIONS.md)); re-review pending; not recorded |
| G-2 Saga contract pinned at `contracts/saga/2026-10-14-14fdab3/` | Saga (producer), copied into Odin | The Saga adapter's compatibility checks | Pin bookkeeping complete: `0.1.1-draft`, producer commit `a84f9ac28a6b4de651fccc057d33a335472f9773` recorded; digest matched the canonical draft at extraction. Appendix B's document check (X-3) now also records the worker-event delivery gap in B-12; producer resolution and a repin are still required. Target API unimplemented per the pin; formal review remains G-1 |
| G-3 Saga confirmed active (open §5.1) | Operator | Phase B, migration step 2 | Open |
| G-4 Saga Phase B exit: CLI submits, watches, guides, stops and cancels; refused for the same reasons Odin would be; `/stop` stops a delegation and reports | Saga | I3, live runs, deployment cutover (D14.5) | Not started |
| G-5 Billing and auth re-test recorded; Max API credits claimed (open §5.6, §5.12) | Saga / Operator | Planning-session `api` default in production (D24.8a: default, pending operator confirmation) | Open; no billing test has run |
| G-6 Saga Phase D policy (TTL, budgets, presence gate, verification policies) | Saga | Phase D exit (identical policy for CLI and Odin) | Not started |
| G-7 Saga Phase E worker contract and Codex image | Saga | Phase E exit (Codex run under the same hooks and ledger) | Not started |
| G-8 Peer interfaces still consumed from a peer (EC-03, EC-04, EC-06, EC-07, EC-10 to EC-12); EC-05, EC-08 and EC-09 withdrawn by ODIN-ADR-007 and 012, ids kept | Herdr, skald, braid, WCU, each data-owning consumer | The corresponding I3 to I7 integrations (Herdr read-only inspection in I3); never the core proof. Peer-side retirements and module moves are G-10 | Proposed only |
| G-9 Saga-side decisions in X-14 recorded in Saga's repository (shared repository and release train, worker intake replacing MQTT, Bragi and Eir, names and prefix, the D14 handoff) and a new Saga contract version pinned here, with Appendix B rechecked (X-3) | Operator (in Saga); Saga (producer); Odin (repin) | ODIN-ADR-016 to 019, the shared repository and any repository import | Open; nothing recorded in Saga; ODIN-ADR-016 to 019 not recorded |
| G-10 Peer-repository decisions recorded (EC-13 to EC-16): heimdall retires its task layer, skald's capture library gains a sink interface, braid is embedded as a library, WCU's guarded input moves to the workstation daemon | Operator, in heimdall, skald, braid and wayland-computer-use | Retiring heimdall's task layer (its import into commitments), importing capture as a module, embedding braid, moving WCU input | Open; not recorded in any peer |
| G-11 Import complete: every former binary builds from the trunk | Operator + Odin | The consolidated release train | Not started; waits on G-9 and G-10 and applies only if the shared repository is decided |

The `G-n` gates above are this roadmap's. G-9 to G-11 come from the
[consolidation plan](#consolidation-plan); none of them blocks I0 to I2,
which import no peer code.
The source review's `G1` to `G7` are implementation gates, listed in
their own table below.

## Implementation gates from the source review

The source review's gaps `G1` to `G7` may stay open now but must close
before the work named in the last column ships. Saga carries its parts
as `IG-1` to `IG-7` in its contract (§18). None is closed by the local fixture implementations; the producer-defined
mechanisms and live evidence remain outstanding. R-S1 was raised while
scoping Saga's record and is carried the same way.

| Gate | Subject | Owner | Must close before |
|---|---|---|---|
| G1 | Operator identity at Saga: how Saga tells an operator's approval or answer from one sent by Odin's service or the CLI (Saga GAP-02) | Saga (mechanism, approved by the operator); Odin forwards approvals and answers only through it | Saga declares Phase B minimum enforcement met; Odin's I3 |
| G2 | Stop split: which of D2's four operations Saga's `POST /stop` performs and which Odin performs; the kill switch while Odin is down (issue X-2; Saga GAP-17) | Saga (stop runs, revoke authority, its own schedules); Odin (pause planner, its timers and evaluators) | Saga's Phase B exit; Odin's direct stop in I1 (fake backend) and live in I3 |
| G3 | Restarts and review cost: a restart's new request id needs renewed verdict and approval coverage; whether unchanged digests avoid a fresh model review; the cost (Saga GAP-07, GAP-08) | Saga (binding rule); Odin (renewal in `stage_run`, review-cost accounting) | Saga builds Phase B binding; Odin's I3 |
| G4 | Saga's validator as a dependency: `stage_run` pre-checks only against a schema Saga publishes, never Saga's code (Saga ADM-10) | Saga (published schema); Odin (pre-check against it) | Odin relies on local pre-checks (I3 at the latest); until then there is no pre-check |
| G5 | Planner answers: Saga can enforce only the request kind and the delegation's permission, not "does not change the plan" (Saga RQ-5) | Saga (enforcement); Odin (the judgment, logged and reviewable) | Saga's Phase B request protocol; Odin's I3 |
| G6 | Unconfirmed integrations: Herdr's API (§5.8), skald retrieval (§5.11), braid integration (EC-07); historical heimdall projection (EC-05) and dotprivate selected-files contract (§5.10) withdrawn from Odin's plan | Odin with each remaining peer | Herdr: I3 (read-only inspection) and I4 (adapter); skald and braid: I6. Heimdall import/retirement is I4 under G-10/EC-13, not the withdrawn I5 projection. Dotprivate has no Odin milestone (ODIN-ADR-007, 012) |
| G7 | Unsettled defaults: the billing and auth re-test; the Console spend cap not applying under a subscription login; wake, interrupt and review caps and the coalescing window; memory evaluation run parameters | Operator (re-test, Phase A; G-5); Odin (caps and window from I3's first week of records; spend-cap behaviour before I3; freeze run parameters under ODIN-ADR-003 before I5) | As stated per owner |
| R-S1 | Whether D7 redaction reaches Bragi's outputs compiled from Odin's chat logs (Saga's record §7) | Saga (Bragi's outputs); Odin (redaction propagation, I/O contract §8) | Bragi is given Odin's history projections (cutover, I/O contract §14 step 3); Saga tracks it as SB-08 |

## Phase A — reset (Saga phase; Odin documentation handoff)

- [x] Odin design documents adapted for this repository, with the
      frozen snapshot, decision map and legacy triage (candidate;
      independent re-review pending)
- [x] Source review findings B1–B7 and N1–N11 corrected in the
      documents (`DECISIONS.md` §6,
      [`REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md)); G1–G7
      carried as implementation gates (above)
- [ ] Independent re-review of the corrections (D14's review cycle)
- [ ] Documentation handoff recorded in both repositories (G-1)
- [x] Saga's producer contract pinned here as a draft (G-2); producer
      commit recorded in `SNAPSHOT.json`; pinned bytes match the canonical
      draft. This completes pin bookkeeping, not the handoff review.
- [x] Appendix B checked against Saga's canonical `0.1.1-draft` at
      document level (X-3); worker-event delivery coverage added to the
      recorded B-12 gaps after the audit. This is a gap inventory, not
      producer capability approval; repeat at each repin.
- [ ] Odin-relevant operator answers to the open questions
      (`DECISIONS.md` §3): default models and retention defaults,
      muninn, third-party reuse terms, the first delegation, Herdr, desktop
      authority, dotprivate, skald retrieval, planning billing mode
- [x] Record Apache-2.0 for Odin (MIT exception for dotprivate), typed
      journal triage and the memory-comparison protocol (ODIN-ADR-001–003).
- [x] Record the narrow attention-classifier experiment, deterministic
      session-class routing and Haiku effort/request-budget experiments
      (ODIN-ADR-004–005); provider facts linked in I/O contract §6/§12.
- [x] Record ODIN-ADR-006 to 015 (consolidation, Odin-owned clauses) and
      the decision-map supersessions; X-11 to X-14 opened.
- [ ] Saga-side decisions (X-14) recorded in Saga's repository and the
      peer-side notes (EC-13 to EC-16) recorded in each peer (G-9, G-10).
- Saga-side Phase A items (credits, billing re-test, Saga active) are
  dependencies G-3 and G-5.

## Phase B — Saga service v1 (Saga) with I0 and I1 in Odin

Saga delivers the API and minimum enforcement (I/O contract §13). In
parallel, and non-production, Odin:

- [ ] **I0 contracts and fixtures** (ODIN-ADR-008): the versioned event
      envelope and kinds (Appendix C, EC-01) with the namespaces of
      ODIN-ADR-006; versioned record schemas (I/O contract §2,
      Appendix A) with the changes of ODIN-ADR-007 (commitment
      checkpoints and task decisions, and the mapping from heimdall's
      record types), 009 (`host_offline`, Environment), 013 (reviewer
      positions) and 014 (session-class decisions); fixtures for the
      duplicate, stale and unknown cases, validated by both the Go and
      the Python implementation against the same fixture set. Exit:
      both implementations validate the same fixtures; duplicate, stale
      and unknown cases have explicit semantics; X-7 is resolved before
      the Review/guidance schemas are written; no peer API is invented
      as implemented. Work on the envelope and other unaffected schemas
      does not wait for X-7.
      **Implemented subset:** event envelope/namespaces, unaffected record
      and workload-class schemas, heimdall target mapping, structural
      fixtures and shared duplicate/stale/unknown contract checks. Run
      `scripts/check_runtime.py` as described in
      [`runtime/README.md`](../runtime/README.md). These are schema and pure contract tests. A separate local Python service
      foundation and fake Saga backend now exist; no live harness has been built.
- [ ] **I1 service foundation:** transactional state, event intake and
      cursors, outbox, scheduling, direct stop, CLI (I/O contract §9);
      moved from I0 by ODIN-ADR-008: the adapter capability matrix
      (§11), the fake Saga backend for Appendix B, a synthetic
      three-document fixture (acceptance §1) and the ownership mapping.
      Store topology (X-11) is decided first; G2's stop split is settled
      before the direct-stop work. The fake-backend
      scenarios exercise the execution-ledger mirror's read-only
      property. Exit: restart and replay produce one logical action and
      retain unknown outcomes (AC-01, AC-02, AC-27 against the fake
      backend).

The local experimental portfolio and consultation protocol (ADR-022) is
checked first with synthetic packets, grants, evidence and adapter intents
(AC-45–AC-50). A typed Herdr layout is only a service-state view. Actual
provider calls, voice transcription, identity-bound approval and worker
execution wait for their I2/I3 and X-12/X-13/X-15/Saga gates. ADR-020's model
comparisons remain Phase G work; fixture configuration is not a result.

## Phase C — Odin v1 (Odin)

- [ ] **I2 first harness** (non-production, fake backend): Claude Code
      adapter and integration package; briefing and `zoom`; session
      lifecycle; the planner profile with tool isolation passing its
      check (I/O contract §7; moved from I0 with the profile schemas,
      ODIN-ADR-008). Exit: one bounded assignment survives replacement
      of its session; unsupported operations are explicit (AC-04).
- [ ] **I2 workstation daemon v0** (non-production, fake backend;
      ODIN-ADR-009): the session host, dialling out with a stable host
      identity and heartbeat and acting only on the service's command;
      the environment probe and its Environment record; `host_offline`
      bindings; compositor and Herdr observers; the capture module with
      a local durable spool appending one atomic batch per checkpoint
      into the transcript namespace (ODIN-ADR-006). The local credential
      lineage is decided first (X-12) and is never the development
      login. The Herdr observer and the capture module are fixture work
      here: live Herdr inspection stays I3, skald enrollment and archive
      ingestion stay I6, and importing heimdall or skald code waits on
      G-9 and G-10. Exit: a host going offline leaves its sessions
      unavailable, not failed, and resume reconciles before any new turn
      (proposed AC-37); a captured batch lands atomically with gaps and
      checkpoints preserved (proposed AC-41).
- [ ] **I2 compactor checks:** synthetic fidelity/effort comparison;
      invalid-output recovery and whole-request accounting (AC-34–AC-35).
      Check corrected merge priority, batch boundaries and identical restart
      rendering against the pinned gist inspection. Resolve compactor
      context scope (X-10) and test ambiguous references before I2.
- [x] Inspect the gist cache fix at revision `3c190e0`; record before/after
      hashes and an isolated arithmetic check in
      [`OPTCHAT-CACHE-REVIEW.md`](provenance/OPTCHAT-CACHE-REVIEW.md).
      This completes source inspection, not runtime regression testing.
- [ ] **I3 governed project** (requires G-4; gates G1 to G5): Saga
      Phase B boundary, operator channel (Telegram with hash-bound
      approvals), required review by two reviewer positions with
      service-run combination (ODIN-ADR-013; proposed AC-40),
      verification; **read-only** workspace inspection through Herdr (no
      adopt or take-control); migration import, shadow mode, cutover (I/O
      contract §14 steps 1 to 5). Exit: one real
      project passes admission and finishes with evidence; the CLI and
      Odin face the same refusal rules.
- [ ] **I3 migration evidence:** repeat compaction fidelity/effort checks on
      scoped real fleet JSON and journals before cutover; retain measured
      configuration and cost, never put real history in repository fixtures.
- Phase exit (D15.C): Odin runs one project end to end without tmux,
  meeting Saga's boundary on its first live submission; an interrupted
  session is replaced without losing the outstanding assignment.

**Fixture-only control (ODIN-ADR-015), not an added gate or sequence
change:** after I2's exit, a minimal Pi RPC adapter runs the same bounded
assignment and session replacement against the fake backend, as a control
for the Claude Code adapter, and publishes its capability matrix and gaps.
It tests whether the records and tool boundary are portable early. It is
non-production; record capability gaps and all evidence as fake-backend,
fixture-only evidence; extract no common adapter framework until both
adapters exist. Claude models through Pi use an API key, never the
subscription or Pi's Anthropic OAuth path. The full second adapter and
Phase E's exit remain I5. This control replaces the earlier proposal of a
minimal Codex adapter experiment (the two may run side by side if both are
wanted); it does not resolve X-1 or authorize live execution before
Phase B.

## Phase D — richer policy (Saga), second project (Odin)

- [ ] **I3 → I4:** second project; adopt-into-supervision and
      take-control with pending-effect holds; ownership rules exercised
      (D20; AC-11, AC-12, AC-16).
- [ ] **I4 parallel workspace:** the full Herdr adapter with explicit
      bindings, scoped planning owners, adopt and takeover (EC-03). Exit:
      projects remain separate, bindings are explicit, no pane state is
      mistaken for completion. (Skald enrollment is I6.)
- [ ] **I4 heimdall import and human view v0** (ODIN-ADR-007; requires
      G-10): standalone heimdall's task, checkpoint and decision records
      imported once into commitments, with original identities and
      revisions as provenance and a receipt, and later heimdall-side
      edits refused (I/O contract §14); one human view shows
      commitments, runs and transcripts with their owners attributed.
      Exit: the import is idempotent with a receipt and no second
      editable task store remains (proposed AC-38).
- Phase exit (D15): the CLI and Odin encounter identical policy (G-6).

## Phase E — workers and portability

- [ ] **I5 portability and context:** the second Odin runtime adapter
      (Codex app-server or Pi RPC) with its capability matrix; memory
      comparison against rolling summary plus notes, using identical frozen
      fixture retrieval in both arms (ODIN-ADR-003; D7, D18). Heimdall
      external views (EC-05) are withdrawn by ODIN-ADR-007 (id kept).
      Exit: capability differences and unavailable-peer behaviour pass the
      acceptance scenarios; Odin runs one assignment through the second
      adapter with its missing capabilities stated. Memory evidence is
      labelled a controlled comparison, not live retrieval integration.
      A Codex worker image
      (Saga, G-7) does not test Odin's harness portability.

## Phase F — integrations

- [ ] **I6 optional optimizations and integrations:** `recall` on braid
      as an in-process library (EC-07; ODIN-ADR-006); `decide`;
      `propose_decider` with the evaluator registry; the first evaluator
      (`journal_attention_v1`) in shadow mode; skald source enrollment
      and archive ingestion through the capture module into the
      transcript namespace (EC-04), then the read-only `archive` scope
      when skald's retrieval exists (§5.11, EC-06); Odin's own package
      export with receipts (ODIN-ADR-012; AC-24 and AC-25 retargeted to
      them); local session backend with its capability matrix (D23);
      observability. Selected preservation through dotprivate (EC-08,
      EC-09) is withdrawn from Odin's plan (ids kept), and §5.10 becomes
      dotprivate's own question. Repeat the memory comparison with the
      same live retrieval adapters in both arms and disclose
      configuration changes (ODIN-ADR-003). Exit: routing benefit
      measured; export receipts distinguish copied locally, committed
      and confirmed on the remote.
- [ ] **I6 attention experiment:** compare journal classifier with Haiku
      and independently assessed outcomes, including AC-33 injection and
      mandatory-event conflicts. Set missed-action/delay limits before
      activation; count fallback and digest costs (ODIN-ADR-004).
- [ ] **I6 attention prompts** (ODIN-ADR-010): typed, capped prompts
      with mandatory response records, logged in shadow mode from I4
      alongside the human view, leave shadow mode only when logged
      outcomes support the caps (proposed AC-39). Voice stays backlog
      until its data-policy decision (X-13) and never carries an
      approval until a hash-binding mechanism exists.
- Bragi on the new inputs is Saga's (D15.Fb); Odin provides the import
  endpoint and history projections.

## Phase G — evaluation and demonstration

- [ ] D18 comparison: Odin plus Saga against an existing agent plus
      Saga; memory hypothesis (D7) and Mimir policy (D8) on the same runs,
      with the two reviewer positions measured against single review and
      an equal extra verification budget (ODIN-ADR-013; acceptance §3).
- [ ] First demonstration: three specifications into coordinated work,
      through the five D18 scenarios (acceptance §1–2).
- [ ] **I7 desktop workflow**, only by operator decision (D21, §5.9):
      guarded desktop input as a gated process of the workstation daemon
      under its own Unix user, the only holder of the seat lease for
      cooperating clients (ODIN-ADR-011; EC-10's shared seat broker;
      moving WCU's input requires G-10); a dedicated desktop worker;
      human takeover; bounded textual classifier experiment (EC-10,
      EC-11; DC-01 to DC-08). Disabled until a delegation naming desktop
      authority exists; until the compositor restriction is verified,
      the lease binds cooperating clients only.
- Exit: measured results and an acceptance report published in this
  repository (acceptance §4).

## Increment summary

| Increment | Phase (I/O contract §13) | Backend | Gate |
|---|---|---|---|
| I0 contracts and fixtures | B | none (non-production) | X-7 before Review/guidance schemas are written; unaffected schema work may start |
| I1 service foundation | B | fake (non-production) | X-11 before I1; G2 before direct-stop work |
| I2 first harness | C | fake (non-production) | X-10 before I2; X-12 for the workstation daemon's local sessions; isolation checks before claiming the planner profile |
| I3 governed project | C | Saga | G-4; G1 to G5; Herdr read-only inspection (EC-03, G6) |
| I4 parallel workspace | D | Saga | G-6 for the phase exit; EC-03; G-10 for heimdall's import |
| I5 portability and context | E | Saga | G-7 for the phase exit (EC-05 withdrawn) |
| I6 optional optimizations and integrations | F | Saga / local | EC-04, EC-06, EC-07; G-10 for capture and braid as modules (EC-08, EC-09 withdrawn) |
| I7 desktop workflow | G (by operator decision) | desktop | D21 authority; EC-10, EC-11; G-10 for moving WCU's input |

The blueprint places I7 after the one-project proof and the I/O
contract lists the desktop workflow in Phase G; Saga's roadmap at
extraction listed the computer-use worker under Phase F "by operator
decision". Both make it conditional on an operator decision; neither is
a commitment. The Pi RPC control after I2 is fixture-only and not an
increment (ODIN-ADR-015).

## Consolidation plan

[`design/CONSOLIDATION-PLAN.md`](design/CONSOLIDATION-PLAN.md) is a
proposal for operator decision. Its phases P0 to P7 map onto the
increments above without reordering them: P0 is Phase A's governance
work, P2 to P4 and P6 correspond to I0 to I3, and P5 and P7 fall within
I4 to I7. Where the plan places an item differently (the Pi RPC
control, attention prompts, the transcript archive), this roadmap's
placement governs. P1, the repository consolidation, is not an
increment; it waits on G-9 and G-10, and G-11 is its exit.

Recorded: the Odin-owned parts, as ODIN-ADR-006 to 015 (one event
substrate, the commitment record as the single task authority, the
narrowed I0, the workstation daemon and session host, operator surfaces
and attention prompts, gated desktop input, preservation without
dotprivate, two reviewer positions as a hypothesis, session-class
decision records, the Pi RPC control). Waiting on X-14, and still
proposals: Saga sharing a repository and release train with Odin,
workers reporting to Saga's own intake instead of MQTT, Bragi and Eir
as Odin classes, the repository names and prefix, and the D14 handoff.
ODIN-ADR-016 to 019 are not recorded. Nothing in the plan is
implemented.

## Carried over from Saga's roadmap

| Item | Odin disposition |
|---|---|
| Spec development Tier 2 | After Phase C (the dev-log becomes a chat-log slice); see legacy triage L-SD-2 |
| Voice over Telegram | Unscheduled; backlog until its data-policy decision (X-13, ODIN-ADR-010); legacy triage L-VT |
| ANTI-PATTERN-1 (verdict polling) | Replaced by Odin's event intake (I1) and Saga's verdict records; Saga tracks the Saga side |
| OBSERVABILITY-1, TELEGRAF-WIRING | Phase F, observability |
