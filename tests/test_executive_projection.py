import unittest

from odin.contracts import canonical, strict_loads
from odin.executive_mcp import ExecutiveBridge
from odin.executive_projection import MAX_COMPACT_BYTES, project_receipt


PROJECT = "01K7M000000000000000000001"
IDENTITY = "01K7M000000000000000000002"
NATIVE = "12345678-1234-4123-8123-123456789abc"


def receipt(result):
    return {"schema_version": 1, "operation_id": IDENTITY,
            "label": "fake-backend evidence", "result": result}


class ProjectionTests(unittest.TestCase):
    def test_delegation_keeps_active_and_failed_turns_with_explicit_history(self):
        historical = [{"id": f"old-{i}", "seq": i, "state": "returned",
                       "result": {"final_text_preview": "秘密" * 1000}}
                      for i in range(30)]
        active = {"id": "active", "seq": 31, "state": "running",
                  "failure": None, "result": None}
        failed = {"id": "failed", "seq": 32, "state": "failed",
                  "failure": "界" * 2000,
                  "result": {"exit_code": 0, "timed_out": True,
                             "interrupted": False, "is_error": False,
                             "stop_reason": "waitingreview",
                             "error_summary": "timeout after review gate"}}
        assignment = {"id": IDENTITY, "rev": 3, "state": "active",
                      "commitment": IDENTITY, "commitment_state": "open",
                      "objective": "work", "criteria": [], "limits": {},
                      "turns": historical + [active, failed]}
        session = {"session": {"id": IDENTITY, "rev": 7, "state": "active",
                               "native_session_id": NATIVE},
                   "options": {"model": "opus", "subagent_model": "haiku"},
                   "assignments": [assignment,
                                   {**assignment, "id": "terminal", "state": "completed"}],
                   "running_turns": ["active"]}
        source = receipt({"enabled": True, "project": PROJECT,
                          "sessions": [session]})
        projected = project_receipt("odin_delegation_status", source)
        self.assertLessEqual(len(canonical(projected).encode()), MAX_COMPACT_BYTES)
        self.assertEqual(projected["operation_id"], IDENTITY)
        view = projected["result"]
        self.assertEqual(view["sessions"][0]["session"]["rev"], 7)
        self.assertEqual(view["sessions"][0]["options"]["subagent_model"], "haiku")
        self.assertEqual(view["sessions"][0]["omitted_terminal_assignment_count"], 1)
        turns = view["sessions"][0]["assignments"][0]["turns"]
        self.assertEqual([turn["id"] for turn in turns], ["old-28", "old-29", "active", "failed"])
        self.assertTrue(turns[-1]["result"]["timed_out"])
        self.assertEqual(turns[-1]["result"]["stop_reason"], "waitingreview")
        self.assertEqual(turns[-1]["result"]["error_summary"], "timeout after review gate")
        self.assertEqual(view["sessions"][0]["assignments"][0]["omitted_turn_count"], 28)
        self.assertIn("view=detail", view["projection"]["detail"])
        self.assertIs(project_receipt("odin_delegation_status", source, view="detail"), source)
        scoped = project_receipt("odin_delegation_status", source,
                                 arguments={"assignment_id": "terminal"})
        self.assertEqual(len(scoped["result"]["sessions"][0]["assignments"]), 2)

    def test_delegation_compact_view_keeps_an_unrequested_budget_explicit(self):
        enforcement = {"budget": "not_requested", "iterations": "harness_option"}
        assignment = {"id": IDENTITY, "rev": 1, "state": "active",
                      "commitment": IDENTITY, "commitment_state": "open",
                      "objective": "work", "criteria": [],
                      "limits": {"iterations": 3, "budget_usd": None},
                      "limit_enforcement": enforcement, "turns": []}
        session = {"session": {"id": IDENTITY, "rev": 1, "state": "idle",
                               "native_session_id": NATIVE},
                   "options": {"model": "opus"}, "assignments": [assignment],
                   "running_turns": []}
        projected = project_receipt("odin_delegation_status", receipt(
            {"enabled": True, "project": PROJECT, "sessions": [session]}))
        view = projected["result"]["sessions"][0]["assignments"][0]
        self.assertEqual(view["limits"], {"iterations": 3, "budget_usd": None})
        self.assertEqual(view["limit_enforcement"], enforcement)

    def test_loop_status_keeps_active_attention_and_exposes_omissions(self):
        loop = {"id": IDENTITY, "revision": 12, "status": "executive_claimed",
                "round": 3, "max_rounds": 8, "current_stage": IDENTITY,
                "session_id": NATIVE, "goal": "界" * 20000,
                "work": {"attention": {"state": "stalled"}, "waiting": "running"},
                "attention": {"state": "attention", "notice_id": IDENTITY},
                "no_progress_count": 2, "no_progress_limit": 3,
                "notices": {"unacknowledged": 2, "latest": [{"kind": "stall"}]},
                "admission": {"decision": "allow"},
                "executive_stage": {"id": IDENTITY, "state": "claimed"},
                "source_packet": "other" * 10000}
        source = receipt({"loops": [loop], "more_available": False,
                          "quiescence": {"restart_quiescent": False}})
        output = project_receipt("odin_loop_status", source)
        self.assertLessEqual(len(canonical(output).encode()), MAX_COMPACT_BYTES)
        projected = output["result"]["loops"][0]
        self.assertEqual(projected["revision"], 12)
        self.assertEqual(projected["round"], 3)
        self.assertEqual(projected["work"]["attention"]["state"], "stalled")
        self.assertEqual(projected["attention"]["notice_id"], IDENTITY)
        self.assertEqual(projected["no_progress_count"], 2)
        self.assertGreater(projected["goal"]["omitted_utf8_bytes"], 0)
        self.assertEqual(len(projected["goal"]["preview"].encode()) +
                         projected["goal"]["omitted_utf8_bytes"],
                         len(loop["goal"].encode()))
        self.assertGreater(projected["omitted_loop_fields"], 0)

    def test_ready_receipt_retains_mutation_identity_and_validation_on_overflow(self):
        result = {"loop": {"id": IDENTITY, "revision": 9, "status": "executive_ready",
                           "current_stage": IDENTITY, "session_id": NATIVE,
                           "notices": {"latest": ["界" * 10000]}},
                  "stage": {"id": IDENTITY, "state": "ready"},
                  "completion_marker": "marker",
                  "receipt_validation": {"status": "failed", "commands_succeeded": False,
                                         "receipts": [{"path": "x"}] * 1000,
                                         "problems": ["bad"] * 1000}}
        output = project_receipt("odin_loop_ready", receipt(result))
        self.assertLessEqual(len(canonical(output).encode()), MAX_COMPACT_BYTES)
        self.assertEqual(output["operation_id"], IDENTITY)
        self.assertEqual(output["result"]["completion_marker"], "marker")
        self.assertEqual(output["result"]["loop"]["revision"], 9)
        self.assertEqual(output["result"]["receipt_validation"]["status"], "failed")
        self.assertEqual(output["result"]["receipt_validation"]["problem_count"], 1000)
        self.assertTrue(output["result"]["projection"]["incomplete_for_action"])

    def test_overflow_never_pretends_all_unresolved_work_was_listed(self):
        assignments = [
            {"id": f"assignment-{i}", "rev": 1, "state": "active",
             "commitment": f"commitment-{i}", "commitment_state": "open",
             "objective": "界" * 100, "criteria": [], "limits": {},
             "turns": [{"id": f"turn-{i}", "seq": 1, "state": "lost",
                        "failure": "unknown outcome"}]}
            for i in range(120)
        ]
        source = receipt({"enabled": True, "sessions": [
            {"session": {"id": IDENTITY, "rev": 4, "state": "active"},
             "assignments": assignments}]})
        output = project_receipt("odin_delegation_status", source)
        self.assertLessEqual(len(canonical(output).encode()), MAX_COMPACT_BYTES)
        projection = output["result"]["projection"]
        self.assertTrue(projection["incomplete_for_action"])
        self.assertEqual(projection["counts"]["unresolved_turns"], 120)
        self.assertEqual(projection["scopes"][0]["rev"], 4)

    def test_loop_overflow_scope_keeps_stage_marker_and_attention(self):
        loop = {"id": IDENTITY, "revision": 14, "status": "executive_ready",
                "round": 6, "max_rounds": 8, "current_stage": IDENTITY,
                "executive_stage": {"id": IDENTITY, "state": "ready",
                                    "completion_marker": "observed-marker"},
                "attention": {"state": "attention", "notice_id": IDENTITY},
                "notices": {"latest": ["界" * 10000]}}
        output = project_receipt("odin_loop_status", receipt({"loops": [loop]}))
        self.assertLessEqual(len(canonical(output).encode()), MAX_COMPACT_BYTES)
        scope = output["result"]["projection"]["scopes"][0]
        self.assertEqual(scope["revision"], 14)
        self.assertEqual(scope["executive_stage"]["completion_marker"], "observed-marker")
        self.assertEqual(scope["attention"]["notice_id"], IDENTITY)

    def test_bridge_strips_view_and_detail_returns_unprojected_receipt(self):
        commands = []
        def gateway(command):
            commands.append(command)
            return {**receipt({"enabled": True, "sessions": []}),
                    "operation_id": command["operation_id"]}
        bridge = ExecutiveBridge(PROJECT, gateway)
        compact = strict_loads(bridge.call("odin_delegation_status", {})["content"][0]["text"])
        detail = strict_loads(bridge.call("odin_delegation_status", {"view": "detail"})["content"][0]["text"])
        self.assertEqual(compact["result"]["projection"]["view"], "compact")
        self.assertNotIn("projection", detail["result"])
        self.assertEqual(commands[-1]["payload"], {"project": PROJECT})

    def test_same_operation_detail_replay_over_transport_budget_keeps_receipt(self):
        commands = []
        def gateway(command):
            commands.append(command)
            return {**receipt({
                "loop": {"id": IDENTITY, "revision": 5, "status": "executive_ready",
                         "round": 2, "max_rounds": 8, "current_stage": IDENTITY},
                "stage": {"id": IDENTITY, "state": "ready"},
                "completion_marker": "observed-marker",
                "receipt_validation": {"status": "uncertain", "commands_succeeded": False,
                                       "receipts": [], "problems": ["界" * 200000]},
            }), "operation_id": command["operation_id"]}
        bridge = ExecutiveBridge(PROJECT, gateway, development_loop=True,
                                 session_id=NATIVE)
        arguments = {"operation_id": IDENTITY, "loop_id": IDENTITY,
                     "stage_id": IDENTITY, "evidence_packet": {}}
        compact = bridge.call("odin_loop_ready", arguments)
        detailed = bridge.call("odin_loop_ready", arguments | {"view": "detail"})
        self.assertFalse(compact["isError"])
        self.assertFalse(detailed["isError"])
        self.assertEqual(commands[0], commands[1])
        output = strict_loads(detailed["content"][0]["text"])
        self.assertEqual(output["operation_id"], IDENTITY)
        self.assertEqual(output["result"]["completion_marker"], "observed-marker")
        self.assertEqual(output["result"]["receipt_validation"]["status"], "uncertain")
        self.assertTrue(output["result"]["projection"]["detail_transport_limited"])
        self.assertTrue(output["result"]["projection"]["incomplete_for_action"])


if __name__ == "__main__":
    unittest.main()
