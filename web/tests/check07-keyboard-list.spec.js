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
