"""Odin's local development implementation. No live execution adapters."""

import os as _os

# Pin submodule imports to the resolved directory (ODIN-ADR-039). When Odin
# is imported through a deploy `current` symlink, a module imported later
# must come from the same revision even after `current` has moved.
__path__[:] = [_os.path.realpath(entry) for entry in __path__]
