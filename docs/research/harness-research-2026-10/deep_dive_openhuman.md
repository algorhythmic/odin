# Deep dive: OpenHuman (tinyhumansai/openhuman) as a harness for Saga

Scope note: findings are as of 2026-10-13/14. Source code citations refer to `main` at commit `e452a415b1ea586ea42814c277648abeafb0b9a7` (merged 2026-10-14, workspace version `0.64.15`), shallow-cloned and read without executing anything. `B` = `https://github.com/tinyhumansai/openhuman/blob/main/`. Doc pages live under `docs/gitbooks/en/` and are also published at https://tinyhumans.gitbook.io/openhuman/. Statements tagged **[inference]** are mine, not documented.

---

## 1. Identity: what it is, who builds it, dates, license, runtime, activity, maturity, community, funding

### Takeaway
OpenHuman is a very young (repo created Feb 2026, public beta May 2026), very high-velocity, single-maintainer-dominated GPL-3.0 Rust project from "Tiny Humans" (GitHub org `tinyhumansai`). It ships as a Tauri desktop "personal AI" app, a headless JSON-RPC server, and an embeddable Rust library. It has ~42k stars, but it is officially "early beta" and its architecture has changed a great deal within months. I found no public information about funding.

### Cited Findings
- Self-description: "The fastest, cheapest, most efficient open-source agent harness. Run more than 500 agents on a $10 VPS." Also: "A desktop app for people. A Rust library for developers." — [GitHub repo / README](https://github.com/tinyhumansai/openhuman)
- README carries an "early beta" badge and says "OpenHuman is under active development, so expect rough edges." — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md)
- GitHub API (2026-10-14): created 2026-02-18; 41,958 stars; 4,128 forks; 198 subscribers; `open_issues_count` 309 (this count includes PRs); primary language Rust; license GPL-3.0; topics include agent-orchestration, local-first, mcp, tauri, second-brain. — [GitHub API repos/tinyhumansai/openhuman](https://api.github.com/repos/tinyhumansai/openhuman)
- Totals (GraphQL): 2,672 issues, 4,918 PRs, 63 releases, 34 discussions. A search shows 288 open issues. — [GitHub issues](https://github.com/tinyhumansai/openhuman/issues)
- The oldest commit on `main` is dated 2026-01-26, author "M3gA-Mind", message "Initialize Tauri application with React and TypeScript setup…". History therefore predates the repo's creation date. `main` has about 39,684 commits. — [GitHub commits](https://github.com/tinyhumansai/openhuman/commits/main)
- Commit activity: 39,503 commits in the last 52 weeks. Weekly counts for the last 12 weeks were 115, 115, 1375, 1370, 3914, 2520, 975, 2779, 1717, 5185, 4028, 7909. — [GitHub stats/participation API](https://api.github.com/repos/tinyhumansai/openhuman/stats/participation)
- Contributor concentration: `senamakel` has 30,701 commits. Next are M3gA-Mind (2,214), YellowSnnowmann (1,526), graycyrus (905), oxoxDev (805) and github-actions[bot] (693). The contributors API lists 180 contributors. — [GitHub contributors](https://github.com/tinyhumansai/openhuman/graphs/contributors)
- The README names "@senamakel (creator)". Recent merge commits are authored by "Steven Enamakel", and some are co-authored by "Medulla <medulla@tinyhumans.ai>" (4 of the last 100 commit messages). — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md); [commits](https://github.com/tinyhumansai/openhuman/commits/main)
- Releases: the earliest GitHub release still published is v0.49.32 (2026-03-31). The latest is v0.64.15 (2026-10-09), titled "The Installed-Build Reliability Upgrade", a hotfix for module admission in installed builds. There are 113 tags. — [Releases](https://github.com/tinyhumansai/openhuman/releases); [v0.64.15](https://github.com/tinyhumansai/openhuman/releases/tag/v0.64.15)
- Third-party sources date the public early-beta launch to May 2026 (one says May 13, 2026). — [Vellum (Aug 7, 2026)](https://www.vellum.ai/blog/best-openhuman-alternatives); [aitoolly 2026-05-13](https://aitoolly.com/zh/ai-news/article/2026-05-13-openhuman-a-new-private-and-powerful-personal-ai-superintelligence-project-emerges-on-github)
- Popularity claims: README says it was "the number one trending repository on GitHub for nine days in a row" within a week of launch. Third-party star counts were 21.8K on May 20, 27k in late May, and 33K "in a month". — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md); [CSDN](https://damodev.csdn.net/6a4379c5662f9a54cb86b71b.html); [mager.co (May 26, 2026)](https://mager.co/blog/2026-05-25-openhuman-explainer/); [themenonlab](https://themenonlab.blog/blog/openhuman-personal-ai-33k-stars-month)
- License is GPL-3.0 (LICENSE; CITATION.cff `license: "GPL-3.0"`). The vendored sibling crates are also GPL-3.0: tinyagents (122★, created 2026-06-29), tinychannels (8★), tinymemory (10★), tinyskills (1★), tinyjuice (22★), tinybox (2★), tinyflows (66★), tinybus (2★). — [B LICENSE](https://github.com/tinyhumansai/openhuman/blob/main/LICENSE); [B CITATION.cff](https://github.com/tinyhumansai/openhuman/blob/main/CITATION.cff); [tinyagents](https://github.com/tinyhumansai/tinyagents)
- Runtime: a Rust workspace of 7 crates (`openhuman-core`, `-embed`, `-rpc`, `-tinyhumans`, `-cli`, `-tui`, `-app`) plus 18 git submodules under `vendor/`. A Tauri v2 + React/TypeScript desktop app lives in `app/`. Contributors need Rust 1.96.1, Node 24+ and pnpm 10.10. My count of the clone: 3,445 `.rs` files, about 735k lines of Rust including tests and excluding the unpopulated submodules. — [B crates/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/README.md); [B .gitmodules](https://github.com/tinyhumansai/openhuman/blob/main/.gitmodules); [README Contributing](https://github.com/tinyhumansai/openhuman/blob/main/README.md)
- Company: the org "Tiny Humans" describes itself as "An AI Lab focused on building towards Open-Source AGI". The org was created 2025-11-25, lists its location as "United States of America", and has 62 public repos. tinyhumans.ai lists three products: OpenHuman, OpenCompany ("team of AI specialists") and Medulla ("a single terminal that runs Claude Code, Codex, and OpenCode side by side"). — [GitHub org](https://github.com/tinyhumansai); [tinyhumans.ai](https://tinyhumans.ai/)
- The tinyhumans.ai pricing page lists credit-based plans: Basic at $20/mo with $21 credits, Pro at $200/mo with $210 credits, and Enterprise at a custom price. They cover OpenCompany, Medulla and the API (LLM/embeddings/voice/OAuth APIs, memory storage). No OpenHuman-specific plan is listed. — [tinyhumans.ai/pricing](https://tinyhumans.ai/pricing)
- Community channels: Discord (guild.tinyhumans.ai), r/tinyhumansai, X @tinyhumansai, GitHub Discussions. Contributors get "free merch". — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md)
- Crypto adjacency: the product includes a non-custodial multi-chain crypto wallet and a `web3` module. A third-party exchange page lists an "OPENHUMAN" token, described in search results as a community coin on Base. — [B features/wallet.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/wallet.md); [WEEX listing](https://www.weex.com/fa-IR/spot/OPENHUMAN-USDT)

### Inferences
- **[inference]** About 77% of all commits come from one account. At roughly 1,000+ commits per day in some weeks, and with PR templates that require "AI Authored PR Metadata (required for Codex/Linear PRs)" ([PR #7020](https://github.com/tinyhumansai/openhuman/pull/7020)), most code is very likely AI-agent-generated under one maintainer's direction. That makes the codebase large, fast-moving and hard for an outsider to audit.
- **[inference]** Version numbers jumped from 0.49 to 0.64 in six months, with no published 1.0 or stability policy for APIs. Treat every interface (RPC names, config keys, hook events) as unstable.

### Gaps
- Funding, investors, legal entity, headcount: not found. A search for "Tiny Humans"/Enamakel funding only returned an unrelated company ("Humans&").
- Why releases before v0.49.32 are missing (deleted, or history imported from another repo): could not determine.
- I did not verify whether the OPENHUMAN token is affiliated with the project.

---

## 2. Architecture: agent loop, tools, prompt assembly, context/compaction, memory, sessions, sub-agents, scheduling, gateways, observability, storage

### Takeaway
The loop is a conventional streaming tool-call loop (the `tinyagents` crate's `AgentHarness`), wrapped in a large amount of product machinery. That machinery includes a frozen-prefix prompt-cache discipline, layered tool rules, content-aware tool-output compression with lossless retrieval handles, filesystem artifact offload, a no-progress circuit breaker, durable async sub-agents with a spawn-tier hierarchy, cron and durable workflow graphs, 15 chat channels including Telegram, and a JSONL event journal with replay RPCs. Memory is not local: it requires CortexDB, either hosted by TinyHumans or your own.

### Cited Findings

**Turn lifecycle and loop**
- Every turn, whether a user message, Telegram message, webhook, cron tick or Composio event, goes through the same lifecycle. External triggers pass through triage first. `Agent::turn()` then: (1) resumes the transcript, (2) builds the system prompt (first turn only), (3) recalls a memory pack, (4) enters the tool loop, (5) dispatches tools and sub-agents, (6) runs the context guard and compaction, (7) checks stop hooks, (8) returns final text. Post-turn hooks run asynchronously afterwards. — [B docs/.../developing/architecture/agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- The inner loop is tinyagents' `AgentHarness`, assembled per turn by `run_turn_via_tinyagents_shared` (`crates/openhuman-core/src/agent/tinyagents/mod.rs`). Each iteration: context guard → stop-hook check → provider call (streamed) → parse → return if there are no tool calls → execute tools → summarize oversized results → append → loop. — [agent-harness.md §The tool-call loop](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Iteration cap: an explicit `[agent] max_tool_iterations_override` (or `OPENHUMAN_AGENT_MAX_TOOL_ITERATIONS`) wins. Otherwise the agent definition's cap applies (the orchestrator's is 200), then the default of 10. The model is told how many calls remain at 50% and 80% of budget. Capped turns report `hit_cap: true` plus a `checkpoint`. — [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md). The cap has churned: [#6930](https://github.com/tinyhumansai/openhuman/issues/6930) "raise orchestrator turn cap from 15 to 50" (Oct 2, 2026).
- Streaming: every iteration emits `AgentProgress` events (token deltas, tool status, per-iteration cost). The embed API's `Agent::stream` returns a bounded `TurnStream` of `Progress` events ending in `Finished`, and dropping the stream cancels the turn and its child work. — [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [embed/concepts/turns-sessions.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/turns-sessions.md)
- Tool-call dialects: `native` (structured), `xml` (`<tool_call>{json}</tool_call>`), `pformat` (compact positional), and `python`/`typescript` code-call syntax. `auto` uses native calling where supported and falls back to prompt-guided calls for providers such as local Ollama. — [agent-harness.md §Tool dispatch](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Reliability and retries:
  - A no-progress circuit breaker (`RepeatedToolFailureMiddleware` over tinyagents' `NoProgressTracker`) fingerprints tool-call arguments and escalates Continue → Nudge (injects a "no progress since step X" message) → Halt (records a root-cause summary). The threshold is 3 consecutive identical failures. Recoverable failures (timeouts, resets, rate limits, 5xx) get extended headroom.
  - Unknown-tool and malformed-argument calls are rewritten into recoverable results.
  - Every tool failure is classified into a `ClassifiedFailure` (MissingPermission, ServiceUnavailable, BadCredentials, BlockedByPolicy, Timeout, Denied, ApprovalExpired…).
  - A halted turn closes with a "grounded close": a tools-disabled wrap-up call, then a separate checker call, then a deterministic fallback.
  - Source: [agent-harness.md §Reliability](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md). Throttle retry: [#6510](https://github.com/tinyhumansai/openhuman/issues/6510) "give a throttled model call a retry schedule that outlasts the throttle".
- Interrupts: Ctrl+C or `/stop` go through the tinyagents steering/cancellation seam. The loop stops at safe points (before each tool execution, sub-agent spawn and provider call), and sub-agents share the cancellation scope. — [agent-harness.md §Interrupts](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)

**Tools**
- Built-in tool families: shell and coder, scraper, documents, image/video generation, cron, browser and desktop control, web search (Exa/Gemini managed; Brave, Tavily, Parallel and others with your own key), memory, `todo`, `goal_*`, and sub-agent spawn/delegate. There are also 119 Composio OAuth apps. — [README "For users"](https://github.com/tinyhumansai/openhuman/blob/main/README.md); [features/native-tools/](https://github.com/tinyhumansai/openhuman/tree/main/docs/gitbooks/en/features/native-tools)
- Tool discovery: tools can be `Deferred` and found with `tool_search`. "Jev" is a tiny ranking model that the README says has the right tool in its top picks 86.8% of the time out of 1,215 tools, versus 70.5% for keyword search. The orchestrator loads "tool packs" (`coding`, `web3`, `system`, `scheduling`, `docs`, `mcp`) on demand via `use_skill`. — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md); [agent-harness.md §built-in archetypes](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Tool rules (`tinytools::ToolRules`) take effects `allow | deny | hide | require_approval | auto_approve` and match on name/family/tag globs, side effects and context (e.g. `when = { channel = "telegram" }`). Rules stack in layers: operator `[tool_rules]` in config.toml, then agent definitions, then sub-agent definitions. Refusals return the rule id, layer and reason. Code: `crates/openhuman-core/src/tools/rules/`. — [agent-harness.md §Tool rules](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)

**System prompt assembly**
- The system prompt is built once, on the first turn, from identity, soul (`SOUL.md`), profile (`USER.md`), memory, connected integrations, tools and the safety preamble. It is then frozen so the KV cache stays valid, and dynamic per-turn context is appended as message content instead. The doc spells out three caching contracts: the tool block is part of the cacheable prefix, history must be append-only, and Anthropic `cache_control` markers go on the last tool, last system block and final message. — [agent-harness.md §Sessions](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); fix history: [#6230](https://github.com/tinyhumansai/openhuman/issues/6230) "make prompt caching actually reach the wire"
- AGENTS.md is supported in two layers: global `<workspace_dir>/AGENTS.md` and project `<action_dir>/AGENTS.md`. They are loaded once at prompt build, capped at about 20,000 chars per layer, and gated by `agent.agents_md_enabled` (default on). — [agent-harness.md §AGENTS.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- In the vendor's benchmark, the coding system prompt was 944 tokens and the 20 tool schemas were 3,647 tokens (4,591 static total). — [openhuman-benchmarks swe-x86-1 summary](https://github.com/tinyhumansai/openhuman-benchmarks/blob/main/results/swe-x86-1/summary.md)

**Context management and compaction**
- Every tool result passes a per-call byte budget (hard truncation with a marker). Microcompact and autocompact middleware (tinyagents `ContextLadder`) summarizes the middle of history while keeping the system prompt and recent turns. — [agent-harness.md §Context management](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Oversized results (default threshold 4,000 tokens) can be routed through a summarizer model. "TokenJuice" content-aware compressors cover JSON → table, code → signatures via tree-sitter, logs (100-rule engine), search, diffs and HTML. Each lossy compression stores the original in a CCR store behind a `⟦tj:<hash>⟧` handle, retrievable with `juice_retrieve`/`juice_find`/`juice_extract`. Coding agents default to `light` compression, so raw build/test/diff text is kept. — [agent-harness.md §TokenJuice](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [features/token-compression.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/token-compression.md)
- Filesystem offload: large sub-agent results go to `action_dir/outputs/`, and the parent receives an `[artifact] kind=output path=… bytes=…` pointer plus an abstract. Path resolution is fail-closed. — [agent-harness.md §Filesystem offload](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- "Compaction seals a generation and opens a child instead of erasing history." Separately, "20:1 compression keeps week-long sessions bounded." — [turns-sessions.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/turns-sessions.md); [features/orchestration.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/orchestration.md)

**Memory**
- Memory runs on a pluggable `MemoryEngine` trait (`recall`, `fetch`, `store`, `forget`, `list`, `health`), but only two engines ship and both are CortexDB:
  - `tinyhumans`: hosted, behind the TinyHumans backend.
  - `cortexdb`: your own CortexDB at `api-v1.cortexdb.ai` or self-hosted, with your key.
  - "If you are signed out and have no CortexDB key, memory is off." — [developing/engines.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/engines.md); [features/memory.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/memory.md)
- Per turn, a token-budgeted "memory pack" (learnings, beliefs, brain documents, this agent's history, other agents' turns) is added ephemerally inside `<memory-context>` and never persisted to the transcript. The `memory` tool offers recall, fetch, learn and forget. Turns are logged in the background with tool names but never arguments. The engine builds "beliefs" in the background. Items are scrubbed for secrets and PII before leaving the machine. — [features/memory.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/memory.md); [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Removed: "memory tree, graph view, goals list, people and contacts, learning profile, `MEMORY.md` or `PROFILE.md` files, or Obsidian vault", and the "Supermemory, Mem0, Cognee, agentMemory and the local TinyCortex engine" engines. — [features/memory.md §What is not here](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/memory.md). A May 2026 third-party write-up still described local SQLite "Memory Tree" storage and Obsidian vault files, which confirms a large redesign since launch. — [mager.co](https://mager.co/blog/2026-05-25-openhuman-explainer/)
- Hosted memory claims only TLS in transit and per-user tenant isolation. "The hosted service can read what it stores." — [features/privacy-and-security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/privacy-and-security.md)
- Pluggable memory adapters (Supermemory, mem0, etc.) are a roadmap item ([#5390](https://github.com/tinyhumansai/openhuman/issues/5390)), not shipped. — [overview/roadmap.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/overview/roadmap.md)

**Sessions, persistence, resume, journals**
- Transcript paths derive from thread and agent IDs. A resumed session reuses its recorded system prompt and tool declarations, so prompt, skill or integration edits apply only to new sessions. — [turns-sessions.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/turns-sessions.md)
- Each run appends to a durable event journal: a JSONL append store at `{workspace}/tinyagents_store/journal`, behind a `RedactingSink` that masks credentials before persistence, with restart-stable event ids `{run_id}-evt-{offset}`. Read-only RPCs: `agent_run_events` (paged replay), `agent_run_status`, `agent_runs_active`. — [agent-harness.md §Journals](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- `threads.edit_message` and `threads.regenerate` fork the transcript at a cut point. The sealed generation is never touched. — [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)

**Sub-agents and multi-agent**
- The user-facing agent is the "Master Agent" (id `orchestrator`). Built-in archetypes: `task_manager_agent`, `vision_agent`, `image_agent`, `video_agent`, `presentation_agent`, `skill_setup`, `workflow_builder`, `flow_discovery`. Non-chat archetypes: `planner`, `critic`, `summarizer`, `trigger_triage`, `trigger_reactor`, `morning_briefing`. Custom archetypes are TOML under `$OPENHUMAN_WORKSPACE/agents/*.toml`. — [agent-harness.md §Sub-agents](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); example definition [B crates/openhuman-core/src/agent/registry/agents/planner/agent.toml](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/agent/registry/agents/planner/agent.toml)
- `spawn_subagent` is durable and asynchronous by default:
  - It reuses a compatible running or idle worker (matched on parent thread, agent id, model, sandbox, action root and task key), injecting the instruction through its `RunQueue`.
  - Finished results are delivered into the parent chat as a new system turn via a JSONL completion store (`.openhuman/background_completions.jsonl`) with leases, so undelivered results are redelivered after a restart.
  - Related tools: `wait_subagent`, `steer_subagent`, `list_subagents`, `close_subagent`, `continue_subagent`.
  - Source: [agent-harness.md §Running a reusable sub-agent](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Spawn tiers: `chat` may spawn reasoning or worker, `reasoning` may spawn worker, and `worker` spawns nothing. The rule is enforced at loader time (`validate_tier_hierarchy`) and by a runtime `MAX_SPAWN_DEPTH = 3`. Sub-agent handback resolves to `Completed`, `AwaitingUser {question, options}` or `Incomplete {reason}`. — [agent-harness.md §Spawn hierarchy / Reliability](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Graph orchestration (tinyagents): a `plan → execute ⇄ review → finalize` delegation graph checkpointed with `SqliteCheckpointer`, workflow phase DAGs with map-reduce fan-out, and agent-teams runtime graphs. A `burst` model tier serves high-fanout, low-context workers. — [agent-harness.md §Agent engine](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [features/orchestration.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/orchestration.md)
- Roadmap: an agent-to-agent (A2A) protocol ([#3463](https://github.com/tinyhumansai/openhuman/issues/3463)) and an "external agent runtimes" layer for Cursor, Windsurf and Codex via ACP ([#4731](https://github.com/tinyhumansai/openhuman/issues/4731)). — [overview/roadmap.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/overview/roadmap.md)

**Scheduling, background jobs, triggers, workflows**
- Cron tools: `cron_add`, `cron_list`, `cron_update`, `cron_remove`, `cron_run`, `cron_runs`, plus a one-shot `schedule` tool. Agent jobs must be at least 5 minutes apart. Shell jobs have no limit. — [features/native-tools/cron.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/native-tools/cron.md)
- Triggers (Composio events: Gmail, Slack, GitHub, etc.) arrive via the OpenHuman backend, which verifies the webhook and forwards over Socket.IO. A cheap `trigger_triage` agent then decides `drop` / `acknowledge` / `react` / `escalate`. "The raw webhook never reaches your machine." — [features/integrations/triggers.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/triggers.md)
- Workflows (tinyflows) are durable graphs with cron, event or manual triggers and approval steps. The `webhook` trigger is "Not implemented. Enabling logs an actionable warning; incoming webhook requests are observed but never start a run." — [features/workflows.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/workflows.md); [B crates/openhuman-core/src/flows/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/flows/README.md)
- Goals and todos: a session `todo` list (Claude Code/Codex shape) and per-thread goals (`goal_set`, `goal_get`, `goal_complete`) with token budgets. — [features/goals-and-todos.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/goals-and-todos.md)

**Chat gateways and input injection**
- There are 15 channel providers: Telegram (Bot API long-poll; your own BotFather token or a managed bot), Discord, Web, iMessage, Lark/Feishu, DingTalk, Yuanbao, Slack, WhatsApp, IRC, Signal, Mattermost, QQ, Linq (SMS) and Email (IMAP IDLE/SMTP). Matrix was removed. Telegram is "the only channel with its own approval surface" (inline approvals), with typing indicators, live drafts and "remote-control commands". Proactive messages go to the "default channel". — [features/channels.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/channels.md)
- Channel transports live in the TinyChannels module, loaded over TinyBus. "The host does not build provider implementations or fall back to local listeners when the module is unavailable." — [B crates/openhuman-core/src/channels/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/channels/README.md)
- The `channel.web_chat` RPC accepts `queue_mode`: `interrupt` (default; cancels the in-flight turn), `steer`, `followup`, `collect` (pushed onto the running turn's `RunQueue` lanes), or `parallel` (isolated fork). It also takes `run_mode: plan|build` and `reasoning_effort`. — [B crates/openhuman-core/src/web_chat/schemas.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/schemas.rs); [B web_chat/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/README.md); [B web_chat/types.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/types.rs)
- No MQTT support anywhere: a grep for "mqtt" across `.rs`, `.md` and `.toml` in the repo returned nothing (my search of the clone).

**Observability and telemetry**
- Per-turn cost (`UsageInfo`, `TurnCost`, backend-authoritative `charged_amount_usd`), live `turn_cost` socket events, context-window gauges, an OTel/Langfuse span model, a local NDJSON exporter (opt-in), an inference capture proxy (`scripts/debug/capture-first-inference.mjs`) and prefix-divergence audit scripts. — [agent-harness.md §Cost accounting](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [developing/agent-observability.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/agent-observability.md)
- Defaults in code: `analytics_enabled = true` (Sentry/product analytics). `share_usage_data = true` ("structured trace spans with the OpenHuman backend's Langfuse"). `agent_tracing.capture_content = true`, meaning "prompt/reply text and tool I/O ride along". — [B crates/openhuman-core/src/config/schema/observability.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/config/schema/observability.rs). Issue [#7016](https://github.com/tinyhumansai/openhuman/issues/7016) "Prompt/reply traces are uploaded to Langfuse by default without opt-in" and PR [#7020](https://github.com/tinyhumansai/openhuman/pull/7020) to make them opt-in were both still OPEN on 2026-10-14.

**State storage**
- One storage URL picks the backend for the whole process: `memory`, `sqlite:<path>` (default `sqlite:<workspace>/storage`), `file:<dir>` (JSON docs plus JSONL streams), or `mongodb://…`. Ports: DocumentStore, StreamStore (transcripts, journals), BlobStore, SearchIndex, SecretStore. Data is scoped per agent id or per SaaS profile. — [developing/architecture/storage.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/storage.md)

### Inferences
- **[inference]** The loop itself is not unusual. What OpenHuman adds is a deep product layer around it: queueing, durability, caching discipline, compression, breakers and journals. Much of that layer is reusable as design patterns. Much of it is also coupled to the TinyHumans backend: memory, triggers, managed search and Composio.
- **[inference]** Running Saga's planner on OpenHuman without the hosted backend would mean no memory engine unless a CortexDB is reachable, no Composio triggers, and no managed search.

### Gaps
- I did not read the tinyagents loop source (the submodule was not cloned). Retry/backoff parameters for provider HTTP errors are only partially documented.
- I could not determine whether CortexDB (cortexdb.ai) is owned by TinyHumans or whether a self-hosted CortexDB is free or open-source. cortexdb.ai names no company or license ([cortexdb.ai docs](https://www.cortexdb.ai/docs/concepts)).

---

## 3. Extension model: plugins, hooks (event names), skills, AGENTS.md, MCP, custom tools, configuration

### Takeaway
OpenHuman has a rich extension surface:
- file-based `hooks.json` hooks that deliberately match Cursor's contract and alias Claude Code's names;
- agentskills.io-style `SKILL.md` bundles, including `.agents/skills` paths;
- AGENTS.md;
- an MCP client with registry search, plus a small stdio MCP server;
- in-process Rust tools and hooks via the embed library;
- TOML configuration.

Several lifecycle events are defined but not yet fired, notably `sessionStart`, `sessionEnd`, `preCompact` and `subagentStop`.

### Cited Findings
- `hooks.json` (schema version 1) is concatenated from four layers: System (`/etc/openhuman/hooks.json`…), User (`~/.openhuman/hooks.json`), Workspace (`<workspace_dir>/hooks.json`) and Project (`<action_dir>/.openhuman/hooks.json`). "The strictest verdict wins" (deny > ask > allow). — [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
- Hook fields: `command`, `type` (`command` | `prompt`), `matcher`, `timeout` (default 30 s), `failClosed`, `loop_limit` (follow-ups per session, default 5, `0` = unlimited), `model`, `enabled`. Protocol: event JSON on stdin; exit 0 means stdout is the decision, exit 2 means deny (stderr becomes the reason), any other exit fails open unless `failClosed`. Decision fields: `permission`, `user_message`, `agent_message`, `updated_input`, `additional_context`, `continue`, `followup_message`, `env`. — [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
- Hook events that are wired and fire today:
  - `preToolUse`, `postToolUse`, `postToolUseFailure`
  - `beforeShellExecution`, `afterShellExecution`
  - `beforeReadFile`, `afterFileEdit`
  - `beforeMCPExecution`, `afterMCPExecution`
  - `beforeSubmitPrompt` (Claude Code's `UserPromptSubmit` maps to it)
  - `subagentStart`
  - `stop` (honors `followup_message`: "sent as another user turn")
  - `afterAgentResponse`
  - Source: [developing/hooks.md §Events](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
- Defined but NOT fired yet: `sessionStart`, `sessionEnd`, `preCompact`, `afterAgentThought`, `subagentStop`. "The core does not fire them yet", and `hooks list` reports `"wired": false` for them. — [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
- Hook processes get `OPENHUMAN_PROJECT_DIR` (also exported as `CLAUDE_PROJECT_DIR` and `CURSOR_PROJECT_DIR`), `OPENHUMAN_HOOK_EVENT`, `OPENHUMAN_SESSION_ID` and `OPENHUMAN_AGENT_ID`. Observational events run in the background, so "a hung audit hook cannot hang the agent". "Prompt" hooks send the event to a model for an `{"ok": …}` verdict. Debug commands: `openhuman-core hooks list|reload|test`. — [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
- In-process Rust hooks: post-turn hooks receive a `TurnContext` (user message, response, every tool call with arguments and outcome, wall-clock, iteration count, session ID). Stop hooks are mid-turn policy levers (budget USD cap, max iterations, actions/hour). They can be scoped per agent without leaking to siblings. — [agent-harness.md §Hooks](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [embed/concepts/hooks-seams.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/hooks-seams.md)
- Skills follow agentskills.io-style `SKILL.md`/`WORKFLOW.md` with YAML frontmatter and an optional `skill.toml`/`workflow.toml`. Scan roots: builtin; user `~/.openhuman/skills/`, `~/.agents/skills/`, `~/.openhuman/workflows/`; project `<workspace>/.openhuman/skills/`, `<workspace>/.agents/skills/` (only with a `.openhuman/trust` marker); legacy `<workspace>/skills/`. Skills appear as a compact catalog, and `run_workflow` "starts a separate agent run". "Skill bodies are never spliced into a chat turn." — [B crates/openhuman-core/src/skills/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/skills/README.md)
- The skills catalog has about 90,000 entries (HermesHub, ClawHub, LobeHub). Downloads are HTTPS-only with SSRF guards and a supply-chain scan before install. — [features/integrations/mcp-and-skills.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/mcp-and-skills.md)
- MCP client: it searches Smithery.ai and the official MCP registry, installs stdio subprocesses or HTTP servers, stores them in SQLite (`mcp_clients/mcp_clients.db`), and a supervisor probes each server about every 60 s with backoff. There is an MCP OAuth callback at `GET /oauth/mcp/callback`. — [mcp-and-skills.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/mcp-and-skills.md); [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md)
- MCP server: `openhuman-core mcp` (stdio) exposes `memory.recall/fetch/list/learn/forget`, `web_search`, `web_answer`, `searxng_search`, `core.list_tools`, `core.tool_instructions`, `agent.list_subagents` and `agent.run_subagent`. — [developing/mcp-server.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/mcp-server.md)
- Custom tools: `AgentSpec::tools` takes a per-turn factory of `Box<dyn Tool>`. These reach the model as real tools with their own schemas, unlike MCP indirection. — [agent-harness.md §An embedder's own tools](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- "Loadable modules" are first-party `cdylib` libraries loaded into the core and served over TinyBus. Search, memory and channels are modules. — [developing/loadable-modules.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/loadable-modules.md); [B AGENTS.md](https://github.com/tinyhumansai/openhuman/blob/main/AGENTS.md)
- Configuration surfaces:
  - TOML `config.toml` in the workspace (`~/.openhuman`), with `[autonomy]`, `[tool_rules]`, `[hooks]`, `[storage]`, `[local_ai]`, `[memory]`, `[tokenjuice]`, `[runtime]`, etc.
  - Agent definitions in TOML.
  - `hooks.json`.
  - Many env vars (`.env.example` is 28 KB).
  - Every controller is reachable as JSON-RPC 2.0 (`openhuman-core <namespace> <function>` or `call --method`).
  - Sources: [B .env.example](https://github.com/tinyhumansai/openhuman/blob/main/.env.example); [B crates/openhuman-cli/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-cli/README.md)

### Inferences
- **[inference]** Hook compatibility with Claude Code is partial. Claude Code's `SessionStart` (which Saga dvergar use to read guidance) has no working equivalent today. `beforeSubmitPrompt` with `additional_context` is the closest substitute. `stop` with `followup_message` is the equivalent of the Stop-hook mechanism that `/ralph-loop` relies on.

### Gaps
- I did not verify whether `loop_limit: 0` on a `stop` hook works reliably for very long unattended loops (there are no tests or issues about it).

---

## 4. Autonomy and unattended operation: headless/server modes, loop modes, Docker/no-TTY, first-run, required config

### Takeaway
It is built to run headless:
- `openhuman-core serve` (JSON-RPC + Socket.IO, port 7788);
- a one-shot in-process `call` mode;
- a published Docker image (amd64) with a non-root user and a healthcheck;
- an embeddable library that needs no daemon.

There is no built-in "loop until done" mode. Goals are not auto-continued, and loops must come from `stop`-hook follow-ups, cron, workflows or an external driver. A server host needs a bearer token, a keyring master key and, for most BYOK cloud providers, a TinyHumans account or API key.

### Cited Findings
- `openhuman-core` subcommands:
  - `run`/`serve` (flags `--host`, `--port`, `--jsonrpc-only`, `--headless-api` = "JSON-RPC only, no background services")
  - `call --method <name> [--params '<json>' | --params-stdin]` ("Invoke one controller in-process (no server needed)… methods that run a turn work")
  - `mcp`
  - `agent dump-prompt|list`
  - `<namespace> <function>`
  - Source: [B crates/openhuman-cli/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-cli/README.md)
- `openhuman.inference_agent_chat` ("Run one-shot agent chat") takes `message`, `model_override`, `thread_id`, `agent_id`, `cwd` (turn working directory), and a per-call `inference_url`/`api_key`/`inference_headers` that are never persisted. It returns `result`, `logs`, `hit_cap` and `checkpoint`. — [B crates/openhuman-core/src/inference/host_runtime/schemas.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/host_runtime/schemas.rs)
- Docker image: `ghcr.io/tinyhumansai/openhuman-core:<version>` (`linux/amd64`; arm64 ships as a tarball). It runs as UID 10001 via a gosu entrypoint that chowns the volumes, exposes `EXPOSE 7788`, has `HEALTHCHECK curl /health` and `CMD ["serve"]`. Deploy recipes exist for DO App Platform, Docker Compose, Fly.io and OCI Terraform. — [B Dockerfile](https://github.com/tinyhumansai/openhuman/blob/main/Dockerfile); [B scripts/docker-entrypoint-core.sh](https://github.com/tinyhumansai/openhuman/blob/main/scripts/docker-entrypoint-core.sh); [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md)
- Required server config:
  - `OPENHUMAN_CORE_TOKEN` ("Anyone with this token can drive the core").
  - `BACKEND_URL` (listed as required, pointing at `https://api.tinyhumans.ai`).
  - `OPENHUMAN_KEYRING_MASTER_KEY` or `_FILE` when there is no OS keychain. Without it, provider-key writes fail with "Failed to encrypt api_key".
  - A persistent `OPENHUMAN_WORKSPACE` volume.
  - Source: [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md)
- Headless without a TinyHumans account: custom cloud providers "are built only when a backend session or TinyHumans API key exists. Without one, every turn fails with a `SESSION_EXPIRED`". The documented workaround is the `local-openai` runtime (any OpenAI-compatible endpoint). Claude Code CLI, Claude Agent SDK and local runtimes are exempt (`provider_uses_independent_auth`). Library (embed) hosts skip the account gate. — [features/cloud-deploy.md §Headless without a TinyHumans account](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md); [B crates/openhuman-core/src/inference/provider/factory/access_gates.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/provider/factory/access_gates.rs)
- Library mode: "call an agent like any other function, with no sidecar or daemon to run". `RuntimeBuilder::lean()` runs turns with no background services. — [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md); [embed/guides/lean-headless.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/guides/lean-headless.md)
- No autonomous goal continuation: "OpenHuman runs no autonomous goal continuation, so every accounted turn is user-initiated." — [B crates/openhuman-core/src/agent/goals/runtime.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/agent/goals/runtime.rs)
- Loop mechanisms that do exist:
  - `stop` hook `followup_message` (re-prompt) with `loop_limit` (0 = unlimited) — [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)
  - cron agent jobs at ≥5-minute spacing — [cron.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/native-tools/cron.md)
  - durable resumable workflow runs — [workflows.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/workflows.md)
- Unattended approvals: the autonomy policy is off by default, so acting tool calls run without prompts. When it is on, approval by turn origin works as follows:
  - Cron, background jobs, CLI and delegated sub-agents are "Allowed, no row".
  - External channel turns (Telegram, Slack) "Park and write a row".
  - Parked calls are denied after a 10-minute TTL.
  - Browser actions are force-denied outside live web chat unless `[browser] unattended_actions` allows them.
  - Source: [features/approval-gate.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/approval-gate.md)
- A no-UI Linux build for servers or a Raspberry Pi is still an open issue ([#4844](https://github.com/tinyhumansai/openhuman/issues/4844)). Recent fixes for headless gaps include keyring master key ([#6935](https://github.com/tinyhumansai/openhuman/issues/6935)), Compose read-only root ([#6925](https://github.com/tinyhumansai/openhuman/issues/6925)) and documented headless gaps ([#6927](https://github.com/tinyhumansai/openhuman/issues/6927)). — [GitHub issues](https://github.com/tinyhumansai/openhuman/issues?q=headless)
- Remote UI is "core remote, UI local". The deployed core "does not serve the full UI as a production web app yet". — [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md)

### Inferences
- **[inference]** Unlike Claude Code, the headless core has no interactive first-run dialogs to dismiss. It is configured by env vars and RPC, so the `claude-baseline.json` problem would disappear. The `claude-code:` provider still spawns the real `claude` CLI, though, and its onboarding and credentials state would still have to be present in the container.
- **[inference]** For a dvergr-style worker, the cleanest container shape is probably `openhuman-core call --method openhuman.inference_agent_chat` in a loop driven by an external script, or a small Rust binary on `openhuman-embed`, rather than `serve`.

### Gaps
- I could not determine exactly which features fail when `BACKEND_URL` is unreachable on a core that uses only `local-openai`, or whether startup blocks.

---

## 5. Models and auth/billing: providers, Claude subscription, Anthropic April-2026 policy, ChatGPT subscription, Google, local, cost controls

### Takeaway
OpenHuman has three routes:
- managed (TinyHumans, the default; OpenRouter-backed);
- BYOK for 26 provider slugs;
- local runtimes.

It also has two Claude subprocess providers that shell out to the `claude` CLI in print mode (`claude -p … stream-json`), plus ChatGPT/Codex OAuth for OpenAI. It never runs an interactive Claude Code session. Under Saga's April-2026 test results, `claude -p` would therefore not bill to the Max subscription. However, Anthropic's own help center now says (June 15 and Oct 7, 2026 updates) that Agent SDK, `claude -p` and third-party-app usage draws from subscription limits, and Max plans now include $100–$200/month of API credits. That directly contradicts Saga's CLAUDE.md constraint and needs re-testing. OpenHuman's docs say nothing about Anthropic's subscription policy.

### Cited Findings
- Managed default: "routing happens behind a single OpenHuman subscription". On the managed backend the pinned default model is `openrouter/deepseek/deepseek-v4-flash`. — [features/model-routing/README.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/model-routing/README.md); [agent-harness.md §Workload routes](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- BYOK slugs: `openai`, `anthropic`, `google`, `openrouter`, `orcarouter`, `groq`, `mistral`, `deepseek`, `together`, `fireworks`, `cerebras`, `xai`, `moonshot`, `gmi`, `huggingface`, `nvidia`, `zai`, `minimax`, `stepfun`, `kilocode`, `deepinfra`, `novita`, `venice`, `vercel-ai-gateway`, `sumopod`, `modelscope`, plus any OpenAI-compatible endpoint. Local: `ollama:`, `lmstudio:`, `mlx:`, `omlx:`, `local-openai:`. Per-workload fields: `chat_provider`, `reasoning_provider`, `agentic_provider`, `coding_provider`, `vision_provider`, `memory_provider`, `embeddings_provider`, `learning_provider`. — [features/model-routing/local-and-byok-models.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/model-routing/local-and-byok-models.md)
- An `anthropic` BYOK entry uses the native Messages adapter so `cache_control` markers reach the wire. Anthropic's OpenAI-compatible endpoint cannot carry them. — [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)
- Claude Code CLI provider (`claude-code:<model>`), owned by tinyagents' `ClaudeCodeProvider`:
  - Spawns `claude` with `-p --input-format stream-json --output-format stream-json --verbose --include-partial-messages`.
  - Uses `--session-id` on the first turn and `--resume` afterwards.
  - Default `--permission-mode acceptEdits` and `--disallowedTools Bash,BashOutput,KillShell,WebFetch,WebSearch,Task`.
  - Exposes OpenHuman tools to the CLI over a loopback HTTP MCP endpoint (`mcp__openhuman__*`).
  - `MAX_CONCURRENT_TURNS = 4`.
  - Auth order: `ANTHROPIC_API_KEY`, then `~/.claude/.credentials.json` "(Pro or Max subscription)".
  - Cost from `result.total_cost_usd` is "not yet wired into OpenHuman's cost tracking".
  - Sandboxed only on macOS (Seatbelt). "Linux and Windows run the CLI unconfined."
  - The CLI's internal tool calls "never reach OpenHuman as harness tool calls".
  - Sources: [developing/providers/claude-code.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/providers/claude-code.md); [B .../factory/subprocess_providers.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/provider/factory/subprocess_providers.rs)
- Claude Code provider bug history:
  - [#5648](https://github.com/tinyhumansai/openhuman/issues/5648) "driver resumes a session it never created" (Aug 21)
  - [#5877](https://github.com/tinyhumansai/openhuman/issues/5877) "trailing user message injected multiple times into shared session (parallel services / loop iterations)" (Aug 31)
  - [#5790](https://github.com/tinyhumansai/openhuman/issues/5790) wrong login command (`claude login` vs `claude auth login`)
  - [#6043](https://github.com/tinyhumansai/openhuman/issues/6043) "make the Claude Code provider usable in the shipped app" (Sep 6)
  - [#7223](https://github.com/tinyhumansai/openhuman/issues/7223) "recover stale sessions" (Oct 9)
- Claude Agent SDK provider (`claude_agent_sdk[:model]`): a subprocess `claude` binary with default model `claude-sonnet-4-6` and an optional `max_budget_usd`. — [B crates/openhuman-core/src/config/schema/claude_agent_sdk.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/config/schema/claude_agent_sdk.rs). It was requested in [#2479](https://github.com/tinyhumansai/openhuman/issues/2479) (May 22, 2026), which cited Anthropic's announced Agent SDK credit and proposed relying on `claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN`.
- OpenAI ChatGPT/Codex OAuth: there are RPCs to start/complete an OpenAI OAuth flow, to import Codex CLI credentials (`inference_openai_oauth_import_codex_cli`), and to report status and disconnect. With OAuth, requests route to `OPENAI_CODEX_BACKEND_BASE_URL` with the account id. — [B .../inference/schemas/oauth_handlers.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/schemas/oauth_handlers.rs); [B .../inference/provider/openai_codex.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/provider/openai_codex.rs); [#2265](https://github.com/tinyhumansai/openhuman/issues/2265) "oauth (chatgpt-style) for openai llm provider"; [#3801](https://github.com/tinyhumansai/openhuman/issues/3801) token_expired 401 floods; [#6022](https://github.com/tinyhumansai/openhuman/issues/6022) session-expired on refresh failure
- Anthropic's position (primary sources):
  - Help-center update of June 15, 2026: "We've paused the previously-announced changes to Claude Agent SDK usage… Claude Agent SDK, `claude -p`, and third-party app usage still draw from your subscription limits."
  - Update of Oct 7, 2026: "Claude Max and Team plans now include monthly API credits… which cover the Claude Agent SDK, `claude -p`, the Claude API, and Claude Managed Agents", and "You can still use the Claude Agent SDK, `claude -p`, and third-party apps with your subscription limits."
  - Caveat: this was retrieved through a summarizing fetch tool, which declined to reproduce the page verbatim.
  - Source: [Claude Help Center: Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- Anthropic platform docs: Max 5x gets $100/mo, Max 20x $200/mo, Team up to $500 pooled. Credits cover Claude API, Managed Agents, Claude Agent SDK and playground, but not Claude Code. They require linking a Console org and creating an API key, and expire monthly. "Credits don't change your usage limits in Claude or Claude Code." — [API credits for Max and Team plans](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers)
- Secondary coverage: Anthropic paused a May 13 proposal to move SDK/`claude -p` usage onto separate credits after developer pushback. — [letsdatascience](https://letsdatascience.com/news/anthropic-pauses-claude-agent-sdk-billing-overhaul-1cff2071); [agenticwire](https://www.agenticwire.news/article/claude-agent-sdk-200-credit-dev-guide)
- OpenHuman docs on Anthropic's April-2026 first-party-only subscription policy: a search of the docs, README and AGENTS.md for "third-party harness", "first-party" and "subscription ban" found no discussion. The provider doc simply states that `~/.claude/.credentials.json` from a Pro/Max login works. — [providers/claude-code.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/providers/claude-code.md)
- Google: there is a `google` BYOK slug, and `web_answer` uses "Gemini with Google Search by default". I found no Google-subscription OAuth route. — [local-and-byok-models.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/model-routing/local-and-byok-models.md); [developing/mcp-server.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/mcp-server.md)
- Cost controls:
  - per-turn budgets (max tool iterations, max payload, max USD)
  - a budget stop hook
  - `config.autonomy.max_actions_per_hour` (`OPENHUMAN_MAX_ACTIONS_PER_HOUR`)
  - goal token budgets
  - live `turn_cost` events
  - a per-tier rate table fallback when the provider reports no charge
  - Privacy Mode `LocalOnly`, which refuses to construct any external provider
  - Sources: [agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md); [access_gates.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/provider/factory/access_gates.rs)
- Vendor benchmark (10 SWE-bench tasks, model `deepseek/deepseek-v4.1-flash` for all harnesses): OpenHuman resolved 7/10. Claude Code, OpenCode, Hermes and the DeepSeek harness resolved 10/10, OpenClaw 9/10 and Codex 7/10. The README's headline numbers are "per solved task". — [swe-x86-1 summary](https://github.com/tinyhumansai/openhuman-benchmarks/blob/main/results/swe-x86-1/summary.md); [README](https://github.com/tinyhumansai/openhuman/blob/main/README.md)

### Inferences
- **[inference]** Saga's CLAUDE.md says `claude -p` requires `ANTHROPIC_API_KEY`, and that subscriptions only cover first-party tools. Anthropic's current help-center text contradicts that for `claude -p`/Agent SDK and says third-party apps draw from subscription limits. Before any harness decision, the operator should re-run the April test: `claude -p` with a subscription `.credentials.json`, no API key, then check `/status` and the usage dashboard. If it now bills to the subscription, both OpenHuman's `claude-code:` provider and a custom Odin harness on the Agent SDK become viable on Max billing. Separately, the Max 20x $200/mo API credit could fund an `anthropic:` BYOK route directly (per-token, capped by that credit).
- **[inference]** Even if billing works, routing Odin through OpenHuman's `claude-code:` provider stacks two harnesses: OpenHuman's loop around a `claude -p` loop. The inner CLI's tool calls are invisible to OpenHuman's hooks and journal, and its Bash/WebFetch/Task are disabled by default.

### Gaps
- I did not test whether OpenHuman's `claude-code:` route bills to subscription; that is not determinable from documentation.
- Exact date and wording of Anthropic's "April 4, 2026" policy as it applies to `claude -p` OAuth in third-party wrappers: not re-verified here.

---

## 6. Security and sandboxing: permission model, sandbox, secrets, network controls

### Takeaway
The security design is extensive but permissive by default:
- The autonomy and approval policy is OFF by default, on the theory that agents run inside an outer container or VM. Only an always-forbidden floor (`~/.ssh`, `~/.gnupg`, `~/.aws`, system roots, `..`) and forced browser approvals are always on.
- Sandboxing is per-session: none, an OS jail (Landlock/Seatbelt), or Docker with no network.
- Secrets are in the OS keyring or a ChaCha20-Poly1305 encrypted file.
- Agent traces with content are shared to the vendor's Langfuse by default (an open issue).

### Cited Findings
- "The autonomy policy is off by default… Agents are expected to run inside a container, a platform jail or a Docker sandbox that already provides isolation." When it is on there are three tiers: `readonly`, `supervised` (default) and `full`. Commands are classified Read/Write/Network/Install/Destructive and classification fails closed (pipes take the highest class). Choices are Approve / Always allow / Deny, with a 10-minute TTL that denies. Pending approvals are stored in SQLite (`approval/approval.db`). — [features/approval-gate.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/approval-gate.md); [developing/architecture/security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/security.md)
- The always-on floor `is_always_forbidden` blocks `~/.ssh`, `~/.gnupg`, `~/.aws`, system roots, `..` traversal and null bytes. — [architecture/security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/security.md)
- Sandbox backends:
  - `None`, `Local` (tinybox-jail: Landlock on Linux, Seatbelt on macOS) and `Docker` ("no network, dropped capabilities and a read-only root filesystem by default", `action_dir` mounted at `/workspace`).
  - "The core process itself always runs on the host; only the spawned command is confined."
  - `OPENHUMAN_SANDBOX=off` disables it when outer isolation exists.
  - Sources: [B crates/openhuman-core/src/sandbox/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/sandbox/README.md); [features/privacy-and-security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/privacy-and-security.md)
- Secrets: OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service) or the `encrypted_file` backend (ChaCha20-Poly1305, `enc2:` prefix). In containers the master key comes from env or a file mount, and group/world-writable key files are rejected. `redact()` is used for logs. The event journal passes through a `RedactingSink`. — [architecture/security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/security.md); [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md)
- Network and RPC exposure:
  - Bearer token on `/rpc` and `/v1/*`.
  - `PairingGuard` requires a pairing token before binding the RPC server to a public address.
  - CORS allowlist.
  - Only `/health`, `/` and `/schema` are unauthenticated.
  - An egress-disclosure event is emitted for each external inference provider.
  - Skills are installed over HTTPS only with SSRF guards.
  - A prompt-injection guardrail runs on chat input (`security::prompt_injection::enforce_prompt_input`).
  - Sources: [features/cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md); [architecture/security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/security.md); [B web_chat/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/README.md)
- Integration OAuth tokens "stay with the backend, not your laptop". The backend brokers each integration request. — [features/privacy-and-security.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/privacy-and-security.md). Contradicting this, a competitor review (Vellum, Aug 2026) says "Integrations like Gmail and Notion store credentials in the local config, which the main model can access" and claims there is no Telegram integration. Both claims conflict with the current docs and may describe an older version. — [Vellum](https://www.vellum.ai/blog/best-openhuman-alternatives)
- A Chinese review lists "no security sandbox" as a risk. — [ai-indeed](https://www.ai-indeed.com/encyclopedia/21118.html). This conflicts with the documented sandbox backends, but is partly consistent with policy being off by default.
- Open hardening issues: [#7248](https://github.com/tinyhumansai/openhuman/issues/7248) "Carve the account dir's secrets and privilege files out of the agent's path surface" and [#7246](https://github.com/tinyhumansai/openhuman/issues/7246) "Account-dir carve-out misses the keyring key, auth profiles and the Claude Code full-access toggle" (both Oct 9, open). — [GitHub issues](https://github.com/tinyhumansai/openhuman/issues/7248)
- Telemetry defaults (agent traces with prompt, reply and tool content shared to the backend Langfuse; Sentry on) are covered in §2 and issue [#7016](https://github.com/tinyhumansai/openhuman/issues/7016).

### Inferences
- **[inference]** OpenHuman has nothing like Heimdall, a deterministic out-of-process launch gate. Its sandbox confines child commands, but the core itself runs unconfined, and policy defaults assume outer isolation. Saga's model of a container plus Heimdall is complementary rather than replaced.
- **[inference]** For a homelab, `share_usage_data` and `capture_content` must be explicitly set to false, and `analytics_enabled` too if desired. Otherwise planner prompts and tool I/O would go to TinyHumans' Langfuse.

### Gaps
- I did not verify whether trace sharing requires a signed-in session (and is therefore inert for an account-less core).

---

## 7. Fit for Saga: (a) planner/Odin, (b) worker/dvergr, (c) patterns worth adopting

### Takeaway
- (a) For Odin, OpenHuman solves the event-injection problem cleanly (RPC with steer/followup/collect queue lanes, native Telegram, MCP or in-process tools for file inboxes). But it cannot host an interactive Claude Code session. Its Claude routes are `claude -p` subprocesses or per-token APIs, so the billing outcome depends on re-verifying Anthropic's current terms. It would also bring heavy backend coupling and beta churn.
- (b) For dvergar, it is a plausible harness-agnostic worker for non-Claude models: one-shot `call` mode, a Docker image, and `stop`/`afterAgentResponse` command hooks that can publish MQTT. It has no SessionStart hook and no built-in loop mode, and its own benchmark resolve rate trails Claude Code.
- (c) Its strongest value for Saga is as a pattern source.

### Cited Findings (evidence base for the assessment; details in §§2–6)
- Event injection without tmux: `channel.web_chat` with `queue_mode` = interrupt/steer/followup/collect/parallel ([B web_chat/schemas.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/schemas.rs)). One-shot `inference.agent_chat` ([B inference/host_runtime/schemas.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/inference/host_runtime/schemas.rs)). Embedding with `Agent::turn` or `Agent::stream` ([turns-sessions.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/turns-sessions.md)). Socket.IO events stream progress ([agent-harness.md §Web channel events](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)).
- There is no MQTT channel and no generic inbound webhook trigger. Workflow `webhook` is "Not implemented" ([B flows/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/flows/README.md)). Composio triggers come only via the hosted backend ([triggers.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/triggers.md)).
- Telegram is a native channel with an own-BotFather-token option, inline approvals and proactive delivery ([features/channels.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/channels.md)). In the embed library, channel-bound agents get "a read-only cap" ([embed/concepts/channels.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/embed/concepts/channels.md)). In the app/core, external-channel turns park acting calls for approval when the autonomy policy is on ([approval-gate.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/approval-gate.md)).
- Billing routes for Claude: see §5.
- Worker hooks: `stop` and `afterAgentResponse` run command scripts with the event on stdin (non-blocking for observational events). `beforeSubmitPrompt` honors `additional_context`. `sessionStart` and `preCompact` are not fired ([developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md)).
- The "500 agents on a $10 VPS" figure was measured with mock inference: "Every scenario also replaces network inference with a mock provider at fixed latency". The Linux cgroup run used a loopback chat-completions mock (3.355 MiB marginal RSS per agent at 500 agents). "Thousands of agents on one box is a goal, not a measured result." — [developing/performance.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/performance.md)

### (a) Could Odin run on it?

**Technically yes, as a different kind of Odin.**

Gains versus Claude Code + Telegram channel plugin + ratatoskr:
- Ratatoskr could call `channel.web_chat` with `queue_mode: "followup"` (deliver after the current turn), `"steer"` (inject into the running turn) or `"collect"`, or `inference.agent_chat` for discrete jobs. That replaces `tmux send-keys` with acknowledged, typed delivery. Progress, cost and completion come back as Socket.IO events or from the journal RPCs (`agent_run_events`, `agent_run_status`).
- Saga's file inboxes and outboxes (Mimir `pending/`/`verdicts/`, Heimdall request YAML) could become first-class tools:
  - via a small Python MCP server, which OpenHuman supervises (stdio/HTTP, health probes);
  - or via in-process `Box<dyn Tool>` if Odin were a Rust binary on `openhuman-embed`.
- Other gains:
  - Native Telegram with inline approvals.
  - Durable async sub-agents (Mimir could be a `critic`-style agent on a different model via per-agent model routing).
  - Spawn depth limits, a no-progress breaker, per-turn USD budgets and an event journal with replay.
  - Strict control over context compaction and prompt caching.

Losses and costs:
- No interactive Claude Code session, which means no first-party Telegram channel plugin and no Claude Code tool suite inside the planner.
- The `claude-code:` provider wraps `claude -p` with Bash, WebFetch and Task disabled by default. Its inner tool calls are invisible to hooks and the journal, and it is capped at 4 concurrent turns.
- Memory requires TinyHumans or CortexDB. With neither it is off, so Odin's journal/principles would have to stay in Saga's own files.
- BYOK cloud routes on a `serve` host require a TinyHumans session or API key. Library hosts, `local-openai`, and the `claude-code`/`claude_agent_sdk` providers are exempt.
- Telemetry defaults must be turned off.
- GPL-3.0 applies (fine for a homelab; it matters only if Saga distributes a linked binary).
- Beta churn: interfaces and features have been removed repeatedly (§8).

Billing consequences:
- Opus via `anthropic:` BYOK is per-token. It could be absorbed by the Max 20x $200/mo API credit, which is far below a heavy planner's usage at Opus rates **[inference]**.
- Opus via `claude-code:` or `claude_agent_sdk` is `claude -p`. Per Saga's April test that means API billing. Per Anthropic's June 15 and Oct 7 help-center text it draws from subscription limits. This conflict must be resolved by re-testing before relying on it.

**Net [inference]:** Adopting OpenHuman wholesale as Odin's harness is not recommended now. For the "extract Odin into a standalone custom harness" track, the embed library (`openhuman-embed`) is a credible base: in-process, Rust, typed tools, queue lanes and journals. Billing, the GPL, backend coupling and API stability are the gating issues, not capability.

### (b) Could a dvergr run on it?

**Partially, best as a harness-agnostic worker for non-Anthropic models** (DeepSeek, GPT via ChatGPT OAuth or API, local `local-openai`).

What fits:
- Container-friendly startup: GHCR image, non-root, `/health`. There are no interactive first-run dialogs, though env/RPC configuration is needed.
- A one-shot `openhuman-core call --method openhuman.inference_agent_chat --params '{"message":…,"cwd":"/workspace"}'` returns `hit_cap` and `checkpoint`.
- A file `stop` hook (or `afterAgentResponse`) can run a script that `mosquitto_pub`s status/journal JSON after every turn. `postToolUse`/`afterFileEdit` give per-tool events.
- A `stop` hook can also return `followup_message` with `loop_limit: 0` to emulate `/ralph-loop`'s re-prompting. Alternatively, an external bash loop can re-invoke `agent_chat` with the checkpoint.
- Guidance-file reading can be done in `beforeSubmitPrompt` via `additional_context`, or in the `stop` hook's `followup_message`.

What is missing or risky:
- No `sessionStart` hook (defined but not fired), no `preCompact`, and no built-in completion-promise or loop mode.
- Its own benchmark resolves fewer tasks: 7/10 vs Claude Code's 10/10 on the same model.
- Heavy product surface for a worker: Composio, a wallet, voice, etc. These are compiled in unless you do a custom build with features disabled.
- amd64-only image.
- The "500 agents" density claim is mock-measured.

For Claude-model workers, the subscription-billing question is identical to (a). Saga's current `/ralph-loop` inside interactive Claude Code remains the only path known (from Saga's own tests) to bill to subscription.

### (c) Patterns worth adopting even if Saga stays on Claude Code
1. **Queue lanes for injected input** (`interrupt` / `steer` / `followup` / `collect` / `parallel`): [B crates/openhuman-core/src/web_chat/types.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/types.rs) and [web_chat/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/web_chat/README.md). Ratatoskr could classify each MQTT event into a lane: steer = urgent operator override, followup = dvergr status after the current turn, collect = batch low-priority telemetry into one digest. It would deliver collect-lane items in one send-keys burst only when Odin's pane is idle, instead of injecting each message as it arrives.
2. **Trigger triage tier (drop / acknowledge / react / escalate) on a cheap model** before waking the expensive planner: [features/integrations/triggers.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/triggers.md); code `crates/openhuman-core/src/agent/triage/`. Saga could do this in ratatoskr with deterministic rules or a Haiku-class classifier, so routine dvergr heartbeats never cost Opus tokens.
3. **No-progress circuit breaker with argument fingerprinting and a Continue → Nudge → Halt ladder**: `RepeatedToolFailureMiddleware` in `crates/openhuman-core/src/agent/tinyagents/middleware.rs` ([agent-harness.md §Reliability](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). This maps directly onto Odin's dvergr stuck-detection: fingerprint repeated failing test/command signatures from journals. Nudge by writing guidance, and halt by cancelling the loop with a root-cause summary.
4. **Typed handback statuses `Completed` / `AwaitingUser{question, options}` / `Incomplete{reason}`**, never silent finishes: `crates/openhuman-core/src/agent/subagent_host/` ([agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). Adopt these as the dvergr completion and journal schema, and the Mimir verdict schema, in `mqtt/TOPIC-SCHEMA.md`.
5. **Grounded close**: a tools-disabled wrap-up, then an independent checker call that rejects narration-only replies or replies contradicting the tool record, then a deterministic fallback: `session_host/driver/grounded_close.rs` ([agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). This is a model for how Mimir should check Odin's status reports to the operator against the actual journal evidence.
6. **Artifact offload with pointer plus abstract**: `[artifact] kind=output path=… bytes=…` plus `[abstract]`, under `crates/openhuman-core/src/agent/harness/artifact_offload/` ([agent-harness.md §Filesystem offload](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). Dvergr summaries and Bragi inputs could be handed to Odin as paths plus abstracts instead of pasted payloads.
7. **Durable completion queue with leases and redelivery after restart**: `.openhuman/background_completions.jsonl` via `CompletionRouter`, deduped by task id, with tombstones ([agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). Ratatoskr's MQTT→Odin delivery could use a lease file so a message is not lost if Odin's pane restarts mid-delivery.
8. **Spawn-tier hierarchy plus hard depth cap** (chat → reasoning → worker; worker spawns nothing; `MAX_SPAWN_DEPTH = 3`, validated at load time): `crates/openhuman-core/src/agent/registry/agents/loader.rs`. Heimdall could enforce a similar rule, e.g. dvergar may never request launches, and Odin's launch requests carry a depth or lineage field.
9. **Append-only event journal with a redaction sink, restart-stable ids `{run_id}-evt-{offset}` and late-attach replay RPCs** (`agent_run_events`): `crates/openhuman-core/src/agent/tinyagents/journal.rs`. Saga's MQTT journal could gain offsets and redaction-before-persist so Grafana and Odin can replay from an offset.
10. **Strictest-verdict hook aggregation with `failClosed`, `loop_limit` and a `hooks test` dry-run command**: [developing/hooks.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/hooks.md). These apply to Saga's dvergr hooks: make the guard hooks fail closed, and add a dry-run harness for hook scripts.
11. **Turn-origin approval matrix** (cron/CLI/sub-agent allowed; external channel parks; unlabelled denied; 10-minute TTL denies): [features/approval-gate.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/approval-gate.md). This is a clean way to express Heimdall policy by request origin: Odin-initiated vs Telegram-originated vs automated.
12. **Layered tool rules with context conditions** (`deny shell when channel = telegram`; rule id and reason returned on refusal): `crates/openhuman-core/src/tools/rules/`. The Claude Code analogue is permission rules per settings layer. The pattern of returning the rule id and reason to the model is worth copying in Heimdall rejections.
13. **Frozen-prefix discipline** (system prompt built once; tools treated as part of the cache prefix; history append-only; per-turn context appended, not spliced) plus prefix-divergence audit scripts: [agent-harness.md §cacheable prefix](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md). This is relevant to keeping Odin's long-lived session cheap, e.g. avoid rewriting CLAUDE.md mid-session and inject MQTT context as messages.
14. **Content-aware tool-output compression with a lossless retrieval handle** (TokenJuice CCR `⟦tj:<hash>⟧` + `juice_retrieve`): [features/token-compression.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/token-compression.md). Ratatoskr could compress large dvergr journals into a table, store the original, and give Odin a handle or path.
15. **Iteration-budget awareness** (tell the model remaining calls at 50% and 80%; `hit_cap` plus a resumable `checkpoint`): `session_host/builder/iteration_cap.rs`. Dvergar could get "iterations remaining" in guidance, and capped runs could emit a checkpoint for the next launch.
16. **Classified failure taxonomy** (`ClassifiedFailure {class, category, cause_plain, next_action, recoverable}`): `vendor/tinyagents/vendor/tinytools` ([agent-harness.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/architecture/agent-harness.md)). This gives dvergr error reports and Heimdall results a shared vocabulary so Odin knows whether to retry, escalate or ask the operator.

### Inferences
- **[inference]** For the operator's option (2), making infrastructure harness-agnostic, OpenHuman's file-hook contract shows that a Cursor/Claude-compatible `hooks.json` envelope works across harnesses. If Saga defines its dvergr status/journal publisher as a stdin-JSON hook script, the same script could run under Claude Code, Cursor or OpenHuman, with event-name aliasing as OpenHuman does.

### Gaps
- I did not test OpenHuman end-to-end in a container. All fit judgments rest on documentation and source reading.
- I could not determine stop-hook `followup_message` behavior under long (hundreds of iterations) unattended loops.

---

## 8. Risks: bus factor, stability, breaking changes, licensing, policy, lock-in

### Takeaway
The risks are high across the board:
- About 77% of commits come from one person.
- The project is self-declared early beta with very high churn, and major subsystems have been removed or replaced within months.
- It is GPL-3.0.
- Its Claude subscription routes depend on Anthropic's shifting `claude -p`/SDK terms.
- Many features are coupled to the vendor's hosted backend and paid credit plans.

### Cited Findings
- Bus factor: `senamakel` has 30,701 of about 39.7k commits; the next contributor has 2,214. — [GitHub contributors](https://github.com/tinyhumansai/openhuman/graphs/contributors)
- Churn: 7,909 commits in the most recent week, and v0.49 → v0.64 between Mar 31 and Oct 9, 2026. — [participation API](https://api.github.com/repos/tinyhumansai/openhuman/stats/participation); [Releases](https://github.com/tinyhumansai/openhuman/releases)
- Removed or replaced features, per the docs:
  - the live Google Meet agent;
  - the embedded Chromium (CEF) runtime;
  - in-app model downloads and runtime management;
  - the skills JavaScript sandbox;
  - the memory tree, graph view, people list and `MEMORY.md`;
  - five memory engines;
  - the Matrix channel;
  - the REPL/Rhai scripting runtime;
  - the TUI moved to a separate executable.
  - Sources: [overview/roadmap.md §Recently removed](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/overview/roadmap.md); [features/memory.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/memory.md); [features/channels.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/channels.md); [features/orchestration.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/orchestration.md); [crates/openhuman-cli/README.md](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-cli/README.md)
- The early-beta exit checklist ([#6047](https://github.com/tinyhumansai/openhuman/issues/6047)) is still open. The memory end-to-end smoke test is "not passing yet", and clean-install sign-in on all platforms is open. Two surfaces are "built but not working yet". — [overview/roadmap.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/overview/roadmap.md)
- Ongoing large refactors: "[core-shrink]" issues moving channels, backend and inference plumbing into vendored crates ([#7412](https://github.com/tinyhumansai/openhuman/issues/7412), [#7405](https://github.com/tinyhumansai/openhuman/issues/7405), [#7393](https://github.com/tinyhumansai/openhuman/issues/7393)), and a provider-registry cutover ([#7741](https://github.com/tinyhumansai/openhuman/issues/7741), closed Oct 13). — [GitHub issues](https://github.com/tinyhumansai/openhuman/issues)
- Third-party view: "OpenHuman is at v0.53 with frequent breaking changes… It is not stable production software." Note this comes from a competitor. — [Vellum, Aug 7, 2026](https://www.vellum.ai/blog/best-openhuman-alternatives)
- Licensing: GPL-3.0 for the repo and all vendored tiny* crates. — [B LICENSE](https://github.com/tinyhumansai/openhuman/blob/main/LICENSE); [tinyagents](https://github.com/tinyhumansai/tinyagents)
- Backend coupling and lock-in:
  - Memory requires TinyHumans hosted CortexDB or a CortexDB key.
  - Composio integrations and triggers go through the TinyHumans backend.
  - Managed search runs through the backend.
  - BYOK cloud providers on server hosts require a TinyHumans session or API key.
  - `BACKEND_URL` is listed as required for deployments.
  - Commercial plans are $20/$200/mo credit packs.
  - Sources: [developing/engines.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/developing/engines.md); [triggers.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/integrations/triggers.md); [cloud-deploy.md](https://github.com/tinyhumansai/openhuman/blob/main/docs/gitbooks/en/features/cloud-deploy.md); [tinyhumans.ai/pricing](https://tinyhumans.ai/pricing)
- Default data sharing: traces including prompt, reply and tool I/O go to the backend Langfuse by default (open issue [#7016](https://github.com/tinyhumansai/openhuman/issues/7016); [observability.rs](https://github.com/tinyhumansai/openhuman/blob/main/crates/openhuman-core/src/config/schema/observability.rs)).
- Policy risk: Anthropic's SDK/`claude -p` billing terms changed three times in 2026 (May 13 proposal, June 15 pause, Oct 7 API credits), and OpenHuman's Claude routes depend on them. — [Claude Help Center](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan); [letsdatascience](https://letsdatascience.com/news/anthropic-pauses-claude-agent-sdk-billing-overhaul-1cff2071)
- Benchmark credibility: vendor-run, 10 tasks, one model (deepseek-v4.1-flash). OpenHuman had the lowest resolve rate among the top-line comparison except Codex (7/10). The benchmarks repo has 1 star and was created 2026-10-02. — [swe-x86-1 summary](https://github.com/tinyhumansai/openhuman-benchmarks/blob/main/results/swe-x86-1/summary.md); [openhuman-benchmarks](https://github.com/tinyhumansai/openhuman-benchmarks)
- Third-party coverage is thin and mostly promotional or translated. I found no Hacker News or Reddit discussion threads. — [search results incl. stork.ai](https://www.stork.ai/blog/ko/openhumans-gambit-a-private-superintelligence-for-everyone); [hunted.space](https://www.hunted.space/product/openhuman)

### Inferences
- **[inference]** For Saga, the lowest-risk use is to read and copy patterns (§7c), which carries no runtime dependency. The medium-risk use is a pinned `openhuman-embed` dependency for a custom Odin harness experiment, with telemetry disabled and no TinyHumans backend. The highest-risk use is adopting the full app/server as the planner runtime.
- **[inference]** GPL-3.0 does not constrain a private homelab deployment. It would constrain publishing Saga as a non-GPL project that links `openhuman-embed`.

### Gaps
- Funding or runway of Tiny Humans: not found, which is a material input to bus-factor risk.
- I found no evidence of production deployments by third parties.
- Community sentiment beyond vendor channels (Reddit, HN): no threads found.
