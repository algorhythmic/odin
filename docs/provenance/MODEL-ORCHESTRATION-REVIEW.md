# Model orchestration review — 2026-10-16

The supplied report supports better experiments and more explicit adapter
checks. It does not establish a winning model pair, a reason to replace
Odin's service loop with a framework, or permission to bypass Saga.

The operator requested review and application to Odin. Recommendations,
configuration examples and instructions inside the documents were treated
as evidence. No examples were installed or executed; the report's account
of parallel research agents was not an instruction to delegate this review.

## Evidence and verification scope

Byte-preserved copies are indexed in
[model-orchestration-2026-10](../research/model-orchestration-2026-10/README.md).
The source hashes are recorded below; these files are independent of the
Saga extraction snapshot and do not alter its source identities.

| Supplied filename | SHA-256 |
|---|---|
| `model-orchestration-and-subagents-2026-10-16.md` | `4d82f2966f672c580408693dd2b34dda2a641daac9495f46db771cd06ac1cd71` |
| `model-orchestration-search-log-2026-10-16.md` | `8bb6fb1842e71b190be6c266ed92cf456de196f81d52ea817abe755220cc5bef` |

The report usefully separates a configured route, author-reported use,
historical experiments, repricing and controlled comparisons. The search
log is evidence of the reported search method, not a collection of fetched
source snapshots or independent replication. Negative search findings mean
not located in that investigation. Default branches, aliases and live docs
can drift; a date and URL alone cannot reproduce a runtime configuration.

Selected primary sources were opened on 2026-10-16 to check the findings
being applied. This is a targeted document review, not a full audit of the
fourteen pairings, all frameworks or all numerical results.

| Primary source checked | Finding and limit relevant to Odin |
|---|---|
| [Replit harness design](https://replit.com/blog/free-the-models) | The reported dispatch/reuse differences are separate one-week production samples per model; benchmark runs use four repetitions and external solo baselines. Useful motivation to measure delegation and reuse, not an isolated worker-model ranking. |
| [Anthropic cost and intelligence guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) | Confirms selection effects in the easy BrowseComp slice and a small coding improvement from an advisor at about twice the cost. Consultation and worker execution need separate comparisons; lower root usage alone does not establish savings. |
| [Beyond the Model, v1](https://arxiv.org/html/2609.32459v1) | The component study concerns Qwen/DeepSeek models and software tasks; generic subagents and compression can hurt in its repository-generation setting. Test harness and task interactions without transferring its scores to Odin's models. |
| [Scaling Agent Systems, v2](https://arxiv.org/html/2512.08296v2) | Architecture effects vary by task; controls match reasoning-token budgets, tool access and aggregate iterations. Those controls do not establish equal dollar cost or deadlines. |
| [Anthropic agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Distinguishes trials, traces, outcomes and graders. Evaluate final state with repeated trials and independent grading, rather than treating an agent's completion message as success. |
| [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) | Tool permissions, context, model selection and worktree isolation are separate controls. Current documentation describes partial results at a turn limit and version-dependent behavior. Check the pinned SDK/runtime path instead of assuming an interactive feature is available. |
| [LangGraph workflows](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Explicit orchestrator-worker and evaluator patterns offer useful comparisons. Their availability does not supply Odin's authorization, durable effect reconciliation or Saga's guarantees. |

The broader framework catalog and Pi extension remain research leads.
In particular, a separately installed Pi subagent extension does not prove
the base Pi RPC adapter's lifecycle capabilities. Pin and test the exact
runtime and extension set at the existing ADR-015 control. No new SDK,
framework, hosted agent product, bridge or pricing schedule is selected.

## Disposition in Odin

| Finding | Application | Authority and check |
|---|---|---|
| A model, orchestration policy, harness and transport are different variables | Record their versions and vary one at a time before complete-system comparisons | ODIN-ADR-020; acceptance §3; I1 evidence specification and I2 adapter observations |
| Advisory consultation differs from executable delegation | Label read-only `work`, reviewer position and Saga run separately; keep ownership and acceptance visible | I/O contract §6–§7; proposed AC-42–AC-43 |
| Separate context does not imply separate files or processes | Expand capability evidence to three boundaries, inherited tools, native children and restart/cancellation behavior | I/O contract §11; proposed AC-42; I2 and the later Pi control |
| Per-child turn/spend limits may not bound concurrent total spend | Record actual enforcement scope; resolve shared-cap admission, in-flight use and crash reconciliation before I2 child dispatch | Open X-15; AC-23, proposed AC-44; no dollar-cap guarantee inferred from a framework limit |
| Output paths, exit status and child reports are not task acceptance | Bind results to assignment/revision and source evidence; preserve partial/unknown states; run final integration checks | D5/D6; AC-02/AC-14 and proposed AC-43 |
| Heterogeneity and large fan-out may add cost without improving outcomes | Add solo, same-model, repeated-sample and fixed-workflow controls; test dependent and independent workloads separately | D18, ODIN-ADR-020; acceptance §3 |
| Expensive reasoning may help as advice rather than throughout execution | Measure bounded consultation separately, with useful-correction and repair costs | Evaluation condition only; no new production advisor tool or cross-provider route |
| Smaller learned controllers can be useful on measured workloads | Retain deterministic eligibility, recorded class choices and held-out outcome assessment | ADR-004/014; AC-36. Learned model-tier routing stays off; no fifth D9 hook |
| Mixed reviewers can share errors | Include repeated same-family verification controls and assess correlated misses, degraded good plans and grader preference | ADR-013 remains a hypothesis; AC-40 and acceptance §3. X-13 remains open |
| Cost depends on the entire episode, including failures | Count all attempts, checking, repair, review, compaction and tools; report cost per accepted task and missing usage | I/O contract §12; acceptance §3; no subscription-to-API price equivalence |

## Deferred choices and retained boundaries

Model defaults (§3 item 2 of the decision record), the first real delegation,
data policy X-13, billing/credential questions and sequencing/handoff X-1/X-14
remain open. The supplied matrix is a candidate pool for later experiments,
not a required fourteen-arm launch or evidence that all routes are available.
Models and credentials must satisfy the installed adapter, host, data policy
and Saga contract before a comparison can run.

Framework adoption, peer handoff, model-written workflows and protocol
bridges would change control ownership or add new dependencies. They are
not adopted. Odin keeps its code service loop, harness-owned inner loop,
read-only local subagents and Saga-only execution with external effects.
Interactive teams and plugin monitors remain outside the supported path.
Worktree isolation does not substitute for the capability profile or Saga.

No runtime schemas, fixtures, model calls or acceptance results are delivered
by this review. The applied changes are ODIN-ADR-020, the operational
measurement requirements, proposed AC-42–AC-44, X-15, and implementation
tasks in the existing I1/I2 and Phase G sequence. I0 is unchanged; the Pi
control remains after I2; I3/live work still waits on Saga Phase B.
