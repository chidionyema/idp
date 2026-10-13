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
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
VOICE = (
    REPO
    / "backstage"
    / "plugins"
    / "fleetview-backend"
    / "src"
    / "fleetview_backend"
    / "voice.py"
)
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


def test_spatial_detector_ignores_bare_direction_words(voice):
    for q in (
        "how many agents are running right now",
        "is everything all right",
        "what is on top of the queue",
    ):
        assert voice._is_spatial_intent(q) is False, q


def test_a_span_of_time_is_not_a_comet(voice):
    # "in the last hour" took the spatial path, found no comets on the pod and 503'd the question.
    for q in (
        "how many calls in the last hour",
        "what failed in the last 3 days",
        "who ran the first time today",
        "what happened in the last couple of minutes",
    ):
        assert voice._is_spatial_intent(q) is False, q
    assert voice._is_spatial_intent("focus the last one") is True
    assert voice._is_spatial_intent("stop the first") is True


def _events(chunks) -> list[tuple[str, dict]]:
    import json

    out = []
    for frame in "".join(chunks).strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_stream_speaks_a_resolved_comet_as_a_delta(voice):
    # The browser only speaks `delta`; an `answer` event was resolved and then never heard.
    frames = _events(voice.stream_ask("focus the one on the left", []))
    assert frames[0][0] == "delta"
    assert "1111111" in frames[0][1]["text"]
    assert frames[-1][0] == "done" and frames[-1][1]["sha"] == "1" * 40


def test_stream_blind_river_falls_through_to_the_model(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_API_KEY_FILE", raising=False)
    v = _load(VOICE, "voice_under_test_blind_stream")
    frames = _events(v.stream_ask("the one on the left", []))
    # No comets: the spatial path steps aside, and the model path speaks for itself.
    assert "no comets visible" not in frames[0][1].get("error", "")
    assert "LITELLM_API_KEY" in frames[0][1]["error"]


def test_router_key_reads_mounted_file_each_call(tmp_path, monkeypatch):
    """In-cluster the key is a mounted file (Kyverno refuses secretKeyRef env), re-read on every
    call so a rotated key lands without a restart; the env var is only the local/dev fallback."""
    voice = _load(VOICE, "voice_router_key_under_test")
    keyfile = tmp_path / "key"
    keyfile.write_text("sk-first\n")
    monkeypatch.setenv("LITELLM_API_KEY_FILE", str(keyfile))
    monkeypatch.setenv("LITELLM_API_KEY", "sk-env")
    assert voice.router_key() == "sk-first"
    keyfile.write_text("sk-rotated\n")
    assert voice.router_key() == "sk-rotated"
    keyfile.unlink()
    assert voice.router_key() == "sk-env"
