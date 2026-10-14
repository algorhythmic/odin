# algorhythmic/muninn as of 2026-10-14: what it is now, how it relates to Saga, and what it means for the Odin drafts

Method: shallow clone of `https://github.com/algorhythmic/muninn` (then `git fetch --unshallow` for history), read without executing anything. HEAD is `45296bf` (2026-07-16 23:12 PDT). Muninn links below are pinned to that commit (`M/` = `https://github.com/algorhythmic/muninn/blob/45296bf/`). Saga links are relative to this file. GitHub metadata came from the REST API on 2026-10-14. Tests were not run, so test counts come from commit messages and static counts.

## 1. Identity: what muninn is today

### Takeaway
Muninn is no longer just "the bookmark wiki." Its own docs now define it as the operator's **unified personal wiki** (Karpathy llm-wiki pattern): one Obsidian vault with `bookmarks/ projects/ sessions/ infra/ concepts/ people/` namespaces, one Qdrant index and one MCP endpoint. Only the bookmark lane has code, and v1 has not shipped. The public repo is a ~5.8k-line Python package. Activity came in two bursts (2026-04-15/16 and 2026-07-16) and there have been no commits since 2026-07-17 UTC. The README is stale and contradicts the current CLAUDE.md and ADRs.

### Cited Findings
- Public repo, created 2026-04-16T17:17:21Z, last push 2026-07-17T06:12:11Z, `license: null`, 0 stars and 0 forks, 313 KB, not archived. Description: "Muninn turns the bookmark corpus into a dual-interface knowledge base: a human-browsable wiki plus a vector-indexed MCP endpoint that any LLM-aware tool can query." — [GitHub API repos/algorhythmic/muninn](https://api.github.com/repos/algorhythmic/muninn)
- There is no LICENSE file in the tree and no license field in `pyproject.toml`. — [M/pyproject.toml](https://github.com/algorhythmic/muninn/blob/45296bf/pyproject.toml)
- Languages by bytes: Python 375,936; Shell 5,729; Dockerfile 1,937; Jinja 1,156. — [GitHub API languages](https://api.github.com/repos/algorhythmic/muninn/languages)
- Package `muninn` 0.1.0, `requires-python >=3.12`, console script `muninn = muninn.consumers.cli.main:cli`. Dependencies include anthropic, qdrant-client, duckdb, mcp, jinja2 and pyarrow, with an optional `[embeddings]` extra (sentence-transformers). — [M/pyproject.toml](https://github.com/algorhythmic/muninn/blob/45296bf/pyproject.toml)
- Static size of the clone: 5,815 lines of Python under `src/`, 4,019 lines under `tests/`, 245 `def test_` functions. Commit `ab874cb` claims "Tests: 406 pass" (parametrized cases; the URL sanitizer alone claims 285 cases). — [commit ab874cb](https://github.com/algorhythmic/muninn/commit/ab874cb)
- History: 21 commits on one branch (`main`), all by the operator. The cadence is 5 docs commits on 2026-04-15, 1 code commit on 2026-04-16 (`ab874cb`, 92 files, +10,468 lines), and 15 commits on 2026-07-16 (local time). There are no `Co-Authored-By` trailers. The April commits come from `daviddunn@MacBook-Air-4.local`; the July commits use the operator's Gmail address. — [commits on main](https://github.com/algorhythmic/muninn/commits/main)
- The April 2026 dvergr stream branches are **not visible**. The remote has only `refs/heads/main` (GitHub branches API returns `main` only). The Saga journal cites stream-1 commit `d6887a8` ("feat: implement muninn stream 1 — ingest + sanitization pipeline"), but that object does not exist in muninn's history (`git cat-file` fails). — [../../../journal/JOURNAL-FORMAT.md L172](../../../journal/JOURNAL-FORMAT.md); [commit ab874cb](https://github.com/algorhythmic/muninn/commit/ab874cb)
- The current self-definition reads: "A **unified personal wiki** (Karpathy llm-wiki pattern, ADR-001/006): one Obsidian-browsable vault with namespaces … one Qdrant index (homelab LXC `.19`), one MCP endpoint. v1 populates only `wiki/bookmarks/` … Memex is retired as a name; its scope is `wiki/infra/`." — [M/CLAUDE.md L18-20](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L18-L20)
- "Norse naming is not required going forward. Muninn is a standalone dataset that Saga happens to be one builder of — don't frame it as 'the thing Saga builds.'" — [M/CLAUDE.md L61-63](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L61-L63)
- ADR-001 (2026-04-19) chose one unified Muninn over separate Muninn, Memex and Bragi-journal stores. ADR-004 made the vault the source of truth for project state, with Bragi as its author. ADR-008 (2026-07-16) sets up two lanes and two canonical stores and is still "**Proposed** … pending operator ratification". — [M/docs/muninn-decisions.md L11-31, L85-107, L195-213](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md)
- The README is stale. It still says "Architecture (planned)" and "Spec drafted, implementation pending", and its relationship table says "Saga … Builds Muninn — Saga's dvergar handle the parallel scrape/summarize work; Saga's Bragi handles the vault compilation". — [M/README.md L36, L130-145, L153](https://github.com/algorhythmic/muninn/blob/45296bf/README.md#L130-L153); contradicted by ADR-002 ("No Claude Code instances, no dvergar") — [M/docs/muninn-decisions.md L43](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L43)
- v1 status per the roadmap:
  - Done: vault skeleton (pushed to Gitea `david/muninn-vault`, tag `v1-skeleton`), Qdrant LXC 119 at `.19` (2026-07-17), and a retrieval smoke test (100 newest bookmarks scraped, 58 enriched and indexed, EmbeddingGemma confirmed).
  - Not done: "Implement bulk bookmark enrichment worker" ("Remaining: … run the ingest on the real export") and "Index `wiki/bookmarks/` into Qdrant". `wiki/projects/` is only partly populated. — [M/docs/muninn-roadmap.md L17, L42-53](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L13-L53)
- The planned bulk run is "~39k-call". — [M/CLAUDE.md L38](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L38)
- Deployment:
  - The vault is a separate repo: `~/Documents/Code/muninn-vault` locally, Gitea `.18` `david/muninn-vault`, deployed at `/opt/muninn/vault`. — [M/CLAUDE.md L53-55](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L53-L55)
  - Qdrant defaults to `http://192.168.86.19:6333`. — [M/src/muninn/config.py L90-91](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L90-L91)
  - The MCP server and its Tailscale exposure are unchecked Phase 2 items. — [M/docs/muninn-roadmap.md L55-66](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L55-L66)
  - There is no CI directory in the tree.

### Inferences
- The project's centre of gravity moved in two steps. On 2026-04-19 the ADRs widened it from "bookmark KB" to "operator-wide memory substrate". On 2026-07-16 the Skald Protocol and `/note` skill gave the session and project lanes a concrete contract. The code has not followed: everything under `src/` is still the April bookmark pipeline plus fixes.
- The repo looks dormant rather than abandoned. The last commit says the retrieval smoke test passed, and the next step (the real-export bulk run) has no commit. Because muninn's last push predates the creation of `skald` (2026-09-10) and `braid` (2026-09-05), the operator's "re-implemented as standalone tools" remark plausibly covers parts of muninn's July plan (session capture, retrieval). See section 3.

### Gaps
- Whether the bulk enrichment of the real export ran after July. It would leave no commit, since data is git-ignored. Could not determine.
- Whether the operator or dev Claude did the April integration. There are no trailers, and the authoring machine was the operator's MacBook.

## 2. Architecture and interfaces

### Takeaway
The bookmark lane is real code:
- Netscape `bookmarks.html` → sanitized SQLite (7 tables + FTS5) → dual-pass HTTP scrape (live + Wayback at-capture) → Haiku 4.5 enrichment over the **API key**.
- Local EmbeddingGemma vectors in Qdrant at `.19`.
- Outputs: CLI, a **stdio** FastMCP server with five bookmark-only tools, a Jinja vault compiler writing `wiki/bookmarks/`, a DuckDB timeline and a Parquet export.

The skald lane (sessions, projects, log) is a protocol plus a linter with no runtime code. Synthesis (Opus in a Saga-style container) is scaffolding that does not yet deliver its task. Nothing is scheduled.

### Cited Findings
- **Two lanes.**
  - Bookmark lane: SQLite is canonical, and the vault compiler is the only writer of `wiki/bookmarks/`.
  - Skald lane: vault-first. Emitters (`/note` now, Bragi later) write `wiki/sessions/`, managed regions of `wiki/projects/`, and `wiki/log.md` directly, one git commit per capture, never mirrored into SQLite.
  - Qdrant is derived data in both lanes. — [M/CLAUDE.md L22-26](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L22-L26); [M/docs/muninn-decisions.md L195-213](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L195-L213)
- **Data model.** `schema.sql` (byte-identical to `schemas/sql/001_initial.sql`) defines:
  - `bookmarks`: INTEGER PK, `UNIQUE (source, source_id)`.
  - `scrape_results`: `UNIQUE (bookmark_id, pass)`.
  - `enriched`: 1:1 with `bookmarks`.
  - `eras`: TEXT PK.
  - `cross_references`, `analyses`.
  - `synthesis_runs`: `UNIQUE (task_id, attempt)`.
  - The FTS5 virtual table `fts_bookmarks`. — [M/schema.sql L12-167](https://github.com/algorhythmic/muninn/blob/45296bf/schema.sql)
- `fts_bookmarks` was changed from contentless to content-storing on 2026-07-16 because "the contentless form rejected the DELETE used on re-enrichment (every re-enrichment write failed silently)". — [commit 82a8954](https://github.com/algorhythmic/muninn/commit/82a8954). The MCP `fts_search` docstring still says "contentless". — [M/src/muninn/consumers/mcp/tools.py L112](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/mcp/tools.py#L112)
- **Synthesis I/O contracts.** JSON Schemas `task-input`, `era-narrative`, `deep-pass` and `ad-hoc-analysis`. — [M/schemas/json/](https://github.com/algorhythmic/muninn/tree/45296bf/schemas/json)
- **Ingestion and scraping.**
  - Netscape HTML parser and upsert. Sanitizer: token-shape regex, a parameter denylist (e.g. `gclid`, `gbraid`, `wbraid`) and scheme rules. The original URL is never stored after ingest. — [M/CLAUDE.md L32, L51](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L32); [M/src/muninn/sanitize/rules.py L88](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/sanitize/rules.py#L88)
  - Scraping: live plus at-capture (±365 d), with recent_archive fallback, a 1 rps per-domain limit, a 0.5 rps limit to the Internet Archive, an on-disk cache and an auth-wall heuristic. Bookmarks are processed concurrently (`asyncio.Semaphore(concurrency=4)` + `gather`). — [M/src/muninn/config.py L98-101](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L98-L101); [M/src/muninn/scrape/pipeline.py L106-139](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/scrape/pipeline.py#L106-L139)
  - There is no robots.txt handling. — [M/CLAUDE.md L41](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L41)
- **Enrichment.**
  - Model `claude-haiku-4-5-20251001` via `anthropic.Anthropic()` with `ANTHROPIC_API_KEY`, which means API billing, not subscription. — [M/src/muninn/config.py L76, L95](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L76-L95); [M/.env.example L13-14](https://github.com/algorhythmic/muninn/blob/45296bf/.env.example#L13-L14); [M/SPEC.md L29-30](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L29-L30)
  - Prompt caching uses `cache_control: ephemeral`, but the hit rate was 0% on the 58-call smoke run. — [M/CLAUDE.md L38](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L38)
  - Idempotency triple: `enrichment_model` + `enrichment_prompt_version` + `content_hash`. — [M/CLAUDE.md L24](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L24)
- **Embeddings and retrieval.**
  - Embeddings run locally with sentence-transformers and `google/embeddinggemma-300m` (768-dim). A `hash` backend remains for tests and offline use. — [M/src/muninn/config.py L86-87](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L86-L87); [commit ae58031](https://github.com/algorhythmic/muninn/commit/ae58031)
  - Qdrant collection `muninn_bookmarks` at `.19`, "v1 no auth (homelab-internal)". — [M/SPEC.md external services registry](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L61-L72)
  - `semantic_search` falls back to FTS5 when Qdrant is unreachable. — [M/src/muninn/consumers/mcp/server.py L22-28](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/mcp/server.py#L22-L28)
- **Outputs.**
  - CLI: `muninn ingest|scrape|enrich|synthesize|triage|status|deep-pass|export|timeline|vault|mcp`. — [M/CLAUDE.md L34](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L34)
  - MCP: FastMCP over **stdio** with exactly five tools (`semantic_search`, `fts_search`, `get_bookmark`, `get_era`, `list_eras`), all over bookmarks and eras. — [M/src/muninn/consumers/mcp/server.py L19-59](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/mcp/server.py#L19-L59)
  - The namespace-aware tools `search(query, namespace, top_k)`, `get_page`, `list_namespace` and `ingest_raw` are unbuilt Phase 2 items. — [M/docs/muninn-roadmap.md L59-66](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L59-L66)
  - The vault compiler writes `{vault}/wiki/bookmarks/{slug}.md`. — [M/src/muninn/consumers/vault/compiler.py](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/vault/compiler.py); [commit 05235a6](https://github.com/algorhythmic/muninn/commit/05235a6)
- **Never-same-vault guard.**
  - `_validate_vault_paths()` raises `VaultPathConflictError` when `MUNINN_VAULT_DIR` equals `MUNINN_PERSONAL_VAULT_DIR` or either is nested inside the other. It runs before any write. — [M/src/muninn/consumers/vault/compiler.py](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/vault/compiler.py)
  - The guard is **opt-out**: when the personal-vault variable is unset, it returns without checking ("allow opt-out"). — same file, `_validate_vault_paths`
  - The SPEC's second mechanism, a `.muninn-compiled-vault` sentinel file, appears nowhere in code. It exists only in SPEC text, and the Obsidian ingest adapter it would protect is also unbuilt. — [M/SPEC.md L56, L282-291](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L56)
- **Other safety checks.**
  - `domain_policy.yml` fails closed: a missing or malformed file aborts instead of scraping everything.
  - MCP `get_bookmark()` returns not-found for `content_visible=0` rows. — [commit e168f42](https://github.com/algorhythmic/muninn/commit/e168f42)
- **Synthesis.**
  - Opus `claude-opus-4-6` in a container built `FROM ghcr.io/trailofbits/devcontainer:latest`. — [M/src/muninn/config.py L77](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L77); [M/containers/synthesis/Dockerfile L11-12](https://github.com/algorhythmic/muninn/blob/45296bf/containers/synthesis/Dockerfile#L11-L12)
  - It mounts `saga-claude-credentials` **read-only** at `/home/vscode/.claude`, runs `claude --dangerously-skip-permissions` under tmux, never uses `-p`, and refuses to start if `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` is set. It is launched by a direct `docker run`. — [M/scripts/launch-synthesis.sh L12-37, L66-75](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/launch-synthesis.sh#L12-L75); [M/src/muninn/synthesis/container.py](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/synthesis/container.py)
  - Known gap: the container "launches interactive `claude` but never feeds it the task JSON; `task-input.schema.json` rejects the orchestrator's own `attempt` field". — [M/CLAUDE.md L40](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L40)
- **Skald lane.** Skald Protocol Draft v1 (2026-07-16):
  - Session pages `wiki/sessions/YYYY-MM-DD-{primary-project}-{slug}.md` with additive-only frontmatter v1 (`schema_version`, `page_type`, `projects`, `emitter`, `outcome`, plus optional `session_id`, `agents`, `decisions`, `next_actions`, `sources`).
  - Project pages with `<!-- skald:begin/end -->` managed regions, and an append-only `wiki/log.md`.
  - "The protocol ships full value with zero Muninn-side code." — [M/docs/skald-protocol.md L65-103, L136-169, L195-218](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L65-L218)
  - Validator `scripts/skald_lint.py` has `EMITTERS = {"note-skill", "stop-hook", "bragi"}`. — [M/scripts/skald_lint.py L40](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/skald_lint.py#L40)
  - The `/note` skill writes to `$SKALD_VAULT_PATH`, then `~/.skald/config`, then defaults to `/opt/muninn/vault`. It refuses inside Saga containers (`$SAGA_ROLE` or `/workspace/.dvergr/`). — [M/docs/note-SKILL.md L15-27](https://github.com/algorhythmic/muninn/blob/45296bf/docs/note-SKILL.md#L15-L27)
- **Scheduling.** There are no cron, systemd or timer units in the repo. The reconcile script's docstring says it may be "run on a cron". The vault watcher is Phase 2+, and lint has a planned "Weekly or on-demand via Telegram trigger" cadence. — [M/scripts/reconcile-vector-index.py L14](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/reconcile-vector-index.py#L14); [M/docs/skald-protocol.md L206-218](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L206-L218); [M/docs/muninn-roadmap.md L100-108](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L100-L108)

### Inferences
- What is usable today is a local, stdio-only bookmark search. The "one MCP endpoint over every namespace" that the ADRs promise does not exist. No code embeds or serves `wiki/sessions/` or `wiki/projects/`, and the Qdrant collection is named for bookmarks.
- The synthesis container is very probably not buildable as written, because the Dockerfile's default base image is `ghcr.io/trailofbits/devcontainer:latest`. Saga's CLAUDE.md states "there is no pre-built image on a public registry" for Trail of Bits — [../../../CLAUDE.md L234](../../../CLAUDE.md). The build works only if a local image carries that tag, or if `BASE_IMAGE` is overridden. This is inference; the build was not attempted.

### Gaps
- The vault repo (`david/muninn-vault` on private Gitea `.18`) was not accessible. Its per-namespace CLAUDE.md, seeded project pages and any session pages could not be inspected.
- Whether the MCP server is registered with any Claude Code or Claude.ai client today could not be determined.

## 3. Relationship to Saga

### Takeaway
Saga's five dvergar wrote muninn v1's code in April. The operator then squashed it into one integration commit that fixed exactly the defects the retrospective named: the canonical INTEGER-keyed schema, epoch timestamps, and the never-same-vault guard. Since then muninn has developed outside Saga. It depends on Saga's credentials volume for synthesis, but **no Saga component uses muninn**: Bragi has no muninn output target, and none of the operator's newer standalone tools (`skald`, `braid`, `heimdall`) reference it.

### Cited Findings
- The Saga retrospective records Muninn v1 as Phase 3 run #1 on 2026-04-15: 5 dvergar, 329 passing tests, and two critical defects (schema divergence, missing safety guard). Each dvergr workspace "was a fresh `git init`". — [../../history/PHASE-3-RETROSPECTIVE.md L1-9, L38-58](../../history/PHASE-3-RETROSPECTIVE.md)
- Stream 1 diverged from SPEC: it was missing `source`, `source_id`, `captured_at`, `domain`, `era_label` and `enrichment_source`, used a SHA256 TEXT PK instead of INTEGER `bookmark_id`, and used ISO-8601 TEXT timestamps instead of epoch INTEGER. Stream 5 lacked the never-same-vault guard. — [../../history/PHASE-3-RETROSPECTIVE.md L40, L44](../../history/PHASE-3-RETROSPECTIVE.md)
- **Reconciled.** `ab874cb` (2026-04-16): "Integrates the five parallel work streams onto a single canonical schema per SPEC.md, replacing the orphan-branch decomposition … INTEGER bookmark_id PK with (source, source_id) upsert key … Epoch-second INTEGER timestamps … Vault generator enforces SPEC Decision 2 … via VaultPathConflictError … Tests: 406 pass." — [commit ab874cb](https://github.com/algorhythmic/muninn/commit/ab874cb). The current `schema.sql` matches. — [M/schema.sql L12-29](https://github.com/algorhythmic/muninn/blob/45296bf/schema.sql#L12-L29)
- The retrospective flagged Stream 2's dual pass as "serial per bookmark, not concurrent". The current scrape pipeline runs bookmarks concurrently through a semaphore. — [../../history/PHASE-3-RETROSPECTIVE.md L41](../../history/PHASE-3-RETROSPECTIVE.md); [M/src/muninn/scrape/pipeline.py L106-139](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/scrape/pipeline.py#L106-L139)
- Saga's INSIGHTS doc planned to "Carve `muninn` out of saga next … create the new repo, move `docs/MUNINN.MD` into it" and rated it Public ("Reference-implementation value is high"). The GitHub repo was created on 2026-04-16 and contains `MUNINN.MD`. — [../../history/INSIGHTS-2026-04-15.md L70, L104, L116, L351-352](../../history/INSIGHTS-2026-04-15.md); [GitHub API](https://api.github.com/repos/algorhythmic/muninn)
- Muninn vendors four Saga docs (`SAGA_ARCHITECTURE.MD`, `SAGA_SETUP.MD`, `SAGA_INSIGHTS_1/2.MD`) "to ground Muninn's synthesis-container design". — [commit 0c5fc4b](https://github.com/algorhythmic/muninn/commit/0c5fc4b)
- **Dependency direction is muninn → Saga infrastructure.** Muninn states it "Depends on Saga Phase 1+2 only (credentials volume, keepalive cron, devcontainer base, container-launch pattern) … Does **not** depend on Phase 3 orchestration." Bulk enrichment explicitly rejects dvergar (ADR-002). — [M/CLAUDE.md L57-59](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L57-L59); [M/docs/muninn-decisions.md L35-56](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L35-L56)
- ADR-007 classifies Muninn and Huginn as "Saga's **workloads**, not alternate deployments of Saga's pattern". It also says Muninn's `sessions/` namespace is the "**substrate** for Saga's generalization Move 1 (typed journals)". — [M/docs/muninn-decisions.md L172-191](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L172-L191)
- **The planned Saga-side integration never landed.**
  - Muninn's roadmap Phase 3 says "Coordinate with Saga. Bragi spec needs a second output target. Add a section to Saga's `saga-spec.md` …" (unchecked). — [M/docs/muninn-roadmap.md L68-78](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L68-L78)
  - Saga's Bragi persona lists only `/workspace/vault/` (= `/opt/saga/vault`) and `/workspace/lessons/` as read-write outputs. — [../../../bragi/CLAUDE.md L41-52, L271-279](../../../bragi/CLAUDE.md)
- In Saga, "muninn" appears only as history and examples (retrospective, journal format, lessons template, Odin/Mimir/Eir prompts). It never appears as a runtime target. A GitHub code search for "muninn" across the owner's repos returns hits only in `algorhythmic/saga`. — [GitHub code search, owner algorhythmic, 2026-10-14](https://github.com/search?q=owner%3Aalgorhythmic+muninn&type=code)
- **The operator's newer standalone tools do not reference muninn.**
  - `skald` (created 2026-09-10): "Skald provides an overview of conversation context across projects, terminals, desktop apps … It complements Heimdall: Skald preserves source conversations; Heimdall owns accepted task state." It has an archive daemon, CLI and TUI for Claude/Codex transcripts. — [algorhythmic/skald README](https://github.com/algorhythmic/skald)
  - `braid` (created 2026-09-05): "Explainable retrieval that fits a budget. Braid combines lexical search, embeddings, graph relationships and recency … Heimdall is the active integration; Saga is deferred." Its features are SQLite FTS5/BM25, brute-force cosine, PageRank and recency, with a byte-limited JSON context export. — [algorhythmic/braid README](https://github.com/algorhythmic/braid)
  - `heimdall`: "A local daemon that observes every surface you work in, keeps an event log, opens tasks in workspaces, and issues ranked work session plans on a schedule." — [GitHub repo list, algorhythmic](https://github.com/algorhythmic?tab=repositories)
  - None of these READMEs mentions muninn, Qdrant or the Skald Protocol (README grep). Code search finds no "muninn" or "Skald Protocol" hits outside `saga`.
- `huginn`, the sibling the muninn docs specify, does not exist under the account (`404`). — [GitHub API repos/algorhythmic/huginn](https://api.github.com/repos/algorhythmic/huginn)

### Inferences
- The operator's remark that Saga features were "re-implemented as standalone tools" maps onto muninn's July plan as follows. This is inference from READMEs only.
  - Session capture (muninn's Skald Protocol, `/note`, Bragi as emitter) appears to have moved to the standalone **skald**, but with a different design: a verbatim transcript archive rather than LLM-written vault narrative pages.
  - Retrieval (muninn's Qdrant + FTS5 MCP) appears to have a successor in **braid**, which fuses FTS5, dense, graph and recency signals.
  - The "planner" role appears to sit with the standalone **heimdall** daemon (ranked work-session plans), which braid integrates with first.
  - Muninn would then be left as a bookmark-corpus pipeline plus a vault design that the newer tools do not consume.
- Confidence is moderate. Neither `skald` nor `braid` mentions muninn, so this is succession by overlap of purpose, not by declared replacement.
- The name "skald" now denotes three different things: Bragi's epithet in Saga, the emitter role in muninn's protocol, and the standalone transcript archive. "Heimdall" denotes two: Saga's container-launch gate and the standalone planning daemon.

### Gaps
- Whether `skald`, `braid` or `heimdall` read muninn data through configuration (paths, env), as opposed to code references. Only READMEs and code search were checked; other researchers may cover those repos in depth.
- Whether Saga's running Bragi on the VM was ever reconfigured outside git to write the muninn vault. There is no evidence in either repo.

## 4. Relevance to the Odin I/O contract

### Takeaway
On paper, muninn was designed to be a knowledge store Odin reads, and a vault Bragi writes. Its protocol names "Odin" as a retrieval consumer, and `bragi` is a registered emitter. In practice neither path exists. The MCP is stdio-only, bookmark-only and unreachable from Odin's firewalled container, and Saga's Bragi has no muninn target.

It does not conflict with the UniiChat log on content: muninn explicitly excludes Saga's operational telemetry. It does conflict on one claim, namely where Generalization Move 1's typed journals live. It also assumes per-run "sessions", a boundary that a never-ending chat lacks. Muninn's project pages and Saga's project wikis can coexist under muninn's own layering rule. Muninn has no lessons layer.

### Cited Findings
- **Designed as Odin's knowledge source.** The protocol's role table says: "Retrieval | Muninn MCP (Phase 2) | `search`, `get_page`, `list_namespace` for session bootstrap by Claude Code, Claude.ai, Odin". — [M/docs/skald-protocol.md L42-50](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L42-L50). The Huginn spec closes the loop with "Saga queries Muninn for context on future builds". — [M/docs/huginn-spec.md L428](https://github.com/algorhythmic/muninn/blob/45296bf/docs/huginn-spec.md#L428)
- **Designed as Bragi's vault.** Under ADR-004, "`wiki/sessions/` holds Bragi-authored session journals, one per Saga run. `wiki/projects/{project}.md` holds the canonical current state … upserted by Bragi." — [M/docs/muninn-decisions.md L95](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L95). Emitter `bragi` covers "Saga *runs* (Odin, dvergar, Mimir activity)", and "a session has exactly one narrative author". — [M/docs/skald-protocol.md L52-63](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L52-L63)
- **Saga telemetry is out of muninn's scope:** "Saga's operational telemetry. Per-iteration journals, verdicts, and guidance stay in `/opt/saga/vault` — different cadence, different consumer." — [M/docs/skald-protocol.md L30-33](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L30-L33)
- **Current reachability.**
  - The MCP is stdio with five bookmark tools. — [M/src/muninn/consumers/mcp/server.py L19-59](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/mcp/server.py#L19-L59)
  - Qdrant is at `192.168.86.19`. — [M/src/muninn/config.py L90](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/config.py#L90)
  - Saga's container firewall allowlist adds only `.12` (Mosquitto), `.18` (Gitea) and `.15` (Grafana/InfluxDB). — [../../../CLAUDE.md L241-243](../../../CLAUDE.md)
- **Contract tools.** The contract's file tools are scoped to `/workspace/odin/projects/**`, `/workspace/lessons/**`, `/workspace/dvergr-workspaces/**` and `/workspace/saga-repo/**`. No knowledge-search tool exists. — [../ODIN-IO-CONTRACT.md §5 L216-245](../ODIN-IO-CONTRACT.md)
- **Move 1 claim conflict.**
  - The contract says the log "is the typed event stream GENERALIZATION.md Move 1 asked for". — [../ODIN-IO-CONTRACT.md L40-41](../ODIN-IO-CONTRACT.md)
  - Muninn ADR-007 says "Generalization Move 1 converts free-form journal entries into typed event streams — those typed entries will live in Muninn". It adds that Move 1 "extends frontmatter; it does not migrate the vault". — [M/docs/muninn-decisions.md L184-188](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L184-L188); [M/docs/skald-protocol.md L244-250](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L244-L250)
- **Session-boundary assumption.** Muninn session pages are "one per Saga run", carrying `session_id`, `started_at`, `ended_at` and `duration_min`. — [M/docs/skald-protocol.md L86-103](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L86-L103). The contract says "Odin has one chat that never ends". — [../ODIN-IO-CONTRACT.md L20-21](../ODIN-IO-CONTRACT.md)
- **Project pages versus project wikis.**
  - Saga's layer is `odin/projects/<p>/{raw,wiki}`, "the operational truth dvergar consume". — [../ODIN-IO-CONTRACT.md L253](../ODIN-IO-CONTRACT.md)
  - Muninn's layering rule: "A repo-local dashboard … is authoritative for **intra-project build state**. `wiki/projects/{slug}.md` is authoritative for **portfolio-level state**". — [M/docs/skald-protocol.md L179-193](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L179-L193)
- **Lessons.**
  - Saga's lessons store lives at `/workspace/lessons/<topic>/<date>-<project>-<slug>.md`, written by Bragi. — [../../../bragi/CLAUDE.md L140-204](../../../bragi/CLAUDE.md)
  - Muninn has no lessons namespace. Its nearest relative is `wiki/concepts/`, "emergent, populated during lint passes". — [M/docs/muninn-decisions.md L117-123](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L117-L123)
- **Operator-surface assumption.** Muninn Phase 4 plans a "Telegram command: `/synthesize {slice-spec}` … Uses the same Telegram bridge Saga already has". Phase 6 lint is "on-demand via Telegram trigger". — [M/docs/muninn-roadmap.md L89, L108](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L89)

### Inferences
- **As a knowledge store for the planner.** Plausible later, not now. A read-only `search_knowledge` tool would need several things: muninn's Phase 2 HTTP MCP with namespace tools, an indexer for the skald lane, a firewall rule for `.19` (or a read-only clone of the vault via Gitea `.18`), and a byte cap on results to protect the constant-size view.
  - Given `braid`'s budgeted, byte-limited context export, braid indexing the muninn vault is a better fit for the contract's "bytes, not tokens, constant view" discipline than muninn's own top-k MCP. Nothing shows braid indexes muninn today.
- **As the vault Bragi or skald writes.** The muninn side is ready as a contract: protocol, `skald_lint`, and `bragi` in the emitter registry. Under the contract, Bragi would derive muninn session pages from the chat JSONL. That requires defining a "Saga run" boundary, for example spec approval through the last dvergr completion of a project.
- **UniiChat log versus muninn.** These are complementary layers at different granularities. The log is the canonical, verbatim, fine-grained operational record; muninn session and project pages are derived, coarse, cross-project narrative. Declaring that explicitly resolves the Move 1 conflict and supersedes muninn ADR-007's claim.
- **Project wikis.** No conflict if muninn's layering rule is adopted: Saga wikis and contracts stay authoritative for build state, and muninn project pages hold portfolio state only. The overlap is in naming ("project wiki" and "project page"), not authority.
- **Lessons.** Muninn's ADR-001 logic (one wiki per operator) argues that cross-project lessons should eventually surface there too, perhaps as `concepts/`. Nothing decides this, and the contract's separate lessons layer is consistent with muninn as written.

### Gaps
- Whether the operator still intends muninn to be the cross-project memory substrate (ADR-001/004), or whether `skald` + `braid` + `heimdall` replaced that intent, is unstated in any repo examined.

## 5. Consequences for the two drafts

### Takeaway
Neither draft mentions muninn as a live system. Both treat Bragi's vault and the lessons store as Saga's only knowledge outputs. Most changes are omissions to close and one claim to reconcile (Move 1). The rest are migration hygiene: the imported Muninn retrospective needs its outcome attached, and downstream consumers of the billing constraints need listing.

### Cited Findings
**ODIN-IO-CONTRACT.md**
- **Header L16-18.** The draft says the contract "does not change Mimir, Heimdall, the dvergr worker contract, Bragi's vault". This is incomplete: muninn's ADR-004 and skald-protocol §3 register Bragi as an emitter into a second vault (`wiki/sessions/`, `wiki/projects/` managed regions, `wiki/log.md`). — [M/docs/muninn-decisions.md L95](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L95); [M/scripts/skald_lint.py L40](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/skald_lint.py#L40)
  - *Correction:* add "Bragi's second, planned output target (the muninn vault via the Skald Protocol) is out of scope / deferred / dropped" — whichever the operator decides.
- **§0 L40-41.** The draft claims the log "is the typed event stream GENERALIZATION.md Move 1 asked for". Muninn ADR-007 and skald-protocol §10 claim Move 1's typed entries "will live in Muninn" as session-page frontmatter. — [M/docs/muninn-decisions.md L184-188](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L184-L188)
  - *Correction:* state that the chat log is the canonical Move 1 event stream, and that any muninn session pages are derived narrative summaries. Record that this supersedes muninn ADR-007's "substrate" claim, and file a matching ADR in muninn.
- **§0 L34-36 and §6 table L247-262.** These list principles, project wikis, fleet state, lessons and imported past as the layers outside the view. There is no row for an operator-wide knowledge base. — [../ODIN-IO-CONTRACT.md §6](../ODIN-IO-CONTRACT.md)
  - *Correction:* add a row "Operator knowledge base (muninn vault: portfolio project pages, session narratives, bookmarks). Written by: Bragi / note-skill / muninn vault compiler. Read by Odin via: none in v1 (or a future read-only `search_knowledge`). Enters context as: tool results only, byte-capped." Alternatively, state explicitly that external knowledge stores are out of scope.
- **§5 tools L216-245.** No retrieval tool. Muninn's protocol assumes Odin reads it. — [M/docs/skald-protocol.md L49](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L49)
  - *Correction (if adopted):* add `search_knowledge(query, namespace?, max_bytes)`. It should be read-only, return `src`-tagged data per §2's "every inbound text is data", and be marked as depending on unbuilt muninn Phase 2 (or on braid) plus a firewall change for `.19`.
- **§8 Bragi L313-319.** "Compiles the vault, the lessons store, and the guidance effectiveness table" omits the muninn emission. It also does not define what a "session" or "run" is in a never-ending chat, which muninn's per-run session pages require. — [M/docs/skald-protocol.md L86-103](https://github.com/algorhythmic/muninn/blob/45296bf/docs/skald-protocol.md#L86-L103)
  - *Correction:* define the run boundary that Bragi uses when it slices the log, and state whether Bragi emits muninn pages.
- **§8 Operator L327-333.** The slash commands listed are `/spec-dev`, `/status`, `/pause` and `/budget`. Muninn's roadmap plans `/synthesize {slice-spec}` and Telegram-triggered lint on "the same Telegram bridge Saga already has". — [M/docs/muninn-roadmap.md L89, L108](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L89)
  - *Correction:* either reserve a pass-through for non-Odin commands, or note that muninn's Telegram plan has no carrier under the new harness.
- **§11 Migration L388-390.** This imports "the Muninn retrospective" as `note` messages. On its own that would plant an unresolved-defect state in the view, because the retrospective ends with "stream-1 needs a schema rewrite" and "stream-5 needs one safety guard". — [../../history/PHASE-3-RETROSPECTIVE.md L373-377](../../history/PHASE-3-RETROSPECTIVE.md)
  - *Correction:* also import a `note` recording the outcome. On 2026-04-16 muninn commit `ab874cb` reconciled the schema, added `VaultPathConflictError` and reported 406 passing tests. Muninn is now a standalone repo (`algorhythmic/muninn`), not a Saga project, dormant since 2026-07-17. — [commit ab874cb](https://github.com/algorhythmic/muninn/commit/ab874cb)
- **§0 L48.** The use of the Muninn "contracts holding" claim as a compaction example stays valid. The retrospective is the source.

**HARNESS-LANDSCAPE-2026-10.md**
- **§4 pattern 8, L339-343.** The draft says "Karpathy's index/log/lint shape for Bragi (already half-adopted)". This is incomplete: the operator's fuller adoption of that pattern is muninn itself (ADR-001/006; `wiki/index.md`, `wiki/log.md`, `skald_lint.py`, Phase 6 lint). — [M/docs/muninn-decisions.md L139-168](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L139-L168)
  - *Correction:* cite muninn, and decide whether `/opt/saga/vault` stays a second Karpathy-shaped wiki or Bragi emits into muninn.
- **§5 "What in Saga should change", L378-436.** There is no item for the open integration debt with muninn: the Bragi second target and the `saga-spec.md` section that muninn's roadmap asked for. — [M/docs/muninn-roadmap.md L74](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L74); [../../../bragi/CLAUDE.md L41-52](../../../bragi/CLAUDE.md)
  - *Correction:* add a §5.2 or §5.4 bullet, "Decide Bragi ↔ muninn (emit, defer, or drop); if dropped, tell muninn (ADR-004/007)".
- **§6 Step 0, L439-445, and §5.1 L382.** The billing re-test also governs muninn. Muninn's synthesis refuses to run when `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` is set, and forbids `claude -p`, citing the same April findings. Its Haiku enrichment is API-key billed. — [M/scripts/launch-synthesis.sh L12-37](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/launch-synthesis.sh#L12-L37); [M/SPEC.md L29-34](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L29-L34)
  - *Correction:* list muninn (SPEC Decision 6, `launch-synthesis.sh`, `containers/synthesis/`) among the documents to update after the re-test.
- **§4 pattern 7 and §5.4 L432 ("single refresher").** Muninn's synthesis container is another consumer of `saga-claude-credentials`, mounted **read-only**. That fits "keepalive is the only process allowed to refresh". — [M/scripts/launch-synthesis.sh L69](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/launch-synthesis.sh#L69)
  - *Correction:* include muninn in the inventory of volume consumers.
- **§5.3 L424 (per-image Heimdall policy).** Muninn launches its container with a direct `docker run` on the host, outside Heimdall. Per-image credential policy in Heimdall would not cover it. — [M/src/muninn/synthesis/container.py](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/synthesis/container.py)
  - *Correction:* note that non-Odin launchers of credentialed containers exist on the host.
- **§7 L529 ("Is Saga currently running?").** Corroborating evidence: muninn's July work went ahead without Saga, and muninn now calls itself "a standalone dataset that Saga happens to be one builder of". — [M/CLAUDE.md L63](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L63)
- **Both drafts, naming.** "Heimdall" and "Bragi (skald)" now collide with the operator's standalone `heimdall` (planning daemon) and `skald` (conversation archive) repos, and with muninn's "skald" emitter role. — [algorhythmic/skald](https://github.com/algorhythmic/skald); [algorhythmic/braid](https://github.com/algorhythmic/braid)
  - *Correction:* qualify the names as "Saga's Heimdall launcher" and "Saga's Bragi" on first use, and add a glossary line.

### Inferences
- None of these is a contradiction that invalidates either draft's main recommendation (extract Odin; UniiChat as memory). They are scope statements to make explicit. The Move 1 ownership claim is the only point where two of the operator's own documents currently disagree.
- If the operator confirms that `skald`, `braid` and `heimdall` superseded muninn's session-capture and retrieval plans, the corrections shrink. The contract would then cite those tools (for example, braid as the retrieval layer behind any knowledge tool, skald as Bragi's transcript source) instead of muninn, and muninn would be noted as a bookmark corpus that the new retrieval layer may ingest.

### Gaps
- The right correction for the knowledge-store row depends on an operator decision (muninn versus braid-indexed sources versus nothing in v1) that no repo records.

## 6. Gaps and risks

### Takeaway
Muninn is a solid but unfinished, dormant pipeline whose larger promises (one MCP over every namespace, Bragi integration, synthesis) are unbuilt. Its public README misdescribes it. Any Saga design that leans on it today would depend on Phase 2 work that does not exist, on a container that probably cannot build as written, and on credential and launch paths that bypass Saga's Heimdall.

### Cited Findings
- **v1 unshipped.** The real-export bulk run and the full Qdrant index are both unchecked. — [M/docs/muninn-roadmap.md L42-46](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-roadmap.md#L42-L46)
- **ADR-008 unratified.** Its status is "Proposed (2026-07-16 …; pending operator ratification)". — [M/docs/muninn-decisions.md L197](https://github.com/algorhythmic/muninn/blob/45296bf/docs/muninn-decisions.md#L197)
- **Stale README.** It is misleading for any agent that reads README before CLAUDE.md. — [M/README.md L130-153](https://github.com/algorhythmic/muninn/blob/45296bf/README.md#L130-L153)
- **Guard weaknesses.** The vault guard is skipped when `MUNINN_PERSONAL_VAULT_DIR` is unset, and the SPEC's sentinel file is not implemented. — [M/src/muninn/consumers/vault/compiler.py](https://github.com/algorhythmic/muninn/blob/45296bf/src/muninn/consumers/vault/compiler.py); [M/SPEC.md L56](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L56)
- **Synthesis does not work end to end.** The task JSON is never fed in, and the schema rejects `attempt`. — [M/CLAUDE.md L40](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L40). The base image `ghcr.io/trailofbits/devcontainer:latest` is unpinned, and Saga records that no public prebuilt image exists. — [M/containers/synthesis/Dockerfile L11](https://github.com/algorhythmic/muninn/blob/45296bf/containers/synthesis/Dockerfile#L11); [../../../CLAUDE.md L234](../../../CLAUDE.md)
- **Shared-subscription contention.** The synthesis container would draw on the same Max credentials volume as Odin, Mimir and the dvergar, launched outside Heimdall. — [M/scripts/launch-synthesis.sh L66-75](https://github.com/algorhythmic/muninn/blob/45296bf/scripts/launch-synthesis.sh#L66-L75)
- **Prompt cache never hits.** Haiku prompt caching showed 0% hits ahead of a ~39k-call run. There is no robots.txt handling. Qdrant runs without auth on the LAN. — [M/CLAUDE.md L38-41](https://github.com/algorhythmic/muninn/blob/45296bf/CLAUDE.md#L38-L41); [M/SPEC.md registry](https://github.com/algorhythmic/muninn/blob/45296bf/SPEC.md#L61-L72)
- **Public repo, no license, vendored private docs.**
  - The repo has no license, so the "reference-implementation value" goal in Saga's INSIGHTS is not legally usable by others. — [GitHub API](https://api.github.com/repos/algorhythmic/muninn); [../../history/INSIGHTS-2026-04-15.md L104](../../history/INSIGHTS-2026-04-15.md)
  - The repo also mirrors April snapshots of Saga's architecture, setup and insights docs (LAN IPs `.11–.20`), although `algorhythmic/saga` itself is private. Spot-checked: no tokens found. — [M/docs/SAGA_SETUP.MD](https://github.com/algorhythmic/muninn/blob/45296bf/docs/SAGA_SETUP.MD); [GitHub API repos/algorhythmic/saga (private)](https://api.github.com/repos/algorhythmic/saga)
- **Huginn spec is orphaned.** The spec in muninn says Saga Phase 3 will build Huginn, but no `huginn` repo exists. — [M/docs/huginn-spec.md L7, L424](https://github.com/algorhythmic/muninn/blob/45296bf/docs/huginn-spec.md#L7); [GitHub API 404](https://api.github.com/repos/algorhythmic/huginn)

### Inferences
- The highest-impact risk for the drafts is silent drift. If the contract and harness docs never mention muninn, muninn's ADR-004 and ADR-007 will keep asserting a Bragi integration and a Move 1 home that Saga no longer intends. Any future Claude session reading muninn's CLAUDE.md would then act on them.
- The second risk is naming collision across the operator's repos ("skald" ×3, "Heimdall" ×2). Agents that read across repos could conflate them.

### Gaps
- **Could not determine:**
  - The private vault's contents (`david/muninn-vault` on Gitea `.18`).
  - Whether `/note` is installed and has written any session pages.
  - Whether the real bookmark export has been processed.
  - Whether any running process (MCP server, cron) exists on the homelab.
  - Whether `skald`, `braid` or `heimdall` consume muninn data through configuration.
  - Whether the operator still endorses ADR-001/004 now that the standalone tools exist.
- Test pass counts (329 in the retrospective, 406 at `ab874cb`) are as reported, not verified, because executing repo code was out of bounds.
