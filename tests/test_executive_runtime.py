"""Local launcher policy only: no login, model call or Remote Control claim."""

import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from jsonschema import ValidationError
from odin import executive_runtime as runtime
from odin.contracts import ROOT


class ExecutiveRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.profile = self.root / "credentials"

    def prepare(self, **changes):
        arguments = {
            "config_dir": self.profile,
            "project": "01K00000000000000000000001",
            "claude_binary": sys.executable,
            "python_executable": sys.executable,
        }
        arguments.update(changes)
        return runtime.prepare(self.state, **arguments)

    def test_prepare_is_private_and_reuses_native_session_identity(self):
        first = self.prepare()
        self.assertEqual(first, self.prepare())
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.profile.stat().st_mode), 0o700)
        for path in (self.state / "executive-pilot").glob("*.json"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaisesRegex(ValueError, "different configuration"):
            self.prepare(model="claude-opus-4-7")

    def test_narrow_native_remote_launch_and_explicit_resume(self):
        manifest = self.prepare()
        spec = runtime.launch_spec(self.state)
        argv = spec["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(argv[argv.index("--model") + 1], runtime.DEFAULT_MODEL)
        self.assertEqual(
            argv[argv.index("--session-id") + 1], manifest["native_session_id"]
        )
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "")
        self.assertEqual(argv[argv.index("--system-prompt-snapshot") + 1], "off")
        for flag in (
            "--restricted",
            "--strict-mcp-config",
            "--remote-control",
            "--no-chrome",
        ):
            self.assertIn(flag, argv)
        for flag in (
            "--bare",
            "--safe-mode",
            "--print",
            "--dangerously-skip-permissions",
            "--fallback-model",
        ):
            self.assertNotIn(flag, argv)
        self.assertEqual(
            set(argv[argv.index("--allowedTools") + 1].split(",")),
            set(runtime.ALLOWED_TOOLS),
        )
        resumed = runtime.launch_spec(self.state, resume=True)["argv"]
        self.assertNotIn("--session-id", resumed)
        self.assertEqual(
            resumed[resumed.index("--resume") + 1], manifest["native_session_id"]
        )

    def test_environment_removes_other_credential_domains_and_loader_overrides(self):
        self.prepare()
        hostile = {
            name: "must-not-inherit"
            for name in (
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
                "CLAUDE_CODE_OAUTH_TOKEN",
                "ANTHROPIC_BASE_URL",
                "CLAUDE_CODE_USE_BEDROCK",
                "CLAUDE_CODE_USE_VERTEX",
                "AWS_ACCESS_KEY_ID",
                "SAGA_TOKEN",
                "TELEGRAM_TOKEN",
                "OPENAI_API_KEY",
                "BASH_ENV",
                "ENV",
                "PYTHONPATH",
                "LD_PRELOAD",
                "NODE_OPTIONS",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
                "DISABLE_GROWTHBOOK",
            )
        }
        with patch.dict(os.environ, hostile):
            spec = runtime.launch_spec(self.state)
            login = runtime.login_spec(self.state)
        for name in hostile:
            self.assertNotIn(name, spec["env"])
        self.assertEqual(spec["env"], login["env"])
        self.assertEqual(spec["env"]["CLAUDE_CONFIG_DIR"], str(self.profile))
        self.assertEqual(
            spec["env"]["HOME"], str(self.state / "executive-pilot" / "home")
        )
        self.assertEqual(login["argv"][1:], ["auth", "login", "--claudeai"])

    def test_mcp_config_is_one_project_scoped_stdio_bridge(self):
        self.prepare()
        config = json.loads((self.state / "executive-pilot" / "mcp.json").read_text())
        self.assertEqual(set(config["mcpServers"]), {"odin"})
        server = config["mcpServers"]["odin"]
        self.assertEqual(
            server["args"],
            [
                "-m",
                "odin.executive_mcp",
                "--state",
                str(self.state),
                "--project",
                "01K00000000000000000000001",
            ],
        )
        self.assertEqual(
            server["env"], {"PYTHONPATH": str(ROOT / "python"), "PYTHONNOUSERSITE": "1"}
        )

    def test_tool_free_preparation_has_no_mcp_or_approvals(self):
        self.prepare(enable_mcp=False)
        spec = runtime.launch_spec(self.state)
        self.assertNotIn("--allowedTools", spec["argv"])
        settings = json.loads(
            (self.state / "executive-pilot" / "settings.json").read_text()
        )
        self.assertEqual(settings["permissions"]["allow"], [])
        self.assertEqual(
            json.loads((self.state / "executive-pilot" / "mcp.json").read_text()),
            {"mcpServers": {}},
        )

    def test_repository_upgrade_exposes_only_read_tools_and_keeps_native_identity(self):
        original = self.prepare()
        base = self.state / "executive-pilot"
        old_settings = (base / "settings.json").read_bytes()
        bridge = (base / "mcp.json").read_bytes()
        result = runtime.enable_repository_reads(self.state)
        self.assertEqual(result["native_session_id"], original["native_session_id"])
        self.assertEqual(result["repository_root"], str(ROOT))
        self.assertEqual(result["native_tools"], ["Read", "Glob", "Grep"])
        self.assertEqual(result, runtime.enable_repository_reads(self.state))
        self.assertEqual(self.prepare()["version"], 2)
        self.assertEqual((base / "settings.json").read_bytes(), old_settings)
        self.assertEqual((base / "mcp.json").read_bytes(), bridge)
        spec = runtime.launch_spec(self.state, resume=True)
        argv = spec["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep")
        self.assertEqual(argv[argv.index("--add-dir") + 1], str(ROOT))
        self.assertEqual(
            argv[argv.index("--resume") + 1], original["native_session_id"]
        )
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("--restricted", argv)
        self.assertEqual(spec["cwd"], str(base / "workspace"))
        prompt = argv[argv.index("--system-prompt") + 1]
        self.assertIn(str(ROOT / "docs"), prompt)
        self.assertIn("persistent local SQLite store", prompt)
        self.assertIn("fake Saga execution backend", prompt)
        self.assertTrue(runtime.status(self.state)["repository_reads_enabled"])

    def test_development_can_be_staged_while_session_is_active_without_mutating_it(
        self,
    ):
        original = self.prepare()
        base = self.state / "executive-pilot"
        manifest = (base / "manifest.json").read_bytes()
        settings = (base / "settings.json").read_bytes()
        with (
            runtime._lease(base / "runtime.lock"),
            runtime._lease(self.profile / ".odin-lineage.lock"),
        ):
            result = runtime.enable_development(self.state)
            self.assertEqual(result, runtime.enable_development(self.state))
            current = runtime.status(self.state)
        self.assertTrue(result["pending_activation"])
        self.assertEqual(result["native_session_id"], original["native_session_id"])
        self.assertEqual((base / "manifest.json").read_bytes(), manifest)
        self.assertEqual((base / "settings.json").read_bytes(), settings)
        self.assertEqual(current["configuration"]["version"], 1)
        self.assertEqual(current["pending_profile_version"], 3)
        self.assertTrue(current["process_lease_held"])
        self.assertFalse(current["development_enabled"])

    def test_development_launch_uses_full_native_tools_environment_and_checkout(self):
        original = self.prepare()
        runtime.enable_development(self.state)
        with patch.dict(
            os.environ, {"ODIN_SYNTHETIC_ENV": "retained", "PATH": "/synthetic/bin"}
        ):
            spec = runtime.launch_spec(self.state, resume=True)
        argv = spec["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "default")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "bypassPermissions")
        self.assertEqual(
            argv[argv.index("--resume") + 1], original["native_session_id"]
        )
        self.assertEqual(argv[argv.index("--system-prompt-snapshot") + 1], "off")
        for removed in (
            "--restricted",
            "--strict-mcp-config",
            "--allowedTools",
            "--settings",
            "--setting-sources",
            "--disable-slash-commands",
            "--no-chrome",
            "--system-prompt",
        ):
            self.assertNotIn(removed, argv)
        self.assertIn("--mcp-config", argv)
        self.assertEqual(spec["cwd"], str(ROOT))
        self.assertEqual(spec["env"]["HOME"], runtime.pwd.getpwuid(os.getuid()).pw_dir)
        self.assertEqual(spec["env"]["CLAUDE_CONFIG_DIR"], str(self.profile))
        self.assertEqual(spec["env"]["ODIN_SYNTHETIC_ENV"], "retained")
        self.assertEqual(spec["env"]["PATH"], "/synthetic/bin")
        prompt = argv[argv.index("--append-system-prompt") + 1]
        self.assertIn("edit code and documentation", prompt)
        self.assertIn("old proposal-only pilot instructions are superseded", prompt)

    def test_development_resume_activates_profile_even_when_odin_service_is_offline(
        self,
    ):
        original = self.prepare()
        runtime.enable_repository_reads(self.state)
        runtime.enable_development(self.state)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(
                runtime, "_socket_ready", side_effect=PermissionError("offline")
            ) as socket_ready,
            patch.object(runtime, "_foreground", return_value=0) as foreground,
        ):
            self.assertEqual(runtime.start(self.state, resume=True), 0)
        socket_ready.assert_not_called()
        spec = foreground.call_args.args[0]
        self.assertEqual(spec["cwd"], str(ROOT))
        self.assertEqual(
            spec["argv"][spec["argv"].index("--resume") + 1],
            original["native_session_id"],
        )
        current = runtime.status(self.state)
        self.assertTrue(current["development_enabled"])
        self.assertIsNone(current["pending_profile_version"])
        self.assertEqual(current["last_launch"]["exit_code"], 0)
        self.assertEqual(self.prepare()["version"], 3)
        self.assertFalse(runtime.enable_development(self.state)["pending_activation"])
        self.assertEqual(
            runtime.enable_repository_reads(self.state)["native_tools"], "default"
        )

    def test_development_activation_requires_both_session_ownership_leases(self):
        self.prepare()
        runtime.enable_development(self.state)
        base = self.state / "executive-pilot"
        for path in (base / "runtime.lock", self.profile / ".odin-lineage.lock"):
            with (
                runtime._lease(path),
                patch.object(sys.stdin, "isatty", return_value=True),
                patch.object(sys.stdout, "isatty", return_value=True),
                self.assertRaisesRegex(PermissionError, "active owner"),
            ):
                runtime.start(self.state, resume=True)
            self.assertEqual(runtime.status(self.state)["configuration"]["version"], 1)
            self.assertTrue((base / "pending-development.json").exists())

    def test_interrupted_development_activation_preserves_resumable_identity(self):
        original = self.prepare(enable_mcp=False)
        runtime.enable_development(self.state)
        original_write = runtime._write

        def fail_manifest(path, name, value):
            if path.name == "manifest.json":
                raise OSError("synthetic interrupted activation")
            return original_write(path, name, value)

        with (
            patch.object(runtime, "_write", side_effect=fail_manifest),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            self.assertRaisesRegex(OSError, "interrupted activation"),
        ):
            runtime.start(self.state, resume=True)
        current = runtime.status(self.state)
        self.assertEqual(
            current["configuration"]["native_session_id"], original["native_session_id"]
        )
        self.assertEqual(current["configuration"]["version"], 1)
        self.assertEqual(current["pending_profile_version"], 3)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0),
        ):
            runtime.start(self.state, resume=True)
        self.assertTrue(runtime.status(self.state)["development_enabled"])

    def test_pending_development_cannot_replace_the_saved_session_identity(self):
        self.prepare()
        runtime.enable_development(self.state)
        path = self.state / "executive-pilot" / "pending-development.json"
        pending = json.loads(path.read_text())
        pending["native_session_id"] = str(runtime.uuid.uuid4())
        path.write_text(json.dumps(pending))
        with self.assertRaisesRegex(PermissionError, "changed session identity"):
            runtime.launch_spec(self.state, resume=True)

    def test_staging_cannot_race_native_identity_rotation(self):
        original = self.prepare()
        original_write = runtime._write
        attempted = []

        def concurrent_stage(path, name, value):
            if path.name == "manifest.json":
                attempted.append(True)
                with self.assertRaisesRegex(PermissionError, "active owner"):
                    runtime.enable_development(self.state)
            return original_write(path, name, value)

        with patch.object(runtime, "_write", side_effect=concurrent_stage):
            rotated = runtime.new_session(self.state)
        self.assertTrue(attempted)
        self.assertNotEqual(rotated["native_session_id"], original["native_session_id"])
        staged = runtime.enable_development(self.state)
        self.assertEqual(staged["native_session_id"], rotated["native_session_id"])
        self.assertEqual(runtime.status(self.state)["pending_profile_version"], 3)

    def test_development_probe_checks_new_flags_without_requiring_old_restrictions(
        self,
    ):
        self.prepare(enable_mcp=False)
        runtime.enable_development(self.state)
        outputs = [
            subprocess.CompletedProcess([], 0, stdout="synthetic CLI\n"),
            subprocess.CompletedProcess(
                [], 0, stdout=" ".join(runtime.DEVELOPMENT_REQUIRED_FLAGS)
            ),
        ]
        with patch.object(runtime.subprocess, "run", side_effect=outputs):
            self.assertEqual(runtime.probe(self.state)["missing_flags"], [])
        self.assertNotIn("--mcp-config", runtime.launch_spec(self.state)["argv"])

    def test_repository_settings_deny_mutation_secrets_and_runtime_state(self):
        self.prepare()
        runtime.enable_repository_reads(self.state)
        settings = json.loads(
            (self.state / "executive-pilot" / "settings-repository-v2.json").read_text()
        )["permissions"]
        self.assertEqual(
            settings["allow"], runtime.ALLOWED_TOOLS + [f"Read(/{ROOT}/**)"]
        )
        for tool in (
            "Bash",
            "PowerShell",
            "REPL",
            "Write",
            "Edit",
            "Agent",
            "ToolSearch",
        ):
            self.assertIn(tool, settings["deny"])
        for tool in runtime.REPOSITORY_TOOLS:
            self.assertNotIn(tool, settings["deny"])
        for private in (self.state, self.profile):
            self.assertIn(f"Read(/{private}/**)", settings["deny"])
        for suffix in ("**/.git", "**/.git/**", "**/.env", "**/.credentials.json"):
            self.assertIn(f"Read(/{ROOT}/{suffix})", settings["deny"])

    def test_repository_upgrade_requires_free_process_and_credential_leases(self):
        self.prepare()
        base = self.state / "executive-pilot"
        manifest = (base / "manifest.json").read_bytes()
        for path in (base / "runtime.lock", self.profile / ".odin-lineage.lock"):
            with (
                runtime._lease(path),
                self.assertRaisesRegex(PermissionError, "active owner"),
            ):
                runtime.enable_repository_reads(self.state)
            self.assertEqual((base / "manifest.json").read_bytes(), manifest)
            self.assertFalse((base / "settings-repository-v2.json").exists())

    def test_interrupted_repository_upgrade_leaves_old_profile_usable(self):
        self.prepare()
        original_write = runtime._write

        def fail_manifest(path, name, value):
            if path.name == "manifest.json":
                raise OSError("synthetic interrupted manifest replacement")
            return original_write(path, name, value)

        with (
            patch.object(runtime, "_write", side_effect=fail_manifest),
            self.assertRaisesRegex(OSError, "synthetic interrupted"),
        ):
            runtime.enable_repository_reads(self.state)
        argv = runtime.launch_spec(self.state)["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertNotIn("--add-dir", argv)
        self.assertFalse(runtime.status(self.state)["repository_reads_enabled"])
        self.assertEqual(
            runtime.enable_repository_reads(self.state)["profile_version"], 2
        )

    def test_changed_repository_scope_or_policy_is_rejected(self):
        self.prepare()
        runtime.enable_repository_reads(self.state)
        base = self.state / "executive-pilot"
        path = base / "manifest.json"
        manifest = json.loads(path.read_text())
        changed = {**manifest, "repository_root": str(self.root)}
        runtime._write(path, "executive-pilot", changed)
        with self.assertRaisesRegex(PermissionError, "repository scope"):
            runtime.launch_spec(self.state)
        runtime._write(path, "executive-pilot", manifest)
        path = base / "settings-repository-v2.json"
        settings = json.loads(path.read_text())
        settings["permissions"]["deny"].remove("Write")
        runtime._write(path, "executive-pilot-settings", settings)
        with self.assertRaisesRegex(PermissionError, "narrow pilot policy"):
            runtime.launch_spec(self.state)

    def test_repository_scope_is_required_only_in_profile_version_two(self):
        manifest = self.prepare()
        contracts = runtime.Contracts()
        with self.assertRaises(ValidationError):
            contracts.validate("executive-pilot", {**manifest, "version": 2})
        with self.assertRaises(ValidationError):
            contracts.validate(
                "executive-pilot", {**manifest, "repository_root": str(ROOT)}
            )

    def test_repository_profile_probe_requires_add_dir_support(self):
        self.prepare()
        runtime.enable_repository_reads(self.state)
        results = [
            subprocess.CompletedProcess([], 0, stdout="2.1.synthetic"),
            subprocess.CompletedProcess([], 0, stdout=" ".join(runtime.REQUIRED_FLAGS)),
        ]
        with patch.object(runtime.subprocess, "run", side_effect=results):
            self.assertEqual(runtime.probe(self.state)["missing_flags"], ["--add-dir"])

    def test_repository_upgrade_keeps_recorded_launch_and_rotation_keeps_profile(self):
        self.prepare(enable_mcp=False)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0),
        ):
            runtime.start(self.state)
        before = runtime.status(self.state)
        runtime.enable_repository_reads(self.state)
        after = runtime.status(self.state)
        self.assertEqual(after["last_launch"], before["last_launch"])
        self.assertEqual(after["configuration"]["config_dir"], str(self.profile))
        rotated = runtime.new_session(self.state)
        current = runtime.status(self.state)
        self.assertTrue(current["repository_reads_enabled"])
        self.assertEqual(
            current["configuration"]["native_session_id"], rotated["native_session_id"]
        )

    def test_launch_observes_repository_upgrade_after_acquiring_ownership(self):
        self.prepare(enable_mcp=False)
        original_lease = runtime._lease
        upgraded = []

        @contextmanager
        def race(path):
            if path.name == "runtime.lock" and not upgraded:
                upgraded.append(True)
                runtime.enable_repository_reads(self.state)
            with original_lease(path) as descriptor:
                yield descriptor

        with (
            patch.object(runtime, "_lease", side_effect=race),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0) as foreground,
        ):
            runtime.start(self.state)
        argv = foreground.call_args.args[0]["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep")
        self.assertEqual(argv[argv.index("--add-dir") + 1], str(ROOT))

    def test_default_developer_profile_and_repository_state_are_rejected(self):
        with self.assertRaisesRegex(PermissionError, "dedicated"):
            self.prepare(config_dir=Path.home() / ".claude")
        with self.assertRaisesRegex(PermissionError, "outside the repository"):
            runtime.prepare(
                ROOT / ".test-executive-state",
                config_dir=self.profile,
                project="01K00000000000000000000001",
            )
        self.assertFalse((ROOT / ".test-executive-state").exists())

    def test_shared_or_symlink_directories_are_rejected(self):
        self.state.mkdir(mode=0o755)
        with self.assertRaisesRegex(PermissionError, "0700"):
            self.prepare()
        self.state.chmod(0o700)
        target = self.root / "actual-profile"
        target.mkdir(mode=0o700)
        self.profile.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(PermissionError, "symlinks"):
            self.prepare()

    def test_profile_inside_workspace_is_rejected(self):
        with self.assertRaisesRegex(PermissionError, "separate"):
            self.prepare(
                config_dir=self.state / "executive-pilot" / "workspace" / "credentials"
            )

    def test_credentials_are_never_read_and_symlinks_are_rejected(self):
        self.prepare()
        credentials = self.profile / ".credentials.json"
        credentials.write_text("not JSON; contents must never be read")
        credentials.chmod(0o600)
        self.assertTrue(runtime.status(self.state)["credential_file_present"])
        credentials.unlink()
        credentials.symlink_to(self.state / "executive-pilot" / "manifest.json")
        with self.assertRaisesRegex(PermissionError, "private regular"):
            runtime.status(self.state)

    def test_world_readable_credentials_are_rejected(self):
        self.prepare()
        credentials = self.profile / ".credentials.json"
        credentials.write_text("synthetic")
        credentials.chmod(0o644)
        with self.assertRaises(PermissionError):
            runtime.launch_spec(self.state)

    def test_changed_settings_or_bridge_are_rejected(self):
        self.prepare()
        path = self.state / "executive-pilot" / "settings.json"
        data = json.loads(path.read_text())
        data["permissions"]["deny"] = []
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(PermissionError, "narrow pilot policy"):
            runtime.launch_spec(self.state)

    def test_machine_config_is_closed_and_validated(self):
        self.prepare()
        path = self.state / "executive-pilot" / "manifest.json"
        data = json.loads(path.read_text())
        data["api_key"] = "synthetic-do-not-accept"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValidationError):
            runtime.launch_spec(self.state)

    def test_status_never_infers_login_model_or_remote_readiness(self):
        self.prepare()
        result = runtime.status(self.state)
        self.assertFalse(result["process_lease_held"])
        self.assertEqual(result["authentication"], "unverified")
        self.assertEqual(result["remote_control"], "requested_not_verified")
        self.assertEqual(result["model"], "requested_not_verified")
        self.assertFalse(result["sdk_adapter_enabled"])
        self.assertFalse(result["delegated_execution_enabled"])
        self.assertFalse(result["service_budget_enforced"])

    def test_status_reports_service_unavailable_without_socket(self):
        self.prepare()
        result = runtime.status(self.state)
        self.assertEqual(result["service_reachability"], "unavailable")

    def test_status_reports_service_reachable(self):
        self.prepare()
        with patch.object(runtime, "ExecutiveBridge") as bridge:
            bridge.return_value.call.return_value = {"isError": False, "content": []}
            result = runtime.status(self.state)
        self.assertEqual(result["service_reachability"], "reachable")

    def test_status_reports_service_unchecked_without_mcp(self):
        self.prepare(enable_mcp=False)
        with patch.object(runtime, "SocketGateway") as gateway:
            result = runtime.status(self.state)
        gateway.assert_not_called()
        self.assertEqual(result["service_reachability"], "unchecked")

    def test_lineage_lease_refuses_a_second_owner(self):
        self.prepare()
        path = self.profile / ".odin-lineage.lock"
        with (
            runtime._lease(path),
            self.assertRaisesRegex(PermissionError, "active owner"),
            runtime._lease(path),
        ):
            self.fail("second credential owner acquired lease")
        with runtime._lease(path):
            pass

    def test_inherited_lineage_lease_survives_wrapper_descriptor_close(self):
        self.prepare()
        path = self.profile / ".odin-lineage.lock"
        with runtime._lease(path) as descriptor:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('ready', flush=True); sys.stdin.read(1)",
                ],
                pass_fds=(descriptor,),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            self.assertEqual(child.stdout.readline(), b"ready\n")
        try:
            with (
                self.assertRaisesRegex(PermissionError, "active owner"),
                runtime._lease(path),
            ):
                self.fail("child lost its inherited credential lease")
        finally:
            child.communicate(b"x", timeout=5)
        with runtime._lease(path):
            pass

    def test_new_session_preserves_old_identity_and_requires_free_leases(self):
        previous = self.prepare()
        path = self.state / "executive-pilot" / "runtime.lock"
        with (
            runtime._lease(path),
            self.assertRaisesRegex(PermissionError, "active owner"),
        ):
            runtime.new_session(self.state)
        result = runtime.new_session(self.state)
        self.assertEqual(
            result["previous_native_session_id"], previous["native_session_id"]
        )
        self.assertNotEqual(result["native_session_id"], previous["native_session_id"])
        self.assertEqual(
            self.prepare()["native_session_id"], result["native_session_id"]
        )
        archived = (
            self.state
            / "executive-pilot"
            / f"launch-{previous['native_session_id']}.json"
        )
        self.assertEqual(json.loads(archived.read_text())["state"], "not_launched")

    def test_launch_uses_identity_read_after_acquiring_runtime_lock(self):
        original = self.prepare(enable_mcp=False)
        original_lease = runtime._lease
        rotated = []

        @contextmanager
        def race(path):
            if path.name == "runtime.lock" and not rotated:
                rotated.append(True)
                runtime.new_session(self.state)
            with original_lease(path) as descriptor:
                yield descriptor

        with (
            patch.object(runtime, "_lease", side_effect=race),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0) as foreground,
        ):
            runtime.start(self.state)
        current = runtime.status(self.state)
        self.assertNotEqual(
            current["configuration"]["native_session_id"], original["native_session_id"]
        )
        self.assertEqual(
            current["last_launch"]["native_session_id"],
            current["configuration"]["native_session_id"],
        )
        argv = foreground.call_args.args[0]["argv"]
        self.assertEqual(
            argv[argv.index("--session-id") + 1],
            current["last_launch"]["native_session_id"],
        )

    def test_rotation_reads_latest_identity_under_runtime_lock(self):
        original = self.prepare()
        original_lease = runtime._lease
        prior = []

        @contextmanager
        def race(path):
            if path.name == "runtime.lock" and not prior:
                prior.append(None)
                prior[0] = runtime.new_session(self.state)
            with original_lease(path) as descriptor:
                yield descriptor

        with patch.object(runtime, "_lease", side_effect=race):
            current = runtime.new_session(self.state)
        self.assertEqual(
            prior[0]["previous_native_session_id"], original["native_session_id"]
        )
        self.assertEqual(
            current["previous_native_session_id"], prior[0]["native_session_id"]
        )

    def test_status_does_not_mislabel_unsafe_lock_as_running(self):
        self.prepare()
        path = self.state / "executive-pilot" / "runtime.lock"
        path.write_text("")
        path.chmod(0o666)
        with self.assertRaisesRegex(PermissionError, "private regular"):
            runtime.status(self.state)

    def test_status_detects_runtime_lease_without_using_pid(self):
        self.prepare()
        path = self.state / "executive-pilot" / "runtime.lock"
        with runtime._lease(path):
            self.assertTrue(runtime.status(self.state)["process_lease_held"])
        self.assertFalse(runtime.status(self.state)["process_lease_held"])

    def test_start_requires_foreground_terminal(self):
        self.prepare()
        with (
            patch.object(sys.stdin, "isatty", return_value=False),
            self.assertRaisesRegex(PermissionError, "foreground"),
        ):
            runtime.start(self.state)

    def test_start_requires_bridge_before_cli_probe(self):
        self.prepare()
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe") as probe,
        ):
            with self.assertRaisesRegex(PermissionError, "scoped executive service"):
                runtime.start(self.state)
            probe.assert_not_called()

    def test_synthetic_launch_records_attempt_and_requires_explicit_resume(self):
        manifest = self.prepare(enable_mcp=False)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=7) as foreground,
        ):
            self.assertEqual(runtime.start(self.state), 7)
            receipt = runtime.status(self.state)["last_launch"]
            self.assertEqual(
                receipt["native_session_id"], manifest["native_session_id"]
            )
            self.assertEqual(receipt["state"], "process_exited")
            self.assertEqual(receipt["exit_code"], 7)
            self.assertEqual(len(foreground.call_args.args[1]), 2)
            with self.assertRaisesRegex(PermissionError, "explicit resume"):
                runtime.start(self.state)
            self.assertEqual(runtime.start(self.state, resume=True), 7)
            self.assertIn("--resume", foreground.call_args.args[0]["argv"])

    def test_missing_cli_capability_refuses_before_launch_journal(self):
        self.prepare(enable_mcp=False)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(
                runtime, "probe", return_value={"missing_flags": ["--restricted"]}
            ),
            patch.object(runtime, "_foreground") as foreground,
        ):
            with self.assertRaisesRegex(PermissionError, "required pilot flags"):
                runtime.start(self.state)
            foreground.assert_not_called()
        self.assertIsNone(runtime.status(self.state)["last_launch"])

    def test_reopen_cli_prints_resume_instruction_without_launching_or_traceback(self):
        from odin.__main__ import main

        manifest = self.prepare(enable_mcp=False)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe", return_value={"missing_flags": []}),
            patch.object(runtime, "_foreground", return_value=0),
        ):
            runtime.start(self.state)
        receipt = runtime.status(self.state)["last_launch"]
        error_output = io.StringIO()
        with (
            patch.object(
                sys, "argv", ["odin", "--state", str(self.state), "executive-start"]
            ),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(runtime, "probe") as probe,
            patch.object(runtime, "_socket_ready") as bridge,
            patch.object(runtime, "_foreground") as foreground,
            redirect_stderr(error_output),
            self.assertRaises(SystemExit) as stopped,
        ):
            main()
        self.assertEqual(stopped.exception.code, 2)
        self.assertIn("executive-start --resume-session", error_output.getvalue())
        self.assertNotIn("Traceback", error_output.getvalue())
        probe.assert_not_called()
        bridge.assert_not_called()
        foreground.assert_not_called()
        current = runtime.status(self.state)
        self.assertEqual(current["last_launch"], receipt)
        self.assertEqual(
            current["configuration"]["native_session_id"], manifest["native_session_id"]
        )


if __name__ == "__main__":
    unittest.main()
