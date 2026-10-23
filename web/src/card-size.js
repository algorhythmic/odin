// Card geometry follows visible content and explicit layout preferences.
export const cardIsExpanded = (s, sizes = {}) => Object.hasOwn(sizes, s.id) ? sizes[s.id] : (s.lifecycle === 'running'
  || s.lifecycle === 'waiting_for_input' || s.needs_operator_input === true);

export function cardDimensions(s, sizes = {}, hasChildren = false, hasLineage = false, hasRuns = false) {
  if (s.project) return { w: 300, h: 60 };
  if (!cardIsExpanded(s, sizes)) return { w: 220, h: 44 };
  return { w: 220, h: 140 + (s.needs_operator_input || s.stale ? 22 : 0)
    + (s.stale || s.lifecycle === 'host_offline' ? 22 : 0) + (hasLineage ? 18 : 0)
    + (s.budget ? 18 : 0) + (hasChildren ? 22 : 0) + (hasRuns ? 24 : 0) };
}

