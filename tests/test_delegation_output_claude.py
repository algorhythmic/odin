"""Synthetic Claude output parser tests; no harness, credential or network."""

import json
import unittest

from odin.delegation_output import MAX_FINAL_TEXT, parse_claude_json


class ClaudeOutputParserTests(unittest.TestCase):
    def test_successful_result_preserves_supported_fields(self):
        body = {
            "session_id": "synthetic-session",
            "result": "Worker report.",
            "is_error": False,
            "stop_reason": "end_turn",
            "num_turns": 3,
            "total_cost_usd": 0.125,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 40,
                "unrecognized_tokens": 999,
            },
            "permission_denials": [],
            "unrecognized_field": "ignored",
        }
        self.assertEqual(
            parse_claude_json(json.dumps(body)),
            {
                "native_session_id": "synthetic-session",
                "final_text": "Worker report.",
                "is_error": False,
                "stop_reason": "end_turn",
                "turns": 3,
                "cost_usd": 0.125,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "cache_read_input_tokens": 30,
                    "cache_creation_input_tokens": 40,
                },
                "permission_denials": 0,
                "parse_error": None,
            },
        )

    def test_empty_object_has_neutral_defaults(self):
        self.assertEqual(
            parse_claude_json("{}"),
            {
                "native_session_id": None,
                "final_text": "",
                "is_error": False,
                "stop_reason": None,
                "turns": None,
                "cost_usd": None,
                "usage": None,
                "permission_denials": None,
                "parse_error": None,
            },
        )

    def test_pretty_printed_json_and_outer_whitespace_are_accepted(self):
        stdout = "\n \t" + json.dumps({"result": "  report\n"}, indent=2) + "\n\t "
        result = parse_claude_json(stdout)
        self.assertIsNone(result["parse_error"])
        self.assertEqual(result["final_text"], "  report\n")

    def test_leading_diagnostics_use_last_nonempty_json_line(self):
        stdout = (
            "synthetic diagnostic\n"
            '{"result": "earlier report"}\n\n'
            '  {"session_id": "synthetic-final", "result": "final report"}  \n\n'
        )
        result = parse_claude_json(stdout)
        self.assertIsNone(result["parse_error"])
        self.assertEqual(result["native_session_id"], "synthetic-final")
        self.assertEqual(result["final_text"], "final report")

    def test_empty_stdout_has_specific_parse_error(self):
        for stdout in ("", " ", "\n\t\r\n"):
            with self.subTest(stdout=repr(stdout)):
                self.assertEqual(
                    parse_claude_json(stdout), {"parse_error": "empty stdout"}
                )

    def test_malformed_and_nonobject_json_are_rejected(self):
        for stdout in (
            "not JSON",
            '{"result":',
            '{"result": "trailing comma",}',
            "null",
            "true",
            "42",
            '"a string"',
            "[]",
            '[{"result": "nested object"}]',
            "diagnostic\nnull",
        ):
            with self.subTest(stdout=stdout):
                self.assertEqual(
                    parse_claude_json(stdout),
                    {"parse_error": "stdout is not a JSON result object"},
                )

    def test_result_list_joins_text_blocks_and_strings_in_order(self):
        body = {
            "result": [
                {"type": "text", "text": "first"},
                {"type": "tool_use", "text": "ignored tool output"},
                "second",
                None,
                12,
                {"text": "ignored untyped block"},
                {"type": "text", "text": "third"},
            ]
        }
        self.assertEqual(
            parse_claude_json(json.dumps(body))["final_text"], "first\nsecond\nthird"
        )

    def test_unsupported_result_values_produce_empty_text(self):
        for value in (None, True, 7, 1.5, {"text": "unwrapped"}, [], [None, 7]):
            with self.subTest(value=value):
                result = parse_claude_json(json.dumps({"result": value}))
                self.assertIsNone(result["parse_error"])
                self.assertEqual(result["final_text"], "")

    def test_string_result_is_bounded_by_characters(self):
        for length in (MAX_FINAL_TEXT - 1, MAX_FINAL_TEXT, MAX_FINAL_TEXT + 1):
            with self.subTest(length=length):
                text = "é" * length
                result = parse_claude_json(json.dumps({"result": text}))
                self.assertEqual(result["final_text"], text[:MAX_FINAL_TEXT])
                self.assertEqual(len(result["final_text"]), min(length, MAX_FINAL_TEXT))

    def test_list_result_is_bounded_after_joining(self):
        prefix = "x" * (MAX_FINAL_TEXT - 3)
        body = {"result": [prefix, {"type": "text", "text": "tail"}]}
        result = parse_claude_json(json.dumps(body))
        self.assertEqual(result["final_text"], prefix + "\nta")
        self.assertEqual(len(result["final_text"]), MAX_FINAL_TEXT)

    def test_session_and_stop_reason_reject_nonstring_metadata(self):
        for value in (None, True, 0, 1.5, [], {}):
            with self.subTest(value=value):
                result = parse_claude_json(
                    json.dumps({"session_id": value, "stop_reason": value})
                )
                self.assertIsNone(result["native_session_id"])
                self.assertIsNone(result["stop_reason"])
        result = parse_claude_json('{"session_id": "", "stop_reason": ""}')
        self.assertIsNone(result["native_session_id"])
        self.assertEqual(result["stop_reason"], "")

    def test_turns_require_integer_and_cost_requires_nonboolean_number(self):
        for value in (None, True, False, "2", [], {}):
            with self.subTest(value=value):
                result = parse_claude_json(
                    json.dumps({"num_turns": value, "total_cost_usd": value})
                )
                self.assertIsNone(result["turns"])
                self.assertIsNone(result["cost_usd"])
        result = parse_claude_json('{"num_turns": 2.0, "total_cost_usd": 2.5}')
        self.assertIsNone(result["turns"])
        self.assertEqual(result["cost_usd"], 2.5)
        for value in (0, 2):
            with self.subTest(integer=value):
                result = parse_claude_json(
                    json.dumps({"num_turns": value, "total_cost_usd": value})
                )
                self.assertEqual(result["turns"], value)
                self.assertIs(type(result["turns"]), int)
                self.assertEqual(result["cost_usd"], float(value))
                self.assertIs(type(result["cost_usd"]), float)

    def test_usage_filters_each_known_token_count_to_integers(self):
        keys = (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        )
        for key in keys:
            for value in (True, False, None, "5", 5.0, [], {}):
                with self.subTest(key=key, value=value):
                    usage = dict.fromkeys(keys, 0)
                    usage[key] = value
                    usage["extra_tokens"] = 123
                    result = parse_claude_json(json.dumps({"usage": usage}))
                    self.assertEqual(
                        result["usage"], {other: 0 for other in keys if other != key}
                    )

    def test_empty_or_invalid_usage_is_distinct_from_filtered_usage(self):
        for usage in (None, {}, [], True, 12, "tokens"):
            with self.subTest(usage=usage):
                result = parse_claude_json(json.dumps({"usage": usage}))
                self.assertIsNone(result["usage"])
        result = parse_claude_json('{"usage": {"unknown_tokens": 5}}')
        self.assertEqual(result["usage"], {})

    def test_permission_denials_count_list_entries_only(self):
        for denials, expected in (
            ([], 0),
            ([{"tool_name": "synthetic-tool"}, {"tool_name": "other-tool"}], 2),
            ([None, "synthetic denial", {}], 3),
            (None, None),
            ({}, None),
            ("denied", None),
            (True, None),
            (2, None),
        ):
            with self.subTest(denials=denials):
                result = parse_claude_json(json.dumps({"permission_denials": denials}))
                self.assertEqual(result["permission_denials"], expected)

    def test_error_flag_does_not_discard_report_or_change_parse_status(self):
        body = {
            "is_error": True,
            "result": "Synthetic harness failure.",
            "stop_reason": "error",
        }
        result = parse_claude_json(json.dumps(body))
        self.assertIs(result["is_error"], True)
        self.assertEqual(result["final_text"], "Synthetic harness failure.")
        self.assertEqual(result["stop_reason"], "error")
        self.assertIsNone(result["parse_error"])
        body["is_error"] = False
        result = parse_claude_json(json.dumps(body))
        self.assertIs(result["is_error"], False)


if __name__ == "__main__":
    unittest.main()
