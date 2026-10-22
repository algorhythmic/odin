"""Service-only activation: restart the Odin pilot service on a reviewed head.

Activation restarts one systemd user unit and nothing else. It never touches
the executive session, the telemetry unit or delegated workers directly; it
refuses instead when any of them could be interrupted. Every attempt, refused
or not, leaves a private activation record before and after acting.
"""

from __future__ import annotations

import os
import re
import socket
import sqlite3
import subprocess
import time
from pathlib import Path

from .contracts import ROOT, deployment, identifier, strict_loads
from .store import now as _now

UNIT = "odin-executive-pilot-service"
REVISION_FILE = "service-revision.json"
ACTIVATIONS = "service-activations"
ACTIVE_TURN_STATES = ("queued", "launching", "running", "interrupting")


class ActivationRefused(Exception):
    pass




def _git(repository, *argv):
    return subprocess.run(
        ["git", "-C", str(repository), *argv], capture_output=True, text=True,
        timeout=30, check=True,
    ).stdout


def code_revision(repository=ROOT):
    """Head and cleanliness of the checkout this process imports Odin from.

    A deployed copy has no git metadata; its marker names the exported commit,
    and cleanliness is unknown (None) rather than asserted.
    """
    marker = deployment(repository)
    if marker is not None:
        return marker["revision"], None
    try:
        return (_git(repository, "rev-parse", "HEAD").strip(),
                _git(repository, "status", "--porcelain") == "")
    except (OSError, subprocess.SubprocessError):
        return None, None


def record_service_revision(state, *, repository=ROOT, pid=None):
    """Called by `serve` once its sockets are bound: the service's own report."""
    from .executive_runtime import _write

    revision, clean = code_revision(repository)
    value = {"version": 1, "pid": pid or os.getpid(), "revision": revision,
             "clean": clean, "started_at": _now()}
    _write(Path(state) / REVISION_FILE, "service-revision", value)
    return value


def service_revision(state):
    from .executive_runtime import _read

    path = Path(state) / REVISION_FILE
    return _read(path, "service-revision") if path.exists() else None


class SystemdUserUnit:
    """The only process control activation uses: `systemctl --user` on one unit."""

    def __init__(self, unit=UNIT, run=subprocess.run):
        self.unit, self._run = unit, run

    def main_pid(self):
        result = self._run(
            ["systemctl", "--user", "show", "--property=MainPID", "--value", self.unit],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return int(result.stdout.strip() or 0)

    def restart(self):
        self._run(["systemctl", "--user", "restart", self.unit],
                  capture_output=True, text=True, timeout=120, check=True)


def quiescence(state, *, include_queued=True):
    """Read-only view of work a service restart would interrupt.

    During a deploy drain (ODIN-ADR-039) queued turns cannot launch, so a
    deploy passes ``include_queued=False`` and only running turns block.
    """
    path = Path(state) / "odin_history.sqlite3"
    blockers = {"delegated_turns": [], "live_interventions": [], "claimed_loop_stages": []}
    if not path.exists():
        return {"quiescent": True, "blockers": blockers}
    # A read-only URI connection never takes the service's namespace writer lock.
    db = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "delegation_turns" in tables:
            states = ACTIVE_TURN_STATES if include_queued else ACTIVE_TURN_STATES[1:]
            marks = ",".join("?" * len(states))
            blockers["delegated_turns"] = [
                {"turn": row[0], "session": row[1], "state": row[2]}
                for row in db.execute(
                    f"SELECT id, session, state FROM delegation_turns WHERE state IN ({marks}) ORDER BY id",
                    states)]
        if "executive_interventions" in tables:
            from .executive_intervention import _live

            for (body,) in db.execute("SELECT body FROM executive_interventions ORDER BY id"):
                item = strict_loads(body)
                if _live(item) or any(p["state"] == "admitted" for p in item["permits"]):
                    blockers["live_interventions"].append(item["id"])
        if "development_loop_stages" in tables:
            for (body,) in db.execute("SELECT body FROM development_loop_stages ORDER BY id"):
                stage = strict_loads(body)
                if stage["state"] == "claimed":
                    blockers["claimed_loop_stages"].append(stage["id"])
    finally:
        db.close()
    # Records keep a bounded sample; quiescence is decided on the full view.
    return {"quiescent": not any(blockers.values()),
            "blockers": {key: value[:32] for key, value in blockers.items()}}


def _checkout(repository, *, branch, head):
    try:
        observed_branch = _git(repository, "symbolic-ref", "--quiet", "--short", "HEAD").strip()
    except (OSError, subprocess.SubprocessError):
        return "checkout_detached_or_unreadable"
    try:
        observed_head = _git(repository, "rev-parse", "HEAD").strip()
        clean = _git(repository, "status", "--porcelain") == ""
    except (OSError, subprocess.SubprocessError):
        return "checkout_unreadable"
    if observed_branch != branch:
        return "checkout_wrong_branch"
    if observed_head != head:
        return "checkout_wrong_head"
    if not clean:
        return "checkout_not_clean"
    return None


def _directory(state):
    from .executive_runtime import _private_directory

    base = _private_directory(Path(state) / "executive-pilot", create=True)
    return _private_directory(base / ACTIVATIONS, create=True)


def _save(state, record):
    from .executive_runtime import _write

    _write(_directory(state) / f"{record['id']}.json", "executive-service-activation", record)


def last_activation(state):
    from .executive_runtime import _read

    directory = Path(state) / "executive-pilot" / ACTIVATIONS
    if not directory.is_dir():
        return None
    names = sorted(p for p in directory.glob("*.json") if len(p.stem) == 26)
    return _read(names[-1], "executive-service-activation") if names else None


def _default_reachable(state):
    from .executive_runtime import _load, _service_reachability

    try:
        observed = _service_reachability(_load(state)[0])
    except (OSError, ValueError):
        observed = "unchecked"
    if observed != "unchecked":
        return observed == "reachable"
    # Without the executive bridge, a bound operator socket is the signal.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        probe.settimeout(2)
        try:
            probe.connect(str(Path(state) / "service.sock"))
        except OSError:
            return False
    return True


def validate_arguments(*, repository, branch, head):
    """Usage checks that precede any record; a failure here is not a refusal."""
    if not re.fullmatch(r"[0-9a-f]{40}", head or ""):
        raise ValueError("--head must be a full lowercase commit id")
    if not branch or len(branch) > 256 or len(str(Path(repository).absolute())) > 4096:
        raise ValueError("--branch and --repository must be non-empty and bounded")


def activate(state, *, repository, branch, head, controller=None, reachable=None,
             timeout=60.0, clock=time.monotonic, sleep=time.sleep, verify_checkout=True,
             include_queued=True, allow_stopped=False):
    """Restart only the service unit when quiescent and the checkout is reviewed.

    A deploy rollback (ODIN-ADR-039) passes ``verify_checkout=False``: the
    previous revision is no longer the checkout's head, and the record still
    requires the service to report that revision afterwards. It also passes
    ``allow_stopped=True``, so a unit left down by the failed restart is
    started rather than refused as ``unit_not_running``.
    """
    from .executive_runtime import _lease, _LeaseBusy

    validate_arguments(repository=repository, branch=branch, head=head)
    controller = controller or SystemdUserUnit()
    reachable = reachable or _default_reachable
    record = {"version": 1, "id": identifier(), "unit": controller.unit,
              "requested_head": head, "requested_branch": branch,
              "repository": str(Path(repository).absolute()),
              "previous_revision": None, "previous_pid": None,
              "started_at": _now(), "finished_at": None, "outcome": "refused",
              "reason": None, "quiescence": None, "running_revision": None, "running_pid": None}

    def finish(outcome, reason=None):
        record.update(outcome=outcome, reason=reason, finished_at=_now())
        _save(state, record)
        return record

    try:
        with _lease(_directory(state) / "activation.lock"):
            try:
                return _activate(state, record, finish, repository=repository, branch=branch,
                                 head=head, controller=controller, reachable=reachable,
                                 timeout=timeout, clock=clock, sleep=sleep,
                                 verify_checkout=verify_checkout, include_queued=include_queued,
                                 allow_stopped=allow_stopped)
            except Exception:
                # An ordinary error never leaves an unexplained `restarting` record.
                finish("failed", "activation_error")
                raise
    except _LeaseBusy:
        return finish("refused", "activation_in_progress")


def _activate(state, record, finish, *, repository, branch, head, controller,
              reachable, timeout, clock, sleep, verify_checkout=True, include_queued=True,
              allow_stopped=False):
    try:
        previous_pid = controller.main_pid()
    except (OSError, subprocess.SubprocessError, ValueError):
        return finish("refused", "unit_state_unreadable")
    if not previous_pid and not allow_stopped:
        return finish("refused", "unit_not_running")
    record["previous_pid"] = previous_pid or None
    reported = service_revision(state)
    if reported and reported["pid"] == previous_pid:
        record["previous_revision"] = reported["revision"]
    problem = _checkout(repository, branch=branch, head=head) if verify_checkout else None
    if problem:
        return finish("refused", problem)
    # Read quiescence last, just before the restart, to narrow the window in
    # which the running service could admit new work.
    try:
        view = quiescence(state, include_queued=include_queued)
    except (sqlite3.Error, ValueError, KeyError, TypeError):
        return finish("refused", "quiescence_unreadable")
    record["quiescence"] = view
    if not view["quiescent"]:
        first = next(key for key, value in view["blockers"].items() if value)
        return finish("refused", "not_quiescent_" + first)
    # Intent is durable before the unit is touched.
    record["outcome"] = "restarting"
    _save(state, record)
    try:
        controller.restart()
    except (OSError, subprocess.SubprocessError):
        return finish("failed", "restart_failed")
    deadline = clock() + timeout
    while True:
        reported = service_revision(state)
        try:
            pid = controller.main_pid()
        except (OSError, subprocess.SubprocessError, ValueError):
            pid = 0
        if (pid and pid != previous_pid and reported and reported["pid"] == pid
                and reachable(state)):
            break
        if clock() >= deadline:
            return finish("failed", "service_unreachable_or_unreported")
        sleep(0.5)
    record.update(running_revision=reported["revision"], running_pid=pid)
    if reported["revision"] != head:
        return finish("failed", "revision_mismatch")
    return finish("activated")
