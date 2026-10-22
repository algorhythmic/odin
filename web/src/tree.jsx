import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { RELATION_LABELS, descendants, relationshipsFor } from './data.js';
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

// The ancestry forest, laid out like the reference: a root's children form
// one horizontal row under it; every deeper level stacks vertically in a
// column aligned with its parent's left edge (one column per first-level
// subtree, in depth-first order). Positions come only from these constants
// and the card size, so connector geometry tracks the layout exactly.
function layout(roots, childMap, collapsed) {
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
    const kids = kidsOf(root.id);
    const rowW = kids.length ? kids.length * CARD_W + (kids.length - 1) * FAN_X : 0;
    const branchW = Math.max(CARD_W, rowW);
    // The root is centred over its children row, like the reference.
    const rx = cursorX + (branchW - CARD_W) / 2;
    pos.set(root.id, { x: rx, y: PAD, s: root });
    ordered.push(root.id);
    let bottom = PAD + CARD_H;
    if (kids.length) {
      dots.push({ id: root.id, x: rx + CARD_W / 2, y: PAD + CARD_H + DOT });
      const rowY = PAD + CARD_H + FAN_Y;
      kids.forEach((k, i) => {
        const kx = cursorX + i * (CARD_W + FAN_X);
        pos.set(k.id, { x: kx, y: rowY, s: k });
        ordered.push(k.id);
        edges.push({ from: root.id, to: k.id, kind: 'fan' });
        bottom = Math.max(bottom, placeStack(k.id, kx, rowY + CARD_H + STACK_GAP) - STACK_GAP, rowY + CARD_H);
      });
    }
    maxBottom = Math.max(maxBottom, bottom);
    cursorX += branchW + ROW_GAP;
  }
  const width = ordered.length ? cursorX - ROW_GAP + PAD : PAD * 2;
  const height = Math.max(maxBottom + PAD, PAD * 2);
  return { ordered, pos, edges, dots, width, height };
}

// First-level fan: down from the port dot, across the shared bus, down into
// the child's top edge. Right angles only.
function fanPath(p, c) {
  const pcx = p.x + CARD_W / 2;
  const ccx = c.x + CARD_W / 2;
  const y0 = p.y + CARD_H + DOT;
  if (Math.abs(ccx - pcx) < 0.5) return `M${pcx},${y0} L${ccx},${c.y}`;
  const busY = p.y + CARD_H + FAN_Y / 2;
  return `M${pcx},${y0} L${pcx},${busY} L${ccx},${busY} L${ccx},${c.y}`;
}

// Stacked level: from the port under the parent's left edge, a short jog to
// the vertical rail in the column's left margin, down the rail, then right
// into the child's left edge. Right angles only.
function stackPath(p, c) {
  const px = p.x + PORT_IN;
  const jogY = p.y + CARD_H + DOT + JOG;
  const railX = c.x - RAIL;
  const tickY = c.y + TICK_Y;
  return `M${px},${p.y + CARD_H + DOT} L${px},${jogY} L${railX},${jogY} L${railX},${tickY} L${c.x},${tickY}`;
}

function relationPath(a, b) {
  const x1 = a.x + CARD_W;
  const y1 = a.y + CARD_H / 2;
  const x2 = b.x + (b.x > a.x ? 0 : CARD_W);
  const y2 = b.y + CARD_H / 2 + 12;
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

export function TreeView({ pid, roots, childMap, collapsed, selectedId, onSelect, onToggle, showRelations }) {
  const { ordered, pos, edges, dots, width, height } = useMemo(
    () => layout(roots, childMap, collapsed), [roots, childMap, collapsed]);
  const relations = useMemo(
    () => relationshipsFor(pid).filter((r) => (r.type === 'review' || r.type === 'delegation') && pos.has(r.from) && pos.has(r.to)),
    [pid, pos],
  );
  const viewport = useRef(null);
  const [scale, setScale] = useState(1);
  const pendingScroll = useRef(null);

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
    const x1 = Math.max(...boxes.map((b) => b.x + CARD_W)) + PAD;
    const y1 = Math.max(...boxes.map((b) => b.y + CARD_H)) + PAD;
    const area = viewArea();
    const s = Math.max(0.35, Math.min(1, area.w / (x1 - x0), area.h / (y1 - y0)));
    const origin = el.getBoundingClientRect();
    pendingScroll.current = {
      left: origin.left + scrollX + x0 * s - 16,
      top: origin.top + scrollY + y0 * s - area.top - 4,
    };
    // Scroll now — the canvas origin does not move when the scale commits —
    // and again after the render in case the scroll range shifted.
    scrollTo(pendingScroll.current);
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
      scrollTo(target);
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

  // Keep the selected card in view without moving the user's scroll otherwise.
  useEffect(() => {
    if (!selectedId) return;
    const card = viewport.current?.querySelector(`[data-testid="session-card"][data-session-id="${CSS.escape(selectedId)}"]`);
    card?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  }, [selectedId]);

  return (
    <div class="tree-wrap">
      <div class="tree-actions">
        <button type="button" onClick={fitBranch} disabled={!selectedId}>Fit branch</button>
        <button type="button" onClick={() => fitTo(ordered)}>Fit all</button>
        <button type="button" onClick={() => setScale(1)}>Actual size</button>
        <span class="muted" aria-live="polite">Zoom {Math.round(scale * 100)}%</span>
        <span class="legend"><span class="legend-line solid" /> started (ancestry) <span class="legend-line dashed" /> typed relationship</span>
      </div>
      <div class="tree-view" ref={viewport} data-testid="tree-view" data-scale={scale}
        style={{ width: Math.max(1, width * scale), height: Math.max(1, height * scale) }}>
        <div class="tree-stage" style={{ width, height, transform: `scale(${scale})` }}>
          <svg class="tree-edges" width={width} height={height} aria-hidden="true">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" class="arrowhead" />
              </marker>
            </defs>
            {edges.map((e) => (
              <path key={`a-${e.to}`} class={`ancestry-edge ${e.kind}`} data-from={e.from} data-to={e.to}
                d={(e.kind === 'fan' ? fanPath : stackPath)(pos.get(e.from), pos.get(e.to))} />
            ))}
            {showRelations && relations.map((r) => {
              const p = relationPath(pos.get(r.from), pos.get(r.to));
              return (
                <g key={r.id} class={`relation-edge relation-${r.type}`} data-type={r.type} data-from={r.from} data-to={r.to}>
                  <path d={p.d} marker-end="url(#arrow)" />
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
            return (
              <SessionCard key={id} session={p.s} childMap={childMap} style={{ left: p.x, top: p.y, width: CARD_W, height: CARD_H }}
                selected={id === selectedId} expanded={!collapsed.has(id)} childCount={kids.length}
                onSelect={onSelect} onToggle={onToggle} />
            );
          })}
        </div>
      </div>
    </div>
  );
}
