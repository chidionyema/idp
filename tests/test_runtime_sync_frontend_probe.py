"""estate-runtime-sync must be able to see the /fleet dev server it just deployed.

2026-09-28: the dev server listens on ::1 only (app.baseUrl is `localhost`), the sync probed the
IPv4 literal 127.0.0.1, so `answers()` failed on every tick and every frontend deploy was rolled
back -- the live token-efficiency panel never reached /fleet. This starts a server bound to ::1
only, the way the real one is, and asks the script's own probe URL whether it can reach it.
"""

from __future__ import annotations

import http.server
import importlib.machinery
import importlib.util
import socket
import threading
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-runtime-sync"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_runtime_sync", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Ok(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


class _V6(http.server.HTTPServer):
    address_family = socket.AF_INET6


@pytest.fixture
def v6_only_server():
    try:
        srv = _V6(("::1", 0), _Ok)
    except OSError:
        pytest.skip("no IPv6 loopback on this machine")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_the_frontend_probe_reaches_a_server_bound_to_ipv6_loopback_only(
    v6_only_server,
):
    mod = _load()
    url = mod.FRONTEND_PROBE.replace(":3100", f":{v6_only_server}")
    assert mod.answers(url, 5), (
        f"{mod.FRONTEND_PROBE} cannot reach an ::1-only dev server"
    )


def test_the_ipv4_literal_cannot_reach_it_which_is_why_the_old_probe_always_failed(
    v6_only_server,
):
    mod = _load()
    assert not mod.answers(f"http://127.0.0.1:{v6_only_server}/", 3)


def test_a_failed_yarn_install_puts_the_reason_in_the_alert(tmp_path, monkeypatch):
    import subprocess

    mod = _load()
    tree = tmp_path / "frontend"
    (tree / ".git").mkdir(parents=True)
    (tree / "backstage/.yarn/releases").mkdir(parents=True)
    (tree / "backstage/.yarn/releases/yarn-4.13.0.cjs").write_text("")
    monkeypatch.setattr(mod, "FRONTEND", tree)

    def fake_git(*args, **kw):
        # rev-parse HEAD -> the old sha; the lockfile diff -> "changed"; everything else quiet
        return "aaaaaaaa" if args[0] == "rev-parse" else "backstage/yarn.lock"

    monkeypatch.setattr(mod, "git", fake_git)
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 1, stdout="", stderr="YN0001: ENOSPC: no space left on device"
        ),
    )
    alerts: list[str] = []
    monkeypatch.setattr(mod, "alert", alerts.append)

    notes = mod.sync_frontend("bbbbbbbb")

    assert notes == ["frontend held at aaaaaaaa (install failed)"]
    assert "ENOSPC: no space left on device" in alerts[0], alerts
