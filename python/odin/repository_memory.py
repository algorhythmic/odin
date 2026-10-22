"""Explicit committed-repository snapshots through the service's sole writer.

Preparation reads Git objects, never worktree contents, credentials or untracked
files. Import is trusted operator plumbing, not a model tool. Sources are exact
text evidence; no statements, approvals or completion claims are inferred.
"""

from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path, PurePosixPath

from .contracts import Contracts, canonical, strict_loads
from .memory import Memory
from .store import Conflict, now

PRODUCER = "odin.repository-snapshot"
READERS = ["fable-executive", "local-operator"]
CHUNK_BYTES = 6000
BATCH_SIZE = 24
MAX_BATCHES = 64
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024


def _digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _allowed(path):
    parts = PurePosixPath(path).parts
    if (
        not parts
        or PurePosixPath(path).is_absolute()
        or any(p in {".", ".."} or p.startswith(".") for p in parts)
        or str(PurePosixPath(path)) != path
        or len(path) > 384
    ):
        return False
    if any(
        part.lower()
        in {
            "logs",
            "conversations",
            "sessions",
            "workspaces",
            "state",
            "cache",
            "dumps",
            "credentials",
            "secrets",
        }
        for part in parts
    ):
        return False
    if PurePosixPath(path).suffix in {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".txt",
    } and any(
        word in parts[-1].lower() for word in ("credential", "secret", "token", "auth.")
    ):
        return False
    if path in {
        "README.md",
        "AGENTS.md",
        "Makefile",
        "requirements.txt",
        "go.mod",
        "go.sum",
    }:
        return True
    if parts[0] not in {
        "docs",
        "python",
        "tests",
        "schemas",
        "scripts",
        "internal",
        "cmd",
    }:
        return False
    if parts[0] == "python" and (len(parts) < 3 or parts[1] != "odin"):
        return False
    if (
        parts[0] == "docs"
        and len(parts) > 1
        and parts[1] in {"history", "research", "contracts"}
    ):
        return False
    return PurePosixPath(path).suffix in {
        ".md",
        ".py",
        ".go",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".txt",
    }


def _git(repository, *args):
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
    ).stdout


def _chunks(raw):
    """Keep complete lines where possible; long lines split on UTF-8 boundaries."""
    start, line, chunk = 0, 1, 0
    while start < len(raw):
        end = min(start + CHUNK_BYTES, len(raw))
        if end < len(raw):
            newline = raw.rfind(b"\n", start, end)
            if newline >= start:
                end = newline + 1
            else:
                while end > start and raw[end] & 0xC0 == 0x80:
                    end -= 1
        content = raw[start:end].decode("utf-8")
        end_line = line + content.count("\n") - int(content.endswith("\n"))
        yield {
            "chunk": chunk,
            "byte_start": start,
            "byte_end": end,
            "line_start": line,
            "line_end": end_line,
            "content": content,
            "digest": sha256(raw[start:end]).hexdigest(),
        }
        line += content.count("\n")
        start, chunk = end, chunk + 1


def _snapshot_id(payload):
    return _digest(
        {
            k: payload[k]
            for k in ("project", "repository", "commit", "file_count", "batch_digests")
        }
    )


def prepare(repository, project):
    """Return bounded operator-upload batches from one explicit Git root's HEAD.

    Fails closed on binary/oversize selected files. Empty text files are omitted.
    Git symlinks and submodules, frozen history, peer contracts and untracked or
    modified worktree bytes are never read into memory.
    """
    repository = Path(repository).resolve(strict=True)
    top = Path(
        _git(repository, "rev-parse", "--show-toplevel").decode().strip()
    ).resolve()
    if top != repository:
        raise ValueError("select the repository root explicitly")
    commit = _git(repository, "rev-parse", "HEAD").decode().strip()
    tree = _git(repository, "ls-tree", "-r", "-l", "-z", commit)
    entries, file_count, total = [], 0, 0
    for row in tree.split(b"\0"):
        if not row:
            continue
        metadata, raw_path = row.split(b"\t", 1)
        path = raw_path.decode("utf-8")
        mode, kind, oid, size = metadata.split()
        if mode not in {b"100644", b"100755"} or kind != b"blob" or not _allowed(path):
            continue
        count = int(size)
        if not count:
            continue
        total += count
        if count > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("selected repository text exceeds snapshot bounds")
        raw = _git(repository, "cat-file", "blob", oid.decode())
        if len(raw) != count or b"\0" in raw:
            raise ValueError(f"selected repository file is not plain text: {path}")
        raw.decode("utf-8")
        file_count += 1
        for entry in _chunks(raw):
            entries.append(
                entry | {"path": path, "file_digest": sha256(raw).hexdigest()}
            )
    if not entries:
        raise ValueError("no selected committed repository text")
    groups, group, catalog_bytes = [], [], 0
    for entry in entries:
        ref_size = (
            len(
                canonical(
                    {
                        "id": source_id(project, entry["path"], entry["chunk"]),
                        "revision": 9223372036854775807,
                        **{
                            k: entry[k]
                            for k in (
                                "path",
                                "chunk",
                                "line_start",
                                "line_end",
                                "digest",
                                "file_digest",
                            )
                        },
                    }
                )
            )
            + 1
        )
        if group and (len(group) == BATCH_SIZE or catalog_bytes + ref_size > 7000):
            groups.append(group)
            group, catalog_bytes = [], 0
        group.append(entry)
        catalog_bytes += ref_size
    if group:
        groups.append(group)
    if len(groups) > MAX_BATCHES or file_count > 1024:
        raise ValueError("selected repository text exceeds catalog bounds")
    common = {
        "schema_version": 1,
        "project": project,
        "repository": str(repository),
        "commit": commit,
        "captured_at": now(),
        "file_count": file_count,
        "batch_digests": [_digest(group) for group in groups],
    }
    common["snapshot_id"] = _snapshot_id(common)
    batches = [
        common | {"batch_index": i, "entries": group} for i, group in enumerate(groups)
    ]
    contracts = Contracts()
    for payload in batches:
        contracts.validate("repository-import", payload)
    return batches


def source_id(project, path, chunk=0):
    """Stable across snapshots and commits for a project's file/chunk identity."""
    return "repository:file:" + _digest([project, path, chunk])[:32]


def catalog_id(project):
    # Sort before file evidence, so even a bounded memory snapshot shows discovery.
    return "000:repository:catalog:" + _digest(project)[:24]


def _page_id(project, index):
    return "001:repository:page:" + _digest(project)[:24] + f":{index:03d}"


def _put(memory, payload, sid, content, locator, source_class):
    store = memory.store
    digest = sha256(content.encode()).hexdigest()
    row = store.db.execute(
        "SELECT body,redacted FROM memory_sources WHERE id=? ORDER BY revision DESC LIMIT 1",
        (sid,),
    ).fetchone()
    old = strict_loads(row[0]) if row else None
    if (
        old
        and store.db.execute(
            "SELECT 1 FROM memory_sources WHERE id=? AND redacted=1 LIMIT 1", (sid,)
        ).fetchone()
    ):
        raise Conflict("redacted repository source cannot be reused")
    if old and (old["readers"] != READERS or old["producer"] != PRODUCER):
        raise Conflict("repository source access or producer changed")
    if old and old["project"] != payload["project"]:
        raise Conflict("repository source scope changed")
    # Exact unchanged file bytes retain their original evidence revision/locator.
    # The current catalog attests which pinned commit contains the same bytes.
    if old and old["digest"] == digest and old["readers"] == READERS:
        return {"id": sid, "revision": old["revision"]}, False
    seq = store.db.execute(
        "SELECT COALESCE(MAX(ingest_seq),0)+1 FROM memory_sources WHERE project=? AND producer=?",
        (payload["project"], PRODUCER),
    ).fetchone()[0]
    stamp = payload["captured_at"]
    source = {
        "id": sid,
        "project": payload["project"],
        "revision": old["revision"] + 1 if old else 1,
        "digest": digest,
        "producer": PRODUCER,
        "source_class": source_class,
        "locator": locator,
        "span": None,
        "readers": READERS,
        "permissions_revision": old["permissions_revision"] if old else 1,
        "event_at": None,
        "effective_at": None,
        "observed_at": stamp,
        "retrieved_at": stamp,
        "ingest_seq": seq,
        "content": content,
    }
    memory.add_source(source)
    memory.processing(payload["project"], PRODUCER, processed=seq)
    return {"id": sid, "revision": source["revision"]}, True


def import_batch(store, payload, *, project):
    """Trusted service operation; caller enforces operator identity and scope.

    Participates in the caller's transaction. Replay does not add revisions;
    invalid, altered or out-of-order batches roll back completely.
    """
    store.contracts.validate("repository-import", payload)
    if payload["project"] != project:
        raise PermissionError("repository import outside project scope")
    index = payload["batch_index"]
    if (
        index >= len(payload["batch_digests"])
        or _digest(payload["entries"]) != payload["batch_digests"][index]
        or _snapshot_id(payload) != payload["snapshot_id"]
    ):
        raise Conflict("repository snapshot digest mismatch")
    seen = set()
    for entry in payload["entries"]:
        identity = (entry["path"], entry["chunk"])
        data = entry["content"].encode()
        if (
            not _allowed(entry["path"])
            or identity in seen
            or b"\0" in data
            or len(data) > CHUNK_BYTES
            or len(data) != entry["byte_end"] - entry["byte_start"]
            or entry["line_end"] < entry["line_start"]
            or sha256(data).hexdigest() != entry["digest"]
        ):
            raise Conflict("invalid repository evidence chunk")
        seen.add(identity)
    memory = Memory(store)
    memory._project(project)
    with store.transaction():
        store.db.execute("""CREATE TABLE IF NOT EXISTS repository_import_batches(
            project TEXT NOT NULL, snapshot TEXT NOT NULL, batch INTEGER NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL,
            PRIMARY KEY(project,snapshot,batch))""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS repository_import_current(
            project TEXT PRIMARY KEY, snapshot TEXT NOT NULL, complete INTEGER NOT NULL,
            repository TEXT NOT NULL)""")
        key = (project, payload["snapshot_id"])
        fingerprint = _digest({k: v for k, v in payload.items() if k != "captured_at"})
        current = store.db.execute(
            "SELECT snapshot,complete,repository FROM repository_import_current WHERE project=?",
            (project,),
        ).fetchone()
        if current and current[2] != payload["repository"]:
            raise Conflict("project repository binding cannot change")
        existing = store.db.execute(
            "SELECT fingerprint,result FROM repository_import_batches WHERE project=? AND snapshot=? AND batch=?",
            (*key, index),
        ).fetchone()
        if existing:
            if current and current[0] != key[1]:
                raise Conflict(
                    "repository snapshot was superseded; prepare the current HEAD"
                )
            if existing[0] != fingerprint:
                raise Conflict("repository batch identity reused")
            return strict_loads(existing[1])
        if current and current[0] != key[1] and not current[1]:
            raise Conflict(
                "finish the prior repository snapshot before importing another"
            )
        previous = store.db.execute(
            "SELECT result FROM repository_import_batches WHERE project=? AND snapshot=? ORDER BY batch",
            key,
        ).fetchall()
        if index != len(previous):
            raise Conflict("repository batches must be imported in order")
        refs, added = [], 0
        for entry in payload["entries"]:
            locator = (
                f"git:{payload['repository']}@{payload['commit']}:{entry['path']}"
                f"#L{entry['line_start']}-L{entry['line_end']};bytes={entry['byte_start']}:{entry['byte_end']}"
            )
            ref, changed = _put(
                memory,
                payload,
                source_id(project, entry["path"], entry["chunk"]),
                entry["content"],
                locator,
                "repository_committed_text",
            )
            added += changed
            refs.append(
                ref
                | {
                    k: entry[k]
                    for k in (
                        "path",
                        "chunk",
                        "line_start",
                        "line_end",
                        "digest",
                        "file_digest",
                    )
                }
            )
        page = {
            "schema_version": 1,
            "repository": payload["repository"],
            "commit": payload["commit"],
            "snapshot_id": key[1],
            "entries": refs,
        }
        # Compact catalog entries still carry exact source revision and provenance.
        store.contracts.validate("repository-catalog-page", page)
        page_text = canonical(page)
        if len(page_text) > 8192:
            raise Conflict("repository catalog page exceeds source bound")
        page_ref, _ = _put(
            memory,
            payload,
            _page_id(project, index),
            page_text,
            f"repository-catalog:{key[1]}:page:{index}",
            "repository_catalog",
        )
        pages = [strict_loads(row[0])["page"] for row in previous] + [page_ref]
        complete = len(pages) == len(payload["batch_digests"])
        catalog = {
            "schema_version": 1,
            "repository": payload["repository"],
            "commit": payload["commit"],
            "snapshot_id": key[1],
            "captured_at": payload["captured_at"],
            "coverage": "complete_committed_selection"
            if complete
            else "partial_committed_selection",
            "freshness": "point_in_time_snapshot; does not observe later worktree or commit changes",
            "selection": "committed first-party docs/code/schema/tests; excludes frozen history, peer contracts, research, symlinks, untracked and worktree edits",
            "file_count": payload["file_count"],
            "batches_expected": len(payload["batch_digests"]),
            "batches_imported": len(pages),
            "pages": pages,
        }
        store.contracts.validate("repository-catalog", catalog)
        catalog_ref, _ = _put(
            memory,
            payload,
            catalog_id(project),
            canonical(catalog),
            f"repository-catalog:{key[1]}",
            "repository_catalog",
        )
        memory.processing(
            project,
            PRODUCER,
            availability="available" if complete else "unknown",
            reason="Committed repository snapshot; later filesystem changes are not monitored."
            if complete
            else "Repository snapshot upload is incomplete.",
        )
        result = {
            "project": project,
            "snapshot_id": key[1],
            "commit": payload["commit"],
            "batch_index": index,
            "batch_count": len(payload["batch_digests"]),
            "complete": complete,
            "added_sources": added,
            "source_count": len(refs),
            "catalog": catalog_ref,
            "page": page_ref,
        }
        store.db.execute(
            "INSERT INTO repository_import_batches VALUES(?,?,?,?,?)",
            (*key, index, fingerprint, canonical(result)),
        )
        store.db.execute(
            """INSERT INTO repository_import_current VALUES(?,?,?,?)
            ON CONFLICT(project) DO UPDATE SET snapshot=excluded.snapshot,complete=excluded.complete""",
            (*key, int(complete), payload["repository"]),
        )
        store._history("repository.snapshot_batch", result)
        return result
