"""Persistent fixture session host. It deliberately executes no model or tool."""

import sqlite3

from .contracts import Contracts, canonical, strict_loads
from .store import Conflict, digest


class FixtureHost:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY,digest TEXT NOT NULL,result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,generation INTEGER NOT NULL,state TEXT NOT NULL);
        """)
        self.online = True
        self.contracts = Contracts()

    def close(self):
        self.db.close()

    def command(self, command):
        self.contracts.validate("host-command", command)
        if not self.online:
            raise ConnectionError("host_offline: outcome unconfirmed")
        fingerprint = digest(command)
        with self.db:
            old = self.db.execute(
                "SELECT * FROM commands WHERE id=?", (command["operation_id"],)
            ).fetchone()
            if old:
                if old["digest"] != fingerprint:
                    raise Conflict("operation_conflict")
                return strict_loads(old["result"])
            session = self.db.execute(
                "SELECT * FROM sessions WHERE id=?", (command["session"],)
            ).fetchone()
            action = command["action"]
            if action == "start" and session:
                raise Conflict("session already exists")
            if action != "start" and (
                not session or session["generation"] != command["generation"]
            ):
                raise Conflict("stale_owner")
            if session and session["state"] == "retired":
                raise Conflict("retired session")
            state = {
                "start": "active",
                "resume": "active",
                "interrupt": "idle",
                "retire": "retired",
            }[action]
            self.db.execute(
                "INSERT OR REPLACE INTO sessions VALUES(?,?,?)",
                (command["session"], command["generation"], state),
            )
            result = {
                "session": command["session"],
                "state": state,
                "generation": command["generation"],
                "assignment": command["assignment"],
                "assignment_revision": command["assignment_revision"],
                "operation_id": command["operation_id"],
                "result": command["fixture_result"],
                "label": "fixture-only; no model or tool execution",
            }
            self.db.execute(
                "INSERT INTO commands VALUES(?,?,?)",
                (command["operation_id"], fingerprint, canonical(result)),
            )
            return result

    def lookup(self, operation_id):
        if not self.online:
            raise ConnectionError("host_offline")
        row = self.db.execute(
            "SELECT result FROM commands WHERE id=?", (operation_id,)
        ).fetchone()
        return strict_loads(row[0]) if row else None


def accept_child_result(result, assignment, ownership_generation):
    if (
        result.get("generation") != ownership_generation
        or result.get("session") != assignment.get("owner")
        or result.get("assignment") != assignment["id"]
        or result.get("assignment_revision") != assignment["rev"]
    ):
        return False
    report = result.get("result")
    # Eligibility for independent checking only. Never closes the assignment.
    return bool(
        report and report.get("status") == "complete" and report.get("evidence")
    )
