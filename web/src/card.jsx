import { useMemo } from 'preact/hooks';
import {
  branchSum, cardElapsed, compactTokens, descendants, getAssignment, isSuperseded, lineageLabel, observedLabel, relationshipsOf,
} from './data.js';
import { ModelName, ProviderLogo, StatusChip, ToolIcons } from './status.jsx';
import { TokenCount, TokenSum } from './tokencount.jsx';

export function SessionCard({
  session: s, childMap, style, selected, expanded, childCount, entering, leaving, muted, onSelect, onToggle, showRelations,
  cardExpanded, onSizeToggle, related, onHover, onFocusCard, compactExecutive,
}) {
  const runs = showRelations ? relationshipsOf(s.id).filter((r) => r.type === 'run_association') : [];
  const assignment = getAssignment(s.assignment_id);
  const lineage = useMemo(() => lineageLabel(s), [s, childMap]);
  const shortLineage = {
    'Imported — parent unknown': 'Imported · parent unknown',
    'Parent cycle in records': 'Parent cycle',
    'Parent in another project': 'Parent in another project',
    'Parent not in this project view': 'Parent outside view',
  }[lineage] || lineage;
  const freshness = s.stale || s.lifecycle === 'host_offline';
  const observed = `Last observed ${observedLabel(s.observed_at)}`;
  const retained = s.lifecycle === 'retired' && childCount > 0 && !leaving;
  const qualifications = [freshness && `${s.stale ? 'Stale observation. ' : ''}${observed} (${s.observed_at || 'unknown'})`,
    lineage, retained && 'Retired · kept for live work'].filter(Boolean).join('. ');
  // Stopped sessions and attempts a later attempt replaced are dimmed.
  const dimmed = s.lifecycle === 'retired' || isSuperseded(s);
  // Collapsing hides the whole subtree, so the chip counts descendants.
  const groups = (childMap.get(s.id) || []).some((node) => node.project);
  const hidden = useMemo(() => groups ? childCount : childCount ? descendants(s.id, childMap).length : 0,
    [s.id, childMap, childCount, groups]);
  const sum = useMemo(() => cardExpanded && !compactExecutive && childCount ? branchSum(s, childMap) : null,
    [s, childMap, childCount, cardExpanded, compactExecutive]);
  const unit = groups ? 'project' : 'session';
  const classes = ['card', muted && 'branch-muted', selected && 'selected', dimmed && 'card-dimmed',
    related && 'relationship-active', compactExecutive && 'scoped-executive',
    entering && 'card-enter', leaving && 'card-leave', !cardExpanded && 'card-compact'];
  const branchChip = childCount > 0 && (
    <button type="button" class="toggle child-chip" aria-expanded={expanded}
      aria-label={`${expanded ? 'Collapse' : 'Expand'} ${hidden} ${unit}${hidden > 1 ? 's' : ''} under ${s.role}`}
      onClick={(e) => { e.stopPropagation(); onToggle(s.id); }}>
      {expanded ? `▾ ${hidden}` : `+${hidden} ›`}
    </button>
  );
  const sizeToggle = <button type="button" class="card-size-toggle" aria-expanded={cardExpanded}
    aria-label={cardExpanded ? 'Collapse card' : 'Expand card'}
    onClick={(e) => { e.stopPropagation(); onSizeToggle(s.id, !cardExpanded); }}>
    <span aria-hidden="true">{cardExpanded ? '⌃' : '⌄'}</span>
  </button>;
  return (
    <div class={classes.filter(Boolean).join(' ')} style={style}
      data-project-id={s.project_id || undefined} data-testid="session-card"
      data-session-id={s.id} data-parent={s.parent_session_id || ''}
      data-card-expanded={cardExpanded} data-lifecycle={s.lifecycle} data-role={s.role}
      data-dimmed={dimmed || undefined}
      onMouseEnter={() => onHover?.(s.id)} onMouseLeave={() => onHover?.(null)}
      onFocusIn={() => onFocusCard?.(s.id)}
      onFocusOut={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) onFocusCard?.(null); }} onClick={() => onSelect(s.id)}>
      <div class="card-head">
        <ProviderLogo model={s.model} />
        <button type="button" class="card-title" aria-pressed={selected}
          aria-label={qualifications ? `${s.role}. ${qualifications}` : undefined}
          title={qualifications || undefined}
          onClick={(e) => { e.stopPropagation(); onSelect(s.id); }}>
          <span class="role">{s.role}</span>
          {cardExpanded && <ModelName model={s.model} />}
        </button>
        <StatusChip session={s} />
        {!cardExpanded && <TokenCount tokens={s.tokens} testid="own-tokens" />}
        {!cardExpanded && branchChip}
        {!compactExecutive && sizeToggle}
      </div>
      {!cardExpanded && <div class="compact-qualifications">
        {freshness && <div class="compact-qualification observed" data-testid="last-observed"
          title={qualifications} aria-label={`${s.stale ? 'Stale observation. ' : ''}${observed} (${s.observed_at || 'unknown'})`}>
          {s.stale ? 'Stale' : 'Last observed'} · {observedLabel(s.observed_at)}
        </div>}
        {lineage && <div class="compact-qualification lineage" data-testid="lineage-label"
          title={lineage} aria-label={lineage}>{shortLineage}</div>}
      </div>}
      {retained && <div class="card-row retained-label" title="Retired · kept for live work"
        data-testid="retained-label">Retired · kept for live work</div>}
      {cardExpanded && <>
        <div class="card-task">
          <ToolIcons session={s} />
          <span class="task-text" data-testid="task-text">{assignment?.summary || 'assignment unknown'}</span>
        </div>
        {!compactExecutive && <>
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
            {runs.map((r) => <span key={r.id} class="run-badge" data-relationship-type="run_association"
              title={`Associated run: ${r.to}`}>run · {r.to}</span>)}
            <span class="foot-metrics">
              <TokenCount tokens={s.tokens} testid="own-tokens" /> · <span data-testid="elapsed">{cardElapsed(s)}</span>
              {s.budget && <span> · budget {compactTokens(s.budget.limit_tokens)} tok ({s.budget.basis})</span>}
            </span>
            {branchChip}
            {childCount > 0 && (
              <TokenSum sum={sum} prefix="branch " testid="branch-tokens" />
            )}
          </div>
        </>}
      </>}
    </div>
  );
}
