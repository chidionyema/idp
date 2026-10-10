"""The fleetview backend's outbox worker runs whenever the bus is configured. Before 2026-09-29
nothing started it: browser steer intents and the router's signed actions were written to
~/.estate/outbox.db and never drained to JetStream, so the Fleet director never saw them."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backstage/plugins/fleetview-backend/src"
sys.path.insert(0, str(SRC))

pytest.importorskip("fastapi")
from fleetview_backend import claude_code_adapter, efficiency_feed, outbox, serve  # noqa: E402


def test_lifespan_starts_and_stops_the_outbox_worker(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "NATS_URL", "nats://127.0.0.1:1"
    )  # nothing listens; the worker retries
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))

    async def _idle(*_a, **_k):
        await asyncio.sleep(0)

    monkeypatch.setattr(claude_code_adapter, "run_claude_code_adapter", _idle)
    monkeypatch.setattr(efficiency_feed, "publish_highlights", _idle)
    outbox._worker = None

    async def run():
        async with serve.lifespan(None):
            w = outbox._worker
            assert w is not None and w._running
            assert w._task is not None and not w._task.done()
        assert not w._running

    asyncio.run(run())


def test_a_row_whose_payload_carries_the_envelope_still_publishes(
    monkeypatch, tmp_path
):
    """estate-execute and action_ledger store the whole event, session_id and all (idp#5651)."""
    import json
    import sqlite3

    sent = []

    class _Adapter:
        @staticmethod
        async def publish(nats_url, session_id, runtime, kind, phase, **kwargs):
            sent.append((session_id, runtime, kind, phase, kwargs))

    monkeypatch.setattr(outbox, "_nats", lambda: _Adapter)
    monkeypatch.delenv("KAFKA_BROKERS", raising=False)
    event = {
        "session_id": "direct",
        "runtime": "claude-code",
        "kind": "gate",
        "phase": "executing",
        "at": "2026-10-10T09:09:38+00:00",
        "gate": {"name": "estate-policy:shadow", "verdict": "refuse"},
    }
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE r (session_id, runtime, kind, phase, payload)",
    )
    con.execute(
        "INSERT INTO r VALUES (?, ?, ?, ?, ?)",
        ("direct", "claude-code", "gate", "executing", json.dumps(event)),
    )
    row = con.execute("SELECT * FROM r").fetchone()

    ok, err = asyncio.run(outbox._publish_row(row, "nats://127.0.0.1:1"))

    assert (ok, err) == (True, "")
    assert sent[0][:4] == ("direct", "claude-code", "gate", "executing")
    assert sent[0][4]["gate"]["verdict"] == "refuse"
