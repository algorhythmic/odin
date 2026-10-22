"""Input contracts for workstream sessions and per-lineage turn concurrency."""

import unittest
import uuid
from unittest.mock import Mock

from jsonschema import ValidationError
from odin.contracts import Contracts
from odin.executive_mcp import ExecutiveBridge

PROJECT = "01K7M000000000000000000001"
OPERATION = "01K7M000000000000000000002"


def create_arguments(**extra):
    arguments = {
        "operation_id": OPERATION,
        "action": "create",
        "harness": "codex",
        "workspace": "/srv/odin/workspaces/example",
        "briefing": "Implement the parser stage.",
    }
    arguments.update(extra)
    return arguments


def delegation_config(**extra):
    config = {
        "schema_version": 1,
        "workspace_roots": ["/srv/odin/workspaces"],
        "turn_timeout_seconds": 3600,
        "harnesses": {
            "codex": {
                "binary": "/usr/bin/codex",
                "credential_ref": "secret:codex-main",
                "refresh_owner": "odin",
            }
        },
    }
    config.update(extra)
    return config


class DelegationSessionInputTests(unittest.TestCase):
    def setUp(self):
        self.contracts = Contracts()

    def validate(self, arguments):
        self.contracts.validate_definition(
            "executive-tool-input", "odin_delegation_session", arguments
        )

    def test_create_accepts_workstream_and_role(self):
        for role in ("integration_owner", "workstream"):
            with self.subTest(role=role):
                self.validate(create_arguments(workstream="parser-v2", role=role))

    def test_workstream_label_pattern_is_enforced(self):
        valid = ("a", "parser.v2", "ws_1-b", "x" * 64)
        invalid = ("", "Parser", "-leading", ".leading", "has space", "x" * 65)
        for label in valid:
            with self.subTest(valid=label):
                self.validate(create_arguments(workstream=label))
        for label in invalid:
            with self.subTest(invalid=label), self.assertRaises(ValidationError):
                self.validate(create_arguments(workstream=label))

    def test_unknown_role_is_rejected(self):
        for role in ("owner", "Workstream", "", None):
            with self.subTest(role=role), self.assertRaises(ValidationError):
                self.validate(create_arguments(role=role))

    def test_other_unknown_fields_are_still_rejected(self):
        with self.assertRaises(ValidationError):
            self.validate(create_arguments(lane="parser"))

    def test_wrapped_tool_input_carries_workstream_and_role(self):
        self.contracts.validate(
            "executive-tool-input",
            {
                "name": "odin_delegation_session",
                "arguments": create_arguments(workstream="docs", role="workstream"),
            },
        )
        with self.assertRaises(ValidationError):
            self.contracts.validate(
                "executive-tool-input",
                {
                    "name": "odin_delegation_session",
                    "arguments": create_arguments(role="lead"),
                },
            )

    def test_bridge_refuses_bad_role_before_gateway_dispatch(self):
        gateway = Mock()
        bridge = ExecutiveBridge(PROJECT, gateway)
        with self.assertRaises(ValidationError):
            bridge.call(
                "odin_delegation_session",
                create_arguments(role="lead") | {"operation_id": OPERATION},
            )
        gateway.assert_not_called()


class ExecutiveToolListingTests(unittest.TestCase):
    def test_delegation_session_listing_exposes_workstream_and_role(self):
        bridge = ExecutiveBridge(PROJECT, Mock(), session_id=str(uuid.uuid4()))
        tool = next(
            item for item in bridge.tools() if item["name"] == "odin_delegation_session"
        )
        properties = tool["inputSchema"]["properties"]
        self.assertEqual(properties["workstream"]["pattern"], "^[a-z0-9][a-z0-9._-]{0,63}$")
        self.assertEqual(properties["role"]["enum"], ["integration_owner", "workstream"])
        self.assertFalse(tool["inputSchema"]["additionalProperties"])
        self.assertIn("integration-owner session", tool["description"])
        self.assertIn("workstream", tool["description"])


class DelegationConfigConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.contracts = Contracts()

    def test_accepts_bounded_concurrency_values(self):
        for value in (1, 8):
            with self.subTest(value=value):
                self.contracts.validate(
                    "delegation-config",
                    delegation_config(max_concurrent_turns_per_lineage=value),
                )

    def test_absent_key_remains_valid(self):
        self.contracts.validate("delegation-config", delegation_config())

    def test_rejects_out_of_range_values(self):
        for value in (0, 9, -1, 1.5, "2", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.contracts.validate(
                    "delegation-config",
                    delegation_config(max_concurrent_turns_per_lineage=value),
                )


if __name__ == "__main__":
    unittest.main()
