"""Single-writer SQLite namespaces for credential-free local development.

The writer lock coordinates trusted components. It is not a sandbox or an
authorization boundary against other code running under the same Unix user.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .contracts import Contracts, canonical, identifier, strict_loads
from .transitions import transition

WRITERS = {
    "odin_history": "service",
    "transcript_archive": "capture",
    "surface_events": "sensors",
    "execution_ledger": "saga_adapter",
}


class Conflict(ValueError):
    """A mutation was rejected before commit."""


class Refusal:
    """Marks an error whose text is a fixed, safe code a surface may relay.

    Use it only for a deterministic refusal: an identical retry is refused
    again, so the caller must change something first. The code never carries
    an input value, path or record from another project.
    """


class Refused(Refusal, Conflict):
    """A relayable refusal of a mutation or its arguments."""


class AccessRefused(Refusal, PermissionError):
    """A relayable refusal of access within the caller's own project."""


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def event(
    kind,
    payload,
    *,
    namespace="odin_history",
    producer="service",
    scope=None,
    source_seq=None,
    key=None,
):
    uid = identifier()
    return {
        "id": uid,
        "envelope": 1,
        "namespace": namespace,
        "producer": producer,
        "kind": kind,
        "scope": scope or {},
        "source_seq": source_seq,
        "received_at": now(),
        "causation": None,
        "correlation": uid,
        "payload": payload,
        "dedupe_key": key or uid,
    }


class Store:
    def __init__(self, directory: Path, namespace="odin_history", writer="service"):
        if WRITERS.get(namespace) != writer:
            raise PermissionError("wrong namespace writer")
        self.namespace, self.writer = namespace, writer
        self.contracts = Contracts()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / f"{namespace}.sqlite3"
        # Refuse symlink files; local state directories are trusted, private input.
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
            raise Conflict("namespace already has a writer") from None
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            self.db = sqlite3.connect(self.path, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise Conflict("unsupported database version")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS records
                  (id TEXT PRIMARY KEY, kind TEXT NOT NULL, rev INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history
                  (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS inbox
                  (id TEXT PRIMARY KEY, producer TEXT NOT NULL, dedupe TEXT NOT NULL,
                   body TEXT NOT NULL, state TEXT NOT NULL, priority INTEGER NOT NULL,
                   UNIQUE(producer, dedupe));
                CREATE TABLE IF NOT EXISTS cursors (producer TEXT PRIMARY KEY, seq INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS effects
                  (id TEXT PRIMARY KEY, body TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS control (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS timers
                  (key TEXT PRIMARY KEY, due TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS mirror
                  (id TEXT PRIMARY KEY, source_seq INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS capture
                  (key TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL,
                   PRIMARY KEY(key, revision));
                PRAGMA user_version=1;
            """)
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self.lock.close()
            raise
        self.dispatch_enabled = False

    def close(self):
        self.db.close()
        self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextlib.contextmanager
    def transaction(self):
        # Service commands compose local operations in one history transaction.
        # Nested operations use savepoints; they must never commit the caller.
        nested = self.db.in_transaction
        self._transaction_sequence = getattr(self, "_transaction_sequence", 0) + 1
        savepoint = f"odin_local_{self._transaction_sequence}"
        self.db.execute(f"SAVEPOINT {savepoint}" if nested else "BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute(f"RELEASE SAVEPOINT {savepoint}" if nested else "COMMIT")
        except BaseException:
            if nested:
                self.db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.db.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self.db.execute("ROLLBACK")
            raise

    def _history(self, kind, payload):
        item = event(kind, payload, namespace=self.namespace, producer=self.writer)
        self.contracts.validate("event", item)
        self.db.execute(
            "INSERT INTO history(id,body) VALUES(?,?)", (item["id"], canonical(item))
        )

    def _core(self):
        if self.namespace != "odin_history":
            raise PermissionError("records/effects belong to the service namespace")

    def get(self, record_id):
        row = self.db.execute(
            "SELECT body FROM records WHERE id=?", (record_id,)
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return strict_loads(row[0])

    def records(self, kind=None):
        rows = self.db.execute(
            "SELECT body FROM records WHERE (? IS NULL OR kind=?) ORDER BY id",
            (kind, kind),
        )
        return [strict_loads(r[0]) for r in rows]

    def _put(self, record, expected_revision):
        self._core()
        if type(expected_revision) is not int or expected_revision < 0:
            raise Conflict("expected_revision must be a nonnegative integer")
        self.contracts.validate("records", record)
        row = self.db.execute(
            "SELECT rev,body FROM records WHERE id=?", (record["id"],)
        ).fetchone()
        current = row[0] if row else 0
        if (
            transition("revision", {"current": current, "expected": expected_revision})
            != "apply"
            or record["rev"] != current + 1
        ):
            raise Conflict("stale_revision")
        if row:
            old = strict_loads(row[1])
            if (
                old["record_type"] != record["record_type"]
                or old["created_at"] != record["created_at"]
            ):
                raise Conflict("immutable record identity")
        if datetime.fromisoformat(record["updated_at"]) < datetime.fromisoformat(
            record["created_at"]
        ):
            raise Conflict("invalid timestamp order")
        self.db.execute(
            "INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET rev=excluded.rev,body=excluded.body",
            (record["id"], record["record_type"], record["rev"], canonical(record)),
        )
        self._history("record.changed", {"record": record})

    def create(self, record):
        with self.transaction():
            self._put(record, 0)

    def update(
        self, record_id, patch, expected_revision, *, owner=None, generation=None
    ):
        with self.transaction():
            old = self.get(record_id)
            if any(
                k in patch
                for k in (
                    "id",
                    "record_type",
                    "rev",
                    "created_at",
                    "schema_version",
                    "owner",
                    "ownership_generation",
                )
            ):
                raise Conflict("immutable or dedicated-operation field")
            if owner is not None:
                session = self.get(owner)
                if (
                    old.get("owner") != owner
                    or old.get("ownership_generation") != generation
                    or session["record_type"] != "PlanningSession"
                    or session["state"] not in ("active", "idle")
                    or session["project"] != old.get("project")
                ):
                    raise Conflict("stale_owner")
            result = old | patch | {"rev": old["rev"] + 1, "updated_at": now()}
            self._put(result, expected_revision)
            return result

    def transfer(self, commitment_id, new_owner, expected_revision):
        with self.transaction():
            old = self.get(commitment_id)
            session = self.get(new_owner)
            if (
                old["record_type"] != "Commitment"
                or session["record_type"] != "PlanningSession"
            ):
                raise Conflict("invalid ownership types")
            if session["project"] != old["project"] or session["state"] not in (
                "active",
                "idle",
            ):
                raise Conflict("invalid new owner")
            result = old | {
                "owner": new_owner,
                "ownership_generation": old["ownership_generation"] + 1,
                "rev": old["rev"] + 1,
                "updated_at": now(),
            }
            self._put(result, expected_revision)
            assignments = {
                r["id"]
                for r in self.records("Assignment")
                if r["commitment"] == commitment_id
            }
            for effect in self.effects():
                if effect["assignment"] in assignments and effect["state"] in (
                    "queued",
                    "held",
                ):
                    self._effect_state(
                        effect, "held", dispatch_blocked_by="ownership_transfer"
                    )
            return result

    def intake(self, item):
        self._core()
        self.contracts.validate("event", item)
        if item["namespace"] != self.namespace:
            raise PermissionError("wrong namespace")
        with self.transaction():
            duplicate = self.db.execute(
                "SELECT body FROM inbox WHERE id=? OR (producer=? AND dedupe=?)",
                (item["id"], item["producer"], item["dedupe_key"]),
            ).fetchone()
            if duplicate:
                old = strict_loads(duplicate[0])
                if any(
                    old.get(k) != item.get(k)
                    for k in (
                        "producer",
                        "kind",
                        "scope",
                        "payload",
                        "payload_ref",
                        "source_seq",
                    )
                ):
                    raise Conflict("event_identity_conflict")
                return False
            cursor = self.db.execute(
                "SELECT seq FROM cursors WHERE producer=?", (item["producer"],)
            ).fetchone()
            seq = item["source_seq"]
            if cursor and seq is not None and seq <= cursor[0]:
                return False
            priority = 0 if item["kind"].startswith("operator.command.") else 1
            self.db.execute(
                "INSERT INTO inbox VALUES(?,?,?,?,?,?)",
                (
                    item["id"],
                    item["producer"],
                    item["dedupe_key"],
                    canonical(item),
                    "received",
                    priority,
                ),
            )
            if seq is not None:
                self.db.execute(
                    "INSERT INTO cursors VALUES(?,?) ON CONFLICT(producer) DO UPDATE SET seq=excluded.seq",
                    (item["producer"], seq),
                )
            self._history("event.received", {"event": item})
            return True

    def process(self, handler):
        self._core()
        rows = self.db.execute(
            "SELECT id,body FROM inbox WHERE state='received' ORDER BY priority,rowid"
        ).fetchall()
        for row in rows:
            with self.transaction():
                item = strict_loads(row["body"])
                handler(self, item)
                self._history("event.processed", {"event": item})
                self.db.execute(
                    "UPDATE inbox SET state='processed' WHERE id=?", (row["id"],)
                )
        return len(rows)

    def _enqueue(self, effect, payload):
        self._core()
        self.contracts.validate("records", effect)
        if (
            effect["record_type"] != "Effect"
            or digest(payload) != effect["payload_digest"]
        ):
            raise Conflict("invalid effect content")
        if (
            effect["state"] != "queued"
            or effect["rev"] != 1
            or effect["attempts"] != 0
            or effect["receipt"] is not None
        ):
            raise Conflict("new effects must be queued and unattempted")
        old = self.db.execute(
            "SELECT body,payload FROM effects WHERE id=?", (effect["operation_id"],)
        ).fetchone()
        if old:
            prior = strict_loads(old[0])
            authority = (
                "destination",
                "destination_capability",
                "assignment",
                "owner_generation",
                "delegation_version",
                "approval_digest",
            )
            if old[1] != canonical(payload) or any(
                prior[k] != effect[k] for k in authority
            ):
                raise Conflict("operation_conflict")
            return False
        self.db.execute(
            "INSERT INTO effects VALUES(?,?,?)",
            (effect["operation_id"], canonical(effect), canonical(payload)),
        )
        self._history("effect.queued", {"effect": effect})
        return True

    def enqueue(self, effect, payload):
        with self.transaction():
            return self._enqueue(effect, payload)

    def effects(self):
        return [
            strict_loads(row[0])
            for row in self.db.execute("SELECT body FROM effects ORDER BY rowid")
        ]

    def _effect_state(self, effect, state, **fields):
        result = (
            effect
            | fields
            | {"state": state, "rev": effect["rev"] + 1, "updated_at": now()}
        )
        self.contracts.validate("records", result)
        self.db.execute(
            "UPDATE effects SET body=? WHERE id=?",
            (canonical(result), result["operation_id"]),
        )
        self._history("effect.state", {"effect": result})
        return result

    def _stop(self, reason):
        self.db.execute("INSERT OR REPLACE INTO control VALUES('stopped',?)", (reason,))
        self.db.execute("DELETE FROM timers")
        for effect in self.effects():
            if effect["state"] in ("queued", "held"):
                self._effect_state(
                    effect, "cancelled_stale", dispatch_blocked_by="stop"
                )
        self._history(
            "control.stopped", {"reason": reason, "remote_outcome": "unconfirmed"}
        )

    def stop(self, reason):
        self._core()
        with self.transaction():
            self._stop(reason)

    def stopped(self):
        return (
            self.db.execute("SELECT 1 FROM control WHERE key='stopped'").fetchone()
            is not None
        )

    def authorized(self, effect):
        if effect["destination"] == "saga:stop":
            return True
        if self.stopped():
            return False
        if effect["assignment"]:
            try:
                assignment = self.get(effect["assignment"])
                commitment = self.get(assignment["commitment"])
            except KeyError:
                return False
            if (
                assignment["state"] in ("failed", "cancelled", "completed")
                or commitment["state"] in ("abandoned", "closed", "satisfied")
                or commitment["ownership_generation"] != effect["owner_generation"]
            ):
                return False
        return True

    def dispatch(self, transport):
        self._core()
        if not self.dispatch_enabled:
            raise Conflict("recovery required")
        if not getattr(transport, "fake_backend", False):
            raise PermissionError("live transports are not enabled")
        if self.db.execute(
            "SELECT 1 FROM inbox WHERE state='received' AND priority=0"
        ).fetchone():
            raise Conflict("process pending operator controls before dispatch")
        for effect in self.effects():
            if effect["state"] != "queued":
                continue
            with self.transaction():
                if not self.authorized(effect):
                    self._effect_state(effect, "cancelled_stale")
                    continue
                active = self._effect_state(
                    effect, "in_flight", attempts=effect["attempts"] + 1
                )
            payload = strict_loads(
                self.db.execute(
                    "SELECT payload FROM effects WHERE id=?", (active["operation_id"],)
                ).fetchone()[0]
            )
            try:
                receipt = transport.send(
                    active["operation_id"], active["destination"], payload
                )
            except Conflict:
                with self.transaction():
                    self._effect_state(active, "failed", reconciliation="refused")
                raise
            except Exception:
                with self.transaction():
                    self._effect_state(active, "unknown", reconciliation="pending")
                raise
            with self.transaction():
                self._effect_state(
                    active, "delivered", receipt=receipt, reconciliation="completed"
                )

    def recover(self, transport, handler):
        self._core()
        if not getattr(transport, "fake_backend", False):
            raise PermissionError("live transports are not enabled")
        self.dispatch_enabled = False
        with self.transaction():
            for effect in self.effects():
                if effect["state"] not in ("in_flight", "unknown"):
                    continue
                if effect["destination_capability"] != "idempotent_by_key":
                    self._effect_state(effect, "unknown", reconciliation="unconfirmed")
                    continue
                result = transport.lookup(effect["operation_id"])
                state = transition(
                    "delivery",
                    {
                        "lookup": result["state"],
                        "idempotent": True,
                        "authorized": False,
                    },
                )
                fields = {"reconciliation": result["state"]}
                if state == "delivered":
                    fields["receipt"] = result["receipt"]
                self._effect_state(effect, state, **fields)
        self.process(handler)  # Queued controls commit before retry eligibility.
        with self.transaction():
            for effect in self.effects():
                if effect["state"] not in ("queued", "held", "unknown"):
                    continue
                if not self.authorized(effect):
                    if effect["state"] != "unknown":
                        self._effect_state(effect, "cancelled_stale")
                elif effect["state"] == "unknown":
                    state = transition(
                        "delivery",
                        {
                            "lookup": effect["reconciliation"],
                            "idempotent": effect["destination_capability"]
                            == "idempotent_by_key",
                            "authorized": True,
                        },
                    )
                    if state == "queued":
                        self._effect_state(effect, state)
            for session in self.records("PlanningSession"):
                if session["state"] == "active":
                    self._put(
                        session
                        | {
                            "state": "retiring",
                            "rev": session["rev"] + 1,
                            "updated_at": now(),
                        },
                        session["rev"],
                    )
        self.dispatch_enabled = True

    def project_history(self, destination):
        destination = Path(destination)
        data = "".join(
            row[0] + "\n"
            for row in self.db.execute("SELECT body FROM history ORDER BY seq")
        )
        temporary = destination.with_name(destination.name + ".tmp")
        fd = os.open(
            temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return hashlib.sha256(data.encode()).hexdigest()
