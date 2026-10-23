import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { ancestryLabel, groupedTree, projectAncestry, projectNodeId, restoredNodeId, storedNodeId } from '../src/ancestry.js';
import { cardDimensions } from '../src/card-size.js';
import { reduceEvent } from '../src/events.js';
import { flattenRows, replacementRow } from '../src/list-rows.js';
import { visibleSessions } from '../src/simulation.js';
import { createRelationshipRouter, fitTree, intersects } from '../src/tree-layout.js';

const read = (file) => JSON.parse(fs.readFileSync(new URL(`../fixtures/${file}`, import.meta.url)));
const fixture = read('default-snapshot.json');
function layout(snapshot, width = 732, height = 792) {
  const sessions = visibleSessions(snapshot.sessions);
  const ancestry = (pid) => projectAncestry(sessions, pid, snapshot.executive_session_id);
  const tree = groupedTree(snapshot.projects, sessions.find((s) => s.id === snapshot.executive_session_id), ancestry);
  const size = (s) => cardDimensions(s, {}, tree.children.get(s.id)?.length,
    !s.project && !!ancestryLabel(s, ancestry(s.project_id)),
    snapshot.relationships.some((r) => r.from === s.id && r.type === 'run_association'));
  return fitTree({ ...tree, executiveId: snapshot.executive_session_id }, size, width, height);
}
function overlays(snapshot, positions, leaving, scale) {
  const route = createRelationshipRouter([...positions.values()], scale, leaving);
  return snapshot.relationships.flatMap((r, i) => {
    if (r.type === 'run_association') return [];
    const target = r.type === 'assignment_owner'
      ? snapshot.assignments.find((a) => a.id === r.to)?.owner_session_id : r.to;
    const line = route(positions.get(r.from), positions.get(target), r.type, i);
    return line ? [{ ...line, id: r.id, from: r.from, target }] : [];
  });
}

test('1100×900 retirement replay routes all relationships around current cards only', () => {
  // Also replay the measured 732×792 canvas inside the reviewer's 1100×900 window.
  for (const [width, height] of [[1100, 900], [732, 792]]) {
    let snapshot = structuredClone(fixture);
    let before = layout(snapshot, width, height);
    const seen = new Set();
    for (const event of read('default-events.json').events.slice(0, 5)) {
      const result = reduceEvent(snapshot, seen, event);
      snapshot = result.snapshot;
      if (result.result.status === 'applied') seen.add(event.event_id);
      const current = layout(snapshot, width, height);
      const leaving = new Set([...before.positions.keys()].filter((id) => !current.positions.has(id)));
      const combined = new Map([...before.positions].filter(([id]) => leaving.has(id)).concat([...current.positions]));
      const lines = overlays(snapshot, combined, leaving, current.scale);
      assert.deepEqual(lines, overlays(snapshot, current.positions, new Set(), current.scale));
      assert.ok(lines.length > 0);
      for (const line of lines) {
        assert.ok(!leaving.has(line.from) && !leaving.has(line.target));
        assert.ok([...current.positions.values()].every((box) => !intersects(line.labelBox, box)));
      }
      before = current;
    }
    assert.equal(snapshot.sessions.find((s) => s.id === 'ses-review-integ').lifecycle, 'retired');
  }
});

test('seeded random retirements never throw or route to leaving sessions', () => {
  let seed = 20261022;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32);
  for (let n = 0; n < 100; n++) {
    const snapshot = structuredClone(fixture);
    const before = layout(snapshot);
    snapshot.sessions = snapshot.sessions.map((s) => s.project_id && random() < 0.5 ? { ...s, lifecycle: 'retired' } : s);
    const current = layout(snapshot, 500 + random() * 1400, 400 + random() * 700);
    const leaving = new Set([...before.positions.keys()].filter((id) => !current.positions.has(id)));
    const combined = new Map([...before.positions].filter(([id]) => leaving.has(id)).concat([...current.positions]));
    const lines = overlays(snapshot, combined, leaving, current.scale);
    assert.deepEqual(lines, overlays(snapshot, current.positions, new Set(), current.scale));
    assert.ok(lines.every((r) => !leaving.has(r.from) && !leaving.has(r.target)));
  }
});

test('an impossible route returns no line; leaving overlaps are not obstacles or endpoints', () => {
  const a = { x: 0, y: 0, w: 100, h: 100, s: { id: 'a' } };
  const b = { x: 0, y: 200, w: 100, h: 100, s: { id: 'b' } };
  const exit = { x: -10, y: -10, w: 200, h: 200, s: { id: 'exit' } };
  assert.equal(createRelationshipRouter([a, b, exit], 1)(a, b, 'reviews'), null);
  const route = createRelationshipRouter([a, b, exit], 1, new Set(['exit']));
  assert.ok(route(a, b, 'reviews'));
  assert.equal(route(exit, b, 'reviews'), null);
  assert.equal(route(a, undefined, 'reviews'), null);
});

test('project grouping and collision sessions have distinct keys in tree and list layouts', () => {
  const snapshot = structuredClone(fixture);
  const id = 'project:proj-odin-webapp';
  snapshot.sessions.push({ ...snapshot.sessions.find((s) => s.id === 'ses-docs-01'),
    id, parent_session_id: snapshot.executive_session_id });
  const ancestry = (pid) => projectAncestry(snapshot.sessions, pid, snapshot.executive_session_id);
  const tree = groupedTree(snapshot.projects, snapshot.sessions.find((s) => s.id === snapshot.executive_session_id), ancestry);
  assert.notEqual(projectNodeId('proj-odin-webapp'), id);
  assert.ok(layout(snapshot).positions.has(id));
  const rows = flattenRows(tree.roots, tree.children, new Set());
  assert.equal(rows.length, snapshot.sessions.length + snapshot.projects.length);
  assert.equal(rows.filter((r) => r.s.id === id).length, 1);
  assert.equal(rows.find((r) => r.s.id === id).parent, projectNodeId('proj-odin-webapp'));
  for (const key of [id, projectNodeId('proj-odin-webapp'), '["project","project:p"]']) {
    assert.equal(restoredNodeId(storedNodeId(key)), key);
  }
  assert.equal(flattenRows(tree.roots, tree.children, new Set([id])).length, rows.length);
  assert.ok(flattenRows(tree.roots, tree.children, new Set([projectNodeId('proj-odin-webapp')])).length < rows.length);
});

test('removed row focus chooses next, previous, then the tree', () => {
  const rows = ['a', 'b', 'c'].map((id) => ({ s: { id } }));
  assert.equal(replacementRow(rows, [rows[0], rows[2]], 'b'), 'c');
  assert.equal(replacementRow(rows, [rows[0]], 'c'), 'a');
  assert.equal(replacementRow(rows, [], 'b'), null);
});

test('compact geometry reserves room for each required qualification', () => {
  const s = { id: 's', lifecycle: 'idle' };
  assert.equal(cardDimensions({ ...s, stale: true }).h, 66);
  assert.equal(cardDimensions({ ...s, lifecycle: 'host_offline' }).h, 66);
  assert.equal(cardDimensions(s, {}, false, true).h, 62);
  assert.equal(cardDimensions({ ...s, lifecycle: 'retired' }, {}, true).h, 62);
  assert.equal(cardDimensions({ ...s, stale: true, lifecycle: 'retired' }, {}, true, true).h, 102);
});
