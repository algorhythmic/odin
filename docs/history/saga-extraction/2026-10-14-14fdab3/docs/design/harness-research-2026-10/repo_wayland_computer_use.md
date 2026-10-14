# algorhythmic/wayland-computer-use (WCU) versus Saga, as of 2026-10-14

Method: shallow clone of `https://github.com/algorhythmic/wayland-computer-use` (HEAD `999944dc64481e34454403c3bab494f3d4e45249`) into a scratch directory, read only (README, DEVELOPMENT, docs, skills, reports, `scripts/`, `native/`, tests). Nothing from the clone was executed, built or installed. Commit history and repo metadata came from the GitHub API on 2026-10-14. Some facts about how the operator's desktop is set up came from read-only inspection of this machine (the Omarchy desktop that runs this research session). Those facts are labelled "local inspection" and cite a local path or command.

Repo links are pinned to commit `999944dc`. Saga paths are relative to `/home/david/Projects/saga/`.

## 1. Identity: what it is, size, history, license, install and run

### Takeaway
WCU is the operator's own experimental Python project. It ships two local stdio MCP servers that let an agent see and drive the operator's live Hyprland/Omarchy desktop. It is packaged first as a plugin for the ChatGPT desktop app's Codex mode, and some later pilots were driven from Claude Code. It was written in a four-day burst (2026-09-06 to 09-10, 15 commits on GitHub) and has not been pushed to since. It has no license, and the operator's local checkout is 10 commits ahead of GitHub.

### Cited Findings
- README self-description: "Experimental local MCP tools for operating and observing a **Hyprland/Wayland** desktop, developed on Omarchy. A community project, not an official OpenAI computer-use implementation or support for every Wayland compositor." — [README.md L3](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L3)
- "One repository, **two independent MCP servers**": Computer Use (root, MCP server name `wayland`) for "Guarded input, screenshots, actionable window observations and outcome waits", and Desktop Observer (`wayland-desktop-observer/`, server `wayland_observer`) for "Read-only versioned state, accessibility evidence, changed-region images and bounded waits." — [README.md L7-L13](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L7)
- The pre-consolidation baseline README calls it a "Personal MCP plugin for the ChatGPT desktop app's Codex mode on Hyprland/Wayland. This is independent of OpenAI's bundled Sky runtime." — [wayland-desktop-observer/baseline/README.md L3-L4](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/baseline/README.md#L3)
- Packaging: Codex plugin manifests `.codex-plugin/plugin.json` (name `wayland-computer-use`, version `0.1.0+codex.20260906101910`, author "Local developer", `"skills": "./skills/"`, `"mcpServers": "./.mcp.json"`) and a second manifest for the observer. — [.codex-plugin/plugin.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/.codex-plugin/plugin.json); [wayland-desktop-observer/.codex-plugin/plugin.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/.codex-plugin/plugin.json)
- Run shape: `.mcp.json` launches `/usr/bin/python3 /absolute/path/to/wayland-computer-use/scripts/dev_host.py` over stdio with `PYTHONDONTWRITEBYTECODE=1` and `startup_timeout_sec: 20`. The observer launches `wayland-desktop-observer/scripts/observer_server.py`. — [.mcp.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/.mcp.json); [wayland-desktop-observer/.mcp.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/.mcp.json)
- Install steps: `python3 scripts/configure_mcp.py --write-plugin-configs` (rewrites path templates), optional `python3 scripts/build_capture.py` (needs cc, pkg-config, wayland-scanner, wayland-client), then `python3 scripts/dev_publish.py --destination .`. Pointer buttons, drag and scroll also need the root-only `scripts/install-mouse.sh`, which installs a systemd `ydotoold` service written as a "UID/GID 1000 template". — [README.md L56-L95](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L56)
- Requirements: "unlocked Hyprland, Python 3, `hyprctl`, `grim`". Input also needs `wtype` and `ydotool` with a private uinput daemon. Accessibility needs PyGObject and the Atspi 2.0 typelib. "The MCP host must allow desktop Unix socket access." — [README.md L58-L65](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L58)
- License: "No open-source license has been selected yet. Publication does not itself grant an open-source license." The GitHub API reports `license: null`, `visibility: public`. — [README.md L237](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L237); [GitHub API repo](https://api.github.com/repos/algorhythmic/wayland-computer-use)
- Repo metadata (GitHub API, 2026-10-14): created 2026-09-06T08:57:20Z, last pushed 2026-09-10T08:18:31Z, description "wayland-co" (truncated), 0 stars, 0 forks, size 741 KB. Languages in bytes: Python 633,696; C 9,999; JavaScript 6,574; Shell 933; HTML 517. One tag, `comparison-2026-09-06`. — [GitHub API repo](https://api.github.com/repos/algorhythmic/wayland-computer-use); [languages](https://api.github.com/repos/algorhythmic/wayland-computer-use/languages)
- Commit history: 15 commits. The first is `da83af93` on 2026-09-06T09:12:52Z ("Consolidate Wayland input and observer with preserved comparison baseline"). The last is `999944dc` on 2026-09-10T08:18:18Z ("Verify Obsidian note transfers with durable receipts and bounded launch acknowledgement"). Per day (UTC): 09-06 2, 09-07 4, 09-08 6 (four of them share the timestamp 00:29:46, so they were committed as a batch), 09-09 1, 09-10 2. The author is David Alexander Dunn, the operator. — [commits on main](https://github.com/algorhythmic/wayland-computer-use/commits/main)
- WCU merges an earlier installed plugin at `/home/david/plugins/wayland-computer-use`; the frozen baseline records its source hashes. The September 6 run tested plugin version `0.1.0+codex.20260905224921`. — [baseline/PROVENANCE.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/baseline/PROVENANCE.json); [reports/2026-09-06-browser-obsidian/retrospective.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-06-browser-obsidian/retrospective.md)
- Size: about 52.8k lines in total, mostly JSON keyboard catalogs and benchmark data. Core code: `scripts/server.py` 1,668 lines, `scripts/cu/` with 15 modules (`observation.py` 575, `obsidian.py` 261, `braid_client.py` 253, and others), `native/capture.c`, and `scripts/dev_host.py` 232. There are 198 `def test_` functions across `tests/` and `wayland-desktop-observer/tests/`. Some tests are live desktop tests (`tests/live_input.py`, `tests/live_text_entry.py`). — local `wc`/`grep` over the clone; [tests/](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/tests/)
- Unpushed local work (local inspection, `git -C /home/david/Projects/wayland-computer-use`): the local `main` is 10 commits ahead of `origin/main` (`999944dc`). The latest local commit is `c618243` on 2026-09-10 13:37 -0700 ("Add isolated launch-inclusive transfer evaluation and retain prerequisite failures"). There is also uncommitted model-evaluation work (`docs/model-evaluation.md`, `scripts/pilot_model_evaluation.py`, untracked `reports/astra-wcu/…`, `reports/2026-09-10-astra-eval-overrun-retrospective.md`).
- Installed on the operator's desktop (local inspection):
  - `systemctl list-units` shows `wayland-computer-use-mouse.service` "Wayland Computer Use input backend for david" as loaded, active and running.
  - `/home/david/plugins/` holds `wayland-computer-use` and `wayland-desktop-observer`.
  - `/home/david/.codex/config.toml` enables `[plugins."wayland-computer-use@personal"]` and `[plugins."wayland-desktop-observer@personal"]`, with `approval_mode = "approve"` set per tool on `focus_window`, `scroll` and `type_text`.
  - `/home/david/.claude.json` has no `mcpServers` entries at user or project scope.

### Inferences
- WCU is a working personal tool on the operator's desktop, not a dormant experiment. The input daemon is running today and Codex is configured with per-tool approvals. Its primary harness is Codex (ChatGPT desktop app), not Claude Code.
- The GitHub copy is a snapshot frozen on 2026-09-10. Anything the operator calls "current" may be in the unpushed local commits.
- Note on "Several Saga features were re-implemented as standalone tools": WCU does not re-implement any Saga component, since Saga has no GUI or desktop layer (see §3). It is the desktop-actuation layer of a newer group of standalone tools: standalone Heimdall, Skald and Braid.

### Gaps
- Neither the unpushed local commits nor the uncommitted files were read. Only their titles and file names were read.
- I did not check whether Claude Code on the desktop loads WCU through a plugin marketplace rather than `mcpServers`. Only `~/.claude.json` was checked.
- No runtime behaviour was verified. Nothing was executed.

## 2. Architecture and interfaces

### Takeaway
WCU uses hand-written MCP JSON-RPC over stdio (protocol `2025-06-18`), with no network listener and no MCP SDK. It exposes 19 custom tools whose coordinates are bound to a `frame_id`. It does not use Anthropic's `computer_*` tool schema or OpenAI's bundled computer use. It works only with Hyprland:
- `hyprctl` for state and focus
- `.socket2.sock` for events
- `grim`, or its own wlr-screencopy client, for screenshots
- `wtype` for text
- a private `ydotoold` uinput daemon for clicks, drags and scrolls
- AT-SPI for accessibility

Its safety comes from per-action guards: frame expiry, pinned target identity, pixel and focus checks, no automatic replay, and execution budgets. Approval and authentication are left to the MCP client and the Unix user boundary.

### Cited Findings
- **MCP transport.** `serve()` reads JSON-RPC lines from stdin and answers `initialize` with `"protocolVersion": "2025-06-18"`, serverInfo `wayland-computer-use` `0.1.0`, plus `ping`, `tools/list` and `tools/call`. There is no SDK import. The observer's serverInfo is `wayland-desktop-observer` `0.2.0`. — [scripts/server.py L1624-L1668](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L1624); [wayland-desktop-observer/scripts/observer_server.py](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/scripts/observer_server.py)
- "No telemetry, network listener or separate cloud service is included. Images sent to a remotely hosted model still leave the machine through its client." — [README.md L163](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L163)
- **Input-server tools (19).**
  - The list: `context_for_task`, `desktop_state`, `screenshot`, `focus_window`, `pointer`, `type_text`, `press_key`, `scroll`, `drag`, `run_steps` (1–12 steps), `open_uri`, `obsidian_create_note`, `obsidian_note_status`, `cdp_read`, `view_frame`, `read_text`, `observe_window`, `wait_for`, `stop_observing`.
  - Each tool carries MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint: true`) and a strict JSON schema with `additionalProperties: false`.
  - — [scripts/server.py L1495-L1550](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L1495)
- **Observer tools.** `observe`, `wait_for_change`, `wait_for`, `stop_observing`, with a renewable 120-second lease. — [README.md, observer paragraph](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md)
- **Other interfaces.**
  - CLI only for the read-only context features: `scripts/context_for_task.py` (JSON on stdin) and `scripts/keyboard_context.py refresh`.
  - A JS adapter, `scripts/wayland_call.js`, is "a function expression for `functions.exec`" used by a local PTY client in a Codex development chat.
  - There is no HTTP API and no Python API meant for importing.
  - — [README.md, Development section](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md); [DEVELOPMENT.md L36-L50](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/DEVELOPMENT.md#L36)
- **Hot-reload host.** `dev_host.py` is a "Stable stdio host" that loads "an explicitly published, SHA-256-identified runtime bundle", switches only between requests, and "verifies complete tool definitions against its startup contract and fails closed on mismatch." — [scripts/dev_host.py L1-L5](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/dev_host.py#L1); [DEVELOPMENT.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/DEVELOPMENT.md)
- **Not Anthropic's or OpenAI's computer-use schema.** No file contains `computer_20…` or "anthropic". The skill says "This is a custom Hyprland integration, not OpenAI's bundled Computer Use implementation. It shares the user's foreground desktop and pointer." — grep over the clone; [skills/wayland-computer-use/SKILL.md L8](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L8)
- **Compositor and protocol mechanics.**
  - State and focus: `hyprctl -j …` and `hyprctl dispatch` ([scripts/server.py L449](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L449)).
  - Event wakeups: Hyprland's `$XDG_RUNTIME_DIR/hypr/<sig>/.socket2.sock` ([scripts/cu/events.py L44](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/events.py#L44)).
  - Session discovery: `hyprctl -j instances` plus `systemctl --user show-environment`, accepting only sockets owned by the same UID ([scripts/cu/system.py](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/system.py)).
  - Text: `wtype -` in 40-character segments (`TEXT_SEGMENT_CHARS = 40`) ([scripts/server.py L156, L1171](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L1171)).
  - Buttons, drag and scroll: `ydotool` via `YDOTOOL_SOCKET=/run/wayland-computer-use-<uid>/mouse.sock` ([scripts/server.py L124, L897](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L897)).
- **Screenshots.**
  - "Captures use raw RGB internally and encode lossless PNG at delivery."
  - "The optional persistent helper uses wlr-screencopy on untransformed scale-1 outputs; other configurations use raw `grim`."
  - "A frame … expires after 120 seconds."
  - — [README.md L108-L113](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L108); [native/capture.c](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/native/capture.c); [native/wlr-screencopy-unstable-v1.xml](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/native/wlr-screencopy-unstable-v1.xml)
- **Accessibility.**
  - A persistent AT-SPI worker (`gi.require_version('Atspi', '2.0')`) is scoped to one application PID and title: "Never fall back to dumping the entire desktop or another window."
  - Password fields are reported as `[protected]`.
  - "there is no OCR."
  - — [scripts/cu/accessibility_worker.py L1-L20, L54](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/accessibility_worker.py#L54); [README.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md)
- **No xdg-desktop-portal.** A grep for "portal" returns 0 files.
- **App surfaces.**
  - `open_uri` accepts only `http`, `https` and bounded `obsidian` URIs, dispatched via `gio open` or `xdg-open`.
  - `cdp_read` requires `WCU_CDP_PORT` and forces "numeric loopback; never resolve a server-provided hostname or proxy". It does no script evaluation, navigation or input.
  - `obsidian_create_note` keeps durable receipts and refuses to overwrite.
  - — [scripts/cu/app_surfaces.py L19-L52, L89, L176-L181](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/app_surfaces.py#L176); [scripts/cu/obsidian.py L1-L5](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/obsidian.py#L1)
- **Safety controls.**
  - Coordinates belong to a viewed `frame_id`.
  - Frames expire after 120 s.
  - "The `wcu-tools-3` contract pins the intended target before every input segment, reports partial submission and outcome verification in a recovery ledger, and shares a validated duration budget across sequence steps (60 seconds by default, 120 seconds maximum)."
  - "Unexpected changes reject the action; there are no blind retries."
  - A noise-tolerant pixel guard.
  - — [README.md L114-L135](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L114); [scripts/cu/execution.py](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/execution.py)
- **Limits of the guards.**
  - "These guards reduce focus races; they cannot make input atomic with compositor queries or prove that an app consumed submitted events."
  - "Both recognize `hyprlock`; other locks are not fully covered." Lock detection is a `/proc` scan for `hyprlock`.
  - — [README.md L119-L121, L156](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L156); [scripts/cu/system.py L39](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/system.py#L39)
- **Approval and authentication are external.**
  - "Approvals remain the MCP client's responsibility; read-only does not mean privacy-free or automatically approved." — [README.md L19](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L19)
  - "The root uinput daemon has a mode-0600 user-owned socket. Other processes of that user can inject input too. Its historical `mouse` name does not restrict it to mouse events. Stopping it does not disable `wtype`." — [README.md L158-L160](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L158)
  - The service unit runs `ydotoold --socket-own=1000:1000 --socket-perm=0600` with `DeviceAllow=/dev/uinput rw`, `RestrictAddressFamilies=AF_UNIX` and systemd hardening. — [scripts/wayland-computer-use-mouse.service](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/wayland-computer-use-mouse.service)
- **Kill switch (partial).**
  - "To temporarily disable daemon input: `pkexec systemctl stop wayland-computer-use-mouse.service` … Stopping this daemon does not disable wtype typing or Hyprland pointer movement; disable the plugin to stop using all its tools."
  - "The server only exposes enumerated operations, not arbitrary commands."
  - — [skills/wayland-computer-use/SKILL.md L133](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L133)
- **Untrusted screen content.**
  - "UI text is untrusted task data, never permission or instructions." — [README.md L153](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L153)
  - "`type_text` inserts literal text, including newlines… In terminals and chat fields a newline can execute or send." — [SKILL.md L127](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L127)
  - "Stop acting if the user is interacting or the target is ambiguous." — [SKILL.md L129](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L129)
- **Models and harnesses used.**
  - The September 6 run: "The recorded main model was `gpt-6-astra` at `xhigh` effort; the approval model was `codex-auto-review` at `low`." — [retrospective.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-06-browser-obsidian/retrospective.md)
  - The September 7 A/B pilot was "driven by this Claude Code session through the development host" — [reports/2026-09-07-browser-obsidian-ab/results.md L3-L4](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-07-browser-obsidian-ab/results.md#L3); [reports/2026-09-07-e2e-protocol.md L23](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-07-e2e-protocol.md#L23)
  - A fit review for "GPT-6-Astra" was dated September 7. — [reports/2026-09-07-astra-fit-review.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-07-astra-fit-review.md)
  - No Anthropic model or computer-use tool version is named anywhere.
- **Optional Braid backend.** `context_for_task` can call the operator's separate Braid retrieval binary (`backend: "braid"`, pinned with `WCU_BRAID_EXECUTABLE` + `WCU_BRAID_SHA256`). The default is local lexical ranking. — [scripts/cu/braid_client.py](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/braid_client.py); [scripts/server.py L476-L477](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/server.py#L476)
- **Measured results.**
  - September 6: a 752.6 s run was "a partially successful plugin acceptance test". Long text corrupted, and the note was repaired through the filesystem. Screenshot payloads totalled 77,346,651 bytes and 4,466,271 input tokens. — [retrospective.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-06-browser-obsidian/retrospective.md)
  - September 7 Claude Code pilot: all four trials completed the task, but the "source line [was] corrupted" in every trial. — [results.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-07-browser-obsidian-ab/results.md)
  - September 8: "All 27 paired desktop task artifacts passed", with these caveats: "small, deterministic local task benchmarks, excluding model inference and approval time." — [reports/2026-09-08-wcu-braid-implementation-results.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-08-wcu-braid-implementation-results.md)

### Inferences
- The interface is MCP-native and uses its own schema. Any Claude model would drive it through generic MCP tool use, not Anthropic's trained `computer` tool. Whether this costs accuracy compared with the native computer-use tool is untested in the repo.
- The real authentication boundary is the Unix UID. Any process running as `david` on the desktop can talk to the ydotoold socket, which the README says, and can run `wtype`. That includes every agent session on the desktop, this Claude Code session among them.
- The design gets its reliability from evidence: outcome conditions, readback, an execution ledger and no replay. This is the same principle as HARNESS-LANDSCAPE pattern 9: "a finished worker turn is not proof its claims are correct." The operator has already built that principle into a working tool.

### Gaps
- Whether `grim` and the wlr-screencopy helper work under a headless or nested Hyprland. Not tested in the repo.
- Rate limiting. I found no per-call or per-minute rate limit. The only bounds are the duration budgets, the 12-step cap and the 40-character text segments.
- The observer's full source was not read in detail; tool names come from the README.

## 3. Relationship to Saga

### Takeaway
WCU never mentions Saga or any Saga component. It is built for the operator's unlocked foreground desktop, not the Docker VM and not a worker container. It belongs to the operator's newer standalone stack:
- standalone **Heimdall**, a task and continuity system unrelated to Saga's container-launch gatekeeper of the same name, which routes "desktop input … through WCU"
- **Skald**
- **Braid**, whose README says "Saga is deferred."

The Saga workflows it could plausibly serve are operator-side desktop automation and, at most, GUI testing of Hyprland apps. It is not a planner tool, and it is not the browser-verification tool Anthropic's long-running-agent post recommends.

### Cited Findings
- A grep of the clone finds 0 files mentioning `saga`, `mimir`, `dvergr`, `heimdall`, `ratatoskr`, `telegram`, `mqtt` or `docker`. "odin" matches only as a substring of other words, and the one "container" hit is about Obsidian key handling. — grep over the clone; [skills/wayland-computer-use/references/environment-context.md L86](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/references/environment-context.md#L86)
- Target environment: "operates the user's unlocked foreground desktop" ([baseline/README.md L5](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/baseline/README.md#L5)); "Both servers observe the composited foreground desktop, not isolated apps" ([README.md L152](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L152)); and it needs an unlocked Hyprland session.
- The operator's local standalone Heimdall (`https://github.com/algorhythmic/heimdall`, local checkout `/home/david/Projects/heimdall`, last commit 2026-09-10) describes itself as "a local task and continuity system for work shared between people and assistants". It states:
  - "Agents run in Claude Code, Codex and herdr; desktop input runs through WCU under its MCP host's approval." — `/home/david/Projects/heimdall/README.md` L239-L240
  - "S2a … Delivered: scoped computer-use intents, action grant, reports and fresh reconciliation"; tested WCU bundle `4c709b70…`, contract `wcu-tools-4`. — `/home/david/Projects/heimdall/README.md` L229; `/home/david/Projects/heimdall/docs/CAPABILITY-LEDGER.md` L70-L90
- "Reports never verify actions. Native/browser observations determine verification; optional read-only WCU metadata … corroborate[s]." — `/home/david/Projects/heimdall/docs/CAPABILITY-LEDGER.md` L75-L77
- Braid: "Heimdall is the active integration; Saga is deferred." Its Saga-named fixture "is not a Saga integration." — `/home/david/Projects/braid/README.md` L5, L36; `/home/david/Projects/braid/docs/roadmap.md` L3
- Skald's plan builds on WCU's catalog persistence and Braid adapter, and keeps its own database separate from Heimdall's and WCU's. — `/home/david/Projects/skald/SKALD-IMPLEMENTATION-PLAN.md` L114, L779, L911-L913
- The Saga repo contains no computer-use, Wayland, Hyprland, Playwright or Puppeteer features. A grep of the repo, excluding the research notes, finds only unrelated substrings such as "guidance".
- Bragi already writes "an Obsidian-friendly git-versioned vault" from a container. — `docs/architecture/ARCHITECTURE.md` L32
- WCU's `obsidian_create_note` instead dispatches `obsidian://` URIs to the desktop Obsidian app for a registered vault (`~/.config/obsidian/obsidian.json`). — [scripts/cu/obsidian.py L1-L5, L61](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/scripts/cu/obsidian.py#L61)
- Anthropic's long-running-agent harness recommends "**browser-level testing** (Puppeteer MCP) because unit tests and curl were insufficient". — `docs/drafts/harness-research-2026-10/custom_harness_and_interop.md` L19, citing [Anthropic Engineering](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- WCU's own skill says: "Prefer an available browser connector for browser tasks." Its `cdp_read` only reads an already-running loopback browser. — [SKILL.md L131](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L131)
- Where dev Claude runs: `CLAUDE.md` ("Where Dev Claude Runs") says the dev session lives on the Docker VM at `/home/david/src/saga`. This research session runs on the Omarchy desktop at `/home/david/Projects/saga` (OS `Linux 7.2.5-3-omarchy`). — `CLAUDE.md`; session environment

### Inferences
- **Placement:** WCU belongs on the operator's desktop only. The VM (192.168.86.17) runs Docker containers. CLAUDE.md does not describe it as having a Wayland session, so WCU has nothing to drive there. The dvergr containers have no compositor, AT-SPI bus or uinput device.
- **Workflows it serves, from most to least plausible:**
  1. The operator's own desktop automation with Codex or Claude Code on the desktop, such as browser-to-Obsidian capture or app operation. This is entirely outside Saga's fleet.
  2. An operator-side "hands" layer that a Saga message could ask the operator's desktop agent to use. The standalone Heimdall already models that as intent, then grant, then report, then independent verification.
  3. GUI testing of Hyprland-targeted software built by a dvergr. This would need a headless Hyprland inside the container, which the repo does not support or test.
- **Not a fit for browser verification in dvergar.** Anthropic's recommendation is met better by a headless Playwright or Puppeteer MCP inside the worker container, which needs no compositor and no uinput.
- **Name collision.** "Heimdall" now names two different operator projects: Saga's Docker launch gatekeeper (`odin/scripts/heimdall.py`) and the standalone task/continuity system that uses WCU. Both drafts use "Heimdall" only in the Saga sense, which a reader of the operator's newer repos could misread.
- **Dev Claude location.** The `CLAUDE.md` statement may be out of date. The operator appears to work on Saga from the desktop, where WCU runs, as well as or instead of the VM.

### Gaps
- Standalone Heimdall, Skald and Braid were not read beyond the lines quoted. Whether they replace Saga features, for example Skald for Bragi, belongs to other notes.
- Whether the desktop can reach the VM over SSH or Tailscale (and the reverse) was not checked. That matters for the security argument in §4.

## 4. Fit with the Odin contract (ODIN-IO-CONTRACT.md §5)

### Takeaway
WCU should be neither a planner tool nor a dvergr tool in the contract. As a planner tool it would hand Odin operator-level control of the live desktop, from which the operator reaches the VM, Gitea and everything else. That bypasses Heimdall's boundary transitively, and it breaks the contract's own rule that tools work without a human present. As a dvergr tool it does not fit, because it needs a live, unlocked Hyprland session and `/dev/uinput`. The most the contract should hold is an explicit exclusion. If desktop actions are ever wanted, the adapter should copy standalone Heimdall's intent, action-grant, report and independent-verification pattern, and a human-approved desktop agent should carry out the actions, not Odin.

### Cited Findings
- The contract's `shell(cmd)` is "Read-only diagnostics inside Odin's container… No Docker socket, no writes outside the scoped paths. Heimdall remains the only launcher." — `docs/drafts/ODIN-IO-CONTRACT.md` §5, L242
- "Tools that need terminal input do not exist; every turn can end without a human present." — `docs/drafts/ODIN-IO-CONTRACT.md` §5, L244-L245
- "The only thing Odin can do to a container is drop validated YAML into `launch-requests/` or a record into `commands/`." — `docs/drafts/ODIN-IO-CONTRACT.md` §8, L308-L311
- "Odin NEVER gets Docker socket access… This is the security boundary — do not bypass it." — `CLAUDE.md`, "Container Launcher Security Model"
- WCU relies on a human at the MCP host: "Approvals remain the MCP client's responsibility" ([README.md L19](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L19)). On this desktop, Codex has `approval_mode = "approve"` on `type_text`, `scroll` and `focus_window` (local inspection, `/home/david/.codex/config.toml` L97-L107).
- The skill tells the agent: "Stop acting if the user is interacting… Stay within the user's requested apps and task." — [SKILL.md L129](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L129)
- Desktop input reaches anything visible: "Input can activate whichever visible control is at a coordinate, including menus and layer surfaces. Focus checks … do not isolate apps." In terminals, a typed newline can execute. — [SKILL.md L127-L129](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L127)
- Even the read-only observer is not privacy-free: "read-only does not mean privacy-free or automatically approved." Overlays "may expose unrelated content." — [README.md L19, L152-L153](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L152)
- WCU is stdio-only with no network listener ([README.md L163](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L163)). Odin runs in a container on the VM (`CLAUDE.md`, file structure and homelab table).
- The contract's Runtime A is "A Python service (the `anthropic` client) [that] owns … the tools above." — `docs/drafts/ODIN-IO-CONTRACT.md` §9, L340-L344
- Standalone Heimdall's adapter pattern: "scoped computer-use intents, action grant, reports and fresh reconciliation"; "Reports never verify actions"; "Cancellation/revocation, expiry and restart still reconcile and never repeat input." — `/home/david/Projects/heimdall/README.md` L229; `/home/david/Projects/heimdall/docs/CAPABILITY-LEDGER.md` L70-L80

### Inferences
- **Planner: no.** Reaching WCU from Odin's container would need a new network path from the VM into the operator's desktop, such as SSH running the stdio server or an MCP-over-HTTP proxy. Every risk follows from that path:
  - Through it, Odin could type into any terminal, browser or chat window on the desktop. That includes a terminal with SSH to the VM, so Odin could run `docker` without Heimdall.
  - That is a strictly larger power than the Docker socket the design denies Odin.
  - The contract's unattended-turn rule (L244) and WCU's human-approval assumption cannot both hold.
  - Odin's job (decompose, guide, audit-route, launch) needs no GUI.
- **Dvergr: no, as built.**
  - **Hyprland only.** A worker would need a headless Hyprland plus an AT-SPI D-Bus session inside the Trail of Bits devcontainer.
  - **uinput passthrough.** Clicks and scrolls need `ydotoold` with `/dev/uinput`. Passing `/dev/uinput` into a container creates input devices in the VM's kernel, a new privilege Heimdall would have to allowlist per image.
  - **Better tools exist.** For web projects, headless Playwright or Puppeteer meets Anthropic's browser-verification advice without any of this. WCU would matter only for a project whose product is a Hyprland desktop app, and then only after a separate sandbox design.
- **If the operator wants desktop actions from Saga at all:**
  - The contract could gain an outbound `request_desktop_action(intent, verification)` routed through `ask_operator`.
  - A human-approved desktop agent (Codex or Claude Code with WCU) would execute the action, using standalone Heimdall's grant/report/verify records.
  - The outcome would come back as a `host` or `operator` message.
  - That keeps the human approval WCU assumes and keeps Odin's container closed.
  - This is a proposal, not something the repo or the drafts specify.

### Gaps
- None of the following were tested: a headless Hyprland in a container; whether WCU's capture helper or `grim` work there; whether AT-SPI is reachable.
- Whether the desktop and VM have SSH trust in either direction was not verified (see §3 Gaps).

## 5. Consequences for HARNESS-LANDSCAPE-2026-10.md and ODIN-IO-CONTRACT.md

### Takeaway
WCU makes no statement in either draft wrong about Saga's own design. It exposes three gaps:
1. The drafts survey third-party harnesses but miss the operator's own September 2026 standalone stack (WCU, standalone Heimdall, Skald, Braid). That stack already uses Codex plugins and independent outcome verification, and it marks Saga as deferred.
2. Anthropic's browser-level verification advice, which is in the research notes, never reaches the patterns list.
3. "Heimdall" is now an ambiguous name.

The Odin contract's §5 tool list stays correct. It should state explicitly that GUI and desktop actuation is excluded.

### Cited Findings
- HARNESS-LANDSCAPE describes its inputs as "a full read of this repo; four landscape surveys …; seven source-level deep dives" — none of the operator's own repos are among them. — `docs/drafts/HARNESS-LANDSCAPE-2026-10.md` L3-L11
- HARNESS-LANDSCAPE §7: "**Is Saga currently running?** Last commit 2026-05-06." — `docs/drafts/HARNESS-LANDSCAPE-2026-10.md` L529-L532. Meanwhile, standalone Heimdall and Skald were last committed 2026-09-10 and Braid 2026-09-09 (local inspection), and Braid says "Saga is deferred by user direction" (`/home/david/Projects/braid/docs/implementation.md` L30).
- HARNESS-LANDSCAPE §2.2 summarises Anthropic's harness guidance but leaves out browser-level verification. — `docs/drafts/HARNESS-LANDSCAPE-2026-10.md` L203-L211
- The research note records that guidance: "(5) **browser-level testing** (Puppeteer MCP) because unit tests and curl were insufficient." — `docs/drafts/harness-research-2026-10/custom_harness_and_interop.md` L19
- HARNESS-LANDSCAPE §4 pattern 5 lists "Project linters, a schema diff …, structural tests as pass/fail gates", with no end-to-end or browser gate. — `docs/drafts/HARNESS-LANDSCAPE-2026-10.md` L321-L325
- HARNESS-LANDSCAPE §3 and §5.3 make Codex the first non-Claude dvergr ("Add a Codex worker image"). — `docs/drafts/HARNESS-LANDSCAPE-2026-10.md` L279, L415-L416. WCU shows the operator already ships Codex plugins that bundle `skills` and `mcpServers` ([.codex-plugin/plugin.json](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/.codex-plugin/plugin.json)) and uses per-tool `approval_mode` in `~/.codex/config.toml` (local inspection).
- ODIN-IO-CONTRACT §5 lists the tools `zoom` … `shell`, and §8 and §9 use "Heimdall" only for Saga's launcher. — `docs/drafts/ODIN-IO-CONTRACT.md` L225-L245, L308-L311
- Standalone Heimdall's README introduces "Heimdall" as "a local task and continuity system". — `/home/david/Projects/heimdall/README.md` L3

### Inferences (proposed corrections, by section)
- **HARNESS-LANDSCAPE header and §0.** The scope covers only third-party and first-party harnesses. Add a sentence saying the operator's own standalone tools (WCU, standalone Heimdall, Skald, Braid; all built 2026-09) were out of scope or are covered in separate notes. They change what "extract Odin" means: parts of the "continuity, memory and retrieval" story already exist outside Saga.
- **HARNESS-LANDSCAPE §3 table.** Add a row for "wayland-computer-use (operator's own)":
  - Odin runtime: No. It is a desktop tool, not a harness.
  - Dvergr runtime: No. It needs a live, unlocked Hyprland session and uinput.
  - Reference value: frame-bound guarded input; outcome-first evidence with readback; an execution ledger; never replay uncertain input; SHA-pinned hot reload that fails closed on a tool-contract hash mismatch; durable operation receipts with reconcile-not-replay (`obsidian_create_note`).
- **HARNESS-LANDSCAPE §2.2 and §4 pattern 5 (or 9).** Add Anthropic's browser-level end-to-end verification as a dvergr gate, implemented with headless Playwright or Puppeteer MCP inside the worker container. Note explicitly that WCU is not that tool, because it drives the operator's live desktop.
- **HARNESS-LANDSCAPE §4 pattern 9.** Cite the operator's own precedent: WCU's "A screenshot alone does not establish task completion" ([README.md L108-L109](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L108)) and standalone Heimdall's "Reports never verify actions."
- **HARNESS-LANDSCAPE §5.3 (Codex worker image).** The worker contract could ship as a Codex plugin (skills plus an MCP server), the format the operator already uses. Whether hooks fire under `codex exec` is still unverified, as §7 says.
- **HARNESS-LANDSCAPE §7 (Is Saga running?).** Add the evidence: in September 2026 the operator's activity moved to standalone repos, and Braid marks the Saga integration "deferred by user direction."
- **ODIN-IO-CONTRACT §5.** After "Tools that need terminal input do not exist", add:
  > No GUI or desktop actuation (for example the operator's `wayland-computer-use` MCP servers) is reachable from Odin. Desktop input acts with the operator's full authority and would bypass Heimdall transitively. Any desktop action is requested from the operator through `ask_operator` and performed by a human-approved desktop agent.
- **Both drafts, terminology.** Add a footnote to the first use of "Heimdall": "Saga's container-launch gatekeeper (`odin/scripts/heimdall.py`), not the operator's standalone Heimdall continuity system (`algorhythmic/heimdall`)."
- **No change needed:** ODIN-IO-CONTRACT §§1–4, §§6–11, and HARNESS-LANDSCAPE §1 (billing), §2.1, §2.3 and §6 sequencing.

### Gaps
- Whether the operator means WCU itself to replace a Saga feature is not stated in the repo. Nothing in WCU maps to an existing Saga component, so this note treats WCU as adjacent, not as a replacement.
- The drafts' coverage of standalone Heimdall, Skald and Braid depends on other notes.

## 6. Gaps and risks

### Takeaway
The main risks are the standing input capability on the operator's desktop and the lack of a license. Others: Hyprland-only scope, text-entry reliability (corruption in every Claude Code pilot trial), unpushed divergence, and the temptation to wire a desktop-control tool into an unattended planner. The main unknowns are anything that requires running it.

### Cited Findings
- Any process running as the operator's user can reach the ydotoold socket ([README.md L158-L160](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L158)), and the service is active on the desktop (local inspection, `systemctl list-units`). Stopping it "does not disable `wtype` typing or Hyprland pointer movement." — [SKILL.md L133](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/skills/wayland-computer-use/SKILL.md#L133)
- Long-text entry corrupted the reflections in the September 6 run ([retrospective.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-06-browser-obsidian/retrospective.md)) and the source line in all four Claude Code pilot trials ([results.md](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/reports/2026-09-07-browser-obsidian-ab/results.md)). The next commit bounded `wtype` to 40 characters per call ([commit `0f094251`](https://github.com/algorhythmic/wayland-computer-use/commit/0f094251)).
- Scope limits:
  - "Version 0.1 targets Hyprland, not every Wayland compositor" ([baseline/README.md L4-L5](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/baseline/README.md#L4)).
  - "The dispatcher implementation targets Hyprland's Lua config mode" ([baseline/README.md L11](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/wayland-desktop-observer/baseline/README.md#L11)).
  - "Window crops spanning monitors may be incomplete" ([README.md L157](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L157)).
- No license, and the repo is public. — [README.md L237](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L237)
- The local checkout is 10 commits ahead of GitHub, plus uncommitted work (local inspection; see §1).
- Benchmarks are explicitly narrow: "These are **not** model inference timings, token counts, approval timings, accuracy gains, or end-to-end agent benchmarks." — [README.md L45-L48](https://github.com/algorhythmic/wayland-computer-use/blob/999944dc64481e34454403c3bab494f3d4e45249/README.md#L45)

### Inferences
- **Standing capability on the desktop.** Any agent the operator runs on the desktop as `david`, including dev Claude sessions working on Saga, can already inject keyboard and mouse input through the socket without going through WCU's guards. That is acceptable for a single-user desktop. It means "the desktop" must be treated as fully trusted, and nothing from Saga's fleet should get a shell or input path onto it.
- **Unattended planner.** Wiring any desktop-control tool into an unattended planner is the risk most likely to be underestimated. It turns Saga's narrow, auditable launch boundary into "whatever the operator can do."
- **Pre-public cleanup.** If Saga's public README draft (`docs/drafts/PUBLIC-README-DRAFT.md`) ever links these tools, the missing license on WCU needs settling first.

### Gaps
- The following could not be determined without running WCU: real behaviour under Claude models; whether Claude Code's MCP client handles its deferred-image and `view_frame` flow well; observer accuracy on apps without accessibility support; and behaviour with multiple monitors, scaling or rotated outputs (the native helper covers only "untransformed scale-1 outputs").
- Whether WCU will be maintained. There have been no pushes for 34 days (2026-09-10 to 2026-10-14), and the cadence afterwards is unknown.
- Whether the operator intends any Saga to WCU integration. The repo and the drafts say nothing about it.
