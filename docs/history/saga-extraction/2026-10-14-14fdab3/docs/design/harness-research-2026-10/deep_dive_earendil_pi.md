# earendil-works/pi: source-level deep dive (architecture, extension model, headless operation, Saga fit), as of 2026-10-13

Method note. Sections 1 to 7 come from reading a shallow clone of `https://github.com/earendil-works/pi` at commit `d20c6e96625143bdb6fc533843d30601a9f6fcf8` (committed 2026-10-14 06:12 UTC, all packages at version 1.2.0 plus an `[Unreleased]` changelog section). Nothing from the clone was built, installed or run. Every runtime claim below is therefore what the docs or source say, not observed behaviour. Source links are pinned to that commit, abbreviated in the text as `pi@d20c6e9`. Section 0 keeps the identity, design and billing facts from the earlier web-research pass, with corrections and source checks added.

## 0. Identity, design reversals, billing and policy (carried over from the web-research pass, checked against source where possible)

### Takeaway
Pi is Mario Zechner's former `badlogic/pi-mono`, now owned by Earendil Inc. and released under MIT. Version 1.0.0 shipped 2026-10-01 and 1.2.0 on 2026-10-12. The source confirms one thing the web pass could not: when Pi uses Anthropic subscription OAuth, pi-ai presents itself as Claude Code (user agent `claude-cli/2.1.280`, `x-app: cli`, the Claude Code beta flags, and a "You are Claude Code" system block), and a code comment calls this "Stealth mode". Saga must never use Pi's Anthropic OAuth path.

### Cited Findings
**Identity** (from the web-research pass; that agent's URLs were not carried over unless noted):
- earendil-works/pi is the same GitHub repository as badlogic/pi-mono (repo id 1035029907, created 2025-08-09), transferred and renamed rather than forked. The 0.74.0 changelog records "the move to `earendil-works/pi-mono` and `@earendil-works/*` package scopes" and self-update support for the rename from `@mariozechner/pi-coding-agent` — [coding-agent CHANGELOG 0.74.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- Earendil Inc. is a public benefit corporation founded in 2025 in Vienna by Armin Ronacher and Colin Daymond Hanna. Named backers are Accel, Balderton, the n8n founder, Peter Steinberger (OpenClaw), Revolut, Sentry and the Slack founders; the round size is undisclosed. Products: Pi, Radius (a hosted gateway, MCP and sharing service for Pi, in early alpha) and Lefos (an email agent). Zechner joined on 2026-04-08 as a shareholder "in charge of all pi decisions". Pi stays MIT with no CLA. Planned tiers are an MIT core, Fair Source value-add and proprietary enterprise/cloud (RFC 0015). (Prior pass; no URL carried over.)
- RFC 0015 "Pi Licensing" is still in "Discussion" status, dated 2026-03-30. Other Pi RFCs: 0019 Pi Telemetry (Implemented), 0031 Terminal Multiplexers (Published), 0038 Pi Analytics (Discussion), 0039 Dynamic Model Configuration (Discussion), 0043 Experimental Pi Flag (Published), 0044 First Time Setup (Discussion), 0047 New Locked Pi Install (Discussion), 0054 Responses Lite Investigation (Discussion) — [rfc.earendil.com keyword pi](https://rfc.earendil.com/keyword/pi/)
- Scale (prior pass): about 114.9k stars, 14.6k forks, 6,921 commits. Top contributors are badlogic (3,898 commits) and mitsuhiko (890). OpenClaw embeds Pi's SDK packages. The README says "See OpenClaw for a real-world integration" — [README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/README.md)
- Every package is MIT except `pi-evals`, which is private — package.json files under [packages/](https://github.com/earendil-works/pi/tree/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages)

**Design and reversals:**
- The 2025-11-30 philosophy (prior pass) was a prompt plus tools under 1k tokens; read, write, edit and bash; no MCP; no built-in subagents, plan mode or todos; YOLO permissions; tmux for background work; session trees with cross-provider handoff. The README still says "Pi ships with powerful defaults but skips features like sub-agents and plan mode" — [README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/README.md)
- 0.99.0 (2026-09-29) added "codemode, tool search, and MCP support as built-in extensions" (stdio and streamable HTTP, with OAuth), virtual models, and Sign in with ChatGPT. 1.0.4 added `--no-mcp`, so MCP is on by default — [coding-agent CHANGELOG 0.99.0, 1.0.4](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- Subagents, plan mode, sandboxing (Gondolin), permission gates and project-trust handling exist only as example extensions in `examples/extensions/` (`subagent/`, `plan-mode/`, `sandbox/`, `gondolin/`, `permission-gate.ts`, `project-trust.ts`) — [examples/extensions](https://github.com/earendil-works/pi/tree/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/examples/extensions)
- Correction to the earlier package list: the monorepo has 11 package directories, not 7. The README table lists 7 (chord, pi-telemetry, pi-ai, pi-durable, pi-agent-core, pi-coding-agent, pi-tui). There are also `pi-codemode` (QuickJS sandbox), `pi-mcp` (a standalone MCP client), `pi-env` (an SSH remote-execution daemon in Rust plus a client) and the private `pi-evals` — [packages/](https://github.com/earendil-works/pi/tree/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages)
- `pi-acp` is a third-party adapter, not an Earendil package. The svkozak/DxTa version speaks ACP JSON-RPC on stdio and spawns `pi --mode rpc`; a victor-software-house fork embeds the SDK instead — [DxTa/pi-acp](https://github.com/DxTa/pi-acp); [victor-software-house/pi-acp](https://github.com/victor-software-house/pi-acp)

**Billing and policy:**
- 0.66.0 (2026-04-08) added an interactive warning that "Anthropic third-party usage draws from extra usage and is billed per token". The setting `warnings.anthropicExtraUsage` (default `true`) controls it — [CHANGELOG 0.66.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md); [settings-defaults.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/settings-defaults.ts)
- **New from source:** for OAuth tokens, `anthropic-messages.ts` sets `"user-agent": "claude-cli/2.1.280"` and `"x-app": "cli"`, adds the betas `claude-code-20250219` and `oauth-2025-04-20`, and prepends the system block "You are Claude Code, Anthropic's official CLI for Claude." under the comment "For OAuth tokens, we MUST include Claude Code identity". It also renames tools to Claude Code's casing (`Read`, `Bash`, `Task`, `TodoWrite`…) under the comment "Stealth mode: Mimic Claude Code's tool naming exactly" — [anthropic-messages.ts L95-130, L1046-1063, L1139, L1218-1230](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/api/anthropic-messages.ts#L95-L130). This confirms the earlier "0.87.1 fixed OAuth requests reporting an outdated Claude Code version" entry ("Fixed inherited Anthropic OAuth requests reporting an outdated Claude Code version") — [CHANGELOG 0.87.1](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- The containerization doc still recommends `claude setup-token` with Docker Sandboxes ("Use a Claude Pro or Max token", injected as `ANTHROPIC_OAUTH_TOKEN`) — [containerization.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/containerization.md). Pi also accepts `ANTHROPIC_OAUTH_TOKEN` "as an API credential" — [providers.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/providers.md)
- 0.71.0 (2026-04-30) "Removed built-in Google Gemini CLI and Google Antigravity support" — [CHANGELOG 0.71.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- 0.99.0 added Sign in with ChatGPT ("Use a ChatGPT subscription with the OpenAI provider through `/login openai`"). Pi's OpenAI Codex requests send `originator: "pi"` and a Pi user agent, not a spoofed identity — [CHANGELOG 0.99.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md); [openai-codex-responses.ts L1648](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/api/openai-codex-responses.ts#L1648)
- Prior-pass statements kept without independent verification here: badlogic in issue #3372 says workarounds are "a ToS violation, you'll need to enable extra usage and get billed by token"; DevDay 2026-09-29 named Pi, OpenClaw, OpenCode and T3 as launch partners for Sign in with ChatGPT; Anthropic's timeline runs from 2026-01-09 blocks, through the ~2026-02-19 legal-page change and the 2026-04-04 removal of third-party harnesses from plan limits, to a help article updated 2026-05-19 that bans tools that "misrepresent their identity to Anthropic's servers".

### Inferences
- Pi's OAuth path impersonates Claude Code at the HTTP and system-prompt level, and Anthropic's help article bans identity misrepresentation. Using Pi with an Anthropic subscription therefore carries account-level policy risk on top of the extra-usage billing. For Saga, any Claude worker on Pi must use `ANTHROPIC_API_KEY` only. Never run `/login anthropic`, and never inject `ANTHROPIC_OAUTH_TOKEN` or a `setup-token` value. The last of these is also forbidden by Saga's own CLAUDE.md findings.

### Gaps
- I did not re-fetch issue #3372, the DevDay announcement or Anthropic's help article. They are carried over from the prior pass, which recorded no URLs.
- Whether Anthropic actively detects or acts on Pi's Claude Code identity headers could not be determined.

## 1. Package architecture: what each package does and how they depend on each other

### Takeaway
The working CLI is a clean three-layer stack, all at 1.2.0 in lockstep:
- `pi-ai` is the provider layer, with no agent logic.
- `pi-agent-core` is a roughly 950-line loop.
- `pi-coding-agent` holds sessions, extensions, modes and tools.

`pi-durable` and `chord` are a separate, new, explicitly experimental line (first released 2026-10-01). The shipping CLI does not use them; 1.1.0 removed coding-agent's dependency on chord. The core loop has no turn, step or cost cap. It runs until the model stops calling tools and no queued input remains, or until a hook ends it.

### Cited Findings
**Dependency graph** (from each package.json):
- `pi-agent-core` depends on `pi-ai` and `typebox` only.
- `pi-coding-agent` depends on `pi-agent-core`, `pi-ai`, `pi-codemode`, `pi-mcp` and `pi-tui`. It does not depend on `pi-durable` or `chord`.
- `pi-durable` depends on `chord`, `pi-ai` and `pi-codemode`.
- `pi-env` depends on `chord` and `pi-durable`.
- `pi-ai` depends on the vendor SDKs (`@anthropic-ai/sdk`, `openai`, `@google/genai`, `@aws-sdk/client-bedrock-runtime`) and `pi-telemetry`.
- `pi-codemode` depends only on `quickjs-wasi`, `pi-mcp` only on `cross-spawn`, and `pi-telemetry` on nothing.

Source: [packages/*/package.json](https://github.com/earendil-works/pi/tree/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages). The 1.1.0 changelog says "Removed the dependency on `@earendil-works/chord`" and removed an unreleased experimental server/client/plugin stack (`pi-client`, `pi-protocol`, `pi-server`) — [coding-agent CHANGELOG 1.1.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)

- **Source sizes** (lines of `src/*.ts`, my count): coding-agent 76,081; ai 27,429; durable 25,159; tui 19,540; chord 11,723; mcp 3,277; codemode 3,037; agent 2,519; env 2,346; evals 1,446; telemetry 935.

**pi-agent-core (loop):**
- The public API is the `Agent` class (`prompt`, `continue`, `steer`, `followUp`, `abort`, `waitForIdle`, `subscribe`, `state`) and the low-level `agentLoop` and `agentLoopContinue` — [agent README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/README.md)
- **Loop structure** — [agent-loop.ts L162-321](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/src/agent-loop.ts#L162-L321):
  - The outer `while (true)` handles follow-ups. The inner `while (hasMoreToolCalls || pendingMessages.length > 0)` handles one assistant turn plus its tools.
  - A response with `stopReason` `error` or `aborted` ends the run immediately (L245).
  - A `length` stop with tool calls fails every call rather than executing truncated arguments (L264-268).
  - After each turn, `finishTurn` may return `{action:"end"}` or `{action:"continue"}` (L286).
  - When the model stops calling tools, follow-up messages are polled (L302). An explicit `continue` triggers one more context-only request (L311).
- **Tool execution:**
  - The default is `parallel`: preflight runs sequentially, then execution is concurrent, with results persisted in source order. Any tool with `executionMode: "sequential"` forces the whole batch to run sequentially.
  - `beforeToolCall` can block a call; `afterToolCall` can rewrite the result.
  - A `terminate: true` hint ends the run only when every result in the batch sets it.
  
  Source: [agent README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/README.md)
- **Hooks:**
  - `prepareRequest` "runs immediately before every conversational provider request", for example to install canonical persisted context.
  - `transformContext` and `convertToLlm` map custom `AgentMessage` types (extended through declaration merging) to LLM messages.
  - `Agent.subscribe` listeners are awaited in order. `agent_end` subscribers count toward settlement.
  
  Source: [agent README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/README.md)
- **Retries in the agent layer:** only `maxRetryDelayMs`, a cap on provider-requested retry delays, is passed to the stream function — [agent.ts L139, L226](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/src/agent.ts#L139). Provider-level retries in pi-ai mirror the OpenAI and Anthropic SDK policy: retry on `x-should-retry`, 408, 409, 429, 5xx or no status, with a default 60 s maximum delay — [provider-retry.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/utils/provider-retry.ts). Session-level auto-retry lives in coding-agent: `retry.maxRetries: 3`, `baseDelayMs: 2000`, exponential backoff, and context overflow handled by compaction instead of retry — [settings-defaults.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/settings-defaults.ts); [agent-session.ts L3739-3745](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L3739-L3745)

**pi-ai (providers):**
- The README lists more than 35 providers, plus "Any OpenAI-compatible API: Ollama, vLLM, LM Studio, etc.". OAuth providers are Anthropic (Pro/Max), OpenAI (Sign in with ChatGPT), OpenAI Codex (legacy), GitHub Copilot and OpenRouter. Refresh is "automatic … under a credential-store lock, so concurrent requests and processes cannot double-refresh" — [ai README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/README.md#oauth-providers)
- **Cross-provider handoff:** user and tool-result messages pass through unchanged. Same-provider assistant messages are preserved. Assistant messages from other providers "have their thinking blocks converted to text with `<thinking>` tags". Contexts and models are plain JSON — [ai README, Cross-Provider Handoffs](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/README.md#cross-provider-handoffs)
- **Prompt and tool changes:**
  - The system prompt and tool set live in transcript `SystemMessage`s (`content`, named `sections`, `toolsAdded`, `toolsRemoved`).
  - Models flagged `supportsMidConvoSystemMessages` receive later system messages in place, so the cached prefix stays intact.
  - Anthropic models with `supportsMidConvoToolChanges` use native `tool_addition` and `tool_removal` blocks (`inline-tools-2026-09-15` beta) "so tool changes do not invalidate the prompt cache".
  - Other models get a collapsed leading system message.
  
  Source: [ai README, System Messages](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/README.md#system-messages)
- **Cost and caching:** every `Usage` carries `input`, `output`, `cacheRead`, `cacheWrite`, `cacheWrite1h` (Anthropic only), `reasoning`, `totalTokens` and a `cost{input,output,cacheRead,cacheWrite,total}` breakdown — [ai types.ts L446-466](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/types.ts#L446-L466). The stream option `cacheRetention` defaults to `"short"`, and `sessionId` drives provider cache affinity — [ai types.ts L239-249](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/types.ts#L239-L249). `PI_CACHE_RETENTION=long` turns on extended caching — [environment-variables.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/environment-variables.md). Coding-agent adds cache warming (`cacheWarming: "streaming"` by default; "runs only when … Pi estimates at least $0.05 in avoided cache-miss cost") — [settings.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/settings.md)

**pi-telemetry:**
- It is a vendor-neutral, callback-based contract: `TelemetryContext` and `TelemetrySpan`, a no-op context, an in-memory reference adapter, typed schemas and a conformance suite. It has "no exporter, global current-span state, or dependency on a telemetry backend". Attributes "should avoid prompts, completions, tool arguments…" — [telemetry README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/telemetry/README.md)
- **Documentation drift:** the telemetry README says pi-agent-core "owns and exports the pi AI-request and harness schemas" (`AGENT_TELEMETRY_SCHEMAS`, `startAiSpan`, …, with names `pi.ai.*`, `pi.harness.*`, `pi.session.*`). No file in the clone defines those symbols. pi-ai only accepts and forwards `telemetryContext` — [ai simple-options.ts L48](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/api/simple-options.ts#L48). A grep found no `startSpan` call in ai, agent, durable or coding-agent `src`.
- **Separate from pi-telemetry, the CLI's install telemetry:**
  - An interactive-mode ping to `https://pi.dev/api/report-install?version=…`, on by default (`enableInstallTelemetry: true`).
  - Provider attribution headers, for example to OpenRouter.
  - Both can be disabled with `PI_TELEMETRY=0`.
  - `enableAnalytics` defaults to `false`.
  
  Source: [interactive-mode.ts L1364-1368](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/modes/interactive/interactive-mode.ts#L1364-L1368); [provider-attribution.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/provider-attribution.ts); [settings-defaults.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/settings-defaults.ts)

**pi-durable:**
- "**Experimental.** The API changes without notice between releases. A durable agent harness. Conversations, model turns, tool calls, and your own state are committed to storage before anything is shown. If the process dies mid-turn, reopening the storage picks the work up where it stopped." — [durable README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md). First release 1.0.0 on 2026-10-01 — [durable CHANGELOG](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/CHANGELOG.md)
- **What it persists:**
  - Immutable entries: `pi.user`, `pi.assistant`, `pi.tool-result`, `pi.system`, `pi.reset`, `pi.compaction`, plus custom kinds.
  - Durable tasks, which are state machines that checkpoint every step. The built-ins are `pi.generation` and `pi.tool`.
  - Submissions, with `requestId` idempotency so a retried submit finds the existing one.
  - Chord-tracked JSON documents: `pi.agent` (per-conversation model, extensions, tools, cwd), `pi.provider` (a persisted UUIDv7 used as the provider `sessionId`), `pi.live` (streaming partials committed at most every 100 ms), `pi.inbox` (queued steer, follow-up and write items) and `pi.usage`.
  
  Source: [durable README, Concepts / Persist and Resume / Watching](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md)
- **Storage backends:**
  - Memory.
  - SQLite (WAL, `synchronous = NORMAL`).
  - Append-only JSONL, which keeps all history in memory: "use SQLite for long-running agents".
  - A Cloudflare Durable Object.
  
  "One process owns a storage at a time; there is no cross-process locking." Storage errors are fatal to the Harness; reopening it recovers — [durable README, Storage / Errors](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md#storage)
- **Replication:** `viewState()` and `watch()` deliver a snapshot and then Chord delta operations per commit. A slow watch keeps at most 100 frames before it is reset to a full view. `watchEvents()` (experimental) emits coding-agent style events — [durable README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md#watching-a-conversation)
- **Tasks and subagents:**
  - Conversations can be owned by tasks. The subagent pattern creates a task-owned child conversation, and `background: true` anchors survive parent aborts.
  - Child tasks wait on others with an `allSettled` or `failFast` policy.
  - Tools declare `replay: "safe"` to rerun after a crash. Otherwise the model gets an `interrupted` error result.
  - The normative spec runs to 5,340 lines.
  
  Source: [durable README, Abort and Subagents / Child Tasks](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md#abort-and-subagents); [durable spec.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/docs/spec.md)

**chord:**
- "Chord builds applications out of objects that live in several processes (a server, workers, browser tabs) and can be hot reloaded while they run". It provides typed contracts (`local`, `remote`, `method`) described as TypeBox runtime values, principals (owner and guest see different methods), observable JSON state with snapshot-plus-delta replication, and hot reload where "work in flight finishes on the code it started with". Hosts exchange JSON frames over in-memory, Node IPC or WebSocket links — [chord README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/chord/README.md)
- 1.2.0 (2026-10-12) "Replaced the facet and service runtime with a typed host runtime". `[Unreleased]` already lists more breaking renames (`Handle`→`Ref`, `epoch`→`codeVersion`, `kind`→`variant`, link `PROTOCOL_VERSION` 2) — [chord CHANGELOG](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/chord/CHANGELOG.md)

**Other packages:**
- `pi-env` is a small Rust daemon deployed over SSH, plus a Durable `ExecutionEnv` client, "so an agent's tools run on another machine … while the Durable worker, its storage and credentials stay local" — [env README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/env/README.md)
- `pi-codemode` runs model-written JavaScript in QuickJS/WASM, where "the only capability is calling injected tools" — [codemode README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/codemode/README.md)
- `pi-mcp` is "A small, standalone Model Context Protocol client. It does not depend on the official MCP SDK" — [mcp README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/mcp/README.md)

### Inferences
- The `pi-ai` → `pi-agent-core` → `pi-coding-agent` split is the decomposition worth copying. The loop is small enough (about 950 lines) to port or re-implement in Python. pi-durable and chord look like Earendil's next-generation server and hosted runtime (Cloudflare Durable Object storage, multi-process replication, Radius). They are not the CLI's foundation today.
- "Loops until the model stops calling tools" is accurate, with two extensions: queued steer and follow-up input keeps the loop going, and `finishTurn` or boundary hooks can force one more request. There is no step or budget limit in agent-core, coding-agent settings or durable settings (grep of `settings-schema.ts` and the loop). Callers must impose caps.

### Gaps
- Whether Earendil plans to move pi-coding-agent onto pi-durable was not found in the repo or the RFC index titles.
- I did not read pi-tui or most of the 27k lines of pi-ai beyond the README, types, retry and Anthropic adapter.

## 2. The coding agent: system prompt, tools, context management, sessions, skills, AGENTS.md

### Takeaway
Pi's coding agent assembles a small, sectioned system prompt and defaults to four tools (read, bash, edit, write). It stores sessions as JSONL trees, compacts at `contextWindow - 16384` tokens into a structured summary, and loads `AGENTS.md`/`CLAUDE.md` from the agent directory and every ancestor directory, regardless of project trust. There is no built-in memory, todo, plan or goal feature.

### Cited Findings
**System prompt** — [system-prompt.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/system-prompt.ts):
- Sections come in order: `preamble` ("You are an expert coding assistant operating inside pi, a coding agent harness…"), `tools` (one-line snippets), `rules` (tool guidelines plus "Be concise…", "Show file paths clearly…"), `docs` (pointers to Pi's own docs), `addendum` (APPEND_SYSTEM.md or `--append-system-prompt`), `project_context` (context files wrapped in `<project_instructions path=…>`), `skills` (name, description and path only) and `cwd`.
- Every section except the preamble is wrapped in a tag of the same name. Prompt changes mid-session are sent as section diffs (`diffSystemPromptSections`).
- `SYSTEM.md` or `--system-prompt` replaces the preamble. A `before_agent_start` handler can force the entire prompt.

**Tools:**
- Built-ins are `read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find` and `ls`. The defaults are `read`, `bash`, `edit` and `write`.
- Built-in extensions add `codemode` and `tool_search`, both off by default, and MCP (on by default).
- Selection flags are `--tools`, `+name/-name`, `--exclude-tools` and `--no-tools`.

Source: [cli.md, Tools](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/cli.md)

**Exposure levels** — [extensions.md, Tool exposure](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md):

| Level | Behaviour |
|---|---|
| `direct` (default) | Declared to the model and callable while active. |
| `model-only` | Declared to the model, never callable from other tools. |
| `codemode` | Callable from codemode scripts, not declared unless activated. |
| `deferred` | Found through `tool_search`. |
| `hidden` | The only way to "unregister" a tool. |

Other tool metadata:
- MCP-style `annotations` (`readOnlyHint`, `destructiveHint`, …) feed permission extensions.
- `prepareLoadout()` lets an orchestrating tool rewrite declarations.
- `reachesTools()` declares which tools a call may reach.
- Nested calls go through `ctx.executeTool()`, which records `nestedCalls` on the parent result: at most 256 calls, with arguments over 8 KiB omitted.

**Compaction** — [compaction.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/compaction.md):
- **Trigger:** `contextTokens > contextWindow - reserveTokens` (default 16384). The check runs between turns after tool results, before a new prompt, and as one compact-and-retry recovery on a provider overflow or early `length` stop.
- **Method:** walk back to keep about `keepRecentTokens` (default 20k) verbatim, then summarize the rest with an LLM. The structured format has Goal, Constraints & Preferences, Progress (Done, In Progress, Blocked), Key Decisions, Next Steps and Critical Context, plus `<read-files>` and `<modified-files>` lists tracked cumulatively.
- **What is written to disk:** a `CompactionEntry` (`summary`, `firstKeptEntryId`, `tokensBefore`, `usage`, `details{readFiles, modifiedFiles}`) is appended to the session JSONL. "The original entries remain in the session tree."
- **Before summarizing:** tool results are truncated to 2,000 characters and thinking blocks are omitted.
- **Branch summaries:** `/tree` navigation can write a `BranchSummaryEntry`.
- **Extensions:** `session_before_compact` can cancel compaction or supply a custom summary.
- **Defaults:** `compaction.enabled: true`, `reserveTokens: 16384`, `keepRecentTokens: 20000` — [settings-defaults.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/settings-defaults.ts)

**Sessions, branching and resume:**
- Sessions are JSONL files at `~/.pi/agent/sessions/--<path>--/<timestamp>_<session-id>.jsonl`, header version 3.
- Entries form a tree through `id`/`parentId`. Entry types: message, model change, thinking-level change, usage, compaction, context edit, branch summary, custom, custom message, label, session info.

  Source: [session-format.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/session-format.md)
- `/tree` moves within a file. `/fork` and `/clone` create new files.
- CLI flags: `--continue`, `--resume`, `--session <path|id>`, `--session-id <id>` ("Opens the exact project session ID or creates it if absent"), `--fork`, `--session-dir`, `--no-session`.

  Source: [sessions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/sessions.md); [cli.md, Sessions](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/cli.md)
- The `bash` tool exports `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_PROVIDER`, `PI_MODEL` and `PI_REASONING_LEVEL` to commands the model runs — [environment-variables.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/environment-variables.md)

**Skills:**
- Pi implements the Agent Skills spec.
- Discovery: `~/.pi/agent/skills`, `.pi/skills` (trust-gated), `~/.agents/skills`, and project `.agents/skills` up to the repo root.
- Only name, description and path go into the prompt. The model reads `SKILL.md` on demand; `/skill:name` forces it.
- `disable-model-invocation` hides a skill from automatic selection.

  Source: [skills.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/skills.md)

**AGENTS.md handling:**
- Pi takes at most one context file per directory, choosing the first of `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`.
- It loads the agent-directory file first, then walks from cwd up to the filesystem root, ordered root-most first.
- `--no-context-files` disables loading.

  Source: [resource-loader.ts L185, L232-273](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/resource-loader.ts#L185); [configuration.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/configuration.md)
- Context files load regardless of project trust: "Treat instructions in a folder as untrusted input even when you decline project trust" — [security.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/security.md)

**Memory:**
- The core docs describe no memory feature. pi-chat, an Earendil extension, injects `/shared/memory.md` and `/workspace/memory.md` into the system prompt each turn — [pi-chat](https://github.com/earendil-works/pi-chat)

### Inferences
- Pi reads `CLAUDE.md`, so the per-container `CLAUDE.md` that `init-dvergr.sh` writes into `/workspace` would be picked up unchanged by a Pi dvergr. It lands in `project_context`, unless an `AGENTS.md` exists in the same directory, because only one file per directory is loaded.
- The compaction summary format is close to what Saga's `journal.md` entries try to capture and could be reused as the journal template.

### Gaps
- I did not read `compaction.ts` (1,119 lines) to confirm exact prompts, or the built-in tool sources for truncation limits.
- No memory or goal feature appears in core docs. I cannot rule out undocumented experimental flags (RFC 0043 "Experimental Pi Flag").

## 3. Extension model: events, tools, message injection, modes, trust, packaging

### Takeaway
Extensions are in-process TypeScript modules, loaded via jiti without compilation. They get 41 `pi.on()` events, tool, command, flag, provider and MCP registration, and two message-injection APIs with explicit delivery modes (`steer`, `followUp`, `nextTurn`). The key events for Saga are:
- `agent_before_settle`: the last point where an extension can append entries and request another model call.
- `agent_settled`: notification that nothing more will run automatically.

Extensions run in all four modes (tui, rpc, json, print). Trust is all-or-nothing: an extension has the full permissions of the process.

### Cited Findings
**All `pi.on()` events** — [extensions/types.ts L1597-1664](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/types.ts#L1597-L1664). Semantics come from the type declarations and extensions.md.

Startup and resources:
- `project_trust`: personal and CLI extensions only. Returns `{trusted:"yes"|"no"|"undecided", remember?}`; the first yes or no wins.
- `resources_discover`: returns extra skill, prompt and theme paths.

Session:
- `session_start`: reason is `startup`, `reload`, `new`, `resume` or `fork`.
- `session_info_changed`.
- `session_before_switch`, `session_before_fork`, `session_before_compact` and `session_before_tree`: all cancellable or customizable.
- `session_compact` and `session_compact_failed`.
- `session_shutdown`: reason is `quit`, `reload`, `new`, `resume` or `fork`.
- `session_tree`.
- `mcp_servers_change`.

Context and provider:
- `context`: rewrites messages without system messages.
- `context_with_system`: owns the full transcript.
- `cache_warming_decision`: warm or stop.
- `before_provider_request`: can replace the payload.
- `before_provider_headers`: mutate in place.
- `after_provider_response`: status and headers.
- `provider_stream_event`: raw parsed events, read-only, not persisted.

Agent lifecycle:
- `before_agent_start`: since 1.2.0 a union on `messageType` (`"user"` or `"custom"`). Can change prompt sections or tools, or force the whole prompt.
- `agent_start` and `agent_end`.
- `agent_before_settle`: returns `BoundaryResult {entries?, continue?}`.
- `agent_settled`: `{aborted}`.
- `ui_prompt_start` and `ui_prompt_end`.

Turn, message and tool:
- `turn_start` and `turn_end`: `turn_end` is also an actionable boundary.
- `message_start` and `message_update`.
- `message_end`: can replace the finalized message.
- `tool_execution_start`, `tool_execution_update` and `tool_execution_end`: the end event carries `durationMs`.
- `model_select` and `thinking_level_select`.
- `tool_call`: can mutate input or block. A handler failure blocks the tool "as a fail-safe".
- `tool_result`: handlers compose.

Input:
- `user_bash`: can take over `!` commands.
- `input`: can transform or handle prompt input.

**Boundary contract:**
- `turn_end` and `agent_before_settle` "can chain proposed `custom`, `custom_message`, `context_edit`, or `compaction` entries and return `continue: true` for one next model request. Guard continuation conditions because an unconditional continuation can loop" — [extensions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md)
- A compaction draft with `firstKeptEntryId: null` "creates a self-retaining compaction that keeps no preceding entries" — [types.ts CompactionEntryDraft](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/types.ts#L992-L999)
- A continuation is rejected, and reported as an extension error, unless the projected context can continue: it must have non-system content and must not end on an assistant message, unless something is queued — [agent-session.ts L1000-1029](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L1000-L1029). Custom messages convert to `role: "user"` for the LLM — [messages.ts L162-169](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/messages.ts#L162-L169)
- Lineage: actionable `turn_end` and `agent_before_settle` were added in 0.87.0 (2026-09-21). `agent_settled` was added around 0.80.x (July 2026). `aborted` was added to `agent_settled` in 1.1.0 — [coding-agent CHANGELOG](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)

**`pi.registerTool`:**
- A tool has a name, description, TypeBox `parameters` and `execute()`.
- Results need `content` and `details`. Throwing marks an error; returning `isError: true` reports an error while keeping data.
- Optional: `outputSchema`/`structuredContent`, `executionMode`, `exposure`, `namespace`, `annotations`, renderers.
- File-mutating tools should use `withFileMutationQueue()`.

Source: [extensions.md, Tools](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md)

**Injecting messages from outside a turn:**
- `pi.sendUserMessage(content, {deliverAs?: "steer"|"followUp", expandPromptTemplates?})` "Always triggers a turn". Since 1.2.0 it requires `deliverAs` while busy.
- `pi.sendMessage({customType, content, display, details}, {triggerTurn?, deliverAs?: "steer"|"followUp"|"nextTurn"})` handles four cases:
  - `nextTurn` queues the message for the next run.
  - While streaming, it steers by default, or follows up.
  - While idle with `triggerTurn`, it starts a run.
  - While idle without `triggerTurn`, it appends with no turn.
- `pi.appendEntry(customType, data)` persists data that is not sent to the LLM.

Source: [types.ts L1731-1747](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/types.ts#L1731-L1747); [agent-session.ts L2323-2358, L2395-2423](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L2323-L2358)
- Steering "is delivered after the current assistant turn finishes executing its tool calls, before the next LLM call". A follow-up "is delivered only when agent stops" — [rpc-commands.md, prompt](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/rpc-commands.md)
- The `file-trigger.ts` example watches `/tmp/agent-trigger.txt` with `fs.watch` and calls `pi.sendMessage({customType:"file-trigger", …}, {triggerTurn:true})`. Its header says it is "Useful for external systems to send messages to the agent" — [file-trigger.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/examples/extensions/file-trigger.ts)

**Other ExtensionAPI surface:**
- `registerCommand`, `registerShortcut`, `registerFlag`/`getFlag`, renderers, `exec(cmd,args)`, `getActiveTools`/`setActiveTools`/`getAllTools`, `setModel`, `setThinkingLevel`.
- `registerProvider` (including OAuth and custom `streamSimple`), `registerMcpServer`, `registerVirtualModel`, and `events` (an inter-extension bus).
- `ExtensionContext` provides `ui`, `mode`, `hasUI`, `cwd`, `sessionManager` (read-only), `modelRegistry`, `isIdle()`, `signal`, `abort()`, `shutdown()`, `getContextUsage()`, `compact()` and `getSystemPrompt()`.

Source: [types.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/types.ts)

**Modes:** `ExtensionMode = "tui" | "rpc" | "json" | "print"`. "Extensions load in interactive, RPC, JSON, and print modes … RPC can forward supported dialogs and notifications through the RPC Extension UI protocol … JSON and print modes have no UI" — [types.ts L323](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/types.ts#L323); [extensions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md)

**Loading and trust:**
- Discovery order is project `.pi/extensions/`, then `~/.pi/agent/extensions/`, then configured paths and `-e`. Each location can hold direct `*.ts`/`*.js` files, `*/index.ts`, or a `package.json` `pi.extensions` manifest, with no recursion beyond one level — [loader.ts L828-876](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/extensions/loader.ts#L828-L876)
- Project extensions, settings, MCP config, skills, prompts and `SYSTEM.md` are gated by project trust. In print, JSON and RPC modes, "If no command-line override, extension, or saved decision applies … `defaultProjectTrust: "ask"` or `"never"` skips them". `--approve` and `--no-approve` force a decision — [security.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/security.md)
- "An extension runs inside the Pi process with the same operating-system permissions" — [extensions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md)
- `/reload` replaces the extension runtime — [extensions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/extensions.md)

**Packaging:**
- Pi packages come from `npm:` (versioned specs pinned), `git:` (tags and commits pinned) or a local path. They carry extensions, skills, prompts and themes through conventional directories or a `pi` manifest.
- Host-provided modules (`pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`, `typebox`) must be listed as `peerDependencies "*"`.
- The `pi-package` npm keyword lists a package in the gallery at pi.dev/packages.

Source: [packages.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/packages.md)

### Inferences
- Pi has an in-process equivalent of each Saga mechanism:
  - Ratatoskr's `tmux send-keys` nudge maps to an extension subscribing to MQTT and calling `pi.sendMessage(..., {triggerTurn:true, deliverAs})`.
  - The Claude Code Stop hook maps to `agent_before_settle`.
  - The SessionStart hook maps to `session_start`.
  - "Is the agent idle?" maps to `agent_settled`, which is what Saga's tmux nudging cannot observe.
- The extension API has no permission boundary, so an extension is as trusted as the harness. Saga's Heimdall-style isolation stays necessary.

### Gaps
- I did not trace every event's exact result type, for example `ToolCallEventResult` fields beyond block and mutate.
- I did not verify which extension UI methods degrade silently in print or JSON mode beyond the doc statement.

## 4. Headless operation: RPC, JSON, print, sessions, first-run, Docker

### Takeaway
Pi is built to run headless:
- `-p` prints the final text and exits.
- `--mode json` streams JSONL events and exits.
- `--mode rpc` is a long-lived JSONL command/event protocol with explicit `agent_settled` idle signals.

Non-interactive modes show no first-run dialogs. First-time setup is interactive-only, and the trust prompt is skipped by a default policy. The process exits with code 1 if no model and credentials resolve. There is an official plain-Docker recipe, and none of Saga's `claude-baseline.json` workaround is needed.

### Cited Findings
**Modes:**
- "With terminal stdin and stdout, Pi opens the terminal UI unless `--print`, `--mode json`, or `--mode rpc` selects another interface. When either stream is redirected and neither JSON nor RPC mode is selected, Pi uses print mode."
- `-p` writes "the final assistant text to stdout, then exit[s]". `--mode json` writes "JSONL events to stdout, then exit[s]". `--mode rpc` reads "JSONL commands from stdin … until shutdown".

Source: [cli.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/cli.md)
- Print mode binds extensions with mode `print` or `json`, awaits `session.prompt()` for each message, and exits 1 on an `error`/`aborted` stop or a `length` truncation — [print-mode.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/modes/print-mode.ts)

**RPC commands** — [rpc-types.ts L22-74](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/modes/rpc/rpc-types.ts#L22-L74); [rpc-commands.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/rpc-commands.md):

| Group | Commands |
|---|---|
| Prompting | `prompt` (with `streamingBehavior` `steer`/`followUp`, required while streaming), `steer`, `follow_up`, `abort`, `clear_queue`, `new_session` |
| State | `get_state`, `get_messages` |
| Model and thinking | `set_model`, `cycle_model`, `get_available_models`, `set_thinking_level`, `cycle_thinking_level`, `get_available_thinking_levels` |
| Queues | `set_steering_mode`, `set_follow_up_mode` |
| Compaction and retry | `compact`, `set_auto_compaction`, `set_auto_retry`, `abort_retry` |
| Bash | `bash` (streams `bash_execution_update`), `abort_bash` |
| Session | `get_session_stats`, `export_html`, `switch_session`, `fork`, `clone`, `get_fork_messages`, `get_entries` (`since`), `get_tree`, `get_last_assistant_text`, `set_session_name` |
| Discovery | `get_commands` |

**RPC protocol rules:**
- A `prompt` response's `data.disposition` is `started`, `queued` or `handled`. Responses are correlated by optional `id`.
- Framing is strict JSONL. Do not use Node `readline`, because it splits on U+2028 and U+2029.
- "Wait for `agent_settled` when the client needs to know Pi will not continue automatically."
- "Close the child's stdin to request an orderly shutdown."
- `RpcClient` (TypeScript) has `promptAndWait()`.

Source: [rpc.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/rpc.md)

**Events (JSON and RPC):**
- `agent_start`, `agent_end` (with `willRetry`), `agent_settled` (`aborted`), `turn_start`, `turn_end`.
- `message_start`, `message_update` (delta-only on the wire, plus cumulative `usage`), `message_end`.
- `tool_execution_*`, `queue_update`, `entry_appended`, `session_info_changed`, `thinking_level_changed`.
- `compaction_start` and `compaction_end`, `auto_retry_start` and `auto_retry_end`, `summarization_retry_*`.
- RPC only: `bash_execution_update`, `extension_error`.
- JSON mode emits the session header first.

Source: [json.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/json.md)

**Extension UI over RPC:**
- `extension_ui_request` methods are `select`, `confirm`, `input`, `editor`, `notify`, `setStatus`, `setWidget`, `setTitle` and `set_editor_text`. The client answers with `extension_ui_response`.

Source: [rpc-types.ts L253-287](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/modes/rpc/rpc-types.ts#L253-L287); [rpc-extension-ui.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/rpc-extension-ui.md)
- RPC has no command to inject a custom (non-user) message. Only `prompt`, `steer` and `follow_up` exist (same file).

**First-run behaviour:**
- `showFirstTimeSetup` runs only when `appMode === "interactive"` — [main.ts L676](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/main.ts#L676). It also requires an official distribution and experimental features. It is skipped when `PI_CODING_AGENT_DIR` is set — [startup-ui.ts L131-146](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/cli/startup-ui.ts#L131-L146)
- Non-interactive modes exit 1 with a "no models" message if no model resolves — [main.ts L927-930](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/main.ts#L927-L930)
- RPC refreshes model catalogs in the background unless offline (same file, L933+).

**Network quieting:** `PI_OFFLINE=1` or `--offline` stops catalog refreshes. `PI_SKIP_VERSION_CHECK` stops the pi.dev version request. `PI_TELEMETRY=0` turns off install telemetry and attribution headers. `PI_CODING_AGENT_DIR` relocates `~/.pi/agent`. `PI_CODING_AGENT_SESSION_DIR` relocates sessions — [environment-variables.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/environment-variables.md)

**Docker recipe:**
- `FROM node:24-bookworm-slim`; install bash, git and ripgrep; `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`; `ENTRYPOINT ["pi"]`.
- Run with `-e ANTHROPIC_API_KEY -v "$PWD:/workspace" -v pi-agent-home:/root/.pi/agent`.
- "Do not mount the host's `~/.pi/agent`."
- Alternatives: Docker Sandboxes (`sbx run --kit docker.io/sbx/pi-kit:latest pi`), NVIDIA OpenShell, and the Gondolin micro-VM extension (tools only).

Source: [containerization.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/containerization.md)

**Local models:**
- Use `models.json` with `"api": "openai-completions"` and a `baseUrl` for Ollama, LM Studio, vLLM or SGLang (example: `http://localhost:11434/v1`, `"apiKey": "ollama"`). The built-in `/llama` integrates the llama.cpp router — [models.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/models.md#configure-a-compatible-endpoint)
- Virtual models route each request to a physical model, for example small versus large — [virtual-models.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/virtual-models.md)

**Credentials without `/login`:**
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` and others, or `--api-key`.
- `auth.json` keys can be `!command` (secret-manager lookups cached per process).
- `pi auth check --provider X --json` returns `ready`, `not_ready` or `invalid` with exit codes 0, 1 or 2.

Source: [providers.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/providers.md); [cli.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/cli.md)

### Inferences
- A container-friendly Pi dvergr is one non-interactive process: no tmux, no `send-keys`, no pre-captured onboarding JSON. The minimal invocation is:

  ```
  PI_CODING_AGENT_DIR=/home/vscode/.pi/agent PI_SKIP_VERSION_CHECK=1 PI_TELEMETRY=0 pi -p --no-approve -e /opt/saga/saga-dvergr.ts --model <provider/id> --session-id "stream-$DVERGR_INSTANCE" --session-dir /workspace/.dvergr/pi-sessions "<kickoff prompt>"
  ```

  `--no-approve` ignores any `.pi/` in the repository under work. Context files still load. Explicit `-e` extensions still load.
- Under Saga's Trail of Bits firewall, Pi needs egress only to the model endpoint (a provider API or a homelab Ollama/vLLM IP) once `PI_OFFLINE`/`PI_SKIP_VERSION_CHECK`/`PI_TELEMETRY=0` are set. `PI_OFFLINE` also freezes the model catalog to the bundled or saved one, which is fine for pinned models.

### Gaps
- Not executed: I did not verify that `-p` with an `agent_before_settle` continuation loop keeps the process alive across iterations. Section 5 explains why the source suggests it does.
- I did not check whether `--session-id` combined with `-p` resumes cleanly after a hard container kill mid-turn. The JSONL is append-only, but a partial last line was not investigated.

## 5. Loop-until-done: building a Ralph-style loop

### Takeaway
Pi has no built-in `/loop`, goal or Ralph feature. It has exactly the right primitive: an `agent_before_settle` handler that appends a `custom_message` and returns `continue: true` drives repeated `agent.continue()` calls inside one `prompt()` until the handler stops. There is no internal cap, so the extension owns the iteration limit and completion check. Two other routes exist: an external RPC driver, and pi-durable's `onYield` hook. Third-party Ralph packages exist but are unreviewed.

### Cited Findings
- `_startRun` calls `agent.prompt(messages)` and then loops `while (!this._agentRunAbortRequested)`. First it handles retry and compaction recovery (`_handlePostAgentRun`). Then, if `_runBeforeSettleBoundary()` returns true, it calls `agent.continue()` again. Only when the boundary declines does it emit `agent_settled` — [agent-session.ts L1837-1882](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L1837-L1882)
- The boundary commits the handler's drafts, flushes pending custom messages, and continues if `result.continue || this.agent.hasQueuedMessages()` and the context can continue — [agent-session.ts L1983-2004](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L1983-L2004)
- The changelog recipe is: "Return `{ entries: [...event.entries, draft], continue: true }` to persist structural entries in order and ensure one next provider request" — [CHANGELOG 0.87.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- The SDK says `prompt()` "resolves after the run finishes, including automatic retries" — [sdk.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/sdk.md). Print mode simply awaits `session.prompt()` — [print-mode.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/modes/print-mode.ts)
- pi-durable offers `hook(GenerationTask, { onYield: (answer) => needsMoreWork(answer) ? { continue: "Keep going." } : undefined })`, where the first continuation wins. Its other hooks are `beforeRequest`, `afterResponse`, `afterTools`, and on tools `beforeTool`/`afterTool` — [durable README, Hooks](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md#hooks); [durable spec.md §6-8](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/docs/spec.md)
- The subagent example spawns child `pi --mode json -p --no-session` processes, which is the external-driver pattern — [subagent/index.ts L300](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/examples/extensions/subagent/index.ts#L300)
- Third-party gallery packages:
  - `@pi-unipi/ralph`: a `ralph_start` tool with a checklist, ending when all items are done or the cap is reached — [pi.dev](https://pi.dev/packages/@pi-unipi/ralph)
  - `ralph-loop-pi`: looped subagent execution until a condition returns false — [pi.dev](https://pi.dev/packages/ralph-loop-pi)
  - `@kimuson/pi-ralph`: chains project commands such as typecheck and test with AI review, with optional PR automation — [pi.dev](https://pi.dev/packages/@kimuson/pi-ralph)
  - The gallery warns that "Pi packages can execute code".

### Inferences
- **Design A, in-process extension (closest to the /ralph-loop Stop hook):** one `pi -p` process runs the whole loop and exits when the extension stops continuing. Each `agent_before_settle` is one iteration boundary. At that boundary the handler should:
  1. Run `post-iteration.sh` through `pi.exec`.
  2. Check the completion promise and cap.
  3. Re-read `latest-guidance.md`.
  4. Append a `custom_message` carrying the next-iteration prompt and guidance, and return `continue: true`.

  Context grows across iterations as with Claude Code's plugin, and Pi auto-compacts. For classic fresh-context Ralph, the handler can also append a compaction draft with `firstKeptEntryId: null` and the journal tail as the summary. That draft type is documented, but I have not tested it.
- **Design B, external driver:** a Python process, which fits ratatoskr's language, spawns `pi --mode rpc --session-id …`. For each iteration it sends `prompt`, reads until `agent_settled`, runs `post-iteration.sh`, reads guidance, and either sends the next `prompt` or closes stdin. This keeps loop policy outside the model process and needs no TypeScript, at the cost of a second process and a hand-written JSONL reader.
- **Publishing MQTT after each iteration:** call the existing `dvergr-hooks/post-iteration.sh` (it already does `mosquitto_pub` for status and journal and `mosquitto_sub` for guidance), either from the extension or from the driver. Alternatively an extension can publish directly using an npm MQTT client declared in its package `dependencies`.

### Gaps
- Not run. Interaction between the continuation loop and auto-retry, overflow compaction or `ctx.shutdown()` under real provider errors is unverified.
- The behaviour of the third-party Ralph packages is not reviewed.

## 6. Fit for Saga

### Takeaway
- **(a) Odin blueprint:** yes, as a design source. Copy pi-ai's transcript and system-message model, pi-agent-core's queue and boundary semantics, and coding-agent's extension and RPC contracts. Treat pi-durable as a reference for crash-safe orchestration state, not as a dependency. Avoid chord. Pi is not an Odin runtime while Odin needs Opus on the Max subscription: the subscription is extra-usage billed and the identity is spoofed.
- **(b) Dvergr runtime:** yes, the lowest-friction option for API-key or local-model workers. One TypeScript extension of about 70 lines, or a Python RPC driver, satisfies Saga's whole worker contract, and print mode removes the tmux, onboarding-JSON and plugin-install steps.
- **(c) Patterns worth adopting on Claude Code:** an explicit settled signal, typed delivery classes for nudges, idempotent request IDs, structured compaction-style journals, and strict JSONL framing.

### Cited Findings
- Saga's worker contract, from the current hooks:
  - `post-iteration.sh` publishes `/workspace/.dvergr/status.json` (retained QoS 1) and the tail of `journal.md` to `dvergr/{project}/{instance}/status|journal`.
  - It pulls retained `…/guidance` into `/workspace/.dvergr/latest-guidance.md` and emits `saga/events/dvergr_completed` once.
  - `init-dvergr.sh` sets `MAX_ITERATIONS` (default 20) and `COMPLETION_PROMISE` (default `COMPLETE`), checks out `stream-$DVERGR_INSTANCE`, and tells the model to push it.

  Source: local files `dvergr-hooks/post-iteration.sh`, `dvergr-hooks/pre-iteration.sh`, `containers/dvergr/init-dvergr.sh`, `mqtt/TOPIC-SCHEMA.md` in the Saga repo.
- pi-chat is Earendil's own "pi extension that bridges Discord and Telegram channels to a sandboxed pi session". It runs workers in "detached tmux/pi sessions". A `chat_workers` tool exposes worker status snapshots (written every 15 s) "to an orchestrating pi agent", and every channel gets its own Gondolin micro-VM — [pi-chat README](https://github.com/earendil-works/pi-chat). The repo sidebar says Apache-2.0 while the README says MIT (per WebFetch of the same page).
- Pi provides no permission system: "Pi does not include a built-in permission system for restricting filesystem, process, network, or credential access" — [README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/README.md)
- The SDK `createAgentSession()` takes injectable `modelRuntime`, `settingsManager`, `sessionManager` (including `SessionManager.inMemory()`), `resourceLoader` with inline extension factories, and `customTools` — [sdk.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/sdk.md)

### Inferences

**(a) Blueprint for a custom Odin harness.**

Copy:
- **pi-ai's `SystemMessage` transcript model**, with named `sections` and `toolsAdded`/`toolsRemoved` ([ai README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/README.md#system-messages)). It lets Odin change its own instructions mid-conversation, for example new principles or a newly launched dvergr list, without breaking prompt caching. Use pi-ai as a dependency rather than copying 27k lines.
- **pi-agent-core's loop contract** ([agent-loop.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/agent/src/agent-loop.ts)): steer versus follow-up queues, `prepareRequest` (reload canonical context from disk before each call), `finishTurn` end/continue, `beforeToolCall`/`afterToolCall`, all-agree `terminate`, and the awaited `agent_end` barrier. At about 950 lines it is portable to Python.
- **coding-agent's session JSONL tree with compaction entries** that never delete raw history ([session-format.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/session-format.md)). This is a better audit substrate for Mimir than tmux scrollback.
- **The RPC protocol** (prompt disposition, `agent_settled`, id correlation) as the model for any Odin↔ratatoskr or Odin↔Telegram bridge.
- **pi-chat's shape**: a chat bridge as an extension, an orchestrator tool that reads worker status snapshots, and per-channel workspaces with injected memory files. It is the nearest existing analogue of Odin + Telegram + dvergar.
- **pi-durable concepts, not code:** commit-before-show, an inbox with steer/follow-up/write classes, `requestId` idempotency, task-owned subagent conversations with background anchors, and replay-safe tools. These map onto Odin's Mimir requests, Heimdall launch requests and dvergr lifecycles.

Avoid:
- **chord.** Its runtime was replaced in 1.2.0, more breaking changes are pending, and it is designed for multi-process, browser and replication scenarios a single-host Odin does not need.
- **Depending on pi-durable directly.** It is "Experimental … changes without notice".
- **Pi's Anthropic OAuth path** (Section 0).
- **YOLO defaults without an outer boundary.** Keep Heimdall.

Runtime decision: a Pi-based Odin implies Opus on `ANTHROPIC_API_KEY` (per-token billing) or a non-Anthropic planner. If the operator wants to keep Max-subscription Opus, Odin stays on Claude Code and Pi is a design source only.

**(b) Dvergr runtime for API-key or local-model workers.** Pi satisfies every contract item.

| Saga contract item | Pi mechanism |
|---|---|
| Read PRD.md | Kickoff prompt; `CLAUDE.md` auto-loaded as a context file |
| Iterate until promise or cap | `agent_before_settle` loop |
| status.json and journal.md each iteration | The model writes them as instructed in `CLAUDE.md`; the extension can also write status.json itself for determinism |
| Run post-iteration.sh | `pi.exec("bash", [".../post-iteration.sh"])` in the boundary handler |
| Read latest-guidance.md each iteration | Read in the handler and injected as a `custom_message` |
| Push the stream branch | Model instruction, or a deterministic `pi.exec("git", ["push", ...])` in the handler |

Sketch (untested; uses only APIs verified in `types.ts`, `session-manager.ts` and the docs):

```ts
// /opt/saga/saga-dvergr.ts  — load with: pi -p --no-approve -e /opt/saga/saga-dvergr.ts ...
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";

const D = "/workspace/.dvergr";
const MAX = Number(process.env.MAX_ITERATIONS ?? 20);
const PROMISE = process.env.COMPLETION_PROMISE ?? "COMPLETE";
const BRANCH = process.env.DVERGR_BRANCH ?? `stream-${process.env.DVERGR_INSTANCE ?? "instance-1"}`;

export default function (pi: ExtensionAPI) {
  let iteration = 0;

  pi.on("session_start", async (_e, ctx) => {
    for (const entry of ctx.sessionManager.getBranch()) {          // resume counter after container restart
      if (entry.type === "custom" && entry.customType === "saga-iteration") iteration = (entry.data as { n: number }).n;
    }
    await pi.exec("bash", ["/opt/saga/dvergr-hooks/pre-iteration.sh"]); // seeds latest-guidance.md
  });

  pi.on("agent_before_settle", async (event) => {
    iteration += 1;
    const last = [...event.context.contextMessages].reverse().find((m: any) => m.role === "assistant") as any;
    const text = (last?.content ?? []).filter((c: any) => c.type === "text").map((c: any) => c.text).join("\n");
    await pi.exec("git", ["-C", "/workspace/repo", "push", "origin", BRANCH]);      // deterministic stream push
    await pi.exec("bash", ["/opt/saga/dvergr-hooks/post-iteration.sh"]);          // MQTT status/journal + guidance pull
    const entries = [...event.entries, { type: "custom" as const, customType: "saga-iteration", data: { n: iteration } }];
    if (event.outcome !== "completed" || text.includes(PROMISE) || iteration >= MAX) return { entries }; // settle -> pi -p exits
    const g = existsSync(`${D}/latest-guidance.md`) ? readFileSync(`${D}/latest-guidance.md`, "utf8").trim() : "";
    entries.push({
      type: "custom_message" as const, customType: "saga-ralph", display: true,
      content: `Iteration ${iteration + 1}/${MAX}. Re-read /workspace/PRD.md and ${D}/journal.md, do the next task, ` +
               `update ${D}/status.json and append to ${D}/journal.md. Say ${PROMISE} only when every PRD criterion is met.` +
               (g ? `\n\nGuidance from Odin:\n${g}` : ""),
    });
    return { entries, continue: true };
  });
}
```

Container changes relative to today's dvergr image:
- Drop `claude-baseline.json`, the tmux kickoff, `/plugin install` and the Stop/SessionStart hook wiring.
- Mount a `pi-agent-home` volume (or set `PI_CODING_AGENT_DIR`).
- Pass a provider key (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) or a `models.json` pointing at a homelab vLLM/Ollama host, and add that IP to the iptables allowlist.
- Set `PI_SKIP_VERSION_CHECK=1 PI_TELEMETRY=0`.

Heimdall's request schema needs a `runtime: pi` field and model/provider fields. The MQTT topics are unchanged. A worker the operator wants to watch live can instead run interactively in tmux with the same `-e` extension, since extensions run in all modes.

A Python RPC driver (Design B in Section 5) is the alternative if the operator prefers Python-owned loop logic.

**(c) Patterns worth adopting even if Saga stays on Claude Code:**
1. **Explicit settled signal.** Have the dvergr Stop hook and Odin's hooks publish a `settled` MQTT message (Pi's `agent_end` versus `agent_settled` distinction), so ratatoskr only nudges an idle pane instead of guessing.
2. **Typed delivery classes for ratatoskr nudges.** Use `steer` (after the current tool round), `followUp` (after the run ends) and `nextTurn` (context for the next run, no trigger). For example: Telegram operator messages as steer, dvergr status digests as nextTurn, Mimir verdicts as followUp. See [agent-session.ts L2323-2358](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/src/core/agent-session.ts#L2323-L2358).
3. **`requestId` idempotency** (pi-durable) for Mimir `pending/`→`verdicts/` files and Heimdall launch YAMLs, so a retried write never double-launches a container.
4. **Pi's compaction summary schema** (Goal / Constraints / Progress Done-InProgress-Blocked / Key Decisions / Next Steps / Critical Context / read-files / modified-files) as the `journal.md` entry template, which Odin can parse ([compaction.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/compaction.md)).
5. **Strict LF-only JSONL framing and id-correlated responses** for any JSON over pipes or MQTT bridges ([rpc.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/rpc.md)).
6. **MCP-style tool annotations** (`readOnlyHint`/`destructiveHint`) as Heimdall- or Mimir-facing metadata for which actions need review.
7. **Supply-chain rules:** exact pins, `min-release-age=2`, `--ignore-scripts` ([README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/README.md)).

### Gaps
- No Pi worker was built or run against Saga's broker. The sketch is unverified against the TypeScript compiler. Exact typings for `event.context.contextMessages` and the custom-entry draft literal types should be checked.
- How pi-chat injects inbound Telegram messages (polling, sendUserMessage or other) is not stated in its README.
- I did not test local-model quality or tool-call reliability with Pi's minimal prompt.

## 7. Risks: API stability, cadence, bus factor, open-core, Anthropic policy

### Takeaway
Treat Pi as fast-moving software where every minor release may break extensions. Pin exact versions and re-test the Saga extension on each bump:
- The written release policy says `minor = breaking changes`, and a 1.0.x patch also broke compatibility.
- Seven releases shipped in the first 12 days after 1.0.
- The durable and chord layers are experimental and churning.

Commercial pull toward Radius is visible in defaults. Bus-factor risk is concentrated in one maintainer. Any Anthropic subscription use through Pi is a policy hazard.

### Cited Findings
- "**Lockstep versioning**: all packages share one version; every release updates all together. `patch` = fixes + additions, `minor` = breaking changes. No major releases." — [.pi/skills/release.md L10](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/.pi/skills/release.md#L10)
- 1.2.0 (2026-10-12) changed extension-facing behaviour:
  - `before_agent_start` became a union on `messageType`.
  - "the session [counts] as busy while a run starts … `pi.sendUserMessage()` requires `deliverAs`".
  
  1.0.3, a patch, carried a "Breaking Changes" entry (Azure provider renamed to `azure`) — [CHANGELOG 1.2.0, 1.0.3](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md). By my scan of the changelog, "Breaking Changes" sections appear in 1.2.0, 1.0.3, 0.87.0, 0.86.0, 0.84.3, 0.84.0, 0.83.0, 0.80.8 and 0.80.7 (since 2026-07).
- **Cadence:** the coding-agent CHANGELOG has 288 versioned releases from 0.10.0 (2025-11-25) to 1.2.0. By month: 21 in 2026-03, 25 in 04, 16 in 05, 16 in 06, 12 in 07, 5 in 08, 9 in 09, 7 in October to date (1.0.0 10/01, 1.0.1 10/03, 1.0.2 10/04, 1.0.3 and 1.0.4 10/05, 1.1.0 10/07, 1.2.0 10/12). `[Unreleased]` already pins internal deps exactly after mixed-version installs broke (#10865) — [coding-agent CHANGELOG](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md)
- **Experimental layers:** pi-durable says "Experimental. The API changes without notice between releases" — [durable README](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/durable/README.md). chord replaced its runtime in 1.2.0, and `[Unreleased]` lists further breaking renames — [chord CHANGELOG](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/chord/CHANGELOG.md)
- **Governance and bus factor:** "All issues and PRs from new contributors are auto-closed by default". Approval comes through maintainer `lgtm`/`lgtmi` replies — [CONTRIBUTING.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/CONTRIBUTING.md). Contributor concentration: badlogic 3,898 and mitsuhiko 890 commits (prior pass).
- **Open-core signals:**
  - Radius is first in `/login` and documented first in Providers.
  - `/share` defaults to a Radius artifact when Radius auth exists.
  - `/bug` uploads go to `radius.pi.dev`.
  - `pi update --self` installs "the package name returned by the version check endpoint".
  - RFC 0015 (licensing tiers) and RFC 0038 (analytics) are in Discussion.

  Source: [CHANGELOG 1.0.0, 0.74.0](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/CHANGELOG.md); [sessions.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/sessions.md); [rfc.earendil.com](https://rfc.earendil.com/keyword/pi/)
- **Documentation drift:** the telemetry README promises agent-core telemetry exports that do not exist in source (Section 1).
- **Anthropic policy:** OAuth requests impersonate Claude Code (Section 0), and the docs suggest `claude setup-token` for Pro/Max in Docker Sandboxes — [anthropic-messages.ts](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/ai/src/api/anthropic-messages.ts#L1218-L1230); [containerization.md](https://github.com/earendil-works/pi/blob/d20c6e96625143bdb6fc533843d30601a9f6fcf8/packages/coding-agent/docs/containerization.md)

### Inferences
Mitigations for Saga:
- Pin `@earendil-works/pi-coding-agent@1.2.x` exactly in the dvergr image.
- Keep the Saga extension small, using only `session_start`, `agent_before_settle`, `exec` and `sessionManager.getBranch`, all present since at least 0.87.0.
- Run a smoke iteration in CI before bumping.
- Never configure Anthropic OAuth in Pi containers.
- Set `PI_TELEMETRY=0`, and avoid `/share` and `/bug` in workers.

The MIT licence and the absence of a CLA mean the current code stays forkable if open-core tiers arrive. The risk is future features, not the existing core.

### Gaps
- No reliable source for Earendil's funding size, runway or roadmap for the MIT core versus Fair Source split. RFC 0015's body was not read.
- I could not establish whether the extension API has any documented stability guarantee beyond the lockstep `minor = breaking` rule.
