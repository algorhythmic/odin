import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { STEPS } from './setup.js';
import { setupStore, useSetup } from './setup-state.jsx';
import { setupHref, settingsHref } from './route.js';
import { Check, Progress, LABELS, TITLES, SUBTITLES, PANELS } from './setup-panels.jsx';

const CONTINUE_REASONS = {
  providers: 'Connect at least one sign-in to continue.',
  harnesses: 'Enable at least one harness with a connected default sign-in.',
  models: 'Choose defaults for an enabled harness.',
  roles: 'Resolve the required role notes to continue.',
};
const isCurrentStep = (step, current) => step === current || (step === 'review' && current === 'roles');

export function SetupProgressCard() {
  const state = useSetup();
  if (state.complete) return null;
  return (
    <a class="setup-footer-card" href={setupHref()} data-testid="setup-progress-card">
      <Progress value={state.progress} />
      <span class="muted">Finish configuring Odin <span aria-hidden="true">→</span></span>
    </a>
  );
}

function Checklist({ state, step }) {
  return (
    <aside class="setup-checklist" aria-label="Setup checklist">
      <h2>Setup checklist</h2>
      <Progress value={state.progress} />
      <ol>
        {STEPS.map((s) => {
          const current = isCurrentStep(step, s);
          const label = state.completed[s] ? 'Done' : current ? 'In progress' : 'To do';
          return (
            <li key={s}>
              <a href={setupHref(s)} aria-current={current ? 'step' : undefined}>
                <Check done={state.completed[s]} />
                <span>{LABELS[s]}<small>{label}</small></span>
              </a>
            </li>
          );
        })}
      </ol>
      <p class="muted">Synthetic: not saved. Reloading resets every choice.</p>
    </aside>
  );
}

function Stepper({ state, step }) {
  return (
    <nav class="setup-stepper" aria-label="Setup steps">
      <ol>
        {STEPS.map((s, i) => (
          <li key={s}>
            <a href={setupHref(s)} aria-current={isCurrentStep(step, s) ? 'step' : undefined}>
              {state.completed[s] ? <Check done /> : <span class="setup-step-number">{i + 1}</span>}
              <span>{LABELS[s]}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function PanelMotion({ id, children }) {
  const previous = useRef(null);
  const [leaving, setLeaving] = useState(null);
  useLayoutEffect(() => {
    const old = previous.current;
    if (!old || old.id === id || matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    setLeaving(old);
    const timer = setTimeout(() => setLeaving(null), 240);
    return () => { clearTimeout(timer); setLeaving(null); };
  }, [id]);
  useLayoutEffect(() => { previous.current = { id, children }; });
  return (
    <div class="setup-motion">
      {leaving && <div class="setup-panel-leaving" aria-hidden="true" inert="">{leaving.children}</div>}
      <div key={id} class="setup-panel-current">{children}</div>
    </div>
  );
}

function ApplyControl({ state }) {
  const blockers = state.notes.filter((n) => n.kind === 'blocking');
  const ready = STEPS.every((s) => setupStore.canContinue(s));
  const reason = [...new Set(blockers.map((n) => n.message))].join(' ')
    || 'Connect a provider and enable a harness with a default model before applying.';
  return (
    <div class="setup-apply">
      <button type="button" class="setup-primary" disabled={!ready}
        aria-describedby={!ready ? 'setup-apply-reason' : undefined} onClick={() => setupStore.apply()}>
        Apply
      </button>
      {!ready && <p class="setup-note blocking" id="setup-apply-reason">{reason}</p>}
    </div>
  );
}

function SettingsTabs({ section }) {
  return (
    <nav class="setup-settings-tabs" aria-label="Settings sections">
      {STEPS.map((s) => (
        <a key={s} href={settingsHref(s)} aria-current={s === section ? 'page' : undefined}>{LABELS[s]}</a>
      ))}
    </nav>
  );
}

function StepActions({ state, current, advance }) {
  const index = STEPS.indexOf(current);
  const canContinue = setupStore.canContinue(current);
  const previous = current === 'review' ? 'roles' : STEPS[index - 1];
  return (
    <>
      <footer class="setup-step-actions">
        {['harnesses', 'models'].includes(current) && (
          <a class="muted setup-skip" href={setupHref(STEPS[index + 1])}>Skip for now</a>
        )}
        <div class="setup-navigation">
          {current !== 'providers' && <a class="setup-button" href={setupHref(previous)}>‹ Back</a>}
          {current === 'review' ? <ApplyControl state={state} /> : (
            <button type="button" class="setup-primary" disabled={!canContinue}
              aria-describedby={!canContinue ? 'setup-continue-reason' : undefined} onClick={advance}>
              Continue <span aria-hidden="true">›</span>
            </button>
          )}
        </div>
      </footer>
      {current !== 'review' && !canContinue && (
        <p class="setup-note blocking setup-continue-note" id="setup-continue-reason">{CONTINUE_REASONS[current]}</p>
      )}
    </>
  );
}

function SaveBar({ state }) {
  return (
    <div class="setup-save-bar" data-testid="setup-save-bar">
      <span>Unsaved synthetic changes</span>
      <div>
        <button type="button" onClick={() => setupStore.discard()}>Discard</button>
        <ApplyControl state={state} />
      </div>
    </div>
  );
}

export function SetupPage({ step, section }) {
  const state = useSetup();
  const current = section || step || setupStore.firstIncomplete();
  const Panel = PANELS[current];
  const index = STEPS.indexOf(current);
  const titleRef = useRef(null);
  const previous = useRef(current);
  useEffect(() => {
    if (!section && !step) location.replace(setupHref(setupStore.firstIncomplete()));
  }, [section, step]);
  useEffect(() => {
    if (previous.current !== current) titleRef.current?.focus();
    previous.current = current;
  }, [current]);
  const advance = () => {
    if (setupStore.completeStep(current)) location.hash = setupHref(STEPS[index + 1] || 'review');
  };
  const eyebrow = section ? 'Settings' : current === 'review' ? 'Step 4 of 4 · Review' : `Step ${index + 1} of 4`;
  const intro = current === 'roles'
    ? 'Preset choices stay editable. Constraint notes explain what is required.'
    : 'These choices apply only in memory for this prototype.';
  return (
    <section class={`setup-page ${section ? 'setup-settings' : ''}`} data-testid="setup-placeholder" aria-labelledby="setup-title">
      <header class="setup-page-head">
        <span class="eyebrow">{eyebrow} · Synthetic: not saved</span>
        <h1 id="setup-title" ref={titleRef} tabIndex="-1">{section ? `Settings: ${LABELS[current]}` : TITLES[current]}</h1>
        <p class="muted">{SUBTITLES[current]}</p>
      </header>
      {section ? <SettingsTabs section={section} /> : <Stepper state={state} step={current} />}
      <div class="setup-layout">
        <div class="setup-main">
          <div class="setup-step-card" role="region" aria-labelledby="setup-title">
            <PanelMotion id={current}>
              <div class="setup-panel-content">
                <p class="muted setup-panel-intro">{intro}</p>
                <Panel state={state} />
              </div>
            </PanelMotion>
            {!section && <StepActions state={state} current={current} advance={advance} />}
          </div>
          {state.appliedOnce && !state.dirty && (
            <p class="setup-applied" role="status"><Check done />Applied (synthetic, not saved)</p>
          )}
          {section && state.dirty && <SaveBar state={state} />}
        </div>
        {!section && <Checklist state={state} step={current} />}
      </div>
    </section>
  );
}
