import { useLayoutEffect, useMemo, useRef, useState } from 'preact/hooks';
import { getSession } from './data.js';
import { prefersReducedMotion } from './live.js';

export const ENTER_MS = 420;
export const LEAVE_MS = 280;

// Keep a removed record just long enough to draw its exit; layout-only removals need no linger.
export function reconcilePresence(previous, items, key, now, reduced, retain) {
  const next = new Map();
  for (const item of items) {
    const id = key(item);
    const old = previous?.get(id);
    const entering = !reduced && previous && !old;
    const phase = entering ? 'entering' : !reduced && old?.phase === 'entering' && now < old.until
      ? 'entering' : 'present';
    next.set(id, { item, phase, until: entering ? now + ENTER_MS : old?.until ?? now });
  }
  if (!reduced) for (const [id, old] of previous || []) {
    if (next.has(id) || !retain(id)) continue;
    const until = old.phase === 'leaving' ? old.until : now + LEAVE_MS;
    if (now < until) next.set(id, { ...old, phase: 'leaving', until });
  }
  return next;
}

const retired = (id) => getSession(id)?.lifecycle === 'retired';

export function usePresence(items, key, retain = retired) {
  const previous = useRef(null);
  const [tick, update] = useState(0);
  const reduced = prefersReducedMotion();
  const records = useMemo(() => {
    const next = reconcilePresence(previous.current, items, key, performance.now(), reduced, retain);
    previous.current = next;
    return next;
  }, [items, key, reduced, retain, tick]);
  const until = Math.min(...[...records.values()].filter((r) => r.phase !== 'present').map((r) => r.until));
  useLayoutEffect(() => {
    if (!Number.isFinite(until)) return;
    const timer = setTimeout(() => update((n) => n + 1), Math.max(1, Math.ceil(until - performance.now())));
    return () => clearTimeout(timer);
  }, [until, tick]);
  useLayoutEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => update((n) => n + 1);
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);
  return [...records.values()];
}

const positionKey = (p) => p.s.id;
export const rowKey = (r) => r.s.id;
export const presenceClass = (phase) => phase === 'entering' ? 'card-enter' : phase === 'leaving' ? 'card-leave' : '';

export function useTreePresence(geometry) {
  const items = useMemo(() => [...geometry.positions.values()], [geometry]);
  const records = usePresence(items, positionKey);
  const previous = useRef(geometry);
  const entering = new Set(records.filter((r) => r.phase === 'entering').map((r) => r.item.s.id));
  const leaving = new Set(records.filter((r) => r.phase === 'leaving').map((r) => r.item.s.id));
  const exits = [...leaving].join('|');
  const result = useMemo(() => {
    // Phase expiry changes classes, not geometry or the routing obstacles.
    if (!leaving.size) return geometry;
    const positions = new Map(records.map((r) => [r.item.s.id, r.item]));
    const edges = [...geometry.edges, ...previous.current.edges.filter((e) => leaving.has(e.to))];
    const dots = [...geometry.dots, ...previous.current.dots.filter((d) => !geometry.dots.some((n) => n.id === d.id)
      && edges.some((e) => e.from === d.id))];
    return { ...geometry, positions, ordered: [...positions.keys()], edges, dots };
  }, [geometry, exits]);
  previous.current = result;
  return { ...result, entering, leaving };
}
