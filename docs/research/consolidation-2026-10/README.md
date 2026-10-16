# Consolidation investigations — 2026-10-16

> **Dated evidence (Odin repository).** Four investigation reports
> written on 2026-10-16 by research agents working for the operator, in
> support of [`../../design/CONSOLIDATION-PLAN.md`](../../design/CONSOLIDATION-PLAN.md).
> They are evidence, not policy. Every repository they describe was read
> from the operator's local checkouts without building, running or
> modifying anything. Claims carry `path:line` evidence; the monorepo
> mechanics report marks the steps it rehearsed on scratch clones.
> Nothing here records a decision; the decision record wins wherever
> they differ. Links inside the reports to sibling repositories and to
> external pages were not re-verified after writing.

| File | Covers |
|---|---|
| [inventory-go-repos.md](inventory-go-repos.md) | Standalone heimdall, skald and braid: module layout, LOC per package and layer, SQLite schemas, coupling between heimdall's sensor, task-core, workspace, UI and agent layers, skald's capture library and archive, braid's embeddable API, shared dependencies, and a package-by-package destination table |
| [inventory-saga-wcu-dotprivate.md](inventory-saga-wcu-dotprivate.md) | Saga's code (launcher, ratatoskr, Bragi, Eir, worker images, spec_dev), the launcher's confinement weaknesses, a gap table from the pinned Saga contract to existing code, wayland-computer-use's servers, guards, input path and privilege model, dotprivate's sync model and proposed contract, and destination tables |
| [decision-record-impact.md](decision-record-impact.md) | Every inherited decision and identifier the consolidation touches, which clauses Odin can amend and which are Saga-owned, drafts for ODIN-ADR-006 to 019 in dependency order, the document-change plan, naming constraints, and the recommended governance sequence |
| [monorepo-mechanics.md](monorepo-mechanics.md) | Importing repositories with history (`git filter-repo`), one Go module, a uv workspace, per-deployable versioning with a release manifest, GitHub Actions shape, Arch packaging, licensing, repository hygiene, recommended layout, anti-patterns, and sources |

Checkouts read, with HEAD at the time: odin `cb55ecc` (working tree
dirty), saga `a84f9ac`, heimdall `3ca80b5`, skald `22114dd`, braid
`7e24af3`, wayland-computer-use `e61f8ed` (12 commits ahead of origin),
dotprivate `51d0fce`.
