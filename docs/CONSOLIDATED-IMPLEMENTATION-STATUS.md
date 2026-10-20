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
Claude Code with Remote Control after operator login. The operator reports
an active executive conversation in Herdr, and its filesystem-access
diagnosis was found as a durable unverified proposal in the local store.
That does not independently verify the running model identity or a Remote
Control conversation. The SDK adapter remains gated.

The repository-evidence slice under ADR-025 adds an operator-triggered
import of selected committed repository text into project-scoped memory,
with exact revision reads and a paged catalog. It also provides an opt-in
Read/Glob/Grep profile for the next explicit native session resume. Reports
and imported evidence persist in local SQLite; the legacy fake-backend
label describes the execution backend, not an ephemeral record store.

The development-profile slice under ADR-026 removes the native pilot's
Odin-imposed tool, directory and environment restrictions. Version 3 runs
normal Claude Code tools and prompt with permission bypass, real checkout
cwd/HOME, inherited environment and normal integration loading. It retains
the dedicated login, session identity and additional Odin MCP bridge.
Inspection, edits, commands, tests and native agents can perform development
directly; the fake backend is not in that execution path, and an unavailable
Odin service does not block native startup. Selecting the profile and observing it in a resumed live session are separate evidence.

## Delivered behavior

| Area | Implementation and evidence | Boundary |
|---|---|---|
| Exact evidence | `Memory.read_source`, the `memory_source_read` gateway action and `evidence` CLI; [tests](../tests/test_memory_evidence.py), [gateway tests](../tests/test_evidence_gateway.py) | Requested source revision, digest and provenance are preserved; historical and current reader policy both apply; bounded reads fail instead of truncating |
| Redaction consistency | Exact reads and memory snapshots quarantine a source identity after a revision is redacted | Unredacted sibling revisions keep physical cleanup pending; callers must explicitly redact remaining revisions before local cleanup can confirm. External destination receipts remain independent. |
| Decision pagination | `decision_page_token` and `next_decision_page_token`; [tests](../tests/test_continuity.py) | Tokens bind project, principal, offset, canonical revisions and memory revision; a changed view requires restarting pagination |
| Decision validity | Shared display/response checks for bound records, memory, resolved evidence and expiry | Stale or expired wording is unavailable; obligations survive; a response still grants no execution authority |
| Continuity demonstration | [integration demo](../python/odin/integration_demo.py) and [integration tests](../tests/test_continuity_integration.py) | Attributed source changes, checkpoint, prepared decision, outage/recovery, restart and exact evidence; reported success leaves independent verification unmet |
| Human and machine views | Human briefing renders the exact bounded `machine_view` from the demo | Both use an operator-authenticated local context; this does not establish a live planner/worker gateway route |
| Repository evidence | [committed-text importer](../python/odin/repository_memory.py), operator gateway action and exact catalog reads; [tests](../tests/test_repository_memory.py) | Explicit committed selection, project-bound readers, replay-safe batches and no live checkout watcher; no semantic statements are invented |
| Native repository reads | Retained version 2 profile preserves session identity on explicit resume; [tests](../tests/test_executive_runtime.py) | Read-only boundaries describe version 2 only; version 3 supersedes them |
| Native development | Version 3 uses the normal native tool set, permission bypass, real checkout cwd/HOME and inherited environment; dedicated login/session and MCP bridge retained | Startup changes require exit/resume; actual model/tool behavior requires live observation; no claim of managed isolation, budgets or Saga guarantees |
| Executive delegation | [delegation module](../python/odin/delegation.py), detached [runner](../python/odin/delegation_runner.py), six `odin_delegation_*` bridge tools and `delegation-configure`; [tests](../tests/test_delegation.py) | One local-backend session per project; Claude Code turns carry harness budget/turn options, Codex turns require explicitly unenforced limits; returns are unverified until executive acceptance; no isolation, managed session host, X-15 child dispatch or Saga guarantees |

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
| OHS-05 | Native executive conversation under ADR-024, repository evidence under ADR-025, native development profile under ADR-026 and local-backend delegation sessions under ADR-027; operator reports an active session | Managed SDK session host, profile isolation, authenticated host transport, X-15 child dispatch and Saga Phase B gates remain separate |
| OHS-06/07 | Synthetic demonstrations only | Reviewed task migration, enforceable old-writer retirement, pinned producer feeds and their existing live gates |
| OHS-08/09 | Executive diagnosis persists; repository evidence and version 3 native development support reconciliation and direct improvement | Independently verified Fable/remote dialogue, measured improvement, connected feeds and managed cutover acceptance |

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

The repository-evidence check passes 244 Python tests, including committed
snapshot import, bounded catalog discovery, exact MCP reads, scope denial,
replay, service restart/readback and idle native profile upgrade. The same
full check passes 13 documentation regressions, 94 contract cases, 24
transitions, Go tests and 73/19 shared parity fixtures. These are component
checks; actual native Read/Glob/Grep behavior still needs an explicit pilot
resume and observation.

The ADR-026 full check passes 252 Python tests, including 42 executive-runtime
tests and 8 new development-profile cases, plus documentation integrity,
13 documentation regressions, 94 contract cases, 24 transitions, Go tests and
73/19 shared parity fixtures. These checks cover launch construction, inherited environment,
normal prompt/tool behavior in the prepared command, identity preservation
and activation without interrupting the current process. Configuration locking
also prevents profile staging from racing a native session identity rotation. Command construction
is not proof of live tool behavior: record an actual read, edit/test or native
agent invocation after resume separately. Earlier read-boundary checks apply
only to retained version 2, not the unrestricted development profile.

The ADR-027 delegation check passes 334 Python tests, including 22 delegation
tests that run real detached runners against synthetic harness binaries
(open, assign, launch, return, follow-up resume, restart, native-id
rotation, stop/interrupt, lost and overdue runners, failure visibility,
unenforced-limit refusal, scope, replay, the bridge envelope, lineage lease
refusal/acquisition/holding, untrusted lease files, shared-lineage
acceptance and one-at-a-time launches on a shared lineage), one cycle
through a real `serve` process and the stdio bridge, the
`delegation-configure` CLI, result size limits and the harness output parsers, plus
documentation integrity, 13 documentation regressions, 94 contract cases,
24 transitions, Go tests and 73/19 shared parity fixtures. Live Claude Code
and Codex delegation turns were observed on the operator's host on
2026-10-20 and are recorded as local-backend evidence outside the
repository; they establish no isolation, enforced ceiling or Saga guarantee.

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
