"""Where each event goes (spec 2.5): everything to the inbox and the card,
a catastrophe to the chat once, and nothing that opens Converse.

`on_state_change` is what the engine's notify path calls for a routine
state change. It writes the one-line receipt to the alert inbox, edits
the Otto card, moves the presence FSM and writes the state file for the
menu bar dot. It has no chat parameter: there is no way to send a chat
message from it.

`integrity_failure` is the catastrophe path: one CatastropheAlert to the
chat, the session halted, Spatial raised with cause "catastrophe".
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from sovereign import config
from sovereign.presence import chat, config_keys, haptic, state as state_mod
from sovereign.presence.fsm import Catastrophe, Ghost, Presence, StateCommit, apply, settle
from sovereign.presence.receipt import from_record

InboxAppend = Callable[[dict[str, Any]], None]
CardEdit = Callable[[dict[str, Any]], Any]
Halt = Callable[[str], Any]


def _default_card_edit(row: dict[str, Any]) -> Any:
    from sovereign.otto import card

    return card.on_change(row)


def _default_halt(session_id: str) -> Any:
    from sovereign.engine import client as engine_client

    return asyncio.run(engine_client.signal(session_id, "stop", "presence", "integrity failure"))


def on_state_change(
    row: dict[str, Any],
    *,
    current: Presence | None = None,
    inbox_append: InboxAppend = config.append_alert,
    card_edit: CardEdit = _default_card_edit,
) -> Presence:
    """A routine state change. Returns the settled presence state."""
    receipt = from_record(row)
    inbox_append(
        {
            "kind": str(config_keys.resolve("presence.receipt_kind")),
            "session_id": row.get("session_id"),
            "line": receipt.text,
            "hash": receipt.hash,
            "budget_delta": receipt.budget_delta,
            "state": receipt.state,
        }
    )
    card_edit(row)
    event = StateCommit(session_id=str(row.get("session_id") or ""))
    if bool(config_keys.resolve("presence.haptic_enabled")):
        haptic.send(event, inbox_append)
    after = apply(current if current is not None else Ghost(), event)
    settled = settle(after)
    state_mod.write(settled)
    return settled


def integrity_failure(
    verdict: dict[str, Any],
    session_id: str | None,
    *,
    sink: chat.ChatSink,
    halt: Halt = _default_halt,
    detected_hash: str | None = None,
    current: Presence | None = None,
) -> Presence:
    """The receipt chain no longer matches. One message, then halt."""
    if verdict.get("ok"):
        raise ValueError("integrity_failure called with a verdict that passed")
    found = detected_hash or str(verdict.get("hash") or verdict.get("first_broken_counter") or verdict.get("reason") or "")
    alert = chat.CatastropheAlert(
        cause="integrity_failure",
        hash=found,
        remediation=str(config_keys.resolve("presence.remediation_command")),
        session_id=session_id,
    )
    chat.send(sink, alert)
    if session_id:
        halt(session_id)
    after = apply(current if current is not None else Ghost(), Catastrophe(kind="integrity_failure", session_id=session_id))
    state_mod.write(after)
    return after
