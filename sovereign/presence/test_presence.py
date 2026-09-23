"""Property tests for sovereign.presence (rung 2 of the testing ladder).

The presence state space is finite, so each property is checked over the
whole product of states and events rather than a sample: that is the
same guarantee a property test gives, with no dependency on hypothesis.

Run:  python -m pytest sovereign/presence/test_presence.py -q
"""
from __future__ import annotations

import itertools
import string

import pytest

from sovereign.presence import chat, fsm, receipt, state as state_mod

ACT = fsm.FounderAct(kind="message", by="founder")
STATES: list[fsm.Presence] = [
    fsm.Ghost(), *(fsm.Haptic(p) for p in fsm.Pattern),
    fsm.Spatial(cause="founder_click"), fsm.Spatial(cause="catastrophe"),
    fsm.Converse(initiated_by=ACT), fsm.Converse(initiated_by=fsm.FounderAct(kind="dead_mans_switch_recovery", by="kernel")),
]
EVENTS: list[fsm.SystemEvent] = [
    fsm.StateCommit("s"), fsm.BoundaryApproaching("s"), fsm.HaltRequired("s"),
    *(fsm.Catastrophe(kind=k) for k in ("integrity_failure", "lockdown", "dead_mans_switch")),
]


def test_property_system_events_never_enter_converse() -> None:
    """R1-R4: for every (state, event), the result is Converse only if the
    state already was. Founder acts are the only way in."""
    for state, event in itertools.product(STATES, EVENTS):
        after = fsm.apply(state, event)
        assert isinstance(after, fsm.Converse) == isinstance(state, fsm.Converse)
        assert isinstance(fsm.on_system_event(event), (fsm.Ghost, fsm.Haptic, fsm.Spatial))
        assert not isinstance(fsm.settle(after), fsm.Converse) or isinstance(state, fsm.Converse)
    for state in STATES:
        assert isinstance(fsm.on_founder(state, ACT), fsm.Converse)
        assert fsm.on_founder(state, fsm.FounderClick(by="founder")) == fsm.Spatial(cause="founder_click")
        assert fsm.leave(state) == fsm.Ghost()


def test_property_ghost_and_haptic_share_one_dot_colour() -> None:
    """spec 2.1: in Ghost no pixel changes, and Haptic is felt not seen."""
    ghost = state_mod.dot_colour(fsm.Ghost())
    for state in STATES:
        colour = state_mod.dot_colour(state)
        assert (colour == ghost) == fsm.is_ghost_equivalent(state), state
        assert isinstance(state_mod.as_dict(state)["state"], str)


_ADVERSARIAL = ["", "plain", "a\nb", "x | y", "with:colon", " spaced  out ", "\t\r\n", string.punctuation, "é✓"]


def test_property_receipt_is_one_line_with_hash_budget_and_state() -> None:
    """R5: whatever a caller puts in a field, the receipt is one line and
    carries hash, budget delta and state."""
    for op, file, hash_, state, tag in itertools.product(_ADVERSARIAL, _ADVERSARIAL, _ADVERSARIAL, _ADVERSARIAL, _ADVERSARIAL[:4]):
        for delta in (-1200, -50, 0, 340, 50000):
            line = receipt.format_line(ok=True, op=op or "op", hash=hash_, budget_delta=delta, state=state, file=file or None, tags=(tag,) if tag else ())
            assert "\n" not in line and "\r" not in line
            assert "hash:" in line and "budget:" in line and "state:" in line
            assert f"budget:{receipt.humanize_delta(delta)}" in line


def test_property_humanize_delta_round_trips_sign_and_magnitude() -> None:
    for tokens in range(-100_000, 100_001, 997):
        text = receipt.humanize_delta(tokens)
        assert (text.startswith("-")) == (tokens < 0)
        value = float(text.rstrip("k")) * (1000 if text.endswith("k") else 1)
        assert abs(value - tokens) <= 50


def test_property_system_chat_messages_cannot_ask_or_overflow() -> None:
    """R13: no system-authored chat message with a question exists; no
    digest longer than the cap exists."""
    for text in ("ok", "approve?", "why", "ready? yes"):
        should_fail = "?" in text
        try:
            chat.CatastropheAlert(cause="lockdown", hash="h", remediation=text)
            chat.Digest(lines=(text, "hash: h"), receipts_hash="h", sig="s")
        except chat.AsksAQuestion:
            assert should_fail
        else:
            assert not should_fail
    for n in range(0, 10):
        lines = tuple(f"line {i}" for i in range(n - 1)) + (("hash: h",) if n else ())
        if 1 <= n <= 6:
            chat.Digest(lines=lines, receipts_hash="h", sig="s")
        else:
            with pytest.raises(ValueError):
                chat.Digest(lines=lines, receipts_hash="h", sig="s")
