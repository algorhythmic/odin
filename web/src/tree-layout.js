export const CARD = { width: 220, height: 182, projectWidth: 300, projectHeight: 74 };
export const MIN_READABLE = 0.75;
const PAD = 16;
const GAP = 24;
const LEVEL = 48;
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
        kind: k === n ? 'fan' : k === 1 ? 'stack' : 'grid',
        width: Math.max(own.w, b.width + (k < n ? INDENT : 0)),
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
  for (const e of edges) {
    e.points = [...e.d.matchAll(/[ML]([\d.-]+),([\d.-]+)/g)].map((m) => ({ x: +m[1], y: +m[2] }));
  }
  return { positions, ordered, edges, dots: [...dots.values()], width, height, scale, mode: 'adaptive' };
}

export const intersects = (a, b, gap = 0) => a.x < b.x + b.w + gap && a.x + a.w > b.x - gap
  && a.y < b.y + b.h + gap && a.y + a.h > b.y - gap;

// Interior tests allow a line to meet a rectangle at its port or gutter boundary.
export function segmentIntersects(a, b, box) {
  return Math.min(a.x, b.x) < box.x + box.w && Math.max(a.x, b.x) > box.x
    && Math.min(a.y, b.y) < box.y + box.h && Math.max(a.y, b.y) > box.y;
}

const pathData = (points) => points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
const distance = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
function simplify(points) {
  points = points.filter((p, i) => !i || p.x !== points[i - 1].x || p.y !== points[i - 1].y);
  return points.filter((p, i) => {
    const a = points[i - 1];
    const b = points[i + 1];
    return !a || !b || !(distance(a, p) + distance(p, b) === distance(a, b)
      && (a.x === p.x && p.x === b.x || a.y === p.y && p.y === b.y));
  });
}

// Cache interval queries for a geometry, so each search checks lanes rather than every card.
function routingContext(boxes, clearance) {
  const obstacles = boxes.map((b) => ({ x: b.x - clearance, y: b.y - clearance,
    w: b.w + clearance * 2, h: b.h + clearance * 2 }));
  const rows = new Map();
  const columns = new Map();
  const intervals = (cache, key, horizontal) => {
    if (!cache.has(key)) {
      const spans = obstacles.filter((b) => horizontal ? key > b.y && key < b.y + b.h : key > b.x && key < b.x + b.w)
        .map((b) => horizontal ? [b.x, b.x + b.w] : [b.y, b.y + b.h]).sort((a, b) => a[0] - b[0]);
      const merged = [];
      for (const span of spans) {
        const last = merged.at(-1);
        if (last && last[1] >= span[0]) last[1] = Math.max(last[1], span[1]);
        else merged.push(span);
      }
      cache.set(key, merged);
    }
    return cache.get(key);
  };
  const clear = (a, b) => {
    const horizontal = a.y === b.y;
    const spans = intervals(horizontal ? rows : columns, horizontal ? a.y : a.x, horizontal);
    const lo = Math.min(horizontal ? a.x : a.y, horizontal ? b.x : b.y);
    const hi = Math.max(horizontal ? a.x : a.y, horizontal ? b.x : b.y);
    let left = 0;
    let right = spans.length;
    while (left < right) {
      const mid = (left + right) >> 1;
      if (spans[mid][1] <= lo) left = mid + 1; else right = mid;
    }
    return left === spans.length || spans[left][0] >= hi;
  };
  const unique = (values) => [...new Set(values)].sort((a, b) => a - b);
  const xs = unique(obstacles.flatMap((b) => [b.x, b.x + b.w]));
  const ys = unique(obstacles.flatMap((b) => [b.y, b.y + b.h]));
  return { obstacles, clear, xs, ys, links: new Uint8Array(xs.length * ys.length * 4),
    costs: new Float64Array(xs.length * ys.length), previous: new Int32Array(xs.length * ys.length) };
}

// A compressed gutter grid keeps search independent of canvas size and zoom.
export function routeOrthogonal(start, end, boxes, clearance = 8, context = routingContext(boxes, clearance)) {
  const { clear } = context;
  const quick = [
    [start, { x: end.x, y: start.y }, end],
    [start, { x: start.x, y: end.y }, end],
  ].filter((ps) => ps.slice(1).every((p, i) => clear(ps[i], p)));
  if (quick.length) return simplify(quick[0]);
  const { xs, ys, links } = context;
  const nx = xs.length;
  const point = (id) => ({ x: xs[id % nx], y: ys[Math.floor(id / nx)] });
  const bounds = (values, n) => {
    let i = 0;
    let j = values.length;
    while (i < j) { const m = (i + j) >> 1; if (values[m] < n) i = m + 1; else j = m; }
    return [...new Set([Math.max(0, i - 1), Math.min(values.length - 1, i)])];
  };
  const attach = (p) => {
    const nodes = new Map();
    for (const x of bounds(xs, p.x)) for (const y of bounds(ys, p.y)) {
      const q = { x: xs[x], y: ys[y] };
      const elbows = [{ x: p.x, y: q.y }, { x: q.x, y: p.y }];
      const elbow = elbows.find((e) => clear(p, e) && clear(e, q));
      if (elbow) nodes.set(y * nx + x, [p, elbow, q]);
    }
    return nodes;
  };
  const starts = attach(start);
  const ends = attach(end);
  const { costs, previous } = context;
  costs.fill(Infinity);
  previous.fill(-1);
  const heuristic = (id) => Math.abs(xs[id % nx] - end.x) + Math.abs(ys[Math.floor(id / nx)] - end.y);
  const heap = [];
  const before = (a, b) => a.score < b.score || a.score === b.score && a.cost > b.cost;
  // Favor progress along the route; shortest-path optimality is not needed for a clear gutter.
  const push = (id, cost) => {
    const item = { id, cost, score: cost + heuristic(id) * 2 };
    let i = heap.length;
    heap.push(item);
    while (i && before(item, heap[(i - 1) >> 1])) {
      heap[i] = heap[(i - 1) >> 1];
      i = (i - 1) >> 1;
    }
    heap[i] = item;
  };
  const pop = () => {
    const top = heap[0];
    const item = heap.pop();
    if (heap.length) {
      let i = 0;
      while (i * 2 + 1 < heap.length) {
        let j = i * 2 + 1;
        if (j + 1 < heap.length && before(heap[j + 1], heap[j])) j++;
        if (!before(heap[j], item)) break;
        heap[i] = heap[j];
        i = j;
      }
      heap[i] = item;
    }
    return top;
  };
  for (const id of starts.keys()) {
    const cost = distance(start, point(id));
    costs[id] = cost;
    push(id, cost);
  }
  let goal;
  let best = Infinity;
  while (heap.length) {
    const { id, cost } = pop();
    if (cost !== costs[id]) continue;
    if (cost + heuristic(id) >= best) break;
    if (ends.has(id)) { best = cost + heuristic(id); goal = id; }
    const x = id % nx;
    const y = Math.floor(id / nx);
    const ax = xs[x];
    const ay = ys[y];
    const neighbors = [x > 0 ? id - 1 : -1, x + 1 < nx ? id + 1 : -1,
      y > 0 ? id - nx : -1, y + 1 < ys.length ? id + nx : -1];
    for (let direction = 0; direction < 4; direction++) {
      const n = neighbors[direction];
      if (n < 0) continue;
      const bx = xs[n % nx];
      const by = ys[Math.floor(n / nx)];
      const next = cost + Math.abs(ax - bx) + Math.abs(ay - by);
      if (next >= costs[n]) continue;
      const key = id * 4 + direction;
      if (!links[key]) links[key] = clear({ x: ax, y: ay }, { x: bx, y: by }) ? 1 : 2;
      if (links[key] === 2) continue;
      costs[n] = next;
      previous[n] = id;
      push(n, next);
    }
  }
  if (goal !== undefined) {
    const path = [point(goal)];
    let first = goal;
    while (previous[first] >= 0) { first = previous[first]; path.push(point(first)); }
    return simplify([...starts.get(first), ...path.reverse(), ...ends.get(goal).toReversed()]);
  }
  throw new Error('No clear gutter route');
}

export function createRelationshipRouter(boxes, scale) {
  const contexts = new Map();
  return (a, b, label, lane = 0) => {
    const clearance = 6 + lane % 4 * 2;
    if (!contexts.has(clearance)) contexts.set(clearance, routingContext(boxes, clearance));
    return routeRelationship(a, b, boxes, label, scale, lane, contexts.get(clearance));
  };
}

export function routeRelationship(a, b, boxes, label, scale, lane = 0, context) {
  const fontScale = Math.max(0.85, Math.min(1.25, scale)) / scale;
  const w = (label.length * 7 + 20) * fontScale;
  const h = 24 * fontScale;
  const offset = [0, 3, -3, 6, -6][lane % 5];
  const clearance = 6 + lane % 4 * 2;
  context ||= routingContext(boxes, clearance);
  const start = { x: a.x + a.w - 1, y: a.y + a.h / 2 + offset };
  const end = { x: b.x + b.w - 1, y: b.y + b.h / 2 + offset };
  const out = { x: a.x + a.w + clearance, y: start.y };
  const into = { x: b.x + b.w + clearance, y: end.y };
  let middle = routeOrthogonal(out, into, boxes, clearance, context);
  let labelBox;
  for (let i = 1; i < middle.length && !labelBox; i++) {
    const p = middle[i - 1];
    const q = middle[i];
    const horizontal = p.y === q.y;
    for (const t of [0.5, 0.25, 0.75]) {
      const anchor = { x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t };
      const shifts = horizontal ? [0, h / 2 + 6, -h / 2 - 6] : [0, w / 2 + 6, -w / 2 - 6];
      for (const shift of shifts) {
        const centre = { x: anchor.x + (horizontal ? 0 : shift), y: anchor.y + (horizontal ? shift : 0) };
        const box = { x: centre.x - w / 2, y: centre.y - h / 2, w, h };
        if (box.x < 0 || box.y < 0 || boxes.some((c) => intersects(box, c, 4)
          || segmentIntersects(anchor, centre, c))) continue;
        labelBox = box;
        if (shift) middle.splice(i, 0, anchor, centre, anchor);
        break;
      }
      if (labelBox) break;
    }
  }
  if (!labelBox) {
    const right = Math.max(...boxes.map((c) => c.x + c.w)) + 16;
    const slots = boxes.flatMap((c) => [c.y - h - 6, c.y + c.h + 6].map((y) =>
      ({ x: c.x + (c.w - w) / 2, y, w, h }))).filter((box) => box.x >= 0 && box.y >= 0
        && box.x + w <= right && boxes.every((c) => !intersects(box, c, 4)));
    const centre = (box) => ({ x: box.x + w / 2, y: box.y + h / 2 });
    slots.sort((p, q) => distance(out, centre(p)) + distance(centre(p), into)
      - distance(out, centre(q)) - distance(centre(q), into));
    // The external lane is needed only if no interior gutter can hold the label.
    labelBox = slots[0] || { x: right + 4 + lane * 4, y: Math.max(0, end.y - h / 2), w, h };
    const via = centre(labelBox);
    middle = [...routeOrthogonal(out, via, boxes, clearance, context),
      ...routeOrthogonal(via, into, boxes, clearance, context)];
  }
  const points = simplify([start, ...middle, end]);
  return { d: pathData(points), points, labelBox, fontScale };
}
