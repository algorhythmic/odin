# CLAUDE.md — Saga

## Project overview

Saga is a governed execution service for long-running agent work on the
operator's homelab; Odin is the orchestration agent that drives it. The
code in this repo is the April 2026 implementation; the target design
is decided in `docs/DECISIONS.md` (wins over every other document where
they conflict) and specified in `docs/design/`. Read those two before
`docs/saga-spec.md`, which is the April design spec with a supersession
banner.

## Terminology

Norse names are used only for agents that carry a persona and make
judgments. Everything deterministic gets a plain functional name,
prefixed `saga-` when it is a deliverable. Never reuse a name used by
one of the operator's standalone repos (heimdall, braid, skald, muninn,
wayland-computer-use). Mythological places and metaphors appear only
in Odin's identity paragraph.

| Term | Meaning | Legacy name |
|---|---|---|
| **Odin** | The orchestration agent (Opus): ingests specs, decomposes, delegates, guides, retrospects. Runs on its own harness (target) or an interactive Claude Code session (today). | — |
| **Mimir** | The reviewer agent. Reviews decisions where mistakes multiply (decompositions, shared-interface changes, material guidance changes, Eir patches, principle changes) from original evidence, never from Odin's reasoning; verdicts are written under its own identity key. Sonnet by default, a stronger model per review type when evaluation shows it is needed. | — |
| **Delegation** | An ongoing responsibility the operator has delegated: outcome and scope, authority, limits, evidence, escalation, expiry and stop conditions; versioned, kept in Saga's ledger, scoped over projects and runs. | — |
| **Evaluator** | A harness-owned, versioned decision (System One model) at a registered hook location, with fixed configuration, shadow mode before activation, and no authority. | — |
| **Worker** | One agent runtime in one container executing one run of one stream. Today Claude Code with `/ralph-loop`. | dvergr, dvergar |
| **Run** | One execution attempt of a stream by a worker; has a durable id and a state (`submitted`, `accepted`, `queued`, `started`, `terminated`, `verified` or `failed`, `closed`). | instance |
| **Stream** | One decomposed unit of a project's work, with its own PRD and branch. | work stream |
| **Saga launcher** | Host daemon that validates launch requests and runs Docker. The security boundary between agents and the Docker socket. Target: the launcher module of the Saga service, where approvals and limits are enforced. | Heimdall, `heimdall.py` |
| **Saga events** | Bridges worker MQTT traffic to the ledger and to Odin. Today a sidecar in Odin's container; target: the events module of the Saga service plus the Saga adapter in Odin. | Ratatoskr, `ratatoskr.py` |
| **Saga service** | Target: the daemon that owns the run ledger, the API, the launcher, events and policy. | — |
| **Bragi** | Compiler agent (Sonnet): vault, lessons store, guidance effectiveness. | "skald" (drop; name of a standalone repo) |
| **Eir** | Healer agent (Sonnet): findings become reviewed pull requests. | — |
| **Operator** | The human running Saga, over Telegram. | — |
| **Spec, PRD, contract, guidance, principles** | Unchanged meanings: the operator's specification; a per-stream requirements document; a byte-identical schema or interface carried into PRDs; Odin's steering messages to workers; Odin's evolved, gated rules. | — |

**Do not use** as alternative agent names: overseer, navigator, critic,
judge, master. "worker" and "run" are the official terms. Legacy names
remain in `docs/history/` and in code until each rename lands
(`DECISIONS.md` D13 has the full mapping). In prose, say "Saga's
launcher", never bare "Heimdall", and "Bragi", never "skald".

## Where dev Claude runs

Two places, by task. **Deployment and fleet work** runs on the Docker
host VM (192.168.86.17, `tmux new -s saga-dev`, checkout at
`/home/david/src/saga`), which has `docker`, `journalctl -u heimdall`,
container filesystems and Gitea at hand. **Design and documentation
work** runs on the operator's Omarchy desktop checkout at
`~/Projects/saga`, which has no Docker and cannot see the VM's state;
never assume the fleet is running from there.

### Auth boundaries (do not cross-wire credentials)

- **Dev Claude** reads `/home/david/.claude/.credentials.json` on
  whichever machine it runs on.
- **Saga agents** (Odin, Mimir, workers, keepalive) read the
  `saga-claude-credentials` Docker volume mounted at
  `/home/vscode/.claude` inside each container.
- **Odin's harness (target)** authenticates per `DECISIONS.md` D24: by
  default an API key from the Console organization linked to the Max
  plan, stored as a Saga-managed secret; alternatively its own
  subscription login lineage. Never the workers' shared credentials
  file. Workers get their own credential lineage each (a one-year
  `setup-token` once the re-test confirms it, or their own login), with
  one refresher per lineage; the shared writable volume is the
  shadow-period mechanism only.

Keep them separate; auth failures must be attributable. Claude Code
refresh tokens are single-use, so only one process may refresh a given
credentials file (`DECISIONS.md`, harness assessment pattern 7).

### Blast radius and guardrails

Dev Claude on the VM can destroy agent state with one command. If an
action touches shared agent infrastructure, state the intent and wait
for explicit approval. Never without explicit confirmation:

- `docker volume rm saga-claude-credentials`
- `docker stop` / `docker kill` any running `saga-*` container that
  was not just requested
- `docker rm -f`, `docker system prune`, `docker image prune -a`
- `git push --force` to any Saga repo on Gitea
- `rm -rf` or `rm -f` anywhere under `/opt/saga/`
- `iptables` changes on the host
- `systemctl stop heimdall` (the launcher)
- editing `/opt/saga/secrets/*`

Local, throwaway operations (files under `/tmp`, branches other than
main, directories the operator said you can use) need no pre-approval.

## Critical constraints

### What is permitted, and what Saga relies on

1. **Agents never get the Docker socket.** The launcher is the only
   thing that starts containers. In the target design it also enforces
   approvals (by hash of the approved PRD and launch configuration,
   bound verdict and operator authorization) and limits, for every
   client. Do not add paths around it.
2. **Permitted auth shapes.** Anthropic's Claude Code legal page permits
   running the unmodified Claude Code binary in hosted sandboxes where
   each user signs in with their own subscription; that is the workers'
   and today's Odin's shape (credentials volume, interactive `/login`
   once, `.claude.json` baseline baked into the image). Odin's target
   runtime is Claude Code through the Agent SDK; authentication and
   billing mode are per-adapter configuration (`DECISIONS.md` D24):
   the default for planning sessions is an API key from a Console
   organization linked to the Max plan, and a subscription login
   lineage through the SDK is supported and draws on plan limits (Help
   Center, 2026-10-07). Max 5x and 20x include
   $100 and $200 a month of API credits that cover the SDK (claim once from claude.ai
   Settings, Billing, "API credits"; the Console's "spend this month"
   figure is a spend cap, not a balance).
3. **Not permitted for Claude work:** third-party harnesses pointed at
   the subscription (Hermes, Pi, oh-my-pi, OpenCode). Pi and oh-my-pi
   impersonate the Claude Code client; OpenCode removed its Claude plan
   auth under legal pressure. Claude workers on any non-Anthropic
   harness must use an API key.
4. **`.claude.json` is a sibling of the credentials volume.** Five
   first-run dialogs (theme, sign-in method, bypass permissions,
   workspace trust, effort) block unattended interactive launch; the
   baseline at `containers/dvergr/claude-baseline.json` is copied in at
   container start and regenerated per Claude Code version. Headless
   (`-p`) and SDK runs do not show these dialogs; verify before relying
   on that.

### Under re-test (April 2026 findings, not yet overturned)

The April 10 tests concluded that `claude -p` and `CLAUDE_CODE_OAUTH_TOKEN`
force API billing. Anthropic's Help Center (update 2026-10-07) says
`claude -p` and the Agent SDK draw on subscription limits, and the
issue cited in earlier versions of this file (#16238) is about
precedence warnings, not the 401. The April result coincides with a
known bug window (claude-code #43333, April 4 to 8) and a known
truncated-token bug (#65320). Until re-tested on the current CLI with
the volume-mounted `.credentials.json` and no auth env vars, workers
stay interactive. Record the re-test result here when done, with the
CLI version. Note that `--bare` will become the `-p` default in a
future release and never reads subscription credentials. The comments
in `init-dvergr.sh`, `start-odin.sh`, `heimdall.py` and the auth
scripts that state the April findings as rules stay as historical
findings until the re-test resolves them; do not edit them before it.

### The launcher's known defects (fix in Phase B, do not work around)

- Nothing consumes `commands/` or `outgoing-commands/`; `stop` and
  `restart` are launch requests with an `action` field.
- `depends_on` counts a crashed prerequisite as satisfied because
  containers run with `--rm`.
- A request held on `depends_on` gets no result file for up to 24 h.
- A reused request id overwrites its result file.
- `approved` means `docker run` returned 0, nothing more.

## Dependency decisions

| Decision | Rationale |
|---|---|
| Official `/ralph-loop` plugin for workers today; `/goal` or a deterministic gate plus judge next | The plugin runs inside interactive sessions; its exact-match promise has open detection bugs and an unlimited default, so the plateau hooks are the second signal. frankbria's external loop was rejected on the old billing rule and is not needed. |
| Trail of Bits devcontainer as the worker base | Explicit threat model, optional iptables firewall, no Docker socket; built locally from a pinned commit (no public image). |
| MQTT (Mosquitto at `.12`) as Saga's internal worker transport | Already in the homelab, bidirectional, retained topics, shared with the surveillance system under separate prefixes. It is Saga's dependency, not Odin's: Odin reaches Saga through the service API. |
| Mimir as a separate agent with no shared context | Cross-model audit of planner decisions, the restraint-biased `APPROVE_UNCHANGED` verdict. Today an interactive session with file handoff; target: a second agent on Odin's harness with its own chat. |
| Claude Code through the Agent SDK as Odin's execution harness | Odin is a supervisory layer: the service owns commitments, memory, events, wake policy, session lifecycle and review coordination; the harness owns reasoning and tools within a session. A custom Messages API runtime only if measured requirements force it (`DECISIONS.md` D7, D19). |
| UniiChat's ideas for Odin's memory | One append-only log that is also the inbox, a 512-byte summary tree, a bounded briefing, `zoom`; adapted to the harness boundary (no fresh call per message, no promised cache economics). A hypothesis judged against a simpler baseline (D7). Design attributed to Victor Taelin's gist, which shows no license. |
| Standalone tools stay separate | braid as `recall` backend; skald as optional archiver and the `archive` recall scope; muninn as optional knowledge scope; wayland-computer-use only for a dedicated computer-use worker under a delegation naming desktop authority, with a seat lease (D21); standalone heimdall never an authority, optionally a human-facing continuity view referencing Odin's commitments (D20); Herdr as the terminal workspace for inspection (`DECISIONS.md` D10, D20, D21). |

## Explored and rejected

| Option | Why |
|---|---|
| frankbria/ralph-claude-code, Praktor, Phantom, OpenClaw | Earlier rejections rested on `claude -p` or SDK billing; that rule is under re-test. They remain unneeded: the official loop plus plateau hooks, and Odin's own harness, cover their roles. |
| Third-party harnesses on the subscription (Hermes, Pi, oh-my-pi, OpenCode) | Prohibited or impersonating; see constraint 3. |
| Custom Messages API loop as Odin's default runtime | Couples the extraction to one memory implementation's inference layout; reconsidered only if the D18 measures show the Agent SDK route cannot meet memory or cost requirements. |
| Interactive Claude Code session in tmux as Odin's runtime | A TUI driven as a daemon (dropped keystrokes, dialogs, no event injection). The shadow-period bridge only. |
| Claude Code agent teams for Odin + workers | Same machine only, file mailboxes, no `-p`; conflicts with per-container isolation. |
| Standalone heimdall as the authority for accepted task state | Desktop tool, unreleased, CI red, explicitly rejects Saga coupling; a second source of truth for approvals. Reference only. |
| Baking credentials into images; `docker commit` after `/login` | Leaks into layers and pushes. |
| Full rack servers, Mac Mini M4 | Noise, power, no Proxmox or Coral support. |

## Dependencies

| Dependency | Why | Pin |
|---|---|---|
| Trail of Bits devcontainer | Worker base image | git commit in `VERSIONS` |
| Claude Code CLI | Worker runtime, today's Odin and Mimir | installed by the base Dockerfile via `install.sh` |
| `/ralph-loop` plugin | Worker loop | `claude-plugins-official` marketplace |
| `claude-baseline.json` | Dismissed first-run dialogs for interactive containers | regenerated per Claude Code version |
| mosquitto-clients, paho-mqtt | Worker hooks and Saga events | Debian package, pip |
| `claude-agent-sdk` (Python) | Odin's runtime adapter over Claude Code (Phase C) | pip; bundles its own Claude Code binary |
| tmux | Interactive sessions in containers (today) | Debian package |
| braid (optional) | `recall` backend, child process over stdio | git tag |

## Homelab context

Lenovo ThinkCentre M75s Gen 2, Ryzen 5 PRO 5650G, 32 GB RAM, 1 TB NVMe,
Proxmox VE 9.x.

| IP | Service |
|---|---|
| 192.168.86.1 | Google Nest router |
| 192.168.86.10 | Proxmox host |
| 192.168.86.11 | Pi-hole (DNS) |
| 192.168.86.12 | Mosquitto (MQTT) |
| 192.168.86.13 | Home Assistant |
| 192.168.86.14 | Frigate (NVR) |
| 192.168.86.15 | Grafana + InfluxDB |
| 192.168.86.16 | Uptime Kuma |
| 192.168.86.17 | Docker host VM (Saga) |
| 192.168.86.18 | Gitea |
| 192.168.86.19 | Qdrant (muninn) |

Static IPs `.10` to `.19` are used; the DHCP pool is `.20` to `.250`.
Remote access over Tailscale. Mullvad VPN must be off for OAuth logins.

## Related projects

The operator's standalone repos in `~/Projects/` are not Saga
components: heimdall (desktop task-and-continuity daemon), braid
(retrieval), skald (transcript archive), muninn (personal wiki and
bookmark pipeline), wayland-computer-use (desktop control, usable only
under `DECISIONS.md` D21), and Herdr (the terminal workspace Odin's
operator interface builds on, not reviewed here). Reviews are in
`docs/design/harness-research-2026-10/repo_*.md`. The ESP32
surveillance system shares the MQTT broker under `surveillance/#`.

## Build order

`docs/DECISIONS.md` D15: Phase A (documentation, credits, billing
re-test, confirm Saga active), B (Saga service v1, launcher fixes, and
the minimum enforcement: approval and verdict binding, reviewer
identity, cancellation, concurrency cap, stop operations, kill switch),
C (Odin v1 in its own repo over the Agent SDK, with workspace
inspection), D (richer policy: TTL, budgets, presence gate,
verification policies, connector boundaries; second project, adopt and
take-control), E (worker contract, Codex worker, the second Odin
runtime adapter), F (recall, decision tool, archiver, preservation,
Bragi, observability), G (evaluation and demonstration).
`docs/ROADMAP.md` tracks what is in flight. Do not start C before B's
API and minimum enforcement exist.

## File structure

```
saga/
├── README.md                       ← front door
├── CLAUDE.md                       ← this file
├── CHANGELOG.md                    ← progress and bugs
├── VERSIONS                        ← pins
├── containers/
│   ├── odin/                       ← today's Odin + Mimir + events container (moves to the odin repo in Phase C)
│   ├── dvergr/                     ← worker image (renamed worker-claude in Phase B)
│   ├── bragi/
│   └── keepalive/
├── odin/
│   ├── CLAUDE.md                   ← Odin's persona (shrinks in Phase C)
│   ├── mimir/CLAUDE.md             ← Mimir's persona
│   └── scripts/                    ← heimdall.py (launcher), ratatoskr.py (events), start-odin.sh, spec_dev/
├── eir/CLAUDE.md, bragi/CLAUDE.md  ← personas
├── dvergr-hooks/                   ← worker hooks (renamed worker-hooks in Phase B)
├── scripts/                        ← auth, deploy, systemd, Eir webhook
├── mqtt/TOPIC-SCHEMA.md            ← topics (renamed to saga/runs/… in Phase B)
├── journal/                        ← journal formats
└── docs/
    ├── DECISIONS.md                ← the decision record
    ├── design/                     ← Odin I/O contract, harness landscape, research notes
    ├── saga-spec.md                ← April 2026 design spec (banner)
    ├── ROADMAP.md
    ├── architecture/, agents/, features/, history/
```

## Rules for new code and docs

- New components, directories, images, topics and tools get functional
  names; the legacy mapping is in `DECISIONS.md` D13.
- Every machine-read file is validated JSON or YAML with a schema;
  Markdown is for prose.
- Every behavioural rule for an agent should be paired with the check
  that enforces it, or a ticket for one.
- Say "Saga's launcher" in prose; reserve "Heimdall" for the legacy
  file name and the operator's standalone repo.
