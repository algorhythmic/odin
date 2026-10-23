// R2 coverage is synthetic prototype evidence only.
import { test, expect } from '@playwright/test';
import { PID, shot } from './helpers.js';
const current = (page) => page.locator('.setup-panel-current');
const row = (page, id) => current(page).getByTestId(`role-${id}`);
const steps = ['providers', 'harnesses', 'models', 'roles', 'review'];
const titles = [
  'Connect your subscriptions', 'Choose your harnesses', 'Choose your default models',
  'Configure Odin’s roles', 'Review your setup',
];
async function settledShot(page, name) {
  await current(page).evaluate(async (el) => { await Promise.allSettled(el.getAnimations({ subtree: true }).map((a) => a.finished)); });
  await shot(page, name);
}
async function next(page) {
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
}
async function simulate(page, id) {
  const lineage = current(page).getByTestId(`lineage-${id}`);
  await lineage.getByRole('button', { name: /^Connect / }).click();
  await expect(lineage).toContainText('Waiting for sign-in');
  await expect(lineage).toContainText('https://example.invalid/device');
  await expect(lineage).toContainText("Odin's service runs the sign-in; your browser never sees the credential.");
  await lineage.getByRole('button', { name: 'Simulate completed sign-in (synthetic)', exact: true }).click();
  await expect(lineage.locator('.setup-pill')).toHaveText('Connected');
}

test('fresh walkthrough connects sign-ins, picks defaults, customizes roles and applies', async ({ page }) => {
  await page.goto('/?setup=fresh#/setup');
  await expect(page).toHaveURL(/setup\/providers$/);
  await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeDisabled();
  for (const id of ['executive-login', 'delegation-login', 'evaluator-codex-login']) await simulate(page, id);
  await next(page);
  await expect(page).toHaveURL(/setup\/harnesses$/);
  await page.getByRole('checkbox', { name: 'Enable Claude Code', exact: true }).check();
  await page.getByRole('checkbox', { name: 'Enable Codex CLI', exact: true }).check();
  await expect(page.getByRole('checkbox', { name: 'Enable Pi RPC', exact: true })).toBeDisabled();
  await next(page);
  await expect(page).toHaveURL(/setup\/models$/);
  await page.getByRole('radio', { name: /^Sonnet 5.5/ }).check();
  await page.getByRole('group', { name: 'Claude Code effort', exact: true }).getByRole('button', { name: 'medium', exact: true }).click();
  await page.getByRole('radio', { name: /^GPT-6 Mini/ }).check();
  await expect(current(page)).toContainText('synthetic descriptors, not measurements');
  await next(page);
  await expect(page).toHaveURL(/setup\/roles$/);
  await page.getByRole('button', { name: 'Cross-family', exact: true }).click();
  await expect(row(page, 'executive').getByRole('combobox', { name: 'Executive model', exact: true })).toHaveValue('claude-opus-5-5');
  await row(page, 'implementer').getByRole('combobox', { name: 'Implementer effort', exact: true }).selectOption('medium');
  await expect(current(page)).toContainText('Preset: Custom');
  await expect(row(page, 'independent_review')).toContainText('Same model family as the author; review is less independent');
  await row(page, 'executive').getByRole('combobox', { name: 'Executive harness', exact: true }).selectOption('codex');
  await expect(row(page, 'executive')).toContainText('The executive must use Claude Code');
  // Direct links still validate the whole draft before applying it.
  await page.evaluate(() => { location.hash = '#/setup/review'; });
  const apply = page.getByRole('button', { name: 'Apply', exact: true });
  await expect(apply).toBeDisabled();
  await expect(apply).toHaveAccessibleDescription(/The executive must use Claude Code/);
  await page.getByRole('link', { name: '‹ Back', exact: true }).click();
  await row(page, 'executive').getByRole('combobox', { name: 'Executive harness', exact: true }).selectOption('claude-code');
  await next(page);
  await expect(current(page).locator('.setup-changed')).not.toHaveCount(0);
  await expect(current(page)).toContainText('Subscriptions and sign-ins');
  await expect(apply).toBeEnabled();
  await settledShot(page, 'setup-review-dark');
  await apply.click();
  await expect(page.getByRole('status').filter({ hasText: 'Applied (synthetic, not saved)' })).toBeVisible();
  await expect(page.getByTestId('setup-progress-card')).toHaveCount(0);
  await page.getByTestId('sidebar-executive').click();
  await expect(page.getByTestId('setup-progress-card')).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId('setup-progress-card')).toContainText('Setup 0 of 4');
});

for (const [i, step] of steps.entries()) test(`setup deep link: ${step}`, async ({ page }) => {
  await page.goto(`/#/setup/${step}`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(titles[i]);
  await expect(page.getByRole('heading', { name: titles[i], exact: true })).toHaveCount(1);
  const card = page.locator('.setup-step-card');
  await expect(card).toHaveAttribute('role', 'region');
  await expect(card).toHaveAccessibleName(titles[i]);
  await expect(page.getByRole('navigation', { name: 'Setup steps' })).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Setup checklist' })).toContainText('Setup 3 of 4');
  await settledShot(page, `setup-${step}-dark`);
});

test('default setup opens roles from the shared sidebar progress card', async ({ page }) => {
  await page.goto('/#/agents');
  await expect(page.getByTestId('setup-progress-card')).toContainText('Setup 3 of 4');
  await page.getByTestId('setup-progress-card').click();
  await expect(page).toHaveURL(/setup\/roles$/);
  await expect(page.getByTestId('update-driver')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Opus-led/ })).toContainText('Illustrative');
  await expect(page.getByRole('button', { name: /Sol-heavy/ })).toContainText('Illustrative');
});

test('shared sign-ins are summarized once above the role table on every role page', async ({ page }) => {
  const messages = [
    '2 roles share Delegation login; limit 1 concurrent turn. Roles interleave.',
    '7 roles share Evaluator Codex login; limit 1 concurrent turn. Roles interleave.',
  ];
  for (const route of ['setup/roles', 'settings/roles', 'setup/review']) {
    await page.goto(`/#/${route}`);
    const summary = current(page).getByRole('region', { name: 'Lineage sharing', exact: true });
    const table = current(page).getByRole('table');
    await expect(summary).toBeVisible();
    for (const message of messages) {
      await expect(summary.getByText(message, { exact: true })).toHaveCount(1);
      await expect(current(page).getByText(message, { exact: true })).toHaveCount(1);
      await expect(table.getByText(message, { exact: true })).toHaveCount(0);
    }
    const summaryBounds = await summary.boundingBox();
    const tableBounds = await table.boundingBox();
    expect(summaryBounds.y + summaryBounds.height).toBeLessThanOrEqual(tableBounds.y);
    await expect(row(page, 'independent_review')).toContainText(
      'Same model family as the author; review is less independent',
    );
  }
});

test('snapshot updates stay on portfolio and project trees when navigating through setup and settings', async ({ page }) => {
  await page.goto('/#/agents');
  const driver = page.getByTestId('update-driver');
  await expect(driver).toBeVisible();
  await driver.getByRole('button', { name: 'Apply next synthetic update', exact: true }).click();
  await expect(page.getByTestId('revision')).toHaveText('1');
  for (const route of ['setup/roles', 'settings/roles']) {
    await page.evaluate((hash) => { location.hash = hash; }, `#/${route}`);
    await expect(page).toHaveURL(new RegExp(`${route}$`));
    await expect(driver).toHaveCount(0);
  }
  for (const route of ['agents', `projects/${PID}`]) {
    await page.evaluate((hash) => { location.hash = hash; }, `#/${route}`);
    await expect(page).toHaveURL(new RegExp(`#/${route}$`));
    await expect(driver).toBeVisible();
    await expect(page.getByTestId('revision')).toHaveText('1');
    await expect(driver.getByRole('button', { name: 'Apply next synthetic update', exact: true })).toBeEnabled();
  }
});

test('settings save bar discards and applies the shared draft and keeps it only in memory', async ({ page }) => {
  await page.goto('/#/settings/roles');
  const save = page.getByTestId('setup-save-bar');
  await expect(save).toHaveCount(0);
  const effort = () => row(page, 'implementer').getByRole('combobox', { name: 'Implementer effort', exact: true });
  await effort().selectOption('medium');
  await expect(save).toBeVisible();
  await settledShot(page, 'settings-roles-save-dark');
  await save.getByRole('button', { name: 'Discard', exact: true }).click();
  await expect(effort()).toHaveValue('high');
  await expect(save).toHaveCount(0);
  await page.getByRole('button', { name: /Opus-led/ }).click();
  const searchModel = row(page, 'subagent_search').getByRole('combobox', { name: 'Subagent · Search model', exact: true });
  await expect(searchModel).toHaveValue('claude-sonnet-5-5');
  await save.getByRole('button', { name: 'Apply', exact: true }).click();
  await expect(save).toHaveCount(0);
  await expect(page.locator('.setup-applied')).toHaveText('Applied (synthetic, not saved)');
  await row(page, 'executive').getByRole('combobox', { name: 'Executive harness', exact: true }).selectOption('codex');
  await expect(save.getByRole('button', { name: 'Apply', exact: true })).toBeDisabled();
  await expect(page.getByTestId('setup-progress-card')).toHaveCount(0);
  await save.getByRole('button', { name: 'Discard', exact: true }).click();
  await page.getByRole('navigation', { name: 'Settings sections' }).getByRole('link', { name: 'Models', exact: true }).click();
  await page.getByRole('radio', { name: /^GPT-6 Mini/ }).check();
  await expect(save).toBeVisible();
  await save.getByRole('button', { name: 'Apply', exact: true }).click();
  await page.reload();
  await expect(page.getByRole('radio', { name: /^GPT-6.1 Sol/ })).toBeChecked();
  await expect(page.getByTestId('setup-progress-card')).toContainText('Setup 3 of 4');
});

test('provider and harness settings share the save bar; sign-ins have editable labels', async ({ page }) => {
  await page.goto('/#/settings/providers');
  const anthropic = current(page).getByRole('region', { name: 'Anthropic', exact: true });
  await anthropic.getByRole('button', { name: /Add another sign-in/ }).click();
  await anthropic.getByRole('textbox').last().fill('Extra synthetic login');
  await expect(page.getByTestId('setup-save-bar')).toBeVisible();
  await simulate(page, 'anthropic-sign-in-3');
  await page.getByTestId('setup-save-bar').getByRole('button', { name: 'Apply', exact: true }).click();
  await page.getByRole('navigation', { name: 'Settings sections' }).getByRole('link', { name: 'Harnesses', exact: true }).click();
  await page.getByRole('combobox', { name: 'Claude Code default sign-in', exact: true }).selectOption('anthropic-sign-in-3');
  await expect(page.getByTestId('setup-save-bar')).toBeVisible();
  await page.getByTestId('setup-save-bar').getByRole('button', { name: 'Discard', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Claude Code default sign-in', exact: true })).toHaveValue('executive-login');
});

test('no setup or settings panel accepts credentials or makes an external request', async ({ page }) => {
  const external = [];
  page.on('request', (request) => {
    if (!new URL(request.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/)) external.push(request.url());
  });
  for (const prefix of ['setup', 'settings']) for (const step of steps.filter((s) => prefix !== 'settings' || s !== 'review')) {
    await page.goto(`/#/${prefix}/${step}`);
    await expect(page.getByTestId('setup-placeholder')).toBeVisible();
    await expect(page.getByTestId('update-driver')).toHaveCount(0);
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    const identifiers = await page.locator('input, select, textarea').evaluateAll((elements) => elements.map((el) => [
      el.name, el.id, el.getAttribute('aria-label'), ...Array.from(el.labels || []).map((l) => l.textContent),
    ].join(' ')));
    for (const label of identifiers) expect(label).not.toMatch(/token|key|secret/i);
  }
  expect(external).toEqual([]);
});

test('a provider step completes using only keyboard activation', async ({ page }) => {
  await page.goto('/?setup=fresh#/setup/providers');
  // Reach Connect through the document's real tab order.
  let reached = false;
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate(() => document.activeElement.textContent.trim() === 'Connect Executive login')) { reached = true; break; }
  }
  expect(reached).toBe(true);
  await page.keyboard.press('Enter');
  // The removed Connect button returns focus to the document; tab to the simulation.
  let simulation = false;
  for (let i = 0; i < 70; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate(() => document.activeElement.textContent === 'Simulate completed sign-in (synthetic)')) {
      simulation = true;
      break;
    }
  }
  expect(simulation).toBe(true);
  await page.keyboard.press('Enter');
  let continuation = false;
  for (let i = 0; i < 70; i++) {
    await page.keyboard.press('Tab');
    if (await page.evaluate(() => (
      document.activeElement.tagName === 'BUTTON' && document.activeElement.textContent.startsWith('Continue')
    ))) {
      continuation = true;
      break;
    }
  }
  expect(continuation).toBe(true);
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/setup\/harnesses$/);
  const heading = page.getByRole('heading', { level: 1 });
  await expect(heading).toBeFocused();
  expect(await heading.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe('none');
  // Heading focus is quiet, while controls reached by Tab keep their visible ring.
  const enable = page.getByRole('checkbox', { name: 'Enable Claude Code', exact: true });
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab');
    if (await enable.evaluate((el) => el === document.activeElement)) break;
  }
  await expect(enable).toBeFocused();
  expect(await enable.evaluate((el) => el.matches(':focus-visible'))).toBe(true);
  expect(await enable.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe('solid');
  expect(await enable.evaluate((el) => parseFloat(getComputedStyle(el).outlineWidth))).toBeGreaterThan(0);
});

test('reduced motion disables entrances, exits, check drawing and effort unfolding', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/setup/models');
  expect(await current(page).evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
  await page.getByRole('radio', { name: /^Sonnet 5.5/ }).check();
  const fold = current(page).locator('.setup-effort-fold.open').first();
  expect(await fold.evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  await next(page);
  await expect(page.locator('.setup-panel-leaving')).toHaveCount(0);
  expect(await page.locator('.setup-stepper .setup-check path').first().evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
});

test('800px layout stacks the checklist, keeps tables contained and supports the drawer', async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 1000 });
  await page.goto('/#/setup/roles');
  const main = await page.locator('.setup-main').boundingBox();
  const checklist = await page.getByRole('complementary', { name: 'Setup checklist' }).boundingBox();
  expect(checklist.y).toBeGreaterThanOrEqual(main.y + main.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(800);
  await settledShot(page, 'setup-roles-800');
  await page.getByRole('button', { name: 'Open menu', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Sidebar', exact: true }).getByTestId('setup-progress-card')).toContainText('Setup 3 of 4');
  await page.keyboard.press('Escape');
  await page.getByRole('navigation', { name: 'Setup steps' }).getByRole('link', { name: 'Models', exact: true }).click();
  await expect(page).toHaveURL(/setup\/models$/);
  await page.getByRole('radio', { name: /^Sonnet 5.5/ }).check();
  await expect(page.getByRole('radio', { name: /^Sonnet 5.5/ })).toBeChecked();
});
