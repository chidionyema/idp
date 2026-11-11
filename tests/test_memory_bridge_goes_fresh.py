#!/usr/bin/env python3
"""A bridge that lives for hours must not serve the code it imported at start.

Measured 2026-11-10: the estate memory door on disk was repaired and proved answering
(`written: true, rung: local-primary`), while nine `estate-memory-mcp` processes aged 2.5 to 8.5
hours went on returning `URLError ... EOF` to every `remember`. The repair was correct and reached
nobody, because `door` is a module imported once when the bridge starts and the runtime keeps one
bridge per session alive for the whole session.

That is AGENTS.md section 9 R6 (the recovery path must not depend on what it recovers) in its
process-shaped form: a fix that requires every running process to restart is not a fix that lands.

The fix under test is `_fresh_door()` in `bin/estate-memory-mcp`: the door is re-imported from
its file when, and only when, that file's mtime changes. These tests prove the reload reaches the
real dispatch path (`Bridge.forward`), that it does NOT happen when the file is untouched (so a
live session does not pay an import per call), and that a broken door file cannot take the
session down with it.
"""

from __future__ import annotations

import importlib.machinery
import os
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BRIDGE = REPO / "bin" / "estate-memory-mcp"


def _load_bridge():
    """Load the extensionless bridge as a module, the estate's own test idiom."""
    loader = importlib.machinery.SourceFileLoader(
        "estate_memory_mcp_under_test", str(BRIDGE)
    )
    module = types.ModuleType(loader.name)
    module.__file__ = str(BRIDGE)
    loader.exec_module(module)
    return module


def _write_door(path: Path, stamp: str) -> None:
    """Write a door whose post() answers with its own STAMP, in the door's real (body, err) shape."""
    path.write_text(
        f"STAMP = '{stamp}'\n\n\n"
        "def post(message, secret, timeout):\n"
        "    return {'result': {'served_by': STAMP}}, ''\n"
    )


@pytest.fixture()
def bridge(monkeypatch, tmp_path):
    """A bridge module whose `door` is a throwaway module with a real file on disk."""
    module = _load_bridge()

    door_dir = tmp_path / "doorhome"
    door_dir.mkdir()
    door_path = door_dir / "door.py"
    _write_door(door_path, "original")

    fake = types.ModuleType("door_under_test")
    fake.__file__ = str(door_path)
    sys.modules["door_under_test"] = fake
    importlib.machinery.SourceFileLoader("door_under_test", str(door_path)).exec_module(
        fake
    )

    module.door = fake
    module._DOOR_STAMP = None
    return module, door_path


def _rewrite(path: Path, stamp: str) -> None:
    """Change the door on disk the way a repair does, and force a distinct mtime."""
    _write_door(path, stamp)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


def test_a_repaired_door_reaches_an_already_running_bridge(bridge):
    """The whole point: the process that was already alive sees the new code, through forward()."""
    module, door_path = bridge
    instance = module.Bridge()
    instance.secret = "test-secret"

    first = instance.forward(1, {"jsonrpc": "2.0", "id": 1})["result"]
    assert first["served_by"] == "original", "the first call must serve what is loaded"

    _rewrite(door_path, "repaired")

    second = instance.forward(2, {"jsonrpc": "2.0", "id": 2})["result"]
    assert second["served_by"] == "repaired", (
        "a door repaired on disk must reach a bridge that started before the repair; "
        "this is the defect that made nine live sessions keep answering URLError EOF"
    )


def test_an_untouched_door_is_not_reloaded_on_every_call(bridge):
    """A live session must not pay a re-import per tool call."""
    module, _door_path = bridge

    module._fresh_door()
    loaded = module.door
    assert module._fresh_door() is loaded
    assert module._fresh_door() is loaded


def test_a_half_written_door_keeps_the_session_alive(bridge):
    """A broken file on disk must not take every memory tool down with it."""
    module, door_path = bridge

    module._fresh_door()
    _rewrite(door_path, "broken")
    door_path.write_text("STAMP = (\n")  # syntactically invalid Python

    served = module._fresh_door()
    outcome, _err = served.post({}, "", 1)
    assert outcome["result"]["served_by"] in {"original", "broken"}, (
        "a door that cannot be re-imported must fall back to the one already loaded"
    )
    assert callable(getattr(served, "post", None)), (
        "the fallback must still be answerable"
    )


def test_the_bridge_actually_calls_fresh_door():
    """The reload must be wired into forward(), not merely defined beside it."""
    source = BRIDGE.read_text()
    assert "_fresh_door().post(" in source, (
        "forward() must call _fresh_door().post(...) so every tool call checks freshness"
    )
