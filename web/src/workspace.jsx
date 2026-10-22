import { useEffect, useMemo, useState } from 'preact/hooks';
import {
  ancestors, childrenMap, conversationFor, decisionsFor, getSession, projects, rootsFor, sessionsFor,
} from './data.js';
import { loadPrefs, savePrefs } from './prefs.js';
import { projectHref, sessionHref } from './route.js';
import { TreeView } from './tree.jsx';
import { ListTree } from './list.jsx';
import { DetailPanel } from './detail.jsx';
import { NotFound } from './notfound.jsx';

const NARROW = '(max-width: 759px)';

function useNarrow() {
  const [narrow, setNarrow] = useState(() => matchMedia(NARROW).matches);
  useEffect(() => {
    const mq = matchMedia(NARROW);
    const onChange = () => setNarrow(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  return narrow;
}

export function Workspace({ project, sid }) {
  const pid = project.id;
  const [prefs, setPrefs] = useState(loadPrefs);
  const narrow = useNarrow();
  const childMap = useMemo(() => childrenMap(pid), [pid]);
  const roots = useMemo(() => rootsFor(pid), [pid]);
  const collapsed = useMemo(() => new Set(prefs.collapsed[pid] || []), [prefs, pid]);
  const selected = sid ? getSession(sid) : null;
  const selectedInProject = selected && selected.project_id === pid ? selected : null;
  const mode = narrow ? 'list' : prefs.mode;

  useEffect(() => { savePrefs(prefs); }, [prefs]);
  const update = (patch) => setPrefs((p) => ({ ...p, ...patch }));
  const setCollapsed = (ids) => setPrefs((p) => ({ ...p, collapsed: { ...p.collapsed, [pid]: [...ids] } }));
  const toggle = (id) => {
    const next = new Set(collapsed);
    if (next.has(id)) next.delete(id); else next.add(id);
    setCollapsed(next);
  };
  const select = (id) => { location.hash = sessionHref(pid, id); };

  // A deep link to a hidden session expands its ancestors.
  useEffect(() => {
    if (!selectedInProject) return;
    const next = new Set(collapsed);
    let changed = false;
    for (const p of ancestors(selectedInProject)) {
      if (next.delete(p)) changed = true;
    }
    if (changed) setCollapsed(next);
  }, [sid]);

  return (
    <div class={`workspace ${narrow ? 'narrow' : ''}`} data-testid="workspace" data-mode={mode}>
      <nav class="project-nav" aria-label="Projects">
        <h2>Projects</h2>
        <ul>
          {projects.map((p) => (
            <li key={p.id}>
              <a href={projectHref(p.id)} aria-current={p.id === pid ? 'page' : undefined}>{p.name}</a>
            </li>
          ))}
        </ul>
        <p class="muted">Host: {project.host}</p>
      </nav>

      <section class="tree-area" aria-label="Agent tree">
        <div class="toolbar">
          <h1>{project.name}</h1>
          <span class="muted">{sessionsFor(pid).length} sessions, {roots.length} roots</span>
          {!narrow && (
            <div class="segmented" role="group" aria-label="View">
              <button type="button" aria-pressed={mode === 'tree'} onClick={() => update({ mode: 'tree' })}>Tree</button>
              <button type="button" aria-pressed={mode === 'list'} onClick={() => update({ mode: 'list' })}>List</button>
            </div>
          )}
          {mode === 'tree' && (
            <label class="check">
              <input type="checkbox" checked={prefs.showRelations}
                onChange={(e) => update({ showRelations: e.currentTarget.checked })} />
              Show typed relationships
            </label>
          )}
        </div>
        {mode === 'tree'
          ? <TreeView pid={pid} roots={roots} childMap={childMap} collapsed={collapsed} selectedId={selectedInProject?.id}
              onSelect={select} onToggle={toggle} showRelations={prefs.showRelations} />
          : <ListTree roots={roots} childMap={childMap} collapsed={collapsed} selectedId={selectedInProject?.id}
              onSelect={select} onToggle={toggle} />}
        <Conversation pid={pid} />
      </section>

      <aside class="detail" aria-label="Session details">
        {sid && !selectedInProject
          ? <NotFound title="Session not found"
              message={`Session "${sid}" is not in ${project.name}. It may not exist, may belong to another project, or you may not have access.`}
              href={projectHref(pid)} linkText="Back to the project" />
          : selectedInProject
            ? <DetailPanel key={selectedInProject.id} session={selectedInProject} childMap={childMap} onSelect={select} />
            : <p class="muted">Select a session in the tree or list to see its assignment, transcript, run, evidence and budget.</p>}
      </aside>
    </div>
  );
}

function Conversation({ pid }) {
  const entries = conversationFor(pid);
  const decisions = decisionsFor(pid).filter((d) => d.status === 'pending');
  return (
    <section class="conversation" aria-labelledby="conv-h">
      <h2 id="conv-h">Planning conversation</h2>
      {decisions.map((d) => (
        <div class="decision" key={d.id} data-testid="pending-decision">
          <strong>{d.kind === 'approval' ? 'Pending approval' : 'Pending decision'}:</strong> {d.title}
          <div class="muted">Request {d.id} · proposal {d.proposal.id} revision {d.proposal.revision} · {d.proposal.digest}</div>
        </div>
      ))}
      <ol class="messages">
        {entries.map((m, i) => (
          <li key={i}><span class="speaker">{m.speaker}</span> <time class="muted">{m.at}</time><p>{m.text}</p></li>
        ))}
      </ol>
      <form class="composer" onSubmit={(e) => e.preventDefault()}>
        <label for="composer-input">Message</label>
        <textarea id="composer-input" rows={2} disabled aria-describedby="composer-note" />
        <button type="submit" disabled aria-describedby="composer-note">Send</button>
        <p id="composer-note" class="muted">Commands are not connected in this synthetic prototype.</p>
      </form>
    </section>
  );
}
