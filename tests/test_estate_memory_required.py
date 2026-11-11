#!/usr/bin/env python3
"""The memory-required gate must be able to FAIL before it is trusted to pass (founder, 2026-11-10).

Founder order: "no session may ever work again without memory, machine enforced, unbreakable."

What happened on 2026-11-10, and what these tests exist to prevent recurring:
  `platform/estate/memory/local_store.py` was deleted uncommitted in a lane checkout. `door.py`
  imports it at module level, so:
    - the memory door died on import (writes "succeeded" via direct SQLite, reads were dead), and
    - `bin/estate-memory-enforce`, which imported `door` at module level, died with it --
      a traceback and exit 1 on every hook call.
  A crashed hook is indistinguishable from a permissive one, and `estate-memory-enforce` ALSO
  failed open by design on an unreachable door. The fleet therefore ran with no memory, every
  session started blank, and the founder had to repeat himself.

Each test below pins one half of the law:
  1. memory that round-trips is OK and work is allowed;
  2. memory whose door will not import is BROKEN and work is REFUSED;
  3. the enforcement hook REFUSES instead of crashing when the door is broken;
  4. the bounded repair window lets the repair through and nothing else.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REQUIRED = REPO / "bin" / "estate-memory-required"
ENFORCE = REPO / "bin" / "estate-memory-enforce"
LOCAL_STORE = REPO / "platform" / "estate" / "memory" / "local_store.py"


def _load_required():
    """Import bin/estate-memory-required by path (it has no .py extension)."""
    spec = importlib.util.spec_from_loader(
        "estate_memory_required",
        importlib.machinery.SourceFileLoader("estate_memory_required", str(REQUIRED)),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def broken_memory(monkeypatch, tmp_path):
    """Reproduce the exact 2026-11-10 failure: local_store.py is not there.

    Deleting the real file would race other tests, so the memory dir is pointed at a copy with the
    module missing. Same import, same ModuleNotFoundError, no shared state.
    """
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "door.py").write_text(
        "import local_store  # deleted: this is the 2026-11-10 bug\n"
    )
    monkeypatch.setattr(_load_required(), "MEMORY_DIR", memory_dir, raising=False)

    mod = _load_required()
    monkeypatch.setattr(mod, "MEMORY_DIR", memory_dir)
    return mod


def test_memory_that_round_trips_is_ok():
    """The healthy case: the real memory plane imports and a write is readable back."""
    r = subprocess.run(
        [sys.executable, str(REQUIRED), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    payload = json.loads(r.stdout)
    assert payload["verdict"] == "OK", payload
    assert r.returncode == 0


def test_broken_door_is_broken_not_unknown(broken_memory):
    """A door that will not import is BROKEN -- never 'unknown means pass'."""
    state, reasons = broken_memory.verdict()
    assert state == "BROKEN", reasons
    assert any("import" in r for r in reasons), reasons


def test_broken_memory_refuses_work(broken_memory, capsys):
    """Exit is non-zero, and the refusal names the repair. Silent = the defect."""
    assert broken_memory.main([]) == 1
    out = capsys.readouterr().out
    assert "may not work without working memory" in out
    assert "git restore platform/estate/memory/" in out


def test_repair_path_is_narrow(broken_memory):
    """Only the memory repair files qualify; a README does not."""
    assert broken_memory.is_repair_path(
        str(REPO / "platform" / "estate" / "memory" / "door.py")
    )
    assert broken_memory.is_repair_path(str(REPO / "bin" / "estate-memory-required"))
    assert not broken_memory.is_repair_path(str(REPO / "README.md"))
    assert not broken_memory.is_repair_path("")


def test_repair_window_opens_once_and_is_bounded(
    broken_memory, tmp_path, monkeypatch, capsys
):
    """The window opens (no fleet deadlock) and is bounded -- it is not a permanent bypass."""
    monkeypatch.setattr(broken_memory, "LEDGER", tmp_path / "required-ledger.jsonl")
    assert broken_memory.main(["--open-repair"]) == 0
    assert broken_memory.repair_window_open() is True
    assert "repair window is open" in capsys.readouterr().out

    # Bounded: a window opened beyond the limit is closed.
    marker = tmp_path / "repair-window.json"
    marker.write_text(json.dumps({"opened_at": 0}))
    assert broken_memory.repair_window_open() is False


def test_enforce_hook_refuses_instead_of_crashing():
    """The decisive one: with the door unimportable the hook must DENY, not raise.

    Before this fix it raised ModuleNotFoundError and exited 1 with no decision -- a dead gate.

    The hook resolves its memory path from its own location, with no env override (checked: there
    is no ESTATE_MEMORY_DIR), so the only honest reproduction is the real file. Break it, run the
    REAL hook, and always restore in a finally -- a test that leaves memory broken would be the
    defect it is testing for.
    """
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(REPO / "README.md")},
        "session_id": "test-broken-door",
        "transcript_path": "",
    }
    saved = LOCAL_STORE.read_bytes()
    repair_marker = Path.home() / ".estate" / "memory" / "repair-window.json"
    marker_saved = repair_marker.read_bytes() if repair_marker.exists() else None
    try:
        LOCAL_STORE.unlink()
        if marker_saved is not None:
            repair_marker.unlink()
        r = subprocess.run(
            [sys.executable, str(ENFORCE), "pre"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
    finally:
        LOCAL_STORE.write_bytes(saved)
        if marker_saved is not None:
            repair_marker.write_bytes(marker_saved)

    combined = (r.stdout or "") + (r.stderr or "")
    assert "Traceback" not in combined, (
        f"the hook crashed instead of deciding:\n{combined}"
    )
    assert "deny" in combined or "may not work" in combined, combined
    # And the store really is back, so this test cannot poison later ones.
    assert LOCAL_STORE.exists(), "the test failed to restore local_store.py"
