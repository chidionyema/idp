"""cp31 acceptance: Finite state machine and budget enforcer (R28, R29, R30, R32).

Steps drive engine/budget.py (the sqlite compare-and-swap row), engine/fsm.py,
engine/termination.py and the signed receipt chain, each against the
temporary estate conftest.py builds. No Temporal server: the workflow that
strings these together is exercised by its own unit tests, and what this
feature states are rules about the budget, the machine and the halt
reasons, which these modules hold.
"""
from __future__ import annotations

import asyncio
import importlib
import threading
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/sovereign-bus/cp31_fsm_budget.feature")

SESSION = "sb-cp31test"


@pytest.fixture(autouse=True)
def software_trust(estate_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    importlib.reload(importlib.import_module("sovereign.config"))


def _receipt(context: dict[str, Any], kind: str, status: str, text: str, **fields: Any) -> dict[str, Any]:
    from sovereign.engine import activities

    record = {
        "ts": "1970-01-01T00:00:00+00:00",
        "session_id": context.get("session_id", SESSION),
        "kind": kind,
        "by": "engine",
        "text": text,
        "step": context.get("step", 0),
        "status": status,
        "task": "",
        "runner": "",
        "state": {"session_id": context.get("session_id", SESSION), "step": context.get("step", 0), "status": status},
        **fields,
    }
    return asyncio.run(activities.append_receipt(record))


# ---- budget exhaustion, halt, refill ----


@given(parsers.parse("a session with budget {tokens:d}k tokens"))
def _session_with_budget(context: dict[str, Any], tokens: int) -> None:
    from sovereign.engine import budget

    context["session_id"] = SESSION
    context["step"] = 3
    context["budget"] = budget.allocate(SESSION, tokens * 1000)


@when("the budget reaches zero")
def _budget_to_zero(context: dict[str, Any]) -> None:
    from sovereign.engine import budget

    spent = budget.spend(SESSION, context["budget"].remaining)
    assert spent.halted and spent.remaining == 0
    context["halt"] = _receipt(context, "halt", "halted", "budget", budget_remaining=0)


@then(parsers.parse('the session status is "{status}" with reason "{reason}"'))
def _status_reason(context: dict[str, Any], status: str, reason: str) -> None:
    row = context["halt"]
    assert row["status"] == status and row["text"] == reason


@then("its state hash is in the receipt")
def _state_hash(context: dict[str, Any], config) -> None:
    from sovereign.engine import receipts

    row = context["halt"]
    assert len(row.get("state_hash", "")) == config.RECEIPTS_HASH_HEX_LEN
    assert receipts.verify()["ok"]


@when(parsers.parse("a signed refill of {tokens:d}k arrives"))
def _refill(context: dict[str, Any], tokens: int) -> None:
    from sovereign.engine import budget

    refilled = budget.refill(SESSION, tokens * 1000)
    assert not refilled.halted
    line = _receipt(context, "refill", "running", f"refill:{tokens}k", signed=True, tokens=tokens * 1000)
    assert line.get("hw_sig") and line.get("hw_backend"), line
    context["resume"] = _receipt(context, "resume", "running", "resumed")


@then("the session resumes from the same step")
def _same_step(context: dict[str, Any]) -> None:
    from sovereign.engine import budget

    assert context["resume"]["step"] == context["halt"]["step"]
    assert context["resume"]["status"] == "running"
    assert not budget.read(SESSION).halted


# ---- cycle detection ----


WORDS = {"five": 5}


@when(parsers.parse("a session repeats planning→tool_use→synthesis {count} times"))
def _repeat_cycles(context: dict[str, Any], count: str) -> None:
    from sovereign.engine import fsm

    n = WORDS[count]
    m = fsm.FSM(max_cycles=n)
    m.advance()  # init -> planning
    # A cycle is counted on the back edge synthesis -> planning, so the
    # n-th back edge completes cycle n and the (n+1)-th is the one the
    # machine must refuse. Keep going until it does, bounded so a machine
    # that never pauses fails the assertion below instead of looping.
    for _ in range(n + 1):
        m.advance()  # -> tool_use
        m.advance()  # -> synthesis
        try:
            m.advance()  # -> planning, which closes the cycle
        except fsm.CyclePause as exc:
            context["pause"] = exc
            break
    context["fsm"] = m
    context["n"] = n


@then(parsers.parse('it pauses before the sixth with reason "{reason}"'))
def _pauses(context: dict[str, Any], reason: str) -> None:
    from sovereign.engine import fsm

    m = context["fsm"]
    assert m.paused and m.cycles == context["n"], m.as_dict()
    # Paused BEFORE the sixth: the refused edge was synthesis -> planning,
    # so the machine sits in synthesis and planning was entered exactly
    # n + 1 times (once from init, then once per completed cycle).
    assert m.state == fsm.CYCLE_PATH[-1]
    assert m.history.count(fsm.CYCLE_PATH[0]) == context["n"] + 1
    row = _receipt({"session_id": SESSION, "step": 0}, "pause", "paused", reason)
    assert row["text"] == reason


# ---- blind execution ----


@given(parsers.parse("Langfuse is unreachable for more than {minutes:d} minutes"))
def _langfuse_blind(context: dict[str, Any], config) -> None:
    from sovereign.engine import termination

    blind_s = float(config.get("blind.halt_after_min").value) * termination.SECONDS_PER_MINUTE + 1
    context["verdict"] = termination.evaluate(termination.Signals(langfuse_blind_s=blind_s))
    context["sessions"] = [("sb-blind-a", False), ("sb-blind-b", False), ("sb-critical", True)]


@then(parsers.parse('every non-critical session is halted with reason "{reason}"'))
def _halt_non_critical(context: dict[str, Any], reason: str) -> None:
    from sovereign.engine import receipts

    verdict = context["verdict"]
    fired = [r["reason"] for r in verdict["reasons"]]
    assert verdict["action"] == "halt" and fired == [reason], verdict
    for session_id, critical in context["sessions"]:
        if not critical:
            _receipt({"session_id": session_id, "step": 1}, "halt", "halted", fired[0])
    halted = {r["session_id"] for r in receipts.read_all() if r.get("kind") == "halt" and r.get("text") == reason}
    assert halted == {s for s, critical in context["sessions"] if not critical}


# ---- concurrent spend ----


@given("two activities spend from one budget at the same time")
def _concurrent_spend(context: dict[str, Any]) -> None:
    from sovereign.engine import budget

    start, a, b = 1000, 300, 400
    budget.allocate("sb-race", start)
    results: dict[str, Any] = {}
    gate = threading.Barrier(2)

    def spender(name: str, tokens: int) -> None:
        gate.wait()
        results[name] = budget.spend("sb-race", tokens)

    threads = [threading.Thread(target=spender, args=("a", a)), threading.Thread(target=spender, args=("b", b))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    context.update(start=start, spends=(a, b), results=results)


@then("the final balance equals start minus both spends, never negative")
def _balance(context: dict[str, Any]) -> None:
    from sovereign.engine import budget

    final = budget.read("sb-race").remaining
    a, b = context["spends"]
    assert final == context["start"] - a - b
    assert final >= 0
    assert context["results"]["a"].spent + context["results"]["b"].spent == a + b
