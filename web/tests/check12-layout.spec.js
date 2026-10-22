// Pass 4 brief item 4 and "Keep" (synthetic): the tree fills the page —
// square-cornered connectors from a port dot under each parent, the first
// level in a horizontal row, deeper levels stacked under the parent's left
// edge, and a canvas that grows with content so the page scrolls (no
// fixed-height box clips it). Details use a right-side drawer; Tree/List
// is the only layout toggle.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot, snapshot } from './helpers.js';

const projectSessions = snapshot.sessions.filter((s) => s.project_id === PID);
const kids = new Map();
for (const s of projectSessions) {
  if (s.parent_session_id) kids.set(s.parent_session_id, [...(kids.get(s.parent_session_id) || []), s.id]);
}
const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const boxOf = (page, id) => card(page, id).boundingBox();

test('the canvas grows with the tree and no ancestor clips it to a fixed height', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const view = page.getByTestId('tree-view');
  const offenders = await view.evaluate((el) => {
    const bad = [];
    for (let n = el.parentElement; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n);
      const clips = ['hidden', 'auto', 'scroll'].includes(cs.overflowY) && n.scrollHeight > n.clientHeight + 1;
      if (clips) bad.push(`${n.tagName.toLowerCase()}.${String(n.className).split(' ')[0]} overflow-y=${cs.overflowY}`);
    }
    return bad;
  });
  expect(offenders, 'no ancestor may clip the canvas vertically').toEqual([]);

  // The canvas is tall enough that the page itself must scroll.
  const metrics = await view.evaluate((el) => ({
    canvas: el.getBoundingClientRect().height,
    page: document.documentElement.scrollHeight,
    win: innerHeight,
  }));
  expect(metrics.page).toBeGreaterThan(metrics.win);

  // The lowest card is reachable by scrolling the page/canvas.
  const lastId = await view.evaluate((el) => {
    const cards = [...el.querySelectorAll('[data-testid="session-card"]')];
    const bottom = cards.reduce((a, b) => (a.getBoundingClientRect().top > b.getBoundingClientRect().top ? a : b));
    bottom.scrollIntoView({ block: 'center' });
    return bottom.dataset.sessionId;
  });
  await expect(card(page, lastId)).toBeInViewport();
});

test('first-level children share a row; deeper levels stack under the parent left edge', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);

  // ses-exec-01's recorded children form the first-level row: same y,
  // strictly increasing x.
  const firstLevel = kids.get('ses-exec-01');
  expect(firstLevel.length).toBeGreaterThan(1);
  const row = [];
  for (const id of firstLevel) row.push(await boxOf(page, id));
  for (const b of row) expect(Math.abs(b.y - row[0].y), 'first-level siblings share a row').toBeLessThanOrEqual(3);
  for (let i = 1; i < row.length; i += 1) expect(row[i].x, 'siblings fan out left to right').toBeGreaterThan(row[i - 1].x);

  // Each second-level child sits below its parent, left edges aligned.
  const integ = await boxOf(page, 'ses-integ-01');
  const secondLevel = kids.get('ses-integ-01');
  expect(secondLevel.length).toBeGreaterThan(1);
  let above = integ;
  for (const id of secondLevel) {
    const b = await boxOf(page, id);
    expect(b.y, `${id} is below its parent`).toBeGreaterThanOrEqual(integ.y + integ.height - 1);
    expect(Math.abs(b.x - integ.x), `${id} left edge aligns with the parent's`).toBeLessThanOrEqual(3);
    if (above !== integ) expect(b.y, `${id} stacks below the previous sibling`).toBeGreaterThan(above.y);
    above = b;
  }

  // A third-level child keeps the same left edge and sits below its parent.
  const a2 = await boxOf(page, 'ses-worker-a2');
  const helper = await boxOf(page, 'ses-helper-01');
  expect(Math.abs(helper.x - a2.x)).toBeLessThanOrEqual(3);
  expect(helper.y).toBeGreaterThan(a2.y);
  await shot(page, 'tree-layout');
});

test('every recorded parent-child edge has a square-cornered connector and a port dot', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const expected = projectSessions.filter((s) => s.parent_session_id).map((s) => `${s.parent_session_id}>${s.id}`);
  const edges = page.locator('path.ancestry-edge');
  await expect(edges).toHaveCount(expected.length);
  const pairs = await edges.evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));
  expect(pairs.sort()).toEqual([...expected].sort());
  // Right angles only: M/L/H/V commands, never curves.
  const curved = await edges.evaluateAll((els) => els.map((e) => e.getAttribute('d')).filter((d) => /[CQSTAcqsta]/.test(d)));
  expect(curved, 'ancestry connectors must be square-cornered').toEqual([]);
  // A port dot under every parent that shows children.
  const parents = new Set(await edges.evaluateAll((els) => els.map((e) => e.dataset.via || e.dataset.from)));
  await expect(page.locator('circle.port-dot')).toHaveCount(parents.size);
  for (const pid of parents) await expect(page.locator(`circle.port-dot[data-parent="${pid}"]`)).toHaveCount(1);
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
