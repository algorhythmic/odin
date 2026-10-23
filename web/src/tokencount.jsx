// Token figures that animate up to a new value when an update event
// changes them. An unknown is never animated: it shows the word
// "unknown" immediately, and a figure that becomes known later jumps in
// at once — no intermediate value is ever shown for an unknown.
import { useEffect, useState } from 'preact/hooks';
import { compactTokens, headlineTokens } from './data.js';
import { prefersReducedMotion } from './live.js';

const FRAMES = 8;
const FRAME_MS = 70;

// Steps the displayed integer toward `target` (or null for unknown).
export function useAnimatedNumber(target) {
  const [shown, setShown] = useState(target);
  useEffect(() => {
    if (target == null || shown == null || target === shown || prefersReducedMotion()) {
      setShown(target);
      return undefined;
    }
    const from = shown;
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      if (i >= FRAMES) {
        setShown(target);
        clearInterval(timer);
      } else {
        setShown(Math.round(from + (target - from) * (i / FRAMES)));
      }
    }, FRAME_MS);
    return () => clearInterval(timer);
  }, [target]); // shown is intentionally read latest inside the interval
  // Reduced motion and unknown transitions must not wait for another paint.
  return target == null || shown == null || prefersReducedMotion() ? target : shown;
}

// One session's headline figure (cache reads excluded), animated.
export function TokenCount({ tokens, testid }) {
  const h = headlineTokens(tokens);
  const shown = useAnimatedNumber(h ? h.value : null);
  return (
    <span data-testid={testid}>
      {shown == null ? 'unknown' : `${h?.estimate ? 'est. ' : ''}${compactTokens(shown)} tok`}
    </span>
  );
}

// A summed token figure (branch or project total). The known part
// animates; the " + unknown (n)" suffix is text and updates at once.
export function TokenSum({ sum, prefix = '', testid, compactUnknown = false }) {
  const shown = useAnimatedNumber(sum.knownCount ? sum.known : null);
  let text;
  if (shown == null) text = `unknown (${sum.unknown})`;
  else {
    text = `${sum.estimate ? 'est. ' : ''}${compactTokens(shown)} tok`;
    if (sum.unknown) text += compactUnknown ? ` + ${sum.unknown} unknown` : ` + unknown (${sum.unknown})`;
  }
  return <span data-testid={testid}>{prefix}{text}</span>;
}
