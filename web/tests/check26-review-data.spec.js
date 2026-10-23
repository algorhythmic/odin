// Review data fixes: synthetic prototype evidence only.
import { test, expect } from '@playwright/test';
import { eventFile, expandCards } from './helpers.js';

const deliver = (page, count) => page.getByRole('button', { name: 'Apply next synthetic update' })
  .evaluate((button, n) => { for (let i = 0; i < n; i++) button.click(); }, count);

test.use({ reducedMotion: 'reduce' });

test('recorded times preserve elapsed across waiting, resuming, display ticks and ending', async ({ page }) => {
  const time = new Date('2026-10-22T12:00:00Z');
  await page.clock.install({ time });
  await page.clock.pauseAt(time);
  await page.goto('/#/agents');
  await page.clock.runFor(100);
  await deliver(page, eventFile.events.length + 73);
  await page.clock.runFor(100);
  const card = page.locator('[data-testid="session-card"][data-session-id="ses-sim-mvl79i-6"]');
  await expect(card).toHaveAttribute('data-lifecycle', 'waiting_for_input');
  await expandCards(page, ['ses-sim-mvl79i-6']);
  await expect(card.getByTestId('elapsed')).toHaveText('0m');
  await page.getByTestId('autoplay-toggle').click();
  await page.clock.runFor(1000);
  await page.getByTestId('autoplay-toggle').click();
  await expect(card.getByTestId('elapsed')).toHaveText('0m');
  await deliver(page, 3);
  await page.clock.runFor(100);
  await expect(card).toHaveAttribute('data-lifecycle', 'running');
  await expect(card.getByTestId('elapsed')).toHaveText('37s');
  await page.getByTestId('autoplay-toggle').click();
  await page.clock.runFor(1000);
  await expect(card.getByTestId('elapsed')).toHaveText('38s');
  await page.getByTestId('autoplay-toggle').click();
  await deliver(page, 33);
  await page.clock.runFor(100);
  await expect(card).toHaveAttribute('data-lifecycle', 'ended');
  await expandCards(page, ['ses-sim-mvl79i-6']);
  await expect(card.getByTestId('elapsed')).toHaveText('1m');
  await deliver(page, 5);
  await page.clock.runFor(100);
  await expect(card).toHaveCount(0);
  await page.evaluate(() => { location.hash = '#/history'; });
  await page.clock.runFor(100);
  await expect(page.locator('tr[data-session-id="ses-sim-mvl79i-6"]')).toContainText('Stopped');
});

test('20,000 generated steps retain bounded History and disclose trimming in both scopes', async ({ page }) => {
  test.setTimeout(60000);
  await page.goto('/#/agents');
  await deliver(page, eventFile.events.length + 20000);
  await expect(page.getByTestId('revision')).toHaveText('20018');
  await page.evaluate(() => { location.hash = '#/history'; });
  await expect(page.getByTestId('history-trimmed').first())
    .toHaveText('older history not retained in the synthetic prototype');
  const rows = page.locator('[data-testid="history-ended"] tbody tr');
  expect(await rows.count()).toBeGreaterThanOrEqual(500);
  expect(await rows.count()).toBeLessThanOrEqual(518);
  await expect(page.locator('tr[data-session-id="ses-sim-mvl79i-1"]')).toHaveCount(0);
  const retained = await rows.last().getAttribute('data-session-id');
  await rows.last().getByRole('link').click();
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', retained);
  await page.evaluate(() => { location.hash = '#/projects/proj-empty/history'; });
  await expect(page.getByTestId('history-trimmed')).toBeVisible();
  await page.evaluate(() => { location.hash = '#/'; });
  await expect(page.getByTestId('dashboard')).toBeVisible();
  await expect(page.locator('.priority-row:not(.priority-setup) .priority-fold ul')).toHaveCount(0);
  expect(await page.getByTestId('recent-activity').locator('li').count()).toBeLessThanOrEqual(12);
});

test('priority activity is read only while its disclosure is unfolded', async ({ page }) => {
  await page.goto('/#/');
  const row = page.locator('[data-kind="needs"][data-attention-session="ses-pin-worker"]');
  await expect(row.locator('.priority-fold li')).toHaveCount(0);
  await row.locator('.priority-disclosure').click();
  await expect(row.locator('.priority-fold')).toContainText('worker requested decision');
  expect(await row.locator('.priority-fold li').count()).toBeLessThanOrEqual(3);
  await row.locator('.priority-disclosure').click();
  await expect(row.locator('.priority-fold li')).toHaveCount(0);
});
