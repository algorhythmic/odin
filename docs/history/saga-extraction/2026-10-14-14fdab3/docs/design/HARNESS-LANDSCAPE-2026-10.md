# Harness landscape versus Saga, and whether to extract Odin (2026-10-13)

> **Status:** Draft for operator decision. Inputs: a full read of this
> repo; four landscape surveys (Claude Code platform as of v2.1.299,
> third-party harnesses, multi-agent orchestrators and Ralph-loop
> derivatives, the custom-harness movement and interop protocols);
> seven source-level deep dives (openhuman, exo, oh-my-pi, hermes-agent,
> earendil-works/pi, talorys, ClickHouse/nerve); reviews of the
> operator's five standalone repos (heimdall, braid, skald, muninn,
> wayland-computer-use), which share names with Saga components but
> replace none of them; and direct verification of the three Anthropic
> billing pages cited in §1. The research notes with inline citations
> are in [`harness-research-2026-10/`](harness-research-2026-10/README.md).
>
> **Names.** "Saga's Heimdall" below means `odin/scripts/heimdall.py`,
> the container gatekeeper; `algorhythmic/heimdall` is a desktop
> task-and-continuity daemon that rules agent execution out of scope.
> "Bragi" means Saga's model-driven compiler; `algorhythmic/skald` is a
> transcript archiver that never calls a model.
>
> **The question:** should Odin be pulled out of Saga and developed as a
> custom harness in parallel, which patterns from the current harness
> landscape are worth adopting, and what in Saga should change so it can
> host other harnesses.

## 0. Answer in brief

1. **Yes, extract Odin, but as two layers, not one.** Define Odin's I/O
   contract first (what it reads, what it writes, where its memory
   lives). Then build a thin, boring harness around the model: a durable
   event queue, tools instead of file inboxes, an outbox, a scheduler, a
   Telegram adapter, bounded memory. Keep judgment in prompts and skills.
   The field's one clear lesson is that the orchestrators that survived
   extraction got *dumber* mechanically (OpenAI's Symphony, Gas City),
   and the one that kept a smart interactive agent in tmux (Gas Town)
   burned down. Odin-in-tmux is that shape.
2. **The billing wall that forced "interactive sessions only" has moved.**
   Anthropic now states that `claude -p` and the Agent SDK draw on
   subscription limits, and Max plans include $100 or $200 a month of API
   credits that cover the Agent SDK. The April 10 tests recorded in
   `CLAUDE.md` coincide with a known bug window and a known token-copy
   bug. Re-test before designing around either constraint.
3. **Two runtimes are viable for the extracted Odin, and they can share
   one contract.** Runtime B keeps Odin an interactive Claude Code
   session but replaces every send-keys and marker-file hack with
   first-party primitives that shipped since April (inbox socket, mods,
   hooks, MCP, skills). Runtime A runs Odin on the Claude Agent SDK
   funded by the included API credits. Build B first because it is
   inside Anthropic's explicitly permitted zone and reuses what exists;
   build A against the same contract as the parallel experiment the
   operator is asking about.
4. **Saga can host other harnesses for workers with modest changes,
   because the harnesses converged on Claude Code's shape.** Every major
   CLI now has headless JSONL output, Stop-style shell hooks (exit 2 =
   block), AGENTS.md, Agent Skills, MCP, and ACP. The worker contract
   needs writing down, Heimdall needs per-image policy, and Codex CLI is
   the first non-Claude worker to add. Gemini is API-key only now.
5. **No third-party harness should run Odin or Claude workers.** Every
   one that offers a Claude subscription path is either billed as extra
   usage (Hermes), was removed under legal pressure (OpenCode), or
   impersonates the Claude Code client (Pi and its fork oh-my-pi; Pi's
   source literally labels it "Stealth mode: Mimic Claude Code"). All
   are useful as reference designs; none as a platform for the Claude
   side. Claude workers on any of them must use an API key.
6. **The operator's own September 2026 stack is adjacent, not a
   replacement.** Between 2026-09-05 and 09-11 the operator built a
   desktop-centric set of tools on Omarchy: standalone heimdall (task
   and continuity daemon with a SQLite event log, TUI, CLI, MCP,
   Hyprland and Claude Code hook adapters), braid (retrieval engine),
   skald (transcript archive), wayland-computer-use (desktop control
   MCP) and dotprivate; muninn (the Phase 3 bookmark pipeline) was
   redefined in April as the operator's single personal wiki and has
   been dormant since July. None mentions Saga except to defer it
   (braid's roadmap: "Heimdall is the active integration; Saga is
   deferred") or to exclude it (standalone heimdall rejects "Saga
   coupling" and MQTT). Where each plugs into the Odin plan is in
   `ODIN-IO-CONTRACT.md` §5, §6 and §8: braid as an optional `recall`
   tool, skald as an optional archiver of the chat log, muninn as a
   possible `recall` scope or Bragi output, wayland-computer-use kept
   out of Odin's reach, standalone heimdall as a design reference only.

## 1. The premise has changed: billing and policy

Verified directly against the live pages on 2026-10-13.

| Source | What it says |
|---|---|
| Help Center 15036540, update dated 2026-10-07 | "Claude Max and Team plans now include monthly API credits, which cover the Claude Agent SDK, `claude -p`, the Claude API, and Claude Managed Agents." and "You can still use the Claude Agent SDK, `claude -p`, and third-party apps with your subscription limits." The 2026-06-15 update: those paths "still draw from your subscription limits." |
| platform.claude.com, "API credits for Max and Team plans" | Max 5x $100/month, Max 20x $200/month, claimed by linking one Console organization, spent via an API key. Covers the Claude API, Managed Agents, the Agent SDK, playground. Does not cover Claude Code or app extra usage. No rollover. "Credits don't change your usage limits in Claude or Claude Code." Requests stop when credits run out unless auto-reload. |
| code.claude.com "Legal and compliance" | OAuth is for "ordinary use of Claude Code and other native Anthropic applications." Third-party developers may not offer claude.ai login or route users through Pro/Max credentials. It explicitly does not "prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription, including where a platform hosts Claude Code" in "hosted sandboxes or other agent infrastructure." "Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK." |

What this does to the constraints in `CLAUDE.md` and `README.md`:

- **Constraint 1 ("`claude -p` bills to API credits")** is contradicted by
  the official page. The platform researcher found anthropics/claude-code
  issue #43333, opened 2026-04-04 on v2.1.91 ("`claude -p` with OAuth
  bills as API usage"), closed by its reporter as fixed on 2026-04-08.
  The Saga test on 2026-04-10 (roughly v2.1.100) fell inside that
  window. The headless docs now say only `--bare` skips subscription
  login, and warn that `--bare` "will become the default for `-p` in a
  future release," so any future `-p` automation must pass the non-bare
  form explicitly.
- **Constraint 2 ("`CLAUDE_CODE_OAUTH_TOKEN` forces API mode, see
  #16238")** cites the wrong issue. #16238 is a January 2026 feature
  request to warn when the env var overrides `.credentials.json`; it
  never mentions "Invalid bearer token." The matching 401 report is
  #65320 (June 2026), closed the same day when the reporter found the
  `setup-token` output had wrapped across two terminal lines and only
  the first 79 of 108 characters were copied. The authentication docs now
  describe `setup-token` as the documented subscription path for CI and
  containers, valid for one year, with no refresh-token dance. That
  makes it worth a controlled re-test for dvergar; it may be *more*
  robust than the shared credentials volume (see §6, refresh tokens).
- **Agent SDK billing** now has two funded paths: SDK via `/login`
  credentials (draws on plan limits, same pool Odin uses today) or SDK
  via an API key in the linked Console org (draws on the included
  credits, separate from plan limits). The "third party developers" note
  in the SDK docs is about products offered to other users.
- **Saga's current shape is explicitly permitted.** Unmodified binary,
  operator's own subscription, operator's own infrastructure.
- **The Explored-and-Rejected table needs a pass.** Praktor, Phantom and
  "swap Claude Code for the SDK" were rejected on the old rule.
- **Policy risk is real and asymmetric.** Anthropic changed course three
  times in 2026 (February terms, April 4 harness cutoff, a May 13 split
  announced for June 15 then paused June 16, October 7 credits) and
  says it "will share advance notice before any future change." Keep a
  billing fallback switchable without code changes. The interactive
  session design carries the least policy risk; the SDK design carries
  more; third-party harnesses on subscription OAuth carry the most and
  are already being blocked (Hermes users got "Third-party apps now draw
  from your extra usage" HTTP 400s on 2026-09-01).

Cost of a custom Odin on the API, from the researcher's computation at
October list prices (Opus 5.5 $4/$20 per MTok, cache read $0.20; Sonnet
5.5 $2/$10):

| Planner load per month | Opus 5.5, no cache | Opus 5.5, 80% cached | Sonnet 5.5, 80% cached |
|---|---|---|---|
| 5M in / 0.5M out | $30 | $16 | $8 |
| 20M in / 2M out | $120 | $63 | $32 |

Max 5x's $100 covers the high end on Opus with caching; Max 20x's $200
covers it uncached. On an API key the prompt cache defaults to five
minutes (one hour on a subscription), so a long-lived SDK session should
use the one-hour cache write (2x) for its static prefix.

## 2. Where Saga sits in the October 2026 landscape

### 2.1 Harnesses converged on one shape

By October 2026 Codex CLI, Gemini CLI, OpenCode, Pi, Hermes, Droid,
Cursor CLI, Qwen Code, Kimi Code, Mistral Vibe and Cline all ship:
headless `-p`/`exec` emitting JSONL with a terminal result event;
Claude-Code-style shell hooks with JSON on stdin and exit 2 = block
(`Stop`, `SessionEnd`, `PostToolUse` and friends); AGENTS.md; the Agent
Skills standard; MCP; subagents; session resume; an ACP server mode. The
differentiators left are whose subscription each can legally bill inside
a container, and a few distinctive mechanisms (OpenCode's server plus
SSE event bus, Pi's TypeScript extension events, Hermes's judge-driven
`/goal`, Codex's reviewer-agent approvals and AGENTS.md layering, Gemini
CLI's policy engine, Droid's autonomy tiers).

Consequence for Saga: the `dvergr-hooks` Stop-hook script ports to
Codex, Droid, Qwen, Gemini and Cursor with payload-field renames, and
every harness can be tailed as JSONL where hooks are undocumented under
headless mode.

### 2.2 What Claude Code itself now offers (v2.1.299, April baseline ~v2.1.100)

The platform grew a great deal between April and October. The items
that bear on Saga:

- **Four in-process ways to push an external event into a running
  session without keystrokes.** (1) The per-session **inbox Unix
  socket** (cross-session messaging, v2.1.224+): a script in the same
  container connects to `$CLAUDE_CODE_MESSAGING_SOCKET`, optionally
  sends an auth line, and posts text; when the session is idle Claude
  Code "starts a new turn with the message," otherwise it is read
  between tool calls. Works for `-p` workers too. Needs
  `crossSessionInbound: accept` in settings for unattended delivery. The
  model is told the text came from another session. (2) **Mods**
  (v2.1.287+, October): plugin JavaScript inside the Claude Code process
  that can `$.process.spawn` a long-lived subscriber, keep timers that
  run between turns, persist a `$.store`, and call
  `$.prompt.submit({text, asUser: true})`, which "waits until the session
  is idle and then starts a new turn." Unsandboxed and two weeks old.
  (3) **Channels**: any stdio MCP server declaring `claude/channel` can
  push `<channel>` events, but during the research preview a custom
  channel needs `--dangerously-load-development-channels`, which shows an
  interactive full-screen dialog and is ignored in `-p`/SDK mode; Pro/Max
  users cannot allowlist their own plugin. The Telegram plugin stays on
  the allowlist. (4) **Monitor tool and plugin monitors**: interactive
  only, bounded watch windows, private addresses denied for WebSocket.
  None of these cross a container boundary; MQTT stays the transport
  between containers.
- **33 hook events** (up from about nine), five handler types including
  `http` and `mcp_tool`, `asyncRewake` hooks that wake an idle session on
  exit 2, `SessionStart` `watchPaths` plus `FileChanged`, `PreCompact`
  that can block, `UserPromptSubmit` now before skill expansion. The
  `Stop` hook has a loop guard: after eight consecutive blocks with no
  tool use, Claude Code ends the turn (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`
  raises it). That is a first-party cap on exactly the re-verification
  pathology Phase 3 run #1 hit.
- **`/goal`** (v2.1.139): a session-scoped prompt-evaluated Stop hook
  that "keeps working toward a condition," restored on resume, and it
  runs to completion under `claude -p`. Together with the official
  plugin's documented fragility (exact-match promise, three open
  detection bugs, unlimited default iterations) this is the natural
  successor to `/ralph-loop`.
- **Agent view** (`claude --bg`, a local supervisor daemon, worktree
  isolation, subscription-billed), **agent teams** (same machine only,
  file mailboxes, no `-p`), **dynamic workflows** (JS scripts spawning up
  to 1,000 subagents, usage-limit pause), **Projects** (cloud
  coordinator plus threads, Pro/Max beta, needs github.com), **Routines**
  (subscription-billed cloud sessions on a schedule or API trigger, fresh
  clone, no local files), **self-hosted environments** (Team/Enterprise
  only), **Remote Control**. The docs are explicit that "in every
  approach the workers are Claude sessions." Agent teams map onto
  Odin + dvergar only if everything shares one container, which breaks
  the Heimdall boundary. Routines cannot replace Bragi because they
  cannot see `/opt/saga`. Agent view is the closest first-party analogue
  to Saga on one host and gives up Docker isolation.
- **Memory**: auto memory (first 200 lines or 25 KB injected), subagent
  `MEMORY.md`, idle compaction, one-hour prompt cache on subscription.
  Odin's master journal exceeds the injection cap, so file-based memory
  with on-demand loading remains correct.
- **Anthropic's own harness guidance** (Nov 2025 to June 2026):
  separate the agent doing the work from the agent judging it; JSON
  feature lists because models mutate JSON less than Markdown; progress
  file plus git as recoverable state; "every component in a harness
  encodes an assumption about what the model can't do on its own"; and
  since June, let the model write deterministic orchestration scripts
  with adversarial verification. Saga's Odin/Mimir split is the
  recommended generator/evaluator shape; what Saga lacks is adversarial
  verification of worker claims before the planner trusts them.

### 2.3 What the orchestrator field learned in 2026

- **Gas Town is dead by its author's account** (August 2026): it "fell
  apart at the seams with Opus 4.7," "ended up only building itself,"
  and "never reliably ran all night." Its successor Wheelhouse keeps the
  topology (design crew, implementation fleet, review by a different
  model family, mail, merge queue, tmux) under the rule "crons watch,
  models act," and runs on twelve $200 Max accounts plus Codex workers
  as the fallback when quotas exhaust. Dan Luu's reading: these
  orchestrators fail on reliability, not design.
- **Symphony** (OpenAI, April 2026) is the clearest "brain extracted"
  design: a deliberately dumb 30-second tracker poller with bounded
  concurrency, a five-minute stall timeout, exponential backoff, a
  20-turn cap, one workspace per issue, and a `WORKFLOW.md` prompt per
  issue. Judgment lives in the worker. Gas City is the same idea as a
  declarative `city.toml` reconcile loop. **The two systems that
  separated brain from substrate did it by making the orchestrator less
  intelligent.**
- **Ralph loops** were absorbed into first-party tooling (`/loop`,
  `/goal`, Qwen's `/loop`, Hermes's `/goal`), and every serious
  derivative added a second signal beyond the promise string: frankbria's
  circuit breaker, ralph-orchestrator's gates, snarktank's `prd.json`
  `passes` flags plus `progress.txt`. Saga's plateau hooks are in this
  family; relying on the plugin's promise tag alone is below the bar.
- **Task state** is JSON or a database everywhere that tried Markdown
  (Anthropic's rationale; Beads moved SQLite+JSONL to Dolt; agent-team
  mailboxes are validated JSON with file locks). Free-text verdict
  Markdown plus marker files is idiosyncratic to Saga.
- **Cross-model review** is now common but post hoc on diffs
  (no_human, codex-plugin-cc's review gate, Wheelhouse's Fable review).
  Pointing the auditor at the *planner's decisions* is Saga's distinctive
  move. Reviewers elsewhere are triggered by lifecycle events; Odin can
  still skip Mimir by choice.
- **Contract drift** is handled mechanically where it is handled at all:
  OpenAI's generated linters and structural tests, file-ownership
  partitioning, gates that reject unverified work. No surveyed system
  carries verbatim interface contracts into worker prompts. Saga has the
  prompt half.
- **Heterogeneous worker pools are table stakes** in open source (Gas
  Town 11 presets, ralph-orchestrator 8, Paperclip ~10) and the stated
  hedge against single-vendor quota walls. First-party Claude surfaces
  are Claude-only.
- **Quota walls, not price walls**, are what subscription-funded
  orchestrators hit. Budgets that *pause work* (Paperclip, Devin's ACU
  limits) are the control Saga lacks; iteration caps bound tokens only
  indirectly.

Saga's seven patterns against that backdrop: planner + auditor + pool
under one decider, Telegram operator, and the worker loop are
mainstream. The deterministic gatekeeper (Heimdall), auditing planner
decisions, and approval-gated principles are unusual but principled
(precedents: bernstein's "no model in the coordination loop," Devin's
reviewed knowledge suggestions, Managed Agents' versioned memory).
Marker files, Markdown verdicts, and a standing healer session are
idiosyncratic.

## 3. Harness verdicts

"Odin" means: could the planner run on it under Saga's constraints.
"Dvergr" means: could a worker container run it with the worker contract
in §5. "Reference" means what to copy regardless.

| Harness | Odin runtime | Dvergr runtime | Reference value |
|---|---|---|---|
| **Claude Code, interactive + plugin** (Runtime B) | **Yes.** Subscription limits, permitted zone, Telegram channel, inbox socket, mods, hooks, MCP, skills. | Current; `claude -p "/goal …"` is a cleaner loop than tmux + send-keys + plugin install (verify onboarding in `-p`). | Hooks reference, cross-session messaging, mods API, `/goal` |
| **Claude Agent SDK** (Runtime A) | **Yes**, on plan limits or on the included API credits. Full control of the loop; policy risk moderate. | Yes for Claude workers. | Sessions, hooks, skills, plugins all load from `.claude/` |
| Codex CLI (OpenAI) | No (planner should stay Claude). | **Yes, first candidate.** Officially documented subscription auth for unattended containers (`codex login --device-auth`, seed `~/.codex/auth.json`, refresh in place); Pro has no five-hour cap; `Stop` hook carries `stop_hook_active`; `codex exec --json`. Hooks under `exec` undocumented; tail JSONL as fallback. | AGENTS.md root-to-cwd layering with 32 KiB cap; `approvals_reviewer = auto_review`; hash-trusted hooks; `--output-schema` |
| Gemini CLI / Antigravity CLI | No. | **API key only.** Consumer and free tiers stopped 2026-06-18; Antigravity CLI is closed, no ACP, `agy -p` reported to hang without a TTY. | Policy engine: `ask_user` becomes `deny` headless, global deny hides the tool |
| OpenCode (anomalyco) | No; Claude plan auth removed under legal requests (March 2026). | Yes with ChatGPT, Copilot, GitLab Duo or OpenCode Go ($10/mo). | Best external-orchestrator surface: `opencode serve`, OpenAPI, SSE `/event`, `--attach` |
| Oh My OpenAgent (OMO) | No (now runs on "senpi," its own Pi fork). | Non-Claude only. | IntentGate, Hashline edits, Todo enforcer, Kibitzer memory reviewed by a cheaper model |
| Pi (earendil-works/pi, 115k stars, v1.2) | No. Its Anthropic OAuth path impersonates Claude Code (`claude-cli/2.1.280` user agent, "You are Claude Code" system prefix, renamed tools) and is extra-usage billed anyway. | **Yes for API-key or local models, lowest friction.** 41 extension events load in all modes; `agent_before_settle` can `continue` so one `pi -p` process runs a whole Ralph loop; no first-run dialogs headless; official Docker recipe; the core loop has no turn or cost cap, so the extension must enforce it. Pin the version: minor releases are breaking by policy, and 1.2.0 broke `sendUserMessage` eleven days after 1.0. | Copy as design: `pi-ai` sectioned system messages, the ~950-line agent-core loop with steer/follow-up queues, session JSONL trees, the RPC protocol with an explicit `agent_settled` signal. Avoid `chord` (runtime replaced in 1.2.0) and `pi-durable` (experimental, unused by the coding agent). Earendil's `pi-chat` (Telegram/Discord bridge with a `chat_workers` tool) is the nearest existing analogue to Odin. |
| oh-my-pi (Stencil Labs, hard fork of Pi) | **No.** Its Claude plan path impersonates the Claude Code client (user agent, prompt prefix, "billing attestation"); ~2 releases/day; yolo default; telemetry hosts. | Non-Claude only; RPC worker + credential sidecar example (robomp). | Typed message delivery (`steer`, `followUp`, `nextTurn` with attribution); advisor note filter with severities, budget and cooldown; bounded stop-hook continuations; settled vs yielded |
| Hermes Agent (Nous, 253k stars) | **Technically the closest to Odin** (gateway, cron, skills, memory, Telegram with approvals, `inject_message`), but Claude is extra-usage only, 24k commits per release, CVE history, in-process plugin trust. | Possible for non-Claude; `/goal` cannot be started headless cleanly. | `/goal` with judge + deterministic quality gates + `blocked` verdict; approval staging pinned to exact text; bounded memory files; cron gating (inject only when idle, coalesce missed ticks); worker lifecycle contract; outbound signed webhooks |
| Exo (exoharness, Braintrust founders) | No; API keys only, wants to own sandbox creation. | Non-Claude only; heavy build. | Durable turn queue with `wake` vs `interrupt`, idempotency keys, one injection at a time; outbox states; scheduler fires recorded before wakeup; host events in the same log; "fail loudly when unattended" |
| Nerve (ClickHouse, OpenClaw successor on the Agent SDK) | Workable but 95k lines of pre-1.0 code and 49 schema migrations. | No loop, no user hooks. | Backend interface with normalized events and capability flags; review-loop controller (criteria IDs, mechanical pass gate, `gamed` flag, no-progress check, different model family as verifier); outbox in the same transaction; `session_usage` columns for Telegraf |
| openhuman (Tiny Humans, Rust, 42k stars, beta) | No; hosted memory service, vendor telemetry by default, GPL, `claude -p` route disables inner tools. | Plausible for non-Anthropic models; amd64 image; no session-start hook. | Queue lanes for injected messages; cheap triage (drop / acknowledge / react / escalate) before waking the planner; nudge-then-halt circuit breaker; typed handback states |
| Talorys | No (four-day-old Cloudflare personal-assistant app). | No. | Hash-bound approvals (SHA-256 of what was shown, 30-minute expiry, single claim); restricted tool set for unattended turns; supersede-not-overwrite memory with a review queue |
| Goose (AAIF) | No. | Via ACP providers for Codex/Claude CLIs; cannot resume or fork sessions. | "Use what you already pay for" ACP providers |
| Cline / Kilo / OpenHands / Droid / Cursor / Qwen / Kimi / Vibe | No. | Possible with API keys or vendor plans; Droid and Cursor have Stop hooks; Qwen has `http` hooks and `/loop`; Kimi has device-code login. | Droid autonomy tiers; Qwen `http` hook type |
| **Operator's own:** standalone heimdall (Go, Sep 2026, unreleased, CI red since 09-09) | No; it is a desktop task-and-continuity daemon that excludes agent execution, launchers, leases and limits by design. | No. | Intent, grant, report and independent-check records per action; `/session/hook` relay for Claude Code hooks; the template for any future `ask_operator`-gated desktop action |
| braid (Go, Sep 2026, v0.1.0, no license) | Not a runtime. | — | Byte-budgeted retrieval with a `why` per hit, BM25 plus optional local embeddings, graph and recency; stdio protocol for a child process; "no-answer" and "forbidden hit" labels as a shape for testing compaction quality |
| skald (Go, Sep 2026, v0.1.1, idle) | Not a runtime; stores Claude Code, Codex and Devin transcripts byte for byte in SQLite, never calls a model. | — | Verified checkpoints and explicit gaps in an archive; needs a provider adapter and a per-line conversation id to archive Odin's log |
| wayland-computer-use (Python MCP, Sep 2026, local checkout 10 commits ahead) | **No**, by design: it types and clicks with the operator's full desktop authority and would route around Saga's Heimdall. | No: needs a live Hyprland session and `/dev/uinput`. | Evidence-checked input (screenshot freshness, window re-check, pixel check, no retries), fail-closed tool-schema pinning; Anthropic's browser-level verification for web projects is headless Playwright in the worker container, not this |
| muninn (Python, Apr to Jul 2026, dormant) | No. | No. | The Karpathy wiki shape fully adopted (ADR-002); a bookmark pipeline with an MCP search endpoint; its synthesis container mounts the credentials volume and launches outside Heimdall, which the billing re-test and per-image policy must cover |
| Symphony (OpenAI) | Shape to copy, not code. | — | Dumb poller, stall timeout, backoff, per-issue `WORKFLOW.md` |
| Paperclip (101k stars) | No (company OS). | — | Budgets that pause work; single assignee with execution locks |
| Gas Town / Gas City | Dormant. | — | Beads as "why" record; "crons watch, models act" |
| Aider, Roo Code, Vibe Kanban | Dormant or archived in 2026. | — | — |

## 4. Patterns to adopt whether or not Odin is extracted

Ordered by leverage against problems Saga has already recorded.

1. **Durable, deduplicated event injection with wake vs interrupt
   semantics** (Exo, Hermes, oh-my-pi, openhuman). Replaces send-keys
   nudges (F11) and the "scan `incoming-verdicts/` at the end of every
   tool sequence" instruction. On Claude Code the primitive is the inbox
   socket or a mod's `$.prompt.submit`; on the SDK it is the harness's
   own queue. Each event carries an idempotency key, a source tag, and a
   delivery mode; only one injection is in flight per session.
2. **Tools instead of file inboxes.** An MCP server (ratatoskr's code)
   exposing `fleet_status`, `pending_verdicts`, `publish_guidance`,
   `request_mimir_review`, `stage_launch_request`, `notify_operator`.
   This is odin-proactive-updates Tier 2 and the end of "read
   state.json by hand."
3. **Validated JSON for every machine-read file.** Mimir verdicts with
   the checklist as fields; markers replaced by queue entries;
   `status.json` with a schema. Keep Markdown for journals and guidance
   prose. (Anthropic, agent teams, Beads, Nerve.)
4. **Mandatory audit triggers from lifecycle events.** A hook on PRD
   write or launch-request staging that blocks until a verdict exists,
   fail-closed (Hermes `pre_tool_call` policy; Codex reviewer approvals).
   Odin should not be able to skip Mimir by judgment.
5. **Mechanical contract gates in dvergar.** Project linters, a schema
   diff against `wiki/contracts/`, structural tests as pass/fail gates
   before a commit counts (OpenAI harness post, ralph-orchestrator,
   Anthropic's "unacceptable to remove or edit tests"). This is the
   missing half of the verbatim-contract rule.
6. **Replace the ralph-loop plugin's promise string with deterministic
   gates plus a judge.** `/goal` with a shell-command gate (Hermes's
   quality gates; Claude Code's prompt-based Stop hook), iteration cap,
   plateau hooks, and the first-party eight-block cap. Hermes's
   `blocked` verdict ("pause, don't fake done") maps onto Saga's stuck
   detection.
7. **Single credential refresher.** Claude Code and Codex refresh tokens
   are single-use; "whichever refreshes first invalidates the other's
   copy" (Hermes security docs; Nerve PR #444). Many containers
   refreshing from one shared volume is a plausible cause of the
   "auto-refresh silently failed within a day" finding. Either the
   keepalive is the only process allowed to refresh, or each container
   gets its own `setup-token` (one-year, no refresh), or a second login.
   Muninn's Opus synthesis container is another reader of the same
   volume and must be counted.
8. **Bounded memory with forced consolidation.** A capped `MEMORY.md`
   re-injected every session, over-limit writes erroring (Hermes,
   Nerve's 300-line cap); supersede-not-overwrite with a review queue
   for principles (Talorys); Karpathy's index/log/lint shape for Bragi
   (half-adopted in Saga's wiki template, fully adopted in muninn's
   ADR-002); principles re-read from a file at session
   start because compaction "can silently delete governance
   constraints" (2026 arXiv finding).
9. **Review-note discipline for Mimir** (oh-my-pi advisor): severities
   nit/concern/blocker, dedupe, a per-review note budget, a cooldown on
   interruptions. And the director rule: a finished worker turn is not
   proof its claims are correct; verify adversarially with a fresh
   context before Odin trusts a completion (Anthropic dynamic-workflows
   post, no_human).
10. **Untrusted input tagged by source** when dvergr journal text or
    Telegram text reaches Odin, and restricted tool sets for unattended
    turns (Talorys, Managed Agents' exfiltration restriction, Gemini's
    `ask_user` to `deny` headless as the Heimdall default).
11. **Budgets that pause work** at a configured limit, and a documented
    kill switch (Paperclip, Devin ACU limits). Saga's README already
    wants concurrency caps, TTLs and operator-presence gating in
    Heimdall; add a token or session-hour budget.
12. **Shrink the persona.** Short prompt at the "right altitude," skills
    loaded on demand, an AGENTS.md map rather than a manual (Anthropic
    context engineering, OpenAI's ~100-line AGENTS.md, Zechner). Move
    the spec-dev contract strings fully into `odin/scripts/spec_dev/`.
    Hierarchical AGENTS.md (Codex's nearest-wins, 32 KiB cap) is a
    testable contract for how guidance layers onto a dvergr workspace.
13. **Cache-stable prompt layout**: static persona and skills first, all
    per-turn context in one trailing block (Nerve, oh-my-pi), plus
    session rotation on a schedule with the retired session indexed into
    memory (Nerve) instead of one days-long session.
14. **Large tool output to a file with a preview in context** (Exo) and
    **host events written into the same event log** with a "back
    online" wakeup after restarts (Exo `SELF-CONTROL.md`).
15. **OpenTelemetry GenAI attributes** as the field list for MQTT to
    Telegraf to InfluxDB, with cached tokens separate so cost panels do
    not overcount (Nerve's `session_usage`; MCP 2026-07-28 carries OTel
    trace context in `_meta`).

## 5. What in Saga should change

### 5.1 Documentation and constraints

- Rewrite `CLAUDE.md` "Critical Constraints" after the re-test (§7 step
  0): record the actual `claude -p`, `setup-token` and SDK results with
  the CLI version, fix the #16238 citation, and note `--bare`'s coming
  default.
- Revisit the Explored-and-Rejected table (Praktor, Phantom, SDK).
- Update GENERALIZATION.md's rejection of "swap Claude Code for the
  SDK" to the new conditions.

### 5.2 Odin side

- Write the Odin contract (§7 step 1). Everything else depends on it.
- Replace send-keys and marker scans with injection (pattern 1), file
  inboxes with tools (pattern 2), Markdown verdicts with JSON (3),
  optional audits with hook-gated audits (4).
- Split the 50 KB persona into a short core plus skills; move contracts
  into code (12).
- Bounded memory and principles review queue (8); cache-stable prompt
  (13); scheduled digests and retrospectives from a scheduler rather
  than a nudge.

### 5.3 Worker side

- Write the worker contract explicitly: `PRD.md` in; `.dvergr/status.json`
  and `.dvergr/journal.md` after each iteration; `post-iteration.sh` run
  after each turn; `.dvergr/latest-guidance.md` read before each; commits
  pushed to `stream-<n>` on Gitea; iteration cap; completion signal.
  Any harness with a post-turn hook or an external per-iteration driver
  satisfies it.
- Replace the tmux + plugin-install + send-keys start with
  `claude -p "/goal …"` plus hooks, once `-p` billing is confirmed and
  onboarding under `-p` is verified. This removes the baseline
  `.claude.json` regeneration, the effort send-keys, and the plugin
  install.
- Add a Codex worker image (`~/.codex/auth.json` volume, `codex exec
  --json`, Stop hook or JSONL tailer). Then a Pi image for API-key or
  local-model workers: `pi -p --no-approve -e <loop-extension>
  --session-id stream-<n>`, `ANTHROPIC_API_KEY` only (never Pi's OAuth
  path), `PI_TELEMETRY=0` and the version check off, version pinned,
  `models.json` for Ollama or vLLM. The Pi deep dive includes a ~70-line
  extension sketch that satisfies the worker contract. A 30B-A3B MoE at
  Q4 fits the 32 GB box at roughly 10 to 17 tokens/s, adequate for
  auditor or summarizer roles, not a frontier planner.
- Saga's Heimdall, all of it new work in `heimdall.py` (the standalone
  heimdall refuses execution limits by design, so nothing here can be
  delegated to it): image allowlist per worker image; credential mount
  and env checks keyed by image rather than unconditional; `ask`-class
  actions denied, logged and escalated rather than silently allowed;
  the concurrency cap, TTL, operator-presence gate, kill switch and
  budget that the README promises but that do not exist yet; a result
  for requests held on `depends_on` instead of silence for up to 24 h;
  an optional `docker ps` sweep so the planner's launch ledger is not
  reconstructed from MQTT alone. Muninn's synthesis container currently
  starts with a direct `docker run` outside Heimdall; either route it
  through a launch request or accept that per-image policy does not
  cover it.
- Mechanical gates in dvergar (pattern 5).

### 5.4 Infrastructure

- Single refresher or per-container tokens (pattern 7).
- JSON everywhere machines read (3).
- The two known anti-patterns (verdict polling, no webhook retry)
  become an outbox and a queue (Exo, Nerve).
- Delete the dead `commands/` and `outgoing-commands/` channel. Nothing
  consumes it; `stop` and `restart` are launch requests with an
  `action` field.

### 5.5 Defects in Saga surfaced by this review

Candidates for the Eir backlog, found while reading Saga against the
standalone repos and the drafts:

1. `commands/` has no consumer, yet `odin/CLAUDE.md` (two places),
   `ratatoskr.py`, `mqtt/TOPIC-SCHEMA.md`, `ARCHITECTURE.md` and spec §4
   describe it as the way Odin stops containers. No `destroy` action
   exists anywhere.
2. `heimdall.py` `depends_on` treats a crashed prerequisite as
   satisfied, because containers run with `--rm` and the check is "not
   in `docker ps`"; the docstring says "exited cleanly".
3. A launch request held on `depends_on` produces no result file for up
   to 24 h, so the planner cannot tell queued from lost.
4. A reused request id overwrites its `launch-results/` file.
5. `bragi/CLAUDE.md` says Bragi cannot write outside the vault and also
   makes it the owner of the lessons folder; `ARCHITECTURE.md` states
   the 30-minute Bragi cron as fact while `launch-bragi-template.sh`
   labels it "Scheduling (future)" and SETUP.md comments it out.
6. `CLAUDE.md` says dev Claude runs on the VM; this review ran from the
   Omarchy desktop checkout at `~/Projects/saga`.
7. `CLAUDE.md` constraints 1 and 2 cite the wrong issue (#16238) and a
   bug-window result (§1).

## 6. Recommendation and sequencing

**Step 0 (half a day): re-test billing on the current CLI.** In a
throwaway dvergr container with the credentials volume mounted and no
auth env vars: `claude -p 'say ok'` and check `/status` or the usage
dashboard; then `claude setup-token` with a verified 108-character token
in `CLAUDE_CODE_OAUTH_TOKEN`; then the Agent SDK with an API key from a
Console org linked to the Max plan's credits, and again with `/login`
credentials. Record all four in `CLAUDE.md`. The same result governs
muninn's Opus synthesis container and its SPEC, which assume the
credentials volume.

**Step 1 (a few days): define the Odin contract.** Inbound events
(fleet status, journal entries, alerts, plateau signals, Mimir verdicts,
Eir failures, operator messages), outbound actions (guidance, events,
alerts, Mimir requests, launch-request drafts, commands, journal
writes), memory files, and the Telegram conversation. Today these are a
dozen directory conventions in `odin/CLAUDE.md` and `ratatoskr.py`. This
is GENERALIZATION.md Move 2 scoped to one role, and it is what makes
Runtime A and Runtime B interchangeable.

> **Update 2026-10-14:** the contract is drafted in
> [`ODIN-IO-CONTRACT.md`](ODIN-IO-CONTRACT.md) with Victor Taelin's
> UniiChat design (one append-only log, a binary tree of 512-byte
> summaries, a constant-size view, `zoom`) as Odin's memory and context
> system.
>
> **Update, later the same day (`DECISIONS.md` v2, D7 and D19):** the
> runtime question is settled differently from the first reading. Odin
> is a supervisory layer over Claude Code's execution harness through
> the Agent SDK: the Odin service owns commitments, memory, event
> intake, wake policy, session lifecycle, delegation and review
> coordination; Claude Code owns reasoning and tools within a session.
> UniiChat's memory ideas (durable log, hierarchical summaries, bounded
> briefing, `zoom`) are kept and adapted to that boundary; its exact
> prompt layout, cache economics and fresh-call-per-message are not
> promised. A custom Messages API runtime is considered only if the
> measured requirements cannot be met through the harness. So Runtime B
> below is closest to the target in spirit (first-party harness, Odin as
> the layer around it) but implemented through the SDK rather than an
> interactive session, and Runtime A survives only as that conditional
> fallback. Build order: the Saga service first, then the Odin service
> and integration package.

**Step 2: Odin harness v1 as a Claude Code plugin in its own repo
(Runtime B).** Components: an MCP server (ratatoskr as tools), an
injector that posts MQTT and file events into Odin's session through
the inbox socket (or a mod once mods have settled), hooks
(`UserPromptSubmit` for mechanical slash parsing, `Stop` for mechanical
end-of-turn checks, `SessionStart` to load the journal, `PreCompact` to
persist), skills (spec-dev, decomposition, retrospective ritual,
guidance), a scheduler (`/loop` scheduled tasks or a mod timer) for
digests, settings with `crossSessionInbound: accept`. Installed into the
saga-odin image from a Gitea-hosted marketplace. Keeps the Telegram
channel plugin, plan limits, the one-hour cache, and the explicitly
permitted deployment shape. The persona shrinks to a core plus skills.
Versioned independently of Saga.

**Step 3: Odin harness v2 on the Agent SDK against the same contract
(Runtime A), as the parallel experiment.** A small Python or TypeScript
service: durable turn queue with wake/interrupt and idempotency keys;
MQTT subscriber and inotify watchers feeding it; the same MCP tools;
outbox written with the state change; scheduler with a missed-run
policy; its own Telegram bot with approval buttons bound to the hash of
the exact request (the Channels plugin may also work under `-p` with the
allowlisted Telegram plugin; verify); bounded memory; cache-stable
prompt with one-hour cache writes; session rotation. Funded by the
included API credits so it never competes with dvergar for plan limits.
Run it on one project alongside v1 and keep whichever removes more of
the "TUI driven as a daemon" failures. The field evidence favors this
shape for the long run; the policy evidence favors keeping v1 as the
fallback.

**Step 4: worker contract and a Codex worker image**, Heimdall per-image
policy, `claude -p "/goal …"` for Claude workers, Pi for API-key or
local models. ACP (JSON-RPC over stdio; adapters for Claude, Codex, Pi,
Hermes, OpenCode, Goose; capability negotiation that can withhold
`terminal` and force permission callbacks) is the optional uniform
driver for later; it is not a substitute for MQTT between containers.

**Step 5: the Saga hygiene items in §5.4**, in the order JSON verdicts,
mandatory audit hooks, single refresher, mechanical gates, budgets.

What this does *not* recommend: adopting Hermes, oh-my-pi, Pi, OpenCode,
Exo, Nerve or openhuman as Odin's runtime; pointing any third-party
harness at the shared subscription credentials; or generalizing Saga's
bus, chat surface or policy engine before a second deployment exists
(GENERALIZATION.md §5 still applies).

## 7. Risks and open items

- **Policy drift.** Three reversals in 2026. Keep the interactive
  runtime (v1) working as the fallback for the SDK runtime (v2), and
  keep API-key versus login switchable by configuration.
- **"Ordinary, individual usage."** Odin plus several dvergar on one Max
  plan is heavier than ordinary. Yegge's experience says the wall is
  quota, not price. Moving Odin to API credits reduces plan pressure;
  Codex workers are the documented hedge.
- **New primitives are new.** Mods are two weeks old; the inbox socket's
  wire format beyond the auth line is undocumented; custom Channels are
  gated behind an interactive dialog on Pro/Max. Build v1 on the inbox
  socket and hooks first, mods second.
- **`--bare` becoming the `-p` default** would silently require an API
  key for headless workers; pin the explicit non-bare form.
- **Is Saga currently running?** Last commit 2026-05-06, Phase 3 run #2
  in flight then. Since then the operator's work moved to the
  standalone desktop stack (all five repos created 2026-09-05 to
  09-11), muninn's July work proceeded without Saga, and braid's
  roadmap records "Saga is deferred by user direction".
  GENERALIZATION.md's "stable base" trigger should be judged honestly
  before adding a second surgery site; the contract work (step 1) is
  safe regardless, and the VM's live state (deployed `heimdall.py`
  revision, stray `commands/` files, vault and lessons contents) was
  not inspected in this review.
- **Unverified in this pass:** whether hooks fire under `codex exec`;
  whether onboarding dialogs appear under `claude -p` in a fresh
  container; whether the Telegram channel plugin works in SDK mode;
  Max 20x's list price (reported $200); exact weekly limits (none
  published).

## 8. Sources

Primary research notes (with inline URLs for every claim) are in
[`harness-research-2026-10/`](harness-research-2026-10/README.md):
`claude_code_platform.md`, `third_party_harnesses.md`,
`orchestrators_and_loops.md`, `custom_harness_and_interop.md`, the
seven `deep_dive_*.md` files, and `saga_side_observations.md`.
Pages verified directly by the coordinator: Help Center article
15036540, platform.claude.com "API credits for Max and Team plans",
code.claude.com "Legal and compliance".
