"""[#6543] a focus fact whose claim has closed is a ghost: the brief drops it, and says so."""

import importlib.machinery
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF = os.path.join(ROOT, "bin", "estate-brief")


def _script():
    loader = importlib.machinery.SourceFileLoader("estate_brief", BRIEF)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mod():
    return _script()


def fact(text):
    return {"text": text}


def test_a_closed_claim_focus_fact_is_dropped(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "claim_state", lambda n, p, c, cp: "CLOSED")
    items = [fact("ACTIVE FOCUS claim idp6525: lane verdicts"), fact("unrelated fact")]
    kept, dropped = mod.drop_stale_focus(items, cache_path=str(tmp_path / "c.json"))
    assert [i["text"] for i in kept] == ["unrelated fact"]
    assert len(dropped) == 1


def test_an_open_or_unknown_claim_keeps_the_fact(mod, tmp_path, monkeypatch):
    states = iter(["OPEN", None])
    monkeypatch.setattr(mod, "claim_state", lambda n, p, c, cp: next(states))
    items = [
        fact("ACTIVE FOCUS claim idp6543: gap analysis"),
        fact("ACTIVE FOCUS claim idp9999: unreachable"),
    ]
    kept, dropped = mod.drop_stale_focus(items, cache_path=str(tmp_path / "c.json"))
    assert len(kept) == 2 and not dropped


def test_a_fact_without_the_marker_is_never_touched(mod, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        mod, "claim_state", lambda n, p, c, cp: calls.append(n) or "CLOSED"
    )
    items = [
        fact("ACTIVE FOCUS was discussed"),
        fact("ACTIVE FOCUS claimless"),
        fact("x"),
    ]
    kept, dropped = mod.drop_stale_focus(items, cache_path=str(tmp_path / "c.json"))
    assert kept == items and not dropped and not calls


def test_the_marker_parses_bare_hashed_and_prefixed_claims(mod, tmp_path, monkeypatch):
    seen = {}

    def spy(n, p, c, cp):
        seen[(p.lower(), n)] = "CLOSED"
        return "OPEN"

    monkeypatch.setattr(mod, "claim_state", spy)
    mod.drop_stale_focus(
        [
            fact("ACTIVE FOCUS claim idp6525: a"),
            fact("ACTIVE FOCUS claim #6525: b"),
            fact("ACTIVE FOCUS claim 6525: c"),
        ],
        cache_path=str(tmp_path / "c.json"),
    )
    assert ("idp", 6525) in seen and ("", 6525) in seen


def test_the_state_lookup_is_cached_for_the_ttl(mod, tmp_path, monkeypatch):
    calls = []

    def fake_run(*a, **k):
        calls.append(1)

        class R:
            returncode = 0
            stdout = "CLOSED\n"

        return R()

    monkeypatch.setattr(mod.focus.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(mod.focus.subprocess, "run", fake_run)
    cache_path = str(tmp_path / "c.json")
    assert mod.claim_state(6525, "idp", {}, cache_path) == "CLOSED"
    assert mod.claim_state(6525, "idp", {}, cache_path) == "CLOSED"
    assert len(calls) == 1  # second answer came from the cache, not the network
    assert mod.focus.load_json(cache_path)["6525"]["state"] == "CLOSED"


def test_a_stalled_or_missing_gh_fails_open(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod.focus.shutil, "which", lambda name: "/usr/bin/gh")

    def stall(*a, **k):
        raise mod.focus.subprocess.TimeoutExpired(cmd="gh", timeout=2)

    monkeypatch.setattr(mod.focus.subprocess, "run", stall)
    assert mod.claim_state(6525, "idp", {}, str(tmp_path / "c.json")) is None
    monkeypatch.setattr(mod.focus.shutil, "which", lambda name: None)
    assert mod.claim_state(6525, "idp", {}, str(tmp_path / "c2.json")) is None


def test_an_unknown_repo_prefix_fails_open(mod, tmp_path, monkeypatch):
    monkeypatch.setattr(mod.focus.shutil, "which", lambda name: "/usr/bin/gh")
    assert mod.claim_state(7, "other", {}, str(tmp_path / "c.json")) is None


def test_dropping_says_so_once_on_stderr(mod, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(mod, "claim_state", lambda n, p, c, cp: "CLOSED")
    mod.drop_stale_focus(
        [fact("ACTIVE FOCUS claim idp6525: a")], cache_path=str(tmp_path / "c.json")
    )
    err = capsys.readouterr().err
    assert "dropped 1 stale focus fact" in err and "idp6525" in err
