import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'preact/hooks';
import {
  ancestors, getExecutive, getSession, portfolioTree, projectSum, projectSummary, sessionsFor,
} from './data.js';
import { projectNodeId } from './ancestry.js';
import { updatePrefs, usePrefs } from './prefs.js';
import { historyHref, projectHref, sessionHref } from './route.js';
import { TreeView } from './tree.jsx';
import { ListTree } from './list.jsx';
import { DetailPanel } from './detail.jsx';
import { NotFound } from './notfound.jsx';
import { AttentionChips } from './attention.jsx';
import { TokenSum } from './tokencount.jsx';
import { ModelName, StatusChip } from './status.jsx';

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

export function Workspace({ project, sid, highlight }) {
  const header = useRef(null);
  useLayoutEffect(() => {
    const el = header.current;
    const measure = () => el.parentElement.style.setProperty('--toolbar-h', `${el.offsetHeight}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const pid = project?.id;
  const title = project?.name || 'Portfolio';
  const base = pid ? projectHref(pid) : '#/';
  const prefs = usePrefs();
  const narrow = useNarrow();
  const executive = getExecutive();
  const { roots, children: childMap } = portfolioTree(pid);
  const prefKey = pid || 'portfolio';
  const collapsed = useMemo(() => new Set(prefs.collapsed[prefKey]
    ?? (sessionsFor(pid).length > 200 ? [...childMap.keys()].filter((id) => id !== executive?.id) : [])),
  [prefs, prefKey, childMap]);
  const selected = sid ? getSession(sid) : null;
  const admitted = selected && (!pid || selected.project_id === pid || selected.id === executive?.id) ? selected : null;
  const mode = narrow ? 'list' : prefs.mode;
  const counts = projectSummary(pid);
  const setCollapsed = (ids) => updatePrefs({ collapsed: { ...prefs.collapsed, [prefKey]: [...ids] } });
  const toggle = (id) => {
    const next = new Set(collapsed);
    if (next.has(id)) next.delete(id); else next.add(id);
    setCollapsed(next);
  };
  const select = (id) => { location.hash = sessionHref(pid, id); };

  // A deep link reveals grouping rows as well as recorded ancestors.
  useEffect(() => {
    if (!admitted) return;
    const next = new Set(collapsed);
    const ids = [...ancestors(admitted), projectNodeId(admitted.project_id)];
    let changed = false;
    for (const id of ids) if (next.delete(id)) changed = true;
    if (changed) setCollapsed(next);
  }, [sid]);

  return (
    <div class={`workspace ${narrow ? 'narrow' : ''} ${sid ? 'has-detail' : ''}`} data-testid="workspace" data-mode={mode}>
      {pid && <div class="scope-header">
        <a href="#/">All projects</a>
        {executive && <a class="executive-header" href={sessionHref(undefined, executive.id)} data-testid="executive-header">
          <strong>{executive.role}</strong> <ModelName model={executive.model} /> <StatusChip session={executive} />
        </a>}
      </div>}
      <div class="toolbar" ref={header} data-testid="tree-header">
        <h1>{title}</h1>
        <span class="muted" data-testid="agent-summary" aria-live="polite">
          {counts.agents} agents · {counts.running} running
        </span>
        <AttentionChips pid={pid} />
        <TokenSum sum={projectSum(pid)} compactUnknown testid="project-tokens" />
        <a href={historyHref(pid)}>History</a>
        <label class="check">
          <input type="checkbox" checked={prefs.showRelations}
            onChange={(e) => updatePrefs({ showRelations: e.currentTarget.checked })} />
          Show typed relationships
        </label>
        {!narrow && (
          <div class="segmented" role="group" aria-label="Layout">
            <button type="button" aria-pressed={mode === 'tree'} onClick={() => updatePrefs({ mode: 'tree' })}>Tree</button>
            <button type="button" aria-pressed={mode === 'list'} onClick={() => updatePrefs({ mode: 'list' })}>List</button>
          </div>
        )}
      </div>
      <section class="tree-area" aria-label="Agent tree">
        {mode === 'tree'
          ? <TreeView pid={pid} roots={roots} childMap={childMap} collapsed={collapsed} selectedId={admitted?.id}
              highlight={highlight} onSelect={select} onToggle={toggle} showRelations={prefs.showRelations} />
          : <ListTree roots={roots} childMap={childMap} collapsed={collapsed} selectedId={admitted?.id}
              highlight={highlight} onSelect={select} onToggle={toggle} />}
      </section>
      {sid && <aside class="detail" aria-label="Session details">
        <div class="drawer-bar"><button type="button" onClick={() => { location.hash = base; }}>Close</button></div>
        {admitted
          ? <DetailPanel key={admitted.id} session={admitted} childMap={childMap} onSelect={select} />
          : <NotFound title="Session not found"
              message={`Session "${sid}" is not in ${title}. `
                + 'It may not exist, may belong to another project, or you may not have access.'}
              href={base} linkText={pid ? 'Back to the project' : 'All projects'} />}
      </aside>}
    </div>
  );
}
