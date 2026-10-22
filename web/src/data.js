// Read-only views over the synthetic fixture. The browser holds no
// authoritative records; a service projection would replace this module.
import * as fx from './fixtures/synthetic.js';

export const isSynthetic = fx.synthetic === true;
export const { loadSessionDetail } = fx;

export const LIFECYCLE_LABELS = {
  running: 'Running',
  waiting_for_input: 'Waiting for input',
  idle: 'Idle',
  ended: 'Ended',
  retired: 'Retired',
  host_offline: 'Host offline',
};

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

export const projects = fx.projects;
export const getProject = (id) => fx.projects.find((p) => p.id === id) || null;
export const sessionsFor = (pid) => fx.sessions.filter((s) => s.project_id === pid);
export const getSession = (id) => fx.sessions.find((s) => s.id === id) || null;
export const getAssignment = (id) => fx.assignments.find((a) => a.id === id) || null;
export const getRun = (id) => fx.runs.find((r) => r.id === id) || null;
export const runsForSession = (sid) => fx.runs.filter((r) => r.session_id === sid);
export const commitmentsFor = (pid) => fx.commitments.filter((c) => c.project_id === pid);
export const decisionsFor = (pid) => fx.decisions.filter((d) => d.project_id === pid);
export const conversationFor = (pid) => fx.conversations[pid] || [];
export const relationshipsFor = (pid) => {
  const ids = new Set(sessionsFor(pid).map((s) => s.id));
  return fx.relationships.filter((r) => ids.has(r.from) || ids.has(r.to));
};
export const relationshipsOf = (id) => fx.relationships.filter((r) => r.from === id || r.to === id);

// Ancestry only: children keyed by parent_session_id.
export function childrenMap(pid) {
  const map = new Map();
  for (const s of sessionsFor(pid)) {
    if (s.parent_session_id) {
      if (!map.has(s.parent_session_id)) map.set(s.parent_session_id, []);
      map.get(s.parent_session_id).push(s);
    }
  }
  return map;
}

export const rootsFor = (pid) => sessionsFor(pid).filter((s) => !s.parent_session_id);

export function descendants(id, children) {
  const out = [];
  const stack = [...(children.get(id) || [])];
  while (stack.length) {
    const s = stack.pop();
    out.push(s);
    stack.push(...(children.get(s.id) || []));
  }
  return out;
}

export function formatCost(cost) {
  if (!cost || cost.amount_usd == null || cost.basis === 'unknown') return 'cost unknown';
  const value = `$${cost.amount_usd.toFixed(2)}`;
  return cost.basis === 'estimate' ? `est. ${value}` : value;
}

// Sums each session's OWN cost once. Unknown stays visible; estimates are marked.
export function branchCost(session, children) {
  let known = 0;
  let unknown = 0;
  let estimate = false;
  for (const s of [session, ...descendants(session.id, children)]) {
    if (s.cost?.amount_usd == null || s.cost?.basis === 'unknown') unknown += 1;
    else {
      known += s.cost.amount_usd;
      if (s.cost.basis === 'estimate') estimate = true;
    }
  }
  let text = `${estimate ? 'est. ' : ''}$${known.toFixed(2)}`;
  if (unknown) text += ` + unknown (${unknown})`;
  return text;
}

export function formatElapsed(seconds) {
  if (seconds == null) return 'elapsed unknown';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`;
}

export function lineageLabel(s) {
  if (s.provenance === 'imported' && !s.parent_session_id) return 'Imported — parent unknown';
  if (s.attempt_of) return `Attempt ${s.attempt}${s.previous_attempt ? ` (after ${s.previous_attempt})` : ''}`;
  if (s.resumption) return `Resumed ×${s.resumption.count} (same session)`;
  return null;
}

export function attentionItems() {
  const items = [];
  for (const d of fx.decisions.filter((x) => x.status === 'pending')) {
    items.push({ key: d.id, kind: d.kind === 'approval' ? 'Pending approval' : 'Pending decision',
      text: d.title, project_id: d.project_id, session_id: d.requested_by });
  }
  for (const s of fx.sessions) {
    if (s.needs_operator_input) items.push({ key: `in-${s.id}`, kind: 'Needs input', text: `${s.role}: ${getAssignment(s.assignment_id)?.summary || ''}`, project_id: s.project_id, session_id: s.id });
    if (s.lifecycle === 'host_offline') items.push({ key: `off-${s.id}`, kind: 'Host offline', text: `${s.role} last observed ${s.observed_at}`, project_id: s.project_id, session_id: s.id });
  }
  for (const a of fx.assignments.filter((x) => x.progress === 'blocked')) {
    const owner = fx.sessions.find((s) => s.assignment_id === a.id);
    items.push({ key: `blk-${a.id}`, kind: 'Blocked', text: `${a.summary}: ${a.blocked_reason}`, project_id: a.project_id, session_id: owner?.id });
  }
  return items;
}

export const activeWork = () => fx.sessions.filter((s) => ['running', 'waiting_for_input'].includes(s.lifecycle));
