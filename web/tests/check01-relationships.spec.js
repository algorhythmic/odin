// Handoff check 1: ancestry, ownership and review are not conflated.
import { test, expect } from '@playwright/test';
import { expandCards, PID, sessionUrl, shot, snapshot } from './helpers.js';

const { sessions, relationships, assignments } = snapshot;

const projectSessions = sessions.filter((s) => s.project_id === PID && s.lifecycle !== 'retired');
const byId = new Map(sessions.map((s) => [s.id, s]));

test('fixture keeps ancestry separate from typed relationships', () => {
  // Exactly one session records a parent outside the data set, on purpose.
  const outside = sessions.filter((s) => s.parent_session_id && !byId.has(s.parent_session_id));
  expect(outside.map((s) => s.id)).toEqual(['ses-pin-audit']);
  expect(sessions.some((s) => s.project_id === PID && !s.parent_session_id && s.provenance === 'imported')).toBe(true);
  const reviews = relationships.filter((r) => r.type === 'review');
  expect(reviews.length).toBeGreaterThanOrEqual(2);
  for (const r of reviews) {
    // A reviewer is never recorded as started by the session it reviews.
    expect(byId.get(r.from).parent_session_id).not.toBe(r.to);
  }
  expect(new Set(reviews.map((r) => byId.get(r.from).parent_session_id)).size).toBe(2);
  expect(projectSessions.some((s) => s.resumption)).toBe(true);
  expect(projectSessions.some((s) => s.attempt_of && s.attempt > 1)).toBe(true);
  // Ownership points at a recorded session or is explicitly unknown.
  for (const a of assignments) {
    if (a.owner_session_id) expect(byId.has(a.owner_session_id), `${a.id} owner exists`).toBe(true);
  }
});

test('a recorded parent outside the view stays a labelled root, never a guessed edge', async ({ page }) => {
  const pid = 'proj-contract-pins';
  const count = sessions.filter((s) => s.project_id === pid).length;
  await page.goto(`/#/projects/${pid}`);
  await expandCards(page, ['ses-pin-audit']);
  await expect(page.getByTestId('session-card')).toHaveCount(count);
  await expect(page.getByTestId('project-node')).toHaveCount(1);
  const audit = page.locator('[data-testid="session-card"][data-session-id="ses-pin-audit"]');
  await expect(audit).toHaveAttribute('data-parent', 'ses-pin-archived');
  await expect(audit.getByTestId('lineage-label')).toHaveText('Parent not in this project view');
  const edges = await page.locator('path.ancestry-edge').evaluateAll((els) => els.map((e) => `${e.dataset.from}>${e.dataset.to}`));
  expect(edges.sort()).toEqual(['ses-exec-01>ses-pin-exec', 'ses-pin-audit>ses-pin-audit-helper', 'ses-pin-exec>ses-pin-worker']);
  // A branch with no known tokens shows no figure, never 0 tok.
  await expect(audit.getByText('branch unknown (2)', { exact: true })).toBeVisible();
  await expect(audit).not.toContainText('tok');
  await audit.click();
  await expect(page.getByTestId('started-by')).toHaveText('ses-pin-archived (not in this view; not inferred)');
  await expect(page.getByRole('button', { name: 'Go to parent' })).toBeDisabled();
  await shot(page, 'parent-outside-view');
  await page.getByRole('button', { name: 'List', exact: true }).click();
  await expect(page.locator('[role="treeitem"]')).toHaveCount(count + 1);
});

test('tree renders the ancestry forest and typed relationships distinctly', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expandCards(page, ['ses-worker-a1', 'ses-worker-a2']);
  await expect(page.getByTestId('synthetic-badge')).toBeVisible();
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

  // Retired imported roots and children retain their recorded lineage in the drawer.
  await expect(page.locator('[data-testid="session-card"][data-parent=""]')).toHaveCount(0);
  await page.goto(sessionUrl('ses-imported-01'));
  await expect(page.getByTestId('detail-lineage')).toHaveText('Imported — parent unknown');
  await expect(page.getByTestId('started-by')).toHaveText('Parent unknown (imported; not inferred)');
  await expect(page.getByRole('button', { name: 'Go to parent' })).toBeDisabled();
  await page.goto(sessionUrl('ses-helper-01'));
  await expect(page.getByTestId('started-by')).toContainText('ses-worker-a2');
  await expect(page.getByTestId('retired-notice')).toBeVisible();
  await page.goto(`/#/projects/${PID}`);

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

test('collapse hides descendants and automatic fit keeps their widths readable', async ({ page }) => {
  await page.goto(sessionUrl('ses-integ-01'));
  const integ = page.locator('[data-session-id="ses-integ-01"]');
  await integ.getByRole('button', { name: /Collapse 3 sessions under/ }).click();
  await expect(page.locator('[data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await expect(page.locator('[data-session-id="ses-helper-01"]')).toHaveCount(0);
  await expect(integ.getByRole('button', { name: /Expand 3/ })).toHaveAttribute('aria-expanded', 'false');
  await integ.getByRole('button', { name: /Expand 3/ }).click();
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toHaveCount(1);
  const view = await page.getByTestId('tree-view').boundingBox();
  for (const id of ['ses-integ-01', 'ses-worker-a1', 'ses-worker-a2', 'ses-review-integ']) {
    const box = await page.locator(`[data-testid="session-card"][data-session-id="${id}"]`).boundingBox();
    expect(box.x, `${id} left`).toBeGreaterThanOrEqual(view.x - 1);
    expect(box.x + box.width, `${id} right`).toBeLessThanOrEqual(view.x + view.width + 1);
  }
  await shot(page, 'fit-branch');
  await page.getByRole('button', { name: 'Go to parent' }).click();
  await expect(page).toHaveURL(/sessions\/ses-exec-01$/);
});

test('portfolio attention chips link to sessions and keep offline observations visible', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.getByTestId('synthetic-badge')).toBeVisible();
  await page.getByTestId('chip-needs').click();
  await page.getByTestId('attention-popover').getByRole('link').first().click();
  await expect(page).toHaveURL(/sessions\/ses-review-exec$/);
  await expect(page.getByTestId('detail-state')).toHaveText('Needs you');
  await page.goto('/#/sessions/ses-ops-01');
  await expect(page.getByTestId('detail-state')).toHaveText('Host offline');
  await expect(page.getByTestId('detail-own-tokens')).toHaveText('unknown');
  await shot(page, 'portfolio-attention');
});

test('go to parent follows recorded ancestry to the root, keeping the target in view', async ({ page }) => {
  await page.goto(sessionUrl('ses-helper-01'));
  const view = page.getByTestId('tree-view');
  for (const id of ['ses-worker-a2', 'ses-integ-01', 'ses-exec-01']) {
    await page.getByRole('button', { name: 'Go to parent' }).click();
    await expect(page).toHaveURL(new RegExp(`sessions/${id}$`));
    const selected = page.locator('[data-testid="session-card"].selected');
    await expect(selected).toHaveAttribute('data-session-id', id);
    await expect(selected).toBeInViewport();
    expect(await view.evaluate((el, sid) => {
      const v = el.getBoundingClientRect();
      const c = el.querySelector(`[data-testid="session-card"][data-session-id="${sid}"]`).getBoundingClientRect();
      return c.left >= v.left - 1 && c.right <= v.right + 1 && c.top >= v.top - 1 && c.bottom <= v.bottom + 1;
    }, id), `${id} inside the tree viewport`).toBe(true);
  }
  await expect(page.getByRole('button', { name: 'Go to parent' })).toBeDisabled();
  // A review relationship is never followed as parentage.
  await page.goto(sessionUrl('ses-review-integ'));
  await page.getByRole('button', { name: 'Go to parent' }).click();
  await expect(page).toHaveURL(/sessions\/ses-integ-01$/);
});

test('automatic width fit includes the forest and reset restores it after zoom', async ({ page }) => {
  await page.goto(sessionUrl('ses-exec-01'));
  const view = page.getByTestId('tree-view');
  await view.focus();
  await page.keyboard.press('+');
  await expect(page.getByRole('button', { name: 'Reset view' })).toBeVisible();
  await page.keyboard.press('0');
  await expect(page.getByRole('button', { name: 'Reset view' })).toHaveCount(0);
  const box = await view.boundingBox();
  for (const s of projectSessions) {
    const c = await page.locator(`[data-testid="session-card"][data-session-id="${s.id}"]`).boundingBox();
    expect(c.x, `${s.id} left`).toBeGreaterThanOrEqual(box.x - 1);
    expect(c.x + c.width, `${s.id} right`).toBeLessThanOrEqual(box.x + box.width + 1);
  }
  expect(Number(await view.getAttribute('data-scale'))).toBeGreaterThanOrEqual(0.85);
  await shot(page, 'automatic-fit');
});
