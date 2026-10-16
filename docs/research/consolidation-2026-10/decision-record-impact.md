# Decision-record impact of the proposed agent-runtime consolidation

Date: 2026-10-16. Read-only analysis of `/home/david/Projects/odin`
(working tree). No file in the repository was edited. The consolidation is
treated as a proposal under evaluation, not a decision.

Read: `AGENTS.md`; `docs/DECISIONS.md` (all); `docs/provenance/DECISION-MAP.md`;
`docs/design/ODIN-ECOSYSTEM-INTEGRATION.md`; `docs/ROADMAP.md`; I/O contract
§1–§15 and Appendices A–D; acceptance scenarios; `scripts/validate_docs.py`;
`docs/provenance/EXTRACTION-MANIFEST.json`. Also consulted: `README.md`,
`docs/README.md`, the blueprint, `docs/contracts/README.md`, the pinned Saga
contract (§0–§2, §15–§16, §20), `HANDOFF.md`, `REVIEW-RESOLUTIONS.md`,
`LEGACY-REQUIREMENTS.md`. Frozen history (frozen D0–D16, extraction plan
§1, §4, §8) was read only to compare wording.

## Baseline facts that change the analysis

- **The validator passes on the working tree** (`35 frozen files ... 1 producer
  pin(s), and local links in 20 live documents`).
- **The governance baseline is uncommitted.** ODIN-ADR-001 to 005, AC-31 to
  AC-36, the new manifest digests, and the exception clause itself ("must
  agree with the frozen copy *except for explicitly recorded operator
  decisions in Odin's ADRs*") exist only in the working tree. At HEAD
  `cb55ecc`, `DECISIONS.md` §4 says "None recorded" and `AGENTS.md` §1 says
  only "these documents must agree with the frozen copy". The mechanism
  that would let ODIN-ADRs carry the consolidation has never been committed.
- **No existing ODIN-ADR supersedes an inherited clause.** ADR-001 to 005
  resolve, operationalize, or set defaults. The map says: "No decision
  clause has been superseded on its merits by this extraction." The
  consolidation would be the first supersession of *locked* inherited
  clauses.
- **Corrections to the brief:** the increments are **I0–I7**, not I0–I6. EC
  items run **EC-01–EC-12**, not EC-01–EC-10. Acceptance runs AC-01–AC-36
  and DC-01–DC-08.
- **Next free identifiers:** ODIN-ADR-006, X-11, AC-37, DC-09, EC-13, B-18,
  roadmap gate G-9. §3 keeps the source §5 numbering 1–12, so new open
  questions should go in as X-n issues, not as §3 items.

## 0. Findings that block or reshape the consolidation

1. **Locked Saga-owned clauses have no Odin-side path.** The execution
   backend that absorbs "launcher, ledger, run lifecycle, approvals/verdict
   binding, limits, stop ops" touches D2, D4, D5 and D17, all owned by
   Saga. So do the replacement of MQTT/ratatoskr (D1.2, D3.3, D13.4a, D15.B
   and Saga contract MQ-1), Bragi becoming an Odin session class (D12.1,
   D1.2, D17.4b, D15.Fb) and Eir becoming an Odin assignment class (D11.1a,
   D11.2, D11.3, D1.2). The repository merge touches D14.1 (a shared rule)
   and D14.7 (Saga's). The repository's only stated path for all of these:
   the operator records a decision in **Saga's** live record, Saga publishes
   a new contract version, and Odin pins it (`contracts/README.md` rule 3).
   An ODIN-ADR "does not amend Saga-owned interfaces or close the
   cross-repository handoff" (AGENTS.md §1). Work in Saga's repository
   cannot be done from this one (AGENTS.md §3).
2. **"Saga's MQTT bus and ratatoskr are replaced by the Odin service's
   intake" contradicts D1.3, D4 and B-17 whoever records it.** Worker
   events that end at Odin's intake bypass the authoritative ledger
   (D4.1). They also break "Workers never reach Odin directly" (I/O §10)
   and the guarantee that only Saga answers or guides a run (B-17, AC-29).
   **Reshape:** the execution backend gets its own intake, which replaces
   MQTT by a Saga decision, and Odin's intake consumes the backend's event
   cursor (B-12).
3. **"Eir becomes an Odin assignment class" conflicts with D11.3.** D11.3
   says Eir "keeps an operator-invoked path outside Saga's failure domain".
   Blueprint §3 says "Odin's availability must not be required for Saga's
   out-of-band recovery." An Odin assignment class lives inside the Odin
   service's failure domain. Eir needs an operator path that requires
   neither the Odin service nor the backend to be running.
4. **D2 ("Enforcement lives in Saga") holds only if the backend stays
   Saga.** That means Saga's product identity, decision record, contract
   and conformance checks (contract §19), running in a separate,
   independently restartable process. Saga's code must not be importable
   by the Odin service: I/O §6 `stage_run` says "Odin never copies or
   imports Saga's code (gate G4)", so in a monorepo this needs a
   build-enforced boundary. The backend must also stay neutral to
   orchestrators (D3.2: CLI second, an existing agent third; D18.1's
   "existing personal agent plus Saga" arm). If the backend stops being
   Saga, D23.2 leaves **no** permitted backend for work with external
   effects until Saga's record changes. The repository forbids presenting
   any other backend as having Saga's guarantees (AGENTS.md §5; D23
   ownership note).
5. **The one event substrate collides with D4.1 and the ecosystem
   principle.** D4.1 reads "Saga's run ledger (SQLite in the Saga
   service)". The ecosystem plan's preamble says Odin "does not merge their
   databases". The execution-ledger namespace must be a separate store
   with one writer, the backend. Otherwise D4 is a Saga-owned change.
6. **Because the handoff is not recorded, Saga's record is authoritative
   even for Odin-designated clauses.** The map "designates owners, it does
   not transfer them" (DECISION-MAP, "Until the handoff is recorded").
   ODIN-ADRs that supersede D8, D10, D20 or D22 are permitted operator
   decisions, but each one creates a recorded divergence from the
   authoritative record. There is no precedent for that.
7. **Naming collisions.** "Seat" already means the desktop seat and seat
   lease (D21.4, EC-10, DC-01) and the subscription seat (§3 item 6).
   "Nudge" is the superseded tmux `send-keys` mechanism (L-PU-1). Under
   D13.1, module names `heimdall`, `skald`, `braid` and
   `wayland-computer-use` cannot survive inside the monorepo (see §E).
8. **Credentials on the workstation.** D24.3 says "a protected credential
   source held by the service". A session host on the operator's machine
   needs a local model credential. It sits next to the development login
   that CLAUDE.md, AGENTS.md §6 and D24.6 keep separate.

---

## A. Inherited decisions and clauses touched

**Categories.** (i) An ODIN-ADR alone is enough for Odin's documents,
subject to the handoff caveat in A.2. (ii) The clause is Saga-owned or a
shared rule; Odin cannot amend it, and the required path is stated.
(iii) Implementation detail; no decision change is needed if the stated
constraint holds.

Owners and statuses are from DECISION-MAP.md. "Path S" means: an operator
decision recorded in Saga's live record (SAGA-ADR-nnn), a new Saga contract
version where the interface changes, a repin under `docs/contracts/saga/<new-snapshot>/`,
and Appendix B rechecked (X-3).

### D0 — Product scope (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D0.5 | Odin · locked | "Desktop control ... never part of the initial product." | Workstation daemon ships WCU guarded input as a module | iii | Ships disabled and gated (ADR-011); otherwise it is a D0 change |
| D0.7 | Shared rule · locked | "hosted inference (Anthropic for Odin's turns and the workers; optionally hosted or local decision models)" | Second frontier reviewer, or a Pi adapter on another provider's models | i (Odin's wording) | Shared rule: "each repo owns its own wording". Odin updates its own text; Saga's wording is untouched |

### D1 — Products and boundary (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D1.1 | Odin · locked | "an **Odin service** (...) plus a **harness integration package** ... Hosts Odin, Mimir review sessions and one-shot subagents." | Adds workstation daemon, substrate, reviewer positions; Bragi and Eir hosted | i | Bragi/Eir part waits on D1.2 (ii) |
| D1.2 | Saga · locked | Saga owns "Runs, workers, images and hooks, policy, events, delegation records, Bragi, Eir." | Bragi, Eir, events (MQTT/ratatoskr) leave Saga | **ii** | Path S (contract SCOPE-2) |
| D1.3 | Odin (consumer obligation) · locked | "Odin reaches Saga only through tools backed by the independently running Saga service" | Backend in the same deployable | iii | Holds only if the backend is a separate, independently restartable process with its own API, and Odin links none of its code |
| D1.4a | Saga · locked | "a lost connection does not lose a run, restarting Odin does not restart workers" | Co-deployment of Odin service and backend | iii / ii | A deployable that restarts both together breaks it; changing it is Path S |
| D1.4b | Odin · locked | stable request id, cursor resumption, no relaunch | — | iii | Unchanged |

### D2 — Enforcement lives in Saga (locked; Saga)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D2 (title), D2.1 | Saga · locked | "Saga validates for every client" (admission, digests, verdict and approval binding, limits) | Backend "absorbs ... approvals/verdict binding, limits" | iii if backend = Saga relocated; **ii** otherwise | Repository location is not part of D2. Ownership of enforcement is. Non-Saga enforcement needs Path S |
| D2.2 | Saga · locked | repository-scoped push, firewall egress | Launcher absorbed | iii / ii | As D2.1 |
| D2.3 | Saga (Odin obligation) · locked | "requires its own enforcement boundary before it is offered to any agent" (desktop input named) | Gated input capability | iii | The separate input-device process is that boundary; it must exist and be enforced before enablement |
| D2.4a | Saga · locked | "Saga verifies the key" | Two-position consensus verdict | iii if one combined verdict goes under the service-held key; **ii** if per-position verdicts or keys change the verdict record (REC-4, B-10) | — |
| D2.4b | Odin · locked | key "never exposes to Odin's turns" | Reviewer-key holder as a separate process | iii | Permitted by D2.5 |
| D2.5 | Odin · locked | "Mimir reviews quality; Saga enforces authority ... a separate process is available" | Mimir replaced by two positions | i | Wording only |
| D2.6–D2.7 | Saga (definition); Odin implements pause planner and disable schedules · locked | "Four distinct operations, each an API call and an operator command" | Backend absorbs "stop ops"; workstation hosts may be offline | iii if backend = Saga; X-2 stays open | Stop must report uncertain outcomes for offline hosts (AC-10) |

### D3 — Pluggability contracts (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D3.1 | Saga · locked | "Orchestrator contract = the Saga API" | Same repository | iii | API stays the only route |
| D3.2 | Saga · locked | "Odin is the first client; a CLI is the second ...; an existing agent is the third" | One release train | iii (constraint) | Backend API must stay usable by the CLI and by a third-party agent; dropping that is Path S |
| D3.3, D3.4a | Saga · locked | worker contract "per image"; structured request fields | MQTT replaced | **ii** | Path S (contract §11, §15) |
| D3.4b | Odin · locked | deliver requests preserving fields | — | iii | Unchanged |

### D4, D5, D6 — Ledgers, completion, side effects

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D4.1 | Saga · locked | "Saga's run ledger (SQLite in the Saga service) is the authoritative record" | Execution ledger as a namespace of one substrate | iii if it is a separate store with the backend as sole writer; **ii** if the store, writer or failure domain is shared | Path S for any change |
| D4.2–D4.3 | Odin (consumer) · locked | "Odin's chat log ... is never consulted to decide whether a run was approved or completed" | Shared substrate | iii | Odin-history namespace can never decide approval or completion |
| D5.1–D5.4 | Saga · locked | run states, `depends_on`, evidence judgement | Backend absorbs "run lifecycle" | iii if backend = Saga; **ii** otherwise | — |
| D5.5 | Odin · locked | lifecycles not collapsed | — | iii | Unchanged |
| D6.1–D6.5 | Shared rule · locked | at-least-once, `unknown`, reconcile, no exactly-once | Substrate | iii | The substrate design must carry it; the rule is unchanged |

### D7 — Runtime and memory (runtime locked; memory hypothesis; Odin)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D7.2 | Odin · locked | "the Odin service starts, resumes and retires Claude Code sessions through the Agent SDK" | Session host on the workstation executes; RPC harness (Pi) added | i (clarify) | Service keeps the decision and the records; host executes |
| D7.6 | Odin · locked | "one implementation is built and validated first" | Pi adapter pulled early | i | Keep it by starting Pi only after I2's exit (ADR-015) |
| D7.7 | Odin · locked | "the service supplies its own Telegram adapter and event intake" | More surfaces and inbound sources | iii / i | Covered by ADR-010 |
| D7.11 | Odin · locked | "Saga keeps authority and execution state; Odin keeps commitments and memory." | "Single task authority" | iii (constraint) | Must not extend to delegations, approvals or run states; that would be a D17 change (ii) |
| D7.12 | Odin · locked | "The append-only rule has one sanctioned exception: redaction." | Substrate namespaces include the transcript archive | iii | Redaction propagates across namespaces with per-destination pending state (AC-26, EC-12) |

### D8 — Mimir (default; Odin)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D8.1–D8.3 | Odin · default | when to review; mechanical first; evidence not narrative | Two positions, same pack | i | Keep: evidence packs only, no access to Odin's reasoning |
| D8.4 | Odin · default | "One review and at most one corrective re-review per artifact; then the operator decides." | Consensus over two positions | i | Rounds must stay bounded; disagreement goes to the operator |
| D8.5 | Odin · default | "Sonnet by default ... Opus and Sonnet share a family and their errors are not independent" | Two frontier models | i | Superseded; §3 item 2 stays open |
| D8.6 | Odin · default | hard daily caps on review spend | Two calls per review | i | Caps restated per position and total |
| D8.7 | Odin · default | "Odin alone, Odin with an equivalent extra verification budget, and Odin plus Mimir are compared" | — | i | Must add the consensus arm |

D8's status is "default (locked unless the operator objects)", so an
operator objection recorded as an ODIN-ADR is in scope. Linked clauses:
D2.4a (verdict format, ii if changed), D13.2a (the Mimir name), D19.3,
D18.2, AC-22.

### D9 — Decision models (locked; Odin)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D9.3 | Odin · locked | four hook locations; "Not supported: ... operator messages" | Classifying heimdall observations, capture lifecycle events, nudge decisions or voice intent | iii if none of these is classified; **i** (new decision) if any gets a hook | ADR-004 forbids a fifth hook without a new decision |
| D9.5 | Odin · locked | "Sensitivity follows content ... only to the local provider" | Voice transcription; desktop text in observations | iii | L-VT-2 already flags hosted speech-to-text as needing a decision |

### D10 — The standalone tools stay separate (locked; Odin consumer, peers own capabilities)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D10 (title), D10.6 | Odin · locked | "Nothing rolls into Odin. The harness core stays generic; Saga-specific tools come from the Saga client library; everything else is an adapter." | Directly reversed | **i** for Odin's text; plus a decision in each peer repository | Peer capability ownership (map: "Odin (consumer); braid (capability)" and so on) is not Odin's to transfer |
| D10.1 | Odin consumer; braid capability · locked | "child process over its stdio protocol; never indexes the chat log"; "after Odin v1" | Braid becomes a library inside the substrate | i | Keep the X-4 reading (never the *active* chat); keep D15.Fa timing unless amended |
| D10.2 | Odin consumer; skald capability · locked | "via a provider adapter and the per-line `chat` id; must honour redaction" | Capture module writes the archive namespace | i | Redaction stays |
| D10.3 | muninn | — | Not merged | iii | §3 item 4 open |
| D10.4 | Odin consumer; WCU capability · locked | "harness-independent ... never reachable from planning sessions or container workers" | Module of the workstation daemon | i | Harness independence and isolation from planning sessions both preserved (ADR-011) |
| D10.5 | Odin consumer; heimdall · locked | "Not an authority for approvals or task state. Optionally connected later as a human-facing continuity surface ... that references Odin's commitment record as the one authoritative record"; "needs a release and green CI" | Task layer folded in; TUI replaced | i, plus a heimdall-side decision | Consistent with D10.5's intent; the release/CI condition becomes moot |

### D11, D12 — Eir and Bragi (locked; Saga, Odin owns interfaces)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D11.1a, D11.2 | Saga · locked | three loops; complete improvement loop | Eir becomes an Odin assignment class | **ii** | Path S |
| D11.3 | Saga · locked | "Eir normally runs as a Saga task and keeps an operator-invoked path outside Saga's failure domain. The merge gate remains the operator." | As above | **ii**, and substantive | The out-of-band path must survive without the Odin service (blueprint §3) |
| D11.4 | Odin · locked | "Odin files maintenance requests only through Saga's task request" (B-16) | Route changes | i, only after D11 changes at Saga | X-8 stays open |
| D12.1 | Saga · locked | "A model-driven compiler in the Saga repo." | Bragi becomes a scheduled Odin session class | **ii** | Path S. Linked: D17.4b, D15.Fb, D16.3 (Saga) |
| D12.2–D12.3 | Odin · locked | import endpoint; history projections | Become internal | i, after D12.1 | R-S1 (redaction reaching Bragi's outputs) stays open |

### D13 — Naming (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D13.1 | Shared rule · locked | "Every deterministic component ... gets a plain functional name, prefixed `saga-` when it is a deliverable. Never reuse a name used by one of the operator's standalone repos." | Monorepo and deployable names; absorbed module names | iii (constraint); changing it is **ii** | See §E |
| D13.2a | Odin · locked | "Odin and Mimir keep their names" | Mimir retired? | i | Only if the name is dropped |
| D13.4a | Saga · locked | "Saga launcher, Saga events" | Saga events replaced | **ii** | Path S |
| D13.5 | Saga · locked | topic and directory renames | MQTT removed | **ii** | Path S |
| D13.6 | Odin · locked | "`containers/odin/` and the `saga-odin` image move to the `odin` repository" | Repository and image names | i | Resolves X-5 by operator decision |
| D13.10 | Shared rule · locked | legacy names remain in history and code until each rename lands | Absorbed code (`heimdall.py`, `ratatoskr.py`) | iii | Keep until renamed |

### D14 — Repositories (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D14.1 | Shared rule · locked | "`saga` and `odin`; the standalone repos stay where they are." | Reversed | **ii** | Must be recorded in Saga's record **and** Odin's (shared rule: no joint editable master), plus peer repos |
| D14.2 | Shared rule · locked | three changes (handoff, code extraction, cutover) | Monorepo reframes "code extraction enters that repository" | **ii** / i | — |
| D14.3 | Odin · locked | documentation-first scaffold | Location moves | i | — |
| D14.4 | Odin · locked | "code extraction enters ... in the blueprint's increments" | Increments still govern | i (if repository changes) | — |
| D14.5 | Odin gate; Saga provider · locked | cutover depends on Phase B | — | iii | Must be preserved |
| D14.6 | Shared rule · locked | "the contract has held for one review cycle, Saga's producer contract is extracted at Saga, and the decision map is written" | The merge does not satisfy it | **ii** | Gate still unmet (re-review pending) |
| D14.7 | Saga · locked | "Until the handoff is recorded, this repository [Saga] remains the document owner." | Merging Saga's record into the monorepo | **ii** | Saga-owned. The map says it "lapses only when the handoff is recorded in both repositories" — a notion a merged repository no longer has. Saga's record must first define how the handoff is recorded |

### D15 — Sequencing (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D15.B | Saga · locked | "facade over the existing launcher and MQTT" | MQTT replaced | **ii** | Path S (contract PH-1) |
| D15.C | Odin · locked | "Odin v1 in the `odin` repo" | Repository name | i | Contents and exit unchanged |
| D15.Eb | Odin · locked | "a second Odin harness adapter (Codex app-server or Pi RPC) ... Odin runs one assignment through it" (Phase E) | Pi pulled early | i | Fixture-only before Phase B |
| D15.Fa | Odin · locked | "`recall` on braid; ...; skald archiver" (Phase F) | Braid library and capture module part of the substrate | i if moved; iii if runtime enrollment stays I6 | Reopens X-9 if moved |
| D15.Fb | Saga · locked | Bragi on new inputs | Bragi moves | **ii** | — |
| D15.8 | Shared rule · locked | "Phase B precedes C ..." | One release train | iii (constraint) | Release-train cadence must not merge Phase B's exit with I3; X-1 open |

### D16–D18

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D16.2 | Odin · locked | design docs in "this repository's `docs/design/`" | Location | iii / i | — |
| D16.3 | Saga · locked | personas unchanged until Phase C | Bragi/Eir personas | **ii** | — |
| D17.1–D17.5 | Saga · locked | delegation "a first-class, versioned object in Saga's ledger" | Single task authority; backend absorption | iii if untouched | "Single task authority" must not include delegations; otherwise Path S |
| D18.1 | Odin · locked | "Odin plus Saga against an existing personal agent plus Saga (Hermes, on an API key, sandboxed)" | One release train; backend integration | iii (constraint) | Backend must stay usable by a non-Odin orchestrator |
| D18.2 | Odin · locked | D7 hypothesis and "Mimir policy (D8)" judged on the same runs | Two positions | i | — |
| D18.3 | Saga · locked | "Saga remains valuable if another agent wins" | Saga absorbed | iii if Saga's identity survives; **ii** otherwise | — |
| D18.5 | Odin · locked | step 4 "task-continuity and archive surfaces alongside"; step 5 "Three visibility surfaces show different truths"; step 7 "a selected project package is preserved (D22)" | One human view; dotprivate removed | i | The one view must still keep three distinct truths |

### D19 — Supervisory layer (locked; Odin)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D19.3 | Odin · locked | "Mimir and the decision models are optional ... Odin must remain useful with both disabled." | Positions replace Mimir | i (wording) | Consensus must stay switchable |
| D19.5 | Odin · locked | "a second (Codex app-server or Pi RPC) is added early enough to test whether the boundary is real, and no universal adapter framework is built before two implementations" | Pi early | iii | The early Pi adapter satisfies D19.5 as written; the conflict is with D15.Eb and D7.6 |
| D19.6 | Odin · locked | "Restrained initial product" | Bar, voice, desktop, Bragi/Eir, substrate | iii (constraint) | None of these may enter the Phase C proof's required scope |
| D19.7 | Odin · locked | "Odin is modular and can supervise work without Saga" | Bundled deployable | iii | Odin must still run without the backend |

### D20 — Topology and operator interfaces (locked; Odin, peer bridges)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D20.1 | Odin · locked | "Three layers, kept distinct" | The daemon spans the interface and session layers | i (clarify) | Separate processes inside the daemon |
| D20.2 | Odin · locked | "One Odin service owns the queues, adapters, memory access, budgets, session records and scheduling." | Remote session host | iii | Records stay in the service |
| D20.5 | Odin · locked | "Two operator interfaces, one command path." | Surfaces as adapters (bar, notifications, voice) | **i** | "One command path", hash-bound approvals and direct stop retained |
| D20.6–D20.7 | Odin · locked | native vs interactive; adopt and take control | Session host implements them | iii | AC-11, AC-12 |
| D20.8–D20.9 | Odin · locked | handling table | New inbound sources; nudge outbound | **i** | — |
| D20.10 | Odin + heimdall · locked | "Odin-managed work appears in heimdall as an externally owned projection; heimdall-managed work keeps its current owner" | No bridge; heimdall's task layer folded in | **i**, plus a heimdall-side decision | EC-05 withdrawn |
| D20.11 | Odin · locked | "First configuration: ... the terminal workspace for inspection, Telegram for remote interaction; then a second project ... before any further supervisory layer." | New surfaces | iii (constraint) | First configuration stays Herdr plus Telegram |

### D21 — Desktop capability (default; Odin coordination, WCU capability)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D21.1 | Odin · default | "wayland-computer-use remains a harness-independent desktop capability." | Module of the daemon | i | Harness independence kept |
| D21.2a, D21.5 | WCU · default | observe, guarded input, guards | Module boundary | i plus a WCU-side decision | — |
| D21.3 | Odin (rule); Saga (delegation field) · default | delegation must name desktop authority | — | iii | Delegation field is Saga's |
| D21.4 | Odin + WCU · default | "exclusive desktop-control lease, enforced at a shared broker or tool boundary across cooperating clients" | Gated capability holds the lease | i | This *is* the broker (EC-10) |
| D21.6 | Odin · default | "not inside the capability's input primitives, so the MCP servers stay usable without hosted inference" | — | iii | Preserve |
| D21.7 | Odin / Operator · default | "Not in the initial product (D0); scheduled after Phase F by operator decision." | Ships in the daemon | iii (constraint) | Disabled; §3 item 9 open |

### D22 — Preservation (locked in shape; integration scheduled)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D22.1, D22.4 | Odin · locked | package contents; imported copies never corroboration | — | iii | Unchanged |
| D22.2 | skald (backups); Odin (rule) · locked (shape) | "The archive (skald) owns full-archive backups" | Capture module and archive namespace | i | — |
| D22.3 | dotprivate capability; Odin reporting · locked (shape) | "Dotprivate carries the package, and the integration distinguishes "copied locally", "committed" and "confirmed on the remote"" | dotprivate removed from the dependency path | **i** (supersede the carrier) | Keep the three-state honesty rule |
| D22.5 | dotprivate / Odin · scheduled | "this integration is scheduled (Phase F), not assumed" | No dotprivate integration | i | §3 item 10 becomes dotprivate's own question |

### D23 — Execution backends (locked; Odin, Saga's guarantees Saga's)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D23.1 | Odin · locked | explicit backend with capability matrix | — | iii | — |
| D23.2 | Odin (routing rule) · locked | "**Saga** is the default and the only backend for work with external effects ... or needing isolation, enforced limits, durable run records and recovery." | "Execution backend" absorbs Saga | iii if backend = Saga; if not, external-effect work has **no** backend until Path S | "must not advertise Saga guarantees for another backend" |
| D23.3 | Odin · locked | local session backend "with its missing guarantees stated" | Session host | iii | Phase F/I6 timing unless amended |
| D23.4 | Odin · locked | "Desktop input is a third backend under D21." | Gated capability | iii | — |

### D24 — Authentication and billing (locked; split)

| Clause | Owner · status | Text affected | Consolidation change | Cat. | Constraint / path |
|---|---|---|---|---|---|
| D24.2a | Odin · locked | session classes "(planner, reviewer, subagents, compactor, triage, decision models)" | Adds reviewer positions, Pi-hosted planner; Bragi and Eir if moved | i | Each needs billing mode, credential reference and refresh owner |
| D24.3 | Odin (its sessions); Saga (secret store, workers) · locked | "a protected credential source held by the service" | Session host needs a local model credential | **i** (Odin's sessions only) | Never the development login |
| D24.4a | Odin · locked | "one refresher per lineage" | Service vs host | iii (constraint) | — |
| D24.4b, D24.7, D24.8b | Saga · locked | worker lineages, launcher injection | Launcher absorbed | iii if backend = Saga; **ii** otherwise | — |
| D24.6 | Shared rule · locked | "The operator's development login and the managed agents' login stay separate" | Workstation co-location | iii (constraint) | Unchanged; must be enforced |
| D24.8a | Odin · default, pending confirmation | planning on `api` | Pi adapter for Claude models | iii | AGENTS.md §6: third-party harnesses never on the subscription for Claude work |

### Record sections outside D0–D24

| Item | Owner | Effect |
|---|---|---|
| §1.b "Standalone heimdall rejected as authority for accepted task direction" | Saga (D17) / Odin (D20 bridge) | Consistent with single task authority; the bridge part is superseded with D20.10 |
| §1.d Saga as a local API with client library, MCP optional | Saga | Preserved by ADR-016 |
| §4.a "braid for retrieval" | Odin | Preserved; braid becomes a library |

### A.2 The "handoff not recorded" condition and what it means now

AGENTS.md §1: "the handoff is **not recorded**. Until it is, Saga's
decision record remains authoritative and these documents must agree with
the frozen copy except for explicitly recorded operator decisions in Odin's
ADRs. Those do not amend Saga-owned interfaces or close the
cross-repository handoff." The DECISIONS.md header and docs/README.md say
the same.

Consequences for making any of these changes now:

1. **Odin-side clauses (category i) can be recorded now, but only as
   operator decisions.** That is the precedent ADR-001 to 005 set. Each one
   leaves the authoritative Saga record saying the opposite, because the
   map only *designates* owners. For locked clauses such as D10, D20.5,
   D20.10 and D22.3 this is new ground, so each ADR should say explicitly
   that Saga's record is not amended.
2. **Saga-owned and shared clauses (category ii) cannot be recorded in
   Odin at all.** Odin's documents may only describe them as proposals
   until Saga's record changes and the contract is repinned.
3. **The exception clause itself is uncommitted.** Until the working tree
   is committed, the repository's recorded rule (HEAD) permits no
   divergence from the frozen copy.
4. **Nothing here closes X-1 or the handoff (G-1, D14.6).** The
   consolidation must not be described as a jointly approved plan.
5. **This repository is documentation-only** (AGENTS.md §1). Merging code
   is not an available action here in any case.

---

## B. Identifiers affected

Identifiers are never renumbered. "Withdrawn" means the id stays in the
text with a note naming the ADR that withdrew it.

### B.1 ODIN-ADRs

| ADR | Effect |
|---|---|
| ADR-001 License | **Preserve.** It "does not relicense retained source material" and makes "no license change ... in a peer repository". Merging heimdall, skald, braid and WCU needs a per-component license decision (§3 item 5; ADR-018). dotprivate stays MIT and separate |
| ADR-002 Journal attention | **Preserve.** New inbound sources (ADR-010) must not reintroduce unconditional planner wakes; the same typed-outcome and maximum-age rules apply |
| ADR-003 Memory comparison | **Preserve.** If braid becomes a substrate library, "same real adapters" becomes "same retrieval library configuration". The I5/I6 staging stays unless ADR-015 or ADR-006 moves it |
| ADR-004 Session-class routing | **Amended by a new ADR (ADR-014)**, not edited in place. Its four-hook limit, "no fifth hook" and "no silent downshift" bind the nudge and observation design. New classes: review positions; Bragi and Eir conditional |
| ADR-005 Compactor | **Preserve.** Unaffected. X-10 stays open |

### B.2 X issues (§5)

| Issue | Effect |
|---|---|
| X-1 Phase C vs fake backend | **Must stay open.** Needs Saga's record. The consolidation must not imply joint approval; one release train must not blur Phase B's exit with I3 |
| X-2 Stop operations | **Stays open.** ADR-016 is the natural place to state the split (pause planner and disable schedules: Odin; stop runs and revoke: backend), but the definition of record is Saga's (D2.6). It closes only with Saga's record or by an ODIN-ADR that moves just the Odin-state clauses, which X-2 itself offers |
| X-3 Pinned Saga contract | **Preserve (resolved as a document check).** It must be repeated at the repin ADR-016 requires. In a monorepo the "pin" becomes an in-repo versioned contract (ADR-018) |
| X-4 Archive retrieval | **Preserve (resolved as a reading).** Restate as: braid never indexes the Odin-history namespace's active chat; the archive scope stays read-only |
| X-5 Odin naming | **Resolved only by a naming decision (ADR-019).** Use plain functional names until then |
| X-6 Shadow-period bridge | **Partly moot** (which repository) if ADR-018 is recorded. Which component owns the bridge stays open; the MQTT replacement (Saga) changes its shape |
| X-7 `APPROVE_UNCHANGED` | **Stays open.** ADR-013 must define how two verdicts combine without choosing X-7's reading |
| X-8 Eir webhook failures | **Stays open.** Becomes Odin-internal only if ADR-017 takes effect |
| X-9 Increment placement | **Reopened in part** by ADR-008 (I0), ADR-015 (Pi) and any move of braid/skald work out of I6. Record the new placement explicitly |
| X-10 Compactor context | **Preserve.** Unaffected |
| New X-11 onward | Needed: substrate store topology and failure domains (ADR-006); heimdall native-task import (ADR-007); credential lineage on the workstation (ADR-009); voice transcription data policy (L-VT-2, ADR-010); reviewer-position terminology and second-provider data policy (ADR-013); per-component licensing (ADR-018) |

### B.3 EC items (EC-01 to EC-12)

| Item | Effect |
|---|---|
| EC-01 envelope and capabilities | **Preserve and expand:** substrate envelope and namespaces; the I0 core under ADR-008 |
| EC-02 Odin + Saga governed submission | **Preserve.** Owner becomes "Odin + execution backend (Saga)"; still a contract boundary |
| EC-03 Herdr adapter | **Preserve.** Moves to the session host (Herdr CLI); §3 item 8 stays open |
| EC-04 Skald + Odin enrollment and provider | **Re-scope:** the "Odin provider" becomes moot (substrate namespace); source enrollment becomes capture-module work; keep the id |
| EC-05 Heimdall projection and command relay | **Withdrawn** by ADR-007 (no bridge); replace with EC-13 (import and retirement) |
| EC-06 Skald archive scope | **Preserve, re-scope** in-repo; still depends on retrieval capability (§3 item 11) |
| EC-07 Braid datasets, exact expansion, archived conversations only | **Preserve.** Braid as a library; the active-chat exclusion is unchanged |
| EC-08 dotprivate selected-files contract | **Withdrawn from Odin's plan** (ADR-012); remains dotprivate's own work |
| EC-09 Selected export consumers (depend on EC-08) | **Withdrawn / superseded** by a carrier-neutral export item (new EC) |
| EC-10 Seat broker | **Preserve.** Becomes the daemon's gated capability; still the desktop-authority prerequisite |
| EC-11 Shadow textual evaluator | **Preserve** |
| EC-12 Deletion propagation | **Preserve; more critical** with one substrate across namespaces |
| New EC-13 onward | heimdall task import and retirement; session host protocol (dial-out, host identity, offline, reconnect); substrate namespace ownership and isolation; surface adapter API (bar, notifications, voice); nudge effect class; preservation carrier; environment probe; backend intake replacing MQTT (Saga-owned, recorded as a request) |

### B.4 Open questions

**DECISIONS.md §3 (source §5, numbering preserved):**

| Item | Effect |
|---|---|
| §5.1 Is Saga active again? | **Must be answered first.** Absorbing an inactive Saga is moot; it still blocks Phase B and I3 |
| §5.2 Default model; decomposition review model | **Affected** by ADR-013 (model per position); stays open |
| §5.3 Memory baseline and retention | Retention now spans substrate namespaces; stays open |
| §5.4 muninn | Unaffected (not merged); open |
| §5.5 Licenses | **Affected:** per-component terms for merged repositories; UniiChat terms still open |
| §5.6 Credits and seats | **Terminology collision** with reviewer "seats"; a second provider may need its own billing |
| §5.7 First delegation | Unaffected |
| §5.8 Herdr API | Unaffected; still open (session host drives the Herdr CLI) |
| §5.9 Desktop authority | Unaffected. ADR-011's gate does **not** answer it |
| §5.10 dotprivate contract | **Made moot for Odin** by ADR-012; dotprivate's own question remains |
| §5.11 skald retrieval | In-repo work; still open as a capability |
| §5.12a/b Billing | **Affected:** Pi adapter (API key), second-provider position, session-host lineage |

**I/O contract §15:** default model per class (affected by ADR-013);
caps/window (nudge caps added, ADR-010); retention and one-hour cache;
braid `recall` in v1 (library form, ADR-006); planning billing mode; muninn;
Saga active before migration step 2; UniiChat terms; Appendix B gaps
(**recheck at the ADR-016 repin**); X-7; X-8; tool execution isolation
"on the deployment host" (**affected:** the session host makes the
workstation a deployment host; ADR-009's environment probe reports the
capability but does not answer the question). None is closed by the
consolidation.

### B.5 Acceptance identifiers

Validator note: only AC-01–AC-30, DC-01–DC-08 and EC-01–EC-12 are
validator-protected, and frozen ids must remain a subset of the live ids.
AC-31–AC-36 and every new id are protected only by review.

| Id | Effect |
|---|---|
| AC-01–AC-03, AC-27 | **Preserve.** The substrate must keep inbox, cursor and outbox transaction semantics |
| AC-04–AC-07 | Preserve |
| AC-10 | **Preserve, extend:** stop with a workstation host offline reports uncertain local outcomes |
| AC-11, AC-12 | **Preserve:** the session host enforces takeover; bindings carry host identity and incarnation |
| AC-13–AC-16 | Preserve |
| AC-17, AC-18 | **Preserve:** substrate dedupe by origin and revision; capture gaps visible |
| AC-19 | **Re-scope, keep id:** "capture, sensors or retrieval component unavailable" |
| AC-20 | **Withdrawn** (no projection) by ADR-007. The id must remain in the text; replace with a new import/stale-observation scenario |
| AC-21 | Preserve |
| AC-22 | **Re-scope, keep id:** "a required reviewer position unavailable" |
| AC-23 | Preserve; nudge caps added |
| AC-24, AC-25 | **Keep ids;** retarget to the chosen carrier or mark deferred (ADR-012) |
| AC-26 | **Preserve:** cross-namespace redaction |
| AC-28 | Preserve |
| AC-29 | **Keep id; Saga-side.** Its transport changes if MQTT is replaced; the B-17 guarantee must persist |
| AC-30–AC-36 | Preserve. AC-36 also covers voice and other surfaces (operator target binding) |
| DC-01–DC-08 | **Preserve.** DC-01 and DC-02 are the gated capability's lease tests; DC-08 is the Herdr CLI path |
| New AC-37 onward | host offline during take control; reconnect with a stale incarnation; environment probe reports missing isolation, so the class is refused; heimdall import idempotent and later heimdall edits refused; reviewer positions disagree, so the operator decides; voice cannot approve; nudge cap and expiry; substrate namespace write isolation; backend restart independent of the Odin service |

### B.6 Other identifiers

- **B-00** "never by planning sessions or workers": the session host must
  not reach the backend API.
- **B-10** verdict format: affected by ADR-013.
- **B-14**: stays withdrawn.
- **B-16** Eir route: changes only if ADR-017 takes effect.
- **B-17**: the transport guarantee must persist.
- **G-1** handoff and **G-2** pin are affected. **G-8** "Peer interfaces
  (EC-03 to EC-12)" becomes mostly internal. Add **G-9** (Saga-side record
  of backend and repository changes) and **G-10** (peer-repository
  records).
- **G1** operator identity (voice), **G2** stop split, **G4**
  no-import-of-Saga-code (monorepo build boundary).
- **I0** narrowed; **I5** loses "heimdall external views (EC-05)"; I6 and
  I7 placement is restated.
- **L-VT-1/2** voice; **L-PU-1** "nudges ... replaced by event intake".
- The Saga contract's SCOPE-2, SCOPE-5, MQ-1–MQ-5, PH-1, PH-3 and RCV-3 are
  Saga-owned and change only at Saga.

---
## C. Proposed ODIN-ADRs, if the operator decides

These are drafts for §4, in the record's existing shape: Status, Context,
Decision, Consequences, Inherited relationship. They are recorded only
after the operator decides. Until then this text belongs in a proposal,
not in `DECISIONS.md`. Numbering starts at **ODIN-ADR-006**. Commit the
working tree first so that ADR-001 to 005 and the exception clause exist
at HEAD.

**Dependency order**

| ADR | Title | Depends on | Can be recorded in Odin alone? |
|---|---|---|---|
| 006 | Event substrate | — | Yes (Odin namespaces); the execution-ledger namespace only by reservation |
| 007 | Single task authority | 006 (schema home) | Yes for Odin; heimdall (and skald) must record their side |
| 008 | I0 scope | 006, 007 | Yes |
| 009 | Workstation daemon and session host | 006, 007 | Yes |
| 010 | Surfaces, inbound sources, nudges | 006, 009 | Yes |
| 011 | Desktop input as gated capability | 009 | Yes for Odin; WCU must record its side |
| 012 | Preservation without dotprivate | 006 | Yes |
| 013 | Two reviewer positions, consensus | — | Yes, unless the verdict record format changes (then Saga) |
| 014 | Session-class decision records (amends 004) | 013 | Yes |
| 015 | Early Pi adapter | 008, 009 | Yes |
| 016 | Execution backend placement | 006; **SAGA-ADR** | **No.** Conditional on Saga's record and a new contract version |
| 017 | Bragi and Eir hosting | 016; **SAGA-ADR** | **No.** Conditional |
| 018 | Repository consolidation | 007, 009, 011, 016, 017; **SAGA-ADR**; peer records; D14 handoff | **No.** Conditional |
| 019 | Deliverable names (X-5) | 018, or the plain-name interim | Yes for Odin names; the `saga-` prefix is Saga's |

---

### ODIN-ADR-006 — One event substrate for Odin's history, records and archive

- **Status:** default design; not implemented.
- **Context:** Odin history, the transcript archive and workstation surface
  events would otherwise be kept in three stores with three identity
  schemes. The I/O contract's single transactional core (§9) and D4's
  ledger split must both survive.
- **Decision:** Odin keeps one append-only event substrate with named
  namespaces for Odin history, the transcript archive and workstation
  surface events. Each namespace has exactly one writing component and its
  own retention and redaction rules. Revisioned records, the inbox, the
  outbox and cursors commit in the same transaction as the history they
  belong to. Braid's retrieval runs as a library over published, scoped
  namespace data and never indexes Odin's active chat. An execution-ledger
  namespace is reserved for the execution backend's own store. Odin reads
  it only through the backend's API and event cursor, never by direct
  access.
- **Consequences:** §9 intake, processing, outbox and recovery are
  unchanged (AC-01–AC-03, AC-27). JSONL and `view.json` remain
  projections. Redaction propagates across namespaces with per-destination
  pending state (AC-26, EC-12). Capture gaps stay visible (AC-18). Store
  topology and failure domains go to a new issue (X-11).
- **Inherited relationship:** amends the D10.1 delivery mode ("child
  process over its stdio protocol") and the D10.2 delivery mode ("via a
  provider adapter") for Odin. Preserves D4, D6, D7.11–D7.12, D22.2's
  exclusion of live databases from git sync, and X-4. Amends I/O §1 store
  table, §3, §9 and Appendix A; the ecosystem plan's preamble ("does not
  merge their databases").
- **Must not claim:** that the execution ledger is an Odin record or that
  Odin's history can decide approval or completion (D4.2); exactly-once
  (D6.5); that a shared store is a security boundary; that braid or skald
  runtime integration moved earlier than I6, unless an ADR moves it.

### ODIN-ADR-007 — The commitment record is the single task authority

- **Status:** locked direction for Odin; migration not designed.
- **Context:** D20.10 planned a projection bridge because heimdall and its
  skald amendment assign accepted task state to heimdall. Two authorities,
  even bridged, need a projection API, command relay and stale-revision
  handling (EC-05) that adds no value once heimdall's task layer is
  retired.
- **Decision:** Odin's commitment record is the only editable record of
  task state, checkpoints and task decisions for work run through these
  tools. Standalone heimdall's task, checkpoint and decision layer is
  retired by a one-time import, not bridged: each native record is
  imported with its original identity and revision as provenance, and
  later heimdall-side edits are refused. Delegations, approvals, verdicts
  and run states remain the execution backend's records (D4, D17). The
  commitment record references them and never copies their authority.
- **Consequences:** Commitment (§2, Appendix A) gains checkpoint and
  task-decision fields. Import is a migration step (§14) with a receipt.
  New EC-13 (import and retirement) and new AC (idempotent import; refused
  post-import edit). EC-05 and AC-20 are withdrawn, ids kept. I5 loses
  "heimdall external views". The human view shows run and delegation state
  attributed to the backend.
- **Inherited relationship:** supersedes D20.10 for Odin. Amends D10.5's
  "Optionally connected later as a human-facing continuity surface" and
  its release/CI condition. Consistent with D10.5's "one authoritative
  record", §1.b and D7.11.
- **Must not claim:** that heimdall's record or the skald–heimdall
  amendment has changed (that needs decisions recorded in those
  repositories); authority over delegations or approvals (D17, D2.1); that
  imported checkpoints corroborate anything independently (D22.4).

### ODIN-ADR-008 — I0 narrowed to the event log and record schemas

- **Status:** locked sequencing within Odin; no phase change.
- **Context:** I0 today bundles schemas, the event envelope, the capability
  matrix, the fake backend, the three-document fixture, the ownership
  mapping and the planner isolation check. The substrate and record
  schemas are the shared prerequisite for everything else.
- **Decision:** I0 delivers the versioned event envelope and namespaces
  (EC-01, ADR-006), the record schemas of I/O §2 and Appendix A (with the
  changes in ADR-007 and ADR-009), and fixtures for the duplicate, stale
  and unknown cases. The adapter capability matrix, the fake Saga backend,
  the synthetic three-document fixture and the ownership mapping move to
  I1. The planner tool-isolation check moves with the profile schemas and
  must still pass before I2 claims the planner profile.
- **Consequences:** blueprint §7, I/O §13 row B, ROADMAP I0/I1, README and
  AGENTS.md §1 change together. I0's exit keeps "no peer API is invented
  as implemented".
- **Inherited relationship:** within D14.4 (increments govern) and D15
  (phase B/C mapping unchanged). X-9 is restated, not reopened on phases.
- **Must not claim:** any phase or gate change; resolution of X-1; that
  any displaced item was dropped. Each must be named in its new increment.

### ODIN-ADR-009 — Workstation daemon and session host

- **Status:** default design; not implemented.
- **Context:** native SDK and RPC sessions, Herdr control and human
  surfaces live on the operator's machine, while records and authority
  live in the homelab service. Bindings already carry `host` and
  `incarnation` (I/O §2, Appendix A) but have no offline state or
  environment evidence.
- **Decision:** A workstation daemon runs on the operator's machine. Its
  session host dials out to the Odin service, registers a stable host
  identity, and starts, resumes, interrupts and retires SDK and RPC harness
  sessions only on the service's command. Session records, ownership
  generations and budgets stay in the service. A binding whose host is
  unreachable becomes `host_offline`: its sessions count as unavailable,
  not failed, and nothing is retried until the host returns and
  reconciles. Each host publishes an Environment record from a
  deterministic probe (harness and Herdr versions, sandbox and isolation
  support, available surfaces). The service refuses session classes whose
  required capabilities the record lacks.
- **Consequences:** I/O §7 isolation must be provided on the workstation,
  or the planner class is refused there. The model credential for local
  sessions lives in a protected store on the host, referenced by the
  service, with one refresher per lineage. It is never the operator's
  development login. Herdr is driven through its CLI (structured; DC-08);
  §3 item 8 stays open. Stop works with the host offline and reports
  uncertain local outcomes (AC-10). New ACs as in B.5; new EC (session
  host protocol); new X (credential lineage).
- **Inherited relationship:** clarifies D7.2 and D20.1–D20.2. Amends D24.3
  for Odin's session classes only. Preserves D24.4a, D24.6, D20.6–D20.7 and
  D23.3's stated missing guarantees.
- **Must not claim:** Saga guarantees for anything the host runs (D23.3);
  that sensor observations are authority; that Herdr's automation API has
  been reviewed; that development-login use is permitted.

### ODIN-ADR-010 — Operator surfaces, new inbound sources and typed nudges

- **Status:** default design; voice is backlog until its data-policy
  decision.
- **Context:** D20.5 names two interfaces (Herdr and Telegram). The
  consolidation adds a bar, notifications and voice, plus inbound
  observations and capture lifecycle events, and an outbound attention
  prompt.
- **Decision:** Operator surfaces (terminal workspace, Telegram, status
  bar, desktop notifications, voice) are adapters on one service API, and
  every one enters the same recorded command path. Heimdall-derived
  observations and capture lifecycle events are typed inbound sources.
  They are recorded as state-only or log-only by default, are never
  authority, and wake a planner only through typed rules. A nudge is a
  typed outbound effect, either an operator attention prompt or a message
  queued to an Odin-run session through the adapter's supported injection,
  with per-surface and per-session caps, dedupe and expiry. It is never a
  synthesized keystroke and never guidance to a Saga run.
- **Consequences:** an approval is accepted only on a surface that shows
  the request id and proposal digest (AC-06, AC-30). Voice may carry
  questions, clarification answers and stop, never an approval, until a
  hash-binding mechanism exists. Voice transcription needs the L-VT-2
  data-policy decision (new X). No evaluator handles operator input (D9.3).
  Take control suspends nudges to that session (AC-11). Caps are logged as
  in §4 (AC-23). New rows go into I/O §3 `src`, §4, Appendix C and the
  outbox destination table.
- **Inherited relationship:** supersedes D20.5's "Two operator interfaces"
  while retaining its other rules. Amends D20.8. Preserves D20.9, D20.11
  (Herdr and Telegram stay the first configuration), D9.5, ADR-002 and
  ADR-004's four hooks. Supersedes L-PU-1's legacy "nudge" meaning.
- **Must not claim:** voice approvals; a fifth evaluator hook; that
  observations change commitments; that the extra surfaces are part of the
  restrained initial product (D19.6).

### ODIN-ADR-011 — Desktop input as a gated capability of the workstation daemon

- **Status:** default (as D21); disabled until the operator decides §3
  item 9.
- **Context:** D21.4 requires a lease enforced "at a shared broker or tool
  boundary across cooperating clients". The workstation daemon is the
  natural single holder.
- **Decision:** Guarded desktop input runs in its own process within the
  workstation daemon. That process is the only holder of the input devices
  and holds the exclusive desktop-seat lease for every client. It is
  disabled until a delegation naming desktop authority exists and the
  operator has decided §3 item 9. When enabled, it serves only a dedicated
  desktop worker, never a planning session, the session host or a
  container worker. Its observation and input MCP servers remain usable
  without hosted inference.
- **Consequences:** EC-10 becomes this process. DC-01–DC-08 apply
  unchanged. The capability's guards stay in force (D21.5).
- **Inherited relationship:** amends D10.4's placement and preserves its
  isolation rule. Implements D21.4. Preserves D0.5, D2.3, D21.1, D21.6,
  D21.7 and D23.4.
- **Must not claim:** that desktop authority is granted; inclusion in the
  initial product; Saga admission for desktop work (contract SCOPE-6);
  that a classifier can override a guard (DC-03).

### ODIN-ADR-012 — Preservation without dotprivate on Odin's dependency path

- **Status:** locked direction; carrier undecided.
- **Context:** D22.3 names dotprivate as the carrier, but its
  selected-files contract is unimplemented (EC-08) and the operator wants
  it off Odin's path.
- **Decision:** Odin does not depend on dotprivate. Odin produces the
  selected project package (D22.1) for a preservation carrier the operator
  chooses later. Until one is chosen, packages are retained locally and
  reported only as "copied locally". Any carrier must report "committed"
  and "confirmed on the remote" separately and never claim remote
  durability it has not confirmed.
- **Consequences:** EC-08 and EC-09 are withdrawn from Odin's plan (ids
  kept). AC-24 and AC-25 are retargeted or deferred. §3 item 10 becomes
  dotprivate's own question. Full-archive backup ownership moves with the
  capture module (D22.2). D18.5 step 7 reads "preserved by the chosen
  carrier".
- **Inherited relationship:** supersedes D22.3's "Dotprivate carries the
  package" and D22.5 for Odin. Preserves D22.1, D22.4 and the three-state
  rule.
- **Must not claim:** remote durability; any change to dotprivate's
  contract or license (ADR-001); that AC-24 or AC-25 pass.

### ODIN-ADR-013 — Two reviewer positions with service-run consensus

- **Status:** **hypothesis.** It stays only if it beats single review and
  an equivalent extra verification budget on D8.7's measures.
- **Context:** D8.5 notes that "Opus and Sonnet share a family and their
  errors are not independent". Two frontier models of different families
  test whether independence prevents more defects. Use "reviewer position"
  (or similar), not "seat", because of D21.4 and §3 item 6.
- **Decision:** Required review is performed by two reviewer sessions on
  frontier models of different families. Each gets the same deterministic
  evidence pack and sees neither Odin's reasoning nor the other's
  findings. Service code combines the verdicts. Approval requires both to
  approve. Any `REJECT` or `INSUFFICIENT_EVIDENCE`, or disagreement after
  the single permitted corrective re-review, goes to the operator. The
  combined verdict is recorded under the service-held reviewer identity
  key, in the verdict format the backend verifies.
- **Consequences:** D24.2a launch configuration per position. Odin's D0.7
  wording is updated if one position is not Anthropic. Sending evidence
  packs to a second provider needs a data-policy decision (new X). Caps
  are per position and total (D8.6). AC-22 is re-scoped and a
  disagreement AC added. D18.2 measures the consensus arm. Consensus stays
  switchable (D19.3).
- **Inherited relationship:** supersedes D8.5 and the single-reviewer
  reading of D8.3–D8.4 (the bounded rounds are kept). Amends D2.5's wording
  and D13.2a if the Mimir name is retired. §3 item 2 stays open.
- **Must not claim:** that the backend accepts per-position verdicts (that
  would be a Saga contract change, B-10); that a decision model settles
  disagreement (D9.1); waiver when a position is unavailable (AC-22); a
  resolution of X-7; independence of errors before measurement.

### ODIN-ADR-014 — Session-class decisions recorded for later evaluation (amends ODIN-ADR-004)

- **Status:** default; evidence only.
- **Context:** ADR-004 makes code choose session classes but keeps no
  record of the rejected alternatives. That record is needed to judge
  those choices later against an independent oracle.
- **Decision:** Each code-made session-class selection records the chosen
  class, the rejected candidate classes with their deterministic reasons,
  the inputs used and the configuration revision, so that an independent
  outcome assessment can evaluate the choice later. The record never
  changes routing at run time. Changing routing on the basis of these
  records requires D9.4's review, replay and shadow period.
- **Consequences:** records live in the Odin-history namespace (ADR-006),
  subject to D9.5's sensitivity rule and D7.12's redaction. New classes
  (review positions; Bragi and Eir if ADR-017 takes effect) are added to
  ADR-004's class table.
- **Inherited relationship:** amends ADR-004. Keeps its four hooks, its
  "no silent downshift" and its "no learned model-tier router".
- **Must not claim:** that a learned router or oracle exists; a fifth
  hook.

### ODIN-ADR-015 — Early Pi RPC adapter as a control

- **Status:** locked experiment placement; fixture-only.
- **Context:** D19.5 wants the second adapter "early enough to test whether
  the boundary is real". The roadmap's Codex experiment is "a proposal, not
  an ADR or a changed gate" (DECISION-MAP).
- **Decision:** After I2's exit, a minimal Pi RPC adapter runs the same
  bounded assignment and session replacement against the fake backend, as
  a control for the Claude Code adapter, and publishes its capability
  matrix and gaps. It is non-production and fixture-only. The full second
  adapter and Phase E's exit remain I5. No common adapter framework is
  extracted until both adapters exist.
- **Consequences:** Claude models through Pi use an API key, never the
  subscription (AGENTS.md §6; D24). Odin's D0.7 wording changes if Pi runs
  other providers' models. It replaces the ROADMAP Codex proposal, or the
  two run side by side if both are wanted. Evidence is labelled fake-backend.
- **Inherited relationship:** amends D15.Eb's timing for an early control
  only. Honours D7.6 by starting after the Claude Code adapter is
  validated at I2. Satisfies D19.5.
- **Must not claim:** Phase E's exit; any live run before Phase B; X-1
  resolution; proven portability.

### ODIN-ADR-016 — Execution backend: Saga in its own process (conditional)

- **Status:** **conditional.** It takes effect only after the operator
  records the matching decision in Saga's record (SAGA-ADR-nnn), Saga
  publishes a new contract version, and Odin pins it.
- **Context:** the consolidation wants one homelab deployable. D1.3, D2,
  D4, D5, D17 and D23.2 require that the enforcer be Saga and that Odin
  reach it only through its API.
- **Decision:** The execution backend is Saga. Its code may share a
  repository and release train with Odin. It runs as a separate,
  independently restartable process with its own store and decision
  record. It is the only holder of the Docker socket, and it alone admits
  runs, binds approvals and verdicts, enforces limits, runs the D5
  lifecycle and executes stop. Workers report to Saga's own intake, which
  replaces MQTT and Saga events only by Saga's decision. Odin's intake
  consumes Saga's event cursor and never receives worker transport. The
  Odin service links no Saga enforcement module and reaches Saga only
  through its API.
- **Consequences:** a build rule prevents Odin code from importing Saga
  enforcement modules (G4). The Odin service restarts without restarting
  Saga (D1.4a, AC-03). The same API serves the CLI and a third-party agent
  (D3.2, D18.1). Saga's conformance checks (contract §19) must pass before
  any guarantee is claimed. Appendix B is rechecked at the repin (X-3).
  The stop split is stated, and X-2 closes only through Saga's record.
  X-6 is restated.
- **Inherited relationship:** honours D1.3, D2, D4, D5, D17 and D23.2
  unchanged. Supersedes nothing Saga owns. Amends I/O §1, §10, §14 and the
  Appendix B note.
- **Must not claim:** Saga's guarantees from co-location; that Phase B is
  met; closure of X-1 or X-2; any edit to the pinned copy; that Odin's
  intake carries worker events.

### ODIN-ADR-017 — Odin-side interfaces if Bragi and Eir move (conditional)

- **Status:** **conditional** on a SAGA-ADR transferring D12.1 and D11's
  Eir clauses (and the matching part of D1.2).
- **Decision:** If Saga's record transfers them, Bragi runs as a scheduled
  Odin session class, and Eir work becomes an Odin assignment class
  executed through the execution backend. Eir keeps an operator-invoked
  path that needs neither the Odin service nor the execution backend to be
  running, and the operator remains the merge gate. Eir patches that
  change system behaviour still get required review (D8.1).
- **Consequences:** D12.2–D12.3 become internal. B-16 is withdrawn at that
  point (id kept). D24.2a gains both classes. Bragi reads the ledger only
  through the backend's API.
- **Must not claim:** any transfer before Saga records it; resolution of
  X-8 or R-S1.

### ODIN-ADR-018 — Repository consolidation (conditional)

- **Status:** **conditional** on a matching decision in Saga's record for
  D14.1 and D14.7 (and D13.1's prefix if changed), a recorded D14 handoff
  or a Saga-recorded replacement for it, and decisions recorded in the
  heimdall, skald, braid and wayland-computer-use repositories.
- **Decision:** Odin, Saga, heimdall's surfaces and sensors, skald's
  capture, braid and wayland-computer-use's guarded input live in one
  repository with one release train. Each component keeps its own decision
  record or a recorded owner, its own versioned interface with
  compatibility tests, and its own process boundary. Capture and sensors
  stay runnable standalone. dotprivate, muninn and Herdr stay outside.
- **Consequences:** Saga's record and contract move as Saga's and stay
  Saga-owned. Pinned snapshots give way to in-repo versioned contracts plus
  compatibility checks; the pinned 2026-10-14 copy stays as history.
  AGENTS.md §3 "Never edit Saga or any peer repository from this one"
  becomes a per-component ownership rule, keeping the Docker, host and
  secret prohibitions. Each imported repository's history arrives with a
  provenance manifest. Each component keeps its license until the operator
  records otherwise (ADR-001). Phase gates stay per component (D15.8).
- **Inherited relationship:** supersedes for Odin D10's title and D10.6
  ("Nothing rolls into Odin"), and D14.1's Odin side. Amends D14.3–D14.4,
  D15.C ("in the `odin` repo") and D16.2.
- **Must not claim:** authority from co-location; amended peer or Saga
  records; a unified license; a recorded handoff.

### ODIN-ADR-019 — Deliverable names and prefix (resolves X-5)

- **Status:** open until the operator chooses.
- **Decision (shape):** the operator chooses the repository name, the
  deliverable prefix(es), and the names of the homelab service, the
  workstation daemon and the harness integration packages, within §E's
  constraints. The `saga-odin` container and image (D13.6) get their new
  names here.
- **Must not claim:** any change to Saga's `saga-` prefix rule (D13.1,
  shared). That needs Saga's record.

---
## D. Document-change plan

### D.1 Which documents change, and how

"Manifest output" means the file is a `destination_path` in
EXTRACTION-MANIFEST.json. Any edit requires updating its
`adapted_output_sha256` and appending to its `transformation` note. Source
hashes must never change.

| Document | Manifest output? | Kind of change | Driven by |
|---|---|---|---|
| `docs/DECISIONS.md` | **Yes** (`split`) | §4: new ADRs. Under each affected `Dn` heading, add an ownership note "superseded/amended in part by ODIN-ADR-0nn" **without editing the verbatim carried text** (D10, D14, D20, D22, D8 carry source text verbatim). §3: annotate items 5, 6 and 10 (and 1 as a prerequisite). §5: annotate X-5, X-6, X-9; add X-11 onward; X-1, X-2, X-7, X-8 unchanged. Header: note the first supersession of inherited clauses | 006–019 |
| `docs/provenance/DECISION-MAP.md` | No (the validator requires it to contain every `SAGA-2026-10-Dn`) | Fill the "Supersession / notes" column for each superseded or amended clause (D0.7, D1.1, D2.5, D7.2, D7.6, D8.3–D8.5, D10 title, D10.1, D10.2, D10.4, D10.5, D10.6, D13.2a, D13.6, D14.1 (Odin side), D14.3, D14.4, D15.C, D15.Eb, D16.2, D18.5, D19.3, D20.1, D20.5, D20.8, D20.10, D22.2, D22.3, D22.5, D24.2a, D24.3). Add rows 006–019 to "Odin decisions after bootstrap". Add a section listing clauses superseded by ODIN-ADRs, keeping "No decision clause has been superseded on its merits by this extraction", which stays true of the extraction. Mark conditional ADRs as not in effect | all |
| `docs/design/ODIN-IO-CONTRACT.md` | **Yes** | Header (EC and AC ranges); §1 store table; §2 Commitment (checkpoints, task decisions), SessionBinding (`host_offline`), Environment record; §3 `src` and `chat` namespaces; §4 new inbound rows, nudge class and caps; §5 session classes; §6 `recall` as a library, `notify_operator` vs nudge; §7 isolation on the workstation, desktop process; §8 cross-namespace redaction; §9 substrate (keep transaction semantics); §10 Mimir → positions, operator surfaces, skald/braid/heimdall in-repo; Eir and Bragi conditional; §11 Pi early, session host; §13 table; §14 heimdall import, MQTT bridge (X-6); §15; Appendices A, C, D. Appendix B **only** after a Saga repin | 006–016 |
| `docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md` | **Yes** | §2 topology; §3 component table (Heimdall, Skald, Braid, WCU, dotprivate rows); §5 surfaces; §6 Mimir → positions; §7 increments (I0, I5 without heimdall views, Pi control, I6, I7) | 006–015 |
| `docs/ROADMAP.md` | **Yes** (`split`) | I0/I1 contents; Pi control; I5 without EC-05; Phase F without dotprivate (EC-08/09); gate table (G-8 re-scope; G-9 Saga-side record; G-10 peer records); increment summary; Phase A checklist (record ADRs) | 008, 012, 015; 016–018 as gates |
| `docs/design/ODIN-ACCEPTANCE-SCENARIOS.md` | **Yes** | Header ranges; withdraw or re-scope notes for AC-19, AC-20, AC-22, AC-24, AC-25 (**ids kept in text**); AC-37 onward; §1 walkthrough "Visibility" row (one view, three truths); §4 release scopes | 007, 009–013 |
| `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | **Yes** | Preamble ("independent products ... does not merge their databases") superseded for the merged components; §1 baseline; §5 heimdall (bridge superseded); §6–§8 in-repo; §9 dotprivate off the path; §10 EC table: annotate EC-04, -05, -08, -09; add EC-13 onward. Keep peer-proposal status for Herdr and dotprivate. Until 016–018 take effect, it is the right home for the Saga-owned proposals, labelled as proposals | 006–018 |
| `docs/provenance/LEGACY-REQUIREMENTS.md` | **Yes** (destination of **three** manifest entries) | L-VT-1/2 disposition (voice), L-PU-1 ("nudge" redefined) | 010 |
| `README.md` | **Yes** | First-milestone I0 list; product description stays (Saga separate) until 016 and 018; repository framing only after 018 | 008; 018 |
| `CLAUDE.md` | **Yes** | Only if the monorepo changes the integration-package directory rule (after 018) | 018 |
| `AGENTS.md` | No (required by the validator) | §1 I0 wording; §4 architecture (substrate; one transactional core restated); §6 workstation credential separation; §7 names list (add dotprivate; terminology "reviewer position", "nudge"), "Peers are proposals until pinned" (after 018); §3 "Never edit Saga or any peer repository" (after 018 only) | 006, 008, 009, 013; 018 |
| `docs/README.md` | No | Identifier ranges (AC, EC, X); reading-order note on conditional ADRs | all |
| `docs/contracts/README.md` | No | Inventory rows for heimdall, skald, braid, WCU (in-repo after 018), dotprivate (off the path) | 012, 018 |
| `docs/provenance/HANDOFF.md` | No | New receipt section for the decision pass (precedent: each operator-directed pass is recorded there) | all |
| `docs/provenance/EXTRACTION-MANIFEST.json` | — (immutable source identities) | Update `adapted_output_sha256` and append to `transformation` for every manifest output edited. Never touch `source_sha256` or add history files | — |
| `scripts/validate_docs.py` | No | Recommended: protect AC-31 onward, EC-13 onward, X-n and ODIN-ADR ids; no change is *required* | — |
| Frozen history, pinned contract, research copies | Immutable | **No edits** | — |

### D.2 What the validator will check

- Every manifest output's bytes match `adapted_output_sha256`. All three
  LEGACY-REQUIREMENTS entries must carry the same new digest.
- `transformation` is non-empty. Only presence is checked, not content.
- Snapshot bytes and the allowlist are unchanged. Adding a file under
  `docs/history/saga-extraction/2026-10-14-14fdab3/` fails.
- DECISION-MAP.md contains `SAGA-2026-10-D0` through `D24`.
- The four design documents together contain every frozen AC/DC/EC id and
  AC-01–AC-30, DC-01–DC-08, EC-01–EC-12. **A withdrawn AC-20, EC-05, EC-08
  or EC-09 must remain textually present.**
- The pinned Saga contract digest matches `SNAPSHOT.json`. A new pin needs
  its own `SNAPSHOT.json` with `producer_repository == "saga"`.
- Local links and anchors resolve. New ADR headings produce anchors such as
  `#odin-adr-006--...`; renaming an existing heading breaks links such as
  README's `#odin-adr-001--project-license`.

**Not checked:** ADR, X, B, G, I and L identifiers; AC-31 onward; semantic
agreement with the frozen copy; whether an ADR exists for a given edit; the
Saga-owned/Odin-owned boundary. A pass "proves documentation integrity, not
semantic completeness" (AGENTS.md §8).

### D.3 Order of operations, and why

The live documents "must agree with the frozen copy except for explicitly
recorded operator decisions in Odin's ADRs". Any edit to a design document
that departs from the frozen text is therefore a violation until the ADR
authorizing it exists. Sequence:

1. Commit the current working tree, so that ADR-001 to 005, AC-31 to 36
   and the exception clause exist at HEAD. Run the validator.
2. Operator decides. Record the Odin-only ADRs (006–015) in
   `DECISIONS.md` §4 **and** update the DECISION-MAP supersession columns
   in the same change.
3. Edit subordinate documents in authority order: I/O contract, then
   blueprint, then roadmap; acceptance scenarios and ecosystem plan
   alongside.
4. Edit entry documents: README, docs/README, AGENTS.md; CLAUDE.md only
   when 018 takes effect.
5. Update the manifest digests and transformation notes **last**, after the
   final bytes of every manifest output.
6. Write the HANDOFF receipt section (not a manifest output). Run
   `python3 scripts/validate_docs.py`. Do a manual semantic check against
   the frozen copy.
7. Leave 016–018 as labelled proposals in the ecosystem plan until Saga's
   record, a new contract pin and the peer records exist.

## E. Naming

### Constraints any name must satisfy

1. **Plain functional name.** The monorepo and all three deployables are
   deterministic components or repositories. Under D13.1, "Every
   deterministic component, directory, image, topic and tool gets a plain
   functional name". Norse names are only for persona-bearing, judging
   agents.
2. **No mythology.** "Mythological places and metaphors appear only in
   Odin's identity paragraph" (D13.1). D13.7 removed Huginn, Muninn (as a
   metaphor), Nidavellir, Midgard, Yggdrasil, Hliðskjálf and Svartalfheim.
3. **No standalone-repository name, including for absorbed modules.**
   "Never reuse a name used by one of the operator's standalone repos"
   (D13.1). Inside the monorepo, the absorbed components become
   deterministic components and need new functional names.
4. **Prefix discipline.** `saga-` is reserved for Saga deliverables
   (D13.1, shared). It may name the execution backend only while that
   backend is Saga, and never the Odin service, the daemon or the
   integration packages. No Odin prefix exists (X-5); one must be chosen by
   operator decision (ADR-019). Plain functional names apply until then.
5. **Do not imply a product boundary that does not exist.** Naming the
   monorepo or the homelab deployable `odin` or `saga` implies the other
   product is part of it, against D1's two products. D14.1 sanctions the
   `odin` and `saga` repository names only for two separate repositories.
   Keeping `odin` as the monorepo name is possible only by explicit
   decision recorded in both records.
6. **No collision with recorded terms.** Avoid worker, run, stream,
   delegation, commitment, assignment, planning session, evaluator (D13.8),
   Saga launcher, Saga events and Saga adapter for anything else. Avoid
   "seat" for reviewers (D21.4 seat lease; §3 item 6). Avoid "nudge"
   without a definition (L-PU-1). Avoid "agent" for deterministic
   deployables (persona confusion).
7. **Banned agent synonyms:** overseer, navigator, critic, judge, master
   (D13.9). This matters for naming the two reviewer positions.

### Forbidden names

| Category | Names |
|---|---|
| Standalone repositories | `heimdall`, `skald`, `braid`, `muninn`, `wayland-computer-use` (and `wcu` as its short form), `dotprivate` |
| Third-party product | `herdr` / Herdr |
| Agent names (persona only) | Odin, Mimir, Eir, Bragi for deterministic components. Saga only for the execution service and its deliverables (`saga-` prefix) |
| Removed metaphors | Huginn, Muninn, Nidavellir, Midgard, Yggdrasil, Hliðskjálf, Svartalfheim |
| Other mythological places | Asgard, Valhalla, Bifrost and similar (D13.1) |
| Legacy names | dvergr/dvergar, instance (for run), Ratatoskr, Heimdall (for the launcher), `saga-dvergr` |
| Banned agent synonyms | overseer, navigator, critic, judge, master |
| Collision-prone terms | "seat" (reviewers), "evaluator" (anything but D13.8's meaning), bare "nudge" |

Names that follow the existing pattern are descriptive phrases such as
"Odin service", "harness integration package" (both in D1.1) and
"workstation daemon". A final name needs ADR-019.

## F. Risks to documentation integrity and governance, and recommended sequence

### Risks

1. **Uncommitted baseline.** Consolidation ADRs would be stacked on
   uncommitted ADR-001 to 005 and on an uncommitted exception clause. HEAD
   still forbids any divergence from the frozen copy.
2. **First supersession of locked inherited clauses while Saga's record is
   authoritative.** Two records disagree, with no joint master and no
   handoff. A reader of Saga's record sees D10 and D20.10 as locked.
3. **Ownership laundering.** Co-locating Saga's code may tempt edits to
   Saga-owned text (D2, D4, D11, D12, D17), to the pinned contract, or to
   Saga's wording through Odin documents. All are forbidden (AGENTS.md §3;
   `contracts/README.md` rule 1).
4. **Guarantee laundering.** Describing "the execution backend" as having
   isolation, limits, durable records or recovery without Saga's identity
   and conformance (AGENTS.md §5; D23).
5. **Identifier loss.** Deleting withdrawn ids. The validator protects only
   AC-01–30, DC and EC-01–12; AC-31 onward, X, ADR, B, G, I and L are
   review-only.
6. **Silent closure.** The consolidation story reads as if it answers X-1,
   X-2, X-6, X-7, X-8 and §3 items 1, 8 and 9. It answers none of them.
7. **Edits to verbatim carried text.** Editing D10, D14, D20 or D22 text
   breaks the "carried verbatim" provenance. Annotate instead.
8. **Manifest churn.** Forgetting a digest (the validator catches it).
   Updating only one of the three LEGACY-REQUIREMENTS entries. The
   temptation to "fix" a source hash (forbidden).
9. **Proposals masquerading as decisions.** Drafting ADR text into §4, or
   edits into design documents, before the operator decides.
10. **Gate erosion.** One release train blurring Phase B's exit with I3
    (D15.8, PH-3), or making the backend Odin-specific (D3.2, D18.1).
11. **Security-boundary erosion in practice.** Shared store or failure
    domain (D4.1, D11.3); joint restarts (D1.4a); Odin importing Saga
    enforcement code (G4); the session host reaching the backend API
    (B-00).
12. **Credential-domain mixing on the workstation** (D24.3, D24.6;
    AGENTS.md §6; CLAUDE.md).
13. **Peer records contradicted.** The skald–heimdall amendment still
    assigns accepted task state to heimdall until heimdall records
    otherwise.
14. **Data policy drift.** Hosted voice transcription (L-VT-2); a second
    reviewer provider receiving evidence packs; desktop text in
    observations (D9.5, DC-07).
15. **Licensing.** Merging repositories under one Apache-2.0 notice without
    per-component decisions (ADR-001; §3 item 5).
16. **Scope creep against D19.6, D20.11 and D0.5.** Surfaces, voice,
    desktop and Bragi/Eir entering the first proof.

### Recommended sequence

1. **First:** commit the working tree and validate. Ask the operator for §3
   item 1 (is Saga active?) and the fork decision: does the execution
   backend remain Saga (identity, record, contract)? Everything in 016–018
   depends on that answer.
2. **Record (Odin only, now):** ADR-013 and ADR-014 (no dependencies;
   D8 is "default"); then 006, 007, 008, 009, 010, 011, 012, 015. Each
   states that Saga's record is not amended. Each conditional consequence
   carries its own gate. Update DECISION-MAP in the same change.
3. **Edit second:** the design documents in authority order, then the
   entry documents, then the manifest digests and transformation notes,
   then the HANDOFF receipt, then the validator and a manual frozen-copy
   check.
4. **Outside this repository (operator, not from here):** a SAGA-ADR for
   backend placement, the MQTT/ratatoskr replacement by Saga's own intake,
   Bragi/Eir transfer with Eir's out-of-band path, D14.1/D14.7, and the
   D13 prefix if needed. A new Saga contract version, then repin in Odin
   with Appendix B rechecked. Decisions in heimdall (task authority and
   import), skald, braid and WCU.
5. **Then:** record or replace the D14 handoff. Record ADR-016, then 017,
   then 018 and 019. Only then edit AGENTS.md §3, CLAUDE.md and the
   repository framing in README.
6. **Leave as proposals until step 4 is done:** 016, 017, 018, the MQTT
   replacement, the naming of Saga-side deliverables, and any statement
   that the homelab deployable contains Saga.
