# Saga

<p align="center">
  <img src="docs/images/saga-banner.jpg" alt="Saga banner" width="900">
</p>

**Odin is a personal agent for running long-term technical projects.
It maintains context across interruptions, coordinates specialist
workers, and brings back evidence and decisions within authority you
explicitly delegate. Saga executes that delegated work with durable
state, enforced permissions, resource limits and recorded outcomes.**

State and execution run on your own hardware; inference is hosted. The
intended user is one technically capable person managing several
software, research or infrastructure projects. What Odin competes on is
what it can be trusted to own over time: explicit delegation,
verifiable outcomes, inspectable history, and reviewed changes to its
own working methods.

You hand Odin a spec over Telegram. Odin compiles it into a project
wiki with verbatim contracts, proposes a decomposition into parallel
streams, gets a second-model audit from Mimir, and asks you to approve.
Saga then starts one isolated worker per stream, records every run's
state and evidence, enforces the limits you set, and streams events back
to Odin, who guides the workers, tells you only what needs your
judgment, and remembers what it learned across projects.

> **Status (2026-10-14).** The code in this repository is the April 2026
> implementation (Phases 1 to 3, one real project run). The direction
> was reset on 2026-10-14; the decisions are in
> [`docs/DECISIONS.md`](docs/DECISIONS.md) and the design documents in
> [`docs/design/`](docs/design/). Code and deployment scripts still use
> the legacy names listed below until each rename lands.

## Two products, one boundary

| Product | What it is | What it owns |
|---|---|---|
| **Odin** (planned as its own repo) | A supervisory layer over Claude Code's execution harness: a service that keeps commitments, memory (an append-only log with hierarchical summaries and `zoom`), queued events, budgets and session records alive between sessions, plus the tools, hooks and skills that make a Claude Code session operate as Odin. Hosts Odin and Mimir review sessions. | Persistent commitments and memory, attention, session lifecycle, delegation coordination, selective review, outcome verification. Reasoning and tools within a session belong to the harness. |
| **Saga** (this repo) | A governed execution service: starts workers in isolated containers, keeps the authoritative run ledger, enforces approvals and limits at the execution boundary, survives failures, exposes an API any orchestrator can use. | Runs, workers, worker images and hooks, policy, events, Bragi, Eir, deployment. |

Odin reaches Saga only through tools backed by the independently
running Saga service. A lost connection does not lose a run; restarting
Odin does not restart workers; a retried submission does not launch a
duplicate. Two things are pluggable, under two separate contracts:
the orchestrator (the Saga API) and the worker harness (per image).

## Components

Norse names are kept only for agents that carry a persona and make
judgments. Everything deterministic has a plain name. Legacy names in
parentheses still appear in code and older docs.

| Component | Kind | Role |
|---|---|---|
| **Odin** | agent (Opus) | Orchestrates: ingests specs, decomposes, delegates, guides, retrospects. |
| **Mimir** | agent (Sonnet by default) | Reviews the decisions where mistakes multiply (a decomposition before workers start, shared-interface changes, guidance that changes an approach, Eir patches, principle changes) from original evidence with no shared context; routine operations get mechanical checks, not model review. |
| **Workers** (dvergar) | agent runtime per container | One per stream and run; today Claude Code with the `/ralph-loop` plugin, bounded by an iteration cap. Codex CLI and API-key or local-model harnesses are added by the worker contract. |
| **Saga launcher** (Heimdall, `heimdall.py`) | host daemon | Validates launch requests against hardcoded rules and runs Docker. The security boundary between agents and the Docker socket. Becomes the launcher module of the Saga service. |
| **Saga events** (Ratatoskr, `ratatoskr.py`) | sidecar | Bridges MQTT and the filesystem today; becomes the events module of the Saga service plus the Saga adapter inside Odin. |
| **Bragi** | agent (Sonnet) | Compiles journals, verdicts and guidance into an Obsidian vault and a cross-project lessons store. |
| **Eir** | agent (Sonnet) | Turns findings into reviewed pull requests; never deploys. |
| **Operator** | you | Approves decompositions, principle changes and merges; from the terminal workspace at the desk and from Telegram when away, both through one recorded command path. |

## What exists today

- Spec ingestion by conversation (`/spec-dev …`) into a project wiki
  with byte-identical contracts; decomposition into independent,
  competitive or hybrid streams; Mimir review on every PRD.
- One worker container per stream, publishing status, journal entries
  and plateau signals (convergence, commit plateau, completion likely)
  over MQTT; guidance back by retained topic.
- A launcher daemon with image allowlists, secret mounting, Gitea
  credentials and dependency ordering.
- Eir's PR pipeline with a Gitea webhook and Mimir's `patch_review`
  checklist; the operator merges.
- A credentials-volume pattern that gives every container the
  operator's own subscription login, which Anthropic's hosting clause
  explicitly permits for the unmodified Claude Code binary.

## What is decided and next

From [`docs/DECISIONS.md`](docs/DECISIONS.md):

1. **A** now: documentation reset; claim the Max plan's included API
   credits; re-test the April billing findings on the current CLI;
   confirm Saga is active again.
2. **B** Saga service v1: run ledger and delegation records, local API
   with a client library, the run state machine (submitted, accepted,
   queued, started, terminated, verified or failed, closed), launcher
   fixes, dead `commands/` channel removed, renames applied, and the
   **minimum enforcement**: approval and verdict binding by hash,
   reviewer-identity verification, cancellation, a concurrency cap,
   the stop operations and the kill switch.
3. **C** Odin v1 in its own repo: the service plus a Claude Code
   integration package over the Agent SDK, memory adapted from Victor
   Taelin's UniiChat design, Mimir as isolated review sessions.
4. **D** Richer policy in Saga: container TTL, budgets, the
   operator-presence gate, verification policies per project type,
   action-authority boundaries for any new connector; a second project
   with adopt-into-supervision and take-control.
5. **E** Worker contract and a Codex CLI worker image.
6. **F** Retrieval (`recall`), the decision-model tool, archiving,
   Bragi on the new inputs, observability.

## Constraints that shape the design

- **Agents never touch the Docker socket.** Saga's launcher is the only
  thing that starts containers, and in the target design it is also
  where approvals and limits are enforced, for every client.
- **Auth shapes that are permitted:** the unmodified Claude Code binary
  signed in with the operator's own subscription inside Saga's
  containers; an API key from a Console organization linked to the Max
  plan for Odin's planning sessions by default (covered by the plan's
  included credits), or a subscription login lineage of their own.
  Authentication and billing mode are explicit configuration per
  runtime, not a property of Odin. Third-party harnesses pointed at the
  subscription are not used for Claude work. The promise is
  subscription-first with bounded, configured API spending, not "no API
  costs".
- **Under re-test, not yet relied on:** the April 2026 findings that
  `claude -p` and `CLAUDE_CODE_OAUTH_TOKEN` force API billing. See
  `CLAUDE.md`.
- **One writer of refresh tokens.** Claude Code refresh tokens are
  single-use; many containers refreshing one shared credentials file
  invalidate each other.
- **Mechanical enforcement compounds; cultural enforcement decays.**
  Every behavioural rule the agents are asked to follow is on its way
  to becoming a check in code.

## Quickstart (current implementation)

Assumes a Proxmox host, a Debian 13 VM at 192.168.86.17 and a Gitea LXC
at 192.168.86.18. Commands use the legacy names the scripts still have.
See [`docs/architecture/SETUP.md`](docs/architecture/SETUP.md) for the
full setup.

```bash
# SSH to the Docker host VM
ssh david@192.168.86.17

# Clone the repo (keep two checkouts: one for dev Claude, one mounted into Odin)
git clone <repo-url> ~/saga-dev      # where you edit
git clone <repo-url> ~/src/saga      # mounted RO into the saga-odin container
cd ~/saga-dev

# One-time: build the devcontainer base + populate the credentials volume
scripts/auth/bootstrap-credentials.sh --build
# (walks you through /login in a throwaway container; ~5 minutes human attention)

# One-time: create the Gitea push secret so workers can push their stream branches
sudo mkdir -p /opt/saga/secrets/gitea
sudo tee /opt/saga/secrets/gitea/saga-push >/dev/null <<EOF
machine 192.168.86.18
login <gitea-username>
password <gitea-token>
protocol http
port 3000
EOF
sudo chmod 600 /opt/saga/secrets/gitea/saga-push

# Build agent images
docker build -f containers/dvergr/Dockerfile -t saga-dvergr:latest .
docker build -f containers/odin/Dockerfile   -t saga-odin:latest   .

# Install the eir-webhook systemd service (handles Gitea PR-opened events)
sudo cp scripts/systemd/eir-webhook.service /etc/systemd/system/
sudo systemctl enable --now eir-webhook
# Then in Gitea: Settings → Webhooks → add http://192.168.86.17:9876/webhook
# (requires ALLOWED_HOST_LIST = private under [webhook] in app.ini)

# Smoke test: launch a single worker against a trivial PRD
mkdir -p /opt/saga/workspaces/smoke/instance-1
echo "# Write /workspace/done.txt with 'ok' and stop" \
  > /opt/saga/workspaces/smoke/instance-1/PRD.md
scripts/auth/launch-dvergr-template.sh smoke instance-1 \
  /opt/saga/workspaces/smoke/instance-1

# Watch MQTT traffic in another terminal
mosquitto_sub -h 192.168.86.12 -t 'dvergr/#' -v
```

## Documentation

[`docs/README.md`](docs/README.md) is the index. Start here:

| Document | Purpose |
|---|---|
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | The decision record: products, boundary, enforcement, ledgers, run states, naming, sequencing. Wins over everything below where they conflict. |
| [`docs/design/ODIN-IO-CONTRACT.md`](docs/design/ODIN-IO-CONTRACT.md) | What Odin perceives, does and remembers; the UniiChat memory design; tools; peer interfaces. |
| [`docs/design/HARNESS-LANDSCAPE-2026-10.md`](docs/design/HARNESS-LANDSCAPE-2026-10.md) | The October 2026 harness landscape and why the boundary was drawn this way. |
| [`CLAUDE.md`](CLAUDE.md) | Guardrails for agents working on this repo: terminology, auth, blast radius. |
| [`docs/saga-spec.md`](docs/saga-spec.md) | The April 2026 design spec, kept as the record of the original design with a supersession banner. |
| [`docs/architecture/`](docs/architecture/) | Current deployment, setup, homelab integration, observability, generalization. |
| [`docs/features/`](docs/features/), [`docs/agents/`](docs/agents/), [`docs/history/`](docs/history/) | Feature designs, Eir's design and backlog, retrospectives and insights. |

## Homelab context

Saga runs on a Lenovo ThinkCentre M75s Gen 2 (Ryzen 5 PRO 5650G, 32 GB
RAM, 1 TB NVMe) under Proxmox VE 9, beside Pi-hole (`.11`), Mosquitto
(`.12`, shared with the ESP32 surveillance system), Home Assistant
(`.13`), Frigate (`.14`), Grafana and InfluxDB (`.15`), Uptime Kuma
(`.16`), the Docker host VM (`.17`) and Gitea (`.18`). Remote access is
over Tailscale. See
[`docs/architecture/HOMELAB-INTEGRATION.md`](docs/architecture/HOMELAB-INTEGRATION.md).

## Related projects

The operator's standalone tools share names with Saga components but
are not Saga components; each plugs into Odin through a tool or
adapter, or stays out by design (see `DECISIONS.md` D10):

- **heimdall** — a desktop task-and-continuity daemon; not the Saga
  launcher, and not in Saga's loop.
- **braid** — a byte-budgeted retrieval engine; the backend for Odin's
  optional `recall` tool.
- **skald** — a transcript archiver with no model calls; an optional
  archiver of Odin's chat log. Not Bragi.
- **muninn** — the Phase 3 bookmark pipeline, redefined as a personal
  wiki; an optional `recall` scope.
- **wayland-computer-use** — a Hyprland desktop-control MCP server;
  deliberately unreachable from Odin and the workers.

Also on the homelab: the ESP32 surveillance system (`surveillance/#` on
the same broker) and Nexus, a prediction-market data pipeline.

## Contributing

If you are an AI coding assistant working on this repo, read
[`CLAUDE.md`](CLAUDE.md) first. If you are a human contributor, read
[`docs/DECISIONS.md`](docs/DECISIONS.md) before opening pull requests
against the launcher, the events bridge, or the personas.

## License

See [`LICENSE`](LICENSE).
