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
            "repository-import",
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
    parser.add_argument("--claude-config", help="dedicated Odin Claude login directory")
    parser.add_argument("--executive-project", help="bind private executive socket to this project")
    parser.add_argument("--resume-session", action="store_true", help="resume the prepared native executive session")
    parser.add_argument("--repository-reads", action="store_true", help="enable read-only checkout tools before starting the executive")
    parser.add_argument("--repository", help="Git repository whose committed source snapshot to import")
    parser.add_argument(
        "--config",
        help="experimental role configuration JSON; live dispatch remains disabled",
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
        elif args.action == "executive-enable-repository-reads":
            try:
                print(canonical(executive_runtime.enable_repository_reads(state)))
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
        from .gateway import Gateway, GatewayContext
        from .orchestration_config import OrchestrationConfig

        gateway = Gateway(service, OrchestrationConfig(args.config))
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
                self.wfile.write((canonical(result) + "\n").encode())

        from contextlib import ExitStack
        import selectors
        import stat

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
                while True:
                    for key, _ in selector.select(timeout=0.5):
                        key.fileobj._handle_request_noblock()
                    service.tick()
        except KeyboardInterrupt:
            pass
        finally:
            for path in created:
                os.unlink(path)


if __name__ == "__main__":
    main()
