"""Synthetic incremental telemetry only; no model calls or home-directory scans."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from odin import executive_runtime as runtime
from odin.contracts import Contracts
from odin.coordination import Actor
from odin.executive_service import prepare_project
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.usage_watch import UsageWatcher, claude_project_dir


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.project = prepare_project(self.state)
        self.service = Service(self.state)
        self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.context = GatewayContext('terminal', Actor('operator', 'synthetic'))
        self.receipts = []
        self.file = self.root / 'native.jsonl'
        self.config = {'schema_version': 1, 'project_id': self.project,
            'cursor_path': str(self.root / 'cursor.sqlite3'), 'max_chunk_bytes': 1024,
            'sources': [{'provider': 'claude', 'session_file': str(self.file),
                         'session_id': 'parent-native', 'agent_id': 'executive',
                         'discover_children': True}]}

    def send(self, _address, envelope):
        command = envelope['command']
        self.receipts.append(command)
        return self.gateway.submit(command, context=self.context)

    def watcher(self, send=None):
        return UsageWatcher(self.config, address='synthetic', send=send or self.send)

    def row(self, message_id, *, session='parent-native', output=2):
        return {'type': 'assistant', 'sessionId': session,
            'message': {'id': message_id, 'model': 'haiku', 'usage':
                {'input_tokens': 3, 'cache_read_input_tokens': 0,
                 'cache_creation_input_tokens': 0, 'output_tokens': output},
                'content': [{'type': 'text', 'text': 'PRIVATE MESSAGE CONTENT'}]}}

    def append(self, path, row, *, newline=True):
        with path.open('a') as stream:
            stream.write(json.dumps(row) + ('\n' if newline else ''))

    def test_partial_line_child_discovery_and_metadata_only(self):
        encoded = json.dumps(self.row('main'))
        self.file.write_text(encoded[:20])
        child_dir = self.root / 'native' / 'subagents'
        child_dir.mkdir(parents=True)
        child = child_dir / 'agent-alpha.jsonl'
        self.append(child, self.row('child', session='child-native'))
        with self.watcher() as watch:
            first = watch.poll()
            self.assertEqual(first['partial'], 1)
            self.assertEqual(first['imported'], 1)
            with self.file.open('a') as stream:
                stream.write(encoded[20:] + '\n')
            watch.poll()
            self.assertEqual(watch.poll()['imported'], 0)
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 2)
        rows = self.service.store.db.execute('SELECT body FROM usage_requests').fetchall()
        observations = [json.loads(row[0]) for row in rows]
        child_item = next(o for o in observations if o['request_id'] == 'child')
        self.assertEqual(child_item['session_id'], 'child-native')
        self.assertIsNone(child_item['loop_id'])
        self.assertIsNone(child_item['stage_id'])
        self.assertIn('parent-native', child_item['source'])
        self.assertIn('child-native', child_item['agent_id'])
        self.assertFalse(summary['coverage_complete'])
        self.assertNotIn(b'PRIVATE MESSAGE CONTENT', Path(self.config['cursor_path']).read_bytes())
        self.assertNotIn(b'PRIVATE MESSAGE CONTENT', self.service.store.path.read_bytes())

    def test_lost_ack_replays_same_batch_after_restart(self):
        self.append(self.file, self.row('once'))
        failed = [False]
        def lost_ack(address, envelope):
            receipt = self.send(address, envelope)
            if not failed[0]:
                failed[0] = True
                raise OSError('synthetic lost reply')
            return receipt
        with self.watcher(lost_ack) as watch:
            with self.assertRaises(OSError):
                watch.poll()
            cursor = watch.db.execute('SELECT offset FROM watch_cursors').fetchone()
            self.assertIsNone(cursor)
            self.assertEqual(watch.db.execute('SELECT COUNT(*) FROM watch_pending').fetchone()[0], 1)
        with self.watcher() as watch:
            watch.poll()
            self.assertEqual(watch.db.execute('SELECT COUNT(*) FROM watch_pending').fetchone()[0], 0)
        self.assertEqual(self.receipts[0]['operation_id'], self.receipts[1]['operation_id'])
        self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 1)

    def test_revisions_survive_append_restart_and_rotation(self):
        self.append(self.file, self.row('revised', output=1))
        with self.watcher() as watch:
            watch.poll()
            self.append(self.file, self.row('revised', output=3))
            watch.poll()
            self.append(self.file, self.row('revised', output=3))
            watch.poll()
        with self.watcher() as watch:
            replacement = self.root / 'replacement.jsonl'
            self.append(replacement, self.row('revised', output=1))
            self.append(replacement, self.row('revised', output=5))
            os.replace(replacement, self.file)
            watch.poll()
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 1)
        self.assertEqual(summary['tokens']['output'], 5)
        body = json.loads(self.service.store.db.execute(
            "SELECT body FROM usage_requests WHERE request_id='revised'").fetchone()[0])
        self.assertEqual(body['revision'], 2)

    def test_mixed_regression_is_quarantined_without_stalling_next_row(self):
        self.append(self.file, self.row('mixed', output=3))
        with self.watcher() as watch:
            watch.poll()
            mixed = self.row('mixed', output=2)
            mixed['message']['usage']['input_tokens'] = 4
            self.append(self.file, mixed)
            self.append(self.file, self.row('following'))
            watch.poll()
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 2)
        self.assertEqual(summary['coverage'][0]['malformed_lines'], 1)
        body = json.loads(self.service.store.db.execute(
            "SELECT body FROM usage_requests WHERE request_id='mixed'").fetchone()[0])
        self.assertEqual(body['tokens']['output'], 3)

    def test_directory_inspection_is_bounded_and_other_sources_continue(self):
        directory = self.root / 'crowded'
        directory.mkdir()
        for index in range(4):
            (directory / f'{index}.txt').write_text('unused')
        self.config['max_files'] = 3
        self.config['sources'].insert(0, {'provider': 'claude', 'sessions_dir': str(directory),
                                          'discover_sessions': True})
        self.append(self.file, self.row('survives'))
        with self.watcher() as watch:
            result = watch.poll()
        self.assertEqual(result['unavailable'], 1)
        self.assertEqual(result['imported'], 1)
        self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 1)

    def test_cursor_and_lock_must_remain_private(self):
        cursor = Path(self.config['cursor_path'])
        cursor.write_text('')
        cursor.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.watcher()
        cursor.chmod(0o600)
        lock = Path(str(cursor) + '.lock')
        lock.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.watcher()

    def test_rotation_and_large_incremental_source(self):
        # Nine oversized, content-only rows exceed the old 8 MiB scan bound.
        padding = 'x' * 1100
        with self.file.open('w') as stream:
            for _ in range(8200):
                stream.write(json.dumps({'type': 'noop', 'padding': padding}) + '\n')
            stream.write(json.dumps(self.row('after-large')) + '\n')
        self.assertGreater(self.file.stat().st_size, 8 * 1024 * 1024)
        self.config['max_chunk_bytes'] = 65536
        with self.watcher() as watch:
            for _ in range(200):
                watch.poll()
                if self.gateway.usage.summary(project_id=self.project)['request_count'] == 1:
                    break
            else:
                self.fail('watcher did not progress beyond 8 MiB')
            replacement = self.root / 'replacement.jsonl'
            self.append(replacement, self.row('after-rotate'))
            os.replace(replacement, self.file)
            watch.poll()
        self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 2)
        coverage = self.gateway.usage.summary(project_id=self.project)['coverage']
        self.assertTrue(any(item['truncated'] for item in coverage))
        self.assertFalse(any(item['complete'] for item in coverage))

    def test_same_inode_rewrite_and_regrow_restarts_at_prefix(self):
        self.append(self.file, self.row('old-message'))
        with self.watcher() as watch:
            watch.poll()
            inode = self.file.stat().st_ino
            # Rewrite in place and grow beyond the prior cursor in one step.
            with self.file.open('w') as stream:
                stream.write(json.dumps(self.row('new-message')) + '\n')
                stream.write(json.dumps(self.row('next-message')) + '\n')
            self.assertEqual(self.file.stat().st_ino, inode)
            self.assertEqual(watch.poll()['imported'], 1)
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 3)
        self.assertTrue(summary['coverage'][0]['truncated'])

    def test_oversized_line_skipped_then_next_request_imported(self):
        self.config['max_chunk_bytes'] = 1024
        self.file.write_text(json.dumps({'type': 'noop', 'padding': 'x' * 2500}) + '\n')
        self.append(self.file, self.row('after-oversize'))
        with self.watcher() as watch:
            for _ in range(6):
                watch.poll()
                if self.gateway.usage.summary(project_id=self.project)['request_count']:
                    break
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 1)
        self.assertGreater(summary['coverage'][0]['malformed_lines'], 0)

    def test_explicit_directory_discovers_future_session(self):
        directory = self.root / 'sessions'
        directory.mkdir()
        self.config['sources'] = [{'provider': 'claude', 'sessions_dir': str(directory),
                                   'discover_sessions': True, 'discover_children': True}]
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['imported'], 0)
            session = directory / 'new-native-session.jsonl'
            self.append(session, self.row('future', session='new-native-session'))
            self.assertEqual(watch.poll()['imported'], 1)
        self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 1)

    def test_evaluator_spool_discovers_jobs_and_keeps_native_thread_across_polls(self):
        spool = self.root / 'development-evaluator'
        spool.mkdir()
        self.config['sources'] = [{'provider': 'codex', 'spool_dir': str(spool),
            'discover_jobs': True, 'usage_semantics': 'session_cumulative'}]
        first = spool / 'job-one'
        first.mkdir()
        log = first / 'stdout.log'
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['unavailable'], 1)
            self.append(log, {'type': 'turn.completed', 'usage': {'input_tokens': 2, 'output_tokens': 1}})
            watch.poll()
            self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 0)
            self.append(log, {'type': 'thread.started', 'thread_id': 'native-codex-one', 'model': 'codex-model'})
            watch.poll()
            self.append(log, {'type': 'turn.started'})
            watch.poll()
            self.append(log, {'type': 'turn.completed', 'usage': {
                'input_tokens': 10, 'cached_input_tokens': 4, 'output_tokens': 3}})
            watch.poll()
        second = spool / 'job-two'
        second.mkdir()
        other = second / 'stdout.log'
        self.append(other, {'type': 'thread.started', 'thread_id': 'native-codex-two'})
        self.append(other, {'type': 'turn.started'})
        self.append(other, {'type': 'turn.completed', 'usage': {
            'input_tokens': 5, 'cached_input_tokens': 2, 'output_tokens': 1}})
        with self.watcher() as watch:
            watch.poll()
        rows = [json.loads(row[0]) for row in self.service.store.db.execute(
            'SELECT body FROM usage_requests ORDER BY session_id')]
        self.assertEqual([row['session_id'] for row in rows],
                         ['native-codex-one', 'native-codex-two'])
        self.assertEqual(rows[0]['model'], 'codex-model')
        self.assertEqual(rows[0]['tokens']['uncached_input'], 6)
        self.assertEqual(rows[0]['tokens']['cache_read'], 4)
        self.assertEqual(rows[0]['scope'], 'cumulative')
        self.assertNotIn('job-one', [row['session_id'] for row in rows])
        coverage = self.gateway.usage.summary(project_id=self.project)['coverage']
        self.assertTrue(any(item['unidentified_usage'] for item in coverage))

    def test_status_file_uses_sample_mtime_and_does_not_count_request(self):
        status = self.root / 'status.json'
        status.write_text(json.dumps({'session_id': 'parent-native',
            'context_window': {'context_window_size': 200000,
            'current_usage': {'input_tokens': 4, 'cache_read_input_tokens': 2,
                              'cache_creation_input_tokens': 1}},
            'rate_limits': {'five_hour': {'used_percentage': 80}}}))
        os.utime(status, (1577836800, 1577836800))
        self.config['sources'] = []
        self.config['status_files'] = [{'path': str(status), 'session_id': 'parent-native',
            'agent_id': 'executive', 'account_id': 'account-a'}]
        with self.watcher() as watch:
            watch.poll()
            self.assertEqual(watch.poll()['imported'], 0)
        summary = self.gateway.usage.summary(project_id=self.project)
        self.assertEqual(summary['request_count'], 0)
        self.assertEqual(summary['latest_quota']['observed_at'], '2020-01-01T00:00:00Z')
        self.assertEqual(summary['latest_context']['context_input_tokens'], 7)

    def test_status_file_with_different_native_session_is_rejected(self):
        status = self.root / 'status.json'
        status.write_text(json.dumps({'session_id': 'other-native',
            'context_window': {'context_window_size': 100}}))
        self.config['sources'] = []
        self.config['status_files'] = [{'path': str(status), 'session_id': 'parent-native',
            'agent_id': 'executive', 'account_id': 'account-a'}]
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['invalid'], 1)
        self.assertIsNone(self.gateway.usage.summary(project_id=self.project)['latest_quota'])

    def test_status_file_bound_to_executive_state_follows_rotation(self):
        executive = self.root / 'executive'
        runtime.prepare(executive, config_dir=self.root / 'login', project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)
        status = self.root / 'status.json'

        def write(session, percent):
            status.write_text(json.dumps({'session_id': session,
                'rate_limits': {'seven_day': {'used_percentage': percent}}}))

        self.config['sources'] = []
        self.config['status_files'] = [{'path': str(status), 'executive_state': str(executive),
            'agent_id': 'executive', 'account_id': 'account-a'}]
        first = runtime.current_session_id(executive)
        with self.watcher() as watch:
            write(first, 40)
            self.assertEqual(watch.poll()['imported'], 1)
            rotated = runtime.new_session(executive)['native_session_id']
            write(first, 41)
            self.assertEqual(watch.poll()['invalid'], 1)
            write(rotated, 42)
            self.assertEqual(watch.poll()['imported'], 1)
        quota = self.gateway.usage.summary(project_id=self.project)['latest_quota']
        self.assertEqual(quota['session_id'], rotated)
        self.assertEqual(quota['rate_limits']['seven_day']['used_percentage'], 42)
        self.config['status_files'][0]['executive_state'] = str(self.root / 'missing')
        self.config['cursor_path'] = str(self.root / 'other-cursor.sqlite3')
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['unavailable'], 1)

    def test_source_bound_to_executive_state_follows_rotation(self):
        executive = self.root / 'executive'
        runtime.prepare(executive, config_dir=self.root / 'login', project=self.project,
                        claude_binary=sys.executable, python_executable=sys.executable)
        self.config['sources'] = [{'provider': 'claude', 'executive_state': str(executive),
            'agent_id': 'executive', 'discover_children': True}]
        first, transcript = runtime.current_transcript(executive)
        children = transcript.with_suffix('') / 'subagents'
        children.mkdir(parents=True)
        self.append(children / 'agent-beta.jsonl', self.row('child', session='child-native'))
        self.append(transcript, self.row('main', session=first))
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['imported'], 2)
            rotated = runtime.new_session(executive)['native_session_id']
            self.assertEqual(runtime.current_transcript(executive)[0], rotated)
            rotated_transcript = runtime.current_transcript(executive)[1]
            self.append(rotated_transcript, self.row('rotated-main', session=rotated))
            # The rotated-out file is no longer resolved, so growth there is not read.
            self.append(transcript, self.row('stale', session=first))
            self.assertEqual(watch.poll()['imported'], 1)
        rows = [json.loads(row[0]) for row in self.service.store.db.execute(
            'SELECT body FROM usage_requests')]
        bodies = {row['request_id']: row for row in rows}
        self.assertEqual(bodies['main']['session_id'], first)
        self.assertEqual(bodies['rotated-main']['session_id'], rotated)
        self.assertIn('child-native', bodies['child']['agent_id'])
        self.assertNotIn('stale', bodies)

    def test_source_bound_to_missing_executive_state_is_unavailable(self):
        self.config['sources'] = [{'provider': 'claude',
            'executive_state': str(self.root / 'missing'), 'agent_id': 'executive'}]
        with self.watcher() as watch:
            self.assertEqual(watch.poll()['unavailable'], 1)
        self.assertEqual(self.gateway.usage.summary(project_id=self.project)['request_count'], 0)

    def test_claude_project_dir_encodes_every_non_alnum_as_dash(self):
        directory = claude_project_dir(
            '/config', '/home/david/.local/state/x/workspaces/odin-worker-claude')
        self.assertEqual(directory, Path('/config/projects'
            '/-home-david--local-state-x-workspaces-odin-worker-claude'))
        self.assertEqual(claude_project_dir('/config', '/a.b/c_d').name, '-a-b-c-d')
        with self.assertRaises(ValueError):
            claude_project_dir('/config', '/' + 'x' * 300)

    def test_executive_state_source_shape_is_schema_checked(self):
        source = {'provider': 'claude', 'executive_state': str(self.root / 'executive'),
                  'agent_id': 'executive'}
        config = dict(self.config, sources=[source])
        Contracts().validate('usage-watch-config', config)
        for extra in ({'session_id': 'native'}, {'session_file': str(self.file)},
                      {'sessions_dir': str(self.root)}, {'spool_dir': str(self.root)},
                      {'provider': 'codex'}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                Contracts().validate('usage-watch-config', dict(config, sources=[source | extra]))

    def test_workspaces_root_discovers_new_workspaces_each_poll(self):
        workspaces = self.root / 'workspaces'
        workspaces.mkdir()
        (workspaces / 'no-transcripts-yet').mkdir()
        (workspaces / ('w' * 200)).mkdir()  # encoded project name exceeds 200 chars
        config_dir = self.root / 'claude-config'
        self.config['sources'] = [{'provider': 'claude',
            'workspaces_root': str(workspaces), 'claude_config_dir': str(config_dir),
            'discover_sessions': True, 'discover_children': True}]
        alpha = workspaces / 'alpha-workspace'
        alpha.mkdir()
        project = claude_project_dir(config_dir, alpha)
        project.mkdir(parents=True)
        row = self.row('one')
        del row['sessionId']  # the session ID falls back to the transcript stem
        self.append(project / 'session-one.jsonl', row)
        with self.watcher() as watch:
            first = watch.poll()
            self.assertEqual(first['imported'], 1)
            self.assertEqual(first['unavailable'], 0)
            beta = workspaces / 'beta-workspace'
            beta.mkdir()
            other = claude_project_dir(config_dir, beta)
            other.mkdir(parents=True)
            self.append(other / 'session-two.jsonl',
                        self.row('two', session='session-two'))
            self.assertEqual(watch.poll()['imported'], 1)
        rows = [json.loads(item[0]) for item in self.service.store.db.execute(
            'SELECT body FROM usage_requests ORDER BY agent_id')]
        self.assertEqual([item['agent_id'] for item in rows],
                         ['workstream:alpha-workspace', 'workstream:beta-workspace'])
        self.assertEqual([item['session_id'] for item in rows],
                         ['session-one', 'session-two'])

    def test_workspaces_source_shape_is_schema_checked(self):
        source = {'provider': 'claude', 'workspaces_root': str(self.root / 'workspaces'),
                  'claude_config_dir': str(self.root / 'claude-config'),
                  'discover_sessions': True}
        config = dict(self.config, sources=[source])
        Contracts().validate('usage-watch-config', config)
        for extra in ({'session_id': 'native'}, {'session_file': str(self.file)},
                      {'sessions_dir': str(self.root)}, {'spool_dir': str(self.root)},
                      {'executive_state': str(self.root / 'executive')},
                      {'loop_id': 'loop'}, {'stage_id': 'stage'},
                      {'provider': 'codex'}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                Contracts().validate('usage-watch-config', dict(config, sources=[source | extra]))
        mixed = {'provider': 'claude', 'session_file': str(self.file),
                 'session_id': 'native', 'agent_id': 'executive',
                 'workspaces_root': str(self.root)}
        with self.assertRaises(ValidationError):
            Contracts().validate('usage-watch-config', dict(config, sources=[mixed]))

    def test_limit_probes_import_label_keyed_samples_through_the_gateway(self):
        secret = 'SYNTHETIC-WATCH-TOKEN-51c2'
        login = self.root / 'claude-login'
        login.mkdir(mode=0o700)
        (login / '.credentials.json').write_text(json.dumps({'claudeAiOauth': {'accessToken': secret}}))
        recorded = {'five_hour': {'utilization': 91.5, 'resets_at': '2026-10-21T12:00:00Z'},
                    'seven_day': {'utilization': 40.0, 'resets_at': '2026-10-25T00:00:00Z'}}

        def transport(url, headers, timeout):
            return 200, json.dumps(recorded).encode()

        self.config['sources'] = []
        self.config['limit_probes'] = {'claude_config_dir': str(login),
                                       'codex_home': str(self.root / 'absent-codex-home')}
        with UsageWatcher(self.config, address='synthetic', send=self.send,
                          limit_transport=transport) as watch:
            # Claude limits plus an unavailable Codex probe (CODEX_HOME has no sessions).
            self.assertEqual(watch.poll()['limit_samples'], 3)
            self.assertEqual(watch.poll()['limit_samples'], 0)  # interval not yet elapsed
        snapshots = self.gateway.usage.summary(project_id=self.project)['limit_snapshots']
        observed = {(s['label'], s['status'], s['utilization_percent']) for s in snapshots}
        self.assertEqual(observed, {('claude.five_hour', 'available', 91.5),
                                    ('claude.weekly', 'available', 40.0),
                                    ('codex.probe', 'unavailable', None)})
        self.assertNotIn(secret, json.dumps(self.receipts))
        self.assertNotIn(secret, json.dumps(snapshots))

    def test_each_limit_probe_runs_only_when_configured(self):
        def transport(url, headers, timeout):
            raise AssertionError('the Claude probe is not configured')

        self.config['sources'] = []
        self.config['limit_probes'] = {'codex_home': str(self.root / 'absent-codex-home')}
        with UsageWatcher(self.config, address='synthetic', send=self.send,
                          limit_transport=transport) as watch:
            self.assertEqual(watch.poll()['limit_samples'], 1)
        snapshots = self.gateway.usage.summary(project_id=self.project)['limit_snapshots']
        self.assertEqual([s['label'] for s in snapshots], ['codex.probe'])


if __name__ == '__main__':
    unittest.main()
