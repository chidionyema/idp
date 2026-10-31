"""The Fleet backend serves the live plan-link state, and says so when it cannot.

The backend is a THIN caller: the numbers come from the estate's own governance module, so the
page, the voice and the publisher cannot describe two different estates. A host without the
module must say "unavailable" -- an empty board and a broken board are different facts, and the
founder must be able to tell them apart.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src"
MODULE = SRC / "fleetview_backend" / "plan_links.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "fleetview_plan_links_under_test", MODULE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_backend_reads_the_canonical_numbers(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_REPO_ROOT", str(ROOT))
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    state = _load().plan_link_state()
    assert state["available"] is True, state
    assert state["error"] is None
    assert state["summary"].startswith("plan links: ")
    assert isinstance(state["rows"], list)


def test_a_host_without_the_module_says_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_REPO_ROOT", str(tmp_path))
    state = _load().plan_link_state()
    assert state["available"] is False
    assert state["error"]
    assert state["summary"] == "plan links: unavailable"
    assert state["rows"] == []


def test_the_route_is_registered_and_named():
    routes = (SRC / "fleetview_backend" / "routes.py").read_text(encoding="utf-8")
    serve = (SRC / "fleetview_backend" / "serve.py").read_text(encoding="utf-8")
    assert "PLAN_LINKS_PATH" in routes
    assert "plan_links_envelope" in routes
    assert "routes.PLAN_LINKS_PATH" in serve


def test_the_voice_may_speak_the_read_only_intent():
    voice = (SRC / "fleetview_backend" / "voice_intents.py").read_text(encoding="utf-8")
    assert '"plan.links"' in voice, (
        "plan.links is a read intent and needs no spoken confirmation"
    )


def test_the_estate_envelope_carries_the_plan_links_segment():
    """The strip, the endpoint and the voice read one envelope: the plan-link segment is part
    of it, so /fleet shows the numbers without a second fetch that could disagree."""
    routes = (SRC / "fleetview_backend" / "routes.py").read_text(encoding="utf-8")
    assert '"plan_links": _soft(plan_links.plan_link_state)' in routes, (
        "the estate envelope must carry the plan-link segment from the canonical reader"
    )
    strip = (
        ROOT
        / "backstage"
        / "packages"
        / "app"
        / "src"
        / "modules"
        / "home"
        / "EstateStrip.tsx"
    ).read_text(encoding="utf-8")
    assert "plan_links" in strip, "the strip must read the plan-link segment"
    assert "planLinks.summary" in strip, (
        "the chip must BE the canonical summary line, so the strip cannot describe a "
        "different estate than the voice"
    )


def test_the_strip_has_a_test_for_the_plan_links_segment():
    """A segment with no test is a segment that rots silently."""
    test = (
        ROOT
        / "backstage"
        / "packages"
        / "app"
        / "src"
        / "modules"
        / "home"
        / "EstateStrip.planlinks.test.tsx"
    )
    assert test.is_file(), "the plan-links strip segment must have its own test"
    body = test.read_text(encoding="utf-8")
    assert "plan links: 25 sessions, 0 violations, 46 gaps" in body
    assert "Plan links: unavailable" in body
