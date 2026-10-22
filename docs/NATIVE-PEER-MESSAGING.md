# Native peer messaging

ODIN-ADR-032 uses Claude Code's existing peer tools for direct coordination.
This is an opt-in local experiment. It adds no custom peer socket, relay or
second task store.

## Transport choice

| Need | Primitive | Reason |
| --- | --- | --- |
| Clarify work during a live Claude turn | Native `ListAgents` / `SendMessage` | Delivery between tool calls; a tool already running is not interrupted |
| Wake an idle native executive with a useful finding | Native peer message | Can start a new turn without terminal input |
| Assign work, resume an exited worker, collect and accept a result | Odin delegation service | Durable identities, owned commitments and explicit acceptance |
| Deliver controller stages and capture completion | Existing Odin MCP channel and native hook | Retains stage correlation, acknowledgements and restart reconciliation |
| Talk directly to a Codex worker | Not implemented by this primitive | Native Claude peer messaging is not a cross-provider adapter |

Native messages are plain text, may be held/refused, and consume model usage
when delivered. A `claude -p` worker receives only while its process is alive.
`accept` permits inbound peers broadly, subject to native settings precedence;
it is not an Odin project allowlist. See the primary
[Claude peer messaging documentation](https://code.claude.com/docs/en/cross-session-messaging).

## Configuration

Stage the executive setting without changing its running process:

```bash
python -m odin --state "$ODIN_PILOT_STATE" executive-configure-peer-messaging \
  --native-peer-messaging
```

Then exit and explicitly resume the same executive with the usual launcher.
The native UUID, dedicated login, context configuration, MCP channel and hooks
are preserved. The launch supplies inline `--settings` JSON, merging Odin's
loop hooks when enabled, and `--name odin-exec-NATIVE_UUID`. User/global Claude
settings are not rewritten. `executive-status` reports configured and pending
states separately. The launch receipt records the requested setting; delivery
remains unverified until observed.

To remove Odin's override on the next resume, use the same configuration
command with `--no-native-peer-messaging`. This returns to inherited native
settings/defaults; it does not set `refuse`.

For a new `odin_delegation_session` create request, include
`"native_peer_messaging": true`. This is a Claude-only option. The service
requires a known Claude version at least 2.1.224 and persists the requested
option. A worker launches with `--settings '{"crossSessionInbound":"accept"}'`
and `--name odin-work-NATIVE_UUID`. The name survives resume and changes if a
failed launch requires rotating the native identity. Session status returns
`native_peer_name` and `native_peer_transport: requested_unverified`; use native
`ListAgents` to resolve the exact live peer. Odin does not promise the process
is discoverable merely because its name is configured. The adapter's generic
`inject_mid_turn` capability remains false: Odin has not implemented that
service operation.

An operator can set `default_native_peer_messaging: true` in the Claude section
of delegation configuration, or use `delegation-configure
--native-peer-messaging` alongside all existing required configuration options.
Do not regenerate a live configuration while omitting its other settings.
Existing session options are unchanged; per-session false overrides that default.

## Records and bounded communication

The native prompt asks participants to resolve exact peers, include correlation
and assignment IDs, batch useful facts, and avoid acknowledgement loops.
Those are model instructions, not a service-enforced message budget or sender
authentication. Native messages cannot alter Odin records by themselves. A
participant uses the existing Odin tools for assignments, accepted scope,
results and dispositions; normal service checks still apply. A delivered
message or idle notification is not proof of task completion.

If delivery is ambiguous, inspect native responses and Odin state before
retrying. If a worker has exited, use the existing durable follow-up/resume
path. Peer text must not become a second automatic retry mechanism. The
controller's MCP channel is retained; a future replacement needs its own
replay/recovery evidence.

## Verification

Synthetic tests cover opt-in settings, version checks, staged configuration,
hook/context preservation, disabling the override, unique names, resume and
unsupported harnesses. Real acceptance must record the live peer discovery,
actual `SendMessage` calls, correlated receipt/reply, and resulting Odin state.
Test a worker receiving during a live turn and an executive waking from idle;
then verify that an exited worker still uses the durable follow-up. Retain
native evidence privately, outside this repository. Do not commit transcripts.
