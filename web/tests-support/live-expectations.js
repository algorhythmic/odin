// Independent oracle: a retired record stays iff its recorded subtree contains live work.
export function expectedLiveRecords(sessions) {
  const children = new Map();
  for (const s of sessions) {
    if (!children.has(s.parent_session_id)) children.set(s.parent_session_id, []);
    children.get(s.parent_session_id).push(s);
  }
  return sessions.filter((s) => {
    const pending = [s];
    const visited = new Set();
    while (pending.length) {
      const node = pending.pop();
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      if (node.lifecycle !== 'retired') return true;
      pending.push(...(children.get(node.id) || []));
    }
    return false;
  });
}
