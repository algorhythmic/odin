#!/usr/bin/env python3
"""Compare the Go and Python conformance results with the fixture expectations.

Usage: compare_conformance.py CASES GO_RESULTS PYTHON_RESULTS

Each results file maps a case id to the outcome object that implementation
produced for that case. The comparison is exact against the ``expected``
object of each case in ``cases.json`` and between the two implementations.
Standard library only. Exit status 1 on any difference or missing case.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__.strip())
        return 2
    cases = load(argv[1])
    results = {"go": load(argv[2]), "python": load(argv[3])}
    expected = {case["id"]: case["expected"] for case in cases}
    groups = Counter(case["group"] for case in cases)
    problems: list[str] = []

    for case_id, want in expected.items():
        for name, got in results.items():
            if case_id not in got:
                problems.append(f"{case_id}: missing from {name} results")
            elif got[case_id] != want:
                problems.append(
                    f"{case_id}: {name} produced {json.dumps(got[case_id], sort_keys=True)}; "
                    f"expected {json.dumps(want, sort_keys=True)}"
                )
    for name, got in results.items():
        for extra in sorted(set(got) - set(expected)):
            problems.append(f"{extra}: reported by {name} but not a fixture case")
    for case_id in expected:
        a, b = results["go"].get(case_id), results["python"].get(case_id)
        if a is not None and b is not None and a != b:
            problems.append(f"{case_id}: Go and Python disagree")

    if problems:
        print("Conformance comparison FAILED:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    summary = ", ".join(f"{group} {count}" for group, count in sorted(groups.items()))
    print(f"PASS: {len(expected)} cases agree across Go, Python and the expectations ({summary}).")
    print("This is I0 fixture-only evidence: no service, store, backend or peer API is exercised.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
