"""Local service CLI and explicit native Claude Code executive pilot."""

import argparse
import os
import socket
import socketserver
import sys

from .contracts import canonical, identifier, strict_loads
from .service import Service


def _socket_command(address, command):
    frame = (canonical(command) + "\n").encode()
    if len(frame) > 1048576:
        raise ValueError("command exceeds local transport budget")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(30)
        client.connect(address)
        client.sendall(frame)
        with client.makefile("rb") as stream:
            raw = stream.readline(1048577)
    if len(raw) > 1048576 or not raw.endswith(b"\n"):
        raise ValueError("invalid local service response")
    return strict_loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        required=False,
        help="private local state directory outside the checkout",
    )
    parser.add_argument(
        "action",
        choices=[
            "demo",
            "orchestration-demo",
            "continuity-demo",
            "integration-demo",
            "serve",
            "status",
            "stop",
            "command",
            "resume",
            "acknowledge",
            "memory",
            "evidence",
            "capabilities",
            "evaluate",
            "executive-prepare",
            "executive-status",
            "executive-login",
            "executive-start",
            "executive-new-session",
            "executive-enable-repository-reads",
            "executive-enable-development",
            "executive-enable-development-loop",
            "repository-import",
            "delegation-configure",
            "development-configure",
            "development-start",
            "development-status",
            "development-control",
        ],
    )
    parser.add_argument("--reason", default="operator requested stop")
    parser.add_argument("--request", help="gateway command or evaluation request JSON")
    parser.add_argument(
        "--fixture-evidence",
        action="store_true",
        help="allow synthetic fixture evidence for offline evaluation only",
    )
    parser.add_argument("--surface", choices=["terminal", "voice"], default="terminal")
    parser.add_argument(
        "--project", help="explicit project ID for resume, memory or evidence"
    )
    parser.add_argument("--source", help="exact local memory source ID for evidence")
    parser.add_argument(
        "--revision", type=int, help="exact source revision for evidence"
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=65536,
        help="maximum exact evidence response size; evidence is never truncated",
    )
    parser.add_argument("--delivery", help="delivered view ID to acknowledge")
    parser.add_argument("--loop", help="exact development loop ID")
    parser.add_argument("--control", choices=["pause", "resume", "stop"])
    parser.add_argument("--operation-id", help="stable ID for a retried development command")
    parser.add_argument("--claude-config", help="dedicated Odin Claude login directory")
    parser.add_argument("--executive-project", help="bind private executive socket to this project")
    parser.add_argument("--resume-session", action="store_true", help="resume the prepared native executive session")
    parser.add_argument("--repository-reads", action="store_true", help="enable read-only checkout tools before starting the executive")
    parser.add_argument("--repository", help="Git repository whose committed source snapshot to import")
    parser.add_argument(
        "--config",
        help="experimental role configuration JSON; live dispatch remains disabled",
    )
    parser.add_argument(
        "--workspace-root",
        action="append",
        default=[],
        help="directory under which delegation workspaces may be created (repeatable)",
    )
    parser.add_argument("--codex-home", help="CODEX_HOME for delegated Codex workers")
    parser.add_argument("--claude-model", default="claude-sonnet-5-5", help="default delegated Claude Code model")
    parser.add_argument("--codex-model", help="default delegated Codex model")
    parser.add_argument("--turn-timeout", type=int, default=1800, help="delegated turn wall-clock limit in seconds")
    parser.add_argument(
        "--lineage-policy",
        choices=["exclusive", "shared_accepted"],
        default="exclusive",
        help="refuse (exclusive) or accept worker turns on a credential lineage another process owns",
    )
    args = parser.parse_args()
    from pathlib import Path

    if args.fixture_evidence and args.action != "evaluate":
        parser.error("--fixture-evidence applies only to evaluate")
    if args.repository_reads and args.action != "executive-start":
        parser.error("--repository-reads applies only to executive-start")
    if args.action == "capabilities":
        from .capabilities import inventory

        print(canonical(inventory()))
        return
    if args.action == "evaluate":
        from .contracts import Contracts
        from .evaluation import evaluate

        if not args.request:
            parser.error(
                "evaluate requires --request JSON with config and observations"
            )
        request = strict_loads(Path(args.request).read_bytes())
        Contracts().validate("evaluation-request", request)
        print(
            canonical(
                evaluate(
                    request["config"],
                    request["observations"],
                    allow_fixture_evidence=args.fixture_evidence,
                )
            )
        )
        return
    if not args.state:
        parser.error("this action requires --state")

    state = Path(args.state).resolve()
    from .contracts import ROOT

    if state == ROOT or ROOT in state.parents:
        parser.error("runtime state must be outside the repository")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.stat().st_mode & 0o077:
        parser.error("state directory must have mode 0700")
    if args.action.startswith("executive-"):
        from . import executive_runtime

        if args.action == "executive-prepare":
            if not args.claude_config:
                parser.error("executive-prepare requires --claude-config")
            from .executive_service import prepare_project

            project = args.project
            if (state / "executive-pilot" / "manifest.json").exists():
                existing = executive_runtime.status(state)["configuration"]
                project = project or existing["project"]
            if args.project:
                prepare_project(state, project)
            project = project or identifier()
            prepared = executive_runtime.prepare(
                state, config_dir=args.claude_config, project=project,
            )
            prepare_project(state, project, create=not bool(args.project))
            print(canonical(prepared))
        elif args.action == "executive-status":
            print(canonical(executive_runtime.status(state)))
        elif args.action == "executive-login":
            sys.exit(executive_runtime.login(state))
        elif args.action == "executive-new-session":
            print(canonical(executive_runtime.new_session(state)))
        elif args.action == "executive-enable-development-loop":
            try:
                print(canonical(executive_runtime.enable_development_loop(state)))
            except PermissionError as error:
                parser.exit(2, f"odin: {error}\n")
        elif args.action in ("executive-enable-repository-reads", "executive-enable-development"):
            try:
                enable = (
                    executive_runtime.enable_development
                    if args.action == "executive-enable-development"
                    else executive_runtime.enable_repository_reads
                )
                print(canonical(enable(state)))
            except PermissionError as error:
                parser.exit(2, f"odin: {error}\n")
        else:
            try:
                if args.repository_reads:
                    executive_runtime.enable_repository_reads(state)
                result = executive_runtime.start(state, resume=args.resume_session)
            except PermissionError as error:
                parser.exit(2, f"odin: {error}\n")
            sys.exit(result)
        return
    if args.action in (
        "demo",
        "orchestration-demo",
        "continuity-demo",
        "integration-demo",
    ):
        if args.action == "demo":
            from .demo import run

            result = run(state)
        elif args.action == "continuity-demo":
            from .continuity_demo import run

            result = run(state)
        elif args.action == "integration-demo":
            from .integration_demo import run

            result = run(state)
        else:
            from .orchestration_config import OrchestrationConfig
            from .orchestration_demo import run

            result = run(state, OrchestrationConfig(args.config))
        print(canonical(result))
        return
    address = str(state / "service.sock")
    if args.action == "development-configure":
        from .development_evaluator import configure

        if not args.request:
            parser.error("development-configure requires --request configuration JSON")
        path = configure(state, strict_loads(Path(args.request).read_bytes()))
        print(canonical({
            "written": str(path),
            "activation": "restart serve to load this configuration",
        }))
        return
    if args.action in {"development-start", "development-status", "development-control"}:
        from .contracts import Contracts

        if args.action == "development-start":
            if not args.request:
                parser.error("development-start requires --request start payload JSON")
            payload = strict_loads(Path(args.request).read_bytes())
        else:
            if not args.project:
                parser.error("development commands require --project")
            payload = {"project": args.project}
            if args.loop:
                payload["loop_id"] = args.loop
            if args.action == "development-control":
                if not args.loop or not args.control:
                    parser.error("development-control requires --loop and --control")
                payload["action"] = args.control
        action = {
            "development-start": "loop_start",
            "development-status": "loop_status",
            "development-control": "loop_control",
        }[args.action]
        Contracts().validate_definition("development-loop-command", action, payload)
        command = {
            "schema_version": 1, "operation_id": args.operation_id or identifier(),
            "action": action, "payload": payload,
        }
        Contracts().validate("gateway-command", command)
        try:
            response = _socket_command(address, {"surface": "terminal", "command": command})
        except (OSError, ValueError):
            parser.exit(
                2, "odin: development command outcome unavailable; inspect status or "
                "retry identical arguments with --operation-id "
                + command["operation_id"] + "\n",
            )
        print(canonical(response))
        if "error" in response:
            sys.exit(1)
        return
    if args.action == "delegation-configure":
        from .delegation import default_config, write_config

        if not args.workspace_root:
            parser.error("delegation-configure requires at least one --workspace-root")
        try:
            config = default_config(
                claude_config_dir=args.claude_config,
                workspace_roots=args.workspace_root,
                codex_home=args.codex_home,
                claude_model=args.claude_model,
                codex_model=args.codex_model,
                turn_timeout_seconds=args.turn_timeout,
                lineage_policy=args.lineage_policy,
            )
            path = write_config(state, config)
        except (ValueError, PermissionError, OSError) as error:
            parser.exit(2, f"odin: {error}\n")
        print(canonical({"written": str(path), "harnesses": sorted(config["harnesses"]),
                         "workspace_roots": config["workspace_roots"],
                         "activation": "restart serve to load this configuration"}))
        return
    if args.action == "repository-import":
        from .repository_memory import prepare

        if not args.project:
            parser.error("repository-import requires --project")
        batches = prepare(Path(args.repository) if args.repository else ROOT, args.project)
        results = []
        for payload in batches:
            request = {
                "surface": args.surface,
                "command": {
                    "schema_version": 1, "operation_id": identifier(),
                    "action": "repository_import", "payload": payload,
                },
            }
            try:
                response = _socket_command(address, request)
            except (OSError, ValueError):
                parser.exit(2, "odin: import outcome unavailable; retry the same committed snapshot to reconcile.\n")
            if "error" in response:
                print(canonical(response))
                sys.exit(1)
            results.append(response["result"])
        print(canonical({"project": args.project, "batches": results}))
        return
    if args.action in (
        "status",
        "stop",
        "command",
        "resume",
        "acknowledge",
        "memory",
        "evidence",
    ):
        if args.action in ("resume", "memory", "evidence"):
            if not args.project:
                parser.error(
                    "resume, memory and evidence require --project; no implicit routing"
                )
            payload = {"project": args.project}
            if args.action == "evidence":
                if not args.source or args.revision is None or args.revision < 1:
                    parser.error("evidence requires --source and a positive --revision")
                if not 2048 <= args.max_bytes <= 1048576:
                    parser.error("--max-bytes must be between 2048 and 1048576")
                payload.update(
                    source_id=args.source,
                    revision=args.revision,
                    max_bytes=args.max_bytes,
                )
            command = {
                "surface": args.surface,
                "command": {
                    "schema_version": 1,
                    "operation_id": identifier(),
                    "action": {
                        "resume": "resume",
                        "memory": "memory_snapshot",
                        "evidence": "memory_source_read",
                    }[args.action],
                    "payload": payload,
                },
            }
        elif args.action == "acknowledge":
            if not args.delivery:
                parser.error("acknowledge requires --delivery")
            command = {
                "surface": args.surface,
                "command": {
                    "schema_version": 1,
                    "operation_id": identifier(),
                    "action": "view_ack",
                    "payload": {"delivery_id": args.delivery},
                },
            }
        elif args.action == "command":
            if not args.request:
                parser.error("command requires --request JSON file")
            from .contracts import Contracts

            command = strict_loads(Path(args.request).read_bytes())
            Contracts().validate("gateway-command", command)
            # Surface identifies operator input only, never an actor or a grant.
            command = {"surface": args.surface, "command": command}
        else:
            command = {
                "schema_version": 1,
                "operation_id": identifier(),
                "action": args.action,
                "reason": args.reason,
            }
        response = _socket_command(address, command)
        print(canonical(response))
        if "error" in response:
            sys.exit(1)
        return
    with Service(state) as service:
        service.recover()
        from .coordination import Actor
        from .delegation import load_config
        from .development_evaluator import EvaluatorRunner, load_config as evaluator_config
        from .gateway import Gateway, GatewayContext
        from .orchestration_config import OrchestrationConfig

        delegation_config = load_config(state)
        development_config = evaluator_config(state)
        gateway = Gateway(
            service, OrchestrationConfig(args.config), delegation_config=delegation_config,
            evaluator_configured=development_config is not None,
        )
        evaluator = EvaluatorRunner(gateway.development_loop, state, development_config)
        if args.executive_project:
            gateway.coordination._project(args.executive_project)
        # The namespace lock proves no other service using this state is active.
        if os.path.lexists(address):
            import stat

            if not stat.S_ISSOCK(os.lstat(address).st_mode):
                raise ValueError("refusing to replace a non-socket path")
            os.unlink(address)

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.request.settimeout(5)
                try:
                    raw = self.rfile.readline(1048577)
                    if not raw:
                        return
                    if len(raw) > 1048576 or not raw.endswith(b"\n"):
                        raise ValueError("invalid request frame")
                    request = strict_loads(raw)
                    if getattr(self.server, "executive_project", None):
                        from .executive_service import submit_executive

                        result = submit_executive(
                            gateway, request, self.server.executive_project
                        )
                    elif set(request) == {"surface", "command"}:
                        if request["surface"] not in ("terminal", "voice"):
                            raise ValueError("unsupported operator surface")
                        context = GatewayContext(
                            request["surface"], Actor("operator", "local-operator")
                        )
                        result = gateway.submit(request["command"], context=context)
                    else:
                        service.store.contracts.validate("operator-command", request)
                        payload = (
                            {"reason": request["reason"]}
                            if request["action"] == "stop"
                            else {}
                        )
                        gateway.submit(
                            {
                                "schema_version": 1,
                                "operation_id": request["operation_id"],
                                "action": request["action"],
                                "payload": payload,
                            },
                            context=GatewayContext(
                                "terminal", Actor("operator", "local-operator")
                            ),
                        )
                        result = service.status()
                    # Delivery is outside the gateway's atomic local transaction.
                    # Stop returns queued/uncertain until the fake receipt arrives.
                    if service.store.dispatch_enabled:
                        service.store.dispatch(service.backend)
                        service.mirror.refresh(service.backend)
                except Exception as error:
                    # Keep protocol errors bounded; never dump a schema or input body.
                    result = {"error": type(error).__name__, "label": service.label}
                    from .delegation import DelegationRefused

                    if isinstance(error, DelegationRefused):
                        result["detail"] = str(error)
                self.wfile.write((canonical(result) + "\n").encode())
                self.wfile.flush()
                # Runner launches follow the recorded command and its reply;
                # a launch problem is a turn failure, never a command failure.
                try:
                    if not service.store.stopped():
                        gateway.delegation.launch_pending()
                except Exception as error:
                    print(
                        "delegation launch failed: " + type(error).__name__,
                        file=sys.stderr,
                        flush=True,
                    )

        import selectors
        import stat
        from contextlib import ExitStack

        addresses = [address]
        if args.executive_project:
            addresses.append(str(state / "executive.sock"))
        created = []
        try:
            with ExitStack() as stack:
                selector = stack.enter_context(selectors.DefaultSelector())
                for path in addresses:
                    if os.path.lexists(path):
                        if not stat.S_ISSOCK(os.lstat(path).st_mode):
                            raise ValueError("refusing to replace non-socket path")
                        os.unlink(path)
                    server = stack.enter_context(socketserver.UnixStreamServer(path, Handler))
                    created.append(path)
                    os.chmod(path, 0o600)
                    server.executive_project = args.executive_project if path != address else None
                    selector.register(server, selectors.EVENT_READ)
                print("Fixture service ready: " + address, flush=True)
                # A detached service is stopped with SIGTERM; treat it like Ctrl-C
                # so sockets are removed and the store closes cleanly.
                import signal

                def _terminate(*_):
                    raise KeyboardInterrupt

                signal.signal(signal.SIGTERM, _terminate)
                if delegation_config is not None:
                    print(
                        "Delegation enabled for harnesses: "
                        + ", ".join(sorted(delegation_config["harnesses"])),
                        flush=True,
                    )
                while True:
                    for key, _ in selector.select(timeout=0.5):
                        key.fileobj._handle_request_noblock()
                    service.tick()
                    try:
                        gateway.delegation.tick()
                    except Exception as error:  # Keep the service up; report it.
                        print(
                            "delegation tick failed: " + type(error).__name__,
                            file=sys.stderr,
                            flush=True,
                        )
                    if args.executive_project:
                        from .executive_loop_hook import drain_spool
                        from .executive_service import submit_executive

                        def capture(command):
                            # Keep a failed capture pending without blocking other
                            # entries. Never reconnect to this single-threaded server.
                            try:
                                return submit_executive(
                                    gateway, {"command": command}, args.executive_project
                                )
                            except Exception as error:
                                return {"error": type(error).__name__}

                        try:
                            drain_spool(
                                state, submit=capture, project=args.executive_project
                            )
                        except Exception as error:
                            print("development capture failed: " + type(error).__name__,
                                  file=sys.stderr, flush=True)
                    try:
                        evaluator.tick()
                    except Exception as error:
                        print("development evaluator tick failed: " + type(error).__name__,
                              file=sys.stderr, flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            for path in created:
                os.unlink(path)


if __name__ == "__main__":
    main()
