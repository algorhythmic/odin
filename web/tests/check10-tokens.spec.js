// Pass 4 brief item 2 (synthetic): token usage replaces cost. No dollar
// figure may render anywhere; a known session shows its exact compact
// headline (uncached input + cache write + output — cache reads excluded),
// an unknown session shows "unknown", and branch totals count unknown
// children. The expected strings are recomputed from the fixture, not
// hardcoded.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot, snapshot } from './helpers.js';

const byId = new Map(snapshot.sessions.map((s) => [s.id, s]));

// Same rules as src/data.js headlineTokens/compactTokens.
const headline = (s) => {
  const t = s.tokens;
  if (!t || t.basis === 'unknown') return null;
  const counts = [t.uncached_input, t.cache_read, t.cache_write, t.output];
  return counts.every(Number.isInteger) ? t.uncached_input + t.cache_write + t.output : null;
};
const compact = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : `${n}`);
const headlineText = (s) => {
  const h = headline(s);
  return h === null ? 'unknown' : `${s.tokens.basis === 'estimate' ? 'est. ' : ''}${compact(h)} tok`;
};

test('no dollar figure anywhere on the portfolio', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('workspace')).toBeVisible();
  expect(await page.locator('body').innerText()).not.toContain('$');
});

test('a known session shows its exact compact headline on the card and in the detail panel', async ({ page }) => {
  await page.goto(sessionUrl('ses-exec-01'));
  const card = page.locator('[data-testid="session-card"][data-session-id="ses-exec-01"]');
  await expect(card.getByTestId('own-tokens')).toHaveText('42.2k tok');
  const panel = page.getByTestId('detail-panel');
  await expect(panel.getByTestId('detail-own-tokens')).toHaveText('42.2k tok');
  // The four-way split is labelled, cache reads included but separate.
  await expect(panel).toContainText('Headline (excl. cache reads)');
  await expect(panel.getByTestId('detail-uncached-input')).toHaveText('9.0k tok');
  await expect(panel.getByTestId('detail-cache-read')).toHaveText('120.0k tok');
  await expect(panel.getByTestId('detail-cache-write')).toHaveText('21.0k tok');
  await expect(panel.getByTestId('detail-output')).toHaveText('12.2k tok');
  // The token budget replaces the dollar budget and is marked as requested.
  await expect(panel).toContainText('2.0M tok (requested');
  // And no dollar figure anywhere on the page.
  expect(await page.locator('body').innerText()).not.toContain('$');
  await shot(page, 'tokens-detail');
});

test('an unknown session shows unknown, never a figure', async ({ page }) => {
  await page.goto(sessionUrl('ses-helper-01'));
  const card = page.locator('[data-testid="session-card"][data-session-id="ses-helper-01"]');
  await expect(card.getByTestId('own-tokens')).toHaveText('unknown');
  const panel = page.getByTestId('detail-panel');
  await expect(panel.getByTestId('detail-own-tokens')).toHaveText('unknown');
  for (const part of ['detail-uncached-input', 'detail-cache-read', 'detail-cache-write', 'detail-output']) {
    await expect(panel.getByTestId(part)).toHaveText('unknown');
  }
});

test('branch totals and the project total sum own tokens once and count unknowns', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  // ses-worker-a2 is an estimate with one unknown child (ses-helper-01).
  const a2 = page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]');
  await expect(a2.getByTestId('branch-tokens')).toHaveText(`branch ${headlineText(byId.get('ses-worker-a2'))} + unknown (1)`);
  // The project header total sums every session's own headline once.
  const sessions = snapshot.sessions.filter((s) => s.project_id === PID);
  let known = 0;
  let unknown = 0;
  let estimate = false;
  for (const s of sessions) {
    const h = headline(s);
    if (h === null) unknown += 1;
    else { known += h; estimate = estimate || s.tokens.basis === 'estimate'; }
  }
  const expected = `${estimate ? 'est. ' : ''}${compact(known)} tok + unknown (${unknown})`;
  expect(unknown).toBeGreaterThan(0);
  await expect(page.getByTestId('project-tokens')).toHaveText(expected.replace(/unknown \((\d+)\)/, '$1 unknown'));
});
