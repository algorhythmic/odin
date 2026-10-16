"""Schema loading, strict decoding and validation (schemas README §2, §4.1).

The schema directory is ``substrate/schemas`` (found from this file, or
from the environment variable ``ODIN_SUBSTRATE_SCHEMAS``). Every
``*.schema.json`` file is registered locally under its ``$id`` in a
``referencing`` registry; nothing is fetched. Validation uses JSON Schema
2020-12 with one override: ``pattern``'s final ``$`` means end of string,
as in RE2, so it is replaced by ``\\Z`` (schemas README §2, "Pattern
dialect").
"""

from __future__ import annotations

import functools
import json
import os
import re
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import jsonschema
import jsonschema.validators
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .kinds import KindCatalogue
from .namespaces import NamespaceCatalogue

SCHEMAS_ENV = "ODIN_SUBSTRATE_SCHEMAS"
"""Environment variable that overrides the schema directory."""

ENVELOPE_SCHEMA = "envelope.schema.json"
INPUTS_SCHEMA = "fixtures/inputs.schema.json"
CASES_SCHEMA = "fixtures/cases.schema.json"

SCHEMA_VALID = "schema_valid"
SCHEMA_INVALID = "schema_invalid"
UNKNOWN_KIND = "unknown_kind"


def default_schema_dir() -> Path:
    """The schema directory: ``$ODIN_SUBSTRATE_SCHEMAS`` or ``substrate/schemas`` beside this package."""
    override = os.environ.get(SCHEMAS_ENV)
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2] / "schemas"


# --------------------------------------------------------------------------
# Strict decoding (schemas README §4.1 step 1)
# --------------------------------------------------------------------------


class StrictDecodeError(ValueError):
    """The text is not strict JSON (malformed, not UTF-8, or a non-finite number)."""


class DuplicateKeyError(StrictDecodeError):
    """The document has a duplicate object key; ``pointers`` locate each duplicated key."""

    def __init__(self, pointers: list[str]) -> None:
        self.pointers = pointers
        super().__init__("duplicate keys at " + ", ".join(repr(p) for p in pointers))


class _Object(dict):
    """A decoded object that remembers which of its keys appeared more than once."""

    __slots__ = ("duplicates",)


def _object_pairs(pairs: list[tuple[str, Any]]) -> _Object:
    obj = _Object()
    duplicates: list[str] = []
    for key, value in pairs:
        if key in obj and key not in duplicates:
            duplicates.append(key)
        obj[key] = value
    obj.duplicates = duplicates
    return obj


def _reject_constant(name: str) -> Any:
    raise StrictDecodeError(f"non-standard JSON constant {name}")


def escape_token(token: object) -> str:
    """Escape one JSON-pointer reference token (RFC 6901: ``~`` → ``~0``, ``/`` → ``~1``)."""
    return str(token).replace("~", "~0").replace("/", "~1")


def to_pointer(path: Iterable[object]) -> str:
    """The RFC 6901 pointer of ``path``; the document root is ``""``."""
    return "".join("/" + escape_token(token) for token in path)


def _strip(value: Any, path: list[object], found: list[str]) -> Any:
    """Convert decoded objects to plain dicts, collecting duplicate-key pointers."""
    if isinstance(value, _Object):
        for key in value.duplicates:
            found.append(to_pointer([*path, key]))
        return {k: _strip(v, [*path, k], found) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip(v, [*path, i], found) for i, v in enumerate(value)]
    return value


def loads_strict(text: str | bytes) -> Any:
    """Decode JSON strictly (schemas README §4.1 step 1).

    Bytes must be UTF-8. ``NaN`` and ``Infinity`` are refused. A duplicate
    key anywhere raises :class:`DuplicateKeyError` with the sorted pointers
    of the duplicated keys (for example ``/kind``).
    """
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StrictDecodeError(f"not UTF-8: {exc}") from exc
    try:
        raw = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise StrictDecodeError(str(exc)) from exc
    found: list[str] = []
    value = _strip(raw, [], found)
    if found:
        raise DuplicateKeyError(sorted(set(found)))
    return value


def load_strict(path: str | os.PathLike[str]) -> Any:
    """Read and strictly decode the JSON file at ``path``."""
    return loads_strict(Path(path).read_bytes())


# --------------------------------------------------------------------------
# Validator: Draft 2020-12 with the pattern override (schemas README §2)
# --------------------------------------------------------------------------


def anchor_end(pattern: str) -> str:
    """Replace a final unescaped ``$`` with ``\\Z`` so it matches only at end of string."""
    if pattern.endswith("$"):
        body = pattern[:-1]
        backslashes = len(body) - len(body.rstrip("\\"))
        if backslashes % 2 == 0:
            return body + r"\Z"
    return pattern


@functools.lru_cache(maxsize=None)
def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(anchor_end(pattern))


def _pattern_keyword(validator: Any, pattern: str, instance: Any, schema: Any) -> Iterator[ValidationError]:
    if validator.is_type(instance, "string") and not _compile(pattern).search(instance):
        yield ValidationError(f"{instance!r} does not match {pattern!r}")


Validator = jsonschema.validators.extend(Draft202012Validator, {"pattern": _pattern_keyword})
"""Draft 2020-12 validator whose ``pattern`` treats a final ``$`` as end of string."""

# Registered for the 2020-12 metaschema so that subschemas reached through
# ``$ref`` (which declare ``$schema``) are also validated by this class
# (schemas README §2). This replaces the stock class for 2020-12 schemas in
# this process.
jsonschema.validators.validates("draft2020-12")(Validator)


# --------------------------------------------------------------------------
# Error pointers (schemas README §4.1 step 2)
# --------------------------------------------------------------------------


def _unknown_keys(error: ValidationError) -> list[str]:
    schema = error.schema if isinstance(error.schema, Mapping) else {}
    properties = schema.get("properties", {})
    patterns = schema.get("patternProperties", {})
    instance = error.instance if isinstance(error.instance, Mapping) else {}
    return [
        key
        for key in instance
        if key not in properties and not any(_compile(p).search(key) for p in patterns)
    ]


def error_pointers(errors: Iterable[ValidationError]) -> list[str]:
    """The sorted, de-duplicated pointer set of schemas README §4.1 step 2.

    ``errors`` are the top-level errors of ``iter_errors()``, which are
    already flattened through ``$ref``, ``allOf``, ``properties``, ``items``
    and ``if``/``then`` and stop at ``anyOf``, ``oneOf``, ``not`` and
    ``contains``. An unknown key reports the key's own pointer; a missing
    required key reports the missing key's pointer; every other error
    reports the location of the failing value.
    """
    pointers: set[str] = set()
    for error in errors:
        path = list(error.absolute_path)
        if error.validator == "additionalProperties":
            keys = _unknown_keys(error)
            pointers.update(to_pointer([*path, k]) for k in keys)
            if keys:
                continue
        elif error.validator == "required":
            instance = error.instance if isinstance(error.instance, Mapping) else {}
            missing = [k for k in error.validator_value if k not in instance]
            pointers.update(to_pointer([*path, k]) for k in missing)
            if missing:
                continue
        pointers.add(to_pointer(path))
    return sorted(pointers)


# --------------------------------------------------------------------------
# The schema set
# --------------------------------------------------------------------------


class SchemaSet:
    """Every schema and catalogue of one schema directory, registered under its ``$id``.

    Construction checks each schema against the 2020-12 metaschema and the
    two catalogues against their schemas, so a defect in the contract fails
    loudly rather than as a case outcome.
    """

    def __init__(self, directory: str | os.PathLike[str] | None = None) -> None:
        self.directory = Path(directory).resolve() if directory is not None else default_schema_dir()
        if not self.directory.is_dir():
            raise FileNotFoundError(f"schema directory not found: {self.directory}")
        self.documents: dict[str, dict[str, Any]] = {}
        self.ids: dict[str, str] = {}
        resources: list[tuple[str, Resource[Any]]] = []
        for path in sorted(self.directory.rglob("*.schema.json")):
            rel = path.relative_to(self.directory).as_posix()
            schema = load_strict(path)
            Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str) or schema_id in self.ids.values():
                raise ValueError(f"{rel}: missing or repeated $id")
            self.documents[rel] = schema
            self.ids[rel] = schema_id
            resources.append((schema_id, DRAFT202012.create_resource(schema)))
        self.registry: Registry[Any] = Registry().with_resources(resources).crawl()
        self._validators: dict[str, Any] = {}
        self.kinds = KindCatalogue(self._load_checked("kinds.json", "kinds.schema.json"))
        self.namespaces = NamespaceCatalogue(
            self._load_checked("namespaces.json", "namespaces.schema.json")
        )

    def _load_checked(self, rel: str, schema_rel: str) -> Any:
        document = self.load(rel)
        pointers = self.errors(document, schema_rel)
        if pointers:
            raise ValueError(f"{rel} does not validate against {schema_rel}: {pointers}")
        return document

    def path(self, rel: str) -> Path:
        """The absolute path of ``rel`` (relative to the schema directory)."""
        return self.directory / rel

    def load(self, rel: str) -> Any:
        """Strictly decode the JSON file ``rel`` (relative to the schema directory)."""
        return load_strict(self.path(rel))

    def validator(self, target: str) -> Any:
        """A validator for a schema file (``records/effect.schema.json``) or a fragment of one
        (``fixtures/inputs.schema.json#/$defs/reconcile``)."""
        cached = self._validators.get(target)
        if cached is not None:
            return cached
        rel, _, fragment = target.partition("#")
        if rel not in self.ids:
            raise KeyError(f"no schema {rel!r} in {self.directory}")
        if fragment:
            schema: Any = {"$ref": f"{self.ids[rel]}#{fragment}"}
        else:
            schema = self.documents[rel]
        validator = Validator(schema, registry=self.registry)
        self._validators[target] = validator
        return validator

    def errors(self, instance: Any, target: str) -> list[str]:
        """The pointer set (schemas README §4.1 step 2) of ``instance`` against ``target``; empty when valid."""
        return error_pointers(self.validator(target).iter_errors(instance))

    def validate_instance(self, instance: Any, schema_rel: str) -> dict[str, Any]:
        """Steps 2 to 4 of schemas README §4.1 for an already decoded document."""
        pointers = self.errors(instance, schema_rel)
        if pointers:
            return {"outcome": SCHEMA_INVALID, "errors": pointers}
        if schema_rel == ENVELOPE_SCHEMA and instance["kind"] not in self.kinds:
            return {"outcome": UNKNOWN_KIND}
        return {"outcome": SCHEMA_VALID}

    def validate_text(self, text: str | bytes, schema_rel: str) -> dict[str, Any]:
        """The ``validate`` operation of schemas README §4.1: decode strictly, validate, check the catalogue.

        Raises :class:`StrictDecodeError` (not :class:`DuplicateKeyError`)
        when the text is not JSON at all: I0 defines no outcome for that.
        """
        try:
            instance = loads_strict(text)
        except DuplicateKeyError as exc:
            return {"outcome": SCHEMA_INVALID, "errors": exc.pointers}
        return self.validate_instance(instance, schema_rel)

    def validate_file(self, rel: str, schema_rel: str) -> dict[str, Any]:
        """:meth:`validate_text` on the file ``rel`` (relative to the schema directory)."""
        return self.validate_text(self.path(rel).read_bytes(), schema_rel)


@functools.lru_cache(maxsize=None)
def _load(directory: Path) -> SchemaSet:
    return SchemaSet(directory)


def load(directory: str | os.PathLike[str] | None = None) -> SchemaSet:
    """The (cached) :class:`SchemaSet` of ``directory``, by default :func:`default_schema_dir`."""
    return _load(Path(directory).resolve() if directory is not None else default_schema_dir())
