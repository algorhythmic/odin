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
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-review-integ"]')).toHaveCount(0);
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
  await expect(liveA1).toHaveCount(0);
  await applyNext(page); // evt-014: retry — a sibling attempt 2 appears
  const liveA2 = page.locator('[data-testid="session-card"][data-session-id="ses-live-a2"]');
  await expect(liveA2).toHaveAttribute('data-parent', 'ses-integ-01');
  await expect(liveA2.getByTestId('lineage-label')).toHaveText('Attempt 2 (after ses-live-a1)');
  await applyNext(page); // evt-015: attempt 2 usage
  await applyNext(page); // evt-016: scout needs the operator
  await applyNext(page); // evt-017: attempt 2 finishes
  await expect(liveA2.getByTestId('state-label')).toHaveText('Done');
  await expect(page.getByTestId('revision')).toHaveText('18');
  await expect(page.getByRole('button', { name: 'Apply next synthetic update' })).toBeEnabled();
  // Applied sessions stay inspectable after the conversation/activity panel was removed.
  await page.goto(sessionUrl('ses-live-a2'));
  await expect(page.getByTestId('run-outcome')).toContainText('not verified');
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
  await integ.getByRole('button', { name: /Collapse 3 sessions under/ }).click();
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002 adds a child elsewhere
  await expect(integ.getByRole('button', { name: /Expand 3/ })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('[data-testid="session-card"][data-session-id="ses-worker-a2"]')).toHaveCount(0);
  await applyNext(page); // duplicate
  await applyNext(page); // evt-003 changes a hidden session
  await applyNext(page); // evt-004 retires a hidden session
  await expect(integ.getByRole('button', { name: /Expand 2/ })).toHaveAttribute('aria-expanded', 'false');
});

test('the list keeps its page reading position when sessions are inserted and removed above it', async ({ page }) => {
  // The narrow detail panel follows the list, leaving room to read its last row near the top.
  await page.setViewportSize({ width: 700, height: 500 });
  await page.goto(sessionUrl('ses-ops-01'));
  const list = page.getByTestId('list-view');
  const row = list.locator('[data-session-id="ses-ops-01"]');
  await page.evaluate(() => {
    const row = document.querySelector('[role="treeitem"][data-session-id="ses-ops-01"]');
    // The first scroll pins the header; measure again at its sticky position.
    for (let i = 0; i < 2; i++) {
      const top = document.querySelector('.toolbar').getBoundingClientRect().bottom;
      scrollBy(0, row.getBoundingClientRect().top - top - 2);
    }
  });
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(0);
  await expect.poll(() => page.evaluate(() => {
    const top = document.querySelector('.toolbar').getBoundingClientRect().bottom;
    return [...document.querySelectorAll('[role="treeitem"]')]
      .find((el) => el.getBoundingClientRect().bottom > top + 4)?.dataset.sessionId;
  }), 'the operations row is the first readable row below the sticky header').toBe('ses-ops-01');
  const before = (await row.boundingBox()).y;
  const scrollBefore = await page.evaluate(() => scrollY);
  await applyNext(page); // evt-001
  await applyNext(page); // evt-002 inserts ses-docs-helper above ses-ops-01
  await expect(list.locator('[data-session-id="ses-docs-helper"]')).toHaveCount(1);
  await expect.poll(async () => Math.abs((await row.boundingBox()).y - before)).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => scrollY), 'the page compensates for the inserted row').toBeGreaterThan(scrollBefore);
  const beforeRemoval = await page.evaluate(() => scrollY);
  await applyNext(page); // duplicate
  await applyNext(page); // usage update
  await applyNext(page); // evt-004 retires ses-review-integ above the anchor
  await expect(list.locator('[data-session-id="ses-review-integ"]')).toHaveCount(0);
  await expect.poll(async () => Math.abs((await row.boundingBox()).y - before)).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => scrollY), 'the page compensates for the removed row').toBeLessThan(beforeRemoval);
  expect(await list.evaluate((el) => el.scrollTop)).toBe(0);
  await expect(page.getByTestId('tree-header')).toBeInViewport({ ratio: 1 });
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
