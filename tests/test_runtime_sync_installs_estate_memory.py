"""estate-runtime-sync must carry estate memory from main into every runtime by itself.

2026-10-19: the brief, the bridge and the enforcement hooks reached a runtime only when someone ran
bin/estate-memory-install by hand, so this laptop ran them from an unlanded worktree and any other
machine would have run none. The sync now runs the installer from its main tree every tick; the
installer writes only what drifted.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-runtime-sync"


def _load(tmp: Path, monkeypatch):
    monkeypatch.setenv("ESTATE_RUNTIME_TREE", str(tmp / "tree"))
    loader = importlib.machinery.SourceFileLoader("estate_runtime_sync", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _installer(tmp: Path, body: str) -> None:
    (tmp / "tree/bin").mkdir(parents=True)
    (tmp / "tree/bin/estate-memory-install").write_text(body)


def test_the_installer_runs_from_main_and_what_it_wrote_is_noted(tmp_path, monkeypatch):
    _installer(
        tmp_path,
        "print('wrote    home         copy /h/bin/estate-brief')\n"
        "print('wrote    claude-code  hook /h/settings.json')\n"
        "print('ok       cursor')\n",
    )
    mod = _load(tmp_path, monkeypatch)
    assert mod.sync_memory() == ["memory +2 (claude-code, home)"]


def test_a_converged_estate_adds_nothing_to_the_log(tmp_path, monkeypatch):
    _installer(tmp_path, "print('ok       home')\n")
    assert _load(tmp_path, monkeypatch).sync_memory() == []


def test_a_refusal_is_reported_and_never_raises(tmp_path, monkeypatch):
    _installer(tmp_path, "import sys\nprint('refused  pi  /h/x')\nsys.exit(1)\n")
    notes = _load(tmp_path, monkeypatch).sync_memory()
    assert (
        len(notes) == 1
        and notes[0].startswith("memory install exit 1")
        and "refused" in notes[0]
    )


def test_a_tree_without_the_installer_or_a_hung_one_is_survived(tmp_path, monkeypatch):
    mod = _load(tmp_path, monkeypatch)
    assert mod.sync_memory() == []

    def hang(*a, **k):
        raise subprocess.TimeoutExpired(a[0], 60)

    _installer(tmp_path, "")
    monkeypatch.setattr(mod.subprocess, "run", hang)
    assert mod.sync_memory()[0].startswith("memory install failed")


def test_the_installer_is_run_with_this_interpreter_not_the_path_one(
    tmp_path, monkeypatch
):
    # launchd's PATH is /usr/bin:/bin; the sync's own interpreter is the one known to exist.
    _installer(tmp_path, "")
    mod = _load(tmp_path, monkeypatch)
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "", ""

    def run(argv, **k):
        seen["argv"] = argv
        return R()

    monkeypatch.setattr(mod.subprocess, "run", run)
    mod.sync_memory()
    assert seen["argv"] == [
        sys.executable,
        str(tmp_path / "tree/bin/estate-memory-install"),
    ]


def test_main_runs_the_memory_step():
    assert "notes += sync_memory()" in SCRIPT.read_text()
