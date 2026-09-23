"""The deploy-journey ledger: recorder and MCP reader, both ways (crew#973 CP1).

WHAT THIS GRADES, AND WHY. The Deploy River (docs/specs/2026-09-23-deploy-river.md) is
only as true as its ledger, so the claims worth grading are the honesty rules:

  - the recorder joins a PR and its check-runs into one journey with ordered stages;
  - a re-run over the same sources writes the same rows (idempotent, never doubled);
  - a check-run with no conclusion is `pending`, never `pass`;
  * gh refusing is BLIND (exit 2, named) and writes nothing -- a broken reader and an
    empty pipeline must not look the same;
  - a sha no PR claims still gets a journey whose PR stage is `unknown`, not invented;
  - the MCP reader answers `available: false` when the store is missing (BLIND), and a
    named miss (`journey: null` + error) for a sha nobody recorded.

WHAT THIS DOES NOT DO. It never calls the real gh or the network: the runner seam is
stubbed at the boundary, the same posture as the voice-on-the-bus tests.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
PLUGIN = ROOT / "mcp" / "plugins" / "deploy_journeys.py"


def _load_recorder():
    loader = importlib.machinery.SourceFileLoader(
        "estate_deploy_recorder", str(RECORDER)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def _load_plugin():
    spec = importlib.util.spec_from_file_location("deploy_journeys", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["deploy_journeys"] = module
    spec.loader.exec_module(module)
    return module


rec = _load_recorder()
plugin = _load_plugin()

SHA = "abc1234def567890"
PR = {
    "number": 3906,
    "title": "Consolidate all work into main",
    "headRefName": "consolidate/all-into-main",
    "headRefOid": SHA,
    "createdAt": "2026-09-23T08:00:00Z",
    "mergedAt": "2026-09-23T09:00:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}
CHECK_RUNS = {
    "check_runs": [
        {
            "name": "fast-gate",
            "conclusion": "success",
            "completedAt": "2026-09-23T08:01:00Z",
            "htmlUrl": "https://example/1",
        },
        {"name": "bdd", "conclusion": None, "startedAt": "2026-09-23T08:01:30Z"},
    ]
}


def _stub_runner(args: list[str]):
    if args[:2] == ["pr", "list"]:
        return [PR]
    # The recorder resolves `owner/name` once and uses it in the check-runs path (fixed
    # 2026-09-23: the call used to send the LITERAL string `repos/{repo}/...`, which gh 404s
    # for a script -- and because gh exits 0 on a 404 body, `.get("check_runs", [])` returned
    # [] and EVERY journey recorded no gates while looking like a successful read). The stub
    # answers that lookup so these tests grade the recorder, not the GitHub API.
    if args[:2] == ["repo", "view"]:
        return "chidionyema/idp"
    if args[0] == "api" and "check-runs" in args[1]:
        return CHECK_RUNS
    raise rec.BlindError(f"unexpected gh call: {args}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    return tmp_path / "estate.db"


# --------------------------------------------------------------------- the recorder


def test_recorder_joins_pr_and_gates_into_one_journey(db):
    journeys = rec.run(None, 25, runner=_stub_runner)
    assert len(journeys) == 1
    j = journeys[0]
    assert j["sha"] == SHA and j["state"] == "merged" and j["pr_number"] == 3906
    stages = [e["stage"] for e in j["events"]]
    assert (
        stages[0] == "pr_opened" and "check:fast-gate" in stages and "merged" in stages
    )
    # A gate with no conclusion is pending, never pass -- the river must not lie green.
    bdd = next(e for e in j["events"] if e["stage"] == "check:bdd")
    assert bdd["status"] == "pending"


def test_recorder_is_idempotent(db):
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub_runner):
        rec.write_journey(con, j)
    con.commit()
    first = con.execute("SELECT COUNT(*) FROM deploy_journey_events").fetchone()[0]
    for j in rec.run(None, 25, runner=_stub_runner):
        rec.write_journey(con, j)
    con.commit()
    assert (
        con.execute("SELECT COUNT(*) FROM deploy_journey_events").fetchone()[0] == first
    )
    assert con.execute("SELECT COUNT(*) FROM deploy_journeys").fetchone()[0] == 1


def test_recorder_blind_writes_nothing(db):
    def refusing(args):
        raise rec.BlindError("gh pr refused: not authed")

    with pytest.raises(rec.BlindError):
        rec.run(None, 25, runner=refusing)


def test_recorder_unclaimed_sha_gets_unknown_pr_stage(db):
    j = rec.lone_journey("deadbeef" * 5)
    assert j["events"][0]["stage"] == "pr_opened"
    assert j["events"][0]["status"] == "unknown"


def test_recorder_flux_events_land_as_cluster_stages(db, tmp_path, monkeypatch):
    feed = tmp_path / "flux.jsonl"
    feed.write_text(
        json.dumps(
            {
                "sha": SHA,
                "stage": "reconcile",
                "status": "pass",
                "ts": "2026-09-23T09:02:00Z",
            }
        )
        + "\n"
    )
    monkeypatch.setenv("FLUX_EVENTS_PATH", str(feed))
    j = rec.run(None, 25, runner=_stub_runner)[0]
    recon = next(e for e in j["events"] if e["stage"] == "reconcile")
    assert recon["status"] == "pass"


# --------------------------------------------------------------------- the MCP reader


def _seed(db):
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub_runner):
        rec.write_journey(con, j)
    con.commit()
    con.close()


def test_plugin_lists_and_fetches_the_journey(db):
    _seed(db)
    env = plugin.list_deploy_journeys()
    assert env["available"] is True and env["error"] is None
    assert env["journeys"][0]["sha"] == SHA
    one = plugin.get_deploy_journey(SHA[:7])  # abbreviated sha resolves
    assert one["journey"]["pr_number"] == 3906
    seqs = [e["seq"] for e in one["journey"]["events"]]
    assert seqs == sorted(seqs)  # the road in order; a renderer never sorts


def test_plugin_names_a_miss(db):
    _seed(db)
    env = plugin.get_deploy_journey("0000000")
    assert env["available"] is True and env["journey"] is None
    assert "no journey recorded" in env["error"]


def test_plugin_blind_when_the_store_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never-created.db"))
    env = plugin.list_deploy_journeys()
    assert env["available"] is False and "unreadable" in env["error"]


def test_plugin_refuses_an_empty_sha(db):
    _seed(db)
    env = plugin.get_deploy_journey("  ")
    assert env["error"] == "get_deploy_journey needs a sha"
