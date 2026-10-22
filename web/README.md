# Odin web app — synthetic prototype

This directory holds the first vertical slice of Odin's web app: an
overview, a project workspace with an interactive agent tree, a detail
panel and a keyboard-navigable list view. **It runs on synthetic data
only.** It is not connected to Odin's service, has no authentication,
and sends no commands. Every view carries a "SYNTHETIC DATA" banner.

The handoff and decision record live in
[`docs/design/WEB-APP-HANDOFF.md`](../docs/design/WEB-APP-HANDOFF.md)
and [`docs/DECISIONS.md`](../docs/DECISIONS.md).

## Start

Requires Node.js and npm (developed with Node 26). After `npm ci` the
app and its tests work offline: no CDN, external font or network call.

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
rewrites: `#/`, `#/projects/<project>`, `#/projects/<project>/sessions/<session>`.

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
(`check01-…` for check 1, and so on). Coverage of checks 2 and 8 is
partial and synthetic.

## Layout

| Path | Purpose |
|---|---|
| `src/fixtures/synthetic.js` | Synthetic records: projects, sessions, assignments, commitments, runs, typed relationships, decisions, transcripts |
| `src/data.js` | Read-only views over the fixture; a service projection replaces it later |
| `src/route.js`, `src/prefs.js` | Hash routes; layout preferences (`odin-web-prefs:v1` in localStorage) |
| `src/overview.jsx`, `src/workspace.jsx` | Overview and project workspace |
| `src/tree.jsx`, `src/card.jsx` | d3-hierarchy tidy-tree layout, SVG edges, session cards |
| `src/list.jsx` | ARIA treeview list alternative with roving tabindex |
| `src/detail.jsx` | Detail panel; transcripts render as plain text |
| `tests/` | Playwright specs |

## Semantics kept by the prototype

- The tree edge is session ancestry only (`parent_session_id`). Review,
  delegation, run association and assignment ownership are typed
  relationships, drawn as dashed overlays and listed in details.
- An imported session with no known parent stays a root.
- A resumption keeps the same session; a new attempt is a distinct
  session linked to the previous attempt.
- Cost covers a session's own turns. Unknown cost reads "cost unknown";
  estimates read "est."; branch totals sum own costs once and say
  "+ unknown" when any is missing.
- A session ending does not mark its run verified.
- The browser keeps only layout preferences (view mode, collapsed
  branches, relationship overlay). Selection lives in the URL.

## Not implemented

Service projection and update stream, reconnect, authentication and
authorization, any command (messages, stop, approvals), history views,
pagination beyond lazy per-session detail loading, large-tree
measurement, and the Omarchy Chromium app launcher. Check 10 and any
desktop behavior need manual evidence on Omarchy.
