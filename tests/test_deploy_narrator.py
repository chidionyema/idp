"""The deploy-journey narrator (crew#973 CP3): templates over the ledger, no LLM.

WHAT THIS GRADES. The narrator's claim is "same input -> same bytes" -- the river
must not lie, must not interpolate, must not guess. The behaviour we lock in:

  - story mode renders the real timestamps from the journey's events;
  - failed gates are named by stage, never glossed over;
  - unknown statuses render verbatim, never as a guessed continuation;
  - a sha with no recorded journey is BLIND with a named error (not a fabricated
    story);
  - two renders of the same journey produce byte-identical text;
  - live commentary emits one line per transition, nothing between transitions;
  - the narrator never imports an LLM client.

WHAT THIS DOES NOT DO. It never calls the network; it reads through the MCP plugin's
read-only sqlite connection, exactly as a renderer would.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
NARRATOR = ROOT / "bin" / "estate-deploy-narrator"


def _load_recorder():
    loader = importlib.machinery.SourceFileLoader(
        "estate_deploy_recorder", str(RECORDER)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def _load_narrator():
    loader = importlib.machinery.SourceFileLoader(
        "estate_deploy_narrator", str(NARRATOR)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


rec = _load_recorder()
nar = _load_narrator()

SHA = "abc1234def567890"
PR = {
    "number": 3906,
    "title": "Consolidate all work into main",
    "headRefName": "consolidate/all-into-main",
    "headRefOid": SHA,
    "createdAt": "2026-09-23T08:00:00Z",
    "mergedAt": "2026-09-23T08:07:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}


def _stub_runner(args):
    if args[:2] == ["pr", "list"]:
        return [PR]
    if args[0] == "api" and "check-runs" in args[1]:
        return {
            "check_runs": [
                {
                    "name": "fast-gate",
                    "conclusion": "success",
                    "completedAt": "2026-09-23T08:01:00Z",
                    "htmlUrl": "https://example/1",
                },
                {
                    "name": "bdd",
                    "conclusion": "failure",
                    "completedAt": "2026-09-23T08:05:00Z",
                    "htmlUrl": "https://example/2",
                },
            ]
        }
    raise rec.BlindError(f"unexpected gh call: {args}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    return tmp_path / "estate.db"


def _seed(db):
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub_runner):
        rec.write_journey(con, j)
    con.commit()
    con.close()


def _write_reconcile(db, sha, status="pass", ts="2026-09-23T08:09:00Z"):
    con = rec._connect()
    con.execute(
        "DELETE FROM deploy_journey_events WHERE sha = ? AND stage = 'reconcile'",
        (sha,),
    )
    seq = con.execute(
        "SELECT COALESCE(MAX(seq), -1) + 1 FROM deploy_journey_events WHERE sha = ?",
        (sha,),
    ).fetchone()[0]
    con.execute(
        "INSERT INTO deploy_journey_events (sha, seq, stage, status, detail_json, ts)"
        " VALUES (?,?,?,?,?,?)",
        (sha, seq, "reconcile", status, json.dumps({}), ts),
    )
    con.commit()
    con.close()


# ----------------------------------------------------------- story mode


def test_story_names_real_push_time_and_real_gates(db):
    _seed(db)
    _write_reconcile(db, SHA)
    env = nar.render_story(SHA)
    assert env["available"] is True
    text = env["text"]
    assert "pushed at 08:00" in text
    assert "merged at 08:07" in text
    # The narrator names failed gates or final state, never both at length.
    assert ("bdd" in text and "failed" in text) or (
        "reconcile" in text and "pass" in text
    )


def test_story_renders_unknown_status_verbatim(db):
    """When reconcile is unknown and there are no failed gates, the narrator names
    it verbatim. (When there are failed gates, the narrator names those instead —
    the two-sentence cap means one signal at a time.)"""
    con = rec._connect()
    con.execute(
        "INSERT INTO deploy_journeys (sha, branch, pr_number, title, state,"
        " started_at, merged_at, metadata_json) VALUES (?,?,?,?,?,?,?,?)",
        (
            SHA,
            "consolidate/all-into-main",
            3906,
            "Consolidate all work into main",
            "in_flight",
            "2026-09-23T08:00:00Z",
            None,
            json.dumps({"event_count": 0}),
        ),
    )
    con.execute(
        "INSERT INTO deploy_journey_events (sha, seq, stage, status,"
        " detail_json, ts) VALUES (?,?,?,?,?,?)",
        (SHA, 0, "pr_opened", "pass", json.dumps({}), "2026-09-23T08:00:00Z"),
    )
    con.commit()
    con.close()
    _write_reconcile(db, SHA, status="unknown")
    env = nar.render_story(SHA)
    assert "reconcile: unknown" in env["text"]


def test_story_blind_when_journey_missing(db):
    _seed(db)
    env = nar.render_story("deadbeef" * 5)
    assert env["available"] is True and env["text"] is None
    assert "no journey recorded" in env["error"]


def test_story_blind_when_store_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    env = nar.render_story(SHA)
    assert env["available"] is False and "unreadable" in env["error"]


def test_story_is_byte_identical_on_two_runs(db):
    _seed(db)
    _write_reconcile(db, SHA)
    a = nar.render_story(SHA)["text"]
    b = nar.render_story(SHA)["text"]
    assert a == b and len(a) > 0


def test_story_never_uses_markdown_or_lists(db):
    _seed(db)
    _write_reconcile(db, SHA)
    text = nar.render_story(SHA)["text"]
    for marker in ("**", "##", "- ", "```"):
        assert marker not in text, (
            f"forbidden markdown marker {marker!r} in story: {text!r}"
        )
    # Two sentences max: at most one period followed by another period.
    assert text.count(". ") <= 2 or text.endswith(".") and text.count(".") <= 3


# ----------------------------------------------------------- live commentary


def test_commentary_emits_one_line_per_transition(db):
    _seed(db)
    env = nar.render_commentary(limit=5)
    assert env["available"] is True
    lines = env["lines"]
    # At least one line per event of the journey (5 events + reconcile = 6).
    assert len(lines) >= 5
    # No consecutive lines for the same stage without a status change.
    for prev, curr in zip(lines, lines[1:], strict=False):
        if prev["stage"] == curr["stage"]:
            assert prev["status"] != curr["status"], (
                f"commentary repeated stage {prev['stage']!r} with no change"
            )


def test_commentary_blind_when_store_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    env = nar.render_commentary(limit=5)
    assert env["available"] is False and env["lines"] == []


# ----------------------------------------------------------- the CLI


def test_cli_story_for_real_sha(db, capsys, monkeypatch):
    _seed(db)
    _write_reconcile(db, SHA)
    monkeypatch.setenv("ESTATE_DB", str(db))
    r = subprocess.run(
        [sys.executable, str(NARRATOR), SHA],
        capture_output=True,
        text=True,
        env={**os.environ, "ESTATE_DB": str(db)},
    )
    assert r.returncode == 0, r.stderr
    assert "pushed at 08:00" in r.stdout
    assert "bdd" in r.stdout


def test_cli_blind_when_store_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    r = subprocess.run(
        [sys.executable, str(NARRATOR), SHA],
        capture_output=True,
        text=True,
        env={**os.environ, "ESTATE_DB": str(tmp_path / "never.db")},
    )
    assert r.returncode == 2
    assert "BLIND estate-deploy-narrator:" in r.stderr


def test_narrator_never_imports_an_llm(db):
    """The narrator's import graph must not touch any LLM client. Forbidden
    imports are caught by reading the source and asserting on import lines."""
    src = NARRATOR.read_text()
    forbidden = (
        "litellm",
        "openai",
        "anthropic",
        "langchain",
        "langgraph",
        "litellm_api_key",
    )
    for name in forbidden:
        assert name not in src, f"narrator imports an LLM client: {name!r}"
