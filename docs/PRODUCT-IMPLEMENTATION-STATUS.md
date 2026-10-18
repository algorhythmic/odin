# Product implementation status

The product plan now has a runnable local continuity slice: durable prepared
decisions, restart-safe resume views, source-attributed memory, freshness and
access checks, and explicit delivery/acknowledgement. The session host and
Claude SDK lifecycle are exercised with protocol mocks. Live model dispatch,
authenticated workstation transport and Saga execution remain disabled.

The imported prototype is preserved by local commit `47e074e` and its
[file inventory](provenance/PROTOTYPE-INTEGRATION.md). The
[product plan](design/ODIN-PRODUCT-IMPLEMENTATION-PLAN.md) describes the full
target; [ADR-023](DECISIONS.md#odin-adr-023--local-continuity-and-attributed-memory)
records the implementation scope. This work changes no peer repository,
producer pin or frozen extraction source.

## Work package status

| Package | Delivered | Remaining |
|---|---|---|
| PLAN-01 | Reconciled source inventory, reproducible local baseline commit, shared validation and capability inventory | Full inherited I1/producer compatibility remains open |
| PLAN-02 | Reused transactional records, recovery and fake-Saga foundation; canonical commitments/checkpoints feed the local view | Production process isolation and complete Appendix B behavior |
| PLAN-03 | Source revisions, attributed status, canonical decision binding, service learning time, current reader checks, transitive invalidation, bounded snapshots, freshness, processing gaps and redaction receipts | Model extraction, actual retrieval/compaction integrations, external deletion executors and production retention policy |
| PLAN-04 | Prepared requests bound to resolved evidence and service policy; scoped, bounded pages; lost-delivery/restart behavior; answers retain commitments | Real-history migration, authenticated remote identity and daily operator pilot |
| PLAN-05 | Exclusive workstation journal, reserved uncertain starts/stops, reconnect observations, current authority checks and mock-tested Claude SDK binding | Actual SDK installation/version probe, credential store, authenticated daemon, permission/profile/limit enforcement; no earlier production Codex route |
| PLAN-06 | Existing three-document and orchestration fake scenarios retained | Live Saga Phase B, published identity/wire/approval protocols, billing choices and I3 migration/shadow/cutover evidence |
| PLAN-07 | Offline comparison validation/accounting and attention measures; adversarial semantic-memory cases | Repeated real trials, compactor comparison, operator-attention baseline and empirical conclusions |
| PLAN-08 | Local reviewed correction proposals; existing Herdr visibility and voice-tag refusal fixtures retained | Real Herdr, audio, archive/retrieval/preservation and desktop integrations under their original gates |

`python -m odin capabilities` returns a validated inventory of **usable now /
fixture-tested / planned / blocked**, with evidence paths, blockers and next
actions. It is informational and never grants runtime capabilities. A
fixture-tested entry is not a live acceptance result.

## Run and inspect

Install the root pinned dependencies in a virtual environment. Validation
for this work uses Python 3.12.15 and Go 1.27.2. The service uses synthetic
Saga behavior; no demo invokes a model or accesses credentials.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make check PYTHON=.venv/bin/python
make compatibility PYTHON=.venv/bin/python
PYTHONPATH=python .venv/bin/python -m odin capabilities
```

Use a fresh private directory outside the repository for each demo:

```bash
odin_state=$(mktemp -d /tmp/odin-continuity.XXXXXX)
PYTHONPATH=python .venv/bin/python -m odin --state "$odin_state" continuity-demo
```

The continuity demo records a changed requirement and interrupted checkpoint,
prepares a decision, records delivery without acknowledgement, restarts, and
shows that the obligation and unacknowledged changes survive. A similarly
named second project remains separate. Integration tests additionally run
memory projections and the recorded gateway through the same service store.

The existing `demo` and `orchestration-demo` actions remain available. Run the
private fixture service against a demo state directory, then use its explicit
project IDs:

```bash
PYTHONPATH=python .venv/bin/python -m odin --state "$odin_state" serve
```

In another terminal, set `odin_state` to the same directory:

```bash
PYTHONPATH=python .venv/bin/python -m odin --state "$odin_state" resume --project PROJECT_ID
PYTHONPATH=python .venv/bin/python -m odin --state "$odin_state" memory --project PROJECT_ID
```

For prepared decisions and view delivery, send a schema-validated gateway
command with `--request`. The gateway actions are `prepare_decision`,
`answer_decision`, `resume`, `view_delivery`, `view_ack` and `memory_snapshot`.
The service supplies operator identity, project scope and current policy
revision; clients cannot supply those as an authorization shortcut. The
private socket is a trusted local-user boundary, not remote authentication
or confinement against other processes owned by that user.

Resume returns a fresh `issue_id`. A `view_delivery` payload contains that
exact briefing and produces a `delivery_id`; explicit `view_ack` or
`acknowledge --delivery DELIVERY_ID` then advances the seen cursor. A lost
response never acknowledges itself. Replaying a projection request asks for
a fresh view rather than serving a saved private snapshot. Paginated views
must carry the returned revision token when continuing a page.

Prepared decision evidence supports canonical `record:` references or a
trusted resolver. Arbitrary unresolved references fail closed; synthetic
`fixture:`/`artifact:` references require explicit fixture mode in component
tests. A response records an answer, clears the matching open question and
keeps the commitment open. A separate authorized action is still required.
Canonical request history keeps generic prompts and stable choice handles;
the user-facing wording lives in a removable prepared projection. Resume
revalidates that projection's evidence before displaying it.

The offline evaluation CLI validates the frozen conditions and paired
observations before accounting for attempts, cost, missing telemetry and
operator attention. Run the supplied synthetic example explicitly:

```bash
PYTHONPATH=python .venv/bin/python -m odin evaluate \
  --request fixtures/synthetic-evaluation-request.json --fixture-evidence
```

The flag accepts only synthetic `fixture:` evidence; it does not invoke a
model or establish a quality ranking. Without it, unresolved evidence is
rejected. Real observation analysis requires a trusted evidence resolver via
the Python API. Correction proposals likewise require a canonical project,
resolved source/review/regression evidence and explicit review; their local
updates cannot change tool permissions, authority or runtime policy.

## Memory and deletion

The [memory implementation](design/MEMORY-IMPLEMENTATION.md) uses the service
namespace and content-free mutation events. It preserves source observation,
effective time and service-stamped learning time separately. Recent imports
cannot appear in past knowledge views; current permissions also apply to
historical queries. Retrieval re-observation does not refresh stale evidence.

Redaction invalidates source and transitive derived content immediately.
`Memory.purge_local_storage()` runs outside the mutation transaction and
confirms the local receipt only after SQLite cleanup and WAL truncation
succeed. A pinned reader leaves cleanup pending for retry. The check covers
active database/WAL content, not filesystem media remnants; external archive,
export or backup destinations each retain their own pending confirmation.

Gateway projection and decision receipts contain metadata, not returned
memory, briefing or prepared-decision bodies. Source redaction conservatively
invalidates prepared questions bound to the project's memory revision and
preserves the underlying obligations. Legacy history containing full question
text needs a separate migration; it cannot receive a complete local deletion
confirmation merely because the current projection was scrubbed.

## Verification scope

`make check` checks documentation integrity and regressions, both-language
contract fixtures and Python component/CLI tests. The socket test binds only
a private temporary Unix socket. `make compatibility` retains the earlier
runtime contract suites. Documentation validation does not establish semantic
completeness or live behavior.

Final local validation passed: 151 Python component/integration tests,
13 documentation-validator regression tests, 89 shared contract cases and
24 transition fixtures. The retained compatibility suites also passed
Go/Python parity for 73 schema fixtures and 19 semantic fixtures. Ruff and
`git diff --check` passed. These counts describe synthetic/local evidence,
not production acceptance or empirical model quality.

| Plan checks | Executable local evidence | Limit |
|---|---|---|
| PLAN-C01 | `tests/test_runtime.py`, `test_continuity.py`, `test_harness.py` | Fake execution and injected transport; real host/Saga crash evidence pending |
| PLAN-C02–C06 | `tests/test_memory.py`, `test_product_integration.py` | Deterministic attributed statements; no model extractor or real retrieval |
| PLAN-C07 | `tests/test_continuity.py`, `test_product_integration.py` | Synthetic scopes and explicit local acknowledgements |
| PLAN-C08–C09 | `tests/test_coordination.py`, `test_harness.py`, budget cases in `test_runtime.py` | Fixture reservations and authority callbacks do not prove provider hard caps |
| PLAN-C10 | `tests/test_chirality.py`, review cases in `test_runtime.py` | Deterministic combination and synthetic reports, not independent live review |
| PLAN-C11 | `tests/test_gateway.py`, `test_product_integration.py` | Herdr observations and voice-origin text only |
| PLAN-C12 | `tests/test_improvements.py` | Inert reviewed local updates; never installs permissions or runtime policy |

## Remaining live prerequisites

The launch boundary requires X-12's dedicated Odin credential/store/refresher,
X-13's provider/data policy and actual adapter capability evidence. Native
children additionally require X-15. The existing developer login is not a
fallback. No authentication file was copied or inspected during this work.

Saga Phase B and the published producer interfaces still gate PLAN-06 and
every live delegated run. X-7 still gates ambiguous guidance. X-10's actual
compactor context/reuse decisions, peer contracts, real migrations and the
operator pilot remain unfinished. The code does not claim these can be
enabled by flipping a single configuration flag.
