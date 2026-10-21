"""Incremental, explicit-root native usage watcher with metadata-only cursor state.

This separate process never opens Odin's service database. It prepares bounded
metadata batches in its private SQLite file, sends them through the operator
socket, and advances byte cursors only after the service acknowledges them.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import sqlite3
import stat
import time
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ROOT, Contracts, canonical, strict_loads
from jsonschema import ValidationError
from .development_loop import _ulid_from_digest
from .usage import (normalize_claude_status, probe_claude_limits, probe_codex_limits,
                    usage_from_claude_jsonl, usage_from_codex_jsonl)

DEFAULT_CHUNK = 262144
MAX_COMMAND_BYTES = 480000
PREFIX_BYTES = 4096


def _regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        os.close(fd)
        raise ValueError("usage source must be a regular file")
    return fd, info


def _directory(path):
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("configured usage root must be a directory, not a symlink")


def _entries(directory, max_files):
    _directory(directory)
    result = []
    with os.scandir(directory) as stream:
        for inspected, entry in enumerate(stream, 1):
            if inspected > max_files:
                raise ValueError("configured session root exceeds max_files entries; narrow the root")
            if not entry.name.endswith(".jsonl") or not entry.is_file(follow_symlinks=False):
                continue
            result.append(Path(entry.path))
    return sorted(result)


def _spool_entries(directory, max_files):
    _directory(directory)
    result = []
    with os.scandir(directory) as stream:
        for inspected, entry in enumerate(stream, 1):
            if inspected > max_files:
                raise ValueError("evaluator spool exceeds max_files entries")
            if entry.is_dir(follow_symlinks=False):
                result.append(Path(entry.path) / "stdout.log")
    return sorted(result)


def _status_time(info):
    return datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


def _prefix_signature(fd, length):
    data = os.pread(fd, length, 0)
    if len(data) != length:
        raise OSError("usage source changed while reading prefix")
    return canonical([length, hashlib.sha256(data).hexdigest()])


def _child_agent(path, row):
    native_agent = row.get("agentId") or row.get("agent_id") or "unknown"
    native_session = row.get("sessionId") or row.get("session_id") or "unknown"
    raw = canonical([path.stem, native_agent, native_session])
    short = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"child:{path.stem[:64]}:{str(native_agent)[:64]}:{str(native_session)[:64]}:{short}"[:256]


def _https_transport(url, headers, timeout):
    """Default HTTPS GET for the Claude usage probe; tests inject a fake instead."""
    import urllib.request
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(65537)


def _private_file(fd, label):
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
            stat.S_IMODE(info.st_mode) & 0o077):
        raise PermissionError(f"watch {label} must be an owner-only regular file")


class UsageWatcher:
    def __init__(self, config, *, address, send, limit_transport=_https_transport):
        Contracts().validate("usage-watch-config", config)
        self.config, self.address, self.send = config, address, send
        self.limit_transport = limit_transport
        self._last_probe = None
        self.max_chunk = config.get("max_chunk_bytes", DEFAULT_CHUNK)
        self.max_files = config.get("max_files", 128)
        cursor = Path(config["cursor_path"]).absolute()
        resolved_cursor = cursor.resolve(strict=False)
        if resolved_cursor == ROOT or ROOT in resolved_cursor.parents:
            raise ValueError("usage watcher cursor must be outside the repository")
        _directory(cursor.parent)
        if cursor.parent.stat().st_mode & 0o077:
            raise PermissionError("watch cursor directory must be private")
        lock_fd = os.open(str(cursor) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            _private_file(lock_fd, "lock")
        except BaseException:
            os.close(lock_fd)
            raise
        self.lock = os.fdopen(lock_fd, "r+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError("usage watcher already owns this cursor") from None
        try:
            fd = os.open(cursor, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                _private_file(fd, "cursor")
            finally:
                os.close(fd)
            self.db = sqlite3.connect(cursor)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS watch_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS watch_cursors
                  (path TEXT PRIMARY KEY, identity TEXT NOT NULL, dev INTEGER NOT NULL,
                   ino INTEGER NOT NULL, offset INTEGER NOT NULL, skipping INTEGER NOT NULL,
                   signature TEXT, coverage TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS watch_pending
                  (path TEXT NOT NULL, ordinal INTEGER NOT NULL, operation_id TEXT NOT NULL,
                   payload TEXT NOT NULL, next_state TEXT NOT NULL,
                   PRIMARY KEY(path,ordinal));
                CREATE TABLE IF NOT EXISTS watch_requests
                  (provider TEXT NOT NULL, project_id TEXT NOT NULL, session_id TEXT NOT NULL,
                   agent_id TEXT NOT NULL, request_id TEXT NOT NULL, body TEXT NOT NULL,
                   PRIMARY KEY(provider,project_id,session_id,agent_id,request_id));
            """)
            old = self.db.execute("SELECT value FROM watch_meta WHERE key='project'").fetchone()
            if old and old[0] != config["project_id"]:
                raise ValueError("watch cursor belongs to a different project")
            self.db.execute("INSERT OR IGNORE INTO watch_meta VALUES('project',?)", (config["project_id"],))
            self.db.commit()
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self.lock.close()
            raise

    def close(self):
        self.db.close()
        self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _sources(self):
        result, unavailable = [], 0
        for spec in self.config["sources"]:
            try:
                candidates = []
                if "session_file" in spec:
                    main = Path(spec["session_file"]).absolute()
                    candidates.append((main, spec, spec["session_id"], spec["agent_id"], False))
                    if spec.get("discover_children"):
                        children = main.with_suffix("") / "subagents"
                        if children.exists():
                            for path in _entries(children, self.max_files):
                                candidates.append((path, spec, spec["session_id"], path.stem, True))
                elif "spool_dir" in spec:
                    for path in _spool_entries(Path(spec["spool_dir"]).absolute(), self.max_files):
                        candidates.append((path, spec, None, "evaluator", False))
                else:
                    directory = Path(spec["sessions_dir"]).absolute()
                    for main in _entries(directory, self.max_files):
                        session = main.stem
                        candidates.append((main, spec, session, "executive", False))
                        if spec.get("discover_children"):
                            children = main.with_suffix("") / "subagents"
                            if children.exists():
                                for path in _entries(children, self.max_files):
                                    candidates.append((path, spec, session, path.stem, True))
                        if len(result) + len(candidates) > self.max_files:
                            raise ValueError("usage watch source count exceeds max_files")
                if len(result) + len(candidates) > self.max_files:
                    raise ValueError("usage watch source count exceeds max_files")
            except (OSError, ValueError):
                unavailable += 1
                continue
            result.extend(candidates)
        return result, unavailable

    def _send(self, operation_id, payload):
        command = {"schema_version": 1, "operation_id": operation_id,
                   "action": "usage_import", "payload": payload}
        response = self.send(self.address, {"surface": "terminal", "command": command})
        if not isinstance(response, dict) or "error" in response:
            raise RuntimeError("usage service refused import; cursor unchanged")
        Contracts().validate("gateway-receipt", response)
        if response["operation_id"] != operation_id:
            raise RuntimeError("usage service returned wrong operation identity")

    def _pending(self, path):
        return self.db.execute("SELECT * FROM watch_pending WHERE path=? ORDER BY ordinal", (str(path),)).fetchall()

    def _flush(self, path):
        batches = self._pending(path)
        if not batches:
            return 0
        for batch in batches:
            self._send(batch["operation_id"], strict_loads(batch["payload"]))
        next_state = strict_loads(batches[0]["next_state"])
        with self.db:
            for batch in batches:
                for observation in strict_loads(batch["payload"])["observations"]:
                    if observation["kind"] != "request":
                        continue
                    key = self._request_key(observation)
                    self.db.execute("""INSERT INTO watch_requests VALUES(?,?,?,?,?,?)
                        ON CONFLICT(provider,project_id,session_id,agent_id,request_id)
                        DO UPDATE SET body=excluded.body""", (*key, canonical(observation)))
            self.db.execute("""INSERT INTO watch_cursors VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(path) DO UPDATE SET identity=excluded.identity,dev=excluded.dev,
                ino=excluded.ino,offset=excluded.offset,skipping=excluded.skipping,
                signature=excluded.signature,coverage=excluded.coverage""",
                (str(path), next_state["identity"], next_state["dev"], next_state["ino"],
                 next_state["offset"], int(next_state["skipping"]), next_state.get("signature"),
                 canonical(next_state.get("coverage", {}))))
            self.db.execute("DELETE FROM watch_pending WHERE path=?", (str(path),))
        return len(batches)

    @staticmethod
    def _request_key(item):
        return tuple(item[name] for name in
                     ("provider", "project_id", "session_id", "agent_id", "request_id"))

    def _revisions(self, observations):
        """Advance only monotonic request samples; quarantine mixed regressions.

        High-water records are committed with the byte cursor after the socket
        acknowledgment, so a lost reply replays exactly the same pending batch.
        """
        accepted, local = [], {}
        invalid = 0
        for item in observations:
            if item["kind"] != "request":
                accepted.append(item)
                continue
            key = self._request_key(item)
            old = local.get(key)
            if old is None:
                row = self.db.execute("""SELECT body FROM watch_requests WHERE provider=?
                    AND project_id=? AND session_id=? AND agent_id=? AND request_id=?""", key).fetchone()
                old = strict_loads(row[0]) if row else None
            if old is not None:
                if any(old[name] is not None and item[name] != old[name]
                       for name in ("model", "scope", "loop_id", "stage_id")):
                    invalid += 1
                    continue
                grew = shrank = False
                for name in ("uncached_input", "cache_read", "cache_write", "output"):
                    before, after = old["tokens"][name], item["tokens"][name]
                    grew |= after is not None and (before is None or after > before)
                    shrank |= before is not None and (after is None or after < before)
                if shrank:
                    if grew:
                        invalid += 1
                    continue
                changed = (grew or item["model"] != old["model"] or
                           item["loop_id"] != old["loop_id"] or
                           item["stage_id"] != old["stage_id"])
                if not changed:
                    continue
                item["revision"] = old["revision"] + 1
            local[key] = item
            accepted.append(item)
        return accepted, invalid

    def _queue(self, path, identity, state, observations, coverage):
        source_id = str(path)
        if len(source_id) > 512:
            raise ValueError("usage source path exceeds service source ID bound")
        batches = [observations[n:n + 128] for n in range(0, len(observations), 128)] or [[]]
        payloads = []
        for index, items in enumerate(batches):
            payload = {"project": self.config["project_id"], "source_id": source_id,
                       "observations": items}
            if index == len(batches) - 1:
                payload["coverage"] = coverage
            if len(canonical(payload).encode()) > MAX_COMMAND_BYTES:
                raise ValueError("normalized usage batch exceeds service bound")
            payloads.append(payload)
        with self.db:
            for index, payload in enumerate(payloads):
                operation = _ulid_from_digest({"watch": str(path), "identity": identity,
                                               "state": state, "batch": index,
                                               "payload": payload})
                self.db.execute("INSERT INTO watch_pending VALUES(?,?,?,?,?)",
                                (str(path), index, operation, canonical(payload), canonical(state)))
        return self._flush(path)

    def _parse_lines(self, path, spec, session_id, agent_id, child, lines, turn,
                     native_thread=None, native_model=None):
        observations = []
        malformed = unidentified = aggregates = 0
        for raw in lines:
            try:
                row = strict_loads(raw.decode("utf-8"))
                if not isinstance(row, dict):
                    raise ValueError("nonobject JSONL row")
                if "spool_dir" in spec and row.get("type") == "thread.started":
                    native_thread = row.get("thread_id") if isinstance(row.get("thread_id"), str) and row["thread_id"] else None
                    native_model = row.get("model") if isinstance(row.get("model"), str) else None
                    turn = 0
                elif "spool_dir" in spec and native_thread and isinstance(row.get("model"), str):
                    native_model = row["model"]
                if "spool_dir" in spec and row.get("type") in ("turn.completed", "result") and isinstance(row.get("usage"), dict) and not native_thread:
                    unidentified += 1
                    continue
                collector = usage_from_claude_jsonl if spec["provider"] == "claude" else usage_from_codex_jsonl
                args = {"project_id": self.config["project_id"],
                        "session_id": native_thread if "spool_dir" in spec else session_id,
                        "agent_id": agent_id, "loop_id": spec.get("loop_id"),
                        "stage_id": spec.get("stage_id")}
                if spec["provider"] == "codex":
                    args["usage_semantics"] = spec.get("usage_semantics", "per_turn")
                    if "spool_dir" in spec:
                        args["model"] = native_model
                    if row.get("type") == "turn.started":
                        turn += 1
                    elif row.get("type") == "turn.completed" and not row.get("turn_id") and not row.get("request_id"):
                        row = {**row, "turn_id": f"watch-turn:{turn}"}
                result = collector([row], **args)
                for item in result["observations"]:
                    if child:
                        native_session = row.get("sessionId") or row.get("session_id")
                        if not isinstance(native_session, str) or not native_session:
                            unidentified += 1
                            continue
                        item["agent_id"] = _child_agent(path, row)
                        item["source"] = ("claude_jsonl:subagents_dir:" + session_id)[:256]
                        item["loop_id"] = None
                        item["stage_id"] = None
                    observations.append(item)
                coverage = result["coverage"]
                unidentified += coverage.get("unidentified_usage", 0)
                aggregates += coverage.get("aggregate_usage", 0)
            except (ValueError, TypeError, UnicodeError, ValidationError):
                malformed += 1
        return observations, malformed, unidentified, aggregates, turn, native_thread, native_model

    def _file(self, path, spec, session_id, agent_id, child):
        self._flush(path)
        identity = canonical({"provider": spec["provider"], "project": self.config["project_id"],
                              "session": session_id, "agent": agent_id, "child": child,
                              "loop": spec.get("loop_id"), "stage": spec.get("stage_id"),
                              "semantics": spec.get("usage_semantics", "per_turn")})
        old = self.db.execute("SELECT * FROM watch_cursors WHERE path=?", (str(path),)).fetchone()
        if old and old["identity"] != identity:
            raise ValueError("usage source identity changed; use a separate cursor")
        try:
            fd, info = _regular(path)
        except OSError:
            return "unavailable"
        try:
            try:
                rotated = bool(old and (old["dev"] != info.st_dev or old["ino"] != info.st_ino or info.st_size < old["offset"]))
                if old and not rotated and old["signature"]:
                    prefix_length = strict_loads(old["signature"])[0]
                    rotated = _prefix_signature(fd, prefix_length) != old["signature"]
                offset = 0 if rotated or not old else old["offset"]
                skipping = False if rotated or not old else bool(old["skipping"])
                raw = os.pread(fd, self.max_chunk, offset)
                after = os.fstat(fd)
            except OSError:
                return "unavailable"
            if (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino) or after.st_size < offset:
                return "changed"
        finally:
            os.close(fd)
        if not raw:
            return "idle"
        prefix_advanced = 0
        if skipping:
            where = raw.find(b"\n")
            if where < 0:
                consumed, lines, skipping = len(raw), [], True
            else:
                consumed = where + 1
                raw = raw[consumed:]
                offset += consumed
                prefix_advanced = consumed
                skipping = False
                consumed = 0
        else:
            consumed = 0
        if not skipping and raw:
            end = raw.rfind(b"\n")
            if end >= 0:
                consumed += end + 1
                lines = raw[:end + 1].splitlines()
            elif len(raw) == self.max_chunk:
                consumed += len(raw)
                lines, skipping = [], True
            else:
                consumed, lines = 0, []
        if consumed == 0 and prefix_advanced == 0 and not rotated:
            return "partial"
        previous = strict_loads(old["coverage"]) if old else {}
        turn = 0 if rotated else previous.get("turn", 0)
        native_thread = None if rotated else previous.get("native_thread")
        native_model = None if rotated else previous.get("native_model")
        observations, malformed, unidentified, aggregates, turn, native_thread, native_model = self._parse_lines(
            path, spec, session_id, agent_id, child, lines, turn, native_thread, native_model)
        observations, invalid = self._revisions(observations)
        malformed += invalid
        if skipping and not (old and old["skipping"]):
            malformed += 1
        coverage = {"truncated": bool(previous.get("truncated") or rotated),
                    "malformed_lines": previous.get("malformed_lines", 0) + malformed,
                    "unidentified_usage": previous.get("unidentified_usage", 0) + unidentified,
                    "aggregate_usage": previous.get("aggregate_usage", 0) + aggregates,
                    "complete": False}
        next_state = {"identity": identity, "dev": info.st_dev, "ino": info.st_ino,
                      "offset": offset + consumed, "skipping": skipping,
                      "coverage": coverage | {"turn": turn, "native_thread": native_thread,
                                              "native_model": native_model}}
        try:
            check_fd, check_info = _regular(path)
        except OSError:
            return "unavailable"
        try:
            if ((check_info.st_dev, check_info.st_ino) != (info.st_dev, info.st_ino) or
                    check_info.st_size < next_state["offset"]):
                return "changed"
            next_state["signature"] = _prefix_signature(
                check_fd, min(PREFIX_BYTES, next_state["offset"]))
        except OSError:
            return "changed"
        finally:
            os.close(check_fd)
        self._queue(path, identity, next_state, observations, coverage)
        return "imported"

    def _status(self, item):
        path = Path(item["path"]).absolute()
        self._flush(path)
        identity = canonical({"status": self.config["project_id"], **item})
        old = self.db.execute("SELECT * FROM watch_cursors WHERE path=?", (str(path),)).fetchone()
        if old and old["identity"] != identity:
            raise ValueError("status source identity changed; use a separate cursor")
        try:
            fd, info = _regular(path)
        except OSError:
            return "unavailable"
        try:
            try:
                if info.st_size > 65536:
                    raise ValueError("status sample exceeds 64 KiB")
                raw = os.pread(fd, 65537, 0)
                after = os.fstat(fd)
            except OSError:
                return "unavailable"
            if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                return "changed"
        finally:
            os.close(fd)
        signature = canonical([info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns])
        if old and old["signature"] == signature:
            return "idle"
        if len(raw) != info.st_size:
            return "changed"
        try:
            native = strict_loads(raw)
            if not isinstance(native, dict) or native.get("session_id") != item["session_id"]:
                return "invalid"
            sample = normalize_claude_status(native, project_id=self.config["project_id"],
                session_id=item["session_id"], agent_id=item["agent_id"],
                account_id=item["account_id"], observed_at=_status_time(info))
        except (ValueError, ValidationError):
            # A partial/malformed status file must not refresh account quota.
            return "invalid"
        next_state = {"identity": identity, "dev": info.st_dev, "ino": info.st_ino,
                      "offset": info.st_size, "skipping": False, "signature": signature,
                      "coverage": {"truncated": False, "malformed_lines": 0, "complete": False}}
        self._queue(path, identity, next_state, [sample],
                    {"truncated": False, "malformed_lines": 0, "complete": False})
        return "imported"

    def _probe_limits(self):
        """Label-keyed account limit samples; stateless, sent without byte cursors.

        Failures are recorded as unavailable samples and never touch the
        status-file cursors or the existing claude status samples.
        """
        probes = self.config.get("limit_probes")
        if not probes:
            return 0
        interval = probes.get("interval_seconds", 300)
        current = time.monotonic()
        if self._last_probe is not None and current - self._last_probe < interval:
            return 0
        self._last_probe = current
        project = self.config["project_id"]
        samples = []
        if "claude_config_dir" in probes:
            samples += probe_claude_limits(probes["claude_config_dir"], project_id=project,
                                           transport=self.limit_transport)
        if "codex_home" in probes:
            samples += probe_codex_limits(probes["codex_home"], project_id=project)
        for sample in samples:
            operation = _ulid_from_digest({"limit_probe": sample["label"], "observed_at": sample["observed_at"],
                                           "status": sample["status"]})
            self._send(operation, {"project": project, "source_id": "probe:" + sample["provider"],
                                   "observations": [sample]})
        return len(samples)

    def poll(self):
        counts = {"imported": 0, "idle": 0, "partial": 0, "unavailable": 0, "changed": 0, "invalid": 0}
        sources, counts["unavailable"] = self._sources()
        for path, spec, session_id, agent_id, child in sources:
            result = self._file(path, spec, session_id, agent_id, child)
            counts[result] += 1
        for item in self.config.get("status_files", []):
            result = self._status(item)
            counts[result] += 1
        if self.config.get("limit_probes"):
            counts["limit_samples"] = self._probe_limits()
        return counts


def run_cli(args, state, address, send, parser):
    if not args.request:
        parser.error("usage-watch requires --request configuration JSON")
    from .usage_cli import _json_file
    config, _ = _json_file(args.request, 65536)
    Contracts().validate("usage-watch-config", config)
    with UsageWatcher(config, address=address, send=send) as watcher:
        while True:
            print(canonical(watcher.poll()), flush=True)
            if args.once:
                return 0
            time.sleep(config.get("poll_seconds", 15))
