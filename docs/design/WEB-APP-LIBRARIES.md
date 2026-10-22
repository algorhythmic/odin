# Web app library choice

Status: recorded 2026-10-21 for the synthetic prototype under
[ODIN-ADR-037](../DECISIONS.md#odin-adr-037--web-app-as-the-primary-human-view-with-an-agent-tree).
It is revisited when service read integration starts (see the
[work plan](WEB-APP-WORKPLAN.md), package W3) if the prototype shows a
problem. Registry facts (version, licence, unpacked size, last publish) were
read with `npm view` on 2026-10-21; they are not audits. The exact pinned
versions are in `web/package.json` and `web/package-lock.json`.

The [handoff](WEB-APP-HANDOFF.md) asks for reusable components, a
consistent style, readable automatic tree layout, keyboard use, narrow
screens and no hand-built design system or graph engine. It does not
require standards-based Custom Elements.

## Component layer

| Candidate | Licence | Styling control | Accessibility | Update performance | Maintenance and size | Fit |
|---|---|---|---|---|---|---|
| **Preact** (with native HTML elements and a small token stylesheet) | MIT | Full; plain CSS with custom properties | Native elements (`button`, `details`, landmarks) carry semantics; ARIA tree pattern written once | Virtual DOM with keyed lists; adequate for hundreds of visible nodes | Active (11.0.1 published 2026-10; the prototype pins the mature 10.29.8 line); about 10 kB runtime gzip; React-compatible API if a component set is needed later | **Chosen** |
| React + a headless set (for example Radix) | MIT | Full with headless components | Strong for dialogs, menus, tabs | Similar to Preact | Active; larger runtime (react-dom unpacked about 8 MB); more dependencies | Viable fallback; heavier than needed for v0 |
| Lit + Shoelace / Web Awesome | BSD-3-Clause / MIT | Good via CSS parts and tokens | Good built-in components | Fine-grained updates | Lit active; Shoelace 2.x last published 2025-03 while its successor changes packaging; about 8 MB unpacked | Good for widgets, but the tree and detail views are custom anyway; component set churn |
| Svelte 5 | MIT | Full, scoped CSS | Compiler warnings help; no built-in widgets | Compiled, very fast | Active; adds a compiler and its own idioms to an otherwise Python/Go repository | Viable; less reuse of the React ecosystem |

Decision: **Preact** for components, rendered with native elements and one
hand-written stylesheet of design tokens. The views need few generic
widgets (buttons, toggles, disclosure, panels), and native elements give
them accessible semantics without a component dependency. This is a small
stylesheet, not a design system. If later packages need dialogs, menus or
comboboxes, add a headless React-compatible set through `preact/compat`
rather than writing those widgets.

## Tree and graph layout

| Candidate | Licence | Layout | Size and maintenance | Fit |
|---|---|---|---|---|
| **d3-hierarchy** (tidy tree), rendered as SVG edges plus HTML cards | ISC | Reingold–Tilford tidy tree for a rooted hierarchy; a forest is laid out under a hidden virtual root | About 136 kB unpacked, no dependencies; stable API (3.1.2, last change 2022, finished rather than abandoned) | **Chosen**: session ancestry is a forest by definition, and typed relationships are drawn as overlays, not layout edges |
| ELK (elkjs) | EPL-2.0 or GPL-3.0-or-later | Layered layouts for general graphs, ports, edge routing | About 8 MB unpacked; weak copyleft; runs best in a worker | Too heavy and too general for an ancestry forest; licence adds review burden |
| dagre (@dagrejs/dagre) | MIT | Layered DAG layout | About 1.4 MB unpacked; maintained fork | Suits DAGs; would tempt drawing non-ancestry relations as layout edges, which ADR-037 forbids |
| React Flow (@xyflow/react) with dagre/ELK | MIT | Interactive canvas; layout delegated | About 1.2 MB unpacked plus React | Rich interaction, but brings React and a canvas model larger than v0 needs |

Decision: **d3-hierarchy** computes positions; Preact renders cards as
HTML (so they are focusable and readable) and edges as SVG. Fit-to-branch is
a viewport transform over the computed positions. Collapsed branches are not
laid out or rendered, which keeps large trees bounded.

## Tooling

- **Vite** with `@preact/preset-vite` for the dev server and static build
  (MIT). Dev and preview servers bind to `127.0.0.1`.
- **Playwright** (`@playwright/test`, Apache-2.0) with Chromium installed
  inside `web/.playwright-browsers` via `PLAYWRIGHT_BROWSERS_PATH`; nothing
  is installed system-wide.
- Exact versions are pinned (no ranges) and `package-lock.json` is
  committed, so `npm ci` reproduces the tree and the app runs offline after
  installation. No CDN, web font or remote asset is loaded.

## Rejected for v0

- An Electron or other native wrapper: ADR-037 uses a Chromium app window.
- A client-side router dependency: hash routes (`#/projects/<id>/sessions/<id>`)
  give deep links with any static server and no rewrite rules.
- A client-side state library: state is a projection from the service plus
  selection and layout preferences.
