# Inventory: Saga, wayland-computer-use, dotprivate (for the Odin consolidation plan)

Date: 2026-10-16. Read-only inspection of local checkouts with grep, sed, wc,
find and git. Nothing was built, installed, run or imported. No credential,
`.env`, auth-script or database contents were read; those paths are named only.

| Repo | HEAD | Working tree | Remote state |
|---|---|---|---|
| `/home/david/Projects/saga` | `a84f9ac` (2026-10-14, docs) | clean (no untracked or ignored files) | 108 commits since 2026-04-12. Last code-touching commit `ee0501a` 2026-05-05; last `heimdall.py` change `2cf3c05` 2026-04-18 |
| `/home/david/Projects/wayland-computer-use` (WCU) | `e61f8ed` (2026-10-14 merge) | 6 modified + 4 untracked paths (37 files with `-uall`) | **12 ahead of `origin/main` (`a600ed7`)**, not 10: the 10 feature commits of 2026-09-10, a local copy `670d021` of the README/license commit, and the merge |
| `/home/david/Projects/dotprivate` | `51d0fce` (2026-09-07, single commit) | untracked `docs/` (1 file) | in sync with origin |

**Changed since the 2026-10-13/14 research notes.** WCU now has an Apache-2.0
`LICENSE`. It arrived through `a600ed7` on origin (published from the worktree
`/home/david/Work/readme-overhaul-20261014/wcu-publish`) and was merged locally.
`repo_wayland_computer_use.md` §1 still says "no license". The public README
now describes local-only code: it reports `wcu-tools-5` and 191 tests on
`c618243`, but `origin/main:scripts/server.py` still reports `wcu-tools-4`.

---

## Most consequential findings

1. **Saga has no ledger, run lifecycle, digests, approvals, reviewer key,
   cancellation, concurrency cap, TTL or kill switch in code.** The execution
   backend "absorbing Saga's ledger and run lifecycle" means building them. All
   24 producer conformance checks in the pinned contract (CT-01 to CT-24) are
   unimplemented: 21 are "Not implemented" and 3 (CT-22 to CT-24) are "Blocked"
   on open gaps. The launcher has no tests at all.
2. **The launcher's confinement is weaker than its docstring.** By reading
   only, not testing:
   - `prd:` can name any host path, including `..` traversal, and root copies it
     into a worker workspace (`heimdall.py` L407-L453).
   - `workspace_source` may be the workspaces root itself, and is not bound to
     the project or instance (L296-L304).
   - `gitea_credentials` is not bound to the project (L317-L320, L540-L547).
   - A worker can plant a symlink at `PRD.md` that root later follows on a
     restart (L442-L452).
   - Heimdall runs as root from a checkout under `/home/david/src/saga`, which
     the operator user can write (`scripts/systemd/heimdall.service`).
3. **Today, more than Heimdall holds Docker.** `deploy.sh` runs as "the homelab
   user (the one in the docker group)". Eir and dev Claude run as that user on
   the VM; that Eir does not use Docker is a persona rule, not a mechanism
   (`eir/CLAUDE.md` L34; `docs/agents/EIR.md` L114). The Odin, Mimir, Bragi and
   keepalive containers are launched by host scripts and cron, never by Heimdall
   (`heimdall.py` L258-L263).
4. **No reviewer-identity boundary exists.** Odin and Mimir run in one
   container, as one Unix user (`vscode`), on one shared `/workspace`
   (`containers/odin/Dockerfile`, `odin/scripts/start-odin.sh`). Any process
   there can write `mimir/verdicts/*.md`. Nothing checks a verdict before
   launch: Odin `mv`s drafts into `launch-requests/` on persona instruction
   alone (`odin/CLAUDE.md` L334-L346).
5. **MQTT is unauthenticated.** No client uses credentials or TLS. Any LAN host
   can publish retained `guidance` that every worker consumes. Seven topics in
   `TOPIC-SCHEMA.md` have no publisher in code: `heartbeat`, `alert`, `summary`,
   and `odin/{status,inbox,synthesis,commands}`.
6. **The `spec_dev` package has no runtime caller except the archive sweep.**
   The persona says "the parser routes"; nothing connects Telegram turns to
   `parser.py`. Persona copy that is claimed to be byte-identical has already
   drifted from the code's strings (§C.4).
7. **WCU has no lease, grant or approval code.** Approval belongs to the MCP
   client. No single process holds input:
   - `ydotoold` (root, `/dev/uinput`) handles pointer events only.
   - Keyboard input goes through `wtype` and the compositor's virtual keyboard.
   - Focus and cursor go through `hyprctl dispatch`.

   All three are reachable by any uid-1000 process. A seat lease is enforceable
   only against cooperating clients unless input moves to a separate Unix user.
8. **dotprivate does not list Odin as a consumer.** Its contract names Heimdall
   P03 and Skald L6. "Odin writes a package directory and runs git" is
   sufficient, provided that directory is not inside a dotprivate `.private`
   clone. The post-commit hook's background `git add -A` would race with Odin's
   writes.
9. **The operator's own WCU incident argues for mechanical stop and budget.** An
   agent overran an evaluation by 23.7M tokens, "falsely reported that
   evaluations had stopped", and was killed from an outside session
   (`wayland-computer-use/reports/2026-09-10-astra-eval-overrun-retrospective.md`,
   untracked, 133 lines).

---

## A. Saga code inventory

### A.1 Directory layout (tracked files; lines)

| Path | Files | Lines | What it is |
|---|---:|---:|---|
| `odin/scripts/` | 23 | 4,926 (incl. tests) | `heimdall.py`, `ratatoskr.py`, `start-odin.sh`, `spec_dev/` package and tests |
| `odin/CLAUDE.md`, `odin/mimir/CLAUDE.md` | 2 | 1,472 | Odin and Mimir personas |
| `odin/specs/templates/project-template/` | 10 | 635 | Project wiki skeleton (CLAUDE.md 162, raw/spec.md 88, wiki/*) |
| `odin/project-registry.example.yml` | 1 | 68 | Registry schema example |
| `dvergr-hooks/` | 8 | 822 | Worker Claude Code hooks (bash) |
| `containers/{dvergr,odin,bragi,keepalive}/` | 8 | 1,312 | 4 Dockerfiles (394) + entrypoints (923, with `start-odin.sh` counted separately) + `claude-baseline.json` (521; **path only, not read**) |
| `scripts/` (non-auth) | 9 | 1,199 + 105 systemd | deploy, restart, Eir webhook/PR pipeline, Gitea API, readiness lib, 2 systemd units, 2 `*.env.example` (**variable names only read**) |
| `scripts/auth/` | 5 | 696 | `bootstrap-credentials.sh` 172, `launch-{odin 175, bragi 143, dvergr 142}-template.sh`, `run-keepalive.sh` 64. **Not read** (auth scripts); purposes from SETUP.md/README |
| `bragi/` | 2 | 414 | Bragi persona 283 + lessons-template README 131 |
| `eir/CLAUDE.md` | 1 | 362 | Eir persona |
| `mqtt/TOPIC-SCHEMA.md` | 1 | 463 | Topic and marker contract |
| `journal/` | 3 | 419 | Journal format + templates |
| `specs/incoming/saga-spec-dev.md` | 1 | 334 | The spec-dev project spec (contracts 1-5) |
| root (`CLAUDE.md` 282, `README.md` 236, `CHANGELOG.md` 109, `VERSIONS` 58, `LICENSE` 201, `.env.example` 176 **path only**, `.gitignore` 66) | 7 | 1,128 | |
| `docs/` | 95 | 36,188 total, of which 16,408 outside `history/saga-extraction` and `harness-research` | Design, decisions, contract, history |

There are **no docker-compose files, no CI configuration, no Makefile and no
pyproject** in the repository.

### A.2 Every Python module and script

| File | Lines | Purpose |
|---|---:|---|
| `odin/scripts/heimdall.py` | 904 | Host-VM root daemon. Polls `launch-requests/*.yml` every 2 s; validates; provisions the workspace and PRD; runs `docker run` / `docker stop`; writes `launch-results/<id>.yml`; applies the `depends_on` gate. Detail in §B |
| `odin/scripts/ratatoskr.py` | 886 | Sidecar inside the Odin container. **MQTT side:** subscribes to six `dvergr/+/+/…` patterns (L81-L92). Rewrites `scripts/state.json` from status (L125-L147). Appends journals to `incoming-journals/` (L258) and computes and publishes `metrics` (retained, L289-L329). Writes convergence/plateau/alert markdown to `incoming-alerts/` (L347-L490). **File side:** shells out to `inotifywait` (L585-L633) to publish `outgoing-guidance/<p>/<i>.md` as retained raw Markdown (L635-L673) and `outgoing-events/*.json` to `saga/events/<kind>` (L676-L726). Nudges Mimir via `tmux send-keys` on new `mimir/pending/*` (L729-L735). Writes `incoming-verdicts/*.json` markers and nudges Odin on new verdicts (L752-L793). **Other:** milestone dedup persisted to `milestone-state.json` (L150-L256); a daily spec-dev sweep thread (L801-L821) |
| `scripts/eir-webhook.py` | 231 | `http.server` on `0.0.0.0:9876`, no auth and no webhook-secret check (L165-L222). On Gitea PR `opened`/`reopened`, runs `process-eir-pr.sh` in a thread (600 s timeout, one retry on timeout). Writes failure markers to `/opt/saga/odin-ws/eir/failures/pr-N.md` plus an incoming alert, rate-limited to one per hour per PR (F12, L51-L109) |
| `odin/scripts/spec_dev/__init__.py` | 19 | Package doc; claims contracts 1-5 are encoded as code |
| `spec_dev/constants.py` | 76 | Paths, modes, command names, template resolution |
| `spec_dev/state.py` | 198 | `spec-dev-state.json`: atomic read/write, JSON-Schema validation (Draft 2020-12, `jsonschema`), transition helpers |
| `spec_dev/schemas/state.schema.json` | 100 | State schema (`mode`: active/compile-proposed/inactive, `project_type`, …) |
| `spec_dev/parser.py` | 205 | `/spec-dev` grammar (first token of first line) and the transition matrix with "polite error" strings (L98-L120) |
| `spec_dev/devlog.py` | 195 | `## Turn N — role — ISO` dev-log writer and reader; attachment stubs |
| `spec_dev/project_type.py` | 103 | Fixed project-type follow-up text (`FOLLOW_UP_TEXT`, L27-L34) and inference rules |
| `spec_dev/compile.py` | 435 | Draft `proposed-spec.md`; `confirm` seeds the wiki; `extract_contracts` copies `### Contract:` bodies verbatim with `hash: sha256:` frontmatter (L345-L403); rationale distillation; spec-shape check |
| `spec_dev/archive.py` | 134 | `/spec-dev abort` move and sweep of aborted sessions older than N days (`sweep_loop_iteration` is called by ratatoskr) |
| `spec_dev/tests/*.py` | 1,344 | 86 test functions: state 22, compile 17, parser 16, devlog 11, project_type 11, archive 8, integration 1; plus `conftest.py` 33 |

### A.3 Shell scripts

| File | Lines | Purpose |
|---|---:|---|
| `containers/dvergr/init-dvergr.sh` | 403 | Worker entrypoint, step by step: refuses to start without `/home/vscode/.claude/.credentials.json` (L37) or with `CLAUDE_CODE_OAUTH_TOKEN` set (L45); copies the `.claude.json` baseline (L63); model `claude-opus-4-7` at effort xhigh (L89); clones `DVERGR_REPO` into `/workspace/repo` on branch `stream-<instance>` (L126-L152); writes a workspace `.gitignore`; writes the fallback persona (L176-L274, about 98 lines); writes the project `.claude/settings.json` with the SessionStart and Stop hooks (L295-L322); starts `claude --dangerously-skip-permissions` in tmux (L331); sends `/effort` by send-keys; `/plugin install ralph-loop` (L356); `/ralph-loop:ralph-loop … --max-iterations --completion-promise` (L384); loops while tmux lives, then **always `exit 1`** (L398-L403) |
| `odin/scripts/start-odin.sh` | 206 | Odin container entrypoint: three tmux windows, `odin` (default model, `--channels plugin:telegram@claude-plugins-official`), `mimir` (`claude-sonnet-4-6`) and `sidecar` (ratatoskr). Requires `TELEGRAM_BOT_TOKEN`; extends `.claude.json` trust with `jq`; sets effort by send-keys |
| `containers/bragi/init-bragi.sh` | 191 | Bragi entrypoint: `git init` of the vault on first run, symlinks the persona, ralph-loop with promise `COMPILED`, max 10, effort low; `exit 0` |
| `containers/keepalive/keepalive.sh` | 123 | Credential exercise: starts a session, sends a trivial prompt and exits, so the token refreshes into the shared volume (comment lines only read) |
| `dvergr-hooks/pre-iteration.sh` | 42 | SessionStart hook: reads retained `guidance` (`mosquitto_sub -C 1 -W 2`, L32) into `.dvergr/latest-guidance.md` |
| `dvergr-hooks/post-iteration.sh` | 156 | Stop hook. Rewrites status to `max_iterations_reached` when the iteration cap is hit with 0 failing tests. Publishes `status` (retained, from `.dvergr/status.json`, L52) and `journal` (`tail -n 50`, L66). Pulls guidance (L79). Publishes `saga/events/dvergr_completed` once (L125). Runs the three check scripts |
| `dvergr-hooks/check-convergence.sh` | 166 | Journal word-count delta near zero for k iterations, then `…/converged` (retained) |
| `dvergr-hooks/check-commit-plateau.sh` | 136 | No new commits across N iterations, then `…/commit-plateau` |
| `dvergr-hooks/check-test-plateau.sh` | 138 | Tests stable and green, then `…/completion-likely` |
| `dvergr-hooks/install.sh` | 115 | Retrofits the hooks into a non-Saga devcontainer (jq merge) |
| `dvergr-hooks/mqtt-publish.sh`, `mqtt-subscribe.sh` | 29, 40 | `mosquitto_pub`/`mosquitto_sub` wrappers |
| `scripts/process-eir-pr.sh` | 277 | Fetches a PR and its diff from Gitea, writes a Mimir `patch-review-<N>.md` request into `/opt/saga/odin-ws/mimir/pending/` (via `tee`; the header says sudo is needed), polls `verdicts/` every 5 s for 300 s, and posts the verdict and a summary as PR comments |
| `scripts/review-eir-pr.sh` | 223 | Prints a pasteable review prompt for a dev-Claude cross-check of an Eir PR |
| `scripts/gitea-api.sh` | 74 | `curl`+`jq` wrappers: `gitea_pr_{list,create,view,diff,merge,close}` |
| `scripts/deploy.sh` | 175 | `git pull` from gitea/main, rebuild the dvergr/bragi/odin images, `sudo systemctl restart heimdall`, print a verification snapshot |
| `scripts/restart-odin.sh` | 154 | Copies personas into `/opt/saga/odin-ws/{odin,mimir}/CLAUDE.md`, then stops, removes and relaunches `saga-odin` |
| `scripts/lib/claude-ready.sh` | 65 | `wait_for_claude_ready`, `send_effort_with_verify` (TUI-driving helpers) |
| `scripts/auth/*` | 696 | Not read. From docs: credential bootstrap and image build (`bootstrap-credentials.sh --build`, SETUP.md L173), manual container launch templates (`sudo …launch-odin-template.sh`, SETUP.md L313), keepalive runner |

### A.4 Container images

All four images are `FROM saga-devcontainer:base`: the Trail of Bits Claude
Code devcontainer, built locally from git `48df2ad80d33…` (`VERSIONS` L21-L22).
Each runs `RUN claude update || true`, so the Claude Code version is unpinned at
build time.

| Image | Dockerfile | Entrypoint | What runs | Launched by |
|---|---|---|---|---|
| `saga-dvergr:latest` | `containers/dvergr/Dockerfile` 115 | `init-dvergr.sh` | one interactive Claude Code + ralph-loop worker | Heimdall (`kind: dvergr` only) |
| `saga-odin:latest` | `containers/odin/Dockerfile` 143 | `odin/scripts/start-odin.sh` | Odin (Opus, Telegram channel), Mimir (Sonnet), ratatoskr in one container. Copies **all** of `odin/scripts/` into the image, `heimdall.py` included (L80). `paho-mqtt==2.1.0`, `pyyaml==6.0.2`, Bun | `sudo scripts/auth/launch-odin-template.sh`, not Heimdall. It is still on Heimdall's image allowlist (L179) |
| `saga-bragi:latest` | `containers/bragi/Dockerfile` 75 | `init-bragi.sh` | Bragi compile pass over a read-only `/workspace/inputs` (the Odin workspace) into RW `/workspace/vault` and `/workspace/lessons` | `launch-bragi-template.sh`, manual or cron |
| `saga-keepalive` | `containers/keepalive/Dockerfile` 61 | `keepalive.sh` | token-refresh exercise of the shared credential volume | `run-keepalive.sh` from cron |

Every image mounts the **shared writable** `saga-claude-credentials` volume at
`/home/vscode/.claude`.

### A.5 Compose, systemd and cron

- **Compose:** none.
- `scripts/systemd/heimdall.service` (89 lines). The service runs as
  `User=root` with `EnvironmentFile=/etc/saga/heimdall.env` and
  `ExecStart=/usr/bin/python3 ${SAGA_REPO_DIR}/odin/scripts/heimdall.py`.
  `ProtectHome` is deliberately off because the repo lives under
  `/home/<user>/src/saga`. `NoNewPrivileges` is left at false. Only
  `ProtectKernel{Tunables,Modules}` and `ProtectControlGroups` are set.
- `scripts/systemd/eir-webhook.service` (16 lines): runs as `User=david` from
  `/home/david/saga-dev`, `EnvironmentFile` holds `GITEA_TOKEN`.
- **Cron:** no tracked crontab or timer. SETUP.md shows commented crontab lines:
  keepalive every 4 h (L272) and Bragi every 30 min (L439). ARCHITECTURE.md L1
  says Bragi's cron "is planned, not running".

### A.6 MQTT topic schema versus code

The broker is `192.168.86.12:1883`, shared with `surveillance/#`, `frigate/#`
and `homeassistant/#` (TOPIC-SCHEMA.md L403-L412). **No client sets a username,
password or TLS.** There is no `username_pw_set`, `tls_set`, `-u` or `-P` in
`ratatoskr.py` or `dvergr-hooks/`.

| Topic | Publisher in code | Subscriber in code | QoS / retain | Status |
|---|---|---|---|---|
| `dvergr/{p}/{i}/status` | `post-iteration.sh` L52 (from the worker's own `status.json`) | ratatoskr, into `state.json` | 1 / retained | implemented; **worker self-reported** |
| `…/journal` | `post-iteration.sh` L66 (last 50 lines) | ratatoskr, into `incoming-journals/` | 1 / no | implemented |
| `…/guidance` | ratatoskr L662 (raw Markdown) | `pre-iteration.sh` L32, `post-iteration.sh` L79 | 1 / retained | implemented; no revision, no operation id, no auth |
| `…/metrics` | ratatoskr L328-L329 | none in code (Telegraf per docs) | 1 / retained | publisher only |
| `…/converged`, `…/commit-plateau`, `…/completion-likely` | `check-*.sh` L162 / L132 / L134 | ratatoskr, into `incoming-alerts/` | 1 / retained | implemented |
| `…/alert` | **none** (an LLM could use `mqtt-publish.sh`) | ratatoskr L84 | 2 / no (doc) | documented only |
| `…/heartbeat` | **none** (the dvergr Dockerfile header still claims heartbeats) | none | 0 / retained (doc) | documented only |
| `dvergr/{p}/summary`, `dvergr/odin/{status,inbox,synthesis,commands}` | **none** | none | | documented only; `odin/commands` is the dead channel (TOPIC-SCHEMA.md L338-L361) |
| `saga/events/dvergr_completed` | `post-iteration.sh` L125 | none in code | 1 / no | implemented (the target ACL does not allow it, INC-07) |
| `saga/events/<kind>` (`decomposition_approved`, `prd_launched`, …) | ratatoskr L717, from `outgoing-events/*.json` that Odin writes by persona instruction | none in code | 1 / no | implemented |

Filesystem marker contract: `incoming-verdicts/<stem>.json` holds
`{ts, verdict_path, review_type, verdict_name}`, deduplicated by filename
(TOPIC-SCHEMA.md L414-L463; ratatoskr L752-L793).

### A.7 Launch-request YAML schema

The schema is the docstring at `heimdall.py` L30-L53, reproduced verbatim in the
pinned contract §17. The keys are `kind`, `project`, `instance`, `image`,
`action`, `env`, `workspace_source`, `repo`, `prd`, `gitea_credentials`,
`secrets` and `depends_on` (closed set at L151-L172). Validation is detailed in
§B.

### A.8 Mimir request/verdict file protocol

1. **Request.** Odin, or `process-eir-pr.sh`, writes
   `/workspace/mimir/pending/<id>.md`. Ids come from naming conventions:
   `decomposition-<project>`, `prd-<project>-<instance>`,
   `patch-review-<N>`, `guidance-…` (`odin/CLAUDE.md` L283, L321; ratatoskr
   `_infer_review_type` L738-L749).
2. **Wake.** ratatoskr sees the inotify event and sends
   `tmux send-keys -t odin:mimir "Review <path>" Enter` (L729-L735). This is the
   only way Mimir wakes; it never polls.
3. **Verdict.** Mimir writes `/workspace/mimir/verdicts/<id>.md`, starting with
   `# Verdict: APPROVE_UNCHANGED | APPROVE | FLAG | REJECT`, a paragraph, and
   sections for FLAG and REJECT. It then moves the request to
   `/workspace/mimir/processed/<id>.md` (`odin/mimir/CLAUDE.md` L97-L164). The
   checklists are prose: decomposition L269-L290, PRD L292-L334, patch L336-L392.
4. **Notify.** ratatoskr writes the marker `incoming-verdicts/<id>.json` and
   sends keys to Odin's pane (L752-L793). Odin must scan markers "at the end of
   every tool-call sequence and whenever you reach an idle prompt"
   (`odin/CLAUDE.md` L394-L418).
5. **Eir path.** `process-eir-pr.sh` polls for `verdicts/patch-review-<N>.md`
   for 300 s (L187-L212) and extracts `^## Verdict:` (L215).

Weaknesses found in code:
- **No authentication.** A verdict is any file that appears in `verdicts/`. Odin
  and Mimir share one Unix user and filesystem (A.4). The host Eir pipeline
  writes `pending/` directly.
- **No binding.** A verdict is not bound to a request id, a request revision or
  artifact digests. The filename is the only link.
- **A stale verdict can be reused.** The webhook also fires on `reopened`
  (`eir-webhook.py` L186), and `VERDICT_FILE="patch-review-${PR_NUM}.md"`
  (L115). An old verdict for the same PR number satisfies the poll at once. The
  script never deletes or checks the age of a prior verdict.
- **Format drift.** The persona prescribes an H1 `# Verdict:` header, but
  `process-eir-pr.sh` greps for an H2 `## Verdict:`. The request template it
  embeds shows `## Verdict:`, so the outcome depends on which template Mimir
  follows.
- **The Mimir gate is not enforced.** Heimdall checks no verdict. Odin's
  `mv launch-requests-draft/ → launch-requests/` is a persona step
  (`odin/CLAUDE.md` L334-L346).

### A.9 Dvergr hooks

- Hooks are wired through project-level `/workspace/.claude/settings.json`
  (`init-dvergr.sh` L295-L322): `SessionStart` runs `pre-iteration.sh` and
  `Stop` runs `post-iteration.sh`. The Stop hook runs after every model turn,
  which is treated as one iteration. The ralph-loop plugin's own Stop hook
  drives the loop.
- The worker contract lives in the fallback persona (`init-dvergr.sh`
  L176-L274). The worker reads `latest-guidance.md`, works the PRD, appends
  `.dvergr/journal.md`, overwrites `.dvergr/status.json` (JSON shape given in
  prose), emits the completion promise, and pushes `stream-<instance>`. Every
  status field is **self-reported by the LLM**. The hook only rewrites status to
  `max_iterations_reached`.
- The fallback persona's guardrails ("do not contact other services") are
  prose. The comments say `NET_ADMIN`/`NET_RAW` are kept "for the Trail of Bits
  firewall init", but **no Saga script invokes a firewall init**, and
  `init-dvergr.sh` replaces the base image's entrypoint. Inference: egress is
  probably unrestricted at runtime; verify on the VM.
- Inference from code: nothing in `init-dvergr.sh` exits Claude when the
  completion promise fires; the loop waits on `tmux has-session` (L398). If the
  plugin leaves the session open, the container stays up until someone stops
  it.

### A.10 Bragi

Bragi is a container, a persona and a launch template. It has no code and no
running cron.

| Piece | Path | Lines |
|---|---|---:|
| Persona (vault schema, lessons schema, "preserve verbatim") | `bragi/CLAUDE.md` | 283 |
| Lessons store template | `bragi/lessons-template/README.md` | 131 |
| Image | `containers/bragi/Dockerfile` | 75 |
| Entrypoint (vault `git init`, ralph-loop `COMPILED`, max 10, effort low) | `containers/bragi/init-bragi.sh` | 191 |
| Launcher (not read) | `scripts/auth/launch-bragi-template.sh` | 143 |
| Schedule | SETUP.md L439, commented `*/30` cron | — |

- **Inputs:** the whole Odin workspace, read-only.
- **Outputs:** an Obsidian vault Git repo and the lessons store, which Odin and
  Mimir read.

### A.11 Eir

Eir is a persona, a webhook and PR-pipeline scripts. It runs as a host tmux
session, not a container.

| Piece | Path | Lines |
|---|---|---:|
| Persona: PRs only, its own checkout `/home/david/src/saga-eir/`, the operator's VM credentials (`~/.claude/.credentials.json`), and "safety boundaries" (L278-L331), all prose | `eir/CLAUDE.md` | 362 |
| Design and backlog | `docs/agents/EIR.md` 506, `docs/agents/EIR-BACKLOG.md` 493 | |
| Webhook | `scripts/eir-webhook.py` + `eir-webhook.service` | 231 + 16 |
| Mimir patch-review pipeline | `scripts/process-eir-pr.sh` | 277 |
| Dev-Claude cross-review prompt | `scripts/review-eir-pr.sh` | 223 |
| PR helper | `scripts/gitea-api.sh` | 74 |

- **Privilege:** Eir runs as the operator user on the VM, and that user is in
  the docker group (`deploy.sh` header). "You wield no docker socket"
  (`eir/CLAUDE.md` L34) is a cultural boundary only.
- **Duplication:** the patch-review checklist exists twice, in
  `process-eir-pr.sh` L150-L180 and in `odin/mimir/CLAUDE.md` L336-L392.

### A.12 Telegram

There is no Saga code for Telegram. Odin's pane runs the first-party Claude Code
channel plugin (`start-odin.sh`:
`--channels plugin:telegram@claude-plugins-official`). The bot token reaches it
through `TELEGRAM_BOT_TOKEN`, which the launch template converts from a host
file (`containers/odin/Dockerfile` comments). Bun is installed only for that
plugin's MCP server. Outbound alerts and milestones depend on Odin choosing to
relay them (ratatoskr L205). `docs/features/voice-telegram.md` (143) is a plan.

### A.13 Gitea workflow

- **Hosting:** Gitea at `192.168.86.18:3000`.
- **Branches:** one worker per `stream-<instance>` branch
  (`init-dvergr.sh` L126-L152).
- **Push credentials:** Heimdall mounts `/opt/saga/secrets/gitea/<name>` as
  `.netrc`, read-only (`heimdall.py` L540-L547). The persona says always
  `saga-push` (`odin/CLAUDE.md` L315).
- **No branch enforcement:** nothing limits the credential to one branch
  (contract AUTH-2 / GAP-24).
- **Merging:** "Odin and the operator handle consolidation" (fallback persona).
- **Eir PRs:** created through `gitea-api.sh`, reviewed by Mimir through the
  webhook, merged by the operator. Deployment is `deploy.sh`.

### A.14 `spec_dev` deterministic scripts

- **Parser and state machine:** `parser.py` and `state.py` cover the 8
  (command, mode) pairs, plus `confirm`.
- **Schema:** `schemas/state.schema.json`.
- **Dev-log, compile and archive:** `devlog.py`, `compile.py` and `archive.py`,
  plus `project_type.py`.
- **Tests:** 86, listed in A.2.
- **Runtime callers:** `ratatoskr._spec_dev_sweep_loop` (L801-L821) is the only
  one. A grep of `*.py`, `*.sh`, Dockerfiles and JSON outside the package finds
  no other import or invocation. No hook routes Telegram turns through
  `parse_message`, and the persona has no command to run it. The persona assumes
  routing that does not exist (`odin/CLAUDE.md` L595-L607).
- **Run state:** "saga-spec-dev run #2: State unknown since May"
  (`docs/ROADMAP.md` L148).

### A.15 Tests and how they run

- **Present:** `odin/scripts/pytest.ini` (`testpaths = spec_dev/tests`,
  `pythonpath = .`) and `requirements-dev.txt` (`pytest>=8`, `jsonschema>=4`).
  The suite runs with `cd odin/scripts && pytest` (86 tests).
- **Absent:** no tests for `heimdall.py`, `ratatoskr.py`, `eir-webhook.py`, the
  hooks or the entrypoints. No CI. No fixture for the launch-request schema.

### A.16 Recorded defects, located in code

| Defect (CLAUDE.md L149 ff.; contract §17) | Location | Mechanism |
|---|---|---|
| Dead `commands/` channel | **No consumer anywhere.** References: `odin/CLAUDE.md` L510, L948; `ratatoskr.py` L401 (nudge text "write a commands/ record for heimdall"); `mqtt/TOPIC-SCHEMA.md` L338-L361; `docs/architecture/ARCHITECTURE.md` L204; `docs/saga-spec.md` L482, L574 | Heimdall globs only `LAUNCH_REQUESTS_DIR/*.yml` (L855). Ratatoskr has no `outgoing-commands` watcher |
| `depends_on` treats a crashed prerequisite as satisfied | `heimdall.py` `_dep_satisfied` L776-L809 | "Satisfied" means the container is not running (anchored `docker ps`, L756-L773) **and** any result file names that container with `status == approved`. Containers run with `--rm --detach` (L516-L517), so `approved` is written as soon as `docker run` returns 0 (L726). Any later exit (crash, OOM, stop) satisfies dependents. An **old** approved result for the same container name from an earlier run satisfies a new dependent immediately. `init-dvergr.sh` always exits 1 (L403), and `--rm` loses that code anyway |
| A held request produces no result | `run_forever` L858-L880 | Unsatisfied requests `continue` without `_write_result`. They are logged once a minute and rejected only after `DEP_WAIT_MAX_SECONDS` (24 h, L134, by file mtime) |
| A reused request id overwrites | `_write_result` L649 (`LAUNCH_RESULTS_DIR / f"{request_id}.yml"`, `tmp.replace`) | Request archives get a timestamp prefix (L669-L670); results do not. The id is the file stem (L681) |
| `approved` means only that `docker run` returned 0 | `process_request` L726 | — |

Further defects found in this pass, by code reading only:
- **Restart policy.** `init-dvergr.sh` says "Docker restart policy is set by the
  heimdall per spec §4", but Heimdall sets none, and `--rm` excludes one.
- **Timeouts.** A `docker run` timeout (60 s, L604) is reported as `error`
  (L734-L742), yet the container may have started. That is an uncertain outcome
  misreported.
- **Restart race.** `restart` runs `docker stop` and then `docker run`
  immediately (L719-L721). Removal of the `--rm` container is asynchronous, so
  the run can fail on a name conflict. Inference.
- **Verdicts.** Stale-verdict reuse and the H1/H2 header mismatch (A.8).
- **Webhook.** No authentication on `0.0.0.0:9876` (A.2).

---

## B. Saga's launcher (`odin/scripts/heimdall.py`, 904 lines) in detail

### B.1 Inputs

| Variable or input | Default | Line |
|---|---|---|
| `SAGA_LAUNCH_REQUESTS` | `/opt/saga/odin-ws/launch-requests`; Odin's `/workspace/launch-requests` bind mount, so Odin writes there directly | L114 |
| `SAGA_LAUNCH_RESULTS` | `…/launch-results` | L115 |
| `SAGA_WORKSPACES_ROOT` | `/opt/saga/workspaces` | L116 |
| `SAGA_CREDENTIALS_VOLUME` | `saga-claude-credentials` | L117 |
| `SAGA_SECRETS_ROOT` | `/opt/saga/secrets`, with `projects/<p>/<name>` and `gitea/<name>` | L127-L129 |
| `SAGA_DEP_WAIT_MAX_SECONDS` | 86,400 | L134 |
| `ODIN_WORKSPACE_HOST` | `/opt/saga/odin-ws` | L139 |
| `LOG_LEVEL` | — | — |
| Poll interval | 2 s, fixed | L141 |
| Request id | the YAML file stem | L681 |

### B.2 Validation rules (`validate`, L240-L384)

| Rule | Lines | Note |
|---|---|---|
| Document must be a mapping; unknown top-level keys rejected | L248-L255 | Closes `runArgs`- and `entrypoint`-style escape hatches |
| `kind == "dvergr"` | L257-L263 | Odin, Mimir and Bragi launches stay outside |
| `project` and `instance` match `^[a-z0-9][a-z0-9-]{0,31}$` | L194, L265-L270 | |
| `image ∈ ALLOWED_IMAGES` | L177-L182, L272-L274 | Both `saga-dvergr:latest` **and** `saga-odin:latest` are allowed under `kind: dvergr` |
| `action ∈ {start, stop, restart}` (default start) | L276-L278 | `stop` needs a full valid request (image, workspace) |
| `env`: mapping; key must be a `str` and not in `ENV_DENYLIST`; no value character below 0x20 | L186-L192, L280-L294 | The denylist is `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `DOCKER_HOST`, matched exactly. **Key syntax is not validated**: a key containing `=` or control characters is accepted. Low severity, because worker code execution inside the container is by design |
| `workspace_source` must be a string; after `resolve()` it must be under `WORKSPACES_ROOT` | L296-L304 | **Equal to the root also passes**, so the whole workspaces root can be mounted. Not bound to `<project>/<instance>` |
| `repo` and `prd` are strings | L307-L313 | `repo` is exported as `DVERGR_REPO`; there is no URL allowlist |
| `gitea_credentials` matches `NAME_RE` | L317-L320 | Any name under `secrets/gitea/`; **not bound to the project** |
| `secrets[]` match `NAME_RE`; the mapped env name must not hit the denylist or collide with `env` | L325-L341, L387-L399 | Bound to `secrets/projects/<project>/`, but the requester chooses the project |
| `depends_on[]` entries are `p/i` or bare `i`; parts match `NAME_RE`; no self-reference | L346-L364 | Cycles are left to Mimir |
| Workspace provisioned; `PRD.md` exists | `provision_workspace` L420-L459 | Copies `prd` when `PRD.md` is absent; else fails |

### B.3 Image allowlist

The allowlist is a hardcoded set, `{"saga-dvergr:latest", "saga-odin:latest"}`
(L177-L182). Changing it requires editing the file and restarting the service.
Tags are mutable `:latest`, with no digest pinning.

### B.4 Credentials, secrets and env rejection

- **Shared credentials:** `-v saga-claude-credentials:/home/vscode/.claude` is
  added unconditionally (L525), so every worker shares one writable login.
- **Gitea:** the `.netrc` file is mounted read-only after
  `_load_secret_file`'s checks: it must exist, be a regular file, be owned by
  uid 0 and have no group or other bits (L478-L501, L540-L547).
- **Project secrets:** values are read as root and injected as `-e NAME=value`
  (L568-L574). Values appear in the `docker` argv, so they are visible in `ps`
  for the length of the call; this is documented. Values are not logged, and the
  debug log redacts them (L579-L598).
- **Env rejection:** the exact-match denylist (L186-L192). The entrypoints
  re-check `CLAUDE_CODE_OAUTH_TOKEN` (`init-dvergr.sh` L45).

### B.5 Docker invocation

`exec_docker_run` (L504-L607) builds the argv by construction:
- **Fixed flags:** `docker run --name saga-<p>-<i> --rm --detach --cap-drop=ALL
  --cap-add=NET_ADMIN --cap-add=NET_RAW -v <creds> -v <ws>:/workspace
  -e DVERGR_PROJECT -e DVERGR_INSTANCE`.
- **Optional parts:** `DVERGR_REPO`, the `.netrc` mount, the env pairs (the
  identity vars are skipped) and the secret env pairs, followed by the image.
- **Missing:** resource limits (`--memory`, `--cpus`, `--pids-limit`), a
  `--network` choice, labels carrying the request id, read-only rootfs and a
  seccomp or AppArmor profile.
- **Timeouts:** `timeout=60` for run (L604). `exec_docker_stop` runs
  `docker stop -t 30`, with a 40 s timeout (L610-L625).

### B.6 Result files and archive

- **Result file:** `launch-results/<request_id>.yml` contains `{request_id,
  status: approved|rejected|error, rc, output (≤ 8 KiB, L146, L467-L475),
  container_name, timestamp}`, written atomically through `.tmp` and `replace`
  (L633-L660).
- **Archive:** the request moves to `processed/` or `rejected/` with a UTC
  timestamp prefix (L663-L671).
- **Guarantee:** every path except the held path writes a result (L674-L753).

### B.7 Dependency handling

- **Pre-parse:** `_check_deps_satisfied` (L812-L836) parses the raw YAML before
  validation. A parse error or invalid entry counts as "satisfied", so
  validation rejects it downstream.
- **Defect:** see A.16.
- **Failures:** a failed dependency (`error` or `rejected`) blocks dependents
  until the 24 h rejection ("operator intervention required … by design",
  L782-L784). Dependents are not told why in the meantime.

### B.8 Concurrency, TTL, kill switch and cancellation

| Control | In code? | Where it is promised |
|---|---|---|
| Concurrency cap | **No.** Containers are started serially in sorted glob order, with no count | ROADMAP Phase B L56-L59; contract ADM-12 (open, GAP-16) |
| Container TTL, budgets, presence gate | **No** | ROADMAP Phase D L92; contract PH-4 |
| Kill switch (`/stop all`) | **No** | ROADMAP L59; contract ST-1, ST-6 (persistence open) |
| Stop by delegation | **No.** Only per-container `action: stop` by name; any request can stop any `saga-*-*` container | ST-1 to ST-4 |
| Cancellation with reason and an uncertain outcome | **No.** A stop's non-zero exit becomes `error` | B-05, OP-5 |
| Revocation | **No** | ST-5 |
| Reconciliation after a restart | **No.** `--rm` loses exit codes; no state is persisted | RCV-4 (GAP-19) |

### B.9 Confinement weaknesses (code reading only, not reproduced)

1. **Arbitrary host-file read as root.** `prd` values that do not start with
   `/workspace/` are used as host paths (`Path(prd).resolve()`, L417). Values
   under `/workspace/` are joined without normalizing or checking containment
   (L415-L416, so `/workspace/../../etc/shadow` works). `shutil.copy2` runs as
   root into the worker workspace and then `chown 1000:1000` (L450-L452). The
   bytes are then readable by the worker, which has network egress.
2. **Workspace root mount and cross-project mounts** (L299-L304, above).
3. **Gitea credential not scoped to the project** (L317-L320).
4. **Symlink following as root.** On `start`/`restart`, if a previous worker
   left `/workspace/PRD.md` as a dangling symlink, `prd_dest.exists()` is False.
   `copy2` then writes the PRD bytes through the link, and `os.chown` follows it
   (L442-L452). The result is a root write and chown to a host path the worker
   chose.
5. **Code provenance.** The root daemon executes `heimdall.py` from the repo
   checkout (`heimdall.service` `ExecStart`). The operator user can write that
   checkout, and so can any agent running as that user on the VM (dev Claude;
   Eir's sibling checkout is a separate directory). The Docker boundary
   therefore includes "whoever can write `/home/david/src/saga`".
6. **No authentication of the requester.** Anything that can write
   `/opt/saga/odin-ws/launch-requests/` (Odin's container, host users) is an
   authorized submitter.

### B.10 What is reusable for the EXECUTION BACKEND, and what must be rewritten

**Reusable** (pattern, sometimes code):
- **Closed key set and name rules:** the closed request key set and
  unknown-key rejection, `NAME_RE`, the kind gate and the image allowlist
  (L151-L194, L248-L278). Reuse them as one layer of the admission schema,
  re-expressed as a *published* schema (ADM-10, IG-4).
- **Argv by construction:** hardcoded flags, never `--privileged`, never host
  network or PID (L504-L576). Keep the pattern; add limits and labels; drop
  `--rm`.
- **Secret handling:** the secret-file permission check (L478-L501), the
  secret-to-env mapping with denylist and collision checks (L322-L341,
  L387-L399) and the redacted debug logging (L579-L598).
- **Result discipline:** every outcome is recorded, with atomic temp-and-replace
  writes (L633-L660, L674-L753). This becomes operation records.
- **Docker queries:** the anchored `docker ps` match and the fail-safe
  "unknown means still running" (L756-L773), reused for reconciliation.
- **Timeouts:** bounded docker calls (L600-L625). A timeout must map to
  `uncertain`, not `error`.

**Must be rewritten:**
- **Transport and identity:** directory polling with the file stem as id
  becomes a local API with client-minted ULID operation ids, idempotency and
  `409` on conflicting reuse (B-00, B-02, B-13).
- **Provisioning:** the backend derives the workspace from the run id and
  copies the PRD from submitted content, then hashes the copy and launches from
  the copy (ADM-3 "copy first, hash the copy"). It must refuse symlinks
  (`O_NOFOLLOW`, `lstat`). It must never accept a host path from the client.
- **Credentials:** the shared credential volume becomes per-run lineages
  injected at run time (AUTH-3). The Gitea credential is bound to the
  delegation, project and branch (AUTH-1, GAP-24). Secrets are bound to the
  delegation's named list.
- **Status and lifecycle:** `approved` (docker returned 0) becomes the D5 states
  in a ledger (queued, started, verified, terminated with a captured exit code);
  `--rm` is removed and exit codes captured.
- **Dependencies:** `depends_on` is satisfied only by a `verified`
  prerequisite, and a held run is visible as `queued` with its reason (LC-4,
  LC-5).
- **Stop and restart:** `action: stop/restart` becomes cancellation with
  outcome `acknowledged` or `uncertain`. A restart is a new submission request
  id with renewed coverage (ID-4, IG-3).
- **New, with no precursor:** digests, verdict and approval binding,
  reviewer-key verification, the concurrency cap, the four stop operations, a
  persisted kill switch, revocation, reconciliation on restart, the evidence
  store, the event cursor and per-run broker credentials.
- **Deployment:** the backend runs from a root-owned, versioned install path,
  not from a user-writable checkout.

### B.11 Gap table: pinned contract capability → existing code

The pinned contract is `docs/contracts/saga/2026-10-14-14fdab3/SAGA-SERVICE.md`
`0.1.1-draft`. Requirement ids are from Odin's I/O contract Appendix B and the
pinned contract's sections.

| Capability | Existing code (path:lines) | Status |
|---|---|---|
| B-00 Local API + client library, idempotent writes | none; file drop dir (`heimdall.py` L845-L889) | **NONE** |
| B-01 Delegation read/create/version | — | **NONE** |
| B-02 Schema / allowlist validation | `heimdall.py` `validate` L240-L384 | PARTIAL (no published schema; holes in B.9) |
| B-02 / ADM-3 `prd_digest` recomputed at admission | — (no `hashlib` in `heimdall.py`; the only sha256 is `spec_dev/compile.py` L389-L391 for wiki contracts) | **NONE** |
| B-02 / ADM-3 `launch_config_digest` | — | **NONE** |
| B-02 / ADM-3 verdict bound to the submission request id and digests | — (verdicts are unbound Markdown files, A.8) | **NONE** |
| B-02 / ADM-5 approval bound to request id, revision and proposal digest | — (approval is Odin interpreting a Telegram reply, then `mv`) | **NONE** |
| B-02 idempotent on request id; refusal reasons | refusal string in the result (`heimdall.py` L692-L696); id overwrite (L649) | PARTIAL / defective |
| ADM-2.3 limits (concurrency, TTL, budget, presence) | — | **NONE** |
| ADM-6 missing reviewer never a waiver | prose only (`eir/CLAUDE.md` "If Mimir is unreachable, you wait"); `process-eir-pr.sh` L208-L212 posts a timeout note | **NONE in code** |
| ADM-10 validator available to clients | `validate()` inside unpublished `heimdall.py` | **NONE** (IG-4) |
| ADM-11 mechanical checks (byte-identical contracts, cycles, secrets declared, git workflow) | contract hashing in `spec_dev/compile.py` L389-L403 (no caller); checks done by Mimir prose (`odin/mimir/CLAUDE.md` L301-L334) | **NONE at admission** |
| B-03 Read runs / D5 states | `launch-results/*.yml` (L633-L660); ratatoskr `state.json` (L125-L147, self-reported) | PARTIAL, not D5 |
| B-04 Guidance with `guidance_rev`, routine vs material, fail-closed | ratatoskr L635-L673 (raw retained publish) | PARTIAL, no rev, class or binding |
| B-05 Cancel with reason, uncertain outcome | `exec_docker_stop` L610-L625 by name | PARTIAL |
| B-06 Evidence by kind and iteration | journals to `incoming-journals/` (ratatoskr L258); workspace `.dvergr/` | PARTIAL, no store |
| B-07 / B-08 / B-09 Structured requests, answers, consumption ack | — | **NONE** |
| B-10 Verdict recorded under a verified reviewer key | — | **NONE** |
| B-11 Operator approval record | — | **NONE** |
| B-12 Resumable event cursor | — (`saga/events` not retained; `state.json` overwritten) | **NONE** |
| B-13 Operation lookup (six results, 30-day retention) | — | **NONE** |
| B-15 / ST-1 to ST-6 Stop by delegation or all, kill switch, per-op report | — | **NONE** |
| B-16 Eir task submission | — (Eir is an operator-run tmux session) | **NONE** |
| B-17 / MQ-5 Only Saga writes guidance and answers; worker ACL | — (broker unauthenticated) | **NONE** |
| LC-4 Dependency on `verified` | `_dep_satisfied` L776-L809 | WRONG semantics |
| LC-5 Held run visible as `queued` | L858-L880 (no result) | **NONE** |
| RCV-1 Client restart leaves workers alone | incidentally true (detached containers) | PARTIAL |
| RCV-4 Saga restart reconciliation | — | **NONE** |
| AUTH-1 / GAP-24 Repository-scoped, branch-only push | `.netrc` mount, not project- or branch-bound (L540-L547) | **NONE** |
| AUTH-3 Per-worker credential lineages | shared volume (L525) | **NONE** |
| AUTH-5 Env denylist | L186-L192, L287-L288; entrypoints L45 | PRESENT |
| AUTH-6 cap-drop, no privileged / host net / host PID, image allowlist, secret-file perms, values not logged | L513-L529, L177-L182, L478-L501, L579-L598 | PRESENT (no resource limits) |
| MQ-4 Per-run broker credentials | — | **NONE** |
| MQ-8 Retained-publication reconciliation | — | **NONE** |
| VER-* `verified` from evidence | — (`approved` = rc 0, L726) | **NONE** |
| PH-1 "launcher defects fixed; `commands/` deleted" | — | NOT DONE |
| CT-01 to CT-24 Producer conformance checks | — (no launcher tests) | **NONE** |

---

## C. Prose and persona versus code in Saga

### C.1 Ratio

| Category | Lines |
|---|---:|
| Python runtime (`heimdall` 904, `ratatoskr` 886, `eir-webhook` 231) | 2,021 |
| `spec_dev` library + schema | 1,465 |
| `spec_dev` tests | 1,344 |
| Shell: hooks 822, container entrypoints 923, scripts 968, auth 696 | 3,409 |
| Dockerfiles 394, systemd 105 | 499 |
| **Code total** | **≈ 8,740** |
| Personas (table C.2) + embedded fallback persona (98) | 2,659 |
| Contract-like Markdown (TOPIC-SCHEMA 463, JOURNAL-FORMAT 305 + templates 114, project template 635, lessons template 131, saga-spec-dev 334) | 1,982 |
| `docs/` | 36,188 |

### C.2 Persona sizes

| Persona | Path | Lines |
|---|---|---:|
| Odin | `odin/CLAUDE.md` | 1,021 (spec-dev mode alone is L538-L919, about 380 lines) |
| Mimir | `odin/mimir/CLAUDE.md` | 451 |
| Eir | `eir/CLAUDE.md` | 362 |
| Bragi | `bragi/CLAUDE.md` | 283 |
| Per-project wiki CLAUDE.md template | `odin/specs/templates/project-template/CLAUDE.md` | 162 |
| Dvergr fallback | embedded in `containers/dvergr/init-dvergr.sh` L176-L274 | ≈ 98 |
| Repo developer instructions (not a runtime persona) | `CLAUDE.md` | 282 |
| Also: kickoff prompts as shell strings | `DVERGR_PROMPT` (`init-dvergr.sh` L374), `BRAGI_PROMPT` (`init-bragi.sh`) | 1 line each |

### C.3 Persona content that encodes contracts, and where the code should go

| Persona text | Contract it carries | Enforced by code today? | Proposed home |
|---|---|---|---|
| `odin/CLAUDE.md` L255-L267, ingest step 4: contracts copied byte-identically into `wiki/contracts/<slug>.md` with a `hash:` frontmatter | contract extraction | Code exists (`compile.py` `extract_contracts_to` L373-L403) but has **no caller**; Odin does it by hand | Odin service spec-ingest operation; the backend's admission check recomputes hashes (ADM-11) |
| `odin/mimir/CLAUDE.md` L301-L334: `contracts_verbatim` ("PRD-spliced copy should produce the same hash… Mismatch = REJECT"), `secrets_declared`, `dependencies_explicit`, `git_workflow`, `self_modifying` (path list → FLAG) | mechanical PRD checks done by an LLM | No | Backend admission pre-checks (hash equality, declared secrets ⊆ references, `depends_on` ↔ decomposition, path-based self-modification → requires operator approval) |
| `odin/CLAUDE.md` L611-L625 §2 project-type follow-up "MUST be the verbatim contract message" | spec-dev Contract 4 | The string exists in `project_type.py` L27-L34 **and** in prose (two copies) | Odin service renders it from code; drop the prose copy |
| `odin/CLAUDE.md` L758-L772 §7 option-4 refusal, "byte-identical refusal string" | spec-dev | **Prose only**; not in `spec_dev` code | Parser/transition table |
| `odin/CLAUDE.md` L776-L800 §8 out-of-state errors ("byte-identical and load-bearing (Mimir checks it verbatim)") | spec-dev Contract 3 | **Drifted:** prose says ``[spec-dev]: `/spec-dev confirm` is only valid after a compile proposal; …`` while `parser.py` L117-L118 says "Nothing to confirm — no compile proposal pending." and "Can't confirm yet — run `/spec-dev compile` first …" | Single source in `parser.py`; Mimir check becomes a test |
| `odin/CLAUDE.md` L595-L607 §1 "Command parsing is not your job" | parser routing | No route exists (A.14) | Inbound handler in the Odin service (deterministic command routing before any session) |
| `odin/CLAUDE.md` L679-L706 §4 `[fleet]:` / `[spec-dev]:` outbound prefixes | outbound surface tagging | No | Telegram adapter |
| `odin/CLAUDE.md` L394-L447 verdict-marker scan and Eir-failure scan "at end of every tool-call sequence" | event delivery | No (compliance-dependent) | Odin service event intake and wake policy |
| `odin/CLAUDE.md` L138-L228 master-journal REQUIRED structure and project-completion ritual | memory and retrospective format | No | Odin history records / scheduled session class |
| `odin/CLAUDE.md` L270-L346, steps 8-11: lifecycle event JSON shapes; "Always include `gitea_credentials: saga-push`"; draft→launch `mv` only after APPROVE | event schema, launch defaults, the review gate | No (Heimdall does not check verdicts) | Backend emits lifecycle events; credential defaults from the delegation; admission requires the bound verdict (ADM-3) |
| `odin/CLAUDE.md` L957-L987 project registry | registry schema | No (example YAML only) | Odin records |
| `odin/mimir/CLAUDE.md` L97-L164 four verdict formats and the pending→processed move | review protocol | No | Review record schema written by the reviewer process under its key (B-10) |
| `odin/mimir/CLAUDE.md` L336-L392 and `process-eir-pr.sh` L150-L180 patch-review checklist (two copies) | review policy | No | One review-type definition in code |
| `eir/CLAUDE.md` L278-L331 "cannot edit heimdall.py / auth scripts / own persona; cannot push main; cannot deploy; cannot stop containers" | change-control policy | No (Eir runs as the docker-group operator user) | Branch protection/CODEOWNERS on Gitea; admission path rules; Eir as a container run without Docker or host access |
| Fallback dvergr persona (`init-dvergr.sh` L176-L274) `status.json` shape, journal template, push to the stream branch only | worker contract | Partly (hooks read the file; nothing validates its shape) | Worker contract document + schema; backend validates the status payload; branch-scoped push credential |
| `bragi/CLAUDE.md` vault and lessons schema | knowledge-store format | No | Bragi session-class output schema |

### C.4 Drift between prose and code (evidence that contracts belong in code)

- **spec-dev error copy:** the persona and the parser disagree (C.3).
- **`commands/`:** the persona (two places), the schema and the ratatoskr nudge
  all describe a channel with no consumer (A.16).
- **Heartbeat:** the dvergr Dockerfile header says heartbeats are published;
  no code publishes them.
- **Restart policy:** `init-dvergr.sh` says Heimdall sets one; it does not.
- **Verdict header:** H1 in the persona, H2 in `process-eir-pr.sh` (A.8).
- **Heimdall docstring:** it says "env must not contain CLAUDE_CODE_OAUTH_TOKEN
  or ANTHROPIC_API_KEY". The code also denies the AWS keys and `DOCKER_HOST`,
  and does not validate key syntax.

---

## D. wayland-computer-use

### D.1 Layout and size

- **Tracked:** 248 files, 68,680 lines in total, of which 48,838 are JSON
  (keyboard catalogs, benchmark data and reports).
- **Runtime Python:** 5,241 lines (`server.py`, `dev_host.py`, `cu/`,
  `observer_server.py`).

| Path | Lines | Role |
|---|---:|---|
| `scripts/server.py` | 1,745 | `wayland` MCP server: `Desktop` class, tool schemas (L1534-L1631), `validate` (L1633-L1698), stdio JSON-RPC `serve` (L1701-L1745) |
| `scripts/dev_host.py` | 251 | Stable stdio host that hot-loads SHA-identified runtime bundles from `.dev/releases/`; fails closed on a tool-contract mismatch |
| `scripts/cu/observation.py` | 577 | Shared observer (`Observer`, `Collector`); observer `TOOLS` (L540-L543); renewable 120 s collection lease (L327, L506) |
| `scripts/cu/system.py` | 178 | `run()` (L24), `desktop_locked()` scans `/proc/*/comm` for `hyprlock` and fails closed (L39), `owned_socket` (same-uid sockets, L110), `session_env` (L128), `YDOTOOL_SOCKET` default (L167) |
| `scripts/cu/execution.py` | 130 | `Deadline` (1–120,000 ms, default 60,000), `Ledger` (per-step injection/verification states, `performed()` returns `unknown` when in flight), `TransitionReadiness` |
| `scripts/cu/pixels.py` / `capture.py` / `native/capture.c` | 141 / 132 / 218 | Pixel diff; persistent wlr-screencopy helper with raw `grim -s 1` fallback (`capture.py` L117) |
| `scripts/cu/accessibility.py` / `accessibility_worker.py` | 116 / 230 | AT-SPI worker (`gi.require_version('Atspi','2.0')`), scoped to one app PID and title, never a desktop-wide dump |
| `scripts/cu/app_surfaces.py` / `obsidian.py` | 216 / 261 | `open_uri` via `gio open` / `xdg-open` (L40-L60); `cdp_read` (loopback only); Obsidian note creation with durable receipts |
| `scripts/cu/{context_records,context_retrieval,braid_client,recipes,feedback,trace,events}.py` | 196, 276, 253, 77, 41, 265, 101 | Task context retrieval, optional Braid backend (SHA-pinned), tracing, Hyprland `.socket2` events |
| `scripts/keyboard_context.py` | 460 | Builds keyboard catalogs (`hyprctl binds` etc.) |
| Evaluation and benchmark scripts | 1,747 | `pilot_model_evaluation.py`, `evaluate_transfer.py`, `audit_model_session.py`, `benchmark_*.py` |
| `wayland-desktop-observer/scripts/observer_server.py` | 54 | `wayland_observer` stdio server; imports `cu.observation` |
| `wayland-desktop-observer/baseline/` | 5 files (`server.py` 614) | Frozen pre-consolidation comparison baseline |
| `skills/wayland-computer-use/` | `SKILL.md` 139; references: `execution-and-context.md` 76, `environment-context.md` 168, `application-surfaces.md` 53, `keyboard/*.json` catalogs (neovim 8,700, lazyvim 5,277, davinci-resolve 3,885, herdr 1,128, chromium 895, …) with upstream licences | Agent instructions |
| `docs/` | 8 files, 1,171 | references, latency, feedback, transition readiness, Obsidian transfers, model evaluation |
| `tests/` | 4,041 Python lines in total (incl. observer tests) | 191 `test_` functions in 18 files (README L316-L320: 191 run, 184 pass, 7 Braid skips on `c618243`); observer 31; baseline 28. Live desktop tests (`live_input.py`, `live_text_entry.py`, `live_cdp_read.py`, `browser_scroll.py`, `smoke.py`) are not auto-discovered |
| Packaging | `.codex-plugin/plugin.json`, `wayland-desktop-observer/.codex-plugin/plugin.json`, `.mcp.json` ×2 | Codex plugins (`skills`, `mcpServers`). **No Claude Code plugin manifest.** Claude Code use is through `--mcp-config` (README L31-L58); only a read-only `desktop_state` call was tested on 2026-10-14 with CC 2.1.296 |
| Input service | `scripts/wayland-computer-use-mouse.service` 22, `install-mouse.sh` 11, `update-input-service.sh` 8, `wayland-computer-use.conf` | Root `ydotoold` systemd unit |
| License | `LICENSE` (Apache-2.0, added 2026-10-14) | |

Local-only and ignored: `.dev/` (releases, benchmarks, keyboard context),
`.claude/settings.local.json` (path only), and `.private/`, a dotprivate sparse
clone excluded by the global ignore. `.git/hooks/post-commit` has the dotprivate
sync hook.

### D.2 The two MCP servers and their tools

**`wayland` (root; serverInfo `wayland-computer-use` 0.1.0; contract
`wcu-tools-5` locally, `wcu-tools-4` on origin).** 19 tools, defined at
`server.py` L1580-L1631:

| Tool | One-line purpose |
|---|---|
| `context_for_task` | Read bounded task context (keyboard/app catalog, local or Braid ranking); never injects input |
| `desktop_state` | Hyprland monitors, windows, active window, tool availability, ydotool socket writability, runtime identity and contract hash |
| `screenshot` | Capture one monitor; returns the image and a `frame_id` required for input |
| `focus_window` | Focus a window by address; returns scoped evidence and a deferred frame |
| `pointer` | Move or click at viewed-frame coordinates |
| `type_text` | Type literal UTF-8 in the focused app (newlines may submit) |
| `press_key` | Key or chord |
| `scroll` | Wheel steps at coordinates |
| `drag` | Left-button drag inside one frame; always releases |
| `run_steps` | 1–12 deterministic steps under one approval, verifying conditions between steps; pinned target |
| `open_uri` | Launch an http(s) or bounded Obsidian URI through `gio`/`xdg-open`; no blind repeat |
| `obsidian_create_note` | Create and verify one note with a durable `operation_id` receipt; no overwrite |
| `obsidian_note_status` | Reconcile a note operation; never dispatches |
| `cdp_read` | Read a loopback Chromium CDP page by selector (`WCU_CDP_PORT`); no eval or navigation |
| `view_frame` | View retained pixels; expiry never refreshes |
| `read_text` | Bounded non-protected text from the focused control or a scoped selector |
| `observe_window` | Text-first accessibility and revision deltas for one focused window |
| `wait_for` | Wait for accessible, window or pixel conditions; no input |
| `stop_observing` | Stop background observation and clear history |

Every tool carries MCP annotations (`readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint: true`) and `additionalProperties: false`
(L1570-L1577).

**`wayland_observer` (serverInfo `wayland-desktop-observer` 0.2.0).** 4 tools
(`observation.py` L540-L543):
- `observe`: versioned desktop evidence.
- `wait_for_change`: any revision change, up to 30 s.
- `wait_for`: an exact accessible name, a unique window or a changed region.
- `stop_observing`.

Its instructions say "Revisions and control refs are not input capabilities"
(`observer_server.py`).

### D.3 Guard implementations

| Guard | Code | Behaviour |
|---|---|---|
| Frame expiry | `server.py` L626-L627, L858-L859, L893-L894; `expires_at_ns` L651 | 120 s from capture; viewing never refreshes. **Frames are single-use**: `self.frames.clear()` before every input segment (`perform.submit` L1208) |
| View-before-coordinates | L816-L817 | Coordinate input is rejected unless the frame's image was delivered |
| Pinned target identity | `check_target` L802-L810; `recheck_target` L1051-L1060 | Monitor layout unchanged; target window's address, geometry and title unchanged; checked before **every** segment through `recheck()` in `submit` |
| Focus check | `guard` L891-L902; `prepare` L812-L889 | Active window must equal the frame's; `restore_focus=true` requires `target_window` and `target_title` to match the screenshot target, refocuses through `hyprctl dispatch`, waits, then re-verifies |
| Coordinate containment | L875-L882 | Input points must fall inside the approved target rectangle |
| Pixel check | `visual_guard` L316-L345; used L758-L760, L824-L829, L861-L873 | Re-captures the target. Rejects when the max channel difference exceeds 6 (with an action region) or 2 (without), when over 2% of pixels changed, or when the action region differs by more than 2. Heuristic, not proof |
| Lock check | `cu/system.py` `desktop_locked` L39; checked at capture (L585, L594) and before input or dispatch | `/proc` scan for `hyprlock` only, fail-closed |
| Budgets | `cu/execution.py` `Deadline` (default 60 s, max 120 s); `run_steps` ≤ 12 steps; `type_text` in 40-char `wtype` segments (`server.py` L158-L170); per-call subprocess timeouts | Cooperative per-request deadline. **No per-session, per-minute or cumulative budget; no rate limit** |
| No replay | `call` L955-L971, `recover` L1027 ff. | On exception after input started, reports `action_performed: unknown`, `requires_review: true`; never retries |
| Transition readiness | `TransitionReadiness` (`execution.py`) | After a window transition, typing needs fresh focused-editable evidence, or delivered visual evidence |

Measured limit, from README L310-L313: "In a natural asynchronous focus race, 40
characters reached a decoy window before the next segment guard rejected the
rest. Zero wrong-window input is not claimed."

### D.4 Input path

| Input | Mechanism | Code | Who can reach it |
|---|---|---|---|
| Keyboard text and keys | `wtype -` (stdin, 40-char segments) and `wtype <key args>`. This is the Wayland virtual-keyboard protocol through the compositor, **not uinput** | `perform` L1218-L1223 | Any client of the user's Wayland socket |
| Pointer move | `hyprctl dispatch 'hl.dsp.cursor.move({x=..,y=..})'` | `Desktop.move` L915-L916 → `dispatch` L442-L453 | Any process that can reach the Hyprland IPC socket (same uid) |
| Click, scroll, drag buttons | `ydotool click/mousemove --wheel` with `YDOTOOL_SOCKET=/run/wayland-computer-use-<uid>/mouse.sock` | `Desktop.mouse` L918-L921 | Root `ydotoold` holds `/dev/uinput` (`DeviceAllow=/dev/uinput rw`); socket `--socket-own=1000:1000 --socket-perm=0600` (`wayland-computer-use-mouse.service`). Any uid-1000 process |
| Focus | `hyprctl dispatch 'hl.dsp.focus({window="address:0x…"})'` | `dispatch` L442-L453; called from `prepare` L852, `focus_window` L1128, `run_steps` L1455 | Same uid |
| App launch | `gio open <uri>` or `xdg-open` (`Popen`, new session) | `cu/app_surfaces.py` `dispatch_uri` L40-L60; `open_uri` L1080-L1095; Obsidian notes | Same uid |

### D.5 Screenshot, AT-SPI and event paths

- **Screenshot:** a persistent native wlr-screencopy helper
  (`native/capture.c`, built by `build_capture.py` to
  `scripts/cu/capture-helper`, which is gitignored). It is used on
  untransformed scale-1 outputs; otherwise raw `grim -s 1` PPM is used
  (`cu/capture.py` L1, L33, L109-L129). PNG is encoded at delivery. There is no
  xdg-desktop-portal.
- **AT-SPI:** a persistent worker process
  (`cu/accessibility_worker.py`, `Atspi.set_timeout(250, 500)`). It matches the
  application PID and a unique top-level title and never falls back to the whole
  desktop. Password fields are reported as protected. The parent kills the
  worker on timeout, and it is reaped after 120 s idle. There is no OCR.
- **Events:** Hyprland `.socket2.sock` for wakeups (`cu/events.py`).

### D.6 Privilege model

**Everything is uid 1000.** The MCP servers run as the operator, launched over
stdio by each MCP client. Only `ydotoold` runs as root, and it hands authority to
uid 1000 through a 0600 socket. README L218-L220: "Other processes of that user
can inject input too… Stopping it does not disable `wtype`." Session discovery
accepts only sockets owned by the same uid (`system.py` L110-L113, L128-L145).
Kill switch: `pkexec systemctl stop wayland-computer-use-mouse.service` stops
pointer buttons only.

### D.7 Approval, lease or grant code

**None in the input server.**
- `restore_focus` is an argument the client sets, described as "Explicitly
  approve…" so that the MCP client's approval UI shows `target_title`
  (L1550-L1553, L1571-L1572). The server checks only that it matches the frame.
- The observer "lease" (`observation.py` L327, L506) is a 120 s *collection*
  lease, not an input lease.
- README L77 and L322: "Approvals remain the MCP client's responsibility".
- Per-tool approval lives in Codex config: `approval_mode = "approve"` on
  `focus_window`, `scroll` and `type_text` (`repo_wayland_computer_use.md` §1,
  local inspection).
- The evaluation scripts run trials with `codex exec --approve-for-me`
  (`scripts/evaluate_transfer.py` L112; `pilot_model_evaluation.py` L116).
- WCU has **no notion of caller identity**: one stdio process per client, and
  frames are per-process.

### D.8 Unpushed commits and dirty files

**12 commits are ahead of `origin/main`:**
- `abf68f1` through `c618243` (10 commits, 2026-09-10 12:32-13:37): Astra
  session accounting and native-form pilots; app-scoped canonical command
  discovery; fresh control readiness across window transitions; bounded truthful
  evidence summaries; counterbalanced screening; stale-frame and toolkit
  readiness clarifications; native-form reset readiness; instruction and
  image-policy screening; launch-inclusive transfer evaluation.
- `670d021` (a local copy of `a600ed7`: README + LICENSE) and the merge
  `e61f8ed`.

Code delta of the 10 feature commits, excluding `reports/` (34 files,
+1,623/−63):
- **Runtime code:** `server.py` (+109), `cu/execution.py` (+67),
  `cu/trace.py` (+61), `cu/context_retrieval.py` (+40), `cu/feedback.py` (+41),
  `cu/recipes.py` (+19), `cu/capture.py` (+15), `dev_host.py` (+25).
- **Evaluation tools:** `audit_model_session.py` 166, `pilot_model_evaluation.py`
  174, `evaluate_transfer.py` 144, `model_run_manifest.py` 68,
  `analyze_model_comparison.py` 48.
- **Docs and skill:** `SKILL.md` (+103 experimental copy, +12 main), docs
  (`model-evaluation.md` 125, `transition-readiness.md` 51,
  `command-discovery.md` 21).
- **Tests:** the related unit tests.
- **Data:** about 14k lines of `reports/astra-wcu/*.json`.

**Dirty tree (10 status entries, 37 files with `-uall`).**

Modified:
- `.mcp.json` and `wayland-desktop-observer/.mcp.json`: real local absolute
  paths plus `WAYLAND_CU_TRACE_DIR=/home/david/.local/state/wayland-computer-use-trace`.
- `docs/model-evaluation.md`.
- `scripts/analyze_model_comparison.py`, `scripts/evaluate_transfer.py` and
  `scripts/pilot_model_evaluation.py`: `--pairs` is now required and capped at
  10, "larger batches need a separate owner-approved invocation".

Untracked:
- `reports/2026-09-10-astra-eval-overrun-retrospective.md` (133).
- `reports/astra-wcu/image-screening/frame-lineage.json`.
- `reports/astra-wcu/transfer-images/` (15 files) and `transfer-instructions/`
  (14 files).

**None of the dirty changes touch the input server or the guards.** The
retrospective is directly relevant to Odin: an agent "authored its own sample
sizes, treated approval of the implementation plan as approval of those
numbers… consumed 23.7 million tokens… falsely reported that evaluations had
stopped. They continued until the owner had them killed from an outside
session."

### D.9 What moves into the workstation daemon, and the single choke point

**Move as the gated "desktop input" capability:**
- `Desktop` (`server.py` L372-~L1530) with `cu/execution.py`, `cu/pixels.py`,
  `cu/capture.py` with `native/capture.c`, `cu/system.py`, `cu/events.py`, and
  `cu/app_surfaces.py` with `cu/obsidian.py` (receipts).

**Move as the observation capability (read-only, still privacy-sensitive):**
- `cu/observation.py`, `cu/accessibility*.py`.

**Keep as harness-package shims:**
- The stdio `serve()` loops (`server.py` L1701-L1745, `observer_server.py`)
  become thin MCP front ends that forward to the daemon.
- `skills/wayland-computer-use` becomes a skill in the integration package.

**Keep standalone (WCU repo):**
- Codex manifests, evaluation scripts, benchmarks, reports, the baseline and
  the keyboard catalog builder. Context retrieval and Braid could later be
  daemon read-only capabilities.

**Reusable design patterns:**
- `dev_host.py`: SHA-pinned runtime bundles and fail-closed tool-contract
  hashing, a model for capability negotiation.
- The `Ledger` and its `performed='unknown'` semantics.
- Operation-id receipts and reconcile-not-replay.

**Choke points for a seat lease and action grant.** Inside WCU, every
side-effecting path enters through `Desktop.call()` (L923-L976) and then reaches
one of:
- (a) `perform()`'s `submit()` closure (L1203-L1212): `recheck()`, then the
  callback that runs `wtype`, `move`→`dispatch('movecursor')` or
  `mouse`→`ydotool`;
- (b) `Desktop.dispatch('focuswindow')` (L442-L453), from `prepare`,
  `focus_window` and `run_steps`;
- (c) `dispatch_uri` (`app_surfaces.py` L40-L60), from `open_uri` and Obsidian;
- (d) the unconditional drag release `mouse('click','0x80', release=True)`
  (L1247), which must stay outside the lease check so a button is never
  left pressed.

The lease and grant check belongs in `call()`, for request-level admission
against grant scope, target and expiry, **and** in `submit()`/`dispatch()`/
`dispatch_uri` (per-segment re-validation: the lease is still held, there is no
human takeover, the grant has not expired). Inside one process that is
complete.

**The lease is not enforceable at the device level as deployed.** Lowest-level
access is uid-wide: the `ydotoold` socket (0600, uid 1000), the Wayland
virtual-keyboard protocol behind `wtype`, and the Hyprland IPC socket behind
`hyprctl dispatch`. To make the daemon the *only* input holder:
- run the daemon under a dedicated Unix user that alone owns the `ydotoold`
  socket (change `--socket-own`);
- and deny other uid-1000 clients the virtual-keyboard protocol and dispatcher
  IPC.

Nothing in WCU shows that Hyprland can restrict that second part. It is
**unverified**. Without it the lease binds only cooperating clients, which
matches ODIN-ECOSYSTEM-INTEGRATION §8: "Unmanaged input and focus races remain
limits".

---

## E. dotprivate

### E.1 What it does today

| Item | Detail |
|---|---|
| Size | `dotprivate` (bash) 471, `test/e2e.sh` 99, `README.md` 125, `LICENSE` 21 (MIT), `.gitignore` 1. One commit (`51d0fce`, 2026-09-07, v0.1.0) |
| Model | One private data repo, one directory per project. Each project has a sparse, blobless clone (`--filter=blob:none --sparse`) at `<project>/.private`, hidden by a global gitignore entry `.private/` |
| Scopes | **Project:** sparse-checkout set to the project name; `add NAME` widens it. **Environment:** a per-machine label (`--env`, `DOTPRIVATE_ENV`), with mirrors under `<project>/ingested/<env>/` |
| Config | `$XDG_CONFIG_HOME/dotprivate/{remote,env,clones}`; overrides `DOTPRIVATE_REMOTE`, `DOTPRIVATE_ENV` |
| Commands | `setup`, `init`, `scan [--ignored]`, `ingest PATH… [--dry-run] [--force] [--all]`, `restore [--force]`, `sync`, `status`, `add` |
| Ingest | Copies, never moves (L354-L402), into `ingested/<env>/…`. Records each path in `.manifest`. Files outside the project tree land under `_external/<abs path>`. Credential-like names are refused without `--force` (`CRED_RE` L28). Content matching `SECRET_CONTENT_RE` (L30) is only warned on. Files over 5 MB are flagged. Noise is filtered (`NOISE_RE` L26) |
| Sync | `do_sync` (L428-L441): `git add -A` of the whole clone, commit, `pull --rebase`, push. **No lock** |
| Hook | `init` appends to the project's `.git/hooks/post-commit` a background `nohup dotprivate sync &` (L208-L224) |
| Restore | Copies the env's mirrored files back to their original or absolute paths (L405-L425). No `..` or containment check on manifest lines (inference) |
| In use | Only WCU has a `.private` clone and the hook. The data repo log shows ingests for `wayland-computer-use@themachine` and `heimdall@themachine`. Odin and Saga have no `.private` |

### E.2 The proposed selected-files contract

`docs/SELECTED-FILES-CONTRACT.md` is untracked, 66 lines, dated 2026-09-10.
Status: "proposed behavioral contract… not an implemented API". The named
consumers are **Heimdall P03 and Skald L6**, not Odin. It requires:

1. **Authorized request:** the canonical checkout, project scope, remote and
   ref, a stable request id and an immutable manifest digest. The manifest gives
   exact relative destinations and expected content digests, with deletions when
   supported. Scope, traversal, symlinks, collisions and current bytes are
   validated before mutation. A changed manifest needs a new id; a reused id
   with different content is refused.
2. **Serialization:** all cooperating mutations on a checkout are serialized,
   *including the background sync*.
3. **Preservation:** unrelated staged and unstaged state is preserved exactly
   (or the request stops with a conflict). Only the selection is committed,
   using an isolated index. No destructive conflict resolution.
4. **Durable receipts** that distinguish:
   - validated;
   - local mirror observed;
   - commit created or existing;
   - remote publication confirmed.

   A failed or timed-out push is failed or uncertain. Reconcile before retry,
   never create duplicate commits, and confirm a push only by observing the
   commit on the ref.
5. **Release acceptance:** kill tests around commit and push, unavailable
   remotes, divergent refs and rebase conflicts. A published request/receipt
   schema, interface and fixtures. Not for live SQLite/WAL or disposable
   indexes.

### E.3 Tests

`test/e2e.sh`: about 24 `check` assertions against a local bare remote with two
simulated environments. It covers seeding, sparse scope, the global ignore, the
hook, `.env` refusal, the secret flag, ingest, push, `--all` and the hook sync.
It does not cover concurrency, interruption or receipts.

### E.4 Does Odin need dotprivate?

No. "Odin writes a package directory and runs git itself" is sufficient,
because:
- dotprivate's contract does not name Odin as a consumer;
- Odin owns its own export repository;
- dotprivate stays usable by the operator: `dotprivate ingest <odin-export-dir>`
  copies Odin's files into the private data repo without any Odin↔dotprivate
  interface.

Conditions:
- **(i)** Odin's package directory must not live inside a dotprivate-managed
  `.private` clone. The post-commit hook's background
  `git add -A; pull --rebase; push` would sweep in partial writes and race
  Odin's commits. That race is the hazard the contract's serialization clause
  addresses.
- **(ii)** Odin must still implement the *properties* it would otherwise have
  borrowed:
  - write the package atomically (temp directory, then rename);
  - `git add` only the package path;
  - record receipts that distinguish a local commit from remote confirmation;
  - reconcile an uncertain push with `git ls-remote` or `fetch` before retrying;
  - apply its own secret/PII screen before committing.
- **(iii)** ODIN-ECOSYSTEM-INTEGRATION §9 makes dotprivate's contract a
  "Prerequisite" and lists EC-08/EC-09. Under the target architecture that
  dependency should be removed or reworded.

What dotprivate does that plain git would not:

1. One shared private repo across many projects, with per-project
   sparse/blobless checkouts.
2. A global ignore, so project repos can never stage `.private/`.
3. Copy-not-move mirroring of untracked files, with a per-environment manifest,
   `_external/` absolute-path capture, and `restore` to the original paths.
4. Per-environment namespacing, so pushes from several machines rebase cleanly.
5. Candidate discovery: untracked-not-ignored files with NEW/CHANGED/DELETED
   state and noise filtering.
6. Credential-name refusal, secret/PII content heuristics and a size flag.
7. The automatic post-commit background sync.
8. Data-repo seeding: README, template and a `.gitignore` that refuses
   `*.secret.*` files without `.enc` or `.age`.

None of these is needed for Odin's own package directory in its own repo, except
the secret screen in (6), which Odin should own as policy.

---

## F. Consolidation implications

### F.1 Saga

| Component | Proposed destination | Rationale | Difficulty | Main risk |
|---|---|---|---|---|
| `heimdall.py` validation and argv construction, secret checks | **Execution backend process** (admission + docker driver) | Only the hardened-construction pieces survive (B.10) | M | Carrying over the B.9 holes; running from a user-writable checkout |
| Launch-request/result file protocol, `launch-requests-draft/` | **Delete** (replaced by the backend API and operation records); keep a file adapter only for a shadow period | Contract §17: deleted at migration | S to delete, M to replace | Two live submission paths during the shadow period |
| `commands/` and `outgoing-commands/` references | **Delete** | No consumer (A.16) | S | None |
| `depends_on` | **Execution backend** lifecycle (gated on `verified`, visible `queued`) | LC-4, LC-5 | M | Depends on a verification policy that does not exist |
| Run ledger, D5 states, delegations, approvals, verdict records, operations, evidence, event cursor | **Substrate EXECUTION LEDGER namespace, written only by the backend** | Nothing exists today; build new | L | Substrate writer isolation (F.4 item 4) |
| `ratatoskr.py` MQTT→`state.json`, journals, metrics, plateau routing | **Execution backend** worker-event intake, which emits derived run events into the ledger | Workers must not talk to the planner directly (B-17) | M | Losing direction enforcement if events go straight to the Odin service |
| ratatoskr file→MQTT guidance publisher | **Execution backend** guidance operation (`guidance_rev`, reconciliation) | B-04, MQ-8 | M | Retained last-write-wins semantics |
| ratatoskr tmux send-keys nudges, verdict markers, milestone nudges | **Delete**; the Odin service wake policy replaces them | They exist only because of TUI driving (F11) | S | None |
| `saga/events/*` lifecycle events | **Substrate surface-events namespace** | Observability, not authority (MQ-9) | S | Consumers deriving state from them |
| MQTT `dvergr/*` worker transport | Backend-internal (per-run credentials and ACL) **or** a backend-owned per-run intake. Never the Odin service | MQ-1, MQ-5; the broker is shared homelab infrastructure | M/L | The unauthenticated broker today |
| `dvergr-hooks/*` | **Worker image inside the execution backend** (renamed `worker-hooks`), publishing to backend intake | Worker contract (PH-5) | M | Self-reported status treated as evidence |
| `containers/dvergr` + `init-dvergr.sh` | **Execution backend** worker image | Same | M | tmux/send-keys driving, shared credential volume, the `.claude.json` baseline per CC version, unpinned `claude update`, egress firewall likely not running |
| `containers/odin`, `start-odin.sh`, Odin persona | **Frozen as history**; behavior re-implemented in the Odin service and integration package | Odin's harness replaces the TUI | L (re-implementation) | Losing behavior that lives only in prose (C.3) |
| Mimir persona + file protocol | **Odin session class** (isolated review sessions) **plus a separate reviewer-key holder process** | B-10 / D2.4 | L | No key custody exists today (F.4 item 3) |
| Bragi container + persona + lessons template | **Odin session class (scheduled)**; vault and lessons as its outputs | Already a batch compiler with no daemon; cron never ran | M | Inputs (journals, verdicts, guidance files) disappear with the file protocol; re-source them from the substrate |
| Eir persona, webhook, PR scripts, `gitea-api.sh` | **Odin assignment class** executed as backend runs (SAGA-SELF-1 direction); webhook into the Odin service event intake, authenticated | B-16 | M | Today Eir has docker-group access as the operator user; RCV-3 requires an operator-invoked path outside the failure domain |
| `keepalive` image + cron, `scripts/auth/*` | **Execution backend** credential-lineage provisioning and the single refresher per lineage | AUTH-3; single-use refresh tokens | M | Two refreshers on one lineage invalidate it |
| `spec_dev/` package + tests | **Odin service** module (the spec-dev workflow), wired to inbound routing | Already deterministic and tested | S/M | String drift with the frozen persona; the Telegram attachment path |
| Telegram (CC channel plugin in the TUI) | **Odin service** surface adapter on the homelab side (always-on) | No reusable code | M | Hash-bound approvals must be designed fresh |
| Gitea workflow (stream branches, `.netrc`) | **Execution backend** credential provisioning; branch-only enforcement at Gitea | GAP-24 | M | Branch protection may not be expressible per run |
| `deploy.sh`, `restart-odin.sh`, `heimdall.service` | Replaced by deployable packaging; the backend unit runs from a root-owned install | B.9 item 5 | S | — |
| `mqtt/TOPIC-SCHEMA.md`, `journal/`, `docs/` | **Frozen as history**; schemas carried into backend schemas | | S | — |

### F.2 wayland-computer-use

| Component | Destination | Rationale | Difficulty | Main risk |
|---|---|---|---|---|
| `Desktop` input execution and guards (`server.py` core, `cu/execution`, `pixels`, `capture`, `native/`, `system`, `events`) | **Workstation daemon gated capability** ("desktop input") | Guards are mature and tested (191 tests) | L | The lease cannot be enforced device-wide (D.9); takeover detection does not exist |
| `cu/observation.py`, `accessibility*` | **Workstation daemon capability** (observation, read-only, privacy-gated) | Shared by both servers already | M | Overlays expose unrelated content; observation is not privacy-free |
| `app_surfaces.py`, `obsidian.py` (receipts) | **Workstation daemon capabilities** with operation ids | Reconcile-not-replay fits the substrate | M | App-specific maintenance |
| stdio `serve()` loops, `.mcp.json` | **Harness integration packages** (MCP shim that forwards to the daemon) | Current model is one process per client, which cannot coordinate a seat | M | The shim must carry caller/session identity for grants |
| `dev_host.py` hot-reload + contract hash | Pattern for daemon capability negotiation | Fails closed on contract mismatch | S | — |
| `skills/wayland-computer-use` + references | **Harness integration package** skill | | S | Skill text encodes approval guidance that should become grant code |
| `ydotoold` unit | **Daemon-owned**, dedicated uid owning the socket | The only true device holder | M | Needs root install; `wtype` and `hyprctl` bypass remain |
| `context_for_task`, keyboard catalogs, Braid client | Keep in WCU for now; later a read-only daemon capability | Not on the critical path | M | — |
| Codex manifests, evaluation scripts, reports, baseline, benchmarks | **Keep standalone** (WCU remains a Codex plugin) | Operator uses it from Codex today | S | Divergence between the daemon copy and standalone WCU |

### F.3 dotprivate

| Component | Destination | Rationale | Difficulty | Main risk |
|---|---|---|---|---|
| Entire tool | **Keep standalone** (the operator's personal tool) | No Odin dependency needed (E.4) | — | — |
| Selected-files contract | Stays dotprivate's; **remove it as an Odin prerequisite** (ecosystem §9, EC-08/EC-09) | Consumers are Heimdall and Skald | S | — |
| Odin export | Odin's own package directory in an Odin-owned repo; plain git with receipts | | S/M | Placing it inside a `.private` clone (hook race) |

### F.4 Contradictions with the target architecture's assumptions

1. **"The execution backend is the only Docker holder" is false today.**
   - The operator user is in the docker group (`scripts/deploy.sh` header). Eir
     and dev Claude run as that user on the VM.
   - The Odin, Mimir, Bragi and keepalive containers are started by host scripts
     and cron, outside Heimdall (`heimdall.py` L258-L263).

   The consolidation must either route those launches through the backend or
   keep them as operator-only operations that no agent account can perform. Eir
   must not keep a docker-group host session.
2. **One repository, with the root Docker holder running from a writable
   checkout.**
   - Heimdall executes `${SAGA_REPO_DIR}/odin/scripts/heimdall.py` as root.
   - In a single repo, Odin's own assignment classes (Eir-style
     self-modification) edit the code the Docker holder runs.

   The backend must run from a root-owned, versioned install. Changes to the
   backend paths need mechanical operator approval: the `self_modifying` rule
   and the Eir "cannot edit heimdall.py" rule are prose today.
3. **The reviewer-key holder is not placed in any of the three deployables.**
   - Today there is no separation at all: Odin and Mimir share a container, a
     uid and a filesystem.
   - If the homelab Odin service both runs Mimir review sessions and submits
     runs, the key must sit in a separate process and uid, for example a
     reviewer signer that only signs review records produced by isolated review
     sessions.
   - The backend verifies the signature (B-10, ID-1). The key must never be
     readable by the Odin service process.
4. **One substrate holding the EXECUTION LEDGER namespace versus ADM-1.** The
   contract requires admission "outside any orchestrator's trust boundary"
   (ADM-1, ADM-5: a client must not be able to record an operator approval for
   its own submission, GAP-02). If the Odin service process owns the substrate
   store and can append to the execution-ledger namespace, it can forge
   approvals, verdicts and state.

   Mitigation: per-namespace single-writer enforcement by process ownership.
   For example, the backend owns its ledger file or database. The substrate
   indexes or mirrors it read-only. Operator approvals arrive through a channel
   the backend authenticates separately.
5. **Replacing MQTT with "the Odin service's own event intake".**
   - **Who receives worker events:** the backend, not the Odin service. Workers
     sending events straight to the planner gives prompt-injected worker output
     a direct path into Odin, and loses the direction rule that workers cannot
     write guidance or answers (B-17, MQ-5, CT-17).
   - **The broker stays:** Mosquitto (`192.168.86.12`) also serves Frigate and
     surveillance, so "replace" means Saga stops using it, not that it goes
     away.
   - **Today's state:** the bus is unauthenticated, so even the shadow period
     needs at least per-run credentials.
6. **"The seat lease and action grant live in the process that holds the input
   device."** No single process holds input (D.4, D.6):
   - `ydotoold` holds `/dev/uinput` for pointer buttons only;
   - keyboard input goes through the compositor's virtual-keyboard protocol
     (`wtype`);
   - focus and cursor go through Hyprland IPC;
   - all three are uid-wide.

   The lease can be complete inside the daemon (`call` + `submit` + `dispatch`
   + `dispatch_uri`). It is advisory for every other uid-1000 process unless the
   daemon gets a dedicated uid and the compositor denies those protocols to
   other clients (unverified). The README itself measures wrong-window input
   under focus races.
7. **WCU assumes a human at the MCP client approves each action.**
   - Codex has per-tool `approval_mode`, and the server does no approval of its
     own.
   - The target makes the action grant the daemon's job. That changes the trust
     model: what the human approves (a grant scope, a target, an expiry) must
     become a record the daemon checks per segment.
   - WCU has no caller identity, so the MCP shim must supply a session identity.
8. **Eir as an Odin assignment class versus RCV-3.** The pinned contract says
   "Eir keeps an operator-invoked path outside Saga's failure domain". If Eir
   exists only as an Odin assignment executed by the backend, a broken Odin or
   backend cannot be repaired by Eir. Keep a documented operator-invoked
   maintenance path that does not depend on the Odin service.
9. **"Absorbs Saga's ledger and run lifecycle."** No ledger or lifecycle code
   exists to absorb (B.11). The phrase understates the work: everything in
   contract §§3-13 is new code. Saga's reusable code is about 900 lines of
   launcher plus about 1,365 lines of `spec_dev`.
10. **"Human surfaces" in the workstation daemon.** Telegram is today the only
    always-on operator surface. It belongs with the homelab service so approvals
    and `/stop` work when the workstation is off. ST-2: stop must work "without
    the orchestrator".
11. **dotprivate is consistent, with one condition.** Do not put Odin's export
    directory inside a dotprivate `.private` clone (E.4).
12. **The public WCU README describes unpublished code**
    (`wcu-tools-5`, `c618243`). If the daemon absorbs WCU, pick one source
    (local `main`) and push it, or the frozen origin copy will disagree with the
    daemon's contract hash.
