# Independent development evaluator and feedback loop

Status: implementation under
[ODIN-ADR-028](DECISIONS.md#odin-adr-028--independent-development-evaluator-and-feedback-loop),
2026-10-20. Configuration and synthetic tests do not establish a working
live channel, completion hook or autonomous multi-round conversation.

The development evaluator designs the next test for Odin, examines the
executive's response and evidence, and chooses the next development stage.
The test can concern functionality, operator experience, reliability,
recovery, or implementation quality. Code review is one possible activity.
The existing Fable executive performs the work using its authorized native
tools, subagents, code changes and tests, while the operator keeps the same
interactive Claude Code conversation and Remote Control access.

The development loop controller is ordinary service code. It records and
validates the exchanges, delivers work, captures completion, and enforces
pause/stop and finite rounds. Its role is to remove manual copying between
the executive and evaluator without hiding failures or turning model
judgment into new authority.

## Responsibilities

| Component | Responsibility | What its output establishes |
|---|---|---|
| Operator | Chooses objective, project, existing executive session, evaluator configuration and loop bounds; can pause or stop | The authorized development scope and controls |
| Development evaluator | Examines the supplied evidence independently of the executive's working conversation; designs a bounded next test or chooses completion/pause | An attributed evaluation and next-stage proposal within the configured scope |
| Development loop controller | Validates configuration/results, records round identity, schedules delivery and evaluation, handles duplicates/recovery and bounds | Durable local transition and delivery/capture observations |
| Fable executive | Performs the current round, delegates where useful, changes code and tests under ADR-026, and produces a final response with evidence | Work and an executive-attributed report; evidence quality still needs assessment |
| Mimir reviewer positions | Perform required review where the product's review rules require it | Their own required-review verdicts, not the development evaluator's assessment |

Independence means a distinct evaluator invocation with its own evidence
pack and recorded model/configuration. It does not establish separate OS
authority, independent credentials, or verified execution merely by giving
the role another name. The evaluator cannot grant a new permission, extend
the objective, satisfy Saga approval, or waive required Mimir review.
Its `complete` decision ends this development loop; it does not itself close
a canonical commitment, approve a patch, or create a Saga-verified result.

## Round flow

1. The operator configures a bounded objective and explicitly enables the
   loop for the existing native executive session.
2. The controller invokes the configured evaluator with the objective,
   current round state and available evidence. The evaluator returns a
   structured `continue`, `complete` or `needs_operator` decision.
3. A next test is durably recorded before the controller offers it through
   the executive's opt-in MCP channel. Transport observation and executive
   acknowledgement are distinct from successful execution.
4. Fable claims the stage through `odin_loop_claim`, performs the task with
   its normal development tools, records its
   evidence through `odin_loop_ready`, and includes the returned completion
   footer in its final response. The main completion hook captures that
   response for the active round automatically.
5. The controller validates correlation and records the return, then gives
   that evidence to the evaluator. The next stage proceeds automatically
   within the configured bounds. A missing, stale or ambiguous return does
   not become a completed round.

The channel is attached to the existing interactive Claude Code process.
The controller does not launch another Claude process using the executive's
credential lineage, send synthesized keystrokes, or replace Remote Control.
The evaluator runner uses its separately selected configuration; its
availability is a separate capability from the executive channel.
Unchanged inbox polling is a scoped transport read and creates no history
or receipt per poll. The controller records stage creation, claims,
completion and state transitions. Notification delivery is still distinct
from a successful claim and is not an authenticated operator command.

## Activation

Use the native development profile from the
[executive guide](EXECUTIVE-PILOT.md). Activation adds the channel and
completion hook to the next owned native start/resume. It does not silently
alter or interrupt a running session. Exit the native session once, then
resume the retained session ID with the loop transport enabled. Preserve
the dedicated Claude configuration and the existing runtime/lineage locks.

The native harness must accept the custom development channel and its
permissions. A configured MCP server can expose tools while its channel
notifications remain unavailable. Confirm an actual channel-delivered test
and correlated acknowledgement in the intended session; do not infer this
from a successful server connection or listed tool.

Channel transport is currently a Claude Code research-preview capability.
The supported custom-channel opt-in is
`--dangerously-load-development-channels server:odin`; availability can
also depend on organization policy. Its presence in launch configuration
does not prove that notifications reach the model.
[Claude Code channels](https://code.claude.com/docs/en/channels),
[channel reference](https://code.claude.com/docs/en/channels-reference).

Run these commands from the checkout with its pinned Python dependencies
installed and `PYTHONPATH` set to its `python` directory. Use the existing
private runtime state path; do not create a second executive state. Obtain
the project and native session UUID from `executive-status`.

```bash
export PYTHONPATH="$PWD/python"
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-status
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-enable-development-loop
```

This requires version 3 development access and the Odin MCP bridge. If
needed, first stage `executive-enable-development` as described in the
executive guide. The loop command stages configuration; it does not itself
start a loop or change the running native process.

Prepare a private evaluator configuration JSON outside the checkout. The
following example uses placeholders: substitute the installed native binary,
checkout, dedicated evaluator login directory and chosen model before
using it. The login must already be available to the chosen harness; this
configuration does not provision credentials.

```json
{
  "schema_version": 1,
  "enabled": true,
  "harness": "codex",
  "binary": "/absolute/path/to/codex",
  "workspace": "/absolute/path/to/odin",
  "config_dir": "/absolute/path/to/private-evaluator-login",
  "model": "CONFIGURED_MODEL",
  "effort": "high",
  "timeout_seconds": 900
}
```

The alternative harness is `claude-code`. Give that evaluator its own login
lineage; it must not share the running executive's dedicated Claude login.
The evaluator uses native read-only controls and an exclusive lineage lease.
These are local harness controls, not an OS isolation guarantee. Its timeout
bounds an evaluator invocation; it does not bound the entire loop or a native
executive turn.

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-configure \
  --request /absolute/private/path/evaluator-config.json
```

Configuration is written locally and loaded on the next service start.
Restart the service using the updated checkout and the existing project
binding. In one terminal:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" serve \
  --executive-project PROJECT_ULID
```

After exiting the existing native executive once, resume it in another
terminal and complete any native channel permission dialog:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start --resume-session
```

Create a private start JSON, substituting the same project and retained
native session UUID. The initial evidence object is optional. This example
requests three development rounds; the evaluator can finish earlier.

```json
{
  "project": "PROJECT_ULID",
  "session_id": "RETAINED_NATIVE_SESSION_UUID",
  "goal": "Exercise Odin's executive bridge and loop recovery against synthetic local state, fix identified Odin defects, and report exact test evidence.",
  "evidence_packet": {"source": "operator-provided development objective"},
  "max_rounds": 3,
  "no_progress_limit": 3
}
```

Start and inspect the loop through the running service:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-start \
  --request /absolute/private/path/development-start.json
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-status \
  --project PROJECT_ULID
```

Keep the returned loop ID. `development-status --loop LOOP_ULID` selects
that loop; its evaluator job, executive stage and reason distinguish pending
work, model-attributed completion, operator attention and uncertainty.
Use `--operation-id OPERATION_ULID` on `development-start` and
`development-control` when retrying an uncertain write, preserving the
original ID and arguments. A fresh operation ID is a new request.

The evaluator receives the recorded packet and returns a validated object
with `decision`, `assessment`, `findings`, `next_prompt` and `evidence_refs`.
It chooses `continue`, `complete` or `needs_operator`; only `continue` may
contain a next prompt. Its selected next stage is automatically offered to
Fable once the controller accepts it. Starting the loop does not prove that
the native channel accepted the offer: verify the stage is claimed and the
completion hook returns a real final response.

## Completion and evidence

Use the main session's Stop input for the final response. A Stop event
means the main agent finished responding; it does not prove that tests
passed or that background tasks finished. Native user interrupts do not
produce Stop, and API failures use StopFailure. The hook's
`last_assistant_message` is preferable to assuming the transcript already
contains that final message.
[Claude Code hooks](https://code.claude.com/docs/en/hooks#stop).

Completion must match the intended session and active round. A response to
unrelated operator conversation, a subagent's closing message, a duplicate
hook, a replaced session or an old round cannot advance the current loop.
When work remains in the background or evidence is unavailable, preserve
that distinction. The development evaluator can request a follow-up test;
it must not turn a claimed result into independent verification.

The current exchange captures the objective, round/session identity,
executive final text, executive-submitted evidence object and prior evaluator
assessment. The bridge offers `odin_loop_claim`, `odin_loop_ready` and
`odin_loop_status` only after loop activation. The ready tool produces a
stage-specific completion footer; a native Stop with that footer supplies
the final response. This does not automatically harvest every changed file,
tool result or subagent transcript. A reference to a file is not proof of
its content, and a model's account of a test is not the same as a retained
command/result receipt. Keep live packs,
transcripts and artifacts in private runtime state outside the repository;
commit only synthetic fixtures and implementation code.

Evaluator next prompts are limited to 12,000 UTF-8 bytes. Evidence objects
and evaluator results each have a 64 KiB controller limit. MCP tool requests
also have a 64 KiB complete-frame limit, so an evidence object at the core
limit cannot fit unchanged inside a tool-call envelope. Final responses are
limited to 256 KiB of UTF-8 text; native hook input and its wrapped capture
command each have a 1 MiB transport limit. Oversized capture fails without
truncating the response. Keep final responses concise and put larger
evidence in retained artifacts with precise references. An oversized final
can leave a stage awaiting capture and needs reconciliation.

## Execution receipts

Status: implementation under
[ODIN-ADR-029](DECISIONS.md#odin-adr-029--structured-execution-receipts-as-attributed-local-evidence),
2026-10-20. A receipt is attributed local execution evidence; it is not Saga
verification, canonical commitment acceptance or required review.

`odin receipt-run` executes one supplied command itself and derives a
schema-validated receipt (`schemas/execution-receipt.schema.json`, version
1) from observations the collector makes, never from a description of the
command or a separately written log:

```bash
PYTHONPATH=python .venv/bin/python -m odin receipt-run \
  --out "$PRIVATE_EVIDENCE/stage-STAGE_ULID/focused-tests" \
  --cwd /absolute/path/to/odin --loop LOOP_ULID --stage STAGE_ULID \
  --label "focused receipt tests" -- \
  .venv/bin/python -m unittest -v test_execution_receipt
PYTHONPATH=python .venv/bin/python -m odin receipt-validate \
  --receipt "$PRIVATE_EVIDENCE/stage-STAGE_ULID/focused-tests/receipt.json" \
  --expect '{"head":"COMMIT","branch":"BRANCH","clean":true,"succeeded":true}'
```

The receipt records the observed repository root and execution cwd; the
actual branch, or `detached: true` with `branch: null`; the commit; staged,
unstaged and untracked path lists with per-section diff digests and one
combined `worktree_identity`; the executed `argv`, resolved executable and
interpreter version where the executable is a Python; start and end
timestamps; the exit status, or `exit_status: null` with an explicit
`uncertainty` for a timeout, signal or spawn failure; and the retained
`stdout.log`/`stderr.log` paths with exact byte SHA256 digests. The
`collector` block binds it to the module source digest and the Odin commit
that produced it; `binding` carries the run ULID and, when supplied, the
loop and stage ULIDs. The repository is observed **before and after** the
command and `changed_during_run` is set when the identity differs, so a run
that modifies files cannot be presented as a run against the committed
tree. `head_subject` is kept for reference only and is marked
`head_subject_is_branch_evidence: false`: a merge subject naming another
branch was the reporting defect that motivated this design.

Coverage and privacy limits: staged and unstaged changes are compared
against `HEAD` with `git diff`; untracked identity covers at most 256
non-ignored files of at most 8 MiB each, recording path, size and content
digest but never content; ignored files and submodule contents are not
listed or read, so a secret kept in an ignored file is neither leaked nor
covered. A failed observation (no git, timeout) is recorded as
`observed: false` with a reason and **never** as a clean tree. Environment
variables and credential files are never recorded; `argv` and the command's
output are retained verbatim, so do not pass secrets through either.
Attribution is local: the collector runs as the same user as the command,
observations are point-in-time, and a concurrent writer that modifies and
restores a file between the two observations is not detected. Nothing here
claims an immutable or independently witnessed environment.

The wrapper's own exit status is the wrapped command's success (`0`) or
failure (`1`); a nonzero command exit is recorded in the receipt and printed
in the summary unless the receipt is internally contradictory, in which case
the summary is redacted and only the exit code carries it; the wrapper never
succeeds in place of the command. The command runs
in its own session; on timeout the whole process group is killed before the
output is hashed and the receipt says that retained output may be
incomplete. `receipt-run` refuses an output directory that already holds a
log or receipt, and only `odin [--state DIR] receipt-run|receipt-validate`
dispatches to it.

### Activation and recovery of the notice release

Records written by this release add `deadlines` and `attention`
(ODIN-ADR-030) and `delegation_profile` (ODIN-ADR-031) to the loops the new
service touches, and `development_loop_notices` rows. Per write, the new code
adds: `start` all three (`attention` as null); a status transition
`attention` (null); a stall observation `attention`; an operator deadline
edit `deadlines`; configuring delegation `delegation_profile`. The pre-notice
service (972a92d and earlier) validates loops against a closed schema when it
writes them and rejects any of these three fields, so one is enough to make
its next write of that loop fail; its command schema also rejects the
bridge's `accept` field. Consequences, stated exactly, each exercised with
real service and bridge processes in isolated temporary state (the current
tree against an extracted 972a92d tree; the output is retained privately with
the stage evidence, never in the checkout):

- **Supported recovery is forward only**: restart the service on the same or
  a later reviewed revision that carries these schemas. State is preserved
  as written; nothing is migrated or discarded. The isolated recovery test
  reopens a store with pending and acknowledged notices and a persisted
  attention observation and finds them intact and quiet. At process level,
  a service stopped while quiescent and restarted on the same revision
  reports the same attention notice identity, deadlines, revision and
  notice counts (one acknowledged, one pending); the live ticks that follow
  write nothing new for the persisted observation; a reconnecting bridge
  replays the pending assignment and notice with their original
  identities; acknowledgement and the late claim then proceed. A loop
  written only by the pre-notice service carries neither `deadlines` nor
  `attention` until the new code first touches it: status reports
  `work.deadlines` as all null, no attention and no notices, and an
  operator deadline edit adds `deadlines` without a transition.
- **Unsupported**: downgrading the service to a pre-notice revision after any
  loop has been started, transitioned, observed as stalled or re-configured
  (deadline edit or delegation) by the new code. That revision reads and
  reports such records without complaint (it validates only on write), so
  status looks healthy, but its next write of that loop (a transition) fails
  its own schema: the bridge sees a generic write failure ("Write outcome
  unavailable"), the record stays unchanged with its new fields, and the loop
  is wedged rather than corrupted until a notice-era service is restored. A
  loop never touched by the new code remains readable by both. There is no
  supported in-place downgrade; recover forward instead.
- **Mixed versions**: a new service with an old bridge delivers assignments
  only (the old bridge never declares `accept`). A new bridge with an old
  service receives an error for `accept` and falls back, for that
  connection, to the legacy poll; assignments keep flowing and notices wait
  until the service is current. Against an old service the new bridge's
  `odin_loop_ack` tool is present but every call fails with the same
  generic write failure; nothing needs acknowledging there because no
  notice can arrive. Both combinations are covered by tests and by the
  process-level scenario, so the reload order is free, but notices and
  `odin_loop_ack` work only once both are current and the conversation has
  reconnected to the new bridge.
- **Restart gate**: replace the service only when `development-status`
  reports `quiescence.restart_quiescent: true` and the supervisor has
  confirmed the native conversation is idle (not mid-turn).
  `development-status` and `odin_loop_status` report the same block. The gate
  is service-wide (`quiescence.scope: "service"`): whichever project the
  status names, it counts every active loop (detail for that project's loops,
  `loops_not_quiescent_other_projects` for the rest), every evaluator job of
  every loop, every delegated turn and the capture spool. It is false while a
  loop is `evaluator_running` or `unknown`, its current evaluator job is
  running or unknown, or a stage is unknown; the capture spool is non-empty
  or unreadable; a delegated turn is queued, launching, running or
  interrupting (`delegated_turns_running`); any delegated turn is `lost`
  (`delegated_turns_lost`), including after its session retired; or a
  dispatched evaluator job, including the cancelled job of a stopped loop,
  still has an observed process (`evaluator_executions_outstanding`) or its
  dispatch evidence or the process table cannot be read
  (`evaluator_executions_unresolved`). Missing or unreadable evidence never
  counts as absence. `quiescence.unresolved` names up to sixteen such records
  with a reason.

  Evaluator executions: `loop_control stop` cancels the job (also relabelling
  an `unknown` or `lost` job as `cancelled`) and deactivates the loop at
  once, but the evaluator scheduler stops the runner and harness later, so
  the gate reads process evidence, not the job state. A job without a durable
  evaluator-start receipt never spawned a process. A process whose arguments
  name a job's spool `development-evaluator/<job>/` keeps that job
  outstanding in any state. Completion is not process-group termination: the
  runner waits for its harness, not for every member of the harness's process
  group, so a successful harness can leave a descendant in its recorded group
  whose arguments name no spool. Every dispatched job, completed, cancelled,
  lost or unknown, is therefore checked against its dispatch reservation and
  `started.json`: it stays outstanding while a recorded runner or harness
  process group has a live member, and unresolved while `dispatch.json`, or
  `started.json` when present or the job is completed (the runner writes it
  before its result), is missing, unreadable or not private. A job that is
  not completed and has no `started.json` is checked against the runner group
  alone. Until the attempt is recorded quiet, a reused process ID can only
  make the reading conservative.

  Decision (stage 7): the evaluator scheduler, not the status, records when a
  finished (`completed`, `cancelled` or `lost`) job's latest started attempt
  has been observed quiet: one process-table reading found no member of the
  runner and harness groups recorded for that attempt and no process naming
  its spool (the runner's and harness's own arguments name it), with its
  dispatch for that attempt and, when present or once completed,
  `started.json` readable and private. The record is a durable loop receipt
  `evaluator-quiet:<job>:<attempt>`; it changes no loop or job state, signals
  nothing and is never written from missing or unreadable evidence or an
  unreadable process table. An empty process group cannot regain members, so
  the gate stops reading that attempt's groups (the spool-argument check
  still applies); a later attempt needs its own record. No existing record is
  erased or relabelled. Inspection is bounded: at most 1024 dispatched jobs
  without that record, and 65536 process entries; beyond either the reading
  is unresolved, never absent. Jobs whose groups stay populated, whose
  evidence is unreadable or that stay `unknown` are never recorded quiet and
  never deleted, so past 1024 of them the gate stays false permanently (the
  remaining fail-closed residual) and every restart needs the external
  observation below. A service older than this decision writes no
  `evaluator-quiet` record: after replacement, the new scheduler records each
  earlier finished job whose evidence it can read, and the gate keeps reading
  every other one, so it stays closed or unresolved until they are recorded.

  Unresolved dispatch evidence keeps the gate false until the files are
  restored as private regular files; if they cannot be, replacing the service
  needs the same explicit supervisor decision as a lost turn, based on no
  live process naming the job's spool and none in the process groups of the
  runner and harness PIDs recorded there (`pgrep -g <pid>` for each), where
  still readable. The runner's and harness's arguments name the job's spool,
  so a runner or harness whose group was never recorded, or that belongs to
  an attempt superseded by a relaunch, is still seen while it runs. The gate
  cannot see a process that left every recorded group (by `setsid` or
  `setpgid`) and names no spool, including a descendant of an unrecorded or
  superseded attempt, nor a process of another user it cannot read. The quiet
  record makes one observation durable: a member hidden from that reading,
  such as another user's process, is not revisited, and after it a reused
  process ID no longer holds the gate.

  Lost delegated turns: a lost turn's native outcome is unknown and no
  supported path records its resolution, so, as for `configure_delegation`,
  it keeps the gate false permanently; the record is never erased or
  relabelled. Retirement and acknowledgement are not process termination. Its
  `unresolved` entry reports whether the recorded runner and harness process
  groups are observed `present` (a group has a live member or a process
  argument names the turn's spool), `absent` or `unknown`. Replacing the
  service with a lost turn on record therefore needs an explicit supervisor
  decision outside the gate, based on this external observation: no live
  process in the turn's recorded runner or harness process group (`pgrep -g
  <pid>` for each), no process naming the turn's spool
  `delegations/<session>/<turn>/`, and no native harness process for that
  turn's session. The gate cannot see a harness whose process group was never
  recorded (the runner exited before writing `started.json`) or a descendant
  that left its process group.

  Any process of this user naming a spool path, even a `tail -f` on a spool
  file, keeps the gate closed while it runs. The status only observes: it
  signals, reconciles and redispatches nothing. A reading is not a lock: an
  evaluator can be dispatched and a delegated turn can start immediately
  after it, so read the gate immediately before the replacement, not earlier.
  An interrupted evaluator must be reconciled through `loop_reconcile` with a
  real observation afterwards.

### Receipts in the development loop

`odin_loop_ready` evidence may carry `receipts`, a list of at most sixteen
compact references `{"kind": "execution_receipt", "path": ..., "sha256": ...}`,
and an optional `claims` object with structured assertions (`head`,
`branch`, `detached`, `clean`, `exit_status`, `succeeded`). The controller
validates deterministically at `ready` and again when the final response is
captured, and records the outcome as `receipt_validation` on the stage and
in the evaluator packet:

| Status | Meaning |
|---|---|
| `validated` | Every referenced receipt is a private file whose bytes match the reference digest, validates against the schema, is bound to this loop and stage, was started after the stage was created, has private artifacts whose bytes match their digests, did not change the worktree during the run, agrees with every claim, and observed a git repository |
| `validated_unobserved` | As `validated`, except the command ran where no repository could be observed; the receipt carries no revision or branch identity |
| `uncertain` | Exactly one of the two repository observations is available (typically the post-run observation failed); the receipt is otherwise consistent, but an unchanged tree is not established, `clean` is null and only `clean_before` is reported |
| `mismatched` | A declared digest, binding, claim, expected identity or start time disagrees with the receipt, or the worktree changed during the run; the problems list names each disagreement. A declared-digest mismatch is reported alone and the file's contents are not echoed |
| `missing` | A referenced receipt or one of its artifacts is absent, or the list is empty |
| `invalid` | A reference is malformed, a receipt is unreadable, not private, changed during inspection or fails the schema, the receipt is internally contradictory (see below), the artifact hashing budget (256 MiB per validation) was exceeded, or the validator itself failed |
| `legacy_no_receipt` | The evidence has no `receipts` key: earlier or receipt-less evidence, recorded as unverified rather than failed |

`commands_succeeded` is reported beside the status: a receipt of a command
that exited nonzero is valid evidence of a failure, never success, and the
bridge answer, stage record and packet all carry each receipt's
`exit_status`, `succeeded`, `observed_before`, `observed_after`,
`before_reason`, `after_reason`, `clean_before`, `clean` and
`changed_during_run` so that no summary can hide them. An `invalid` receipt
reports `succeeded: null` and `commands_succeeded: null` and keeps only its
path, digest, binding, `cwd` and `argv` identity fields.

Consistency is checked, not assumed. Before any artifact is hashed the
validator recomputes the derived fields the format carries: `succeeded`
must equal `exit_status == 0`; a null exit status needs a recorded timeout,
signal or uncertainty, and a timed-out run has no exit status; `finished_at`
must not precede `started_at` and `duration_seconds` must agree with them;
exactly one `stdout` and one `stderr` artifact must be listed, with absolute
paths; each observation's `untracked_digest`, list order and length,
`untracked_coverage`, empty-diff digests, `worktree_identity`, `clean` and
`detached` must derive from its own lists, digests and branch; the observed
root must contain the repository path; two observations must name one root,
bracket the command in time and agree with `changed_during_run`, which must
be null when either observation is missing. Any contradiction makes the
receipt `invalid`, and an invalid receipt reports no observed field (head,
branch, clean, exit status, start time) at all; a failing, signalled, timed-out or
uncertain command with consistent fields stays `valid` evidence of that
outcome. A claimed or expected `clean` is compared with the derived value and
can only be met by a receipt with both observations and no change during the
run. Timestamps are compared as timestamps (UTC, at most microseconds).
If the wall clock moves backward during a command, the collector still
persists the original timestamps, exact exit status and retained output
digests. It records `duration_seconds: null` and explicit clock uncertainty.
Reversed chronology remains `invalid`; validation and the `receipt-run`
summary redact observed success and repository fields. The raw outcome
remains in the receipt, and the CLI exit code still reports command success
or failure, not receipt validity. A null duration without reversed timestamps
or a recorded uncertainty is also invalid.

Retained files are inspected through one descriptor: non-regular files such
as a FIFO are never read (the open is non-blocking and the type is checked
before any read), byte limits are enforced against the bytes actually read,
a file whose size or mtime differs after the read, or whose path then names
another inode, is reported as changed, and the receipt is parsed from the
exact bytes whose digest was checked. An artifact beyond the 64 MiB
inspection limit, or beyond the per-validation budget, makes the receipt
`invalid`. These inspections are point-in-time, not snapshots, and a hung
filesystem can still block an open or read. Validation establishes internal consistency and
binding, not authorship: the executive principal runs as the same user as
the collector and could write a receipt by hand; such a file is marked
`collector_matches_validator: false` only when its collector digest differs
from the validating module, which is a hint, not proof. A controller-side
registry of collected receipts is the recorded follow-up for stronger
attribution. The evaluator is instructed to read the retained receipt
itself, compare the executive's prose with the receipt's observed fields and
retained output, recompute artifact digests, and treat `legacy_no_receipt`
as unverified. Validation runs before the controller's write transaction,
is bounded (16 receipts, 256 problems of at most 1400 bytes, 64 KiB in
total) and is reported in the packet; it is never raised as success, and a
structurally malformed reference list is reported as `invalid` rather than
refused, so the executive's return is still captured and assessed. Existing
stages and packets without `receipt_validation` remain valid records.

## Notices and attention

Status: implementation under
[ODIN-ADR-030](DECISIONS.md#odin-adr-030--durable-loop-notices-and-conservative-attention),
2026-10-21. Synthetic tests exercise these paths through isolated service and
bridge processes; live acceptance requires an observed activation.

A **notice** is a durable, project- and session-scoped record that the
controller writes in the same transaction as the loop transition it
describes: `completion` (evaluator decided `complete`), `intervention`
(`needs_operator` or `unknown`), `failure` (`needs_operator` with a lost or
blocked evaluator job), `stopped` (operator stop) and `stalled` (a deadline
observation, below). Its identity is a function of the loop, kind, status
and loop revision, so a replayed or repeated transition never creates a
second notice. It carries the loop, stage and job identities, the
transition, a bounded summary, the evaluator's assessment and decision when
one exists, what needs attention, and a status reference
(`odin_loop_status`). Any completion footer quoted in model text (an
evaluator assessment or loop reason) is redacted before the notice is
written, and again on delivery, so a notice never carries a usable footer
and a quoted footer never blocks the inbox. A `stalled` notice's identity
also includes the observation, the deadline in force and the time the
observation was made, so a deadline changed and reverted, or disabled and
re-enabled, yields a new notice for the new observation while the same
persisted observation is never written twice. Rendered notice content is
bounded to 16,384 UTF-8 bytes: the identity header, acknowledgement
guidance, attention, related identities and status guidance are kept whole,
the summary and assessment share the remaining budget and are clipped on
character boundaries after redaction, and notices persisted under earlier
character-based limits are bounded the same way on delivery, so a valid but
oversized narrative cannot block the inbox.

Notices travel through the existing channel as events with
`meta.kind: "notice"` and `meta.notice_id`, beside assignments with
`meta.kind: "assignment"`. The bridge declares the kinds it accepts in each
inbox read (`accept`); a bridge from before notices declares nothing and
keeps receiving assignments only, so the service and the bridge can be
reloaded in either order and a pending notice waits for a current bridge. The inbox returns at most eight of each per poll
so neither starves the other. A notice is offered until the executive
acknowledges it with `odin_loop_ack`; it stays deliverable after the loop
has ended or while it awaits the operator. The channel offers the eight
oldest unacknowledged notices; later ones wait their turn but are always
visible in status. Only the executive's own inbox reads count as offers;
an operator reading the inbox over the socket records nothing. An operator
acknowledgement over the socket is labelled by role
(`operator_terminal_acknowledgement_not_approval`); like a model
acknowledgement it stops re-delivery and approves nothing. Delivery is **at least once**: a
channel write, a bridge emission or a lost reply proves nothing, a reconnect
replays the same `message_id`, and the service records only the first offer
(`first_offered_at`), never one write per poll. Acknowledgement is
model-attributed (`acknowledgement_authority:
model_attributed_not_operator_approval`): it stops re-delivery and grants
nothing else. No notice asks the executive to claim or execute a stage, and
the native-facing instructions say so; a reply to a notice has no footer
and is never captured as a stage completion. There is no exactly-once
delivery and no human acknowledgement in this path. Operator-only actions
(continue, pause, resume, stop, reconcile, deadlines) remain on the operator
command path; authenticated routing of operator decisions from a chat
surface is still future work and is not provided by notices.

**Deadlines** are per-loop, optional and disabled by default:
`offer_seconds` (stage offered, unclaimed), `claim_seconds` (claimed, not
ready), `ready_seconds` (ready, not captured) and `evaluator_seconds`
(evaluator pending or running). They are set at `loop_start` or changed by
the operator with `development-control --control deadlines --deadlines
'{"offer_seconds": 600}'` (the `loop_control` action `deadlines`), each a
positive number of seconds up to one week or null. A deadline edit is not a
transition: status, revision, timing and delivery identities are untouched,
and only an attention observation made under the deadline being changed is
cleared. The service checks waiting loops every few seconds. When
the time since the loop's last transition exceeds the applicable deadline,
the controller records an **attention** observation on the loop
(`observed`: `offer_unanswered`, `claimed_stalled`, `ready_uncaptured` or
`evaluator_stalled`, with elapsed and deadline seconds) and writes one
`stalled` notice. The loop's status and revision do not change: nothing is
redispatched, no new round starts, no process is terminated, no session is
replaced, and a pending stage stays claimable. Elapsed time never proves a
command was not started. Repeated checks after attention observe nothing new
and write nothing. Any real transition (a late claim, ready, capture,
evaluation, pause, resume or reconciliation) clears the observation and
restarts timing from that transition. Paused, unknown, intervention-bound and
terminal loops are not timed; a clock that moved backwards raises no
attention; records written before deadlines existed are untimed and remain
valid. Existing late-result and reconciliation protections are unchanged:
reconciliation still requires a real observation of the native session or
evaluator process.

`development-status` and `odin_loop_status` show `work` (`waiting`:
pending, running, unknown or none; the applicable deadline; `since`; the
current `attention`) and `notices` (pending, acknowledged and unoffered
counts with the latest four). Pausing or stopping the controller remains a
controller transition; the `stopped` notice says that running native tools
or delegated jobs were not terminated by it.

## Failure, restart and operator control

| Situation | Required controller behavior |
|---|---|
| Duplicate notification or hook | Retain the same operation/round identity; do not create another task or evaluation |
| Duplicate or replayed notice | Same notice identity until acknowledged; acknowledgement is idempotent and changes no loop state |
| Deadline exceeded | Record attention and one stalled notice; keep status, revision and pending work unchanged; never redispatch or terminate |
| Stale session, round or evaluator result | Refuse the transition and show why it cannot advance the current loop |
| Uncertain delivery or interrupted turn | Keep an explicit pending/unknown state; do not silently invent a replacement round |
| Service or bridge restart | Recover durable state and reconcile the outstanding exchange before continuing |
| Unaccepted channel or missing completion hook | Keep delivery unverified or the stage awaiting return; do not infer completion from silence |
| Invalid evaluator output | Hold continuation with an attributable failure; do not invent a next test |
| Pause | Prevent new automatic dispatch/evaluation; preserve work and evidence for an explicit resume |
| Stop | Prevent further loop work directly, independently of the evaluator's opinion |
| Evaluator requests operator intervention | Retain the completed result; accept a recorded operator response through `development-continue` when work is inactive and round budget remains |
| Round or repeated-evidence bound reached | Enter `needs_operator` with the reason recorded; do not reset the bound automatically |

An explicitly reconciled retry keeps the stage identity and changes the
delivery identity so the current MCP connection can offer it again. Old
claim/ready receipts cannot revive a stage after pause, stop or a changed
loop revision. The executive must claim the current delivery using a fresh
logical operation after such recovery; transport retries of an unchanged
operation retain its original ID.

Pausing or stopping the controller is not a claim that an already running
native tool, subagent or detached delegation was killed. The operator retains
native session controls, and delegated work retains its own stop/recovery
path. A native interrupt is not automatically a durable controller pause
unless the controller records that observation. The finite round bound
limits loop continuation; it does not enforce model spend or all execution
inside one native turn.

The initial limits are `max_rounds` (default 12) and `no_progress_limit`
(default 3), each configurable from 1 to 100. The latter counts consecutive
repetitions of the normalized evaluator evidence-reference set. It detects
that particular stall pattern; it does not measure semantic progress. The
controller's deadline checks (above) only observe and notify; an unanswered
channel offer or interrupted turn still requires an explicit status check
and, when needed, reconciliation.

Direct controls use the operator socket and do not ask the evaluator whether
the request should be obeyed. Replace `pause` with `resume` or `stop` for the
corresponding transition:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-control \
  --project PROJECT_ULID --loop LOOP_ULID --control pause
```

An evaluator's completed `needs_operator` decision has a separate response
path. Once its intervention is addressed, read `development-status` and
write a private request file containing the current loop revision:

```json
{
  "project": "PROJECT_ULID",
  "loop_id": "LOOP_ULID",
  "expected_revision": 13,
  "response": "The requested service-only activation is complete; assess the retained evidence and determine the next test within the existing objective.",
  "evidence_packet": {}
}
```

Submit it through the operator socket, retaining one operation ID for retries:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-continue \
  --request /absolute/private/path/operator-response.json \
  --operation-id OPERATION_ULID
```

This records the response and optional bounded evidence in a fresh evaluator
packet, alongside the original executive evidence, receipt validation and
previous assessment. The completed stage and previous job are preserved.
The new evaluator job stays at the same round; configured bounds and progress
counters are unchanged. Only its accepted assessment can create the next
executive stage. Exact retries return the original command receipt, including
after a service restart; changed payloads or stale revisions are refused.

Continuation requires a completed evaluator `needs_operator` result, all
executive stages completed and remaining round budget. It cannot resume a
paused loop, reconcile uncertain delivery or a lost evaluator, retry a failed
job, reopen a stopped/completed loop or reset an exhausted bound. Use the
corresponding status, resume or reconciliation path for those states. The
command is operator-only and is not an executive MCP tool. Its response is
evidence for assessment, not authority to expand the configured objective.

For a service upgrade requested by an intervention, first confirm there is
no active executive stage or evaluator. Restart only the service on the
verified revision, preserving the native executive session and bridge, then
reobserve the durable loop state before submitting the response. A successful
restart alone does not establish live receipt validation; observe the next
ready result and captured evaluator packet through the existing bridge.

A paused final response and evaluator result remain retryable after resume.
A StopFailure holds the correlated executive stage as unknown; it never
advances a successful round. For a known native interruption, the operator
can record `loop_hold` through the generic command path:

```json
{
  "schema_version": 1,
  "operation_id": "OPERATION_ULID",
  "action": "loop_hold",
  "payload": {
    "project": "PROJECT_ULID",
    "loop_id": "LOOP_ULID",
    "stage_id": "STAGE_ULID",
    "reason": "Operator observed the native executive turn interrupted."
  }
}
```

Use a fresh ULID for this logical request, preserve it on an uncertain retry,
and submit the file with:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" command \
  --request /absolute/private/path/development-hold.json
```

Reconciliation uses the same envelope with action `loop_reconcile` and
payload `project`, `loop_id`, `target`, `observed`, and the target identity:
`stage_id` for target `executive`, or `job_id` for target `evaluator`.
Allowed observations are `running`, `not_started` and `lost`. Supply the
observation only after checking the actual native turn or evaluator process;
a timeout or missing response alone does not prove `not_started`.
`running` restores the recorded in-flight state, `not_started` makes the
same work eligible again, and `lost` requires operator attention. Paused
loops must resume before reconciliation; a failure received during pause
keeps them paused with an unknown state to reconcile afterward.

## Acceptance before calling the loop live

The first live receipt must cover the intended native session and at least
two linked rounds, with no manual copying of prompts or final responses.

| Check | Evidence to retain |
|---|---|
| One executive process | Same retained native session and credential lineage; no second Claude driver process |
| Channel works | A controller-generated test reaches that executive and is acknowledged with the current round identity |
| Executive performs the task | Actual native work, including a test and, when relevant, subagent or code-change evidence |
| Automatic return works | Final-response hook records the correlated return and the supported evidence pack |
| Evaluation changes the next stage | Separate evaluator output explains its assessment and delivers the next test without operator copying |
| Bounds work | Round or repeated-evidence exhaustion prevents another automatic round |
| Stop/pause work | Operator control prevents subsequent controller work even if the model wants to continue |
| Recovery works | Restart plus duplicate/stale input preserves the intended round and does not repeat unconfirmed execution |
| Human conversation survives | Remote Control still reaches the same executive, and unrelated human messages do not masquerade as round completion |

Synthetic transport/evaluator tests are local implementation evidence.
They do not close these live checks, full I2/I3, Saga Phase B, the managed
session-host work, or the cross-repository handoff. Required Mimir review
remains separate from this development loop's assessment.

The focused local checks use synthetic model binaries and temporary state:

```bash
PYTHONPATH=python:tests .venv/bin/python -m unittest test_execution_receipt -v
PYTHONPATH=python:tests .venv/bin/python -m unittest test_development_notices -v
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests -p 'test_development_*.py' -v
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests -p 'test_executive_loop_transport.py' -v
```

The integration test exercises a real service process, MCP channel frames,
synthetic evaluator execution and native-shaped hook input across two
rounds, including capture during service outage and drainage after restart.
It requires local Unix socket/process access. It does not invoke Fable,
authenticate a new login or prove that a native Claude client accepts the
custom channel.


## Usage and orchestration experiment

New loops can require an accountable separate orchestrator return through
`delegation_profile` and `odin_loop_delegate`. Optional usage policies hold
future admissions while retaining existing work identities; bounded context
checkpoints preserve attributed continuation notes. Existing loops and their
round limits remain unchanged. See [usage and routing](USAGE-AND-ROUTING.md)
for the explicit collection commands, settings, limitations and staged live
acceptance. These controls do not enforce in-flight native spend or establish
that every native subagent source has been captured.
