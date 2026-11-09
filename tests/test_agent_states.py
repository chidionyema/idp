"""Falsifier for catalog/agent_states.py - the founder's closed three-state machine.

Founder protocol (2026-11-09): an agent given work has exactly three states -
yielding / in-progress / abandoned - and no fourth. This test proves the closed set
TWO WAYS: it accepts the three legal states and their legal transitions, and it
REJECTS every value outside the set (a fourth state, empty, missing, a case variant,
and the old free-text statuses the founder banned). A gate that only shows the legal
side passes can be satisfied by a function that accepts everything; the rejections
here are what make `validate_state` a falsifier rather than a stamp.

The estate built a free-text status surface three times and abandoned it twice
(catalog/census/model.py). This test is the tripwire that keeps a fourth state from
ever being expressible again: add one and this suite goes red.
"""

from __future__ import annotations

import pytest

from catalog.agent_states import (
    ABANDONED_REASONS,
    AGENT_STATES,
    LEGACY_STATUS_TO_STATE,
    REASON_CLAIM_RELEASED,
    REASON_STALLED,
    REASON_SUPERSEDED,
    STATE_ABANDONED,
    STATE_IN_PROGRESS,
    STATE_YIELDING,
    IllegalTransition,
    UnknownStateError,
    allowed_transitions,
    is_agent_state,
    validate_abandoned_reason,
    validate_state,
    validate_transition,
)


# --- the closed set is exactly three, and only the three -------------------------------


def test_the_closed_set_is_exactly_the_three_founder_states():
    assert AGENT_STATES == ("yielding", "in-progress", "abandoned")


def test_each_legal_state_is_accepted():
    for s in (STATE_YIELDING, STATE_IN_PROGRESS, STATE_ABANDONED):
        assert validate_state(s) == s


def test_is_agent_state_membership_agrees_with_validate():
    assert is_agent_state(STATE_YIELDING) is True
    assert is_agent_state(STATE_IN_PROGRESS) is True
    assert is_agent_state(STATE_ABANDONED) is True
    assert is_agent_state("running") is False
    assert is_agent_state(None) is False


# --- a fourth state, empty, missing, and every variant are refused ---------------------


@pytest.mark.parametrize(
    "bad",
    [
        "running",  # the old default that must die
        "blocked",  # the state the founder banned: no blocking out
        "narrating",  # the disease: narrating is not a state
        "pausing",  # another name for the same disease
        "done",  # terminal, not a live agent-work state
        "yielding ",  # trailing whitespace is not canonical
        "YIELDING",  # case variant is not canonical
        "in_progress",  # underscore variant is not canonical
        "",  # empty is not a state
    ],
)
def test_any_value_outside_the_set_is_refused(bad):
    with pytest.raises(UnknownStateError):
        validate_state(bad)


def test_missing_state_is_refused():
    with pytest.raises(UnknownStateError):
        validate_state(None)


def test_non_string_state_is_refused():
    with pytest.raises(UnknownStateError):
        validate_state(123)


# --- legal and illegal transitions -----------------------------------------------------


def test_legal_transitions_are_accepted():
    assert validate_transition(STATE_IN_PROGRESS, STATE_YIELDING) == STATE_YIELDING
    assert validate_transition(STATE_IN_PROGRESS, STATE_ABANDONED) == STATE_ABANDONED
    assert validate_transition(STATE_YIELDING, STATE_IN_PROGRESS) == STATE_IN_PROGRESS
    assert validate_transition(STATE_YIELDING, STATE_ABANDONED) == STATE_ABANDONED


def test_abandoned_has_no_outgoing_edge():
    # abandoned is terminal for its owner: auto-reassign, never silently resume.
    assert allowed_transitions(STATE_ABANDONED) == ()
    with pytest.raises(IllegalTransition):
        validate_transition(STATE_ABANDONED, STATE_IN_PROGRESS)
    with pytest.raises(IllegalTransition):
        validate_transition(STATE_ABANDONED, STATE_YIELDING)


def test_transition_to_a_fourth_state_is_refused():
    with pytest.raises(UnknownStateError):
        validate_transition(STATE_IN_PROGRESS, "running")


# --- the abandon reasons are a closed set too -----------------------------------------


def test_abandon_reasons_are_closed():
    assert ABANDONED_REASONS == (
        REASON_CLAIM_RELEASED,
        REASON_STALLED,
        REASON_SUPERSEDED,
    )
    for r in ABANDONED_REASONS:
        assert validate_abandoned_reason(r) == r


def test_free_text_abandon_reason_is_refused():
    with pytest.raises(UnknownStateError):
        validate_abandoned_reason("I got bored")


# --- the legacy status -> state mapping leaves no drift --------------------------------


def test_the_legacy_card_statuses_map_onto_the_three_states():
    # waiting (asking the founder) is YIELDING; running is IN-PROGRESS; the terminal
    # statuses are not live agent-work states. Every legacy status maps somewhere.
    assert LEGACY_STATUS_TO_STATE["running"] == STATE_IN_PROGRESS
    assert LEGACY_STATUS_TO_STATE["waiting"] == STATE_YIELDING
    assert LEGACY_STATUS_TO_STATE["done"] is None
    assert LEGACY_STATUS_TO_STATE["stopped"] is None
    assert LEGACY_STATUS_TO_STATE["denied"] is None
    assert LEGACY_STATUS_TO_STATE["failed"] is None
