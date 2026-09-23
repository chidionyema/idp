"""The harness proving itself (R39).

This module is also the worked example the other five builders copy: a
`scenarios(...)` call naming the feature by its repository path, steps that
drive real code, and state carried in `context`.
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from .conftest import FakeBudget, FakeClock, MessageSink, Overdrawn

scenarios("sovereign/tests/fixtures/bdd/harness_selftest.feature")


# --- the temporary estate ---------------------------------------------------


@given("a temporary estate")
def _temp_estate(estate_home: Path, context: dict) -> None:
    context["estate_home"] = estate_home


@then("the DAG root exists and is empty")
def _dag_root_empty(dag_root: Path) -> None:
    assert dag_root.is_dir()
    assert list(dag_root.iterdir()) == []


@then("the receipts path is inside the temporary estate")
def _receipts_inside(receipts_path: Path, estate_home: Path) -> None:
    assert estate_home in receipts_path.parents, f"{receipts_path} escaped {estate_home}"


@then('"sovereign.config" resolves "estate.home" to the temporary estate')
def _config_resolves(config, estate_home: Path) -> None:
    assert Path(config.get("estate.home").value) == estate_home


# --- the fake clock ---------------------------------------------------------


@given("a fake clock")
def _a_clock(clock: FakeClock, context: dict) -> None:
    context["t0"] = clock.now()


@when("the clock advances 300 seconds")
def _advance(clock: FakeClock) -> None:
    clock.advance(300)


@then("300 seconds have elapsed")
def _elapsed(clock: FakeClock, context: dict) -> None:
    assert clock.now() - context["t0"] == 300
    assert clock.monotonic() == 300


@then("the clock did not move on its own")
def _clock_still(clock: FakeClock) -> None:
    first = clock.now()
    # Real time passes here; the fixture's clock must not.
    subprocess.run(["true"], check=True)
    assert clock.now() == first


# --- the budget -------------------------------------------------------------


@given("a session with budget 2000 tokens", target_fixture="session_budget")
def _budget_2k(budget) -> FakeBudget:
    return budget(2000)


@when("8 threads each spend 250 tokens at the same time")
def _concurrent_spend(session_budget: FakeBudget, context: dict) -> None:
    start = threading.Barrier(8)
    errors: list[BaseException] = []
    below_zero: list[int] = []

    def worker() -> None:
        start.wait()
        try:
            balance = session_budget.spend(250)
        except BaseException as exc:  # noqa: BLE001 - recorded, then asserted on
            errors.append(exc)
            return
        if balance < 0:
            below_zero.append(balance)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    context["errors"] = errors
    context["below_zero"] = below_zero


@then("the balance is 0")
def _balance_zero(session_budget: FakeBudget, context: dict) -> None:
    assert context["errors"] == [], f"a spend inside budget was refused: {context['errors']!r}"
    assert session_budget.balance == 0
    assert session_budget.spent == 2000


@then("no spend took the balance below zero")
def _never_negative(context: dict) -> None:
    assert context["below_zero"] == []


@when("the budget is exhausted")
def _exhaust(session_budget: FakeBudget) -> None:
    session_budget.spend(session_budget.balance)
    assert session_budget.exhausted


@then("an unsigned refill of 10000 tokens is refused")
def _unsigned_refused(session_budget: FakeBudget) -> None:
    with pytest.raises(PermissionError, match="signature required"):
        session_budget.refill(10_000)
    assert session_budget.balance == 0


@then("a signed refill of 10000 tokens restores the balance")
def _signed_ok(session_budget: FakeBudget) -> None:
    assert session_budget.refill(10_000, signed=True) == 10_000


# --- the message sink -------------------------------------------------------


@given("a captured-messages sink")
def _sink(messages: MessageSink) -> None:
    assert isinstance(messages, MessageSink)


@then("zero messages were sent to the chat")
def _silent(messages: MessageSink) -> None:
    messages.assert_silent()


@when("a catastrophe is reported")
def _catastrophe(messages: MessageSink) -> None:
    messages.send("home", "integrity failure: hash mismatch", kind="catastrophe")


@then("exactly one message was sent to the chat")
def _one_message(messages: MessageSink) -> None:
    assert messages.assert_exactly_one().kind == "catastrophe"


# --- the scratch repo -------------------------------------------------------


@given("a scratch repo", target_fixture="repo")
def _repo(scratch_repo: Path) -> Path:
    return scratch_repo


@then("HEAD names a commit that exists in the repo")
def _head_exists(repo: Path) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert len(head) == 40
    kind = subprocess.run(
        ["git", "cat-file", "-t", head], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert kind == "commit"


def test_overdraw_is_refused() -> None:
    """Incident-shaped unit check on the fixture the scenarios lean on: a
    spend larger than the balance must raise rather than go negative, or
    cp31's "never negative" scenario would pass against a broken budget."""
    b = FakeBudget(balance=100)
    with pytest.raises(Overdrawn):
        b.spend(101)
    assert b.balance == 100

    # Compare-and-swap: a writer holding a stale version loses.
    seen = b.version
    assert b.try_spend(10, seen) == 90
    assert b.try_spend(10, seen) is None
    assert b.balance == 90
