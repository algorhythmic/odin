"""`python -m odin_runtime` I0 validation entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .contracts import check_ownership, check_revision, classify_intake, reconcile_operation
from .validation import SchemaValidator, StrictJSONError, load_json_strict


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMAS = ROOT / "runtime/schemas/v1"
DEFAULT_FIXTURES = ROOT / "runtime/fixtures/v1"


def _emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _case_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("fixture file must be a nonempty relative path")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise ValueError(f"fixture file outside fixture root or missing: {relative}")
    return candidate


def _schema_integer(value: object) -> int:
    """JSON Schema accepts 2.0 as an integer; typed helpers take Python ints."""
    if type(value) is int:
        return value
    if type(value) is float and value.is_integer():
        return int(value)
    raise ValueError(f"semantic fixture has a noninteger value: {value!r}")


def _optional_schema_integer(value: object) -> int | None:
    return None if value is None else _schema_integer(value)


def run_fixtures(validator: SchemaValidator, fixture_root: Path) -> int:
    manifest = load_json_strict(fixture_root / "cases.json")
    if not validator.validate("cases.schema.json", manifest):
        raise ValueError("fixture manifest does not match cases.schema.json")
    assert isinstance(manifest, dict)
    failures = 0
    for case in manifest["cases"]:
        actual = validator.validate_file(case["schema"], _case_file(fixture_root, case["file"]))
        expected = case["valid"]
        passed = actual == expected
        _emit({"name": case["name"], "actual_valid": actual,
               "expected_valid": expected, "pass": passed})
        failures += not passed
    return 1 if failures else 0


def run_semantics(validator: SchemaValidator, fixture_root: Path) -> int:
    manifest = load_json_strict(fixture_root / "semantics.json")
    if not validator.validate("semantics.schema.json", manifest):
        raise ValueError("semantic fixture manifest does not match semantics.schema.json")
    assert isinstance(manifest, dict)
    failures = 0
    for case in manifest["cases"]:
        operation, arguments = case["operation"], case["input"]
        if operation == "intake":
            actual = classify_intake(_optional_schema_integer(arguments["last_sequence"]),
                                     _optional_schema_integer(arguments["incoming_sequence"]),
                                     arguments["dedupe_seen"])
        elif operation == "revision":
            actual = check_revision(_schema_integer(arguments["expected"]),
                                    _schema_integer(arguments["actual"]))
        elif operation == "owner":
            actual = check_ownership(_schema_integer(arguments["expected_generation"]),
                                     _schema_integer(arguments["actual_generation"]))
        elif operation == "reconcile":
            state, action = reconcile_operation(arguments["status"])
            actual = {"state": state, "action": action}
        else:
            raise ValueError(f"unknown semantic fixture operation: {operation}")
        expected = case["expected"]
        passed = actual == expected
        _emit({"name": case["name"], "actual": actual, "expected": expected, "pass": passed})
        failures += not passed
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Odin I0 JSON records and shared fixtures")
    parser.add_argument("--schemas", type=Path, default=DEFAULT_SCHEMAS, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--schema", required=True)
    validate.add_argument("path", type=Path)
    fixtures = commands.add_parser("fixtures")
    fixtures.add_argument("--root", type=Path, default=DEFAULT_FIXTURES, help=argparse.SUPPRESS)
    semantics = commands.add_parser("semantics")
    semantics.add_argument("--root", type=Path, default=DEFAULT_FIXTURES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        validator = SchemaValidator(args.schemas)
        if args.command == "validate":
            valid = validator.validate_file(args.schema, args.path)
            _emit({"valid": valid})
            return 0 if valid else 1
        if args.command == "fixtures":
            return run_fixtures(validator, args.root)
        return run_semantics(validator, args.root)
    except (OSError, StrictJSONError, ValueError) as exc:
        _emit({"error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
