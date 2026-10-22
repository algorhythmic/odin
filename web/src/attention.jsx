// Header attention chips (pass 4 item 7): "N needs you ˅" and
// "N failed ˅", live from the snapshot. Each opens a popover listing the
// session, its task and the reason. The command controls are disabled —
// this prototype sends no commands.
import { useEffect, useRef, useState } from 'preact/hooks';
import { failedRunFor, failedSessions, getAssignment, needsYouSessions, projectSummary } from './data.js';
import { sessionHref } from './route.js';

const GROUPS = {
  needs: {
    label: 'needs you',
    list: needsYouSessions,
    reason: (s) => (s.lifecycle === 'waiting_for_input' ? 'Waiting for operator input' : 'Flagged as needing operator input'),
    actions: ['Send input', 'Dismiss'],
  },
  failed: {
    label: 'failed',
    list: failedSessions,
    reason: (s) => {
      const run = failedRunFor(s);
      return run ? `Run recorded failed — ${run.summary}` : 'Run recorded failed';
    },
    actions: ['Retry', 'Dismiss'],
  },
};

export function AttentionChips({ pid }) {
  const counts = projectSummary(pid);
  const [open, setOpen] = useState(null); // 'needs' | 'failed' | null
  const chipsRef = useRef({ needs: null, failed: null });
  const popRef = useRef(null);

  const close = () => {
    const which = open;
    setOpen(null);
    if (which) chipsRef.current[which]?.focus();
  };

  useEffect(() => {
    if (!open) return undefined;
    popRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
    const onDown = (e) => {
      if (!popRef.current?.contains(e.target)
        && e.target !== chipsRef.current.needs
        && e.target !== chipsRef.current.failed) close();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
    };
  }, [open]);

  const anchor = open && chipsRef.current[open]?.getBoundingClientRect();
  const popupStyle = anchor ? {
    top: anchor.bottom + 6,
    left: Math.max(8, Math.min(anchor.left, innerWidth - Math.min(380, innerWidth * 0.8) - 8)),
  } : undefined;

  return (
    <span class="attention-chips" data-testid="attention-chips">
      {Object.entries(GROUPS).map(([kind, g]) => {
        const count = kind === 'needs' ? counts.needsYou : counts.failed;
        const sessions = g.list(pid);
        return (
          <span class="attention-wrap" key={kind}>
            <button type="button" class={`attention-chip attention-${kind}`} data-testid={`chip-${kind}`}
              ref={(el) => { chipsRef.current[kind] = el; }}
              aria-haspopup="dialog" aria-expanded={open === kind} disabled={!count}
              onClick={() => setOpen(open === kind ? null : kind)}>
              {count} {g.label} ˅
            </button>
            {open === kind && (
              <div class="attention-pop" role="dialog" aria-label={`Sessions that ${g.label}`}
                style={popupStyle} tabIndex={-1} ref={popRef} data-testid="attention-popover" data-kind={kind}>
                <ul class="attention-items">
                  {sessions.map((s) => (
                    <li key={s.id} data-testid="attention-pop-item" data-session-id={s.id}>
                      <a href={sessionHref(pid, s.id)}><strong>{s.role}</strong> <code>{s.id}</code></a>
                      <div class="attention-task">{getAssignment(s.assignment_id)?.summary || 'Assignment unknown'}</div>
                      <div class="muted attention-reason">{g.reason(s)}</div>
                      <div class="actions-row">
                        {g.actions.map((a) => (
                          <button key={a} type="button" disabled aria-describedby="attention-note">{a}</button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
                <p id="attention-note" class="muted" data-testid="attention-note">
                  Commands are not connected in this prototype.
                </p>
              </div>
            )}
          </span>
        );
      })}
    </span>
  );
}
