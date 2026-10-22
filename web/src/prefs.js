// Browser state is limited to layout preferences: view mode, collapsed
// branches and the relationship overlay. Records are never stored here.
const KEY = 'odin-web-prefs:v1';

// Keeps only { projectId: [sessionId, ...] } entries; anything else is dropped.
function cleanCollapsed(value) {
  const out = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return out;
  for (const [pid, ids] of Object.entries(value)) {
    if (Array.isArray(ids)) out[pid] = ids.filter((id) => typeof id === 'string');
  }
  return out;
}

export function loadPrefs() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || '{}') || {};
    return {
      mode: value.mode === 'list' ? 'list' : 'tree',
      collapsed: cleanCollapsed(value.collapsed),
      showRelations: value.showRelations !== false,
    };
  } catch {
    return { mode: 'tree', collapsed: {}, showRelations: true };
  }
}

export function savePrefs(prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify({
      mode: prefs.mode, collapsed: prefs.collapsed, showRelations: prefs.showRelations,
    }));
  } catch {
    // Storage may be unavailable; preferences then last for the page only.
  }
}
