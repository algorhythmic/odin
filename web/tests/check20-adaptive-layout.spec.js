// R3e synthetic prototype: adaptive geometry and state-sized cards, without live simulation.
import { test, expect } from '@playwright/test';
import { eventFile, PID, shot } from './helpers.js';

const canvas = (p) => p.getByTestId('tree-view');
const card = (p, id) => p.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const scale = async (p) => Number(await canvas(p).getAttribute('data-scale'));
const geometry = (p) => p.locator('.card, .project-node').evaluateAll((els) => els.map((el) =>
  [el.dataset.sessionId || el.dataset.projectId, el.offsetLeft, el.offsetTop, el.offsetHeight]));
const settled = (p) => expect.poll(() => p.evaluate(() => document.getAnimations()
  .filter((a) => a.effect?.getTiming().iterations !== Infinity).length)).toBe(0);

for (const [width, height] of [[1440, 900], [1100, 800], [800, 1000]]) {
  test(`portfolio uses three or more card columns at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto('/#/');
    await settled(page);
    const columns = await page.locator('.card').evaluateAll((els) =>
      Math.max(...els.map((el) => els.filter((c) => c.offsetTop === el.offsetTop).length)));
    expect(columns).toBeGreaterThanOrEqual(3);
    expect(await scale(page)).toBeGreaterThanOrEqual(0.75);
    expect(await canvas(page).evaluate((el) => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
    await shot(page, `adaptive-${width}`);
  });
}

test('a tree that fits is visible in full without scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1400 });
  await page.goto(`/#/projects/${PID}`);
  await page.getByRole('checkbox', { name: 'Show typed relationships' }).uncheck();
  await settled(page);
  expect(await scale(page)).toBeGreaterThanOrEqual(0.75);
  const over = await canvas(page).evaluate((el) => [el.scrollWidth - el.clientWidth, el.scrollHeight - el.clientHeight]);
  expect(over).toEqual([0, 0]);
  for (const c of await page.locator('.card, .project-node').all()) await expect(c).toBeInViewport({ ratio: 1 });
});

test('card toggles are keyboard reachable, separate from branches, and persist with validated values', async ({ page }) => {
  await page.goto('/#/');
  const exec = card(page, 'ses-exec-01');
  const original = await geometry(page);
  const collapse = exec.getByRole('button', { name: 'Collapse card', exact: true });
  await collapse.focus();
  await page.keyboard.press('Enter');
  await expect(exec).toHaveAttribute('data-card-expanded', 'false');
  await settled(page);
  expect((await geometry(page)).filter((r) => r[0] !== 'ses-exec-01').map((r) => r.slice(0, 3)))
    .not.toEqual(original.filter((r) => r[0] !== 'ses-exec-01').map((r) => r.slice(0, 3)));
  await expect(page.getByTestId('project-node')).toHaveCount(4);
  await expect(exec.getByRole('button', { name: 'Collapse 4 projects under executive' })).toBeVisible();
  await expect(exec.getByTestId('provider-logo')).toBeVisible();
  await expect(exec.locator('.role')).toHaveText('executive');
  await expect(exec.getByTestId('state-label')).toHaveText('Running');
  await expect(exec.getByTestId('own-tokens')).toHaveText('42.2k tok');
  expect(await exec.evaluate((el) => el.offsetHeight)).toBe(44);
  await page.reload();
  await expect(exec).toHaveAttribute('data-card-expanded', 'false');
  const expand = exec.getByRole('button', { name: 'Expand card', exact: true });
  await expand.focus();
  await page.keyboard.press('Space');
  await expect(exec).toHaveAttribute('data-card-expanded', 'true');
  await settled(page);
  expect(await geometry(page)).toEqual(original);
  await expect(exec.getByTestId('elapsed')).toBeVisible();
  await page.evaluate(() => localStorage.setItem('odin-web-prefs:v1', JSON.stringify({
    cardSizes: { 'ses-exec-01': 'false', 'ses-worker-a2': true, bad: 2, 'bad key': false },
  })));
  await page.reload();
  await expect(exec).toHaveAttribute('data-card-expanded', 'true');
  await expect(card(page, 'ses-worker-a2')).toHaveAttribute('data-card-expanded', 'true');
  await exec.getByRole('button', { name: 'Collapse card', exact: true }).click();
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('odin-web-prefs:v1')).cardSizes))
    .toEqual({ 'ses-exec-01': false, 'ses-worker-a2': true });
});

test('compact terminal cards retain status and own usage, and selection opens details without expansion', async ({ page }) => {
  await page.goto('/#/');
  for (const [id, state, tokens] of [
    ['ses-worker-a1', 'Failed', '14.3k tok'], ['ses-worker-a2', 'Done', 'est. 18.7k tok'],
    ['ses-review-integ', 'Idle', '2.0k tok'],
    ['ses-ops-01', 'Host offline', 'unknown'],
  ]) {
    const c = card(page, id);
    await expect(c).toHaveAttribute('data-card-expanded', 'false');
    await expect(c.getByTestId('state-label')).toHaveText(state);
    await expect(c.getByTestId('own-tokens')).toHaveText(tokens);
    await expect(c.getByTestId('status-chip').getByRole('img')).toHaveAttribute('aria-label', state);
    await expect(c.getByRole('button', { name: 'Expand card', exact: true })).toHaveAttribute('aria-expanded', 'false');
  }
  await card(page, 'ses-worker-a2').locator('.card-title').click();
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(card(page, 'ses-worker-a2')).toHaveAttribute('data-card-expanded', 'false');
});

test('a lifecycle completion resizes and rearranges unless the user overrode that session', async ({ page }) => {
  await page.goto('/#/');
  const apply = page.getByRole('button', { name: 'Apply next synthetic update' });
  const events = eventFile.events;
  const start = events.findIndex((e) => e.event_id === 'evt-014');
  for (let i = 0; i <= start; i++) await apply.click();
  const retry = card(page, 'ses-live-a2');
  await expect(retry).toHaveAttribute('data-card-expanded', 'true');
  const before = await geometry(page);
  for (let i = start + 1; i < events.length; i++) await apply.click();
  await expect(retry.getByTestId('state-label')).toHaveText('Done');
  await expect(retry).toHaveAttribute('data-card-expanded', 'false');
  await settled(page);
  expect((await geometry(page)).filter((r) => r[0] !== 'ses-live-a2').map((r) => r.slice(0, 3)))
    .not.toEqual(before.filter((r) => r[0] !== 'ses-live-a2').map((r) => r.slice(0, 3)));
  // An explicit expanded choice survives the same running-to-done update on reload.
  await page.reload();
  for (let i = 0; i <= start; i++) await apply.click();
  await retry.getByRole('button', { name: 'Collapse card', exact: true }).click();
  await retry.getByRole('button', { name: 'Expand card', exact: true }).click();
  for (let i = start + 1; i < events.length; i++) await apply.click();
  await expect(retry).toHaveAttribute('data-card-expanded', 'true');
});

test('sidebar and drawer changes rearrange while preserving manual zoom and the selected anchor', async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 800 });
  await page.goto('/#/');
  const first = await geometry(page);
  await page.getByRole('button', { name: 'Collapse sidebar', exact: true }).click();
  await expect.poll(() => geometry(page)).not.toEqual(first);
  await settled(page);
  await page.getByRole('button', { name: 'Expand sidebar', exact: true }).click();
  await settled(page);
  const sep = page.getByRole('separator', { name: 'Sidebar width' });
  const b = await sep.boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + 200);
  await page.mouse.down();
  await page.mouse.move(b.x + 120, b.y + 200, { steps: 6 });
  await page.mouse.up();
  await settled(page);
  expect(await geometry(page)).not.toEqual(first);
  const title = card(page, 'ses-exec-01').locator('.card-title');
  await title.click();
  await expect(page.getByTestId('detail-panel')).toBeVisible();
  await settled(page);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  const zoom = await scale(page);
  await title.focus();
  const anchor = await title.boundingBox();
  await page.getByRole('button', { name: 'Collapse sidebar', exact: true }).click();
  await settled(page);
  expect(await scale(page)).toBe(zoom);
  // The selected card stays at its screen position as the canvas moves.
  const point = await title.boundingBox();
  expect(Math.abs(point.y - anchor.y)).toBeLessThanOrEqual(2);
  expect(Math.abs(point.x - anchor.x)).toBeLessThanOrEqual(2);
  await page.locator('aside.detail').getByRole('button', { name: 'Close', exact: true }).click();
  expect(await scale(page)).toBe(zoom);
});

test('grouping uses violet and all layout and size motion stops under reduced motion', async ({ page }) => {
  await page.goto('/#/');
  const group = await page.locator('.project-edge').first().evaluate((el) => getComputedStyle(el).stroke);
  expect(group).toBe('rgb(163, 148, 224)');
  expect(await page.locator('.ancestry-edge').first().evaluate((el) => getComputedStyle(el).stroke)).not.toBe(group);
  const exec = card(page, 'ses-exec-01');
  expect(await exec.evaluate((el) => getComputedStyle(el).transitionDuration)).toContain('0.28s');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await exec.getByRole('button', { name: 'Collapse card', exact: true }).click();
  for (const loc of [exec, page.locator('.project-node').first(), page.locator('.tree-stage'),
    page.locator('.tree-edges path').first()]) {
    expect(await loc.evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  }
});
