"""Synthetic end-to-end checks: UsageWatcher -> Gateway usage_import -> UsageLedger.

Only synthetic session ids, request ids and token counts are used. No home
directory, credential file, or model call is touched.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from odin.coordination import Actor
from odin.executive_service import prepare_project
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.usage_watch import UsageWatcher

SESSION = "synthetic-session-alpha"
AGENT = "executive"


class LiveWatchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.project = prepare_project(self.state)
        self.service = Service(self.state)
        # Cleanup closes whichever service is current; reopen tests replace it.
        self.addCleanup(lambda: self.service.close())
        self.gateway = Gateway(self.service)
        self.context = GatewayContext("terminal", Actor("operator", "synthetic"))
        self.transcript = self.root / "transcripts" / f"{SESSION}.jsonl"
        self.transcript.parent.mkdir()
        self.cursor = self.root / "cursor.sqlite3"
        self.config = {
            "schema_version": 1,
            "project_id": self.project,
            "cursor_path": str(self.cursor),
            "max_chunk_bytes": 65536,
            "sources": [
                {
                    "provider": "claude",
                    "session_file": str(self.transcript),
                    "session_id": SESSION,
                    "agent_id": AGENT,
                    "discover_children": True,
                }
            ],
        }

    # -- helpers -----------------------------------------------------------

    def send(self, _address, envelope):
        # Route through the real Gateway the same way the operator socket would.
        return self.gateway.submit(envelope["command"], context=self.context)

    def watcher(self):
        return UsageWatcher(self.config, address="synthetic", send=self.send)

    def row(self, request_id, *, output=2, uncached=3, session=SESSION):
        return {
            "type": "assistant",
            "sessionId": session,
            "message": {
                "id": request_id,
                "model": "synthetic-model",
                "usage": {
                    "input_tokens": uncached,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": output,
                },
                "content": [{"type": "text", "text": "PRIVATE MESSAGE CONTENT"}],
            },
        }

    def append(self, path, *rows):
        with path.open("a") as stream:
            for item in rows:
                stream.write(json.dumps(item) + "\n")

    def summary(self):
        return self.gateway.usage.summary(project_id=self.project)

    def bodies(self):
        rows = self.service.store.db.execute(
            "SELECT body FROM usage_requests ORDER BY session_id, agent_id, request_id"
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def reopen(self, watch):
        """Close the watcher and service, then reopen both on the same paths."""
        watch.close()
        self.service.close()
        self.service = Service(self.state)
        self.gateway = Gateway(self.service)
        return self.watcher()

    # -- (a) ingestion attribution -----------------------------------------

    def test_several_request_rows_ingested_once_with_stable_attribution(self):
        self.append(
            self.transcript,
            self.row("req-a1", output=2),
            self.row("req-a2", output=5),
            self.row("req-a3", output=7),
        )
        with self.watcher() as watch:
            result = watch.poll()
        self.assertEqual(result["imported"], 1)
        summary = self.summary()
        self.assertEqual(summary["request_count"], 3)
        self.assertEqual(summary["tokens"]["output"], 14)
        self.assertEqual(summary["tokens"]["uncached_input"], 9)
        bodies = self.bodies()
        self.assertEqual(
            sorted(b["request_id"] for b in bodies), ["req-a1", "req-a2", "req-a3"]
        )
        for body in bodies:
            self.assertEqual(body["session_id"], SESSION)
            self.assertEqual(body["agent_id"], AGENT)
            self.assertEqual(body["provider"], "claude")
            self.assertEqual(body["project_id"], self.project)
            self.assertEqual(body["revision"], 0)
        # Metadata only: message text must never reach the cursor or ledger.
        self.assertNotIn(b"PRIVATE MESSAGE CONTENT", self.cursor.read_bytes())
        self.assertNotIn(
            b"PRIVATE MESSAGE CONTENT", self.service.store.path.read_bytes()
        )

    # -- (b) reopen does not double count ----------------------------------

    def test_reopen_watcher_and_service_does_not_double_count(self):
        self.append(
            self.transcript, self.row("req-b1", output=2), self.row("req-b2", output=4)
        )
        with self.watcher() as watch:
            watch.poll()
            before = self.summary()
            self.assertEqual(before["request_count"], 2)
            watch = self.reopen(watch)
            with watch:
                self.assertEqual(watch.poll()["imported"], 0)
                self.assertEqual(watch.poll()["imported"], 0)
        after = self.summary()
        self.assertEqual(after["request_count"], before["request_count"])
        self.assertEqual(after["tokens"], before["tokens"])
        self.assertEqual(len(self.bodies()), 2)

    def test_reopen_then_new_rows_adds_only_new_requests(self):
        self.append(self.transcript, self.row("req-c1", output=2))
        with self.watcher() as watch:
            watch.poll()
            watch = self.reopen(watch)
            with watch:
                self.append(self.transcript, self.row("req-c2", output=6))
                watch.poll()
        summary = self.summary()
        self.assertEqual(summary["request_count"], 2)
        self.assertEqual(summary["tokens"]["output"], 8)

    # -- (c) repeated revisions of one requestId ----------------------------

    def test_repeated_revisions_keep_one_request_at_latest_revision(self):
        # Observed behaviour: a growing revision is accepted as revision n+1 and
        # replaces the stored body; equal-token repeats are skipped; the ledger
        # never sums the revisions.
        self.append(self.transcript, self.row("req-d1", output=1))
        with self.watcher() as watch:
            watch.poll()
            self.append(self.transcript, self.row("req-d1", output=3))
            watch.poll()
            self.append(self.transcript, self.row("req-d1", output=3))
            watch.poll()
            self.append(self.transcript, self.row("req-d1", output=8))
            watch.poll()
        summary = self.summary()
        self.assertEqual(summary["request_count"], 1)
        self.assertEqual(summary["tokens"]["output"], 8)
        self.assertEqual(summary["tokens"]["uncached_input"], 3)
        bodies = self.bodies()
        self.assertEqual(len(bodies), 1)
        self.assertEqual(bodies[0]["tokens"]["output"], 8)
        self.assertEqual(bodies[0]["revision"], 2)

    def test_revision_survives_reopen_without_double_counting(self):
        self.append(self.transcript, self.row("req-e1", output=1))
        with self.watcher() as watch:
            watch.poll()
            self.append(self.transcript, self.row("req-e1", output=4))
            watch.poll()
            watch = self.reopen(watch)
            with watch:
                # Replaying the same revision after reopen must not bump it again.
                self.assertEqual(watch.poll()["imported"], 0)
                self.append(self.transcript, self.row("req-e1", output=9))
                watch.poll()
        summary = self.summary()
        self.assertEqual(summary["request_count"], 1)
        self.assertEqual(summary["tokens"]["output"], 9)
        self.assertEqual(self.bodies()[0]["revision"], 2)

    # -- (d) rotation -------------------------------------------------------

    def test_rename_and_replace_with_same_session_adds_only_new_rows(self):
        # Observed behaviour: a new inode at the configured path is detected as
        # rotation, the cursor restarts at byte zero of the replacement, and only
        # requests not already stored are added.
        self.append(
            self.transcript, self.row("req-f1", output=2), self.row("req-f2", output=3)
        )
        with self.watcher() as watch:
            watch.poll()
            self.assertEqual(self.summary()["request_count"], 2)
            os.rename(self.transcript, self.transcript.with_name("rotated-old.jsonl"))
            replacement = self.transcript.with_name("replacement.tmp")
            self.append(replacement, self.row("req-f3", output=4))
            os.replace(replacement, self.transcript)
            watch.poll()
        summary = self.summary()
        self.assertEqual(summary["request_count"], 3)
        self.assertEqual(summary["tokens"]["output"], 9)
        self.assertEqual(
            sorted(b["request_id"] for b in self.bodies()),
            ["req-f1", "req-f2", "req-f3"],
        )

    def test_replacement_repeating_old_rows_does_not_double_count(self):
        # Observed behaviour: a full-copy replacement re-reads old rows, but equal
        # token counters are deduplicated by the watcher's revision check.
        self.append(
            self.transcript, self.row("req-g1", output=2), self.row("req-g2", output=3)
        )
        with self.watcher() as watch:
            watch.poll()
            replacement = self.transcript.with_name("replacement.tmp")
            self.append(
                replacement,
                self.row("req-g1", output=2),
                self.row("req-g2", output=3),
                self.row("req-g3", output=5),
            )
            os.replace(replacement, self.transcript)
            watch.poll()
        summary = self.summary()
        self.assertEqual(summary["request_count"], 3)
        self.assertEqual(summary["tokens"]["output"], 10)
        self.assertEqual(summary["tokens"]["uncached_input"], 9)

    # -- (e) stable identity across reopen and rotation ---------------------

    def test_session_and_agent_identity_stable_across_reopen_and_rotation(self):
        child_dir = self.transcript.with_suffix("") / "subagents"
        child_dir.mkdir(parents=True)
        child = child_dir / "agent-synthetic-beta.jsonl"
        self.append(self.transcript, self.row("req-h1", output=2))
        self.append(
            child, self.row("req-h-child", output=1, session="synthetic-child-session")
        )
        with self.watcher() as watch:
            watch.poll()
            before = {
                b["request_id"]: (b["session_id"], b["agent_id"]) for b in self.bodies()
            }
            self.assertEqual(before["req-h1"], (SESSION, AGENT))
            child_session, child_agent = before["req-h-child"]
            self.assertEqual(child_session, "synthetic-child-session")
            self.assertIn("agent-synthetic-beta", child_agent)

            watch = self.reopen(watch)
            with watch:
                watch.poll()
                reopened = {
                    b["request_id"]: (b["session_id"], b["agent_id"])
                    for b in self.bodies()
                }
                self.assertEqual(reopened, before)

                os.rename(
                    self.transcript, self.transcript.with_name("rotated-old.jsonl")
                )
                replacement = self.transcript.with_name("replacement.tmp")
                self.append(replacement, self.row("req-h2", output=3))
                os.replace(replacement, self.transcript)
                watch.poll()
        rotated = {
            b["request_id"]: (b["session_id"], b["agent_id"]) for b in self.bodies()
        }
        self.assertEqual(rotated["req-h1"], before["req-h1"])
        self.assertEqual(rotated["req-h-child"], before["req-h-child"])
        self.assertEqual(rotated["req-h2"], (SESSION, AGENT))
        self.assertEqual(self.summary()["request_count"], 3)


if __name__ == "__main__":
    unittest.main()
