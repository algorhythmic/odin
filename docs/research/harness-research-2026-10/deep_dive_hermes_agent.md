# Deep dive: Hermes Agent (NousResearch/hermes-agent), as of 2026-10-13

Method note: the repo was shallow-cloned at commit `560b250` (committed 2026-10-13 22:52 -0700) and read as data only. Nothing from the clone was executed. File citations below point at `https://github.com/NousResearch/hermes-agent/blob/main/<path>`. The docs site (https://hermes-agent.nousresearch.com/docs/) is built from `website/docs/` in the same repo, so those files are the primary docs source. Repo metrics come from the GitHub REST API on 2026-10-14 UTC. "Inference" marks my reasoning. Everything else is a documented or measured fact with a source.

## 1. Identity: what it is, who builds it, dates, license, runtime, activity, maturity, community, stated goals

### Takeaway
Hermes Agent is Nous Research's MIT-licensed Python agent harness: a persistent, self-improving personal agent with a messaging gateway, cron, skills and memory. It started as a repo in July 2025, had its first tagged release in March 2026 and shipped v0.22.0 on 2026-10-13. By raw numbers (253k stars, ~52k commits, ~4.5k contributors) it is one of the most active open-source agent projects. Churn is extreme, and a stable SemVer channel has existed only since early October 2026.

### Cited Findings
- README self-description: "The self-improving AI agent built by Nous Research. It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions." — [README.md](https://github.com/NousResearch/hermes-agent/blob/main/README.md)
- License: MIT, "Copyright (c) 2025 Nous Research". — [LICENSE](https://github.com/NousResearch/hermes-agent/blob/main/LICENSE)
- Language and runtime: Python. `pyproject.toml` declares `requires-python = ">=3.11,<3.15"` with a comment that "we *only* support 3.14". Every direct dependency is exact-pinned, a policy "tightened on 2026-05-12 in response to the Mini Shai-Hulud worm hitting mistralai 2.4.6 on PyPI". The TUI and desktop parts are Node/Electron. — [pyproject.toml](https://github.com/NousResearch/hermes-agent/blob/main/pyproject.toml), [docs/developer-guide/architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md)
- GitHub repo created 2025-07-22. As of 2026-10-14: 253,560 stars, 55,005 forks, 978 watchers, last push 2026-10-14. — [GitHub API repos/NousResearch/hermes-agent](https://api.github.com/repos/NousResearch/hermes-agent)
- Activity:
  - ~52,275 commits on the default branch.
  - ~4,496 contributors, anonymous included.
  - Weekly commit counts over the last 12 weeks ranged from 1,323 to 6,149.
  - Search counts: 15,325 open issues, 33,199 open PRs, 34,826 issues total, 18,436 merged PRs.
  - Sources: [commits](https://github.com/NousResearch/hermes-agent/commits/main), [contributors API](https://api.github.com/repos/NousResearch/hermes-agent/contributors), [participation stats API](https://api.github.com/repos/NousResearch/hermes-agent/stats/participation), [issues](https://github.com/NousResearch/hermes-agent/issues), [pulls](https://github.com/NousResearch/hermes-agent/pulls)
- First tagged release: v0.2.0 (2026-03-12), described as the "First tagged release since v0.1.0 (the initial pre-public foundation). In just over two weeks, Hermes Agent went from a small internal project to a full-featured AI agent platform… 216 merged pull requests from 63 contributors". — [Release v2026.3.12](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.3.12)
- Latest release: v0.22.0 "The Threshold Release", 2026-10-13 (published 2026-10-14 03:21 UTC). The notes report "Since v0.21.0: ~24,200 commits · ~6,080 merged PRs · ~15,600 files changed · ~2,045,000 insertions · ~1,140,000 deletions · ~7,180 issues closed · ~2,520 contributors." — [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Release cadence: 39 GitHub releases between 2026-03-12 and 2026-10-13. Versions were CalVer-tagged (v2026.M.D) up to v0.21.5 (2026-09-24), then plain SemVer (v0.21.6, 2026-10-08 onward). — [Releases](https://github.com/NousResearch/hermes-agent/releases)
- Stable channel: "The committed project version is always 0.0.0." A gated "Stable Release" workflow was seeded at 0.21.5, the "last legacy CalVer release". The v0.22.0 notes say "v0.21.6 and v0.21.7 were the first through the new gate", and that source installs "now move from release to release by default instead of tracking every commit on main". — [docs/developer-guide/stable-releases.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/stable-releases.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Public launch date is reported inconsistently:
  - TNW (citing WSJ) says it was released in February. Nous says it has been "cloned more than 24 million times since February" and estimates the agent drives "about 2.5% of global token usage". — [The Next Web, 2026-10-07](https://thenextweb.com/news/nous-research-90m-1-5bn-hermes-agent-wsj)
  - One blog gives February 25, 2026. — [aibuilderclub](https://www.aibuilderclub.com/blog/hermes-nous-research-self-improving-agent)
  - Nous's own response to a plagiarism accuser said "its repository dates to July 2025". — [36Kr](https://www.36kr.com/p/3767967755371011)
- Funding: Nous Research raised $90M at a reported $1.5bn valuation. The WSJ/TNW investor list is Nvidia, Microsoft M12, Samsung, Robot Ventures, USV, Y Combinator and Menlo Ventures. The money is meant for "Hermes for Businesses". — [The Next Web, 2026-10-07](https://thenextweb.com/news/nous-research-90m-1-5bn-hermes-agent-wsj)
- Nous's stated mission (via TNW): formed in 2023 "to counter what it calls a trend toward centralized, walled-off AI". Earlier work includes Llama fine-tunes and YaRN. — [The Next Web](https://thenextweb.com/news/nous-research-90m-1-5bn-hermes-agent-wsj)
- Link to Hermes models: Nous's own Hermes 4 models (Hermes-4-70B, Hermes-4-405B) are on Nous Portal but "are **not recommended for use inside Hermes Agent**… Hermes 4 is tuned for chat and reasoning, not the rapid-fire tool-calling loop the agent relies on." — [docs/integrations/nous-portal.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/nous-portal.md)
- Link to autoreason:
  - What it is: `NousResearch/autoreason` (created 2026-03-28, 609 stars, README byline "SHL0MS | HERMES AGENT") is "Self-Refinement That Knows When to Stop". Each iteration runs incumbent A vs adversarial revision B vs synthesis AB, judged by fresh-context agents via blind Borda count, with "Do nothing" as a first-class option. — [autoreason README](https://github.com/NousResearch/autoreason)
  - How Hermes uses it: only as reference material for the optional `research-paper-writing` skill, not in the agent core. — [optional-skills/research/research-paper-writing/references/autoreason-methodology.md](https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/research/research-paper-writing/references/autoreason-methodology.md)
- Default persona file `SOUL.md`: "You are Hermes Agent, built by Nous Research. Be direct…" — [SOUL.md](https://github.com/NousResearch/hermes-agent/blob/main/SOUL.md)
- Ecosystem: the NousResearch org also publishes `hermes-official-plugins`, `hermes-example-plugins`, `Hermes-Bot-Mode` (669 stars) and many `hermes-plugin-*` repos. The in-repo plugin catalog has 604 entries. — [NousResearch org repos](https://github.com/NousResearch), [plugin-catalog/](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog)

### Inferences
- Maturity is mixed. Feature breadth and test volume are high: ~25,000 tests across ~1,250 files are claimed in [architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md). But the codebase is 7 months past first tag, and v0.22.0 alone reports roughly a 1.06M→698K line refactor. Treat it as fast-moving pre-1.0 software.
- The 33k open PRs against 18k merged suggest a very high volume of automated or agent-authored PRs. The root AGENTS.md mentions a "triage sweeper" that may auto-close PRs ([AGENTS.md](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md)). Raw contributor counts overstate the core maintainer pool.

### Gaps
- No primary Nous blog post fixing the public launch date was found. February 2026 (press) and July 2025 (repo creation) are both defensible.
- No Hacker News thread was retrievable by search. One was referenced second-hand by the eesel review.
- Whether the top contributors are Nous employees could not be determined.

## 2. Architecture: loop, tools, prompt, context, memory, skills and self-improvement, sessions, delegation, cron, gateway, observability, state

### Takeaway
A single synchronous `AIAgent` core (OpenAI-style message format, three wire modes: chat_completions, codex_responses, anthropic_messages) is reused by the CLI, the gateway, cron, the API server, ACP and batch. The design pillars are:
- a frozen, cache-stable system prompt;
- small bounded memory files plus FTS5 session search;
- skills as procedural memory, written by a background "review fork" after turns;
- a curator that ages skills out;
- a gateway that turns platform messages, webhooks, cron ticks, heartbeats and plugin injections into turns.

### Cited Findings

**Agent loop and turn lifecycle**
- `run_agent.py` is a facade. The loop lives in `agent/conversation_loop.py` and `agent/turn_*.py` (iteration prep, API call, API error, overflow, truncation, recovery).
- Turn lifecycle: build or reuse the cached system prompt → preflight compression check (>50% of context) → build API messages → inject ephemeral layers (budget warnings, context pressure) → apply Anthropic cache markers → interruptible API call → on tool_calls, execute and loop; on text, persist and return.
- Source: [docs/developer-guide/agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)
- Interrupts: the API call runs on a background thread watched for an interrupt event. On interrupt, "the API thread is abandoned… No partial response is injected into conversation history." — [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)
- Tool execution:
  - A single tool call runs inline. Multiple calls run concurrently on a ThreadPoolExecutor, except interactive tools such as `clarify`. Results are re-ordered to call order.
  - Per tool: `pre_tool_call` hook → dangerous-command check (`tools/approval.py`) → handler → `post_tool_call` hook.
  - `todo`, `memory`, `session_search` and `delegate_task` are intercepted in `agent/tool_executor.py`.
  - Source: [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)
- Budget, retries and fallback:
  - Default iteration budget is 500 (`agent.max_turns`). Subagents are capped by `delegation.max_iterations` (default 50).
  - On 429, 5xx or 401/403, Hermes walks the `fallback_providers` list, refreshing credentials first on 401/403.
  - Auxiliary tasks (vision, compression, web extraction) each have their own fallback chain.
  - Source: [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)
- Streaming and callbacks: `stream_delta_callback`, `tool_progress_callback`, `reasoning_callback`, `step_callback`, `status_callback` and others feed the CLI, gateway and ACP progress displays. — [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)

**Tools**
- Registry: `tools/registry.py`, described as "70+ registered tools across ~28 toolsets". Each tool file self-registers at import time.
- Terminal backends (7): local, Docker, SSH, Daytona, Modal, Singularity, Vercel Sandbox.
- Source: [architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md)
- The tools reference lists, among others:
  - terminal and files: `terminal`, `read_terminal`, `process_manage`, `read_file`, `write_file`, `patch`, `search_files`, `execute_code`;
  - agent state: `delegate_task`, `cronjob_manage`, `memory`, `session_search`, `skill_manage`, `skill_view`, `skills_list`, `todo_list`, `clarify`;
  - kanban: `kanban_*` (14 tools);
  - web and media: `web_search`, `web_extract`, `browser_*`, `vision_analyze`, `image_generate`, `text_to_speech`, `computer_use`.
  - Source: [docs/reference/tools-reference.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/tools-reference.md)
- v0.22.0: "about 19 rarely used tools now load only when the agent searches for them, roughly halving the desktop tool schema sent on every call." — [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)

**System-prompt assembly**
- Three ordered tiers (`agent/system_prompt.py`):
  1. stable: identity from SOUL.md, tool/model guidance, coding brief;
  2. context: caller `system_message`, project context files `.hermes.md`/`AGENTS.md`/`CLAUDE.md`/`.cursorrules`, git workspace snapshot, operator instructions, platform hints;
  3. volatile: skills index, frozen `MEMORY.md` snapshot, frozen `USER.md` snapshot, external memory-provider block, timestamp/session/model line, runtime environment hints.
- Skills-index changes ride a "one-shot note" channel on the user message so the cached prefix survives.
- Source: [docs/developer-guide/prompt-assembly.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/prompt-assembly.md)
- Design invariant: "Per-conversation prompt caching is sacred. Mutating past context, swapping toolsets, reloading memories or rebuilding the system prompt mid-conversation breaks the cached prefix… the ONE exception is context compression." — [AGENTS.md](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md)

**Context management and compaction**
- Pluggable `ContextEngine` ABC. The default `ContextCompressor` does lossy summarization; plugins can replace it (e.g. "lcm" lossless).
- Two layers:
  - agent preflight compression at 50% of context (default);
  - gateway "session hygiene" at 85%, a safety net between turns.
- Middle turns are summarized. The last N messages are kept (`compression.protect_last_n`, default 20). Tool call/result pairs are never split.
- Compression creates a child session lineage, and memory is flushed before compressing.
- Sources: [docs/developer-guide/context-compression-and-caching.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/context-compression-and-caching.md), [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md)
- Optional "micro-compaction" (off by default) folds the oldest exchange into a running summary after each turn. It breaks the prompt-cache prefix every turn. — [docs/developer-guide/micro-compaction.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/micro-compaction.md)

**Memory**
- Two files in `~/.hermes/memories/`:
  - `MEMORY.md`: agent notes, 2,200-char cap.
  - `USER.md`: user profile, 1,375-char cap.
- They are injected as a frozen snapshot at session start with a usage header ("[67% — 1,474/2,200 chars]") and `§`-delimited entries.
- The `memory` tool supports add/patch/remove only (no read). Over-limit writes return an error telling the agent to consolidate in one batch.
- Entries are scanned for injection/exfiltration patterns and invisible Unicode.
- Source: [docs/user-guide/features/memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
- Session search: all sessions live in `~/.hermes/state.db` (SQLite + FTS5). `session_search` returns raw messages and can scroll within a session. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
- Session boundaries: "Memory Needs Session Boundaries". Messaging chats are "one continuous session" that survives restarts. Users are advised to `/new` at natural boundaries so the learn→recall loop fires. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
- External memory providers (Honcho, Mem0, Hindsight, Supermemory, OpenViking, Holographic; ByteRover and RetainDB bundled) are single-select plugins. They moved to catalog plugins in v0.22.0. — [architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Memory approval gate: `memory.write_approval: true` stages writes, both foreground and background-review, for `/memory pending|approve|reject`. Approval is pinned to the exact entry text and refused if that entry has changed since staging. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)

**Skills and the self-improvement loop**
- SKILL.md format: frontmatter with `name`, `description`, `version`, `platforms`, and `metadata.hermes.{tags, category, requires_toolsets, fallback_for_toolsets, config}`, followed by sections When to Use / Procedure / Pitfalls / Verification. Support dirs are `references/`, `templates/`, `scripts/`. Loading is progressive disclosure via `skill_view`. — [docs/user-guide/features/skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
- Standard: the README says skills are "Compatible with the agentskills.io open standard". — [README.md](https://github.com/NousResearch/hermes-agent/blob/main/README.md)
- `skill_manage` actions are create/patch/delete/write_file/remove_file. An advisory linter flags `incident-log-shape`, `references-sprawl` and `oversized-body`. It warns and never blocks. — [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
- Background review mechanism:
  - After a turn, a daemon thread may fork `AIAgent`. It replays the conversation snapshot and asks whether any skill or memory should be saved, under a dispatch-side tool whitelist (skills, memory, read-only file tools).
  - The fork inherits the parent's provider and cached prompt to hit the same prefix cache.
  - Source: [agent/background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py)
- Review triggers:
  - Memory nudge: `memory.nudge_interval` defaults to 10.
  - Skill nudge: fires when tool iterations since the last skill review reach `skills.creation_nudge_interval` (default 10).
  - The review is suppressed for cron because "the fork costs ~30K tokens / event with no human-in-the-loop benefit".
  - Sources: [agent/agent_init.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/agent_init.py), [agent/turn_finalizer.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/turn_finalizer.py)
- Review prompt content (`_SKILL_REVIEW_PROMPT`, `_COMBINED_REVIEW_PROMPT`):
  - "Be ACTIVE — most sessions produce at least one skill update".
  - Preference order: patch a currently-loaded skill, then patch an existing umbrella skill, then add a support file, then create a new class-level skill.
  - Read-before-write is enforced: `skill_manage` refuses edits not preceded by a fresh `skill_view`.
  - An explicit "Do NOT capture" list: environment-dependent failures, negative claims about tools ("these harden into refusals the agent cites against itself for months"), transient errors, one-off narratives, and unresolved failures dressed up as workflows.
  - Source: [agent/background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py)
- Review cost controls: the review can run on a cheaper model (`auxiliary.background_review.provider/model`, replaying a digest instead of the full transcript), can be disabled (`enabled: false`), and can be capped (`max_input_tokens`). `/refine` triggers it manually. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
- Skill approval gate: `skills.write_approval: true` stages every `skill_manage` write in `~/.hermes/pending/skills/` (survives restarts) for `/skills pending|diff|approve|reject` from the CLI or messaging. The default is write freely. — [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
- Curator (background maintenance of agent-created skills):
  - Runs on an inactivity check (default every 7 days, after 2h idle), not on cron.
  - Deterministic pass: skills go stale at 14 days and are archived at 30.
  - Optional LLM consolidation pass into "umbrella" skills, off by default.
  - Never auto-deletes. Pinned skills and skills referenced by cron jobs are exempt.
  - Pre-run tar.gz snapshots, plus an append-only JSONL ledger (`~/.hermes/skills/.curator_ledger.jsonl`) recording actor (curator/agent/user), action, evidence, and before/after sha256 manifests with content-addressed blobs. `hermes curator rollback <entry-id>` undoes a single mutation.
  - Source: [docs/user-guide/features/curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md)
- Provenance: only skills created by the background review fork are marked agent-created and curator-managed. Foreground `skill_manage(create)` and `/learn` skills are `created_by: learn` and "considered user-directed". — [curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md)

**Sessions, persistence, resume**
- SQLite + FTS5 with lineage across compressions. Sessions resume via `/resume` or `hermes chat --resume`.
- Loop, heartbeat and goal state persist in `SessionDB.state_meta` and follow compression rotations.
- v0.22.0 enables `sessions.auto_prune` by default, deleting ended sessions inactive for 90 days.
- Sources: [agent-loop.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md), [docs/user-guide/features/heartbeat.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/heartbeat.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)

**Delegation and sub-agents**
- `delegate_task` spawns child `AIAgent`s with isolated context. Only the child's summary returns to the parent.
- Concurrency and depth: up to 10 concurrent children by default. Delegation is flat by default (`max_spawn_depth: 1`); `role="orchestrator"` children can nest when depth is raised.
- Top-level delegations run in the background and post their completion back as a new message.
- Results can be checked against a JSON-Schema `output_schema`, with one bounded correction turn.
- Children can use a different (cheaper) model.
- Source: [docs/user-guide/features/delegation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md)
- `/review` spawns a full-privilege background reviewer subagent over the last 10 messages. Its model can be pinned via `auxiliary.review` (e.g. a different provider or model). The review re-enters the session as a completion. — [delegation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md)
- Kanban board:
  - A durable SQLite board (`~/.hermes/kanban.db`) shared across profiles. Agents drive it via `kanban_*` tools.
  - The dispatcher spawns each worker as an OS process with `hermes -p <assignee> chat -q <prompt>` and `HERMES_KANBAN_*` env vars.
  - Each run must end in exactly one of `kanban_complete` / `kanban_request_review` / `kanban_block`.
  - Failure handling: stale-claim TTL (15 min, extended for live PIDs), crash detection, `max_runtime_seconds`, a consecutive-failure breaker, and stranded-task diagnostics.
  - Sources: [docs/user-guide/features/kanban.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md), [docs/user-guide/features/kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md)

**Scheduling and cron**
- Execution model: cron jobs are agent tasks stored in `~/.hermes/cron/jobs.json` and ticked every 60s by the gateway. Each due job gets a fresh `AIAgent` session, optionally with attached skills, and delivers its result to a platform target.
- Job variants:
  - `no_agent` script-only jobs;
  - pre-check scripts that emit `{"wakeAgent": false}` to skip the LLM;
  - `context_from` chaining;
  - event-triggered jobs from webhook routes.
- Controls: cron sessions cannot manage cron unless `cron.allow_agent_scheduling: true`. Model pins are user-owned. Under systemd, jobs run in transient scopes so a gateway restart doesn't kill them.
- Source: [docs/user-guide/features/cron.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md)
- In-session recurrence:
  - `/loop` re-runs a prompt on a fixed or self-paced cadence (backoff 1→15 min when output is unchanged), with a `max_ticks` default of 100. — [docs/user-guide/features/loops.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/loops.md)
  - `/heartbeat` injects one recurring prompt only while idle; missed ticks coalesce. — [heartbeat.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/heartbeat.md)
  - `/goal` is a judge-driven continuation loop ("Our take on the Ralph loop"), inspired by Codex CLI's `/goal`. It supports completion contracts and deterministic shell "quality gates" that run before the LLM judge. — [docs/user-guide/features/goals.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md)

**Gateway (how messages and external events become turns)**
- Flow: platform event → `Adapter.on_message()` → `MessageEvent` → `GatewayRunner._handle_message()` → authorize → resolve session key → `AIAgent` with history → deliver.
- Platforms: 25+ adapters, built-in or bundled plugins, including Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email, SMS, ntfy, Home Assistant, webhook, API server and A2A.
- v0.22.0 makes one multiplexed gateway per machine serving all profiles the default.
- Sources: [architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Busy sessions: `display.busy_input_mode` is `interrupt` (default: redirects the active turn at the next tool-result boundary), `queue` (runs as the next turn) or `steer` (injected after the next tool call). — [docs/user-guide/messaging/index.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md)
- Webhook adapter:
  - HTTP server (default port 8644) with HMAC-validated routes.
  - Route options: event filters, payload `filters`, `script` transforms, prompt templates, `skills`, per-route `toolsets`, `deliver` targets, `deliver_only` (no LLM), `cron_job` (fire an existing job), `coalesce` debouncing, and `mirror_to_session`.
  - By default each event runs in its own fresh session.
  - Source: [docs/user-guide/messaging/webhooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/webhooks.md)
- API server: OpenAI-compatible `/v1/chat/completions` and `/v1/responses`, a Runs API with SSE events, stop and approval endpoints, and a Sessions API.
  - `POST /api/sessions/{id}/chat` runs one synchronous turn in an existing session.
  - "Session turn leases serialize concurrent writers."
  - Source: [docs/user-guide/features/api-server.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/api-server.md)
- Plugin injection: `ctx.inject_message(content, role="user", session_key=… | origin=…)` feeds text into an existing gateway session or a new chat session. It uses the busy-session queue, rechecks authorization, cannot invoke slash commands or approvals, and is disabled per plugin until `allow_gateway_injection: true`. — [docs/user-guide/features/plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
- `hermes send --to telegram[:chat_id[:thread_id]] "text"` sends one-shot messages to bot-token platforms without a running gateway. — [docs/reference/cli-commands.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md)

**Observability and state**
- Observer hooks: plugins carry `telemetry_schema_version="hermes.observer.v1"` and are meant for Langfuse, OpenTelemetry-style collectors and NeMo Relay. — [docs/developer-guide/observer-hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/observer-hooks.md)
- Gateway monitoring exports content-free OTLP/HTTP metrics, traces and logs: gateway state, platform health, cron heartbeat and execution lifecycle. — [docs/developer-guide/gateway-monitoring.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/gateway-monitoring.md)
- Telemetry: the FAQ says Hermes "does not collect telemetry". v0.22.0 adds "opt-in telemetry" for install, update, skill and plugin failure reasons. — [docs/reference/faq.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/faq.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- State layout under `HERMES_HOME` (`~/.hermes`, or `/opt/data` in Docker): `config.yaml`, `.env`, `auth.json`, `state.db`, `memories/`, `skills/` (plus `.archive/`, `.curator_ledger.jsonl`), `cron/jobs.json`, `kanban.db`, `pending/`, `profiles/<name>/`. — [docs/user-guide/docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md), [curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md), [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), [kanban.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md)

### Inferences
- Hermes's self-improvement loop is close to a reference implementation of what Odin's journal and principles system aims for. It differs from Saga in three ways:
  - default writes are ungated;
  - the reviewer is the same model, a fork, not a cross-model auditor;
  - the units are skills and memory entries, not principles.
- Hermes is designed around one long-lived conversational agent per profile. Odin's role (planner fielding operator chat and fleet events) fits that shape more naturally than dvergar's per-iteration fresh-context loop does.

### Gaps
- No independent evaluation was found showing that the skill loop improves task outcomes. A blog-cited Nous claim of "40% faster with 20+ skills" is unverified ([aibuilderclub](https://www.aibuilderclub.com/blog/hermes-nous-research-self-improving-agent)).
- No measured data was found on how often background reviews write harmful or incorrect skills in practice.

## 3. Extension model: plugins, hooks, skills format, MCP, custom tools, configuration

### Takeaway
Hermes has a broad, documented extension surface:
- in-process Python plugins registering tools, hooks, platforms, providers, memory, context engines, approval transports, middleware, CLI commands and system-prompt sections;
- subprocess "shell hooks" using Claude-Code-compatible JSON and exit-code semantics;
- gateway hooks;
- signed outbound webhooks;
- an MCP client and a limited MCP server;
- agentskills.io-compatible skills;
- YAML configuration.

### Cited Findings
- Plugin discovery and layout:
  - Three sources: `~/.hermes/plugins/` (user), `.hermes/plugins/` (project, disabled unless `HERMES_ENABLE_PROJECT_PLUGINS=true`), and pip entry points.
  - Each plugin is a `plugin.yaml` manifest plus `register(ctx)`.
  - Plugins are opt-in via `plugins.enabled`, with exceptions.
  - Source: [docs/user-guide/features/plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
- Plugin context API (from docs): `register_tool`, `register_hook`, `register_command`, `register_cli_command`, `register_platform`, `register_platform_handler`, `register_memory_provider`, `register_context_engine`, `register_middleware`, `register_approval_transport`, `register_skill`, `register_terminal_environment_provider`, `register_tts_provider`, `register_transcription_provider`, `register_image_gen_provider`, `register_video_gen_provider`, `register_computer_use_provider`, `register_dashboard_auth_provider`, `register_automation_blueprint`, `register_locale`, `register_system_prompt_section`, plus `inject_message`. — [plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md), [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Four hook systems: gateway hooks (`HOOK.yaml` + `handler.py`), plugin hooks, shell hooks (`hooks:` in config.yaml) and outbound webhooks (`hooks.outbound:`). — [docs/user-guide/features/hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Plugin and shell hook events (`VALID_HOOKS` in `hermes_cli/plugins.py`, 45 names):
  - tools and output: `pre_tool_call`, `post_tool_call`, `transform_terminal_output`, `transform_tool_result`, `transform_llm_output`;
  - LLM and streaming: `pre_llm_call`, `post_llm_call`, `on_stream_start`, `on_stream_delta`, `on_stream_end`, `on_interim_message`, `pre_verify`;
  - API and auxiliary calls: `pre_api_request`, `post_api_request`, `api_request_error`, `pre_auxiliary_call`, `post_auxiliary_call`, `transform_api_error_classification`;
  - sessions and skills: `on_session_start`, `on_session_end`, `on_session_finalize`, `on_session_reset`, `on_skill_lifecycle`;
  - subagents: `subagent_start`, `subagent_stop`;
  - gateway and commands: `pre_gateway_dispatch`, `post_gateway_admission`, `agent_loop_stopped`, `gateway_platform_event`, `pre_command`;
  - approvals and human input: `pre_approval_request`, `post_approval_response`, `on_human_input_request`, `on_human_input_resolved`;
  - other: `on_room_member_activity`, `pre_transcription`;
  - kanban: `kanban_task_claimed`, `kanban_task_completed`, `kanban_task_blocked`, `on_kanban_worker_spawned`, `on_kanban_worker_exited`, `on_kanban_worker_stale_claim`, `on_kanban_task_updated`, `on_kanban_dispatch_tick`.
  - Source: [hermes_cli/plugins.py](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/plugins.py), [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Gateway hook events: `gateway:startup`, `session:start`, `session:end`, `session:reset`, `session:compress`, `agent:start`, `agent:step`, `agent:end`, `reaction:added`, `reaction:removed`, `command:*`. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Hook semantics:
  - Categories are observers (return ignored), transforms (first string wins) and directive/control.
  - `pre_tool_call` can `block`, `approve` (escalate to human approval) or `modify` args. It fails closed on timeout or exception.
  - `pre_llm_call` returns are injected into the user message ("Claude Code's `UserPromptSubmit` event is intentionally not a separate Hermes event — `pre_llm_call` fires at the same place").
  - Source: [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Shell hooks:
  - Any executable, run with `shell=False`.
  - Timeout defaults to 60s, capped at 300.
  - `fail_closed` is honored only on `pre_tool_call`.
  - "Exit code 2 = block (Claude Code / Cursor compatible)". Claude-Code-format JSON (`{"decision": "modify", "tool_input": …}`) is accepted.
  - First-use consent prompt per (event, command).
  - Source: [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Outbound webhooks push signed lifecycle events to HTTP endpoints. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Cache-safe system-prompt sections via `ctx.register_system_prompt_section(id, fn, position="after_memory", max_chars≤4000)`. They render once per new session and are frozen thereafter. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- MCP client: stdio and HTTP transports with reconnection, resources/prompts and sampling (since v0.2.0). — [Release v2026.3.12](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.3.12), [docs/user-guide/features/mcp.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md)
- MCP server: `hermes mcp serve` (stdio) exposes 10 messaging tools, e.g. `conversations_list`, `messages_read`, `events_poll`, `events_wait`, `messages_send`, `permissions_list_open`. It lets "Claude Code, Cursor, or another coding agent… send and read Telegram/Discord/Slack messages through Hermes". It does not expose the agent itself. — [mcp.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md)
- Programmatic protocols: ACP (stdio JSON-RPC), TUI-gateway JSON-RPC (`prompt.submit`, `session.steer`, `session.interrupt`, …) and the HTTP API. Hermes can also be imported as a Python library (`from run_agent import AIAgent`). No supported wheel is published. — [docs/developer-guide/programmatic-integration.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/programmatic-integration.md), [docs/guides/python-library.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/python-library.md)
- Configuration: `~/.hermes/config.yaml` (non-secret) plus `~/.hermes/.env` (secrets), with per-profile copies under `~/.hermes/profiles/<name>/`. The annotated example `cli-config.yaml.example` is ~125 KB. — [docs/user-guide/configuration.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md), [cli-config.yaml.example](https://github.com/NousResearch/hermes-agent/blob/main/cli-config.yaml.example)
- Imports from other agents: `hermes import-agent` brings in a Claude Code (`~/.claude`) or Codex CLI setup (instructions, allowlists, MCP servers, skills, memories). Claude Code session logs can also be imported. — [docs/user-guide/import-from-other-agents.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/import-from-other-agents.md), [docs/user-guide/sessions.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/sessions.md)

### Inferences
- The hook taxonomy is a strict superset of what Saga uses from Claude Code (Stop and SessionStart hooks). Shell-hook compatibility means existing dvergr hook scripts could be adapted mostly by remapping event names (`Stop` ≈ `post_llm_call`/`on_session_end`; `UserPromptSubmit` ≈ `pre_llm_call`).

### Gaps
- I did not read the full `register_platform` adapter contract in code (only the docs summary), so the effort to write an MQTT platform adapter is estimated, not measured.

## 4. Autonomy and unattended operation: daemons, loops, Docker without a TTY, first-run, config, multiple instances

### Takeaway
Hermes is built to run unattended as a supervised gateway daemon (systemd or s6-overlay in Docker) with cron, heartbeats, loops, goals and a kanban dispatcher. Headless one-shot runs (`chat --oneshot -q`, `--query-file`, `--format stream-json`) and file-based configuration avoid interactive setup. Multiple instances are handled by profiles, and the default topology is now one gateway per machine.

### Cited Findings
- Official Docker image (`nousresearch/hermes-agent`):
  - stateless image plus a `/opt/data` data volume;
  - `gateway run` is supervised by s6-overlay (auto-restart);
  - optional dashboard and API server on port 8642;
  - "never point two containers at the same ~/.hermes directory".
  - Unattended gateway and cron sessions enable tool-loop hard stops by default.
  - Source: [docs/user-guide/docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md)
- First-run: the documented first step is an interactive `docker run -it … setup` wizard that writes `.env` and `config.yaml`. Configuration can also be supplied directly via env vars and config files. `HERMES_NONINTERACTIVE=1` suppresses interactive prompts in scripted starts. — [docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md), [docs/user-guide/windows-native.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/windows-native.md)
- Headless CLI flags:
  - `--oneshot` ("answer the query and exit… Implied on non-TTY stdio and by `-Q`");
  - `--query-file` (no shell interpretation);
  - `--format stream-json` (JSONL events on stdout);
  - `--yolo`, `--ignore-user-config`, `--ignore-rules`, `--safe-mode`, `--max-turns`, `--resume`.
  - A `-q` prompt "is never parsed as a slash command".
  - Source: [docs/reference/cli-commands.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md)
- Headless approvals: `approvals.cron_mode`, `single_query_mode` and `unattended_mode` default to `deny`, so a dangerous command is blocked instantly instead of waiting for a human. — [docs/user-guide/security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Cron under systemd uses transient user scopes. Hosts without a user systemd session (containers, minimal LXCs) "degrade" to unscoped workers. — [cron.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md)
- Profiles: each `hermes -p <name>` profile gets its own HERMES_HOME, config, memory, sessions and gateway identity, and "Multiple profiles run concurrently". v0.22.0 makes one multiplexed gateway per machine the default. — [architecture.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/architecture.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Shared memory: "Don't point two agent processes at the same Hermes home directory." Shared memory should go through an external memory provider. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
- Loop guardrails: `/loop` backstop `loops.max_ticks: 100`; `/goal` default 20-turn budget; kanban `--goal --goal-max-turns`. — [loops.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/loops.md), [goals.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md), [kanban.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md)
- `/goal` and kanban: the only CLI flag that starts a goal loop headlessly is `--goal` on `hermes kanban create` (`hermes_cli/kanban_parser.py`). `/goal` itself is a slash command. — [hermes_cli/kanban_parser.py](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/kanban_parser.py), [goals.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md)

### Inferences
- Compared with Saga's Claude Code containers, Hermes has no equivalent of the `.claude.json` first-run dialog problem. Its interactive steps are an optional wizard and are avoidable with pre-written `config.yaml`/`.env`. This needs confirming by a container smoke test.
- For a dvergr-style headless loop, the paved options are:
  - a kanban goal-mode card;
  - driving `/goal` through the TUI-gateway JSON-RPC (`prompt.submit`) or the API server;
  - an external loop calling `hermes chat --oneshot --resume <session>` per iteration.

### Gaps
- I did not test Hermes in a no-TTY container, so the claim of no blocking first-run prompts rests on docs, not observation.

## 5. Models, auth and billing: providers, Claude subscription, Anthropic policy, ChatGPT subscription, local models, cost controls

### Takeaway
Hermes is provider-agnostic: Nous Portal, OpenRouter, Anthropic, OpenAI, Codex/ChatGPT OAuth, Copilot, Gemini/Vertex, Bedrock, xAI OAuth, local llama.cpp/Ollama/vLLM and more. For Claude subscriptions there are two routes:
- Built-in Anthropic OAuth, which per Hermes docs bills only Max "extra usage" credits, never the base allowance.
- An official but experimental Nous plugin that drives the official `claude` CLI per request. Its maintainers measured it as drawing subscription usage at the `claude -p` / Agent SDK rate, about 1.7x the interactive TUI's metering.

Anthropic's Help Center (update dated 2026-10-07) now says the Agent SDK, `claude -p` and third-party apps can be used with subscription limits. That conflicts with Saga's April 2026 test result and needs re-testing.

### Cited Findings
- Provider table:
  - Nous Portal (OAuth subscription);
  - OpenAI Codex ("ChatGPT or Codex Subscription", ChatGPT OAuth);
  - GitHub Copilot (OAuth device code);
  - Anthropic ("Claude Max + extra usage credits via OAuth; also supports Anthropic API key or manual setup-token");
  - OpenRouter (API key or PKCE OAuth);
  - xAI Grok OAuth (SuperGrok/Premium+);
  - Qwen OAuth, MiniMax OAuth;
  - Google Vertex, Gemini API key;
  - and many more.
  - Source: [docs/integrations/providers.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md)
- Built-in Anthropic OAuth: "The OAuth path routes as Claude Code against your Anthropic account and **only works on a Claude Max plan with purchased extra usage credits** — the base Max allowance is never consumed by Hermes, only the extra/overage credits on top. Claude Pro subscribers cannot use this path". — [providers.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md)
- Borrowed Claude Code login: Hermes can read and refresh Claude Code's `~/.claude/.credentials.json`. The security docs warn that both CLIs "use single-use, rotating refresh tokens: once two programs hold one token family, whichever refreshes first invalidates the other's copy". `auth.adopt_external_logins: false` disables borrowing. — [docs/user-guide/security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Official plugin `claude-subscription-directsdk` (experimental): what it is and how it works
  - "drives the unmodified official Claude Code executable as a request-scoped model client for your Claude Pro/Max subscription. Hermes keeps its normal agent loop, tools, approvals and compaction."
  - Each request spawns a fresh `claude` process in stream-json mode with native tools disabled.
  - A loopback relay admits exactly one upstream Messages request per Hermes call.
  - Requirements: Hermes ≥0.21.4 and Claude Code ≥2.1.280 for Opus 5.5. "Native Claude Code 2.1.263 is qualified".
  - Source: [NousResearch/hermes-plugin-claude-subscription-directsdk README](https://github.com/NousResearch/hermes-plugin-claude-subscription-directsdk) (moved to [hermes-official-plugins](https://github.com/NousResearch/hermes-official-plugins/tree/main/claude-subscription-directsdk))
- The same plugin's metering measurement (Pro plan, 2026-09-09): "This provider draws subscription usage at exactly the `claude -p` / Agent SDK rate… Interactive Claude Code is metered at roughly 0.58x that rate, so plan for about 60% of the TUI's throughput per 5-hour window". Its catalog entry discloses that "every turn is billed against your Claude subscription's Agent SDK allowance". — [plugin README](https://github.com/NousResearch/hermes-plugin-claude-subscription-directsdk), [plugin-catalog/claude-subscription-directsdk.yaml](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/claude-subscription-directsdk.yaml)
- Anthropic Help Center, "Use the Claude Agent SDK with your Claude plan":
  - 2026-10-07 update: "You can still use the Claude Agent SDK, `claude -p`, and third-party apps with your subscription limits", and "Claude Max and Team plans now include monthly API credits, which cover the Claude Agent SDK, claude -p, the Claude API, and Claude Managed Agents."
  - 2026-06-15 update: Anthropic "paused the previously-announced changes to Claude Agent SDK usage".
  - Source: [support.claude.com article 15036540](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- Conflicting secondary reading: Developers Digest (2026-10-08) says the new monthly credit applies only when `claude -p`/SDK runs use an API key from a linked Console org, and that runs signed in with a plan draw from plan limits. — [Developers Digest](https://www.developersdigest.tech/blog/claude-max-team-monthly-api-credits-2026)
- Community history: issue #25267 ("Claude Agent SDK model provider with subscription OAuth", 57 reactions, still open) cites Anthropic's planned June 15 Agent SDK credit. On 2026-09-20 maintainer teknium1 pointed to the DirectSDK plugin as the resolution path. — [issue #25267](https://github.com/NousResearch/hermes-agent/issues/25267)
- Codex App-Server runtime: optionally hands OpenAI turns to the Codex CLI app-server to "Run OpenAI agent turns against your **ChatGPT subscription** (no API key required)". Codex's tools and sandbox execute, and Hermes provides sessions, gateway, memory and skill review. ChatGPT plan-quota semantics are "not currently documented". — [docs/user-guide/features/codex-app-server-runtime.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/codex-app-server-runtime.md), [providers.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md)
- Local models: v0.22.0 adds one-click llama.cpp management (CPU/CUDA/Metal/Vulkan/ROCm). Ollama, vLLM and LM Studio are supported. — [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0), [docs/user-guide/docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md)
- Cost controls:
  - per-task auxiliary model routing (compression, review, curator, approval, goal judge);
  - cheaper subagent models;
  - background-review `enabled`/`max_input_tokens`;
  - `/usage` and `/insights`;
  - `agent.max_turns`;
  - loop `max_ticks`;
  - prompt caching with `cache_ttl: auto`;
  - "auto-routing never bills a provider you didn't pick".
  - Sources: [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), [delegation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Overhead reports (weak sources): third-party cost write-ups say fixed tool-schema and system overhead is large and gateway sessions cost more input tokens than the CLI. One attributes "73% of every API call is fixed overhead" to a Reddit user's dashboard. — [getopenclaw.ai](https://www.getopenclaw.ai/blog/hermes-agent-cost) (vendor blog, weak)

### Inferences
- Hermes's own docs and the Help Center conflict. The providers.md note (extra usage only) may predate Anthropic's 2026-06-15 and 2026-10-07 updates, or may describe the direct-OAuth path specifically, as distinct from the CLI-driven plugin path.
- Under Saga's stated hard constraint (interactive Claude Code sessions only), none of Hermes's Claude routes qualify:
  - built-in OAuth: extra usage;
  - DirectSDK plugin: `claude -p` metering, about 1.7x more allowance per token than interactive;
  - API key: per-token.
- If Anthropic's 2026-10-07 statement holds for subscription-signed-in runs, the constraint has partly dissolved. The remaining cost is the ~1.7x metering penalty the plugin authors measured on Pro. Saga should re-run its April 2026 billing test before using the constraint to reject any harness.
- The rotating refresh-token warning is a plausible explanation for Saga's observed credential-volume refresh failures, where many containers share one `.credentials.json` token family. Reasoning: each refresh by one holder invalidates the others' copies. This is my inference, not a Hermes claim about Saga.

### Gaps
- Whether the 2026-10-07 Max monthly API credits apply to subscription-OAuth `claude -p` runs or only to Console API-key runs could not be confirmed. Sources conflict.
- The DirectSDK plugin's metering was measured on Pro, not Max.
- No first-hand statement was found from Hermes maintainers on Anthropic's April 4, 2026 third-party-harness policy specifically. Hermes docs do not mention it by date.

## 6. Security and sandboxing

### Takeaway
Hermes has a layered but mostly cooperative security model:
- gateway user allowlists and DM pairing;
- dangerous-command approval (smart, manual or off) over a hardline blocklist;
- file-write denylists;
- hardened Docker, Modal and other sandbox backends;
- environment-variable filtering;
- context-file injection scanning;
- an optional TLS-intercepting egress proxy.

Python plugins and gateway hooks run in-process with full trust. The project has had several CVEs and an external audit reporting Critical findings in default config.

### Cited Findings
- Eight-layer model: user authorization, dangerous-command approval, file-write safety, container isolation, MCP credential filtering, context-file scanning, cross-session isolation, input sanitization. — [docs/user-guide/security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Approval modes:
  - `approvals.mode: smart` (default): an auxiliary LLM auto-approves low-risk commands, auto-denies dangerous ones and escalates uncertain ones;
  - `manual`;
  - `off` (= `--yolo`).
  - A hardline blocklist (`rm -rf /`, fork bombs, mkfs, dd to disks, piping URLs to sh) cannot be overridden. User `approvals.deny` globs are applied before yolo.
  - Source: [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Terminal backends: local (no isolation), ssh, docker, singularity, modal, daytona, vercel_sandbox. For container and cloud backends the "Dangerous Cmd Check" is "Skipped (container is boundary)". — [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Docker backend flags: `--cap-drop ALL` (+DAC_OVERRIDE/CHOWN/FOWNER), `no-new-privileges`, `--pids-limit 256`, size-limited tmpfs, CPU/memory/disk limits, and no host env by default. Credential files are mounted read-only. — [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Network controls:
  - SSRF protection and a website access policy;
  - the "iron-proxy" egress option, an "outbound credential-injection firewall for remote terminal sandboxes. The sandbox only ever holds opaque proxy tokens; real API keys never leave the host";
  - recommended network isolation by running the gateway separately and executing via the SSH backend.
  - Sources: [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md), [docs/user-guide/egress/index.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/egress/index.md)
- Trust model:
  - Gateway hooks are "trusted-by-placement… no sandbox, no first-use prompt, and `HERMES_SAFE_MODE` does not skip this loader". — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
  - Python plugins "run in-process and this setting is not a sandbox". — [plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
  - Kanban descendant fencing is "cooperative runtime scoping, **not OS confinement**". — [kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md)
- Secrets: `.env` per profile, external secret sources (1Password, Bitwarden, command), an encrypted credential vault, and `env_passthrough` allowlists. `execute_code` strips vars whose names contain KEY/TOKEN/SECRET/etc. — [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Security history:
  - CSA research note (2026-05-04, explicitly "AI-assisted… has not undergone official CSA review"): an external audit by @Anic888 disclosed on 2026-04-11 found "four Critical and nine High severity findings in the framework's default configuration, including unrestricted shell execution, containerized approval bypass, and persistent skill injection vectors". It also lists CVE-2026-7396 (WeCom path traversal, v0.8.0), CVE-2026-7397 (file_tools symlink following, fixed in v0.9.0) and CVE-2026-6829 (separate hermes-webui package). — [CSA research note](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/05/CSA_research_note_hermes_agent_CVEs_20260504-csa-styled.pdf)
  - CVE-2026-18976: incorrect privilege assignment in `disabled_toolsets` handling, up to 0.16.0. — [NVD](https://nvd.nist.gov/vuln/detail/cve-2026-18976)
  - CVE-2026-9368: `execute_code` sandboxing, before 0.11.0. — [Kodem](https://www.kodemsecurity.com/cve-archive/cve-2026-9368)
  - CVE-2026-9369: project-plugin discovery LPE, 2026.4.23. — [vuln.today](https://vuln.today/cve/CVE-2026-9369)
- Supply chain: exact-pinned dependencies since 2026-05-12; v0.22.0 adds hash-checked installers and a reviewed, commit-pinned plugin catalog ("catalog rules keep listed plugins from patching Hermes internals or shipping unscannable binaries"). — [pyproject.toml](https://github.com/NousResearch/hermes-agent/blob/main/pyproject.toml), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)

### Inferences
- The Docker terminal backend has Hermes create containers itself, which needs Docker socket access. That conflicts with Saga's rule that "Odin NEVER gets Docker socket access". A Hermes-based Odin would have to use the `local` backend inside its own Trail-of-Bits container and keep Heimdall as the only launch path, via a custom file-writing tool.
- The smart-approval LLM judge and the `/review` cross-model reviewer show Nous accepts LLM-as-gate designs. Hermes has no built-in equivalent of a separate-process cross-model auditor holding veto over planner decisions.

### Gaps
- I could not read the full @Anic888 audit or confirm which findings were fixed.
- Some CVE details (version ranges, CVSS) differ across aggregators and were not checked against vendor advisories.

## 7. Fit for Saga

### Takeaway
- (a) Odin: Hermes is a technically strong fit for Odin's shape: persistent chat agent, Telegram, scheduled checks, memory and skills, external-event injection without tmux. It would replace ratatoskr's tmux nudging with first-class injection APIs. The cost is giving up interactive Claude Code billing, which is Saga's current hard constraint, and adopting a fast-churning harness.
- (b) dvergar: Hermes has every primitive a worker needs (post-turn hooks, Ralph-style `/goal` loop with deterministic gates, headless startup), but its loop paths are either interactive slash commands or tied to its own kanban.
- (c) Patterns: the highest-value takeaways even if Saga stays on Claude Code are Hermes's memory, skill-review, approval-staging, curator-ledger, heartbeat/cron gating and kanban lifecycle patterns.

### Cited Findings

**(a) Odin on Hermes: mechanisms**
- External events as turns (replacing `tmux send-keys`):
  - `ctx.inject_message(..., session_key="agent:main:telegram:dm:<id>")` queues text into Odin's live Telegram session via the busy-session queue, with authorization rechecked. — [plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
  - `POST /api/sessions/{id}/chat` runs one turn in a named session over REST, serialized by session turn leases. — [api-server.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/api-server.md)
  - Webhook routes (HMAC, filters, coalescing, `cron_job`) run fresh sessions per event and can mirror deliveries into the chat session. — [webhooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/webhooks.md)
  - A custom platform adapter can be added as a plugin (`BasePlatformAdapter.connect/send`, inbound via `self.handle_message(event)`). — [docs/developer-guide/adding-platform-adapters.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/adding-platform-adapters.md)
  - No MQTT integration exists in the repo or the 604-entry plugin catalog (grep found none). — [plugin-catalog/](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog)
- Busy handling: `busy_input_mode` (interrupt/queue/steer) governs what happens when operator or event messages arrive mid-turn. — [messaging/index.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md)
- Inbox and outbox files as tools: `ctx.register_tool(name, toolset, schema, handler)` adds Python tools. MCP servers are also supported. — [plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md), [mcp.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md)
- Policy gating for the Mimir handoff: `pre_tool_call` can `block` or `approve` (escalate to a human) a specific tool call, and fails closed on timeout. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Approval routing: `register_approval_transport` changes where a human answers approvals. It is "not an authorization-policy API". — [plugins.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md)
- Cross-model review: `/review` with `auxiliary.review` pinned to another model runs a background reviewer whose findings re-enter the session. — [delegation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md)
- Separate review lane: kanban `kanban_request_review(reviewer=…)` routes work to a reviewer lane. — [kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md)
- Principles gating analog:
  - `skills.write_approval: true` and `memory.write_approval: true` stage all writes, including background ones, in pending queues approved via `/skills approve`/`/memory approve` from Telegram. — [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
  - The curator ledger provides audit and per-mutation rollback. — [curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md)
- Telegram: native adapter with allowlists, DM pairing, forum topics, inline approval buttons, home channel, cron delivery to topics, and voice transcription. — [docs/user-guide/messaging/telegram.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/telegram.md), [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)

**(b) A dvergr on Hermes: mechanisms**
- Post-turn hooks to publish status:
  - `post_llm_call` (each successful, non-interrupted turn, with full response);
  - `on_session_end` ("Canonically at each turn finalization" with `completed`/`failed`/`interrupted`/`turn_exit_reason`);
  - `post_tool_call`, `subagent_stop`;
  - gateway `agent:step` per loop iteration.
  - Shell hooks can run any executable (e.g. `mosquitto_pub`) as a subprocess per event.
  - Source: [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Reading guidance files: `pre_llm_call` (plugin or shell hook) injects context into each turn's user message, e.g. the contents of a guidance file. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
- Loop mode:
  - `/goal` with judge, completion contracts and quality gates ("Gates run before the judge… a red gate is deterministic evidence the goal isn't done"). Default budget is 20 turns, and `/goal wait <pid>` parks the loop on a process. — [goals.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md)
  - Kanban `--goal` cards. — [kanban.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md)
- Container startup: official image with s6 supervision, `/opt/data` volume, `--oneshot`/`--query-file`/`--format stream-json`/`--yolo`, and default deny for unattended dangerous commands. — [docker.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/docker.md), [cli-commands.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md), [security.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md)
- Kanban lanes:
  - "Wiring a non-Hermes CLI tool (Codex CLI, Claude Code CLI, OpenCode CLI…) as a kanban worker lane is *not yet a paved path*". `spawn_fn` is pluggable, but a Codex-specific PR (#19924) was closed unmerged. — [kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md)
  - Hermes profile lanes run as local OS processes, not Docker containers. — [kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md)
- Driving Claude Code from Hermes: the bundled `claude-code` skill drives Claude Code either via `claude -p` ("PREFERRED") or interactively via tmux `send-keys`/`capture-pane`, the same technique ratatoskr uses. — [skills/autonomous-ai-agents/claude-code/SKILL.md](https://github.com/NousResearch/hermes-agent/blob/main/skills/autonomous-ai-agents/claude-code/SKILL.md)

**(c) Patterns worth adopting (file references)**
1. Bounded, frozen-snapshot memory with a visible capacity header and error-on-overflow that forces consolidation. Agent-environment notes and user profile live in separate stores. — [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md), [tools/memory_tool.py](https://github.com/NousResearch/hermes-agent/blob/main/tools/memory_tool.py)
2. Post-turn background review fork with a tool whitelist, trigger intervals (`nudge_interval` 10), and an explicit "Do NOT capture" list (environment failures, negative tool claims, unresolved failures). — [agent/background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py), [agent/turn_finalizer.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/turn_finalizer.py)
3. Lesson-shape contract for durable knowledge: "lessons, not logs", a rule plus one clause of why, no PR numbers or dates, fix in place rather than append "UPDATE:", class-level names. — [background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py), [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
4. Write-approval staging queue: persistent pending dir, `/pending|diff|approve|reject` over chat, and approval pinned to the exact target text (refused if it changed). — [skills.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md), [memory.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/memory.md)
5. Curator lifecycle and ledger: provenance (`created_by` agent/learn/user), usage counters, active→stale→archived, pinning, never auto-delete, append-only ledger with content-addressed before/after blobs, single-entry rollback, snapshot before mutating passes. — [curator.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/curator.md), [agent/curator.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/curator.py), [tools/skill_ledger.py](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_ledger.py)
6. Read-before-write enforcement on durable-knowledge edits: `skill_manage` refuses edits without a fresh `skill_view`. — [background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py)
7. Heartbeat semantics: inject only between turns as a plain user message, coalesce missed ticks, real user messages win, a silence marker (`NO_REPLY`/`[SILENT]`) suppresses delivery, and a "don't-invent-work" guard. — [heartbeat.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/heartbeat.md)
8. Cron cost gating: `no_agent` script jobs and pre-check scripts emitting `{"wakeAgent": false}` skip the LLM. Cron cannot create cron by default. Model pins are user-owned. Failure incidents alert once and then remind on a cooldown. — [cron.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md)
9. Busy-input policy (interrupt/queue/steer) with debounce of merged busy text. — [messaging/index.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md)
10. Goal loop with completion contract (outcome / verification / constraints / boundaries / stop_when) and deterministic quality gates before any LLM judge. — [goals.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md)
11. Worker lifecycle contract: exactly one terminator per run (complete / request_review / block), heartbeat, stale-claim TTL with live-PID extension, `max_runtime_seconds`, consecutive-failure breaker, stranded-task diagnostics, idempotent creation keys, durable `task_runs`/`task_events`, ~90% budget checkpoint notice. — [kanban-worker-lanes.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md), [kanban.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md)
12. Hook taxonomy with explicit failure semantics: observers fail-open; policy `pre_tool_call` fails closed with a timeout; transforms take the first valid replacement. — [hooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md)
13. Prompt-cache invariants: frozen system prompt per session; mid-session changes (new skills, memory) delivered as one-shot user-channel notes; config changes deferred to the next session. — [prompt-assembly.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/prompt-assembly.md), [AGENTS.md](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md)
14. Autoreason-style judging: A/B/AB with fresh-context judges, blind Borda count, and "no change" as a first-class winner. A candidate template for Mimir verdicts. — [autoreason README](https://github.com/NousResearch/autoreason)
15. Webhook ingestion recipe: HMAC per route, payload filters, script transform, coalesce key and window, `deliver_only`, and mirror-to-session so the chat agent knows what was pushed. — [webhooks.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/webhooks.md)

### Inferences

**(a) Could Odin run on Hermes? Technically yes. Policy and billing say not as Saga's constraints stand today.**

Gained:
- Event injection without tmux: an MQTT→`inject_message` plugin, or ratatoskr calling the Sessions REST API.
- Real busy and queue semantics instead of keystroke timing.
- Native Telegram with approval buttons, so no dependency on the Claude Code Telegram channel plugin.
- Cron and heartbeat for periodic fleet sweeps, with `wakeAgent` gating to save tokens.
- A tested memory/skills/curator stack that could host the master journal and principles.
- Approval staging for human gating.
- OTLP metrics to Grafana.
- `hermes send` for one-shot alerts from ratatoskr or Heimdall.

Lost:
- Interactive-Claude-Code billing. Odin would bill via API key, Max extra usage, or the DirectSDK plugin at `claude -p` metering, about 1.7x the interactive rate per the plugin's own Pro measurement.
- Claude Code's own tool and harness behavior and first-party plugin ecosystem.
- Saga's documented rejection of third-party harnesses, which would need revisiting.
- Stability: Hermes ships breaking changes most releases.

Mimir mapping options:
1. Mimir as a separate Hermes profile reached via kanban review lanes.
2. A `pre_tool_call` plugin that blocks Odin's "launch/delegate" tools until a Sonnet verdict file exists. This fails closed, so it preserves the auditor-veto property.
3. `/review` with `auxiliary.review` on Sonnet. This is advisory only, not a gate.

Principles mapping: skills/memory `write_approval` gives the human gate. Adding Mimir before human approval would need a small plugin that reviews the staged pending files. Inference: there is no built-in auditor stage.

Heimdall stays the boundary: Odin-on-Hermes would use the `local` terminal backend in its container and a custom tool writing YAML requests. Hermes's own Docker backend must not be enabled.

**(b) Could a dvergr run on Hermes? Yes for mechanics.**
- `on_session_end` and `post_llm_call` shell hooks can publish MQTT status and journal JSON per turn.
- `pre_llm_call` can read guidance files.
- The container image and `--oneshot`/stream-json make startup clean.
- The friction is the loop. `/goal` is a slash command, and `-q` never parses slash commands. A headless dvergr would need one of:
  - an external loop calling `hermes chat --oneshot --resume`;
  - TUI-gateway JSON-RPC to submit `/goal`;
  - Hermes kanban, which would duplicate Odin/MQTT orchestration.
- `/goal` quality gates and completion contracts are arguably better than ralph-loop's completion-promise string. Gates are deterministic test commands; ralph-loop relies on a model-emitted completion-promise string.
- For a harness-agnostic Saga, Hermes's kanban-worker-lane contract is a useful spec for the harness-neutral worker protocol Saga would need: env-var task handoff, exactly-one terminator, heartbeat/TTL. Hermes itself says non-Hermes CLI lanes are not yet paved.

**(c) Top patterns to adopt.** In descending value:
1. Bounded frozen memory plus the background-review "lessons not logs" and "do-not-capture" rules, applied to Odin's journal and principles.
2. Write-approval staging with target pinning plus the curator ledger and rollback, for principles governance.
3. Heartbeat and busy-input semantics, to harden ratatoskr's nudging.
4. Cron `wakeAgent`/`no_agent` gating, for cheap periodic checks.
5. Goal quality gates and the kanban terminator/TTL contract, for dvergr completion and liveness.
6. Hook failure semantics.

### Gaps
- No live experiment was run. Feasibility claims for Odin and dvergr are inferred from docs and code, not tested.
- The exact `session_key` format and lifecycle for a long-lived Telegram DM session were taken from a doc example (`agent:main:telegram:dm:123456789`). I did not verify how it changes across compression rotations.
- Whether `/goal` can be triggered through the API server's chat endpoints (slash-command parsing over HTTP) was not verified.

## 8. Risks: bus factor, stability, breaking changes, licensing, policy, lock-in

### Takeaway
The main risks are extreme churn with frequent breaking changes, heavy commit concentration in one maintainer despite thousands of contributors, a security history typical of persistent-agent frameworks, Anthropic billing-policy dependence for any Claude-subscription route, and growing commercial pull toward Nous Portal. MIT licensing and agentskills.io-compatible skills keep lock-in moderate.

### Cited Findings
- Bus factor: of ~52,275 commits, the top contributors are teknium1 (20,670), kshitijk4poor (5,037), OutThisLife (4,560) and ethernet8023 (2,260). — [contributors API](https://api.github.com/repos/NousResearch/hermes-agent/contributors)
- Churn:
  - v0.21.0→v0.22.0 (2026-08-31→2026-10-13) reports ~24,200 commits and ~6,080 merged PRs.
  - The source shrank from ~1.06M to 698K lines in one cycle.
  - `gateway/run.py` went from 34,847 to 5,512 lines.
  - Source: [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Breaking or behavioral changes in v0.22.0:
  - Python 3.14 runtime;
  - one gateway per machine by default;
  - chats no longer auto-reset on idle/daily timers;
  - sessions auto-pruned after 90 days by default;
  - memory providers moved to catalog plugins;
  - "the old plugin compatibility import layer is gone", `hermes sync` removed, tirith scanner removed, "Several tools were renamed".
  - Source: [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Release discipline is new: tested stable releases date from v0.21.6 (2026-10-08). Before that, installs tracked `main` or CalVer tags. — [stable-releases.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/stable-releases.md), [Release v0.22.0](https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.0)
- Backlog: 15,325 open issues and 33,199 open PRs (2026-10-14). — [issues](https://github.com/NousResearch/hermes-agent/issues), [pulls](https://github.com/NousResearch/hermes-agent/pulls)
- Licensing and provenance controversy:
  - EvoMap alleged Hermes copied its Evolver self-evolution architecture. Reports say a GitHub issue was retitled and comments deleted, and Nous reportedly told the accuser to "delete your account". EvoMap then relicensed Evolver from MIT to GPLv3.
  - These are unadjudicated allegations reported mainly by the accusing side.
  - Sources: [Yicai Global](https://www2.yicaiglobal.com/news/chinese-ai-team-evomap-changes-ai-agents-license-after-accusing-silicon-valley-ai-lab-of-copying-code), [36Kr](https://www.36kr.com/p/3767967755371011), [hn.svelte.dev mirror of HN thread](https://hn.svelte.dev/item/48318706)
- Third-party UX review (eesel, a vendor of a competing support product, last edited 2026-07-19): reports of "Sluggish, very slow to start" and a "janky, flickery" CLI. It cites community advice to "Run it within a sandbox". — [eesel review](https://www.eesel.ai/blog/hermes-agent-review)
- Policy risk:
  - The Claude-subscription plugin is "Experimental" and qualified against specific Claude Code CLI versions ("Replay acknowledgments and extra-body behavior are version-sensitive interfaces, not a public arbitrary-history SDK guarantee"). — [plugin README](https://github.com/NousResearch/hermes-plugin-claude-subscription-directsdk)
  - Anthropic's Agent SDK and subscription terms changed at least twice in 2026 (June 15 pause; October 7 credits). — [Anthropic Help Center](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- Commercial direction: README and docs steer users to Nous Portal as "the recommended way to run Hermes Agent", and the $90M raise is for "Hermes for Businesses". — [providers.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md), [The Next Web](https://thenextweb.com/news/nous-research-90m-1-5bn-hermes-agent-wsj)
- Lock-in mitigators: MIT license; any OpenAI-compatible or local provider; skills compatible with agentskills.io; `hermes import-agent` from Claude Code/Codex and session export in Claude Code JSONL `trace` format. — [LICENSE](https://github.com/NousResearch/hermes-agent/blob/main/LICENSE), [README.md](https://github.com/NousResearch/hermes-agent/blob/main/README.md), [sessions.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/sessions.md)

### Inferences
- For Saga, the biggest practical risk is churn, not abandonment. A homelab system pinned to a Hermes version would need periodic migrations, since plugin APIs and tool names changed even in the last release. Pinning to the new stable channel and the Docker image digest mitigates this.
- Adopting Hermes patterns into Saga's own Claude Code-based code (option c) carries none of these risks. The value is in copying designs, not depending on the codebase.
- Lock-in risk is moderate. Hermes state (SQLite `state.db`, kanban.db, YAML config) is Hermes-specific. Skills (SKILL.md) and memory (Markdown) are portable.

### Gaps
- Nous's organizational size and the employment status of core maintainers could not be determined.
- No public SLA, LTS or deprecation policy beyond the new stable-release gate was found.
- I could not verify the EvoMap allegations or Nous's formal response.
