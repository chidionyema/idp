"""CP6 spatial-cli tests: the full chain -- phrase -> live comets -> sha."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
CLI = ROOT / "bin" / "estate-spatial-cli"


def _load(p, name):
    loader = importlib.machinery.SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


rec = _load(RECORDER, "estate_deploy_recorder")

PR1 = {
    "number": 3901,
    "title": "first",
    "headRefName": "feat/first",
    "headRefOid": "1" * 40,
    "createdAt": "2026-09-20T08:00:00Z",
    "mergedAt": "2026-09-20T08:30:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}
PR2 = {
    "number": 3902,
    "title": "middle",
    "headRefName": "feat/middle",
    "headRefOid": "2" * 40,
    "createdAt": "2026-09-21T08:00:00Z",
    "mergedAt": None,
    "state": "OPEN",
    "baseRefName": "main",
}
PR3 = {
    "number": 3903,
    "title": "last",
    "headRefName": "feat/last",
    "headRefOid": "3" * 40,
    "createdAt": "2026-09-22T08:00:00Z",
    "mergedAt": "2026-09-22T08:30:00Z",
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
    raise rec.BlindError(args)


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


@pytest.fixture()
def cli(db):
    loader = importlib.machinery.SourceFileLoader("estate_spatial_cli", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules["estate_spatial_cli"] = m
    loader.exec_module(m)
    return m


def test_route_resolves_leftmost_to_oldest(cli, db):
    r = cli.route("the one on the left", limit=8)
    assert r["available"] is True
    # Oldest first in comet list -> PR1 (the 1s).
    assert r["sha"] == "1" * 40
    assert r["rule"] == "leftmost"


def test_route_resolves_rightmost_to_newest(cli, db):
    r = cli.route("the one on the right", limit=8)
    assert r["sha"] == "3" * 40
    assert r["rule"] == "rightmost"


def test_route_unrecognised_phrase_is_named_miss(cli, db):
    r = cli.route("the purple one", limit=8)
    assert r["available"] is True and r["sha"] is None
    assert "unrecognised" in r["error"]


def test_route_blind_when_store_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    loader = importlib.machinery.SourceFileLoader("estate_spatial_cli", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules["estate_spatial_cli"] = m
    loader.exec_module(m)
    r = m.route("the one on the left")
    assert r["available"] is False
    assert "no comets visible" in r["error"]


def test_route_never_invents_sha(cli, db):
    """The CLI must never fabricate a sha when the resolver says miss."""
    for phrase in ["the purple one", "the 99th one", "", "   "]:
        r = cli.route(phrase, limit=3)
        assert r.get("sha") is None, f"phrase {phrase!r} produced a sha: {r}"


def test_cli_subprocess(db):
    """Run the actual binary and confirm it round-trips a phrase to a sha."""
    import os

    env = {**os.environ, "ESTATE_DB": str(db)}
    r = subprocess.run(
        [sys.executable, str(CLI), "the one on the left"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["available"] is True
    assert out["sha"] in {"1" * 40, "2" * 40, "3" * 40}


def test_cli_subprocess_blind_returns_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    import os

    env = {**os.environ, "ESTATE_DB": str(tmp_path / "never.db")}
    r = subprocess.run(
        [sys.executable, str(CLI), "the one on the left"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["available"] is False
    assert "no comets visible" in out["error"]
