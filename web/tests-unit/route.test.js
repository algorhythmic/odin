// Routes are pure so deep links can be checked without a browser.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseHash, overviewHref, projectHref, historyHref, projectViewHref, sessionHref,
  setupHref, settingsHref, PROJECT_VIEWS, SETUP_STEPS, SETTINGS_SECTIONS,
} from '../src/route.js';

test('existing routes keep their shapes and hrefs', () => {
  for (const hash of ['', '#', '#/', undefined]) assert.deepEqual(parseHash(hash), { view: 'overview' });
  assert.equal(overviewHref(), '#/');
  assert.equal(projectHref('p'), '#/projects/p');
  assert.equal(historyHref('p'), '#/projects/p/history');
  assert.equal(sessionHref('p', 's'), '#/projects/p/sessions/s');
  assert.deepEqual(parseHash(projectHref('p')), { view: 'project', pid: 'p', sid: null });
  assert.deepEqual(parseHash(sessionHref('p', 's')), { view: 'project', pid: 'p', sid: 's' });
  assert.deepEqual(parseHash(historyHref('p')), { view: 'history', pid: 'p' });
});

test('every project view round trips with and without session selection', () => {
  for (const view of PROJECT_VIEWS) {
    const extra = view === 'tree' ? {} : { projectView: view };
    assert.deepEqual(parseHash(projectViewHref('p', view)), { view: 'project', pid: 'p', ...extra, sid: null });
    assert.deepEqual(parseHash(sessionHref('p', 's', view)), { view: 'project', pid: 'p', ...extra, sid: 's' });
  }
  assert.equal(projectViewHref('p'), projectHref('p'));
  assert.equal(projectViewHref('p', 'tree'), projectHref('p'));
});

test('setup and all steps round trip', () => {
  assert.equal(setupHref(), '#/setup');
  assert.deepEqual(parseHash(setupHref()), { view: 'setup', step: null });
  for (const step of SETUP_STEPS) assert.deepEqual(parseHash(setupHref(step)), { view: 'setup', step });
});

test('all settings sections round trip', () => {
  for (const section of SETTINGS_SECTIONS) assert.deepEqual(parseHash(settingsHref(section)), { view: 'settings', section });
});

test('project and session identifiers are encoded separately and decoded once', () => {
  const pid = 'project / #?% 雪';
  const sid = 'session / %2F';
  for (const view of PROJECT_VIEWS) {
    assert.equal(parseHash(projectViewHref(pid, view)).pid, pid);
    const route = parseHash(sessionHref(pid, sid, view));
    assert.equal(route.pid, pid);
    assert.equal(route.sid, sid);
  }
  assert.equal(parseHash(historyHref(pid)).pid, pid);
});

test('unknown and incomplete routes are not found', () => {
  for (const hash of [
    '#/missing', '#/projects', '#/projects/p/tree', '#/projects/p/unknown',
    '#/projects/p/queue/sessions', '#/projects/p/queue/sessions/s/extra',
    '#/projects/p/sessions', '#/projects/p/sessions/s/extra', '#/projects/p/history/sessions/s',
    '#/setup/unknown', '#/setup/providers/extra', '#/settings', '#/settings/review',
    '#/settings/unknown', '#/settings/models/extra', '#/projects/p/Queue',
  ]) assert.deepEqual(parseHash(hash), { view: 'unknown' }, hash);
});

test('a malformed encoded identifier never throws', () => {
  assert.deepEqual(parseHash('#/projects/%E0%A4%A'), { view: 'project', pid: '%E0%A4%A', sid: null });
});
