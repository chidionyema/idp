"""estate-runtime-sync must never sit stuck on an old main without saying so.

2026-10-08/09: for ten hours every tick died -- first a hand edit in the runtime tree made `checkout`
refuse, then a missing go binary crashed the voice build before the router step -- and the only trace
was 610 tracebacks in runtime-sync.err.log. Merged router fixes never reached the live router.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-runtime-sync"


def _load(tmp: Path, monkeypatch):
    monkeypatch.setenv("ESTATE_RUNTIME_TREE", str(tmp / "tree"))
    monkeypatch.setenv("HOME", str(tmp / "home"))
    loader = importlib.machinery.SourceFileLoader("estate_runtime_sync", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    monkeypatch.setattr(mod, "STATE", tmp / "home/.estate")
    (tmp / "home/.estate").mkdir(parents=True)
    alerts: list[str] = []
    monkeypatch.setattr(mod, "alert", alerts.append)
    return mod, alerts


def _repo(path: Path) -> None:
    path.mkdir(parents=True)
    run = lambda *a: subprocess.run(
        ["git", "-C", str(path), *a], check=True, capture_output=True
    )  # noqa: E731
    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (path / "gateway.py").write_text("main\n")
    run("add", ".")
    run("commit", "-qm", "main")


def test_a_hand_edit_in_the_tree_is_put_back_kept_and_announced(tmp_path, monkeypatch):
    mod, alerts = _load(tmp_path, monkeypatch)
    _repo(tmp_path / "tree")
    (tmp_path / "tree/gateway.py").write_text("hand patch\n")
    note = mod.scrub_tree()
    assert (tmp_path / "tree/gateway.py").read_text() == "main\n"
    kept = list((tmp_path / "home/.estate").glob("runtime-sync-discarded-*.diff"))
    assert len(kept) == 1 and "+hand patch" in kept[0].read_text()
    assert note and alerts and kept[0].name in alerts[0]


def test_a_clean_tree_is_left_alone_and_nobody_is_told(tmp_path, monkeypatch):
    mod, alerts = _load(tmp_path, monkeypatch)
    _repo(tmp_path / "tree")
    assert mod.scrub_tree() == "" and alerts == []


def test_a_missing_go_is_a_failed_build_not_a_crash(tmp_path, monkeypatch):
    mod, _ = _load(tmp_path, monkeypatch)
    (tmp_path / "tree/platform/voice-router").mkdir(parents=True)
    monkeypatch.setattr(mod, "GO", str(tmp_path / "no/such/go"))
    assert mod.build_voice_router() is False


def test_go_is_found_off_launchds_path(tmp_path, monkeypatch):
    go = tmp_path / "home/.local/bin/go"
    go.parent.mkdir(parents=True)
    go.write_text("#!/bin/sh\n")
    go.chmod(0o755)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    mod, _ = _load(tmp_path, monkeypatch)
    assert mod.GO == str(go)
