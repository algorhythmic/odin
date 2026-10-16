# odin-substrate (Python)

The Python implementation of the I0 substrate contract in
[`../schemas/`](../schemas/README.md) (ODIN-ADR-008). It validates every
fixture against the schemas, implements the semantics of the schemas
README §4 and writes the conformance results file that
`scripts/compare_conformance.py` compares with the Go implementation and
with the expected outcomes.

I0 is non-production and fixture-only. No peer API is implemented; there
is no service, store, fake backend or Saga client. The inbox and the
namespace log here are in-memory models of the semantics; the physical
store layout is open (X-11).

## Modules

| Module | Content | Governing section |
|---|---|---|
| `ids` | ULID validation and minting (stdlib only) | schemas README §2 |
| `schemas` | Schema loading and `$id` registry, strict decoding, the `pattern` override, error pointers, the `unknown_kind` check | schemas README §2, §4.1 |
| `kinds`, `namespaces`, `envelope` | Catalogues, the namespace writer check, the envelope | schemas README §4.2, §5 |
| `intake` | In-memory inbox: intake and dedupe, process, replay | schemas README §4.3, §4.4 |
| `records` | Revision, owner, transfer, operation reuse, message size, review combination | schemas README §4.5, §4.6 |
| `effects` | Restart, reconcile, dispatch, revalidate | schemas README §4.7 |
| `migration` | heimdall-to-commitment mapping coverage | schemas README §4.8 |
| `conformance` | Runs every case of `fixtures/cases.json`; writes the results file | schemas README §3 |

The only third-party dependency is `jsonschema` (with its `referencing`
registry). The schema directory is found relative to the package source
(`substrate/schemas`); set `ODIN_SUBSTRATE_SCHEMAS` to use another one,
for example when the package is installed from a wheel, which does not
carry the schemas.

## Running

With uv, from the repository root (the root `pyproject.toml` is a virtual
uv workspace whose one member is this package):

```bash
uv sync --locked
uv run python -m pytest -q substrate/python/tests
uv run python -m odin_substrate.conformance --out conformance-python.json
```

With the system interpreter, from the repository root. The tests need
only `pytest` and `jsonschema>=4.23`: this package's `pyproject.toml`
sets pytest's `pythonpath`, so they import the package from the source
tree. `python3 -m odin_substrate.conformance` needs the package
importable, so install it once in editable mode:

```bash
uv pip install --system -e substrate/python   # or: python3 -m pip install -e substrate/python
python3 -m pytest -q substrate/python/tests
python3 -m odin_substrate.conformance --out conformance-python.json
```

The results file maps every case id to its result, with keys sorted,
2-space indentation and a trailing newline. The runner also prints how
many cases differ from `expected` on standard error; the comparison that
gates CI is `scripts/compare_conformance.py`. A pass is I0 fixture-only
evidence.
