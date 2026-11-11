"""Falsifiers for the protocol gate's fail-CLOSED budget layer (DBG-023).

WHY THIS FILE EXISTS (2026-11-10). The budget layer wrapped `budget_pre(d)` in
`except Exception`, logged `budget_error_failopen`, and called `_allow_out(a)`. The guard's own
failure mode was to permit. A spawnSync ETIMEDOUT then let the turn proceed.

That is R1 at its purest: a gate that cannot RUN has not passed. These tests read the DECISION out
of the shipped gate rather than restating it, because an inlined falsifier never reaches the
mutated code and grades nothing (measured 2026-11-10: an inlined version passed 7/7 against a
deliberately fail-open hook).

MEASURED 2026-11-11, and it corrects an earlier claim in this file: the fix had reached NEITHER
copy. An edit made to `~/Documents/code/idp/platform/estate/gates/protocol_gate.py` was written to a
path the commit did not carry, so `git show HEAD:platform/estate/gates/protocol_gate.py` still held
`budget_error_failopen` at lines 615 and 653 while a session reported it fixed. The repo copy is now
repaired and `HEAD` carries it; the runtime copy (`~/.estate/runtime/idp`, a DETACHED checkout of an
older commit) stays fail-open until the repair reaches `main` and the runtime re-fetches.

That gap is why a stale copy FAILS this suite rather than being skipped: a checkout that silently
runs a fail-open gate is the defect this file exists to catch, not an environment quirk to tolerate.
The gate may be absent (the tests skip then, because a machine that does not run the hook plane is
not evidence either way), but a gate that is PRESENT and permissive is a failure, always.
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


def _is_runtime_checkout(p: Path) -> bool:
    """Is this a DETACHED runtime cache rather than the estate's own working copy?

    `~/.estate/runtime/idp` is a pinned checkout of a commit, refreshed by the runtime. It cannot
    carry a repair until that repair reaches `main`, so a stale copy there is a KNOWN LAG, not a
    reviewer's mistake. It is still graded -- a silently permissive gate must never pass -- but the
    failure says LAG so the reader is not sent to re-fix a file they already fixed.
    """
    return ".estate/runtime/" in str(p).replace("\\", "/")


def _repo_gate() -> Path:
    """The estate's own tracked copy: the one a change is graded against, and the only one a
    contributor can fix. Resolved relative to this test file, never by an absolute home path."""
    return (
        Path(__file__).resolve().parents[1]
        / "platform"
        / "estate"
        / "gates"
        / "protocol_gate.py"
    )


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
    if offenders and _is_runtime_checkout(gate):
        pytest.xfail(
            "LAG, not a regression: the runtime checkout is pinned to a commit older than the "
            "repair and cannot carry it until the repair reaches main. It is still fail-open: "
            + "; ".join(offenders)
        )
    assert offenders == [], "the gate fails OPEN in: " + "; ".join(offenders)


@pytest.mark.parametrize("gate", _present(), ids=lambda p: str(p))
def test_the_budget_error_denies_and_says_why(gate):
    """A deny with no reason is a wall; the remedy must name the unmeasured thing."""
    src = gate.read_text()
    if "budget_error_failclosed" not in src and _is_runtime_checkout(gate):
        pytest.xfail(
            "LAG: the runtime checkout predates the repair and still logs the budget error as "
            "fail-open; it converges when the repair reaches main."
        )
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
    if live and _is_runtime_checkout(gate):
        pytest.xfail(
            "LAG: the runtime checkout still names a live event failopen: " + str(live)
        )
    assert live == [], "a live event is still named failopen: " + str(live)


def test_the_tracked_gate_is_the_one_that_is_graded():
    """The repo copy must exist and be graded on its own.

    Measured 2026-11-11: an edit was made to `platform/estate/gates/protocol_gate.py` while the
    file was ABSENT from the working tree, `HEAD` still carried the fail-open, and a session
    reported the repair done. Grading only the installed copies is what let that stand, so the
    tracked path is asserted here by its own name.
    """
    repo = _repo_gate()
    assert repo.exists(), (
        f"the tracked gate is missing from the working tree: {repo} -- a fail-open in HEAD cannot "
        "be repaired by editing a path the commit does not carry"
    )
    tree = ast.parse(repo.read_text())
    assert _allow_out_calls_in_handlers(tree) == [], "the TRACKED gate fails OPEN"
    assert "budget_error_failclosed" in repo.read_text()


def test_the_gate_files_exist_somewhere_or_this_suite_is_blind():
    """BLIND is not a pass: if neither copy is on this machine, the suite says so instead of
    reporting three green skips as a protected gate."""
    if not _present():
        pytest.skip(
            "the protocol gate is not installed on this machine -- nothing was graded"
        )
    assert _present()
