# Odin documentation

Reading order, authority and status for every document in this
repository. This checkout is a **documentation-first scaffold**
(D14.3) plus the I0 substrate (`substrate/`, 2026-10-16): the event
envelope, record schemas and fixture set with their Go and Python
validators, non-production and fixture-only. No service, store or
backend code exists.

## Handoff state

These documents are a candidate handoff from Saga (extraction snapshot
`2026-10-14-14fdab3`). The handoff is **not recorded**. The D14 gate
(contract held one review cycle, Saga producer contract extracted, decision
map written) is under independent review. The source review returned
CHANGES_REQUIRED; its corrections are applied as recorded in
`DECISIONS.md` §6 and [`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md),
and the re-review is pending. Until it is recorded in both
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

- [`design/ODIN-ACCEPTANCE-SCENARIOS.md`](design/ODIN-ACCEPTANCE-SCENARIOS.md):
  AC-01 to AC-41 (AC-37 to AC-41 proposed), DC-01 to DC-08 and the
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
| [`provenance/SOURCE-REVIEW.md`](provenance/SOURCE-REVIEW.md) | The source contract review (CHANGES_REQUIRED); the state of each finding is in `DECISIONS.md` §6 |
| [`provenance/REVIEW-RESOLUTIONS.md`](provenance/REVIEW-RESOLUTIONS.md) | How each review finding (B1–B7, N1–N11, G1–G7) was resolved against existing decisions, with evidence, and what remains open |
| [`provenance/HISTORICAL-LINKS.md`](provenance/HISTORICAL-LINKS.md) | Complete inventory of unresolved links in frozen and research evidence |
| [`provenance/EXTRACTION-MANIFEST.json`](provenance/EXTRACTION-MANIFEST.json) | Source paths, commit and SHA-256 digests of the 35 captured files |
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
- `X-n`: issues raised by the extraction, X-1 to X-14 (`DECISIONS.md`
  §5); `B1`–`B7`, `N1`–`N11`, `G1`–`G7`: source review findings
  (`DECISIONS.md` §6).
- `I0`–`I7`: blueprint increments; phases `A`–`G`: D15; the mapping
  between them is I/O contract §13.
- `AC-nn`, `DC-nn`: acceptance scenarios (AC-01 to AC-41, with AC-37
  to AC-41 proposed; DC-01 to DC-08); `EC-nn`: ecosystem work items
  (EC-01 to EC-16);
  `B-nn`: required Saga capabilities (I/O contract Appendix B);
  `L-xx-n`: legacy triage entries; `G-n`: roadmap gates.

## Validation

Run `python3 scripts/validate_docs.py` from the repository root for
metadata, hash, identifier and link checks. These checks pass for the
bootstrap; no runtime test or final semantic review is claimed. See
[the bootstrap receipt](provenance/HANDOFF.md).
