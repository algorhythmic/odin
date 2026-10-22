"""Strict JSON and local Draft 2020-12 schema validation for I0 fixtures."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012


BASE_URI = "https://odin.invalid/schemas/v1/"
UTC_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
ULID = re.compile(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$")
MAX_SAFE_INTEGER = 2**53 - 1


class StrictJSONError(ValueError):
    """The input is not interoperable JSON (including duplicate keys)."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-JSON numeric constant: {value}")


def _safe_int(value: str) -> int:
    parsed = int(value)
    if abs(parsed) > MAX_SAFE_INTEGER:
        raise StrictJSONError(f"JSON integer exceeds interoperable range: {value}")
    return parsed


def _safe_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or abs(parsed) > MAX_SAFE_INTEGER:
        raise StrictJSONError(f"JSON number exceeds interoperable range: {value}")
    if Decimal(value) != Decimal(str(parsed)):
        raise StrictJSONError(f"JSON number loses precision: {value}")
    return parsed


def _check_unicode_scalars(value: object) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise StrictJSONError("unpaired Unicode surrogate in JSON string")
    elif isinstance(value, list):
        for item in value:
            _check_unicode_scalars(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_unicode_scalars(key)
            _check_unicode_scalars(item)


def load_json_strict(path: Path) -> object:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant, parse_int=_safe_int,
                           parse_float=_safe_float)
        _check_unicode_scalars(value)
        return value
    except (UnicodeError, OSError, json.JSONDecodeError) as exc:
        raise StrictJSONError(f"invalid JSON in {path}: {exc}") from exc


def valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not UTC_TIMESTAMP.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc


def valid_ulid(value: object) -> bool:
    return isinstance(value, str) and bool(ULID.fullmatch(value)) and value != "0" * 26


FORMAT_CHECKER = FormatChecker()
FORMAT_CHECKER.checks("date-time")(valid_utc_timestamp)
FORMAT_CHECKER.checks("utc-date-time")(valid_utc_timestamp)
FORMAT_CHECKER.checks("ulid")(valid_ulid)


def _schema_references(node: object):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"$ref", "$dynamicRef", "$id"} and isinstance(value, str):
                yield value
            else:
                yield from _schema_references(value)
    elif isinstance(node, list):
        for item in node:
            yield from _schema_references(item)


def _no_remote_retrieval(uri: str):
    raise NoSuchResource(ref=uri)


class SchemaValidator:
    """Validate against only schemas physically present in one local directory."""

    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir.resolve()
        self.schemas: dict[str, object] = {}
        for path in sorted(self.schema_dir.glob("*.schema.json")):
            self.schemas[path.name] = load_json_strict(path)
        if not self.schemas:
            raise ValueError(f"no schemas found in {self.schema_dir}")
        for filename, schema in self.schemas.items():
            if not isinstance(schema, dict):
                raise ValueError(f"schema must be an object: {filename}")
            Draft202012Validator.check_schema(schema)
            for reference in _schema_references(schema):
                absolute = urljoin(BASE_URI + filename, reference)
                parsed = urlsplit(absolute)
                target = unquote(parsed.path.removeprefix(urlsplit(BASE_URI).path))
                if (parsed.scheme != "https" or parsed.netloc != "odin.invalid"
                        or not parsed.path.startswith(urlsplit(BASE_URI).path)
                        or target not in self.schemas):
                    raise ValueError(f"nonlocal schema reference in {filename}: {reference}")
        registry = Registry(retrieve=_no_remote_retrieval)
        for filename, schema in self.schemas.items():
            registry = registry.with_resource(BASE_URI + filename,
                                              Resource.from_contents(schema, default_specification=DRAFT202012))
        self.registry = registry

    def validate(self, schema_name: str, instance: object) -> bool:
        if schema_name not in self.schemas:
            raise ValueError(f"unknown local schema: {schema_name}")
        validator = Draft202012Validator(self.schemas[schema_name], registry=self.registry,
                                         format_checker=FORMAT_CHECKER)
        return validator.is_valid(instance)

    def validate_file(self, schema_name: str, path: Path) -> bool:
        if schema_name not in self.schemas:
            raise ValueError(f"unknown local schema: {schema_name}")
        try:
            instance = load_json_strict(path)
        except StrictJSONError:
            return False
        return self.validate(schema_name, instance)
