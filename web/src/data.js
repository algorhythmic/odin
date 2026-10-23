// Read-only views over the synthetic projection. The browser holds no
// authoritative records: it keeps one snapshot, applies update events to it
// and re-derives every view. A service projection would replace the source.
import { useEffect, useState } from 'preact/hooks';
import { tokenSum, formatTokenSum } from './tokens.js';
export { compactTokens, headlineTokens, formatTokens, tokenSum, formatTokenSum } from './tokens.js';
import * as fx from './fixtures/synthetic.js';
import { ancestryLabel, groupedTree, projectAncestry } from './ancestry.js';
import { createSyntheticStore } from './synthetic-store.js';
import {
  attentionCounts, cleanSpeed, displayedElapsed, failedSessionIds, intervalFor, observeElapsed, simulationSummary,
} from './live.js';
import { createSimulation, DEFAULT_SEED, liveSessions, visibleSessions } from './simulation.js';

export const isSynthetic = fx.synthetic === true;
const params = new URLSearchParams(location.search);
export const datasetName = params.get('setup') === 'fresh' ? 'empty' : params.get('dataset') === 'large' ? 'large' : 'default';

const loaded = fx.loadDataset(datasetName);
let snap = loaded.snapshot;
const store = createSyntheticStore(snap);
const queue = loaded.events;
const simulation = datasetName === 'default'
  ? createSimulation(new URLSearchParams(location.search).get('seed') ?? DEFAULT_SEED) : null;
const listeners = new Set();
let version = 0;
let dataVersion = 0;
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
  if (index && index.version === dataVersion) return index;
  const byProject = new Map();
  for (const s of snap.sessions) {
    if (!byProject.has(s.project_id)) byProject.set(s.project_id, []);
    byProject.get(s.project_id).push(s);
  }
  const runs = new Map();
  for (const r of snap.runs) {
    if (!runs.has(r.session_id)) runs.set(r.session_id, []);
    runs.get(r.session_id).push(r);
  }
  index = {
    version: dataVersion, byProject, runs, ancestry: new Map(), liveAncestry: new Map(), grouped: new Map(),
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

export const getSnapshot = () => snap;
export const historyTrimmed = (pid) => store.historyTrimmed(pid);
export const getProjects = () => snap.projects;
export const getExecutive = () => {
  const session = getSession(snap.executive_session_id);
  return session?.project_id === null ? session : null;
};
export const getProject = (id) => snap.projects.find((p) => p.id === id) || null;
export const sessionsFor = (pid) => pid === undefined ? snap.sessions : ix().byProject.get(pid) || [];
export const liveSessionsFor = (pid) => liveSessions(sessionsFor(pid));
export const getSession = (id) => ix().sessions.get(id) || null;
export const getAssignment = (id) => ix().assignments.get(id) || null;
export const getRun = (id) => snap.runs.find((r) => r.id === id) || null;
export const runsForSession = (sid) => ix().runs.get(sid) || [];
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
  const result = projectAncestry(snap.sessions, pid, snap.executive_session_id);
  cache.set(pid, result);
  return result;
}

function liveAncestry(pid) {
  const cache = ix().liveAncestry;
  if (!cache.has(pid)) cache.set(pid, projectAncestry(visibleSessions(snap.sessions), pid, snap.executive_session_id));
  return cache.get(pid);
}

export const parentOutsideProject = (s) => ancestry(s.project_id).outside.has(s.id);
export const inParentCycle = (s) => ancestry(s.project_id).cycle.has(s.id);
// The parent drawn in the tree, or null for any kind of root.
export function treeParent(s) {
  if (s.id === snap.executive_session_id) return null;
  if (s.parent_session_id === snap.executive_session_id) return getExecutive();
  return getSession(ancestry(s.project_id).parentOf.get(s.id)) || null;
}
export const childrenMap = (pid) => ancestry(pid).children;
export const rootsFor = (pid) => ancestry(pid).roots;

// Tree ancestors, nearest first. The forest is acyclic by construction.
export function ancestors(s) {
  const out = [];
  for (let p = treeParent(s); p; p = treeParent(p)) out.push(p.id);
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

export const branchSum = (session, children) => {
  // Group rows carry no usage. The executive totals only its admitted descendants.
  if (session.id === snap.executive_session_id) {
    return tokenSum([session, ...snap.sessions.filter((s) => s.id !== session.id && ancestors(s).includes(session.id))]);
  }
  return tokenSum([session, ...descendants(session.id, children)].filter((s) => !s.project));
};
export function branchTokens(session, children) {
  return formatTokenSum(branchSum(session, children));
}

// The project's header total: every session's own tokens summed once.
export const projectSum = (pid) => tokenSum(sessionsFor(pid));
export const projectTokens = (pid) => formatTokenSum(projectSum(pid));

export function formatElapsed(seconds) {
  if (seconds == null) return 'elapsed unknown';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`;
}

// Seconds added to a running session's displayed elapsed while the
// synthetic player runs. Ticks never rewrite the recorded elapsed_s.
// Each session's baseline is the player tick at which its
// (lifecycle, elapsed_s, observed_at) baseline was first seen this playback (live.js
// holds the rule), so a session that starts running mid-play counts only
// the ticks since it appeared, not every tick since play began.
let elapsedTick = 0;
const elapsedBaselines = new Map();
observeElapsed(snap.sessions, elapsedBaselines, elapsedTick);
export const liveElapsed = (s) => displayedElapsed(s, elapsedBaselines, elapsedTick);

// Card footer elapsed: a running session ticks each second while the
// player runs, so it shows seconds; anything else keeps the recorded
// minute format.
export function cardElapsed(s) {
  const sec = liveElapsed(s);
  if (sec == null) return 'elapsed unknown';
  if (s.lifecycle !== 'running') return formatElapsed(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const ss = sec % 60;
  return h
    ? `${h}h ${String(m).padStart(2, '0')}m ${String(ss).padStart(2, '0')}s`
    : m ? `${m}m ${String(ss).padStart(2, '0')}s` : `${ss}s`;
}

export function lineageLabel(s) {
  const label = ancestryLabel(s, s.lifecycle === 'retired' ? ancestry(s.project_id) : liveAncestry(s.project_id));
  if (label) return label;
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

// Live header summary for one project (live.js holds the counting rule):
// agents, running, needs-you and failed counts.
export const projectSummary = (pid) => attentionCounts(liveSessionsFor(pid), failedSessionIds(snap.runs));

// Sessions behind the header attention chips, live from the snapshot.
export const needsYouSessions = (pid) =>
  sessionsFor(pid).filter((s) => s.lifecycle === 'waiting_for_input' || s.needs_operator_input);
export const failedSessions = (pid) =>
  sessionsFor(pid).filter((s) => sessionStatus(s).key === 'failed');
// The failed run behind a session's Failed status, for its listed reason.
export const failedRunFor = (s) => runsForSession(s.id).find((r) => r.outcome === 'failed') || null;

// "HH:MM UTC" for a recorded observation time; the raw value if unparsable.
export function observedLabel(at) {
  const m = /T(\d{2}:\d{2})/.exec(at || '');
  return m ? `${m[1]} UTC` : (at || 'unknown');
}

// --- Synthetic update driver -------------------------------------------
// Applies projection update events to the loaded snapshot; the rules live in
// events.js so they can be tested without a browser.

export function applyEvent(evt) {
  const result = store.apply(evt);
  if (result.status === 'applied') {
    snap = store.getSnapshot();
    dataVersion += 1;
    observeElapsed(snap.sessions, elapsedBaselines, elapsedTick);
    index = null;
    bump();
  }
  return result;
}

export const driverState = () => ({
  revision: snap.revision, cursor: snap.cursor, pending: queue.length, last: lastResult,
  ...simulationSummary(snap.sessions, queue.length, !!simulation),
});

// Applies the next queued synthetic event and reports what happened.
export function applyNextSyntheticEvent() {
  const evt = queue.shift() || simulation?.next(snap);
  if (!evt) return null;
  lastResult = applyEvent(evt);
  if (lastResult.status !== 'applied') bump();
  return lastResult;
}

// --- Synthetic autoplay --------------------------------------------------
// Applies the queued fixture events on a timer through the same path as
// the manual driver, and ticks running sessions' displayed elapsed each
// second while it plays. Interval math lives in live.js for unit tests.

let playing = false;
let speed = 1;
let eventTimer = null;
let tickTimer = null;

export const autoplayState = () => ({ ...driverState(), playing, speed });

function scheduleEvent() {
  clearTimeout(eventTimer);
  eventTimer = setTimeout(autoplayStep, intervalFor(speed));
}

function autoplayStep() {
  applyNextSyntheticEvent();
  if (queue.length || simulation) scheduleEvent();
  else stopAutoplay();
}

function stopAutoplay() {
  playing = false;
  clearTimeout(eventTimer);
  eventTimer = null;
  clearInterval(tickTimer);
  tickTimer = null;
  bump();
}

export function playAutoplay() {
  if (playing || (!queue.length && !simulation)) return;
  playing = true;
  scheduleEvent();
  tickTimer = setInterval(() => { elapsedTick += 1; bump(); }, 1000);
  bump();
}

export function pauseAutoplay() {
  if (playing) stopAutoplay();
}

export function setAutoplaySpeed(next) {
  speed = cleanSpeed(next);
  if (playing) scheduleEvent();
  bump();
}

export function portfolioTree(pid) {
  const cache = ix().grouped;
  if (!cache.has(pid)) cache.set(pid, groupedTree(pid ? [getProject(pid)] : getProjects(),
    getExecutive(), liveAncestry, !!pid));
  return cache.get(pid);
}

export function projectStatus(pid) {
  const c = projectSummary(pid);
  if (c.failed) return { key: 'failed', label: 'Failed' };
  if (c.needsYou) return { key: 'needs-you', label: 'Needs you' };
  if (c.running) return { key: 'running', label: 'Running' };
  return { key: 'idle', label: 'Done or idle' };
}
