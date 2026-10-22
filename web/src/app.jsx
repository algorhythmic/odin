import { useEffect, useLayoutEffect, useState } from 'preact/hooks';
import { parseHash, overviewHref } from './route.js';
import { getProject, isSynthetic, useDataVersion } from './data.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { Overview } from './overview.jsx';
import { Workspace } from './workspace.jsx';
import { NotFound } from './notfound.jsx';
import { History } from './history.jsx';
import { UpdateDriver } from './driver.jsx';

function useRoute() {
  const [route, setRoute] = useState(() => parseHash(location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(location.hash));
    addEventListener('hashchange', onChange);
    return () => removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

// Dark is the default whatever the system setting; the stored preference
// is the only override.
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

export function App() {
  const route = useRoute();
  useDataVersion();
  let body;
  const project = route.pid ? getProject(route.pid) : null;
  if (route.view === 'overview') body = <Overview />;
  else if (route.view === 'history' && project) body = <History project={project} />;
  else if (route.view === 'project' || route.view === 'history') {
    body = project
      ? <Workspace key={project.id} project={project} sid={route.sid} />
      : <NotFound title="Project not found"
          message={`No project "${route.pid}" exists in this data set, or you do not have access to it.`}
          href={overviewHref()} linkText="Back to the overview" />;
  } else {
    body = <NotFound title="Page not found" message="This address does not match a project or session route."
      href={overviewHref()} linkText="Back to the overview" />;
  }
  return (
    <div class="app">
      <header class="topbar">
        <a class="brand" href={overviewHref()}>Odin</a>
        <nav aria-label="Primary"><a href={overviewHref()}>Overview</a></nav>
        <span class="topbar-space" />
        {isSynthetic && (
          <span class="synthetic-badge" role="note" data-testid="synthetic-badge"
            aria-label="Synthetic data — prototype, not connected to Odin's service"
            title="Prototype, not connected to Odin's service">Synthetic data</span>
        )}
        <ThemeToggle />
      </header>
      {isSynthetic && <UpdateDriver />}
      <main class="content">{body}</main>
    </div>
  );
}
