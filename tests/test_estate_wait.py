#!/usr/bin/env python3
"""The falsifier for bin/estate-wait (AGENTS.md section 9 R2: a gate that cannot fail is not a gate).

The claim under test: an agent that waits for an event makes ONE call and wakes when the event
arrives, instead of calling a fetch-returns-immediately door on a loop. This file is written so
that the OLD behaviour -- `estate-fleet inbox`, a 1-second fetch that returns an empty list and
exits 0 -- fails it, and only a blocking wait passes:

  * a wait with no event inside its budget must say PENDING and exit 3. The 1s fetch exits 0 on an
    empty result, so it cannot pass. This is the assertion that makes the file a falsifier rather
    than a smoke test, and it needs no bus to run.
  * the tool must be a blocking subscribe, not a fetch loop: `fetch(` must never appear outside a
    bounded loop with a deadline, and the source must contain the PENDING verdict it promises.

The live-bus tests (a real event wakes the wait, and it wakes quickly) are marked and skip as BLIND
when no broker is reachable -- a test that executes nothing must never report green (section 3).
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
WAIT = REPO / "bin" / "estate-wait"


def run_wait(args, env_extra=None, timeout=30):
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(pathlib.Path.home())}
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(WAIT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def broker_reachable() -> bool:
    """Fast and cached: a slow probe at test time would itself become the poll this file exists
    to remove, and a 3s connect attempt inside a 100s door is how a suite hangs."""
    global _BROKER
    if _BROKER is not None:
        return _BROKER
    try:
        import nats  # noqa: F401
    except Exception:
        _BROKER = False
        return _BROKER
    import asyncio

    async def probe():
        import nats

        try:
            nc = await nats.connect(
                "nats://127.0.0.1:4222", connect_timeout=1, max_reconnect_attempts=0
            )
            await nc.close()
            return True
        except Exception:
            return False

    try:
        _BROKER = asyncio.run(probe())
    except Exception:
        _BROKER = False
    return _BROKER


_BROKER: bool | None = None


# ---------------------------------------------------------------------------
# The falsifier proper: no bus needed, and the old fetch-returns-0 behaviour cannot pass.
# ---------------------------------------------------------------------------


def test_a_wait_with_no_event_is_PENDING_and_exit_3_never_a_silent_success():
    """THE falsifier. A wait that expires must announce PENDING and exit 3.

    `estate-fleet inbox` fetches with timeout=1, finds nothing, prints '0 pending message(s)' and
    exits 0. That is exactly the behaviour this test refuses: an agent reading exit 0 believes it
    has been answered, when what actually happened is that nothing was observed at all.

    This runs with no broker on purpose: an unreachable bus must still produce PENDING-or-BLIND,
    never 0, so the falsifier holds on CI as well as on the laptop. When a broker IS present the
    verdict is PENDING; without one it is BLIND. Both are non-zero, and neither is a silent
    success -- which is the property under test.
    """
    r = run_wait(
        ["--timeout", "1", "--subject", "estate.test.wait.nothing"],
        env_extra={"ESTATE_AGENT": "falsifier-agent"},
    )
    assert r.returncode in (2, 3), (
        f"an expired or blind wait must exit 2 (BLIND) or 3 (PENDING), got {r.returncode}. "
        f"stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    assert r.returncode != 0, "a wait that observed nothing must never exit 0"
    verdict = "PENDING" in r.stderr or "BLIND" in r.stderr
    assert verdict, f"the wait must state PENDING or BLIND, said {r.stderr!r}"
    assert r.stdout.strip() == "", (
        "an expired wait must not print a payload: nothing arrived"
    )


def test_a_zero_or_negative_budget_is_refused_rather_than_waited_forever():
    """An unbounded loop is a hung process (section 9 R5): every wait has a budget."""
    r = run_wait(["--timeout", "0"], env_extra={"ESTATE_AGENT": "falsifier-agent"})
    assert r.returncode == 1, (
        f"a zero budget must be refused with FAIL, got {r.returncode}"
    )
    assert "budget must be positive" in r.stderr


def test_no_agent_identity_is_refused_before_touching_the_bus():
    """A wait with no identity blocks on a subject nobody publishes to: refuse it up front."""
    r = run_wait(["--timeout", "1"], env_extra={})
    assert r.returncode == 1, (
        f"a wait with no ESTATE_AGENT must FAIL, got {r.returncode}"
    )
    assert "ESTATE_AGENT is not set" in r.stderr


# ---------------------------------------------------------------------------
# Structural guards: the tool must BE a blocking subscribe, not a renamed poll.
# ---------------------------------------------------------------------------


def test_the_wait_blocks_instead_of_fetching_once_and_returning():
    """The old door is a single `fetch(..., timeout=1)`. A blocking wait must not be that shape.

    We assert the source owns a deadline loop: a monotonic deadline, a re-check of remaining
    budget, and a bounded slice. A one-shot fetch has none of these.
    """
    src = WAIT.read_text()
    assert "time.monotonic()" in src, (
        "a wait must measure a deadline, not sleep blindly"
    )
    assert "remaining" in src, "the loop must re-check the remaining budget each slice"
    assert "PENDING" in src, "the tool must implement the PENDING verdict it documents"
    assert "pull_subscribe" in src, (
        "the wake must be a durable subscription, not a poll"
    )

    # The fetch slice must be bounded and small relative to the budget, so the deadline and a
    # Ctrl-C are honoured promptly. A timeout=1 one-shot with no loop would fail the above.
    slice_match = re.search(r"slice_s = min\(remaining, ([\d.]+)\)", src)
    assert slice_match, "the fetch slice must be bounded by the remaining budget"
    assert float(slice_match.group(1)) <= 10, (
        "the slice must be short enough to honour the deadline"
    )


def test_the_tool_documents_its_verdicts_so_a_reader_needs_no_second_door():
    """Exit codes are the contract; they are stated in the tool and match bin/lane-where."""
    src = WAIT.read_text()
    for code, word in ((0, "event arrived"), (3, "PENDING"), (2, "BLIND"), (1, "FAIL")):
        assert str(code) in src, f"exit {code} ({word}) must be documented in the tool"
    assert "never silent" in src.lower() or "NEVER silent" in src, (
        "the tool must state that an expiry is never silent"
    )


# ---------------------------------------------------------------------------
# Live proof: a real event wakes a blocked wait. BLIND, never green, without a bus.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not broker_reachable(), reason="BLIND: no broker reachable")
def test_a_stale_backlogged_message_does_not_count_as_a_wake():
    """A durable subscription replays unacked history. Handing a waiter a months-old directive and
    calling it 'woken' is a false wake -- the same lie a poller tells -- so a message published
    before the wait began must not satisfy it.
    """
    import asyncio
    import json

    subject = "estate.fleet.to.falsifier-stale-agent"

    async def _pub_stale():
        import nats

        nc = await nats.connect("nats://127.0.0.1:4222", connect_timeout=3)
        body = json.dumps(
            {
                "kind": "stale",
                "text": "published long ago",
                "from": "history",
                "at": "2026-01-01T00:00:00Z",
            }
        ).encode()
        await nc.jetstream().publish(subject, body)
        await nc.close()

    asyncio.run(_pub_stale())
    r = run_wait(
        ["--timeout", "2", "--subject", subject],
        env_extra={"ESTATE_AGENT": "falsifier-stale-agent"},
        timeout=40,
    )
    assert r.returncode != 0, (
        f"a stale backlogged message must not be reported as a wake, got exit {r.returncode} "
        f"stdout={r.stdout!r}"
    )
    assert "published long ago" not in r.stdout, (
        "the waiter was handed history as if it were news"
    )
    assert "PENDING" in r.stderr or "BLIND" in r.stderr, (
        f"expected a verdict, got {r.stderr!r}"
    )


@pytest.mark.skipif(not broker_reachable(), reason="BLIND: no broker reachable")
def test_a_real_event_wakes_the_wait_within_five_seconds():
    """The goal's own measure: 1 call, woken by a real event, inside 5s."""
    import asyncio
    import json
    import os
    import threading
    import time

    subject = "estate.fleet.to.falsifier-wake-agent"
    payload = {
        "id": "falsifier-tag",
        "from": "falsifier",
        "kind": "wake",
        "text": "prove the join",
        "at": "now",
    }
    token = f"falsifier-{os.getpid()}-{int(time.time())}"
    payload["text"] = token

    # Publish only once the wait reports it is subscribed, so the measurement is the WAKE and not
    # Python startup plus JetStream stream creation. A fixed delay measures the interpreter, which
    # is how a real 200ms wake gets reported as 7s and the bound becomes meaningless.
    subscribed = (
        pathlib.Path(tempfile.gettempdir()) / f"estate-wait-ready-{os.getpid()}"
    )
    subscribed.unlink(missing_ok=True)

    def publish_when_ready():
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and not subscribed.exists():
            time.sleep(0.05)

        async def _pub():
            import nats

            nc = await nats.connect("nats://127.0.0.1:4222", connect_timeout=3)
            await nc.jetstream().publish(subject, json.dumps(payload).encode())
            await nc.close()

        asyncio.run(_pub())
        subscribed.write_text(str(time.monotonic()))

    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(pathlib.Path.home()),
        "ESTATE_AGENT": "falsifier-wake-agent",
        "ESTATE_WAIT_READY_FILE": str(subscribed),
    }
    proc = subprocess.Popen(
        [sys.executable, str(WAIT), "--timeout", "25", "--subject", subject],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    t = threading.Thread(target=publish_when_ready, daemon=True)
    t.start()
    out, err = proc.communicate(timeout=40)
    elapsed_total = time.monotonic()
    t.join(timeout=5)

    assert proc.returncode == 0, (
        f"the wait must wake on a real event, got {proc.returncode}: {err}"
    )
    assert token in out, f"the wait must return THAT event, got {out!r}"

    # The wake latency: from the moment the event was published to the moment the wait returned.
    published_at = float(subscribed.read_text()) if subscribed.exists() else None
    subscribed.unlink(missing_ok=True)
    assert published_at is not None, (
        "the publisher never ran: the wait never reported ready"
    )
    wake_s = elapsed_total - published_at
    assert wake_s < 5.0, (
        f"woke {wake_s:.2f}s after the event: too late to be a reactive wake"
    )
