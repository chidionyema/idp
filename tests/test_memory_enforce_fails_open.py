"""An unreachable memory door must not deadlock every write (idp#7351).

Measured 2026-10-28: with the cluster down, `brief` could not succeed, so the edit-time gate refused
every Write, including the repair work. The gate's own docstring says it fails open on anything that
is not a clear violation; an agent that cannot brief has not violated anything.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin" / "estate-memory-enforce"


def load():
    loader = importlib.machinery.SourceFileLoader("estate_memory_enforce", str(BIN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_unreachable_door_is_detected(monkeypatch):
    m = load()

    def boom(*a, **k):
        raise RuntimeError("memory door unreachable")

    monkeypatch.setattr(m.door, "call", boom)
    monkeypatch.setattr(m.door, "key", lambda: "k")
    assert m.door_unreachable() is True


def test_reachable_door_is_not_unreachable(monkeypatch):
    m = load()
    monkeypatch.setattr(m.door, "call", lambda *a, **k: {"ok": 1})
    monkeypatch.setattr(m.door, "key", lambda: "k")
    assert m.door_unreachable() is False


def test_unbriefed_write_passes_the_brief_check_when_door_is_down(
    monkeypatch, tmp_path
):
    m = load()
    log = []
    monkeypatch.setattr(m, "transcript_text", lambda d: "no brief here")
    monkeypatch.setattr(m, "durable", lambda p: True)
    monkeypatch.setattr(m, "door_unreachable", lambda: True)
    monkeypatch.setattr(m, "record", lambda *a, **k: log.append(a))
    denied = []
    monkeypatch.setattr(m, "deny_pre", lambda r: denied.append(r))
    monkeypatch.setattr(m.focus, "live_focus", lambda: None)
    m.pre(
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "x.py")},
            "session_id": "s",
        }
    )
    assert not any("not briefed" in a for entry in log for a in entry)


def test_unbriefed_write_is_refused_when_door_is_up(monkeypatch, tmp_path):
    m = load()
    monkeypatch.setattr(m, "transcript_text", lambda d: "no brief here")
    monkeypatch.setattr(m, "durable", lambda p: True)
    monkeypatch.setattr(m, "door_unreachable", lambda: False)
    monkeypatch.setattr(m, "record", lambda *a, **k: None)
    denied = []
    monkeypatch.setattr(m, "deny_pre", lambda r: denied.append(r))
    m.pre(
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "x.py")},
            "session_id": "s",
        }
    )
    assert denied
