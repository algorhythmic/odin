// Hash routes keep deep links working from a static build without rewrites.
export const PROJECT_VIEWS = ['tree', 'queue', 'lanes', 'graph', 'decisions', 'board'];
export const SETTINGS_SECTIONS = ['providers', 'harnesses', 'models', 'roles'];
export const SETUP_STEPS = [...SETTINGS_SECTIONS, 'review'];

export function parseHash(hash) {
  const parts = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map((p) => {
    try { return decodeURIComponent(p); } catch { return p; }
  });
  if (parts.length === 0) return { view: 'overview' };
  if (parts[0] === 'setup') {
    if (parts.length === 1) return { view: 'setup', step: null };
    if (parts.length === 2 && SETUP_STEPS.includes(parts[1])) return { view: 'setup', step: parts[1] };
  }
  if (parts[0] === 'settings' && parts.length === 2 && SETTINGS_SECTIONS.includes(parts[1])) {
    return { view: 'settings', section: parts[1] };
  }
  if (parts[0] === 'projects' && parts[1]) {
    const pid = parts[1];
    if (parts.length === 2) return { view: 'project', pid, sid: null };
    if (parts[2] === 'sessions' && parts[3] && parts.length === 4) {
      return { view: 'project', pid, sid: parts[3] };
    }
    if (parts[2] === 'history' && parts.length === 3) return { view: 'history', pid };
    if (PROJECT_VIEWS.slice(1).includes(parts[2])) {
      const projectView = parts[2];
      if (parts.length === 3) return { view: 'project', pid, projectView, sid: null };
      if (parts[3] === 'sessions' && parts[4] && parts.length === 5) {
        return { view: 'project', pid, projectView, sid: parts[4] };
      }
    }
  }
  return { view: 'unknown' };
}

export const overviewHref = () => '#/';
export const projectHref = (pid) => `#/projects/${encodeURIComponent(pid)}`;
export const historyHref = (pid) => `${projectHref(pid)}/history`;
export const projectViewHref = (pid, view = 'tree') => `${projectHref(pid)}${view === 'tree' ? '' : `/${encodeURIComponent(view)}`}`;
export const sessionHref = (pid, sid, view = 'tree') => `${projectViewHref(pid, view)}/sessions/${encodeURIComponent(sid)}`;
export const setupHref = (step) => `#/setup${step ? `/${encodeURIComponent(step)}` : ''}`;
export const settingsHref = (section) => `#/settings/${encodeURIComponent(section)}`;
