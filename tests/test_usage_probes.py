"""Limit probes use injected recorded responses; no live network or real home is touched."""
import json
import tempfile
import unittest
from pathlib import Path

from odin.contracts import Contracts, identifier
from odin.store import Store, now
from odin.usage import probe_claude_limits, probe_codex_limits
from odin.usage_policy import LIMITS, UsagePolicy, band_for

SECRET = "SYNTHETIC-OAUTH-TOKEN-7f3a9c"
OBSERVED = "2026-10-21T10:00:00Z"
RECORDED = {
    "five_hour": {"utilization": 91.5, "resets_at": "2026-10-21T12:00:00Z"},
    "seven_day": {"utilization": 84.9, "resets_at": "2026-10-25T00:00:00Z"},
    "seven_day_fable": {"utilization": 40.0, "resets_at": "2026-10-25T00:00:00Z"},
    "seven_day_sonnet": None,
    "extra_unknown": {"note": "ignored"},
}


def fake_transport(status=200, body=None, calls=None, raises=None):
    def transport(url, headers, timeout):
        if calls is not None:
            calls.append((url, headers, timeout))
        if raises is not None:
            raise raises
        raw = body if isinstance(body, bytes) else json.dumps(body if body is not None else RECORDED).encode()
        return status, raw
    return transport


class ClaudeProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = identifier()
        self.config = self.root / "claude-login"
        self.config.mkdir()
        (self.config / ".credentials.json").write_text(
            json.dumps({"claudeAiOauth": {"accessToken": SECRET, "expiresAt": 1}}))

    def tearDown(self):
        self.temp.cleanup()

    def assertNoSecret(self, value):
        self.assertNotIn(SECRET, json.dumps(value, default=str))

    def test_success_records_label_keyed_samples(self):
        calls = []
        samples = probe_claude_limits(str(self.config), project_id=self.project,
                                      transport=fake_transport(calls=calls))
        self.assertEqual(len(calls), 1)
        url, headers, _ = calls[0]
        self.assertEqual(url, "https://api.anthropic.com/api/oauth/usage")
        self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
        self.assertEqual(headers["anthropic-beta"], "oauth-2025-04-20")
        by_label = {s["label"]: s for s in samples}
        self.assertEqual(set(by_label), {"claude.five_hour", "claude.weekly", "claude.weekly.fable"})
        for sample in samples:
            Contracts().validate("usage-observation", sample)
            self.assertEqual(sample["kind"], "limit")
            self.assertEqual(sample["status"], "available")
            self.assertEqual(sample["source"], "probe")
        self.assertEqual(by_label["claude.five_hour"]["utilization_percent"], 91.5)
        self.assertEqual(by_label["claude.weekly"]["resets_at"], "2026-10-25T00:00:00Z")
        self.assertNoSecret(samples)

    def test_failure_modes_are_unavailable_without_secret(self):
        def write(text):
            (self.config / ".credentials.json").write_text(text)
        cases = {
            "no config dir": (None, fake_transport()),
            "missing dir": (str(self.root / "absent"), fake_transport()),
            "missing credential": (str(self.root / "empty"), fake_transport()),
            "malformed credential": (None, fake_transport()),
            "no token": (None, fake_transport()),
            "http error": (str(self.config), fake_transport(status=401)),
            "transport raised": (str(self.config), fake_transport(raises=OSError("token " + SECRET))),
            "malformed json": (str(self.config), fake_transport(body=b"{not json")),
            "not an object": (str(self.config), fake_transport(body=[1, 2])),
            "bad utilization": (str(self.config), fake_transport(body={"five_hour": {"utilization": 101}})),
            "no limits": (str(self.config), fake_transport(body={"unrelated": 1})),
        }
        (self.root / "empty").mkdir()
        for name, (directory, transport) in cases.items():
            with self.subTest(name):
                if name == "malformed credential":
                    write("{broken " + SECRET)
                    directory = str(self.config)
                elif name == "no token":
                    write(json.dumps({"claudeAiOauth": {"accessToken": ""}}))
                    directory = str(self.config)
                else:
                    write(json.dumps({"claudeAiOauth": {"accessToken": SECRET}}))
                samples = probe_claude_limits(directory, project_id=self.project, transport=transport)
                self.assertEqual(len(samples), 1)
                sample = samples[0]
                Contracts().validate("usage-observation", sample)
                self.assertEqual(sample["status"], "unavailable")
                self.assertEqual(sample["label"], "claude.probe")
                self.assertIsNone(sample["utilization_percent"])
                self.assertTrue(sample["reason"])
                self.assertNoSecret(samples)

    def test_missing_credential_file_does_not_fall_back_to_home(self):
        (self.config / ".credentials.json").unlink()
        samples = probe_claude_limits(str(self.config), project_id=self.project, transport=fake_transport())
        self.assertEqual(samples[0]["status"], "unavailable")
        self.assertNoSecret(samples)


class CodexProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / "codex-home"
        self.project = identifier()

    def tearDown(self):
        self.temp.cleanup()

    def write_session(self, name, rows):
        directory = self.home / "sessions"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text("\n".join(json.dumps(row) for row in rows))

    def test_present_limits_map_to_five_hour_and_weekly(self):
        self.write_session("rollout-a.jsonl", [
            {"type": "event", "timestamp": "2026-10-21T09:00:00Z", "payload": {"rate_limits": {
                "primary": {"used_percent": 10.0, "window_minutes": 300, "resets_at": "2026-10-21T11:00:00Z"},
                "secondary": {"used_percent": 20.0, "window_minutes": 10080, "resets_at": "2026-10-25T00:00:00Z"}}}},
            {"type": "event", "timestamp": "2026-10-21T09:30:00Z", "payload": {"rate_limits": {
                "primary": {"used_percent": 93.0, "window_minutes": 300, "resets_at": "2026-10-21T11:00:00Z"},
                "secondary": {"used_percent": 88.0, "window_minutes": 10080, "resets_at": "2026-10-25T00:00:00Z"}}}},
        ])
        samples = probe_codex_limits(str(self.home), project_id=self.project)
        by_label = {s["label"]: s for s in samples}
        self.assertEqual(set(by_label), {"codex.five_hour", "codex.weekly"})
        self.assertEqual(by_label["codex.five_hour"]["utilization_percent"], 93.0)
        self.assertEqual(by_label["codex.weekly"]["utilization_percent"], 88.0)
        for sample in samples:
            Contracts().validate("usage-observation", sample)
            self.assertEqual(sample["source"], "probe")

    def test_absent_codex_home_is_unavailable(self):
        for home in (None, str(self.home)):
            with self.subTest(home=home):
                samples = probe_codex_limits(home, project_id=self.project)
                self.assertEqual(len(samples), 1)
                self.assertEqual(samples[0]["status"], "unavailable")
                self.assertEqual(samples[0]["label"], "codex.probe")

    def test_session_without_limit_data_is_unavailable(self):
        self.write_session("rollout-b.jsonl", [{"type": "turn.completed", "usage": {"input_tokens": 1}}])
        samples = probe_codex_limits(str(self.home), project_id=self.project)
        self.assertEqual(samples[0]["status"], "unavailable")


class BandTests(unittest.TestCase):
    def test_claude_weekly_boundaries(self):
        expected = {79.9: "clear", 80: "wind_down", 84.9: "wind_down", 85: "ordinary_stop",
                    89.9: "ordinary_stop", 90: "handoff_only", 95: "handoff_only"}
        for value, band in expected.items():
            with self.subTest(value=value):
                self.assertEqual(band_for("claude.weekly", value), band)

    def test_five_hour_and_fable_use_ceiling_95(self):
        self.assertEqual(band_for("claude.five_hour", 85), "wind_down")
        self.assertEqual(band_for("claude.five_hour", 90), "ordinary_stop")
        self.assertEqual(band_for("claude.five_hour", 95), "handoff_only")
        self.assertEqual(band_for("claude.weekly.fable", 94.9), "ordinary_stop")
        self.assertEqual(band_for("codex.weekly", 90), "handoff_only")
        self.assertEqual(set(LIMITS), {"claude.five_hour", "claude.weekly", "claude.weekly.fable",
                                       "codex.five_hour", "codex.weekly"})

    def test_unknown_label_and_missing_value_fall_back_to_legacy(self):
        self.assertIsNone(band_for("claude.weekly.opus", 99))
        self.assertIsNone(band_for("claude.weekly", None))


class UsageStatusBandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.project = identifier()
        stamp = now()
        self.store.create({'schema_version': 1, 'record_type': 'Project', 'id': self.project,
            'rev': 1, 'created_at': stamp, 'updated_at': stamp, 'name': 'synthetic',
            'sources': [], 'delegations': [], 'interface_decision_owner': None})
        self.policy = UsagePolicy(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_status_decision_reports_per_label_band(self):
        self.policy.configure(self.project, {"mode": "observe"}, "cfg-bands")
        samples = probe_claude_limits(None, project_id=self.project, transport=fake_transport())
        self.assertEqual(samples[0]["status"], "unavailable")
        self.policy.usage.ingest(samples[0])
        decision = self.policy.check(self.project, purpose="status", now="2026-10-21T10:00:30Z")
        self.assertEqual(decision["limit_bands"], [])
        self.assertEqual(decision["decision"], "allow")
        self.assertNotIn(SECRET, json.dumps(decision))
        config = Path(self.temp.name) / "claude-login"
        config.mkdir()
        (config / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": SECRET}}))
        recorded = probe_claude_limits(str(config), project_id=self.project, transport=fake_transport(
            body={"five_hour": {"utilization": 91.5, "resets_at": None},
                  "seven_day": {"utilization": 84.9, "resets_at": None}}))
        for sample in recorded:
            sample["observed_at"] = "2026-10-21T10:00:20Z"
            self.policy.usage.ingest(sample)
        decision = self.policy.check(self.project, purpose="status", now="2026-10-21T10:00:30Z")
        bands = {b["label"]: b["band"] for b in decision["limit_bands"]}
        self.assertEqual(bands, {"claude.five_hour": "ordinary_stop", "claude.weekly": "wind_down"})
        Contracts().validate("usage-policy-decision", decision)
        self.assertEqual(decision["decision"], "allow")


if __name__ == "__main__":
    unittest.main()
