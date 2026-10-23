import { useLayoutEffect, useRef, useState } from 'preact/hooks';
import { formatTokens, getAssignment, isSuperseded, lineageLabel, observedLabel } from './data.js';
import { ProjectLabel } from './project-node.jsx';
import { StatusChip } from './status.jsx';
import { presenceClass, rowKey, usePresence } from './presence.js';

// Visible rows in depth-first order. Collapsed branches are not rendered.
function flatten(roots, childMap, collapsed) {
  const rows = [];
  const walk = (list, level, parent) => {
    list.forEach((s, i) => {
      const kids = childMap.get(s.id) || [];
      rows.push({ s, level, parent, kids, pos: i + 1, size: list.length });
      if (kids.length && !collapsed.has(s.id)) walk(kids, level + 1, s.id);
    });
  };
  walk(roots, 1, null);
  return rows;
}

// ARIA treeview with roving tabindex: Up/Down move, Right expands or enters,
// Left collapses or moves to the parent, Home/End jump, Enter/Space select.
export function ListTree({ roots, childMap, collapsed, selectedId, onSelect, onToggle, highlight }) {
  const present = usePresence(flatten(roots, childMap, collapsed), rowKey);
  const rows = present.map((r) => r.item);
  const [focusId, setFocusId] = useState(null);
  const ref = useRef(null);
  const active = rows.find((r) => r.s.id === focusId) ? focusId
    : rows.find((r) => r.s.id === selectedId) ? selectedId : rows[0]?.s.id;
  const moved = useRef(false);
  // Keep a second row as a fallback if the row being read retires.
  const anchor = useRef([]);
  const headerBottom = () => ref.current?.closest('.workspace').querySelector('.toolbar').getBoundingClientRect().bottom || 0;
  // Entrance transforms are presentation; anchor to each row's layout position.
  const rowTop = (row) => row.offsetTop + ref.current.getBoundingClientRect().top + ref.current.clientTop;
  const remember = () => {
    const el = ref.current;
    if (!el) return;
    anchor.current = [];
    if (!scrollY) return;
    const top = headerBottom();
    const listTop = el.getBoundingClientRect().top + el.clientTop;
    for (const row of el.children) {
      if (row.classList.contains('card-leave')) continue;
      const y = listTop + row.offsetTop;
      if (y + row.offsetHeight <= top + 4 || y >= innerHeight) continue;
      anchor.current.push({ id: row.dataset.sessionId, top: y });
      if (anchor.current.length === 2) break;
    }
  };

  useLayoutEffect(() => {
    addEventListener('scroll', remember, { passive: true });
    return () => removeEventListener('scroll', remember);
  }, []);

  useLayoutEffect(() => {
    const el = ref.current;
    for (const a of anchor.current) {
      const row = el?.querySelector(`[data-session-id="${CSS.escape(a.id)}"]`);
      if (!row || row.classList.contains('card-leave')) continue;
      scrollBy(0, rowTop(row) - a.top);
      break;
    }
    remember();
  });

  const reveal = (row) => {
    if (!row) return;
    row.focus({ preventScroll: true });
    const box = row.getBoundingClientRect();
    const top = headerBottom() + 4;
    const driver = ref.current.closest('.workspace').querySelector('.list-driver');
    const bottom = Math.min(innerHeight, driver?.getBoundingClientRect().top ?? innerHeight) - 4;
    if (box.top < top) scrollBy(0, box.top - top);
    else if (box.bottom > bottom) scrollBy(0, Math.min(box.top - top, box.bottom - bottom));
    remember();
  };

  useLayoutEffect(() => {
    if (!moved.current) return;
    moved.current = false;
    reveal(ref.current?.querySelector(`[data-session-id="${CSS.escape(active)}"]`));
  });

  const go = (id) => { moved.current = true; setFocusId(id); };
  const onKeyDown = (e) => {
    const i = rows.findIndex((r) => r.s.id === active);
    const row = rows[i];
    if (!row) return;
    const expanded = row.kids.length && !collapsed.has(row.s.id);
    switch (e.key) {
      case 'ArrowDown': if (i < rows.length - 1) go(rows[i + 1].s.id); break;
      case 'ArrowUp': if (i > 0) go(rows[i - 1].s.id); break;
      case 'Home': go(rows[0].s.id); break;
      case 'End': go(rows[rows.length - 1].s.id); break;
      case 'ArrowRight':
        if (row.kids.length && !expanded) { moved.current = true; onToggle(row.s.id); } else if (expanded) go(row.kids[0].id);
        break;
      case 'ArrowLeft':
        if (expanded) { moved.current = true; onToggle(row.s.id); } else if (row.parent) go(row.parent);
        break;
      case 'Enter': case ' ':
        moved.current = true;
        if (row.s.project) onToggle(row.s.id); else onSelect(row.s.id);
        break;
      default: return;
    }
    e.preventDefault();
  };

  return (
    <ul class="list-tree" role="tree" aria-label="Sessions by ancestry" ref={ref}
      onKeyDown={onKeyDown} data-testid="list-view">
      {present.map(({ item: { s, level, kids, pos, size }, phase }) => {
        const lineage = s.project ? null : lineageLabel(s);
        const dimmed = s.lifecycle === 'retired' || isSuperseded(s);
        const muted = highlight && s.project_id && s.project_id !== highlight;
        const classes = ['list-row', presenceClass(phase), s.id === selectedId && 'selected',
          dimmed && 'dimmed', muted && 'branch-muted'];
        return (
          <li key={s.id} role="treeitem" aria-level={level} aria-setsize={size} aria-posinset={pos}
            aria-label={s.project ? `Project ${s.project.name}` : undefined}
            aria-description={s.project ? `${collapsed.has(s.id) ? 'Expand' : 'Collapse'} project ${s.project.name}` : undefined}
            aria-expanded={s.project || kids.length ? !collapsed.has(s.id) : undefined}
            aria-selected={s.project ? undefined : s.id === selectedId}
            tabIndex={s.id === active ? 0 : -1} data-session-id={s.id} data-project-id={s.project_id || undefined}
            data-node-kind={s.project ? 'project' : 'session'} data-parent={s.parent_session_id || ''}
            data-lifecycle={s.lifecycle} data-dimmed={dimmed || undefined} class={classes.filter(Boolean).join(' ')}
            style={{ paddingLeft: `${(level - 1) * 1.25 + 0.5}rem` }}
            onClick={() => { setFocusId(s.id); if (s.project) onToggle(s.id); else onSelect(s.id); }}
            onFocus={() => setFocusId(s.id)}>
            {/* Pointer path for expand and collapse; keyboard users have the arrow keys. */}
            <span class={`twisty ${kids.length ? 'twisty-toggle' : ''}`} aria-hidden="true" data-testid={kids.length ? 'list-toggle' : undefined}
              onClick={kids.length ? (e) => { e.stopPropagation(); moved.current = true; setFocusId(s.id); onToggle(s.id); } : undefined}>
              {kids.length ? (collapsed.has(s.id) ? '▸' : '▾') : '·'}</span>
            {s.project ? <ProjectLabel project={s.project} /> : <>
            <span class="role">{s.role}</span>
            <span class="assignment-short">{getAssignment(s.assignment_id)?.summary}</span>
            <StatusChip session={s} />
            {s.needs_operator_input && <span class="tag tag-needs-input">Needs input</span>}
            {s.stale && <span class="tag tag-stale">Stale</span>}
            {(s.stale || s.lifecycle === 'host_offline') && (
              <span class="observed" data-testid="last-observed">Last observed {observedLabel(s.observed_at)}</span>
            )}
            {lineage && <span class="lineage">{lineage}</span>}
            <span class="muted">{formatTokens(s.tokens)}</span>
            </>}
          </li>
        );
      })}
    </ul>
  );
}
