"""The founder's agent-work state machine: YIELDING, IN-PROGRESS, ABANDONED.

Founder protocol (2026-11-09, issued over Telegram): an agent given work has exactly
three states and no others.

    YIELDING      - the agent is still driving the work but has surfaced ONE bounded,
                    structured decision to the founder (via the Telegram door) after
                    proving it exhausted every discovery mechanism and playbook. The
                    work is NOT parked; yielding is a live state, and the agent keeps
                    working every other part of the task. The founder's one tap is a
                    capability, never a prerequisite.
    IN-PROGRESS   - the agent is working. This is the DEFAULT, and autonomy is the
                    default: the agent runs to done/operational/proven without waiting
                    for the founder to be "there".
    ABANDONED     - the work is released: the claim lapsed or was forfeited, the
                    session stalled, or it was superseded. Abandoned is terminal for
                    THIS owner - a stalled session is auto-reassigned, never silently
                    resumed by the same agent. Resuming requires a fresh claim.

There is NO fourth state. "running", "blocked", "narrating", "done" and
"pausing" are NOT states an agent may report - they are either a sub-status of the
three above, or they are the disease this machine exists to extinguish. The estate
built a free-text status surface three times and abandoned it twice (see
catalog/census/model.py); this module is the closed set that makes a fourth state
impossible to express rather than merely forbidden.

A state is a closed enum of three string constants. Enforcement is `validate_state`
and `validate_transition`: they RAISE a typed `UnknownStateError` / `IllegalTransition`
on any value outside the set, any empty value, any missing value, or any transition
not in the table. There is no silent default and no coercion - case and whitespace
variants are refused, so each state has exactly one canonical spelling. A machine that
admits an ambiguous state is a machine with room for gossip; this one has none.

The transition table makes ABANDONED terminal for its owner: an abandoned session is
auto-reassigned, so `abandoned -> in-progress` is illegal (a fresh claim is required,
which is a new IN-PROGRESS - the reassignment mechanism always opens a new owner).

This module is a leaf: nothing imports it yet. It is the single source of truth the
engine, the census and the card are to adopt, so the estate has ONE state machine and
not eleven.
"""

from __future__ import annotations

# --- the closed set ---------------------------------------------------------------------------

STATE_YIELDING = "yielding"
STATE_IN_PROGRESS = "in-progress"
STATE_ABANDONED = "abandoned"

# The ONLY three states. The tuple is the contract; the validator is its enforcement.
AGENT_STATES = (STATE_YIELDING, STATE_IN_PROGRESS, STATE_ABANDONED)

# Why a session was abandoned. A closed set on purpose (the census's UNCATALOGUED_REASONS
# idiom): a new reason is a new fact about the estate, not a free-text excuse.
REASON_CLAIM_RELEASED = "claim_released"
REASON_STALLED = "stalled"
REASON_SUPERSEDED = "superseded"

ABANDONED_REASONS = (REASON_CLAIM_RELEASED, REASON_STALLED, REASON_SUPERSEDED)

# The legal transitions. ABANDONED is terminal for its owner, so it has no outgoing edge.
# A fresh claim is a NEW in-progress session, not a transition out of abandoned.
_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    STATE_IN_PROGRESS: (STATE_YIELDING, STATE_ABANDONED),
    STATE_YIELDING: (STATE_IN_PROGRESS, STATE_ABANDONED),
    STATE_ABANDONED: (),
}


class UnknownStateError(ValueError):
    """A state outside the closed set. Raised before anything acts on the value."""


class IllegalTransition(ValueError):
    """A state change not in the transition table (e.g. abandoned -> in-progress)."""


def validate_state(state: str | None) -> str:
    """Return the state if it is exactly one of the three; raise otherwise.

    No silent default, no coercion, no case/whitespace normalisation: an agent that
    cannot name its state correctly has not set its state, and the machine says so.
    """
    if state is None:
        raise UnknownStateError("agent state is missing (None); it must be set")
    if not isinstance(state, str):
        raise UnknownStateError(
            f"agent state must be a string, got {type(state).__name__}"
        )
    if state not in AGENT_STATES:
        raise UnknownStateError(
            f"unknown agent state {state!r}; must be one of {AGENT_STATES}"
        )
    return state


def validate_transition(current: str, nxt: str) -> str:
    """Validate a move current -> nxt; raise on either an unknown state or an illegal edge."""
    current = validate_state(current)
    nxt = validate_state(nxt)
    if nxt not in _ALLOWED_TRANSITIONS.get(current, ()):
        raise IllegalTransition(
            f"illegal agent-state transition {current!r} -> {nxt!r}; "
            f"allowed: {_ALLOWED_TRANSITIONS.get(current, ())}"
        )
    return nxt


def allowed_transitions(state: str) -> tuple[str, ...]:
    """The legal next states from `state` (raises if `state` is unknown)."""
    validate_state(state)
    return _ALLOWED_TRANSITIONS[state]


def is_agent_state(value: object) -> bool:
    """Non-raising membership check for the closed set."""
    return isinstance(value, str) and value in AGENT_STATES


def validate_abandoned_reason(reason: str) -> str:
    """An abandoned session must name WHY it was abandoned, from the closed set."""
    if reason not in ABANDONED_REASONS:
        raise UnknownStateError(
            f"unknown abandon reason {reason!r}; must be one of {ABANDONED_REASONS}"
        )
    return reason


# --- the mapping of legacy free-text statuses -> the three ------------------------------

# The card (sovereign/otto/card.py) speaks the statuses running/waiting/done/stopped/
# denied/failed. Those are SUB-statuses, not states. This table maps them onto the three
# so the card and the state machine cannot drift: every legacy status is exactly one of
# YIELDING / IN-PROGRESS / ABANDONED / TERMINAL.
STATUS_RUNNING = "running"
STATUS_WAITING = "waiting"
STATUS_DONE = "done"
STATUS_STOPPED = "stopped"
STATUS_DENIED = "denied"
STATUS_FAILED = "failed"

# waiting (which in the card means "asking the founder") is YIELDING; running is
# IN-PROGRESS; the terminal statuses are the closed-set outcomes of a session, and
# "abandoned" is what a lapsed/stalled session becomes.
LEGACY_STATUS_TO_STATE: dict[str, str | None] = {
    STATUS_RUNNING: STATE_IN_PROGRESS,
    STATUS_WAITING: STATE_YIELDING,
    STATUS_DONE: None,  # terminal: finished, not a live agent-work state
    STATUS_STOPPED: None,
    STATUS_DENIED: None,
    STATUS_FAILED: None,
}
