# Developer recipes for the Odin repository. One group per deliverable;
# only the substrate (I0) exists so far.

scratch := env_var_or_default("ODIN_SCRATCH", ".build")

# Run every check CI runs.
ci: docs go python conformance

# Documentation integrity (metadata, digests, identifiers, links).
docs:
    python3 scripts/validate_docs.py

# Go substrate packages: format check, vet, tests.
go:
    test -z "$(gofmt -l substrate)" || (gofmt -l substrate && exit 1)
    go vet ./...
    go test ./...

# Python substrate mirror: tests.
python:
    python3 -m pytest -q substrate/python/tests

# Both implementations validate the same fixture set; the results must agree.
conformance:
    mkdir -p {{scratch}}
    go run ./substrate/cmd/substrate-conformance -out {{scratch}}/conformance-go.json
    python3 -m odin_substrate.conformance --out {{scratch}}/conformance-python.json
    python3 scripts/compare_conformance.py substrate/schemas/fixtures/cases.json {{scratch}}/conformance-go.json {{scratch}}/conformance-python.json
