import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { dashboardKPIs, priorityItems, filterPriority, priorityCounts, dashboardTime,
  projectOverview, recentActivity, recentSessionActivity, relativeTime } from '../src/dashboard.js';
import { createSetupStore } from '../src/setup.js';
const read = (file) => JSON.parse(fs.readFileSync(new URL(`../fixtures/${file}.json`, import.meta.url)));
const snapshot = read('default-snapshot');
const fixture = read('setup');
const setup = () => createSetupStore(fixture).getState();

test('priority types follow urgency, preserve recorded proposals, and include failed retired runs', () => {
  const list = priorityItems(snapshot, setup());
  assert.deepEqual([...new Set(list.map((i) => i.kind))], ['setup', 'needs', 'failed', 'decision', 'usage', 'host']);
  assert.equal(list[0].step, 'roles');
  assert.equal(list.filter((i) => i.kind === 'failed').length, snapshot.runs.filter((r) => r.outcome === 'failed').length);
  assert.deepEqual(list.find((i) => i.kind === 'decision').decision, snapshot.decisions[0]);
  assert.equal(list.filter((i) => i.kind === 'usage').length, 2);
  assert(!list.some((i) => i.title === 'Delegation login'));
  for (let i = 1; i < list.length; i++) assert(list[i].rank >= list[i - 1].rank);
});

test('filters count every match, without mixing pending decisions into the input filter', () => {
  const list = priorityItems(snapshot, setup());
  const counts = priorityCounts(list);
  assert.equal(counts.All, list.length);
  for (const [filter, kind] of [['Needs you', 'needs'], ['Failed', 'failed'], ['Setup', 'setup']]) {
    assert.equal(counts[filter], list.filter((i) => i.kind === kind).length);
    assert(filterPriority(list, filter).every((i) => i.kind === kind));
  }
});

test('empty applied portfolio has no priorities; unavailable usage creates no warning', () => {
  const state = setup(); state.complete = true;
  for (const p of state.draft.providers) for (const l of p.lineages) l.status = 'not_connected';
  assert.deepEqual(priorityItems(read('empty-snapshot'), state), []);
});

test('stale and offline are one row per session, ordered by latest observation', () => {
  const snap = structuredClone(snapshot);
  snap.sessions = [
    { id: 'a', lifecycle: 'host_offline', stale: true, observed_at: '2026-10-21T10:00:00Z' },
    { id: 'b', lifecycle: 'running', stale: true, observed_at: '2026-10-21T11:00:00Z' },
  ];
  const items = priorityItems(snap, setup()).filter((i) => i.kind === 'host');
  assert.deepEqual(items.map((i) => i.sessionId), ['b', 'a']);
});

test('KPIs count own tokens once excluding cache reads; estimates, missing counters and zero stay distinct', () => {
  const snap = { sessions: [
    { id: 'a', lifecycle: 'running', tokens: { basis: 'estimate', uncached_input: 10, cache_read: 99999,
      cache_write: 20, output: 30 } },
    { id: 'b', lifecycle: 'waiting_for_input', needs_operator_input: true, tokens: { basis: 'unknown' } },
    { id: 'c', lifecycle: 'retired', tokens: { basis: 'measured', uncached_input: 0, cache_read: 0,
      cache_write: 0, output: 0 } },
    { id: 'd', lifecycle: 'ended', tokens: { basis: 'measured', uncached_input: 10, cache_write: 20, output: 30 } },
  ], runs: [{ session_id: 'c', outcome: 'failed' }, { session_id: 'c', outcome: 'failed' }] };
  assert.deepEqual(dashboardKPIs(snap), { running: 1, needsYou: 1, failed: 1, ended: 2,
    tokens: { known: 60, knownCount: 2, unknown: 2, estimate: true } });
  assert.equal(dashboardKPIs({ sessions: [snap.sessions[1]], runs: [] }).tokens.knownCount, 0);
});

test('project tiles keep cumulative tokens but status bars describe live records', () => {
  const p = projectOverview(snapshot, 'proj-odin-webapp');
  assert.equal(p.agents, snapshot.sessions.filter((s) => s.project_id === 'proj-odin-webapp'
    && s.lifecycle !== 'retired').length);
  assert.equal(Object.values(p.buckets).reduce((a, b) => a + b, 0), p.agents);
  assert.equal(projectOverview(snapshot, 'proj-empty').at, undefined);
});

test('activity orders across projects, excludes token noise, and relative times retain unknown', () => {
  const events = recentActivity(snapshot);
  assert(events[0].at >= events.at(-1).at);
  assert(Number.isFinite(dashboardTime(snapshot)));
  assert.equal(relativeTime(null, dashboardTime(snapshot)), 'time unknown');
  assert.equal(relativeTime('2026-10-21T10:00:00Z', Date.parse('2026-10-21T10:02:00Z')), '2m ago');
});

test('activity is indexed once per snapshot and session slices preserve sorted, non-usage activity', () => {
  const snap = structuredClone(snapshot);
  snap.activity = { a: [
    { id: 'a', session_id: 's', at: '2026-10-22T10:00:00Z', kind: 'session.started' },
    { id: 'noise', session_id: 's', at: '2026-10-22T12:00:00Z', kind: 'session.usage_updated' },
  ], b: Array.from({ length: 4 }, (_, i) => ({ id: `b${i}`, session_id: 's',
    at: `2026-10-22T11:00:0${i}Z`, kind: 'session.lifecycle_changed' })) };
  const sorted = recentActivity(snap);
  assert.equal(recentActivity(snap), sorted, 'elapsed-only renders reuse the same sorted array');
  assert.deepEqual(sorted.map((e) => e.id), ['b3', 'b2', 'b1', 'b0', 'a']);
  assert.deepEqual(recentSessionActivity(snap, 's'), sorted.slice(0, 3));
  assert.deepEqual(recentSessionActivity(snap, 'missing'), []);
  const updated = { ...snap, activity: { a: snap.activity.a } };
  assert.notEqual(recentActivity(updated), sorted);
  assert.deepEqual(recentActivity(updated).map((e) => e.id), ['a']);
});
