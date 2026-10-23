import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { CARD, fitTree, intersects, routeRelationship } from '../src/tree-layout.js';
import { groupedTree, projectAncestry } from '../src/ancestry.js';
import { generateLargeSnapshot } from '../src/fixtures/large.js';

const snapshot = JSON.parse(fs.readFileSync(new URL('../fixtures/default-snapshot.json', import.meta.url)));
function hierarchy(s = snapshot, scoped = false) {
  const executive = s.sessions.find((x) => x.id === s.executive_session_id);
  const h = groupedTree(scoped ? s.projects.slice(0, 1) : s.projects, executive,
    (p) => projectAncestry(s.sessions, p, s.executive_session_id), scoped);
  return { roots: h.roots, children: h.children, executiveId: s.executive_session_id };
}
const fit = (width, h = hierarchy()) => fitTree(h, CARD, width);

test('tries tidy, then deepest stacking, then wrapping before shrinking', () => {
  const tidy = fit(6000);
  assert.equal(tidy.mode, 'tidy');
  const roots = hierarchy().children.get('project:proj-odin-webapp');
  const row = roots.map((s) => tidy.positions.get(s.id));
  assert.ok(row.every((p) => p.y === row[0].y));
  assert.ok(row.slice(1).every((p, i) => p.x > row[i].x));
  assert.equal(fit(3000).mode, 'stack-3');
  assert.equal(fit(1800).mode, 'stack-2');
  assert.equal(fit(1072).mode, 'projects-wrap-2');
  assert.equal(fit(732).mode, 'projects-wrap-4');
  for (const width of [6000, 3000, 1800, 1072, 732, 768, 400]) {
    const l = fit(width);
    assert.ok(l.scale >= 0.85);
    assert.ok(l.width * l.scale <= width);
    const boxes = [...l.positions.values()];
    boxes.forEach((a, i) => boxes.slice(i + 1).forEach((b) => assert.ok(!intersects(a, b))));
  }
  assert.equal(fit(120).scale, 0.5);
  assert.ok(fit(120).width * 0.5 > 120);
});

test('ancestry and labelled-root grouping survive every arrangement unchanged', () => {
  const reference = fit(6000).edges.map((e) => `${e.ancestryFrom || e.from}>${e.to}:${e.grouping}`).sort();
  for (const w of [3000, 1800, 1072, 732, 120]) {
    const l = fit(w);
    assert.deepEqual(l.edges.map((e) => `${e.ancestryFrom || e.from}>${e.to}:${e.grouping}`).sort(), reference);
    assert.equal(l.positions.size, snapshot.sessions.length + snapshot.projects.length);
    assert.ok(!l.edges.some((e) => !e.grouping && e.to === 'ses-mal-cycle-a'));
    assert.ok(l.dots.every((d) => l.edges.some((e) => e.from === d.id && !e.grouping)));
  }
});

test('stacking indents children and allocates preceding subtrees without overlap', () => {
  const l = fit(732);
  const p = l.positions;
  for (const e of l.edges.filter((e) => e.kind === 'stack')) {
    assert.ok(p.get(e.to).x > p.get(e.from).x);
    assert.ok(p.get(e.to).y > p.get(e.from).y + p.get(e.from).h);
    assert.ok(!/[CQSTA]/.test(e.d));
  }
  const boxes = [...p.values()];
  boxes.forEach((a, i) => boxes.slice(i + 1).forEach((b) => assert.ok(!intersects(a, b))));
});

test('collapse, empty hierarchies and scoped roots have finite deterministic geometry', () => {
  const h = hierarchy();
  const collapsed = new Set([snapshot.executive_session_id]);
  assert.equal(fit(700, { ...h, collapsed }).positions.size, 1);
  const empty = fitTree({ roots: [], children: new Map() }, CARD, 700);
  assert.ok(Number.isFinite(empty.scale) && empty.width > 0 && empty.height > 0);
  assert.deepEqual(fit(800, hierarchy(snapshot, true)), fit(800, hierarchy(snapshot, true)));
  assert.equal(h.children.get(snapshot.executive_session_id).length, snapshot.projects.length);
});

test('pills clear every card across modes and counter-scale at zoom limits', () => {
  for (const scoped of [false, true]) for (const width of [6000, 3000, 1072, 732, 768]) {
    const l = fit(width, hierarchy(snapshot, scoped));
    const boxes = [...l.positions.values()];
    for (const scale of [0.5, 0.85, 1, 2]) for (const r of snapshot.relationships) {
      const to = r.type === 'assignment_owner'
        ? snapshot.assignments.find((a) => a.id === r.to)?.owner_session_id : r.to;
      if (!l.positions.has(r.from) || !l.positions.has(to)) continue;
      const line = routeRelationship(l.positions.get(r.from), l.positions.get(to), boxes, r.type, scale);
      assert.ok(boxes.every((c) => !intersects(line.labelBox, c)), `${width}: ${r.id}`);
      assert.ok(line.fontScale * scale >= 0.85 && line.fontScale * scale <= 1.25);
    }
  }
});

test('full seeded hierarchy fits bounded width without losing nodes', () => {
  const l = fit(732, hierarchy(generateLargeSnapshot()));
  assert.equal(l.positions.size, 2002);
  assert.ok(l.scale >= 0.85);
  assert.ok(l.height > 900);
});
