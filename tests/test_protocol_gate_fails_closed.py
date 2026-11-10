"""Falsifiers for the protocol gate's fail-CLOSED budget layer (DBG-023).

WHY THIS FILE EXISTS (2026-11-10). `/Users/roseonyema/.estate/gates/protocol_gate.py` wrapped
`budget_pre(d)` in `except Exception`, logged `budget_error_failopen`, and called `_allow_out(a)`.
The guard's own failure mode was to permit. A spawnSync ETIMEDOUT then let the turn proceed.

That is R1 at its purest: a gate that cannot RUN has not passed. These tests read the DECISION out
of the shipped gate rather than restating it, because an inlined falsifier never reaches the
mutated code and grades nothing (measured 2026-11-10: an inlined version passed 7/7 against a
deliberately fail-open hook).

The gate lives outside the repo (`~/.estate/gates/`), so the tests skip when it is absent rather
than failing a checkout on a machine that does not run the estate's hook plane.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

GATES = [
    Path.home() / ".estate" / "gates" / "protocol_gate.py",
    Path.home()
    / ".estate"
    / "runtime"
    / "idp"
    / "platform"
    / "estate"
    / "gates"
    / "protocol_gate.py",
]


def _present():
    return [p for p in GATES if p.exists()]


def _allow_out_calls_in_handlers(tree: ast.AST):
    """Every `except` handler that can reach `_allow_out` -- the fail-open shape, by AST.

    Reading the AST rather than grepping the text is deliberate: the module's own comments name
    `budget_error_failopen` to explain the defect, and a text search would flag the explanation.
    """
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call):
                fn = inner.func
                name = getattr(fn, "id", "") or getattr(fn, "attr", "")
                if name == "_allow_out":
                    offenders.append(
                        f"line {inner.lineno}: except handler at line {node.lineno} calls _allow_out"
                    )
    return offenders


@pytest.mark.parametrize("gate", _present(), ids=lambda p: str(p))
def test_no_except_handler_can_allow_the_turn(gate):
    """DBG-023's falsifier: a guard whose error path is the permissive path."""
    tree = ast.parse(gate.read_text())
    offenders = _allow_out_calls_in_handlers(tree)
    assert offenders == [], "the gate fails OPEN in: " + "; ".join(offenders)


@pytest.mark.parametrize("gate", _present(), ids=lambda p: str(p))
def test_the_budget_error_denies_and_says_why(gate):
    """A deny with no reason is a wall; the remedy must name the unmeasured thing."""
    src = gate.read_text()
    assert "budget_error_failclosed" in src, (
        "the budget error must be logged as fail-CLOSED"
    )
    assert "_deny_out(" in src, "the budget error path must deny"


@pytest.mark.parametrize("gate", _present(), ids=lambda p: str(p))
def test_no_live_event_still_named_failopen(gate):
    """A lying log-event name is how a fail-open survives a grep for fail-opens: the one real
    fail-open hid behind a line that had already been renamed to something harmless."""
    src = gate.read_text()
    live = [
        ln
        for ln in src.splitlines()
        if "failopen" in ln and not ln.lstrip().startswith("#")
    ]
    assert live == [], "a live event is still named failopen: " + str(live)


def test_the_gate_files_exist_somewhere_or_this_suite_is_blind():
    """BLIND is not a pass: if neither copy is on this machine, the suite says so instead of
    reporting three green skips as a protected gate."""
    if not _present():
        pytest.skip(
            "the protocol gate is not installed on this machine -- nothing was graded"
        )
    assert _present()
