// Hash routes keep deep links working from a static build without rewrites.
export const SETTINGS_SECTIONS = ['providers', 'harnesses', 'models', 'roles'];
export const SETUP_STEPS = [...SETTINGS_SECTIONS, 'review'];

export function parseHash(hash) {
  const parts = (hash || '').replace(/^#\/?/, '').split('/').filter(Boolean).map((p) => {
    try { return decodeURIComponent(p); } catch { return p; }
  });
  if (parts.length === 0) return { view: 'dashboard' };
  if (parts[0] === 'agents' && parts.length === 1) return { view: 'portfolio', sid: null };
  if (parts[0] === 'history' && parts.length === 1) return { view: 'history' };
  if (parts[0] === 'sessions' && parts[1] && parts.length === 2) return { view: 'portfolio', sid: parts[1] };
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
  }
  return { view: 'unknown' };
}

export const agentsHref = () => '#/agents';
export const overviewHref = () => '#/';
export const projectHref = (pid) => `#/projects/${encodeURIComponent(pid)}`;
export const historyHref = (pid) => pid ? `${projectHref(pid)}/history` : '#/history';
export const sessionHref = (pid, sid) => `${pid ? projectHref(pid) : '#'}/sessions/${encodeURIComponent(sid)}`;
export const setupHref = (step) => `#/setup${step ? `/${encodeURIComponent(step)}` : ''}`;
export const settingsHref = (section) => `#/settings/${encodeURIComponent(section)}`;
