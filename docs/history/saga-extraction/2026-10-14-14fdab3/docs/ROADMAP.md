# Roadmap

Single view of what is next. The phases and exit criteria are decided
in [`DECISIONS.md`](DECISIONS.md) D15; this file tracks progress against
them. For history see [`../CHANGELOG.md`](../CHANGELOG.md); for Eir's
task queue see [`agents/EIR-BACKLOG.md`](agents/EIR-BACKLOG.md).

## Phase A — reset (in progress, 2026-10-14)

- [x] Harness landscape assessment and research notes
- [x] Odin I/O contract (v7, the implementation specification), with
      the blueprint, ecosystem plan, acceptance scenarios and
      repository extraction plan beside it
- [x] Decision record
- [x] Documentation consolidated (README, CLAUDE.md, index, banners)
- [ ] Claim the Max plan's included API credits (claude.ai Settings,
      Billing, "API credits"); confirm a "Promotional credits" line in
      the Console
- [ ] Billing and auth re-test on the current CLI, recorded in
      `CLAUDE.md` with versions: `claude -p` with the mounted
      credentials; `setup-token` with a complete 108-character token;
      the Agent SDK with a linked-org API key; the Agent SDK with a
      subscription login; two concurrent workers on separate lineages
      and on one copied file (expect the copy to break); refresh across
      a restart; behaviour at quota exhaustion (queue or pause, no
      silent fallback to paid usage)
- [ ] Operator answers to `DECISIONS.md` §5 (Saga active again; default
      models per session class; memory baseline and retention defaults;
      muninn; licenses; credits and seats; the first delegation; Herdr's
      capabilities; desktop authority; dotprivate's contract; skald
      retrieval; billing modes)
- [ ] Documentation handoff to the `odin` repository per
      `design/ODIN-REPOSITORY-EXTRACTION.md`, gated on: the contract
      held for one review cycle; `saga/docs/contracts/SAGA-SERVICE.md`
      extracted at the producer; the decision provenance map written.
      Code extraction stays in Phase C; the first live Odin deployment
      still depends on Phase B (D14)

## Phase B — Saga service v1

- [ ] Run ledger (SQLite) and the D5 state machine
- [ ] Local API with a client library: submit, status, evidence,
      guidance, cancel, event cursor, review and task requests
- [ ] Facade over the existing launcher and MQTT
- [ ] Launcher fixes: `depends_on` on `verified`, queued signal,
      unique result files, `approved` renamed `accepted`
- [ ] Delete `commands/` and `outgoing-commands/` and their references
- [ ] Renames: `worker-hooks/`, `containers/worker-claude/`,
      `saga/runs/{project}/{run}/…` topics
- [ ] Delegation records (D17) in the ledger and API
- [ ] Run evidence store (full journal entries, test output, commits,
      structured `needs_input` requests) behind the API
- [ ] Per-worker credential provisioning in the launcher (one lineage
      per worker, one refresher per lineage; `setup-token` once the
      re-test confirms it; Codex `auth.json` per worker) replacing the
      shared writable volume (D24)
- [ ] Minimum enforcement: approval and verdict binding by hash at
      submission, reviewer-identity verification, cancellation,
      concurrency cap, the four stop operations and `/stop all`
- [ ] Minimum verification policy (`verified` = success criteria matched
      to evidence and the stream branch pushed) and the worker
      `needs_input` request protocol in the Claude Code worker image
      (contract §10, §13)
- Exit: a run can be submitted, watched by cursor, guided, stopped and
  cancelled from a CLI; the CLI is refused for the same reasons Odin
  would be; `/stop <delegation>` stops everything under it and reports

## Phase C — Odin harness v1 (new `odin` repo)

- [ ] The Odin service: commitment records, log, tree, briefing
      rendering and compactor; event queue, wake policy and budget
      caps; session records; scheduler; outbox
- [ ] Runtime adapter over the Agent SDK (start, resume, inject,
      interrupt, budget, transcript) with its capability matrix; the
      Claude Code integration package (instructions, tools, hooks,
      skills)
- [ ] Telegram adapter with hash-bound approvals; Saga client tools;
      import endpoint
- [ ] Mimir as isolated review sessions with evidence packs; file
      adapter for the transition
- [ ] Terminal workspace (Herdr) **inspection**: overview, per-project
      Odin conversation and worker terminals where attachable; one
      command path shared with Telegram; `/stop` as a direct service
      operation (D20). Adopt-into-supervision and take-control are
      Phase D.
- [ ] Migration import (master journal, retrospectives and their
      outcomes, lessons); shadow mode; cutover
- Exit: Odin runs one project end to end without tmux

## Phase D — richer policy in Saga, second project

- [ ] Container TTL, per-run and per-day budget, operator-presence gate
- [ ] Second project; adopt-into-supervision and take-control with
      pending-effect holds; ownership rules exercised (D20)
- [ ] Action-authority boundaries for any new connector (none planned)
- [ ] Evidence rules for `verified` per project type; false completion
      reports measured
- Exit: the CLI and Odin encounter identical policy

## Phase E — workers by contract

- [ ] Worker contract document
- [ ] Codex CLI worker image (`auth.json` volume, Stop hook or JSONL
      tailer)
- [ ] Pi image for API-key or local models (pinned, telemetry off)
- [ ] The second Odin runtime adapter (Codex app-server or Pi RPC) with
      its capability matrix; a Codex worker image does not test Odin's
      harness portability (D15, D19)
- [ ] Memory comparison against the baseline (D7, D18)
- Exit: a Codex run completes under the same hooks and ledger; Odin
  runs one assignment through the second adapter with its missing
  capabilities stated

## Phase F — integrations

- [ ] `recall` on braid
- [ ] `decide` turn tool; `propose_decider` with the evaluator registry,
      replay and shadow mode before activation
- [ ] skald archiver adapter, then the `archive` recall scope when
      skald's retrieval exists
- [ ] Selected project package export through dotprivate (D22)
- [ ] Local session backend with its capability matrix (D23)
- [ ] Bragi on the chat log and ledger; lessons through the import
      endpoint
- [ ] Observability wiring (Telegraf, InfluxDB, Grafana)
- [ ] By operator decision: a computer-use worker type with the desktop
      seat lease and app-scoped authority, and the first desktop
      classification experiment (D21)

## Phase G — evaluation and demonstration (D18)

- [ ] Odin plus Saga against Hermes plus Saga (API key, sandboxed) on a
      small set of delegations: verified outcomes per operator hour,
      false completion reports, recovery after failure, missed
      commitments, unauthorized or duplicate effects, total cost
- [ ] Memory hypothesis (D7) and Mimir policy (D8) judged on the same
      runs
- [ ] First demonstration: three specifications into coordinated work,
      through the five scenarios in D18 (requirement change mid-flight,
      vanished worker with an artifact, operator takeover, integration
      failure after individual completion, preservation unavailable)
- Exit: results published in the repo

## Carried over from April

| Item | Status |
|---|---|
| saga-spec-dev run #2 | State unknown since May; re-check on the VM before Phase B |
| OBSERVABILITY-1, TELEGRAF-WIRING | Phase F |
| ANTI-PATTERN-1 (verdict polling), ANTI-PATTERN-2 (webhook retry) | Phase B (outbox and queue) |
| Secrets management Tier 1 | Phase B |
| Spec development Tier 2 | After Phase C (the dev-log becomes a chat log slice) |
| Voice over Telegram | Unscheduled |
| SAGA-SELF-1 (Eir as per-task containers) | Phase B (Eir as a Saga task) |
