"""Explicit source collection exposes only bounded metadata to the service."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from odin.contracts import identifier
from odin.usage_cli import _json_file, run


class UsageCLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = identifier()
        self.source = self.root / "native.jsonl"
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def collect(self, provider, **overrides):
        args = argparse.Namespace(action="usage-collect", project=self.project,
            source_file=str(self.source), native_session="11111111-2222-4333-8444-555555555555",
            usage_provider=provider, agent_id="executive", account_id="account",
            loop=None, stage=None, max_bytes=65536, operation_id=None,
            usage_semantics="per_turn", **overrides)
        def send(address, envelope):
            self.calls.append(envelope["command"])
            return {"result": {"accepted": True}}
        with contextlib.redirect_stdout(io.StringIO()):
            return run(args, "unused", send, argparse.ArgumentParser())

    def test_batches_strip_content_and_replay_same_metadata(self):
        rows = [{"type": "assistant", "timestamp": "2026-10-20T00:00:00Z",
                 "message": {"id": "r" + str(n), "model": "haiku",
                    "content": "PRIVATE CONTENT MUST NOT BE IMPORTED",
                    "usage": {"input_tokens": 1, "cache_read_input_tokens": 0,
                              "cache_creation_input_tokens": 0, "output_tokens": 2}}}
                for n in range(130)]
        self.source.write_text("\n".join(json.dumps(row) for row in rows))
        self.assertEqual(self.collect("claude"), 0)
        first = list(self.calls)
        self.assertEqual([len(c["payload"]["observations"]) for c in first], [128, 2])
        self.assertNotIn("PRIVATE CONTENT", json.dumps(first))
        self.assertNotIn("coverage", first[0]["payload"])
        self.assertTrue(first[-1]["payload"]["coverage"]["complete"])
        self.calls.clear()
        self.collect("claude")
        self.assertEqual(first, self.calls)

    def test_status_reimport_keeps_source_sample_time(self):
        self.source.write_text(json.dumps({"context_window": {"current_usage": {
            "input_tokens": 1, "cache_read_input_tokens": 2, "cache_creation_input_tokens": 3}},
            "rate_limits": {"five_hour": {"used_percentage": 40}}}))
        os.utime(self.source, (1000000000, 1000000000))
        self.collect("claude-status")
        sample = self.calls[-1]["payload"]["observations"][0]
        self.assertEqual(sample["observed_at"], "2001-09-09T01:46:40Z")
        self.assertEqual(sample["context_input_tokens"], 6)
        self.collect("claude-status")
        self.assertEqual(sample, self.calls[-1]["payload"]["observations"][0])

    def test_fifo_and_oversize_json_are_refused(self):
        os.mkfifo(self.source)
        with self.assertRaisesRegex(ValueError, "regular"):
            _json_file(self.source, 20)
        self.source.unlink()
        self.source.write_text('"' + 'x' * 100 + '"')
        with self.assertRaisesRegex(ValueError, "bound"):
            _json_file(self.source, 20)
