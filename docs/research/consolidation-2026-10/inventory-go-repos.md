# Inventory of heimdall, skald and braid for the Odin consolidation plan

*Examined 2026-10-16. Local checkouts: `/home/david/Projects/heimdall` (HEAD `3ca80b5`), `/home/david/Projects/skald` (HEAD `22114dd`), `/home/david/Projects/braid` (HEAD `7e24af3`). The method was read-only: `git log/ls-files/show/diff`, `grep`, `sed`, `wc` and `ls`. Nothing was built, run, fetched or modified. I also took `ls` metadata of the installed binaries and data directories, and ran `pacman -Qi herdr`. I did not query the GitHub API, so the CI results below come from in-repo files and from the 2026-10-14 research notes. Line counts are physical lines (`wc -l`) of tracked files. Paths are repo-relative unless absolute.*

---

## 0. Most consequential findings

1. **Heimdall already embeds skald's capture library in-process.** go.mod requires `github.com/algorhythmic/skald v0.1.1`. It is mislabelled `// indirect`, but `internal/session/service.go` and `internal/daemon/session.go` import it directly. This proves that "capture as a module writing into another store" works. Heimdall's consumer, however, keeps only lifecycle and description metadata (evidence blobs of at most 4 KiB), not the full transcript.
2. **Heimdall's sensors cannot be lifted out as they are.** All state lives in one Go struct, `model.State` (62 fields, 58 of them maps; `internal/model/model.go:145-210`). It is serialized as a single JSON row, `projection_state`, which is rewritten on every command (`internal/store/store.go:258`). One central `Apply` switch handles 29 event subjects (84 subject.verb pairs). Several sensors are tied to task records:
   - Herdr agent polling only watches sockets from task-bound session bindings (`internal/workspace/agents.go:56`).
   - Conversations are attributed to tasks through task `Resources` (`internal/session/service.go:204`).
   - The browser popup writes task captures (`internal/browser/service.go:476`).
3. **Three target-architecture assumptions are not met by the code:**
   - There is no "ranked work session plan", planner or notifier (S4, planned only).
   - There is no Neovim sensor. The Neovim Lua module is a task UI over the CLI.
   - There is no SSE or change feed. Heimdall's `/events` returns the whole log, and skald's `changes` table is written but never read.
4. **The plan's five-way split leaves out a sixth heimdall layer.** Desktop workspace and actuation (snapshots, recovery, Hyprland dispatch, browser commands, app-launch recipes, action journals) is **9,567 non-test LOC and 6,193 test LOC**, as large as the task core. Guarded keyboard and mouse input proper is in WCU, a separate Python repository. Heimdall only records intents and reports for it.
5. **Braid can be embedded as a library: it is pure Go, has no globals and no env reads.** It does make demands on its host:
   - It always opens its *own* SQLite file per dataset (`pkg/braid/store.go:29-56`).
   - It recomputes a SHA-256 digest over all nodes, edges and vectors on *every* write (`pkg/braid/dataset.go:143`).
   - Dense, graph and temporal queries load every filtered node and every vector into memory.
   - The stdio protocol v1 lives in `package main`.
6. **Odin's own `docs/DECISIONS.md` D10 is still marked "(locked)".** It says "The standalone tools stay separate … Nothing rolls into Odin", with braid as a child process. The consolidation needs a superseding decision.
7. **Both tools hold live operator data:**
   - skald `archive.sqlite` is 1.5 GB, plus about 2.4 GB of pre-upgrade backups, last written 2026-10-15 23:14.
   - heimdall `heimdall.db` is 3 MB plus a 4.5 MB WAL, last written 2026-10-15 22:24.

   A migration is unavoidable.
8. **The same transcript gets different identity keys in the two tools.** Heimdall derives the capture namespace from `os.Hostname()` (`internal/daemon/session.go:135`), skald from `/etc/machine-id` (`cmd/skald/connect.go:200`). Records will not join until one rule is chosen.

---

## A. Per-repository inventory

### A.1 heimdall

| Item | Value | Evidence |
|---|---|---|
| Module path | **`heimdall`** (bare, not `github.com/...`) | `go.mod:1` |
| Go | `go 1.25.0`, `toolchain go1.27.1` | `go.mod:3-5` |
| Direct deps | `gdamore/tcell/v2 v2.13.10`, `modelcontextprotocol/go-sdk v1.7.0`, `rivo/uniseg v0.4.7`, `golang.org/x/sys v0.41.0`, `golang.org/x/term v0.37.0`, `gopkg.in/yaml.v3 v3.0.1`, `modernc.org/sqlite v1.38.2` | `go.mod:7-15` |
| Effectively direct but marked `// indirect` | `github.com/algorhythmic/skald v0.1.1` (imported by `internal/session`, `internal/daemon`); go.sum also holds v0.1.0 | `go.mod:18`, `go.sum:1-4` |
| Go size | 201 non-test files / **33,582 LOC**; 109 test files / **15,339 LOC**; 293 `func Test` (294 including fuzz) | `git ls-files '*.go'` + `wc` |
| Binaries | `cmd/heimdall` is a single multi-mode binary. It also runs as the browser native host when argv0 is `heimdall-browser-host` or `browser-host` | `cmd/heimdall/main.go:30-40` |
| Other code | `extension/` (MV3 Chromium extension v0.6.1, perms `nativeMessaging, tabs, storage, alarms`; 26 files, 676 dense lines / 57 KB); `integrations/neovim/lua/heimdall/*.lua` (3 files, 840 lines); `contrib/omarchy/heimdall/Heimdall.qml` (553) + `manifest.json` (61); `schemas/` 22 JSON schemas (2,608 lines); `testdata/` 63 files, 2.25 MB (schema-17/19/20 SQL dumps, golden events); `scripts/` 28 Node `.cjs` smokes, 4 Python fixtures, 3 PowerShell, 1 Lua, an npm `browser-test` package; `docs/` 98 files | `git ls-files` |
| Build | `Makefile` (build/test/vet/install into `~/.local/bin`) | `Makefile` |
| Packaging | `PKGBUILD` `heimdall-git`, `pkgver=r25.gd3e4694` (stale), **`license=('custom')`** (stale after the Apache license). Installs the binary, the extension under `/usr/lib/heimdall/extension`, Neovim files under `/usr/share/heimdall/neovim`, and docs. A locally built `heimdall-git-r25.gd3e4694-1-x86_64.pkg.tar.zst` (2026-09-10) is git-ignored | `PKGBUILD:7,12`, `.gitignore` |
| systemd | User unit `contrib/systemd/heimdall.service` (`ExecStart=%h/.local/bin/heimdall start --data-dir %h/.local/share/heimdall`); `heimdall service install` writes the same unit to `~/.config/systemd/user` | `contrib/systemd/heimdall.service`, `cmd/heimdall/service.go:20-36` |
| CI | `.github/workflows/test.yml`: matrix ubuntu-latest + windows-latest; go test/vet/build, Node 24 extension tests, `tsc --strict`, Playwright Chromium (Linux), and about 20 Node smoke scripts | `.github/workflows/test.yml` |
| CI status | **Red, as far as can be determined.** The last published pass recorded in-repo is W06 `f58cc28` (`docs/VERIFICATION.md:16`). The 2026-10-14 notes (GitHub API) recorded the 11 most recent runs failing through `c7fee4b`. The README now says "current CI success is not claimed" (`README.md:29`). The uncommitted fix in `internal/core/materialize_test.go` (EvalSymlinks for "Windows short temp paths and symlinked TMPDIRs") looks like work on a platform-specific test failure (inference) | as cited |
| License | **Apache-2.0 `LICENSE`, added 2026-10-14 10:42:05 -0700 in `3ca80b5`**. `docs/licenses/` holds 30 third-party notice files | `git log -- LICENSE` |
| Tags / releases | **None.** README describes "development milestones, not a complete v1 release", schema 22 | `git tag`, `README.md:63` |
| Commits | 36 total (7 by "Algorhythmic", 29 by David Alexander Dunn); first `2aa2457` 2026-09-04 | `git log` |
| Last 5 commits | `3ca80b5` 2026-10-14 docs: refresh README, add dashboard screenshot and Apache license · `c7fee4b` 2026-09-10 Add supervised Braid retrieval (S3.1 foundation) · `5bc272c` 2026-09-10 Deliver S1 acceptance and start S2b startup readiness · `fb6b30d` 2026-09-10 Complete S1.4 sensor surface and S1.5 acceptance coverage · `1b9e02a` 2026-09-10 Implement S1.2 direct session consumer with pinned Skald capture | `git log -5` |
| Dirty tree | `M internal/core/materialize_test.go` (+7/−1, EvalSymlinks on `t.TempDir()`). Ignored but present: `.private/` (a nested dotprivate sparse checkout with ingested docs), `.tools/`, `bin/`, `demo-data/`, the `heimdall` binary, `pkg/`, `src/`, the package archive, `scripts/browser-test/node_modules/` | `git status --ignored` |
| Live install | `~/.local/bin/heimdall` (25 MB, 2026-09-10 23:54), `~/.local/bin/braid`. Data in `~/.local/share/heimdall`: `heimdall.db` 3 MB + WAL 4.5 MB modified 2026-10-15 22:24; `endpoint.json` from 2026-10-14 15:37 still present but no process running, so the last exit was unclean; `braid/braid.yaml` + `braid/heimdall.db` (100 KB). No user unit installed | `ls -la` |
| Changes since the 2026-10-14 notes | License added; README rewritten ("Part of: the agent runtime … Skald is integrated; Braid integration is partial"); MCP tool list corrected (see B.4); dirty test file; 36 commits instead of 35 | `git show 3ca80b5` |

**Package layout (every package directory; non-test LOC / test LOC):**

| Package | Files | LOC | Test files | Test LOC | Package doc / role |
|---|---:|---:|---:|---:|---|
| `cmd/heimdall` | 31 | 3,581 | 6 | 543 | CLI, daemon launcher, browser-host mode |
| `internal/actions` | 2 | 738 | 6 | 1,740 | "shared task-bound intent and attempt history" (C12/S2a) |
| `internal/adapters/application` | 3 | 249 | 1 | 52 | reviewed launch recipes (foot / foot-herdr / foot-nvim) |
| `internal/adapters/dotprivate` | 1 | 248 | 1 | 96 | inspects dotprivate mirrors for preservation |
| `internal/adapters/herdr` | 3 | 511 | 2 | 271 | Herdr 0.8.2 / protocol 20 socket client |
| `internal/adapters/hyprland` | 7 | 1,070 | 5 | 499 | Hyprland IPC: observer, attention, inventory, **dispatch** |
| `internal/adapters/wcu` | 4 | 387 | 1 | 142 | read-only WCU Desktop Observer over MCP stdio |
| `internal/authz` | 1 | 157 | 0 | 0 | expiring, task-scoped read credentials |
| `internal/browser` | 8 | 1,510 | 6 | 930 | browser ingress, pairing, verification, command queue |
| `internal/capture` | 1 | 78 | 1 | 19 | quick-capture *line parser* (task captures, not transcripts) |
| `internal/checks` | 2 | 516 | 2 | 431 | evidence evaluators (runs git and `test.exit` argv) |
| `internal/client` | 1 | 139 | 0 | 0 | scoped-credential API client |
| `internal/continuity` | 14 | 2,950 | 16 | 2,047 | contracts, decisions, checkpoints, resources, progress, preservation, summaries, resume |
| `internal/conversation` | 2 | 442 | 1 | 76 | conversation source, record and checkpoint types |
| `internal/core` | 3 | 1,105 | 2 | 522 | command boundary, `tasks.yaml`, check materialization |
| `internal/daemon` | 19 | 1,726 | 8 | 537 | loopback HTTP server; starts every service goroutine |
| `internal/mcpbridge` | 1 | 179 | 1 | 140 | MCP stdio adapter (6 tools) |
| `internal/model` | 27 | 4,707 | 4 | 182 | **monolithic** domain model (`State` and every record type) |
| `internal/nativebridge` | 2 | 258 | 1 | 76 | framed browser native-messaging proxy |
| `internal/resourceobs` | 1 | 202 | 0 | 0 | file/tree digest observation |
| `internal/retrieval` | 2 | 325 | 1 | 49 | supervises `braid serve --stdio` |
| `internal/session` | 2 | 629 | 1 | 236 | transcript and hook consumer built on skald `sessioncapture` |
| `internal/store` | 33 | 4,529 | 29 | 3,338 | event log, projection, per-domain reducers |
| `internal/surface` | 1 | 146 | 1 | 123 | URL/surface identity normalization |
| `internal/testdesktop` | 1 | 103 | 0 | 0 | synthetic IPC fixtures |
| `internal/tui` | 10 | 2,992 | 3 | 615 | tcell terminal dashboard |
| `internal/workspace` | 19 | 4,105 | 10 | 2,675 | manifests, Herdr binding, snapshots, previews, operations, recovery, plus agent, attention and viewport sensors |

### A.2 skald

| Item | Value | Evidence |
|---|---|---|
| Module path | `github.com/algorhythmic/skald` | `go.mod:1` |
| Go | `go 1.25.0`, `toolchain go1.27.1` | `go.mod:3-5` |
| Direct deps | `google/jsonschema-go v0.4.3` (used only in `sessioncapture/capture_test.go`), `gdamore/tcell/v2 v2.13.10`, `rivo/uniseg v0.4.7`, `modernc.org/sqlite v1.38.2` | `go.mod:7-13` |
| Go size | 30 non-test files / **7,314 LOC**; 13 test files / **2,424 LOC**; 50 test/fuzz funcs | `wc` |
| Binaries | `cmd/skald`: daemon (`serve`), TUI (default), CLI (`sources/connect/status/sessions/artifacts/get/backup/restore/inspect/probe/discover/validate/version`) | `cmd/skald/main.go:22-47` |
| Public packages | `sessionrecord`, `sessioncapture` (contract "v1"; "import no Heimdall code, database, task state, hooks …") | `docs/CONTRACT-V1.md:1-10` |
| Build | `Makefile` (prefers `.tools/go`; `GOCACHE`/`GOMODCACHE` under `.cache`; test target runs `python3 scripts/check_schema.py`; smoke/tui-smoke/demo/discovery-smoke are Python) | `Makefile` |
| Packaging | `PKGBUILD` `skald` `pkgver=0.1.0` (stale versus tag v0.1.1), **`license=('custom')`** (stale); installs only the binary and README. A local `skald-0.1.0-1-x86_64.pkg.tar.zst` (2026-09-10) is git-ignored | `PKGBUILD:4-10` |
| systemd | **None** ("packaging and user units are pending") | `docs/ARCHIVE-SETUP.md` |
| CI | **None.** No `.github/`; the README says "there is no CI workflow in this repository" | `README.md` (2026-10-14 diff) |
| License | **Apache-2.0, added 2026-10-14 10:42:05 -0700 in `22114dd`** | `git log -- LICENSE` |
| Tags | `v0.1.0` → `54e6871` (2026-09-10, "sessionrecord v1 contract, archive schema 2"); `v0.1.1` → `cc5f0f7` (2026-09-10, "aiTitle titles, Devin source, session page loading"). Three commits after v0.1.1: two touch only `internal/tui`, `internal/archive/store_test.go` and `sessioncapture/devin_test.go`. **The library code heimdall pins (v0.1.1) is identical to HEAD for non-test files** | `git diff --stat v0.1.1 HEAD` |
| Commits | 14 | |
| Last 5 commits | `22114dd` 2026-10-14 docs: refresh README, add archive screenshot and Apache license · `d364f8f` 2026-09-10 Cover continuation, file-evidence projects, and TUI controls · `c9b2d86` 2026-09-10 Fold duplicate titles and add overview ordering · `cc5f0f7` 2026-09-10 Project Devin liveness from WAL growth and file-evidence repos · `27d5f90` 2026-09-10 Load all session pages and derive Devin projects from file evidence | `git log -5` |
| Dirty tree | Clean. Ignored: `.cache/`, `.tools/`, `bin/`, `pkg/`, `src/`, `scripts/__pycache__/`, the package archive | `git status --ignored` |
| Live data | `~/.local/share/skald/archive.sqlite` **1.50 GB** (+12 MB WAL), last write 2026-10-15 23:14; pre-upgrade copies `pre-schema-3/4/5-*.sqlite` (0.59 + 0.59 + 1.26 GB); total 3.7 GB; `~/.local/bin/skald` dated 2026-09-10 23:01 | `ls -la`, `du` |
| Other files | `SKALD-IMPLEMENTATION-PLAN.md` (952 lines), `SKALD-HEIMDALL-AMENDMENT.md` (382), `STATUS.md`, two HTML mockups, `schemas/session-record-v1.schema.json` (461), `testdata/{claude,codex}/session.jsonl`, `testdata/identity-v1.json`, `examples/fixture-sources.json`, 6 Python scripts (517 lines) | `git ls-files` |

| Package | Files | LOC | Test files | Test LOC |
|---|---:|---:|---:|---:|
| `cmd/skald` | 4 | 748 | 2 | 149 |
| `internal/archive` | 6 | 1,986 (+274 SQL in 5 migrations) | 2 | 787 |
| `internal/client` | 1 | 62 | 1 | 41 |
| `internal/daemon` | 6 | 1,122 | 2 | 423 |
| `internal/tui` | 6 | 2,046 | 2 | 402 |
| `sessioncapture` | 5 | 1,026 | 3 | 506 |
| `sessionrecord` | 2 | 324 | 1 | 116 |

### A.3 braid

| Item | Value | Evidence |
|---|---|---|
| Module path | `github.com/algorhythmic/braid` | `go.mod:1` |
| Go | `go 1.24.0` (no toolchain line) | `go.mod:3` |
| Direct deps | `gopkg.in/yaml.v3 v3.0.1`, `modernc.org/sqlite v1.38.2` | `go.mod:5-8` |
| Go size | 20 non-test files / **4,213 LOC**; 15 test files / **1,922 LOC**; 51 tests + 1 benchmark | `wc` |
| Binaries | `cmd/braid` (CLI and `serve --stdio`) | `cmd/braid/main.go` |
| Build | `scripts/dev.sh` (Go wrapper, prefers `.tools/go`), `scripts/verify-contract.sh` (needs Go, `jq`, GNU `timeout`; dataset `heimdall:contract`). No Makefile or PKGBUILD | `scripts/` |
| systemd / packaging | None | |
| CI | `.github/workflows/test.yml`: ubuntu-latest; `bash -n`, `dev.sh test -race`, vet, build, `verify-contract.sh`. **Green**: the 2026-10-14 notes recorded 5/5 successful runs. The run for `7e24af3` (docs only) is not determinable from files | `.github/workflows/test.yml` |
| License | **Apache-2.0, added 2026-10-14 10:42:05 -0700 in `7e24af3`** (same timestamp as the other two, so one batch) | `git log -- LICENSE` |
| Tags | `v0.1.0` → `41bc392` (tag dated 2026-09-10, "Pin subprocess protocol v1 + dataset APIs for Heimdall S3"); one commit after it (docs and license) | `git tag` |
| Commits | 6 | |
| Last 5 commits | `7e24af3` 2026-10-14 docs: clarify runtime context and add Apache license · `41bc392` 2026-09-09 docs: explain exact and lexical retrieval in README · `65c7f6e` 2026-09-07 build: replace PowerShell helpers with Bash for Linux · `9941b21` 2026-09-07 docs: publish retrieval contracts and catalog benchmarks · `7602263` 2026-09-07 feat: enforce constrained and revision-consistent retrieval | `git log -5` |
| Dirty tree | Clean, nothing ignored present | `git status --ignored` |
| README change 2026-10-14 | "Braid is Heimdall's planned retrieval layer; Heimdall has a partial publish/query path"; "Saga is deferred" retained | `git show 7e24af3` |

| Package | Files | LOC | Test files | Test LOC |
|---|---:|---:|---:|---:|
| `cmd/braid` | 3 (`main.go` 278, `protocol.go` 407, `reindex_jobs.go` 75) | 760 | 5 | 418 |
| `pkg/braid` | 17 | 3,453 | 10 | 1,504 |

---

## B. Heimdall decomposition

### B.1 Layers, with LOC

The packages are mixed, so I classified heimdall at **file** level. Every non-test file is assigned exactly once, and the totals reconcile to 33,582 / 15,339. Test files were assigned by matching base name or by the dominant layer of their package.

| Layer | Non-test files | Non-test LOC | Test files | Test LOC | Contents |
|---|---:|---:|---:|---:|---|
| (1) **Sensor / adapter** | 64 | **8,607** | 30 | 3,932 | Hyprland observer, attention, inventory, transport; Herdr adapter; WCU observer; `browser/*` + `nativebridge` + `surface` + `resourceobs`; `session` + `conversation` (skald consumer); `workspace/{agents,attention,viewport,application_observation,browser_pairing}`; sensor reducers in `store/` (agent, compositor_focus, focus, observed_surface, sensor, source, conversation*, viewport, browser_pairing); sensor types in `model/` (agent, sensor, observed_surface, focus, conversation, browser, browser_pairing, viewport); daemon/cmd glue (session, conversation, browser, viewport, herdr, source, hook) |
| (2) **Task core** | 55 | **9,561** | 34 | 4,129 | `core`, `capture`, `continuity`, `checks`, `authz`, `adapters/dotprivate`; `model/{model,continuity,dependency,evidence,grant,preservation,progress,artifact,scope}`; matching `store/`, `daemon/`, `cmd/` files |
| (6) **Workspace / actuation** (not in the plan's list) | 54 | **9,567** | 36 | 6,193 | `actions`, `adapters/application`, `adapters/hyprland/dispatch.go`, `testdesktop`; `workspace/{service,herdr,snapshot*,preview*,operation*,recovery*,application*}`; `model/{action,application,external_*,native_action,snapshot_payload,workspace*,browser_verification}`; matching `store/`, `daemon/`, `cmd/` files |
| (3) **Human UI** | 11 | **3,070** | 3 | 615 | `internal/tui`, `cmd/heimdall/ui.go`; plus non-Go: Omarchy QML bar (614 lines), Neovim Lua (840 lines), extension popup |
| (4) **Agent interfaces** | 10 | **1,683** | 3 | 296 | `mcpbridge`, `client`, `cmd/heimdall/{main,mcp,service,up*,doctor}.go`, `daemon/daemon.go` (HTTP server); `cmd/heimdall/hook.go` (Claude Code hook relay) is counted under sensors |
| (5) **Retrieval** | 3 | **412** | 1 | 49 | `internal/retrieval`, `cmd/heimdall/retrieval.go` |
| Shared infrastructure | 4 | 682 | 2 | 125 | `store/store.go` (event log, Transact, Apply, Replay), `store/backup.go`, file locks |

The full file-to-layer map is in this session's scratchpad as `layer_files.txt` and `test_layer.txt`.

**Facts the plan should know about each layer:**

- **Sensor:**
  - The browser layer is both an observer and an actuator. `service.go` (524) queues `open/navigate/focus/move/close` commands.
  - Hyprland observation is read-only, but `dispatch.go` in the same package sends native window commands over `.socket.sock` (`internal/adapters/hyprland/dispatch.go:168`).
- **Agent interfaces:**
  - **There is no SSE.** `grep` finds no `text/event-stream`.
  - `/events` returns the entire log with no cursor (`internal/store/store.go:515`).
  - The daemon serves 88 route paths on `127.0.0.1:0` with three bearer tokens (CLI, browser, scoped grants) written to `endpoint.json`, `client-endpoint.json` and `browser-endpoint.json` (`internal/daemon/daemon.go:78-110`).
- **Human UI:**
  - The TUI reads the whole projection through `GET /state` and imports DTO types from `core`, `continuity`, `workspace`, `browser` and `checks`.
  - The Omarchy bar shells out to `heimdall status --json` every 5 s (`contrib/omarchy/heimdall/Heimdall.qml:140`). Its offline hint says "`heimdall serve`", but the verb is `start`.
  - The TUI also reads `$XDG_STATE_HOME/omarchy/agents/usage/` (`internal/tui/usage.go:21-36`).
- **Neovim is not a sensor.** `integrations/neovim/lua/heimdall/*.lua` runs `heimdall resume`, `heimdall checkpoint draft/submit` and `heimdall tui` via `vim.system` and `jobstart`. Neovim appears in the workspace layer only as a relaunch recipe (`foot-nvim`).
- **Planner and scheduler:** nothing implements ranked plans, a planner or notifications (`grep -i planner|ranked|notif` finds nothing). README: "planning and notifications remain planned" (`README.md:29`); S4 row (`README.md:274`). The only scheduling is `timer.*` events: capture expiry, `resume_by` reminders and `silence` checks, processed by `tick`.

### B.2 SQLite tables and state ownership

There are **no migration files.** `store.Open` runs inline `CREATE TABLE IF NOT EXISTS` statements, takes a pre-upgrade backup for markers 1–21, and sets `PRAGMA user_version=22` (`internal/store/store.go:92-120`). Upgrades rely on replaying events (`Replay`, `store.go:541-606`). There are only **7 tables**:

| Table | Owner layer | Definition |
|---|---|---|
| `events(id, event_version, ts, subject, verb, actor, entity_id, command_id, payload json, idempotency_key UNIQUE)` | shared (all layers) | `store.go:117` |
| `projection_state(id=1, body json)`, which holds the **whole `model.State`** | shared | `store.go:118`, rewritten at `store.go:258` |
| `commands(id, request_hash, result)`: request-id idempotency | shared | `store.go:119` |
| `workspace_snapshots`, `workspace_snapshot_payloads` (128 MiB cap) | workspace (W03) | `internal/store/snapshot_sql.go:11-18` |
| `conversation_evidence(digest, body ≤4096 B)`, `conversation_description_associations` | sensor (S1 capture) | `internal/store/conversation_sql.go:14-25` |

Real ownership is by **event subject** and **`model.State` field** (`internal/model/model.go:145-210`):

| Layer | Event subjects (`store.Apply`) | `model.State` maps |
|---|---|---|
| Sensor | `surface.{observed,opened,closed,changed,focused}`, `workspace.focused`, `browser.{profile_seen,pairing_changed,inventory_observed,inventory_delta,association_observed}`, `agent.{observed,detached}`, `sensor.{degraded,recovered}`, `source.{configured,activated,deactivated,registered,checkpointed,gap,lost}`, `conversation.{started,ended,description_observed}`, `desktop.selected` | Conversations, SessionSources, SourceRoots, SensorHealth, *FocusSpans (4 maps), ObservedSurfaces, SurfaceContainers, BrowserAssociations, Browsers, DesktopSources/Head, AgentHeads |
| Task core | `task.{created,updated,completed,reopened,dropped}`, `capture.{created,assigned,expired}`, `proposal.*`, `timer.*`, `contract.accepted`, `decision.accepted`, `resource.{bound,unbound}`, `checkpoint.recorded`, `dependency.recorded`, `progress.{proposed,reviewed}`, `preservation.*`, `evaluator.accepted`, `evidence.*`, `grant.*`, `artifact.*` | Tasks, Captures, Proposals, Timers, Contracts/Heads, Decisions, Resources, Checkpoints/Heads, Dependencies/Heads, Progress*, Preservation*, Evaluators/Heads, Evidence, EvidenceInvalidations, Grants, Artifacts* |
| Workspace / actuation | `workspace.{accepted,residency_observed,operation_*,diffed,closed}`, `session.{bound,unbound}`, `viewport.{bound,unbound}`, `snapshot.*`, `application.reviewed`, `action.{queued,transitioned}`, `browser.{command_queued,command_finished,challenge_issued,readback_observed}` | WorkspaceManifests/Heads/Surfaces, SessionBindings/Heads, ViewportBindings/Heads, Snapshot*, ApplicationRecipes/Heads, WorkspaceOperations/Slots/Residency, Actions, BrowserOperations |
| Shared | `command.accepted` | Revision, LastEventID |

Every `Transact` also calls `model.ValidateDependencyGraph(st)`, a task-core invariant, even for pure sensor events (`store.go:251`). Pure background scans by actors `scheduler`, `coordinator`, `observer:browser`, `observer:herdr` and source do not append events when nothing changed (`store.go:201`).

### B.3 Coupling between layers (non-test imports)

```
adapters/{herdr,hyprland,wcu,dotprivate} -> model            (only)
adapters/application -> adapters/herdr, adapters/hyprland, model
model      -> conversation          (model is the hub; every layer imports it)
store      -> model, conversation, surface
browser    -> actions, adapters/hyprland, capture(!), model, store, surface
session    -> skald/sessioncapture, skald/sessionrecord, conversation, model, store
workspace  -> actions, adapters/{application,herdr,hyprland}, browser, continuity, model, store
continuity -> adapters/{dotprivate,hyprland}, authz, model, resourceobs, store
core       -> capture, model, resourceobs, store
checks     -> continuity, model, store
actions    -> adapters/hyprland, authz, model, store
tui        -> browser, checks, continuity, core, model, workspace   (DTO types; data over HTTP)
mcpbridge  -> actions, client, continuity, model
retrieval  -> model
daemon     -> almost everything + skald/sessionrecord
```

**Cross-layer couplings that block a clean split:**

1. **`model.State` monolith.** The adapters look independent because they "only import model", but `model` carries every task type and helpers such as `NewID`, `StrictJSON`, `OpaqueID`, `SessionLocator` and `HerdrIdentity`.
2. **Herdr agent sensor depends on task bindings.** `agentSources()` collects sockets only from active `SessionBindings` (`internal/workspace/agents.go:56-71`), and those are created by `heimdall session bind-herdr TASK`.
3. **Conversation attribution depends on task resources.** `taskBinding()` matches a transcript's `native_cwd` against task `Resources` of kind `tree` (`internal/session/service.go:204-228`). This is worth porting as a commitment-attribution heuristic.
4. **Browser depends on task capture.** The extension popup's capture lines are parsed by `capture.Parse` and become task `Capture` records (`internal/browser/service.go:476-516`).
5. **Continuity depends on Hyprland types.** `continuity/service.go:190` declares `ReadFocused(context.Context) (hyprland.Status, error)` for intent registration.
6. **One process.** `daemon.Serve` wires all services into one process and starts 8 goroutines: external actions, snapshot, operations, pairings, viewport observer, agents, sessions and the `tasks.yaml` watch (`internal/daemon/daemon.go:115-197`).
7. **Not importable.** Module path `heimdall` plus every package under `internal/` means no other module can import any of it. Reuse means moving code: **527 import lines in 247 files** reference `"heimdall/..."`.

### B.4 What a sensor-only heimdall build would keep and cut

**Keep:**

| Item | Detail |
|---|---|
| Hyprland adapter | `adapters/hyprland` minus `dispatch.go` (823 LOC): socket2 events, attention and focus spans, inventory, peer-credential and epoch checks |
| Herdr adapter | `adapters/herdr`: `Observe` + `Agents`. `Report` (metadata) and `Focus` are optional actuation |
| WCU observer | `adapters/wcu` (387): read-only, launches a pinned WCU argv over MCP |
| Browser sensor | `browser/{protocol,surface,active,lease,pairing}` + `nativebridge` + `extension/` (observation half) |
| Supporting packages | `surface`, `resourceobs` |
| Sensor services | `workspace/{agents,attention,viewport,application_observation,browser_pairing}` |
| Storage core | `store/store.go` core plus the sensor reducers and sensor model types |
| Shared model helpers | `NewID`, `StrictJSON`, `OpaqueID`, `Clone`, `DesktopSource`, `SessionLocator`, `HerdrIdentity`, `WindowIdentity` |
| Transcript capture | `session` + `conversation` + `cmd/heimdall/hook.go`, unless replaced by the skald capture module |

**Must cut or replace:**

- Split `model.State` and `store.Apply` into a sensor reducer set. Better still, have sensors emit envelopes to the substrate and drop the projection.
- Replace Herdr agent-source discovery from task `SessionBindings` with explicit sensor configuration, for example "watch these Herdr sockets".
- Move `session.taskBinding` and browser→`capture` out of the sensor path, so attribution happens service-side.
- Remove `ValidateDependencyGraph` from the sensor commit path.
- Replace the loopback HTTP daemon with the session-host dial-out connection, keeping a local socket for standalone use.
- Drop `actions`, browser command dispatch and `hyprland/dispatch.go` from a strictly observational build, or put them behind the gated-capability boundary.

Rough size of a sensor-only build: about 8.6k non-test LOC today, before the split refactor. Platform: `local_linux.go`/`local_other.go` stubs exist, so it builds on Windows but observes only on Linux and Hyprland.

### B.5 Task-core record types, mapped to Odin commitments

Fields are as declared in `internal/model/*.go`; JSON names are shown.

| Heimdall record | Fields | Source |
|---|---|---|
| `Task` | id, parent, title, type, status, importance, resume_by, estimate_minutes, next_action, impact{income,skill,portfolio,relationships: 0..5}, done{text, mode, checks[]}, subtasks[]Step | `model.go:63-76`, impact keys at `model.go:378` |
| `Step` | id, title, status (open/blocked/done/dropped), after[], due, estimate_minutes, done | `model.go:55-62`, `:408` |
| `TaskRecord` | task, revision, workflow, created_at, updated_at, completed{step→{at, token}} | `model.go:106-113` |
| `Workflow` (type template) | version, statuses, initial_status, success_statuses, dropped_statuses, subtasks, proposed_status_mappings. Defaults: project / application / research / study | `model.go:86-99`, `internal/core/defaults/types.yaml` |
| `Check` (acceptance check) | id, kind ∈ {manual, action.verified, agent.released, artifact.exists, artifact.digest, repo.commit, repo.state, test.exit, gh.pr_merged, mail.sent, mail.received, silence} + kind params (path, argv, timeout, expected_digest/commit, require_clean, env, exclude, days, after, response_check, account, from/to(_domain), correlation, since, repo, ref, session, url) | `model.go:23-49`, `:460-560` |
| `Contract` | id, target, task_revision, previous, objective, constraints[], acceptance(Done), resource_ids[], actor, at, materialized_from | `continuity.go:17-29` |
| `Decision` | id, target, task_revision, text, supersedes, actor, at | `continuity.go:49-57` |
| `Resource` | id, target, kind (file/tree), root, path, exclude[], active, initial{digest, files, bytes} | `continuity.go:59-72` |
| `Checkpoint` | id, target, task_revision, contract_id, previous, source_event, summary, current_step, next_action, blockers[], resources[]{id, snapshot}, context[]{target, task_revision, contract_id}, decisions[], actions[], artifacts[], grant_id, actor, at | `continuity.go:87-106` |
| `TaskDependency` | id, target, depends_on, task_revision, prerequisite_revision, previous, active, reason | `dependency.go:11-22` |
| `ProgressProposal` / `ProgressReview` | proposal: kind (incl. `decision`, `artifact`), text, contract_id, context, decision_digest, artifacts, supersedes, digest; review: proposal_id, status (reviewed/accepted/rejected), note, authority{session, resource_ids, expires_at} | `progress.go:19-125` |
| `Evaluator` / `Evidence` | evaluator: check_id, contract_id, spec{kind, resource_id, argv, timeout, expected digest/commit, require_clean, env}; evidence: status, outcome, reason, observer, inputs, context, output/executable digests, started/finished | `evidence.go:20-66` |
| `Proposal` (ratify) | id, target, target_revision, kind, status, evidence[] | `model.go:127-135` |
| `Timer` | id, target, kind, anchor, due_at, status, outcome | `model.go:136-144` |
| `Capture` | id, client, pointer, title, targets[], kind, why, origin, expires_at, expired | `model.go:114-126` |
| `Grant` | id, name, target, subtree, resource_ids, token_hash, expires_at, revoked_at, action_write, checkpoint_write | `grant.go:13-26` |
| `SessionBinding` (workspace layer) | target, task_revision, manifest_id, surface_id, locator{adapter, host, source_epoch, session_id, workspace_id, pane_id, cwd, repository, worktree, agent_session_id}, herdr{protocol, server_version, terminal_id, tab_id, shell_pid, shell_start} | `workspace.go:42-69,132-140` |

**Mapping to the Odin commitment record.** The commitment record's fields come from `odin/docs/DECISIONS.md:265-270`: objective, acceptance criteria, owner and delegated assignments, dependencies and pending decisions, evidence so far, next trigger or review date, delegation, budget.

| Odin commitment field | Heimdall source | Gap |
|---|---|---|
| Objective | `Contract.objective` (+ `Task.title`) | none |
| Acceptance criteria | `Contract.acceptance` / `Task.done{text, mode, checks[]}` with 12 check kinds | `mail.*`, `gh.pr_merged` and `silence` checks have no evaluator yet |
| Owner and delegated assignments | **none**. Records have only `actor`. Agents are *observed* (`AgentRecord`), never assigned. `SessionBinding` links a task to a Herdr pane | **new** in Odin |
| Dependencies | `TaskDependency` (revision-pinned, history-chained) | none |
| Pending decisions | `ProgressProposal{kind:decision}` pending review; accepted `Decision` | heimdall has no open-question record other than proposals |
| Evidence so far | `Checkpoint`, `Evidence`, `ArtifactVersion`, `PreservationReceipt`, `ProgressReview` | none |
| Next trigger or review date | `Task.resume_by`, `Step.due`, `Timer.due_at` | none |
| Delegation it runs under | `Grant` (scoped read/checkpoint/action credential) | partial: it is a credential, not a delegation with authority limits |
| Budget | **none** (`estimate_minutes` only) | **new** |
| Revisioning and idempotency | `revision` / `task_revision` / `previous` chains; `commands` request-id table | keep the pattern |

### B.6 Herdr adapter

The adapter is `internal/adapters/herdr` (511 LOC + 271 test LOC):

| Aspect | Detail | Evidence |
|---|---|---|
| Transport | Newline-delimited JSON request `{id, method, params}` over a **Unix socket**, one request per connection ("Herdr closes each ordinary RPC connection after its single response"), 1 MiB response cap, 2 s deadline | `herdr.go:70-121` |
| Socket checks | Must be user-owned, not group- or other-writable; peer checked with `SO_PEERCRED`; the epoch hashes host machine-id, boot id, peer PID and start time, and socket dev/ino/ctime | `local_linux.go:54-99` |
| Methods used | `ping`, `pane.get`, `pane.process_info`, `agent.list`, `pane.report_metadata`, `workspace.report_metadata`, `workspace.get`, `pane.focus` | `herdr.go:144,129,175; 221-312` |
| CLI use | `herdr terminal attach <terminal_id>` inside a dedicated `foot`, with `HERDR_SOCKET_PATH` (application recovery recipe) | `internal/adapters/application/local_linux.go:37-61` |
| Version pin | **Exact**: `ping.Protocol != 20 \|\| ping.Version != "0.8.2"` is refused | `herdr.go:156` |
| Installed version | `herdr 0.8.2-1` (pacman) | `pacman -Qi herdr` |
| Not supported | Pane or workspace creation, layout, prompting or sending input, waits, adopt or takeover | guide `docs/guides/HERDR-SETUP.md:3-7`: "does not launch agents, send terminal input, change agent runtime status" |

**Could it be reused as Odin's Herdr workspace adapter?** Partly. The dial, identity and epoch layer and the `ping` / `pane.get` / `process_info` / `agent.list` primitives, about 400 LOC, are a solid base. They depend only on `model` helpers, so extraction is small work. Odin's adapter needs more, per `odin/docs/design/ODIN-ECOSYSTEM-INTEGRATION.md:90-109`:

- workspace layout and launch through API operations;
- prompting and waiting;
- adopt, takeover and return.

None of these exist in heimdall. The exact 0.8.2/20 pin must become capability negotiation. Binding authority also lives in task-bound `workspace/herdr.go` (364 LOC), which Odin would replace with its own session-binding record.

---

## C. Skald decomposition

### C.1 Layers

| Layer | Files | Non-test LOC | Test LOC |
|---|---|---:|---:|
| **Capture library (public)** | `sessionrecord/{record,identity}.go` (324); `sessioncapture/{capture,normalize,discovery,probe,devin}.go` (1,026) | 1,350 | 622 |
| **Capture runtime (internal)** | `internal/daemon/{collector 236, discovery 276, file_stamp 57, config 162, config_write 109}` | 840 | ~400 (daemon tests) |
| **Archive** | `internal/archive/{ingest 986, read 374, store 283, backup 223, transcript 87, registration 33}` + `migrations/001-005.sql` (274) | 1,986 + 274 SQL | 787 |
| **Daemon / socket API** | `internal/daemon/server.go` (282), `internal/client/client.go` (62) | 344 | ~64 |
| **TUI** | `internal/tui/*` (2,046) + `cmd/skald/tui.go` (111) | 2,157 | 402 |
| **CLI** | `cmd/skald/{main 264, archive 157, connect 216}` | 637 | 149 |

The checkpoint and gap model is in `sessioncapture.Checkpoint` (version, source_key, generation, epoch, offset, parsed_offset, ordinal, prefix_digest, conversation_id, provider_version, has_gaps) and `Gap` (code, offset, ordinal, generation) (`sessioncapture/capture.go:35-61`). `Read()` returns a **candidate** checkpoint that "only the consumer can commit … with all records and gaps" in one transaction (`capture.go:99-102`; `docs/CONTRACT-V1.md:67-90`).

### C.2 Archive schema

The archive uses STRICT tables with immutability triggers (`internal/archive/migrations/*.sql`; `user_version` 5):

| Migration | Tables |
|---|---|
| 001_capture | `archive_meta`, `sources`, `source_roots`, `streams`, `ingest_checkpoints`, `sessions`, `session_aliases`, `content_objects` (original bytes, sha256 key), `artifacts`, `artifact_versions`, `normalizations` (envelope JSON), `record_observations`, `capture_gaps`, `changes` (AUTOINCREMENT sequence; kinds record/gap/withdrawal/source), `consumer_checkpoints`, `purge_tombstones`; triggers `immutable_content`, `immutable_versions`, `immutable_normalizations` |
| 002_daemon | `archive_meta` v2 (+`restored_from`), `stream_locators`, `record_heads`, `stream_generations`, `session_projects`, `session_titles` |
| 003_titles | `session_titles.origin` (native/derived) |
| 004_activity | `session_activity` (signal none/working/idle/input) |
| 005_continuation | `session_titles` rebuilt with origin `continuation` |

The database is `archive.sqlite` with `writer.lock` in the data dir, DSN `_pragma=foreign_keys(1)&busy_timeout(5000)`, `SetMaxOpenConns(1)`. Migrations are embedded with `//go:embed` (`internal/archive/store.go:30,86-130`). The planned `relations` table does not exist.

### C.3 Socket API

The server is HTTP over the Unix socket `$XDG_RUNTIME_DIR/skald/skald.sock`, with `SO_PEERCRED` same-uid checks and 0700 directories (`internal/daemon/server.go:164-229`, `config.go:157-161`). Endpoints, each with a strict query allowlist and `namespace` scoping (`server.go:46-120`):

- `GET /v1/status`
- `GET /v1/sessions` (limit, cursor)
- `GET /v1/transcript` (conversation, history, limit, cursor)
- `GET /v1/artifacts`
- `GET /v1/record` (record, revision, adapter, raw)
- `POST /manage/backup`

### C.4 TUI

The TUI uses tcell v2 directly, with no framework. It reads only through `internal/client` over the socket and imports `internal/archive` for DTO types. It has themes `heimdall|desktop|amber` (`cmd/skald/main.go:33`). Plain `skald` auto-starts the daemon (`cmd/skald/tui.go:66`, `ensureDaemon`).

### C.5 Running capture as a module that writes to the shared substrate

**What already works.** The public library is store-agnostic: "reads configured provider sources without durable writes, hooks, model calls, application state or consumer-owned cursor commits" (`sessioncapture/capture.go:1-2`). Heimdall is a live second consumer. It calls `sessioncapture.Inventory` (`internal/session/service.go:100`), `Identify` (`:142`) and `Read(f, source, checkpoint, limits, now)` (`:244`), and journals into its own event log. Skald's test `TestIndependentConsumersConform` covers this.

**What is not reusable as is:**

1. Discovery, enrollment, relocation and the collector loop are in `internal/daemon` (about 840 LOC). They are typed on the concrete `*archive.Store`.
2. The store surface the collector uses is narrow: `Registrations`, `Register`, `Enroll`, `Checkpoint(key)`, `Ingest(reg, prev, batch, now)` and `SetHealth` (`internal/daemon/collector.go:66-132`, `discovery.go:37-193`; `internal/archive/ingest.go:43-167,931`).
3. Projections are computed *inside* `archive.Ingest` (986 LOC, SQL): titles, project derivation from cwd and file evidence, activity signals, continuation labels, and Codex approval justification (`ingest.go:424,554-573,836`).

**Work required:**

1. Extract a `Sink` interface with those six methods and move the collector and discovery into a public package.
2. Implement a substrate sink. One atomic append per batch: record envelopes, content-addressed raw bytes, gaps and the new checkpoint. The checkpoint must be readable back by stream key. Dedupe on `(record_key, source_revision)`, as skald does today ("at-least-once delivery with idempotent record/version insertion").
3. Because capture runs on the workstation and the substrate on the homelab, the sink is remote. Either the append is transactional over the dial-out link, or a local durable spool is kept. Skald's idempotent re-read makes resend safe.
4. Port or recompute the projections in the transcript namespace or the human view.
5. Honour redaction: `purge_tombstones` exists, and Odin's DECISIONS requires the archiver to honour redaction.
6. Keep `archive.Store` as the standalone sink to preserve "useful without Odin".

**Costs to budget:**

- 26.81× SQLite bytes per source byte on small records (`STATUS.md` benchmark).
- Full-prefix re-hash on every batch ("linear read cost on every batch", `docs/CONTRACT-V1.md:96-99`).
- The 1.5 GB live archive to migrate.

### C.6 Provider-specific code and adding a provider

Providers are hard-coded constants `claude_code`, `codex`, `devin` (`sessioncapture/capture.go:20-24`). There is no registry or interface; branches are `if`/`else` chains. The branch sites are:

| Location | Lines |
|---|---|
| `sessioncapture/capture.go` | 93 |
| `sessioncapture/normalize.go` | 33-41, 94-99, 110 `normalizeClaude`, 148 `normalizeCodex` |
| `sessioncapture/discovery.go` | 36, 104-111, 148 |
| `sessioncapture/probe.go` | 36-51 (verified versions Claude 2.1.263, Codex 0.153.4) |
| `sessioncapture/devin.go` | 253 LOC, reads Devin's SQLite stores, which is why the library imports `modernc.org/sqlite` |
| `internal/archive/ingest.go` | 424, 554-573, 836 |
| `internal/daemon/config.go` | 93 |
| `internal/daemon/discovery.go` | 232 |
| `internal/daemon/file_stamp.go` | 41 |
| `internal/daemon/collector.go` | 87, 141, 201 |
| `cmd/skald/connect.go` | 33-48 (default roots) |

Heimdall duplicates the allowlist (`claude_code|codex` only) in `internal/conversation/source.go:54,82`, `record.go:144` and `internal/daemon/session.go:117`.

**Effort to add a provider: about 15 sites in 10 files, medium.**

- **Pi:** JSONL *tree* sessions at `~/.pi/agent/sessions/--<path>--/<ts>_<id>.jsonl`, header v3 (`odin/docs/research/harness-research-2026-10/deep_dive_earendil_pi.md:194`). Line tailing fits. Parent links have no home, because the `relations` table does not exist.
- **Odin history:** if Odin's history lives *in* the substrate, it needs no capture. A capture adapter matters only for exporting to standalone skald. The earlier note's `{i, kind, src, text, size, date, ref}` adapter sketch still applies, and identity must come from content, not filenames (`sessioncapture/discovery.go:100-101`).

### C.7 Change feed or MCP beyond the plan?

- **No MCP code** anywhere in skald. `grep mcp|changes.read|context.query|braid` finds nothing.
- **A change feed is half built.** `changes` rows are written for `record`, `gap` and `source` (`internal/archive/ingest.go:134,286,368,926`). They are read only as `max(sequence)` for status (`store.go:281`). `consumer_checkpoints` is never used.
- Planned but unimplemented: `changes.read`, `context.query`, read-only MCP, Braid retrieval (`SKALD-IMPLEMENTATION-PLAN.md:618-632`; README 2026-10-14).

---

## D. Braid

### D.1 Public Go API (`github.com/algorhythmic/braid/pkg/braid`)

| Area | API |
|---|---|
| Engine | `Open(ctx, Config, ...Option) (*Engine, error)`, `WithProvider(Provider)`, `WithCost(CostFunc)`, `(*Engine).Close` |
| Write | `Upsert(Batch)`, `Ingest([]Event)` / `Replay()` (legacy mode), `ReplaceSnapshot(Snapshot)`, `Apply(Update)`, `Dataset()` → `DatasetState{ID, Revision, Digest}` |
| Read | `Query(Query) (Result, error)`, `Retriever(name)`, `GetMany(GetRequest)`, `Export(ExportRequest)` |
| Index | `Reindex()`, `ReindexWithOptions(ReindexOptions)` |
| Eval | `Eval([]Label)`, `GridSearch(labels, Grid, objective)`, `LoadGrid`, `EvalConstraints`, `Metrics`, `Evaluation` |
| Config | `Config` (dataset_id, version, store{backend, path}, embed{provider, model, url}, index, projection, graph, temporal, defaults, candidate_limit), `DefaultConfig()`, `LoadConfig(path)`, `Validate()` |
| Types | `Node{id, type, text, ts, cost?, attrs}`, `Edge{src, dst, type, weight, ts}`, `Embedding{node_id, model, vec}`, `Batch`, `Event`, `Budget`, `Boost`, `Filters`, `Predicate`, `Query`, `Hit`, `Item`, `Result`, `CostAccounting`, `Rejection`, `Snapshot{dataset_id, expected_revision, batch}`, `Update{dataset_id, expected_revision, upsert, delete_nodes, delete_edges}`, `EdgeKey`, `Projection/NodeRule/EdgeRule`, `Ollama{URL, ModelName, Client}` |
| Interfaces | `Retriever`, `Provider{Model(); Embed(ctx, []string)}`, `CostFunc` |
| Errors | `ErrRevisionConflict`, `ErrDatasetMismatch` |

Sources: `pkg/braid/{store,types,dataset,query,access,export,reindex,eval,grid,config,embed,projection}.go`.

### D.2 Stdio protocol

- Version: `protocolVersion = 1` (`cmd/braid/protocol.go:18`).
- 28 capabilities (`:21`). The first request must be `hello{versions, required_capabilities}` (`:252-291`).
- Strict NDJSON, `maxRequestBytes = 16 MiB`.
- **It is implemented in `package main`, so it cannot be imported.**
- Heimdall's client negotiates `query, apply, replace_snapshot, dataset, strict_requests, structured_errors, dataset_binding` (`heimdall/internal/retrieval/client.go:114`).

### D.3 Dataset schema

The schema is in `pkg/braid/store.go:68-82` and `dataset.go:70`. Each dataset is one SQLite file with WAL, `busy_timeout=5000` and `foreign_keys=ON`:

- `nodes`
- `nodes_fts` (FTS5, unicode61 remove_diacritics 2, synced by 3 triggers)
- `edges` (PK src, dst, type)
- `embeddings` (BLOB vec, PK node_id, model)
- `events` (legacy)
- `labels`, `evaluation_labels`, `eval_runs`
- `dataset_state` (singleton: dataset_id, revision, digest, mode `legacy|snapshot`)

### D.4 Ollama

Ollama is optional (`embed.provider: none` by default). The built-in provider sends `POST {url}/api/embed` with no auth and a 60 s timeout. The default URL is `http://localhost:11434` (`config.go:64`, `embed.go:27-34`). Any `Provider` can be injected (`WithProvider`). Ingestion never calls the provider.

### D.5 How a consumer publishes data

- **Snapshot mode (recommended):** `ReplaceSnapshot{dataset_id, expected_revision, batch{nodes, edges, embeddings}}`, then incremental `Apply{expected_revision, upsert, delete_nodes, delete_edges}`. After the first snapshot or apply, `Ingest` and `Replay` are disabled for that file.
- **Legacy mode:** `Ingest([]Event)` with YAML `projection` rules.
- Heimdall's publisher redefines the wire structs itself instead of importing braid. It emits `task:`, `capture:`, `conversation:` and `surface:` nodes with `targets`/`bound` edges, metadata only (`heimdall/internal/retrieval/publish.go:10-70`).

### D.6 Embedding braid as a library in a larger Go service

| Requirement or assumption | Evidence | Implication |
|---|---|---|
| Opens its **own** `*sql.DB` from `Config.Store.Path`; `Backend` must be `sqlite`; no option to pass a handle or use Postgres | `store.go:29-56`, `config.go:~101` | The substrate cannot hold braid tables in its own DB without a change. Plan one braid file per dataset or scope |
| `SetMaxOpenConns(1)`; operations serialized by a channel mutex | `store.go:43`, `access.go:12-35` | Queries block during writes. Use one Engine per dataset |
| Every write recomputes SHA-256 over **all** nodes, edges and vectors | `dataset.go:82,143` | Many small `Apply` calls fed by a change stream cost O(dataset) each. Batch them |
| Dense, graph and temporal queries load all filtered nodes and **all vectors** per query; dense search is brute force; reindex runs in memory | `query.go:121-136`, `retrieve.go:146,164` | Fine at about 20k records (benchmarks); a scale ceiling for a unified substrate |
| Default `store.path = "braid.db"` is **relative to the CWD**; "paths in YAML resolve relative to the process working directory" | `config.go:62` | Always set an absolute path in a service, whose CWD may be `/` |
| No `init()`, no env reads, no logging, no `os.Exit`, no mutable globals (only `retrieverNames`, error vars, a regexp) | grep | Safe in-process |
| Shares the `modernc.org/sqlite` driver name `"sqlite"`, same v1.38.2 as the other repos | go.mod | No driver conflict |
| Protocol, capability negotiation and background reindex jobs are in `cmd/braid` | `cmd/braid/{protocol,reindex_jobs}.go` | An in-process embedder loses the strict-request and timeout layer unless it is moved to a package |
| `go 1.24.0` | go.mod | Merges cleanly under 1.25 |

---

## E. Cross-cutting

### E.1 Shared and duplicated code

| Concern | heimdall | skald | braid |
|---|---|---|---|
| SQLite driver | modernc v1.38.2, `SetMaxOpenConns(1)`, WAL, `synchronous=FULL`, `busy_timeout=2500` (`store.go:85-116`) | modernc, DSN pragmas, `busy_timeout(5000)`, single conn (`archive/store.go:86-96`) | modernc, WAL, `busy_timeout=5000`, single conn |
| Single-writer lock | `writer.lock` + `flock` (Unix) / `LockFileEx` (Windows) (`store/lock_*.go`) | `writer.lock` + `syscall.Flock`, `O_NOFOLLOW` (`archive/store.go:110-120`) | none (one Engine) |
| Backup | `VACUUM INTO` (`store/backup.go:36`) | SQLite online backup API via `driver.NewBackup` (`archive/backup.go:15-51`) | none |
| Event log | `events` + `commands` idempotency + JSON projection + replay | immutable content-addressed archive + `changes` sequence | legacy `events` + projection rules, or snapshot revisions + digest |
| IDs and digests | `model.NewID`, `conversation.ValidDigest` (copy of skald's pattern, `conversation/record.go:26`) | `archive.NewID`, `sessionrecord.ValidDigest` | `dataset digest` |
| Same-user socket checks | `SO_PEERCRED` via `x/sys/unix` in the herdr and hyprland clients | `SO_PEERCRED` via `syscall` in its server | n/a |
| Servers | loopback TCP HTTP, bearer tokens, `endpoint.json` | Unix-socket HTTP, peer credentials | stdio NDJSON |
| TUI | tcell v2.13.10, hand-rolled | tcell v2.13.10, hand-rolled (has a `heimdall` theme) | none |
| Config | flags plus `tasks.yaml` / `types.yaml` (embedded defaults), `wcu-observer.json`; "`config.toml` is future work" (`README.md:206`) | `sources.json` v1 in `$XDG_CONFIG_HOME/skald` (`config_write.go:14-26`), `SKALD_THEME` | YAML `--config` |
| Strict JSON | `model.StrictJSON` (rejects unknown and duplicate keys) | `sessionrecord.Decode` strict | protocol strict decoder |
| Braid wire types | redefined in `retrieval/publish.go` | none | canonical in `types.go` |
| Duplicated function names | non-test code: heimdall∩skald share 36 function names (Backup, NewID, ValidDigest, readBounded, ensureDaemon, writeJSON, Restore, Probe, Identify, …); heimdall∩braid 14; skald∩braid 12 | | |

### E.2 Dependency versions if merged

| Module | heimdall | skald | braid | Conflict? |
|---|---|---|---|---|
| modernc.org/sqlite | v1.38.2 | v1.38.2 | v1.38.2 | no |
| modernc.org/libc / memory / mathutil | v1.66.3 / v1.11.0 / v1.7.1 | same | same | no |
| golang.org/x/sys | **v0.41.0** | v0.38.0 | v0.34.0 | MVS picks v0.41.0; harmless |
| golang.org/x/term, x/text | v0.37.0, v0.31.0 | same | — | no |
| golang.org/x/exp | 2025-06-20 pseudo | same | same | no |
| gdamore/tcell/v2, rivo/uniseg | v2.13.10, v0.4.7 | same | — | no |
| gopkg.in/yaml.v3 | v3.0.1 | — | v3.0.1 | no |
| google/jsonschema-go | v0.4.3 (indirect) | v0.4.3 | — | no |
| modelcontextprotocol/go-sdk | v1.7.0 | — | — | heimdall only |
| go directive | 1.25.0 / toolchain 1.27.1 | 1.25.0 / 1.27.1 | 1.24.0 | take 1.25 + toolchain 1.27.1 |

**Merge mechanics:**

- No repository has a `go.work`.
- A workspace with `use ./heimdall ./skald ./braid` would silently replace heimdall's proxy-pinned skald v0.1.1 with local skald. That is safe today because library code is identical.
- A single module requires:
  - rewriting heimdall's bare `heimdall/...` path (527 imports, 247 files);
  - moving code out of `internal/`, or into the new module's own `internal/` tree;
  - adding Linux build tags to skald's `archive` and `daemon` (they use `syscall.Flock`, `O_NOFOLLOW` and `GetsockoptUcred` without tags) if heimdall's Windows CI matrix is kept. Skald's two public packages are portable; heimdall's Windows CI already builds them.

### E.3 Test fixtures and scripts that would have to move

- **heimdall:**
  - `testdata/` (63 files, 2.25 MB; schema-15/17/19/20 SQL dumps and `events-v1.json` goldens), referenced by **36 test files** through `../../testdata/...`;
  - `internal/surface/testdata/fuzz/`;
  - 28 Node `.cjs` smoke scripts, which need built binaries plus Node 24;
  - `scripts/browser-test` (npm, Playwright, TypeScript);
  - 4 Python fixtures (`hyprland-fixture.py`, `hyprland-operation-fixture.py`, `native-workspace-fixture.py`, `tui-pty.py`), spawned by `viewport/snapshot/browser-pairing/external-action/tui-smoke.cjs`;
  - `scripts/neovim-smoke.lua`;
  - 3 PowerShell scripts;
  - `extension/test/*.test.js`.
- **skald:**
  - `testdata/{claude,codex}/session.jsonl`, `testdata/identity-v1.json` (v1 identity vectors), referenced by 5 test files;
  - `schemas/session-record-v1.schema.json`, checked by `scripts/check_schema.py` in `make test`;
  - Python smokes: `native_smoke`, `tui_smoke`, `discovery_smoke`, `tui_demo`, `benchmark_archive`.
- **braid:**
  - `examples/` (`saga.yaml`, `heimdall.yaml`, `events.jsonl`, `labels.jsonl`, `query.json`, `grid.yaml`);
  - `scripts/verify-contract.sh` (jq, GNU timeout).

### E.4 Hard-coded paths and in-process collisions

| Tool | Paths and endpoints |
|---|---|
| heimdall | `$XDG_DATA_HOME/heimdall` or `~/.local/share/heimdall` (`cmd/heimdall/main.go:83-91`) containing `heimdall.db`, `writer.lock`, `endpoint.json`, `client-endpoint.json`, `browser-endpoint.json`, `tasks.yaml`, `tasks.pending.yaml`, `types.yaml`, `task-file-history/`, `backups/`, `tui-drafts/`, `wcu-observer.json`, `daemon.log`, `braid/braid.yaml`, **`braid/heimdall.db`** (`retrieval/client.go:87-96`); `~/.claude/settings.json` (hook merge) and `~/.claude/projects` (`cmd/heimdall/hook.go:40,93`); `~/.config/systemd/user/heimdall.service`; `~/.local/bin/braid` fallback (`retrieval/client.go:70`); `$XDG_RUNTIME_DIR/hypr/<sig>/.socket.sock` and `.socket2.sock`; `$XDG_STATE_HOME/omarchy/agents/usage/`; `/etc/machine-id`; listener `127.0.0.1:0` |
| skald | `$XDG_DATA_HOME/skald` containing `archive.sqlite`, `writer.lock`, `backups/`; `$XDG_CONFIG_HOME/skald/sources.json`; `$XDG_RUNTIME_DIR/skald/skald.sock`; provider roots `${CLAUDE_CONFIG_DIR:-~/.claude}/projects`, `${CODEX_HOME:-~/.codex}/sessions`, `${DEVIN_DESKTOP_CONFIG:-~/.config/Devin}/User/acp-messages`; `/etc/machine-id` |
| braid | `braid.db` relative to the CWD; `http://localhost:11434` |

**Collisions if run in one process.** No file path collides: the data directories are distinct, and both lock files are named `writer.lock` but sit in different directories. The real hazards are:

1. Heimdall (every 5 s) and skald (every 1 s) **both tail the same Claude Code roots**, and assign different namespace keys: hostname versus machine-id (`heimdall/internal/daemon/session.go:135`, `skald/cmd/skald/connect.go:200`).
2. Several independent single-connection SQLite writers, plus heimdall's whole-state JSON rewrite on every sensor commit.
3. Heimdall's `/session/hook` and Claude Code hook installation touch the user's `~/.claude/settings.json`, which belongs in a harness integration package.
4. Braid's CWD-relative default path.

---

## F. Consolidation tables

Difficulty: S = days, M = 1–3 weeks, L = more than 3 weeks or a semantic redesign.

### F.1 heimdall

| Package or area | Proposed destination | Rationale | Diff. | Main risk |
|---|---|---|---|---|
| `adapters/hyprland` (observer, attention, inventory, transport) | Workstation daemon sensor (Hyprland) | Pure observation over the compositor sockets; depends only on `model` | M | Untangling `model` types; epoch and peer checks must survive |
| `adapters/hyprland/dispatch.go` | Workstation daemon gated actuation | Native window focus, move and close | M | Authority model (the actions journal) must be re-homed |
| `adapters/herdr` | Workstation sensor + seed of the Odin Herdr workspace adapter | Transport and identity layer reusable; observation, metadata and focus only | S (extract) / L (launch, layout, prompt, takeover) | Exact 0.8.2/20 pin; no launch or input APIs |
| `adapters/wcu` | Workstation sensor (read-only desktop observer) | Bounded MCP client to WCU | S | Depends on the separate Python WCU repo and a pinned argv digest |
| `adapters/application` | Workstation gated actuation (launch recipes) | foot / foot-herdr / foot-nvim relaunch | M | Overlaps Odin's Herdr launch path; desktop authority (D21) |
| `adapters/dotprivate` | Delete, or service-side evidence observer | Preservation receipts for dotprivate mirrors only | S | Loses the P03 preservation workflow |
| `browser`, `nativebridge`, `extension/` | Workstation sensor (browser) + gated actuation (commands) | Observation and command channel share one service | L | MV3 + native-host protocol, pairing, epochs, verification semantics; Node/Playwright test stack |
| `surface` | Substrate library (shared identity normalization) | Content identity independent of tasks | S | none |
| `resourceobs` | Workstation sensor (file/tree observation) | Must run where the files are | S | Currently keyed by task Resources |
| `session`, `conversation`, `cmd/heimdall/{source,hook,conversation}.go` | **Delete after the switch to the skald capture module**; hook relay goes to a harness integration package | Duplicates skald capture; lossy metadata only | M | Namespace host mismatch; `taskBinding` cwd attribution must move service-side |
| `workspace/{agents,attention,viewport,application_observation,browser_pairing}` | Workstation sensors | Sensor services | M | The agent poller is gated on task SessionBindings |
| `workspace/{service,herdr}` | Odin service session-binding records | Task-bound pane bindings become assignment and session bindings | M | Revision and precondition semantics |
| `workspace/{snapshot*,preview*,operation*,recovery*,application*}` | Workstation gated capability (desktop restore), or defer | W03–W07 desktop recovery | L | 3.4k LOC + much of the 6.2k test LOC; journaled-uncertainty semantics |
| `actions` | Execution-ledger namespace (records) + workstation gated capability | C12/S2a intent, attempt and report records | L | Uncertain-outcome rules; ties to WCU |
| `core` (commands, `tasks.yaml`, materialize, checks wiring) | Fold into Odin commitment records (service); the `tasks.yaml` watcher becomes an import tool or is deleted | Odin becomes the single task authority | L | Mapping revision, workflow and template semantics; migrating the live `heimdall.db` |
| `continuity` | Odin service (contracts, decisions, checkpoints, dependencies, progress, summary, resume context) | Core of the commitment model | L | 2,950 + 2,047 test LOC of invariants |
| `checks` | Execution backend or workstation evaluator (records stay in the service) | Runs git and `test.exit` argv where the repo lives | M | Scrubbed-environment and test-execution placement |
| `authz` | Odin service delegations and grants | Expiring scoped credentials | M | Grant ≠ delegation; needs authority limits |
| `capture` (quick-capture parser) | Odin service event intake | Capture lines become intake events | S | none |
| `model` | Split: substrate envelope + sensor records (workstation) + commitment records (service) | The keystone coupling | L | Every package depends on it |
| `store` | Substrate library: reuse the design (append-only log, request-id idempotency, replay), not the single-JSON-blob projection | Matches "one append-only event substrate" | L | Projection scale; 22 schema generations of replay compatibility |
| `daemon` | Delete (replaced by session host + service API) | Monolithic wiring | M | 88 route paths that clients depend on |
| `mcpbridge`, `client`, `cmd/heimdall/mcp.go` | Harness integration package (MCP against the Odin service) | Six tools (task, context, history, checkpoint, intent, report) | M | Grant semantics |
| `tui`, `cmd/heimdall/ui.go` | Human view (replace; reuse the needs-you, workstreams and review-dialog design) | One human view | L (new view) | Feature parity with drafts and retries |
| `contrib/omarchy` (QML bar) | Workstation human surface adapter (bar) | Already polls a CLI | S | Must point at a new status source |
| `integrations/neovim` | Harness or human integration package | Editor task UI over the CLI | M | CLI contract changes |
| `retrieval`, `cmd/heimdall/retrieval.go` | Delete (braid becomes an in-process library) | Subprocess supervisor redundant | S | none |
| `testdesktop`, Python and Node fixtures | Move with sensor and actuation tests | Synthetic IPC fixtures | S | Node and Playwright CI dependency |
| `cmd/heimdall` | Split: standalone `heimdall-sensors` binary ("useful without Odin") + delete task CLI | Standalone requirement | M | Users' scripts and bar module |

### F.2 skald

| Package or area | Proposed destination | Rationale | Diff. | Main risk |
|---|---|---|---|---|
| `sessionrecord` | Substrate library (transcript record envelope and v1 identity encoding) | Released v1 contract, stdlib-only | S | Contract freeze; namespace host rule must be unified |
| `sessioncapture` | Capture module (workstation daemon) | Already a store-free library with a live second consumer | S | Hard-coded providers; full-prefix rehash cost |
| `internal/daemon` collector, discovery, config | Capture module (refactor to a `Sink` interface) | Enrollment, relocation and polling loop needed by any host | M | Remote sink transactionality and checkpoint readback |
| `internal/daemon/server.go`, `internal/client` | Keep standalone (skald binary); not used in the integrated build | Same-user socket API | S | none |
| `internal/archive` + migrations | Keep standalone sink; port projections and the schema to the substrate "transcript archive" namespace | Lossless archive; projections inside Ingest | L | 1.5 GB live data; 26.8× amplification; immutability vs redaction |
| `internal/tui`, `cmd/skald/tui.go` | Human view (replace) | One human view | M | Transcript browsing UX parity |
| `cmd/skald` | Keep standalone | "Useful without Odin" | S | none |
| `scripts/*.py`, `testdata/`, `schemas/` | Move with capture module tests | Fixtures and schema check | S | Python dependency in `make test` |

### F.3 braid

| Package or area | Proposed destination | Rationale | Diff. | Main risk |
|---|---|---|---|---|
| `pkg/braid` retrieval core | Substrate library | Pure Go, no globals, injectable provider | M | Own SQLite file per dataset; O(dataset) digest per write; brute-force dense; single connection |
| `pkg/braid` eval and grid | Keep as dev tooling (substrate eval command) | Labelled retrieval evaluation | S | none |
| `cmd/braid/protocol.go` (stdio v1) | Keep standalone binary; optionally move to a package if child-process isolation is still wanted | Contract pinned for heimdall S3 | S | Losing strict-request and timeout guards in-process |
| `cmd/braid/main.go`, `reindex_jobs.go` | Keep standalone CLI | Operator tooling | S | none |
| `examples/`, `scripts/verify-contract.sh` | Move with the library's contract tests | CI gate | S | jq and GNU timeout dependency |

---

## G. Contradictions with the target architecture, and other risks

1. **Odin's decision record conflicts.** `odin/docs/DECISIONS.md` D10 is titled "The standalone tools stay separate (locked)": "Nothing rolls into Odin"; braid is a "child process over its stdio protocol"; standalone heimdall is "not an authority … for task state". `ODIN-ECOSYSTEM-INTEGRATION.md:118-140` proposes a projection, not a fold-in. The consolidation needs an explicit superseding decision.
2. **"Ranked work session plans on a schedule"** (the GitHub description) is not implemented. The planner and notifier are S4 "planned".
3. **"Neovim" as a sensor** does not exist. The Neovim code is an editor UI for tasks and checkpoints, plus a relaunch recipe.
4. **"SSE" and a change feed** do not exist in heimdall. Skald's `changes` table has a writer but no reader.
5. **Sensors are coupled to the task core**, through the monolithic `model.State`, the central `Apply`, Herdr polling gated on task bindings, cwd→task attribution and browser→task capture. "Host heimdall's adapters as sensors" means a real refactor (L), not a move.
6. **Desktop actuation is a sixth layer** the plan omits, about 9.6k LOC plus 6.2k test LOC. "Guarded desktop input" proper is WCU (Python, a separate repo); heimdall only journals intents and reports.
7. **Capture-as-module is proven in-process**, but a *remote* substrate breaks skald's one-transaction checkpoint contract unless the session host's append is atomic or spooled.
8. **Identity key mismatch** (hostname versus machine-id) between heimdall and skald capture namespaces.
9. **Braid "inside the substrate"** still means separate SQLite files per dataset and full-digest writes; it cannot share the substrate's database without code changes.
10. **Live data and maturity:**
    - Live data that must migrate: skald 1.5 GB, heimdall about 7.5 MB, both written 2026-10-15.
    - CI: heimdall red; skald has no CI; braid green.
    - Stale packaging: both PKGBUILDs still say `license=('custom')`, and their pkgver values are stale.
    - No heimdall tags; skald v0.1.1 and braid v0.1.0 are the only releases.
