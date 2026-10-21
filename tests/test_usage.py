"""Synthetic usage only; no native transcripts, credentials or model calls."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.store import Conflict, Store
from odin.usage import (UsageLedger, _tokens, normalize_claude_status, request,
                        usage_from_claude_jsonl, usage_from_codex_jsonl)


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.ledger = UsageLedger(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_duplicate_blocks_replay_and_partial_revision(self):
        path = Path(self.temp.name) / 'claude.jsonl'
        def row(output):
            return {'type': 'assistant', 'sessionId': 's', 'agentId': 'a',
                    'message': {'id': 'm1', 'model': 'haiku',
                                'content': [{'type': 'text', 'text': 'not persisted'}],
                                'usage': {'input_tokens': 3, 'output_tokens': output}}}
        path.write_text('\n'.join(json.dumps(x) for x in (row(1), row(1), row(2))) + '\n')
        result = usage_from_claude_jsonl(path, project_id='p', session_id='s')
        self.assertEqual([x['revision'] for x in result['observations']], [0, 0, 1])
        for item in result['observations']:
            self.ledger.ingest(item)
        for item in result['observations']:
            self.ledger.ingest(item)
        summary = self.ledger.summary(project_id='p')
        self.assertEqual(summary['request_count'], 1)
        self.assertEqual(summary['tokens']['output'], 2)
        newer = usage_from_claude_jsonl([row(3)], project_id='p', session_id='s')
        self.assertEqual(newer['observations'][0]['revision'], 0)
        self.assertEqual(self.ledger.ingest(newer['observations'][0]), 'revised')
        self.assertEqual(self.ledger.summary(project_id='p')['tokens']['output'], 3)
        self.assertNotIn('not persisted', self.store.path.read_bytes().decode('utf8', errors='ignore'))

    def test_missing_fields_sessions_and_conflicts(self):
        a = request(provider='claude', project_id='p', source='fixture', session_id='parent',
                    agent_id='worker', request_id='same', model='haiku',
                    tokens=_tokens(4, None, None, None))
        b = {**a, 'session_id': 'child', 'tokens': _tokens(8, None, None, 2)}
        self.ledger.ingest(a)
        self.ledger.ingest(b)
        summary = self.ledger.summary(project_id='p')
        self.assertEqual(summary['request_count'], 2)
        self.assertEqual(summary['missing_requests']['cache_read'], 2)
        self.assertIsNone(summary['cache_inclusive_input_tokens'])
        with self.assertRaises(Conflict):
            self.ledger.ingest({**a, 'model': 'opus'})
        with self.assertRaises((Conflict, ValueError)):
            self.ledger.ingest({**a, 'revision': 1, 'tokens': _tokens(3)})
        self.assertEqual(self.ledger.summary(project_id='elsewhere')['request_count'], 0)

    def test_aggregate_is_excluded(self):
        args = dict(provider='claude', project_id='p', source='fixture', session_id='s',
                    agent_id='a', model='haiku')
        self.ledger.ingest(request(**args, request_id='child', tokens=_tokens(5, 1, 2, 3)))
        self.ledger.ingest(request(**args, request_id='parent', scope='aggregate', tokens=_tokens(100, 0, 0, 100)))
        summary = self.ledger.summary(project_id='p')
        self.assertEqual(summary['tokens']['uncached_input'], 5)
        self.assertEqual(summary['aggregate_excluded'], 1)
        self.assertEqual(summary['cache_inclusive_input_tokens'], 8)
        self.ledger.record_coverage('fixture', {'truncated': False, 'malformed_lines': 0,
                                                'complete': True}, project_id='p')
        self.assertFalse(self.ledger.summary(project_id='p')['coverage_complete'])
        parsed = usage_from_claude_jsonl([
            {'type': 'result', 'request_id': 'summary',
             'usage': {'input_tokens': 100, 'output_tokens': 100}}],
            project_id='p', session_id='s')
        self.assertFalse(parsed['coverage']['complete'])
        self.assertEqual(parsed['coverage']['aggregate_usage'], 1)

    def test_codex_inclusive_cache_normalization(self):
        source = [
            {'type': 'thread.started', 'thread_id': 't'},
            {'type': 'turn.started'},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 4, 'output_tokens': 2}},
        ]
        path = Path(self.temp.name) / 'codex.jsonl'
        path.write_text('\n'.join(json.dumps(x) for x in source) + '\n')
        result = usage_from_codex_jsonl(path, project_id='p', session_id='fallback', model='codex')
        item = result['observations'][0]
        self.assertEqual(item['session_id'], 't')
        self.assertEqual(item['tokens'], _tokens(6, 4, 0, 2))
        self.assertEqual(item['context_input_tokens'], 10)
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(result['coverage']['unidentified_usage'], 1)

    def test_codex_cumulative_session_totals_replace_instead_of_double_count(self):
        source = [
            {'type': 'turn.started'},
            {'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 4, 'output_tokens': 2}},
            {'type': 'turn.started'},
            {'type': 'turn.completed', 'usage': {'input_tokens': 18, 'cached_input_tokens': 7, 'output_tokens': 5}},
        ]
        parsed = usage_from_codex_jsonl(source, project_id='p', session_id='s',
                                        usage_semantics='session_cumulative')
        self.assertEqual([x['request_id'] for x in parsed['observations']],
                         ['session-total', 'session-total'])
        self.assertEqual([x['revision'] for x in parsed['observations']], [0, 1])
        for item in parsed['observations']:
            self.ledger.ingest(item)
        resumed = usage_from_codex_jsonl([
            {'type': 'turn.started'},
            {'type': 'turn.completed', 'usage': {'input_tokens': 25,
                'cached_input_tokens': 10, 'output_tokens': 8}}],
            project_id='p', session_id='s', usage_semantics='session_cumulative')
        self.assertEqual(self.ledger.ingest(resumed['observations'][0]), 'revised')
        self.assertEqual(self.ledger.summary(project_id='p')['tokens']['uncached_input'], 15)
        self.assertEqual(self.ledger.summary(project_id='p')['tokens']['output'], 8)
        self.assertEqual(self.ledger.summary(project_id='p')['cumulative_sessions'], 1)
        self.assertFalse(self.ledger.summary(project_id='p')['coverage_complete'])

    def test_cumulative_snapshot_cannot_hide_larger_known_atomic_usage(self):
        args = dict(provider='codex', project_id='p', source='fixture', session_id='s',
                    agent_id='executive', model='codex')
        for index in range(2):
            self.ledger.ingest(request(**args, request_id=f'turn-{index}',
                tokens=_tokens(6, 1, 0, 3)))
        self.ledger.ingest(request(**args, request_id='session-total', scope='cumulative',
            tokens=_tokens(5, 1, 0, 2)))
        summary = self.ledger.summary(project_id='p')
        self.assertEqual(summary['tokens']['uncached_input'], 12)
        self.assertEqual(summary['tokens']['cache_read'], 2)
        self.assertEqual(summary['tokens']['output'], 6)
        self.assertEqual(summary['request_count'], 2)
        self.assertEqual(summary['shadowed_atomic'], 2)

    def test_quota_null_and_stale_sample_retained(self):
        q = normalize_claude_status({'context_window': {'context_window_size': 200000},
                'rate_limits': {'five_hour': {'used_percentage': 50}, 'seven_day': None}},
                project_id='p', session_id='s', observed_at='2020-01-01T00:00:00Z')
        self.assertEqual(self.ledger.ingest(q), 'inserted')
        self.assertEqual(self.ledger.ingest(q), 'duplicate')
        latest = self.ledger.summary(project_id='p')['latest_quota']
        self.assertIsNone(latest['rate_limits']['seven_day']['used_percentage'])
        self.assertEqual(latest['observed_at'], '2020-01-01T00:00:00Z')
        self.assertTrue(self.ledger.summary(project_id='p', as_of='2020-01-01T01:00:00Z')['quota_stale'])
        self.assertFalse(self.ledger.summary(project_id='p', as_of='2020-01-01T00:01:00Z')['quota_stale'])
        offset = normalize_claude_status({}, project_id='p', session_id='s',
            observed_at='2020-01-01T02:00:00+02:00')
        self.assertEqual(offset['observed_at'], '2020-01-01T00:00:00Z')
        self.assertTrue(self.ledger.summary(project_id='p', as_of='2019-12-31T23:59:59Z')['quota_stale'])

    def test_invalid_counters_and_parsed_rows(self):
        with self.assertRaises(ValueError):
            _tokens(True, None, None, None)
        with self.assertRaises(ValueError):
            _tokens(1.5, None, None, None)
        result = usage_from_codex_jsonl([
            {"type": "turn.started"},
            {"type": "turn.completed", "usage": {"input_tokens": 7, "cached_input_tokens": 3, "output_tokens": 2}},
        ], project_id="p", session_id="s")
        self.assertEqual(result["observations"][0]["tokens"]["uncached_input"], 4)
        with self.assertRaises(ValueError):
            request(provider='claude', project_id='p', source='fixture',
                    session_id='s', agent_id='a', request_id='bad-time',
                    tokens=_tokens(1, 0, 0, 0), observed_at='not-a-time')

    def test_nonregular_file_rejected_without_blocking(self):
        fifo = Path(self.temp.name) / 'fifo'
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            usage_from_claude_jsonl(fifo, project_id='p', session_id='s')

    def test_file_bounds_and_malformed_coverage(self):
        path = Path(self.temp.name) / 'partial.jsonl'
        path.write_text('bad json\n' + json.dumps({'type': 'assistant', 'message': {'usage': {'input_tokens': 1}}}) + '\n' + 'x' * 100)
        result = usage_from_claude_jsonl(path, project_id='p', session_id='s', max_bytes=120)
        self.assertTrue(result['coverage']['truncated'])
        self.assertGreaterEqual(result['coverage']['malformed_lines'], 1)
        self.assertFalse(result['coverage']['complete'])
        with self.assertRaises(ValueError):
            usage_from_claude_jsonl(path, project_id='p', session_id='s', max_bytes=0)
        with self.assertRaises(ValueError):
            usage_from_claude_jsonl([{'padding': 'x' * 200}],
                                    project_id='p', session_id='s', max_bytes=100)
        self.ledger.record_coverage('file-1', result['coverage'], project_id='p')
        self.assertFalse(self.ledger.summary(project_id='p')['coverage_complete'])

    def test_changed_or_short_read_file_has_incomplete_coverage(self):
        path = Path(self.temp.name) / 'changing.jsonl'
        path.write_text(json.dumps({'type': 'irrelevant'}) + '\n')
        original_read = os.read
        with patch('odin.usage.os.read', side_effect=lambda fd, count: original_read(fd, 1)):
            short = usage_from_claude_jsonl(path, project_id='p', session_id='s')
        self.assertFalse(short['coverage']['complete'])
        def growing_read(fd, count):
            data = original_read(fd, count)
            with path.open('a') as output:
                output.write(json.dumps({'type': 'later'}) + '\n')
            return data
        with patch('odin.usage.os.read', side_effect=growing_read):
            growing = usage_from_claude_jsonl(path, project_id='p', session_id='s')
        self.assertFalse(growing['coverage']['complete'])
        def replaced_read(fd, count):
            data = original_read(fd, count)
            path.rename(path.with_suffix('.old'))
            path.write_text(json.dumps({'type': 'replacement'}) + '\n')
            return data
        with patch('odin.usage.os.read', side_effect=replaced_read):
            replaced = usage_from_claude_jsonl(path, project_id='p', session_id='s')
        self.assertFalse(replaced['coverage']['complete'])


if __name__ == '__main__':
    unittest.main()
