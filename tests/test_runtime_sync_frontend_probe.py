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
    monkeypatch.setattr(mod, "FRONTEND_ENABLED", True)
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


# --- the retirement, 2026-11-08 -------------------------------------------------------------
#
# The /fleet frontend is retired (the work surface is argon) and its backstage/node_modules was
# closing every executor door on the machine: a 2.3G dependency tree under a 1500M floor. These
# are the FALSIFIERS. Remove the `FRONTEND_ENABLED` gate from sync_frontend, or provision the
# clone unconditionally again, and they fail -- a test that would pass either way is not a test.


def test_the_frontend_is_not_provisioned_unless_it_is_opted_in(tmp_path, monkeypatch):
    """Unset flag: nothing is cloned, checked out or installed. The tick states why."""
    mod = _load()
    monkeypatch.setattr(mod, "FRONTEND_ENABLED", False)
    tree = tmp_path / "frontend"
    monkeypatch.setattr(mod, "FRONTEND", tree)

    called = []
    monkeypatch.setattr(mod, "git", lambda *a, **k: called.append(a) or "")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: called.append(a))

    notes = mod.sync_frontend("deadbeef")

    assert called == [], f"a retired frontend did work anyway: {called[:3]}"
    assert not tree.exists(), "a retired frontend was provisioned on disk"
    # Absent tree + retired flag is the normal steady state, so it is silent (see
    # test_an_absent_retired_frontend_is_silent). Nothing ran, and nothing was created.
    assert notes == [], notes


def test_the_retired_frontend_says_so_once_and_never_deletes_the_tree(
    tmp_path, monkeypatch
):
    """It reports, and it leaves the tree alone: deleting is disk-reclaim's job, not the sync's."""
    mod = _load()
    monkeypatch.setattr(mod, "FRONTEND_ENABLED", False)
    tree = tmp_path / "frontend"
    (tree / "backstage").mkdir(parents=True)
    keep = tree / "backstage" / "app-config.yaml"
    keep.write_text("title: fleet\n")
    monkeypatch.setattr(mod, "FRONTEND", tree)

    notes = mod.sync_frontend("deadbeef")

    assert keep.exists() and keep.read_text() == "title: fleet\n"
    assert "left as it is" in notes[0], notes


def test_an_absent_retired_frontend_is_silent(tmp_path, monkeypatch):
    """No tree and no flag is the normal state now, not a complaint on every tick."""
    mod = _load()
    monkeypatch.setattr(mod, "FRONTEND_ENABLED", False)
    monkeypatch.setattr(mod, "FRONTEND", tmp_path / "absent")

    assert mod.sync_frontend("deadbeef") == []


def test_opting_in_restores_the_old_behaviour_exactly(tmp_path, monkeypatch):
    """ESTATE_FRONTEND_ENABLED=1 must still provision, so the retirement is reversible."""
    mod = _load()
    monkeypatch.setattr(mod, "FRONTEND_ENABLED", True)
    tree = tmp_path / "frontend"
    (tree / ".git").mkdir(parents=True)
    monkeypatch.setattr(mod, "FRONTEND", tree)

    called = []

    def fake_git(*args, **kw):
        called.append(args)
        return "aaaaaaaa" if args[0] == "rev-parse" else ""

    monkeypatch.setattr(mod, "git", fake_git)
    mod.sync_frontend("aaaaaaaa")

    assert any(a[0] == "rev-parse" for a in called), (
        "opted in, but the frontend was still skipped"
    )


def test_the_flag_is_off_by_default():
    """The default is the whole point: an unset env var retires the frontend."""
    import os

    loader = importlib.machinery.SourceFileLoader(
        "estate_runtime_sync_default", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    had = os.environ.pop("ESTATE_FRONTEND_ENABLED", None)
    try:
        loader.exec_module(mod)
        assert mod.FRONTEND_ENABLED is False
    finally:
        if had is not None:
            os.environ["ESTATE_FRONTEND_ENABLED"] = had
