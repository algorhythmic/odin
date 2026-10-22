"""One-use native tool permits for the trusted local development executive.

A permit controls a future hook admission, not an OS process or a filesystem
sandbox. Tool inputs are hashed; neither commands nor edit contents are retained.
A Bash permit may be bound to background execution; it closes at launch because
Odin does not observe a background command's outcome.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .contracts import Contracts, canonical, strict_loads
from .store import AccessRefused, Conflict, Refused, digest, now

ACTIONS = {"intervention_begin", "intervention_end", "intervention_status",
           "intervention_authorize", "intervention_finish", "intervention_reconcile"}
EXECUTIVE_ACTIONS = ACTIONS - {"intervention_reconcile"}
TOOLS = ("Bash", "Write", "Edit", "NotebookEdit")
BACKGROUND_NOTE = ("Background permits close at launch. Odin does not observe the outcome "
                   "of a background command; inspect its effects directly.")


def initialize(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS executive_interventions
        (id TEXT PRIMARY KEY, project TEXT NOT NULL, session TEXT NOT NULL, body TEXT NOT NULL)""")


def normalized(tool, inputs):
    if tool not in TOOLS or not isinstance(inputs, dict):
        raise ValueError("intervention_tool_not_supported")
    inputs = dict(inputs)
    # Native descriptions are UI labels, not executable inputs.
    inputs.pop("description", None)
    if tool == "Bash":
        if not isinstance(inputs.get("command"), str) or not inputs["command"].strip():
            raise ValueError("intervention_command_required")
        if inputs.pop("dangerouslyDisableSandbox", None) not in (None, False):
            raise ValueError("intervention_sandbox_override_denied")
        # Background execution stays in the digest, so a permit is bound to it.
        background = inputs.pop("run_in_background", None)
        if background is True:
            inputs["run_in_background"] = True
        elif background not in (None, False):
            raise ValueError("intervention_background_invalid")
    else:
        path = inputs.get("notebook_path" if tool == "NotebookEdit" else "file_path")
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ValueError("intervention_absolute_path_required")
    if len(canonical(inputs).encode()) > 16384:
        raise ValueError("intervention_input_too_large")
    return {"tool": tool, "input": inputs}


def _call_input(call):
    """Executable input a begin call permits, with background bound explicitly."""
    inputs = call["input"]
    if call.get("background"):
        if call["tool"] != "Bash":
            raise ValueError("intervention_background_bash_only")
        inputs = inputs | {"run_in_background": True}
    elif inputs.get("run_in_background") not in (None, False):
        raise ValueError("intervention_background_requires_flag")
    return normalized(call["tool"], inputs)


def _live(item):
    return item["state"] == "active" and datetime.fromisoformat(item["expires_at"]) > datetime.now(timezone.utc)


def _rows(store, project):
    initialize(store)
    return [strict_loads(row[0]) for row in store.db.execute(
        "SELECT body FROM executive_interventions WHERE project=?", (project,))]


def delegation_guard(store, project):
    if any(_live(x) or any(p["state"] == "admitted" for p in x["permits"])
           for x in _rows(store, project)):
        raise Conflict("executive_intervention_active")


def _busy(store, project):
    # queued work also owns the workspace before its runner starts.
    return store.db.execute("SELECT 1 FROM delegation_turns WHERE project=? AND state IN ('queued','launching','running','interrupting') LIMIT 1", (project,)).fetchone() is not None


def _save(store, item):
    store.contracts.validate("executive-intervention", item)
    store.db.execute("INSERT INTO executive_interventions VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                     (item["id"], item["project"], item["session_id"], canonical(item)))


def _view(item):
    if item is None:
        return {"mode": "executive", "intervention": None}
    copy = dict(item)
    effective_state = "expired" if copy["state"] == "active" and not _live(item) else copy["state"]
    view = {"mode": "intervention" if _live(item) else "executive", "intervention": copy, "effective_state": effective_state,
            "in_flight_unknown": any(p["state"] == "admitted" for p in item["permits"]),
            "boundary": "native_hook_admission_not_os_isolation"}
    if any(p.get("background") for p in item["permits"]):
        view["background_outcome"] = "not_observed_by_odin"
        view["background_note"] = BACKGROUND_NOTE
    return view


def dispatch(gateway, action, payload, context, operation):
    store = gateway.store
    store.contracts.validate_definition("intervention-command", action, payload)
    project, session = payload["project"], payload["session_id"]
    gateway.coordination._project(project)
    # Only an operator-staged, activated v3 delegated manifest enables this path.
    from .executive_runtime import _load
    manifest, _ = _load(gateway.service.directory)
    if (manifest.get("intervention_enabled") is not True or
        manifest.get("implementation_mode") != "delegated" or
        manifest["project"] != project or manifest["native_session_id"] != session):
        raise AccessRefused("executive_intervention_not_configured")
    rows = [x for x in _rows(store, project) if x["session_id"] == session]
    item = next((x for x in rows if x["id"] == payload.get("intervention_id")), None)
    if action == "intervention_status":
        return _view(max(rows, key=lambda x: x["created_at"], default=None))
    if action == "intervention_begin":
        gateway.coordination._live()
        delegation_guard(store, project)
        if _busy(store, project):
            raise Refused("delegated_work_active")
        # `uses` repeats an identical call; each use is its own one-use permit.
        permits = [{"tool": p["tool"], "input_digest": digest(_call_input(p)),
                    "state": "available", "tool_use_id": None} | ({"background": True} if p.get("background") else {})
                   for p in payload["calls"] for _ in range(p.get("uses", 1))]
        item = {"schema_version": 1, "id": operation, "project": project, "session_id": session,
                "purpose": payload["purpose"], "created_at": now(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=payload["ttl_seconds"])).isoformat().replace("+00:00", "Z"),
                "state": "active", "permits": permits}
    elif action == "intervention_reconcile":
        gateway._operator(context)
        if item is None:
            raise Conflict("intervention_not_found")
        if _busy(store, project):
            raise Refused("delegated_work_active")
        for permit in item["permits"]:
            if permit["state"] == "admitted":
                permit["state"] = "reconciled"
        item["state"] = "closed"
        store._history("executive.intervention_reconciled", {
            "id": item["id"], "project": project, "actor": context.actor.subject,
            "observation": payload["observation"], "verification": "operator_attributed_not_process_attestation"})
    elif action == "intervention_end":
        if item is None:
            raise Conflict("intervention_not_found")
        if any(p["state"] == "admitted" for p in item["permits"]):
            raise Conflict("intervention_tool_outcome_unknown")
        item["state"] = "closed"
    elif action in {"intervention_authorize", "intervention_finish"}:
        if payload["cwd"] != manifest["repository_root"]:
            raise AccessRefused("intervention_working_directory_mismatch")
        wanted = digest(normalized(payload["tool"], payload["input"]))
        tool_use = payload["tool_use_id"]
        matches = [(x, p) for x in rows for p in x["permits"]
                   if p["tool_use_id"] == tool_use]
        if matches:
            item, permit = matches[0]
            if permit["input_digest"] != wanted:
                raise Conflict("intervention_tool_identity_changed")
            if action == "intervention_authorize":
                # A lost admission response must not authorize a second execution.
                raise Conflict("intervention_admission_already_consumed")
            if permit["state"] != "launched":
                permit["state"] = "finished"
        elif action == "intervention_finish":
            return {"recorded": False, "reason": "no_matching_admission"}
        else:
            gateway.coordination._live()
            if _busy(store, project):
                raise Refused("delegated_work_active")
            matches = [(x, p) for x in rows if _live(x) for p in x["permits"]
                       if p["state"] == "available" and p["input_digest"] == wanted]
            if not matches:
                raise AccessRefused("intervention_permit_required")
            item, permit = matches[0]
            # A background permit closes at launch: no completion is awaited.
            permit.update(state="launched" if permit.get("background") else "admitted", tool_use_id=tool_use)
        if all(p["state"] in ("finished", "launched") for p in item["permits"]):
            item["state"] = "closed"
    _save(store, item)
    store._history("executive.intervention", {"action": action, "id": item["id"],
                   "project": project, "session_id": session, "state": item["state"]})
    return _view(item)
