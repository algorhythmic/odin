// Handoff check 7: keyboard navigation through an equivalent list, state as text,
// and narrow layouts that keep conversation and decision actions usable.
import { test, expect } from '@playwright/test';
import { PID, shot, snapshot } from './helpers.js';

const { sessions } = snapshot;

const LABELS = ['Running', 'Waiting for input', 'Idle', 'Ended', 'Retired', 'Host offline'];
const focusedId = (page) => page.evaluate(() => document.activeElement?.dataset.sessionId);

test('list view is keyboard navigable and conveys state as text', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  const tree = page.getByRole('tree', { name: 'Sessions by ancestry' });
  await expect(tree).toBeVisible();
  const items = tree.getByRole('treeitem');
  await expect(items).toHaveCount(sessions.filter((s) => s.project_id === PID).length);

  // Every row carries a text state label, not only a colour.
  for (const row of await items.all()) {
    await expect(row.getByTestId('state-label')).toHaveText(new RegExp(`^(${LABELS.join('|')})$`));
  }

  // Tab into the tree: the roving tab stop is the first root.
  await page.getByRole('button', { name: 'List', exact: true }).focus();
  await page.keyboard.press('Tab');
  await expect.poll(() => focusedId(page)).toBe('ses-exec-01');
  await expect(tree.getByRole('treeitem', { selected: false }).first()).toHaveAttribute('tabindex', '0');

  await page.keyboard.press('ArrowDown');
  await expect.poll(() => focusedId(page)).toBe('ses-integ-01');
  await page.keyboard.press('ArrowLeft'); // collapse integration owner
  await expect(page.locator('[role="treeitem"][data-session-id="ses-integ-01"]')).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('[role="treeitem"][data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await page.keyboard.press('ArrowRight'); // expand again
  await expect(page.locator('[role="treeitem"][data-session-id="ses-worker-a2"]')).toHaveCount(1);
  await page.keyboard.press('ArrowRight'); // move to first child
  await expect.poll(() => focusedId(page)).toBe('ses-worker-a1');
  await page.keyboard.press('ArrowDown');
  await expect.poll(() => focusedId(page)).toBe('ses-worker-a2');
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => focusedId(page)).toBe('ses-helper-01');
  await page.keyboard.press('ArrowLeft'); // leaf: go to parent
  await expect.poll(() => focusedId(page)).toBe('ses-worker-a2');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/sessions\/ses-worker-a2$/);
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(page.locator('[role="treeitem"][data-session-id="ses-worker-a2"]')).toHaveAttribute('aria-selected', 'true');
  await expect.poll(() => focusedId(page)).toBe('ses-worker-a2');
  await page.keyboard.press('End');
  await expect.poll(() => focusedId(page)).toBe('ses-imported-01');
  await page.keyboard.press('Home');
  await expect.poll(() => focusedId(page)).toBe('ses-exec-01');
  await shot(page, 'list-view');
});

test('tree cards also carry text state labels', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await page.getByRole('button', { name: 'Tree', exact: true }).click();
  const cards = page.getByTestId('session-card');
  for (const card of await cards.all()) {
    await expect(card.getByTestId('state-label')).toHaveText(new RegExp(`^(${LABELS.join('|')})$`));
  }
  await expect(page.locator('[data-session-id="ses-review-exec"]')).toContainText('Needs input');
  await expect(page.locator('[data-session-id="ses-ops-01"]')).toContainText('Stale');
});

test('narrow layout defaults to the list and keeps actions usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#/projects/${PID}/sessions/ses-review-exec`);
  await expect(page.getByTestId('workspace')).toHaveAttribute('data-mode', 'list');
  await expect(page.getByTestId('list-view')).toBeVisible();
  await expect(page.getByTestId('tree-view')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Tree', exact: true })).toHaveCount(0);
  await expect(page.getByTestId('detail-panel')).toBeVisible();
  await expect(page.getByTestId('pending-decision')).toBeVisible();
  const composer = page.getByLabel('Message');
  await composer.scrollIntoViewIfNeeded();
  await expect(composer).toBeVisible();
  const actions = page.getByTestId('actions-note');
  await actions.scrollIntoViewIfNeeded();
  await expect(actions).toBeVisible();
  // No horizontal overflow at phone width.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await shot(page, 'narrow-list');
});

test('list view rows expand and collapse with the pointer on the large synthetic set', async ({ page }) => {
  await page.goto('/?dataset=large#/projects/proj-large-synthetic');
  await page.getByRole('button', { name: 'List', exact: true }).click();
  const tree = page.getByRole('tree', { name: 'Sessions by ancestry' });
  const items = tree.getByRole('treeitem');
  // Branches start collapsed above 200 sessions: only the 40 roots show.
  await expect(items).toHaveCount(40);
  const first = items.first();
  await expect(first).toHaveAttribute('aria-expanded', 'false');
  await first.getByTestId('list-toggle').click();
  await expect(first).toHaveAttribute('aria-expanded', 'true');
  const id = await first.getAttribute('data-session-id');
  await expect(tree.locator(`[role="treeitem"][data-parent="${id}"]`).first()).toBeVisible();
  // The toggle does not select the row.
  await expect(first).toHaveAttribute('aria-selected', 'false');
  await first.getByTestId('list-toggle').click();
  await expect(first).toHaveAttribute('aria-expanded', 'false');
  await expect(tree.locator(`[role="treeitem"][data-parent="${id}"]`)).toHaveCount(0);
});

// Card footers wrap instead of clipping: the branch cost text stays whole
// and inside its card at a wide and a just-above-narrow viewport.
for (const width of [1280, 800]) {
  test(`card footers show the whole branch cost at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/#/projects/${PID}`);
    const costs = page.getByTestId('branch-cost');
    await expect(costs.first()).toBeVisible();
    expect(await costs.count()).toBeGreaterThan(2);
    const clipped = await costs.evaluateAll((els) => els.flatMap((el) => {
      const card = el.closest('[data-testid="session-card"]').getBoundingClientRect();
      const r = el.getBoundingClientRect();
      const ok = el.scrollWidth <= el.clientWidth + 1 && r.right <= card.right + 1 && r.bottom <= card.bottom + 1 && r.left >= card.left - 1;
      return ok ? [] : [`${el.closest('[data-session-id]').dataset.sessionId}: ${el.textContent}`];
    }));
    expect(clipped).toEqual([]);
    await expect(page.locator('[data-testid="session-card"][data-session-id="ses-integ-01"]').getByTestId('branch-cost'))
      .toHaveText(/^branch .*\+ unknown \(\d+\)$/);
    if (width === 800) await shot(page, 'card-footers-800');
  });
}

test('the transcript pager keeps keyboard focus across page loads', async ({ page }) => {
  await page.goto(`/#/projects/${PID}/sessions/ses-worker-a2`);
  const pager = page.getByTestId('transcript-pager');
  await expect(pager).toContainText('Page 1 of 2');
  const later = pager.getByRole('button', { name: 'Later' });
  const earlier = pager.getByRole('button', { name: 'Earlier' });
  await expect(earlier).toHaveAttribute('aria-disabled', 'true');
  await later.focus();
  await page.keyboard.press('Enter');
  await expect(pager).toHaveCount(1); // still mounted while page 2 loads
  await expect(pager).toContainText('Page 2 of 2');
  await expect(later).toBeFocused();
  await expect(later).toHaveAttribute('aria-disabled', 'true');
  await page.keyboard.press('Enter'); // at the last page: nothing happens
  await expect(pager).toContainText('Page 2 of 2');
  await page.keyboard.press('Shift+Tab');
  await expect(earlier).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(pager).toContainText('Page 1 of 2');
  await expect(earlier).toBeFocused();
  await expect(page.getByTestId('transcript')).toContainText('Progress note 1:');
});
