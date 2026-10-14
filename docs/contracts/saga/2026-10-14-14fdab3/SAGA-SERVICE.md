# Saga service contract

> **Contract:** `saga-service`, version `0.1.1-draft`. **Status:** draft;
> a proposed target API for Saga service v1 (Phase B), not a description
> of running software. `0.1.0-draft` was the first extraction;
> `0.1.1-draft` applies the corrections from the producer-side source
> review of 2026-10-14 (findings B3 to B6 and implementation gates G1 to
> G7; §18) and has not yet been re-reviewed. Nothing in this document is
> implemented, no schema exists for it, no runtime or conformance test
> has run, and no release is recorded in Saga's release table (Saga
> `docs/contracts/README.md`).
>
> **Extracted:** 2026-10-14 from Saga commit
> `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada` (clean working tree).
> **Frozen source:** the capture at
> `docs/history/saga-extraction/2026-10-14-14fdab3/` already exists,
> byte-verified against that commit (§20); it is the handoff
> `2026-10-14-14fdab3`. **Live decisions:** Saga `docs/DECISIONS.md`.

**Authority.** This is Saga's canonical producer contract for the Saga
service: its API, identities and authorization, run admission with
approval and reviewer binding, run lifecycle and verification, the
event cursor, operation idempotency and unknown outcomes, stop,
revocation and recovery, action authority, and the worker transport.
Precedence:

1. Saga's live decision record wins over this contract. A conflict is
   corrected here, with a new contract version.
2. For Saga's behaviour, this contract wins over every consumer
   document: Odin's design in any repository, any pinned copy of this
   contract, any adapter. A consumer requirement not stated here is a
   request to the producer, not an obligation of Saga.
3. The frozen source documents are provenance. They show where each
   requirement came from; they add nothing, and later edits to them or
   to a consumer's live design do not change this contract.

**Self-contained.** Every requirement is restated here in full. Source
references (§20) are for provenance and review, never needed to know
what Saga must do. Decision numbers `D0` to `D24` are the legacy
identifiers `SAGA-2026-10-D0` to `SAGA-2026-10-D24` of the joint
decision record as frozen at the base commit.

**Names.** `DECISIONS.md` D13 applies: "worker" and "run", not the
legacy "dvergr" and "instance"; "Saga's launcher" for the component
whose current file is `odin/scripts/heimdall.py`; "Saga events" for
the component whose current file is `odin/scripts/ratatoskr.py`. Legacy
names appear here only in current paths, topics and quoted sources.

## 0. Reading this contract

### Status labels

Every requirement carries one label. The label says how settled it is,
not whether it is built: nothing here is built.

| Label | Meaning | Who may change it |
|---|---|---|
| **Locked** | Stated by a locked decision (`D`-number given) | The operator, by amending the decision record; this contract follows |
| **Default** | Stated by a default decision; locked unless the operator objects | As Locked |
| **Specified** | Stated as a Saga obligation in the frozen design documents (most of it written from the consumer side), not ratified by a decision of its own. The current requirement for Phase B design | The producer, by a recorded Saga decision and a new contract version that consumers re-pin |
| **Proposed here** | Introduced by this extraction to close an obvious hole or to state the reading this document takes of a source. Not binding until accepted by producer review | The producer review |
| **Open** | Unresolved; the question is stated, with the gap id from §18 | Must be decided before the dependent wire detail is frozen |
| **Current** | Behaviour of the April 2026 implementation at the base commit. Describes the facade's starting point; never a target | Replaced in Phase B |

Requirement identifiers (`ADM-3`, `MQ-5`, …) are stable within this
contract and never reused; a withdrawn requirement keeps its id and is
marked withdrawn. "Must" is used for Locked, Default and Specified
requirements, "should" for Proposed here.

### What this document is not

It is not an implementation, a schema, or evidence of behaviour. Where
a wire detail (a field type, an error code, a page size, a header) is
unspecified in the sources, this contract says so and records the gap
instead of supplying a plausible value. Examples marked *verbatim from
source* are reproduced byte for byte to show field names that the
design already uses; they are not schemas and their placeholder values
(`"..."`) are not formats.

## 1. Scope, boundary and guarantees

**SCOPE-1** · Locked (D0). Saga executes delegated agent work with
durable state, enforced permissions, resource limits and recorded
outcomes. Deployment is described as locally operated state and
execution with hosted inference, never as "self-hosted".

**SCOPE-2** · Locked (D1). Saga is a governed execution service: it
starts workers in isolated environments, keeps the run ledger and the
delegation records, enforces admission, action authority, limits and
approvals, survives failures, and exposes an API any orchestrator can
use. It owns runs, workers, images and hooks, policy, events,
delegation records, Bragi and Eir.

**SCOPE-3** · Locked (D1, D3). Orchestrators reach Saga only through
the Saga service API (§7). The orchestrator contract is that API:
submit a run and get a durable run id; read status, results and
evidence; send guidance; cancel; consume events from a resumable
cursor; request a review or a maintenance task; read and propose
changes to delegation records. Odin is the first client, a CLI the
second (it proves the API), an existing agent the third.

**SCOPE-4** · Locked (D1, D7, D17). Saga does not own an
orchestrator's commitments, memory, assignments, planning sessions,
operator channels, wake policy or review coordination. Saga keeps
authority and execution state; the orchestrator keeps its model of the
work. Saga treats orchestrator identifiers it is given (an assignment
id, for instance) as opaque references.

**SCOPE-5** · Locked (`CLAUDE.md` critical constraint 1, D2). Agents
never get the Docker socket. Saga's launcher is the only component
that starts containers and enforces approvals and limits for every
client. No path around it may be added.

**SCOPE-6** · Locked (D23). Saga is the governed default execution
backend and the only backend for work with external effects (pushes to
shared branches, publication, deployments) or needing isolation,
enforced limits, durable run records and recovery. Other backends must
not advertise Saga's guarantees; a desktop backend (D21) is not a
Saga-admitted container.

### Guarantees in one list

Each is detailed in the section given. Status is that of the
guarantee itself; the wire detail behind several is still open.

| # | Guarantee | Status | Section |
|---|---|---|---|
| G1 | A submitted run has a durable id; a lost client connection does not lose it and a client restart does not restart its worker | Locked (D1) | §5, §13 |
| G2 | A retried submission does not launch a duplicate | Locked (D1, D6) | §9 |
| G3 | Every client meets the same admission rules and is refused for the same reasons | Locked (D2, D15) | §4 |
| G4 | Admission requires the exact approved artifacts by hash, a verdict bound to the submission where review is required, and an operator authorization bound to what was shown; neither an orchestrator nor a decision model can manufacture either | Locked (D2, D9); operator-principal mechanism Open (GAP-02) | §2, §4 |
| G5 | Admission never implies authority; a run gets repository-scoped credentials and only the secrets its delegation names | Locked (D2) | §14 |
| G6 | `accepted` and `started` never mean success; `verified` is judged from evidence | Locked (D5) | §5, §6 |
| G7 | The ledger is authoritative, with a monotonically increasing event sequence from which a client can rebuild its picture | Locked (D4) | §8 |
| G8 | Writes are at-least-once with an idempotency key; an uncertain outcome is recorded as `unknown`; nothing claims exactly-once | Locked (D6) | §9 |
| G9 | Stop has distinct operations, a delegation-wide stop and a global kill switch, and reports uncertain outcomes as uncertain | Locked (D2); report Specified | §12 |
| G10 | A worker can publish and read only its own run's topics, in the permitted direction | Specified | §15 |

## 2. Identities and principals

### Identifiers

| Identifier | Minted by | Status | Notes |
|---|---|---|---|
| Run id | Saga, at submission | Locked that it exists and is durable (D1); format Open (GAP-05) | One execution attempt of a stream by a worker (D13) |
| Submission request id | The client, preallocated before review and staging (ID-4) | Specified: a ULID, and it *is* the submission's operation id | Source examples in other formats are historical and nonconforming (INC-01) |
| Operation id | The client, once per logical operation, reused unchanged on every retry | Specified | Sent as `Idempotency-Key: <operation_id>` on every write (§9) |
| Delegation id and version | Saga | Locked (D17: versioned) | Version increments on every accepted change (Specified) |
| Approval id | Open who mints | Specified as a record | §3 |
| Verdict id | Open who mints | Specified: a submission carries it | §3, §4 |
| Human request id (`request_id`, also "rid") | The worker that raises it | Specified | Uniqueness scope Open (GAP-05) |
| Request revision | Saga | Specified: an answer is bound to it | §11 |
| Ledger event sequence | Saga | Locked (D4): monotonically increasing | Density Open (GAP-11) |
| `guidance_rev` | Saga, per run | Specified | Carried in every guidance publication (§10, §15) |
| Evidence reference | Saga | Specified as a concept; format Open (GAP-21) | The design's examples use `evid:...` |
| Container name | Saga's launcher | Current: `saga-<project>-<instance>` | Target derivation Open (§9, SAGA-9) |
| Project and stream names | Client | Current: `^[a-z0-9][a-z0-9-]{0,31}$` | |

Field types the design uses throughout: identifiers as ULIDs where the
owning service mints them, timestamps as ISO-8601 UTC, digests as
SHA-256 hex, revisions as integers starting at 1. That convention is
Specified for the design's own records. The submission request id is a
ULID (ID-4); whether Saga's run ids and worker request ids are ULIDs is
Open (GAP-05).

**ID-4** · Specified (D2 read with the operation-id rule of §9;
resolves INC-01 and review finding B6). The client mints the submission
request id once, as the ULID operation id of the intended submission,
*before* the artifacts are reviewed and staged, because the verdict
(D2: "bound to the request id") and the operator approval must name it
before submission. Staging, the review request, the approval request,
the final `POST /runs` and every retry of it carry that same value;
Saga never mints or rewrites it. A restart (LC-6) is a new attempt with
a new identity: the client mints a new submission request id, and every
binding that names the old id (the verdict, and the approval's coverage
of the submission) must be renewed for the new one before Saga admits
it. Whether an unchanged-digest restart can be covered without a fresh
model review is Open (GAP-07, GAP-08; implementation gate IG-3).

### Principals

| Principal | What it is | How it authenticates | Status |
|---|---|---|---|
| Operator | The human | **Open** (GAP-02). The design verifies the operator in the client's service code (a sender allowlist on the chat channel) and then forwards the grant to Saga; no source says how Saga itself verifies that an approval or answer came from the operator | Open |
| Orchestrator client service | Code that calls the API on an orchestrator's behalf: Odin's service, the Saga CLI, a later third-party agent's adapter | A Saga credential held by the service process; mechanism Open (GAP-01) | Specified that it exists |
| Orchestrator model | The model turns of any orchestrator | Never holds a Saga credential, the reviewer key or a channel token; reaches Saga only through tools run by its client service | Specified |
| Reviewer (Mimir) | The review agent | An identity key held by the hosting service and used on Mimir's behalf, never exposed to the orchestrator's turns; Saga verifies it | Locked (D2); key scheme Open (GAP-03) |
| Saga events | Saga's internal events module | Internal to Saga | Specified |
| Saga's launcher | Saga's internal launcher module; sole holder of the Docker socket | Internal to Saga | Locked |
| Worker run | One run's worker in its container | Per-run broker credentials, username = run id; never reaches the API socket | Specified |
| Bragi | Saga's compiler agent | Read access to the ledger and delegation records; mechanism Open | Locked that it reads them (D12) |
| Decision models and evaluators | Any System One model or evaluator | None. Their outputs cannot satisfy an approval requirement or waive a required review, and nothing in Saga's enforcement path calls one | Locked (D9) |

**ID-1** · Locked (D2). Verdicts are written to Saga's ledger only
under the reviewer's identity key, which Saga verifies. Mimir reviews
quality and reasoning; Saga enforces authority. Sharing a process with
the orchestrator is an operational convenience, not a security
boundary.

**ID-2** · Locked (D2, D9). An orchestrator must not be able to
manufacture its own approval or verdict, and a decision model's output
is never accepted as either. For verdicts this is ID-1. For operator
approvals the property is required but the mechanism is Open
(GAP-02): with client-service credentials alone, any client service
holding a Saga credential could record an approval for its own
submission, and the model is excluded only because it holds no
credential.

**ID-3** · Locked (D24) that secrets never appear in prompts,
histories, briefings or exports. Proposed here, as Saga's reading of
that rule: secret values never appear in the ledger, events, evidence,
results or logs. Current: Saga's launcher injects values at `docker
run` and does not log them.

### Authorization by operation

Derived from the sources cited in §7. "Client" means an authenticated
orchestrator client service.

| Operation | Permitted principal | Status |
|---|---|---|
| Submit a run | Client | Specified |
| Read runs, evidence, requests, events, operations | Client; Bragi (ledger and delegation records); the operator interface | Specified; read scoping per client Open (GAP-01) |
| Publish guidance | Client; routine guidance after Saga's mechanical checks, material guidance only with a bound verdict (GD-3) | Default (D8); policy representation Open (GAP-10) |
| Cancel a run | Client; operator | Specified |
| Answer a run's request | Operator; a client only for `clarification` requests where the delegation permits planner answers | Specified; principal distinction depends on GAP-02 |
| Record a verdict | Reviewer key only | Locked (D2) |
| Record an approval | Operator principal only | Locked in intent (D2); mechanism Open (GAP-02) |
| Create or change a delegation | Operator-approved; a client may only propose | Specified (D17: changes go through the operator) |
| Stop a delegation; kill switch | Operator; a client relaying an operator command; the Saga CLI | Specified |
| Record a worker request or consumption acknowledgement | Saga events only | Specified |
| Request a maintenance task | Client | Specified; schema Open (GAP-26) |

## 3. Records owned by Saga

**REC-1** · Locked (D4). Saga's run ledger (SQLite in the Saga
service) is the authoritative record of delegations, submissions,
approvals, states, limits, evidence and events. An orchestrator's own
memory is never consulted to decide whether a run was approved or
completed.

### Delegation

**REC-2** · Locked (D17). A delegation is an ongoing responsibility the
operator has delegated: a first-class, versioned record in the ledger,
above projects and runs. Every run, limit and stop is scoped to a
delegation.

| Field group | Content | Status |
|---|---|---|
| `outcome`, `scope` | What the operator wants kept true, over which repositories, projects or services | Locked (D17) |
| `authority` | Permitted resources and actions: repositories and branches, secrets by name, worker images, network allowances, connectors (none in the first release) | Locked (D17) |
| `limits` | Budget (money, runs, container hours), concurrency, review cadence | Locked (D17); only concurrency is enforced in Phase B (§16) |
| `evidence` | What counts as success for a run and for the delegation's periodic review | Locked (D17) |
| `escalation`, `expiry`, `stop` | When to ask the operator, when the delegation lapses, what `/stop` stops | Locked (D17) |
| Planner answers permitted | Whether a client may answer `clarification` requests | Specified (§11) |
| Review requirement | Which artifacts require a verdict before admission | Open (GAP-09) |

Delegation states (active, revoked, expired, …), the revocation record
and the wire schema are Open (GAP-20). A change is proposed by a client
and applied by Saga only on operator approval, with `version`
incremented (Specified).

### Run

The run record must carry what other requirements depend on. Columns
name the requirement that needs it; none of these is a wire field name
yet.

| Information | Needed by | Status |
|---|---|---|
| Run id, submission request id (= operation id, ID-4) | G1, §9 | Specified |
| Delegation id and the version admitted under | REC-2, §12 | Locked (D17) that runs are scoped to a delegation |
| Client principal that submitted | G3, audit | Proposed here |
| Opaque assignment reference | §11 (requests carry it) | Specified |
| Project, stream, image, launch configuration and its `launch_config_digest`, PRD digest | ADM-2, ADM-9 | Locked (D2) |
| Verdict id, approval id | ADM-2 | Specified |
| `depends_on` | LC-4 | Locked (D5) |
| D5 state, with reason; exit code at `terminated` | §5 | Locked (D5) |
| Latest worker status fields, evidence references, limits in force | `GET /runs/{id}` | Specified |
| `guidance_rev` | §10 | Specified |
| Predecessor run when the submission is a restart | LC-6 | Specified |

### Approval

**REC-3** · Specified. Saga holds the authority-bearing approval
records (plan approvals, delegation changes); a client keeps its own
copy as a record. An approval names the verified principal, the
specific request id and revision it answers, the proposal digest it
binds, the source event, the channel, received and expiry times, and a
state. *Verbatim from source* (the design's record example):

```jsonc
// Approval (Saga authority; Odin record)
{ "id": "...", "request_id": "...", "request_rev": 2,
  "principal": "operator:telegram:123", "proposal_digest": "...",
  "source_event": "telegram:cb:98765", "channel": "telegram",
  "received_at": "...", "expires_at": "...", "state": "granted" }
```

The approval state set (only `granted` appears), the default expiry
and the principal format are Open (GAP-07, GAP-02).

### Verdict (review record)

**REC-4** · Locked (D2, D8) for identity and results; Specified for
fields. Saga stores the verdict; review coordination (when to review,
building the evidence pack) belongs to the client. A delivered verdict
carries `request_id`, `type`, `result` ∈ `APPROVE_UNCHANGED | APPROVE
| FLAG | REJECT | INSUFFICIENT_EVIDENCE`, `checklist`, and `findings[]`,
each finding with `evidence`, `consequence`, `minimal_correction` and
`citations`. One review and at most one corrective re-review per
artifact, then the operator decides (D8). *Verbatim from source*:

```jsonc
// Review (Odin coordination; Saga verdict record)
{ "id": "...", "type": "decomposition", "artifact_lineage": ["..."],
  "evidence_pack_digest": "...", "reviewer": "mimir", "round": 1,
  "verdict": { "result": "FLAG", "checklist": {}, "findings": [] }, "usage": {} }
```

The two source shapes differ (flat fields in the delivery, a nested
`verdict` object in the record; INC-09). Review types named in the
sources: `decomposition`, `prd`, `guidance`, `patch_review` (Current
filename prefixes); D8 names decompositions, shared-interface and
contract changes, material guidance, Eir patches and principle changes.
The type enumeration is Open (GAP-08).

### Human request raised by a run

**REC-5** · Specified. When a run raises a structured request for
operator input, Saga owns the record: Saga events records it in the
run's evidence, emits a run event, and accepts the answer and the
consumption acknowledgement. A client holds a projection. Requests a
client raises itself are the client's records, except
authority-bearing ones, which Saga holds as approvals (REC-3).
*Verbatim from source*:

```jsonc
// HumanRequest (Saga-owned when raised by a run; Odin-owned when raised by ask_operator; the other holds a projection)
{ "id": "...", "rev": 1, "assignment": "...", "run": "...", "kind": "clarification",
  "question": "...", "options": ["A", "B"], "authorizes": "...", "proposal_digest": null,
  "recipient": "operator", "expires_at": "...", "state": "delivered",
  "response": null, "channel": null }
```

Lifecycle and protocol in §11.

### Operation record

**REC-6** · Specified. Saga keeps a record per operation id: state
(`pending`, `completed` with the original receipt and the resource it
produced, `failed`), kept for at least 30 days and never expired while
its run or request is open (§9). Wire schema Open (GAP-12).

### Evidence

**REC-7** · Specified. Saga's evidence store holds, per run: full
journal entries, test output, commits, plateau signals, and the run's
structured requests, read through `GET /runs/{id}/evidence`. Kinds,
reference format, capture of test output and retention are Open
(GAP-21). Current: workers publish a status JSON and a Markdown journal
per iteration; no test output is captured beyond the pass and fail
counts in the status.

### Ledger event

**REC-8** · Locked (D4) that events exist with a monotonically
increasing sequence; envelope Open (GAP-11). See §8.

## 4. Run admission, approval binding and reviewer binding

**ADM-1** · Locked (D2, D15). Admission is enforced by Saga, outside
any orchestrator's trust boundary, identically for every client. The
Phase B exit test is that the CLI is refused for the same reasons Odin
would be.

**ADM-2** · Locked (D2). At submission Saga validates:

1. the launch configuration against a schema and allowlists;
2. the exact approved artifacts by hash: the PRD, the launch
   configuration, the Mimir verdict bound to the submission's request
   id where review is required, and the operator authorization bound
   to the hash of what was shown;
3. the delegation's limits: concurrent runs, container TTL, budget,
   operator-presence gate (Phase B enforces concurrency only; §16).

**ADM-3** · Locked (D2; corrected in 0.1.1 per review finding B3).
Every submission carries, and every admission binds, five values:

| Value | Saga's check |
|---|---|
| Submission request id (ID-4) | Equals the operation id of the `POST /runs` |
| `prd_digest` | Equals the digest of the PRD bytes Saga mounts into the worker |
| `launch_config_digest` | Equals the digest of the launch configuration Saga will start the run with |
| Verdict id, where review is required | A verdict recorded under the reviewer key (ID-1), bound to this submission request id and to the reviewed artifact digests that include this `prd_digest` and `launch_config_digest`, with an admitting result (ADM-7) |
| Approval id | An operator approval (ADM-5) whose `proposal_digest` covers exactly this submission request id, `prd_digest` and `launch_config_digest` |

Saga refuses unless every check holds and limits allow. A digest a
client supplies is a claim: Saga recomputes both digests itself and
never admits on the supplied value alone. The field name
`launch_config_digest` is fixed at contract level; its type and the
canonical encoding of the launch configuration it is computed over are
Open (GAP-04). Proposed here: Saga computes each digest over the exact
bytes it then uses (copy first, hash the copy, mount or launch from the
copy), so nothing can change between check and use.

**ADM-4** · Specified. A refusal is a `409` response carrying the
reasons. The refusal-reason catalogue, the status code for each class
(schema, authorization, binding, limit), and whether every failing
check is reported or only the first are Open (GAP-06).

**ADM-5** · Specified. Approval checks, in code, never by a model: the
approval answers the specific request id and request revision; its
principal is the operator (GAP-02); it has not expired; its proposal
digest still equals the digest of the artifact submitted. A modified
proposal needs a new request, and an earlier response can never
approve new content. A request reissued for unchanged content has a new
request id, and its answer is applied, not discarded as a duplicate of
the expired one, because the digest still binds the content.

**ADM-6** · Locked (D8, D9) and Specified. Where review is required, a
missing, disabled or unavailable reviewer is never a waiver: the
submission is refused or waits, and the gap is recorded. A decision
model's output cannot satisfy an approval requirement or waive a
required review.

**ADM-7** · Open (GAP-08). Which verdict results admit. The sources
say `APPROVE_UNCHANGED` and `APPROVE` proceed and `REJECT` does not;
`FLAG` goes to the operator; `INSUFFICIENT_EVIDENCE` is a result
without a stated admission consequence. Whether `FLAG` plus an operator
approval admits is Open.

**ADM-8** · Locked (D2) that the coverage in ADM-3 is exact; envelope
Open (GAP-07, GAP-08). A plan approval and a decomposition verdict
cover several runs, while admission checks one submission. The
multi-run approval envelope (how one approval or one verdict covers
several submissions) is not decided. Proposed here: the approval binds
a plan manifest digest whose manifest lists, per submission, the
submission request id, `prd_digest` and `launch_config_digest`; Saga
checks the submission's membership; a verdict likewise names the
request ids and artifact digests it reviewed. Until the envelope is
decided, Saga fails closed: a submission whose coverage by an approval
or verdict Saga cannot verify mechanically is refused, never admitted
on a client's assertion.

**ADM-9** · Locked (D2; resolves INC-02). `launch_config_digest` is a
required submission value (ADM-3). The design's submission tool
signature omits it; D2 governs, and the consumer's signature is
corrected on its side. Its canonical
encoding is Open (GAP-04) and must be decided before the `POST /runs`
schema (GAP-06) is frozen.

**ADM-10** · Specified. The validation Saga uses at admission is
available to clients, so a client's local pre-check applies the same
rules. A pre-check is feedback only; it never substitutes for admission
and its result is never trusted by Saga. Whether that is a shared code
module or a published schema a client validates against is Open
(implementation gate IG-4); a client in another repository must not
depend on Saga's unpublished code.

**ADM-11** · Default (D8). Mechanical checks precede model review:
byte-identical contract quoting, dependency cycles, approval and
artifact hashes, declared secrets, git workflow presence. Which of
these Saga runs at admission, beyond the hash checks of ADM-2, is Open
(GAP-08).

**ADM-12** · Open (GAP-16). Concurrency: whether a submission beyond
the delegation's concurrency cap is refused or admitted to `queued`,
and whether a global host cap also exists. Whether an approval that
expires while its run is `queued` still admits it to `started` is Open
(GAP-07).

## 5. Run lifecycle

**LC-1** · Locked (D5). Run states:

```text
submitted → accepted → queued → started → terminated → verified | failed → closed
side states: cancelled, limit-paused
```

`terminated` records the exit code and reason. `verified` or `failed`
is judged from evidence (§6). The launcher's former `approved` becomes
`accepted`/`started` and never means success.

| From | To | Trigger | Status |
|---|---|---|---|
| (none) | `submitted` | Submission recorded under its operation id | Locked (D5) |
| `submitted` | `accepted` | Admission passed (§4) | Locked (D5) |
| `accepted` | `queued` | Waiting on `depends_on`, a limit, or capacity | Locked (D5); whether `queued` is always entered is Open (GAP-13) |
| `queued` | `started` | Container started by Saga's launcher | Locked (D5) |
| `started` | `terminated` | Worker exited; exit code and reason recorded | Locked (D5) |
| `terminated` | `verified` or `failed` | Evidence judged (§6) | Locked (D5) |
| `verified`, `failed` | `closed` | Close trigger Open (GAP-13) | Locked (D5) that `closed` follows |
| any non-terminal | `cancelled` | Cancel or stop (§12) | Locked (D5) as a side state; exact source states Proposed here |
| `queued`, `started` | `limit-paused` | A limit reached, including the account's quota (D24: queue or pause, never a silent paid fallback) | Locked (D5) as a side state; entry and exit conditions Open (GAP-13) |

A refused submission is not a D5 state; how a refusal appears in the
ledger and in the operation record is Open (GAP-13).

**LC-2** · Locked (D5). A false completion report is a defect of the
evidence rules and is tracked as a measure (D18).

**LC-3** · Specified. Worker status values (`running`, `paused`,
`completed`, `max_iterations_reached`, `failed`, `rate-limited`) and
plateau signals are the worker's claims, carried as status fields and
evidence; they never set a D5 state by themselves.

**LC-4** · Locked (D5). `depends_on` waits on `verified`. A crashed,
failed or cancelled prerequisite never satisfies a dependency. What a
dependent does when its prerequisite reaches `failed` or `cancelled`,
and whether a dependency names a stream or a run (a restart creates a
new run), are Open (GAP-15).

**LC-5** · Specified. A run held on a dependency or limit is visible as
`queued` with its reason, in the ledger and to every client,
immediately; it never waits silently (Current defect: no result for up
to 24 hours).

**LC-6** · Specified. Restart is a new submission referencing the old
run; there is no restart action on an existing run. It carries a new
submission request id and renewed bindings (ID-4); a retry of the
original submission is not a restart. The referencing field is Open
(GAP-13).

## 6. Verification

**VER-1** · Locked (D5). `verified` and `failed` are judged from
evidence: success criteria, tests, the pushed branch, and, where
configured, a verdict.

**VER-2** · Specified (Phase B minimum). `verified` requires the run's
success criteria matched to evidence and the stream branch pushed.

**VER-3** · Locked (D15). Phase D adds evidence rules for `verified`
per project type, and false completion reports are measured.

**VER-4** · Specified. None of these is verification: a worker's
`completed` status or `completion-likely` signal, container exit code
0, `accepted` or `started`, a workspace reporting a session as done or
ready for input.

**VER-5** · Specified. `verified` is per run. Saga does not judge
whether a project, commitment or integration is complete; a client may
keep a larger objective open after all its runs are verified.

**VER-6** · Open (GAP-14). How the Phase B minimum is evaluated: the
machine-readable form of a run's success criteria (today they are prose
in the PRD), who performs the match (deterministic check, reviewer,
operator), which remote, ref and commit count as "pushed", and how test
output becomes evidence.

## 7. API surface (Phase B)

**API-1** · Specified. Local HTTP over a Unix socket; a client library
wraps it; an MCP adapter over the same API is optional, for other
clients. Workers never reach this socket. The socket path, its
permissions and client authentication are Open (GAP-01).

**API-2** · Specified. Every write is idempotent on a client-supplied
key: `Idempotency-Key: <operation_id>`; for a submission, the request
id is the operation id (§9).

**API-3** · Locked (D13). The file interfaces `launch-requests/`,
`launch-results/` and `commands/` are replaced by this API; `commands/`
and `outgoing-commands/` are deleted.

Endpoints as the design lists them. "Specified" covers the method,
path and purpose; the last column says what is not yet specified.
No request or response body below has a schema.

| Method and path | Purpose (Specified) | Caller | Not yet specified |
|---|---|---|---|
| `POST /delegations`, `PATCH /delegations/{id}` | Create or change a delegation; operator-approved; `version` increments | Client proposes; operator approves | Body; how operator approval is attached (GAP-02); whether `PATCH` carries an expected version (Proposed here: yes); states (GAP-20) |
| `POST /runs` | Submit: submission request id (ID-4), assignment, launch configuration, `prd_digest`, `launch_config_digest`, verdict id where review is required, approval id (ADM-3). Saga validates schema, allowlists, digests, bindings, limits; returns the run id; idempotent on the submission request id; `409` with reasons on refusal | Client | Body schema and remaining field names (GAP-06); canonical digest encoding (GAP-04); multi-run approval envelope (GAP-07); response; refusal catalogue |
| `GET /runs`, `GET /runs/{id}` | D5 states, worker status fields, evidence refs, limits in force | Client, operator interface, Bragi | Filters, pagination, field names |
| `POST /runs/{id}/guidance` | Guidance: mechanical checks for routine guidance, a bound verdict for material guidance (GD-3); Saga records it, assigns `guidance_rev` and publishes it internally (GD-2) | Client | Classification and policy representation (GAP-10); body; refusal when run not `started` |
| `POST /runs/{id}/cancel` | Cancel; records `cancelled` with reason; reports uncertain outcomes | Client, operator | Body; outcome report schema (GAP-17) |
| `GET /runs/{id}/evidence?kind=&n=` | Journal entry, tests, commits, plateau signals, requests | Client, Bragi | Kinds enumeration and formats (GAP-21) |
| `POST /runs/{id}/requests` | Saga events records a `needs_input` request relayed from the run's MQTT request topic | Saga events only | Whether this is an internal call rather than a public endpoint |
| `GET /runs/{id}/requests?state=` | Read request state | Client, operator interface | Body |
| `POST /requests/{rid}/answer` | Answer; one answer wins; Saga publishes it on the run's retained answer topic | Operator; client for permitted clarifications | Body (answer, request revision); principal distinction (GAP-02); rid scope (GAP-05) |
| `POST /requests/{rid}/consume` | Saga records the worker's consumption acknowledgement relayed from MQTT | Saga events only | As for `POST /runs/{id}/requests` |
| `POST /reviews` | Record a verdict under the reviewer identity key | Reviewer key | Key scheme and signed bytes (GAP-03); body (INC-09) |
| `POST /approvals` | Record an operator approval bound to a digest | Operator principal | Principal verification (GAP-02); body |
| `GET /events?after={seq}` | Resumable cursor over the ledger | Client, Bragi | Envelope, kinds, paging, retention (GAP-11) |
| `GET /operations/{operation_id}` | Operation lookup: `pending`, `completed` (original receipt, produced resource), `failed`, `superseded` (guidance only; OP-4), `absent`, `unknown_expired` | The client that issued the operation | Body; scoping by client (GAP-12) |
| `POST /stop` | `{scope: delegation or all, operations: [...]}`; reports per-operation outcomes | Operator, client relaying an operator command, CLI | Operations enumeration and ownership (GAP-17); report schema |
| `POST /tasks` | Eir maintenance task request | Client | Everything beyond the purpose (GAP-26) |

Operations the decisions require that the endpoint list lacks, all
Open: reading delegations (D3 "read … delegation records"; GAP-20);
requesting a review (D3; INC-03); reporting that a request was
delivered to the operator (§11; INC-06).

**API-4** · Specified. Conflict responses named in the sources: `409`
with reasons for a refused submission; `409 operation_conflict` for an
operation id reused with a different payload (§9). Proposed here:
`409 stale_revision` for a delegation change or an answer whose
expected revision is stale. No other error codes are specified.

**API-5** · Open (GAP-27). API versioning and compatibility
negotiation between client library and service.

## 8. Event cursor and replay

**EV-1** · Locked (D4). The ledger's events carry a monotonically
increasing sequence. A client rebuilds its picture after a restart by
replaying the cursor from the last sequence it recorded. Therefore the
cursor must carry every change a client needs to rebuild run, request,
approval, verdict, delegation and stop state without other reads.

**EV-2** · Specified. `GET /events?after={seq}` returns the events
after `seq` in sequence order. The ledger sequence is Saga's order;
events from different producers have no implied total order with it.

**EV-3** · Proposed here. Ledger events are immutable: reading after
the same `seq` twice returns the same events. Delivery to a client is
at-least-once; the client deduplicates by sequence and commits its
cursor with its processing.

**EV-4** · Specified, from the events a client must react to: run
state changes (each D5 state and side state), refusal at submission,
a run's structured request, recorded verdicts, recorded approvals,
delegation changes, stop outcomes. The consumer-side kind names in the
design (`run.state.accepted`, `run.request`, `review.verdict`, …) are
the consumer's; Saga's own kind names are Open (GAP-11).

**EV-5** · Open (GAP-11). Envelope schema; page size; long-poll or
stream; per-client filtering and read scope; whether sequences are
dense; retention. Proposed here: a request with `after` older than the
retention horizon is an explicit error, never a silent skip.

## 9. Operations, idempotency and unknown outcomes

**OP-1** · Locked (D6). Side effects are at-least-once with an
idempotency key per action; destination deduplication where possible;
an explicit `unknown` outcome is recorded after a crash between action
and record, and reconciled on restart. No component claims
exactly-once. This binds Saga both as a destination of client writes
and as an actor with its own effects.

### Saga as the destination of client writes

**OP-2** · Specified. Every write accepts `Idempotency-Key:
<operation_id>`. An operation id names one logical operation, minted by
the client in the transaction that decided it and reused unchanged on
every retry. For a submission that transaction is the one that decided
to propose the run, before review and staging, so the id already exists
when the verdict and approval bind to it (ID-4). Identity is never
derived from content: two legitimate
operations with identical payloads (the same guidance issued again
later) are two operations.

**OP-3** · Specified. A retried write with the same operation id and
the same payload returns the original outcome and creates nothing new:
a duplicate submission yields one run. A reuse of an operation id with
a different payload fails with `409 operation_conflict` and changes
nothing. How the payload is digested for this comparison is Open
(GAP-04).

**OP-4** · Specified. `GET /operations/{operation_id}` reports:

| Result | Meaning | Client may retry? |
|---|---|---|
| `completed` | Done; returns the original receipt and the resource it produced | No; use the receipt |
| `pending` | Accepted, not finished | No; wait |
| `failed` | Finished unsuccessfully | Per the failure |
| `superseded` | Guidance only: recorded, but a newer `guidance_rev` for the run was delivered first, so Saga will never publish it (GD-4) | No; never republish or resend it |
| `absent` | No record, within the retention window: confirmed absence | Yes |
| `unknown_expired` | The record aged out | No: not confirmed absence; the outcome stays unknown and is surfaced to the operator |

Records are kept at least 30 days and never expired while their run or
request is open. Whether a refused submission is `completed` with a
refusal receipt or `failed` is Open (GAP-13). The `superseded` result
is a design clarification added in 0.1.1 (review finding B5): the
sources require supersession (AC-28) but gave the client no API by
which to learn it. Its status is that of GD-4 (Specified); the result's
name and body are Proposed here until GAP-12 fixes the operation
schema.

**OP-5** · Specified. Uncertain outcomes are reported as uncertain:
cancel and stop report acknowledged and uncertain outcomes separately,
and an operation Saga could not confirm (an unreachable worker, a
`docker stop` timeout) is never reported as success.

### Saga as an actor

Saga's own effects: starting and stopping containers, provisioning and
revoking per-run broker credentials and credential lineages, retained
MQTT publications (guidance, answers).

**OP-6** · Specified. Retained MQTT publications follow the per-topic
revision rule in §15 (MQ-8). They are Saga's effects, not a client's:
a client's guidance or answer operation completes at the API, and the
client learns the publication outcome through `GET /operations` and the
event cursor, never by reading or writing the broker.

**OP-7** · Proposed here. A container's name derives from its run id,
so Docker's name uniqueness deduplicates a repeated `docker run` and a
container can be found by name after a crash. Current: the name derives
from project and instance, so two runs of the same stream collide.

**OP-8** · Open (GAP-19). The reconciliation procedure for each of
Saga's own effects after a crash (§13).

## 10. Guidance

**GD-1** · Locked (D3). A worker reads guidance before each iteration.

**GD-2** · Specified. A client sends guidance with `POST
/runs/{id}/guidance`. Saga records it, increments the run's
`guidance_rev`, and Saga events publishes it as a retained message on
the run's `guidance` topic carrying the operation id and the new
`guidance_rev`. Only Saga events may write that topic. Clients never
publish guidance to MQTT (MQ-1).

**GD-3** · Default (D8); corrected in 0.1.1 per review finding B4,
resolving INC-04. Guidance is not uniformly verdict-bound:

1. *Routine guidance* (guidance that stays within the run's approved
   scope, approach, contracts and success criteria) passes Saga's
   mechanical checks and needs no verdict.
2. *Material guidance* (guidance that changes the run's scope, its
   approach, a contract or interface it must honour, or its success
   criteria) requires a D8 review: a verdict recorded under the
   reviewer key (ID-1), bound to this guidance operation and its exact
   text, with an admitting result (GAP-08).
3. A class label supplied by a client (or by any agent or decision
   model) is never authority. Saga may accept a declared class as
   input, but whether guidance is routine is established by Saga's own
   check against the delegation's policy, never by assertion (D9).
4. Where Saga cannot establish that review is not required, it fails
   closed: it refuses the guidance, or holds it, until a bound verdict
   is supplied. It never publishes on an unresolved classification.
5. `APPROVE_UNCHANGED` on a guidance review means the worker is left
   unchanged; it never authorizes publishing the reviewed guidance
   (Specified, from current practice and the restraint bias of D8).
   The source phrase "or `APPROVE_UNCHANGED` semantics" is withdrawn as
   uncheckable by Saga.

The mechanical definition of "material", the representation of the
policy (delegation field, per project, per review type) and the
binding fields are Open (GAP-09, GAP-10) and must be decided in Phase B
before guidance enforcement is built; points 1 to 5 hold whatever
representation is chosen.

**GD-4** · Specified (AC-28); API exposure corrected in 0.1.1 per
review finding B5. Saga, not the client, reconciles guidance
revisions. A newer `guidance_rev` is never replaced by an older
operation: when an older guidance operation is reconciled after a newer
one was delivered, Saga marks the older one `superseded`, never
republishes it, and reports `superseded` through `GET /operations`
(OP-4) and a ledger event. A client that sees `superseded` does not
retry or resend; it never reconciles by reading the retained MQTT
value.

**GD-5** · Proposed here. Guidance to a run that is not `started` is
refused. Guidance under a revoked or expired delegation: Open
(GAP-18).

**GD-6** · Open (GAP-10). The guidance payload format. Today it is a
raw Markdown string that the worker hooks write to a file; GD-2 needs
the operation id and revision in the payload, which changes the worker
hooks.

## 11. Structured requests for operator input

**RQ-1** · Locked (D3, D20). A worker blocked on a decision raises a
structured request carrying a request id, the assignment, the decision
needed, the options and what answering authorizes, then continues
other work or stops cleanly. The request is delivered directly to the
operator's queue with those fields preserved; the answer returns to
that exact request. A typed request is routed by its type and never
classified by a model (D9).

**RQ-2** · Specified. Wire protocol, worker side. The worker's hooks
write the request as a JSON file in `.dvergr/requests/` (path renamed
with the worker hooks in Phase B) and publish it on
`saga/runs/<project>/<run>/request` with these fields:

| Field | Content | Type |
|---|---|---|
| `request_id` | Worker-minted id | Open |
| `assignment` | The opaque assignment reference the run was submitted with | Open |
| `kind` | `clarification`; the only kind a worker may raise | Specified |
| `question` | The decision needed | Open |
| `options` | The choices offered | Open |
| `what_answering_authorizes` | What an answer permits the worker to do | Open |
| `expires_at` | Expiry | Open |

No complete example payload exists in the sources. In the shadow
period, before the request topic exists, the request is published on
the run's alert topic (Specified).

**RQ-3** · Specified. Saga owns the record (REC-5). Lifecycle:

```text
open → delivered → answered → consumed → closed
terminal: expired, cancelled
```

One answer wins. A later or conflicting answer is recorded as
`rejected_duplicate` and changes nothing. A late answer to a terminal
request is refused. The answer is bound to the assignment and the
request revision; a request re-raised after a plan change is a new
request.

**RQ-4** · Specified. Saga publishes the answer as a retained message
on `saga/runs/<project>/<run>/answers/<rid>`. The worker's
pre-iteration hook reads it and publishes
`saga/runs/<project>/<run>/requests/<rid>/consumed`, which Saga events
records. Nothing outside that run's ACL can read or answer its
requests (§15).

**RQ-5** · Specified. The operator may answer any request. A client may
answer only a `clarification` request, and only where the delegation
permits planner answers; Saga refuses otherwise. Whether the answer
changes the plan is the client's judgment and is not checkable by
Saga.

**RQ-6** · Specified. Clarification answers are distinct from plan
approvals (hash-bound, operator only, REC-3), from Saga authorization,
and from harness permission prompts. An answer never acts as an
approval.

**RQ-7** · Specified. A restricted HTTP worker endpoint may later
replace the MQTT relay; record ownership and lifecycle do not change.

**RQ-8** · Open. Who sets `delivered` (the client delivers to the
operator queue; no endpoint receives that report; INC-06); what moves a
request to `closed`; what cancels a request at Saga (the design ties it
to the client's assignment cancel; Proposed here: cancelling or closing
the run cancels its open requests); default expiry; whether the
retained answer is cleared from the broker after consumption (GAP-22,
GAP-23).

## 12. Stop, revocation and the kill switch

**ST-1** · Locked (D2). Four distinct operations, each an API call and
an operator command:

| Operation | Effect | Executed by |
|---|---|---|
| Pause the planner | No new orchestrator turns except operator messages | The orchestrator's service |
| Stop runs | Cancel the workers of a delegation or project | Saga |
| Disable schedules | Timers and evaluators | The orchestrator's service for its timers and evaluators; Saga for any schedule of its own (GAP-17) |
| Revoke authority | Withdraw the delegation's permissions, so nothing can be resubmitted | Saga |

One operator command, `/stop <delegation>`, performs all four and
reports what it stopped; a global kill switch, `/stop all`, does it for
everything. The operations and the two commands are Locked; the
"Executed by" column is Proposed here, reading D2 against D1's
ownership (an orchestrator's planner, timers and evaluators are not
Saga's), and is confirmed by GAP-17.

**ST-2** · Locked (D15, D20). Stop works without inference and without
the orchestrator: the Phase B exit requires `/stop <delegation>` from
the CLI to stop a whole delegation and report. Saga's part of a stop
must succeed when every orchestrator is down or unresponsive.

**ST-3** · Specified. `POST /stop` takes a scope (`delegation` or
`all`) and the operations to apply, and reports a per-operation
outcome: acknowledged, or uncertain with what is unknown. A lost
connection to a worker or to Docker is uncertain, never success.

**ST-4** · Proposed here. Sequence for Saga's part, chosen so that no
submission can race a stop:

1. Record the stop command durably under its operation id; a repeated
   command returns the first outcome.
2. Revoke or block admission for the scope first. From this commit,
   every submission under the scope is refused.
3. Drop `queued` runs in the scope to `cancelled`.
4. Stop `started` runs; record `cancelled` with reason, or the
   uncertain outcome.
5. Revoke what the runs held (per-run broker credentials; credential
   lineages per D24), recording each.
6. Emit ledger events for every outcome and return the report.

**ST-5** · Locked (D2) in purpose; detail Open (GAP-18). After
revocation nothing under the delegation can be resubmitted. Open:
whether revocation alone (without stop runs) ends running work; whether
guidance and answers under a revoked delegation are refused; the
interplay with D24, which retires a worker's credential lineage when
its delegation is revoked or expires; whether a lapsed delegation
(expiry) behaves as a revocation (Proposed here: yes, for admission).

**ST-6** · Open (GAP-17). Whether the kill switch persists (refusing
all admission until the operator clears it) or acts once (Proposed
here: persists until cleared).

## 13. Recovery

**RCV-1** · Locked (D1). A lost connection does not lose a run;
restarting a client does not restart workers; a retried submission does
not launch a duplicate.

**RCV-2** · Locked (D4) and Specified. After a client restarts, Saga
supports its recovery with cursor replay from the client's last
sequence (§8) and operation lookup for its uncertain writes (§9). Saga
never relaunches a surviving worker because a client restarted.

**RCV-3** · Locked (D11). Three loops with distinct owners: the Saga
service retries delivery, reconciles worker state and enforces
timeouts; the orchestrator decides that work needs different guidance;
Eir changes code, prompts or configuration through reviewed patches.
Eir keeps an operator-invoked path outside Saga's failure domain.

**RCV-4** · Proposed here; the whole procedure is Open (GAP-19).
Saga's own restart:

1. Open the ledger; roll back uncommitted transactions. Admission and
   dispatch stay disabled until step 5.
2. Apply recorded stop, revocation and kill-switch state.
3. Reconcile runs in `queued`, `started` and `limit-paused` against
   Docker by container identity. A container still running stays
   `started`. A container absent without a recorded exit becomes
   `terminated` with reason and exit code unknown; it is never
   `verified` on that basis.
4. Reconcile Saga's uncertain effects: container starts by name
   (OP-7), retained publications by the per-topic rule (MQ-8),
   credential provisioning and revocation.
5. Enable admission and dispatch; resume the queue.
6. Emit a ledger event for every reconciliation outcome.

Current: workers run with `--rm`, so an exit code is lost once the
container is gone; Phase B must capture it (§17).

## 14. Action authority and credentials

**AUTH-1** · Locked (D2). Action authority for the first release:
repository-scoped credentials (push to the stream branch of the named
repository only); no other secrets unless the delegation names them;
network egress as the firewall allows. Any future connector that can
act outside the container (email, purchases, calendar writes,
deployments, desktop input) requires its own enforcement boundary
before any agent is offered it. Admission never implies authority.

**AUTH-2** · Open (GAP-24). The enforcement mechanism for "stream
branch only". Current: Saga's launcher mounts a named Gitea credential
(the persona instructs `saga-push`) as `.netrc`; nothing in this
repository shows it limited to one branch.

**AUTH-3** · Locked (D24), Saga's clauses. Worker credential lineages:
a lineage is one login or one issued token with its own refresh
history. It is established by a separate login or `setup-token` per
worker lineage; persisted in Saga's secret store under the assignment
it serves, so a replacement worker for the same assignment inherits it;
refreshed by exactly one owner; retired when the assignment closes or
the delegation expires or is revoked. Saga's launcher injects the
lineage at `docker run`. Copying one login file into several containers
does not create lineages. After the shadow period nothing mounts a
shared writable credentials directory.

**AUTH-4** · Locked (D24). Quota behaviour: queue or pause when the
selected account reaches its limit; paid API usage only through an
explicitly configured fallback.

**AUTH-5** · Locked (`CLAUDE.md`, "Under re-test"). The April findings
that `claude -p` and `CLAUDE_CODE_OAUTH_TOKEN` force API billing are
under re-test. Until it is recorded, workers stay interactive, and the
Current environment denylist (rejecting `CLAUDE_CODE_OAUTH_TOKEN` and
`ANTHROPIC_API_KEY` in launch requests) stays. AUTH-3's per-worker
`setup-token` depends on the re-test.

**AUTH-6** · Current, to be kept unless a decision changes it:
containers start with `--cap-drop=ALL` plus `NET_ADMIN` and `NET_RAW`
for the firewall; never `--privileged`, host network or host PID; the
image must be on a hardcoded allowlist; secret files must be
root-owned and not group- or world-readable; secret values are injected
at `docker run` and never logged.

## 15. Worker transport (MQTT)

**MQ-1** · Locked (`CLAUDE.md` dependency decisions). MQTT on the
homelab's Mosquitto broker (192.168.86.12) is Saga's internal worker
transport. It is Saga's dependency, not an orchestrator's: clients
reach Saga through the API (§7).

**MQ-2** · Current, kept. The broker is shared; Saga never publishes to
or subscribes from `surveillance/#`, `frigate/#` or `homeassistant/#`.

**MQ-3** · Locked (D13). Run topics move from
`dvergr/{project}/{instance}/…` to `saga/runs/{project}/{run}/…` when
Saga events v1 lands.

**MQ-4** · Specified. Saga's launcher provisions per-run broker
credentials (username = run id), injected like the other run secrets
and revoked at `closed`. The broker mechanism (password file, dynamic
security plugin, other) is Open (GAP-23).

**MQ-5** · Specified. Direction-specific ACL under
`saga/runs/<project>/<run>/`, enforced by the broker:

| Topic suffix | Worker | Saga events | Payload today (Current) |
|---|---|---|---|
| `request` | write | read | (new) JSON, RQ-2 |
| `status` | write | read | JSON, retained, QoS 1 |
| `journal` | write | read | Markdown, not retained, QoS 1 |
| `metrics` | write (INC-05) | read | JSON, retained, QoS 1; today computed and published by Saga events |
| `heartbeat` | write | read | JSON, retained, QoS 0, every 60 s |
| `converged` | write | read | JSON, retained, QoS 1 |
| `commit-plateau` | write | read | JSON, retained, QoS 1 |
| `completion-likely` | write | read | JSON, retained, QoS 1 |
| `alert` | write | read | JSON, not retained, QoS 2 |
| `requests/+/consumed` | write | read | (new) |
| `answers/#` | read | write (only) | (new) retained |
| `guidance` | read | write (only) | Markdown today, retained, QoS 1 (GD-6) |

Prefix isolation alone does not say who may produce a message; the ACL
does. The broker rejects a worker's publish on `answers/#` or
`guidance`; the attempt is visible in Saga's logs; no answer or
guidance record changes (AC-29).

**MQ-6** · Open (GAP-23). ACL entries not in the design: Saga events'
own credential; read access for observability (the Telegraf pipeline);
who may publish `saga/events/<kind>` (today a worker hook publishes
`saga/events/dvergr_completed`, which the target ACL does not allow,
INC-07); QoS and retain for `request`, `answers/<rid>` (retained is
Specified) and `requests/<rid>/consumed`; transport encryption, which
no source specifies.

**MQ-7** · Current, kept until replaced. Payload of the `status`
topic, *verbatim from source*:

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "iteration": 14,
  "max_iterations": 30,
  "status": "running",
  "current_task": "Implement caching layer for API responses",
  "task_id": "US-007",
  "started_at": "2026-04-09T22:15:00Z",
  "iteration_started": "2026-04-10T01:43:12Z",
  "iteration_duration_s": 187,
  "exit_signal": false,
  "tests_passing": 42,
  "tests_failing": 3,
  "last_commit": "a1b2c3d",
  "last_commit_msg": "Add Redis cache wrapper with TTL support",
  "files_changed": 7,
  "rate_limit_remaining": true,
  "error": null
}
```

Valid `status` values: `running`, `paused`, `completed`,
`max_iterations_reached`, `failed`, `rate-limited`. Alert `severity`:
`info`, `warning`, `critical`; alert `type`: `stuck_loop`,
`test_regression`, `rate_limit`, `circuit_break`, `quality_concern`,
`completion`. The `project` and `instance` fields become run-scoped
with the rename; their target names are Open.

**MQ-8** · Specified. Per-topic revision reconciliation. A retained
publish is last-write-wins by topic, so the publisher reconciles an
uncertain publication by reading the retained value back:

| Retained value found | Outcome for this operation |
|---|---|
| Carries this operation id | `delivered` |
| Carries a **newer** revision | `superseded`; never republished |
| Older revision, or absent | Republish |

A differing value is not proof that the earlier publication failed.
Every payload Saga publishes on `guidance` carries the operation id and
the run's `guidance_rev` from the ledger. For `answers/<rid>` the
authoritative revision is Open (Proposed here: the request revision);
one answer wins, so supersession should not arise. In the target, Saga
events is the only publisher of these topics and performs this
reconciliation, and records each outcome against the client's
operation (GD-4, OP-4); in the shadow period the publishing sidecar,
today part of Saga events, does. This read-back is Saga-internal; no
client performs it.

**MQ-9** · Current, kept. Lifecycle events on `saga/events/<kind>`:
QoS 1, not retained, uniform envelope. *Verbatim from source*:

```json
{
  "ts": "2026-04-16T15:30:00Z",       // ISO-8601 UTC, when the event happened
  "kind": "dvergr_completed",         // matches the topic suffix
  "source": "dvergr/muninn/instance-1", // who emitted (free-form identifier)
  "project": "muninn",                // optional, scoped events
  "instance": "instance-1",           // optional, scoped events
  "data": { ... }                     // kind-specific payload
}
```

These are observability signals, not the ledger: a client never
derives run state from them (EV-1).

## 16. Phase gates

**PH-1** · Locked (D15). Phase B, Saga service v1: run ledger and
delegation records; local API with client library; facade over the
existing launcher and MQTT; the D5 state machine; launcher defects
fixed; `commands/` deleted; D13 renames applied. Minimum enforcement:
approval and verdict binding by hash at submission, reviewer-identity
verification, cancellation, the concurrency cap, the stop operations
and the kill switch. Exit: a run can be submitted, watched by cursor,
guided, stopped and cancelled from a CLI; the CLI is refused for the
same reasons Odin would be; `/stop <delegation>` stops a whole
delegation and reports.

**PH-2** · Specified (Phase B, additionally): the minimum verification
policy (VER-2); the `needs_input` worker protocol in the Claude Code
worker image (§11); the run evidence store (REC-7); per-worker
credential provisioning replacing the shared writable volume (AUTH-3);
launcher fixes named in the roadmap: `depends_on` on `verified`, a
queued signal, unique result files, `approved` renamed `accepted`.

**PH-3** · Locked (D15, D19). Odin's first live project requires Phase
B's minimum enforcement; Odin v1 (Phase C) is not started before B's
API and minimum enforcement exist. Development against a fake backend
is allowed and establishes no production readiness.

**PH-4** · Locked (D15). Phase D: container TTL, per-run and per-day
budget, operator-presence gate, action-authority boundaries for any new
connector, evidence rules for `verified` per project type. Exit: a
second client and Odin encounter identical policy; false completion
reports measured.

**PH-5** · Locked (D15). Phase E: the worker contract document; a Codex
CLI worker image; a Pi image for API-key or local models. Exit: a Codex
run completes under the same hooks and ledger.

**PH-6** · Locked (D15, D21). Phase F and later: Bragi on the ledger
and delegation records; observability; a computer-use worker only by
operator decision, under a delegation naming desktop authority, never
in the first release.

## 17. Current implementation (the facade's starting point)

All Current. Read from code at the base commit; not re-verified on the
Docker host, whose state cannot be seen from the documentation checkout.

**Launch request.** A YAML file in `launch-requests/`; its file stem is
the request id. *Verbatim from source* (Saga's launcher's docstring):

```yaml
    kind: dvergr            # only "dvergr" accepted; odin/mimir launches
                           #   stay outside this pipeline (host scripts)
    project: nexus
    instance: instance-1
    image: saga-dvergr:latest
    env:
      MQTT_HOST: 192.168.86.12
      MAX_ITERATIONS: "20"
      COMPLETION_PROMISE: COMPLETE
    workspace_source: /opt/saga/workspaces/nexus/instance-1
    action: start          # start | stop | restart
    repo: http://192.168.86.18:3000/david/nexus    # optional — exported as DVERGR_REPO
    prd: /workspace/odin/prds/nexus/instance-1.md  # optional — heimdall copies into workspace
    gitea_credentials: nexus-write                 # optional — file in /opt/saga/secrets/gitea/
    secrets:                                       # optional — files in /opt/saga/secrets/projects/<project>/
      - stripe-api-key                             # → injected as -e STRIPE_API_KEY=<value>
      - polygon-io-key                             # → injected as -e POLYGON_IO_KEY=<value>
    depends_on:                                    # optional — list of "<project>/<instance>"
      - nexus/instance-0                           #   heimdall holds this request until each named
                                                   #   container has completed (status=approved)
```

Validation: unknown top-level keys rejected; `kind` must be the worker
kind; names match `^[a-z0-9][a-z0-9-]{0,31}$`; image on the allowlist;
`action` ∈ start, stop, restart; denylisted environment keys and
control characters rejected; `workspace_source` under the workspaces
root; secret names valid and not colliding with the denylist or `env`;
`depends_on` may not name the request itself (cycles are left to
review); the PRD must exist after provisioning.

**Launch result.** `launch-results/<request id>.yml` with `request_id`,
`status` (`approved`, `rejected`, `error`), `rc`, `output` (truncated to
8 KiB), `container_name`, `timestamp`. `approved` means `docker run`
returned 0.

**Known defects.** Locked (`CLAUDE.md`): fix in Phase B, do not work
around.

- Nothing consumes `commands/` or `outgoing-commands/`; `stop` and
  `restart` are launch requests with an `action` field.
- `depends_on` counts a crashed prerequisite as satisfied because
  containers run with `--rm`. (The code treats a dependency as
  satisfied when its container is not running and any `approved` result
  exists for that container name.)
- A request held on `depends_on` gets no result file for up to 24
  hours, then is rejected.
- A reused request id overwrites its result file.
- `approved` means `docker run` returned 0, nothing more.

**Other current facts the facade must replace.** The launcher polls
every 2 seconds. Every worker mounts the shared `saga-claude-credentials`
volume. The events sidecar subscribes to `dvergr/+/+/{status, journal,
alert, converged, commit-plateau, completion-likely}`, publishes
`metrics`, publishes guidance from `outgoing-guidance/` files as raw
retained Markdown, and publishes lifecycle events from
`outgoing-events/`. Worker hooks read retained guidance at session start
and after each iteration, publish status and journal after each
iteration, and publish `saga/events/dvergr_completed` once. MQTT clients
in this repository connect without credentials; the broker's own
configuration is not in this repository. The orchestrator's file
interfaces (`launch-requests-draft/`, `incoming-*`, `outgoing-*`,
`mimir/pending/`, verdict marker files) are deleted at migration
(Specified).

## 18. Open register

### Gaps

Each must be closed by a producer decision before the dependent wire
detail is frozen. Saga's producer backlog (items `P-nn` and `X-nn` in
Saga `docs/contracts/README.md`) orders them.

| Id | Gap | Blocks |
|---|---|---|
| GAP-01 | Client authentication and authorization on the Unix socket: credential type, socket path and permissions, principal names, per-client read scope | API-1, all endpoints |
| GAP-02 | How Saga verifies the operator principal for approvals, answers and delegation changes, so a client service cannot record an operator approval for its own submission | ID-2, ADM-5, RQ-5, G4 |
| GAP-03 | Reviewer identity key: algorithm, custody, rotation, the bytes signed, verification at `POST /reviews` | ID-1 |
| GAP-04 | Canonical digests: PRD bytes, the canonical encoding over which `launch_config_digest` is computed, plan manifest, payload digest for operation conflicts | ADM-3, ADM-9, OP-3 |
| GAP-05 | Identifier formats and uniqueness scopes: run id, worker request id. (The submission request id is a client-minted ULID, ID-4; only its uniqueness scope across clients remains here) | §2 |
| GAP-06 | `POST /runs` body and response; refusal-reason catalogue; status codes | ADM-4 |
| GAP-07 | The multi-run approval envelope (how one plan-level approval covers several submissions' request ids and digests), approval states, default expiry, expiry while queued, restart coverage (ID-4) | ADM-8, ADM-12, ID-4 |
| GAP-08 | Verdict binding fields (to submission request ids, guidance operations and artifact digests), which results admit, review types, which mechanical checks Saga runs | ADM-7, ADM-8, ADM-11, GD-3 |
| GAP-09 | Where the review requirement comes from (a delegation field, per review type, per project) | ADM-6, GD-3 |
| GAP-10 | Guidance: the mechanical definition of "material" and the policy representation behind GD-3 (rules 1 to 5 are fixed); the retained payload envelope; whether guidance carries an expected `guidance_rev` | GD-3, GD-6 |
| GAP-11 | Event envelope, kinds, paging, streaming, retention, sequence density, read scope | EV-4, EV-5 |
| GAP-12 | Operation record schema, receipt format, scoping of lookups to the issuing client | OP-4 |
| GAP-13 | Full transition table: whether `queued` is always entered, `limit-paused` entry and exit, `closed` trigger, refusal representation, restart reference field | LC-1, LC-6, OP-4 |
| GAP-14 | Evaluation of the Phase B verification minimum | VER-6 |
| GAP-15 | `depends_on` target (stream or run) and behaviour on a failed or cancelled prerequisite | LC-4 |
| GAP-16 | Concurrency cap: refuse or queue; global cap | ADM-12 |
| GAP-17 | Stop: operations enumeration, which are Saga's, report schema, kill-switch persistence | ST-1, ST-3, ST-6 |
| GAP-18 | Revocation effects on running runs, guidance, answers, credentials; expiry | ST-5, GD-5 |
| GAP-19 | Saga's own restart and reconciliation procedure | RCV-4, OP-8 |
| GAP-20 | Delegation schema, states, read endpoint, change approval flow | REC-2, §7 |
| GAP-21 | Evidence kinds, reference format, test output capture, retention, redaction | REC-7 |
| GAP-22 | Request lifecycle mechanics: delivered report, close trigger, cancellation source, default expiry | RQ-8 |
| GAP-23 | Broker mechanism for per-run credentials and ACL; Saga events' and observability's access; lifecycle-event publishers; QoS and retain for new topics; clearing retained answers; transport encryption | MQ-4, MQ-6, RQ-8 |
| GAP-24 | Enforcing "push to the stream branch only" on Gitea | AUTH-2 |
| GAP-25 | Credential lineage provisioning mechanism, pending the billing and auth re-test | AUTH-3, AUTH-5 |
| GAP-26 | `POST /tasks` (Eir maintenance task) schema and semantics | §7 |
| GAP-27 | API versioning and client–service compatibility | API-5 |

### Inconsistencies between sources

Recorded, not silently resolved.

| Id | Inconsistency | Reading taken here |
|---|---|---|
| INC-01 | A submission's request id "is" its ULID operation id, yet the design's record example shows `"request_id": "muninn-stream1-20261014T0900Z-a1b2"`; and the design has the request id both assigned at staging and minted with the operation | **Resolved in 0.1.1** (ID-4): a client-minted ULID, preallocated before review and staging, reused by submission and retries. The source example stays verbatim in the frozen source as a historical example that does not conform to the corrected format |
| INC-02 | D2 and `CLAUDE.md` bind the launch configuration by hash; the design's submission tool takes only the PRD digest, verdict id and approval hash | **Resolved in 0.1.1**: D2 governs; `launch_config_digest` is required (ADM-3, ADM-9); its encoding stays Open (GAP-04) |
| INC-03 | D3 lists "request a review" in the orchestrator contract; the design gives review coordination to the client and only verdict recording to Saga. A CLI client without a reviewer could then never satisfy a required review | Open; matters for G3 |
| INC-04 | Guidance is "verdict-bound" for every publication, but D8 reviews only material guidance; "or `APPROVE_UNCHANGED` semantics" conflicts with "`APPROVE_UNCHANGED` means do not publish" | **Resolved in 0.1.1** (GD-3): D8 governs; routine guidance takes mechanical checks, material guidance a bound verdict, unresolved cases fail closed, `APPROVE_UNCHANGED` never publishes. Representation Open (GAP-10) |
| INC-10 | The design's client outbox lists a retained MQTT publish of guidance and answers as its own destination, and its acceptance scenario has the client reconcile by reading the retained value; D1 and the ACL (MQ-5) keep MQTT inside Saga | **Resolved in 0.1.1** (GD-4, OP-4, OP-6, MQ-8): Saga reconciles and reports `superseded` through the API; a client's MQTT publication is shadow-period practice only |
| INC-05 | The target ACL lets a worker write `metrics`; today Saga events computes and publishes `metrics` from journals | Open; Proposed here: Saga events keeps computing it |
| INC-06 | The request lifecycle has `delivered`, set by the client's delivery, but no endpoint receives that report | GAP-22 |
| INC-07 | Worker hooks publish `saga/events/dvergr_completed`; the target ACL grants no such write | GAP-23 |
| INC-08 | The worker request field is `what_answering_authorizes`; the record example field is `authorizes`; D5 writes `limit-paused`, the consumer's event kinds write `limit_paused` | Names Open until the schema |
| INC-09 | Verdict delivery uses flat fields; the review record nests `verdict` | GAP-08 |

### Implementation gates (source review G1 to G7)

The producer-side source review of 2026-10-14 (retained in Saga at
`docs/provenance/SOURCE-REVIEW.md`) named seven gaps, G1 to G7, that
may stay open but must be closed before the dependent work ships. They
are numbered `IG-` here because `G1` to `G10` in §1 are guarantees.
None is closed by this version; this contract does not implement
operator authentication and claims no conformance.

| Id | Gate | Owner | Closes by | Related |
|---|---|---|---|---|
| IG-1 | Operator identity at Saga: how Saga distinguishes an operator's approval or answer from one sent by a client service or the CLI | Saga producer (operator approves the mechanism) | Before Phase B minimum enforcement is declared met; required for Odin's first live project (PH-3) | GAP-02, ID-2, P-01 |
| IG-2 | Stop split: which of D2's four stop operations `POST /stop` performs and which belong to the orchestrator's service; what the kill switch does when the orchestrator is down | Saga producer for Saga's operations; Odin for its planner, timers and evaluators | Phase B exit (`/stop <delegation>` from the CLI) | GAP-17, ST-1, ST-2, P-13 |
| IG-3 | Restarts and review cost: a restart's new request id (ID-4) needs a renewed verdict or approval coverage; whether unchanged digests can be covered without a fresh model review, and the review-cost consequence | Saga producer (binding rule); Odin (review-cost accounting) | Before Phase B approval and verdict binding is built | GAP-07, GAP-08, ID-4, LC-6, P-05 |
| IG-4 | Saga's validator as a dependency: a client's pre-check in another repository needs a published artifact (a schema, or a released validation library), never Saga's unpublished code | Saga producer | Before Phase C relies on pre-checks; with the first `schemas/` release | ADM-10, GAP-04, GAP-06, P-04, P-08, X-01 |
| IG-5 | Planner answers: Saga can enforce only the request kind and the delegation's permission, not "does not change the plan" | Saga producer (enforcement); Odin (the judgment) | Phase B, with the request protocol | RQ-5, GAP-22, P-17 |
| IG-6 | Unconfirmed integrations: Herdr's API, Skald retrieval, dotprivate's selected-files contract, the Heimdall projection | Odin (consumer integrations; not Saga obligations) | Per Odin increment, Phases C to F | None in this contract |
| IG-7 | Unsettled defaults: the billing and auth re-test; the Console spend cap not applying under a subscription login; caps and coalescing window; the memory baseline | Operator (re-test, Phase A); Saga producer (concurrency caps, Phase B); Odin (coalescing, memory baseline, Phase C) | As stated per owner | AUTH-5, GAP-16, GAP-25 |

## 19. Producer conformance checks

None is implemented; none has run. Each is the check that enforces the
requirements named, per the repository rule that every behavioural rule
is paired with its check or a ticket. Consumer scenario ids are the
acceptance identifiers of the frozen design (`AC-`, `EC-`).

| Id | Check | Requirements | Consumer scenario | Status |
|---|---|---|---|---|
| CT-01 | The same submission sent twice under one operation id yields one run and the same receipt | G2, OP-3 | AC-01, EC-02 | Not implemented |
| CT-02 | An operation id reused with a different payload returns `409 operation_conflict`; nothing changes | OP-3 | — | Not implemented |
| CT-03 | Operation lookup returns each of the six results; `unknown_expired` is never treated as absence | OP-4 | AC-02 | Not implemented |
| CT-04 | A submission whose PRD or launch configuration changed after approval, whose supplied `prd_digest` or `launch_config_digest` differs from Saga's recomputation, or whose approval or verdict does not cover its request id and both digests, is refused | ADM-2, ADM-3, ADM-5, ADM-8 | AC-06, EC-02 | Not implemented |
| CT-05 | An answer to a reissued request for unchanged content is applied; an answer to the expired request is refused | ADM-5 | AC-30 | Not implemented |
| CT-06 | A verdict without the reviewer key, or recorded with a client credential, is refused | ID-1 | — | Not implemented |
| CT-07 | A required review with the reviewer unavailable refuses or holds the submission and records the gap | ADM-6 | AC-22 | Not implemented |
| CT-08 | The CLI and Odin's client are refused for identical reasons on identical submissions | ADM-1 | Phase B exit | Not implemented |
| CT-09 | A dependent starts only after its prerequisite is `verified`; a crashed prerequisite does not satisfy it | LC-4 | EC-02 | Not implemented |
| CT-10 | A run held on a dependency is visible as `queued` with its reason at once | LC-5 | — | Not implemented |
| CT-11 | Restarting a client leaves workers running; cursor replay rebuilds its run state | RCV-1, RCV-2, EV-1 | AC-03, EC-02 | Not implemented |
| CT-12 | Reading after the same sequence twice returns identical events | EV-3 | AC-01 | Not implemented |
| CT-13 | A cancel that cannot be confirmed is reported uncertain | OP-5, ST-3 | AC-10, EC-02 | Not implemented |
| CT-14 | `/stop <delegation>` from the CLI with no orchestrator running revokes admission, cancels runs and reports; a later submission is refused | ST-1 to ST-4 | AC-10, Phase B exit | Not implemented |
| CT-15 | The kill switch refuses all admission and cancels all runs | ST-1, ST-6 | — | Not implemented |
| CT-16 | Submissions beyond the delegation's concurrency cap are queued or refused per GAP-16 | ADM-2, ADM-12 | — | Not implemented |
| CT-17 | A worker's publish on `answers/#` or `guidance` is rejected by the broker, logged, and changes no record | MQ-5 | AC-29 | Not implemented |
| CT-18 | Reconciling an older guidance operation after a newer one marks it `superseded`, does not republish, and `GET /operations` reports `superseded` for it | GD-4, MQ-8, OP-4 | AC-28 (Saga side; the client counterpart reconciles through the API) | Not implemented |
| CT-19 | One answer wins; a second is recorded `rejected_duplicate`; an answer to a terminal request is refused | RQ-3 | AC-05 | Not implemented |
| CT-20 | Worker `completed`, `completion-likely` or exit code 0 alone never yields `verified` | LC-3, VER-4 | AC-13 | Not implemented |
| CT-21 | No secret value appears in the ledger, events, evidence, results or logs | ID-3, AUTH-6 | — | Not implemented |
| CT-22 | After a Saga restart, a started run whose container vanished becomes `terminated` with unknown exit, never `verified` | RCV-4 | — | Blocked on GAP-19 |
| CT-23 | Material guidance without a bound verdict is refused or held, including when labelled routine by the client; guidance whose classification Saga cannot establish is not published; a guidance review result of `APPROVE_UNCHANGED` publishes nothing | GD-3 | — | Blocked on GAP-10 |
| CT-24 | A restart reusing the predecessor's verdict or approval coverage, bound to the old submission request id, is refused; a retry of the original submission under its own id yields the original receipt | ID-4, LC-6, OP-3 | — | Blocked on GAP-07 |

## 20. Source mapping

### Frozen source

The base commit is clean, so every cited byte is recoverable from
Saga's history as `14fdab3:<path>`. The frozen capture for handoff
`2026-10-14-14fdab3` already exists at
`docs/history/saga-extraction/2026-10-14-14fdab3/` and keeps
repository-relative paths beneath that root (so the decision record is
`docs/history/saga-extraction/2026-10-14-14fdab3/docs/DECISIONS.md`).
Each captured copy was verified to have the SHA-256 of the committed
file listed below. Paths in this section are plain source references,
not links, so they read the same wherever this file is copied. Code
files are not in the capture; for them, and for any captured copy that
ever disagrees, the commit path and digest are the identity of the
source.

| Key | Source (path at `14fdab3`; also under the capture root unless marked code) | SHA-256 |
|---|---|---|
| DEC | `docs/DECISIONS.md` | `685230a381b0075f261967781b396fa7cc9c5540012c102ae5d6a5f9d7842af9` |
| IO | `docs/design/ODIN-IO-CONTRACT.md` (v7) | `eae64b777c2dc51608fc0062beb195df283bbc6d575ef45ff6f008cd74197271` |
| BP | `docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md` | `228dc508d1c13febc5b4103ccfc473440da835210112df486ff35656c1a20489` |
| ECO | `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | `83f3e7a4fabb8fa686eab3688dbe07637a1a19ed1317f01a04ef6347fe19b07b` |
| ACC | `docs/design/ODIN-ACCEPTANCE-SCENARIOS.md` | `5f6471c6747578cbc06267247bf7672b081fcd7f8be4ffba0af1a2a939664422` |
| EXT | `docs/design/ODIN-REPOSITORY-EXTRACTION.md` | `ab2290941589b96ddb9f242ef5ff7bee736ebfefcbbf56fe49eb6b45f2f2bdf5` |
| RM | `docs/ROADMAP.md` | `f2ad3fa84f7f8ac8c674a7d4163c3e52d387a0236ce7a95c9cbcfd66611b52f6` |
| CL | `CLAUDE.md` | `6d7a8e8ca9ea4f6bfd6c2239075a6d72d7363cb57db7d67a864e32512b846360` |
| TOP | `mqtt/TOPIC-SCHEMA.md` | `7a73e551ba924329ccd5af775bc98e4e47e55695126ce57859db5c38546e6a36` |
| LCH | `odin/scripts/heimdall.py` (code; at the commit, not in the capture) | `8ef049d91b13d32b63a738c1e5b2332a2f487570c8edc604a96b77aac98359bc` |
| EVT | `odin/scripts/ratatoskr.py` (code; as LCH) | `7a601f0a9c40723c077a72eb2bd425f9bc388e483e11e90b40b5cb148cf6035d` |
| HK1 | `dvergr-hooks/pre-iteration.sh` (code; as LCH) | `ebd33647f47f6938d223348eda91505a5a3cbbca3bb7c0f872dc3091decc5780` |
| HK2 | `dvergr-hooks/post-iteration.sh` (code; as LCH) | `d79876fc3c227a3a7ed7a1c05dff663a2d43944aeb4e7f0177e4195a78080460` |
| PER | `odin/CLAUDE.md` (today's orchestrator persona) | `f6bc19475ec0118cfe48c1d5678df78a1f67db21512c5444f6b99f78cf6d458f` |
| REV | `docs/provenance/SOURCE-REVIEW.md` in Saga (the 2026-10-14 source review, verdict CHANGES_REQUIRED; not part of the capture and not a requirement source; it motivated the 0.1.1 corrections) | Not recorded |

The live Saga decision record is Saga `docs/DECISIONS.md`; the live
roadmap is Saga `docs/ROADMAP.md`; the release table and producer
backlog are in Saga `docs/contracts/README.md`. None is needed to read
this contract.

### Corrections in 0.1.1

| Review finding | Requirements changed | Authority |
|---|---|---|
| B3 Launch configuration not bound | ADM-3, ADM-8, ADM-9, §7 `POST /runs`, CT-04; INC-02 resolved | DEC D2 "Run admission"; CL critical constraint 1 |
| B4 All guidance verdict-bound | GD-3, §2 authorization table, §7 guidance row, CT-23; INC-04 resolved | DEC D8 "When", "Mechanical first"; D9 |
| B5 Client publishes to MQTT | GD-2, GD-4, OP-4, OP-6, MQ-8, §7 operations row, CT-18; INC-10 added | DEC D1; CL dependency decisions (MQTT); MQ-5 ACL; ACC AC-28, AC-29 |
| B6 Request id minted twice | ID-4, OP-2, LC-6, §2 identifier table, CT-24; INC-01 resolved | DEC D2 (verdict bound to the request id); IO §9 (request id = operation id) |
| G1 to G7 | §18 implementation gates IG-1 to IG-7 | REV |

### Contract section to source

| Contract | Sources |
|---|---|
| §1 Scope, guarantees | DEC D0, D1, D3, D7 ("Commitments are not memory"), D17, D23; CL critical constraint 1; IO §1, §10 "The Saga service"; BP §3 |
| §2 Identities, principals | DEC D2 "Reviewer identity", D9, D13, D24 table "Credential reference"; IO §2 (identifier rule), §7 profile table (planner holds no Saga token or reviewer key; reviewer key held by the service), §10 workers (per-run credentials), App. A field types; LCH name rule |
| §3 Records | DEC D4, D8 "Bounded and actionable", D17; IO §2 table rows Delegation, HumanRequest, Approval, Review, §9 "Outbox", §10 Mimir, App. A (Approval, Review, HumanRequest verbatim), App. B evidence row; RM Phase B "Run evidence store"; TOP status payload |
| §4 Admission | DEC D2 "Run admission", D8 "Mechanical first", D9, D15 Phase B exit; CL constraint 1 ("by hash of the approved PRD and launch configuration"); IO §4 "Approval response" row, §6 `stage_run` and `submit_run`, §10 Mimir and Operator, App. B `POST /runs`; ACC AC-06, AC-22, AC-30; ECO §3 acceptance |
| §5 Lifecycle | DEC D5, D18 (false completion measure); IO §6 `cancel_run` (restart), §4 lifecycle handler (consumer side), App. C state kinds; BP §4 last paragraph; CL "The launcher's known defects"; RM Phase B "Launcher fixes"; TOP status values; LCH `_dep_satisfied`, `DEP_WAIT_MAX_SECONDS` |
| §6 Verification | DEC D5, D15 Phase D; IO §13 Phase B row ("minimum verification policy"); BP §4; DEC D20 "Adapter modes" (workspace done is not completion); ACC AC-13, AC-14 |
| §7 API | DEC D3, D13 table (file interfaces → API); IO App. B, §6 Saga tools, §9 destination table; RM Phase B "Local API" |
| §8 Cursor | DEC D4; IO §9 "Inbox, cursors and processing states", App. B `GET /events`; BP §4 ("Saga's ledger sequence remains its own authoritative order") |
| §9 Operations | DEC D1, D6; IO §9 "Outbox" and the destination table, App. B `GET /operations`; ACC AC-01, AC-02, AC-10; ECO §3 acceptance; LCH container naming |
| §10 Guidance | DEC D3 worker contract, D8 "When"; IO §6 `publish_guidance`, §9 MQTT row, §10 workers (ACL); ACC AC-28; TOP guidance topic; EVT guidance publish; HK1, HK2; PER "Active Evaluation" step 4 (`APPROVE_UNCHANGED` means do not publish; INC-04) |
| §11 Requests | DEC D3, D9 "Safety rules", D20 routing table; IO §10 "Workers: the structured request protocol", §6 `answer_request`, §4 needs_input row; ACC AC-05, AC-07, AC-29 |
| §12 Stop | DEC D2 "Stop semantics", D15 Phase B exit, D20 ("stop is a direct service operation"); IO §10 Operator, App. B `POST /stop`; ACC AC-10, AC-27 (consumer side); BP §5 |
| §13 Recovery | DEC D1, D4, D11; IO §9 "Recovery on start" (consumer protocol; Saga's own procedure not in any source); ACC AC-03; ECO §3 |
| §14 Authority, credentials | DEC D2 "Action authority", D24; CL "Auth boundaries", "Under re-test", "Permitted auth shapes"; IO §7 implementation-worker profile; RM Phase B credential provisioning, Phase A re-test; LCH validation, secrets and argv |
| §15 MQTT | CL dependency decisions (MQTT); DEC D13 topic rename; IO §9 MQTT row, §10 workers; ACC AC-28, AC-29; TOP (all topics, payloads, lifecycle envelope, namespace coexistence); EVT subscriptions and publishes; HK1, HK2 |
| §16 Phases | DEC D15, D19 ("restrained initial product"), D21; IO §13; RM Phases B–F; EXT §1 (fake backend establishes no readiness); CL "Build order" |
| §17 Current | LCH; EVT; HK1, HK2; TOP; CL known defects; IO §10 "As it is today", §14 step 4 |
| §18 Register | Each entry's sources are those of the requirement it blocks; INC rows cite both sides |
| §19 Checks | ACC §2 (AC ids); ECO §3 acceptance and §10 EC-02; DEC D15 Phase B exit |

### Decision coverage (D0 to D24)

Which clauses of the joint record bind Saga and where they landed here;
what is not carried and why. Clause ownership follows EXT §4.

| Decision | Carried (Saga's clauses) | Not carried |
|---|---|---|
| D0 | Saga's promise and deployment language (SCOPE-1) | Odin's promise and audience |
| D1 | Saga's role, ownership, boundary guarantees (SCOPE-2, G1, G2, RCV-1) | Odin's ownership |
| D2 | Admission, action authority, reviewer identity, stop semantics (§4, §14, ID-1, §12) | — |
| D3 | Orchestrator contract (SCOPE-3, §7); worker contract clauses on guidance and requests (GD-1, RQ-1) | Codex worker detail (Phase E) |
| D4 | Ledger and cursor (REC-1, EV-1) | Odin's chat log |
| D5 | States, `depends_on`, evidence judgement (§5, §6) | — |
| D6 | Side-effect rule for Saga as destination and actor (§9) | Odin's own outbox implementation |
| D7 | Only "Saga keeps authority and execution state" (SCOPE-4) | Runtime and memory (Odin) |
| D8 | Verdict results, bounded rounds, mechanical checks, review never waived (REC-4, ADM-6, ADM-11) | When Odin requests review; model choice; measurement |
| D9 | Decision-model outputs never authorize or waive; typed requests not classified (ID-2, ADM-6, RQ-1) | `decide`, evaluators (Odin) |
| D10 | — | Standalone tools (not Saga components) |
| D11 | Three loops; Saga's loop; Eir's out-of-band path; maintenance tasks (RCV-3, `POST /tasks`) | Eir's patch loop detail (Saga-owned, outside this API contract) |
| D12 | Bragi reads the ledger and delegation records (principal table) | Bragi's outputs |
| D13 | Names, topic rename, file interfaces replaced (Names, MQ-3, API-3) | — |
| D14 | Producer-side: this contract exists at the producer (Saga `docs/contracts/README.md`) | Odin repository handoff mechanics |
| D15 | Phases B, D, E gates (§16) | Phases C, G (Odin) |
| D16 | — | Documentation actions |
| D17 | Delegation record (REC-2) | Odin's priorities within a delegation |
| D18 | False completion and duplicate or unauthorized effects as measures (LC-2, §19) | The comparative experiment |
| D19 | Phase B before Odin's first live project (PH-3) | Adapters, capability matrices |
| D20 | Typed request routing, approvals bound regardless of channel, direct stop (RQ-1, ADM-5, ST-2) | Topology, workspace, ownership rules |
| D21 | Desktop work is not a Saga-admitted container; never in the first release (SCOPE-6, PH-6) | The desktop capability |
| D22 | — | Preservation |
| D23 | Saga as the governed default backend (SCOPE-6) | Backend selection |
| D24 | Worker lineages, quota behaviour, launcher injection (AUTH-3, AUTH-4) | Odin's planner authentication |
