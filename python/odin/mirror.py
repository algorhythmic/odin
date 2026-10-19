"""Read-only-to-consumers execution projection fed by an explicit adapter."""

from .contracts import canonical, strict_loads
from .store import Conflict, Store, event


class SagaMirror:
    def __init__(self, directory):
        self.store = Store(directory, "execution_ledger", "saga_adapter")

    def close(self):
        self.store.close()

    def refresh(self, backend):
        if not getattr(backend, "fake_backend", False):
            raise PermissionError("live mirror ingestion is gated")
        db = self.store.db
        cursor = db.execute("SELECT seq FROM cursors WHERE producer='saga'").fetchone()
        sequence = cursor[0] if cursor else 0
        batch = backend.events(sequence)
        with self.store.transaction():
            for item in batch:
                if item["seq"] != sequence + 1:
                    raise Conflict("mirror sequence gap; reconcile at producer")
                db.execute(
                    "INSERT INTO mirror VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET source_seq=excluded.source_seq,body=excluded.body",
                    (item["id"], item["seq"], canonical(item["body"])),
                )
                envelope = event(
                    "mirror.updated",
                    item,
                    namespace="execution_ledger",
                    producer="saga",
                    source_seq=item["seq"],
                    key=f"saga:{item['seq']}",
                )
                self.store.contracts.validate("event", envelope)
                db.execute(
                    "INSERT INTO history(id,body) VALUES(?,?)",
                    (envelope["id"], canonical(envelope)),
                )
                sequence = item["seq"]
            db.execute(
                "INSERT INTO cursors VALUES('saga',?) ON CONFLICT(producer) DO UPDATE SET seq=excluded.seq",
                (sequence,),
            )
        return len(batch)

    def get(self, resource_id):
        row = self.store.db.execute(
            "SELECT body FROM mirror WHERE id=?", (resource_id,)
        ).fetchone()
        if not row:
            raise KeyError(resource_id)
        return strict_loads(row[0])
