# Usage, orchestration and context experiment

ODIN-ADR-031 adds an opt-in local experiment. It does not activate changes in an
already running Fable session. Existing loops retain their objective and round bound. ADR-033 adds an explicit
operator transition for an existing paused loop; it is never implicit. The first rollout is synthetic verification,
then one observed native cycle, then comparison of quality and usage before
changing defaults. Opus/Haiku are requested routing choices, not a claim of
measured superiority or guaranteed savings.

## Accountable delegation

For a **new** `development-start` request, add:

```json
"delegation_profile": {
  "harness": "claude-code",
  "model": "opus",
  "subagent_model": "haiku",
  "subagent_model_force": true
}
```

This is a property of the existing request object, alongside project, native
executive session UUID, goal and bounds. It does not automatically change an active loop; see the explicit paused-loop
transition below.
Fable claims an offered stage, creates or resumes a separate
`odin_delegation_session` matching that profile, then calls `odin_loop_delegate`
with loop/stage IDs, the **Odin** `orchestrator_session_id`, native harness limits
and a stable operation ID. The service creates the stage's commitment,
assignment and queued turn atomically. Retries do not create another assignment.

`limits.iterations` is required; `limits.budget_usd` is optional. Admission is
governed by the ADR-031 usage policy below when the operator configures one
(the default `observe` mode holds nothing), not by a USD cap. When no budget is
requested, Odin passes no `--max-budget-usd` to Claude Code and records the
budget as `limit_enforcement.budget: not_requested`. The harness's own USD
figure (`cost_usd`, which the operator treats as an API-list-rate estimate, not
a subscription charge), token usage and model usage are still recorded exactly
as reported; unreported cost stays unknown. None of these is enforced. A
supplied `budget_usd` is passed as the harness option, as before, and can stop
the turn. The session-level `budget_usd` given to `odin_delegation_session` is
informational only: it is never passed to a harness or enforced, and a session
opened before this change may still show `0` (ODIN-ADR-027, 2026-10-21
amendment, which now states this; W0 review-8ba8918 finding 1).

The orchestrator receives the complete fixed stage prompt and instructions to
delegate independent bounded tasks to native subagents, integrate, test, obtain
review and return concise evidence. Fable reads the result, sends follow-ups
on the same assignment when needed, and records `odin_delegation_close`
acceptance with evidence for criterion `stage`. `odin_loop_ready` checks a
successful return from a separate native session and the accepted assignment.
The service adds the binding to the evidence packet. Canonical verification
and required independent review are not replaced by executive acceptance.

This check enforces accountable routing. It does not prevent Fable's native
tools from editing files, prove that subagents were used, or establish which
models ran. Those claims require native observations. The profile is fixed once selected, either at
loop creation or the one-time paused-loop transition; a cancelled stage assignment requires operator reconciliation,
not a replacement operation ID that silently repeats uncertain work.

Session creation supports `subagent_model`, `subagent_model_force` and
`auto_compact_window_tokens`. Defaults can be supplied to `delegation-configure`
with `--claude-subagent-model`, `--claude-subagent-model-force` and
`--auto-compact-window-tokens`. Top-level `--claude-model` chooses the
orchestrator. Session status preserves requested settings across resume;
result summaries retain observed `model_usage`, `observed_model` and
`usage_scope` when emitted by the harness. Inclusive aggregate totals are not
added to their children. When force is requested, Odin also disables the
fork agent (`CLAUDE_CODE_FORK_SUBAGENT=0`, which would otherwise inherit the
parent model) and sets `CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL` to the same
model. Inherited skill models and provider fallbacks remain exceptions. Live
harness behaviour is unverified, so session views report the status field
`fork_subagent: "disabled_requested_not_verified"`. See
[native subagent controls](https://code.claude.com/docs/en/sub-agents#run-every-subagent-on-one-model).

Session creation also supports `disallowed_tools`, a list of plain tool names
passed to every claude-code turn as `--disallowedTools`. The harness default is
`default_disallowed_tools`, set with `delegation-configure
--claude-disallowed-tools Agent,Task`. It is off unless configured; the session
value wins, and an empty list turns it off for that session. Codex sessions
refuse it. ODIN-ADR-031's 2026-10-22 amendment records why the operator denies
`Agent` (and its legacy name `Task`) to delegated sessions.

Delegation failures are surfaced, not left for the executive to find. When a
turn ends `failed` (reported as `turn_timed_out` when the runner hit the
wall-clock deadline, otherwise `turn_failed`), `interrupted` or `lost`, or when
any terminal turn leaves the assignment's commitment open with no turn running
(`commitment_open_after_terminal_turn`), the service writes one notice to the
`delegation_notices` table in the same transaction as the turn result. The
notice ID is derived from the turn ID and terminal state, and the insert ignores
conflicts, so reconciling or restarting never duplicates it and a restart never
drops it. `odin_delegation_status` shows the live `attention` reasons and
`pending_notices` for each open assignment, in both the compact and the detail
view, and a top-level `attention` summary. A closed assignment stays in the
compact view while it still has a pending notice.

In development-loop bridge mode, `odin_loop_inbox` offers pending delegation
notices as `kind: notice` with no loop or stage. They are redelivered until
acknowledged with `odin_loop_ack`, are never claimable, grant no authority and
point at `odin_delegation_status`. Acknowledgement records attribution, not
operator approval or acceptance. A notice whose only reason is the open
commitment resolves itself when the executive queues a follow-up or closes the
assignment, so an accepted return leaves nothing pending. A failure notice stays
pending until acknowledged, even after the assignment is cancelled. Without
development-loop mode the bridge has no inbox or acknowledgement tool, and only
the status flags apply. Every returned turn, including a development-loop
stage return, carries an open-commitment notice until the executive accepts or
closes the assignment or queues a follow-up. Failure notices are offered before
open-commitment reminders, oldest first within each group, and they only fill
the inbox slots that assignments and loop notices leave within the bridge's
bound of 16. A queued turn stranded by session retirement is recorded as
`interrupted` and notifies like any other; a queued turn cancelled by
`odin_delegation_close` does not, because the executive made that decision.
Notices are addressed to the project, not a specific executive session, so
acknowledgement is project-scoped. The failure excerpt is labelled as
untrusted harness output. Delegation notices have no separate contract schema;
the bridge validates the inbox item shape.

### Workstream sessions and lineage concurrency (ODIN-ADR-036, phase 1)

A delegation session can be opened with an optional `workstream` label and a
`role` of `integration_owner` or `workstream`. A label alone makes a workstream
session. A session declaring neither is legacy and acts as the integration
owner. Refusals are fixed codes: `workstream_label_required`,
`workstream_already_has_active_session`, `project_already_has_integration_owner`,
`project_already_has_active_session` (legacy sessions meeting each other only)
and `workspace_in_use_by_active_session`. Resume applies the same checks.
Only the integration owner sets the project's interface decision owner. A
workstream session works on its own branch and worktree, never fast-forwards
the canonical checkout, and returns a merge-ready head with receipts; the
executive assigns integration to the integration owner. Odin cannot enforce
these git rules. They are stated in the session briefing.

`max_concurrent_turns_per_lineage` (integer 1–8, default 1, set with
`delegation-configure --max-concurrent-turns-per-lineage`) bounds the running
turns per credential lineage across sessions. Each session still runs one turn
at a time. At the default, Odin runs one `claude -p` turn at a time on the
dedicated login. Several orchestrator sessions therefore interleave their turns;
they are not parallel execution. A value above 1 is refused by
`delegation-configure` and ignored by `launch_pending` unless `lineage_policy`
is `shared_accepted`, because the runner's exclusive lineage lease would refuse
the concurrent turn. The pilot runs 8 by operator decision since 2026-10-22
(ODIN-ADR-036 amendment), without the isolated concurrent-turn credential test
(X-12, D24.4a stay open); set it back to 1 if a credential refresh race appears.
Status shows the configured and effective values in `project_aggregate`.

Claude Code print results report cost as an inclusive figure for the resumed
native session. Views therefore use per-turn deltas: each turn's figure minus
the previous inclusive figure of that native session. The first turn of a native
session counts as its own delta, and a drop below the previous figure counts as
its own figure. An unknown figure stays unknown and does not move the baseline,
so the next known turn's delta also carries the unknown turn's share; the total
is unaffected. A session's cost is the sum of its
deltas. The project aggregate in status (`project_aggregate`) sums the sessions
and is labelled `attributed_not_verified`. Raw inclusive figures stay in each
turn result for audit. Codex per-turn costs are summed as reported.

## Executive model

The executive's requested model is stored in its manifest and passed as
`--model` at every launch and resume. To change it, stage the new model and
resume the same executive once its current work has drained:

```bash
python -m odin --state "$ODIN_PILOT_STATE" executive-configure-model \
  --model claude-opus-5-5
```

The native session ID, login and conversation are kept. Staging the configured
model again cancels the change, and it composes with the other staged settings.
`executive-status` reports `configured_model` and `pending_model`. The running
session keeps its model until it exits, and the model actually used remains
`requested_not_verified`. Nothing changes the model automatically.

## Executive role and existing-loop transition

ADR-033 separates the executive's context from project implementation. This is
an explicit operator choice, composed with the existing v3 development profile.
Stage the role, then resume the same executive once after its current work has
drained:

```bash
python -m odin --state "$ODIN_PILOT_STATE" executive-configure-execution-role \
  --implementation-mode delegated
```

With ADR-034, explicitly staging this role also enables bounded intervention
support. After the one activation resume, Bash, Write, Edit and NotebookEdit
are visible but gated by native hooks. PowerShell, Agent, Task, Monitor,
Workflow, EnterWorktree and ExitWorktree remain removed from the executive.
Native reads, search/discovery, peer coordination and Odin MCP stay available.
Older manifests without intervention enablement retain the former deny list.
The profile preserves session/login identity and pending loop, peer and
compaction settings. `executive-status` reports configured and pending modes
and intervention configuration. `--implementation-mode direct` stages rollback
to the prior development role; worker permissions are independent.

Read-only allowlisted Bash and operator-registered scripts need no permit;
see [executive admission paths](EXECUTIVE-PILOT.md#executive-admission-paths).
For any other bounded authorized diagnostic or repair, call `odin_intervention_begin`
with a purpose, `ttl_seconds` (1–3600), and 1–32 `calls`, each containing `tool`
and exact `input`, optionally `uses` (1–20) to repeat an identical call and,
for Bash, `background: true` to bind background execution. Keep Bash `command`
and `timeout` identical when invoking the native tool; its description is
ignored. A background permit closes at launch and Odin does not observe its
outcome. Do not include secrets or request a sandbox override. The returned intervention ID is
the begin operation ID. No orchestrator turn may be queued or running. The
hook consumes each exact-input permit once; unmatched calls are denied with
instructions to delegate or request a scoped permit. Close unused permits
with `odin_intervention_end` before delegating again. Completed permits close
automatically; expiry forbids new admissions but never stops an existing
process. A missing completion remains visible as `in_flight_unknown` and
blocks new delegation pending reconciliation. Never retry an uncertain native
execution merely because a hook response was lost. A trusted local operator can
resolve a missing completion through `odin command --request <command.json>`:
use action `intervention_reconcile` and payload `project`, `session_id`,
`intervention_id`, and a bounded `observation` explaining the process/effect
inspection. This closes unused permits and marks admitted calls `reconciled`,
not successful. Executive requests cannot use this operator-only action;
its observation is attributed and does not attest process termination.

This local role policy is not OS isolation or universal plugin enforcement.
The executive must not use alternate tools to bypass it. Exact Bash arguments
do not enforce filesystem containment of subprocess effects. A native hook
completion is not proof that all descendants exited. Observe the live manifest
and actual hook behavior before claiming activation. Hook settings use
`onFailure: block` and require Claude Code 2.1.295 or newer; see the
[native hook reference](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails).

Fable assigns the objective, current revision, constraints, acceptance criteria,
remaining work and exact evidence references to a separate project orchestrator.
Keep a resumable orchestrator for related work; send changes on follow-ups.
Detailed source exploration, edits, integration, tests and worker progress stay
there. The executive inspects concise results and selected evidence, records
acceptance or an unresolved decision, and submits its stage. Raw worker
transcripts and full logs should not be copied into each executive update.

To enable the stage completion requirement on an existing loop, pause it using
`development-control --control pause` and let native work drain. Preserve a
checkpoint and unfinished work. Prepare a private JSON request with these
fields, substituting actual identities and the newly observed revision:

```json
{
  "action": "configure_delegation",
  "project": "PROJECT_ULID",
  "loop_id": "LOOP_ULID",
  "stage_id": "CURRENT_STAGE_ULID",
  "session_id": "EXISTING_FABLE_UUID",
  "expected_revision": 30,
  "delegation_profile": {
    "harness": "claude-code",
    "model": "opus",
    "subagent_model": "haiku",
    "subagent_model_force": true
  }
}
```

```bash
python -m odin --state "$ODIN_PILOT_STATE" development-control \
  --control configure_delegation --request /private/routing-request.json \
  --operation-id STABLE_OPERATION_ULID
```

The service rejects stale/mismatched identity, an existing profile or stage
binding, ready/captured evidence, unsupported paused states and active
service-recorded evaluator/delegation work. It does not infer native quiescence
from those records. The supervisor must observe the executive's outstanding
tools and children finishing before restarting the service/bridge or executive.
After activation, resume the existing loop and have Fable delegate the remaining
stage through `odin_loop_delegate`; do not recreate the loop or reset its bound.
Existing completed work remains attributed to its actual author. A resumed
claimed stage is not a new claim, and a successful transition is not completion.

Native tools are checked through launch construction and capability probing;
`tests/test_executive_role.py` covers staged role behavior. Stage routing,
operator authorization, quiescent-state refusals and replay are checked in
`tests/test_stage_delegation.py`; CLI identity preservation is covered in
`tests/test_routing_cli.py`. Transcript/model evidence establishes actual child
execution, which the service's accepted-return gate alone does not establish.

## Metadata accounting and coverage

`usage-collect` reads an explicitly named, bounded native source and submits
metadata through the service's operator command path. It does not scan the
home directory, persist message content, install hooks or silently enable
tracing. Example (substitute real source and identity values):

```bash
python -m odin --state "$ODIN_PILOT_STATE" usage-collect \
  --project PROJECT_ULID --usage-provider claude \
  --native-session NATIVE_UUID --agent-id executive \
  --source-file /absolute/private/session.jsonl --max-bytes 8388608
python -m odin --state "$ODIN_PILOT_STATE" usage-status --project PROJECT_ULID
```

Collect each known subagent source with its own agent identity. Loop/stage
attribution is optional (`--loop`, `--stage`) and reported, not inferred from
the entire executive transcript. Do not attribute a multi-stage transcript to
one stage. `usage-import --request` accepts already normalized metadata in
batches of at most 128 observations, plus a source ID and optional coverage.
Imports are operator scoped; models can inspect `odin_usage_status` but cannot
use an MCP tool to author telemetry or policy. Same-user native development
access remains trusted, so this is provenance rather than tamper-proof metering.

Claude uncached input, cache reads, cache creation and output remain separate.
Repeated request blocks revise one identity; inclusive aggregates are retained
but excluded from additive request totals. Codex input already includes cached
input. Its per-turn collector does not silently reinterpret cumulative session
reports; callers with confirmed cumulative semantics must use the explicit
collector option (CLI `--usage-semantics session_cumulative`). Unknown counters, absent identities, malformed/truncated
sources and partial coverage stay visible. Registered-source coverage is not
proof that every executive, worker or evaluator source has been discovered.

`--usage-provider claude-status` accepts an explicit native status-line JSON
sample; the source file modification time is retained as the sample time, so
re-importing an old snapshot does not refresh it. Supply a nonsecret `--account-id` to identify its quota scope. Status
samples are not requests. Native quota percentages are account-level samples,
separate from request tokens and API-price estimates. Neither prices nor
subscription quota can be inferred from token totals. See
[native monitoring](https://code.claude.com/docs/en/monitoring-usage) and
[status-line fields](https://code.claude.com/docs/en/statusline).

The incremental watcher below continuously collects explicit session sources.
Live activation must still establish each executive, orchestrator, child and
evaluator source; an empty ledger remains missing evidence. Discovery is bounded
to configured paths, and continuous coverage remains explicitly incomplete.

For native context and account quota, an opt-in status-line command is available:

```bash
python -m odin.usage_statusline --output /private/telemetry/executive-status.json \
  --executive-state "$ODIN_PILOT_STATE" --project PROJECT_ULID
```

`--executive-state` reads the executive's current native UUID from its manifest
on every render, so the capture follows `executive-new-session`. A fixed
`--session-id NATIVE_UUID` is still accepted, but it stops capturing after a
rotation.

Configure this command in the dedicated Claude profile's `statusLine` setting,
preserving any existing display configuration. It reads bounded native stdin,
requires the configured native UUID, and retains only context counters and the
five-hour/seven-day quota windows in a schema-validated private snapshot. It
never stores working paths, message contents or credentials. Identical rerenders
leave the snapshot mtime unchanged rather than refreshing cached evidence.
The watcher imports this file with its configured account label; native epoch
reset times are normalized to UTC timestamps. The helper does not query the
provider or guarantee that native cached quota is current.

## Admission controls

`usage-configure --request /absolute/private/policy.json` accepts:

```json
{
  "project": "PROJECT_ULID",
  "policy": {
    "mode": "hold",
    "missing_telemetry": "hold",
    "account_id": "operator-chosen-account-label",
    "limits": {
      "max_input_tokens": 2000000,
      "max_output_tokens": 100000,
      "max_context_tokens": 180000,
      "max_five_hour_used_percentage": 85,
      "max_sample_age_seconds": 300
    }
  }
}
```

Values above are an illustrative experiment configuration, not recommended
defaults. Omitted limits are disabled. Start with `mode: observe` to see what
would hold. Request-count and seven-day quota thresholds are also supported.
Token/request limits are cumulative for the project, not reset at each stage.
Known lower bounds can breach a limit even when coverage is incomplete.
Missing, stale, wrong-account or wrong-session telemetry cannot satisfy a
configured required observation. Context thresholds require that native
session's sample; evaluator sessions may have no such sample and therefore
hold under a strict missing-telemetry policy.

The service checks before offering/claiming an executive stage and immediately
before launching queued evaluator or delegated work. Holds leave the existing
stage, job and turn identities pending. New telemetry or an explicit operator
policy change lets the same work be admitted; it does not reset loop bounds.
Inspect `usage-status` and `development-status` for reasons. An entirely
unconfigured project keeps legacy behavior without adding idle poll history.

These controls do **not** reserve provider quota, interrupt already-running
turns, enforce an in-flight native spending ceiling or provide Saga guarantees.
Two admitted processes can consume usage before the next sample. There is no
automatic model downshift or change to required review.

### Account limit probes, labels and admission bands (W3a)

`usage_watch` can run two stateless limit probes. Each reported limit becomes a
`kind: "limit"` usage sample with a label, `utilization_percent`, `resets_at`,
`observed_at`, `source: "probe"` and `status`. Probe samples carry no tokens,
prompts or account identifiers.

- `claude.five_hour`, `claude.weekly` and `claude.weekly.<model>` (for example
  `claude.weekly.fable`) come from the Claude OAuth usage endpoint
  `GET https://api.anthropic.com/api/oauth/usage` with `Authorization: Bearer`
  and `anthropic-beta: oauth-2025-04-20`. The probe reads
  `claudeAiOauth.accessToken` from `.credentials.json` inside the configured
  `claude_config_dir` at call time only. It never defaults to a home directory,
  and the token is never logged, stored in a sample, placed in an exception or
  returned. The transport is injected; tests use recorded fixture responses and
  make no network calls.
- **Endpoint and shape are unverified and undocumented.** Nothing in this
  repository's research or fixtures records them. The shape used is the commonly
  reported one: top-level `five_hour`, `seven_day` and `seven_day_<model>` objects,
  each with `utilization` (a percentage from 0 to 100) and `resets_at`. Live
  acceptance against the real endpoint is still required.
- `codex.five_hour` (300-minute window) and `codex.weekly` (10080-minute window)
  come from `rate_limits` objects in the newest JSONL session under
  `CODEX_HOME/sessions`, read with the same bounded reader as the Codex usage
  collector. The existing Codex collector only reads token-usage rows, so the
  rate-limit shape is also unverified. `CODEX_HOME` is never defaulted to a
  real home directory.
- **Unavailable semantics.** A missing or unreadable configuration or
  credential, an HTTP error, malformed JSON, out-of-range values, or no
  recognised limit produces one `status: "unavailable"` sample under the label
  `claude.probe` or `codex.probe`, with a short fixed reason and null
  utilization. Unavailable samples never contribute a band. The existing
  `claude_status` quota samples and their cursors are unchanged.
- The watcher config accepts an optional `limit_probes` object with
  `claude_config_dir`, `codex_home` and `interval_seconds` (default 300). Each
  probe runs only when its own key is configured. Probe
  samples are sent through the same `usage_import` command path without byte
  cursors or coverage records.

**Admission bands are not hard ceilings.** Each known label has a ceiling. Its
bands are `wind_down` at ceiling minus 10, `ordinary_stop` at ceiling minus 5
and `handoff_only` at the ceiling. Below the first band the value is `clear`.
These bands only describe Odin's own admission decisions. They do not stop a
running native session, and they do not reflect or enforce the provider's
limits.

| Label | Ceiling | wind_down | ordinary_stop | handoff_only |
| --- | --- | --- | --- | --- |
| `claude.five_hour` | 95 | 85 | 90 | 95 |
| `claude.weekly` | 90 | 80 | 85 | 90 |
| `claude.weekly.fable` | 95 | 85 | 90 | 95 |
| `codex.five_hour` | 95 | 85 | 90 | 95 |
| `codex.weekly` | 90 | 80 | 85 | 90 |

Labels not in this table, such as `claude.weekly.opus`, have no band. They keep
the legacy `max_*_used_percentage` policy behaviour exactly. The default
`observe` mode still holds nothing. Each policy decision reports the latest
available sample and band per known label in `limit_bands`, and `usage-status`
returns that decision. Band membership does not change the `hold` decision.

**Band changes are events.** When a newly imported sample moves a label to a
different band, the service records `usage.limit_band_changed` in history and a
durable `limit_band` notice for the executive. Probe samples count under their
label. Status-line quota samples count as `claude.five_hour` and
`claude.weekly`. A first observation in `clear` records the band without a
notice, and an older or simultaneous sample never moves it. A newer notice for
the same label supersedes a pending older one. The executive receives the
notice through its channel, like a delegation notice, and acknowledges it with
`odin_loop_ack`; acknowledgement is model-attributed and grants nothing. When
`claude.weekly.fable` reaches `ordinary_stop` or `handoff_only`, the notice
suggests that the operator stage `executive-configure-model --model
claude-opus-5-5`. The notice is the only effect: no model is switched and no
work is held. The live pilot shows Fable-specific figures only once the limit
probes are configured; the status line reports account-wide windows.

## Context continuity and compaction

`odin_context_checkpoint` records a bounded, attributed continuation note
before compaction. The note contains a monotonically increasing revision,
branch/worktree, artifact references with hashes, outstanding obligations,
pending reviews, stable operation IDs, next action and short summary. The
schema and 16 KiB bound are enforced. Optional loop/stage identities are
checked against service records. The bridge supplies Fable's native UUID.
`odin_context_status` and `odin_resume` expose the retained note; commitments,
assignments and stage state remain authoritative. A note never completes work
or independently proves that an artifact exists or matches its supplied hash.
With `predecessor: true`, `odin_context_status` also returns the latest
checkpoint of the session that most recently handed a loop to the bound
session, per the recorded `development_loop.handed_over` history events
(ODIN-ADR-038). The read is on request only, never rewrites the checkpoint,
and labels it `predecessor_checkpoint`: an attributed claim to reconcile with
loop status, commitments and git.

Stage native earlier compaction without changing the executive UUID:

```bash
python -m odin --state "$ODIN_PILOT_STATE" executive-configure-context \
  --auto-compact-window-tokens 200000
```

This stages a requested window for the next start/resume. A one-launch
override is available on `executive-start --resume-session`. Status shows
configured and pending values, and the launch receipt records the request.
Native Claude chooses the actual compaction timing and caps the window at the
model context limit. The checkpoint tool does not itself invoke compaction.
See [native context-window configuration](https://code.claude.com/docs/en/model-config#set-the-auto-compact-window).

## Activation and comparison

Reconcile the current unfinished stage before integrating this branch. Preserve
its uncommitted work and fixed loop objective; do not restart uncertain native
work as a new stage. Deploy the reviewed service and bridge together, then
resume the same Fable UUID to refresh the tool manifest. Use a new explicitly
configured loop or the ADR-033 paused-loop transition for delegation. Verify separately: actual
Opus orchestrator, actual Haiku child observations, complete collector coverage,
no duplicate requests, quota freshness, hold/release with unchanged identities,
checkpoint recovery, and final accepted evidence. Compare usage **and** quality
against the baseline before selecting defaults. Synthetic tests establish
controller behavior, not completion of that live experiment.

## Incremental native usage watch

`usage-watch` is an opt-in, separate local process. It discovers transcripts only
under the exact files or directories named in a private, schema-validated
configuration. It sends normalized metadata through the operator service socket;
it never opens the service database or stores message content. The service must
be running. A private cursor SQLite file and exclusive lock allow one watcher
for that cursor. Pending metadata batches are retained before sending and replayed
with the same operation ID after an uncertain reply; byte cursors advance only
after the service acknowledges them. The private cursor also retains per-request
metadata high-water marks, so older samples replayed after transcript rotation
cannot reduce already observed counters. A sample that mixes increased and
decreased counters is treated as invalid coverage while other requests continue.

```json
{
  "schema_version": 1,
  "project_id": "PROJECT_ULID",
  "cursor_path": "/private/odin-usage-watch/cursor.sqlite3",
  "poll_seconds": 15,
  "max_chunk_bytes": 262144,
  "max_files": 128,
  "sources": [
    {
      "provider": "claude",
      "session_file": "/explicit/claude/project/SESSION_UUID.jsonl",
      "session_id": "SESSION_UUID",
      "agent_id": "executive",
      "discover_children": true
    }
  ],
  "status_files": [
    {
      "path": "/explicit/private/status.json",
      "executive_state": "/explicit/odin/pilot/state",
      "agent_id": "executive",
      "account_id": "operator-chosen-account-label"
    }
  ]
}
```

A status file names either a fixed `session_id` or `executive_state`, which
resolves the executive's current native UUID at each poll. An unreadable
manifest counts the file as `unavailable`. Changing an existing entry changes
its cursor identity, so point the new entry at a new status file path. For
token usage across rotations, a claude source may name `executive_state` with
`agent_id` (and optional `discover_children`) instead of `session_file` and
`session_id`: each poll resolves the manifest's current native session ID and
reads `<config_dir>/projects/<launch cwd encoded as a Claude project
directory>/<session>.jsonl`, so rotation moves to a new path with its own
cursor and the old file is no longer polled. Alternatively, a `sessions_dir`
source with `discover_sessions` picks up new session files in one directory.

For workspace discovery, a claude source may instead name `workspaces_root`,
`claude_config_dir` and `discover_sessions: true` (with optional
`discover_children`); `loop_id` and `stage_id` are not accepted. Each
poll lists the directories directly under `workspaces_root` — non-directories
and symlinks are skipped and the order is sorted — and resolves each
workspace's transcript directory as `<claude_config_dir>/projects/<absolute
workspace path encoded as a Claude project directory>`. The encoding replaces
every character outside `[A-Za-z0-9]` in the path with `-`; the rule was
verified against real Claude project directory names, and encodings longer
than 200 characters are unsupported — such a workspace is skipped rather than
failing the whole source. A workspace whose project directory does not exist
yet is skipped silently, and a workspace added later is discovered at the next
poll with no configuration change. Each existing project directory is then read
exactly like a `sessions_dir` source: every direct `*.jsonl` is a session named
by its file stem, plus `<stem>/subagents` children when enabled. Its agent
identity is `workstream:<workspace directory name>` truncated to the usage
contract's 256-character bound, giving each workspace project-only usage
attribution. On rotation the new native session is a new transcript path with
its own byte cursor; under `executive_state` the old path is no longer polled,
while under `workspaces_root` or `sessions_dir` the rotated file remains
listed but simply reports `idle` once it stops growing.

Run one poll with `python -m odin --state "$ODIN_PILOT_STATE" usage-watch
--request /private/watch-config.json --once`; omit `--once` to poll at the
configured interval. `session_file` watches that exact file and, when enabled,
only its sibling `<session-file-stem>/subagents/*.jsonl`. Alternatively,
`sessions_dir` plus `discover_sessions: true` watches direct `*.jsonl` files
and their exact sibling subagent directories. This directory mode is explicit
permission to discover future native sessions in that one directory; it gives
them project-only usage attribution. File counts, directory depth, read bytes,
source JSON size, import batch size and poll cadence are bounded. Missing files
remain unavailable and may appear in a later poll; one unavailable or oversized
directory does not stop other configured sources. Existing cursor and lock files
must be owner-only regular files. A status snapshot must carry the configured
native session ID. A bounded committed-prefix fingerprint detects same-inode
rewrites that grow beyond the previous byte cursor. Codex sources may declare
`usage_semantics: "session_cumulative"` when confirmed for that source.

For the development evaluator's ephemeral Codex jobs, configure an additional
source with `{"provider":"codex","spool_dir":"/explicit/development-evaluator",
"discover_jobs":true,"usage_semantics":"session_cumulative"}`. This scans only
direct job directories for `stdout.log`; it does not read prompt, result, or
last-message files. The watcher persists `thread.started` identity across
polls and uses that native thread ID for later usage. Usage before an observed
thread ID is marked unidentified rather than attributed to the job directory.

A discovered child retains its own reported native session ID. It receives
project-only attribution, while its source records the configured parent
directory and its agent identity includes the child filename and native child
metadata. Rows without a native child session ID are omitted and counted as
unidentified coverage. This is provenance from local transcripts, not proof of
which model executed.
Repeated native messages, a lost socket reply, rotation and truncation cannot
advance the cursor before an acknowledged import. Continuous sources always
report incomplete coverage because more lines or undiscovered agents may appear.
Oversized or malformed lines are skipped with an error count; they do not become
zero usage. Status snapshots use the explicitly named file's modification time
as the sample time, so a copied or touched file must be treated as a new local
observation rather than an attested provider timestamp.

### Migrating an existing watch.json

Replace the fixed executive entry

```json
{"provider":"claude","session_file":"/explicit/claude/project/SESSION_UUID.jsonl",
 "session_id":"SESSION_UUID","agent_id":"executive","discover_children":true}
```

with an `executive_state` entry that follows rotation:

```json
{"provider":"claude","executive_state":"/explicit/odin/pilot/state",
 "agent_id":"executive","discover_children":true}
```

and replace hand-written per-workstream `session_file` or `sessions_dir`
entries with a single discovery entry:

```json
{"provider":"claude","workspaces_root":"/explicit/odin/workspaces",
 "claude_config_dir":"/explicit/claude/config",
 "discover_sessions":true,"discover_children":true}
```

then restart the watcher. Cursor rows are keyed by transcript path, so the
existing private cursor file can be retained: an `executive_state` entry that
resolves to the same native session keeps the same cursor identity and byte
offset, and each later rotation or newly discovered workspace session simply
begins a new path. The live `watch.json` migration is documented here and is
not performed by this change.

## Compact executive responses and checkpoint diagnostics

Executive delegation status and loop status/claim/ready responses default to
compact projections, bounded to 16 KiB. Historical details have explicit
omission counts. An overflow is marked `incomplete_for_action`; it must not be
read as evidence that omitted work is complete. Use `view: "detail"` with a
scoped session/assignment/loop ID when needed. Write detail retries retain the
same operation ID and arguments; the display option does not change the
canonical command. Operator CLI responses and stored records are unaffected.

The checkpoint tool advertises every required caller-supplied field. Its
schema version, project and native session identity are supplied by the bridge.
Invalid arguments return a field-specific `not dispatched` error. Transport
uncertainty still requires reconciliation or an identical retry with the same
operation ID. Checkpoints are attributed handoffs; native auto compaction is
separate and is not the planned OptChat/UniiChat memory compactor.

A deterministic refusal reaches the executive as
`Executive service refused the request: <code>.`, never as an unknown write
outcome. An identical retry is refused again, so the executive must change
something first. Each code is fixed text with no input, path or foreign record:

| Code | Meaning |
|---|---|
| `operation_id_reused` | The operation ID was already used with other arguments; any write tool |
| `loop_owned_by_other_session` | The loop belongs to another native session in this project, as after `executive-new-session` |
| `notice_owned_by_other_session` | The same, for a loop notice |
| `checkpoint_loop_owned_by_other_session` | The checkpoint names a loop owned by another native session; omit `loop_id` and `stage_id` |
| `checkpoint_stage_owned_by_other_session` | The same, for the named stage |
| `checkpoint_loop_unavailable` | The loop is unknown, or belongs to another project; the two are indistinguishable |
| `checkpoint_stage_unavailable` | The stage is unknown or not part of the named loop |
| `checkpoint_stage_requires_loop` | A `stage_id` was given without `loop_id` |
| `checkpoint_revision_not_advanced` | The revision does not exceed this session's latest checkpoint |
| `checkpoint_binding_mismatch`, `checkpoint_session_mismatch` | A field differs from the bridge's trusted binding |
| `no_recorded_predecessor` | `odin_context_status` with `predecessor: true`, but no recorded `development_loop.handed_over` event names the calling session as successor |

A loop in another project still returns the generic `access denied` read
error. A rotated executive session takes over its predecessor's loop only
through the operator's `loop_handover` transition (ODIN-ADR-038).
