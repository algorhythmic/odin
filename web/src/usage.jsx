import { useState } from 'preact/hooks';
import { compactTokens } from './data.js';
import { admissionBand, availableSample, bandLabel, bandTicks, mostConstrainedSample, resetLabel, windowName } from './usage.js';
import { ShellIcon } from './shell-icons.jsx';

function WindowDetail({ sample: s, ceilings, lineageId }) {
  const band = admissionBand(s, ceilings);
  const ticks = bandTicks(s.label, ceilings);
  const description = `usage-description-${lineageId}-${s.label}`;
  return <div class="usage-window" data-testid="usage-window" data-label={s.label}>
    <div class="usage-window-head"><span title={s.label}>{windowName(s.label)}</span>
      {availableSample(s) && <strong>{s.utilization_percent} %</strong>}</div>
    <span class="sr-only" id={description}>{s.label}; {resetLabel(s)}.</span>
    {availableSample(s) ? <>
      <div class="usage-bar" role="meter" aria-label={windowName(s.label)} aria-describedby={description}
        title={s.label} aria-valuenow={s.utilization_percent} aria-valuemin="0" aria-valuemax="100"
        aria-valuetext={`${s.utilization_percent} %${band ? ` · ${bandLabel(band)}` : ''}; ${resetLabel(s)}`}>
        <span class="usage-fill" style={{ width: `${s.utilization_percent}%` }} />
        {ticks.map((tick, i) => <i class="usage-tick" key={tick} style={{ left: `${tick}%` }}
          title={`${bandLabel(['wind_down', 'ordinary_stop', 'handoff_only'][i])}: ${tick} %`} aria-hidden="true" />)}
      </div>
      {!!ticks.length && <span class="sr-only usage-thresholds">Band thresholds: {ticks.join(', ')} percent.</span>}
      <div class="usage-window-foot"><span>{resetLabel(s)}</span>
        {band && <span class={`usage-band band-${band}`} data-band={band}>{bandLabel(band)}</span>}</div>
    </> : <p class="usage-unavailable">Probe unavailable{s.reason ? ` · ${s.reason}` : ''}</p>}
  </div>;
}

function UsageMeter({ lineage: l, ceilings }) {
  const [expanded, setExpanded] = useState(false);
  const samples = l.usage?.samples || [];
  const constrained = mostConstrainedSample(samples, ceilings);
  const band = admissionBand(constrained, ceilings);
  const details = `usage-details-${l.id}`;
  const description = `usage-summary-description-${l.id}`;
  const summary = constrained
    ? `${windowName(constrained.label)} ${constrained.utilization_percent} %${band ? ` ${bandLabel(band)}` : ''}`
    : samples.length ? 'Probe unavailable' : 'No samples yet';
  return <article class="usage-meter" data-testid="usage-meter" data-lineage-id={l.id}>
    <header class="usage-summary">
      <span class="usage-monogram" role="img" aria-label={l.provider.label}>{l.provider.label[0]}</span>
      <strong class="usage-sign-in-label" title={l.label}>{l.label}</strong>
      <div class="usage-summary-reading" title={summary}>
        {constrained ? <>
          <div class="usage-summary-text"><span title={constrained.label}>{windowName(constrained.label)}</span>
            <strong>{constrained.utilization_percent} %</strong>
            {band && <span class={`usage-band band-${band}`} data-band={band}>{bandLabel(band)}</span>}</div>
          <span class="sr-only" id={description}>{constrained.label}; {resetLabel(constrained)}.</span>
          <div class="usage-bar usage-mini-bar" role="meter" aria-label={`${l.label}: ${windowName(constrained.label)}`}
            title={constrained.label} aria-describedby={description} aria-valuemin="0" aria-valuemax="100"
            aria-valuenow={constrained.utilization_percent} aria-valuetext={summary}>
            <span class="usage-fill" style={{ width: `${constrained.utilization_percent}%` }} />
          </div>
        </> : <span class="usage-summary-empty">{summary}</span>}
      </div>
      <button type="button" class="usage-disclosure" aria-label={`Usage details for ${l.label}`}
        title={`Usage details for ${l.label}`} aria-expanded={expanded} aria-controls={details}
        onClick={() => setExpanded(!expanded)}><ShellIcon name={expanded ? 'collapse' : 'expand'} /></button>
    </header>
    <div class="usage-details" id={details} data-testid="usage-details" hidden={!expanded}>
      {expanded && <>
        {!samples.length && <p class="muted">No samples yet</p>}
        {samples.map((s) => <WindowDetail key={s.label} sample={s} ceilings={ceilings} lineageId={l.id} />)}
        <p class="usage-tokens muted">{Number.isInteger(l.usage?.tokens?.value) && l.usage.tokens.value >= 0
        ? <>{l.usage.tokens.basis === 'estimate' ? 'est. ' : ''}{compactTokens(l.usage.tokens.value)} tok
          {' · '}{l.usage.tokens.window}</>
        : 'Token usage unknown'}</p>
      </>}
    </div>
  </article>;
}

export function UsageMeters({ lineages, ceilings, hidden }) {
  return <section class="sidebar-usage" aria-label="Provider usage" data-testid="sidebar-usage" hidden={hidden}>
    <h2>Usage</h2>
    <div class="usage-list">
      {lineages.map((l) => <UsageMeter key={l.id} lineage={l} ceilings={ceilings} />)}
    </div>
    <small class="muted" title="Reset intervals use each synthetic sample's observation time">Synthetic samples</small>
  </section>;
}
