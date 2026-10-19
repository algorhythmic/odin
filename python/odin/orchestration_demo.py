"""Executable synthetic portfolio → task → consultation → return workflow.

No model, audio, Herdr process or external service is invoked. Model identities
on simulated responses are fixture assertions, not observed provider access.
"""

from datetime import datetime, timedelta, timezone

from .contracts import ROOT, identifier, strict_loads
from .coordination import Actor
from .gateway import Gateway, GatewayContext
from .service import Service, fixture_record
from .store import Conflict, digest, now


def command(action, payload):
    return {
        "schema_version": 1,
        "operation_id": identifier(),
        "action": action,
        "payload": payload,
    }


def fixture(name):
    return strict_loads((ROOT / "fixtures" / name).read_text())


def seed(service, gateway):
    """Construct trusted synthetic records; this is not model-accessible intake."""
    if service.store.records():
        raise Conflict("orchestration demo requires empty state")
    project = fixture_record("Project", interface_decision_owner=None)
    session = fixture_record("PlanningSession", project=project["id"], state="active")
    project["interface_decision_owner"] = session["id"]
    commitment = fixture_record(
        "Commitment", project=project["id"], owner=session["id"]
    )
    assignment = fixture_record(
        "Assignment", commitment=commitment["id"], owner=session["id"]
    )
    for record in (project, session, commitment, assignment):
        service.store.create(record)
    budget_id = "fixture-budget:" + identifier()
    gateway.budget.create(budget_id, 120, 6, 0)
    expires = (
        (datetime.now(timezone.utc) + timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z")
    )
    templates = fixture("coordination.json")
    grant = templates["grant"] | {
        "id": identifier(),
        "project": project["id"],
        "resources": [project["id"], budget_id],
        "issued_at": now(),
        "expires_at": expires,
    }
    packet = templates["handoff"] | {
        "operation_id": identifier(),
        "project": project["id"],
        "project_rev": project["rev"],
        "commitment": commitment["id"],
        "commitment_rev": commitment["rev"],
        "assignment": assignment["id"],
        "assignment_rev": assignment["rev"],
        "ownership_generation": commitment["ownership_generation"],
        "to_session": session["id"],
        "to_incarnation": session["incarnation"],
        "grant_id": grant["id"],
        "budget_ref": budget_id,
        "deadline": expires,
        "issued_at": now(),
        "model_config_rev": gateway.config.config_rev,
        "requirements": {
            "objective": commitment["objective"],
            "criteria": [
                {"id": c["id"], "text": c["text"]} for c in commitment["criteria"]
            ],
        },
    }
    operator = GatewayContext("terminal", Actor("operator", grant["issuer"]))
    fable = GatewayContext("harness", Actor("coordinator", "Fable"))
    astra = GatewayContext(
        "harness", Actor("planner", "Astra", session["id"], session["incarnation"])
    )
    return {
        "project": project,
        "session": session,
        "commitment": commitment,
        "assignment": assignment,
        "grant": grant,
        "packet": packet,
        "budget_id": budget_id,
        "operator": operator,
        "fable": fable,
        "astra": astra,
    }


def consultation_config(gateway, deadline):
    config = fixture("chirality-config.json")
    config["enabled"] = True  # Explicit experiment; ordinary routing never starts it.
    config["deadline_at"] = deadline
    for branch in config["branches"]:
        spec = gateway.config.data["roles"][branch["role"]]
        branch.update(
            provider=spec["provider"],
            harness=spec["harness"],
            harness_version=spec["harness_version"],
            requested_model=spec["model"],
            effort=spec["effort"],
            config_revision=gateway.config.config_rev,
        )
    return config


def branch_response(state, role, *, recommendation, objection, cost):
    """A simulated adapter response with exact invocation and packet lineage."""
    branch = next(b for b in state["config"]["branches"] if b["role"] == role)
    packet = state["packets"][-1]
    response = {
        "schema_version": 1,
        "consultation_id": state["id"],
        "invocation_id": f"chirality:{state['id']}:{state['round']}:{role}",
        "round": state["round"],
        "role": role,
        "packet_revision": packet["packet"]["revision"],
        "packet_digest": packet["digest"],
        "status": "complete",
        "recommendation": recommendation,
        "evidence": ["fixture:contract-check"],
        "assumptions": ["Synthetic evidence only"],
        "objections": [objection] if objection else [],
        "actual_microusd": cost,
        "requested_config_revision": branch["config_revision"],
    }
    for key in ("provider", "harness", "harness_version", "model", "effort"):
        value = branch["requested_model" if key == "model" else key]
        response["requested_" + key] = value
        response["resolved_" + key] = value
    return response


def run(directory, config=None):
    with Service(directory) as service:
        service.recover()
        gateway = Gateway(service, config)
        data = seed(service, gateway)
        gateway.submit(command("grant", data["grant"]), context=data["operator"])
        handoff_command = command("handoff", data["packet"])
        handoff_receipt = gateway.submit(handoff_command, context=data["fable"])
        gateway.submit(
            command(
                "accept_handoff", {"handoff_operation": data["packet"]["operation_id"]}
            ),
            context=data["astra"],
        )
        intent = gateway.submit(
            command(
                "session_intent",
                {"handoff_operation": data["packet"]["operation_id"], "role": "sol"},
            ),
            context=data["astra"],
        )["result"]
        portfolio = gateway.submit(
            command(
                "portfolio",
                {
                    "projects": [data["project"]["id"]],
                    "grant_ids": {data["project"]["id"]: data["grant"]["id"]},
                },
            ),
            context=data["fable"],
        )["result"]
        source = {
            "handoff_operation": data["packet"]["operation_id"],
            "handoff_digest": digest(data["packet"]),
            "project": data["project"]["id"],
            "assignment": data["assignment"]["id"],
            "assignment_revision": data["assignment"]["rev"],
            "ownership_generation": data["commitment"]["ownership_generation"],
            "source_revision": data["commitment"]["rev"],
        }
        packet = fixture("chirality-packet.json") | {"source": source}
        consultation = identifier()
        gateway.submit(
            command(
                "consult_start",
                {
                    "consultation_id": consultation,
                    "config": consultation_config(gateway, data["packet"]["deadline"]),
                    "packet": packet,
                    "budget_id": data["budget_id"],
                },
            ),
            context=data["astra"],
        )
        for round_number in (1, 2):
            state = gateway.chirality.status(consultation)
            for role in ("fable", "astra"):
                response = branch_response(
                    state,
                    role,
                    recommendation="Proceed" if role == "fable" else "Hold",
                    objection="Independent acceptance evidence is incomplete"
                    if role == "astra"
                    else "",
                    cost=None if round_number == 2 and role == "astra" else 5,
                )
                branch = GatewayContext(
                    "adapter",
                    Actor("consultant", role, response["invocation_id"], round_number),
                )
                gateway.submit(
                    command(
                        "consult_response",
                        {"consultation_id": consultation, "response": response},
                    ),
                    context=branch,
                )
            state = gateway.submit(
                command("consult_close", {"consultation_id": consultation}),
                context=data["astra"],
            )["result"]
            if round_number == 1:
                packet = packet | {
                    "revision": 2,
                    "target": "Identify the missing acceptance evidence",
                }
                gateway.submit(
                    command(
                        "consult_followup",
                        {"consultation_id": consultation, "packet": packet},
                    ),
                    context=data["astra"],
                )
        result = fixture("coordination.json")["result"] | {
            "report_id": identifier(),
            "operation_id": data["packet"]["operation_id"],
            "project": data["project"]["id"],
            "commitment": data["commitment"]["id"],
            "assignment": data["assignment"]["id"],
            "session": data["session"]["id"],
            "incarnation": data["session"]["incarnation"],
            "reported_at": now(),
        }
        gateway.submit(command("report", result), context=data["astra"])
        voice = GatewayContext("voice", data["operator"].actor)
        voice_refused = False
        try:
            gateway.submit(
                command("grant", data["grant"] | {"id": identifier()}), context=voice
            )
        except PermissionError:
            voice_refused = True
        gateway.submit(
            command(
                "message",
                {
                    "project": data["project"]["id"],
                    "text": "Summarize the pending decision.",
                },
            ),
            context=voice,
        )
        binding = {
            "schema_version": 1,
            "project": data["project"]["id"],
            "session": data["session"]["id"],
            "incarnation": data["session"]["incarnation"],
            "host": "fixture-host",
            "server_incarnation": "fixture-server-1",
            "workspace": "fixture-project-workspace",
            "tab": "fixture-feature-tab",
            "pane": "fixture-pane",
            "evidence_mode": "fixture",
        }
        gateway.submit(command("layout_bind", binding), context=data["operator"])
        observed = {
            k: v for k, v in binding.items() if k not in {"project", "workspace", "tab"}
        } | {"state": "done"}
        gateway.submit(command("layout_observe", observed), context=data["operator"])
    with Service(directory) as service:
        service.recover()
        gateway = Gateway(service, config)
        replayed = (
            gateway.submit(handoff_command, context=data["fable"]) == handoff_receipt
        )
        gateway.submit(
            command("revoke", {"grant_id": data["grant"]["id"]}),
            context=data["operator"],
        )
        gateway.submit(
            command("stop", {"reason": "synthetic workflow finished"}), context=voice
        )
        output = {
            "schema_version": 1,
            "label": "fake-backend evidence",
            "models_executed": False,
            "handoff": data["packet"]["operation_id"],
            "consultation": consultation,
            "advice_state": state["state"],
            "disagreement_preserved": bool(state["syntheses"][-1]["dissent"]),
            "assignment_state": service.store.get(data["assignment"]["id"])["state"],
            "worker_execution_path": intent["execution_path"],
            "unknown_cost_reservations": service.store.db.execute(
                "SELECT count(*) FROM reservations WHERE state='unknown'"
            ).fetchone()[0],
            "receipt_count": service.store.db.execute(
                "SELECT count(*) FROM gateway_commands"
            ).fetchone()[0],
            "portfolio_projects": len(portfolio["projects"]),
            "restart_replay": replayed,
            "voice_approval_refused": voice_refused,
            "stop_recorded": service.store.stopped(),
        }
        service.store.contracts.validate("orchestration-demo", output)
        return output
