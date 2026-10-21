"""Opt-in admission observations and bounded, non-authoritative continuity notes.

A hold affects only a future admission call site. Native sessions already running
are not interrupted, and these observed counters are not hard spend ceilings.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from .contracts import Contracts, canonical, strict_loads
from .store import Conflict, now
from .usage import UsageLedger

POLICY_LIMITS = (
    "max_input_tokens", "max_output_tokens", "max_requests", "max_context_tokens",
    "max_five_hour_used_percentage", "max_seven_day_used_percentage",
    "max_sample_age_seconds",
)

# Label-keyed admission bands for probed account limits (ADR-031 follow-up).
# Each ceiling defines three admission bands for Odin's own decisions: wind_down
# at ceiling-10, ordinary_stop at ceiling-5 and handoff_only at ceiling. These
# are not enforced ceilings; the provider's own limits and running native
# sessions are not controlled by them. Labels absent here keep the legacy
# behaviour: no band is reported and the policy_limits checks are unchanged.
LIMITS = {
    "claude.five_hour": {"ceiling": 95},
    "claude.weekly": {"ceiling": 90},
    "claude.weekly.fable": {"ceiling": 95},
    "codex.five_hour": {"ceiling": 95},
    "codex.weekly": {"ceiling": 90},
}
BANDS = ("clear", "wind_down", "ordinary_stop", "handoff_only")


def band_for(label, utilization_percent):
    """Return the admission band for a known label, or None for legacy labels."""
    entry = LIMITS.get(label)
    if entry is None or utilization_percent is None:
        return None
    ceiling = entry["ceiling"]
    if utilization_percent >= ceiling:
        return "handoff_only"
    if utilization_percent >= ceiling - 5:
        return "ordinary_stop"
    if utilization_percent >= ceiling - 10:
        return "wind_down"
    return "clear"


def _limit_bands(summary):
    bands = []
    for sample in summary.get("limit_snapshots", []):
        if sample.get("status") != "available":
            continue
        band = band_for(sample["label"], sample["utilization_percent"])
        if band is None:
            continue
        bands.append({"label": sample["label"], "utilization_percent": sample["utilization_percent"],
                      "observed_at": sample["observed_at"], "band": band})
    return bands
_UNSET = object()


def _id(value, name):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ValueError(f"{name} must be a nonempty bounded string")
    return value


def _time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must have a timezone")
    return parsed


def _stamp(value):
    return _time(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _quota_fresh(sample, stamp, max_age_seconds):
    if sample is None:
        return False
    age = (_time(stamp) - _time(sample["observed_at"])).total_seconds()
    return 0 <= age <= max_age_seconds


def _matching_quotas(summary, account_id, session_id):
    matching = [q for q in summary["quota_snapshots"]
                if q["provider"] == "claude" and account_id not in (None, "unknown")
                and q["account_id"] == account_id]
    quota = max(matching, key=lambda q: _time(q["observed_at"]), default=None)
    context_quota = max((q for q in matching if session_id is not None and q["session_id"] == session_id),
                        key=lambda q: _time(q["observed_at"]), default=None)
    return quota, context_quota


def _project(store, project_id):
    _id(project_id, "project_id")
    try:
        record = store.get(project_id)
    except KeyError:
        raise ValueError("unknown project") from None
    if record["record_type"] != "Project":
        raise ValueError("scope is not a Project")


def _default_policy():
    return {"schema_version": 1, "mode": "observe", "missing_telemetry": "observe", "account_id": None,
            "limits": {key: None for key in POLICY_LIMITS}}


def _normalize_policy(policy):
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    if set(policy) - {"schema_version", "mode", "missing_telemetry", "account_id", "limits"}:
        raise ValueError("unknown policy field")
    result = _default_policy()
    result.update({key: value for key, value in policy.items() if key != "limits"})
    given = policy.get("limits", {})
    if not isinstance(given, dict):
        raise ValueError("limits must be an object")
    result["limits"].update(given)
    Contracts().validate("usage-policy", result)
    for key in ("max_input_tokens", "max_output_tokens", "max_requests", "max_context_tokens", "max_sample_age_seconds"):
        value = result["limits"][key]
        if value is not None and type(value) is not int:
            raise ValueError(f"{key} must be integer")
    return result


class UsagePolicy:
    def __init__(self, store):
        store._core()
        self.store = store
        self.usage = UsageLedger(store)
        store.db.execute("""CREATE TABLE IF NOT EXISTS usage_policies
            (project_id TEXT PRIMARY KEY, body TEXT NOT NULL)""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS usage_policy_operations
            (operation_id TEXT PRIMARY KEY, kind TEXT NOT NULL, project_id TEXT NOT NULL,
             input TEXT NOT NULL, body TEXT NOT NULL)""")

    def configure(self, project_id, policy, operation_id):
        _project(self.store, project_id)
        _id(operation_id, "operation_id")
        normalized = _normalize_policy(policy)
        encoded = canonical(normalized)
        with self.store.transaction():
            prior = self.store.db.execute("SELECT kind,project_id,input,body FROM usage_policy_operations WHERE operation_id=?", (operation_id,)).fetchone()
            if prior:
                if prior[0] != "configure" or prior[1] != project_id or prior[2] != encoded:
                    raise Conflict("operation id reused with different policy")
                return strict_loads(prior[3])
            self.store.db.execute("INSERT INTO usage_policies VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET body=excluded.body", (project_id, encoded))
            self.store.db.execute("INSERT INTO usage_policy_operations VALUES(?,?,?,?,?)", (operation_id, "configure", project_id, encoded, encoded))
            self.store._history("usage.policy_configured", {"project_id": project_id, "operation_id": operation_id, "policy": normalized})
        return normalized

    def get(self, project_id):
        _project(self.store, project_id)
        row = self.store.db.execute("SELECT body FROM usage_policies WHERE project_id=?", (project_id,)).fetchone()
        return strict_loads(row[0]) if row else _default_policy()

    def check(self, project_id, *, purpose, loop_id=None, stage_id=None,
              session_id=None, now=None):
        """Reevaluate when policy, observed usage, or the minute changes.

        The generated operation id makes unchanged polls replay the same persisted
        decision without freezing admission after telemetry or time changes.
        """
        _project(self.store, project_id)
        _id(purpose, "purpose")
        for name, value in (("loop_id", loop_id), ("stage_id", stage_id),
                            ("session_id", session_id)):
            if value is not None:
                _id(value, name)
        stamp = _stamp(now or globals()["now"]())
        configured = self.store.db.execute(
            "SELECT 1 FROM usage_policies WHERE project_id=?", (project_id,)
        ).fetchone()
        if configured is None:
            # Ordinary legacy polling must not create a durable admission
            # event or scan telemetry until the operator opts into a policy.
            decision = {
                "schema_version": 1, "project_id": project_id,
                "operation_id": "usage-unconfigured:" + hashlib.sha256(
                    canonical((project_id, purpose, loop_id, stage_id, session_id)).encode()
                ).hexdigest(),
                "purpose": purpose, "loop_id": loop_id, "stage_id": stage_id,
                "session_id": session_id, "evaluated_at": stamp,
                "mode": "observe", "decision": "allow", "reasons": [],
                "configured": False,
                "limit_bands": [],
                "observed": {
                    "request_count": 0, "cache_inclusive_input_tokens": None,
                    "output_tokens": None, "context_input_tokens": None,
                    "five_hour_used_percentage": None,
                    "seven_day_used_percentage": None,
                    "quota_observed_at": None, "coverage_complete": False,
                    "quota_stale": True, "context_stale": True,
                },
            }
            self.store.contracts.validate("usage-policy-decision", decision)
            return decision
        policy = self.get(project_id)
        age = policy["limits"]["max_sample_age_seconds"]
        effective_age = age if age is not None else 300
        summary = self.usage.summary(project_id=project_id, as_of=stamp,
                                     max_quota_age_seconds=effective_age)
        quota, context_quota = _matching_quotas(summary, policy["account_id"], session_id)
        fingerprint = hashlib.sha256(canonical({"policy": policy,
            "summary": summary, "purpose": purpose, "loop_id": loop_id,
            "stage_id": stage_id, "session_id": session_id,
            "quota_fresh": _quota_fresh(quota, stamp, effective_age),
            "context_fresh": _quota_fresh(context_quota, stamp, effective_age),
            "minute": stamp[:16]}).encode()).hexdigest()
        return self.evaluate(project_id, operation_id=f"usage-check:{fingerprint}",
                             purpose=purpose, loop_id=loop_id, stage_id=stage_id,
                             session_id=session_id, now=stamp)

    def evaluate(self, project_id, *, operation_id, purpose, loop_id=None,
                 stage_id=None, session_id=None, now=None):
        _project(self.store, project_id)
        _id(operation_id, "operation_id")
        _id(purpose, "purpose")
        if loop_id is not None: _id(loop_id, "loop_id")
        if stage_id is not None: _id(stage_id, "stage_id")
        if session_id is not None: _id(session_id, "session_id")
        stamp = _stamp(now or globals()["now"]())
        request = {"purpose": purpose, "loop_id": loop_id,
                   "stage_id": stage_id, "session_id": session_id}
        encoded = canonical(request)
        with self.store.transaction():
            prior = self.store.db.execute("SELECT kind,project_id,input,body FROM usage_policy_operations WHERE operation_id=?", (operation_id,)).fetchone()
            if prior:
                if prior[0] != "evaluate" or prior[1] != project_id or prior[2] != encoded:
                    raise Conflict("operation id reused with different admission")
                return strict_loads(prior[3])
            configured = self.store.db.execute(
                "SELECT 1 FROM usage_policies WHERE project_id=?", (project_id,)
            ).fetchone() is not None
            policy = self.get(project_id)
            age = policy["limits"]["max_sample_age_seconds"]
            # Policy limits are project-cumulative. A new stage or loop must
            # not reset the observed lower bound.
            summary = self.usage.summary(project_id=project_id,
                                         as_of=stamp, max_quota_age_seconds=age if age is not None else 300)
            account_id = policy["account_id"]
            quota, context_quota = _matching_quotas(summary, account_id, session_id)
            effective_age = age if age is not None else 300
            quota_stale = not _quota_fresh(quota, stamp, effective_age)
            context_stale = not _quota_fresh(context_quota, stamp, effective_age)
            rate = quota["rate_limits"] if quota else {}
            known_input = sum(summary["tokens"][k] for k in ("uncached_input", "cache_read", "cache_write"))
            observed = {
                "request_count": summary["request_count"],
                "cache_inclusive_input_tokens": known_input,
                "output_tokens": summary["tokens"]["output"],
                "context_input_tokens": context_quota["context_input_tokens"] if context_quota else None,
                "five_hour_used_percentage": rate.get("five_hour", {}).get("used_percentage"),
                "seven_day_used_percentage": rate.get("seven_day", {}).get("used_percentage"),
                "quota_observed_at": quota["observed_at"] if quota else None,
                "coverage_complete": summary["coverage_complete"],
                "quota_stale": quota_stale,
                "context_stale": context_stale,
            }
            reasons = []
            checks = (
                ("input_tokens", "max_input_tokens", observed["cache_inclusive_input_tokens"]),
                ("output_tokens", "max_output_tokens", observed["output_tokens"]),
                ("requests", "max_requests", observed["request_count"]),
                ("context_tokens", "max_context_tokens", observed["context_input_tokens"]),
                ("five_hour", "max_five_hour_used_percentage", observed["five_hour_used_percentage"]),
                ("seven_day", "max_seven_day_used_percentage", observed["seven_day_used_percentage"]),
            )
            threshold = False
            missing = False
            for name, limit_name, value in checks:
                limit = policy["limits"][limit_name]
                if limit is None: continue
                if name in ("five_hour", "seven_day") and quota_stale:
                    reasons.append(f"{name}:stale_sample")
                    missing = True
                elif name == "context_tokens" and context_stale:
                    reasons.append("context_tokens:stale_sample")
                    missing = True
                elif value is None:
                    reasons.append(f"{name}:missing")
                    missing = True
                elif value >= limit:
                    reasons.append(f"{name}:threshold")
                    threshold = True
                elif name in ("input_tokens", "output_tokens", "requests") and not summary["coverage_complete"]:
                    reasons.append(f"{name}:missing")
                    missing = True
            if not summary["coverage_complete"] and any(policy["limits"][k] is not None for k in ("max_input_tokens", "max_output_tokens", "max_requests")):
                reasons.append("request_coverage:incomplete")
                missing = True
            hold = policy["mode"] == "hold" and (threshold or (missing and policy["missing_telemetry"] == "hold"))
            decision = {"schema_version": 1, "project_id": project_id, "operation_id": operation_id,
                        "purpose": purpose, "loop_id": loop_id, "stage_id": stage_id,
                        "session_id": session_id,
                        "evaluated_at": stamp, "mode": policy["mode"],
                        "configured": configured,
                        "decision": "hold" if hold else "allow", "reasons": list(dict.fromkeys(reasons)),
                        "limit_bands": _limit_bands(summary),
                        "observed": observed}
            self.store.contracts.validate("usage-policy-decision", decision)
            body = canonical(decision)
            self.store.db.execute("INSERT INTO usage_policy_operations VALUES(?,?,?,?,?)", (operation_id, "evaluate", project_id, encoded, body))
            self.store._history("usage.admission_evaluated", {"decision": decision})
            return decision


class ContinuityCheckpoints:
    def __init__(self, store):
        store._core()
        self.store = store
        store.db.execute("""CREATE TABLE IF NOT EXISTS context_checkpoints
            (operation_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, session_id TEXT NOT NULL,
             revision INTEGER NOT NULL, created_at TEXT NOT NULL, body TEXT NOT NULL)""")
        store.db.execute("CREATE INDEX IF NOT EXISTS context_checkpoints_lookup ON context_checkpoints(project_id,session_id,revision)")

    def checkpoint(self, project_id, payload, operation_id, *,
                   expected_session_id=_UNSET, expected_loop_id=_UNSET,
                   expected_stage_id=_UNSET):
        _project(self.store, project_id)
        _id(operation_id, "operation_id")
        if not isinstance(payload, dict):
            raise ValueError("checkpoint payload must be object")
        item = {"schema_version": 1, "project_id": project_id, "loop_id": None, "stage_id": None, **payload}
        if item["project_id"] != project_id:
            raise Conflict("checkpoint project mismatch")
        for field, expected in (("session_id", expected_session_id),
                                ("loop_id", expected_loop_id),
                                ("stage_id", expected_stage_id)):
            if expected is not _UNSET and item.get(field) != expected:
                raise Conflict(f"checkpoint {field} differs from trusted binding")
        body = canonical(item)
        if len(body.encode("utf-8")) > 16 * 1024:
            raise ValueError("checkpoint exceeds 16 KiB")
        self.store.contracts.validate("context-checkpoint", item)
        if type(item["revision"]) is not int:
            raise ValueError("checkpoint revision must be integer")
        if item.get("stage_id") is not None and item.get("loop_id") is None:
            raise Conflict("checkpoint stage requires a loop")
        if item.get("loop_id") is not None:
            row = self.store.db.execute(
                "SELECT body FROM development_loops WHERE id=?", (item["loop_id"],)
            ).fetchone() if self.store.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='development_loops'"
            ).fetchone() else None
            if row is None:
                raise Conflict("checkpoint loop identity unavailable")
            loop = strict_loads(row[0])
            if loop["project"] != project_id or loop["session_id"] != item["session_id"]:
                raise Conflict("checkpoint loop belongs to another project or session")
            if item.get("stage_id") is not None:
                row = self.store.db.execute(
                    "SELECT body FROM development_loop_stages WHERE id=?",
                    (item["stage_id"],),
                ).fetchone()
                if row is None:
                    raise Conflict("checkpoint stage identity unavailable")
                stage = strict_loads(row[0])
                if stage["loop_id"] != item["loop_id"] or stage["session_id"] != item["session_id"]:
                    raise Conflict("checkpoint stage belongs to another loop or session")
        with self.store.transaction():
            prior = self.store.db.execute("SELECT project_id,body FROM context_checkpoints WHERE operation_id=?", (operation_id,)).fetchone()
            if prior:
                if prior[0] != project_id or prior[1] != body:
                    raise Conflict("checkpoint operation id reused")
                return strict_loads(prior[1])
            previous = self.latest_checkpoint(project_id, session_id=item["session_id"])
            if previous and item["revision"] <= previous["revision"]:
                raise Conflict("checkpoint revision must advance")
            self.store.db.execute("INSERT INTO context_checkpoints VALUES(?,?,?,?,?,?)", (operation_id, project_id, item["session_id"], item["revision"], now(), body))
            self.store._history("context.checkpoint_recorded", {"operation_id": operation_id, "checkpoint": item})
        return item

    def latest_checkpoint(self, project_id, session_id=None):
        _project(self.store, project_id)
        if session_id is not None: _id(session_id, "session_id")
        row = self.store.db.execute("SELECT body FROM context_checkpoints WHERE project_id=? AND (? IS NULL OR session_id=?) ORDER BY created_at DESC, rowid DESC LIMIT 1", (project_id, session_id, session_id)).fetchone()
        return strict_loads(row[0]) if row else None
