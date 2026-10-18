"""Durable, fixture-only coordination across a portfolio and planning sessions.

Actors are identities supplied by trusted local service code. This module is
not a model-callable endpoint and does not authenticate remote principals.
"""

from dataclasses import dataclass
from datetime import datetime

from .contracts import canonical, strict_loads
from .store import Conflict, digest, now


@dataclass(frozen=True)
class Actor:
    role: str
    subject: str
    session: str | None = None
    incarnation: int | None = None


class Coordination:
    def __init__(self, store, config=None):
        store._core()
        self.store = store
        self.config = {"coordinator": "Fable", "planner": "Astra"} | (config or {})
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS coordination_grants
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL,
               revoked_at TEXT);
            CREATE TABLE IF NOT EXISTS coordination_handoffs
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL,
               accepted_at TEXT);
            CREATE TABLE IF NOT EXISTS coordination_reports
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL,
               eligible INTEGER NOT NULL);
        """)

    def _actor(self, actor, role):
        if not isinstance(actor, Actor) or actor.role != role:
            raise PermissionError("trusted actor role required")
        if role == "coordinator" and actor.subject != self.config["coordinator"]:
            raise PermissionError("wrong coordinator")
        if role == "planner" and actor.subject != self.config["planner"]:
            raise PermissionError("wrong planner")

    def _live(self):
        if self.store.stopped():
            raise Conflict("coordination stopped")

    def grant(self, grant, *, actor):
        """Record an operator-issued, immutable scoped authority reference."""
        self._actor(actor, "operator")
        self.store.contracts.validate("coordination-grant", grant)
        if grant["issuer"] != actor.subject or grant["subject"] == actor.subject:
            raise PermissionError("grant issuer/subject mismatch")
        if datetime.fromisoformat(grant["expires_at"]) <= datetime.fromisoformat(
            grant["issued_at"]
        ):
            raise Conflict("grant expires before issuance")
        with self.store.transaction():
            self._live()
            self._project(grant["project"])
            old = self.store.db.execute(
                "SELECT digest FROM coordination_grants WHERE id=?", (grant["id"],)
            ).fetchone()
            if old:
                if old[0] != digest(grant):
                    raise Conflict("grant identity conflict")
                return False
            self.store.db.execute(
                "INSERT INTO coordination_grants VALUES(?,?,?,NULL)",
                (grant["id"], digest(grant), canonical(grant)),
            )
            self.store._history("coordination.grant", {"grant": grant})
            return True

    def revoke(self, grant_id, *, actor):
        self._actor(actor, "operator")
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT body,revoked_at FROM coordination_grants WHERE id=?",
                (grant_id,),
            ).fetchone()
            if not row:
                raise KeyError(grant_id)
            if strict_loads(row[0])["issuer"] != actor.subject:
                raise PermissionError("wrong grant issuer")
            if row[1]:
                return False
            stamp = now()
            self.store.db.execute(
                "UPDATE coordination_grants SET revoked_at=? WHERE id=?",
                (stamp, grant_id),
            )
            self.store._history(
                "coordination.grant_revoked", {"grant_id": grant_id, "at": stamp}
            )
            return True

    def _authorized(self, grant_id, action, resource, actor, *, project=None):
        self._live()
        row = self.store.db.execute(
            "SELECT body,revoked_at FROM coordination_grants WHERE id=?", (grant_id,)
        ).fetchone()
        if not row or row[1]:
            raise PermissionError("missing or revoked grant")
        grant = strict_loads(row[0])
        if (
            (project is not None and grant["project"] != project)
            or resource not in grant["resources"]
            or grant["subject"] != actor.subject
            or grant["subject_role"] != actor.role
            or action not in grant["actions"]
            or datetime.fromisoformat(grant["issued_at"])
            > datetime.fromisoformat(now())
            or datetime.fromisoformat(grant["expires_at"])
            <= datetime.fromisoformat(now())
        ):
            raise PermissionError("grant scope or expiry mismatch")
        return grant

    def authorize_action(self, grant_id, action, resource, *, actor):
        if not isinstance(actor, Actor):
            raise PermissionError("trusted actor required")
        with self.store.transaction():
            self._authorized(grant_id, action, resource, actor)
            return True

    def _project(self, project_id):
        record = self.store.get(project_id)
        if record["record_type"] != "Project":
            raise Conflict("project reference mismatch")
        return record

    def _packet_current(self, packet):
        project = self._project(packet["project"])
        commitment = self.store.get(packet["commitment"])
        session = self.store.get(packet["to_session"])
        if (
            project["rev"] != packet["project_rev"]
            or commitment["record_type"] != "Commitment"
            or commitment["project"] != project["id"]
            or commitment["rev"] != packet["commitment_rev"]
            or commitment["ownership_generation"] != packet["ownership_generation"]
            or commitment["state"] in ("satisfied", "closed", "abandoned")
            or commitment["owner"] != session["id"]
            or session["record_type"] != "PlanningSession"
            or session["project"] != project["id"]
            or session["incarnation"] != packet["to_incarnation"]
            or session["state"] not in ("active", "idle")
            or project["interface_decision_owner"] != session["id"]
        ):
            raise Conflict("stale or unowned handoff")
        if packet["assignment"] is not None:
            assignment = self.store.get(packet["assignment"])
            if (
                assignment["record_type"] != "Assignment"
                or assignment["commitment"] != commitment["id"]
                or assignment["rev"] != packet["assignment_rev"]
                or assignment["owner"] != session["id"]
                or assignment["state"] in ("completed", "failed", "cancelled")
                or assignment["backend"] != "saga"
            ):
                raise Conflict("stale or non-Saga assignment")
        return commitment

    def handoff(self, packet, *, actor):
        self._actor(actor, "coordinator")
        self.store.contracts.validate("coordination-handoff", packet)
        if packet["from_subject"] != actor.subject:
            raise PermissionError("handoff sender mismatch")
        with self.store.transaction():
            self._live()
            old = self.store.db.execute(
                "SELECT digest FROM coordination_handoffs WHERE id=?",
                (packet["operation_id"],),
            ).fetchone()
            if old:
                if old[0] != digest(packet):
                    raise Conflict("handoff identity conflict")
                return False
            self._authorized(
                packet["grant_id"],
                "handoff",
                packet["project"],
                actor,
                project=packet["project"],
            )
            commitment = self._packet_current(packet)
            if (
                datetime.fromisoformat(packet["deadline"])
                <= datetime.fromisoformat(now())
                or packet["requirements"]["objective"] != commitment["objective"]
                or packet["requirements"]["criteria"]
                != [{"id": c["id"], "text": c["text"]} for c in commitment["criteria"]]
            ):
                raise Conflict("expired or altered requirements")
            self.store.db.execute(
                "INSERT INTO coordination_handoffs VALUES(?,?,?,NULL)",
                (packet["operation_id"], digest(packet), canonical(packet)),
            )
            self.store._history("coordination.handoff", {"packet": packet})
            return True

    def accept_handoff(self, operation_id, *, actor):
        self._actor(actor, "planner")
        with self.store.transaction():
            self._live()
            row = self.store.db.execute(
                "SELECT body,accepted_at FROM coordination_handoffs WHERE id=?",
                (operation_id,),
            ).fetchone()
            if not row:
                raise KeyError(operation_id)
            packet = strict_loads(row[0])
            self._recipient(packet, actor)
            self._authorized(
                packet["grant_id"],
                "handoff",
                packet["project"],
                Actor("coordinator", packet["from_subject"]),
                project=packet["project"],
            )
            self._packet_current(packet)
            if datetime.fromisoformat(packet["deadline"]) <= datetime.fromisoformat(
                now()
            ):
                raise Conflict("handoff expired")
            if row[1]:
                return False
            stamp = now()
            self.store.db.execute(
                "UPDATE coordination_handoffs SET accepted_at=? WHERE id=?",
                (stamp, operation_id),
            )
            self.store._history(
                "coordination.handoff_accepted",
                {"operation_id": operation_id, "at": stamp},
            )
            return True

    def _recipient(self, packet, actor):
        if (
            packet["to_subject"] != actor.subject
            or packet["to_session"] != actor.session
            or packet["to_incarnation"] != actor.incarnation
        ):
            raise PermissionError("wrong planning session incarnation")

    def report(self, result, *, actor):
        """Retain a return; True means eligible for checking, never completion."""
        self._actor(actor, "planner")
        self.store.contracts.validate("coordination-result", result)
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT digest,eligible FROM coordination_reports WHERE id=?",
                (result["report_id"],),
            ).fetchone()
            if row:
                if row[0] != digest(result):
                    raise Conflict("result identity conflict")
                return False  # A replay can never advance acceptance twice.
            dispatch = self.store.db.execute(
                "SELECT body,accepted_at FROM coordination_handoffs WHERE id=?",
                (result["operation_id"],),
            ).fetchone()
            if not dispatch or not dispatch[1]:
                raise Conflict("unaccepted dispatch")
            packet = strict_loads(dispatch[0])
            self._recipient(packet, actor)
            try:
                self._authorized(
                    packet["grant_id"],
                    "handoff",
                    packet["project"],
                    Actor("coordinator", packet["from_subject"]),
                    project=packet["project"],
                )
                self._packet_current(packet)
                current = True
            except (Conflict, PermissionError, KeyError):
                current = False
            complete = result["status"] == "complete"
            criteria = {c["id"] for c in packet["requirements"]["criteria"]}
            covered = [e["criterion"] for e in result["evidence"] if e["refs"]]
            eligible = bool(
                current
                and complete
                and set(covered) == criteria
                and len(covered) == len(criteria)
                and result["session"] == packet["to_session"]
                and result["incarnation"] == packet["to_incarnation"]
                and result["project"] == packet["project"]
                and result["commitment"] == packet["commitment"]
                and result["assignment"] == packet["assignment"]
                and result["repository_revision"]
                and datetime.fromisoformat(now())
                <= datetime.fromisoformat(packet["deadline"])
            )
            self.store.db.execute(
                "INSERT INTO coordination_reports VALUES(?,?,?,?)",
                (result["report_id"], digest(result), canonical(result), int(eligible)),
            )
            self.store._history(
                "coordination.result",
                {"result": result, "eligible_for_checking": eligible},
            )
            return eligible

    def portfolio(self, projects, *, actor, grant_ids):
        self._actor(actor, "coordinator")
        result = []
        for project_id in projects:
            self.authorize_action(
                grant_ids[project_id], "portfolio", project_id, actor=actor
            )
            project = self._project(project_id)
            commitments = [
                r
                for r in self.store.records("Commitment")
                if r["project"] == project_id
            ]
            assignments = [
                r
                for r in self.store.records("Assignment")
                if r["commitment"] in {c["id"] for c in commitments}
            ]
            handoffs = [
                strict_loads(r[0])
                for r in self.store.db.execute("SELECT body FROM coordination_handoffs")
            ]
            result.append(
                {
                    "project": project_id,
                    "project_rev": project["rev"],
                    "planning_owner": project["interface_decision_owner"],
                    "commitments": [
                        {
                            "id": c["id"],
                            "rev": c["rev"],
                            "state": c["state"],
                            "owner": c["owner"],
                            "ownership_generation": c["ownership_generation"],
                            "objective": c["objective"],
                            "next_trigger": c["next_trigger"],
                            "open_decisions": c["open_decisions"],
                        }
                        for c in commitments
                    ],
                    "assignments": [
                        {
                            "id": a["id"],
                            "rev": a["rev"],
                            "state": a["state"],
                            "backend": a["backend"],
                        }
                        for a in assignments
                    ],
                    "handoffs": [
                        h["operation_id"]
                        for h in handoffs
                        if h["project"] == project_id
                    ],
                }
            )
        self.store.contracts.validate("coordination-portfolio", result)
        return result
