// W3a admission describes Odin's decisions, never a provider-enforced stop.
export const BANDS = ['clear', 'wind_down', 'ordinary_stop', 'handoff_only'];
export const bandLabel = (band) => band?.replaceAll('_', ' ');
export function bandTicks(label, ceilings) {
  const ceiling = Object.hasOwn(ceilings || {}, label) ? ceilings[label] : null;
  return Number.isFinite(ceiling) && ceiling >= 10 && ceiling <= 100
    ? [ceiling - 10, ceiling - 5, ceiling] : [];
}
export const availableSample = (sample) => sample?.status === 'available'
  && Number.isFinite(sample.utilization_percent) && sample.utilization_percent >= 0 && sample.utilization_percent <= 100;

export function admissionBand(sample, ceilings) {
  const ticks = bandTicks(sample?.label, ceilings);
  const n = sample?.utilization_percent;
  if (!availableSample(sample) || !ticks.length) return null;
  return BANDS[ticks.filter((tick) => n >= tick).length];
}
// Admission severity wins before percentage because window ceilings differ.
export function mostConstrainedSample(samples, ceilings) {
  const rank = (s) => Math.max(0, BANDS.indexOf(admissionBand(s, ceilings)));
  return (samples || []).filter(availableSample).reduce((worst, s) => {
    if (!worst || rank(s) > rank(worst)) return s;
    return rank(s) === rank(worst) && s.utilization_percent > worst.utilization_percent ? s : worst;
  }, null);
}
export function windowName(label) {
  if (/^(claude|codex)\.five_hour$/.test(label)) return '5-hour';
  if (/^(claude|codex)\.weekly$/.test(label)) return 'Weekly';
  const model = /^claude\.weekly\.(.+)$/.exec(label)?.[1];
  return model ? `Weekly · ${model.replaceAll('_', ' ').replace(/\b[a-z]/g, (c) => c.toUpperCase())}` : label;
}
export function connectedUsage(state) {
  return state.draft.providers.flatMap((p) => p.lineages.filter((l) => l.status === 'connected')
    .map((l) => ({ ...l, provider: p, usage: state.catalogue.usage?.lineages[l.id] })));
}
export function worstBand(lineages, ceilings) {
  const bands = lineages.flatMap((l) => (l.usage?.samples || []).map((s) => admissionBand(s, ceilings))).filter(Boolean);
  return bands.length ? BANDS[Math.max(...bands.map((b) => BANDS.indexOf(b)))] : null;
}
// Synthetic time stays anchored to the sample so reloads show the same evidence.
export function resetLabel(sample) {
  const ms = Date.parse(sample.resets_at) - Date.parse(sample.observed_at);
  if (!Number.isFinite(ms)) return 'reset unknown';
  const minutes = Math.max(0, Math.ceil(ms / 60000));
  if (minutes >= 1440) {
    const hours = Math.floor(minutes % 1440 / 60);
    return `resets in ${Math.floor(minutes / 1440)}d${hours ? ` ${hours}h` : ''}`;
  }
  return `resets in ${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
