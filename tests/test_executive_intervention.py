"""Synthetic permits, durable uncertainty and native hook enforcement."""
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.contracts import ROOT, identifier, strict_loads
from odin.coordination import Actor
from odin import executive_runtime as runtime
from odin.executive_service import prepare_project, submit_executive
from odin.executive_mcp import ExecutiveBridge, SocketGateway
from odin.executive_intervention import delegation_guard, initialize
from odin.executive_intervention_hook import configured_memory, handle
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.store import Conflict


class InterventionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.state = Path(temp.name) / 'state'
        self.project = prepare_project(self.state)
        runtime.prepare(self.state, config_dir=Path(temp.name)/'login', project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state): pass
        runtime.configure_execution_role(self.state, implementation_mode='delegated')
        with runtime._owned_runtime(self.state): pass
        self.manifest = runtime._load(self.state)[0]
        self.service = Service(self.state); self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.native = self.manifest['native_session_id']
        self.bridge = ExecutiveBridge(self.project, self.send, development_loop=True, session_id=self.native)
        self.call = {'tool':'Bash', 'input':{'command':'pwd','timeout':1000}}

    def send(self, command):
        return submit_executive(self.gateway, {'command':command}, self.project)

    def begin(self, **kw):
        args={'operation_id':identifier(),'purpose':'Inspect current checkout','ttl_seconds':60,'calls':[self.call]}|kw
        result=self.bridge.call('odin_intervention_begin', args)
        self.assertFalse(result['isError'],result)
        return strict_loads(result['content'][0]['text'])['result']['intervention']

    def event(self, kind='PreToolUse', **kw):
        return {'hook_event_name':kind,'session_id':self.native,'cwd':self.manifest['repository_root'],
                'tool_name':'Bash','tool_use_id':'synthetic-tool-1','tool_input':self.call['input']}|kw

    def hook(self, event):
        return handle(event,state=self.state,project=self.project,session=self.native,gateway=self.send)

    def test_exact_one_use_permit_finish_automatically_restores_mode(self):
        with self.assertRaises(PermissionError): self.hook(self.event())
        item=self.begin()
        with self.assertRaises(Conflict): delegation_guard(self.service.store,self.project)
        with self.assertRaises(PermissionError): self.hook(self.event(tool_input={'command':'pwd; touch bad','timeout':1000}))
        allowed=self.hook(self.event(tool_input=self.call['input']|{'description':'label only'}))
        self.assertEqual(allowed['hookSpecificOutput']['permissionDecision'],'allow')
        with self.assertRaises(Conflict): self.hook(self.event())
        blocked=self.bridge.call('odin_intervention_end',{'operation_id':identifier(),'intervention_id':item['id']})
        self.assertTrue(blocked['isError'])
        self.hook(self.event('PostToolUse'))
        self.assertEqual(self.gateway.store.db.execute('select count(*) from executive_interventions').fetchone()[0],1)
        status=self.bridge.call('odin_intervention_status',{})
        self.assertEqual(strict_loads(status['content'][0]['text'])['result']['mode'],'executive')
        delegation_guard(self.service.store,self.project)
        # No command or edit contents enter the intervention record or gateway audit.
        body=self.service.store.db.execute('select body from executive_interventions').fetchone()[0]
        self.assertNotIn('pwd',body)

    def test_expired_admission_stays_unknown_and_blocks_delegation(self):
        self.begin();self.hook(self.event())
        row=self.service.store.db.execute('select id,body from executive_interventions').fetchone()
        item=strict_loads(row[1]);item['expires_at']='2000-01-01T00:00:00Z'
        self.service.store.db.execute('update executive_interventions set body=? where id=?',(json.dumps(item),row[0]))
        with self.assertRaises(Conflict): delegation_guard(self.service.store,self.project)
        status=strict_loads(self.bridge.call('odin_intervention_status',{})['content'][0]['text'])['result']
        self.assertEqual(status['mode'],'executive');self.assertTrue(status['in_flight_unknown'])
        self.hook(self.event('PostToolUseFailure'))
        delegation_guard(self.service.store,self.project)

    def test_expired_unused_and_explicit_end_deny_new_calls(self):
        item=self.begin()
        self.assertFalse(self.bridge.call('odin_intervention_end',{'operation_id':identifier(),'intervention_id':item['id']})['isError'])
        with self.assertRaises(PermissionError): self.hook(self.event())
        item=self.begin();item['expires_at']='2000-01-01T00:00:00Z'
        self.service.store.db.execute('update executive_interventions set body=? where id=?',(json.dumps(item),item['id']))
        with self.assertRaises(PermissionError): self.hook(self.event())
        delegation_guard(self.service.store,self.project)

    def test_busy_boundaries_identity_and_transport_failure(self):
        with patch('odin.executive_intervention._busy',return_value=True):
            result=self.bridge.call('odin_intervention_begin',{'operation_id':identifier(),'purpose':'repair','ttl_seconds':60,'calls':[self.call]})
            self.assertTrue(result['isError'])
        self.begin()
        with patch('odin.executive_intervention._busy',return_value=True):
            with self.assertRaises(Conflict):self.hook(self.event())
        with self.assertRaises(ValueError):self.hook(self.event(session_id='other'))
        with self.assertRaises(PermissionError):self.hook(self.event(cwd='/tmp/other'))
        with self.assertRaises(ValueError):
            handle(self.event(),state=self.state,project=self.project,session=self.native,gateway=lambda c:{'error':'failure'})
        with self.assertRaises(ValueError):self.hook(self.event(tool_input={'command':'pwd','run_in_background':True}))

    def test_actual_queue_turn_guard_refuses_active_intervention(self):
        self.begin()
        before = self.service.store.db.execute(
            'select count(*) from delegation_turns').fetchone()[0]
        with self.assertRaisesRegex(Conflict, 'executive_intervention_active'):
            self.gateway.delegation._queue_turn(
                {'id': identifier(), 'project': self.project}, {'id': identifier()},
                kind='assignment', prompt='synthetic implementation',
                operation=identifier(), actor='synthetic-executive')
        self.assertEqual(self.service.store.db.execute(
            'select count(*) from delegation_turns').fetchone()[0], before)

    def test_persisted_busy_turn_states_refuse_intervention_begin(self):
        initialize(self.service.store)
        for state in ('queued', 'launching', 'running', 'interrupting'):
            with self.subTest(state=state):
                turn = identifier()
                self.service.store.db.execute(
                    'insert into delegation_turns (id,session,assignment,project,seq,state,body) '
                    'values (?,?,?,?,?,?,?)',
                    (turn, identifier(), identifier(), self.project, 1, state, '{}'))
                with self.assertRaisesRegex(Conflict, 'delegated_work_active'):
                    self.send({'schema_version': 1, 'operation_id': identifier(),
                               'action': 'intervention_begin',
                               'payload': {'project': self.project,
                                           'session_id': self.native,
                                           'purpose': 'Inspect current checkout',
                                           'ttl_seconds': 60,
                                           'calls': [self.call]}})
                self.assertEqual(self.service.store.db.execute(
                    'select count(*) from executive_interventions').fetchone()[0], 0)
                self.service.store.db.execute('delete from delegation_turns where id=?', (turn,))

    def test_expired_multi_permit_post_records_finish_without_false_closure(self):
        second = {'tool': 'Bash', 'input': {'command': 'pwd -P', 'timeout': 1000}}
        item = self.begin(calls=[self.call, second])
        self.hook(self.event())
        item = strict_loads(self.service.store.db.execute(
            'select body from executive_interventions where id=?',
            (item['id'],)).fetchone()[0])
        item['expires_at'] = '2000-01-01T00:00:00Z'
        self.service.store.db.execute(
            'update executive_interventions set body=? where id=?',
            (json.dumps(item), item['id']))
        self.assertEqual(self.hook(self.event('PostToolUse')), {})
        status = strict_loads(self.bridge.call(
            'odin_intervention_status', {})['content'][0]['text'])['result']
        self.assertEqual(status['mode'], 'executive')
        self.assertEqual(status['effective_state'], 'expired')
        self.assertEqual(status['intervention']['state'], 'active')
        self.assertEqual([p['state'] for p in status['intervention']['permits']],
                         ['finished', 'available'])
        with self.assertRaises(PermissionError):
            self.hook(self.event(tool_input=second['input'], tool_use_id='second'))

    def test_only_operator_can_reconcile_uncertain_admission(self):
        item = self.begin()
        self.hook(self.event())
        item = strict_loads(self.service.store.db.execute(
            'select body from executive_interventions where id=?',
            (item['id'],)).fetchone()[0])
        item['expires_at'] = '2000-01-01T00:00:00Z'
        self.service.store.db.execute(
            'update executive_interventions set body=? where id=?',
            (json.dumps(item), item['id']))
        command = {'schema_version': 1, 'operation_id': identifier(),
                   'action': 'intervention_reconcile',
                   'payload': {'project': self.project, 'session_id': self.native,
                               'intervention_id': item['id'],
                               'observation': 'Synthetic operator observed no process running'}}
        with self.assertRaises(PermissionError):
            self.send(command)
        with self.assertRaises(Conflict):
            delegation_guard(self.service.store, self.project)
        receipt = self.gateway.submit(command, context=GatewayContext(
            'terminal', Actor('operator', 'local-operator')))
        reconciled = receipt['result']['intervention']
        self.assertEqual(reconciled['state'], 'closed')
        self.assertEqual(reconciled['permits'][0]['state'], 'reconciled')
        self.assertFalse(receipt['result']['in_flight_unknown'])
        delegation_guard(self.service.store, self.project)

    def test_native_hook_round_trip_through_real_executive_socket(self):
        # The subprocess owns the single writer; bridge and hook use the same
        # private socket contract as the native pilot, with synthetic inputs.
        self.service.close()
        process = subprocess.Popen(
            [sys.executable, '-m', 'odin', '--state', str(self.state), 'serve',
             '--executive-project', self.project],
            env=os.environ | {'PYTHONPATH': str(ROOT / 'python')},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def stop():
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.communicate()
        self.addCleanup(stop)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(15), 'fixture service did not start')
        ready = process.stdout.readline()
        if not ready.startswith('Fixture service ready:'):
            _, errors = process.communicate(timeout=5)
            self.fail('fixture service failed to start: ' + errors)
        socket = SocketGateway(self.state, timeout=3)
        bridge = ExecutiveBridge(self.project, socket, development_loop=True,
                                 session_id=self.native)
        started = bridge.call('odin_intervention_begin', {
            'operation_id': identifier(), 'purpose': 'Inspect current checkout',
            'ttl_seconds': 60, 'calls': [self.call]})
        self.assertFalse(started['isError'], started)
        intervention = strict_loads(started['content'][0]['text'])['result']['intervention']
        self.assertEqual(intervention['state'], 'active')
        allowed = handle(self.event(), state=self.state, project=self.project,
                         session=self.native, gateway=socket)
        self.assertEqual(allowed['hookSpecificOutput']['permissionDecision'], 'allow')
        self.assertEqual(handle(self.event('PostToolUse'), state=self.state,
                                project=self.project, session=self.native, gateway=socket), {})
        status = bridge.call('odin_intervention_status', {})
        self.assertFalse(status['isError'], status)
        self.assertEqual(strict_loads(status['content'][0]['text'])['result']['mode'],
                         'executive')
        with self.assertRaises(Exception):
            handle(self.event(), state=self.state, project=self.project,
                   session=self.native, gateway=socket)

    def test_hook_rejects_unconfirmed_or_mismatched_receipt(self):
        self.begin()
        def receipt(command, result):
            return {'schema_version': 1, 'operation_id': command['operation_id'],
                    'label': 'fake-backend evidence', 'result': result}
        event = self.event()
        failures = [
            lambda command: receipt(command, {}),
            lambda command: receipt(command, {'mode': 'intervention', 'intervention':
                {'schema_version': 1, 'id': identifier(), 'project': self.project,
                 'session_id': self.native, 'purpose': 'repair',
                 'created_at': '2026-01-01T00:00:00Z',
                 'expires_at': '2099-01-01T00:00:00Z', 'state': 'active',
                 'permits': [{'tool': 'Bash', 'input_digest': '0' * 64,
                              'state': 'admitted', 'tool_use_id': event['tool_use_id']}]}}),
            lambda command: receipt(command, {'recorded': False}),
            lambda command: receipt(command, {}) | {'operation_id': identifier()},
            lambda command: {'schema_version': 1, 'operation_id': command['operation_id'],
                             'label': 'wrong', 'result': {}},
        ]
        for fake in failures:
            with self.subTest(fake=fake), self.assertRaises(Exception):
                handle(event, state=self.state, project=self.project,
                       session=self.native, gateway=fake)
        self.assertTrue(self.hook(event)['hookSpecificOutput']['permissionDecision'] == 'allow')

    def test_hook_rejects_expired_or_wrong_native_admission_after_dispatch(self):
        self.begin()
        def stale(command):
            response = self.send(command)
            response['result']['intervention']['expires_at'] = '2000-01-01T00:00:00Z'
            return response
        with self.assertRaises(ValueError):
            handle(self.event(), state=self.state, project=self.project,
                   session=self.native, gateway=stale)
        # The service may have consumed the permit despite the failed response;
        # a second PreToolUse must not turn that uncertainty into execution.
        with self.assertRaises(Conflict):
            self.hook(self.event())

    def test_configured_hook_settings_and_native_tool_visibility(self):
        spec=runtime.launch_spec(self.state,resume=True)
        argv=spec['argv'];denied=argv[argv.index('--disallowedTools')+1].split(',')
        self.assertNotIn('Bash',denied);self.assertIn('Agent',denied)
        settings=json.loads(argv[argv.index('--settings')+1])
        for name in ['PreToolUse','PostToolUse','PostToolUseFailure']:
            hook=settings['hooks'][name][0]['hooks'][0]
            self.assertEqual(hook['onFailure'],'block')
            self.assertIn('odin.executive_intervention_hook',hook['args'])
        self.assertEqual(argv[argv.index('--resume')+1],self.native)

class MemoryDirectoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.state = self.temp / 'state'
        self.project = prepare_project(self.state)
        runtime.prepare(self.state, config_dir=self.temp/'login', project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)
        runtime.enable_development(self.state)
        with runtime._owned_runtime(self.state): pass
        runtime.configure_execution_role(self.state, implementation_mode='delegated')
        with runtime._owned_runtime(self.state): pass
        self.manifest = runtime._load(self.state)[0]
        self.service = Service(self.state); self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.native = self.manifest['native_session_id']
        self.bridge = ExecutiveBridge(self.project, self.send, development_loop=True, session_id=self.native)
        self.memory = self.temp / 'memory'; self.memory.mkdir()
        self.outside = self.temp / 'outside'; self.outside.mkdir()
        self.calls = []

    def send(self, command):
        return submit_executive(self.gateway, {'command':command}, self.project)

    def refuse(self, request):
        self.calls.append(request)
        return {'error': 'refused'}

    def event(self, tool, tool_input, kind='PreToolUse'):
        return {'hook_event_name':kind,'session_id':self.native,'cwd':self.manifest['repository_root'],
                'tool_name':tool,'tool_use_id':'synthetic-tool-1','tool_input':tool_input}

    def decide(self, event, gateway=None):
        return handle(event, state=self.state, project=self.project, session=self.native,
                      gateway=gateway or self.refuse, memory=configured_memory(self.state))

    def configure(self, path=None):
        runtime.configure_memory_directory(self.state, directory=str(path or self.memory))

    def assertGateway(self, event):
        self.calls.clear()
        with self.assertRaises(ValueError): self.decide(event)
        self.assertEqual(len(self.calls), 1)

    def test_unconfigured_write_goes_to_gateway(self):
        self.assertGateway(self.event('Write', {'file_path': str(self.memory/'n.md'), 'content': 'x'}))

    def test_configured_write_and_edit_allowed_without_gateway(self):
        self.configure()
        (self.memory/'old.md').write_text('a')
        (self.memory/'sub').mkdir()
        for tool, inputs in [('Write', {'file_path': str(self.memory/'n.md'), 'content': 'x'}),
                             ('Edit', {'file_path': str(self.memory/'old.md'), 'old_string': 'a', 'new_string': 'b'}),
                             ('Write', {'file_path': str(self.memory/'sub'/'n.md'), 'content': 'x'})]:
            result = self.decide(self.event(tool, inputs))
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'allow')
            self.assertEqual(result['hookSpecificOutput']['permissionDecisionReason'], 'Configured executive memory directory.')
            self.assertEqual(self.decide(self.event(tool, inputs, 'PostToolUse')), {})
        self.assertEqual(self.calls, [])

    def test_rejected_memory_writes_fall_through_to_gateway(self):
        self.configure()
        (self.memory/'real.md').write_text('a')
        (self.outside/'secret.md').write_text('s')
        os.symlink(self.outside, self.memory/'linkdir')
        os.symlink(self.outside/'secret.md', self.memory/'link.md')
        cases = [
            {'file_path': str(self.memory/'..'/'outside'/'x.md'), 'content': 'x'},
            {'file_path': str(self.memory/'link.md'), 'content': 'x'},
            {'file_path': str(self.memory/'linkdir'/'x.md'), 'content': 'x'},
            {'file_path': str(self.outside/'x.md'), 'content': 'x'},
            {'file_path': str(self.memory), 'content': 'x'},
            {'file_path': str(self.memory/'missing'/'x.md'), 'content': 'x'},
        ]
        for inputs in cases:
            self.assertGateway(self.event('Write', inputs))
        # Relative or non-string paths are refused by the existing normalizer before any gateway call.
        for inputs in [{'file_path': 'note.md', 'content': 'x'}, {'file_path': 7, 'content': 'x'}]:
            self.calls.clear()
            with self.assertRaises(ValueError): self.decide(self.event('Write', inputs))
        self.assertEqual(self.calls, [])

    def test_symlinked_configured_directory_rejected(self):
        real = self.temp / 'real'; real.mkdir()
        link = self.temp / 'link'; os.symlink(real, link)
        with self.assertRaises(ValueError): self.configure(link)
        self.configure()
        moved = self.temp / 'moved'; self.memory.rename(moved); os.symlink(moved, self.memory)
        self.assertGateway(self.event('Write', {'file_path': str(self.memory/'n.md'), 'content': 'x'}))

    def test_bash_and_notebook_inside_directory_still_gateway(self):
        self.configure()
        self.assertGateway(self.event('Bash', {'command': f'touch {self.memory}/n.md'}))
        self.assertGateway(self.event('NotebookEdit', {'notebook_path': str(self.memory/'n.ipynb')}))

    def test_post_failure_for_memory_write_does_not_call_gateway(self):
        self.configure()
        event = self.event('Write', {'file_path': str(self.memory/'n.md'), 'content': 'x'}, 'PostToolUseFailure')
        self.assertEqual(self.decide(event), {})
        self.assertEqual(self.calls, [])

    def test_existing_permit_still_allows_write_outside_directory(self):
        self.configure()
        target = str(self.outside/'x.md')
        call = {'tool': 'Write', 'input': {'file_path': target, 'content': 'x'}}
        result = self.bridge.call('odin_intervention_begin', {'operation_id': identifier(),
            'purpose': 'Write a synthetic note', 'ttl_seconds': 60, 'calls': [call]})
        self.assertFalse(result['isError'], result)
        event = self.event('Write', call['input'])
        allowed = self.decide(event, gateway=self.send)
        self.assertEqual(allowed['hookSpecificOutput']['permissionDecisionReason'],
                         'Recorded single-use Odin intervention permit.')

    def test_configuration_validation(self):
        bad = ['relative', str(self.memory/'..'/'outside'), str(self.temp/'missing'),
               str(self.temp/'state'), str(ROOT), str(ROOT/'python')]
        for value in bad:
            with self.assertRaises(ValueError, msg=value): runtime.configure_memory_directory(self.state, directory=value)
        file = self.temp/'file.md'; file.write_text('x')
        with self.assertRaises(ValueError): runtime.configure_memory_directory(self.state, directory=str(file))
        os.symlink(self.memory, self.temp/'alias')
        with self.assertRaises(ValueError): runtime.configure_memory_directory(self.state, directory=str(self.temp/'alias'))
        self.assertIsNone(configured_memory(self.state))
        self.configure()
        self.assertEqual(configured_memory(self.state), str(self.memory))
        runtime.configure_memory_directory(self.state, directory=None)
        self.assertIsNone(configured_memory(self.state))

    def test_hook_arguments_unchanged_when_configured(self):
        before = runtime._intervention_hooks(self.manifest)
        self.configure()
        after = runtime._intervention_hooks(self.manifest)
        self.assertEqual(before, after)
        self.assertNotIn('--memory-directory', json.dumps(after))


if __name__=='__main__':unittest.main()
