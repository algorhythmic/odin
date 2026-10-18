"""Local, permission checked semantic memory over the service event substrate.

This is deterministic ingestion of explicitly attributed statements. It does
not interpret source text or confer command/decision authority.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256

from .contracts import canonical, strict_loads
from .store import Conflict, now


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _span(value, length):
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r"\d+:\d+", value):
        raise Conflict("invalid source span")
    start, end = map(int, value.split(":"))
    if start >= end or end > length:
        raise Conflict("source span outside content")


class Memory:
    def __init__(self, store):
        store._core()
        self.store = store
        db = store.db
        db.execute("PRAGMA secure_delete=ON")
        migration = """
                CREATE TABLE IF NOT EXISTS memory_migrations(version INTEGER PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS memory_sources(
                  id TEXT NOT NULL, revision INTEGER NOT NULL, project TEXT NOT NULL,
                  producer TEXT NOT NULL, ingest_seq INTEGER NOT NULL,
                  body TEXT NOT NULL, redacted INTEGER NOT NULL DEFAULT 0,
                  learned_at TEXT,
                  PRIMARY KEY(id,revision));
                CREATE TABLE IF NOT EXISTS memory_statements(
                  id TEXT PRIMARY KEY, project TEXT NOT NULL, body TEXT NOT NULL,
                  redacted INTEGER NOT NULL DEFAULT 0, learned_at TEXT);
                CREATE TABLE IF NOT EXISTS memory_dependencies(
                  statement TEXT NOT NULL, depends_on TEXT NOT NULL,
                  PRIMARY KEY(statement,depends_on));
                CREATE TABLE IF NOT EXISTS memory_relations(
                  id TEXT PRIMARY KEY, project TEXT NOT NULL, kind TEXT NOT NULL,
                  subject TEXT NOT NULL, object TEXT NOT NULL, body TEXT NOT NULL,
                  learned_at TEXT);
                CREATE TABLE IF NOT EXISTS memory_revision(
                  project TEXT PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS memory_processing(
                  project TEXT NOT NULL, producer TEXT NOT NULL,
                  captured INTEGER NOT NULL DEFAULT 0, processed INTEGER NOT NULL DEFAULT 0,
                  holes TEXT NOT NULL DEFAULT '[]', failures TEXT NOT NULL DEFAULT '[]',
                  availability TEXT NOT NULL DEFAULT 'unknown',
                  availability_reason TEXT, PRIMARY KEY(project,producer));
                CREATE TABLE IF NOT EXISTS memory_processed(
                  project TEXT NOT NULL, producer TEXT NOT NULL, seq INTEGER NOT NULL,
                  PRIMARY KEY(project,producer,seq));
                CREATE TABLE IF NOT EXISTS memory_freshness(
                  source_class TEXT PRIMARY KEY, max_age_seconds INTEGER,
                  action TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS memory_redaction(
                  source TEXT NOT NULL, revision INTEGER NOT NULL,
                  destination TEXT NOT NULL, state TEXT NOT NULL,
                  PRIMARY KEY(source,revision,destination));
                CREATE TABLE IF NOT EXISTS memory_retrieval(
                  source TEXT NOT NULL, revision INTEGER NOT NULL,
                  retrieved_at TEXT NOT NULL, PRIMARY KEY(source,revision));
            """
        with store.transaction():
            db.execute(
                "CREATE TABLE IF NOT EXISTS memory_migrations(version INTEGER PRIMARY KEY)"
            )
            version = (
                db.execute("SELECT MAX(version) FROM memory_migrations").fetchone()[0]
                or 0
            )
            if version > 3:
                raise Conflict("unsupported memory database version")
            for statement in migration.split(";"):
                if statement.strip():
                    db.execute(statement)
            columns = {r[1] for r in db.execute("PRAGMA table_info(memory_statements)")}
            if "redacted" not in columns:
                db.execute(
                    "ALTER TABLE memory_statements ADD COLUMN redacted INTEGER NOT NULL DEFAULT 0"
                )
            for table in ("memory_sources", "memory_statements", "memory_relations"):
                columns = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                if "learned_at" not in columns:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN learned_at TEXT")
                db.execute(
                    f"UPDATE {table} SET learned_at=? WHERE learned_at IS NULL",
                    (now(),),
                )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS memory_unique_producer_seq ON memory_sources(project,producer,ingest_seq)"
            )
            db.execute("INSERT OR IGNORE INTO memory_migrations(version) VALUES(3)")

    def _bump(self, project):
        self.store.db.execute(
            "INSERT INTO memory_revision VALUES(?,1) ON CONFLICT(project) DO UPDATE SET revision=revision+1",
            (project,),
        )

    def dependency_revision(self, project):
        row = self.store.db.execute(
            "SELECT revision FROM memory_revision WHERE project=?", (project,)
        ).fetchone()
        return row[0] if row else 0

    def add_source(self, source):
        self.store.contracts.validate("memory-source", source)
        if sha256(source["content"].encode()).hexdigest() != source["digest"]:
            raise Conflict("source digest mismatch")
        _span(source["span"], len(source["content"]))
        if _instant(source["retrieved_at"]) < _instant(source["observed_at"]):
            raise Conflict("retrieval precedes observation")
        self._project(source["project"])
        db = self.store.db
        with self.store.transaction():
            row = db.execute(
                "SELECT revision,body,redacted FROM memory_sources WHERE id=? ORDER BY revision DESC LIMIT 1",
                (source["id"],),
            ).fetchone()
            if row:
                old = strict_loads(row[1])
                if (
                    old["project"] != source["project"]
                    or old["producer"] != source["producer"]
                ):
                    raise Conflict("source identity changed")
                if source["revision"] == row[0]:
                    if old == source or (
                        row[2]
                        and old["digest"] == source["digest"]
                        and old["project"] == source["project"]
                    ):
                        return False
                    raise Conflict("source revision already exists")
                tombstone = db.execute(
                    "SELECT 1 FROM memory_sources WHERE id=? AND redacted=1 LIMIT 1",
                    (source["id"],),
                ).fetchone()
                if tombstone:
                    raise Conflict("redacted source identity cannot be reused")
                if (
                    source["revision"] != row[0] + 1
                    or source["permissions_revision"] < old["permissions_revision"]
                ):
                    raise Conflict("source revision or permissions regressed")
                if (
                    source["readers"] != old["readers"]
                    and source["permissions_revision"] <= old["permissions_revision"]
                ):
                    raise Conflict("access changed without permission revision")
            elif source["revision"] != 1:
                raise Conflict("first source revision must be one")
            duplicate = db.execute(
                "SELECT id FROM memory_sources WHERE project=? AND producer=? AND ingest_seq=?",
                (source["project"], source["producer"], source["ingest_seq"]),
            ).fetchone()
            if duplicate:
                raise Conflict("producer sequence reused")
            db.execute(
                "INSERT INTO memory_sources(id,revision,project,producer,ingest_seq,body,learned_at) VALUES(?,?,?,?,?,?,?)",
                (
                    source["id"],
                    source["revision"],
                    source["project"],
                    source["producer"],
                    source["ingest_seq"],
                    canonical(source),
                    now(),
                ),
            )
            db.execute(
                "INSERT OR IGNORE INTO memory_processing(project,producer) VALUES(?,?)",
                (source["project"], source["producer"]),
            )
            db.execute(
                "UPDATE memory_processing SET captured=MAX(captured,?) WHERE project=? AND producer=?",
                (source["ingest_seq"], source["project"], source["producer"]),
            )
            self._bump(source["project"])
            self.store._history(
                "memory.source",
                {
                    "id": source["id"],
                    "revision": source["revision"],
                    "project": source["project"],
                },
            )
        return True

    def add_statement(self, statement):
        self.store.contracts.validate("memory-statement", statement)
        self._project(statement["project"])
        if statement["kind"] == "decision" and statement["status"] == "accepted":
            if not self._accepted_decision(statement):
                raise Conflict("accepted decision lacks matching canonical record")
        elif statement["status"] == "accepted":
            raise Conflict("only canonical decision may be accepted")
        db = self.store.db
        with self.store.transaction():
            existing = db.execute(
                "SELECT body FROM memory_statements WHERE id=?", (statement["id"],)
            ).fetchone()
            if existing:
                if strict_loads(existing[0]) == statement:
                    return False
                raise Conflict("statement is immutable")
            for ref in statement["source_refs"]:
                row = db.execute(
                    "SELECT project,redacted,body FROM memory_sources WHERE id=? AND revision=?",
                    (ref["id"], ref["revision"]),
                ).fetchone()
                if not row or row[0] != statement["project"] or row[1]:
                    raise Conflict("missing, foreign or redacted source revision")
                source = strict_loads(row[2])
                _span(ref["span"], len(source["content"]))
                if _instant(statement["recorded_at"]) < _instant(source["observed_at"]):
                    raise Conflict("statement learned before source observation")
            for ref in statement["statement_refs"]:
                row = db.execute(
                    "SELECT project FROM memory_statements WHERE id=?", (ref,)
                ).fetchone()
                if not row or row[0] != statement["project"]:
                    raise Conflict("missing or foreign statement dependency")
            db.execute(
                "INSERT INTO memory_statements(id,project,body,learned_at) VALUES(?,?,?,?)",
                (statement["id"], statement["project"], canonical(statement), now()),
            )
            for ref in statement["statement_refs"]:
                db.execute(
                    "INSERT INTO memory_dependencies VALUES(?,?)",
                    (statement["id"], ref),
                )
            self._bump(statement["project"])
            self.store._history(
                "memory.statement",
                {"id": statement["id"], "project": statement["project"]},
            )
        return True

    def _project(self, project):
        try:
            record = self.store.get(project)
        except KeyError:
            raise Conflict("unknown project") from None
        if record["record_type"] != "Project":
            raise Conflict("not a project")

    def change_access(self, source_id, readers, permissions_revision, ingest_seq):
        """Append an access revision; never mutate evidence or observation time."""
        row = self.store.db.execute(
            "SELECT body,redacted FROM memory_sources WHERE id=? ORDER BY revision DESC LIMIT 1",
            (source_id,),
        ).fetchone()
        if not row or row[1]:
            raise Conflict("source unavailable")
        old = strict_loads(row[0])
        if permissions_revision <= old["permissions_revision"]:
            raise Conflict("access revision must advance")
        revised = old | {
            "revision": old["revision"] + 1,
            "readers": readers,
            "permissions_revision": permissions_revision,
            "ingest_seq": ingest_seq,
        }
        return self.add_source(revised)

    def retrieved(self, source_id, revision, retrieved_at):
        _instant(retrieved_at)
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT project,redacted FROM memory_sources WHERE id=? AND revision=?",
                (source_id, revision),
            ).fetchone()
            if not row or row[1]:
                raise Conflict("source unavailable")
            self.store.db.execute(
                "INSERT INTO memory_retrieval VALUES(?,?,?) ON CONFLICT(source,revision) DO UPDATE SET retrieved_at=excluded.retrieved_at",
                (source_id, revision, retrieved_at),
            )
            self._bump(row[0])
            self.store._history(
                "memory.retrieved",
                {"id": source_id, "revision": revision, "project": row[0]},
            )

    def _accepted_decision(self, statement, *, require_exact=True):
        ref = statement["authority_ref"]
        if ref is None:
            return False
        try:
            record = self.store.get(ref["commitment"])
        except KeyError:
            return False
        return (
            record["record_type"] == "Commitment"
            and record["project"] == statement["project"]
            and (
                record["rev"] == ref["revision"]
                if require_exact
                else record["rev"] >= ref["revision"]
            )
            and any(
                d["id"] == ref["decision"] and d["choice"] == statement["text"]
                for d in record["decisions"]
            )
        )

    def relate(self, relation):
        required = {"id", "project", "kind", "subject", "object", "recorded_at"}
        if set(relation) != required or relation["kind"] not in {
            "corrects",
            "supersedes",
            "disputes",
            "retracts",
        }:
            raise ValueError("invalid relation")
        self.store.contracts.validate("memory-relation", relation)
        with self.store.transaction():
            members = {}
            for key in ("subject", "object"):
                row = self.store.db.execute(
                    "SELECT project,body,redacted FROM memory_statements WHERE id=?",
                    (relation[key],),
                ).fetchone()
                if not row or row[0] != relation["project"]:
                    raise Conflict("foreign or absent statement")
                if row[2]:
                    raise Conflict("redacted statement")
                members[key] = strict_loads(row[1])
            if _instant(relation["recorded_at"]) < max(
                _instant(v["recorded_at"]) for v in members.values()
            ):
                raise Conflict("relationship learned before statements")
            if (
                members["object"]["status"] == "accepted"
                and relation["kind"] != "disputes"
            ):
                raise Conflict("relation cannot override canonical decision")
            if relation["kind"] != "disputes" and not (
                members["subject"]["status"] == "accepted"
                and self._accepted_decision(members["subject"], require_exact=False)
            ):
                raise Conflict(
                    "destructive relation requires canonical accepted decision"
                )
            self.store.db.execute(
                "INSERT INTO memory_relations(id,project,kind,subject,object,body,learned_at) VALUES(?,?,?,?,?,?,?)",
                (
                    relation["id"],
                    relation["project"],
                    relation["kind"],
                    relation["subject"],
                    relation["object"],
                    canonical(relation),
                    now(),
                ),
            )
            self._bump(relation["project"])
            self.store._history("memory.relationship", relation)

    def set_freshness(self, source_class, max_age_seconds, action="warn"):
        if (
            not source_class
            or (
                max_age_seconds is not None
                and (type(max_age_seconds) is not int or max_age_seconds < 0)
            )
            or action not in {"warn", "hold", "refresh"}
        ):
            raise ValueError("invalid freshness policy")
        with self.store.transaction():
            self.store.db.execute(
                "INSERT INTO memory_freshness VALUES(?,?,?) ON CONFLICT(source_class) DO UPDATE SET max_age_seconds=excluded.max_age_seconds,action=excluded.action",
                (source_class, max_age_seconds, action),
            )
            self.store._history(
                "memory.freshness_policy",
                {
                    "source_class": source_class,
                    "max_age_seconds": max_age_seconds,
                    "action": action,
                },
            )
            projects = {
                r[0]
                for r in self.store.db.execute(
                    "SELECT project,body FROM memory_sources"
                )
                if strict_loads(r[1])["source_class"] == source_class
            }
            for project in projects:
                self._bump(project)

    def processing(
        self,
        project,
        producer,
        *,
        processed=None,
        failed=None,
        availability=None,
        reason=None,
    ):
        self._project(project)
        db = self.store.db
        with self.store.transaction():
            db.execute(
                "INSERT OR IGNORE INTO memory_processing(project,producer) VALUES(?,?)",
                (project, producer),
            )
            row = db.execute(
                "SELECT captured,processed,holes,failures,availability,availability_reason FROM memory_processing WHERE project=? AND producer=?",
                (project, producer),
            ).fetchone()
            done = {
                x[0]
                for x in db.execute(
                    "SELECT seq FROM memory_processed WHERE project=? AND producer=?",
                    (project, producer),
                )
            }
            if processed is not None:
                if type(processed) is not int or processed < 1 or processed > row[0]:
                    raise Conflict("invalid processed sequence")
                captured = db.execute(
                    "SELECT 1 FROM memory_sources WHERE project=? AND producer=? AND ingest_seq=?",
                    (project, producer, processed),
                ).fetchone()
                if not captured:
                    raise Conflict("cannot process uncaptured sequence")
                db.execute(
                    "INSERT OR IGNORE INTO memory_processed VALUES(?,?,?)",
                    (project, producer, processed),
                )
                done.add(processed)
            cursor = row[1]
            while cursor + 1 in done:
                cursor += 1
            failures = {item["seq"]: item for item in strict_loads(row[3])}
            if failed is not None:
                if type(failed) is not int or failed < 1 or failed > row[0]:
                    raise Conflict("invalid failed sequence")
                source_row = db.execute(
                    "SELECT id FROM memory_sources WHERE project=? AND producer=? AND ingest_seq=? ORDER BY revision DESC LIMIT 1",
                    (project, producer, failed),
                ).fetchone()
                if not source_row:
                    raise Conflict("cannot fail uncaptured sequence")
                failures[failed] = {"seq": failed, "source": source_row[0]}
            for seq in done:
                failures.pop(seq, None)
            covered = sorted(x for x in done | set(failures) if cursor < x <= row[0])
            holes = []
            next_seq = cursor + 1
            for seq in covered:
                if next_seq < seq:
                    holes.append([next_seq, seq - 1])
                next_seq = seq + 1
            if next_seq <= row[0]:
                holes.append([next_seq, row[0]])
            state = availability if availability is not None else row[4]
            if state not in {"unknown", "available", "unavailable"}:
                raise ValueError("invalid availability")
            db.execute(
                "UPDATE memory_processing SET processed=?,holes=?,failures=?,availability=?,availability_reason=? WHERE project=? AND producer=?",
                (
                    cursor,
                    canonical(holes),
                    canonical([failures[k] for k in sorted(failures)]),
                    state,
                    reason if availability is not None else row[5],
                    project,
                    producer,
                ),
            )
            self._bump(project)
            self.store._history(
                "memory.processing",
                {
                    "project": project,
                    "producer": producer,
                    "processed": cursor,
                    "availability": state,
                },
            )

    def redact(self, source_id, revision, destinations):
        if (
            not isinstance(destinations, list)
            or not destinations
            or any(not isinstance(d, str) or not d for d in destinations)
            or len(set(destinations)) != len(destinations)
        ):
            raise ValueError("redaction requires distinct destinations")
        db = self.store.db
        with self.store.transaction():
            row = db.execute(
                "SELECT project FROM memory_sources WHERE id=? AND revision=?",
                (source_id, revision),
            ).fetchone()
            if not row:
                raise KeyError((source_id, revision))
            original = strict_loads(
                db.execute(
                    "SELECT body FROM memory_sources WHERE id=? AND revision=?",
                    (source_id, revision),
                ).fetchone()[0]
            )
            original["content"] = ""
            original["locator"] = "[redacted]"
            original["span"] = None
            db.execute(
                "UPDATE memory_sources SET redacted=1,body=? WHERE id=? AND revision=?",
                (canonical(original), source_id, revision),
            )
            statements = {
                r[0]: strict_loads(r[1])
                for r in db.execute(
                    "SELECT id,body FROM memory_statements WHERE project=? AND redacted=0",
                    (row[0],),
                )
            }
            affected = {
                sid
                for sid, item in statements.items()
                if any(
                    ref["id"] == source_id and ref["revision"] == revision
                    for ref in item["source_refs"]
                )
            }
            changed = True
            while changed:
                before = len(affected)
                affected |= {
                    sid
                    for sid, item in statements.items()
                    if set(item["statement_refs"]) & affected
                }
                changed = len(affected) != before
            for sid in affected:
                item = statements[sid]
                item["text"] = "[redacted]"
                item["speaker"] = "[redacted]"
                for ref in item["source_refs"]:
                    ref["span"] = None
                db.execute(
                    "UPDATE memory_statements SET body=?,redacted=1 WHERE id=?",
                    (canonical(item), sid),
                )
            legacy_history = self._quarantine_continuity(row[0])
            for destination in [*destinations, "local_storage"]:
                db.execute(
                    "INSERT OR IGNORE INTO memory_redaction VALUES(?,?,?,'pending')",
                    (source_id, revision, destination),
                )
            if legacy_history:
                db.execute(
                    "INSERT OR IGNORE INTO memory_redaction VALUES(?,?,'legacy_history','pending')",
                    (source_id, revision),
                )
            self._bump(row[0])
            self.store._history(
                "memory.redacted",
                {
                    "id": source_id,
                    "revision": revision,
                    "project": row[0],
                    "destinations": destinations,
                },
            )

    def _quarantine_continuity(self, project):
        """Scrub project-memory descendants while preserving commitments."""
        db = self.store.db
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='continuity_decisions'"
        ).fetchone()
        if not exists:
            return False
        rows = db.execute(
            "SELECT request_id,body FROM continuity_decisions WHERE project=?",
            (project,),
        ).fetchall()
        request_ids = {row[0] for row in rows}
        legacy = False
        for request_id, body in rows:
            meta = strict_loads(body)
            if meta.get("redacted"):
                continue
            request = self.store.get(request_id)
            if request[
                "question"
            ] != "Prepared decision; inspect scoped metadata" or any(
                not option.startswith("choice:") for option in request["options"]
            ):
                legacy = True
            patch = {"question": "Prepared decision unavailable", "options": []}
            if request["state"] in {"open", "delivered", "expired"}:
                patch["state"] = "cancelled"
            if request["response"] is not None and not request["response"].startswith(
                "choice:"
            ):
                legacy = True
                patch["response"] = "[redacted]"
            self.store.update(request_id, patch, request["rev"])
            for link in meta.get("commitments", []):
                commitment = self.store.get(link["id"])
                linked = [
                    d for d in commitment["open_decisions"] if d["id"] == request_id
                ]
                if linked:
                    if any(d["text"] != "Prepared decision" for d in linked):
                        legacy = True
                    remaining = [
                        d for d in commitment["open_decisions"] if d["id"] != request_id
                    ]
                    self.store.update(
                        commitment["id"],
                        {"open_decisions": remaining},
                        commitment["rev"],
                    )
            tombstone = {
                "redacted": True,
                "project": project,
                "recipient": meta.get("recipient"),
                "memory_revision": meta.get("memory_revision"),
            }
            db.execute(
                "UPDATE continuity_decisions SET body=? WHERE request_id=?",
                (canonical(tombstone), request_id),
            )
        gateway = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gateway_commands'"
        ).fetchone()
        if gateway:
            for command_id, raw in db.execute(
                "SELECT id,result FROM gateway_commands"
            ).fetchall():
                receipt = strict_loads(raw)
                result = receipt.get("result", {})
                if (
                    isinstance(result, dict)
                    and result.get("record_type") == "HumanRequest"
                    and result.get("id") in request_ids
                ):
                    db.execute(
                        "UPDATE gateway_commands SET result=? WHERE id=?",
                        (
                            canonical(
                                receipt | {"result": {"projection_not_cached": True}}
                            ),
                            command_id,
                        ),
                    )
        for history_row in db.execute("SELECT body FROM history"):
            item = strict_loads(history_row[0])
            if item["kind"] == "gateway.command":
                command = item["payload"].get("command", {})
                payload = command.get("payload", {})
                decision = payload.get("decision")
                if (
                    command.get("action") == "prepare_decision"
                    and isinstance(decision, dict)
                    and decision.get("project") == project
                ):
                    legacy = True
            elif item["kind"] == "record.changed":
                record = item["payload"].get("record", {})
                if record.get("id") in request_ids and record.get("question") not in {
                    "Prepared decision; inspect scoped metadata",
                    "Prepared decision unavailable",
                }:
                    legacy = True
                if (
                    record.get("record_type") == "Commitment"
                    and record.get("project") == project
                ):
                    if any(
                        d["id"] in request_ids and d["text"] != "Prepared decision"
                        for d in record.get("open_decisions", [])
                    ):
                        legacy = True
        return legacy

    def purge_local_storage(self):
        """Attempt physical cleanup after the caller's redaction transaction commits.

        A blocked checkpoint leaves durable local_storage receipts pending. This
        only covers active SQLite database/WAL bytes, not media remnants or
        independent backups, which require their own destination receipts.
        """
        db = self.store.db
        if db.in_transaction:
            return False
        pending = db.execute(
            "SELECT source,revision FROM memory_redaction WHERE destination='local_storage' AND state='pending'"
        ).fetchall()
        if not pending:
            return True
        if db.execute(
            "SELECT 1 FROM memory_redaction WHERE destination='legacy_history' AND state='pending' LIMIT 1"
        ).fetchone():
            return False
        try:
            if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                return False
            db.execute("VACUUM")
            if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] != 0:
                return False
        except sqlite3.OperationalError:
            return False
        with self.store.transaction():
            for source_id, revision in pending:
                db.execute(
                    "UPDATE memory_redaction SET state='confirmed' WHERE source=? AND revision=? AND destination='local_storage' AND state='pending'",
                    (source_id, revision),
                )
                self.store._history(
                    "memory.local_storage_purged",
                    {"id": source_id, "revision": revision},
                )
        return True

    def confirm_redaction(self, source_id, revision, destination):
        if destination in {"local_storage", "legacy_history"}:
            raise Conflict("local history/storage cannot be confirmed externally")
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT state FROM memory_redaction WHERE source=? AND revision=? AND destination=?",
                (source_id, revision, destination),
            ).fetchone()
            if not row:
                raise KeyError(destination)
            self.store.db.execute(
                "UPDATE memory_redaction SET state='confirmed' WHERE source=? AND revision=? AND destination=?",
                (source_id, revision, destination),
            )
            self.store._history(
                "memory.redaction_confirmed",
                {"id": source_id, "revision": revision, "destination": destination},
            )

    def redaction_receipts(self, source_id, revision):
        return [
            {"destination": r[0], "state": r[1]}
            for r in self.store.db.execute(
                "SELECT destination,state FROM memory_redaction WHERE source=? AND revision=? ORDER BY destination",
                (source_id, revision),
            )
        ]

    def snapshot(self, project, principal, at=None, limit=32, max_bytes=65536):
        if type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError("limit must be 1..128")
        if type(max_bytes) is not int or not 2048 <= max_bytes <= 1048576:
            raise ValueError("max_bytes must be 2048..1048576")
        if at is not None and (
            set(at) != {"known", "effective"}
            or any(v is not None and not isinstance(v, str) for v in at.values())
        ):
            raise ValueError("at requires known and effective timestamps")
        known = (
            _instant(at["known"]) if at and at["known"] else datetime.now(timezone.utc)
        )
        effective = (
            _instant(at["effective"])
            if at and at["effective"]
            else datetime.now(timezone.utc)
        )
        db = self.store.db
        all_sources = {}
        for row in db.execute(
            "SELECT body,redacted,learned_at FROM memory_sources WHERE project=? ORDER BY id,revision",
            (project,),
        ):
            source = strict_loads(row[0])
            if _instant(row[2]) <= known:
                all_sources[source["id"]] = (source, row[1])
        # A historical knowledge cutoff never resurrects a revoked reader.
        current_access = {}
        for row in db.execute(
            "SELECT body,redacted FROM memory_sources WHERE project=? ORDER BY id,revision",
            (project,),
        ):
            current = strict_loads(row[0])
            current_access[current["id"]] = (
                not row[1] and principal in current["readers"]
            )
        visible = {}
        for sid, (source, redacted) in all_sources.items():
            if (
                current_access.get(sid)
                and not redacted
                and principal in source["readers"]
                and (
                    source["effective_at"] is None
                    or _instant(source["effective_at"]) <= effective
                )
            ):
                visible[sid] = source
        valid_statements = {}
        for row in db.execute(
            "SELECT body,learned_at FROM memory_statements WHERE project=? AND redacted=0 ORDER BY id",
            (project,),
        ):
            statement = strict_loads(row[0])
            if (
                _instant(row[1]) > known
                or (
                    statement["effective_from"]
                    and _instant(statement["effective_from"]) > effective
                )
                or (
                    statement["effective_to"]
                    and _instant(statement["effective_to"]) <= effective
                )
            ):
                continue
            if all(
                visible.get(ref["id"], {}).get("revision") == ref["revision"]
                for ref in statement["source_refs"]
            ):
                valid_statements[statement["id"]] = statement
        # Current canonical record revision must still back authoritative statements.
        for sid, statement in list(valid_statements.items()):
            if statement["status"] == "accepted" and not self._accepted_decision(
                statement, require_exact=False
            ):
                del valid_statements[sid]
        for row in db.execute(
            "SELECT body,learned_at FROM memory_relations WHERE project=?", (project,)
        ):
            relation = strict_loads(row[0])
            if relation["kind"] == "disputes" or _instant(row[1]) > known:
                continue
            subject = valid_statements.get(relation["subject"])
            target = valid_statements.get(relation["object"])
            if subject and target and target["status"] != "accepted":
                valid_statements.pop(relation["object"], None)
        changed = True
        while changed:
            before = len(valid_statements)
            valid_statements = {
                k: v
                for k, v in valid_statements.items()
                if all(ref in valid_statements for ref in v["statement_refs"])
            }
            changed = len(valid_statements) != before
        ordered = []
        source_ids = set()
        candidates = sorted(
            valid_statements.values(),
            key=lambda s: (s["recorded_at"], s["id"]),
            reverse=True,
        )
        for candidate in candidates:
            needed = {ref["id"] for ref in candidate["source_refs"]}
            if len(ordered) < limit and len(source_ids | needed) <= limit:
                ordered.append(candidate)
                source_ids |= needed
        for sid in sorted(visible):
            if len(source_ids) >= limit:
                break
            source_ids.add(sid)
        sources = [visible[sid] for sid in sorted(source_ids)]
        freshness = []
        clock = datetime.now(timezone.utc)
        for source in sources:
            retrieval = db.execute(
                "SELECT retrieved_at FROM memory_retrieval WHERE source=? AND revision=?",
                (source["id"], source["revision"]),
            ).fetchone()
            row = db.execute(
                "SELECT max_age_seconds,action FROM memory_freshness WHERE source_class=?",
                (source["source_class"],),
            ).fetchone()
            max_age, action = (row[0], row[1]) if row else (None, "warn")
            age = max(0, int((clock - _instant(source["observed_at"])).total_seconds()))
            freshness.append(
                {
                    "source": source["id"],
                    "revision": source["revision"],
                    "observed_at": source["observed_at"],
                    "retrieved_at": retrieval[0]
                    if retrieval
                    else source["retrieved_at"],
                    "age_seconds": age,
                    "stale": max_age is not None and age > max_age,
                    "action": action,
                }
            )
        permitted_producers = {source["producer"] for source in visible.values()}
        coverage = []
        for r in db.execute(
            "SELECT producer,captured,processed,holes,failures,availability,availability_reason FROM memory_processing WHERE project=? ORDER BY producer",
            (project,),
        ):
            if r[0] not in permitted_producers:
                continue
            failures = strict_loads(r[4])
            for failure in failures:
                if failure["source"] not in visible:
                    failure["source"] = None
            holes = strict_loads(r[3])
            clipped = len(holes) > 64 or len(failures) > 64
            coverage.append(
                {
                    "producer": r[0],
                    "captured": r[1],
                    "processed": r[2],
                    "holes": holes[:64],
                    "failures": failures[:64],
                    "availability": r[5],
                    "reason": r[6],
                    "truncated": clipped,
                }
            )
        availability = (
            "unavailable"
            if any(c["availability"] == "unavailable" for c in coverage)
            else "incomplete"
            if any(
                c["holes"]
                or c["failures"]
                or c["captured"] > c["processed"]
                or c["availability"] == "unknown"
                for c in coverage
            )
            else "available"
            if coverage
            else "unknown"
        )
        result = {
            "project": project,
            "sources": sources,
            "statements": ordered,
            "freshness": freshness,
            "coverage": coverage,
            "availability": availability,
            "dependency_revision": self.dependency_revision(project),
            "truncated": len(candidates) > len(ordered) or len(visible) > len(sources),
        }
        while len(canonical(result).encode()) > max_bytes:
            required = {
                ref["id"]
                for item in result["statements"]
                for ref in item["source_refs"]
            }
            optional = next(
                (
                    i
                    for i in range(len(result["sources"]) - 1, -1, -1)
                    if result["sources"][i]["id"] not in required
                ),
                None,
            )
            if optional is not None:
                removed = result["sources"].pop(optional)
                result["freshness"] = [
                    f for f in result["freshness"] if f["source"] != removed["id"]
                ]
            elif result["statements"]:
                result["statements"].pop()
            elif result["coverage"]:
                result["coverage"].pop()
                result["availability"] = "incomplete"
            elif result["sources"]:
                removed = result["sources"].pop()
                result["freshness"] = [
                    f for f in result["freshness"] if f["source"] != removed["id"]
                ]
            else:
                raise ValueError("snapshot identity exceeds byte budget")
            result["truncated"] = True
        return result
