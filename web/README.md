# Odin web app — synthetic prototype

This directory holds the synthetic Odin web app: a dashboard and portfolio agent tree
rooted at one executive, project grouping nodes, scoped project trees,
a detail drawer, a keyboard-navigable list and portfolio/project history.
**It runs on synthetic data only.** It is not connected to Odin's service,
has no authentication and sends no commands. Every view carries a
"Synthetic data" badge in the sidebar.

The handoff and decision record live in
[`docs/design/WEB-APP-HANDOFF.md`](../docs/design/WEB-APP-HANDOFF.md)
and [`docs/DECISIONS.md`](../docs/DECISIONS.md).

## Start

Requires Node.js and npm (developed with Node 26). Installing needs the
network once: `npm ci`, and `npm run browsers:install` for the test
browser. Once installed, the app makes no network call at runtime: no
CDN, external font or remote request.

```sh
cd web
npm ci
npm run dev          # http://127.0.0.1:5317/
```

Static build served locally:

```sh
npm run build
npm run preview      # http://127.0.0.1:5318/
```

Routes are hash based so a static build deep-links without server rewrites:

- `#/`: dashboard home; `#/agents`: portfolio tree.
- `#/sessions/<session>` selects in the full tree.
- `#/projects/<project>`: scoped project tree with a compact executive header.
- `#/projects/<project>/sessions/<session>`: scoped session selection.
- `#/history` and `#/projects/<project>/history`: portfolio and project history.
- `#/setup`, `#/setup/<step>` and `#/settings/<section>`: synthetic setup and settings.

The sidebar connects projects beneath the executive. Hover or keyboard
focus highlights a project's branch on portfolio routes; clicking scopes
the tree. The Dashboard entry shows the number of open priority items.
Portfolio attention and activity live on the dashboard; the sidebar keeps
usage for connected sign-ins. Usage stays pinned above setup and settings,
with one compact row per sign-in. Each row shows its most constrained available
window; its disclosure unfolds per-window details in a bounded scrolling list.
Disclosure state lasts only in memory, including through sidebar collapse. It resizes from 220 to 440 px by dragging
its right edge or using the separator's arrow keys (16 px), Home and End.
A button collapses it to a 56 px rail; width and collapse are validated
layout preferences. Container queries reveal more detail from 300 px.
Below 900 px the sidebar is always an expanded modal drawer. Below 760 px the
list replaces the canvas. Tree/List is a layout preference; selection
stays in the URL. Deferred Queue, Lanes, Graph, Decisions and Board routes
render not found. Setup and settings share working synthetic panels.

The canvas fits its available width on load, resize, sidebar changes,
drawer changes and branch expansion. It tries a full horizontal tree,
then stacks progressively shallower levels into indented columns, then
wraps project columns into rows. It keeps a scale of at least 0.85 whenever
an arrangement permits, and never scales below 0.5; tall arrangements scroll
inside the canvas. The relationship key has a reserved band above the tree.

Ctrl/Meta + wheel (including trackpad pinch) zooms about the pointer;
plain wheel scrolls. Drag empty canvas to pan; one-finger drag and two-finger
pinch are supported through pointer events. Focus **Agent tree canvas** and
use `+` / `-` to zoom about its centre, arrow keys to pan and `0` to reset.
Compact Zoom out / Zoom in buttons offer the same control. A manual move
pauses automatic fitting and reveals **Reset view**. New selections are
brought into view at the current manual zoom. Tree/List stays the full
keyboard alternative; selection and layout preferences retain their existing
storage rules. Arrangement changes take 420 ms on the shared motion curve,
and are instant under reduced motion.

Ancestry uses solid neutral lines and port dots; grouping uses lighter
long dashes without dots. Typed overlays are above cards, with arrowheads
and distinct review, delegation and assignment ownership patterns. An
assignment record is anchored to its recorded owner card; it does not
become a node. Run associations are card badges. Relationship pills search
for space clear of every card, with a clear arrowhead-side fallback. Their
screen font size stays within 0.85–1.25 of the base size across zoom levels.
The vertical key lists only the line styles in the current view.

Data sets: the default loads the shared fixtures in `fixtures/`. Add
`?dataset=large` before the hash (for example
`http://127.0.0.1:5317/?dataset=large#/projects/proj-large-synthetic`)
for 2,000 seeded project sessions plus one executive, generated in the browser from
`src/fixtures/large.js`; `npm run describe:large` checks it from Node.

Setup uses its own `fixtures/setup.json`, separate from the projection
fixtures. The default draft has three of four steps done and opens Roles.
Add `?setup=fresh` before the hash to start with no connected sign-ins,
enabled harnesses or completed steps and an empty portfolio from
`fixtures/empty-snapshot.json`. Fresh setup takes precedence over `dataset=large`.
Home shows a welcome checklist until a sign-in connects; partial setup leads the
priority queue. Apply removes that item and shows a five-second confirmation,
without opening a modal. Sign-in completion is an explicitly labelled
simulation. No field accepts a credential, and no sign-in request leaves
the browser. Disconnect removes a sign-in from the draft; Discard restores
the applied snapshot. The model speed/depth bars are synthetic descriptors.

Usage meters follow the connected sign-ins in that draft. Their synthetic
limit samples mirror W3a labels and admission thresholds; unlisted labels
have no band. Probe-unavailable windows show a reason without a bar.
Tokens are separate from probes and unknown usage stays explicit. Friendly
window names retain their raw labels in tooltips and meter descriptions. Reset
intervals use the sample's observation time so the fixture stays repeatable;
durations of a day or more use days and hours.
Admission text uses warning and failed status colours; meter fills stay
monochrome. These are descriptions of Odin admission, not provider-enforced
limits, and no live probe runs in the browser.

Providers, harnesses, default models and role routing share one in-memory
draft across the wizard and settings. Apply records an in-memory snapshot;
Discard restores that snapshot. Nothing is saved across reload, and this
applies no configuration to the service. The executive must use Claude Code;
roles need enabled harnesses and connected sign-ins. Same-family independent
review is allowed with a warning; shared-lineage capacity is informational.

The dashboard has a small Synthetic data · Play/Pause control. It shares playback
with the tree; navigating between them preserves the current projection.
On tree pages the compact synthetic update driver includes "Apply next
synthetic update", which applies the next event from
`fixtures/default-events.json` to the loaded snapshot and reports
whether it was applied, a duplicate, a revision gap or rejected. Play
and a speed selector (0.5×/1×/2×/4×) apply the same queue on a timer so
the tree runs live: sessions appear with a drawn-in connector, running
elapsed ticks each second and token figures count up. Pausing freezes
both. When the default fixture queue drains, a seeded continuous generator
keeps delivering the same four event types through the unchanged reducer.
`?seed=your-seed` before the hash overrides the default seed `20261022`.
It spreads work over the non-malformed projects, starts workers, subagents
and reviewers under recorded running parents, measures growing token usage,
waits for synthetic input, finishes with recorded run outcomes and sometimes
retries failed work as a distinct session in the same place. Ended sessions
linger for about six seconds at 1×, then retire. The fixed fixture briefly
leaves 20 live sessions; the generator drains old ended records and keeps
8–18 live sessions thereafter. The malformed project's records stay untouched.
The large dataset remains a fixed performance fixture with no autoplay.

Retired sessions, including those in the initial snapshot, leave both live
layouts and stay in project and portfolio History. A retired deep link opens
its original detail record with “Retired · see History”; ancestry, evidence,
unknown usage and run outcomes remain inspectable there. A live descendant
of a retired parent becomes a labelled root without acquiring a new parent.
Live counts exclude retired sessions. Portfolio and project token totals
keep their cumulative record scope; visible branch totals follow the live
branch (the executive total still follows all recorded ancestry).

Presence tracking holds leaving cards and their connectors for 280 ms.
New cards rise 6 px and scale from 0.98 over 360 ms, connectors draw over
420 ms, and the existing position transitions move siblings. These all use
`cubic-bezier(0.32, 0.72, 0.24, 1)` and become instant under reduced motion.
Pause freezes simulation events, retirement scheduling and elapsed ticks;
already-started presentation animations finish. Speeds scale event cadence,
including the linger. Nothing changes for a rejected event, and its id is not
remembered, so a corrected re-delivery can apply. Rejected: a
non-integer revision; an unknown event type; a missing or unknown
`session_id`; a `session.started` without a record, with a non-string
`id` or `project_id`, for an unknown project, with an unknown lifecycle
or for an existing id; a `session.lifecycle_changed` with a lifecycle
outside the documented set or a malformed `run` record; a
`session.usage_updated` whose `tokens` record is missing, half-null,
non-integer or negative, or has a `basis` that disagrees with the
counters. Reloading the page starts from the snapshot again.

The event rules live in `src/events.js`, without browser or fixture
imports, and have Node unit tests (built-in runner, no extra
dependency):

```sh
npm run test:unit
```

## Tests

Playwright drives headless Chromium installed inside this directory
(`web/.playwright-browsers`, git-ignored); nothing is installed
system-wide.

```sh
npm run browsers:install   # once, downloads Chromium into ./.playwright-browsers
npm test                   # builds, serves on 127.0.0.1:5318, runs tests/
EVIDENCE_DIR=/private/path npm test   # screenshots elsewhere
```

Screenshots go to `test-results/screenshots/` unless `EVIDENCE_DIR`
is set. Specs are named after the handoff acceptance checks they cover
(`check01-…` for check 1, and so on). `check22-simulation.spec.js` covers
continuous playback, lifecycle removal/history, presence motion, pause/speed,
seed replay and reduced motion. `tests-unit/simulation.test.js` validates
2,000 generated steps, identity, running parents, outcomes, usage and bounds.
`check23-dashboard.spec.js` covers dashboard routes, priorities, filters, KPI
totals, projects, running sessions, live activity, container layouts, first use,
confirmation and reduced motion. `tests-unit/dashboard.test.js` checks the pure
queue and summary rules. The draft projection currently carries no harness field;
the running table explicitly shows "Harness unknown" for these records.
All coverage is synthetic; checks
2, 3 and 8 are partial.

The large-tree timing scenario (check 9) runs separately so it does not
skew the functional suite:

```sh
EVIDENCE_DIR=/private/path npm run test:perf   # writes large-timings.json and large-deep-timings.json
```

It records first fitted render, reset-to-fit, expand and select times on the seeded dataset,
and the time to expand three depth-8 paths step by step in the tree and
in the list, and compares them with the proposed targets (first render under 1 s,
expand or select under 150 ms). Large trees open collapsed to their project nodes. The values are written first; a missed
target then fails the run, so a red timing run still leaves its
numbers. The values are synthetic prototype timings on one machine,
not service or desktop measurements.

## Layout

| Path | Purpose |
|---|---|
| `fixtures/empty-snapshot.json` | Empty draft projection for fresh setup |
| `fixtures/default-*.json` | Shared synthetic projection fixtures: snapshot, session details, update events ([draft shape](../docs/design/WEB-APP-PROJECTION.md)) |
| `src/fixtures/synthetic.js`, `src/fixtures/large.js` | Fixture loading and paged detail requests; seeded large-dataset generator |
| `src/data.js`, `src/ancestry.js` | Versioned store over the snapshot: views, ancestry analysis (cycles, outside parents), indexes by session and assignment; the autoplay timers |
| `fixtures/setup.json` | Separate synthetic setup catalogue, presets and initial draft |
| `src/setup.js` | Browser-independent setup store, validation, apply and discard |
| `src/setup-state.jsx`, `src/setup-page.jsx`, `src/setup-panels.jsx` | Setup subscription, wizard, shared settings panels and progress cards |
| `src/dashboard.jsx`, `src/dashboard.js` | Dashboard and welcome; pure priority, KPI, project and activity projections |
| `src/tokens.js` | Shared pure token rules, re-exported by the data store |
| `src/events.js` | Update-event rules (pure; unit-tested in `tests-unit/`) |
| `src/live.js` | Autoplay scheduling, driver availability/population and header counts (pure; unit-tested) |
| `src/simulation.js` | Seeded continuous synthetic events; bounded live population and step-based retirement |
| `src/presence.js` | Enter/present/leave tracking shared by the canvas and list |
| `src/driver.jsx`, `src/history.jsx` | Synthetic update driver bar; project history |
| `src/route.js`, `src/prefs.js` | Hash routes; layout preferences (`odin-web-prefs:v1` in localStorage): view mode, collapsed branches, relationship overlay, colour theme, sidebar width/collapse |
| `src/models.js`, `src/status.jsx` | Friendly model names and providers; the status chip, provider monogram and tool icons |
| `src/shell.jsx`, `src/usage.jsx`, `src/usage.js` | Sidebar branch, rail, resize controls and pure admission-band helpers |
| `src/workspace.jsx` | Portfolio and scoped project workspace |
| `src/tree-layout.js` | Pure adaptive layout, recorded-edge geometry and clear relationship label routing |
| `src/tree.jsx`, `src/card.jsx`, `src/project-node.jsx` | Canvas fit, pointer/keyboard gestures, SVG layers, session cards and project groupings |
| `src/tokencount.jsx`, `src/attention.jsx` | Animated token figures; the header attention chips and popovers |
| `src/list.jsx` | ARIA treeview list alternative with roving tabindex |
| `src/detail.jsx` | Detail panel; transcripts render as plain text |
| `tests/`, `tests-perf/`, `tests-unit/` | Playwright specs; the check 9 timing scenarios; Node unit tests |
| `scripts/describe-large.mjs` | Determinism and shape check for the large dataset |

## Semantics kept by the prototype

- Solid tree edges are session ancestry only (`parent_session_id`). Review,
  delegation, run association and assignment ownership are typed
  relationships, drawn as patterned overlays or run badges and listed in details.
- An imported session with no known parent stays a root.
- The draft snapshot requires `executive_session_id` (string or null).
  Only that executive has `project_id: null`. Cross-project ancestry is
  admitted only from the executive; other cross-project parents yield
  "Parent in another project". Unavailable parents stay labelled roots.
- Project nodes are grouping rows, never sessions. Lighter long-dashed connectors
  distinguish project membership from recorded starts. An executive's
  recorded starts route through their project node. Labelled roots hang
  from their group without acquiring an ancestry parent.
- Sessions whose parent chain loops (including a self-parent) are shown
  as roots labelled "Parent cycle in records": never dropped, never given
  a guessed edge.
- A resumption keeps the same session; a new attempt is a distinct
  session linked to the previous attempt.
- Token usage covers a session's own turns. The headline figure
  (uncached input + cache write + output) excludes cache reads; the
  detail panel shows the four-way split. Unknown reads "unknown";
  estimates read "est."; branch totals and the project header total sum
  own tokens once and say "+ unknown" when any is missing. Group rows add no usage;
  the executive branch totals only its admitted recorded descendants. Token budgets
  are arbitrary synthetic values, not real limits.
- A session ending does not mark its run verified.
- The setup draft and applied configuration are synthetic in-memory values
  that reset on reload. The browser persists only layout preferences (view
  mode, collapsed branches, relationship overlay, colour theme, sidebar width
  and collapse). Selection lives in the
  URL.

## Presentation

- Dark theme is the default whatever the system setting. The header
  toggle stores the choice in `odin-web-prefs`; it is validated on load
  like the other preferences. Colour tokens live on `:root` (dark) with
  a `:root[data-theme="light"]` override. Surfaces, text, chrome,
  ancestry connectors and selection are monochrome. Colour is reserved
  for the status set, the quiet `--warn` synthetic-data badge (a muted
  amber, calmer than `--status-needs`) and `--accent`, a calm blue used
  only on links, buttons, focus rings, active resize feedback and the
  typed-relationship overlay. Usage admission text uses `--warn` from wind down and
  `--status-failed` at handoff only; fills and threshold ticks are monochrome.
- The status set is Running (blue, spinner), Needs you (amber, clock),
  Done (green, check), Failed (red, triangle) and Stopped (grey,
  square). "Needs you" replaces the old "Waiting for input" label
  everywhere; a failed run on an ended session reads "Failed". `idle`
  and `host_offline` are recorded lifecycles the set does not cover and
  keep their precise labels. A stopped session or an attempt a later
  attempt replaced is dimmed. The spinner does not animate under
  `prefers-reduced-motion`.
- Cards show a provider monogram, the role, a friendly model name
  (`claude-opus-5-5` reads "Opus 5.5"; unmapped ids show as-is), the
  status chip, the task clamped to two lines, tool/integration icons
  when the record carries `tools` or `integrations`, and a footer with
  own tokens, elapsed time, budget, a child-count chip and the branch
  token total.
- While the player runs, applied updates animate: new sessions
  fade/slide in and their connector draws itself, running sessions tick
  elapsed each second and token figures count up to the new value (an
  unknown is shown immediately, never through an intermediate number).
  The one-line workspace header carries `N agents · N running`, a token
  total and inline attention chips whose popovers
  list each session needing you or failed, its task and the reason;
  their command controls are disabled because commands are not
  connected. A collapsed branch chip reads `+N ›` for the hidden
  descendants. All of it is instant under `prefers-reduced-motion`. Setup
  panels use a blur-crossfade and slide (360 ms entrance, 240 ms exit); selected model
  effort controls unfold over 420 ms. Setup motion uses
  `cubic-bezier(0.32, 0.72, 0.24, 1)` and is also instant under reduced motion.

## Not implemented

Service projection and update stream (updates come only from the
synthetic driver), reconnect and cursor expiry, authentication and
authorization, any command (messages, stop, approvals), virtualised
rendering for large expanded trees, and the Omarchy Chromium app
launcher. Check 10 and any
desktop behavior need manual evidence on Omarchy.
