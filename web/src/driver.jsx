import {
  applyNextSyntheticEvent, autoplayState, datasetName, driverState,
  pauseAutoplay, playAutoplay, setAutoplaySpeed,
} from './data.js';
import { SPEEDS } from './live.js';

const STATUS_TEXT = {
  applied: (r) => `Applied ${r.event_id} (${r.type}) at revision ${r.revision}.`,
  duplicate: (r) => `Ignored ${r.event_id}: already applied (re-delivered event).`,
  gap: (r) => `Not applied ${r.event_id}: revision ${r.revision} skips ahead of ${r.current}; a fresh snapshot is needed.`,
  stale: (r) => `Ignored ${r.event_id}: revision ${r.revision} is not newer than ${r.current}.`,
  rejected: (r) => `Rejected ${r.event_id}: ${r.reason}.`,
};

// Drives the fixture's update events, by hand or on the autoplay timer,
// so update handling can be exercised without a service. It re-renders
// through the data version.
export function UpdateDriver() {
  const { revision, cursor, pending, last, generating } = driverState();
  const auto = autoplayState();
  return (
    <div class="update-driver" data-testid="update-driver">
      <span>Synthetic updates ({datasetName} dataset): revision <strong data-testid="revision">{revision}</strong> · cursor <code>{cursor}</code> · {pending} pending</span>
      <button type="button" disabled={!auto.available} onClick={applyNextSyntheticEvent}>Apply next synthetic update</button>
      <span class="autoplay">
        <button type="button" data-testid="autoplay-toggle" disabled={!auto.available}
          aria-pressed={auto.playing} onClick={auto.playing ? pauseAutoplay : playAutoplay}>
          {auto.playing ? 'Pause' : 'Play'}
        </button>
        <label class="autoplay-speed">Speed{' '}
          <select data-testid="autoplay-speed" value={auto.speed} disabled={!auto.available}
            onChange={(e) => setAutoplaySpeed(Number(e.currentTarget.value))}>
            {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
          </select>
        </label>
      </span>
      <span class="muted" role="status" data-testid="update-status">
        {last ? STATUS_TEXT[last.status](last) : 'No update applied yet.'}
        {generating && <> · <span>Generating synthetic activity</span></>}
      </span>
    </div>
  );
}
