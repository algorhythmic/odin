"""Local development evidence only; no test contacts Saga or a model provider."""

import copy
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError
from odin.budgets import Budget
from odin.capture import Archive, CaptureSpool
from odin.contracts import ROOT, Contracts, canonical, identifier, strict_loads
from odin.demo import run as demo
from odin.demo import staged_run
from odin.host import FixtureHost
from odin.policy import (
    account,
    combine_review,
    require_capabilities,
    route,
    session_class,
)
from odin.profiles import ToolBoundary
from odin.service import Service, fixture_record, make_effect
from odin.store import Conflict, Store, event
from odin.transitions import transition


def fixture(path):
    return strict_loads((ROOT / "fixtures" / path).read_text())


class ContractsTest(unittest.TestCase):
    def test_shared_contracts(self):
        contracts = Contracts()
        self.assertGreaterEqual(
            contracts.fixtures(ROOT / "fixtures/contracts.json"), 53
        )
        contracts.validate("examples", fixture("examples.json"))
        for schema, path in [
            ("capabilities", "fixture-capabilities.json"),
            ("evaluation-episode", "evaluation-episode.json"),
            ("three-document", "three-document/manifest.json"),
            ("transitions", "transitions.json"),
        ]:
            contracts.validate(schema, fixture(path))
        for name in ("planner", "reviewer", "subagent"):
            contracts.validate("profile", fixture("profiles/" + name + ".json"))

    def test_shared_transitions(self):
        for case in fixture("transitions.json")["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(
                    transition(case["kind"], case["input"]), case["expected"]
                )

    def test_strict_json(self):
        for raw in ('{"x":1,"x":2}', '{"x":{"a":1,"a":2}}', "{} {}", "1e999", "NaN"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_loads(raw)


class LocalTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.service = Service(self.path)
        self.addCleanup(lambda: self.service.close() if self.service else None)
        self.service.recover()
        self.store = self.service.store

    def setup_work(self):
        project = fixture_record("Project")
        session = fixture_record(
            "PlanningSession", project=project["id"], state="active"
        )
        commitment = fixture_record(
            "Commitment", project=project["id"], owner=session["id"]
        )
        assignment = fixture_record(
            "Assignment",
            commitment=commitment["id"],
            owner=session["id"],
            request_id=identifier(),
        )
        for r in (project, session, commitment, assignment):
            self.store.create(r)
        return project, session, commitment, assignment

    def restart(self):
        self.service.close()
        self.service = None
        self.service = Service(self.path)
        self.store = self.service.store
        self.service.recover()

    def test_single_writer_and_namespace_ownership(self):
        with self.assertRaises(Conflict):
            Store(self.path)
        with self.assertRaises(PermissionError):
            Store(self.path, "transcript_archive", "service")
        with self.assertRaises(PermissionError):
            self.service.mirror.store.create(fixture_record("Project"))

    def test_stale_revision_rolls_back_history(self):
        record = fixture_record("Project")
        self.store.create(record)
        count = self.store.db.execute("SELECT count(*) FROM history").fetchone()[0]
        with self.assertRaises(Conflict):
            self.store.update(record["id"], {"name": "stale"}, 0)
        self.assertEqual(self.store.get(record["id"]), record)
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM history").fetchone()[0], count
        )

    def test_commitment_closure_needs_criterion_evidence(self):
        _, _, c, _ = self.setup_work()
        with self.assertRaises(ValidationError):
            self.store.update(c["id"], {"state": "closed"}, 1)
        self.assertEqual(self.store.get(c["id"])["state"], "open")

    def test_duplicate_intake_and_conflicting_replay(self):
        item = event(
            "run.journal",
            {"summary": "synthetic"},
            producer="fixture",
            source_seq=1,
            key="journal:1",
        )
        self.assertTrue(self.store.intake(item))
        self.assertFalse(self.store.intake(item | {"id": identifier()}))
        with self.assertRaises(Conflict):
            self.store.intake(item | {"payload": {"summary": "changed"}})
        self.assertEqual(
            self.store.db.execute(
                'SELECT seq FROM cursors WHERE producer="fixture"'
            ).fetchone()[0],
            1,
        )

    def test_processing_record_and_effect_roll_back_together(self):
        item = event("work.report", {"status": "complete"})
        self.store.intake(item)
        record = fixture_record("Project")
        payload = {"id": identifier(), "task": "synthetic maintenance"}
        effect = make_effect("saga:task.request", payload)

        def fail(store, event):
            store._put(record, 0)
            store._enqueue(effect, payload)
            raise RuntimeError("injected before commit")

        with self.assertRaises(RuntimeError):
            self.store.process(fail)
        self.assertEqual(self.store.records(), [])
        self.assertEqual(self.store.effects(), [])
        self.assertEqual(
            self.store.db.execute("SELECT state FROM inbox").fetchone()[0], "received"
        )
        self.assertEqual(self.store.process(self.service.handle), 1)
        self.assertEqual(self.store.process(self.service.handle), 0)

    def test_process_death_before_commit(self):
        self.service.close()
        self.service = None
        script = """import os,sys
from odin.store import Store
from odin.service import fixture_record
with Store(sys.argv[1]) as s:
 with s.transaction():
  s._put(fixture_record('Project'),0)
  os._exit(23)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.path)], capture_output=True
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.service = Service(self.path)
        self.store = self.service.store
        self.assertEqual(self.store.records(), [])
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM history").fetchone()[0], 0
        )

    def test_lost_receipt_and_process_death_create_one_logical_run(self):
        *_, assignment = self.setup_work()
        run_id = staged_run(self.service, assignment)
        self.service.close()
        self.service = None
        script = """import os,sys
from odin.service import Service
with Service(sys.argv[1]) as s:
 s.recover()
 s.backend.lose_next_receipt=True
 try:s.store.dispatch(s.backend)
 except TimeoutError:os._exit(24)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.path)], capture_output=True
        )
        self.assertEqual(result.returncode, 24, result.stderr)
        self.service = Service(self.path)
        self.store = self.service.store
        self.service.recover()
        self.store.dispatch(self.service.backend)
        self.assertEqual(len(self.service.backend.resources("run")), 1)
        self.assertEqual(self.store.effects()[0]["receipt"], run_id)
        self.assertEqual(self.store.effects()[0]["attempts"], 1)

    def test_unknown_expired_is_never_retried(self):
        payload = {"id": identifier(), "task": "synthetic maintenance"}
        effect = make_effect("saga:task.request", payload)
        self.store.enqueue(effect, payload)
        with self.store.transaction():
            self.store._effect_state(effect, "unknown")
        self.service.backend.lookup = lambda operation: {"state": "unknown_expired"}
        self.service.recover()
        self.store.dispatch(self.service.backend)
        self.assertEqual(self.store.effects()[0]["state"], "unknown")
        self.assertEqual(self.service.backend.resources("task"), [])

    def test_non_idempotent_unknown_stays_unknown(self):
        payload = {"id": identifier(), "task": "synthetic maintenance"}
        effect = make_effect(
            "saga:task.request", payload, destination_capability="irreducibly_unknown"
        )
        self.store.enqueue(effect, payload)
        with self.store.transaction():
            self.store._effect_state(effect, "unknown")
        self.service.recover()
        self.assertEqual(self.store.effects()[0]["state"], "unknown")

    def test_stop_before_replay_prevents_run_and_disables_timers(self):
        *_, assignment = self.setup_work()
        staged_run(self.service, assignment)
        self.service.schedule("wake", "2026-10-16T00:00:00Z", event("timer.wake", {}))
        command = {
            "schema_version": 1,
            "operation_id": identifier(),
            "action": "stop",
            "reason": "synthetic stop",
        }
        item = event(
            "operator.command.stop",
            command,
            producer="fixture-cli",
            key=command["operation_id"],
        )
        self.store.intake(item)
        with self.assertRaises(Conflict):
            self.store.dispatch(self.service.backend)
        self.restart()
        self.store.dispatch(self.service.backend)
        self.assertTrue(self.store.stopped())
        self.assertEqual(self.service.backend.resources("run"), [])
        self.assertEqual(self.service.tick(), 0)
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM timers").fetchone()[0], 0
        )
        self.assertTrue(
            all(d["revoked"] for d in self.service.backend.resources("delegation"))
        )

    def test_untrusted_operator_producer_rejected(self):
        command = {
            "schema_version": 1,
            "operation_id": identifier(),
            "action": "stop",
            "reason": "synthetic",
        }
        self.store.intake(event("operator.command.stop", command, producer="worker"))
        with self.assertRaises(PermissionError):
            self.store.process(self.service.handle)
        self.assertFalse(self.store.stopped())

    def test_timer_replay_is_idempotent(self):
        item = event("timer.wake", {})
        self.service.schedule("wake", "2026-10-16T00:00:00Z", item)
        self.store.intake(item)  # Inject crash boundary before timer deletion.
        self.assertEqual(self.service.tick("2026-10-16T01:00:00Z"), 1)
        self.assertEqual(self.service.tick("2026-10-16T01:00:00Z"), 0)
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM routes").fetchone()[0], 1
        )

    def test_ownership_transfer_holds_pending_effects(self):
        project, session, commitment, assignment = self.setup_work()
        staged_run(self.service, assignment)
        replacement = fixture_record(
            "PlanningSession", project=project["id"], state="active"
        )
        self.store.create(replacement)
        self.store.transfer(commitment["id"], replacement["id"], 1)
        with self.assertRaises(Conflict):
            self.store.update(
                commitment["id"],
                {"objective": "stale"},
                2,
                owner=session["id"],
                generation=1,
            )
        self.assertEqual(self.store.effects()[0]["state"], "held")
        self.store.dispatch(self.service.backend)
        self.assertEqual(self.service.backend.resources("run"), [])

    def test_operation_id_content_conflicts(self):
        payload = {"id": identifier(), "task": "synthetic maintenance"}
        effect = make_effect("saga:task.request", payload)
        self.assertTrue(self.store.enqueue(effect, payload))
        self.assertFalse(self.store.enqueue(effect, payload))
        altered = payload | {"task": "different"}
        from odin.store import digest

        with self.assertRaises(Conflict):
            self.store.enqueue(effect | {"payload_digest": digest(altered)}, altered)

    def test_fake_refuses_stale_review_and_missing_criteria_evidence(self):
        *_, assignment = self.setup_work()
        run_id = staged_run(self.service, assignment)
        row = self.store.db.execute("SELECT payload FROM effects").fetchone()
        payload = strict_loads(row[0])
        with self.assertRaises(Conflict):
            self.service.backend.send(identifier(), "saga:run.submit", payload)
        with self.assertRaises(Conflict):
            self.service.backend.send(
                assignment["request_id"],
                "saga:run.submit",
                payload | {"digest": "changed"},
            )
        self.store.dispatch(self.service.backend)
        with self.assertRaises(Conflict):
            self.service.backend.inject_run_state(run_id, "verified", [])
        with self.assertRaises(Conflict):
            self.service.backend.inject_run_state(run_id, "verified", ["evidence"])

    def test_requests_are_single_consumption(self):
        *_, assignment = self.setup_work()
        run_id = staged_run(self.service, assignment)
        self.store.dispatch(self.service.backend)
        request = self.service.backend.inject_request(run_id, "Synthetic clarification")
        op = identifier()
        payload = {"request": request, "answer": "synthetic answer"}
        first = self.service.backend.send(op, "saga:request.answer", payload)
        self.assertEqual(
            self.service.backend.send(op, "saga:request.answer", payload), first
        )
        with self.assertRaises(Conflict):
            self.service.backend.send(identifier(), "saga:request.answer", payload)
        self.service.backend.consume_answer(request)
        self.assertEqual(self.service.backend.get(request)["state"], "consumed")

    def test_mirror_envelope_and_gap_rollback(self):
        self.service.backend.send(
            identifier(), "saga:task.request", {"id": "synthetic-task", "task": "check"}
        )
        self.assertEqual(self.service.mirror.refresh(self.service.backend), 1)
        self.assertEqual(self.service.mirror.refresh(self.service.backend), 0)
        for row in self.service.mirror.store.db.execute("SELECT body FROM history"):
            self.store.contracts.validate("event", strict_loads(row[0]))
        self.service.backend.events = lambda after: [
            {"seq": 3, "id": "gap", "body": {}, "kind": "task"}
        ]
        with self.assertRaises(Conflict):
            self.service.mirror.refresh(self.service.backend)
        with self.assertRaises(KeyError):
            self.service.mirror.get("gap")
        self.assertEqual(
            self.service.mirror.store.db.execute("SELECT seq FROM cursors").fetchone()[
                0
            ],
            1,
        )

    def test_projection_rebuild_after_restart_is_identical(self):
        self.store.create(fixture_record("Project"))
        path = self.path / "history.jsonl"
        before = self.store.project_history(path)
        self.restart()
        path.write_text("partial")
        self.assertEqual(self.store.project_history(path), before)

    def test_host_offline_does_not_fail_assignment_and_stop_blocks_resume(self):
        *_, assignment = self.setup_work()
        binding = fixture_record(
            "SessionBinding",
            host="fixture-host",
            subject={"kind": "assignment", "id": assignment["id"]},
        )
        self.store.create(binding)
        self.service.host_offline("fixture-host")
        self.assertEqual(self.store.get(binding["id"])["state"], "host_offline")
        self.assertEqual(self.store.get(assignment["id"])["state"], "drafted")
        self.store.stop("synthetic")
        self.assertEqual(
            self.service.reconcile_binding(binding["id"], binding), "invalidated"
        )

    def test_child_partial_stale_duplicate_returns_never_complete_work(self):
        _, _, commitment, assignment = self.setup_work()
        result = {
            "operation_id": identifier(),
            "session": assignment["owner"],
            "assignment": assignment["id"],
            "assignment_revision": assignment["rev"],
            "generation": 1,
            "state": "active",
            "result": {
                "status": "partial",
                "evidence": ["artifact:path"],
                "text": "unfinished",
            },
            "label": "fixture-only; no model or tool execution",
        }
        self.assertFalse(self.service.record_child_return(result, assignment["id"], 1))
        complete = result | {
            "operation_id": identifier(),
            "result": result["result"] | {"status": "complete"},
        }
        self.assertTrue(self.service.record_child_return(complete, assignment["id"], 1))
        self.assertFalse(
            self.service.record_child_return(complete, assignment["id"], 1)
        )
        stale = complete | {"operation_id": identifier(), "assignment_revision": 2}
        self.assertFalse(self.service.record_child_return(stale, assignment["id"], 1))
        self.assertEqual(self.store.get(commitment["id"])["state"], "open")
        self.assertEqual(self.store.get(assignment["id"])["state"], "drafted")

    def test_budget_unknown_usage_survives_restart_and_holds_allowance(self):
        budget = Budget(self.store)
        budget.create("fixture", 100, 2, 1)
        budget.reserve("fixture", "first", 60, 1, enforceable=True)
        budget.settle("first", None)
        self.restart()
        budget = Budget(self.store)
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "second", 50, 1, enforceable=True)
        budget.settle("first", 40)
        budget.reserve("fixture", "second", 60, 1, enforceable=True)
        with self.assertRaises(Conflict):
            budget.settle("first", 39)

    def test_budget_depth_concurrency_unbounded_adapter_and_stop(self):
        budget = Budget(self.store)
        budget.create("fixture", 100, 1, 1)
        with self.assertRaises(PermissionError):
            budget.reserve("fixture", "unbounded", 1, 0, enforceable=False)
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "deep", 1, 2, enforceable=True)
        budget.reserve("fixture", "first", 10, 1, enforceable=True)
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "second", 10, 1, enforceable=True)
        budget.settle("first", 5)
        self.store.stop("synthetic")
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "second", 10, 1, enforceable=True)

    def test_budget_bound_overrun_blocks_new_admission(self):
        budget = Budget(self.store)
        budget.create("fixture", 100, 2, 1)
        budget.reserve("fixture", "first", 10, 1, enforceable=True)
        budget.settle("first", 11)
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "second", 1, 1, enforceable=True)

    def test_reservation_is_not_released_on_uncertain_lookup(self):
        budget = Budget(self.store)
        budget.create("fixture", 100, 1, 0)
        budget.reserve("fixture", "first", 100, 0, enforceable=True)
        budget.settle("first", None)
        original = self.service.backend.lookup
        self.service.backend.lookup = lambda operation: {"state": "unknown_expired"}
        with self.assertRaises(Conflict):
            budget.reconcile_absent("first", self.service.backend)
        with self.assertRaises(Conflict):
            budget.reserve("fixture", "second", 1, 0, enforceable=True)
        self.service.backend.lookup = original
        budget.reconcile_absent("first", self.service.backend)
        budget.reserve("fixture", "second", 100, 0, enforceable=True)

    def test_observational_class_recording_does_not_change_selection(self):
        project, _, _, _ = self.setup_work()
        environment = fixture_record("Environment")
        self.store.create(environment)
        item = event("work.report", {})
        candidates = [
            {
                "name": "routine",
                "supports": ["read"],
                "cost_bound_microusd": 0,
                "capabilities": ["start"],
            },
            {
                "name": "alternative",
                "supports": ["read"],
                "cost_bound_microusd": 0,
                "capabilities": ["start"],
            },
        ]
        args = (
            project["id"],
            item,
            ["read"],
            candidates,
            fixture("fixture-capabilities.json"),
            0,
            environment,
            "fixture-config-v1",
        )
        first = self.service.choose_fixture_class(*args, record=False)
        self.assertEqual(self.store.records("SessionClassDecision"), [])
        self.assertEqual(self.service.choose_fixture_class(*args), first)
        decision = self.store.records("SessionClassDecision")[0]
        self.assertEqual(decision["chosen"], "routine")
        self.assertEqual(decision["rejected"][0]["class"], "alternative")

    def test_known_refusal_is_failed_not_unknown(self):
        *_, assignment = self.setup_work()
        staged_run(self.service, assignment)
        self.service.backend.send(identifier(), "saga:stop", {"scope": "all"})
        with self.assertRaises(Conflict):
            self.store.dispatch(self.service.backend)
        self.assertEqual(self.store.effects()[0]["state"], "failed")
        self.restart()
        self.store.dispatch(self.service.backend)
        self.assertEqual(self.service.backend.resources("run"), [])


class CaptureHostTest(unittest.TestCase):
    def test_cli_records_status_and_stop_over_private_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, "-m", "odin", "--state", directory]
            server = subprocess.Popen(
                command + ["serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(server.stdout, selectors.EVENT_READ)
                    self.assertTrue(
                        selector.select(timeout=10), "fixture CLI did not become ready"
                    )
                ready = server.stdout.readline()
                self.assertIn("Fixture service ready", ready)
                request = Path(directory) / "command.json"
                request.write_text(
                    canonical(
                        {
                            "schema_version": 1,
                            "operation_id": identifier(),
                            "action": "message",
                            "payload": {
                                "project": None,
                                "text": "synthetic voice text",
                            },
                        }
                    )
                )
                result = subprocess.run(
                    command
                    + ["command", "--request", str(request), "--surface", "voice"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                receipt = strict_loads(result.stdout)
                self.assertEqual(
                    receipt["result"]["delivery"], "pending_harness_integration"
                )
                # Input cannot manufacture an adapter/coordinator context.
                request.write_text(
                    canonical(
                        {
                            "schema_version": 1,
                            "operation_id": identifier(),
                            "action": "portfolio",
                            "payload": {"projects": [], "grant_ids": {}},
                        }
                    )
                )
                result = subprocess.run(
                    command + ["command", "--request", str(request)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(
                    strict_loads(result.stdout)["error"], "PermissionError"
                )
                for action in ("status", "stop", "status"):
                    result = subprocess.run(
                        command + [action], capture_output=True, text=True, timeout=10
                    )
                    self.assertEqual(
                        result.returncode, 0, result.stderr + result.stdout
                    )
                    response = strict_loads(result.stdout)
                    self.assertEqual(response["label"], "fake-backend evidence")
                    if action == "stop":
                        self.assertTrue(response["stopped"])
            finally:
                if server.poll() is None:
                    server.send_signal(signal.SIGINT)
                output, error = server.communicate(timeout=10)
                self.assertEqual(server.returncode, 0, error)

    def test_atomic_capture_replay_preserves_gaps_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            archive = Archive(path)
            spool = CaptureSpool(path / "spool.sqlite3")
            try:
                batch = {
                    "schema_version": 1,
                    "checkpoint": "checkpoint1",
                    "records": [
                        {
                            "key": "record1",
                            "revision": 1,
                            "content": "synthetic content",
                            "gap": False,
                        },
                        {
                            "key": "gap1",
                            "revision": 1,
                            "content": "source gap",
                            "gap": True,
                        },
                    ],
                }
                spool.append(batch)
                archive.append(batch)  # Ack lost: spool still holds the batch.
                spool.flush(archive)
                self.assertEqual(
                    archive.store.db.execute("SELECT count(*) FROM capture").fetchone()[
                        0
                    ],
                    2,
                )
                self.assertEqual(
                    archive.store.db.execute(
                        "SELECT count(*) FROM checkpoints"
                    ).fetchone()[0],
                    1,
                )
                self.assertEqual(
                    spool.db.execute("SELECT count(*) FROM batches").fetchone()[0], 0
                )
                with self.assertRaises(Conflict):
                    archive.append(batch | {"records": []})
                archive.append(batch | {"checkpoint": "checkpoint2", "records": []})
                self.assertEqual(
                    archive.store.db.execute(
                        "SELECT count(*) FROM checkpoints"
                    ).fetchone()[0],
                    2,
                )
                bad = batch | {
                    "checkpoint": "checkpoint3",
                    "records": [batch["records"][0] | {"content": "changed"}],
                }
                with self.assertRaises(Conflict):
                    archive.append(bad)
                self.assertEqual(
                    archive.store.db.execute(
                        "SELECT count(*) FROM checkpoints"
                    ).fetchone()[0],
                    2,
                )
            finally:
                spool.close()
                archive.close()

    def test_fixture_host_operation_replay_offline_and_stale_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            host = FixtureHost(Path(directory) / "host.sqlite3")
            try:
                command = {
                    "schema_version": 1,
                    "operation_id": identifier(),
                    "action": "start",
                    "session": identifier(),
                    "generation": 1,
                    "profile": "planner",
                    "assignment": identifier(),
                    "assignment_revision": 1,
                    "fixture_result": None,
                }
                first = host.command(command)
                self.assertEqual(host.command(command), first)
                host.online = False
                with self.assertRaises(ConnectionError):
                    host.command(command)
                host.online = True
                with self.assertRaises(Conflict):
                    host.command(
                        command
                        | {
                            "operation_id": identifier(),
                            "action": "resume",
                            "generation": 2,
                        }
                    )
                self.assertEqual(host.lookup(command["operation_id"]), first)
            finally:
                host.close()


class PolicyTest(unittest.TestCase):
    def test_required_events_cannot_be_suppressed_by_classifier(self):
        for kind, expected in [
            ("run.request", "operator_queue"),
            ("operator.command.stop", "direct"),
            ("review.verdict", "interrupt"),
            ("run.state.failed", "wake"),
            ("run.state.verified", "lifecycle"),
        ]:
            self.assertEqual(
                route(event(kind, {"classification": "routine"})), expected
            )
        self.assertEqual(route(event("unknown.kind", {})), "wake")
        self.assertEqual(
            route(
                event(
                    "work.report",
                    {
                        "type": "journal_triage",
                        "status": "no_attention",
                        "complete_coverage": False,
                    },
                )
            ),
            "wake",
        )

    def test_review_unavailable_disagreement_and_round_limit(self):
        a = {"position": "a", "verdict": {"result": "APPROVE"}}
        for verdict in (
            None,
            {"result": "REJECT"},
            {"result": "INSUFFICIENT_EVIDENCE"},
        ):
            self.assertEqual(
                combine_review([a, {"position": "b", "verdict": verdict}], 1)[
                    "combination"
                ],
                "escalated",
            )
        self.assertEqual(
            combine_review([a, a | {"position": "b"}], 2)["result"], "APPROVE"
        )
        with self.assertRaises(ValueError):
            combine_review([a, a | {"position": "b"}], 3)

    def test_capability_gaps_refuse_live_classes(self):
        matrix = fixture("fixture-capabilities.json")
        with self.assertRaises(PermissionError):
            require_capabilities(matrix, ["start"])
        with self.assertRaises(PermissionError):
            require_capabilities(matrix, ["native_children"], allow_fixture=True)
        require_capabilities(matrix, ["start"], allow_fixture=True)

    def test_all_rejected_classes_are_recorded_without_changing_choice(self):
        matrix = fixture("fixture-capabilities.json")
        candidates = [
            {
                "name": name,
                "supports": ["read"],
                "cost_bound_microusd": cost,
                "capabilities": ["start"],
            }
            for name, cost in [("expensive", 50), ("chosen", 5), ("later", 5)]
        ]
        self.assertEqual(
            session_class(["read"], candidates, matrix, 10),
            (
                "chosen",
                [
                    {"class": "expensive", "reason": "budget"},
                    {"class": "later", "reason": "lower_configured_priority"},
                ],
            ),
        )

    def test_profile_denies_before_execution_and_native_child_is_disabled(self):
        executed = []
        handlers = {
            name: lambda args: executed.append(args)
            for name in ("shell", "edit", "credentials.read", "records.read")
        }
        for name in ("planner", "reviewer", "subagent"):
            boundary = ToolBoundary(fixture("profiles/" + name + ".json"), handlers)
            for tool in ("shell", "edit", "credentials.read", "spawn_native_child"):
                with self.assertRaises(PermissionError):
                    boundary.call(tool, {"synthetic": "attempt"})
            with self.assertRaises(PermissionError):
                boundary.native_child()
        self.assertEqual(executed, [])
        with self.assertRaises(ValidationError):
            ToolBoundary(
                fixture("profiles/subagent.json") | {"allowed_tools": ["shell"]},
                handlers,
            )

    def test_accounting_includes_failed_attempts_and_unknown_cost(self):
        accepted = fixture("evaluation-episode.json")
        failed = copy.deepcopy(accepted)
        failed.update(
            episode_id="failed",
            accepted=False,
            failure="partial",
            cost_microusd=20,
            result_status="partial",
        )
        failed["cost_components"][0]["cost_microusd"] = 20
        result = account("single-parent", [accepted, failed])
        self.assertEqual(result["cost_per_accepted_microusd"], 20)
        self.assertIsNone(
            account("single-parent", [failed])["cost_per_accepted_microusd"]
        )
        failed["cost_microusd"] = None
        failed["cost_components"][0].update(
            cost_microusd=None, missing_reason="provider usage unavailable"
        )
        self.assertIsNone(
            account("single-parent", [accepted, failed])["cost_per_accepted_microusd"]
        )

    def test_inclusive_usage_is_not_double_counted(self):
        episode = fixture("evaluation-episode.json")
        child = copy.deepcopy(episode["cost_components"][0])
        child.update(operation="child", role="child")
        episode["cost_components"][0]["includes_operations"] = ["child"]
        episode["cost_components"].append(child)
        with self.assertRaises(ValueError):
            account("single-parent", [episode])

    def test_three_document_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            result = demo(Path(directory))
            self.assertEqual(result["label"], "fake-backend evidence")
            self.assertEqual(result["logical_runs"], 3)
            self.assertEqual(result["commitment_state"], "closed")
            for key in (
                "lost_receipt_reconciled",
                "termination_did_not_complete",
                "integration_gate_held",
                "replacement_preserved_commitment",
            ):
                self.assertTrue(result[key], key)


if __name__ == "__main__":
    unittest.main()
