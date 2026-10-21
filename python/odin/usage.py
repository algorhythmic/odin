"""Metadata-only native usage observations. No prices or spend enforcement.

Collectors inspect only explicit data or an explicit, size-bounded JSONL file.
A request is counted once per provider/session/agent/request identity. Aggregate
parent totals are retained for inspection but excluded from additive summaries.
"""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from .contracts import Contracts, canonical, strict_loads
from .store import Conflict, now

TOKEN_KEYS = ("uncached_input", "cache_read", "cache_write", "output")
MAX_BYTES = 8 * 1024 * 1024


def _integer(value):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= 9007199254740991:
        raise ValueError("usage counters must be bounded nonnegative integers or null")
    return value


def _tokens(uncached=None, read=None, write=None, output=None):
    return dict(zip(TOKEN_KEYS, map(_integer, (uncached, read, write, output))))


def _timestamp(value=None):
    if value is None:
        return now()
    if not isinstance(value, str):
        raise ValueError("observed_at must be a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid observed_at timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("observed_at must have a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def request(*, provider, project_id, source, session_id, agent_id, request_id, model=None,
            tokens, revision=0, scope="atomic", loop_id=None, stage_id=None,
            attribution="exact", context_input_tokens=None, observed_at=None):
    item = {"schema_version": 1, "kind": "request", "provider": provider,
            "project_id": project_id, "source": source, "session_id": session_id, "agent_id": agent_id,
            "request_id": request_id, "model": model, "revision": revision,
            "scope": scope, "loop_id": loop_id, "stage_id": stage_id,
            "attribution": attribution, "tokens": tokens,
            "context_input_tokens": _integer(context_input_tokens),
            "observed_at": _timestamp(observed_at)}
    Contracts().validate("usage-observation", item)
    return item


def normalize_claude_status(status, *, project_id, session_id, agent_id="executive",
                            account_id="unknown", observed_at=None):
    """Status-line JSON is a quota/context sample, never a billable request."""
    if not isinstance(status, dict):
        raise ValueError("status must be an object")
    ctx = status.get("context_window") or {}
    limits = status.get("rate_limits") or {}
    if not isinstance(ctx, dict) or not isinstance(limits, dict):
        raise ValueError("status context and limits must be objects")
    current = ctx.get("current_usage") if isinstance(ctx.get("current_usage"), dict) else {}
    categories = [current.get(k) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
    context_input = sum(_integer(v) for v in categories) if all(v is not None for v in categories) else None
    def limit(value):
        value = value or {}
        if not isinstance(value, dict):
            raise ValueError("rate limit must be an object")
        # `utilization` has no documented percentage unit here; treating a
        # fractional value as percent would understate an account limit.
        utilization = value.get("used_percentage")
        if utilization is not None and (type(utilization) not in (int, float) or
                                         not 0 <= utilization <= 100):
            raise ValueError("invalid utilization")
        return {"used_percentage": utilization, "resets_at": value.get("resets_at")}
    item = {"schema_version": 1, "kind": "quota", "provider": "claude",
            "source": "claude_status", "project_id": project_id, "session_id": session_id,
            "agent_id": agent_id, "account_id": account_id,
            "observed_at": _timestamp(observed_at),
            "context_input_tokens": context_input,
            "context_window_tokens": _integer(ctx.get("context_window_size")),
            "rate_limits": {"five_hour": limit(limits.get("five_hour")),
                            "seven_day": limit(limits.get("seven_day"))}}
    Contracts().validate("usage-observation", item)
    return item


def _rows(source, max_bytes):
    if type(max_bytes) is not int or max_bytes <= 0 or max_bytes > MAX_BYTES:
        raise ValueError("invalid scan bound")
    if isinstance(source, (str, Path)):
        path = Path(source)
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("usage source must be a regular file")
            raw = os.read(fd, max_bytes + 1)
            after = os.fstat(fd)
            try:
                pathname = os.stat(path, follow_symlinks=False)
            except FileNotFoundError:
                pathname = None
            # A single bounded read can be short, or the source may change
            # while inspected. In either case its coverage is unknown.
            changed = (info.st_size != after.st_size or
                       (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino) or
                       pathname is None or
                       (after.st_dev, after.st_ino) != (pathname.st_dev, pathname.st_ino) or
                       after.st_size != pathname.st_size or
                       len(raw) < min(info.st_size, max_bytes + 1))
            truncated = len(raw) > max_bytes or info.st_size > max_bytes or changed
        finally:
            os.close(fd)
        if truncated:
            raw = raw[:max_bytes]
            raw = raw[:raw.rfind(b"\n") + 1] if b"\n" in raw else b""
        lines = raw.splitlines()
    elif isinstance(source, (dict, list)):
        items = source if isinstance(source, list) else [source]
        lines = []
        used = 0
        for item in items:
            line = canonical(item).encode()
            used += len(line) + 1
            if used > max_bytes:
                raise ValueError("input exceeds scan bound")
            lines.append(line)
        truncated = False
    else:
        raise TypeError("source must be explicit path or parsed JSON")
    malformed = 0
    for raw_line in lines:
        try:
            value = strict_loads(raw_line.decode("utf-8"))
            if isinstance(value, dict):
                yield value, None
            else:
                malformed += 1
        except (UnicodeError, ValueError):
            malformed += 1
    yield None, {"truncated": truncated, "malformed_lines": malformed,
                 "complete": not truncated and malformed == 0}


def usage_from_claude_jsonl(source, *, project_id, session_id, agent_id="executive",
                            loop_id=None, stage_id=None, max_bytes=MAX_BYTES):
    observations, coverage = [], None
    unidentified = 0
    aggregates = 0
    for row, state in _rows(source, max_bytes):
        if state is not None:
            coverage = state
            coverage["unidentified_usage"] = unidentified
            coverage["aggregate_usage"] = aggregates
            coverage["complete"] = coverage["complete"] and unidentified == 0 and aggregates == 0
            break
        message = row.get("message") or {}
        usage = message.get("usage")
        if not isinstance(usage, dict):
            # Result usage is inclusive across requests; keep it separate.
            if row.get("type") == "result" and isinstance(row.get("usage"), dict):
                message, usage = row, row["usage"]
                scope = "aggregate"
                aggregates += 1
            else:
                continue
        else:
            scope = "atomic"
        rid = message.get("id") or row.get("request_id")
        if not isinstance(rid, str) or not rid:
            unidentified += 1
            continue
        sid = row.get("sessionId") or row.get("session_id") or session_id
        aid = row.get("agentId") or row.get("agent_id") or agent_id
        cache_creation = usage.get("cache_creation_input_tokens")
        observations.append(request(provider="claude", project_id=project_id, source="claude_jsonl",
            session_id=sid, agent_id=aid, request_id=rid,
            model=message.get("model"), revision=0, scope=scope,
            loop_id=loop_id, stage_id=stage_id, attribution="reported",
            tokens=_tokens(usage.get("input_tokens"), usage.get("cache_read_input_tokens"),
                           cache_creation, usage.get("output_tokens")),
            context_input_tokens=None, observed_at=row.get("timestamp")))
    _assign_revisions(observations)
    return {"observations": observations, "coverage": coverage}


def usage_from_codex_jsonl(source, *, project_id, session_id, agent_id="executive",
                           model=None, loop_id=None, stage_id=None,
                           usage_semantics="per_turn", max_bytes=MAX_BYTES):
    if usage_semantics not in ("per_turn", "session_cumulative"):
        raise ValueError("unknown Codex usage semantics")
    observations, coverage = [], None
    sid, turn = session_id, 0
    unstable_identity = 0
    aggregates = 0
    for row, state in _rows(source, max_bytes):
        if state is not None:
            coverage = state
            coverage["unidentified_usage"] = unstable_identity
            coverage["aggregate_usage"] = aggregates
            coverage["complete"] = coverage["complete"] and unstable_identity == 0 and aggregates == 0
            break
        typ = row.get("type")
        if typ == "thread.started":
            sid = row.get("thread_id") or sid
        elif typ == "turn.started":
            turn += 1
        usage = row.get("usage")
        if typ not in ("turn.completed", "result") or not isinstance(usage, dict):
            continue
        if typ == "result":
            aggregates += 1
        if typ == "result":
            rid = "result-total"
        elif usage_semantics == "session_cumulative":
            rid = "session-total"
        else:
            rid = row.get("turn_id") or row.get("request_id")
            if not isinstance(rid, str) or not rid:
                rid = f"turn:{turn}"
                unstable_identity += 1
        total = _integer(usage.get("input_tokens"))
        cached = _integer(usage.get("cached_input_tokens"))
        if total is not None and cached is not None and cached > total:
            raise ValueError("cached input exceeds total input")
        uncached = total - cached if total is not None and cached is not None else None
        observations.append(request(provider="codex", project_id=project_id, source="codex_jsonl",
            session_id=sid, agent_id=agent_id, request_id=rid,
            model=row.get("model") or model,
            loop_id=None if usage_semantics == "session_cumulative" else loop_id,
            stage_id=None if usage_semantics == "session_cumulative" else stage_id,
            scope="aggregate" if typ == "result" else ("cumulative" if usage_semantics == "session_cumulative" else "atomic"), attribution="reported", tokens=_tokens(uncached, cached, 0,
                                                    usage.get("output_tokens")),
            context_input_tokens=total, observed_at=row.get("timestamp")))
    _assign_revisions(observations)
    return {"observations": observations, "coverage": coverage}


def _assign_revisions(observations):
    seen = {}
    for observation in observations:
        key = tuple(observation[k] for k in ("provider", "project_id", "session_id", "agent_id", "request_id"))
        old = seen.get(key)
        if old is not None:
            if old["tokens"] == observation["tokens"] and old["model"] == observation["model"]:
                observation["revision"] = old["revision"]
            else:
                observation["revision"] = old["revision"] + 1
        seen[key] = observation


class UsageLedger:
    """Service-owned tables inside the Store transaction and history boundary."""
    def __init__(self, store):
        store._core()
        self.store = store
        store.db.execute("""CREATE TABLE IF NOT EXISTS usage_requests (
            provider TEXT NOT NULL, project_id TEXT NOT NULL, session_id TEXT NOT NULL, agent_id TEXT NOT NULL,
            request_id TEXT NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(provider,project_id,session_id,agent_id,request_id))""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS usage_quotas (
            provider TEXT NOT NULL, project_id TEXT NOT NULL, account_id TEXT NOT NULL, session_id TEXT NOT NULL,
            observed_at TEXT NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(provider,project_id,account_id,session_id,observed_at))""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS usage_coverage (
            project_id TEXT NOT NULL, source_id TEXT NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(project_id,source_id))""")

    def ingest(self, observation):
        self.store.contracts.validate("usage-observation", observation)
        if observation["kind"] == "request" and type(observation["revision"]) is not int:
            raise ValueError("revision must be an integer")
        with self.store.transaction():
            if observation["kind"] == "quota":
                key = tuple(observation[k] for k in ("provider", "project_id", "account_id", "session_id", "observed_at"))
                row = self.store.db.execute("SELECT body FROM usage_quotas WHERE provider=? AND project_id=? AND account_id=? AND session_id=? AND observed_at=?", key).fetchone()
                if row:
                    if strict_loads(row[0]) != observation:
                        raise Conflict("conflicting quota sample")
                    return "duplicate"
                self.store.db.execute("INSERT INTO usage_quotas VALUES(?,?,?,?,?,?)", (*key, canonical(observation)))
                self.store._history("usage.quota_observed", {"observation": observation})
                return "inserted"
            key = tuple(observation[k] for k in ("provider", "project_id", "session_id", "agent_id", "request_id"))
            row = self.store.db.execute("SELECT body FROM usage_requests WHERE provider=? AND project_id=? AND session_id=? AND agent_id=? AND request_id=?", key).fetchone()
            if row:
                old = strict_loads(row[0])
                for field in ("model", "scope", "loop_id", "stage_id"):
                    if old[field] is not None and observation[field] != old[field]:
                        raise Conflict("conflicting usage identity")
                if observation["revision"] < old["revision"]:
                    grew = any(
                        observation["tokens"][field] is not None and
                        (old["tokens"][field] is None or observation["tokens"][field] > old["tokens"][field])
                        for field in TOKEN_KEYS
                    )
                    shrank = any(
                        old["tokens"][field] is not None and
                        (observation["tokens"][field] is None or observation["tokens"][field] < old["tokens"][field])
                        for field in TOKEN_KEYS
                    )
                    if shrank and grew:
                        raise Conflict("mixed stale and growing usage counters")
                    if not grew:
                        return "stale"
                    observation = {**observation, "revision": old["revision"] + 1}
                for field in TOKEN_KEYS:
                    before, after = old["tokens"][field], observation["tokens"][field]
                    if before is not None and (after is None or after < before):
                        raise Conflict("nonmonotonic usage revision")
                if observation["revision"] == old["revision"]:
                    if observation["tokens"] == old["tokens"] and observation["model"] == old["model"]:
                        return "duplicate"
                    observation = {**observation, "revision": old["revision"] + 1}
                self.store.db.execute("UPDATE usage_requests SET body=? WHERE provider=? AND project_id=? AND session_id=? AND agent_id=? AND request_id=?", (canonical(observation), *key))
                action = "revised"
            else:
                self.store.db.execute("INSERT INTO usage_requests VALUES(?,?,?,?,?,?)", (*key, canonical(observation)))
                action = "inserted"
            self.store._history("usage.request_observed", {"observation": observation})
            return action

    def record_coverage(self, source_id, coverage, *, project_id):
        if not isinstance(source_id, str) or not source_id or not isinstance(project_id, str) or not project_id:
            raise ValueError("project_id and source_id required")
        if set(coverage) - {"truncated", "malformed_lines", "complete", "unidentified_usage", "aggregate_usage"} or not {"truncated", "malformed_lines", "complete"} <= set(coverage):
            raise ValueError("invalid coverage")
        self.store.contracts.validate("usage-coverage", {"schema_version": 1, **coverage})
        if type(coverage["truncated"]) is not bool or type(coverage["complete"]) is not bool or type(coverage["malformed_lines"]) is not int or coverage["malformed_lines"] < 0:
            raise ValueError("invalid coverage")
        if coverage["complete"] and (coverage["truncated"] or coverage["malformed_lines"]
                                     or coverage.get("unidentified_usage", 0)
                                     or coverage.get("aggregate_usage", 0)):
            raise ValueError("complete coverage conflicts with observed gaps")
        with self.store.transaction():
            old = self.store.db.execute("SELECT body FROM usage_coverage WHERE project_id=? AND source_id=?", (project_id, source_id)).fetchone()
            if old and strict_loads(old[0]) == coverage:
                return "duplicate"
            self.store.db.execute("INSERT INTO usage_coverage VALUES(?,?,?) ON CONFLICT(project_id,source_id) DO UPDATE SET body=excluded.body", (project_id, source_id, canonical(coverage)))
            self.store._history("usage.coverage_observed", {"project_id": project_id, "source_id": source_id, "coverage": coverage})
            return "recorded"

    def summary(self, *, project_id, loop_id=None, stage_id=None, as_of=None, max_quota_age_seconds=300):
        rows = [strict_loads(r[0]) for r in self.store.db.execute("SELECT body FROM usage_requests")]
        rows = [r for r in rows if r["project_id"] == project_id and (loop_id is None or r["loop_id"] == loop_id) and
                (stage_id is None or r["stage_id"] == stage_id)]
        cumulative = [r for r in rows if r["scope"] == "cumulative"]
        cumulative_groups = {}
        for row in cumulative:
            key = (row["provider"], row["session_id"], row["agent_id"])
            cumulative_groups.setdefault(key, []).append(row)
        atomic_groups = {}
        for row in rows:
            if row["scope"] == "atomic":
                key = (row["provider"], row["session_id"], row["agent_id"])
                atomic_groups.setdefault(key, []).append(row)
        shadowed_atomic = sum(len(atomic_groups.get(key, [])) for key in cumulative_groups)
        additive = [r for key, group in atomic_groups.items() if key not in cumulative_groups for r in group] + cumulative
        totals = {k: 0 for k in TOKEN_KEYS}
        missing = {k: 0 for k in TOKEN_KEYS}
        for key in atomic_groups.keys() | cumulative_groups.keys():
            atomics = atomic_groups.get(key, [])
            snapshots = cumulative_groups.get(key, [])
            for field in TOKEN_KEYS:
                atomic_total = sum(r["tokens"][field] or 0 for r in atomics)
                if snapshots:
                    snapshot_total = max((r["tokens"][field] or 0 for r in snapshots), default=0)
                    totals[field] += max(atomic_total, snapshot_total)
                    missing[field] += int(all(r["tokens"][field] is None for r in snapshots)
                                          and (not atomics or any(r["tokens"][field] is None for r in atomics)))
                else:
                    totals[field] += atomic_total
                    missing[field] += sum(r["tokens"][field] is None for r in atomics)
        quotas = [strict_loads(r[0]) for r in self.store.db.execute(
            "SELECT body FROM usage_quotas WHERE project_id=? "
            "ORDER BY provider,account_id,session_id,observed_at", (project_id,)
        )]
        coverage = [strict_loads(r[0]) for r in self.store.db.execute(
            "SELECT body FROM usage_coverage WHERE project_id=? ORDER BY source_id", (project_id,)
        )]
        latest_quota = max(quotas, key=lambda q: datetime.fromisoformat(q["observed_at"]), default=None)
        if type(max_quota_age_seconds) is not int or max_quota_age_seconds < 0:
            raise ValueError("invalid quota age bound")
        current_time = datetime.fromisoformat(_timestamp(as_of))
        quota_stale = (latest_quota is None or
                       not 0 <= (current_time - datetime.fromisoformat(latest_quota["observed_at"])).total_seconds() <= max_quota_age_seconds)
        latest_context = ({k: latest_quota[k] for k in ("observed_at", "context_input_tokens", "context_window_tokens", "session_id", "agent_id")} if latest_quota else None)
        inclusive = None if missing["uncached_input"] or missing["cache_read"] or missing["cache_write"] else sum(totals[k] for k in ("uncached_input", "cache_read", "cache_write"))
        attribution_counts = {a: sum(r["attribution"] == a for r in additive) for a in ("exact", "reported", "inferred")}
        return {"project_id": project_id, "loop_id": loop_id, "stage_id": stage_id,
                "tokens": totals, "cache_inclusive_input_tokens": inclusive,
                "attribution_counts": attribution_counts, "latest_context": latest_context,
                "latest_quota": latest_quota, "quota_stale": quota_stale, "missing_requests": missing,
                "request_count": sum(max(len(atomic_groups.get(key, [])), 1) for key in cumulative_groups) +
                                 sum(len(group) for key, group in atomic_groups.items() if key not in cumulative_groups),
                "cumulative_sessions": len(cumulative_groups),
                "aggregate_excluded": sum(r["scope"] == "aggregate" for r in rows),
                "shadowed_atomic": shadowed_atomic,
                "coverage_complete": not cumulative and not any(r["scope"] == "aggregate" for r in rows) and
                                     bool(coverage) and all(c["complete"] for c in coverage) and not any(missing.values()),
                "coverage": coverage, "quota_snapshots": quotas,
                "limitations": ["coverage_complete covers registered sources only; unregistered native requests may be omitted", "token totals do not infer prices or account quota"]}
