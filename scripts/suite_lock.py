"""Limit concurrent full Python suites on this host, using per-user flock slots."""

import fcntl
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time


SLOTS = 2


def lock_directory():
    override = os.environ.get("ODIN_SUITE_LOCK_DIR")
    if override is not None:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        try:
            metadata = Path(runtime).stat()
        except OSError:
            pass
        else:
            if stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == os.getuid():
                return Path(runtime) / "odin-suite-lock"
    return Path(f"/tmp/odin-suite-lock-{os.getuid()}")


def acquire_slot(directory):
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    metadata = directory.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{directory} is not a directory")
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(directory, flags)
    try:
        metadata = os.fstat(directory_fd)
        if metadata.st_uid != os.getuid():
            raise ValueError(f"{directory} is not owned by the current uid")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError(f"{directory} has group/other permissions")
        waiting = False
        while True:
            for number in range(SLOTS):
                flags = os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
                slot = os.open(f"slot-{number}.lock", flags, 0o600, dir_fd=directory_fd)
                acquired = False
                try:
                    metadata = os.fstat(slot)
                    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                        raise ValueError(f"slot-{number}.lock is not a regular file owned by the current uid")
                    try:
                        fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    acquired = True
                    return slot
                finally:
                    if not acquired:
                        os.close(slot)
            if not waiting:
                print(
                    f"odin suite lock: waiting for a free slot ({SLOTS} in use) in {directory}",
                    file=sys.stderr, flush=True,
                )
                waiting = True
            time.sleep(1)
    finally:
        os.close(directory_fd)


def run_command(command):
    child = None
    pending = []

    def forward(signum, _frame):
        if child is None:
            pending.append(signum)
        else:
            try:
                child.send_signal(signum)
            except ProcessLookupError:
                pass

    previous = {signum: signal.signal(signum, forward)
                for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        # Receive terminal signals only through the wrapper, avoiding double SIGINT.
        child = subprocess.Popen(command, start_new_session=True)
        for signum in pending:
            forward(signum, None)
        status = child.wait()
        return status if status >= 0 else 128 - status
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) < 2 or arguments[0] != "--":
        print("usage: suite_lock.py -- <command...>", file=sys.stderr)
        return 2
    slot = None
    try:
        if os.environ.get("ODIN_SUITE_LOCK") != "0":
            slot = acquire_slot(lock_directory())
        return run_command(arguments[1:])
    except (OSError, ValueError) as error:
        print(f"odin suite lock: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 128 + signal.SIGINT
    finally:
        if slot is not None:
            os.close(slot)


if __name__ == "__main__":
    sys.exit(main())
