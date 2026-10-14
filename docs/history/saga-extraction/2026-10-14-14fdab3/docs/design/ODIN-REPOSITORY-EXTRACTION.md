# Odin repository extraction plan

Date: 2026-10-14. Status: proposed documentation handoff, before implementation.
Source: the local Saga working tree. Destination: `~/Projects/odin`, a sibling
of `~/Projects/saga`; `/odin` below means that repository root, not an absolute
directory at the filesystem root.

Create a documentation-first Odin repository from an explicit snapshot of the
local design. Give every live specification one owner, preserve the joint
decision history, and carry pinned copies of the external contracts Odin needs.
Do not maintain two independently editable copies of the same specification.

This plan prepares the handoff; it does not perform it. Saga remains the current
document owner while the operator's revisions are in progress. The existing
[DECISIONS.md](../DECISIONS.md) remains authoritative until the handoff is recorded.

## 1. Separate the documentation handoff from runtime extraction

Three changes have different completion criteria:

1. **Documentation handoff:** Odin has a self-contained implementation brief,
   requirements, acceptance scenarios, provenance, and dependency contracts.
2. **Code extraction:** reviewed implementations and adapted personas enter the
   new repository in the planned increments.
3. **Deployment cutover:** the new service replaces the existing Odin session,
   with migration, recovery and admission checks satisfied.

Only the first is needed to start work from the new repository. It does not
require copying containers, credentials, journals, databases, or the existing
`saga/odin/` directory into the new root.

D14 currently creates the repository at Phase C. Record a narrow amendment when
executing this plan: a documentation scaffold may exist earlier; the first live
Odin deployment still depends on Saga Phase B. Offline contract work and a fake
backend do not establish production readiness.

## 2. Destination layout

Keep the existing Odin design filenames during the handoff so references and
review comments remain recognizable. Further document splitting can follow code
boundaries once they exist.

```text
odin/
  README.md                         product, current status, first implementation milestone
  AGENTS.md                         instructions for developers working on Odin
  CLAUDE.md                         short entry point to AGENTS.md and runtime-specific dev notes
  docs/
    README.md                       reading order and authority
    DECISIONS.md                    current Odin decisions and inherited decision mapping
    ROADMAP.md                      Odin work, with explicit Saga and peer dependencies
    design/
      ODIN-IO-CONTRACT.md
      ODIN-IMPLEMENTATION-BLUEPRINT.md
      ODIN-ECOSYSTEM-INTEGRATION.md
      ODIN-ACCEPTANCE-SCENARIOS.md
    contracts/
      README.md                     producer ownership, versions and update procedure
      saga/<snapshot-id>/           pinned consumer copy of Saga's contract
    provenance/
      EXTRACTION-MANIFEST.json       exact source bytes and transformation mapping
      DECISION-MAP.md                every inherited decision and its current owner
    history/
      saga-extraction/<snapshot-id>/ original selected documents, original relative paths
    research/
      HARNESS-LANDSCAPE-2026-10.md
      harness-research-2026-10/      dated evidence, outside normative reading order
```

The historical snapshot is frozen. Its contents establish what was inherited;
they never override current decisions. Preserve raw snapshot bytes, including
old links; record unresolved historical references in its wrapper index. Fix
links in the live documents instead of modifying the evidence snapshot.

## 3. Source to destination map

| Current Saga source | Odin destination and treatment | Saga after handoff |
|---|---|---|
| `docs/design/ODIN-IO-CONTRACT.md` | Same path; adapt authority and links; replace the producer API appendix with a reference to the pinned Saga contract | Short forwarding document at the original path |
| `docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md` | Same path; implementation overview and increment mapping | Forwarding document |
| `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | Same path; Odin consumer requirements and proposed peer work | Forwarding document; Saga work gets its own backlog entries |
| `docs/design/ODIN-ACCEPTANCE-SCENARIOS.md` | Same path; preserve AC, DC and evaluation identifiers | Forwarding document; producer-side checks referenced from Saga's contract tests |
| `docs/DECISIONS.md` | Exact historical snapshot plus an Odin-specific live `docs/DECISIONS.md` | Saga-specific live decisions plus the same frozen joint record |
| `docs/ROADMAP.md` | Exact historical snapshot; derive an Odin roadmap with dependency gates | Saga milestones and a cross-repository milestone mapping |
| `README.md`, root `CLAUDE.md` | Snapshot for provenance; write new Odin entry documents | Remain Saga's product and developer documentation |
| `docs/design/HARNESS-LANDSCAPE-2026-10.md` and its research directory | Dated research under `docs/research/`; preserve the internal directory relationship | Keep as historical Saga research, with Odin's current design linked separately |
| `odin/CLAUDE.md`, `odin/mimir/CLAUDE.md` | Historical persona inputs; select and adapt instructions when the integration package is built | Existing runtime personas remain in place until deployment cutover |
| `journal/JOURNAL-FORMAT.md`, `mqtt/TOPIC-SCHEMA.md` | Selected historical references if cited by the imported design | Canonical Saga transport/evidence formats until their replacements land |
| `docs/features/spec-development.md`, `odin-proactive-updates.md`, `voice-telegram.md` | Triage relevant requirements into Odin's backlog; copy only selected historical inputs | Mark disposition and retain history; old phase numbers do not become new commitments |
| `docs/saga-spec.md`, deployment/setup docs, Eir backlog, worker/auth scripts | Reference only where necessary; no wholesale import | Stay Saga-owned |

Forwarding documents are added only at the completed handoff. They identify the
new owner, destination path and extraction snapshot. While there is no remote,
use a sibling-checkout link plus the repository name and relative path; do not
invent a GitHub URL. These forwarding links are conveniences, not dependencies
required to read Odin's implementation specification.

## 4. Decision ownership and authority

Preserve legacy identifiers as `SAGA-2026-10-D0` through `SAGA-2026-10-D24` in
the provenance map. Existing D-number references resolve through that map; do
not silently renumber them. New decisions use repository-specific identifiers,
for example `ODIN-ADR-001` and `SAGA-ADR-001`.

| Legacy decisions | Treatment |
|---|---|
| D0, D1, D3, D6, D13–D16, D18, D24 | Split clauses by owner. Product scope, integration obligations, sequencing and authentication policy need explicit mappings in both repos; no new joint editable master |
| D2, D4, D5, D17 | Saga owns execution authority, its ledger, run states and delegations. Odin records the consumer obligations and pins the corresponding Saga contract |
| D7–D10, D19–D23 | Odin owns supervision, memory, review, evaluator policy, consumer integrations, topology, preservation and backend selection. Peer capabilities remain owned by their respective projects |
| D11, D12 | Saga owns Eir and Bragi. Odin owns its event, history and import interfaces to them |

For a split decision, map individual clauses, not just its title. For example,
D6's general side-effect requirement remains applicable to both services, but
each owns its delivery and recovery implementation. D24's planner authentication
belongs in Odin; worker credential provisioning belongs in Saga.

Each mapped clause records its source identifier, new owner and document,
status (locked/default/hypothesis/open), and any explicit supersession. Preserve
open questions as open. Moving a document does not approve its proposals or
resolve outstanding review findings.

Within Odin, establish one clear order: current decisions, operational contract,
implementation overview, roadmap. Acceptance scenarios must agree with the
decisions and contract; a conflict is an issue to resolve before claiming the
scenario passes. Research and historical snapshots are evidence, not policy.
Producer-owned interfaces remain governed by their pinned producer contract.

## 5. Extract the Saga contract at its producer

The current I/O contract embeds a Saga API appendix and worker protocol. Before
Odin implementation depends on them:

1. Establish `saga/docs/contracts/SAGA-SERVICE.md` as Saga's canonical contract.
   Extract the run/delegation/evidence API, identities and authorization rules,
   request and response semantics, event cursor, idempotency, stop semantics,
   verification responsibilities, and worker transport boundary. Carry known
   gaps explicitly; an endpoint list is not a complete executable contract.
2. Add schemas and compatibility fixtures alongside that contract as they are
   specified. Record their actual status; do not label proposed schemas as
   implemented or tested.
3. Copy a versioned snapshot into Odin's `docs/contracts/saga/<snapshot-id>/`,
   with producer path, digest and commit when available. Odin's adapter design
   references that snapshot and states its required capabilities.
4. Later changes originate in Saga, then update Odin's pinned snapshot and
   adapter compatibility checks together. Never edit the pinned copy as the
   source of a new Saga capability.

Use the same ownership rule for Herdr, Heimdall, Skald, Braid, WCU and dotprivate.
The ecosystem integration plan records requested capabilities and limitations;
it cannot establish that a peer has implemented an interface. A third shared
documentation repository or Git submodule is unnecessary for this handoff.

## 6. Capture local work without losing provenance

The local design includes untracked and modified files. `git archive HEAD`, a
remote clone, or a history-only extraction would omit the current design.
The recorded Saga HEAD at planning time is
`9e0282353796e88732ce8fc657bca702695ea49f`; it does not identify the design bytes.

At handoff, use an explicit file allowlist and a staging directory:

1. Record the actual Saga HEAD, capture time and selected paths. Include the
   five live design/decision inputs, roadmap, entry documents, selected legacy
   references and the research set specified above.
2. Hash each source file, copy its bytes into the staging snapshot, and hash
   both source and copy again. If a source changed during capture, discard that
   candidate and repeat after the edits settle. Do not combine revisions from
   an active editing pass into an allegedly final handoff.
3. Write `EXTRACTION-MANIFEST.json`: snapshot ID, source repository, base HEAD,
   captured time, dirty/untracked status per file, source path, source SHA-256,
   snapshot path, destination path, treatment (`exact`, `adapted`, `split`,
   `reference`), and adapted-output digest when applicable. The manifest is
   metadata; the frozen files provide the actual source bytes.
4. Create live Odin documents from the staged snapshot, never by rereading
   changing originals midway through the transformation. Record transformations
   and decision mappings. Include this plan in the handoff materials.

A local documentation checkpoint commit can simplify provenance, but is not a
prerequisite and does not require a push. A byte-addressed snapshot is sufficient
when the working tree must remain uncommitted. Do not stage unrelated Saga work.

Use a fresh local Odin repository with recorded provenance. A Git history split
is unnecessary for documentation bootstrap and would miss the current untracked
inputs. Revisit history preservation for selected code during code extraction.

## 7. Write Odin developer instructions separately from its persona

Root `AGENTS.md` describes how to develop the service: architecture, authority
order, validation commands as they become available, runtime adapter contracts,
credential handling, and the distinction between fake-backend checks and live
Saga execution. Root `CLAUDE.md` points to those shared instructions and contains
only Claude-specific development notes.

The existing `saga/odin/CLAUDE.md` describes how the deployed orchestration agent
behaves. It must not become the new repository's root developer instructions.
When code extraction starts, derive runtime personas and skills into the actual
integration package, removing obsolete filesystem mailboxes and deployment
assumptions. Mimir's persona likewise belongs to the review integration.

Do not copy authentication caches, `.env` files, active logs, raw conversations,
workspaces, databases or deployment secrets. Use synthetic fixtures for initial
acceptance work. Selected real history enters only through a separate, scoped
runtime migration. Keep existing attribution and unresolved licensing questions
with imported research and design references; do not imply a new license grant.

## 8. Handoff sequence and completion checks

1. Finish the current document corrections in Saga and record remaining issues.
2. Capture and verify the local snapshot; produce the manifest and decision map.
3. Create the Odin scaffold, adapt its live documents, and extract the Saga-owned
   service contract into Saga. Existing live deployment remains unchanged.
4. Validate the candidate Odin checkout on its own, without a Saga sibling:
   all required live-document links resolve; pinned contracts and historical
   decision evidence are present; external capabilities have explicit status.
5. Check every D0–D24 clause has a destination or recorded historical disposition;
   AC/DC/EC identifiers survive; phase A–G and increment I0–I7 mappings agree;
   unresolved questions and review findings have not disappeared.
6. Verify snapshot hashes, inspect the exact new-file allowlist, and check for
   accidental private material. No source deletion is needed to validate Odin.
7. Record the authority handoff in both repositories. Replace Saga's four live
   Odin design documents with forwarding documents, update its index and narrow
   its decisions/roadmap. Record Odin's dependency snapshot and the handoff ID.
   If interrupted, resume from the manifest; never overwrite newer files blindly.
8. If creating local checkpoint commits, record both commit IDs in the handoff
   receipt. A remote repository, push, or publication is a separate operation.

Implementation can begin from Odin when a developer can identify the current
requirements, the first increment, the dependency gates, and the acceptance
criteria from that checkout alone. Keep the first task small: service records,
event processing and fake-backend recovery, followed by the first supported
runtime adapter and the live Saga integration at the agreed phase boundary.
