#!/usr/bin/env python3
"""Run both I0 implementations and require matching shared-fixture verdicts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"{' '.join(command)} failed ({result.returncode})\n"
                           f"{result.stdout}{result.stderr}")
    return result.stdout


def verdicts(output: str) -> dict[str, dict]:
    result = {}
    for line in output.splitlines():
        value = json.loads(line)
        name = value.get("name")
        if not isinstance(name, str) or name in result or value.get("pass") is not True:
            raise ValueError(f"invalid, duplicate or failing fixture verdict: {value}")
        result[name] = value
    if not result:
        raise ValueError("fixture command returned no verdicts")
    return result


def expected_names(filename: str) -> set[str]:
    manifest = json.loads((ROOT / "runtime/fixtures/v1" / filename).read_text())
    names = [case["name"] for case in manifest["cases"]]
    if not names or len(names) != len(set(names)):
        raise ValueError(f"empty or duplicate names in {filename}")
    return set(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--go", default="go")
    args = parser.parse_args()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "runtime/python")
    try:
        run([args.python, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=ROOT / "runtime/python", env=env)
        print("PASS: Python runtime contract tests")
        run([args.go, "test", "./..."], cwd=ROOT / "runtime/go", env=env)
        print("PASS: Go runtime contract tests")
        with tempfile.TemporaryDirectory(prefix="odin-runtime-check-") as temporary:
            binary = Path(temporary) / "validate"
            run([args.go, "build", "-o", str(binary), "./cmd/validate"],
                cwd=ROOT / "runtime/go", env=env)
            python_result = verdicts(run([args.python, "-m", "odin_runtime", "fixtures"],
                                         cwd=ROOT, env=env))
            go_result = verdicts(run([str(binary), "--fixtures"], cwd=ROOT, env=env))
            if set(python_result) != expected_names("cases.json"):
                raise ValueError("schema verdicts do not cover the shared manifest")
            if python_result != go_result:
                different = sorted(name for name in python_result.keys() | go_result.keys()
                                   if python_result.get(name) != go_result.get(name))
                raise ValueError(f"Go/Python fixture results differ: {different}")
            print(f"PASS: Go/Python parity for {len(python_result)} shared schema fixtures")
            python_semantics = verdicts(run([args.python, "-m", "odin_runtime", "semantics"],
                                            cwd=ROOT, env=env))
            go_semantics = verdicts(run([str(binary), "--semantics"], cwd=ROOT, env=env))
            if set(python_semantics) != expected_names("semantics.json"):
                raise ValueError("semantic verdicts do not cover the shared manifest")
            if python_semantics != go_semantics:
                different = sorted(name for name in python_semantics.keys() | go_semantics.keys()
                                   if python_semantics.get(name) != go_semantics.get(name))
                raise ValueError(f"Go/Python semantic results differ: {different}")
            print(f"PASS: Go/Python parity for {len(python_semantics)} shared semantic fixtures")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Runtime contract validation FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
