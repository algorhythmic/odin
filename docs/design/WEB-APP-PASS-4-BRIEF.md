# Web app pass 4 brief

Status: operator direction, 2026-10-21, for the webapp workstream's pass 4
under [ODIN-ADR-037](../DECISIONS.md#odin-adr-037--web-app-as-the-primary-human-view-with-an-agent-tree).
It extends the [work plan](WEB-APP-WORKPLAN.md) packages W2a to W2c and
amends the cost rules of the [projection draft](WEB-APP-PROJECTION.md)
(section 7), which is not adopted. Pass 3 head `007aac7` is accepted. The
result stays a **synthetic prototype**: no service connection, commands or
desktop packaging in this pass.

The reference for the tree's design and behaviour is a 23-second screen
recording held by the operator outside the repository
(`/home/david/Downloads/fPXQnvz1LhjAWxd5.mp4`; light theme, then dark). It
shows a live agent tree: agents appearing, running, needing the operator,
failing, being retried and finishing.

## Must have

1. **Dark theme as the default**, whatever the system setting. A light/dark
   toggle stores the operator's choice in the existing layout preferences
   (`odin-web-prefs`). Colour tokens on `:root`, monochrome
   surfaces, colour reserved for status.
2. **Token usage instead of cost, everywhere** (cards, branch totals, header,
   detail panel). Odin's usage telemetry already records per-observation
   tokens as `uncached_input`, `cache_read`, `cache_write`, `output`.
   - Card footer: total tokens in compact form (`48.2k tok`) and elapsed
     time; the detail panel shows the four-way split.
   - Branch totals and the header total sum each session's own tokens once.
   - Unknown stays `unknown` (never `0`), with ` + unknown (n)` on sums, as
     the current cost rules do.
   - Projection draft: replace `cost {amount_usd, basis}` with
     `tokens {uncached_input, cache_read, cache_write, output, basis}`,
     `session.cost_updated` with `session.usage_updated`, and update section 7,
     the schemas, fixtures and tests. Remove dollar figures and budgets from the
     UI; a token budget may replace the dollar budget where one exists.
   - Decide and document whether cache reads count in the headline figure
     (they dominate long sessions); default proposal: headline excludes cache
     reads, the split shows them.
3. **Live behaviour.** A synthetic autoplay player (play/pause, speed) that
   applies the event fixture on a timer, plus:
   - new sessions fade/slide in and their connector draws in;
   - running sessions tick elapsed time each second; token counts animate up;
   - Running chip has a spinner; header summary
     (`N agents · N running · N needs you · N failed · total tokens`) updates live;
   - collapse/expand animates; collapsed chip reads `+N ›`.
   Respect `prefers-reduced-motion`.
4. **Tree layout like the reference.** Square-cornered connectors from a port
   dot under the parent; first level fans out horizontally, deeper levels stack
   vertically under the parent's left edge. The tree fills the page (no
   fixed-height inner box that clips rows); pan/scroll the canvas instead.
5. **Card design.** Compact, rounded, soft shadow; provider logo; role in bold
   with a friendly model name below ("Opus 5.5", not `claude-opus-5-5`); status
   chip with icon top-right; task text wraps to two lines (no one-line
   ellipsis); tool/integration icons before the task where known; footer with
   tokens, elapsed and child-count chip.
6. **Status set.** Running (blue, spinner), Needs you (amber, clock; replaces
   "Waiting for input"), Done (green, check), Failed (red, triangle), Stopped
   (grey, square; whole card dimmed). Superseded attempts are dimmed.
7. **Header attention chips.** `1 needs you ˅` and `1 failed ˅` open a
   popover listing the session, its task and the reason. Show Retry/Dismiss
   (and similar) controls disabled with a short "commands are not connected"
   explanation (checks 5 and 6 are not in scope). A retry is drawn as a new
   sibling attempt and the old one as Stopped, which is the existing
   new-attempt semantics.

## Keep (handoff requirements the reference lacks)

Detail panel, keyboard list view, typed relationship overlays, host
offline/stale markers, planning conversation, history, deep links. Move them
into secondary panels or toggles around the full-page tree rather than the
fixed three-column layout. Make the synthetic-data banner a quiet badge in
the header instead of a full-width yellow bar.

## Evidence

Playwright coverage for the dark default and toggle, token rendering and
unknown handling, autoplay updates preserving selection and scroll, collapse,
the status set and the attention popover; screenshots in both themes; the
check 9 timings re-run with animations on. Retain review outputs as files
(pass 3 kept none).

## Working rules for this pass (from the pass 1–3 time review)

Passes 1–3 spent about a third of their working time on repeated
verification: 12 full `make check` runs (about 3.4 min each) and 10
`--repeat-each=10` Playwright runs, for passes that barely touched Python.

1. **While iterating**, run only what the change touches: `npm run
   test:unit`, the affected Playwright specs, the schema test when schemas or
   fixtures change, and `scripts/validate_docs.py` when docs change. Do not
   create receipts for intermediate heads.
2. **`make check` once per pass**, at the final head, as a receipt. If a
   review fix lands after it, rerun `make check` only when the fix touches
   `python/`, `schemas/`, `go/`, `scripts/` or the docs it validates;
   otherwise rerun the web checks and state why `make check` was not
   repeated.
3. **The 10× Playwright repeat once per pass**, at the final head, as a
   receipt. Use single runs while iterating.
4. **Subagents are Haiku only** (ODIN-ADR-036). Pass 1 used an Opus subagent
   to build the prototype; do not repeat that. Opus work stays in the
   workstream session itself.
