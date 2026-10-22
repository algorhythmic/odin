"""Executive restart requests and their outcomes (ODIN-ADR-039).

The executive asks; the operator's supervisor (``executive-supervise``) acts.
The service only records a request, refuses it with a fixed code when a
restart would be unsafe, and records the supervisor's reported transitions and
outcome. Nothing here stops, starts or signals a process. A request is a record,
not authority: the supervisor rechecks safety before it stops the executive.
"""
import sqlite3

from .contracts import canonical, identifier, strict_loads
from .store import AccessRefused, Conflict, Refused, now

ACTIONS = {"executive_restart_request", "executive_restart_status", "executive_restart_transition",
           "executive_supervisor_event"}
EXECUTIVE_ACTIONS = {"executive_restart_request", "executive_restart_status"}
# Requests that still need the supervisor: one at a time per project.
OPEN = ("pending", "stopping", "relaunching")
FINAL = ("restarted", "failed", "refused", "cancelled")
# The only transitions the supervisor (operator path) may record.
TRANSITIONS = {
    "pending": {"stopping", "refused", "cancelled"},
    "stopping": {"relaunching", "failed"},
    "relaunching": {"restarted", "failed"},
}
# Loop statuses in which the executive holds a development stage.
HELD_STAGE_STATUSES = ("executive_claimed", "executive_ready")
NOTICE_HEADER = ("Odin executive restart notice {notice_id} (informational; acknowledge with "
                 "odin_loop_ack; it grants no authority): ")


def initialize(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS executive_restarts
        (id TEXT PRIMARY KEY, project TEXT NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL)""")
    store.db.execute("""CREATE TABLE IF NOT EXISTS executive_supervision_notices
        (id TEXT PRIMARY KEY, project TEXT NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL)""")


def _rows(store, project, states=None):
    initialize(store)
    query = "SELECT body FROM executive_restarts WHERE project=?"
    arguments = [project]
    if states:
        query += " AND state IN ({})".format(",".join("?" * len(states)))
        arguments.extend(states)
    return [strict_loads(row[0]) for row in store.db.execute(query + " ORDER BY rowid", arguments)]


def _save(store, item):
    store.contracts.validate("executive-restart", item)
    store.db.execute(
        "INSERT INTO executive_restarts VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
        "state=excluded.state, body=excluded.body",
        (item["id"], item["project"], item["state"], canonical(item)))


def unsafe_reason(store, project):
    """The fixed code that makes a restart unsafe now, or None.

    An admitted intervention permit with no observed completion has an unknown
    outcome, and a claimed or ready loop stage is executive work in progress.
    Delegated turns belong to the service, not the executive, and do not block.
    """
    from .executive_intervention import _rows as interventions

    if any(permit["state"] == "admitted" for item in interventions(store, project)
           for permit in item["permits"]):
        return "intervention_outcome_unknown"
    try:
        rows = store.db.execute(
            "SELECT body FROM development_loops WHERE project=? AND active=1", (project,)).fetchall()
    except sqlite3.OperationalError as error:
        # Only a missing table means no loop stage; anything else fails closed.
        if "no such table" not in str(error):
            raise
        rows = []
    if any(strict_loads(row[0])["status"] in HELD_STAGE_STATUSES for row in rows):
        return "loop_stage_active"
    return None


def _notice(store, item):
    notice = {
        "schema_version": 1, "id": identifier(), "kind": "executive_restart",
        "project": item["project"], "request_id": item["id"], "outcome": item["state"],
        "code": item.get("code"), "created_at": now(), "state": "pending",
        "first_offered_at": None, "acknowledged_at": None, "acknowledged_by": None,
    }
    store.contracts.validate("executive-supervision-notice", notice)
    store.db.execute("INSERT INTO executive_supervision_notices VALUES(?,?,?,?)",
                     (notice["id"], notice["project"], "pending", canonical(notice)))
    return notice["id"]


def notice(store, notice_id):
    initialize(store)
    row = store.db.execute("SELECT body FROM executive_supervision_notices WHERE id=?",
                           (notice_id,)).fetchone()
    return strict_loads(row[0]) if row else None


def _save_notice(store, value):
    store.db.execute("UPDATE executive_supervision_notices SET state=?, body=? WHERE id=?",
                     (value["state"], canonical(value), value["id"]))


def pending_notices(store, project, limit=4):
    initialize(store)
    rows = store.db.execute(
        "SELECT body FROM executive_supervision_notices WHERE project=? AND state='pending' "
        "ORDER BY rowid LIMIT ?", (project, limit))
    return [strict_loads(row[0]) for row in rows]


def mark_offered(store, notice_ids):
    stamp = now()
    for notice_id in notice_ids:
        value = notice(store, notice_id)
        if value and value["first_offered_at"] is None:
            _save_notice(store, value | {"first_offered_at": stamp})


def acknowledge(store, notice_id, project, *, actor):
    """Model-attributed acknowledgement: stops re-delivery and grants nothing."""
    value = notice(store, notice_id)
    if value is None or value["project"] != project:
        raise Conflict("notice belongs to another project")
    if value["state"] == "pending":
        value = value | {"state": "acknowledged", "acknowledged_at": now(), "acknowledged_by": actor}
        _save_notice(store, value)
        store._history("executive.supervision_notice_acknowledged",
                       {"notice_id": notice_id, "actor": actor})
    return {"notice": {key: value[key] for key in ("id", "kind", "outcome", "state", "acknowledged_at")}}


def render_notice(store, value):
    item = next((row for row in _rows(store, value["project"]) if row["id"] == value["request_id"]), None)
    text = NOTICE_HEADER.format(notice_id=value["id"])
    if value["outcome"] == "restarted":
        text += "the executive was restarted by the supervisor and resumed this native session."
    elif value["outcome"] == "refused":
        text += f"the restart request was refused at stop time ({value['code']}); nothing was stopped."
    elif value["outcome"] == "cancelled":
        text += "the restart request was cancelled; nothing was stopped."
    else:
        text += f"the restart failed ({value['code'] or 'unknown'})."
    if item is not None:
        text += f" Request {item['id']}, reason: {item['reason']}."
        timings = item.get("timings") or {}
        if timings:
            text += " Timings (s): " + ", ".join(f"{k}={v:g}" for k, v in sorted(timings.items())) + "."
    return text


def _view(item):
    return {key: item.get(key) for key in (
        "id", "kind", "project", "session_id", "reason", "state", "code", "requested_at",
        "updated_at", "timings", "clean_exit_observed", "exit_code")}


def status(store, project, limit=8):
    rows = _rows(store, project)
    return {"requests": [_view(item) for item in rows[-limit:]],
            "open": [_view(item) for item in rows if item["state"] in OPEN],
            "unsafe_reason": unsafe_reason(store, project)}


def dispatch(gateway, action, payload, context, operation):
    store = gateway.store
    store.contracts.validate_definition("executive-restart-command", action, payload)
    project = payload["project"]
    gateway.coordination._project(project)
    if action == "executive_restart_status":
        return status(store, project)
    if action == "executive_restart_request":
        from .executive_runtime import _load

        manifest, _ = _load(gateway.service.directory)
        if manifest["project"] != project or manifest["native_session_id"] != payload["session_id"]:
            raise AccessRefused("restart_session_not_current")
        if _rows(store, project, OPEN):
            raise Refused("restart_request_pending")
        reason = unsafe_reason(store, project)
        if reason:
            raise Refused(reason)
        stamp = now()
        item = {"schema_version": 1, "id": operation, "kind": "restart", "project": project,
                "session_id": payload["session_id"], "reason": payload["reason"],
                "requested_at": stamp, "updated_at": stamp, "state": "pending", "code": None,
                "timings": {}, "clean_exit_observed": None, "exit_code": None}
        _save(store, item)
        store._history("executive.restart_requested", {
            "id": item["id"], "project": project, "session_id": item["session_id"]})
        return {"request": _view(item), "supervisor": (
            "Recorded only. The operator's executive-supervise process stops this session at "
            "the next idle turn end and resumes it; without a running supervisor nothing happens. "
            "Do not start new work you cannot leave at a turn end.")}
    gateway._operator(context)
    if action == "executive_supervisor_event":
        # A supervisor observation (start, end, crash, waiting for the operator).
        fields = {key: payload[key] for key in ("exit_code", "code") if key in payload}
        store._history(f"executive.supervisor_{payload['kind']}", {
            "project": project, "actor": context.actor.subject} | fields)
        return {"recorded": payload["kind"]}
    # executive_restart_transition: the operator's supervisor reports progress.
    item = next((row for row in _rows(store, project) if row["id"] == payload["request_id"]), None)
    if item is None:
        raise Refused("restart_request_not_found")
    target = payload["state"]
    if target == item["state"]:
        return {"request": _view(item), "unchanged": True}
    if target not in TRANSITIONS.get(item["state"], ()):
        raise Refused("restart_transition_invalid")
    if target == "stopping":
        reason = unsafe_reason(store, project)
        if reason:
            # Stopping now would be unsafe: refuse the request, never wait silently.
            target, payload = "refused", payload | {"code": reason}
    item = item | {"state": target, "updated_at": now()}
    for key in ("code", "clean_exit_observed", "exit_code"):
        if key in payload:
            item[key] = payload[key]
    if "timings" in payload:
        item["timings"] = item["timings"] | payload["timings"]
    _save(store, item)
    store._history(f"executive.restart_{target}", {
        "id": item["id"], "project": project, "code": item.get("code"),
        "timings": item["timings"], "actor": context.actor.subject})
    if target in FINAL:
        _notice(store, item)
    return {"request": _view(item)}
