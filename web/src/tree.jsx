import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { RELATION_LABELS, descendants, getExecutive, relationshipsFor } from './data.js';
import { ProjectNode } from './project-node.jsx';
import { SessionCard } from './card.jsx';

const CARD_W = 220;
const CARD_H = 182;
const FAN_X = 32; // gap between siblings in a first-level row
const FAN_Y = 56; // vertical gap: parent bottom to the first-level row
const ROW_GAP = 48; // gap between root regions
const STACK_GAP = 26; // vertical gap between cards in a stacked column
const RAIL = 14; // stacked rail distance left of the column's left edge
const JOG = 10; // drop from a stacked parent's port to its rail jog
const PORT_IN = 10; // stacked-parent port inset from the card's left edge
const TICK_Y = 40; // elbow height below a stacked child's top edge
const DOT = 8; // port dot centre below a parent's bottom edge
const PAD = 24;

// Project roots share a row. Recorded descendants stack in each root's
// column, so expanding a branch does not move other projects sideways.
function sessionLayout(roots, childMap, collapsed) {
  const pos = new Map();
  const ordered = [];
  const edges = [];
  const dots = [];
  const kidsOf = (id) => (collapsed.has(id) ? [] : (childMap.get(id) || []));

  // Descendants of `id`, depth-first, stacked in the column at `x` starting
  // at `y`. Returns the y below the last card (bottom + STACK_GAP).
  const placeStack = (id, x, y) => {
    const kids = kidsOf(id);
    if (kids.length) dots.push({ id, x: pos.get(id).x + PORT_IN, y: pos.get(id).y + CARD_H + DOT });
    for (const c of kids) {
      pos.set(c.id, { x, y, s: c });
      ordered.push(c.id);
      edges.push({ from: id, to: c.id, kind: 'stack' });
      y = placeStack(c.id, x, y + CARD_H + STACK_GAP);
    }
    return y;
  };

  let cursorX = PAD;
  let maxBottom = PAD + CARD_H;
  for (const root of roots) {
    const rx = cursorX;
    pos.set(root.id, { x: rx, y: PAD, s: root });
    ordered.push(root.id);
    const bottom = Math.max(PAD + CARD_H, placeStack(root.id, rx, PAD + CARD_H + STACK_GAP) - STACK_GAP);
    maxBottom = Math.max(maxBottom, bottom);
    cursorX += CARD_W + FAN_X;
  }
  const width = ordered.length ? cursorX - FAN_X + PAD : PAD * 2;
  const height = Math.max(maxBottom + PAD, PAD * 2);
  return { ordered, pos, edges, dots, width, height };
}

const PROJECT_W = 480;
const PROJECT_H = 44;

// Project regions keep the recorded forest intact below a separate grouping row.
function layout(roots, childMap, collapsed) {
  const executive = roots[0] && !roots[0].project ? roots[0] : null;
  const projects = executive ? (collapsed.has(executive.id) ? [] : childMap.get(executive.id) || []) : roots;
  const pos = new Map();
  const ordered = [];
  const edges = [];
  const dots = [];
  const projectY = executive ? PAD + CARD_H + FAN_Y : PAD;
  let cursorX = PAD;
  let bottom = projectY + PROJECT_H;
  for (const node of projects) {
    const local = sessionLayout(collapsed.has(node.id) ? [] : childMap.get(node.id) || [], childMap, collapsed);
    const regionW = Math.max(PROJECT_W, local.width);
    const x = cursorX + (regionW - PROJECT_W) / 2;
    pos.set(node.id, { x, y: projectY, s: node, w: PROJECT_W, h: PROJECT_H });
    ordered.push(node.id);
    const dx = cursorX + (regionW - local.width) / 2;
    const dy = projectY + PROJECT_H + FAN_Y - PAD;
    for (const id of local.ordered) {
      pos.set(id, { ...local.pos.get(id), x: local.pos.get(id).x + dx, y: local.pos.get(id).y + dy });
      ordered.push(id);
    }
    edges.push(...local.edges);
    dots.push(...local.dots.map((d) => ({ ...d, x: d.x + dx, y: d.y + dy })));
    if (!collapsed.has(node.id)) {
      for (const root of childMap.get(node.id) || []) {
        edges.push({ from: node.id, to: root.id, kind: 'fan',
          ancestryFrom: root.parent_session_id === getExecutive()?.id ? getExecutive().id : null });
      }
      if ((childMap.get(node.id) || []).length) dots.push({ id: node.id, x: x + PROJECT_W / 2, y: projectY + PROJECT_H + DOT });
    }
    if (executive) edges.push({ from: executive.id, to: node.id, kind: 'fan', grouping: true });
    bottom = Math.max(bottom, local.ordered.length ? dy + local.height : projectY + PROJECT_H);
    cursorX += regionW + ROW_GAP;
  }
  const width = Math.max(CARD_W + PAD * 2, cursorX - ROW_GAP + PAD);
  if (executive) {
    pos.set(executive.id, { x: (width - CARD_W) / 2, y: PAD, s: executive });
    ordered.unshift(executive.id);
    if (projects.length) dots.push({ id: executive.id, x: width / 2, y: PAD + CARD_H + DOT });
  }
  return { ordered, pos, edges, dots, width, height: bottom + PAD };
}

// First-level fan: down from the port dot, across the shared bus, down into
// the child's top edge. Right angles only.
function fanPath(p, c) {
  const pcx = p.x + (p.w || CARD_W) / 2;
  const ccx = c.x + (c.w || CARD_W) / 2;
  const y0 = p.y + (p.h || CARD_H) + DOT;
  if (Math.abs(ccx - pcx) < 0.5) return `M${pcx},${y0} L${ccx},${c.y}`;
  const busY = p.y + (p.h || CARD_H) + FAN_Y / 2;
  return `M${pcx},${y0} L${pcx},${busY} L${ccx},${busY} L${ccx},${c.y}`;
}

// Stacked level: from the port under the parent's left edge, a short jog to
// the vertical rail in the column's left margin, down the rail, then right
// into the child's left edge. Right angles only.
function stackPath(p, c) {
  const px = p.x + PORT_IN;
  const jogY = p.y + (p.h || CARD_H) + DOT + JOG;
  const railX = c.x - RAIL;
  const tickY = c.y + TICK_Y;
  return `M${px},${p.y + (p.h || CARD_H) + DOT} L${px},${jogY} L${railX},${jogY} L${railX},${tickY} L${c.x},${tickY}`;
}

function relationPath(a, b) {
  const x1 = a.x + CARD_W;
  const y1 = a.y + CARD_H / 2;
  const x2 = b.x + (b.x > a.x ? 0 : CARD_W);
  const y2 = b.y + (b.h || CARD_H) / 2 + 12;
  const cx = (x1 + x2) / 2;
  const cy = Math.min(y1, y2) - 40;
  return { d: `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`, lx: cx, ly: (Math.min(y1, y2) + cy) / 2 + 8 };
}

// Height of the page chrome pinned above the canvas: the sticky header plus
// the workspace toolbar. The canvas scrolls under both.
function pinnedTop(el) {
  const chrome = el.closest('.app')?.querySelector('.chrome');
  const toolbar = el.closest('.workspace')?.querySelector('.toolbar');
  return (chrome?.offsetHeight || 0) + (toolbar?.offsetHeight || 0);
}

const edgeKey = (e) => `${e.from}>${e.to}`;

export function TreeView({ pid, roots, childMap, collapsed, selectedId, onSelect, onToggle, showRelations, highlight }) {
  const { ordered, pos, edges, dots, width, height } = useMemo(
    () => layout(roots, childMap, collapsed), [roots, childMap, collapsed]);
  const relations = useMemo(
    () => relationshipsFor(pid).filter((r) => (r.type === 'review' || r.type === 'delegation') && pos.has(r.from) && pos.has(r.to)),
    [pid, pos],
  );
  const viewport = useRef(null);
  const [scale, setScale] = useState(1);
  const pendingScroll = useRef(null);

  // Cards and connectors that mount after the first render — sessions a
  // delivered event added, or children an expand reveals — enter with an
  // animation. The first paint never animates.
  const seen = useRef(null);
  const seenEdges = useRef(null);
  if (seen.current === null) {
    seen.current = new Set(ordered);
    seenEdges.current = new Set(edges.map(edgeKey));
  }
  const entering = new Set(ordered.filter((id) => !seen.current.has(id)));
  const enteringEdges = new Set(edges.map(edgeKey).filter((k) => !seenEdges.current.has(k)));
  useEffect(() => {
    seen.current = new Set(ordered);
    seenEdges.current = new Set(edges.map(edgeKey));
  });

  // The canvas grows with the tree and the page scrolls, so the usable
  // region is the window minus the pinned chrome and the side padding —
  // and minus a detail drawer's width when one is open.
  const viewArea = () => {
    const el = viewport.current;
    const host = el?.parentElement;
    if (!el || !host) return { w: 800, h: 600 };
    const top = pinnedTop(el);
    return {
      w: Math.max(120, Math.min(host.clientWidth, innerWidth - 16)),
      h: Math.max(120, innerHeight - top - 16),
      top,
    };
  };

  const fitTo = (ids) => {
    const boxes = ids.map((id) => pos.get(id)).filter(Boolean);
    const el = viewport.current;
    if (!boxes.length || !el) return;
    const x0 = Math.min(...boxes.map((b) => b.x)) - PAD;
    const y0 = Math.min(...boxes.map((b) => b.y)) - PAD;
    const x1 = Math.max(...boxes.map((b) => b.x + (b.w || CARD_W))) + PAD;
    const y1 = Math.max(...boxes.map((b) => b.y + (b.h || CARD_H))) + PAD;
    const area = viewArea();
    const s = Math.max(0.1, Math.min(1, area.w / (x1 - x0), area.h / (y1 - y0)));
    const origin = el.getBoundingClientRect();
    pendingScroll.current = {
      left: scrollX,
      canvasLeft: x0 * s,
      top: origin.top + scrollY + y0 * s - area.top - 4,
    };
    // Scroll now — the canvas origin does not move when the scale commits —
    // and again after the render in case the scroll range shifted.
    scrollTo({ left: pendingScroll.current.left, top: pendingScroll.current.top });
    setScale(s);
  };
  const fitBranch = () => {
    if (!selectedId) return;
    fitTo([selectedId, ...descendants(selectedId, childMap).map((s) => s.id)]);
  };

  useEffect(() => {
    if (pendingScroll.current) {
      const target = pendingScroll.current;
      pendingScroll.current = null;
      viewport.current.parentElement.scrollLeft = target.canvasLeft;
      scrollTo({ left: target.left, top: target.top });
    }
  });

  // Start on the whole forest when it fits at a readable scale, else at
  // actual size centred on the first root.
  useEffect(() => {
    const el = viewport.current;
    if (!el || selectedId) return;
    const area = viewArea();
    const s = Math.min(1, area.w / width, area.h / height);
    if (s >= 0.7) setScale(s);
    else el.querySelector('[data-testid="session-card"]')?.scrollIntoView?.({ block: 'nearest', inline: 'center' });
  }, []);

  // Timing mark for the large-tree check: first commit of the tree view.
  useEffect(() => { performance.mark('odin:tree-rendered'); }, []);

  // A deep link may reveal its card one render after expanding ancestors.
  // Scroll once per selection; projection updates preserve reading position.
  const scrolledSelection = useRef(null);
  useEffect(() => {
    if (!selectedId) { scrolledSelection.current = null; return; }
    if (scrolledSelection.current === selectedId) return;
    const card = viewport.current?.querySelector(`[data-testid="session-card"][data-session-id="${CSS.escape(selectedId)}"]`);
    if (card) {
      card.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
      scrolledSelection.current = selectedId;
    }
  });

  return (
    <div class="tree-wrap">
      <div class="tree-actions">
        <button type="button" onClick={fitBranch} disabled={!selectedId}>Fit branch</button>
        <button type="button" onClick={() => fitTo(ordered)}>Fit all</button>
        <button type="button" onClick={() => setScale(1)}>Actual size</button>
        <span class="muted" aria-live="polite">Zoom {Math.round(scale * 100)}%</span>
        <span class="legend">
          <span class="legend-line project" /> project <span class="legend-line solid" /> started (ancestry)
          <span class="legend-line dashed" /> typed relationship
        </span>
      </div>
      <div class="tree-scroller">
      <div class="tree-view" ref={viewport} data-testid="tree-view" data-scale={scale}
        style={{ width: Math.max(1, width * scale), height: Math.max(1, height * scale) }}>
        <div class="tree-stage" style={{ width, height, transform: `scale(${scale})` }}>
          <svg class="tree-edges" width={width} height={height} aria-hidden="true">
            {edges.map((e) => {
              const grouping = e.grouping || (pos.get(e.from).s.project && !e.ancestryFrom);
              const projectId = pos.get(e.to).s.project_id;
              return <path key={`a-${e.to}`}
                class={`${grouping ? 'project-edge' : 'ancestry-edge'} ${e.kind}`
                  + (enteringEdges.has(edgeKey(e)) ? ' edge-enter' : '')}
                data-from={e.ancestryFrom || e.from} data-to={e.to} data-via={e.ancestryFrom ? e.from : undefined}
                data-project-id={projectId} data-muted={highlight && projectId !== highlight ? 'true' : undefined}
                pathLength={grouping ? undefined : 1}
                d={(e.kind === 'fan' ? fanPath : stackPath)(pos.get(e.from), pos.get(e.to))} />;
            })}
            {showRelations && relations.map((r) => {
              const p = relationPath(pos.get(r.from), pos.get(r.to));
              // Each overlay carries its own arrowhead marker inside the
              // .relation-edge group, so the accent fill stays scoped to
              // the overlay.
              return (
                <g key={r.id} class={`relation-edge relation-${r.type}`} data-type={r.type} data-from={r.from} data-to={r.to}>
                  <marker id={`arrow-${r.id}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0,0 L10,5 L0,10 z" class="arrowhead" />
                  </marker>
                  <path d={p.d} marker-end={`url(#arrow-${r.id})`} />
                  <text x={p.lx} y={p.ly} text-anchor="middle">{RELATION_LABELS[r.type]}</text>
                </g>
              );
            })}
            {dots.map((d) => (
              <circle key={`p-${d.id}`} class="port-dot" data-parent={d.id} cx={d.x} cy={d.y} r={4.5} />
            ))}
          </svg>
          {ordered.map((id) => {
            const p = pos.get(id);
            const kids = childMap.get(id) || [];
            if (p.s.project) return <ProjectNode key={id} project={p.s.project}
              style={{ left: p.x, top: p.y, width: p.w, height: p.h }} expanded={!collapsed.has(id)}
              muted={highlight && p.s.project_id !== highlight} onToggle={() => onToggle(id)} />;
            return (
              <SessionCard key={id} session={p.s} childMap={childMap} style={{ left: p.x, top: p.y, width: CARD_W, height: CARD_H }}
                muted={highlight && p.s.project_id && p.s.project_id !== highlight}
                selected={id === selectedId} expanded={!collapsed.has(id)} childCount={kids.length}
                entering={entering.has(id)} onSelect={onSelect} onToggle={onToggle} />
            );
          })}
        </div>
      </div>
      </div>
    </div>
  );
}
