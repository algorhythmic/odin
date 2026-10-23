// Synthetic activity only. The caller supplies the current projection and applies each returned event.
export const DEFAULT_SEED = '20261022';
export const SIMULATION_STEP_MS = 1200;
export const LINGER_MS = 6000;
export const MAX_LIVE_SESSIONS = 18;
export const liveSessions = (sessions) => sessions.filter((s) => s.lifecycle !== 'retired');

function hash(seed) {
  let n = 2166136261;
  for (const c of String(seed)) n = Math.imul(n ^ c.charCodeAt(0), 16777619);
  return n >>> 0;
}

export function createSimulation(seed = DEFAULT_SEED) {
  let randomState = hash(seed);
  const prefix = `sim-${randomState.toString(36)}`;
  const random = () => {
    randomState = (Math.imul(randomState, 1664525) + 1013904223) >>> 0;
    return randomState / 4294967296;
  };
  const pick = (list) => list[Math.floor(random() * list.length)];
  let step = 0;
  let serial = 0;
  let projectTurn = 0;
  let epoch;
  const clocks = new Map();
  const retries = [];

  return {
    next(snapshot) {
      step += 1;
      epoch ??= Math.max(Date.parse(snapshot.generated_at),
        ...snapshot.sessions.map((s) => Date.parse(s.observed_at)));
      const at = new Date(epoch + step * SIMULATION_STEP_MS).toISOString();
      const event = (type, payload, summary) => ({
        event_id: `${prefix}-event-${step}`, revision: snapshot.revision + 1,
        cursor: `${prefix}-cursor-${step}`, at, type, payload, summary,
      });
      const active = liveSessions(snapshot.sessions);
      // Preserve the malformed project's demonstrations, including its ended cycle members.
      const projects = snapshot.projects.filter((p) => p.id !== 'proj-malformed');
      const managed = active.filter((s) => projects.some((p) => p.id === s.project_id));
      const executive = snapshot.sessions.find((s) => s.id === snapshot.executive_session_id);
      const hasChildren = (s) => active.some((c) => c.parent_session_id === s.id);
      for (const s of managed) {
        const clock = clocks.get(s.id);
        if (!clock) clocks.set(s.id, { born: step, finish: step + 10 + Math.floor(random() * 12), usage: 0,
          ended: s.lifecycle === 'ended' ? Math.min(0, (Date.parse(s.observed_at) - epoch) / SIMULATION_STEP_MS) : null,
          waiting: s.lifecycle === 'waiting_for_input' ? step : null, asked: false });
        else if (s.lifecycle === 'ended' && clock.ended === null) clock.ended = step;
      }
      const retiring = managed.find((s) => s.lifecycle === 'ended' && !hasChildren(s)
        && (step - clocks.get(s.id).ended) * SIMULATION_STEP_MS >= LINGER_MS);
      if (retiring) return event('session.retired', { session_id: retiring.id, observed_at: at },
        'Synthetic session retired after its linger');

      const lifecycle = (s, state, extra = {}) => event('session.lifecycle_changed', {
        session_id: s.id, lifecycle: state, needs_operator_input: state === 'waiting_for_input', observed_at: at, ...extra,
      }, `Synthetic ${s.role}: ${state}`);
      const waiting = managed.find((s) => s.lifecycle === 'waiting_for_input'
        && step - clocks.get(s.id).waiting >= 2);
      if (waiting) return lifecycle(waiting, 'running');

      const start = (pid, previous) => {
        const running = managed.filter((s) => s.project_id === pid && s.lifecycle === 'running');
        const parent = previous ? running.find((s) => s.id === previous.parent_session_id)
          || (previous.parent_session_id === executive?.id && executive.lifecycle === 'running' ? executive : null)
          : pick(running);
        if (!parent && executive?.lifecycle !== 'running') return null;
        const role = previous?.role || (!parent ? 'integration owner' : pick(['worker', 'subagent', 'reviewer']));
        if (parent?.id === executive?.id && role !== 'integration owner') return null;
        let id;
        do { id = `ses-${prefix}-${++serial}`; } while (snapshot.sessions.some((s) => s.id === id));
        const assignment = snapshot.assignments.find((a) => a.project_id === pid);
        const session = {
          id, project_id: pid, parent_session_id: parent?.id || executive.id, provenance: 'recorded', role,
          assignment_id: previous?.assignment_id || assignment?.id || null,
          model: pick(['claude-sonnet-5-5', 'gpt-6.1-sol', 'claude-haiku-5-5']), lifecycle: 'running',
          needs_operator_input: false, observed_at: at, stale: false, elapsed_s: 0, budget: null,
          tokens: { uncached_input: 100, cache_read: 0, cache_write: 50, output: 50, basis: 'measured' },
          attempt: previous ? (previous.attempt || 1) + 1 : 1,
          attempt_of: previous?.attempt_of || previous?.assignment_id || assignment?.id || null,
          previous_attempt: previous?.id || null,
        };
        // A retry keeps its recorded place; an unavailable parent cannot be substituted.
        if (previous && (!parent || parent.id !== previous.parent_session_id)) return null;
        return event('session.started', { session }, `Synthetic ${role} started`);
      };

      if (active.length < MAX_LIVE_SESSIONS) {
        while (retries.length) {
          const previous = retries.shift();
          const retry = start(previous.project_id, previous);
          if (retry) return retry;
        }
        if (projects.length && (active.length < 13 || random() < 0.32)) {
          const pid = projects[projectTurn++ % projects.length].id;
          const started = start(pid);
          if (started) return started;
        }
      }

      const running = managed.filter((s) => s.lifecycle === 'running');
      const workers = running.filter((s) => s.role !== 'integration owner' || s.id.startsWith(`ses-${prefix}-`));
      const finishing = workers.find((s) => clocks.get(s.id).usage > 0
        && step >= clocks.get(s.id).finish && !hasChildren(s));
      if (finishing) {
        const failed = random() < 0.22;
        const outcome = failed ? 'failed' : 'verified';
        clocks.get(finishing.id).ended = step;
        if (failed && (finishing.attempt || 1) < 3 && random() < 0.7) retries.push(finishing);
        let id = `run-${prefix}-${step}`;
        while (snapshot.runs.some((r) => r.id === id)) id += '-next';
        return lifecycle(finishing, 'ended', { run: { id, project_id: finishing.project_id,
          assignment_id: finishing.assignment_id, session_id: finishing.id, outcome,
          summary: failed ? 'Synthetic checks failed' : 'Synthetic checks passed' } });
      }
      const asking = workers.find((s) => !clocks.get(s.id).asked && clocks.get(s.id).usage > 0
        && step - clocks.get(s.id).born > 3);
      if (asking && random() < 0.22) {
        Object.assign(clocks.get(asking.id), { asked: true, waiting: step });
        return lifecycle(asking, 'waiting_for_input');
      }
      const working = pick(running) || (executive?.lifecycle === 'running' ? executive : null);
      if (!working) return null;
      if (clocks.has(working.id)) clocks.get(working.id).usage += 1;
      const tokens = { basis: 'measured' };
      for (const key of ['uncached_input', 'cache_read', 'cache_write', 'output']) {
        tokens[key] = (working.tokens[key] || 0) + 100 + Math.floor(random() * 700);
      }
      return event('session.usage_updated', { session_id: working.id, tokens }, 'Synthetic measured usage');
    },
  };
}
