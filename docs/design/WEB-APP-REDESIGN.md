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
| R3 | Agent tree presentation pass to the reference (header summary, card layout, harness tag, fold to one line) | R1 |
| R4 | Decision Tree over the snapshot's recorded `decisions` | R1 |
| R5 | Agent Queue and Delegate Board (assignments, lineage capacity, admission blockers; synthetic fixture extension) | R1 |
| R6 | Agent Lanes (turns, waits, reviews, handoffs over time) | R1 |
| R7 | Agent Graph (typed relationships, reviewer positions, tools) | R1 |

Fixture fields that later slices need beyond `fixtures/setup.json` are
drafted in the webapp workstream and proposed to the integration owner
before any shared schema changes, as in W3.

## Not in scope

Real sign-in, credential storage, harness detection or configuration
writes; any command; service read integration (W4); desktop packaging
(W6); using affectUI source or assets.
