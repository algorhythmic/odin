# algorhythmic/braid: what it is, how it relates to Saga, and what it changes in the two drafts (as of 2026-10-14)

Snapshot reviewed: `main` at commit `41bc392` (2026-09-09), the only branch, also tagged `v0.1.0`.
Method: a shallow clone into the session scratchpad
(`/tmp/claude-1000/-home-david-Projects-saga/ee1f44ea-6827-4f1f-a443-1eaa50e37a14/scratchpad/repos/algo-braid/braid`),
read as data. Nothing from the clone was executed, built or installed. Commit, tag, CI and repo metadata
came from the GitHub REST API. To work out which "Heimdall" braid serves, I read only the READMEs of two
sibling repos by the same owner (`algorhythmic/heimdall`, `algorhythmic/skald`). I did not review those
repos.
Citation base for braid files: `https://github.com/algorhythmic/braid/blob/41bc392/<path>`. Saga
files are cited by their absolute local path and line number.

## 1. Identity: what braid is, its size, history, license, deployment, and references to Saga

### Takeaway
Braid is a small Go library, CLI and versioned stdio subprocess for "explainable retrieval that fits a budget". It fuses
SQLite FTS5/BM25, optional embedding cosine (Ollama), anchor-seeded PageRank over a typed graph, and
recency. It then packs a diverse, dependency-complete context set bounded by cost or bytes, and attaches a `why` to every item.
It is **not** a memory, summarization or log system, a worktree manager, or a Saga component.
Its active consumer is the operator's *separate* standalone "Heimdall", a local task and continuity daemon, which is
not Saga's container-launch gatekeeper. Its own docs state that "Saga is deferred" by the operator's direction.

### Cited Findings
- README one-liner: "Explainable retrieval that fits a budget. Braid combines lexical search, embeddings, graph relationships and recency, then selects diverse context within a consumer-defined cost limit." — [README.md](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- README status line: "early implementation with a Go library, CLI, versioned subprocess protocol and evaluation harness. Heimdall is the active integration; Saga is deferred. Synthetic and contract tests pass. … held-out consumer effectiveness and end-to-end deployment performance remain unverified." — [README.md line 5](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- GitHub description: "Retrieval engine utilizing: lexical, dense, graph, and temporal methods." The repo is public and was created 2026-09-05T05:32Z. The last push was 2026-09-11T06:51Z. GitHub reports the language as Go, the size as 122 KB, no topics and no homepage. — [GitHub API repos/algorhythmic/braid](https://api.github.com/repos/algorhythmic/braid)
- Language and dependencies: module `github.com/algorhythmic/braid`, `go 1.24.0`. The only direct dependencies are `modernc.org/sqlite v1.38.2` (pure-Go SQLite, no cgo) and `gopkg.in/yaml.v3 v3.0.1`. — [go.mod](https://github.com/algorhythmic/braid/blob/41bc392/go.mod); [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)
- Size, counted locally in the clone: 7,286 lines across all tracked files. Of these, about 4,213 are non-test Go (`pkg/braid/*.go`, `cmd/braid/*.go`) and about 1,922 are test Go. There are 15 `_test.go` files with 51 `func Test…` and 1 `BenchmarkRetrieval`, and 12 docs files totalling about 61 KB. The largest source files are `pkg/braid/query.go` (374 lines), `cmd/braid/protocol.go` (407) and `pkg/braid/selection.go` (353). — local `wc -l` over the clone (see the [tree at 41bc392](https://github.com/algorhythmic/braid/tree/41bc392))
- Commit history: 5 commits on `main`. The rest of this bullet comes from the [GitHub commits API](https://github.com/algorhythmic/braid/commits/main).
  - `b530618` 2026-09-05 "Initial Braid retrieval engine". +5,267/−0 lines in 50 files. Author and committer name "Algorhythmic".
  - `7602263` 2026-09-08 "feat: enforce constrained and revision-consistent retrieval". +1,693/−224 in 18 files.
  - `9941b21` 2026-09-08 "docs: publish retrieval contracts and catalog benchmarks". +464/−15.
  - `65c7f6e` 2026-09-08 "build: replace PowerShell helpers with Bash for Linux". +159/−92.
  - `41bc392` 2026-09-09 "docs: explain exact and lexical retrieval in README". +44/−10.
  - The four later commits are authored by "David Alexander Dunn".
  - There are no other branches, no pull requests and no issues.
- First and last dates, and cadence: first commit 2026-09-05, last commit 2026-09-09. The annotated tag `v0.1.0` points at `41bc392` and is dated 2026-09-11, with the message "Pin subprocess protocol v1 + dataset APIs for Heimdall S3". There is no GitHub Release object. Cadence: one large initial drop, three commits on 2026-09-08 and one on 2026-09-09, then nothing for about five weeks up to 2026-10-14. — [GitHub tags API](https://api.github.com/repos/algorhythmic/braid/tags); [git tag object 4f8b9ce](https://api.github.com/repos/algorhythmic/braid/git/tags/4f8b9cec8ccade5f4e33175de64afa847e1130a8)
- CI: `.github/workflows/test.yml` runs on `ubuntu-latest`. It checks Bash syntax, then runs `./scripts/dev.sh test -race ./...`, `vet`, `build` and `./scripts/verify-contract.sh`. GitHub Actions shows 5 runs between 2026-09-05 and 2026-09-11, and all completed with `success`. — [.github/workflows/test.yml](https://github.com/algorhythmic/braid/blob/41bc392/.github/workflows/test.yml); [Actions runs API](https://api.github.com/repos/algorhythmic/braid/actions/runs)
- License: none. There is no LICENSE file in the tree and the GitHub API returns `"license": null`. — [GitHub API](https://api.github.com/repos/algorhythmic/braid)
- Deployment artifacts: none. There is no Dockerfile, compose file, systemd unit, packaging or release binary. The only helpers are `scripts/dev.sh` (a Go wrapper) and `scripts/verify-contract.sh` (a contract checker that needs Go, `jq` and GNU `timeout`). The README says "Development and deployment target Linux/Omarchy". — [README.md line 38](https://github.com/algorhythmic/braid/blob/41bc392/README.md); [scripts/](https://github.com/algorhythmic/braid/tree/41bc392/scripts)
- On provenance: "The supplied `fuse-retrieval-engine.md` is design input, not authority to access consumer repositories or run their jobs. … No upstream project or trademark availability check has been performed." The design draft itself is not in the repo. `.gitignore` excludes `docs/heimdall/` with the comment "Imported local consumer handoff packet". — [docs/implementation.md line 3](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md); [.gitignore](https://github.com/algorhythmic/braid/blob/41bc392/.gitignore)
- References to Saga:
  - `examples/saga.yaml` and `examples/events.jsonl` form a fixture with four events (`task.created`, `file.observed`, two `worker.reported` with `summary`, `failure`, `status`, `tokens`, `files`) and one label. The README calls it "synthetic … It is not a Saga integration or a quality benchmark". — [README.md line 36](https://github.com/algorhythmic/braid/blob/41bc392/README.md); [examples/saga.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/saga.yaml); [examples/events.jsonl](https://github.com/algorhythmic/braid/blob/41bc392/examples/events.jsonl)
  - The roadmap says: "Updated from the user's direction: **Heimdall is the active integration; Saga is deferred.** The existing Saga example remains a synthetic engine smoke test." — [docs/roadmap.md line 3](https://github.com/algorhythmic/braid/blob/41bc392/docs/roadmap.md)
  - The implementation notes say: "Saga is deferred by user direction" and "Saga's exporter and completed-task ablations wait until its integration resumes." — [docs/implementation.md lines 30, 32](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)
- References to the Norse-named components: a grep of all Go, shell and YAML files finds no mention of Odin, Mimir, dvergr or dvergar, Bragi, Ratatoskr, Eir, MQTT, Telegram, Docker or Anthropic. "Heimdall" appears in many places: `docs/heimdall-integration.md`, `examples/heimdall.yaml`, the `heimdall:contract` dataset in `scripts/verify-contract.sh`, and `heimdall:test` in `cmd/braid/protocol_test.go`. — local grep of the clone; [docs/heimdall-integration.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/heimdall-integration.md)
- **Which Heimdall braid means:**
  - The same owner has a separate repo, `algorhythmic/heimdall`. It is written in Go, was created 2026-09-05 (the same day as braid) and was last pushed 2026-09-11. Its description is "A local daemon that observes every surface you work in, keeps an event log, opens tasks in workspaces, and issues ranked work session plans on a schedule." — [GitHub API users/algorhythmic/repos](https://api.github.com/users/algorhythmic/repos)
  - Its README begins: "Heimdall is a local task and continuity system for work shared between people and assistants. … Retrieval belongs to the separate Braid project."
  - The same README also says:
    - "Project-aware Braid memory | Planned; Braid is not integrated."
    - "Braid will remain a separate retrieval component when its adapter is implemented."
    - Its delivery plan has the row "S3 (C14–C16) | Braid assignment and continuity retrieval, typed checkpoint MCP records, optional intent extraction".
  - The words "saga", "odin", "dvergr", "mqtt" and "docker" appear 0 times in that README. — [algorhythmic/heimdall README](https://github.com/algorhythmic/heimdall)
- Braid's Heimdall docs use continuity and task-assignment vocabulary, not container-launch vocabulary: "permitted, nonpurged entities", "account/project scope", "held-out task-assignment evaluation", "Split held-out labels by conversation/artifact lineage", "Revalidate proposal targets against current Heimdall state at acceptance", and "Do not reuse Heimdall's own database". — [docs/heimdall-integration.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/heimdall-integration.md)
- Saga's Heimdall, by contrast, is a "Python daemon on the host VM. Validates and executes container launch requests. The security boundary between Odin and Docker." — [/home/david/Projects/saga/CLAUDE.md line 18](/home/david/Projects/saga/CLAUDE.md)
- Other consumers braid names:
  - The `wayland-computer-use` keybinding catalogs. They are the source of the 2026-09-07 "computer-use backlog" (BRD-01..08) and of the 1,998-record benchmark. — [docs/retrieval-improvement-plan.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-improvement-plan.md); [docs/retrieval-benchmarks.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-benchmarks.md)
  - "Nexus scale work" (Postgres, ANN), which is listed as a future milestone. — [docs/implementation.md line 33](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)

### Inferences
- In braid, "Heimdall" is a name collision with Saga's Heimdall, not a reference to it. Braid's consumer is the standalone continuity daemon `algorhythmic/heimdall`. Nothing in braid touches container launches, launch-request YAML, or Saga's security boundary.
- The Saga fixture is shaped like Saga's fleet. Its task, file and `worker.reported` events carry `summary`, `failure`, `status`, `tokens` and `files`, and the docs plan a "Saga exporter" and "completed-task ablations". Together these suggest that the original design draft (`fuse-retrieval-engine.md`) aimed braid at recalling past worker reports and tasks for Saga's planner. The operator then moved priority to the standalone Heimdall. This is inference: the draft is not public.
- The history looks like an agent-implemented build from a design document: one 5,267-line initial commit, then documents organized as numbered backlog items (B-01..B-06, BRD-01..08), all within five days. This is inference from the commit shape and doc wording ("the draft", "as requested by the draft"). The repo does not say how it was written.
- Braid targets the operator's Linux/Omarchy workstation, alongside standalone Heimdall's "local daemon". It does not target the homelab Docker VM where Saga runs.

### Gaps
- The design input `fuse-retrieval-engine.md` and the `docs/heimdall/` handoff packet are not in the repo, so I could not see the original Saga use case or acceptance criteria.
- I could not determine whether braid is deployed or used anywhere. Standalone Heimdall's README says "Braid is not integrated", and braid says Heimdall "adapter deployment … remain[s] pending".
- I did not establish whether the initial-commit author "Algorhythmic" is the same person as the later author. It is presumably the operator's own account, but I did not check emails.

## 2. Architecture and interfaces: data model, storage, API and CLI, configuration, model calls, integrations

### Takeaway
Braid is a single-process, single-SQLite-file index per "dataset" (one scope per file) over consumer-defined nodes, edges and optional
vectors. It is driven through a Go library, a CLI, or a strict NDJSON-over-stdio protocol (v1, capability-negotiated). Its
only network or model call is an optional Ollama embedding endpoint. It has no MQTT, Telegram, Docker, git or LLM integration.

### Cited Findings
- **Data model.** These types are in [pkg/braid/types.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/types.go). "Node and edge types are consumer-defined labels", per the [README](https://github.com/algorhythmic/braid/blob/41bc392/README.md).
  - `Node{id, type, text, ts, cost?, attrs}`
  - `Edge{src, dst, type, weight, ts}`
  - `Embedding{node_id, model, vec []float32}`
  - `Event{id int64, ts, name, payload}`
  - `Query` has the fields `text`, `anchors`, `weights`, `filters`, `boosts`, `budget`, `requires`, `mandatory_ids`, `require_evidence`, `min_score`, `expected_revision`, `dataset_id`, `at` (which pins the recency clock), `explain` and `trace`.
  - `Result` has `items` (each item carries `score`, `cost` and `why`), `accounting`, `rejections`, `abstained` with `abstention_reason`, `dataset`, `config_hash` and `ranking_version`.
- **Storage.** One SQLite database per dataset. `PRAGMA journal_mode=WAL; busy_timeout=5000`.
  - Tables: `nodes`, an FTS5 virtual table `nodes_fts` (tokenizer `unicode61 remove_diacritics 2`) kept in sync by triggers, `edges`, `embeddings` (vectors stored as BLOBs), `events`, `labels`, `evaluation_labels` and `eval_runs`.
  - `db.SetMaxOpenConns(1)`. One Engine serializes operations.
  - Sources: [pkg/braid/store.go lines 15–83](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/store.go); [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)
- **Two write modes.**
  - (a) Legacy event-sourced mode. `Ingest` "atomically appends and projects events". IDs must be positive and increasing. Re-ingesting identical content is idempotent, and conflicting content is rejected. YAML `projection` rules map event payloads to nodes and edges, for example `on: worker.reported → report:{{.id}}` with an edge `for` to `task:{{.task}}`. `Replay` rebuilds nodes and edges from the `events` table. — [pkg/braid/projection.go lines 151–200](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/projection.go); [examples/saga.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/saga.yaml)
  - (b) Snapshot-managed mode. `replace_snapshot` and revision-checked `apply` support node and edge deletion. "After first snapshot/apply publication, ingest/replay are disabled for that database". New integrations are steered to this mode. — [docs/datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md)
- **Dataset identity.** Each database has an immutable `dataset_id`, a revision counter, and a deterministic SHA-256 digest over the published nodes, edges and vectors. Every query reports `{id, revision, digest}`. "This is a boundary on a trusted bound Engine, not authentication." — [docs/datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md)
- **Retrieval and selection.**
  - Four independent retrievers: lexical BM25, dense brute-force cosine, anchor-seeded PageRank (20 iterations, damping configurable) and exponential recency with a half-life.
  - They are combined by weighted reciprocal-rank fusion with boosts.
  - Selection is deterministic greedy MMR over "complete, affordable dependency bundles" (`requires` closures and `mandatory_ids`). The ranking version is `mmr-admitted-dependencies-v2`. It is "not a globally optimal knapsack solver".
  - Sources: [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md); [docs/retrieval-contract.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-contract.md); [pkg/braid/selection.go line 9](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/selection.go)
- **Budgets and byte bounds.**
  - Costs are arbitrary units, resolved in this order: a custom `CostFunc`, then the node's `cost`, then a configured attribute, then "text rune count divided by four … not a token-exact estimate".
  - `export_context` / `Engine.Export` bounds the serialized JSON `context` array to an exact `max_bytes`. "No tokenizer or token-exact rendering contract is supplied."
  - The diagnostic envelope sits outside that bound.
  - Source: [docs/retrieval-contract.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-contract.md)
- **Explanations.** "Every selected item includes text, score, cost and `why`. `explain: true` adds raw rank lists and fused order." — [README.md](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- **Exact reads.** `get_many` / `Engine.GetMany` returns exact stored records in request order, plus `missing_ids` and an optional `expected_revision` precondition. "Exact lookup performs no fuzzy search or embedding calls." — [README.md](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- **Filters.** `types`, `since`, `exclude_ids`, `allowed_ids`, and a typed predicate tree over `attrs` (`eq`/`in`/`contains`/`exists`/`and`/`or`, up to depth 32 and 256 clauses). All are applied in SQL before each retriever's candidate limit. — [docs/retrieval-contract.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-contract.md); [pkg/braid/filters.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/filters.go)
- **Public interfaces.**
  - Go library: `Open`, `Query`, `Retriever`, `GetMany`, `Export`, `Ingest`, `Upsert`, `Replay`, `Dataset`, `ReplaceSnapshot`, `Apply`, `ReindexWithOptions`, `Eval`, `GridSearch`.
  - CLI: `init`, `ingest`, `upsert`, `replay`, `query`, `explain`, `dataset`, `replace-snapshot`, `apply`, `reindex`, `eval`, `serve --stdio`.
  - Subprocess: protocol version 1.
  - Sources: [README.md "Interfaces"](https://github.com/algorhythmic/braid/blob/41bc392/README.md); [cmd/braid/main.go](https://github.com/algorhythmic/braid/blob/41bc392/cmd/braid/main.go)
- **Subprocess protocol v1.** This is the main integration surface.
  - One UTF-8 JSON object per line on stdin. Stdout carries protocol responses only and stderr carries diagnostics.
  - The first request must be `hello` with `versions` and `required_capabilities`.
  - There are 28 capabilities and 12 error codes (`dataset_mismatch`, `revision_conflict`, …).
  - Strict schema: unknown fields and duplicate keys are rejected. Requests are limited to 16 MiB (`maxRequestBytes = 16 << 20`).
  - Optional `timeout_ms` per query. Dispatch is sequential, with background `reindex_start`/`status`/`cancel` jobs.
  - Sources: [docs/protocol.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/protocol.md); [cmd/braid/protocol.go line 19](https://github.com/algorhythmic/braid/blob/41bc392/cmd/braid/protocol.go)
- **Configuration.** YAML (`version`, `dataset_id`, `store`, `embed`, `index`, `projection`, `graph`, `temporal`, `defaults` with weights, k, boosts, `mmr_lambda` and budget). "Paths in YAML resolve relative to the process working directory." — [examples/saga.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/saga.yaml); [examples/heimdall.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/heimdall.yaml); [pkg/braid/config.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/config.go)
- **Model calls.** There are no LLM calls of any kind.
  - Embeddings are off by default (`provider: none`). The only built-in provider is Ollama, which sends `POST {url}/api/embed` with a 60-second default HTTP timeout and no authentication.
  - A library caller can inject any `Provider`.
  - "Ollama is supported; the draft's Anthropic provider is not implemented."
  - "Ingestion does not call the provider or download models."
  - Sources: [pkg/braid/embed.go lines 16–41](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/embed.go); [pkg/braid/config.go lines 63, 104–105](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/config.go); [docs/implementation.md line 20](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md); [README.md "Embeddings"](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- **MQTT, Telegram, Docker and git.** None of these appear. The only network import in non-test code is `net/http`, in `embed.go`. — local grep of the clone; [pkg/braid/embed.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/embed.go)
- **Evaluation harness.**
  - Labels are JSONL (`query_id`, `query`, `expected`, or `no_answer: true`, plus `stale_ids`, `cross_workstream_ids`, `forbidden_ids`).
  - Metrics: recall@5 and @20, MRR, nDCG@10, coverage, abstention, precision@5, no-answer false-positive rate, and stale and cross-workstream hit rates.
  - Grid search over 648 combinations. It writes a proposal YAML that is "never applied automatically", with optional constraint gates.
  - Sources: [docs/negative-evaluation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/negative-evaluation.md); [docs/grid-search.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/grid-search.md); [examples/grid.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/grid.yaml)
- **Measured performance.** The test is warm Go-library lexical retrieval on an i5-8600K. At 1,998 records it ran at p50 1.266 ms and p95 1.634 ms; at 19,980 records, p50 6.225 ms and p95 6.719 ms (λ=1). The doc says this is "not end-to-end computer use or retrieval quality" and that the vectors "provide no evidence about semantic retrieval quality". — [docs/retrieval-benchmarks.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-benchmarks.md)
- **Reproducibility.** Stable ID tie-breaking and a pinned query `at` make replay results byte-identical in the fixture. "No historical replay cutoff exists yet." — [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)

### Inferences
- Braid is designed as a **derived, rebuildable index beside a consumer that owns the truth**. In snapshot mode the consumer publishes and deletes. Braid never claims authority over the source log.
- The stdio protocol is language-neutral and expects a supervisor ("Launch the pinned Braid executable with `serve --stdio` … Supervise the child and capture stderr separately"). So a Python service, such as the Runtime A Odin service in the contract, could run it as a child process without writing Go.
- Because there are no Anthropic calls, adopting braid has no effect on Saga's billing constraints. Optional embeddings would run on local Ollama, on the same 32 GB box or on the workstation.

### Gaps
- I did not run the tests or the contract checker, by instruction. The claims that they pass rest on the green Actions runs and on the docs.
- Behaviour at scale is undetermined: physical storage size, memory at 20k+ vectors, and publication latency for large snapshots. The docs say "need measurement".

## 3. Relationship to Saga: what braid replaces or extends, and how its interfaces differ

### Takeaway
Braid does not replace any component that Saga ships today, because Saga has no retrieval engine. Its memory is the Markdown master journal plus a
Markdown lessons store read by directory listing and file reads. The nearest Saga features braid could serve are the
unbuilt "master journal search" (spec Phase 8) and on-demand recall of lessons, wikis, contracts and past worker reports.
Braid's own docs have parked that integration. Its "Heimdall" is not Saga's Heimdall.

### Cited Findings
- Saga's memory today:
  - Odin's `master-journal.md` ("This file IS your memory"). — [/home/david/Projects/saga/odin/CLAUDE.md line 131](/home/david/Projects/saga/odin/CLAUDE.md)
  - A lessons store of "one lesson file per completed project per topic". "Odin reads the index on startup; Mimir consults topic directories during PRD review." Odin is told to "drill in when relevant". — [/home/david/Projects/saga/bragi/lessons-template/README.md lines 1–10](/home/david/Projects/saga/bragi/lessons-template/README.md); [/home/david/Projects/saga/odin/CLAUDE.md lines 119–123](/home/david/Projects/saga/odin/CLAUDE.md)
- The Saga spec lists "Master journal search and summarization improvements" under Phase 8, "Scale and Polish". — [/home/david/Projects/saga/docs/saga-spec.md line 2335](/home/david/Projects/saga/docs/saga-spec.md)
- Saga's transports are MQTT for events and file mounts for data at rest. Neither includes a query service. — [/home/david/Projects/saga/docs/architecture/ARCHITECTURE.md lines 130–131](/home/david/Projects/saga/docs/architecture/ARCHITECTURE.md)
- A grep of the Saga repo for "braid" finds nothing in any `.md` file. — local grep of `/home/david/Projects/saga`
- Braid's Saga fixture projects `task.created`, `file.observed` and `worker.reported` into `task`, `file` and `report` nodes. It adds edges `for` (report→task) and `touched` (report→file, fanned out over `files`), takes cost from `tokens`, and boosts failed reports ×1.3. The example query is "ConnectionResetError in consumer loop" anchored on `task:T-112` and `file:src/queue.py`, filtered to `report`. — [examples/saga.yaml](https://github.com/algorhythmic/braid/blob/41bc392/examples/saga.yaml); [examples/query.json](https://github.com/algorhythmic/braid/blob/41bc392/examples/query.json)
- Saga's dvergr outputs, which such a projection would consume, are per-iteration `.dvergr/status.json` and `.dvergr/journal.md`, published on `dvergr/+/+/journal` and `dvergr/+/+/status`. — [/home/david/Projects/saga/docs/drafts/HARNESS-LANDSCAPE-2026-10.md §5.3 lines 404–409](/home/david/Projects/saga/docs/drafts/HARNESS-LANDSCAPE-2026-10.md); [/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md §2](/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md)
- How the interfaces differ:
  - Saga components talk through MQTT topics, YAML request files, Markdown verdicts and journals, and `tmux send-keys`. — [/home/david/Projects/saga/docs/architecture/ARCHITECTURE.md](/home/david/Projects/saga/docs/architecture/ARCHITECTURE.md)
  - Braid speaks a strict, negotiated NDJSON stdio protocol to a single supervising parent, or offers an in-process Go API, and keeps its state in its own SQLite file. — [docs/protocol.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/protocol.md)
- Saga's Heimdall is a launch gatekeeper on the VM (see §1). Braid's Heimdall is the standalone continuity daemon. — [/home/david/Projects/saga/CLAUDE.md line 18](/home/david/Projects/saga/CLAUDE.md); [algorhythmic/heimdall README](https://github.com/algorhythmic/heimdall)

### Inferences
- If braid is one of the "Saga features re-implemented as standalone tools", the feature it generalizes is **planner recall over past work**: master-journal search, lessons lookup, and "which earlier worker report already hit this error". It does not replace Odin, Mimir, Heimdall, Bragi, Ratatoskr or Eir.
- Braid also extends what Saga planned. It adds hybrid ranking, graph anchoring (task→report→file), dependency-complete packing, explanations, revision-pinned reads and a no-answer evaluation harness. Saga's docs describe none of these.
- To use braid, Saga would need an **exporter**. This could be (a) an MQTT or log subscriber that turns journal entries, status transitions, verdicts and lessons into nodes and edges and publishes them with `apply`, or (b) braid's legacy `ingest` with projection rules. Braid's docs name this exact piece as deferred ("Saga's exporter … wait[s] until its integration resumes").
- Braid targets a desktop (Omarchy), while Saga runs on the homelab VM. Running braid inside Odin's container would need a Go binary in the `saga-odin` image, or a static build. The repo ships no image or binary.
- The **name collision matters for the drafts.** The operator said that "several Saga features … have been re-implemented as standalone tools". The standalone `heimdall` repo is a continuity and task-planning daemon, not a re-implementation of Saga's launch gatekeeper, at least by its README. The standalone `skald` repo is a conversation archive whose README says it "complements Heimdall". Its name echoes Bragi's role ("skald"), but I did not review it. — [algorhythmic/skald README](https://github.com/algorhythmic/skald)

### Gaps
- The operator's intended mapping from braid to Saga is not written down anywhere public. The missing `fuse-retrieval-engine.md` is the most likely place it lives.
- Whether standalone Heimdall or Skald supersede Saga components is outside this note. They need their own repo reviews.

## 4. Relationship to the UniiChat memory design in ODIN-IO-CONTRACT.md

### Takeaway
The two designs are **orthogonal and complementary, not substitutes.**
- UniiChat keeps a *query-independent*, constant-size, multi-resolution view of the whole chat, built by an LLM summary tree and navigated with `zoom`.
- Braid retrieves a *query-dependent*, byte- or cost-bounded subset of a typed corpus, with deterministic, explainable ranking and no summarization.

The contract should **not** be built on braid, because braid has no log authority, summary tree, view or zoom. The contract **could add braid as an optional recall tool** for material that is deliberately outside the view: lessons, project wikis and contracts, the imported past, and dvergr journals across projects. It should also **absorb several of braid's ideas** (see Inferences).

### Cited Findings

Feature-by-feature comparison. The contract's side is cited to `/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md` and braid's side to the files named.

| Feature | ODIN-IO-CONTRACT (UniiChat) | Braid | Source (braid side) |
|---|---|---|---|
| Append-only log | Permanent JSONL per day, `{i, kind, src, text, size, date, ref?}`, ids dense from 0, "only append, flush every write, never edit or delete, one process owns the log" (§1) | Legacy mode: SQLite `events(id, ts, name, payload)`; ingest appends with positive, increasing ids, idempotent re-ingest, conflicts rejected; replay re-projects. Snapshot mode (recommended for new integrations) has **no log**: consumer-owned truth, revisioned replace/apply **with deletion** | [projection.go 151–200](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/projection.go); [datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md) |
| Typed message kinds | 9 kinds (`operator`, `verdict`, `odin`, `fleet`, `host`, `work`, `tool`, `echo`, `note`) with a compaction value rank (§1, §7) | Free consumer-defined `type` labels on nodes and edges; `filters.types`; `boosts` by type plus `attrs.FIELD == VALUE` with a multiplicative factor | [types.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/types.go); [implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md) |
| Summary tree | Binary tree of ≤512-byte summaries made by a Haiku compactor; value-ordered; "never make anything look further along than it was" (§7) | **None.** No summarization and no LLM calls; nodes keep their text verbatim | [embed.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/embed.go); [implementation.md line 20](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md) |
| View sizing | Constant 64–128 KB of summary lines covering the *whole* chat, merged by due-order, sized in UTF-8 bytes (§0, §4) | Per-query budget in arbitrary cost units, plus `export_context.max_bytes`, an exact UTF-8 JSON byte bound on the selected context; covers only *relevant* items | [retrieval-contract.md "Costs and bounded export"](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-contract.md) |
| Zoom | `zoom(id, n)` splits a tree line into its halves; `n=1` returns the original message; `zoom("Name")` opens a subagent log (§5) | No hierarchy. The closest analogue is `get_many(ids)`, which returns exact originals by id with `missing_ids` and a revision precondition (the equivalent of zoom at `n=1` only) | [README "Simple retrieval"](https://github.com/algorhythmic/braid/blob/41bc392/README.md) |
| Navigation rule | "Zoom is the only way to navigate memory; never grep the log" (§4, lines 204–205) | Search-first: text and/or anchor queries over BM25, dense, graph and recency | [README](https://github.com/algorhythmic/braid/blob/41bc392/README.md) |
| Cache discipline | Stable `[tools][system]` prefix, view saved and never rebuilt, explicit cache marks, about 98% cache reads (§4, §9, §10) | No prompt-cache concept. Determinism and stable tie-breaks give byte-identical results for the same query, `at` and snapshot, but retrieved context changes with every query | [implementation.md "Reproducibility"](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md) |
| Subagent logs | `chat/work/<name>/` with the same layout; reports return as one `work` message (§1, §5) | None. The nearest structure is one dataset per SQLite file, with no cross-dataset references | [datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md) |
| Correlation | `ref` joins request to result (§1) | Typed, weighted edges; anchor-seeded PageRank; `requires` dependency closures | [retrieval-contract.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/retrieval-contract.md) |
| Provenance and explanation | `src` on every line; Evidence cites `i=…` ids (§1, §4) | `why` on every selected item; raw ranks with `explain`; dataset `{id, revision, digest}`, `config_hash` and `ranking_version` on every result | [README](https://github.com/algorhythmic/braid/blob/41bc392/README.md); [datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md) |
| Evaluation | "Validate compaction quality on real fleet JSON … tune the value order" (§11 step 2); no metric defined | Labelled retrieval eval: recall, MRR, nDCG, no-answer false positives, stale and cross-workstream hits, grid search with gates | [negative-evaluation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/negative-evaluation.md) |
| Runtime and language | Python service on the Messages API (§9) | Go binary; stdio NDJSON child process or Go library | [protocol.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/protocol.md) |
| Model and auth | Opus or Sonnet turns plus a Haiku compactor on an API key from the Max-linked Console org (§9, §10) | None, apart from optional local Ollama embeddings | [embed.go](https://github.com/algorhythmic/braid/blob/41bc392/pkg/braid/embed.go) |

- The contract states that "principles, project wikis, fleet state and lessons live outside the view and reach it through the stable prompt or through tools". Its tools for those are only `read_file`, `write_file` and `list_dir`. Its memory-layer table gives the Lessons row as "read by Odin via `read_file`" and the Imported-past row as "via `zoom`". — [/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md lines 35, 230, 255–256](/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md)

### Inferences
- **Should not build on braid.** Braid's recommended snapshot mode deletes and replaces content, which contradicts "never edit or delete". Its legacy event log lives in SQLite rather than daily JSONL, and its ids must be positive (UniiChat's start at 0). It provides no tree, view, compactor or zoom. The log, tree and view must remain the contract's own Python-owned structure.
- **Could use braid as a recall tool for content outside the view.** Odin would call a hypothetical `recall(query, anchors?, kinds?, max_bytes)`, backed by braid's `export_context` with `require_evidence: true`, and the result would be logged as an `echo`. Candidate corpora:
  - cross-project lessons (Mimir also "consults topic directories during PRD review");
  - project wikis and `wiki/contracts/`;
  - the imported master journal and retrospectives;
  - every project's dvergr journals, which the view summarizes only coarsely once old.
- **The mapping is clean.** A log line maps to a braid node:
  - `i` → `msg:<i>` id;
  - `kind` → `type`;
  - `text` → `text`;
  - `date` → `ts`;
  - `src`, `ref` and `size` → `attrs`;
  - `ref` joins and `[project/instance]` prefixes → edges to `task:`, `project:` or `stream:` nodes.
- **Using braid would change the contract's navigation rule.** "Never grep the log" would have to become "zoom for the chat; recall for out-of-view corpora", or recall would also enter the chat log as an index. That is an operator decision, and the draft currently forecloses it implicitly.
- **Braid sits outside the cached prefix.** Recall output is query-dependent, so it belongs in the per-turn tail (as tool results), never in the stable `[tools][system][view]` prefix. It does not undermine the cache discipline.
- **Ideas the contract could absorb even without braid:**
  1. Exact byte bounds on any tool output that enters context, matching the contract's "bytes, never tokens" stance.
  2. A `why` or provenance list on every retrieved item.
  3. A `{revision, digest}` identity for the tree and view, so a turn records exactly which memory state it saw. This would strengthen "logged as part of the triggering message".
  4. A versioned, capability-negotiated, strict-schema stdio protocol for the harness's internal sidecars (Mimir verdict ingestion, the ingress daemon).
  5. No-answer and "forbidden hit" labels as the evaluation shape for compaction quality in §11 step 2. For example, label which ids must survive into the top-level view, and check that the summaries never state progress beyond the source text. This adapts braid's evaluation design; braid does not evaluate summaries.

### Gaps
- No measurement exists of braid on Saga-shaped data (journals, verdicts, lessons). The Saga fixture is four synthetic events. — [README.md line 36](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- Whether hybrid recall beats zoom-only navigation for Odin is undetermined. Braid's own docs say "The first implementation does not establish that fusion beats dense-only or no context." — [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)

## 5. Consequences for HARNESS-LANDSCAPE-2026-10.md and ODIN-IO-CONTRACT.md

### Takeaway
Braid does not falsify either draft's core design. It does make several statements incomplete, and one point in each draft is now ambiguous:
- The drafts survey retrieval and memory patterns from third parties but omit the retrieval engine the operator already built.
- The contract's memory layers offer only `read_file` for out-of-view corpora.
- "Heimdall" now names two different systems in the operator's work.
- Braid's docs record that the operator deferred Saga integration in September 2026, which bears on the "Is Saga currently running?" risk.

### Cited Findings

**HARNESS-LANDSCAPE-2026-10.md** (`/home/david/Projects/saga/docs/drafts/HARNESS-LANDSCAPE-2026-10.md`). The "Correction" column is inference.

| Location | Draft statement | What braid shows | Correction |
|---|---|---|---|
| Header, lines 3–11 (Inputs) | Inputs are "a full read of this repo; four landscape surveys …; seven source-level deep dives" | The operator's own Go retrieval engine, built 2026-09-05..09, is absent from the inputs. — [braid commits](https://github.com/algorhythmic/braid/commits/main) | Add the operator's standalone tools (braid; and heimdall and skald, pending their own reviews) as inputs, and cite this note. |
| §2.2 "Memory" bullet, lines 199–202 | "Odin's master journal exceeds the injection cap, so file-based memory with on-demand loading remains correct." | On-demand loading has an existing local implementation: a hybrid BM25, dense, graph and recency retriever with byte-bounded export and `why`. — [README](https://github.com/algorhythmic/braid/blob/41bc392/README.md) | Add: "on-demand loading can be braid-backed (`export_context` with `max_bytes`) rather than file reads alone". |
| §4 pattern 8, lines 339–345 | "Bounded memory with forced consolidation … Karpathy's index/log/lint shape for Bragi" | Braid is a bounded *retrieval* path, a different answer to the same problem. It bounds what enters context per query instead of capping the store. | Mention braid as the complementary half: cap what is injected every session; retrieve the rest under a byte budget. |
| §4 pattern 13, lines 366–369 | "session rotation on a schedule with the retired session indexed into memory (Nerve)" | The operator already has an indexer suitable for "indexed into memory". — [docs/datasets.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/datasets.md) | Name braid as the candidate indexer, with the caveats in §6 of this note. |
| §5.3 (line 424) and §6 step 4 | "Heimdall: image allowlist per worker image …" | The operator's `algorhythmic/heimdall` is a different system (a local task and continuity daemon). In braid, "Heimdall" always means that system. — [heimdall README](https://github.com/algorhythmic/heimdall) | The statements stay correct for Saga's launcher, but disambiguate everywhere: "Saga's Heimdall (launch gatekeeper)" versus "standalone Heimdall (continuity daemon)". |
| §6 Step 3, line 490 | Runtime v2 components include "bounded memory" | Braid's stdio protocol is designed to run as a supervised, pinned child process. — [docs/heimdall-integration.md "Process ownership"](https://github.com/algorhythmic/braid/blob/41bc392/docs/heimdall-integration.md) | Optional: "bounded memory, with optional braid recall as a supervised child process". |
| §7 Risks, lines 529–532 | "Is Saga currently running? Last commit 2026-05-06 …" | Braid's docs record that, by the operator's direction in Sept 2026, "Heimdall is the active integration; Saga is deferred". The operator's new repos (braid, heimdall, skald, wayland-computer-use) were all created 2026-09-05..10. — [docs/roadmap.md line 3](https://github.com/algorhythmic/braid/blob/41bc392/docs/roadmap.md); [GitHub API repos](https://api.github.com/users/algorhythmic/repos) | Strengthen the risk: development attention moved to standalone local tools in Sept 2026, and braid explicitly deferred Saga. Confirm with the operator which Saga roles those tools now own before investing in the Odin harness. |
| §8 Sources | Lists only the `harness-research-2026-10/` notes and three Anthropic pages | — | Add `repo_braid.md`. |

**ODIN-IO-CONTRACT.md** (`/home/david/Projects/saga/docs/drafts/ODIN-IO-CONTRACT.md`). The "Correction" column is inference.

| Location | Draft statement | What braid shows | Correction |
|---|---|---|---|
| §0, line 35 | "principles, project wikis, fleet state and lessons live outside the view and reach it through the stable prompt or through tools" | The only tools listed for wikis and lessons are file reads. Braid is a ready retrieval option. | Add a `recall` tool, or state explicitly that file reads plus `list_dir` are a deliberate choice over retrieval. |
| §4, lines 204–205 | "Zoom is the only way to navigate memory; never grep the log." | Braid is search-first. If adopted, this rule needs scoping. | Scope it: "within the chat, navigate by zoom; for out-of-view corpora (lessons, wikis, contracts, imported past, cross-project journals) use `recall`". Or keep zoom-only and record braid as considered and rejected. |
| §5 tools table, line 230 | `read_file` / `list_dir` over `/workspace/lessons/**` and so on | — | If adopted, add `recall(query, anchors?, kinds?, max_bytes)` → braid `export_context` (`require_evidence: true`, `why` retained), with output logged as `echo`. |
| §6 memory layers, lines 255–256 | Lessons "read by Odin via `read_file`"; Imported past "via `zoom`" | Braid could index both, plus wikis and contracts and every project's dvergr journals. Mimir's PRD review also consults lessons. — [/home/david/Projects/saga/bragi/lessons-template/README.md line 6](/home/david/Projects/saga/bragi/lessons-template/README.md) | Add an optional "Recall index (braid)" layer: written by an exporter from the log and Bragi's lessons, read by Odin and Mimir via `recall`, entering context as per-turn tool results, never in the view. |
| §7 Compaction | Haiku compactor builds the tree | Braid does not summarize. — [implementation.md line 20](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md) | No change. Do not cite braid as a compactor. |
| §8 "Heimdall. Unchanged." | Refers to Saga's launcher | Name collision with the standalone Heimdall, which is braid's consumer | Add one line: "Heimdall here means Saga's launch gatekeeper, not the standalone `algorhythmic/heimdall` continuity daemon." |
| §8 "Bragi" | Bragi compiles the vault and lessons from `chat/main/*.jsonl` | An operator repo named `skald` (Bragi's role name) now exists as a conversation archive. — [skald README](https://github.com/algorhythmic/skald) | Out of scope here. Flag for a separate review before fixing Bragi's input contract. |
| §9 Runtime consequence | A Python service owns log, tree, view and tools | Braid runs as a Go child process speaking NDJSON. It adds no Anthropic auth or billing surface. | Note compatibility: braid can be supervised by the service; no Go is needed in the service itself. The `saga-odin` image would need the binary, and the repo ships none. |
| §10 Cost model | Opus, Sonnet and Haiku costs | Braid adds no API cost; optional embeddings run on local Ollama. | No change, or one line noting recall adds zero model spend. |
| §11 Migration, step 2 | "Validate compaction quality … tune the value order" | Braid shows a working eval shape (labels, no-answer, forbidden hits, constraint gates). — [negative-evaluation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/negative-evaluation.md) | Optionally define compaction acceptance as labelled must-survive ids and forbidden overstatements, adapted from braid's eval design. |
| §12 Open questions | Five questions | Missing: whether to use braid for out-of-view recall; whether the operator's Sept 2026 "Saga is deferred" direction still stands. | Add both. |

### Inferences
- Neither draft has to be withdrawn. Braid's existence most changes the *framing* of memory. The drafts present UniiChat plus file reads as the whole memory story, while the operator already owns a second, complementary piece: retrieval.
- The single most consequential finding for the drafts is the operator's recorded direction that Saga integration is deferred (braid `docs/roadmap.md`, `docs/implementation.md`). It bears directly on HARNESS §7's "Is Saga currently running?" and on whether the ODIN-IO-CONTRACT migration (§11) should proceed before the operator confirms what Saga is still for.

### Gaps
- I could not see the operator's statement listing which Saga features are now standalone tools, so the mapping above rests on the repos' own text.

## 6. Gaps, risks and maturity

### Takeaway
Braid is a well-documented, contract-tested **v0.1.0 prototype**. It has no consumer in production, no held-out quality evidence, no license and no deployment artifacts, and it has had no commits for five weeks. Treat it as a candidate component, not a dependency, until a Saga-shaped evaluation exists.

### Cited Findings
- Tests: 51 test functions and 1 benchmark. They cover scope checks, atomic rollback, revision conflicts, deletion cleanup, reader snapshots, diversity, protocol validation, background jobs and negative metrics. A generated acceptance fixture has 200 nodes, 600 edges and 40 labels. — [README "Development"](https://github.com/algorhythmic/braid/blob/41bc392/README.md); local count of `func Test` in the clone
- "No live Ollama instance is required for automated tests", and dense retrieval is tested only with injected vectors and an HTTP test server. — [README](https://github.com/algorhythmic/braid/blob/41bc392/README.md); [docs/verification.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/verification.md)
- Self-declared limits:
  - "Heimdall adapter deployment and held-out calibration remain pending; Saga integration is deferred."
  - "Dataset isolation is one database per scope, not authentication."
  - "Dense search is brute force. Reindex builds are in memory."
  - "Postgres, ANN, consumer outcome recording and learned reranking are not implemented."
  - Source: [README "Current limits", line 174 onward](https://github.com/algorhythmic/braid/blob/41bc392/README.md)
- Effectiveness is unproven: "The first implementation does not establish that fusion beats dense-only or no context." — [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md)
- Doc staleness: `docs/verification.md` line 14 says "The updated remote CI workflow has not yet run." Yet Actions shows a successful run on `65c7f6e` at 2026-09-08T07:00Z and later runs on `41bc392`. — [docs/verification.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/verification.md); [Actions runs API](https://api.github.com/repos/algorhythmic/braid/actions/runs)
- No LICENSE (API `license: null`). There are no releases beyond the `v0.1.0` tag, no issues and no PRs. — [GitHub API](https://api.github.com/repos/algorhythmic/braid)
- Concurrency: one Engine serializes all operations, SQLite has a 5-second busy timeout, and the subprocess handles one request at a time. "Reindex is not a durable build queue: a process crash discards the unpublished build." — [docs/implementation.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/implementation.md); [docs/reindex.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/reindex.md)
- Platform: Go 1.24+. The target is Linux/Omarchy, and the earlier Windows verification history is retained. — [docs/verification.md](https://github.com/algorhythmic/braid/blob/41bc392/docs/verification.md)

### Inferences
- **Risks if Saga adopts braid:**
  - It would add a second language and runtime (Go) to a Python and Bash codebase.
  - The repo has no license yet, which matters if Saga goes public, as CLAUDE.md anticipates.
  - Single-maintainer cadence: one five-day burst.
  - The snapshot model (replace or apply with deletion) would make braid a derived cache that must be rebuildable from the chat log, never a store of record.
- **Low-risk aspects:**
  - No network calls by default.
  - Strict input validation.
  - Per-scope database files map naturally onto Saga's per-project boundaries: one dataset per project, plus one for lessons.

### Gaps
- Undetermined: how braid performs on Saga data; whether the operator intends braid for Saga at all after the deferral; the content of `fuse-retrieval-engine.md`; whether standalone `heimdall` and `skald` supersede Saga's Heimdall naming or Bragi's role (they need their own reviews); and whether any braid binary is deployed on the operator's machines (none of this was checked on the host).
