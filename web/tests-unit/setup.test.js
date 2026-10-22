import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createSetupStore, STEPS } from '../src/setup.js';
import { friendlyModelName } from '../src/models.js';
const fixture = JSON.parse(readFileSync(new URL('../fixtures/setup.json', import.meta.url)));
const store = (options) => createSetupStore(fixture, options);
const blocking = (s) => s.getState().notes.filter((n) => n.kind === 'blocking');
const sharing = (s) => s.getState().notes.filter((n) => n.kind === 'info');

// These are configuration rules, not claims about a live harness.
test('the default draft starts at roles, with three completed steps', () => {
  const s = store();
  assert.equal(s.getState().progress, 3);
  assert.equal(s.firstIncomplete(), 'roles');
  assert.equal(s.getState().dirty, false);
  assert.equal(s.getState().draft.roles.executive.lineage, 'executive-login');
  assert.equal(friendlyModelName('gpt-6.1-sol'), 'GPT-6.1 Sol');
  assert.equal(friendlyModelName('gpt-6-mini'), 'GPT-6 Mini');
});
test('fresh configuration has no connected sign-in, enabled harness or completed step', () => {
  const s = store({ fresh: true });
  assert.equal(s.getState().progress, 0);
  assert.equal(s.firstIncomplete(), 'providers');
  for (const p of s.getState().draft.providers) for (const l of p.lineages) assert.equal(l.status, 'not_connected');
  assert.equal(s.canContinue('providers'), false);
  assert.equal(s.setHarness('claude-code', true), false);
  assert.equal(s.completeStep('providers'), false);
  assert.equal(s.apply(), false);
  assert.ok(blocking(s).some((n) => n.message.includes('no connected sign-in')));
});
test('sign-in waits for explicit synthetic completion and unsupported providers cannot connect', () => {
  const s = store({ fresh: true });
  s.completeSignIn('anthropic', 'executive-login');
  assert.equal(s.canContinue('providers'), false);
  s.connect('anthropic', 'executive-login');
  assert.equal(s.getState().draft.providers[0].lineages[0].status, 'waiting');
  assert.equal(s.canContinue('providers'), false);
  s.completeSignIn('anthropic', 'executive-login');
  assert.equal(s.canContinue('providers'), true);
  assert.equal(s.completeStep('providers'), true);
  assert.equal(s.getState().progress, 1);
  assert.equal(s.addLineage('google'), undefined);
  assert.equal(s.setHarness('pi-rpc', true), false);
});
test('new sign-ins are labelled independently and do not alter the fixture', () => {
  const s = store();
  const id = s.addLineage('anthropic');
  s.setLineageLabel('anthropic', id, 'Extra delegation');
  const l = s.getState().draft.providers[0].lineages.at(-1);
  assert.equal(l.label, 'Extra delegation');
  assert.equal(l.status, 'not_connected');
  assert.equal(fixture.providers[0].lineages.length, 2);
  const inspect = (v) => {
    for (const [k, value] of Object.entries(v)) {
      assert.doesNotMatch(k, /token|secret|key/i);
      if (value && typeof value === 'object') inspect(value);
    }
  };
  inspect(s.getState().draft);
});
test('all three presets reproduce the fixture and a per-cell change makes Custom', () => {
  const s = store();
  for (const id of Object.keys(fixture.presets)) {
    s.applyPreset(id);
    assert.deepEqual(s.getState().draft.roles, fixture.presets[id].roles);
    assert.equal(s.getState().draft.preset, id);
  }
  s.changeRole('implementer', 'effort', 'medium');
  assert.equal(s.getState().draft.preset, 'custom');
  s.applyPreset('cross_family');
  assert.equal(s.getState().draft.preset, 'cross_family');
});
test('executive on Codex blocks apply with an explicit reason', () => {
  const s = store();
  s.changeRole('executive', 'harness', 'codex');
  assert.ok(blocking(s).some((n) => n.role === 'executive' && n.message.includes('must use Claude Code')));
  assert.equal(s.apply(), false);
  assert.equal(s.getState().appliedOnce, false);
  s.changeRole('executive', 'harness', 'claude-code');
  assert.equal(s.apply(), true);
});
test('same-family review warns across different models but never blocks', () => {
  const s = store();
  s.changeRole('independent_review', 'model', 'gpt-6-mini');
  assert.ok(s.getState().notes.some((n) => (
    n.kind === 'warning' && n.message === 'Same model family as the author; review is less independent'
  )));
  assert.equal(blocking(s).length, 0);
  assert.equal(s.apply(), true);
  s.changeRole('independent_review', 'harness', 'claude-code');
  assert.equal(s.getState().notes.some((n) => n.kind === 'warning'), false);
});
test('lineage capacity produces one nonblocking summary for each shared sign-in', () => {
  const s = store();
  const info = sharing(s);
  assert.equal(info.length, 2);
  assert.equal(new Set(info.map((n) => n.lineage)).size, info.length);
  assert.ok(info.every((n) => n.role === null));
  assert.deepEqual(info.map((n) => [n.lineage, n.message]), [
    ['delegation-login', '2 roles share Delegation login; limit 1 concurrent turn. Roles interleave.'],
    ['evaluator-codex-login', '7 roles share Evaluator Codex login; limit 1 concurrent turn. Roles interleave.'],
  ]);
  assert.equal(blocking(s).length, 0);
  assert.equal(s.apply(), true);
});
test('lineage summaries follow role assignments and disappear below the capacity', () => {
  const s = store();
  s.changeRole('workstream_orchestrator', 'lineage', 'executive-login');
  let info = sharing(s);
  assert.equal(info.length, 2);
  assert.equal(info.some((n) => n.lineage === 'delegation-login'), false);
  assert.ok(info.some((n) => n.lineage === 'executive-login' && n.message.startsWith('2 roles share Executive login;')));
  s.changeRole('implementer', 'harness', 'claude-code');
  info = sharing(s);
  assert.equal(info.length, 2);
  assert.equal(new Set(info.map((n) => n.lineage)).size, info.length);
  assert.ok(info.every((n) => n.role === null));
  assert.ok(info.some((n) => n.lineage === 'executive-login' && n.message.startsWith('3 roles share Executive login;')));
  assert.ok(info.some((n) => n.lineage === 'evaluator-codex-login' && n.message.startsWith('6 roles share Evaluator Codex login;')));
  assert.equal(blocking(s).length, 0);
});
test('roles require an enabled harness and a connected lineage from its provider', () => {
  const s = store();
  s.setHarness('codex', false);
  assert.equal(s.apply(), false);
  assert.ok(blocking(s).some((n) => n.message.startsWith('Enable this harness')));
  s.setHarness('codex', true);
  s.changeRole('implementer', 'lineage', 'executive-login');
  assert.equal(s.apply(), false);
  assert.ok(blocking(s).some((n) => n.role === 'implementer' && n.message.startsWith('Choose a connected sign-in')));
});
test('harness and model changes keep dependent choices compatible', () => {
  const s = store();
  s.changeRole('implementer', 'harness', 'claude-code');
  let r = s.getState().draft.roles.implementer;
  assert.equal(r.lineage, 'executive-login');
  assert.equal(r.model, 'claude-opus-5-5');
  s.changeRole('implementer', 'effort', 'max');
  s.changeRole('implementer', 'harness', 'codex');
  r = s.getState().draft.roles.implementer;
  assert.ok(fixture.models.codex[0].efforts.includes(r.effort));
  s.changeRole('implementer', 'model', 'unknown');
  assert.equal(s.apply(), false);
});
test('apply snapshots the draft, discard restores it, and a new store resets everything', () => {
  const s = store();
  let updates = 0;
  const unsubscribe = s.subscribe(() => updates++);
  s.changeRole('implementer', 'effort', 'medium');
  assert.equal(s.getState().dirty, true);
  assert.equal(s.getState().applied.roles.implementer.effort, 'high');
  assert.equal(s.apply(), true);
  assert.equal(s.getState().complete, true);
  assert.equal(s.getState().progress, 4);
  assert.equal(s.getState().dirty, false);
  s.changeRole('implementer', 'effort', 'low');
  s.discard();
  assert.equal(s.getState().draft.roles.implementer.effort, 'medium');
  assert.equal(s.getState().dirty, false);
  assert.equal(updates, 4);
  unsubscribe(); s.applyPreset('opus_led'); assert.equal(updates, 4);
  assert.equal(store().getState().draft.roles.implementer.effort, 'high');
});
test('a fresh draft can complete setup and apply without bypassing prerequisites', () => {
  const s = store({ fresh: true });
  for (const p of fixture.providers.filter((p) => p.supported)) {
    for (const l of p.lineages) {
      s.connect(p.id, l.id);
      s.completeSignIn(p.id, l.id);
    }
  }
  s.completeStep('providers');
  s.setHarness('claude-code', true); s.setHarness('codex', true);
  s.completeStep('harnesses'); s.completeStep('models'); s.applyPreset('cross_family');
  assert.equal(s.getState().progress, 3);
  s.completeStep('roles');
  assert.equal(s.getState().progress, 3);
  assert.equal(s.apply(), true);
  assert.deepEqual(s.getState().completed, Object.fromEntries(STEPS.map((s) => [s, true])));
});

test('an invalid settings draft does not undo applied setup completion', () => {
  const s = store();
  s.apply();
  s.changeRole('executive', 'harness', 'codex');
  assert.equal(s.apply(), false);
  assert.equal(s.getState().complete, true);
  assert.equal(s.getState().progress, 4);
  assert.equal(s.getState().applied.roles.executive.harness, 'claude-code');
  s.discard();
  assert.equal(s.getState().complete, true);
  assert.equal(s.getState().dirty, false);
});
