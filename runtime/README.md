# Runtime implementation

This directory contains the first implemented part of I0: versioned record
schemas, a synthetic fixture set, independent Go and Python validators, and
pure checks for duplicate events, stale revisions/ownership and unknown
effect outcomes. It is not yet an Odin service or workstation daemon.

The two validators consume the same JSON Schema Draft 2020-12 files and the
same structural and semantic fixtures. Their results must agree. The
[schema notes](schemas/v1/README.md) describe the supported records, native
identity mapping and checks that require later transactional implementation.
The schemas' `https://odin.invalid/` identifiers are local registry names;
validation never fetches a schema over the network.

## Run the checks

Requirements: Python 3.11 or later, Go 1.23 or later, and the dependencies
pinned in `python/requirements.txt` and `go/go.mod`/`go/go.sum`.
From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r runtime/python/requirements.txt
.venv/bin/python scripts/check_runtime.py
python3 scripts/validate_docs.py
```

`check_runtime.py` runs both language test suites, then compares their JSON
verdicts for every shared structural and semantic fixture. It fails on an
empty result, duplicate case name, unexpected validation result or language
disagreement. `--python` and `--go` select toolchain executables when needed.
Generated Go test binaries live in a temporary directory.

To validate an individual record with each implementation:

```bash
PYTHONPATH=runtime/python .venv/bin/python -m odin_runtime validate \
  --schema event.schema.json runtime/fixtures/v1/valid/event_valid.json
cd runtime/go
go run ./cmd/validate --schema event.schema.json \
  ../fixtures/v1/valid/event_valid.json
```

The shared fixture commands are `python -m odin_runtime fixtures` and
`python -m odin_runtime semantics` (with the same `PYTHONPATH`), or the Go
CLI's `--fixtures` and `--semantics` flags. Fixtures contain synthetic data
only. Invalid fixtures deliberately exercise rejected inputs.

## Guarantees and boundaries

Validation checks record shapes, versions, state enums, UTC calendar times,
non-nil ULIDs and local schema references. JSON decoding rejects duplicate
object keys, trailing data, nonfinite values and numbers outside the agreed
interoperable range. Schema definitions and fixture manifests are validated
as well. These checks do not authenticate the producer or make a record
authoritative.

The pure semantic checks classify replayed events without assuming dense
producer sequences, require exact revision and ownership generations, and
retain uncertain effects. `unknown_expired` never grants retry; a confirmed
`absent` result still requires authority revalidation before retry. These
functions do not persist or dispatch anything. Transactional intake,
single-writer enforcement, replay, outbox delivery and recovery are I1 work.

Workload classes remain configuration data; the synthetic fixture does not
select a production model, provider or effort default. The heimdall mapping
defines Odin target fields only; no peer reader or migration runs here.

## Remaining gates

- **I0 remains incomplete:** X-7 must be decided before Review/guidance
  schemas are written. No Review or guidance schema is included yet.
- **I1 has not started:** X-11's store layout and failure domains require a
  recorded choice; G2 governs the direct-stop split with Saga.
- **I2 has not started:** the host credential lineage (X-12), compactor
  context policy (X-10), capability profiles and isolation checks remain.
- **I3 is gated on Saga Phase B:** no live Saga calls, delegated execution,
  model sessions, deployment or peer imports are exercised by these tests.

See the [roadmap](../docs/ROADMAP.md) and
[decision record](../docs/DECISIONS.md) for the authoritative gates.
