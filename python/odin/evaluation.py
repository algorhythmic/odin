"""Deterministic offline comparison of frozen synthetic episodes.

Caller-provided strings are claims. Independent assessments and condition
observations need a trusted resolver, or explicit fixture mode.
"""

from collections import defaultdict

from .contracts import Contracts, canonical
from .policy import account
from .store import digest

ATTENTION = (
    "restatements",
    "corrections",
    "interruptions",
    "decision_wait_seconds",
    "missed_obligations",
    "stale_claims",
)
VARIATION = {
    "semantic_memory": {"memory_features"},
    "compactor": {"compactor_digest"},
    "orchestration": {"orchestration"},
}


def _evidence(kind, value, project, resolver, fixture_mode):
    if fixture_mode and value["ref"].startswith("fixture:"):
        return
    if resolver is None:
        raise ValueError("unresolved " + kind + " evidence")
    observed = resolver(kind, value["ref"], project=project)
    expected = value | {"project": project}
    if not isinstance(observed, dict) or any(
        observed.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("changed or mismatched " + kind + " evidence")


def _observed_controls(item, condition, config, resolver, fixture_mode):
    episode = item["episode"]
    if episode["fixture_digest"] != config["fixture_digest"]:
        raise ValueError("episode fixture differs from frozen config")
    if (
        episode["context"]["tools"] != condition["tools"]
        or episode["context"]["retrieval_digest"] != condition["retriever_digest"]
    ):
        raise ValueError("observed tools or retriever differ from config")
    if digest(episode["limits"]) != condition["resource_policy_digest"]:
        raise ValueError("observed resource policy differs from config")
    control = item["condition_evidence"]
    if any(
        control[key] != condition[key]
        for key in ("compactor_digest", "memory_features", "orchestration")
    ):
        raise ValueError("observed condition differs from config")
    _evidence("condition", control, item["project"], resolver, fixture_mode)
    for part in episode["cost_components"]:
        if part["role"] != "parent":
            continue
        identity = part["identity"]
        for key in (
            "provider",
            "harness",
            "harness_version",
            "adapter_version",
            "effort",
        ):
            if identity[key] != condition[key]:
                raise ValueError("observed parent identity differs from config")
        if condition["model"] not in (
            identity["resolved_model"],
            identity["model_alias"],
        ):
            raise ValueError("observed parent model differs from config")
        if identity["resolved_model"] is None and not fixture_mode:
            raise ValueError("resolved model identity unknown")
        if part["tools"] != condition["tools"]:
            raise ValueError("observed parent tools differ from config")


def evaluate(config, episodes, *, evidence_resolver=None, allow_fixture_evidence=False):
    """Analyze paired episodes; never infer missing money or token telemetry."""
    contracts = Contracts()
    contracts.validate("evaluation-config", config)
    if not episodes:
        raise ValueError("evaluation needs observations")
    conditions = {item["name"]: item for item in config["conditions"]}
    if len(conditions) != len(config["conditions"]):
        raise ValueError("duplicate condition")
    first = config["conditions"][0]
    allowed = VARIATION[config["experiment"]]
    if all(
        all(c[key] == first[key] for key in allowed) for c in config["conditions"][1:]
    ):
        raise ValueError("experiment has no controlled variation")
    for condition in config["conditions"][1:]:
        differences = {
            key for key in first if key != "name" and condition[key] != first[key]
        }
        if not differences <= allowed:
            raise ValueError(
                "comparison confound: " + ", ".join(sorted(differences - allowed))
            )

    observed = defaultdict(list)
    lineages = defaultdict(dict)
    task_controls = defaultdict(dict)
    attempt_controls = {}
    deadlines = {}
    attempts = defaultdict(set)
    episode_ids = set()
    for item in episodes:
        contracts.validate("evaluation-observation", item)
        episode = item["episode"]
        contracts.validate("evaluation-episode", episode)
        name = episode["condition"]
        if name not in conditions:
            raise ValueError("unconfigured condition")
        _observed_controls(
            item, conditions[name], config, evidence_resolver, allow_fixture_evidence
        )
        assessment = item["assessment"]
        if (
            assessment["episode_id"] != episode["episode_id"]
            or assessment["accepted"] != episode["accepted"]
            or assessment["evidence_digest"] != digest(episode["acceptance_evidence"])
            or assessment["usage_digest"]
            != digest(
                {
                    "billing": episode["billing"],
                    "cost_microusd": episode["cost_microusd"],
                    "cost_components": episode["cost_components"],
                }
            )
        ):
            raise ValueError("assessment does not bind episode evidence")
        _evidence(
            "assessment",
            assessment,
            item["project"],
            evidence_resolver,
            allow_fixture_evidence,
        )
        if episode["episode_id"] in episode_ids:
            raise ValueError("duplicate episode id")
        episode_ids.add(episode["episode_id"])
        task = (item["project"], episode["task_lineage"])
        key = (name, task)
        if episode["attempt"] in attempts[key]:
            raise ValueError("duplicate lineage attempt")
        attempts[key].add(episode["attempt"])
        deadline = deadlines.setdefault(key, episode["deadline_seconds"])
        if deadline != episode["deadline_seconds"]:
            raise ValueError("task deadline changed across attempts")
        if not episode["cost_components"]:
            raise ValueError("all attempts need operation accounting")
        if episode["attempt"] == 1 and not any(
            part["role"] == "parent" for part in episode["cost_components"]
        ):
            raise ValueError("initial attempt needs parent accounting")
        if episode["billing"]["repriced"]:
            raise ValueError("repricing is not a comparable rerun")
        identities = {
            part["identity"][field]
            for part in episode["cost_components"]
            for field in ("resolved_model", "model_alias")
        }
        if episode["accepted"] and assessment["assessor"] in identities:
            raise ValueError("accepted result needs independent assessor")
        sources = item["source_revisions"]
        if len({source["source"] for source in sources}) != len(sources):
            raise ValueError("duplicate source revision")
        frozen = (
            episode["fixture_digest"],
            episode["split"],
            canonical(sorted(sources, key=lambda source: source["source"])),
        )
        previous = lineages[task].setdefault(name, frozen)
        if previous != frozen:
            raise ValueError("task source or split changed within a condition")
        controls = tuple(
            canonical(value)
            for value in (
                episode["billing"],
                episode["limits"],
                episode["context"]["tools"],
                episode["context"]["retrieval_digest"],
            )
        )
        if attempt_controls.setdefault(key, controls) != controls:
            raise ValueError(
                "billing, limits, tools or retriever changed across attempts"
            )
        if episode["attempt"] == 1:
            parent = [
                p["identity"]
                for p in episode["cost_components"]
                if p["role"] == "parent"
            ]
            task_controls[task][name] = controls + (canonical(parent[:1]),)
        observed[name].append(item)

    expected_tasks = set(lineages)
    for name in conditions:
        actual = {
            (item["project"], item["episode"]["task_lineage"])
            for item in observed[name]
        }
        if actual != expected_tasks:
            raise ValueError("conditions lack paired project/task lineages")
        for task in actual:
            nums = attempts[(name, task)]
            if nums != set(range(1, max(nums) + 1)):
                raise ValueError("attempt numbering has a gap")
    for task, pairs in lineages.items():
        if len({canonical(value) for value in pairs.values()}) != 1:
            raise ValueError(
                "fixture, split or source revisions differ across conditions: "
                + str(task)
            )
        if len({canonical(value) for value in task_controls[task].values()}) != 1:
            raise ValueError(
                "observed billing, limits, tools or retriever confound: " + str(task)
            )

    reports = []
    for name in conditions:
        items = observed[name]
        stats = account(name, [item["episode"] for item in items])
        tasks = defaultdict(list)
        for item in items:
            tasks[(item["project"], item["episode"]["task_lineage"])].append(
                item["episode"]
            )
        for task in tasks:
            tasks[task].sort(key=lambda episode: episode["attempt"])
        task_elapsed = [
            sum(ep["elapsed_seconds"] for ep in tasks[t]) for t in sorted(tasks)
        ]
        reports.append(
            {
                "name": name,
                "accounting": stats,
                "attention": {
                    key: sum(item["attention"][key] for item in items)
                    for key in ATTENTION
                },
                "known_operator_seconds": sum(
                    item["episode"]["operator_seconds"] or 0 for item in items
                ),
                "missing_operator_time": sum(
                    item["episode"]["operator_seconds"] is None for item in items
                ),
                "incomplete_token_episodes": sum(
                    any(
                        part[field] is None
                        for part in item["episode"]["cost_components"]
                        for field in (
                            "input_tokens",
                            "output_tokens",
                            "cache_read_tokens",
                            "cache_write_tokens",
                        )
                    )
                    for item in items
                ),
                "task_elapsed_seconds": task_elapsed,
                "deadline_successes": sum(
                    any(ep["accepted"] for ep in tasks[t])
                    and tasks[t][0]["deadline_seconds"] is not None
                    and sum(ep["elapsed_seconds"] for ep in tasks[t])
                    <= tasks[t][0]["deadline_seconds"]
                    for t in tasks
                ),
            }
        )
    report = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "experiment": config["experiment"],
        "frozen_revision": config["frozen_revision"],
        "label": "offline fixture analysis",
        "lineages": [
            {"project": project, "task_lineage": lineage}
            for project, lineage in sorted(expected_tasks)
        ],
        "conditions": reports,
        "ranking": None,
    }
    contracts.validate("evaluation-run", report)
    return report
