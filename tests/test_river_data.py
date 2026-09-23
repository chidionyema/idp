"""CP2 river-data tests: scene binding is honest, deterministic, BLIND on missing ledger."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
RIVER = ROOT / "bin" / "estate-river-data"


def _load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


rec = _load(RECORDER, "estate_deploy_recorder")
river = _load(RIVER, "estate_river_data")

PR_OK = {
    "number": 3906,
    "title": "ok",
    "headRefName": "feat/ok",
    "headRefOid": "a" * 40,
    "createdAt": "2026-09-23T08:00:00Z",
    "mergedAt": "2026-09-23T08:07:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}
PR_FAIL = {
    "number": 3907,
    "title": "fail",
    "headRefName": "feat/fail",
    "headRefOid": "b" * 40,
    "createdAt": "2026-09-23T08:30:00Z",
    "mergedAt": None,
    "state": "OPEN",
    "baseRefName": "main",
}


def _stub(args):
    if args[:2] == ["pr", "list"]:
        return [PR_OK, PR_FAIL]
    if args[0] == "api" and "check-runs" in args[1]:
        if "feat/ok" in args[1]:
            return {
                "check_runs": [
                    {
                        "name": "g",
                        "conclusion": "success",
                        "completedAt": "2026-09-23T08:01:00Z",
                        "htmlUrl": "x",
                    }
                ]
            }
        return {
            "check_runs": [
                {
                    "name": "g",
                    "conclusion": "failure",
                    "completedAt": "2026-09-23T08:35:00Z",
                    "htmlUrl": "y",
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


def test_scene_is_blind_when_ledger_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    s = river.render_scene()
    assert s["available"] is False and "ledger" in s["error"]


def test_scene_names_ambient_red_when_a_comet_failed(db):
    s = river.render_scene()
    assert s["available"] is True
    assert s["ambient"]["state"] == "red"


def test_scene_comets_are_in_flight_only(db):
    s = river.render_scene()
    # PR_OK merged, PR_FAIL still open -> exactly one in-flight comet.
    assert len(s["comets"]) == 1
    assert s["comets"][0]["state"] in ("in_flight", "pending", "failed")


def test_scene_recent_is_merged_only(db):
    s = river.render_scene()
    assert all(c["state"] == "merged" for c in s["recent"])
    assert any(c["sha"] == "a" * 40 for c in s["recent"])


def test_scene_comet_has_gate_progress(db):
    s = river.render_scene()
    c = s["comets"][0]
    assert "pr_opened" in c["passed_gates"]
    # Each individual gate becomes its own stage (e.g. "check:g"), so the
    # test asserts "a failed check exists", not on a specific name.
    assert any(name.startswith("check:") for name in c["failed_gates"])


def test_scene_is_byte_identical_on_two_calls(db):
    a = river.render_scene()
    b = river.render_scene()
    assert a == b
