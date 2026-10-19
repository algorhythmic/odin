"""Synthetic two-project continuity demonstration; no live integration."""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .continuity import Continuity
from .service import fixture_record
from .store import Store


def _future():
    return (
        (datetime.now(timezone.utc) + timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z")
    )


def run(directory=None):
    temporary = tempfile.TemporaryDirectory() if directory is None else None
    path = Path(temporary.name if temporary else directory)
    try:
        with Store(path) as store:
            continuity = Continuity(store, allow_fixture_evidence=True)
            project = fixture_record("Project", name="Atlas")
            other = fixture_record("Project", name="Atlas Archive")
            obligation = fixture_record(
                "Commitment",
                project=project["id"],
                objective="Deliver the revised interface",
            )
            private = fixture_record(
                "Commitment", project=other["id"], objective="Unrelated private work"
            )
            for record in (project, other, obligation, private):
                store.create(record)
            store.update(
                obligation["id"],
                {
                    "objective": "Deliver the changed interface requirement",
                    "state": "blocked",
                },
                obligation["rev"],
            )
            obligation = store.get(obligation["id"])
            continuity.checkpoint(
                obligation["id"],
                summary="Work interrupted before review",
                evidence=["fixture:working-tree"],
                recorded_by=project["id"],
                expected_rev=obligation["rev"],
            )
            obligation = store.get(obligation["id"])
            prepared = {
                "schema_version": 1,
                "project": project["id"],
                "dedupe_key": "review:1",
                "recipient": "operator-1",
                "kind": "clarification",
                "question": "Accept the changed interface requirement?",
                "options": ["accept", "revise"],
                "recommendation": "accept",
                "evidence": [{"ref": "fixture:requirements", "revision": "2"}],
                "artifact": {"ref": "fixture:proposed-diff", "digest": "a" * 64},
                "authorization": {
                    "action": "accept requirement",
                    "scope": [project["id"]],
                },
                "blockers": ["operator decision"],
                "urgency": "soon",
                "commitments": [{"id": obligation["id"], "rev": obligation["rev"]}],
                "record_refs": [],
                "memory_revision": None,
                "authority_revision": "fixture-policy:1",
                "expires_at": _future(),
            }
            request = continuity.prepare_decision(
                prepared, principal="operator-1", permitted_projects=[project["id"]]
            )
            first = continuity.resume(
                project["id"],
                principal="operator-1",
                permitted_projects=[project["id"]],
                detail_bytes=300,
            )
            delivery = continuity.record_delivery(
                first, principal="operator-1", permitted_projects=[project["id"]]
            )
        # Deliberately omit acknowledgement and restart the service writer.
        with Store(path) as store:
            continuity = Continuity(store, allow_fixture_evidence=True)
            briefing = continuity.resume(
                project["id"],
                principal="operator-1",
                permitted_projects=[project["id"]],
                detail_bytes=300,
            )
            return {
                "evidence_label": "synthetic local continuity; memory integration unavailable",
                "project": briefing["project"],
                "objective": briefing["commitments"][0]["objective"],
                "checkpoint": briefing["commitments"][0]["checkpoints"][-1]["summary"],
                "decision": {
                    "id": request["id"],
                    "question": briefing["decisions"][0]["prepared"]["question"],
                    "authorization": briefing["decisions"][0]["prepared"][
                        "authorization"
                    ],
                },
                "integration": briefing["memory"],
                "unacknowledged_changes": len(briefing["changes"])
                + briefing["changes_omitted"],
                "delivery_id": delivery,
                "visible_commitment_ids": [c["id"] for c in briefing["commitments"]],
                "other_project_excluded": private["id"]
                not in [c["id"] for c in briefing["commitments"]],
            }
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
