"""Synthetic account limit samples crossing admission bands; no network calls."""
import tempfile
import unittest
import uuid

from odin.contracts import identifier, strict_loads
from odin.coordination import Actor
from odin.executive_mcp import ExecutiveBridge
from odin.executive_service import prepare_project, submit_executive
from odin.gateway import Gateway, GatewayContext
from odin.service import Service
from odin.usage import _limit_sample, normalize_claude_status


class LimitNoticeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = temporary.name
        self.project = prepare_project(self.state)
        self.other = prepare_project(self.state)
        self.service = Service(self.state)
        self.addCleanup(self.service.close)
        self.gateway = Gateway(self.service)
        self.operator = GatewayContext('terminal', Actor('operator', 'synthetic'))
        self.session = str(uuid.uuid4())

    def send(self, action, payload, *, project=None, executive=False):
        project = project or self.project
        command = {'schema_version': 1, 'operation_id': identifier(),
                   'action': action, 'payload': {'project': project} | payload}
        if executive:
            return submit_executive(self.gateway, {'command': command}, project)['result']
        return self.gateway.submit(command, context=self.operator)['result']

    def status(self, weekly, at, *, five_hour=10):
        sample = normalize_claude_status(
            {'session_id': self.session,
             'rate_limits': {'five_hour': {'used_percentage': five_hour},
                             'seven_day': {'used_percentage': weekly}}},
            project_id=self.project, session_id=self.session, observed_at=at)
        return self.send('usage_import', {'source_id': 'fixture:status:' + at,
                                          'observations': [sample]})

    def probe(self, label, percent, at, *, status='available'):
        sample = _limit_sample('claude', label, project_id=self.project, observed_at=at,
                               status=status, utilization=percent,
                               reason='synthetic' if status != 'available' else None)
        return self.send('usage_import', {'source_id': 'fixture:probe:' + at,
                                          'observations': [sample]})

    def pending(self):
        return self.gateway.limit_notices.pending(self.project)

    def bridge(self, project=None):
        project = project or self.project

        def gateway(command):
            return submit_executive(self.gateway, {'command': command}, project)
        return ExecutiveBridge(project, gateway, development_loop=True,
                               session_id=self.session)

    def test_band_changes_create_one_current_notice_per_label(self):
        self.status(47, '2026-10-21T10:00:00Z')
        self.assertEqual(self.pending(), [])
        self.status(82, '2026-10-21T11:00:00Z')
        (wind_down,) = self.pending()
        self.assertEqual((wind_down['label'], wind_down['previous_band'], wind_down['band']),
                         ('claude.weekly', 'clear', 'wind_down'))
        self.assertEqual(wind_down['source'], 'status_line')
        self.status(83, '2026-10-21T11:30:00Z')
        self.assertEqual([n['id'] for n in self.pending()], [wind_down['id']])
        self.status(86, '2026-10-21T12:00:00Z')
        (stop,) = self.pending()
        self.assertEqual((stop['previous_band'], stop['band']), ('wind_down', 'ordinary_stop'))
        self.assertEqual(self.gateway.limit_notices.notice(wind_down['id'])['state'], 'superseded')
        # An older sample never moves the band, and a replay inserts nothing.
        self.status(95, '2026-10-21T09:00:00Z')
        self.status(86, '2026-10-21T12:00:00Z')
        self.assertEqual([n['id'] for n in self.pending()], [stop['id']])
        history = [strict_loads(row[0]) for row in self.service.store.db.execute(
            "SELECT body FROM history WHERE body LIKE '%usage.limit_band_changed%'")]
        self.assertEqual(len(history), 2)

    def test_fable_weekly_notice_suggests_the_operator_model_switch(self):
        self.probe('claude.weekly.fable', 80, '2026-10-21T10:00:00Z')
        self.assertEqual(self.pending(), [])
        self.probe('claude.weekly.fable', None, '2026-10-21T10:30:00Z', status='unavailable')
        self.assertEqual(self.pending(), [])
        self.probe('claude.weekly.fable', 91, '2026-10-21T11:00:00Z')
        (notice,) = self.pending()
        self.assertEqual(notice['band'], 'ordinary_stop')
        self.assertIn('executive-configure-model --model claude-opus-5-5',
                      notice['suggested_action'])
        text = self.gateway.limit_notices.render(notice)
        self.assertIn('NOTICE, not an assignment', text)
        self.assertIn("operator's decision", text)
        self.probe('claude.weekly.opus', 99, '2026-10-21T11:00:00Z')
        self.assertEqual(len(self.pending()), 1)

    def test_notice_reaches_the_executive_and_acknowledgement_stops_it(self):
        self.status(82, '2026-10-21T11:00:00Z')
        (notice,) = self.pending()
        messages = self.bridge().loop_inbox()
        self.assertEqual([(m['kind'], m['notice_id'], m['loop_id']) for m in messages],
                         [('notice', notice['id'], None)])
        self.assertIn('claude.weekly moved from unobserved to wind_down at 82%', messages[0]['content'])
        self.assertIsNotNone(self.gateway.limit_notices.notice(notice['id'])['first_offered_at'])
        other = self.bridge(self.other).call(
            'odin_loop_ack', {'notice_id': notice['id'], 'operation_id': identifier()})
        self.assertTrue(other['isError'])
        acknowledged = self.bridge().call(
            'odin_loop_ack', {'notice_id': notice['id'], 'operation_id': identifier()})
        self.assertFalse(acknowledged['isError'], acknowledged['content'][0]['text'])
        stored = self.gateway.limit_notices.notice(notice['id'])
        self.assertEqual(stored['state'], 'acknowledged')
        self.assertEqual(stored['acknowledgement_authority'],
                         'model_attributed_not_operator_approval')
        self.assertEqual(self.bridge().loop_inbox(), [])


if __name__ == '__main__':
    unittest.main()
