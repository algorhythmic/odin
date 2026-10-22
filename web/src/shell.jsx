import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import {
  cardElapsed, failedSessions, getExecutive, getProjects, isSynthetic, needsYouSessions,
  projectStatus, projectSummary, projectSum, sessionStatus, sessionsFor,
} from './data.js';
import { overviewHref, projectHref, sessionHref, setupHref, settingsHref } from './route.js';
import { friendlyModelName } from './models.js';
import { clampSidebarWidth, SIDEBAR_MIN, SIDEBAR_MAX, updatePrefs, usePrefs } from './prefs.js';
import { SetupProgressCard } from './setup-page.jsx';
import { useSetup } from './setup-state.jsx';
import { SidebarAttention } from './attention.jsx';
import { TokenCount, TokenSum } from './tokencount.jsx';
import { ShellIcon } from './shell-icons.jsx';
import { UsageMeters } from './usage.jsx';
import { bandLabel, connectedUsage, worstBand } from './usage.js';

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

function ThemeToggle({ collapsed }) {
  const prefs = usePrefs();
  useLayoutEffect(() => { document.documentElement.dataset.theme = prefs.theme; }, [prefs.theme]);
  const label = `Theme: ${prefs.theme === 'light' ? 'Light' : 'Dark'}`;
  return <button type="button" class="theme-toggle" data-testid="theme-toggle" aria-label={label}
    aria-pressed={prefs.theme === 'light'} title={`${label} · Toggle theme`}
    onClick={() => updatePrefs({ theme: prefs.theme === 'light' ? 'dark' : 'light' })}>
    <ShellIcon name="theme" />{!collapsed && <span>{label}</span>}
  </button>;
}

function ProjectBar({ pid }) {
  const buckets = { running: 0, 'needs-you': 0, failed: 0, done: 0 };
  for (const s of sessionsFor(pid)) {
    const key = s.needs_operator_input && sessionStatus(s).key !== 'failed' ? 'needs-you' : sessionStatus(s).key;
    if (Object.hasOwn(buckets, key)) buckets[key] += 1;
  }
  const total = Object.values(buckets).reduce((a, b) => a + b, 0);
  const text = Object.entries(buckets).map(([key, count]) => `${count} ${key.replace('-', ' ')}`).join(', ');
  return <span class="project-status-bar sidebar-detail" role="img" aria-label={text} title={text}>
    {Object.entries(buckets).map(([key, count]) => <i key={key} class={`status-${key}`}
      style={{ width: `${total ? count / total * 100 : 0}%` }} />)}
  </span>;
}

function Activity() {
  const list = sessionsFor();
  const ended = list.filter((s) => ['ended', 'retired'].includes(s.lifecycle)).length;
  return <section class="sidebar-activity" aria-label="Activity" data-testid="sidebar-activity">
    <h2>Activity</h2>
    <div class="activity-values">
      <span><strong>{projectSummary().running}</strong> running</span>
      <span title="Ended or retired in the snapshot"><strong>{ended}</strong> ended
        <span class="sidebar-detail"> in snapshot</span></span>
      <TokenSum sum={projectSum()} compactUnknown />
    </div>
  </section>;
}

export function Sidebar({ route, narrow, open, onClose, onHighlight }) {
  const dialogRef = useRef(null);
  const prefs = usePrefs();
  const setup = useSetup();
  const collapsed = !narrow && prefs.sidebarCollapsed;
  const executive = getExecutive();
  const executiveStatus = executive && sessionStatus(executive);
  const lineages = connectedUsage(setup);
  const ceilings = setup.catalogue.usage?.band_ceilings;
  const worst = worstBand(lineages, ceilings);
  const attentionTarget = needsYouSessions()[0] || failedSessions()[0];
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
  const [dragging, setDragging] = useState(false);
  const drag = useRef(null);
  useEffect(() => { drag.current = null; setDragging(false); }, [narrow, collapsed]);
  const resize = (width) => updatePrefs({ sidebarWidth: clampSidebarWidth(width) });
  const collapseLabel = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
  const Container = narrow ? 'dialog' : 'aside';
  return <Container class={`sidebar ${collapsed ? 'sidebar-collapsed' : ''} ${dragging ? 'sidebar-resizing' : ''}`}
    id="app-sidebar" ref={dialogRef} aria-label="Sidebar"
    style={!narrow ? { width: collapsed ? 56 : prefs.sidebarWidth } : undefined}
    onClose={onClose}>
    <div class="sidebar-brand">
      <a class="brand" href={overviewHref()} aria-label="Odin" title="Odin">
        <span class="odin-mark" aria-hidden="true">O</span>{!collapsed && 'Odin'}
      </a>
      {narrow ? <button type="button" aria-label="Close menu" onClick={onClose}>×</button> : (
        <button type="button" class="sidebar-collapse" aria-label={collapseLabel} title={collapseLabel}
          aria-expanded={!collapsed} aria-controls="app-sidebar"
          onClick={() => updatePrefs({ sidebarCollapsed: !collapsed })}>
          <ShellIcon name={collapsed ? 'expand' : 'collapse'} /></button>
      )}
    </div>
    <nav class="sidebar-nav" aria-label="Primary" onClick={(e) => { if (narrow && e.target.closest('a')) onClose(); }}>
      <div class="sidebar-scroll">
        <a class="sidebar-executive" href={overviewHref()} data-testid="sidebar-executive"
          aria-label={collapsed ? `Executive · ${executiveStatus?.label || 'unavailable'}` : undefined}
          title={collapsed ? `Executive · ${executiveStatus?.label || 'unavailable'}` : undefined}
          aria-current={route.view === 'portfolio' ? 'page' : undefined}>
          {executive ? <>
            <span class={`status-dot status-${executiveStatus.key}`} role="img" aria-label={executiveStatus.label} />
            {!collapsed && <span class="executive-label"><strong>{executive.role}</strong>
              <small>{friendlyModelName(executive.model)}</small>
              <small class="sidebar-detail"><TokenCount tokens={executive.tokens} /> · {cardElapsed(executive)}</small></span>}
          </> : !collapsed && <span>Portfolio · Executive unavailable</span>}
        </a>
        <ul class="sidebar-branch">
          {getProjects().map((project) => {
            const status = projectStatus(project.id);
            const c = projectSummary(project.id);
            const count = c.running ? `${c.running} running` : c.needsYou ? `${c.needsYou} needs you`
              : c.failed ? `${c.failed} failed` : `${c.agents} agents`;
            const label = `${project.name} · ${status.label}`;
            return <li key={project.id}>
              <a href={projectHref(project.id)} data-testid="sidebar-project" data-project-id={project.id}
                aria-label={collapsed ? label : undefined} title={label}
                aria-current={route.pid === project.id ? 'page' : undefined}
                onMouseEnter={() => { hovered.current = project.id; highlight(); }}
                onMouseLeave={() => { hovered.current = null; highlight(); }}
                onFocus={() => { focused.current = project.id; highlight(); }}
                onBlur={() => { focused.current = null; highlight(); }}>
                <span class={`status-dot status-${status.key}`} role="img" aria-label={status.label} />
                {!collapsed && <span class="sidebar-project-body"><span class="sidebar-project-line">
                  <span class="sidebar-project-name">{project.name}</span><small>{count}</small>
                </span><ProjectBar pid={project.id} /></span>}
              </a>
            </li>;
          })}
        </ul>
        {collapsed ? <div class="sidebar-rail-indicators">
          {!!attentionTarget && <a href={sessionHref(undefined, attentionTarget.id)} class="rail-attention"
            aria-label="Attention: operator attention needed" title="Attention: operator attention needed">
            <ShellIcon name="attention" /></a>}
          <a href={settingsHref('providers')} class={`rail-usage usage-band band-${worst || 'unknown'}`}
            aria-label={`Usage: ${bandLabel(worst) || 'unavailable'}`} title={`Usage: ${bandLabel(worst) || 'unavailable'}`}>
            <ShellIcon name="usage" /></a>
        </div> : <>
          <SidebarAttention />
          <Activity />
        </>}
      </div>
      <footer class="sidebar-footer">
        <UsageMeters lineages={lineages} ceilings={ceilings} hidden={collapsed} />
        {!collapsed && <SetupProgressCard />}
        <div class="sidebar-bottom-links">
          <a href={setupHref()} title="Setup" aria-label="Setup"
            aria-current={route.view === 'setup' ? 'page' : undefined}>
            <ShellIcon name="setup" />{!collapsed && <span>Setup</span>}</a>
          <a href={settingsHref('providers')} title="Settings" aria-label="Settings"
            aria-current={route.view === 'settings' ? 'page' : undefined}>
            <ShellIcon name="settings" />{!collapsed && <span>Settings</span>}</a>
          <ThemeToggle collapsed={collapsed} />
        </div>
        {isSynthetic && <span class="synthetic-badge" role="note" data-testid="synthetic-badge"
          aria-label="Synthetic data — prototype, not connected to Odin's service"
          title="Synthetic data — prototype, not connected to Odin's service">
          <ShellIcon name="synthetic" />{!collapsed && <span>Synthetic data</span>}</span>}
      </footer>
    </nav>
    {!narrow && !collapsed && <div class="sidebar-resize" role="separator" aria-label="Sidebar width"
      tabIndex="0" aria-orientation="vertical" aria-valuenow={prefs.sidebarWidth}
      aria-valuemin={SIDEBAR_MIN} aria-valuemax={SIDEBAR_MAX} aria-controls="app-sidebar"
      onKeyDown={(e) => {
        const width = { ArrowLeft: prefs.sidebarWidth - 16, ArrowRight: prefs.sidebarWidth + 16,
          Home: SIDEBAR_MIN, End: SIDEBAR_MAX }[e.key];
        if (width !== undefined) { e.preventDefault(); resize(width); }
      }}
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.preventDefault(); e.currentTarget.focus(); e.currentTarget.setPointerCapture(e.pointerId);
        drag.current = { start: e.clientX, width: prefs.sidebarWidth }; setDragging(true);
      }}
      onPointerMove={(e) => { if (drag.current) resize(drag.current.width + e.clientX - drag.current.start); }}
      onPointerUp={(e) => {
        if (drag.current) e.currentTarget.releasePointerCapture(e.pointerId);
        drag.current = null; setDragging(false);
      }}
      onLostPointerCapture={() => { drag.current = null; setDragging(false); }} />}
  </Container>;
}
