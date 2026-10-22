import { activeWork, attentionItems, commitmentsFor, getAssignment, getProjects, lifecycleLabel, sessionsFor } from './data.js';
import { projectHref, sessionHref } from './route.js';

export function Overview() {
  const attention = attentionItems();
  const active = activeWork();
  return (
    <div class="overview" data-testid="overview">
      <h1>Overview</h1>
      <section aria-labelledby="attention-h">
        <h2 id="attention-h">Needs attention</h2>
        <ul class="attention-list">
          {attention.map((item) => (
            <li key={item.key} data-testid="attention-item">
              <a href={item.session_id ? sessionHref(item.project_id, item.session_id) : projectHref(item.project_id)}>
                <span class={`tag tag-${item.kind.toLowerCase().replace(/\s+/g, '-')}`}>{item.kind}</span>
                <span>{item.text}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="projects-h">
        <h2 id="projects-h">Projects</h2>
        <ul class="project-list">
          {getProjects().map((p) => {
            const sessions = sessionsFor(p.id);
            return (
              <li key={p.id}>
                <a href={projectHref(p.id)} data-testid="project-link">{p.name}</a>
                <span class="muted"> — {sessions.length} sessions, {commitmentsFor(p.id).length} commitments</span>
                <ul class="commitments">
                  {commitmentsFor(p.id).map((c) => (
                    <li key={c.id}>{c.title} <span class="muted">({c.status.replace('_', ' ')})</span></li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      </section>
      <section aria-labelledby="active-h">
        <h2 id="active-h">Active work</h2>
        <ul class="active-list">
          {active.map((s) => (
            <li key={s.id}>
              <a href={sessionHref(s.project_id, s.id)}>
                <span class={`state state-${s.lifecycle}`}>{lifecycleLabel(s.lifecycle)}</span>
                <span>{s.role}: {getAssignment(s.assignment_id)?.summary}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
