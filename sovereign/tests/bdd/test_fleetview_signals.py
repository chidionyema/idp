"""FleetView nudge (item #6, CP8): src/signals.py, graded the same way test_fleetview_notes.py and
test_fleetview_spend.py grade their modules -- a plain unit suite, no feature file, no live
Temporal cluster.

`sovereign.engine.client.signal` is stubbed: this suite proves signals.py's own contract (input
validation, runtime scoping, and that every real attempt is recorded) rather than Temporal's own
delivery, which `sovereign/tests/bdd/test_engine_*` already covers.

CP8 additions: claude-code directives mailbox, otto NATS steer, cyrus Linear comment, and the
routing through the updated _dispatch_steer(session_id, runtime, by, text) signature.
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
        signals.nudge("sb-1", "dagster", "chidi")
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


# ---------------------------------------------------------------------------
# CP8: claude-code directives mailbox
# ---------------------------------------------------------------------------


def test_dispatch_steer_claude_code_writes_correct_json(signals, tmp_path, monkeypatch):
    """_dispatch_steer_claude_code writes a file at <directives_dir>/<raw_uuid>.json with the
    expected keys, deriving the directives dir from ESTATE_STATE_PATH_PREFIX."""
    ledger = tmp_path / "prompt-ledger"
    ledger.mkdir()
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(ledger) + "/")

    error = signals._dispatch_steer_claude_code(
        "idp:s-xyz", "founder", "check the signals"
    )
    assert error is None

    import json as _json

    dest = tmp_path / "directives" / "s-xyz.json"
    assert dest.exists(), f"expected directive file at {dest}"
    payload = _json.loads(dest.read_text(encoding="utf-8"))
    assert payload["session_id"] == "idp:s-xyz"
    assert payload["by"] == "founder"
    assert payload["text"] == "check the signals"
    assert "written_at" in payload


def test_nudge_with_claude_code_runtime_succeeds(signals, tmp_path, monkeypatch):
    """nudge() with runtime='claude-code' calls _dispatch_steer_claude_code and records ok=True."""
    ledger = tmp_path / "prompt-ledger"
    ledger.mkdir()
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(ledger) + "/")

    record = signals.nudge("idp:s-xyz", "claude-code", "founder", "check the signals")
    assert record["ok"] is True
    assert record["error"] is None
    assert record["session_id"] == "idp:s-xyz"
    rows = signals.signals_for("idp:s-xyz")
    assert len(rows) == 1
    assert rows[0]["ok"] is True


# ---------------------------------------------------------------------------
# CP8: cyrus — no LINEAR_API_KEY returns error, never raises
# ---------------------------------------------------------------------------


def test_dispatch_steer_cyrus_without_api_key_returns_error_not_raise(
    signals, monkeypatch
):
    """_dispatch_steer_cyrus with no LINEAR_API_KEY returns an error string -- never raises."""
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.delenv("LINEAR_API_KEY_FILE", raising=False)

    error = signals._dispatch_steer_cyrus("IDP-1234:some-uuid", "founder", "hello")
    assert error is not None
    assert "LINEAR_API_KEY" in error


# ---------------------------------------------------------------------------
# CP8: dagster — unsupported runtime raises UnsupportedRuntime before any row
# ---------------------------------------------------------------------------


def test_nudge_with_dagster_runtime_raises_unsupported(signals):
    """nudge() with runtime='dagster' raises UnsupportedRuntime and records nothing."""
    with pytest.raises(signals.UnsupportedRuntime):
        signals.nudge("dag-1", "dagster", "founder", "hello")
    assert signals.signals_for("dag-1") == []


# ---------------------------------------------------------------------------
# CP8: otto — no NATS_URL records ok=False with the real error
# ---------------------------------------------------------------------------


def test_nudge_with_otto_runtime_no_nats_url_records_ok_false(signals, monkeypatch):
    """nudge() with runtime='otto' and NATS_URL unset records ok=False with a real error message.
    Two conditions are acceptable: NATS_URL not configured (env missing) or nats library not
    importable -- both are honest 'cannot reach Otto' outcomes that must be recorded, never silently
    dropped."""
    monkeypatch.delenv("NATS_URL", raising=False)

    record = signals.nudge("otto:t-789", "otto", "founder", "pause and report")
    assert record["ok"] is False
    assert record["error"] is not None
    # Either the nats library is missing, or NATS_URL is not configured -- both are valid errors
    assert "NATS_URL" in record["error"] or "nats" in record["error"].lower()
    rows = signals.signals_for("otto:t-789")
    assert len(rows) == 1
    assert rows[0]["ok"] is False


# ---------------------------------------------------------------------------------------------
# 2026-09-18: the buttons that lied. Read from the client's own backend log, which recorded the
# real outcomes of real presses:
#
#     POST /nudge          200   (claude-code: writes a directive file, no cluster needed)
#     POST /approve        502   <- reported as a failed attempt; nothing was attempted
#     POST /deny           502   <- same
#     POST /stop           404, then 500
#
# The 502s came from `else: error = f"... not yet wired for {runtime}"`, which RECORDED A FAILED
# ATTEMPT and returned it through the `ok is None` path, so routes.py turned it into 502 --
# "the signal was attempted against a real session and failed". That sentence is false: there is
# no channel, so there is nothing to attempt, and an operator sent to debug a healthy service is
# the cost of saying it anyway. The correct answer is 422, and `SIGNAL_RUNTIMES` is now the one
# place that decides.


def test_approve_on_a_runtime_with_no_channel_is_422_not_502(routes):
    """The button that lied on 2026-09-18, graded on the status code it must not return."""
    body, status = routes.add_approve(
        {"session_id": "claude-code:fleet-live-001", "runtime": "claude-code", "by": "founder"}
    )
    assert status == 422, (
        f"approve on claude-code returned {status}. 502 means 'attempted and failed', which is "
        "not what happened -- there is no approve channel for claude-code."
    )
    # And the refusal has to be usable: name the signal, the runtime, and what to do instead.
    assert "approve" in body["error"]
    assert "claude-code" in body["error"]
    assert "steer" in body["error"], "the reader is told the verb that does work"


def test_deny_on_a_runtime_with_no_channel_is_422_not_502(routes):
    _body, status = routes.add_deny(
        {"session_id": "otto:fleet-live-003", "runtime": "otto", "by": "founder"}
    )
    assert status == 422


def test_stop_on_otto_is_422_and_names_the_runtimes_that_work(routes):
    body, status = routes.add_stop(
        {"session_id": "otto:fleet-live-003", "runtime": "otto", "by": "founder"}
    )
    assert status == 422
    assert "sovereign" in body["error"] and "claude-code" in body["error"]


def test_a_refused_channel_writes_no_audit_row(signals, tmp_path):
    """An attempt that never reached a session is not an attempt.

    Same rule notes.py's InvalidNote follows. Before this, the row existed and said ok=False,
    which is why the audit trail looked like a service failing rather than a request that named
    an impossible combination.
    """
    with pytest.raises(signals.UnsupportedRuntime):
        signals.approve(
            session_id="claude-code:fleet-live-001", runtime="claude-code", by="founder"
        )
    assert signals.signals_for("claude-code:fleet-live-001") == []


def test_steer_still_covers_every_runtime(signals, monkeypatch):
    """The one verb with a channel everywhere, so the table did not narrow it by accident."""
    assert signals.SIGNAL_RUNTIMES["steer"] == frozenset(
        {"sovereign", "claude-code", "otto", "cyrus"}
    )
    # And a steer to each runtime is accepted (dispatch stubbed: this grades the channel check,
    # not the four delivery mechanisms, which the CP8 cases already cover above).
    for name in (
        "_dispatch_steer_sovereign",
        "_dispatch_steer_claude_code",
        "_dispatch_steer_otto",
        "_dispatch_steer_cyrus",
    ):
        monkeypatch.setattr(signals, name, lambda *a, **k: None)
    for runtime in ("sovereign", "claude-code", "otto", "cyrus"):
        record = signals.nudge(
            session_id=f"{runtime}:fleet-live-001",
            runtime=runtime,
            by="founder",
            text="check the signals",
        )
        assert record["ok"] is True, f"steer to {runtime} was refused: {record.get('error')}"


def test_the_channel_table_names_every_signal_the_module_exposes(signals):
    """A signal added without a row would KeyError at runtime; this makes it a test failure."""
    for name in ("steer", "stop", "approve", "deny"):
        assert name in signals.SIGNAL_RUNTIMES, f"{name} has no entry in SIGNAL_RUNTIMES"
        assert signals.SIGNAL_RUNTIMES[name], f"{name} declares no runtime at all"


def test_a_missing_engine_is_reported_as_a_502_with_the_real_reason(routes):
    """The sovereign path: the channel EXISTS, so 502 is right -- and the message must say why.

    The old `except Exception: error = str(exc)` produced `No module named 'temporalio'`, which
    reads as a mystery. Naming it as an import failure tells an operator the host is missing a
    dependency rather than that the far end is broken.
    """
    body, status = routes.add_approve(
        {"session_id": "sovereign:fleet-live-002", "runtime": "sovereign", "by": "founder"}
    )
    # 502 when the engine cannot be reached; the reason must be specific.
    assert status == 502
    assert "sovereign engine" in body["error"] or "temporalio" in body["error"]
