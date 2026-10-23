# Web app redesign: onboarding, role configuration and control-plane views

Status: proposal, 2026-10-22. Operator direction for the
[ODIN-ADR-037](../DECISIONS.md#odin-adr-037--web-app-as-the-primary-human-view-with-an-agent-tree)
web app, starting from the pass 3 prototype (`7d94b5f`). Everything below
is a **synthetic prototype** until the records and service operations it
names exist; the result labels of the [work plan](WEB-APP-WORKPLAN.md)
apply unchanged. Nothing here amends ADR-037: the browser stays a client
of the service, holds no credentials and no task store, and every control
enters the shared command path.

## Operator direction (2026-10-22)

1. **Purpose of the GUI.** Onboard a new user: connect provider
   subscriptions, choose harnesses, choose models, and configure the
   harness and model for each Odin role. After setup, the **agent tree is
   the baseline view**: at a glance, which agent is doing what, its status,
   its token usage and elapsed time, as in the reference video
   (`~/Downloads/fPXQnvz1LhjAWxd5.mp4`, kept outside Git).
2. **Visual reference.** The affectUI catalogue
   (<https://www.affectui.com/components>), chiefly Agent Tree, Agent
   Queue, Agent Lanes, Agent Graph, Decision Tree, Delegate Board, the
   Onboarding screen, Model Picker, Stepper Form, Setup Guide, App Shell
   and Segmented Control. Most of these are paid PRO components. They are a
   **visual and interaction reference only**: no affectUI source, asset or
   copied markup enters this Apache-2.0 repository. Odin re-implements the
   patterns in its own stack (Preact, d3-hierarchy, one token stylesheet;
   [library choice](WEB-APP-LIBRARIES.md)).
3. **Token usage, not cost.** The reference shows dollars; Odin shows
   tokens (ODIN-ADR-031 usage telemetry). Unknown stays "unknown", never 0.
   Dark remains the default theme.

## Revised direction after the R2 review (2026-10-22)

The operator accepted setup and settings and revised the rest. Where this
section conflicts with later sections, this section wins.

1. **One executive, one portfolio tree.** There is only ever one
   executive, and it oversees every project. The baseline view is a single
   tree rooted at the executive's session, with each project as a branch
   under it and the project's sessions under that. `#/` opens this tree.
   The separate overview page is dropped: attention is carried by the
   tree header's chips, and setup progress by the sidebar card.
2. **Project nodes are grouping nodes, not sessions.** A project node is
   drawn between the executive and the project's sessions and is visually
   distinct from a session card (a compact label row with the project's
   live counts and token total). ADR-037's rules still hold: a session's
   edge comes only from its recorded `parent_session_id`. A session the
   executive started is drawn from the executive through its project's
   node; a session whose recorded parent is missing, outside the
   projection, in a cycle or itself hangs from its project node as a
   labelled root, as before. Nothing is inferred.
3. **Sidebar as a branch.** The sidebar drops the per-project view lists
   and the setup sub-links. It shows the executive at the top with the
   projects connected beneath it as a small branch (square connectors,
   status dot and counts per project), then "Setup" and "Settings" as
   single entries, the setup progress card while incomplete, the theme
   toggle and the synthetic badge. Hovering or focusing a project
   highlights its branch in the full tree; clicking it scopes the view to
   that project (`#/projects/<p>`), shown as the executive (collapsed to a
   one-line header) above the project's branch, with a way back to the
   whole portfolio.
4. **Less repeated information.** The tree header is one line:
   `N agents · N running`, the attention chips ("1 needs you", "1 failed")
   inline as the only place those counts appear, and the token total
   (`131.6k tok + 3 unknown`). The "N sessions, N roots" line, the
   Projects and Conversation toggles and the planning conversation panel
   are removed. History stays as a small link, since retired sessions now
   leave the live tree. The only view control is the Tree/List layout
   toggle.
5. **Queue, Lanes, Graph, Decisions and Board are deferred.** Their
   routes, switchers and placeholders are removed. The control-plane
   table below stays as the record of what each will show when it
   returns.
6. **Live simulation.** The synthetic driver runs as a continuous
   simulation in which agents are created, work, finish and are removed:
   new sessions rise in with their connector drawing in, ended sessions
   linger briefly and then leave the live tree with a retract-and-fade
   exit (they stay in History), and siblings glide to their new places.
   Every simulated change goes through the existing event rules
   (`src/events.js`). Motion follows the observed Agent Tree timings
   (node rise 360 ms, connector draw 420 ms, leave and retract 280 ms,
   sibling slide 420 ms, all on `cubic-bezier(0.32, 0.72, 0.24, 1)`), and
   is instant under `prefers-reduced-motion`.

7. **The overview returns as the sidebar** (operator, after R3a). The
   left panel becomes a compact, detailed dashboard that adapts to its
   width: the executive and the project branch, the attention items
   (needs you, failed) and portfolio activity, and a **usage meter per
   connected provider sign-in**. Setup and Settings move to the bottom
   beside the theme toggle. The panel can be collapsed to a narrow rail
   with a button, and resized by dragging its edge. Usage meters show the
   W3a limit-probe windows of each sign-in (for example
   `claude.five_hour`, `claude.weekly`, `codex.five_hour`) as utilization
   percentages with reset times and Odin's admission band
   ([usage and routing](../USAGE-AND-ROUTING.md)), plus token usage; an
   unavailable probe reads "unavailable", never 0, and there are no
   prices. The prototype uses synthetic samples.

8. **The canvas always fits, and the user can move it** (operator, after
   R3a). The Fit all, Actual size and Fit branch buttons and the zoom
   readout are removed. The tree is laid out and scaled to fit the
   viewport by default, and it fits narrow viewports by **re-arranging**
   rather than shrinking: deeper levels and wide sibling sets stack
   vertically (an indented column with elbow connectors, as in the
   reference video) until the tree fits at a readable scale. The user can
   zoom (wheel, pinch, keyboard) and pan (drag, keyboard) and still click
   and select cards; once they have moved the view, automatic fitting
   pauses until they reset it. The relationship key is stacked vertically
   with clearly different line styles, and typed-relationship labels are
   never hidden behind session cards.

9. **Layout that fills the viewport, and cards that size to their
   state** (operator, after R3d). The first adaptive layout produced
   either one vertical column or at most two columns; the arrangement
   must instead use the viewport's width and height, choosing per branch
   between a horizontal fan, a vertical stack and a wrapped grid. Cards
   size to their state: a running session's card is expanded; a done,
   failed or stopped session collapses to a compact one-line card (role,
   status, tokens). Expanded cards have a collapse button and compact
   ones an expand button. Any change in card size, the viewport, or the
   sidebar (including collapsing it) re-arranges the tree with the
   shared motion. The zoom icons stay for keyboard and accessibility use,
   and the project grouping line is coloured with its own token.

10. **No line over a card; a smaller header** (operator, after R3e).
    Connectors and relationship lines must not run over or be hidden
    behind cards: every line is routed through the gaps between cards.
    The tree header is cut to one compact row; the relationship key
    becomes a small collapsible element inside the canvas; the
    synthetic driver shrinks to a compact control. The scoped header
    ("All projects · Executive · Fable 5.1 · Running") is replaced by a
    breadcrumb ("Portfolio / <project>"), and the executive appears in
    the scoped canvas as a compact card above the project node, so it is
    clear who oversees the project and what it is doing.

11. **A dashboard is the home screen** (operator, after the R3b merge).
    A "Dashboard" entry sits at the top of the left panel, above the
    executive and the project branch, and `#/` opens it; the agent tree
    moves to `#/agents` (the executive's entry). The dashboard is very
    compact and dense, re-flows to the viewport, and leads with the
    operator's high-priority tasks: finishing setup, agents that failed,
    agents that need input. It is what people see on first use and on
    every later visit, so first use has a deliberate flow (below). The
    sidebar's attention and activity sections move into the dashboard so
    nothing is shown twice; the sidebar keeps the branch, usage meters,
    Setup, Settings and the theme toggle. The agent list loses its fixed
    height and flows with the page's scroll, and project nodes in the tree
    are restyled so they read as projects, not agents.

#### Dashboard: component evaluation

Every captured affectUI reference was judged for the dashboard
(visual references only, as before):

| Reference | Verdict | Use |
|---|---|---|
| Agent Inbox | **Adopt** | The priority queue: grouped rows with counts and filter tabs, a row unfolds to its last steps and actions (actions disabled until W5) |
| Setup Guide, Progress Tracker | **Adopt** | Setup as the first priority item: progress bar and the remaining steps |
| Permission Request, Approval Card | **Adapt** | Pending recorded decisions in the queue: who asks, the proposal and its digest; Approve and Deny disabled until W5 |
| Number Ticker | **Adopt** | KPI figures roll to new values |
| KPI Board, Analytics screen | **Adapt** | Density and grid: a row of small KPI tiles (running, needs you, failed, ended, tokens) and a project grid; no prices |
| Segmented Control | **Adopt** | Queue filters (All, Needs you, Failed, Setup) |
| Usage Meter | **Partial** | The sidebar keeps the meters; the dashboard lists only sign-ins at "wind down" or worse, as priority items |
| Agent Run, Evals screens | **Adapt** | Compact activity feed and dense tables for "Running now" |
| Onboarding screen, Stepper Form, Assistant Home | **Adopt** | The first-run welcome screen and its hand-off to the setup wizard |
| Agent Tree | Exclude | It is the Agents view one click away; project tiles link to it |
| Trace Waterfall | Exclude here | Per-run detail; a candidate for the session drawer later |
| Agent Lanes | Defer | A compact "last 30 minutes" strip is possible later |
| Agent Queue, Delegate Board, Agent Graph, Decision Tree | Exclude | Deferred views (item 5) |
| Model Picker | Exclude | Setup only |

#### Dashboard layout

A responsive grid (container queries on the main area; one column on a
phone, up to four on a wide screen), top to bottom:

1. **Priority queue** (Agent Inbox): one list sorted by urgency, with
   filter tabs and counts: setup incomplete, needs input, failed runs,
   pending recorded decisions, sign-ins at a limit band of wind down or
   worse, hosts offline. Each row: icon, what, where (project, role),
   how long, and an Open action that goes to the agent in the tree or to
   the setup step. When the queue is empty it says so in one line.
2. **KPI tiles**: running, needs you, failed, ended in the snapshot, and
   tokens (with "+ N unknown"), each a compact tile with a rolling number.
3. **Projects**: one dense tile per project (status bar, counts, tokens,
   last activity); clicking scopes the agent tree to it.
4. **Running now**: a dense table of running agents (role, project,
   model, harness, elapsed, tokens).
5. **Recent activity**: the latest events (started, needs input, ended,
   retired) as single lines.

#### First use and continued use

Odin's first screen depends on the setup stage, without blocking modals:

- **Fresh install** (no sign-in connected, no executive yet): `#/` shows a
  full welcome screen in the app shell instead of the dashboard: what
  Odin is in one line, the four setup steps as a checklist, and "Connect
  your first subscription", which opens the setup wizard. The sidebar
  shows the empty states. In the prototype, `?setup=fresh` also loads an
  empty portfolio to stand for a fresh install.
- **Partly set up**: the dashboard shows, with setup as the first priority
  item (Setup Guide: progress and the next step) until it is applied.
- **Set up**: the dashboard shows; the setup item is gone.
- No modal or overlay gates the app: Odin is a monitoring surface and a
  modal would hide what the operator came to check. The one transient
  element is a short confirmation after setup is applied.

ADR-037 records its layout (an overview page, a planning conversation or
activity area) as default design rather than accepted direction; this
revision replaces that layout for the prototype. Its accepted parts (the
agent tree, ancestry-only edges, the browser/service boundary, the
command path) are unchanged.

**Projection change this needs (draft only).** The draft snapshot gains a
top-level `executive_session_id`, and the executive's session carries
`project_id: null`; every other session keeps a project. Cross-project
ancestry is allowed only from the executive. The draft schema and its
Python test are updated with the fixtures; the schemas stay marked draft
and not adopted ([projection draft](WEB-APP-PROJECTION.md)).

## Control-plane views

These views expose different aspects of Odin's control plane (operator
assessment, 2026-10-22):

| View | What it reveals | Useful controls |
|---|---|---|
| Agent Tree | Actual parent/child session relationships, assignment ownership, status and accumulated token usage | Inspect a branch, open its evidence, request cancellation |
| Agent Queue | Pending assignments, admission blockers, concurrency limits and backpressure | Reprioritize work, pause scheduling, adjust authorized limits |
| Agent Lanes | Parallel activity over time: execution, review, waits, interruptions and handoffs | Select an interval, inspect a wait, steer or pause work |
| Agent Graph | Relationships among planners, workers, reviewer positions, assignments, tools and dependencies | Follow a dependency, inspect ownership, find what blocks an outcome |
| Decision Tree | Recorded alternatives, their consequences, selected paths and unresolved operator choices | Choose an option, request clarification, approve a specific proposal |
| Delegate Board | Assignment distribution, available capacity and capability fit | Assign or propose reassignment, change priority, inspect routing choices |

**Unit of attention.** A terminal workspace such as Herdr centres on
sessions and workspaces. Odin's control plane centres on commitments,
assignments, coordination, authority and outcomes. An agent can appear in
both because the views answer different questions. Herdr might show three
sessions running; Odin's lanes can show that one worker is executing,
another is blocked on its output, and two reviewer positions
(ODIN-ADR-013) are independently evaluating the same evidence pack. The
graph explains those dependencies; the queue shows what becomes eligible
next.

**Rules for every view.**

- Each view is a **projection of the same recorded state** (the browser
  projection snapshot and update stream, [draft](WEB-APP-PROJECTION.md)).
  No view keeps its own model of the work, and a selection made in one
  view is the same selection in the others (selection lives in the URL).
- Controls enter **Odin's shared command path**. Dragging a card on the
  board, editing a branch in the tree or picking a node in the graph has
  an explicit operational meaning (a named command with its record), never
  a visual move alone. Until package W5 (and W5a's security definition)
  exists, every control renders disabled with the reason "Commands are not
  connected", as pass 3 already does.
- The decision tree shows **recorded** options and decisions, including
  rejected alternatives. It never shows inferred model reasoning.
- ADR-037's tree rules hold everywhere: the tree edge is session ancestry
  only; review, delegation, run association and assignment ownership are
  typed relationships; nothing is inferred from timing, layout or wording.

## Information architecture

An **app shell** after affectUI's App Shell: a collapsible left sidebar
and an edge-to-edge page.

- **Sidebar:** Odin mark; Overview; the project list (each project expands
  to its views); Setup (Providers, Harnesses, Models, Roles); a footer card
  with setup progress ("Setup 3 of 4") while setup is incomplete; the theme
  toggle and the synthetic-data badge. At narrow widths the sidebar
  becomes a drawer.
- **Project workspace:** a header with the live summary
  (`N agents · N running · N need you · total tokens`) and attention chips,
  then a **segmented control** to switch views: Tree (default), Queue,
  Lanes, Graph, Decisions, Board. The detail drawer is shared by all views.
- **Routes** (hash based, as now):

| Route | Shows |
|---|---|
| `#/` | Overview; a setup guide card while setup is incomplete |
| `#/setup` and `#/setup/<step>` | Onboarding wizard; steps `providers`, `harnesses`, `models`, `roles`, `review` |
| `#/settings/<section>` | The same panels outside the wizard: `providers`, `harnesses`, `models`, `roles` |
| `#/projects/<p>` | Project workspace, Tree view |
| `#/projects/<p>/<view>` | `queue`, `lanes`, `graph`, `decisions` or `board` |
| `#/projects/<p>/sessions/<s>` | Tree view with that session selected (existing deep links keep working) |
| `#/projects/<p>/<view>/sessions/<s>` | Another view with that session selected |
| `#/projects/<p>/history` | History (existing) |

## Onboarding and role configuration

A four-step wizard after affectUI's Onboarding screen and Stepper Form: a
step header (`Step 2 of 4`, numbered steps that check off), one card per
step with Back and Continue, "Skip for now" where a step is optional, and a
setup checklist beside it. Every panel is reusable on its settings page.

### Step 1: Providers (connect subscriptions)

One card per provider with a monogram, plan and status: **Not connected**,
**Waiting for sign-in**, **Connected** (account label, plan tier, the
credential lineage name), **Expired** or **Error** (reason).

- **Credentials never reach the browser** (ADR-037). "Connect" asks the
  service to run the harness's own sign-in in a dedicated credential
  directory: `claude` sign-in for an Anthropic subscription, `codex login`
  for a ChatGPT subscription. The browser only shows what the operator
  must do (open this verification URL, enter this one-time code, or finish
  in the window that opened) and polls the status. It never shows,
  accepts or stores a token or API key, and there is no paste-a-key field.
- A provider can hold more than one **credential lineage** (for example
  the executive's dedicated login and the evaluator's Codex login). Each
  is a labelled row with "Add another sign-in". The lineage is what
  ODIN-ADR-036's `max_concurrent_turns_per_lineage` and the W3a account
  limit probes key on, so the card shows the lineage's concurrency setting
  and, where a probe exists, its admission band.
- At least one connected lineage is required to continue.

### Step 2: Harnesses

Detected harness CLIs (Claude Code, Codex CLI; Pi RPC is shown as
fixture-only per ODIN-ADR-015) with version, which providers they can use,
and capabilities that matter for roles: native subagents, resume, effort
levels, native compaction, Remote Control and the Odin channel. The
operator enables harnesses and picks the default lineage for each. A
harness whose provider is not connected is shown but cannot be enabled.

### Step 3: Models

A model picker per enabled harness, after affectUI's Model Picker: one row
per model with a monogram, friendly name (`claude-opus-5-5` reads
"Opus 5.5"), a one-line purpose, and bars for relative speed and depth.
Bars are **descriptors from the setup fixture, labelled as such**, not
measurements. There is no price column. Effort levels unfold under the
selected model. The step sets each harness's default model and effort.

### Step 4: Roles

A matrix, one row per Odin role, columns **Harness · Sign-in · Model ·
Effort**, each cell a compact picker constrained by steps 1–3. Roles:
Executive, Integration owner, Workstream orchestrator, Implementer,
Subagent (search, implement, review), Self-review, Independent review,
Development evaluator.

- **Presets** set the whole matrix at once: *Cross-family* (the operator's
  current plan: Opus 5.5 coordinates, Codex gpt-6.1-sol implements,
  reviews and evaluates), *Opus-led* and *Sol-heavy*. After a preset, any
  cell can be changed; the preset label then reads "Custom".
- **Constraint notes** are shown inline, never silently enforced by the
  browser: the executive needs native Claude Code (Remote Control and the
  Odin channel); an independent reviewer from the same model family as
  the author is allowed but flagged; a lineage shared by many roles shows
  its concurrency limit.

### Review and apply

A summary of every choice, then **Apply**. Applying is a configuration
command on the shared command path. In the prototype it applies to an
in-memory synthetic state, is labelled "Synthetic: not saved", and resets
on reload.

### Records this needs (not implemented)

Today these settings are CLI configuration (`delegation-configure`,
`executive-configure-model`, the `delegation_profile` of a
`development-start` request) and per-harness login directories. The web
flow needs service-side records and operations that do not exist yet:
credential lineage status (without secrets), harness detection, the
model catalogue, a role routing profile, and sign-in start/status
commands. Their schemas belong to the integration owner (W3-style work);
the prototype uses a separate synthetic `fixtures/setup.json` and does not
extend the projection schemas.

## Agent tree (baseline view)

Keep everything pass 3 built (ancestry-only edges, typed overlays,
labelled roots for cycles and outside parents, token rules, live
autoplay, attention chips, keyboard list) and bring the presentation
closer to the reference video:

- Header: `Agents · N agents · N running · N need you` and the project's
  token total; counts update live.
- Card: provider monogram tile; role as the title and the friendly model
  name under it; status pill (Running, Needs you, Done, Failed, Stopped)
  with icon and tint; tool and integration icons inline before the task;
  task clamped to two lines; footer `tokens · elapsed`, and a child-count
  chevron that folds the branch to one line. Add a small **harness tag**
  (Claude Code, Codex) because multi-harness routing is a first-class goal.
- Connectors: a node dot under the parent and elbow connectors to the
  children; a newly started child's connector draws in.
- Stopped sessions and replaced attempts are dimmed.

## Visual language

From the affectUI references, within the existing colour rules (monochrome
surfaces; colour only for the status set, `--warn` and `--accent`):

- Near-black neutral surfaces with hairline borders in dark; a light
  override as now. Cards have a 12 px radius, 1 px border and no heavy
  shadow.
- Status pills: tinted background, coloured icon and label.
- Monogram tiles (rounded square, 28–32 px) for providers and harnesses.
  No third-party logos are bundled.
- Numbers use tabular figures; token figures roll to new values (already
  in pass 3), and the motion is off under `prefers-reduced-motion`.
- System font stack; no web fonts, CDN or remote assets.

## Implementation slices

Implemented by Codex gpt-6.1-sol, one slice at a time, under the
operator's cross-family plan; reviewed and committed by the coordinating
session. Each slice keeps `npm run test:unit` and `npm test` green and adds
Playwright specs for what it adds.

| Slice | Scope | Depends on |
|---|---|---|
| R1 | App shell (sidebar, drawer on narrow screens), refreshed tokens, project view switcher and routes for all six views; Queue, Lanes, Graph, Decisions and Board render a placeholder stating what they will show and which records they need | — |
| R2 | `fixtures/setup.json`, the onboarding wizard (`#/setup`), settings pages and synthetic in-memory apply; the overview's setup guide card | R1 |
| R3a | Portfolio tree (revised direction 1–5): single executive root, project grouping nodes, sidebar branch with highlight and scope, one-line header, removal of the overview page, conversation panel, Projects toggle and deferred views; fixtures, draft schema and Python test for `executive_session_id` | R2 |
| R3c | Sidebar dashboard (revised direction 7): overview content, provider usage meters, Setup and Settings at the bottom, collapse to a rail, drag to resize | R3a |
| R3d | Canvas (revised direction 8): fit to viewport, responsive vertical stacking, zoom and pan, stacked legend with distinct line styles, unobstructed relationship labels | R3c |
| R3e | Viewport-filling layout and state-sized cards (revised direction 9) | R3d |
| R3f | Collision-free routing, compact header, in-canvas key, breadcrumb scope (revised direction 10) | R3e |
| R4a | Dashboard home, Agents route, sidebar Dashboard entry, first-run welcome (revised direction 11) | R3b merge |
| R4b | Unbounded agent list with page scroll; project node styling in tree and list (revised direction 11) | R3b merge; parallel with R4a |
| R3b | Live simulation (revised direction 6): continuous create, work, finish and remove through the event rules, with the observed Agent Tree motion; card presentation pass (harness tag, fold to one line) | R3a |
| Deferred | Decision Tree, Agent Queue and Delegate Board, Agent Lanes, Agent Graph (formerly R4–R7) | operator decision |

Fixture fields that later slices need beyond `fixtures/setup.json` are
drafted in the webapp workstream and proposed to the integration owner
before any shared schema changes, as in W3.

## Not in scope

Real sign-in, credential storage, harness detection or configuration
writes; any command; service read integration (W4); desktop packaging
(W6); using affectUI source or assets.
