"""estate-runtime-sync must carry router fixes from main into the laptop router by itself, and keep
them only if voice still answers.

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


def _estate(tmp: Path, live: str, main: str, live_cfg: str = "c", main_cfg: str = "c"):
    (tmp / "tree/bin").mkdir(parents=True)
    (tmp / "tree/llm").mkdir(parents=True)
    (tmp / "tree/llm/config.yaml").write_text(main_cfg)
    (tmp / "router").mkdir(parents=True, exist_ok=True)
    (tmp / "router/config.yaml").write_text(live_cfg)
    (tmp / "tree/platform/llm").mkdir(parents=True)
    (tmp / "router/modules").mkdir(parents=True)
    (tmp / "tree/bin/litellm-local").write_text('MODULES="efficiency_gateway.py"\n')
    (tmp / "tree/platform/llm/efficiency_gateway.py").write_text(main)
    (tmp / "router/modules/efficiency_gateway.py").write_text(live)


def _stub(mod, monkeypatch, comes_back: bool, voice=lambda cfg: True, swap_ok=True):
    # voice(cfg) says whether voice-router's /readyz answers with the router running `cfg`.
    # swap_ok=False is a new router that never answered in its slot: the live one kept serving.
    calls = {"kick": 0, "alerts": []}

    def restart_router():
        calls["kick"] += 1
        return swap_ok

    monkeypatch.setattr(mod, "restart_router", restart_router)

    def answers(url, s):
        if url == mod.VOICE_PROBE:
            return voice((mod.ROUTER / "config.yaml").read_text())
        return comes_back

    monkeypatch.setattr(mod, "answers", answers)
    monkeypatch.setattr(mod, "alert", calls["alerts"].append)
    return calls


def test_a_changed_module_reaches_the_router_and_restarts_it(tmp_path, monkeypatch):
    _estate(tmp_path, live="old", main="new")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=True)
    notes = mod.sync_router()
    assert (tmp_path / "router/modules/efficiency_gateway.py").read_text() == "new"
    assert calls["kick"] == 1 and not calls["alerts"]
    assert "deployed com.estate.litellm-local" in notes[0]


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


def test_a_lane_added_on_main_reaches_the_router_and_voice_comes_back(
    tmp_path, monkeypatch
):
    # 2026-09-29: #4962 put the `voice` lane in llm/config.yaml; the router kept its old config and
    # voice was dead for a day. The config now follows main, and voice answering is the acceptance.
    _estate(tmp_path, live="m", main="m", live_cfg="no voice", main_cfg="lanes: voice")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(
        mod,
        monkeypatch,
        comes_back=True,
        voice=lambda cfg: "voice" in cfg.split(": ")[-1],
    )
    notes = mod.sync_router()
    assert (tmp_path / "router/config.yaml").read_text() == "lanes: voice"
    assert calls["kick"] == 1 and not calls["alerts"]
    assert notes[0].endswith("voice ready")


def test_a_change_that_kills_voice_is_rolled_back(tmp_path, monkeypatch):
    _estate(
        tmp_path, live="m", main="m", live_cfg="lanes: voice", main_cfg="lanes: none"
    )
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(
        mod, monkeypatch, comes_back=True, voice=lambda cfg: cfg == "lanes: voice"
    )
    notes = mod.sync_router()
    assert (tmp_path / "router/config.yaml").read_text() == "lanes: voice"
    assert calls["kick"] == 2 and calls["alerts"]
    assert notes[0].startswith("ROUTER KEPT")


def test_the_live_router_config_is_mains_config():
    # The file the sync copies must be the one main edits: a lane on main is a lane on the laptop.
    import re

    root = SCRIPT.parent.parent
    assert re.search(
        r"^  - model_name: voice$", (root / "llm/config.yaml").read_text(), re.M
    )


def test_a_changed_watchdog_reaches_the_stage_without_restarting_the_router(
    tmp_path, monkeypatch
):
    # 2026-10-02: the guardian's fix sat on main while the staged copy restarted a slow router 12
    # times; only `litellm-local install` ever copied it.
    _estate(tmp_path, live="same", main="same")
    (tmp_path / "tree/platform/llm/watchdog.py").write_text("fixed")
    (tmp_path / "router/watchdog.py").write_text("restarts a slow router")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=True)

    out = mod.sync_router(within_s=1)

    assert (tmp_path / "router/watchdog.py").read_text() == "fixed"
    assert calls["kick"] == 0
    assert out == ["router watchdog.py staged"]


def test_a_router_that_never_answers_in_its_slot_is_never_put_into_service(
    tmp_path, monkeypatch
):
    # 2026-10-02: deploys boot the new router beside the live one (bin/litellm-local swap). One
    # that never answers is stopped by swap and the live one keeps serving -- so the front still
    # answering must not be read as acceptance, and there is nothing to restart back.
    _estate(tmp_path, live="old", main="broken")
    mod = _load(tmp_path, monkeypatch)
    calls = _stub(mod, monkeypatch, comes_back=True, swap_ok=False)
    notes = mod.sync_router()
    assert (tmp_path / "router/modules/efficiency_gateway.py").read_text() == "old"
    assert calls["kick"] == 1 and calls["alerts"]
    assert notes[0].startswith("ROUTER KEPT")


def test_a_slotted_stage_is_deployed_by_swap_not_by_kickstart(tmp_path, monkeypatch):
    _estate(tmp_path, live="same", main="same")
    (tmp_path / "router/litellm-local").write_text("case x in\n  swap) swap ;;\nesac\n")
    mod = _load(tmp_path, monkeypatch)
    ran = []
    monkeypatch.setattr(
        mod, "kickstart", lambda label: ran.append(("kickstart", label))
    )
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda argv, **_: (
            ran.append(tuple(argv[-1:]))
            or mod.subprocess.CompletedProcess(argv, 0, "", "")
        ),
    )
    assert mod.restart_router() is True
    assert ran == [("swap",)]
