// Handoff check 1: ancestry, ownership and review are not conflated.
import { test, expect } from '@playwright/test';
import { sessions, relationships, assignments } from '../src/fixtures/synthetic.js';
import { PID, sessionUrl, shot } from './helpers.js';

const projectSessions = sessions.filter((s) => s.project_id === PID);
const byId = new Map(sessions.map((s) => [s.id, s]));

test('fixture keeps ancestry separate from typed relationships', () => {
  for (const s of sessions) {
    if (s.parent_session_id) expect(byId.has(s.parent_session_id), `${s.id} parent exists`).toBe(true);
  }
  const roots = projectSessions.filter((s) => !s.parent_session_id);
  expect(roots.length).toBeGreaterThanOrEqual(2);
  expect(roots.some((s) => s.provenance === 'imported')).toBe(true);
  const reviews = relationships.filter((r) => r.type === 'review');
  expect(reviews.length).toBeGreaterThanOrEqual(2);
  for (const r of reviews) {
    // A reviewer is never recorded as started by the session it reviews.
    expect(byId.get(r.from).parent_session_id).not.toBe(r.to);
  }
  expect(new Set(reviews.map((r) => byId.get(r.from).parent_session_id)).size).toBe(2);
  expect(projectSessions.some((s) => s.resumption)).toBe(true);
  expect(projectSessions.some((s) => s.attempt_of && s.attempt > 1)).toBe(true);
  expect(assignments.every((a) => a.id)).toBe(true);
});

test('tree renders the ancestry forest and typed relationships distinctly', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(page.getByTestId('synthetic-banner')).toBeVisible();
  const cards = page.getByTestId('session-card');
  await expect(cards).toHaveCount(projectSessions.length);

  // Every card's tree parent is the recorded parent_session_id, nothing else.
  for (const s of projectSessions) {
    await expect(page.locator(`[data-testid="session-card"][data-session-id="${s.id}"]`))
      .toHaveAttribute('data-parent', s.parent_session_id || '');
  }
  // Ancestry edges are exactly parent -> child pairs from the fixture.
  const edges = await page.locator('path.ancestry-edge').evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));
  const expected = projectSessions.filter((s) => s.parent_session_id).map((s) => `${s.parent_session_id}>${s.id}`);
  expect(edges.sort()).toEqual(expected.sort());
  // A review is never drawn as parentage in either direction.
  for (const r of relationships.filter((x) => x.type === 'review')) {
    expect(edges).not.toContain(`${r.from}>${r.to}`);
    expect(edges).not.toContain(`${r.to}>${r.from}`);
  }

  // Multiple roots, including the unparented imported session.
  await expect(page.locator('[data-testid="session-card"][data-parent=""]')).toHaveCount(2);
  const imported = page.locator('[data-session-id="ses-imported-01"]');
  await expect(imported.getByTestId('lineage-label')).toHaveText('Imported — parent unknown');

  // Nested child: helper -> worker attempt 2 -> integration owner -> executive.
  await expect(page.locator('[data-session-id="ses-helper-01"]')).toHaveAttribute('data-parent', 'ses-worker-a2');

  // Delegation is drawn as its own typed overlay, even where it coincides with ancestry.
  await expect(page.locator('.relation-edge[data-type="delegation"]')).toHaveCount(1);

  // Two reviewers in different tree positions, each linked by a typed review edge.
  await expect(page.locator('.relation-edge[data-type="review"]')).toHaveCount(2);
  await expect(page.locator('[data-session-id="ses-review-exec"]')).toHaveAttribute('data-parent', 'ses-exec-01');
  await expect(page.locator('[data-session-id="ses-review-integ"]')).toHaveAttribute('data-parent', 'ses-integ-01');

  // Resumption and new attempt are labelled differently.
  await expect(page.locator('[data-session-id="ses-docs-01"]').getByTestId('lineage-label')).toHaveText(/Resumed ×1 \(same session\)/);
  await expect(page.locator('[data-session-id="ses-worker-a2"]').getByTestId('lineage-label')).toHaveText(/Attempt 2 \(after ses-worker-a1\)/);
  await expect(page.locator('[data-session-id="ses-worker-a1"]').getByTestId('lineage-label')).toHaveText(/^Attempt 1$/);
  await shot(page, 'project-tree');

  // Detail panel lists the review as a typed relationship, not as parentage.
  await page.goto(sessionUrl('ses-review-integ'));
  const panel = page.getByTestId('detail-panel');
  await expect(panel.getByTestId('started-by')).toContainText('ses-integ-01');
  await expect(panel.locator('[data-relationship-type="review"]')).toContainText('ses-worker-a2');
  await page.goto(sessionUrl('ses-worker-a2'));
  await expect(panel.locator('[data-relationship-type="review"]')).toHaveCount(2);
  await expect(panel.getByTestId('started-by')).toContainText('ses-integ-01');
  await expect(panel.getByTestId('run-outcome')).toHaveText(/Session ended — run not verified/);
  await expect(panel.getByTestId('transcript-gap')).toBeVisible();
  await shot(page, 'detail-panel');
});

test('collapse hides descendants and fit branch scales to the selection', async ({ page }) => {
  await page.goto(sessionUrl('ses-integ-01'));
  const integ = page.locator('[data-session-id="ses-integ-01"]');
  await integ.getByRole('button', { name: /Collapse 3 started sessions/ }).click();
  await expect(page.locator('[data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await expect(page.locator('[data-session-id="ses-helper-01"]')).toHaveCount(0);
  await expect(integ.getByRole('button', { name: /Expand 3/ })).toHaveAttribute('aria-expanded', 'false');
  await integ.getByRole('button', { name: /Expand 3/ }).click();
  await expect(page.locator('[data-session-id="ses-helper-01"]')).toHaveCount(1);
  await page.getByRole('button', { name: 'Fit branch' }).click();
  const view = await page.getByTestId('tree-view').boundingBox();
  for (const id of ['ses-integ-01', 'ses-worker-a1', 'ses-worker-a2', 'ses-helper-01', 'ses-review-integ']) {
    const box = await page.locator(`[data-testid="session-card"][data-session-id="${id}"]`).boundingBox();
    expect(box.x, `${id} left`).toBeGreaterThanOrEqual(view.x - 1);
    expect(box.y, `${id} top`).toBeGreaterThanOrEqual(view.y - 1);
    expect(box.x + box.width, `${id} right`).toBeLessThanOrEqual(view.x + view.width + 1);
    expect(box.y + box.height, `${id} bottom`).toBeLessThanOrEqual(view.y + view.height + 1);
  }
  await shot(page, 'fit-branch');
  await page.getByRole('button', { name: 'Go to parent' }).click();
  await expect(page).toHaveURL(/sessions\/ses-exec-01$/);
});

test('overview shows attention items that link to sessions', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('synthetic-banner')).toBeVisible();
  const items = page.getByTestId('attention-item');
  for (const label of ['Pending approval', 'Pending decision', 'Needs input', 'Host offline', 'Blocked']) {
    await expect(items.filter({ hasText: label }).first()).toBeVisible();
  }
  await shot(page, 'overview');
  await items.filter({ hasText: 'Host offline' }).first().getByRole('link').click();
  await expect(page).toHaveURL(/sessions\/ses-ops-01$/);
  await expect(page.getByTestId('detail-state')).toHaveText('Host offline');
  await expect(page.getByTestId('own-cost')).toHaveText('cost unknown');
});
