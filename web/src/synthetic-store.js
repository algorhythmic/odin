// Retention belongs to the synthetic source, never to a future service projection.
import { reduceEvent } from './events.js';
import { visibleSessions } from './simulation.js';

export const MAX_RETIRED_SESSIONS = 500;
export const MAX_ACTIVITY_PER_PROJECT = 1000;
export const MAX_SEEN_EVENTS = 4096;

export function createSyntheticStore(initial) {
  let snapshot = initial;
  const seen = new Set();
  const trimmedProjects = new Set();

  function retain(next) {
    const retired = next.sessions.filter((s) => s.lifecycle === 'retired');
    let sessions = next.sessions;
    if (retired.length > MAX_RETIRED_SESSIONS) {
      const keep = new Set(visibleSessions(sessions).map((s) => s.id));
      retired.sort((a, b) => b.observed_at.localeCompare(a.observed_at) || a.id.localeCompare(b.id));
      for (const s of retired.slice(0, MAX_RETIRED_SESSIONS)) keep.add(s.id);
      sessions = sessions.filter((s) => {
        if (keep.has(s.id)) return true;
        trimmedProjects.add(s.project_id);
        return false;
      });
    }
    const ids = new Set(sessions.map((s) => s.id));
    const activity = Object.fromEntries(Object.entries(next.activity).map(([pid, entries]) => {
      const retained = entries.filter((e) => ids.has(e.session_id));
      if (retained.length !== entries.length || retained.length > MAX_ACTIVITY_PER_PROJECT) trimmedProjects.add(pid);
      return [pid, retained.slice(-MAX_ACTIVITY_PER_PROJECT)];
    }));
    return { ...next, sessions, activity, runs: next.runs.filter((r) => ids.has(r.session_id)) };
  }

  return {
    getSnapshot: () => snapshot,
    historyTrimmed: (pid) => pid === undefined ? trimmedProjects.size > 0 : trimmedProjects.has(pid),
    seenCount: () => seen.size,
    apply(evt) {
      const out = reduceEvent(snapshot, seen, evt);
      if (out.result.status === 'applied') {
        snapshot = retain(out.snapshot);
        seen.add(evt.event_id);
        if (seen.size > MAX_SEEN_EVENTS) seen.delete(seen.values().next().value);
      }
      return out.result;
    },
  };
}
