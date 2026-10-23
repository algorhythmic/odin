import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { reduceEvent } from '../src/events.js';
import { createSimulation, LINGER_MS, MAX_LIVE_SESSIONS, SIMULATION_STEP_MS, liveSessions } from '../src/simulation.js';

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

test('2,000 generated steps obey the unchanged reducer, parent, identity, usage and linger rules', () => {
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
