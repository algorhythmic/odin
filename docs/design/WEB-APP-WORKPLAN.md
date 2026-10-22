# Web app work plan

Status: plan, 2026-10-21. It turns the
[web app handoff](WEB-APP-HANDOFF.md) and
[ODIN-ADR-037](../DECISIONS.md#odin-adr-037--web-app-as-the-primary-human-view-with-an-agent-tree)
into dependency-ordered packages. The packages sit inside the roadmap's
increments ([human-view track](../ROADMAP.md#human-view-track-odin-adr-037));
they are not new increments. Library choices are in
[WEB-APP-LIBRARIES.md](WEB-APP-LIBRARIES.md).

Result labels are distinct and never upgraded by implication: **synthetic
prototype**, **fake-backend integration** (the Saga execution backend is the
fake one; Odin's service is real), **service integration** and **validated
desktop behaviour**.

"Checks" below are the handoff's acceptance checks 1–10. The proposed
scenarios are AC-51 (ancestry, check 1), AC-52 (navigation, check 2), AC-53
(updates and visible states, checks 3–4), AC-54 (reconnect, check 3), AC-55
(commands and approvals, checks 5–6), AC-56 (accessibility, untrusted
content, access and large trees, checks 7–9) and AC-57 (desktop, check 10).

## Owners

- **webapp workstream:** the ADR-036 workstream session for this work. It
  commits on its own branch and returns merge-ready heads with receipts.
- **integration owner:** the project's ADR-036 integration owner, who
  merges workstream heads and owns shared files (`schemas/`, `runtime/`,
  `python/odin/` service code) unless the executive assigns a package.
- **executive / operator:** decisions the workstream cannot take
  (authentication model, installing a launcher on the operator's desktop).

## Packages

| ID | Package | Owner | Prerequisites | Acceptance (checks) | Enforcement | Target pass |
|---|---|---|---|---|---|---|
| W1 | Documentation alignment: ADR-037, decision map, I/O contract §10/§13, blueprint §5/§7, roadmap track, AC-51–AC-57, AGENTS.md and indexes | webapp workstream; merge by integration owner | Handoff copied verbatim | All checks are traced to a package and an enforcement method (this table) | `scripts/validate_docs.py` through the receipt path; non-author Haiku semantic review for competing claims about the primary surface, human-view timing and terminal requirements | 1 |
| W2a | Synthetic prototype slice: overview with attention items, project workspace with tree, detail panel and list toggle, hash routes for project and session, untrusted transcript rendering, unknown cost | webapp workstream | W1 library choice | 1; 2 (routing and reload, not access); 4 (static states only); 7; 8 (markup rendering only) | Playwright: `check01-relationships`, `check02-deeplink`, `check07-keyboard-list`, `check08-untrusted-transcript`; screenshots in private evidence | 1 |
| W2b | Prototype depth: planning/activity area content, history view (retired sessions, attempts versus resumptions), stale and `host_offline` presentation, fit-branch and follow-parent assertions, reading-position preservation under simulated synthetic updates | webapp workstream | W2a | 1; 3 (selection and reading position under synthetic updates only); 4; 7 | Playwright scenarios per behaviour; synthetic update driver in the fixture module | 2 |
| W2c | Large synthetic tree: record the dataset (proposed: 2,000 sessions, 40 roots, depth up to 8, 20 transcript pages per session) and target (proposed: first render of the collapsed project under 1 s, expand or select under 150 ms, headless Chromium on the workstation) before optimizing | webapp workstream | W2a | 9 | Playwright timing scenario with the recorded dataset; results reported as synthetic prototype timings | 2 |
| W3 | Record and projection foundation: stable identities for sessions, assignments, commitments, runs; `parent_session_id` and provenance; typed relationships; lifecycle identity (resumption versus attempt); browser projection and update-event schemas with cursor and revision; validated synthetic fixtures shared by Go and Python | integration owner (shared `schemas/`, `runtime/`); webapp workstream drafts the projection schema and fixtures | W1 accepted; I0 conventions (ODIN-ADR-008, 021); X-7 does not block these schemas | 1; 3 (schema level: idempotent event identity, cursor expiry) | Go and Python validators over shared fixtures (`make check`); prototype switched to load the same fixtures | 3 |
| W4 | Service read integration: snapshot and resumable update stream from the local service against the fake Saga backend; history; transcript pages and gaps; reconnect and expired-cursor snapshot; freshness; access checks in the service | integration owner for service endpoints; webapp workstream for the client | W3; I1 service foundation; transport chosen and recorded; W5a's authentication for any non-loopback exposure | 2 (including missing and inaccessible records); 3; 4; 8 (access refusal) | Python service tests plus Playwright against a locally started service with the fake backend, labelled fake-backend integration; never against the live pilot state | 4 |
| W5a | Web surface security definition: authentication, authorization, CSRF or equivalent protection of state-changing requests, request validation, origin and serving model | executive / operator decision, drafted by the integration owner | W1 | 8 | Recorded decision; tests in W4/W5 | before W5 |
| W5 | Operator command integration: conversation input, supported lifecycle and decision actions, approvals with request id, revision and proposal digest, stop with acknowledged and uncertain outcomes, idempotency keys, capability-driven controls | integration owner (command path); webapp workstream (UI) | W4; W5a; recorded command path; Saga-touching commands keep the I3 live gates | 5; 6; 8 | Service tests for each command record and idempotent repeat; Playwright for acknowledged, rejected, uncertain and unsupported presentation; fake-backend label until I3 | 5 |
| W6 | Desktop delivery: Chromium app-mode launcher and desktop entry with its own window class, start script, documented browser and development use; restart and reconnect | webapp workstream delivers scripts and instructions; installation only on explicit executive instruction | W4 (a service to reconnect to); Omarchy instructions | 10 | Script checks (generated desktop entry content, `--app` URL, window class) automated; launch, window identity, close/reopen and deep links need **manual desktop evidence** (no interactive desktop is available to the workstream) | 6 |

W2 can run in parallel with W3 once the projection contract is agreed; W4
and later depend on the service. Nothing waits for the I4 heimdall import.

## Check traceability

Status is as of pass 3 (2026-10-22). Every result so far is a
**synthetic prototype** result; none is fake-backend, service or
desktop evidence.

| Check | Packages | First enforcement | Status after pass 3 |
|---|---|---|---|
| 1 Relationships | W2a, W3, W4 | Playwright `check01-relationships`, `check01-malformed` (synthetic) | Synthetic: ancestry versus typed overlays, imported and outside-parent roots, cycles and self-parents as labelled roots, follow-parent, fit branch. W3: draft JSON Schemas under `schemas/web-projection-*` with a Python fixture test ([WEB-APP-PROJECTION.md](WEB-APP-PROJECTION.md)); not adopted |
| 2 Selection, deep links, missing records | W2a, W4 | Playwright `check02-deeplink` (synthetic routing); access refusal in W4 | Synthetic routing, reload and not-found (including a missing previous attempt); access refusal not started |
| 3 Updates and reconnect | W2b, W3, W4 | Synthetic update driver (W2b); fake-backend stream tests (W4) | Synthetic: `check03-updates` (idempotent re-delivery, revision gap, rejected malformed events, selection, collapsed state, list and transcript reading position); Node unit tests of the event rules (`tests-unit/events.test.js`). No stream, reconnect or cursor expiry yet |
| 4 Visible states | W2a, W2b, W4 | Playwright state labels (synthetic); fake-backend states (W4) | Synthetic: `check04-states-history` (stale and host-offline last-observed times, history with attempts versus resumptions) |
| 5 Commands and idempotency | W5 | Service and Playwright tests (W5) | Not started; controls shown disabled |
| 6 Approval binding and stop | W5 | Service and Playwright tests (W5) | Not started |
| 7 Keyboard, text states, narrow layouts | W2a, W2b | Playwright `check07-keyboard-list` | Synthetic; keyboard list also covered on malformed records; pointer expand in the list; card footers unclipped at 1280 and 800 px; transcript pager keeps keyboard focus |
| 8 Access, unsafe markup, credentials | W2a, W5a, W4, W5 | Playwright `check08-untrusted-transcript`; access tests in W4 | Synthetic markup rendering and stored-preference checks; access and credentials not started |
| 9 Large tree | W2c | Playwright timing scenario with recorded dataset | Synthetic timings recorded by `tests-perf/check09-large-timing` on the seeded 2,000-session set: first render, expand, select, and depth-8 path expansion in tree and list (pass 3 evidence, `large-timings.json` and `large-deep-timings.json`, kept outside Git). All within the proposed targets, so windowing is deferred; targets still proposals |
| 10 Desktop | W6 | Manual desktop evidence plus script checks | Not started; outside the workstream's current scope |

## Redesign (2026-10-22)

The operator's redesign direction (onboarding with provider sign-in,
harness, model and per-role configuration; the agent tree as the baseline
view, rooted at the single executive with projects as branches; Queue,
Lanes, Graph, Decisions and Board deferred) and its slices R1–R3b are in
[WEB-APP-REDESIGN.md](WEB-APP-REDESIGN.md). Every slice is a synthetic
prototype result under the labels above.

## Not in scope

Saga application redesign, cross-repository consolidation, manual graph
editing, an embedded terminal in v0, and any native wrapper.
