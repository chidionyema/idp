"""The governance FSM and its cycle detector (R28/R30, master spec 4.3).

    init -> planning -> tool_use -> synthesis -> terminal

Pure data and pure functions: no Temporal import, no disk, no clock. That
is deliberate. workflow.py runs inside the Temporal sandbox and this
module is imported there, so anything with a side effect would have to
live in an activity instead. It also means the whole state machine is
testable as a value, which is the cheapest rung that can hold this
guarantee (types first, then one property).

The spec names the states `tool_use` and `synthesis`; the crew#219 brief
paraphrased the same two as `executing` and `verifying`. Rather than pick
a winner and leave half the estate speaking the other dialect, ALIASES
below resolves either spelling to the spec's own name. The spec is the
record; the alias is the courtesy.

Cycle detection (spec 4.3): `planning -> tool_use -> synthesis -> planning`
repeated fsm.max_cycles times is suspicious, so the machine pauses BEFORE
the next one begins -- pause before the 6th at the default of 5, not
after it, which is the difference between catching a loop and logging it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from sovereign import config

INIT = config.FSM_INITIAL_STATE
TERMINAL = config.FSM_TERMINAL_STATE
CYCLE_PATH: tuple[str, ...] = tuple(config.FSM_CYCLE_PATH)
STATES: tuple[str, ...] = (INIT,) + CYCLE_PATH + (TERMINAL,)

ALIASES: dict[str, str] = {"executing": "tool_use", "verifying": "synthesis", "done": TERMINAL}

# Forward edges along the spec's line, plus the one back edge the spec
# names explicitly (synthesis -> planning, the loop cycle detection
# counts). Every state may end at terminal: a halt, a denial or a failure
# is still a terminal state.
_ALLOWED: dict[str, frozenset[str]] = {}


def _build_allowed() -> dict[str, frozenset[str]]:
    order = (INIT,) + CYCLE_PATH
    allowed: dict[str, set[str]] = {s: {TERMINAL} for s in STATES}
    for i, state in enumerate(order):
        if i + 1 < len(order):
            allowed[state].add(order[i + 1])
    if CYCLE_PATH:
        allowed[CYCLE_PATH[-1]].add(CYCLE_PATH[0])
    allowed[TERMINAL] = set()
    return {k: frozenset(v) for k, v in allowed.items()}


_ALLOWED = _build_allowed()


class IllegalTransition(ValueError):
    """The FSM refused a move the spec's line does not contain."""


class CyclePause(RuntimeError):
    """fsm.max_cycles complete cycles have run; the next one is refused."""


def canonical(state: str) -> str:
    """Resolve an alias to the spec's own state name. Unknown names are
    returned unchanged so the caller, not this function, decides that they
    are illegal -- one place raises, not two."""
    return ALIASES.get(state, state)


def is_state(state: str) -> bool:
    return canonical(state) in STATES


def allowed_from(state: str) -> frozenset[str]:
    return _ALLOWED.get(canonical(state), frozenset())


@dataclass
class FSM:
    """One session's machine. `cycles` counts completed passes through
    fsm.cycle_path; `paused` records that the cycle limit refused the next
    one. max_cycles is a field, not a constant read at call time, so a
    workflow can carry the value it started with across a config change
    (Temporal replay determinism)."""

    state: str = INIT
    cycles: int = 0
    paused: bool = False
    max_cycles: int = config.FSM_MAX_CYCLES
    history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.state = canonical(self.state)
        if not self.history:
            self.history = [self.state]

    def can(self, to: str) -> bool:
        return canonical(to) in allowed_from(self.state)

    def would_exceed_cycles(self, to: str) -> bool:
        """True when moving to `to` would begin cycle number max_cycles+1.
        The cycle is counted as complete on the back edge, so the check
        that matters is the one taken on the *next* entry into the head of
        the cycle path."""
        target = canonical(to)
        if not CYCLE_PATH or target != CYCLE_PATH[0]:
            return False
        return self.cycles >= self.max_cycles

    def transition(self, to: str) -> str:
        target = canonical(to)
        if target not in STATES:
            raise IllegalTransition(f"not a state: {to!r}")
        if target not in allowed_from(self.state):
            raise IllegalTransition(f"{self.state!r} cannot move to {target!r}")
        if self.would_exceed_cycles(target):
            self.paused = True
            raise CyclePause(f"{self.cycles} cycles completed; refusing cycle {self.cycles + 1}")
        if CYCLE_PATH and self.state == CYCLE_PATH[-1] and target == CYCLE_PATH[0]:
            self.cycles += 1
        self.state = target
        self.history.append(target)
        return self.state

    def advance(self) -> str:
        """Take the one forward edge from here: init -> planning ->
        tool_use -> synthesis -> planning -> ... Raises CyclePause exactly
        where transition() would."""
        order = (INIT,) + CYCLE_PATH
        if self.state == TERMINAL:
            return TERMINAL
        idx = order.index(self.state)
        nxt = order[idx + 1] if idx + 1 < len(order) else CYCLE_PATH[0]
        return self.transition(nxt)

    def finish(self) -> str:
        return self.transition(TERMINAL)

    def as_dict(self) -> dict:
        return {"state": self.state, "cycles": self.cycles, "paused": self.paused, "max_cycles": self.max_cycles}


def replay(states: Iterable[str], max_cycles: int | None = None) -> FSM:
    """Drive a fresh FSM through `states`. Used by the tests and by
    `sb show` to re-derive a session's machine from its receipt history."""
    m = FSM(max_cycles=config.FSM_MAX_CYCLES if max_cycles is None else max_cycles)
    for s in states:
        m.transition(s)
    return m
