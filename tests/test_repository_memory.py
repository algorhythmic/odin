"""Committed repository evidence is bounded, exact, scoped and restart-safe."""

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from odin.contracts import strict_loads
from odin.memory import Memory
from odin.repository_memory import (
    _digest,
    _snapshot_id,
    catalog_id,
    import_batch,
    prepare,
    source_id,
)
from odin.store import Conflict, Store
from test_memory import P, Q, project


class RepositoryMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "user.name", "Synthetic repository fixture")
        self.store = Store(self.root / "state")
        self.store.create(project(P, "Odin"))
        self.store.create(project(Q, "Other"))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
        ).stdout

    def write(self, path, content):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Synthetic evidence")

    def upload(self, batches=None):
        return [
            import_batch(self.store, b, project=P)
            for b in (batches or prepare(self.repo, P))
        ]

    def read(self, ref, principal="fable-executive", project_id=P, scopes=(P,)):
        return Memory(self.store).read_source(
            project_id,
            ref["id"],
            ref["revision"],
            principal=principal,
            permitted_projects=scopes,
        )["source"]

    def test_only_selected_committed_regular_files_and_explicit_root(self):
        self.write("docs/design.md", "committed text\n")
        self.write("docs/history/frozen.md", "excluded historical bytes")
        self.write("docs/contracts/peer.md", "excluded peer bytes")
        self.write("docs/research/evidence.md", "excluded research bytes")
        self.write(".env", "SYNTHETIC_SECRET=never_ingest")
        self.write("unselected.txt", "excluded file")
        self.write("docs/secrets.txt", "synthetic excluded secret file")
        self.write("docs/auth.json", "synthetic excluded auth file")
        (self.repo / "docs/link.md").symlink_to("design.md")
        self.commit()
        self.write("docs/design.md", "uncommitted replacement")
        self.write("docs/untracked.md", "untracked content")
        batches = prepare(self.repo, P)
        self.assertEqual(
            [e["path"] for b in batches for e in b["entries"]], ["docs/design.md"]
        )
        self.assertEqual(batches[0]["entries"][0]["content"], "committed text\n")
        with self.assertRaises(ValueError):
            prepare(self.repo / "docs", P)

    def test_exact_read_discovery_replay_and_restart(self):
        text = "# Design\nA source fact, not approval.\n"
        self.write("docs/design.md", text)
        self.commit()
        batches = prepare(self.repo, P)
        first = self.upload(batches)[0]
        memory = Memory(self.store)
        revision = memory.dependency_revision(P)
        self.assertEqual(first, self.upload(prepare(self.repo, P))[0])
        self.assertEqual(revision, memory.dependency_revision(P))
        view = memory.snapshot(P, "fable-executive")
        self.assertEqual(view["sources"][0]["id"], catalog_id(P))
        self.assertEqual(view["availability"], "available")
        self.assertEqual(view["statements"], [])
        root = strict_loads(self.read(first["catalog"])["content"])
        page = strict_loads(self.read(root["pages"][0])["content"])
        evidence = self.read(page["entries"][0])
        self.assertEqual(evidence["content"], text)
        self.assertIn(batches[0]["commit"], evidence["locator"])
        self.assertEqual(evidence["readers"], ["fable-executive", "local-operator"])
        self.store.close()
        self.store = Store(self.root / "state")
        self.assertEqual(self.read(page["entries"][0])["content"], text)
        self.assertEqual(first, self.upload(batches)[0])

    def test_changed_source_new_revision_and_unchanged_source_deduped(self):
        self.write("docs/a.md", "old\n")
        self.write("docs/b.md", "unchanged\n")
        self.commit()
        old_batches = prepare(self.repo, P)
        self.upload(old_batches)
        self.write("docs/a.md", "new\n")
        self.commit()
        result = self.upload()[0]
        self.assertEqual(result["added_sources"], 1)
        with self.assertRaisesRegex(Conflict, "superseded"):
            self.upload(old_batches)
        self.assertEqual(
            self.read({"id": source_id(P, "docs/a.md"), "revision": 1})["content"],
            "old\n",
        )
        self.assertEqual(
            self.read({"id": source_id(P, "docs/a.md"), "revision": 2})["content"],
            "new\n",
        )
        row = self.store.db.execute(
            "SELECT MAX(revision) FROM memory_sources WHERE id=?",
            (source_id(P, "docs/b.md"),),
        ).fetchone()
        self.assertEqual(row[0], 1)

    def test_cross_project_and_reader_scope(self):
        self.write("README.md", "Scoped evidence\n")
        self.commit()
        batches = prepare(self.repo, P)
        with self.assertRaises(PermissionError):
            import_batch(self.store, batches[0], project=Q)
        result = self.upload(batches)[0]
        with self.assertRaises(Conflict):
            self.read(result["catalog"], principal="other-agent")
        with self.assertRaises((PermissionError, Conflict)):
            self.read(result["catalog"], project_id=Q, scopes=(Q,))
        self.assertEqual(
            Memory(self.store).snapshot(Q, "fable-executive")["sources"], []
        )

    def test_utf8_long_lines_and_catalog_pages_are_bounded(self):
        text = "α" * 8000 + "\n" + "line\n" * 1500
        for n in range(10):
            self.write(f"docs/long-{n}.md", text)
        self.commit()
        batches = prepare(self.repo, P)
        self.assertGreater(len(batches), 1)
        pieces = [
            e for b in batches for e in b["entries"] if e["path"] == "docs/long-0.md"
        ]
        self.assertEqual("".join(e["content"] for e in pieces), text)
        self.assertTrue(all(len(e["content"].encode()) <= 6000 for e in pieces))
        first = import_batch(self.store, batches[0], project=P)
        self.assertFalse(first["complete"])
        self.assertEqual(
            Memory(self.store).snapshot(P, "fable-executive")["availability"],
            "incomplete",
        )
        for b in batches[1:]:
            result = import_batch(self.store, b, project=P)
        self.assertTrue(result["complete"])
        view = Memory(self.store).snapshot(P, "fable-executive", max_bytes=8192)
        self.assertEqual(view["sources"][0]["id"], catalog_id(P))
        root = strict_loads(self.read(result["catalog"])["content"])
        self.assertEqual(len(root["pages"]), len(batches))
        for page in root["pages"]:
            self.assertLessEqual(len(self.read(page)["content"]), 8192)

    def test_tampering_disallowed_paths_and_out_of_order_fail_atomically(self):
        for n in range(30):
            self.write(f"docs/{n}.md", "content\n")
        self.commit()
        batches = prepare(self.repo, P)
        with self.assertRaises(Conflict):
            import_batch(self.store, batches[1], project=P)
        tampered = copy.deepcopy(batches[0])
        tampered["entries"][0]["content"] = "tampered\n"
        with self.assertRaises(Conflict):
            import_batch(self.store, tampered, project=P)
        denied = copy.deepcopy(batches[0])
        denied["entries"][0]["path"] = "docs/../../.credentials.json"
        denied["batch_digests"][0] = _digest(denied["entries"])
        denied["snapshot_id"] = _snapshot_id(denied)
        with self.assertRaises(Conflict):
            import_batch(self.store, denied, project=P)
        self.assertEqual(
            Memory(self.store).snapshot(P, "fable-executive")["sources"], []
        )
        with self.assertRaises(RuntimeError), self.store.transaction():
            import_batch(self.store, batches[0], project=P)
            raise RuntimeError("caller rolled back")
        self.assertEqual(
            Memory(self.store).snapshot(P, "fable-executive")["sources"], []
        )

    def test_redaction_is_not_undone_by_import(self):
        self.write("README.md", "Initial source\n")
        self.commit()
        self.upload()
        sid = source_id(P, "README.md")
        Memory(self.store).redact(sid, 1, ["local"])
        self.write("README.md", "Changed source\n")
        self.commit()
        with self.assertRaises(Conflict):
            self.upload()

    def test_project_repository_binding_cannot_be_replaced(self):
        self.write("README.md", "Initial source\n")
        self.commit()
        batches = prepare(self.repo, P)
        self.upload(batches)
        other = copy.deepcopy(batches[0])
        other["repository"] = "/different/repository"
        other["snapshot_id"] = _snapshot_id(other)
        with self.assertRaisesRegex(Conflict, "binding"):
            import_batch(self.store, other, project=P)

    def test_selected_binary_and_oversize_files_refused(self):
        self.write("docs/a.md", "synthetic\0binary")
        self.commit()
        with self.assertRaises(ValueError):
            prepare(self.repo, P)
        self.write("docs/a.md", "x" * (1024 * 1024 + 1))
        self.commit()
        with self.assertRaises(ValueError):
            prepare(self.repo, P)


if __name__ == "__main__":
    unittest.main()
