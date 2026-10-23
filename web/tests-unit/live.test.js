// Unit tests for the live-surface helpers (src/live.js): autoplay
// interval scheduling and the header summary counts. Run by Node's
// built-in test runner: npm run test:unit.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  BASE_INTERVAL_MS, SPEEDS, attentionCounts, cleanSpeed, displayedElapsed, failedSessionIds,
  intervalFor, observeElapsed, simulationSummary,
} from '../src/live.js';

test('autoplay speed validation keeps documented speeds and defaults the rest', () => {
  assert.deepEqual(SPEEDS, [0.5, 1, 2, 4]);
  for (const s of SPEEDS) assert.equal(cleanSpeed(s), s);
  for (const bad of [0, 3, 8, -1, 1.5, '4', 'fast', null, undefined, NaN]) {
    assert.equal(cleanSpeed(bad), 1, JSON.stringify(bad));
  }
});

test('the event interval divides the base interval by speed', () => {
  assert.equal(intervalFor(1), BASE_INTERVAL_MS);
  assert.equal(intervalFor(0.5), BASE_INTERVAL_MS * 2);
  assert.equal(intervalFor(2), BASE_INTERVAL_MS / 2);
  assert.equal(intervalFor(4), BASE_INTERVAL_MS / 4);
  assert.equal(intervalFor(99), BASE_INTERVAL_MS); // unknown speed falls back to 1x
});

test('failed session ids come only from runs recorded failed', () => {
  const runs = [
    { session_id: 'a', outcome: 'failed' },
    { session_id: 'a', outcome: 'unverified' },
    { session_id: 'b', outcome: 'failed' },
    { session_id: 'c', outcome: 'verified' },
    { session_id: 'd', outcome: 'unknown' },
  ];
  assert.deepEqual([...failedSessionIds(runs)].sort(), ['a', 'b']);
  assert.deepEqual([...failedSessionIds([])], []);
});

const session = (lifecycle, extra = {}) => ({ id: extra.id || Math.random().toString(36).slice(2), lifecycle, needs_operator_input: false, ...extra });

test('attention counts match the status rules', () => {
  const sessions = [
    session('running'),
    session('running'),
    session('waiting_for_input'),
    session('running', { needs_operator_input: true }),
    session('ended', { id: 'done-ok' }),
    session('ended', { id: 'done-failed' }),
    session('retired'),
    session('idle'),
    session('host_offline'),
  ];
  const counts = attentionCounts(sessions, failedSessionIds([{ session_id: 'done-failed', outcome: 'failed' }]));
  assert.deepEqual(counts, { agents: 9, running: 3, needsYou: 2, failed: 1 });
});

test('a failed run on a non-ended session does not count as failed', () => {
  const sessions = [session('running', { id: 'mid-run' }), session('retired', { id: 'stopped' })];
  const failed = failedSessionIds([{ session_id: 'mid-run', outcome: 'failed' }, { session_id: 'stopped', outcome: 'failed' }]);
  const counts = attentionCounts(sessions, failed);
  assert.equal(counts.failed, 0);
  assert.equal(counts.running, 1);
});

test('an empty project reports zeros, never undefined', () => {
  assert.deepEqual(attentionCounts([], new Set()), { agents: 0, running: 0, needsYou: 0, failed: 0 });
});

test('the driver distinguishes queued fixtures, generation and a fixed large dataset', () => {
  const sessions = [session('running'), session('ended'), session('retired')];
  assert.deepEqual(simulationSummary(sessions, 1, true), { generating: false, population: 2, available: true });
  assert.deepEqual(simulationSummary(sessions, 0, true), { generating: true, population: 2, available: true });
  assert.deepEqual(simulationSummary(sessions, 0, false), { generating: false, population: 2, available: false });
});

test('a session already running at play accumulates ticks from the start', () => {
  const baselines = new Map();
  const s = { id: 's-exec', lifecycle: 'running', elapsed_s: 9240 };
  observeElapsed([s], baselines, 0);
  assert.equal(displayedElapsed(s, baselines, 0), 9240);
  assert.equal(displayedElapsed(s, baselines, 3), 9243);
  assert.equal(displayedElapsed(s, baselines, 60), 9300);
});

test('a session that starts running mid-play ticks only since it appeared', () => {
  const baselines = new Map();
  const first = { id: 's-exec', lifecycle: 'running', elapsed_s: 100 };
  observeElapsed([first], baselines, 0);
  // The newcomer is observed running at tick 16 with recorded elapsed_s 10.
  const late = { id: 's-late', lifecycle: 'running', elapsed_s: 10 };
  observeElapsed([first, late], baselines, 16);
  assert.equal(displayedElapsed(late, baselines, 16), 10);
  assert.equal(displayedElapsed(late, baselines, 20), 14);
  // The earlier session keeps its own baseline, not the newcomer's.
  assert.equal(displayedElapsed(first, baselines, 20), 120);
});

test('a lifecycle or elapsed_s change resets the baseline', () => {
  const baselines = new Map();
  let s = { id: 's', lifecycle: 'running', elapsed_s: 50 };
  observeElapsed([s], baselines, 3);
  assert.equal(displayedElapsed(s, baselines, 8), 55);
  // Ending at tick 10 stops the ticking; the recorded value is kept.
  s = { ...s, lifecycle: 'ended' };
  observeElapsed([s], baselines, 10);
  assert.equal(displayedElapsed(s, baselines, 15), 50);
  // Running again at tick 14 starts a fresh count from the record.
  s = { ...s, lifecycle: 'running' };
  observeElapsed([s], baselines, 14);
  assert.equal(displayedElapsed(s, baselines, 14), 50);
  assert.equal(displayedElapsed(s, baselines, 18), 54);
  // An elapsed_s change re-bases the display on the new record.
  s = { ...s, elapsed_s: 200 };
  observeElapsed([s], baselines, 20);
  assert.equal(displayedElapsed(s, baselines, 25), 205);
});

test('forward observations rebase display ticks even within the same elapsed second', () => {
  const baselines = new Map();
  const s = { id: 's', lifecycle: 'running', elapsed_s: 10, observed_at: '2026-10-22T12:00:00Z' };
  observeElapsed([s], baselines, 0);
  assert.equal(displayedElapsed(s, baselines, 2), 12);
  const observed = { ...s, elapsed_s: 12, observed_at: '2026-10-22T12:00:02Z' };
  observeElapsed([observed], baselines, 2);
  assert.equal(displayedElapsed(observed, baselines, 3), 13, 'recorded seconds are not counted twice');
  const fractional = { ...observed, observed_at: '2026-10-22T12:00:02.900Z' };
  observeElapsed([fractional], baselines, 3);
  assert.equal(displayedElapsed(fractional, baselines, 3), 12);
  assert.equal(displayedElapsed(fractional, baselines, 4), 13);
});

test('non-running and unknown elapsed are untouched by ticks', () => {
  const baselines = new Map();
  const sessions = [
    { id: 'n1', lifecycle: 'idle', elapsed_s: 30 },
    { id: 'n2', lifecycle: 'running', elapsed_s: null },
    { id: 'n3', lifecycle: 'ended', elapsed_s: null },
  ];
  observeElapsed(sessions, baselines, 7);
  assert.equal(displayedElapsed(sessions[0], baselines, 99), 30);
  assert.equal(displayedElapsed(sessions[1], baselines, 99), null);
  assert.equal(displayedElapsed(sessions[2], baselines, 99), null);
  // A session with no recorded baseline shows only its record.
  assert.equal(displayedElapsed({ id: 'new', lifecycle: 'running', elapsed_s: 5 }, baselines, 99), 5);
});
