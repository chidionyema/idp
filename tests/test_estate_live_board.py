import importlib.machinery
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader(
    "elb", str(ROOT / "bin" / "estate-live-board")
)
_s = importlib.util.spec_from_loader("elb", _l)
b = importlib.util.module_from_spec(_s)
_l.exec_module(b)
T = datetime(2026, 10, 31, 14, 0, 0, tzinfo=timezone.utc)


def test_parse_claim_reads_the_estates_exact_form_and_rejects_prose():
    p = b.parse_claim(
        "CLAIM agent=pi paths=docs/**,bin/** heartbeat=2026-10-31T13:30:00Z"
    )
    assert p["agent"] == "pi" and p["paths"] == "docs/**,bin/**"
    assert b.parse_claim("I am claiming this") is None
    assert b.parse_claim("CLAIM paths=x") is None


def test_a_claim_is_live_under_two_hours_and_lapsed_after():
    cs = [
        {
            "issue_url": "u/1",
            "body": "CLAIM agent=a paths=x heartbeat=2026-10-31T13:30:00Z",
        },
        {
            "issue_url": "u/2",
            "body": "CLAIM agent=b paths=y heartbeat=2026-10-31T11:00:00Z",
        },
    ]
    out = {c["agent"]: c for c in b.claims_from(cs, T)}
    assert (
        out["a"]["live"] is True
        and out["b"]["live"] is False
        and out["b"]["age_h"] == 3.0
    )


def test_only_the_latest_heartbeat_per_claim_counts():
    cs = [
        {
            "issue_url": "u/1",
            "body": "CLAIM agent=a paths=x heartbeat=2026-10-31T09:00:00Z",
        },
        {
            "issue_url": "u/1",
            "body": "CLAIM agent=a paths=x heartbeat=2026-10-31T13:45:00Z",
        },
    ]
    out = b.claims_from(cs, T)
    assert len(out) == 1 and out[0]["live"] is True


def test_landed_buckets_by_hour_and_names_the_agent_or_says_it_has_none():
    commits = [
        {
            "commit": {
                "committer": {"date": "2026-10-31T13:30:00Z"},
                "message": "x\n\nAgent: pi",
            }
        },
        {"commit": {"committer": {"date": "2026-10-31T13:10:00Z"}, "message": "y"}},
        {"commit": {"committer": {"date": "2026-10-30T10:00:00Z"}, "message": "old"}},
    ]
    by_hour, agents = b.landed_by_hour(commits, T)
    assert by_hour[-1] == 2 and sum(by_hour) == 2
    assert agents["pi"] == 1 and agents["(no Agent trailer)"] == 2


def test_runs_last_hour_counts_results_and_ignores_older():
    rs = [
        {
            "name": "ci",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-10-31T13:50:00Z",
        },
        {
            "name": "ci",
            "status": "in_progress",
            "conclusion": None,
            "created_at": "2026-10-31T13:55:00Z",
        },
        {
            "name": "ci",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-31T10:00:00Z",
        },
    ]
    r = b.runs_last_hour(rs, T)["ci"]
    assert r == dict(total=2, success=0, failure=1, running=1, other=0)
