# Odin ecosystem integration plan

Date: 2026-10-14. Status: proposed cross-repository implementation contracts.
Companion to the [implementation blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md)
and [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md); subordinate to the
[decision record](../DECISIONS.md) and the [I/O contract](ODIN-IO-CONTRACT.md).
Adapted for the Odin repository from extraction snapshot `2026-10-14-14fdab3`
([frozen original](../history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-ECOSYSTEM-INTEGRATION.md));
the adaptation changes links and provenance, not proposals. The source review's
corrections added the archive-scope reading (§7) and increment placement to
EC-03 and EC-04 ([`REVIEW-RESOLUTIONS.md`](../provenance/REVIEW-RESOLUTIONS.md)).
Updated 2026-10-16 for ODIN-ADR-006 to 015 ([decision record](../DECISIONS.md)
§4): the preamble, §1 and §4 to §10 carry dated notes, and §11 holds the
Saga-owned parts of the [consolidation plan](CONSOLIDATION-PLAN.md) as
proposals.

The tools remain independent products. Odin consumes versioned interfaces;
it does not merge their databases or make them all prerequisites for startup.
**Superseded in part (2026-10-16):** ODIN-ADR-006 supersedes "does not merge
their databases" for the transcript-archive and workstation surface-event
namespaces, which become namespaces of Odin's one event substrate, each with
one writing component. The execution ledger stays Saga's separate store; Odin
holds at most a read-only mirror filled through Saga's API and event cursor.
Each peer remains a separate product, and each item below remains a request to
that peer, until the Saga-side decisions in issue X-14 and the peers' own
recorded notes exist. The repository consolidation is a proposal (§11).
The changes here are implementation proposals, not claims that adapters exist.
No sibling repository was modified to produce this reference. Each peer owns
its interface; Odin pins a peer's contract under [`../contracts/`](../contracts/README.md)
only once that peer publishes one, and none has been pinned. Until then every
peer capability below has the status recorded here: observed, proposed or
unavailable.

Peer sources are cited as `repository:path` in the operator's local checkouts
as observed on 2026-10-14. They are not vendored here, are not required to read
this plan, and may have changed since. The 2026-10-16 notes rest on the
read-only inventories in
[`../research/consolidation-2026-10/`](../research/consolidation-2026-10/README.md).

## 1. Local baseline and evidence limits

The working trees, not remote Saga, were inspected. These are source/document
observations; the applications were not deployed or acceptance-tested in this task.
The rows are dated observations and were not re-verified during extraction.
The peer rows were re-inspected read-only on 2026-10-16; the 2026-10-14 HEAD
follows "was" in each.

| Repository / installed tool | Baseline | Observed capability and gap |
|---|---|---|
| Saga | HEAD `9e02823`; substantial uncommitted October docs (since committed; this repository's design inputs were captured clean at `14fdab3`). 2026-10-16: HEAD `a84f9ac`, clean | April implementation plus new supervisory-layer design; service extraction is future work. 2026-10-16: no ledger, run lifecycle, approvals, reviewer key, cancellation or kill switch exists in code |
| Skald | HEAD `22114dd` (2026-10-16; was `d364f8f`); Apache-2.0 license added 2026-10-14; no CI | Source collection, independent archive, CLI/TUI and backup; Braid, peer integrations, Odin provider and portable export workflow need work. The `changes` table has a writer but no reader |
| Heimdall | HEAD `3ca80b5` (2026-10-16; was `c7fee4b`); Apache-2.0 license added 2026-10-14; CI red | Task/checkpoint/review/TUI and Herdr binding facilities; retrieval foundation code exists, while README/status still describe broader integration as planned. The ranked planner, SSE and change feed do not exist; sensors are coupled to task records |
| Braid | HEAD `7e24af3` (2026-10-16; was `41bc392`); Apache-2.0 license added 2026-10-14; CI green | Retrieval library, CLI and subprocess contracts; Odin/Skald consumers and workload calibration remain work. Opens its own SQLite file per dataset and recomputes a whole-dataset digest on every write |
| WCU | HEAD `e61f8ed` (2026-10-16; was `c618243`), 12 commits ahead of `origin/main`; Apache-2.0 license added 2026-10-14; modified evaluation/config files | Two MCP servers, skill and Codex packaging, guarded execution/readback; shared desktop lease and Jev workflow are proposals. No lease, grant or caller identity exists in code |
| dotprivate | HEAD `51d0fce` (unchanged 2026-10-16); untracked contract docs | Ingest/sync tooling; selected-files preservation contract is explicitly unimplemented and names heimdall and skald as consumers, not Odin |
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

**Reuse:** D2–D6 and D17 (Saga-owned; Odin's obligations in [DECISIONS.md](../DECISIONS.md),
owners in the [decision map](../provenance/DECISION-MAP.md)): delegation records,
run lifecycle, authenticated reviews, approvals bound to exact artifacts, event
cursors, cancellation, limits, idempotency, and explicit uncertain outcomes.
Saga's interface is its pinned contract
([`../contracts/saga/2026-10-14-14fdab3/SAGA-SERVICE.md`](../contracts/saga/2026-10-14-14fdab3/SAGA-SERVICE.md));
the capabilities Odin requires are the I/O contract's Appendix B.

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

**Update under ODIN-ADR-009 (2026-10-16).** Herdr is to be driven through its
CLI: locally by the workstation daemon where one runs, or over SSH with
`herdr --machine` from the service, with the SSH key and the Herdr target held
by the service and never by a session. The automation API remains unreviewed
(decision record §3 item 8) until the adapter is built against the installed
version.

Launching `skald tui` in a pane remains feasible as workspace setup; heimdall's
TUI is to be replaced by the human view (§5).
Automatic project selection or linked navigation requires each application's
supported interface; opening a TUI does not implement the data integration.

**Acceptance:** moved/replaced panes invalidate bindings; takeover prevents
automated prompting; a prompt timeout reconciles before retry; visibility loss
does not imply worker failure; closing the workspace client does not cancel work.

References: [Herdr automation](https://herdr.dev/docs/agent-automation/) and
local Heimdall Herdr contract (`heimdall:docs/guides/HERDR-SETUP.md`).

## 5. Heimdall: workstream visibility without competing ownership

**Superseded by ODIN-ADR-007 (2026-10-16).** The ownership bridge proposed
below is not planned. Odin's commitment record is the only editable record of
task state, checkpoints and task decisions for work run through these tools.
Instead:

- **Import, not bridge.** Heimdall's tasks, checkpoints and decisions are
  imported once into commitments, each with its original identity and revision
  as provenance, and the import writes a receipt; a second run on the same
  database adds nothing (AC-38). After the import, heimdall-side edits are
  refused, or ignored with a visible record. The mapping from heimdall's record
  types is kept with the record schemas. Delegations, approvals, verdicts and
  run states stay Saga's records.
- **Sensors are to move to the workstation daemon.** Heimdall's surface sensors
  (compositor, Herdr agents, browser, file trees) become workstation-daemon
  sensors (ODIN-ADR-009) with explicit configuration instead of discovery
  through task-bound session bindings and task resources. Their observations
  are state-only or log-only inbound sources, never authority (ODIN-ADR-010).
  The 2026-10-16 inventory found them coupled to task records, so extracting
  them is a refactor, not a move.
- **One human view.** Heimdall's TUI and bar are to be replaced by one human view,
  which shows commitments, runs and transcripts with their owners attributed,
  and by a bar adapter on the service API.
- **Peer record.** Retiring heimdall's task authority and the skald–heimdall
  amendment is heimdall's decision to record in its own repository (EC-13).
  Until then, heimdall's record and the amendment stand unchanged there.
  EC-05 is withdrawn from Odin's plan.

**Acceptance:** a repeated import yields one set of commitments and one
receipt; a later heimdall-side edit never changes a commitment and leaves a
visible record; heimdall's absence hides no task state.

The 2026-10-14 proposal follows, kept for traceability. Where it conflicts
with the paragraphs above, they win.

**Reuse:** task/contract/decision records, checkpoints, dependency views, needs-you
TUI, explicit session bindings, and scoped client access. The existing MCP
checkpoint grant does not confer arbitrary contract/decision acceptance authority.

**Conflict to resolve:** D20 (inherited from the joint Saga record, now Odin's) makes Odin's commitment record authoritative
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

Sources: README (`heimdall:README.md`),
MCP contract (`heimdall:docs/guides/MCP-SETUP.md`), and
Skald amendment (`skald:SKALD-HEIMDALL-AMENDMENT.md`).

## 6. Skald: transcript visibility and archive integration

**Reuse:** selected-root native source discovery, reusable parsing/record
contracts, immutable source revisions, capture gaps, archive reads, project
grouping, native recaps, TUI, and consistent full-archive backup/restore.
Skald remains useful without Odin, Heimdall, Braid, or an inference provider.

**Update under ODIN-ADR-006 (2026-10-16).** Skald's capture library is to run as
the capture module of the workstation daemon and write the transcript-archive
namespace of Odin's substrate. Requests to skald (EC-14):

- the capture library behind a `Sink` interface, with the collector and
  discovery moved to a public package;
- a local durable spool on the workstation, because capture runs there and
  the substrate on the homelab: records, gaps and the checkpoint are appended
  as one atomic batch per checkpoint, and redelivered records are deduplicated
  by record key and source revision (AC-41);
- one namespace key, derived from machine-id (heimdall's embedded capture
  derives it from the hostname today, so one transcript gets two keys);
- a reader for the `changes` table, which today has a writer and no reader,
  so the existing archive can be ingested incrementally instead of in one step.

Skald's own archive stays a standalone sink, so the skald binary stays useful
without Odin, and it remains the owner of consistent full-archive backup
(ODIN-ADR-012). Runtime enrollment stays I6; before that the module is
exercised on synthetic fixtures. Item 2 below is moot: Odin history is a
namespace of the same substrate, so no Odin provider is needed. Its rule that
Odin's references never become a second native event stands.

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
have remaining gates in STATUS.md (`skald:STATUS.md`). Do not mark an
assignment fully archived when only its primary session has been captured.

**Acceptance:** source disappearance leaves retained history; native source and
export copies deduplicate by origin/revision; gaps remain visible; imported task
status stays attributed; archive read failures do not halt execution; restricted
reads cannot expand into another project's records.

Sources: README (`skald:README.md`),
archive setup (`skald:docs/ARCHIVE-SETUP.md`),
record contract (`skald:docs/CONTRACT-V1.md`),
TUI (`skald:docs/TUI.md`).

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
past sessions. Reading of "never indexes the chat log" (D10.1; `DECISIONS.md`
issue X-4, review finding N7): Braid never indexes Odin's **active** chat, which
is the source record's own wording (frozen record §2, "braid still never indexes
Odin's active chat") and the I/O contract's `recall` row; the `archive` scope is
read-only retrieval over source material that Skald has archived and explicitly
published, with original record ids. Skald provides exact expansion; Braid
provides candidates and provenance. Shared origin keys prevent multiple copies
from becoming multiple supporting sources. The reading settles the wording only:
the Skald and Braid capabilities it needs remain proposals of their owners
(EC-06, EC-07), Skald retrieval is open (§5.11), and the scope is enabled no
earlier than I6.

Dataset isolation is not authentication. The adapter must select authorized
datasets and recheck scope on expansion. Temporal ranking is not proof a fact is
current; inspect source revision and supersession. Purges remove published nodes
and derived vectors. A stale dataset is labeled and cannot override current
accepted state.

**Update under ODIN-ADR-006 (2026-10-16).** Braid runs as an in-process
library, not a child process over its stdio protocol, over published, scoped
namespace data held in its own per-dataset files; it does not share the
substrate's database. Because every write recomputes a digest over the whole
dataset, publication is batched, never per event. It still never indexes
Odin's active chat (X-4), and runtime retrieval stays I6. Requests to braid
(EC-15): supported library embedding, and the stdio protocol layer movable
out of `package main` into a package, so child-process isolation stays
available where it is wanted.

**Likely change location:** mostly Odin/Skald/Heimdall consumer adapters, not a
new Braid core architecture. Add core capabilities only after a concrete gap is
demonstrated. Heimdall has `internal/retrieval` foundation code despite older
README wording; inspect and finish that contract before duplicating it.

**Acceptance:** wrong-workstream and superseded hits are tested; required context
is never truncated silently; source/index revisions remain attributable; no-index
fallback retains mandatory context; a retrieved instruction never becomes an
approval or active policy automatically.

Sources: README (`braid:README.md`),
retrieval contract (`braid:docs/retrieval-contract.md`),
Heimdall integration (`braid:docs/heimdall-integration.md`).

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

**Update under ODIN-ADR-011 (2026-10-16).** The shared boundary becomes a
gated process of the workstation daemon. WCU's guarded input runs there under
a dedicated Unix user that alone owns the input socket. That process is the
only holder of the seat lease for every cooperating client and checks lease,
grant scope, target and expiry on admission and again before every input
segment, so inside it the lease is complete. It is not device-wide: other
processes of the operator's user can still reach the compositor's
virtual-keyboard protocol and dispatcher IPC, and whether the compositor can
deny them is unverified. Until that is verified, the lease binds cooperating
clients only. The observation and input MCP servers become thin shims that
forward to the process and carry the caller's session identity. The Codex
plugin, evaluations and reports stay standalone in WCU. WCU's 12 local
commits ahead of `origin/main` are pushed before any import, so the public
copy and the daemon's contract hash agree. The process stays disabled until a
delegation naming desktop authority exists and the operator decides §3 item 9,
and then serves only a dedicated desktop worker. Requests to WCU: EC-16.

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

Sources: README (`wayland-computer-use:README.md`),
feedback (`wayland-computer-use:docs/feedback.md`),
execution contract (`wayland-computer-use:skills/wayland-computer-use/references/execution-and-context.md`).

## 9. Dotprivate: selected preservation, not the runtime store

**Update under ODIN-ADR-012 (2026-10-16).** dotprivate is off Odin's
dependency path. Odin writes the selected project package (D22.1) atomically
to its own export directory, stages only the package path, applies its own
secret and personal-data screen, runs git itself, and records receipts that
distinguish "copied locally", "committed" and "confirmed on the remote"; an
uncertain push is reconciled by observing the ref before any retry (AC-24,
AC-25). The export directory never sits inside a dotprivate-managed
`.private` clone, whose background sync would race Odin's writes. The
selected-files contract remains dotprivate's own, with heimdall and skald as
its named consumers. The operator may still ingest Odin's export with
dotprivate by hand; that is dotprivate's feature, not an Odin interface.
EC-08 and EC-09 are withdrawn from Odin's plan (identifiers kept in §10). The
rest of this section still describes what an export contains and excludes;
the prerequisite below is withdrawn and kept for traceability.

**Reuse:** explicit project/environment scopes, copying selected private material,
local Git storage and remote publication. This is independent of task completion.

**Prerequisite (withdrawn by ODIN-ADR-012):** implement and release dotprivate's own
selected-files contract (`dotprivate:docs/SELECTED-FILES-CONTRACT.md`).
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
| EC-03 | Odin | Herdr workspace adapter and explicit session bindings; validate installed API. Read-only inspection in I3; adapter, bindings, adopt and takeover in I4 |
| EC-04 | Skald + Odin | Native source enrollment and Odin provider; define remote-source coverage. Runtime enrollment in I6; fixtures only before. **Re-scoped by ODIN-ADR-006:** the Odin provider is moot (Odin history is a substrate namespace); enrollment becomes capture-module work over skald's library (EC-14) |
| EC-05 | Heimdall + Odin | Adopt external-work projection semantics and revisioned owner command relay. **Withdrawn by ODIN-ADR-007; identifier retained; replaced by EC-13** |
| EC-06 | Skald + Odin | Exact evidence navigation and archive scope; depends on EC-01/04 |
| EC-07 | Consumers + Braid | Published scoped datasets and exact expansion; archived conversations only, never the active chat (§7). **Re-scoped by ODIN-ADR-006:** braid as an in-process library over published scoped data in its own per-dataset files, with batched publication (EC-15) |
| EC-08 | dotprivate | Release selected-files contract and conformance tests. **Withdrawn from Odin's plan by ODIN-ADR-012; identifier retained;** remains dotprivate's own work |
| EC-09 | Skald / Heimdall / Odin | Selected export consumers; depend on EC-08, no substitute Git interface. **Withdrawn by ODIN-ADR-012; identifier retained;** Odin's own package export with three-state receipts replaces Odin's part (§9; AC-24, AC-25) |
| EC-10 | Odin + WCU boundary | Shared seat broker, takeover and reconciliation; desktop authority prerequisite. **Becomes the gated desktop-input process of the workstation daemon (ODIN-ADR-011);** it binds cooperating clients only until the compositor restriction is verified; WCU's part is EC-16 |
| EC-11 | Odin workflow package | Shadow textual evaluator; depends on measured baseline and EC-10 for input effects |
| EC-12 | All data-owning consumers | Source-identity deletion propagation, pending receipts, and documented backup/export limits |
| EC-13 | Heimdall | Record retirement of task authority and the skald–heimdall amendment; review the import mapping Odin authors with its record schemas (§5; ODIN-ADR-007). Feeds gate G-10 |
| EC-14 | Skald | Sink interface, public collector, changes-table reader (§6; ODIN-ADR-006). Feeds gate G-10 |
| EC-15 | Braid | Library embedding, protocol layer movable to a package (§7; ODIN-ADR-006). Feeds gate G-10 |
| EC-16 | WCU | Input capability move, caller-identity shim, dedicated uid (§8; ODIN-ADR-011). Feeds gate G-10 |

EC-13 to EC-16 are requests that the operator records in each peer's own
repository; together they feed the roadmap gate G-10 (peer-repository
records). None exists yet, and no Odin code calls a peer capability before it
is published and pinned.

Freeze only the contracts needed for the next increment. Preserve each product's
standalone operation, version negotiation, and unavailable-peer behavior. Run
the [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md) as integrations land.

## 11. Proposals pending Saga's record (not decisions)

Nothing in this section is recorded. It holds the Saga-owned parts of the
[consolidation plan](CONSOLIDATION-PLAN.md) until Saga's own record decides
them (issue X-14 in the [decision record](../DECISIONS.md)). The drafts
ODIN-ADR-016 to 019 named here are not recorded and not in effect, and D10.6,
D14.1 and D14.7 stand as carried. Saga's guarantees (isolation, enforced
limits, durable run records, recovery) are Saga's and are claimed for no
other backend, fake or real (D23.3).

| Proposal | Saga-owned clauses | Draft | What would make it a decision |
|---|---|---|---|
| The execution backend (Saga) runs as a separate, independently restartable process with its own store, record, contract and conformance checks, and may share a repository and release train with Odin | D1.2, D14.1, D14.7 | ODIN-ADR-016 | Saga's record decides it; Saga publishes a new contract version; Odin repins it and rechecks Appendix B (X-3) |
| Workers report to the backend's own intake, replacing MQTT for Saga's worker transport; the broker stays, because other homelab systems use it; Odin reads the backend's event cursor and never receives worker transport (B-17) | D3.3, D13.4a, D15.B, contract MQ-1 | ODIN-ADR-016 | As above |
| Bragi becomes a scheduled Odin session class and Eir an Odin assignment class; Eir keeps an operator-invoked path that needs neither Odin nor the backend, outside both failure domains | D11, D12.1, D17.4b | ODIN-ADR-017 | Saga's record transfers them |
| One repository with imported histories and archived originals, and the names of the repository, the deliverable prefix and the deployables | D13.1, D14.1, D14.6 | ODIN-ADR-018, 019 | Saga's record, the peers' notes (EC-13 to EC-16) and a naming decision within D13 (X-5) |

Until these exist, §3 holds as written: Odin reaches Saga only through its
pinned API, Saga's ledger alone decides approval and completion, and results
against the fake backend are labelled fake-backend evidence. No deployable or
product name is chosen here.
