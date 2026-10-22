import { useLayoutEffect, useRef, useState } from 'preact/hooks';
import { formatCost, getAssignment, lifecycleLabel, lineageLabel, observedLabel } from './data.js';

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
export function ListTree({ roots, childMap, collapsed, selectedId, onSelect, onToggle }) {
  const rows = flatten(roots, childMap, collapsed);
  const [focusId, setFocusId] = useState(null);
  const ref = useRef(null);
  const active = rows.find((r) => r.s.id === focusId) ? focusId
    : rows.find((r) => r.s.id === selectedId) ? selectedId : rows[0]?.s.id;
  const moved = useRef(false);
  // Reading position: the first visible row and its offset from the top.
  // Rows inserted or removed above it by an update must not move it.
  const anchor = useRef(null);
  const remember = () => {
    const el = ref.current;
    if (!el) return;
    // A row with less than a few pixels showing is not the one being read.
    const row = [...el.children].find((r) => r.offsetTop + r.offsetHeight > el.scrollTop + 4);
    anchor.current = row && el.scrollTop > 0 ? { id: row.dataset.sessionId, delta: row.offsetTop - el.scrollTop } : null;
  };

  useLayoutEffect(() => {
    const el = ref.current;
    const a = anchor.current;
    const row = a && el?.querySelector(`[data-session-id="${CSS.escape(a.id)}"]`);
    if (row) el.scrollTop = row.offsetTop - a.delta;
  });

  useLayoutEffect(() => {
    if (!moved.current) return;
    moved.current = false;
    ref.current?.querySelector(`[data-session-id="${CSS.escape(active)}"]`)?.focus();
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
      case 'Enter': case ' ': moved.current = true; onSelect(row.s.id); break;
      default: return;
    }
    e.preventDefault();
  };

  return (
    <ul class="list-tree" role="tree" aria-label="Sessions by ancestry" ref={ref} onKeyDown={onKeyDown} onScroll={remember} data-testid="list-view">
      {rows.map(({ s, level, kids, pos, size }) => {
        const lineage = lineageLabel(s);
        return (
          <li key={s.id} role="treeitem" aria-level={level} aria-setsize={size} aria-posinset={pos}
            aria-expanded={kids.length ? !collapsed.has(s.id) : undefined} aria-selected={s.id === selectedId}
            tabIndex={s.id === active ? 0 : -1} data-session-id={s.id} data-parent={s.parent_session_id || ''}
            data-lifecycle={s.lifecycle} class={`list-row ${s.id === selectedId ? 'selected' : ''}`}
            style={{ paddingLeft: `${(level - 1) * 1.25 + 0.5}rem` }}
            onClick={() => { setFocusId(s.id); onSelect(s.id); }} onFocus={() => setFocusId(s.id)}>
            <span class="twisty" aria-hidden="true">{kids.length ? (collapsed.has(s.id) ? '▸' : '▾') : '·'}</span>
            <span class="role">{s.role}</span>
            <span class="assignment-short">{getAssignment(s.assignment_id)?.summary}</span>
            <span class={`state state-${s.lifecycle}`} data-testid="state-label">{lifecycleLabel(s.lifecycle)}</span>
            {s.needs_operator_input && <span class="tag tag-needs-input">Needs input</span>}
            {s.stale && <span class="tag tag-stale">Stale</span>}
            {(s.stale || s.lifecycle === 'host_offline') && (
              <span class="observed" data-testid="last-observed">Last observed {observedLabel(s.observed_at)}</span>
            )}
            {lineage && <span class="lineage">{lineage}</span>}
            <span class="muted">{formatCost(s.cost)}</span>
          </li>
        );
      })}
    </ul>
  );
}
