# Odin documentation

Reading order, authority and status for every document in this
repository. This checkout now includes a **partial I0 contract
implementation**: shared schemas and fixtures with Go/Python validators
and pure state checks ([runtime guide](../runtime/README.md)). The Odin
local Python service foundation exists against a fake Saga backend; the workstation daemon and live adapters are not implemented.

## Handoff state

These documents are a candidate handoff from Saga (extraction snapshot
`2026-10-14-14fdab3`). The handoff is **not recorded**. The D14 gate
(contract held one review cycle, Saga producer contract extracted, decision
map written) is awaiting formal independent re-review. The retained source
review returned CHANGES_REQUIRED; `DECISIONS.md` §6 summarizes draft
dispositions and [`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md)
maps findings to current clauses, evidence and remaining work. That map is
not a retained independent approval. The re-review is pending. Until the
handoff is recorded in both
repositories, Saga's decision record remains the document owner, and
these documents must agree with the frozen record except for explicitly
recorded operator decisions in Odin's ADRs. These do not amend Saga-owned
interfaces or close the handoff. The I0–I2 sequencing interpretation
still awaits reconciliation with Saga (X-1).

On 2026-10-16, ODIN-ADR-006 to 015 supersede or amend inherited clauses
that Odin owns, for the first time. The carried text of each affected
decision stays verbatim, with an ownership note pointing to the ADR;
Saga-owned clauses are untouched. The conditional ADRs (016 to 019) are
drafts in the [consolidation plan](design/CONSOLIDATION-PLAN.md) and are
not in effect until Saga's record decides the parts it owns (X-14).

## Reading order and authority

Read in this order. Where two disagree, the earlier one wins.

| # | Document | Role |
|---|---|---|
| 1 | [`DECISIONS.md`](DECISIONS.md) | Current decisions: inherited `SAGA-2026-10-Dn` decisions as they apply to Odin, open questions, issues raised by the extraction, and local `ODIN-ADR`s |
| 2 | [`design/ODIN-IO-CONTRACT.md`](design/ODIN-IO-CONTRACT.md) | The operational contract: records, history, events and routing, sessions, tools, profiles, memory, durability and recovery, peer protocols, runtime adapter, required Saga capabilities |
| 3 | [`design/ODIN-IMPLEMENTATION-BLUEPRINT.md`](design/ODIN-IMPLEMENTATION-BLUEPRINT.md) | Implementation overview: product boundary, component ownership, invariants, increments I0 to I7 |
| 4 | [`ROADMAP.md`](ROADMAP.md) | Progress against phases A to G and increments I0 to I7, with dependency gates |

Alongside them:

- [Fable executive pilot](EXECUTIVE-PILOT.md): native Claude Code Remote
  Control launcher, dedicated login, scoped Odin tools and live acceptance
  checklist under ADR-024. Authentication and remote dialogue remain unverified.
- [Consolidated implementation status](CONSOLIDATED-IMPLEMENTATION-STATUS.md):
  first Odin delivery under the three-repository work plan, with exact local
  evidence reads, continuity checks, a synthetic demonstration and peer
  dependencies kept explicit.
- [Web app handoff](design/WEB-APP-HANDOFF.md) (operator input, verbatim),
  [web app work plan](design/WEB-APP-WORKPLAN.md),
  [library choice](design/WEB-APP-LIBRARIES.md), the
  [browser projection draft](design/WEB-APP-PROJECTION.md) and the
  [pass 4 brief](design/WEB-APP-PASS-4-BRIEF.md): ODIN-ADR-037's
  primary human view and agent tree, its dependency-ordered packages with
  acceptance and enforcement checks, the frontend library comparison, and a
  DRAFT (not adopted) snapshot and update-event shape, and the operator's
  direction for pass 4 (dark default, live reference-style tree, token usage
  instead of cost, verification rules). Only a synthetic
  prototype exists in [`web/`](../web/README.md).
- [Odin Heimdall and Skald consolidated work plan](design/ODIN-HEIMDALL-SKALD-WORK-PLAN.md):
  proposed delivery sequence for task-authority migration, shared capture,
  retained Skald browsing and one continuity experience. It identifies the
  selected implementation baseline and preserves producer ownership and
  existing live gates.
- [`PRODUCT-IMPLEMENTATION-STATUS.md`](PRODUCT-IMPLEMENTATION-STATUS.md):
  current product-plan execution, commands, regression evidence and remaining
  operator/producer dependencies; ODIN-ADR-023 records its local scope.
- [`design/ODIN-PRODUCT-IMPLEMENTATION-PLAN.md`](design/ODIN-PRODUCT-IMPLEMENTATION-PLAN.md):
  product implementation plan, prioritizing resume, prepared decisions,
  memory provenance and then governed orchestration. Its execution status
  distinguishes local evidence from live capabilities and remaining gates.
- [`design/ODIN-ACCEPTANCE-SCENARIOS.md`](design/ODIN-ACCEPTANCE-SCENARIOS.md):
  AC-01 to AC-57 (AC-37 to AC-57 proposed), DC-01 to DC-08 and the
  evaluation design. It must agree with documents 1 and 2; a conflict
  is resolved before a scenario is claimed to pass.
- [`design/ODIN-ECOSYSTEM-INTEGRATION.md`](design/ODIN-ECOSYSTEM-INTEGRATION.md):
  proposed peer work EC-01 to EC-16. It records requests and observed
  limits and cannot establish that a peer has implemented anything.
- [`contracts/`](contracts/README.md): pinned copies of producer
  contracts. Producer-owned interfaces are governed by these, not by
  Odin's documents. Saga's copy is a pinned draft whose target API is
  unimplemented.

## Provenance and evidence (not policy)

| Document | Content |
|---|---|
| [`provenance/DECISION-MAP.md`](provenance/DECISION-MAP.md) | Every D0–D24 clause, §5 open question and non-decision section: owner, Odin location, status, supersession |
| [`provenance/LEGACY-REQUIREMENTS.md`](provenance/LEGACY-REQUIREMENTS.md) | Triage of legacy features and personas into carried, superseded, Saga-owned, persona input, backlog or needs-decision |
| [`provenance/HANDOFF.md`](provenance/HANDOFF.md) | Handoff receipt and its state |
| [`provenance/OPTCHAT-CACHE-REVIEW.md`](provenance/OPTCHAT-CACHE-REVIEW.md) | Pinned gist cache-fix inspection, arithmetic check, Odin applicability and remaining compactor-context question |
| [`provenance/SOURCE-REVIEW.md`](provenance/SOURCE-REVIEW.md) | Retained source contract review (CHANGES_REQUIRED); `DECISIONS.md` §6 summarizes current draft dispositions |
| [`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md) | Current finding-to-clause trace for B1–B7, N1–N11 and G1–G7, plus F1–F9 audit correction targets and remaining checks; not an independent re-review report |
| [`provenance/HISTORICAL-LINKS.md`](provenance/HISTORICAL-LINKS.md) | Complete inventory of unresolved links in frozen and research evidence |
| [`provenance/EXTRACTION-MANIFEST.json`](provenance/EXTRACTION-MANIFEST.json) | Source paths, commit and SHA-256 digests of the 35 captured files |
| [`provenance/STABLE-IDS.json`](provenance/STABLE-IDS.json) | Schema-validated registry of active and withdrawn AC/DC/EC identifiers; each requires one defining row in its canonical document |
| [`history/saga-extraction/README.md`](history/saga-extraction/README.md) | The frozen snapshot's index, source-to-destination map, unresolved historical links, and the [extraction plan](history/saga-extraction/2026-10-14-14fdab3/docs/design/ODIN-REPOSITORY-EXTRACTION.md) that governed this handoff |
| [`design/CONSOLIDATION-PLAN.md`](design/CONSOLIDATION-PLAN.md) and [`research/consolidation-2026-10/`](research/consolidation-2026-10/README.md) | **Proposal, not recorded (2026-10-16):** consolidation of the agent-runtime repositories into one repository with three deployables, with its four investigation reports; it names the ADRs that would record it and whose record each belongs to. ODIN-ADR-006 to 015 are recorded from it; drafts 016 to 019 and every Saga-side part remain proposals (X-14) |
| [`research/HARNESS-LANDSCAPE-2026-10.md`](research/HARNESS-LANDSCAPE-2026-10.md) and [`research/harness-research-2026-10/`](research/harness-research-2026-10/README.md) | Dated research (2026-10-13/14); some internal links point into Saga's tree and are explained in the research README |

The frozen snapshot under `history/` and the manifest's source identities
and source hashes are immutable. When live adapted outputs change, update
their destination digests and transformation notes as required by `AGENTS.md`.

## Identifiers

- `Dn` = `SAGA-2026-10-Dn`; clause numbers such as `D24.8a` are defined
  in the decision map. New Odin decisions: `ODIN-ADR-nnn`; ODIN-ADR-001
  to 015 are recorded, and 016 to 019 are drafts, not in effect.
- `X-n`: issues raised by the extraction, X-1 to X-15 (`DECISIONS.md`
  §5); `B1`–`B7`, `N1`–`N11`, `G1`–`G7`: source review findings
  (`DECISIONS.md` §6).
- `I0`–`I7`: blueprint increments; phases `A`–`G`: D15; the mapping
  between them is I/O contract §13.
- `AC-nn`, `DC-nn`: acceptance scenarios (AC-01 to AC-50, with AC-37
  to AC-41 proposed; DC-01 to DC-08); `EC-nn`: ecosystem work items
  (EC-01 to EC-16);
  `B-nn`: required Saga capabilities (I/O contract Appendix B);
  `L-xx-n`: legacy triage entries; `G-n`: roadmap gates.

## Validation

Run `python3 scripts/validate_docs.py` from the repository root for
metadata, hash, identifier and link checks. The 2026-10-16 audit correction
pass also passes all 11 validator regression tests; commands and coverage
are in [AGENTS.md](../AGENTS.md#8-validation). No runtime test or final
semantic review is claimed. See
[the bootstrap receipt](provenance/HANDOFF.md).
