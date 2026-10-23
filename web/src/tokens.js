// Compact token counts: 850 tok, 48.2k tok, 1.2M tok.
export function compactTokens(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return `${n}`;
}

// The headline figure: uncached input + cache write + output. Cache reads
// are EXCLUDED (they dominate long sessions; the detail panel shows the
// split). Returns null when the session's tokens are unknown: all four
// counters are integers or the record reports them as unknown — anything
// half-known is reported as unknown, never as a partial sum or zero.
export function headlineTokens(tokens) {
  if (!tokens || tokens.basis === 'unknown') return null;
  const counts = [tokens.uncached_input, tokens.cache_read, tokens.cache_write, tokens.output];
  if (!counts.every(Number.isInteger)) return null;
  return { value: counts[0] + counts[2] + counts[3], estimate: tokens.basis === 'estimate' };
}

export function formatTokens(tokens) {
  const h = headlineTokens(tokens);
  if (!h) return 'unknown';
  return `${h.estimate ? 'est. ' : ''}${compactTokens(h.value)} tok`;
}

// Sums each session's OWN headline tokens once. Returns the parts so the
// header and cards can animate the known figure; formatTokenSum renders
// the text. Unknown stays visible; estimates are marked.
export function tokenSum(list) {
  const sum = { known: 0, knownCount: 0, unknown: 0, estimate: false };
  for (const s of list) {
    const h = headlineTokens(s.tokens);
    if (!h) sum.unknown += 1;
    else {
      sum.known += h.value;
      sum.knownCount += 1;
      sum.estimate = sum.estimate || h.estimate;
    }
  }
  return sum;
}

export function formatTokenSum(t) {
  // With no known tokens there is no figure to show; unknown is never zero.
  if (!t.knownCount) return `unknown (${t.unknown})`;
  let text = `${t.estimate ? 'est. ' : ''}${compactTokens(t.known)} tok`;
  if (t.unknown) text += ` + unknown (${t.unknown})`;
  return text;
}

