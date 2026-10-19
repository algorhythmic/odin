"""Validated capability evidence inventory, never a runtime permission grant."""

from .contracts import ROOT, Contracts, strict_loads


def inventory():
    value = strict_loads((ROOT / "fixtures/capability-inventory.json").read_text())
    Contracts().validate("capability-inventory", value)
    names = set()
    for entry in value["capabilities"]:
        if entry["id"] in names:
            raise ValueError("duplicate capability")
        names.add(entry["id"])
        for path in entry["evidence"]:
            target = (ROOT / path).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError("missing local capability evidence")
    return value
