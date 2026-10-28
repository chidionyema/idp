"""The estate adapter's own rules, tested where they can be wrong.

WHAT IS WORTH A TEST HERE, and what is not. The adapter's job is to observe without changing
the work, and to be honest about money. Three things can be silently wrong, and each has a
test below:

  1. the price table parse. It is a shallow walk of the router's config, not a YAML library,
     so a shape it does not recognise must yield UNKNOWN, never zero.
  2. the cost derivation. Only the DEPLOYMENT can price a call (`default` is four deployments
     with four prices), and a deployment with no price row has no cost -- which is unknown,
     not $0.0000.
  3. the emitter's flush. Evidence that is still queued when the process ends is evidence that
     was never written, and a caller that returns before its events have left is a caller that
     reports a task it has not recorded.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
_SRC = REPO / "packages" / "aei" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aei import core, estate  # noqa: E402
from aei.client import Emitter  # noqa: E402


def test_the_price_table_is_read_from_the_router_config():
    """The estate's own price table, and it is not empty: the router config declares prices."""
    rows = estate._price_rows()
    assert rows, "no price rows were parsed from platform/llm/config.yaml"
    assert any("input_cost_per_token" in row for row in rows.values())


def test_a_priced_deployment_prices_a_call():
    rows = estate._price_rows()
    deployment = next(
        name
        for name, row in rows.items()
        if "input_cost_per_token" in row and "output_cost_per_token" in row
    )
    cost, grade = estate.derived_cost(deployment, 1000, 1000)
    assert cost is not None and cost > 0
    assert grade == "derived"


def test_an_unpriced_deployment_is_unknown_not_zero():
    """The hole the estate already paid for: tokens spent, money recorded as zero."""
    cost, grade = estate.derived_cost("some/unpriced-deployment", 1000, 1000)
    assert cost is None
    assert grade == "unknown"


def test_no_deployment_is_unknown():
    cost, grade = estate.derived_cost(None, 1000, 1000)
    assert cost is None
    assert grade == "unknown"


def test_a_missing_price_table_is_unknown_not_zero(monkeypatch, tmp_path):
    """A router config that is not there must not make every call free."""
    monkeypatch.setattr(estate, "IDP_ROOT", tmp_path)
    cost, grade = estate.derived_cost("openai/MiniMax-M3", 1000, 1000)
    assert cost is None
    assert grade == "unknown"


def test_identity_carries_the_six_identifiers():
    ident = estate.identity(
        run_id="run-1",
        task_id="task-1",
        agent_id="agent-1",
        harness_id="harness-1",
        revision="abc123",
    )
    assert set(ident) == set(core.IDENTIFIERS)
    assert ident["trace_id"] == "run-1"
    assert all(isinstance(v, str) and v for v in ident.values())


class _Recorder:
    """An emitter stand-in that keeps what was emitted, so the test reads the events."""

    def __init__(self):
        self.events: list[dict] = []

    def emit(self, event_type, attributes=None, parent_id=None):
        event = core.make_event(
            event_type,
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            harness_id="harness-1",
            trace_id="run-1",
            revision="abc123",
            parent_id=parent_id,
            attributes=attributes,
        )
        self.events.append(event)
        return event


def test_a_tool_invocation_is_recorded_on_both_sides():
    recorder = _Recorder()
    with estate.tool(
        recorder, {}, "read_file", source_path="a.py", attributes={"bytes_in": 12}
    ):
        pass
    types = [e["type"] for e in recorder.events]
    assert types == ["tool.started", "tool.completed"]
    assert recorder.events[0]["attributes"]["bytes_in"] == 12
    assert recorder.events[1]["attributes"]["duration_ms"] >= 0


def test_a_failing_tool_is_recorded_as_failed_and_re_raised():
    recorder = _Recorder()
    with pytest.raises(RuntimeError):
        with estate.tool(recorder, {}, "read_file"):
            raise RuntimeError("boom")
    types = [e["type"] for e in recorder.events]
    assert types == ["tool.started", "tool.failed"]
    assert recorder.events[1]["attributes"]["error_type"] == "RuntimeError"


def test_a_failed_verification_is_a_failed_verification():
    recorder = _Recorder()
    with pytest.raises(AssertionError):
        with estate.verification(recorder, {}):
            raise AssertionError("not verified")
    types = [e["type"] for e in recorder.events]
    assert types == ["verification.started", "verification.failed"]


def test_a_task_that_finishes_is_recorded_as_completed():
    recorder = _Recorder()
    with estate.task(recorder, {}):
        pass
    types = [e["type"] for e in recorder.events]
    assert types == ["task.started", "task.completed"]


def test_a_task_that_fails_is_recorded_as_failed():
    recorder = _Recorder()
    with pytest.raises(RuntimeError):
        with estate.task(recorder, {}):
            raise RuntimeError("boom")
    types = [e["type"] for e in recorder.events]
    assert types == ["task.started", "task.failed"]


def test_the_emitter_writes_to_the_collector_and_flushes(tmp_path):
    """The whole loop, against a collector that is really there: a local HTTP server.

    The point is the FLUSH: evidence still queued when the process ends is evidence nobody
    ever read. So the test asserts that after flush() the collector has the event.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    received: list[dict] = []

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            received.append(body)
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        emitter = Emitter(
            f"http://127.0.0.1:{server.server_port}",
            "test-token",
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "harness_id": "harness-1",
                "trace_id": "run-1",
                "revision": "abc123",
            },
        )
        emitter.emit("task.started", attributes={"status": "started"})
        emitter.flush(timeout=5.0)
        assert received, (
            "flush returned without the collector having received the event"
        )
        assert received[0]["type"] == "task.started"
        core.validate(received[0])
    finally:
        server.shutdown()
