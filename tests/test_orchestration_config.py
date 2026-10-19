"""Synthetic role requests only; no model, Saga, or session host execution."""

import json
import tempfile
import unittest
from pathlib import Path

from odin.orchestration_config import OrchestrationConfig
from odin.store import Conflict


class OrchestrationConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = OrchestrationConfig()

    def observation(self, role):
        intent = self.config.intent(role, "project:synthetic", "session:synthetic", 1)
        spec = self.config.data["roles"][role]
        worker = intent["execution_path"] == "saga_api"
        return {
            "intent": intent,
            "resolved_model": spec["model"],
            "resolved_provider": spec["provider"],
            "resolved_harness": spec["harness"],
            "resolved_harness_version": spec["harness_version"],
            "resolved_effort": spec["effort"],
            "execution_path": spec["execution_path"],
            "cli_version": spec["cli_observed_version"],
            "capabilities": spec["required_capabilities"],
            "native_session_id": None if worker else "native:synthetic",
            "run_id": "run:synthetic" if worker else None,
            "request_id": "request:synthetic" if worker else None,
        }

    def test_roles_and_paths(self):
        identities = {
            "fable": "claude-fable-5-1",
            "astra": "gpt-6-astra",
            "opus": "claude-opus-5-5",
            "sol": "gpt-6-sol",
        }
        for role, model in identities.items():
            intent = self.config.intent(role, "project:x", "session:y", 1)
            self.assertEqual(intent["requested_model"], model)
            self.assertFalse(intent["live_enabled"])
            self.assertEqual(
                intent["execution_path"],
                "saga_api" if role in ("opus", "sol") else "service_session",
            )
            self.assertTrue(
                self.config.verify_observation(role, self.observation(role))
            )
        with self.assertRaises(Conflict):
            self.config.intent("astra", "p", "s", 1, mode="implementation")
        with self.assertRaises(Conflict):
            self.config.intent("sol", "p", "s", 1, mode="advice")
        self.assertEqual(
            self.config.intent("astra", "p", "s", 1, mode="advice")["mode"], "advice"
        )

    def test_missing_capabilities_and_live_gate(self):
        with self.assertRaises(Conflict):
            self.config.intent(
                "opus", "p", "s", 1, available_capabilities=["run_record"]
            )
        capabilities = self.config.data["roles"]["opus"]["required_capabilities"]
        with self.assertRaises(PermissionError):
            self.config.intent(
                "opus",
                "p",
                "s",
                1,
                available_capabilities=capabilities,
                for_launch=True,
            )
        with self.assertRaises(Conflict):
            self.config.intent("opus", "p", "s", 1, for_launch=True)

    def test_observation_rejects_substitution_and_missing_binding(self):
        for field, changed in [
            ("resolved_model", "other-model"),
            ("resolved_provider", "other"),
            ("resolved_harness", "other"),
            ("resolved_harness_version", "0.0"),
            ("resolved_effort", "low"),
            ("execution_path", "saga_api"),
        ]:
            observation = self.observation("astra")
            observation[field] = changed
            with self.subTest(field=field), self.assertRaises(Conflict):
                self.config.verify_observation("astra", observation)
        observation = self.observation("astra")
        observation["native_session_id"] = None
        with self.assertRaises(Conflict):
            self.config.verify_observation("astra", observation)
        observation = self.observation("sol")
        observation["run_id"] = None
        with self.assertRaises(Conflict):
            self.config.verify_observation("sol", observation)
        observation = self.observation("fable")
        observation["cli_version"] = "2.1.297"
        with self.assertRaises(Conflict):
            self.config.verify_observation("fable", observation)

    def test_config_revision_and_closed_schema(self):
        observation = self.observation("sol")
        observation["intent"]["config_rev"] = "unreviewed"
        with self.assertRaises(Conflict):
            self.config.verify_observation("sol", observation)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            data = json.loads(Path(self.config.path).read_text())
            data["roles"]["sol"]["model"] = "gpt-6-astra"
            data["extra"] = True
            path.write_text(json.dumps(data))
            with self.assertRaises(Exception):
                OrchestrationConfig(path)


if __name__ == "__main__":
    unittest.main()
