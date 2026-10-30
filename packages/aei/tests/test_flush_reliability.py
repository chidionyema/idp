"""A collector acknowledgement, rather than dequeueing, completes delivery."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aei.client import Emitter


@pytest.mark.parametrize("status", [201, 503])
def test_flush_reports_unacknowledged_event_as_pending(status):
    received = threading.Event()
    acknowledge = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            received.set()
            acknowledge.wait(5)
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    emitter = Emitter(
        f"http://127.0.0.1:{server.server_port}",
        "test-token",
        dict(
            run_id="flush-run",
            task_id="flush-task",
            agent_id="test",
            harness_id="pytest",
            trace_id="flush-trace",
            revision="test",
        ),
        timeout=3,
    )
    try:
        emitter.emit("task.started")
        assert received.wait(3), "collector did not receive the request"
        stats = emitter.flush(timeout=0)
        assert stats["pending"] == 1, "in-flight delivery disappeared from pending"
        assert stats["sent"] == 0
        acknowledge.set()
        stats = emitter.flush(timeout=3)
        assert stats == {
            "pending": 0,
            "sent": int(status == 201),
            "errors": int(status == 503),
            "dropped": 0,
        }
    finally:
        acknowledge.set()
        emitter.close(timeout=3)
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
