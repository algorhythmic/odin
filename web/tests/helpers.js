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
