import { liveSessionsFor, projectSum, projectSummary, sessionStatus } from './data.js';
import { TokenSum } from './tokencount.jsx';

function ProjectGlyph() {
  return <span class="project-glyph" data-testid="project-glyph" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round">
      <path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v10H3Z" />
      <path d="M3 10h18" />
    </svg>
  </span>;
}

export function ProjectLabel({ project }) {
  const c = projectSummary(project.id);
  const buckets = new Map();
  for (const s of liveSessionsFor(project.id)) {
    const recorded = sessionStatus(s);
    const status = s.needs_operator_input && recorded.key !== 'failed'
      ? { key: 'needs-you', label: 'Needs you' } : recorded;
    const bucket = buckets.get(status.key) || { ...status, count: 0 };
    bucket.count += 1;
    buckets.set(status.key, bucket);
  }
  const text = [...buckets.values()].map((b) => `${b.count} ${b.label.toLowerCase()}`).join(', ') || 'No live agents';
  return <span class="project-label">
    <span class="project-heading">
      <ProjectGlyph />
      <span class="project-title"><span class="project-eyebrow">PROJECT</span>
        <strong title={project.name}>{project.name}</strong></span>
    </span>
    <span class="project-state-bar" role="img" aria-label={text} title={text}>
      {[...buckets.values()].map((b) => <i key={b.key} class={`status-${b.key}`}
        style={{ flexGrow: b.count }} />)}
    </span>
    <span class="project-counts">
      <span class="project-count" data-count="running">{c.running} running</span>
      <span class="project-count" data-count="needs-you">{c.needsYou} needs you</span>
      <span class="project-count" data-count="failed">{c.failed} failed</span>
    </span>
    <span class="project-metrics"><span>{c.agents} agents</span><TokenSum sum={projectSum(project.id)} /></span>
  </span>;
}

export function ProjectNode({ project, style, expanded, onToggle, muted }) {
  return <button type="button" class={`project-node ${muted ? 'branch-muted' : ''}`} style={style}
    data-testid="project-node" data-project-id={project.id} aria-expanded={expanded}
    aria-label={`${expanded ? 'Collapse' : 'Expand'} project ${project.name}`} onClick={onToggle}>
    <span class="project-disclosure" aria-hidden="true">{expanded ? '⌃' : '⌄'}</span>
    <ProjectLabel project={project} />
  </button>;
}
