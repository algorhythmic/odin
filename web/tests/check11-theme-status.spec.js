// Pass 4 brief items 1, 5 and 6 (synthetic): dark theme is the default
// and the toggle persists through the layout preferences; the synthetic
// notice is a quiet header badge, not a banner; cards carry the new
// status set with icons; stopped and superseded cards are dimmed; model
// names are friendly and the task text wraps.
import { test, expect } from '@playwright/test';
import { PID, shot, snapshot } from './helpers.js';

const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const theme = (page) => page.evaluate(() => document.documentElement.dataset.theme);
const bodyBg = (page) => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const storedPrefs = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('odin-web-prefs:v1') || '{}'));

test.describe('theme', () => {
  // Even a light system preference must not lighten the default theme.
  test.use({ colorScheme: 'light' });

  test('dark theme is the default whatever the system prefers', async ({ page }) => {
    await page.goto('/#/');
    await expect(page.getByTestId('session-card').first()).toBeVisible();
    expect(await theme(page)).toBe('dark');
    expect(await bodyBg(page)).toBe('rgb(16, 20, 25)');
    expect((await storedPrefs(page)).theme).toBeUndefined();
    await shot(page, 'theme-dark-default');
  });

  test('the toggle switches theme and persists it across reload', async ({ page }) => {
    await page.goto('/#/');
    const toggle = page.getByTestId('theme-toggle');
    await expect(toggle).toHaveText('Theme: Dark');
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');

    await toggle.click();
    expect(await theme(page)).toBe('light');
    expect(await bodyBg(page)).toBe('rgb(245, 246, 248)');
    await expect(toggle).toHaveText('Theme: Light');
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect((await storedPrefs(page)).theme).toBe('light');
    await shot(page, 'theme-light');

    await page.reload();
    await expect(page.getByTestId('workspace')).toBeVisible();
    expect(await theme(page)).toBe('light');
    expect(await bodyBg(page)).toBe('rgb(245, 246, 248)');

    await page.getByTestId('theme-toggle').click();
    expect(await theme(page)).toBe('dark');
    expect((await storedPrefs(page)).theme).toBe('dark');
  });

  test('an unknown stored theme falls back to dark', async ({ page }) => {
    await page.goto('/#/');
    await page.evaluate(() => {
      localStorage.setItem('odin-web-prefs:v1', JSON.stringify({ theme: 'neon', mode: 'tree' }));
    });
    await page.reload();
    await expect(page.getByTestId('workspace')).toBeVisible();
    expect(await theme(page)).toBe('dark');
    expect(await bodyBg(page)).toBe('rgb(16, 20, 25)');
  });
});

test('a quiet synthetic badge in the header replaces the banner on every view', async ({ page }) => {
  const badge = page.getByTestId('synthetic-badge');
  for (const hash of ['#/', `#/projects/${PID}`, `#/projects/${PID}/history`]) {
    await page.goto(`/${hash}`);
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText('Synthetic data');
    await expect(badge).toHaveAttribute('aria-label', /prototype, not connected/);
    // The old full-width banner is gone.
    await expect(page.locator('.synthetic-banner')).toHaveCount(0);
  }
});

test('every status renders its label and icon on the card', async ({ page }) => {
  await page.goto('/#/');
  const cases = [
    ['ses-exec-01', 'Running', 'status-icon-spinner'],
    ['ses-review-exec', 'Needs you', 'status-icon-clock'],
    ['ses-worker-a2', 'Done', 'status-icon-check'],
    ['ses-worker-a1', 'Failed', 'status-icon-triangle'],
    ['ses-helper-01', 'Stopped', 'status-icon-square'],
  ];
  for (const [id, label, icon] of cases) {
    const chip = card(page, id).getByTestId('status-chip');
    await expect(chip.getByTestId('state-label')).toHaveText(label);
    const svg = chip.getByTestId(icon);
    await expect(svg).toBeVisible();
    await expect(svg).toHaveAttribute('aria-label', label);
  }
  // Idle and host-offline keep their precise recorded labels.
  await expect(card(page, 'ses-review-integ').getByTestId('state-label')).toHaveText('Idle');
  await expect(card(page, 'ses-ops-01').getByTestId('state-label')).toHaveText('Host offline');
  // No "Waiting for input" label survives anywhere.
  await expect(page.getByTestId('tree-view')).not.toContainText('Waiting for input');
  await shot(page, 'status-set');
});

test('stopped cards and superseded attempts are dimmed', async ({ page }) => {
  await page.goto('/#/');
  for (const id of ['ses-helper-01', 'ses-worker-a1']) {
    await expect(card(page, id)).toHaveAttribute('data-dimmed', 'true');
    const opacity = await card(page, id).evaluate((el) => Number(getComputedStyle(el).opacity));
    expect(opacity, `${id} is dimmed`).toBeLessThan(1);
  }
  // A current attempt and a running card are not dimmed.
  for (const id of ['ses-worker-a2', 'ses-exec-01']) {
    const opacity = await card(page, id).evaluate((el) => Number(getComputedStyle(el).opacity));
    expect(opacity, `${id} is not dimmed`).toBe(1);
  }
});

test('cards show a provider monogram and a friendly model name', async ({ page }) => {
  await page.goto('/#/');
  const expected = new Map(snapshot.sessions.filter((s) => s.project_id === PID).map((s) => [s.id, s.model]));
  const names = {
    'claude-opus-5-5': 'Opus 5.5',
    'claude-sonnet-5-5': 'Sonnet 5.5',
    'claude-haiku-5-5': 'Haiku 5.5',
    'claude-fable-5-1': 'Fable 5.1',
  };
  await expect(card(page, 'ses-exec-01').getByTestId('model-name')).toHaveText('Fable 5.1');
  await expect(card(page, 'ses-exec-01')).not.toContainText('claude-fable-5-1');
  for (const [id, provider] of [['ses-exec-01', 'anthropic'], ['ses-ops-01', 'openai'], ['ses-helper-01', 'unknown']]) {
    await expect(card(page, id).getByTestId('provider-logo')).toHaveAttribute('data-provider', provider);
  }
  for (const [id, model] of expected) {
    if (model === null) continue;
    await expect(card(page, id).getByTestId('model-name')).toHaveText(names[model] || model);
  }
});

test('the task text wraps to two lines instead of truncating to one', async ({ page }) => {
  await page.goto('/#/');
  const task = card(page, 'ses-exec-01').getByTestId('task-text');
  await expect(task).toBeVisible();
  const style = await task.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { whiteSpace: cs.whiteSpace, textOverflow: cs.textOverflow, lineClamp: cs.webkitLineClamp };
  });
  expect(style.whiteSpace).not.toBe('nowrap');
  expect(style.lineClamp).toBe('2');
  // A second line actually renders: the clamped box is taller than one line.
  const box = await task.boundingBox();
  expect(box.height).toBeGreaterThan(25);
});
