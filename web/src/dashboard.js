// Read-only dashboard projections. Urgency comes from recorded types, never inferred intent.
import { tokenSum } from './tokens.js';
import { STEPS } from './setup.js';
import { bandLabel, connectedUsage, mostConstrainedSample, admissionBand, resetLabel } from './usage.js';

export const FILTERS = ['All', 'Needs you', 'Failed', 'Setup'];
export const STEP_LABELS = { providers: 'Connect subscriptions', harnesses: 'Choose harnesses',
  models: 'Choose models', roles: 'Configure roles' };
const needsInput = (s) => s.lifecycle === 'waiting_for_input' || s.needs_operator_input;
const byTime = (a, b) => (b.at || '').localeCompare(a.at || '') || a.id.localeCompare(b.id);
export function dashboardKPIs(snapshot) {
  const sessions = snapshot.sessions;
  const failed = new Set(snapshot.runs.filter((r) => r.outcome === 'failed').map((r) => r.session_id));
  return {
    running: sessions.filter((s) => s.lifecycle === 'running').length,
    needsYou: sessions.filter(needsInput).length,
    failed: sessions.filter((s) => failed.has(s.id)).length,
    ended: sessions.filter((s) => ['ended', 'retired'].includes(s.lifecycle)).length,
    tokens: tokenSum(sessions),
  };
}

export function priorityItems(snapshot, setup) {
  const items = [];
  const sessions = new Map(snapshot.sessions.map((s) => [s.id, s]));
  const assignments = new Map(snapshot.assignments.map((a) => [a.id, a]));
  const add = (kind, rank, s, fields) => items.push({ kind, rank, sessionId: s?.id,
    projectId: s?.project_id, role: s?.role, at: s?.observed_at, ...fields });
  if (!setup.complete) {
    const step = STEPS.find((s) => !setup.completed[s]) || 'review';
    add('setup', 0, null, { id: 'setup', title: 'Finish configuring Odin', step,
      description: `Next: ${STEP_LABELS[step] || 'Review and apply'}`, progress: setup.progress });
  }
  for (const s of snapshot.sessions.filter(needsInput)) {
    add('needs', 1, s, { id: `input:${s.id}`, title: assignments.get(s.assignment_id)?.summary || 'Assignment unknown',
      description: 'Waiting for operator input' });
  }
  for (const r of snapshot.runs.filter((r) => r.outcome === 'failed')) {
    const s = sessions.get(r.session_id);
    add('failed', 2, s, { id: `failed:${r.id}`, sessionId: r.session_id, projectId: r.project_id,
      title: assignments.get(r.assignment_id)?.summary || r.summary, description: `Run recorded failed · ${r.summary}` });
  }
  for (const d of snapshot.decisions.filter((d) => d.status === 'pending')) {
    add('decision', 3, sessions.get(d.requested_by), { id: d.id, sessionId: d.requested_by,
      projectId: d.project_id, title: d.title, description: 'Pending recorded decision', decision: d });
  }
  for (const l of connectedUsage(setup)) {
    const sample = mostConstrainedSample(l.usage?.samples, setup.catalogue.usage?.band_ceilings);
    const band = admissionBand(sample, setup.catalogue.usage?.band_ceilings);
    if (band && band !== 'clear') add('usage', 4, null, { id: `usage:${l.id}`, title: l.label,
      description: `${bandLabel(band)} · ${sample.utilization_percent}% · ${resetLabel(sample)}`,
      at: sample.observed_at, role: l.provider.label, step: 'providers' });
  }
  for (const s of snapshot.sessions.filter((s) => s.lifecycle === 'host_offline' || s.stale)) {
    add('host', 5, s, { id: `host:${s.id}`, title: s.lifecycle === 'host_offline' ? 'Host offline' : 'Stale observation',
      description: assignments.get(s.assignment_id)?.summary || 'Assignment unknown' });
  }
  return items.sort((a, b) => a.rank - b.rank || byTime(a, b));
}

export function filterPriority(items, filter) {
  const kind = { 'Needs you': 'needs', Failed: 'failed', Setup: 'setup' }[filter];
  return kind ? items.filter((item) => item.kind === kind) : items;
}
export const priorityCounts = (items) => Object.fromEntries(FILTERS.map((f) => [f, filterPriority(items, f).length]));
export const relativeTime = (at, now) => {
  const seconds = Math.max(0, Math.floor((now - Date.parse(at)) / 1000));
  if (!Number.isFinite(seconds)) return 'time unknown';
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};
const activityCache = new WeakMap();
function activityIndex(snapshot) {
  if (activityCache.has(snapshot)) return activityCache.get(snapshot);
  const all = Object.entries(snapshot.activity).flatMap(([pid, entries]) =>
    entries.map((e) => ({ ...e, projectId: pid })));
  const recent = all.filter((e) => e.kind !== 'session.usage_updated').sort(byTime);
  const bySession = new Map();
  for (const e of recent) {
    if (!bySession.has(e.session_id)) bySession.set(e.session_id, []);
    bySession.get(e.session_id).push(e);
  }
  const time = Math.max(Date.parse(snapshot.generated_at), ...snapshot.sessions.map((s) => Date.parse(s.observed_at)),
    ...all.map((e) => Date.parse(e.at)));
  const index = { recent, bySession, time };
  activityCache.set(snapshot, index);
  return index;
}

// Snapshot identity changes with data, so elapsed ticks reuse the sorted index.
export const dashboardTime = (snapshot) => activityIndex(snapshot).time;
export const recentActivity = (snapshot) => activityIndex(snapshot).recent;
export const recentSessionActivity = (snapshot, sid) => (activityIndex(snapshot).bySession.get(sid) || []).slice(0, 3);

export function projectOverview(snapshot, pid) {
  const sessions = snapshot.sessions.filter((s) => s.project_id === pid);
  const kpis = dashboardKPIs({ ...snapshot, sessions });
  const failed = new Set(snapshot.runs.filter((r) => r.outcome === 'failed').map((r) => r.session_id));
  const buckets = {};
  for (const s of sessions.filter((s) => s.lifecycle !== 'retired')) {
    const key = failed.has(s.id) && s.lifecycle === 'ended' ? 'failed' : needsInput(s) ? 'needs-you'
      : ({ ended: 'done', host_offline: 'host-offline', running: 'running' }[s.lifecycle] || 'idle');
    buckets[key] = (buckets[key] || 0) + 1;
  }
  return { ...kpis, agents: sessions.filter((s) => s.lifecycle !== 'retired').length, buckets,
    at: (snapshot.activity[pid] || []).map((e) => e.at).concat(sessions.map((s) => s.observed_at)).sort().at(-1) };
}
