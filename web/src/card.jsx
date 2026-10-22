import { branchCost, formatCost, formatElapsed, getAssignment, lifecycleLabel, lineageLabel, observedLabel } from './data.js';

export function SessionCard({ session: s, childMap, style, selected, expanded, childCount, onSelect, onToggle }) {
  const assignment = getAssignment(s.assignment_id);
  const lineage = lineageLabel(s);
  return (
    <div class={`card state-border-${s.lifecycle} ${selected ? 'selected' : ''}`} style={style}
      data-testid="session-card" data-session-id={s.id} data-parent={s.parent_session_id || ''}
      data-lifecycle={s.lifecycle} data-role={s.role} onClick={() => onSelect(s.id)}>
      <button type="button" class="card-title" aria-pressed={selected} onClick={(e) => { e.stopPropagation(); onSelect(s.id); }}>
        <span class="role">{s.role}</span>
        <span class="assignment-short">{assignment?.summary || 'assignment unknown'}</span>
      </button>
      <div class="card-row">
        <span class={`state state-${s.lifecycle}`} data-testid="state-label">{lifecycleLabel(s.lifecycle)}</span>
        {s.needs_operator_input && <span class="tag tag-needs-input">Needs input</span>}
        {s.stale && <span class="tag tag-stale">Stale</span>}
      </div>
      {(s.stale || s.lifecycle === 'host_offline') && (
        <div class="card-row observed" data-testid="last-observed">Last observed {observedLabel(s.observed_at)}</div>
      )}
      <div class="card-row muted">{s.model || 'model unknown'}</div>
      {lineage && <div class="card-row lineage" data-testid="lineage-label">{lineage}</div>}
      <div class="card-row muted">
        <span>{formatCost(s.cost)}</span> · <span>{formatElapsed(s.elapsed_s)}</span>
        {s.budget && <span> · budget ${s.budget.limit_usd}</span>}
      </div>
      {childCount > 0 && (
        <div class="card-row card-foot">
          <button type="button" class="toggle" aria-expanded={expanded}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} ${childCount} started session${childCount > 1 ? 's' : ''} of ${s.role}`}
            onClick={(e) => { e.stopPropagation(); onToggle(s.id); }}>
            {expanded ? '▾' : '▸'} {childCount} started
          </button>
          <span class="muted" title="Own costs of this session and its descendants">branch {branchCost(s, childMap)}</span>
        </div>
      )}
    </div>
  );
}
