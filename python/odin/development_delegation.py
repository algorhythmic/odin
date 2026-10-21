"""Bind development stages to accountable local orchestration assignments.

This checks recorded routing and attributed acceptance. It does not isolate the
executive's native tools or establish that a requested child model actually ran.
"""
from .contracts import canonical, strict_loads
from .store import Conflict, digest


def initialize(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS development_delegations
        (stage_id TEXT PRIMARY KEY, loop_id TEXT NOT NULL, project TEXT NOT NULL,
         assignment_id TEXT UNIQUE NOT NULL, body TEXT NOT NULL)""")


def binding(store, stage_id):
    initialize(store)
    row = store.db.execute(
        "SELECT body FROM development_delegations WHERE stage_id=?", (stage_id,)
    ).fetchone()
    return strict_loads(row[0]) if row else None


def assign(gateway, payload, operation, actor):
    core = gateway.development_loop
    loop, stage = core._correlate_stage(
        payload["loop_id"], payload["stage_id"], payload["session_id"]
    )
    if loop["status"] != "executive_claimed" or stage["state"] != "claimed":
        raise Conflict("claim the current stage before delegating")
    if binding(gateway.store, stage["id"]):
        raise Conflict("stage already has a delegation; inspect or follow up that assignment")
    session = gateway.delegation._session(payload["orchestrator_session_id"], loop["project"])
    options = gateway.delegation._options(session["id"]) | {"harness": session["harness"]}
    profile = loop.get("delegation_profile")
    if not profile:
        raise Conflict("loop has not opted into staged delegation")
    if profile and any(options.get(key) != value for key, value in profile.items()):
        raise Conflict("orchestrator does not match the loop's requested profile")
    if session.get("native_session_id") == loop["session_id"]:
        raise Conflict("orchestrator must be a separate native session")
    arguments = {
        "session_id": session["id"],
        "objective": "Complete development stage " + stage["id"],
        "criteria": [{"id": "stage", "text": "Address the complete stage prompt; return revisions, tests, review findings and unresolved work."}],
        "scope": "Only the assigned development stage in the configured workspace.",
        "output_contract": "Concise result with exact revisions, artifact references, test results, review findings, child-agent model observations and unresolved work.",
        "instructions": (
            "Act as the project orchestrator. Delegate independent bounded implementation "
            "tasks to native subagents when available, integrate their results, test the "
            "combined change, and obtain review. Report unavailable capabilities and "
            "requested versus observed models separately. Do not weaken the objective "
            "or acceptance criteria. Stage " + stage["id"] + ":\n\n" + stage["prompt"]
        ),
        "limits": payload["limits"],
        "allow_unenforced_limits": payload.get("allow_unenforced_limits", False),
    }
    gateway.store.contracts.validate_definition(
        "executive-tool-input", "odin_delegation_assign", arguments | {"operation_id": operation}
    )
    result = gateway.delegation.assign(arguments, project=loop["project"], actor=actor, operation=operation)
    item = {"schema_version": 1, "project": loop["project"], "loop_id": loop["id"],
            "stage_id": stage["id"], "session_id": session["id"],
            "assignment_id": result["assignment"], "operation_id": operation,
            "prompt_digest": digest(stage["prompt"])}
    gateway.store.contracts.validate("development-delegation", item)
    gateway.store.db.execute("INSERT INTO development_delegations VALUES(?,?,?,?,?)", (
        stage["id"], loop["id"], loop["project"], item["assignment_id"], canonical(item)))
    gateway.store._history("development.stage_delegated", item)
    return result | {"stage_binding": item}


def require_return(store, loop, stage):
    if not loop.get("delegation_profile"):
        return None
    item = binding(store, stage["id"])
    if not item or item["loop_id"] != loop["id"] or item["prompt_digest"] != digest(stage["prompt"]):
        raise Conflict("stage requires its own delegated orchestrator return")
    assignment = store.get(item["assignment_id"])
    session = store.get(item["session_id"])
    if assignment["state"] != "completed":
        raise Conflict("review and accept the delegated assignment before ready")
    if not session.get("native_session_id") or session["native_session_id"] == loop["session_id"]:
        raise Conflict("separate native orchestrator identity has not been observed")
    rows = store.db.execute("SELECT body FROM delegation_turns WHERE assignment=? ORDER BY rowid", (assignment["id"],)).fetchall()
    turns = [strict_loads(row[0]) for row in rows]
    if (not turns or turns[-1]["state"] != "returned"
            or turns[-1].get("native_session_mismatch")
            or turns[-1]["session"] != session["id"]
            or (turns[-1].get("result") or {}).get("native_session_id") != session["native_session_id"]):
        raise Conflict("a successful observed orchestrator return is required")
    return item | {"returned_turn": turns[-1]["id"], "acceptance": "executive_attributed"}
