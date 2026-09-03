"""crew#284 CP6: self-termination rules, one incident test per rule (rung 4),
and the enforcement step with the Temporal boundary stubbed.

Before this, evaluate() was a pure function only `sb self-check` printed;
nothing halted. The thresholds are read from config, never typed here.
"""
from __future__ import annotations

import asyncio
from typing import Any

from sovereign import config
from sovereign.engine import termination
from sovereign.engine import config_keys as ck


def _blind_s(extra: float) -> float:
    return float(config.get("blind.halt_after_min").value) * termination.SECONDS_PER_MINUTE + extra


def test_incident_cp6_langfuse_blind_over_five_minutes_halts() -> None:
    assert termination.evaluate(termination.Signals(langfuse_blind_s=_blind_s(+1)))["action"] == "halt"
    assert termination.evaluate(termination.Signals(langfuse_blind_s=_blind_s(0)))["action"] == "continue"


def test_incident_cp6_low_confidence_three_steps_soft_halts() -> None:
    n = int(ck.get("terminate.low_confidence_steps"))
    assert termination.evaluate(termination.Signals(low_confidence_streak=n))["action"] == "soft_halt"
    assert termination.evaluate(termination.Signals(low_confidence_streak=n - 1))["action"] == "continue"
    assert termination.is_low_confidence(float(ck.get("terminate.min_confidence")) - 0.01)


def test_incident_cp6_alert_flood_over_fifty_per_hour_digests() -> None:
    cap = int(config.get("alerts.digest_over_per_hour").value)
    assert termination.evaluate(termination.Signals(alerts_last_hour=cap + 1))["action"] == "digest"
    assert termination.evaluate(termination.Signals(alerts_last_hour=cap))["action"] == "continue"


def test_incident_cp6_enforce_stops_running_sessions_only_on_halt(monkeypatch: Any) -> None:
    from sovereign.engine import client as engine_client

    rows = [
        {"session_id": "s-run", "status": "running"},
        {"session_id": "s-ask", "status": "asking"},
        {"session_id": "s-done", "status": "done"},
        {"session_id": "s-crit", "status": "running", "critical": True},
    ]
    signalled: list[tuple[str, str, str]] = []

    async def fake_list() -> list[dict[str, Any]]:
        return rows

    async def fake_signal(session_id: str, name: str, by: str, reason: str = "") -> dict[str, Any]:
        signalled.append((session_id, name, reason))
        return {"ok": True}

    monkeypatch.setattr(engine_client, "list_sessions", fake_list)
    monkeypatch.setattr(engine_client, "signal", fake_signal)

    halt = termination.evaluate(termination.Signals(langfuse_blind_s=_blind_s(+1)))
    done = termination.enforce(halt)
    assert done["stopped"] == ["s-run", "s-ask"]
    assert done["kept"] == ["s-crit"]
    assert all(n == "stop" and r.startswith("self-termination:blind") for _, n, r in signalled)

    signalled.clear()
    assert termination.enforce(termination.evaluate(termination.Signals())) == {"action": "continue"}
    assert signalled == []
