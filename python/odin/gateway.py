"""One recorded command path for the local orchestration experiment.

GatewayContext is supplied by trusted service/fixture code, never decoded from
an operator message or a model response. This is not remote authentication.
All handlers are local transactions: no network or subprocess is dispatched.
"""

from dataclasses import asdict, dataclass
from datetime import datetime

from .budgets import Budget
from .chirality import Chirality
from .continuity import Continuity
from .contracts import ROOT, canonical, strict_loads
from .coordination import Actor, Coordination
from .delegation import Delegation
from .development_gateway import ACTIONS as LOOP_ACTIONS
from .development_gateway import EXECUTIVE_ACTIONS as EXECUTIVE_LOOP_ACTIONS
from .development_loop import DevelopmentLoop
from .executive_intervention import ACTIONS as INTERVENTION_ACTIONS, EXECUTIVE_ACTIONS as EXECUTIVE_INTERVENTION_ACTIONS
from .executive_supervision import ACTIONS as SUPERVISION_ACTIONS, EXECUTIVE_ACTIONS as EXECUTIVE_SUPERVISION_ACTIONS
from .memory import Memory
from .orchestration_config import OrchestrationConfig
from .store import Conflict, Refusal, Refused, digest, event, now
from .usage import UsageLedger
from .usage_policy import UsagePolicy, ContinuityCheckpoints, LimitNotices
from .usage_gateway import ACTIONS as USAGE_ACTIONS, EXECUTIVE_ACTIONS as EXECUTIVE_USAGE_ACTIONS

DELEGATION_ACTIONS = {
    "delegation_session": "odin_delegation_session",
    "delegation_assign": "odin_delegation_assign",
    "delegation_followup": "odin_delegation_followup",
    "delegation_status": "odin_delegation_status",
    "delegation_result": "odin_delegation_result",
    "delegation_close": "odin_delegation_close",
}


@dataclass(frozen=True)
class GatewayContext:
    surface: str
    actor: Actor
    # Populated by the trusted service authentication layer, never message data.
    # None means all local projects for the private operator socket only.
    projects: tuple[str, ...] | None = None


def error_result(error, label):
    """A bounded socket reply: the error type and, if fixed, its refusal code."""
    result = {"error": type(error).__name__, "label": label}
    if isinstance(error, Refusal):
        result["detail"] = str(error)
    return result


def fields(payload, required, optional=()):
    if not isinstance(payload, dict) or not set(required) <= payload.keys():
        raise ValueError("missing command fields")
    if payload.keys() - set(required) - set(optional):
        raise ValueError("unknown command fields")


class Gateway:
    def __init__(self, service, config=None, *, delegation_config=None,
                 evaluator_configured=False):
        self.service, self.store = service, service.store
        self.config = config or OrchestrationConfig()
        self.coordination = Coordination(self.store)
        self.budget = Budget(self.store)
        self.chirality = Chirality(self.store, self.budget)
        self.memory = Memory(self.store)
        self.continuity = Continuity(self.store, self.memory)
        # Local delegation is enabled only by an explicit operator configuration
        # file in the state directory; without it every delegation tool refuses.
        self.delegation = Delegation(
            self.store, service.directory, delegation_config
        )
        self.development_loop = DevelopmentLoop(self.store)
        self.usage = UsageLedger(self.store)
        self.usage_policy = UsagePolicy(self.store)
        self.checkpoints = ContinuityCheckpoints(self.store)
        self.limit_notices = LimitNotices(self.store)
        self.evaluator_configured = evaluator_configured
        self.store.db.executescript("""
            CREATE TABLE IF NOT EXISTS gateway_commands
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS gateway_layouts
              (session TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS executive_reports
              (id TEXT PRIMARY KEY, project TEXT NOT NULL, body TEXT NOT NULL);
        """)

    def submit(self, command, *, context):
        """Commit command, local mutations and receipt together, or none of them."""
        self.store.contracts.validate("gateway-command", command)
        if (
            not isinstance(context, GatewayContext)
            or not isinstance(context.actor, Actor)
            or context.surface not in {"terminal", "voice", "harness", "adapter"}
        ):
            raise PermissionError("trusted gateway context required")
        effective_projects = (
            tuple(sorted(self._projects(context)))
            if context.actor.role == "operator"
            and context.surface in {"terminal", "voice"}
            else tuple(sorted(context.projects or ()))
        )
        identity = {
            "surface": context.surface,
            "actor": asdict(context.actor),
            "projects": effective_projects,
        }
        fingerprint = digest({"command": command, "context": identity})
        with self.store.transaction():
            if context.actor.subject == "fable-executive":
                self._executive_scope(command["action"], command["payload"], context)
            self._check_operator_scope(
                command["action"], command["payload"], context, effective_projects
            )
            if command["action"] in LOOP_ACTIONS:
                from .development_gateway import check_scope

                check_scope(self, command["action"], command["payload"])
            if command["action"] in USAGE_ACTIONS:
                from .usage_gateway import scope
                scope(self, command["payload"])
            if command["action"] == "loop_inbox":
                # This internal transport poll observes durable stages; it is
                # not an acknowledgement or a model command. Do not append a
                # receipt and history entry every second while the channel is
                # idle. Claims and every actual transition remain recorded.
                if context.surface == "voice":
                    raise PermissionError("voice cannot read the development inbox")
                value = self._dispatch(
                    command["action"], command["payload"], context, command["operation_id"]
                )
                result = {
                    "schema_version": 1, "operation_id": command["operation_id"],
                    "label": "fake-backend evidence", "result": value,
                }
                self.store.contracts.validate("gateway-receipt", result)
                return result
            prior = self.store.db.execute(
                "SELECT digest,result FROM gateway_commands WHERE id=?",
                (command["operation_id"],),
            ).fetchone()
            if prior:
                if prior[0] != fingerprint:
                    # Deterministic: the same ID with other arguments never succeeds.
                    raise Refused("operation_id_reused")
                receipt = strict_loads(prior[1])
                if receipt["result"].get("held"):
                    # No claim was made. Preserve argument identity, then
                    # reevaluate this same operation with current telemetry.
                    self.store.db.execute("DELETE FROM gateway_commands WHERE id=?", (command["operation_id"],))
                    prior = None
            if prior:
                if command["action"] in {"loop_claim", "loop_ready"}:
                    current = self.development_loop.get(command["payload"]["loop_id"])
                    if receipt["result"]["loop"]["revision"] != current["revision"]:
                        raise Conflict("development acknowledgement revision changed")
                if receipt["result"].get("projection_not_cached"):
                    raise Conflict(
                        "historical projection receipt; request a fresh view"
                    )
                return receipt
            action = command["action"]
            if context.surface == "voice" and action not in {
                "message", "status", "stop",
            }:
                raise PermissionError("voice cannot authorize or dispatch work")
            # Keep raw rejected input out of durable history. A successful action
            # and its recorded command share this same transaction.
            value = self._dispatch(
                action, command["payload"], context, command["operation_id"]
            )
            result = {
                "schema_version": 1,
                "operation_id": command["operation_id"],
                "label": "fake-backend evidence",
                "result": value,
            }
            self.store.contracts.validate("gateway-receipt", result)
            audit_command = command
            if action == "view_delivery":
                # A receipt never archives a private, derived briefing body.
                audit_command = command | {
                    "payload": {
                        "issue_id": command["payload"]["briefing"]["issue_id"],
                        "digest": digest(command["payload"]["briefing"]),
                    }
                }
            elif action == "prepare_decision":
                audit_command = command | {
                    "payload": {
                        "request_id": value["id"],
                        "digest": digest(command["payload"]["decision"]),
                    }
                }
            elif action == "answer_decision":
                audit_command = command | {
                    "payload": {
                        "request_id": command["payload"]["request_id"],
                        "response_digest": digest(command["payload"]["response"]),
                    }
                }
            elif action in LOOP_ACTIONS | USAGE_ACTIONS | INTERVENTION_ACTIONS | SUPERVISION_ACTIONS:
                audit_command = command | {
                    "payload": {
                        "project": command["payload"].get("project"),
                        "digest": digest(command["payload"]),
                    }
                }
            elif action == "repository_import":
                audit_command = command | {
                    "payload": {
                        "project": command["payload"]["project"],
                        "digest": digest(command["payload"]),
                        "snapshot_id": command["payload"]["snapshot_id"],
                        "batch_index": command["payload"]["batch_index"],
                    }
                }
            self.store._history(
                "gateway.command", {"command": audit_command, "context": identity}
            )
            stored_result = result
            if action in {
                "resume",
                "memory_snapshot",
                "memory_source_read",
                "prepare_decision",
                "answer_decision",
                "executive_reports",
                "delegation_status",
                "delegation_result",
                "loop_status",
                "loop_inbox", "usage_status", "context_status", "intervention_status",
                "executive_restart_status",
            }:
                stored_result = result | {"result": {"projection_not_cached": True}}
            self.store.db.execute(
                "INSERT INTO gateway_commands VALUES(?,?,?)",
                (command["operation_id"], fingerprint, canonical(stored_result)),
            )
            return result

    def _executive_scope(self, action, payload, context):
        """Pilot capabilities come from the service binding, never chat text."""
        if (
            context.surface != "harness"
            or context.actor.role != "coordinator"
            or context.actor.subject != "fable-executive"
            or not context.projects
            or action not in {
                "resume", "memory_snapshot", "memory_source_read",
                "executive_report", "executive_reports", *DELEGATION_ACTIONS,
                *EXECUTIVE_LOOP_ACTIONS, *EXECUTIVE_USAGE_ACTIONS, *EXECUTIVE_INTERVENTION_ACTIONS,
                *EXECUTIVE_SUPERVISION_ACTIONS,
            }
            or payload.get("project") not in context.projects
        ):
            raise PermissionError("executive capability denied")
        self.coordination._project(payload["project"])

    def _check_operator_scope(self, action, payload, context, effective_projects):
        """Check current trusted scope before serving even an old receipt."""
        if context.actor.role != "operator" or context.surface not in {
            "terminal",
            "voice",
        }:
            return
        restricted = context.projects is not None
        if action in {"status", "stop"}:
            if restricted:
                raise PermissionError("global operator action requires global scope")
            return
        project = None
        if action in {
            "resume", "memory_snapshot", "memory_source_read", "executive_reports",
            "repository_import", *DELEGATION_ACTIONS, *LOOP_ACTIONS, *USAGE_ACTIONS, *INTERVENTION_ACTIONS,
            *SUPERVISION_ACTIONS,
        }:
            project = payload.get("project")
        elif action == "prepare_decision":
            project = payload.get("decision", {}).get("project")
        elif action == "answer_decision":
            project, _ = self.continuity._request_meta(payload["request_id"])
        elif action == "view_delivery":
            project = payload.get("briefing", {}).get("project", {}).get("id")
        elif action == "view_ack":
            row = self.store.db.execute(
                "SELECT project FROM continuity_deliveries WHERE id=?",
                (payload["delivery_id"],),
            ).fetchone()
            project = row[0] if row else None
        elif action in {"message", "grant", "layout_bind"}:
            project = payload.get("project")
        elif action == "revoke":
            row = self.store.db.execute(
                "SELECT body FROM coordination_grants WHERE id=?",
                (payload["grant_id"],),
            ).fetchone()
            project = strict_loads(row[0])["project"] if row else None
        elif action == "layout_observe":
            row = self.store.db.execute(
                "SELECT body FROM gateway_layouts WHERE session=?",
                (payload["session"],),
            ).fetchone()
            project = strict_loads(row[0])["project"] if row else None
        if project is None:
            if restricted:
                raise PermissionError("unscoped operator action denied")
        elif project not in effective_projects:
            raise PermissionError("project command denied")

    def _projects(self, context):
        self._operator(context)
        if context.projects is not None:
            return context.projects
        return tuple(p["id"] for p in self.store.records("Project"))

    def _authority_revision(self):
        # The service supplies current policy, not the operator's old answer.
        return digest(self.config.data)

    @staticmethod
    def _operator(context):
        if context.actor.role != "operator" or context.surface not in {
            "terminal",
            "voice",
        }:
            raise PermissionError("operator command path required")

    def _handoff(self, source):
        row = self.store.db.execute(
            "SELECT digest,body,accepted_at FROM coordination_handoffs WHERE id=?",
            (source["handoff_operation"],),
        ).fetchone()
        if not row or row[0] != source["handoff_digest"] or not row[2]:
            raise Conflict("consultation requires the accepted handoff")
        return strict_loads(row[1])

    def current_source(self, source):
        """Resolve lineage from stored records, never from a model's assertion."""
        try:
            packet = self._handoff(source)
            if datetime.fromisoformat(packet["deadline"]) <= datetime.fromisoformat(
                now()
            ):
                raise Conflict("handoff deadline expired")
            self.coordination._packet_current(packet)
            self.coordination._authorized(
                packet["grant_id"],
                "handoff",
                packet["project"],
                Actor("coordinator", packet["from_subject"]),
                project=packet["project"],
            )
            assignment = self.store.get(packet["assignment"])
            commitment = self.store.get(packet["commitment"])
            return {
                "handoff_operation": packet["operation_id"],
                "handoff_digest": digest(packet),
                "project": packet["project"],
                "assignment": assignment["id"],
                "assignment_revision": assignment["rev"],
                "ownership_generation": commitment["ownership_generation"],
                "source_revision": commitment["rev"],
            }
        except (Conflict, PermissionError, KeyError, TypeError):
            return None

    def _consultation_owner(self, source, actor, *, current=True):
        packet = self._handoff(source)
        if actor.role == "coordinator":
            self.coordination._actor(actor, "coordinator")
            if actor.subject != packet["from_subject"]:
                raise PermissionError("wrong consultation coordinator")
        elif actor.role == "planner":
            self.coordination._actor(actor, "planner")
            self.coordination._recipient(packet, actor)
        else:
            raise PermissionError("consultation owner required")
        if current and self.current_source(source) != source:
            raise Conflict("stale consultation authority")
        return packet

    @staticmethod
    def _service_context():
        return {
            "record_store": "persistent_local_sqlite",
            "execution_backend": "fake_saga",
            "legacy_label_scope": "execution_backend_not_record_persistence",
            "reports": "persisted_unverified_not_applied",
            "repository_path": str(ROOT),
            "documentation_path": str(ROOT / "docs"),
            "repository_memory": "explicit_committed_snapshot_not_live_checkout",
        }

    def _dispatch(self, action, payload, context, operation):
        actor = context.actor
        if action in INTERVENTION_ACTIONS:
            if actor.subject != "fable-executive":
                self._operator(context)
            from .executive_intervention import dispatch
            return dispatch(self, action, payload, context, operation)
        if action in USAGE_ACTIONS:
            from .usage_gateway import dispatch
            return dispatch(self, action, payload, context, operation)
        if action in SUPERVISION_ACTIONS:
            if actor.subject != "fable-executive":
                self._operator(context)
            from .executive_supervision import dispatch
            return dispatch(self, action, payload, context, operation)
        if action in LOOP_ACTIONS:
            from .development_gateway import dispatch

            return dispatch(self, action, payload, context, operation)
        if action in DELEGATION_ACTIONS:
            if actor.subject == "fable-executive":
                self._executive_scope(action, payload, context)
            else:
                self._operator(context)
            project = payload["project"]
            arguments = {k: v for k, v in payload.items() if k != "project"}
            if action not in {"delegation_status", "delegation_result"}:
                # Reads stay available during an operator stop; writes do not.
                self.coordination._live()
                # The bridge carries the stable operation_id on the command
                # envelope; the tool definition requires the same value.
                if arguments.setdefault("operation_id", operation) != operation:
                    raise Conflict("delegation operation identity mismatch")
            self.store.contracts.validate_definition(
                "executive-tool-input", DELEGATION_ACTIONS[action], arguments
            )
            arguments.pop("operation_id", None)
            if action == "delegation_status":
                return self.delegation.status(arguments, project=project)
            if action == "delegation_result":
                return self.delegation.result(arguments, project=project)
            common = {"project": project, "actor": actor.subject, "operation": operation}
            if action == "delegation_session":
                method = {
                    "create": self.delegation.open_session,
                    "resume": self.delegation.resume_session,
                    "stop": self.delegation.stop_session,
                }[arguments["action"]]
                return method(arguments, **common)
            if action == "delegation_assign":
                return self.delegation.assign(arguments, **common)
            if action == "delegation_followup":
                return self.delegation.followup(arguments, **common)
            return self.delegation.close(arguments, **common)
        if action == "repository_import":
            from .repository_memory import import_batch

            self._operator(context)
            self.coordination._live()
            return import_batch(self.store, payload, project=payload["project"])
        if action == "executive_report":
            self._executive_scope(action, payload, context)
            self.store.contracts.validate("executive-report", payload)
            self.coordination._live()
            report = payload | {
                "id": operation, "actor": actor.subject, "recorded_at": now(),
                "verification": "unverified", "applied": False,
            }
            self.store.db.execute(
                "INSERT INTO executive_reports VALUES(?,?,?)",
                (operation, payload["project"], canonical(report)),
            )
            self.store._history("executive.reported", report)
            return {"report": report, "service_context": self._service_context()}
        if action == "executive_reports":
            if actor.subject == "fable-executive":
                self._executive_scope(action, payload, context)
            else:
                self._operator(context)
            fields(payload, ("project",), ("limit",))
            limit = payload.get("limit", 10)
            if type(limit) is not int or not 1 <= limit <= 20:
                raise ValueError("invalid report limit")
            rows = self.store.db.execute(
                "SELECT body FROM executive_reports WHERE project=? "
                "ORDER BY rowid DESC LIMIT ?", (payload["project"], limit),
            )
            return {
                "reports": [strict_loads(row[0]) for row in rows], "applied": False,
                "service_context": self._service_context(),
            }
        if action in {
            "resume",
            "prepare_decision",
            "answer_decision",
            "view_delivery",
            "view_ack",
            "memory_snapshot",
            "memory_source_read",
        }:
            if actor.subject == "fable-executive":
                self._executive_scope(action, payload, context)
                scope = context.projects
            else:
                self._operator(context)
                scope = self._projects(context)
            common = {"principal": actor.subject, "permitted_projects": scope}
            if action == "resume":
                fields(
                    payload,
                    ("project",),
                    (
                        "detail_bytes",
                        "obligation_offset",
                        "obligation_page_token",
                        "obligation_limit",
                        "decision_offset",
                        "decision_page_token",
                        "decision_limit",
                    ),
                )
                view = self.continuity.resume(**payload, **common)
                if actor.subject == "fable-executive":
                    loops = self.development_loop.for_project(payload["project"])
                    active = [
                        {key: loop[key] for key in (
                            "id", "session_id", "status", "round", "revision",
                            "current_job", "current_stage", "reason",
                        )}
                        for loop in loops if loop["status"] not in {"complete", "stopped"}
                    ]
                    return view | {
                        "service_context": self._service_context(),
                        "development_loops": active,
                        "context_checkpoint": self.checkpoints.latest_checkpoint(payload["project"]),
                        "usage_policy": self.usage_policy.get(payload["project"]),
                    }
                return view
            if action == "memory_source_read":
                self.store.contracts.validate("memory-source-read", payload)
                return self.memory.read_source(**payload, **common)
            if action == "prepare_decision":
                fields(payload, ("decision",))
                prepared = payload["decision"] | {
                    "recipient": actor.subject,
                    "authority_revision": self._authority_revision(),
                }
                return self.continuity.prepare_decision(prepared, **common)
            if action == "answer_decision":
                fields(
                    payload,
                    ("request_id", "response", "expected_rev", "evidence_digest"),
                )
                return self.continuity.respond_decision(
                    **payload,
                    authority_revision=self._authority_revision(),
                    channel="text",
                    **common,
                )
            if action == "view_delivery":
                fields(payload, ("briefing",))
                delivery = self.continuity.record_delivery(
                    payload["briefing"], delivery_id=operation, **common
                )
                return {"delivery_id": delivery}
            if action == "view_ack":
                fields(payload, ("delivery_id",))
                return {
                    "acknowledged_seq": self.continuity.acknowledge(**payload, **common)
                }
            fields(payload, ("project",), ("at", "limit", "max_bytes"))
            if payload["project"] not in scope:
                raise PermissionError("project view denied")
            return self.memory.snapshot(**payload, principal=actor.subject)
        if action in {
            "message",
            "status",
            "stop",
            "grant",
            "revoke",
            "layout_bind",
            "layout_observe",
        }:
            self._operator(context)
        if action == "status":
            fields(payload, ())
            return self.service.status()
        if action == "stop":
            fields(payload, ("reason",))
            command = {
                "schema_version": 1,
                "operation_id": operation,
                "action": "stop",
                "reason": payload["reason"],
            }
            self.store.contracts.validate("operator-command", command)
            item = event(
                "operator.command.stop", command, producer="fixture-cli", key=operation
            )
            item["id"] = operation
            self.service.handle(self.store, item)
            return {"local_stopped": True, "remote_outcome": "queued_for_fake_backend"}
        if action == "message":
            self.store.contracts.validate("surface-message", payload)
            if payload["project"] is not None:
                self.coordination._project(payload["project"])
            item = event(
                "operator.message",
                payload | {"surface": context.surface},
                producer="fixture-gateway",
                scope={"project": payload["project"]} if payload["project"] else {},
                key=operation,
            )
            self.store.intake(item)
            self.store.process(self.service.handle)
            return {"status": "recorded", "delivery": "pending_harness_integration"}
        if action == "grant":
            return {"created": self.coordination.grant(payload, actor=actor)}
        if action == "revoke":
            fields(payload, ("grant_id",))
            return {
                "revoked": self.coordination.revoke(payload["grant_id"], actor=actor)
            }
        if action == "handoff":
            if payload.get("model_config_rev") != self.config.config_rev:
                raise Conflict("unconfigured handoff model revision")
            if (
                payload.get("budget_ref") is None
                or not self.store.db.execute(
                    "SELECT 1 FROM budgets WHERE id=?", (payload["budget_ref"],)
                ).fetchone()
            ):
                raise Conflict("handoff budget is not recorded")
            self.coordination._authorized(
                payload["grant_id"],
                "handoff",
                payload["budget_ref"],
                actor,
                project=payload["project"],
            )
            return {"created": self.coordination.handoff(payload, actor=actor)}
        if action == "accept_handoff":
            fields(payload, ("handoff_operation",))
            return {
                "accepted": self.coordination.accept_handoff(
                    payload["handoff_operation"], actor=actor
                )
            }
        if action == "report":
            return {
                "eligible_for_checking": self.coordination.report(payload, actor=actor)
            }
        if action == "portfolio":
            fields(payload, ("projects", "grant_ids"))
            return {
                "projects": self.coordination.portfolio(
                    payload["projects"], actor=actor, grant_ids=payload["grant_ids"]
                )
            }
        if action == "consult_start":
            fields(payload, ("consultation_id", "config", "packet", "budget_id"))
            self.store.contracts.validate("chirality-packet", payload["packet"])
            handoff = self._consultation_owner(payload["packet"]["source"], actor)
            if datetime.fromisoformat(
                payload["config"]["deadline_at"]
            ) > datetime.fromisoformat(handoff["deadline"]):
                raise Conflict("consultation exceeds handoff deadline")
            if payload["budget_id"] != handoff["budget_ref"]:
                raise Conflict("consultation must charge the handoff budget")
            self.store.contracts.validate("chirality-config", payload["config"])
            for branch in payload["config"]["branches"]:
                spec = self.config.data["roles"][branch["role"]]
                expected = {
                    "provider": spec["provider"],
                    "harness": spec["harness"],
                    "harness_version": spec["harness_version"],
                    "requested_model": spec["model"],
                    "effort": spec["effort"],
                    "config_revision": self.config.config_rev,
                }
                if any(branch[key] != value for key, value in expected.items()):
                    raise Conflict("unconfigured consultation identity")
            state = self.chirality.start(
                payload["consultation_id"],
                payload["config"],
                payload["packet"],
                payload["budget_id"],
                context_current=self.current_source,
            )
            return {
                "consultation_id": state["id"],
                "state": state["state"],
                "packet_digest": state["packets"][0]["digest"],
            }
        if action in {"consult_response", "consult_late"}:
            fields(payload, ("consultation_id", "response"))
            response = payload["response"]
            self.store.contracts.validate("chirality-response", response)
            expected = self.chirality._operation(
                payload["consultation_id"], response["round"], response["role"]
            )
            # Independent branch contexts have only a response path. They cannot
            # read the other branch or the operator's portfolio through this API.
            if (
                context.surface != "adapter"
                or actor.role != "consultant"
                or actor.subject != response["role"]
                or actor.session != expected
                or actor.incarnation != response["round"]
            ):
                raise PermissionError("bound independent branch context required")
            method = (
                self.chirality.respond
                if action == "consult_response"
                else self.chirality.record_late
            )
            method(
                payload["consultation_id"],
                response,
                context_current=self.current_source,
            )
            return {"status": "recorded", "consultation_id": payload["consultation_id"]}
        if action == "consult_usage":
            fields(
                payload,
                (
                    "consultation_id",
                    "invocation_id",
                    "round",
                    "role",
                    "actual_microusd",
                ),
            )
            expected = self.chirality._operation(
                payload["consultation_id"], payload["round"], payload["role"]
            )
            if (
                context.surface != "adapter"
                or actor.role != "consultant"
                or actor.subject != payload["role"]
                or actor.session != expected
                or actor.incarnation != payload["round"]
                or payload["invocation_id"] != expected
            ):
                raise PermissionError("bound independent branch context required")
            self.chirality.reconcile_usage(
                payload["consultation_id"], expected, payload["actual_microusd"]
            )
            return {
                "status": "usage_recorded",
                "consultation_id": payload["consultation_id"],
                "invocation_id": expected,
            }
        if action in {
            "consult_close",
            "consult_followup",
            "consult_status",
            "consult_end",
        }:
            required = (
                ("consultation_id", "packet")
                if action == "consult_followup"
                else ("consultation_id",)
            )
            fields(payload, required)
            state = self.chirality.status(payload["consultation_id"])
            source = state["packets"][-1]["packet"]["source"]
            self._consultation_owner(
                source, actor, current=action == "consult_followup"
            )
            if action == "consult_followup":
                state = self.chirality.followup(
                    state["id"], payload["packet"], context_current=self.current_source
                )
            elif action == "consult_close":
                state = self.chirality.close_round(
                    state["id"], context_current=self.current_source
                )
            elif action == "consult_end":
                state = self.chirality.terminate_between_rounds(state["id"])
            # Portfolio coordinator can inspect synthesis; isolated consultant
            # contexts have already been denied above.
            return state
        if action == "session_intent":
            fields(payload, ("handoff_operation", "role"))
            if payload["role"] not in {"opus", "sol"}:
                raise Conflict("planning context may request Saga worker intents only")
            row = self.store.db.execute(
                "SELECT body,accepted_at FROM coordination_handoffs WHERE id=?",
                (payload["handoff_operation"],),
            ).fetchone()
            if not row:
                raise KeyError(payload["handoff_operation"])
            if not row[1]:
                raise Conflict("handoff not accepted")
            packet = strict_loads(row[0])
            self.coordination._actor(actor, "planner")
            self.coordination._recipient(packet, actor)
            self.coordination._packet_current(packet)
            if datetime.fromisoformat(packet["deadline"]) <= datetime.fromisoformat(
                now()
            ):
                raise Conflict("handoff deadline expired")
            self.coordination.authorize_action(
                packet["grant_id"],
                "handoff",
                packet["project"],
                actor=Actor("coordinator", packet["from_subject"]),
            )
            return self.config.intent(
                payload["role"], packet["project"], actor.session, actor.incarnation
            )
        if action == "layout_bind":
            self.store.contracts.validate("layout-binding", payload)
            session = self.store.get(payload["session"])
            if (
                session["record_type"] != "PlanningSession"
                or session["project"] != payload["project"]
                or session["incarnation"] != payload["incarnation"]
                or session["state"] not in {"active", "idle"}
            ):
                raise Conflict("stale layout binding")
            self.store.db.execute(
                "INSERT INTO gateway_layouts VALUES(?,?) ON CONFLICT(session) DO UPDATE SET body=excluded.body",
                (payload["session"], canonical(payload)),
            )
            self.store._history("layout.bound", payload)
            return {"status": "bound", "authority": "visibility_only"}
        if action == "layout_observe":
            self.store.contracts.validate("layout-observation", payload)
            row = self.store.db.execute(
                "SELECT body FROM gateway_layouts WHERE session=?",
                (payload["session"],),
            ).fetchone()
            if not row:
                raise Conflict("unbound layout")
            binding = strict_loads(row[0])
            if any(
                payload[key] != binding[key]
                for key in ("incarnation", "host", "server_incarnation", "pane")
            ):
                raise Conflict("layout incarnation mismatch")
            session = self.store.get(payload["session"])
            if (
                session["record_type"] != "PlanningSession"
                or session["project"] != binding["project"]
                or session["incarnation"] != binding["incarnation"]
                or session["state"] not in {"active", "idle"}
            ):
                raise Conflict("layout session no longer active")
            self.store._history("layout.observed", payload)
            return {"status": "recorded", "authority": "visibility_only"}
        raise ValueError("unsupported gateway action")
