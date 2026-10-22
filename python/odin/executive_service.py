"""Local executive socket binding; no remote operator authentication.

The native harness has no socket or filesystem tools. Its explicitly configured
MCP bridge can use this socket, which supplies one fixed identity and scope.
Same-user processes are trusted, as with the existing local operator socket.
"""

from .coordination import Actor
from .gateway import GatewayContext


def submit_executive(gateway, request, project):
    if not isinstance(request, dict) or set(request) != {"command"}:
        raise PermissionError("executive command envelope required")
    return gateway.submit(
        request["command"],
        context=GatewayContext(
            "harness", Actor("coordinator", "fable-executive"), (project,)
        ),
    )


def prepare_project(state, project=None, *, create=False):
    """Create a real empty pilot project, never seed production from fixtures."""
    from .contracts import identifier
    from .service import Service
    from .store import now

    with Service(state) as service:
        if project is not None:
            try:
                record = service.store.get(project)
            except KeyError:
                if not create:
                    raise
            else:
                if record["record_type"] != "Project":
                    raise ValueError("executive scope must reference a Project")
                return project
        stamp = now()
        record = {
            "schema_version": 1,
            "record_type": "Project",
            "id": project or identifier(),
            "rev": 1,
            "created_at": stamp,
            "updated_at": stamp,
            "name": "Odin executive pilot",
            "sources": [],
            "delegations": [],
            "interface_decision_owner": None,
        }
        service.store.create(record)
        return record["id"]
