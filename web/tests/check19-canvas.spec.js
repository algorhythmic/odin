// R3d: adaptive geometry and direct manipulation, synthetic prototype evidence.
import { test, expect } from '@playwright/test';
import { expandCards, PID, shot } from './helpers.js';

const canvas = (p) => p.getByRole('region', { name: 'Agent tree canvas' });
const card = (p, id) => p.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const reset = (p) => p.getByRole('button', { name: 'Reset view', exact: true });
const scale = async (p) => Number(await canvas(p).getAttribute('data-scale'));
const transform = (p) => p.locator('.tree-stage').evaluate((el) => el.style.transform);
const settled = async (p) => {
  await expect.poll(() => p.locator('.tree-stage').evaluate((el) =>
    el.getAnimations({ subtree: true }).filter((a) => a.effect?.getTiming().iterations !== Infinity).length)).toBe(0);
};

async function assertLabelsClear(page) {
  await settled(page);
  const hits = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.card, .project-node')].map((el) => el.getBoundingClientRect());
    return [...document.querySelectorAll('.relation-label')].flatMap((el) => {
      const a = el.getBoundingClientRect();
      return cards.some((b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top)
        ? [el.textContent] : [];
    });
  });
  expect(hits, 'every relationship pill clears every session and project card').toEqual([]);
}

for (const [width, mode] of [[1440, 'adaptive'], [1100, 'adaptive'], [800, 'adaptive']]) {
  test(`load fits at ${width}px by rearranging before shrinking`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/#/');
    await expect(canvas(page)).toHaveAttribute('data-mode', mode);
    await settled(page);
    expect(await scale(page)).toBeGreaterThanOrEqual(0.75);
    await expect(reset(page)).toHaveCount(0);
    for (const name of ['Fit all', 'Actual size', 'Fit branch']) {
      await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0);
    }
    await expect(page.getByText(/Zoom \d+%/)).toHaveCount(0);
    const bounds = await canvas(page).boundingBox();
    for (const box of await page.locator('.card, .project-node').evaluateAll((els) =>
      els.map((el) => el.getBoundingClientRect().toJSON()))) {
      expect(box.x).toBeGreaterThanOrEqual(bounds.x - 1);
      expect(box.right).toBeLessThanOrEqual(bounds.x + bounds.width + 1);
    }
    const collision = await page.locator('.legend').evaluate((key) => {
      const a = key.getBoundingClientRect();
      return [...document.querySelectorAll('.card, .project-node')].some((el) => {
        const b = el.getBoundingClientRect();
        return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
      });
    });
    expect(collision).toBe(false);
    await assertLabelsClear(page);
    await shot(page, `canvas-${width}`);
  });
}

test('automatic fitting follows resize, sidebar, drawer and content changes', async ({ page }) => {
  await page.goto('/#/');
  await expect(canvas(page)).toHaveAttribute('data-mode', 'adaptive');
  const initialWidth = await canvas(page).evaluate((el) => el.clientWidth);
  const separator = page.getByRole('separator', { name: 'Sidebar width' });
  await separator.focus();
  await page.keyboard.press('End');
  await expect.poll(() => canvas(page).evaluate((el) => el.clientWidth)).toBeLessThan(initialWidth);
  await page.keyboard.press('Home');
  await expect.poll(() => canvas(page).evaluate((el) => el.clientWidth)).toBeGreaterThan(initialWidth);
  await page.keyboard.press('ArrowRight');
  await page.evaluate(() => {
    const prefs = JSON.parse(localStorage.getItem('odin-web-prefs:v1'));
    prefs.sidebarWidth = 320;
    localStorage.setItem('odin-web-prefs:v1', JSON.stringify(prefs));
  });
  await page.reload();
  await page.setViewportSize({ width: 1100, height: 900 });
  await expect(canvas(page)).toHaveAttribute('data-mode', 'adaptive');
  await page.getByRole('button', { name: 'Collapse sidebar', exact: true }).click();
  await expect(canvas(page)).toHaveAttribute('data-mode', 'adaptive');
  await card(page, 'ses-exec-01').getByRole('button', { name: 'Collapse 4 projects under executive' }).click();
  await expect(page.getByTestId('session-card')).toHaveCount(1);
  await expect(canvas(page)).toHaveAttribute('data-mode', 'adaptive');
  await card(page, 'ses-exec-01').getByRole('button', { name: 'Expand 4 projects under executive' }).click();
  const width = await canvas(page).evaluate((el) => el.clientWidth);
  await card(page, 'ses-exec-01').getByRole('button').first().click();
  await expect.poll(() => canvas(page).evaluate((el) => el.clientWidth)).toBeLessThan(width);
  await expect(card(page, 'ses-exec-01')).toBeInViewport();
  await page.locator('aside.detail').getByRole('button', { name: 'Close', exact: true }).click();
  await expect.poll(() => canvas(page).evaluate((el) => el.clientWidth)).toBe(width);
  await page.getByRole('button', { name: 'Apply next synthetic update' }).click();
  await page.getByRole('button', { name: 'Apply next synthetic update' }).click();
  await expect(card(page, 'ses-docs-helper')).toHaveCount(1);
  await expect(reset(page)).toHaveCount(0);
});

test('wheel zoom anchors the pointer, plain wheel scrolls, keyboard clamps and resets', async ({ page }) => {
  await page.goto('/#/');
  await settled(page);
  const c = canvas(page);
  const b = await c.boundingBox();
  const point = { x: Math.round(b.x + 500) - b.x, y: Math.round(b.y + 280) - b.y };
  const before = await page.locator('.tree-stage').evaluate((el) => {
    const m = new DOMMatrix(el.style.transform); return { x: m.e, y: m.f, s: m.a };
  });
  await c.dispatchEvent('wheel', { clientX: b.x + point.x, clientY: b.y + point.y, deltaY: -100, ctrlKey: true });
  await expect(reset(page)).toBeVisible();
  const after = await page.locator('.tree-stage').evaluate((el) => {
    const m = new DOMMatrix(el.style.transform); return { x: m.e, y: m.f, s: m.a };
  });
  expect((point.x - after.x) / after.s).toBeCloseTo((point.x - before.x) / before.s, 2);
  expect((point.y - after.y) / after.s).toBeCloseTo((point.y - before.y) / before.s, 2);
  await c.dispatchEvent('wheel', { clientX: b.x + point.x, clientY: b.y + point.y, deltaY: -20, metaKey: true });
  const oldScale = await scale(page);
  await c.dispatchEvent('wheel', { deltaY: 240 });
  expect(await c.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
  expect(await scale(page)).toBe(oldScale);
  await c.focus();
  for (let i = 0; i < 12; i++) await page.keyboard.press('+');
  expect(await scale(page)).toBe(2);
  for (let i = 0; i < 20; i++) await page.keyboard.press('-');
  expect(await scale(page)).toBe(0.5);
  const manualScale = await scale(page);
  await page.setViewportSize({ width: 1100, height: 900 });
  expect(await scale(page)).toBe(manualScale);
  await page.keyboard.press('0');
  await expect(reset(page)).toHaveCount(0);
  expect(await scale(page)).toBeGreaterThanOrEqual(0.75);
  const fittedScale = await scale(page);
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  expect(await scale(page)).toBeGreaterThan(fittedScale);
  await reset(page).click();
  await page.getByRole('button', { name: 'Zoom out', exact: true }).click();
  expect(await scale(page)).toBeLessThan(1);
});

test('background drag pans after 4px, while card, chip and link clicks still work', async ({ page }) => {
  await page.goto('/#/');
  await settled(page);
  const b = await canvas(page).boundingBox();
  const before = await transform(page);
  await page.mouse.move(b.x + 20, b.y + 200);
  await page.mouse.down();
  await page.mouse.move(b.x + 22, b.y + 201);
  await page.mouse.up();
  await expect(reset(page)).toHaveCount(0);
  await page.mouse.move(b.x + 20, b.y + 200);
  await page.mouse.down();
  await page.mouse.move(b.x + 90, b.y + 240, { steps: 4 });
  await page.mouse.up();
  expect(await transform(page)).not.toBe(before);
  await expect(reset(page)).toBeVisible();
  await reset(page).click();
  const title = card(page, 'ses-exec-01').getByRole('button').first();
  const cb = await title.boundingBox();
  const fitted = await transform(page);
  await page.mouse.move(cb.x + 5, cb.y + 5);
  await page.mouse.down();
  await page.mouse.move(cb.x + 30, cb.y + 15);
  await page.mouse.up();
  expect(await transform(page)).toBe(fitted);
  await expect(reset(page)).toHaveCount(0);
  await expect(page.getByTestId('detail-panel')).toHaveCount(0);
  await page.mouse.move(cb.x + 8, cb.y + 8);
  await page.mouse.down();
  await page.mouse.move(cb.x + 10, cb.y + 9);
  await page.mouse.up();
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-exec-01');
  await expect(reset(page)).toHaveCount(0);
  await page.getByRole('button', { name: 'Collapse 4 projects under executive' }).click();
  await expect(page.getByTestId('project-node')).toHaveCount(0);
  await page.getByRole('link', { name: 'History', exact: true }).click();
  await expect(page).toHaveURL(/history$/);
});

test.describe('native touch', () => {
  test.use({ hasTouch: true });
  test('one-finger drag and two-finger pinch move the canvas and cancel cleanly', async ({ page }) => {
    await page.goto('/#/');
    const c = canvas(page);
    const b = await c.boundingBox();
    const client = await page.context().newCDPSession(page);
    const one = { id: 1, x: b.x + 30, y: b.y + 50 };
    const send = (type, touchPoints) => client.send('Input.dispatchTouchEvent', { type, touchPoints });
    await send('touchStart', [one]);
    one.x += 20;
    one.y += 20;
    await send('touchMove', [one]);
    await expect(reset(page)).toBeVisible();
    const before = await scale(page);
    const two = { id: 2, x: one.x + 100, y: one.y };
    await send('touchStart', [one, two]);
    two.x += 100;
    await send('touchMove', [one, two]);
    await expect.poll(() => scale(page)).toBeGreaterThan(before);
    await send('touchCancel', []);
    await reset(page).click();
    await expect(reset(page)).toHaveCount(0);
  });
});

test('external selection reveals its card while preserving a manual zoom', async ({ page }) => {
  await page.goto('/#/');
  await canvas(page).focus();
  await page.keyboard.press('+');
  const zoom = await scale(page);
  await page.evaluate(() => { location.hash = '#/sessions/ses-worker-a2'; });
  await expect(card(page, 'ses-worker-a2')).toBeInViewport();
  expect(await scale(page)).toBe(zoom);
  await page.getByRole('button', { name: 'Go to parent', exact: true }).click();
  await expect(card(page, 'ses-integ-01')).toBeInViewport();
  expect(await scale(page)).toBe(zoom);
});

for (const [url, width] of [['/#/', 1440], [`/#/projects/${PID}`, 1440], ['/#/', 800]]) {
  test(`legend and unobstructed labels: ${url} at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(url);
    await settled(page);
    const grouping = await page.locator('.tree-edges .project-edge').count() > 0;
    await expect(page.locator('.legend-row')).toHaveCount(grouping ? 5 : 4);
    for (const s of ['ancestry', ...(grouping ? ['project'] : []), 'review', 'delegation', 'assignment_owner']) {
      await expect(page.locator(`.legend-row[data-style="${s}"]`)).toBeVisible();
    }
    if (grouping) expect(await page.locator('.tree-edges .project-edge').first()
      .evaluate((el) => getComputedStyle(el).strokeDasharray)).toBe('8px, 4px');
    await expandCards(page, ['ses-worker-a2']);
    await expect(page.locator('.run-badge').first()).toHaveCount(1);
    await assertLabelsClear(page);
    await canvas(page).focus();
    for (let i = 0; i < 6; i++) await page.keyboard.press('-');
    await assertLabelsClear(page);
    const small = await page.locator('.relation-label text').first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(small * await scale(page)).toBeCloseTo(11 * 0.85, 3);
    for (let i = 0; i < 12; i++) await page.keyboard.press('+');
    await assertLabelsClear(page);
    const large = await page.locator('.relation-label text').first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(large * await scale(page)).toBeCloseTo(11 * 1.25, 3);
    await page.getByRole('checkbox', { name: 'Show typed relationships' }).uncheck();
    await expect(page.locator('.legend-row')).toHaveCount(grouping ? 2 : 1);
    await expect(page.locator('.relation-label, .run-badge')).toHaveCount(0);
    await page.goto('/#/projects/proj-empty');
    await expect(page.locator('.legend-row')).toHaveCount(0);
  });
}

test('arrangement motion uses the shared curve and becomes instant with reduced motion', async ({ page }) => {
  await page.goto('/#/');
  const duration = await card(page, 'ses-exec-01').evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(duration).toContain('0.42s');
  expect(await card(page, 'ses-exec-01').evaluate((el) => getComputedStyle(el).transitionTimingFunction))
    .toContain('cubic-bezier(0.32, 0.72, 0.24, 1)');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 1100, height: 900 });
  for (const loc of [card(page, 'ses-exec-01'), page.locator('.project-node').first(), page.locator('.tree-stage')]) {
    expect(await loc.evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  }
  await expect(canvas(page)).toHaveAccessibleDescription(/Use \+ and - to zoom/);
});
