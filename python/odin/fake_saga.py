"""Durable test double. Shapes here are fixture protocol, never Saga wire API.

No containers, subprocesses, credentials, broker or network are used. Passing
this backend's checks establishes none of Saga's isolation/authority guarantees.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .contracts import Contracts, canonical, identifier, strict_loads
from .store import Conflict, digest


class FakeSaga:
    fake_backend = True
    evidence_label = "fake-backend evidence"

    def __init__(self, path: Path):
        self.contracts = Contracts()
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS operations
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT);
            CREATE TABLE IF NOT EXISTS resources
              (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events
              (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL);
        """)
        self.lose_next_receipt = False

    def close(self):
        self.db.close()

    def get(self, resource):
        row = self.db.execute(
            "SELECT body FROM resources WHERE id=?", (resource,)
        ).fetchone()
        if not row:
            raise KeyError(resource)
        return strict_loads(row[0])

    def resources(self, kind):
        return [
            strict_loads(r[0])
            for r in self.db.execute("SELECT body FROM resources WHERE kind=?", (kind,))
        ]

    def _save(self, resource, kind, data):
        self.db.execute(
            "INSERT OR REPLACE INTO resources VALUES(?,?,?)",
            (resource, kind, canonical(data)),
        )
        self.db.execute(
            "INSERT INTO events(id,kind,body) VALUES(?,?,?)",
            (resource, kind, canonical(data)),
        )

    def send(self, operation_id, destination, payload):
        if not destination.startswith("saga:"):
            raise ValueError("fixture destination must name saga")
        operation = destination.removeprefix("saga:")
        self.contracts.validate(
            "fake-command", {"operation": operation, "data": payload}
        )
        fingerprint = digest({"destination": destination, "payload": payload})
        with self.db:
            prior = self.db.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if prior:
                if prior["digest"] != fingerprint:
                    raise Conflict("operation_conflict")
                return prior["receipt"]
            receipt = self._apply(operation, payload, operation_id)
            self.db.execute(
                "INSERT INTO operations VALUES(?,?,?,?)",
                (operation_id, fingerprint, "completed", receipt),
            )
        if self.lose_next_receipt:
            self.lose_next_receipt = False
            raise TimeoutError("injected: receipt lost after fake commit")
        return receipt

    def _apply(self, operation, payload, operation_id):
        uid = payload.get("id") or identifier()
        if operation == "run.submit":
            if payload["request_id"] != operation_id:
                raise Conflict("submission operation must equal request id")
            approval = self.get(payload["approval"])
            verdict = self.get(payload["review"])
            delegation = self.get(payload["delegation"])
            if delegation.get("revoked"):
                raise Conflict("fake delegation revoked")
            if payload["delegation_version"] != delegation["version"]:
                raise Conflict("fake stale delegation")
            active = [
                r
                for r in self.resources("run")
                if r["delegation"] == delegation["id"]
                and r["state"] not in ("verified", "closed", "cancelled", "failed")
            ]
            if len(active) >= delegation["concurrency"]:
                raise Conflict("fake concurrency cap")
            for record in (approval, verdict):
                if (
                    record.get("request_id") != payload["request_id"]
                    or record.get("digest") != payload["digest"]
                ):
                    raise Conflict("fake binding mismatch")
            if verdict.get("result") not in ("APPROVE", "APPROVE_UNCHANGED"):
                raise Conflict("fake review refused")
            if approval.get("operator") != "synthetic-operator":
                raise Conflict("fake operator missing")
            run = payload | {
                "id": uid,
                "state": "accepted",
                "evidence": [],
                "label": self.evidence_label,
            }
            if self.db.execute("SELECT 1 FROM resources WHERE id=?", (uid,)).fetchone():
                raise Conflict("resource identity conflict")
            self._save(uid, "run", run)
        elif operation == "run.cancel":
            run = self.get(payload["run"])
            self._save(run["id"], "run", run | {"state": "cancelled"})
            uid = run["id"]
        elif operation == "stop":
            for run in self.resources("run"):
                if run["state"] not in ("verified", "failed", "cancelled", "closed"):
                    self._save(run["id"], "run", run | {"state": "cancelled"})
            for delegation in self.resources("delegation"):
                self._save(
                    delegation["id"], "delegation", delegation | {"revoked": True}
                )
        elif operation == "request.answer":
            request = self.get(payload["request"])
            if request.get("answer") is not None:
                raise Conflict("request_already_answered")
            self._save(
                request["id"],
                "request",
                request | {"answer": payload["answer"], "state": "answered"},
            )
            uid = request["id"]
        elif operation == "guidance":
            raise Conflict("guidance held: X-7 and producer wire gaps unresolved")
        else:
            kind = operation.split(".")[0]
            old = self.db.execute(
                "SELECT body FROM resources WHERE id=?", (uid,)
            ).fetchone()
            if old and old[0] != canonical(payload | {"id": uid}):
                raise Conflict("resource identity conflict")
            self._save(uid, kind, payload | {"id": uid})
        return uid

    def inject_run_state(self, run_id, state, evidence=()):
        if state not in (
            "started",
            "terminated",
            "verified",
            "failed",
            "cancelled",
            "limit_paused",
            "closed",
        ):
            raise ValueError(state)
        if state == "verified" and not evidence:
            raise Conflict("fake evidence required")
        with self.db:
            run = self.get(run_id)
            allowed = {
                "accepted": {"started", "cancelled", "failed"},
                "started": {"terminated", "failed", "cancelled", "limit_paused"},
                "terminated": {"verified", "failed", "cancelled"},
                "limit_paused": {"started", "cancelled"},
                "verified": {"closed"},
                "closed": set(),
                "failed": set(),
                "cancelled": set(),
            }
            if state not in allowed.get(run["state"], set()):
                raise Conflict("fake invalid run transition")
            if state == "verified" and len(evidence) < len(run["criteria"]):
                raise Conflict("fake evidence missing criteria")
            self._save(
                run_id,
                "run",
                run | {"state": state, "evidence": list(evidence) or run["evidence"]},
            )

    def inject_request(self, run_id, question):
        uid = identifier()
        with self.db:
            self._save(
                uid,
                "request",
                {
                    "id": uid,
                    "run": run_id,
                    "question": question,
                    "answer": None,
                    "state": "open",
                },
            )
        return uid

    def consume_answer(self, request_id):
        with self.db:
            request = self.get(request_id)
            if request["answer"] is None:
                raise Conflict("no answer")
            self._save(request_id, "request", request | {"state": "consumed"})

    def lookup(self, operation_id):
        row = self.db.execute(
            "SELECT state,receipt FROM operations WHERE id=?", (operation_id,)
        ).fetchone()
        return dict(row) if row else {"state": "absent"}

    def events(self, after=0):
        return [
            {
                "seq": r["seq"],
                "id": r["id"],
                "kind": r["kind"],
                "body": strict_loads(r["body"]),
            }
            for r in self.db.execute(
                "SELECT * FROM events WHERE seq>? ORDER BY seq", (after,)
            )
        ]
