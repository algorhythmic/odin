# Deep dive: oh-my-pi (omp) by can1357 / Stencil Labs, and its relationship to Pi (badlogic/pi-mono → earendil-works/pi), assessed against Saga

Evidence base: shallow clone of `can1357/oh-my-pi` at commit `b91db66e9b0b65a2c977e6a5bc74b0f4b1d58d1c` (committed 2026-10-14 00:39 +0200, "Merge PR #15642"). I read it as data only and did not build or run anything. I also used the GitHub REST API (queried 2026-10-13), the upstream `earendil-works/pi` repo through the GitHub API, and web sources. In the URLs below, `…/blob/main/` stands for `https://github.com/can1357/oh-my-pi/blob/main/`.

## 1. Identity: what it is, who builds it, dates, license, runtime, activity, maturity, community, funding, and relationship to Pi

### Takeaway
omp ("oh-my-pi", command `omp`) is an MIT-licensed hard fork of Mario Zechner's Pi. It runs TypeScript on Bun with roughly 80k lines of Rust behind an N-API addon. Can Bölük, now operating as Stencil Labs, Inc., created it on 2025-12-31. It has shipped 658 releases (latest v18.10.4 on 2026-10-13), has about 35k stars, and changes very fast. It stopped full upstream syncs at a 2026-03-22 marker and since then has only cherry-picked selected upstream features while keeping compatibility shims for Pi extensions.

### Cited Findings
- The README says omp is "Built by Stencil Labs · Fork of Pi by @mariozechner". It also says "omp is a fork of Pi by Mario Zechner, rewritten as a coding-first surface" and "Originally built on Mario Zechner's wonderful Pi, omp adds everything you're missing." — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- The README's headline claims are "60+ providers · 31 built-in tools · 14 lsp ops · 28 dap ops · ~80k lines of Rust core". The runtime is Bun ≥ 1.3.14 on macOS, Linux and Windows. Install options are a curl script, Homebrew (`can1357/tap/omp`), `bun install -g @oh-my-pi/pi-coding-agent`, Nix flake, mise and PowerShell. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- The license is MIT, with copyright lines "2025 Mario Zechner", "2025-2026 Can Bölük" and "2026 Stencil Labs, Inc." — [LICENSE](https://github.com/can1357/oh-my-pi/blob/main/LICENSE). The root `package.json` names the author "Stencil Labs, Inc." with homepage omp.sh. — [package.json](https://github.com/can1357/oh-my-pi/blob/main/package.json)
- GitHub API, 2026-10-13: created 2025-12-31T14:01:28Z. `fork: false` and no parent, so it is not a GitHub-network fork. 35,361 stars, 3,852 forks, 97 watchers, 3,869 open issues plus PRs. Description: "Coding agent with the IDE wired in. Built by Stencil Labs." — [GitHub API repos/can1357/oh-my-pi](https://api.github.com/repos/can1357/oh-my-pi)
- Releases total 658. The first is v1.337.1 (2026-01-02) and the latest is v18.10.4 (2026-10-13). Major versions: v4.0.0 2026-01-10, v5 01-12, v6 01-19, v7 01-21, v8 01-23, v9 01-29, v10 02-01, v11 02-05, v12 02-12, v13 02-22, v15 05-13, v16 06-15, v17 07-15, v18 08-22. — [Releases](https://github.com/can1357/oh-my-pi/releases)
- Commit activity: about 29,982 commits on main, and about 7,020 since 2026-09-13. Weekly commit totals over the last 12 weeks ran 673–1,963, of which the owner made 210–664 per week. — [GitHub API commits / stats/participation](https://api.github.com/repos/can1357/oh-my-pi/stats/participation)
- Contributors number about 890 including anonymous ones. Top committers: can1357 13,195; roboomp (the project's bot) 4,085; badlogic 1,343 (inherited upstream history); H4vC 908; will-bogusz 669. — [Contributors](https://github.com/can1357/oh-my-pi/graphs/contributors)
- Issues and PRs (GitHub search API, 2026-10-13): 6,182 issues with 2,284 open, and 8,470 PRs with 1,585 open. — [Issues](https://github.com/can1357/oh-my-pi/issues)
- Stencil Labs calls itself "a research company that builds tools for agentic software development". Founders: Can Bölük (founder & CEO; "systems engineer and security researcher") and Meehir Patel (co-founder & COO, San Francisco). It is a Delaware corporation. It describes omp as "our open-source proving ground for applied AI research" and lists Hashline, Prewalk and Snapcompact as research outputs. — [stencil.so/about](https://stencil.so/about). The homepage also links a product called "Tern". — [stencil.so](https://stencil.so)
- Third-party coverage: Composio (2026-09-01) reports the fork was created 2025-12-31 by "security researcher Can Bölük", with "over 500 releases, 12,000+ commits, and over 26k GitHub stars" at the time. — [Composio: Pi vs OMP](https://composio.dev/content/pi-vs-omp). YUV.AI (2026-08-06) reported 22,344 stars and called it "an official fork". — [yuv.ai](https://yuv.ai/blog/oh-my-pi-omp-explained)
- Upstream: `badlogic/pi-mono` now resolves to `earendil-works/pi`, with 114,945 stars and 14,636 forks per the API. Its latest release is v1.2.0 (2026-10-12). — [GitHub API repos/badlogic/pi-mono](https://api.github.com/repos/badlogic/pi-mono). Composio says Pi "now sits under Earendil". — [Composio](https://composio.dev/content/pi-vs-omp). A search summary reports Earendil announced on April 8, 2026 that it had acquired Pi, with Zechner as a stakeholder. This is secondary and I did not open the primary source. — [Composio Pi vs Claude Code](https://composio.dev/blog/pi-agent-vs-claude-code)
- Upstream's own README says Pi "skips features like sub-agents and plan mode" and that "New issues and PRs from new contributors are auto-closed by default". — [earendil-works/pi README](https://github.com/earendil-works/pi)
- **Fork mechanics and divergence.** omp keeps a merge guide that records "Last Sync Point … Commit b21b42d032919de2f2e6920a76fa9a37c3920c0a, Date: 2026-03-22". It maps `@mariozechner/*` and `@earendil-works/*` to `@oh-my-pi/*` and lists "Intentional Divergences — do not port these upstream patterns":
  - a different UI architecture (StatusLineComponent);
  - a different tool factory (`createTools(session)`);
  - SQLite `agent.db` multi-credential auth instead of upstream `auth.json`;
  - capability-based discovery instead of upstream resource/package/settings managers;
  - `bun:test` instead of vitest.

  — [docs/porting-from-pi-mono.md](https://github.com/can1357/oh-my-pi/blob/main/docs/porting-from-pi-mono.md)
- Compatibility with Pi extensions is kept through adapters: `extensibility/legacy-*.ts` and `plugins/legacy-pi-compat.ts` ("removing them would break existing pi extensions"). `pkg.omp` is preferred, with fallback to `pkg.pi`. — [docs/porting-from-pi-mono.md](https://github.com/can1357/oh-my-pi/blob/main/docs/porting-from-pi-mono.md)
- Selective later ports exist. Coding-agent 18.3.5 (2026-09-27) says "Added prompt-cache warming, ported from earendil-works/pi". TUI 14.9.8 (2026-05-12) lists several "ports pi-mono `<sha>`" entries. A "sync: pi-mono v0.57.0" PR (#330) closed 2026-03-10. — [packages/coding-agent/CHANGELOG.md](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/CHANGELOG.md), [packages/tui/CHANGELOG.md](https://github.com/can1357/oh-my-pi/blob/main/packages/tui/CHANGELOG.md), [PR #330](https://github.com/can1357/oh-my-pi/pull/330)
- Upstream Pi has grown packages that omp does not have under those names (`chord`, `codemode`, `durable`, `env`, `evals`, `mcp`, `telemetry`). omp has its own packages instead, including `natives`, `mnemopi`, `snapcompact`, `omptype`, `collab-web`, `metaharness` and `wire`. — [earendil-works/pi packages/](https://github.com/earendil-works/pi/tree/main/packages), [omp README monorepo table](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- Maturity signals:
  - SECURITY.md: "Only the latest release is supported with security updates … Reports are handled on a best-effort basis." — [.github/SECURITY.md](https://github.com/can1357/oh-my-pi/blob/main/.github/SECURITY.md)
  - PRs are "temporarily open to everyone as a trial"; a vouch requirement previously applied.
  - The robomp bot "treats actionable issues as work to pick up".
  - AI-assisted PRs must contain a human-written sentence.

  — [CONTRIBUTING.md](https://github.com/can1357/oh-my-pi/blob/main/CONTRIBUTING.md)

### Inferences
- omp is a hard fork with one-way compatibility. It can load most Pi extensions through shims, but its internals (tool factories, auth store, discovery, session format extensions) have diverged substantially. Full upstream merges stopped around March 2026, and only selective cherry-picks have happened since.
- The project is effectively a single-author, company-backed codebase. Two-thirds of the non-inherited commits come from can1357 or the project bot. The weekly commit volume (hundreds to ~2,000 per week) implies heavy agent-generated development.
- "Maturity" here means feature-rich but in flux, not stable. Version numbers move by a major release roughly monthly.

### Gaps
- Funding, investors and headcount for Stencil Labs: none found (the search returned unrelated "Stencil" companies).
- I found no Hacker News or Reddit discussion threads specifically about oh-my-pi; search results were unrelated.
- The exact date and terms of Earendil's acquisition of Pi rest on secondary sources.

## 2. Architecture: agent loop, tools, system prompt, context and compaction, memory, sessions, sub-agents, background jobs, gateways, observability, state

### Takeaway
omp keeps Pi's layered design (pi-ai provider layer → pi-agent-core loop → coding-agent session/CLI) and adds a very large surface on top:
- 31 built-in tools, with hashline anchored edits as the default edit format;
- regex "time-traveling" stream rules (TTSR);
- multi-method compaction, including bitmap "snapcompact";
- pluggable memory;
- JSONL tree sessions;
- in-process subagents with optional workspace isolation;
- an "advisor" second-model reviewer;
- a vibe-mode director/worker pattern;
- OTLP export.

It has no chat gateway (Telegram/Slack) and no cron scheduler.

### Cited Findings
- **Layering.** `@oh-my-pi/pi-ai` is the multi-provider LLM client, `pi-agent-core` is the "agent runtime with tool calling and state management", `pi-coding-agent` is the CLI and SDK, `pi-tui` is the terminal UI, and `pi-natives` holds the N-API bindings. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- **Boot flow.** `cli.ts` → `main.ts` → `createAgentSession(...)` (`sdk.ts` → `AgentSession`), which then runs `InteractiveMode`, `runPrintMode` or `runRpcMode`. — [packages/coding-agent/DEVELOPMENT.md](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/DEVELOPMENT.md)
- **Agent loop.**
  - A turn is one LLM call plus its tool executions. The event sequence is `agent_start → turn_start → message_start/update/end → tool_execution_start/update/end → turn_end → … → agent_end`.
  - `continue()` resumes from the current context for retries.
  - Messages flow `AgentMessage[] → transformContext() → convertToLlm() → LLM`.
  - "Steering messages are checked after each tool call by default"; `interruptMode: "wait"` defers them to the end of the turn.
  - `followUp()` queues work after the agent would stop, and `queueMode` is `one-at-a-time` or `all`.

  — [packages/agent/README.md](https://github.com/can1357/oh-my-pi/blob/main/packages/agent/README.md) (implementation in `packages/agent/src/agent-loop.ts`, `agent.ts`)
- **Tool-call handling.** A model-issued `tool_call` hook runs "during argument preparation, before scheduling, `tool_execution_start`, and approval". Replacement input is revalidated and becomes the displayed, persisted and executed call. — [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md). The `edit` tool "is strict, essential, and uses exclusive concurrency". — [docs/tools/edit.md](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/edit.md)
- **Retries.**
  - `AnthropicMessagesClient` retries 408/409/429/5xx and honors `retry-after`.
  - Rate-limit errors are classified as QUOTA_EXHAUSTED (30m backoff or credential rotation), RATE_LIMIT_EXCEEDED (30s), CONCURRENT_LIMIT (5s) or MODEL_CAPACITY_EXHAUSTED (45s ± 15s).
  - Streams have first-event and idle watchdogs, and empty completions trigger `withReplaySafeStreamRetry`.

  — [docs/provider-quirks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/provider-quirks.md)
  - Per-role `retry.fallbackChains` switch model or provider on 429 or quota walls. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- **Built-in tools** listed in the README:
  - Files and search: `read`, `write`, `edit`, `ast_edit`, `ast_grep`, `grep`, `glob`.
  - Runtime: `bash` (in-process coreutils, PTY, background jobs) and `eval` (persistent Python and JS cells that can call back into the agent's tools).
  - Code intelligence: `lsp`, `debug` (DAP), `security_scan`.
  - Coordination: `task`, `wait`, `todo`, `ask`.
  - Desktop and web: `browser`, `computer`, `web_search`, `github`, `generate_image`, `tts`.
  - Memory and skills: `checkpoint`, `rewind`, `retain`, `recall`, `reflect`, `memory_edit`, `learn`, `manage_skill`.

  Several are "setting-gated, off by default". Rarely used tools sit behind `xd://` devices. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md). The tool registry is `BUILTIN_TOOLS`/`HIDDEN_TOOLS` in `src/tools/index.ts`. — [DEVELOPMENT.md](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/DEVELOPMENT.md)
- **Hashline anchored edit tool.**
  - `edit` defaults to `hashline` mode. Each `[PATH#TAG]` section "MUST copy the four-uppercase-hex snapshot tag from the latest anchored `read`, `grep`, or successful `edit` result", and "Hashline rejects untagged anchored edits at application time".
  - The available modes are `hashline`, `apply_patch`, `patch`, `replace` and `sloppy`. Some model families (Kimi, MiMo, MiniMax, DeepSeek, StepFun, Codex Spark, GLM 5.3 Flash) fall back to `replace`.
  - The engine is the Rust crate `pi-edit`, and there are constrained-decoding grammars.

  — [docs/tools/edit.md](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/edit.md)
- **Hashline research** (author's own blog, 2026-02-12). Benchmark: 16 models × 3 edit formats × 3 runs of 180 mutated-React-file tasks. Hashline averaged about +15 points over patch and beat patch in 14 of 16 models. Grok Code Fast 1 went from 6.7% to 68.3%, and Grok 4 Fast used up to 61% fewer output tokens. — [stencil.so/blog/the-harness-problem](https://stencil.so/blog/the-harness-problem) (redirect target of blog.can.ac). YUV.AI relays the same post's figure for Claude Sonnet 4.5 as "+14.4 points". — [yuv.ai](https://yuv.ai/blog/oh-my-pi-omp-explained)
- **System-prompt assembly.**
  - The prompt is an ordered block array. Static, cwd-independent blocks come first. Everything derived from the working directory goes in one trailing `<project-context>` footer: workstation data, context files in `<repo-rules>`, dir-context pointers and similar.
  - On Anthropic, the cache breakpoint sits before the first `<project-context>`, so worktree subagents share the cached prefix.
  - Overrides: `--system-prompt`, `--system-prompt-template` (Handlebars), `SYSTEM.md`, `SYSTEM_TEMPLATE.md`, `--append-system-prompt`, `APPEND_SYSTEM.md`.

  — [docs/system-prompt-customization.md](https://github.com/can1357/oh-my-pi/blob/main/docs/system-prompt-customization.md). Prompts are static `.md` Handlebars templates, never built in code. — [docs/porting-from-pi-mono.md](https://github.com/can1357/oh-my-pi/blob/main/docs/porting-from-pi-mono.md)
- **Context files.**
  - omp discovers `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and the conventions of Cursor, Windsurf, Cline, Codex, OpenCode, Copilot and VS Code.
  - Native `.omp/AGENTS.md` comes from the nearest non-empty `.omp/` directory.
  - `RULES.md` is "converted into an always-apply rule whose full body is carried on every request".
  - Foreign user-level sources are opt-in through `enabledProviders`.

  — [docs/context-files.md](https://github.com/can1357/oh-my-pi/blob/main/docs/context-files.md)
- **TTSR (time-traveling stream rules).** "A regex match aborts the stream mid-token, injects the rule as a system reminder, and retries from the same point … Injections survive compaction." — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md), [docs/ttsr-injection-lifecycle.md](https://github.com/can1357/oh-my-pi/blob/main/docs/ttsr-injection-lifecycle.md)
- **Compaction triggers** (six): manual `/compact`, overflow recovery, `stopReason === "length"` recovery, post-turn threshold, mid-turn threshold before the next provider request, and idle. — [docs/compaction.md](https://github.com/can1357/oh-my-pi/blob/main/docs/compaction.md)
- **Compaction methods.** The default `compaction.methodOrder` is `["remote", "snapcompact", "handoff", "shake", "soft"]`.
  - `remote` uses provider-native server compaction (OpenAI Responses compact, Anthropic compaction beta).
  - `snapcompact` prints the discarded history onto PNG bitmap frames for vision-capable models.
  - `shake` replaces tool results with recoverable `artifact://` references.
  - `handoff` generates a handoff document, which can also be saved to disk via `compaction.handoffSaveToDisk`.
  - Async speculative compaction starts before the threshold, and `keepRecentTokens` defaults to 20000.
  - An experimental "notes-backed context windows" mode adds `context_notes` (a 16,384-byte notebook), `new_context` rollover, and `history://current/full` retrieval.

  — [docs/compaction.md](https://github.com/can1357/oh-my-pi/blob/main/docs/compaction.md)
- **Memory.** Memory is disabled by default. Backends are `local` (project-scoped summaries and lessons from persisted sessions), `hindsight` (remote), `mnemopi` (local SQLite) and `sharpshooter` (friction-gated decision files). At session start a "Memory Guidance" block is injected. `memory://` URLs and the `retain`/`recall`/`reflect`/`learn` tools provide access. — [docs/memory.md](https://github.com/can1357/oh-my-pi/blob/main/docs/memory.md)
- **Session persistence.**
  - Sessions are JSONL trees (`id`/`parentId` plus a leaf pointer) stored at `~/.omp/agent/sessions/<encoded-cwd>/<timestamp>_<sessionId>.jsonl`.
  - Blobs are content-addressed at `~/.omp/agent/blobs/<sha256>`.
  - Titles and recaps are indexed in `history.db`.
  - Sessions can branch, fork and resume.

  — [docs/session.md](https://github.com/can1357/oh-my-pi/blob/main/docs/session.md)
- **Sub-agents.**
  - The `task` tool fans out batches of subagents with a required shared `context`, a per-item `outputSchema` for schema-validated structured results (`permissive`/`strict`), and `agent://<id>` / `agent://<id>/<json-path>` output addressing.
  - Background jobs are available via `async.enabled`. Agents can be kept alive, idle or parked, and revived.
  - `isolated` workspaces are built through `pi-iso`: overlayfs, btrfs, zfs, reflink, APFS, projfs or recursive copy. Results merge back as patch or branch.
  - `task.maxRecursionDepth` defaults to 2.

  — [docs/tools/task.md](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md), [docs/task-agent-discovery.md](https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md)
- **Agent Hub** (`Alt+A`) is a TUI roster for watching, steering, reviving and killing subagents. — [docs/agent-hub.md](https://github.com/can1357/oh-my-pi/blob/main/docs/agent-hub.md)
- **Vibe mode** (`/vibe`, interactive TUI only) makes the top-level session a "director". Its tools shrink to `read`, an optional `todo`, and `vibe_spawn`, `vibe_send`, `vibe_wait`, `vibe_kill` and `vibe_list`, which drive persistent `fast` (`@smol`) and `good` (`@task`) worker sessions. Worker results self-deliver. Its rule: "worker completion means the turn settled, not that its claims are correct". — [docs/vibe-mode.md](https://github.com/can1357/oh-my-pi/blob/main/docs/vibe-mode.md)
- **Advisor / watchdog.**
  - Optional reviewer model(s) receive each new transcript delta. They have their own `Agent` and `ToolSession`; the default tools are `read`, `grep` and `glob`.
  - Advisors inject notes through an `advise` tool at severity `nit`, `concern` or `blocker`.
  - A `WATCHDOG.yml` roster defines named advisors with their own models, tools, cadence and budgets.
  - An emission guard normalizes notes, filters content-free phrases ("lgtm", "done"), dedupes by severity, and caps notes per update (default 4).
  - `advisor.immuneTurns` (default 3) rate-limits interrupting concerns.
  - Advisors have backup-reviewer fallback chains.
  - Advisors are disabled by default and off under RPC/ACP unless the host opts in.

  — [docs/advisor-watchdog.md](https://github.com/can1357/oh-my-pi/blob/main/docs/advisor-watchdog.md)
- **Background work.**
  - The `wait` tool plus `proc://` and `agent://` URLs cover background jobs, supervised services in `bash`, and agent messaging (added in 18.3.0, 2026-09-24). — [coding-agent CHANGELOG](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/CHANGELOG.md)
  - `omp ps` lists "daemon-supervised background processes". — [docs/cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
  - Extensions get managed timers `ctx.setInterval`/`ctx.setTimeout`. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Chat gateways.** No Telegram, Slack or Discord gateway appears in the source; a repo-wide grep for "telegram" matched only a glyph table. The remote-access features are `/collab`, which shares a live session through a relay with browser joining at `my.omp.sh` and frames "sealed client-side", and ACP for editors such as Zed. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md), [docs/collab.md](https://github.com/can1357/oh-my-pi/blob/main/docs/collab.md)
- **Observability.**
  - `telemetry.otlpExportEnabled` defaults to true and exports traces, logs and metrics only when `OTEL_*` endpoints are set. — [telemetry-settings.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/telemetry-settings.ts)
  - The `omp-stats` package is a "local observability dashboard"; `omp usage` and `/dump` also exist. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md), [cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- **Outbound data by default.**
  - Auto-QA "grievance" reporting (`dev.autoqa`) is "Enabled by default". In the TUI it asks for consent once; after consent it pushes to `qa.omp.sh`. Non-interactive runs default consent to false, but `PI_AUTO_QA_PUSH=1` forces pushing. — [src/tools/report-tool-issue.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/tools/report-tool-issue.ts)
  - Every catalog refresh contacts `catalog.stencil.so`, with "no setting to disable it" according to an open issue. — [Issue #10934](https://github.com/can1357/oh-my-pi/issues/10934)
  - A persistent install UUID feeds provider device metadata, including the derived Claude `device_id`. — [docs/install-id.md](https://github.com/can1357/oh-my-pi/blob/main/docs/install-id.md)
- **State storage.** Credentials live in SQLite `agent.db` via `bun:sqlite`, or in a remote auth broker. Sessions are JSONL; there is also a blob store and `history.db`. — [docs/porting-from-pi-mono.md](https://github.com/can1357/oh-my-pi/blob/main/docs/porting-from-pi-mono.md), [docs/session.md](https://github.com/can1357/oh-my-pi/blob/main/docs/session.md)

### Inferences
- The agent loop is a classic stream-then-execute-tools loop with explicit steer and follow-up queues. That queue model is what makes external event injection first-class; contrast Claude Code, where Saga resorts to `tmux send-keys`.
- Subagents run as in-process or subprocess child sessions sharing the host and credentials. Their "isolation" is filesystem copy-on-write for merge hygiene, not a security boundary. That makes them structurally different from Saga's one-container-per-dvergr model.

### Gaps
- I did not read `agent-loop.ts` line by line. Parallel tool execution semantics beyond "exclusive concurrency" for `edit` are not fully characterized here.
- I did not verify the README's claim of 23 web-search backends or its LSP/DAP op counts.

## 3. Extension model: extensions API, hooks and lifecycle events, skills, AGENTS.md, MCP, custom tools, configuration

### Takeaway
An extension is a TypeScript/JS module with a default-export factory receiving `ExtensionAPI`. It can register tools, commands, providers and renderers, subscribe to about 50 lifecycle events, and inject messages with typed delivery semantics. Hooks are the same mechanism, loaded from `hooks/pre|post` directories. Skills use `SKILL.md` folders compatible with Claude, Codex and Agents layouts. omp is an MCP client; I found no MCP-server mode. Configuration is YAML.

### Cited Findings
- **Extension surface.** An extension module may combine event handlers (`pi.on`), LLM-callable tools (`pi.registerTool`), slash commands, shortcuts, flags, renderers, and the "session/message injection APIs (`sendMessage`, `sendUserMessage`, `appendEntry`)". Core methods also include:
  - `exec`, `setActiveTools`, `setModel`, `setThinkingLevel`;
  - `registerProvider`;
  - `registerFileWriteFallback`;
  - a shared `events` bus.

  — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Isolation.** "Extensions run in-process with no isolation." A throw from a raw timer "tears down the whole session". Use `ctx.setInterval`/`ctx.setTimeout`, which are contained, `unref`'d, and cleared on `session_shutdown`. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Message delivery semantics.**

  | `deliverAs` | Behavior |
  |---|---|
  | `steer` | Default while streaming; steers the current run. |
  | `followUp` | Queued behind the current run. |
  | `nextTurn` | Held for the next turn; when idle without `triggerTurn` it is appended to context without starting a turn. |
  | `aside` | Injected at the next step boundary without interrupting the current tool batch. |

  - `triggerTurn: true` starts a turn when idle.
  - `pi.sendUserMessage(content, { deliverAs, attribution })` records the message as `attribution: "user"` unless `attribution: "agent"` is passed ("use 'agent' for text … relayed from another agent").

  — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Event names**, per `docs/extensions.md` and `docs/hooks.md`:
  - Session: `session_start`, `session_before_switch`, `session_switch`, `session_before_branch`, `session_branch`, `session_before_compact`, `session.compacting`, `session_compact`, `session_before_tree`, `session_tree`, `session_shutdown`.
  - Prompt and turn: `input`, `before_agent_start`, `before_provider_request`, `after_provider_response`, `context`, `agent_start`, `agent_end`, `session_stop`, `cache_warming_decision`, `turn_start`, `turn_end`, `assistant_message`, `message_start`, `message_update`, `message_end`.
  - Tool: `tool_call`, `tool_result`, `tool_execution_start`, `tool_execution_update`, `tool_execution_end`, `tool_approval_requested`, `tool_approval_resolved`.
  - Plan: `plan_review_requested`, `plan_review_resolved`.
  - Subagent: `before_subagent_spawn`.
  - Reliability: `auto_compaction_start`, `auto_compaction_end`, `auto_retry_start`, `auto_retry_end`, `retry_fallback_applied`, `retry_fallback_succeeded`, `ttsr_triggered`, `todo_reminder`, `goal_updated`, `credential_disabled`.
  - MCP: `mcp_notification`.
  - User command interception: `user_bash`, `user_python`.
  - `resources_discover`, which is typed but "there are no `AgentSession` callsites invoking it".

  — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md), [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md)
- **`session_stop`.** This is the "main-session stop hook, awaited before settle". Returning `{ continue: true, additionalContext }` requests a continuation, "capped at 8 continuations". "Explicit `{ decision: "block", reason }` refusals … do not consume that allowance, and remain blocking until the hook allows completion or the operator interrupts." The hook never fires for subagent sessions. The type carries `stop_hook_active`, `turn_id`, `last_assistant_message`, `session_id` and `session_file`, and the result type is commented "Claude/Codex-compatible block decision". — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md), [src/extensibility/shared-events.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/extensibility/shared-events.ts)
- **Tool hooks.**
  - `tool_call` can return `{ block, reason, input, additionalContext }`. Handler errors fail closed.
  - `tool_result` can patch `content`, `details` and `isError` and add `additionalContext`, which is delivered as "trusted handler-authored instructions … with developer/system priority".

  — [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md)
- **MCP notifications to steering.** `mcp_notification` delivers every JSON-RPC notification from connected MCP servers, buffered with a cap of 100. The docs give an example of bridging a push-capable MCP server into `pi.sendUserMessage(..., { deliverAs: "steer", attribution: "agent" })`. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Ephemeral side turns.** `ctx.runEphemeralTurn({ promptText, tools: false, maxTokens, maxContextBytes, onTextDelta })` runs a `/btw`-style side query over the current context without touching history. The docs use a NATS bridge answering another agent as the example. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Hook discovery.** Hooks are loaded from `.omp/hooks/pre|post/*.ts|js` and `~/.omp/agent/hooks/pre|post/` as extension modules ("This mirrors `.claude/hooks/pre|post/`"). — [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md). The Claude discovery provider loads TS/JS hook factories from `.claude/hooks/pre/` and `.claude/hooks/post/`. — [src/discovery/claude.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/discovery/claude.ts)
- **Skills.** "file-backed capability packs" at `<skills-root>/<name>/SKILL.md`, discovered from native, Claude, Codex, Agents and plugin roots. They are exposed as name and description in the system prompt, as on-demand `skill://` reads, and as `/skill:<name>` commands. — [docs/skills.md](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md). `omp skills` installs and publishes via skills.omp.sh. — [docs/cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- **MCP client.** Server definitions become callable `mcp__<server>_<tool>` tools. Configs are discovered from `.mcp.json` and other tools' files, and connected servers' `instructions` are appended to the system prompt. — [docs/mcp-server-tool-authoring.md](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-server-tool-authoring.md). Transports and lifecycle are documented separately. — [docs/mcp-protocol-transports.md](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-protocol-transports.md), [docs/mcp-runtime-lifecycle.md](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-runtime-lifecycle.md)
- **No MCP-server mode.** The CLI subcommand list includes `acp`, `auth-broker`, `auth-gateway`, `plugin` and `skills`, but no MCP-server subcommand. — [docs/cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- **Custom tool parameters** accept omptype (ArkType-compatible) schemas, a Zod-compatible builder (`pi.zod`), or a legacy TypeBox shim. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md), [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md)
- **Configuration.**
  - YAML files: `~/.omp/agent/config.yml`, project `.omp/config.yml`, `~/.omp/agent/models.yml` (custom providers in 13 wire-API styles), `WATCHDOG.yml`, and `--config <file>` overlays.
  - Precedence is env > runtime > overlay > project > global > default.

  — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md), [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Plugins and packages.** `omp plugin install`, a marketplace, npm publishing, and `/reload-plugins`. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md), [docs/marketplace.md](https://github.com/can1357/oh-my-pi/blob/main/docs/marketplace.md)

### Inferences
- omp's hook model is code (TS/JS modules in-process), not Claude Code's shell-command `settings.json` hooks. I grepped for `PreToolUse`, `PostToolUse` and `UserPromptSubmit` in `packages/coding-agent/src` and found no matches, so existing Claude Code command hooks (such as Saga's `dvergr-hooks/*.sh`) would not run as-is. They would need a thin TS extension calling `pi.exec()` on the scripts.
- `session_stop` deliberately mirrors Claude Code's Stop-hook contract (`decision: "block"`, `reason`, `stop_hook_active`). That is the mechanism the official `/ralph-loop` plugin relies on, so porting the Ralph pattern is straightforward.

### Gaps
- I did not verify MCP OAuth/auth handling or exactly which transports are supported (stdio, HTTP, SSE) beyond the documents' existence.
- I did not read `gemini-manifest-extensions.md`. Gemini-style extension manifests are documented there.

## 4. Autonomy and unattended operation: headless/RPC/server modes, loop and goal modes, Docker without TTY, first-run prompts, config needed

### Takeaway
omp is built to be driven by another program:
- Print/JSON one-shot (`-p`, `--mode json`).
- A typed NDJSON RPC protocol over stdio, with generated Python, Rust and Go clients, host-owned tools and URI schemes, steer/follow-up commands, and explicit "settled" signals.
- ACP.
- An embeddable SDK.

Built-in loop constructs are `/loop` (TUI-only, with shell-exit-code gating) and "goal mode" (TUI, and RPC when opted in). The first-run setup wizard runs only in an interactive TTY and can be disabled. The project ships its own Docker image recipe and a reference containerized orchestrator, robomp.

### Cited Findings
- **Entry points.** "`omp` runs the TUI. `omp -p` answers a single prompt and exits. The Node SDK embeds the session in your process. `omp --mode rpc` and `omp acp` hand the wheel to another program over stdio." — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- **Non-TTY behavior.** "Piped input or a non-TTY stdin selects print mode when `--mode` is omitted". `--mode json` emits NDJSON events, and `--no-session` makes a session ephemeral. — [docs/cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- **RPC protocol.**
  - It is "a custom JSONL protocol, not JSON-RPC 2.0". The process writes a `ready` frame, and protocol v2 adds chunked frames.
  - Commands include `prompt`, `steer`, `follow_up`, `abort`, `abort_and_prompt`, `new_session`, `open_session`, `get_state`, `goal`, `set_host_tools`, `set_host_uri_schemes`, `set_subagent_subscription`, `cancel_subagent` and `set_event_filter`.
  - Each prompt completes exactly once via the response or a later `prompt_result`; `session_settled` signals quiescence.
  - Under stdout backpressure the server spills to a temp file.

  — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **Host-owned tools.** `set_host_tools` registers tools that "the RPC server may call back into over stdio" before the next model call. Host URI schemes are also supported. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **Generated clients.** Clients for Python (`omp-rpc`, package `omp_rpc`), Rust and Go are generated from a JSON Schema wire bundle. They offer `prompt_and_wait`/`PromptAndWait`, host-tool serving, and v2 chunk reassembly. Python example: `RpcClient(provider="anthropic", model=...)` then `client.prompt_and_wait(...)`. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **RPC defaults.** RPC disables auto-title generation (`PI_NO_TITLE=1`), and `rpc-ui` sets `PI_NO_PTY=1`. RPC and ACP pin "neutral defaults" for task isolation, memory and advisor settings. `--no-ui` makes extensions headless. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **`/loop`.**
  - Usage: `/loop [count|duration] [--while|--until '<cmd>'] [prompt]`. "While enabled, the next prompt you send re-submits after every yield … the command's exit status decides whether the next iteration runs."
  - `loop.mode` controls what happens between iterations: `prompt` (re-submit as a follow-up), `compact` (compact, then re-submit) or `reset` (new session, then re-submit).
  - `loop.conditionTimeoutMs` defaults to 30,000.
  - The command is implemented with `handleTui`, so it is interactive-TUI.

  — [src/slash-commands/builtin-modes.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/slash-commands/builtin-modes.ts), [src/modes/settings.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/modes/settings.ts)
- **Goal mode.**
  - Entry points: `/goal`, `--goal <objective>` (interactive only), and the RPC `goal` op (`get|create|resume|pause|drop`, with an optional `token_budget`).
  - Over RPC, goals do not auto-continue "unless `goal.continuationModes` contains `"rpc"`". The default is `["interactive"]`.
  - Continuation "stops after a goal turn with no new tool activity".
  - `abort` pauses the goal.
  - When completed, the `goal` tool is removed.

  — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md), [src/goals/settings.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/goals/settings.ts), [docs/cli-reference.md](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md)
- **Headless advisor.** `omp -p --advisor "..."` enables the advisor for one print-mode run. The process waits up to 10 minutes for final reviews before disposing. — [docs/advisor-watchdog.md](https://github.com/can1357/oh-my-pi/blob/main/docs/advisor-watchdog.md)
- **First-run.** The setup wizard is lazy-loaded only when the stored setup version is stale, or when forced or splashed. Scene selection receives `isTTY: process.stdin.isTTY && process.stdout.isTTY` and `setupWizardEnabled: cfgStartupSetupWizard`, and the wizard runs inside interactive mode. — [src/main.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/main.ts). The `startup.setupWizard` setting defaults to true ("Show newly added onboarding steps once per setup version"). — [docs/settings.md](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md)
- **Docker image.** The repo `Dockerfile` builds `oh-my-pi/pi:dev`: a natives builder (Rust and Bun), an `omp_rpc` wheel, and a python:3.12-slim base with Bun and an `omp` shim. "docker run --rm -it -v "$PWD":/work oh-my-pi/pi:dev cli # interactive omp". — [Dockerfile](https://github.com/can1357/oh-my-pi/blob/main/Dockerfile)
- **robomp reference orchestrator.**
  - A FastAPI service with a sqlite event queue (deduped on `X-GitHub-Delivery`) and a `WorkerPool` that "spawns `omp --mode rpc` with `cwd=worktree`".
  - The worker container "Holds the HMAC key, never the PAT". A sibling **gh-proxy** container on an `internal: true` network holds `GITHUB_TOKEN`, verifies HMAC-signed requests, and has "Only egress to `api.github.com`".
  - Host tools are "the exclusive surface for GitHub writes", and every host-tool call is "audited into the `tool_calls` table with credential-redacted args".
  - Follow-ups resume the same session via `--continue`.
  - The model is drawn from a LiteLLM-style proxy configured in `models.yml`.

  — [python/robomp/README.md](https://github.com/can1357/oh-my-pi/blob/main/python/robomp/README.md), [Dockerfile.robomp](https://github.com/can1357/oh-my-pi/blob/main/Dockerfile.robomp)
- **Credentials for containers.** `omp auth-broker serve` holds refresh tokens in SQLite and refreshes them. `omp auth-gateway serve` is a forward proxy, so "Clients (containerised omp, llm-git, … robomp containers) never see the access token". — [docs/auth-broker-gateway.md](https://github.com/can1357/oh-my-pi/blob/main/docs/auth-broker-gateway.md)
- **Config needed for unattended runs.** Either credentials via `/login` (stored in `agent.db`) or env keys (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), plus optional `config.yml` and `models.yml`. `PI_CODING_AGENT_DIR` relocates the agent dir, and profiles use `~/.omp/profiles/<name>/agent`. — [docs/providers.md](https://github.com/can1357/oh-my-pi/blob/main/docs/providers.md), [docs/context-files.md](https://github.com/can1357/oh-my-pi/blob/main/docs/context-files.md)
- **Approvals.** The default approval mode is `yolo` (auto-approve read, write and exec), so unattended runs do not block on approvals. — [docs/approval-mode.md](https://github.com/can1357/oh-my-pi/blob/main/docs/approval-mode.md)

### Inferences
- For a dvergr-style container, the cleanest shape is a host process speaking RPC; robomp is a working in-repo precedent. The second option is an interactive TUI in tmux with an extension implementing the loop via `session_stop`. Neither needs the pre-captured onboarding JSON that Saga uses for Claude Code: set `startup.setupWizard: false`, or run non-TTY/RPC.
- Goal mode's "stop after a turn with no new tool activity" and `/loop --until '<cmd>'` are built-in equivalents of Saga's convergence and plateau checks.

### Gaps
- I did not verify end to end whether interactive omp inside a no-network or firewalled container stalls on version checks (`versionCheckPromise` exists in `main.ts`) or on catalog fetches. Testing was out of scope.

## 5. Models and auth/billing: providers, Claude subscription OAuth versus Anthropic's April 2026 policy, ChatGPT subscription, Google, local models, cost controls

### Takeaway
omp supports 60+ providers, including local engines. It does support Claude Pro/Max OAuth, but only by impersonating Anthropic's first-party clients:
- a Claude Code user agent and system identity line;
- the "Cowork `claude-desktop` request profile" with "billing attestation";
- auto-bumping the spoofed version when rejected.

That is exactly what Anthropic's guidance prohibits ("misrepresent their identity"). After April 4, 2026, genuine third-party harness traffic bills as pay-as-you-go extra usage. omp's documentation says nothing about this policy. For Saga's hard constraint, omp provides no legitimate Max-subscription billing path for Claude.

### Cited Findings
- **Providers.** The README lists Anthropic `oauth`, OpenAI, OpenAI Codex `oauth`, Google Gemini/Vertex, Google Antigravity `oauth`, xAI, Bedrock and Azure, plus coding plans (Cursor `oauth`, GitHub Copilot `oauth`, Kimi, MiniMax, Z.AI, etc.). Local options are Ollama, LM Studio, llama.cpp, vLLM and LiteLLM. Custom `models.yml` providers can use 13 wire APIs.
  - Model routing uses nine roles: `default`, `smol`, `slow`, `plan`, `commit`, `vision`, `task`, `advisor`, `tiny`.
  - Routing extras: fallback chains, path-scoped models, and round-robin credentials.

  — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- **Claude Code impersonation in the Anthropic OAuth path.**
  - OAuth "uses `getClaudeCodeUserAgent()` … `claude-cli/<version> (external, cli)`, with fallback version `2.1.280`… a newer version required by a server rejection can be adopted".
  - "Billing attestation and metadata use `generateClaudeCloakingUserId`, `deriveClaudeDeviceId`…".
  - `buildAnthropicSystemBlocks` "automatically prepends … 'You are Claude Code, Anthropic's official CLI for Claude.' as system[0] for OAuth credentials".
  - Custom tool names get a `_` prefix under OAuth.
  - The streaming path uses `buildClaudeCodeTlsFetchOptions`.

  — [docs/provider-quirks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/provider-quirks.md), [packages/ai/src/providers/claude-code-fingerprint.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/ai/src/providers/claude-code-fingerprint.ts). A maintenance script is named `scripts/check-spoofed-versions.ts`. — [scripts/](https://github.com/can1357/oh-my-pi/tree/main/scripts)
- **Changelog history of the OAuth path.**
  - ai 17.2.1 (2026-07-30): "Anthropic OAuth requests now reproduce Cowork's current `claude-desktop` request profile, including client/runtime metadata, beta selection, system and billing attestation, the 64K output cap, and stable HTTP/1.1 header ordering."
  - ai 18.0.7 (2026-08-26): "Fixed Anthropic Claude subscription OAuth requests being rejected by the upstream service (#9801)".

  — [packages/ai/CHANGELOG.md](https://github.com/can1357/oh-my-pi/blob/main/packages/ai/CHANGELOG.md). PR #9801's body: "align the Cowork fingerprint with Claude Code 2.1.246 and its bundled Anthropic SDK 0.112.1"; before the fix, `anthropic/claude-opus-5` returned HTTP 403. — [PR #9801](https://github.com/can1357/oh-my-pi/pull/9801)
- **Usage-limit handling on Claude subscriptions.** omp tracks rolling `five_hour` and `seven_day` windows via `api.anthropic.com/api/oauth/usage` and rotates credentials on quota exhaustion. — [docs/provider-quirks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/provider-quirks.md). Its `usageLimit` state reports `wrap_up` or `low_priority` stages and "whether `extraUsage` follows. Claude subscriptions are the only producer today". — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md). "Claude Extra Usage" USD reporting was added in ai 17.1.1 (2026-07-24). — [packages/ai/CHANGELOG.md](https://github.com/can1357/oh-my-pi/blob/main/packages/ai/CHANGELOG.md). `providers.anthropic.slowMode` offers "Anthropic subscription low-priority recovery when a 5-hour limit is reached". — [docs/settings.md](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md)
- **Anthropic's April 2026 change.** On April 4, 2026 (12pm PT), Anthropic stopped letting Claude subscriptions cover third-party harnesses. Enforcement started with OpenClaw and was to "roll out to more shortly". Such usage now bills as pay-as-you-go "extra usage", and API users were unaffected. — [Computerworld](https://www.computerworld.com/article/4154440/anthropic-cuts-openclaw-access-from-claude-subscriptions-offers-credits-to-ease-transition-2.html), [TechRadar](https://www.techradar.com/pro/bad-news-claude-users-anthropic-says-youll-need-to-pay-to-use-openclaw-now), [Hongkiat](https://www.hongkiat.com/blog/anthropic-closed-openclaw-loophole/)
- **Earlier policy.** Anthropic's Feb 19, 2026 documentation said Free/Pro/Max OAuth tokens are only for Claude Code and Claude.ai. — [Gigazine](https://gigazine.net/gsc_news/en/20260220-anthropic-third-party-block)
- **Open issue #12487** (2026-09-19, one comment, no maintainer reply visible) summarizes Anthropic's current guidance: "Third-party tools that misrepresent their identity to Anthropic's servers, attempt to route third-party traffic against subscription limits … are prohibited and may be enforced against". It states that omp "sends a `User-Agent: claude-code/<version>` fingerprint while OMP itself is not Claude Code". It also notes Google explicitly prohibits third-party use of Antigravity and Gemini CLI OAuth. — [Issue #12487](https://github.com/can1357/oh-my-pi/issues/12487)
- I grepped omp's `docs/` for Anthropic subscription policy terms ("third-party", "first-party", "terms of service") and found no statement about Anthropic's subscription policy. — [docs/](https://github.com/can1357/oh-my-pi/tree/main/docs)
- **Upstream Pi** also still ships Anthropic OAuth ("Anthropic (Claude Pro/Max subscription)") with code commented "Stealth mode: Mimic Claude Code's tool naming exactly" and a `claude-cli/${claudeCodeVersion}` user agent. — [earendil-works/pi packages/ai/README.md](https://github.com/earendil-works/pi/blob/main/packages/ai/README.md), [earendil-works/pi anthropic-messages.ts](https://github.com/earendil-works/pi/blob/main/packages/ai/src/api/anthropic-messages.ts)
- **Pi users' experience.** A Pi user was told usage through Pi "is billed through the API rather than charged to his Max subscription". — [yage.ai](https://yage.ai/share/pi-coding-agent-locked-out-en-20260518.html). Composio advises API keys for account safety and reports the omp author "had his Gemini account disabled while running benchmarks". — [Composio](https://composio.dev/content/pi-vs-omp). The author's own post: Google "Disabled" his Gemini account with no stated reason. — [stencil.so/blog/the-harness-problem](https://stencil.so/blog/the-harness-problem)
- **OpenAI.** omp supports ChatGPT-subscription Codex OAuth (`openai-codex`, Responses API against `chatgpt.com/backend-api/codex/responses`). — [docs/provider-quirks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/provider-quirks.md). Secondary reports say OpenAI permits ChatGPT-plan use in third-party tools (OpenCode Codex auth since Jan 2026) and launched a "Sign in with ChatGPT" program for third-party developer tools. — [DevGenius](https://blog.devgenius.io/jump-ship-in-minutes-codex-oauth-now-works-in-opencode-d2708c32f571), [The New Stack](https://thenewstack.io/sign-in-with-chatgpt/)
- **Cost controls.** Goal mode accepts `token_budget`. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md). Thinking budgets and a status-line cost segment are configurable. — [docs/settings.md](https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md)

### Inferences
- If Saga ran Odin or dvergar on omp with Claude OAuth, it would either violate Anthropic's stated terms (impersonation, with ban risk to the operator's single Max account that all Saga agents share) or, if detected as third-party, be billed as extra usage. Neither satisfies Saga's "bill to Max subscription" constraint legitimately. The only policy-clean Claude path in omp is an API key, billed per token.
- omp is policy-viable for non-Anthropic workers: OpenAI ChatGPT-plan OAuth (subject to OpenAI's terms), API-key providers (DeepSeek, etc.), and local models on homelab hardware.

### Gaps
- I could not determine whether omp's spoofed Claude OAuth traffic is currently billed against plan limits or as extra usage. That would require a live test with an account, which I did not do.
- I found no reports of Anthropic suspending omp users specifically.
- I found no hard dollar spend cap in `docs/settings.md`, only token budgets and usage reporting.
- Whether omp or Pi is among OpenAI's "Sign in with ChatGPT" launch partners: not determined (the article body did not load).

## 6. Security and sandboxing: permission model, sandboxing, secrets, network controls

### Takeaway
omp's permission model is a tiered approval system that defaults to **yolo**, meaning everything is auto-approved. It loads project-supplied extensions, hooks, tools and MCP config without a trust prompt. Extensions run in-process with no isolation. I found no OS-level sandbox and no network egress controls. Secret obfuscation and the auth broker/gateway are the main protective features, and both are opt-in.

### Cited Findings
- **Approval tiers and modes.** Tiers are `read`, `write` and `exec`. Modes are `always-ask`, `write` and `yolo`, with "`yolo` (default)" auto-approving all three. Per-tool `allow`/`deny`/`prompt` policies apply. Unknown custom tools default to `exec`, and MCP tools are declared `write`. — [docs/approval-mode.md](https://github.com/can1357/oh-my-pi/blob/main/docs/approval-mode.md)
- **Project trust.** "Opening a repository loads its project inputs by design: settings, extensions, hooks, tools, commands, skills, rules, and project MCP configuration." Mitigations are `--no-extensions` and `--trusted-extension <path>`. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md). `ctx.isProjectTrusted()` is "always `true`; OMP does not ask for per-directory trust before loading project inputs". — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Extension isolation.** "Extensions run **in-process with no isolation**." — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **No OS sandbox found.** A grep of `packages/coding-agent/src`, `crates` and `docs` for landlock, bubblewrap/bwrap, seatbelt and sandbox-exec found no sandbox implementation. Task "isolation" means workspace copy/overlay backends (overlayfs, reflink, etc.) for merging changes. — [docs/tools/task.md](https://github.com/can1357/oh-my-pi/blob/main/docs/tools/task.md)
- **Upstream contrast.** Pi documents running inside plain Docker, Docker Sandboxes, OpenShell or a Gondolin micro-VM extension. — [earendil-works/pi containerization.md](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/containerization.md)
- **Secret obfuscation.**
  - "Disabled by default".
  - When enabled, it collects env vars with secret-like names, `secrets.yml`, and regexes for common token shapes. It replaces them with reversible `$$HASH$$` placeholders in provider-visible text and restores them before tool execution.
  - "Static system prompts, static tool definitions, and binary payloads are not redacted."

  — [docs/secrets.md](https://github.com/can1357/oh-my-pi/blob/main/docs/secrets.md)
- **Auth broker/gateway.** Clients never see access tokens. "Transport security between operator, broker, and gateway is delegated to the operator (Tailscale / Wireguard / reverse proxy + TLS)." — [docs/auth-broker-gateway.md](https://github.com/can1357/oh-my-pi/blob/main/docs/auth-broker-gateway.md)
- **Advisor tool grants.** Advisor tools honor `tools.approvalMode`, and a `WATCHDOG.yml` entry "may grant any built-in — including mutating tools". — [docs/advisor-watchdog.md](https://github.com/can1357/oh-my-pi/blob/main/docs/advisor-watchdog.md)
- **Outbound traffic not controlled by the agent:** auto-QA push to `qa.omp.sh` after consent, catalog fetches from `catalog.stencil.so`, and the collab relay. — [report-tool-issue.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/tools/report-tool-issue.ts), [Issue #10934](https://github.com/can1357/oh-my-pi/issues/10934), [docs/collab.md](https://github.com/can1357/oh-my-pi/blob/main/docs/collab.md)
- **Supply chain.** The installer fetches prebuilt binaries from `build.stencil.so` "and check[s] its SHA-256". — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)

### Inferences
- Saga's existing security model is container-per-agent behind the Trail of Bits firewall, with Heimdall as the launch boundary. Saga would still have to provide that model around omp; omp supplies none of it. Inside a dvergr container, yolo and auto-loaded project inputs are acceptable only because the container is the boundary.
- The robomp pattern (worker without secrets, plus an HMAC-verifying credential sidecar with single-destination egress) shows the omp authors already think in container-boundary terms. It closely mirrors Heimdall's role.

### Gaps
- No independent security audit of omp was found.
- I did not inspect `bash` tool interception (`checkBashInterception`) in detail.

## 7. Fit for Saga: (a) Odin, (b) dvergar, (c) patterns worth adopting even if Saga stays on Claude Code

### Takeaway
- **(a) Odin.** Technically omp would be a much better event-driven host for Odin than Claude Code plus tmux: native message injection, RPC, host tools, advisor and director patterns. It fails Saga's billing constraint for Claude (impersonation or extra usage), and it lacks the first-party Telegram channel. Not adoptable for Odin while Odin must be Opus on Max.
- **(b) dvergar.** omp has everything a dvergr needs: `session_stop`, `turn_end` and `agent_end` hooks, `/loop` and goal mode, RPC and headless operation, and Docker recipes. It is a strong candidate only for non-Claude workers (OpenAI plan, API-key, local) under a harness-agnostic Saga.
- **(c) Patterns.** Several are directly portable regardless (listed below).

### Cited Findings
- **External events into turns without tmux.** An extension can call `pi.sendUserMessage(text, { deliverAs: "steer" | "followUp" | "aside" | "nextTurn", attribution: "agent" })` from managed timers or async callbacks. The docs include a worked example bridging pushed MCP notifications into a steer. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md). Alternatively, a host process drives `omp --mode rpc` with `prompt`/`steer`/`follow_up` and waits on `prompt_result` or `session_settled`. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **File inbox/outbox as tools.** `pi.registerTool(...)` in-process. — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md). Or `set_host_tools` / `set_host_uri_schemes` served by the RPC host (Python `omp_rpc` supports host tools). — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **Built-in cross-model reviewer.** The advisor reviews each turn delta on a different model (the advisor role resolves to `slow`, "it does not simply inherit the primary model") and injects `nit`/`concern`/`blocker` notes. — [docs/advisor-watchdog.md](https://github.com/can1357/oh-my-pi/blob/main/docs/advisor-watchdog.md). `ctx.models.family()` exists explicitly to "pick a model from a different family … (e.g. a cross-family reviewer)". — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md)
- **Director pattern.** In vibe mode the director keeps read-only tools and delegates to persistent workers. "The director remains responsible for the final outcome: worker completion means the turn settled, not that its claims are correct." — [docs/vibe-mode.md](https://github.com/can1357/oh-my-pi/blob/main/docs/vibe-mode.md)
- **Post-turn hooks for dvergr status.** `turn_end`, `agent_end` (notification), `session_stop` (awaited, can block or continue), and `tool_result`, with `pi.exec()` available for shell calls (e.g. `mosquitto_pub` or Saga's `post-iteration.sh`). — [docs/extensions.md](https://github.com/can1357/oh-my-pi/blob/main/docs/extensions.md), [docs/hooks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/hooks.md)
- **Loop modes for dvergar.**
  - `/loop … --until '<cmd>'` with `loop.mode` set to `prompt`, `compact` or `reset`. — [builtin-modes.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/slash-commands/builtin-modes.ts), [modes/settings.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/modes/settings.ts)
  - Goal mode with `token_budget`, plus RPC continuation via `goal.continuationModes: ["rpc"]`. — [docs/rpc.md](https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md)
- **Container precedent.** robomp runs `omp --mode rpc` per worktree in Docker, with a secret-holding sidecar and audited host tools. — [python/robomp/README.md](https://github.com/can1357/oh-my-pi/blob/main/python/robomp/README.md)
- **No Telegram.** omp has no Telegram or chat gateway. — repo grep (see Section 2), [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md)
- **Benchmark.** On a 30-task benchmark (DeepSeek V4 Flash, eight harnesses), omp passed 17/30 versus Pi's 20/30. omp's median time was 272s versus 132s, its average tokens 742k versus 559k, and its cost $1.75 versus $0.56. It ranked above Claude Code (16/30) in that run. The reviewer says omp "often over-worked tasks". — [Composio](https://composio.dev/content/pi-vs-omp)

### Inferences

**(a) Could Odin run on omp?**

What Saga would gain:
- Events delivered as typed, attributed messages instead of `tmux send-keys` keystrokes. No more risk of keystrokes landing in dialogs. Explicit idle and settled signals (`isIdle()`, `session_settled`) instead of pane scraping.
- Ratatoskr shrinking into either an omp extension (MQTT client in `session_start`, `sendUserMessage` on message) or an RPC host in Python using `omp_rpc`.
- Mimir's request/verdict files becoming host tools, or Mimir becoming a WATCHDOG.yml advisor on another model family.
- No onboarding-dialog baseline JSON to maintain.

What Saga would lose:
- **Max-subscription billing for Opus.** The only Claude subscription path is impersonation, which policy prohibits and puts the shared Max account at risk. Otherwise it is extra usage or API per-token.
- The first-party Telegram channel plugin; a Telegram bridge would have to be written.
- Anthropic-supported tooling, such as the official `/ralph-loop` plugin.
- Stability: omp ships multiple releases per day and seven breaking-change sections in four weeks.

Net: omp is not adoptable for Odin under the current hard constraint. It is a strong reference design for the operator's option (1), a standalone custom harness, especially if that harness ever runs Odin on a non-Anthropic model or on an API key.

**(b) Could a dvergr run on omp?**

Yes, technically:
- `session_stop` is the Ralph-loop primitive. Its Claude-compatible `decision: "block"` shape means Saga's stop-hook logic ports almost one-for-one into a TS extension that shells out to the existing scripts.
- `turn_end` and `agent_end` can publish MQTT status and journal JSON.
- A guidance file can be polled with `ctx.setInterval` and delivered as `aside` or `followUp`.
- Container startup is clean: RPC or print mode, or TUI with `startup.setupWizard: false`.

Under a harness-agnostic Saga this fits workers on OpenAI-plan, API-key or local models. Claude-based dvergar would hit the same billing wall as Odin.

Required hardening:
- pin the omp version;
- set `dev.autoqa: false` and do not set `PI_AUTO_QA_PUSH`;
- firewall `catalog.stencil.so` and `qa.omp.sh` if undesired;
- set the approval mode deliberately;
- keep Heimdall and the container boundary.

**(c) Patterns worth adopting in Saga's planner even on Claude Code**, each with its omp reference:

1. **Typed delivery modes with attribution** (steer / followUp / aside / nextTurn, and `attribution: "agent"` for relayed text). Ratatoskr could tag every injected message by mode and source, and queue rather than interrupt unless the message is a blocker. Ref: `docs/extensions.md` "Message delivery semantics".
2. **Advisor emission guard for Mimir.** Severity levels (nit/concern/blocker), normalization plus a content-free phrase filter ("lgtm", "done"), severity-aware dedupe, a per-review note budget (default 4), and an `immuneTurns` cooldown (default 3) so concerns cannot interrupt Odin every turn. Plus the rule that a deliberate operator interrupt suppresses advisor auto-resume. Ref: `docs/advisor-watchdog.md` (`src/advisor/emission-guard.ts`).
3. **Bounded stop-hook continuations.** Advisory continuations are capped at 8, while an explicit `block` with a reason is unlimited; and stop hooks are not fired for subagents. A direct template for Saga's dvergr stop-hook policy. Ref: `docs/extensions.md` `session_stop`, `src/extensibility/shared-events.ts`.
4. **Progress-based loop termination.** Goal continuation stops "after a goal turn with no new tool activity", and `/loop --until '<cmd>'` gates iterations on a shell command's exit code. These complement Saga's `check-convergence.sh` and plateau scripts. Ref: `docs/rpc.md` goal payload, `builtin-modes.ts`.
5. **Yield versus settled distinction.** `prompt_result` (the agent yielded) is separate from `session_settled` (fully quiescent, including background jobs and pending continuations). Ratatoskr could adopt the same two-state notion when deciding whether Odin's pane is safe to nudge. Ref: `docs/rpc.md` "Yield vs settled".
6. **Director discipline.** The orchestrator gets read-only tools, workers get self-contained briefs, and "worker completion means the turn settled, not that its claims are correct; verify by reading touched files". This is a principle for Odin's master journal. Ref: `docs/vibe-mode.md`.
7. **Structured worker results.** `outputSchema` with strict or permissive validation, plus `agent://<id>/<json-path>` extraction. Saga could require dvergar to emit schema-validated final reports in journal JSON and validate them before Odin reads them. Ref: `docs/tools/task.md`.
8. **Secretless worker plus credential sidecar.** robomp's gh-proxy holds the PAT, verifies HMAC-signed requests, has single-destination egress, and audits every host-tool call with redacted arguments into SQLite. It also dedupes events by delivery ID and claims work with `BEGIN IMMEDIATE`. This pattern applies to Heimdall, Gitea credentials and Eir PRs. Ref: `python/robomp/README.md`.
9. **Single credential refresher.** An auth broker holds refresh tokens and refreshes them centrally; clients receive only access tokens or go through a gateway. This is conceptually the same as Saga's keepalive container and supports making the keepalive the only writer of `.credentials.json`. Ref: `docs/auth-broker-gateway.md`.
10. **Cache-aware prompt layout.** Static blocks come first and all cwd-specific context goes into one trailing `<project-context>` block, so per-worktree sessions share a cached prefix. Applicable when structuring Odin's and dvergar's CLAUDE.md and appended context. Ref: `docs/system-prompt-customization.md`.
11. **Sticky rules versus context.** A short `RULES.md` re-sent on every request versus long `AGENTS.md` background. Maps to keeping Odin's evolved principles short and separate from bulky context. Ref: `docs/context-files.md`.
12. **Handoff-as-compaction persisted to disk** (`compaction.handoffSaveToDisk`) and notes-backed context windows (a bounded 16 KB notebook plus rollover). These are models for Odin's master-journal checkpointing before compaction. Ref: `docs/compaction.md`.
13. **TTSR-style rule tripwires.** Mid-stream abort is not possible in Claude Code, but the idea of rules that cost no context until a regex fires could be approximated with PreToolUse/PostToolUse hooks that inject a rule only when a matching tool input or output appears. That mapping is my inference. Ref: `docs/ttsr-injection-lifecycle.md`.
14. **Hashline edits.** Not directly applicable inside Claude Code's built-in Edit tool. Claude gains in the author's benchmark were smaller than for weaker models, so this is low priority for Saga's Claude dvergar. Ref: `docs/tools/edit.md`; [stencil.so/blog/the-harness-problem](https://stencil.so/blog/the-harness-problem).

### Gaps
- I did not test Odin-like long-running interactive omp sessions in tmux, or the reliability of extension-driven injection under load.
- I could not determine whether omp's collab relay could substitute for remote viewing of Odin without exposing session content to omp.sh infrastructure. Frames are described as sealed client-side, but the relay is operated by the vendor.

## 8. Risks: bus factor, stability, breaking changes, licensing, policy, lock-in

### Takeaway
The risks are high on stability and policy and moderate on lock-in:
- one dominant author and a two-founder company with no disclosed funding;
- about 2 releases per day and a new major version roughly monthly, with frequent breaking changes;
- deliberate impersonation of Anthropic and Google first-party clients on OAuth paths;
- an omp-specific extension API that has diverged from Pi.

The MIT license itself is low risk.

### Cited Findings
- **Concentration.** can1357 authored 13,195 of about 29,982 commits, and the roboomp bot 4,085. Stencil Labs lists two founders. — [Contributors](https://github.com/can1357/oh-my-pi/graphs/contributors), [stencil.so/about](https://stencil.so/about)
- **Release cadence.** 658 releases between 2026-01-02 and 2026-10-13, with major versions v4 through v18 in that window. — [Releases](https://github.com/can1357/oh-my-pi/releases)
- **Breaking changes.** The current coding-agent changelog window (18.2.2, 2026-09-16 → 18.10.4, 2026-10-13) contains seven "Breaking Changes" sections. Examples:
  - the `task` tool's `complexity` field replaced by `solutionSpace` (18.3.4);
  - edit syntax changed to `*** Edit File:` / `*** Find` / `*** Replace` headers, and the `hub` tool deprecated (18.3.0);
  - the bash tool's `env` parameter removed (18.2.7);
  - `createAgentSession` now throws when saved models cannot be restored (18.6.3).

  Older entries are archived out of the file. — [packages/coding-agent/CHANGELOG.md](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/CHANGELOG.md)
- **Session storage churn.** Session bucket naming changed in 17.2.5–17.2.8 and was reverted in 17.2.9 (#7397), with best-effort migration. — [docs/session.md](https://github.com/can1357/oh-my-pi/blob/main/docs/session.md)
- **Backlog.** 2,284 open issues and 1,585 open PRs as of 2026-10-13. — [GitHub search API](https://github.com/can1357/oh-my-pi/issues)
- **Support policy.** Only the latest release gets security fixes, on a best-effort basis. — [.github/SECURITY.md](https://github.com/can1357/oh-my-pi/blob/main/.github/SECURITY.md)
- **Licensing.** MIT for omp. Vendored `brush-core` and third-party utilities in `pi-builtins` keep their upstream licenses. — [README.md](https://github.com/can1357/oh-my-pi/blob/main/README.md). `about.toml` accepts permissive licenses globally, with package-scoped exceptions for CDDL-1.0 (`inferno`) and WTFPL (`terminfo`). — [about.toml](https://github.com/can1357/oh-my-pi/blob/main/about.toml)
- **Policy.** omp impersonates Claude Code and Cowork on Anthropic OAuth, and exposes Google Antigravity and Gemini CLI OAuth, which Google's terms prohibit for third-party tools. An open issue requests making these "safe by default". — [docs/provider-quirks.md](https://github.com/can1357/oh-my-pi/blob/main/docs/provider-quirks.md), [Issue #12487](https://github.com/can1357/oh-my-pi/issues/12487). The author reports his Gemini account was disabled. — [stencil.so/blog/the-harness-problem](https://stencil.so/blog/the-harness-problem)
- **Privacy and phone-home.** Auto-QA pushes after consent, catalog fetches from `catalog.stencil.so` have no disable setting per the issue, and the install ID feeds device metadata. — [report-tool-issue.ts](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/tools/report-tool-issue.ts), [Issue #10934](https://github.com/can1357/oh-my-pi/issues/10934), [docs/install-id.md](https://github.com/can1357/oh-my-pi/blob/main/docs/install-id.md)
- **Lock-in.**
  - Extensions target `@oh-my-pi/*` APIs, and Pi compatibility is via shims only.
  - Bun is required (no Node entry points for the CLI), plus a platform-specific Rust N-API binary.
  - Credentials live in an omp-specific SQLite `agent.db`.

  — [docs/porting-from-pi-mono.md](https://github.com/can1357/oh-my-pi/blob/main/docs/porting-from-pi-mono.md)
- **Quality versus cost.** omp was slower and more expensive than Pi on one third-party benchmark, and "talks too much". — [Composio](https://composio.dev/content/pi-vs-omp)

### Inferences
- If Saga adopts omp anywhere, pin exact versions and vendor the image. Treat omp upgrades as deliberate migrations, given monthly major versions and renamed tool schemas.
- Keep Saga's MQTT, journal and guidance contract harness-neutral (shell scripts plus JSON), so an omp-, Pi- or Claude-Code-based dvergr can all speak it. omp's breadth makes deep coupling to its APIs costly.
- The impersonation-based Anthropic path is a single point of failure for any omp deployment using Claude subscriptions: it can break on any server-side fingerprint change (as #9801 shows) or trigger enforcement.

### Gaps
- Funding runway and the company's commercial plans for omp, Tern and omp.sh services: not found.
- I could not quantify how many recent commits are agent-authored. Unlinked author emails account for 39 of the last 100 commits, which is suggestive but not conclusive.
