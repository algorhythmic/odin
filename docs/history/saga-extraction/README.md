# Saga extraction history

This directory holds the evidence of what Odin inherited from Saga. The
subdirectories are **frozen snapshots**: exact source bytes, kept at
their original relative paths, including links that no longer resolve.
Never edit them. They establish what was inherited; they never override
Odin's current [decisions](../../DECISIONS.md), contract or roadmap.
Fix links in the live documents instead.

## Snapshot `2026-10-14-14fdab3`

| Field | Value |
|---|---|
| Source repository | `saga`, the operator's local checkout |
| Source commit | `14fdab3bce1a5a565176cec9db5d7dc8d1c15ada` (base HEAD at capture) |
| Captured at | 2026-10-14T17:44:08Z |
| Source status | every file clean and tracked at capture |
| Files | 35 ([manifest](../../provenance/EXTRACTION-MANIFEST.json)) |
| Handoff state | candidate; **not recorded**; the D14 gate is under review |

The manifest is metadata; the frozen files are the source bytes. Its
destination paths, treatments and adapted-output digests are finalized
separately after review; until then the table below describes the
adaptation performed. The extraction plan's earlier planning HEAD,
`9e0282353796e88732ce8fc657bca702695ea49f`, did not identify the
design bytes. The design was committed before capture, so this snapshot
supersedes that reference.

### Handoff instructions

The extraction was performed under the plan captured in this snapshot:
[`docs/design/ODIN-REPOSITORY-EXTRACTION.md`](2026-10-14-14fdab3/docs/design/ODIN-REPOSITORY-EXTRACTION.md).
It is a historical instruction set, not a live Odin document. Its
target layout, ownership table and completion checks were followed. Its
step 7 (recording the authority handoff in both repositories and
installing Saga's forwarding documents) and step 8 (the handoff receipt)
remain to be done.

### Source to destination

Paths are relative to the snapshot root; destinations are relative to
the repository root.

| Snapshot path | Odin destination | Treatment |
|---|---|---|
| `CLAUDE.md` | inputs to `AGENTS.md`, `CLAUDE.md`, `docs/DECISIONS.md` (inherited constraints) | reference |
| `README.md` | input to `README.md` | reference |
| `docs/DECISIONS.md` | `docs/DECISIONS.md` (Odin clauses carried verbatim) and `docs/provenance/DECISION-MAP.md` | split |
| `docs/ROADMAP.md` | `docs/ROADMAP.md` | split |
| `docs/design/ODIN-IO-CONTRACT.md` | `docs/design/ODIN-IO-CONTRACT.md` | adapted: Saga API appendix and worker transport replaced by consumer obligations and required capabilities |
| `docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md` | `docs/design/ODIN-IMPLEMENTATION-BLUEPRINT.md` | adapted: authority, links, provenance |
| `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | adapted: links, provenance, peer status |
| `docs/design/ODIN-ACCEPTANCE-SCENARIOS.md` | `docs/design/ODIN-ACCEPTANCE-SCENARIOS.md` | adapted: authority, check ownership; identifiers unchanged |
| `docs/design/ODIN-REPOSITORY-EXTRACTION.md` | none (historical handoff instructions) | reference |
| `docs/design/HARNESS-LANDSCAPE-2026-10.md` | `docs/research/HARNESS-LANDSCAPE-2026-10.md` | adapted: dated-evidence banner, one link |
| `docs/design/harness-research-2026-10/README.md` | `docs/research/harness-research-2026-10/README.md` | adapted: dated-evidence banner and link note |
| `docs/design/harness-research-2026-10/*.md` (the 17 other notes) | `docs/research/harness-research-2026-10/` | exact copies |
| `docs/features/odin-proactive-updates.md`, `spec-development.md`, `voice-telegram.md` | triaged in `docs/provenance/LEGACY-REQUIREMENTS.md` | reference |
| `journal/JOURNAL-FORMAT.md` | cited by I/O contract §5; triaged | reference |
| `mqtt/TOPIC-SCHEMA.md` | cited by I/O contract §6; triaged | reference |
| `odin/CLAUDE.md`, `odin/mimir/CLAUDE.md` | runtime persona inputs; triaged; not developer instructions | reference |

Not imported: Saga's specification, architecture and deployment
documents, the Eir backlog, worker and authentication scripts,
containers, credentials, journals, databases and runtime state.

### Unresolved references inside the snapshot

A complete per-link inventory is in
[`HISTORICAL-LINKS.md`](../../provenance/HISTORICAL-LINKS.md); this is a
summary. These links were valid in Saga's tree and do not resolve here. They
stay as captured; the targets are Saga-owned or peer-owned and are not
required to read Odin's live documents.

| Snapshot file | Unresolved targets |
|---|---|
| `README.md` | `docs/README.md`, `docs/saga-spec.md`, `docs/architecture/` (including `SETUP.md`, `HOMELAB-INTEGRATION.md`), `docs/agents/`, `docs/history/`, `LICENSE`, the banner image |
| `docs/ROADMAP.md` | `../CHANGELOG.md`, `agents/EIR-BACKLOG.md` |
| `docs/design/ODIN-ECOSYSTEM-INTEGRATION.md` | sibling checkouts `../../../{heimdall,skald,braid,wayland-computer-use,dotprivate}/…` (16 links) |
| `docs/design/harness-research-2026-10/repo_braid.md` | absolute paths under `/home/david/Projects/saga/` (Saga files, some under a former `docs/drafts/` location) |
| `docs/design/harness-research-2026-10/repo_heimdall.md` | Saga code and docs: `scripts/systemd/heimdall.*`, `odin/scripts/heimdall.py`, `odin/scripts/ratatoskr.py`, `docs/saga-spec.md`, `docs/architecture/ARCHITECTURE.md` |
| `docs/design/harness-research-2026-10/repo_muninn.md` | `docs/history/PHASE-3-RETROSPECTIVE.md`, `docs/history/INSIGHTS-2026-04-15.md`, `bragi/CLAUDE.md` |
| `docs/design/harness-research-2026-10/repo_skald.md` | `bragi/CLAUDE.md`, `containers/bragi/*`, `scripts/auth/launch-bragi-template.sh`, `docs/architecture/*`, `docs/history/PHASE-3-RETROSPECTIVE.md` |
| `odin/CLAUDE.md` | `../../muninn/wiki/index.md` (an example path inside persona text) |

Unlinked path mentions in the personas (for example
`docs/history/PHASE-3-RETROSPECTIVE.md`, `odin/specs/templates/…`,
`bragi/CLAUDE.md`, `/workspace/…` container paths) also refer to Saga's
tree or its deployment and were not captured.

### Attribution and licensing

The snapshot carries its attributions unchanged, including Victor
Taelin's UniiChat design (gist with no license shown) and the research
notes' citations of third-party projects. The operator's standalone
repositories show no license. Nothing here grants a license; the
question is open (`DECISIONS.md` §3, item 5).

## Unresolved historical references

The complete generated [reference inventory](../../provenance/HISTORICAL-LINKS.md) records unresolved links in the frozen snapshot and dated research. Frozen source links retain their original bytes; live requirements are checked separately.
