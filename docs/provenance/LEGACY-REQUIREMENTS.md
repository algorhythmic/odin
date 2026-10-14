# Legacy requirements triage

Status: candidate, written for extraction snapshot `2026-10-14-14fdab3`.
This file records what happens in Odin to requirements found in the
legacy documents captured in the
[snapshot](../history/saga-extraction/2026-10-14-14fdab3/). Those
documents describe the April 2026 implementation (one tmux Claude Code
session, file mailboxes, `tmux send-keys` nudges, MQTT sidecars).
Their phase numbers ("Phase 3", "Phase 4+") are legacy and **do not
become Odin commitments**. Scheduling is decided only in the
[roadmap](../ROADMAP.md) and the decisions it cites.

Dispositions:

- **Carried**: already a requirement in a live Odin document (cited).
- **Superseded**: the mechanism or rule is replaced by a decision or
  the contract (cited); its intent survives where noted.
- **Saga-owned**: belongs to Saga; not imported into Odin.
- **Persona input**: behavioural guidance to carry into the Odin or
  Mimir instructions derived at code extraction (extraction plan §7).
  A behavioural rule should be paired with the check that enforces it,
  or a ticket for one.
- **Backlog**: a candidate Odin capability, unscheduled unless a phase
  is named.
- **Needs decision**: legacy and current documents disagree or are
  silent; an issue is recorded and nothing is resolved here.

Legacy status is quoted from the source document and has not been
re-verified.

## Proactive updates — [`docs/features/odin-proactive-updates.md`](../history/saga-extraction/2026-10-14-14fdab3/docs/features/odin-proactive-updates.md)

| ID | Legacy requirement | Legacy status | Disposition | Odin location / next step |
|---|---|---|---|---|
| L-PU-1 | Odin tells the operator about milestone events (worker completed, errored, test regression, convergence) without being polled | Tier 1 implemented (tmux nudges) | Carried; mechanism superseded | I/O contract §4 (status transitions incl. test regression wake the planner; alerts; `notify_operator`); `send-keys` nudges are replaced by event intake (D7.7) |
| L-PU-2a | Structured session status tool | Tier 2 scoped | Carried | `fleet_status` (I/O contract §6) |
| L-PU-2b | Project timeline (per-iteration history: test trends, guidance adoption, time per iteration) and progress chart tools | Tier 2 scoped | Backlog | Unscheduled; data from Saga evidence (B-03, B-06); guidance adoption overlaps Bragi's guidance-effectiveness table (D12, Saga) |
| L-PU-3 | Periodic session digest to Telegram | Tier 3 scoped | Backlog | Building blocks carried (`set_timer`, `notify_operator`, digests of deferred entries in I/O contract §4); a scheduled operator digest and its cadence need an operator choice |

## Spec development — [`docs/features/spec-development.md`](../history/saga-extraction/2026-10-14-14fdab3/docs/features/spec-development.md)

| ID | Legacy requirement | Legacy status | Disposition | Odin location / next step |
|---|---|---|---|---|
| L-SD-1 | Capture design decisions and rejected alternatives with each spec; flag a spec without rationale before proceeding; compile decisions into the project wiki; Mimir checks the decomposition against the rationale | Scoped; partly present in the legacy persona (`wiki/rationale.md` from `/spec-dev compile`; Mimir `rationale_check`) | Backlog; persona input | Spec-ingestion skill of the integration package (I/O contract §11); evidence packs (D8.3) can carry the rationale |
| L-SD-2 | Development log as a wiki citizen (`raw/dev-log.md`, `wiki/rationale.md`) | Scoped | Backlog | After Phase C, where "the dev-log becomes a chat log slice" (Saga roadmap carry-over) |
| L-SD-3 | Spec-dev conversational mode | Source said "defer indefinitely"; the legacy persona documents a built version (L-OP-17) | See L-OP-17 | — |
| L-SD-4 | If dev-log rationale contradicts the final spec, the spec wins and the contradiction is flagged for the operator; Mimir is the natural catcher | Caveat | Persona input | Spec-ingestion skill; Mimir decomposition review |

## Voice over Telegram — [`docs/features/voice-telegram.md`](../history/saga-extraction/2026-10-14-14fdab3/docs/features/voice-telegram.md)

| ID | Legacy requirement | Legacy status | Disposition | Odin location / next step |
|---|---|---|---|---|
| L-VT-1 | Operator sends voice notes and may receive voice replies | Scoped, not implemented; unscheduled | Backlog | Unscheduled (Saga roadmap carry-over). If built, it is a feature of Odin's own Telegram adapter (D7.7), not a tmux or file-queue sidecar |
| L-VT-2 | Hosted speech-to-text and text-to-speech (OpenAI proposed), key stored as a secret | Proposal | Needs decision | Voice notes are operator message content; D9 restricts operator-derived content to the local provider for decision models, and the same sensitivity question applies to a hosted transcription provider. Any key is a credential reference (D24.3) |

## Odin's legacy persona — [`odin/CLAUDE.md`](../history/saga-extraction/2026-10-14-14fdab3/odin/CLAUDE.md)

The legacy persona is runtime behaviour, not developer instructions
(extraction plan §7). Its filesystem mailboxes, mount paths and
deployment assumptions are dropped when Odin's instructions are derived.

| ID | Legacy requirement | Disposition | Odin location / next step |
|---|---|---|---|
| L-OP-1 | Identity paragraph with Norse metaphors (Nidavellir, Huginn and Muninn, Midgard, Yggdrasil) | Superseded in part; persona input | D13.1 allows myth only in Odin's identity paragraph; D13.7 removes the listed metaphors |
| L-OP-2 | Read Saga's documentation through a read-only repository mount | Carried | `read_file` scope `/workspace/saga-repo/**` (I/O contract §6) |
| L-OP-3 | Worker workspaces are read-only and for post-hoc verification only: never read a running worker's workspace for live monitoring | Carried (read-only scope); rule is persona input | I/O contract §6; candidate check: refuse workspace reads for runs in `started`. Needs a ticket |
| L-OP-4 | Memory is `master-journal.md`, re-read on every start, plus registry, state file and lessons | Superseded | D7 memory (log, tree, briefing) and commitment records; the master journal is imported once (I/O contract §14) |
| L-OP-5 | Every log entry has Events / Observations / Evidence / Implication; empty sections are written as `none` with a reason | Carried (shape); persona input (empty-section rule) | I/O contract §5 output |
| L-OP-6 | Project-completion ritual (Mimir flag retrospection, estimate accuracy, pattern extraction, failure-mode catalog, "what I would do differently"); a project is not complete without it | Carried in part; needs decision | Retrospective skill (I/O contract §11). Whether the retrospective is an acceptance criterion for closing a project commitment is not decided |
| L-OP-7 | Spec ingestion: raw spec immutable, revisions as siblings; compile a wiki; extract contracts byte-identically, never paraphrased, superseded rather than edited; validate the compiled wiki with the operator before decomposition; per-stream contract dependencies; record the decomposition decision; lifecycle events | Carried in part; persona input | Project source documents with digests (I/O contract §2); contracts never edited in place (§6); byte-identical contract checks as mechanical evidence (D8.2); spec-ingestion and decomposition skills (§11); acceptance §1 intake. Operator validation of the compiled wiki before decomposition is persona input |
| L-OP-7b | Launch by moving request files; `gitea_credentials: saga-push` in every launch request | Superseded; Saga-owned | `submit_run` through Saga (D1.3); repository-scoped credentials are Saga's launch configuration (D2.2) |
| L-OP-8 | Decomposition strategy: independent, competitive (2–3 attempts) or hybrid, by boundary clarity and risk | Persona input | Decomposition skill; worker count follows decomposition and budget (D18.5) |
| L-OP-9 | Passive monitoring through sidecar-written files | Superseded | Event intake and cursors (I/O contract §4, §9) |
| L-OP-10 | Guidance flow: draft → Mimir; on `APPROVE_UNCHANGED` **do not publish** (the worker is on track); `FLAG` → operator; `REJECT` → revise | Superseded in part; needs decision | D8.1 reviews only guidance that materially changes a worker's approach. The live `publish_guidance` requires "an approved `guidance` verdict or `APPROVE_UNCHANGED` semantics"; under D8.4 `APPROVE_UNCHANGED` means the draft is approved as is, while the legacy flow meant "publish nothing". Issue X-7 |
| L-OP-11 | End-of-turn scan of verdict marker files | Superseded | Verdicts arrive as events (`review.verdict`, interrupt; I/O contract §4) |
| L-OP-12 | Surface every Eir webhook failure (a failed pipeline means the merge gate silently disappeared); distinguish structural from transient; escalate repeats | Carried in part; needs decision | I/O contract §4 logs Eir webhook failures as `host` and wakes only for credential expiry or limits, so a failure is log-only. Whether it must wake or notify is issue X-8 |
| L-OP-13 | Cross-project knowledge transfer as a core function: cite the source, review, publish, log | Carried in part; persona input | Cross-project lessons in every briefing (I/O contract §2); `recall` over lessons (§6); guidance review per D8.1 |
| L-OP-14 | Telegram interaction: concise, phone-friendly, lead with the answer; commands never executed as Docker operations | Carried; persona input (style) | D20, I/O contract §10 operator; stop and cancel through the service |
| L-OP-15 | Outgoing alerts: stuck 3+ iterations on one task, test regression, rate limit exhausted, circuit breaker tripped, all PRD items done | Carried in part; persona input | Worker transitions and alerts wake the planner (I/O contract §4); "stuck for 3+ iterations" detection is a candidate code check |
| L-OP-16 | Plateau handling: `converged` → assess done, stuck, degenerating (with `monotonic_shrink_streak`) or non-recoverable; `commit-plateau` → corrective guidance; `completion-likely` → ask for the completion promise and **never** issue corrective guidance | Carried (event routing); persona input (ladder) | Plateau events wake (I/O contract §4, Appendix C); non-recoverable runs are cancelled with `cancel_run`, not `commands/` |
| L-OP-17 | Spec-dev mode: `/spec-dev start|compile|abort|status|confirm`, state file, dev-log format, `[spec-dev]:`/`[fleet]:` prefixes, disambiguation rule, pivot flow, verbatim copy strings, confirm stops at the wiki | Carried (command parsing); backlog (behaviour) | The service parses `/spec-dev …` (I/O contract §10). The legacy state file, dev-log format and grammar are Saga code contracts (`odin/scripts/spec_dev/`); re-specify them as Odin schemas or drop them by decision before carrying the behaviour |
| L-OP-18 | Communication style: guidance as suggestions with rationale and citations; track guidance effectiveness | Persona input | Guidance-effectiveness table is Bragi's (D12, Saga) |
| L-OP-19 | Does not write code, approve PRs, decide architecture unilaterally, control containers directly, or access the internet beyond allowances; "never bypass Mimir" | Carried; "always Mimir" superseded | Planner profile (no Bash, Edit or Write; WebFetch allowlist; I/O contract §7); execution through Saga (D1.3); selective review (D8.1) |
| L-OP-20 | `project-registry.yml` | Superseded | Project records (I/O contract §2) |
| L-OP-21 | Immutable safety boundaries: cannot modify its own instructions; cannot bypass the launcher; cannot disable human approval of decomposition or principle changes; no Docker socket; cannot remove Mimir; cannot ignore operator commands; at most 25 principles; each principle cites ≥2 independent data points | Carried; one superseded in form | Instructions loaded read-only, principles changed only through the gated flow (I/O contract §5, §7); `propose_principle` enforces 25 and ≥2 evidence ids (§6); operator approval before execution (D18.5, acceptance §1); Docker socket (D2, Saga). "Cannot remove Mimir" becomes: Mimir is switchable (D19.3) but a disabled reviewer never satisfies required review (AC-22) |

## Mimir's legacy persona — [`odin/mimir/CLAUDE.md`](../history/saga-extraction/2026-10-14-14fdab3/odin/mimir/CLAUDE.md)

| ID | Legacy requirement | Disposition | Odin location / next step |
|---|---|---|---|
| L-MP-1 | Restraint by default; `APPROVE_UNCHANGED` preferred when no concrete improvement exists; no invented flaws | Carried | D8.4 |
| L-MP-2 | Four verdicts in Markdown files | Superseded | Five verdicts including `INSUFFICIENT_EVIDENCE`, validated JSON with findings (D8.4; I/O contract §10) |
| L-MP-3 | Stateless between reviews; reads earlier verdicts from `processed/` | Superseded | No perpetual memory; prior verdicts for the artifact lineage attached deterministically (D8.3) |
| L-MP-4 | Look for gaps, overconfidence, hidden coupling, unmeasurable criteria, over- and under-decomposition, principle inflation, guidance contradicting an accepted principle | Persona input | D8.2 names semantic coupling, sufficiency of success criteria and guidance against intent as Mimir's work |
| L-MP-5 | Do not replan, extend scope, approve with caveats (that is `FLAG`), or second-guess operator-approved decisions | Persona input | — |
| L-MP-6 | Consult cross-project lessons; cite them when flagging or rejecting | Needs decision | D8.3's evidence pack does not list lessons. Decide whether lessons are a deterministic attachment or Mimir gets read-only `recall` |
| L-MP-7 | Gated checklists: decomposition (coverage, gaps, coupling, measurability, acyclic dependencies, rationale), PRD (contracts verbatim and complete, git workflow, secrets declared, dependencies explicit, success criteria, stream awareness, self-modification forces `FLAG`), patch review (safety-critical, reversible, test plan, persona recursion = instant `REJECT`, launcher changes pre-authorized, scope focused, motivation cited); an unticked box forbids approval | Carried in part; backlog | Mechanical boxes become code checks given to Mimir as evidence (D8.2); the remaining boxes become review-type definitions in the integration package. Which review types need a verdict per run (D2.1 "where review is required") is to be defined with the review schemas in I0 |
| L-MP-8 | Guidance review, principle proposal (≥2 data points; weakening a safety boundary is instant `REJECT`) and stuck-instance assessment criteria | Persona input | `propose_principle` (I/O contract §6) |
| L-MP-9 | Mimir never talks to Telegram; concerns reach the operator through Odin | Carried | Reviewer profile (I/O contract §7) |
| L-MP-10 | Mimir cannot approve bypassing the launcher, removing human approval of decomposition, weakening Odin's boundaries or under-evidenced principles; cannot write review requests or edit its persona | Persona input; carried in part | Reviewer profile is read-only with review tools only (I/O contract §7) |
| L-MP-11 | Read workers' workspaces as evidence in PRD and decomposition reviews (prior runs; existing branches drifted from contracts) | Carried | Evidence packs with exact artifacts and `read_evidence` (I/O contract §7, §10) |

## Journal and topic formats

| ID | Source | Legacy requirement | Disposition | Odin location / next step |
|---|---|---|---|---|
| L-JF-1 | [`journal/JOURNAL-FORMAT.md`](../history/saga-extraction/2026-10-14-14fdab3/journal/JOURNAL-FORMAT.md) | Per-project worker journal entry format | Saga-owned | Worker contract (D3.3); Odin reads entries as run evidence (B-06) |
| L-JF-2 | same | Master-journal sections and the four-part entry format with its worked example | Carried (shape); superseded (file) | I/O contract §5; entries imported once (§14) |
| L-TS-1 | [`mqtt/TOPIC-SCHEMA.md`](../history/saga-extraction/2026-10-14-14fdab3/mqtt/TOPIC-SCHEMA.md) | Worker topics, status and metrics payloads, plateau signal definitions | Saga-owned | Odin consumes them as run events (I/O contract Appendix C) |
| L-TS-2 | same | `saga/events/<kind>` lifecycle envelope (`decomposition_approved`, `prd_launched`) | Carried (capability); Saga-owned (envelope) | `emit_event` (I/O contract §6, B-14) |
| L-TS-3 | same | `dvergr/odin/*` topics, including commands | Superseded | Odin is reached through its service; `commands/` deleted (D13.5) |
| L-TS-4 | same | Filesystem marker contracts (verdict markers) | Superseded | Deleted at migration (I/O contract §14 step 4) |

## Saga developer instructions — [`CLAUDE.md`](../history/saga-extraction/2026-10-14-14fdab3/CLAUDE.md)

| ID | Legacy requirement | Disposition | Odin location |
|---|---|---|---|
| L-DI-1 | Terminology, functional naming and banned synonyms | Carried | [`AGENTS.md`](../../AGENTS.md); D13 |
| L-DI-2 | Auth boundaries: development credentials, managed agents' credentials and Odin's harness credentials never cross-wired; one refresher per credentials lineage | Carried | `AGENTS.md`; D24 |
| L-DI-3 | Permitted and prohibited auth shapes; April billing findings under re-test, not relied on | Carried | `AGENTS.md`; roadmap gate G-5 |
| L-DI-4 | Blast-radius guardrails for the Docker host and Saga's infrastructure | Saga-owned; carried as a rule | `AGENTS.md` (never touch Saga infrastructure from this repository) |
| L-DI-5 | Odin dependency choices: Agent SDK (`claude-agent-sdk`, Python, bundles its own Claude Code binary), braid as an optional child process, UniiChat ideas, standalone tools separate; rejected: custom Messages API loop as default, tmux session as runtime, agent teams, standalone heimdall as authority, third-party harnesses on the subscription, credentials baked into images | Carried | `AGENTS.md`; D7, D10, D19 |
| L-DI-6 | Every machine-read file is validated JSON or YAML with a schema; Markdown for prose; every behavioural rule paired with its check or a ticket | Carried | `AGENTS.md` |
| L-DI-7 | Homelab addresses and deployment hosts | Saga-owned | Not imported; see the snapshot for deployment context |
