"""Experimental model-role requests and fixture-only launch intentions.

This module neither launches a model nor conveys authority. Observations must
come from a separately trusted host/Saga adapter; names alone prove nothing.
"""

from pathlib import Path

from jsonschema import Draft202012Validator

from .contracts import ROOT, Contracts, canonical, strict_loads
from .store import Conflict


class OrchestrationConfig:
    def __init__(self, path=None):
        self.contracts = Contracts()
        self.path = Path(path or ROOT / "fixtures/orchestration-config.json")
        self.data = strict_loads(self.path.read_text())
        self.contracts.validate("orchestration-config", self.data)

    @property
    def config_rev(self):
        return self.data["config_rev"]

    def intent(
        self,
        role,
        project,
        session,
        incarnation,
        *,
        mode=None,
        available_capabilities=None,
        for_launch=False,
    ):
        if role not in self.data["roles"]:
            raise KeyError(role)
        spec = self.data["roles"][role]
        worker = role in ("opus", "sol")
        mode = mode or ("implementation" if worker else "plan")
        if worker != (mode == "implementation"):
            raise Conflict("implementation requires Saga worker path")
        if mode not in ("plan", "advice", "implementation"):
            raise Conflict("unknown intent mode")
        if worker != (spec["execution_path"] == "saga_api"):
            raise Conflict("role path mismatch")
        required = set(spec["required_capabilities"])
        if available_capabilities is not None and not required <= set(
            available_capabilities
        ):
            raise Conflict("required capabilities unavailable")
        if for_launch:
            if available_capabilities is None:
                raise Conflict("launch capability matrix required")
            raise PermissionError(
                "live model dispatch unavailable: X-12/X-13/X-15 and I3"
            )
        intent = {
            "schema_version": 1,
            "config_rev": self.config_rev,
            "role": role,
            "project": project,
            "session": session,
            "incarnation": incarnation,
            "mode": mode,
            "requested_model": spec["model"],
            "requested_provider": spec["provider"],
            "requested_harness": spec["harness"],
            "requested_harness_version": spec["harness_version"],
            "requested_effort": spec["effort"],
            "execution_path": spec["execution_path"],
            "required_capabilities": spec["required_capabilities"],
            "live_enabled": False,
        }
        self.contracts.validate("session-intent", intent)
        return intent

    def verify_observation(self, role, observation):
        """Check a trusted adapter receipt against the exact requested identity.

        Return a validated copy; this check cannot establish authentication or
        authorize execution by itself.
        """
        schema = self.contracts.validators["session-intent"].schema["$defs"][
            "observation"
        ]
        Draft202012Validator(schema).validate(observation)
        canonical(observation)
        intent = observation["intent"]
        self.contracts.validate("session-intent", intent)
        if role != intent["role"] or intent["config_rev"] != self.config_rev:
            raise Conflict("stale or mismatched config revision")
        expected = self.intent(
            role,
            intent["project"],
            intent["session"],
            intent["incarnation"],
            mode=intent["mode"],
        )
        if intent != expected:
            raise Conflict("intent does not match configured identity")
        spec = self.data["roles"][role]
        comparisons = {
            "resolved_model": "model",
            "resolved_provider": "provider",
            "resolved_harness": "harness",
            "resolved_effort": "effort",
            "execution_path": "execution_path",
            "cli_version": "cli_observed_version",
        }
        if any(observation[field] != spec[key] for field, key in comparisons.items()):
            raise Conflict("observed model identity changed")
        if (
            spec["harness_version"] is not None
            and observation["resolved_harness_version"] != spec["harness_version"]
        ):
            raise Conflict("observed harness version changed")
        if not set(spec["required_capabilities"]) <= set(observation["capabilities"]):
            raise Conflict("observed capabilities incomplete")
        if spec["execution_path"] == "saga_api":
            if (
                not observation["request_id"]
                or not observation["run_id"]
                or observation["native_session_id"] is not None
            ):
                raise Conflict("Saga run binding missing")
        elif (
            not observation["native_session_id"]
            or observation["run_id"] is not None
            or observation["request_id"] is not None
        ):
            raise Conflict("session binding missing")
        return observation.copy()
