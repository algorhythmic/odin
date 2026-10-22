import { useEffect, useState } from 'preact/hooks';
import { parseHash, overviewHref } from './route.js';
import { getProject, isSynthetic, useDataVersion } from './data.js';
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
      {isSynthetic && (
        <div class="synthetic-banner" role="note" data-testid="synthetic-banner">
          SYNTHETIC DATA — prototype, not connected to Odin's service
        </div>
      )}
      <header class="topbar">
        <a class="brand" href={overviewHref()}>Odin</a>
        <nav aria-label="Primary"><a href={overviewHref()}>Overview</a></nav>
      </header>
      {isSynthetic && <UpdateDriver />}
      <main class="content">{body}</main>
    </div>
  );
}
