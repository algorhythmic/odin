// Unit tests for presentation helpers: friendly model names and
// providers (src/models.js) and stored-preference validation
// (src/prefs.js). Run by Node's built-in test runner: npm run test:unit.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { friendlyModelName, providerFor } from '../src/models.js';
import { cleanPrefs } from '../src/prefs.js';

test('known model ids get friendly names', () => {
  assert.equal(friendlyModelName('claude-opus-5-5'), 'Opus 5.5');
  assert.equal(friendlyModelName('claude-sonnet-5-5'), 'Sonnet 5.5');
  assert.equal(friendlyModelName('claude-haiku-5-5'), 'Haiku 5.5');
  assert.equal(friendlyModelName('claude-fable-5-1'), 'Fable 5.1');
});

test('unknown model ids are shown as-is and missing models stay unknown', () => {
  assert.equal(friendlyModelName('gpt-codex (synthetic)'), 'gpt-codex (synthetic)');
  assert.equal(friendlyModelName('claude-opus-9-9'), 'claude-opus-9-9');
  assert.equal(friendlyModelName(null), 'model unknown');
  assert.equal(friendlyModelName(undefined), 'model unknown');
  assert.equal(friendlyModelName(''), 'model unknown');
});

test('providers come from the model id and are never guessed', () => {
  assert.equal(providerFor('claude-opus-5-5'), 'anthropic');
  assert.equal(providerFor('claude-fable-5-1'), 'anthropic');
  assert.equal(providerFor('gpt-codex (synthetic)'), 'openai');
  assert.equal(providerFor('o4-mini'), 'openai');
  assert.equal(providerFor('mistral-large-2'), 'unknown');
  assert.equal(providerFor(null), 'unknown');
  assert.equal(providerFor(undefined), 'unknown');
  assert.equal(providerFor(42), 'unknown');
});

test('preference validation keeps documented fields and defaults the rest', () => {
  assert.deepEqual(cleanPrefs(null), { mode: 'tree', collapsed: {}, showRelations: true, theme: 'dark' });
  assert.deepEqual(cleanPrefs('list'), { mode: 'tree', collapsed: {}, showRelations: true, theme: 'dark' });
  assert.deepEqual(
    cleanPrefs({ mode: 'list', showRelations: false, theme: 'light', collapsed: { p1: ['s1', 's2'] } }),
    { mode: 'list', collapsed: { p1: ['s1', 's2'] }, showRelations: false, theme: 'light' },
  );
});

test('theme validation accepts only dark and light; dark is the default', () => {
  assert.equal(cleanPrefs({ theme: 'light' }).theme, 'light');
  assert.equal(cleanPrefs({ theme: 'dark' }).theme, 'dark');
  for (const bad of ['neon', '', null, undefined, 1, true, {}]) {
    assert.equal(cleanPrefs({ theme: bad }).theme, 'dark', JSON.stringify(bad));
  }
});

test('collapsed and showRelations validation is unchanged by the theme field', () => {
  assert.deepEqual(cleanPrefs({ collapsed: { p: ['a', 7, null] } }).collapsed, { p: ['a'] });
  assert.deepEqual(cleanPrefs({ collapsed: 'x' }).collapsed, {});
  assert.equal(cleanPrefs({ showRelations: false }).showRelations, false);
  assert.equal(cleanPrefs({ showRelations: 'no' }).showRelations, true);
});
