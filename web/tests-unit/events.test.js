// Unit tests for the projection update-event rules (src/events.js), run by
// Node's built-in test runner: npm run test:unit. Synthetic fixtures only.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { reduceEvent, LIFECYCLES } from '../src/events.js';

const read = (name) => JSON.parse(fs.readFileSync(new URL(`../fixtures/${name}`, import.meta.url), 'utf8'));
const snapshot = read('default-snapshot.json');
const { events } = read('default-events.json');
const byId = (id) => events.filter((e) => e.event_id === id);

// Feeds events through reduceEvent the way the store does.
function replay(list, start = snapshot) {
  let snap = start;
  const seen = new Set();
  const results = [];
  for (const evt of list) {
    const out = reduceEvent(snap, seen, evt);
    if (out.result.status === 'applied') { snap = out.snapshot; seen.add(evt.event_id); } else assert.equal(out.snapshot, snap);
    results.push(out.result);
  }
  return { snap, seen, results };
}

const atRevision4 = () => replay(events.slice(0, 5)).snap;
const rejected = (evt, snap = atRevision4()) => {
  const { result, snapshot: after } = reduceEvent(snap, new Set(), evt);
  assert.equal(result.status, 'rejected', `${evt.event_id}: ${JSON.stringify(result)}`);
  assert.equal(after, snap, 'a rejected event leaves the snapshot object untouched');
  return result.reason;
};

test('the fixture sequence yields the documented statuses', () => {
  const { snap, results } = replay(events);
  assert.deepEqual(results.map((r) => `${r.event_id}:${r.status}`), [
    'evt-001:applied', 'evt-002:applied', 'evt-002:duplicate', 'evt-003:applied', 'evt-004:applied',
    'evt-bad-1:rejected', 'evt-bad-2:rejected', 'evt-bad-3:rejected', 'evt-bad-4:rejected',
    'evt-bad-5:rejected', 'evt-bad-6:rejected', 'evt-bad-7:rejected', 'evt-bad-8:rejected',
    'evt-bad-9:rejected', 'evt-bad-6:applied', 'evt-005:gap',
  ]);
  assert.equal(snap.revision, 5);
  assert.equal(snap.sessions.length, snapshot.sessions.length + 1);
});

test('non-integer revision is rejected', () => {
  assert.equal(rejected(byId('evt-bad-3')[0]), 'revision is not an integer');
  for (const revision of ['5', null, undefined, Number.NaN]) {
    assert.equal(rejected({ ...byId('evt-001')[0], event_id: 'x', revision }), 'revision is not an integer');
  }
});

test('unknown event type is rejected', () => {
  assert.equal(rejected(byId('evt-bad-2')[0]), 'unknown event type');
});

test('missing or unknown session_id is rejected', () => {
  assert.equal(rejected(byId('evt-bad-7')[0]), 'missing session_id');
  assert.equal(rejected(byId('evt-bad-1')[0]), 'unknown session');
  assert.equal(rejected({ ...byId('evt-bad-7')[0], payload: { session_id: '', cost: null } }), 'missing session_id');
});

test('session.started without a usable record is rejected', () => {
  assert.equal(rejected(byId('evt-bad-4')[0]), 'missing session record');
  assert.equal(rejected(byId('evt-bad-8')[0]), 'session id is not a string');
  assert.equal(rejected(byId('evt-bad-9')[0]), 'unknown project');
  const record = byId('evt-002')[0].payload.session;
  const started = (session) => ({ ...byId('evt-bad-4')[0], event_id: 'y', payload: { session } });
  assert.equal(rejected(started({ ...record, project_id: 7 })), 'project_id is not a string');
  assert.equal(rejected(started({ ...record, lifecycle: 'paused' })), 'unknown lifecycle');
});

test('session.started for an existing id is rejected', () => {
  assert.equal(rejected(byId('evt-bad-5')[0]), 'session already exists');
});

test('lifecycle_changed outside the documented set is rejected', () => {
  assert.equal(rejected(byId('evt-bad-6')[0]), 'unknown lifecycle');
  for (const lifecycle of LIFECYCLES) {
    const { result } = reduceEvent(atRevision4(), new Set(), { ...byId('evt-bad-6')[0], payload: { session_id: 'ses-pin-worker', lifecycle } });
    assert.equal(result.status, 'applied', lifecycle);
  }
});

test('a corrected re-delivery under a previously rejected id applies once', () => {
  const [bad, corrected] = byId('evt-bad-6');
  const { snap, seen, results } = replay([...events.slice(0, 5), bad, corrected, corrected]);
  assert.deepEqual(results.slice(5).map((r) => r.status), ['rejected', 'applied', 'duplicate']);
  assert.ok(seen.has('evt-bad-6'));
  const worker = snap.sessions.find((s) => s.id === 'ses-pin-worker');
  assert.equal(worker.lifecycle, 'running');
  assert.equal(worker.needs_operator_input, false);
  assert.equal(snap.activity['proj-contract-pins'].at(-1).id, 'evt-bad-6');
});

test('gap and stale revisions are reported, not applied', () => {
  const snap = atRevision4();
  const gap = reduceEvent(snap, new Set(), byId('evt-005')[0]);
  assert.deepEqual([gap.result.status, gap.result.current, gap.snapshot], ['gap', 4, snap]);
  const stale = reduceEvent(snap, new Set(), { ...byId('evt-001')[0], event_id: 'z' });
  assert.deepEqual([stale.result.status, stale.snapshot], ['stale', snap]);
});

test('applying never mutates the input snapshot', () => {
  const before = JSON.stringify(snapshot);
  replay(events);
  assert.equal(JSON.stringify(snapshot), before);
});
