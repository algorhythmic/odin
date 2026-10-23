import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'preact/hooks';
import { RELATION_LABELS, getAssignment, getExecutive, lineageLabel, relationshipsOf, relationshipsFor } from './data.js';
import { createRelationshipRouter, fitTree } from './tree-layout.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { ProjectNode } from './project-node.jsx';
import { SessionCard } from './card.jsx';
import { cardDimensions, cardIsExpanded } from './card-size.js';
import { useTreePresence } from './presence.js';
import { nodeLabel, storedNodeId } from './ancestry.js';

const edgeKey = (e) => JSON.stringify([storedNodeId(e.from), storedNodeId(e.to)]);
const clamp = (n) => Math.max(0.5, Math.min(2, n));
const INSTRUCTIONS = 'Use + and - to zoom, arrow keys to pan, and 0 to reset the view. Drag the background to pan.';
const STYLES = { project: 'project', ancestry: 'started (ancestry)', review: 'reviews',
  delegation: 'delegated to', assignment_owner: 'owns assignment' };

function RelationshipKey({ styles, prefs }) {
  return <div class="legend" aria-label="Relationship key">
    <button type="button" aria-expanded={prefs.keyOpen} aria-controls="relationship-key"
      onClick={() => updatePrefs({ keyOpen: !prefs.keyOpen })}><span aria-hidden="true">☷</span> Key</button>
    {prefs.keyOpen && <div id="relationship-key" class="key-content">
      <label class="check"><input type="checkbox" checked={prefs.showRelations}
        onChange={(e) => updatePrefs({ showRelations: e.currentTarget.checked })} />Show all relationships</label>
      {styles.map((type) => <div class="legend-row" key={type} data-style={type}>
        <svg width="40" height="16" aria-hidden="true" class={type === 'project' || type === 'ancestry'
          ? '' : `relation-edge relation-${type}`}>
          <path class={type === 'project' ? 'sample-project' : type === 'ancestry' ? 'sample-ancestry' : ''} d="M2,8 L36,8" />
          {type === 'ancestry' && <circle class="sample-port" cx="5" cy="8" r="3" />}
          {type !== 'project' && type !== 'ancestry' && <path class="arrowhead" d="M32,4 L38,8 L32,12 z" />}
        </svg>
        <span>{STYLES[type]}</span>
      </div>)}
    </div>}
  </div>;
}

export function TreeView({ pid, roots, childMap, collapsed, selectedId, onSelect, onToggle, showRelations, highlight,
  cardSizes, onSizeToggle, driver }) {
  const prefs = usePrefs();
  const [hovered, setHovered] = useState(null);
  const [focused, setFocused] = useState(null);
  const executive = getExecutive();
  const treeRoots = useMemo(() => pid && executive ? [executive] : roots, [pid, executive, roots]);
  const treeChildren = useMemo(() => pid && executive
    ? new Map([...childMap, [executive.id, roots]]) : childMap, [pid, executive, roots, childMap]);
  const viewport = useRef(null);
  const [area, setArea] = useState({ w: 0, h: 600, x: 0, y: 0 });
  const [manual, setManual] = useState(null);
  // A detail drawer needs a taller arrangement to keep the selected card readable.
  const geometry = useMemo(() => fitTree({ roots: treeRoots, children: treeChildren, collapsed,
    executiveId: executive?.id, minReadable: selectedId ? 0.85 : undefined },
    (s) => pid && s.id === executive?.id ? { w: 220, h: 112 }
      : cardDimensions(s, cardSizes, treeChildren.get(s.id)?.length, !s.project && !!lineageLabel(s),
        !s.project && relationshipsOf(s.id).some((r) => r.type === 'run_association')), area.w, Math.max(180, area.h)),
  [treeRoots, treeChildren, collapsed, cardSizes, area.w, area.h, !!selectedId]);
  const { ordered, positions: pos, edges, dots, width, height, mode, entering, leaving } = useTreePresence(geometry);
  const relations = useMemo(() => relationshipsFor(pid).flatMap((r) => {
    // Assignment records are anchored to their recorded owner, never made into tree nodes.
    const target = r.type === 'assignment_owner' ? getAssignment(r.to)?.owner_session_id : r.to;
    return r.type !== 'run_association' && geometry.positions.has(r.from) && geometry.positions.has(target)
      ? [{ ...r, target }] : [];
  }), [pid, geometry]);
  const styles = [...new Set([...edges.map((e) => e.grouping ? 'project' : 'ancestry'),
    ...relations.map((r) => r.type)])];
  const fit = { scale: geometry.scale, x: Math.max(0, (area.w - width * geometry.scale) / 2), y: 0 };
  const view = manual || fit;
  const current = useRef(view);
  current.current = view;
  const manualRef = useRef(false);
  manualRef.current = !!manual;
  const previousGeometry = useRef(null);
  // Exit cards keep old positions for animation, never for routing or obstacles.
  const extent = useMemo(() => [...geometry.positions.values()], [geometry]);
  const active = useMemo(() => new Set([selectedId, hovered, focused].filter(Boolean)), [selectedId, hovered, focused]);
  const routeRelation = useMemo(() => createRelationshipRouter(extent, view.scale), [extent, view.scale]);
  const overlays = useMemo(() => relations.filter((r) => showRelations || active.has(r.from) || active.has(r.target))
    .flatMap((r, i) => {
      const line = routeRelation(geometry.positions.get(r.from), geometry.positions.get(r.target), RELATION_LABELS[r.type], i);
      // The detail panel still lists relationships that have no clear route this frame.
      return line ? [{ ...r, ...line }] : [];
    }), [showRelations, active, relations, routeRelation]);
  const related = new Set(overlays.flatMap((r) => [r.from, r.target]));
  const stageWidth = Math.max(width, ...overlays.map((r) => r.labelBox.x + r.labelBox.w + 24));
  const stageHeight = Math.max(height, ...overlays.map((r) => r.labelBox.y + r.labelBox.h + 24));

  // ResizeObserver includes sidebar and drawer changes, not just window resizes.
  useLayoutEffect(() => {
    const el = viewport.current;
    const measure = () => {
      const { top, left } = el.getBoundingClientRect();
      const h = Math.max(180, innerHeight - top - 56);
      el.style.height = `${h}px`;
      setArea((old) => old.w === el.clientWidth && old.h === h && old.x === left && old.y === top
        ? old : { w: el.clientWidth, h, x: left, y: top });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    observer.observe(el.closest('.workspace').querySelector('.toolbar'));
    addEventListener('resize', measure);
    return () => { observer.disconnect(); removeEventListener('resize', measure); };
  }, []);

  const startManual = () => {
    const old = previousGeometry.current;
    if (!manualRef.current && old) {
      old.scrollLeft = viewport.current.scrollLeft;
      old.scrollTop = viewport.current.scrollTop;
    }
    manualRef.current = true;
  };
  const move = (next, reflow = false) => {
    startManual();
    current.current = next;
    setManual({ ...next, reflow });
  };
  const reset = () => {
    manualRef.current = false;
    setManual(null);
    viewport.current.scrollTo(0, 0);
  };
  const zoom = (factor, x, y) => {
    const el = viewport.current;
    const old = current.current;
    const scale = clamp(old.scale * factor);
    const px = x + el.scrollLeft;
    const py = y + el.scrollTop;
    move({ scale, x: px - (px - old.x) * scale / old.scale, y: py - (py - old.y) * scale / old.scale });
  };
  const zoomCentre = (factor) => zoom(factor, area.w / 2, area.h / 2);
  const pan = (dx, dy) => { const v = current.current; move({ ...v, x: v.x + dx, y: v.y + dy }); };

  // A non-passive listener is needed to consume browser pinch zoom.
  useEffect(() => {
    const el = viewport.current;
    const wheel = (e) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        const b = el.getBoundingClientRect();
        zoom(Math.exp(-e.deltaY * 0.002), e.clientX - b.left, e.clientY - b.top);
      } else {
        startManual();
        setManual(current.current);
        el.scrollTop += e.deltaY;
        el.scrollLeft += e.deltaX;
      }
    };
    el.addEventListener('wheel', wheel, { passive: false });
    return () => el.removeEventListener('wheel', wheel);
  });

  useLayoutEffect(() => {
    const old = previousGeometry.current;
    const el = viewport.current;
    // Only manual reflow needs a scroll snapshot; reading it here otherwise forces a full layout during expansion.
    previousGeometry.current = { pos, area, selectedId,
      scrollLeft: manualRef.current ? el.scrollLeft : old?.scrollLeft || 0,
      scrollTop: manualRef.current ? el.scrollTop : old?.scrollTop || 0 };
    if (!manualRef.current || !old || old.pos === pos) return;
    const focused = document.activeElement?.closest('[data-session-id]')?.dataset.sessionId;
    const v = current.current;
    const id = [selectedId, focused, old.selectedId, ...ordered].find((key) => {
      const p = old.pos.get(key);
      return p && pos.has(key) && (key === selectedId || key === focused
        || p.y * v.scale + v.y >= el.scrollTop && p.y * v.scale + v.y < el.scrollTop + area.h);
    });
    if (!id) return;
    const a = old.pos.get(id);
    const b = pos.get(id);
    const dx = (a.x - b.x) * v.scale + old.area.x - area.x - old.scrollLeft + el.scrollLeft;
    const dy = (a.y - b.y) * v.scale + old.area.y - area.y - old.scrollTop + el.scrollTop;
    if (dx || dy) move({ ...v, x: v.x + dx, y: v.y + dy }, true);
  }, [pos]);

  // One selection can be revealed after its ancestors mount or a drawer resizes.
  const scrolledSelection = useRef(null);
  useLayoutEffect(() => {
    if (!selectedId) { scrolledSelection.current = null; return; }
    const el = viewport.current;
    const p = pos.get(selectedId);
    const key = `${selectedId}:${area.w}:${mode}`;
    if (!p || scrolledSelection.current === key
      || manualRef.current && scrolledSelection.current?.startsWith(`${selectedId}:`)) return;
    scrolledSelection.current = key;
    const v = current.current;
    const left = p.x * v.scale + v.x - el.scrollLeft;
    const top = p.y * v.scale + v.y - el.scrollTop;
    const right = left + p.w * v.scale;
    const bottom = top + p.h * v.scale;
    const dx = left < 8 ? 8 - left : right > area.w - 8 ? area.w - 8 - right : 0;
    const dy = top < 8 ? 8 - top : bottom > area.h - 8 ? area.h - 8 - bottom : 0;
    if (dx || dy) {
      if (manualRef.current) move({ ...v, x: v.x + dx, y: v.y + dy });
      else { el.scrollLeft -= dx; el.scrollTop -= dy; }
    }
  }, [selectedId, area, pos, mode]);

  useLayoutEffect(() => {
    if (area.w !== viewport.current.clientWidth) return;
    performance.mark('odin:tree-fitted');
    if (!performance.getEntriesByName('odin:tree-rendered').length) performance.mark('odin:tree-rendered');
  }, [geometry, area]);

  const pointers = useRef(new Map());
  const gesture = useRef(null);
  const suppressClick = useRef(false);
  const cardPress = useRef(null);
  const startGesture = () => {
    const ps = [...pointers.current.values()];
    gesture.current = ps.length === 2 ? { x: (ps[0].x + ps[1].x) / 2, y: (ps[0].y + ps[1].y) / 2,
      distance: Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y), pinch: true }
      : ps.length ? { ...ps[0], pinch: false, moved: false } : null;
  };
  const pointerDown = (e) => {
    if (e.button !== 0) return;
    suppressClick.current = false;
    if (e.target.closest('.card, .project-node, button, a')) {
      cardPress.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
      return;
    }
    viewport.current.focus({ preventScroll: true });
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    viewport.current.setPointerCapture(e.pointerId);
    startGesture();
  };
  const pointerMove = (e) => {
    const press = cardPress.current;
    if (press?.id === e.pointerId) {
      if (Math.hypot(e.clientX - press.x, e.clientY - press.y) >= 4) suppressClick.current = true;
      return;
    }
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const g = gesture.current;
    if (!g) return;
    if (g.pinch && pointers.current.size === 2) {
      const ps = [...pointers.current.values()];
      const x = (ps[0].x + ps[1].x) / 2;
      const y = (ps[0].y + ps[1].y) / 2;
      const distance = Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y);
      const b = viewport.current.getBoundingClientRect();
      zoom(distance / Math.max(1, g.distance), g.x - b.left, g.y - b.top);
      pan(x - g.x, y - g.y);
      gesture.current = { x, y, distance, pinch: true };
      suppressClick.current = true;
    } else {
      const dx = e.clientX - g.x;
      const dy = e.clientY - g.y;
      if (!g.moved && Math.hypot(dx, dy) < 4) return;
      pan(dx, dy);
      gesture.current = { x: e.clientX, y: e.clientY, moved: true };
      suppressClick.current = true;
    }
  };
  const pointerUp = (e) => {
    cardPress.current = null;
    if (e.type === 'pointercancel') suppressClick.current = false;
    pointers.current.delete(e.pointerId);
    startGesture();
  };
  const keyDown = (e) => {
    if (e.target !== e.currentTarget) return;
    switch (e.key) {
      case '+': case '=': zoomCentre(1.2); break;
      case '-': zoomCentre(1 / 1.2); break;
      case '0': reset(); break;
      case 'ArrowLeft': pan(48, 0); break;
      case 'ArrowRight': pan(-48, 0); break;
      case 'ArrowUp': pan(0, 48); break;
      case 'ArrowDown': pan(0, -48); break;
      default: return;
    }
    e.preventDefault();
  };

  return <div class="tree-wrap">
    <p id="tree-instructions" class="sr-only">{INSTRUCTIONS}</p>
    <div class="tree-view" ref={viewport} data-testid="tree-view" data-scale={view.scale} data-mode={mode}
      data-layout-width={area.w} data-layout-height={area.h} data-layout-x={area.x} data-layout-y={area.y}
      data-manual={!!manual} role="region" aria-label="Agent tree canvas" aria-describedby="tree-instructions" tabIndex={0}
      onScroll={(e) => {
        const old = previousGeometry.current;
        const el = e.currentTarget;
        // A resize may clamp scroll offsets before the next layout commits.
        if (old && old.area.w === el.clientWidth && Math.abs(old.area.h - el.clientHeight) < 1) {
          old.scrollLeft = el.scrollLeft;
          old.scrollTop = el.scrollTop;
        }
      }}
      onKeyDown={keyDown} onPointerDown={pointerDown} onPointerMove={pointerMove}
      onPointerUp={pointerUp} onPointerCancel={pointerUp} onLostPointerCapture={pointerUp}
      onClickCapture={(e) => { if (suppressClick.current) { e.stopPropagation(); suppressClick.current = false; } }}>
      <div class="tree-space" style={{ width: Math.max(area.w, stageWidth * view.scale + view.x),
        height: Math.max(area.h, stageHeight * view.scale + view.y) }}>
        {area.w > 0 && <div class={`tree-stage ${manual ? 'manual-view' : ''} ${manual?.reflow ? 'reflow-view' : ''}`}
          style={{ width: stageWidth, height: stageHeight,
            transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}>
          <svg class="tree-edges" width={stageWidth} height={stageHeight} aria-hidden="true">
            {edges.map((e) => {
              // Only animating ancestry edges get a unit path length: it would turn the dashed grouping line solid.
              const motion = e.grouping ? '' : entering.has(e.to) ? ' edge-enter' : leaving.has(e.to) ? ' edge-leave' : '';
              const shared = e.grouping && !leaving.has(e.to);
              return <path key={edgeKey(e)}
              class={`${e.grouping ? 'project-edge' : 'ancestry-edge'} ${e.kind}${motion}`}
              data-from={nodeLabel(e.ancestryFrom || e.from)} data-to={nodeLabel(e.to)}
              data-via={e.ancestryFrom ? nodeLabel(e.from) : undefined}
              data-project-id={pos.get(e.to).s.project_id}
              data-muted={highlight && pos.get(e.to).s.project_id !== highlight ? 'true' : undefined}
              style={shared ? { strokeDashoffset: e.paintOffset } : undefined}
              pathLength={motion ? 1 : undefined} d={shared ? e.paintD : e.d} />;
            })}
            {dots.map((d) => <circle key={storedNodeId(d.id)} class="port-dot" data-parent={nodeLabel(d.id)}
              cx={d.x} cy={d.y} r={4.5} />)}
          </svg>
          <svg class="tree-overlays" width={stageWidth} height={stageHeight} aria-hidden="true">
            {overlays.map((r) => {
              const b = r.labelBox;
              return <g key={r.id} class={`relation-edge relation-${r.type}`} data-type={r.type}
                data-from={r.from} data-to={r.to} data-target={r.target}>
                <defs><marker id={`arrow-${r.id}`} viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="arrowhead" /></marker></defs>
                <path d={r.d} marker-end={`url(#arrow-${r.id})`} />
                <g class="relation-label" data-testid="relationship-label" transform={`translate(${b.x},${b.y})`}>
                  <rect width={b.w} height={b.h} rx={b.h / 2} />
                  <text x={b.w / 2} y={b.h / 2} dominant-baseline="central" text-anchor="middle"
                    style={{ fontSize: 11 * r.fontScale }}>{RELATION_LABELS[r.type]}</text>
                </g>
              </g>;
            })}
          </svg>
          {ordered.map((id) => {
            const p = pos.get(id);
            const style = { left: p.x, top: p.y, width: p.w, height: p.h };
            const muted = highlight && p.s.project_id && p.s.project_id !== highlight;
            if (p.s.project) return <ProjectNode key={storedNodeId(id)} project={p.s.project} style={style}
              expanded={!collapsed.has(id)} muted={muted} onToggle={() => onToggle(id)} />;
            return <SessionCard key={storedNodeId(id)} session={p.s} childMap={treeChildren} style={style} muted={muted}
              selected={id === selectedId} related={related.has(id)}
              onHover={setHovered} onFocusCard={setFocused} compactExecutive={!!pid && id === executive?.id}
              cardExpanded={pid && id === executive?.id || cardIsExpanded(p.s, cardSizes)} onSizeToggle={onSizeToggle}
              expanded={!collapsed.has(id)} childCount={(treeChildren.get(id) || []).length}
              entering={entering.has(id)} leaving={leaving.has(id)} onSelect={onSelect} onToggle={onToggle}
              showRelations={showRelations || active.has(id)} />;
          })}

        </div>}
      </div>
    </div>
    <RelationshipKey styles={styles} prefs={prefs} />
    <div class="canvas-bottom-right">{driver}
      <div class="canvas-controls" role="group" aria-label="Canvas view">
        {manual && <button type="button" onClick={reset}>Reset view</button>}
        <button type="button" aria-label="Zoom out" onClick={() => zoomCentre(1 / 1.2)}>−</button>
        <button type="button" aria-label="Zoom in" onClick={() => zoomCentre(1.2)}>+</button>
      </div>
    </div>
  </div>;
}
