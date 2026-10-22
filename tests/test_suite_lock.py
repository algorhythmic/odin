"""Suite locking uses only synthetic children and private temporary directories."""

import fcntl
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import suite_lock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "suite_lock.py"


class SuiteLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / "locks"
        self.environment = os.environ | {
            "ODIN_SUITE_LOCK_DIR": str(self.directory),
            "ODIN_SUITE_LOCK_TEST": "1",
            "ODIN_SUITE_LOCK": "1",
        }

    def command(self, code):
        return [sys.executable, str(SCRIPT), "--", sys.executable, "-c", code]

    def run_command(self, code, **environment):
        return subprocess.run(
            self.command(code), env=self.environment | environment,
            capture_output=True, text=True, timeout=3,
        )

    def start_command(self, code):
        process = subprocess.Popen(
            self.command(code), env=self.environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        def cleanup():
            if process.poll() is None:
                process.terminate()
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=3)

        self.addCleanup(cleanup)
        return process

    def read_line(self, stream):
        with selectors.DefaultSelector() as selector:
            selector.register(stream, selectors.EVENT_READ)
            self.assertTrue(selector.select(timeout=2), "child produced no output")
        return stream.readline()

    def hold_slots(self):
        self.directory.mkdir(mode=0o700)
        slots = []
        for number in range(2):
            slot = (self.directory / f"slot-{number}.lock").open("w")
            self.addCleanup(slot.close)
            fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
            slots.append(slot)
        return slots

    def test_make_test_wraps_the_full_suite(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn(
            "test:\n\tPYTHONPATH=python $(PYTHON) scripts/suite_lock.py -- "
            "$(PYTHON) -m unittest discover -s tests -v\n",
            makefile,
        )

    def test_exit_status_and_output_passthrough(self):
        for status in (0, 3):
            with self.subTest(status=status):
                result = self.run_command(
                    f"import sys; print('out'); print('err', file=sys.stderr); sys.exit({status})"
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, "out\n")
                self.assertEqual(result.stderr, "err\n")
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.assertEqual(
            stat.S_IMODE((self.directory / "slot-0.lock").stat().st_mode), 0o600
        )

    def test_bypass_ignores_held_slots(self):
        self.hold_slots()
        result = self.run_command("raise SystemExit(3)", ODIN_SUITE_LOCK="0")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_bypass_does_not_create_directory(self):
        result = self.run_command("pass", ODIN_SUITE_LOCK="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.directory.exists())

    def test_directory_override_without_test_marker_is_refused(self):
        self.environment.pop("ODIN_SUITE_LOCK_TEST")
        result = self.run_command("print('must not run')")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            result.stderr,
            "odin suite lock: ODIN_SUITE_LOCK_DIR is test-only; "
            "set ODIN_SUITE_LOCK_TEST=1 with it, or unset it\n",
        )
        self.assertFalse(self.directory.exists())

    def test_directory_override_with_test_marker_is_used(self):
        result = self.run_command("print('ran')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ran\n")
        self.assertEqual(result.stderr, "")
        self.assertTrue((self.directory / "slot-0.lock").is_file())

    def test_bypass_ignores_directory_override_without_test_marker(self):
        self.environment.pop("ODIN_SUITE_LOCK_TEST")
        result = self.run_command("print('ran'); raise SystemExit(3)", ODIN_SUITE_LOCK="0")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(result.stdout, "ran\n")
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.directory.exists())

    def test_waits_once_then_runs_when_a_slot_is_released(self):
        slots = self.hold_slots()
        process = self.start_command("print('ran')")
        waiting = f"odin suite lock: waiting for a free slot (2 in use) in {self.directory}\n"
        self.assertEqual(self.read_line(process.stderr), waiting)
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(timeout=0.1)
        fcntl.flock(slots[1], fcntl.LOCK_UN)
        stdout, stderr = process.communicate(timeout=2)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertEqual(stdout, "ran\n")
        self.assertEqual(stderr, "")

    def test_lock_is_held_until_child_exits(self):
        process = self.start_command(
            "import os, signal; print('ready', flush=True); signal.pause()"
        )
        self.assertEqual(self.read_line(process.stdout), "ready\n")
        with (self.directory / "slot-0.lock").open("r") as slot:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=2)
            self.assertEqual(process.returncode, -signal.SIGTERM, stderr)
            self.assertEqual((stdout, stderr), ("", ""))
            fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_sigint_is_forwarded_and_child_status_is_preserved(self):
        process = self.start_command(
            "import signal, sys; "
            "signal.signal(signal.SIGINT, lambda *_: sys.exit(3)); "
            "print('ready', flush=True); signal.pause()"
        )
        self.assertEqual(self.read_line(process.stdout), "ready\n")
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=2)
        self.assertEqual(process.returncode, 3, stderr)
        self.assertEqual((stdout, stderr), ("", ""))

    def test_child_signal_exit_is_reported_as_if_run_directly(self):
        result = self.run_command("import os, signal; os.kill(os.getpid(), signal.SIGTERM)")
        self.assertEqual(result.returncode, -signal.SIGTERM, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_suite_replaces_the_wrapper_in_the_callers_process_group(self):
        # No separate wrapper can die and release the slot while the suite
        # runs, and terminal signals reach the suite's whole process group.
        process = self.start_command(
            "import os, signal; print(os.getpid(), os.getpgrp(), flush=True); signal.pause()"
        )
        pid, group = map(int, self.read_line(process.stdout).split())
        self.assertEqual((pid, group), (process.pid, os.getpgrp()))
        with (self.directory / "slot-0.lock").open("r") as slot:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process.kill()
            process.communicate(timeout=2)
            fcntl.flock(slot, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_insecure_directory_is_refused(self):
        self.directory.mkdir(mode=0o700)
        for permissions in (0o750, 0o707):
            with self.subTest(permissions=oct(permissions)):
                self.directory.chmod(permissions)
                result = self.run_command("print('must not run')")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("odin suite lock:", result.stderr)
                self.assertIn("group/other permissions", result.stderr)

    def test_non_directory_is_refused(self):
        self.directory.touch(mode=0o600)
        result = self.run_command("print('must not run')")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("not a directory", result.stderr)

    def test_directory_symlink_is_refused(self):
        target = self.root / "private"
        target.mkdir(mode=0o700)
        self.directory.symlink_to(target, target_is_directory=True)
        result = self.run_command("print('must not run')")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("not a directory", result.stderr)
        self.assertEqual(list(target.iterdir()), [])

    def test_directory_override_takes_precedence(self):
        with patch.dict(os.environ, self.environment | {"XDG_RUNTIME_DIR": str(self.root)}):
            self.assertEqual(suite_lock.lock_directory(), self.directory)

    def test_runtime_directory_does_not_split_the_slots(self):
        for runtime in (None, str(self.root)):
            with self.subTest(runtime=runtime):
                environment = {} if runtime is None else {"XDG_RUNTIME_DIR": runtime}
                with patch.dict(os.environ, environment, clear=True):
                    self.assertEqual(
                        suite_lock.lock_directory(),
                        Path(f"/tmp/odin-suite-lock-{os.getuid()}"),
                    )

    def test_directory_owned_by_another_uid_is_refused(self):
        uid = os.getuid() + 1
        with patch.object(suite_lock.os, "getuid", return_value=uid):
            with self.assertRaisesRegex(ValueError, "not owned by the current uid"):
                suite_lock.acquire_slot(self.directory)

    def test_slot_symlink_is_refused(self):
        self.directory.mkdir(mode=0o700)
        target = self.root / "target"
        target.write_text("unchanged")
        (self.directory / "slot-0.lock").symlink_to(target)
        result = self.run_command("print('must not run')")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("odin suite lock:", result.stderr)
        self.assertEqual(target.read_text(), "unchanged")

    def test_slot_fifo_is_refused_without_hanging(self):
        self.directory.mkdir(mode=0o700)
        os.mkfifo(self.directory / "slot-0.lock", mode=0o600)
        # run_command's timeout also catches a blocking FIFO open.
        result = self.run_command("print('must not run')")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("slot-0.lock is not a regular file owned by the current uid", result.stderr)

    def test_slot_owned_by_another_uid_is_refused(self):
        self.directory.mkdir(mode=0o700)
        (self.directory / "slot-0.lock").touch(mode=0o600)
        real_fstat = os.fstat

        def fstat(descriptor):
            # Keep the directory's real owner; report a foreign slot owner.
            metadata = real_fstat(descriptor)
            if stat.S_ISREG(metadata.st_mode):
                fields = list(metadata)
                fields[stat.ST_UID] = os.getuid() + 1
                return os.stat_result(fields)
            return metadata

        with patch.object(suite_lock.os, "fstat", side_effect=fstat):
            with self.assertRaisesRegex(
                ValueError, "slot-0.lock is not a regular file owned by the current uid"
            ):
                suite_lock.acquire_slot(self.directory)


if __name__ == "__main__":
    unittest.main()
