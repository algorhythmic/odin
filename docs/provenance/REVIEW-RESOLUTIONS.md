# Review findings and current evidence

The retained [source review](SOURCE-REVIEW.md) returned **CHANGES_REQUIRED**.
This is a trace from its findings to current draft clauses, not a retained
independent re-review or an approval. The clauses show how Odin's documents
address the findings; they do not prove runtime behavior or amend Saga's
producer-owned interface. The formal D14 re-review and handoff remain pending
([receipt](HANDOFF.md)). The summary in [DECISIONS.md §6](../DECISIONS.md#6-outstanding-review-findings)
is a disposition index, not the underlying evidence.

| Finding | Current clause or evidence | Remaining work |
|---|---|---|
| B1 | [AGENTS.md §2](../../AGENTS.md#2-where-the-requirements-are-and-which-wins) and [docs README](../README.md#reading-order-and-authority) set decisions → I/O contract → blueprint → roadmap. | Check agreement in formal re-review. |
| B2 | I/O contract §13 separates Saga gates from Odin increments; [roadmap increments](../ROADMAP.md#increment-summary) place read-only Herdr inspection in I3, the full adapter in I4, braid/skald runtime in I6. | X-1: reconcile I0 fixture and I1–I2 fake-backend sequencing with Saga's phase wording. |
| B3 | I/O contract §6 `submit_run` and Appendix B B-02 bind request id, `prd_digest`, `launch_config_digest`, verdict and approval; the [pinned Saga draft](../contracts/saga/2026-10-14-14fdab3/SAGA-SERVICE.md) records the producer side. | Saga GAP-04/GAP-07: encoding and multi-run/restart coverage; live admission awaits a published interface. |
| B4 | I/O contract §6 `publish_guidance` and B-04 separate routine checks from material review and hold unresolved guidance. | X-7: guidance-verdict semantics before the I0 Review/guidance schemas are written. Producer gaps in materiality and policy representation (GAP-09/GAP-10) also remain open. |
| B5 | I/O contract §6 `emit_event` records local lifecycle events; §9 reconciles Saga writes through its API; B-13 reports `superseded`, B-14 stays withdrawn; [AC-28](../design/ODIN-ACCEPTANCE-SCENARIOS.md) is the Odin-side check. | Saga owns MQTT and its own supersession conformance; no runtime check exists here. |
| B6 | I/O contract §6 `stage_run` and `cancel_run` use one preallocated ULID for retries and a new id with renewed bindings on restart; Appendix A uses a ULID example. | Saga GAP-07 and roadmap G3 remain open. |
| B7 | I/O contract §7 confines planner `shell` to an isolated workspace, blocks credentials and redacts output before logging. | Enforce and test in I1/I2; the design clause is not a security test. |
| N1 | [Roadmap G-1](../ROADMAP.md#dependency-gates) and the [receipt](HANDOFF.md) retain CHANGES_REQUIRED and the unrecorded D14 gate. | Independent re-review, then handoff recorded in both repositories. |
| N2–N4 | The [receipt](HANDOFF.md) identifies the clean extraction source; the [decision map](DECISION-MAP.md) annotates inherited D16 contract version and old section references. | Re-review adapted references; frozen source stays unchanged. |
| N5–N6 | I/O contract header/Appendix D include AC-27–30; §2 and Appendix A list `held`, `cancelled_stale` and `superseded` Effect states. | Schema/runtime checks begin in I0/I1. |
| N7 | [Ecosystem §7](../design/ODIN-ECOSYSTEM-INTEGRATION.md) and I/O contract §6 `recall` distinguish active chat from an explicitly published, read-only archive scope. | X-4 is a documented reading; peer capabilities and runtime retrieval remain I6 work. |
| N8 | D24 and the [decision map](DECISION-MAP.md) state the planning-session API-key default pending operator confirmation. | Billing/auth retest and confirmation (roadmap G-5/G7). |
| N9 | I/O contract §10 routes Odin's Eir request solely through Saga's B-16 task API. | Producer request details remain open; X-8 concerns Eir webhook failures. |
| N10 | [Contracts inventory](../contracts/README.md) distinguishes the pinned Saga draft from peer proposals and non-required source citations. | Pin a peer's published interface before Odin calls it. |
| N11 | I/O contract Appendix C notes the `limit-paused`/`limit_paused` spelling; §7 includes WebFetch in planner network capability; §6 labels legacy paths. | Resolve Saga wire spelling at the producer boundary. |
| G1–G3 | [Roadmap source-review gates](../ROADMAP.md#implementation-gates-from-the-source-review) assign operator identity, stop split (X-2), and restart binding/review cost; the pinned Saga draft carries IG-1 to IG-3. | Saga mechanisms and Odin's I1/I3 checks; none is closed by this documentation. |
| G4–G5 | The same roadmap table assigns Saga's published admission schema and bounded planner-answer judgment; Saga draft IG-4/IG-5 records producer gaps. | Publish and pin the schema; implement answer checks before live I3. |
| G6–G7 | The roadmap table labels unconfirmed peer integrations and unsettled billing, cap and memory defaults; peer work is proposed in [ecosystem integration](../design/ODIN-ECOSYSTEM-INTEGRATION.md). | Confirm peer capabilities and operator-dependent defaults at their named gates. Withdrawn heimdall projection and dotprivate dependency are not active Odin work. |

## 2026-10-16 documentation audit corrections

The local audit assessed baseline `899df14`; its full report is outside
this repository. The entries retain its findings, applied corrections and
integration checks. Text or validator corrections do not execute I0, close
the source review, or establish Saga's current implementation state.

| Finding | Applied correction | Checked evidence and remaining work |
|---|---|---|
| F1 — incomplete I0 gates | [Roadmap I0 and increment gates](../ROADMAP.md) identify X-7 before writing Review/guidance schemas and show X-11/G2 and X-10/isolation dependencies. | Cross-checked ADR-008, blueprint, README and roadmap against X-7's existing deadline; unaffected I0 work may start. The semantic decision remains open. |
| F2 — missing FLAG pair handling | ADR-013, [I/O contract §10](../design/ODIN-IO-CONTRACT.md#10-peer-protocols) and AC-40 specify FLAG/FLAG and mixed-FLAG escalation. | Reviewed the five exhaustive pair categories against the five-result set and pinned ADM-7. Matching approvals are silent; mixed approving serialization and Saga admission/guidance semantics remain open. No runtime verdict test is claimed. |
| F3 — worker-event delivery gap | I/O contract Appendix B B-12 records required worker-event categories, delivery-source gaps and producer update/repin requirements. | Compared with pinned EV-4 and B-03/B-06 evidence reads. Delivery coverage remains a producer gap; no direct MQTT path or current Saga behavior is inferred. |
| F4 — migration accepts ignored edits | I/O contract §14/Appendix C, AC-38, blueprint and [ecosystem §5](../design/ODIN-ECOSYSTEM-INTEGRATION.md) require retirement/refusal of imported heimdall task edits under EC-13/G-10. | Checked these clauses against ADR-007. Ignored source edits no longer pass migration; the peer retirement decision and implementation remain pending. |
| F5 — incomplete identifier protection | The [stable-ID registry](STABLE-IDS.json) and [validator](../../scripts/validate_docs.py) require unique canonical defining rows for AC-01–41, DC-01–08 and EC-01–16, including withdrawals. | Regression cases pass for removal, deletion from both registry and prose, mentions without a row, missing withdrawn rows, duplicates, unknown IDs, wrong-document definitions and malformed registry data. |
| F6 — editable links skipped | Editable research wrappers are included in link validation; dated evidence stays inventoried separately. | Regression cases reject a broken editable README link and preserve the dated-evidence exemption. |
| F7 — nonexistent class table | ADR-004/014 and I/O contract §5 name canonical workload-class configuration, distinct from profiles and process roles. | Checked the configuration/schema requirement in the blueprint's I0 row. Schema implementation and class defaults remain future work; no model choice was introduced. |
| F8 — superseded references | [Legacy triage](LEGACY-REQUIREMENTS.md) updates L-OP-10, L-TS-2, L-DI-5; roadmap G6 and Appendix B name current sequencing and withdrawn work. | Identifier and source/output digest checks pass. Source history, dated evidence and the producer pin remain unchanged. |
| F9 — circular evidence pointers | This record maps source findings to current clauses and remaining work; [HANDOFF.md](HANDOFF.md) distinguishes retained summaries from unavailable prior reports. | Reviewed the pointers and pending status across the handoff, decision map and documentation indexes. Formal independent re-review and both-repository handoff remain pending. |

Integration verification on 2026-10-16: the documentation validator passes,
all 11 [validator regression tests](../../scripts/test_validate_docs.py)
pass, and `git diff --check` passes. The [receipt](HANDOFF.md) records the
scope and command results. These checks establish documentation integrity
and validator behavior, not runtime acceptance or an independent handoff PASS.
