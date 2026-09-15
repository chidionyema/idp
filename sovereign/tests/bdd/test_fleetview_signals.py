"""FleetView nudge (item #6): src/signals.py, graded the same way test_fleetview_notes.py and
test_fleetview_spend.py grade their modules -- a plain unit suite, no feature file, no live
Temporal cluster.

`sovereign.engine.client.signal` is stubbed: this suite proves signals.py's own contract (input
validation, runtime scoping, and that every real attempt is recorded) rather than Temporal's own
delivery, which `sovereign/tests/bdd/test_engine_*` already covers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SIGNALS_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "signals.py"
)
ROUTES_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "routes.py"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def signals(monkeypatch, tmp_path):
    db = tmp_path / "estate.db"
    monkeypatch.setenv("ESTATE_DB", str(db))
    return _load(SIGNALS_MODULE, "fleetview_signals_under_test")


@pytest.fixture()
def routes(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate-test.db"))
    return _load(ROUTES_MODULE, "fleetview_routes_under_test")


def _fake_engine_client(monkeypatch, module, ok: bool, error: str | None = None):
    """Stubs the `from sovereign.engine import client as engine_client` import inside
    _dispatch_steer by monkeypatching sys.modules -- signals.py imports it lazily, at call time,
    so this must be in place before nudge() runs, not before signals.py is loaded."""
    import sys
    import types

    fake_client = types.ModuleType("sovereign.engine.client")

    async def fake_signal(session_id, kind, by, text=""):
        assert kind == "steer"
        return {"ok": ok} if ok else {"ok": False, "error": error or "boom"}

    fake_client.signal = fake_signal
    fake_engine = types.ModuleType("sovereign.engine")
    fake_engine.client = fake_client
    fake_sovereign = sys.modules.get("sovereign") or types.ModuleType("sovereign")
    monkeypatch.setitem(sys.modules, "sovereign", fake_sovereign)
    monkeypatch.setitem(sys.modules, "sovereign.engine", fake_engine)
    monkeypatch.setitem(sys.modules, "sovereign.engine.client", fake_client)


def test_a_blank_session_id_is_invalid_and_writes_nothing(signals):
    with pytest.raises(signals.InvalidSignal):
        signals.nudge("", "sovereign", "chidi")
    assert signals.signals_for("") == []


def test_a_blank_by_is_invalid(signals):
    with pytest.raises(signals.InvalidSignal):
        signals.nudge("sb-1", "sovereign", "")


def test_an_unsupported_runtime_is_refused_and_writes_nothing(signals):
    with pytest.raises(signals.UnsupportedRuntime):
        signals.nudge("sb-1", "claude-code", "chidi")
    assert signals.signals_for("sb-1") == []


def test_a_successful_steer_is_recorded_ok(signals, monkeypatch):
    _fake_engine_client(monkeypatch, signals, ok=True)
    record = signals.nudge("sb-1", "sovereign", "chidi", "please wrap up")
    assert record["ok"] is True
    assert record["error"] is None
    assert record["text"] == "please wrap up"
    rows = signals.signals_for("sb-1")
    assert len(rows) == 1
    assert rows[0]["ok"] is True


def test_a_blank_text_falls_back_to_the_default_nudge(signals, monkeypatch):
    _fake_engine_client(monkeypatch, signals, ok=True)
    record = signals.nudge("sb-1", "sovereign", "chidi", "")
    assert record["text"] == signals.DEFAULT_NUDGE_TEXT


def test_a_failed_signal_is_still_recorded_never_silently_dropped(signals, monkeypatch):
    _fake_engine_client(monkeypatch, signals, ok=False, error="workflow not found")
    record = signals.nudge("sb-1", "sovereign", "chidi")
    assert record["ok"] is False
    assert "workflow not found" in record["error"]
    rows = signals.signals_for("sb-1")
    assert len(rows) == 1
    assert rows[0]["ok"] is False


def test_get_route_is_always_200_even_when_empty(routes):
    body, status = routes.signals_envelope("no-such-session")
    assert status == 200
    assert body == {"signals": []}


def test_get_route_after_a_nudge_sees_the_same_signal(routes, monkeypatch):
    _fake_engine_client(monkeypatch, routes, ok=True)
    routes.add_nudge(
        {"session_id": "sb-4", "runtime": "sovereign", "by": "chidi", "text": "wrap up"}
    )
    body, status = routes.signals_envelope("sb-4")
    assert status == 200
    assert [s["text"] for s in body["signals"]] == ["wrap up"]
    assert body["signals"][0]["ok"] is True
