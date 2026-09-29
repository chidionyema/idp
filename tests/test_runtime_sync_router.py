"""estate-runtime-sync must carry router fixes from main into the laptop router by itself.

2026-09-29: #4909's holdout trial merged while the router still ran the commit before it, because
only a hand-copied file ever updated the router's modules. The sync now copies MODULES from main,
restarts the router, and keeps the previous bytes if the router does not come back.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-runtime-sync"


def _load(tmp: Path, monkeypatch):
    monkeypatch.setenv("ESTATE_RUNTIME_TREE", str(tmp / "tree"))
    monkeypatch.setenv("ESTATE_ROUTER_DIR", str(tmp / "router"))
    loader = importlib.machinery.SourceFileLoader("estate_runtime_sync", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _estate(tmp: Path, live: str, main: str):
    (tmp / "tree/bin").mkdir(parents=True)
    (tmp / "tree/platform/llm").mkdir(parents=True)
    (tmp / "router/modules").mkdir(parents=True)
    (tmp / "tree/bin/litellm-local").write_text('MODULES="efficiency_gateway.py"\n')
    (tmp / "tree/platform/llm/efficiency_gateway.py").write_text(main)
    (tmp / "router/modules/efficiency_gateway.py").write_text(live)


def _stub(mod, monkeypatch, comes_back: bool):
    calls = {"kick": 0, "alerts": []}
    monkeypatch.setattr(
        mod, "kickstart", lambda label: calls.__setitem__("kick", calls["kick"] + 1)
    )
    monkeypatch.setattr(mod, "answers", lambda url, s: comes_back)
    monkeypatch.setattr(mod, "alert", calls["alerts"].append)
    return calls


def test_a_changed_module_reaches_the_router_and_restarts_it(tmp_path, monkeypatch):
    _estate(tmp_path, live="old", main="new")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=True)
    notes = mod.sync_router()
    assert (tmp_path / "router/modules/efficiency_gateway.py").read_text() == "new"
    assert calls["kick"] == 1 and not calls["alerts"]
    assert "restarted com.estate.litellm-local" in notes[0]


def test_an_unchanged_router_is_left_running(tmp_path, monkeypatch):
    _estate(tmp_path, live="same", main="same")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=True)
    assert mod.sync_router() == [] and calls["kick"] == 0


def test_a_router_that_does_not_come_back_gets_its_previous_modules(
    tmp_path, monkeypatch
):
    _estate(tmp_path, live="old", main="broken")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=False)
    notes = mod.sync_router()
    assert (tmp_path / "router/modules/efficiency_gateway.py").read_text() == "old"
    assert calls["kick"] == 2 and calls["alerts"]
    assert notes[0].startswith("ROUTER KEPT")
