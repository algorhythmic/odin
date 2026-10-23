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
  const { revision, cursor, pending, last } = driverState();
  const auto = autoplayState();
  return (
    <div class="update-driver" data-testid="update-driver">
      <details class="driver-details">
        <summary aria-label="Synthetic update details">Synthetic <span aria-hidden="true">ⓘ</span></summary>
        <div class="driver-metadata">
          <span>Synthetic updates ({datasetName} dataset): revision <strong data-testid="revision">{revision}</strong>
            {' '}· cursor <code>{cursor}</code> · {pending} pending</span>
          <p>{last ? STATUS_TEXT[last.status](last) : 'No update applied yet.'}</p>
        </div>
      </details>
      <button type="button" disabled={!pending} onClick={applyNextSyntheticEvent}
        aria-label="Apply next synthetic update"><span class="apply-text">Apply next synthetic update</span>
        <span class="apply-icon" aria-hidden="true">↦</span></button>
      <span class="autoplay">
        <button type="button" data-testid="autoplay-toggle" disabled={!auto.pending && !auto.playing}
          aria-pressed={auto.playing} onClick={auto.playing ? pauseAutoplay : playAutoplay}>
          {auto.playing ? 'Pause' : 'Play'}
        </button>
        <label class="autoplay-speed">Speed{' '}
          <select data-testid="autoplay-speed" value={auto.speed} disabled={!auto.pending && !auto.playing}
            onChange={(e) => setAutoplaySpeed(Number(e.currentTarget.value))}>
            {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
          </select>
        </label>
      </span>
      <span class="sr-only" role="status" data-testid="update-status">
        {last ? STATUS_TEXT[last.status](last) : 'No update applied yet.'}
      </span>
    </div>
  );
}
