"""A cache stamped in the future must never read as fresh.

MEASURED DEFECT (2026-11-11). The active-focus register was stamped
``2026-11-11T10:13:15Z`` while the machine clock read ``09:00:15Z`` -- a
73-minute skew. ``live_focus`` tested freshness as

    now - hit.get("at", 0) < FOCUS_TTL_S

so ``now - at`` was ``-4380``, which is smaller than any TTL, and the register
was treated as fresh **forever**. The consequence was not cosmetic: the focus
gate compares a write's path against the claims in that register, so once the
register froze, every claim opened after it became invisible. ``claim-open``
printed ``ok #7943 as pi (19 paths)``, GitHub showed the claim comment with a
live heartbeat, and the gate still refused the write with "No active focus for
this change" -- and would have gone on refusing forever, because the cache
never expired.

These tests pin the rule at the unit that enforces it. ``_is_fresh`` is the
single decision both caches use, so a fix here covers the focus register and
the issue-state cache together rather than teaching two call sites the same
lesson twice.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_FOCUS_PY = REPO_ROOT / "platform" / "estate" / "memory" / "focus.py"


def _load_focus():
    """Import focus.py by path: `platform` collides with Python's stdlib package name."""
    spec = importlib.util.spec_from_file_location("estate_focus", _FOCUS_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


focus = _load_focus()

NOW = 1_800_000_000.0
TTL = 300.0


def test_a_future_stamp_is_not_fresh() -> None:
    """The defect itself: a stamp 4380s ahead must read as expired, not fresh."""
    assert focus._is_fresh(NOW + 4380, NOW, TTL) is False


def test_the_naive_test_would_have_accepted_it() -> None:
    """Prove the falsifier bites on the old expression, so this is not a tautology."""
    stamp = NOW + 4380
    assert (NOW - stamp) < TTL, (
        "the naive `now - stamp < ttl` test now rejects a future stamp; this test is "
        "documenting a defect that no longer exists and should be deleted, not weakened"
    )


def test_a_recent_past_stamp_is_fresh() -> None:
    """The happy path must still work, or we have replaced a freeze with a permanent miss."""
    assert focus._is_fresh(NOW - 10, NOW, TTL) is True


def test_a_stamp_older_than_ttl_is_not_fresh() -> None:
    assert focus._is_fresh(NOW - (TTL + 1), NOW, TTL) is False


def test_a_stamp_exactly_at_ttl_is_not_fresh() -> None:
    """Boundary: the TTL is a half-open interval, so exactly-ttl has expired."""
    assert focus._is_fresh(NOW - TTL, NOW, TTL) is False


def test_a_missing_stamp_is_not_fresh() -> None:
    assert focus._is_fresh(0, NOW, TTL) is False
    assert focus._is_fresh(None, NOW, TTL) is False


def test_a_malformed_stamp_is_not_fresh() -> None:
    """A corrupt cache must re-read, not crash the gate that is trying to protect a write."""
    assert focus._is_fresh("not-a-number", NOW, TTL) is False


@pytest.mark.parametrize("offset", [1, 300, 4380, 86_400])
def test_live_focus_ignores_a_future_stamped_cache(tmp_path: Path, offset: int) -> None:
    """End to end: a future-stamped register must not be returned as the live answer.

    The gate must fall through to the ledger (here: an unreadable/absent one), never
    serve the frozen rows. Returning them is exactly the freeze this fixes.
    """
    cache = tmp_path / "focus-register.json"
    cache.write_text(
        json.dumps({"at": time.time() + offset, "rows": [{"claim": "idp#1"}]}),
        encoding="utf-8",
    )
    rows = focus.live_focus(path=str(cache))
    assert rows != [{"claim": "idp#1"}], (
        "live_focus served a future-stamped cache as the live register; the focus gate "
        "will refuse writes against claims that can never refresh"
    )


def test_live_focus_still_serves_a_fresh_cache(tmp_path: Path) -> None:
    """A genuinely fresh cache must still short-circuit, or every write calls gh."""
    cache = tmp_path / "focus-register.json"
    cache.write_text(
        json.dumps({"at": time.time() - 5, "rows": [{"claim": "idp#2"}]}),
        encoding="utf-8",
    )
    assert focus.live_focus(path=str(cache)) == [{"claim": "idp#2"}]
