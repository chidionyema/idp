"""router-doctor names the lanes the laptop router dropped (idp#7352).

Measured 2026-10-28: 19 OKE lanes were absent from the laptop's rendered config (keys unreadable
while the cluster was down) and the doctor reported healthy because it only looked for 3 names.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "platform/estate/libexec/router-doctor.py"


def load():
    loader = importlib.machinery.SourceFileLoader("router_doctor", str(SRC))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def test_dropped_lanes_are_named():
    m = load()
    source = "- model_name: minimax\n- model_name: deepseek\n- model_name: default\n"
    runtime = "- model_name: default\n"
    assert m.dropped_lanes(source, runtime) == ["deepseek", "minimax"]


def test_nothing_dropped_is_empty():
    m = load()
    s = "- model_name: default\n"
    assert m.dropped_lanes(s, s) == []


def test_check_lanes_fails_and_names_when_lane_dropped(tmp_path, monkeypatch):
    m = load()
    (tmp_path / "config.yaml").write_text(
        "- model_name: minimax\n- model_name: claude-*\n"
    )
    (tmp_path / "config.runtime.yaml").write_text(
        "- model_name: claude-*\nefficiency_gateway\nanthropic_beta_passthrough\n"
    )
    # The truth is the LIVE runtime config (the one the running router reads), not the staged
    # shadow: measured 2026-10-31, the staged copy carried nine September lanes against the
    # router's twenty-nine, and comparing against the shadow is what made the doctor reinstall
    # the router every 120 s for a whole day. The manifest is the render's own declaration, so
    # without one the doctor falls back to comparing the declared source with the live config.
    monkeypatch.setattr(m, "STAGE", tmp_path)
    monkeypatch.setattr(m, "RUNTIME_CONFIG", tmp_path / "config.runtime.yaml")
    monkeypatch.setattr(m, "MANIFEST", tmp_path / "manifest.json")
    ok, why = m.check_lanes()
    assert ok is False and "minimax" in why


def test_check_lanes_reads_the_live_config_not_the_staged_shadow(tmp_path, monkeypatch):
    """The falsifier for the class: a shadow that disagrees with the live config must not
    produce a dropped-lane verdict. The staged copy here is missing a lane the live config
    serves; reading the shadow would name it as dropped and restart a healthy router."""
    m = load()
    (tmp_path / "config.yaml").write_text(
        "- model_name: minimax\n- model_name: claude-*\n"
    )
    (tmp_path / "config.runtime.yaml").write_text(
        "- model_name: claude-*\n- model_name: minimax\n"
        "efficiency_gateway\nanthropic_beta_passthrough\n"
    )
    # A staged shadow from September: it has no efficiency gateway at all.
    (tmp_path / "staged.runtime.yaml").write_text("- model_name: claude-*\n")
    monkeypatch.setattr(m, "STAGE", tmp_path)
    monkeypatch.setattr(m, "RUNTIME_CONFIG", tmp_path / "config.runtime.yaml")
    monkeypatch.setattr(m, "MANIFEST", tmp_path / "manifest.json")
    ok, why = m.check_lanes()
    assert ok is True, why
