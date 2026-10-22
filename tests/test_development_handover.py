"""Operator development-loop handover (ODIN-ADR-038); synthetic records only."""

import tempfile
import unittest
import uuid

from odin.contracts import identifier, strict_loads
from odin.coordination import Actor
from odin.executive_mcp import ExecutiveBridge
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext, error_result
from odin.service import Service
from odin.store import Conflict


class DevelopmentHandoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = prepare_project(self.temp.name)
        self.other = prepare_project(self.temp.name)
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        self.session = str(uuid.uuid4())
        self.successor = str(uuid.uuid4())
        self.operator = GatewayContext("terminal", Actor("operator", "test"))
        self.loop = None
        self.stage = None

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    @property
    def core(self):
        return self.gateway.development_loop

    def command(self, action, payload, operation=None):
        return {
            "schema_version": 1,
            "operation_id": operation or identifier(),
            "action": action,
            "payload": payload,
        }

    def send(self, action, payload, operation=None, *, executive=False, project=None):
        command = self.command(
            action, {"project": project or self.project} | payload, operation
        )
        if executive:
            return submit_executive(
                self.gateway, {"command": command}, project or self.project
            )["result"]
        return self.gateway.submit(command, context=self.operator)["result"]

    def start(self, session=None, project=None):
        return self.send(
            "loop_start",
            {"goal": "Synthetic handover work", "session_id": session or self.session},
            project=project,
        )

    def evaluate(self, loop_id, job, result=None):
        self.core.mark_evaluator_started(
            loop_id, job["id"], job["packet_digest"], identifier()
        )
        return self.core.accept_evaluation(
            loop_id,
            job["id"],
            job["packet_digest"],
            result
            or {
                "decision": "continue",
                "assessment": "Synthetic",
                "findings": [],
                "next_prompt": "Do bounded work.",
                "evidence_refs": [],
            },
            identifier(),
        )

    def pending_loop(self):
        """A live loop waiting in executive_pending with a pending stage."""
        started = self.start()
        self.loop = started["loop"]["id"]
        evaluated = self.evaluate(self.loop, started["job"])
        self.stage = evaluated["stage"]["id"]
        return {
            "loop_id": self.loop,
            "stage_id": self.stage,
            "session_id": self.session,
        }

    def intervention(self):
        """A loop held in needs_operator with an unacknowledged notice."""
        ids = self.pending_loop()
        self.send("loop_claim", ids, executive=True)
        ready = self.send(
            "loop_ready", ids | {"evidence_packet": {}}, executive=True
        )
        captured = self.send(
            "loop_capture",
            {
                "session_id": self.session,
                "hook_event_name": "Stop",
                "last_assistant_message": "Operator needed.\n"
                + ready["completion_marker"],
            },
            executive=True,
        )
        job = self.core.job(captured["job"]["id"])
        self.core.mark_evaluator_started(
            self.loop, job["id"], job["packet_digest"], identifier()
        )
        return self.core.accept_evaluation(
            self.loop,
            job["id"],
            job["packet_digest"],
            {
                "decision": "needs_operator",
                "assessment": "Operator decision required",
                "findings": [],
                "next_prompt": "",
                "evidence_refs": [],
            },
            identifier(),
        )

    def checkpoint(self, summary, **extra):
        return {
            "revision": 1,
            "branch": "codex/synthetic",
            "worktree": "/tmp/synthetic",
            "artifact_refs": [],
            "open_obligations": [],
            "pending_reviews": [],
            "operation_ids": [],
            "next_action": "continue",
            "summary": summary,
        } | extra

    def payload(self, **overrides):
        loop = self.core.get(self.loop)
        value = {
            "loop_id": self.loop,
            "from_session": self.session,
            "to_session": self.successor,
            "expected_revision": loop["revision"],
            "reason": "executive session rotated",
        }
        return value | overrides

    def test_handover_moves_ownership_and_reoffers_pending_stage(self):
        ids = self.pending_loop()
        first = self.send(
            "loop_inbox", {"session_id": self.session}, executive=True
        )["messages"][0]
        before = self.core.get(self.loop)
        result = self.send("loop_handover", self.payload())
        loop = result["loop"]
        self.assertEqual(loop["session_id"], self.successor)
        self.assertEqual(loop["previous_session_ids"], [self.session])
        self.assertEqual(loop["revision"], before["revision"] + 1)
        for key in ("status", "round", "max_rounds", "no_progress_count",
                    "current_job", "current_stage", "goal"):
            self.assertEqual(loop[key], before[key], key)
        stage = self.core.stage(self.stage)
        self.assertEqual(stage["session_id"], self.successor)
        self.assertEqual(result["stage"]["id"], self.stage)
        # The predecessor's offer is stale; the successor's inbox re-offers the
        # same stage under a new delivery identity.
        self.assertEqual(
            self.send("loop_inbox", {"session_id": self.session}, executive=True),
            {"messages": []},
        )
        offered = self.send(
            "loop_inbox", {"session_id": self.successor}, executive=True
        )["messages"][0]
        self.assertEqual(offered["stage_id"], self.stage)
        self.assertNotEqual(offered["message_id"], first["message_id"])

    def test_predecessor_refused_and_successor_claims_and_checkpoints(self):
        ids = self.pending_loop()
        self.send("loop_handover", self.payload())
        for action, extra in (
            ("loop_status", {"loop_id": self.loop, "session_id": self.session}),
            ("loop_claim", ids),
            ("loop_ready", ids | {"evidence_packet": {}}),
        ):
            with self.subTest(action=action), self.assertRaisesRegex(
                PermissionError, "loop_owned_by_other_session"
            ):
                self.send(action, extra, executive=True)
        # A late completion capture from the old session creates no work.
        capture = self.send(
            "loop_capture",
            {
                "session_id": self.session,
                "hook_event_name": "Stop",
                "last_assistant_message": "<!-- odin-development-complete:"
                + self.stage
                + ":"
                + "0" * 32
                + " -->",
            },
            executive=True,
        )
        self.assertFalse(capture["captured"])
        # The successor reads the loop, claims the re-offered stage and may
        # checkpoint with the loop's identity.
        view = self.send(
            "loop_status",
            {"loop_id": self.loop, "session_id": self.successor},
            executive=True,
        )
        self.assertEqual(view["loops"][0]["id"], self.loop)
        claimed = self.send(
            "loop_claim",
            ids | {"session_id": self.successor},
            executive=True,
        )
        self.assertEqual(claimed["stage"]["state"], "claimed")
        checkpoint = {
            "revision": 1,
            "branch": None,
            "worktree": None,
            "artifact_refs": [],
            "open_obligations": [],
            "pending_reviews": [],
            "operation_ids": [],
            "next_action": "continue",
            "summary": "successor context",
            "loop_id": self.loop,
            "stage_id": self.stage,
        }
        saved = self.send(
            "context_checkpoint",
            {"session_id": self.successor, "checkpoint": checkpoint},
            executive=True,
        )
        self.assertEqual(saved["checkpoint"]["loop_id"], self.loop)

    def test_each_refusal_has_a_fixed_code(self):
        self.pending_loop()
        loop = self.core.get(self.loop)
        cases = [
            ("stale_loop_revision", {"expected_revision": loop["revision"] + 1}),
            ("handover_source_mismatch", {"from_session": str(uuid.uuid4())}),
            ("handover_same_session", {"to_session": self.session}),
        ]
        for code, change in cases:
            with self.subTest(code=code), self.assertRaisesRegex(Conflict, code):
                self.send("loop_handover", self.payload(**change))
        # A format-valid but non-canonical target takes the invalid-argument path.
        with self.assertRaisesRegex(Conflict, "canonical native session UUID"):
            self.send(
                "loop_handover",
                self.payload(to_session=self.successor.upper()),
            )
        self.assertEqual(self.core.get(self.loop), loop)

    def test_terminal_loop_and_busy_target_are_refused(self):
        self.pending_loop()
        other = self.start(session=self.successor, project=self.other)
        self.assertEqual(other["loop"]["session_id"], self.successor)
        with self.assertRaisesRegex(Conflict, "target_session_has_active_loop"):
            self.send("loop_handover", self.payload())
        self.send(
            "loop_control",
            {"loop_id": other["loop"]["id"], "action": "stop"},
            project=self.other,
        )
        self.send("loop_control", {"loop_id": self.loop, "action": "stop"})
        with self.assertRaisesRegex(Conflict, "loop_terminal"):
            self.send("loop_handover", self.payload())

    def test_executive_stage_in_progress_is_refused(self):
        ids = self.pending_loop()
        self.send("loop_claim", ids, executive=True)
        for step in ("claimed", "ready", "unknown", "paused_claimed"):
            loop = self.core.get(self.loop)
            stage = self.core.stage(self.stage)
            if step == "ready":
                self.send(
                    "loop_ready",
                    ids | {"evidence_packet": {"synthetic": True}},
                    executive=True,
                )
            elif step == "unknown":
                self.send(
                    "loop_hold",
                    {
                        "loop_id": self.loop,
                        "stage_id": self.stage,
                        "reason": "synthetic loss",
                    },
                )
            elif step == "paused_claimed":
                self.send(
                    "loop_reconcile",
                    {
                        "loop_id": self.loop,
                        "stage_id": self.stage,
                        "target": "executive",
                        "observed": "not_started",
                    },
                )
                self.send("loop_claim", ids, executive=True)
                self.send(
                    "loop_control", {"loop_id": self.loop, "action": "pause"}
                )
            with self.subTest(step=step), self.assertRaisesRegex(
                Conflict, "executive_stage_in_progress"
            ):
                self.send("loop_handover", self.payload(
                    expected_revision=self.core.get(self.loop)["revision"]))
        # Paused from an untouched pending stage hands over normally.
        self.send("loop_control", {"loop_id": self.loop, "action": "stop"})
        self.pending_loop()
        self.send("loop_control", {"loop_id": self.loop, "action": "pause"})
        moved = self.send("loop_handover", self.payload())
        self.assertEqual(moved["loop"]["status"], "paused")
        self.assertEqual(moved["loop"]["session_id"], self.successor)

    def test_identical_replay_returns_first_receipt_conflicts_refused(self):
        self.pending_loop()
        operation = identifier()
        payload = self.payload()
        first = self.send("loop_handover", payload, operation)
        self.assertEqual(first, self.send("loop_handover", payload, operation))
        for change in (
            {"to_session": str(uuid.uuid4())},
            {"reason": "different reason"},
            {"expected_revision": first["loop"]["revision"]},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(
                Conflict, "operation_id_reused"
            ):
                self.send("loop_handover", payload | change, operation)

    def test_unacknowledged_notices_move_acknowledged_stay(self):
        self.intervention()
        notices = self.core.notices(self.loop)
        self.assertEqual(len(notices), 1)
        first_notice = notices[0]
        self.core.acknowledge(
            first_notice["id"],
            self.project,
            self.session,
            identifier(),
            actor="fable-executive",
        )
        # A second intervention leaves a pending notice still with the owner.
        held = self.core.get(self.loop)
        continued = self.core.continue_after_intervention(
            self.loop,
            "Synthetic operator answer",
            identifier(),
            expected_revision=held["revision"],
        )
        self.evaluate(self.loop, continued["job"], {
            "decision": "needs_operator",
            "assessment": "Second intervention",
            "findings": [],
            "next_prompt": "",
            "evidence_refs": [],
        })
        pending = self.core.pending_notices(self.project, self.session)
        self.assertEqual(len(pending), 1)
        self.core.mark_offered([pending[0]["id"]])
        self.assertIsNotNone(self.core.notice(pending[0]["id"])["first_offered_at"])
        result = self.send("loop_handover", self.payload(
            expected_revision=self.core.get(self.loop)["revision"]))
        self.assertEqual(result["reoffered_notices"], [pending[0]["id"]])
        moved = self.core.notice(pending[0]["id"])
        self.assertEqual(moved["session_id"], self.successor)
        self.assertIsNone(moved["first_offered_at"])
        self.assertEqual(moved["state"], "pending")
        kept = self.core.notice(first_notice["id"])
        self.assertEqual(kept["session_id"], self.session)
        self.assertEqual(kept["state"], "acknowledged")
        self.assertIsNotNone(kept["acknowledged_at"])
        self.assertEqual(
            self.core.pending_notices(self.project, self.session), []
        )
        self.assertEqual(
            [n["id"] for n in self.core.pending_notices(self.project, self.successor)],
            [pending[0]["id"]],
        )
        # The notice reaches the successor's channel and can be acknowledged.
        inbox = self.send(
            "loop_inbox",
            {"session_id": self.successor, "accept": ["assignment", "notice"]},
            executive=True,
        )
        self.assertEqual(
            [m["notice_id"] for m in inbox["messages"] if m["kind"] == "notice"],
            [pending[0]["id"]],
        )
        acked = self.send(
            "loop_ack",
            {"session_id": self.successor, "notice_id": pending[0]["id"]},
            executive=True,
        )
        self.assertEqual(acked["notice"]["state"], "acknowledged")

    def test_history_event_and_persistence_across_restart(self):
        self.pending_loop()
        before = self.core.get(self.loop)
        self.send("loop_handover", self.payload())
        events = [
            strict_loads(row[0])
            for row in self.service.store.db.execute("SELECT body FROM history")
        ]
        handed = [
            e for e in events if e["kind"] == "development_loop.handed_over"
        ]
        self.assertEqual(len(handed), 1)
        payload = handed[0]["payload"]
        self.assertEqual(payload["loop_id"], self.loop)
        self.assertEqual(payload["from_session"], self.session)
        self.assertEqual(payload["to_session"], self.successor)
        self.assertEqual(payload["revision"], before["revision"] + 1)
        self.assertEqual(payload["actor"], "test")
        self.assertEqual(payload["reason"], "executive session rotated")
        self.service.close()
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        loop = self.core.get(self.loop)
        self.assertEqual(loop["session_id"], self.successor)
        self.assertEqual(loop["previous_session_ids"], [self.session])
        stage = self.core.stage(self.stage)
        self.assertEqual(stage["session_id"], self.successor)
        claimed = self.send(
            "loop_claim",
            {
                "loop_id": self.loop,
                "stage_id": self.stage,
                "session_id": self.successor,
            },
            executive=True,
        )
        self.assertEqual(claimed["stage"]["state"], "claimed")

    def test_previous_owners_are_bounded_oldest_first(self):
        self.pending_loop()
        sessions = [self.session, self.successor] + [
            str(uuid.uuid4()) for _ in range(16)
        ]
        for index in range(17):
            loop = self.core.get(self.loop)
            self.send(
                "loop_handover",
                self.payload(
                    from_session=sessions[index],
                    to_session=sessions[index + 1],
                    expected_revision=loop["revision"],
                ),
            )
        self.assertEqual(self.core.get(self.loop)["previous_session_ids"],
                         sessions[1:17])
        self.assertEqual(len(sessions[1:17]), 16)

    def test_no_handover_tool_on_executive_bridge_or_voice(self):
        self.pending_loop()
        bridge = ExecutiveBridge(
            self.project,
            lambda command: submit_executive(
                self.gateway, {"command": command}, self.project
            ),
            development_loop=True,
            session_id=self.session,
        )
        names = {tool["name"] for tool in bridge.tools()}
        self.assertFalse(any("handover" in name for name in names))
        with self.assertRaises(PermissionError):
            self.send("loop_handover", self.payload(), executive=True)
        with self.assertRaises(PermissionError):
            self.gateway.submit(
                self.command("loop_handover", self.payload()),
                context=GatewayContext("voice", Actor("operator", "test")),
            )
        self.assertEqual(self.core.get(self.loop)["session_id"], self.session)

    def test_project_mismatch_is_refused_before_owner_change(self):
        self.pending_loop()
        command = self.command(
            "loop_handover", {"project": self.other} | self.payload()
        )
        with self.assertRaises(PermissionError):
            self.gateway.submit(command, context=self.operator)
        self.assertEqual(self.core.get(self.loop)["session_id"], self.session)

    def test_predecessor_checkpoint_returned_only_on_request(self):
        self.pending_loop()
        operation = identifier()
        saved = self.send(
            "context_checkpoint",
            {
                "session_id": self.session,
                # Deliberately unbound: the read never requires a loop field.
                "checkpoint": self.checkpoint("predecessor working notes"),
            },
            operation,
            executive=True,
        )
        self.send("loop_handover", self.payload())
        plain = self.send(
            "context_status", {"session_id": self.successor}, executive=True
        )
        self.assertNotIn("predecessor_checkpoint", plain)
        self.assertNotIn("predecessor_session_id", plain)
        view = self.send(
            "context_status",
            {"session_id": self.successor, "predecessor": True},
            executive=True,
        )
        # The caller's own checkpoint field is unchanged; the predecessor's
        # is an attributed claim with identity, id, time and a reconcile note.
        self.assertIsNone(view["checkpoint"])
        self.assertEqual(view["predecessor_session_id"], self.session)
        entry = view["predecessor_checkpoint"]
        self.assertEqual(entry["session_id"], self.session)
        self.assertEqual(entry["checkpoint_id"], operation)
        self.assertTrue(entry["recorded_at"])
        self.assertEqual(entry["checkpoint"], saved["checkpoint"])
        self.assertIn("reconcile", entry["claim"])

    def test_predecessor_checkpoint_requires_recorded_handover(self):
        self.pending_loop()
        for payload in (
            {"session_id": self.successor, "predecessor": True},
            {"predecessor": True},
        ):
            with self.subTest(payload=payload), self.assertRaisesRegex(
                Conflict, "no_recorded_predecessor"
            ):
                self.send("context_status", payload, executive=True)
        # The session that handed a loop away has no recorded predecessor.
        self.send("loop_handover", self.payload())
        with self.assertRaisesRegex(Conflict, "no_recorded_predecessor"):
            self.send(
                "context_status",
                {"session_id": self.session, "predecessor": True},
                executive=True,
            )

    def test_predecessor_checkpoint_through_bridge(self):
        self.pending_loop()
        self.send("loop_handover", self.payload())

        def socket(command):
            try:
                return submit_executive(
                    self.gateway, {"command": command}, self.project
                )
            except Exception as error:  # noqa: BLE001 - as the serve handler
                return error_result(error, "synthetic")

        bridge = ExecutiveBridge(
            self.project, socket, development_loop=True,
            session_id=self.successor,
        )
        definition = next(
            tool for tool in bridge.tools() if tool["name"] == "odin_context_status"
        )
        self.assertEqual(
            definition["inputSchema"]["properties"]["predecessor"],
            {"type": "boolean"},
        )
        # A handover exists but the predecessor never wrote a checkpoint:
        # the entry is null and the predecessor session is named.
        result = strict_loads(
            bridge.call("odin_context_status", {"predecessor": True})[
                "content"
            ][0]["text"]
        )["result"]
        self.assertIsNone(result["predecessor_checkpoint"])
        self.assertEqual(result["predecessor_session_id"], self.session)
        # The bound session identity is used even when another is supplied.
        result = strict_loads(
            bridge.call(
                "odin_context_status",
                {"predecessor": True, "session_id": self.session},
            )["content"][0]["text"]
        )["result"]
        self.assertEqual(result["predecessor_session_id"], self.session)
        # Without a recorded handover the refusal is a fixed code.
        rotated = ExecutiveBridge(
            self.project, socket, development_loop=True,
            session_id=self.session,
        )
        refused = rotated.call("odin_context_status", {"predecessor": True})
        self.assertTrue(refused["isError"])
        self.assertEqual(
            refused["content"][0]["text"],
            "Executive service refused the request: no_recorded_predecessor.",
        )

    def test_predecessor_is_the_most_recent_recorded_hander(self):
        self.pending_loop()
        third = str(uuid.uuid4())
        for session, summary in (
            (self.session, "first owner"),
            (third, "third owner"),
        ):
            self.send(
                "context_checkpoint",
                {
                    "session_id": session,
                    "checkpoint": self.checkpoint(summary),
                },
                executive=True,
            )
        # session -> successor -> third -> successor: history, not the loop
        # field, decides that the successor's predecessor is the third session.
        self.send("loop_handover", self.payload())
        self.send(
            "loop_handover",
            self.payload(from_session=self.successor, to_session=third),
        )
        self.send(
            "loop_handover",
            self.payload(from_session=third, to_session=self.successor),
        )
        view = self.send(
            "context_status",
            {"session_id": self.successor, "predecessor": True},
            executive=True,
        )
        self.assertEqual(view["predecessor_session_id"], third)
        self.assertEqual(
            view["predecessor_checkpoint"]["checkpoint"]["summary"],
            "third owner",
        )
        # The middle session's own recorded predecessor is still resolvable.
        view = self.send(
            "context_status",
            {"session_id": third, "predecessor": True},
            executive=True,
        )
        self.assertEqual(view["predecessor_session_id"], self.successor)


if __name__ == "__main__":
    unittest.main()
