# Fable executive conversation pilot

Status: bounded implementation under
[ODIN-ADR-024](DECISIONS.md#odin-adr-024--native-fable-executive-conversation-pilot)
and [ODIN-ADR-025](DECISIONS.md#odin-adr-025--executive-repository-evidence-access),
2026-10-19. Preparation and component checks do not establish a live login,
Fable entitlement, Remote Control connection or production readiness.

This pilot gives the operator a persistent conversation with Fable in native
Claude Code, with scoped access to Odin's local continuity records. It is a
first place to test executive behavior and collect improvement proposals.
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
| Repository evidence | Opt-in native `Read`, `Glob`, `Grep` for current checkout files; operator-imported committed snapshots through the existing memory tools |
| Progress | Record and read back explicitly unverified reports; a report does not close a commitment or verify an outcome |
| Improvement | Record unapplied proposals for later evidence, review and regression work |
| Authority | `fable-executive` is a coordinator bound by the service to one project; model tool arguments cannot select a different principal |
| Execution | No Saga worker launch, native child dispatch, shell or file-write tools, approval/grant tool, or policy/repository mutation through the bridge |
| Runtime | An operator-launched local pilot; the authenticated homelab/workstation daemon and full SDK lifecycle remain future work |

There is no service-enforced model cost or turn budget in this pilot. Native
account limits and operator control are not evidence of Odin budget
enforcement; `executive-status` reports this boundary explicitly.

The bridge does not yet let Fable create or edit canonical commitments.
Those records remain in Odin's existing service paths. Ordinary chat stays
in Claude Code's native transcript; it is not automatically captured into
Odin memory, interpreted as progress, or recorded as an authenticated
operator command. A statement relayed by the model is a model report.

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

The executive uses the dedicated `executive.sock` service binding and its
own prepared workspace. Native login, workspace-trust and Remote Control
dialogs must be completed in Claude Code. Follow the session URL or QR code
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

The launcher selects the workspace, dedicated login, tools and saved session;
no `cd` is needed. Running bare `claude` from that workspace bypasses those
settings and can load the development profile's hooks. An error such as
`heimdall: json: unknown field "scratchpad_dir"` from that ordinary profile
is a separate hook compatibility issue, not an Odin resume error. The Odin
launcher disables inherited hooks. A repeated `executive-start` now prints
the explicit resume instruction without a Python traceback.

If a launch ended before Claude created a resumable session, or the operator
intends to start a fresh conversation, allocate a new native ID explicitly:

```bash
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-new-session
.venv/bin/python -m odin --state "$ODIN_PILOT_STATE" executive-start
```

The reset requires the launch/credential locks to be free, archives launch
metadata and retains native transcripts. It does not erase project records
or recover a failed operation by silently replaying it.

## Enable repository evidence

The original profile intentionally exposes only five `odin_*` MCP tools. It
does not hide the native read tools in a deferred pool: they were excluded
from the launch. An empty memory snapshot means no sources have been
imported for the project. The prepared conversation workspace is separate
from the source checkout and is intentionally empty.

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

The launch uses Claude Code's restricted mode and an explicit additional
repository directory. It enables only `Read`, `Glob` and `Grep` in addition
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

Then ask for a progress report and an improvement proposal, each with a
short explanation of its basis. Read them back from the service and check
that they remain `unverified` and `applied: false`. The first loop is:
operator test, recorded observation/proposal, bounded implementation change,
regression check, then another operator test. Proposals are not executable
instructions. The existing reviewed-correction component is a later path
for evidenced changes, not an automatic consumer of these pilot reports.

| Acceptance observation | Evidence required |
|---|---|
| Requested model is available | A native response with the observed model recorded separately from the requested configuration |
| Remote dialogue works | A message sent from the remote device and its reply in the same native session |
| Project scope holds | A valid local snapshot and refusal of foreign-project/actor/tool substitution |
| Reports persist | Unverified report/proposal readback after reconnect or service restart; no canonical completion or policy change |
| Direct control works | Operator interrupt/exit stops the native session without waiting for a model decision |
| Resume preserves continuity | Same intended session resumes, can read current service state, and does not duplicate or claim application of prior reports |
| Repository tools are visible | After profile upgrade/resume, native `Read`, `Glob`, `Grep` appear and a read of the configured checkout succeeds |
| Repository evidence persists | Catalog discovery and exact source reads show the selected commit after service restart; no live-update claim is made |
| Read boundaries hold | Actual native checks refuse out-of-scope/private reads and keep shell/edit tools unavailable; tests of launch arguments alone are insufficient |
| Failure is visible | Service outage, model refusal, missing login or Remote Control failure is distinguishable from success |

These are pilot checks, not new completed AC scenarios. Keep live receipts
outside the repository and avoid committing conversation, account or
credential material. Synthetic tests of launch construction and the MCP
boundary establish only the cases exercised. Full I2/I3, Saga Phase B,
native children, peer feeds and production credential/process isolation
remain separate gates.

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
