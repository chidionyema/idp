"""UNKNOWN is not zero, and a measurement that failed is not silence.

Measured 2026-11-28 on this host: `bin/estate-state-page --json` died with

    TypeError: 'NoneType' object is not iterable
    state_page.py, line 118, in compute   (claims = _focus_rows())

because `focus.live_focus()` returns None when the claim ledger cannot be read, and its own
docstring says so -- "or None when the ledger could not be read (unknown)". Two of the estate's
laws were broken by that one boundary:

  * section 3 / R1 (a gate that cannot fail): `bin/estate-brief` caught the exception and returned
    "", so every session started with no estate state at all and nothing anywhere said why. A
    failed measurement was rendered as "there is no state", which looks healthy.
  * section 9 principle 1 (unknown = refuse): an unknown claim count must read UNKNOWN. It must
    never be printed as `0 of 0`, because a reader cannot tell that from a measured zero.

These are the platform-side falsifiers: each one fails before the fix in
platform/estate/governance/state_page.py and names the behaviour the law demands.
"""

from __future__ import annotations

import pathlib
import sys


REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "platform" / "estate"))

from governance import state_page  # noqa: E402


def _facts(**claims) -> dict:
    """The smallest facts dict `render` accepts, with the claim block under test."""
    return {
        "ts": "2026-11-28T00:00:00Z",
        "law_gate": {
            "ok": True,
            "laws": 1,
            "failing": [],
            "warning": [],
            "audit_count": 0,
        },
        "specs": {"total": 1, "open": [], "done": ["s"]},
        "renewals": {},
        "denied_providers": [],
        "claims": claims or {"live": 0, "total": 0, "unknown": False},
        "violations": {"total": 0, "by_class": {}},
        "locked_sessions": [],
    }


# 1. The boundary: an unreadable ledger is UNKNOWN, not a crash and not zero.
def test_unreadable_claim_ledger_is_unknown_not_zero():
    counts = state_page._claim_counts(None)
    assert counts["unknown"] is True
    assert counts["live"] is None and counts["total"] is None, (
        "an unreadable ledger must not be reported as a number: %r" % (counts,)
    )


def test_a_measured_zero_is_still_a_zero():
    counts = state_page._claim_counts([])
    assert counts == {"live": 0, "total": 0, "unknown": False}


def test_a_read_ledger_counts_its_live_rows():
    rows = [{"live": True}, {"live": False}, {"live": True}]
    assert state_page._claim_counts(rows) == {"live": 2, "total": 3, "unknown": False}


def test_a_malformed_row_does_not_hide_the_rest_of_the_ledger():
    # One malformed record costs that record, not the corpus (AGENTS.md 3a).
    rows = [{"live": True}, "not-a-row", None, {"live": True}]
    assert state_page._claim_counts(rows) == {"live": 2, "total": 4, "unknown": False}


# 2. The page: UNKNOWN is rendered as UNKNOWN, and never as `0 of 0`.
def test_page_renders_unknown_claims_as_unknown():
    page = state_page.render(_facts(live=None, total=None, unknown=True))
    assert "UNKNOWN" in page, (
        "an unknown claim count was rendered as if it were measured: %r" % page
    )
    assert "0 of 0" not in page


def test_page_renders_a_measured_count_as_a_number():
    page = state_page.render(_facts(live=2, total=3, unknown=False))
    assert "2 of 3" in page
    assert "UNKNOWN" not in page


def unknown_rendered() -> int:
    """1 when an unreadable claim ledger renders as UNKNOWN, 0 when it renders as a zero.

    This is the Optimus reading the estate takes from main AFTER this lands: the measure is this
    file, run as `python3 tests/estate/test_state_page_unknown.py --optimus`.
    """
    counts = state_page._claim_counts(None)
    page = state_page.render(_facts(live=None, total=None, unknown=True))
    healthy = counts["unknown"] is True and "UNKNOWN" in page and "0 of 0" not in page
    return 1 if healthy else 0


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(f"optimus.state_page.unknown_rendered={unknown_rendered()}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
