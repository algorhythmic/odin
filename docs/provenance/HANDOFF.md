# Odin documentation bootstrap receipt

Status: **bootstrap complete; formal documentation ownership handoff pending**.

Source: Saga commit `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada`, captured from a clean tree as snapshot `2026-10-14-14fdab3`. All 35 allowlisted source files are preserved byte-for-byte in both repositories. Odin is a new local documentation-first repository, with no remote or runtime implementation.

The user clarified that the immediate objective was moving the documentation into a new repository to start Odin. Further design-review rounds were stopped. Saga retains its original authoritative decisions and four live Odin design documents. Odin's adapted copies and extracted producer contract are development drafts; their recorded clarifications do not amend Saga's decisions. This bootstrap approves no unresolved policy or new interface.

The Opus source review returned CHANGES_REQUIRED and is retained in `SOURCE-REVIEW.md`. Subsequent author passes addressed many findings, but no final independent PASS is claimed. D14's formal ownership-transfer gate remains pending. The decision maps describe intended ownership after that future handoff. Do not replace Saga's live documents with forwarders until the gate is explicitly closed.

Validation covers the frozen-byte hashes, extraction metadata, pinned contract digest, preserved decision/acceptance identifiers, and local documentation links. A standalone copy is checked without a Saga sibling. These are documentation checks, not runtime acceptance tests. Runtime implementation, code extraction and deployment were not performed.

The proposed development start is I0 contracts and synthetic fixtures, then fake-backend foundations. Allowing I0–I2 alongside Phase B is Odin's interpretation; producer reconciliation remains open (X-1). Live Saga integration remains gated on Saga Phase B. Unresolved operator questions, third-party reuse terms, producer wire details and peer capability gaps remain open. The project-license choice is settled by ODIN-ADR-001.

The initial local Odin checkpoint is `cb55ecc` (documentation bootstrap).
No push or publication is part of this bootstrap.

Validation completed: standalone Odin checkout passed; all 35 frozen snapshot pairs match their source SHA-256 digests; pinned Saga bytes match the canonical draft; local link checks passed. No runtime tests were run.

Saga producer checkpoint: `a84f9ac28a6b4de651fccc057d33a335472f9773` on `docs/odin-extraction-2026-10`. Odin’s initial checkpoint is the commit containing this receipt; the two concrete IDs are also recorded in the local orchestration receipt.

## Operator-directed corrections — 2026-10-14

This follow-up corrects the live documentation, not the frozen source:

- Removed the false claim that Saga recorded Odin's fake-backend sequencing
  interpretation. X-1 remains open; I3/live execution still requires Phase B.
- Recorded the existing Apache-2.0 default (dotprivate MIT), added Odin's
  license, and separated third-party UniiChat permission/attribution.
- Recorded typed journal attention outcomes, no immediate wake for
  `no_attention`, bounded digest deadlines and explicit fallback (ADR-002;
  proposed runtime acceptance scenarios AC-31 and AC-32).
- Specified equal fixture retrieval for the I5 memory comparison and a
  repeated live-retrieval comparison after I6 (ADR-003).
- Reconciled pin status with `SNAPSHOT.json`: producer commit is recorded;
  SHA-256 `5ad4871d27e47a0842479c5e6e4335f7a68b8435676b8da97a949ed6afc9511e`
  matches both the pinned contract and Saga's canonical draft.

The roadmap's earlier Codex adapter experiment is explicitly a proposal;
the full second adapter remains I5. The handoff remains pending, the
producer API remains unimplemented, and this pass claims no independent
approval or runtime acceptance result. No Saga or peer files are changed.

Verification: `python3 scripts/validate_docs.py` passes for all 35 frozen
files, source and adapted-output hashes, inherited identifiers, the producer
pin and local links. `git diff --check` passes. Frozen history, dated research,
the producer snapshot and manifest source identities/hashes are unchanged.
The new routing scenarios remain specifications; no runtime tests were run.

## Routing and Haiku follow-up — 2026-10-14

The operator supplied further analysis of Jev routing and Haiku compaction.
ODIN-ADR-004–005 carry the resulting defaults and experiments: retain four
evaluator hooks, conservative journal deferral, explicit operator targets,
stable session-class models, a compactor effort sweep and whole-request
token accounting. AC-33–AC-36 specify checks; the roadmap assigns them to
I2/I3/I6 without moving the runtime integration phases.

Anthropic effort/pricing/migration/caching documentation and TypeSafe's
confidence/limitations pages were checked; sources are linked in the I/O
contract. The gist was unavailable through the web reader, so its reported
cache fix remains an explicit revision-inspection prerequisite before reuse.
`high` is a trial setting, not a vendor-mandated or measured optimum. No
classifier activation, runtime result or formal ownership transfer is claimed.

## Gist cache inspection — 2026-10-15

GitHub's public API supplied the revision history and author comment after
the web reader failed. Inspection of corrected revision `3c190e0` against
`f51fe5c` is complete; [the report](OPTCHAT-CACHE-REVIEW.md) records exact
hashes, changes and an isolated arithmetic check. The contract now spells
out the corrected pair priority and distinguishes projection regeneration
from reselecting a view. Implementation/cache regression tests remain I2
work. X-10 records the compactor-context gap; no policy is silently chosen.

## Consolidation direction recorded — 2026-10-16

The operator reviewed the harness-landscape tradeoffs, the delineation of
the agent-runtime tools (saga, standalone heimdall, skald, braid,
wayland-computer-use, dotprivate) and the runtime topology, judged the
consolidation direction correct, and asked for an implementation plan and
then for the design documents to be revised under it.

Evidence: four investigation reports written on 2026-10-16 by research
agents from read-only inspection of the local checkouts
(`docs/research/consolidation-2026-10/`). Plan:
`docs/design/CONSOLIDATION-PLAN.md`, a proposal whose Odin-owned parts are
now recorded and whose Saga-owned parts are not.

Recorded: ODIN-ADR-006 to 015 in `DECISIONS.md` §4 (event substrate with
namespaces; commitment record as single task authority; I0 narrowed;
workstation daemon and session host; operator surfaces, new inbound
sources and attention prompts; desktop input as a gated capability;
preservation without dotprivate; two reviewer positions with service-run
consensus, as a hypothesis; session-class decisions recorded; early Pi RPC
fixture-only control). These are the first Odin ADRs to supersede or amend
inherited clauses Odin owns (D8.5, D10.1, D10.2, D10.4, D10.5, D20.5 in
part, D20.8, D20.10, D22.3, D22.5, D24.3 for Odin's classes, and the
timing of D15.Eb). The carried text under each `Dn` heading is
unchanged; ownership notes point to the ADRs, and `DECISION-MAP.md`
carries the same supersessions with a new summary table. Issues X-11 to
X-14 opened.

Not recorded, by design: anything that touches a Saga-owned clause. The
execution backend stays Saga in its own process; worker events never reach
the Odin service; Bragi and Eir do not move; no repository is shared or
imported; no deliverable is named (X-5). These wait on decisions the
operator records in Saga's repository, a new contract version and a repin
(X-14). Drafts ADR-016 to 019 live in the plan and in
`research/consolidation-2026-10/decision-record-impact.md` and are labelled
not in effect.

Documents revised in authority order: the I/O contract (§1 to §11, §13 to
§15, Appendices A, C and D; Appendix B unchanged except one note),
blueprint, roadmap (gates G-9 to G-11 added), acceptance scenarios (AC-37
to AC-41 proposed; AC-20 withdrawn with its identifier kept; AC-19, AC-22,
AC-24, AC-25 re-scoped), ecosystem plan (EC-13 to EC-16 added; EC-05,
EC-08, EC-09 withdrawn with identifiers kept; a labelled section for the
Saga-side proposals), legacy triage (L-PU-1, L-VT-1, L-VT-2), README,
AGENTS.md, `docs/README.md`, `docs/contracts/README.md`. Manifest digests
and transformation notes updated last for every manifest output touched;
source identities and hashes unchanged.

Baseline: the 2026-10-14 pass (ADR-001 to 005, AC-31 to AC-36) and the
Apache-2.0 `LICENSE` were committed on 2026-10-16 (`c3c4ba2` adds the
license, `f621831` records ADR-001 to 005) before this pass's edits began, so the exception clause
("except for explicitly recorded operator decisions in Odin's ADRs")
exists at HEAD before the first supersession recorded under it. This pass
is the next commit.

Verification: `python3 scripts/validate_docs.py` passes; an independent
verification read compared the revised documents with the ADRs and the
frozen copy (its report is in the session scratchpad, not the repository).
No runtime exists; nothing is implemented or tested. No Saga or peer
repository file was changed.
