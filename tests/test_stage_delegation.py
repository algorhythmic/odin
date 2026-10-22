"""Synthetic development stage routed through a separate fake Claude orchestrator."""
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from odin.contracts import identifier, strict_loads
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

    def stage(self, profile=None, *, max_rounds=12):
        payload = {'goal': 'synthetic staged development', 'session_id': self.native_session,
                   'max_rounds': max_rounds}
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

    def test_stage_delegation_without_budget_passes_no_budget_option(self):
        loop_id, stage_id = self.stage({'harness': 'claude-code', 'model': 'opus', 'subagent_model': 'haiku'})
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        orchestrator = self.open_orchestrator(budget_usd=None)
        self.assertIsNone(self.h.service.store.get(orchestrator)['budget_usd'])
        self.executive_call('loop_claim', ids)
        assigned = self.executive_call('loop_delegate', ids | {'orchestrator_session_id': orchestrator,
            'limits': {'iterations': 3}})
        self.assertEqual(assigned['limit_enforcement'],
                         {'budget': 'not_requested', 'iterations': 'harness_option'})
        self.assertEqual(self.h.service.store.get(assigned['assignment'])['limits'],
                         {'iterations': 3, 'budget_usd': None})
        self.assertEqual(self.h.gateway.delegation.launch_pending(), [assigned['turn']])
        self.h.wait(lambda: self.h.assignment_state(assigned['assignment'])['turns'][0]['state'] == 'returned')
        result = self.h.call('delegation_result', {'assignment_id': assigned['assignment']})
        argv = strict_loads(Path(result['transcript_paths']['spec.json']).read_text())['argv']
        self.assertNotIn('--max-budget-usd', argv)
        self.assertEqual(argv[argv.index('--max-turns') + 1], '3')

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

    def test_paused_pending_stage_can_gain_required_profile_without_restarting(self):
        loop_id, stage_id = self.stage(max_rounds=8)
        core = self.h.gateway.development_loop
        before = core.get(loop_id)
        stage_before = core.stage(stage_id)
        paused = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'pause',
            'expected_revision': before['revision']})['loop']
        profile = {'harness': 'claude-code', 'model': 'opus', 'subagent_model': 'haiku'}
        configure = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session,
            'action': 'configure_delegation', 'expected_revision': paused['revision'],
            'delegation_profile': profile}
        operation = identifier()
        changed = self.operator_call('loop_control', configure, operation)
        self.h.restart()
        core = self.h.gateway.development_loop
        self.assertEqual(changed, self.operator_call('loop_control', configure, operation))
        self.assertEqual(self.h.service.store.db.execute(
            "SELECT COUNT(*) FROM history WHERE json_extract(body, '$.kind')=?",
            ('development_loop.delegation_configured',)).fetchone()[0], 1)
        self.assertEqual(changed['loop']['status'], 'paused')
        self.assertEqual(changed['loop']['paused_from'], 'executive_pending')
        self.assertEqual(changed['loop']['round'], 1)
        self.assertEqual(changed['loop']['max_rounds'], 8)
        self.assertEqual(changed['loop']['current_stage'], stage_id)
        self.assertEqual(changed['loop']['session_id'], self.native_session)
        self.assertEqual(changed['loop']['revision'], paused['revision'] + 1)
        self.assertEqual(core.stage(stage_id), stage_before)
        self.assertEqual(changed['loop']['delegation_profile'], profile)
        with self.assertRaisesRegex(Conflict, 'replaced'):
            self.operator_call('loop_control', configure | {'expected_revision': changed['loop']['revision']})
        resumed = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'resume',
            'expected_revision': changed['loop']['revision']})['loop']
        self.assertEqual(resumed['status'], 'executive_pending')
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        self.executive_call('loop_claim', ids)
        with self.assertRaisesRegex(Conflict, 'delegated orchestrator'):
            self.executive_call('loop_ready', ids | {'evidence_packet': {}})
        orchestrator = self.open_orchestrator()
        assigned = self.executive_call('loop_delegate', ids | {
            'orchestrator_session_id': orchestrator,
            'limits': {'iterations': 3, 'budget_usd': 0.5}})
        self.assertEqual(assigned['stage_binding']['stage_id'], stage_id)

    def test_claimed_transition_refuses_stale_wrong_session_and_model_actor(self):
        loop_id, stage_id = self.stage()
        ids = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session}
        claimed = self.executive_call('loop_claim', ids)['loop']
        stage_before = self.h.gateway.development_loop.stage(stage_id)
        paused = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'pause',
            'expected_revision': claimed['revision']})['loop']
        payload = ids | {'action': 'configure_delegation',
            'expected_revision': paused['revision'],
            'delegation_profile': {'harness': 'claude-code', 'model': 'opus'}}
        with self.assertRaisesRegex(Conflict, 'stale'):
            self.operator_call('loop_control', payload | {'expected_revision': claimed['revision']})
        with self.assertRaises(PermissionError):
            self.operator_call('loop_control', payload | {'session_id': str(uuid.uuid4())})
        with self.assertRaises(PermissionError):
            self.executive_call('loop_control', payload)
        changed = self.operator_call('loop_control', payload)['loop']
        self.assertEqual(changed['paused_from'], 'executive_claimed')
        self.assertEqual(self.h.gateway.development_loop.stage(stage_id), stage_before)
        resumed = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'resume',
            'expected_revision': changed['revision']})['loop']
        self.assertEqual(resumed['status'], 'executive_claimed')

    def test_transition_refuses_nonquiescent_project_and_completion_evidence(self):
        loop_id, stage_id = self.stage()
        core = self.h.gateway.development_loop
        paused = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'pause'})['loop']
        payload = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session,
            'action': 'configure_delegation', 'expected_revision': paused['revision'],
            'delegation_profile': {'harness': 'claude-code', 'model': 'opus'}}
        orchestrator = self.open_orchestrator()
        assigned = self.h.call('delegation_assign', {'session_id': orchestrator,
            'objective': 'Synthetic unrelated work', 'criteria': [{'id': 'c', 'text': 'report'}],
            'scope': 'synthetic', 'output_contract': 'text', 'instructions': 'wait',
            'limits': {'iterations': 2, 'budget_usd': 0.5}})
        with self.assertRaisesRegex(Conflict, 'active delegated turn'):
            self.operator_call('loop_control', payload)
        turn = self.h.gateway.delegation._turn(assigned['turn'])
        self.h.gateway.delegation._save_turn(turn | {'state': 'lost'})
        stopped = self.h.call('delegation_session', {'action': 'stop',
            'session_id': orchestrator, 'reason': 'synthetic retirement after uncertain turn'})
        self.assertEqual(stopped['session']['state'], 'retired')
        with self.assertRaisesRegex(Conflict, 'lost delegated turn with unknown native outcome'):
            self.operator_call('loop_control', payload)
        self.h.gateway.delegation._save_turn(turn | {'state': 'failed'})
        job = core.job(core.get(loop_id)['current_job'])
        core._save_job(job | {'state': 'running'})
        with self.assertRaisesRegex(Conflict, 'active or unresolved evaluator job'):
            self.operator_call('loop_control', payload)
        core._save_job(job | {'state': 'lost'})
        with self.assertRaisesRegex(Conflict, 'active or unresolved evaluator job'):
            self.operator_call('loop_control', payload)
        core._save_job(job)
        stage = core.stage(stage_id)
        core._save_stage(stage | {'evidence': {'synthetic': 'already present'}})
        with self.assertRaisesRegex(Conflict, 'completion evidence'):
            self.operator_call('loop_control', payload)

    def test_restart_gate_counts_lost_turns_even_after_retirement(self):
        loop_id, _ = self.stage()
        def gate():
            return self.operator_call('loop_status', {'loop_id': loop_id})['quiescence']
        self.assertTrue(gate()['restart_quiescent'])
        orchestrator = self.open_orchestrator()
        assigned = self.h.call('delegation_assign', {'session_id': orchestrator,
            'objective': 'Synthetic lost work', 'criteria': [{'id': 'c', 'text': 'report'}],
            'scope': 'synthetic', 'output_contract': 'text', 'instructions': 'wait',
            'limits': {'iterations': 2, 'budget_usd': 0.5}})
        self.assertEqual(gate()['delegated_turns_running'], 1)
        delegation = self.h.gateway.delegation
        turn = delegation._turn(assigned['turn'])
        exited = subprocess.Popen([sys.executable, '-c', 'pass'], start_new_session=True)
        exited.wait()
        lost = turn | {'state': 'lost', 'finished_at': now(),
            'failure': 'runner exited without a result; native outcome unknown',
            'runner': {'pid': exited.pid, 'launched_at': now(), 'harness_pid': exited.pid,
                       'started_at': now()}}
        delegation._save_turn(lost)
        reading = gate()
        self.assertEqual(reading['delegated_turns_running'], 0)
        self.assertEqual(reading['delegated_turns_lost'], 1)
        self.assertFalse(reading['restart_quiescent'])
        self.assertEqual(reading['unresolved'][0]['kind'], 'delegated_turn_lost')
        self.assertEqual(reading['unresolved'][0]['id'], turn['id'])
        # Observed process absence is reported but does not establish the outcome.
        self.assertEqual(reading['unresolved'][0]['reason'],
                         'native outcome unknown; recorded processes absent')
        stopped = self.h.call('delegation_session', {'action': 'stop',
            'session_id': orchestrator, 'reason': 'synthetic retirement after a lost turn'})
        self.assertEqual(stopped['session']['state'], 'retired')
        retired = gate()
        self.assertFalse(retired['restart_quiescent'])
        self.assertEqual(retired['delegated_turns_lost'], 1)
        self.assertEqual(retired['unresolved'], reading['unresolved'])
        self.assertEqual(delegation._turn(turn['id']), lost)  # never erased or relabelled
        delegation._save_turn(lost | {'runner': None})
        self.assertEqual(gate()['unresolved'][0]['reason'],
                         'native outcome unknown; recorded processes unknown')
        harness = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],
                                   start_new_session=True)
        self.addCleanup(harness.wait)
        self.addCleanup(harness.kill)
        delegation._save_turn(lost | {'runner': lost['runner'] | {'harness_pid': harness.pid}})
        self.assertEqual(gate()['unresolved'][0]['reason'],
                         'native outcome unknown; recorded processes present')
        self.assertIsNone(harness.poll())  # observed, never signalled
        # Lost turns of any project close the service-wide gate.
        delegation._save_turn(lost | {'id': identifier(), 'project': identifier()})
        self.assertEqual(gate()['delegated_turns_lost'], 2)
        self.assertFalse(gate()['restart_quiescent'])

    def test_transition_refuses_existing_stage_binding(self):
        loop_id, stage_id = self.stage()
        paused = self.operator_call('loop_control', {'loop_id': loop_id, 'action': 'pause'})['loop']
        payload = {'loop_id': loop_id, 'stage_id': stage_id, 'session_id': self.native_session,
            'action': 'configure_delegation', 'expected_revision': paused['revision'],
            'delegation_profile': {'harness': 'claude-code', 'model': 'opus'}}
        from odin.development_delegation import initialize
        initialize(self.h.service.store)
        self.h.service.store.db.execute(
            'INSERT INTO development_delegations VALUES(?,?,?,?,?)',
            (stage_id, loop_id, self.h.project, identifier(), '{}'))
        with self.assertRaisesRegex(Conflict, 'already has a delegated assignment'):
            self.operator_call('loop_control', payload)
        self.assertIsNone(self.h.gateway.development_loop.get(loop_id)['delegation_profile'])


if __name__ == '__main__':
    unittest.main()
