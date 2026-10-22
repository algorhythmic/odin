"""Real detached evaluator scheduling using synthetic native executables only."""

import fcntl
import os
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

from odin.contracts import identifier
from odin.development_evaluator import (
    EvaluatorRunner,
    _read,
    _write,
    configure,
    load_config,
)
from odin.development_loop import DevelopmentLoop
from odin.store import Store
from test_memory import P, Q, project

SESSION = "11111111-1111-4111-8111-111111111111"
NATIVE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, pathlib, re, sys, time
    args = sys.argv[1:]
    def option(flag):
        return args[args.index(flag)+1] if flag in args else None
    model = option('-m') or option('--model')
    prompt = option('-p') or args[-1]
    packet_path = re.search(r'(/[^ ]+/packet.json)', prompt).group(1)
    packet = json.loads(pathlib.Path(packet_path).read_text())
    count = pathlib.Path(os.getcwd()) / 'native-count.txt'
    with count.open('a') as out: out.write(packet['loop_id']+'\\n')
    if model == 'sleep': time.sleep(60)
    if model == 'failure': sys.exit(3)
    if model == 'descendant':
        # Exits successfully, leaving a member in its own process group whose
        # arguments name no spool path.
        import subprocess
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd='/')
        (pathlib.Path(os.getcwd()) / 'descendant.pid').write_text(str(child.pid))
    value = dict(decision='continue', assessment='Synthetic evaluator assessment',
        findings=['Fixture evidence inspected'], next_prompt='Execute a bounded synthetic test',
        evidence_refs=[dict(ref='fixture:check', revision=str(packet['round']), digest='a'*64)])
    text = '```json\\n{}\\n```' if model == 'malformed' else json.dumps(value)
    if '-p' in args:
        print(json.dumps(dict(result=text, is_error=False)))
    else:
        pathlib.Path(option('-o')).write_text(text)
        print(json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=text))))
        print(json.dumps(dict(type='turn.completed',usage=dict(input_tokens=2,output_tokens=3))))
""")


class DevelopmentEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.profile = self.root / "profile"
        self.profile.mkdir(mode=0o700)
        self.binary = self.root / "native-fixture"
        self.binary.write_text(NATIVE)
        self.binary.chmod(0o700)
        self.store = Store(self.state)
        self.store.create(project(P, "Synthetic development"))
        self.loop = DevelopmentLoop(self.store)
        self.config = {
            "schema_version": 1,
            "enabled": True,
            "harness": "codex",
            "binary": str(self.binary),
            "workspace": str(self.workspace),
            "config_dir": str(self.profile),
            "model": "fixture",
            "timeout_seconds": 30,
        }
        self.runners = []

    def tearDown(self):
        for runner in self.runners:
            for child in runner._children:
                if child.poll() is None:
                    child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        self.store.close()
        self.temp.cleanup()

    def runner(self, config=None):
        result = EvaluatorRunner(
            self.loop, self.state, self.config if config is None else config
        )
        self.runners.append(result)
        return result

    def start(self):
        return self.loop.start(
            P, "Synthetic development objective", SESSION, identifier()
        )["job"]

    def wait(self, runner, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            runner.tick()
            result = predicate()
            if result:
                return result
            time.sleep(0.03)
        self.fail("synthetic evaluator did not reach the expected state")

    def count(self):
        path = self.workspace / "native-count.txt"
        return len(path.read_text().splitlines()) if path.exists() else 0

    def test_configuration_is_private_disabled_and_rejects_unsafe_locations(self):
        self.assertIsNone(load_config(self.state))
        path = configure(self.state, self.config)
        self.assertEqual(load_config(self.state), self.config)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        configure(self.state, self.config | {"enabled": False})
        self.assertIsNone(load_config(self.state))
        with self.assertRaises(ValueError):
            configure(self.state, self.config | {"workspace": str(self.root)})
        self.profile.chmod(0o755)
        with self.assertRaises(PermissionError):
            configure(self.state, self.config)

    def test_inherited_nondefault_developer_profile_is_rejected(self):
        for harness, env_key in (
            ("codex", "CODEX_HOME"),
            ("claude-code", "CLAUDE_CONFIG_DIR"),
        ):
            with (
                mock.patch.dict(os.environ, {env_key: str(self.profile)}),
                self.assertRaises(ValueError),
            ):
                configure(self.state, self.config | {"harness": harness})

    def test_native_codex_process_strict_result_and_no_duplicate_after_restart(self):
        configure(self.state, self.config)
        job, runner = self.start(), self.runner()
        first = runner.tick()
        self.assertEqual(first["started"], [job["id"]])
        self.wait(runner, lambda: self.loop.job(job["id"])["state"] == "completed")
        stage = self.loop.pending_stages(P, SESSION)[0]
        self.assertEqual(stage["prompt"], "Execute a bounded synthetic test")
        self.assertEqual(self.count(), 1)
        directory = runner.spool / job["id"]
        spec = _read(
            directory / "spec.json", "development-evaluator-config", definition="spec"
        )
        self.assertIn("read-only", spec["argv"])
        self.assertEqual(spec["lineage"]["credential_file"], None)
        self.assertEqual(spec["env"], {"CODEX_HOME": str(self.profile)})
        self.store.close()
        self.store = Store(self.state)
        self.loop = DevelopmentLoop(self.store)
        restarted = self.runner()
        for _ in range(3):
            restarted.tick()
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.loop.pending_stages(P, SESSION)[0], stage)

    def test_native_claude_uses_read_tools_and_separate_profile(self):
        job, runner = (
            self.start(),
            self.runner(self.config | {"harness": "claude-code"}),
        )
        self.wait(runner, lambda: self.loop.job(job["id"])["state"] == "completed")
        spec = _read(
            runner.spool / job["id"] / "spec.json",
            "development-evaluator-config",
            definition="spec",
        )
        self.assertEqual(
            spec["argv"][spec["argv"].index("--tools") + 1], "Read,Glob,Grep"
        )
        self.assertNotIn("--dangerously-skip-permissions", spec["argv"])
        self.assertEqual(spec["env"], {"CLAUDE_CONFIG_DIR": str(self.profile)})
        self.assertEqual(self.count(), 1)

    def test_pause_keeps_finished_result_until_resume(self):
        job, runner = self.start(), self.runner()
        runner.tick()
        self.loop.control(job["loop_id"], "pause", identifier())
        result_path = runner.spool / job["id"] / "result.json"
        self.wait(runner, result_path.exists)
        self.assertEqual(self.loop.job(job["id"])["state"], "running")
        self.assertEqual(self.loop.pending_stages(P, SESSION), [])
        self.loop.control(job["loop_id"], "resume", identifier())
        runner.tick()
        self.assertEqual(self.loop.job(job["id"])["state"], "completed")
        self.assertEqual(self.count(), 1)

    def test_missing_spawn_observation_holds_and_explicit_not_started_retries(self):
        job, runner = self.start(), self.runner()
        with mock.patch(
            "odin.development_evaluator.subprocess.Popen",
            side_effect=OSError("synthetic spawn uncertainty"),
        ):
            runner.tick()
        self.assertEqual(self.loop.job(job["id"])["state"], "unknown")
        self.runner().tick()
        self.assertEqual(self.count(), 0)
        self.loop.reconcile_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            observed="not_started",
        )
        self.wait(runner, lambda: self.loop.job(job["id"])["state"] == "completed")
        self.assertEqual(self.count(), 1)
        dispatch = _read(
            runner.spool / job["id"] / "dispatch.json",
            "development-evaluator-config",
            definition="dispatch",
        )
        self.assertEqual(dispatch["attempt"], 2)

    def test_late_result_requires_reconciliation_before_acceptance(self):
        job, runner = self.start(), self.runner()
        runner.tick()
        self.loop.fail_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            outcome="unknown",
            reason="synthetic observer interruption",
        )
        result_path = runner.spool / job["id"] / "result.json"
        self.wait(runner, result_path.exists)
        self.assertEqual(self.loop.job(job["id"])["state"], "unknown")
        self.loop.reconcile_evaluator(
            job["loop_id"],
            job["id"],
            job["packet_digest"],
            identifier(),
            observed="running",
        )
        runner.tick()
        self.assertEqual(self.loop.job(job["id"])["state"], "completed")
        self.assertEqual(self.count(), 1)

    def test_malformed_json_and_packet_tampering_hold_without_redispatch(self):
        job, runner = self.start(), self.runner(self.config | {"model": "malformed"})
        self.wait(runner, lambda: self.loop.job(job["id"])["state"] == "unknown")
        runner.tick()
        self.assertEqual(self.count(), 1)
        self.loop.control(job["loop_id"], "stop", identifier())
        job = self.start()
        runner = self.runner()
        runner.tick()
        path = runner.spool / job["id"] / "packet.json"
        packet = _read(path, "development-loop-packet")
        _write(path, packet | {"goal": "changed packet"}, "development-loop-packet")
        runner.tick()
        self.assertEqual(self.loop.job(job["id"])["state"], "unknown")
        self.assertEqual(self.loop.pending_stages(P, SESSION), [])

    def test_failed_native_process_escalates(self):
        job, runner = self.start(), self.runner(self.config | {"model": "failure"})
        self.wait(runner, lambda job=job: self.loop.job(job["id"])["state"] == "lost")
        self.assertEqual(self.loop.get(job["loop_id"])["status"], "needs_operator")
        self.assertEqual(self.count(), 1)

    def test_busy_and_unavailable_credential_lineage_fail_closed(self):
        for unavailable in (False, True):
            job, runner = self.start(), self.runner()
            lock_path = self.profile / ".odin-lineage.lock"
            lock = None
            if unavailable:
                lock_path.unlink(missing_ok=True)
                lock_path.symlink_to(self.root / "nonexistent-lineage")
            else:
                lock = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                self.wait(
                    runner, lambda job=job: self.loop.job(job["id"])["state"] == "lost"
                )
                self.assertEqual(self.count(), 0)
                result = _read(
                    runner.spool / job["id"] / "result.json", "delegation-result"
                )
                self.assertEqual(
                    result["lineage"]["lease"], "unavailable" if unavailable else "busy"
                )
                self.assertTrue(result["lineage"]["refused"])
            finally:
                if lock is not None:
                    os.close(lock)
                lock_path.unlink(missing_ok=True)
                self.loop.control(job["loop_id"], "stop", identifier())

    def test_single_lineage_serializes_queued_evaluators(self):
        self.store.create(project(Q, "Second synthetic project"))
        first = self.start()
        second = self.loop.start(
            Q, "Second goal", "22222222-2222-4222-8222-222222222222", identifier()
        )["job"]
        runner = self.runner()
        self.assertEqual(runner.tick()["started"], [first["id"]])
        self.assertEqual(self.loop.job(second["id"])["state"], "pending")
        self.wait(runner, lambda: self.loop.job(second["id"])["state"] == "completed")
        self.assertEqual(self.count(), 2)
        self.assertEqual(self.loop.job(first["id"])["state"], "completed")

    def test_dead_runner_live_native_child_holds_lineage_and_blocks_redispatch(self):
        self.store.create(project(Q, "Second synthetic project"))
        first, runner = self.start(), self.runner(self.config | {"model": "sleep"})
        runner.tick()
        directory = runner.spool / first["id"]
        self.wait(
            runner, lambda: (directory / "started.json").exists() and self.count() == 1
        )
        started = _read(
            directory / "started.json",
            "development-evaluator-config",
            definition="started",
        )
        harness_pid = started["harness_pid"]
        try:
            os.kill(started["runner_pid"], signal.SIGKILL)
            for child in runner._children:
                child.wait(timeout=3)
            second = self.loop.start(
                Q, "Queued goal", "22222222-2222-4222-8222-222222222222", identifier()
            )["job"]
            runner.tick()
            self.assertEqual(self.loop.job(first["id"])["state"], "unknown")
            self.assertEqual(self.loop.job(second["id"])["state"], "pending")
            self.assertEqual(runner._harness(directory), (harness_pid, "running"))
            lease = os.open(self.profile / ".odin-lineage.lock", os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(lease)
            restarted = self.runner()
            restarted.tick()
            self.assertEqual(self.count(), 1)
            self.assertEqual(self.loop.job(second["id"])["state"], "pending")
            self.loop.control(first["loop_id"], "stop", identifier())
            self.assertIn(first["id"], restarted.tick()["stopped"])
            self.wait(restarted, lambda: restarted._harness(directory)[1] == "absent")
            self.wait(
                restarted, lambda: self.loop.job(second["id"])["state"] == "completed"
            )
            self.assertEqual(self.count(), 2)
        finally:
            try:
                os.killpg(harness_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_stop_and_global_stop_prevent_launch_and_signal_owned_runner(self):
        job, runner = self.start(), self.runner(self.config | {"model": "sleep"})
        runner.tick()
        self.wait(runner, lambda: self.count() == 1)
        self.loop.control(job["loop_id"], "stop", identifier())
        summary = runner.tick()
        self.assertIn(job["id"], summary["stopped"])
        self.wait(runner, lambda: (runner.spool / job["id"] / "result.json").exists())
        new_job = self.start()
        self.store.stop("synthetic global stop")
        runner.tick()
        self.assertEqual(self.loop.get(new_job["loop_id"])["status"], "stopped")
        self.assertEqual(self.count(), 1)

    def test_pending_setup_failure_is_visible_and_does_not_starve_other_jobs(self):
        self.store.create(project(Q, "Second synthetic project"))
        first = self.start()
        second = self.loop.start(
            Q, "Second goal", "22222222-2222-4222-8222-222222222222", identifier()
        )["job"]
        runner = self.runner()
        (runner.spool / first["id"]).write_text("synthetic invalid directory")
        self.wait(runner, lambda: self.loop.job(second["id"])["state"] == "completed")
        blocked = self.loop.job(first["id"])
        self.assertEqual(blocked["state"], "blocked")
        self.assertIn("before model start", blocked["failure_reason"])
        self.assertEqual(self.loop.get(first["loop_id"])["status"], "needs_operator")
        self.assertEqual(self.count(), 1)

    def test_packet_write_failure_records_preparation_refusal_without_model_start(self):
        job, runner = self.start(), self.runner()
        with mock.patch(
            "odin.development_evaluator._write",
            side_effect=PermissionError("synthetic write refusal"),
        ):
            runner.tick()
        self.assertEqual(self.loop.job(job["id"])["state"], "blocked")
        self.assertEqual(self.loop.get(job["loop_id"])["status"], "needs_operator")
        self.assertEqual(self.count(), 0)

    def test_scheduler_refuses_transaction_and_does_not_leak_inherited_keys(self):
        runner = self.runner()
        with self.store.transaction(), self.assertRaises(RuntimeError):
            runner.tick()
        from odin.development_evaluator import _environment

        with mock.patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "synthetic-secret",
                "OPENAI_API_KEY": "synthetic-secret",
                "CLAUDECODE": "1",
            },
        ):
            environment = _environment()
        self.assertNotIn("ANTHROPIC_API_KEY", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CLAUDECODE", environment)


if __name__ == "__main__":
    unittest.main()
