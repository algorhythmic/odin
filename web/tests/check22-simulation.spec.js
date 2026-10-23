// R3b synthetic prototype only: continuous events, retained history and presence motion.
import { test, expect } from '@playwright/test';
import { eventFile, PID, sessionUrl, shot } from './helpers.js';

const card = (p, id) => p.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const toggle = (p) => p.getByTestId('autoplay-toggle');
const revision = (p) => p.getByTestId('revision');
const status = (p) => p.getByTestId('update-status');
const next = (p) => p.getByRole('button', { name: 'Apply next synthetic update' }).click();
const generated = 'ses-sim-mvl79i-1';
const drain = async (page, url = '/#/agents') => {
  await page.goto(url);
  await page.reload();
  await page.clock.runFor(100);
  await toggle(page).click();
  await page.clock.runFor(eventFile.events.length * 1200);
  await expect(revision(page)).toHaveText('18');
  await expect(page.getByText('Generating synthetic activity', { exact: true })).toBeVisible();
  await expect(toggle(page)).toHaveText('Pause');
};

test.beforeEach(async ({ page }) => {
  const time = new Date('2026-10-22T12:00:00Z');
  await page.clock.install({ time });
  await page.clock.pauseAt(time);
});

test('Play continues after the fixtures, cards enter, and counts and tokens update', async ({ page }) => {
  await drain(page);
  const before = await page.getByTestId('agent-summary').textContent();
  const tokens = await page.getByTestId('project-tokens').textContent();
  await page.clock.runFor(7 * 1200);
  await expect(card(page, generated)).toHaveClass(/card-enter/);
  const edge = page.locator(`.ancestry-edge[data-to="${generated}"]`);
  await expect(edge).toHaveClass(/edge-enter/);
  expect(await card(page, generated).evaluate((el) => getComputedStyle(el).animationDuration)).toBe('0.36s');
  expect(await edge.evaluate((el) => getComputedStyle(el).animationDuration)).toBe('0.42s');
  await expect(page.getByTestId('agent-summary')).not.toHaveText(before);
  await page.clock.runFor(3 * 1200 + 500);
  await expect(card(page, generated).getByTestId('own-tokens')).not.toHaveText('200 tok');
  await expect(page.getByTestId('project-tokens')).not.toHaveText(tokens);
  await shot(page, 'simulation-generated');
});

test('ended sessions linger six seconds, retract, then remain in project and portfolio History', async ({ page }) => {
  await drain(page);
  await page.clock.runFor(21 * 1200);
  await expect(card(page, generated).getByTestId('state-label')).toHaveText('Done');
  await page.clock.runFor(4 * 1200);
  await expect(card(page, generated)).toHaveCount(1);
  await page.clock.runFor(1200);
  await expect(card(page, generated)).toHaveClass(/card-leave/);
  await expect(page.locator(`.ancestry-edge[data-to="${generated}"]`)).toHaveClass(/edge-leave/);
  await page.clock.runFor(279);
  await expect(card(page, generated)).toHaveCount(1);
  await page.clock.runFor(1);
  await expect(card(page, generated)).toHaveCount(0);
  await toggle(page).click();
  await page.getByRole('link', { name: 'History', exact: true }).click();
  await expect(page.locator(`tr[data-session-id="${generated}"]`)).toContainText('Stopped');
  await page.evaluate((pid) => { location.hash = `#/projects/${pid}/history`; }, PID);
  await expect(page.locator(`tr[data-session-id="${generated}"]`)).toContainText('Stopped');
  await page.locator(`tr[data-session-id="${generated}"] a`).click();
  await expect(page.getByTestId('retired-notice')).toHaveText('Retired · see History');
  await expect(page.getByTestId('run-outcome')).toHaveText('Verified');
  await expect(card(page, generated)).toHaveCount(0);
});

test('Pause freezes generated events, population, tokens, retirement and elapsed; speed changes cadence', async ({ page }) => {
  await drain(page);
  await page.clock.runFor(7 * 1200 + 1000);
  await toggle(page).click();
  await page.clock.runFor(1000); // finish already-started token presentation animations
  const before = await page.locator('.workspace').innerText();
  const rev = await revision(page).textContent();
  await page.clock.runFor(30000);
  await expect(revision(page)).toHaveText(rev);
  expect(await page.locator('.workspace').innerText()).toBe(before);
  await page.getByTestId('autoplay-speed').selectOption('4');
  await toggle(page).click();
  await page.clock.runFor(299);
  await expect(revision(page)).toHaveText(rev);
  await page.clock.runFor(1);
  await expect(revision(page)).toHaveText(String(Number(rev) + 1));
  await page.getByTestId('autoplay-speed').selectOption('0.5');
  await page.clock.runFor(2399);
  await expect(revision(page)).toHaveText(String(Number(rev) + 1));
  await page.clock.runFor(1);
  await expect(revision(page)).toHaveText(String(Number(rev) + 2));
});

test('snapshot retirement is absent from both live layouts and a deep link retains its evidence', async ({ page }) => {
  await page.goto(sessionUrl('ses-helper-01'));
  await page.clock.runFor(100);
  await expect(page.getByTestId('retired-notice')).toHaveText('Retired · see History');
  await expect(page.getByTestId('started-by')).toContainText('ses-worker-a2');
  await expect(page.getByTestId('detail-own-tokens')).toHaveText('unknown');
  await expect(card(page, 'ses-helper-01')).toHaveCount(0);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await page.clock.runFor(100);
  await expect(page.locator('[role="treeitem"][data-session-id="ses-helper-01"]')).toHaveCount(0);
  await page.getByTestId('retired-notice').getByRole('link', { name: 'see History' }).click();
  await page.clock.runFor(100);
  await expect(page.locator('tr[data-session-id="ses-helper-01"]')).toContainText('Stopped');
});

test('the list also animates a delivered retirement before removing its row', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await page.clock.runFor(100);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await page.clock.runFor(100);
  for (let i = 0; i < 5; i++) await next(page);
  const row = page.locator('[role="treeitem"][data-session-id="ses-review-integ"]');
  await expect(row).toHaveClass(/card-leave/);
  await page.clock.runFor(280);
  await expect(row).toHaveCount(0);
});

test('two runs produce the same first 20 generated deliveries and seed overrides vary them', async ({ page }) => {
  const run = async (query = '') => {
    await drain(page, `/${query}#/agents`);
    await toggle(page).click();
    const deliveries = [];
    for (let i = 0; i < 20; i++) {
      await next(page);
      await page.clock.runFor(1000);
      deliveries.push({ status: await status(page).textContent(),
        cards: await page.getByTestId('session-card').evaluateAll((els) => els.map((el) => ({
          id: el.dataset.sessionId, parent: el.dataset.parent, state: el.dataset.lifecycle,
          tokens: el.querySelector('[data-testid="own-tokens"]')?.textContent,
        }))) });
    }
    return deliveries;
  };
  const first = await run();
  expect(await run()).toEqual(first);
  expect(await run('?seed=another')).not.toEqual(first);
});

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' });
  test('generated enter and retirement have no presence delay or animation', async ({ page }) => {
    await drain(page);
    await page.clock.runFor(7 * 1200);
    await expect(card(page, generated)).toHaveCount(1);
    await expect(page.locator('.card-enter, .edge-enter, .card-leave, .edge-leave')).toHaveCount(0);
    expect(await card(page, generated).evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
    await page.clock.runFor(19 * 1200);
    await expect(card(page, generated)).toHaveCount(0);
    await expect(page.locator(`.ancestry-edge[data-to="${generated}"]`)).toHaveCount(0);
    await expect(page.locator('.card-leave, .edge-leave')).toHaveCount(0);
  });
});
