# Fable executive development runtime

Status: native development profile under
[ODIN-ADR-026](DECISIONS.md#odin-adr-026--native-executive-development-access),
building on [ODIN-ADR-024](DECISIONS.md#odin-adr-024--native-fable-executive-conversation-pilot)
and [ODIN-ADR-025](DECISIONS.md#odin-adr-025--executive-repository-evidence-access),
2026-10-19. Preparation and component checks do not establish a live login,
Fable entitlement, Remote Control connection or production readiness.

This pilot gives the operator a persistent conversation with Fable in native
Claude Code, with scoped access to Odin's local continuity records. The
version 3 development profile also gives it the normal native tools and
operator environment to inspect, implement, test and improve Odin directly.
The older versions 1 and 2 remain restricted profiles; their limitations do
not apply after the development upgrade.
The local Odin service stores memory and reports in persistent SQLite. Its
execution backend is still fake Saga, so results retain the compatibility
label `fake-backend evidence` even when the conversation uses a live model.
The label does not mean that the record store is a stub or that reports
disappear on restart. Resume/report results include `service_context` to
make this distinction explicit; it does not confer live Saga guarantees.

## What this slice can do

| Capability | Pilot boundary |
|---|---|
| Conversation | Native interactive Claude Code, requesting `claude-fable-5-1`; Remote Control provides the human interface |
| Continuity | Read the bound project's commitments, unresolved work, memory coverage and exact source revisions through the service |
| Repository and environment | Version 3 uses the normal native file, shell and edit tools with the real checkout cwd/HOME and inherited environment; committed snapshots remain available through Odin memory |
| Progress | Record and read back explicitly unverified reports; a report does not close a commitment or verify an outcome |
| Improvement | Inspect, edit, execute commands/tests and use native agents for operator-directed development; report evidence and resulting changes |
| Authority | `fable-executive` is a coordinator bound by the service to one project; model tool arguments cannot select a different principal |
| Execution | Normal native development execution with permission bypass; the added MCP bridge does not itself expose Saga worker launch or approval/grant tools |
| Delegation | Six `odin_delegation_*` tools under ADR-027 open accountable local-backend sessions (a legacy or integration-owner session per project, plus workstream sessions under ADR-036), assign owned commitments, run detached Claude Code or Codex turns, send follow-ups, collect unverified returns and record executive acceptance; no Saga launch, approval or grant |
| Workstream delegation sessions | ADR-036 phase 1: optional `workstream` label and `role`, with per-workstream, one-integration-owner and distinct-workspace refusals; only the integration owner sets the interface decision owner. Default concurrency is one turn per credential lineage, so sessions interleave rather than run in parallel. Odin does not enforce the git rules; status reports `project_aggregate` with cost labelled `attributed_not_verified` |
| Runtime | An operator-launched local pilot; the authenticated homelab/workstation daemon and full SDK lifecycle remain future work |

There is no service-enforced model cost or turn budget in this pilot. Native
account limits and operator control are not evidence of Odin budget
enforcement; `executive-status` reports this boundary explicitly. It also
reports `service_reachability`: `reachable` means one scoped `odin_resume`
probe over `executive.sock` succeeded (two-second socket timeout per stage,
not a total deadline), `unavailable` means the probe failed for any reason,
including access denial or an invalid reply, and `unchecked` means the
bridge is disabled in the manifest. It is a point-in-time probe, not a
service-health guarantee, and for version 3 an unavailable Odin service is
not a loss of native coding capability.

The bridge lets Fable create commitments only through delegation assignments
(ADR-027); other commitment edits remain in Odin's existing service paths. Ordinary chat stays
in Claude Code's native transcript; it is not automatically captured into
Odin memory, interpreted as progress, or recorded as an authenticated
operator command. A statement relayed by the model is a model report.

## Enable the development profile

For the existing workstation runtime, select the version 3 profile with:

```bash
~/.local/state/odin-executive-pilot/run executive-enable-development
~/.local/state/odin-executive-pilot/run executive-status
```

This writes a validated pending profile without interrupting the active
Claude process. Status distinguishes the current configured profile from
pending development access. Startup arguments cannot change the tool
manifest of an already running conversation. Exit Claude when ready, then
resume the same session:

```bash
~/.local/state/odin-executive-pilot/run executive-start --resume-session
```

The next owned runtime operation, normally this resume, activates the
pending profile under the existing launch and credential-ownership locks. It preserves the native session UUID, dedicated
login, project binding, conversation and local Odin records. The equivalent
repository commands are:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-enable-development
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start --resume-session
```

No additional development flag is needed on subsequent resumes.

Version 3 uses Claude Code's normal native tools and system prompt, appends
brief Odin context, selects `bypassPermissions`, starts in the actual Odin
checkout, and inherits the real HOME and operator environment. Odin no longer
restricts native tools or filesystem paths, limits MCP discovery to its own
server, or disables hooks, plugins, skills, native memory, browser tools or
native agents. The old generated settings files remain on disk but version
3 does not load those restrictive settings. The optional
[development feedback loop](DEVELOPMENT-LOOP.md) adds its own completion
hooks and custom MCP channel on an explicit resume under ADR-028. These capabilities
load through the harness's normal configuration mechanisms; the upgrade does
not install missing integrations.
The dedicated `CLAUDE_CONFIG_DIR` is retained for the existing login and
session history. It is not an isolation boundary from the rest of the local
environment.

The executive can now implement and test improvements directly. It does not
need to wait for the fake Saga backend or obtain a proposal disposition to
perform operator-directed native development. Existing project instructions
and explicit operator choices still apply. Odin's MCP principal remains
bound to its project, and recorded reports/proposals retain their existing
meaning: a native edit is evidence of a change, not automatically a
Saga-verified outcome or a rewritten approval record.

For automatic next-test delivery, final-response capture and independent
assessment between development rounds, use the
[development evaluator runbook](DEVELOPMENT-LOOP.md). It retains this native
session and Remote Control, with separate evaluator invocation and direct
operator pause/stop controls. Configuration alone does not prove live
channel delivery or a completed multi-round loop.

An unavailable Odin service does not prevent version 3 from launching native
development. Its added MCP reads/reports will be unavailable until the service
is reachable; the runtime must report that condition without treating it as a
loss of native coding capability.

The actual source checkout is `/home/david/.codex/worktrees/23e7/odin`, with
design documents under `docs/`. Current native files and committed Odin
memory are different evidence: import a new commit to refresh the latter.

## Prepare the local pilot

Run from the repository root using a virtual environment with the pinned
root requirements. Keep both runtime state and the dedicated Claude
configuration outside the repository. Use a new pilot state directory to
avoid importing existing conversations or synthetic demo projects by accident.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/python"
ODIN_PILOT_STATE="$HOME/.local/state/odin/executive-pilot"
ODIN_CLAUDE_CONFIG="$HOME/.local/share/odin/claude-executive"
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-prepare \
  --claude-config "$ODIN_CLAUDE_CONFIG"
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-status
```

Preparation creates a local Project if `--project` is omitted. To select an
existing Project in this state, supply `--project PROJECT_ULID`. Record the
project identifier returned by preparation; the service and executive
configuration must bind to that same project. Preparing files does not log
in, invoke a model or connect Remote Control.

Use `executive-login` to enter the native login flow for the dedicated
configuration:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-login
```

Complete the native subscription login as the operator. Do not copy the
development login, put tokens into configuration files, or run a second
login/session owner against this credential lineage. The preparation path
is not a credential-provisioning or account-entitlement check.

## Start and connect

In one terminal, start the local service with the project from preparation:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" serve \
  --executive-project PROJECT_ULID
```

In another terminal, with the same repository and Python environment:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start
```

The executive uses the dedicated `executive.sock` service binding. Versions
1 and 2 use a prepared workspace; version 3 starts in the actual checkout.
Native login, workspace-trust and Remote Control dialogs must be completed in Claude Code. Follow the session URL or QR code
shown there to connect from the Claude app or browser. Observe an actual
Fable response and connected Remote Control state before describing either
as working. A running process can coexist with a failed remote connection.

Use the native session's interrupt/exit controls to stop the conversation.
Ctrl+C can interrupt a turn while leaving the session open; verify that the
native process has exited when testing stop. The service's `stop` command stops service-authorized
work but does not terminate the foreground Claude process. Resume the
prepared session, using its retained native ID and the same project binding:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start --resume-session
```

`--resume-session` is a flag, not a transcript path or a way to select an
arbitrary conversation from the development profile. Resume is a separate
live check, not a claim made by the saved session ID.

With the prepared workstation launcher, reopen from any terminal, including
Herdr's terminal, with:

```bash
~/.local/state/odin-executive-pilot/run executive-start --resume-session
```

The launcher selects the cwd, dedicated login, current/pending profile and
saved session; no `cd` is needed. Running bare `claude` bypasses that identity
and profile selection. Versions 1 and 2 disable inherited hooks; version 3
loads hooks normally. An error such as
`heimdall: json: unknown field "scratchpad_dir"` is a separate hook
compatibility issue, not an Odin resume error. A repeated `executive-start`
prints the explicit resume instruction without a Python traceback.

If a launch ended before Claude created a resumable session, or the operator
intends to start a fresh conversation, allocate a new native ID explicitly:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-new-session
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start
```

The reset requires the launch/credential locks to be free, archives launch
metadata and retains native transcripts. It does not erase project records
or recover a failed operation by silently replaying it.

Rotation never moves a development loop. After rotating, the command reads
the service for a non-terminal loop still owned by the previous session;
when one exists the output includes `development_loop_handover` with the
loop's ID, its revision and the exact `odin development-handover` command
for the operator to run. If the service cannot be reached the check is
reported unmade (`checked: false`) and the output names the manual step:
inspect `odin development-status` for a loop owned by the previous session,
then run `development-handover`.

## Delegate work through Odin

Version 3 has two delegation paths. Native subagents (the Agent tool) suit
quick bounded work whose result the executive integrates in the same
conversation. The Odin delegation tools suit work that must persist as a
project commitment, run detached as a resumable Claude Code or Codex session,
survive the conversation or a service restart, or be collected and accepted
later. ODIN-ADR-027 records the decision.

Enable the path once per state directory, then restart `serve` so it loads
the configuration:

```bash
~/.local/state/odin-executive-pilot/run delegation-configure \
  --claude-config ~/.local/state/odin-executive-pilot/claude-login \
  --workspace-root ~/.local/state/odin-executive-pilot/workspaces
```

The file names the harness binaries, the Claude configuration directory the
workers use, an optional `CODEX_HOME`, default models and the directories
under which session workspaces may live. Workers inherit the operator
environment plus those settings.

Credential ownership is enforced, not only labelled. The executive runtime
holds a `flock` lease on `.odin-lineage.lock` inside its login directory
for as long as it runs; the detached runner takes the same lease on the
worker's Claude configuration directory (or on `CODEX_HOME` when one is
configured) before it starts a harness process and releases it afterwards.
Under the default `lineage_policy` of `exclusive`, a session on a lineage
the executive owns (the same login directory) or on the operator's own
`~/.codex` login is refused with `lineage_shared_requires_acceptance`, and a
turn whose lease is busy, or whose lease file cannot be trusted (symlink,
foreign owner, loose mode), is refused by the runner without starting the
harness (`lease: busy` or `unavailable`, `refused: true` in the turn
result); the operator's own development login (`~/.claude` or the
service's `CLAUDE_CONFIG_DIR`) is refused as `operator-claude-login`, and
sessions whose lineage is already running another session's turn stay
queued rather than being refused. Setting
`--lineage-policy shared_accepted` records the operator's acceptance of a
shared lineage: such turns run, and the result still records `lease: busy`
and `shared_with: executive`. Every turn result also carries a
`credential_before`/`credential_after` fingerprint (mtime, size and digest
of the credential file, never its contents) and `credential_changed`, so a
refresh during a worker turn is evidence in the record. Sharing the
executive's dedicated login with workers remains an interim operator choice
while X-12 is open, not managed credential isolation; `exclusive` is the
policy X-12's resolution needs.

The cycle, with every mutating call carrying a fresh ULID `operation_id`
that is safe to replay with identical arguments:

1. `odin_delegation_session` `create` with harness, workspace, briefing and
   options opens the session (a `PlanningSession`, binding and host
   `Environment` record). A session that declares neither `workstream` nor
   `role` (legacy), or declares `role: integration_owner`, becomes the
   project's planning owner (interface decision owner); a `workstream` label
   alone makes a workstream session under ADR-036, which never does.
2. `odin_delegation_assign` records an open `Commitment` with acceptance
   criteria and a `backend: local` `Assignment`, and queues the first turn.
   Claude Code turns pass `--max-turns`, and `--max-budget-usd` only when a
   budget is requested (`limits.budget_usd` is optional; an omitted budget is
   recorded as `not_requested`). Codex offers no such options, so an
   assignment there requires `allow_unenforced_limits`. Odin records limits
   and reported usage; it enforces no ceiling.
3. The service launches a detached runner on its next tick. The runner
   executes `claude -p --output-format json --session-id` (later
   `--resume`) or `codex exec --json` (later `codex exec resume`), forwards
   interrupts, applies the wall-clock limit and writes `result.json` under
   `STATE/delegations/SESSION/TURN/` with the prompt, argv and logs.
4. `odin_delegation_status` ingests finished runners and shows session,
   assignment and turn states (`queued`, `launching`, `running`,
   `interrupting`, `returned`, `failed`, `interrupted`, `lost`), runner
   liveness, known cost and turns whose cost is unknown.
5. `odin_delegation_followup` sends another message into the same native
   conversation for an open assignment; it is refused while a turn runs.
6. `odin_delegation_result` returns a finished turn's full final text and
   transcript paths within `max_bytes`, or says the text is larger.
7. `odin_delegation_close` records `accepted` (evidence references for every
   criterion; the assignment completes and the commitment closes as
   executive-attributed acceptance) or `cancelled` (the commitment is
   abandoned). A returned turn never closes anything by itself.
8. `odin_delegation_session` `stop` signals a running turn and retires the
   session; the remote outcome stays unconfirmed until the runner reports.
   A service restart retires an active session; `resume` opens a new
   incarnation and binding when no turn is running. A runner that exits
   without a result is `lost`, never retried. A new session adopts open
   commitments left by a retired one with a new ownership generation; under
   ADR-036 adoption is restricted to the same workstream, and a legacy session
   adopts only from unlabelled sessions.

Observed on 2026-10-20 with Claude Code 2.1.303: a `-p` worker under
`permission_mode: acceptEdits` can edit files but every shell command returns
"This command requires approval", so a worker that must run tests needs
`bypassPermissions` (the launcher then adds `--dangerously-skip-permissions`)
or the executive runs the checks in the worker's workspace itself before
accepting. Codex workers run under the configured sandbox (`read-only` or
`workspace-write`) and report usage without cost; their native thread id is
known only after the first turn returns.

`executive-status` reports `local_delegation_configured` (the configuration
file exists) separately from `delegated_execution_enabled`, which still
describes the unavailable service-managed Saga/SDK path.

Delegated commitments appear in `odin_resume` as open obligations until
closed, and the view's `delegation` section lists the non-retired sessions,
running turns and every latest turn that has finished while its commitment
is still open (`awaiting_executive`), with `review a delegated return` as
the recommended next action; no separate status call is needed to notice
outstanding delegated work. Refusals reach the executive as fixed codes
such as `project_already_has_active_session`, `turn_still_running`,
`limits_not_enforceable_on_harness`, `lineage_shared_requires_acceptance`,
`delegation_not_configured` or, under ADR-036, `workstream_label_required`,
`workstream_already_has_active_session`, `project_already_has_integration_owner`
and `workspace_in_use_by_active_session`.
`tests/test_delegation.py` covers the cycle with synthetic harness binaries
and real detached runners. Live Claude Code and Codex receipts are operator
evidence outside the repository; they are local-backend evidence without
isolation or Saga guarantees. Tools added after a conversation started are
visible only after that conversation exits and resumes.

### Executive admission paths

In delegated implementation mode the native intervention hook admits a
`Bash`, `Write`, `Edit` or `NotebookEdit` call on one of three paths
([ODIN-ADR-034](DECISIONS.md#odin-adr-034--bounded-executive-intervention-and-concise-working-context),
2026-10-22 amendment). Anything else is refused, and the refusal message
names the three paths. The paths inspect the literal tool input before the
shell runs it; they are a workflow boundary, not OS isolation.

1. **Read-only diagnostics, no permit.** One foreground `Bash` command, or a
   `|` pipe of commands, each from the allowlist: git read subcommands
   (`status`, `log`, `diff`, `show`, `rev-parse`, `rev-list`, `merge-base`,
   `ls-files`, `cat-file`, `blame`, `describe`, `cherry`, `shortlog`, `grep`,
   `for-each-ref`, `worktree list`, `stash list`, listing-only `branch`,
   `reflog` or `reflog show`, `remote -v`), optionally after `git -C <path>`
   or `--no-pager`; `ls`, `cat`, `head`, `tail` (not following), `wc`, `stat`,
   `du`, `df`, `find` without `-exec`, `-execdir`, `-delete`, `-ok`, `-okdir`,
   `-fprint*` or `-fls`, `grep` and `rg` without `--pre` (nor rg's
   `--hostname-bin` or `-z`), `jq`, `sort` without `-o` or
   `--compress-program`, `uniq` with at most one operand, `cut`, `ps`,
   `pgrep`, `date` without `-s`, `uptime`, `id`, `whoami`, `which`, `pwd`;
   `systemctl --user` `status`, `show`, `is-active`, `is-enabled`,
   `list-units` or `cat`; `journalctl --user` without follow, vacuum, rotate,
   flush, sync or cursor-file options; and the pilot launcher, the
   operator-owned `run` file beside the state directory, by absolute path,
   with `status`, `executive-status`, `development-status`, `usage-status` or
   `context-status` and only `--project`, `--loop`, `--stage` or
   `--native-session` values. `;`, `&`, backticks, `$(`, `<`, `>` and
   newlines are refused anywhere, even inside quotes. Unquoted `$`, globs,
   braces, parentheses, `#` and `!` are refused, as are
   `run_in_background`, a sandbox override and abbreviated long options that
   could select a refused one. When a memory directory is configured, git is
   refused if it would start inside it (through `-C` or the current
   directory), because the executive writes there without a permit and a
   planted git configuration could name a program for git to run. The hook
   decides this locally and never calls the service, so it still works when
   the service is down.
2. **Operator-registered scripts, no permit.** The operator registers a
   script by absolute path:

   ```bash
   ~/.local/state/odin-executive-pilot/run executive-register-script \
     --path /absolute/path/to/script.sh
   ~/.local/state/odin-executive-pilot/run executive-register-script \
     --path /absolute/path/to/script.sh --remove
   ```

   Registration refuses relative or non-normalized paths, symlinks in any
   component and non-regular files, and stores the path and SHA-256 in
   `executive-pilot/registered-scripts.json` (mode 0600). Editing the script
   requires registering it again. The hook admits a `Bash` call whose first
   word is a registered path whose current hash matches, followed by plain
   arguments and optional `>`, `>>`, `1>`, `2>` or `<` redirections to
   absolute paths, or `2>&1`. A redirection target may not be a registered
   script (bash reads a script as it runs, so appending to it would add
   commands), lie inside the state directory, contain a `.git` component or
   pass through a symlink. Other absolute targets the operator's user can
   write are allowed. Background execution is allowed. Registration refuses
   an interpreter or shell with the code `script_is_interpreter`, because a
   registered `python` or `sh` would admit any program in its arguments. It
   matches the basename of the path and of its real path (shells, `python*`,
   `node`, `perl*`, `ruby*`, `env`, `uv`/`uvx`, `npx`, `deno`, `bun` and
   command wrappers such as `xargs`, `sudo` or `timeout`, and tools with a
   command escape such as `find`, `sed`, `git`, `make`, editors and pagers,
   with any version suffix such as `python3.14`; a script named like one of
   these is refused too), then the file's identity (same inode, or same
   size and SHA-256) against the interpreter-named programs on `PATH` and in
   the standard directories, which catches a renamed copy of an ELF
   interpreter or a wrapper such as `npx-cli.js`. A script whose shebang names
   an interpreter is a script and is allowed. The hook repeats the check at
   admission, so an interpreter registered before this check is refused there
   (the call goes on to the permit path, and its refusal carries
   `script_is_interpreter`). A copy of an interpreter found on neither `PATH`
   nor the standard directories is not detected. There is no
   executive tool for registration, and the executive is instructed not to
   change registrations; a permit-admitted command runs with the same user
   authority and could, so this rests on the workflow, not on isolation.
   The hash is checked at `PreToolUse`; a change between that check and
   execution is not prevented.
3. **Exact permits.** `odin_intervention_begin` records a purpose and up to 32
   exact calls for up to 3600 seconds, only while no delegated turn is queued
   or running. A call's optional `uses` (1–20) creates that many single-use
   permits for the identical input. An optional `background: true` on a Bash
   call binds `run_in_background` into the input digest, so the same command
   in the foreground does not match it, and the reverse. A background permit
   closes at launch (state `launched`); it never becomes an unknown outcome,
   and the intervention view carries `background_outcome:
   not_observed_by_odin` with a note that Odin does not observe the outcome.
   Foreground permits keep the existing completion tracking, unknown-outcome
   blocking of new delegation and operator-only `intervention_reconcile`.
   A launched background command, like a background registered script, is
   invisible to the busy guard, so delegated turns may run while it does.

`Write` and `Edit` inside a configured memory directory (below) are also
admitted without a permit. Each admission without a permit appends one
record to `executive-pilot/intervention-audit.jsonl` (mode 0600): schema
version, time, path kind (`read_only`, `registered_script` or
`memory_directory`), tool, a keyed fingerprint (`input_hmac`, HMAC-SHA256 of
the executable input) and the key id. It holds no command text, file content
or tool-use identity. The key is 32 random bytes created on first use in
`executive-pilot/audit-key` (mode 0600, refused if it is a symlink, has
another owner, wider permissions or the wrong size), stays the same across
restarts, and is never logged, shown or exported; the key id is a truncated
SHA-256 of the key, so it names the key without revealing it. Without the
key, a short command cannot be confirmed by hashing guesses. Records written
before this change (schema version 1, a plain `input_digest`) stay as they
are; `executive-status` reports `intervention_audit` with keyed and unkeyed
counts and the current key id, and `audit_records` marks each record
`keyed: true` or `false`. Anyone who can read the state directory can read
the key, including the executive through a read-only `cat`, so this protects
exported or copied audit files, not against a local reader. Deleting the key starts a new key id; older
fingerprints can then no longer be compared. If the record or the key cannot
be written, the call is refused.

When a call matches no local path, the hook asks the service for a permit.
Its refusal code says why: `intervention_permit_required` (the service
answered and found no matching permit), `delegated_work_active`,
`script_is_interpreter`, another fixed code from the service, or
`intervention_not_admitted` when the service refused without one.
`intervention_service_unreachable` means the permit path did not answer and
`intervention_service_response_invalid` that its reply was malformed;
read-only diagnostics still work in both cases. A registered script inside a
configured memory directory can be replaced by Write/Edit; the hash check then
refuses it, except for a write that lands between the check and execution. The file is not rotated. Allowed programs still run as the operator:
git may run a configured pager, textconv or fsmonitor, the Claude Code shell
may apply the operator's own aliases or functions, and `git -C` into a
workspace reads that workspace's git configuration. The code is in
`python/odin/executive_admission.py` and the tests in
`tests/test_executive_admission.py`. Nothing changes until the operator
restarts the service on a head with this change and resumes the executive in
delegated mode.

### Optional executive memory directory

In delegated implementation mode the native intervention hook permits
`Write` and `Edit` outside the read-only and registered-script paths only
through a single-use permit. An operator may name one
directory where the executive writes its own memory notes without a permit:

```bash
~/.local/state/odin-executive-pilot/run executive-configure-memory-directory \
  --memory-directory /absolute/path/to/notes
```

The value must be an absolute existing directory, with no `..` component and
no symlink in any component. It must not be the repository, the state
directory, or a path containing either. Passing an empty value clears it. The
setting lives in `executive-pilot/memory-directory.json` in the state directory;
the hook re-checks it on every call, so it applies without a relaunch. A
`Write` or `Edit` whose real target lies strictly inside that directory, through
existing real directories, is allowed without a permit. Target paths that are
symlinks, relative, contain `..`, or resolve outside the directory fall through
to the normal permit path, and so does any target with a `.git` component.
`NotebookEdit` and all other tools are
unchanged, and `Bash` follows the admission paths above. The check is a path boundary, not an inode boundary: a hard link
inside the directory is not detected (creating one needs `Bash`, which stays
permit-gated). It runs at `PreToolUse`, so a concurrent change between the
check and the write is not prevented. Memory notes never replace Odin records
of commitments, approvals or acceptance.

### Service-only activation

After a reviewed head is fast-forwarded into the canonical checkout, the
operator can restart the Odin service on it without touching the executive:

```bash
~/.local/state/odin-executive-pilot/run executive-activate-service \
  --repository /path/to/canonical/checkout \
  --branch codex/odin-continuity-integration --head <full commit>
```

The action restarts only the `odin-executive-pilot-service` systemd user unit
through `systemctl --user restart`. It never addresses the executive session,
the telemetry unit or delegated workers directly. It refuses, without acting,
when the store shows a delegated turn queued, launching, running or
interrupting, a live intervention or admitted permit, or a claimed loop stage;
when the checkout is detached, on another branch, at another head or not clean;
when the unit has no main process; or when another activation holds the lease.
Delegated workers are children of the service; with the unit's default
`KillMode=control-group` a restart would stop them, which is why a running
turn blocks activation. The unit's kill mode is an assumption about the
external unit, not something Odin checks. Quiescence is read last, just before
the restart, through a read-only SQLite connection. It is a point-in-time
check: work admitted between the check and the restart is not prevented. A
`--head` that is not a full lowercase commit id, or an unbounded `--branch`,
is a usage error (exit 2) and leaves no record.

`serve` records its own process id, checkout revision and cleanliness in
`service-revision.json` in the state directory once its sockets are bound.
After the restart the action waits, up to `--activation-timeout` seconds
(default 60), for a new main process whose own report matches, and for the
service to answer. It then compares the reported revision with `--head`. Each
attempt leaves a private record in
`executive-pilot/service-activations/<ULID>.json` with the requested head,
the previous pid and revision, start and finish times, the outcome
(`refused`, `restarting`, `activated` or `failed`) and a typed reason. The
record is written before the restart, so an interrupted attempt stays visible
as `restarting`. `executive-status` reports `service_revision` and
`last_service_activation`. The exit status is 0 when activated, 2 when refused
and 1 on failure. A service started before this change writes no revision
report, so the first activation records the previous revision as `null`.
Restarting a transient `systemd-run` unit has been exercised only with a fake
unit controller, not against the live service.

## Executive restarts and the supervisor

[ODIN-ADR-039](DECISIONS.md#odin-adr-039--executive-self-restart-through-an-operator-run-supervisor)
lets the executive ask for its own restart, and an operator-run supervisor
carry it out. Nothing changes until the operator restarts the service on a
head with this change and starts the supervisor.

**Start it.** In the executive's Herdr tab, instead of `executive-start
--resume-session`, run:

```bash
~/.local/state/odin-executive-pilot/run executive-supervise
```

It refuses without a terminal, refuses a second supervisor for the same state
directory (`supervisor_already_running`) and needs the version 3 profile. It
launches Claude Code exactly as `executive-start --resume-session` does (the
first launch of a new session uses `--session-id`), as a child in the same
terminal, adding only turn-marker hooks to the inline settings. Use the
session as before. After a reboot, start only this command in the tab: Herdr
restores the shell, not the command, and systemd cannot host it because the
session needs a terminal.

**Restart.** The executive calls `odin_executive_restart` with a reason and a
new operation_id, then ends its turn. The service refuses with
`intervention_outcome_unknown`, `loop_stage_active`, `restart_request_pending`
or `restart_session_not_current`; delegated turns do not block. The supervisor
waits until the executive is idle (a Stop marker from this launch, no
background task reported, marker and transcript unchanged for 15 s), asks the
service to move the request to `stopping` (the service refuses it then if it
has become unsafe), sends SIGTERM to the Claude Code process and relaunches
through the normal start path. Staged changes (`executive-configure-model`,
`executive-configure-execution-role`, peer messaging, context window) apply
at that relaunch, and the same native session resumes. The outcome
(`restarted`, `failed` or `refused`, with timings, exit status and whether a
SessionEnd marker was seen) is recorded in history and reaches the executive
as a notice on the development channel; acknowledge it with `odin_loop_ack`.
`executive_restart_status` on the operator socket shows open and recent
requests.

**Stopping and crashes.** `/exit` with no pending request ends supervision,
and the supervisor exits too. A request left `stopping` or `relaunching` by a
supervisor that ended mid-restart is completed by the next supervisor's first
launch. An unexpected non-zero exit relaunches after
10, 30 and 90 s; a fourth crash within ten minutes stops supervision and
records `crash_limit`. If Claude Code does not exit within 60 s of SIGTERM,
the request fails with `stop_timeout` and the session keeps running; the
supervisor never kills it. If that session exits later, the supervisor treats
the exit as the delayed effect of its signal and relaunches without counting
a crash. Ctrl+C in the tab goes to Claude Code as before.
The supervisor journal, `executive-pilot/supervisor-journal.jsonl`, records
each step without content.

**The development-channel warning.** With the development loop enabled the
launch passes `--dangerously-load-development-channels`, and Claude Code
2.1.308 shows the "WARNING: Loading development channels" screen at every
interactive start where channels are on for the session. The answer is not
stored, so it is not a one-time acknowledgement, and no user setting skips it.
It is skipped only when channels are off for that session (an account gate or
entitlement), for a non-first-party provider or under a managed policy block.
A resume that did not show it most likely had channels off, so check the
channel before relying on loop delivery in that session. The supervisor never
answers it. If the relaunched session has not started within 120 s it
records `awaiting_operator_confirmation` and prints a line asking the operator
to answer the screen in the tab. An unattended restart therefore waits for
the operator whenever the screen appears. Moving the bridge to an approved
plugin channel (`--channels` with a managed `allowedChannelPlugins` entry)
would avoid it but needs plugin packaging and root-owned managed settings;
that is not done.

**Live acceptance (operator).** Synthetic tests use a fake Claude binary. The
following have not been observed and are the operator's to check at
activation: that SIGTERM ends a real idle session cleanly with SessionEnd
hooks (read from the 2.1.308 code), that the marker hooks fire as described
(including for channel-delivered and Remote Control turns), that the resumed
session shows the staged change, and how the warning screen behaves on the
first supervised relaunch.

### Deploying accepted changes

A restart only loads executive-side changes. Most improvements live in the
service, so the supervisor also deploys
([ODIN-ADR-039](DECISIONS.md#odin-adr-039--executive-self-restart-through-an-operator-run-supervisor),
items 5–9). Nothing here is active until the one-time migration below is
done and the supervisor runs.

**Flow.** An accepted change is merged by the integration owner. The
executive then calls `odin_runtime_deploy` with the integration branch's head
and ends its turn. The service accepts only that head from a clean checkout
on that branch. It refuses with `deploy_not_configured`,
`deploy_request_pending`, `deploy_head_not_integration_head`,
`deploy_tree_dirty`, `deploy_checkout_not_on_integration_branch`,
`deploy_checkout_unreadable`, `deploy_head_already_current`,
`deploy_not_migrated` (no `current` yet), `restart_request_pending` or a
restart safety code. The code cannot tell
whether a head was accepted; never deploy an unaccepted head.

**Drain.** From the request until the service restart, no new delegated turn
or evaluator job starts: queued work stays queued, running work finishes, and
nothing is killed. `executive_restart_status` on the operator socket shows
`drain` with `waiting_for` (running turns, running evaluator jobs, live
interventions, claimed stages) and `queued_turns_held`. The drain ends at
`drain_timeout_seconds` (default 3600) even without a supervisor, and the
request then fails with `drain_timeout`. Evaluator jobs in `unknown` are
listed but do not hold the drain, since they need operator reconciliation.
A `deploying` step that stops reporting for 900 s is failed with
`supervisor_lost`.

**What the supervisor does.** Once nothing is running and the executive is
idle, it stops the executive (as for a restart), exports the commit to
`deploy/<revision>`, switches `deploy/current`, restarts
`odin-executive-pilot-service` through the same activation logic as
`executive-activate-service` (an activation record under
`executive-pilot/service-activations/`), and checks that the socket
answers, the service reports the new revision and a status call works. On
failure it switches `current` back and restarts the service on the previous
revision (`rolled_back`; `rollback_failed` if that also fails, after
pointing `current` at what the service reports; `rollback_unavailable` with
no previous copy, which removes `current`). A refused activation switches
`current` back without any restart. An executive that is busy again for
300 s after the deploy began fails it with `executive_not_idle`. Any
unexpected error records `deploy_error` and the executive is still
relaunched. It then restarts `odin-executive-telemetry`, and re-execs itself,
handing over its locked lease, so the deployed code supervises, and resumes
the executive. The executive gets a notice
saying `deployed`, `rolled_back` or `failed`, with timings. The deploy record,
history events (`executive.deploy_*`) and the supervisor journal keep each
step.

**Configure (operator, once):**

```bash
~/.local/state/odin-executive-pilot/run executive-configure-deploy \
  --repository /home/david/.codex/worktrees/23e7/odin \
  --branch codex/odin-continuity-integration --keep 3 --drain-timeout 3600
```

`--deploy-root` defaults to `~/.local/state/odin-executive-pilot/deploy`
(created 0700; it must lie outside the repository and the state directory).

### One-time migration to pinned deploy copies

Today the runtime reads code from the live integration worktree, so a merge
silently changes code for any newly started hook, CLI or bridge process while
the service runs old code. These settings were read on 2026-10-22:

| Component | Where | Current code path |
|---|---|---|
| Service unit | `~/.config/systemd/user/odin-executive-pilot-service.service` | `WorkingDirectory=/home/david/.codex/worktrees/23e7/odin`, `Environment=PYTHONPATH=/home/david/.codex/worktrees/23e7/odin/python`, `ExecStart=.../venv/bin/python -m odin --state .../state serve --executive-project 01M5BAGF5757NS4MA7PKANFTRH` |
| Telemetry unit | `~/.config/systemd/user/odin-executive-telemetry.service` | the same `WorkingDirectory` and `PYTHONPATH`; `ExecStart=... usage-watch --request .../telemetry/watch.json` |
| Running units | `/run/user/1000/systemd/transient/` | both units currently run as transient `systemd-run` units that shadow the files above, with the same worktree environment |
| Launcher | `~/.local/state/odin-executive-pilot/run` | `export PYTHONPATH=/home/david/.codex/worktrees/23e7/odin/python` |
| Status line | `~/.local/state/odin-executive-pilot/claude-login/settings.json`, `statusLine.command` | `/usr/bin/env PYTHONPATH=/home/david/.codex/worktrees/23e7/odin/python .../venv/bin/python -m odin.usage_statusline ...` |
| Executive hooks and MCP bridge | built at each executive launch from the launcher's code | intervention hook: `/usr/bin/env PYTHONPATH=/home/david/.codex/worktrees/23e7/odin/python .../venv/bin/python -m odin.executive_intervention_hook --state ... --project ... --session-id ...`; the loop Stop hook, the turn-marker hooks and the MCP bridge use the same `PYTHONPATH` |

Steps, with the operator present, at a quiescent point, on a head that
contains this change (call it `HEAD`). The worker documents them; it does not
perform them.

1. Configure deploys (above), then export the head and create `current`
   without restarting anything:
   `run executive-deploy-prepare --head HEAD`.
2. Launcher: change its export to
   `PYTHONPATH=/home/david/.local/state/odin-executive-pilot/deploy/current/python`.
3. Unit files: in both units set
   `WorkingDirectory=/home/david/.local/state/odin-executive-pilot/deploy/current`
   and
   `Environment=PYTHONPATH=/home/david/.local/state/odin-executive-pilot/deploy/current/python`.
4. Replace the transient units: `systemctl --user stop
   odin-executive-telemetry odin-executive-pilot-service`, then
   `systemctl --user daemon-reload`, then `systemctl --user start
   odin-executive-pilot-service odin-executive-telemetry` (and `enable` them
   if they should start at login). Until the transient units are gone, a
   restart re-creates their worktree environment and the split-version state
   remains.
5. Status line: change the `PYTHONPATH=` in `statusLine.command` to
   `.../deploy/current/python`. It runs per refresh, so it follows `current`.
6. Executive: exit the running session and start
   `run executive-supervise` in its tab. The hooks and bridge are rebuilt from
   the launcher's code at that launch. Because `ROOT` is resolved, they name
   `deploy/<HEAD>/python`, the revision that launched them, and keep it until
   the next restart, which every deploy performs.
7. Check: `run executive-status` (the configuration's `repository_root` is
   still the checkout), `~/.local/state/odin-executive-pilot/state/service-revision.json` reports
   `HEAD` with `clean: null` (a deployed copy has no git metadata), and
   `systemctl --user show -p Environment odin-executive-pilot-service` shows
   `current`.

To undo, restore the four edited files and restart the units. After the
migration, `executive-activate-service` checks the running revision against
its `--head`. Use a deploy instead, unless `--head` equals `current`.

**Live acceptance (operator).** The first real deploy (by hand, operator
present) and a forced rollback, for example deploying a head whose service
fails to start. Also observe the drain holding a queued turn, the
re-exec'd supervisor taking the lease, and the resumed executive receiving
the deploy notice. The tests use a fake service unit and a fake Claude
binary.

## Repository evidence and the retained read-only profile

Version 3 already exposes native file tools. The following version 2 upgrade
is retained for an operator who specifically selects read-only access; it is
not a prerequisite or restriction on the development profile. The committed
snapshot import described below works independently of native tool access.

The original profile intentionally exposes only five `odin_*` MCP tools. It
does not hide the native read tools in a deferred pool: they were excluded
from the launch. An empty memory snapshot means no sources have been
imported for the project. The original prepared conversation workspace is
separate from the source checkout and is intentionally empty; version 3 uses the
checkout itself.

For native reads, exit the Claude conversation first, then resume it with
the workstation launcher:

```bash
~/.local/state/odin-executive-pilot/run executive-start --resume-session --repository-reads
```

This upgrades the idle profile to version 2 and preserves the saved native
session ID, login and records. Later resumes retain the read tools without
repeating `--repository-reads`. A running session refuses the upgrade; no
second process is started against its credential lineage. The equivalent
repository command is:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start \
  --resume-session --repository-reads
```

The configured repository path appears in `executive-status` and the native
prompt. For this pilot checkout it is
`/home/david/.codex/worktrees/23e7/odin`; design documents are under its
`docs/` directory. Use absolute paths in the read tools. Native reads show
current checkout contents, including any uncommitted edits. They are not
automatically saved as Odin evidence.

The version 2 launch uses Claude Code's restricted mode and an explicit
additional repository directory. It enables only `Read`, `Glob` and `Grep` in addition
to the existing MCP bridge, with Read exclusions for private files and the
runtime/credential directories. These are harness permission controls,
not OS isolation. Search exclusions are best effort; verify actual native
behavior separately and use the committed snapshot path for bounded,
revision-pinned evidence. Shell, write, edit, child-agent and web tools
remain excluded.

To populate Odin memory, run an operator import while the local service is
running. Use the project ID from `executive-status`:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" repository-import \
  --project PROJECT_ULID --repository "$PWD"
```

Run this command from the repository root. It imports selected first-party
documentation, code, schemas and tests from committed `HEAD`, reading Git
objects rather than working-tree files. It excludes hidden/private paths,
untracked files, symlinks, submodules, frozen history, pinned peer contracts
and dated research. The service validates each bounded batch on its recorded
operator path; this import is not exposed as a model tool.

The memory snapshot exposes a repository catalog. Fable can read that source
with `odin_read_evidence`, follow its page references, then request the exact
source IDs and revisions for files/chunks. The catalog records the selected
commit, coverage and snapshot-only freshness. Importing the same snapshot
again is safe after an interrupted request; incomplete batches remain
visible as incomplete. Import again after a later commit to update the
catalog. Old exact revisions remain historical evidence; a later working
tree edit does not refresh them. Repository text becomes attributed source
evidence without inferred statements or completed-work claims.

To test both paths, ask Fable to identify the repository catalog commit,
read one design-document source and its implementation source through Odin,
then compare those with the corresponding current files using native Read.
It should state which evidence is committed and which reflects the current
checkout, and record any discrepancy as an unverified report/proposal.

## Test the first conversation

Start with a small project brief whose disclosure to the selected provider
the operator intends. Ask Fable to read its project snapshot and explain
which obligations, evidence and source coverage are available. An empty
project should be reported as empty; it should not invent completed work or
infer that peer feeds are connected.

For version 3, ask for an evidence-backed discrepancy, an implemented fix,
and an appropriate test, then inspect the resulting diff and test output.
That loop can run with the native development tools. Ask for a progress
report or proposal when useful; service readback still marks that record
`unverified` and `applied: false`. Those fields describe the report record,
not a prohibition on separately authorized native implementation. The
reviewed-correction component remains a separate managed path and does not
automatically consume pilot reports or verify native edits.

| Acceptance observation | Evidence required |
|---|---|
| Requested model is available | A native response with the observed model recorded separately from the requested configuration |
| Remote dialogue works | A message sent from the remote device and its reply in the same native session |
| Project scope holds | A valid local snapshot and refusal of foreign-project/actor/tool substitution |
| Reports persist | Unverified report/proposal readback after reconnect or service restart; no canonical completion or policy change |
| Direct control works | Operator interrupt/exit stops the native session without waiting for a model decision |
| Resume preserves continuity | Same intended session resumes, can read current service state, and does not duplicate or claim application of prior reports |
| Development tools are visible | After version 3 resume, inspect the native tool manifest and perform a real checkout read plus an operator-requested edit/test; observe native agents separately if used |
| Repository evidence persists | Catalog discovery and exact source reads show the selected commit after service restart; no live-update claim is made |
| Selected profile is active | Status distinguishes pending and active configuration; the resumed process uses the same session identity, real checkout and intended environment. Version 2 read-boundary checks apply only when that older profile is selected |
| Failure is visible | Service outage, model refusal, missing login or Remote Control failure is distinguishable from success |

These are pilot checks, not new completed AC scenarios. Keep live receipts
outside the repository and avoid committing conversation, account or
credential material. Synthetic tests of launch construction and the MCP
boundary establish only the cases exercised. Full I2/I3, Saga Phase B,
service-managed children, peer feeds and production credential/process
isolation remain separate gates; ordinary version 3 native agents do not
wait on that managed-child implementation.

## Supported transport and observed CLI

On 2026-10-19, a read-only CLI probe observed Claude Code **2.1.296** and
the native `--remote-control` option. Official documentation lists
`claude-fable-5-1` as a supported explicit model ID. These checks establish
CLI support, not entitlement or successful inference.
[CLI reference](https://code.claude.com/docs/en/cli-reference),
[model configuration](https://code.claude.com/docs/en/model-config).

Remote Control requires eligible subscription authentication and a direct
Anthropic endpoint; API-key and setup-token authentication do not provide
this channel. Use the interactive `--remote-control` flag: the server-mode
subcommand does not preserve the same launch settings. The native process
must remain running, and its remote conversation is synchronized through
Anthropic. The launcher does not accept login, pairing or billing dialogs
on the operator's behalf.
[Remote Control documentation](https://code.claude.com/docs/en/remote-control).

The implementation intentionally distinguishes requested configuration,
local process observations and live acceptance. Native model selection can
change, and Remote Control can fail independently of the conversation.
Recheck the observed state during a pilot rather than treating the launch
arguments as proof of continued behavior.
