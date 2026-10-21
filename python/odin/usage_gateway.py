"""Project-scoped metadata imports and non-authoritative context checkpoints."""
from .contracts import canonical, strict_loads
from .store import Conflict

EXECUTIVE_ACTIONS = {"usage_status", "context_status", "context_checkpoint"}
ACTIONS = EXECUTIVE_ACTIONS | {"usage_import", "usage_configure"}


def scope(gateway, payload):
    project = payload["project"]
    gateway.coordination._project(project)
    if payload.get("loop_id"):
        loop = gateway.development_loop.get(payload["loop_id"])
        if loop["project"] != project:
            raise PermissionError("usage loop belongs to another project")
        if payload.get("session_id") and loop["session_id"] != payload["session_id"]:
            raise PermissionError("usage loop belongs to another native session")
    if payload.get("stage_id"):
        stage = gateway.development_loop.stage(payload["stage_id"])
        if stage["project"] != project or stage["loop_id"] != payload.get("loop_id"):
            raise PermissionError("usage stage scope mismatch")


def dispatch(gateway, action, payload, context, operation):
    if context.actor.subject != "fable-executive" or action not in EXECUTIVE_ACTIONS:
        gateway._operator(context)
    gateway.store.contracts.validate_definition("usage-command", action, payload)
    scope(gateway, payload)
    project = payload["project"]
    if action == "usage_configure":
        return {"policy": gateway.usage_policy.configure(project, payload["policy"], operation),
                "scope": "future_admission_only_not_native_spend_enforcement"}
    if action == "usage_import":
        if len(canonical(payload).encode()) > 480000:
            raise ValueError("usage import exceeds bounded command size")
        outcomes = {}
        for item in payload["observations"]:
            if item.get("project_id") != project:
                raise PermissionError("usage observation project mismatch")
            scope(gateway, {"project": project, "loop_id": item.get("loop_id"),
                            "stage_id": item.get("stage_id")})
            if item.get("loop_id"):
                loop = gateway.development_loop.get(item["loop_id"])
                native_sessions = {loop["session_id"]}
                if item.get("stage_id"):
                    from .development_delegation import binding
                    delegated = binding(gateway.store, item["stage_id"])
                    if delegated:
                        native_sessions.add(gateway.store.get(delegated["session_id"])["native_session_id"])
                else:
                    from .development_delegation import initialize
                    initialize(gateway.store)
                    for row in gateway.store.db.execute(
                        "SELECT body FROM development_delegations WHERE loop_id=? AND project=?",
                        (loop["id"], project),
                    ):
                        delegated = strict_loads(row[0])
                        native_sessions.add(gateway.store.get(delegated["session_id"])["native_session_id"])
                if item.get("session_id") not in native_sessions:
                    raise PermissionError("usage native session has no recorded loop/stage lineage; import project-only metadata")
            outcome = gateway.usage.ingest(item)
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if "coverage" in payload:
            gateway.usage.record_coverage(payload["source_id"], payload["coverage"], project_id=project)
        return {"outcomes": outcomes, "provenance": "operator_imported_native_metadata_not_attested"}
    if action == "usage_status":
        view = gateway.usage.summary(project_id=project, **{
            k: payload[k] for k in ("loop_id", "stage_id") if k in payload})
        # Detailed imports remain stored; a status view must not grow with history.
        view.pop("quota_snapshots", None)
        view["coverage_more_available"] = len(view["coverage"]) > 16
        view["coverage"] = view["coverage"][:16]
        return {"usage": view, "policy": gateway.usage_policy.get(project),
                "admission": gateway.usage_policy.check(project, purpose="status", session_id=payload.get("session_id"))}
    if action == "context_status":
        return {"checkpoint": gateway.checkpoints.latest_checkpoint(project, payload.get("session_id")),
                "verification": "attributed_summary_not_canonical_state"}
    if action == "context_checkpoint":
        item = payload["checkpoint"]
        if item.get("session_id", payload["session_id"]) != payload["session_id"]:
            raise Conflict("checkpoint native session mismatch")
        return {"checkpoint": gateway.checkpoints.checkpoint(
            project, item | {"session_id": payload["session_id"]}, operation,
            expected_session_id=payload["session_id"]),
            "verification": "attributed_summary_not_canonical_state"}
    raise ValueError("unknown usage command")
