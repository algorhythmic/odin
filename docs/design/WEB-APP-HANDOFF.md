# Odin web app documentation and implementation handoff

Date: 2026-10-21. Recipient: Odin, orchestrating the documentation and
implementation work.

Build a purpose-built, barebones web app as Odin's primary human view.
Its defining feature is an interactive agent tree that makes it easy to
see who started whom, what each session is working on, and where the
operator needs to intervene. Use reusable web UI components and a
consistent visual style. The same application should work in a browser
and in a dedicated Chromium app window on Omarchy.

The operator explicitly wants the agent tree and a purpose-built web
app. The layout, rollout and implementation defaults below turn that
direction into an actionable plan. First reconcile them into Odin's
decision record; this handoff does not itself amend the authoritative
documents or claim any implementation exists. Do not expand this work
into a Saga application redesign or cross-repository consolidation.

## Product direction

The web app becomes the primary place to understand and direct Odin's
work. It combines commitments, planning conversations, sessions, runs,
review results and evidence in one navigable interface. Telegram stays
available for remote interaction. Terminal attachment remains useful
where an adapter supports it, but the operator should not need a
terminal workspace to understand overall progress.

The visual reference is Flo's
[agent tree demonstration](https://x.com/flohoeller/status/2112150373565612534/video/1),
captioned "Agent tree component, see who started whom". It shows
connected session cards with roles, models, tasks, status, cost and
elapsed time. Use that interaction idea as inspiration; the deliverable
is an Odin interface with Odin's actual records and semantics.

The desktop form is a Chromium app window with a launcher entry and
its own window identity. It uses the same web app and service as an
ordinary browser tab. An Electron or other native wrapper is not
required for v0. Closing the window must not stop sessions or lose work.

## Interface scope

### Overview

Open on an overview of projects, commitments that need attention,
pending decisions and approvals, and active work. Show enough context
to distinguish blocked work from work that is merely running. Selecting
an item opens its project and the relevant session or record.

### Project workspace

Use a project navigation area, a planning conversation or activity area,
and an agent tree. Selecting a tree node opens a detail panel with its
assignment, transcript, related run, evidence, budget and available
actions. Preserve the selected node and reading position during live
updates. Provide shareable routes to projects, sessions and records.

The tree must support expanding and collapsing descendants, selecting
a node, following its parent, and fitting the visible branch on screen.
Start with a readable automatic layout; manual graph editing is outside
v0. A compact list alternative must support keyboard use and narrow
screens. Large trees must not force every transcript or hidden branch
to load at once.

Each session card should show its role, short assignment, model when
known, lifecycle state, and whether it needs operator input. Show cost,
elapsed time and budget information when supplied by records. Unknown
cost is unknown, not zero; identify estimates and avoid counting parent
aggregate cost again when summing descendants.

### History

Completed and retired sessions remain inspectable with their original
relationships and evidence. History should distinguish current work
from previous attempts and resumptions. It must remain useful after a
host disconnects or an app window closes.

## Relationship and state semantics

The primary tree edge means session ancestry: which recorded session
started which other session. Assignment ownership, review, delegation
and run association are separate typed relationships. Do not turn
every relationship into a parent edge or imply that a reviewer was
started by the worker it reviews.

During schema work, define stable identities for sessions, assignments,
commitments and runs, plus explicit ancestry and provenance. Display
multiple roots where appropriate. An imported session with no known
parent must remain unparented; do not infer ancestry from timing,
window layout or transcript wording. A resumed session and a new
attempt must follow the recorded lifecycle identity rules.

The UI must distinguish session activity, assignment progress and run
outcome. A session ending or saying "done" does not establish verified
completion. Preserve `host_offline`, unknown outcomes, transcript gaps
and stale observations as visible states. Show who owns each record
and where evidence came from when inspecting details.

## Architecture and implementation defaults

Keep the browser a client of Odin's service. The service supplies
projections of records and accepts commands through the same recorded
command path as the other operator surfaces. Browser state may hold
layout preferences and current selection; it must not become another
editable task store or the authority for session lifecycle.

Serve the app from the service deployment, or alongside it under the
same authenticated origin. Use a snapshot plus a resumable update
stream, with an explicit cursor or revision. Choose the transport
during implementation. On reconnect, recover missed updates or obtain
a new snapshot; duplicates must not duplicate nodes or activity.
Indicate stale data and do not present a queued action as acknowledged.

Keep model credentials and service secrets out of the browser. Define
authentication, authorization, request validation and protection of
state-changing requests before enabling real commands. Project and
record access checks belong in the service. Render transcript content
as untrusted data, including safe handling of links and rich text.

Use existing UI and graph libraries where they reduce implementation
work. Compare a small set against styling control, accessibility,
automatic layout, update performance, maintenance and licensing.
Record the choice and build a small vertical prototype before committing
to it. "Web component libraries" expresses the preference for reusable
components; it does not require standards-based Custom Elements over
framework components. Avoid building a design system or graph engine
from scratch.

The workstation daemon continues to host sessions and local
integrations. The web app is not another session host. Offer terminal
attachment only where supported; embedding a terminal is optional for
v0. Responsive browser access should be usable on a laptop and phone,
with the tree replaced by the list view where space is limited.

## Documentation work to orchestrate first

Read the current documents before editing. Preserve existing identifiers
and use the next available ADR number rather than assuming one here.

| Document | Required change |
|---|---|
| [Decisions](../DECISIONS.md) | Record the web app as the primary human view, the agent tree, Chromium app presentation, and the revised role of terminal surfaces. Name the exact inherited clauses amended, including the Herdr-first configuration and relevant parts of ADR-007 and ADR-010. |
| [Decision map](../provenance/DECISION-MAP.md) | Map the amended clauses to the new ADR without renumbering inherited decisions. |
| [I/O contract](ODIN-IO-CONTRACT.md) | Add the web operator surface, relationship semantics, query/update behavior and command acknowledgements. Specify approval content binding, state freshness and reconnect behavior. |
| [Implementation blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md) | Describe the browser/service boundary, frontend delivery, tree projection, session details and terminal attachment. Remove contradictory Herdr-first overview requirements. |
| [Roadmap](../ROADMAP.md) | Introduce early UI prototyping and incremental service integration. Separate human-view delivery from the later historical import currently grouped with I4. Keep import prerequisites attached to the import. |
| [Acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md) | Add scenarios for ancestry, navigation, updates, reconnect, command results, accessibility and desktop packaging. Keep existing scenario identities stable. |
| Repository guidance and entry points | Update AGENTS.md and relevant README or design indexes to reflect the recorded decision and actual implementation status. |

Update live-output digests and transformation notes where modified
documents are tracked by the extraction manifest. Preserve frozen
source bytes and source hashes. Keep existing unresolved issues open
unless the new recorded decision actually resolves their substance.

Run `python3 scripts/validate_docs.py` from the repository root after
the documentation changes. Also perform a semantic review for competing
claims about the primary surface, human-view timing and terminal
requirements. The validator proves documentation integrity, not that
those architectural statements agree.

## Implementation sequence

These are work packages within the existing roadmap, not replacement
increment identifiers. Each package should have an owner, prerequisites,
acceptance checks and a concrete reviewable result.

| Package | Deliverable and completion condition |
|---|---|
| Documentation alignment | ADR and dependent documents agree; implementation tickets identify enforcement checks for each behavioral requirement. |
| Synthetic UI prototype | Overview, project workspace, interactive tree, node details and responsive list view using clearly labeled synthetic data. Demonstrate a useful end-to-end interaction before adding polish. |
| Record and projection foundation | Add the required identities and relationship fields through I0 schema work, with validated synthetic fixtures. Define the browser-facing projection and update schemas without duplicating authoritative records. |
| Service read integration | Connect the UI to the available service foundation in I1/I2. Verify initial load, incremental updates, history, transcript gaps and reconnect. Label fake-backend evidence explicitly. |
| Operator command integration | Add conversation input and supported lifecycle/decision actions through the recorded command path. Capability checks determine available controls. Acknowledged, rejected and uncertain results are distinguishable. |
| Desktop delivery | Package the same app for Chromium app mode on Omarchy; verify launch, window identity, deep links, restart and reconnection. Document ordinary browser use and development startup. |

The prototype can proceed before a working service exists. Do not wait
for historical import to make current synthetic or service-backed work
visible. Integrate runtime features only when their underlying records
and service operations exist; a visual prototype must not silently
stand in for them. Existing live-execution prerequisites remain attached
to live execution, without making them a blocker for frontend work.

## Acceptance checks

Turn these into automated checks where practical, with manual browser
and desktop evidence for the interactions that need it.

1. A synthetic project displays multiple roots, a nested child session,
   two reviewer positions, a resumed session and a new attempt without
   conflating ancestry, ownership or review relationships.
2. Selecting a session shows the correct assignment, transcript,
   evidence and related run. A deep link restores that context after a
   reload; a missing or inaccessible record gives a useful response.
3. Incremental updates preserve selection and transcript reading
   position. Reconnect recovers missed events without duplicate nodes;
   an expired cursor triggers a consistent fresh snapshot.
4. Offline hosts, stale data, unknown costs, transcript gaps and
   uncertain command outcomes remain visible. A session ending does
   not visually mark its run verified.
5. Every enabled command creates the appropriate service record and
   displays the actual acknowledgement. Repeated submission uses the
   defined idempotency behavior. Unsupported actions are explained.
6. Approval controls display the exact request identity and proposal
   binding required by the contract; changed proposals invalidate old
   approval context. Stop reports acknowledged and uncertain outcomes.
7. Keyboard users can navigate and inspect the tree through an
   equivalent list. State is conveyed by text as well as color. Narrow
   layouts keep conversation and decision actions usable.
8. Unauthenticated or unauthorized access and unsafe transcript markup
   are rejected or safely rendered. No model credential is delivered to
   browser code or persisted in frontend storage.
9. A representative large synthetic tree remains usable with collapsed
   branches and paginated details. Record the dataset size and measured
   performance target in the implementation ticket before optimizing.
10. On Omarchy, the launcher opens the dedicated Chromium window.
    Closing and reopening it preserves service work and restores usable
    navigation. Ordinary browser access reaches the same records.

## Orchestration and completion

Begin by recording the decision and producing a dependency-ordered work
plan. Frontend prototyping can run alongside record and service work
once the projection contract is agreed. Keep implementation changes in
reviewable packages with demonstrations and evidence tied to the checks
above. Use the applicable Omarchy instructions when implementing desktop
configuration and packaging.

Keep status explicit: synthetic prototype, fake-backend integration,
service integration and validated desktop behavior are distinct results.
Update the roadmap as each result lands. Deliver the recorded decision,
aligned documents, runnable app, startup and packaging instructions,
acceptance evidence, and a short list of remaining limitations. Do not
stop after selecting a library or producing a static mockup.
