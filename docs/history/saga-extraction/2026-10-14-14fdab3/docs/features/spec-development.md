# Feature: Spec development as part of Saga's loop

> **Status:** Scoped, not implemented.
> **Effort estimate:** Low-effort version is a Phase 3 template tweak
> (~1 hour). Mid-effort version (development log as wiki citizen) is
> 1-2 days post-Phase-3. High-effort version (Odin spec-dev mode) is
> 3-5 days post-Phase-3.
> **Priority:** The low-effort version should land DURING Phase 3 since
> it changes the spec-ingestion contract; higher-effort versions
> are Phase 4+ candidates.

## The gap

Saga currently treats the spec as the **end of a thinking process**:
operator does the brainstorming somewhere external (a Claude
conversation, a notebook, a whiteboard, dev Claude on the VM), arrives
at a refined spec, and hands the spec to Odin as a finished artifact.
Odin compiles the spec into the project wiki (per the post-Phase-2
spec-as-wiki restructure) and decomposes from there.

What gets lost in this handoff:

- **Rejected alternatives.** The operator considered Postgres vs
  SQLite vs DuckDB and picked SQLite for single-user homelab reasons.
  The spec only records the choice, not the reasoning.
- **Constraint discovery.** During brainstorming, the operator
  realized that "real-time" was actually "within 5 seconds" because
  of a downstream consumer — but that nuance never made it into the
  written spec.
- **Tradeoff weights.** Why was simplicity prioritized over
  performance here? The spec implies it; the dev log states it.

The cost of losing this context downstream:

- **Dvergar make uninformed implementation choices.** A dvergr might
  switch from SQLite to Postgres mid-iteration "for scalability"
  without realizing the original choice was deliberate.
- **Mimir's reviews miss alignment.** Mimir audits decompositions
  against the spec, but can't catch "this decomposition contradicts a
  rationale that wasn't written down."
- **Cross-project knowledge transfer is shallower.** Odin's master
  journal records what worked, but learning compounds faster when the
  WHY behind each decision is recoverable.

## Architecture options (three tiers, build incrementally)

### Tier 1: Extend the spec template (Phase 3, ~1 hour)

The cheapest, highest-leverage version. Add a required section to
`odin/specs/templates/spec-template.md` (or wherever the canonical
template lives) called something like:

```markdown
## Design decisions and rejected alternatives

For each significant choice in this spec, capture:

- **What was chosen** — the decision as it appears elsewhere in the spec
- **What was considered and rejected** — the alternatives that were on the table
- **Why this choice won** — the constraint, preference, or tradeoff that drove it
- **What would change the decision** — what new information would make us reconsider

Example:

### Decision: SQLite for state storage

- **Chosen:** SQLite, single file per dvergr workspace
- **Considered:** Postgres in a sidecar container; DuckDB for analytical workloads
- **Why:** Single-user homelab, no concurrent writers, want zero ops overhead
- **Would change if:** We add multi-tenant access, or analytical queries grow past
  100k rows
```

Odin's spec-ingestion workflow (per `odin/CLAUDE.md` § "Spec
Ingestion") then naturally pulls these into wiki decision records and
makes them available to Mimir during decomposition review.

**Effort:** template edit + a paragraph in `odin/CLAUDE.md` directing
Odin to call out "no decision rationale provided" if the section is
empty. Done in an hour.

**Limit:** relies on operator discipline. If the operator doesn't fill
in the section, no rationale is captured.

### Tier 2: Development log as a wiki citizen (post-Phase-3, 1-2 days)

Operator brainstorms wherever they want (dev Claude, claude.ai web,
phone Telegram, paper notes transcribed) and submits the brainstorm
TRANSCRIPT alongside the spec. Saga's wiki layout grows a new layer:

```
odin/projects/<project>/
├── raw/
│   ├── spec.md             ← the refined spec (current behavior)
│   └── dev-log.md          ← NEW: brainstorm transcript, decisions in flight
├── wiki/
│   ├── index.md
│   ├── components.md
│   ├── constraints.md
│   ├── decisions/          ← compiled from raw/dev-log.md by Odin
│   │   └── <date>-<slug>.md
│   └── rationale.md        ← NEW: distilled "why" extracted from dev-log
```

Odin's spec-ingestion workflow gains a step: read both `raw/spec.md`
AND `raw/dev-log.md`, compile decision records into
`wiki/decisions/`, surface tradeoffs in `wiki/rationale.md`. Mimir's
decomposition review now has access to the rationale layer and can
catch alignment issues.

**Effort:** ~1-2 days. Requires:

- Update spec-as-wiki schema in
  `odin/specs/templates/project-template/CLAUDE.md`
- Update Odin's spec-ingestion workflow in `odin/CLAUDE.md`
- Update Mimir's persona to reference the rationale layer when
  reviewing decompositions
- New entity-page template for `rationale.md`

**Limit:** still relies on the operator to produce a dev-log
transcript. Tools like Claude's "Export conversation" make this easy
but it's a manual step.

### Tier 3: Odin spec-development mode (Phase 4+, 3-5 days)

Brainstorming happens INSIDE Saga, with Odin as the dialogue partner.
Operator DMs Odin "I want to start a new project. Idea is X" and Odin
enters a spec-dev mode where it:

- Asks clarifying questions
- Surfaces ambiguity
- Proposes considerations the operator might not have thought of
- Cross-references Odin's master-journal for relevant prior projects

Each dialog turn appends to `raw/dev-log.md` automatically. When the
operator says "ok, commit this spec," Odin compiles the dev log into
`raw/spec.md` + structured wiki + decision records, then drops back
into normal spec-ingestion mode.

**Effort:** ~3-5 days. Requires:

- New "spec-dev" mode flag in Odin's persona/CLAUDE.md
- A state machine for the spec-dev conversation (questions to ask,
  when to compile, how to detect "ok done")
- Logic to detect spec-dev vs normal-ops messages on Telegram
- Token budget consideration — long brainstorming conversations chew
  through Opus tokens; might want to use Sonnet for spec-dev mode
- Telegram UX considerations — phone keyboards aren't great for long
  brainstorms. Voice (per voice-telegram) actually pairs well
  with this: speak the brainstorm, get text refinement back

**Benefit:** the brainstorm IS the wiki. Nothing gets lost in
translation. Cross-project context flows in naturally because Odin
already knows the master journal.

**Limit:** more complex; introduces a mode-switching surface that can
confuse the operator or Odin if not designed carefully.

## Recommended sequencing

1. **Land Tier 1 during Phase 3** — it's a template change, costs an
   hour, and captures the most important wins (rationale capture and
   downstream awareness) for free. Do it before Phase 3 ships so the
   first real spec-ingestion run uses the new template.
2. **Land Tier 2 in early Phase 4** — once Phase 3 has been exercised
   on a real project, the gap between "spec only" and "spec + dev log"
   will be visible in dvergr behavior. Add the dev-log layer to the
   wiki schema.
3. **Defer Tier 3 indefinitely** — only build if Tier 1 + Tier 2
   leave a clear gap. The "Odin holds your hand through brainstorming"
   experience is appealing but might add complexity for marginal
   benefit. Validate the simpler tiers first.

## Why this isn't urgent (but Tier 1 should still happen now)

- Tier 1 is *literally a template change* — almost free
- Tier 1 sets the expectation that rationale capture is part of spec
  authoring, which compounds in value over time
- Tier 2 + Tier 3 can wait until Phase 3 ships and we can measure the
  actual gap on real projects

The risk of NOT doing Tier 1 in Phase 3: the first projects to ship
through Saga set the cultural norm. If they don't capture rationale,
neither will subsequent ones, and the "decisions without context"
problem compounds.

## Cross-references

- Spec-as-wiki schema: `odin/specs/templates/project-template/CLAUDE.md`
- Odin's spec ingestion workflow: `odin/CLAUDE.md` § "Spec Ingestion"
- Mimir's decomposition review type:
  `odin/mimir/CLAUDE.md` § "Decomposition Review"
- Cross-project knowledge transfer pattern: `odin/CLAUDE.md` §
  "Cross-Project Knowledge Transfer" — the rationale layer feeds
  directly into this
- Bragi's vault structure (where decisions get chronicled long-term):
  `bragi/CLAUDE.md`
- Voice integration that pairs well with spec-dev mode (Tier 3):
  `docs/features/voice-telegram.md`

## Action items for when picked up

### For Tier 1 (during Phase 3)

1. Update `odin/specs/templates/spec-template.md` (or the
   project-template equivalent) with the "Design decisions and
   rejected alternatives" section + the example.
2. Update `odin/CLAUDE.md` § "Spec Ingestion" to:
   - Direct Odin to read the design-decisions section first
   - Compile each decision into `wiki/decisions/<date>-<slug>.md`
   - If the section is empty/missing, flag it via Telegram before
     proceeding (don't silently process a spec without rationale)
3. Update `odin/mimir/CLAUDE.md` § "Decomposition Review" to read
   `wiki/decisions/` files and check the proposed decomposition
   against the documented rationale.
4. Update the Phase 3 end-to-end test plan to verify the
   design-decisions flow: submit a spec with the new section, watch
   it land in the wiki, watch Mimir reference it.

### For Tier 2 (post-Phase-3)

5. Extend wiki schema with `raw/dev-log.md` slot and
   `wiki/rationale.md` entity page.
6. Update Odin's spec-ingestion workflow to compile the dev log
   alongside the spec.
7. Document the "export your brainstorm conversation" workflow for
   common Claude interfaces (web, CLI, dev) in
   `docs/architecture/SETUP.md` or a new dedicated guide.

### For Tier 3 (Phase 4+, validate need first)

8. Design the spec-dev mode state machine and entry/exit conditions
9. Decide on the model (Opus for the strategic asks, Sonnet for the
   conversational refinement?) and document the token-budget
   tradeoff
10. Build it; consider voice pairing per
    `voice-telegram.md`

## One worth-thinking-about caveat

This feature implies a new failure mode: **rationale provided in the
dev log can contradict the final spec.** If the operator brainstormed
Postgres, then the spec says SQLite, which one wins? Default answer:
the spec wins — that's why it's the refined artifact. But Odin should
flag the contradiction during ingestion so the operator can confirm
the spec is right and the dev log was superseded. Mimir is the natural
catcher for this kind of inconsistency; review-flow update needed.
