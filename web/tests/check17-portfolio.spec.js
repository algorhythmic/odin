// R3a: grouping is presentation; ancestry and usage still come from records.
import { test, expect } from '@playwright/test';
import { PID, snapshot, shot } from './helpers.js';

const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const project = (page, id) => page.locator(`[data-testid="project-node"][data-project-id="${id}"]`);
const sidebarProject = (page, id) => page.locator(`[data-testid="sidebar-project"][data-project-id="${id}"]`);
const edges = (page, kind) => page.locator(`path.${kind}`).evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));

test('one executive, ordered grouping nodes and recorded ancestry through projects', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('session-card')).toHaveCount(snapshot.sessions.length);
  await expect(page.getByRole('region', { name: 'Agent tree canvas' })).toBeInViewport();
  await expect(card(page, snapshot.executive_session_id).getByRole('button', { name: 'Collapse 4 projects under executive' }))
    .toHaveText('▾ 4');
  await expect(page.locator('[data-testid="session-card"][data-role="executive"]')).toHaveCount(1);
  await expect(card(page, snapshot.executive_session_id)).toHaveAttribute('data-parent', '');
  expect(await page.getByTestId('project-node').evaluateAll((els) => els.map((e) => e.dataset.projectId)))
    .toEqual(snapshot.projects.map((p) => p.id));
  const groups = await edges(page, 'project-edge');
  for (const p of snapshot.projects) {
    expect(groups).toContain(`${snapshot.executive_session_id}>project:${p.id}`);
    await expect(project(page, p.id).getByTestId('status-chip')).toHaveCount(0);
  }
  const ancestry = await edges(page, 'ancestry-edge');
  for (const s of snapshot.sessions.filter((s) => s.parent_session_id === snapshot.executive_session_id)) {
    expect(ancestry).toContain(`${snapshot.executive_session_id}>${s.id}`);
    await expect(page.locator(`path.ancestry-edge[data-to="${s.id}"]`)).toHaveAttribute('data-via', `project:${s.project_id}`);
  }
  await expect(page.locator('.legend')).toContainText('started (ancestry)');
  await expect(page.locator('.legend')).toContainText('project');
  await expect(page.locator('.legend')).toContainText('reviews');
  await shot(page, 'portfolio-tree');
});

test('labelled roots hang from project groupings with no invented ancestry', async ({ page }) => {
  await page.goto('/#/');
  const groups = await edges(page, 'project-edge');
  const ancestry = await edges(page, 'ancestry-edge');
  for (const [id, pid, label] of [
    ['ses-imported-01', PID, 'Imported — parent unknown'],
    ['ses-pin-audit', 'proj-contract-pins', 'Parent not in this project view'],
    ['ses-mal-cycle-a', 'proj-malformed', 'Parent cycle in records'],
    ['ses-mal-cycle-b', 'proj-malformed', 'Parent cycle in records'],
    ['ses-mal-self', 'proj-malformed', 'Parent cycle in records'],
  ]) {
    expect(groups).toContain(`project:${pid}>${id}`);
    expect(ancestry.some((e) => e.endsWith(`>${id}`))).toBe(false);
    await expect(card(page, id).getByTestId('lineage-label')).toHaveText(label);
  }
  expect(ancestry).toContain('ses-mal-cycle-a>ses-mal-cycle-child');
});

test('sidebar hover and focus highlight a branch without changing geometry', async ({ page }) => {
  await page.goto('/#/');
  const target = sidebarProject(page, PID);
  const before = await project(page, PID).boundingBox();
  await target.hover();
  await expect(project(page, PID)).not.toHaveClass(/branch-muted/);
  await expect(project(page, 'proj-contract-pins')).toHaveClass(/branch-muted/);
  await expect(card(page, 'ses-pin-worker')).toHaveClass(/branch-muted/);
  expect(await project(page, PID).boundingBox()).toEqual(before);
  await page.getByTestId('sidebar-executive').hover();
  await expect(project(page, 'proj-contract-pins')).not.toHaveClass(/branch-muted/);
  await target.focus();
  await expect(project(page, 'proj-contract-pins')).toHaveClass(/branch-muted/);
  await page.keyboard.press('Tab');
  await expect(project(page, PID)).toHaveClass(/branch-muted/);
  await page.getByTestId('sidebar-executive').focus();
  await expect(project(page, PID)).not.toHaveClass(/branch-muted/);
  await target.click();
  await sidebarProject(page, 'proj-contract-pins').hover();
  await expect(project(page, PID)).not.toHaveClass(/branch-muted/);
});

test('scope keeps one project, a compact executive and All projects; session routes still work', async ({ page }) => {
  await page.goto('/#/');
  await sidebarProject(page, PID).click();
  await expect(page).toHaveURL(new RegExp(`projects/${PID}$`));
  await expect(page.getByTestId('project-node')).toHaveCount(1);
  await expect(page.getByTestId('executive-header')).toContainText('executive');
  await expect(page.getByTestId('executive-header')).toContainText('Fable 5.1');
  await expect(page.getByTestId('executive-header')).toContainText('Running');
  await expect(card(page, snapshot.executive_session_id)).toHaveCount(0);
  await card(page, 'ses-integ-01').getByRole('button', { name: /integration owner/ }).first().click();
  await expect(page).toHaveURL(new RegExp(`projects/${PID}/sessions/ses-integ-01$`));
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-integ-01');
  await page.getByRole('link', { name: 'All projects', exact: true }).click();
  await expect(page).toHaveURL(/#\/$/);
  await page.goto('/#/sessions/ses-exec-01');
  await expect(card(page, 'ses-exec-01')).toHaveClass(/selected/);
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-exec-01');
});

test('portfolio History reuses the view grouped in snapshot project order', async ({ page }) => {
  await page.goto('/#/');
  await page.getByRole('link', { name: 'History', exact: true }).click();
  await expect(page).toHaveURL(/#\/history$/);
  await expect(page.getByTestId('history')).toHaveCount(snapshot.projects.length);
  expect(await page.locator('.portfolio-history > section').evaluateAll((els) => els.map((e) => e.dataset.projectId)))
    .toEqual(snapshot.projects.map((p) => p.id));
  await expect(page.locator('tr[data-session-id="ses-worker-a1"]')).toHaveCount(1);
  await expect(page.locator('tr[data-session-id="ses-pin-audit"]')).toHaveCount(1);
  await page.locator('tr[data-session-id="ses-pin-audit"] a').click();
  await expect(page).toHaveURL(/projects\/proj-contract-pins\/sessions\/ses-pin-audit$/);
});

test('header has one line of controls and no repeated attention summary or removed views', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto('/#/');
  const header = page.getByTestId('tree-header');
  await expect(header.getByRole('heading', { name: 'Portfolio', exact: true })).toBeVisible();
  await expect(header.getByTestId('agent-summary')).toHaveText('20 agents · 5 running');
  await expect(header.getByTestId('agent-summary')).not.toContainText(/needs you|failed/);
  await expect(header.getByTestId('project-tokens')).toContainText(/tok \+ \d+ unknown/);
  // One line at a wide viewport; the header may wrap on narrower ones so no control is clipped.
  const tops = await header.evaluate((el) => [...el.children].filter((c) => c.offsetParent)
    .map((c) => Math.round(c.getBoundingClientRect().top + c.getBoundingClientRect().height / 2)));
  expect(Math.max(...tops) - Math.min(...tops)).toBeLessThanOrEqual(6);
  await expect(header).not.toContainText(/sessions,|roots/);
  await expect(page.locator('.view-switcher, .conversation, .overview')).toHaveCount(0);
  for (const label of ['Projects', 'Conversation']) await expect(header.getByRole('button', { name: label })).toHaveCount(0);
});

for (const mode of ['Tree', 'List']) test(`project groupings are keyboard reachable and collapsible in ${mode}`, async ({ page }) => {
  await page.goto('/#/');
  await page.getByRole('button', { name: mode, exact: true }).click();
  if (mode === 'Tree') {
    const node = project(page, PID);
    // Walk the actual tab order to the project button.
    await page.getByRole('region', { name: 'Agent tree canvas' }).focus();
    for (let i = 0; i < 10 && !(await node.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('Tab');
    await expect(node).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(node).toHaveAttribute('aria-expanded', 'false');
    await expect(card(page, 'ses-integ-01')).toHaveCount(0);
    await page.keyboard.press('Space');
    await expect(node).toHaveAttribute('aria-expanded', 'true');
  } else {
    const tree = page.getByRole('tree');
    const node = tree.getByRole('treeitem', { name: 'Project Odin web app (synthetic)', exact: true });
    await page.getByRole('button', { name: 'List', exact: true }).focus();
    await page.keyboard.press('Tab');
    await page.keyboard.press('ArrowDown');
    await expect(node).toBeFocused();
    await page.keyboard.press('ArrowLeft');
    await expect(node).toHaveAttribute('aria-expanded', 'false');
    await page.keyboard.press('ArrowRight');
    await expect(node).toHaveAttribute('aria-expanded', 'true');
    await page.keyboard.press('Enter');
    await expect(node).toHaveAttribute('aria-expanded', 'false');
    await expect(node).not.toHaveAttribute('aria-selected');
  }
  await expect(page).toHaveURL(/#\/$/);
  await expect(page.getByTestId('detail-panel')).toHaveCount(0);
});

test('800px drawer opens by keyboard, traps focus, closes and scopes on navigation', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 900 });
  await page.goto('/#/');
  const menu = page.getByRole('button', { name: 'Open menu' });
  const drawer = page.getByRole('dialog', { name: 'Sidebar', exact: true });
  await menu.focus();
  await page.keyboard.press('Enter');
  await expect(drawer).toBeVisible();
  await drawer.getByTestId('theme-toggle').focus();
  const brand = drawer.getByRole('link', { name: 'Odin', exact: true });
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press('Tab');
    await expect(menu).not.toBeFocused();
    if (await brand.evaluate((el) => el === document.activeElement)) break;
  }
  await expect(brand).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(drawer).not.toBeVisible();
  await expect(menu).toBeFocused();
  await menu.click();
  await drawer.getByRole('button', { name: 'Close menu' }).click();
  await expect(drawer).not.toBeVisible();
  await menu.click();
  await sidebarProject(page, PID).click();
  await expect(drawer).not.toBeVisible();
  await expect(page.getByTestId('project-node')).toHaveCount(1);
  await shot(page, 'portfolio-800');
});

test('portfolio, project and executive totals sum own usage without grouping or duplicate descendants', async ({ page }) => {
  const sum = (sessions, compactUnknown = false) => {
    const known = sessions.filter((s) => s.tokens.basis !== 'unknown');
    const unknown = sessions.length - known.length;
    if (!known.length) return `unknown (${unknown})`;
    const n = known.reduce((total, s) => total + s.tokens.uncached_input + s.tokens.cache_write + s.tokens.output, 0);
    const compact = n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;
    let text = `${known.some((s) => s.tokens.basis === 'estimate') ? 'est. ' : ''}${compact} tok`;
    if (unknown) text += compactUnknown ? ` + ${unknown} unknown` : ` + unknown (${unknown})`;
    return text;
  };
  await page.goto('/#/');
  await expect(page.getByTestId('project-tokens')).toHaveText(sum(snapshot.sessions, true));
  for (const p of snapshot.projects) {
    await expect(project(page, p.id)).toContainText(sum(snapshot.sessions.filter((s) => s.project_id === p.id)));
  }
  // These records have no admitted path to the executive, despite sharing a project group.
  const outside = new Set([
    'ses-imported-01', 'ses-pin-audit', 'ses-pin-audit-helper',
    'ses-mal-cycle-a', 'ses-mal-cycle-b', 'ses-mal-cycle-child', 'ses-mal-self',
  ]);
  const executiveTotal = sum(snapshot.sessions.filter((s) => !outside.has(s.id)));
  await expect(card(page, snapshot.executive_session_id).getByTestId('branch-tokens')).toHaveText(`branch ${executiveTotal}`);
  await page.goto('/#/sessions/ses-exec-01');
  await expect(page.getByTestId('detail-branch-tokens')).toHaveText(executiveTotal);
});

test('large portfolio starts at project nodes and a deep link reveals its recorded ancestors', async ({ page }) => {
  await page.goto('/?dataset=large#/');
  await expect(page.getByTestId('session-card')).toHaveCount(1);
  await expect(page.getByTestId('project-node')).toHaveCount(1);
  await expect(page.getByTestId('project-node')).toHaveAttribute('aria-expanded', 'false');
  // The generator's fixed spine ends at this session at project depth 8.
  await page.goto('/?dataset=large#/sessions/ses-L-0046');
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-L-0046');
  await expect(card(page, 'ses-L-0046')).toBeInViewport();
  await expect(page.getByTestId('project-node')).toHaveAttribute('aria-expanded', 'true');
});
