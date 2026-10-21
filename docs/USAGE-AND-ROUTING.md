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
governed by the ADR-031 quota policy below, not by a USD cap. When no budget is
requested, Odin passes no `--max-budget-usd` to Claude Code and records the
budget as `limit_enforcement.budget: not_requested`; the harness's USD figure
(`cost_usd`, an API-list-rate estimate) is still reported for comparison but
is not enforced. A supplied `budget_usd` is passed as the harness option, as
before (ODIN-ADR-027, 2026-10-21 amendment).

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
added to their children. Claude's force setting has exceptions, including
forked agents and inherited skill models, and does not override all provider
fallbacks. See [native subagent controls](https://code.claude.com/docs/en/sub-agents#run-every-subagent-on-one-model).

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

For a bounded authorized diagnostic or repair, call `odin_intervention_begin`
with a purpose, `ttl_seconds` (1–300), and 1–8 `calls`, each containing `tool`
and exact `input`. Keep Bash `command` and `timeout` identical when invoking
the native tool; its description is ignored. Do not include secrets or request
background execution or a sandbox override. The returned intervention ID is
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
python -m odin.usage_statusline --output /private/telemetry/fable-status.json \
  --session-id NATIVE_UUID --project PROJECT_ULID
```

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
      "session_id": "SESSION_UUID",
      "agent_id": "executive",
      "account_id": "operator-chosen-account-label"
    }
  ]
}
```

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
