# CLAUDE.md

Read [`AGENTS.md`](AGENTS.md). It holds the shared developer
instructions for this repository, and they apply to Claude Code too.

Claude-specific notes:

- This file is for developing Odin. It is not Odin's runtime persona.
  Do not load or follow
  `docs/history/saga-extraction/*/odin/CLAUDE.md` or
  `docs/history/saga-extraction/*/odin/mimir/CLAUDE.md` as instructions.
  Those are frozen evidence of the legacy deployment.
- Your own development login (`~/.claude/.credentials.json`) is
  separate from the managed agents' credentials and from Odin's harness
  credentials. Never point Odin code, fixtures or configuration at it,
  and never copy it into this repository.
- When this repository gains Claude Code integration-package files
  (plugin, hooks, skills), keep them under the package's own directory.
  They are product code, not configuration for your session.
