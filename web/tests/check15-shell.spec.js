// R1 (synthetic prototype): shared shell, URL-based project views and
// honest placeholders. The browser still sends no commands.
import { test, expect } from '@playwright/test';
import { PID, snapshot, shot } from './helpers.js';

const views = ['Tree', 'Queue', 'Lanes', 'Graph', 'Decisions', 'Board'];
const sections = ['providers', 'harnesses', 'models', 'roles'];
const projectUrl = (view = '', sid = '') => `/#/projects/${PID}${view ? `/${view}` : ''}${sid ? `/sessions/${sid}` : ''}`;
const sidebar = (page) => page.getByRole('complementary', { name: 'Sidebar', exact: true });
const switcher = (page) => page.getByRole('navigation', { name: 'Project views', exact: true });

test('sidebar lists snapshot projects, current project views and setup links', async ({ page }) => {
  await page.goto('/#/');
  const nav = sidebar(page).getByRole('navigation', { name: 'Primary' });
  await expect(nav.getByRole('link', { name: 'Overview', exact: true })).toHaveAttribute('aria-current', 'page');
  for (const project of snapshot.projects) {
    await expect(nav.getByRole('link', { name: project.name, exact: true })).toHaveAttribute('href', `#/projects/${project.id}`);
  }
  await expect(nav.locator('.sidebar-views')).toHaveCount(0);
  await expect(nav.getByRole('link', { name: 'Setup guide' })).toHaveAttribute('href', '#/setup');
  for (const section of sections) await expect(nav.locator(`a[href="#/settings/${section}"]`)).toHaveCount(1);
  await nav.locator(`a[href="#/projects/${PID}"]`).click();
  await expect(nav.locator('.sidebar-views')).toHaveCount(1);
  for (const name of views) await expect(nav.getByRole('link', { name, exact: true })).toBeVisible();
  await nav.getByRole('link', { name: 'Queue', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${PID}/queue$`));
  await expect(nav.getByRole('link', { name: 'Queue', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(sidebar(page).getByTestId('theme-toggle')).toBeVisible();
  await expect(sidebar(page).getByTestId('synthetic-badge')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Apply next synthetic update' })).toBeVisible();
  await shot(page, 'shell-sidebar');
});

test('the 800px drawer opens by keyboard, traps focus and closes on Escape or navigation', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 900 });
  await page.goto(projectUrl());
  const menu = page.getByRole('button', { name: 'Open menu', exact: true });
  const drawer = page.getByRole('dialog', { name: 'Sidebar', exact: true });
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await expect(drawer).not.toBeVisible();
  await menu.focus();
  await page.keyboard.press('Enter');
  await expect(drawer).toBeVisible();
  await expect(menu).toHaveAttribute('aria-expanded', 'true');
  const last = drawer.getByTestId('theme-toggle');
  await last.focus();
  await page.keyboard.press('Tab');
  // Chromium visits browser chrome before cycling back into the modal.
  await expect(menu).not.toBeFocused();
  await page.keyboard.press('Tab');
  await expect(drawer.getByRole('link', { name: 'Odin', exact: true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(drawer).not.toBeVisible();
  await expect(menu).toBeFocused();
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await menu.click();
  await drawer.getByRole('button', { name: 'Close menu' }).click();
  await expect(drawer).not.toBeVisible();
  await menu.click();
  await drawer.getByRole('link', { name: 'Graph', exact: true }).click();
  await expect(page).toHaveURL(/\/graph$/);
  await expect(drawer).not.toBeVisible();
  await expect(page.getByTestId('view-placeholder')).toBeVisible();
  await shot(page, 'shell-800');
});

test('the sidebar changes between drawer and desktop navigation on resize', async ({ page }) => {
  await page.goto(projectUrl());
  await expect(sidebar(page)).toBeVisible();
  await page.setViewportSize({ width: 800, height: 900 });
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(page.getByRole('dialog', { name: 'Sidebar', exact: true })).toBeVisible();
  await page.setViewportSize({ width: 900, height: 900 });
  await expect(sidebar(page)).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Sidebar', exact: true })).toHaveCount(0);
  await page.setViewportSize({ width: 800, height: 900 });
  await expect(page.getByRole('button', { name: 'Open menu' })).toHaveAttribute('aria-expanded', 'false');
});

test('view switcher preserves session selection, reload and history round trips', async ({ page }) => {
  const sid = 'ses-worker-a2';
  await page.goto(projectUrl('queue', sid));
  const detail = page.getByTestId('detail-panel');
  await expect(detail).toHaveAttribute('data-session-id', sid);
  await expect(switcher(page).getByRole('link', { name: 'Queue', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.reload();
  await expect(detail).toHaveAttribute('data-session-id', sid);
  const graph = switcher(page).getByRole('link', { name: 'Graph', exact: true });
  await graph.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(new RegExp(`/graph/sessions/${sid}$`));
  await expect(detail).toHaveAttribute('data-session-id', sid);
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/queue/sessions/${sid}$`));
  await page.goForward();
  await expect(page).toHaveURL(new RegExp(`/graph/sessions/${sid}$`));
  await switcher(page).getByRole('link', { name: 'Tree', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${PID}/sessions/${sid}$`));
  await expect(page.getByTestId('tree-view')).toBeVisible();
  await expect(page.locator('[data-testid="session-card"].selected')).toHaveAttribute('data-session-id', sid);
  await switcher(page).getByRole('link', { name: 'Board', exact: true }).click();
  await page.getByRole('complementary', { name: 'Session details' }).getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${PID}/board$`));
  await expect(detail).toHaveCount(0);
});

const panels = [
  ['queue', 'Agent Queue', 'Pending assignments', 'Reprioritize work'],
  ['lanes', 'Agent Lanes', 'Parallel activity over time', 'Select an interval'],
  ['graph', 'Agent Graph', 'Relationships among planners', 'Follow a dependency'],
  ['decisions', 'Decision Tree', 'Recorded alternatives', 'Choose an option'],
  ['board', 'Delegate Board', 'Assignment distribution', 'Assign work'],
];
for (const [view, title, reveals, control] of panels) {
  test(`${view} shows its planned purpose, records and disabled controls`, async ({ page }) => {
    await page.goto(projectUrl(view));
    const panel = page.getByTestId('view-placeholder');
    await expect(panel.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await expect(panel).toContainText(reveals);
    await expect(panel).toContainText('Not built yet');
    await expect(panel).toContainText('Records needed');
    await expect(panel).toContainText('Commands are not connected');
    await expect(panel.getByRole('button', { name: control, exact: true })).toBeDisabled();
    for (const button of await panel.getByRole('button').all()) {
      await expect(button).toBeDisabled();
      await expect(button).toHaveAccessibleDescription('Commands are not connected');
    }
    await expect(page.getByTestId('tree-view')).toHaveCount(0);
    await switcher(page).getByRole('link', { name: 'Tree', exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/projects/${PID}$`));
    await expect(page.getByTestId('tree-view')).toBeVisible();
  });
}

test('session selection from attention and details stays in the current view', async ({ page }) => {
  await page.goto(projectUrl('lanes'));
  await page.getByTestId('chip-needs').click();
  await page.getByTestId('attention-popover').getByRole('link').click();
  await expect(page).toHaveURL(/\/lanes\/sessions\/ses-review-exec$/);
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-review-exec');
  await page.goto(projectUrl('queue', 'missing'));
  await expect(page.getByTestId('not-found')).toContainText('Session not found');
  await page.getByTestId('not-found').getByRole('link', { name: 'Back to the project' }).click();
  await expect(page).toHaveURL(/\/queue$/);
});

test('setup guide links to the wizard and setup and settings routes open their panels', async ({ page }) => {
  await page.goto('/#/');
  const guide = page.getByTestId('setup-guide');
  await expect(guide.getByRole('heading', { name: 'Finish setup' })).toBeVisible();
  await guide.getByRole('link', { name: 'Finish setup' }).click();
  await expect(page).toHaveURL(/#\/setup\/roles$/);
  await expect(page.getByTestId('setup-placeholder').getByRole('heading', { level: 1 })).toHaveText('Configure Odin’s roles');
  for (const step of [...sections, 'review']) {
    await page.goto(`/#/setup/${step}`);
    await expect(page.getByRole('navigation', { name: 'Setup steps' })).toBeVisible();
    await expect(page.locator('.setup-panel-current')).toBeVisible();
    await expect(page.getByTestId('setup-placeholder')).toContainText('Synthetic: not saved');
  }
  for (const section of sections) {
    await sidebar(page).locator(`a[href="#/settings/${section}"]`).click();
    await expect(page.getByTestId('setup-placeholder')).toContainText(`Settings: ${section[0].toUpperCase() + section.slice(1)}`);
  }
});

test('unknown views, steps and sections render the existing not-found page', async ({ page }) => {
  for (const hash of [`#/projects/${PID}/unknown`, `#/projects/${PID}/unknown/sessions/ses-worker-a2`, '#/setup/unknown', '#/settings/review']) {
    await page.goto(`/${hash}`);
    await expect(page.getByTestId('not-found')).toContainText('Page not found');
    await expect(page.getByTestId('view-placeholder')).toHaveCount(0);
    await expect(page.getByTestId('setup-placeholder')).toHaveCount(0);
  }
});
