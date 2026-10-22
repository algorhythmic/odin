// SYNTHETIC, seeded, generated at load time so no multi-MB fixture is committed.
// Same seed and spec always produce identical output. Not real sessions.
// Used by the browser (Vite) and by web/scripts/describe-large.mjs under Node.

export const LARGE_SEED = 20261022;
export const LARGE_SPEC = { sessions: 2000, roots: 40, maxDepth: 8, transcriptPages: 20, pageSize: 50, projectId: 'proj-large-synthetic' };

const LIFECYCLES = ['running', 'waiting_for_input', 'idle', 'ended', 'retired', 'host_offline'];
const PROGRESS = ['in_progress', 'blocked', 'awaiting_review', 'done_unverified', 'accepted'];
const ROLES = ['executive', 'integration owner', 'worker', 'reviewer'];
const MODELS = ['claude-opus-5-5', 'claude-haiku-5-5', 'claude-sonnet-5-5', null];
const DAY_START = Date.UTC(2026, 9, 21);

// mulberry32: small seeded PRNG. Never Math.random.
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const pick = (rnd, list) => list[Math.floor(rnd() * list.length)];
const padId = (prefix, i) => `${prefix}-${String(i).padStart(4, '0')}`;

// ISO timestamp on 2026-10-21 (UTC), whole seconds.
function isoOnDay(rnd) {
  const s = Math.floor(rnd() * 86400);
  return new Date(DAY_START + s * 1000).toISOString().slice(0, 19) + 'Z';
}

export function generateLargeSnapshot(spec = LARGE_SPEC, seed = LARGE_SEED) {
  if (spec.roots < 1 || spec.maxDepth < 2 || spec.sessions < spec.roots + spec.maxDepth - 1) {
    throw new RangeError('LARGE_SPEC cannot reach maxDepth with the given roots and sessions');
  }
  const rnd = mulberry32(seed);
  const pid = spec.projectId;
  const sessions = [];
  const assignments = [];
  const depth = [];
  const eligible = []; // indices whose depth is below maxDepth, so a child may attach

  for (let i = 0; i < spec.sessions; i += 1) {
    let parentIdx = null;
    if (i >= spec.roots) {
      // A fixed spine (roots..roots+maxDepth-2) guarantees one chain at maxDepth;
      // every other non-root attaches to a node that keeps the depth within maxDepth.
      parentIdx = i < spec.roots + spec.maxDepth - 1 ? (i === spec.roots ? 0 : i - 1) : pick(rnd, eligible);
    }
    depth[i] = parentIdx === null ? 1 : depth[parentIdx] + 1;
    if (depth[i] < spec.maxDepth) eligible.push(i);

    const sid = padId('ses-L', i);
    const asgId = padId('asg-L', i);
    const lifecycle = pick(rnd, LIFECYCLES);
    const progress = pick(rnd, PROGRESS);
    const r = rnd();
    const cost = r < 0.15
      ? { amount_usd: null, basis: 'unknown' }
      : { amount_usd: Math.round(rnd() * 10000) / 100, basis: r < 0.4 ? 'estimate' : 'measured' };

    sessions.push({
      id: sid,
      project_id: pid,
      parent_session_id: parentIdx === null ? null : padId('ses-L', parentIdx),
      provenance: 'recorded',
      role: pick(rnd, ROLES),
      assignment_id: asgId,
      model: pick(rnd, MODELS),
      lifecycle,
      needs_operator_input: lifecycle === 'waiting_for_input' && rnd() < 0.5,
      observed_at: isoOnDay(rnd),
      stale: lifecycle === 'host_offline',
      cost,
      elapsed_s: Math.floor(rnd() * 20000),
      budget: null,
    });

    const asg = { id: asgId, project_id: pid, commitment_id: 'cmt-L', owner_session_id: sid, summary: `Synthetic assignment ${i}`, progress };
    if (progress === 'blocked') asg.blocked_reason = 'Synthetic block';
    assignments.push(asg);
  }

  const relationships = [];
  for (let n = 0; n < 100; n += 1) {
    const from = Math.floor(rnd() * spec.sessions);
    // Offset of 1..sessions-1 guarantees to !== from.
    const to = (from + 1 + Math.floor(rnd() * (spec.sessions - 1))) % spec.sessions;
    relationships.push({ id: `rel-L-${n}`, type: 'review', from: padId('ses-L', from), to: padId('ses-L', to) });
  }

  return {
    schema: 'odin.web.projection.snapshot/v0-draft',
    synthetic: true,
    dataset: 'large',
    revision: 0,
    cursor: 'cur-large-0000',
    generated_at: '2026-10-21T10:45:00Z',
    projects: [{
      id: pid,
      name: 'Large synthetic tree (generated)',
      summary: 'Seeded generated dataset for timing; not real sessions.',
      host: 'workstation-a (synthetic)',
    }],
    commitments: [{ id: 'cmt-L', project_id: pid, title: 'Large synthetic commitment', status: 'in_progress', owner: 'ses-L-0000' }],
    assignments,
    runs: [],
    sessions,
    relationships,
    decisions: [],
    conversations: { [pid]: [] },
    activity: { [pid]: [] },
  };
}

// Deterministic per (sessionId, page). Pages outside 1..pages return no entries.
export function loadLargeTranscriptPage(sessionId, page, spec = LARGE_SPEC, seed = LARGE_SEED) {
  if (!Number.isInteger(page) || page < 1 || page > spec.transcriptPages) {
    return { page, pages: spec.transcriptPages, entries: [] };
  }
  let h = seed ^ page;
  for (const ch of sessionId) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  const rnd = mulberry32(h);
  const entries = [];
  for (let i = 0; i < spec.pageSize; i += 1) {
    const seq = (page - 1) * spec.pageSize + i + 1;
    entries.push({ seq, at: isoOnDay(rnd), speaker: sessionId, text: `Synthetic note ${seq} for ${sessionId}.` });
  }
  return { page, pages: spec.transcriptPages, entries };
}

export function describeLarge(snapshot) {
  const byId = new Map(snapshot.sessions.map((s) => [s.id, s]));
  let maxDepth = 0;
  for (const s of snapshot.sessions) {
    // Walk up to a root; the seen set stops cycles.
    const seen = new Set([s.id]);
    let d = 1;
    for (let p = s.parent_session_id; p && byId.has(p) && !seen.has(p); p = byId.get(p).parent_session_id) {
      seen.add(p);
      d += 1;
    }
    maxDepth = Math.max(maxDepth, d);
  }
  return {
    sessions: snapshot.sessions.length,
    roots: snapshot.sessions.filter((s) => s.parent_session_id === null).length,
    maxDepth,
    projects: snapshot.projects.length,
    unknownCost: snapshot.sessions.filter((s) => s.cost.basis === 'unknown').length,
    reviewRelationships: snapshot.relationships.filter((r) => r.type === 'review').length,
    transcriptPagesPerSession: LARGE_SPEC.transcriptPages,
    pageSize: LARGE_SPEC.pageSize,
    seed: LARGE_SEED,
  };
}
