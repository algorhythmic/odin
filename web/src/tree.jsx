import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { hierarchy, tree } from 'd3-hierarchy';
import { RELATION_LABELS, relationshipsFor } from './data.js';
import { SessionCard } from './card.jsx';

const CARD_W = 220;
const CARD_H = 172;
const GAP_X = 24;
const GAP_Y = 60;
const PAD = 24;

// Tidy-tree layout of the ancestry forest. A virtual root joins the
// recorded roots for layout only; it is never drawn and never an edge.
function layout(roots, childMap, collapsed) {
  const forest = { id: '__forest', virtual: true, kids: roots };
  const root = hierarchy(forest, (d) => (d.virtual ? d.kids : (collapsed.has(d.id) ? null : childMap.get(d.id))));
  tree().nodeSize([CARD_W + GAP_X, CARD_H + GAP_Y]).separation((a, b) => (a.parent === b.parent ? 1 : 1.2))(root);
  const nodes = root.descendants().filter((n) => !n.data.virtual);
  const minX = Math.min(...nodes.map((n) => n.x));
  const maxX = Math.max(...nodes.map((n) => n.x));
  const maxDepth = Math.max(...nodes.map((n) => n.depth));
  const pos = new Map();
  for (const n of nodes) {
    pos.set(n.data.id, { x: n.x - minX + PAD, y: (n.depth - 1) * (CARD_H + GAP_Y) + PAD, node: n });
  }
  return {
    nodes,
    pos,
    width: maxX - minX + CARD_W + PAD * 2,
    height: maxDepth * (CARD_H + GAP_Y) - GAP_Y + PAD * 2,
  };
}

function ancestryPath(a, b) {
  const x1 = a.x + CARD_W / 2;
  const y1 = a.y + CARD_H;
  const x2 = b.x + CARD_W / 2;
  const y2 = b.y;
  const my = (y1 + y2) / 2;
  return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
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

export function TreeView({ pid, roots, childMap, collapsed, selectedId, onSelect, onToggle, showRelations }) {
  const { nodes, pos, width, height } = useMemo(() => layout(roots, childMap, collapsed), [roots, childMap, collapsed]);
  const relations = useMemo(
    () => relationshipsFor(pid).filter((r) => (r.type === 'review' || r.type === 'delegation') && pos.has(r.from) && pos.has(r.to)),
    [pid, pos],
  );
  const viewport = useRef(null);
  const [scale, setScale] = useState(1);
  const pendingScroll = useRef(null);

  const fitTo = (ids) => {
    const boxes = ids.map((id) => pos.get(id)).filter(Boolean);
    const el = viewport.current;
    if (!boxes.length || !el) return;
    const x0 = Math.min(...boxes.map((b) => b.x)) - PAD;
    const y0 = Math.min(...boxes.map((b) => b.y)) - PAD;
    const x1 = Math.max(...boxes.map((b) => b.x + CARD_W)) + PAD;
    const y1 = Math.max(...boxes.map((b) => b.y + CARD_H)) + PAD;
    const s = Math.max(0.35, Math.min(1, el.clientWidth / (x1 - x0), el.clientHeight / (y1 - y0)));
    pendingScroll.current = { left: x0 * s, top: y0 * s };
    setScale(s);
  };
  const fitBranch = () => {
    if (!selectedId) return;
    const sel = pos.get(selectedId)?.node;
    if (sel) fitTo(sel.descendants().map((n) => n.data.id));
  };

  useEffect(() => {
    const el = viewport.current;
    if (el && pendingScroll.current) {
      el.scrollTo(pendingScroll.current);
      pendingScroll.current = null;
    }
  });

  // Start on the whole forest when it fits at a readable scale, else at
  // actual size centred on the first root.
  useEffect(() => {
    const el = viewport.current;
    if (!el || selectedId) return;
    const s = Math.min(1, el.clientWidth / width, el.clientHeight / height);
    if (s >= 0.7) setScale(s);
    else el.querySelector('[data-testid="session-card"]')?.scrollIntoView?.({ block: 'nearest', inline: 'center' });
  }, []);

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
        <button type="button" onClick={() => fitTo(nodes.map((n) => n.data.id))}>Fit all</button>
        <button type="button" onClick={() => setScale(1)}>Actual size</button>
        <span class="muted" aria-live="polite">Zoom {Math.round(scale * 100)}%</span>
        <span class="legend"><span class="legend-line solid" /> started (ancestry) <span class="legend-line dashed" /> typed relationship</span>
      </div>
      <div class="tree-viewport" ref={viewport} data-testid="tree-view" data-scale={scale}>
        <div style={{ width: width * scale, height: height * scale, position: 'relative' }}>
          <div class="tree-stage" style={{ width, height, transform: `scale(${scale})` }}>
            <svg class="tree-edges" width={width} height={height} aria-hidden="true">
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" class="arrowhead" />
                </marker>
              </defs>
              {nodes.filter((n) => !n.parent.data.virtual).map((n) => (
                <path key={`a-${n.data.id}`} class="ancestry-edge" data-from={n.parent.data.id} data-to={n.data.id}
                  d={ancestryPath(pos.get(n.parent.data.id), pos.get(n.data.id))} />
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
            </svg>
            {nodes.map((n) => {
              const p = pos.get(n.data.id);
              const kids = childMap.get(n.data.id) || [];
              return (
                <SessionCard key={n.data.id} session={n.data} childMap={childMap} style={{ left: p.x, top: p.y, width: CARD_W, height: CARD_H }}
                  selected={n.data.id === selectedId} expanded={!collapsed.has(n.data.id)} childCount={kids.length}
                  onSelect={onSelect} onToggle={onToggle} />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
