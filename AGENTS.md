# AGENTS.md — developing Odin

Instructions for anyone, human or coding agent, working **on** this
repository. They are not Odin's runtime persona. The instructions that
make a deployed session behave as Odin or Mimir belong to the
integration package, which is derived at code extraction. The legacy
personas in `docs/history/` are evidence, not instructions for you.

## 1. Current state

- Documentation scaffold with a local documentation validator and
  extraction-metadata schemas. No Odin service implementation, runtime
  record schemas, synthetic runtime fixtures or runtime acceptance tests
  exist yet. Do not describe them as implemented or tested.
- This is a candidate documentation handoff from Saga (snapshot
  `2026-10-14-14fdab3`), and the handoff is **not recorded**. Until it is,
  Saga's decision record remains authoritative and these documents must
  agree with the frozen copy.
- The first implementation work is **I0** (contracts and fixtures),
  then **I1** and **I2** against a fake Saga backend. **I3** and every
  live delegated run require Saga Phase B ([roadmap](docs/ROADMAP.md)).

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

Never edit Saga or any peer repository from this one.

## 4. Architecture in brief

- **Two loops.** The service loop is ordinary code: intake, records,
  routing, scheduling, outbox, budgets, session lifecycle. The harness
  loop is a Claude Code session started through the Agent SDK. Most
  events never reach a model (I/O contract §4).
- **One transactional core.** SQLite (WAL) holds records, inbox, outbox,
  cursors, messages and tree nodes. JSONL files and `view.json` are
  regenerated projections (§9).
- **Commitments are records, not memory.** Summaries serve recall; open
  obligations live in commitment records (D7).
- **Saga boundary.** Odin reaches Saga only through its API (D1.3).
  Saga's ledger decides whether a run was approved or completed (D4);
  Odin's history never does. Odin requires the capabilities in the I/O
  contract's Appendix B.
- **Runtime adapters.** Each adapter publishes a capability matrix
  (start, resume, inject mid-turn, interrupt, budget, model and effort,
  transcript, hooks, profile enforcement, attachable view,
  permission-prompt relay). The service refuses a session class whose
  required capabilities are missing. The adapter translates assignments,
  events and results; it does not reimplement the harness. Claude Code
  through the Agent SDK comes first. Build no universal adapter framework
  before a second adapter exists (D19). Don't rely on interactive-only
  behaviours: channels, plugin monitors, teammates (D7).
- **Capability profiles** (planner, reviewer, worker, desktop worker,
  subagent) are enforced before tool execution, not by prompt (§7).
- **Effects** are at-least-once with stable operation ids, explicit
  `unknown`, and reconciliation before retry; nothing claims
  exactly-once (D6, §9).

## 5. Fake backend versus live Saga

- The fake Saga backend implements Appendix B for development and the
  acceptance scenarios (I0 to I2). Label every result obtained with it
  as fake-backend evidence.
- Never present the fake backend, or any backend other than Saga, as
  providing Saga's guarantees (isolation, enforced limits, durable run
  records, recovery). Work with external effects goes only through Saga
  (D23).
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
- A session process holds only its model credential. The Saga token, the
  reviewer identity key and the Telegram token stay in the service.
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
  muninn, wayland-computer-use). No Odin deliverable prefix is defined
  yet (issue X-5).
- **Terms.** Use worker, run, stream, delegation, commitment,
  assignment, planning session, evaluator, Saga launcher, Saga events,
  and the Saga adapter (Odin's side). Don't use overseer, navigator,
  critic, judge or master as agent names. Legacy names (dvergr,
  instance, Heimdall for the launcher, Ratatoskr) stay only in history
  and in code until each rename lands. In prose, say "Saga's launcher",
  never bare "Heimdall".
- **Formats.** Every machine-read file is validated JSON or YAML with a
  schema. Markdown is for prose.
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
```

This standard-library-only command checks the extraction metadata against
its schemas, frozen-source and live-output digests, the snapshot allowlist,
D0–D24 mapping presence, AC/DC/EC identifier preservation, the pinned Saga
contract digest, and local links and anchors. Historical and dated-research
links are inventoried separately in `docs/provenance/HISTORICAL-LINKS.md`.
A pass proves documentation integrity, not semantic completeness or runtime
behavior. The semantic review and standalone-check evidence are in
`docs/provenance/HANDOFF.md`. Runtime tests will be added in I0–I3.
