# MQTT Topic Schema

Canonical specification for all MQTT topics used by Saga. Sourced from
`saga-spec.md` §6 — keep this file in sync with the spec if either
changes.

All Saga topics live under the `dvergr/` prefix, coexisting with the
`surveillance/` and `frigate/` topics already on the Mosquitto broker at
**192.168.86.12** (homelab CT 101). Do not publish Saga data under other
prefixes and do not subscribe to `surveillance/` or `frigate/` from
Saga components.

## Topic Hierarchy

```
dvergr/
├── {project}/
│   ├── {instance}/
│   │   ├── status              # Machine-readable state (JSON)
│   │   ├── journal             # Latest journal entry (Markdown)
│   │   ├── guidance            # Instructions FROM Odin (Markdown)
│   │   ├── heartbeat           # Periodic alive signal (JSON)
│   │   ├── metrics             # Journal word-count telemetry (JSON)
│   │   ├── converged           # Convergence-stuck signal (JSON, retained)
│   │   ├── commit-plateau      # No new commits across N iters (JSON, retained)
│   │   ├── completion-likely   # Tests stable + green = done (JSON, retained)
│   │   └── alert               # Escalation requiring human attention (JSON)
│   └── summary                 # Odin-generated project summary (Markdown)
├── odin/
│   ├── status                  # Odin's own state (JSON)
│   ├── inbox                   # Messages from Telegram bridge (if needed)
│   ├── synthesis               # Cross-project insights (Markdown)
│   └── commands                # Control commands (JSON)
└── ...

saga/
└── events/
    ├── dvergr_completed        # dvergr ralph loop finished successfully
    ├── decomposition_approved  # Odin decomposition plan Mimir-approved
    ├── prd_launched            # Odin launched a dvergr PRD via heimdall
    └── ...                     # extensible per operator need
```

`{project}` is the short project name (e.g. `nexus`, `esp32-firmware`).
`{instance}` is the container identifier (e.g. `instance-1`, `instance-2`).
The word "instance" here is used only as a container ID component — dvergr
agents themselves are referred to as "dvergar" in prose per `CLAUDE.md`.

## Topic Details

### `dvergr/{project}/{instance}/status`

- **Publisher**: dvergr container, after each loop iteration
- **QoS**: 1 (at least once)
- **Retained**: yes — latest state is always available to new subscribers

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

Valid `status` values: `running` | `paused` | `completed` | `max_iterations_reached` | `failed` | `rate-limited`

### `dvergr/{project}/{instance}/journal`

- **Publisher**: dvergr container, after each iteration
- **QoS**: 1
- **Retained**: no — historical entries live in git and in
  `/workspace/.dvergr/journal.md` inside the container
- **Payload**: markdown string following `journal/JOURNAL-FORMAT.md`

### `dvergr/{project}/{instance}/guidance`

- **Publisher**: Odin (indirectly — Odin writes to
  `outgoing-guidance/{project}/{instance}.md` and `ratatoskr.py`
  publishes)
- **QoS**: 1
- **Retained**: yes — dvergr reads the latest on next iteration start
- **Payload**: markdown string

Example:

```markdown
## Guidance for nexus/instance-1 — Iteration 15

### Priority Adjustments
- Deprioritize the Redis sentinel config — single-node Redis is sufficient
  for the current scale. Focus on the API response serialization instead.

### Cross-Project Insight
- instance-2 on the esp32-firmware project solved a similar serialization
  issue using MessagePack instead of JSON. Their journal entry from
  iteration 8 documented a 4x size reduction. Consider evaluating this
  for the cache payload format.

### Quality Concerns
- The test coverage for the cache invalidation path is thin. Add edge
  case tests for TTL expiry during concurrent reads before moving to
  the next task.

### Architectural Note
- The current approach of wrapping every endpoint individually will
  create maintenance burden. Consider a middleware-based approach
  that applies caching declaratively.
```

### `dvergr/{project}/{instance}/heartbeat`

- **Publisher**: dvergr container, every 60 seconds
- **QoS**: 0 (fire-and-forget — heartbeats are cheap, missed ones tolerable)
- **Retained**: yes

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "alive": true,
  "timestamp": "2026-04-10T01:44:00Z",
  "cpu_percent": 12.3,
  "memory_mb": 847,
  "disk_used_percent": 34
}
```

### `dvergr/{project}/{instance}/metrics`

- **Publisher**: `ratatoskr.py` (computed from each incoming journal
  payload, not emitted by the dvergr itself)
- **QoS**: 1
- **Retained**: yes — latest value available on reconnect for Odin and
  Grafana
- **Payload**: JSON

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "journal_word_count": 412,
  "delta_words": -87,
  "monotonic_shrink_streak": 2,
  "timestamp": "2026-04-10T01:45:00Z"
}
```

Purpose: autoreason (Nous Research) degradation signature. Naive
critique-and-revise loops shrink outputs 59–70% across iterations as
critics invent flaws and writers trim to appease them. Three or more
consecutive shrinking entries (`monotonic_shrink_streak >= 3`) suggests
Mimir is over-critiquing and dvergr output is degrading — ratatoskr
logs a warning at that threshold; downstream consumers should review
recent Mimir verdicts for `APPROVE_UNCHANGED` candidates that were
instead given concrete critiques. See `docs/history/INSIGHTS-2026-04-13.md` §2.

`delta_words` is the difference vs. the previous journal entry from
the same dvergr. First entry after ratatoskr startup reports
`delta_words=0` and `monotonic_shrink_streak=0` (counter is in-memory
and resets on restart, deliberately — stale streaks across a ratatoskr
crash would mislead).

### `dvergr/{project}/{instance}/converged`

- **Publisher**: dvergr container, from
  `dvergr-hooks/check-convergence.sh` invoked by post-iteration
- **QoS**: 1
- **Retained**: yes — latest convergence state is always available to
  new subscribers (Odin, Grafana)
- **Payload**: JSON

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "iteration": 18,
  "word_count": 412,
  "delta_words": -3,
  "convergent_streak": 2,
  "word_threshold": 10,
  "streak_threshold": 2,
  "timestamp": "2026-04-14T09:30:00Z"
}
```

Purpose: autoreason's "do nothing wins k=2" convergence signal
(Nous Research). When consecutive iterations show `|delta_words| <=
word_threshold`, the dvergr has plateaued — stuck or done — even when
its own completion promise still thinks there is work to do.

Distinct from the `metrics` topic (which tracks *shrinkage*, the
Mimir-induced degradation signature) and from `alert` (which the
dvergr or Odin emits for arbitrary escalations). Convergence is a
specific, machine-computed condition and earns its own topic.

Consumer: Odin (via ratatoskr, which routes these into
`incoming-alerts/`). Odin decides whether to tear down the loop —
e.g. write a `commands/` record so heimdall stops the container, or
publish guidance asking the dvergr to reconsider scope.

See `dvergr-hooks/check-convergence.sh` for threshold defaults and
`docs/history/INSIGHTS-2026-04-13.md` §4 for the rationale.

### `dvergr/{project}/{instance}/commit-plateau`

- **Publisher**: dvergr container, from
  `dvergr-hooks/check-commit-plateau.sh` invoked by post-iteration
- **QoS**: 1
- **Retained**: yes — latest plateau state always available
- **Payload**: JSON

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "iteration": 12,
  "sha": "a1b2c3d",
  "streak": 3,
  "streak_threshold": 3,
  "timestamp": "2026-04-16T11:00:00Z"
}
```

Purpose: detects "talking but not coding" stalls — iteration advances
but `git rev-parse HEAD` of `/workspace/repo` is unchanged. Phase 3
run #1 saw instance-1 spend 12 iterations re-verifying after
self-completing in iteration 1; word-count convergence missed it
because re-verification produced verbose journals; this signal would
have caught it. See `docs/history/PHASE-3-IMPROVEMENTS.md` proposal #5.

Distinct from `converged` (word-count plateau) and `completion-likely`
(test-stable + green plateau). Action Odin takes per signal:

- `converged`         — possibly stuck OR done; assess via state.json
- `commit-plateau`    — stuck (no code progress); issue corrective guidance
- `completion-likely` — likely done; consider issuing completion promise

Skipped silently in legacy mode (no `/workspace/repo`); the
workspace/repo split (proposal #1) is what makes this hook useful.

### `dvergr/{project}/{instance}/completion-likely`

- **Publisher**: dvergr container, from
  `dvergr-hooks/check-test-plateau.sh` invoked by post-iteration
- **QoS**: 1
- **Retained**: yes
- **Payload**: JSON

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "iteration": 4,
  "tests_passing": 42,
  "tests_failing": 0,
  "streak": 2,
  "streak_threshold": 2,
  "timestamp": "2026-04-16T11:05:00Z"
}
```

Purpose: detects "tests stable AND green AND non-zero" — strong
evidence the dvergr's actual work is complete and it's now in
re-verification mode. Stronger semantics than `commit-plateau`: not
just "no progress" but "looks done". Odin should consider issuing the
completion promise rather than corrective guidance.

Threshold defaults to streak=2 (lower than `commit-plateau`) because
test stability is a more specific signal than commit stability.

### `dvergr/{project}/{instance}/alert`

- **Publisher**: dvergr container OR Odin
- **QoS**: 2 (exactly once — alerts must not duplicate)
- **Retained**: no

```json
{
  "project": "nexus",
  "instance": "instance-1",
  "severity": "warning",
  "type": "stuck_loop",
  "message": "3 consecutive iterations with no test improvement",
  "iteration": 14,
  "timestamp": "2026-04-10T01:45:00Z",
  "suggested_action": "Review journal entries 12-14, consider revised approach"
}
```

Valid `severity` values: `info` | `warning` | `critical`
Valid `type` values: `stuck_loop` | `test_regression` | `rate_limit` | `circuit_break` | `quality_concern` | `completion`

### `dvergr/{project}/summary`

- **Publisher**: Odin
- **QoS**: 1
- **Retained**: yes
- **Payload**: markdown project summary, regenerated when project state
  changes meaningfully

### `dvergr/odin/status`

- **Publisher**: Odin
- **QoS**: 1
- **Retained**: yes
- **Payload**: JSON state describing Odin's current activity, active
  projects, and any pending Mimir evaluations

### `dvergr/odin/inbox`

- **Publisher**: Telegram bridge (if a bridge process is used separately
  from Odin's Channels integration)
- **QoS**: 1
- **Retained**: no

### `dvergr/odin/synthesis`

- **Publisher**: Odin
- **QoS**: 1
- **Retained**: yes
- **Payload**: markdown cross-project insights and patterns

### `dvergr/odin/commands`

- **Publisher**: Odin (via `ratatoskr.py` reading `outgoing-commands/`)
- **QoS**: 1
- **Retained**: no
- **Payload**: JSON control commands for dvergr lifecycle actions

```json
{
  "project": "nexus",
  "instance": "instance-2",
  "action": "stop",
  "reason": "Stuck for 4 iterations, human approved stop",
  "timestamp": "2026-04-10T03:15:00Z"
}
```

Valid `action` values: `start` | `stop` | `restart` | `destroy`

Note: these are advisory commands on the MQTT bus. Actual container
lifecycle actions are executed by `heimdall.py` on the Docker
host VM in response to YAML request files in the shared launch-requests
volume, not by reading MQTT. See `saga-spec.md` §4 for the security
model.

## Lifecycle events (`saga/events/<kind>`)

Point-in-time lifecycle events. **Distinct from `dvergr/.../*`
topics in two important ways:**

1. **Not retained.** Events fire once and are gone — they describe
   transitions, not state. Subscribers that care about "what happened
   while I was offline" should keep their own log.
2. **Schema is uniform across kinds.** Every event has the same
   envelope; the `data` field carries kind-specific detail.

Envelope:

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

Per-kind `data` shape:

| `kind` | Publisher | `data` shape |
|---|---|---|
| `dvergr_completed` | dvergr `post-iteration.sh` when status crosses to "completed" or "max_iterations_reached" | `{iteration, tests_passing, tests_failing}` |
| `decomposition_approved` | Odin (via outgoing-events/) after writing the decomposition decision record | `{streams, allocation, mimir_verdict}` |
| `prd_launched` | Odin (via outgoing-events/) after `mv`'ing each draft launch-request | `{model, effort, depends_on, secrets}` |

Add new kinds as new operator-driven workflows surface — kinds are
strings, not enums, and subscribers filter by the topic suffix. The
intended consumer is the observability stack (Telegraf → InfluxDB →
Grafana, see `docs/architecture/OBSERVABILITY.md`); a future usage-capture sidecar
also subscribes to drive event-triggered `/usage` snapshots.

QoS 1, retain=false. Events are point-in-time signals.

## Namespace Coexistence

The Mosquitto broker at 192.168.86.12 also serves:

- `surveillance/#` — ESP32 camera node telemetry
- `frigate/#` — NVR events
- `homeassistant/#` — Home Assistant state (if/when configured)

Saga owns `dvergr/#` exclusively. Do not publish to or subscribe from
the other prefixes inside Saga components.

## Filesystem marker contracts (non-MQTT transport)

Some ratatoskr notifications use the filesystem instead of (or
alongside) MQTT. These are documented here because they follow the
same producer/consumer contract pattern and future ratatoskr nudges
should use them.

### Verdict markers (`incoming-verdicts/`)

- **Directory:** `/workspace/odin/incoming-verdicts/`
- **Processed archive:** `/workspace/odin/incoming-verdicts/processed/`
- **Producer:** `ratatoskr.py` — writes a marker whenever a new file
  appears in `/workspace/mimir/verdicts/` (same trigger as the
  `tmux send-keys` nudge to Odin's pane)
- **Consumer:** Odin — scans the directory at end-of-turn and idle
  prompt; reads the referenced verdict; moves the marker to
  `processed/` after acting on it

**Marker payload** (JSON, one file per verdict):

```json
{
  "ts": "2026-04-17T02:29:00+00:00",
  "verdict_path": "/workspace/mimir/verdicts/decomposition-saga-spec-dev.md",
  "review_type": "decomposition",
  "verdict_name": "decomposition-saga-spec-dev"
}
```

- `ts` — ISO-8601 UTC, when ratatoskr wrote the marker
- `verdict_path` — absolute path to the Mimir verdict file
- `review_type` — inferred from filename prefix: `decomposition`,
  `prd`, `patch_review`, `guidance`, or `unknown`
- `verdict_name` — stem of the verdict filename (no extension)

**Why this exists:** `tmux send-keys` is silently dropped when
Claude Code is mid-tool-execution (Edit, Write, Bash). The marker
file persists on disk regardless of Odin's pane state, guaranteeing
the verdict is surfaced on the next scan. Send-keys is retained as
an idempotent fast-path for the idle-pane case.

**Dedupe:** ratatoskr skips writing the marker if a file with the
same name already exists in `incoming-verdicts/`. This prevents
double-writes from inotify re-fires or ratatoskr restarts.

**Extending the pattern:** future ratatoskr nudges (Eir PR-merged
events, plateau alerts, lifecycle milestones) can use the same directory
convention: write a JSON marker, let the consumer scan at idle,
move to `processed/` after handling. The send-keys path stays as
backup.
