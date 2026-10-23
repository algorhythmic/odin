// Pure helpers for the prototype's live surface: autoplay scheduling and
// the header's live summary counts. No DOM and no fixtures, so Node can
// test it directly (tests-unit/live.test.js). The store in data.js owns
// the timers and calls into these.

export const SPEEDS = [0.5, 1, 2, 4];
export const BASE_INTERVAL_MS = 1200;

// Only the documented speeds schedule events; anything else falls back
// to 1× rather than disabling or guessing.
export const cleanSpeed = (s) => (SPEEDS.includes(s) ? s : 1);

// Milliseconds between applied events at a playback speed.
export const intervalFor = (speed) => BASE_INTERVAL_MS / cleanSpeed(speed);

export const simulationSummary = (sessions, pending, enabled) => ({
  generating: enabled && pending === 0,
  population: sessions.filter((s) => s.lifecycle !== 'retired').length,
  available: pending > 0 || enabled,
});

// Session ids with a run recorded failed. A failed run on an ended
// session is what the status set reads as "Failed".
export const failedSessionIds = (runs) =>
  new Set(runs.filter((r) => r.outcome === 'failed').map((r) => r.session_id));

// Live header counts for one project's sessions. "Needs you" covers a
// session waiting for input or flagged needs_operator_input; "failed" is
// an ended session with a run recorded failed (the same rule as the
// status chip). Unknown states are not guessed into a bucket.
export function attentionCounts(sessions, failedIds) {
  let running = 0;
  let needsYou = 0;
  let failed = 0;
  for (const s of sessions) {
    if (s.lifecycle === 'running') running += 1;
    if (s.lifecycle === 'waiting_for_input' || s.needs_operator_input) needsYou += 1;
    if (s.lifecycle === 'ended' && failedIds.has(s.id)) failed += 1;
  }
  return { agents: sessions.length, running, needsYou, failed };
}

// New observations rebase ticks so recorded intervals are not counted twice.
// Lifecycle and elapsed changes also rebase; new sessions inherit no earlier ticks.
export function observeElapsed(sessions, baselines, tick) {
  const retained = new Set(sessions.map((s) => s.id));
  for (const id of baselines.keys()) if (!retained.has(id)) baselines.delete(id);
  for (const s of sessions) {
    const prev = baselines.get(s.id);
    if (!prev || prev.lifecycle !== s.lifecycle || prev.elapsed !== s.elapsed_s
      || Date.parse(s.observed_at) > Date.parse(prev.observedAt)) {
      baselines.set(s.id, { lifecycle: s.lifecycle, elapsed: s.elapsed_s, observedAt: s.observed_at, since: tick });
    }
  }
}

// The displayed elapsed: a running session with a known elapsed_s adds
// only the ticks since its baseline; anything else keeps the recorded
// value (null stays null). The recorded elapsed_s is never rewritten.
export function displayedElapsed(session, baselines, tick) {
  if (session.lifecycle !== 'running' || session.elapsed_s == null) return session.elapsed_s;
  const base = baselines.get(session.id);
  return base ? session.elapsed_s + Math.max(0, tick - base.since) : session.elapsed_s;
}

// Animations must be instant when the operator prefers reduced motion.
// Guarded so the pure module still loads under Node.
export const prefersReducedMotion = () =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
