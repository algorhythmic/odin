"""Executive restart and runtime deploy requests and their outcomes (ODIN-ADR-039).

The executive asks; the operator's supervisor (``executive-supervise``) acts.
The service only records a request, refuses it with a fixed code when it would
be unsafe or is not allowed, and records the supervisor's reported transitions
and outcome. Nothing here stops, starts or signals a process or touches a
deploy copy. A request is a record, not authority: the supervisor rechecks
before it acts. While a deploy is open before the service restart, the
service drains: queued delegated turns and evaluator jobs stay queued.
"""
import sqlite3
import subprocess
from datetime import datetime, timedelta

from .contracts import canonical, identifier, strict_loads
from .store import AccessRefused, Conflict, Refused, now

ACTIONS = {"executive_restart_request", "executive_restart_status", "executive_restart_transition",
           "executive_supervisor_event", "runtime_deploy_request", "runtime_deploy_transition"}
EXECUTIVE_ACTIONS = {"executive_restart_request", "executive_restart_status", "runtime_deploy_request"}
# Requests that still need the supervisor: one at a time per project.
OPEN = ("pending", "stopping", "relaunching")
FINAL = ("restarted", "failed", "refused", "cancelled")
# The only transitions the supervisor (operator path) may record.
TRANSITIONS = {
    "pending": {"stopping", "refused", "cancelled"},
    "stopping": {"relaunching", "failed"},
    "relaunching": {"restarted", "failed"},
}
DEPLOY_OPEN = ("pending", "draining", "deploying", "restarting_executive")
DEPLOY_FINAL = ("deployed", "rolled_back", "failed", "refused", "cancelled")
DEPLOY_TRANSITIONS = {
    "pending": {"draining", "refused", "cancelled"},
    "draining": {"deploying", "failed", "cancelled"},
    "deploying": {"restarting_executive", "failed"},
    "restarting_executive": {"deployed", "rolled_back", "failed"},
}
# Until the service is restarted on the new revision it launches nothing new.
DRAIN_STATES = ("pending", "draining", "deploying")
RUNNING_TURN_STATES = ("launching", "running", "interrupting")
# Loop statuses in which the executive holds a development stage.
HELD_STAGE_STATUSES = ("executive_claimed", "executive_ready")
DEPLOY_NOTICE_HEADER = ("Odin runtime deploy notice {notice_id} (informational; acknowledge with "
                        "odin_loop_ack; it grants no authority): ")
NOTICE_HEADER = ("Odin executive restart notice {notice_id} (informational; acknowledge with "
                 "odin_loop_ack; it grants no authority): ")


def initialize(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS executive_restarts
        (id TEXT PRIMARY KEY, project TEXT NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL)""")
    store.db.execute("""CREATE TABLE IF NOT EXISTS executive_deploys
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
    initialize(store)
    deploy = item["kind"] == "deploy"
    store.contracts.validate("executive-deploy" if deploy else "executive-restart", item)
    table = "executive_deploys" if deploy else "executive_restarts"
    store.db.execute(
        f"INSERT INTO {table} VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
        "state=excluded.state, body=excluded.body",
        (item["id"], item["project"], item["state"], canonical(item)))


def _deploys(store, project=None, states=None):
    initialize(store)
    query, arguments = "SELECT body FROM executive_deploys WHERE 1=1", []
    if project is not None:
        query += " AND project=?"
        arguments.append(project)
    if states:
        query += " AND state IN ({})".format(",".join("?" * len(states)))
        arguments.extend(states)
    return [strict_loads(row[0]) for row in store.db.execute(query + " ORDER BY rowid", arguments)]


def _expired(item, at=None):
    """A pending or draining deploy past its drain deadline no longer drains."""
    return (item["state"] in ("pending", "draining") and
            datetime.fromisoformat(at or now()) >= datetime.fromisoformat(item["drain_deadline"]))


def draining(store):
    """True while a deploy is open before its service restart (item 6).

    A pending or draining deploy stops draining at its deadline even when no
    supervisor is running, so queued work is never held indefinitely.
    """
    try:
        rows = store.db.execute(
            "SELECT body FROM executive_deploys WHERE state IN ({})".format(
                ",".join("?" * len(DRAIN_STATES))), DRAIN_STATES).fetchall()
    except sqlite3.OperationalError as error:
        if "no such table" not in str(error):
            raise
        return False
    stamp = now()
    return any(not _expired(strict_loads(row[0]), stamp) for row in rows)


def expire(store, project):
    """Record drain_timeout for deploys past their deadline; returns their ids."""
    expired = []
    for item in _deploys(store, project, ("pending", "draining")):
        if _expired(item):
            item = item | {"state": "failed", "code": "drain_timeout", "updated_at": now()}
            _save(store, item)
            store._history("executive.deploy_failed", {"id": item["id"], "project": project,
                                                        "code": "drain_timeout", "timings": item["timings"],
                                                        "actor": "service"})
            _notice(store, item)
            expired.append(item["id"])
    return expired


def _ids(store, query, arguments=()):
    try:
        return [row[0] for row in store.db.execute(query, arguments).fetchall()]
    except sqlite3.OperationalError as error:
        if "no such table" not in str(error):
            raise
        return []


def drain_view(store, project):
    """What a drain waits for: work already running. Queued work stays queued."""
    from .executive_intervention import _live
    from .executive_intervention import _rows as interventions

    marks = ",".join("?" * len(RUNNING_TURN_STATES))
    turns = _ids(store, f"SELECT id FROM delegation_turns WHERE state IN ({marks}) ORDER BY id",
                 RUNNING_TURN_STATES)
    queued = len(_ids(store, "SELECT id FROM delegation_turns WHERE state='queued'"))
    jobs = [strict_loads(body)["id"] for body in _ids(
        store, "SELECT body FROM development_loop_jobs ORDER BY rowid")
        if strict_loads(body)["state"] in ("running", "unknown")]
    stages = [strict_loads(body)["id"] for body in _ids(
        store, "SELECT body FROM development_loop_stages ORDER BY rowid")
        if strict_loads(body)["state"] == "claimed"]
    live = [item["id"] for item in interventions(store, project)
            if _live(item) or any(p["state"] == "admitted" for p in item["permits"])]
    waiting = {"delegated_turns": turns[:32], "evaluator_jobs": jobs[:32],
               "live_interventions": live[:32], "claimed_loop_stages": stages[:32]}
    return {"active": draining(store), "waiting_for": waiting,
            "drained": not any(waiting.values()), "queued_turns_held": queued}


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
        "schema_version": 1, "id": identifier(),
        "kind": "runtime_deploy" if item["kind"] == "deploy" else "executive_restart",
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
    if value["kind"] == "runtime_deploy":
        return _render_deploy(store, value)
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


def _render_deploy(store, value):
    item = next((row for row in _deploys(store, value["project"]) if row["id"] == value["request_id"]), None)
    text = DEPLOY_NOTICE_HEADER.format(notice_id=value["id"])
    head = item["requested_head"] if item else "unknown"
    previous = (item or {}).get("previous_revision") or "none"
    if value["outcome"] == "deployed":
        text += (f"{head} is deployed: the service runs it, and this executive was restarted on it "
                 f"(previous revision {previous}).")
    elif value["outcome"] == "rolled_back":
        text += (f"deploying {head} failed its health check ({value['code']}); current and the "
                 f"service were switched back to {previous} and the executive restarted on it.")
    elif value["outcome"] == "refused":
        text += f"the deploy of {head} was refused ({value['code']}); nothing was changed."
    elif value["outcome"] == "cancelled":
        text += f"the deploy of {head} was cancelled; nothing was changed."
    else:
        text += f"the deploy of {head} failed ({value['code'] or 'unknown'}); see the deploy record."
    if item is not None and item.get("timings"):
        text += " Timings (s): " + ", ".join(f"{k}={v:g}" for k, v in sorted(item["timings"].items())) + "."
    return text


def _deploy_view(item):
    return {key: item.get(key) for key in (
        "id", "kind", "project", "session_id", "requested_head", "previous_revision", "state",
        "drain_deadline",
        "code", "requested_at", "updated_at", "timings", "activation_id", "rollback_activation_id",
        "pending_outcome", "clean_exit_observed", "exit_code")}


def _integration_problem(config, head):
    """The fixed code refusing ``head``, or None when it is the clean integration head."""
    from .service_activation import _checkout, _git

    try:
        tip = _git(config["repository"], "rev-parse", "--verify", "--quiet",
                   "refs/heads/" + config["branch"]).strip()
    except (OSError, subprocess.SubprocessError):
        return "deploy_checkout_unreadable"
    if tip != head:
        return "deploy_head_not_integration_head"
    problem = _checkout(config["repository"], branch=config["branch"], head=head)
    return {None: None, "checkout_not_clean": "deploy_tree_dirty",
            "checkout_wrong_branch": "deploy_checkout_not_on_integration_branch",
            "checkout_wrong_head": "deploy_head_not_integration_head"}.get(
                problem, "deploy_checkout_unreadable")


def _view(item):
    return {key: item.get(key) for key in (
        "id", "kind", "project", "session_id", "reason", "state", "code", "requested_at",
        "updated_at", "timings", "clean_exit_observed", "exit_code")}


def status(store, project, limit=8, *, state=None):
    rows = _rows(store, project)
    deploys = _deploys(store, project)
    config = None
    if state is not None:
        from .deploy_copies import read_config

        config = read_config(state)
    return {"requests": [_view(item) for item in rows[-limit:]],
            "open": [_view(item) for item in rows if item["state"] in OPEN],
            "unsafe_reason": unsafe_reason(store, project),
            "deploys": [_deploy_view(item) for item in deploys[-limit:]],
            "open_deploys": [_deploy_view(item) for item in deploys if item["state"] in DEPLOY_OPEN],
            "drain": drain_view(store, project),
            "deploy_config": config}


def dispatch(gateway, action, payload, context, operation):
    store = gateway.store
    store.contracts.validate_definition("executive-restart-command", action, payload)
    project = payload["project"]
    gateway.coordination._project(project)
    if action == "executive_restart_status":
        return status(store, project, state=gateway.service.directory)
    if action == "runtime_deploy_request":
        expire(store, project)
        return _request_deploy(gateway, payload, operation)
    if action == "executive_restart_request":
        from .executive_runtime import _load

        manifest, _ = _load(gateway.service.directory)
        if manifest["project"] != project or manifest["native_session_id"] != payload["session_id"]:
            raise AccessRefused("restart_session_not_current")
        if _rows(store, project, OPEN):
            raise Refused("restart_request_pending")
        if _deploys(store, project, DEPLOY_OPEN):
            raise Refused("deploy_request_pending")
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
    deploy = action == "runtime_deploy_transition"
    if deploy:
        expire(store, project)
    # The operator's supervisor reports progress.
    rows = _deploys(store, project) if deploy else _rows(store, project)
    item = next((row for row in rows if row["id"] == payload["request_id"]), None)
    if item is None:
        raise Refused("deploy_request_not_found" if deploy else "restart_request_not_found")
    view = _deploy_view if deploy else _view
    target = payload["state"]
    if target == item["state"]:
        return {"request": view(item), "unchanged": True}
    if target not in (DEPLOY_TRANSITIONS if deploy else TRANSITIONS).get(item["state"], ()):
        raise Refused("deploy_transition_invalid" if deploy else "restart_transition_invalid")
    if target in ("stopping", "draining", "deploying"):
        reason = unsafe_reason(store, project)
        if deploy and reason is None and target == "deploying":
            from .deploy_copies import read_config

            config = read_config(gateway.service.directory)
            reason = ("deploy_not_configured" if config is None
                      else _integration_problem(config, item["requested_head"]))
        if reason:
            # Acting now would be unsafe or no longer allowed: refuse, never wait silently.
            target = ("refused" if item["state"] == "pending" else "failed")
            payload = payload | {"code": reason}
    item = item | {"state": target, "updated_at": now()}
    for key in ("code", "clean_exit_observed", "exit_code", "activation_id",
                "rollback_activation_id", "pending_outcome"):
        if key in payload and (deploy or key in ("code", "clean_exit_observed", "exit_code")):
            item[key] = payload[key]
    if "timings" in payload:
        item["timings"] = item["timings"] | payload["timings"]
    _save(store, item)
    store._history(f"executive.{'deploy' if deploy else 'restart'}_{target}", {
        "id": item["id"], "project": project, "code": item.get("code"),
        "timings": item["timings"], "actor": context.actor.subject})
    if target in (DEPLOY_FINAL if deploy else FINAL):
        _notice(store, item)
    return {"request": view(item)}


def _request_deploy(gateway, payload, operation):
    """Item 5: record a deploy of the current, clean integration head, or refuse."""
    from .deploy_copies import DeployError, current_revision, read_config
    from .executive_runtime import _load
    from .service_activation import service_revision

    store, project, head = gateway.store, payload["project"], payload["head"]
    manifest, _ = _load(gateway.service.directory)
    if manifest["project"] != project or manifest["native_session_id"] != payload["session_id"]:
        raise AccessRefused("restart_session_not_current")
    config = read_config(gateway.service.directory)
    if config is None:
        raise AccessRefused("deploy_not_configured")
    if _deploys(store, project, DEPLOY_OPEN):
        raise Refused("deploy_request_pending")
    if _rows(store, project, OPEN):
        raise Refused("restart_request_pending")
    reason = unsafe_reason(store, project) or _integration_problem(config, head)
    if reason:
        raise Refused(reason)
    try:
        previous = current_revision(config["deploy_root"])
    except (DeployError, OSError):
        previous = None
    if previous is None:
        reported = service_revision(gateway.service.directory)
        previous = reported["revision"] if reported else None
    if previous == head:
        raise Refused("deploy_head_already_current")
    stamp = now()
    deadline = (datetime.fromisoformat(stamp) + timedelta(seconds=config["drain_timeout_seconds"]))
    item = {"schema_version": 1, "id": operation, "kind": "deploy", "project": project,
            "drain_deadline": deadline.isoformat().replace("+00:00", "Z"),
            "session_id": payload["session_id"], "requested_head": head,
            "previous_revision": previous, "requested_at": stamp, "updated_at": stamp,
            "state": "pending", "code": None, "timings": {}, "activation_id": None,
            "rollback_activation_id": None, "pending_outcome": None,
            "clean_exit_observed": None, "exit_code": None}
    _save(store, item)
    store._history("executive.deploy_requested", {
        "id": item["id"], "project": project, "requested_head": head, "previous_revision": previous})
    return {"request": _deploy_view(item), "supervisor": (
        "Recorded only; draining has begun: queued delegated turns and evaluator jobs stay queued, "
        "running ones finish. The operator's executive-supervise process deploys at the next idle "
        "turn end, restarts the service and then this executive, and a notice reports the outcome. "
        "Without a running supervisor nothing is deployed; the drain ends when the request does. "
        "End your turn now.")}
