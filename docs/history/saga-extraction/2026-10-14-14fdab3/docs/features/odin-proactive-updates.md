# Feature: Proactive Odin → Telegram updates

> **Status:** Tier 1 implemented. Tiers 2-3 scoped for future phases.
> **Effort estimate:** Tier 1 ~30 min (ratatoskr event nudges). Tier 2
> ~2-3 days (custom MCP tools). Tier 3 ~1 day (scheduled digests).
> **Priority:** Tier 1 is immediate quality-of-life; discovered during
> the first real Phase 3 run (2026-04-15) when Odin completed an
> entire dvergr stream without proactively telling the operator.

## The gap

Odin is **reactive** — it responds when the operator asks "any
updates?" but doesn't push notifications on key session events. The
ratatoskr sidecar continuously updates `state.json` and writes
incoming journals from MQTT, but nobody nudges Odin to check them
and relay to Telegram. The operator has to poll manually.

This was fine during Phase 2 validation (small, supervised runs)
but becomes a real friction point with live workers where dvergar
complete, error, or get stuck asynchronously while the operator is
away from the terminal.

## Tier 1: Event-driven nudges from ratatoskr (implemented)

Ratatoskr already processes every `dvergr/+/+/status` MQTT message
and updates `state.json`. Extend it to detect milestone events and
`tmux send-keys` a notification into Odin's pane — same pattern as
the existing Mimir verdict nudge.

Events worth a nudge:

- **Dvergr completed** — status payload contains
  `"status": "complete"` or the iteration count equals
  `max_iterations`. Most important signal; Odin should relay to
  Telegram and submit the next sequential dvergr if applicable.
- **Dvergr errored** — status contains `"error"` or `"status":
  "failed"`. Odin should assess and potentially alert the operator.
- **Test regression** — `tests_passing` decreased from the previous
  status update for the same dvergr. Early warning that quality is
  degrading.
- **Convergence alert** — already wired via the
  `dvergr/+/+/converged` topic and `write_convergence_alert()`.
  Ratatoskr writes an alert file; Odin picks it up via the existing
  incoming-alerts flow. No new nudge needed for this one.

Implementation: new `check_status_milestones()` function in
ratatoskr.py called from `update_state()` after writing state.json.
Compares the new status against the previous state for the same
dvergr key and fires `_send_keys(TMUX_ODIN_TARGET, ...)` on
qualifying transitions.

## Tier 2: Custom MCP tools for Odin (Phase 4+)

Give Odin programmatic tools to query session state and generate rich
summaries, rather than relying on file reads:

- `saga:session-status` — returns a structured JSON summary of all
  active dvergar (project, instance, iteration, tests, last commit)
- `saga:project-timeline` — returns iteration-by-iteration history
  for a specific project (test trends, guidance adoption, time per
  iteration)
- `saga:progress-chart` — renders a simple ASCII or image chart of
  session progress (could use matplotlib in a sidecar, or just ASCII
  bar charts)

These would be MCP server endpoints running alongside ratatoskr
(or inside it). Odin invokes them as tool calls and composes
Telegram messages from the structured output.

**Effort:** ~2-3 days. Requires an MCP server scaffold, tool
definitions, and integration with the existing state.json / journal
data.

## Tier 3: Scheduled digest messages (Phase 4+)

Odin sends a periodic session summary to Telegram every N minutes:

> "Session digest (every 30m): 3 dvergar active, 1 completed since
> last digest, 0 stuck, 412 tests passing across all workers."

Implementation: a cron-like nudge from ratatoskr that sends-keys
a "compose and send a session digest" prompt into Odin's pane on a
timer. Or a dedicated `saga:send-digest` MCP tool Odin calls on
a self-set reminder.

**Effort:** ~1 day once Tier 2's `saga:session-status` tool exists
(the digest is just a scheduled invocation of that tool).

## Cross-references

- Ratatoskr's existing nudge patterns:
  `odin/scripts/ratatoskr.py` § `_send_keys`, `handle_mimir_*`
- Odin's alert escalation behavior:
  `odin/CLAUDE.md` § "Alert Escalation"
- Convergence alert flow (already wired):
  `odin/scripts/ratatoskr.py` § `write_convergence_alert`
- Voice integration (pairs with Tier 3 for hands-free digests):
  `docs/features/voice-telegram.md`
