"""bin/voice-latency-gate's verdict: over the limit is red, no measurement is blind, never green.

The live turns are timed against the running stack (fleet-regression's voice-latency step); these
pin the arithmetic that turns those timings into an exit code.
"""

from importlib.machinery import SourceFileLoader
from pathlib import Path

gate = SourceFileLoader(
    "voice_latency_gate",
    str(Path(__file__).resolve().parents[1] / "bin" / "voice-latency-gate"),
).load_module()


def test_p95_of_ten_turns_is_the_slowest():
    assert gate.p([0.1 * i for i in range(1, 11)], 95) == 1.0


def test_inside_the_limits_is_green():
    assert gate.verdict("router", [0.4, 0.5, 0.6, 0.7, 0.9], 5) == 0


def test_a_slow_median_is_red():
    assert gate.verdict("router", [4.08, 5.38, 3.31], 3) == 1


def test_one_slow_tail_turn_is_red():
    assert gate.verdict("router", [0.3] * 9 + [1.5], 10) == 1


def test_a_turn_that_never_answered_is_red():
    assert gate.verdict("estate", [0.3, 0.3], 3) == 1


def test_nothing_measured_is_blind():
    assert gate.verdict("estate", [], 3) == gate.BLIND
