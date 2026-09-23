"""CP6 voice integration: spatial fast-path bypasses the LLM for spatial intents.

The voice service has two routes into the answer:
  - spatial_fast_path(question)  -- resolves "the one on the left" to a sha
                                    without ever calling the router
  - the LLM path                 -- everything else

These tests prove the spatial path: it returns the right envelope, falls
through to the LLM path on non-spatial questions, and never invents a sha
when the comet list is empty or the phrase is unresolvable.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
VOICE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "voice.py"
RECORDER = REPO / "bin" / "estate-deploy-recorder"


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


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
    "title": "last",
    "headRefName": "feat/last",
    "headRefOid": "2" * 40,
    "createdAt": "2026-09-22T08:00:00Z",
    "mergedAt": "2026-09-22T08:30:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}


def _stub(args):
    if args[:2] == ["pr", "list"]:
        return [PR1, PR2]
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
    raise Exception(f"unexpected gh call: {args}")


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    rec = _load(RECORDER, "rec")
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub):
        rec.write_journey(con, j)
    con.commit()
    con.close()
    return tmp_path / "estate.db"


@pytest.fixture()
def voice(db):
    return _load(VOICE, "voice_under_test")


# ----------------------------------------------------------- detection


def test_spatial_detector_recognises_left(voice):
    assert voice._is_spatial_intent("focus the one on the left") is True


def test_spatial_detector_recognises_right(voice):
    assert voice._is_spatial_intent("tell the rightmost to stop") is True


def test_spatial_detector_recognises_ordinal(voice):
    assert voice._is_spatial_intent("the 2nd from the left one") is True


def test_spatial_detector_rejects_named_intent(voice):
    assert voice._is_spatial_intent("what is sha aaaabbbb doing") is False


def test_spatial_detector_rejects_general_question(voice):
    assert voice._is_spatial_intent("how many agents are stuck") is False


# ----------------------------------------------------------- fast path


def test_fast_path_resolves_leftmost_to_oldest(voice):
    body, status = voice.spatial_fast_path("focus the one on the left")
    assert status == 200
    assert body["sha"] == "1" * 40
    assert body["rule"] == "leftmost"
    assert body["model"] == "spatial-fast-path"


def test_fast_path_resolves_rightmost_to_newest(voice):
    body, status = voice.spatial_fast_path("tell the rightmost to stop")
    assert status == 200
    assert body["sha"] == "2" * 40


def test_fast_path_named_miss_returns_200_with_error(voice):
    body, status = voice.spatial_fast_path("focus the one on the back left")
    assert status == 200
    assert body["sha"] is None
    assert "unrecognised" in body["error"]


def test_fast_path_returns_none_for_non_spatial(voice):
    """Non-spatial questions must NOT be hijacked by the spatial path; the
    LLM still gets to answer them."""
    assert voice.spatial_fast_path("how many agents are stuck") is None


def test_fast_path_blind_when_store_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    v = _load(VOICE, "voice_under_test_blind")
    body, status = v.spatial_fast_path("the one on the left")
    assert status == 503
    assert body["sha"] is None
    assert "no comets visible" in body["error"]


def test_fast_path_never_invents_sha(voice):
    """Belt and braces: try every spatial phrase and assert none returns a sha
    that isn't in the seeded comet list."""
    seeded = {"1" * 40, "2" * 40}
    for phrase in [
        "the one on the left",
        "the rightmost",
        "the 2nd from the left",
        "the red one",
        "the 99th one",
        "",
        "  ",
    ]:
        result = voice.spatial_fast_path(phrase)
        if result is None:
            continue
        body, _ = result
        if body.get("sha") is not None:
            assert body["sha"] in seeded, (
                f"phrase {phrase!r} produced sha {body['sha']!r} not in seeded"
            )


def test_fast_path_does_not_call_router(voice, monkeypatch):
    """The whole point: the fast path returns BEFORE router_key() is checked.
    With the env var explicitly empty (BLIND), the spatial path still works."""
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    body, status = voice.spatial_fast_path("the one on the left")
    assert status == 200
    assert body["sha"] == "1" * 40
