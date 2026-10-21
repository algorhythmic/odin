"""Synthetic gateway authorization and replay for usage and continuity metadata."""
import tempfile
import sys
from pathlib import Path
import unittest
import uuid

from odin.contracts import identifier, strict_loads
from jsonschema import ValidationError
from odin.coordination import Actor
from odin.executive_service import prepare_project, submit_executive
from odin.executive_mcp import ExecutiveBridge
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict
from odin.usage import _tokens, request
from odin.development_evaluator import EvaluatorRunner
from test_development_evaluator import NATIVE


class UsageGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = prepare_project(self.temp.name)
        self.other = prepare_project(self.temp.name)
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        self.operator = GatewayContext('terminal', Actor('operator', 'synthetic'))
        self.session = str(uuid.uuid4())
        self.runners = []

    def tearDown(self):
        for runner in self.runners:
            for child in runner._children:
                if child.poll() is None:
                    child.terminate()
                child.wait(timeout=3)
        self.service.close()
        self.temp.cleanup()

    def send(self, action, payload, *, operation=None, project=None, executive=False):
        project = project or self.project
        command = {'schema_version': 1, 'operation_id': operation or identifier(),
                   'action': action, 'payload': {'project': project} | payload}
        if executive:
            return submit_executive(self.gateway, {'command': command}, project)['result']
        return self.gateway.submit(command, context=self.operator)['result']

    def test_mcp_tools_bind_project_and_native_session(self):
        def gateway(command):
            return submit_executive(self.gateway, {'command': command}, self.project)
        bridge = ExecutiveBridge(self.project, gateway, development_loop=True,
                                 session_id=self.session)
        names = {tool['name'] for tool in bridge.tools()}
        self.assertIn('odin_usage_status', names)
        self.assertIn('odin_context_checkpoint', names)
        self.assertNotIn('odin_usage_import', names)
        self.assertNotIn('odin_usage_configure', names)
        status = bridge.call('odin_usage_status', {})
        self.assertFalse(status['isError'])
        receipt = strict_loads(status['content'][0]['text'])
        self.assertEqual(receipt['result']['usage']['project_id'], self.project)
        checkpoint = {'revision': 1, 'branch': 'codex/synthetic', 'worktree': '/tmp/synthetic',
            'artifact_refs': [], 'open_obligations': [], 'pending_reviews': [],
            'operation_ids': [], 'next_action': 'continue', 'summary': 'attributed'}
        operation = identifier()
        saved = bridge.call('odin_context_checkpoint', {'operation_id': operation,
            'checkpoint': checkpoint})
        self.assertFalse(saved['isError'])
        self.assertEqual(strict_loads(saved['content'][0]['text'])['result']['checkpoint']['session_id'], self.session)
        self.assertEqual(saved, bridge.call('odin_context_checkpoint', {'operation_id': operation,
            'checkpoint': checkpoint}))
        other_bridge = ExecutiveBridge(self.other, gateway, development_loop=True,
                                       session_id=self.session)
        self.assertTrue(other_bridge.call('odin_usage_status', {})['isError'])

    def test_import_authority_project_scope_replay_and_status(self):
        observation = request(provider='claude', project_id=self.project,
            source='synthetic', session_id=self.session, agent_id='worker',
            request_id='req-1', model='haiku', tokens=_tokens(10, 2, 1, 3))
        payload = {'source_id': 'fixture:1', 'observations': [observation],
            'coverage': {'complete': True, 'truncated': False, 'malformed_lines': 0}}
        with self.assertRaises(PermissionError):
            self.send('usage_import', payload, executive=True)
        operation = identifier()
        first = self.send('usage_import', payload, operation=operation)
        self.assertEqual(first, self.send('usage_import', payload, operation=operation))
        replay = self.send('usage_import', payload)
        self.assertEqual(replay['outcomes'], {'duplicate': 1})
        status = self.send('usage_status', {})
        self.assertEqual(status['usage']['request_count'], 1)
        self.assertEqual(status['usage']['tokens']['uncached_input'], 10)
        self.assertEqual(status['usage']['cache_inclusive_input_tokens'], 13)
        self.assertEqual(self.send('usage_status', {}, project=self.other)['usage']['request_count'], 0)
        self.assertEqual(self.send('usage_status', {}, executive=True)['usage']['request_count'], 1)
        with self.assertRaises((PermissionError, Conflict)):
            self.send('usage_import', payload, project=self.other)
        with self.assertRaises((PermissionError, Conflict)):
            self.send('usage_import', payload, project=self.other, operation=operation)
        with self.assertRaises((PermissionError, Conflict)):
            self.send('usage_import', payload | {'observations': [{**observation, 'project_id': self.other}]})
        self.assertEqual(self.send('usage_status', {})['usage']['request_count'], 1)

    def test_import_rejects_unknown_native_loop_lineage(self):
        loop = self.send('loop_start', {'goal': 'synthetic', 'session_id': self.session})['loop']
        observation = request(provider='claude', project_id=self.project,
            source='synthetic', session_id=str(uuid.uuid4()), agent_id='worker',
            request_id='wrong-session', model='haiku', tokens=_tokens(1, 0, 0, 1),
            loop_id=loop['id'])
        with self.assertRaisesRegex(PermissionError, 'lineage'):
            self.send('usage_import', {'source_id': 'fixture:wrong-session', 'observations': [observation]})
        self.assertEqual(self.send('usage_status', {})['usage']['request_count'], 0)

    def test_checkpoint_native_uuid_and_loop_stage_binding_survive_restart(self):
        started = self.send('loop_start', {'goal': 'synthetic', 'session_id': self.session})
        loop_id = started['loop']['id']
        job = started['job']
        core = self.gateway.development_loop
        core.mark_evaluator_started(loop_id, job['id'], job['packet_digest'], identifier())
        evaluated = core.accept_evaluation(loop_id, job['id'], job['packet_digest'],
            {'decision': 'continue', 'assessment': 'synthetic', 'findings': [],
             'next_prompt': 'Do work', 'evidence_refs': []}, identifier())
        stage_id = evaluated['stage']['id']
        checkpoint = {'revision': 1, 'branch': 'codex/synthetic', 'worktree': '/tmp/synthetic',
            'artifact_refs': [], 'open_obligations': ['finish stage'], 'pending_reviews': [],
            'operation_ids': ['op-1'], 'next_action': 'delegate', 'summary': 'attributed'}
        with self.assertRaises((ValueError, Conflict, ValidationError)):
            self.send('context_checkpoint', {'session_id': 'not-a-uuid', 'checkpoint': checkpoint})
        with self.assertRaises((ValueError, Conflict)):
            self.send('context_checkpoint', {'session_id': str(uuid.uuid4()),
                'checkpoint': checkpoint | {'loop_id': loop_id, 'stage_id': stage_id}})
        operation = identifier()
        payload = {'session_id': self.session,
                   'checkpoint': checkpoint | {'loop_id': loop_id, 'stage_id': stage_id}}
        first = self.send('context_checkpoint', payload, operation=operation, executive=True)
        self.assertEqual(first, self.send('context_checkpoint', payload, operation=operation, executive=True))
        self.assertEqual(self.send('context_status', {'session_id': self.session})['checkpoint'], first['checkpoint'])
        with self.assertRaises((PermissionError, Conflict)):
            self.send('context_checkpoint', payload, project=self.other, executive=True)
        self.service.close()
        self.service = Service(self.temp.name)
        self.gateway = Gateway(self.service)
        self.assertEqual(self.send('context_status', {'session_id': self.session})['checkpoint'], first['checkpoint'])

    def test_evaluator_dispatch_held_then_released_with_same_job(self):
        root = Path(self.temp.name)
        workspace = root / 'workspace'
        workspace.mkdir()
        profile = root / 'profile'
        profile.mkdir(mode=0o700)
        binary = root / 'fake-evaluator'
        binary.write_text(NATIVE)
        binary.chmod(0o700)
        started = self.send('loop_start', {'goal': 'synthetic', 'session_id': self.session})
        job_id = started['job']['id']
        config = {'schema_version': 1, 'enabled': True, 'harness': 'codex',
            'binary': str(binary), 'workspace': str(workspace), 'config_dir': str(profile),
            'model': 'fixture', 'timeout_seconds': 30}
        runner = EvaluatorRunner(self.gateway.development_loop, self.service.directory, config)
        self.runners.append(runner)
        self.send('usage_configure', {'policy': {'mode': 'hold', 'missing_telemetry': 'hold',
            'limits': {'max_requests': 1}}})
        held = runner.tick()
        self.assertIn(job_id, held['held'])
        self.assertEqual(self.gateway.development_loop.job(job_id)['state'], 'pending')
        self.send('usage_configure', {'policy': {'mode': 'observe'}})
        released = runner.tick()
        self.assertIn(job_id, released['started'])
        self.assertEqual(self.gateway.development_loop.job(job_id)['id'], job_id)

    def test_policy_hold_then_observe_allows_new_stage_claim(self):
        started = self.send('loop_start', {'goal': 'synthetic', 'session_id': self.session})
        loop_id = started['loop']['id']
        job = started['job']
        self.gateway.development_loop.mark_evaluator_started(loop_id, job['id'], job['packet_digest'], identifier())
        evaluated = self.gateway.development_loop.accept_evaluation(loop_id, job['id'], job['packet_digest'],
            {'decision': 'continue', 'assessment': 'synthetic', 'findings': [],
             'next_prompt': 'Do work', 'evidence_refs': []}, identifier())
        stage_id = evaluated['stage']['id']
        self.send('usage_configure', {'policy': {'mode': 'hold', 'missing_telemetry': 'hold',
            'limits': {'max_requests': 1}}})
        claim = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.session}
        operation = identifier()
        held = self.send('loop_claim', claim, operation=operation, executive=True)
        self.assertTrue(held['held'])
        self.assertEqual(held['admission']['decision'], 'hold')
        with self.assertRaisesRegex(Conflict, 'identity conflict'):
            self.send('loop_claim', claim | {'prompt_id': 'changed'}, operation=operation, executive=True)
        self.send('usage_configure', {'policy': {'mode': 'observe'}})
        result = self.send('loop_claim', claim, operation=operation, executive=True)
        self.assertEqual(result['stage']['state'], 'claimed')


if __name__ == '__main__':
    unittest.main()
