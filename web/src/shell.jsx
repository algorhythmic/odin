import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { getExecutive, getProjects, isSynthetic, projectStatus, projectSummary, sessionStatus } from './data.js';
import { overviewHref, projectHref, setupHref, settingsHref } from './route.js';
import { friendlyModelName } from './models.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { SetupProgressCard } from './setup-page.jsx';

export function useSidebarNarrow() {
  const [narrow, setNarrow] = useState(() => matchMedia('(max-width: 899px)').matches);
  useEffect(() => {
    const mq = matchMedia('(max-width: 899px)');
    const change = () => setNarrow(mq.matches);
    mq.addEventListener('change', change);
    return () => mq.removeEventListener('change', change);
  }, []);
  return narrow;
}

function ThemeToggle() {
  const prefs = usePrefs();
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = prefs.theme;
  }, [prefs.theme]);
  return (
    <button type="button" class="theme-toggle" data-testid="theme-toggle"
      aria-pressed={prefs.theme === 'light'} title="Toggle between the dark and light themes"
      onClick={() => updatePrefs({ theme: prefs.theme === 'light' ? 'dark' : 'light' })}>
      Theme: {prefs.theme === 'light' ? 'Light' : 'Dark'}
    </button>
  );
}

export function Sidebar({ route, narrow, open, onClose, onHighlight }) {
  const dialogRef = useRef(null);
  const executive = getExecutive();
  const executiveStatus = executive && sessionStatus(executive);
  const hovered = useRef(null);
  const focused = useRef(null);
  const highlight = () => onHighlight(route.view === 'portfolio' ? hovered.current || focused.current : null);
  // A native modal supplies focus containment, Escape and focus return.
  useLayoutEffect(() => {
    const dialog = dialogRef.current;
    if (!narrow || !dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [narrow, open]);
  const Container = narrow ? 'dialog' : 'aside';
  return (
    <Container class="sidebar" id="app-sidebar" ref={dialogRef} aria-label="Sidebar"
      onClose={onClose}>
      <div class="sidebar-brand">
        <a class="brand" href={overviewHref()}><span class="odin-mark" aria-hidden="true">O</span>Odin</a>
        {narrow && <button type="button" aria-label="Close menu" onClick={onClose}>×</button>}
      </div>
      <nav class="sidebar-nav" aria-label="Primary" onClick={(e) => { if (narrow && e.target.closest('a')) onClose(); }}>
        <a class="sidebar-executive" href={overviewHref()} data-testid="sidebar-executive"
          aria-current={route.view === 'portfolio' ? 'page' : undefined}>
          {executive ? <>
            <span class={`status-dot status-${executiveStatus.key}`} role="img" aria-label={executiveStatus.label} />
            <span><strong>{executive.role}</strong><small>{friendlyModelName(executive.model)}</small></span>
          </> : <span>Portfolio · Executive unavailable</span>}
        </a>
        <ul class="sidebar-branch">
          {getProjects().map((project) => {
            const status = projectStatus(project.id);
            const counts = projectSummary(project.id);
            return <li key={project.id}>
              <a href={projectHref(project.id)} data-testid="sidebar-project" data-project-id={project.id}
                aria-current={route.pid === project.id ? 'page' : undefined}
                onMouseEnter={() => { hovered.current = project.id; highlight(); }}
                onMouseLeave={() => { hovered.current = null; highlight(); }}
                onFocus={() => { focused.current = project.id; highlight(); }}
                onBlur={() => { focused.current = null; highlight(); }}>
                <span class={`status-dot status-${status.key}`} role="img" aria-label={status.label} />
                <span class="sidebar-project-name">{project.name}</span>
                <small>{counts.agents}</small>
              </a>
            </li>;
          })}
        </ul>
        <a href={setupHref()} aria-current={route.view === 'setup' ? 'page' : undefined}>Setup</a>
        <a href={settingsHref('providers')} aria-current={route.view === 'settings' ? 'page' : undefined}>Settings</a>
      </nav>
      <footer class="sidebar-footer">
        <SetupProgressCard />
        <ThemeToggle />
        {isSynthetic && (
          <span class="synthetic-badge" role="note" data-testid="synthetic-badge"
            aria-label="Synthetic data — prototype, not connected to Odin's service"
            title="Prototype, not connected to Odin's service">Synthetic data</span>
        )}
      </footer>
    </Container>
  );
}
