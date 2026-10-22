"""Foreground supervisor for the native executive (ODIN-ADR-039).

``executive-supervise`` runs in the executive's terminal. It holds one
supervisor lease per state directory and launches Claude Code through the
ordinary start path (``executive_runtime.start`` with ``--resume`` once a launch
is recorded), as a child that keeps the terminal. While the child runs it polls
the service for an executive restart request. When one is pending and the
turn-marker hooks show an idle executive, it asks the service to move the
request to ``stopping`` (the service rechecks safety), sends SIGTERM to the
Claude Code process, which runs its own graceful shutdown and SessionEnd hooks,
and relaunches through the same start path, so staged pending-development
changes apply and the same native session resumes. Outcomes are reported to
the service, which records history and an executive notice.

It never kills a process, never sends keystrokes and never answers a native
confirmation. An operator ``/exit`` (exit status 0) with no pending request
ends supervision. An unexpected non-zero exit relaunches with backoff, at most
three times in ten minutes. Code and synthetic tests do not establish native
behaviour; the clean exit, the idle marker and the startup confirmation are
live acceptance for the operator.
"""
import fcntl
import glob
import os
import signal
import socket
import stat
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from .contracts import Contracts, canonical, identifier, strict_loads
from .executive_turn_hook import read_marker
from .store import now

LEASE_FILE = "supervisor.lock"
JOURNAL_FILE = "supervisor-journal.jsonl"
CRASH_LIMIT = 3
CRASH_WINDOW_SECONDS = 600
CRASH_BACKOFF_SECONDS = (10, 30, 90)
IDLE_EVENTS = ("Stop", "StopFailure")
STARTED_EVENTS = ("SessionStart", "UserPromptSubmit", "Stop", "StopFailure")


class SupervisorRefused(PermissionError):
    """A fixed refusal code; the supervisor did not start a child."""


class ServiceRefused(OSError):
    """The service answered and refused; retrying the same report cannot help."""


class ServiceClient:
    """Operator-socket client for restart status, transitions and events."""

    def __init__(self, state, project, *, timeout=10):
        self.address = str(Path(state) / "service.sock")
        self.project = project
        self.timeout = timeout

    def _command(self, action, payload):
        command = {"schema_version": 1, "operation_id": identifier(), "action": action,
                   "payload": {"project": self.project} | payload}
        frame = (canonical({"surface": "terminal", "command": command}) + "\n").encode()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(self.timeout)
            client.connect(self.address)
            client.sendall(frame)
            with client.makefile("rb") as stream:
                raw = stream.readline(1048577)
        if len(raw) > 1048576 or not raw.endswith(b"\n"):
            raise OSError("invalid service response")
        try:
            response = strict_loads(raw)
        except (ValueError, RecursionError) as error:
            raise OSError("invalid service response") from error
        if not isinstance(response, dict):
            raise OSError("invalid service response")
        if "error" in response:
            detail = response.get("detail")
            raise ServiceRefused(detail if isinstance(detail, str) else "service_refused")
        if not isinstance(response.get("result"), dict):
            raise OSError("invalid service response")
        return response["result"]

    def status(self):
        return self._command("executive_restart_status", {})

    def transition(self, request_id, state, **fields):
        return self._command("executive_restart_transition",
                             {"request_id": request_id, "state": state} | fields)["request"]

    def event(self, kind, **fields):
        return self._command("executive_supervisor_event", {"kind": kind} | fields)


def _seconds(start, end):
    return round(max(0.0, end - start), 3)


def _parse(stamp):
    return datetime.fromisoformat(stamp).timestamp()


class Supervisor:
    def __init__(self, state, *, client=None, launcher=None, clock=time.time, sleep=time.sleep,
                 quiet_seconds=15.0, stop_timeout=60.0, startup_window=120.0, poll_seconds=1.0,
                 status_seconds=2.0, output=sys.stderr):
        from .executive_runtime import _load

        self.state = Path(state)
        manifest, self.base = _load(state)
        if manifest["version"] != 3:
            raise SupervisorRefused("supervisor_requires_development_profile")
        self.project = manifest["project"]
        self.client = client or ServiceClient(state, self.project)
        self.launcher = launcher or self._start
        self.clock, self.sleep = clock, sleep
        self.quiet_seconds, self.stop_timeout = quiet_seconds, stop_timeout
        self.startup_window, self.poll_seconds = startup_window, poll_seconds
        self.status_seconds = status_seconds
        self.output = output
        self.crashes = deque()
        self.outbox = []
        self.carry = None        # request being carried out across a relaunch
        self.stopped_for = None  # request whose stop ended the last child
        self.late_signal = False  # SIGTERM sent, exit not seen before the timeout

    # -- records ---------------------------------------------------------

    def journal(self, kind, **fields):
        """Append one private, content-free line; failures are reported, not fatal."""
        record = {"schema_version": 1, "time": now(), "kind": kind} | fields
        try:
            Contracts().validate("executive-supervisor-journal", record)
            fd = os.open(self.base / JOURNAL_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(fd)
                if stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077:
                    os.write(fd, (canonical(record) + "\n").encode())
            finally:
                os.close(fd)
        except Exception as error:  # noqa: BLE001 - the journal never stops supervision
            self.say(f"journal not written: {type(error).__name__}")

    def say(self, text):
        print(f"odin executive-supervise: {text}", file=self.output, flush=True)

    def _send(self, call):
        """Deliver one service report now or keep it for the next poll."""
        self.outbox.append(call)
        self._flush()

    def _flush(self):
        while self.outbox:
            kind, args, fields = self.outbox[0]
            try:
                if kind == "transition":
                    self.client.transition(*args, **fields)
                else:
                    self.client.event(*args, **fields)
            except ServiceRefused as error:
                # An answered refusal is final for this report; keep the rest flowing.
                self.journal("report_refused", code=_code(error))
                self.outbox.pop(0)
                continue
            except (OSError, KeyError, TypeError, ValueError):
                return False
            self.outbox.pop(0)
        return True

    def _transition_now(self, request, state, **fields):
        """A transition whose answer decides what happens next; None when unreachable."""
        try:
            return self.client.transition(request["id"], state, **fields)
        except (OSError, KeyError, TypeError, ValueError) as error:
            self.journal("service_unavailable", code=_code(error))
            return None

    def _open_request(self):
        return next((item for item in self._open() if item["state"] == "pending"), None)

    def _open(self):
        """Open requests as the service reports them; empty when it cannot answer."""
        try:
            items = self.client.status()["open"]
            if not isinstance(items, list) or not all(
                    isinstance(item, dict) and isinstance(item.get("id"), str) and
                    item.get("state") in ("pending", "stopping", "relaunching") for item in items):
                return []
            return items
        except (OSError, KeyError, TypeError, ValueError):
            return []

    # -- launch ----------------------------------------------------------

    def _start(self, resume, watch):
        from .executive_runtime import start

        return start(self.state, resume=resume, supervised=True, watch=watch, require_terminal=False)

    def _session(self):
        from .executive_runtime import _load

        return _load(self.state)[0]

    def _transcript_quiet(self, manifest, at):
        """True when no transcript of the session changed within the quiet window."""
        pattern = os.path.join(glob.escape(manifest["config_dir"]), "projects", "*",
                               glob.escape(manifest["native_session_id"]) + ".jsonl")
        for path in glob.glob(pattern):
            try:
                if at - os.stat(path).st_mtime < self.quiet_seconds:
                    return False
            except OSError:
                continue
        return True

    def idle(self, launched_at):
        """The idle signal: a Stop marker from this launch, quiet for the window.

        The marker must be the latest event of the current native session,
        written after this launch, with no background task reported, unchanged
        for ``quiet_seconds``, and the session transcript must be as quiet.
        """
        manifest = self._session()
        marker = read_marker(self.state)
        at = self.clock()
        if (marker is None or marker["session_id"] != manifest["native_session_id"] or
                marker["event"] not in IDLE_EVENTS or marker["background_tasks"] not in (None, 0)):
            return False
        stamp = _parse(marker["at"])
        return (stamp >= launched_at and at - stamp >= self.quiet_seconds and
                self._transcript_quiet(manifest, at))

    def _started(self, launched_at):
        manifest = self._session()
        marker = read_marker(self.state)
        return (marker is not None and marker["session_id"] == manifest["native_session_id"] and
                marker["event"] in STARTED_EVENTS and _parse(marker["at"]) >= launched_at)

    def _ended_cleanly(self, signalled_at):
        marker = read_marker(self.state)
        return marker is not None and marker["event"] == "SessionEnd" and _parse(marker["at"]) >= signalled_at - 1

    def _stop(self, process, request, requested_at, launched_at):
        """SIGTERM at idle, then wait. Never escalates to a kill."""
        moved = self._transition_now(request, "stopping")
        if moved is None or moved["state"] != "stopping":
            if moved is not None:
                self.journal("restart_refused", request_id=request["id"], code=moved.get("code"))
            return None
        # Recheck after the round trip, so a turn that began meanwhile is not cut.
        while not self.idle(launched_at):
            code = process.poll()
            if code is not None:
                return self._stopped(request, requested_at, None, code)
            self.sleep(self.poll_seconds)
        signalled = self.clock()
        self.journal("stop_signalled", request_id=request["id"])
        try:
            process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            pass
        while self.clock() - signalled < self.stop_timeout:
            code = process.poll()
            if code is not None:
                return self._stopped(request, requested_at, signalled, code)
            self.sleep(min(self.poll_seconds, 0.2))
        # A later exit is this SIGTERM taking effect, not a crash or an operator exit.
        self.late_signal = True
        self.journal("stop_timeout", request_id=request["id"])
        self._send(("transition", (request["id"], "failed"), {"code": "stop_timeout", "timings": {
            "wait_idle_seconds": _seconds(requested_at, signalled),
            "stop_seconds": _seconds(signalled, self.clock())}}))
        self.say("Claude Code did not exit after SIGTERM; it keeps running. The restart failed "
                 "(stop_timeout); nothing was killed.")
        return None

    def _stopped(self, request, requested_at, signalled, code):
        ended = self.clock()
        start = signalled if signalled is not None else ended
        self.stopped_for = request | {"timings": {
            "wait_idle_seconds": _seconds(requested_at, start),
            "stop_seconds": _seconds(start, ended)},
            "exit_code": code,
            "clean_exit_observed": self._ended_cleanly(start) if signalled is not None else None,
            "stopped_at": ended}
        return code

    def watch(self, process):
        launched_at = self.clock()
        warned = False
        seen_at = None
        last_status = 0.0
        request = None
        while True:
            try:
                code = process.poll()
                if code is not None:
                    return code
                self._flush()
                if self.carry is not None:
                    if self._started(launched_at):
                        carry, self.carry = self.carry, None
                        timings = carry.get("timings", {}) | {
                            "relaunch_seconds": _seconds(carry.get("stopped_at", launched_at), self.clock())}
                        self.journal("restarted", request_id=carry["id"])
                        self._send(("transition", (carry["id"], "restarted"), {
                            "timings": timings, "exit_code": carry.get("exit_code"),
                            "clean_exit_observed": carry.get("clean_exit_observed")}))
                    elif not warned and self.clock() - launched_at >= self.startup_window:
                        warned = True
                        self.journal("awaiting_operator_confirmation", request_id=self.carry["id"])
                        self._send(("event", ("awaiting_operator_confirmation",), {}))
                        self.say("the relaunched session has not started. If Claude Code shows a "
                                 "startup confirmation (for example the development-channel warning), "
                                 "the operator must answer it; the supervisor never answers it.")
                if self.clock() - last_status >= self.status_seconds:
                    last_status = self.clock()
                    request = self._open_request()
                    if request is not None and seen_at is None:
                        seen_at = self.clock()
                        self.journal("restart_seen", request_id=request["id"])
                    elif request is None:
                        seen_at = None
                if request is not None and self.carry is None and self.idle(launched_at):
                    code = self._stop(process, request, seen_at or self.clock(), launched_at)
                    if code is not None:
                        return code
                    request, seen_at = None, None
                self.sleep(self.poll_seconds)
            except KeyboardInterrupt:
                # Ctrl+C belongs to Claude Code in the same terminal.
                continue

    # -- main loop -------------------------------------------------------

    def _carry_pending_at_start(self):
        """An open request before any child runs: nothing to stop, so the launch is the restart.

        A request left ``stopping`` or ``relaunching`` by a supervisor that
        ended mid-restart is carried the same way, so it cannot block every
        later request. The lease guarantees no other supervisor owns it.
        """
        request = next(iter(self._open()), None)
        if request is None:
            return
        if request["state"] == "pending":
            moved = self._transition_now(request, "stopping")
            if moved is None or moved["state"] != "stopping":
                return
        self.journal("restart_at_supervisor_start", request_id=request["id"])
        if request["state"] != "relaunching":
            self._send(("transition", (request["id"], "relaunching"), {}))
        self.carry = request | {"timings": {"wait_idle_seconds": 0, "stop_seconds": 0},
                                "stopped_at": self.clock(), "exit_code": None,
                                "clean_exit_observed": None}

    def run(self):
        with _lease(self.base / LEASE_FILE):
            self.journal("supervision_started")
            self._send(("event", ("supervision_started",), {}))
            self._carry_pending_at_start()
            while True:
                resume = (self.base / "launch.json").exists()
                self.stopped_for = None
                self.late_signal = False
                try:
                    code = self.launcher(resume, self.watch)
                except Exception as error:
                    if not isinstance(error, PermissionError):
                        # Unexpected: record what is known, then let it surface.
                        self.journal("supervisor_error", code=_code(error))
                        if self.carry is not None:
                            self._send(("transition", (self.carry["id"], "failed"),
                                        {"code": "supervisor_error"}))
                        self._flush()
                        raise
                    # The ordinary start path refused before launching a child.
                    self.journal("launch_failed", code=_code(error))
                    if self.carry is not None:
                        self._send(("transition", (self.carry["id"], "failed"), {"code": "launch_failed"}))
                        self.carry = None
                    self._send(("event", ("launch_failed",), {"code": _code(error)}))
                    self.say(f"launch refused: {error}. Supervision ended.")
                    self._flush()
                    return 2
                if self.stopped_for is not None:
                    stopped, self.stopped_for = self.stopped_for, None
                    self._send(("transition", (stopped["id"], "relaunching"), {
                        "timings": stopped["timings"], "exit_code": code,
                        "clean_exit_observed": stopped["clean_exit_observed"]}))
                    self.carry = stopped
                    self.journal("relaunching", request_id=stopped["id"], exit_code=code)
                    continue
                if self.late_signal:
                    # The timed-out SIGTERM took effect after all: relaunch, no crash.
                    self.journal("late_exit", exit_code=_exit(code))
                    continue
                if self.carry is not None:
                    # The relaunch itself ended before the session started.
                    self._send(("transition", (self.carry["id"], "failed"), {
                        "code": "relaunch_exited", "exit_code": code}))
                    self.carry = None
                if code == 0:
                    request = self._open_request()
                    if request is None:
                        self.journal("operator_exit", exit_code=0)
                        self._send(("event", ("supervision_ended",), {"exit_code": 0}))
                        self._flush()
                        return 0
                    # The session ended while a restart was pending: that is the stop.
                    moved = self._transition_now(request, "stopping")
                    if moved is not None and moved["state"] == "stopping":
                        self._send(("transition", (request["id"], "relaunching"), {"exit_code": 0}))
                        self.carry = request | {"timings": {}, "stopped_at": self.clock(),
                                                "exit_code": 0, "clean_exit_observed": None}
                        continue
                    self.journal("operator_exit", exit_code=0)
                    self._send(("event", ("supervision_ended",), {"exit_code": 0}))
                    self._flush()
                    return 0
                at = self.clock()
                while self.crashes and at - self.crashes[0] > CRASH_WINDOW_SECONDS:
                    self.crashes.popleft()
                self.journal("crash", exit_code=_exit(code))
                self._send(("event", ("crash",), {"exit_code": _exit(code)}))
                if len(self.crashes) >= CRASH_LIMIT:
                    self.journal("crash_limit", exit_code=_exit(code))
                    self._send(("event", ("crash_limit",), {"exit_code": _exit(code)}))
                    self.say(f"Claude Code exited unexpectedly ({code}) {CRASH_LIMIT + 1} times within "
                             f"{CRASH_WINDOW_SECONDS} s. Supervision stopped; start it again when fixed.")
                    self._flush()
                    return code
                delay = CRASH_BACKOFF_SECONDS[len(self.crashes)]
                self.crashes.append(at)
                self.say(f"Claude Code exited unexpectedly ({code}); relaunching in {delay} s.")
                self.sleep(delay)


def _exit(code):
    return code if type(code) is int and -255 <= code <= 255 else None


def _code(error):
    text = str(error)
    return text if text.replace("_", "").isalnum() and text.islower() and len(text) <= 64 else type(error).__name__.lower()


class _lease:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        info = os.fstat(self.fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            os.close(self.fd)
            raise SupervisorRefused("supervisor_lease_not_private")
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd)
            raise SupervisorRefused("supervisor_already_running") from None
        return self

    def __exit__(self, *exc):
        os.close(self.fd)


def supervise(state, **options):
    """CLI entry point: refuses without a terminal, then runs until it ends."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SupervisorRefused("supervisor_requires_terminal")
    # The child gets Ctrl+C from the terminal; the supervisor keeps running.
    # A Python handler, not SIG_IGN: an ignored disposition would be inherited
    # by Claude Code across exec, while a handler resets to the default there.
    signal.signal(signal.SIGINT, lambda *_: None)
    return Supervisor(state, **options).run()
