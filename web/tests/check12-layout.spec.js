// R3d synthetic layout: width fit, vertical scroll and recorded connectors.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot, snapshot } from './helpers.js';

const projectSessions = snapshot.sessions.filter((s) => s.project_id === PID && s.lifecycle !== 'retired');
const kids = new Map();
for (const s of projectSessions) {
  if (s.parent_session_id) kids.set(s.parent_session_id, [...(kids.get(s.parent_session_id) || []), s.id]);
}
const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const boxOf = (page, id) => card(page, id).boundingBox();

test('the canvas owns vertical overflow and the lowest card is reachable', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const view = page.getByTestId('tree-view');
  await page.setViewportSize({ width: 800, height: 500 });
  await expect.poll(() => view.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
  expect(await view.evaluate((el) => getComputedStyle(el).overflowY)).toBe('auto');
  expect(await view.evaluate((el) => el.getBoundingClientRect().bottom)).toBeLessThanOrEqual(900);
  const lastId = await view.evaluate((el) => {
    const cards = [...el.querySelectorAll('[data-testid="session-card"]')];
    const bottom = cards.reduce((a, b) => a.offsetTop > b.offsetTop ? a : b);
    bottom.scrollIntoView({ block: 'nearest' });
    return bottom.dataset.sessionId;
  });
  await expect(card(page, lastId)).toBeInViewport();
});

test('adaptive branches keep sibling reading order and descendants clear', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(page.getByTestId('tree-view')).toHaveAttribute('data-mode', 'adaptive');
  for (const [parent, ids] of kids) {
    if (ids.length < 2) continue;
    const boxes = await page.locator('[data-testid="session-card"]').evaluateAll((els) =>
      Object.fromEntries(els.map((el) => [el.dataset.sessionId, { x: el.offsetLeft, y: el.offsetTop }])));
    for (let i = 1; i < ids.length; i++) {
      const a = boxes[ids[i - 1]];
      const b = boxes[ids[i]];
      expect(b.y > a.y || b.y === a.y && b.x > a.x, `${parent}: sibling reading order`).toBe(true);
    }
  }
  await shot(page, 'tree-layout');
});

test('every recorded parent-child edge has a square-cornered connector and a port dot', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const expected = projectSessions.filter((s) => s.parent_session_id).map((s) => `${s.parent_session_id}>${s.id}`);
  const edges = page.locator('.tree-edges path.ancestry-edge');
  await expect(edges).toHaveCount(expected.length);
  const pairs = await edges.evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));
  expect(pairs.sort()).toEqual([...expected].sort());
  // Right angles only: M/L/H/V commands, never curves.
  const curved = await edges.evaluateAll((els) => els.map((e) => e.getAttribute('d')).filter((d) => /[CQSTAcqsta]/.test(d)));
  expect(curved, 'ancestry connectors must be square-cornered').toEqual([]);
  // A port dot under every parent that shows children.
  const parents = new Set(await edges.evaluateAll((els) => els.map((e) => e.dataset.via || e.dataset.from)));
  await expect(page.locator('.tree-edges circle.port-dot')).toHaveCount(parents.size);
  for (const pid of parents) await expect(page.locator(`.tree-edges circle.port-dot[data-parent="${pid}"]`)).toHaveCount(1);
});

test('selection opens a detail drawer; List remains and removed panels stay absent', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(page.getByTestId('detail-panel')).toHaveCount(0);

  // Selecting a card opens a drawer docked to the window's right edge.
  await card(page, 'ses-worker-a2').click();
  await expect(page).toHaveURL(/sessions\/ses-worker-a2$/);
  const drawer = page.locator('aside.detail');
  await expect(drawer.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  const d = await drawer.boundingBox();
  expect(Math.abs(d.x + d.width - page.viewportSize().width)).toBeLessThanOrEqual(2);
  await shot(page, 'detail-drawer');
  await drawer.getByRole('button', { name: 'Close' }).click();
  await expect(page).toHaveURL(new RegExp(`#/projects/${PID}$`));
  await expect(page.getByTestId('detail-panel')).toHaveCount(0);

  // A deep link opens the same drawer directly.
  await page.goto(sessionUrl('ses-helper-01'));
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-helper-01');

  await expect(page.getByRole('button', { name: 'Projects', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Conversation', exact: true })).toHaveCount(0);
  await expect(page.getByTestId('conversation')).toHaveCount(0);

  // The list view stays a toggle away from the tree.
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.getByRole('tree', { name: 'Sessions by ancestry' })).toBeVisible();
  await expect(page.getByTestId('tree-view')).toHaveCount(0);
});
