"""Synthetic continuity slice through Odin's local recorded command path.

The source is an Odin memory-source fixture, not a Skald or Heimdall wire
contract. The service uses its fake Saga backend; no producer, model, live
Saga, import or deployment is exercised.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from .contracts import identifier
from .coordination import Actor
from .gateway import Gateway, GatewayContext
from .service import Service, fixture_record
from .store import Conflict, now

# Match the private local CLI's operator identity so the demo can subsequently
# be inspected with serve/evidence. This does not widen the source reader ACL.
PRINCIPAL = "local-operator"
PRODUCER = "synthetic-session-capture"
SOURCE_ID = "synthetic-interface-session"
SOURCE_REF = f"fixture:{SOURCE_ID}@2"
CHECKPOINT = (
    "Worker report captured; scope decision and independent verification remain open."
)


def _source(project, revision, content, *, source_id=SOURCE_ID, readers=None):
    timestamp = now()
    return {
        "id": source_id,
        "project": project,
        "revision": revision,
        "digest": sha256(content.encode()).hexdigest(),
        "producer": PRODUCER,
        "source_class": "worker_status",
        "locator": f"fixture:{source_id}@{revision}",
        "span": None,
        "readers": [PRINCIPAL] if readers is None else readers,
        "permissions_revision": 1,
        "event_at": timestamp,
        "effective_at": timestamp,
        "observed_at": timestamp,
        "retrieved_at": timestamp,
        "ingest_seq": revision,
        "content": content,
    }


def _command(gateway, context, action, payload):
    return gateway.submit(
        {
            "schema_version": 1,
            "operation_id": identifier(),
            "action": action,
            "payload": payload,
        },
        context=context,
    )["result"]


def _gateway(service):
    gateway = Gateway(service)

    def resolve(ref, *, project, principal):
        # This explicit fixture association is local demo wiring. It is not a
        # URI protocol or an assertion about a published producer interface.
        if ref != SOURCE_REF:
            raise Conflict("unresolved synthetic evidence reference")
        return gateway.memory.read_source(
            project,
            SOURCE_ID,
            2,
            principal=principal,
            permitted_projects=[project],
        )["source"]

    gateway.continuity.evidence_resolver = resolve
    return gateway


def _decision(gateway, project, commitment, source, key):
    return {
        "schema_version": 1,
        "project": project,
        "dedupe_key": key,
        "recipient": PRINCIPAL,
        "kind": "clarification",
        "question": "Accept the revised interface scope for the next local step?",
        "options": ["accept scope", "revise scope"],
        "recommendation": "accept scope",
        "evidence": [{"ref": SOURCE_REF, "revision": "2"}],
        "artifact": {"ref": SOURCE_REF, "digest": source["digest"]},
        "authorization": {"action": "choose interface scope", "scope": [project]},
        "blockers": ["operator scope decision", "independent verification"],
        "urgency": "routine",
        "commitments": [{"id": commitment["id"], "rev": commitment["rev"]}],
        "record_refs": [],
        "memory_revision": gateway.memory.dependency_revision(project),
        "authority_revision": "synthetic-policy-placeholder",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z"),
    }


def human_briefing(view):
    """Render the bounded machine view without reading or inferring more state."""
    project = view["project"]
    lines = [
        f"{project['name']} (project revision {project['rev']})",
        f"Open commitments: {view['commitment_count']}; pending decisions: {view['decision_count']}.",
    ]
    for commitment in view["commitments"]:
        lines.append(
            f"- {commitment['objective']} [{commitment['state']}, revision {commitment['rev']}]"
        )
        for checkpoint in commitment["checkpoints"]:
            lines.append(f"  Checkpoint: {checkpoint['summary']}")
    for decision in view["decisions"]:
        prepared = decision["prepared"]
        if prepared.get("unavailable"):
            lines.append(f"- Decision unavailable: {prepared['reason']}.")
        else:
            lines.append(f"- Decision: {prepared['question']}")
            for ref in prepared["evidence"]:
                lines.append(f"  Evidence: {ref['ref']}, revision {ref['revision']}.")
    lines.append(f"Source coverage: {view['memory']['availability']}.")
    for coverage in view["memory"].get("coverage", []):
        lines.append(
            f"- {coverage['producer']}: {coverage['availability']}; "
            f"captured {coverage['captured']}, processed {coverage['processed']}, "
            f"holes {coverage['hole_count']}, failures {coverage['failure_count']}."
        )
    lines.append(
        f"Changes since acknowledgement {view['acknowledged_seq']}: "
        f"{len(view['changes'])} shown, {view['changes_omitted']} omitted."
    )
    lines.append(f"Next action: {view['recommended_next_action']}.")
    return "\n".join(lines)


def _stage(view):
    return {
        "coverage": view["memory"],
        "commitments": [
            {"id": item["id"], "rev": item["rev"], "state": item["state"]}
            for item in view["commitments"]
        ],
        "unavailable_decisions": [
            item["request"]["id"]
            for item in view["decisions"]
            if item["prepared"].get("unavailable")
        ],
        "acknowledged_seq": view["acknowledged_seq"],
    }


def run(directory=None):
    """Build and restart a fresh local synthetic slice; return reviewable evidence."""
    temporary = tempfile.TemporaryDirectory() if directory is None else None
    path = Path(temporary.name if temporary else directory)
    try:
        with Service(path) as service:
            if service.store.records():
                raise Conflict("integration demo requires an empty state directory")
            project = fixture_record("Project", name="Synthetic interface project")
            other = fixture_record("Project", name="Synthetic unrelated project")
            session = fixture_record(
                "PlanningSession", project=project["id"], state="active"
            )
            commitment = fixture_record(
                "Commitment",
                project=project["id"],
                objective="Deliver the revised local interface",
                criteria=[
                    {
                        "id": "interface-verified",
                        "text": "Independently verify the accepted interface revision",
                        "evidence": [],
                        "met": False,
                    }
                ],
            )
            private = fixture_record(
                "Commitment", project=other["id"], objective="Unrelated private work"
            )
            for record in (project, other, session, commitment, private):
                service.store.create(record)
            context = GatewayContext(
                "terminal", Actor("operator", PRINCIPAL), (project["id"],)
            )
            gateway = _gateway(service)
            memory = gateway.memory
            view_request = {
                "project": project["id"],
                "detail_bytes": 500,
                "obligation_limit": 1,
                "decision_limit": 2,
            }
            first_source = _source(
                project["id"], 1, "Synthetic worker opened the interface work."
            )
            memory.add_source(first_source)
            unknown = _command(gateway, context, "resume", view_request)
            memory.processing(
                project["id"], PRODUCER, processed=1, availability="available"
            )
            changed_source = _source(
                project["id"],
                2,
                "Synthetic worker reports local tests passed for fixture:interface@2. "
                "Scope approval and independent verification remain outstanding.",
            )
            memory.add_source(changed_source)
            report = {
                "id": "synthetic-interface-report",
                "project": project["id"],
                "kind": "report",
                "status": "reported",
                "text": changed_source["content"],
                "speaker": "synthetic-worker",
                "source_refs": [{"id": SOURCE_ID, "revision": 2, "span": None}],
                "statement_refs": [],
                "recorded_at": now(),
                "effective_from": changed_source["effective_at"],
                "effective_to": None,
                "authority_ref": None,
                "extraction_config": "explicit-synthetic-attribution-v1",
            }
            memory.add_statement(report)
            memory.processing(
                project["id"], PRODUCER, processed=2, availability="available"
            )
            memory.add_source(
                _source(
                    other["id"],
                    1,
                    "Unrelated private synthetic evidence.",
                    source_id="synthetic-private-session",
                    readers=["other-operator"],
                )
            )
            gateway.continuity.checkpoint(
                commitment["id"],
                summary=CHECKPOINT,
                evidence=[SOURCE_REF],
                recorded_by=session["id"],
                expected_rev=commitment["rev"],
            )
            commitment = service.store.get(commitment["id"])
            service.store.update(
                commitment["id"], {"state": "blocked"}, commitment["rev"]
            )
            commitment = service.store.get(commitment["id"])
            request = _command(
                gateway,
                context,
                "prepare_decision",
                {
                    "decision": _decision(
                        gateway, project["id"], commitment, changed_source, "scope:1"
                    )
                },
            )
            before_outage = _command(gateway, context, "resume", view_request)
            memory.processing(
                project["id"],
                PRODUCER,
                availability="unavailable",
                reason="synthetic collector disconnected",
            )
            outage = _command(gateway, context, "resume", view_request)
            memory.processing(project["id"], PRODUCER, availability="available")
            recovered = _command(gateway, context, "resume", view_request)
            # Recovery does not silently revive a decision prepared against an
            # earlier memory revision. Prepare a new, current request explicitly.
            commitment = service.store.get(commitment["id"])
            current_request = _command(
                gateway,
                context,
                "prepare_decision",
                {
                    "decision": _decision(
                        gateway, project["id"], commitment, changed_source, "scope:2"
                    )
                },
            )
            delivered_view = _command(gateway, context, "resume", view_request)
            delivery = _command(
                gateway, context, "view_delivery", {"briefing": delivered_view}
            )

        # Delivery was recorded, but no acknowledgement was sent before restart.
        with Service(path) as service:
            gateway = _gateway(service)
            view = _command(gateway, context, "resume", view_request)
            exact = _command(
                gateway,
                context,
                "memory_source_read",
                {"project": project["id"], "source_id": SOURCE_ID, "revision": 2},
            )
            historical = _command(
                gateway,
                context,
                "memory_source_read",
                {"project": project["id"], "source_id": SOURCE_ID, "revision": 1},
            )
            snapshot = _command(
                gateway,
                context,
                "memory_snapshot",
                {"project": project["id"], "limit": 2, "max_bytes": 4096},
            )
            denials = {}
            for label, action, payload in (
                ("foreign_project", "resume", {"project": other["id"]}),
                (
                    "foreign_evidence",
                    "memory_source_read",
                    {
                        "project": project["id"],
                        "source_id": "synthetic-private-session",
                        "revision": 1,
                    },
                ),
            ):
                try:
                    _command(gateway, context, action, payload)
                except (PermissionError, Conflict):
                    denials[label] = True
                else:
                    raise AssertionError(f"synthetic scope check failed: {label}")
            persisted = service.store.get(commitment["id"])
            return {
                "evidence_label": "synthetic local integration; fake-backend evidence; no live feeds or model",
                "source_change": {
                    "id": SOURCE_ID,
                    "from_revision": 1,
                    "to_revision": 2,
                },
                "stages": {
                    "unknown": _stage(unknown),
                    "available": _stage(before_outage),
                    "outage": _stage(outage),
                    "recovered": _stage(recovered),
                    "restarted": _stage(view),
                },
                "machine_view": view,
                "human_briefing": human_briefing(view),
                "attributed_memory": snapshot,
                "exact_evidence": exact,
                "historical_evidence": historical,
                "invalidated_decision_id": request["id"],
                "current_decision_id": current_request["id"],
                "delivery": delivery,
                "scope_denials": denials,
                "commitment_criteria": persisted["criteria"],
            }
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
