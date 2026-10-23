import { useEffect, useRef, useState } from 'preact/hooks';
import { autoplayState, cardElapsed, getExecutive, getSnapshot, pauseAutoplay, playAutoplay } from './data.js';
import { dashboardKPIs, dashboardTime, filterPriority, FILTERS, priorityCounts, priorityItems,
  projectOverview, recentActivity, relativeTime, STEP_LABELS } from './dashboard.js';
import { agentsHref, historyHref, projectHref, sessionHref, setupHref, settingsHref } from './route.js';
import { useSetup } from './setup-state.jsx';
import { STEPS } from './setup.js';
import { connectedUsage } from './usage.js';
import { TokenCount, TokenSum, useAnimatedNumber } from './tokencount.jsx';
import { friendlyModelName } from './models.js';
import { Check } from './setup-panels.jsx';

const ICONS = { setup: '☷', needs: '◷', failed: '△', decision: '◇', usage: '◴', host: '⊘' };
const linkFor = (item) => item.kind === 'setup' ? setupHref(item.step) : item.kind === 'usage'
  ? settingsHref('providers') : sessionHref(null, item.sessionId);
const projectName = (snapshot, pid) => snapshot.projects.find((p) => p.id === pid)?.name || 'Portfolio';

function Welcome({ state }) {
  return <section class="dashboard-welcome" data-testid="welcome" aria-labelledby="welcome-title">
    <span class="eyebrow">Welcome to Odin</span>
    <h1 id="welcome-title">Your agents, working together.</h1>
    <p class="muted">Odin coordinates your agents across projects and keeps you informed.</p>
    <div class="welcome-checklist">
      <h2>Make Odin yours</h2><span class="muted">Four steps to get started</span>
      <ol>{STEPS.map((step, i) => <li key={step}><Check done={state.completed[step]} />
        <span><strong>{STEP_LABELS[step]}</strong><small>Step {i + 1} of 4</small></span></li>)}</ol>
      <a class="setup-primary" href={setupHref('providers')}>Connect your first subscription <span aria-hidden="true">→</span></a>
    </div>
  </section>;
}

function PriorityRow({ item, snapshot, now, setup }) {
  const [expanded, setExpanded] = useState(false);
  const activity = recentActivity(snapshot).filter((e) => e.session_id === item.sessionId).slice(0, 3);
  const id = `priority-${item.id}`;
  return <li class={`priority-row priority-${item.kind}`} data-testid="priority-item" data-kind={item.kind}
    data-attention-session={item.sessionId}>
    <div class="priority-line">
      <span class="priority-icon" aria-hidden="true">{ICONS[item.kind]}</span>
      <button type="button" class="priority-disclosure" aria-expanded={expanded} aria-controls={id}
        onClick={() => setExpanded(!expanded)}>
        <strong title={item.title}>{item.title}</strong>
        <small title={item.kind === 'setup' ? `Setup · ${setup.progress} of 4 complete`
          : `${projectName(snapshot, item.projectId)} · ${item.role || 'Role unknown'}`}>
          {item.kind === 'setup' ? `${setup.progress}/4`
            : `${projectName(snapshot, item.projectId)} · ${item.role || 'Role unknown'}`}</small>
        <span class="priority-description" title={item.description}>{item.description}</span>
        {item.kind === 'setup' && <progress class="dashboard-progress" aria-label="Setup progress"
          max="4" value={setup.progress} />}
      </button>
      <time dateTime={item.at} title={item.at}>{item.kind === 'setup' ? 'Not applied' : relativeTime(item.at, now)}</time>
      <a class="dashboard-open" href={linkFor(item)}>{item.kind === 'setup' ? 'Continue setup' : 'Open'}</a>
    </div>
    <div class={`priority-fold ${expanded ? 'open' : ''}`} id={id} aria-hidden={!expanded} inert={!expanded ? '' : undefined}>
      <div>
        <p class="priority-full-summary">{item.title} · {projectName(snapshot, item.projectId)}
          {' · '}{item.role || (item.kind === 'setup' ? 'Setup' : 'Role unknown')} · {item.description}</p>
        {item.decision && <div class="priority-proposal">
          <span>Requested by <code>{item.decision.requested_by}</code> · Proposal revision {item.decision.proposal.revision}</span>
          <code>{item.decision.proposal.digest}</code>
          <span class="decision-actions"><button disabled aria-describedby={`${id}-reason`}>Approve</button>
            <button disabled aria-describedby={`${id}-reason`}>Deny</button>
            <small id={`${id}-reason`}>Commands are not connected</small></span>
        </div>}
        {item.kind === 'setup' ? <ul class="priority-steps">{STEPS.map((step) => <li key={step}>
        <Check done={setup.completed[step]} /><a href={setupHref(step)}>{STEP_LABELS[step]}</a></li>)}</ul>
        : activity.length ? <ul>{activity.map((e) => <li key={e.id}>{e.text}
          <time>{relativeTime(e.at, now)}</time></li>)}</ul> : <p class="muted">No recent activity recorded.</p>}</div>
    </div>
  </li>;
}

function PriorityQueue({ items, snapshot, now, setup }) {
  const [filter, setFilter] = useState('All');
  const [all, setAll] = useState(false);
  const counts = priorityCounts(items);
  const filtered = filterPriority(items, filter);
  const visible = all ? filtered : filtered.slice(0, 8);
  return <section class="dashboard-panel dashboard-priority" aria-labelledby="priority-title" data-testid="priority-queue">
    <header class="dashboard-section-head"><h2 id="priority-title">Priority queue</h2>
      <span class="muted">{items.length} open</span></header>
    <div class="dashboard-filters" role="group" aria-label="Priority filters">
      {FILTERS.map((f) => <button key={f} aria-pressed={filter === f} onClick={() => { setFilter(f); setAll(false); }}>
        {f} <span>{counts[f]}</span></button>)}
    </div>
    {visible.length ? <ul class="priority-list" id="priority-list">{visible.map((item) =>
      <PriorityRow key={item.id} item={item} snapshot={snapshot} now={now} setup={setup} />)}</ul>
      : <p class="dashboard-empty">Nothing needs you</p>}
    {filtered.length > 8 && <button class="dashboard-more" aria-controls="priority-list" aria-expanded={all}
      onClick={() => setAll(!all)}>{all ? 'Show less' : `+${filtered.length - visible.length} more`}</button>}
  </section>;
}

function KPI({ label, value, name }) {
  const shown = useAnimatedNumber(value);
  return <div class="dashboard-kpi" data-testid={`kpi-${name}`}><span>{label}</span><strong>{shown}</strong></div>;
}

export function Dashboard() {
  const state = useSetup();
  const snapshot = getSnapshot();
  const auto = autoplayState();
  const anchor = dashboardTime(snapshot);
  const clock = useRef({ anchor, tick: 0 });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!auto.playing) return undefined;
    const timer = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, [auto.playing]);
  if (clock.current.anchor !== anchor) clock.current = { anchor, tick };
  const now = anchor + (tick - clock.current.tick) * 1000;
  if (!getExecutive() && !connectedUsage(state).length) return <Welcome state={state} />;
  const kpis = dashboardKPIs(snapshot);
  const items = priorityItems(snapshot, state);
  const running = snapshot.sessions.filter((s) => s.lifecycle === 'running');
  return <div class="dashboard" data-testid="dashboard">
    <header class="dashboard-head"><div><h1>Dashboard</h1><span class="muted">Your portfolio at a glance</span></div>
      <a href={agentsHref()}>Agents <span aria-hidden="true">↗</span></a>
      <span class="dashboard-play">Synthetic data · <button data-testid="autoplay-toggle" aria-pressed={auto.playing}
        disabled={!auto.available} onClick={auto.playing ? pauseAutoplay : playAutoplay}>
        {auto.playing ? 'Pause' : 'Play'}</button></span>
    </header>
    <div class="dashboard-grid">
      <PriorityQueue items={items} snapshot={snapshot} now={now} setup={state} />
      <div class="dashboard-summary">
        <section class="dashboard-kpis" aria-label="Portfolio totals" data-testid="dashboard-kpis">
          <KPI label="Running" name="running" value={kpis.running} />
          <KPI label="Needs you" name="needs" value={kpis.needsYou} />
          <KPI label="Failed" name="failed" value={kpis.failed} />
          <KPI label="Ended in snapshot" name="ended" value={kpis.ended} />
          <div class="dashboard-kpi kpi-tokens"><span>Tokens · cache reads excluded</span>
            <strong><TokenSum sum={kpis.tokens} compactUnknown testid="kpi-tokens" /></strong></div>
        </section>
        <section class="dashboard-panel dashboard-projects" aria-labelledby="projects-title">
          <header class="dashboard-section-head"><h2 id="projects-title">Projects</h2>
            <span class="muted">{snapshot.projects.length}</span></header>
          <div class="dashboard-project-grid">{snapshot.projects.map((p) => {
            const info = projectOverview(snapshot, p.id);
            const total = Object.values(info.buckets).reduce((a, b) => a + b, 0);
            const text = Object.entries(info.buckets).map(([key, count]) => `${count} ${key.replaceAll('-', ' ')}`).join(', ');
            const counts = `${info.agents} agents · ${info.running} running · ${info.needsYou} needs you · ${info.failed} failed`;
            return <a key={p.id} href={projectHref(p.id)} class="dashboard-project" data-testid="dashboard-project"
              title={`${p.name} · ${counts} · ${info.at ? `Last activity ${relativeTime(info.at, now)}` : 'No activity yet'}`}>
              <strong title={p.name}>{p.name}</strong>
              <span class="dashboard-status-bar" role="img" aria-label={text || 'No active sessions'}>
                {Object.entries(info.buckets).map(([key, count]) => <i key={key} class={`status-${key}`}
                  style={{ width: `${count / total * 100}%` }} />)}</span>
              <span class="dashboard-project-counts" role="group" aria-label={counts} title={counts}>
                <span title={`${info.agents} agents`}>{info.agents}</span>
                <span class="status-running" title={`${info.running} running`}>
                  <i class="status-dot" aria-hidden="true" />{info.running}</span>
                <span class="status-needs-you" title={`${info.needsYou} needs you`}>
                  <i class="status-dot" aria-hidden="true" />{info.needsYou}</span>
                <span class="status-failed" title={`${info.failed} failed`}>
                  <i class="status-dot" aria-hidden="true" />{info.failed}</span>
              </span>
              <span class="dashboard-project-tokens"><TokenSum sum={info.tokens} compactUnknown /></span>
              <small class="sr-only">{info.at ? `Last activity ${relativeTime(info.at, now)}` : 'No activity yet'}</small>
            </a>;
          })}</div>
          {!snapshot.projects.length && <p class="dashboard-empty">No projects yet</p>}
        </section>
      </div>
      <section class="dashboard-panel dashboard-running" aria-labelledby="running-title">
        <header class="dashboard-section-head"><h2 id="running-title">Running now</h2>
          <span class="muted">{running.length} agents</span></header>
        {running.length > 0 && <table class="dashboard-table" data-testid="running-table"><thead><tr>
          {['Role / Project', 'Model / Harness', 'Elapsed', 'Tokens'].map((label) => <th key={label}>{label}</th>)}
        </tr></thead><tbody>{running.map((s) => <tr key={s.id} data-session-id={s.id}>
          <td><a href={sessionHref(null, s.id)} title={`${s.role} · ${projectName(snapshot, s.project_id)}`}>
            {s.role}<small> · {projectName(snapshot, s.project_id)}</small></a></td>
          <td title={`${friendlyModelName(s.model)} · ${s.harness || 'Harness unknown'}`}>
            {friendlyModelName(s.model)}<small class="dashboard-harness">{s.harness || 'Harness unknown'}</small></td>
          <td>{cardElapsed(s)}</td><td><TokenCount tokens={s.tokens} /></td>
        </tr>)}</tbody></table>}
        {!running.length && <p class="dashboard-empty">No agents running</p>}
      </section>
      <section class="dashboard-panel dashboard-activity" aria-labelledby="activity-title" data-testid="recent-activity">
        <header class="dashboard-section-head"><h2 id="activity-title">Recent activity</h2><a href={historyHref()}>History</a></header>
        {recentActivity(snapshot).length > 0 && <ul>{recentActivity(snapshot).slice(0, 12).map((e) =>
          <li key={e.id} data-event-id={e.id}>
          <a href={sessionHref(null, e.session_id)} title={`${projectName(snapshot, e.projectId)} · ${e.text}`}>{e.text}</a>
          <time dateTime={e.at} title={e.at}>{relativeTime(e.at, now)}</time></li>)}</ul>}
        {!recentActivity(snapshot).length && <p class="dashboard-empty">No activity yet</p>}
      </section>
    </div>
  </div>;
}
