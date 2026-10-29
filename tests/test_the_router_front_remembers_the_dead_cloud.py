"""The router's front must not re-arm a cloud that has already been proved dead.

WHAT THIS GRADES. `platform/llm/front.py` claims:
  * the cloud cooldown -- the front's knowledge that the cloud cannot answer -- SURVIVES a
    restart of the front, so a restarted front does not hand the dead cloud to the first caller
    again;
  * one dead-cloud attempt is bounded inside the caller's budget, so a caller who arrives right
    after a restart is answered by the laptop instead of stalling.

WHY (2026-10-29). Two measured defects, both on this machine:
  * `CLOUD_DOWN_UNTIL` was an in-memory module global. `mark_cloud_down()` set it, but a front
    RESTART re-imported the module and the cooldown was gone, so the route was
    `[CLOUD] + healthy + sick` again -- the dead cloud first again. The front's own log printed
    `front: the cloud failed to answer (N in a row); the laptop answers for 600s` over and over,
    and every restart re-armed the cloud that had just been proved dead.
  * `ANSWER_TIMEOUT = 120.0` was the whole time one dead-cloud attempt could take. The caller's
    budget here is 60 s, so even the FIRST attempt after a restart could not fit inside it.

THE ORDER IS NOT WHAT THIS GRADES. A sibling session fixed the ordering (a cloud in cooldown is
tried last) in commit 7e0b96914 on branch lane/front-dead-cloud-last. This file grades the two
defects that fix did not touch: the restart reset, and the bound.

THE CLOUD IS STILL THE DEFAULT ROUTE. The founder's 2026-10-26 ruling stands: the cloud is the
default and the laptop is the fallback. These tests grade the FAILURE path -- a bound and a
remembered cooldown -- not a demotion of the cloud. A cloud that answers is still first.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import socket
import time

import pytest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "front.py"

# The caller's budget. The front must answer inside it, from a cold start, even when the cloud
# cannot answer at all.
CALLER_BUDGET_S = 60.0


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def front(tmp_path, monkeypatch):
    mod = _load("router_front_cooldown")
    monkeypatch.setattr(mod, "SLOTS", (free_port(), free_port()))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", free_port()))
    monkeypatch.setattr(mod, "CLOUD", "https://cloud.invalid")
    monkeypatch.setattr(mod, "CLOUD_DOWN_S", 60.0)
    monkeypatch.setattr(mod, "CLOUD_DOWN_MAX_S", 600.0)
    # This front's cooldown lives in its OWN directory, never in the estate's live state.
    monkeypatch.setenv("ESTATE_ROUTER_CLOUD_STATE", str(tmp_path / "cloud-down"))
    return mod


def _state_of(front) -> pathlib.Path:
    return front.cloud_state_path()


def test_the_cloud_cooldown_survives_a_restart(front) -> None:
    """KNOWN-BAD (pre-fix): a restart re-armed the dead cloud.

    Falsifier: with an in-memory-only cooldown, `CLOUD_DOWN_UNTIL` is 0.0 in the fresh module
    and `restore_cloud_cooldown()` has nothing to restore -- the front hands the dead cloud to
    the first caller again.
    """
    front.mark_cloud_down()
    assert front.CLOUD_DOWN_UNTIL > 0, (
        "the cooldown was not established in the first place"
    )

    # A RESTART: a fresh import of the module, the way a restarted front reads it.
    restarted = _load("router_front_cooldown_after_restart")
    assert restarted.CLOUD_DOWN_UNTIL == 0.0, "a fresh module starts with no cooldown"

    restarted.restore_cloud_cooldown()

    assert restarted.CLOUD_DOWN_UNTIL > 0, (
        "the restart forgot the cloud was dead: the first caller is handed it again"
    )
    assert restarted.CLOUD_FAILURES >= 1, "the restart forgot how many times it failed"


def test_the_restarted_front_does_not_put_the_dead_cloud_first(front) -> None:
    """A restarted front passes the dead cloud over instead of trying it first."""
    front.mark_cloud_down()
    restarted = _load("router_front_cooldown_routes")
    restarted.restore_cloud_cooldown()

    route = restarted.route()
    assert route[-1] == restarted.CLOUD, (
        f"the dead cloud must be tried LAST, not first: {route}"
    )


def test_a_dead_cloud_attempt_is_bounded_inside_the_caller_budget(front) -> None:
    """ONE dead-cloud attempt must fit inside the caller's budget.

    Falsifier: with `ANSWER_TIMEOUT = 120.0` used for the cloud leg, a single attempt could
    take twice the caller's 60 s budget, so a caller arriving right after a restart could not
    be answered at all.
    """
    assert front.cloud_answer_timeout() < CALLER_BUDGET_S, (
        f"one cloud attempt may take {front.cloud_answer_timeout()}s, "
        f"but the caller waits {CALLER_BUDGET_S:.0f}s"
    )
    assert front.cloud_answer_timeout() > 0
    # The cloud's budget is always inside the laptop's: a slot that is slow is slow but real.
    assert front.cloud_answer_timeout() <= front.ANSWER_TIMEOUT
    # And with the production ANSWER_TIMEOUT, inside the caller's budget.
    assert front.CLOUD_ANSWER_TIMEOUT_MAX <= CALLER_BUDGET_S


def test_the_cloud_is_still_the_default_route_when_it_answers(front) -> None:
    """The founder's 2026-10-26 ruling stands: a cloud that answers is tried FIRST.

    This is the check that the fix bounds the FAILURE path without demoting the cloud.
    """
    front.CLOUD_DOWN_UNTIL = 0.0
    front.CLOUD_FAILURES = 0
    route = front.route()
    assert route[0] == front.CLOUD, f"the cloud must be the default route: {route}"


def test_a_cloud_that_answers_clears_the_remembered_cooldown(front) -> None:
    """The remembered cooldown must not permanently sideline a cloud that came back.

    A state file that is never cleared would be a cloud that is never tried again.
    """
    front.mark_cloud_down()
    assert _state_of(front).exists(), "the cooldown was not remembered"

    front.mark_cloud_up()

    assert not _state_of(front).exists(), (
        "the cloud answered but its cooldown was kept: the cloud is now never tried again"
    )
    assert front.CLOUD_DOWN_UNTIL == 0.0
    assert front.CLOUD_FAILURES == 0


def test_a_corrupt_state_file_does_not_stop_the_router(front) -> None:
    """A state file that cannot be read means NO cooldown -- not a crash.

    A bad file must never be the reason the router stops serving.
    """
    front.cloud_state_path().write_text("{not json at all", encoding="utf-8")
    deadline, failures = front._cloud_state_read()
    assert deadline == 0.0
    assert failures == 0

    front.restore_cloud_cooldown()  # must not raise
    assert front.CLOUD_DOWN_UNTIL == 0.0


def test_a_missing_state_file_does_not_stop_the_router(front) -> None:
    """First boot: no state file, no cooldown, the cloud is tried."""
    assert not front.cloud_state_path().exists()
    front.restore_cloud_cooldown()
    assert front.CLOUD_DOWN_UNTIL == 0.0
    assert front.route()[0] == front.CLOUD


def test_the_state_file_is_written_atomically(front) -> None:
    """A kill mid-write must not leave a half-written file for the next boot."""
    front.mark_cloud_down()
    state = front.cloud_state_path()
    # The temp file is gone: the write was a rename, not a truncate-in-place.
    leftovers = list(state.parent.glob(state.name + "*"))
    assert leftovers == [state], f"a temp file was left behind: {leftovers}"
    json.loads(state.read_text(encoding="utf-8"))  # it is one whole record


def test_the_cooldown_expires_so_the_cloud_is_tried_again(front) -> None:
    """A cooldown that never expires would be a cloud that is never tried again."""
    front.mark_cloud_down()
    # A deadline in the past: the cooldown is over.
    front._cloud_state_write(time.time() - 1.0, 1)
    restarted = _load("router_front_cooldown_expired")
    restarted.restore_cloud_cooldown()
    assert restarted.CLOUD_DOWN_UNTIL == 0.0, "an expired cooldown must not linger"
    assert restarted.route()[0] == restarted.CLOUD
