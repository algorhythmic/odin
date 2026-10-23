// R3c coverage is synthetic prototype evidence, including the W3a sample display.
import { test, expect } from '@playwright/test';
import { PID, shot } from './helpers.js';
const panel = (page) => page.locator('#app-sidebar');
const handle = (page) => page.getByRole('separator', { name: 'Sidebar width' });
const meter = (page, id) => page.locator(`[data-testid="usage-meter"][data-lineage-id="${id}"]`);
const windowFor = (page, label, id = 'executive-login') => meter(page, id).locator(`[data-label="${label}"]`);
const collapse = (page) => page.getByRole('button', { name: 'Collapse sidebar', exact: true });
const expand = (page) => page.getByRole('button', { name: 'Expand sidebar', exact: true });
const width = (page) => panel(page).evaluate((el) => el.getBoundingClientRect().width);
async function resizeKey(page, key, expected) {
  await handle(page).focus();
  await page.keyboard.press(key);
  await expect(handle(page)).toHaveAttribute('aria-valuenow', `${expected}`);
  await expect.poll(() => width(page)).toBe(expected);
}
test('usage shows exact bands, thresholds, reset intervals, monograms and explicit unavailable probes', async ({ page }) => {
  await page.goto('/#/agents');
  await expect(page.getByTestId('usage-meter')).toHaveCount(3);
  const executive = meter(page, 'executive-login');
  await expect(executive.getByRole('img', { name: 'Anthropic' })).toBeVisible();
  for (const id of ['executive-login', 'delegation-login', 'evaluator-codex-login']) {
    await meter(page, id).getByRole('button', { name: /^Usage details/ }).click();
  }
  for (const [label, percent, band, ticks, id] of [
    ['claude.five_hour', 42, 'clear', [85, 90, 95], 'executive-login'],
    ['claude.weekly', 81, 'wind down', [80, 85, 90], 'executive-login'],
    ['claude.weekly.fable', 64, 'clear', [85, 90, 95], 'executive-login'],
    ['claude.five_hour', 12, 'clear', [85, 90, 95], 'delegation-login'],
    ['codex.five_hour', 91, 'ordinary stop', [85, 90, 95], 'evaluator-codex-login'],
    ['codex.weekly', 38, 'clear', [80, 85, 90], 'evaluator-codex-login'],
  ]) {
    const w = windowFor(page, label, id);
    await expect(w.getByRole('meter')).toHaveAttribute('aria-valuenow', `${percent}`);
    await expect(w.getByRole('meter')).toHaveAttribute('title', label);
    await expect(w.getByRole('meter')).toHaveAccessibleDescription(new RegExp(label.replaceAll('.', '\\.')));
    await expect(w.getByRole('meter')).toHaveAttribute('aria-valuetext', new RegExp(`${percent} % · ${band}`));
    await expect(w.locator('.usage-band')).toHaveText(band);
    const positions = await w.locator('.usage-tick').evaluateAll((els) => els.map((el) => el.style.left));
    expect(positions).toEqual(ticks.map((n) => `${n}%`));
    await expect(w.locator('.usage-thresholds')).toHaveText(`Band thresholds: ${ticks.join(', ')} percent.`);
  }
  await expect(windowFor(page, 'claude.five_hour')).toContainText('resets in 2h 10m');
  await expect(windowFor(page, 'claude.weekly')).toContainText('resets in 3d');
  await expect(windowFor(page, 'claude.weekly.fable').locator('.usage-window-head')).toContainText('Weekly · Fable');
  const unavailable = windowFor(page, 'claude.weekly', 'delegation-login');
  await expect(unavailable).toContainText('Probe unavailable · credential not readable');
  await expect(unavailable.getByRole('meter')).toHaveCount(0);
  await expect(unavailable).not.toContainText('0 %');
  await expect(executive).toContainText('184.2k tok · five hour');
  await expect(meter(page, 'delegation-login')).toContainText('Token usage unknown');
  await expect(meter(page, 'evaluator-codex-login')).toContainText('est. 68.2k tok · five hour');
  await expect(panel(page).getByText(/Synthetic samples/)).toHaveCount(1);
  await shot(page, 'sidebar-dashboard-dark');
});

test('meters follow setup connection, disconnect, label edits and discard; new lineages have no samples', async ({ page }) => {
  await page.goto('/?setup=fresh#/settings/providers');
  await expect(page.getByTestId('usage-meter')).toHaveCount(0);
  const row = page.getByTestId('lineage-executive-login');
  await row.getByRole('button', { name: 'Connect Executive login', exact: true }).click();
  await expect(page.getByTestId('usage-meter')).toHaveCount(0);
  await row.getByRole('button', { name: 'Simulate completed sign-in (synthetic)' }).click();
  await expect(page.getByTestId('usage-meter')).toHaveCount(1);
  await row.getByRole('textbox').fill('Coordination login');
  await expect(meter(page, 'executive-login').locator('.usage-sign-in-label')).toHaveText('Coordination login');
  await row.getByRole('button', { name: 'Disconnect Coordination login', exact: true }).click();
  await expect(page.getByTestId('usage-meter')).toHaveCount(0);
  await page.getByRole('button', { name: /Add another sign-in for Anthropic/ }).click();
  const extra = page.getByTestId('lineage-anthropic-sign-in-3');
  await extra.getByRole('button', { name: 'Connect Additional login', exact: true }).click();
  await extra.getByRole('button', { name: 'Simulate completed sign-in (synthetic)' }).click();
  await expect(meter(page, 'anthropic-sign-in-3')).toContainText('No samples yet');
  await expect(meter(page, 'anthropic-sign-in-3').getByRole('meter')).toHaveCount(0);
  await page.getByTestId('setup-save-bar').getByRole('button', { name: 'Discard', exact: true }).click();
  await expect(page.getByTestId('usage-meter')).toHaveCount(0);
  await page.goto('/#/settings/providers');
  await expect(page.getByTestId('usage-meter')).toHaveCount(3);
  await page.getByTestId('lineage-evaluator-codex-login').getByRole('button', { name: /^Disconnect / }).click();
  await expect(meter(page, 'evaluator-codex-login')).toHaveCount(0);
  await page.getByTestId('setup-save-bar').getByRole('button', { name: 'Discard', exact: true }).click();
  await expect(meter(page, 'evaluator-codex-login')).toHaveCount(1);
});

test('collapse and keyboard expand free space, retain rail tooltips and project highlighting', async ({ page }) => {
  await page.goto('/#/agents');
  const before = await page.locator('.page').boundingBox();
  await expect(collapse(page)).toHaveAttribute('aria-expanded', 'true');
  await expect(collapse(page)).toHaveAttribute('aria-controls', 'app-sidebar');
  await collapse(page).click();
  await expect(expand(page)).toHaveAttribute('aria-expanded', 'false');
  await expect.poll(() => width(page)).toBe(56);
  const after = await page.locator('.page').boundingBox();
  expect(after.width - before.width).toBe(264);
  expect(after.x).toBe(56);
  const labels = ['Odin', 'Executive · Running', 'Dashboard, 9 items need attention', 'Usage: ordinary stop',
    'Setup', 'Settings', 'Theme: Dark', 'Expand sidebar'];
  for (const label of labels) {
    const el = panel(page).getByLabel(label, { exact: true });
    await expect(el).toHaveAttribute('title', new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    await expect(el).toBeVisible();
  }
  for (const label of ['Dashboard, 9 items need attention', 'Usage: ordinary stop', 'Setup', 'Settings', 'Theme: Dark']) {
    const icon = panel(page).getByLabel(label, { exact: true }).locator('svg.shell-icon');
    await expect(icon).toHaveCount(1);
    await expect(icon).toHaveAttribute('aria-hidden', 'true');
    await expect(icon).toHaveAttribute('stroke-width', '1.7');
  }
  await expect(page.getByTestId('synthetic-badge').locator('svg.shell-icon')).toHaveCount(1);
  await expect(handle(page)).toHaveCount(0);
  const target = page.locator(`[data-testid="sidebar-project"][data-project-id="${PID}"]`);
  await expect(target).toHaveAttribute('title', /Odin web app/);
  await expect(target).toHaveAttribute('aria-label', /Odin web app/);
  await expect(target.locator('.status-dot')).toHaveCount(1);
  await target.hover();
  await expect(page.locator('[data-testid="project-node"][data-project-id="proj-contract-pins"]')).toHaveClass(/branch-muted/);
  await panel(page).getByLabel('Odin', { exact: true }).hover();
  await target.focus();
  await expect(page.locator('[data-testid="project-node"][data-project-id="proj-contract-pins"]')).toHaveClass(/branch-muted/);
  await expand(page).focus();
  await page.keyboard.press('Enter');
  await expect.poll(() => width(page)).toBe(320);
  await collapse(page).focus();
  await page.keyboard.press('Space');
  await expect.poll(() => width(page)).toBe(56);
  await expand(page).click();
  await expect.poll(() => width(page)).toBe(320);
});

test('keyboard resize clamps to 220–440 and container queries reveal details by panel width', async ({ page }) => {
  await page.goto('/#/agents');
  await expect(handle(page)).toHaveAttribute('aria-orientation', 'vertical');
  await expect(handle(page)).toHaveAttribute('aria-valuemin', '220');
  await expect(handle(page)).toHaveAttribute('aria-valuemax', '440');
  await resizeKey(page, 'ArrowLeft', 304);
  await resizeKey(page, 'Home', 220);
  await resizeKey(page, 'ArrowLeft', 220);
  const bar = panel(page).locator('.project-status-bar').first();
  await expect(bar).not.toBeVisible();
  const bottom = panel(page).locator('.sidebar-bottom-links');
  expect(await bottom.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
  for (const entry of await bottom.locator('a, button').all()) {
    expect(await entry.evaluate((el) => getComputedStyle(el).whiteSpace)).toBe('nowrap');
  }
  await expect(panel(page).locator('.executive-label > .sidebar-detail')).not.toBeVisible();
  await resizeKey(page, 'End', 440);
  await resizeKey(page, 'ArrowRight', 440);
  await expect(bar).toBeVisible();
  await expect(bar).toHaveAttribute('aria-label', /\d+ running, \d+ needs you, \d+ failed, \d+ done/);
  await expect(panel(page).locator('.executive-label > .sidebar-detail')).toContainText(/tok.*\d+m/);
  await resizeKey(page, 'ArrowLeft', 424);
  await shot(page, 'sidebar-dashboard-wide');
});

test('pointer resize tracks movement, clamps both ends and preserves width through collapse and reload', async ({ page }) => {
  await page.goto('/#/agents');
  const box = await handle(page).boundingBox();
  await page.mouse.move(box.x + box.width / 2, 200);
  await page.mouse.down();
  await page.mouse.move(800, 200);
  await expect(handle(page)).toHaveAttribute('aria-valuenow', '440');
  await page.mouse.move(40, 200);
  await expect(handle(page)).toHaveAttribute('aria-valuenow', '220');
  await page.mouse.move(box.x + box.width / 2 + 40, 200);
  await page.mouse.up();
  await expect.poll(() => width(page)).toBe(360);
  await collapse(page).click();
  await page.reload();
  await expect.poll(() => width(page)).toBe(56);
  await expand(page).click();
  await expect.poll(() => width(page)).toBe(360);
  await page.reload();
  await expect.poll(() => width(page)).toBe(360);
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('odin-web-prefs:v1')));
  expect(stored.sidebarWidth).toBe(360);
  expect(stored.sidebarCollapsed).toBe(false);
  const chrome = await page.locator('.chrome').boundingBox();
  const toolbar = await page.getByTestId('tree-header').boundingBox();
  expect(chrome.x).toBe(360);
  expect(toolbar.x).toBe(384);
});

test('invalid persisted widths and collapse values fall back without losing other preferences', async ({ page }) => {
  await page.goto('/#/agents');
  for (const sidebarWidth of [219, 441, 300.5, '400', null]) {
    await page.evaluate((sidebarWidth) => localStorage.setItem('odin-web-prefs:v1', JSON.stringify({
      sidebarWidth, sidebarCollapsed: 'true', theme: 'light', mode: 'list',
    })), sidebarWidth);
    await page.reload();
    await expect.poll(() => width(page)).toBe(320);
    await expect(collapse(page)).toBeVisible();
    await expect(page.getByTestId('list-view')).toBeVisible();
    await expect(page.getByTestId('theme-toggle')).toHaveAttribute('aria-pressed', 'true');
  }
});

test('collapse uses the shared 280ms easing and becomes instant with reduced motion', async ({ page }) => {
  await page.goto('/#/agents');
  const css = await panel(page).evaluate((el) => ({
    duration: getComputedStyle(el).transitionDuration, easing: getComputedStyle(el).transitionTimingFunction,
  }));
  expect(css).toEqual({ duration: '0.28s', easing: 'cubic-bezier(0.32, 0.72, 0.24, 1)' });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  expect(await panel(page).evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  expect(await panel(page).locator('.usage-fill').first().evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  await collapse(page).click();
  await expect.poll(() => width(page)).toBe(56);
  await expand(page).click();
  await expect.poll(() => width(page)).toBe(320);
});

test('800px drawer always expands independently of stored desktop collapse and width', async ({ page }) => {
  await page.goto('/#/agents');
  await resizeKey(page, 'End', 440);
  await collapse(page).click();
  await page.setViewportSize({ width: 800, height: 900 });
  const menu = page.getByRole('button', { name: 'Open menu' });
  await menu.focus();
  await page.keyboard.press('Enter');
  const drawer = page.getByRole('dialog', { name: 'Sidebar', exact: true });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByTestId('usage-meter')).toHaveCount(3);
  await expect(drawer.getByRole('button', { name: /Collapse sidebar|Expand sidebar/ })).toHaveCount(0);
  await expect(handle(page)).toHaveCount(0);
  await expect(drawer.getByTestId('sidebar-dashboard')).toBeVisible();
  expect(await width(page)).toBe(280);
  await page.keyboard.press('Escape');
  await expect(menu).toBeFocused();
  await menu.click();
  await drawer.getByRole('link', { name: 'Settings', exact: true }).click();
  await expect(drawer).not.toBeVisible();
  await page.setViewportSize({ width: 1000, height: 900 });
  await expect.poll(() => width(page)).toBe(56);
  await expand(page).click();
  await expect.poll(() => width(page)).toBe(440);
});

for (const theme of ['dark', 'light']) test(`usage colour rules in ${theme}: neutral bars and band text`, async ({ page }) => {
  await page.goto('/#/agents');
  if (theme === 'light') await page.getByTestId('theme-toggle').click();
  const colors = await panel(page).evaluate((el) => {
    const token = (name) => {
      const probe = document.createElement('span');
      probe.style.color = `var(${name})`; el.append(probe);
      const color = getComputedStyle(probe).color; probe.remove(); return color;
    };
    return { muted: token('--muted'), warn: token('--warn'), failed: token('--status-failed') };
  });
  const styles = await panel(page).locator('.usage-fill')
    .evaluateAll((els) => els.map((el) => getComputedStyle(el).backgroundColor));
  expect(styles.every((color) => color === colors.muted)).toBe(true);
  for (const [band, color] of [['clear', colors.muted], ['wind_down', colors.warn], ['ordinary_stop', colors.warn]]) {
    expect(await panel(page).locator(`[data-band="${band}"]`).first().evaluate((el) => getComputedStyle(el).color)).toBe(color);
  }
  // Exercise the final band style without altering fixture or admission computation.
  const handoffColor = await panel(page).evaluate((el) => {
    const probe = document.createElement('span'); probe.className = 'usage-band band-handoff_only';
    el.append(probe); const color = getComputedStyle(probe).color; probe.remove(); return color;
  });
  expect(handoffColor).toBe(colors.failed);
  await expect(panel(page)).not.toContainText(/\$|\/mo|price/i);
});


test('compact usage is pinned above setup at 1440×1000 and remains visible while the dashboard scrolls', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/agents');
  const usage = page.getByTestId('sidebar-usage');
  expect(await usage.evaluate((el) => el.closest('.sidebar-scroll'))).toBeNull();
  await expect(panel(page).getByTestId('sidebar-activity')).toHaveCount(0);
  const assertPinned = async () => {
    await expect(usage).toBeInViewport({ ratio: 1 });
    await expect(page.getByTestId('setup-progress-card')).toBeInViewport({ ratio: 1 });
    await expect(panel(page).getByRole('link', { name: 'Settings', exact: true })).toBeInViewport({ ratio: 1 });
    expect((await usage.boundingBox()).height).toBeLessThanOrEqual(155);
  };
  await assertPinned();
  const before = await usage.boundingBox();
  await panel(page).locator('.sidebar-scroll').evaluate((el) => { el.scrollTop = el.scrollHeight; });
  expect(await usage.boundingBox()).toEqual(before);
  await resizeKey(page, 'Home', 220);
  await assertPinned();
  const summaries = await usage.locator('.usage-summary-reading').evaluateAll((els) => els.map((el) => el.title));
  expect(summaries).toEqual(['Weekly 81 % wind down', '5-hour 12 % clear', '5-hour 91 % ordinary stop']);
  await shot(page, 'sidebar-compact-pinned');
});

test('per-sign-in disclosure keeps details bounded, preserves controls and resets only on reload', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/agents');
  const executive = meter(page, 'executive-login');
  const toggle = executive.getByRole('button', { name: 'Usage details for Executive login', exact: true });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(executive.getByTestId('usage-details')).toBeHidden();
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(executive.getByTestId('usage-window')).toHaveCount(3);
  await expect(meter(page, 'delegation-login').getByRole('button')).toHaveAttribute('aria-expanded', 'false');
  const mini = executive.getByRole('meter', { name: 'Executive login: Weekly', exact: true });
  await expect(mini).toHaveAccessibleDescription(/claude\.weekly/);
  await collapse(page).click();
  await expand(page).click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  for (const id of ['delegation-login', 'evaluator-codex-login']) {
    await meter(page, id).getByRole('button').click();
  }
  await expect(page.getByTestId('setup-progress-card')).toBeInViewport({ ratio: 1 });
  await expect(panel(page).getByRole('link', { name: 'Settings', exact: true })).toBeInViewport({ ratio: 1 });
  const usage = page.getByTestId('sidebar-usage');
  expect((await usage.boundingBox()).height).toBeLessThanOrEqual(440);
  expect(await usage.locator('.usage-list').evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
  await page.reload();
  for (const button of await page.getByTestId('usage-meter').getByRole('button').all()) {
    await expect(button).toHaveAttribute('aria-expanded', 'false');
  }
});

test('resize feedback is one neutral pixel idle and two accent pixels on hover, focus and drag', async ({ page }) => {
  await page.goto('/#/agents');
  const line = () => handle(page).evaluate((el) => {
    const pseudo = getComputedStyle(el, '::before');
    const resolve = (token) => {
      const probe = document.createElement('span'); probe.style.color = `var(${token})`; el.append(probe);
      const color = getComputedStyle(probe).color; probe.remove(); return color;
    };
    return { width: pseudo.width, color: pseudo.backgroundColor, outline: getComputedStyle(el).outlineStyle,
      neutral: resolve('--border'), accent: resolve('--accent') };
  });
  await page.mouse.move(900, 300);
  let css = await line();
  expect(css.width).toBe('1px'); expect(css.color).toBe(css.neutral);
  await handle(page).hover();
  css = await line(); expect(css.width).toBe('2px'); expect(css.color).toBe(css.accent);
  await page.mouse.move(900, 300);
  await handle(page).focus();
  css = await line(); expect(css.width).toBe('2px'); expect(css.color).toBe(css.accent);
  expect(css.outline).toBe('none');
  await handle(page).hover();
  await page.mouse.down();
  await page.mouse.move(400, 300);
  css = await line(); expect(css.width).toBe('2px'); expect(css.color).toBe(css.accent);
  await page.mouse.up();
});


test('a sign-in with only unavailable probes has an explicit compact summary and no meter', async ({ page }) => {
  // Supply an unavailable synthetic fixture before the setup store clones it.
  await page.addInitScript(() => {
    const clone = window.structuredClone;
    window.structuredClone = (value, options) => {
      const result = clone(value, options);
      const samples = result?.usage?.lineages?.['executive-login']?.samples;
      for (const s of samples || []) {
        s.status = 'unavailable'; s.utilization_percent = null; s.resets_at = null;
        s.reason = 'credential not readable';
      }
      return result;
    };
  });
  await page.goto('/#/agents');
  const executive = meter(page, 'executive-login');
  await expect(executive.locator('.usage-summary-empty')).toHaveText('Probe unavailable');
  await expect(executive.getByRole('meter')).toHaveCount(0);
  await expect(executive).not.toContainText('0 %');
  await executive.getByRole('button').click();
  await expect(executive.locator('.usage-unavailable')).toHaveCount(3);
  await expect(executive.getByRole('meter')).toHaveCount(0);
  await expect(executive).toContainText('credential not readable');
});
