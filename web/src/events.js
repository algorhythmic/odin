// Projection update events applied to a snapshot (draft rules in
// docs/design/WEB-APP-PROJECTION.md, section 4). Pure: no DOM, no fixtures,
// so Node can test it directly (tests-unit/). The store in data.js keeps the
// current snapshot and the set of applied event ids and calls reduceEvent.
//
// An event id seen before is ignored (idempotent re-delivery); a revision
// that skips ahead is a gap and is not applied, because only a fresh
// snapshot can repair it. Rejected events change nothing and are not
// remembered, so a corrected re-delivery under the same id can still apply.

export const LIFECYCLES = new Set(['running', 'idle', 'waiting_for_input', 'ended', 'retired', 'host_offline']);
export const EVENT_TYPES = new Set(['session.lifecycle_changed', 'session.started', 'session.usage_updated', 'session.retired']);
export const TOKEN_COUNTERS = ['uncached_input', 'cache_read', 'cache_write', 'output'];
export const TOKEN_BASES = new Set(['measured', 'estimate', 'unknown']);
export const RUN_OUTCOMES = new Set(['verified', 'unverified', 'failed', 'unknown']);

const isId = (v) => typeof v === 'string' && v.length > 0;

// A run record riding on a session.lifecycle_changed event (the draft
// carries a run's recorded outcome with the lifecycle change that ended
// it, so a failure appears in one update, not two). Returns a reason, or
// null when the record is usable.
function runProblem(run, sessionId) {
  if (!run || typeof run !== 'object' || Array.isArray(run)) return 'run is not an object';
  if (!isId(run.id)) return 'run id is not a string';
  if (run.session_id !== sessionId) return 'run names a different session';
  if (!RUN_OUTCOMES.has(run.outcome)) return 'unknown run outcome';
  return null;
}

// The tokens record's documented shape (projection draft section 7): the
// four counters are all non-negative integers or all null, and `basis` is
// "unknown" exactly when they are null. Returns a reason, or null when the
// record is usable.
function tokensProblem(t) {
  if (!t || typeof t !== 'object' || Array.isArray(t)) return 'tokens is not an object';
  if (!TOKEN_BASES.has(t.basis)) return 'tokens basis is not documented';
  const counts = TOKEN_COUNTERS.map((k) => t[k]);
  if (counts.some((c) => c === undefined)) return 'a token counter is missing';
  const nulls = counts.filter((c) => c === null).length;
  if (nulls === counts.length) return t.basis === 'unknown' ? null : 'null token counters require basis "unknown"';
  if (nulls > 0) return 'token counters are all integers or all null, not mixed';
  if (!counts.every((c) => Number.isInteger(c))) return 'a token counter is not an integer';
  if (counts.some((c) => c < 0)) return 'a token counter is negative';
  return t.basis === 'unknown' ? 'basis "unknown" requires null token counters' : null;
}

// Returns { result, snapshot }. `snapshot` is a new object when the event
// applied and the same object otherwise; `seen` is read, never modified.
export function reduceEvent(snapshot, seen, evt) {
  const base = { event_id: evt.event_id, type: evt.type, revision: evt.revision };
  const keep = (extra) => ({ result: { ...base, ...extra }, snapshot });
  const reject = (reason) => keep({ status: 'rejected', reason });
  if (seen.has(evt.event_id)) return keep({ status: 'duplicate' });
  if (!Number.isInteger(evt.revision)) return reject('revision is not an integer');
  if (!EVENT_TYPES.has(evt.type)) return reject('unknown event type');
  if (evt.revision > snapshot.revision + 1) return keep({ status: 'gap', current: snapshot.revision });
  if (evt.revision <= snapshot.revision) return keep({ status: 'stale', current: snapshot.revision });

  const p = evt.payload || {};
  const byId = new Map(snapshot.sessions.map((s) => [s.id, s]));
  let sessions = snapshot.sessions;
  let runs = snapshot.runs;
  let sessionId = p.session_id;
  const patch = (fields) => snapshot.sessions.map((s) => (s.id === sessionId ? { ...s, ...fields } : s));

  if (evt.type === 'session.started') {
    const s = p.session;
    if (!s || typeof s !== 'object') return reject('missing session record');
    if (!isId(s.id)) return reject('session id is not a string');
    if (!isId(s.project_id)) return reject('project_id is not a string');
    if (!snapshot.projects.some((pr) => pr.id === s.project_id)) return reject('unknown project');
    if (!LIFECYCLES.has(s.lifecycle)) return reject('unknown lifecycle');
    if (byId.has(s.id)) return reject('session already exists');
    sessionId = s.id;
    sessions = [...snapshot.sessions, s];
  } else {
    if (!isId(sessionId)) return reject('missing session_id');
    if (!byId.has(sessionId)) return reject('unknown session');
    switch (evt.type) {
      case 'session.lifecycle_changed': {
        if (!LIFECYCLES.has(p.lifecycle)) return reject('unknown lifecycle');
        if (p.run !== undefined) {
          const problem = runProblem(p.run, sessionId);
          if (problem) return reject(`malformed run: ${problem}`);
          runs = [...snapshot.runs, p.run];
        }
        const fields = { lifecycle: p.lifecycle, observed_at: p.observed_at };
        if ('needs_operator_input' in p) fields.needs_operator_input = p.needs_operator_input;
        if ('stale' in p) fields.stale = p.stale;
        sessions = patch(fields);
        break;
      }
      case 'session.usage_updated': {
        const problem = tokensProblem(p.tokens);
        if (problem) return reject(`malformed tokens: ${problem}`);
        sessions = patch({ tokens: p.tokens });
        break;
      }
      default: sessions = patch({ lifecycle: 'retired', needs_operator_input: false, observed_at: p.observed_at }); // session.retired
    }
  }

  const pid = sessions.find((s) => s.id === sessionId).project_id;
  const activity = { ...snapshot.activity, [pid]: [...(snapshot.activity?.[pid] || []), {
    id: evt.event_id, at: evt.at, kind: evt.type, session_id: sessionId, text: evt.summary || evt.type,
  }] };
  return {
    result: { ...base, status: 'applied' },
    snapshot: { ...snapshot, sessions, runs, activity, revision: evt.revision, cursor: evt.cursor },
  };
}
