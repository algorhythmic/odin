"""Synthetic end-to-end Claude status-line pipeline: sanitize -> snapshot file ->
normalize_claude_status -> UsageLedger ingest -> summary.

Only synthetic payloads and temporary stores are used. No native transcripts,
credentials or model calls.
"""

import json
import stat
import tempfile
import unittest
from pathlib import Path

from odin.store import Store
from odin.usage import UsageLedger, normalize_claude_status
from odin.usage_statusline import sanitize, write_snapshot

PROJECT = "01K7M000000000000000000001"
SESSION = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
T1 = "2025-02-01T12:00:00Z"
T2 = "2025-02-01T18:00:00Z"
RESET_OLD = 1738425600  # 2025-02-01T16:00:00Z
RESET_NEW = 1738443600  # 2025-02-01T21:00:00Z
WEEK_NEW = 1739030400  # 2025-02-08T16:00:00Z

SENSITIVE_VALUES = (
    "sk-ant-synthetic-DO-NOT-LEAK",
    "/private/synthetic/workspace",
    "/private/synthetic/transcript.jsonl",
    "RAW PROMPT TEXT synthetic",
    "synthetic-session-title",
    "claude-synthetic-model",
    "spend-synthetic-999",
)


def status(session=SESSION, *, usage=None, five=None, seven=None, window=200000):
    """Build a synthetic native status-line payload with sensitive extras."""
    return {
        "session_id": session,
        "api_key": SENSITIVE_VALUES[0],
        "cwd": SENSITIVE_VALUES[1],
        "transcript_path": SENSITIVE_VALUES[2],
        "raw_text": SENSITIVE_VALUES[3],
        "session_name": SENSITIVE_VALUES[4],
        "model": {"id": SENSITIVE_VALUES[5], "display_name": "Synthetic"},
        "spend_limit": {"used_usd": SENSITIVE_VALUES[6]},
        "context_window": {
            "context_window_size": window,
            "current_usage": usage
            if usage is not None
            else {
                "input_tokens": 3,
                "cache_creation_input_tokens": 4,
                "cache_read_input_tokens": 5,
                "secret": SENSITIVE_VALUES[0],
            },
        },
        "rate_limits": {
            "five_hour": five
            if five is not None
            else {
                "used_percentage": 23.5,
                "resets_at": RESET_OLD,
                "token": SENSITIVE_VALUES[0],
            },
            "seven_day": seven
            if seven is not None
            else {"used_percentage": 41.2, "resets_at": WEEK_NEW},
        },
    }


class LiveStatusPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.ledger = UsageLedger(self.store)
        self.output = self.root / "private" / "status.json"

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def capture(self, native, *, session=SESSION):
        """sanitize, then write the snapshot file and read it back."""
        snapshot = sanitize(native, session_id=session, project=PROJECT)
        if snapshot is None:
            return None
        # write_snapshot returns False for an identical rewrite; both are fine here.
        write_snapshot(self.output, snapshot)
        return json.loads(self.output.read_text())

    def ingest(self, native, *, observed_at=T1, session=SESSION):
        snapshot = self.capture(native, session=session)
        observation = normalize_claude_status(
            snapshot, project_id=PROJECT, session_id=session, observed_at=observed_at
        )
        return self.ledger.ingest(observation), observation

    # (a) happy path
    def test_happy_path_context_quota_and_no_request(self):
        outcome, observation = self.ingest(status())
        self.assertEqual(outcome, "inserted")
        self.assertEqual(observation["kind"], "quota")
        self.assertEqual(observation["context_input_tokens"], 12)
        self.assertEqual(observation["context_window_tokens"], 200000)
        summary = self.ledger.summary(project_id=PROJECT, as_of=T1)
        self.assertEqual(summary["request_count"], 0)
        self.assertEqual(
            summary["missing_requests"], {k: 0 for k in summary["missing_requests"]}
        )
        self.assertEqual(summary["latest_context"]["context_input_tokens"], 12)
        self.assertEqual(summary["latest_context"]["session_id"], SESSION)
        self.assertEqual(
            summary["latest_quota"]["rate_limits"]["five_hour"]["used_percentage"], 23.5
        )
        self.assertEqual(
            summary["latest_quota"]["rate_limits"]["seven_day"]["used_percentage"], 41.2
        )
        self.assertEqual(
            summary["latest_quota"]["rate_limits"]["five_hour"]["resets_at"],
            "2025-02-01T16:00:00Z",
        )
        self.assertFalse(summary["quota_stale"])

    # (b) synthetic epoch reset
    def test_epoch_reset_latest_quota_reflects_new_window_without_double_count(self):
        before = status(
            five={"used_percentage": 90.0, "resets_at": RESET_OLD},
            seven={"used_percentage": 80.0, "resets_at": WEEK_NEW},
        )
        after = status(
            five={"used_percentage": 2.0, "resets_at": RESET_NEW},
            seven={"used_percentage": 1.0, "resets_at": WEEK_NEW + 604800},
            usage={
                "input_tokens": 1,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        )
        self.assertEqual(self.ingest(before, observed_at=T1)[0], "inserted")
        self.assertEqual(self.ingest(after, observed_at=T2)[0], "inserted")
        summary = self.ledger.summary(project_id=PROJECT, as_of=T2)
        latest = summary["latest_quota"]
        self.assertEqual(latest["observed_at"], T2)
        self.assertEqual(latest["rate_limits"]["five_hour"]["used_percentage"], 2.0)
        self.assertEqual(
            latest["rate_limits"]["five_hour"]["resets_at"], "2025-02-01T21:00:00Z"
        )
        self.assertEqual(latest["rate_limits"]["seven_day"]["used_percentage"], 1.0)
        self.assertEqual(latest["context_input_tokens"], 1)
        # Both samples retained as separate quota rows; no request totals created.
        self.assertEqual(len(summary["quota_snapshots"]), 2)
        self.assertEqual(summary["request_count"], 0)
        self.assertEqual(sum(summary["tokens"].values()), 0)
        # Replaying the older sample does not overwrite the latest view.
        self.assertEqual(self.ingest(before, observed_at=T1)[0], "duplicate")
        replayed = self.ledger.summary(project_id=PROJECT, as_of=T2)
        self.assertEqual(replayed["latest_quota"]["observed_at"], T2)
        self.assertEqual(len(replayed["quota_snapshots"]), 2)

    # (c) null, missing and malformed context / limits
    def test_null_and_missing_context_and_limits_yield_nulls(self):
        # Each case uses its own observed_at: the ledger dedupes identical samples.
        cases = (
            (
                "explicit nulls",
                {"session_id": SESSION, "context_window": None, "rate_limits": None},
                T1,
            ),
            ("missing keys", {"session_id": SESSION}, "2025-02-01T12:01:00Z"),
            (
                "null current_usage",
                {
                    "session_id": SESSION,
                    "context_window": {
                        "context_window_size": 200000,
                        "current_usage": None,
                    },
                    "rate_limits": {"five_hour": None, "seven_day": None},
                },
                "2025-02-01T12:02:00Z",
            ),
        )
        for name, native, when in cases:
            with self.subTest(case=name):
                snapshot = sanitize(native, session_id=SESSION, project=PROJECT)
                self.assertIsNone(snapshot["context_window"]["current_usage"])
                self.assertIsNone(
                    snapshot["rate_limits"]["five_hour"]["used_percentage"]
                )
                outcome, observation = self.ingest(native, observed_at=when)
                self.assertEqual(outcome, "inserted")
                self.assertIsNone(observation["context_input_tokens"])
                self.assertIsNone(
                    observation["rate_limits"]["five_hour"]["used_percentage"]
                )
                self.assertIsNone(
                    observation["rate_limits"]["seven_day"]["used_percentage"]
                )
                self.assertIsNone(observation["rate_limits"]["five_hour"]["resets_at"])

    def test_malformed_shapes_raise_value_error_only(self):
        bad_natives = (
            ("context not object", {"session_id": SESSION, "context_window": "x"}),
            ("limits not object", {"session_id": SESSION, "rate_limits": "x"}),
            ("list limits", {"session_id": SESSION, "rate_limits": []}),
            (
                "usage not object",
                {"session_id": SESSION, "context_window": {"current_usage": "x"}},
            ),
            (
                "percentage over 100",
                status(five={"used_percentage": 101, "resets_at": RESET_OLD}),
            ),
            (
                "boolean counter",
                status(
                    usage={
                        "input_tokens": True,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                    }
                ),
            ),
            ("non-object native", None),
        )
        for name, native in bad_natives:
            with self.subTest(case=name):
                # Sanitizer, the trust boundary for the snapshot, raises ValueError.
                with self.assertRaises(ValueError):
                    sanitize(native, session_id=SESSION, project=PROJECT)
                # Normalizer on the same malformed input is a ValueError or, for a
                # falsy/nonstandard container, a silently empty sample (recorded below).
                # Any other exception type propagates and errors the subtest.
                try:
                    normalize_claude_status(
                        native, project_id=PROJECT, session_id=SESSION, observed_at=T1
                    )
                except ValueError:
                    pass
        # Observed behaviour: normalize_claude_status treats falsy containers
        # ([] for rate_limits, a string for current_usage) as absent instead of
        # rejecting them. Sanitize rejects both, so the real pipeline fails closed.
        quiet = normalize_claude_status(
            {
                "session_id": SESSION,
                "rate_limits": [],
                "context_window": {"current_usage": "x"},
            },
            project_id=PROJECT,
            session_id=SESSION,
            observed_at=T1,
        )
        self.assertIsNone(quiet["context_input_tokens"])
        self.assertIsNone(quiet["rate_limits"]["five_hour"]["used_percentage"])

    # (d) sensitive and unknown fields
    def test_sensitive_fields_absent_from_snapshot_file_and_ledger(self):
        native = status()
        snapshot = sanitize(native, session_id=SESSION, project=PROJECT)
        self.assertEqual(set(snapshot), {"session_id", "context_window", "rate_limits"})
        self.assertEqual(
            set(snapshot["context_window"]["current_usage"]),
            {"input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"},
        )
        write_snapshot(self.output, snapshot)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        file_text = self.output.read_text()
        for value in SENSITIVE_VALUES:
            self.assertNotIn(value, file_text)
        self.assertNotIn("api_key", file_text)
        outcome, observation = self.ingest(native)
        self.assertEqual(outcome, "inserted")
        self.assertEqual(
            set(observation),
            {
                "schema_version",
                "kind",
                "provider",
                "source",
                "project_id",
                "session_id",
                "agent_id",
                "account_id",
                "observed_at",
                "context_input_tokens",
                "context_window_tokens",
                "rate_limits",
            },
        )
        ledger_text = json.dumps(observation)
        for value in SENSITIVE_VALUES:
            self.assertNotIn(value, ledger_text)
        self.assertNotIn("api_key", ledger_text)
        self.assertNotIn("transcript", ledger_text)
        # The durable store must not contain the sensitive values either.
        store_bytes = self.store.path.read_bytes()
        for value in SENSITIVE_VALUES:
            self.assertNotIn(value.encode(), store_bytes)

    # (e) native session id match versus mismatch
    def test_matching_native_session_is_ingested_under_configured_session(self):
        outcome, observation = self.ingest(status(SESSION), session=SESSION)
        self.assertEqual(outcome, "inserted")
        self.assertEqual(observation["session_id"], SESSION)

    def test_mismatched_native_session_is_dropped_by_sanitize(self):
        # Observed behaviour: sanitize returns None (not an exception) for a
        # native session that is not the configured one, so nothing is written
        # and no observation is produced for the executive session.
        self.assertIsNone(sanitize(status(OTHER), session_id=SESSION, project=PROJECT))
        self.assertIsNone(
            sanitize({"context_window": {}}, session_id=SESSION, project=PROJECT)
        )
        self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            # The pipeline has no snapshot to normalize; None is not a status object.
            normalize_claude_status(
                None, project_id=PROJECT, session_id=SESSION, observed_at=T1
            )
        self.assertEqual(self.ledger.summary(project_id=PROJECT)["latest_quota"], None)

    def test_normalize_does_not_check_native_session_id(self):
        # Observed finding: the session check lives only in sanitize. Passing a
        # raw status for another native session directly to normalize_claude_status
        # stamps the configured session_id onto that other session's numbers.
        observation = normalize_claude_status(
            status(OTHER), project_id=PROJECT, session_id=SESSION, observed_at=T1
        )
        self.assertEqual(observation["session_id"], SESSION)
        self.assertEqual(
            observation["rate_limits"]["five_hour"]["used_percentage"], 23.5
        )


if __name__ == "__main__":
    unittest.main()
