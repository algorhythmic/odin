// Browser state is limited to layout preferences: view mode, collapsed
// branches, card sizes, the key, relationships, theme and sidebar size.
// Records are never stored here.
import { useEffect, useState } from 'preact/hooks';

const KEY = 'odin-web-prefs:v1';
export const SIDEBAR_MIN = 220;
export const SIDEBAR_MAX = 440;
export const SIDEBAR_DEFAULT = 320;
export const clampSidebarWidth = (value) => Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, Math.round(value)));
const THEMES = new Set(['dark', 'light']);

// Keeps only { projectId: [sessionId, ...] } entries; anything else is dropped.
function cleanCollapsed(value) {
  const out = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return out;
  for (const [pid, ids] of Object.entries(value)) {
    if (Array.isArray(ids)) out[pid] = ids.filter((id) => typeof id === 'string');
  }
  return out;
}

// Bound both keys and count; values are explicit expanded/compact choices only.
function cleanCardSizes(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter(([id, expanded]) =>
    /^[a-zA-Z0-9][a-zA-Z0-9:_-]{0,127}$/.test(id) && typeof expanded === 'boolean').slice(-500));
}

// Validates a parsed preference object: every field falls back to its
// default when missing or malformed. Dark is the default theme whatever
// the system setting.
export function cleanPrefs(value) {
  const v = value && typeof value === 'object' ? value : {};
  return {
    cardSizes: cleanCardSizes(v.cardSizes),
    mode: v.mode === 'list' ? 'list' : 'tree',
    collapsed: cleanCollapsed(v.collapsed),
    showRelations: v.showRelations === true,
    keyOpen: v.keyOpen === true,
    theme: THEMES.has(v.theme) ? v.theme : 'dark',
    sidebarCollapsed: v.sidebarCollapsed === true,
    sidebarWidth: Number.isInteger(v.sidebarWidth) && v.sidebarWidth >= SIDEBAR_MIN && v.sidebarWidth <= SIDEBAR_MAX
      ? v.sidebarWidth : SIDEBAR_DEFAULT,
  };
}

export function loadPrefs() {
  try {
    return cleanPrefs(JSON.parse(localStorage.getItem(KEY) || '{}'));
  } catch {
    return cleanPrefs(null);
  }
}

export function savePrefs(prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(cleanPrefs(prefs)));
  } catch {
    // Storage may be unavailable; preferences then last for the page only.
  }
}

// One in-memory preference object shared by every component, so a toggle
// in the header and the workspace toolbar can never write over each
// other's fields.
let current = null;
const listeners = new Set();

export function getPrefs() {
  if (!current) current = loadPrefs();
  return current;
}

export function updatePrefs(patch) {
  current = cleanPrefs({ ...getPrefs(), ...patch });
  savePrefs(current);
  for (const fn of listeners) fn(current);
}

export function usePrefs() {
  const [prefs, setPrefs] = useState(getPrefs);
  useEffect(() => {
    listeners.add(setPrefs);
    return () => listeners.delete(setPrefs);
  }, []);
  return prefs;
}
