# Odin web app — synthetic prototype

This directory holds the first vertical slice of Odin's web app: an
overview, a project workspace with an interactive agent tree, a detail
panel, a keyboard-navigable list view and a per-project history. **It
runs on synthetic data only.** It is not connected to Odin's service, has no authentication,
and sends no commands. Every view carries a "SYNTHETIC DATA" banner.

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
`#/projects/<project>/sessions/<session>`.

Data sets: the default loads the shared fixtures in `fixtures/`. Add
`?dataset=large` before the hash (for example
`http://127.0.0.1:5317/?dataset=large#/projects/proj-large-synthetic`)
for the seeded 2,000-session tree, generated in the browser from
`src/fixtures/large.js`; `npm run describe:large` checks it from Node.

The bar under the header is a synthetic update driver: "Apply next
synthetic update" applies the next event from
`fixtures/default-events.json` to the loaded snapshot and reports
whether it was applied, a duplicate, a revision gap or rejected
(unknown session or event type; nothing changes). Reloading the
page starts from the snapshot again.

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
EVIDENCE_DIR=/private/path npm run test:perf   # writes large-timings.json
```

It records first render, expand and select times on the seeded dataset
and compares them with the proposed targets (first render under 1 s,
expand or select under 150 ms). The values are written first; a missed
target then fails the run, so a red timing run still leaves its
numbers. The values are synthetic prototype timings on one machine,
not service or desktop measurements.

## Layout

| Path | Purpose |
|---|---|
| `fixtures/*.json` | Shared synthetic projection fixtures: snapshot, session details, update events ([draft shape](../docs/design/WEB-APP-PROJECTION.md)) |
| `src/fixtures/synthetic.js`, `src/fixtures/large.js` | Fixture loading and paged detail requests; seeded large-dataset generator |
| `src/data.js` | Versioned store over the snapshot: views, ancestry analysis (cycles, outside parents), update-event application |
| `src/driver.jsx`, `src/history.jsx` | Synthetic update driver bar; project history |
| `src/route.js`, `src/prefs.js` | Hash routes; layout preferences (`odin-web-prefs:v1` in localStorage) |
| `src/overview.jsx`, `src/workspace.jsx` | Overview and project workspace |
| `src/tree.jsx`, `src/card.jsx` | d3-hierarchy tidy-tree layout, SVG edges, session cards |
| `src/list.jsx` | ARIA treeview list alternative with roving tabindex |
| `src/detail.jsx` | Detail panel; transcripts render as plain text |
| `tests/`, `tests-perf/` | Playwright specs; the check 9 timing scenario |
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
- Cost covers a session's own turns. Unknown cost reads "cost unknown";
  estimates read "est."; branch totals sum own costs once and say
  "+ unknown" when any is missing.
- A session ending does not mark its run verified.
- The browser keeps only layout preferences (view mode, collapsed
  branches, relationship overlay). Selection lives in the URL.

## Not implemented

Service projection and update stream (updates come only from the
synthetic driver), reconnect and cursor expiry, authentication and
authorization, any command (messages, stop, approvals), virtualised
rendering for large expanded trees, and the Omarchy Chromium app
launcher. Check 10 and any
desktop behavior need manual evidence on Omarchy.
