"""MUM-283 instrument: the founder's agent reaching its event bus is a red row, not a silence.

bin/idp-agent-event-bus grades a reachability observation for the founder-agent -> NATS edge
fail-closed. Every case here grades the program over real fixture files (no cluster), so the
estate can tell 'the founder is being heard' from 'the founder's agent cannot reach the bus and
every prompt to him is going void' -- the exact distinction that was invisible until a human read
pod logs on 2026-09-09.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin" / "idp-agent-event-bus"
FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "agent-event-bus"


def grade(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BIN), str(FIX / name)], capture_output=True, text=True
    )


def test_the_agent_reaching_the_bus_is_ok():
    p = grade("reachable.json")
    assert p.returncode == 0 and p.stdout.startswith("ok")


def test_the_agent_unable_to_reach_the_bus_is_fail():
    p = grade("unreachable.json")
    assert p.returncode == 1
    assert "UNABLE to reach the event bus" in p.stdout


def test_an_unmeasured_reach_is_fail_not_pass():
    """A reach probe that did not run or did not answer (null) is FAIL, never ok -- the founder's
    channel must be proven, and an unmeasured agent is exactly the void MUM-283 exists to red."""
    p = grade("unmeasured.json")
    assert p.returncode == 1 and "UNPROVEN" in p.stdout


def test_a_missing_observation_is_blind_not_pass():
    p = subprocess.run(
        [sys.executable, str(BIN), str(FIX / "does-not-exist.json")],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2 and p.stderr.startswith("BLIND")
