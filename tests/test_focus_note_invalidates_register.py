#!/usr/bin/env python3
"""Falsifier for RC2: a claim note must invalidate the register it contradicts.

THE DEFECT, MEASURED (2026-11-08). `bin/claim-open` posts a CLAIM comment, then calls
`focus.note_claim(n)` so the write gate sees the claim immediately rather than at the next poll.
But `live_focus()` serves a 300-second cache (`FOCUS_TTL_S`), and `note_claim` recorded the note
WITHOUT touching that cache. Observed on the live register:

    note_claim recorded 7801 at 1794131288
    cached register age  25s   (TTL 300s)
    cached rows cover the claimed path: False

So the door refused an edit whose own CLAIM comment covered the file -- three times in one
session -- and the author's only recourse was to wait out a cache TTL, which reads as "the door
is broken, route around it." That is worse than a slow door: a guard that refuses valid work
teaches agents to disable it.

This test asserts the opposite: a note and a fresh read must agree.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "estate" / "memory"))

import focus  # noqa: E402


def _row(paths: str, agent: str = "pi") -> dict:
    return {"claim": "idp#1", "agent": agent, "paths": paths, "live": True}


def test_note_drops_the_cached_register(tmp_path, monkeypatch):
    """The note must make the next read refetch, not reuse a pre-claim snapshot."""
    register = tmp_path / "focus-register.json"
    noted = tmp_path / "noted.json"
    monkeypatch.setattr(focus, "focus_cache_path", lambda: str(register))
    monkeypatch.setattr(focus, "noted_claims_path", lambda: str(noted))

    # A register snapshot from BEFORE the claim: it does not carry the path.
    focus.save_json(
        str(register), {"at": focus.time.time(), "rows": [_row("other/file.py")]}
    )
    assert register.exists(), "precondition: a stale register exists"

    focus.note_claim(7801, path=str(noted))

    assert not register.exists(), (
        "note_claim left the pre-claim register in place, so the next read is stale -- "
        "this is the exact defect that refused three valid writes"
    )


def test_note_still_records_itself(tmp_path, monkeypatch):
    """Dropping the cache must not lose the note; the fix is additive, not a replacement."""
    noted = tmp_path / "noted.json"
    register = tmp_path / "focus-register.json"
    monkeypatch.setattr(focus, "focus_cache_path", lambda: str(register))
    monkeypatch.setattr(focus, "noted_claims_path", lambda: str(noted))

    focus.note_claim(7801, path=str(noted))

    recorded = focus.load_json(str(noted))
    assert "7801" in recorded, "the note itself must survive"


def test_note_tolerates_a_missing_register(tmp_path, monkeypatch):
    """A first-ever claim has no cache file; that is not an error."""
    register = tmp_path / "absent.json"
    noted = tmp_path / "noted.json"
    monkeypatch.setattr(focus, "focus_cache_path", lambda: str(register))
    monkeypatch.setattr(focus, "noted_claims_path", lambda: str(noted))

    focus.note_claim(7801, path=str(noted))  # must not raise

    assert "7801" in focus.load_json(str(noted))


def test_note_survives_an_unremovable_register(tmp_path, monkeypatch):
    """If the drop fails the note still lands -- a failed cache drop costs a delay, not the claim."""

    def boom() -> str:
        raise OSError("permission denied")

    noted = tmp_path / "noted.json"
    monkeypatch.setattr(focus, "focus_cache_path", boom)
    monkeypatch.setattr(focus, "noted_claims_path", lambda: str(noted))

    focus.note_claim(7801, path=str(noted))

    assert "7801" in focus.load_json(str(noted)), (
        "a broken cache path must not lose the note"
    )


def test_the_ttl_is_still_a_cache_and_not_a_writethrough(tmp_path, monkeypatch):
    """Guard against 'fix' by removing the cache: a fresh snapshot inside the TTL is still reused.

    The bug was that a WRITE did not invalidate the cache. It was never that the cache exists --
    it keeps the write gate off the network on every tool call, which is the whole point.
    """
    register = tmp_path / "focus-register.json"
    fresh = {"at": focus.time.time(), "rows": [_row("cached/file.py")]}
    focus.save_json(str(register), fresh)

    hit = focus.load_json(str(register))
    age = focus.time.time() - hit.get("at", 0)
    assert age < focus.FOCUS_TTL_S, "a just-written snapshot is inside the TTL"
    assert hit["rows"][0]["paths"] == "cached/file.py"
