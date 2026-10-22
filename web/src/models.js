// Presentation names for recorded model ids. Pure functions: no browser
// or fixture imports, so they are unit-tested under Node. The model id
// itself stays the record; these are display names only.

const MODEL_NAMES = {
  'claude-opus-5-5': 'Opus 5.5',
  'claude-sonnet-5-5': 'Sonnet 5.5',
  'claude-haiku-5-5': 'Haiku 5.5',
  'claude-fable-5-1': 'Fable 5.1',
};

// "Opus 5.5" for a known id, the raw id for an unmapped one, and the
// existing "model unknown" wording when none is recorded.
export function friendlyModelName(model) {
  if (!model) return 'model unknown';
  return MODEL_NAMES[model] || model;
}

// Which provider a recorded model belongs to, for the card monogram.
// Unknown ids and missing models get 'unknown': nothing is guessed.
export function providerFor(model) {
  if (typeof model !== 'string') return 'unknown';
  if (model.startsWith('claude-')) return 'anthropic';
  if (/^(gpt-|o\d|openai|codex)/.test(model)) return 'openai';
  return 'unknown';
}
