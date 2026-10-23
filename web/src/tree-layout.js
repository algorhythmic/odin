export const CARD = { width: 220, height: 182, projectWidth: 300, projectHeight: 60 };
export const MIN_READABLE = 0.75;
const PAD = 16;
const GAP = 24;
const LEVEL = 32;
const INDENT = 24;

// Keep the frontier's extremes and sample its middle, so narrow and short shapes survive.
function pareto(shapes) {
  const sorted = shapes.sort((a, b) => a.width - b.width || a.height - b.height);
  let height = Infinity;
  const frontier = sorted.filter((s) => {
    if (s.height >= height) return false;
    height = s.height;
    return true;
  });
  if (frontier.length <= 8) return frontier;
  return Array.from({ length: 8 }, (_, i) => frontier[Math.round(i * (frontier.length - 1) / 7)]);
}

// Geometry consumes admitted parents and caller-supplied node sizes; it never chooses ancestry.
export function fitTree({ roots, children, collapsed = new Set(), executiveId }, size = CARD,
  viewportWidth = 800, viewportHeight = 900) {
  const dimensions = (s) => typeof size === 'function' ? size(s) : s.project
    ? { w: size.projectWidth, h: size.projectHeight } : { w: size.width, h: size.height };
  const kids = (s) => collapsed.has(s.id) ? [] : children.get(s.id) || [];
  const measure = (s) => {
    const own = s.virtual ? { w: 0, h: 0 } : dimensions(s);
    const cs = kids(s).map(measure);
    if (!cs.length) return [{ s, ...own, width: own.w, height: own.h, picks: [], kind: 'leaf' }];
    const shapes = [];
    const n = cs.length;
    const columns = [...new Set([1, 2, 3, 4, 5, 6, 8, Math.ceil(Math.sqrt(n)), n])].filter((k) => k <= n);
    for (const k of columns) {
      // A bounded beam combines different child shapes without a Cartesian explosion.
      let beam = [{ width: 0, height: 0, rowW: 0, rowH: 0, finishedH: 0, picks: [] }];
      for (let i = 0; i < n; i++) {
        const next = [];
        for (const b of beam) for (const c of cs[i]) {
          const newRow = i % k === 0;
          const finishedH = newRow && i ? b.finishedH + b.rowH + LEVEL : b.finishedH;
          const rowW = newRow ? c.width : b.rowW + GAP + c.width;
          const rowH = newRow ? c.height : Math.max(b.rowH, c.height);
          next.push({ width: Math.max(b.width, rowW), height: finishedH + rowH,
            rowW, rowH, finishedH, picks: [...b.picks, c] });
        }
        beam = pareto(next);
      }
      for (const b of beam) shapes.push({ s, ...own, k, picks: b.picks,
        kind: k === 1 ? 'stack' : k === n ? 'fan' : 'grid',
        width: Math.max(own.w, b.width + (k < n || k === 1 ? INDENT : 0)),
        height: own.h + LEVEL + b.height });
    }
    return pareto(shapes);
  };
  const virtual = { id: '__layout_root__', virtual: true };
  const forest = roots.length === 1 ? roots[0] : virtual;
  if (forest === virtual) children = new Map([...children, [virtual.id, roots]]);
  const candidates = measure(forest);
  const widthOf = (c) => c.width + PAD * 2;
  const heightOf = (c) => c.height + PAD * 2;
  const score = (c) => Math.min(1, viewportWidth / widthOf(c), viewportHeight / heightOf(c));
  let chosen = [...candidates].sort((a, b) => score(b) - score(a) || a.height - b.height || a.width - b.width)[0];
  if (score(chosen) < MIN_READABLE) {
    const readable = candidates.filter((c) => widthOf(c) * MIN_READABLE <= viewportWidth);
    if (readable.length) chosen = readable.sort((a, b) => a.height - b.height || a.width - b.width)[0];
  }
  const width = widthOf(chosen);
  const height = heightOf(chosen);
  const scale = Math.max(0.5, score(chosen) >= MIN_READABLE ? score(chosen) : Math.min(1, viewportWidth / width));
  const positions = new Map();
  const edges = [];
  const ordered = [];
  const place = (b, x, y, depth) => {
    const stacked = b.kind === 'stack';
    const px = stacked ? x : x + (b.width - b.w) / 2;
    if (!b.s.virtual) {
      positions.set(b.s.id, { x: px, y, w: b.w, h: b.h, s: b.s, depth, arrangement: b.kind });
      ordered.push(b.s.id);
    }
    let cy = y + b.h + LEVEL;
    for (let i = 0; i < b.picks.length; i += b.k) {
      const row = b.picks.slice(i, i + b.k);
      const rowWidth = row.reduce((v, c) => v + c.width, 0) + GAP * (row.length - 1);
      let cx = x + (stacked || b.kind === 'grid' ? INDENT : (b.width - rowWidth) / 2);
      for (const c of row) {
        place(c, cx, cy, depth + 1);
        if (!b.s.virtual) {
          const ancestryFrom = b.s.project && c.s.parent_session_id === executiveId ? executiveId : undefined;
          edges.push({ from: b.s.id, to: c.s.id, ancestryFrom,
            grouping: !!b.s.project && !ancestryFrom || !!c.s.project, kind: b.kind,
            rail: x + 10, bus: cy - LEVEL / 2, row: i / b.k });
        }
        cx += c.width + GAP;
      }
      cy += Math.max(...row.map((c) => c.height)) + LEVEL;
    }
  };
  place(chosen, PAD, PAD, forest.virtual ? -1 : 0);
  const dots = new Map();
  for (const e of edges) {
    const p = positions.get(e.from);
    const c = positions.get(e.to);
    const px = p.x + (e.kind === 'stack' ? 10 : p.w / 2);
    const py = p.y + p.h + (e.grouping ? 0 : 8);
    if (!e.grouping) dots.set(e.from, { id: e.from, x: px, y: py });
    if (e.kind === 'stack') {
      const rail = e.rail;
      e.d = `M${px},${py} L${px},${p.y + p.h + 16} L${rail},${p.y + p.h + 16}`
        + ` L${rail},${c.y + Math.min(22, c.h / 2)} L${rail},${c.y + Math.min(22, c.h / 2)}`
        + ` L${c.x},${c.y + Math.min(22, c.h / 2)}`;
    } else {
      const tx = c.x + c.w / 2;
      e.d = e.row === 0
        ? `M${px},${py} L${px},${e.bus} L${px},${e.bus} L${tx},${e.bus} L${tx},${c.y} L${tx},${c.y}`
        : `M${px},${py} L${px},${p.y + p.h + 16} L${e.rail},${p.y + p.h + 16}`
          + ` L${e.rail},${e.bus} L${tx},${e.bus} L${tx},${c.y}`;
    }
  }
  return { positions, ordered, edges, dots: [...dots.values()], width, height, scale, mode: 'adaptive' };
}

export const intersects = (a, b, gap = 0) => a.x < b.x + b.w + gap && a.x + a.w > b.x - gap
  && a.y < b.y + b.h + gap && a.y + a.h > b.y - gap;

// Search the routed line; a clear lane outside the cards is the final fallback.
export function routeRelationship(a, b, boxes, label, scale, lane = 0) {
  // Clamp the screen size, then undo the canvas scale.
  const fontScale = Math.max(0.85, Math.min(1.25, scale)) / scale;
  const w = (label.length * 7 + 20) * fontScale;
  const h = 24 * fontScale;
  const start = { x: a.x + a.w, y: a.y + a.h / 2 };
  let end = { x: b.x + b.w, y: b.y + b.h / 2 + 12 };
  const rail = Math.max(start.x, end.x) + 24 + lane * 12;
  const points = [start, { x: rail, y: start.y }, { x: rail, y: end.y }, end];
  let labelBox;
  const rightBound = Math.max(...boxes.map((c) => c.x + c.w)) + 24;
  for (let i = 0; i < points.length - 1 && !labelBox; i++) {
    const p = points[i];
    const q = points[i + 1];
    for (let t = 0.5; t < 1; t += 0.05) {
      const box = { x: p.x + (q.x - p.x) * t - w / 2, y: p.y + (q.y - p.y) * t - h / 2, w, h };
      if (box.x >= 0 && box.x + w <= rightBound && boxes.every((c) => !intersects(box, c, 8))) { labelBox = box; break; }
    }
  }
  if (!labelBox) {
    const above = { x: b.x + (b.w - w) / 2, y: b.y - h - 8, w, h };
    if (boxes.every((c) => !intersects(above, c, 4))) {
      labelBox = above;
      end = { x: b.x + b.w / 2, y: b.y };
      points.splice(2, points.length, { x: rail, y: above.y + h / 2 },
        { x: end.x, y: above.y + h / 2 }, end);
    } else {
      const right = Math.max(...boxes.map((c) => c.x + c.w)) + 16;
      const bottom = Math.max(...boxes.map((c) => c.y + c.h)) + 16;
      const lanes = boxes.flatMap((c) => [c.y - h - 8, c.y + c.h + 8]);
      const slots = [];
      for (const y of [0, ...lanes]) for (const x of [0, b.x, b.x + b.w - w, right - w]) {
        const box = { x, y, w, h };
        if (x >= 0 && y >= 0 && x + w <= right && y + h <= bottom
          && boxes.every((c) => !intersects(box, c, 4))) slots.push(box);
      }
      labelBox = slots.sort((a, c) => Math.hypot(a.x - b.x, a.y - b.y)
        - Math.hypot(c.x - b.x, c.y - b.y))[0] || { x: right + 8, y: end.y - h / 2, w, h };
      const cy = labelBox.y + h / 2;
      points.splice(1, points.length, { x: rail, y: start.y }, { x: rail, y: cy },
        { x: labelBox.x + w / 2, y: cy }, { x: rail, y: cy }, { x: rail, y: end.y }, end);
    }
  }
  return { d: points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' '), labelBox, fontScale };
}
