// Handoff check 8 (partial, synthetic): transcript markup is shown as text.
import { test, expect } from '@playwright/test';
import { sessionUrl, shot } from './helpers.js';

test('hostile transcript markup renders as literal text', async ({ page }) => {
  const dialogs = [];
  page.on('dialog', (d) => { dialogs.push(d.message()); d.dismiss(); });
  await page.goto(sessionUrl('ses-worker-a2'));
  const transcript = page.getByTestId('transcript');
  await expect(transcript).toContainText('<img src=x onerror=alert(1)>');
  await expect(transcript).toContainText('<script>alert("xss")</script>');
  await expect(transcript).toContainText('javascript:alert(1)');
  await expect(transcript.locator('img, script, a, iframe, object')).toHaveCount(0);
  await page.waitForTimeout(200);
  expect(dialogs).toEqual([]);
  await shot(page, 'untrusted-transcript');
  // The browser stores layout preferences only, and does store them.
  await page.getByRole('button', { name: 'List', exact: true }).click();
  // Preferences are written by an effect after the render, so wait for it.
  const stored = () => page.evaluate(() => JSON.parse(localStorage.getItem('odin-web-prefs:v1') || 'null'));
  await expect.poll(async () => (await stored())?.mode).toBe('list');
  expect(Object.keys(await stored()).sort()).toEqual([
    'collapsed', 'mode', 'showRelations', 'sidebarCollapsed', 'sidebarWidth', 'theme',
  ]);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual(['odin-web-prefs:v1']);
});

test('tampered layout preferences are ignored rather than breaking the app', async ({ page }) => {
  // Planted before any app script runs, as a stale or edited store would be.
  await page.addInitScript(() => localStorage.setItem('odin-web-prefs:v1',
    JSON.stringify({ mode: 'tree', collapsed: { 'proj-odin-webapp': 42, other: { x: 1 } }, showRelations: 'yes' })));
  await page.goto(sessionUrl('ses-helper-01'));
  await expect(page.getByTestId('workspace')).toBeVisible();
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-helper-01"]')).toBeVisible();
});

test('the built app has no websocket allowance in its CSP', async ({ page }) => {
  await page.goto('/#/');
  const csp = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
  expect(csp).toContain("script-src 'self'");
  expect(csp).not.toContain('ws:');
});
