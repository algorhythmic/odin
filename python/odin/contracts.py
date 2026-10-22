"""Validate versioned, closed runtime records before they reach storage."""

from __future__ import annotations

import json
import re
import secrets
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
# A deployed copy (ODIN-ADR-039) carries this marker, naming the commit it was
# exported from and the repository the executive works in. ROOT is only where
# the code runs from; REPOSITORY_ROOT is the executive's checkout. Without a
# marker they are the same directory, as before.
DEPLOYMENT_FILE = ".odin-deployment.json"
_REVISION = re.compile(r"[0-9a-f]{40}")


def deployment(root):
    """The validated deployment marker in ``root``, or None; raises when invalid."""
    path = Path(root) / DEPLOYMENT_FILE
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    repository = value.get("repository") if isinstance(value, dict) else None
    if (not isinstance(value, dict) or value.get("schema_version") != 1 or
            set(value) != {"schema_version", "revision", "repository", "exported_at"} or
            not isinstance(value.get("revision"), str) or not _REVISION.fullmatch(value["revision"]) or
            not isinstance(repository, str) or not repository.startswith("/") or
            str(Path(repository)) != repository or not isinstance(value.get("exported_at"), str)):
        raise ValueError(f"invalid deployment marker in {root}")
    return value


DEPLOYMENT = deployment(ROOT)
REPOSITORY_ROOT = Path(DEPLOYMENT["repository"]) if DEPLOYMENT else ROOT
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=ValueError)
def utc_timestamp(value):
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", value):
        return False
    datetime.fromisoformat(value)
    return True


def identifier() -> str:
    value = (time.time_ns() // 1_000_000 << 80) | secrets.randbits(80)
    result = ""
    for _ in range(26):
        result = ALPHABET[value & 31] + result
        value >>= 5
    return result


def canonical(value) -> str:
    # Odin-local encoding only; never asserts Saga's undecided wire digest.
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def strict_loads(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"non-JSON number: {value}")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    canonical(value)
    return value


@lru_cache(maxsize=8)
def _validators(directory):
    validators = {}
    for path in directory.glob("*.schema.json"):
        schema = strict_loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        validators[path.name.removesuffix(".schema.json")] = Draft202012Validator(
            schema, format_checker=FORMATS
        )
    return validators


class Contracts:
    def __init__(self, directory: Path | None = None):
        # Schemas are immutable for a process lifetime; restart after editing them.
        self.validators = _validators((directory or ROOT / "schemas").resolve())

    def validate(self, name: str, value) -> None:
        canonical(value)  # Reject NaN/Infinity even when passed as Python values.
        self.validators[name].validate(value)

    def validate_definition(self, name: str, definition: str, value) -> None:
        """Validate against one self-contained `$defs` entry of a schema."""
        canonical(value)
        fragment = self.validators[name].schema["$defs"][definition]
        Draft202012Validator(fragment, format_checker=FORMATS).validate(value)

    def fixtures(self, path: Path) -> int:
        data = strict_loads(path.read_text())
        self.validate("fixtures", data)
        names = set()
        for case in data["cases"]:
            if case["name"] in names:
                raise ValueError(f"duplicate fixture: {case['name']}")
            names.add(case["name"])
            valid = self.validators[case["schema"]].is_valid(case["value"])
            if valid != case["valid"]:
                raise AssertionError(f"fixture disagrees: {case['name']}")
        return len(names)
