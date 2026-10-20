"""The hedged embed: a lane that drops half its requests must not cost the brief 20 s.

hedge.py is graded directly; its wiring into /memories/brief is pinned by reading main.py (ast),
because main.py cannot be imported here (see test_ranking_and_consolidation.py).
"""

from __future__ import annotations

import ast
import threading
import time
from pathlib import Path

import hedge

HERE = Path(__file__).resolve().parent.parent


def lane(answers):
    """A fake upstream: call i sleeps answers[i][0] (capped at its timeout), then returns [1]."""
    calls = []
    lock = threading.Lock()

    def call(timeout):
        with lock:
            i = len(calls)
            calls.append(timeout)
        delay, value = answers[i]
        time.sleep(min(delay, timeout))
        return value if delay <= timeout else None

    return call, calls


def timed(fn):
    t = time.monotonic()
    got = fn()
    return got, time.monotonic() - t


def test_a_fast_first_answer_is_used_without_a_second_attempt():
    call, calls = lane([(0.01, "v1"), (0.01, "v2")])
    got, took = timed(lambda: hedge.first_answer(call, 3, 0.2, 1.0))
    assert got == "v1"
    assert len(calls) == 1
    assert took < 0.15


def test_a_hung_first_attempt_is_overtaken_by_the_hedge():
    # the measured failure: the first request never answers, the next one answers at once
    call, calls = lane([(30, "hung"), (0.01, "v2")])
    got, took = timed(lambda: hedge.first_answer(call, 3, 0.1, 1.0))
    assert got == "v2"
    assert len(calls) == 2
    assert took < 0.4


def test_every_attempt_hanging_costs_the_deadline_not_the_upstream_timeout():
    call, calls = lane([(30, "a"), (30, "b"), (30, "c")])
    got, took = timed(lambda: hedge.first_answer(call, 3, 0.05, 0.3))
    assert got is None
    assert len(calls) == 3
    assert took < 0.5
    # each attempt is handed what is left of the deadline, never more
    assert all(t <= 0.3 for t in calls)


def test_a_failed_attempt_is_a_miss_and_the_next_one_still_counts():
    seen = []

    def call(timeout):
        seen.append(timeout)
        if len(seen) == 1:
            raise OSError("connection reset")
        return "v2"

    assert hedge.first_answer(call, 3, 0.05, 1.0) == "v2"


def test_none_from_every_attempt_is_none():
    assert hedge.first_answer(lambda t: None, 3, 0.01, 0.2) is None


def test_the_brief_embeds_its_task_through_the_hedge():
    tree = ast.parse((HERE / "main.py").read_text())
    brief = next(
        n
        for n in tree.body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "memory_brief"
    )
    src = ast.unparse(brief)
    assert "hedge.first_answer" in src
    assert "BRIEF_EMBED_DEADLINE_S" in src
    # the deadline sits inside the router callback's 1.5 s read of the brief
    consts = {
        t.id: n.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        for t in n.targets
        if isinstance(t, ast.Name)
    }
    default = float(ast.literal_eval(consts["BRIEF_EMBED_DEADLINE_S"].args[0].args[1]))
    assert default < 1.5
