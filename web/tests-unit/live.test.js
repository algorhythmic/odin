// Unit tests for the live-surface helpers (src/live.js): autoplay
// interval scheduling and the header summary counts. Run by Node's
// built-in test runner: npm run test:unit.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  BASE_INTERVAL_MS, SPEEDS, attentionCounts, cleanSpeed, failedSessionIds, intervalFor,
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
