"""The presence gate intake honours (R4, spec 2.3 step 4).

sovereign/presence is workstream W3's territory and does not exist on the
integration branch this lane started from, so the smallest interface intake
needs is declared here as a Protocol. When W3 lands a real presence state
type, `PresenceGate` should be replaced by an import of it; nothing here
depends on more than reading the current state name.

The rule intake enforces: a photo arriving in a Converse thread is handled
silently, one receipt line goes back to the thread that asked, and the
presence state is never moved to Converse by intake itself. Intake reads the
state before and after and refuses to report success if it changed.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PresenceGate(Protocol):
    """Whatever object W3 ships, intake only needs to read the state name."""

    def current(self) -> str:
        """The presence state name, e.g. "ghost", "converse", "command"."""
        ...


class GhostPresence:
    """A presence that is always Ghost. The default when no gate is wired,
    and what the CLI entry point uses -- a laptop shell is not a thread."""

    def __init__(self, state: str = "ghost") -> None:
        self._state = state

    def current(self) -> str:
        return self._state
