import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  admissionBand, bandTicks, connectedUsage, mostConstrainedSample, resetLabel, windowName, worstBand,
} from '../src/usage.js';
import { createSetupStore } from '../src/setup.js';
const fixture = JSON.parse(readFileSync(new URL('../fixtures/setup.json', import.meta.url)));
const ceilings = fixture.usage.band_ceilings;
const sample = (label, n) => ({ label, status: 'available', utilization_percent: n });

test('fixture ceilings match exactly the W3a table', () => {
  assert.deepEqual(ceilings, {
    'claude.five_hour': 95, 'claude.weekly': 90, 'claude.weekly.fable': 95, 'codex.five_hour': 95, 'codex.weekly': 90,
  });
});
test('every band boundary is inclusive, including decimals on either side', () => {
  for (const [label, ceiling] of Object.entries(ceilings)) {
    assert.deepEqual(bandTicks(label, ceilings), [ceiling - 10, ceiling - 5, ceiling]);
    for (const [n, band] of [
      [0, 'clear'], [ceiling - 10.01, 'clear'], [ceiling - 10, 'wind_down'],
      [ceiling - 5.01, 'wind_down'], [ceiling - 5, 'ordinary_stop'],
      [ceiling - 0.01, 'ordinary_stop'], [ceiling, 'handoff_only'], [100, 'handoff_only'],
    ]) assert.equal(admissionBand(sample(label, n), ceilings), band, `${label} ${n}`);
  }
});
test('unknown labels, unavailable probes and malformed utilization never contribute a band', () => {
  assert.equal(admissionBand(sample('claude.weekly.opus', 99), ceilings), null);
  assert.equal(admissionBand(sample('toString', 99), ceilings), null);
  assert.deepEqual(bandTicks('claude.weekly.opus', ceilings), []);
  for (const n of [null, undefined, NaN, Infinity, -1, 101, '91']) {
    assert.equal(admissionBand(sample('codex.five_hour', n), ceilings), null);
  }
  assert.equal(admissionBand({ ...sample('codex.five_hour', 99), status: 'unavailable' }, ceilings), null);
  assert.equal(admissionBand(null, ceilings), null);
  assert.equal(admissionBand(sample('codex.five_hour', 99), null), null);
});
test('most constrained window compares admission severity before utilization', () => {
  const ordinary = sample('claude.five_hour', 94);
  const handoff = sample('claude.weekly', 90);
  assert.equal(mostConstrainedSample([ordinary, handoff], ceilings), handoff);
  assert.equal(mostConstrainedSample([handoff, ordinary], ceilings), handoff);
  const clear = sample('claude.five_hour', 84);
  const windDown = sample('claude.weekly', 80);
  assert.equal(mostConstrainedSample([clear, windDown], ceilings), windDown);
});
test('most constrained window breaks equal admission bands by utilization', () => {
  const lower = sample('claude.weekly', 87);
  const higher = sample('claude.five_hour', 92);
  assert.equal(mostConstrainedSample([lower, higher], ceilings), higher);
  assert.equal(mostConstrainedSample([higher, lower], ceilings), higher);
});
test('most constrained window skips unavailable and malformed samples', () => {
  const available = sample('codex.weekly', 38);
  const invalid = [
    null, {}, { ...sample('codex.five_hour', 99), status: 'unavailable' },
    ...[null, undefined, NaN, Infinity, -1, 101, '91'].map((n) => sample('codex.five_hour', n)),
  ];
  assert.equal(mostConstrainedSample([...invalid, available], ceilings), available);
  assert.equal(mostConstrainedSample(invalid, ceilings), null);
  assert.equal(mostConstrainedSample([], ceilings), null);
  assert.equal(mostConstrainedSample(undefined, ceilings), null);
});
test('window names are friendly while unknown labels remain unchanged', () => {
  for (const provider of ['claude', 'codex']) {
    assert.equal(windowName(`${provider}.five_hour`), '5-hour');
    assert.equal(windowName(`${provider}.weekly`), 'Weekly');
  }
  assert.equal(windowName('claude.weekly.fable'), 'Weekly · Fable');
  assert.equal(windowName('claude.weekly.opus'), 'Weekly · Opus');
  for (const label of ['custom.monthly', 'codex.weekly.fable', 'claude.daily']) {
    assert.equal(windowName(label), label);
  }
});
test('connected usage follows sign-in edits, disconnect, discard and explicit completion', () => {
  const store = createSetupStore(fixture);
  let state = store.getState();
  assert.equal(connectedUsage(state).length, 3);
  assert.equal(worstBand(connectedUsage(state), ceilings), 'ordinary_stop');
  store.disconnect('openai', 'evaluator-codex-login');
  assert.equal(connectedUsage(store.getState()).length, 2);
  assert.equal(worstBand(connectedUsage(store.getState()), ceilings), 'wind_down');
  store.discard();
  assert.equal(connectedUsage(store.getState()).length, 3);
  const id = store.addLineage('anthropic');
  store.connect('anthropic', id);
  assert.equal(connectedUsage(store.getState()).length, 3);
  store.completeSignIn('anthropic', id);
  assert.equal(connectedUsage(store.getState()).length, 4);
  assert.equal(connectedUsage(store.getState()).at(-2).usage, undefined);
  assert.equal(worstBand([], ceilings), null);
  assert.deepEqual(fixture.providers[0].lineages.length, 2);
});
test('reset intervals use sample observation with unknown and elapsed resets explicit', () => {
  assert.equal(resetLabel(fixture.usage.lineages['executive-login'].samples[0]), 'resets in 2h 10m');
  for (const [resets_at, label] of [
    ['2026-10-23T18:00:00Z', 'resets in 1d'],
    ['2026-10-25T18:00:00Z', 'resets in 3d'],
    ['2026-10-25T22:00:00Z', 'resets in 3d 4h'],
    ['2026-10-22T18:45:00Z', 'resets in 0h 45m'],
  ]) assert.equal(resetLabel({ observed_at: '2026-10-22T18:00:00Z', resets_at }), label);
  assert.equal(resetLabel({}), 'reset unknown');
  assert.equal(resetLabel({ observed_at: '2026-10-22T18:00:00Z', resets_at: '2026-10-22T17:00:00Z' }), 'resets in 0h 0m');
});
