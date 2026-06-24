"""Shared application state.

A single source of truth for runtime flags. The most important is ``dry_run``:
it defaults to ``True`` (safety first) and is passed explicitly to every core
function, so behaviour is never ambiguous or hidden behind a hidden global.
"""
from __future__ import annotations

from dataclasses import dataclass

# Safety-first default. The UI exposes a toggle that flips this value; the
# executor receives it on every call and refuses to touch the system when True.
DRY_RUN_DEFAULT = True


@dataclass
class AppState:
    """Mutable, process-wide UI/runtime state."""

    dry_run: bool = DRY_RUN_DEFAULT
    is_admin: bool = False
    busy: bool = False  # True while a task is executing (prevents overlap)
