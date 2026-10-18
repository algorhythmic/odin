"""Three-document development proof. All execution and evidence are synthetic."""

import hashlib

from .contracts import ROOT, identifier, strict_loads
from .service import Service, fixture_record, make_effect
from .store import Conflict, digest


def staged_run(service, assignment, *, delegation="synthetic-delegation"):
    """Create fixture authority with explicit synthetic identities, then queue."""
    backend = service.backend
    try:
        backend.get(delegation)
    except KeyError:
        backend.send(
            identifier(),
            "saga:delegation.record",
            {"id": delegation, "version": 1, "revoked": False, "concurrency": 3},
        )
    request = assignment["request_id"]
    content = digest(
        {
            "assignment": assignment["id"],
            "inputs": assignment["inputs"],
            "scope": assignment["scope"],
        }
    )
    approval, review, run = identifier(), identifier(), identifier()
    backend.send(
        identifier(),
        "saga:approval.record",
        {
            "id": approval,
            "request_id": request,
            "digest": content,
            "operator": "synthetic-operator",
        },
    )
    backend.send(
        identifier(),
        "saga:review.record",
        {
            "id": review,
            "request_id": request,
            "digest": content,
            "reviewer": "synthetic-reviewer",
            "result": "APPROVE",
        },
    )
    payload = {
        "id": run,
        "request_id": request,
        "digest": content,
        "approval": approval,
        "review": review,
        "delegation": delegation,
        "delegation_version": 1,
        "criteria": ["synthetic stream check"],
    }
    commitment = service.store.get(assignment["commitment"])
    effect = make_effect(
        "saga:run.submit",
        payload,
        operation_id=request,
        assignment=assignment["id"],
        owner_generation=commitment["ownership_generation"],
        delegation_version=1,
        approval_digest=content,
    )
    service.store.enqueue(effect, payload)
    return run


def run(directory):
    manifest = strict_loads(
        (ROOT / "fixtures/three-document/manifest.json").read_text()
    )
    with Service(directory) as service:
        service.store.contracts.validate("three-document", manifest)
        if service.store.records():
            raise Conflict("demo requires a new empty state directory")
        service.recover()
        sources = []
        for doc in manifest["documents"]:
            actual = hashlib.sha256(
                (ROOT / "fixtures/three-document" / doc["path"]).read_bytes()
            ).hexdigest()
            if actual != doc["digest"]:
                raise Conflict("source document changed")
            sources.append(
                {
                    "locator": doc["path"],
                    "digest": actual,
                    "version": doc["version"],
                    "registered_at": "2026-10-16T00:00:00Z",
                }
            )
        project = fixture_record(
            "Project", name="Synthetic three-document project", sources=sources
        )
        service.store.create(project)
        session = fixture_record(
            "PlanningSession", project=project["id"], state="active"
        )
        service.store.create(session)
        criteria = [
            {"id": s["name"], "text": s["criterion"], "evidence": [], "met": False}
            for s in manifest["streams"]
        ]
        criteria.append(
            {
                "id": "integration",
                "text": manifest["integration_criterion"],
                "evidence": [],
                "met": False,
            }
        )
        commitment = fixture_record(
            "Commitment",
            project=project["id"],
            owner=session["id"],
            objective="All document streams and their integrated result pass",
            criteria=criteria,
        )
        service.store.create(commitment)
        assignments = []
        for stream in manifest["streams"]:
            source = next(
                d for d in manifest["documents"] if d["path"] == stream["input"]
            )
            assignment = fixture_record(
                "Assignment",
                commitment=commitment["id"],
                owner=session["id"],
                scope=stream["name"],
                inputs=[{"ref": source["path"], "digest": source["digest"]}],
                request_id=identifier(),
            )
            service.store.create(assignment)
            run_id = staged_run(service, assignment)
            if not assignments:
                service.backend.lose_next_receipt = True
            try:
                service.store.dispatch(service.backend)
            except TimeoutError:
                service.recover()
            service.store.update(
                assignment["id"],
                {"state": "dispatched", "run": run_id},
                assignment["rev"],
            )
            assignments.append((assignment["id"], run_id))
        # Replace the planner without erasing the open commitment or assignments.
        replacement = service.replace_fixture_session(session["id"])
        for assignment_id, run_id in assignments:
            service.backend.inject_run_state(run_id, "started")
            service.backend.inject_run_state(run_id, "terminated")
        service.reconcile_runs()
        termination_did_not_complete = all(
            a["state"] != "completed" for a in service.store.records("Assignment")
        )
        for assignment_id, run_id in assignments:
            service.backend.inject_run_state(
                run_id, "verified", [f"synthetic:stream-check:{run_id}"]
            )
        service.reconcile_runs()
        current = service.store.get(commitment["id"])
        evidence = {
            s["name"]: [f"synthetic:accepted:{s['name']}"] for s in manifest["streams"]
        }
        try:
            service.close_commitment(current["id"], current["rev"], evidence)
        except Conflict:
            integration_gate_held = True
        else:
            raise AssertionError("integration evidence was not required")
        evidence["integration"] = ["synthetic:integration-check:passed"]
        service.close_commitment(current["id"], current["rev"], evidence)
        service.store.project_history(service.directory / "history.jsonl")
        result = {
            "label": service.label,
            "documents": len(sources),
            "logical_runs": len(service.backend.resources("run")),
            "lost_receipt_reconciled": service.store.effects()[0]["state"]
            == "delivered",
            "termination_did_not_complete": termination_did_not_complete,
            "integration_gate_held": integration_gate_held,
            "replacement_preserved_commitment": service.store.get(commitment["id"])[
                "owner"
            ]
            == replacement["id"],
            "commitment_state": service.store.get(commitment["id"])["state"],
        }
        service.store.contracts.validate("demo-result", result)
        return result
