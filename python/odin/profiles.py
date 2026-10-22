"""Deny-by-default fixture tool boundary. Does not sandbox a real harness."""

from .contracts import Contracts


class ToolBoundary:
    def __init__(self, profile, handlers):
        Contracts().validate("profile", profile)
        self.profile = profile
        self.handlers = handlers

    def call(self, tool, arguments):
        if tool not in self.profile["allowed_tools"] or tool not in self.handlers:
            raise PermissionError("tool unavailable under " + self.profile["name"])
        return self.handlers[tool](arguments)

    def native_child(self, *args, **kwargs):
        raise PermissionError(
            "native children disabled until X-15 and adapter confinement checks"
        )
