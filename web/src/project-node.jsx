import { projectSum, projectSummary } from './data.js';
import { TokenSum } from './tokencount.jsx';

export function ProjectLabel({ project }) {
  const c = projectSummary(project.id);
  return <>
    <strong title={project.name}>{project.name}</strong>
    <span class="muted">{c.running} running · {c.needsYou} needs you</span>
    <TokenSum sum={projectSum(project.id)} />
  </>;
}

export function ProjectNode({ project, style, expanded, onToggle, muted }) {
  return <button type="button" class={`project-node ${muted ? 'branch-muted' : ''}`} style={style}
    data-testid="project-node" data-project-id={project.id} aria-expanded={expanded}
    aria-label={`${expanded ? 'Collapse' : 'Expand'} project ${project.name}`} onClick={onToggle}>
    <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>
    <ProjectLabel project={project} />
  </button>;
}
