# Odin Heimdall and Skald consolidated work plan

**Prepared 2026-10-19. Status: proposed execution plan.** Make Odin the
operator's portfolio and commitment system, reuse Skald's capture and archive,
and retain Skald's standalone session browser. Import Heimdall's task,
checkpoint and decision records into Odin, then retire that task writer.
Reuse its useful sensors through the workstation daemon.

The first product outcome is a dependable answer to: **What changed, what
remains owed, what needs my attention, and where is the evidence?** Humans
and agents receive scoped views of the same records. Session browsing remains
useful without creating a commitment for every conversation.

This plan coordinates work in three repositories. It does not require their
merger, record a peer decision, authorize a live cutover, or change I0–I7.
[Decisions](../DECISIONS.md), the [I/O contract](ODIN-IO-CONTRACT.md), the
[blueprint](ODIN-IMPLEMENTATION-BLUEPRINT.md) and the
[roadmap](../ROADMAP.md) retain their authority. OHS identifiers below are
work packages, not replacements for existing AC, EC, I, S or L identifiers.

## Target ownership and retained products

| Area | Destination and owner | Treatment |
|---|---|---|
| Commitments, checkpoints, accepted task decisions, dependencies and progress | Odin service | One editable task authority under ADR-007; import native identity and revision as provenance |
| Portfolio priorities and project interpretation | Odin planning sessions | Proposed interpretations and work requests pass through service policy; Fable/Astra remain experimental role configuration from the newer baseline |
| Transcript normalization, capture identity, source revisions and gaps | Skald packages, consumed by the workstation capture module | Publish and pin reusable producer contracts; retain the standalone archive sink |
| Session browsing and exact transcript reads | Skald TUI, CLI and read API | Preserve independent operation and link from Odin's human view |
| Surface observations and source health | Heimdall-derived sensors in the workstation daemon | Separate observation from task ownership and desktop input; retain source epochs and coverage |
| Human continuity view and bounded agent context | Odin service projections | Shared record meanings, separate presentation and scope; writes use the recorded command path |
| Run approvals, delegations, run outcomes and enforced execution limits | Saga | External dependency; Odin references or mirrors its records through its API |
| Workspace recovery and desktop actuation | Existing owning components until separately migrated | Keep outside the initial continuity release and behind existing desktop-authority gates |

Keep Skald's browser as a maintained product capability. This differs from
the older [consolidation proposal](CONSOLIDATION-PLAN.md#6-component-migration-summary),
whose table replaces the Skald TUI. OHS-01 records the refinement before
implementation plans are treated as reconciled. ADR-006 already preserves
the standalone archive; ADR-007 already establishes Odin's task destination.

## Baseline and reusable work

| Repository or checkout | Observed baseline on 2026-10-19 | Reuse and remaining work |
|---|---|---|
| This Odin checkout | `899df14`; documentation scaffold | Keep its authority and provenance constraints. It contains no runtime implementation. |
| Newer Odin checkout | `a9f22a1`, clean; includes prototype integration `47e074e` | Reuse the committed local service, deterministic continuity, attributed memory, protocol checks and synthetic fixtures after integration review. Full I0/I1 exits, real harness enforcement, authenticated transport and live Saga remain open. |
| Heimdall | `3ca80b5`; local change in `internal/core/materialize_test.go` | Reuse task invariants, checkpoints, decisions, dependency semantics and sensor designs. Preserve the local change. Startup/recovery release gates remain; its independent planner is unstarted. |
| Skald | `22114dd`, clean | Reuse shared capture/record packages, archive, bounded reads, backup/restore and TUI. Complete relevant capture/recovery release gates and publish EC-14. Braid retrieval is future work. |

The 2026-10-17 diagnostic report recorded session-inventory and Herdr
agent-list failures, only Claude Code sources configured in Heimdall, and
no paired browser profiles. These are leads for OHS-02, not fresh machine
health or established root causes. Absence of Codex in Heimdall does not
justify duplicating Skald's existing Codex capture path.

Source documents and exact checkout locations are listed at the end.
Their reported test results are development evidence; each implementation
package below specifies the checks to reproduce for its selected revision.

## Delivery order and gates

| Package | Responsible repository | Deliverable | Dependencies and placement |
|---|---|---|---|
| OHS-01 | Odin, with operator decisions recorded by each peer | Selected implementation baseline and reconciled product scope | Start now; integrates newer Odin ADRs explicitly |
| OHS-02 | Heimdall and Skald | Reliable existing source visibility and standalone browser | Can start independently; fixes remain in their owning repositories |
| OHS-03 | Skald and Heimdall as producers, Odin as consumer | Published boundary contracts and task-import mapping | OHS-01; EC-13/14 and relevant G-10 records before imports |
| OHS-04 | Odin | Deterministic continuity and scoped human/agent views | OHS-01; unaffected I0 contracts then I1/I2 local preparation; OHS-03 fixtures |
| OHS-05 | Odin; Saga supplies its own prerequisite evidence | Real session host and governed execution path | Complete I0/I1 gaps, then I2; Saga Phase B before I3/live delegated work |
| OHS-06 | Heimdall and Odin | Rehearsed import and enforceable retirement of the old writer | OHS-03/04; OHS-05 live prerequisites before actual I4 migration; relevant G-10 |
| OHS-07 | Skald, Heimdall and Odin | Capture and sensor feeds connected to continuity | OHS-02/03/04; fixtures in I2, Herdr inspection I3, management I4, live archive integration I6 |
| OHS-08 | Odin | Optional model interpretation and attention proposals | OHS-04 and authorized real harness/data access; does not gate basic updates |
| OHS-09 | All three, with operator cutover | Integrated pilot, task-authority cutover and retirement receipt | OHS-05 live prerequisites and OHS-06/07; model features only if separately ready |

The immediate development path is **OHS-01 → OHS-03 → OHS-04**. OHS-02 can
improve today's tools independently. After contracts stabilize, migration
rehearsal, capture fixtures and runtime completion can proceed separately.
This is scheduling guidance, not authorization to edit a peer from Odin.

Under the current roadmap, the complete live product crosses I3, I4 and I6.
**Recommended sequencing decision:** propose a narrow observation-only
continuity pilot earlier than I6, covering selected source ingestion, exact
evidence reads and source health. Specify identity, retention, reader scope,
producer pins and removal behavior. Exclude task cutover, managed session
launch, worker dispatch and desktop input. Record the affected Odin clauses
and any producer-owned agreement before enabling it. Until then, early Odin
integration uses synthetic data and live archive ingestion remains I6.

Existing gates apply to the capability they protect:

| Gate or decision | Work it constrains |
|---|---|
| EC-13/14 and G-10 | Heimdall retirement and capture/sensor module moves; each peer records its own part |
| X-7 and producer contract gaps | Affected Review/guidance schemas and full compatibility; unresolved guidance remains held |
| X-11 and X-12 | Production writer ownership/failure domains; dedicated harness credentials and refresh ownership |
| Data policy, X-10 and X-13 | Real-history use, retention and semantic memory; provider disclosure and voice where applicable |
| Saga Phase B, G-4 and Appendix B | I3, live delegated work, live Saga submission and governed deployment cutover |
| X-1 and G-1 | Joint phase interpretation and formal documentation ownership transfer |
| X-14 and G-9 | Shared repository/release train and Saga-owned consolidation proposals; not a prerequisite for preparing this plan's independent components |

## Work packages

### OHS-01 Select and reconcile the implementation baseline

**Owner:** Odin engineering; operator and peer maintainers own their decisions.

1. Review and integrate the committed Odin work through `a9f22a1`, including
   its integration receipt, ADR-020–023, X-15, status documents and checks.
   Preserve conditional ADR-016–019 and reconcile current documentation
   rather than copying isolated modules into this scaffold.
2. Reproduce that baseline's documented checks with its pinned dependencies.
   Record what is usable locally, synthetic, planned or blocked; a test
   count does not establish completion of an increment.
3. Prepare repository-owned scope changes: keep Skald's browser; adopt
   Heimdall retirement under EC-13; publish Skald's EC-14 capture boundary;
   replace obsolete permanent-bridge proposals in each owner's plan.
4. Decide the earlier observation pilot described above. Keep its outcome
   independent of model selection, repository merger and task cutover.

**Exit:** one identified implementation baseline, reproduced local checks,
an owner and next action for each gap, and recorded dispositions for the
scope changes. Unaccepted proposals remain explicit.

### OHS-02 Restore useful visibility in the existing tools

**Owners:** Heimdall for its diagnostics/sensors; Skald for source capture,
archive health and browsing.

1. Reproduce the reported inventory and Herdr protocol failures using
   metadata-only diagnostics. Compare installed binaries, protocol versions,
   configuration and source revisions before selecting a fix.
2. Configure the selected Claude Code and Codex sources in Skald. Show
   enrollment, capture position, source age, failures and unavailable states.
   Do not add another Codex parser to Heimdall merely to match Skald.
3. Pair browser profiles only if browser observations are in the selected
   scope; otherwise report that source as disabled. Preserve existing hooks.
4. Verify standalone browsing with Odin absent, source loss/reappearance,
   daemon restart and archive restore. Prioritize recovery, capacity and
   large-transcript issues that affect the selected sources.

**Exit:** a before/after diagnostic receipt for each repaired source, one
attributable captured change per selected provider, explicit remaining gaps,
and usable browsing/restore without Odin. Capture recency is never presented
as live presence or verified task completion. Repairs do not close unrelated
Heimdall reboot/VM-power-loss or Skald release gates.

### OHS-03 Publish the shared boundaries and migration mapping

**Owners:** Skald publishes capture contracts; Heimdall reviews source task
semantics and records retirement; Odin owns its records and adapters.

Publish only the interfaces needed for the next slice:

| Boundary | Required content | Contract checks |
|---|---|---|
| Capture and archive changes, EC-14 | Record identity, source revision, ordering/cursor scope, checkpoint, gaps, correction/removal, schema version; public collector and sink boundary | Shared producer/consumer fixtures; replay, cursor invalidation, interrupted batch and unsupported-version cases |
| Surface observations | Host/source identity, epoch, observation time, coverage, binding evidence and unavailable reason | Reconnect, reused surface IDs, partial inventory and stale observation cases; no implied task ownership |
| Task import, EC-13 | Native IDs/revisions mapped to commitments, checkpoints, decisions, dependencies and artifact references; receipt and unmapped-state policy | Duplicate import, missing targets, cycles, incompatible states and changed export refusal |
| Evidence references and project associations | Exact source/revision locator, reader scope, provenance, revocation and explicit ambiguous association | Cross-project denial, stale revision, redaction and broken-locator cases |

Preserve many-to-many relationships between sessions and commitments.
Project path/name heuristics may propose associations; they cannot silently
grant access, assign an owner or create accepted obligations.

Odin pins published producer contracts and versions before calling them.
An internal table's existence is not a public changes API. The initial
adapter can be narrow; no universal framework is needed. Machine-readable
contracts and import receipts require schemas.

**Exit:** producer-owned versioned interfaces, matching consumer pins and
shared fixtures, plus a reviewed mapping that accounts for all relevant
Heimdall state. This is EC-01/04/06/12/13/14 work, not a replacement for them.

### OHS-04 Deliver the deterministic continuity experience

**Owner:** Odin. Reuse the newer continuity and memory implementation.

Build one project slice first. Its human view shows objective, owner, open
commitments, recent activity, last supported milestone, blockers, pending
decisions, next trigger, evidence age and source coverage. Provide a
portfolio view and a change-since-acknowledgement briefing. Preserve the
difference between delivery and explicit acknowledgement.

Serve agents bounded snapshots and exact evidence reads from those same
records. Include revisions, change cursors, omitted counts and explicit
unavailable states. Enforce portfolio/project scope at the read and command
boundaries, not through model instructions. Revalidate pages and prepared
decisions after relevant state or permission changes.

Keep provenance and verification separate. A worker report remains a
report; an inferred milestone carries its evidence and uncertainty.
Verification identifies the exact claim, artifact revision, check and
result. A passing check does not close an entire commitment by itself.
Saga's run state remains attributed to Saga.

**Exit:** shared fixtures demonstrate agreement between human and agent
views, restart-safe obligations, stale-page handling, scope denial, unknown
coverage, contradiction visibility and invalidation after correction or
revocation. Every displayed completion claim has a resolvable basis. These
are local component checks; real evidence reads depend on OHS-07.

### OHS-05 Complete the real runtime prerequisites

**Owner:** Odin for its service and harness; Saga for its own API and execution.

Close the remaining I0/I1 contract and fake-backend gaps, resolving affected
producer semantics rather than inventing wire contracts. Then implement
the first Claude Agent SDK path and workstation daemon under I2: dedicated
credential lineage, authenticated host identity, capability probes, tool
profile enforcement, limits, heartbeat, interruption, reconnect and
reconciliation of unknown outcomes. Refuse unsupported session classes.

Keep the fixture-only Pi control after I2 and the second production adapter
at I5 unless separately amended. Fable/Astra role labels do not establish
an available model route. Native children remain disabled until their
budget, authority and stop requirements are resolved and enforced.

After Saga provides Phase B evidence, pin its supported contract and run
the I3 governed-project proof: submission, refusal, approval, cursor replay,
stop, uncertain outcomes and reconciliation. Odin never substitutes local
history or a fake result for Saga's authoritative outcome.

**Exit:** separate receipts for local/fake behavior, real host/harness
enforcement and live Saga behavior. AC-29 remains a Saga-side check.
OHS-02 and synthetic OHS-04 work can continue while this package is gated.

### OHS-06 Prepare and rehearse the task migration

**Owners:** Heimdall for export/fencing; Odin for import and commitment writes.

Implement a preview and importer from the OHS-03 mapping. Preserve original
identity, revision, checkpoints, decision disposition, dependencies and
artifact pins. Handle owner/assignment/budget fields that Heimdall did not
have explicitly. Keep source claims attributed; imported checkpoints do
not become independent corroboration.

Use synthetic fixtures first. Rehearse the authorized real-data migration
in private disposable state, outside the repository. Report counts and
reference reconciliation, unmapped records and a receipt bound to the
source snapshot and mapping version. Partial failure must leave a safely
resumable or rolled-back import, never silent partial task authority.

Add enforceable Heimdall write fencing for migrated work and exercise every
writer path, including CLI, TUI, editor and agent interfaces. A retained
client may later forward commands to Odin; it must not retain a writable
task replica. No permanent two-way synchronization is introduced.

**Exit:** repeated import yields one result and receipt; changed input is
detected; references reconcile; post-fence writes cannot change task state.
Restore and abort procedures pass. Actual import remains I4/G-10 work;
the production freeze and switch occur under OHS-09. Implements proposed
AC-38 without declaring that scenario passed before its full evidence.

### OHS-07 Connect capture and surface feeds

**Owners:** Skald and Heimdall for reusable components; Odin for consumption.

Use Skald's public collector/sink boundary in the workstation capture
module, with a durable local spool, stable batch identity and atomic
checkpoint application. Maintain one writer per destination namespace.
Ingest historical archive changes incrementally with original identities
and revisions, and reconcile overlap with ongoing capture.

Keep Skald's local archive and browser usable when Odin is unavailable.
Define per-destination acknowledgements and visible backlog; one sink's
success must not advance another sink's checkpoint. Reconcile retries and
deduplicate by source identity/revision without promising exactly-once
delivery. Keep separate retention and redaction receipts for destinations.

Extract Heimdall observations from task, planner and actuation dependencies.
Start with source health and one useful surface observer, then expand.
Host loss produces stale/unknown coverage or `host_offline`, not failure
or completion of the underlying work. Desktop input stays gated separately.

Connect each accepted event to OHS-04 and provide exact session navigation
through a published Skald interface. Fixture a locator first if no suitable
interface exists; do not make an internal database path the public contract.
Keep archived activity and live session-host observations distinguishable.

**Exit:** producer/consumer tests cover duplicate and interrupted delivery,
outage/backfill, archive restore, source rewrite/removal, redaction and sink
failure. No selected record is silently lost; gaps are visible. Skald works
with Odin down and Odin retains obligations with Skald down. AC-18/26/37/41
evidence remains scoped to what each check exercises. Real integrations
follow the placements in the delivery table unless amended under OHS-01.

### OHS-08 Add interpretation only where it earns its cost

**Owner:** Odin planning and evaluation components.

After deterministic views work, add bounded interpretation of meaningful
changes: possible milestone advancement, emerging blockers, unresolved
decisions and conflicting priorities. Use the authorized portfolio view
for the coordinator and project scope for each planning owner or worker.

Require typed proposals with source revisions, uncertainty and affected
commitments. Service checks prevent an inference from granting authority,
accepting a decision or closing a commitment. Ordinary informational
updates need no approval ceremony; authoritative state transitions retain
their existing rules.

Keep explicit checkpoint/report commands usable without model extraction.
Run attention proposals in shadow mode with coalescing, expiry, quiet hours
and caps before enabling notifications under ADR-010. Compare against the
deterministic briefing using the same evidence and full cost accounting.

**Exit:** supported summaries help the operator resume work with fewer
corrections or less effort at an accepted cost. Unsupported claims remain
visible in evaluation; rejected or stale proposals cause no authoritative
mutation. Poor performance leaves the deterministic product usable.

### OHS-09 Run the pilot and complete cutover

**Owners:** Odin release engineering, each producer for its component,
operator for migration scope and final cutover.

Pilot one project, selected Claude Code and Codex sources, and the retained
Skald browser. Exercise interruption, a changed requirement, an unresolved
decision, source outage/recovery and a reported success whose verification
fails. Broaden only after the first project meets the acceptance below.

Use this cutover sequence:

1. Record the exact project/task scope, source selection, versions, backup
   location, responsible operator and rollback boundary. Verify restore.
2. Fence Heimdall writes for that scope and drain in-flight writes. Seal the
   export and source revision after the fence; keep the original read-only.
3. Import once, reconcile all in-scope records/references and inspect the
   prepared continuity view. Abort on unexplained loss or unmapped semantics.
4. Enable Odin's task writes and redirect supported clients. Verify that
   old Heimdall writer paths refuse edits. Keep source provenance and the
   import receipt accessible from the new records.
5. Observe the pilot period, then remove duplicate capture paths only after
   identity and coverage equivalence is demonstrated. Retire the migrated
   task writer, its scheduling/configuration and obsolete bridge work.
   Retain backups, required readers, useful sensors and Skald's browser.

Before Odin accepts new writes, rollback can disable its writer and restore
the original owner after reconciliation. After new Odin writes exist,
pause task writes and preserve them; repair forward or perform an explicitly
reviewed reverse migration. Restoring an old Heimdall database alone would
lose new work. Never run both writers for the same migrated scope.

**Exit:** a cutover receipt names the sole task writer, source/mapping
versions, reconciled counts, remaining unavailable capabilities and tested
recovery procedure. Unmigrated scope remains explicitly identified until
its own migration; it has no synchronization bridge to migrated tasks.

## Pilot acceptance and measures

Use component tests during implementation, producer/consumer tests at each
boundary, and a real operator pilot only after the applicable gates. Keep
real conversations, databases and credentials out of fixtures and Git.
The initial proposed pilot is five working days; agree final targets in
OHS-01 before judging results.

| Measure | Proposed acceptance |
|---|---|
| Obligation preservation | No in-scope open commitment, checkpoint or unresolved decision lost across migration, restart or view rebuild |
| Task authority | Exactly one permitted writer per migrated scope; every attempted legacy write visibly refused |
| Claim quality | No unqualified completion inferred from idle state, a conversation statement or an imported checkpoint |
| Source coverage | Every selected source shows its capture/processing position, freshness and unavailable or gap state |
| Update delay | Measure source-to-capture and capture-to-view separately; initial target is p95 at most 10 seconds from accepted structured event to view under normal operation |
| Evidence access | Every selected pilot claim opens its exact available evidence revision, or explains why it is unavailable |
| Human and agent agreement | Equivalent authorized reads report the same obligations and decision state; omissions and pagination are explicit |
| Resume effort | Compare time to identify the next useful action and repeated-context effort against the current Skald/Heimdall workflow |
| Independent operation | Skald browses and captures through an Odin outage; Odin preserves task state through a capture outage |
| Recovery and removal | Restore, retry, correction, access revocation and redaction checks leave no silent loss or stale authorized view |

The latency and pilot-duration targets are proposed product targets, not
measured capabilities. Required invariants do not become optional when a
usability or latency target is missed. Full runtime acceptance and Saga's
guarantees need their own evidence.

## First execution batch and deferred work

Start these bounded changes in priority order:

1. **Odin baseline:** review `a9f22a1`, reproduce its checks and reconcile the
   current branch with its ADRs and implementation status.
2. **Product decisions:** prepare the Skald-browser retention change,
   Heimdall EC-13 retirement record, Skald EC-14 publication plan and the
   narrow earlier-pilot decision. Record each in its owning repository.
3. **Current visibility:** reproduce the two Heimdall failures, verify the
   actual Skald source selection and produce a source-health inventory.
4. **Contracts:** agree one capture-change fixture and a complete task-state
   mapping, including dependency/decision semantics and unsupported cases.
5. **First demonstration:** drive the existing Odin continuity view with a
   synthetic source change, checkpoint, decision and outage, with matching
   human/agent reads and a scoped evidence locator.

Estimate calendar delivery after baseline checks, the first producer
contract review and the runtime probe. Track engineering work separately
from operator and producer waits; do not use speculative dates to bypass
those dependencies.

Defer the independent Heimdall planner, permanent task bridge, merged
Skald/Heimdall product, repository merger, universal adapter framework,
full archive semantic search/Braid integration, voice and desktop input.
Retain required existing safety and release work for components still in
use. Heimdall's recovery machinery and Skald's portable preservation can
continue independently where justified; they do not gate the synthetic
continuity demonstration.

## Source references

Portable Odin requirements:

- [ADR-006 through ADR-015](../DECISIONS.md#4-odin-decisions-odin-adr),
  especially task authority, capture, workstation placement and surfaces.
- [Roadmap gates and increments](../ROADMAP.md).
- [Cross-repository queue](ODIN-ECOSYSTEM-INTEGRATION.md#10-contract-first-cross-repository-work-queue),
  especially EC-04/06/12/13/14.
- [Migration contract](ODIN-IO-CONTRACT.md#14-migration) and
  [acceptance scenarios](ODIN-ACCEPTANCE-SCENARIOS.md).
- [Older consolidation proposal](CONSOLIDATION-PLAN.md), whose shared
  repository and Skald-TUI replacement proposals are not prerequisites here.

External local evidence inspected on 2026-10-19 is identified by checkout
and revision rather than made a dependency of this document's local links:

- `/home/david/.codex/worktrees/5402/odin` at `a9f22a1`:
  `docs/PRODUCT-IMPLEMENTATION-STATUS.md`, `docs/IMPLEMENTATION-STATUS.md`,
  `docs/design/ODIN-PRODUCT-IMPLEMENTATION-PLAN.md`, `docs/DECISIONS.md`
  ADR-020–023 and `python/odin/continuity.py`.
- `/home/david/Projects/heimdall` at `3ca80b5` with the local test change
  noted above: `docs/STATUS.md`, `docs/HEIMDALL-IMPLEMENTATION-ROADMAP.md`
  and `internal/session/service.go`.
- `/home/david/Projects/skald` at `22114dd`: `STATUS.md` and
  `SKALD-IMPLEMENTATION-PLAN.md`. Reconcile reported release tags against
  the selected consumer pin during OHS-03; historical status text is not
  proof of a currently compatible published contract.
- `/home/david/Work/odin-heimdall-skald-product-review-2026-10-17/report.txt`
  and `health-summary.json`: the earlier product review and diagnostic leads.
