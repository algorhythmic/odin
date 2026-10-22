// Handoff check 9 (synthetic prototype timings): the seeded large dataset
// (2,000 sessions, 40 roots, depth 8) opened collapsed to its roots. Records
// first render, expand and select times in headless Chromium on this machine
// and writes them before comparing with the proposed targets. The targets
// are proposals (W2c); the values are written whether or not they pass,
// and a missed target then fails the run.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import { describeLarge, generateLargeSnapshot, LARGE_SEED, LARGE_SPEC } from '../src/fixtures/large.js';

const PID = LARGE_SPEC.projectId;
const URL = `/?dataset=large#/projects/${PID}`;
const TARGETS = { first_render_ms: 1000, expand_ms: 150, select_ms: 150 };
const LOADS = 5;
const SAMPLES = 8;
const outDir = process.env.EVIDENCE_DIR || 'test-results/perf';

const median = (xs) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
const summary = (xs) => ({ samples: xs.map((x) => Math.round(x * 10) / 10), median: Math.round(median(xs) * 10) / 10, max: Math.round(Math.max(...xs) * 10) / 10 });

// Time from a click to the frame after the expected DOM change, in the page.
// `done` is data, not code: either { cards: n } or { detail: sessionId }.
const timedClick = (page, selector, done) => page.evaluate(([sel, want]) => new Promise((resolve, reject) => {
  const target = document.querySelector(sel);
  if (!target) { reject(new Error(`missing ${sel}`)); return; }
  const check = () => ('cards' in want
    ? document.querySelectorAll('[data-testid="session-card"]').length === want.cards
    : document.querySelector('[data-testid="detail-panel"]')?.dataset.sessionId === want.detail);
  const t0 = performance.now();
  const finish = () => requestAnimationFrame(() => resolve(performance.now() - t0));
  const obs = new MutationObserver(() => { if (check()) { obs.disconnect(); finish(); } });
  obs.observe(document.body, { childList: true, subtree: true, attributes: true });
  target.click();
  if (check()) { obs.disconnect(); finish(); }
}), [selector, done]);

test('large synthetic tree: first render, expand and select timings', async ({ page, browserName }) => {
  test.setTimeout(120_000);
  const data = describeLarge(generateLargeSnapshot());
  expect(data.sessions).toBe(2000);
  const snapshot = generateLargeSnapshot();
  const kids = new Map();
  for (const s of snapshot.sessions) if (s.parent_session_id) kids.set(s.parent_session_id, (kids.get(s.parent_session_id) || 0) + 1);
  const roots = snapshot.sessions.filter((s) => !s.parent_session_id).map((s) => s.id);

  const first = [];
  for (let i = 0; i < LOADS; i += 1) {
    await page.goto('about:blank');
    await page.goto(URL);
    await expect(page.getByTestId('session-card')).toHaveCount(roots.length);
    const t = await page.evaluate(() => new Promise((resolve) => {
      const read = () => performance.getEntriesByName('odin:tree-rendered')[0]?.startTime;
      const poll = () => (read() != null ? resolve(read()) : setTimeout(poll, 5));
      poll();
    }));
    first.push(t);
  }
  await page.screenshot({ path: path.join(outDir, 'large-collapsed.png') }).catch(() => {});

  // Expand: the roots with the most children, one at a time, collapsing again after.
  const expandIds = [...roots].sort((a, b) => (kids.get(b) || 0) - (kids.get(a) || 0)).slice(0, SAMPLES);
  const expand = [];
  for (const id of expandIds) {
    const n = kids.get(id) || 0;
    const sel = `[data-testid="session-card"][data-session-id="${id}"] button.toggle`;
    expand.push(await timedClick(page, sel, { cards: roots.length + n }));
    await page.locator(sel).click();
    await expect(page.getByTestId('session-card')).toHaveCount(roots.length);
  }

  // Select: root cards across the forest; done when the detail panel shows it.
  const select = [];
  for (const id of roots.filter((_, i) => i % 5 === 0).slice(0, SAMPLES)) {
    select.push(await timedClick(page, `[data-testid="session-card"][data-session-id="${id}"] .card-title`, { detail: id }));
  }
  await page.screenshot({ path: path.join(outDir, 'large-selected.png') }).catch(() => {});

  const result = {
    label: 'synthetic prototype timings (not service integration)',
    dataset: { ...data, seed: LARGE_SEED },
    method: {
      first_render: `performance mark "odin:tree-rendered" (TreeView first effect) relative to navigation start; ${LOADS} fresh loads of the built app from vite preview on 127.0.0.1`,
      expand: 'in-page click on a root\'s expand toggle until the expected card count is in the DOM, plus one animation frame',
      select: 'in-page click on a card title until the detail panel shows that session, plus one animation frame (transcript loads after)',
      browser: `${browserName} headless (Playwright ${test.info().config.version})`,
    },
    machine: { platform: os.platform(), release: os.release(), cpus: os.cpus().length, cpu_model: os.cpus()[0]?.model, memory_gb: Math.round(os.totalmem() / 2 ** 30) },
    caveat: 'Single workstation, headless, no throttling, other load unknown; not representative of the desktop window or a service-backed tree.',
    targets_proposed: TARGETS,
    first_render_ms: summary(first),
    expand_ms: summary(expand),
    select_ms: summary(select),
  };
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'large-timings.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({ first: result.first_render_ms, expand: result.expand_ms, select: result.select_ms }));

  expect.soft(result.first_render_ms.median, 'first render median vs proposed 1 s').toBeLessThan(TARGETS.first_render_ms);
  expect.soft(result.expand_ms.max, 'slowest expand vs proposed 150 ms').toBeLessThan(TARGETS.expand_ms);
  expect.soft(result.select_ms.max, 'slowest select vs proposed 150 ms').toBeLessThan(TARGETS.select_ms);
});
