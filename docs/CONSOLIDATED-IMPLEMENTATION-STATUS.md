# Consolidated Odin implementation status

**2026-10-19. Continuity slice and executive pilot under the
[consolidated work plan](design/ODIN-HEIMDALL-SKALD-WORK-PLAN.md).**
The committed Odin baseline through `a9f22a1` is integrated on
`codex/odin-continuity-integration` by merge `ea164d2`. The work plan is
preserved in `5bf336b`. Heimdall and Skald remain separate producer work.

The first slice adds exact local evidence reads, fixes stale decision views and
demonstrates one synthetic continuity flow. It uses the existing local
service and fake Saga backend. No producer interface is invented or pinned,
and no live feed, task import or cutover is enabled.

The next slice implements the [native Fable executive pilot](EXECUTIVE-PILOT.md)
under ADR-024: private Claude login/configuration, explicit native session
start/resume/reset, a separate project-bound MCP socket, scoped continuity
and evidence reads, and durable unverified reports/proposals. It can launch
Claude Code with Remote Control after operator login; no live model response
or remote conversation has yet been observed. The SDK adapter remains gated.

## Delivered behavior

| Area | Implementation and evidence | Boundary |
|---|---|---|
| Exact evidence | `Memory.read_source`, the `memory_source_read` gateway action and `evidence` CLI; [tests](../tests/test_memory_evidence.py), [gateway tests](../tests/test_evidence_gateway.py) | Requested source revision, digest and provenance are preserved; historical and current reader policy both apply; bounded reads fail instead of truncating |
| Redaction consistency | Exact reads and memory snapshots quarantine a source identity after a revision is redacted | Unredacted sibling revisions keep physical cleanup pending; callers must explicitly redact remaining revisions before local cleanup can confirm. External destination receipts remain independent. |
| Decision pagination | `decision_page_token` and `next_decision_page_token`; [tests](../tests/test_continuity.py) | Tokens bind project, principal, offset, canonical revisions and memory revision; a changed view requires restarting pagination |
| Decision validity | Shared display/response checks for bound records, memory, resolved evidence and expiry | Stale or expired wording is unavailable; obligations survive; a response still grants no execution authority |
| Continuity demonstration | [integration demo](../python/odin/integration_demo.py) and [integration tests](../tests/test_continuity_integration.py) | Attributed source changes, checkpoint, prepared decision, outage/recovery, restart and exact evidence; reported success leaves independent verification unmet |
| Human and machine views | Human briefing renders the exact bounded `machine_view` from the demo | Both use an operator-authenticated local context; this does not establish a live planner/worker gateway route |

Exact-read results are not cached in gateway receipts, so old commands
cannot replay content after access changes. The recorded command retains
query identity, not a second copy of the returned source body. Reads always
use the current trusted service context; callers cannot supply a principal
or enlarge their own project scope in the payload.

## Work package progress

| Package | Current state | Next dependency or deliverable |
|---|---|---|
| OHS-01 | Implementation baseline integrated and reproduced | Browser-retention and early-pilot dispositions, plus producer-owned EC-13/14 records, remain separate work |
| OHS-03 | Odin-local exact-read request/result schemas and synthetic contract cases added | Published Skald/Heimdall contracts and complete task-import mapping; local schemas are not peer wire contracts |
| OHS-04 | First continuity slice implemented and exercised | Portfolio presentation, typed checkpoint/progress admission, source enrollment/health before first capture, and full omission/pagination coverage |
| OHS-05 | Native executive conversation pilot implemented under ADR-024; session-host/SDK mocks retained | Dedicated login and live pilot acceptance; full profile isolation, authenticated host transport and Saga Phase B gates remain separate |
| OHS-06/07 | Synthetic demonstrations only | Reviewed task migration, enforceable old-writer retirement, pinned producer feeds and their existing live gates |
| OHS-08/09 | Operator pilot preparation implemented; reports and improvement proposals remain inert | Observed Fable/remote dialogue, governed changes, connected feeds and cutover acceptance |

The OHS-02 repairs are in the user's separate Heimdall/Skald sessions. No
peer repository, installed source configuration or desktop setting changed
as part of this Odin implementation.

## Run the synthetic slice

Use the repository's pinned Python dependencies and a private state
directory outside the checkout:

```bash
odin_state=$(mktemp -d /tmp/odin-continuity-slice.XXXXXX)
PYTHONPATH=python python -m odin --state "$odin_state" integration-demo
```

The result includes a `human_briefing`, the same underlying `machine_view`,
current and historical evidence, source coverage stages, denied foreign
reads and the still-unmet commitment criterion. Source reads and decisions
use the recorded gateway; synthetic ingestion and checkpoint creation are
trusted fixture setup. Reusing nonempty service state is refused.

To inspect this synthetic state through the existing local operator socket,
start `serve` and use the project ID from `machine_view.project.id`:

```bash
PYTHONPATH=python python -m odin --state "$odin_state" serve
```

In another terminal, with the same state path:

```bash
PYTHONPATH=python python -m odin --state "$odin_state" evidence \
  --project PROJECT_ID --source synthetic-interface-session --revision 2
PYTHONPATH=python python -m odin --state "$odin_state" resume --project PROJECT_ID
```

The generic server does not install the demonstration's private fixture
evidence resolver. Its exact source reads work, while prepared decisions
whose fixture references cannot resolve appear unavailable. The complete
prepared-decision flow is demonstrated inside `integration-demo`, where
the explicit synthetic resolver is installed. No permissive fallback is
added to the server.

The local Unix socket authenticates the existing `local-operator` context;
it is not remote authentication or a public model API. The demo uses that
same identity and records its checkpoint against a synthetic planning
session.

## Validation and remaining limits

The integrated baseline was checked from an isolated export of `ea164d2`:
13 documentation-validator regression tests, 151 Python service tests,
89 local contract cases, 24 transitions, Go tests and Go/Python parity for
73 I0 schema fixtures and 19 semantic fixtures. Source identities, frozen
bytes, pinned producer contracts and the 223-entry prototype receipt were
preserved. These counts describe the baseline, not full runtime acceptance.

The completed first-slice check passed 13 documentation-validator regression
tests, 177 Python service tests (including the actual
`integration-demo → serve → evidence → resume` CLI flow), 94 local contract
cases, 24 transitions, Go tests and the same 73/19 I0 cross-language fixture
sets. New demonstration and test files pass targeted Ruff checks. The final
memory regression suite also passes after test formatting cleanup.

The executive-pilot check passes 224 Python tests, including 47 new pilot
tests and the real local `serve → MCP report → restart → readback` process
flow. The same full check passes documentation integrity, 13 documentation
regressions, 94 contract cases, 24 transitions, Go tests and 73/19 shared
Go/Python parity fixtures. This is synthetic/component evidence, without
model inference, authentication, Remote Control pairing or live Saga work.

The implementation check commands are:

```bash
make check compatibility
```

Use the documented Python/Go executables through `PYTHON` and `GO` when they
are not on the shell path. Tests include synthetic local Unix sockets; a
socket-restricted sandbox cannot run those cases. Exported source trees
without Git metadata can use `GOFLAGS=-buildvcs=false` for validation.

Production profile enforcement, authenticated remote identity, real
capture, producer source enrollment, task import and model interpretation
remain open. Memory coverage before a producer's first visible source is
also still incomplete; the demo's unknown-source stage follows its first
captured fixture. A passing synthetic demonstration does not complete
I0/I1/I2 or the live acceptance scenarios.
