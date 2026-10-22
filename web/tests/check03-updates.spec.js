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

  await applyNext(page); // evt-003: usage update
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toContainText('19.8k tok');
  await applyNext(page); // evt-004: retired
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-review-integ"]').getByTestId('state-label')).toHaveText('Stopped');
  // Malformed events change nothing and keep the revision.
  await applyNext(page); // evt-bad-1: unknown session
  await expect(status(page)).toHaveText('Rejected evt-bad-1: unknown session.');
  await expect(page.getByTestId('revision')).toHaveText('4');
  await applyNext(page); // evt-bad-2: unknown event type
  await expect(status(page)).toHaveText('Rejected evt-bad-2: unknown event type.');
  await expect(page.getByTestId('revision')).toHaveText('4');
  // The remaining malformed deliveries (unit-tested in tests-unit/) are rejected too.
  for (const [id, reason] of [
    ['evt-bad-3', 'revision is not an integer'], ['evt-bad-4', 'missing session record'],
    ['evt-bad-5', 'session already exists'], ['evt-bad-6', 'unknown lifecycle'], ['evt-bad-7', 'missing session_id'],
    ['evt-bad-8', 'session id is not a string'], ['evt-bad-9', 'unknown project'],
  ]) {
    await applyNext(page);
    await expect(status(page)).toHaveText(`Rejected ${id}: ${reason}.`);
    await expect(page.getByTestId('revision')).toHaveText('4');
  }
  await applyNext(page); // evt-bad-6 re-delivered, corrected: applies
  await expect(status(page)).toHaveText('Applied evt-bad-6 (session.lifecycle_changed) at revision 5.');
  await expect(page.getByTestId('revision')).toHaveText('5');
  await applyNext(page); // evt-005: skips revisions
  await expect(status(page)).toHaveText('Not applied evt-005: revision 9 skips ahead of 5; a fresh snapshot is needed.');
  await expect(page.getByTestId('revision')).toHaveText('5');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-docs-01"]').getByTestId('state-label')).toHaveText('Running');
  // The live-run deliveries follow. evt-005 is re-delivered once the
  // missed revisions have arrived and applies late, so the gap repairs.
  await applyNext(page); // evt-006: a scout appears under the executive
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-live-scout"]')).toHaveAttribute('data-parent', 'ses-exec-01');
  await applyNext(page); // evt-007: ops worker attempt 1 under the integration owner
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-live-a1"]')).toHaveAttribute('data-parent', 'ses-integ-01');
  await applyNext(page); // evt-008: attempt 1 needs the operator
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-live-a1"]').getByTestId('state-label')).toHaveText('Needs you');
  await applyNext(page); // evt-005 re-delivered: the missed revisions are in, it applies
  await expect(status(page)).toHaveText('Applied evt-005 (session.lifecycle_changed) at revision 9.');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-docs-01"]').getByTestId('state-label')).toHaveText('Idle');
  await applyNext(page); // evt-009: running again
  await applyNext(page); // evt-010: scout usage
  await applyNext(page); // evt-011: attempt 1 usage
  await applyNext(page); // evt-012: attempt 1 ended; run recorded failed
  const liveA1 = page.locator('[data-testid="session-card"][data-session-id="ses-live-a1"]');
  await expect(liveA1.getByTestId('state-label')).toHaveText('Failed');
  await applyNext(page); // evt-013: the failed attempt is stopped
  await expect(liveA1.getByTestId('state-label')).toHaveText('Stopped');
  await applyNext(page); // evt-014: retry — a sibling attempt 2 appears
  const liveA2 = page.locator('[data-testid="session-card"][data-session-id="ses-live-a2"]');
  await expect(liveA2).toHaveAttribute('data-parent', 'ses-integ-01');
  await expect(liveA2.getByTestId('lineage-label')).toHaveText('Attempt 2 (after ses-live-a1)');
  await applyNext(page); // evt-015: attempt 2 usage
  await applyNext(page); // evt-016: scout needs the operator
  await applyNext(page); // evt-017: attempt 2 finishes
  await expect(liveA2.getByTestId('state-label')).toHaveText('Done');
  await expect(page.getByTestId('revision')).toHaveText('18');
  await expect(page.getByRole('button', { name: 'Apply next synthetic update' })).toBeDisabled();
  // Activity lists the applied events, newest first.
  const activity = page.getByTestId('activity-item');
  await expect(activity.first()).toContainText('ops worker attempt 2 finished');
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
  await expect(page.getByTestId('detail-own-tokens')).toHaveText('19.8k tok');

  // A fresh page starts from the snapshot again. Collapse a branch, then
  // apply events inside and outside it: the branch stays collapsed.
  await page.goto(`/#/projects/${PID}`);
  await page.reload();
  await integ.getByRole('button', { name: /Collapse 4 sessions under/ }).click();
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002 adds a child elsewhere
  await expect(integ.getByRole('button', { name: /Expand 4/ })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003 changes a hidden session
  await applyNext(page); // evt-004 retires a hidden session
  await expect(integ.getByRole('button', { name: /Expand 4/ })).toHaveAttribute('aria-expanded', 'false');
});

test('the list keeps its reading position when a session is inserted above it', async ({ page }) => {
  await page.goto(`/#/projects/${PID}`);
  await page.getByRole('button', { name: 'List', exact: true }).click();
  const list = page.getByTestId('list-view');
  // The synthetic project has only 11 rows; a short list box lets the row
  // below the insertion point be the first visible row, as in a long list.
  await page.addStyleTag({ content: '.list-tree { max-height: 90px !important; }' });
  await expect.poll(() => list.evaluate((el) => el.scrollHeight > el.clientHeight), 'the short list box scrolls').toBe(true);
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
  await applyNext(page); // evt-003 updates this session's tokens
  await expect(page.getByTestId('detail-own-tokens')).toHaveText('19.8k tok');
  expect(await transcript.evaluate((el) => el.scrollTop)).toBe(marker);
  await expect(page.getByTestId('transcript-pager')).toContainText('Page 1 of 2');
  // Paging loads the next page for this session only.
  await page.getByRole('button', { name: 'Later' }).click();
  await expect(page.getByTestId('transcript-pager')).toContainText('Page 2 of 2');
  await expect(transcript).toContainText('Progress note 30:');
  await expect(transcript).not.toContainText('Progress note 1:');
});
