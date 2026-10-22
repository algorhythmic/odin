"""Operator routing CLI retains explicit identities and rejects mixed requests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from odin.__main__ import main
from odin.contracts import identifier
from odin.delegation import load_config


class RoutingCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / 'state'
        self.payload = {
            'action': 'configure_delegation', 'project': identifier(),
            'loop_id': identifier(), 'stage_id': identifier(),
            'session_id': '00000000-0000-4000-8000-000000000001',
            'expected_revision': 30,
            'delegation_profile': {'harness': 'claude-code', 'model': 'opus',
                                   'subagent_model': 'haiku', 'subagent_model_force': True},
        }
        self.request = Path(self.temp.name) / 'request.json'
        self.request.write_text(json.dumps(self.payload))

    def invoke(self, *args):
        with patch('sys.argv', ['odin', '--state', str(self.state), *args]), \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            main()

    def test_transition_passes_exact_request_and_operation_to_service(self):
        operation = identifier()
        with patch('odin.__main__._socket_command', return_value={'result': {}}) as send:
            self.invoke('development-control', '--control', 'configure_delegation',
                        '--request', str(self.request), '--operation-id', operation)
        request = send.call_args.args[1]
        self.assertEqual(request['surface'], 'terminal')
        self.assertEqual(request['command']['operation_id'], operation)
        self.assertEqual(request['command']['action'], 'loop_control')
        self.assertEqual(request['command']['payload'], self.payload)

    def test_mismatched_project_or_wrong_action_never_reaches_service(self):
        with patch('odin.__main__._socket_command') as send:
            with self.assertRaises(SystemExit):
                self.invoke('development-control', '--control', 'configure_delegation',
                            '--request', str(self.request), '--project', identifier())
            self.request.write_text(json.dumps(self.payload | {'action': 'resume'}))
            with self.assertRaises(SystemExit):
                self.invoke('development-control', '--control', 'configure_delegation',
                            '--request', str(self.request))
        send.assert_not_called()

    def test_role_selection_requires_explicit_mode(self):
        with patch('odin.executive_runtime.configure_execution_role', return_value={}) as configure:
            with self.assertRaises(SystemExit):
                self.invoke('executive-configure-execution-role')
            configure.assert_not_called()
            self.invoke('executive-configure-execution-role', '--implementation-mode', 'delegated')
            configure.assert_called_once_with(self.state, implementation_mode='delegated')

    def _configure_delegation(self, *flags):
        config_dir = Path(self.temp.name) / 'synthetic-claude-config'
        config_dir.mkdir(mode=0o700, exist_ok=True)
        workspace = Path(self.temp.name) / 'workspaces'
        workspace.mkdir(exist_ok=True)
        with patch('odin.delegation.shutil.which',
                   side_effect=lambda name: '/bin/true' if name == 'claude' else None):
            self.invoke('delegation-configure', '--claude-config', str(config_dir),
                        '--workspace-root', str(workspace), *flags)

    def test_disallowed_tools_configure_omitted_comma_separated_and_empty(self):
        self._configure_delegation()
        self.assertNotIn('default_disallowed_tools', load_config(self.state)['harnesses']['claude-code'])
        self._configure_delegation('--claude-disallowed-tools', 'Agent,Task,Bash')
        self.assertEqual(load_config(self.state)['harnesses']['claude-code']['default_disallowed_tools'],
                         ['Agent', 'Task', 'Bash'])
        self._configure_delegation('--claude-disallowed-tools', '')
        self.assertEqual(load_config(self.state)['harnesses']['claude-code']['default_disallowed_tools'], [])

    def test_disallowed_tools_configure_rejects_invalid_names_without_writing(self):
        for value in ('Bash(git *)', '-x', 'Agent,Agent', 'Agent, Task', 'Agent,', 'A' * 65,
                      ','.join('Tool' + str(i) for i in range(17))):
            with self.subTest(value=value):
                with self.assertRaises(SystemExit) as raised:
                    self._configure_delegation('--claude-disallowed-tools=' + value)
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse((self.state / 'delegation.json').exists())


if __name__ == '__main__':
    unittest.main()
