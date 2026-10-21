"""Synthetic development stage routed through a separate fake Claude orchestrator."""
import tempfile
import unittest
import uuid

from odin.contracts import identifier
from odin.coordination import Actor
from odin.executive_service import submit_executive
from odin.gateway import GatewayContext
from odin.store import Conflict, now
from odin.usage import request, _tokens
from test_delegation import DelegationHarness


class StageDelegationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.h = DelegationHarness(self.temp.name)
        self.addCleanup(self.h.close)
        self.native_session = str(uuid.uuid4())
        self.operator = GatewayContext('terminal', Actor('operator', 'synthetic'))

    def operator_call(self, action, payload, operation=None):
        command = {'schema_version': 1, 'operation_id': operation or identifier(),
            'action': action, 'payload': {'project': self.h.project} | payload}
        return self.h.gateway.submit(command, context=self.operator)['result']

    def executive_call(self, action, payload, operation=None, *, project=None):
        project = project or self.h.project
        command = {'schema_version': 1, 'operation_id': operation or identifier(),
            'action': action, 'payload': {'project': project} | payload}
        return submit_executive(self.h.gateway, {'command': command}, project)['result']

    def stage(self, profile=None):
        payload = {'goal': 'synthetic staged development', 'session_id': self.native_session}
        if profile is not None:
            payload['delegation_profile'] = profile
        started = self.operator_call('loop_start', payload)
        loop, job = started['loop'], started['job']
        core = self.h.gateway.development_loop
        core.mark_evaluator_started(loop['id'], job['id'], job['packet_digest'], identifier())
        evaluated = core.accept_evaluation(loop['id'], job['id'], job['packet_digest'],
            {'decision': 'continue', 'assessment': 'synthetic evaluator', 'findings': [],
             'next_prompt': 'Implement a synthetic stage', 'evidence_refs': []}, identifier())
        return loop['id'], evaluated['stage']['id']

    def open_orchestrator(self, **options):
        opened = self.h.call('delegation_session', {'action': 'create', 'harness': 'claude-code',
            'workspace': str(self.h.workspace), 'briefing': 'Synthetic orchestrator',
            'model': 'opus', 'subagent_model': 'haiku', 'budget_usd': 5} | options)
        return opened['session']['id']

    def test_stage_requires_accepted_separate_return_and_replays(self):
        loop_id, stage_id = self.stage({'harness': 'claude-code', 'model': 'opus', 'subagent_model': 'haiku'})
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        orchestrator = self.open_orchestrator()
        with self.assertRaises(Conflict):
            self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        self.executive_call('loop_claim', ids)
        with self.assertRaises(Conflict):
            self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        delegation = ids | {'orchestrator_session_id': orchestrator,
                            'limits': {'iterations': 3, 'budget_usd': 0.5}}
        operation = identifier()
        assigned = self.executive_call('loop_delegate', delegation, operation)
        self.assertEqual(assigned, self.executive_call('loop_delegate', delegation, operation))
        assignment_id = assigned['assignment']
        turn_id = assigned['turn']
        self.h.restart()
        self.assertEqual(self.executive_call('loop_delegate', delegation, operation), assigned)
        rows = self.h.service.store.db.execute('SELECT COUNT(*) FROM development_delegations WHERE stage_id=?', (stage_id,)).fetchone()[0]
        self.assertEqual(rows, 1)
        self.assertEqual(assigned['stage_binding']['stage_id'], stage_id)
        self.operator_call('usage_configure', {'policy': {'mode': 'hold', 'missing_telemetry': 'hold',
            'limits': {'max_requests': 1}}})
        self.assertEqual(self.h.gateway.delegation.launch_pending(), [])
        self.assertEqual(self.h.assignment_state(assignment_id)['turns'][0]['id'], turn_id)
        self.operator_call('usage_configure', {'policy': {'mode': 'observe'}})
        self.assertEqual(self.h.gateway.delegation.launch_pending(), [turn_id])
        self.h.wait(lambda: self.h.assignment_state(assignment_id)['turns'][0]['state'] == 'returned')
        with self.assertRaises(Conflict):
            self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        self.h.call('delegation_close', {'assignment_id': assignment_id,
            'disposition': 'accepted', 'evidence': {'stage': ['turn:' + turn_id]},
            'reason': 'inspected synthetic return'})
        turn = self.h.gateway.delegation._turns(assignment=assignment_id)[-1]
        self.h.gateway.delegation._save_turn(turn | {'result': turn['result'] | {'native_session_id': None}})
        with self.assertRaisesRegex(Conflict, 'observed orchestrator'):
            self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        self.h.gateway.delegation._save_turn(turn)
        ready = self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        self.assertEqual(ready['stage']['state'], 'ready')
        self.assertEqual(self.h.gateway.development_loop.stage(stage_id)['evidence']['delegation']['assignment_id'], assignment_id)
        capture = self.executive_call('loop_capture', {'session_id': self.native_session,
            'hook_event_name': 'Stop', 'last_assistant_message': 'Synthetic stage complete.\n' + ready['completion_marker']})
        self.assertTrue(capture['captured'])
        with self.assertRaises(Conflict):
            self.executive_call('loop_delegate', delegation, operation)

    def test_wrong_profile_project_and_stale_stage_refused(self):
        loop_id, stage_id = self.stage({'harness': 'claude-code', 'model': 'opus', 'subagent_model': 'haiku'})
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        wrong = self.open_orchestrator(model='sonnet')
        self.executive_call('loop_claim', ids)
        with self.assertRaises((Conflict, PermissionError)):
            self.executive_call('loop_delegate', ids | {'orchestrator_session_id': wrong,
                'limits': {'iterations': 3, 'budget_usd': 0.5}})
        other_project = identifier()
        stamp = now()
        self.h.service.store.create({'schema_version': 1, 'record_type': 'Project',
            'id': other_project, 'rev': 1, 'created_at': stamp, 'updated_at': stamp,
            'name': 'other synthetic', 'sources': [], 'delegations': [],
            'interface_decision_owner': None})
        with self.assertRaises((Conflict, PermissionError)):
            self.executive_call('loop_delegate', ids | {'orchestrator_session_id': wrong,
                'limits': {'iterations': 3, 'budget_usd': 0.5}}, project=other_project)
        with self.assertRaises((Conflict, PermissionError)):
            self.executive_call('loop_delegate', ids | {'stage_id': identifier(),
                'orchestrator_session_id': wrong, 'limits': {'iterations': 3, 'budget_usd': 0.5}})

    def test_usage_requires_orchestrator_binding_even_within_same_project(self):
        loop_id, stage_id = self.stage({'harness': 'claude-code', 'model': 'opus'})
        orchestrator = self.open_orchestrator()
        native = self.h.service.store.get(orchestrator)['native_session_id']
        observation = request(provider='claude', project_id=self.h.project,
            source='synthetic', session_id=native, agent_id='orchestrator',
            request_id='observed-request', model='opus', tokens=_tokens(1, 0, 0, 1),
            loop_id=loop_id)
        payload = {'source_id': 'fixture:orchestrator', 'observations': [observation]}
        with self.assertRaisesRegex(PermissionError, 'lineage'):
            self.operator_call('usage_import', payload)
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        self.executive_call('loop_claim', ids)
        self.executive_call('loop_delegate', ids | {'orchestrator_session_id': orchestrator,
            'limits': {'iterations': 3, 'budget_usd': 0.5}})
        self.assertEqual(self.operator_call('usage_import', payload)['outcomes'], {'inserted': 1})

    def test_default_loop_ready_without_delegation(self):
        loop_id, stage_id = self.stage()
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        self.executive_call('loop_claim', ids)
        orchestrator = self.open_orchestrator()
        with self.assertRaisesRegex(Conflict, 'opted'):
            self.executive_call('loop_delegate', ids | {'orchestrator_session_id': orchestrator,
                'limits': {'iterations': 3, 'budget_usd': 0.5}})
        ready = self.executive_call('loop_ready', ids | {'evidence_packet': {'revision': 'synthetic'}})
        self.assertEqual(ready['stage']['state'], 'ready')


if __name__ == '__main__':
    unittest.main()
