# Opus source-contract review

**Verdict: CHANGES_REQUIRED**

v7 has one consistent execution model (a supervisory layer over the Agent SDK), so it no longer mixes in the old custom-runtime design. The records, the outbox and the recovery protocol agree with D4 and D6. All of D0–D24 is assigned in the plan's §4 table, and the EC IDs are consistent. D14 (`DECISIONS.md:557-571`) already allows the early scaffold. But seven contradictions would carry into the producer contract or fail the plan's own completion checks. All seven are text fixes. This was a document read only; nothing was run, and no links or sibling repos were checked.

## Blocking contradictions

**B1. Three different authority orders.**
- The contract says the blueprint wins over it when they conflict (`ODIN-IO-CONTRACT.md:23-25`).
- The blueprint reads itself first and treats the contract as "existing detailed design" (`ODIN-IMPLEMENTATION-BLUEPRINT.md:9-16`).
- The extraction plan says: decisions, then the contract, then the blueprint (`ODIN-REPOSITORY-EXTRACTION.md:122-126`).
- This matters now because the contract and the blueprint disagree on substance (see B2).
- *Fix:* adopt the plan's order. In the contract, replace lines 23-25 with "the decision record wins; the blueprint is an overview corrected to match this contract". Reorder the blueprint's §1 to DECISIONS, contract, blueprint, integration plan, acceptance scenarios.

**B2. The phase-to-increment mappings disagree, which fails the plan's check at `EXTRACTION.md:216`.**
- **Herdr:** the contract puts Herdr inspection in Phase C (I2/I3) (`CONTRACT.md:680`). The blueprint puts the Herdr adapter in I4 (`BLUEPRINT.md:223`).
- **Braid and Skald:** the contract puts them in Phase F/I6 (`:683`), and so does D15 (`DECISIONS.md:582`). The blueprint puts the Braid/Skald history adapter in I5 and Skald enrollment in I4 (`BLUEPRINT.md:223-224`).
- **I0/I1:** the contract lists them in the Phase B row next to Saga deliverables (`:679`). The blueprint lets I0–I2 run against a fake backend (`BLUEPRINT.md:228`). D15 (`:585`) and CLAUDE.md say "Phase B precedes C" / "do not start C before B". D14 only gates cutover on B.
- *Fix:*
  - Split contract §13 into two columns: Saga phase gate and Odin increment.
  - State once, in D15 next to D14, that I0–I2 may run against a fake backend during Phase B and that I3 requires B's exit criteria.
  - Put read-only Herdr inspection in I3, as D20's first configuration describes, and adopt/takeover in I4.
  - Move Braid recall and Skald archive/enrollment to I6, or amend D15 and D10.

**B3. Run admission does not bind the launch configuration.**
- D2 binds the PRD, the launch configuration, the verdict and the approval by hash (`DECISIONS.md:256-260`), and CLAUDE.md constraint 1 says the same.
- `submit_run` (`CONTRACT.md:292`) and `POST /runs` (`:832`) only check the PRD digest against an approval. Nothing says how one plan-level approval covers each run's artifacts.
- *Fix:*
  - Change the call to `submit_run(request_id, prd_digest, launch_config_digest, verdict_id, approval_id)`.
  - Saga refuses unless the approval's `proposal_digest` covers a manifest that lists both digests for this request id, and the verdict is bound to the same request id and digests.

**B4. Every piece of guidance requires a verdict, which contradicts D8.**
- `publish_guidance` "requires an approved `guidance` verdict or `APPROVE_UNCHANGED` semantics" (`:294`), and Appendix B says guidance is "verdict-bound" (`:834`).
- D8 reviews only guidance that "materially changes" a worker's approach and uses mechanical checks for routine operations (`DECISIONS.md:407-412`).
- "`APPROVE_UNCHANGED` semantics" is not something Saga can check.
- *Fix:* each guidance message carries a declared class (`routine` or `material`), with a mechanical definition of `material` (for example, it changes scope, the output contract or the criteria). Saga requires a verdict only when the delegation's policy says material guidance needs review.

**B5. Odin's outbox publishes to MQTT, which crosses the Saga boundary.**
- The outbox lists MQTT retained publish of guidance and answers as its own destination (`:462`), and `emit_event` publishes to `saga/events/<kind>` (`:297`).
- This conflicts with D1 (Odin reaches Saga only through the API), with the §10 ACL that lets only Saga events write `guidance` and `answers/#` (`:516-519`), and with CLAUDE.md ("MQTT is Saga's dependency, not Odin's").
- AC-28 (`ACCEPTANCE-SCENARIOS.md:82`) has Odin reconcile by reading the retained MQTT value. `GET /operations` (`:844`) has no `superseded` result, so in the target design Odin has no way to learn of supersession.
- *Fix:*
  - Label the MQTT row as shadow-period only.
  - Make guidance supersession a Saga rule: guidance carries `expected_guidance_rev`, and `GET /operations` can return `superseded`.
  - Move AC-28 to Saga's producer tests, with an Odin-side counterpart that reconciles through the API.
  - Map `emit_event` to an API endpoint, or drop it.

**B6. The submission request ID is created in two places.**
- `stage_run` "assigns the request id" (`:291`), and D2 binds the verdict to that request ID before submission (`DECISIONS.md:258`).
- §9 says the operation ID is a ULID minted "in the transaction that decided it" and is the same value as the request ID (`:427-433`).
- The Appendix A example uses a non-ULID, `muninn-stream1-20261014T0900Z-a1b2` (`:755`).
- *Fix:* `stage_run` mints a ULID request ID, and that value becomes the submission's operation ID; retries reuse it. Correct the example. State that a restart mints a new ID and say which bindings must then be renewed (see G3).

**B7. The `shell` tool can expose credentials to Odin's turns.**
- `shell(cmd)` runs "inside Odin's environment" (`:307`), and every tool result is logged (`:277`).
- The planner profile (`:336`), `:649-651` and D2 (`DECISIONS.md:272-274`) require that the reviewer key, the Saga token and the model credential never reach turns or the history.
- *Fix:* run `shell` in the planner's sandbox, never in the service process. Deny environment variables, `/proc` and credential paths. Redact tool output before logging. Or drop `shell` from v1.

## Non-blocking corrections

1. `EXTRACTION.md:32-35`: as you noted, the D14 amendment instruction is stale. Replace it with a pointer to D14. Separately, D14's gate ("held for one review cycle") is not met while this review is CHANGES_REQUIRED.
2. Several provenance notes are stale: "untracked" or "uncommitted" at `CONTRACT.md:9-12`, `BLUEPRINT.md:236-237` and `INTEGRATION.md:19`, and HEAD `9e02823` at `EXTRACTION.md:155-158`. At session start the tree was clean at `14fdab3`. The snapshot procedure itself still works.
3. D16 says the contract is v4 (`DECISIONS.md:596`).
4. Cross-references in DECISIONS point to old contract sections:
   - "contract §1" (`:161`) is now §3.
   - "contract §5" (`:163`, `:984`) is now §6.
   - "contract §3" (`:707`) is now §4.
   - D9's "also named in the blueprint" (`:463-464`) no longer holds.
5. The contract header gives the range AC-01–AC-26 (`:20`), but AC-27–AC-30 exist and are cited. Appendix D (`:863-869`) leaves them out.
6. The Effect states in §2 (`:86`) omit `held`, `cancelled_stale` and `superseded`.
7. D10's Braid row still says "never indexes the chat log" (`:494`). The decision text in §2 and contract §6 settled this as "active chat" plus a Skald `archive` scope, but `INTEGRATION.md:184-186` and EC-07 still say it needs clarification. Align all three.
8. D24 is marked locked, but open decision 12 (`:987-989`) and contract §15 (`:720-722`) still call the `api` default "proposed". The decision map should record it as "default, pending confirmation".
9. Requests to Eir go three different ways: `write_file` (`:615`), the Gitea outbox (`:463`) and `POST /tasks` (`:846`, D3). Use `POST /tasks`.
10. Peer contracts:
    - Plan §5 applies the producer-contract rule to every peer (`EXTRACTION.md:148`), but the layout only has `contracts/saga/` (`:57-59`).
    - The integration plan's `../../../<peer>/` links will fail the standalone check in plan §8 step 4.
    - *Fix:* mark peer links as non-required evidence, or add pinned peer contracts.
11. Minor:
    - The run state is `limit-paused` in D5 and `limit_paused` in Appendix C.
    - The planner profile allows WebFetch, but its network column doesn't include it (`:336`).
    - Legacy paths `dvergr-workspaces` and `.dvergr/requests` remain (`:306`, `:523`).

## Implementation gaps to carry forward

These can stay open, but they should appear as explicit gaps in `SAGA-SERVICE.md` and Odin's roadmap.

- **G1. Operator identity at Saga.** Approvals claim a "verified operator identity" (`:83`), and `POST /approvals` and the answer endpoint exist (`:839-842`). Mimir has a key, but the operator doesn't. Nothing says how Saga tells an operator's approval or answer apart from one sent by Odin's service or the CLI.
- **G2. Stop is split across two services.** It's unspecified which of D2's four stop operations `POST /stop` performs (`:845`) and which are Odin's (`:818`). It's also unclear what the kill switch does when Odin is down.
- **G3. Restarts and review cost.** Because D2 binds verdicts to the request ID, a restart ("new submission", `:293`) needs a new verdict or a manifest-covered approval. The review-cost consequence is unstated.
- **G4. Saga's validator as a dependency.** `stage_run` reuses "the same validation module Saga's launcher uses" (`:291`). That is a code dependency across repos, so it needs a published schema.
- **G5. Planner answers.** For `answer_request` (`:296`), Saga can enforce only the request kind and the delegation's permission, not "does not change the plan".
- **G6. Unconfirmed integrations.** Herdr's API is unreviewed, Skald retrieval is unfinished, dotprivate's selected-files contract is still a proposal, and the Heimdall projection doesn't exist yet. The documents already label these correctly.
- **G7. Unsettled defaults.** The billing re-test is pending. The Console spend cap doesn't apply under a subscription login. The caps and the coalescing window are guesses. The memory baseline is not chosen.

**Recommendation:** fix B1–B7 and non-blocking items 1–8 in Saga first (plan §8 step 1), then rerun this review as D14's review cycle. G1–G7 can carry forward as recorded gaps.
