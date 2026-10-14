# Harness research notes — 2026-10-13

Supporting material for [`../HARNESS-LANDSCAPE-2026-10.md`](../HARNESS-LANDSCAPE-2026-10.md),
the assessment of whether to extract Odin into a standalone harness and
how Saga compares with the October 2026 harness landscape.

Each file was written by a research agent on 2026-10-13 and carries an
inline URL or file path for every claim, with findings, inferences and
gaps separated. Treat the contents as dated snapshots: star counts,
prices and Anthropic policy text were all current that day and several
had changed more than once earlier in 2026.

## Landscape surveys

| File | Covers |
|---|---|
| [claude_code_platform.md](claude_code_platform.md) | Claude Code v2.1.299 as a platform: all 33 hook events, the four ways to inject external events into a running session (inbox socket, mods, channels, monitors), MCP, plugins and skills, subagents and agent teams, workflows, agent view, routines, Projects, self-hosted environments, memory, `claude -p` and Agent SDK billing, `CLAUDE_CODE_OAUTH_TOKEN` issue history, the April 4 policy and later updates, Anthropic's harness guidance |
| [third_party_harnesses.md](third_party_harnesses.md) | Codex CLI, Gemini CLI and Antigravity CLI, OpenCode, Oh My OpenAgent, Pi, Hermes, Goose, Aider, Cline/Roo/Kilo, OpenHands, Amp, Crush, Droid, Cursor CLI, Mistral Vibe, Kimi Code, Qwen Code, Warp Oz, Copilot CLI, OpenClaw: architecture, hooks, loop modes, headless operation, auth and billing, ACP |
| [orchestrators_and_loops.md](orchestrators_and_loops.md) | Gas Town, Beads, Gas City, Wheelhouse, Symphony, the Ralph-loop lineage, Claude Code first-party multi-agent surfaces, worktree managers, Paperclip, claude-flow, hosted agents (Devin, Codex cloud, Cursor, Jules, Copilot), long-running-harness research; synthesis of where Saga's seven patterns are mainstream, unusual, or idiosyncratic |
| [custom_harness_and_interop.md](custom_harness_and_interop.md) | Schools of thought on building a harness (Anthropic, OpenAI, Hashimoto, Zechner, Hermes, Karpathy, Ball), reference harnesses, interop protocols (ACP, MCP 2026-07-28, A2A, AG-UI, Agent Skills, AGENTS.md, OTel GenAI), billing of ACP-driven agents, a cost matrix for a continuously running planner, provider automation policies |

## Deep dives (one repo each, read from a shallow clone without executing anything)

| File | Repo |
|---|---|
| [deep_dive_hermes_agent.md](deep_dive_hermes_agent.md) | NousResearch/hermes-agent |
| [deep_dive_oh_my_pi.md](deep_dive_oh_my_pi.md) | can1357/oh-my-pi |
| [deep_dive_earendil_pi.md](deep_dive_earendil_pi.md) | earendil-works/pi (source read at commit d20c6e9, all packages 1.2.0; includes a worker-contract extension sketch and launch line) |
| [deep_dive_exo.md](deep_dive_exo.md) | exoharness/exo |
| [deep_dive_nerve.md](deep_dive_nerve.md) | ClickHouse/nerve |
| [deep_dive_openhuman.md](deep_dive_openhuman.md) | tinyhumansai/openhuman |
| [deep_dive_talorys.md](deep_dive_talorys.md) | rociiu/talorys |

## The operator's standalone repos (reviewed 2026-10-14)

Each was read from a shallow clone without executing anything, and
compared against the Saga component it shares a name or role with.
None replaces a Saga component; each note ends with the statements in
the two drafts that it corrects.

| File | Repo | One-line verdict |
|---|---|---|
| [repo_heimdall.md](repo_heimdall.md) | algorhythmic/heimdall | Desktop task-and-continuity daemon; excludes agent execution; not Saga's gatekeeper. Also documents `heimdall.py`'s real interface and its `commands/` and `depends_on` defects |
| [repo_braid.md](repo_braid.md) | algorhythmic/braid | Byte-budgeted retrieval engine; complementary to the UniiChat log as a `recall` tool |
| [repo_skald.md](repo_skald.md) | algorhythmic/skald | Transcript archiver, no model calls; cannot replace Bragi; needs a provider adapter and per-line conversation ids to archive the chat log |
| [repo_muninn.md](repo_muninn.md) | algorhythmic/muninn | Phase 3 bookmark pipeline redefined as the operator's personal wiki; dormant since July; the retrospective's defects were fixed in `ab874cb` |
| [repo_wayland_computer_use.md](repo_wayland_computer_use.md) | algorhythmic/wayland-computer-use | Hyprland desktop-control MCP server; must stay outside Odin and the workers |

## Coordinator notes

| File | Covers |
|---|---|
| [saga_side_observations.md](saga_side_observations.md) | What Odin physically is today, the harness-shaped pain points in the backlog, what is Claude-Code-specific versus already harness-agnostic, the implicit worker contract, and the three readings of "Odin as a custom harness" |

## Pages the coordinator verified directly

- https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
- https://code.claude.com/docs/en/legal-and-compliance
