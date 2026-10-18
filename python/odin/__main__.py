"""Local development CLI. No live backend, credentials or model invocation."""

import argparse
import os
import socket
import socketserver
import sys

from .contracts import canonical, identifier, strict_loads
from .service import Service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        required=True,
        help="private local state directory outside the checkout",
    )
    parser.add_argument(
        "action",
        choices=["demo", "orchestration-demo", "serve", "status", "stop", "command"],
    )
    parser.add_argument("--reason", default="operator requested stop")
    parser.add_argument(
        "--request", help="validated gateway command JSON, for the command action"
    )
    parser.add_argument("--surface", choices=["terminal", "voice"], default="terminal")
    parser.add_argument(
        "--config",
        help="experimental role configuration JSON; live dispatch remains disabled",
    )
    args = parser.parse_args()
    from pathlib import Path

    state = Path(args.state).resolve()
    from .contracts import ROOT

    if state == ROOT or ROOT in state.parents:
        parser.error("runtime state must be outside the repository")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.stat().st_mode & 0o077:
        parser.error("state directory must have mode 0700")
    if args.action in ("demo", "orchestration-demo"):
        if args.action == "demo":
            from .demo import run

            result = run(state)
        else:
            from .orchestration_config import OrchestrationConfig
            from .orchestration_demo import run

            result = run(state, OrchestrationConfig(args.config))
        print(canonical(result))
        return
    address = str(state / "service.sock")
    if args.action in ("status", "stop", "command"):
        if args.action == "command":
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
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(10)
            client.connect(address)
            client.sendall((canonical(command) + "\n").encode())
            with client.makefile("rb") as stream:
                response = strict_loads(stream.readline(1048577))
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
                    if len(raw) > 1048576 or not raw.endswith(b"\n"):
                        raise ValueError("invalid request frame")
                    request = strict_loads(raw)
                    if set(request) == {"surface", "command"}:
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

        with socketserver.UnixStreamServer(address, Handler) as server:
            os.chmod(address, 0o600)
            server.timeout = 0.5
            print("Fixture service ready: " + address, flush=True)
            try:
                while True:
                    server.handle_request()
                    service.tick()
            except KeyboardInterrupt:
                pass
            finally:
                os.unlink(address)


if __name__ == "__main__":
    main()
