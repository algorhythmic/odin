# Odin web app — synthetic prototype

This directory holds the first vertical slice of Odin's web app: an
overview, a project workspace with an interactive agent tree, a detail
panel, a keyboard-navigable list view and a per-project history. **It
runs on synthetic data only.** It is not connected to Odin's service, has no authentication,
and sends no commands. Every view carries a "Synthetic data" badge in the header.

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

Routes are hash based so a static build deep-links without server
rewrites: `#/`, `#/projects/<project>`, `#/projects/<project>/history`,
`#/projects/<project>/sessions/<session>`, and from the redesign
([WEB-APP-REDESIGN.md](../docs/design/WEB-APP-REDESIGN.md)) the project
views `#/projects/<project>/<view>` and
`#/projects/<project>/<view>/sessions/<session>` (`queue`, `lanes`,
`graph`, `decisions`, `board`; the tree is the default), `#/setup`,
`#/setup/<step>` and `#/settings/<section>`. A sidebar carries the
overview, the projects with their views, setup, the theme toggle and the
synthetic-data badge; below 900 px it is a modal drawer. The five
non-tree views are placeholders until slices R4–R7. Setup and settings
share working synthetic configuration panels (R2).

Data sets: the default loads the shared fixtures in `fixtures/`. Add
`?dataset=large` before the hash (for example
`http://127.0.0.1:5317/?dataset=large#/projects/proj-large-synthetic`)
for the seeded 2,000-session tree, generated in the browser from
`src/fixtures/large.js`; `npm run describe:large` checks it from Node.

Setup uses its own `fixtures/setup.json`, separate from the projection
fixtures. The default draft has three of four steps done and opens Roles.
Add `?setup=fresh` before the hash to start with no connected sign-ins,
enabled harnesses or completed steps; it can be combined with
`?dataset=large&setup=fresh`. Sign-in completion is an explicitly labelled
simulation. No field accepts a credential, and no sign-in request leaves
the browser. The model speed/depth bars are synthetic descriptors.

Providers, harnesses, default models and role routing share one in-memory
draft across the wizard and settings. Apply records an in-memory snapshot;
Discard restores that snapshot. Nothing is saved across reload, and this
applies no configuration to the service. The executive must use Claude Code;
roles need enabled harnesses and connected sign-ins. Same-family independent
review is allowed with a warning; shared-lineage capacity is informational.

The bar under the header is a synthetic update driver: "Apply next
synthetic update" applies the next event from
`fixtures/default-events.json` to the loaded snapshot and reports
whether it was applied, a duplicate, a revision gap or rejected. Play
and a speed selector (0.5×/1×/2×/4×) apply the same queue on a timer so
the tree runs live: sessions appear with a drawn-in connector, running
elapsed ticks each second and token figures count up. Pausing freezes
both. Nothing changes for a rejected event, and its id is not
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
(`check01-…` for check 1, and so on). All coverage is synthetic; checks
2, 3 and 8 are partial.

The large-tree timing scenario (check 9) runs separately so it does not
skew the functional suite:

```sh
EVIDENCE_DIR=/private/path npm run test:perf   # writes large-timings.json and large-deep-timings.json
```

It records first render, expand and select times on the seeded dataset,
and the time to expand three depth-8 paths step by step in the tree and
in the list, and compares them with the proposed targets (first render under 1 s,
expand or select under 150 ms). The values are written first; a missed
target then fails the run, so a red timing run still leaves its
numbers. The values are synthetic prototype timings on one machine,
not service or desktop measurements.

## Layout

| Path | Purpose |
|---|---|
| `fixtures/default-*.json` | Shared synthetic projection fixtures: snapshot, session details, update events ([draft shape](../docs/design/WEB-APP-PROJECTION.md)) |
| `src/fixtures/synthetic.js`, `src/fixtures/large.js` | Fixture loading and paged detail requests; seeded large-dataset generator |
| `src/data.js` | Versioned store over the snapshot: views, ancestry analysis (cycles, outside parents), indexes by session and assignment; the autoplay timers |
| `fixtures/setup.json` | Separate synthetic setup catalogue, presets and initial draft |
| `src/setup.js` | Browser-independent setup store, validation, apply and discard |
| `src/setup-state.jsx`, `src/setup-page.jsx`, `src/setup-panels.jsx` | Setup subscription, wizard, shared settings panels and progress cards |
| `src/events.js` | Update-event rules (pure; unit-tested in `tests-unit/`) |
| `src/live.js` | Autoplay scheduling and header summary counts (pure; unit-tested) |
| `src/driver.jsx`, `src/history.jsx` | Synthetic update driver bar; project history |
| `src/route.js`, `src/prefs.js` | Hash routes; layout preferences (`odin-web-prefs:v1` in localStorage): view mode, collapsed branches, relationship overlay, colour theme |
| `src/models.js`, `src/status.jsx` | Friendly model names and providers; the status chip, provider monogram and tool icons |
| `src/overview.jsx`, `src/workspace.jsx` | Overview and project workspace |
| `src/tree.jsx`, `src/card.jsx` | d3-hierarchy tidy-tree layout, SVG edges, session cards |
| `src/tokencount.jsx`, `src/attention.jsx` | Animated token figures; the header attention chips and popovers |
| `src/list.jsx` | ARIA treeview list alternative with roving tabindex |
| `src/detail.jsx` | Detail panel; transcripts render as plain text |
| `tests/`, `tests-perf/`, `tests-unit/` | Playwright specs; the check 9 timing scenarios; Node unit tests |
| `scripts/describe-large.mjs` | Determinism and shape check for the large dataset |

## Semantics kept by the prototype

- The tree edge is session ancestry only (`parent_session_id`). Review,
  delegation, run association and assignment ownership are typed
  relationships, drawn as dashed overlays and listed in details.
- An imported session with no known parent stays a root.
- A session whose recorded parent is outside the project view is shown as
  a labelled root; no parent is guessed.
- Sessions whose parent chain loops (including a self-parent) are shown
  as roots labelled "Parent cycle in records": never dropped, never given
  a guessed edge.
- A resumption keeps the same session; a new attempt is a distinct
  session linked to the previous attempt.
- Token usage covers a session's own turns. The headline figure
  (uncached input + cache write + output) excludes cache reads; the
  detail panel shows the four-way split. Unknown reads "unknown";
  estimates read "est."; branch totals and the project header total sum
  own tokens once and say "+ unknown" when any is missing. Token budgets
  are arbitrary synthetic values, not real limits.
- A session ending does not mark its run verified.
- The setup draft and applied configuration are synthetic in-memory values
  that reset on reload. The browser persists only layout preferences (view
  mode, collapsed branches, relationship overlay, colour theme). Selection lives in the
  URL.

## Presentation

- Dark theme is the default whatever the system setting. The header
  toggle stores the choice in `odin-web-prefs`; it is validated on load
  like the other preferences. Colour tokens live on `:root` (dark) with
  a `:root[data-theme="light"]` override. Surfaces, text, chrome,
  ancestry connectors and selection are monochrome. Colour is reserved
  for the status set, the quiet `--warn` synthetic-data badge (a muted
  amber, calmer than `--status-needs`) and `--accent`, a calm blue used
  only on links, buttons, focus rings and the typed-relationship
  overlay.
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
  The workspace header carries a live summary (`N agents · N running ·
  N needs you · N failed · total`) and attention chips whose popovers
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
