"""Jev consensus pre-screen tests (ADR 0030 T1).

Tests collect() routing based on Jev confidence:
  high confidence (>= floor) -> single cheap vote, skip fan-out
  low confidence (< floor)  -> full 3-model fan-out
  Jev unavailable           -> BLIND, full fan-out
  non-destructive           -> no Jev call, single cheap vote

The critical behavior (skip vs fan-out) is tested by checking the length of
the result and the jev_skip flag. The number of _one_vote calls is verified
in separate integration tests that run against a real httpx mock.
"""

from __future__ import annotations

import asyncio


from sovereign.consensus import models as m


class TestCollectJevRouting:
    """Test collect() routing by directly assigning async fakes to the module."""

    def _run_collect(self, op: str, destructive: bool):
        return asyncio.run(m.collect(op, destructive))

    def test_non_destructive_skips_prescreen_returns_cheap_vote(self):
        """Non-destructive: no Jev call, returns single cheap model vote."""
        orig_prescreen = m._jev_prescreen
        called = []

        async def tracking_prescreen(op, destructive):
            called.append((op, destructive))
            return (True, 0.5)

        m._jev_prescreen = tracking_prescreen
        try:
            result = self._run_collect("echo hello", destructive=False)
            assert called == [], f"expected no prescreen call, got {called}"
            assert len(result) == 1
            cheap_model = str(m.ck.get("consensus.cheap_model"))
            assert result[0]["model"] == cheap_model
        finally:
            m._jev_prescreen = orig_prescreen

    def test_high_confidence_skips_fanout_returns_cheap_vote(self):
        """Destructive + Jev high confidence -> single cheap vote, jev_skip=True."""
        orig_prescreen = m._jev_prescreen

        async def fake_prescreen(op, destructive):
            return (False, 0.92)  # proceed=False -> skip fan-out

        m._jev_prescreen = fake_prescreen
        try:
            result = self._run_collect("echo hello", destructive=True)
            assert len(result) == 1
            assert result[0].get("jev_skip") is True
            assert result[0].get("jev_confidence") == 0.92
            cheap_model = str(m.ck.get("consensus.cheap_model"))
            assert result[0]["model"] == cheap_model
        finally:
            m._jev_prescreen = orig_prescreen

    def test_low_confidence_runs_fanout(self):
        """Destructive + Jev low confidence -> runs 3-model fan-out (len=3)."""
        orig_prescreen = m._jev_prescreen

        async def fake_prescreen(op, destructive):
            return (True, 0.3)  # proceed=True -> run fan-out

        m._jev_prescreen = fake_prescreen
        try:
            result = self._run_collect("echo hello", destructive=True)
            assert len(result) == 3, f"expected 3 fan-out votes, got {len(result)}"
            assert result[0].get("jev_skip") is not True
        finally:
            m._jev_prescreen = orig_prescreen


class TestJevPrescreenDirect:
    """Direct tests for _jev_prescreen return types (no mocking needed)."""

    def test_returns_tuple(self):
        """Always returns (bool, float) for destructive ops."""
        result = asyncio.run(m._jev_prescreen("echo hello", destructive=True))
        assert isinstance(result, tuple)
        assert len(result) == 2
        skip, confidence = result
        assert isinstance(skip, bool)
        assert isinstance(confidence, float)

    def test_non_destructive_returns_early(self):
        """Non-destructive: returns (True, 0.0) without calling Jev."""
        result = asyncio.run(m._jev_prescreen("echo hello", destructive=False))
        assert result == (True, 0.0)
