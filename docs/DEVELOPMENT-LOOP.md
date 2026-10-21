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
failure (`1`); a nonzero command exit is recorded in the receipt, printed in
the summary and never concealed by the wrapper succeeding. The command runs
in its own session; on timeout the whole process group is killed before the
output is hashed and the receipt says that retained output may be
incomplete. `receipt-run` refuses an output directory that already holds a
log or receipt, and only `odin [--state DIR] receipt-run|receipt-validate`
dispatches to it.

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
`after_reason`, `clean_before`, `clean` and `changed_during_run` so that no
summary can hide them. An `invalid` receipt reports `succeeded: null` and
`commands_succeeded: null`.

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
branch, clean, exit status) at all; a failing, signalled, timed-out or
uncertain command with consistent fields stays `valid` evidence of that
outcome. A claimed or expected `clean` is compared with the derived value and
can only be met by a receipt with both observations and no change during the
run. Timestamps are compared as timestamps (UTC, at most microseconds).
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

## Failure, restart and operator control

| Situation | Required controller behavior |
|---|---|
| Duplicate notification or hook | Retain the same operation/round identity; do not create another task or evaluation |
| Stale session, round or evaluator result | Refuse the transition and show why it cannot advance the current loop |
| Uncertain delivery or interrupted turn | Keep an explicit pending/unknown state; do not silently invent a replacement round |
| Service or bridge restart | Recover durable state and reconcile the outstanding exchange before continuing |
| Unaccepted channel or missing completion hook | Keep delivery unverified or the stage awaiting return; do not infer completion from silence |
| Invalid evaluator output | Hold continuation with an attributable failure; do not invent a next test |
| Pause | Prevent new automatic dispatch/evaluation; preserve work and evidence for an explicit resume |
| Stop | Prevent further loop work directly, independently of the evaluator's opinion |
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
controller has no wall-clock deadline scheduler. An unanswered channel
offer or interrupted turn requires an explicit status check and, when
needed, reconciliation.

Direct controls use the operator socket and do not ask the evaluator whether
the request should be obeyed. Replace `pause` with `resume` or `stop` for the
corresponding transition:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" development-control \
  --project PROJECT_ULID --loop LOOP_ULID --control pause
```

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
