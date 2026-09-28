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
    r = spatial.resolve("the purple one", COMETS)
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


def test_colour_phrase_red_resolves_to_failed_comet():
    """Voice leads with colour because the river shows colour before the sha.
    'the red one' must resolve to the first comet whose status == failed."""
    comets = [
        {"sha": "s1", "status": "merged"},
        {"sha": "s2", "status": "failed"},
        {"sha": "s3", "status": "failed"},
    ]
    r = spatial.resolve("the red one", comets)
    assert r["sha"] == "s2"
    assert r["rule"] == "colour:red"


def test_colour_phrase_green_resolves_to_merged_comet():
    comets = [
        {"sha": "s1", "status": "failed"},
        {"sha": "s2", "status": "merged"},
        {"sha": "s3", "status": "merged"},
    ]
    r = spatial.resolve("the green one", comets)
    assert r["sha"] == "s2"


def test_colour_phrase_with_no_matching_comet_is_honest_miss():
    """If no comet has the requested colour the resolver must say so, never
    fall through to leftmost/rightmost."""
    comets = [{"sha": "s1", "status": "merged"}]
    r = spatial.resolve("the red one", comets)
    assert r["sha"] is None
    assert "no red comets visible" in r["error"]


def test_colour_phrase_degrades_when_caller_passes_shas_only():
    """Legacy callers pass Sequence[str]; colour resolution needs status.
    Without status the resolver must report an unrecognised intent, not
    silently invent one."""
    r = spatial.resolve("the red one", ["s1", "s2", "s3"])
    assert r["sha"] is None


def test_spelled_out_ordinal_from_left():
    """Voice users say 'second' not '2nd'. The regex must parse the word."""
    r = spatial.resolve("the second from the left", COMETS)
    assert r["sha"] == "sha_mid" and r["index"] == 1


def test_spelled_out_ordinal_from_right():
    r = spatial.resolve("the third from the right", ["a", "b", "c", "d"])
    assert r["sha"] == "b" and r["index"] == 1


def test_bare_ordinal_the_first():
    r = spatial.resolve("the first", COMETS)
    assert r["sha"] == "sha_left"


def test_bare_ordinal_the_99th_out_of_range():
    r = spatial.resolve("the 99th one", COMETS)
    assert r["sha"] is None
    assert "out of range" in r["error"]
