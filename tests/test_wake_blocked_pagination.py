"""Regression coverage for the wake-blocked full-history timeout."""
import runpy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-wake-blocked"


def load():
    ns = runpy.run_path(str(SCRIPT))
    return ns["closed_blocked_prs"], ns["closed_blocked_prs"].__globals__


def pr(n, body="", merged_at=None):
    return {"number": n, "body": body, "merged_at": merged_at}


def test_page_beyond_first_and_filter_merged():
    census, ns = load()
    calls = []

    def gh(*args, timeout):
        calls.append(args[-1])
        pages = [
            [pr(n) for n in range(1, 101)],
            [pr(101, "Blocked-by: idp#1"), pr(102, "Blocked-by: idp#2", "yes")],
        ]
        return ns["json"].dumps(pages[len(calls) - 1])

    ns["gh"] = gh
    assert [p["number"] for p in census("owner/repo")] == [101]
    assert calls[0].endswith("page=1")
    assert calls[1].endswith("page=2")


def test_incomplete_census_raises():
    census, ns = load()

    def gh(*args, timeout):
        if args[-1].endswith("page=1"):
            return ns["json"].dumps([pr(n, "Blocked-by: idp#1") for n in range(100)])
        raise RuntimeError("timed out")

    ns["gh"] = gh
    with pytest.raises(RuntimeError, match="timed out"):
        census("owner/repo")


def test_duplicate_page_is_not_complete():
    census, ns = load()
    ns["gh"] = lambda *args, **kwargs: ns["json"].dumps([pr(n) for n in range(100)])
    with pytest.raises(RuntimeError, match="shifted"):
        census("owner/repo")


def test_expired_budget_does_not_query():
    census, ns = load()
    ns["gh"] = lambda *args, **kwargs: pytest.fail("query after deadline")
    with pytest.raises(RuntimeError, match="budget"):
        census("owner/repo", budget_s=0)
