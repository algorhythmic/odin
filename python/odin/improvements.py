"""Reviewed local correction proposals; never an authority or grant path.

Proposal text is source data. No text in these tables is interpreted as an
instruction, an accepted decision, or permission to use a tool.
"""

from .contracts import canonical, strict_loads
from .coordination import Actor
from .store import Conflict, digest


class Improvements:
    """Trusted service component; Actor objects are not remote authentication."""

    SCOPES = {
        "fact": "project_fact",
        "preference": "response_style",
        "procedure": "workflow_notes",
        "authority": "authority_request",
    }

    def __init__(self, store, *, evidence_resolver=None, allow_fixture_evidence=False):
        store._core()
        self.store = store
        self.contracts = store.contracts
        self.evidence_resolver = evidence_resolver
        self.allow_fixture_evidence = allow_fixture_evidence
        # Individual DDL statements stay inside Store's transaction. SQLite
        # executescript would commit an outer transaction before migration.
        with store.transaction():
            store.db.execute(
                "CREATE TABLE IF NOT EXISTS improvement_meta (version INTEGER NOT NULL)"
            )
            version = store.db.execute(
                "SELECT version FROM improvement_meta"
            ).fetchone()
            if version is not None and version[0] != 1:
                raise Conflict("unsupported improvement module version")
            store.db.execute("""CREATE TABLE IF NOT EXISTS improvement_proposals
              (id TEXT PRIMARY KEY, digest TEXT NOT NULL, body TEXT NOT NULL)""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS improvement_reviews
              (proposal TEXT NOT NULL, position TEXT NOT NULL,
               digest TEXT NOT NULL, body TEXT NOT NULL,
               PRIMARY KEY(proposal,position))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS improvement_updates
              (proposal TEXT PRIMARY KEY, project TEXT NOT NULL, scope TEXT NOT NULL,
               kind TEXT NOT NULL, version INTEGER NOT NULL, body TEXT NOT NULL)""")
            if version is None:
                store.db.execute("INSERT INTO improvement_meta VALUES(1)")

    def _project(self, project_id):
        try:
            project = self.store.get(project_id)
        except KeyError as error:
            raise Conflict("unknown canonical project") from error
        if project["record_type"] != "Project":
            raise Conflict("reference is not a project")
        return project

    def _evidence(self, kind, ref, project):
        reference = ref["id"] if isinstance(ref, dict) else ref
        if self.allow_fixture_evidence and reference.startswith("fixture:"):
            return
        if self.evidence_resolver is None:
            raise Conflict("unresolved " + kind + " evidence")
        observed = self.evidence_resolver(kind, reference, project=project)
        expected = (ref if isinstance(ref, dict) else {"ref": ref}) | {
            "project": project
        }
        if not isinstance(observed, dict) or any(
            observed.get(k) != v for k, v in expected.items()
        ):
            raise Conflict("changed or mismatched " + kind + " evidence")

    def _proposal(self, proposal_id):
        row = self.store.db.execute(
            "SELECT body FROM improvement_proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        if row is None:
            raise KeyError(proposal_id)
        return strict_loads(row[0])

    def current_version(self, project, scope, kind):
        row = self.store.db.execute(
            "SELECT max(version) FROM improvement_updates "
            "WHERE project=? AND scope=? AND kind=?",
            (project, scope, kind),
        ).fetchone()
        return row[0] or 0

    def propose(self, correction):
        self.contracts.validate("improvement-proposal", correction)
        if correction["scope"] != self.SCOPES[correction["kind"]]:
            raise PermissionError("proposal kind cannot change authority scope")
        with self.store.transaction():
            self._project(correction["project"])
            self._evidence("source", correction["source"], correction["project"])
            self._evidence(
                "correction",
                {
                    "id": correction["source"]["id"],
                    "correction_digest": correction["correction_digest"],
                },
                correction["project"],
            )
            prior = self.store.db.execute(
                "SELECT digest FROM improvement_proposals WHERE id=?",
                (correction["id"],),
            ).fetchone()
            if prior:
                if prior[0] != digest(correction):
                    raise Conflict("proposal identity conflict")
                return False
            if correction["kind"] != "authority" and correction[
                "expected_version"
            ] != self.current_version(
                correction["project"], correction["scope"], correction["kind"]
            ):
                raise Conflict("stale proposal policy version")
            self.store.db.execute(
                "INSERT INTO improvement_proposals VALUES(?,?,?)",
                (correction["id"], digest(correction), canonical(correction)),
            )
            self.store._history(
                "improvement.proposed",
                {
                    "id": correction["id"],
                    "kind": correction["kind"],
                    "project": correction["project"],
                    "source": correction["source"],
                },
            )
            return True

    def review(self, proposal_id, disposition, evidence, *, position, reviewer):
        if not isinstance(reviewer, Actor) or reviewer.role != position:
            raise PermissionError("trusted reviewer or operator actor required")
        value = {
            "schema_version": 1,
            "proposal_id": proposal_id,
            "position": position,
            "reviewer": reviewer.subject,
            "disposition": disposition,
            "evidence": evidence,
        }
        self.contracts.validate("improvement-review", value)
        with self.store.transaction():
            proposal = self._proposal(proposal_id)
            self._project(proposal["project"])
            for ref in evidence:
                self._evidence("review", ref, proposal["project"])
            if reviewer.subject == proposal["proposer"]:
                raise PermissionError("proposer cannot review own change")
            prior = self.store.db.execute(
                "SELECT digest FROM improvement_reviews WHERE proposal=? AND position=?",
                (proposal_id, position),
            ).fetchone()
            if prior:
                if prior[0] != digest(value):
                    raise Conflict("review position already decided")
                return False
            self.store.db.execute(
                "INSERT INTO improvement_reviews VALUES(?,?,?,?)",
                (proposal_id, position, digest(value), canonical(value)),
            )
            self.store._history(
                "improvement.reviewed",
                {
                    "id": proposal_id,
                    "position": position,
                    "disposition": disposition,
                    "evidence": evidence,
                },
            )
            return True

    def apply(self, proposal_id, expected_policy_version, regression_evidence):
        if (
            not isinstance(regression_evidence, list)
            or not regression_evidence
            or any(not isinstance(ref, str) or not ref for ref in regression_evidence)
        ):
            raise ValueError("regression evidence required")
        if type(expected_policy_version) is not int or expected_policy_version < 0:
            raise ValueError("invalid expected policy version")
        with self.store.transaction():
            proposal = self._proposal(proposal_id)
            if proposal["kind"] == "authority":
                raise PermissionError(
                    "authority proposals require the explicit authority path"
                )
            prior = self.store.db.execute(
                "SELECT body FROM improvement_updates WHERE proposal=?", (proposal_id,)
            ).fetchone()
            if prior:
                result = strict_loads(prior[0])
                if (
                    result["version"] != expected_policy_version + 1
                    or result["regression_evidence"] != regression_evidence
                ):
                    raise Conflict("applied proposal replay conflict")
                return result | {
                    "historical_replay": True,
                    "current_version": self.current_version(
                        proposal["project"], proposal["scope"], proposal["kind"]
                    ),
                }
            if expected_policy_version != proposal[
                "expected_version"
            ] or expected_policy_version != self.current_version(
                proposal["project"], proposal["scope"], proposal["kind"]
            ):
                raise Conflict("stale policy version")
            reviews = [
                strict_loads(row[0])
                for row in self.store.db.execute(
                    "SELECT body FROM improvement_reviews WHERE proposal=?",
                    (proposal_id,),
                )
            ]
            by_position = {review["position"]: review for review in reviews}
            if any(review["disposition"] == "reject" for review in reviews):
                raise PermissionError("proposal rejected")
            required = (
                ("reviewer", "operator")
                if proposal["kind"] in ("preference", "procedure")
                else ("reviewer",)
            )
            if any(
                position not in by_position
                or by_position[position]["disposition"] != "approve"
                for position in required
            ):
                raise PermissionError("required review missing")
            if len(required) > 1 and len(
                {by_position[position]["reviewer"] for position in required}
            ) != len(required):
                raise PermissionError("review positions must be independent")
            if proposal["regression_case"] not in regression_evidence:
                raise PermissionError("named regression case has no passing evidence")
            self._project(proposal["project"])
            self._evidence("source", proposal["source"], proposal["project"])
            self._evidence(
                "correction",
                {
                    "id": proposal["source"]["id"],
                    "correction_digest": proposal["correction_digest"],
                },
                proposal["project"],
            )
            for review in reviews:
                for ref in review["evidence"]:
                    self._evidence("review", ref, proposal["project"])
            for ref in regression_evidence:
                self._evidence("regression", ref, proposal["project"])
            update = {
                "schema_version": 1,
                "proposal_id": proposal_id,
                "project": proposal["project"],
                "scope": proposal["scope"],
                "kind": proposal["kind"],
                "version": expected_policy_version + 1,
                "text": proposal["proposed_text"],
                "source": proposal["source"],
                "review_evidence": sorted(
                    {ref for review in reviews for ref in review["evidence"]}
                ),
                "regression_evidence": regression_evidence,
                "non_authorizing": True,
            }
            self.contracts.validate("improvement-update", update)
            self.store.db.execute(
                "INSERT INTO improvement_updates VALUES(?,?,?,?,?,?)",
                (
                    proposal_id,
                    proposal["project"],
                    proposal["scope"],
                    proposal["kind"],
                    update["version"],
                    canonical(update),
                ),
            )
            self.store._history(
                "improvement.applied",
                {
                    "id": proposal_id,
                    "version": update["version"],
                    "regression_evidence": regression_evidence,
                },
            )
            return update | {
                "historical_replay": False,
                "current_version": update["version"],
            }
