"""Synthetic Codex output parser checks; no harness, credential or network."""

import json
import unittest

from odin.delegation_output import (
    MAX_FINAL_TEXT,
    parse_codex_jsonl,
    parse_codex_text,
)


def jsonl(*events):
    return "\n".join(json.dumps(event) for event in events)


def agent_message(text):
    return {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": text},
    }


class CodexJsonlParserTests(unittest.TestCase):
    def test_extracts_session_message_and_usage(self):
        result = parse_codex_jsonl(
            jsonl(
                {"type": "thread.started", "thread_id": "synthetic-thread"},
                {"type": "turn.started"},
                agent_message("Synthetic worker report."),
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 30,
                        "cached_input_tokens": 100,
                        "reasoning_output_tokens": 5,
                        "unsupported_counter": 900,
                    },
                },
            )
        )
        self.assertEqual(
            result,
            {
                "native_session_id": "synthetic-thread",
                "final_text": "Synthetic worker report.",
                "is_error": False,
                "stop_reason": "end_turn",
                "turns": None,
                "cost_usd": None,
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "cached_input_tokens": 100,
                    "reasoning_output_tokens": 5,
                },
                "usage_scope": "inclusive_aggregate",
                "model_usage": None,
                "observed_model": None,
                "permission_denials": None,
                "parse_error": None,
                "errors": [],
            },
        )

    def test_joins_completed_agent_messages_in_order(self):
        result = parse_codex_jsonl(
            jsonl(
                agent_message("First paragraph."),
                {
                    "type": "item.started",
                    "item": {"type": "agent_message", "text": "Unfinished"},
                },
                {
                    "type": "item.completed",
                    "item": {"type": "command_execution", "text": "Tool output"},
                },
                agent_message("Second paragraph.\nWith a second line."),
            )
        )
        self.assertEqual(
            result["final_text"],
            "First paragraph.\n\nSecond paragraph.\nWith a second line.",
        )

    def test_last_message_overrides_event_text_without_losing_metadata(self):
        result = parse_codex_jsonl(
            jsonl(
                {"type": "thread.started", "thread_id": "synthetic-thread"},
                agent_message("Earlier event text"),
                {"type": "turn.completed", "usage": {"output_tokens": 9}},
                {"type": "error", "message": "Synthetic failure"},
            ),
            last_message="  Final file text\n",
        )
        self.assertEqual(result["final_text"], "  Final file text\n")
        self.assertEqual(result["native_session_id"], "synthetic-thread")
        self.assertEqual(result["usage"], {"output_tokens": 9})
        self.assertTrue(result["is_error"])
        self.assertEqual(result["stop_reason"], "error")
        self.assertEqual(result["errors"], ["Synthetic failure"])

    def test_empty_or_nonstring_last_message_falls_back_to_events(self):
        for last_message in ("", None, 0, True, [], {"text": "Not a string"}):
            with self.subTest(last_message=last_message):
                result = parse_codex_jsonl(
                    jsonl(agent_message("Event text")), last_message=last_message
                )
                self.assertEqual(result["final_text"], "Event text")
                self.assertIsNone(result["parse_error"])

    def test_last_message_alone_is_sufficient(self):
        result = parse_codex_jsonl(
            "diagnostic text\n{malformed JSON", last_message="Final file text"
        )
        self.assertEqual(result["final_text"], "Final file text")
        self.assertIsNone(result["native_session_id"])
        self.assertIsNone(result["usage"])
        self.assertIsNone(result["parse_error"])
        self.assertFalse(result["is_error"])

    def test_skips_noise_malformed_lines_and_nonobject_json(self):
        stdout = "\n".join(
            (
                "",
                "diagnostic text",
                "{broken JSON",
                '["not", "an", "event"]',
                "null",
                "42",
                'prefix {"type":"error","message":"Not an event line"}',
                '  {"type":"thread.started","thread_id":"synthetic-thread"}  ',
                '{"type":"error","message":"Trailing garbage"} trailing',
                jsonl(agent_message("Usable output")),
            )
        )
        result = parse_codex_jsonl(stdout)
        self.assertEqual(result["native_session_id"], "synthetic-thread")
        self.assertEqual(result["final_text"], "Usable output")
        self.assertEqual(result["errors"], [])
        self.assertIsNone(result["parse_error"])

    def test_unknown_event_object_counts_as_parsed_input(self):
        for event in ({}, {"type": "future.event", "text": "Ignored"}):
            with self.subTest(event=event):
                result = parse_codex_jsonl(jsonl(event))
                self.assertIsNone(result["parse_error"])
                self.assertEqual(result["final_text"], "")
                self.assertFalse(result["is_error"])

    def test_ignores_invalid_session_and_item_shapes(self):
        for invalid in (None, 3, True, [], {"text": "Wrong shape"}):
            with self.subTest(invalid=invalid):
                result = parse_codex_jsonl(
                    jsonl(
                        {"type": "thread.started", "thread_id": invalid},
                        {"type": "item.completed", "item": invalid},
                    )
                )
                self.assertIsNone(result["native_session_id"])
                self.assertEqual(result["final_text"], "")
                self.assertIsNone(result["parse_error"])

    def test_latest_valid_session_and_usage_win(self):
        result = parse_codex_jsonl(
            jsonl(
                {"type": "thread.started", "thread_id": "synthetic-first"},
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": 10, "output_tokens": 2},
                },
                {"type": "thread.started", "thread_id": "synthetic-second"},
                {"type": "turn.completed", "usage": {"output_tokens": 7}},
                {"type": "thread.started", "thread_id": 5},
                {"type": "turn.completed", "usage": []},
            )
        )
        self.assertEqual(result["native_session_id"], "synthetic-second")
        self.assertEqual(result["usage"], {"output_tokens": 7})

    def test_usage_accepts_only_integers_for_supported_keys(self):
        keys = (
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
            "reasoning_output_tokens",
        )
        for key in keys:
            for value in (True, False, 1.0, "1", None, [], {}):
                with self.subTest(key=key, value=value):
                    result = parse_codex_jsonl(
                        jsonl({"type": "turn.completed", "usage": {key: value}})
                    )
                    self.assertIsNone(result["usage"])
                    self.assertIsNone(result["usage_scope"])
            for value in (0, 12):
                with self.subTest(key=key, value=value):
                    result = parse_codex_jsonl(
                        jsonl({"type": "turn.completed", "usage": {key: value}})
                    )
                    self.assertEqual(result["usage"], {key: value})
                    self.assertEqual(result["usage_scope"], "inclusive_aggregate")

    def test_missing_or_nonobject_usage_remains_unavailable(self):
        for event in (
            {"type": "turn.completed"},
            *(
                {"type": "turn.completed", "usage": usage}
                for usage in (None, [], "usage", 1, True)
            ),
        ):
            with self.subTest(event=event):
                self.assertIsNone(parse_codex_jsonl(jsonl(event))["usage"])

    def test_failure_events_choose_error_message_or_event_kind(self):
        events = (
            (
                {
                    "type": "turn.failed",
                    "error": "Primary failure",
                    "message": "Secondary failure",
                },
                "Primary failure",
            ),
            (
                {"type": "error", "error": "", "message": "Message failure"},
                "Message failure",
            ),
            ({"type": "turn.failed"}, "turn.failed"),
            ({"type": "error", "error": None, "message": ""}, "error"),
        )
        for event, expected in events:
            with self.subTest(event=event):
                result = parse_codex_jsonl(jsonl(event))
                self.assertTrue(result["is_error"])
                self.assertEqual(result["stop_reason"], "error")
                self.assertEqual(result["errors"], [expected])
                self.assertIsNone(result["parse_error"])

    def test_error_list_retains_only_first_eight_failures(self):
        result = parse_codex_jsonl(
            jsonl(
                *(
                    {"type": "error", "message": f"Synthetic failure {index}"}
                    for index in range(12)
                ),
                agent_message("Partial report"),
                {"type": "turn.completed", "usage": {"output_tokens": 3}},
            )
        )
        self.assertEqual(
            result["errors"], [f"Synthetic failure {index}" for index in range(8)]
        )
        self.assertTrue(result["is_error"])
        self.assertEqual(result["stop_reason"], "error")
        self.assertEqual(result["final_text"], "Partial report")

    def test_no_events_or_final_message_returns_only_parse_error(self):
        for stdout in ("", " \n\t", "diagnostic\n{broken", 'null\n[]\n42\n"text"'):
            for last_message in (None, "", 1):
                with self.subTest(stdout=stdout, last_message=last_message):
                    self.assertEqual(
                        parse_codex_jsonl(stdout, last_message=last_message),
                        {"parse_error": "no codex events or final message found"},
                    )

    def test_final_text_limit_applies_to_joined_messages(self):
        first = "é" * (MAX_FINAL_TEXT - 1)
        result = parse_codex_jsonl(jsonl(agent_message(first), agent_message("tail")))
        self.assertEqual(result["final_text"], first + "\n")
        self.assertEqual(len(result["final_text"]), MAX_FINAL_TEXT)
        self.assertIsNone(result["parse_error"])

    def test_final_text_limit_preserves_exact_boundary_and_truncates_overflow(self):
        for size in (MAX_FINAL_TEXT, MAX_FINAL_TEXT + 1):
            text = "é" * size
            for source in ("event", "last_message"):
                with self.subTest(size=size, source=source):
                    result = (
                        parse_codex_jsonl(jsonl(agent_message(text)))
                        if source == "event"
                        else parse_codex_jsonl("", last_message=text)
                    )
                    self.assertEqual(result["final_text"], text[:MAX_FINAL_TEXT])
                    self.assertEqual(len(result["final_text"]), MAX_FINAL_TEXT)
                    self.assertIsNone(result["parse_error"])


class CodexTextParserTests(unittest.TestCase):
    def test_strips_stdout_and_returns_text_result_fields(self):
        self.assertEqual(
            parse_codex_text("\n  Synthetic report.\nSecond line. \t"),
            {
                "native_session_id": None,
                "final_text": "Synthetic report.\nSecond line.",
                "is_error": False,
                "stop_reason": "end_turn",
                "turns": None,
                "cost_usd": None,
                "usage": None,
                "permission_denials": None,
                "parse_error": None,
            },
        )

    def test_last_message_takes_precedence_and_preserves_whitespace(self):
        result = parse_codex_text("Diagnostic stdout", last_message="  Final report.\n")
        self.assertEqual(result["final_text"], "  Final report.\n")
        self.assertIsNone(result["parse_error"])

    def test_last_message_succeeds_without_stdout(self):
        result = parse_codex_text("", last_message="Final report.")
        self.assertEqual(result["final_text"], "Final report.")
        self.assertFalse(result["is_error"])
        self.assertIsNone(result["parse_error"])

    def test_empty_or_nonstring_last_message_falls_back_to_stdout(self):
        for last_message in ("", None, 0, True, [], {"text": "Wrong shape"}):
            with self.subTest(last_message=last_message):
                result = parse_codex_text(
                    "  Stdout report.\n", last_message=last_message
                )
                self.assertEqual(result["final_text"], "Stdout report.")

    def test_empty_output_returns_only_parse_error(self):
        for stdout in ("", " ", "\t\r\n"):
            for last_message in (None, "", 1):
                with self.subTest(stdout=stdout, last_message=last_message):
                    self.assertEqual(
                        parse_codex_text(stdout, last_message=last_message),
                        {"parse_error": "empty codex output"},
                    )

    def test_text_mode_does_not_interpret_json_as_events(self):
        stdout = jsonl({"type": "error", "message": "Synthetic error event"})
        result = parse_codex_text(stdout)
        self.assertEqual(result["final_text"], stdout)
        self.assertFalse(result["is_error"])
        self.assertEqual(result["stop_reason"], "end_turn")

    def test_final_text_limit_applies_to_stdout_and_last_message(self):
        for size in (MAX_FINAL_TEXT, MAX_FINAL_TEXT + 1):
            text = "é" * size
            for source in ("stdout", "last_message"):
                with self.subTest(size=size, source=source):
                    result = (
                        parse_codex_text(" \n" + text + "\n ")
                        if source == "stdout"
                        else parse_codex_text("Diagnostic", last_message=text)
                    )
                    self.assertEqual(result["final_text"], text[:MAX_FINAL_TEXT])
                    self.assertEqual(len(result["final_text"]), MAX_FINAL_TEXT)
                    self.assertIsNone(result["parse_error"])


if __name__ == "__main__":
    unittest.main()
