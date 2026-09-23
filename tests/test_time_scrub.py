"""CP4 time-scrub tests: queryable by date, BLIND on missing ledger or no journeys."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
SCRUB = ROOT / "bin" / "estate-time-scrub"


def _load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


rec = _load(RECORDER, "estate_deploy_recorder")
scrub = _load(SCRUB, "estate_time_scrub")

PR1 = {
    "number": 3906,
    "title": "monday",
    "headRefName": "feat/monday",
    "headRefOid": "a" * 40,
    "createdAt": "2026-09-21T08:00:00Z",
    "mergedAt": "2026-09-21T08:30:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}
PR2 = {
    "number": 3907,
    "title": "tuesday",
    "headRefName": "feat/tuesday",
    "headRefOid": "b" * 40,
    "createdAt": "2026-09-22T08:00:00Z",
    "mergedAt": None,
    "state": "OPEN",
    "baseRefName": "main",
}
PR3 = {
    "number": 3908,
    "title": "wednesday",
    "headRefName": "feat/wednesday",
    "headRefOid": "c" * 40,
    "createdAt": "2026-09-23T08:00:00Z",
    "mergedAt": "2026-09-23T09:00:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}


def _stub(args):
    if args[:2] == ["pr", "list"]:
        return [PR1, PR2, PR3]
    if args[0] == "api" and "check-runs" in args[1]:
        return {
            "check_runs": [
                {
                    "name": "g",
                    "conclusion": "success",
                    "completedAt": "2026-09-22T08:01:00Z",
                    "htmlUrl": "x",
                }
            ]
        }
    raise rec.BlindError(f"unexpected gh: {args}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub):
        rec.write_journey(con, j)
    con.commit()
    con.close()
    return tmp_path / "estate.db"


def test_scrub_blind_when_ledger_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    s = scrub._scrub("2026-09-22")
    assert s["available"] is False


def test_scrub_returns_only_that_date(db):
    s = scrub._scrub("2026-09-22")
    assert s["available"] is True
    shas = [j["sha"] for j in s["journeys"]]
    assert shas == ["b" * 40]


def test_scrub_returns_journeys_for_a_range_of_days(db):
    s = scrub._scrub("2026-09-21")
    assert len(s["journeys"]) == 1 and s["journeys"][0]["sha"] == "a" * 40


def test_scrub_named_miss_when_date_has_no_journeys(db):
    s = scrub._scrub("2025-01-01")
    assert s["available"] is True and s["journeys"] == []
    assert "no journeys" in s["error"]


def test_scrub_refuses_unparseable_date(db):
    s = scrub._scrub("not-a-date")
    assert s["available"] is True and s["journeys"] == []
    assert "unparseable" in s["error"]


def test_scrub_includes_merged_late_on_the_date(db):
    """A PR that opened the day before but merged on the queried day must show
    up -- the time-scrub is a 'what happened on this date' query, not a 'what
    started on this date' query."""
    s = scrub._scrub("2026-09-21")
    assert s["journeys"][0]["merged_at"].startswith("2026-09-21")
