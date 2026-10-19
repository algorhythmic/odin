#!/usr/bin/env python3
"""Run Python contract checks without connecting to any service."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from odin.capabilities import inventory  # noqa: E402
from odin.contracts import Contracts, strict_loads  # noqa: E402
from odin.transitions import transition  # noqa: E402

contracts = Contracts()
inventory()
fixture_paths = [
    ROOT / "fixtures/contracts.json",
    *sorted((ROOT / "fixtures").glob("*-contracts.json")),
]
count = sum(contracts.fixtures(path) for path in fixture_paths)
contracts.validate(
    "examples", strict_loads((ROOT / "fixtures/examples.json").read_text())
)
transitions = strict_loads((ROOT / "fixtures/transitions.json").read_text())
contracts.validate("transitions", transitions)
for case in transitions["cases"]:
    if transition(case["kind"], case["input"]) != case["expected"]:
        raise AssertionError(case["name"])
for name, path in [
    ("capabilities", "fixture-capabilities.json"),
    ("evaluation-episode", "evaluation-episode.json"),
    ("evaluation-request", "synthetic-evaluation-request.json"),
    ("three-document", "three-document/manifest.json"),
    ("orchestration-config", "orchestration-config.json"),
    ("chirality-config", "chirality-config.json"),
    ("chirality-packet", "chirality-packet.json"),
    ("coordination-fixture", "coordination.json"),
    ("chirality-fixture", "chirality-responses.json"),
]:
    contracts.validate(name, strict_loads((ROOT / "fixtures" / path).read_text()))
coordination = strict_loads((ROOT / "fixtures/coordination.json").read_text())
for kind in ("grant", "handoff", "result"):
    contracts.validate("coordination-" + kind, coordination[kind])
responses = strict_loads((ROOT / "fixtures/chirality-responses.json").read_text())
for response in responses["examples"]:
    contracts.validate("chirality-response", response)
for path in (ROOT / "fixtures/profiles").glob("*.json"):
    contracts.validate("profile", strict_loads(path.read_text()))
print(
    f"PASS: Python validates {count} shared contract cases, {len(transitions['cases'])} transitions and all fixture files."
)
