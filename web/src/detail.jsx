import { useEffect, useState } from 'preact/hooks';
import {
  OUTCOME_LABELS, PROGRESS_LABELS, RELATION_LABELS, branchCost, formatCost, formatElapsed, getAssignment,
  getSession, lifecycleLabel, lineageLabel, loadSessionDetail, relationshipsOf, runsForSession,
} from './data.js';
import { sessionHref } from './route.js';

const ENDED = new Set(['ended', 'retired']);

function runText(session, run) {
  const outcome = OUTCOME_LABELS[run.outcome] || `Outcome unknown (${run.outcome})`;
  if (ENDED.has(session.lifecycle) && run.outcome !== 'verified') return `Session ended — run not verified (${outcome})`;
  return outcome;
}

function recordLabel(id) {
  const s = getSession(id);
  return s ? `${s.role} (${id})` : id;
}

export function DetailPanel({ session: s, childMap, onSelect }) {
  const [detail, setDetail] = useState(null);
  useEffect(() => {
    let live = true;
    setDetail(null);
    loadSessionDetail(s.id).then((d) => { if (live) setDetail(d); });
    return () => { live = false; };
  }, [s.id]);

  const assignment = getAssignment(s.assignment_id);
  const parent = s.parent_session_id ? getSession(s.parent_session_id) : null;
  const lineage = lineageLabel(s);
  // A target in another project opens in that project's workspace; an
  // unknown id opens the not-found response rather than doing nothing.
  const goTo = (id) => {
    const target = getSession(id);
    if (!target || target.project_id === s.project_id) onSelect(id);
    else location.hash = sessionHref(target.project_id, id);
  };
  const runs = runsForSession(s.id);
  const relations = relationshipsOf(s.id);

  return (
    <div class="detail-panel" data-testid="detail-panel" data-session-id={s.id}>
      <h2>{s.role} <code>{s.id}</code></h2>
      <dl class="facts">
        <dt>Session state</dt>
        <dd><span class={`state state-${s.lifecycle}`} data-testid="detail-state">{lifecycleLabel(s.lifecycle)}</span>
          {s.needs_operator_input && <span class="tag tag-needs-input">Needs input</span>}</dd>
        <dt>Observed</dt>
        <dd>{s.observed_at}{s.stale && <strong class="tag tag-stale"> Stale observation</strong>}</dd>
        <dt>Model</dt><dd>{s.model || 'model unknown'}</dd>
        <dt>Provenance</dt><dd>{s.provenance === 'imported' ? 'Imported record' : 'Recorded by Odin'} (synthetic)</dd>
        <dt>Started by</dt>
        <dd data-testid="started-by">
          {parent ? recordLabel(parent.id)
            : s.parent_session_id ? `${s.parent_session_id} (not in this view; not inferred)`
            : s.provenance === 'imported' ? 'Parent unknown (imported; not inferred)' : 'No recorded parent (root)'}
        </dd>
        {lineage && <><dt>Lifecycle identity</dt><dd data-testid="detail-lineage">{lineage}
          {s.resumption && <> — resumed from host session {s.resumption.resumed_from_host_session} at {s.resumption.resumed_at}</>}
        </dd></>}
      </dl>
      <div class="actions-row">
        <button type="button" disabled={!parent} onClick={() => parent && goTo(parent.id)}>Go to parent</button>
        {s.previous_attempt && <button type="button" onClick={() => goTo(s.previous_attempt)}>Previous attempt</button>}
      </div>

      <section aria-labelledby="asg-h">
        <h3 id="asg-h">Assignment</h3>
        {assignment ? (
          <dl class="facts" data-testid="detail-assignment">
            <dt>Id</dt><dd>{assignment.id}</dd>
            <dt>Summary</dt><dd>{assignment.summary}</dd>
            <dt>Owner</dt><dd>{assignment.owner_session_id ? recordLabel(assignment.owner_session_id) : 'Owner unknown'}</dd>
            <dt>Progress</dt><dd>{PROGRESS_LABELS[assignment.progress] || assignment.progress}
              {assignment.blocked_reason && <> — {assignment.blocked_reason}</>}</dd>
          </dl>
        ) : <p>Assignment unknown.</p>}
      </section>

      <section aria-labelledby="run-h">
        <h3 id="run-h">Related run</h3>
        {runs.length ? (
          <ul data-testid="detail-runs">
            {runs.map((r) => <li key={r.id}><code>{r.id}</code>: <span data-testid="run-outcome">{runText(s, r)}</span> — {r.summary}</li>)}
          </ul>
        ) : <p class="muted">No associated run recorded.</p>}
      </section>

      <section aria-labelledby="rel-h">
        <h3 id="rel-h">Typed relationships</h3>
        {relations.length ? (
          <ul data-testid="detail-relationships">
            {relations.map((r) => (
              <li key={r.id} data-relationship-type={r.type}>
                <strong>{r.type}</strong>: {recordLabel(r.from)} {RELATION_LABELS[r.type]} {recordLabel(r.to)}
              </li>
            ))}
          </ul>
        ) : <p class="muted">No typed relationships beyond ancestry.</p>}
      </section>

      <section aria-labelledby="cost-h">
        <h3 id="cost-h">Cost and budget</h3>
        <dl class="facts">
          <dt>Own cost</dt><dd data-testid="own-cost">{formatCost(s.cost)}</dd>
          {(childMap.get(s.id) || []).length > 0 && <><dt>Branch (own costs summed)</dt><dd>{branchCost(s, childMap)}</dd></>}
          <dt>Elapsed</dt><dd>{formatElapsed(s.elapsed_s)}</dd>
          <dt>Budget</dt><dd>{s.budget ? `$${s.budget.limit_usd} (${s.budget.basis}, not enforced by this view)` : 'No budget recorded'}</dd>
        </dl>
      </section>

      <section aria-labelledby="ev-h">
        <h3 id="ev-h">Evidence</h3>
        {!detail ? <p class="muted">Loading…</p> : detail.evidence.length ? (
          <ul data-testid="detail-evidence">
            {detail.evidence.map((e) => <li key={e.id}>{e.label} — source: {e.source}; owner: {recordLabel(e.owner)}</li>)}
          </ul>
        ) : <p class="muted">No evidence recorded.</p>}
      </section>

      <section aria-labelledby="tr-h">
        <h3 id="tr-h">Transcript</h3>
        <p class="muted">Transcript text is untrusted and shown as plain text.</p>
        {!detail ? <p class="muted">Loading…</p> : (
          <ol class="transcript" data-testid="transcript">
            {detail.transcript.map((t, i) => (t.kind === 'gap' ? (
              <li key={`gap-${i}`} class="gap" data-testid="transcript-gap">
                Transcript gap: entries {t.from_seq}–{t.to_seq} missing. {t.reason}
              </li>
            ) : (
              <li key={t.seq}>
                <span class="speaker">{t.speaker}</span> <time class="muted">{t.at}</time>
                <p class="transcript-text">{t.text}</p>
              </li>
            )))}
          </ol>
        )}
      </section>

      <section aria-labelledby="act-h">
        <h3 id="act-h">Actions</h3>
        <div class="actions-row">
          <button type="button" disabled aria-describedby="act-note">Send message</button>
          <button type="button" disabled aria-describedby="act-note">Stop session</button>
          <button type="button" disabled aria-describedby="act-note">Review decision</button>
        </div>
        <p id="act-note" class="muted" data-testid="actions-note">Commands are not connected in this synthetic prototype.</p>
      </section>
    </div>
  );
}
