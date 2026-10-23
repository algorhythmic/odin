import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { cardDimensions, cardIsExpanded } from '../src/card-size.js';
import { CARD, createRelationshipRouter, fitTree, intersects, routeOrthogonal, routeRelationship, segmentIntersects } from '../src/tree-layout.js';
import { groupedTree, projectAncestry } from '../src/ancestry.js';
import { generateLargeSnapshot, LARGE_SPEC } from '../src/fixtures/large.js';

const snapshot = JSON.parse(fs.readFileSync(new URL('../fixtures/default-snapshot.json', import.meta.url)));
function hierarchy(s = snapshot, scoped = false) {
  const executive = s.sessions.find((x) => x.id === s.executive_session_id);
  const h = groupedTree(scoped ? s.projects.slice(0, 1) : s.projects, executive,
    (p) => projectAncestry(s.sessions, p, s.executive_session_id), scoped);
  return { roots: h.roots, children: h.children, executiveId: s.executive_session_id };
}
const sizes = (h) => (s) => cardDimensions(s, {}, h.children.get(s.id)?.length,
  !!(s.attempt || s.resumption || s.provenance === 'imported' || s.id.includes('cycle') || s.id.includes('self')));
const fit = (width, h = hierarchy(), height = 900) => fitTree(h, sizes(h), width, height);

test('per-branch candidates use both viewport dimensions and preserve readable columns', () => {
  for (const [width, height] of [[1440, 900], [1100, 800], [800, 1000]]) {
    const l = fit(width, hierarchy(), height);
    const cards = [...l.positions.values()].filter((p) => !p.s.project);
    const columns = Math.max(...cards.map((p) => cards.filter((c) => c.y === p.y).length));
    assert.ok(columns >= 3, `${width}: ${columns} columns`);
    assert.ok(l.scale >= 0.75);
    assert.ok(l.width * l.scale <= width);
    cards.forEach((a, i) => cards.slice(i + 1).forEach((b) => assert.ok(!intersects(a, b))));
  }
  assert.equal(fit(120).scale, 0.5);
  const h = hierarchy();
  assert.notDeepEqual(fitTree(h, sizes(h), 1440, 300), fitTree(h, sizes(h), 1440, 3000));
});

test('a fitting tree maximises scale across both axes without unnecessary vertical scrolling', () => {
  const h = hierarchy(snapshot, true);
  const l = fit(1100, h, 800);
  assert.ok(l.scale >= 0.75);
  assert.ok(l.height * l.scale <= 800);
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
  assert.ok(l.scale >= 0.75);
  assert.ok(l.height > 900);
});

test('card defaults follow lifecycle and input, and overrides win', () => {
  for (const lifecycle of ['ended', 'retired', 'idle', 'host_offline']) {
    const s = { id: 's', lifecycle };
    assert.equal(cardIsExpanded(s), false);
    assert.deepEqual(cardDimensions(s), { w: 220, h: 44 });
    assert.equal(cardIsExpanded({ ...s, needs_operator_input: true }), true);
    assert.equal(cardIsExpanded(s, { s: true }), true);
  }
  assert.equal(cardIsExpanded({ id: 's', lifecycle: 'running' }), true);
  assert.equal(cardIsExpanded({ id: 's', lifecycle: 'running' }, { s: false }), false);
});

test('200 visible generated sessions lay out in under 50 ms', () => {
  const large = generateLargeSnapshot();
  const sample = { ...large, sessions: large.sessions.slice(0, 201) };
  const h = hierarchy(sample);
  fit(1100, h);
  const start = performance.now();
  const l = fit(1100, h);
  assert.equal(l.positions.size, 202);
  assert.ok(performance.now() - start < 50);
});

function assertRoutes(l, relationships, assignments = []) {
  const boxes = [...l.positions.values()];
  const check = (points, from, to) => {
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1];
      const b = points[i];
      assert.ok(a.x === b.x || a.y === b.y, 'orthogonal segment');
      for (const box of boxes) {
        if (box.s.id === from || box.s.id === to) continue;
        assert.ok(!segmentIntersects(a, b, box), `${from}>${to} crosses ${box.s.id}`);
      }
    }
  };
  l.edges.forEach((e) => check(e.points, e.from, e.to));
  const route = createRelationshipRouter(boxes, l.scale);
  relationships.forEach((r, i) => {
    const to = r.type === 'assignment_owner' ? assignments.find((a) => a.id === r.to)?.owner_session_id : r.to;
    if (r.type === 'run_association' || !l.positions.has(r.from) || !l.positions.has(to)) return;
    const line = route(l.positions.get(r.from), l.positions.get(to), r.type, i);
    check(line.points, r.from, to);
    // Only the final one-pixel port inset may enter an endpoint.
    for (const box of [l.positions.get(r.from), l.positions.get(to)]) {
      const inner = { x: box.x + 2, y: box.y + 2, w: box.w - 4, h: box.h - 4 };
      line.points.slice(1).forEach((p, j) => assert.ok(!segmentIntersects(line.points[j], p, inner)));
    }
    assert.ok(boxes.every((b) => !intersects(line.labelBox, b)));
  });
}

test('every default edge and relationship clears non-endpoint rectangles at all requested viewports', () => {
  for (const [w, h] of [[1440, 900], [1100, 800], [800, 1000]]) {
    for (const scoped of [false, true]) {
      const tree = hierarchy(snapshot, scoped);
      if (scoped) {
        const executive = snapshot.sessions.find((s) => s.id === snapshot.executive_session_id);
        tree.children.set(executive.id, tree.roots);
        tree.roots = [executive];
      }
      assertRoutes(fit(w, tree, h), snapshot.relationships, snapshot.assignments);
    }
  }
});

test('expanded large project routes around the visible compact and expanded cards', () => {
  const s = generateLargeSnapshot();
  const h = hierarchy(s);
  h.collapsed = new Set([...h.children.keys()].filter((id) => !id.startsWith('project:') && id !== s.executive_session_id));
  assertRoutes(fit(1100, h, 800), s.relationships, s.assignments);
});

test('gutter search detours around a wall and separates parallel relationship ports', () => {
  const wall = { x: 40, y: 0, w: 20, h: 80 };
  const route = routeOrthogonal({ x: 0, y: 40 }, { x: 100, y: 40 }, [wall]);
  assert.ok(route.some((p) => p.y <= -8 || p.y >= 88));
  route.slice(1).forEach((p, i) => assert.ok(!segmentIntersects(route[i], p, wall)));
  const a = { x: 0, y: 0, w: 20, h: 44 };
  const b = { x: 80, y: 100, w: 20, h: 44 };
  const one = routeRelationship(a, b, [a, b], 'reviews', 1, 0);
  const two = routeRelationship(a, b, [a, b], 'reviews', 1, 1);
  assert.notDeepEqual(one.points, two.points);
});

test('shared routing queries keep all 100 generated relationships clear across 200 visible sessions', () => {
  const large = generateLargeSnapshot({ ...LARGE_SPEC, sessions: 200 });
  const h = hierarchy(large);
  assertRoutes(fit(1100, h, 800), large.relationships, large.assignments);
});
