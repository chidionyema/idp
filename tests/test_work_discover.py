"""The work.discover intent: one query that finds any work in the estate, wherever it is.

The intent exists because locating work was friction: the same piece of work was in a
ticket, a lane, a salvage ref, a claim and a memory, and finding it meant a dozen
commands. These tests hold the parts that can be checked without the network: the intent's
shape, the terms it searches for, and the way it reports a source that is unavailable
(an honest "unavailable", never a silent shrink of the answer).
"""

from __future__ import annotations

import importlib.util
import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
INTENT = REPO / "platform" / "estate" / "intents" / "work.discover.yaml"
SCRIPT = REPO / "platform" / "estate" / "libexec" / "work-discover.py"


def _load():
    spec = importlib.util.spec_from_file_location("work_discover", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_intent_exists_and_is_named_after_its_file():
    data = yaml.safe_load(INTENT.read_text())
    assert data["name"] == "work.discover"
    assert data["class"] == "read"
    args = data["args"]
    assert "query" in args, "the intent must take the query as data"
    assert args["query"].get("description"), "the query argument must say what it is"
    assert data["door_s"] <= 100, "the intent must fit the estate's door"


def test_the_intent_calls_the_helper_and_not_a_shell_string():
    body = yaml.safe_load(INTENT.read_text())["steps"][0]["cmd"]
    assert "work-discover.py" in body
    assert "python3 ~/.estate/libexec/work-discover.py" in body


def test_terms_drop_stopwords_and_keep_the_rare_ones():
    mod = _load()
    assert mod.terms_of("the surface redesign of the kit") == [
        "surface",
        "redesign",
        "kit",
    ]
    assert mod.terms_of("ui") == ["ui"], "a short term is kept when it is all there is"


def test_matching_is_case_insensitive_and_names_the_terms():
    mod = _load()
    assert mod.matched(
        "Founder surfaces on the estate KIT", ["founder", "kit", "absent"]
    ) == [
        "founder",
        "kit",
    ]


def test_a_claim_is_live_only_inside_two_hours():
    mod = _load()
    fresh = {"heartbeat": mod.iso(mod.now_utc())}
    old = {"heartbeat": "2020-01-01T00:00:00Z"}
    assert mod._claim_live(fresh) is True
    assert mod._claim_live(old) is False
    assert mod._claim_live({"heartbeat": "not a time"}) is False


def test_a_broken_source_is_reported_not_hidden():
    """One source failing must not shrink the answer: it is named as unavailable."""
    mod = _load()
    payload = {
        "query": "kit",
        "terms": ["kit"],
        "elapsed_s": 1.0,
        "total_hits": 1,
        "limit": 5,
        "sources": [
            {"name": "tickets", "ok": True, "error": None, "hits": [], "seconds": 0.1},
            {
                "name": "graph",
                "ok": False,
                "error": "growmos query failed: timed out",
                "hits": [],
                "seconds": 12.0,
            },
        ],
    }
    printed = []
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.print_human(payload)
    printed = buf.getvalue()
    assert "unavailable" in printed
    assert "not searched: graph" in printed
