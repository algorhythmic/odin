# Feature: Voice messages over Telegram

> **Status:** Scoped, not implemented. Pick up after Phase 3 completes.
> **Effort estimate:** 2-3 days for a working v1.
> **Priority:** Quality-of-life. Unlocks hands-free use cases (driving,
> walking) but doesn't block any other Saga work.

Lets the operator send voice notes to Odin's bot and receive Odin's
replies as voice messages instead of text. Use case: driving and you
want to hear the morning session status, or speaking a quick redirect
without typing.

## Telegram capability

Telegram natively carries voice in both directions:

- **Inbound:** user records a voice note in the Telegram client; the
  bot receives it via the `voice` message type as an Opus-encoded
  `.ogg` file
- **Outbound:** the bot sends voice via the `sendVoice` Bot API
  method; user's client auto-plays it inline with the waveform UI
  (distinct from `sendAudio`, which delivers as a downloadable music
  file)

Telegram itself does NOT do speech-to-text or text-to-speech. That's
a processing layer Saga adds.

## Architecture: sidecar, not plugin extension

Two paths to add voice to Saga:

| Approach | Pros | Cons |
|---|---|---|
| **Extend `claude-plugins-official/telegram`** | Stays in one place; voice is "first-class" in the channel API | Significant TypeScript/Bun work; needs upstream acceptance to avoid maintaining a fork; couples Saga to plugin internals |
| **Sidecar (recommended)** | Matches Saga's existing pattern (ratatoskr); no plugin changes; can swap STT/TTS engines independently; can be added incrementally | Two consumers polling the same bot need careful `getUpdates` offset coordination |

Recommended: **sidecar approach**. Matches the Saga architectural
pattern of "Claude Code sessions can't watch directories or do
heavy IO; sidecars do." A new `saga-voice` (or aptly-named) container
on the same VM that:

1. **Reads voice messages** from the Telegram bot. Cleanest version:
   the existing channel plugin emits voice messages as a recognizable
   text marker (e.g., `[voice: <download_url>]`) that the sidecar
   intercepts via a file watcher on Odin's incoming channel queue. If
   that's not feasible, the sidecar polls the Bot API directly with a
   coordinated `getUpdates` offset — but parallel polling is fragile.
2. **Pipes the audio through STT** to text.
3. **Drops the transcribed text** into
   `/opt/saga/odin-ws/incoming-voice/<timestamp>.txt`.
4. **Ratatoskr (or a new watcher) picks it up** and `tmux send-keys`
   the text into Odin's pane as if the user had typed it. Odin
   processes it normally — no change to Odin's own workflow.
5. **For outbound:** Odin marks responses for voice delivery (e.g.,
   `[VOICE]: Three dvergar running, all healthy.`) which ratatoskr
   routes to `/opt/saga/odin-ws/outgoing-voice/`. The voice sidecar
   watches that dir, TTS-converts the text, and sends via `sendVoice`.

This keeps the existing text channel intact, makes voice opt-in per
message, and isolates STT/TTS concerns from the orchestration layer.

## STT/TTS engine choice

Three tiers; pick by cost vs control:

| Approach | Cost | Latency | Quality | Saga RAM impact |
|---|---|---|---|---|
| **OpenAI Whisper API + OpenAI TTS API** | ~$0.006/min STT, ~$15/M chars TTS | ~1-2s round-trip | Excellent | ~zero (cloud) |
| **Local Whisper (small/medium) + Piper TTS** | $0 ongoing | 1-3× realtime | Whisper excellent, Piper good | 500 MB-1.5 GB on whichever box runs it |
| **ElevenLabs TTS (with API for STT)** | ~$5-22/mo | ~1-2s | Best-in-class voices, character options | ~zero |

**Recommendation: OpenAI APIs for v1.** Cheap (probably $1-3/month for
typical use), high quality, no homelab RAM pressure. Local Whisper
saves money but the homelab is already reasonably loaded; the marginal
savings don't justify the operational complexity.

If voice usage scales heavily and the API bill creeps past ~$10/month,
revisit local Whisper on a dedicated LXC at .19 (the unused slot
mentioned in `docs/history/HOMELAB_NETWORKING_PROJECT.md`). Piper TTS is so
lightweight it could run on the saga-docker VM directly without
issue.

## Implementation prerequisites

Before this feature can be built:

- [ ] Phase 3 ships (spec ingestion → decomposition → dvergr launch
      pipeline working end-to-end). Voice integrates with Odin's
      response pipeline; that pipeline needs to exist first.
- [ ] OpenAI API key obtained and stored at
      `/opt/saga/secrets/openai-api-key` with 0600 root perms (same
      pattern as the Telegram bot token).
- [ ] Decision on the inbound interception model — does the channel
      plugin emit voice-message markers we can intercept, or do we
      need parallel polling? Worth a 30-min investigation of the
      plugin's source before designing the sidecar.

## Action items for when picked up

1. Investigate the official telegram channel plugin's handling of
   `voice` message type. Does it pass through to Odin's session as
   a text marker, drop them silently, or something else? Determines
   whether interception is via Odin's channel queue or via parallel
   Bot API polling.
2. Scaffold `containers/voice/Dockerfile` mirroring the keepalive /
   bragi pattern: thin Python container, mounts the Odin workspace
   (RW for the voice queues), runs a long-lived `voice-sidecar.py`.
3. Implement `voice-sidecar.py`:
   - Watch incoming channel queue for voice markers; download audio;
     send to OpenAI Whisper; drop text into
     `/opt/saga/odin-ws/incoming-voice/`
   - Watch `/opt/saga/odin-ws/outgoing-voice/` for Odin-generated TTS
     requests; send through OpenAI TTS; deliver via `sendVoice`
4. Extend `ratatoskr.py` with a fourth inotify watcher on
   `incoming-voice/` that send-keys the transcribed text into Odin's
   pane (mirrors the existing mimir-pending pattern).
5. Update `odin/CLAUDE.md` with the `[VOICE]:` marker convention so
   Odin knows when to request voice delivery (probably driven by an
   incoming-message marker like `[from-voice]:` so Odin can choose to
   reply in kind).
6. Update `docs/architecture/SETUP.md` with the new step (OpenAI key file, voice
   container build + launch).
7. End-to-end test: voice note from phone → transcript appears in
   Odin's pane → Odin replies with `[VOICE]: ...` → audio plays back
   in the Telegram client.

## Why this isn't urgent

- Phase 3 is the load-bearing capability; voice is icing
- Text already works fine for all current use cases
- Adding voice before Phase 3 ships means two unfinished features
  competing for attention
- Estimated RAM/cost impact of postponing: zero (text continues to
  work indefinitely)

## Cross-references

- The existing Telegram setup: `docs/architecture/SETUP.md` § 10-12
- Odin's persona and Telegram interaction style: `odin/CLAUDE.md`
- Sidecar architecture pattern: `odin/scripts/ratatoskr.py` and
  `docs/architecture/ARCHITECTURE.md` § "Three rules for message passing"
- Phase plan and where this feature lands: `saga-spec.md` § 12
  (Phase 4+ candidate)
