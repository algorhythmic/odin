# algorhythmic/heimdall versus Saga's in-repo Heimdall (as of 2026-10-14)

> Method: `git clone --depth 1 https://github.com/algorhythmic/heimdall` into an isolated scratch directory on 2026-10-14 (HEAD `c7fee4b2f93403b589e51b628cd260cfb17d6d7f`). Nothing in the clone was built or run. Commit history, languages, CI runs and the operator's repo list came from the GitHub API through `gh api`. Read-only checks were made on the operator's desktop ("themachine", Omarchy) for an installed binary, unit, data directory and local checkout. The Saga side was read at `/home/david/Projects/saga` (HEAD `9e02823`, 2026-05-06). Links of the form `GH:path#Lnn` point to `https://github.com/algorhythmic/heimdall/blob/c7fee4b/path#Lnn`. Saga paths are relative to the repo root. **Bottom line: the repo is a different product that shares the name. It does not supersede Saga's launcher.**

## 1. Identity: what is algorhythmic/heimdall?

### Takeaway
algorhythmic/heimdall is a Go daemon for task and work continuity on the operator's Omarchy/Hyprland workstation. It has a SQLite event log, a terminal UI, a CLI, an MCP adapter, a Chromium extension, and Herdr, Neovim and Hyprland adapters. It was built in a six-day burst (2026-09-05 to 2026-09-11) and has had no commits since. It does not launch containers and never mentions Docker. Its design documents name "Saga coupling" as a rejected option.

### Cited Findings
- **Self-description:** "Heimdall is a local task and continuity system for work shared between people and assistants. It records changes as events, preserves accepted decisions and progress checkpoints, and supplies scoped resume context." — [README.md#L3](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L3)
- **GitHub description:** "A local daemon that observes every surface you work in, keeps an event log, opens tasks in workspaces, and issues ranked work session plans on a schedule." The repo is public, not a fork, and has 0 stars, no topics, one branch (`main`), no tags and no releases. — [GitHub API `repos/algorhythmic/heimdall`](https://api.github.com/repos/algorhythmic/heimdall)
- **Language and size:**
  - The GitHub languages API reports Go 1,724,577 bytes, JavaScript 228,005 (browser extension and Node smoke tests), Lua 36,661 (Neovim), QML 19,409 (Omarchy bar), Python 8,679 (test fixtures), plus PowerShell, Shell, HTML, TypeScript and Makefile. — [GitHub API `languages`](https://api.github.com/repos/algorhythmic/heimdall/languages)
  - The clone has 48,915 lines of Go. 109 of the files are `_test.go`, totalling 15,333 lines. `go.mod` pins `go 1.25.0` and `toolchain go1.27.1`. — [go.mod#L3-L5](https://github.com/algorhythmic/heimdall/blob/c7fee4b/go.mod#L3-L5)
- **Commit history:**
  - There are 35 commits. The first is `2aa2457`, 2026-09-05T06:22:04Z, "feat: bootstrap Heimdall task core, browser bridge and scoped MCP". The last is `c7fee4b`, 2026-09-11T06:55:43Z, "Add supervised Braid retrieval (S3.1 foundation)".
  - Commits per UTC day: 7 on 09-05, 17 on 09-09, 4 on 09-10 and 7 on 09-11.
  - The first 7 commits are authored as "Algorhythmic" and the remaining 28 as "David Alexander Dunn".
  - The last push was 2026-09-11T06:55:44Z, so the repo has had no activity for 33 days as of 2026-10-14. — [GitHub API `commits`](https://api.github.com/repos/algorhythmic/heimdall/commits)
- **Release state:**
  - The README calls the current state "extending 0.7.0 with database schema 22" and says "These are development milestones, not a complete v1 release." — [README.md#L5](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L5), [README.md#L28](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L28)
  - The CHANGELOG entries are headed "Unreleased". — [CHANGELOG.md#L3](https://github.com/algorhythmic/heimdall/blob/c7fee4b/CHANGELOG.md#L3)
- **License:**
  - GitHub reports no license, and there is no LICENSE file at the root.
  - The PKGBUILD declares `license=('custom')`. — [PKGBUILD#L12](https://github.com/algorhythmic/heimdall/blob/c7fee4b/PKGBUILD#L12)
  - `docs/licenses/` holds only third-party notices for Go dependencies. — [docs/licenses/INDEX.txt](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/licenses/INDEX.txt)
- **Deployment artifacts (in the repo):**
  - A **user-level** systemd unit: `After=graphical-session.target`, `ExecStart=%h/.local/bin/heimdall start --data-dir %h/.local/share/heimdall`, `WantedBy=default.target`. — [contrib/systemd/heimdall.service](https://github.com/algorhythmic/heimdall/blob/c7fee4b/contrib/systemd/heimdall.service)
  - An Arch `heimdall-git` PKGBUILD: "Verified session and workspace continuity daemon with a terminal interface (Hyprland, Herdr, Chromium)". — [PKGBUILD#L9](https://github.com/algorhythmic/heimdall/blob/c7fee4b/PKGBUILD#L9)
  - A Makefile `install` target that builds into `$(HOME)/.local/bin`. — [Makefile](https://github.com/algorhythmic/heimdall/blob/c7fee4b/Makefile)
  - An Omarchy QML bar module. — [contrib/omarchy/heimdall/](https://github.com/algorhythmic/heimdall/tree/c7fee4b/contrib/omarchy/heimdall)
  - `heimdall service install|uninstall|status` manages the optional user unit. — [docs/STATUS.md#L18](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/STATUS.md#L18)
  - There is no Dockerfile, no compose file and no Docker invocation. A case-insensitive grep for `docker|podman|container|compose` matches only Go identifiers such as `service` and `ContainerKey`, which keys browser-tab surfaces. — clone grep, 2026-10-14
- **Deployment on the operator's machine (local observation, 2026-10-14):**
  - `/home/david/.local/bin/heimdall` exists (25 MB, dated Sep 10 23:54, which matches the Makefile install path).
  - `~/.local/share/heimdall/daemon.log` was last modified 2026-10-13 17:21 and holds repeated `{"status":"running"}` lines with different PIDs.
  - The user unit is not installed (`systemctl --user is-enabled heimdall.service` returns `not-found`), and there is no pacman package.
  - The local checkout `~/Projects/heimdall` is at `c7fee4b` with 0 commits ahead of or behind `origin/main` and a clean working tree.
  - Conclusion: the daemon is in ad-hoc use on the desktop, not on the Saga Docker VM.
- **References to Saga.** There are three, all in design history and all keeping Saga out. There is no mention of Odin, Mimir, dvergar, Ratatoskr, Bragi, Gitea, Mosquitto, Telegram, launch-requests, `init-dvergr.sh` or Saga images.
  - The original locked handoff's decision table: "Judgment runtime | direct model calls from the daemon, provider optional | … | **Rejected:** Saga coupling; a long-running overseer agent". The next row: "Event bus | none; in-process dispatch + SSE | … | **Rejected:** MQTT (a bus, not a log; second path)". The same document says Heimdall "is not a harness, not an orchestrator". — [docs/history/design-v1/sources/HANDOFF-heimdall-v1.original.md#L16](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/design-v1/sources/HANDOFF-heimdall-v1.original.md#L16), [#L32-L33](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/design-v1/sources/HANDOFF-heimdall-v1.original.md#L32-L33)
  - "Do not … open the sample Saga database". — [docs/history/design-v1/IMPLEMENTATION.md#L11](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/design-v1/IMPLEMENTATION.md#L11)
  - "Do not share Heimdall's database with Braid or reuse the sample `saga.braid.db`." — [docs/history/design-v1/BRAID-CONTRACT.md#L28](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/design-v1/BRAID-CONTRACT.md#L28)
  - The current r4 handoff keeps "Event bus: none … rejected MQTT/NATS". — [docs/design/HANDOFF-heimdall-v1-r4.md#L169](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L169)
- **Sibling standalone tools from the same September 2026 burst:**
  - `skald` (Go; created 2026-09-10; "Skald preserves source conversations; Heimdall owns accepted task state").
  - `braid` (Go; retrieval engine; README: "Heimdall is the active integration; Saga is deferred").
  - `wayland-computer-use` (WCU; Python).
  - Saga's own GitHub repo is private, with its last push on 2026-05-07.
  - Sources: [`gh repo list algorhythmic`](https://github.com/algorhythmic) (listing includes private repos), `/home/david/Projects/skald/README.md` lines 1-6, `/home/david/Projects/braid/README.md` line 5.

### Inferences
- This is a name collision, not a successor. Both components are deterministic daemons named Heimdall, but they guard different bridges. Saga's guards Odin to Docker on the VM. This one guards a person's and their assistants' workstation state on the desktop.
- Among the operator's "re-implemented as standalone tools", Skald and Braid are better candidates for overlap with Saga than Heimdall:
  - Skald archives Claude and Codex transcripts, which is adjacent to Bragi's compile inputs.
  - Braid is retrieval and explicitly names Saga as a deferred consumer.
  - Neither was researched beyond its README head. They should be checked separately before a draft claims any Saga feature is superseded.

### Gaps
- The operator's intent cannot be determined from the repo: whether they believe this repo replaced Saga's Heimdall, or plan to rename either component.
- How heavily the desktop daemon is used beyond "started several times, last log write 2026-10-13".

## 2. Architecture and interfaces of algorhythmic/heimdall, against the launcher checklist

### Takeaway
Requests reach the daemon through an authenticated loopback HTTP API. Its clients are the CLI and TUI, an MCP stdio adapter, a browser native helper and a Claude Code hook relay, plus a watched `tasks.yaml`. Everything becomes events in one SQLite log. It acts only on the local desktop: Hyprland windows, browser tabs, reviewed Foot/Herdr/Neovim launches, and evaluator test commands. Most items on the launcher checklist have no counterpart:
- no container execution, image or env policy, secret injection, TTL, kill switch or usage budget
- execution limits are declared permanently out of scope

### Cited Findings
- **Runtime shape:** "The Go daemon owns the database, task state and authorization. The TUI, CLI commands and each MCP stdio adapter connect to it over authenticated loopback HTTP." The diagram is CLI / MCP adapter / browser native helper / TUI → Go daemon → SQLite event log. "No model runner or automatic task dispatcher is included yet." — [README.md#L30-L41](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L30-L41)
- **Request entry:**
  - Loopback endpoint recorded in `endpoint.json`, with the token kept out of normal output. "The endpoint is local-only and has no browser CORS or remote access support." — [README.md#L159](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L159)
  - Route families: `/commands`, `/continuity/*`, `/evidence/*`, `/grants/*`, `/client/*`, `/dependency/*`, `/artifact/*`, `/preservation/*`, `/progress/*`, `/workspace/*`, `/action/*`, `/browser/*`, `/events`, `/state`, `/health`, `/replay`, `/fmt`, `/sync`, `/private/source`. "No CORS, no remote listener." — [docs/design/HANDOFF-heimdall-v1-r4.md#L841-L848](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L841-L848)
  - Claude Code hooks arrive via `heimdall hook`, which POSTs to `/session/hook`. — [internal/daemon/session.go#L45](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/daemon/session.go#L45), [cmd/heimdall/hook.go#L27](https://github.com/algorhythmic/heimdall/blob/c7fee4b/cmd/heimdall/hook.go#L27)
  - `tasks.yaml` is polled with "two stable reads". — [README.md#L161](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L161)
  - There is no file-drop request queue and no MQTT.
- **Request schema:**
  - Strict revisioned task YAML that rejects unknown and duplicate keys. — [docs/STATUS.md "Strict YAML task/workflow parsing"](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/STATUS.md)
  - JSON command bodies carrying `--request-id` for exact retries and `--expected-task-revision` preconditions. — [README.md#L153](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L153)
  - Nothing resembles Saga's `kind/project/instance/image/env/workspace_source`.
- **MCP surface:** six tools: `heimdall_task`, `heimdall_context`, `heimdall_history`, `heimdall_checkpoint`, summary and dependencies. Credentials are scoped, and checkpoint writes are explicitly delegated. — [README.md#L21](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L21), [README.md#L139-L144](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L139-L144)
- **What it executes.** These are all the non-test `exec.Command` sites; none is Docker. It also dispatches Hyprland IPC and browser operations through its own adapters.
  - `$EDITOR`. — [internal/tui/dialogs.go#L725](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/tui/dialogs.go#L725)
  - `braid serve --stdio`. — [internal/retrieval/client.go#L96](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/retrieval/client.go#L96)
  - `git`, for identity and evidence. — [internal/checks/evaluate.go#L98](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/checks/evaluate.go#L98)
  - Evaluator `test.exit` with an absolute argv. — [internal/checks/evaluate.go#L185](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/checks/evaluate.go#L185)
  - WCU observer argv. — [internal/adapters/wcu/observer.go#L87](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/adapters/wcu/observer.go#L87)
  - Reviewed application recipes for Foot, Herdr and Neovim. — [internal/adapters/application/local_linux.go#L50](https://github.com/algorhythmic/heimdall/blob/c7fee4b/internal/adapters/application/local_linux.go#L50)
  - Itself (`heimdall start`). — [cmd/heimdall/up.go#L52](https://github.com/algorhythmic/heimdall/blob/c7fee4b/cmd/heimdall/up.go#L52)
  - `systemctl --user`. — [cmd/heimdall/service.go#L39](https://github.com/algorhythmic/heimdall/blob/c7fee4b/cmd/heimdall/service.go#L39)
- **Result reporting and logging:**
  - Append-only events with projections and receipts. Actions are journaled as request → attempt → observation → verification, with `uncertain` as a first-class outcome. — [docs/design/HANDOFF-heimdall-v1-r4.md#L35-L60](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L35-L60)
  - CLI output is JSON by default. — [README.md#L106](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L106)
- **Policy configuration:**
  - Expiring, revocable, subtree- or resource-scoped grants. Authz is "frozen after S2a". — [r4 §3 Grants row](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L140-L178)
  - Evaluator test runs inherit only `PATH`, system-directory and temp variables, "not … API tokens". — [docs/guides/EVIDENCE-SETUP.md#L54](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/guides/EVIDENCE-SETUP.md#L54)
  - `config.toml` is future work. — [README.md#L165](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L165)
- **Secrets:** per-role loopback tokens and grant credential files only. No secret is injected into workloads. — [README.md#L139-L143](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L139-L143), [README.md#L159](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L159)
- **Dependency ordering:** P04 task prerequisites with "derived satisfaction without task mutation or dispatch". The prerequisites never gate execution. — [docs/STATUS.md (P04 bullet)](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/STATUS.md)
- **Lifecycle look-alikes:**
  - Workspace operations open/focus/close/swap/cancel/reconcile, with "The default resident limit is three". This is a cap on open task workspaces on the desktop, not on agents. — [docs/guides/WORKSPACE-OPERATIONS.md#L52-L60](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/guides/WORKSPACE-OPERATIONS.md#L52-L60)
  - The daemon polls Herdr `agent.list` and records working/blocked/idle agents. This is observation only, and "the recorder never assigns ownership". — [docs/STATUS.md#L20](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/STATUS.md#L20)
  - Startup marks still-`dispatching` actions as uncertain. — [docs/STATUS.md#L18](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/STATUS.md#L18)
  - Notifications and "needs-you" wake conditions are planned for S4. — [README.md#L226-L237](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L226-L237)
- **"Budget" means context size, not usage:** `context TARGET --budget N`. The estimate is `ceil(serialized UTF-8 bytes / 4)`, and a too-small budget returns HTTP 422 `budget_too_small`. — [docs/guides/CONTINUITY-SETUP.md#L89](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/guides/CONTINUITY-SETUP.md#L89)
- **Execution host explicitly excluded:** "**Agent execution is out of scope for Heimdall.** … No run state machine, dispatch outbox, leases, fencing, resource locks, execution limits or execution-host adapter will be added." — [README.md#L239-L245](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L239-L245), [docs/BACKLOG.md#L32-L38](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/BACKLOG.md#L32-L38)
- **The r4 handoff deletes roadmap rows C17–C20:**
  - "C20 execution host | **delete** | attachment is built (W06); launch is herdr's; cancellation of external work is not Heimdall's". — [docs/design/HANDOFF-heimdall-v1-r4.md#L1139-L1141](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L1139-L1141)
  - Its §3 row: "Execution host | none inside Heimdall; agents run in Claude Code, Codex, herdr". — [#L164](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L164)
  - "No model and no agent runs inside Heimdall." — [#L60](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/design/HANDOFF-heimdall-v1-r4.md#L60)
- **What the deleted rows had planned (2026-09-09 baseline):**
  - C17 "Run state machine, dispatch outbox, leases, fencing and resource locks".
  - C18 "Manual handoff/resume, limits, wake conditions and cancellation".
  - C19 "Run controls…".
  - C20 "One verified real execution-host adapter" with "Launch/attach-or-reconcile/status/cancel acceptance".
  - None mention Docker or containers. The plan says "Cooperative metadata fencing is not a filesystem sandbox."
  - Sources: [docs/history/roadmaps/BACKLOG-baseline-2f11175.md#L66-L69](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/roadmaps/BACKLOG-baseline-2f11175.md#L66-L69), [docs/history/roadmaps/IMPLEMENTATION-PLAN.md#L187](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/history/roadmaps/IMPLEMENTATION-PLAN.md#L187)

### Inferences
- The closest this repo came to Saga's launcher role was the C17–C20 agent-run layer: dispatch, limits and cancellation for an external execution host. It was planned for about four days and then deleted in r4 before any code existed. Even then it was aimed at Herdr- and Claude-Code-style sessions on the desktop, not containers.
- **Patterns Saga could borrow (as designs, not code):**
  - idempotent `request-id` retries with refusal of the same id for a different body
  - `uncertain` as a recorded outcome instead of silent loss
  - a scrubbed environment for anything that runs tests
  - expiring, scoped credentials
  The ODIN-IO-CONTRACT outbox and hash-bound approvals already lean this way.

### Gaps
- Request bodies were not traced for every route. Behaviour is taken from docs, code reading and test names; nothing was executed, by constraint.

## 3. Relationship to Saga's in-repo Heimdall

### Takeaway
There is no lineage: different language (Go versus Python), host (desktop user service versus Docker-VM root service), job (desktop continuity versus container launch gate), schema and code. algorhythmic/heimdall does not supersede `odin/scripts/heimdall.py`. Saga's request YAML has no counterpart in it, and it never references `init-dvergr.sh` or Saga images. Saga's heimdall.py, last changed 2026-04-18, is still the only implementation of the Odin-to-Docker gate. Reading it closely also shows that the `commands/` channel which Saga docs and both drafts rely on has no consumer.

### Cited Findings
**Saga's heimdall.py as it actually is**
- **Unit and config:** a root system unit, `Requires=docker.service`, `ExecStart=/usr/bin/python3 ${SAGA_REPO_DIR}/odin/scripts/heimdall.py`, `EnvironmentFile=/etc/saga/heimdall.env`. — [scripts/systemd/heimdall.service:45-89](../../../scripts/systemd/heimdall.service)
- **Queue paths:** `SAGA_LAUNCH_REQUESTS=/opt/saga/odin-ws/launch-requests` and `SAGA_LAUNCH_RESULTS=/opt/saga/odin-ws/launch-results`. — [scripts/systemd/heimdall.env.example:16-25](../../../scripts/systemd/heimdall.env.example)
- **Intake:** polls `launch-requests/*.yml` (`.yml` only) every 2 s. The request id is the file stem. — [odin/scripts/heimdall.py:141, 681, 855](../../../odin/scripts/heimdall.py)
- **Schema and validation rules:**
  - Top-level keys allowed: `kind, project, instance, image, action, env, workspace_source, repo, prd, gitea_credentials, secrets, depends_on`. Unknown keys are rejected. — heimdall.py:151-172, 251-255
  - `kind` must be `dvergr`. — :258
  - Names must match `^[a-z0-9][a-z0-9-]{0,31}$`. — :194
  - `image` must be in `{saga-dvergr:latest, saga-odin:latest}`. — :177-182
  - `action` is `start|stop|restart`, default `start`. — :276-278
  - Env keys in the denylist are rejected: `CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DOCKER_HOST`. Control characters in env values are rejected. — :186-192, :280-293
  - `workspace_source` must resolve under `/opt/saga/workspaces`. — :296-303
  - Each secret name becomes an `UPPER_SNAKE` env var that may not collide with the denylist or with explicit env entries. — :323-341
  - `depends_on` entries are `<project>/<instance>` or a bare instance name; a request may not depend on itself. — :346-366
- **Execution:**
  - Start runs `docker run --name saga-<project>-<instance> --rm --detach --cap-drop=ALL --cap-add=NET_ADMIN --cap-add=NET_RAW -v saga-claude-credentials:/home/vscode/.claude -v <ws>:/workspace -e DVERGR_PROJECT -e DVERGR_INSTANCE [-e DVERGR_REPO] [-v <gitea secret>:/home/vscode/.netrc:ro] <env> <secrets> <image>` with a 60 s timeout. — heimdall.py:504-605
  - Stop runs `docker stop -t 30`. Restart runs stop, then run. — :610-628, :713-724
- **Provisioning:** start and restart create the workspace (chowned to 1000) and copy the PRD. The PRD path is translated from `/workspace/...` to `/opt/saga/odin-ws/...`. — heimdall.py:407-460, 702-709
- **Secrets:**
  - Files live under `/opt/saga/secrets/{projects/<project>,gitea}/`.
  - Each must be a root-owned regular file with no group or other permission bits.
  - Values are injected as `-e` arguments and never logged. Gitea credentials are mounted read-only as `.netrc`.
  - Source: heimdall.py:118-128, 473-501, 536-576
- **Results:**
  - Written to `launch-results/<request_id>.yml` (temporary file, then atomic rename) with fields `request_id`, `status` (one of `approved|rejected|error`), `rc`, `output` (combined stdout and stderr, truncated to 8,192 bytes), `container_name` and `timestamp`. — heimdall.py:146, 633-660
  - `approved` means the docker call returned 0, for start, stop and restart alike. — :726
  - The request file is archived to `processed/` or `rejected/` with a UTC timestamp prefix. — :663-671
- **`depends_on` gating:**
  - A request is held until each dependency's container is not running **and** some result file for that `container_name` has `status: approved`. — heimdall.py:776-806
  - Requests still waiting after 24 h (`SAGA_DEP_WAIT_MAX_SECONDS`) are rejected. — :134, 862-871
  - While a request waits, no result file is written. The only trace is a journald line every 60 s. — :872-878
- **What the daemon does not do:**
  - It has no watcher for `commands/` or `outgoing-commands/`.
  - It has no TTL, concurrency cap, operator-presence gate, kill switch or budget.
  - The README lists those as the "next concrete priority". — [README.md:80-87](../../../README.md)
  - grep over all `*.py` and `*.sh` finds no consumer of `commands/`. — 2026-10-14 grep
- **History and tests:**
  - Last change: `2cf3c05`, 2026-04-18, "fix(heimdall): accept bare instance names in depends_on". — `git log -- odin/scripts/heimdall.py`
  - No tests for heimdall.py exist in the Saga repo. — `find`/`grep` for heimdall tests, 2026-10-14
- **Spec versus code:**
  - The spec's §4 still shows `commands/{project}-{instance}.json` with actions `start | stop | restart | destroy`, and results as `launch-results/{project}.json` with an `instances[]` array.
  - The code implements neither shape: it has no commands channel and no `destroy`, and writes one YAML result per request.
  - Source: [docs/saga-spec.md:470-600](../../../docs/saga-spec.md)
- **Dead `commands/` channel elsewhere in Saga.** Several places tell Odin, or claim, that `commands/` or `outgoing-commands/` reach Heimdall or MQTT. No code implements any of them.
  - ARCHITECTURE.md says `outgoing-commands/ ← Odin writes container commands here; heimdall picks them up`. — [docs/architecture/ARCHITECTURE.md:202-203](../../../docs/architecture/ARCHITECTURE.md)
  - TOPIC-SCHEMA.md says `dvergr/odin/commands` is "Publisher: Odin (via `ratatoskr.py` reading `outgoing-commands/`)". ratatoskr.py contains no such reader. — [mqtt/TOPIC-SCHEMA.md:340](../../../mqtt/TOPIC-SCHEMA.md)
  - Odin's persona says "write a `commands/` record telling heimdall to stop the container" and "`commands/` JSON and `heimdall.py` … handles execution". — [odin/CLAUDE.md:510, 948](../../../odin/CLAUDE.md)
  - Ratatoskr's nudge text says "write a commands/ record for heimdall". — [odin/scripts/ratatoskr.py:401](../../../odin/scripts/ratatoskr.py)

**Side-by-side**

| Aspect | Saga `odin/scripts/heimdall.py` | `algorhythmic/heimdall` |
|---|---|---|
| Purpose | Gate between Odin and Docker | Desktop task and continuity daemon |
| Language and size | Python, 904 lines, no tests | Go, about 49k lines, 109 test files, plus JS, Lua and QML |
| Host | Docker VM 192.168.86.17, root system unit | Omarchy desktop, user unit or ad-hoc `~/.local/bin` |
| Input | YAML files in `launch-requests/` | Loopback HTTP (CLI, TUI, MCP, browser helper, hooks) and `tasks.yaml` |
| Executes | `docker run` / `docker stop` | Hyprland and browser actions, Foot/Herdr/Neovim recipes, test argv, git |
| Results | `launch-results/<id>.yml` | SQLite event log, receipts, `uncertain` outcomes |
| Policy | Hardcoded allowlists in source | Scoped expiring grants; execution limits refused |
| MQTT | Not used by Heimdall (Saga uses it elsewhere) | Rejected as a design choice |
| Last change | 2026-04-18 | 2026-09-11 |

### Inferences
- **No lineage.** Nothing in the algorhythmic repo was copied from, rewritten from or extended from Saga's Heimdall. The shared Norse name and the "deterministic, no model in the loop" ethos are the only overlap. Saga's request schema is neither compatible nor incompatible with it; the concept simply does not exist there.
- **Name collision risk is operational.** Two `heimdall.service` units exist: a system unit on the VM read with `journalctl -u heimdall`, and a user unit on the desktop managed with `systemctl --user`. There are also two `heimdall` executables. They live on different hosts, so collision risk is low. Docs and dev-Claude prompts should still say which one they mean.
- **The `commands/` claims are wrong today, independent of the algorhythmic repo.** The only container-lifecycle path Odin actually has is a launch request with `action: stop|restart`, which must pass the full validation, including image allowlist and `workspace_source`.
- **A depends_on subtlety.** heimdall.py considers a dependency satisfied when its container is gone and its *launch* result was `approved`. Because containers run with `--rm`, a dvergr that crashed also satisfies its dependents. The docstring's "exited cleanly" (heimdall.py:779-783) is not what the code checks. This matters for how the Odin contract describes launch outcomes.

### Gaps
- Whether a private repo outside the `algorhythmic` account re-implements the launcher. The `gh repo list` output included private repos and showed no launcher candidate, but other orgs were not checked.
- Whether Odin's `launch-requests-draft/` and `launch-requests/` share one filesystem, which would make `mv` atomic. Both sit under `/opt/saga/odin-ws`, which suggests yes; this was not verified on the VM.

## 4. Consequences for the two drafts

### Takeaway
Neither draft is wrong *because of* algorhythmic/heimdall: every Heimdall statement in them refers to Saga's heimdall.py, which is still current. They are incomplete in three ways:
- They never disambiguate the name.
- They assume the bounded-usage primitives will be built in Heimdall without saying they are unimplemented, and the standalone tool will never provide them.
- They rely on a `commands/` channel and a "Heimdall sweep" that do not exist.

ODIN-IO-CONTRACT's `send_command`, `fleet_status` and the `host` result vocabulary need redefinition against heimdall.py's real interface. So does its claim that Heimdall is "unchanged".

### Cited Findings
**HARNESS-LANDSCAPE-2026-10.md**
- **L44-49 (§0 item 4):** "Heimdall needs per-image policy". This is correct for Saga's heimdall.py, where `kind` must be `dvergr` (heimdall.py:258) and the credentials mount and cap-adds are unconditional (:522-526). Add "(Saga's `odin/scripts/heimdall.py`, not the unrelated desktop daemon algorhythmic/heimdall)". — [HARNESS-LANDSCAPE-2026-10.md](../HARNESS-LANDSCAPE-2026-10.md)
- **L194-198 and L260-265:** "breaks the Heimdall boundary" and "The deterministic gatekeeper (Heimdall) … unusual but principled". Both remain correct. Optional addition: the operator's own standalone Heimdall applies the same "no model in the coordination loop" rule to desktop actions, which is further precedent.
- **L317-320 (pattern 4):** "A hook on PRD write or launch-request staging that blocks until a verdict exists". Add that heimdall.py itself checks no verdicts. It accepts any valid YAML in the directory, so the gate must sit in the harness or tool, or a verdict-id field must be added to `ALLOWED_REQUEST_KEYS` (heimdall.py:151-172).
- **L352-355 and L424-427:** "Gemini's `ask_user` to `deny` headless as the Heimdall default" and "`ask`-class actions denied, logged and escalated rather than silently allowed". heimdall.py has no ask class: every request is `approved`, `rejected` or `error` (:633-660, :726). State these as new Heimdall features, not adjustments to existing ones.
- **L356-359 (pattern 11):** "Saga's README already wants concurrency caps, TTLs and operator-presence gating in Heimdall; add a token or session-hour budget." This is accurate (README.md:80-87, which also lists a "documented kill switch") but incomplete. Say that none is implemented in heimdall.py, and that the standalone algorhythmic/heimdall explicitly will not supply "execution limits" ([BACKLOG.md#L32-L38](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/BACKLOG.md#L32-L38)). They must be built in Saga's heimdall.py.
- **L424-427 (§5.3):** "budgets and TTLs as already planned". Change to "planned in README.md:80-87; not implemented".
- **L447-452 (§6 Step 1):** "outbound actions (… launch-request drafts, commands …) … Today these are a dozen directory conventions in `odin/CLAUDE.md` and `ratatoskr.py`". Add that `commands/` is a convention with no consumer. heimdall.py reads only `launch-requests/*.yml`, and ratatoskr.py has no `outgoing-commands/` reader despite TOPIC-SCHEMA.md:340 and ARCHITECTURE.md:202-203. Today a stop is a launch request with `action: stop`.
- **L498 (§6 Step 4):** "Heimdall per-image policy". Same disambiguation as L44-49. Also note this needs `kind` values beyond `dvergr` and image-keyed mount and env rules in `validate()` and `exec_docker_run()`.
- **Research basis:** the notes README does not list a Heimdall comparison. Add this file and its conclusion: the algorhythmic repo is not a launcher and supersedes nothing. — [harness-research-2026-10/README.md](README.md)

**ODIN-IO-CONTRACT.md**
- **L15-18 and L395:** "It does not change Mimir, Heimdall, …" and "Mimir, Heimdall, dvergar, Bragi unchanged". These are inconsistent with §5. As drafted, `send_command` (with `destroy`) and `fleet_status`'s "Heimdall sweep" need Heimdall features that do not exist. Choose one:
  - **(a)** Keep Heimdall unchanged and redefine those tools as described below.
  - **(b)** List the Heimdall changes explicitly: a `commands/` watcher or `destroy` action, a container-inventory snapshot, and a pending or queued result.
- **L68:** `ref` "a launch-request name". Define it as the `requestId`, which is the request file stem, heimdall's `request_id` and the result file stem. — heimdall.py:681, 642
- **L79 (`host` kind):** "Heimdall launch results and rejections". Add:
  - `error` (docker non-zero exit, timeout or exception; heimdall.py:726, 734-753)
  - dependency-timeout rejections (:862-871)
  - "queued, waiting on depends_on", which Heimdall never reports, so the harness must infer it from the absence of a result
- **L116 (Heimdall row):** `[heimdall] <name>: accepted/rejected/stopped — <stderr tail>`. Corrections:
  - The real statuses are `approved|rejected|error`.
  - The result has no `action` field, so "stopped" must come from joining to the staged request in the outbox.
  - `output` is combined stdout and stderr, truncated to 8 KB.
  - Wake classes should be: `rejected` and `error` → **wake**; `approved` → **log only**.
  - Dedupe key: "result filename" is unsafe because a reused requestId overwrites the same `launch-results/<id>.yml` (:642-660). Use `(filename, timestamp)` and make requestIds unique per attempt.
- **L137-138 (wake table):** add "Heimdall errors" to **wake**, and rename "accepted launch results" to "approved launch results".
- **L209-213 and L308-311:** "the tool refuses launches that lack an approved verdict". Make explicit that this is the *only* verdict gate. Heimdall accepts any valid YAML placed in `launch-requests/`, so the harness must be Odin's only writer to that directory.
- **L222:** "These tools replace … `commands/`". Change to "replace the documented-but-unconsumed `commands/` convention".
- **L229 (`fleet_status`):** "container list from the last Heimdall sweep". Heimdall does no sweep and publishes no inventory; its only `docker ps` call is an internal dependency check (heimdall.py:756-773). Either:
  - derive the list from MQTT `status` and `heartbeat` plus `launch-results/`, or
  - add a Heimdall sweep that writes, for example, `launch-results/_containers.yml`, and list it as a Heimdall change.
- **L233 (`stage_launch_request(yaml)`):** "Validates against Heimdall's schema locally". The rules are those in Saga's heimdall.py `validate()`: the allowed key set, `kind: dvergr`, `NAME_RE`, the image allowlist, `action ∈ {start, stop, restart}`, the env denylist with no control characters, `workspace_source` under `/opt/saga/workspaces`, secret-name → env-var collision checks, and `depends_on` format with no self-dependency (heimdall.py:240-384). Also define:
  - Share the code, or a schema generated from it, so the two validators cannot drift. heimdall.py has no tests to catch drift.
  - Mark the host-only checks the tool cannot perform: secret file existence, owner and mode; PRD existence after the `/workspace` → `/opt/saga/odin-ws` translation; dependency satisfaction.
  - Enforce the persona rule `gitea_credentials: saga-push`. — [odin/CLAUDE.md step 9](../../../odin/CLAUDE.md)
  - Return a requestId that is filename-safe and unique per attempt.
- **L234 (`launch(requestId)`):** "Moves a draft into `launch-requests/` … Result arrives as a `host` message." Specify:
  - Write `<requestId>.yml` by atomic rename on the same filesystem. Heimdall globs `*.yml` every 2 s, and a partially written file is rejected as a YAML parse error (:682-688).
  - No result appears while `depends_on` is open, for up to 24 h (:134).
  - `approved` means only that `docker run --detach` returned 0. Completion comes from MQTT `status`, not from Heimdall.
  - Dependents can start after a prerequisite crashes (§3 above), so a dependent's launch is not evidence that its prerequisite succeeded.
- **L235 (`send_command(project, instance, action, reason)`):** "Writes a `commands/` record for Heimdall (`stop`, `restart`). Operator approval required for `destroy`." This does not match the code: there is no `commands/` consumer and no `destroy` action anywhere. Against heimdall.py as it is:
  - `send_command` should compose a launch request with `action: stop|restart` for `saga-<project>-<instance>`. It must still carry a valid `kind`, allowlisted `image` and `workspace_source`, and a `prd` or existing `PRD.md` for restart. Drop it through the same path as `launch`.
  - `reason` must stay in the harness log, because Heimdall rejects unknown keys (:251-255).
  - Either drop `destroy` or specify it as a new Heimdall action. Note that `--rm` already removes the container on stop, so "destroy" would have to mean workspace deletion, which today requires operator action under `/opt/saga/`.
- **L242 (`shell`):** "Heimdall remains the only launcher." Correct.
- **L308-311 (§8 Heimdall):** "drop validated YAML into `launch-requests/` or a record into `commands/`". Change to "drop validated YAML (`action: start|stop|restart`) into `launch-requests/`; results in `launch-results/<requestId>.yml`". Add one line: "This is Saga's `odin/scripts/heimdall.py`; the operator's standalone algorhythmic/heimdall is an unrelated desktop continuity daemon."

### Inferences
- If the operator wants the contract to keep "Heimdall unchanged", option (a) above is the minimal consistent edit: `send_command` becomes a launch request with an `action`, `destroy` is removed, and `fleet_status` derives containers from MQTT. Option (b) is the natural place to add the README's concurrency cap, TTL, presence gate and kill switch, since the contract already plans a Heimdall-facing outbox.
- The same `commands/` correction applies outside the drafts: `odin/CLAUDE.md:510,948`, `odin/scripts/ratatoskr.py:401`, `mqtt/TOPIC-SCHEMA.md:340`, `docs/architecture/ARCHITECTURE.md:202-203` and `docs/saga-spec.md` §4 command and result formats.

### Gaps
- It is not known whether the live Odin has ever written a `commands/` record, or whether a stop was ever attempted that way. That would need inspecting `/opt/saga/odin-ws/` on the VM, which was not done from this host.

## 5. Gaps and risks

### Takeaway
algorhythmic/heimdall is a well-documented but young, unreleased and currently red-CI desktop tool that is unrelated to container launching. The material risks for Saga's drafts are three: the name collision; reliance on a non-existent `commands/` channel; and an untested Python Heimdall whose real result vocabulary and depends_on semantics differ from what the drafts and spec describe.

### Cited Findings
- **algorhythmic/heimdall CI:**
  - The workflow runs `go test`, `go vet`, build, extension tests and about 20 Node smoke scripts on ubuntu-latest and windows-latest. — [.github/workflows/test.yml](https://github.com/algorhythmic/heimdall/blob/c7fee4b/.github/workflows/test.yml)
  - Of 29 runs, the 11 most recent all **failed**, through HEAD `c7fee4b`. The last success was `f58cc28` (W06) at 2026-09-09T18:23Z. — [GitHub API `actions/runs`](https://api.github.com/repos/algorhythmic/heimdall/actions/runs)
- **algorhythmic/heimdall maturity:**
  - "These are development milestones, not a complete v1 release." — [README.md#L28](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L28)
  - Native-host installation, workspace recovery and macOS acceptance are open. — [README.md#L59](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L59)
  - Notifier and planner are S4, mail and packaging are S5. — [README.md#L226-L237](https://github.com/algorhythmic/heimdall/blob/c7fee4b/README.md#L226-L237)
- **algorhythmic/heimdall docs:** about 24 setup guides under `docs/guides/`, design docs (r4 handoff, about 1,160 lines), STATUS, BACKLOG, a capability ledger and verification records. — [docs/README.md](https://github.com/algorhythmic/heimdall/blob/c7fee4b/docs/README.md)
- **Saga heimdall.py:**
  - No tests in the repo.
  - Spec §4 formats differ from the code. — [docs/saga-spec.md:470-600](../../../docs/saga-spec.md)
  - The `commands/` channel is unconsumed (§3 above).
  - A crashed prerequisite satisfies `depends_on`. — heimdall.py:776-806

### Inferences
- **Why CI is red:** probably the Linux PTY or browser acceptance steps added after W06, rather than unit tests. This is a guess: the failing job logs were not read.
- **Risk of conflation:** a future agent asked about "Heimdall" on the operator's desktop will find `~/.local/bin/heimdall` and `~/Projects/heimdall` first, and could treat the desktop daemon as Saga's launcher. A one-line disambiguation in Saga's CLAUDE.md glossary would prevent that.
- **Risk of drift:** if ODIN-IO-CONTRACT's `stage_launch_request` re-implements validation in the harness, it will drift from heimdall.py, which has no tests. Shared code or a shared schema plus a few golden-request tests would close that.

### Gaps
- CI failure logs were not read, so the cause of the red CI is undetermined.
- The algorhythmic test suite was not run, by the no-execute constraint.
- Skald and Braid were not examined beyond README heads. Whether either supersedes a Saga component (Bragi, the lessons store) is undetermined and should be researched separately.
- The live VM state was not inspected: the deployed heimdall.py revision on 192.168.86.17, `/opt/saga/odin-ws/launch-results/`, and any stray `commands/` files.
