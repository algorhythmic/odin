"""Pinned deploy copies of reviewed commits (ODIN-ADR-039, item 7).

The service, hooks, status line, MCP bridge and launcher run from
``<deploy root>/current``, a symlink to ``<deploy root>/<revision>``: a
read-only export of one commit with a marker naming the revision and the
repository it serves. A merge into the checkout therefore changes no running
or newly started process until a deploy switches ``current``. Switching is one
atomic rename of a symlink. A bounded number of previous copies is kept, and
``current`` and the rollback target are never removed.
"""
import io
import os
import re
import secrets
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path

from .contracts import DEPLOYMENT_FILE, REPOSITORY_ROOT, canonical, deployment
from .store import now

CURRENT = "current"
REVISION = re.compile(r"[0-9a-f]{40}")
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


class DeployError(Exception):
    """A fixed code; nothing outside the deploy root was changed."""


def private_root(value):
    """The deploy root: absolute, no symlinked component, owned, mode 0700."""
    path = Path(value)
    if not path.is_absolute() or os.path.normpath(value) != str(value):
        raise DeployError("deploy_root_invalid")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise DeployError("deploy_root_invalid")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise DeployError("deploy_root_invalid")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise DeployError("deploy_root_not_private")
    return path


def current_revision(root):
    """The revision ``current`` points at, or None when there is no link."""
    link = Path(root) / CURRENT
    if not link.is_symlink():
        return None
    target = os.readlink(link)
    if not REVISION.fullmatch(target):
        raise DeployError("deploy_current_invalid")
    return target


def _git_archive(repository, revision):
    result = subprocess.run(["git", "-C", str(repository), "archive", "--format=tar", revision],
                            capture_output=True, timeout=300, check=False)
    if result.returncode != 0 or len(result.stdout) > MAX_ARCHIVE_BYTES:
        raise DeployError("deploy_export_failed")
    return result.stdout


def _read_only(path):
    for directory, names, files in os.walk(path, topdown=False):
        for name in files:
            target = Path(directory) / name
            if not target.is_symlink():
                mode = target.stat().st_mode
                target.chmod(mode & ~0o222 & 0o755)
        Path(directory).chmod(0o555)


def _writable(path):
    for directory, _names, _files in os.walk(path):
        Path(directory).chmod(0o700)


def export(root, repository, revision):
    """Export ``revision`` of ``repository`` to ``<root>/<revision>``; idempotent.

    The archive is extracted with tarfile's data filter (no absolute paths,
    links out of the tree or device files) into a temporary directory, given
    its marker, made read-only and renamed into place.
    """
    if not REVISION.fullmatch(revision or ""):
        raise DeployError("deploy_revision_invalid")
    root = private_root(root)
    target = root / revision
    if target.exists():
        marker = deployment(target)
        if marker is None or marker["revision"] != revision or marker["repository"] != str(repository):
            raise DeployError("deploy_copy_mismatch")
        return target
    temporary = root / f".{revision}.{secrets.token_hex(6)}"
    temporary.mkdir(mode=0o700)
    try:
        try:
            with tarfile.open(fileobj=io.BytesIO(_git_archive(repository, revision)), mode="r:") as archive:
                archive.extractall(temporary, filter="data")
        except tarfile.TarError as error:
            raise DeployError("deploy_export_unsafe") from error
        marker = {"schema_version": 1, "revision": revision, "repository": str(repository),
                  "exported_at": now()}
        # Never follow a committed file or link of the same name.
        try:
            fd = os.open(temporary / DEPLOYMENT_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
        except FileExistsError:
            raise DeployError("deploy_marker_invalid") from None
        with os.fdopen(fd, "w") as handle:
            handle.write(canonical(marker) + "\n")
        if deployment(temporary) != marker:
            raise DeployError("deploy_marker_invalid")
        _read_only(temporary)
        temporary.chmod(0o700)
        os.rename(temporary, target)
        target.chmod(0o555)
    except BaseException:
        if temporary.exists():
            _writable(temporary)
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return target


def switch(root, revision):
    """Point ``current`` at ``revision`` with one atomic rename; returns the previous revision."""
    root = Path(root)
    copy = root / revision
    marker = deployment(copy) if copy.is_dir() else None
    if marker is None or marker["revision"] != revision:
        raise DeployError("deploy_copy_missing")
    previous = current_revision(root)
    temporary = root / f".{CURRENT}.{secrets.token_hex(6)}"
    os.symlink(revision, temporary)
    try:
        os.replace(temporary, root / CURRENT)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return previous


def copies(root):
    """Exported revisions under the root, oldest first (by marker export time)."""
    found = []
    for path in Path(root).iterdir():
        if REVISION.fullmatch(path.name) and path.is_dir() and not path.is_symlink():
            try:
                marker = deployment(path)
            except (OSError, ValueError):
                continue
            if marker and marker["revision"] == path.name:
                found.append((marker["exported_at"], path.name))
    return [name for _stamp, name in sorted(found)]


def prune(root, keep, *, protect=()):
    """Keep the newest ``keep`` previous copies, plus ``current`` and ``protect``."""
    root = Path(root)
    current = current_revision(root)
    protected = {current, *protect} - {None}
    names = [name for name in copies(root) if name != current]
    removable = [name for name in names[:max(0, len(names) - keep)] if name not in protected]
    for name in removable:
        _writable(root / name)
        shutil.rmtree(root / name)
    return removable


CONFIG_FILE = "deploy.json"


def configure(state, *, repository, branch, deploy_root=None, keep=3, drain_timeout_seconds=3600):
    """Operator-only: record where deploys come from and go; returns the record.

    ``repository`` is the canonical checkout (the executive's repository) and
    ``branch`` the integration branch whose head alone may be deployed.
    """
    from .executive_runtime import _private_directory, _write

    state = _private_directory(state)
    base = _private_directory(state / "executive-pilot")
    repository = Path(repository)
    if not repository.is_absolute() or not (repository / ".git").exists():
        raise DeployError("deploy_repository_invalid")
    repository = repository.resolve()
    if repository != REPOSITORY_ROOT:
        raise DeployError("deploy_repository_mismatch")
    root = Path(deploy_root) if deploy_root else state.parent / "deploy"
    for other in (repository, state):
        if root == other or root.is_relative_to(other) or other.is_relative_to(root):
            raise DeployError("deploy_root_invalid")
    private_root(root)
    value = {"schema_version": 1, "repository": str(repository), "branch": branch,
             "deploy_root": str(root), "keep": keep, "drain_timeout_seconds": drain_timeout_seconds}
    _write(base / CONFIG_FILE, "executive-deploy-config", value)
    return value


def read_config(state):
    """The validated deploy configuration, or None when not configured."""
    from .executive_runtime import _read

    path = Path(state) / "executive-pilot" / CONFIG_FILE
    return _read(path, "executive-deploy-config") if path.exists() else None


def integration_problem(config, head):
    """The fixed code refusing ``head``, or None when it is the clean integration head."""
    from .service_activation import _checkout, _git

    try:
        tip = _git(config["repository"], "rev-parse", "--verify", "--quiet",
                   "refs/heads/" + config["branch"]).strip()
    except (OSError, subprocess.SubprocessError):
        return "deploy_checkout_unreadable"
    if tip != head:
        return "deploy_head_not_integration_head"
    problem = _checkout(config["repository"], branch=config["branch"], head=head)
    return {None: None, "checkout_not_clean": "deploy_tree_dirty",
            "checkout_wrong_branch": "deploy_checkout_not_on_integration_branch",
            "checkout_wrong_head": "deploy_head_not_integration_head"}.get(
                problem, "deploy_checkout_unreadable")


def prepare(state, *, head):
    """Operator-only, for the one-time migration: export ``head`` and point
    ``current`` at it without restarting anything. Only the clean integration
    head is accepted, as for a deploy."""
    config = read_config(state)
    if config is None:
        raise DeployError("deploy_not_configured")
    problem = integration_problem(config, head)
    if problem:
        raise DeployError(problem)
    export(config["deploy_root"], config["repository"], head)
    previous = switch(config["deploy_root"], head)
    return {"current": head, "previous": previous, "deploy_root": config["deploy_root"],
            "restarted": False}
