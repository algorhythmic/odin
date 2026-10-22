// SYNTHETIC fixtures for the Odin web app prototype.
//
// Nothing here comes from Odin's service or any real session. The records
// live in web/fixtures/*.json in the draft projection shape described in
// docs/design/WEB-APP-PROJECTION.md, so a service could later emit the same
// files unchanged. The large dataset is generated from a fixed seed.
//
// Semantics the prototype must preserve:
// - parent_session_id is session ANCESTRY only. null means a root, or an
//   imported session whose parent is unknown. Never inferred.
// - Review, delegation, run association and assignment ownership are typed
//   entries in `relationships`, never parent edges.
// - tokens cover the session's OWN turns; all four counters null (basis
//   "unknown") means unknown. Token budget values are arbitrary synthetic
//   values, not real limits.
// - A resumption keeps the same session; a new attempt is a distinct one.
import snapshot from '../../fixtures/default-snapshot.json';
import details from '../../fixtures/default-details.json';
import eventFile from '../../fixtures/default-events.json';
import { generateLargeSnapshot, loadLargeTranscriptPage, LARGE_SPEC } from './large.js';

export const synthetic = true;

// The large dataset is opt-in through ?dataset=large and has no update events.
export function loadDataset(name) {
  if (name === 'large') return { snapshot: generateLargeSnapshot(), events: [] };
  return { snapshot: structuredClone(snapshot), events: structuredClone(eventFile.events) };
}

// Simulates a paginated detail request: transcripts and evidence load only
// for the selected session, one page at a time. The result has the draft
// per-session detail shape (schemas/web-projection-session-detail.schema.json).
export function loadSessionDetail(dataset, session, page = 1) {
  let result;
  if (dataset === 'large') {
    const { entries, pages } = loadLargeTranscriptPage(session.id, page);
    result = { session_id: session.id, page, pages, page_size: LARGE_SPEC.pageSize, transcript: entries, evidence: [] };
  } else {
    const all = details.transcripts[session.id]
      || [{ seq: 1, at: session.observed_at, speaker: session.id, text: `Synthetic transcript entry for ${session.id}.` }];
    const size = details.page_size;
    const pages = Math.max(1, Math.ceil(all.length / size));
    const p = Math.min(Math.max(1, page), pages);
    result = { session_id: session.id, page: p, pages, page_size: size, transcript: all.slice((p - 1) * size, p * size), evidence: details.evidence[session.id] || [] };
  }
  return new Promise((resolve) => { setTimeout(() => resolve(result), 30); });
}
