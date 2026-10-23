// R3f synthetic prototype: gutter routing and compact canvas controls.
import { test, expect } from '@playwright/test';
import { PID, snapshot, shot } from './helpers.js';

const canvas = (p) => p.getByTestId('tree-view');
const card = (p, id) => p.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const lines = (p) => p.locator('.tree-overlays .relation-edge');
const key = (p) => p.getByRole('button', { name: 'Key', exact: true });
const all = (p) => p.getByRole('checkbox', { name: 'Show all relationships' });
const settled = (p) => expect.poll(() => p.locator('.tree-stage').evaluate((el) => el.getAnimations({ subtree: true })
  .filter((a) => a.effect?.getTiming().iterations !== Infinity).length)).toBe(0);

async function assertRouting(page) {
  await settled(page);
  const hits = await page.evaluate(() => {
    const boxes = [...document.querySelectorAll('.card, .project-node')].map((el) => ({
      id: el.dataset.sessionId || `project:${el.dataset.projectId}`, rect: el.getBoundingClientRect(),
    }));
    const paths = [...document.querySelectorAll('.tree-edges > path, .tree-overlays .relation-edge > path')];
    return paths.flatMap((path) => {
      const data = path.classList.contains('ancestry-edge') || path.classList.contains('project-edge')
        ? path.dataset : path.parentElement.dataset;
      const endpoints = [data.via || data.from, data.target || data.to];
      const matrix = path.getScreenCTM();
      const points = [...path.getAttribute('d').matchAll(/[ML]([\d.-]+),([\d.-]+)/g)]
        .map((m) => new DOMPoint(+m[1], +m[2]).matrixTransform(matrix));
      return points.slice(1).flatMap((b, i) => boxes.flatMap(({ id, rect: c }) => {
        if (endpoints.includes(id)) return [];
        const a = points[i];
        const hit = Math.min(a.x, b.x) < c.right - 0.1 && Math.max(a.x, b.x) > c.left + 0.1
          && Math.min(a.y, b.y) < c.bottom - 0.1 && Math.max(a.y, b.y) > c.top + 0.1;
        return hit ? [`${data.from}>${data.to} crosses ${id}`] : [];
      }));
    });
  });
  expect(hits, 'rendered segments clear non-endpoint cards and project nodes').toEqual([]);
  const labelHits = await page.locator('.relation-label').evaluateAll((els) => els.filter((el) => {
    const a = el.getBoundingClientRect();
    return [...document.querySelectorAll('.card, .project-node')].some((c) => {
      const b = c.getBoundingClientRect();
      return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    });
  }).map((el) => el.textContent));
  expect(labelHits, 'relationship labels clear every card').toEqual([]);
}

for (const [width, height] of [[1440, 900], [1100, 800], [800, 1000]]) {
  for (const scoped of [false, true]) test(`clear DOM routing: ${scoped ? 'project' : 'portfolio'} ${width}x${height}`,
    async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto(scoped ? `/#/projects/${PID}` : '/#/');
      await key(page).click();
      await all(page).check();
      await expect(lines(page)).toHaveCount(4);
      await assertRouting(page);
      if (width === 1440) {
        await expect(page.getByTestId('tree-header').getByRole('link', { name: 'History' })).toBeInViewport();
        await expect(page.getByRole('button', { name: 'List', exact: true })).toBeInViewport();
      }
      const layers = await page.locator('.tree-stage').evaluate((el) => {
        const svg = el.querySelector('.tree-overlays');
        const card = el.querySelector('.card');
        return Number(getComputedStyle(svg).zIndex) < Number(getComputedStyle(card).zIndex);
      });
      expect(layers, 'cards hide any transient connector collision').toBe(true);
      if (width === 1440) {
        await key(page).click();
        await expect(page.getByTestId('tree-header').getByRole('link', { name: 'History' })).toBeInViewport({ ratio: 1 });
        await expect(page.getByRole('button', { name: 'List', exact: true })).toBeInViewport({ ratio: 1 });
        await shot(page, scoped ? 'r3f-scoped' : 'r3f-portfolio');
      }
    });
}

test('expanded generated project also clears rendered cards', async ({ page }) => {
  await page.goto('/?dataset=large#/');
  await page.getByTestId('project-node').click();
  await key(page).click();
  await all(page).check();
  await expect(page.getByTestId('session-card')).toHaveCount(41);
  await assertRouting(page);
});

test('relationships follow hover, keyboard focus and selection, with both endpoints highlighted', async ({ page }) => {
  await page.goto('/#/');
  await expect(lines(page)).toHaveCount(0);
  await card(page, 'ses-review-exec').hover();
  await expect(lines(page)).toHaveCount(1);
  await expect(card(page, 'ses-review-exec')).toHaveClass(/relationship-active/);
  await expect(card(page, 'ses-worker-a2')).toHaveClass(/relationship-active/);
  await page.mouse.move(0, 0);
  await expect(lines(page)).toHaveCount(0);
  await card(page, 'ses-review-integ').locator('.card-title').focus();
  await expect(lines(page)).toHaveCount(1);
  await expect(lines(page)).toHaveAttribute('data-from', 'ses-review-integ');
  await canvas(page).focus();
  await expect(lines(page)).toHaveCount(0);
  await page.evaluate(() => { location.hash = '#/sessions/ses-worker-a2'; });
  await expect(lines(page)).toHaveCount(3);
  await canvas(page).focus();
  await expect(lines(page)).toHaveCount(3);
  await key(page).click();
  await all(page).check();
  await expect(lines(page)).toHaveCount(4);
  await assertRouting(page);
});

test('project title, counts and tokens have separate unclipped measured rows', async ({ page }) => {
  await page.goto('/#/');
  await settled(page);
  const failures = await page.getByTestId('project-node').evaluateAll((nodes) => nodes.flatMap((node) => {
    const parent = node.getBoundingClientRect();
    const rows = [...node.children].slice(1).map((el) => ({ el, box: el.getBoundingClientRect() }));
    return rows.flatMap(({ el, box }, i) => box.top < parent.top + 1 || box.bottom > parent.bottom - 1
      || el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth
      || i && box.top < rows[i - 1].box.bottom - 0.1 ? [el.textContent] : []);
  }));
  expect(failures).toEqual([]);
});

for (const scoped of [false, true]) test(`compact header and key preferences: ${scoped ? 'project' : 'portfolio'}`,
  async ({ page }) => {
    await page.goto(scoped ? `/#/projects/${PID}` : '/#/');
    await expect(key(page)).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('.legend-row')).toHaveCount(0);
    expect((await page.getByTestId('tree-header').boundingBox()).height).toBeLessThanOrEqual(56);
    await expect(page.getByTestId('tree-header').getByRole('link', { name: 'History' })).toBeInViewport();
    await expect(page.getByRole('button', { name: 'List', exact: true })).toBeInViewport();
    await settled(page);
    const covers = await page.locator('.legend').evaluate((el) => {
      const a = el.getBoundingClientRect();
      return [...document.querySelectorAll('.card, .project-node')].some((c) => {
        const b = c.getBoundingClientRect();
        const v = document.querySelector('.tree-view').getBoundingClientRect();
        if (b.top >= v.bottom || b.bottom <= v.top) return false;
        return a.top < Math.min(b.bottom, v.bottom) && a.bottom > Math.max(b.top, v.top)
          && a.left < b.right && a.right > b.left;
      });
    });
    expect(covers).toBe(false);
    await key(page).click();
    await expect(page.locator('.legend-row')).toHaveCount(5);
    await all(page).check();
    await page.reload();
    await expect(key(page)).toHaveAttribute('aria-expanded', 'true');
    await expect(all(page)).toBeChecked();
    await page.evaluate(() => localStorage.setItem('odin-web-prefs:v1', JSON.stringify({ keyOpen: 'true' })));
    await page.reload();
    await expect(key(page)).toHaveAttribute('aria-expanded', 'false');
  });

test('compact synthetic driver plays, pauses, changes speed, applies and announces results', async ({ page }) => {
  await page.clock.install();
  await page.goto('/#/');
  const driver = page.getByTestId('update-driver');
  expect((await driver.boundingBox()).height).toBeLessThanOrEqual(44);
  await driver.getByRole('button', { name: 'Play', exact: true }).click();
  await page.clock.runFor(1200);
  await expect(driver.getByTestId('revision')).toHaveText('1');
  await driver.getByRole('button', { name: 'Pause', exact: true }).click();
  await page.clock.runFor(2400);
  await expect(driver.getByTestId('revision')).toHaveText('1');
  await driver.getByRole('combobox', { name: 'Speed' }).selectOption('4');
  await driver.getByRole('button', { name: 'Apply next synthetic update' }).click();
  await expect(driver.getByRole('status')).toHaveText('Applied evt-002 (session.started) at revision 2.');
  await expect(driver.getByTestId('update-status')).toHaveAttribute('role', 'status');
  await driver.getByText('Synthetic', { exact: false }).first().click();
  await expect(driver.getByText(/cursor/)).toBeVisible();
  await expect(driver.locator('.driver-metadata')).toContainText('Applied evt-002');
});

test('breadcrumb returns to portfolio and the scoped executive shows its work and is selectable', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const header = page.getByTestId('tree-header');
  await expect(header.getByRole('heading')).toHaveText('Portfolio / Odin web app (synthetic)');
  await expect(header.getByRole('link', { name: 'Portfolio', exact: true })).toHaveAttribute('href', '#/');
  const executive = card(page, snapshot.executive_session_id);
  await expect(executive).toContainText('executive');
  await expect(executive).toContainText('Fable 5.1');
  await expect(executive).toContainText('Running');
  await expect(executive).toContainText('Oversee every project and keep the operator informed');
  const a = await executive.boundingBox();
  const b = await page.getByTestId('project-node').boundingBox();
  expect(a.y + a.height).toBeLessThan(b.y);
  await expect(page.locator('.project-edge[data-from="ses-exec-01"]')).toHaveCount(1);
  await executive.locator('.card-title').click();
  await expect(executive).toHaveClass(/selected/);
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', snapshot.executive_session_id);
  await header.getByRole('link', { name: 'Portfolio', exact: true }).click();
  await expect(page).toHaveURL(/#\/$/);
});
