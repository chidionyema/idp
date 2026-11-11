"""The greenlane's verdict must reach a waiter, and only when the verdict changes.

bin/estate-wait blocks on the bus so an agent stops polling. That only works if something
publishes: `github.report()` is the one funnel every lane verdict passes through, so it is the
only correct place for the producer. This falsifier holds both halves of the contract that make
it safe to put there:

  1. a verdict is ANNOUNCED -- otherwise the waiter blocks forever and the agent polls anyway;
  2. the same verdict is announced ONCE -- otherwise a lane sitting pending for an hour fills the
     stream with identical events and the "it is not polling" claim becomes false in the broker.

Both are proven without a live broker: the publish is captured, not sent, so the test is honest
on CI and cannot pass because of a broker that happens to be up.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from greenlane import github as gh  # noqa: E402


class Captured:
    """Captures what _announce would publish, without touching the bus."""

    def __init__(self):
        self.sent = []


@pytest.fixture()
def reporter(monkeypatch):
    """A GitHub backend whose status write and broker publish are both captured."""
    from greenlane.github import GitHubBackend

    inst = GitHubBackend.__new__(GitHubBackend)  # no network, no token, no cluster
    inst.run_url = "https://example.invalid/run/1"
    written = []
    inst._status = lambda sha, fields: written.append((sha, fields))

    captured = Captured()
    monkeypatch.setattr(gh, "asyncio", gh.asyncio)  # keep the real module reference

    def fake_run(coro):
        # Close the coroutine we never await so nothing warns, then record its intent.
        coro.close()
        captured.sent.append(True)

    monkeypatch.setattr(gh.asyncio, "run", fake_run)
    inst._captured = captured
    inst._written = written
    inst._announced = set()
    return inst


def test_a_lane_verdict_is_announced_so_a_waiter_can_wake(reporter):
    reporter.report("lane/thing", "abc123", "landed", "green on main")
    assert len(reporter._captured.sent) == 1, (
        "a landing published nothing: a waiter blocked on the bus would never wake"
    )


def test_the_same_verdict_is_announced_once_not_every_tick(reporter):
    for _ in range(5):
        reporter.report("lane/thing", "abc123", "pending", "still testing")
    assert len(reporter._captured.sent) == 1, (
        "the same verdict was published again: the stream fills with identical events"
    )


def test_a_changed_verdict_is_announced_again(reporter):
    reporter.report("lane/thing", "abc123", "pending", "still testing")
    reporter.report("lane/thing", "abc123", "landed", "green on main")
    assert len(reporter._captured.sent) == 2, (
        "the verdict changed and the waiter was told nothing: the poll moved, it did not go away"
    )


def test_a_dead_bus_does_not_fail_the_landing(reporter, monkeypatch):
    def boom(coro):
        coro.close()
        raise OSError("nats: connection refused")

    monkeypatch.setattr(gh.asyncio, "run", boom)
    reporter.report("lane/thing", "abc123", "landed", "green on main")  # must not raise


def test_the_producer_publishes_on_the_subject_the_waiter_subscribes_to():
    source = (REPO / "greenlane" / "github.py").read_text()
    assert "estate.lane." in source, "the producer does not name a lane subject"
    assert "estate.fleet.broadcast" in source, (
        "the producer does not reach a waiter subscribed to the fleet broadcast"
    )
    wait = (REPO / "bin" / "estate-wait").read_text()
    assert "estate.fleet.broadcast" in wait, (
        "the waiter and the producer no longer share a subject: the wake can never fire"
    )
