"""Durable local session-host command journal with fail-closed dispatch.

This is a trusted-process prototype. Authentication, outbound service
transport, credential store and real SDK enforcement are not present.
"""

import fcntl
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .contracts import Contracts, canonical, strict_loads
from .store import Conflict, digest

START_CAPABILITIES = frozenset(
    {
        "profile_enforcement",
        "credential_isolation",
        "budget_enforcement",
        "model_resolution",
        "effort_resolution",
        "transcript",
        "permission_relay",
    }
)


class SessionHost:
    def __init__(self, path, transport, *, host_id):
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.lock = os.fdopen(
            os.open(
                str(self.path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
            ),
            "a+",
        )
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise Conflict("session host already has a writer") from None
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS operations
              (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, command TEXT NOT NULL,
               state TEXT NOT NULL, observation TEXT);
            CREATE TABLE IF NOT EXISTS bindings
              (session TEXT PRIMARY KEY, generation INTEGER NOT NULL,
               assignment TEXT NOT NULL, assignment_revision INTEGER NOT NULL,
               ownership_generation INTEGER NOT NULL, state TEXT NOT NULL,
               native_session_id TEXT, operation_id TEXT);
        """)
        columns = {r[1] for r in self.db.execute("PRAGMA table_info(bindings)")}
        if "operation_id" not in columns:
            self.db.execute("ALTER TABLE bindings ADD COLUMN operation_id TEXT")
        with self.db:
            self.db.execute(
                "UPDATE bindings SET state='host_offline' WHERE state IN ('active','idle')"
            )
        self.host_id = host_id
        self.transport = transport
        self.contracts = Contracts()
        self.online = True

    def close(self):
        self.db.close()
        self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def host_offline(self):
        self.online = False
        with self.db:
            self.db.execute(
                "UPDATE bindings SET state='host_offline' WHERE state IN ('active','idle')"
            )

    def host_online(self):
        # Offline bindings stay unavailable until each operation/session is
        # explicitly reconciled. A heartbeat alone proves no process state.
        self.online = True

    def lookup(self, operation_id):
        row = self.db.execute(
            "SELECT state,observation FROM operations WHERE id=?", (operation_id,)
        ).fetchone()
        return (
            None
            if row is None
            else {
                "state": row[0],
                "observation": strict_loads(row[1]) if row[1] else None,
            }
        )

    @staticmethod
    def _authorize(command, authority):
        if authority is None or not callable(authority):
            raise PermissionError("service authority check required")
        current = authority(command)
        if (
            not isinstance(current, dict)
            or current.get("command_digest") != digest(command)
            or any(
                current.get(key) != command[key]
                for key in (
                    "session",
                    "generation",
                    "assignment",
                    "assignment_revision",
                    "ownership_generation",
                    "grant_id",
                    "budget_ref",
                    "credential_ref",
                    "data_policy_ref",
                )
            )
        ):
            raise PermissionError("stale or missing service authority")
        control = command["action"] in ("interrupt", "retire")
        if not control and (
            current.get("stopped") is not False
            or current.get("grant_active") is not True
            or current.get("budget_available") is not True
            or current.get("credential_ready") is not True
            or current.get("data_policy_allowed") is not True
            or current.get("grant_action") != command["action"]
            or current.get("grant_resource") != command["assignment"]
            or datetime.fromisoformat(command["deadline"]) <= datetime.now(timezone.utc)
        ):
            raise PermissionError("stop, grant, budget, credential or data policy gate")

    def _binding(self, command):
        row = self.db.execute(
            "SELECT * FROM bindings WHERE session=?", (command["session"],)
        ).fetchone()
        if command["action"] == "start":
            if row is not None:
                raise Conflict("session already bound")
            return
        if row is None or any(
            row[key] != command[key]
            for key in (
                "generation",
                "assignment",
                "assignment_revision",
                "ownership_generation",
            )
        ):
            raise Conflict("stale session binding")
        if row["state"] == "retired":
            raise Conflict("binding requires reconciliation")
        if row["state"] in (
            "host_offline",
            "invalidated",
            "unknown",
            "stop_unknown",
        ) and command["action"] not in ("interrupt", "retire"):
            raise Conflict("pending operation requires reconciliation")

    def _capabilities(self, command):
        required = set(command["required_capabilities"]) | {command["action"]}
        if command["action"] in ("start", "resume"):
            required |= START_CAPABILITIES
        require = getattr(self.transport, "require", None)
        if not callable(require):
            raise PermissionError("transport has no verified capability check")
        require(required)

    def command(self, command, *, authority=None):
        self.contracts.validate("harness-command", command)
        if command["host"] != self.host_id:
            raise PermissionError("wrong host")
        fingerprint = digest(command)
        old = self.db.execute(
            "SELECT fingerprint,state,observation FROM operations WHERE id=?",
            (command["operation_id"],),
        ).fetchone()
        if old:
            if old[0] != fingerprint:
                raise Conflict("operation identity conflict")
            return self.lookup(command["operation_id"]) | {"historical": True}
        if not self.online:
            raise ConnectionError("host_offline")
        self._authorize(command, authority)
        self._binding(command)
        self._capabilities(command)
        with self.db:
            self.db.execute(
                "INSERT INTO operations VALUES(?,?,?,'unknown',NULL)",
                (command["operation_id"], fingerprint, canonical(command)),
            )
            if command["action"] == "start":
                self.db.execute(
                    "INSERT INTO bindings VALUES(?,?,?,?,?,?,?,?)",
                    (
                        command["session"],
                        command["generation"],
                        command["assignment"],
                        command["assignment_revision"],
                        command["ownership_generation"],
                        "unknown",
                        None,
                        command["operation_id"],
                    ),
                )
            elif command["action"] in ("interrupt", "retire"):
                self.db.execute(
                    "UPDATE bindings SET state='stop_unknown',operation_id=? WHERE session=?",
                    (command["operation_id"], command["session"]),
                )
            else:
                self.db.execute(
                    "UPDATE bindings SET state='unknown',operation_id=? WHERE session=?",
                    (command["operation_id"], command["session"]),
                )
        # The unknown journal entry is durable before transport invocation.
        # A crash after an accepted request must reconcile before retry.
        try:
            observation = self.transport.execute(command["action"], command)
            self.contracts.validate("harness-observation", observation)
            if observation["operation_id"] != command["operation_id"]:
                raise Conflict("transport returned wrong operation")
        except BaseException:
            raise
        self._record(command, observation)
        return self.lookup(command["operation_id"])

    def _record(self, command, observation):
        self._observation(command, observation)
        state = observation["state"]
        with self.db:
            binding = self.db.execute(
                "SELECT operation_id FROM bindings WHERE session=?",
                (command["session"],),
            ).fetchone()
            if binding is None or binding[0] != command["operation_id"]:
                self.db.execute(
                    "UPDATE operations SET state='held',observation=? WHERE id=?",
                    (canonical(observation), command["operation_id"]),
                )
                return
            self.db.execute(
                "UPDATE operations SET state=?,observation=? WHERE id=?",
                (state, canonical(observation), command["operation_id"]),
            )
            if state in ("active", "idle", "retired"):
                self.db.execute(
                    "INSERT INTO bindings VALUES(?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(session) DO UPDATE SET state=excluded.state,"
                    "native_session_id=excluded.native_session_id,operation_id=excluded.operation_id",
                    (
                        command["session"],
                        command["generation"],
                        command["assignment"],
                        command["assignment_revision"],
                        command["ownership_generation"],
                        state,
                        observation["native_session_id"],
                        command["operation_id"],
                    ),
                )
            elif command["action"] in ("interrupt", "retire"):
                self.db.execute(
                    "UPDATE bindings SET state='stop_unknown' WHERE session=?",
                    (command["session"],),
                )

    def _observation(self, command, observation):
        self.contracts.validate("harness-observation", observation)
        if observation["operation_id"] != command["operation_id"]:
            raise Conflict("transport returned wrong operation")
        allowed = {
            "start": {"active", "idle", "partial", "unknown", "failed"},
            "resume": {"active", "idle", "partial", "unknown", "failed"},
            "interrupt": {"idle", "retired", "unknown", "failed"},
            "retire": {"retired", "unknown", "failed"},
        }[command["action"]]
        if observation["state"] not in allowed:
            raise Conflict("observation contradicts command action")
        if (
            observation["state"] in ("active", "idle", "retired")
            and not observation["native_session_id"]
        ):
            raise Conflict("settled observation lacks native session")
        binding = self.db.execute(
            "SELECT native_session_id FROM bindings WHERE session=?",
            (command["session"],),
        ).fetchone()
        if binding and binding[0] and observation["native_session_id"] != binding[0]:
            raise Conflict("native session identity changed")

    def reconcile(self, operation_id, *, authority=None):
        row = self.db.execute(
            "SELECT command,state FROM operations WHERE id=?", (operation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(operation_id)
        if row[1] != "unknown":
            return self.lookup(operation_id)
        if not self.online:
            raise ConnectionError("host_offline")
        command = strict_loads(row[0])
        observation = self.transport.lookup(operation_id)
        if observation is None:
            # Absence does not imply a safe retry. Check current authority
            # and let the service issue a new operation after reconciliation.
            self._authorize(command, authority)
            return self.lookup(operation_id)
        self.contracts.validate("harness-observation", observation)
        if observation["operation_id"] != operation_id:
            raise Conflict("lookup returned wrong operation")
        try:
            self._authorize(command, authority)
        except PermissionError:
            # Retain the historical host result, but do not reinstate a
            # binding after owner transfer, revocation, stop or expiry.
            with self.db:
                self.db.execute(
                    "UPDATE operations SET state='held',observation=? WHERE id=?",
                    (canonical(observation), operation_id),
                )
                self.db.execute(
                    "UPDATE bindings SET state='stop_unknown' WHERE session=? AND operation_id=?",
                    (command["session"], operation_id),
                )
            return self.lookup(operation_id)
        self._record(command, observation)
        return self.lookup(operation_id)

    def reconcile_binding(self, session, *, authority=None):
        """Revalidate an offline binding using the last host operation.

        A historical operation receipt cannot prove the process is online.
        The transport must provide a fresh session observation; unsupported,
        unknown or absent observations leave the binding unavailable.
        """
        if not self.online:
            raise ConnectionError("host_offline")
        binding = self.db.execute(
            "SELECT state,operation_id FROM bindings WHERE session=?", (session,)
        ).fetchone()
        if binding is None:
            raise KeyError(session)
        if binding[0] == "stop_unknown":
            return "stop_unknown"
        row = self.db.execute(
            "SELECT command FROM operations WHERE id=?", (binding[1],)
        ).fetchone()
        if row is None:
            return "host_offline"
        command = strict_loads(row[0])
        observer = getattr(self.transport, "observe_session", None)
        if observer is None:
            return "host_offline"
        observation = observer(session, command["operation_id"])
        if observation is None:
            return "host_offline"
        self.contracts.validate("harness-observation", observation)
        if observation["operation_id"] != command["operation_id"]:
            raise Conflict("host binding lookup mismatch")
        try:
            self._authorize(command, authority)
        except PermissionError:
            with self.db:
                self.db.execute(
                    "UPDATE bindings SET state='stop_unknown' WHERE session=?",
                    (session,),
                )
            return "stop_unknown"
        self._observation(command, observation)
        if observation["state"] not in ("active", "idle", "retired"):
            return "host_offline"
        self._record(command, observation)
        return observation["state"]

    def eligible_return(self, command, observation, *, authority=None):
        """Eligibility for verification only; never assignment completion."""
        self.contracts.validate("harness-command", command)
        self.contracts.validate("harness-observation", observation)
        try:
            self._authorize(command, authority)
            self._observation(command, observation)
        except PermissionError:
            return False
        except Conflict:
            return False
        saved = self.lookup(command["operation_id"])
        if (
            not saved
            or saved["state"] != observation["state"]
            or saved["observation"] != observation
        ):
            return False
        return bool(
            observation["operation_id"] == command["operation_id"]
            and observation["state"] == "idle"
            and observation["evidence"]
            and observation["usage_state"] == "known"
        )
