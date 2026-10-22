import { useEffect, useMemo, useState } from 'preact/hooks';
import {
  activityFor, ancestors, childrenMap, conversationFor, decisionsFor, getProjects, getSession, observedLabel,
  projectSum, projectSummary, rootsFor, sessionsFor,
} from './data.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { historyHref, projectHref, sessionHref } from './route.js';
import { TreeView } from './tree.jsx';
import { ListTree } from './list.jsx';
import { DetailPanel } from './detail.jsx';
import { NotFound } from './notfound.jsx';
import { AttentionChips } from './attention.jsx';
import { TokenSum } from './tokencount.jsx';

const NARROW = '(max-width: 759px)';
// Large projects open collapsed to their roots until the user expands them.
const COLLAPSE_ABOVE = 200;

function defaultCollapsed(pid, childMap) {
  return sessionsFor(pid).length > COLLAPSE_ABOVE ? [...childMap.keys()] : [];
}

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
  const prefs = usePrefs();
  const narrow = useNarrow();
  // Secondary panels around the full-page tree: the project list and the
  // planning conversation are toggles, session details open as a drawer.
  const [showProjects, setShowProjects] = useState(false);
  const [showConv, setShowConv] = useState(true);
  // Derived per data version, so update events show without a reload.
  const childMap = childrenMap(pid);
  const roots = rootsFor(pid);
  const collapsed = useMemo(() => new Set(prefs.collapsed[pid] ?? defaultCollapsed(pid, childMap)), [prefs, pid, childMap]);
  const selected = sid ? getSession(sid) : null;
  const selectedInProject = selected && selected.project_id === pid ? selected : null;
  const mode = narrow ? 'list' : prefs.mode;

  const update = updatePrefs;
  const setCollapsed = (ids) => updatePrefs({ collapsed: { ...prefs.collapsed, [pid]: [...ids] } });
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
    <div class={`workspace ${narrow ? 'narrow' : ''} ${sid ? 'has-detail' : ''}`} data-testid="workspace" data-mode={mode}>
      <div class="toolbar">
        <h1>{project.name}</h1>
        <span class="muted">{sessionsFor(pid).length} sessions, {roots.length} roots</span>
        <AgentSummary pid={pid} />
        <AttentionChips pid={pid} />
        <a href={historyHref(pid)}>History</a>
        <button type="button" aria-expanded={showProjects} onClick={() => setShowProjects((v) => !v)}>Projects</button>
        <button type="button" aria-expanded={showConv} onClick={() => setShowConv((v) => !v)}>Conversation</button>
        {mode === 'tree' && (
          <label class="check">
            <input type="checkbox" checked={prefs.showRelations}
              onChange={(e) => update({ showRelations: e.currentTarget.checked })} />
            Show typed relationships
          </label>
        )}
        {/* Segmented is last: Tab from List must reach the list's roving
            treeitem before any other control. */}
        {!narrow && (
          <div class="segmented" role="group" aria-label="View">
            <button type="button" aria-pressed={mode === 'tree'} onClick={() => update({ mode: 'tree' })}>Tree</button>
            <button type="button" aria-pressed={mode === 'list'} onClick={() => update({ mode: 'list' })}>List</button>
          </div>
        )}
      </div>

      {showProjects && (
        <nav class="project-nav" aria-label="Projects">
          <h2>Projects</h2>
          <ul>
            {getProjects().map((p) => (
              <li key={p.id}>
                <a href={projectHref(p.id)} aria-current={p.id === pid ? 'page' : undefined}>{p.name}</a>
              </li>
            ))}
          </ul>
          <p class="muted">Host: {project.host}</p>
        </nav>
      )}

      <section class="tree-area" aria-label="Agent tree">
        {mode === 'tree'
          ? <TreeView pid={pid} roots={roots} childMap={childMap} collapsed={collapsed} selectedId={selectedInProject?.id}
              onSelect={select} onToggle={toggle} showRelations={prefs.showRelations} />
          : <ListTree roots={roots} childMap={childMap} collapsed={collapsed} selectedId={selectedInProject?.id}
              onSelect={select} onToggle={toggle} />}
      </section>

      {showConv && <Conversation pid={pid} />}

      {sid && (
        <aside class="detail" aria-label="Session details">
          <div class="drawer-bar">
            <button type="button" onClick={() => { location.hash = projectHref(pid); }}>Close</button>
          </div>
          {selectedInProject
            ? <DetailPanel key={selectedInProject.id} session={selectedInProject} childMap={childMap} onSelect={select} />
            : <NotFound title="Session not found"
                message={`Session "${sid}" is not in ${project.name}. It may not exist, may belong to another project, or you may not have access.`}
                href={projectHref(pid)} linkText="Back to the project" />}
        </aside>
      )}
    </div>
  );
}

// Live header summary: agent and attention counts plus the project token
// total, all re-derived from the snapshot on every applied update.
function AgentSummary({ pid }) {
  const c = projectSummary(pid);
  return (
    <span class="agent-summary" data-testid="agent-summary" aria-live="polite">
      {c.agents} agents · {c.running} running · {c.needsYou} needs you · {c.failed} failed ·{' '}
      <TokenSum sum={projectSum(pid)} prefix="total " testid="project-tokens" />
    </span>
  );
}

function Conversation({ pid }) {
  const entries = conversationFor(pid);
  const activity = activityFor(pid);
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
      {entries.length ? (
        <ol class="messages" data-testid="conversation">
          {entries.map((m, i) => (
            <li key={i}><span class="speaker">{m.speaker}</span> <time class="muted">{m.at}</time><p>{m.text}</p></li>
          ))}
        </ol>
      ) : <p class="muted">No planning messages recorded for this project.</p>}
      <h3 id="activity-h">Recent activity</h3>
      {activity.length ? (
        <ol class="activity" aria-labelledby="activity-h" data-testid="activity">
          {activity.map((a) => (
            <li key={a.id} data-testid="activity-item" data-kind={a.kind}>
              <time class="muted">{observedLabel(a.at)}</time> <a href={sessionHref(pid, a.session_id)}>{a.text}</a>
            </li>
          ))}
        </ol>
      ) : <p class="muted">No activity recorded for this project.</p>}
      <form class="composer" onSubmit={(e) => e.preventDefault()}>
        <label for="composer-input">Message</label>
        <textarea id="composer-input" rows={2} disabled aria-describedby="composer-note" />
        <button type="submit" disabled aria-describedby="composer-note">Send</button>
        <p id="composer-note" class="muted">Commands are not connected in this synthetic prototype.</p>
      </form>
    </section>
  );
}
