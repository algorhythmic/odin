// Both layouts traverse the same typed grouping keys and recorded session IDs.
export function flattenRows(roots, childMap, collapsed) {
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

export function replacementRow(previous, rows, id) {
  const index = previous.findIndex((r) => r.s.id === id);
  if (index < 0 || rows.some((r) => r.s.id === id)) return null;
  const remaining = new Set(rows.map((r) => r.s.id));
  return [...previous.slice(index + 1), ...previous.slice(0, index).reverse()]
    .find((r) => remaining.has(r.s.id))?.s.id ?? rows[0]?.s.id ?? null;
}
