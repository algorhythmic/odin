# Local implementation — 2026-10-16

The repository now contains executable contract validators and a local,
credential-free service foundation. Every workflow result is **fake-backend
evidence**. This is not completion of I2–I7, a live Saga adapter, or a deployed
Odin agent. The operator explicitly left live credentials undecided.

## Implemented and reproducible

| Area | Code and evidence | Limit |
|---|---|---|
| I0 record/event contracts | [schemas](../schemas/README.md), [Go validator](../internal/contracts/contracts.go), [Python validator](../python/odin/contracts.py): 12 unaffected record types, four namespaces, 53 shared valid/invalid cases and 24 shared transition cases | Shape and narrow transition validation; not authority from a producer receipt |
| I0 import mapping | Task, checkpoint, decision, dependency, workflow and evidence mapping beside the schemas | Specification only; no peer import or retirement, no source actor promoted to owner |
| I1 transactional core | [store](../python/odin/store.py): WAL, one writer per namespace, revision checks, record/history atomicity, durable intake, cursor and outbox, regenerated history projection | File locks coordinate trusted processes; they are not process isolation |
| I1 recovery and direct control | [service](../python/odin/service.py): control-first recovery, persisted stop, timer replay, ownership-transfer holds, unknown reconciliation, recorded local CLI commands | Stop reports local state and leaves uncertain remote outcomes explicit; no live operator transport |
| I1 fake Saga and mirror | [fake](../python/odin/fake_saga.py), [mirror](../python/odin/mirror.py): stable operation IDs, synthetic digest/review/approval/delegation checks, run states, requests, event cursor, read-only consumer mirror | Fixture shapes, not Saga wire types, authentication, isolation or production conformance |
| I1 three-document proof | [demo](../python/odin/demo.py), [fixture](../fixtures/three-document/manifest.json): three synthetic streams, lost receipt, planner replacement, termination versus verification, integration acceptance gate | Execution, reviews and evidence are synthetic; no model creates or validates the artifacts |
| I1 evaluation and capability metadata | [episode schema](../schemas/evaluation-episode.schema.json), [matrix](../fixtures/fixture-capabilities.json), [policy](../python/odin/policy.py): exact identity slots, context/tools, limits, cost components and inclusion scope, missing usage, failed-attempt cost | No comparative model trial or model ranking; the example explicitly says no provider/model ran |
| I2 local preparatory components | [fixture host](../python/odin/host.py), [capture](../python/odin/capture.py), [profiles](../python/odin/profiles.py): idempotent host commands, offline/reconnect state, result lineage, atomic checkpoint spool, denied tool paths | No SDK process, real host transport, native-child dispatch, credential store, peer observer or real capture module |
| I2 budget prototype | [reservations](../python/odin/budgets.py): transactionally serialized cap/count/depth admission, unknown usage retains allowance, overrun blocks admission | Arithmetic on asserted fixture bounds; no claim of an enforceable provider dollar cap, X-15 remains open |
| ADR-022 portfolio and handoff | [coordination](../python/odin/coordination.py): synthetic project owner, scoped operator grants, typed durable handoffs, stale/revoked/expired checks and returns eligible for checking | Receipt replay is historical; any future dispatch must reauthorize current ownership, grant, budget and stop state |
| ADR-022 command and model configuration | [gateway](../python/odin/gateway.py), [role configuration](../python/odin/orchestration_config.py): one transactional command path, exact requested model/provider/harness identity and fixture session intents; private socket accepts validated local operator commands | No model process, real adapter, remote authentication or live dispatch; voice is a recorded source tag only |
| ADR-022 consultation and layout | [chirality](../python/odin/chirality.py), gateway layout bindings: bounded two-round synthetic responses retain dissent and unknown-cost allowance; stop/restart and stale context are explicit | No model consultation or Herdr process; layout `done` is visibility, never assignment acceptance |

The service is Python; Go is an independent contract/transition validator.
No second production service or universal harness adapter has been added.
The private Unix socket exposes `status`, `stop` and validated typed local
operator `command` requests through the gateway. The caller supplies a
terminal or voice source tag, not an actor identity or authorization. The
socket is not a public model tool API; trusted fixture code supplies the
harness and adapter contexts.

## Experimental orchestration scope

ODIN-ADR-022's local prototype has a configured portfolio coordinator, one
planning owner per project, scoped grants, durable typed handoffs, fixture
session intents, bounded read-only chirality and recorded layout observations.
The [orchestration demo](../python/odin/orchestration_demo.py) joins these in
one synthetic flow, restarts the service, replays a receipt, preserves
independent dissent and unknown usage, revokes a grant and records a stop.
AC-45–AC-50 define full acceptance targets; these local checks exercise
protocol pieces without completing the real harness or Saga scenarios.

The role names Fable, Astra, Opus and Sol are requested configuration in
fixtures. No provider or model runs. Worker intents identify Saga's API as
the only execution path, but do not submit a run. The Herdr fixture records
session/layout bindings and observations; it does not operate Herdr or turn
a `done` display into assignment completion. `voice` tags already transcribed
text at intake; there is no microphone, transcription or speech output, and
voice cannot approve or grant authority. A replayed command receipt proves
what was committed earlier; a future real dispatcher must check current
authority again before any effect. X-1, X-7, X-12, X-13, X-15 and Saga Phase B
remain open.

## Run the local checks

Tested with Python 3.14.7 and Go 1.27.2 on Linux. Python requires 3.11 or
newer. Install dependencies in a virtual environment; runtime state belongs
outside this checkout. The dependency versions are pinned in
[`requirements.txt`](../requirements.txt) and [`go.mod`](../go.mod).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make check PYTHON=.venv/bin/python
```

`make check` runs documentation integrity and its regression suite, Python
fixture validation, Go tests and the Python runtime suite. The socket test needs permission to bind
a private local Unix socket; it uses no TCP network or credentials.

```bash
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-demo-new demo
PYTHONPATH=python python -m odin --state /tmp/odin-orchestration-demo orchestration-demo
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-service-new serve
```

Use a fresh private directory for each demo, including the orchestration demo.
The `python` command above assumes the virtual environment is activated;
`.venv/bin/python` works without activation. The CLI creates state with mode `0700` and
refuses state inside the checkout or a directory accessible by other users.
The demo intentionally leaves its synthetic databases and regenerated history
there for inspection. In another terminal while `serve` is running:

```bash
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-service-new status
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-service-new command --request /absolute/path/request.json --surface terminal
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-service-new command --request /absolute/path/request.json --surface voice
PYTHONPATH=python .venv/bin/python -m odin --state /tmp/odin-service-new stop
```

The request file contains a `gateway-command` JSON object with
`schema_version`, a unique operation ID, action and payload. The `voice`
surface means the text was supplied as voice-origin input; it adds no voice
authority. The socket binds only inside the private state directory. `stop`
persists the stopped state and holds remote outcome as queued or uncertain
until the fake backend reconciles it; the service stays available for status.
Ctrl-C stops the development service process. There is no live mode switch.

Optional formatting/lint checks use the pinned development dependency:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff format --isolated --check python tests scripts/validate_runtime.py
.venv/bin/ruff check --isolated --select E4,E7,E9,F,I python tests scripts/validate_runtime.py
```

## Evidence and boundaries

The integrated checks pass 79 Python runtime/component tests, 53 shared
Go/Python structural cases, 24 transition cases, and 13 documentation-validator
regressions. The earlier `runtime/` compatibility suites also pass with
73 structural and 19 semantic cases. This counts synthetic checks, not live
acceptance or model evaluation results.

The [runtime tests](../tests/test_runtime.py) include actual process death
before commit and after the fake backend committed a submission. Recovery
retains one logical run. They also cover duplicate/conflicting intake,
stale writes, stop received before a crash, timer replay, mirror gaps,
unknown-expired and irreducibly unknown effects, checkpoint replay, offline
bindings, partial/stale/duplicate child returns, unavailable review positions,
capability refusal, observational class recording, and incomplete cost data.

This supplies local evidence for parts of AC-01–AC-07, AC-10, AC-14,
AC-22–AC-23, AC-27, AC-36–AC-37 and AC-41–AC-50. The orchestration
checks use synthetic handoffs, consultations, commands and layout observations. It does **not** mark these
entire scenarios passed: several require a real SDK, authenticated operator
channel, independently assessed evidence, or producer behavior. AC-29 remains
Saga's test. AC-34–AC-35 are not implemented by this work.

The fake provides behavioral pieces of B-00–B-03, B-05–B-13 and B-15–B-16.
It models only one synthetic operator/reviewer, one content digest, immutable
fixture delegation creation and global stop. It does not implement production
identity, approval expiry/reissue, scoped stop reports, all operation-lookup
retention states, published admission schemas or worker isolation. Tests
inject uncertain lookup states where needed. B-04 guidance is explicitly
refused while X-7 is unresolved; B-14 is withdrawn and B-17 is Saga-owned.
Consequently, full Appendix B conformance and the full I1 exit remain open.

## Remaining work and gates

| Work | Required before it can be claimed complete |
|---|---|
| Full I1 compatibility evidence | Complete the fake's remaining Appendix B semantics against resolved producer requirements; document each remaining gap, without inventing Saga wire contracts. X-2/X-7 and producer gaps stay open. |
| I2 first harness and workstation daemon | Claude Agent SDK adapter and runtime integration package; real tool isolation and replacement/briefing checks; host identity/transport, heartbeat and environment probe; credential lineage X-12. No development login is a fallback. |
| I2 child dispatch and compaction | Resolve X-15's provider/adapter enforcement and lifecycle design before enabling native children; resolve X-10 context policy and third-party reuse terms before compactor integration; run AC-34–AC-35 and actual SDK AC-42–AC-44. |
| Pi RPC control | I2 exit first (ADR-015); no adapter has been prematurely added. |
| I3 and any live run | Saga Phase B, pinned API and authentication/approval/reviewer protocols, billing decision, Telegram and real acceptance evidence. |
| I4–I7 | Prior increments and their operator/peer gates: Herdr, heimdall retirement/import, capture/retrieval contracts, package preservation and desktop authority. No peer repository was changed. |
| Phase G comparison | Real repeated controlled trials with complete accounting and independently assessed outcomes; schema examples are not trial results. |

The existing handoff, X-1, X-7, X-10–X-15 and producer gates are not closed
by local tests. ODIN-ADR-021 chooses the local SQLite layout; X-11 still
requires production process-ownership and failure-domain validation.
