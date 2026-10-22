"""Fixture-only, durable, read-only two-position consultation.

No model transport is provided here. A caller delivers independent outcomes;
neither a branch nor the synthesis has routing, approval, or review authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .contracts import canonical, strict_loads
from .store import Conflict, digest


class Chirality:
    def __init__(self, store, budget):
        store._core()
        if budget.store is not store:
            raise ValueError("budget must use the same Store")
        self.store, self.budget = store, budget
        store.db.execute(
            "CREATE TABLE IF NOT EXISTS chirality (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )

    def status(self, consultation_id):
        row = self.store.db.execute(
            "SELECT body FROM chirality WHERE id=?", (consultation_id,)
        ).fetchone()
        if row is None:
            raise KeyError(consultation_id)
        return strict_loads(row[0])

    def _save(self, state):
        self.store.db.execute(
            "INSERT INTO chirality VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
            (state["id"], canonical(state)),
        )
        self.store._history(
            "chirality.changed",
            {"id": state["id"], "state": state["state"], "round": state["round"]},
        )

    @staticmethod
    def _operation(consultation_id, round_number, role):
        return f"chirality:{consultation_id}:{round_number}:{role}"

    @staticmethod
    def _expired(config):
        return datetime.now(timezone.utc) >= datetime.fromisoformat(
            config["deadline_at"].replace("Z", "+00:00")
        )

    def _reserve_round(self, state, round_number):
        """Admit all three Budget reservations together inside caller's transaction."""
        db = self.store.db
        config = state["config"]
        budget_id = state["budget_id"]
        row = db.execute("SELECT * FROM budgets WHERE id=?", (budget_id,)).fetchone()
        if row is None:
            raise KeyError(budget_id)
        slots = [
            (branch["role"], branch["max_microusd"]) for branch in config["branches"]
        ]
        slots.append(("synthesis", config["synthesis_max_microusd"]))
        active = db.execute(
            "SELECT count(*),coalesce(sum(amount),0) FROM reservations WHERE budget=? AND state IN ('reserved','unknown')",
            (budget_id,),
        ).fetchone()
        if (
            self.store.stopped()
            or row["stopped"]
            or config["depth"] > row["depth"]
            or active[0] + len(slots) > row["concurrency"]
            or row["spent"] + active[1] + sum(amount for _, amount in slots)
            > row["cap"]
        ):
            raise Conflict("chirality budget admission refused")
        for role, amount in slots:
            operation = self._operation(state["id"], round_number, role)
            if db.execute(
                "SELECT 1 FROM reservations WHERE id=?", (operation,)
            ).fetchone():
                raise Conflict("chirality reservation identity conflict")
            db.execute(
                "INSERT INTO reservations VALUES(?,?,?,'reserved',NULL)",
                (operation, budget_id, amount),
            )
            self.store._history(
                "budget.reserved", {"operation": operation, "amount": amount}
            )

    def _settle(self, operation, actual):
        """Budget.settle semantics within the consultation's atomic transaction."""
        row = self.store.db.execute(
            "SELECT * FROM reservations WHERE id=?", (operation,)
        ).fetchone()
        if row is None:
            raise KeyError(operation)
        if row["state"] == "settled":
            if row["actual"] != actual:
                raise Conflict("settlement conflict")
            return
        if actual is None:
            self.store.db.execute(
                "UPDATE reservations SET state='unknown' WHERE id=?", (operation,)
            )
        else:
            self.store.db.execute(
                "UPDATE reservations SET state='settled',actual=? WHERE id=?",
                (actual, operation),
            )
            self.store.db.execute(
                "UPDATE budgets SET spent=spent+?,stopped=max(stopped,?) WHERE id=?",
                (actual, int(actual > row["amount"]), row["budget"]),
            )
        self.store._history(
            "budget.settled", {"operation": operation, "actual": actual}
        )

    @staticmethod
    def _context_matches(packet, context_current):
        if not callable(context_current):
            raise ValueError("trusted context_current callback required")
        return context_current(deepcopy(packet["source"])) == packet["source"]

    def start(self, consultation_id, config, packet, budget_id, *, context_current):
        self.store.contracts.validate("chirality-config", config)
        self.store.contracts.validate("chirality-packet", packet)
        if not config["enabled"]:
            raise Conflict("chirality disabled")
        if self._expired(config):
            raise Conflict("chirality deadline expired")
        if {branch["role"] for branch in config["branches"]} != {"fable", "astra"}:
            raise ValueError("exactly one branch per role required")
        if packet["revision"] != 1 or packet["target"] is not None:
            raise ValueError("initial packet must have revision 1 and no target")
        if not self._context_matches(packet, context_current):
            raise Conflict("stale source context")
        if (
            not isinstance(consultation_id, str)
            or not consultation_id
            or not isinstance(budget_id, str)
            or not budget_id
        ):
            raise ValueError("invalid identity")
        state = {
            "schema_version": 1,
            "id": consultation_id,
            "budget_id": budget_id,
            "config": deepcopy(config),
            "round": 1,
            "state": "collecting",
            "packets": [{"packet": deepcopy(packet), "digest": digest(packet)}],
            "responses": [],
            "held_responses": [],
            "late_responses": [],
            "syntheses": [],
            "authority": "advice_only",
        }
        with self.store.transaction():
            prior = self.store.db.execute(
                "SELECT body FROM chirality WHERE id=?", (consultation_id,)
            ).fetchone()
            if prior:
                old = strict_loads(prior[0])
                if (
                    old["config"] != config
                    or old["packets"][0]["packet"] != packet
                    or old["budget_id"] != budget_id
                ):
                    raise Conflict("consultation identity conflict")
                return old
            for round_number in range(1, config["max_rounds"] + 1):
                self._reserve_round(state, round_number)
            self._save(state)
        return state

    def respond(self, consultation_id, response, *, context_current):
        self.store.contracts.validate("chirality-response", response)
        with self.store.transaction():
            state = self.status(consultation_id)
            role = response["role"]
            prior = next(
                (
                    r
                    for r in state["responses"]
                    if r["round"] == response["round"] and r["role"] == role
                ),
                None,
            )
            held = next(
                (
                    h["response"]
                    for h in state["held_responses"]
                    if h["response"]["round"] == response["round"]
                    and h["response"]["role"] == role
                ),
                None,
            )
            prior = prior or held
            if prior:
                if prior != response:
                    raise Conflict("response identity conflict")
                return state
            packet = state["packets"][state["round"] - 1]
            branch = next(b for b in state["config"]["branches"] if b["role"] == role)
            if (
                state["state"] != "collecting"
                or response["consultation_id"] != consultation_id
                or response["invocation_id"]
                != self._operation(consultation_id, response["round"], role)
                or response["round"] != state["round"]
                or response["packet_revision"] != packet["packet"]["revision"]
                or response["packet_digest"] != packet["digest"]
                or any(
                    response[key] != branch[branch_key]
                    for key, branch_key in (
                        ("requested_provider", "provider"),
                        ("requested_harness", "harness"),
                        ("requested_harness_version", "harness_version"),
                        ("requested_model", "requested_model"),
                        ("requested_effort", "effort"),
                        ("requested_config_revision", "config_revision"),
                    )
                )
            ):
                raise Conflict("stale or mismatched response")
            self._check_bounds(response, state["config"]["limits"])
            if response["status"] == "complete" and (
                not response["resolved_model"] or not response["recommendation"]
            ):
                raise ValueError("complete response needs model and recommendation")
            if response["resolved_model"] not in (None, branch["requested_model"]):
                raise Conflict("unapproved resolved model")
            if (
                response["status"] == "complete"
                and response["resolved_model"] != branch["requested_model"]
            ):
                raise Conflict("unverified resolved model")
            resolved = ("provider", "harness", "harness_version", "effort")
            if response["status"] == "complete" and any(
                response["resolved_" + key] != branch[key] for key in resolved
            ):
                raise Conflict("unapproved resolved execution path")
            if response["status"] != "complete" and any(
                response["resolved_" + key] not in (None, branch[key])
                for key in resolved
            ):
                raise Conflict("unapproved resolved execution path")
            self._settle(
                self._operation(consultation_id, state["round"], role),
                response["actual_microusd"],
            )
            if self._context_matches(packet["packet"], context_current):
                state["responses"].append(deepcopy(response))
            else:
                state["held_responses"].append(
                    {"reason": "stale_source_context", "response": deepcopy(response)}
                )
            self._save(state)
            return state

    @staticmethod
    def _check_bounds(response, limits):
        for field in ("recommendation",):
            if len(response[field]) > limits[field]:
                raise ValueError(f"{field} exceeds configured bound")
        for field in ("evidence", "assumptions", "objections"):
            if len(response[field]) > limits["items"] or any(
                len(item) > limits[field] for item in response[field]
            ):
                raise ValueError(f"{field} exceeds configured bound")

    def close_round(
        self, consultation_id, synthesis_actual_microusd=0, *, context_current
    ):
        if type(synthesis_actual_microusd) is not int or synthesis_actual_microusd < 0:
            raise ValueError("invalid synthesis cost")
        with self.store.transaction():
            state = self.status(consultation_id)
            if state["state"] != "collecting":
                if (
                    state["syntheses"]
                    and state["syntheses"][-1]["round"] == state["round"]
                    and state["syntheses"][-1]["actual_microusd"]
                    == synthesis_actual_microusd
                ):
                    return state
                raise Conflict("round already closed")
            round_number = state["round"]
            outcomes = {
                r["role"]: r for r in state["responses"] if r["round"] == round_number
            }
            held_roles = {
                h["response"]["role"]
                for h in state["held_responses"]
                if h["response"]["round"] == round_number
            }
            closure_reasons = []
            if self.store.stopped():
                closure_reasons.append("parent_stopped")
            if not self._context_matches(
                state["packets"][-1]["packet"], context_current
            ):
                closure_reasons.append("stale_source_context")
            if self._expired(state["config"]):
                closure_reasons.append("deadline_expired")
            if closure_reasons:
                state["state"] = "escalated"
            for branch in state["config"]["branches"]:
                role = branch["role"]
                if role not in outcomes:
                    missing = {
                        "schema_version": 1,
                        "round": round_number,
                        "role": role,
                        "requested_model": branch["requested_model"],
                        "resolved_model": None,
                        "packet_revision": state["packets"][-1]["packet"]["revision"],
                        "packet_digest": state["packets"][-1]["digest"],
                        "status": "unknown",
                        "consultation_id": consultation_id,
                        "invocation_id": self._operation(
                            consultation_id, round_number, role
                        ),
                        "requested_provider": branch["provider"],
                        "requested_harness": branch["harness"],
                        "requested_harness_version": branch["harness_version"],
                        "requested_effort": branch["effort"],
                        "requested_config_revision": branch["config_revision"],
                        "resolved_provider": None,
                        "resolved_harness": None,
                        "resolved_harness_version": None,
                        "resolved_effort": None,
                        "recommendation": "",
                        "evidence": [],
                        "assumptions": [],
                        "objections": [],
                        "actual_microusd": None,
                    }
                    outcomes[role] = missing
                    state["responses"].append(missing)
                    if role not in held_roles:
                        self._settle(
                            self._operation(consultation_id, round_number, role), None
                        )
            # Synthesis is deterministic; this reservation accounts for any caller-provided
            # fixture synthesis work without letting that work overwrite branch provenance.
            self._settle(
                self._operation(consultation_id, round_number, "synthesis"),
                synthesis_actual_microusd,
            )
            positions = [deepcopy(outcomes[role]) for role in ("fable", "astra")]
            complete = all(p["status"] == "complete" for p in positions)
            if not complete:
                closure_reasons.append("missing_or_incomplete")
            unresolved = [
                {"role": p["role"], "objection": objection}
                for p in positions
                for objection in p["objections"]
            ]
            agreement = (
                complete
                and positions[0]["recommendation"] == positions[1]["recommendation"]
                and not unresolved
                and not closure_reasons
            )
            if complete and not agreement and not closure_reasons:
                closure_reasons.append("dissent")
            synthesis = {
                "schema_version": 1,
                "round": round_number,
                "packet_digest": state["packets"][-1]["digest"],
                "positions": positions,
                "agreement": agreement,
                "dissent": []
                if agreement
                else [
                    {
                        "role": p["role"],
                        "status": p["status"],
                        "recommendation": p["recommendation"],
                        "objections": p["objections"],
                    }
                    for p in positions
                ],
                "unresolved": unresolved,
                "closure_reasons": closure_reasons,
                "actual_microusd": synthesis_actual_microusd,
                "authority": "advice_only",
            }
            self.store.contracts.validate("chirality-synthesis", synthesis)
            state["syntheses"].append(synthesis)
            if state["state"] != "escalated":
                state["state"] = (
                    "advice_ready"
                    if agreement
                    else (
                        "followup_available"
                        if round_number < state["config"]["max_rounds"] and complete
                        else "escalated"
                    )
                )
            if state["state"] in ("advice_ready", "escalated"):
                for unused in range(
                    round_number + 1, state["config"]["max_rounds"] + 1
                ):
                    for role in ("fable", "astra", "synthesis"):
                        self._settle(self._operation(consultation_id, unused, role), 0)
            self._save(state)
            return state

    def followup(self, consultation_id, packet, *, context_current):
        self.store.contracts.validate("chirality-packet", packet)
        with self.store.transaction():
            state = self.status(consultation_id)
            if state["round"] == 2 and state["packets"][1]["packet"] == packet:
                return state
            if (
                state["state"] != "followup_available"
                or self.store.stopped()
                or self._expired(state["config"])
            ):
                raise Conflict("followup unavailable")
            prior = state["packets"][-1]
            if (
                packet["revision"] != prior["packet"]["revision"] + 1
                or not packet["target"]
                or digest(packet) == prior["digest"]
                or packet["source"] != prior["packet"]["source"]
            ):
                raise ValueError("followup needs a revised, targeted packet")
            if not self._context_matches(packet, context_current):
                raise Conflict("stale source context")
            state["round"] += 1
            state["state"] = "collecting"
            state["packets"].append(
                {"packet": deepcopy(packet), "digest": digest(packet)}
            )
            self._save(state)
            return state

    def terminate_between_rounds(self, consultation_id):
        """Discard an unstarted follow-up; already observed costs remain intact."""
        with self.store.transaction():
            state = self.status(consultation_id)
            if state["state"] == "escalated":
                return state
            if state["state"] != "followup_available":
                raise Conflict("no unstarted followup")
            next_round = state["round"] + 1
            for role in ("fable", "astra", "synthesis"):
                self._settle(self._operation(consultation_id, next_round, role), 0)
            state["state"] = "escalated"
            self._save(state)
            return state

    def record_late(self, consultation_id, response, *, context_current):
        """Reconcile an unknown branch cost without reopening a closed conclusion."""
        self.store.contracts.validate("chirality-response", response)
        with self.store.transaction():
            state = self.status(consultation_id)
            prior = next(
                (
                    r
                    for r in state["late_responses"]
                    if r["round"] == response["round"] and r["role"] == response["role"]
                ),
                None,
            )
            if prior:
                if prior != response:
                    raise Conflict("late response identity conflict")
                return state
            if state["state"] not in (
                "escalated",
                "advice_ready",
                "followup_available",
            ):
                raise Conflict("round is not closed")
            if response["round"] > len(state["syntheses"]):
                raise Conflict("round is not closed")
            packet = state["packets"][response["round"] - 1]
            branch = next(
                b for b in state["config"]["branches"] if b["role"] == response["role"]
            )
            placeholder = next(
                (
                    r
                    for r in state["responses"]
                    if r["round"] == response["round"] and r["role"] == response["role"]
                ),
                None,
            )
            if (
                placeholder is None
                or placeholder["status"] != "unknown"
                or any(
                    h["response"]["round"] == response["round"]
                    and h["response"]["role"] == response["role"]
                    for h in state["held_responses"]
                )
                or response["consultation_id"] != consultation_id
                or response["invocation_id"]
                != self._operation(consultation_id, response["round"], response["role"])
                or response["packet_revision"] != packet["packet"]["revision"]
                or response["packet_digest"] != packet["digest"]
                or any(
                    response[key] != branch[branch_key]
                    for key, branch_key in (
                        ("requested_provider", "provider"),
                        ("requested_harness", "harness"),
                        ("requested_harness_version", "harness_version"),
                        ("requested_model", "requested_model"),
                        ("requested_effort", "effort"),
                        ("requested_config_revision", "config_revision"),
                    )
                )
            ):
                raise Conflict("late response does not match unknown invocation")
            self._check_bounds(response, state["config"]["limits"])
            if response["resolved_model"] not in (None, branch["requested_model"]):
                raise Conflict("unapproved resolved model")
            if any(
                response["resolved_" + key] not in (None, branch[key])
                for key in ("provider", "harness", "harness_version", "effort")
            ):
                raise Conflict("unapproved late execution path")
            if response["status"] == "complete" and (
                response["resolved_model"] != branch["requested_model"]
                or not response["recommendation"]
                or any(
                    response["resolved_" + key] != branch[key]
                    for key in ("provider", "harness", "harness_version", "effort")
                )
            ):
                raise Conflict("unapproved late execution path")
            # The callback still records whether the source moved; it cannot confer
            # authority on an already terminal consultation.
            current = self._context_matches(packet["packet"], context_current)
            self._settle(
                self._operation(consultation_id, response["round"], response["role"]),
                response["actual_microusd"],
            )
            state["late_responses"].append(deepcopy(response))
            state.setdefault("late_context", []).append(
                {
                    "round": response["round"],
                    "role": response["role"],
                    "source_current": current,
                }
            )
            self._save(state)
            return state

    def reconcile_usage(self, consultation_id, invocation_id, actual_microusd):
        """Settle delayed telemetry for one known invocation with unknown cost.

        This changes accounting only. The original response, packet, synthesis,
        and terminal decision remain immutable, even if source lineage moved.
        """
        if type(actual_microusd) is not int or actual_microusd < 0:
            raise ValueError("actual_microusd must be a nonnegative integer")
        with self.store.transaction():
            state = self.status(consultation_id)
            outcomes = list(state["responses"])
            outcomes.extend(h["response"] for h in state["held_responses"])
            outcomes.extend(state["late_responses"])
            matching = [
                r
                for r in outcomes
                if r["invocation_id"] == invocation_id
                and r["consultation_id"] == consultation_id
            ]
            if not matching:
                raise Conflict("unknown consultation invocation")
            response = matching[-1]
            if response["actual_microusd"] is not None:
                raise Conflict("invocation usage was already known")
            expected = self._operation(
                consultation_id, response["round"], response["role"]
            )
            if invocation_id != expected:
                raise Conflict("invocation identity mismatch")
            previous = next(
                (
                    entry
                    for entry in state.get("usage_reconciliations", [])
                    if entry["invocation_id"] == invocation_id
                ),
                None,
            )
            if previous:
                if previous["actual_microusd"] != actual_microusd:
                    raise Conflict("usage reconciliation conflict")
                return state
            row = self.store.db.execute(
                "SELECT state,actual FROM reservations WHERE id=?", (invocation_id,)
            ).fetchone()
            if row is None or row["state"] != "unknown":
                raise Conflict("invocation usage is not unknown")
            self._settle(invocation_id, actual_microusd)
            state.setdefault("usage_reconciliations", []).append(
                {"invocation_id": invocation_id, "actual_microusd": actual_microusd}
            )
            self._save(state)
            return state
