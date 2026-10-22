import fs from 'node:fs';
import path from 'node:path';

export const evidenceDir = process.env.EVIDENCE_DIR || 'test-results/screenshots';

export async function shot(page, name) {
  fs.mkdirSync(evidenceDir, { recursive: true });
  await page.screenshot({ path: path.join(evidenceDir, `${name}.png`), fullPage: true });
}

export const PID = 'proj-odin-webapp';
export const sessionUrl = (sid, pid = PID) => `/#/projects/${pid}/sessions/${sid}`;
