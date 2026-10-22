// Handoff check 9 (synthetic prototype timings): the seeded large dataset
// (2,000 project sessions, 40 executive starts, depth 8, plus one executive) opened collapsed to its project node. Records
// first render, expand and select times, and expanding whole depth-8 paths
// in the tree and the list, in headless Chromium on this machine
// and writes them before comparing with the proposed targets. The targets
// are proposals (W2c); the values are written whether or not they pass,
// and a missed target then fails the run.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import { describeLarge, generateLargeSnapshot, LARGE_SEED, LARGE_SPEC } from '../src/fixtures/large.js';

const PID = LARGE_SPEC.projectId;
const URL = '/?dataset=large#/';
const PROJECT = `project:${PID}`;
const TARGETS = { first_render_ms: 1000, expand_ms: 150, select_ms: 150 };
const DEEP_PATHS = 3;
const LOADS = 5;
const SAMPLES = 8;
const outDir = process.env.EVIDENCE_DIR || 'test-results/perf';

const median = (xs) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
const machine = () => ({ platform: os.platform(), release: os.release(), cpus: os.cpus().length, cpu_model: os.cpus()[0]?.model, memory_gb: Math.round(os.totalmem() / 2 ** 30) });
const CAVEAT = 'Single workstation, headless, no throttling, other load unknown; not representative of the desktop window or a service-backed tree.';
const summary = (xs) => ({ samples: xs.map((x) => Math.round(x * 10) / 10), median: Math.round(median(xs) * 10) / 10, max: Math.round(Math.max(...xs) * 10) / 10 });

// Time from a click to the frame after the expected DOM change, in the page.
// `done` is data, not code: { cards: n }, { rows: n } (list items) or
// { detail: sessionId }.
const timedClick = (page, selector, done) => page.evaluate(([sel, want]) => new Promise((resolve, reject) => {
  const target = document.querySelector(sel);
  if (!target) { reject(new Error(`missing ${sel}`)); return; }
  const check = () => {
    if ('cards' in want) return document.querySelectorAll('[data-testid="session-card"]').length === want.cards;
    if ('rows' in want) return document.querySelectorAll('[role="treeitem"]').length === want.rows;
    return document.querySelector('[data-testid="detail-panel"]')?.dataset.sessionId === want.detail;
  };
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
  expect(data.sessions).toBe(2001);
  const snapshot = generateLargeSnapshot();
  const kids = new Map();
  for (const s of snapshot.sessions) if (s.parent_session_id) kids.set(s.parent_session_id, (kids.get(s.parent_session_id) || 0) + 1);
  const roots = snapshot.sessions.filter((s) => s.parent_session_id === snapshot.executive_session_id).map((s) => s.id);

  const first = [];
  for (let i = 0; i < LOADS; i += 1) {
    await page.goto('about:blank');
    await page.goto(URL);
    await expect(page.getByTestId('session-card')).toHaveCount(1);
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
  const expand = [await timedClick(page, '[data-testid="project-node"]', { cards: roots.length + 1 })];
  for (const id of expandIds) {
    const n = kids.get(id) || 0;
    const sel = `[data-testid="session-card"][data-session-id="${id}"] button.toggle`;
    expand.push(await timedClick(page, sel, { cards: roots.length + 1 + n }));
    await page.locator(sel).click();
    await expect(page.getByTestId('session-card')).toHaveCount(roots.length + 1);
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
      expand: 'in-page click on a project or session expand toggle until the expected card count is in the DOM, plus one animation frame',
      select: 'in-page click on a card title until the detail panel shows that session, plus one animation frame (transcript loads after)',
      browser: `${browserName} headless (Playwright ${test.info().config.version})`,
    },
    machine: machine(),
    caveat: CAVEAT,
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

// Root-to-leaf paths ending at the deepest sessions, from distinct roots.
function deepPaths(snapshot, count) {
  const byId = new Map(snapshot.sessions.map((x) => [x.id, x]));
  const pathTo = (x) => { const p = [x.id]; for (let q = x.parent_session_id; q && q !== snapshot.executive_session_id; q = byId.get(q).parent_session_id) p.unshift(q); return p; };
  const all = snapshot.sessions.filter((s) => s.id !== snapshot.executive_session_id).map(pathTo).sort((a, b) => b.length - a.length || a.at(-1).localeCompare(b.at(-1)));
  const picked = [];
  for (const p of all) if (!picked.some((q) => q[0] === p[0])) { picked.push(p); if (picked.length === count) break; }
  return picked;
}

test('large synthetic tree: expanding depth-8 paths in the tree and the list', async ({ page, browserName }) => {
  test.setTimeout(180_000);
  const snapshot = generateLargeSnapshot();
  const kids = new Map();
  for (const x of snapshot.sessions) if (x.parent_session_id) kids.set(x.parent_session_id, (kids.get(x.parent_session_id) || 0) + 1);
  const roots = snapshot.sessions.filter((x) => x.parent_session_id === snapshot.executive_session_id).length;
  const paths = deepPaths(snapshot, DEEP_PATHS);
  expect(paths.every((p) => p.length === LARGE_SPEC.maxDepth)).toBe(true);

  const fresh = async (mode) => {
    await page.goto(URL);
    await page.evaluate(() => localStorage.clear());
    await page.goto('about:blank');
    await page.goto(URL);
    await expect(page.getByTestId('session-card')).toHaveCount(1);
    if (mode === 'list') {
      await page.getByRole('button', { name: 'List', exact: true }).click();
      await expect(page.getByRole('treeitem')).toHaveCount(2);
    }
  };

  const tree = { step: [], total: [], select: [] };
  for (const p of paths) {
    await fresh('tree');
    let shown = roots + 1;
    let total = await timedClick(page, '[data-testid="project-node"]', { cards: shown });
    tree.step.push(total);
    for (const id of p.slice(0, -1)) {
      shown += kids.get(id);
      const t = await timedClick(page, `[data-testid="session-card"][data-session-id="${id}"] button.toggle`, { cards: shown });
      tree.step.push(t);
      total += t;
    }
    tree.total.push(total);
    const leaf = p.at(-1);
    tree.select.push(await timedClick(page, `[data-testid="session-card"][data-session-id="${leaf}"] .card-title`, { detail: leaf }));
  }
  await page.screenshot({ path: path.join(outDir, 'large-deep-tree.png') }).catch(() => {});

  const list = { step: [], total: [] };
  for (const p of paths) {
    await fresh('list');
    let shown = roots + 2;
    let total = await timedClick(page, `[role="treeitem"][data-session-id="${PROJECT}"] [data-testid="list-toggle"]`, { rows: shown });
    list.step.push(total);
    for (const id of p.slice(0, -1)) {
      shown += kids.get(id);
      const t = await timedClick(page, `[role="treeitem"][data-session-id="${id}"] [data-testid="list-toggle"]`, { rows: shown });
      list.step.push(t);
      total += t;
    }
    list.total.push(total);
  }
  await page.screenshot({ path: path.join(outDir, 'large-deep-list.png') }).catch(() => {});

  const result = {
    label: 'synthetic prototype timings (not service integration)',
    dataset: { ...describeLarge(snapshot), seed: LARGE_SEED },
    paths: paths.map((p) => ({ root: p[0], leaf: p.at(-1), depth: p.length, cards_added: p.slice(0, -1).map((id) => kids.get(id)) })),
    method: {
      step: 'one project or session expand on a depth-8 path, from a fresh load with every branch collapsed: in-page click on the toggle until the expected number of cards (tree) or rows (list) is in the DOM, plus one animation frame',
      total: 'project expansion plus seven ancestry expansions along one path',
      select: 'in-page click on the depth-8 card title until the detail panel shows it, plus one frame (assignment lookup by index)',
      browser: `${browserName} headless (Playwright ${test.info().config.version})`,
    },
    machine: machine(),
    caveat: CAVEAT,
    targets_proposed: { expand_step_ms: TARGETS.expand_ms, select_ms: TARGETS.select_ms, path_total_ms: null },
    tree_expand_step_ms: summary(tree.step),
    tree_path_total_ms: summary(tree.total),
    tree_deep_select_ms: summary(tree.select),
    list_expand_step_ms: summary(list.step),
    list_path_total_ms: summary(list.total),
  };
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'large-deep-timings.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({ tree: result.tree_expand_step_ms, tree_total: result.tree_path_total_ms, select: result.tree_deep_select_ms, list: result.list_expand_step_ms, list_total: result.list_path_total_ms }));

  expect.soft(result.tree_expand_step_ms.max, 'slowest tree expand step vs proposed 150 ms').toBeLessThan(TARGETS.expand_ms);
  expect.soft(result.list_expand_step_ms.max, 'slowest list expand step vs proposed 150 ms').toBeLessThan(TARGETS.expand_ms);
  expect.soft(result.tree_deep_select_ms.max, 'slowest deep select vs proposed 150 ms').toBeLessThan(TARGETS.select_ms);
});
