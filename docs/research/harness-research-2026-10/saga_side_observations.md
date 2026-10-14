# Saga-side observations (from reading the repo, 2026-10-13)

Written by the coordinator before the external research returned, so the
final comparison is anchored on what Saga actually is today.

## Repo state

- 106 commits, 2026-04-12 → 2026-05-06. Last substantive code: 2026-05-02
  (F12 Eir webhook fix, SAGA-SELF-1 backlog entry). Last commits are docs.
  ~5 months without commits as of today. Phase 3 run #2 was "in flight"
  per ROADMAP.md when activity stopped. Unknown whether the fleet is
  currently running on the VM (this session is on the operator's desktop,
  not the VM).
- GENERALIZATION.md (2026-04-19) already analyses "Saga as a pattern":
  seven durable patterns, five generalization moves, explicit timing
  rule ("finish roadmap first; need two trigger conditions"), and an
  explicit rejection of "swap Claude Code for the Agent SDK" pending
  subscription-compatible SDK auth.
- INSIGHTS-2026-04-15 §2: public-release stance is "reference
  implementation, idiosyncratic by design; don't make the stack swappable".
- CLAUDE.md "Explored and Rejected" table bans re-exploring OpenClaw,
  frankbria, Praktor, Phantom, API-key auth, OAUTH_TOKEN env var.

## What Odin physically is today

- One tmux window running
  `claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official`
  with cwd `/workspace/odin`, which loads a 1,021-line / 50 KB CLAUDE.md.
- Effort set post-launch via `tmux send-keys "/effort xhigh"` with
  verify+retry (`scripts/lib/claude-ready.sh`). Model = Claude Code default.
- Onboarding dialogs bypassed with a baked `.claude.json` baseline
  (regenerated per Claude Code version), extended at start with `jq`.
- Inputs reach Odin by four different mechanisms:
  1. Telegram channel events (first-party plugin; arrive as user turns).
  2. `tmux send-keys` nudges from ratatoskr (Mimir verdicts, milestones,
     alerts) — silently dropped when Odin is mid-tool (F11).
  3. Marker files Odin is told to scan "at the end of every tool-call
     sequence and whenever you reach an idle prompt"
     (`incoming-verdicts/*.json`, `/workspace/eir/failures/pr-*.md`).
  4. Passive files: `scripts/state.json`, `incoming-journals/`,
     `incoming-alerts/`, project wikis, `lessons/`.
- Outputs are all files that a sidecar or daemon acts on:
  `outgoing-guidance/`, `outgoing-events/`, `outgoing-alerts/`,
  `mimir/pending/`, `launch-requests-draft/` → `launch-requests/`,
  `commands/`, `master-journal.md`, `odin/projects/<p>/wiki/…`.
- Memory: `master-journal.md` read in full on every startup/context reset;
  `project-registry.yml`; Bragi-maintained `lessons/`; per-project wiki.
  Persona admits old journal entries "contain claims those documents
  contradict" (memory hygiene problem).
- Sidecar `ratatoskr.py` (36 KB): MQTT subscriber → state.json +
  incoming files; inotify watchers → publish guidance/events, nudge Mimir
  and Odin; milestone dedup; journal metrics; spec-dev sweep loop.
- Deterministic Python already growing around the LLM:
  `odin/scripts/spec_dev/` (parser, state machine, dev-log, compile,
  archive, schemas, tests). The persona says "Command parsing is not your
  job" — the harness-vs-prompt split has already started organically.

## Harness-shaped pain points (things caused by driving a TUI as a daemon)

1. F11: send-keys dropped mid-tool → marker files + prompt-level polling
   instruction. Compliance-dependent.
2. SAGA-SELF-1: persona rituals (PERSONA-3) don't reliably fire in a
   long-lived session → proposal to make every Eir task an ephemeral
   container. Repo's own principle: "mechanical enforcement compounds;
   cultural enforcement decays" (PHASE-3-IMPROVEMENTS).
3. 50 KB persona carries byte-identical contract strings (spec-dev §2,
   §7, §8, §9) that Mimir checks verbatim — prose doing a state machine's
   job.
4. Odin is reactive; proactive updates = send-keys nudges (Tier 1).
   Tier 2 (MCP tools for fleet state) and Tier 3 (digests) not built.
5. No direct tool access to fleet state; Odin reads state.json by hand.
6. Effort/model/plugin install all via slash commands typed into the TUI.
7. `.claude.json` baseline must be regenerated per Claude Code version.
8. Eir webhook polls `mimir/verdicts/` (anti-pattern 1 in ARCHITECTURE).
9. Persona edits require redeploy/restart (PERSONA-REFRESH-AUTO deferred).
10. Credentials auto-refresh fragile → keepalive cron is load-bearing.
11. Odin cannot read MQTT itself; cannot be nudged reliably; cannot
    schedule its own wakeups (no timer primitive) — all three are
    exactly what a harness provides.

## What is Claude-Code-specific vs already harness-agnostic

Harness-agnostic today (would survive a harness swap unchanged):
- MQTT topic schema and `status.json` contract (TOPIC-SCHEMA.md).
- Journal format, PRD/wiki/contracts structure, launch-request YAML.
- Mimir request/verdict file protocol; verdict marker contract.
- Heimdall (validate YAML → docker run), except: it unconditionally
  mounts `saga-claude-credentials` at `/home/vscode/.claude`, rejects
  `CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY` env, and allowlists
  `saga-dvergr:latest`-style images only.
- Bragi vault, Gitea branch-per-stream workflow, lessons store.
- Telegram as the operator surface (conceptually; the transport is the
  Claude Code channel plugin, which is CC-specific).

Claude-Code-specific:
- `/ralph-loop` plugin as the worker loop; hooks via
  `/workspace/.claude/settings.json` (SessionStart + Stop).
- `.claude.json` baseline; credentials volume; `claude` CLI flags;
  effort/model slash commands; Telegram channel plugin; tmux send-keys
  driving; CLAUDE.md persona loading; Trail of Bits base image.

## The dvergr "worker contract" (already implicit, could be made explicit)

A worker, on any harness, must: (1) read PRD.md and its persona file;
(2) iterate until a completion promise or an iteration cap;
(3) after each iteration write `.dvergr/status.json` + append
`.dvergr/journal.md` and run `post-iteration.sh` (publishes to MQTT,
runs plateau checks); (4) read `.dvergr/latest-guidance.md` at iteration
start; (5) commit/push `stream-<instance>` on Gitea. A harness needs
either a post-turn hook or an external per-iteration driver, plus
unattended startup and subscription-or-cheap auth in a container.
Harnesses without hooks can be driven by an outer loop
(`<cli> exec/run` per iteration) — the frankbria pattern, which is only
"rejected" for Anthropic because of billing, not on its merits.

## Three readings of "Odin as a custom harness"

A. **Odin as a Claude Code plugin** (harness-on-harness, like OMO on
   OpenCode): skills (spec-dev, decomposition, retrospective ritual),
   hooks (UserPromptSubmit → mechanical slash-command parsing; Stop →
   mechanical marker scan; SessionStart → journal load; PreCompact →
   persist), an MCP server replacing ratatoskr's file inboxes with tools
   (`fleet_status`, `pending_verdicts`, `publish_guidance`,
   `request_mimir_review`, `stage_launch_request`), and — if Channels
   permits custom channels — an MQTT channel so fleet events arrive as
   turns instead of send-keys. Separate repo, versioned independently,
   installed into the saga-odin image. Keeps subscription billing.
B. **Odin on a standalone harness** (Agent SDK, Hermes, Pi, …): full
   control of the loop/event injection/tools/memory; but per-token
   billing for Claude, or a non-Claude model, or policy risk if a
   third-party harness is pointed at a Claude subscription.
C. **Odin as a protocol**: define the orchestrator's I/O contract
   (files + MQTT + launch-requests + Mimir handoff + operator surface)
   so the brain is swappable. This is GENERALIZATION.md Move 2 scoped
   to one role, and it is a prerequisite for both A and B anyway.

Open facts needed from research before recommending: Oct-2026 status of
subscription billing for `claude -p`/Agent SDK/OAuth token; whether
Claude Code Channels supports custom channel plugins; Agent Teams and
Workflows semantics and billing; which third-party harnesses allow
subscription auth headless; cost of running an Opus-class planner on
API; which harnesses have post-turn hooks + loop modes for workers.
