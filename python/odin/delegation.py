"""Local delegation sessions for the version 3 native development executive.

The executive opens one accountable orchestration session per project, assigns
bounded work, sends follow-ups, inspects progress and collects returns. Work
runs in a non-interactive harness turn (`claude -p` or `codex exec`) executed
by a detached runner process; the service remains the only writer of Odin's
records and ingests the runner's spool. This is the D23.3 local backend under
ODIN-ADR-026/027: no isolation, limits only where the harness offers them, run
records kept by Odin's service, and no Saga guarantees. A worker return is a
report; acceptance is a separate, attributed executive action.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import uuid
from pathlib import Path

from .contracts import ALPHABET, ROOT, Contracts, canonical, identifier, strict_loads
from .native_peer import guidance, peer_name
from .store import Conflict, digest, now

HARNESSES = ("claude-code", "codex")
PROVIDERS = {"claude-code": "anthropic", "codex": "openai"}
ADAPTERS = {"claude-code": "claude-code-print", "codex": "codex-exec"}
# Capability evidence for each local adapter. "harness_option" means the
# harness exposes a command-line limit; Odin records the request and the
# harness's own accounting, and does not independently enforce the ceiling.
CAPABILITIES = {
    "claude-code": {
        "start": True,
        "resume": True,
        "inject_mid_turn": False,
        "interrupt": "signal",
        "budget": "harness_option",
        "iterations": "harness_option",
        "model_selection": True,
        "effort_selection": True,
        "transcript": "json_result_and_native_session_file",
        "profile_enforcement": "permission_mode_option",
    },
    "codex": {
        "start": True,
        "resume": True,
        "inject_mid_turn": False,
        "interrupt": "signal",
        "budget": "unavailable",
        "iterations": "unavailable",
        "model_selection": True,
        "effort_selection": False,
        "transcript": "jsonl_events_and_last_message_file",
        "profile_enforcement": "sandbox_option",
    },
}
ACTIVE_SESSION_STATES = ("starting", "active", "idle", "retiring")
RUNNING_TURN_STATES = ("queued", "launching", "running", "interrupting")
TERMINAL_TURN_STATES = ("returned", "failed", "interrupted", "lost")
PERMISSION_MODES = ("default", "acceptEdits", "plan", "dontAsk", "bypassPermissions")
SANDBOXES = ("read-only", "workspace-write", "danger-full-access")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
OPEN_COMMITMENT = "commitment_open_after_terminal_turn"
CLOSED_COMMITMENT_STATES = ("closed", "abandoned")
CLOSED_ASSIGNMENT_STATES = ("completed", "failed", "cancelled")
NOTICE_HEADER = (
    "NOTICE, not an assignment. Delegation turn {turn} of assignment {assignment} "
    "ended {state}. Do not call odin_loop_claim or odin_loop_ready for this message "
    "and do not execute or re-execute any stage because of it. Acknowledge it with "
    "odin_loop_ack notice_id={notice_id} and a stable operation_id so it stops being "
    "offered; acknowledgement records only that you saw it and grants no authority.\n\n"
)


def _limit_enforcement(capabilities, limits):
    """Report how each limit is handled; a budget nobody asked for is not one."""
    return {
        "budget": capabilities["budget"]
        if limits.get("budget_usd") is not None
        else "not_requested",
        "iterations": capabilities["iterations"],
    }


class DelegationRefused(Conflict):
    """A fixed, safe refusal code the bridge may relay verbatim."""


def _notice_id(value):
    """A deterministic ULID-shaped identity, so a re-observed outcome never repeats."""
    number = int(digest(value)[:32], 16)
    result = ""
    for _ in range(26):
        result = ALPHABET[number & 31] + result
        number >>= 5
    return result


def _turn_attention(turn):
    """The attention reason for one terminal turn outcome, or None."""
    if turn["state"] == "failed":
        return (
            "turn_timed_out"
            if (turn.get("result") or {}).get("timed_out")
            else "turn_failed"
        )
    if turn["state"] in ("interrupted", "lost"):
        return "turn_" + turn["state"]
    return None


def _commitment_open_after_turns(assignment, commitment, turns):
    """Open work with no turn left to report on it: someone has to decide."""
    return (
        bool(turns)
        and assignment["state"] not in CLOSED_ASSIGNMENT_STATES
        and commitment["state"] not in CLOSED_COMMITMENT_STATES
        and not any(t["state"] in RUNNING_TURN_STATES for t in turns)
    )


def _role(options):
    """Effective ADR-036 role; a session declaring neither field is legacy."""
    return options.get("role") or ("workstream" if options.get("workstream") else "integration_owner")


def _legacy(options):
    return options.get("workstream") is None and options.get("role") is None


WORKSTREAM_BRIEFING = (
    "You are a workstream session (workstream {workstream}). Work on your own "
    "branch in your own worktree. Never fast-forward, merge into or commit on the "
    "canonical checkout. Return a merge-ready head plus receipts; the executive "
    "assigns integration to the project's integration owner."
)


def _refuse(code):
    raise DelegationRefused(code)


def _same_path(left, right):
    try:
        return Path(left).resolve() == Path(right).resolve()
    except (OSError, RuntimeError):  # RuntimeError: symlink loops on 3.12
        return str(left) == str(right)


def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat") as handle:
            return handle.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def _runner_alive(pid, directory):
    """True only for a live runner process that belongs to this turn directory."""
    if not _pid_alive(pid):
        return False
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            cmdline = handle.read().split(b"\0")
    except OSError:
        return True  # Cannot verify identity; treat as alive conservatively.
    return b"odin.delegation_runner" in cmdline and str(directory).encode() in cmdline


def _kill_group(pid, signum):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.killpg(pid, signum)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _age_seconds(stamp):
    from datetime import datetime, timezone

    return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds()


RUNNER_GRACE_SECONDS = 15
DEADLINE_SLACK_SECONDS = 60


def _version(binary):
    try:
        completed = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return text[0][:120] if text else None


def load_config(state):
    path = Path(state) / "delegation.json"
    if not path.exists():
        return None
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise PermissionError("delegation configuration must be a private file")
    value = strict_loads(path.read_text())
    from .contracts import Contracts

    Contracts().validate("delegation-config", value)
    return value


def write_config(state, config):
    from .contracts import Contracts

    Contracts().validate("delegation-config", config)
    for root in config["workspace_roots"]:
        path = Path(root)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("workspace roots must be absolute existing directories")
        if path == ROOT or ROOT.is_relative_to(path) or path.is_relative_to(ROOT):
            raise ValueError("workspace roots must not contain or be the checkout")
    for name, harness in config["harnesses"].items():
        if not os.access(harness["binary"], os.X_OK):
            raise ValueError(f"{name} binary is not executable")
        if name == "claude-code":
            directory = Path(harness["config_dir"])
            if not directory.is_dir() or directory.stat().st_mode & 0o077:
                raise ValueError("claude-code config_dir must be a private directory")
    path = Path(state) / "delegation.json"
    temporary = path.with_name(path.name + ".new")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(canonical(config) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _cost_deltas(harness, turns):
    """Map turn id to its cost delta, or None where the cost is unknown.

    A claude-code turn reports the inclusive cost of its resumed native session,
    so each turn contributes the increase over the previous figure seen for the
    same native session. Other harnesses report per-turn costs as-is.
    """
    deltas = {}
    previous = {}
    for turn in sorted(turns, key=lambda t: t["seq"]):
        result = turn.get("result")
        if not result:
            continue
        cost = result.get("cost_usd")
        if cost is None:
            deltas[turn["id"]] = None
            continue
        if harness == "claude-code":
            key = result.get("native_session_id")
            if key is None:
                key = turn.get("native_session_id")
            if key in previous and cost >= previous[key]:
                delta = cost - previous[key]
            else:
                delta = cost
            previous[key] = cost
        else:
            delta = cost
        deltas[turn["id"]] = round(float(delta), 6)
    return deltas


class Delegation:
    def __init__(self, store, state, config=None, *, python_executable=None):
        store._core()
        self.store = store
        self.state = Path(state)
        self.config = config
        self.python = python_executable or sys.executable
        self.spool = self.state / "delegations"
        self._children = []
        # Probe harness versions once at service start, not inside requests.
        self.versions = (
            {name: _version(h["binary"]) for name, h in config["harnesses"].items()}
            if config
            else {}
        )
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS delegation_turns
              (id TEXT PRIMARY KEY, session TEXT NOT NULL, assignment TEXT NOT NULL,
               project TEXT NOT NULL, seq INTEGER NOT NULL, state TEXT NOT NULL,
               body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS delegation_sessions
              (id TEXT PRIMARY KEY, project TEXT NOT NULL, options TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS delegation_notices
              (id TEXT PRIMARY KEY, project TEXT NOT NULL, assignment TEXT NOT NULL,
               turn TEXT NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL);
        """)

    # -- configuration and environment ------------------------------------

    def enabled(self):
        return self.config is not None

    def _harness(self, name):
        if not self.enabled():
            _refuse("delegation_not_configured")
        if name not in self.config["harnesses"]:
            _refuse("harness_not_configured")
        return self.config["harnesses"][name]

    def _executive_config_dir(self):
        """The running executive's own login directory, when this host has one."""
        manifest = self.state / "executive-pilot" / "manifest.json"
        try:
            value = strict_loads(manifest.read_text())
            return Path(value["config_dir"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _lineage(self, name):
        """Credential lineage facts for a harness: lease path, file, sharing.

        Ownership is enforced by the runner through the same `.odin-lineage.lock`
        flock the executive runtime holds; labels alone prove nothing.
        """
        harness = self._harness(name)
        policy = self.config.get("lineage_policy", "exclusive")
        if name == "claude-code":
            home = Path(harness["config_dir"])
            executive = self._executive_config_dir()
            operator_logins = [Path.home() / ".claude"]
            if os.environ.get("CLAUDE_CONFIG_DIR"):
                operator_logins.append(Path(os.environ["CLAUDE_CONFIG_DIR"]))
            if executive is not None and _same_path(home, executive):
                shared_with = "executive"
                lock = str(home / ".odin-lineage.lock")
            elif any(_same_path(home, login) for login in operator_logins):
                # The operator's own development login (CLAUDE.md): never a
                # worker lineage, and never a place Odin creates lease files.
                shared_with = "operator-claude-login"
                lock = None
            else:
                shared_with = None
                lock = str(home / ".odin-lineage.lock")
            credential = str(home / ".credentials.json")
        elif harness.get("codex_home"):
            home = Path(harness["codex_home"])
            shared_with = None
            lock = str(home / ".odin-lineage.lock")
            credential = str(home / "auth.json")
        else:
            home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
            shared_with = "operator-codex-login"
            lock = None  # Never create lease files inside the operator's own login.
            credential = str(home / "auth.json")
        return {
            "policy": policy,
            "shared_with": shared_with,
            "lock": lock,
            "credential_file": credential,
            "lease_enforced": lock is not None,
        }

    def _workspace(self, value):
        path = Path(value)
        if not path.is_absolute():
            _refuse("workspace_must_be_absolute")
        if not path.is_dir():
            _refuse("workspace_missing")
        resolved = path.resolve()
        if not any(
            resolved.is_relative_to(Path(root).resolve())
            for root in self.config["workspace_roots"]
        ):
            _refuse("workspace_outside_configured_roots")
        return str(resolved)

    def _environment_record(self):
        host = socket.gethostname()
        existing = [r for r in self.store.records("Environment") if r["host"] == host]
        harnesses = []
        lineages = []
        for name, harness in self.config["harnesses"].items():
            version = self.versions.get(name)
            harnesses.append({"name": name, "version": version or "unknown"})
            lineages.append(
                {
                    "ref": harness["credential_ref"],
                    "mode": "subscription",
                    "refresher": harness["refresh_owner"],
                }
            )
        stamp = now()
        body = {
            "host": host,
            "host_incarnation": 1,
            "probed_at": stamp,
            "probe_version": "delegation-1",
            "harnesses": harnesses,
            "herdr": None,
            "isolation": {"sandbox": None, "planner_workspace": False},
            "surfaces": [],
            "sensors": [],
            "credential_lineages": lineages,
        }
        if existing:
            record = existing[-1]
            unchanged = all(
                record[key] == body[key]
                for key in ("harnesses", "credential_lineages", "isolation")
            )
            if unchanged:
                return record
            updated = record | body | {"rev": record["rev"] + 1, "updated_at": stamp}
            self.store._put(updated, record["rev"])
            return updated
        record = {
            "schema_version": 1,
            "record_type": "Environment",
            "id": identifier(),
            "rev": 1,
            "created_at": stamp,
            "updated_at": stamp,
        } | body
        self.store._put(record, 0)
        return record

    # -- record lookups ----------------------------------------------------

    def _project(self, project):
        record = self.store.get(project)
        if record["record_type"] != "Project":
            raise Conflict("project reference mismatch")
        return record

    def _session(self, session_id, project):
        try:
            record = self.store.get(session_id)
        except KeyError:
            _refuse("unknown_session")
        if (
            record["record_type"] != "PlanningSession"
            or record["project"] != project
            or record["adapter"] not in ADAPTERS.values()
        ):
            _refuse("unknown_session")
        return record

    def _assignment(self, assignment_id, project):
        try:
            record = self.store.get(assignment_id)
            commitment = self.store.get(record["commitment"])
        except KeyError:
            _refuse("unknown_assignment")
        if (
            record["record_type"] != "Assignment"
            or record["backend"] != "local"
            or commitment["project"] != project
        ):
            _refuse("unknown_assignment")
        return record, commitment

    def _active_sessions(self, project):
        return [
            record
            for record in self.store.records("PlanningSession")
            if record["project"] == project
            and record["adapter"] in ADAPTERS.values()
            and record["state"] in ACTIVE_SESSION_STATES
        ]

    def _check_identity(self, project, identity, workspace, *, exclude=None):
        """ADR-036 uniqueness over the project's other active sessions."""
        others = [
            (record, self._options(record["id"]))
            for record in self._active_sessions(project)
            if record["id"] != exclude
        ]
        if _legacy(identity) and any(_legacy(options) for _, options in others):
            _refuse("project_already_has_active_session")
        workstream = identity.get("workstream")
        if workstream and any(options.get("workstream") == workstream for _, options in others):
            _refuse("workstream_already_has_active_session")
        if _role(identity) == "integration_owner" and any(
            _role(options) == "integration_owner" for _, options in others
        ):
            _refuse("project_already_has_integration_owner")
        if workspace and any(
            options.get("workspace") and _same_path(options["workspace"], workspace)
            for _, options in others
        ):
            _refuse("workspace_in_use_by_active_session")

    def _turns(self, *, session=None, assignment=None, project=None):
        rows = self.store.db.execute(
            "SELECT body FROM delegation_turns WHERE (? IS NULL OR session=?) "
            "AND (? IS NULL OR assignment=?) AND (? IS NULL OR project=?) ORDER BY id",
            (session, session, assignment, assignment, project, project),
        )
        return [strict_loads(row[0]) for row in rows]

    def _turn(self, turn_id):
        row = self.store.db.execute(
            "SELECT body FROM delegation_turns WHERE id=?", (turn_id,)
        ).fetchone()
        if row is None:
            _refuse("unknown_turn")
        return strict_loads(row[0])

    def _save_turn(self, turn):
        self.store.contracts.validate("delegation-turn", turn)
        self.store.db.execute(
            "INSERT INTO delegation_turns VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET state=excluded.state, body=excluded.body",
            (
                turn["id"],
                turn["session"],
                turn["assignment"],
                turn["project"],
                turn["seq"],
                turn["state"],
                canonical(turn),
            ),
        )

    def _put_session(self, session, **changes):
        updated = session | changes | {"rev": session["rev"] + 1, "updated_at": now()}
        self.store._put(updated, session["rev"])
        return updated

    # -- session lifecycle -------------------------------------------------

    def open_session(self, payload, *, project, actor, operation):
        harness = self._harness(payload["harness"])
        workspace = self._workspace(payload["workspace"])
        workstream, role = payload.get("workstream"), payload.get("role")
        if role == "workstream" and not workstream:
            _refuse("workstream_label_required")
        identity = {"workstream": workstream, "role": role}
        self._check_identity(project, identity, workspace)
        model = payload.get("model") or harness.get("default_model")
        if payload["harness"] == "claude-code" and not model:
            _refuse("model_required")
        claude_only = ("subagent_model", "subagent_model_force", "auto_compact_window_tokens", "native_peer_messaging")
        if payload["harness"] != "claude-code" and any(payload.get(key) is not None for key in claude_only):
            _refuse("claude_options_unsupported_by_harness")
        subagent_model = payload.get("subagent_model", harness.get("default_subagent_model"))
        subagent_model_force = payload.get("subagent_model_force", harness.get("default_subagent_model_force", False))
        auto_compact_window = payload.get("auto_compact_window_tokens", harness.get("default_auto_compact_window_tokens"))
        native_peer_messaging = payload.get("native_peer_messaging", harness.get("default_native_peer_messaging", False))
        if type(native_peer_messaging) is not bool:
            _refuse("invalid_native_peer_messaging")
        if native_peer_messaging:
            version = self.versions.get("claude-code") or ""
            match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
            if match is None or tuple(map(int, match.groups())) < (2, 1, 224):
                _refuse("native_peer_messaging_unsupported_by_claude_version")
        if type(subagent_model_force) is not bool:
            _refuse("invalid_subagent_model_force")
        if subagent_model_force and not subagent_model:
            _refuse("subagent_model_required_for_force")
        if subagent_model_force:
            version = self.versions.get("claude-code") or ""
            match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
            if match is None or tuple(map(int, match.groups())) < (2, 1, 257):
                _refuse("subagent_model_force_unsupported_by_claude_version")
        if subagent_model is not None and (not isinstance(subagent_model, str) or not 1 <= len(subagent_model) <= 128):
            _refuse("invalid_subagent_model")
        if auto_compact_window is not None and (type(auto_compact_window) is not int or not 100000 <= auto_compact_window <= 1000000):
            _refuse("invalid_auto_compact_window_tokens")
        lineage = self._lineage(payload["harness"])
        if lineage["shared_with"] and lineage["policy"] != "shared_accepted":
            _refuse("lineage_shared_requires_acceptance")
        options = {
            "lineage": {
                key: lineage[key] for key in ("policy", "shared_with", "lease_enforced")
            },
            "workspace": workspace,
            "workstream": workstream,
            "role": role,
            "model": model,
            "subagent_model": subagent_model,
            "subagent_model_force": subagent_model_force,
            "auto_compact_window_tokens": auto_compact_window,
            "native_peer_messaging": native_peer_messaging,
            "effort": payload.get("effort"),
            "permission_mode": payload.get("permission_mode")
            or harness.get("default_permission_mode", "acceptEdits"),
            "sandbox": payload.get("sandbox")
            or harness.get("default_sandbox", "workspace-write"),
        }
        with self.store.transaction():
            project_record = self._project(project)
            environment = self._environment_record()
            stamp = now()
            session = {
                "schema_version": 1,
                "record_type": "PlanningSession",
                "id": identifier(),
                "rev": 1,
                "created_at": stamp,
                "updated_at": stamp,
                "project": project,
                "harness": payload["harness"],
                "adapter": ADAPTERS[payload["harness"]],
                "native_session_id": str(uuid.uuid4())
                if payload["harness"] == "claude-code"
                else None,
                "incarnation": 1,
                "state": "idle",
                "briefing": payload["briefing"],
                "budget_usd": payload.get("budget_usd"),
                "ownership_generation": 1,
                "profile": "planner",
                "auth": {
                    "mode": "subscription",
                    "credential_ref": harness["credential_ref"],
                    "refresh_owner": harness["refresh_owner"],
                },
            }
            self.store._put(session, 0)
            self.store.db.execute(
                "INSERT INTO delegation_sessions VALUES(?,?,?)",
                (session["id"], project, canonical(options)),
            )
            adopted = []
            for commitment in self.store.records("Commitment"):
                if commitment["project"] != project or commitment["state"] not in (
                    "open",
                    "blocked",
                ):
                    continue
                if commitment["owner"] is None:
                    continue
                owner = self.store.get(commitment["owner"])
                if (
                    owner["adapter"] in ADAPTERS.values()
                    and owner["state"] == "retired"
                    # ADR-036: a replacement adopts only its own workstream's work.
                    and self._options(owner["id"]).get("workstream") == workstream
                ):
                    self.store._put(
                        commitment
                        | {
                            "owner": session["id"],
                            "ownership_generation": commitment["ownership_generation"]
                            + 1,
                            "rev": commitment["rev"] + 1,
                            "updated_at": stamp,
                        },
                        commitment["rev"],
                    )
                    adopted.append(commitment["id"])
                    for assignment in self.store.records("Assignment"):
                        if assignment["commitment"] == commitment["id"] and assignment[
                            "state"
                        ] not in ("completed", "failed", "cancelled"):
                            self.store._put(
                                assignment
                                | {
                                    "owner": session["id"],
                                    "rev": assignment["rev"] + 1,
                                    "updated_at": stamp,
                                },
                                assignment["rev"],
                            )
            binding = None
            if session["native_session_id"]:
                binding = self._bind(session, environment, predecessor=None)
            if _role(options) == "integration_owner":
                # Workstream sessions never take the project's planning ownership.
                self.store._put(
                    project_record
                    | {
                        "interface_decision_owner": session["id"],
                        "rev": project_record["rev"] + 1,
                        "updated_at": stamp,
                    },
                    project_record["rev"],
                )
            self.store._history(
                "delegation.session",
                {
                    "action": "create",
                    "operation_id": operation,
                    "actor": actor,
                    "session": session["id"],
                    "project": project,
                    "harness": payload["harness"],
                    "workspace": workspace,
                    "workstream": workstream,
                    "role": _role(options),
                    "adopted_commitments": adopted,
                },
            )
        return self._session_view(session, options, adopted=adopted, binding=binding)

    def _bind(self, session, environment, *, predecessor):
        stamp = now()
        binding = {
            "schema_version": 1,
            "record_type": "SessionBinding",
            "id": identifier(),
            "rev": 1,
            "created_at": stamp,
            "updated_at": stamp,
            "subject": {"kind": "planning_session", "id": session["id"]},
            "harness": session["harness"],
            "provider": PROVIDERS[session["harness"]],
            "native_session_id": session["native_session_id"],
            "host": environment["host"],
            "incarnation": session["incarnation"],
            "state": "active",
            "environment": {"id": environment["id"], "rev": environment["rev"]},
            "capabilities": [
                name
                for name, value in CAPABILITIES[session["harness"]].items()
                if value is True or isinstance(value, str) and value != "unavailable"
            ],
            "workspace": None,
            "predecessor": predecessor,
        }
        self.store._put(binding, 0)
        return binding

    def _current_binding(self, session_id):
        bindings = [
            b
            for b in self.store.records("SessionBinding")
            if b["subject"] == {"kind": "planning_session", "id": session_id}
        ]
        return bindings[-1] if bindings else None

    def resume_session(self, payload, *, project, actor, operation):
        session = self._session(payload["session_id"], project)
        self._harness(session["harness"])
        if session["state"] == "retired":
            _refuse("session_retired")
        if payload.get("workstream") is not None or payload.get("role") is not None:
            _refuse("session_identity_fixed_at_create")
        options = self._options(session["id"])
        self._check_identity(project, options, options.get("workspace"), exclude=session["id"])
        self.reconcile()
        running = [
            t
            for t in self._turns(session=session["id"])
            if t["state"] in RUNNING_TURN_STATES
        ]
        if running:
            _refuse("turn_still_running")
        with self.store.transaction():
            environment = self._environment_record()
            previous = self._current_binding(session["id"])
            session = self._put_session(
                session, state="idle", incarnation=session["incarnation"] + 1
            )
            binding = None
            if session["native_session_id"]:
                if previous is not None and previous["state"] == "active":
                    self.store._put(
                        previous
                        | {
                            "state": "invalidated",
                            "rev": previous["rev"] + 1,
                            "updated_at": now(),
                        },
                        previous["rev"],
                    )
                binding = self._bind(
                    session,
                    environment,
                    predecessor=previous["id"] if previous else None,
                )
            project_record = self._project(project)
            if (
                _role(options) == "integration_owner"
                and project_record["interface_decision_owner"] != session["id"]
            ):
                self.store._put(
                    project_record
                    | {
                        "interface_decision_owner": session["id"],
                        "rev": project_record["rev"] + 1,
                        "updated_at": now(),
                    },
                    project_record["rev"],
                )
            self.store._history(
                "delegation.session",
                {
                    "action": "resume",
                    "operation_id": operation,
                    "actor": actor,
                    "session": session["id"],
                    "project": project,
                    "incarnation": session["incarnation"],
                },
            )
        return self._session_view(session, options, binding=binding)

    def stop_session(self, payload, *, project, actor, operation):
        session = self._session(payload["session_id"], project)
        if session["state"] == "retired":
            return self._session_view(session, self._options(session["id"]))
        signalled = []
        with self.store.transaction():
            for turn in self._turns(session=session["id"]):
                if turn["state"] in ("launching", "running"):
                    pid = (turn.get("runner") or {}).get("pid")
                    directory = self.spool / turn["session"] / turn["id"]
                    if pid and _runner_alive(pid, directory):
                        try:
                            os.kill(pid, signal.SIGTERM)
                            signalled.append(turn["id"])
                        except OSError:
                            pass
                    self._save_turn(
                        turn
                        | {
                            "state": "interrupting",
                            "stop_reason": payload.get("reason"),
                            "interrupt_requested_at": now(),
                        }
                    )
            session = self._put_session(session, state="retiring")
            if not any(
                t["state"] in ("launching", "running", "interrupting")
                for t in self._turns(session=session["id"])
            ):
                # Nothing is running: retire immediately and release ownership.
                session = self._retire(session, reason=payload.get("reason"))
            self.store._history(
                "delegation.session",
                {
                    "action": "stop",
                    "operation_id": operation,
                    "actor": actor,
                    "session": session["id"],
                    "project": project,
                    "reason": payload.get("reason"),
                    "signalled_turns": signalled,
                    "remote_outcome": "unconfirmed" if signalled else "no_running_turn",
                },
            )
        self.reconcile()
        return self._session_view(
            self.store.get(session["id"]), self._options(session["id"])
        )

    def _options(self, session_id):
        row = self.store.db.execute(
            "SELECT options FROM delegation_sessions WHERE id=?", (session_id,)
        ).fetchone()
        return strict_loads(row[0]) if row else {}

    # -- assignments and turns ---------------------------------------------

    def assign(self, payload, *, project, actor, operation):
        session = self._session(payload["session_id"], project)
        harness = self._harness(session["harness"])
        if session["state"] not in ("idle", "active"):
            _refuse("session_not_accepting_work")
        capabilities = CAPABILITIES[session["harness"]]
        limits = payload["limits"]
        enforcement = _limit_enforcement(capabilities, limits)
        unenforced = [
            name for name, value in enforcement.items() if value == "unavailable"
        ]
        if unenforced and not payload.get("allow_unenforced_limits"):
            _refuse("limits_not_enforceable_on_harness")
        criteria_ids = [c["id"] for c in payload["criteria"]]
        if len(set(criteria_ids)) != len(criteria_ids):
            _refuse("duplicate_criterion_id")
        with self.store.transaction():
            stamp = now()
            commitment = {
                "schema_version": 1,
                "record_type": "Commitment",
                "id": identifier(),
                "rev": 1,
                "created_at": stamp,
                "updated_at": stamp,
                "project": project,
                "objective": payload["objective"],
                "criteria": [
                    {"id": c["id"], "text": c["text"], "evidence": [], "met": False}
                    for c in payload["criteria"]
                ],
                "state": "open",
                "owner": session["id"],
                "ownership_generation": session["ownership_generation"],
                "dependencies": [],
                "open_decisions": [],
                "next_trigger": None,
                "delegation": None,
                "evidence": [],
                "checkpoints": [],
                "decisions": [],
                "provenance": None,
            }
            self.store._put(commitment, 0)
            assignment = {
                "schema_version": 1,
                "record_type": "Assignment",
                "id": identifier(),
                "rev": 1,
                "created_at": stamp,
                "updated_at": stamp,
                "commitment": commitment["id"],
                "commitment_rev": commitment["rev"],
                "inputs": payload.get("inputs", []),
                "scope": payload["scope"],
                "output_contract": payload["output_contract"],
                "owner": session["id"],
                "backend": "local",
                "limits": {
                    "iterations": limits["iterations"],
                    "budget_usd": limits.get("budget_usd"),
                },
                "state": "dispatched",
                "run": None,
                "request_id": identifier(),
            }
            self.store._put(assignment, 0)
            turn = self._queue_turn(
                session,
                assignment,
                kind="assignment",
                prompt=payload["instructions"],
                operation=operation,
                actor=actor,
            )
            self.store._history(
                "delegation.assigned",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "session": session["id"],
                    "commitment": commitment["id"],
                    "assignment": assignment["id"],
                    "turn": turn["id"],
                    "limits": assignment["limits"],
                    "limit_enforcement": enforcement,
                },
            )
        return {
            "session": session["id"],
            "commitment": commitment["id"],
            "assignment": assignment["id"],
            "turn": turn["id"],
            "state": assignment["state"],
            "limit_enforcement": enforcement,
            "launch": "queued_until_service_tick",
            "harness_version_note": harness.get("binary"),
        }

    def followup(self, payload, *, project, actor, operation):
        session = self._session(payload["session_id"], project)
        self._harness(session["harness"])
        assignment, commitment = self._assignment(payload["assignment_id"], project)
        if assignment["owner"] != session["id"]:
            _refuse("assignment_not_owned_by_session")
        if session["state"] not in ("idle", "active"):
            _refuse("session_not_accepting_work")
        if assignment["state"] in ("completed", "failed", "cancelled"):
            _refuse("assignment_closed")
        self.reconcile()
        if any(
            t["state"] in RUNNING_TURN_STATES
            for t in self._turns(session=session["id"])
        ):
            _refuse("turn_still_running")
        with self.store.transaction():
            turn = self._queue_turn(
                session,
                assignment,
                kind="followup",
                prompt=payload["message"],
                operation=operation,
                actor=actor,
            )
            self._resolve_open_notices(assignment["id"], "followup_queued")
        return {
            "session": session["id"],
            "assignment": assignment["id"],
            "turn": turn["id"],
            "launch": "queued_until_service_tick",
        }

    def _queue_turn(self, session, assignment, *, kind, prompt, operation, actor):
        from .executive_intervention import delegation_guard
        delegation_guard(self.store, session["project"])
        seq = (
            self.store.db.execute(
                "SELECT COALESCE(MAX(seq),0) FROM delegation_turns WHERE session=?",
                (session["id"],),
            ).fetchone()[0]
            + 1
        )
        turn = {
            "schema_version": 1,
            "id": identifier(),
            "operation_id": operation,
            "actor": actor,
            "session": session["id"],
            "assignment": assignment["id"],
            "project": session["project"],
            "seq": seq,
            "kind": kind,
            "state": "queued",
            "prompt_digest": digest(prompt),
            "prompt_bytes": len(prompt.encode("utf-8")),
            "created_at": now(),
            "runner": None,
            "result": None,
        }
        self._save_turn(turn)
        directory = self.spool / session["id"] / turn["id"]
        for parent in (self.spool, self.spool / session["id"]):
            parent.mkdir(mode=0o700, exist_ok=True)
        directory.mkdir(mode=0o700, exist_ok=False)
        (directory / "prompt.txt").write_text(prompt)
        os.chmod(directory / "prompt.txt", 0o600)
        self.store._history(
            "delegation.turn",
            {
                "turn": turn["id"],
                "session": session["id"],
                "assignment": assignment["id"],
                "kind": kind,
                "state": "queued",
                "prompt_digest": turn["prompt_digest"],
            },
        )
        return turn

    def _spec(self, session, assignment, turn, prompt):
        harness = self._harness(session["harness"])
        options = self._options(session["id"])
        lineage = self._lineage(session["harness"])
        if lineage["shared_with"] and lineage["policy"] != "shared_accepted":
            # The policy may have changed since the session opened; every
            # launch re-applies it rather than trusting the opening check.
            _refuse("lineage_shared_requires_acceptance")
        directory = self.spool / session["id"] / turn["id"]
        earlier = [
            t for t in self._turns(session=session["id"]) if t["id"] != turn["id"]
        ]
        observed = any(
            (t.get("result") or {}).get("native_session_id") for t in earlier
        )
        first = not observed
        env = {}
        if session["harness"] == "claude-code":
            if not observed and any(t["state"] != "queued" for t in earlier):
                # An earlier launch may or may not have created the native
                # session; never reuse its id. Rotate to a fresh identity.
                session = self._rotate_native_session(session)
            briefing = session["briefing"]
            if _role(options) == "workstream":
                briefing += "\n\n" + WORKSTREAM_BRIEFING.format(workstream=options["workstream"])
            if options.get("subagent_model"):
                briefing += (
                    "\n\nDelegate bounded implementation or research tasks to native workers "
                    "when useful. Integrate their results, run appropriate tests, review "
                    "the final change, and return a concise report with evidence and limits."
                )
            if options.get("native_peer_messaging"):
                briefing += "\n\n" + guidance(session["native_session_id"], "worker")
            argv = [
                harness["binary"],
                "-p",
                prompt,
                "--output-format",
                "json",
                "--model",
                options["model"],
                "--permission-mode",
                options["permission_mode"],
                "--append-system-prompt",
                briefing,
                "--max-turns",
                str(assignment["limits"]["iterations"]),
            ]
            if assignment["limits"].get("budget_usd") is not None:
                argv.extend(
                    ["--max-budget-usd", str(assignment["limits"]["budget_usd"])]
                )
            if options.get("effort"):
                argv.extend(["--effort", options["effort"]])
            if options["permission_mode"] == "bypassPermissions":
                argv.append("--dangerously-skip-permissions")
            if options.get("native_peer_messaging"):
                settings = {"crossSessionInbound": "accept"}
                Contracts().validate("native-peer-settings", settings)
                argv.extend(["--settings", canonical(settings)])
                argv.extend(["--name", peer_name(session["native_session_id"], "worker")])
            if first:
                argv.extend(["--session-id", session["native_session_id"]])
            else:
                argv.extend(["--resume", session["native_session_id"]])
            env = {"CLAUDE_CONFIG_DIR": harness["config_dir"]}
            if options.get("subagent_model"):
                env["CLAUDE_CODE_SUBAGENT_MODEL"] = options["subagent_model"]
            if options.get("subagent_model_force"):
                env["CLAUDE_CODE_SUBAGENT_MODEL_FORCE"] = "1"
            if options.get("auto_compact_window_tokens") is not None:
                env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(options["auto_compact_window_tokens"])
            output_format = "json"
            last_message = None
        else:
            last_message = str(directory / "last-message.txt")
            if first or not session["native_session_id"]:
                text = session["briefing"]
                if _role(options) == "workstream":
                    text += "\n\n" + WORKSTREAM_BRIEFING.format(workstream=options["workstream"])
                text += "\n\n" + prompt
                argv = [
                    harness["binary"],
                    "exec",
                    "--json",
                    "--skip-git-repo-check",
                    "-C",
                    options["workspace"],
                    "-s",
                    options["sandbox"],
                    "-o",
                    last_message,
                ]
                if options.get("model"):
                    argv.extend(["-m", options["model"]])
                argv.append(text)
            else:
                argv = [
                    harness["binary"],
                    "exec",
                    "resume",
                    session["native_session_id"],
                    "--json",
                    "--skip-git-repo-check",
                    "-c",
                    f'sandbox_mode="{options["sandbox"]}"',
                    "-o",
                    last_message,
                ]
                if options.get("model"):
                    argv.extend(["-m", options["model"]])
                argv.append(prompt)
            if harness.get("codex_home"):
                env = {"CODEX_HOME": harness["codex_home"]}
            output_format = "jsonl"
        return {
            "schema_version": 1,
            "turn": turn["id"],
            "harness": session["harness"],
            "argv": argv,
            "cwd": options["workspace"],
            "env": env,
            "timeout_seconds": self.config.get("turn_timeout_seconds", 1800),
            "output_format": output_format,
            "last_message_file": last_message,
            "lineage": {
                key: value for key, value in lineage.items() if key != "lease_enforced"
            },
        }

    def _lineage_limit(self):
        return self.config.get("max_concurrent_turns_per_lineage", 1)

    def launch_pending(self):
        """Spawn runners for queued turns; one running turn per session.

        Turns on one credential lineage lock run up to
        `max_concurrent_turns_per_lineage` at a time across sessions (default
        1, so several sessions interleave their turns rather than run them in
        parallel).
        """
        if not self.enabled():
            return []
        launched = []
        busy = set()
        busy_locks = {}
        limit = self._lineage_limit()
        for t in self._turns():
            if t["state"] in ("launching", "running", "interrupting"):
                busy.add(t["session"])
                lock = self._lock_of(t["session"])
                busy_locks[lock] = busy_locks.get(lock, 0) + 1
        for turn in self._turns():
            if turn["state"] != "queued" or turn["session"] in busy:
                continue
            session = self.store.get(turn["session"])
            if session["state"] not in ("idle", "active"):
                continue
            lock = self._lock_of(session["id"], session)
            if lock is not None and busy_locks.get(lock, 0) >= limit:
                # Another session's turn holds this credential lineage; stay
                # queued instead of being refused by the runner's lease.
                continue
            from .usage_policy import UsagePolicy
            admission = UsagePolicy(self.store).check(
                turn["project"], purpose="delegation:" + turn["id"],
                session_id=session.get("native_session_id"),
            )
            if admission["decision"] == "hold":
                continue
            try:
                launched.append(self._launch(turn, session))
            except (DelegationRefused, OSError, ValueError, KeyError) as error:
                # One unlaunchable turn must not block other sessions' turns.
                with self.store.transaction():
                    self._finish_turn(
                        turn,
                        "failed",
                        failure=f"launch failed: {type(error).__name__}: {error}"[:200],
                    )
            busy.add(turn["session"])
            busy_locks[lock] = busy_locks.get(lock, 0) + 1
        return launched

    def _lock_of(self, session_id, session=None):
        session = session or self.store.get(session_id)
        try:
            return self._lineage(session["harness"])["lock"]
        except DelegationRefused:
            return None

    def _launch(self, turn, session):
        assignment = self.store.get(turn["assignment"])
        directory = self.spool / turn["session"] / turn["id"]
        prompt = (directory / "prompt.txt").read_text()
        # 1. Commit the launch intent (and any native identity rotation) first,
        #    so a crash between commit and spawn leaves a reconcilable record.
        with self.store.transaction():
            spec = self._spec(session, assignment, turn, prompt)
            spec_path = directory / "spec.json"
            if not spec_path.exists():
                spec_path.write_text(canonical(spec) + "\n")
                os.chmod(spec_path, 0o600)
            self._save_turn(
                turn
                | {"state": "launching", "runner": None, "launch_committed_at": now()}
            )
        # 2. Spawn outside any transaction; the runner guards against doubles.
        try:
            log_fd = os.open(
                directory / "runner.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
            )
            with os.fdopen(log_fd, "ab") as log:
                process = subprocess.Popen(
                    [self.python, "-m", "odin.delegation_runner", str(directory)],
                    cwd=str(directory),
                    env=os.environ
                    | {"PYTHONPATH": str(ROOT / "python"), "PYTHONNOUSERSITE": "1"},
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
        except OSError as error:
            with self.store.transaction():
                self._finish_turn(
                    self._turn(turn["id"]),
                    "failed",
                    failure=f"runner spawn failed: {type(error).__name__}",
                )
            return turn["id"]
        self._children.append(process)
        # 3. Record the observed runner identity.
        with self.store.transaction():
            current = self._turn(turn["id"])
            self._save_turn(
                current | {"runner": {"pid": process.pid, "launched_at": now()}}
            )
            session = self.store.get(session["id"])
            if session["state"] != "active":
                self._put_session(session, state="active")
            assignment = self.store.get(assignment["id"])
            if assignment["state"] == "dispatched":
                self.store._put(
                    assignment
                    | {
                        "state": "active",
                        "rev": assignment["rev"] + 1,
                        "updated_at": now(),
                    },
                    assignment["rev"],
                )
            self.store._history(
                "delegation.turn",
                {
                    "turn": turn["id"],
                    "session": turn["session"],
                    "assignment": turn["assignment"],
                    "state": "launching",
                    "runner_pid": process.pid,
                    "argv_digest": digest(spec["argv"]),
                },
            )
        return turn["id"]

    def _rotate_native_session(self, session):
        """Give a Claude Code session a fresh native id after an unobserved launch."""
        environment = self._environment_record()
        previous = self._current_binding(session["id"])
        old = session["native_session_id"]
        session = self._put_session(session, native_session_id=str(uuid.uuid4()))
        if previous is not None and previous["state"] == "active":
            self.store._put(
                previous
                | {
                    "state": "invalidated",
                    "rev": previous["rev"] + 1,
                    "updated_at": now(),
                },
                previous["rev"],
            )
        self._bind(
            session, environment, predecessor=previous["id"] if previous else None
        )
        self.store._history(
            "delegation.session",
            {
                "action": "rotate_native_session",
                "session": session["id"],
                "project": session["project"],
                "previous_native_session_id": old,
                "native_session_id": session["native_session_id"],
                "reason": "earlier launch never reported its native session",
            },
        )
        return session

    def reconcile(self):
        """Ingest runner results and detect lost runners; never retries."""
        if not self.enabled():
            return []
        # Reap finished detached runners so no zombie or warning lingers.
        self._children = [child for child in self._children if child.poll() is None]
        changed = []
        for session in self.store.records("PlanningSession"):
            if (
                session["adapter"] in ADAPTERS.values()
                and session["state"] == "retiring"
                and not any(
                    t["state"] in ("launching", "running", "interrupting")
                    for t in self._turns(session=session["id"])
                )
            ):
                with self.store.transaction():
                    self._retire(session, reason="service recovery")
                changed.append(session["id"])
        timeout = (self.config or {}).get("turn_timeout_seconds", 1800)
        for turn in self._turns():
            if turn["state"] not in ("launching", "running", "interrupting"):
                continue
            directory = self.spool / turn["session"] / turn["id"]
            result_path = directory / "result.json"
            started_path = directory / "started.json"
            runner = turn.get("runner") or {}
            launched_at = runner.get("launched_at") or turn.get("launch_committed_at")
            overdue = launched_at is not None and _age_seconds(launched_at) > (
                timeout + RUNNER_GRACE_SECONDS + DEADLINE_SLACK_SECONDS
            )
            stuck_interrupt = (
                turn["state"] == "interrupting"
                and turn.get("interrupt_requested_at")
                and _age_seconds(turn["interrupt_requested_at"])
                > (RUNNER_GRACE_SECONDS + DEADLINE_SLACK_SECONDS)
            )
            if (overdue or stuck_interrupt) and not result_path.exists():
                self._kill_turn_processes(turn, directory)
                with self.store.transaction():
                    self._finish_turn(
                        turn,
                        "lost",
                        failure="runner deadline exceeded; processes signalled; "
                        "native outcome unknown",
                    )
                changed.append(turn["id"])
                continue
            if result_path.exists():
                try:
                    result = strict_loads(result_path.read_text())
                    self.store.contracts.validate("delegation-result", result)
                except (ValueError, OSError, Exception) as error:
                    with self.store.transaction():
                        self._finish_turn(
                            turn,
                            "failed",
                            failure=f"unreadable result: {type(error).__name__}",
                        )
                    changed.append(turn["id"])
                    continue
                if result["timed_out"]:
                    state = "failed"
                elif result["interrupted"]:
                    state = "interrupted"
                elif result["is_error"] or result["parse_error"]:
                    state = "failed"
                else:
                    state = "returned"
                failure = (
                    result.get("error_summary")
                    if state == "failed"
                    and (result.get("lineage") or {}).get("refused")
                    else None
                )
                with self.store.transaction():
                    self._finish_turn(turn, state, result=result, failure=failure)
                changed.append(turn["id"])
                continue
            if started_path.exists() and turn["state"] == "launching":
                try:
                    started = strict_loads(started_path.read_text())
                except (ValueError, OSError):
                    started = {}
                with self.store.transaction():
                    self._save_turn(
                        turn
                        | {
                            "state": "running",
                            "runner": runner
                            | {
                                "harness_pid": started.get("harness_pid"),
                                "started_at": started.get("started_at"),
                            },
                        }
                    )
                changed.append(turn["id"])
                continue
            if runner.get("pid") is None:
                continue  # Launch committed but not yet spawned by this process.
            if not _runner_alive(runner.get("pid"), directory):
                killed = self._kill_turn_processes(turn, directory)
                with self.store.transaction():
                    self._finish_turn(
                        turn,
                        "lost",
                        failure="runner exited without a result; native outcome unknown"
                        + ("; harness process signalled" if killed else ""),
                    )
                changed.append(turn["id"])
        return changed

    def _kill_turn_processes(self, turn, directory):
        """Signal a turn's runner and harness groups; identity-checked, best effort."""
        runner = turn.get("runner") or {}
        killed = False
        if _runner_alive(runner.get("pid"), directory):
            killed |= _kill_group(runner["pid"], signal.SIGKILL)
        harness_pid = runner.get("harness_pid")
        if harness_pid and _pid_alive(harness_pid):
            killed |= _kill_group(harness_pid, signal.SIGKILL)
        return killed

    def _retire(self, session, *, reason=None):
        """Retire a session: strand no queued turn, release project ownership."""
        for turn in self._turns(session=session["id"]):
            if turn["state"] == "queued":
                stranded = turn | {
                    "state": "interrupted",
                    "stop_reason": reason or "session_retired",
                    "finished_at": now(),
                }
                self._save_turn(stranded)
                self._notify(stranded)
        if session["state"] != "retired":
            session = self._put_session(session, state="retired")
        self._release_owner(session)
        return session

    def _finish_turn(self, turn, state, *, result=None, failure=None):
        session = self.store.get(turn["session"])
        updated = turn | {
            "state": state,
            "finished_at": now(),
            "result": self._result_summary(result) if result else None,
            "failure": failure,
        }
        self._save_turn(updated)
        changes = {}
        if result and result.get("native_session_id"):
            if session["native_session_id"] is None:
                changes["native_session_id"] = result["native_session_id"]
                environment = self._environment_record()
                self._bind(session | changes, environment, predecessor=None)
            elif session["native_session_id"] != result["native_session_id"]:
                updated["native_session_mismatch"] = True
                self._save_turn(updated)
        still_running = any(
            t["state"] in ("launching", "running", "interrupting")
            for t in self._turns(session=session["id"])
            if t["id"] != turn["id"]
        )
        if session["state"] == "retiring":
            if changes:
                session = self._put_session(session, **changes)
                changes = {}
            if not still_running:
                self._retire(session)
        elif session["state"] == "active" and not still_running:
            changes["state"] = "idle"
        if changes:
            self._put_session(session, **changes)
        self.store._history(
            "delegation.result",
            {
                "turn": turn["id"],
                "session": turn["session"],
                "assignment": turn["assignment"],
                "state": state,
                "failure": failure,
                "report": updated["result"],
                "verification": "unverified",
            },
        )
        self._notify(updated)

    # -- attention notices -------------------------------------------------

    def _notify(self, turn):
        """Persist one notice for a terminal turn that needs the executive.

        Called inside the transaction that records the outcome, so a restart
        cannot lose it. The identity is a function of the turn and its terminal
        state; observing the same outcome again inserts nothing.
        """
        assignment = self.store.get(turn["assignment"])
        commitment = self.store.get(assignment["commitment"])
        reasons = [reason for reason in (_turn_attention(turn),) if reason]
        if _commitment_open_after_turns(
            assignment, commitment, self._turns(assignment=assignment["id"])
        ):
            reasons.append(OPEN_COMMITMENT)
        if not reasons:
            return None
        notice_id = _notice_id(
            {"kind": "delegation_turn", "turn": turn["id"], "state": turn["state"]}
        )
        result = turn.get("result") or {}
        notice = {
            "schema_version": 1,
            "id": notice_id,
            "kind": "delegation_turn",
            "project": turn["project"],
            "session": turn["session"],
            "assignment": assignment["id"],
            "commitment": commitment["id"],
            "turn": turn["id"],
            "turn_state": turn["state"],
            "timed_out": bool(result.get("timed_out")),
            "cost_usd": result.get("cost_usd"),
            "failure": (turn.get("failure") or "")[:400] or None,
            "reasons": reasons,
            "status_reference": {
                "tool": "odin_delegation_status",
                "assignment_id": assignment["id"],
            },
            "created_at": now(),
            "state": "pending",
            "first_offered_at": None,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "acknowledgement_authority": None,
            "resolved_at": None,
            "resolution": None,
        }
        inserted = self.store.db.execute(
            "INSERT INTO delegation_notices VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
            (
                notice_id,
                notice["project"],
                notice["assignment"],
                notice["turn"],
                "pending",
                canonical(notice),
            ),
        ).rowcount
        if inserted:
            self.store._history(
                "delegation.notice",
                {
                    "notice_id": notice_id,
                    "turn": turn["id"],
                    "assignment": assignment["id"],
                    "turn_state": turn["state"],
                    "reasons": reasons,
                },
            )
        return notice_id

    def notice(self, notice_id):
        row = self.store.db.execute(
            "SELECT body FROM delegation_notices WHERE id=?", (notice_id,)
        ).fetchone()
        return strict_loads(row[0]) if row else None

    def _save_notice(self, notice):
        self.store.db.execute(
            "UPDATE delegation_notices SET state=?,body=? WHERE id=?",
            (notice["state"], canonical(notice), notice["id"]),
        )

    def pending_notices(self, project, limit=8, *, assignment=None):
        """Unacknowledged, unresolved notices for this project.

        Notices reporting a failed, timed-out, interrupted or lost turn come
        first so open-commitment reminders cannot crowd them out; each group
        is oldest first.
        """
        query = "SELECT body FROM delegation_notices WHERE project=? AND state='pending'"
        arguments = [project]
        if assignment is not None:
            query += " AND assignment=?"
            arguments.append(assignment)
        rows = self.store.db.execute(
            query
            + " ORDER BY (json_array_length(body,'$.reasons')=1"
            " AND json_extract(body,'$.reasons[0]')=?), rowid LIMIT ?",
            (*arguments, OPEN_COMMITMENT, limit),
        )
        return [strict_loads(row[0]) for row in rows]

    def mark_offered(self, notice_ids, at=None):
        """Record the first channel offer only; later polls write nothing."""
        stamp = at or now()
        with self.store.transaction():
            for notice_id in notice_ids:
                notice = self.notice(notice_id)
                if notice and notice["first_offered_at"] is None:
                    self._save_notice(notice | {"first_offered_at": stamp})

    def acknowledge_notice(self, notice_id, project, *, actor):
        """Model-attributed acknowledgement: stops re-delivery, grants nothing else."""
        with self.store.transaction():
            notice = self.notice(notice_id)
            if notice is None or notice["project"] != project:
                raise Conflict("notice belongs to another project")
            if notice["state"] == "pending":
                notice = notice | {
                    "state": "acknowledged",
                    "acknowledged_at": now(),
                    "acknowledged_by": actor,
                    "acknowledgement_authority": (
                        "model_attributed_not_operator_approval"
                        if actor == "fable-executive"
                        else "operator_terminal_acknowledgement_not_approval"
                    ),
                }
                self._save_notice(notice)
                self.store._history(
                    "delegation.notice_acknowledged",
                    {"notice_id": notice_id, "actor": actor},
                )
        return {
            "notice": {
                key: notice[key]
                for key in (
                    "id",
                    "kind",
                    "assignment",
                    "turn",
                    "state",
                    "acknowledged_at",
                    "acknowledged_by",
                    "acknowledgement_authority",
                )
            }
        }

    def _resolve_open_notices(self, assignment_id, resolution):
        """An executive decision answers an open-commitment-only notice.

        Notices that also report a failed, timed-out, interrupted or lost turn
        stay pending until acknowledged.
        """
        rows = self.store.db.execute(
            "SELECT body FROM delegation_notices WHERE assignment=? AND state='pending'",
            (assignment_id,),
        ).fetchall()
        for notice in (strict_loads(row[0]) for row in rows):
            if notice["reasons"] == [OPEN_COMMITMENT]:
                self._save_notice(
                    notice
                    | {"state": "resolved", "resolved_at": now(), "resolution": resolution}
                )

    @staticmethod
    def render_notice(notice):
        header = NOTICE_HEADER.format(
            turn=notice["turn"],
            assignment=notice["assignment"],
            state="timed out" if notice["timed_out"] else notice["turn_state"],
            notice_id=notice["id"],
        )
        lines = [
            f"Reasons: {', '.join(notice['reasons'])}.",
            f"Commitment {notice['commitment']} is "
            + (
                "still open with no turn running; it needs an executive decision "
                "(follow-up, acceptance or cancellation)."
                if OPEN_COMMITMENT in notice["reasons"]
                else "not reported open by this notice."
            ),
        ]
        if notice.get("failure"):
            lines.append(
                f"Untrusted harness output excerpt (recorded failure): {notice['failure']}"
            )
        lines.append(
            "Reported cost: "
            + (
                f"{notice['cost_usd']} USD (harness estimate)"
                if notice.get("cost_usd") is not None
                else "unknown"
            )
            + "."
        )
        lines.append(
            "Inspect odin_delegation_status with assignment_id="
            f"{notice['assignment']} for the full state. A worker return is a report, "
            "not verified evidence; nothing in this notice is operator approval or "
            "acceptance."
        )
        return header + "\n".join(lines)

    def _release_owner(self, session):
        project = self._project(session["project"])
        if project["interface_decision_owner"] == session["id"]:
            self.store._put(
                project
                | {
                    "interface_decision_owner": None,
                    "rev": project["rev"] + 1,
                    "updated_at": now(),
                },
                project["rev"],
            )
        binding = self._current_binding(session["id"])
        if binding is not None and binding["state"] == "active":
            self.store._put(
                binding
                | {
                    "state": "invalidated",
                    "rev": binding["rev"] + 1,
                    "updated_at": now(),
                },
                binding["rev"],
            )

    @staticmethod
    def _result_summary(result):
        text = result.get("final_text") or ""
        return {
            "exit_code": result["exit_code"],
            "started_at": result["started_at"],
            "finished_at": result["finished_at"],
            "timed_out": result["timed_out"],
            "interrupted": result["interrupted"],
            "is_error": result["is_error"],
            "stop_reason": result.get("stop_reason"),
            "turns": result.get("turns"),
            "cost_usd": result.get("cost_usd"),
            "usage": result.get("usage"),
            "usage_scope": result.get("usage_scope"),
            "model_usage": result.get("model_usage"),
            "observed_model": result.get("observed_model"),
            "permission_denials": result.get("permission_denials"),
            "parse_error": result.get("parse_error"),
            "error_summary": result.get("error_summary"),
            "lineage": result.get("lineage"),
            "native_session_id": result.get("native_session_id"),
            "final_text_bytes": len(text.encode("utf-8")),
            "final_text_digest": digest(text),
            "final_text_preview": text[:600],
        }

    # -- views ---------------------------------------------------------------

    def _session_view(self, session, options, *, adopted=(), binding=None):
        turns = self._turns(session=session["id"])
        deltas = _cost_deltas(session["harness"], turns)
        known_cost = sum(delta for delta in deltas.values() if delta is not None)
        unknown_cost = sum(
            1
            for t in turns
            if t["state"] in TERMINAL_TURN_STATES
            and ((t.get("result") or {}).get("cost_usd") is None)
        )
        binding = binding or self._current_binding(session["id"])
        return {
            "session": {
                key: session[key]
                for key in (
                    "id",
                    "rev",
                    "project",
                    "harness",
                    "adapter",
                    "native_session_id",
                    "incarnation",
                    "state",
                    "budget_usd",
                    "ownership_generation",
                )
            },
            "options": options,
            "workstream": options.get("workstream"),
            "role": _role(options),
            "native_peer_name": (
                peer_name(session["native_session_id"], "worker")
                if session["harness"] == "claude-code" and options.get("native_peer_messaging")
                else None
            ),
            "native_peer_transport": (
                "requested_unverified" if options.get("native_peer_messaging") else "disabled"
            ),
            "capabilities": CAPABILITIES[session["harness"]],
            "binding": {
                "id": binding["id"],
                "state": binding["state"],
                "host": binding["host"],
                "incarnation": binding["incarnation"],
            }
            if binding
            else None,
            "native_session_observed": any(
                (t.get("result") or {}).get("native_session_id") for t in turns
            ),
            "turn_count": len(turns),
            "running_turns": [
                t["id"] for t in turns if t["state"] in RUNNING_TURN_STATES
            ],
            "cost_usd_known": round(known_cost, 6),
            "cost_accounting": (
                "per_turn_delta_of_inclusive_native_session_cost"
                if session["harness"] == "claude-code"
                else "per_turn_reported_cost"
            ),
            "turns_with_unknown_cost": unknown_cost,
            "adopted_commitments": list(adopted),
            "execution_backend": "local_native_harness",
            "guarantees": "none; no isolation, no Saga admission, limits only as harness options",
        }

    def status(self, payload, *, project):
        if not self.enabled():
            return {
                "enabled": False,
                "reason": "delegation_not_configured",
                "sessions": [],
            }
        self.reconcile()
        detail = payload.get("detail_bytes", 4096)
        sessions = [
            r
            for r in self.store.records("PlanningSession")
            if r["project"] == project and r["adapter"] in ADAPTERS.values()
        ]
        if payload.get("session_id"):
            sessions = [r for r in sessions if r["id"] == payload["session_id"]]
            if not sessions:
                _refuse("unknown_session")
        views = []
        for session in sessions[-8:]:
            view = self._session_view(session, self._options(session["id"]))
            deltas = _cost_deltas(session["harness"], self._turns(session=session["id"]))
            assignments = []
            for assignment in self.store.records("Assignment"):
                if (
                    assignment["owner"] != session["id"]
                    or assignment["backend"] != "local"
                ):
                    continue
                if (
                    payload.get("assignment_id")
                    and assignment["id"] != payload["assignment_id"]
                ):
                    continue
                commitment = self.store.get(assignment["commitment"])
                turns = self._turns(assignment=assignment["id"])
                attention = []
                if turns and assignment["state"] not in CLOSED_ASSIGNMENT_STATES:
                    reason = _turn_attention(turns[-1])
                    if reason:
                        attention.append(reason)
                    if _commitment_open_after_turns(assignment, commitment, turns):
                        attention.append(OPEN_COMMITMENT)
                pending = [
                    n["id"]
                    for n in self.pending_notices(
                        project, 16, assignment=assignment["id"]
                    )
                ]
                assignments.append(
                    {
                        "id": assignment["id"],
                        "rev": assignment["rev"],
                        "state": assignment["state"],
                        "commitment": commitment["id"],
                        "commitment_state": commitment["state"],
                        "objective": commitment["objective"][:240],
                        "criteria": [
                            {"id": c["id"], "met": c["met"]}
                            for c in commitment["criteria"]
                        ],
                        "limits": assignment["limits"],
                        "limit_enforcement": _limit_enforcement(
                            CAPABILITIES[session["harness"]], assignment["limits"]
                        ),
                        "attention": attention,
                        "pending_notices": pending,
                        "turns": [
                            {
                                "id": t["id"],
                                "seq": t["seq"],
                                "kind": t["kind"],
                                "state": t["state"],
                                "created_at": t["created_at"],
                                "finished_at": t.get("finished_at"),
                                "failure": t.get("failure"),
                                "native_session_mismatch": t.get(
                                    "native_session_mismatch", False
                                ),
                                "runner": t.get("runner"),
                                "cost_usd_delta": deltas.get(t["id"]),
                                "result": {
                                    k: v
                                    for k, v in (t.get("result") or {}).items()
                                    if k != "final_text_preview"
                                }
                                | (
                                    {
                                        "final_text_preview": t["result"][
                                            "final_text_preview"
                                        ][: max(detail // 4, 80)]
                                    }
                                    if t.get("result")
                                    else {}
                                )
                                if t.get("result")
                                else None,
                            }
                            for t in turns
                        ],
                    }
                )
            view["assignments"] = assignments
            views.append(view)
        if payload.get("assignment_id") and not any(v["assignments"] for v in views):
            _refuse("unknown_assignment")
        pending = self.pending_notices(project, 64)
        return {
            "enabled": True,
            "project": project,
            "project_aggregate": self._project_aggregate(project),
            "attention": {
                "assignments": sorted(
                    a["id"] for v in views for a in v["assignments"] if a["attention"]
                ),
                "pending_notice_count": len(pending),
                "pending_notices": [n["id"] for n in pending[:8]],
                "acknowledge_with": "odin_loop_ack",
            },
            "sessions": views,
            "verification": "worker returns are reports; acceptance is a separate executive action",
        }

    def _project_aggregate(self, project):
        """ADR-036 view: sessions by workstream and role, lineage queues, cost."""
        sessions = [
            r
            for r in self.store.records("PlanningSession")
            if r["project"] == project and r["adapter"] in ADAPTERS.values()
        ]
        locks = {}
        for name in self.config["harnesses"]:
            try:
                locks.setdefault(self._lineage(name)["lock"], []).append(name)
            except DelegationRefused:
                pass
        lineages = {
            lock: {"harnesses": sorted(names), "queued": 0, "running": 0,
                   "running_any_project": 0}
            for lock, names in locks.items()
        }
        lock_of = {}
        for turn in self._turns():
            if turn["session"] not in lock_of:
                lock_of[turn["session"]] = self._lock_of(turn["session"])
            entry = lineages.get(lock_of[turn["session"]])
            if entry is None:
                continue
            running = turn["state"] in ("launching", "running", "interrupting")
            entry["running_any_project"] += running
            if turn["project"] == project:
                entry["running"] += running
                entry["queued"] += turn["state"] == "queued"
        rows, known, unknown, owner = [], 0.0, 0, None
        for session in sessions:
            options = self._options(session["id"])
            view = self._session_view(session, options)
            active = session["state"] in ACTIVE_SESSION_STATES
            if active and view["role"] == "integration_owner":
                owner = session["id"]
            known += view["cost_usd_known"]
            unknown += view["turns_with_unknown_cost"]
            if not active:
                continue
            attention = []
            for assignment in self.store.records("Assignment"):
                if (
                    assignment["owner"] != session["id"]
                    or assignment["backend"] != "local"
                    or assignment["state"] in CLOSED_ASSIGNMENT_STATES
                ):
                    continue
                turns = self._turns(assignment=assignment["id"])
                commitment = self.store.get(assignment["commitment"])
                if turns and (
                    _turn_attention(turns[-1])
                    or _commitment_open_after_turns(assignment, commitment, turns)
                ):
                    attention.append(assignment["id"])
            rows.append(
                {
                    "id": session["id"],
                    "workstream": view["workstream"],
                    "role": view["role"],
                    "legacy": _legacy(options),
                    "state": session["state"],
                    "running_turn": (view["running_turns"] or [None])[0],
                    "attention_assignments": attention,
                }
            )
        return {
            "active_sessions": rows,
            "integration_owner": owner,
            "max_concurrent_turns_per_lineage": self._lineage_limit(),
            "lineages": list(lineages.values()),
            "execution": (
                "turns on one credential lineage run at most "
                "max_concurrent_turns_per_lineage at a time across sessions; "
                "with 1, several sessions interleave turns and do not run in parallel"
            ),
            "cost_usd_known": round(known, 6),
            "turns_with_unknown_cost": unknown,
            "cost_label": "attributed_not_verified",
        }

    def result(self, payload, *, project):
        if not self.enabled():
            _refuse("delegation_not_configured")
        self.reconcile()
        if payload.get("turn_id"):
            turn = self._turn(payload["turn_id"])
            if turn["project"] != project:
                _refuse("unknown_turn")
        elif payload.get("assignment_id"):
            self._assignment(payload["assignment_id"], project)
            finished = [
                t
                for t in self._turns(assignment=payload["assignment_id"])
                if t["state"] in TERMINAL_TURN_STATES
            ]
            if not finished:
                _refuse("no_finished_turn")
            turn = finished[-1]
        else:
            _refuse("turn_or_assignment_required")
        directory = self.spool / turn["session"] / turn["id"]
        result_path = directory / "result.json"
        if turn["state"] not in TERMINAL_TURN_STATES:
            _refuse("turn_not_finished")
        body = None
        if result_path.exists():
            try:
                body = strict_loads(result_path.read_text())
            except (ValueError, OSError):
                return {
                    "turn": turn["id"],
                    "state": turn["state"],
                    "available": False,
                    "reason": "result_unreadable",
                    "transcript_paths": self._paths(directory),
                }
        text = (body or {}).get("final_text", "") if body else ""
        limit = payload.get("max_bytes", 65536)
        encoded = text.encode("utf-8")
        if len(encoded) > limit:
            return {
                "turn": turn["id"],
                "state": turn["state"],
                "available": False,
                "reason": "final_text_exceeds_max_bytes",
                "final_text_bytes": len(encoded),
                "transcript_paths": self._paths(directory),
            }
        return {
            "turn": turn["id"],
            "assignment": turn["assignment"],
            "session": turn["session"],
            "state": turn["state"],
            "available": True,
            "failure": turn.get("failure"),
            "report": turn.get("result"),
            "final_text": text,
            "stderr_tail": (body or {}).get("stderr_tail", "")[:2048],
            "transcript_paths": self._paths(directory),
            "verification": "unverified worker report",
        }

    @staticmethod
    def _paths(directory):
        return {
            name: str(directory / name)
            for name in (
                "prompt.txt",
                "spec.json",
                "stdout.log",
                "stderr.log",
                "result.json",
            )
            if (directory / name).exists()
        }

    def close(self, payload, *, project, actor, operation):
        assignment, commitment = self._assignment(payload["assignment_id"], project)
        if assignment["state"] in ("completed", "failed", "cancelled"):
            _refuse("assignment_closed")
        self.reconcile()
        turns = self._turns(assignment=assignment["id"])
        if any(t["state"] in ("launching", "running", "interrupting") for t in turns):
            _refuse("turn_still_running")
        if payload["disposition"] == "accepted" and any(
            t["state"] == "queued" for t in turns
        ):
            _refuse("turn_still_running")
        stamp = now()
        with self.store.transaction():
            for t in turns:
                if t["state"] == "queued":
                    self._save_turn(
                        t
                        | {
                            "state": "interrupted",
                            "stop_reason": "assignment_cancelled",
                            "finished_at": stamp,
                        }
                    )
            if payload["disposition"] == "accepted":
                evidence = payload.get("evidence") or {}
                required = {c["id"] for c in commitment["criteria"]}
                if set(evidence) != required or any(
                    not refs for refs in evidence.values()
                ):
                    _refuse("acceptance_evidence_incomplete")
                turn_ids = {t["id"] for t in self._turns(assignment=assignment["id"])}
                for refs in evidence.values():
                    for ref in refs:
                        if ref.startswith("turn:") and ref[5:] not in turn_ids:
                            _refuse("evidence_turn_not_in_assignment")
                self.store._put(
                    assignment
                    | {
                        "state": "completed",
                        "rev": assignment["rev"] + 1,
                        "updated_at": stamp,
                    },
                    assignment["rev"],
                )
                closed = commitment | {
                    "state": "closed",
                    "criteria": [
                        c | {"met": True, "evidence": sorted(evidence[c["id"]])}
                        for c in commitment["criteria"]
                    ],
                    "evidence": sorted(
                        {ref for refs in evidence.values() for ref in refs}
                    ),
                    "checkpoints": commitment["checkpoints"]
                    + [
                        {
                            "id": operation,
                            "at": stamp,
                            "summary": (
                                payload.get("reason") or "accepted by executive"
                            )[:2000],
                            "evidence": sorted(
                                {ref for refs in evidence.values() for ref in refs}
                            ),
                            "recorded_by": assignment["owner"],
                        }
                    ],
                    "rev": commitment["rev"] + 1,
                    "updated_at": stamp,
                }
                self.store._put(closed, commitment["rev"])
                state = "closed"
            else:
                self.store._put(
                    assignment
                    | {
                        "state": "cancelled",
                        "rev": assignment["rev"] + 1,
                        "updated_at": stamp,
                    },
                    assignment["rev"],
                )
                self.store._put(
                    commitment
                    | {
                        "state": "abandoned",
                        "rev": commitment["rev"] + 1,
                        "updated_at": stamp,
                    },
                    commitment["rev"],
                )
                state = "abandoned"
            self.store._history(
                "delegation.closed",
                {
                    "operation_id": operation,
                    "actor": actor,
                    "assignment": assignment["id"],
                    "commitment": commitment["id"],
                    "disposition": payload["disposition"],
                    "reason": payload.get("reason"),
                    "acceptance": "executive_attributed_not_saga_verified",
                },
            )
            self._resolve_open_notices(assignment["id"], "assignment_" + payload["disposition"])
        return {
            "assignment": assignment["id"],
            "commitment": commitment["id"],
            "assignment_state": "completed" if state == "closed" else "cancelled",
            "commitment_state": state,
            "acceptance": "executive_attributed_not_saga_verified",
        }

    def tick(self):
        if not self.enabled():
            return
        self.reconcile()
        if self.store.stopped():
            return  # An operator stop halts new launches; running turns reconcile.
        self.launch_pending()


def default_config(
    *,
    claude_config_dir,
    workspace_roots,
    codex_home=None,
    claude_binary=None,
    codex_binary=None,
    claude_model="claude-sonnet-5-5",
    claude_subagent_model=None,
    claude_subagent_model_force=False,
    claude_auto_compact_window_tokens=None,
    claude_native_peer_messaging=False,
    codex_model=None,
    turn_timeout_seconds=1800,
    lineage_policy="exclusive",
    max_concurrent_turns_per_lineage=1,
):
    """Build an operator delegation configuration from explicit choices."""
    harnesses = {}
    claude = claude_binary or shutil.which("claude")
    if claude is not None and not os.access(claude, os.X_OK):
        claude = None
    if claude_config_dir:
        if claude is None:
            raise ValueError("Claude Code binary not found")
        harnesses["claude-code"] = {
            "binary": str(Path(claude).absolute()),
            "config_dir": str(Path(claude_config_dir).absolute()),
            "credential_ref": "secret:odin-delegation-claude-login",
            "refresh_owner": "odin-delegation-claude-config-dir",
            "default_model": claude_model,
            **({"default_subagent_model": claude_subagent_model} if claude_subagent_model else {}),
            **({"default_subagent_model_force": claude_subagent_model_force} if claude_subagent_model_force else {}),
            **({"default_auto_compact_window_tokens": claude_auto_compact_window_tokens} if claude_auto_compact_window_tokens is not None else {}),
            **({"default_native_peer_messaging": True} if claude_native_peer_messaging else {}),
            "default_permission_mode": "acceptEdits",
        }
    codex = codex_binary or shutil.which("codex")
    if codex is not None and os.access(codex, os.X_OK):
        harnesses["codex"] = {
            "binary": str(Path(codex).absolute()),
            "codex_home": str(Path(codex_home).absolute()) if codex_home else None,
            "credential_ref": "secret:odin-delegation-codex-home",
            "refresh_owner": "codex-cli",
            "default_model": codex_model,
            "default_sandbox": "workspace-write",
        }
    if not harnesses:
        raise ValueError("no delegation harness configured")
    return {
        "schema_version": 1,
        "workspace_roots": [str(Path(root).absolute()) for root in workspace_roots],
        "turn_timeout_seconds": turn_timeout_seconds,
        "lineage_policy": lineage_policy,
        "max_concurrent_turns_per_lineage": max_concurrent_turns_per_lineage,
        "harnesses": harnesses,
    }
