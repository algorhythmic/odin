export const CARD = { width: 220, height: 182, projectWidth: 400, projectHeight: 60 };
export const MIN_READABLE = 0.85;
const PAD = 24;
const GAP = 40;
const LEVEL = 56;
const STACK = 56;
const INDENT = 28;

// The caller supplies an admitted hierarchy. Geometry never chooses a parent.
export function fitTree({ roots, children, collapsed = new Set(), executiveId }, size = CARD, viewportWidth = 800) {
  const kids = (s) => collapsed.has(s.id) ? [] : children.get(s.id) || [];
  const executive = roots.find((s) => s.id === executiveId);
  const projects = executive ? kids(executive) : roots;
  let deepest = 2;
  const measureDepth = (s, depth) => {
    deepest = Math.max(deepest, depth);
    for (const c of kids(s)) measureDepth(c, depth + 1);
  };
  projects.forEach((s) => measureDepth(s, 1));

  const arrange = (cutoff, wrap = false) => {
    const positions = new Map();
    const edges = [];
    const ordered = [];
    const dimensions = (s) => s.project
      ? { w: size.projectWidth, h: size.projectHeight } : { w: size.width, h: size.height };
    const extents = new Map();
    const measure = (s, depth) => {
      const own = dimensions(s);
      const cs = kids(s).map((c) => measure(c, depth + 1));
      const stacked = depth + 1 >= cutoff;
      const width = !cs.length ? own.w : stacked
        ? Math.max(own.w, INDENT + Math.max(...cs.map((c) => c.width)))
        : Math.max(own.w, cs.reduce((n, c) => n + c.width, 0) + GAP * (cs.length - 1));
      const height = own.h + (!cs.length ? 0 : stacked
        ? STACK + cs.reduce((n, c) => n + c.height, 0) + STACK * (cs.length - 1)
        : LEVEL + Math.max(...cs.map((c) => c.height)));
      const box = { ...own, width, height, stacked };
      extents.set(s.id, box);
      return box;
    };
    projects.forEach((s) => measure(s, 1));
    const place = (s, depth, x, y) => {
      const b = extents.get(s.id);
      const px = b.stacked ? x : x + (b.width - b.w) / 2;
      positions.set(s.id, { x: px, y, w: b.w, h: b.h, s, depth });
      ordered.push(s.id);
      let cx = x + (b.stacked ? INDENT : 0);
      let cy = y + b.h + (b.stacked ? STACK : LEVEL);
      for (const c of kids(s)) {
        const ancestryFrom = s.project && c.parent_session_id === executiveId ? executiveId : undefined;
        edges.push({ from: s.id, to: c.id, ancestryFrom, grouping: !!s.project && !ancestryFrom,
          kind: b.stacked ? 'stack' : 'fan' });
        place(c, depth + 1, cx, cy);
        if (b.stacked) cy += extents.get(c.id).height + STACK;
        else cx += extents.get(c.id).width + GAP;
      }
    };
    const budget = Math.max(0, viewportWidth / MIN_READABLE - PAD * 2);
    let x = PAD;
    let y = PAD + (executive ? size.height + LEVEL : 0);
    let rowHeight = 0;
    let width = executive ? size.width + PAD * 2 : PAD * 2;
    let rows = projects.length ? 1 : 0;
    for (const p of projects) {
      const b = extents.get(p.id);
      if (wrap && x > PAD && x - PAD + b.width > budget) {
        x = PAD;
        y += rowHeight + LEVEL;
        rowHeight = 0;
        rows++;
      }
      place(p, 1, x, y);
      if (executive) edges.push({ from: executive.id, to: p.id, grouping: true, kind: 'fan' });
      width = Math.max(width, x + b.width + PAD);
      x += b.width + GAP;
      rowHeight = Math.max(rowHeight, b.height);
    }
    if (executive) {
      positions.set(executive.id, { x: (width - size.width) / 2, y: PAD,
        w: size.width, h: size.height, s: executive, depth: 0 });
      ordered.unshift(executive.id);
    }
    const height = Math.max(PAD * 2, y + rowHeight + PAD);
    const scale = Math.max(0.5, Math.min(1, viewportWidth / width));
    const dots = new Map();
    for (const e of edges) {
      const p = positions.get(e.from);
      const c = positions.get(e.to);
      const px = p.x + (e.kind === 'stack' ? 10 : p.w / 2);
      const py = p.y + p.h + (e.grouping ? 0 : 8);
      if (!e.grouping) dots.set(e.from, { id: e.from, x: px, y: py });
      if (e.kind === 'stack') {
        const rail = c.x - 14;
        const jog = p.y + p.h + 18;
        e.d = `M${px},${py} L${px},${jog} L${rail},${jog} L${rail},${c.y + 28} L${c.x},${c.y + 28}`;
      } else {
        const tx = c.x + c.w / 2;
        const bus = p.y + p.h + LEVEL / 2;
        e.d = `M${px},${py} L${px},${bus} L${tx},${bus} L${tx},${c.y} L${tx},${c.y}`;
      }
    }
    return { positions, ordered, edges, dots: [...dots.values()], width, height, scale,
      mode: wrap ? `projects-wrap-${rows}` : cutoff === Infinity ? 'tidy' : `stack-${cutoff}` };
  };
  let result = arrange(Infinity);
  if (result.width * MIN_READABLE <= viewportWidth) return result;
  for (let d = deepest; d >= 2; d--) {
    result = arrange(d);
    if (result.width * MIN_READABLE <= viewportWidth) return result;
  }
  return arrange(2, true);
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
      const right = Math.max(...boxes.map((c) => c.x + c.w));
      labelBox = { x: right + 8, y: end.y - h / 2, w, h };
      points.splice(1, points.length, { x: right + w + 16, y: start.y },
        { x: right + w + 16, y: end.y }, end);
    }
  }
  return { d: points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' '), labelBox, fontScale };
}
