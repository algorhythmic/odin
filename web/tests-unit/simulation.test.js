import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { reduceEvent } from '../src/events.js';
import { createSimulation, LINGER_MS, MAX_LIVE_SESSIONS, SIMULATION_STEP_MS, liveSessions, visibleSessions } from '../src/simulation.js';
import { generateLargeSnapshot } from '../src/fixtures/large.js';
import { expectedLiveRecords } from '../tests-support/live-expectations.js';
import { displayedElapsed, observeElapsed } from '../src/live.js';

const read = (file) => JSON.parse(fs.readFileSync(new URL(`../fixtures/${file}`, import.meta.url), 'utf8'));
function replay(seed, steps = 2000, fixtures = true) {
  let snapshot = read('default-snapshot.json');
  const seen = new Set();
  if (fixtures) for (const e of read('default-events.json').events) {
    const out = reduceEvent(snapshot, seen, e);
    snapshot = out.snapshot;
    if (out.result.status === 'applied') seen.add(e.event_id);
  }
  const initial = structuredClone(snapshot);
  const simulation = createSimulation(seed);
  const events = [];
  const ids = new Set(snapshot.sessions.map((s) => s.id));
  const endedAt = new Map();
  const populations = [];
  const starts = [];
  for (let i = 0; i < steps; i++) {
    const e = simulation.next(snapshot);
    assert(e, `step ${i} supplies an event`);
    assert(!seen.has(e.event_id), 'unique event id');
    const s = e.payload.session;
    if (s) {
      assert(!ids.has(s.id), 'unique session id, including retired sessions');
      ids.add(s.id);
      const parent = snapshot.sessions.find((p) => p.id === s.parent_session_id);
      assert.equal(parent?.lifecycle, 'running', 'the recorded parent is running at start time');
      assert(parent.project_id === s.project_id || (parent.id === snapshot.executive_session_id
        && s.role === 'integration owner'), 'same project, or executive starting an integration owner');
      if (s.previous_attempt) {
        const previous = snapshot.sessions.find((p) => p.id === s.previous_attempt);
        assert.equal(previous.parent_session_id, s.parent_session_id);
        assert.equal(previous.project_id, s.project_id);
        assert.notEqual(previous.id, s.id);
        assert.equal(snapshot.runs.find((r) => r.session_id === previous.id).outcome, 'failed');
      }
      starts.push(s);
    }
    if (e.payload.lifecycle === 'ended') endedAt.set(e.payload.session_id, i);
    if (e.type === 'session.retired' && endedAt.has(e.payload.session_id)) {
      assert((i - endedAt.get(e.payload.session_id)) * SIMULATION_STEP_MS >= LINGER_MS);
    }
    if (e.type === 'session.usage_updated') {
      const before = snapshot.sessions.find((p) => p.id === e.payload.session_id);
      assert.equal(before.lifecycle, 'running');
      assert.equal(e.payload.tokens.basis, 'measured');
      for (const key of ['uncached_input', 'cache_read', 'cache_write', 'output']) {
        assert(e.payload.tokens[key] > (before.tokens[key] || 0));
      }
    }
    const out = reduceEvent(snapshot, seen, e);
    assert.equal(out.result.status, 'applied', JSON.stringify(out.result));
    seen.add(e.event_id);
    snapshot = out.snapshot;
    events.push(e);
    populations.push(liveSessions(snapshot.sessions).length);
  }
  return { snapshot, initial, events, populations, starts };
}

test('2,000 generated steps obey the reducer, parent, identity, usage and linger rules', () => {
  const { snapshot, initial, events, starts } = replay();
  assert.deepEqual(snapshot.sessions.filter((s) => s.project_id === 'proj-malformed'),
    initial.sessions.filter((s) => s.project_id === 'proj-malformed'));
  assert.deepEqual(new Set(events.map((e) => e.type)), new Set([
    'session.started', 'session.lifecycle_changed', 'session.usage_updated', 'session.retired',
  ]));
  for (const role of ['worker', 'subagent', 'reviewer']) assert(starts.some((s) => s.role === role));
  assert(starts.some((s) => s.previous_attempt), 'failed work sometimes starts a distinct retry');
  const outcomes = events.filter((e) => e.payload.run).map((e) => e.payload.run.outcome);
  assert(outcomes.includes('failed'));
  assert(outcomes.filter((o) => o === 'verified').length > outcomes.filter((o) => o === 'failed').length);
  assert(events.some((e) => e.payload.lifecycle === 'waiting_for_input'));
  assert(events.some((e) => e.payload.lifecycle === 'running'));
  assert.equal(new Set(starts.map((s) => s.project_id)).size, 3, 'work spreads into the empty project too');
});

test('the population settles inside 8–18 after the fixture overflow drains, across seeds', () => {
  for (const seed of ['20261022', 'one', 'two']) {
    const { populations } = replay(seed);
    // The fixed queue briefly leaves 20 live records; existing ended leaves drain first.
    assert(populations.slice(5).every((n) => n >= 8 && n <= MAX_LIVE_SESSIONS), `${seed}: ${Math.max(...populations)}`);
  }
  assert(replay('snapshot', 2000, false).populations.every((n) => n >= 8 && n <= MAX_LIVE_SESSIONS));
});

test('the default and explicit seeds are deterministic and different seeds vary', () => {
  assert.deepEqual(replay(undefined, 100).events, replay(undefined, 100).events);
  assert.deepEqual(replay('same', 100).events, replay('same', 100).events);
  assert.notDeepEqual(replay('same', 100).events, replay('different', 100).events);
});

test('retired sessions stay visible while a descendant is live, and leave with their subtree', () => {
  const s = (id, parent, lifecycle) => ({ id, parent_session_id: parent, lifecycle });
  const ids = (list) => visibleSessions(list).map((x) => x.id);
  assert.deepEqual(ids([s('a', null, 'retired'), s('b', 'a', 'retired'), s('c', 'b', 'running')]), ['a', 'b', 'c']);
  assert.deepEqual(ids([s('a', null, 'retired'), s('b', 'a', 'retired'), s('c', 'b', 'retired')]), []);
  assert.deepEqual(ids([s('a', 'b', 'retired'), s('b', 'a', 'retired'), s('c', 'a', 'ended')]), ['a', 'b', 'c']);
});

test('default and large visibility agree with the recorded descendant rule independently', () => {
  for (const snapshot of [read('default-snapshot.json'), generateLargeSnapshot()]) {
    const expected = expectedLiveRecords(snapshot.sessions);
    assert.deepEqual(visibleSessions(snapshot.sessions), expected);
    const retired = expected.filter((s) => s.lifecycle === 'retired');
    if (snapshot.dataset === 'large') {
      assert.equal(retired.length, 168);
      const ids = new Set(expected.map((s) => s.id));
      assert.equal(expected.filter((s) => s.project_id && (s.parent_session_id === snapshot.executive_session_id
        || !ids.has(s.parent_session_id))).length, 40);
    } else {
      assert.deepEqual(retired, []);
      assert(!expected.some((s) => s.id === 'ses-helper-01'));
    }
  }
});

test('default-seed replay derives elapsed through waiting, resuming, ending and retirement without new event fields', () => {
  const { initial, events } = replay(undefined, 2000);
  let snapshot = initial;
  const states = new Map();
  const accumulated = new Map();
  const baselines = new Map();
  const covered = new Set();
  for (const e of events) {
    const s = e.payload.session;
    if (s) {
      assert.equal(s.elapsed_s, 0);
      states.set(s.id, { lifecycle: s.lifecycle, at: Date.parse(s.observed_at) });
      accumulated.set(s.id, 0);
    } else assert(!('elapsed_s' in e.payload), 'elapsed is never a lifecycle or retirement event field');
    const sid = e.payload.session_id;
    if (['session.lifecycle_changed', 'session.retired'].includes(e.type) && accumulated.has(sid)) {
      const state = states.get(sid);
      const at = Date.parse(e.payload.observed_at);
      if (state.lifecycle === 'running') {
        accumulated.set(sid, accumulated.get(sid) + Math.max(0, Math.floor((at - state.at) / 1000)));
      }
      const lifecycle = e.type === 'session.retired' ? 'retired' : e.payload.lifecycle;
      states.set(sid, { lifecycle, at });
      covered.add(lifecycle);
    }
    snapshot = reduceEvent(snapshot, new Set(), e).snapshot;
    observeElapsed(snapshot.sessions, baselines, 0);
    const after = snapshot.sessions.find((s) => s.id === sid);
    if (after && accumulated.has(sid) && ['session.lifecycle_changed', 'session.retired'].includes(e.type)) {
      assert.equal(displayedElapsed(after, baselines, 0), accumulated.get(sid));
      if (after.lifecycle === 'running') {
        assert.equal(displayedElapsed(after, baselines, 7), after.elapsed_s + 7);
      }
    }
  }
  assert.deepEqual(covered, new Set(['waiting_for_input', 'running', 'ended', 'retired']));
  assert(accumulated.get('ses-sim-mvl79i-6') >= 60, 'the reported long-lived session keeps its elapsed');
});
