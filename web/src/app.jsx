import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { parseHash, overviewHref, agentsHref } from './route.js';
import { getProject, useDataVersion } from './data.js';
import { Sidebar, useSidebarNarrow } from './shell.jsx';
import { SetupPage } from './setup-page.jsx';
import { Workspace } from './workspace.jsx';
import { NotFound } from './notfound.jsx';
import { Dashboard } from './dashboard.jsx';
import { useSetup } from './setup-state.jsx';
import { History } from './history.jsx';

function useRoute() {
  const [route, setRoute] = useState(() => parseHash(location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(location.hash));
    addEventListener('hashchange', onChange);
    return () => removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

function AppliedNotice() {
  const state = useSetup();
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!state.appliedOnce || state.dirty) { setVisible(false); return undefined; }
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), 5000);
    return () => clearTimeout(timer);
  }, [state.applied, state.appliedOnce, state.dirty]);
  return visible && <p class="setup-applied dashboard-confirmation" role="status">Applied (synthetic, not saved)</p>;
}

export function App() {
  const route = useRoute();
  useDataVersion();
  const narrow = useSidebarNarrow();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [highlight, setHighlight] = useState(null);
  useEffect(() => { setHighlight(null); }, [route]);
  useEffect(() => { setDrawerOpen(false); }, [route, narrow]);
  const appRef = useRef(null);
  const chromeRef = useRef(null);
  // The pinned header's real height, published as --chrome-h so the toolbar
  // and the detail drawer can sit exactly below it at any wrap width.
  useLayoutEffect(() => {
    const app = appRef.current;
    const chrome = chromeRef.current;
    if (!app || !chrome) return undefined;
    const set = () => app.style.setProperty('--chrome-h', `${chrome.offsetHeight}px`);
    set();
    const ro = new ResizeObserver(set);
    ro.observe(chrome);
    return () => ro.disconnect();
  }, []);
  let body;
  const project = route.pid ? getProject(route.pid) : null;
  if (route.view === 'dashboard') body = <Dashboard />;
  else if (route.view === 'portfolio') body = <Workspace sid={route.sid} highlight={highlight} />;
  else if (route.view === 'setup' || route.view === 'settings') body = <SetupPage step={route.step} section={route.section} />;
  else if (route.view === 'history' && (!route.pid || project)) body = <History project={project} />;
  else if (route.view === 'project' || route.view === 'history') {
    body = project
      ? <Workspace key={project.id} project={project} sid={route.sid} />
      : <NotFound title="Project not found"
          message={`No project "${route.pid}" exists in this data set, or you do not have access to it.`}
          href={agentsHref()} linkText="All projects" />;
  } else {
    body = <NotFound title="Page not found" message="This address does not match a project or session route."
      href={agentsHref()} linkText="All projects" />;
  }
  return (
    <div class="app" ref={appRef}>
      <Sidebar route={route} narrow={narrow} open={drawerOpen} onClose={() => setDrawerOpen(false)} onHighlight={setHighlight} />
      <div class="page">
        <div class="chrome" ref={chromeRef}>
          {narrow && (
            <header class="topbar">
              <button type="button" aria-label="Open menu" aria-controls="app-sidebar" aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen(true)}>☰ Menu</button>
              <a class="brand" href={overviewHref()}>Odin</a>
            </header>
          )}
        </div>
        <main class="content">{body}</main>
        <AppliedNotice />
      </div>
    </div>
  );
}
