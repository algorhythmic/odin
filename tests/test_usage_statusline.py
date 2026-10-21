"""Synthetic native status-line payloads only; no live configuration changes."""

import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from odin.contracts import Contracts
from odin.usage_statusline import main, sanitize, status_text, write_snapshot


PROJECT = "01K7M000000000000000000001"
SESSION = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def native(session=SESSION):
    return {
        "session_id": session,
        "cwd": "/private/top-secret",
        "transcript_path": "/private/conversation.jsonl",
        "session_name": "secret title",
        "model": {"id": "claude-opus", "display_name": "Opus"},
        "context_window": {"context_window_size": 200000,
            "current_usage": {"input_tokens": 3, "cache_creation_input_tokens": 4,
                              "cache_read_input_tokens": 5, "secret": "do not retain"}},
        "rate_limits": {"five_hour": {"used_percentage": 23.5,
                                      "resets_at": 1738425600, "token": "secret"},
                        "seven_day": {"used_percentage": 41.2,
                                      "resets_at": 1738857600},
                        "spend_limit": {"used_usd": 10}},
    }


class StatuslineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "private" / "fable-status.json"

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, value, *, session=SESSION):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = main(["--output", str(self.output), "--session-id", session,
                     "--project", PROJECT], stdin=io.BytesIO(json.dumps(value).encode()),
                    stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_sanitized_native_shape_private_atomic_file(self):
        code, line, error = self.invoke(native())
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(line.strip(), "Odin context 12/200000 | 5h 23.5% | 7d 41.2%")
        self.assertEqual(stat.S_IMODE(self.output.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])
        payload = self.output.read_text()
        for secret in ("private", "secret", "claude-opus", "spend_limit"):
            self.assertNotIn(secret, payload)
        snapshot = json.loads(payload)
        Contracts().validate("usage-statusline-snapshot", snapshot)
        self.assertEqual(snapshot["session_id"], SESSION)
        self.assertEqual(snapshot["rate_limits"]["five_hour"]["resets_at"], 1738425600)

    def test_identical_sample_does_not_refresh_mtime(self):
        self.invoke(native())
        old = 1_700_000_000_000_000_000
        os.utime(self.output, ns=(old, old))
        self.invoke(native())
        self.assertEqual(self.output.stat().st_mtime_ns, old)
        changed = native()
        changed["rate_limits"]["five_hour"]["used_percentage"] = 24
        self.invoke(changed)
        self.assertNotEqual(self.output.stat().st_mtime_ns, old)

    def test_wrong_native_session_is_ignored(self):
        code, line, error = self.invoke(native(OTHER))
        self.assertEqual((code, line.strip(), error), (0, "Odin status unavailable", ""))
        self.assertFalse(self.output.exists())
        self.invoke(native())
        original = self.output.read_bytes()
        self.invoke(native(OTHER))
        self.assertEqual(self.output.read_bytes(), original)

    def test_missing_values_remain_null(self):
        snapshot = sanitize({"session_id": SESSION}, session_id=SESSION, project=PROJECT)
        self.assertIsNone(snapshot["context_window"]["current_usage"])
        self.assertIsNone(snapshot["context_window"]["context_window_size"])
        self.assertIsNone(snapshot["rate_limits"]["five_hour"]["used_percentage"])
        self.assertEqual(status_text(snapshot), "Odin context -- | 5h -- | 7d --")

    def test_invalid_and_oversize_inputs_do_not_write(self):
        bad = native()
        bad["context_window"]["current_usage"]["input_tokens"] = -1
        self.assertEqual(self.invoke(bad)[0], 1)
        self.assertFalse(self.output.exists())
        stdout, stderr = io.StringIO(), io.StringIO()
        code = main(["--output", str(self.output), "--session-id", SESSION,
                     "--project", PROJECT], stdin=io.BytesIO(b"x" * 65537),
                    stdout=stdout, stderr=stderr)
        self.assertEqual(code, 1)
        self.assertFalse(self.output.exists())
        self.assertNotIn("x", stderr.getvalue())

    def test_rejects_nonprivate_directory_and_symlink_output(self):
        self.output.parent.mkdir(mode=0o700)
        self.output.parent.chmod(0o755)
        with self.assertRaises(ValueError):
            write_snapshot(self.output, sanitize(native(), session_id=SESSION, project=PROJECT))
        self.output.parent.chmod(0o700)
        target = self.output.parent / "target"
        target.write_text("unchanged")
        self.output.symlink_to(target)
        with self.assertRaises(OSError):
            write_snapshot(self.output, sanitize(native(), session_id=SESSION, project=PROJECT))
        self.assertEqual(target.read_text(), "unchanged")

    def test_existing_fifo_is_refused_without_opening_a_writer(self):
        self.output.parent.mkdir(mode=0o700)
        os.mkfifo(self.output, 0o600)
        with self.assertRaises(ValueError):
            write_snapshot(self.output, sanitize(native(), session_id=SESSION, project=PROJECT))


if __name__ == "__main__":
    unittest.main()
