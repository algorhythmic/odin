import { applyNextSyntheticEvent, datasetName, driverState } from './data.js';

const STATUS_TEXT = {
  applied: (r) => `Applied ${r.event_id} (${r.type}) at revision ${r.revision}.`,
  duplicate: (r) => `Ignored ${r.event_id}: already applied (re-delivered event).`,
  gap: (r) => `Not applied ${r.event_id}: revision ${r.revision} skips ahead of ${r.current}; a fresh snapshot is needed.`,
  stale: (r) => `Ignored ${r.event_id}: revision ${r.revision} is not newer than ${r.current}.`,
  rejected: (r) => `Rejected ${r.event_id}: ${r.reason}.`,
};

// Drives the fixture's update events by hand so update handling can be
// exercised without a service. It re-renders through the data version.
export function UpdateDriver() {
  const { revision, cursor, pending, last } = driverState();
  return (
    <div class="update-driver" data-testid="update-driver">
      <span>Synthetic updates ({datasetName} dataset): revision <strong data-testid="revision">{revision}</strong> · cursor <code>{cursor}</code> · {pending} pending</span>
      <button type="button" disabled={!pending} onClick={applyNextSyntheticEvent}>Apply next synthetic update</button>
      <span class="muted" role="status" data-testid="update-status">{last ? STATUS_TEXT[last.status](last) : 'No update applied yet.'}</span>
    </div>
  );
}
