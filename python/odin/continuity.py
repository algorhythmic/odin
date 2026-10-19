"""Deterministic, local continuity projection over canonical service records.

The caller authenticates the principal and supplies its permitted project IDs.
This module checks that scope again, but is not an authentication service.
"""

from __future__ import annotations

from datetime import datetime

from .contracts import canonical, identifier, strict_loads
from .store import Conflict, digest, now


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Continuity:
    def __init__(
        self, store, memory=None, evidence_resolver=None, allow_fixture_evidence=False
    ):
        store._core()
        self.store = store
        self.memory = memory
        self.evidence_resolver = evidence_resolver
        self.allow_fixture_evidence = allow_fixture_evidence
        with store.transaction():
            store.db.execute("""CREATE TABLE IF NOT EXISTS continuity_migrations
                (module TEXT PRIMARY KEY, version INTEGER NOT NULL)""")
            row = store.db.execute(
                "SELECT version FROM continuity_migrations WHERE module='continuity'"
            ).fetchone()
            if row and row[0] not in (1, 2, 3):
                raise Conflict("unsupported continuity migration")
            if not row:
                store.db.execute("""CREATE TABLE continuity_decisions
                    (request_id TEXT PRIMARY KEY, project TEXT NOT NULL, dedupe TEXT NOT NULL,
                     body TEXT NOT NULL, UNIQUE(project,dedupe))""")
                store.db.execute("""CREATE TABLE continuity_deliveries
                    (id TEXT PRIMARY KEY, principal TEXT NOT NULL, project TEXT NOT NULL,
                     history_seq INTEGER NOT NULL, dependency_revision TEXT,
                     body TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0)""")
                store.db.execute("""CREATE TABLE continuity_ack
                    (principal TEXT NOT NULL, project TEXT NOT NULL, history_seq INTEGER NOT NULL,
                     PRIMARY KEY(principal,project))""")
                store.db.execute(
                    "INSERT INTO continuity_migrations VALUES('continuity',1)"
                )
            store.db.execute("""CREATE TABLE IF NOT EXISTS continuity_issued
                (id TEXT PRIMARY KEY, principal TEXT NOT NULL, project TEXT NOT NULL,
                 body TEXT NOT NULL)""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS continuity_evidence
                (request_id TEXT PRIMARY KEY, resolved_digest TEXT NOT NULL)""")
            store.db.execute(
                "UPDATE continuity_migrations SET version=3 WHERE module='continuity'"
            )

    def _scope(self, project, principal, permitted_projects):
        if not principal or project not in set(permitted_projects):
            raise PermissionError("project view denied")
        record = self.store.get(project)
        if record["record_type"] != "Project":
            raise Conflict("not a project")
        return record

    def _memory_revision(self, project):
        return self.memory.dependency_revision(project) if self.memory else None

    def _record_project(self, record):
        if record["record_type"] == "Project":
            return record["id"]
        if record["record_type"] == "Assignment":
            return self.store.get(record["commitment"])["project"]
        return record.get("project")

    def _project_state_digest(self, project):
        request_ids = {
            r[0]
            for r in self.store.db.execute(
                "SELECT request_id FROM continuity_decisions WHERE project=?",
                (project,),
            )
        }
        revisions = []
        for record in self.store.records():
            if self._record_project(record) == project or record["id"] in request_ids:
                revisions.append((record["id"], record["record_type"], record["rev"]))
        return digest({"records": sorted(revisions), "stopped": self.store.stopped()})

    def _resolve_evidence(self, item, principal):
        resolved = []
        for entry in [
            *(
                dict(ref=e["ref"], revision=e["revision"], expected_digest=None)
                for e in item["evidence"]
            ),
            dict(
                ref=item["artifact"]["ref"],
                revision=None,
                expected_digest=item["artifact"]["digest"],
            ),
        ]:
            ref = entry["ref"]
            if ref.startswith("record:"):
                record_id = ref.removeprefix("record:")
                if record_id in {r["id"] for r in item["commitments"]}:
                    raise Conflict(
                        "linked commitment changes during preparation; use commitment revision binding"
                    )
                record = self.store.get(record_id)
                evidence = {
                    "project": self._record_project(record),
                    "revision": str(record["rev"]),
                    "digest": digest(record),
                }
            elif self.evidence_resolver is not None:
                evidence = self.evidence_resolver(
                    ref, project=item["project"], principal=principal
                )
            elif self.allow_fixture_evidence and (
                ref.startswith("fixture:") or ref.startswith("artifact:")
            ):
                evidence = {
                    "project": item["project"],
                    "revision": entry["revision"],
                    "digest": entry["expected_digest"],
                    "synthetic": True,
                }
            else:
                raise Conflict("unresolved evidence reference")
            if (
                not isinstance(evidence, dict)
                or evidence.get("project") != item["project"]
            ):
                raise PermissionError("evidence outside project")
            if (
                evidence.get("readers") is not None
                and principal not in evidence["readers"]
            ):
                raise PermissionError("evidence reader denied")
            if (
                entry["revision"] is not None
                and str(evidence.get("revision")) != entry["revision"]
            ):
                raise Conflict("evidence revision changed")
            if (
                entry["expected_digest"] is not None
                and evidence.get("digest") != entry["expected_digest"]
            ):
                raise Conflict("artifact digest changed")
            resolved.append(
                {
                    "ref": ref,
                    "revision": evidence.get("revision"),
                    "digest": evidence.get("digest"),
                    "synthetic": bool(evidence.get("synthetic", False)),
                }
            )
        return digest(resolved)

    def _request_meta(self, request_id):
        row = self.store.db.execute(
            "SELECT project,body FROM continuity_decisions WHERE request_id=?",
            (request_id,),
        ).fetchone()
        if row is None:
            raise KeyError(request_id)
        return row[0], strict_loads(row[1])

    def prepare_decision(self, item, *, principal, permitted_projects):
        """Persist a prepared request and its canonical obligation link atomically.

        ``item`` is validated against continuity-decision. Dedupe is stable per
        project; a changed payload under one key is rejected for explicit revision.
        """
        self.store.contracts.validate("continuity-decision", item)
        project = item["project"]
        self._scope(project, principal, permitted_projects)
        if principal != item["recipient"]:
            raise PermissionError("recipient mismatch")
        with self.store.transaction():
            if self.store.stopped():
                raise Conflict("service stopped")
            if _time(item["expires_at"]) <= _time(now()):
                raise Conflict("decision request already expired")
            old = self.store.db.execute(
                "SELECT request_id,body FROM continuity_decisions WHERE project=? AND dedupe=?",
                (project, item["dedupe_key"]),
            ).fetchone()
            if old:
                if strict_loads(old[1]) != item:
                    raise Conflict("decision dedupe conflict")
                return self.store.get(old[0]) | {
                    "question": item["question"],
                    "options": item["options"],
                }
            for link in item["commitments"]:
                record = self.store.get(link["id"])
                if (
                    record["record_type"] != "Commitment"
                    or record["project"] != project
                ):
                    raise Conflict("commitment project mismatch")
                if record["rev"] != link["rev"] or record["state"] not in (
                    "open",
                    "blocked",
                ):
                    raise Conflict("stale commitment")
            if len({r["id"] for r in item["commitments"]}) != len(item["commitments"]):
                raise Conflict("duplicate commitment")
            if len({r["id"] for r in item["record_refs"]}) != len(item["record_refs"]):
                raise Conflict("duplicate evidence record")
            for ref in item["record_refs"]:
                record = self.store.get(ref["id"])
                if record["rev"] != ref["rev"]:
                    raise Conflict("stale evidence record")
                linked_project = self._record_project(record)
                if linked_project != project:
                    raise PermissionError("cross-project evidence record")
            allowed_scope = (
                {project}
                | {r["id"] for r in item["commitments"]}
                | {r["id"] for r in item["record_refs"]}
            )
            if not set(item["authorization"]["scope"]) <= allowed_scope:
                raise PermissionError(
                    "authorization scope outside bound project records"
                )
            if item["memory_revision"] != self._memory_revision(project):
                raise Conflict("stale memory dependency")
            resolved_digest = self._resolve_evidence(item, principal)
            request_id = identifier()
            timestamp = now()
            request = {
                "schema_version": 1,
                "record_type": "HumanRequest",
                "id": request_id,
                "rev": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
                "assignment": None,
                "run": None,
                "kind": item["kind"],
                "question": "Prepared decision; inspect scoped metadata",
                "options": [f"choice:{index}" for index in range(len(item["options"]))],
                "proposal_digest": digest(item["artifact"])
                if item["kind"] == "plan_approval"
                else None,
                "recipient": principal,
                "expires_at": item["expires_at"],
                "state": "open",
                "response": None,
                "channel": None,
            }
            self.store._put(request, 0)
            self.store.db.execute(
                "INSERT INTO continuity_decisions VALUES(?,?,?,?)",
                (request_id, project, item["dedupe_key"], canonical(item)),
            )
            self.store.db.execute(
                "INSERT INTO continuity_evidence VALUES(?,?)",
                (request_id, resolved_digest),
            )
            for link in item["commitments"]:
                record = self.store.get(link["id"])
                updated = record["open_decisions"] + [
                    {
                        "id": request_id,
                        "text": "Prepared decision",
                        "raised_by": principal,
                    }
                ]
                self.store.update(
                    record["id"], {"open_decisions": updated}, record["rev"]
                )
            self.store._history(
                "continuity.decision.prepared",
                {"request": request_id, "project": project},
            )
            return request | {"question": item["question"], "options": item["options"]}

    def respond_decision(
        self,
        request_id,
        *,
        response,
        expected_rev,
        evidence_digest,
        authority_revision,
        principal,
        permitted_projects,
        channel="text",
    ):
        if channel == "voice":
            raise PermissionError("voice cannot confer decision authority")
        with self.store.transaction():
            if self.store.stopped():
                raise Conflict("service stopped")
            project, meta = self._request_meta(request_id)
            self._scope(project, principal, permitted_projects)
            request = self.store.get(request_id)
            if principal != request["recipient"] or principal != meta["recipient"]:
                raise PermissionError("recipient mismatch")
            if request["rev"] != expected_rev or request["state"] not in (
                "open",
                "delivered",
            ):
                raise Conflict("stale or inactive request")
            if _time(now()) >= _time(request["expires_at"]):
                raise Conflict("request expired")
            if evidence_digest != digest(meta["evidence"]):
                raise Conflict("evidence changed")
            resolved = self.store.db.execute(
                "SELECT resolved_digest FROM continuity_evidence WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if not resolved or resolved[0] != self._resolve_evidence(meta, principal):
                raise Conflict("resolved evidence changed")
            # This is a trusted caller's current policy revision. The answer
            # remains non-authorizing even when the revision matches.
            if authority_revision != meta["authority_revision"]:
                raise Conflict("authority revision changed")
            commitment_ids = {r["id"] for r in meta["commitments"]}
            for ref in meta["record_refs"] + meta["commitments"]:
                current = self.store.get(ref["id"])
                # The preparation itself adds an open-decision link to commitments.
                allowed_rev = ref["rev"] + (1 if ref["id"] in commitment_ids else 0)
                if current["rev"] != allowed_rev:
                    raise Conflict("bound record changed")
            if meta["memory_revision"] != self._memory_revision(project):
                raise Conflict("evidence dependency changed")
            if response not in meta["options"]:
                raise Conflict("response outside prepared options")
            # An answer is an auditable response. Separate command admission
            # must validate any effect or authority grant against live policy.
            updated = self.store.update(
                request_id,
                {
                    "state": "answered",
                    "response": f"choice:{meta['options'].index(response)}",
                    "channel": channel,
                },
                request["rev"],
            )
            for link in meta["commitments"]:
                current = self.store.get(link["id"])
                remaining = [
                    d for d in current["open_decisions"] if d["id"] != request_id
                ]
                self.store.update(
                    link["id"], {"open_decisions": remaining}, current["rev"]
                )
            self.store._history(
                "continuity.decision.answered",
                {
                    "request": request_id,
                    "project": project,
                    "response_digest": digest(response),
                    "authority_revision": authority_revision,
                },
            )
            return updated

    def expire_decision(self, request_id, *, at=None):
        with self.store.transaction():
            project, _ = self._request_meta(request_id)
            request = self.store.get(request_id)
            if request["state"] not in ("open", "delivered"):
                return request
            if _time(at or now()) < _time(request["expires_at"]):
                return request
            updated = self.store.update(
                request_id, {"state": "expired"}, request["rev"]
            )
            self.store._history(
                "continuity.decision.expired",
                {"request": request_id, "project": project},
            )
            return updated

    def checkpoint(
        self, commitment_id, *, summary, evidence, recorded_by, expected_rev
    ):
        with self.store.transaction():
            record = self.store.get(commitment_id)
            if record["record_type"] != "Commitment":
                raise Conflict("checkpoint requires commitment")
            if not summary or not recorded_by:
                raise ValueError("checkpoint summary and recorder required")
            point = {
                "id": identifier(),
                "at": now(),
                "summary": summary,
                "evidence": evidence,
                "recorded_by": recorded_by,
            }
            return self.store.update(
                commitment_id,
                {
                    "checkpoints": record["checkpoints"] + [point],
                },
                expected_rev,
            )

    def resume(
        self,
        project,
        *,
        principal,
        permitted_projects,
        detail_bytes=4096,
        obligation_offset=0,
        obligation_limit=32,
        decision_offset=0,
        decision_limit=4,
        obligation_page_token=None,
    ):
        record = self._scope(project, principal, permitted_projects)
        if (
            not 0 <= detail_bytes <= 16384
            or obligation_offset < 0
            or decision_offset < 0
            or not 1 <= obligation_limit <= 32
            or not 1 <= decision_limit <= 4
        ):
            raise ValueError("invalid view budget or page")
        project_digest = self._project_state_digest(project)
        if obligation_offset:
            expected_token = digest(
                {
                    "project": project,
                    "principal": principal,
                    "offset": obligation_offset,
                    "revision": project_digest,
                }
            )
            if obligation_page_token != expected_token:
                raise Conflict("stale or missing obligation page token")
        elif obligation_page_token is not None:
            raise ValueError("page token requires nonzero offset")
        last = self.store.db.execute(
            "SELECT history_seq FROM continuity_ack WHERE principal=? AND project=?",
            (principal, project),
        ).fetchone()
        ack_seq = last[0] if last else 0
        seq = self.store.db.execute(
            "SELECT COALESCE(MAX(seq),0) FROM history"
        ).fetchone()[0]
        commitments = [
            c for c in self.store.records("Commitment") if c["project"] == project
        ]
        active = [c for c in commitments if c["state"] in ("open", "blocked")]
        assignment_ids = {c["id"] for c in active}
        all_assignments = [
            a
            for a in self.store.records("Assignment")
            if a["commitment"] in assignment_ids
        ]
        page_records = active[obligation_offset : obligation_offset + obligation_limit]
        next_offset = (
            obligation_offset + len(page_records)
            if obligation_offset + len(page_records) < len(active)
            else None
        )
        page_ids = {c["id"] for c in page_records}
        assignments = [
            {
                "id": a["id"],
                "commitment": a["commitment"],
                "state": a["state"],
                "rev": a["rev"],
            }
            for a in all_assignments
            if a["commitment"] in page_ids
        ][:100]
        page = [
            {
                "id": c["id"],
                "rev": c["rev"],
                "objective": c["objective"][:240],
                "objective_truncated": len(c["objective"]) > 240,
                "state": c["state"],
                "owner": c["owner"],
                "dependency_count": len(c["dependencies"]),
                "open_decision_count": len(c["open_decisions"]),
                "next_trigger": c["next_trigger"],
                "checkpoints": [
                    {
                        "summary": c["checkpoints"][-1]["summary"][:240],
                        "at": c["checkpoints"][-1]["at"],
                    }
                ]
                if c["checkpoints"]
                else [],
            }
            for c in page_records
        ]
        requests = []
        for row in self.store.db.execute(
            "SELECT request_id,body FROM continuity_decisions WHERE project=? ORDER BY request_id",
            (project,),
        ):
            req = self.store.get(row[0])
            if req["state"] in ("open", "delivered", "expired"):
                prepared = strict_loads(row[1])
                resolved = self.store.db.execute(
                    "SELECT resolved_digest FROM continuity_evidence WHERE request_id=?",
                    (row[0],),
                ).fetchone()
                stale = prepared.get("memory_revision") != self._memory_revision(
                    project
                )
                if not stale:
                    try:
                        stale = not resolved or resolved[0] != self._resolve_evidence(
                            prepared, principal
                        )
                    except (Conflict, PermissionError, KeyError, TypeError):
                        stale = True
                if stale:
                    req = req | {
                        "question": "Prepared decision unavailable",
                        "options": [],
                    }
                    requests.append(
                        {
                            "request": req,
                            "prepared": {
                                "unavailable": True,
                                "reason": "evidence invalidated; reissue request",
                            },
                        }
                    )
                else:
                    requests.append({"request": req, "prepared": prepared})
        actionable_requests = [
            r
            for r in requests
            if r["request"]["state"] in ("open", "delivered")
            and not r["prepared"].get("unavailable")
        ]
        unavailable_requests = any(r["prepared"].get("unavailable") for r in requests)
        changes = []
        related_count = 0
        first_omitted = None
        used = 0
        for row in self.store.db.execute(
            "SELECT seq,body FROM history WHERE seq>? AND seq<=? ORDER BY seq",
            (ack_seq, seq),
        ):
            event = strict_loads(row[1])
            payload = event["payload"]
            related = payload.get("project") == project
            if not related and event["kind"] == "record.changed":
                changed = payload["record"]
                related = (
                    changed["id"] == project
                    or changed.get("project") == project
                    or changed.get("commitment") in assignment_ids
                )
            if not related:
                continue
            related_count += 1
            entry = {"seq": row[0], "kind": event["kind"], "at": event["received_at"]}
            size = len(canonical(entry).encode())
            if used + size <= detail_bytes:
                changes.append(entry)
                used += size
            elif first_omitted is None:
                first_omitted = row[0]
        if self.memory:
            raw_memory = self.memory.snapshot(project, principal)
            memory = {
                "availability": raw_memory["availability"],
                "dependency_revision": raw_memory["dependency_revision"],
                "truncated": raw_memory["truncated"],
                "source_count": len(raw_memory["sources"]),
                "statement_count": len(raw_memory["statements"]),
                "stale_sources": [
                    f["source"] for f in raw_memory["freshness"] if f["stale"]
                ][:32],
                "coverage": [
                    {
                        "producer": c["producer"],
                        "availability": c["availability"],
                        "captured": c["captured"],
                        "processed": c["processed"],
                        "hole_count": len(c["holes"]),
                        "failure_count": len(c["failures"]),
                    }
                    for c in raw_memory["coverage"]
                ][:32],
            }
        else:
            memory = {
                "availability": "unavailable",
                "reason": "memory adapter absent",
                "dependency_revision": None,
            }
        issue_id = identifier()
        briefing = {
            "project": {
                "id": project,
                "name": record["name"][:240],
                "rev": record["rev"],
                "owner": record["interface_decision_owner"],
            },
            "principal": principal,
            "history_seq": seq,
            "acknowledged_seq": ack_seq,
            "acknowledgeable_seq": (first_omitted - 1) if first_omitted else seq,
            "issue_id": issue_id,
            "detail_bytes": detail_bytes,
            "changes": changes,
            "changes_omitted": related_count - len(changes),
            "commitments": page,
            "commitment_count": len(active),
            "next_obligation_offset": next_offset,
            "next_obligation_page_token": digest(
                {
                    "project": project,
                    "principal": principal,
                    "offset": next_offset,
                    "revision": project_digest,
                }
            )
            if next_offset is not None
            else None,
            "assignments": assignments,
            "decisions": requests[decision_offset : decision_offset + decision_limit],
            "decision_count": len(requests),
            "next_decision_offset": decision_offset + decision_limit
            if decision_offset + decision_limit < len(requests)
            else None,
            "blockers": [c["id"] for c in page if c["state"] == "blocked"],
            "next_triggers": [
                {"commitment": c["id"], "trigger": c["next_trigger"]}
                for c in page
                if c["next_trigger"]
            ],
            "memory": memory,
            "recommended_next_action": "answer a prepared decision"
            if actionable_requests
            else (
                "reissue an unavailable decision request"
                if unavailable_requests
                else "reissue an expired decision request"
                if any(r["request"]["state"] == "expired" for r in requests)
                else "resolve a blocker"
                if any(c["state"] == "blocked" for c in active)
                else "continue the first open commitment"
                if active
                else "no outstanding commitment"
            ),
        }
        if len(canonical(briefing).encode()) > 131072:
            raise Conflict("view exceeds bound; request a smaller page")
        issued = {
            "digest": digest(briefing),
            "history_seq": seq,
            "acknowledgeable_seq": briefing["acknowledgeable_seq"],
            "dependency_revision": memory.get("dependency_revision"),
            "project_state_digest": project_digest,
        }
        with self.store.transaction():
            self.store.db.execute(
                "INSERT INTO continuity_issued VALUES(?,?,?,?)",
                (issue_id, principal, project, canonical(issued)),
            )
            self.store._history("continuity.view.issued", {"issue": issue_id})
            issued["issue_seq"] = self.store.db.execute(
                "SELECT MAX(seq) FROM history"
            ).fetchone()[0]
            self.store.db.execute(
                "UPDATE continuity_issued SET body=? WHERE id=?",
                (canonical(issued), issue_id),
            )
        return briefing

    def record_delivery(
        self, briefing, *, principal, permitted_projects, delivery_id=None
    ):
        project = briefing["project"]["id"]
        self._scope(project, principal, permitted_projects)
        if briefing["principal"] != principal:
            raise PermissionError("briefing principal mismatch")
        delivery_id = delivery_id or identifier()
        existing = self.store.db.execute(
            "SELECT principal,project,body FROM continuity_deliveries WHERE id=?",
            (delivery_id,),
        ).fetchone()
        if existing:
            if (
                existing[0] != principal
                or existing[1] != project
                or strict_loads(existing[2])["briefing_digest"] != digest(briefing)
            ):
                raise Conflict("delivery identity conflict")
            return delivery_id
        issued_row = self.store.db.execute(
            "SELECT principal,project,body FROM continuity_issued WHERE id=?",
            (briefing["issue_id"],),
        ).fetchone()
        if not issued_row or issued_row[0] != principal or issued_row[1] != project:
            raise Conflict("unknown issued briefing")
        issued = strict_loads(issued_row[2])
        if (
            digest(briefing) != issued["digest"]
            or issued["dependency_revision"] != self._memory_revision(project)
            or self._project_state_digest(project) != issued["project_state_digest"]
            or self.store.stopped()
        ):
            raise Conflict("briefing invalidated before delivery")
        with self.store.transaction():
            metadata = {
                "project": project,
                "principal": principal,
                "history_seq": issued["acknowledgeable_seq"],
                "dependency_revision": briefing["memory"].get("dependency_revision"),
                "briefing_digest": digest(briefing),
            }
            self.store.db.execute(
                "INSERT INTO continuity_deliveries VALUES(?,?,?,?,?,?,0)",
                (
                    delivery_id,
                    principal,
                    project,
                    issued["acknowledgeable_seq"],
                    canonical(briefing["memory"].get("dependency_revision")),
                    canonical(metadata),
                ),
            )
            self.store._history(
                "continuity.view.delivered",
                {"delivery": delivery_id, "project": project},
            )
        return delivery_id

    def acknowledge(self, delivery_id, *, principal, permitted_projects):
        with self.store.transaction():
            row = self.store.db.execute(
                "SELECT principal,project,history_seq,body,acknowledged FROM continuity_deliveries WHERE id=?",
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            self._scope(row[1], principal, permitted_projects)
            if row[0] != principal:
                raise PermissionError("delivery owner mismatch")
            metadata = strict_loads(row[3])
            if metadata["dependency_revision"] != self._memory_revision(row[1]):
                raise Conflict("delivered memory view invalidated")
            if row[4]:
                return row[2]
            self.store.db.execute(
                "UPDATE continuity_deliveries SET acknowledged=1 WHERE id=?",
                (delivery_id,),
            )
            self.store.db.execute(
                """INSERT INTO continuity_ack VALUES(?,?,?)
                ON CONFLICT(principal,project) DO UPDATE SET history_seq=MAX(history_seq,excluded.history_seq)""",
                (principal, row[1], row[2]),
            )
            self.store._history(
                "continuity.view.acknowledged",
                {"delivery": delivery_id, "project": row[1]},
            )
            return row[2]
