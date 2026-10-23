import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createSimulation, visibleSessions } from '../src/simulation.js';
import { createSyntheticStore, MAX_RETIRED_SESSIONS, MAX_ACTIVITY_PER_PROJECT, MAX_SEEN_EVENTS } from '../src/synthetic-store.js';
import { dashboardKPIs, dashboardTime, priorityItems, projectOverview,
  recentActivity, recentSessionActivity } from '../src/dashboard.js';
import { createSetupStore } from '../src/setup.js';
import { observeElapsed } from '../src/live.js';

const read = (file) => JSON.parse(fs.readFileSync(new URL(`../fixtures/${file}.json`, import.meta.url)));

test('20,000 generated steps bound records, activity, dedupe and elapsed state; dashboard projects under 5 ms', () => {
  const store = createSyntheticStore(read('default-snapshot'));
  for (const e of read('default-events').events) store.apply(e);
  const simulation = createSimulation();
  const baselines = new Map();
  let last;
  for (let i = 0; i < 20000; i++) {
    last = simulation.next(store.getSnapshot());
    assert.equal(store.apply(last).status, 'applied');
    const snap = store.getSnapshot();
    observeElapsed(snap.sessions, baselines, i);
    assert(snap.sessions.length <= MAX_RETIRED_SESSIONS + 18);
    assert(baselines.size <= MAX_RETIRED_SESSIONS + 18);
    assert(store.seenCount() <= MAX_SEEN_EVENTS);
  }
  const snap = store.getSnapshot();
  const ids = new Set(snap.sessions.map((s) => s.id));
  assert.equal(snap.sessions.filter((s) => s.lifecycle === 'retired').length, MAX_RETIRED_SESSIONS);
  assert(snap.runs.length <= snap.sessions.length + 10);
  assert(snap.runs.every((r) => ids.has(r.session_id)));
  for (const entries of Object.values(snap.activity)) {
    assert(entries.length <= MAX_ACTIVITY_PER_PROJECT);
    assert(entries.every((e) => ids.has(e.session_id)));
  }
  assert(store.historyTrimmed());
  assert.equal(store.seenCount(), MAX_SEEN_EVENTS);
  assert.equal(store.apply(last).status, 'duplicate');
  assert.equal(store.apply({ ...last, event_id: 'old-delivery', revision: 1 }).status, 'stale');
  const setup = createSetupStore(read('setup')).getState();
  // Include a fresh activity index and every unfolded row, as well as cached elapsed renders.
  const samples = [];
  for (let i = 0; i < 15; i++) {
    const version = { ...snap };
    const start = performance.now();
    dashboardKPIs(version);
    dashboardTime(version);
    const rows = priorityItems(version, setup);
    for (const row of rows) recentSessionActivity(version, row.sessionId);
    for (const p of version.projects) projectOverview(version, p.id);
    recentActivity(version).slice(0, 12);
    samples.push(performance.now() - start);
  }
  const median = samples.sort((a, b) => a - b)[Math.floor(samples.length / 2)];
  console.log(`20,000-step synthetic dashboard projection median: ${median.toFixed(3)} ms`);
  assert(median < 5, `${median.toFixed(3)} ms < 5 ms`);
});

test('retention protects retired ancestry of live work and releases it when the subtree retires', () => {
  const snap = read('default-snapshot');
  const template = snap.sessions[0];
  const old = { ...template, id: 'old-parent', lifecycle: 'retired', parent_session_id: null };
  const child = { ...template, id: 'live-child', lifecycle: 'running', parent_session_id: old.id };
  snap.sessions = [old, child, ...Array.from({ length: 501 }, (_, i) => ({
    ...old, id: `retired-${i}`, observed_at: '2026-10-22T12:00:00Z',
  }))];
  const store = createSyntheticStore(snap);
  const event = (sid, revision) => ({ event_id: `retire-${revision}`, revision, type: 'session.retired',
    at: '2026-10-23T12:00:00Z', payload: { session_id: sid, observed_at: '2026-10-23T12:00:00Z' } });
  assert.equal(store.apply(event('retired-0', 1)).status, 'applied');
  assert.deepEqual(visibleSessions(store.getSnapshot().sessions).map((s) => s.id), ['old-parent', 'live-child']);
  assert(store.getSnapshot().sessions.some((s) => s.id === old.id));
  assert.equal(store.apply(event(child.id, 2)).status, 'applied');
  assert(!store.getSnapshot().sessions.some((s) => s.id === old.id));
});

test('dedupe expires by the applied delivery window; rejected IDs remain correctable', () => {
  const store = createSyntheticStore(read('default-snapshot'));
  const event = (revision) => ({ event_id: `event-${revision}`, revision, type: 'session.lifecycle_changed',
    at: '2026-10-23T12:00:00Z', payload: { session_id: 'ses-docs-01', lifecycle: 'idle' } });
  for (let i = 1; i <= MAX_SEEN_EVENTS + 1; i++) assert.equal(store.apply(event(i)).status, 'applied');
  assert.equal(store.apply(event(1)).status, 'stale');
  assert.equal(store.apply(event(2)).status, 'duplicate');
  const next = event(MAX_SEEN_EVENTS + 2);
  assert.equal(store.apply({ ...next, payload: { ...next.payload, lifecycle: 'invalid' } }).status, 'rejected');
  assert.equal(store.apply(next).status, 'applied');
});
