"""Tests for the inlined Holmes-finding writer (MUM-285). Pure HTTP, no Dagster.

The scheduler image is believed to ship ``urllib.request`` reliably; mirroring
``estate_memory``'s test pattern, ``_retain`` is verified by standing up a
local HTTP server in a thread, pointing the writer at it via
``ESTATE_MEMORY_URL``, and asserting the request the server received.
"""

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import pytest

# The pytest job in CI does not install dagster (it only runs tests that the
# holmes scheduler image isn't required for). Skip the whole module when dagster
# is absent so the suite passes collection cleanly; the bdd job, where dagster
# IS installed, runs every assertion below.
dagster = pytest.importorskip("dagster")

from scheduler.estate_scheduler.holmes_watch import (
    _build_finding,
    _retain,
    _truncate_to_bytes,
)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def memory_server(monkeypatch):
    """Spin up an HTTP server that records every POST it receives."""
    received = {}
    port = _free_port()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            return

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length) if length else b""
            received["path"] = self.path
            received["body"] = raw
            received["ct"] = self.headers.get("content-type", "")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

    httpd = HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("ESTATE_MEMORY_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("ESTATE_MEMORY_BANK", "hermes-test")
    monkeypatch.setenv("ESTATE_MEMORY_ORG", "default")
    monkeypatch.setenv("ESTATE_MEMORY_TIMEOUT_S", "3")
    monkeypatch.setenv("ESTATE_MEMORY_BYTE_CEILING", "8000")
    # Reload the module-level constants in holmes_watch so the fixture's
    # env values take effect for the duration of the test.
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    yield received
    httpd.shutdown()


def test_retain_posts_exact_contract(memory_server):
    finding = _build_finding(
        analysis="WHAT IS WRONG: foo. WHY: bar. FIX: baz.",
        fingerprint="abc123",
        alert_names=["KubePodCrashLooping", "Watchdog"],
    )
    out = _retain(
        finding["analysis"],
        subject=finding["subject"],
        kind=finding["kind"],
        tags=finding["tags"],
        fingerprint=finding["fingerprint"],
    )
    assert out["written"] is True
    assert urlparse(memory_server["path"]).path == (
        "/v1/default/banks/hermes-test/memories"
    )
    body = json.loads(memory_server["body"])
    item = body["items"][0]
    meta = item["metadata"]
    assert body["async"] is True
    assert "WHAT IS WRONG" in item["content"]
    assert meta["kind"] == "incident.investigation"
    assert meta["source"] == "holmes_watch"
    assert meta["fingerprint"] == "abc123"
    assert "alert:kubepodcrashlooping" in meta["tags"]
    assert "fp-abc123" in meta["tags"]
    assert memory_server["ct"] == "application/json"


def test_retain_fails_open_when_store_unreachable(monkeypatch):
    """Down store = logged warning, never raises, never pages."""
    monkeypatch.setenv("ESTATE_MEMORY_URL", "http://127.0.0.1:1")  # unreachable
    monkeypatch.setenv("ESTATE_MEMORY_TIMEOUT_S", "1")
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    out = _hw._retain(
        "WHAT IS WRONG: x. WHY: y. FIX: z.",
        subject="Holmes finding for foobar",
        kind="incident.investigation",
        tags=["holmes", "alert:foobar"],
        fingerprint="f1",
    )
    assert out["written"] is False
    assert "memory store unreachable" in out["error"]


def test_retain_refuses_non_http(monkeypatch):
    """A bad scheme is refused outright so the store cannot be hijacked."""
    monkeypatch.setenv("ESTATE_MEMORY_URL", "file:///etc/passwd")
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    out = _hw._retain("x", subject="x", kind="x", tags=[], fingerprint="")
    assert out["written"] is False
    assert "http(s)" in out["error"]


def test_retain_refuses_empty_analysis(monkeypatch):
    """A blank analysis is a 0-byte recall, never a no-op success."""
    monkeypatch.setenv("ESTATE_MEMORY_URL", "http://127.0.0.1:1")
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    out = _hw._retain("   ", subject="x", kind="x", tags=[], fingerprint="")
    assert out["written"] is False
    assert "empty" in out["error"]


def test_retain_refuses_unset_url(monkeypatch):
    monkeypatch.delenv("ESTATE_MEMORY_URL", raising=False)
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    out = _hw._retain("analysis", subject="x", kind="x", tags=[], fingerprint="")
    assert out["written"] is False
    assert "unset" in out["error"]


def test_retain_truncates_oversize(memory_server):
    """A burst analysis that exceeds the byte ceiling still posts, tail-cut."""
    big = ("x" * 200) + "\n\n[truncated to byte ceiling]"
    os.environ["ESTATE_MEMORY_BYTE_CEILING"] = "20"
    import importlib
    import scheduler.estate_scheduler.holmes_watch as _hw

    importlib.reload(_hw)
    out = _hw._retain(
        big,
        subject="Holmes finding for sizing",
        kind="incident.investigation",
        tags=["holmes"],
        fingerprint="s1",
    )
    assert out["written"] is True
    item = json.loads(memory_server["body"])["items"][0]
    assert len(item["content"].encode("utf-8")) <= 200
    assert "[truncated to byte ceiling]" in item["content"]
    os.environ.pop("ESTATE_MEMORY_BYTE_CEILING", None)


def test_build_finding_subject_and_tags_match_contract():
    f = _build_finding(
        analysis="x", fingerprint="fp1", alert_names=["KubePodCrashLooping"]
    )
    assert "Holmes finding for KubePodCrashLooping" in f["subject"]
    assert "alert:kubepodcrashlooping" in f["tags"]
    assert "fp-fp1" in f["tags"]
    assert f["kind"] == "incident.investigation"


def test_truncate_helper_is_byte_aware():
    s = "x" * 5000
    out = _truncate_to_bytes(s, 100)
    assert len(out.encode("utf-8")) <= 100 + 50
    assert "[truncated to byte ceiling]" in out
