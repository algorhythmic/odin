"""Synthetic capture batches with a durable local spool and atomic replay."""

import sqlite3

from .contracts import Contracts, canonical, strict_loads
from .store import Conflict, Store, digest


class CaptureSpool:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS batches(checkpoint TEXT PRIMARY KEY,body TEXT NOT NULL)"
        )

    def close(self):
        self.db.close()

    def append(self, batch):
        Contracts().validate("capture-batch", batch)
        body = canonical(batch)
        with self.db:
            prior = self.db.execute(
                "SELECT body FROM batches WHERE checkpoint=?", (batch["checkpoint"],)
            ).fetchone()
            if prior and prior[0] != body:
                raise Conflict("capture checkpoint conflict")
            self.db.execute(
                "INSERT OR IGNORE INTO batches VALUES(?,?)", (batch["checkpoint"], body)
            )

    def flush(self, archive):
        for checkpoint, body in self.db.execute(
            "SELECT checkpoint,body FROM batches ORDER BY rowid"
        ).fetchall():
            archive.append(strict_loads(body))
            with self.db:
                self.db.execute("DELETE FROM batches WHERE checkpoint=?", (checkpoint,))


class Archive:
    def __init__(self, directory):
        self.store = Store(directory, "transcript_archive", "capture")
        self.store.db.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints(id TEXT PRIMARY KEY,digest TEXT NOT NULL)"
        )

    def close(self):
        self.store.close()

    def append(self, batch):
        self.store.contracts.validate("capture-batch", batch)
        db = self.store.db
        with self.store.transaction():
            prior = db.execute(
                "SELECT digest FROM checkpoints WHERE id=?", (batch["checkpoint"],)
            ).fetchone()
            fingerprint = digest(batch)
            if prior:
                if prior[0] != fingerprint:
                    raise Conflict("capture checkpoint conflict")
                return 0
            new = 0
            for record in batch["records"]:
                old = db.execute(
                    "SELECT body FROM capture WHERE key=? AND revision=?",
                    (record["key"], record["revision"]),
                ).fetchone()
                if old and old[0] != canonical(record):
                    raise Conflict("capture revision conflict")
                if not old:
                    db.execute(
                        "INSERT INTO capture VALUES(?,?,?)",
                        (record["key"], record["revision"], canonical(record)),
                    )
                    new += 1
            db.execute(
                "INSERT INTO checkpoints VALUES(?,?)",
                (batch["checkpoint"], fingerprint),
            )
            self.store._history("capture.batch", batch)
        return new
