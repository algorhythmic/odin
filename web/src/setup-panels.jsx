import { friendlyModelName } from './models.js';
import { setupStore } from './setup-state.jsx';

const STATUS = {
  connected: 'Connected', waiting: 'Waiting for sign-in', expired: 'Expired', error: 'Error', not_connected: 'Not connected',
};
export const LABELS = { providers: 'Providers', harnesses: 'Harnesses', models: 'Models', roles: 'Roles', review: 'Review' };
export const TITLES = {
  providers: 'Connect your subscriptions',
  harnesses: 'Choose your harnesses',
  models: 'Choose your default models',
  roles: 'Configure Odin’s roles',
  review: 'Review your setup',
};
export const SUBTITLES = {
  providers: 'Use the harness’s own sign-in. Every account here is synthetic.',
  harnesses: 'Choose which installed harnesses Odin can use and their default sign-ins.',
  models: 'Set a default model and effort for each enabled harness.',
  roles: 'Choose who coordinates, implements and reviews each piece of work.',
  review: 'Check your draft before applying it to this synthetic session.',
};
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function Mark({ children }) {
  return <span class="setup-monogram" aria-hidden="true">{children}</span>;
}

export function Check({ done }) {
  return (
    <span class={`setup-check ${done ? 'done' : ''}`} aria-hidden="true">
      {done && <svg viewBox="0 0 16 16"><path d="m3 8 3 3 7-7" pathLength="1" /></svg>}
    </span>
  );
}

export function Progress({ value }) {
  return (
    <div class="setup-progress">
      <span>Setup {value} of 4</span>
      <progress aria-label="Setup progress" value={value} max="4" />
    </div>
  );
}

function Select({ label, value, options, onChange, disabled, describedby }) {
  const missing = !options.some((o) => o.id === value);
  return (
    <label class="setup-field">
      <span>{label}</span>
      <select aria-label={label} value={value} disabled={disabled} aria-describedby={describedby}
        onChange={(e) => onChange(e.currentTarget.value)}>
        {missing && <option value={value} disabled>{value ? 'Unavailable selection' : 'Choose a sign-in'}</option>}
        {options.map((o) => <option key={o.id} value={o.id}>{o.label || o.id}</option>)}
      </select>
    </label>
  );
}

function providerStatus(provider) {
  if (!provider.supported) return 'Unsupported';
  const priority = ['connected', 'waiting', 'error', 'expired', 'not_connected'];
  const status = priority.find((s) => provider.lineages.some((l) => l.status === s));
  return STATUS[status] || 'Not connected';
}

function SignInPanel({ provider, lineage }) {
  const code = lineage.id.length.toString().padStart(4, '0');
  return (
    <div class="setup-signin" role="region" aria-label={`Synthetic sign-in for ${lineage.label}`}>
      <strong>Synthetic sign-in</strong>
      <p>Verification URL: <span class="setup-url">https://example.invalid/device</span></p>
      <p>One-time code: <code>ODIN-{code}</code> (synthetic)</p>
      <p>Odin's service runs the sign-in; your browser never sees the credential.</p>
      <button type="button" onClick={() => setupStore.completeSignIn(provider.id, lineage.id)}>
        Simulate completed sign-in (synthetic)
      </button>
    </div>
  );
}

function LineageRow({ provider, lineage }) {
  const canConnect = lineage.status !== 'connected' && lineage.status !== 'waiting';
  return (
    <div class="setup-lineage" data-testid={`lineage-${lineage.id}`}>
      <div class="setup-lineage-main">
        <label class="setup-field">
          <span>Sign-in label</span>
          <input aria-label={`${provider.label} sign-in label ${lineage.id}`} value={lineage.label}
            onInput={(e) => setupStore.setLineageLabel(provider.id, lineage.id, e.currentTarget.value)} />
        </label>
        <span class={`setup-pill lineage-${lineage.status}`}>{STATUS[lineage.status]}</span>
        {lineage.status === 'connected' && (
          <button type="button" onClick={() => setupStore.disconnect(provider.id, lineage.id)}>
            Disconnect <span class="sr-only">{lineage.label}</span>
          </button>
        )}
        {canConnect && (
          <button type="button" onClick={() => setupStore.connect(provider.id, lineage.id)}>
            Connect <span class="sr-only">{lineage.label}</span>
          </button>
        )}
      </div>
      <p class="muted setup-caption">
        {lineage.status === 'connected' && <>{lineage.account_label} · {lineage.plan} · </>}
        Limit: {lineage.max_concurrent_turns} concurrent turn{lineage.max_concurrent_turns === 1 ? '' : 's'}
      </p>
      {lineage.reason && ['expired', 'error'].includes(lineage.status) && (
        <p class="setup-note blocking">{lineage.reason}</p>
      )}
      {lineage.status === 'waiting' && <SignInPanel provider={provider} lineage={lineage} />}
    </div>
  );
}

function ProviderCard({ provider }) {
  return (
    <section class="setup-provider" aria-label={provider.label}>
      <header class="setup-item-head">
        <Mark>{provider.label[0]}</Mark>
        <div>
          <h3>{provider.label}</h3>
          <p class="muted">{provider.subscription}</p>
        </div>
        <span class="setup-pill">{providerStatus(provider)}</span>
      </header>
      {!provider.supported ? <p class="muted">{provider.reason}</p> : (
        <>
          <p class="muted setup-caption">{provider.sign_in}</p>
          {provider.lineages.map((l) => <LineageRow key={l.id} provider={provider} lineage={l} />)}
          <button type="button" class="setup-text-button" onClick={() => setupStore.addLineage(provider.id)}>
            + Add another sign-in <span class="sr-only">for {provider.label}</span>
          </button>
        </>
      )}
    </section>
  );
}

export function ProvidersPanel({ state }) {
  return (
    <div class="setup-panels">
      {state.draft.providers.map((p) => <ProviderCard key={p.id} provider={p} />)}
    </div>
  );
}

function HarnessCard({ harness, state }) {
  const draft = state.draft.harnesses[harness.id];
  const lineages = setupStore.connectedLineages(harness.id);
  const provider = state.draft.providers.find((p) => p.id === harness.provider)?.label || 'Control fixture';
  return (
    <section class="setup-provider" aria-label={harness.label}>
      <header class="setup-item-head">
        <Mark>{harness.label[0]}</Mark>
        <div>
          <h3>{harness.label}</h3>
          <p class="muted">{harness.version} · {provider}</p>
        </div>
        <label class="setup-enable">
          <input type="checkbox" checked={draft?.enabled || false} disabled={harness.fixture_only || !lineages.length}
            onChange={(e) => setupStore.setHarness(harness.id, e.currentTarget.checked)} />
          Enable {harness.label}
        </label>
      </header>
      {harness.fixture_only ? <p class="muted">{harness.note}</p> : (
        <>
          <ul class="setup-capabilities" aria-label={`${harness.label} capabilities`}>
            {harness.capabilities.map((c) => <li key={c}>{c}</li>)}
          </ul>
          {!lineages.length && <p class="setup-note blocking">Connect a provider sign-in before enabling this harness.</p>}
          <Select label={`${harness.label} default sign-in`} value={draft.lineage} options={lineages} disabled={!draft.enabled}
            onChange={(v) => setupStore.setDefaultLineage(harness.id, v)} />
        </>
      )}
    </section>
  );
}

export function HarnessesPanel({ state }) {
  return (
    <div class="setup-panels">
      {state.catalogue.harnesses.map((h) => <HarnessCard key={h.id} harness={h} state={state} />)}
    </div>
  );
}

function Bars({ value, label }) {
  return (
    <span class="setup-bars" aria-label={`${label} ${value} of 5`}>
      <span>{label}</span>
      <span aria-hidden="true">
        {[1, 2, 3, 4, 5].map((i) => <i key={i} class={i <= value ? 'filled' : ''} />)}
      </span>
    </span>
  );
}

function EffortControl({ harness, model, effort, selected }) {
  return (
    <div class={`setup-effort-fold ${selected ? 'open' : ''}`}
      inert={!selected ? '' : undefined} aria-hidden={!selected ? 'true' : undefined}>
      <div>
        <fieldset class="setup-efforts">
          <legend>{harness.label} effort</legend>
          <div class="setup-segments" aria-label={`${harness.label} effort`}>
            {model.efforts.map((e) => (
              <button key={e} type="button" aria-pressed={e === effort} onClick={() => setupStore.setEffort(harness.id, e)}>
                {e}
              </button>
            ))}
          </div>
        </fieldset>
      </div>
    </div>
  );
}

function ModelOption({ harness, model, draft }) {
  const selected = model.id === draft.model;
  const name = friendlyModelName(model.id);
  return (
    <div class={`setup-model ${selected ? 'selected' : ''}`}>
      <label class="setup-model-choice">
        <input type="radio" name={`model-${harness.id}`} value={model.id} checked={selected}
          onChange={() => setupStore.selectModel(harness.id, model.id)} />
        <Mark>{name[0]}</Mark>
        <span class="setup-model-text">
          <strong>{name}</strong>
          <span class="muted">{model.purpose}</span>
        </span>
        <span class="setup-metrics">
          <Bars label="Speed" value={model.speed} />
          <Bars label="Depth" value={model.depth} />
        </span>
        <Check done={selected} />
      </label>
      <EffortControl harness={harness} model={model} effort={draft.effort} selected={selected} />
    </div>
  );
}

function ModelList({ harness, state }) {
  return (
    <fieldset class="setup-model-list">
      <legend>{harness.label}</legend>
      <p class="muted setup-caption">Speed and depth: synthetic descriptors, not measurements.</p>
      {state.catalogue.models[harness.id].map((m) => (
        <ModelOption key={m.id} harness={harness} model={m} draft={state.draft.harnesses[harness.id]} />
      ))}
    </fieldset>
  );
}

export function ModelsPanel({ state }) {
  const enabled = state.catalogue.harnesses.filter((h) => state.draft.harnesses[h.id]?.enabled);
  return (
    <div class="setup-panels">
      {!enabled.length && <p class="muted">Enable a harness in Harnesses to choose its default model.</p>}
      {enabled.map((h) => <ModelList key={h.id} harness={h} state={state} />)}
    </div>
  );
}

export function Presets({ state }) {
  return (
    <div class="setup-presets">
      <div class="setup-segments" role="group" aria-label="Role presets">
        {Object.entries(state.catalogue.presets).map(([id, preset]) => (
          <button key={id} type="button" aria-pressed={state.draft.preset === id} onClick={() => setupStore.applyPreset(id)}>
            {preset.label}
            {preset.illustrative && <small>Illustrative</small>}
          </button>
        ))}
      </div>
      <p class="muted">
        Preset: <strong>{state.catalogue.presets[state.draft.preset]?.label || 'Custom'}</strong>
        {state.draft.preset === 'cross_family' && ' · Operator’s current plan'}
      </p>
    </div>
  );
}

function LineageSummary({ notes }) {
  const shared = notes.filter((n) => n.kind === 'info' && n.lineage);
  if (!shared.length) return null;
  return (
    <div class="setup-lineage-summary" role="region" aria-label="Lineage sharing">
      <ul>
        {shared.map((note) => <li key={note.lineage} class="setup-note info">{note.message}</li>)}
      </ul>
    </div>
  );
}

function RoleNotes({ role, notes }) {
  return notes.map((note, i) => (
    <p key={note.message} class={`setup-note ${note.kind}`} id={`note-${role.id}-${i}`}>
      {note.kind === 'blocking' ? 'Required: ' : 'Warning: '}{note.message}
    </p>
  ));
}

function roleCellLabel(cell, value, options) {
  if (cell === 'model') return friendlyModelName(value);
  if (cell === 'effort') return value;
  return options.find((o) => o.id === value)?.label || value;
}

function RoleCell({ role, choice, cell, options, notes, review }) {
  const labels = { harness: 'harness', lineage: 'sign-in', model: 'model', effort: 'effort' };
  const describedby = notes.map((n, i) => `note-${role.id}-${i}`).join(' ') || undefined;
  return (
    <td>
      {review ? <span>{roleCellLabel(cell, choice[cell], options)}</span> : (
        <Select label={`${role.label} ${labels[cell]}`} value={choice[cell]} options={options} describedby={describedby}
          onChange={(v) => setupStore.changeRole(role.id, cell, v)} />
      )}
    </td>
  );
}

function RoleRow({ role, state, review }) {
  const choice = state.draft.roles[role.id];
  const lineages = setupStore.connectedLineages(choice.harness);
  const available = state.catalogue.models[choice.harness] || [];
  const models = available.map((m) => ({ id: m.id, label: friendlyModelName(m.id) }));
  const efforts = available.find((m) => m.id === choice.model)?.efforts.map((id) => ({ id })) || [];
  const notes = state.notes.filter((n) => n.role === role.id && ['blocking', 'warning'].includes(n.kind));
  const changed = !same(choice, state.applied.roles[role.id]) || (!state.completed.roles && review);
  const cells = [
    ['harness', state.catalogue.harnesses.filter((h) => state.draft.harnesses[h.id]?.enabled)],
    ['lineage', lineages], ['model', models], ['effort', efforts],
  ];
  return (
    <tr data-testid={`role-${role.id}`} class={review && changed ? 'setup-changed' : ''}>
      <th scope="row">
        <strong>{role.label}</strong>
        <span class="muted setup-role-description">{role.description}</span>
        {review && changed && <span class="setup-change-label">{state.completed.roles ? 'Changed' : 'Not yet applied'}</span>}
        <RoleNotes role={role} notes={notes} />
      </th>
      {cells.map(([cell, options]) => (
        <RoleCell key={cell} role={role} choice={choice} cell={cell} options={options} notes={notes} review={review} />
      ))}
    </tr>
  );
}

export function RolesTable({ state, review = false }) {
  return (
    <>
      <LineageSummary notes={state.notes} />
      <div class="setup-table-scroll" tabIndex="0" role="region" aria-label="Role configuration table">
        <table class="setup-role-table">
          <thead>
            <tr>
              {['Role', 'Harness', 'Sign-in', 'Model', 'Effort'].map((s) => <th key={s} scope="col">{s}</th>)}
            </tr>
          </thead>
          <tbody>
            {state.catalogue.roles.map((role) => <RoleRow key={role.id} role={role} state={state} review={review} />)}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function RolesPanel({ state }) {
  return <><Presets state={state} /><RolesTable state={state} /></>;
}

function ReviewProvider({ provider, applied }) {
  const changed = !same(provider, applied);
  const lineages = provider.lineages.map((l) => `${l.label}: ${STATUS[l.status]}`).join(' · ');
  return <li class={changed ? 'setup-changed' : ''}><strong>{provider.label}</strong> · {lineages}</li>;
}

function ReviewHarness({ harness, state }) {
  const draft = state.draft.harnesses[harness.id];
  const changed = !same(draft, state.applied.harnesses[harness.id]);
  const lineage = setupStore.connectedLineages(harness.id).find((l) => l.id === draft.lineage);
  const defaults = `${friendlyModelName(draft.model)} · ${draft.effort} · ${lineage?.label || 'Sign-in unavailable'}`;
  return <li class={changed ? 'setup-changed' : ''}><strong>{harness.label}</strong> · {draft.enabled ? defaults : 'Disabled'}</li>;
}

export function ReviewPanel({ state }) {
  return (
    <div class="setup-review">
      <section>
        <h3>Subscriptions and sign-ins</h3>
        <ul>
          {state.draft.providers.filter((p) => p.supported).map((p) => (
            <ReviewProvider key={p.id} provider={p} applied={state.applied.providers.find((a) => a.id === p.id)} />
          ))}
        </ul>
      </section>
      <section>
        <h3>Harnesses and default models</h3>
        <ul>
          {state.catalogue.harnesses.filter((h) => !h.fixture_only).map((h) => (
            <ReviewHarness key={h.id} harness={h} state={state} />
          ))}
        </ul>
      </section>
      <h3>Roles · {state.catalogue.presets[state.draft.preset]?.label || 'Custom'}</h3>
      <p class="muted">Marked rows differ from the applied state or have not yet been applied.</p>
      <RolesTable state={state} review />
    </div>
  );
}

export const PANELS = {
  providers: ProvidersPanel, harnesses: HarnessesPanel, models: ModelsPanel, roles: RolesPanel, review: ReviewPanel,
};
