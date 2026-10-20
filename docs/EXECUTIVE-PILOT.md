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
| Delegation | Six `odin_delegation_*` tools under ADR-027 open one accountable local-backend session per project, assign owned commitments, run detached Claude Code or Codex turns, send follow-ups, collect unverified returns and record executive acceptance; no Saga launch, approval or grant |
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
3 does not load them or pass an overriding settings file. These capabilities
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
environment plus those settings. Pointing workers at the executive's own
dedicated login shares that credential lineage between the executive and
its workers; this is an interim operator choice while X-12 remains open, not
managed credential isolation.

The cycle, with every mutating call carrying a fresh ULID `operation_id`
that is safe to replay with identical arguments:

1. `odin_delegation_session` `create` with harness, workspace, briefing and
   options opens the project's one active session (a `PlanningSession`,
   binding and host `Environment` record) and makes it the planning owner.
2. `odin_delegation_assign` records an open `Commitment` with acceptance
   criteria and a `backend: local` `Assignment`, and queues the first turn.
   Claude Code turns pass `--max-turns` and `--max-budget-usd`; Codex offers
   no such options, so an assignment there requires
   `allow_unenforced_limits`. Odin records limits and reported usage; it
   enforces no ceiling.
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
   commitments left by a retired one with a new ownership generation.

Observed on 2026-10-20 with Claude Code 2.1.303: a `-p` worker under
`permission_mode: acceptEdits` can edit files but every shell command returns
"This command requires approval", so a worker that must run tests needs
`bypassPermissions` (the launcher then adds `--dangerously-skip-permissions`)
or the executive runs the checks in the worker's workspace itself before
accepting. Codex workers run under the configured sandbox (`read-only` or
`workspace-write`) and report usage without cost; their native thread id is
known only after the first turn returns.

Delegated commitments appear in `odin_resume` as open obligations until
closed. Refusals reach the executive as fixed codes such as
`project_already_has_active_session`, `turn_still_running`,
`limits_not_enforceable_on_harness` or `delegation_not_configured`.
`tests/test_delegation.py` covers the cycle with synthetic harness binaries
and real detached runners. Live Claude Code and Codex receipts are operator
evidence outside the repository; they are local-backend evidence without
isolation or Saga guarantees. Tools added after a conversation started are
visible only after that conversation exits and resumes.

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
