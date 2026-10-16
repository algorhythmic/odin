"""Fixture conformance runner (schemas README §3, §4; ODIN-ADR-008 exit evidence).

Runs every case of ``fixtures/cases.json`` by its operation and returns the
results map ``{case id: result}``. Before a non-``validate`` operation runs,
its input is checked against ``fixtures/inputs.schema.json#/$defs/<operation>``;
a failure there is a defect in the fixture and raises :class:`FixtureDefect`
rather than becoming an outcome.

Command line (from the repository root)::

    python3 -m odin_substrate.conformance --out <path>

writes the results file: keys sorted, 2-space indentation, trailing newline.
A pass is I0 fixture-only evidence; it exercises no service, store,
backend or peer API.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import effects, intake, migration, records, schemas
from .namespaces import NamespaceLog

CASES = "fixtures/cases.json"


class FixtureDefect(ValueError):
    """A fixture or case index does not match its schema; not a case outcome (schemas README §3)."""


def _append_op(name: str) -> Callable[[schemas.SchemaSet, Any], dict[str, Any]]:
    def run(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
        log = NamespaceLog(s.namespaces)
        return getattr(log, name)(doc["writer"], doc["event"])

    return run


def _intake_sequence(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
    inbox = intake.Inbox(s.kinds)
    return {"steps": [inbox.intake(event) for event in doc["events"]]}


def _replay(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
    return intake.Inbox.from_events(doc["events"], s.kinds).replay()


def _inbox_sequence(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
    inbox = intake.Inbox.from_events(doc["events"], s.kinds)
    steps: list[dict[str, Any]] = []
    for step in doc["steps"]:
        if step["op"] == "process":
            steps.append(inbox.process(step["event_id"]))
        else:
            steps.append(inbox.replay())
    return {"steps": steps}


def _check_revision(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
    if "expected_revision" in doc:
        return records.check_revision(doc["record_rev"], doc["expected_revision"])
    return records.check_revision(doc["record_rev"])


def _commitment_transfer(s: schemas.SchemaSet, doc: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "expected_revision" in doc:
        kwargs["expected_revision"] = doc["expected_revision"]
    return records.commitment_transfer(doc["commitment"], doc["new_owner"], doc["effects"], **kwargs).result


OPERATIONS: dict[str, Callable[[schemas.SchemaSet, Any], dict[str, Any]]] = {
    "append": _append_op("append"),
    "amend": _append_op("amend"),
    "delete": _append_op("delete"),
    "intake_sequence": _intake_sequence,
    "replay": _replay,
    "inbox_sequence": _inbox_sequence,
    "check_revision": _check_revision,
    "check_owner": lambda s, d: records.check_owner(d["session"], d["commitment"]),
    "commitment_transfer": _commitment_transfer,
    "operation_reuse": lambda s, d: records.operation_reuse(d["existing"], d["incoming"]),
    "check_message_size": lambda s, d: records.check_message_size(d),
    "combine": lambda s, d: records.combine(d["positions"], d["round"]),
    "restart": lambda s, d: effects.restart(d["effects"])[0],
    "reconcile": lambda s, d: effects.reconcile(d["effect"], d["lookup"], d["host_state"]),
    "dispatch": lambda s, d: effects.dispatch(d["effect"], d["prompt"], d["recovery_in_progress"]),
    "revalidate": lambda s, d: effects.revalidate(d["effect"], d["context"]),
    "check_mapping_coverage": lambda s, d: migration.check_mapping_coverage(
        d, s.documents[migration.COMMITMENT_SCHEMA]
    ),
}
"""Every non-``validate`` operation of schemas README §4, by name."""


def load_cases(schema_set: schemas.SchemaSet) -> list[dict[str, Any]]:
    """The case index, checked against ``fixtures/cases.schema.json`` and for unique ids."""
    cases = schema_set.load(CASES)
    pointers = schema_set.errors(cases, schemas.CASES_SCHEMA)
    if pointers:
        raise FixtureDefect(f"{CASES} does not validate against {schemas.CASES_SCHEMA}: {pointers}")
    seen: set[str] = set()
    for case in cases:
        if case["id"] in seen:
            raise FixtureDefect(f"case id {case['id']!r} appears twice")
        seen.add(case["id"])
        if (case["operation"] == "validate") != ("schema" in case):
            raise FixtureDefect(f"{case['id']}: `schema` must be present exactly for `validate`")
        if case["operation"] != "validate" and case["operation"] not in OPERATIONS:
            raise FixtureDefect(f"{case['id']}: unknown operation {case['operation']!r}")
    return cases


def run_case(schema_set: schemas.SchemaSet, case: Mapping[str, Any]) -> dict[str, Any]:
    """Run one case and return its result (schemas README §3, §4)."""
    operation = case["operation"]
    if operation == "validate":
        return schema_set.validate_file(case["input"], case["schema"])
    try:
        document = schema_set.load(case["input"])
    except schemas.StrictDecodeError as exc:
        raise FixtureDefect(f"{case['id']}: {case['input']}: {exc}") from exc
    pointers = schema_set.errors(document, f"{schemas.INPUTS_SCHEMA}#/$defs/{operation}")
    if pointers:
        raise FixtureDefect(
            f"{case['id']}: {case['input']} does not validate against inputs.schema.json "
            f"#/$defs/{operation}: {pointers}"
        )
    return OPERATIONS[operation](schema_set, document)


def run(schema_set: schemas.SchemaSet | None = None) -> dict[str, dict[str, Any]]:
    """Run every case; the results map ``{case id: result}``."""
    schema_set = schema_set or schemas.load()
    return {case["id"]: run_case(schema_set, case) for case in load_cases(schema_set)}


def mismatches(schema_set: schemas.SchemaSet, results: Mapping[str, Any]) -> list[str]:
    """Ids of the cases whose result differs from ``expected``, in index order."""
    return [c["id"] for c in load_cases(schema_set) if results.get(c["id"]) != c["expected"]]


def dumps(results: Mapping[str, Any]) -> str:
    """The results file text: keys sorted, 2-space indentation, trailing newline (schemas README §3)."""
    return json.dumps(results, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m odin_substrate.conformance",
        description="Run the I0 fixture cases and write the results file (schemas README §3).",
    )
    parser.add_argument("--out", help="results file to write (default: standard output)")
    parser.add_argument(
        "--schemas",
        help=f"schema directory (default: ${schemas.SCHEMAS_ENV} or substrate/schemas)",
    )
    args = parser.parse_args(argv)
    schema_set = schemas.load(args.schemas)
    results = run(schema_set)
    text = dumps(results)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    differing = mismatches(schema_set, results)
    print(
        f"{len(results)} cases; {len(differing)} differ from expected"
        + (": " + ", ".join(differing) if differing else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
