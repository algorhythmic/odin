// Pass 4 brief items 3 and 7 (synthetic): the autoplay player applies
// the event fixture on a timer through the existing reducer; new
// sessions fade in with a drawn connector, running elapsed ticks each
// second, the header summary updates live, collapse reads "+N ›",
// everything is instant under prefers-reduced-motion, a retry draws a
// new sibling attempt with the failed one Stopped, and the attention
// chips open a keyboard-accessible popover with disabled commands.
// Timers are driven with page.clock, never real waits.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot } from './helpers.js';

const card = (page, id) => page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
const toggle = (page) => page.getByTestId('autoplay-toggle');
const speed = (page) => page.getByTestId('autoplay-speed');
const revision = (page) => page.getByTestId('revision');
const summary = (page) => page.getByTestId('agent-summary');
const applyNext = (page) => page.getByRole('button', { name: 'Apply next synthetic update' }).click();
const animationName = (loc) => loc.evaluate((el) => getComputedStyle(el).animationName);

test.beforeEach(async ({ page }) => {
  await page.clock.install();
});

test('play applies events on a timer, pause freezes them and speed rescales the interval', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(revision(page)).toHaveText('0');
  await toggle(page).click();
  await expect(toggle(page)).toHaveText('Pause');
  // 1x: one delivery every 1200 ms.
  await page.clock.runFor(1200);
  await expect(revision(page)).toHaveText('1');
  await page.clock.runFor(1200);
  await expect(revision(page)).toHaveText('2');
  // Paused, no deliveries happen.
  await toggle(page).click();
  await expect(toggle(page)).toHaveText('Play');
  await page.clock.runFor(10000);
  await expect(revision(page)).toHaveText('2');
  // 4x: one delivery every 300 ms (next is the evt-002 re-delivery, then evt-003).
  await speed(page).selectOption('4');
  await toggle(page).click();
  await page.clock.runFor(300);
  await expect(page.getByTestId('update-status')).toHaveText(/Ignored evt-002: already applied/);
  await page.clock.runFor(300);
  await expect(revision(page)).toHaveText('3');
  // 0.5x: one delivery every 2400 ms.
  await speed(page).selectOption('0.5');
  await page.clock.runFor(2400);
  await expect(revision(page)).toHaveText('4');
});

test('a delivered session fades in and its connector draws in', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(card(page, 'ses-docs-helper')).toHaveCount(0);
  await speed(page).selectOption('4');
  await toggle(page).click();
  await page.clock.runFor(600); // evt-001, evt-002
  await expect(card(page, 'ses-docs-helper')).toBeVisible();
  const edge = page.locator('path.ancestry-edge[data-from="ses-docs-01"][data-to="ses-docs-helper"]');
  await expect(edge).toHaveCount(1);
  // Both carry their entering animations.
  expect(await animationName(card(page, 'ses-docs-helper'))).toBe('card-in');
  expect(await animationName(edge)).toBe('edge-draw');
});

test('running sessions tick elapsed each second and the Running chip spins', async ({ page }) => {
  await page.goto('/#/');
  const elapsed = card(page, 'ses-exec-01').getByTestId('elapsed');
  await expect(elapsed).toHaveText('2h 34m 00s');
  // Nothing ticks while the player is stopped.
  await page.clock.runFor(5000);
  await expect(elapsed).toHaveText('2h 34m 00s');
  await toggle(page).click();
  await page.clock.runFor(3000);
  await expect(elapsed).toHaveText('2h 34m 03s');
  // A stopped card does not tick.
  await expect(card(page, 'ses-helper-01').getByTestId('elapsed')).toHaveText('10m');
  // The Running chip's spinner animates.
  const spin = card(page, 'ses-exec-01').getByTestId('status-icon-spinner');
  expect(await animationName(spin)).toBe('odin-spin');
});

test('a session that starts running mid-play ticks only since it appeared', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await speed(page).selectOption('4');
  await toggle(page).click();
  // evt-014 delivers ses-live-a2 (recorded elapsed_s 10) on the 26th
  // delivery, 7800 ms in — seven ticks after play began.
  await page.clock.runFor(7900);
  const elapsed = card(page, 'ses-live-a2').getByTestId('elapsed');
  await expect(elapsed).toHaveText('10s');
  await page.clock.runFor(150); // one more tick, still before evt-017 ends it
  await expect(elapsed).toHaveText('11s');
});

test('the header summary counts update live with the run', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(summary(page)).toContainText('9 agents · 2 running');
  await applyNext(page); // evt-001: reviewer running again
  await expect(summary(page)).toContainText('9 agents · 3 running');
  await applyNext(page); // evt-002: docs helper appears
  await expect(summary(page)).toContainText('10 agents · 4 running');
  // Token totals update live too (a2 gains 19.8k measured on evt-003,
  // which also drops the est. marker from the project total; evt-002's
  // docs helper already added its measured 850 tok).
  await expect(page.getByTestId('project-tokens')).toContainText('est. 89.4k tok');
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003: worker a2 usage measured
  await page.clock.runFor(1000); // let the count animation reach its target
  await expect(page.getByTestId('project-tokens')).toContainText('91.3k tok + 3 unknown');
  // And the attention chips track the same counts.
  await expect(page.getByTestId('chip-needs')).toHaveText('0 needs you ˅');
  await expect(page.getByTestId('chip-failed')).toHaveText('1 failed ˅');
});

test('token counts animate up to a new value', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const own = card(page, 'ses-worker-a2').getByTestId('own-tokens');
  await expect(own).toHaveText('est. 18.7k tok');
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003: usage updated to 19.8k measured
  // Mid-animation the card shows a value between old and new, never 0 or unknown.
  await page.clock.runFor(140);
  const mid = await own.textContent();
  expect(mid).not.toBe('est. 18.7k tok');
  expect(mid).not.toBe('19.8k tok');
  expect(mid).toMatch(/^[\d.]+k tok$/);
  await page.clock.runFor(1000);
  await expect(own).toHaveText('19.8k tok');
  // An unknown session shows the word, never a figure or a 0.
  await expect(card(page, 'ses-helper-01').getByTestId('own-tokens')).toHaveText('unknown');
});

test('autoplay preserves the selection and a manually panned canvas', async ({ page }) => {
  await page.goto(sessionUrl('ses-worker-a2'));
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  const view = page.getByTestId('tree-view');
  await view.focus();
  await page.keyboard.press('ArrowDown');
  const transform = await page.locator('.tree-stage').evaluate((el) => el.style.transform);
  await speed(page).selectOption('4');
  await toggle(page).click();
  await page.clock.runFor(6000); // through the malformed batch and the first live sessions
  expect(await page.locator('.tree-stage').evaluate((el) => el.style.transform)).toBe(transform);
  await expect(view).toHaveAttribute('data-manual', 'true');
  await expect(page).toHaveURL(/sessions\/ses-worker-a2$/);
  await expect(page.locator('[data-testid="session-card"].selected')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await toggle(page).click(); // leave the player paused
});

test('collapse reads "+N ›" for the hidden descendants and expand restores them', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  const integ = card(page, 'ses-integ-01');
  // Four sessions are recorded under the integration owner.
  await expect(integ.getByRole('button', { name: 'Collapse 4 sessions under integration owner' })).toHaveText('▾ 4');
  // Collapse/expand animates through the cards' position transition.
  const transition = await integ.evaluate((el) => getComputedStyle(el).transitionProperty);
  expect(transition).toContain('left');
  await integ.getByRole('button', { name: 'Collapse 4 sessions under integration owner' }).click();
  const expand = integ.getByRole('button', { name: 'Expand 4 sessions under integration owner' });
  await expect(expand).toHaveText('+4 ›');
  await expect(expand).toHaveAttribute('aria-expanded', 'false');
  await expect(card(page, 'ses-worker-a2')).toHaveCount(0);
  await expect(card(page, 'ses-helper-01')).toHaveCount(0);
  await expand.click();
  await expect(card(page, 'ses-helper-01')).toBeVisible();
  await expect(integ.getByRole('button', { name: 'Collapse 4 sessions under integration owner' })).toHaveText('▾ 4');
});

test('a failed session is retried as a new sibling and the old attempt shows Stopped', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await speed(page).selectOption('4');
  await toggle(page).click();
  await page.clock.runFor(7300); // through evt-012: attempt 1 ended, run failed
  const a1 = card(page, 'ses-live-a1');
  await expect(a1.getByTestId('state-label')).toHaveText('Failed');
  await page.clock.runFor(600); // evt-013 stops it, evt-014 starts the retry
  await expect(a1.getByTestId('state-label')).toHaveText('Stopped');
  await expect(a1).toHaveAttribute('data-dimmed', 'true');
  // The retry is a sibling in the same stacked column, linked as attempt 2.
  const a2 = card(page, 'ses-live-a2');
  await expect(a2).toHaveAttribute('data-parent', 'ses-integ-01');
  await expect(a2.getByTestId('lineage-label')).toHaveText('Attempt 2 (after ses-live-a1)');
  await expect(a2.getByTestId('state-label')).toHaveText('Running');
  const [b1, b2] = await Promise.all([a1.boundingBox(), a2.boundingBox()]);
  expect(Math.abs(b1.x - b2.x), 'the retry stacks in its sibling column').toBeLessThanOrEqual(3);
  // The run keeps playing to the end: attempt 2 finishes Done.
  await page.clock.runFor(1000);
  await expect(a2.getByTestId('state-label')).toHaveText('Done');
  await shot(page, 'live-run-finished');
});

test.describe('attention chips', () => {
  test('the popovers list sessions, tasks and reasons; commands are disabled', async ({ page }) => {
    await page.goto(`/#/projects/${PID}`);
    const chipNeeds = page.getByTestId('chip-needs');
    const chipFailed = page.getByTestId('chip-failed');
    await expect(chipNeeds).toHaveText('1 needs you ˅');
    await expect(chipFailed).toHaveText('1 failed ˅');

    await chipFailed.click();
    await expect(chipFailed).toHaveAttribute('aria-expanded', 'true');
    const pop = page.getByTestId('attention-popover');
    await expect(pop).toBeFocused();
    const failedItem = pop.locator('[data-session-id="ses-worker-a1"]');
    await expect(failedItem).toContainText('worker');
    await expect(failedItem).toContainText('Build the tree prototype');
    await expect(failedItem).toContainText('Attempt 1 checks failed');
    await expect(failedItem.getByRole('button', { name: 'Retry' })).toBeDisabled();
    await expect(failedItem.getByRole('button', { name: 'Dismiss' })).toBeDisabled();
    await expect(pop.getByTestId('attention-note')).toHaveText('Commands are not connected in this prototype.');
    // Escape closes and focus returns to the chip.
    await page.keyboard.press('Escape');
    await expect(pop).toHaveCount(0);
    await expect(chipFailed).toBeFocused();
    await expect(chipFailed).toHaveAttribute('aria-expanded', 'false');

    await chipNeeds.click();
    const pop2 = page.getByTestId('attention-popover');
    const needsItem = pop2.locator('[data-session-id="ses-review-exec"]');
    await expect(needsItem).toContainText('reviewer');
    await expect(needsItem).toContainText('Independent review of the tree prototype');
    await expect(needsItem).toContainText('Waiting for operator input');
    await expect(needsItem.getByRole('button', { name: 'Send input' })).toBeDisabled();
    await expect(needsItem.getByRole('button', { name: 'Dismiss' })).toBeDisabled();
    await expect(pop2.getByTestId('attention-note')).toHaveText('Commands are not connected in this prototype.');
    await shot(page, 'attention-popover');
  });

  test('chip counts update live with the run', async ({ page }) => {
    await page.goto(`/#/projects/${PID}`);
    await speed(page).selectOption('4');
    await toggle(page).click();
    await page.clock.runFor(5700); // through evt-008: ops worker needs the operator
    await expect(page.getByTestId('chip-needs')).toHaveText('1 needs you ˅');
    await page.clock.runFor(1500); // through evt-012: attempt 1 failed
    await expect(page.getByTestId('chip-failed')).toHaveText('2 failed ˅');
    await expect(page.getByTestId('chip-needs')).toHaveText('0 needs you ˅');
    await page.clock.runFor(3000); // to the end: retry done, scout needs you
    await expect(page.getByTestId('chip-failed')).toHaveText('1 failed ˅');
    await expect(page.getByTestId('chip-needs')).toHaveText('1 needs you ˅');
    // The queue is drained: the player stopped itself and Play is disabled.
    await expect(toggle(page)).toHaveText('Play');
    await expect(toggle(page)).toBeDisabled();
  });
});

test.describe('reduced motion', () => {
  test.use({ reducedMotion: 'reduce' });

  test('new sessions, connectors and the spinner are instant under prefers-reduced-motion', async ({ page }) => {
    await page.goto('/#/');
    await speed(page).selectOption('4');
    await toggle(page).click();
    await page.clock.runFor(600); // evt-001, evt-002
    const helper = card(page, 'ses-docs-helper');
    await expect(helper).toBeVisible();
    expect(await animationName(helper)).toBe('none');
    const edge = page.locator('path.ancestry-edge[data-to="ses-docs-helper"]');
    expect(await animationName(edge)).toBe('none');
    // The connector is fully drawn, not offset.
    expect(await edge.evaluate((el) => getComputedStyle(el).strokeDashoffset)).toBe('0px');
    // No spinner animation and no card position transition.
    const spin = card(page, 'ses-exec-01').getByTestId('status-icon-spinner');
    expect(await animationName(spin)).toBe('none');
    expect(await card(page, 'ses-exec-01').evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
    // Token figures jump to the new value instead of counting.
    await applyNext(page); // duplicate
    await applyNext(page); // evt-003
    await expect(card(page, 'ses-worker-a2').getByTestId('own-tokens')).toHaveText('19.8k tok');
  });
});
