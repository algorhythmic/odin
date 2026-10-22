// Read-only views over the synthetic projection. The browser holds no
// authoritative records: it keeps one snapshot, applies update events to it
// and re-derives every view. A service projection would replace the source.
import { useEffect, useState } from 'preact/hooks';
import * as fx from './fixtures/synthetic.js';
import { reduceEvent } from './events.js';

export const isSynthetic = fx.synthetic === true;
export const datasetName = new URLSearchParams(location.search).get('dataset') === 'large' ? 'large' : 'default';

const loaded = fx.loadDataset(datasetName);
let snap = loaded.snapshot;
const queue = loaded.events;
const seenEvents = new Set();
const listeners = new Set();
let version = 0;
let index = null;
let lastResult = null;
performance.mark('odin:data-ready');

export const loadSessionDetail = (session, page) => fx.loadSessionDetail(datasetName, session, page);

function bump() {
  version += 1;
  for (const fn of listeners) fn(version);
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// Re-renders the caller whenever an update event changes the records.
export function useDataVersion() {
  const [v, setV] = useState(version);
  useEffect(() => subscribe(setV), []);
  return v;
}

function ix() {
  if (index && index.version === version) return index;
  const byProject = new Map();
  for (const s of snap.sessions) {
    if (!byProject.has(s.project_id)) byProject.set(s.project_id, []);
    byProject.get(s.project_id).push(s);
  }
  index = {
    version, byProject, ancestry: new Map(),
    sessions: new Map(snap.sessions.map((s) => [s.id, s])),
    assignments: new Map(snap.assignments.map((a) => [a.id, a])),
    // Session ids a later attempt names as its previous_attempt: the
    // superseded attempt stays in records but is drawn dimmed.
    superseded: new Set(snap.sessions.filter((s) => s.previous_attempt).map((s) => s.previous_attempt)),
  };
  return index;
}

export const LIFECYCLE_LABELS = {
  running: 'Running',
  waiting_for_input: 'Needs you',
  idle: 'Idle',
  ended: 'Done',
  retired: 'Stopped',
  host_offline: 'Host offline',
};

// The card status set. Colour and icon are presentation; the label is
// always shown as text too. `idle` and `host_offline` are recorded
// lifecycles the reference status set does not cover: they keep their
// precise labels with neutral and attention styling respectively.
export const SESSION_STATUS = {
  running: { key: 'running', icon: 'spinner' },
  waiting_for_input: { key: 'needs-you', icon: 'clock' },
  idle: { key: 'idle', icon: 'pause' },
  ended: { key: 'done', icon: 'check' },
  failed: { key: 'failed', icon: 'triangle' },
  retired: { key: 'stopped', icon: 'square' },
  host_offline: { key: 'host-offline', icon: 'offline' },
};

// The status a session's card and row show. An ended session whose run
// is recorded as failed reads "Failed"; "ended" alone reads "Done". An
// unknown lifecycle is labelled, never guessed.
export function sessionStatus(s) {
  if (s.lifecycle === 'ended' && runsForSession(s.id).some((r) => r.outcome === 'failed')) {
    return { ...SESSION_STATUS.failed, label: 'Failed' };
  }
  const st = SESSION_STATUS[s.lifecycle];
  return st ? { ...st, label: LIFECYCLE_LABELS[s.lifecycle] } : { key: 'unknown', icon: 'question', label: `Unknown state (${s.lifecycle})` };
}

// True when a later attempt names this session as its previous_attempt.
export const isSuperseded = (s) => ix().superseded.has(s.id);

export const PROGRESS_LABELS = {
  in_progress: 'In progress',
  blocked: 'Blocked',
  awaiting_review: 'Awaiting review',
  done_unverified: 'Reported done (not verified)',
  accepted: 'Accepted',
  unknown: 'Unknown',
};

export const OUTCOME_LABELS = {
  unverified: 'Not verified',
  verified: 'Verified',
  failed: 'Failed',
  unknown: 'Outcome unknown',
};

export const RELATION_LABELS = {
  review: 'reviews',
  delegation: 'delegated to',
  run_association: 'associated run',
  assignment_owner: 'owns assignment',
};

export const lifecycleLabel = (s) => LIFECYCLE_LABELS[s] || `Unknown state (${s})`;

export const getProjects = () => snap.projects;
export const getProject = (id) => snap.projects.find((p) => p.id === id) || null;
export const sessionsFor = (pid) => ix().byProject.get(pid) || [];
export const getSession = (id) => ix().sessions.get(id) || null;
export const getAssignment = (id) => ix().assignments.get(id) || null;
export const getRun = (id) => snap.runs.find((r) => r.id === id) || null;
export const runsForSession = (sid) => snap.runs.filter((r) => r.session_id === sid);
export const commitmentsFor = (pid) => snap.commitments.filter((c) => c.project_id === pid);
export const decisionsFor = (pid) => snap.decisions.filter((d) => d.project_id === pid);
export const conversationFor = (pid) => snap.conversations[pid] || [];
export const activityFor = (pid) => [...(snap.activity[pid] || [])].sort((a, b) => b.at.localeCompare(a.at));
export const relationshipsFor = (pid) => {
  const ids = new Set(sessionsFor(pid).map((s) => s.id));
  return snap.relationships.filter((r) => ids.has(r.from) || ids.has(r.to));
};
export const relationshipsOf = (id) => snap.relationships.filter((r) => r.from === id || r.to === id);

// The ancestry forest of one project, derived from parent_session_id only.
// Malformed records are reported, never repaired: a session whose recorded
// parent is outside the project, or whose parent chain loops back on itself
// (including a session naming itself), becomes a labelled root. No edge is
// guessed and no session is dropped. Non-cycle descendants of a cycle
// member still attach to it.
export function ancestry(pid) {
  const cache = ix().ancestry;
  if (cache.has(pid)) return cache.get(pid);
  const list = sessionsFor(pid);
  const inProject = new Map(list.map((s) => [s.id, s]));
  const outside = new Set(list.filter((s) => s.parent_session_id && !inProject.has(s.parent_session_id)).map((s) => s.id));
  const cycle = new Set();
  const state = new Map(); // 1: on the current walk, 2: finished
  for (const s of list) {
    const path = [];
    let cur = s;
    while (cur && !state.has(cur.id)) {
      state.set(cur.id, 1);
      path.push(cur.id);
      cur = cur.parent_session_id ? inProject.get(cur.parent_session_id) : null;
    }
    if (cur && state.get(cur.id) === 1) {
      for (const id of path.slice(path.indexOf(cur.id))) cycle.add(id);
    }
    for (const id of path) state.set(id, 2);
  }
  const children = new Map();
  const parentOf = new Map();
  const roots = [];
  for (const s of list) {
    if (!s.parent_session_id || outside.has(s.id) || cycle.has(s.id)) roots.push(s);
    else {
      if (!children.has(s.parent_session_id)) children.set(s.parent_session_id, []);
      children.get(s.parent_session_id).push(s);
      parentOf.set(s.id, s.parent_session_id);
    }
  }
  const result = { roots, children, parentOf, outside, cycle };
  cache.set(pid, result);
  return result;
}

export const parentOutsideProject = (s) => ancestry(s.project_id).outside.has(s.id);
export const inParentCycle = (s) => ancestry(s.project_id).cycle.has(s.id);
// The parent drawn in the tree, or null for any kind of root.
export const treeParent = (s) => getSession(ancestry(s.project_id).parentOf.get(s.id)) || null;
export const childrenMap = (pid) => ancestry(pid).children;
export const rootsFor = (pid) => ancestry(pid).roots;

// Tree ancestors, nearest first. The forest is acyclic by construction.
export function ancestors(s) {
  const { parentOf } = ancestry(s.project_id);
  const out = [];
  for (let p = parentOf.get(s.id); p; p = parentOf.get(p)) out.push(p);
  return out;
}

export function descendants(id, children) {
  const out = [];
  const seen = new Set([id]);
  const stack = [...(children.get(id) || [])];
  while (stack.length) {
    const s = stack.pop();
    if (seen.has(s.id)) continue;
    seen.add(s.id);
    out.push(s);
    stack.push(...(children.get(s.id) || []));
  }
  return out;
}

// Compact token counts: 850 tok, 48.2k tok, 1.2M tok.
export function compactTokens(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return `${n}`;
}

// The headline figure: uncached input + cache write + output. Cache reads
// are EXCLUDED (they dominate long sessions; the detail panel shows the
// split). Returns null when the session's tokens are unknown: all four
// counters are integers or the record reports them as unknown — anything
// half-known is reported as unknown, never as a partial sum or zero.
export function headlineTokens(tokens) {
  if (!tokens || tokens.basis === 'unknown') return null;
  const counts = [tokens.uncached_input, tokens.cache_read, tokens.cache_write, tokens.output];
  if (!counts.every(Number.isInteger)) return null;
  return { value: counts[0] + counts[2] + counts[3], estimate: tokens.basis === 'estimate' };
}

export function formatTokens(tokens) {
  const h = headlineTokens(tokens);
  if (!h) return 'unknown';
  return `${h.estimate ? 'est. ' : ''}${compactTokens(h.value)} tok`;
}

// Sums each session's OWN headline tokens once. Unknown stays visible;
// estimates are marked.
function tokenSum(list) {
  let known = 0;
  let knownCount = 0;
  let unknown = 0;
  let estimate = false;
  for (const s of list) {
    const h = headlineTokens(s.tokens);
    if (!h) unknown += 1;
    else {
      known += h.value;
      knownCount += 1;
      estimate = estimate || h.estimate;
    }
  }
  // With no known tokens there is no figure to show; unknown is never zero.
  if (!knownCount) return `unknown (${unknown})`;
  let text = `${estimate ? 'est. ' : ''}${compactTokens(known)} tok`;
  if (unknown) text += ` + unknown (${unknown})`;
  return text;
}

export function branchTokens(session, children) {
  return tokenSum([session, ...descendants(session.id, children)]);
}

// The project's header total: every session's own tokens summed once.
export const projectTokens = (pid) => tokenSum(sessionsFor(pid));

export function formatElapsed(seconds) {
  if (seconds == null) return 'elapsed unknown';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`;
}

export function lineageLabel(s) {
  if (s.provenance === 'imported' && !s.parent_session_id) return 'Imported — parent unknown';
  if (inParentCycle(s)) return 'Parent cycle in records';
  if (parentOutsideProject(s)) return 'Parent not in this project view';
  if (s.attempt) return `Attempt ${s.attempt}${s.previous_attempt ? ` (after ${s.previous_attempt})` : ''}`;
  if (s.resumption) return `Resumed ×${s.resumption.count} (same session)`;
  return null;
}

export function attentionItems() {
  const items = [];
  for (const d of snap.decisions.filter((x) => x.status === 'pending')) {
    items.push({ key: d.id, kind: d.kind === 'approval' ? 'Pending approval' : 'Pending decision',
      text: d.title, project_id: d.project_id, session_id: d.requested_by });
  }
  for (const s of snap.sessions) {
    if (s.needs_operator_input) items.push({ key: `in-${s.id}`, kind: 'Needs input', text: `${s.role}: ${getAssignment(s.assignment_id)?.summary || ''}`, project_id: s.project_id, session_id: s.id });
    if (s.lifecycle === 'host_offline') items.push({ key: `off-${s.id}`, kind: 'Host offline', text: `${s.role} last observed ${observedLabel(s.observed_at)}`, project_id: s.project_id, session_id: s.id });
  }
  for (const a of snap.assignments.filter((x) => x.progress === 'blocked')) {
    const owner = snap.sessions.find((s) => s.assignment_id === a.id);
    items.push({ key: `blk-${a.id}`, kind: 'Blocked', text: `${a.summary}: ${a.blocked_reason}`, project_id: a.project_id, session_id: owner?.id });
  }
  return items;
}

export const activeWork = () => snap.sessions.filter((s) => ['running', 'waiting_for_input'].includes(s.lifecycle));

// "HH:MM UTC" for a recorded observation time; the raw value if unparsable.
export function observedLabel(at) {
  const m = /T(\d{2}:\d{2})/.exec(at || '');
  return m ? `${m[1]} UTC` : (at || 'unknown');
}

// --- Synthetic update driver -------------------------------------------
// Applies projection update events to the loaded snapshot; the rules live in
// events.js so they can be tested without a browser.

export function applyEvent(evt) {
  const { result, snapshot } = reduceEvent(snap, seenEvents, evt);
  if (result.status === 'applied') {
    snap = snapshot;
    seenEvents.add(evt.event_id);
    index = null;
    bump();
  }
  return result;
}

export const driverState = () => ({
  revision: snap.revision, cursor: snap.cursor, pending: queue.length, last: lastResult,
});

// Applies the next queued synthetic event and reports what happened.
export function applyNextSyntheticEvent() {
  const evt = queue.shift();
  if (!evt) return null;
  lastResult = applyEvent(evt);
  if (lastResult.status !== 'applied') bump();
  return lastResult;
}
