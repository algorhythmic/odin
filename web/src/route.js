// Hash routes keep deep links working from a static build without rewrites.
export function parseHash(hash) {
  const parts = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map((p) => {
    try { return decodeURIComponent(p); } catch { return p; }
  });
  if (parts.length === 0) return { view: 'overview' };
  if (parts[0] === 'projects' && parts[1] && parts.length === 2) return { view: 'project', pid: parts[1], sid: null };
  if (parts[0] === 'projects' && parts[1] && parts[2] === 'sessions' && parts[3] && parts.length === 4) {
    return { view: 'project', pid: parts[1], sid: parts[3] };
  }
  if (parts[0] === 'projects' && parts[1] && parts[2] === 'history' && parts.length === 3) return { view: 'history', pid: parts[1] };
  return { view: 'unknown' };
}

export const overviewHref = () => '#/';
export const projectHref = (pid) => `#/projects/${encodeURIComponent(pid)}`;
export const historyHref = (pid) => `${projectHref(pid)}/history`;
export const sessionHref = (pid, sid) => `${projectHref(pid)}/sessions/${encodeURIComponent(sid)}`;
