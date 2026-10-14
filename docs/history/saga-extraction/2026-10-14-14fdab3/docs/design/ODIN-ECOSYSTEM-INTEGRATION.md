# Odin ecosystem integration plan

Date: 2026-10-14. Status: proposed cross-repository implementation contracts.
Companion to the [implementation blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md)
and [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md).

The tools remain independent products. Odin consumes versioned interfaces;
it does not merge their databases or make them all prerequisites for startup.
The changes here are implementation proposals, not claims that adapters exist.
No sibling repository was modified to produce this reference.

## 1. Local baseline and evidence limits

The working trees, not remote Saga, were inspected. These are source/document
observations; the applications were not deployed or acceptance-tested in this task.

| Repository / installed tool | Baseline | Observed capability and gap |
|---|---|---|
| Saga | HEAD `9e02823`; substantial uncommitted October docs | April implementation plus new supervisory-layer design; service extraction is future work |
| Skald | HEAD `d364f8f` | Source collection, independent archive, CLI/TUI and backup; Braid, peer integrations, Odin provider and portable export workflow need work |
| Heimdall | HEAD `c7fee4b` | Task/checkpoint/review/TUI and Herdr binding facilities; retrieval foundation code exists, while README/status still describe broader integration as planned |
| Braid | HEAD `41bc392` | Retrieval library, CLI and subprocess contracts; Odin/Skald consumers and workload calibration remain work |
| WCU | HEAD `c618243`; modified evaluation/config files | Two MCP servers, skill and Codex packaging, guarded execution/readback; shared desktop lease and Jev workflow are proposals |
| dotprivate | HEAD `51d0fce`; untracked contract docs | Ingest/sync tooling; selected-files preservation contract is explicitly unimplemented |
| Herdr | Installed `0.8.2` | Local Heimdall bindings target protocol 20; latest web capabilities must not be assumed available in this binary |

Before implementation, record full commits, dirty-file digests, adapter versions,
and installed capabilities. Repository HEAD alone cannot reproduce a dirty tree.
Resolve code/document status disagreements through focused inspection and tests,
not optimistic interpretation of a commit title.

## 2. Shared identity and provenance

Define mappings, not a replacement identity system. A proposed binding record
contains Odin instance/project/commitment/assignment IDs, authority-owner ID and
revision, Saga instance/delegation/run IDs where applicable, harness/native session
identity, optional Herdr host/server incarnation/terminal/pane binding, and Skald
source/conversation references. Preserve each owner's IDs unchanged.

Bindings can be absent or stale. A moved pane, copied transcript, common cwd,
matching title, or reused process ID is not proof of identity. Session replacement
records a new binding and its predecessor. Bindings are explicitly established
and revision-checked. Project grouping is a display association, not an authority
grant; one conversation may relate to several projects or none.

Every imported view reports source owner, source revision/sequence, fetch time,
and freshness/coverage. A retained transcript is evidence of a conversation,
not proof of live process presence. A document path mentioned in that transcript
is not preservation of the document's bytes.

## 3. Saga: execution and authority

**Reuse:** D2–D6 and D17 in [DECISIONS.md](../DECISIONS.md): delegation records,
run lifecycle, authenticated reviews, approvals bound to exact artifacts, event
cursors, cancellation, limits, idempotency, and explicit uncertain outcomes.

**Odin adapter work:** submit approved assignments, associate returned run IDs,
consume events transactionally, attach evidence, send scoped guidance, and expose
stop/reconciliation outcomes. Publish run status to operator views without making
those views independent launchers or completion authorities.

Herdr must not create a second worker when displaying a Saga-owned run. The Saga
execution adapter owns creation/cancellation; the workspace adapter only exposes
a supported attachment or a clearly labeled log/status view. No Docker socket
is given to a planner, workspace plugin, or computer-use worker.

**Acceptance:** duplicate submission yields one run; stale approval is refused;
dependency starts only after `verified`; restarting Odin leaves workers intact;
lost connectivity cannot be reported as successful remote cancellation.

## 4. Herdr: workspace and supported session controls

**Reuse:** CLI/socket layout and agent primitives, explicit IDs, attachment,
agent state and session identity where supported. Use the installed API schema.
Latest documentation describes prompting/waiting, but waits are not assignment
receipts and `done` is readiness for input, not verified work.

**Odin adapter work:** organize project workspaces; show the planning client,
workers, tests and views; map explicit live bindings; support adopt/takeover/return
where the harness can cooperate. Use API operations for layout and launch, not
WCU keystrokes. Keep native SDK sessions distinct from interactive PTY sessions;
an SDK transcript view is not an attachable native TUI.

Launching `skald tui` or `heimdall tui` in panes is feasible as workspace setup.
Automatic project selection or linked navigation requires each application's
supported interface; opening a TUI does not implement the data integration.

**Acceptance:** moved/replaced panes invalidate bindings; takeover prevents
automated prompting; a prompt timeout reconciles before retry; visibility loss
does not imply worker failure; closing the workspace client does not cancel work.

References: [Herdr automation](https://herdr.dev/docs/agent-automation/) and
[local Heimdall Herdr contract](../../../heimdall/docs/guides/HERDR-SETUP.md).

## 5. Heimdall: workstream visibility without competing ownership

**Reuse:** task/contract/decision records, checkpoints, dependency views, needs-you
TUI, explicit session bindings, and scoped client access. The existing MCP
checkpoint grant does not confer arbitrary contract/decision acceptance authority.

**Conflict to resolve:** Saga D20 makes Odin's commitment record authoritative
for Odin-managed work. Heimdall and its Skald amendment make Heimdall authoritative
for native accepted tasks. Neither should be silently reinterpreted.

**Proposed resolution:** add an externally owned workstream projection, separate
from native accepted task records:

- Native Heimdall tasks retain existing authority and transaction rules.
- Odin commitments appear with `owner=Odin`, external identity/revision, and
  an explicitly stale/offline state. Saga owns the referenced run and delegation.
- The same UI can display both classes, but cannot independently mark an imported
  Odin commitment complete. Controls route commands to its authoritative service.
- Desktop/window bindings remain Heimdall observations. Their presence does not
  make Heimdall the owner of the assignment or approval.
- A native task can be linked to an Odin assignment without duplicating its
  accepted task state. Automatic bidirectional ownership transfer is out of v1.

The projection API, UI distinction, command relay, and stale-revision handling
are new work. Until they exist, launch the current TUI for native work and use
Odin's own overview for Odin work; do not fabricate native checkpoints to simulate
an integrated authoritative view. A later ownership transfer needs an explicit
handoff protocol and separate adoption in both projects.

**Acceptance:** imported records cannot be edited through native acceptance
commands; commands reach the owner once; stale revisions fail visibly; Odin
absence leaves native Heimdall tasks usable; displaying old data grants nothing.

Sources: [README](../../../heimdall/README.md),
[MCP contract](../../../heimdall/docs/guides/MCP-SETUP.md), and
[Skald amendment](../../../skald/SKALD-HEIMDALL-AMENDMENT.md).

## 6. Skald: transcript visibility and archive integration

**Reuse:** selected-root native source discovery, reusable parsing/record
contracts, immutable source revisions, capture gaps, archive reads, project
grouping, native recaps, TUI, and consistent full-archive backup/restore.
Skald remains useful without Odin, Heimdall, Braid, or an inference provider.

**Changes needed:**

1. Enroll supported worker/planner sources from explicit adapter configuration.
   Remote/container transcripts require a supported source transport or export;
   do not assume a local root watcher can see a VM. Report coverage gaps.
2. Add a provider for Odin service events/chat records, preserving per-line chat,
   producer and correlation identity. Distinguish original harness records from
   Odin's copied/selected references to them; do not invent a second native event.
3. Extend explicit session/project associations to carry Odin assignment and
   Saga run references. Add operator navigation from a request/checkpoint to
   its exact conversation record and back, once the peer interfaces exist.
4. Implement L3 scoped retrieval using Braid and bounded exact expansion.
   Native summaries remain source claims, not accepted task decisions.
5. Support portable selected exports, provenance, and deletion/redaction handling
   needed by the consumers. Preserve full-archive recovery as a separate facility.

Native subagent/fork discovery, source activation, and broader peer/group features
have remaining gates in [STATUS.md](../../../skald/STATUS.md). Do not mark an
assignment fully archived when only its primary session has been captured.

**Acceptance:** source disappearance leaves retained history; native source and
export copies deduplicate by origin/revision; gaps remain visible; imported task
status stays attributed; archive read failures do not halt execution; restricted
reads cannot expand into another project's records.

Sources: [README](../../../skald/README.md),
[archive setup](../../../skald/docs/ARCHIVE-SETUP.md),
[record contract](../../../skald/docs/CONTRACT-V1.md),
[TUI](../../../skald/docs/TUI.md).

## 7. Braid: scoped context, including archived conversations

**Reuse:** exact reads, lexical retrieval, optional dense/graph/recency stages,
hard eligibility filters, dependency bundles, revisioned snapshots, byte-bounded
context export, cancellation, and evaluation controls. Each consumer owns its
dataset and source publication. No mandatory global Braid service is needed.

**Odin consumer work:** publish selected source documents, accepted decisions,
lessons, contracts, worker evidence and optional validated private exports with
source identity, revisions, scope, supersession and provenance. Fetch mandatory
current assignment/authority context exactly; relevance ranking must not omit it.
Use retrieval for supplementary context and exact reads for known source IDs.

**Archived conversation proposal:** retain the existing direct OptChat `zoom`
path for active Odin history; add a separately scoped Skald history corpus for
past sessions. The existing I/O contract's "never indexes the chat log" statement
needs clarification before this is enabled: no second index of the live working
chat, but optional retrieval over explicitly published archived source material.
Skald provides exact expansion; Braid provides candidates and provenance. Shared
origin keys prevent multiple copies from becoming multiple supporting sources.

Dataset isolation is not authentication. The adapter must select authorized
datasets and recheck scope on expansion. Temporal ranking is not proof a fact is
current; inspect source revision and supersession. Purges remove published nodes
and derived vectors. A stale dataset is labeled and cannot override current
accepted state.

**Likely change location:** mostly Odin/Skald/Heimdall consumer adapters, not a
new Braid core architecture. Add core capabilities only after a concrete gap is
demonstrated. Heimdall has `internal/retrieval` foundation code despite older
README wording; inspect and finish that contract before duplicating it.

**Acceptance:** wrong-workstream and superseded hits are tested; required context
is never truncated silently; source/index revisions remain attributable; no-index
fallback retains mandatory context; a retrieved instruction never becomes an
approval or active policy automatically.

Sources: [README](../../../braid/README.md),
[retrieval contract](../../../braid/docs/retrieval-contract.md),
[Heimdall integration](../../../braid/docs/heimdall-integration.md).

## 8. Wayland Computer Use: optional supervised desktop work

**Reuse:** independent observer/input MCP servers, skills and host packaging,
guarded frames, target checks, bounded sequences, accessibility/readback,
explicit outcome conditions, execution receipts, and application-specific paths.
Local source reports `wcu-tools-5`; README contains older `wcu-tools-3` wording.
Negotiate actual runtime capabilities instead of assuming either document alone.

**Odin integration work:** create a dedicated scoped desktop assignment, associate
progress/evidence with its commitment, and acquire an exclusive desktop-seat
lease before input. Enforce the lease at a shared broker or tool boundary across
cooperating clients; one prompt or one MCP process's lock is insufficient when
several hosts can control the same seat. Stop/expiry/restart invalidates ownership;
human takeover suspends automation. Unmanaged input and focus races remain limits.

**Optional workflow component:** classify bounded textual observations or rank
already eligible procedures with a decision model. Keep this outside WCU's input
primitives. Exact checks remain code. Jev's currently documented text-only input
cannot locate screenshot coordinates. Accessibility references are not input
capabilities. A suggested action must still pass current observation/guard and
authority checks. Missing accessibility escalates to a capable agent; there is
no implicit OCR or permission expansion.

Terminal control and VM access remain excluded by default under D21. Herdr's
structured workspace adapter handles session layout; desktop automation cannot
route around Saga. Prefer APIs, browser connectors, and verified application
surfaces where available. Host permissions and delegated desktop authority remain
necessary; loading a plugin is not an action grant.

**Acceptance:** two workers cannot acquire input simultaneously; human takeover
prevents new segments; stale frames reject; uncertain input reconciles without
blind retry; exact readback is not replaced by a model score; hosted classification
obeys D9's content restrictions. Evaluate whole tasks, including model turns and
approvals, against the existing WCU workflow.

Sources: [README](../../../wayland-computer-use/README.md),
[feedback](../../../wayland-computer-use/docs/feedback.md),
[execution contract](../../../wayland-computer-use/skills/wayland-computer-use/references/execution-and-context.md).

## 9. Dotprivate: selected preservation, not the runtime store

**Reuse:** explicit project/environment scopes, copying selected private material,
local Git storage and remote publication. This is independent of task completion.

**Prerequisite:** implement and release dotprivate's own
[selected-files contract](../../../dotprivate/docs/SELECTED-FILES-CONTRACT.md).
It is currently a proposal. Its manifest-bound requests, checkout serialization,
unrelated-change preservation, durable receipts, and reconciliation are required
before automated selected publication. Existing broad `sync` is not a substitute.

An export selection can contain versioned source specs, approved plans,
project-specific private notes, relevant instruction-file snapshots, selected
evidence and portable conversation exports. Include origin/digest/revision and
the relationships needed to interpret them. Public/project-owned instruction
files and code retain their normal repository history; a private snapshot records
which version was used rather than becoming a competing editable authority.

Keep live SQLite/WAL files, disposable indexes, credentials, and uncontrolled
desktop captures outside this export path. Skald owns consistent archive backups.
Source transcript discovery is not blanket permission to publish its contents.
Use an explicit selection/retention policy. Git history makes deletion different
from removing the latest file: do not promise full redaction of preserved history
without an implemented procedure and evidence across destinations/backups.

**Acceptance:** only selected bytes are committed; unrelated staged/unstaged
changes survive; local-copy/local-commit/remote-confirmed states are distinct;
retry after uncertain push reconciles the intended commit/ref; an unavailable
remote leaves work usable and preservation pending.

## 10. Contract-first cross-repository work queue

These are proposed work items, not created issues or existing callable APIs.

| ID | Owner | Work / dependency |
|---|---|---|
| EC-01 | Odin | Version the identity/event/assignment envelope and adapter capabilities |
| EC-02 | Odin + Saga | Implement governed submission, cursor replay, evidence and stop; first live-project prerequisite |
| EC-03 | Odin | Herdr workspace adapter and explicit session bindings; validate installed API |
| EC-04 | Skald + Odin | Native source enrollment and Odin provider; define remote-source coverage |
| EC-05 | Heimdall + Odin | Adopt external-work projection semantics and revisioned owner command relay |
| EC-06 | Skald + Odin | Exact evidence navigation and archive scope; depends on EC-01/04 |
| EC-07 | Consumers + Braid | Published scoped datasets and exact expansion; clarify archived-chat design first |
| EC-08 | dotprivate | Release selected-files contract and conformance tests |
| EC-09 | Skald / Heimdall / Odin | Selected export consumers; depend on EC-08, no substitute Git interface |
| EC-10 | Odin + WCU boundary | Shared seat broker, takeover and reconciliation; desktop authority prerequisite |
| EC-11 | Odin workflow package | Shadow textual evaluator; depends on measured baseline and EC-10 for input effects |
| EC-12 | All data-owning consumers | Source-identity deletion propagation, pending receipts, and documented backup/export limits |

Freeze only the contracts needed for the next increment. Preserve each product's
standalone operation, version negotiation, and unavailable-peer behavior. Run
the [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md) as integrations land.
