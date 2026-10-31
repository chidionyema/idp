"""Lose any ONE home and the front still answers (ADR 0037 R1/R2; founder, 2026-10-30).

"Seamless fall back lanes, never a critical service as a single point of failure." This is that
sentence as a table: for every home the front can lose, one caller sends one request and is
answered. It is the offline form of the 12:17 outage, so it runs in a second and needs no Mac, no
cluster and no GitHub.

The cell that fails today is the box being saturated while the cloud is healthy: since #7547 the
front refuses at once above LOAD_MAX and never asks the cloud, so the laptop's load alone empties
the service even with a working remote home. It is marked strict-xfail, so the fix (ticket
router-ladder-actuator) turns it into an XPASS that fails the suite until the marker is removed:
the repair cannot land unrecorded, and the defect cannot be forgotten.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "front_budget_fixture",
    ROOT / "tests" / "test_router_front_answers_inside_its_budget.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # one set of fake homes, not a tenth copy

front = _mod.front  # the fixture: a fresh front on free ports


async def _ask_body(f):
    """One request through the front: the status line and the first bytes of the body."""
    r, w = await asyncio.open_connection(*f.LISTEN)
    w.write(_mod.REQUEST)
    await w.drain()
    head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 15)
    body = await asyncio.wait_for(r.read(16), 15)
    w.close()
    return head.split(b"\r\n", 1)[0], body


def _port_of(url: str) -> int:
    return int(url.rsplit(":", 1)[1])


# what is lost, which homes stay up, and who must answer
CELLS = [
    pytest.param(set(), "cloud", id="nothing lost: the cloud is primary (#7079)"),
    pytest.param({"cloud"}, "slot", id="the cloud is lost"),
    pytest.param({"slot-a"}, "cloud", id="the active slot is lost"),
    pytest.param(
        {"cloud", "slot-a"}, "slot", id="the cloud and the active slot: the twin"
    ),
    pytest.param({"slot-a", "slot-b"}, "cloud", id="the whole laptop router is lost"),
    pytest.param(
        {"box-saturated"},
        "cloud",
        id="the laptop is saturated: it spills to the cloud, it does not shed (#7547 fixed)",
    ),
]


@pytest.mark.parametrize("lost, answered_by", CELLS)
def test_one_lost_home_does_not_lose_the_answer(front, monkeypatch, lost, answered_by):
    async def run():
        a, b = front.SLOTS
        cloud = _port_of(front.CLOUD)
        servers = []
        if "slot-a" not in lost:
            servers.append(await _mod.answering(a, b"slot"))
        if "slot-b" not in lost:
            servers.append(await _mod.answering(b, b"slot"))
        if "cloud" not in lost:
            servers.append(await _mod.answering(cloud, b"cloud"))
        if "box-saturated" in lost:
            monkeypatch.setattr(front.os, "getloadavg", lambda: (999.0, 999.0, 999.0))
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.4)  # the front probes its slots before it routes
        try:
            line, body = await _ask_body(front)
        finally:
            task.cancel()
            for srv in servers:
                srv.close()
        return line, body

    line, body = asyncio.run(run())
    assert line.startswith(b"HTTP/1.1 200"), (lost, line)
    assert body.startswith(answered_by.encode()), (lost, body)


def test_saturated_and_cloud_lost_is_refused_at_once_not_held(front, monkeypatch):
    """The spill must not turn the old shed into a hang: with the box saturated AND the only
    remote home gone, nothing can answer, so the caller is told 503 + Retry-After immediately and
    may retry (the pre-spill behaviour, kept for the one cell where no home is left)."""

    async def run():
        a, b = front.SLOTS
        servers = [
            await _mod.answering(a, b"slot"),
            await _mod.answering(b, b"slot"),
        ]  # the cloud port has no listener: the cloud is lost
        monkeypatch.setattr(front.os, "getloadavg", lambda: (999.0, 999.0, 999.0))
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.4)
        try:
            r, w = await asyncio.open_connection(*front.LISTEN)
            w.write(_mod.REQUEST)
            await w.drain()
            head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 15)
            w.close()
        finally:
            task.cancel()
            for srv in servers:
                srv.close()
        return head

    head = asyncio.run(run())
    assert head.startswith(b"HTTP/1.1 503"), head
    assert b"Retry-After: 30" in head, head


def test_saturated_with_no_remote_home_configured_is_refused(front, monkeypatch):
    """No remote home in the route at all (CLOUD turned off): the shed is unchanged."""

    async def run():
        monkeypatch.setattr(front, "CLOUD", "")
        monkeypatch.setattr(front.os, "getloadavg", lambda: (999.0, 999.0, 999.0))
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.4)
        try:
            r, w = await asyncio.open_connection(*front.LISTEN)
            w.write(_mod.REQUEST)
            await w.drain()
            head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 15)
            w.close()
        finally:
            task.cancel()
        return head

    head = asyncio.run(run())
    assert head.startswith(b"HTTP/1.1 503"), head
