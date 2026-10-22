// Handoff check 4 (synthetic): stale and host_offline sessions say when they
// were last observed; the history view keeps attempts and resumptions apart.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot } from './helpers.js';

test('stale and host-offline sessions show their last observed time', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const ops = page.locator('[data-testid="session-card"][data-session-id="ses-ops-01"]');
  await expect(ops.getByTestId('state-label')).toHaveText('Host offline');
  await expect(ops).toContainText('Stale');
  await expect(ops.getByTestId('last-observed')).toHaveText('Last observed 06:05 UTC');
  // Fresh sessions carry no last-observed warning.
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-exec-01"]').getByTestId('last-observed')).toHaveCount(0);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.locator('[role="treeitem"][data-session-id="ses-ops-01"]').getByTestId('last-observed')).toHaveText('Last observed 06:05 UTC');
  await page.goto(sessionUrl('ses-ops-01'));
  const observed = page.getByTestId('detail-observed');
  await expect(observed).toContainText('2026-10-21T06:05:00Z (06:05 UTC)');
  await expect(observed).toContainText('Stale observation');
  await expect(observed).toContainText('host not reporting');
  await page.goto('/#/');
  await page.getByRole('button', { name: 'Tree', exact: true }).click();
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-ops-01"]').getByTestId('last-observed'))
    .toHaveText('Last observed 06:05 UTC');
  await shot(page, 'stale-offline');
});

test('history lists ended sessions and separates attempts from resumptions', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  for (let i = 0; i < 5; i += 1) await page.getByRole('button', { name: 'Apply next synthetic update' }).click();
  await page.getByRole('link', { name: 'History', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`#/projects/${PID}/history$`));
  const ended = page.getByTestId('history-ended');
  for (const id of ['ses-worker-a1', 'ses-worker-a2', 'ses-helper-01', 'ses-imported-01']) {
    await expect(ended.locator(`tr[data-session-id="${id}"]`)).toHaveCount(1);
  }
  // Running and waiting sessions are not history.
  for (const id of ['ses-exec-01', 'ses-docs-01', 'ses-review-exec']) {
    await expect(ended.locator(`tr[data-session-id="${id}"]`)).toHaveCount(0);
  }
  // Attempts are distinct sessions, in order.
  const attempts = page.locator('[data-testid="history-attempts"][data-assignment="asg-tree-proto"] li');
  await expect(attempts).toHaveCount(2);
  await expect(attempts.nth(0)).toHaveAttribute('data-session-id', 'ses-worker-a1');
  await expect(attempts.nth(1)).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(attempts.nth(1)).toContainText('Attempt 2');
  // A resumption is the same session: listed once, not as a new attempt.
  const resumed = page.getByTestId('history-resumptions').locator('li');
  await expect(resumed).toHaveCount(1);
  await expect(resumed).toHaveAttribute('data-session-id', 'ses-docs-01');
  await expect(resumed).toContainText('still one Odin session');
  await expect(page.locator('[data-testid="history-attempts"] [data-session-id="ses-docs-01"]')).toHaveCount(0);
  await shot(page, 'history');
  // Retiring a session through an update adds it to the history.
  await expect(ended.locator('tr[data-session-id="ses-review-integ"]')).toContainText('Stopped');
  await ended.locator('tr[data-session-id="ses-worker-a1"] a').click();
  await expect(page).toHaveURL(/sessions\/ses-worker-a1$/);
});

test('history of an unknown project gives a useful response', async ({ page }) => {
  await page.goto('/#/projects/proj-missing/history');
  await expect(page.getByTestId('not-found')).toContainText('Project not found');
});
