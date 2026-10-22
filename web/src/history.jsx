import { getAssignment, lifecycleLabel, lineageLabel, observedLabel, sessionsFor } from './data.js';
import { projectHref, sessionHref } from './route.js';

const ENDED = new Set(['ended', 'retired']);

// History of a project: sessions that have ended or retired, then the two
// kinds of continuation kept apart. A new attempt is a distinct session; a
// resumption continues the same session and never adds a row of its own.
export function History({ project }) {
  const pid = project.id;
  const sessions = sessionsFor(pid);
  const ended = sessions.filter((s) => ENDED.has(s.lifecycle)).sort((a, b) => b.observed_at.localeCompare(a.observed_at));
  const attempts = new Map();
  for (const s of sessions.filter((x) => x.attempt)) {
    const key = s.attempt_of || s.assignment_id || 'unknown';
    if (!attempts.has(key)) attempts.set(key, []);
    attempts.get(key).push(s);
  }
  const resumed = sessions.filter((s) => s.resumption);
  const link = (s) => <a href={sessionHref(pid, s.id)}>{s.role} <code>{s.id}</code></a>;

  return (
    <div class="history" data-testid="history">
      <p><a href={projectHref(pid)}>Back to {project.name}</a></p>
      <h1>History — {project.name}</h1>

      <section aria-labelledby="hist-ended-h">
        <h2 id="hist-ended-h">Ended and retired sessions</h2>
        {ended.length ? (
          <table data-testid="history-ended">
            <thead><tr><th>Session</th><th>State</th><th>Last observed</th><th>Assignment</th><th>Lifecycle identity</th></tr></thead>
            <tbody>
              {ended.map((s) => (
                <tr key={s.id} data-session-id={s.id}>
                  <td>{link(s)}</td>
                  <td><span class={`state state-${s.lifecycle}`}>{lifecycleLabel(s.lifecycle)}</span></td>
                  <td>{observedLabel(s.observed_at)}</td>
                  <td>{getAssignment(s.assignment_id)?.summary || 'Assignment unknown'}</td>
                  <td>{lineageLabel(s) || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p class="muted">No ended or retired sessions.</p>}
      </section>

      <section aria-labelledby="hist-attempts-h">
        <h2 id="hist-attempts-h">Attempts (distinct sessions)</h2>
        {attempts.size ? [...attempts].map(([key, list]) => (
          <div key={key} data-testid="history-attempts" data-assignment={key}>
            <h3>{getAssignment(key)?.summary || key}</h3>
            <ol>
              {list.sort((a, b) => a.attempt - b.attempt).map((s) => (
                <li key={s.id} data-session-id={s.id}>
                  Attempt {s.attempt}: {link(s)} — {lifecycleLabel(s.lifecycle)}
                  {s.previous_attempt && <> (after {s.previous_attempt})</>}
                </li>
              ))}
            </ol>
          </div>
        )) : <p class="muted">No repeated attempts recorded.</p>}
      </section>

      <section aria-labelledby="hist-resumed-h">
        <h2 id="hist-resumed-h">Resumptions (same session)</h2>
        {resumed.length ? (
          <ul data-testid="history-resumptions">
            {resumed.map((s) => (
              <li key={s.id} data-session-id={s.id}>
                {link(s)} resumed ×{s.resumption.count} from host session {s.resumption.resumed_from_host_session} at {observedLabel(s.resumption.resumed_at)} — still one Odin session
              </li>
            ))}
          </ul>
        ) : <p class="muted">No resumptions recorded.</p>}
      </section>
    </div>
  );
}
