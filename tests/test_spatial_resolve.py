"""CP6 spatial resolver tests: pure function, no I/O, BLIND on empty comet list."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPATIAL = ROOT / "lib" / "estate_spatial.py"

spec = importlib.util.spec_from_file_location("estate_spatial", str(SPATIAL))
spatial = importlib.util.module_from_spec(spec)
sys.modules["estate_spatial"] = spatial
spec.loader.exec_module(spatial)

COMETS = ["sha_left", "sha_mid", "sha_right"]


def test_leftmost_resolves_to_index_zero():
    r = spatial.resolve("the one on the left", COMETS)
    assert r == {"available": True, "sha": "sha_left", "index": 0, "rule": "leftmost"}


def test_rightmost_resolves_to_index_minus_one():
    r = spatial.resolve("the one on the right", COMETS)
    assert r == {"available": True, "sha": "sha_right", "index": 2, "rule": "rightmost"}


def test_second_from_left_resolves_to_middle():
    r = spatial.resolve("the 2nd from the left", COMETS)
    assert r["sha"] == "sha_mid" and r["index"] == 1


def test_first_from_right_resolves_to_middle():
    r = spatial.resolve("the 1st from the right", COMETS)
    assert r["sha"] == "sha_right" and r["index"] == 2


def test_third_from_right_out_of_range():
    r = spatial.resolve("the 3rd from the right", ["only_one"])
    assert r["available"] is True and r["sha"] is None
    assert "out of range" in r["error"]


def test_unrecognised_phrase_returns_named_error():
    r = spatial.resolve("the red one", COMETS)
    assert r["available"] is True and r["sha"] is None
    assert "unrecognised" in r["error"]


def test_empty_comet_list_is_blind():
    r = spatial.resolve("the one on the left", [])
    assert r["available"] is False and r["sha"] is None
    assert "no comets visible" in r["error"]


def test_empty_intent_is_honest_miss():
    r = spatial.resolve("", COMETS)
    assert r["available"] is True and r["sha"] is None
    assert "empty intent" in r["error"]


def test_plain_ordinal_resolves():
    r = spatial.resolve("the 3rd one", COMETS)
    assert r["sha"] == "sha_right" and r["index"] == 2


def test_trailing_punctuation_ignored():
    r = spatial.resolve("the one on the left.", COMETS)
    assert r["sha"] == "sha_left"


def test_verb_wrapped_phrases_resolve():
    """Voice phrases arrive wrapped: 'tell the one on the left to stop',
    'focus the 2nd from the right one'. The resolver must find the spatial
    token WITHIN the phrase, not require exact match."""
    assert (
        spatial.resolve("tell the one on the left to stop", COMETS)["sha"] == "sha_left"
    )
    assert spatial.resolve("focus the rightmost comet", COMETS)["sha"] == "sha_right"
    assert spatial.resolve("halt the 2nd from the right", COMETS)["sha"] == "sha_mid"
