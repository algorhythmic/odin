import { branchSum, cardElapsed, compactTokens, descendants, getAssignment, isSuperseded, lineageLabel, observedLabel } from './data.js';
import { ModelName, ProviderLogo, StatusChip, ToolIcons } from './status.jsx';
import { TokenCount, TokenSum } from './tokencount.jsx';

export function SessionCard({
  session: s, childMap, style, selected, expanded, childCount, entering, muted, onSelect, onToggle,
}) {
  const assignment = getAssignment(s.assignment_id);
  const lineage = lineageLabel(s);
  // Stopped sessions and attempts a later attempt replaced are dimmed.
  const dimmed = s.lifecycle === 'retired' || isSuperseded(s);
  // Collapsing hides the whole subtree, so the chip counts descendants.
  const groups = (childMap.get(s.id) || []).some((node) => node.project);
  const hidden = groups ? childCount : childCount ? descendants(s.id, childMap).length : 0;
  const unit = groups ? 'project' : 'session';
  const classes = ['card', muted && 'branch-muted', selected && 'selected', dimmed && 'card-dimmed', entering && 'card-enter'];
  return (
    <div class={classes.filter(Boolean).join(' ')} style={style}
      data-project-id={s.project_id || undefined} data-testid="session-card"
      data-session-id={s.id} data-parent={s.parent_session_id || ''}
      data-lifecycle={s.lifecycle} data-role={s.role} data-dimmed={dimmed || undefined} onClick={() => onSelect(s.id)}>
      <div class="card-head">
        <ProviderLogo model={s.model} />
        <button type="button" class="card-title" aria-pressed={selected} onClick={(e) => { e.stopPropagation(); onSelect(s.id); }}>
          <span class="role">{s.role}</span>
          <ModelName model={s.model} />
        </button>
        <StatusChip session={s} />
      </div>
      <div class="card-task">
        <ToolIcons session={s} />
        <span class="task-text" data-testid="task-text">{assignment?.summary || 'assignment unknown'}</span>
      </div>
      {(s.needs_operator_input || s.stale) && (
        <div class="card-row">
          {s.needs_operator_input && <span class="tag tag-needs-input">Needs input</span>}
          {s.stale && <span class="tag tag-stale">Stale</span>}
        </div>
      )}
      {(s.stale || s.lifecycle === 'host_offline') && (
        <div class="card-row observed" data-testid="last-observed">Last observed {observedLabel(s.observed_at)}</div>
      )}
      {lineage && <div class="card-row lineage" data-testid="lineage-label">{lineage}</div>}
      <div class="card-row card-foot muted">
        <span class="foot-metrics">
          <TokenCount tokens={s.tokens} testid="own-tokens" /> · <span data-testid="elapsed">{cardElapsed(s)}</span>
          {s.budget && <span> · budget {compactTokens(s.budget.limit_tokens)} tok ({s.budget.basis})</span>}
        </span>
        {childCount > 0 && (
          <button type="button" class="toggle child-chip" aria-expanded={expanded}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} ${hidden} ${unit}${hidden > 1 ? 's' : ''} under ${s.role}`}
            onClick={(e) => { e.stopPropagation(); onToggle(s.id); }}>
            {expanded ? `▾ ${hidden}` : `+${hidden} ›`}
          </button>
        )}
        {childCount > 0 && (
          <TokenSum sum={branchSum(s, childMap)} prefix="branch " testid="branch-tokens" />
        )}
      </div>
    </div>
  );
}
