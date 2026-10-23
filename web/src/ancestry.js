// Grouping never repairs ancestry: only recorded, admitted parents join sessions.
export function projectAncestry(sessions, pid, executiveId) {
  const list = sessions.filter((s) => s.project_id === pid);
  const all = new Map(sessions.map((s) => [s.id, s]));
  const executive = all.get(executiveId);
  const admittedExecutive = executive?.project_id === null ? executive.id : null;
  const inProject = new Map(list.map((s) => [s.id, s]));
  const outside = new Set();
  const crossProject = new Set();
  for (const s of list) {
    if (!s.parent_session_id || s.parent_session_id === admittedExecutive) continue;
    const parent = all.get(s.parent_session_id);
    if (!parent) outside.add(s.id);
    else if (!inProject.has(parent.id)) crossProject.add(s.id);
  }
  const cycle = new Set();
  const state = new Map();
  for (const s of list) {
    const path = [];
    let cur = s;
    while (cur && !state.has(cur.id)) {
      state.set(cur.id, 1);
      path.push(cur.id);
      cur = inProject.get(cur.parent_session_id);
    }
    if (cur && state.get(cur.id) === 1) {
      for (const id of path.slice(path.indexOf(cur.id))) cycle.add(id);
    }
    for (const id of path) state.set(id, 2);
  }
  const children = new Map();
  const parentOf = new Map();
  const roots = [];
  for (const s of list) {
    if (!s.parent_session_id || s.parent_session_id === admittedExecutive
      || outside.has(s.id) || crossProject.has(s.id) || cycle.has(s.id)) roots.push(s);
    else {
      if (!children.has(s.parent_session_id)) children.set(s.parent_session_id, []);
      children.get(s.parent_session_id).push(s);
      parentOf.set(s.id, s.parent_session_id);
    }
  }
  return { roots, children, parentOf, outside, crossProject, cycle };
}

// Session IDs accept every nonempty string. Symbols keep grouping keys in a separate namespace.
export const projectNodeId = (pid) => Symbol.for(`project:${pid}`);
export const nodeLabel = (id) => typeof id === 'symbol' ? Symbol.keyFor(id) : id;
export const storedNodeId = (id) => JSON.stringify([typeof id === 'symbol' ? 'project' : 'session', nodeLabel(id)]);
export function restoredNodeId(value) {
  try {
    const [kind, id] = JSON.parse(value);
    if (typeof id === 'string' && kind === 'project') return Symbol.for(id);
    if (typeof id === 'string' && kind === 'session') return id;
  } catch { /* Older preferences stored raw IDs. */ }
  return value.startsWith('project:') ? Symbol.for(value) : value;
}

// Project rows are layout nodes, never session records or ancestry parents.
export function groupedTree(projects, executive, ancestryFor, scoped = false) {
  const nodes = projects.map((p) => ({ id: projectNodeId(p.id), project_id: p.id, project: p }));
  const children = new Map();
  for (const node of nodes) {
    const a = ancestryFor(node.project_id);
    children.set(node.id, a.roots);
    for (const [id, kids] of a.children) children.set(id, kids);
  }
  if (executive && !scoped) children.set(executive.id, nodes);
  return { roots: executive && !scoped ? [executive] : nodes, children };
}

export function ancestryLabel(session, forest) {
  if (session.provenance === 'imported' && !session.parent_session_id) return 'Imported — parent unknown';
  if (forest.cycle.has(session.id)) return 'Parent cycle in records';
  if (forest.crossProject.has(session.id)) return 'Parent in another project';
  if (forest.outside.has(session.id)) return 'Parent not in this project view';
  return null;
}
