import { expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const evidenceDir = process.env.EVIDENCE_DIR || 'test-results/screenshots';

export async function shot(page, name) {
  fs.mkdirSync(evidenceDir, { recursive: true });
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
}

export const PID = 'proj-odin-webapp';
export const sessionUrl = (sid, pid = PID) => sid === 'ses-exec-01' ? `/#/sessions/${sid}` : `/#/projects/${pid}/sessions/${sid}`;

// Fixtures are read as JSON so the specs see exactly what the app loads.
const fixtureDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'fixtures');
const readFixture = (name) => JSON.parse(fs.readFileSync(path.join(fixtureDir, name), 'utf8'));
export const snapshot = readFixture('default-snapshot.json');
export const eventFile = readFixture('default-events.json');
export const details = readFixture('default-details.json');

// Detail assertions explicitly expand cards that now default to one line.
export async function expandCards(page, ids) {
  for (const id of ids) {
    const card = page.locator(`[data-testid="session-card"][data-session-id="${id}"]`);
    const toggle = card.getByRole('button', { name: 'Expand card', exact: true });
    if (await toggle.count()) await toggle.click();
  }
  const stage = page.locator('.tree-stage');
  if (await stage.count()) await expect.poll(() => stage.evaluate((el) => el.getAnimations({ subtree: true })
    .filter((a) => a.effect?.getTiming().iterations !== Infinity).length)).toBe(0);
}
