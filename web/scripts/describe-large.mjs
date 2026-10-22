// Node check for the seeded large fixture: determinism, shape counts, and a digest.
// Run from web/: node scripts/describe-large.mjs
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { describeLarge, generateLargeSnapshot } from '../src/fixtures/large.js';

const first = JSON.stringify(generateLargeSnapshot());
const second = JSON.stringify(generateLargeSnapshot());
assert.equal(first, second, 'same seed must produce identical output');

const snapshot = JSON.parse(first);
const summary = describeLarge(snapshot);
assert.equal(summary.sessions, 2000, 'session count');
assert.equal(summary.roots, 40, 'root count');
assert.equal(summary.maxDepth, 8, 'maximum depth');

console.log(JSON.stringify(summary, null, 2));
console.log(`sha256 ${createHash('sha256').update(JSON.stringify(snapshot)).digest('hex')}`);
