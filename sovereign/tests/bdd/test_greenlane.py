"""Binds features/gates/greenlane.feature: the Greenlane engine driven through the chaos model
at 500 lanes, three seeds. The assertions are the founder's acceptance criteria of 2026-09-29,
and they are strict: zero, not "under a threshold"."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from greenlane.simulate import run as _simulate  # noqa: E402

_CACHE: dict = {}


def run(**kw):
    # six scenarios read the same three runs; run each (lanes, seed, reload) once per process
    key = tuple(sorted(kw.items()))
    if key not in _CACHE:
        _CACHE[key] = _simulate(**kw)
    return _CACHE[key]


scenarios("features/gates/greenlane.feature")

SEEDS = (0, 1, 2)
LANES = 500
TICK_BOUND = (
    1500  # ~500 lanes at 3-tick checks, batches of 8, bisection on red: measured < 1000
)


@pytest.fixture
def world():
    return {"lanes": LANES, "seeds": SEEDS}


@given(
    parsers.parse(
        "{n:d} lanes cut from stale worktrees, with broken commits, incompatible pairs, "
        "overlapping files, re-pushes, deletions, hand-raised pull requests, direct pushes "
        "to main, a bot lane and flaky checks"
    )
)
def _lanes(world, n):
    world["lanes"] = n


@given("the same chaos")
def _same(world):
    world["seeds"] = (SEEDS[0],)


@when("the engine runs the lanes to completion")
def _run(world):
    world["reports"] = [run(lanes=world["lanes"], seed=s) for s in world["seeds"]]


@when("the engine runs the lanes with its state serialised and reloaded on every tick")
def _run_reload(world):
    world["reports"] = [run(lanes=world["lanes"], seed=s) for s in world["seeds"]]
    world["reloaded"] = [
        run(lanes=world["lanes"], seed=s, reload_state=True) for s in world["seeds"]
    ]


@then("every sha main ever pointed to is green")
def _main_green(world):
    for r in world["reports"]:
        assert r.main_ever_red == 0, r
        assert r.main_history > 1, r


@then("no broken change is in main")
def _no_broken(world):
    for r in world["reports"]:
        assert r.broken_lanes_landed == 0, r


@then("at least one agent tried to push main directly")
def _pushed(world):
    for r in world["reports"]:
        assert r.direct_push_attempts > 0, r


@then("zero direct pushes to main succeeded")
def _none_pushed(world):
    for r in world["reports"]:
        assert r.direct_push_succeeded == 0, r


@then("at least one agent raised a pull request by hand")
def _hand(world):
    for r in world["reports"]:
        assert r.hand_prs > 0, r


@then("every hand-raised pull request was refused and its branch kept as a lane")
def _refused(world):
    for r in world["reports"]:
        assert r.hand_prs_refused == r.hand_prs, r


@then("no open pull request was ever observed after the platform handled the event")
def _no_open(world):
    for r in world["reports"]:
        assert r.open_red_pr_observations == 0, r


@then(
    "every pull request the engine raised was green at the sha it was raised with, and merged in the same act"
)
def _engine_prs(world):
    # ChaosBackend.land() asserts a green verdict and a fast-forward before it raises; a run that
    # completed without AssertionError is the proof, and it raised at least one.
    for r in world["reports"]:
        assert r.landed > 0, r


@then(
    "every lane is landed, red with a reason, in conflict with a reason, or deleted by its own agent"
)
def _accounted(world):
    for r in world["reports"]:
        assert r.landed + r.red + r.conflict + r.deleted_by_agents == r.lanes, r
        assert r.still_open == 0, r


@then("no lane is silent")
def _no_silent(world):
    for r in world["reports"]:
        assert r.work_lost == 0, r


@then("every lane that is green on top of main has landed")
def _liveness(world):
    for r in world["reports"]:
        assert r.good_lanes_not_landed == 0, r


@then("the run finished in a bounded number of ticks")
def _bounded(world):
    for r in world["reports"]:
        assert r.ticks < TICK_BOUND, r


@then("the outcome is identical to the uninterrupted run")
def _identical(world):
    for a, b in zip(world["reports"], world["reloaded"]):
        da, db = dataclasses.asdict(a), dataclasses.asdict(b)
        da.pop("log_tail"), db.pop("log_tail")
        assert da == db
