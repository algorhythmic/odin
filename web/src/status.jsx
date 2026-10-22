// The status chip: an inline SVG icon with an accessible label next to
// the status word. Colour never carries meaning alone — the label is
// always rendered as text.
import { sessionStatus } from './data.js';
import { friendlyModelName, providerFor } from './models.js';

const ICONS = {
  spinner: <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="26 12" stroke-linecap="round" />,
  clock: (<>
    <circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" stroke-width="1.7" />
    <path d="M8 4.6v3.6l2.4 1.4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
  </>),
  check: <path d="M3.2 8.6l3.1 3.1L12.8 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />,
  triangle: (<>
    <path d="M8 2.6 L14.4 13.4 H1.6 Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
    <path d="M8 6.4v3.2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
    <circle cx="8" cy="11.4" r="0.9" fill="currentColor" />
  </>),
  square: <rect x="3.8" y="3.8" width="8.4" height="8.4" rx="1" fill="currentColor" />,
  pause: (<>
    <rect x="4.4" y="3.4" width="2.5" height="9.2" rx="0.8" fill="currentColor" />
    <rect x="9.1" y="3.4" width="2.5" height="9.2" rx="0.8" fill="currentColor" />
  </>),
  offline: (<>
    <circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" stroke-width="1.7" />
    <path d="M4.4 11.6 L11.6 4.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
  </>),
  question: <text x="8" y="11.8" text-anchor="middle" font-size="11" font-weight="700" fill="currentColor">?</text>,
};

export function StatusChip({ session, testid = 'state-label' }) {
  const st = sessionStatus(session);
  return (
    <span class={`status-chip status-${st.key}`} data-status={st.key} data-testid="status-chip">
      <svg class={`status-icon${st.icon === 'spinner' ? ' spin' : ''}`} viewBox="0 0 16 16"
        role="img" aria-label={st.label} data-testid={`status-icon-${st.icon}`}>
        {ICONS[st.icon] || ICONS.question}
      </svg>
      <span class="status-text" data-testid={testid}>{st.label}</span>
    </span>
  );
}

const PROVIDERS = {
  anthropic: { letter: 'A', name: 'Anthropic' },
  openai: { letter: 'O', name: 'OpenAI' },
  unknown: { letter: '?', name: 'Provider unknown' },
};

// A small monogram per provider: no external assets. The provider comes
// from the recorded model id; nothing is inferred when it is unknown.
export function ProviderLogo({ model }) {
  const p = PROVIDERS[providerFor(model)];
  return (
    <svg class="provider-logo" viewBox="0 0 18 18" role="img" aria-label={p.name}
      data-provider={providerFor(model)} data-testid="provider-logo">
      <rect x="0.75" y="0.75" width="16.5" height="16.5" rx="4.5" class="provider-box" />
      <text x="9" y="12.7" text-anchor="middle" font-size="10" font-weight="700" class="provider-letter">{p.letter}</text>
    </svg>
  );
}

export function ModelName({ model }) {
  return <span class="model-name" data-testid="model-name">{friendlyModelName(model)}</span>;
}

// Tool and integration glyphs shown before the task where the record
// carries them. Sessions without either field get no icons.
const TOOL_ICONS = {
  tool: <path d="M8.9 1.5a3 3 0 0 0-3.7 3.7L1.5 8.9a1.3 1.3 0 1 0 1.8 1.8l3.7-3.7a3 3 0 0 0 3.7-3.7L8.5 5.5 6.7 3.7Z" fill="currentColor" />,
  integration: (<>
    <circle cx="3.6" cy="6" r="2.1" fill="none" stroke="currentColor" stroke-width="1.3" />
    <circle cx="8.6" cy="6" r="2.1" fill="none" stroke="currentColor" stroke-width="1.3" />
    <path d="M5.7 6h0.8" stroke="currentColor" stroke-width="1.3" />
  </>),
};

export function ToolIcons({ session: s }) {
  const items = [
    ...(Array.isArray(s.tools) ? s.tools : []).map((name) => ({ kind: 'tool', name })),
    ...(Array.isArray(s.integrations) ? s.integrations : []).map((name) => ({ kind: 'integration', name })),
  ];
  if (!items.length) return null;
  return (
    <span class="task-tools">
      {items.map((it) => (
        <svg key={`${it.kind}-${it.name}`} class="task-tool" viewBox="0 0 12 12" role="img"
          aria-label={`${it.kind === 'tool' ? 'Tool' : 'Integration'}: ${it.name}`}>
          {TOOL_ICONS[it.kind]}
        </svg>
      ))}
    </span>
  );
}
