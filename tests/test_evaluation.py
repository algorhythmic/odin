import copy
import json
import os
import subprocess
import sys
import unittest

from odin.contracts import ROOT, Contracts
from odin.evaluation import evaluate
from odin.store import digest


class EvaluationTests(unittest.TestCase):
    def test_cli_fixture_evidence_requires_explicit_opt_in(self):
        command = [
            sys.executable,
            "-m",
            "odin",
            "evaluate",
            "--request",
            str(ROOT / "fixtures/synthetic-evaluation-request.json"),
        ]
        env = os.environ | {"PYTHONPATH": str(ROOT / "python")}
        rejected = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(rejected.stdout, "")
        accepted = subprocess.run(
            command + ["--fixture-evidence"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(accepted.stdout)
        self.assertEqual(report["label"], "offline fixture analysis")
        self.assertIsNone(report["ranking"])

    def setUp(self):
        self.config = json.loads(
            (ROOT / "fixtures/evaluation-contracts.json").read_text()
        )["cases"][0]["value"]
        self.template = json.loads(
            (ROOT / "fixtures/evaluation-episode.json").read_text()
        )

    def observation(self, condition, *, attempt=1, accepted=True, cost=7):
        episode = copy.deepcopy(self.template)
        episode.update(
            episode_id=f"{condition}-{attempt}",
            condition=condition,
            attempt=attempt,
            accepted=accepted,
            result_status="complete" if accepted else "failed",
            acceptance_evidence=["independent-check-1"] if accepted else [],
            failure=None if accepted else "synthetic test failure",
            cost_microusd=cost,
            elapsed_seconds=10 + attempt,
            operator_seconds=3,
            deadline_seconds=20,
        )
        episode["cost_components"][0].update(
            operation=f"{condition}-{attempt}-call",
            role="parent" if attempt == 1 else "repair",
            cost_microusd=cost,
        )
        episode["context"]["retrieval_digest"] = "retriever-1"
        return {
            "project": "project-1",
            "episode": episode,
            "source_revisions": [
                {"source": "requirements", "revision": 2, "digest": "source-digest-2"}
            ],
            "condition_evidence": {
                "ref": f"fixture:condition:{condition}",
                "compactor_digest": "compactor-1",
                "memory_features": []
                if condition == "baseline"
                else ["status", "time", "provenance"],
                "orchestration": "solo",
            },
            "assessment": {
                "ref": f"fixture:assessment:{condition}:{attempt}",
                "assessor": "independent-reviewer",
                "episode_id": episode["episode_id"],
                "accepted": accepted,
                "evidence_digest": digest(episode["acceptance_evidence"]),
                "usage_digest": digest(
                    {
                        "billing": episode["billing"],
                        "cost_microusd": episode["cost_microusd"],
                        "cost_components": episode["cost_components"],
                    }
                ),
            },
            "attention": {
                "restatements": 1 if condition == "baseline" else 0,
                "corrections": 1 if condition == "baseline" else 0,
                "interruptions": 0,
                "decision_wait_seconds": 5,
                "missed_obligations": 0,
                "stale_claims": 0,
            },
        }

    def test_counts_failed_repair_and_attention_without_ranking(self):
        items = [
            self.observation("baseline", accepted=False),
            self.observation("baseline", attempt=2, cost=11),
            self.observation("typed"),
        ]
        report = evaluate(self.config, items, allow_fixture_evidence=True)
        baseline = report["conditions"][0]
        self.assertEqual(baseline["accounting"]["attempted"], 2)
        self.assertEqual(baseline["accounting"]["known_cost_microusd"], 18)
        self.assertEqual(baseline["accounting"]["accepted"], 1)
        self.assertEqual(baseline["attention"]["restatements"], 2)
        self.assertEqual(baseline["task_elapsed_seconds"], [23])
        self.assertEqual(baseline["deadline_successes"], 0)
        self.assertEqual(baseline["incomplete_token_episodes"], 2)
        self.assertIsNone(report["ranking"])
        self.assertEqual(report["label"], "offline fixture analysis")

    def test_unknown_cost_remains_unknown(self):
        baseline = self.observation("baseline")
        baseline["episode"]["cost_microusd"] = None
        part = baseline["episode"]["cost_components"][0]
        part["cost_microusd"] = None
        part["missing_reason"] = "fixture telemetry absent"
        baseline["assessment"]["usage_digest"] = digest(
            {
                "billing": baseline["episode"]["billing"],
                "cost_microusd": baseline["episode"]["cost_microusd"],
                "cost_components": baseline["episode"]["cost_components"],
            }
        )
        report = evaluate(
            self.config,
            [baseline, self.observation("typed")],
            allow_fixture_evidence=True,
        )
        stats = report["conditions"][0]["accounting"]
        self.assertEqual(stats["missing_cost_episodes"], 1)
        self.assertIsNone(stats["cost_per_accepted_microusd"])

    def test_confounds_and_unpaired_sources_refused(self):
        items = [self.observation("baseline"), self.observation("typed")]
        changed = copy.deepcopy(self.config)
        changed["conditions"][1]["model"] = "other-model"
        with self.assertRaisesRegex(ValueError, "confound"):
            evaluate(changed, items, allow_fixture_evidence=True)
        items[1]["source_revisions"][0]["revision"] = 3
        with self.assertRaisesRegex(ValueError, "source revisions differ"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_assessment_binds_usage_telemetry(self):
        items = [self.observation("baseline"), self.observation("typed")]
        items[0]["episode"]["cost_microusd"] = 100
        with self.assertRaisesRegex(ValueError, "assessment does not bind"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_duplicates_gaps_and_missing_independent_assessor_refused(self):
        items = [self.observation("baseline"), self.observation("typed")]
        with self.assertRaisesRegex(ValueError, "duplicate episode id"):
            evaluate(self.config, items + [items[0]], allow_fixture_evidence=True)
        items[0]["episode"]["attempt"] = 2
        with self.assertRaisesRegex(ValueError, "attempt numbering"):
            evaluate(self.config, items, allow_fixture_evidence=True)
        items[0]["episode"]["attempt"] = 1
        items[0]["assessment"]["assessor"] = "fixture/no-model"
        with self.assertRaisesRegex(ValueError, "independent assessor"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_retry_cannot_change_limits_or_billing(self):
        items = [
            self.observation("baseline", accepted=False),
            self.observation("baseline", attempt=2),
            self.observation("typed"),
        ]
        items[1]["episode"]["limits"]["turns"] = 99
        with self.assertRaisesRegex(ValueError, "resource policy"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_both_arms_changed_from_frozen_config_are_refused(self):
        items = [self.observation("baseline"), self.observation("typed")]
        for item in items:
            part = item["episode"]["cost_components"][0]
            part["identity"]["model_alias"] = "other-model"
            part["identity"]["harness"] = "other-harness"
            part["tools"] = ["other-tool"]
            item["episode"]["context"]["tools"] = ["other-tool"]
        with self.assertRaisesRegex(ValueError, "tools or retriever"):
            evaluate(self.config, items, allow_fixture_evidence=True)
        for item in items:
            item["episode"]["context"]["tools"] = self.config["conditions"][0]["tools"]
        with self.assertRaisesRegex(ValueError, "parent identity"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_unresolved_assessment_and_wrong_project_pairing_are_refused(self):
        items = [self.observation("baseline"), self.observation("typed")]
        with self.assertRaisesRegex(ValueError, "unresolved condition"):
            evaluate(self.config, items)
        items[1]["project"] = "other-project"
        with self.assertRaisesRegex(ValueError, "paired project/task"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_deadline_is_order_independent_and_pinned(self):
        items = [
            self.observation("baseline", accepted=False),
            self.observation("baseline", attempt=2),
            self.observation("typed"),
        ]
        forward = evaluate(self.config, items, allow_fixture_evidence=True)
        reverse = evaluate(
            self.config, list(reversed(items)), allow_fixture_evidence=True
        )
        self.assertEqual(
            forward["conditions"][0]["deadline_successes"],
            reverse["conditions"][0]["deadline_successes"],
        )
        items[1]["episode"]["deadline_seconds"] = 100
        with self.assertRaisesRegex(ValueError, "deadline changed"):
            evaluate(self.config, items, allow_fixture_evidence=True)

    def test_separate_experiment_control_fields(self):
        items = [self.observation("baseline"), self.observation("typed")]
        config = copy.deepcopy(self.config)
        config["experiment"] = "compactor"
        with self.assertRaisesRegex(ValueError, "no controlled variation"):
            evaluate(config, items, allow_fixture_evidence=True)
        config["conditions"][1]["memory_features"] = []
        config["conditions"][1]["compactor_digest"] = "other-compactor"
        for item in items:
            item["condition_evidence"]["memory_features"] = []
        items[1]["condition_evidence"]["compactor_digest"] = "other-compactor"
        evaluate(config, items, allow_fixture_evidence=True)
        config["conditions"][1]["retriever_digest"] = "other-retriever"
        with self.assertRaisesRegex(ValueError, "retriever_digest"):
            evaluate(config, items, allow_fixture_evidence=True)

    def test_contract_fixtures(self):
        cases = json.loads((ROOT / "fixtures/evaluation-contracts.json").read_text())[
            "cases"
        ]
        validators = Contracts().validators
        for case in cases:
            with self.subTest(case["name"]):
                self.assertEqual(
                    validators[case["schema"]].is_valid(case["value"]), case["valid"]
                )

    def test_synthetic_request_file_is_explicit_fixture_only(self):
        request = json.loads(
            (ROOT / "fixtures/synthetic-evaluation-request.json").read_text()
        )
        Contracts().validate("evaluation-request", request)
        with self.assertRaisesRegex(ValueError, "unresolved condition"):
            evaluate(request["config"], request["observations"])
        report = evaluate(
            request["config"], request["observations"], allow_fixture_evidence=True
        )
        self.assertEqual(report["label"], "offline fixture analysis")


if __name__ == "__main__":
    unittest.main()
