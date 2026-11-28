"""Optimus measure: engine.verification_deadline_bounded (MERIDIAN-CTRL-001 section 11.1).

Prints `optimus.engine.verification_deadline_bounded=1` when SessionWorkflow's custody wait
for the independent verifier is bounded: with no verifier answer it re-dispatches for a fixed
number of rounds and then fails closed, and it never reaches an unbounded wait. Prints 0 on
code that still waits forever (or that lacks the bound at all).

Stdlib only (the Greenlane judge has no temporalio, no pytest). It stubs the temporalio
surface workflow.py imports and drives the real `_retain_instruction` coroutine with a fake
workflow clock. The real Temporal Test Server proof is sovereign/engine/test_instruction_id.py.
"""

from __future__ import annotations

import asyncio
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEADLINE_S = 60
ROUNDS = 3


class WouldHang(Exception):
    pass


def _install_stubs(trace: dict) -> None:
    def passthrough(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return lambda fn: fn

    wf = types.ModuleType("temporalio.workflow")
    wf.defn = passthrough
    wf.signal = passthrough
    wf.query = passthrough
    wf.update = passthrough
    wf.run = passthrough
    wf.patched = lambda marker: True
    wf.info = lambda: types.SimpleNamespace(run_id="run-measure")
    wf.now = lambda: __import__("datetime").datetime(
        2026, 1, 1, tzinfo=__import__("datetime").timezone.utc
    )

    async def wait_condition(fn, timeout=None):
        if timeout is None:
            raise WouldHang("unbounded wait_condition")
        trace["virtual_s"] += timeout.total_seconds()
        trace["timeouts"] += 1
        raise asyncio.TimeoutError()

    async def execute_activity(name, arg=None, **kwargs):
        if name == "append_receipt":
            trace["kinds"].append(arg["kind"])
        return {}

    wf.wait_condition = wait_condition
    wf.execute_activity = execute_activity

    common = types.ModuleType("temporalio.common")
    common.RetryPolicy = lambda **kw: kw
    exc = types.ModuleType("temporalio.exceptions")
    exc.ActivityError = type("ActivityError", (Exception,), {})
    exc.CancelledError = type("CancelledError", (Exception,), {})
    pkg = types.ModuleType("temporalio")
    pkg.workflow = wf
    for name, mod in (
        ("temporalio", pkg),
        ("temporalio.workflow", wf),
        ("temporalio.common", common),
        ("temporalio.exceptions", exc),
    ):
        sys.modules[name] = mod


async def _drive(cls) -> tuple[str, object]:
    session = cls()
    session.instruction_id = "INS-MEASURE"
    session.task = "measure the wait"
    session.step = 1
    session.critical = False
    session._guarded_instruction = True
    session._bounded_verification = True
    session._verification_deadline_s = DEADLINE_S
    session._verification_max_rounds = ROUNDS
    session._receipt_activity_timeout_s = 30
    session._receipt_retry_max_attempts = 1
    session._notify_activity_timeout_s = 30
    session._notify_retry_max_attempts = 1
    out = await asyncio.wait_for(
        session._retain_instruction("worker-exit-unverified"), 10
    )
    return out, session


def measure() -> int:
    trace = {"virtual_s": 0, "timeouts": 0, "kinds": []}
    _install_stubs(trace)
    sys.path.insert(0, str(ROOT))
    try:
        from sovereign.engine.workflow import SessionWorkflow

        out, session = asyncio.run(_drive(SessionWorkflow))
    except Exception:
        return 0
    ok = (
        out == "terminal"
        and session.status == "failed"
        and session.reason == "verification-deadline-exceeded"
        and trace["timeouts"] == ROUNDS
        and trace["virtual_s"] == DEADLINE_S * ROUNDS
        and trace["kinds"].count("verification_requested") == ROUNDS
        and trace["kinds"][-1] == "fail"
        and "done" not in trace["kinds"]
    )
    return 1 if ok else 0


if __name__ == "__main__":
    print(f"optimus.engine.verification_deadline_bounded={measure()}")
