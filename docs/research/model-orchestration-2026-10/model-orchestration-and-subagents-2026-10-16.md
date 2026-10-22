# Mixed model orchestration across frameworks and harnesses

**Research cutoff: 16 October 2026. Expanded edition.** Fourteen directed model pairings, eight framework families, eight execution-harness categories, and hosted orchestration options, with implementation references and evidence quality distinguished throughout.

**The broader search found real directional implementations and historical pairing experiments, but no controlled ranking of all the current combinations.** Fable↔Astra advisory bridges, Astra→Sol/Luna worker runs, and Fable→Terra/Sol/Luna historical tests add useful evidence beyond the original Fable→Opus versus Fable→Sol question. None establishes a universal best team.

The most consequential choice is often the orchestration design: a brief advisor consultation, a persistent tool-using worker, an explicit execution graph, and a peer team have different costs and responsibilities. Model, role, harness, context, and verification must be considered together. The report therefore compares model directions first, then the mechanisms that make those directions work.

## Model identities and directional evidence

Family labels alone are insufficient for a reproducible comparison. The following IDs anchor the current configurations considered here; historical evidence retains the versions actually used.

| Family | Model ID used for current consideration | Reference |
|---|---|---|
| Fable | `claude-fable-5-1` | [Official model](https://platform.claude.com/docs/en/models/fable-5-1/overview) |
| Astra | `gpt-6-astra` | [Official model](https://developers.openai.com/api/docs/models/gpt-6-astra) |
| Opus | `claude-opus-5-5` | [Official model](https://platform.claude.com/docs/en/models/opus-5-5/overview) |
| Sonnet | `claude-sonnet-5-5` | [Official model](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) |
| Haiku | `claude-haiku-5-5` | [Official model](https://platform.claude.com/docs/en/models/haiku-5-5/overview) |
| Sol | `gpt-6-sol` | [Exact requested version](https://developers.openai.com/api/docs/models/gpt-6-sol) |
| Terra | `gpt-5.6-terra` | [Documented Terra version](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
| Luna | `gpt-6-luna` | [Official model](https://developers.openai.com/api/docs/models/gpt-6-luna) |

Terra is not assumed to have a GPT-6 release. Sol remains the exact GPT-6 version requested, even when a project's “latest Sol” resolves to GPT-6.1 Sol. Sonnet 5.5 and Haiku 5.5 were released on 28 September and 7 October respectively, so much available operational evidence predates them. [Sonnet lifecycle](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [Haiku lifecycle](https://platform.claude.com/docs/en/models/haiku-5-5/overview).

**Evidence labels:** configuration means a concrete public route; observed means an author's reported use, not independent reproduction; historical benchmark means a stated task comparison using older versions. General adapter support is weaker evidence than an exact configured or observed direction. An advisor returns a judgment while the parent retains execution.

### Fable as the lead

| Direction | Best directional evidence located | What remains to be established |
|---|---|---|
| **Fable → Astra** | **Current advisory configuration.** A Fable of Codexes pins Fable 5.1 as conductor and GPT-6 Astra for deep consultation through Codex CLI. [Implementation](https://github.com/jvogan/a-fable-of-codexes/blob/main/README.md) | This proves a defined consultation route, not the performance of a fleet of Astra implementation workers. |
| **Fable → Opus** | **Current configuration and older observations.** The same project assigns Opus 5.5 squad-lead/design roles; native Claude subagent model overrides support the mechanism. [Fleet](https://github.com/jvogan/a-fable-of-codexes/blob/main/README.md), [native configuration](https://code.claude.com/docs/en/sub-agents) | Current same-root, same-budget outcome comparison against the other workers. |
| **Fable → Sonnet** | **Current configuration plus historical benchmarks.** Sonnet 5.5 scouts appear in the fleet; older Fable 5→Sonnet 5 has measured evidence. [Fleet](https://github.com/jvogan/a-fable-of-codexes/blob/main/README.md), [historical benchmark](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md) | Whether current Sonnet preserves quality on the actual assigned tasks; older scores cannot be transferred. |
| **Fable → Haiku** | **Current role configuration; older measured lane.** A public allocation configuration lists Fable 5.1 and Haiku 5.5; historical trials used Haiku 4.5. [Configuration](https://gist.github.com/yanhua1010/de94760c972b7cb61f2c0fb9c7f50ba2), [benchmark](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md) | Exact current successful execution and quality under the chosen context/tools. |
| **Fable → Sol** | **Exact Sol configuration.** Fable Advisor exposes GPT-6 Sol implementation lanes and permits a Fable architect. Its author currently uses Opus as architect. [Implementation](https://github.com/DannyMac180/fable-advisor) | Configurability is not an observed Fable 5.1→Sol 6 result. Historical Sol 5.6 evidence is separate. |
| **Fable → Terra** | **Historical measured execution.** Fable 5 coordinated Terra 5.6 through a CLI lane, including a feature follow-up with hidden checks. [Benchmark](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md), [author follow-up](https://www.reddit.com/r/ClaudeAI/comments/1v1tnmn/comment/oyrkstz/) | Fable 5.1 replication with matched tools and effort; native and CLI lanes were not identical. |
| **Fable → Luna** | **Current configuration plus historical lane tests.** Fable 5.1→Luna 6 scout dispatch is documented; earlier measurements used Luna 5.6. [Fleet](https://github.com/jvogan/a-fable-of-codexes/blob/main/README.md), [benchmark](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md) | Cost per accepted result after checking and repair, especially for tasks that are only superficially simple. |

### Astra as the lead

| Direction | Best directional evidence located | What remains to be established |
|---|---|---|
| **Astra → Fable** | **Observed advisory use and a public protocol.** Density describes Astra periodically consulting Fable; fables provides a Codex→Claude advisor route. [Firsthand account](https://www.density.ai/articles/ai-setup-sep-2026), [protocol](https://github.com/czlonkowski/fables/blob/main/README.md) | Density's Fable naming mixes 5 and 5.1. Advisory evidence does not establish a full Fable execution worker. |
| **Astra → Opus** | **Family-level reported use plus a current adapter.** An author reports trying Opus workers under Astra; Codex on Crack supplies a Codex-host→Opus 5.5 execution route. [Author](https://www.reddit.com/r/vibecoding/comments/1wl3lfi/i_built_an_orchestration_package_that_lowered_my/), [implementation](https://github.com/ethanplusai/codex-on-crack) | Exact worker version and controlled outcomes in the original account. Its headline savings concern a different worker family. |
| **Astra → Sonnet** | **Family-level reported use and generic Codex→Sonnet wiring.** [Author](https://www.reddit.com/r/vibecoding/comments/1wl3lfi/i_built_an_orchestration_package_that_lowered_my/), [wrapper](https://github.com/alectivism/cross-model-agent-delegation) | No opened trace establishes exact Astra→Sonnet 5.5 behavior. |
| **Astra → Haiku** | **Generic adapter feasibility.** Codex→Haiku lanes exist, but the inspected wrapper table still uses Haiku 4.5. [Wrapper](https://github.com/alectivism/cross-model-agent-delegation) | Exact Astra→Haiku 5.5 observed execution was not located; this is the weakest current pairing evidence in the matrix. |
| **Astra → Sol** | **Author-reported exact-generation run and current configuration.** Orca's stress run names GPT-6 Sol editors; Astral explicitly routes to `gpt-6-sol`. [Run report](https://www.reddit.com/r/AI_Agents/comments/1wpvs6s/we_asked_our_coding_agent_to_use_at_least_100/), [routing](https://astral-orchestrator.vercel.app/docs/routing/) | The stress run has no paired baseline; configuration alone supplies no quality ranking. |
| **Astra → Terra** | **Observed usage ledger.** A September run records an Astra coordinator with one Terra 5.6 reader among other workers. [Author's ledger](https://community.openai.com/t/routing-delegated-work-to-cheaper-models-cut-this-runs-price-by-54/1398071) | Its savings calculation reprices the same token workload; it is not an all-Astra rerun. This is a user report, not an OpenAI study. |
| **Astra → Luna** | **Current exact configuration and reported run.** Donvito publishes Astra/Luna 6 profiles; Orca reports 100 Luna 6 reviewers. [Profiles](https://github.com/donvito/codex-astra-luna-orchestrator), [run report](https://www.reddit.com/r/AI_Agents/comments/1wpvs6s/we_asked_our_coding_agent_to_use_at_least_100/) | Missed defects, escalation frequency, and value against fewer reviewers or a single strong worker. |

### Read the new pairing measurements narrowly

The July multimodels benchmark contains **198 runs: six stations × eleven models × three repeats**, with prompts, responses, and graders. It is stronger than a configuration-only example. However, versions, effort, and native-versus-CLI execution differ; some initial costs omit hidden reasoning. The real-feature follow-up supplies hidden checks, but remains a small task sample. [Benchmark artifacts](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md), [author's methods and follow-up](https://www.reddit.com/r/ClaudeAI/comments/1v1tnmn/comment/oyrkstz/).

Orca's author reports 100 Luna 6 reviewers, 25 Sol 6 editors, and two Sol checks under Astra for about $5.75 through OpenRouter. The linked PR corroborates the documentation work and review assignments, not every model-specific usage claim. Treat it as a stress demonstration, not evidence that very large fan-out is economical or necessary. [Author report](https://www.reddit.com/r/AI_Agents/comments/1wpvs6s/we_asked_our_coding_agent_to_use_at_least_100/), [implementation PR](https://github.com/okikorg/orca-harness/pull/32).

The Astra ledger records nine Sol 5.6, six Luna 5.6, and one Terra 5.6 worker. Its 54.4% counterfactual saving holds token usage fixed while applying Astra prices and excludes unknown-price approval work. It demonstrates heterogeneous execution and accounting, not equivalent quality from an unrun all-Astra system. [Ledger and limitations](https://community.openai.com/t/routing-delegated-work-to-cheaper-models-cut-this-runs-price-by-54/1398071).

## What changes when the direction is reversed

The arrow describes who owns the work, not a fixed intelligence ranking. In **Fable→Astra**, Fable may request a compact judgment from Astra while retaining implementation. In **Astra→Fable**, Astra may ask for a design review, or launch a complete Claude worker with its own tools. Those are different experiments even if the model names are identical.

Separate five implementation layers when evaluating a pairing:

| Layer | Decision or responsibility | Why the distinction matters |
|---|---|---|
| Model | Reason, propose tool calls, produce a result | An API model ID does not supply a coding workspace or scheduler |
| Orchestration policy | Choose worker, assignment, dependencies, retries, and stopping | May live in prompts, application code, a graph, or a learned policy |
| Framework | Provide agent objects, state transitions, tool wrappers, and checkpoints | Makes patterns implementable; does not establish their task quality |
| Execution harness | Run model/tool loops, manage context and permissions, edit files, resume work | Changing the harness can change the outcome while the model stays fixed |
| Transport or bridge | Connect providers, processes, or remote agents | API compatibility does not guarantee equivalent tool or lifecycle behavior |

This separation also explains why a model switch, an advisor call, a worker spawn, and a conversation handoff should not be counted as the same operation. For manager-owned delegation, the child returns evidence and the parent decides what to accept. For a handoff, the receiving agent owns the next interaction. [Ownership patterns](https://developers.openai.com/api/docs/guides/agents/orchestration).

### Additional architectures surfaced by broader searches

| Search vocabulary | Actual control pattern | What to test |
|---|---|---|
| Supervisor, coordinator, manager, boss-worker | Lead repeatedly assigns and integrates | Assignment quality, worker reuse, verification, unnecessary spawns |
| Architect-editor, planner-executor, plan-and-execute | Planning precedes implementation, often serially | Whether a separate plan helps enough to pay for its handoff |
| Advisor, consult-up, escalation, second opinion | Executor keeps the loop and asks for help | Consultation rate, useful corrections, added latency |
| Agent team, swarm, peer collaboration | Agents share a task list or select the next participant | Ownership, cycles, duplicate work, stopping, shared-state conflicts |
| Graph, DAG, map-reduce, scatter-gather | Code schedules dependencies and joins | Correct joins, bounded parallelism, replay and idempotency |
| Blackboard, shared memory, artifact coordination | Agents exchange work through a common record | Stale reads, provenance, merge policy, write ownership |
| Council, debate, mixture of agents, ensemble | Several proposals are selected or synthesized | Diversity benefit against repeated same-model samples |
| Router, cascade, budget-aware policy | Select a model or escalate by a decision rule | Calibration, cost of routing, recovery after wrong routes |

These are search and design categories rather than interchangeable product features. A framework can implement several; a harness may expose only one.

## New evidence from the wider search

### Production leads behave differently in the same product

Replit's September 2026 report describes a core loop choosing specialist type, worker tier, effort, and whether to resume an existing worker. Production observations at medium effort found:

| Measure | Fable 5.1 | GPT-6 Astra |
|---|---|---|
| Turns dispatching any subagent | 21% | 36% |
| Turns dispatching a general worker | 2.3% | 20% |
| Dispatches returning to an existing subagent | 29% | 42% |

These were separate one-week production samples, not randomized matched tasks. Worker model IDs are not disclosed sufficiently to populate exact pairings. In its benchmark comparison, the Astra-led product scored 72% at $2.11/task on DeepSWE versus 61% at $1.34 for a single persistent sidekick. Four repetitions support a system-level result; different cost and external solo baselines prevent attributing it solely to model selection. [Replit harness design](https://replit.com/blog/free-the-models).

### Delegation and advisory calls have measurable failure cases

Anthropic's cost guide reports that Fable 5 with Sonnet 5 workers saved money on a selected easy BrowseComp slice, but selection included only cases the delegated system consistently solved. On the full harder set, solo Fable matched delegated accuracy at 22–30% lower cost. Larger-than-context defect search roughly halved cost with delegation, while losing 10–12 score points.

The reverse pattern also has current evidence: Opus 5.5 with a Fable 5.1 advisor gained 1.7 coding score points, at the edge of run-to-run noise, for about 2.1× cost. This makes **Opus→Fable advisor** a useful additional comparison, not a demonstrated bargain. [Measured cost and intelligence tradeoffs](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence).

### Harness effects deserve their own comparison

The September 2026 *Beyond the Model* study compares mini-SWE-agent and OpenCode using ten Qwen/DeepSeek models across three benchmarks, then isolates components in NanoHarness. On repository-generation tasks, structured tools and task-specific subagents helped more consistently than generic subagents or context compression, which could hurt. These are open-model results, not a ranking of Astra or Fable. They justify testing **model × harness × task**, rather than crediting every gain to the named lead. [Paper and component analysis](https://arxiv.org/html/2609.32459v1).

Anthropic's earlier planner–generator–evaluator application harness provides a readable implementation counterpoint: agents exchange files and negotiate acceptance criteria. As the underlying model improved from Opus 4.5 to 4.6, the author removed sprint scaffolding and moved evaluation later. The examples are illustrative builds, with large resource differences, rather than a controlled modern mixed-model trial. [Long-running application harness](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## Framework comparison by control and implementation

“Supports multiple models” is only the first requirement. These frameworks differ in who chooses the next action, how children receive state, what persists, and which failures the runtime can recover from. Direct provider clients and translation adapters should be distinguished; neither guarantees every current model feature behaves identically.

### Control flow and model boundaries

| Framework family | Who selects and schedules work | How models and context are assigned |
|---|---|---|
| **LangGraph** | Code defines nodes and transitions; a planner can produce jobs dispatched with `Send`, and reducers combine worker outputs. | Each model-calling node can use a different provider client. Job state, shared state, and merge logic are explicit. [Orchestrator-worker examples](https://docs.langchain.com/oss/python/langgraph/workflows-agents) |
| **LangChain and DeepAgents** | A supervisor calls tool-wrapped children. DeepAgents adds a built-in `task` tool and planning/context scaffolding; background subagents have a separate lifecycle. | Child model/provider overrides are supported. DeepAgents defaults to isolated input; beta fork mode copies parent history/state. Do not let its default general-purpose child become an unrecorded comparison arm. [LangChain](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents), [DeepAgents](https://docs.langchain.com/oss/python/deepagents/subagents) |
| **PydanticAI** | Core delegation is an async tool invoking another agent. Harness `SubAgents` supplies dispatch; `DynamicWorkflow` lets the model write orchestration code. | Direct Anthropic/OpenAI adapters and independent model objects. SubAgents starts fresh child histories, forwards dependencies/workspace, and does not automatically forward parent tools. [Core example](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), [SubAgents](https://pydantic.dev/docs/ai/harness/subagents/) |
| **OpenAI Agents SDK** | Agent tools return to the manager; handoffs change the active owner. Application code can schedule independent runs. | Per-agent models; cross-provider adapters are language-specific. Explicit task input and history policy matter, especially across handoffs. [Ownership](https://developers.openai.com/api/docs/guides/agents/orchestration), [providers](https://developers.openai.com/api/docs/guides/agents/models) |
| **Microsoft Agent Framework** | Separate sequential/concurrent patterns, selected-speaker group chat, handoffs, and Magentic's plan/progress/stall loop. GroupChat and Magentic are not automatic parallel fan-out. | Participants and manager use independent provider clients. Shared conversation, workflow messages, and scoped state are different choices. [Group chat](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/group-chat), [Magentic](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic) |
| **Google ADK 2.0** | Collaboration modes coexist with explicit and dynamic workflow nodes. `task`/`single_turn` return to the parent; `chat` retains ownership until transfer. | Branch-isolated contexts; language-specific providers. Python OpenAI uses LiteLLM, while Go has experimental native Responses support. [Collaboration](https://adk.dev/workflows/collaboration/), [Python bridge](https://adk.dev/agents/models/litellm/), [OpenAI route](https://adk.dev/agents/models/openai/) |
| **Strands** | Manager-as-tools, peer-selected Swarm handoffs, or code-defined Graph. Swarm naming does not imply simultaneous workers. | Each agent has its own model object. Python and TypeScript differ in shared-context and handoff payload behavior. [Tools](https://strandsagents.com/docs/user-guide/sdk/multi-agent/agents-as-tools/), [Swarm](https://strandsagents.com/docs/user-guide/sdk/multi-agent/swarm/) |
| **CrewAI** | Sequential tasks or hierarchical manager delegation; Flows add explicit routing and state. Async work requires dependency design. | Agents set their own `llm`, with a separate manager. Native Anthropic and OpenAI Responses are documented; task context selects predecessor results. [Hierarchy](https://docs.crewai.com/en/learn/hierarchical-process), [models](https://docs.crewai.com/en/concepts/llms) |

### Recovery, budgets, and acceptance

| Framework family | Persistence and recovery | Limits and verification mechanisms |
|---|---|---|
| **LangGraph** | A checkpointer records thread execution; a Store serves application data across threads. RAM persistence does not survive process loss. | Explicit counters, job caps, verifier nodes, and `interrupt`/resume gates. Replayed side effects need idempotency. [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) |
| **LangChain and DeepAgents** | Uses LangGraph checkpoints. Async children have independent server threads and parent task metadata, distinct from a Python async function. | Run/thread model- and tool-call middleware; thread counts require a checkpointer. Child approval policy and background cancellation need explicit setup. [Async children](https://docs.langchain.com/oss/python/deepagents/async-subagents), [middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in) |
| **PydanticAI** | Saving message history is separate from durable execution through a backend such as Temporal, DBOS, or Prefect. | Core usage limits, child/depth limits, validators, and traces. DynamicWorkflow does not inherit parent `usage_limits`; set its child limits. Spend checks are next-request brakes, not concurrent reservations. [Durability](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/), [workflow](https://pydantic.dev/docs/ai/harness/dynamic-workflow/), [spend](https://pydantic.dev/docs/ai/harness/spend/) |
| **OpenAI Agents SDK** | Sessions retain conversation; approval interruptions produce resumable run state. This is not automatically a durable application job queue. | Turn limits and guardrails; tool approval pauses; host handles overall deadlines/concurrency/spend. Built-in traces cover nested events. [Running](https://developers.openai.com/api/docs/guides/agents/running-agents), [approvals](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals), [tracing](https://developers.openai.com/api/docs/guides/agents/integrations-observability) |
| **Microsoft Agent Framework** | Checkpoints include executor/shared state, messages, and pending requests. Rebuild compatible workflows with stable identities. | Group-chat termination predicates; Magentic round/stall/reset caps and plan-review options. Concurrent requests need fresh manager state. [Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints), [human input](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop), [Magentic](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic) |
| **Google ADK 2.0** | Dynamic child executions are checkpointed and reused on replay. Parent orchestrators calling `ctx.run_node` need `rerun_on_resume=True`. | Explicit loop/route bounds and acceptance nodes. Scheduling identities must be deterministic enough for replay; task agents have mode-specific restrictions. [Dynamic workflows](https://adk.dev/graphs/dynamic/), [mode constraints](https://adk.dev/workflows/collaboration/) |
| **Strands** | Graph/Swarm session managers belong on the orchestrator. Snapshots and individual conversation persistence are separate concerns. | Graph/swarm step and time limits, hooks, and cooperative cancellation. Python Graph defaults to an OR join; require all dependencies explicitly before synthesis. [Sessions](https://strandsagents.com/docs/user-guide/sdk/agents/session-management/), [Graph](https://strandsagents.com/docs/user-guide/sdk/multi-agent/graph/), [production controls](https://strandsagents.com/docs/user-guide/sdk/deploy/operating-agents-in-production/) |
| **CrewAI** | Flow `@persist` stores state, with resume/fork support. State restoration does not imply exactly-once external effects. | Agent iteration/time/retry settings, task guardrails, human-input/feedback gates. A structured result or LLM guardrail still needs outcome validation. [Flows](https://docs.crewai.com/en/concepts/flows), [agents](https://docs.crewai.com/en/concepts/agents), [tasks](https://docs.crewai.com/en/concepts/tasks) |

### Current implementation details that invalidate older examples

- **LangChain:** `langgraph-supervisor` is no longer actively maintained; use the documented subagent pattern or explicit graph composition. [Migration guidance](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents).
- **Microsoft:** current Python `OpenAIChatClient` uses Responses; the old Responses-client name changed, and Chat Completions is now `OpenAIChatCompletionClient`. AutoGen directs new work to Agent Framework. [Migration](https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes), [provider guide](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/openai), [AutoGen](https://github.com/microsoft/autogen).
- **ADK and Strands:** language is part of the configuration. Python/Go provider paths and Python/TypeScript join or handoff behavior should not be assumed equivalent. Use the specific runtime's documentation cited in the tables.
- **Exact Sol:** use Responses for reasoning with tools. GPT-6 Sol's Chat Completions function calling requires `reasoning_effort='none'`; a generic gateway can change the treatment. [Model reference](https://developers.openai.com/api/docs/models/gpt-6-sol).
- **Claude state:** adapters must handle current thinking/tool-choice constraints. Keep signed provider-native reasoning state in its original session; exchange task briefs and results across vendors. [Anthropic adapter](https://pydantic.dev/docs/ai/models/anthropic/).

### Three implementations with different control ownership

The following are original, unexecuted pseudocode sketches. They show what the application owns; concrete SDK entry points are linked in the tables. Credentials, storage, tools, and provider-specific message formats are intentionally outside these sketches.

```text
MANAGER CALL AND RETURN
start lead with a fixed worker catalog
repeat until complete or episode budget exhausted:
    action = lead.choose_next_action(task, accepted_reports)
    if action delegates:
        reserve budget; create bounded child context
        report = worker_loop(action.model, action.brief, allowed_tools)
        persist usage and outcome; validate report; return it to lead
    otherwise execute an allowed lead action or produce final output
```

PydanticAI tools, LangChain subagents, DeepAgents tasks, and SDK agent tools fit this pattern. The manager controls whether another child runs. An outer runtime must still enforce limits and verify completion.

```text
CODE SCHEDULED PLAN AND EXECUTE
jobs = validate_and_cap(planner(task))
checkpoint jobs with stable IDs
run independent unfinished jobs through a bounded worker pool
checkpoint each artifact and acceptance result
join only when every required dependency is terminal
if checks fail: enter a bounded repair path
otherwise synthesize, then commit the accepted result
```

LangGraph or ADK dynamic workflows can implement this design. The application defines legal transitions and joins, even if a model writes the plan. Retrying a node must not duplicate a completed external action.

```text
PEER HANDOFF                 ADAPTIVE LEDGER MANAGER
active worker acts          manager updates plan and progress
chooses next peer           manager chooses next participant
passes bounded context      participant returns evidence
checks shared stop rule     manager detects stalls and replans
continues at that peer      manager stops or synthesizes
```

Strands Swarm illustrates peer-directed ownership; Microsoft Magentic illustrates ledger-driven coordination. A speaker-selection rule alone is not the full planning/stall-recovery loop. Microsoft explicitly cautions that behavior outside the original Magentic-One design is untested. [Swarm](https://strandsagents.com/docs/user-guide/sdk/multi-agent/swarm/), [Magentic](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic).

## Execution harness comparison

A shared-framework Fable→Sol worker and a Fable→Codex CLI worker are different treatments. The second changes the worker's tool loop, system instructions, context management, and lifecycle along with its model. Record three independent boundaries: conversation, process/session, and filesystem. None implies the others.

| Harness category | Orchestration approach and model selection | Execution, recovery, and verification implications |
|---|---|---|
| **Claude Code subagents and teams** | Fresh subagents run a tool loop and return results; full Claude model IDs select worker tiers. Forks inherit the parent's model. Experimental teams add peer messaging and shared tasks. | Fresh context differs from copied history; `isolation: worktree` supplies repository isolation explicitly. `maxTurns` can return partial work. Team completion/idle hooks exist, but in-process teammates are not restored by `/resume`. [Subagents](https://code.claude.com/docs/en/sub-agents), [teams](https://code.claude.com/docs/en/agent-teams) |
| **Codex CLI** | Lead creates threads, follows up, waits, and integrates. Role TOML sets model/effort; provider and security context are inherited. A Claude model string alone does not create a cross-provider child. | Explicit workspace policy is needed; a read-only prompt is not a sandbox boundary. `max_concurrent_threads_per_session` bounds child concurrency. Native GPT-tier delegation and an external Claude worker use different integration paths. [Role configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| **OpenCode** | Primary agents call child subagents. Per-agent `provider/model-id` supports a common execution substrate for either lead and either provider, subject to adapter compatibility. | Separate child conversations do not establish separate filesystems. Agent definitions specify model, permission, and `steps`; the step limit triggers a summary rather than a dollar cap. Omitted child models inherit the parent. [Agent schema and examples](https://opencode.ai/docs/agents/) |
| **OmO and the OpenCode edition** | Adds opinionated task categories, specialists, and execution workflows over model routing. Current standalone OmO and the OpenCode edition are distinct runtimes. | Plans, progress state, evidence ledgers, concurrency, depth, and TTL controls affect execution. Current standalone and older OpenCode configuration keys differ. The old repository now redirects to Oh My OpenAgent. [Current docs](https://omo.dev/docs), [repository and migration](https://github.com/code-yeongyu/oh-my-openagent) |
| **Pi with pi-subagent** | A small extensible coding harness; this named extension launches independent Pi processes in tmux with child provider/model/thinking overrides. | Durable JSONL history and metadata support inspect/steer/wait/follow-up. Parent shutdown suspends children; resume restores them idle with history. Nested delegation is disabled. `--cwd` selects an existing directory, not a new worktree. [Extension](https://github.com/badlogic/pi-subagent), [base harness](https://github.com/earendil-works/pi/tree/main/packages/coding-agent) |
| **Aider architect and editor** | A serial two-model protocol: architect proposes a solution, editor applies edits. `--model` and `--editor-model` choose the roles. | Both use the selected repository/files; this is not a persistent worker team. Same-model architect/editor is a useful control. Two calls add latency/cost; model backend and edit-format support matter. [Modes and flags](https://aider.chat/docs/usage/modes.html) |
| **Kilo and Roo delegation** | Current Kilo full-tool agents delegate through `task`, with per-agent `provider/model`; its dedicated Orchestrator mode is deprecated. Roo's Boomerang mechanism pauses the parent, runs the child, then resumes from its summary. | Kilo child sessions isolate conversation; permission/step settings are explicit. Roo is a serial return-to-parent design. Pin product and edition instead of combining current CLI docs with older mode tutorials. [Kilo agents](https://kilo.ai/docs/customize/custom-subagents), [deprecation](https://kilo.ai/docs/code-with-ai/agents/orchestrator-mode), [Roo](https://docs.roocode.com/features/boomerang-tasks) |
| **OpenHands Software Agent SDK** | Registered specialists expose task delegation. A non-inherited child `model` is an **LLM profile name**, not necessarily an API model slug. | Profile, tool, context, and workspace choices must be explicit. Child settings expose per-run iteration and USD caps; resolved parent MCP servers are inherited. The source example demonstrates registration and combined cost retrieval. [Loader rules](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/subagent/AGENTS.md), [implementation example](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/42_file_based_subagents.py) |

### Concrete configuration examples

These are unexecuted configuration sketches. They identify the actual model-selection location; account access, package versions, and endpoint compatibility still require validation.

For a common-runtime comparison in OpenCode, keep the worker role fixed and swap only its model. Reverse the two model assignments to test the opposite direction. [Configuration reference](https://opencode.ai/docs/agents/).

```json
{
  "agent": {
    "lead": {
      "mode": "primary",
      "model": "anthropic/claude-fable-5-1"
    },
    "worker": {
      "mode": "subagent",
      "description": "Resolve one bounded assignment and return evidence",
      "model": "openai/gpt-6-astra",
      "steps": 20
    }
  }
}
```

For native Claude delegation, a fresh worker definition can pin its model and worktree. The lead model is selected separately. [Claude agent fields](https://code.claude.com/docs/en/sub-agents).

```yaml
# .claude/agents/worker.md
---
name: worker
description: Executes bounded implementation assignments
model: claude-opus-5-5
maxTurns: 20
isolation: worktree
---
Return changed artifacts, checks performed, and unresolved issues.
```

Codex uses a different role file and inherits the provider. An Astra lead can explicitly select this exact Sol child rather than a newer default. [Codex role fields](https://learn.chatgpt.com/docs/agent-configuration/subagents).

```toml
# .codex/agents/sol_worker.toml
name = "sol_worker"
description = "Bounded implementation worker"
developer_instructions = "Return artifacts, checks, and unresolved issues."
model = "gpt-6-sol"
model_reasoning_effort = "medium"
```

### Cross-harness bridges and larger coordination layers

The bidirectional **cross-model-agent-delegation** repository supplies concrete Claude↔Codex scripts, with task classes controlling model, effort, and execution settings. Its current default selects GPT-6.1 Sol; use its explicit `--model gpt-6-sol` override for this report's Sol comparison. [Repository](https://github.com/alectivism/cross-model-agent-delegation).

Inspect its worker script before adopting it: the Codex command uses `|| true`, and an exit trap prints an output path. Therefore an `OUT=` line is not a successful task outcome. Capture completion status and verify artifacts independently. [Wrapper implementation](https://github.com/alectivism/cross-model-agent-delegation/blob/main/for-claude-code/skills/delegate-to-codex/scripts/codex-run.sh).

**SubSwitch** represents a different route: protocol translation while retaining the originating client's execution loop. Its bidirectional bridge is community infrastructure, not first-party native cross-vendor delegation. **Claude Dialects** maps model tiers through a proxy; its exact Sol mapping is used only when the relevant worker tier is selected. Neither is equivalent to launching a separate CLI harness. [SubSwitch](https://github.com/dean0x/subswitch), [Claude Dialects](https://github.com/stefandevo/claude-dialects#mix-multiple-providers-in-one-session).

**Ruflo**, formerly Claude Flow, adds a broader coordination layer with swarms, memory, federation, and routing. It is worth inspecting when those features are required; its broad performance claims do not establish a controlled current model-pair result. Verify which process actually runs inference rather than treating coordination metadata as worker execution. [Repository](https://github.com/ruvnet/ruflo).

Aider provides historical evidence for a simpler alternative: its 2024 author experiment reports o1-preview architect with o1-mini or DeepSeek editor at 85.0%, versus o1-preview solo at 79.7%; a Claude 3.5 Sonnet editor scored 82.7%. These older edit-benchmark results support testing role separation but do not isolate diversity from the extra call or rank today's models. [Architect/editor experiment](https://aider.chat/2024/09/26/architect.html).

## Connecting separate harnesses

An MCP wrapper can expose a complete worker behind a tool call, but the wrapper still needs to manage its process, model selection, timeout, status, and artifacts. A2A describes remote agents through capability cards and stateful task lifecycles, with messages, artifacts, polling, streaming, or push updates. It can connect agents implemented in different frameworks while keeping their internal state opaque. [A2A concepts](https://a2a-protocol.org/latest/topics/key-concepts/), [A2A and MCP](https://a2a-protocol.org/latest/topics/a2a-and-mcp/).

Neither connection mechanism chooses a good worker or proves its result correct. For a bidirectional Claude/Codex bridge, record the parent model, requested child model, resolved child model, child harness, tool permissions, exit status, and acceptance outcome. An output file or a completed transport request is not sufficient evidence that the delegated task succeeded.

### Hosted orchestration is a separate implementation choice

| Hosted surface | Approach and state | Mixed-model boundary |
|---|---|---|
| Claude Managed Agents | Current `multiagent_20261001` configuration distinguishes reusable subagent threads, model-written background workflows, and advisory consultations. Subagents can receive follow-ups; workflow threads are archived after the run. Contexts are separate but sandbox/filesystem are shared. | Predefined agents retain their model/tool configuration; inline agents inherit the lead's. For a controlled worker comparison, list versioned predefined agents and disable inline creation. Delegation has one level and a 25-child-thread limit. This documents Claude model mixing, not native GPT children. [Guide](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration) |
| OpenAI Agents API | `agent.multi_agent.enabled` supplies spawn/message/wait/interrupt tools; `max_concurrent_subagents` bounds active children. The guide demonstrates an Astra lead, independent contexts, and a shared environment filesystem. | Managed orchestration is established; the opened guide does not establish arbitrary Fable child models. Treat a cross-provider worker as a separately integrated capability. [Guide](https://developers.openai.com/api/docs/guides/agents-api/multi-agent) |
| Responses Multi-agent beta | Request-level multi-agent execution is distinct from the Agents API and the local Codex harness. | Descendants share the request's model/tools. Its current supported list names GPT-6.1 Sol and GPT-5.6 models, so it is not the documented route for the requested heterogeneous pool. [Guide](https://developers.openai.com/api/docs/guides/responses-multi-agent) |

For these hosted surfaces, inspect environment sharing and resume semantics before treating a child as an isolated machine. Separate conversation history is not a filesystem boundary.

## Recent developments worth following

**October 2026 — typed decision endpoints.** OpenAI launched the Decisions API on 6 October; the current public beta supports `gpt-6-luna`. It returns a predicate probability, a selection from supplied choices, or a score over ordered levels. That makes it relevant to narrow routing and triage inside an orchestrator. It does not itself provide a stateful planning loop. [API changelog](https://developers.openai.com/api/docs/changelog), [Decisions guide and examples](https://developers.openai.com/api/docs/guides/decisions).

**September 2026 — orchestration offered as a model product.** Sakana's Fugu Max and Fugu Ultra v2 release follows its earlier trained orchestration system. The release describes Ultra v2 operating without Fable 5/5.1 or GPT-6 Astra in its pool. Its benchmark and price claims concern a complete proprietary system; they do not isolate the effect of heterogeneous workers or answer the exact Fable pairing question. [September release](https://sakana.ai/fugu-max-release/), [June technical report](https://arxiv.org/html/2606.21228v1).

**May 2026 — controllers trained with their actual tools.** Microsoft's MagenticBrain is a Qwen3-14B controller trained in the MagenticLite harness, including delegation to the Fara1.5 browser specialist. This is a concrete example of a smaller model learning coordination in its execution environment. [Microsoft release and architecture](https://www.microsoft.com/en-us/research/blog/magenticlite-magenticbrain-fara1-5-an-agentic-experience-optimized-for-small-models/).

## What measured research supports

Numbers below are local to each study's tasks, model versions, tools, and resource policy. They are not a cross-paper leaderboard.

| Study and date | Result most relevant to orchestration | Scope and limitation |
|---|---|---|
| ToolOrchestra, November 2025 | Trained Qwen3-8B scored 37.1/76.3/80.2 on HLE/FRAMES/τ² versus 21.2/57.5/62.3 for GPT-5 with the same expanded toolkit. | GPT-5 with basic tools scored 35.1/74.0/77.7: more available models alone hurt. Up to 50 turns; HLE text-only; reproduced τ² baseline differs from provider results. [Paper](https://arxiv.org/html/2511.21689v1) |
| Conductor, March 2026 revision | A 7B controller learned assignments, model selection, and information flow; controlled four-task average 72.35 versus MoA 62.13 and five-turn GPT-5 reflection 64.52. | Workers had constrained context/reasoning. About three calls under a five-step ceiling. Improvement does not isolate model diversity from orchestration design. [Paper](https://arxiv.org/html/2512.04388v4) |
| Google scaling study, v2 | Across 180 configurations and four benchmarks, architecture gains depended strongly on task. Centralized finance scored .631 versus .349 single-agent; PlanCraft .282 versus .568. | Matched aggregate reasoning tokens, tools, and maximum aggregate iterations; not matched dollars or elapsed time. [Paper](https://arxiv.org/html/2512.08296v2) |
| Self-MoA, February 2025 | Repeated strongest-model proposals achieved 65.7 versus 59.1 length-controlled win rate for a mixed ensemble on AlpacaEval 2.0. | A 6.6 percentage-point difference. Answer aggregation with older models, not interactive coding agents; establishes an essential same-model sampling control. [Paper](https://arxiv.org/html/2502.00674v1) |
| Router-R1, June 2025 | A 3B controller with up to four subquery calls averaged .416 exact match across seven QA sets versus .338 for always selecting the largest worker. | Main accuracy result used zero cost penalty. Increasing cost weight changed the tradeoff. Static QA does not establish repository-task competence. [Paper](https://arxiv.org/html/2506.09033v1) |
| LAMaS, July 2026 | On GSM8K, 93.65% accuracy at 11.73 seconds versus MaAS 93.36% at 48.11 seconds. | Main comparisons use the same GPT-4o-mini backbone. Single generation was faster at 5.43 seconds and less accurate at 87.46%; three runs, static tasks. [Paper](https://arxiv.org/html/2607.13359v1) |
| Controlled workflow evaluation, August 2026 | Largest averaged improvement over chain of thought was 4.6 points. Debate did not significantly beat chain of thought on any domain. | Equal GEPA optimization budgets across five backbones, 200 tasks per domain. Fixed reasoning workflows, not broad tool-using delegation. [Paper](https://arxiv.org/html/2608.00685v1) |
| Anthropic research system, June 2025 | Opus 4 lead with Sonnet 4 workers improved performance 90.2% relative to single Opus 4 on an internal research evaluation. | Architecture and compute changes were not independently isolated. The reported 15× token usage is versus ordinary chat, not versus that single-agent baseline. [Engineering writeup](https://www.anthropic.com/engineering/multi-agent-research-system) |

### Does the strongest model need to lead

The Google study's role ablation is unusually relevant. On BrowseComp-Plus, its within-family high/low pairs were GPT-5/GPT-5 nano, Sonnet 4.5/Sonnet 3.7, and Gemini 2.5 Pro/Gemini 2.0 Flash. A weaker lead with stronger workers scored .42 versus .32 for an all-strong centralized Anthropic team, but mixed-capability centralized teams worsened for OpenAI and Gemini. Strong-worker configurations beat strong-lead configurations across families. This is evidence to test role assignments, not evidence that cheap leads universally win or that cross-vendor Fable teams behave similarly. [Figure 4 and budget definitions](https://arxiv.org/html/2512.08296v2).

### What firsthand Fable writeups add

The July 2026 **fable-baton** experiment held an older Fable 5 root across three tasks and two repeats per condition: 12 successful plugin-on/off runs. In review work, total cost rose $2.13→$2.71 while Fable output fell 13.7k→8.5k; workers included Opus and Haiku. Feature cost was essentially unchanged. This shows why conserving root tokens and saving total money are different outcomes. The sample is small and the benchmark harness is not shipped. [Implementation and benchmark](https://github.com/realgarit/fable-baton#benchmark).

A September operational writeup records 86 spawns, including 33 Opus owners launched by Fable, with evidence-return conventions and depth limits. It is useful implementation telemetry, without a counterfactual worker-model trial. [Practical Systems writeup](https://www.practicalsystems.io/blog/fable-opus-sonnet-claude-code-subagent-routing).

An October writeup separates repricing 245 historical runs from actual experiments over three briefs and 21 arm-runs. Its concurrency lessons are valuable; historical repricing assumes unchanged model behavior, and the actual comparison is Claude-only with an Opus judge. [Benchmark subagent models the way you run them](https://jeanfbrito.github.io/posts/benchmark-subagents-the-way-you-run-them/).

## Smaller decision models and learned routers

There are three different places to economize: route the original request, select the next worker during an episode, or decide whether a result is good enough to stop. They require different training labels and should be evaluated separately.

| Approach | What it learns or returns | Useful starting material |
|---|---|---|
| Preference router | Strong-versus-cheap model choice from the request | RouteLLM's accessible explanation and implementation use historical GPT-4/Mixtral examples; savings depend on the chosen quality threshold and distribution. [Author writeup](https://www.lmsys.org/blog/2024-07-01-routellm/), [paper](https://arxiv.org/html/2406.18665v1) |
| Cascade with acceptance | Whether to accept an answer or pay for another model | FrugalGPT is a foundational example of learned model sequences and acceptance thresholds. Historical prices and benchmark distributions limit direct deployment estimates. [TMLR paper](https://lingjiaochen.com/papers/2024_FrugalGPT_TMLR.pdf) |
| Small policy from partial feedback | Model choice with a tunable cost-quality objective | BaRP combines frozen MiniLM embeddings with small decision/preference networks. Its experiments simulate bandit feedback from full benchmark logs; they are not live online agent trials. [Paper](https://arxiv.org/html/2510.07429v1) |
| Iterative generative controller | Subqueries, worker selection, and synthesis | Router-R1 and ToolOrchestra provide trained-controller examples. Inspect cost rewards and tool pools before adopting headline results. [Router-R1](https://arxiv.org/html/2506.09033v1), [ToolOrchestra code and checkpoints](https://github.com/NVlabs/ToolOrchestra) |
| Typed decision endpoint | Predicate, choice, or ordered score | Decisions exposes a narrow API suitable for dispatch or escalation signals; inspect its request and answer schemas. [API reference](https://developers.openai.com/api/reference/resources/decisions/methods/create) |

For a practical hybrid, begin with application rules for hard requirements such as available tools and budget. Use a learned route for recurring, labeled task classes; reserve a full coordinator for tasks needing decomposition or recovery. Calibrate acceptance and escalation thresholds on held-out outcomes. A model's reported probability is a prediction to validate, not an assurance that a worker will succeed.

A useful routing objective is expected verified utility after worker cost, delay, and failure consequences. “Cheapest model that sounds confident” does not estimate that objective. Collect task features, selected route, actual acceptance result, repair cost, and elapsed time so the route can improve from observed outcomes. This is a proposed engineering policy, not a measured ranking of Fable, Opus, and Sol.

## Cost and latency should be measured per accepted task

Standard API list prices checked on 16 October 2026, in USD per million tokens:

| Model | Uncached input | Cached input read | Output |
|---|---|---|---|
| Fable 5.1 | $10 | $0.25 | $50 |
| Opus 5.5 | $4 | $0.20 | $20 |
| GPT-6 Sol | $2 | $0.20 | $10 |

Sources: [Fable](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Opus](https://platform.claude.com/docs/en/models/opus-5-5/overview), [Sol](https://developers.openai.com/api/docs/models/gpt-6-sol). These are not subscription-quota conversion rates. Sol requests above 272K input tokens apply full-request multipliers of 2× to input/cache rates and 1.5× to output. Cache writes, tools, processing tiers, and other deployment premiums need separate accounting.

**Illustrative arithmetic, not benchmark usage:** suppose the entire Fable coordination episode consumes 20,000 uncached input and 4,000 billable output tokens, and four worker jobs each consume 30,000 input and 6,000 billable output tokens. Assume identical token counts across models, no retries or cache hits, and no tool fees or premium rates.

| Component | Opus workers | Sol workers |
|---|---|---|
| Fable coordination | $0.40 | $0.40 |
| Four worker jobs | $0.96 | $0.48 |
| Total | $1.36 | $0.88 |

Under those assumptions, half-price worker input/output produces a **35.3% whole-team reduction**, not 50%. Equal token counts are an artificial simplification; extra worker reasoning, failed attempts, or root repair can reverse the comparison. Equal cached-read prices also mean cache-heavy workloads have a different price relationship.

Use these accounting definitions:

```text
Episode cost = lead + all workers + retries + verification + tools
Cost per accepted task = sum of all episode costs / accepted task count
Elapsed time = time from original task submission to verified completion
```

Include unsuccessful episodes in the numerator. Report cost and latency distributions as well as averages; a low mean can hide expensive recovery or missed deadlines. For parallel work, the slowest dependency chain and synthesis step determine completion time, so summed worker durations are not wall-clock latency.

## How to compare the expanded permutation set

The requested matrix is a **two-lead × six-worker design**—Fable or Astra leading Opus, Sonnet, Haiku, Sol, Terra, or Luna—plus Fable→Astra and Astra→Fable. Treat advisory calls and full executable workers as separate conditions. Otherwise a cheap verdict and a long-running implementation appear to be comparable samples when they are not.

| Comparison | What stays fixed | What it reveals |
|---|---|---|
| Worker substitution | Lead, assignment, tools, context, harness, acceptance | Which worker fits that lead's handoffs |
| Lead substitution | Worker pool, task, worker count, tools, limits | Routing, decomposition, follow-up, and reconciliation quality |
| Harness substitution | Model IDs, task, acceptance, resource policy | Value of execution loop, context strategy, persistence, and tools |
| Advisory versus delegated execution | Task and success criterion; report modes separately | Whether expensive reasoning is needed for a judgment or for the whole tool loop |
| Dynamic routing versus fixed assignment | Same available pool and budget | Whether the selection policy earns its overhead |

Start with identical frozen delegation packets to diagnose worker quality, then run complete adaptive episodes. For each lead, compare the same worker under the same operational conditions. Include solo Fable, solo Astra, relevant solo workers, same-model delegation, repeated same-model samples, and a fixed-workflow baseline. Changing lead, worker, and harness together is a deployment comparison, not an isolated model effect.

Separate provider-default operation from dollar-capped and deadline-capped experiments. Equal token counts or effort labels do not equal compute. Test the single-model effort curve before concluding that a second model is necessary. For the bidirectional high-end pairs, begin with bounded consultations and separately test full execution if that is the intended deployment.

The original evaluation method below remains applicable across the expanded matrix.

## Evaluation tasks and outcome measures

### Choose tasks and endpoints that reflect real use

A 20–30 task pilot with repeated paired runs can expose large failures and estimate variance; it is not enough to confidently rank close systems. Build a larger held-out set according to the smallest useful quality difference. Include research, implementation, review, and synthesis only in the proportions the application actually needs. Stratify independent versus tightly dependent tasks and short versus long contexts. Keep prompt tuning separate from the held-out test.

Prefer executable checks or final-state validation. For prose, use a task-specific rubric, blinded identities, randomized answer order, and human calibration of any model judge. A judge from one candidate family can introduce a systematic preference; measure that risk rather than assuming blindness removes it. Anthropic's evaluation guide is a readable starting point for grader design and the distinction between at-least-one-success and repeated reliability. [Agent evaluation guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

Evaluate operational defaults and budget-constrained conditions separately. Sweep whole-episode dollar caps and, separately, deadlines. Counterbalance run order over time; repeat tasks to observe variability. Record model versions, prompts, tool schemas, provider endpoints, timeouts, and resource settings. Infrastructure is a real confound: Anthropic measured a six-percentage-point spread across Terminal-Bench 2.0 resource configurations while holding model and harness fixed. [Infrastructure study](https://www.anthropic.com/engineering/infrastructure-noise).

### Record failures that an average score conceals

The primary endpoint should be verified end-to-end success. Also track cost per accepted task, unconditional cost, p50/p95 latency, deadline success, human intervention, regression rate, retries, transport errors, unnecessary delegation, and root-versus-worker usage. Preserve failure examples with their assignment and acceptance checks.

Distinguish poor decomposition, insufficient worker context, execution failure, a correct result rejected by the lead, an incorrect result accepted by the lead, and premature stopping. MAST's 1,642-trace study across seven frameworks offers a useful failure taxonomy, including context loss, repetition, and verification failures; it does not rank current model pairings. [MAST study](https://arxiv.org/html/2503.13657v3).

## Practical starting configurations

These are implementation-fit hypotheses, not measured model rankings:

- **Compare the models within one coding runtime:** OpenCode's explicit per-agent model configuration is a useful starting point. Keep tools, context policy, permissions, and worker role fixed.
- **Compare complete vendor coding systems:** use a transparent Claude↔Codex wrapper and label the result model-plus-harness. Pin exact IDs and require explicit completion evidence.
- **Compare expensive judgment in both directions:** test Fable→Astra and Astra→Fable as bounded advisor calls, then evaluate full workers separately.
- **Coordinate stable dependencies and acceptance checks:** use an explicit LangGraph or ADK workflow. Code owns joins and retry boundaries; a model may still generate assignments.
- **Allow adaptive planning and recovery:** test manager-as-tools against Magentic's richer progress/stall loop. Count manager calls and unnecessary replanning.
- **Keep persistent local child sessions:** evaluate a named Pi extension or another harness with documented child lifecycle; do not infer it from a “swarm” label.
- **Separate planning from patch formatting:** Aider's architect/editor mode provides a narrower serial experiment than a full multi-worker system.
- **Route repetitive traffic cheaply:** evaluate a small learned router or decision endpoint, with measured escalation and acceptance. A full lead need not participate in every request.

## Search vocabulary and coverage

The expanded pass searched directions separately, then varied both role names and system descriptions. The companion search log records actual query strings and classifications; these examples illustrate the breadth used:

| Search dimension | Variants used | Representative issued query |
|---|---|---|
| Lead role | orchestrator, coordinator, supervisor, manager, lead, controller, planner | `"Astra" "Fable" (manager OR lead OR controller) (delegation OR routing)` |
| Delegated role | subagent, worker, specialist, executor, advisor, editor | `"Astra" "Opus" (worker OR subagent OR executor)` |
| Mixed composition | cross-model, mixed-model, heterogeneous, polyglot, cross-provider | `"Fable" "Astra" ("cross-model" OR "mixed-model" OR heterogeneous OR polyglot OR "cross-provider") delegation` |
| Exact generation | model IDs instead of family labels | `"gpt-6-astra" "claude-haiku-5-5"` |
| Role split | architect/editor, planner/executor, conductor/worker, boss/worker | `site.aider.chat architect editor model architect mode` |
| Control topology | handoff, swarm, graph, workflow, group chat, blackboard | `site:learn.microsoft.com agent framework blackboard orchestration shared state` |
| Runtime behavior | checkpoint, resume, cancellation, concurrency, budgets, worktree | `site:strandsagents.com swarm graph workflow limits cancellation checkpoint` |

The search rejected standalone model comparisons as evidence of directed delegation, latest-model aliases as proof of exact GPT-6 Sol, and a list of supported workers as proof that Astra actually supervised them. Stale snippets were checked against opened README/docs content. Shared names also produced mythology, poetry, and unrelated software results; those were excluded.

See the [search log](model-orchestration-search-log-2026-10-16.html) for the full pairing queries and framework/harness search traces. Negative findings mean “not located in this investigation,” not proof that an implementation or study does not exist.

## Prioritized reading and implementation path

| Priority | Source | Why begin here |
|---|---|---|
| 1 | [Replit harness design](https://replit.com/blog/free-the-models) | Readable production explanation of worker type, tier, reuse, and effort |
| 2 | [Anthropic cost and intelligence guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) | Advisor and orchestrator measurements with explicit limitations |
| 3 | [A Fable of Codexes](https://github.com/jvogan/a-fable-of-codexes/blob/main/README.md) and [fables](https://github.com/czlonkowski/fables/blob/main/README.md) | Concrete directional role definitions; inspect current IDs and advisor boundaries |
| 4 | [Multimodels benchmark](https://github.com/dpmadsen/multimodels-mcp/blob/main/benchmark/README.md) | Historical prompts, responses, and graders behind a multi-worker comparison |
| 5 | [OpenCode agents](https://opencode.ai/docs/agents/) | Minimal explicit model selection in a common execution harness |
| 6 | [LangGraph workflows](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Orchestrator-worker, graph, and evaluator control patterns |
| 7 | [DeepAgents subagents](https://docs.langchain.com/oss/python/deepagents/subagents) | Added harness behavior beyond a raw graph |
| 8 | [PydanticAI delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/) | Compact typed Python call-and-return implementation |
| 9 | [Microsoft Magentic](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic) | Adaptive plan, progress, stall, and reset mechanics |
| 10 | [Pi subagent extension](https://github.com/badlogic/pi-subagent) | Process/session lifecycle rather than only prompt-role abstractions |
| 11 | [Aider architect experiment](https://aider.chat/2024/09/26/architect.html) | Simple historical directional pairing with same-model controls |
| 12 | [Codex MCP cookbook](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk) | Official example of exposing a full coding harness as a tool |

**Method and limits.** Three parallel GPT-6.1 Sol agents expanded the pairing, framework, and harness searches; the main agent consolidated findings and checked additional primary sources. Access date is 16 October 2026. Living docs and repository defaults can change. Exact-current configurations, author observations, historical experiments, and proposed designs are separated throughout. This is web research: no model-pair trials, installations, or paid provider calls were performed. Configuration and pseudocode examples are unexecuted; their references are the implementation starting points.
