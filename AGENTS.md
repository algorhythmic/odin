# AGENTS.md — developing Odin

Instructions for anyone, human or coding agent, working **on** this
repository. They are not Odin's runtime persona. The instructions that
make a deployed session behave as Odin or Mimir belong to the
integration package, which is derived at code extraction. The legacy
personas in `docs/history/` are evidence, not instructions for you.

## 1. Current state

- ODIN-ADR-028 authorizes the independent **development evaluator** and
  deterministic **development loop controller**. The evaluator chooses
  bounded tests and next stages for the existing native Fable executive;
  it is not Mimir's required-review role. An opt-in MCP channel delivers
  work into that same interactive session, and a native completion hook
  returns its final response for evaluation. Activation, channel delivery,
  completion capture and multi-round live behavior require separate
  evidence; code and synthetic tests do not establish them. See
  [`docs/DEVELOPMENT-LOOP.md`](docs/DEVELOPMENT-LOOP.md).
- ODIN-ADR-027 adds the executive's delegation path: six scoped bridge tools
  open one accountable local-backend planning session per project, assign
  work as owned commitments and local assignments, run detached
  non-interactive Claude Code or Codex turns, send follow-ups, collect
  unverified returns and record explicit acceptance. It needs an operator
  `delegation-configure` file; it supplies no isolation, enforced ceilings or
  Saga guarantees and does not deliver the managed session host, X-15 child
  dispatch or the I5 second adapter. See
  [`docs/EXECUTIVE-PILOT.md`](docs/EXECUTIVE-PILOT.md).
- ODIN-ADR-026 authorizes the operator's native development executive profile
  (version 3). It uses Claude Code's normal tools and prompt, permission
  bypass, the actual checkout as cwd, and the inherited operator environment
  and HOME. Odin adds no tool/path allowlist or disabling of hooks, plugins,
  skills, native memory, discovery, browser tools or native agents. The
  dedicated Claude login and session identity are retained. Direct inspection,
  edits, command execution, tests and native delegation for operator-directed
  development no longer depend on the fake Saga backend or the restricted
  planner profile. The older ADR-024/025 restrictions below describe versions
  1 and 2; they do not constrain version 3. Odin's MCP record semantics and
  Saga's own interfaces/guarantees are unchanged. See
  [`docs/EXECUTIVE-PILOT.md`](docs/EXECUTIVE-PILOT.md) for activation and evidence.
- ODIN-ADR-025 extends the executive pilot with explicitly enabled native
  `Read`, `Glob` and `Grep` for this checkout, and operator-imported committed
  repository snapshots in attributed memory. Native reads show current files;
  memory reads retain exact committed source revisions. These are evidence
  paths, not permission to edit, execute workers or apply improvements.
  Claude permission rules are not OS isolation; live tool visibility and
  read boundaries require separate pilot checks. The local SQLite records
  persist even though the execution backend remains fake Saga.
- ODIN-ADR-024 authorizes a bounded native Claude Code executive pilot:
  Fable conversation through Remote Control, with a scoped local MCP bridge
  for Odin reads and unverified reports/proposals. See
  [`docs/EXECUTIVE-PILOT.md`](docs/EXECUTIVE-PILOT.md). This is an explicit
  exception to the SDK-only invocation and interactive-only transport
  constraints for this pilot. Dedicated login, observed model/connection
  and live acceptance are separate from command construction and tests.
  The full SDK adapter, authenticated daemon and Saga live path remain gated.
- ODIN-ADR-023 adds local attributed memory, resume/decision views,
  session-host protocol checks and offline evaluation preparation. See
  `docs/PRODUCT-IMPLEMENTATION-STATUS.md` for exact evidence and gaps.
  Memory source/derived data is synthetic in fixtures. The actual SDK,
  authenticated daemon, credentials, native children and Saga live path
  remain gated; do not equate protocol mocks with real enforcement.
- Partial I0 contracts remain in `runtime/`. The repository also has shared Go/Python validators, synthetic fixtures and one Python service foundation against a fake Saga backend. See `docs/IMPLEMENTATION-STATUS.md` for local evidence and limits. Review/guidance schemas remain gated on X-7. The native executive pilot does not establish the full live harness adapter or live Saga; local component tests are not full runtime acceptance.
- This is a candidate documentation handoff from Saga (snapshot
  `2026-10-14-14fdab3`), and the handoff is **not recorded**. Until it is,
  Saga's decision record remains authoritative and these documents must
  agree with the frozen copy except for explicitly recorded operator
  decisions in Odin's ADRs. Those do not amend Saga-owned interfaces
  or close the cross-repository handoff.
- ODIN-ADR-006 to 015, recorded on 2026-10-16, supersede or amend
  inherited clauses Odin owns. The consolidation plan
  ([`docs/design/CONSOLIDATION-PLAN.md`](docs/design/CONSOLIDATION-PLAN.md))
  is a proposal: its Saga-side parts, a shared repository among them,
  wait on Saga's record (issue X-14). Don't build or describe them as
  decided.
- ODIN-ADR-020 and 021 record evaluation and local storage conventions.
  ODIN-ADR-022 records only an experimental portfolio and handoff protocol;
  AC-42–AC-50 are proposed full scenarios. X-15 remains open for
  service-managed native child dispatch; ADR-026 permits ordinary native
  agents in the development executive without claiming that service-managed
  protocol is delivered. Exact role configuration is local fixture evidence,
  never proof that a live model or harness path is available.
- The first implementation work is **I0** (the event envelope,
  namespaces and record schemas, validated in Go and Python against one
  fixture set; ODIN-ADR-008), then **I1** (capability matrix, fake Saga
  backend, three-document fixture, ownership mapping, then the service
  foundation) and **I2** (first harness, workstation daemon v0), both
  against the fake backend. A fixture-only Pi RPC control follows I2
  (ODIN-ADR-015). **I3** and every Saga-managed live delegated run require
  Saga Phase B ([roadmap](docs/ROADMAP.md)).
  X-7 must be resolved before writing the Review/guidance schemas in I0;
  the envelope and unaffected schema work may start.
  Allowing I0–I2 alongside Phase B is an Odin-side interpretation;
  reconciliation with Saga's phase wording remains open (issue X-1).

## 2. Where the requirements are, and which wins

1. [`docs/DECISIONS.md`](docs/DECISIONS.md): current decisions.
2. [`docs/design/ODIN-IO-CONTRACT.md`](docs/design/ODIN-IO-CONTRACT.md): the operational contract.
3. [`docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md`](docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md): implementation overview and increments.
4. [`docs/ROADMAP.md`](docs/ROADMAP.md): progress and gates.

[Acceptance scenarios](docs/design/ODIN-ACCEPTANCE-SCENARIOS.md) must
agree with 1 and 2. If they conflict, raise an issue; don't pick a
side in code. Producer interfaces (Saga and peers) are governed by
their pinned contracts in [`docs/contracts/`](docs/contracts/README.md),
not by Odin's documents. Research and history are evidence, not policy.

A bare `D7` means `SAGA-2026-10-D7`. Resolve it and its clauses through
[`docs/provenance/DECISION-MAP.md`](docs/provenance/DECISION-MAP.md).
Never renumber an inherited decision. To change one, record an
`ODIN-ADR-nnn` in `docs/DECISIONS.md` §4 that names the clause it
supersedes, then update the map. Open questions and `X-n` issues stay
open until the operator or a recorded decision closes them; moving or
rewording a document does not close them.

## 3. Files you must not edit

- `docs/history/saga-extraction/<snapshot-id>/**`: frozen source bytes.
  Fix links in the live documents instead.
- `docs/provenance/EXTRACTION-MANIFEST.json`: source identities and
  source hashes are immutable. When deliberately editing a live handoff
  output, update its destination digest and transformation note; never
  change a source hash to make a modified historical file pass.
- `docs/contracts/<producer>/<snapshot-id>/**`: pinned producer
  contracts. A new capability starts in the producer's repository; then
  pin a new snapshot and update the adapter's compatibility checks
  together.
- `docs/research/harness-research-2026-10/*.md` other than its README:
  exact copies of dated evidence.
- `docs/research/consolidation-2026-10/*.md` other than its README:
  dated evidence.
- `docs/research/model-orchestration-2026-10/*.md` other than its README:
  byte-preserved operator research.

Never edit Saga or any peer repository from this one.

## 4. Architecture in brief

- **Two loops.** The service loop is ordinary code: intake, records,
  routing, scheduling, outbox, budgets, session lifecycle. The harness
  loop is a Claude Code session started through the Agent SDK. ADR-024
  additionally permits a native interactive CLI session for the bounded
  executive pilot; ADR-026 adds native development tools and agents to that
  pilot. Most service events never reach a model (I/O contract §4).
- **One event substrate.** The transactional core (SQLite, WAL) becomes
  an append-only event substrate with namespaces: Odin history,
  transcript archive, workstation surface events. Each namespace has
  exactly one writer. Records, inbox, outbox, cursors, messages and tree
  nodes commit in the same transaction as their history. The
  execution-ledger namespace is a read-only mirror of Saga's store, fed
  only through Saga's API and cursor; never author or amend a mirrored
  record, and never write Saga's store. JSONL files and
  `view.json` are regenerated projections (§9, ODIN-ADR-006). The
  local physical layout is one WAL file per namespace (ODIN-ADR-021);
  production ownership and failure-domain checks remain open (X-11).
- **Commitments are records, not memory.** Summaries serve recall; open
  obligations live in commitment records (D7). The commitment record is
  the only editable task record: heimdall's task layer is imported once
  and retired, with no bridge (ODIN-ADR-007).
- **Service and workstation daemon.** The service runs on the homelab.
  A workstation daemon hosts the session host, sensors, transcript
  capture and local surface adapters. The session host starts, resumes,
  interrupts and retires sessions only on the service's command;
  session records, ownership and budgets stay in the service. An
  unreachable host makes its bindings `host_offline`, not failed
  (ODIN-ADR-009).
- **Operator surfaces** are adapters on one service API, and every one
  enters the same recorded command path. An attention prompt is a typed,
  capped outbound effect whose response is a record; never a
  synthesized keystroke (ODIN-ADR-010). ADR-024's Remote Control pilot
  carries conversation in Claude Code; it is not an authenticated Odin
  command adapter. Model-relayed text cannot approve, grant or verify work.
- **Saga boundary.** Odin reaches Saga only through its API (D1.3).
  Saga's ledger decides whether a run was approved or completed (D4);
  Odin's history never does. Odin requires the capabilities in the I/O
  contract's Appendix B.
- **Runtime adapters.** Each adapter publishes a capability matrix
  (start, resume, inject mid-turn, interrupt, budget, model and effort,
  transcript, hooks, profile enforcement, attachable view,
  permission-prompt relay). The service refuses a session class whose
  required capabilities are missing. Record each code-made class choice
  with its rejected alternatives; the record never changes routing
  (ODIN-ADR-014). The adapter translates assignments,
  events and results; it does not reimplement the harness. Claude Code
  through the Agent SDK comes first; a fixture-only Pi RPC control
  follows I2 (ODIN-ADR-015). Build no universal adapter framework
  before a second adapter exists (D19). Don't rely on interactive-only
  behaviours for the managed SDK adapter: channels, plugin monitors,
  teammates (D7). ADR-024 permits Remote Control for pilot conversation;
  ADR-026 permits the development executive's native tools and agents.
  ADR-028 adds an opt-in development channel and completion hook for the
  existing native session; it does not start a second Claude credential owner.
  This does not deliver service-managed child dispatch or a second harness.
- **Capability profiles** (planner, reviewer, worker, desktop worker,
  subagent) are enforced before tool execution, not by prompt (§7). The
  ADR-026 native development executive is explicitly outside those restricted
  profiles and runs with the operator's local process authority.
- **Review.** Required review uses two reviewer positions, on different
  model families where adapters allow, given the same evidence pack;
  service code combines their verdicts and sends disagreement to the
  operator. This is a hypothesis, not a settled design (ODIN-ADR-013).
  The development evaluator assesses behavior and selects the next test
  under ADR-028; it does not replace those reviewer positions or approve
  external effects. The development loop controller owns delivery identity,
  durable transitions, pause/stop and round bounds, not model judgment.
- **Desktop input** is a gated process of the workstation daemon, under
  its own Unix user, disabled until desktop authority is decided; never
  reachable from a planning session (ODIN-ADR-011).
- **Preservation.** Odin writes and commits its own package; dotprivate
  is off its dependency path (ODIN-ADR-012).
- **Effects** are at-least-once with stable operation ids, explicit
  `unknown`, and reconciliation before retry; nothing claims
  exactly-once (D6, §9).

## 5. Fake backend versus live Saga

- The fake Saga backend implements Appendix B for development and the
  acceptance scenarios (I1 to I2; I0 has fixtures only). Label every result obtained with it
  as fake-backend evidence.
- Never present the fake backend, or any backend other than Saga, as
  providing Saga's guarantees (isolation, enforced limits, durable run
  records, recovery). The managed product routes work with external effects
  through Saga (D23). ADR-026 exempts operator-directed native development
  work from that Odin routing rule; it supplies no Saga guarantees and does
  not grant access to Saga-owned hosts, stores or secrets.
- A passing fake-backend scenario does not establish production
  readiness. Live claims need I3 against Saga after Phase B.
- AC-29 is checked at Saga, not here.

## 6. Credentials, data and private material

- Never commit secrets, authentication caches, `.env` files,
  `.credentials.json`, Codex `auth.json`, logs, raw conversations,
  databases, workspaces or other runtime state. Use synthetic fixtures.
  Real history enters only through the scoped migration (I/O contract
  §14), never as a fixture.
- Keep three credential domains separate: your development login, the
  managed agents' credentials (Saga's), and Odin's harness credentials.
  Auth failures must be attributable to one of them.
- A workstation session host holds Odin's local model credential in a
  protected store that the service references, with one refresher per
  lineage. It is a separate lineage within Odin's harness credentials, never your
  development login (X-12).
- Managed planning sessions hold only their model credential. The Saga
  token, reviewer identity key and Telegram token stay in the service.
  ADR-026's native development executive inherits the operator environment
  and HOME; do not describe it as having managed credential isolation.
  Secrets never appear in prompts, history, briefings or exports (D24).
- Claude Code refresh tokens are single-use: exactly one process
  refreshes a given credential lineage. Copying one login file into
  several processes does not create separate lineages (D24).
- Permitted: the unmodified Claude Code binary with the operator's own
  subscription; Odin's planning sessions on an API key from the Console
  organization linked to the plan (default, still to be confirmed), or a
  subscription login lineage of their own. Not permitted for Claude
  work: third-party harnesses pointed at the subscription. Claude
  workers on a non-Anthropic harness use an API key.
- Still under re-test, so don't rely on them: the April 2026 findings
  that `claude -p` and `CLAUDE_CODE_OAUTH_TOKEN` force API billing.
- Agents never get the Docker socket. Don't add paths around Saga's
  launcher. Don't touch Saga's hosts, volumes, containers or secrets
  from this repository.

## 7. Conventions

- **Names** (D13). Norse names are only for agents that carry a persona
  and make judgments: Odin, Mimir (and Saga's Eir and Bragi). Everything
  deterministic gets a plain functional name. Never reuse a name from
  the operator's standalone repositories (heimdall, braid, skald,
  muninn, wayland-computer-use, dotprivate) or the third-party Herdr.
  No Odin deliverable prefix is defined yet (issue X-5); don't invent
  deployable names.
- **Terms.** Use worker, run, stream, delegation, commitment,
  assignment, planning session, evaluator, Saga launcher, Saga events,
  the Saga adapter (Odin's side), reviewer position (never "seat" for
  reviewers), attention prompt (never bare "nudge"), workstation daemon,
  session host, event substrate and human view. Use "execution backend"
  only as a synonym for Saga, and attribute its guarantees to Saga.
  Mimir names the reviewer role; whether the two reviewer positions are
  one persona or two is open with X-5 (ODIN-ADR-013).
  Don't use overseer, navigator,
  critic, judge or master as agent names. Legacy names (dvergr,
  instance, Heimdall for the launcher, Ratatoskr) stay only in history
  and in code until each rename lands. In prose, say "Saga's launcher",
  never bare "Heimdall".
- **Formats.** Every machine-read file is validated JSON or YAML with a
  schema. Markdown is for prose; native build manifests and dependency
  lockfiles use their tool formats (ODIN-ADR-021).
- **Rules need checks.** Pair every behavioural rule for an agent with
  the code check that enforces it, or a ticket for one.
- **Identifiers survive.** Keep AC, DC, EC, I, B, L and X identifiers
  stable. Add new ones rather than renumbering.
- **Peers are proposals until pinned.** The ecosystem plan records
  requests. Don't call a peer API from Odin code until the peer has
  published it and its contract is pinned.
- **Git.** Keep local commits within the authorized task scope. No
  remotes are configured; creating a remote or publishing requires a
  separate instruction.

## 8. Validation

Run from the repository root:

```bash
python3 scripts/validate_docs.py
python3 -m unittest discover -s scripts -p 'test_validate_docs.py' -v
```

For I0 contract tests, install the pinned Python dependency and run
`python scripts/check_runtime.py` in that environment with Go available;
see [`runtime/README.md`](runtime/README.md). Both implementations must
validate the same structural and semantic fixtures. The command fails if
their results differ.

For the current local service and orchestration prototype, install the root
`requirements.txt` in a virtual environment and run `make check` with that
environment's `PYTHON` and Go available. It validates the root fixtures in
both languages, runs the Python component/CLI suite, and checks documentation
and its regression suite. `make compatibility` retains the earlier `runtime/`
fixture checks. See [`docs/IMPLEMENTATION-STATUS.md`](docs/IMPLEMENTATION-STATUS.md)
for the synthetic demos and the distinction from live acceptance.

The standard-library-only validator checks the extraction metadata against
its schemas, frozen-source and live-output digests, the snapshot allowlist,
D0–D24 mapping presence, the schema-validated AC/DC/EC stable-ID registry
and unique defining rows in their canonical documents, the pinned Saga
contract digest, and local links and anchors, including editable research
wrappers. When adding acceptance IDs, append them to
`docs/provenance/STABLE-IDS.json` and advance the corresponding preservation
floor in `scripts/validate_docs.py` (`BASELINE_ID_COUNTS`); never reduce a
floor or remove a registry entry. Retain withdrawn IDs and their defining
rows. Historical and dated-research
evidence links are inventoried separately in `docs/provenance/HISTORICAL-LINKS.md`.
A pass proves documentation integrity, not semantic completeness or runtime
behavior. The regression suite exercises validator failures in isolated
temporary copies. Retained review summaries and current validation evidence
are in `docs/provenance/HANDOFF.md`; formal independent re-review remains
pending. I0 contract tests and local fake-backend component tests exist;
full harness and live acceptance remain I2–I3 work.
