import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { ancestryLabel, groupedTree, projectAncestry, projectNodeId } from '../src/ancestry.js';
import { generateLargeSnapshot } from '../src/fixtures/large.js';

const snapshot = JSON.parse(fs.readFileSync(new URL('../fixtures/default-snapshot.json', import.meta.url)));
const ancestry = (pid) => projectAncestry(snapshot.sessions, pid, snapshot.executive_session_id);

test('only the executive can start sessions across project boundaries', () => {
  const list = [
    { id: 'exec', project_id: null },
    { id: 'owner', project_id: 'a', parent_session_id: 'exec' },
    { id: 'cross', project_id: 'b', parent_session_id: 'owner' },
    { id: 'child', project_id: 'b', parent_session_id: 'cross' },
  ];
  const a = projectAncestry(list, 'a', 'exec');
  assert.deepEqual([...a.outside], []);
  assert.deepEqual(a.roots.map((s) => s.id), ['owner']);
  const b = projectAncestry(list, 'b', 'exec');
  assert.deepEqual([...b.crossProject], ['cross']);
  assert.equal(ancestryLabel(list[2], b), 'Parent in another project');
  assert.deepEqual(b.roots.map((s) => s.id), ['cross']);
  assert.equal(b.parentOf.get('child'), 'cross');
  assert.equal(b.parentOf.has('cross'), false);
});

test('malformed ancestry stays labelled and its valid descendants stay attached', () => {
  const a = ancestry('proj-malformed');
  assert.deepEqual([...a.cycle].sort(), ['ses-mal-cycle-a', 'ses-mal-cycle-b', 'ses-mal-self']);
  assert.equal(a.parentOf.get('ses-mal-cycle-child'), 'ses-mal-cycle-a');
  assert.deepEqual([...ancestry('proj-contract-pins').outside], ['ses-pin-audit']);
  assert(ancestry('proj-odin-webapp').roots.some((s) => s.id === 'ses-imported-01'));
});

test('group rows preserve project order and never enter session ancestry', () => {
  const executive = snapshot.sessions.find((s) => s.id === snapshot.executive_session_id);
  const tree = groupedTree(snapshot.projects, executive, ancestry);
  assert.deepEqual(tree.roots, [executive]);
  assert.deepEqual(tree.children.get(executive.id).map((s) => s.project), snapshot.projects);
  for (const p of snapshot.projects) assert.deepEqual(tree.children.get(projectNodeId(p.id)), ancestry(p.id).roots);
  const scoped = groupedTree([snapshot.projects[0]], executive, ancestry, true);
  assert.equal(scoped.roots[0].project, snapshot.projects[0]);
  assert.equal(scoped.children.has(executive.id), false);
});

test('large snapshot is deterministic with one executive and forty recorded starts', () => {
  const s = generateLargeSnapshot();
  assert.deepEqual(s, generateLargeSnapshot());
  assert.equal(s.sessions.length, 2001);
  assert.equal(s.sessions.filter((x) => x.project_id === null).length, 1);
  assert.equal(s.sessions.filter((x) => x.parent_session_id === s.executive_session_id).length, 40);
  const a = projectAncestry(s.sessions, s.projects[0].id, s.executive_session_id);
  assert.equal(a.roots.length, 40);
  assert.equal(a.outside.size, 0);
});

test('an unavailable executive is not an admitted ancestry parent', () => {
  const s = { id: 's', project_id: 'a', parent_session_id: 'missing' };
  const a = projectAncestry([s], 'a', 'missing');
  assert.equal(ancestryLabel(s, a), 'Parent not in this project view');
});
