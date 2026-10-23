// Shared shell and removed routes, synthetic prototype evidence only.
import { test, expect } from '@playwright/test';
import { PID, snapshot, shot } from './helpers.js';

const sidebar = (page) => page.getByRole('complementary', { name: 'Sidebar', exact: true });

test('sidebar lists the executive, project branch, Setup and Settings', async ({ page }) => {
  await page.goto('/#/agents');
  const nav = sidebar(page).getByRole('navigation', { name: 'Primary' });
  await expect(page.getByTestId('sidebar-executive')).toHaveAttribute('aria-current', 'page');
  for (const project of snapshot.projects) {
    await expect(nav.locator(`a[href="#/projects/${project.id}"]`)).toContainText(project.name);
  }
  await expect(nav.getByRole('link', { name: 'Setup', exact: true })).toHaveAttribute('href', '#/setup');
  await expect(nav.getByRole('link', { name: 'Settings', exact: true })).toHaveAttribute('href', '#/settings/providers');
  await expect(nav.locator('.sidebar-views')).toHaveCount(0);
  await expect(sidebar(page).getByTestId('theme-toggle')).toBeVisible();
  await expect(sidebar(page).getByTestId('synthetic-badge')).toBeVisible();
  await shot(page, 'shell-sidebar');
});

test('the sidebar changes between drawer and desktop navigation on resize', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
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

test('layout switching preserves selection, reload and browser history', async ({ page }) => {
  await page.goto(`/#/projects/${PID}/sessions/ses-worker-a2`);
  const detail = page.getByTestId('detail-panel');
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(detail).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await page.reload();
  await expect(page.getByTestId('list-view')).toBeVisible();
  await expect(detail).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await page.getByRole('button', { name: 'Go to parent' }).click();
  await expect(page).toHaveURL(/sessions\/ses-integ-01$/);
  await page.goBack();
  await expect(detail).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await page.goForward();
  await expect(detail).toHaveAttribute('data-session-id', 'ses-integ-01');
  await page.getByRole('button', { name: 'Tree', exact: true }).click();
  await expect(page.locator('[data-testid="session-card"].selected')).toHaveAttribute('data-session-id', 'ses-integ-01');
  await page.getByRole('complementary', { name: 'Session details' }).getByRole('button', { name: 'Close' }).click();
  await expect(page).toHaveURL(new RegExp(`/projects/${PID}$`));
  await expect(detail).toHaveCount(0);
});

for (const view of ['queue', 'lanes', 'graph', 'decisions', 'board']) {
  test(`${view} and its session route are deferred and render not found`, async ({ page }) => {
    for (const suffix of ['', '/sessions/ses-worker-a2']) {
      await page.goto(`/#/projects/${PID}/${view}${suffix}`);
      await expect(page.getByTestId('not-found')).toContainText('Page not found');
      await expect(page.getByTestId('view-placeholder')).toHaveCount(0);
      await expect(page.getByTestId('detail-panel')).toHaveCount(0);
    }
  });
}

test('Setup progress links to the wizard and Settings has its own section tabs', async ({ page }) => {
  await page.goto('/#/agents');
  await page.getByTestId('setup-progress-card').click();
  await expect(page).toHaveURL(/setup\/roles$/);
  for (const step of ['providers', 'harnesses', 'models', 'roles', 'review']) {
    await page.goto(`/#/setup/${step}`);
    await expect(page.getByRole('navigation', { name: 'Setup steps' })).toBeVisible();
    await expect(page.locator('.setup-panel-current')).toBeVisible();
  }
  await sidebar(page).getByRole('link', { name: 'Settings', exact: true }).click();
  const tabs = page.getByRole('navigation', { name: 'Settings sections' });
  for (const section of ['Providers', 'Harnesses', 'Models', 'Roles']) {
    await tabs.getByRole('link', { name: section, exact: true }).click();
    await expect(tabs.getByRole('link', { name: section, exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(`Settings: ${section}`);
  }
});

test('unknown views, steps and sections render the existing not-found page', async ({ page }) => {
  for (const hash of [`#/projects/${PID}/unknown`, '#/setup/unknown', '#/settings/review']) {
    await page.goto(`/${hash}`);
    await expect(page.getByTestId('not-found')).toContainText('Page not found');
    await expect(page.getByTestId('setup-placeholder')).toHaveCount(0);
  }
});
