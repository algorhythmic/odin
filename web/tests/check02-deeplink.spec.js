// Handoff check 2 (partial, synthetic): deep links restore context; missing records explain themselves.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot } from './helpers.js';

test('a session deep link restores the selection after reload', async ({ page }) => {
  await page.goto(sessionUrl('ses-worker-a2'));
  const panel = page.getByTestId('detail-panel');
  await expect(panel).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(panel.getByTestId('detail-assignment')).toContainText('asg-tree-proto');
  await expect(panel.getByTestId('detail-runs')).toContainText('run-tree-2');
  await expect(panel.getByTestId('detail-evidence')).toContainText('rcpt-synthetic-1');
  await page.reload();
  await expect(panel).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(page.locator('[data-testid="session-card"].selected')).toHaveAttribute('data-session-id', 'ses-worker-a2');
});

test('a deep link into a collapsed branch expands its ancestors', async ({ page }) => {
  await page.goto(sessionUrl('ses-integ-01'));
  await page.locator('[data-session-id="ses-integ-01"]').getByRole('button', { name: /Collapse/ }).click();
  await expect(page.locator('[data-session-id="ses-helper-01"]')).toHaveCount(0);
  await page.goto(sessionUrl('ses-helper-01'));
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-helper-01"]')).toBeVisible();
});

test('unknown session and project give a useful response', async ({ page }) => {
  await page.goto(sessionUrl('ses-does-not-exist'));
  const notFound = page.getByTestId('not-found');
  await expect(notFound).toContainText('Session not found');
  await expect(notFound).toContainText('ses-does-not-exist');
  await shot(page, 'not-found-session');
  await notFound.getByRole('link', { name: 'Back to the project' }).click();
  await expect(page).toHaveURL(new RegExp(`#/projects/${PID}$`));

  // A session from another project is not shown under this one.
  await page.goto(sessionUrl('ses-pin-worker'));
  await expect(page.getByTestId('not-found')).toContainText('Session not found');

  await page.goto('/#/projects/proj-missing');
  await expect(page.getByTestId('not-found')).toContainText('Project not found');
  await shot(page, 'not-found-project');
});
