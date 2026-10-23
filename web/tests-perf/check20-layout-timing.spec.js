// Pure layout timing on 200 visible sessions from the seeded synthetic dataset.
import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import { fitTree } from '../src/tree-layout.js';
import { cardDimensions } from '../src/card-size.js';
import { groupedTree, projectAncestry } from '../src/ancestry.js';
import { generateLargeSnapshot, LARGE_SPEC } from '../src/fixtures/large.js';

test('200 visible synthetic sessions: adaptive layout stays under 50 ms', () => {
  const s = generateLargeSnapshot({ ...LARGE_SPEC, sessions: 200 });
  const h = groupedTree(s.projects, s.sessions[0],
    (p) => projectAncestry(s.sessions, p, s.executive_session_id), false);
  const input = { ...h, executiveId: s.executive_session_id };
  const size = (node) => cardDimensions(node, {}, h.children.get(node.id)?.length, true);
  fitTree(input, size, 1100, 800);
  const samples = [];
  for (let i = 0; i < 8; i++) {
    const t = performance.now();
    const result = fitTree(input, size, 1100, 800);
    samples.push(performance.now() - t);
    expect(result.positions.size).toBe(202);
  }
  const result = { label: 'synthetic prototype, pure adaptive layout; 200 visible project sessions plus executive',
    target_ms: 50, samples_ms: samples, max_ms: Math.max(...samples) };
  const dir = process.env.EVIDENCE_DIR || 'test-results/perf';
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'adaptive-layout-200.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result));
  expect(result.max_ms).toBeLessThan(50);
});
