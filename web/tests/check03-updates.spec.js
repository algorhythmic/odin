// Handoff check 3 (synthetic only): fixture update events applied by the
// prototype's update driver keep selection, expanded state and the reading
// position in the list and the transcript. No service or stream is involved.
import { test, expect } from '@playwright/test';
import { PID, sessionUrl, shot } from './helpers.js';

const applyNext = (page) => page.getByRole('button', { name: 'Apply next synthetic update' }).click();
const status = (page) => page.getByTestId('update-status');

test('update events apply once, report duplicates and gaps, and change the views', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await expect(page.getByTestId('revision')).toHaveText('0');
  await expect(page.locator('[data-session-id="ses-review-exec"]').first()).toContainText('Needs input');

  await applyNext(page); // evt-001: reviewer running again
  await expect(status(page)).toHaveText('Applied evt-001 (session.lifecycle_changed) at revision 1.');
  const reviewer = page.locator('[data-testid="session-card"][data-session-id="ses-review-exec"]');
  await expect(reviewer.getByTestId('state-label')).toHaveText('Running');
  await expect(reviewer).not.toContainText('Needs input');

  await applyNext(page); // evt-002: new child of the docs session
  await expect(status(page)).toHaveText('Applied evt-002 (session.started) at revision 2.');
  const helper = page.locator('[data-testid="session-card"][data-session-id="ses-docs-helper"]');
  await expect(helper).toHaveAttribute('data-parent', 'ses-docs-01');
  await expect(page.locator('path.ancestry-edge[data-from="ses-docs-01"][data-to="ses-docs-helper"]')).toHaveCount(1);

  await applyNext(page); // evt-002 re-delivered
  await expect(status(page)).toHaveText('Ignored evt-002: already applied (re-delivered event).');
  await expect(page.getByTestId('revision')).toHaveText('2');
  await expect(helper).toHaveCount(1);

  await applyNext(page); // evt-003: cost update
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toContainText('$2.45');
  await applyNext(page); // evt-004: retired
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-review-integ"]').getByTestId('state-label')).toHaveText('Retired');
  await applyNext(page); // evt-005: skips revisions
  await expect(status(page)).toHaveText('Not applied evt-005: revision 9 skips ahead of 4; a fresh snapshot is needed.');
  await expect(page.getByTestId('revision')).toHaveText('4');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-docs-01"]').getByTestId('state-label')).toHaveText('Running');
  await expect(page.getByRole('button', { name: 'Apply next synthetic update' })).toBeDisabled();
  // Activity lists the applied events, newest first.
  const activity = page.getByTestId('activity-item');
  await expect(activity.first()).toContainText('integration reviewer retired');
  await expect(activity.filter({ hasText: 'docs helper started by documentation' })).toHaveCount(1);
  await shot(page, 'updates-applied');
});

test('selection and collapsed branches survive updates', async ({ page }) => {
  await page.goto(sessionUrl('ses-worker-a2'));
  const integ = page.locator('[data-testid="session-card"][data-session-id="ses-integ-01"]');
  await expect(integ).toBeVisible();
  for (let i = 0; i < 5; i += 1) await applyNext(page);
  await expect(page.getByTestId('revision')).toHaveText('4');
  await expect(page).toHaveURL(/sessions\/ses-worker-a2$/);
  await expect(page.getByTestId('detail-panel')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(page.locator('[data-testid="session-card"].selected')).toHaveAttribute('data-session-id', 'ses-worker-a2');
  await expect(page.getByTestId('own-cost')).toHaveText('$2.45');

  // A fresh page starts from the snapshot again. Collapse a branch, then
  // apply events inside and outside it: the branch stays collapsed.
  await page.goto(`/#/projects/${PID}`);
  await page.reload();
  await integ.getByRole('button', { name: /Collapse 3 started sessions/ }).click();
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002 adds a child elsewhere
  await expect(integ.getByRole('button', { name: /Expand 3/ })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003 changes a hidden session
  await applyNext(page); // evt-004 retires a hidden session
  await expect(integ.getByRole('button', { name: /Expand 3/ })).toHaveAttribute('aria-expanded', 'false');
});

test('the list keeps its reading position when a session is inserted above it', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  const list = page.getByTestId('list-view');
  // The synthetic project has only 11 rows; a short list box lets the row
  // below the insertion point be the first visible row, as in a long list.
  await page.addStyleTag({ content: '.list-tree { max-height: 90px !important; }' });
  const row = page.locator('[role="treeitem"][data-session-id="ses-ops-01"]');
  // Scroll the list so the operations row is the first visible row.
  await list.evaluate((el) => {
    const r = el.querySelector('[data-session-id="ses-ops-01"]');
    el.scrollTop = r.offsetTop;
  });
  await expect.poll(() => list.evaluate((el) => {
    const r = el.querySelector('[data-session-id="ses-ops-01"]');
    return Math.round(r.getBoundingClientRect().top - el.getBoundingClientRect().top);
  }), 'the operations row is the first visible row').toBeLessThanOrEqual(1);
  const before = (await row.boundingBox()).y;
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002 inserts ses-docs-helper above ses-ops-01
  await expect(page.locator('[role="treeitem"][data-session-id="ses-docs-helper"]')).toHaveCount(1);
  const after = (await row.boundingBox()).y;
  expect(Math.abs(after - before), 'row did not move').toBeLessThanOrEqual(2);
  await shot(page, 'list-reading-position');
});

test('the transcript keeps its reading position when the session record changes', async ({ page }) => {
  await page.goto(sessionUrl('ses-worker-a2'));
  const transcript = page.getByTestId('transcript');
  await expect(transcript).toContainText('Progress note');
  await expect(page.getByTestId('transcript-pager')).toContainText('Page 1 of 2');
  await transcript.evaluate((el) => { el.scrollTop = 200; });
  const marker = await transcript.evaluate((el) => el.scrollTop);
  expect(marker).toBeGreaterThan(0);
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003 updates this session's cost
  await expect(page.getByTestId('own-cost')).toHaveText('$2.45');
  expect(await transcript.evaluate((el) => el.scrollTop)).toBe(marker);
  await expect(page.getByTestId('transcript-pager')).toContainText('Page 1 of 2');
  // Paging loads the next page for this session only.
  await page.getByRole('button', { name: 'Later' }).click();
  await expect(page.getByTestId('transcript-pager')).toContainText('Page 2 of 2');
  await expect(transcript).toContainText('Progress note 30:');
  await expect(transcript).not.toContainText('Progress note 1:');
});
