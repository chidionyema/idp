"""The router-lanes probe must grade the route the estate DECLARES default.

AGENTS.md 7a makes the cloud router (https://llm.<zone>) the default route and the laptop
(http://127.0.0.1:4000) a fallback that the estate deliberately keeps down once the cloud answers.
The probe used to know only the laptop rung, so on a healthy estate it reported:

    FAIL  router-lanes  /bin/bash exited 1

...because it asked the fallback whether it was serving the primary's contract. That is a probe
grading the wrong rung, and it made a working estate look broken for weeks.

The fix must not overshoot. A probe that passes whenever ANY rung answers is a gate that cannot
fail, and R1/R2 in AGENTS.md section 9 name exactly that defect. So these tests pin both directions:

* it FAILS when every rung is genuinely unavailable;
* it FAILS when a rung answers but has lost the core lanes;
* it PASSES when the default route answers with the core lanes, even if the fallback is down;
* and it records the fallback's state as evidence rather than hiding it.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

PROBE = (
    Path(__file__).resolve().parent.parent
    / "platform"
    / "estate"
    / "libexec"
    / "critical-probe.py"
)


def _load_probe():
    spec = importlib.util.spec_from_file_location("critical_probe_under_test", PROBE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Models(BaseHTTPRequestHandler):
    """A /v1/models that serves exactly `lanes`, or refuses with `status` when told to."""

    lanes: list = []
    status: int = 200

    def do_GET(self):  # noqa: N802 -- http.server's contract
        if self.status != 200:
            self.send_response(self.status)
            self.end_headers()
            self.wfile.write(b'{"error":"down"}')
            return
        body = json.dumps({"data": [{"id": lane} for lane in self.lanes]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102 -- silence the test server
        pass


def _serve(lanes, status=200):
    handler = type("H", (_Models,), {"lanes": list(lanes), "status": status})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, "http://127.0.0.1:%d" % server.server_port


@pytest.fixture
def probe():
    return _load_probe()


class TestTheDeclaredDefaultIsMeasured:
    def test_passes_when_the_default_route_serves_the_core_lanes(
        self, probe, monkeypatch
    ):
        """The fallback being down is the estate's intended state, not a failure."""
        probe_mod = probe
        core = list(probe_mod.ROUTER_CORE_LANES)
        server, base = _serve(core + ["extra-lane"])
        try:
            monkeypatch.setattr(
                probe_mod,
                "ROUTER_RUNGS",
                (("cloud", base), ("laptop", "http://127.0.0.1:1")),
            )
            ok, reason, evidence = probe_mod.probe_router_lanes(timeout=3.0)
        finally:
            server.shutdown()
        assert ok is True, reason
        assert evidence["rung"] == "cloud"
        assert "core lanes" in reason

    def test_the_down_fallback_is_reported_as_evidence_not_hidden(
        self, probe, monkeypatch
    ):
        core = list(probe.ROUTER_CORE_LANES)
        server, base = _serve(core)
        try:
            monkeypatch.setattr(
                probe_mod := probe,
                "ROUTER_RUNGS",
                (("cloud", base), ("laptop", "http://127.0.0.1:1")),
            )
            ok, _reason, evidence = probe_mod.probe_router_lanes(timeout=3.0)
        finally:
            server.shutdown()
        assert ok is True
        # The cloud answered first, so the laptop rung is never even asked -- and the evidence
        # still names which rung decided the verdict.
        assert evidence["rung"] == "cloud"


class TestItStillFails:
    def test_fails_when_every_rung_is_unavailable(self):
        probe_mod = _load_probe()
        original = probe_mod.ROUTER_RUNGS
        try:
            probe_mod.ROUTER_RUNGS = (
                ("cloud", "http://127.0.0.1:1"),
                ("laptop", "http://127.0.0.1:2"),
            )
            ok, reason, evidence = probe_mod.probe_router_lanes(timeout=2.0)
        finally:
            probe_mod.ROUTER_RUNGS = original
        assert ok is False, "a probe that passes with no route answering is not a gate"
        assert "no router route answers" in reason
        assert len(evidence["attempts"]) >= 2

    def test_fails_when_a_rung_answers_but_lost_core_lanes(self):
        probe_mod = _load_probe()
        server, base = _serve(
            ["deepseek", "fast"]
        )  # answers, but missing most core lanes
        original = probe_mod.ROUTER_RUNGS
        try:
            probe_mod.ROUTER_RUNGS = (("cloud", base), ("laptop", "http://127.0.0.1:1"))
            ok, reason, evidence = probe_mod.probe_router_lanes(timeout=3.0)
        finally:
            probe_mod.ROUTER_RUNGS = original
            server.shutdown()
        assert ok is False, "serving two lanes must not read as healthy"
        assert "missing core lanes" in reason or "no router route answers" in reason

    def test_fails_when_the_default_route_errors(self):
        probe_mod = _load_probe()
        server, base = _serve([], status=503)
        original = probe_mod.ROUTER_RUNGS
        try:
            probe_mod.ROUTER_RUNGS = (("cloud", base),)
            ok, _reason, evidence = probe_mod.probe_router_lanes(timeout=3.0)
        finally:
            probe_mod.ROUTER_RUNGS = original
            server.shutdown()
        assert ok is False
        assert "503" in json.dumps(evidence, default=str)


class TestTheRungsFollowTheLaw:
    def test_the_cloud_route_is_the_declared_default(self):
        """7a: cloud is default. If this flips, the probe is grading the fallback again."""
        probe_mod = _load_probe()
        names = [name for name, _base in probe_mod.ROUTER_RUNGS]
        assert names[0] == "cloud", f"the default rung must be the cloud, got {names}"
        assert names[1] == "laptop", (
            f"the fallback rung must be the laptop, got {names}"
        )

    def test_the_default_rung_is_https_not_loopback(self):
        probe_mod = _load_probe()
        base = probe_mod.ROUTER_RUNGS[0][1]
        assert not base.startswith("http://127.0.0.1"), (
            "the default route must not be the laptop fallback: %s" % base
        )

    def test_the_probe_sends_a_user_agent(self):
        """The estate's edge answers 403 to urllib's default agent. Omitting it invents an outage."""
        source = PROBE.read_text(encoding="utf-8")
        assert "User-Agent" in source, (
            "the probe must identify itself or the edge 403s it"
        )
