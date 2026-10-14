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
harness.

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
to check documentation integrity. No Odin service implementation or runtime
test exists yet.

Saga retains formal document authority while D14's ownership-transfer
review remains pending. The adapted specifications here are development
drafts; unresolved design questions remain explicit. See the
[bootstrap receipt](docs/provenance/HANDOFF.md). This work does not inspect
or change the existing deployment.

## First implementation milestone

1. **I0, contracts and fixtures:** versioned record schemas, the event
   envelope, the adapter capability matrix, a fake Saga backend, and a
   synthetic three-document fixture.
2. **I1, service foundation**, then **I2, first harness**, both against
   the fake backend.
3. **I3, governed project.** The first live delegated run waits for Saga
   Phase B (its API and minimum enforcement). Fake-backend results do
   not establish production readiness.

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

This repository has no license file, and nothing in it grants a
license. Odin's first memory implementation adapts Victor Taelin's
UniiChat design, credited, from a gist that shows no license. The
operator's standalone tools also show none. These questions are open
and must be settled before anything is published
([`docs/DECISIONS.md`](docs/DECISIONS.md) §3, item 5).
