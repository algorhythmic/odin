#!/usr/bin/env python3
"""Validate the documentation handoff using only this checkout and Python stdlib."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        ERRORS.append(f"{path.relative_to(ROOT)}: {exc}")
        return {}


def validate_schema(value, schema: dict, where: str) -> None:
    """Validate the small JSON Schema vocabulary used by our metadata schemas."""
    types = schema.get("type", [])
    types = [types] if isinstance(types, str) else types
    predicates = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: type(x) is int,
        "boolean": lambda x: type(x) is bool,
        "null": lambda x: x is None,
    }
    if types and not any(predicates[t](value) for t in types):
        ERRORS.append(f"{where}: expected {types}")
        return
    if "const" in schema:
        check(value == schema["const"] and type(value) is type(schema["const"]), f"{where}: wrong constant")
    if "enum" in schema:
        check(value in schema["enum"], f"{where}: invalid enum value")
    if isinstance(value, str):
        check(len(value) >= schema.get("minLength", 0), f"{where}: string too short")
        if "pattern" in schema:
            check(bool(re.search(schema["pattern"], value)), f"{where}: invalid format")
        if schema.get("format") == "date-time":
            try:
                check(datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None,
                      f"{where}: timezone missing")
            except ValueError:
                ERRORS.append(f"{where}: invalid date-time")
    if isinstance(value, list):
        check(len(value) >= schema.get("minItems", 0), f"{where}: too few items")
        for i, item in enumerate(value):
            validate_schema(item, schema.get("items", {}), f"{where}[{i}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            check(key in value, f"{where}: missing {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            check(not (value.keys() - properties.keys()), f"{where}: unknown properties {value.keys() - properties.keys()}")
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], f"{where}.{key}")


def links(text: str):
    # Fence contents and inline code are examples, not Markdown links.
    text = re.sub(r"^```.*?^```[^\n]*", "", text, flags=re.M | re.S)
    text = re.sub(r"`[^`\n]+`", "", text)
    yield from re.findall(r"\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)", text)
    yield from re.findall(r"^\s*\[[^\]]+\]:\s*<?([^\s>]+)", text, re.M)


def anchors(path: Path) -> set[str]:
    text = path.read_text()
    found = set(re.findall(r'\b(?:id|name)=["\']([^"\']+)["\']', text))
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        heading = re.sub(r"<[^>]+>", "", heading).lower()
        slug = "".join(c for c in heading if c in "-_ " or unicodedata.category(c)[0] not in "PS")
        slug = slug.replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(f"{slug}-{count}" if count else slug)
    return found


def main() -> int:
    manifest = read_json(ROOT / "docs/provenance/EXTRACTION-MANIFEST.json")
    validate_schema(manifest, read_json(ROOT / "docs/provenance/EXTRACTION-MANIFEST.schema.json"), "manifest")
    check(manifest.get("schema_version") == 1, "manifest schema_version must be 1")
    for key in ("snapshot_id", "source_repository", "source_commit", "captured_at", "files"):
        check(bool(manifest.get(key)), f"manifest missing {key}")
    check(bool(re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_commit", ""))), "invalid source commit")
    records = manifest.get("files", [])
    seen = set()
    snapshots = set()
    for entry in records:
        source = entry.get("source_path", "")
        check(bool(source) and source not in seen, f"duplicate/missing source path: {source}")
        seen.add(source)
        check(entry.get("source_status") == "clean" and entry.get("dirty") is False and entry.get("untracked") is False,
              f"unexpected source status: {source}")
        snapshot = ROOT / entry.get("snapshot_path", "")
        check(snapshot.is_file(), f"missing snapshot: {source}")
        snapshots.add(snapshot)
        if snapshot.is_file():
            check(sha(snapshot) == entry.get("source_sha256"), f"snapshot digest mismatch: {source}")
        check(entry.get("treatment") in {"exact", "adapted", "split", "reference"}, f"bad treatment: {source}")
        destination = entry.get("destination_path")
        if destination:
            path = ROOT / destination
            check(path.is_file(), f"missing destination: {destination}")
            if path.is_file():
                check(sha(path) == entry.get("adapted_output_sha256"), f"output digest mismatch: {destination}")
        check(bool(entry.get("transformation")), f"missing transformation record: {source}")
    snapshot_root = ROOT / "docs/history/saga-extraction" / manifest.get("snapshot_id", "missing")
    actual = {p for p in snapshot_root.rglob("*") if p.is_file()}
    check(actual == snapshots, "snapshot file allowlist mismatch")

    required = ["README.md", "AGENTS.md", "CLAUDE.md", "docs/README.md", "docs/DECISIONS.md", "docs/ROADMAP.md",
                "docs/provenance/DECISION-MAP.md", "docs/provenance/LEGACY-REQUIREMENTS.md",
                "docs/provenance/HANDOFF.md", "docs/contracts/README.md"]
    for relative in required:
        check((ROOT / relative).is_file(), f"required document missing: {relative}")
    mapping_path = ROOT / "docs/provenance/DECISION-MAP.md"
    mapping = mapping_path.read_text() if mapping_path.is_file() else ""
    for n in range(25):
        check(bool(re.search(rf"SAGA-2026-10-D{n}(?!\d)", mapping)), f"missing decision mapping D{n}")
    design_names = ["ODIN-IO-CONTRACT.md", "ODIN-IMPLEMENTATION-BLUEPRINT.md",
                    "ODIN-ECOSYSTEM-INTEGRATION.md", "ODIN-ACCEPTANCE-SCENARIOS.md"]
    source_text = "\n".join((snapshot_root / "docs/design" / name).read_text() for name in design_names)
    live_text = "\n".join((ROOT / "docs/design" / name).read_text() for name in design_names)
    ids = lambda text: set(re.findall(r"\b(?:AC|DC|EC)-\d{2}\b", text))
    check(ids(source_text) <= ids(live_text), f"lost acceptance identifiers: {sorted(ids(source_text) - ids(live_text))}")
    for prefix, count in (("AC", 30), ("DC", 8), ("EC", 12)):
        for n in range(1, count + 1):
            check(f"{prefix}-{n:02}" in ids(live_text), f"missing {prefix}-{n:02}")

    pins = list((ROOT / "docs/contracts/saga").glob("*/SNAPSHOT.json"))
    check(bool(pins), "no pinned Saga contract metadata")
    for pin in pins:
        meta = read_json(pin)
        validate_schema(meta, read_json(ROOT / "docs/contracts/SNAPSHOT.schema.json"), "producer snapshot")
        check(meta.get("producer_repository") == "saga", f"bad producer: {pin}")
        check(bool(meta.get("producer_path")) and bool(meta.get("status")), f"incomplete pin metadata: {pin}")
        contract = pin.parent / "SAGA-SERVICE.md"
        check(contract.is_file(), "pinned Saga contract missing")
        if contract.is_file():
            check(sha(contract) == meta.get("sha256"), "pinned Saga contract digest mismatch")

    checked = 0
    for path in sorted(ROOT.rglob("*.md")):
        relative = path.relative_to(ROOT)
        if ".git" in relative.parts or path in snapshots or str(relative).startswith("docs/research/"):
            continue  # Frozen and dated research links are inventoried in the historical wrapper.
        checked += 1
        for target in links(path.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            if parsed.path.startswith("/"):
                ERRORS.append(f"nonportable absolute link: {relative}: {target}")
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            check(resolved.is_relative_to(ROOT), f"sibling dependency: {relative}: {target}")
            check(resolved.exists(), f"broken link: {relative}: {target}")
            if parsed.fragment and resolved.is_file() and resolved.suffix == ".md":
                check(unquote(parsed.fragment) in anchors(resolved), f"missing anchor: {relative}: {target}")
    if ERRORS:
        print("Documentation validation FAILED:")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    print(f"PASS: {len(records)} frozen files, source/output hashes, D0–D24 mapping presence, "
          f"AC/DC/EC preservation, {len(pins)} producer pin(s), and local links in {checked} live documents.")
    print("This checks documentation integrity, not semantic completeness or runtime behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
