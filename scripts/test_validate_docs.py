"""Regression tests for the documentation handoff validator."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]
SCENARIOS = Path("docs/design/ODIN-ACCEPTANCE-SCENARIOS.md")
MANIFEST = Path("docs/provenance/EXTRACTION-MANIFEST.json")


class DocumentationValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="odin-doc-validator-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "odin"
        shutil.copytree(SOURCE, self.root, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", "node_modules", ".playwright-browsers",
            "dist", "test-results", "playwright-report"))

    def edit(self, relative: Path, transform) -> None:
        path = self.root / relative
        path.write_text(transform(path.read_text()))

    def validate(self) -> subprocess.CompletedProcess[str]:
        # Concurrent prose edits in the source checkout can leave its output
        # digests stale. Each isolated copy records its own current outputs.
        manifest_path = self.root / MANIFEST
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest["files"]:
            destination = entry.get("destination_path")
            if destination:
                entry["adapted_output_sha256"] = hashlib.sha256((self.root / destination).read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        return subprocess.run(
            ["python3", "scripts/validate_docs.py"],
            cwd=self.root, text=True, capture_output=True, check=False,
        )

    def assert_fails_with(self, result: subprocess.CompletedProcess[str], message: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(message, result.stdout)

    def test_unchanged_standalone_checkout_passes(self) -> None:
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_removed_added_id_cannot_disappear_from_all_live_documents(self) -> None:
        for path in (self.root / "docs").rglob("*.md"):
            if "history" in path.parts or "contracts" in path.parts:
                continue
            path.write_text(path.read_text().replace("AC-41", "scenario 41"))
        self.assert_fails_with(self.validate(), "expected one defining row for AC-41, found 0")

    def test_removed_id_from_registry_and_documents_still_fails(self) -> None:
        for path in (self.root / "docs").rglob("*.md"):
            if "history" in path.parts or "contracts" in path.parts:
                continue
            path.write_text(path.read_text().replace("AC-41", "scenario 41"))
        registry_path = self.root / "docs/provenance/STABLE-IDS.json"
        registry = json.loads(registry_path.read_text())
        registry["groups"]["AC"]["ids"] = [
            entry for entry in registry["groups"]["AC"]["ids"] if entry["id"] != "AC-41"
        ]
        registry_path.write_text(json.dumps(registry, indent=2) + "\n")
        self.assert_fails_with(self.validate(), "missing baseline registry IDs: ['AC-41']")

    def test_reference_does_not_replace_definition(self) -> None:
        self.edit(SCENARIOS, lambda text: "\n".join(
            line for line in text.split("\n") if not line.startswith("| AC-41 |")))
        self.assertIn("AC-41", (self.root / SCENARIOS).read_text())
        self.assert_fails_with(self.validate(), "expected one defining row for AC-41, found 0")

    def test_withdrawn_id_still_requires_defining_row(self) -> None:
        self.edit(SCENARIOS, lambda text: "\n".join(
            line for line in text.split("\n") if not line.startswith("| AC-20 |")))
        self.assert_fails_with(self.validate(), "expected one defining row for AC-20, found 0")

    def test_ec_definition_in_acceptance_document_fails(self) -> None:
        ecosystem = Path("docs/design/ODIN-ECOSYSTEM-INTEGRATION.md")
        row = next(line for line in (self.root / ecosystem).read_text().splitlines()
                   if line.startswith("| EC-16 |"))
        self.edit(ecosystem, lambda text: text.replace(row + "\n", "", 1))
        self.edit(SCENARIOS, lambda text: text + "\n" + row + "\n")
        result = self.validate()
        self.assert_fails_with(result, "expected one defining row for EC-16, found 0")
        self.assertIn("wrong canonical document", result.stdout)

    def test_duplicate_definition_fails(self) -> None:
        self.edit(SCENARIOS, lambda text: text.replace(
            "| AC-41 |", "| AC-41 | Duplicate trigger | Duplicate result |\n| AC-41 |", 1))
        self.assert_fails_with(self.validate(), "duplicate defining ID")

    def test_unknown_definition_fails(self) -> None:
        self.edit(SCENARIOS, lambda text: text.replace(
            "| AC-41 |", "| AC-58 | New trigger | New result |\n| AC-41 |", 1))
        self.assert_fails_with(self.validate(), "unknown defining ID")

    def test_invalid_registry_structure_fails_cleanly(self) -> None:
        registry = self.root / "docs/provenance/STABLE-IDS.json"
        registry.write_text('{"schema_version": 1, "groups": {"AC": {"ids": [{"id": []}]}}}\n')
        self.assert_fails_with(self.validate(), "stable IDs")

    def test_editable_research_readme_link_is_checked(self) -> None:
        readme = Path("docs/research/consolidation-2026-10/README.md")
        self.edit(readme, lambda text: text + "\n[broken](missing-local-page.md)\n")
        self.assert_fails_with(self.validate(), f"broken link: {readme}")

    def test_new_acceptance_id_cannot_be_removed_from_registry(self) -> None:
        registry_path = self.root / "docs/provenance/STABLE-IDS.json"
        registry = json.loads(registry_path.read_text())
        registry["groups"]["AC"]["ids"] = [
            entry for entry in registry["groups"]["AC"]["ids"] if entry["id"] != "AC-50"
        ]
        registry_path.write_text(json.dumps(registry, indent=2) + "\n")
        self.assert_fails_with(self.validate(), "missing baseline registry IDs: ['AC-50']")

    def test_model_research_evidence_links_remain_exempt(self) -> None:
        evidence = Path("docs/research/model-orchestration-2026-10/model-orchestration-and-subagents-2026-10-16.md")
        self.edit(evidence, lambda text: text + "\n[historical](missing-local-page.md)\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_immutable_research_evidence_links_remain_exempt(self) -> None:
        evidence = Path("docs/research/consolidation-2026-10/decision-record-impact.md")
        self.edit(evidence, lambda text: text + "\n[historical](missing-local-page.md)\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dependency_dirs_under_web_are_skipped(self) -> None:
        for relative in (Path("web/node_modules/somepkg/README.md"), Path("web/dist/notes.md")):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[x](missing-page.md)\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dependency_dir_names_outside_web_are_checked(self) -> None:
        path = self.root / "docs/dist/notes.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[x](missing-page.md)\n")
        self.assert_fails_with(self.validate(), "docs/dist/notes.md")


if __name__ == "__main__":
    unittest.main()
