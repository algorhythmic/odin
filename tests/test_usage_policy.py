import tempfile
import unittest
from pathlib import Path

from odin.store import Conflict, Store, now
from odin.contracts import identifier
from odin.usage import UsageLedger, _tokens, request, normalize_claude_status
from odin.usage_policy import UsagePolicy, ContinuityCheckpoints


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.project = identifier()
        stamp = now()
        self.store.create({'schema_version': 1, 'record_type': 'Project', 'id': self.project,
            'rev': 1, 'created_at': stamp, 'updated_at': stamp, 'name': 'synthetic',
            'sources': [], 'delegations': [], 'interface_decision_owner': None})
        self.policy = UsagePolicy(self.store)
        self.checkpoints = ContinuityCheckpoints(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_default_observe_and_idempotent_decision(self):
        self.assertEqual(self.policy.get(self.project)['mode'], 'observe')
        a = self.policy.evaluate(self.project, operation_id='admit-1', purpose='worker')
        self.assertEqual(a['decision'], 'allow')
        self.assertEqual(a, self.policy.evaluate(self.project, operation_id='admit-1', purpose='worker'))
        with self.assertRaises(Conflict):
            self.policy.evaluate(self.project, operation_id='admit-1', purpose='other')

    def test_unconfigured_idle_check_is_ephemeral(self):
        before = self.store.db.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        decision = self.policy.check(self.project, purpose='idle', session_id='native')
        self.assertEqual(decision['decision'], 'allow')
        self.assertFalse(decision['configured'])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM history").fetchone()[0], before)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM usage_policy_operations").fetchone()[0], 0)

    def test_check_identity_is_stable_when_sqlite_reverses_unordered_rows(self):
        self.policy.configure(self.project, {'mode': 'observe'}, 'cfg-order')
        for account in ('acct-b', 'acct-a'):
            self.policy.usage.ingest(normalize_claude_status({},
                project_id=self.project, session_id='native', account_id=account,
                observed_at='2026-10-20T00:00:00Z'))
        for source in ('source-b', 'source-a'):
            self.policy.usage.record_coverage(source,
                {'truncated': False, 'malformed_lines': 0, 'complete': True},
                project_id=self.project)
        first = self.policy.check(self.project, purpose='idle',
                                  now='2026-10-20T00:00:10Z')
        self.store.db.execute('PRAGMA reverse_unordered_selects=ON')
        second = self.policy.check(self.project, purpose='idle',
                                   now='2026-10-20T00:00:10Z')
        self.assertEqual(first, second)

    def test_threshold_and_missing_telemetry(self):
        policy = {'mode': 'hold', 'missing_telemetry': 'hold', 'account_id': 'acct-1',
                  'limits': {'max_requests': 1, 'max_five_hour_used_percentage': 80}}
        self.assertEqual(self.policy.configure(self.project, policy, 'config-1'), self.policy.get(self.project))
        decision = self.policy.evaluate(self.project, operation_id='admit-2', purpose='worker')
        self.assertEqual(decision['decision'], 'hold')
        self.assertIn('request_coverage:incomplete', decision['reasons'])
        self.assertIn('five_hour:stale_sample', decision['reasons'])
        with self.assertRaises(Conflict):
            self.policy.configure(self.project, {'mode': 'observe'}, 'config-1')
        # Explicit observed request and quota do not become hard native limits.
        self.policy.usage.ingest(request(provider='claude', project_id=self.project, source='synthetic',
            session_id='s', agent_id='a', request_id='r', model='haiku', tokens=_tokens(4, 0, 0, 2)))
        self.policy.usage.record_coverage('synthetic', {'truncated': False, 'malformed_lines': 0, 'complete': True}, project_id=self.project)
        self.policy.usage.ingest(normalize_claude_status({'rate_limits': {'five_hour': {'used_percentage': 90}}},
            project_id=self.project, session_id='s', account_id='acct-1', observed_at='2026-10-20T00:00:00Z'))
        decision = self.policy.evaluate(self.project, operation_id='admit-3', purpose='worker', now='2026-10-20T00:00:10Z')
        self.assertIn('requests:threshold', decision['reasons'])
        self.assertIn('five_hour:threshold', decision['reasons'])
        self.assertEqual(decision['decision'], 'hold')

    def test_check_recomputes_after_telemetry_and_rejects_other_account(self):
        self.policy.configure(self.project, {'mode': 'hold', 'missing_telemetry': 'hold',
            'account_id': 'target', 'limits': {'max_five_hour_used_percentage': 80}}, 'cfg-account')
        stamp = '2026-10-20T00:00:10Z'
        first = self.policy.check(self.project, purpose='worker', now=stamp)
        self.assertEqual(first, self.policy.check(self.project, purpose='worker', now=stamp))
        self.policy.usage.ingest(normalize_claude_status({'rate_limits': {'five_hour': {'used_percentage': 10}}},
            project_id=self.project, session_id='s', account_id='other', observed_at='2026-10-20T00:00:09Z'))
        second = self.policy.check(self.project, purpose='worker', now=stamp)
        self.assertEqual(second['decision'], 'hold')
        self.assertNotEqual(second['operation_id'], first['operation_id'])
        self.policy.usage.ingest(normalize_claude_status({'rate_limits': {'five_hour': {'used_percentage': 10}}},
            project_id=self.project, session_id='s', account_id='target', observed_at='2026-10-20T00:00:11Z'))
        future = self.policy.check(self.project, purpose='worker', now=stamp)
        self.assertEqual(future['decision'], 'hold')
        self.assertIn('five_hour:stale_sample', future['reasons'])
        self.policy.usage.ingest(normalize_claude_status({'rate_limits': {'five_hour': {'used_percentage': 10}}},
            project_id=self.project, session_id='s', account_id='target', observed_at='2026-10-20T00:00:12Z'))
        settled = self.policy.check(self.project, purpose='worker', now='2026-10-20T00:00:13Z')
        self.assertEqual(settled['decision'], 'allow')

    def test_check_recomputes_at_configured_freshness_boundaries(self):
        self.policy.configure(self.project, {'mode': 'hold', 'missing_telemetry': 'hold',
            'account_id': 'acct', 'limits': {'max_sample_age_seconds': 5,
                'max_five_hour_used_percentage': 80, 'max_context_tokens': 100}}, 'cfg-freshness')
        def sample(observed_at):
            self.policy.usage.ingest(normalize_claude_status({
                'rate_limits': {'five_hour': {'used_percentage': 10}},
                'context_window': {'current_usage': {'input_tokens': 10,
                    'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}},
                project_id=self.project, session_id='native', account_id='acct',
                observed_at=observed_at))
        sample('2026-10-20T00:00:00Z')
        fresh = self.policy.check(self.project, purpose='worker', session_id='native',
                                  now='2026-10-20T00:00:05Z')
        self.assertEqual(fresh['decision'], 'allow')
        self.assertEqual(fresh, self.policy.check(self.project, purpose='worker',
            session_id='native', now='2026-10-20T00:00:05Z'))
        expired = self.policy.check(self.project, purpose='worker', session_id='native',
                                    now='2026-10-20T00:00:06Z')
        self.assertEqual(expired['decision'], 'hold')
        self.assertNotEqual(fresh['operation_id'], expired['operation_id'])
        self.assertIn('five_hour:stale_sample', expired['reasons'])
        self.assertIn('context_tokens:stale_sample', expired['reasons'])
        sample('2026-10-20T00:00:12Z')
        future = self.policy.check(self.project, purpose='worker', session_id='native',
                                   now='2026-10-20T00:00:10Z')
        self.assertEqual(future['decision'], 'hold')
        present = self.policy.check(self.project, purpose='worker', session_id='native',
                                    now='2026-10-20T00:00:12Z')
        self.assertEqual(present['decision'], 'allow')
        self.assertNotEqual(future['operation_id'], present['operation_id'])

    def test_observe_mode_records_reasons_without_hold(self):
        self.policy.configure(self.project, {'mode': 'observe', 'limits': {'max_input_tokens': 1}}, 'cfg')
        result = self.policy.evaluate(self.project, operation_id='admit', purpose='stage')
        self.assertEqual(result['decision'], 'allow')
        self.assertIn('input_tokens:missing', result['reasons'])

    def test_checkpoint_revisions_bounds_and_isolation(self):
        payload = {'session_id': 'native-1', 'revision': 1, 'branch': 'codex/test',
                   'worktree': '/tmp/synthetic', 'artifact_refs': [{'ref': 'a.txt', 'sha256': '0' * 64}],
                   'open_obligations': ['finish tests'], 'pending_reviews': [],
                   'operation_ids': ['op-1'], 'next_action': 'run tests', 'summary': 'attributed note'}
        first = self.checkpoints.checkpoint(self.project, payload, 'cp-1')
        self.assertEqual(first, self.checkpoints.checkpoint(self.project, payload, 'cp-1'))
        self.assertEqual(self.checkpoints.latest_checkpoint(self.project, 'native-1'), first)
        with self.assertRaises(Conflict):
            self.checkpoints.checkpoint(self.project, {**payload, 'summary': 'changed'}, 'cp-1')
        with self.assertRaises(Conflict):
            self.checkpoints.checkpoint(self.project, payload, 'cp-2')
        with self.assertRaises(ValueError):
            self.checkpoints.checkpoint(self.project, {**payload, 'revision': 2, 'summary': 'a' * 17000}, 'cp-3')
        with self.assertRaises(Conflict):
            self.checkpoints.checkpoint(self.project, {**payload, 'revision': 2, 'project_id': 'other'}, 'cp-4')
        self.assertIsNone(self.checkpoints.latest_checkpoint(self.project, 'other-session'))

    def test_known_lower_bound_holds_even_with_incomplete_coverage_across_stages(self):
        self.policy.configure(self.project, {'mode': 'hold', 'missing_telemetry': 'observe',
            'limits': {'max_input_tokens': 5, 'max_requests': 1}}, 'cfg-lower')
        self.policy.usage.ingest(request(provider='claude', project_id=self.project,
            source='synthetic', session_id='native', agent_id='worker', request_id='r1',
            model='haiku', loop_id='loop-1', stage_id='stage-1', tokens=_tokens(6, None, None, 1)))
        decision = self.policy.evaluate(self.project, operation_id='admit-stage-2',
            purpose='stage', loop_id='loop-1', stage_id='stage-2')
        self.assertEqual(decision['decision'], 'hold')
        self.assertIn('input_tokens:threshold', decision['reasons'])
        self.assertIn('requests:threshold', decision['reasons'])
        self.assertFalse(decision['observed']['coverage_complete'])
        self.assertEqual(decision['observed']['cache_inclusive_input_tokens'], 6)

    def test_context_sample_must_match_native_session(self):
        self.policy.configure(self.project, {'mode': 'hold', 'missing_telemetry': 'hold',
            'account_id': 'acct', 'limits': {'max_context_tokens': 10}}, 'cfg-context')
        self.policy.usage.ingest(normalize_claude_status(
            {'context_window': {'current_usage': {'input_tokens': 20,
                'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}},
            project_id=self.project, session_id='other-native', account_id='acct',
            observed_at='2026-10-20T00:00:00Z'))
        decision = self.policy.evaluate(self.project, operation_id='context-admit',
            purpose='stage', session_id='target-native', now='2026-10-20T00:00:10Z')
        self.assertEqual(decision['decision'], 'hold')
        self.assertIsNone(decision['observed']['context_input_tokens'])
        self.assertIn('context_tokens:stale_sample', decision['reasons'])

    def test_checkpoint_rejects_forged_trusted_binding_and_unknown_loop(self):
        payload = {'session_id': 'native-1', 'revision': 1, 'branch': None,
                   'worktree': None, 'artifact_refs': [], 'open_obligations': [],
                   'pending_reviews': [], 'operation_ids': [], 'next_action': 'resume',
                   'summary': ''}
        with self.assertRaises(Conflict):
            self.checkpoints.checkpoint(self.project, payload, 'cp-binding',
                                        expected_session_id='native-2')
        with self.assertRaises(Conflict):
            self.checkpoints.checkpoint(self.project, {**payload, 'loop_id': 'forged'},
                                        'cp-loop', expected_session_id='native-1')


if __name__ == '__main__':
    unittest.main()
