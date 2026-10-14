# Journal Format

Defines the structure of journal entries written by dvergar and by Odin.
Sourced from `saga-spec.md` §7 — keep in sync with the spec if either
changes.

Two journal types exist:

1. **Per-project journal** — `/workspace/.dvergr/journal.md` inside each
   dvergr container. Written by the dvergr after every iteration.
2. **Master journal** — `odin/master-journal.md` in Odin's container.
   Written by Odin after evaluating incoming dvergr entries and after
   human interactions via Telegram. This file IS Odin's memory across
   restarts and context resets.

## Per-Project Journal

The container's CLAUDE.md instructs the dvergr to append an entry after
each loop iteration. Each entry captures:

- **Task** — the task or user story being worked
- **Approach** — strategy chosen and why
- **What Worked** — successful bits of the approach
- **What Didn't Work** — dead ends, with causes
- **Decisions Made** — concrete architectural or implementation choices
- **Discoveries** — non-obvious things learned (libraries, behaviors, gotchas)
- **Test Results** — pass/fail counts and context on failures
- **Files Changed** — modified / added / deleted files
- **Open Questions** — unresolved things worth Odin's attention
- **Next Iteration Plan** — what the dvergr intends to do next

See `journal/templates/iteration-entry.md` for the blank template.

### Example iteration entry

```markdown
## Iteration 14 — 2026-04-10T01:43:12Z

### Task
US-007: Implement caching layer for API responses

### Approach
Chose Redis as the cache backend over in-memory LRU because the
multi-instance deployment requires shared cache state. Used the
`ioredis` library with connection pooling.

### What Worked
- Redis connection wrapper with automatic reconnection handles
  broker restarts gracefully
- TTL-based expiration eliminates the need for manual invalidation
  on most read-heavy endpoints

### What Didn't Work
- Initial attempt to cache at the ORM level caused stale data issues
  with nested relations. Moved caching up to the route handler level
  where the serialized response is the cache value.

### Decisions Made
- Cache key format: `{endpoint}:{hash(query_params)}` — simple,
  debuggable, and avoids key collisions
- Default TTL: 300s for list endpoints, 3600s for individual resources
- No cache warming — cold start latency is acceptable for this scale

### Discoveries
- The `serialize-javascript` package handles circular references that
  `JSON.stringify` chokes on — useful for caching complex API responses
  that include nested model references

### Test Results
- 42 passing, 3 failing
- Failures are in cache invalidation edge cases (concurrent writes
  during TTL window) — will address next iteration

### Files Changed
- src/middleware/cache.ts (new)
- src/config/redis.ts (new)
- src/routes/predictions.ts (modified — added cache middleware)
- tests/cache.test.ts (new, 3 failures)
- package.json (added ioredis)

### Open Questions
- Should cache invalidation be event-driven (pub/sub on writes) or
  TTL-only? Event-driven is more correct but adds complexity.

### Next Iteration Plan
- Fix the 3 failing cache invalidation tests
- Add cache hit/miss metrics endpoint for monitoring
```

### Publishing

After writing an entry to `/workspace/.dvergr/journal.md`, the dvergr's
`post-iteration.sh` hook publishes the latest entry (tail -n 50) to
`dvergr/{project}/{instance}/journal` via MQTT. See
`mqtt/TOPIC-SCHEMA.md` and `dvergr-hooks/post-iteration.sh`.

## Master Journal (Odin)

Sections:

- **Last Updated** — timestamp of most recent write
- **Active Projects** — per-project status, current phase, health,
  key insights
- **Cross-Project Patterns** — recurring approaches and shared failure
  modes, cross-referenced by project/instance/iteration
- **Guidance Effectiveness Log** — table tracking what guidance Odin
  issued and whether it was adopted
- **Human Interactions** — log of Telegram Q&A with summary of
  actions taken
- **Principles** — managed by the self-evolution system starting in
  Phase 6. See `saga-spec.md` §11 for the evolution cycle and
  principle format.
- **Log** — chronological event log under the structured entry format
  below. Append-only; project retrospectives become a single Log
  entry titled `{date} — {project} retrospective` (see Odin's
  CLAUDE.md § "Project-completion ritual").

See `journal/templates/master-entry.md` for the blank template.

### Required entry format (`## Log` entries)

Every entry under `## Log` MUST have all four sections. Empty
sections are not allowed; if a section genuinely has nothing, write
`none` explicitly with a one-clause reason. Empty implies "I didn't
think about this," not "nothing here." The format exists to force
the inference step that Phase 3 run #1's journal repeatedly skipped.

```markdown
### {YYYY-MM-DD} — {short title}

**Events**
- Bare facts. What MQTT/state.json/files told you. No interpretation.
- One bullet per event. Cite SHA / iteration / file as appropriate.

**Observations**
- What surprised you. What assumption was tested.
- "Expected X but saw Y." "This contradicts/confirms our earlier
  estimate of Z." "First time we've seen pattern P."
- If nothing surprised you, say so explicitly with a reason
  ("Nothing surprising — predicted path"). Surprise is information.

**Evidence**
- Pointers (not paraphrase) to the specific journal entries / SHAs /
  verdict files / status.json fields backing each Observation.

**Implication**
- How this should change future decomposition / guidance / principles.
- "If we see pattern P again, do X." "Update Cross-Project Patterns
  with Y." "Propose principle Z (need 1 more data point)."
- "none" is allowed only for genuinely routine events. A surprise
  in Observations almost always implies an Implication.
```

### Worked example — bad → good

The actual most-consequential event of Phase 3 run #1 was instance-1
completing its real work in iteration 1 then re-verifying for 12
more iterations — the autoreason degradation signature. Here is how
that event was journaled (bad), and how the new format requires it
to be journaled (good).

#### Bad (what Phase 3 run #1 actually wrote)

```markdown
### 2026-04-16 — Heimdall Updated, Instance-1 Launched and COMPLETE

- Third launch attempt accepted after operator updated Heimdall to
  accept `repo` and `prd` fields and auto-create workspace directories.
- muninn/instance-1 completed in iteration 1 (then 12 re-verification passes).
  - 160 tests (138 unit sanitization, 22 integration), 0 failing
  - All 7 success criteria verified
  - Commit d6887a8: "feat: implement muninn stream 1 — ingest + sanitization pipeline"
  - 28 files created. Built entire pipeline in single pass.
- Instance-2 (Scrape) launch config submitted immediately.
- **Status: instance-1 COMPLETE, instance-2 launch submitted.**
```

The entry is structurally indistinguishable from a routine
status-tracker post. The most important fact in the run — "iter 1
work, iter 2-13 churn" — sits as a parenthetical. No surprise
recorded. No change to future estimates. No flag for the autoreason
pattern that the retrospective spent days analyzing afterward.

#### Good (what the new format requires)

```markdown
### 2026-04-16 — muninn/instance-1 completed in 1 iteration + 12 churn

**Events**
- 3rd launch attempt accepted after heimdall fix (repo + prd field
  support) — see commit 10e50a5.
- muninn/instance-1 status flipped to "completed" at iter 1, commit
  d6887a8 ("feat: implement muninn stream 1 — ingest + sanitization
  pipeline"), 160/0 tests, 28 files.
- Iters 2-13 produced no new commits and no test count changes;
  status stayed "completed" throughout.
- Instance-2 launch config submitted.

**Observations**
- 1-iter-real-work-then-12-iter-churn is the autoreason degradation
  signature in its purest form. Estimated 15 iterations; productive
  work was 1; the 12 trailing iterations are pure re-verification
  noise (the dvergr re-running its tests, not adding code).
- The completion-promise mechanism failed to short-circuit — the
  dvergr believes it's making progress when it isn't. This is the
  same pattern the smoke test showed at smaller scale (smoke iter
  2-5 re-validation under rewritten PRD, journal entry 2026-04-13).
- The 15-iteration estimate was off by 14×. The estimate was based
  on PRD complexity heuristics; actual difficulty was much lower
  because the spec's contracts were unusually clean for stream 1.

**Evidence**
- `dvergr/muninn/instance-1/status` retained payload: tests_passing=160
  from iter 1 onward, no change through iter 13.
- `git log` on instance-1's stream branch: only one commit, d6887a8.
  Iters 2-13 produced zero commits.
- Mimir verdict file `mimir/processed/decomposition-muninn.md`
  estimated max 15 iterations for this stream.
- `dvergr/smoke/instance-1/journal` 2026-04-13 entry: smoke test
  showed iter 1 produced done.txt, iters 2-5 re-validated under a
  rewritten PRD without producing new artifacts. Same shape.

**Implication**
- This is the second confirmed sighting of the
  one-real-iteration-then-N-churn pattern (smoke test was the first).
  Add to `## Cross-Project Patterns` immediately as a recognized
  failure mode: "dvergar may declare completion early then burn
  remaining iteration budget on re-verification; trust commit count
  over self-reported status when assessing 'is this dvergr done?'"
- For run #2 estimation: when stream complexity is "low" (clean
  contracts, well-scoped success criteria), iteration budget should
  be bounded at 5, not 15. Saves ~10 iterations of subscription
  budget per stream.
- Propose a Phase 3 mitigation: convergence/plateau hooks (eventually
  shipped as proposal #5 in `docs/history/PHASE-3-IMPROVEMENTS.md`). With
  `commit-plateau` firing at k=3 unchanged HEAD SHAs, instance-1
  would have been flagged at iter 4 instead of consuming all 12.
- Eligible for principle proposal once we see this in a third project
  (≥2 independent data points, smoke + muninn count as one project's
  worth of evidence).
```

The Good version is longer (~50 lines vs ~10) but produces
durable artifacts: a Cross-Project Patterns candidate, an updated
estimation heuristic, a mitigation proposal, and a principle
candidate marked for future promotion. The Bad version produces
nothing future-Odin can build on.

### Sections the worked example is silent on

When you have nothing to say in a section, name the silence:

- `**Implication**: none — routine sequential launch, no new pattern`
- `**Observations**: nothing surprising — instance-2 completion
  matches the iteration estimate within 10%`

Saying `none` deliberately is information ("I checked, nothing here").
Omitting the section is failure ("I didn't check"). Mimir's
journal-quality reviews (when implemented) treat omissions as REJECT.

### Other-section examples (`Active Projects`, `Cross-Project Patterns`, etc.)

The `## Active Projects` section stays one-line-per-project:

```markdown
### nexus (3 dvergar)
- **Status**: Running, 67% of PRD complete
- **Current Phase**: Backend API hardening
- **Health**: instance-1, instance-3 progressing; instance-2 stuck
  on auth refactor for 4 iterations — guidance published 2026-04-10
- **Key Insight**: serialize-javascript pattern from iter 14 may
  port to esp32-firmware telemetry encoding
```

`## Cross-Project Patterns` accumulates as Log entries promote
observations into recognized patterns:

```markdown
### Premature-completion churn
- Dvergar may declare completion early then burn remaining iteration
  budget on re-verification. Trust commit count over self-reported
  status. Sources: smoke/instance-1 (2026-04-13), muninn/instance-1
  (2026-04-16). Mitigation: commit-plateau hook (proposal #5,
  PHASE-3-IMPROVEMENTS).
```

`## Guidance Effectiveness Log` stays as a table:

| Date | Target | Guidance Summary | Outcome |
|------|--------|-----------------|---------|
| 04-10 | nexus/instance-2 | Switch from JWT refresh to sessions | Pending |
| 04-09 | esp32/instance-1 | Use deep sleep periodic BLE scan | Adopted, reduced power 80% |

## Persistence Rules

- Odin reads `master-journal.md` completely on every startup or context
  reset to restore its operational context. If the file grows beyond
  what's readable in one pass, the monthly consolidation step (Phase 6,
  §11) is responsible for compressing older entries into patterns.
- Dvergar read their own `journal.md` at the start of every iteration
  as part of the `/ralph-loop` loop, to maintain continuity across
  iterations.
- Both journals are plain markdown, committed to the project's git repo
  (for dvergar) or the Odin container's mounted volume (for Odin).
  They are not ephemeral state — losing them is losing memory.
