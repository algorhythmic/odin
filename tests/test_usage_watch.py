"""Synthetic incremental telemetry only; no model calls or home-directory scans."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from odin.coordination import Actor
from odin.executive_service import prepare_project
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.usage_watch import UsageWatcher


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
        self.assertEqual(child_item['session_id'], 'parent-native')
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

    def test_status_file_uses_sample_mtime_and_does_not_count_request(self):
        status = self.root / 'status.json'
        status.write_text(json.dumps({'context_window': {'context_window_size': 200000,
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


if __name__ == '__main__':
    unittest.main()
