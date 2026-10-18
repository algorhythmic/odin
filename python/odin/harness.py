"""Claude Agent SDK capability boundary; live launches remain gated.

The public SDK has a stateful ClaudeSDKClient and interrupt method, but the
installed package and CLI are not pinned here. This module does not infer
runtime enforcement from a Python option or from a mocked transport.
"""

from importlib import metadata

CAPABILITIES = (
    "start",
    "resume",
    "interrupt",
    "retire",
    "transcript",
    "permission_relay",
    "profile_enforcement",
    "model_resolution",
    "effort_resolution",
    "budget_enforcement",
    "native_children",
    "credential_isolation",
)


class CapabilityRefusal(PermissionError):
    pass


class ClaudeAgentSDKAdapter:
    """A concrete SDK seam with explicit evidence, never an implied live probe.

    An injected client factory is for protocol tests. A real client factory
    may only be enabled after the installed SDK/CLI pair and the host's
    credential, data and process boundaries have been separately verified.
    """

    def __init__(self, client_factory=None, *, verified=None, protocol_test=False):
        self.client_factory = client_factory
        self.verified = frozenset(verified or ())
        self.protocol_test = protocol_test

    @staticmethod
    def probe():
        try:
            version = metadata.version("claude-agent-sdk")
        except metadata.PackageNotFoundError:
            version = None
        return {
            "adapter": "claude-agent-sdk-python",
            "installed_version": version,
            "sdk_api_reference": "https://github.com/anthropics/claude-agent-sdk-python",
            "supported_live": [],
            "fixture_protocol": ["start", "resume", "interrupt", "retire"],
            "unverified": list(CAPABILITIES),
            "reason": "installed SDK/CLI and enforcement probes are not pinned",
        }

    def require(self, names):
        if not self.protocol_test:
            raise CapabilityRefusal("live SDK transport remains disabled")
        missing = set(names) - self.verified
        if missing or self.client_factory is None:
            raise CapabilityRefusal(
                "unverified Claude Agent SDK capabilities: "
                + ", ".join(sorted(missing or {"client_factory"}))
            )
        if "native_children" in names:
            raise CapabilityRefusal("native children disabled until X-15")

    def execute(self, action, command):
        # Even a test client must pass profile, credential and data gates at
        # the SessionHost before this point. There is no implicit environment
        # or developer-login fallback.
        self.require(command["required_capabilities"] + [action])
        if command["profile"] == "subagent":
            raise CapabilityRefusal("native children disabled until X-15")
        client = self.client_factory(command)
        return client.execute(action, command)

    def lookup(self, operation_id):
        if not self.protocol_test or self.client_factory is None:
            raise CapabilityRefusal("SDK operation lookup has no verified transport")
        return self.client_factory(None).lookup(operation_id)


def build_denied_sdk_options(sdk, *, model, effort, resume=None):
    """Construct the documented Python SDK options for a tool-free probe.

    This builds a real ClaudeAgentOptions object if supplied the installed
    package. It intentionally cannot enable a planning class: no service MCP
    tools, PreToolUse enforcement, credential isolation, or cost cap have been
    verified on an exact SDK/CLI version. A controlled probe may use these
    options only in an isolated test process after its own launch gates.
    """
    if not model or effort not in {"low", "medium", "high", "xhigh", "max"}:
        raise ValueError("exact model and supported effort required")

    async def deny_tool(tool_name, input_data, context):
        return sdk.PermissionResultDeny(
            message="Odin profile gate has no verified live tool authority"
        )

    return sdk.ClaudeAgentOptions(
        model=model,
        effort=effort,
        resume=resume,
        setting_sources=[],
        tools=[],
        allowed_tools=[],
        permission_mode="dontAsk",
        can_use_tool=deny_tool,
        agents={},
        max_turns=1,
    )


class ClaudeSDKClientSession:
    """Direct binding to the SDK's stateful client lifecycle for probes.

    The caller owns the host's long-lived async context and must check all
    service and credential gates before calling ``open``. It is intentionally
    separate from SessionHost's synchronous durable journal until the daemon
    has an authenticated transport and a verified installed SDK/CLI pair.
    """

    def __init__(
        self, sdk, *, model, effort, native_session_id=None, protocol_test=False
    ):
        self.sdk = sdk
        self.options = build_denied_sdk_options(
            sdk, model=model, effort=effort, resume=native_session_id
        )
        self.client = None
        self.protocol_test = protocol_test

    async def open(self):
        client_type = getattr(self.sdk, "ClaudeSDKClient", None)
        if (
            not self.protocol_test
            or client_type is None
            or getattr(client_type, "__module__", "").startswith("claude_agent_sdk")
        ):
            raise CapabilityRefusal(
                "SDK launch disabled until dedicated credential, data policy, "
                "profile and budget enforcement probes are verified"
            )
        if self.client is not None:
            raise RuntimeError("SDK client already open")
        client = self.sdk.ClaudeSDKClient(options=self.options)
        await client.connect()
        self.client = client

    async def query(self, prompt):
        if self.client is None:
            raise RuntimeError("SDK client not open")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("nonempty prepared briefing required")
        await self.client.query(prompt)
        messages = []
        async for message in self.client.receive_response():
            messages.append(message)
        return messages

    async def interrupt(self):
        if self.client is None:
            raise RuntimeError("SDK client not open")
        await self.client.interrupt()

    async def close(self):
        if self.client is not None:
            try:
                await self.client.disconnect()
            finally:
                self.client = None
