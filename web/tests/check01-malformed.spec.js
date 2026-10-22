// Handoff check 1, malformed and edge records (synthetic): cycles and
// self-parents become labelled roots, empty projects render, unknown token
// usage never becomes zero, and a run is verified only when recorded so.
import { test, expect } from '@playwright/test';
import { sessionUrl, shot, snapshot } from './helpers.js';

const MAL = 'proj-malformed';
const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const edgesOf = (page) => page.locator('path.ancestry-edge').evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));

test('cycle and self-parent sessions are labelled roots, never dropped or given a guessed edge', async ({ page }) => {
  const malformed = snapshot.sessions.filter((s) => s.project_id === MAL);
  await page.goto(`/#/projects/${MAL}`);
  // Every record is shown: nothing in a cycle is dropped.
  await expect(page.getByTestId('session-card')).toHaveCount(malformed.length);
  await expect(page.getByTestId('project-node')).toHaveCount(1);
  for (const id of ['ses-mal-cycle-a', 'ses-mal-cycle-b', 'ses-mal-self']) {
    await expect(card(page, id).getByTestId('lineage-label')).toHaveText('Parent cycle in records');
  }
  // The recorded parent is kept as data; only the non-cycle child attaches.
  await expect(card(page, 'ses-mal-self')).toHaveAttribute('data-parent', 'ses-mal-self');
  expect((await edgesOf(page)).sort()).toEqual(['ses-exec-01>ses-mal-root', 'ses-mal-cycle-a>ses-mal-cycle-child', 'ses-mal-root>ses-mal-attempt']);
  await shot(page, 'malformed-cycles');

  await card(page, 'ses-mal-cycle-b').getByRole('button').first().click();
  await expect(page.getByTestId('started-by')).toHaveText(/ses-mal-cycle-a \(recorded parent is part of a cycle; shown as a root, not inferred\)/);
  await expect(page.getByRole('button', { name: 'Go to parent' })).toBeDisabled();
  await page.goto(sessionUrl('ses-mal-cycle-child', MAL));
  await expect(page.getByTestId('started-by')).toContainText('ses-mal-cycle-a');
  await page.getByRole('button', { name: 'Go to parent' }).click();
  await expect(page).toHaveURL(/sessions\/ses-mal-cycle-a$/);

  // The list view shows the same forest and stays keyboard navigable.
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.locator('[role="treeitem"]')).toHaveCount(malformed.length + 1);
  await expect(page.locator('[role="treeitem"][aria-level="2"]')).toHaveCount(4);
  await page.locator('[role="treeitem"][data-session-id="ses-mal-root"]').focus();
  await page.keyboard.press('End');
  await expect.poll(() => page.evaluate(() => document.activeElement?.dataset.sessionId)).toBe('ses-mal-self');
});

test('an empty project renders an empty forest with finite dimensions', async ({ page }) => {
  await page.goto('/#/projects/proj-empty');
  await expect(page.getByTestId('agent-summary')).toHaveText('0 agents · 0 running');
  await expect(page.getByTestId('session-card')).toHaveCount(0);
  const svg = page.locator('svg.tree-edges');
  for (const attr of ['width', 'height']) {
    const value = Number(await svg.getAttribute(attr));
    expect(Number.isFinite(value), `${attr} is finite`).toBe(true);
    expect(value).toBeGreaterThan(0);
  }
  await expect(page.getByTestId('tree-view')).toHaveAttribute('data-scale', /^(0|1)(\.\d+)?$/);
  // Fit all on an empty forest must not produce NaN or Infinity.
  await page.getByRole('button', { name: 'Fit all' }).click();
  await expect(page.getByText(/Zoom \d+%/)).toBeVisible();
  const html = await page.getByTestId('tree-view').innerHTML();
  expect(html).not.toMatch(/NaN|Infinity/);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.locator('[role="treeitem"]')).toHaveCount(1);
  await shot(page, 'empty-project');
});

test('a branch with no known tokens shows no figure and no Infinity', async ({ page }) => {
  await page.goto(`/#/projects/${MAL}`);
  const text = await page.getByTestId('tree-view').innerText();
  expect(text).not.toMatch(/Infinity|NaN|\$|0 tok/);
  await expect(card(page, 'ses-mal-cycle-a')).toContainText('branch unknown (2)');
});

test('an ended session shows Verified only when the run outcome is recorded as verified', async ({ page }) => {
  // Recorded verified outcome on an ended session.
  await page.goto(sessionUrl('ses-pin-audit', 'proj-contract-pins'));
  await expect(page.getByTestId('detail-state')).toHaveText('Done');
  await expect(page.getByTestId('run-outcome')).toHaveText('Verified');
  // Ended without a verified record: never shown as verified.
  await page.goto(sessionUrl('ses-worker-a2'));
  await expect(page.getByTestId('run-outcome')).toHaveText('Session ended — run not verified (Not verified)');
  await page.goto(sessionUrl('ses-helper-01'));
  await expect(page.getByTestId('detail-state')).toHaveText('Stopped');
  await expect(page.getByTestId('run-outcome')).toHaveText('Session ended — run not verified (Outcome unknown)');
});

test('"Previous attempt" naming a missing session opens a not-found response', async ({ page }) => {
  await page.goto(sessionUrl('ses-mal-attempt', MAL));
  await expect(card(page, 'ses-mal-attempt').getByTestId('lineage-label')).toHaveText('Attempt 2 (after ses-mal-gone)');
  await page.getByRole('button', { name: 'Previous attempt' }).click();
  await expect(page).toHaveURL(/sessions\/ses-mal-gone$/);
  await expect(page.getByTestId('not-found')).toContainText('Session not found');
  await expect(page.getByTestId('not-found')).toContainText('ses-mal-gone');
});
