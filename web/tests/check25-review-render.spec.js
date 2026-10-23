// Synthetic prototype regressions from the independent rendering review.
import { test, expect } from '@playwright/test';
import { PID, snapshot } from './helpers.js';

const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const apply = (page) => page.getByRole('button', { name: 'Apply next synthetic update' }).evaluate((el) => el.click());
const focused = (page) => page.evaluate(() => document.activeElement?.dataset.sessionId);

// Change cloned synthetic inputs without adding a production test interface.
async function patchFixture(page, patches = [], additions = []) {
  await page.addInitScript(({ patches, additions }) => {
    const clone = window.structuredClone.bind(window);
    window.structuredClone = (value, ...args) => {
      const result = clone(value, ...args);
      if (result?.sessions && result?.projects) {
        result.sessions = result.sessions.map((s) => ({ ...s, ...patches.find((p) => p.id === s.id) }));
        result.sessions.push(...additions);
      }
      return result;
    };
  }, { patches, additions });
}

test('1100×900 all-relationship replay survives the first five deliveries and retirement', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1100, height: 900 });
  await page.goto('/#/agents');
  await page.getByRole('button', { name: 'Key', exact: true }).click();
  await page.getByRole('checkbox', { name: 'Show all relationships' }).check();
  for (let n = 0; n < 5; n++) await apply(page);
  await expect(card(page, 'ses-review-integ')).toHaveCount(0);
  await expect(page.getByTestId('tree-view')).toBeVisible();
  await expect(page.locator('.relation-edge[data-from="ses-review-integ"]')).toHaveCount(0);
  await expect(page.locator('.tree-overlays .relation-edge')).not.toHaveCount(0);
  expect(errors).toEqual([]);
  await page.goto('/#/sessions/ses-review-integ');
  await expect(page.getByTestId('detail-relationships')).toContainText('reviews');
});

for (const reducedMotion of ['no-preference', 'reduce']) {
  test(`list focus follows a retiring row and arrows keep working (${reducedMotion})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion });
    await page.goto('/#/agents');
    await page.getByRole('button', { name: 'List', exact: true }).click();
    for (let n = 0; n < 4; n++) await apply(page);
    const list = page.getByTestId('list-view');
    const ids = await list.getByRole('treeitem').evaluateAll((els) => els.map((el) => el.dataset.sessionId));
    const i = ids.indexOf('ses-review-integ');
    const retiring = list.locator('[data-session-id="ses-review-integ"]');
    await retiring.focus();
    await apply(page);
    await expect(retiring).toHaveCount(0);
    await expect.poll(() => focused(page)).toBe(ids[i + 1]);
    await page.keyboard.press('ArrowDown');
    await expect.poll(() => focused(page)).toBe(ids[i + 2]);
  });
}

test('retirement leaves focus on a control outside the list', async ({ page }) => {
  await page.goto('/#/agents');
  await page.getByRole('button', { name: 'List', exact: true }).click();
  for (let n = 0; n < 4; n++) await apply(page);
  await page.getByTestId('list-view').locator('[data-session-id="ses-review-integ"]').focus();
  const button = page.getByRole('button', { name: 'Apply next synthetic update' });
  await button.click();
  await expect(page.getByTestId('list-view').locator('[data-session-id="ses-review-integ"]')).toHaveCount(0);
  await expect(button).toBeFocused();
});

test('compact cards keep freshness, ancestry and retained retirement visible without expansion', async ({ page }) => {
  const template = snapshot.sessions.find((s) => s.id === 'ses-docs-01');
  await patchFixture(page, [
    { id: 'ses-mal-cycle-a', lifecycle: 'retired' },
  ], [
    { ...template, id: 'review-imported', lifecycle: 'idle', provenance: 'imported', parent_session_id: null },
    { ...template, id: 'review-cross', lifecycle: 'idle', parent_session_id: 'ses-pin-exec' },
    { ...template, id: 'review-stale', lifecycle: 'idle', stale: true, observed_at: '2026-10-21T06:07:00Z' },
  ]);
  await page.goto('/#/agents');
  for (const [id, text, full] of [
    ['ses-ops-01', 'Stale · 06:05 UTC', 'Stale observation'],
    ['review-stale', 'Stale · 06:07 UTC', 'Last observed 06:07 UTC'],
    ['ses-mal-cycle-b', 'Parent cycle', 'Parent cycle in records'],
    ['ses-pin-audit', 'Parent outside view', 'Parent not in this project view'],
    ['review-imported', 'Imported · parent unknown', 'Imported — parent unknown'],
    ['review-cross', 'Parent in another project', 'Parent in another project'],
    ['ses-mal-cycle-a', 'Retired · kept for live work', 'Retired · kept for live work'],
  ]) {
    const node = card(page, id);
    await expect(node).toHaveAttribute('data-card-expanded', 'false');
    await expect(node.getByText(text, { exact: true })).toBeVisible();
    await expect(node.locator('.card-title')).toHaveAccessibleName(new RegExp(full));
    await expect(node.locator('.card-title')).toHaveAttribute('title', new RegExp(full));
    expect(await node.getByText(text, { exact: true }).evaluate((el) => {
      const card = el.closest('.card').getBoundingClientRect();
      const box = el.getBoundingClientRect();
      return box.top >= card.top && box.bottom <= card.bottom && el.scrollWidth <= el.clientWidth;
    }), `${id}: qualification fits inside the compact card`).toBe(true);
  }
  await expect(card(page, 'ses-mal-cycle-child')).toHaveAttribute('data-parent', 'ses-mal-cycle-a');
  await expect(card(page, 'ses-ops-01').locator('.card-title')).toHaveAccessibleName(/2026-10-21T06:05:00Z/);
});

test('host offline without a stale flag still shows its observation on the compact card', async ({ page }) => {
  await patchFixture(page, [{ id: 'ses-ops-01', stale: false }]);
  await page.goto('/#/agents');
  const ops = card(page, 'ses-ops-01');
  await expect(ops).toHaveAttribute('data-card-expanded', 'false');
  await expect(ops.getByTestId('last-observed')).toHaveText('Last observed · 06:05 UTC');
});

test('session ID matching the old grouping ID renders and navigates in both layouts', async ({ page }) => {
  const id = `project:${PID}`;
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await patchFixture(page, [], [{ ...snapshot.sessions.find((s) => s.id === 'ses-docs-01'), id }]);
  await page.goto('/#/agents');
  await expect(card(page, id)).toHaveCount(1);
  await expect(page.locator(`[data-testid="project-node"][data-project-id="${PID}"]`)).toHaveCount(1);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  const group = page.locator(`[role="treeitem"][data-node-kind="project"][data-project-id="${PID}"]`);
  const session = page.locator(`[role="treeitem"][data-node-kind="session"][data-session-id="${id}"]`);
  await session.focus();
  await expect(session).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(group).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(session).toHaveCount(0);
  await page.reload();
  await expect(group).toHaveAttribute('aria-expanded', 'false');
  await expect(session).toHaveCount(0);
  await group.focus();
  await page.keyboard.press('ArrowRight');
  await expect(session).toHaveCount(1);
  expect(errors).toEqual([]);
});
