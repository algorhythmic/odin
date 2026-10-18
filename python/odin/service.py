"""Single-threaded local service using only the synthetic Saga backend.

Internal methods are trusted service code, not model-callable tools. The
socket exposes only recorded operator status/stop commands in this increment.
"""

from datetime import datetime
from pathlib import Path

from .contracts import ROOT, canonical, identifier, strict_loads
from .fake_saga import FakeSaga
from .mirror import SagaMirror
from .policy import route, session_class
from .store import Conflict, Store, digest, event, now


def fixture_record(kind, **fields):
    """Synthetic factory; never import production defaults from these fixtures."""
    result = strict_loads((ROOT / "fixtures/examples.json").read_text())[kind]
    return (
        result | {"id": identifier(), "created_at": now(), "updated_at": now()} | fields
    )


def make_effect(destination, payload, *, operation_id=None, **fields):
    return fixture_record(
        "Effect",
        operation_id=operation_id or identifier(),
        destination=destination,
        payload_digest=digest(payload),
        **fields,
    )


class Service:
    label = "fake-backend evidence"

    def __init__(self, directory):
        self.directory = Path(directory)
        self.store = Store(self.directory)
        try:
            self.backend = FakeSaga(self.directory / "fake-saga.sqlite3")
            self.mirror = SagaMirror(self.directory)
        except BaseException:
            if hasattr(self, "backend"):
                self.backend.close()
            self.store.close()
            raise
        self.store.db.executescript("""
            CREATE TABLE IF NOT EXISTS child_returns
              (operation TEXT PRIMARY KEY, digest TEXT NOT NULL, eligible INTEGER NOT NULL, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS routes(event TEXT PRIMARY KEY, destination TEXT NOT NULL);
        """)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.mirror.close()
        self.backend.close()
        self.store.close()

    def recover(self):
        self.mirror.refresh(self.backend)
        self.store.recover(self.backend, self.handle)

    def command(self, command):
        self.store.contracts.validate("operator-command", command)
        uid = command["operation_id"]
        item = event(
            "operator.command." + command["action"],
            command,
            producer="fixture-cli",
            key=uid,
        )
        item["id"] = uid
        self.store.intake(item)
        self.store.process(self.handle)
        # Reads and reconciliation precede outbound writes, even for direct stop.
        if self.store.dispatch_enabled:
            self.store.dispatch(self.backend)
            self.mirror.refresh(self.backend)
        return self.status()

    def handle(self, store, item):
        """Runs inside the inbox transaction; must not start another transaction."""
        destination = route(item)
        if destination == "direct":
            if item["producer"] != "fixture-cli":
                raise PermissionError("untrusted operator command producer")
            command = item["payload"]
            store.contracts.validate("operator-command", command)
            if item["kind"] != "operator.command." + command["action"]:
                raise Conflict("command kind mismatch")
            if command["action"] == "stop":
                store._stop(command["reason"])
                payload = {"scope": "all"}
                effect = make_effect(
                    "saga:stop", payload, operation_id=command["operation_id"]
                )
                store._enqueue(effect, payload)
        store.db.execute(
            "INSERT OR REPLACE INTO routes VALUES(?,?)", (item["id"], destination)
        )

    def schedule(self, key, due, item):
        self.store.contracts.validate("event", item)
        self.store.contracts.validate("event", item | {"received_at": due})
        with self.store.transaction():
            if self.store.stopped():
                raise Conflict("scheduler stopped")
            old = self.store.db.execute(
                "SELECT due,payload FROM timers WHERE key=?", (key,)
            ).fetchone()
            if old and tuple(old) != (due, canonical(item)):
                raise Conflict("timer identity conflict")
            self.store.db.execute(
                "INSERT OR IGNORE INTO timers VALUES(?,?,?)",
                (key, due, canonical(item)),
            )
            if not old:
                self.store._history(
                    "timer.scheduled", {"key": key, "due": due, "event": item}
                )

    def choose_fixture_class(
        self,
        project,
        subject,
        requirements,
        candidates,
        matrix,
        budget,
        environment,
        config_revision,
        *,
        record=True,
    ):
        chosen, rejected = session_class(requirements, candidates, matrix, budget)
        if record:
            inputs = {
                "event_kind": subject["kind"],
                "assignment_requirements": requirements,
                "environment": {"id": environment["id"], "rev": environment["rev"]},
                "budget_state": canonical({"available_microusd": budget}),
            }
            if chosen is None:
                with self.store.transaction():
                    self.store._history(
                        "session_class.refused",
                        {
                            "rejected": rejected,
                            "inputs": inputs,
                            "config_rev": config_revision,
                        },
                    )
            else:
                self.store.create(
                    fixture_record(
                        "SessionClassDecision",
                        project=project,
                        subject={"kind": "event", "id": subject["id"]},
                        chosen=chosen,
                        rejected=rejected,
                        inputs=inputs,
                        config_rev=config_revision,
                        decided_at=now(),
                    )
                )
        return chosen  # Recording is observational; no outcome record is consulted.

    def tick(self, at=None):
        self.store.process(self.handle)  # Stop always precedes due timers.
        if self.store.stopped():
            return 0
        stamp = datetime.fromisoformat(at or now())
        due = [
            r
            for r in self.store.db.execute("SELECT * FROM timers ORDER BY rowid")
            if datetime.fromisoformat(r["due"]) <= stamp
        ]
        for timer in due:
            # A crash after intake leaves the timer for idempotent replay.
            self.store.intake(strict_loads(timer["payload"]))
            with self.store.transaction():
                self.store.db.execute("DELETE FROM timers WHERE key=?", (timer["key"],))
                self.store._history("timer.fired", {"key": timer["key"]})
        self.store.process(self.handle)
        return len(due)

    def reconcile_runs(self):
        self.mirror.refresh(self.backend)
        with self.store.transaction():
            for assignment in self.store.records("Assignment"):
                if assignment["backend"] != "saga" or not assignment["run"]:
                    continue
                if assignment["state"] in ("completed", "cancelled", "failed"):
                    continue
                run = self.mirror.get(assignment["run"])
                if run["request_id"] != assignment["request_id"]:
                    raise Conflict("run binding mismatch")
                if run["state"] in ("verified", "closed") and run["evidence"]:
                    state = "completed"
                elif run["state"] in ("failed", "cancelled"):
                    state = run["state"]
                elif run["state"] == "started":
                    state = "active"
                else:
                    continue  # Termination is not verification.
                self.store._put(
                    assignment
                    | {
                        "state": state,
                        "rev": assignment["rev"] + 1,
                        "updated_at": now(),
                    },
                    assignment["rev"],
                )

    def close_commitment(self, commitment_id, expected_revision, evidence):
        """Trusted acceptance check: every criterion, including integration, is covered."""
        with self.store.transaction():
            commitment = self.store.get(commitment_id)
            assignments = [
                a
                for a in self.store.records("Assignment")
                if a["commitment"] == commitment_id
            ]
            if not assignments or any(a["state"] != "completed" for a in assignments):
                raise Conflict("work not verified")
            required = {c["id"] for c in commitment["criteria"]}
            if set(evidence) != required or any(not refs for refs in evidence.values()):
                raise Conflict("acceptance evidence incomplete")
            criteria = [
                c | {"met": True, "evidence": evidence[c["id"]]}
                for c in commitment["criteria"]
            ]
            result = commitment | {
                "state": "closed",
                "criteria": criteria,
                "evidence": sorted({ref for refs in evidence.values() for ref in refs}),
                "rev": commitment["rev"] + 1,
                "updated_at": now(),
            }
            self.store._put(result, expected_revision)
            return result

    def record_child_return(self, result, assignment_id, generation):
        from .host import accept_child_result

        self.store.contracts.validate("host-result", result)
        with self.store.transaction():
            assignment = self.store.get(assignment_id)
            commitment = self.store.get(assignment["commitment"])
            old = self.store.db.execute(
                "SELECT digest FROM child_returns WHERE operation=?",
                (result["operation_id"],),
            ).fetchone()
            if old:
                if old[0] != digest(result):
                    raise Conflict("child return identity conflict")
                return False
            eligible = generation == commitment[
                "ownership_generation"
            ] and accept_child_result(result, assignment, generation)
            self.store.db.execute(
                "INSERT INTO child_returns VALUES(?,?,?,?)",
                (
                    result["operation_id"],
                    digest(result),
                    int(eligible),
                    canonical(result),
                ),
            )
            self.store._history(
                "child.returned", {"report": result, "eligible_for_checking": eligible}
            )
            return eligible  # Does not mark the assignment or commitment complete.

    def host_offline(self, host):
        with self.store.transaction():
            for binding in self.store.records("SessionBinding"):
                if binding["host"] == host and binding["state"] == "active":
                    self.store._put(
                        binding
                        | {
                            "state": "host_offline",
                            "rev": binding["rev"] + 1,
                            "updated_at": now(),
                        },
                        binding["rev"],
                    )

    def replace_fixture_session(self, previous_id):
        """Atomic synthetic replacement; old-generation effects stay held."""
        with self.store.transaction():
            old = self.store.get(previous_id)
            if old["record_type"] != "PlanningSession" or old["state"] == "retired":
                raise Conflict("invalid replacement")
            new = fixture_record(
                "PlanningSession",
                project=old["project"],
                state="active",
                ownership_generation=old["ownership_generation"] + 1,
            )
            self.store._put(
                old | {"state": "retired", "rev": old["rev"] + 1, "updated_at": now()},
                old["rev"],
            )
            self.store._put(new, 0)
            commitments = set()
            for commitment in self.store.records("Commitment"):
                if commitment["owner"] != previous_id:
                    continue
                commitments.add(commitment["id"])
                self.store._put(
                    commitment
                    | {
                        "owner": new["id"],
                        "ownership_generation": commitment["ownership_generation"] + 1,
                        "rev": commitment["rev"] + 1,
                        "updated_at": now(),
                    },
                    commitment["rev"],
                )
            assignments = set()
            for assignment in self.store.records("Assignment"):
                if assignment["commitment"] not in commitments:
                    continue
                assignments.add(assignment["id"])
                self.store._put(
                    assignment
                    | {
                        "owner": new["id"],
                        "rev": assignment["rev"] + 1,
                        "updated_at": now(),
                    },
                    assignment["rev"],
                )
            for effect in self.store.effects():
                if effect["assignment"] in assignments and effect["state"] in (
                    "queued",
                    "held",
                ):
                    self.store._effect_state(
                        effect, "held", dispatch_blocked_by="session_replacement"
                    )
            return new

    def reconcile_binding(self, binding_id, observed):
        with self.store.transaction():
            binding = self.store.get(binding_id)
            matches = all(
                binding[k] == observed.get(k)
                for k in ("host", "incarnation", "native_session_id", "environment")
            )
            state = "active" if matches and not self.store.stopped() else "invalidated"
            result = binding | {
                "state": state,
                "rev": binding["rev"] + 1,
                "updated_at": now(),
            }
            self.store._put(result, binding["rev"])
            return state

    def status(self):
        result = {
            "label": self.label,
            "stopped": self.store.stopped(),
            "dispatch_enabled": self.store.dispatch_enabled,
            "records": len(self.store.records()),
            "effects": [
                {
                    k: e[k]
                    for k in ("operation_id", "destination", "state", "reconciliation")
                }
                for e in self.store.effects()
            ],
            "runs": [
                {k: r[k] for k in ("id", "state")}
                for r in self.backend.resources("run")
            ],
        }
        self.store.contracts.validate("service-status", result)
        return result
