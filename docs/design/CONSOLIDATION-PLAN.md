# Consolidation implementation plan and repository strategy

Date: 2026-10-16. **Status: proposal, partly recorded.** Later on
2026-10-16 the operator directed the Odin-owned parts to be recorded:
ODIN-ADR-006 to 015 are in [`../DECISIONS.md`](../DECISIONS.md) §4 and
the design documents are revised under them. The Saga-owned parts
(§3.3, drafts ADR-016 to 019) remain proposals pending issue X-14. This
document does not amend the decision record, the pinned Saga contract, or
any peer repository; where it and the record differ, the record wins. Where it proposes a change
to an inherited decision, it names the ADR that would record it and says
whose record the change belongs to. The decision record continues to
win until the operator records otherwise ([`../DECISIONS.md`](../DECISIONS.md)).

Evidence: four investigation reports dated 2026-10-16 in
[`../research/consolidation-2026-10/`](../research/consolidation-2026-10/README.md),
referred to below as the Go inventory, the Saga inventory, the
decision-record analysis and the mechanics report. Each claim about a
repository's code carries its `path:line` evidence there.

## 0. Summary

The operator's agent-runtime tools are delineated correctly by *kind of
fact* and incorrectly by *product*. Six repositories, four TUIs, five
event logs and ten cross-repository integration items exist for one
operator. This plan consolidates them into one repository with one
release train and three deployables, while keeping every boundary that
encodes a security property as a process boundary and every boundary
that encodes an ownership rule as a module boundary.

Three findings from the investigations reshape the earlier design
discussion and are built into this plan:

1. **The execution backend stays Saga.** Moving Saga's launcher,
   ledger, run lifecycle, approvals and stop operations into "an Odin
   backend" touches D1, D2, D4, D5, D17 and D23, which Saga owns. An
   Odin ADR cannot amend them (AGENTS.md §1). The only path is a
   decision in Saga's own record, a new contract version and a repin.
   So the backend keeps Saga's identity, record, contract and
   conformance checks, runs as a separate, independently restartable
   process with its own store and its own worker intake, and may share
   a repository and release train with Odin only after Saga's record
   says so. Odin consumes its event cursor and never receives worker
   transport.
2. **Saga has almost nothing to absorb.** No ledger, run lifecycle,
   digest or approval binding, reviewer key, cancellation with
   uncertain outcome, concurrency cap, TTL or kill switch exists in
   code (Saga inventory §B.11). About 900 lines of launcher validation
   and argv construction and 1,365 lines of `spec_dev` are reusable.
   The backend is new work wherever it lives, which makes keeping
   Saga's identity nearly free.
3. **The three process boundaries this plan relies on do not hold
   today.** Docker is reachable by several users and processes, no
   reviewer key exists, and no single process holds desktop input
   (Saga inventory §F.4). They are remediation items (§7), not
   assumptions.

## 1. What changes against the current documents

| Area | Current documents | This plan |
|---|---|---|
| Repositories (D14) | `saga` and `odin`; standalone repos stay where they are | One repository; imported histories; archived originals. Conditional on Saga's record (ADR-018) |
| Standalone tools (D10) | Separate products; braid as child process; skald via provider adapter; heimdall as later continuity surface with an ownership bridge | Capture, sensors and retrieval become modules of the three deployables; heimdall's task layer is retired by import into commitments; no bridge (ADR-006, 007, 011) |
| Task authority (D20.10) | Odin for Odin work, heimdall for native tasks, projected across | Odin's commitment record is the single editable task record (ADR-007) |
| Event stores | Odin history, skald archive, heimdall event log, Saga ledger, each its own store | One substrate with namespaces and one writer per namespace; the execution ledger stays a separate store owned by the backend and is only mirrored read-only (ADR-006) |
| Operator interfaces (D20.5) | Herdr workspace and Telegram | Adapters on one service API: summoned terminal conversation, bar, notifications, Telegram, voice later; one command path (ADR-010) |
| Inbound sources (§4) | Worker, Saga, Mimir, operator | Plus workstation observations and capture lifecycle as state-only or log-only sources; a typed, capped attention prompt as an outbound effect (ADR-010) |
| Review (D8) | One selective reviewer, Sonnet by default | Two reviewer positions on different model families, verdicts combined by service code, disagreement escalates; a hypothesis judged on D8's measures (ADR-013) |
| Second adapter (D19, D15.Eb) | Codex app-server or Pi RPC in Phase E | A fixture-only Pi RPC control after I2; full second adapter stays I5 (ADR-015) |
| Session topology | Service and sessions on one host | Service on the homelab; a workstation daemon hosts local sessions, sensors, capture and surfaces; bindings gain host identity and `host_offline` (ADR-009) |
| Desktop input (D21) | wayland-computer-use stays separate, excluded from planners | Its guarded input moves into a gated process of the workstation daemon that holds the seat lease; disabled until desktop authority is decided (ADR-011) |
| Preservation (D22) | dotprivate carries the package | Odin writes the package and runs git; dotprivate stays the operator's tool, off Odin's path (ADR-012) |
| I0 scope | Schemas, envelope, capability matrix, fake backend, fixture, mapping, isolation check | Event log and record schemas only; the rest moves to I1 (ADR-008) |
| Routing records | Class choice in code, unrecorded | Chosen class and rejected alternatives recorded for later oracle evaluation (ADR-014) |
| Bragi and Eir (D11, D12) | Saga components | Bragi as a scheduled Odin session class and Eir as an Odin assignment class **only if** Saga's record transfers them; Eir keeps an operator path that needs neither Odin nor the backend (ADR-017) |

Not changed: D0's product promise, D2's enforcement guarantees, D4's
ledger authority, D5, D6, D9, D17, D23's backend rule, D24's credential
rules, the Saga API boundary, the fake-backend rule that no non-Saga
backend claims Saga's guarantees, and the sequence rule that I3 and every
live run wait for Phase B.

## 2. Target architecture

### 2.1 Deployables and processes

| Deployable | Processes | Language | Runs on |
|---|---|---|---|
| **Homelab service** | Odin service (intake, routing, records, sessions, memory, scheduler, outbox, gateway API, Telegram adapter); compactor; reviewer signer (holds the reviewer identity key; signs verdict records from isolated review sessions; readable by no other process) | Python (uv workspace member) | Homelab VM, always on |
| **Execution backend (Saga)** | Admission and ledger process (only Docker holder; own store; worker intake; event cursor; stop and kill switch); worker images | Python; root-owned versioned install, never a user-writable checkout | Homelab VM |
| **Workstation daemon** | Session host (dials out; spawns SDK and RPC sessions; drives Herdr through its CLI); sensors (compositor, Herdr agents, browser, file trees); capture module (transcripts, with a local durable spool); surface adapters (bar, notifications, summoned terminal client, push-to-talk); guarded desktop input as a separate, gated process under its own Unix user | Go (one root module) | Workstation; later the laptop |
| **Harness integration packages** | Claude Code plugin (instructions, skills, hooks, MCP server); Pi extension and RPC adapter | Markdown, JSON, Python MCP server, TypeScript extension | Wherever sessions run |

Names above are descriptive placeholders. D13 forbids the standalone
repository names, mythological names and the `saga-` prefix for Odin
deliverables; no Odin prefix exists (X-5). ADR-019 chooses the names.

### 2.2 Boundaries that must survive as process boundaries

| Boundary | Why | Enforced by |
|---|---|---|
| Docker holder | D2: enforcement lives in Saga; a planner that can launch is a planner that can bypass approval | Backend process alone has the socket; its install path is root-owned; the operator's user leaves the docker group on the VM; Odin, Bragi, Eir and keepalive containers launch through the backend or by operator-only operations |
| Reviewer key holder | D2.4b, B-10: a verdict is accepted only under a verified key the planner cannot use | Signer process and uid; the Odin service never reads the key |
| Desktop input holder | D21.4: one agent has input on a seat at a time; a planner must never reach the desktop | Gated process under a dedicated uid that alone owns the input socket; disabled until a delegation names desktop authority |
| Execution ledger writer | D4.1, ADM-1: a client must not record approvals or state for its own submission | The backend owns the ledger store; the substrate mirrors it read-only |
| Service to backend code | G4: Odin never imports Saga's code | Separate workspace members and an import-linter rule in CI |
| Worker transport | B-17, MQ-5: workers never reach the planner | Worker events terminate at the backend's intake; Odin reads the cursor |

### 2.3 The substrate

One append-only event store with named namespaces, each with exactly
one writing component, its own retention and redaction rules, and
revisioned records committed in the same transaction as the history
they belong to (I/O contract §9 unchanged).

| Namespace | Writer | Content | Standalone sink |
|---|---|---|---|
| Odin history | Odin service | The log of §3: dispatches, messages, decisions, routing outcomes, references | none |
| Transcript archive | Capture module (via spool) | Lossless transcript records, content-addressed bytes, gaps, checkpoints, projections | skald's `archive.sqlite` keeps working for "useful without Odin" |
| Surface events | Workstation sensors | Focus spans, observed surfaces, agent observations, sensor health | A sensor-only binary with a local store |
| Execution ledger (mirror) | Backend, through its API and cursor | Runs, delegations, approvals, verdicts, operations | The backend's own store is authoritative; the mirror is read-only |

Retrieval (braid) runs in-process as a library over published, scoped
namespace data in its own per-dataset files. It never indexes the active
chat (X-4). Its O(dataset) digest per write means batched publication,
not per-event updates (Go inventory §D.6).

### 2.4 Why not the alternatives

Running the service on the workstation breaks always-on. Two services
breaks D20. Leaving the backend out of the repository keeps five release
trains and the dormant Saga repository as a gate on everything. Keeping
heimdall's task layer keeps two prioritisers and the EC-05 bridge whose
only purpose is reconciling a split nobody chose on the merits.

## 3. Governance track

The decision-record analysis is the authority for this section. Two
tracks run in parallel, and the second gates the repository merge.

### 3.1 Baseline first

ODIN-ADR-001 to 005, AC-31 to AC-36, the manifest digests and the
exception clause "except for explicitly recorded operator decisions in
Odin's ADRs" exist only in the working tree. At HEAD `cb55ecc` nothing
may differ from the frozen copy. **Commit the working tree and the
untracked `LICENSE`, run the validator, and only then record anything.**

### 3.2 Track A: decisions Odin can record now

Recorded in `DECISIONS.md` §4 with the decision map updated in the same
change. Drafts in the decision-record analysis §C.

| ADR | Title | Supersedes or amends | Depends on |
|---|---|---|---|
| 013 | Two reviewer positions with service-run consensus (hypothesis) | D8.5; single-reviewer reading of D8.3 and D8.4 | none |
| 014 | Session-class decisions recorded for later evaluation | amends ODIN-ADR-004 | 013 |
| 006 | One event substrate with namespaces | D10.1 and D10.2 delivery modes for Odin | none |
| 007 | The commitment record is the single task authority | D20.10; D10.5 | 006 |
| 008 | I0 narrowed to the event log and record schemas | blueprint §7, I/O §13 row B, roadmap I0 and I1 | 006, 007 |
| 009 | Workstation daemon and session host | clarifies D7.2, D20.1 and D20.2; amends D24.3 for Odin's classes | 006, 007 |
| 010 | Operator surfaces, new inbound sources and typed attention prompts | D20.5; amends D20.8; redefines legacy L-PU-1 "nudge" | 006, 009 |
| 011 | Desktop input as a gated capability of the workstation daemon | amends D10.4 placement; implements D21.4 | 009 |
| 012 | Preservation without dotprivate on Odin's dependency path | D22.3, D22.5 for Odin | 006 |
| 015 | Early Pi RPC adapter as a fixture-only control | amends D15.Eb timing | 008, 009 |

Each states that Saga's record is not amended. Each is the first
supersession of a locked inherited clause while Saga's record is still
authoritative, so each adds an ownership note under the affected `Dn`
heading without editing the verbatim carried text.

### 3.3 Track B: decisions that belong to Saga's record

Made by the operator **in Saga's repository**, never from this one
(AGENTS.md §3). Then Saga publishes a new contract version, Odin pins it
and rechecks Appendix B (X-3). Only after that are ADR-016 to 019
recorded here.

| Saga-side decision | Clauses | Odin ADR that follows |
|---|---|---|
| The backend may share a repository and release train with Odin, as a separate process with its own store, record and contract | D14.1, D14.7, D1.2 | 016 |
| Workers report to the backend's own intake; Saga stops using MQTT for worker transport (the broker stays; it serves other homelab systems) | D3.3, D13.4a, D15.B, MQ-1 | 016 |
| Bragi and Eir transfer to Odin session and assignment classes, with Eir's operator-invoked path outside both failure domains | D11, D12.1, D17.4b | 017 |
| Repository names, the `saga-` prefix, and whether `odin` may name the monorepo | D13.1, D14.1 | 018, 019 |
| The D14 handoff recorded, or replaced by the merge decision | D14.6 | 018 |

### 3.4 Track C: decisions in peer repositories

Each is a short recorded note in that repository by the operator before
it is archived: heimdall retires its task, checkpoint and decision
authority and the skald–heimdall amendment with it; skald's capture
library gains the sink interface and the archive becomes one sink among
two; braid is embedded as a library; wayland-computer-use's guarded
input moves to the daemon and the Codex plugin stays standalone. The
licenses are already Apache-2.0 for heimdall, skald, braid and WCU;
Saga's is recorded on import after a `git shortlog -sne` check for other
contributors.

### 3.5 Document changes and order

From the decision-record analysis §D, which lists every file, whether it
is a manifest output, and what the validator checks.

1. Commit the baseline. Validate.
2. Record Track A ADRs and update the decision map together.
3. Edit the I/O contract, then the blueprint, then the roadmap, with the
   acceptance scenarios and the ecosystem plan alongside. Withdrawn ids
   (EC-05, EC-08, EC-09, AC-20) stay in the text; re-scoped ids (AC-19,
   AC-22, AC-24, AC-25) get notes; new ids start at AC-37, EC-13, X-11,
   roadmap gate G-9.
4. Edit the entry documents: README, `docs/README.md`, AGENTS.md.
   CLAUDE.md and AGENTS.md §3 only when ADR-018 takes effect.
5. Update manifest digests and transformation notes last. Never touch a
   source hash. All three LEGACY-REQUIREMENTS entries take the same
   digest.
6. Write the HANDOFF receipt section. Run the validator. Check against
   the frozen copy by hand.
7. Keep ADR-016 to 018 as labelled proposals in the ecosystem plan until
   Track B is done.

Do this before the import: scope the validator's link check to Odin's
own documents, because it walks every Markdown file in the repository
and the imported trees produced 33 failures in rehearsal (mechanics
report §2.5).

## 4. Repository strategy

### 4.1 Trunk and import

The existing `odin` repository is the trunk, so its hashes and its
frozen `docs/history/` stay unchanged. Each imported repository is
rewritten in a fresh clone with
`git filter-repo --to-subdirectory-filter <name> --tag-rename ':<name>/'`
and merged with `--allow-unrelated-histories --no-ff`, one merge commit
per repository, pushed directly and never squashed. Follow-up
restructuring happens in separate commits so every imported path keeps
an unbroken log. Commit maps are kept under `scripts/imports/`.
Procedure and rehearsal results: mechanics report §2.

The originals are **archived, never deleted or renamed.** About 846
commit-pinned links point into them, most from frozen research files
that cannot be edited. Each gets a pointer README and the GitHub archive
flag.

### 4.2 Layout

Top level by deployable, not by language, so path filters, release
notes, the manifest and Docker COPY lines map onto what is deployed.

```text
<repo>/
├── README.md  AGENTS.md  CLAUDE.md  LICENSE  NOTICE  justfile
├── go.mod  go.sum                       # one Go module
├── pyproject.toml  uv.lock              # one uv workspace (virtual root)
├── release/manifest.json                # the release train
├── .github/workflows/{ci.yml,release.yml}   .githooks/pre-commit
├── substrate/                           # shared contracts and libraries
│   ├── schemas/                         # JSON Schema records, envelope, fixtures (I0)
│   ├── eventlog/ records/ ids/ retrieval/   # Go packages
│   └── python/                          # uv member mirroring the schemas
├── homelab/                             # deployable 1
│   ├── service/                         # uv member: Odin service processes
│   └── backend/                         # uv member: the execution backend (Saga); import-linter wall
├── workstation/                         # deployable 2 (Go)
│   ├── cmd/<daemon>/  cmd/<sensors-only>/
│   └── internal/{sessionhost,sensors,capture,surfaces,desktopinput}/
├── integrations/                        # deployable 3
│   ├── claude-code/.claude-plugin/marketplace.json
│   ├── claude-code/<plugin>/            # plugin root with its own LICENSE
│   └── pi/<extension>/
├── <imported>/ ...                      # heimdall/ skald/ braid/ wayland-computer-use/ saga/
│                                        # histories intact; transitional; emptied as code moves
├── deploy/{homelab,arch,systemd}/
├── scripts/                             # validate_docs.py, release.py, imports/
└── docs/                                # unchanged; docs/history/** frozen
```

The imported directories keep their repository names because they *are*
those projects with their histories, not new components reusing the
names. As code moves into `substrate/`, `workstation/` and `homelab/`
it takes plain functional names, and the imported trees shrink to their
standalone binaries or disappear. ADR-018 states this reading of D13
explicitly.

### 4.3 Build systems

- **Go:** one module at the root, `go 1.25.0`, `toolchain go1.27.1`, no
  committed `go.work`, an `ignore` directive for `node_modules`,
  `integrations`, `deploy` and `docs`. heimdall's bare `heimdall/...`
  import path is rewritten (527 imports in 247 files). Each imported
  tree keeps its own `internal/`; shared code lives under `substrate/`.
  Every former binary still builds with `go build ./<name>/cmd/<name>`.
  No root `vX.Y.Z` tags, ever, because `v2` would force `/v2` import
  paths repository-wide.
- **Python:** one uv workspace with one `uv.lock`. Members: the Odin
  service, the backend, the substrate mirror, the MCP server. Docker
  images install a subset with `uv sync --package <member> --frozen`;
  CI uses `--locked`. The service and backend members may not import
  each other; CI enforces it.
- **TypeScript**, only for the Pi extension and, if chosen, hook code
  built into the plugin directory. If the Odin service is written in
  TypeScript instead of Python, the mechanics report §10.2 gives the
  pnpm layout; everything else here stands.
- **Orchestration:** a root `justfile` with one recipe group per
  deployable. No Bazel, Nx or Pants at this scale.

### 4.4 Versioning and release train

Semver per deployable, tags `<deployable>/vX.Y.Z`, and
`release/manifest.json` as the train: at every commit it says which
versions of the deployables belong together and is what gets deployed.
Imported version lines continue (`skald/v0.1.2`). A stdlib
`scripts/release.py` refuses a dirty tree or a non-increasing version,
bumps the manifest and the plugin's `version`, commits, tags with
path-scoped notes, and pushes atomically. Shared code changes bump
nothing by themselves; each deployable that should ship them is released.

### 4.5 CI and packaging

`ci.yml`: a path-filter job, then Go, Python, plugin and docs jobs, then
one `ci-ok` aggregator as the only required check. The docs job always
runs the validator and refuses modifications under `docs/history/`.
`release.yml` runs on `*/v*` tags and dispatches by deployable. Nested
workflows from imported repositories are inert and get ported.
Arch packages: one PKGBUILD per binary under `deploy/arch/`, built with
`makepkg -si`, `license=('Apache-2.0')`, units installed under
`/usr/lib/systemd/user`. The backend ships as a Docker image plus a
root-owned install on the VM.

### 4.6 Licensing

Root `LICENSE` (Apache-2.0, currently untracked) and a minimal `NOTICE`
naming the imported projects. Copies of `LICENSE` wherever a
distribution is cut from a subdirectory: the plugin root, each Python
member, each image, each package. Regenerate third-party notices per
shipped binary after `go mod tidy`, since heimdall's pinned
`docs/licenses/` tree goes stale. dotprivate stays MIT and outside.

### 4.7 Hygiene and ownership rules

- Protect `main` from force-push and deletion; require only `ci-ok` on
  pull requests; keep a bypass for import merges and release commits.
- `.gitattributes`: `-text` on `docs/history/**`, pinned contracts and
  dated research; `linguist-generated` on lockfiles; LF on shell,
  PKGBUILD and unit files.
- Pre-commit hook refuses staged modifications under `docs/history/`
  and runs the validator.
- Conventional commits with a deployable scope.
- AGENTS.md §3 "never edit Saga or any peer repository from this one"
  becomes a per-component ownership rule inside one repository: Saga's
  decision record, contract and backend code remain Saga-owned and
  change only through Saga's own process; the Docker, host, volume and
  secret prohibitions stay verbatim.
- Agent instruction files inside imported trees are not loaded as
  instructions; none exist today, keep it so.

### 4.8 What stays outside

Herdr (third-party workspace, driven through its CLI), dotprivate (the
operator's tool; Odin's export directory must never sit inside a
dotprivate `.private` clone because the background sync would race it),
muninn (dormant), the Mosquitto broker (shared homelab infrastructure
that Saga simply stops using for worker transport).

## 5. Build sequence

Phases P0 to P7 map onto the roadmap's increments and gates. They add
three gates: **G-9** Saga-side decisions recorded and a new contract
pinned; **G-10** peer-repository decisions recorded; **G-11** import
complete with every former binary building from the trunk. The phase
rule D15.8 stands: I3 and every live run wait for the backend's Phase B
exit, now measured by the same conformance checks in the same
repository. Fake-backend evidence establishes nothing about production.

P2 does not depend on P0's Track B or on P1, so substrate work starts at
once.

### P0. Baseline and governance

Goal: a committed baseline and the Track A record.

- Commit the working tree and `LICENSE`; validate.
- Operator decisions: the backend stays Saga (recommended yes); whether
  Saga is active (§3 item 1); the service language (recommended Python,
  so `spec_dev` and the launcher code are reused and the backend and
  service share one workspace); names (X-5).
- Record ADR-013, 014, then 006 to 012 and 015; edit documents in the
  order of §3.5; update the manifest; write the receipt; validate.
- Scope the validator's link check; add `.gitattributes`, the hook and
  the `.gitignore` entries.
- Operator, in Saga's repository: record the Track B decisions; publish
  the contract version; repin here; recheck Appendix B. Then record
  ADR-016 to 019. (Gate G-9.)
- Operator, in each peer repository: record the Track C notes. (G-10.)

Exit: validator passes at HEAD; Track A recorded; G-9 and G-10 either
met or explicitly open with ADR-016 to 018 held as proposals.

### P1. Repository consolidation (after G-9 and G-10)

Goal: one repository, every former binary building from it.

- Freeze heimdall, skald, braid, wayland-computer-use and saga; push
  WCU's 12 local commits first so the public copy and the imported copy
  agree.
- Import each with filter-repo on an `import/2026-10` branch; save
  commit maps; fast-forward `main`; push with tags.
- Separate commits: single `go.mod`; import rewrites; `ignore`; `go mod
  tidy`; tests; build every `cmd`; move PKGBUILDs and units into
  `deploy/`; port nested workflows; create the uv workspace with Saga's
  Python under `homelab/backend/`; add the manifest, `release.py`,
  `release.yml`; first tags continuing the old lines.
- Archive the originals with pointer READMEs.

Exit (G-11): `go test ./...` and `uv run --all-packages pytest` pass;
`heimdall`, `skald`, `braid` and the WCU servers build and run
standalone from the trunk; validator passes; archives in place.

### P2. I0: substrate and record schemas (ADR-008)

Goal: the versioned contracts everything else is built against.

- `substrate/schemas/`: the event envelope and namespaces (EC-01); the
  §2 records with the changes from ADR-007 and 009: Commitment gains
  checkpoint and task-decision fields and the owner, assignment and
  budget fields heimdall never had; SessionBinding gains host identity
  and `host_offline`; an Environment record; Review carries positions;
  a SessionClassDecision record (ADR-014). Fixtures for the duplicate,
  stale and unknown cases.
- Go `substrate/eventlog`: reuse heimdall's store design (append-only
  log, request-id idempotency, replay) and drop its single-JSON-blob
  projection. Python mirror validated against the same fixtures.
- Mapping table from heimdall's record types to commitments (Go
  inventory §B.5) checked into `substrate/schemas/migrations/`.

Exit: both languages validate the same fixtures; the duplicate, stale
and unknown cases have explicit semantics; no peer API is invented as
implemented.

### P3. I1: service foundation and backend skeleton

Goal: the homelab deployable runs, against the fake backend for the
service and against conformance checks for the real one.

Service: transactional core, intake and cursors, outbox, scheduler,
direct stop, CLI; the gateway API (local socket, command endpoint, event
stream) that every surface and the session host use; the Telegram
adapter with hash-bound approvals (always on, so it lives here, not on
the workstation).

Backend (Saga): published admission schema (ADM-10); client-minted ULID
operation ids with `409` on conflicting reuse; copy-first-hash-the-copy
provisioning that refuses symlinks and never accepts a host path;
argv-by-construction Docker driver with resource limits, labels and no
`--rm`; ledger with D5 states; event cursor; cancellation with
`acknowledged` or `uncertain`; the four stop operations and a persisted
kill switch; concurrency cap; worker intake replacing MQTT for Saga's
use, with per-run credentials; the conformance checks CT-01 to CT-24
started. Reuse the launcher's validation, argv, secret handling and
result discipline (about 900 lines) and fix the confinement holes in
Saga inventory §B.9 while porting. Install root-owned.

Reviewer signer: key custody and a signing API; nothing else yet.

Exit: AC-01, AC-02, AC-27 against the fake backend; the real backend
passes the admission and ledger subset of the conformance checks; the
import-linter wall holds; the fake and the real backend pass the same
contract test double.

### P4. I2: first harness and workstation daemon v0

Goal: one bounded assignment survives replacement of its session, and
the workstation is a session host.

- Claude Code adapter through the Agent SDK; the plugin under
  `integrations/claude-code/`; profiles enforced by PreToolUse; briefing
  and `zoom`; session lifecycle; compactor checks (AC-34, AC-35).
- Workstation daemon v0: dial-out session-host protocol with host
  identity and heartbeat; environment probe; `host_offline`; local
  sessions under a provisioned credential lineage that is never the
  development login; Herdr driven through its CLI locally (SSH plus
  `herdr --machine` remains the path for an environment without the
  daemon).
- Sensors v0 extracted from heimdall under functional names: compositor
  observer (without `dispatch.go`), Herdr agent observation with
  explicit socket configuration instead of task-bound discovery. The
  model split is the keystone refactor; budget it as large.
- Capture module: skald's library behind a `Sink` interface, collector
  and discovery moved to a public package, a local durable spool, and
  one atomic append per batch into the transcript namespace; skald's
  archive remains the standalone sink. Unify the namespace key on
  machine-id.

Exit: AC-04; a live transcript lands in the transcript namespace with
gaps and checkpoints preserved; the daemon going offline marks sessions
unavailable, not failed, and they resume on return.

### P5. The two merges that hurt most

Goal: one task authority and one log.

- Import tool: `heimdall.db` to commitments with original identities and
  revisions as provenance and a receipt; heimdall-side edits refused
  after import; task CLI retired; the bar module reads the service;
  human view v0 (summoned terminal client: overview, needs-you,
  commitments, transcript browsing) replaces both TUIs.
- Transcript archive: write a reader for skald's half-built `changes`
  table and ingest the existing 1.5 GB archive into the namespace
  incrementally rather than migrating it in one step; recompute
  projections in the namespace; honour redaction across namespaces.
- Attention tiers (ADR-010) in shadow: ranking recomputed on every event,
  deltas logged, nothing sent; the heimdall focus and idle signals and
  capture session-end as boundaries.

Exit: no second editable task store; one view shows commitments, runs
and transcripts with their owners attributed; capture gaps visible; the
shadow log shows what would have been sent and when.

### P6. I3: governed project, plus the controls (the Pi control starts at I2's exit, per ADR-015)

Requires the backend's Phase B exit (G-4) and gates G1 to G5 as in the
roadmap.

- First live submission through the backend; the CLI and Odin face the
  same refusals; Telegram approvals bound to proposal digests.
- Two reviewer positions (ADR-013): isolated review sessions, service-
  combined verdicts signed by the signer, disagreement to the operator;
  measured against single review and an equal extra verification budget.
- Pi RPC control adapter (ADR-015) against the fake backend, started at
  I2's exit and finished alongside I3 preparation; capability matrix
  published, gaps recorded as fixture evidence.
- Attention prompts leave shadow only when the outcome records support
  the caps; voice stays backlog until its data-policy decision.

Exit: one real project passes admission and finishes with evidence; an
interrupted session is replaced without losing the assignment.

### P7. I4 to I7, re-scoped

As the roadmap, minus EC-05, EC-08 and EC-09: second project and adopt
and take-control (I4); full second adapter and the memory comparison
(I5); retrieval as a library, evaluators in shadow, local session backend
(I6); desktop input as the gated process only after the operator decides
desktop authority (I7), with a dedicated uid owning the input socket and
a spike to verify whether the compositor can deny the virtual-keyboard
protocol and dispatcher IPC to other clients. Until that is verified the
seat lease binds cooperating clients only, which is what the ecosystem
plan already says.

## 6. Component migration summary

Difficulty: S days, M one to three weeks, L more than three weeks or a
semantic redesign. Full tables with evidence: Go inventory §F, Saga
inventory §F.

| Component | Destination | Diff. | Note |
|---|---|---|---|
| heimdall sensor adapters (compositor, Herdr, WCU observer, browser observation, file trees) | Workstation daemon sensors | M, browser L | Sensors are entangled with task records through one 62-field state struct; a refactor, not a move |
| heimdall task core and continuity (tasks, contracts, decisions, checkpoints, dependencies, progress) | Odin commitment records, by import | L | Adds owner, assignment and budget; 2,950 lines of invariants to map |
| heimdall workspace and actuation (snapshots, recovery, dispatch, app recipes), 9.6k lines | Workstation gated capability, or defer | L | A sixth layer the earlier discussion omitted |
| heimdall TUI, Neovim UI, bar | Human view; bar adapter | L (view), S (bar) | The ranked planner never existed |
| heimdall `session`, `conversation`, hook relay | Delete in favour of the capture module; relay to the plugin | M | Duplicates skald with lossy metadata |
| heimdall `store` design | Substrate eventlog | L | Reuse the design, not the blob projection |
| skald `sessionrecord`, `sessioncapture` | Substrate record library; capture module | S | Already store-agnostic with a live second consumer |
| skald collector, discovery, archive | Capture module with `Sink`; standalone sink kept | M, archive L | 1.5 GB live data; projections inside `Ingest` |
| skald TUI, socket API, CLI | Human view replaces the TUI; API and CLI stay standalone | M | |
| braid `pkg/braid` | Substrate retrieval library | M | Own file per dataset; batched publication |
| Saga launcher validation, argv, secrets, results | Backend admission and driver | M | Fix confinement holes while porting |
| Saga ledger, lifecycle, bindings, cursor, stop, conformance | Backend, new code | L | Nothing exists to absorb |
| ratatoskr intake and guidance publisher | Backend intake and guidance operation | M | Never the Odin service |
| ratatoskr send-keys prompts, markers, `commands/` | Delete | S | |
| Saga worker image and hooks | Backend worker image | M | Per-run lineages; drop tmux driving |
| Odin persona, container, start scripts | Frozen as history; re-implemented in the service and plugin | L | Behaviour that exists only in prose |
| Mimir persona and file protocol | Review session class plus the signer | L | No key custody exists today |
| Bragi, Eir | Session and assignment classes, conditional on Saga's record; Eir keeps an out-of-band path | M | |
| `spec_dev` package | Odin service module | S to M | 86 tests; nothing calls it today |
| keepalive and auth scripts | Backend credential-lineage provisioning, one refresher per lineage | M | |
| WCU `Desktop`, guards, capture helper, system checks | Gated desktop-input process | L | Lease complete in-process; device-wide needs a dedicated uid |
| WCU observation and accessibility | Daemon observation capability | M | Privacy-sensitive |
| WCU stdio servers, skill | Plugin shims and skill | M | Shims must carry caller identity |
| WCU Codex manifests, evaluations, reports | Keep standalone | S | |
| dotprivate | Keep standalone; off Odin's path | S | |

## 7. Security remediation (must close before the matching claim)

| Item | Found | Closes before |
|---|---|---|
| Launcher runs as root from a user-writable checkout; `prd` accepts any host path including `..`; `workspace_source` may equal the workspaces root; Gitea credential not bound to the project; symlink at `PRD.md` followed as root; requester unauthenticated | Saga inventory §B.9 | Any run through the backend (P3) |
| Operator user in the docker group on the VM; Eir runs as that user; Odin, Bragi and keepalive containers launched outside the launcher | Saga inventory §F.4.1 | Claiming "only Docker holder" (P3) |
| No reviewer key; Odin and Mimir share a container, uid and filesystem | Saga inventory §F.4.3 | Any verdict accepted by the backend (P6) |
| Broker unauthenticated, no TLS; seven documented topics have no publisher | Saga inventory §A.6 | Shadow period with workers (P3) |
| Shared credential volume across workers; refresh tokens single-use | Saga inventory §B.4 | Per-run lineages (P3) |
| Desktop input reachable by every uid-1000 process; no caller identity in WCU; a recorded overrun where an agent consumed 23.7M tokens and falsely reported stopping | Saga inventory §D.6 to §D.9 | Enabling desktop input (P7); mechanical stop and budget for every session class (P3) |
| Development login on the workstation next to Odin's lineage | AGENTS.md §6; D24.6 | Workstation sessions (P4) |

## 8. Data migration

| Data | Size | Plan |
|---|---|---|
| heimdall `heimdall.db` | about 7.5 MB, written 2026-10-15 | One-time import to commitments with provenance and a receipt (P5); keep the file read-only afterwards |
| skald `archive.sqlite` and backups | 1.5 GB plus 2.4 GB of pre-upgrade backups | Incremental ingest through the `changes` table into the transcript namespace (P5); the archive stays the standalone sink; backups stay skald's |
| Saga `master-journal.md`, project wikis, lessons, `launch-results/`, `incoming-*` | On the VM, not inspected here | Scoped migration import per I/O contract §14 at I3; never as repository fixtures |
| Live workstation `~/.claude/projects` transcripts | Growing | Captured by the module from P4; nothing moves |

## 9. Risks and rollback

- **Governance.** First supersession of locked clauses while Saga's
  record is authoritative; two records disagree until Track B is done.
  Mitigation: Track A ADRs each state what they do not amend; Track B
  decisions live in Saga's repository; the validator and a manual
  frozen-copy check run before every push.
- **Guarantee laundering.** Calling the backend "Saga" without its
  conformance checks passing. Mitigation: the same CT checks gate the
  claim in-repo as they would across repos; fake-backend evidence is
  labelled.
- **A monolith that stalls stalls everything.** Mitigation: standalone
  binaries for capture and sensors with their existing tests; path-
  filtered CI; per-deployable releases.
- **The heimdall refactor is larger than it looks.** Mitigation: P4
  extracts only the compositor and Herdr observers; everything else in
  the sixth layer is deferred until a delegation needs it.
- **Capture over a remote link breaks the one-transaction checkpoint
  contract.** Mitigation: a local durable spool and idempotent re-read.
- **Scope creep into the first proof.** Surfaces, voice, desktop input,
  Bragi and Eir are explicitly after I3 or conditional.
- **Rollback.** Every import is a merge commit on a branch; the
  originals are archived, not deleted; commit maps translate old SHAs;
  heimdall's database is kept read-only after import; skald's archive is
  never modified by the ingest. Reverting to separate repositories is a
  matter of unarchiving and reverting the merge commits before any
  restructuring commit lands, so the import and the restructuring are
  deliberately separate commits.

## 10. Decisions the operator must make

1. Does the execution backend stay Saga, with its identity, record and
   contract, as a separate process that may share the repository?
   Recommended yes. Everything in Track B depends on it.
2. Is Saga active (§3 item 1)? If not, Track B is a day of recording
   decisions in a dormant repository, which is fine, but say so.
3. Service language: Python (recommended) or TypeScript.
4. Names: repository, deliverable prefix, the three deployables, the
   plugin, within the D13 constraints and the forbidden list in the
   decision-record analysis §E. Resolves X-5 through ADR-019.
5. Eir's operator-invoked path that needs neither Odin nor the backend:
   a documented host procedure, or a separate minimal unit.
6. Data policy for voice transcription (local only, per D9) and for
   sending evidence packs to a second review provider.
7. Desktop authority (§3 item 9), which gates the desktop-input process.
8. Licensing on import of Saga after the contributor check.
9. When to archive each original repository; muninn's future (§3 item 4).

## 11. Effort, as estimates

For one operator with coding agents. These are ranges, not commitments,
derived from the S/M/L marks in the inventories.

| Phase | Estimate | Dominant cost |
|---|---|---|
| P0 | 1 to 2 weeks | Document edits in authority order; Track B in Saga's repository |
| P1 | 1 week | Import rewrites and the Go module merge; CI port |
| P2 | 2 to 3 weeks | Record schemas in two languages against one fixture set |
| P3 | 6 to 10 weeks | The backend is new code end to end; conformance checks |
| P4 | 6 to 8 weeks | SDK adapter and plugin; daemon protocol; the heimdall model split |
| P5 | 3 to 5 weeks | Commitment import; incremental archive ingest; human view v0 |
| P6 | 4 to 6 weeks | Live submission; two-position review; Pi control |
| P7 | As the roadmap | |

The two things that shorten this are the operator confirming decision 1
early and starting P2 in parallel with P0.
