"""The haptic channel (spec 2.1, 2.6): felt, not read.

A pattern is one line in the estate's alert inbox (config.append_alert),
the notification path the cockpit's /api/inbox and the phone already
tail. Nothing here touches the chat: a haptic pattern has no ChatMessage
type, so chat.send cannot carry it.
"""
from __future__ import annotations

from typing import Any, Callable

from sovereign import config
from sovereign.presence import config_keys
from sovereign.presence.fsm import (
    BoundaryApproaching,
    Catastrophe,
    HaltRequired,
    Pattern,
    StateCommit,
    SystemEvent,
)

InboxAppend = Callable[[dict[str, Any]], None]


def pattern_for(event: SystemEvent) -> Pattern:
    """spec 2.1: single tap = state commit OK; double tap = budget
    threshold approaching; sustained buzz = halt required."""
    if isinstance(event, StateCommit):
        return Pattern.TAP
    if isinstance(event, BoundaryApproaching):
        return Pattern.DOUBLE_TAP
    if isinstance(event, (HaltRequired, Catastrophe)):
        return Pattern.BUZZ
    raise TypeError(f"not a system event: {event!r}")


def send(event: SystemEvent, inbox_append: InboxAppend = config.append_alert) -> Pattern:
    pattern = pattern_for(event)
    inbox_append(
        {
            "kind": str(config_keys.resolve("presence.haptic_kind")),
            "pattern": pattern.value,
            "event": type(event).__name__,
            "session_id": getattr(event, "session_id", None),
        }
    )
    return pattern
