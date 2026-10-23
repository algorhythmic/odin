// R4a coverage is synthetic prototype evidence, never service or desktop acceptance.
import { test, expect } from '@playwright/test';
import { snapshot, PID, shot } from './helpers.js';
import { generateLargeSnapshot } from '../src/fixtures/large.js';

const queue = (page) => page.getByTestId('priority-queue');
const rows = (page) => queue(page).getByTestId('priority-item');
const filter = (page, label) => queue(page).getByRole('button', { name: new RegExp(`^${label} \\d+$`) });
const rowKind = (page, type) => queue(page).locator(`[data-testid="priority-item"][data-kind="${type}"]`);
function expectedTokens(sessions) {
  const known = sessions.filter((s) => s.tokens.basis !== 'unknown');
  if (!known.length) return `unknown (${sessions.length})`;
  const n = known.reduce((a, s) => a + s.tokens.uncached_input + s.tokens.cache_write + s.tokens.output, 0);
  const text = n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;
  return `${known.some((s) => s.tokens.basis === 'estimate') ? 'est. ' : ''}${text} tok`
    + (sessions.length > known.length ? ` + ${sessions.length - known.length} unknown` : '');
}

// Change only synthetic inputs, before the application clones them.
async function quietPortfolio(page, { unknown = false } = {}) {
  await page.addInitScript(({ unknown }) => {
    const clone = window.structuredClone;
    window.structuredClone = (value, options) => {
      const result = clone(value, options);
      if (result?.schema === 'odin.web.projection.snapshot/v0-draft') {
        for (const s of result.sessions) {
          s.needs_operator_input = false; s.stale = false;
          if (['waiting_for_input', 'host_offline'].includes(s.lifecycle)) s.lifecycle = 'idle';
          if (unknown) s.tokens = { uncached_input: null, cache_read: null, cache_write: null, output: null, basis: 'unknown' };
        }
        result.runs = result.runs.map((r) => ({ ...r, outcome: 'unverified' }));
        result.decisions = [];
      }
      if (result?.schema === 'odin-web-setup-draft-1') {
        for (const s of Object.keys(result.state.completed)) result.state.completed[s] = true;
        for (const l of Object.values(result.usage.lineages)) {
          for (const s of l.samples) if (s.status === 'available') s.utilization_percent = 0;
        }
      }
      if (result && result.providers === true && result.harnesses === true && result.models === true
        && result.roles === false) result.roles = true;
      return result;
    };
  }, { unknown });
}

test('home, sidebar badge, Agents entry, session close, breadcrumb and History links', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('dashboard')).toBeVisible();
  const nav = page.getByTestId('sidebar-dashboard');
  await expect(nav).toHaveAttribute('href', '#/');
  await expect(nav).toHaveAttribute('aria-current', 'page');
  await expect(nav).toHaveAccessibleName(/Dashboard, \d+ items need attention/);
  const badge = Number(await nav.locator('.dashboard-badge').textContent());
  await expect(queue(page).locator('.dashboard-section-head')).toContainText(`${badge} open`);
  await expect(page.getByTestId('sidebar-attention')).toHaveCount(0);
  await expect(page.getByTestId('sidebar-activity')).toHaveCount(0);
  await expect(page.getByTestId('update-driver')).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByTestId('sidebar-executive').click();
  await expect(page).toHaveURL(/#\/agents$/);
  await expect(page.getByTestId('workspace')).toBeVisible();
  await page.goto('/#/sessions/ses-exec-01');
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-exec-01');
  await page.getByRole('complementary', { name: 'Session details' }).getByRole('button', { name: 'Close' }).click();
  await expect(page).toHaveURL(/#\/agents$/);
  await page.goto(`/#/projects/${PID}`);
  await page.getByTestId('tree-header').getByRole('link', { name: 'Portfolio', exact: true }).click();
  await expect(page).toHaveURL(/#\/agents$/);
  await page.goto('/#/history');
  await page.getByRole('link', { name: 'All projects', exact: true }).click();
  await expect(page).toHaveURL(/#\/agents$/);
  await page.goto('/#/agents/no-such-view');
  await expect(page.getByTestId('not-found')).toBeVisible();
});

test('one urgency queue contains every recorded type and filters retain exact counts', async ({ page }) => {
  await page.goto('/#/');
  if (await queue(page).getByRole('button', { name: /^\+\d+ more$/ }).count()) {
    await queue(page).getByRole('button', { name: /^\+\d+ more$/ }).click();
  }
  const types = await rows(page).evaluateAll((els) => els.map((el) => el.dataset.kind));
  expect([...new Set(types)]).toEqual(['setup', 'needs', 'failed', 'decision', 'usage', 'host']);
  const needs = snapshot.sessions.filter((s) => s.needs_operator_input || s.lifecycle === 'waiting_for_input');
  const failed = snapshot.runs.filter((r) => r.outcome === 'failed');
  for (const [label, type, count] of [['Needs you', 'needs', needs.length], ['Failed', 'failed', failed.length],
    ['Setup', 'setup', 1]]) {
    await expect(filter(page, label)).toHaveText(`${label} ${count}`);
    await filter(page, label).click();
    await expect(rows(page)).toHaveCount(count);
    expect(await rows(page).evaluateAll((els, kind) => els.every((el) => el.dataset.kind === kind), type)).toBe(true);
  }
  await filter(page, 'Needs you').click();
  for (const s of needs) {
    const row = queue(page).locator(`[data-attention-session="${s.id}"]`);
    await expect(row).toContainText(s.role);
    await expect(row).toContainText(snapshot.projects.find((p) => p.id === s.project_id).name);
    const task = snapshot.assignments.find((a) => a.id === s.assignment_id);
    await expect(row.locator('.priority-disclosure strong')).toHaveText(task.summary);
    expect(await row.locator('.priority-disclosure strong').evaluate((el) => getComputedStyle(el).textOverflow))
      .toBe('ellipsis');
    await expect(row.getByRole('link', { name: 'Open', exact: true })).toHaveAttribute('href', `#/sessions/${s.id}`);
  }
  await rows(page).first().getByRole('link', { name: 'Open', exact: true }).click();
  await expect(page.getByTestId('detail-panel')).toBeVisible();
});

test('decisions retain proposal identity and disabled commands; usage and hosts open their source', async ({ page }) => {
  await page.goto('/#/');
  await queue(page).getByRole('button', { name: /^\+\d+ more$/ }).click();
  for (const d of snapshot.decisions) {
    const row = rowKind(page, 'decision').filter({ hasText: d.title });
    await expect(row).toContainText(d.requested_by);
    await expect(row).toContainText(`Proposal revision ${d.proposal.revision}`);
    await expect(row).toContainText(d.proposal.digest);
    for (const label of ['Approve', 'Deny']) {
      await expect(row.getByRole('button', { name: label, exact: true })).toBeDisabled();
      await expect(row.getByRole('button', { name: label, exact: true })).toHaveAccessibleDescription('Commands are not connected');
    }
  }
  await expect(rowKind(page, 'usage')).toHaveCount(2);
  await expect(rowKind(page, 'usage').filter({ hasText: 'Executive login' })).toContainText('wind down');
  await expect(rowKind(page, 'usage').filter({ hasText: 'Evaluator Codex login' })).toContainText('ordinary stop');
  await expect(rowKind(page, 'usage').first().getByRole('link')).toHaveAttribute('href', '#/settings/providers');
  await expect(rowKind(page, 'host').first().getByRole('link')).toHaveAttribute('href', '#/sessions/ses-ops-01');
  const row = queue(page).locator('[data-kind="needs"][data-attention-session="ses-pin-worker"]');
  await row.getByRole('button').click();
  await expect(row.getByRole('button')).toHaveAttribute('aria-expanded', 'true');
  await expect(row.locator('.priority-fold')).toContainText('worker requested decision');
  await row.getByRole('button').click();
  await expect(row.getByRole('button')).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByTestId('dashboard')).not.toContainText(/\$|price/i);
});

test('large input and failure filters unfold all matches and fold again without changing route', async ({ page }) => {
  const large = generateLargeSnapshot();
  await page.goto('/?dataset=large#/');
  for (const [label, count] of [
    ['Needs you', large.sessions.filter((s) => s.lifecycle === 'waiting_for_input' || s.needs_operator_input).length],
    ['Failed', large.runs.filter((r) => r.outcome === 'failed').length],
  ]) {
    await filter(page, label).click();
    await expect(rows(page)).toHaveCount(Math.min(8, count));
    if (count > 8) {
      await queue(page).getByRole('button', { name: `+${count - 8} more`, exact: true }).click();
      await expect(rows(page)).toHaveCount(count);
      await expect(page).toHaveURL(/#\/$/);
      await queue(page).getByRole('button', { name: 'Show less', exact: true }).click();
      await expect(rows(page)).toHaveCount(8);
    }
  }
});

test('KPIs cover snapshot outcomes and tokens once including retired records and unknowns', async ({ page }) => {
  for (const [url, data] of [['/#/', snapshot], ['/?dataset=large#/', generateLargeSnapshot()]]) {
    await page.goto(url);
    await expect(page.getByTestId('kpi-running')).toHaveText(
      `Running${data.sessions.filter((s) => s.lifecycle === 'running').length}`);
    await expect(page.getByTestId('kpi-ended')).toHaveText(`Ended in snapshot${data.sessions
      .filter((s) => ['ended', 'retired'].includes(s.lifecycle)).length}`);
    await expect(page.getByTestId('kpi-needs')).toHaveText(`Needs you${data.sessions
      .filter((s) => s.needs_operator_input || s.lifecycle === 'waiting_for_input').length}`);
    const failed = new Set(data.runs.filter((r) => r.outcome === 'failed').map((r) => r.session_id));
    await expect(page.getByTestId('kpi-failed')).toHaveText(`Failed${failed.size}`);
    await expect(page.getByTestId('kpi-tokens')).toHaveText(expectedTokens(data.sessions));
  }
});

test('empty queue says nothing needs you and wholly unknown usage never reads zero', async ({ page }) => {
  await quietPortfolio(page, { unknown: true });
  await page.goto('/#/');
  await expect(queue(page)).toContainText('Nothing needs you');
  await expect(rows(page)).toHaveCount(0);
  await expect(page.getByTestId('kpi-tokens')).toHaveText(`unknown (${snapshot.sessions.length})`);
  await expect(page.getByTestId('kpi-tokens')).not.toContainText('0 tok');
  await expect(page.getByTestId('sidebar-dashboard')).toHaveAccessibleName('Dashboard, 0 items need attention');
});

test('stale observations are priorities even when a host has no offline lifecycle', async ({ page }) => {
  await quietPortfolio(page);
  await page.addInitScript(() => {
    const clone = window.structuredClone;
    window.structuredClone = (value, options) => {
      const result = clone(value, options);
      if (result?.schema === 'odin.web.projection.snapshot/v0-draft') result.sessions[0].stale = true;
      return result;
    };
  });
  await page.goto('/#/');
  await expect(rowKind(page, 'host')).toHaveCount(1);
  await expect(rowKind(page, 'host')).toContainText('Stale observation');
  await expect(rowKind(page, 'host').getByRole('link')).toHaveAttribute('href', '#/sessions/ses-exec-01');
});

test('project tiles scope the tree and running table links recorded sessions with exact models and elapsed', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('dashboard-project')).toHaveCount(snapshot.projects.length);
  for (const p of snapshot.projects) {
    const tile = page.getByTestId('dashboard-project').filter({ hasText: p.name });
    await expect(tile).toHaveAttribute('href', `#/projects/${p.id}`);
    await expect(tile).toContainText(expectedTokens(snapshot.sessions.filter((s) => s.project_id === p.id)));
    await expect(tile.getByRole('img')).toHaveAccessibleName(/running|idle|needs you|No active sessions/);
  }
  const table = page.getByTestId('running-table');
  const running = snapshot.sessions.filter((s) => s.lifecycle === 'running');
  await expect(table.locator('tbody tr')).toHaveCount(running.length);
  await expect(table).toContainText('Fable 5.1');
  await expect(table).toContainText('Harness unknown');
  await expect(table).toContainText('elapsed unknown');
  for (const s of running) await expect(table.locator(`[data-session-id="${s.id}"] a`))
    .toHaveAttribute('href', `#/sessions/${s.id}`);
  await page.getByTestId('dashboard-project').filter({ hasText: 'Odin web app' }).click();
  await expect(page).toHaveURL(new RegExp(`#/projects/${PID}$`));
  await expect(page.getByTestId('project-node')).toHaveCount(1);
});

test('activity and running rows update during playback; pause freezes updates and the sidebar badge follows', async ({ page }) => {
  const time = new Date('2026-10-22T12:00:00Z');
  await page.clock.install({ time });
  await page.clock.pauseAt(time);
  await page.goto('/#/');
  const feed = page.getByTestId('recent-activity');
  const before = await feed.textContent();
  const player = page.getByTestId('autoplay-toggle');
  await player.click();
  await page.clock.runFor(1800);
  await expect(feed).not.toHaveText(before);
  await expect(page.getByTestId('kpi-running')).toHaveText('Running6');
  await page.clock.runFor(1200);
  await expect(page.getByTestId('running-table').locator('[data-session-id="ses-docs-helper"]')).toHaveCount(1);
  await expect(page.getByTestId('kpi-running')).toHaveText('Running7');
  await player.click();
  const paused = await feed.textContent();
  await page.clock.runFor(2400);
  await expect(feed).toHaveText(paused);
  await expect(queue(page).locator('.dashboard-section-head')).toContainText(
    `${await page.getByTestId('sidebar-dashboard').locator('.dashboard-badge').textContent()} open`);
});

test('dashboard follows input, failure and retirement, then continues into generated activity', async ({ page }) => {
  const time = new Date('2026-10-22T12:00:00Z');
  await page.clock.install({ time });
  await page.clock.pauseAt(time);
  await page.goto('/#/');
  await page.getByTestId('autoplay-toggle').click();
  await page.clock.runFor(19 * 1200);
  await filter(page, 'Needs you').click();
  await expect(queue(page).locator('[data-kind="needs"][data-attention-session="ses-live-a1"]')).toHaveCount(1);
  await expect(page.getByTestId('recent-activity')).toContainText('ops worker needs the operator');
  await page.clock.runFor(5 * 1200);
  await filter(page, 'Failed').click();
  const failed = queue(page).locator('[data-kind="failed"][data-attention-session="ses-live-a1"]');
  await expect(failed).toHaveCount(1);
  await expect(page.getByTestId('recent-activity')).toContainText('its run was recorded failed');
  await page.clock.runFor(1200);
  await expect(failed).toHaveCount(1);
  await expect(page.getByTestId('recent-activity')).toContainText('failed ops worker attempt 1 stopped');
  await page.clock.runFor(11 * 1200);
  await expect(page.getByTestId('recent-activity').locator('[data-event-id^="sim-"]')).not.toHaveCount(0);
  await expect(page.getByTestId('running-table').locator('[data-session-id="ses-sim-mvl79i-1"]')).toHaveCount(1);
  await page.getByTestId('autoplay-toggle').click();
});

for (const [width, columns] of [[1440, 3], [1100, 2], [800, 2], [480, 1]]) {
  test(`container layout at ${width}px has ${columns} columns and no horizontal overflow`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/#/');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    const grid = page.locator('.dashboard-grid');
    expect(await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(columns);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByTestId('dashboard-project').last()).toBeVisible();
    await shot(page, `dashboard-${width}`);
  });
}

test('fresh setup welcomes in the shell with empty portfolio, four steps, a primary action and no modal', async ({ page }) => {
  await page.goto('/?setup=fresh#/');
  await expect(page.getByTestId('welcome')).toBeVisible();
  await expect(page.getByTestId('dashboard')).toHaveCount(0);
  await expect(page.getByTestId('welcome').locator('li')).toHaveCount(4);
  await expect(page.locator('#app-sidebar')).toContainText('No executive yet');
  await expect(page.locator('#app-sidebar')).toContainText('No projects yet');
  await expect(page.getByTestId('sidebar-project')).toHaveCount(0);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await shot(page, 'dashboard-welcome');
  await page.getByRole('link', { name: 'Connect your first subscription' }).click();
  await expect(page).toHaveURL(/#\/setup\/providers$/);
  const row = page.getByTestId('lineage-executive-login');
  await row.getByRole('button', { name: 'Connect Executive login', exact: true }).click();
  await row.getByRole('button', { name: 'Simulate completed sign-in (synthetic)' }).click();
  await page.evaluate(() => { location.hash = '#/'; });
  await expect(page.getByTestId('dashboard')).toBeVisible();
  await expect(rows(page).first()).toHaveAttribute('data-kind', 'setup');
  await expect(page.getByTestId('dashboard-project')).toHaveCount(0);
  await expect(page.getByTestId('autoplay-toggle')).toBeDisabled();
});

test('partial setup leads queue, unfolds the checklist, and Apply removes it with a short confirmation', async ({ page }) => {
  await page.goto('/#/');
  const setup = rows(page).first();
  await expect(setup).toHaveAttribute('data-kind', 'setup');
  await expect(setup).toContainText('Next: Configure roles');
  await expect(setup.getByRole('progressbar')).toHaveAttribute('value', '3');
  await setup.getByRole('button').click();
  await expect(setup.locator('.priority-steps li')).toHaveCount(4);
  await setup.getByRole('link', { name: 'Continue setup', exact: true }).click();
  await expect(page).toHaveURL(/setup\/roles$/);
  await page.getByRole('button', { name: 'Continue', exact: false }).click();
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  const confirmation = page.getByRole('status').filter({ hasText: 'Applied (synthetic, not saved)' });
  await expect(confirmation).toBeVisible();
  await page.evaluate(() => { location.hash = '#/'; });
  await expect(confirmation).toBeVisible();
  await expect(rowKind(page, 'setup')).toHaveCount(0);
  await expect(page.getByTestId('setup-progress-card')).toHaveCount(0);
  await expect(confirmation).toHaveCount(0, { timeout: 6500 });
});

test('reduced motion changes KPI numbers immediately and disables dashboard fold and progress transitions', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const time = new Date('2026-10-22T12:00:00Z');
  await page.clock.install({ time });
  await page.clock.pauseAt(time);
  await page.goto('/#/');
  await rows(page).first().getByRole('button').click();
  expect(await page.locator('.priority-fold').first().evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
  await page.getByTestId('autoplay-toggle').click();
  await page.clock.runFor(1200);
  await expect(page.getByTestId('kpi-running')).toHaveText('Running6');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
