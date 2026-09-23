"""The presence FSM: Ghost, Haptic, Spatial, Converse (R1-R4, spec 2.1).

The rule this module exists for: the system may never push the founder
from Ghost into Converse. It is held in the types, not in a check:

* `SystemEvent` is everything the estate can do on its own (a state
  commit, a boundary warning, a halt, a catastrophe).
* `on_system_event` returns `SystemReachable`, and `Converse` is not a
  member of that union. A version of this function that returned Converse
  would not type-check under pyright --strict.
* `Converse` cannot be built without a `FounderAct`, and a `FounderAct` is
  only ever constructed by the two entry points the spec names: the
  founder sending a message, and the dead man's switch recovery prompt.

Pure data, no disk, no clock. The side effects (write the state file for
the menu bar dot, emit a haptic pattern) live in router.py and haptic.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Pattern(str, Enum):
    """The three haptic patterns of spec 2.1."""

    TAP = "tap"  # single tap: state commit OK
    DOUBLE_TAP = "double_tap"  # budget threshold approaching
    BUZZ = "buzz"  # sustained: halt required, glance at the Mac


# --- states ---------------------------------------------------------------


@dataclass(frozen=True)
class Ghost:
    """Default. Nothing on screen changes; the dot is grey."""


@dataclass(frozen=True)
class Haptic:
    """Felt, not read. A sub-threshold signal: the founder is still in Ghost
    for every other purpose (spec 2.1: "Haptic may fire without leaving
    Ghost")."""

    pattern: Pattern


SpatialCause = Literal["founder_click", "catastrophe"]


@dataclass(frozen=True)
class Spatial:
    """The estate graph is on screen. Entered by the founder clicking the
    menu bar, or by a catastrophe."""

    cause: SpatialCause


FounderActKind = Literal["message", "dead_mans_switch_recovery"]


@dataclass(frozen=True)
class FounderAct:
    """Evidence that the founder started this. The only way to build a
    Converse value."""

    kind: FounderActKind
    by: str


@dataclass(frozen=True)
class Converse:
    """Interactive. Fires only when the founder initiates."""

    initiated_by: FounderAct


@dataclass(frozen=True)
class FounderClick:
    """The founder clicked the menu bar app."""

    by: str


SystemReachable = Ghost | Haptic | Spatial
Presence = SystemReachable | Converse


# --- events the system raises on its own -----------------------------------


@dataclass(frozen=True)
class StateCommit:
    session_id: str


@dataclass(frozen=True)
class BoundaryApproaching:
    session_id: str


@dataclass(frozen=True)
class HaltRequired:
    session_id: str


CatastropheKind = Literal["integrity_failure", "lockdown", "dead_mans_switch"]


@dataclass(frozen=True)
class Catastrophe:
    kind: CatastropheKind
    session_id: str | None = None


SystemEvent = StateCommit | BoundaryApproaching | HaltRequired | Catastrophe


# --- transitions ----------------------------------------------------------


def on_system_event(event: SystemEvent) -> SystemReachable:
    """The surface a system event may raise. The return type has no
    Converse in it; that is the invariant."""
    if isinstance(event, StateCommit):
        return Haptic(Pattern.TAP)
    if isinstance(event, BoundaryApproaching):
        return Haptic(Pattern.DOUBLE_TAP)
    if isinstance(event, HaltRequired):
        return Haptic(Pattern.BUZZ)
    return Spatial(cause="catastrophe")


def apply(state: Presence, event: SystemEvent) -> Presence:
    """A system event against the current state. A founder already in
    Converse is left there; a system event never moves anyone into it."""
    if isinstance(state, Converse):
        return state
    return on_system_event(event)


def on_founder(state: Presence, act: FounderAct | FounderClick) -> Presence:
    """The founder acts. These are the only transitions into Converse."""
    if isinstance(act, FounderClick):
        return Spatial(cause="founder_click")
    return Converse(initiated_by=act)


def settle(state: Presence) -> Presence:
    """A haptic signal is over once it has been felt: the state returns to
    Ghost. Spatial stays until the founder closes it; Converse stays until
    the founder leaves."""
    if isinstance(state, Haptic):
        return Ghost()
    return state


def leave(state: Presence) -> Ghost:
    """The founder closes Spatial or ends Converse."""
    return Ghost()


def name(state: Presence) -> str:
    return type(state).__name__.lower()


def is_ghost_equivalent(state: Presence) -> bool:
    """True when no pixel should change: Ghost, or a Haptic sub-signal."""
    return isinstance(state, (Ghost, Haptic))
