# Odin

**Odin is a personal agent for running long-term technical projects. It
maintains context across interruptions, coordinates specialist workers,
and brings back evidence and decisions within authority you explicitly
delegate.**

Odin turns agent sessions into persistent, supervised work across
projects, using the harness the operator already prefers. It is a
supervisory layer, not a new agent harness. An Odin **service**, written
as ordinary code, keeps commitments, memory, queued events, wake policy,
budgets, session records, the scheduler and the outbox alive between
sessions. A **harness integration package** (tools, hooks, skills,
instructions) makes a Claude Code session, driven through the Agent SDK,
operate as Odin. Reasoning and tool use within a session belong to the
harness. The service runs on the homelab; a **workstation daemon** on the
operator's machine hosts local sessions, sensors, transcript capture and
the local operator surfaces, acting only on the service's command
([ODIN-ADR-009](docs/DECISIONS.md#odin-adr-009--workstation-daemon-and-session-host),
ODIN-ADR-010).

Execution with external effects goes through
[Saga](docs/contracts/README.md), a separate governed execution service
that owns runs, workers, delegation records, approvals and limits. Odin
reaches Saga only through Saga's API. Deployment means locally operated
state and execution, with hosted inference. The billing promise is
subscription-first, with bounded, explicitly configured API spending,
never "no API costs".

The initial audience is one technically capable person managing several
software, research or infrastructure projects who is willing to run a
local service. General life administration is out of scope. Desktop
control is an optional later capability.

## Status (2026-10-14)

The documentation bootstrap is complete: design documents, decisions,
acceptance criteria, research, provenance, developer instructions, and a
pinned draft Saga contract are present. Run `python3 scripts/validate_docs.py`
to check documentation integrity.

On 2026-10-16, increment I0 was implemented under
[`substrate/`](substrate/README.md): the versioned event envelope and
namespaces, the record schemas, the heimdall-to-commitment mapping and
one fixture set for the duplicate, stale and unknown cases, validated by
a Go and a Python implementation that produce identical outcomes. It is
non-production and fixture-only. No Odin service, store, fake backend,
adapter or peer integration exists yet.

On 2026-10-16, ODIN-ADR-006 to 015 recorded the operator's consolidation
direction for the inherited clauses Odin owns
([decisions §4](docs/DECISIONS.md#4-odin-decisions-odin-adr)). A
[consolidation plan](docs/design/CONSOLIDATION-PLAN.md) exists as a
proposal, not a decision; its Saga-side parts wait on decisions in
Saga's repository ([X-14](docs/DECISIONS.md#5-issues-raised-by-the-extraction)).

Saga retains formal document authority while D14's ownership-transfer
review remains pending. The adapted specifications here are development
drafts; unresolved design questions remain explicit. See the
[bootstrap receipt](docs/provenance/HANDOFF.md). This work does not inspect
or change the existing deployment.

## First implementation milestone

1. **I0, event log and record schemas (delivered):** the versioned
   event envelope, its namespaces and the record schemas, validated by
   both the Go and the Python implementation against one fixture set
   ([ODIN-ADR-008](docs/DECISIONS.md#odin-adr-008--i0-narrowed-to-the-event-log-and-record-schemas);
   [`substrate/`](substrate/README.md)).
2. **I1, service foundation:** the adapter capability matrix, a fake
   Saga backend, the synthetic three-document fixture and the ownership
   mapping, then the service foundation. **I2, first harness**, adds the
   workstation daemon v0. Both run against the fake backend. A
   fixture-only Pi RPC control follows I2
   ([ODIN-ADR-015](docs/DECISIONS.md#odin-adr-015--early-pi-rpc-adapter-as-a-fixture-only-control)).
3. **I3, governed project.** The first live delegated run waits for Saga
   Phase B (its API and minimum enforcement). Fake-backend results do
   not establish production readiness.

Allowing I0–I2 alongside Phase B is Odin's interpretation of the source
blueprint; reconciliation with Saga's stricter phase wording remains
open ([X-1](docs/DECISIONS.md#5-issues-raised-by-the-extraction)).

Details, exit evidence and dependency gates are in
[`docs/ROADMAP.md`](docs/ROADMAP.md).

## Documentation

Start at [`docs/README.md`](docs/README.md), which gives the reading
order and authority:
[decisions](docs/DECISIONS.md) → [I/O contract](docs/design/ODIN-IO-CONTRACT.md)
→ [blueprint](docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md) →
[roadmap](docs/ROADMAP.md), with the
[acceptance scenarios](docs/design/ODIN-ACCEPTANCE-SCENARIOS.md) and the
[ecosystem integration plan](docs/design/ODIN-ECOSYSTEM-INTEGRATION.md)
alongside. Inherited decision references (`D0` to `D24`) resolve through
the [decision map](docs/provenance/DECISION-MAP.md).

## Contributing

Developers and coding agents: read [`AGENTS.md`](AGENTS.md) first.

## License and attribution

Odin's original work is licensed under [Apache-2.0](LICENSE), following
the operator's project-wide default; dotprivate's chosen license is MIT.
This does not relicense third-party material retained as research or
historical evidence.

The planned memory implementation draws on Victor Taelin's UniiChat
design. Attribution and permission for any reuse of material from its
gist remain to be resolved before that material is incorporated or
published; credit alone does not settle reuse terms. See
[ODIN-ADR-001](docs/DECISIONS.md#odin-adr-001--project-license).
