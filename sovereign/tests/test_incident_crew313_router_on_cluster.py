"""Incident crew#313 (2026-08-26): the router ran only in colima on the founder's Mac.

Two rules, one test file, RUNG 4 of the ladder in `~/AGENTS.md`:

1. Every model alias sovereign defaults to is one the estate router serves
   (idp platform/llm/config.yaml). `ollama` is a laptop-only lane, so a default naming
   it fails the moment LITELLM_BASE_URL is the cluster.
2. An `sb` error surfaced to chat keeps its last characters, not its first. The photo
   refusal on crew#284 CP1 read "Traceback (most recent call last): File ..." for 500
   chars and never reached the line saying the router was unreachable.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "sovereign" / "otto" / "hermes_plugin" / "__init__.py"


def _router_aliases() -> set[str]:
    cfg = yaml.safe_load((ROOT / "platform" / "llm" / "config.yaml").read_text())
    return {m["model_name"] for m in cfg["model_list"]}


def test_every_default_model_alias_is_served_by_the_estate_router() -> None:
    from sovereign import config
    from sovereign.consensus import config_keys as cck

    served = _router_aliases()
    defaults = {config._R["model.default"].value, config._R["model.vision"].value, cck.CONSENSUS_KEYS["consensus.cheap_model"][0]}
    consensus = list(config._R["model.consensus"].value)
    assert defaults <= served, defaults - served
    assert set(consensus) <= served, set(consensus) - served
    assert len(consensus) == 3 and len(set(consensus)) == 3, consensus


def test_sb_error_surfaced_to_chat_keeps_the_exception_line(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("hermes_sovereign_plugin_313", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    err_max = mod.ck.get("otto.plugin_error_max_chars")
    last = "httpx.ConnectError: [Errno 61] Connection refused (router at http://localhost:4000)"
    stderr = "Traceback (most recent call last):\n" + ("  File \"/x/y.py\", line 1, in <module>\n    import z\n" * 60) + last
    assert len(stderr) > err_max

    def fake_run(*_a, **_k):
        return subprocess.CompletedProcess(_a, 1, stdout="", stderr=stderr)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    ok, data = mod._run_sb("intake", "photo.jpg")
    assert ok is False
    assert isinstance(data, str) and len(data) <= err_max
    assert data.endswith(last), data[-120:]
