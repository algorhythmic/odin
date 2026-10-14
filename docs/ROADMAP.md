# Odin roadmap

Progress against the inherited sequence. The phases (A to G) and their
exit criteria are decided in D15; the increments (I0 to I7) are the
[blueprint's](design/ODIN-IMPLEMENTATION-BLUEPRINT.md) §7; the
phase-to-increment mapping is the
[I/O contract's](design/ODIN-IO-CONTRACT.md) §13. This file tracks them
and does not change their order. Where it conflicts with those
documents, they win ([`DECISIONS.md`](DECISIONS.md) authority order).
Old phase numbers from legacy feature documents are not commitments
([`provenance/LEGACY-REQUIREMENTS.md`](provenance/LEGACY-REQUIREMENTS.md)).

Nothing below is implemented. Checked items are documentation only.

## Where to start

**First task: I0, contracts and fixtures.** Then I1 (service
foundation) and I2 (first harness), both non-production, against a
fake Saga backend that implements the I/O contract's Appendix B and is
never presented as Saga. **I3, any live delegated run and any live Saga
submission wait for Saga Phase B's exit criterion and minimum
enforcement.** This is the handoff clarification recorded under D15 in
`DECISIONS.md` (issue X-1, review finding B2).

## Dependency gates

| Gate | Owner | Blocks | State |
|---|---|---|---|
| G-1 Documentation handoff recorded (D14.6: contract held one review cycle, Saga producer contract extracted, decision map written) | Saga + Odin | Odin becoming the document owner | Source review returned CHANGES_REQUIRED ([findings](provenance/SOURCE-REVIEW.md)); corrections applied ([resolutions](provenance/REVIEW-RESOLUTIONS.md)); re-review pending; not recorded |
| G-2 Saga contract pinned at `contracts/saga/2026-10-14-14fdab3/` | Saga (producer), copied into Odin | The Saga adapter's compatibility checks | Draft pinned (`0.1.1-draft`); producer commit not recorded; to be repinned from the corrected canonical bytes; Appendix B checked against the canonical draft at document level (X-3) |
| G-3 Saga confirmed active (open §5.1) | Operator | Phase B, migration step 2 | Open |
| G-4 Saga Phase B exit: CLI submits, watches, guides, stops and cancels; refused for the same reasons Odin would be; `/stop` stops a delegation and reports | Saga | I3, live runs, deployment cutover (D14.5) | Not started |
| G-5 Billing and auth re-test recorded; Max API credits claimed (open §5.6, §5.12) | Saga / Operator | Planning-session `api` default in production (D24.8a: default, pending operator confirmation) | Open; no billing test has run |
| G-6 Saga Phase D policy (TTL, budgets, presence gate, verification policies) | Saga | Phase D exit (identical policy for CLI and Odin) | Not started |
| G-7 Saga Phase E worker contract and Codex image | Saga | Phase E exit (Codex run under the same hooks and ledger) | Not started |
| G-8 Peer interfaces (EC-03 to EC-12) | Herdr, heimdall, skald, braid, WCU, dotprivate | The corresponding I3 to I7 integrations (Herdr read-only inspection in I3); never the core proof | Proposed only |

The `G-n` gates above are this roadmap's. The source review's `G1` to
`G7` are implementation gates, listed in their own table below.

## Implementation gates from the source review

The source review's gaps `G1` to `G7` may stay open now but must close
before the work named in the last column ships. Saga carries its parts
as `IG-1` to `IG-7` in its contract (§18). None is closed; nothing here
is designed or implemented beyond the documents. R-S1 was raised while
scoping Saga's record and is carried the same way.

| Gate | Subject | Owner | Must close before |
|---|---|---|---|
| G1 | Operator identity at Saga: how Saga tells an operator's approval or answer from one sent by Odin's service or the CLI (Saga GAP-02) | Saga (mechanism, approved by the operator); Odin forwards approvals and answers only through it | Saga declares Phase B minimum enforcement met; Odin's I3 |
| G2 | Stop split: which of D2's four operations Saga's `POST /stop` performs and which Odin performs; the kill switch while Odin is down (issue X-2; Saga GAP-17) | Saga (stop runs, revoke authority, its own schedules); Odin (pause planner, its timers and evaluators) | Saga's Phase B exit; Odin's direct stop in I1 (fake backend) and live in I3 |
| G3 | Restarts and review cost: a restart's new request id needs renewed verdict and approval coverage; whether unchanged digests avoid a fresh model review; the cost (Saga GAP-07, GAP-08) | Saga (binding rule); Odin (renewal in `stage_run`, review-cost accounting) | Saga builds Phase B binding; Odin's I3 |
| G4 | Saga's validator as a dependency: `stage_run` pre-checks only against a schema Saga publishes, never Saga's code (Saga ADM-10) | Saga (published schema); Odin (pre-check against it) | Odin relies on local pre-checks (I3 at the latest); until then there is no pre-check |
| G5 | Planner answers: Saga can enforce only the request kind and the delegation's permission, not "does not change the plan" (Saga RQ-5) | Saga (enforcement); Odin (the judgment, logged and reviewable) | Saga's Phase B request protocol; Odin's I3 |
| G6 | Unconfirmed integrations: Herdr's API (§5.8), skald retrieval (§5.11), dotprivate's selected-files contract (§5.10), the heimdall projection (EC-05) | Odin with each peer | Herdr: I3 (read-only inspection) and I4 (adapter); heimdall: I5; skald, braid, dotprivate: I6 |
| G7 | Unsettled defaults: the billing and auth re-test; the Console spend cap not applying under a subscription login; wake, interrupt and review caps and the coalescing window; the memory baseline | Operator (re-test, Phase A; G-5); Odin (caps and window from I3's first week of records; spend-cap behaviour before I3; baseline before the I5 memory comparison) | As stated per owner |
| R-S1 | Whether D7 redaction reaches Bragi's outputs compiled from Odin's chat logs (Saga's record §7) | Saga (Bragi's outputs); Odin (redaction propagation, I/O contract §8) | Bragi is given Odin's history projections (cutover, I/O contract §14 step 3); Saga tracks it as SB-08 |

## Phase A — reset (Saga phase; Odin documentation handoff)

- [x] Odin design documents adapted for this repository, with the
      frozen snapshot, decision map and legacy triage (candidate; under
      review)
- [x] Source review findings B1–B7 and N1–N11 corrected in the
      documents (`DECISIONS.md` §6,
      [`REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md)); G1–G7
      carried as implementation gates (above)
- [ ] Independent re-review of the corrections (D14's review cycle)
- [ ] Documentation handoff recorded in both repositories (G-1)
- [x] Saga's producer contract pinned here as a draft (G-2); producer
      commit still to be recorded; repin from the corrected canonical
      bytes pending
- [x] Appendix B checked against Saga's canonical `0.1.1-draft` at
      document level (X-3); repeat at each repin
- [ ] Odin-relevant operator answers to the open questions
      (`DECISIONS.md` §3): default models, memory baseline and retention
      defaults, muninn, licenses, the first delegation, Herdr, desktop
      authority, dotprivate, skald retrieval, planning billing mode
- Saga-side Phase A items (credits, billing re-test, Saga active) are
  dependencies G-3 and G-5.

## Phase B — Saga service v1 (Saga) with I0 and I1 in Odin

Saga delivers the API and minimum enforcement (I/O contract §13). In
parallel, and non-production, Odin:

- [ ] **I0 contracts and fixtures:** versioned record schemas (I/O
      contract §2, Appendix A), the event envelope and kinds
      (Appendix C, EC-01), the adapter capability matrix (§11), the
      fake Saga backend for Appendix B, a synthetic three-document
      fixture (acceptance §1), the ownership mapping, the planner
      profile's tool-isolation check (I/O contract §7). Exit: duplicate,
      stale and unknown cases have explicit semantics; no peer API is
      invented as implemented.
- [ ] **I1 service foundation:** transactional state, event intake and
      cursors, outbox, scheduling, direct stop, CLI (I/O contract §9).
      Exit: restart and replay produce one logical action and retain
      unknown outcomes (AC-01, AC-02, AC-27 against the fake backend).

## Phase C — Odin v1 (Odin)

- [ ] **I2 first harness** (non-production, fake backend): Claude Code
      adapter and integration package; briefing and `zoom`; session
      lifecycle; the planner profile with tool isolation passing its
      check (I/O contract §7). Exit: one bounded assignment survives
      replacement of its session; unsupported operations are explicit
      (AC-04).
- [ ] **I3 governed project** (requires G-4; gates G1 to G5): Saga
      Phase B boundary, operator channel (Telegram with hash-bound
      approvals), selective Mimir, verification; **read-only** workspace
      inspection through Herdr (no adopt or take-control); migration
      import, shadow mode, cutover (I/O contract §14). Exit: one real
      project passes admission and finishes with evidence; the CLI and
      Odin face the same refusal rules.
- Phase exit (D15.C): Odin runs one project end to end without tmux,
  meeting Saga's boundary on its first live submission; an interrupted
  session is replaced without losing the outstanding assignment.

## Phase D — richer policy (Saga), second project (Odin)

- [ ] **I3 → I4:** second project; adopt-into-supervision and
      take-control with pending-effect holds; ownership rules exercised
      (D20; AC-11, AC-12, AC-16).
- [ ] **I4 parallel workspace:** the full Herdr adapter with explicit
      bindings, scoped planning owners, adopt and takeover (EC-03). Exit:
      projects remain separate, bindings are explicit, no pane state is
      mistaken for completion. (Skald enrollment is I6.)
- Phase exit (D15): the CLI and Odin encounter identical policy (G-6).

## Phase E — workers and portability

- [ ] **I5 portability and context:** the second Odin runtime adapter
      (Codex app-server or Pi RPC) with its capability matrix; memory
      comparison against the baseline (D7, D18); heimdall external views
      (EC-05). Exit:
      capability differences and unavailable-peer behaviour pass the
      acceptance scenarios; Odin runs one assignment through the second
      adapter with its missing capabilities stated. A Codex worker image
      (Saga, G-7) does not test Odin's harness portability.

## Phase F — integrations

- [ ] **I6 optional optimizations and integrations:** `recall` on braid
      (EC-07); `decide`; `propose_decider` with the evaluator registry;
      the first evaluator (`journal_attention_v1`) in shadow mode; skald
      source enrollment and archiver (EC-04), then the read-only
      `archive` scope when skald's retrieval exists (§5.11, EC-06);
      selected
      preservation through dotprivate once its contract is released
      (EC-08, EC-09; §5.10); local session backend with its capability
      matrix (D23); observability. Exit: routing benefit measured;
      publication receipts distinguish local and remote state.
- Bragi on the new inputs is Saga's (D15.Fb); Odin provides the import
  endpoint and history projections.

## Phase G — evaluation and demonstration

- [ ] D18 comparison: Odin plus Saga against an existing agent plus
      Saga; memory hypothesis (D7) and Mimir policy (D8) on the same runs
      (acceptance §3).
- [ ] First demonstration: three specifications into coordinated work,
      through the five D18 scenarios (acceptance §1–2).
- [ ] **I7 desktop workflow**, only by operator decision (D21, §5.9):
      WCU worker, shared seat broker, human takeover, bounded textual
      classifier experiment (EC-10, EC-11; DC-01 to DC-08).
- Exit: measured results and an acceptance report published in this
  repository (acceptance §4).

## Increment summary

| Increment | Phase (I/O contract §13) | Backend | Gate |
|---|---|---|---|
| I0 contracts and fixtures | B | none / fake (non-production) | — |
| I1 service foundation | B | fake (non-production) | — |
| I2 first harness | C | fake (non-production) | — |
| I3 governed project | C | Saga | G-4; G1 to G5; Herdr read-only inspection (EC-03, G6) |
| I4 parallel workspace | D | Saga | G-6 for the phase exit; EC-03 |
| I5 portability and context | E | Saga | G-7 for the phase exit; EC-05 |
| I6 optional optimizations and integrations | F | Saga / local | EC-04, EC-06 to EC-09 |
| I7 desktop workflow | G (by operator decision) | desktop | D21 authority; EC-10, EC-11 |

The blueprint places I7 after the one-project proof and the I/O
contract lists the desktop workflow in Phase G; Saga's roadmap at
extraction listed the computer-use worker under Phase F "by operator
decision". Both make it conditional on an operator decision; neither is
a commitment.

## Carried over from Saga's roadmap

| Item | Odin disposition |
|---|---|
| Spec development Tier 2 | After Phase C (the dev-log becomes a chat-log slice); see legacy triage L-SD-2 |
| Voice over Telegram | Unscheduled; legacy triage L-VT |
| ANTI-PATTERN-1 (verdict polling) | Replaced by Odin's event intake (I1) and Saga's verdict records; Saga tracks the Saga side |
| OBSERVABILITY-1, TELEGRAF-WIRING | Phase F, observability |
