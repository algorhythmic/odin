import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { getProjects, isSynthetic } from './data.js';
import { overviewHref, projectHref, projectViewHref, sessionHref, setupHref, settingsHref, PROJECT_VIEWS, SETTINGS_SECTIONS } from './route.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { SetupProgressCard } from './setup-page.jsx';
import { VIEW_LABELS } from './placeholders.jsx';

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

export function Sidebar({ route, narrow, open, onClose }) {
  const dialogRef = useRef(null);
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
        <a href={overviewHref()} aria-current={route.view === 'overview' ? 'page' : undefined}>Overview</a>
        <h2>Projects</h2>
        <ul>
          {getProjects().map((project) => (
            <li key={project.id}>
              <a href={projectHref(project.id)} aria-current={route.pid === project.id && route.view === 'project' && !route.projectView ? 'page' : undefined}>
                {project.name}
              </a>
              {route.pid === project.id && (
                <ul class="sidebar-views" aria-label={`${project.name} views`}>
                  {PROJECT_VIEWS.map((view) => (
                    <li key={view}>
                      <a href={route.sid ? sessionHref(project.id, route.sid, view) : projectViewHref(project.id, view)}
                        aria-current={route.view === 'project' && (route.projectView || 'tree') === view ? 'page' : undefined}>
                        {VIEW_LABELS[view]}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
        <h2>Setup</h2>
        <a href={setupHref()} aria-current={route.view === 'setup' ? 'page' : undefined}>Setup guide</a>
        {SETTINGS_SECTIONS.map((section) => (
          <a key={section} href={settingsHref(section)} aria-current={route.section === section ? 'page' : undefined}>
            {section[0].toUpperCase() + section.slice(1)}
          </a>
        ))}
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
