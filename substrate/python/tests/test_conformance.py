"""Every fixture case gives exactly its expected result (schemas README §3; ODIN-ADR-008 exit evidence)."""

from __future__ import annotations

import json

from odin_substrate import conformance, schemas


def test_every_case_matches_expected() -> None:
    schema_set = schemas.load()
    cases = conformance.load_cases(schema_set)
    results = conformance.run(schema_set)
    assert sorted(results) == sorted(c["id"] for c in cases)
    differing = [
        f"{c['id']}: expected {json.dumps(c['expected'], sort_keys=True)}, "
        f"got {json.dumps(results[c['id']], sort_keys=True)}"
        for c in cases
        if results[c["id"]] != c["expected"]
    ]
    assert not differing, f"{len(differing)} of {len(cases)} cases differ:\n" + "\n".join(differing)


def test_results_file_format(tmp_path) -> None:
    out = tmp_path / "results.json"
    assert conformance.main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.endswith("}\n")
    data = json.loads(text)
    assert text == json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    # Keys that do not apply are omitted; only cursor_after may be null.
    def nulls(value, key=None):
        if isinstance(value, dict):
            for k, v in value.items():
                yield from nulls(v, k)
        elif isinstance(value, list):
            for v in value:
                yield from nulls(v, key)
        elif value is None:
            yield key
    assert set(nulls(data)) <= {"cursor_after"}


def test_every_operation_is_exercised() -> None:
    cases = conformance.load_cases(schemas.load())
    assert {c["operation"] for c in cases} == set(conformance.OPERATIONS) | {"validate"}
