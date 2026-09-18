"""Device access (2026-09-18): src/device_access.py, graded like the other fleetview modules.

The tile on /ops shows this device's read-only cluster identity and offers the one action only
the owner can take. It reports; it does not provision. The distinction is the whole point, and
the first test below is the one that keeps it: a route that could provision would be a route
that can make any caller trustworthy, which is the property the JIT broker exists to deny.

The states are read from `bin/idp-jit status`. The command is stubbed here so the suite grades
this module's own contract -- the mapping from a status document to a response, and the refusal
to guess when it cannot read -- rather than the local install, which varies per machine.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
DEVICE_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "device_access.py"
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
def device():
    return _load(DEVICE_MODULE, "fleetview_device_access_under_test")


def _stub_status(
    monkeypatch, device, *, stdout: str = "", returncode: int = 0, stderr: str = ""
):
    class _P:
        pass

    def fake_run(*_a, **_k):
        p = _P()
        p.stdout = stdout
        p.stderr = stderr
        p.returncode = returncode
        return p

    monkeypatch.setattr(device.subprocess, "run", fake_run)


def test_the_route_reports_and_never_provisions(device):
    """The property WJ.1 rests on: this door answers a question, it does not grant access.

    `bin/idp-mac-secret-deliver` refuses an agent session by design, and nothing here may
    become a second way to put a key on a device. Graded by naming, so a future method that
    does provision cannot slip in unnoticed.
    """
    provision = [
        n for n in dir(device) if "provision" in n.lower() or "deliver" in n.lower()
    ]
    assert provision == [], (
        "device_access.py grew something that can provision: "
        f"{provision}. Putting the agent key on a device is the owner's act alone."
    )


def test_not_provisioned_is_an_answer_not_an_error(device, monkeypatch):
    """A device with no key is a 200 carrying a state, never a 5xx."""
    _stub_status(
        monkeypatch,
        device,
        stdout=json.dumps(
            {"state": "not_provisioned", "has_key": False, "expires_in": None}
        ),
    )
    body, status = device.device_status_envelope()
    assert status == 200
    assert body["state"] == "not_provisioned"


def test_active_carries_the_expiry_the_tile_renders(device, monkeypatch):
    _stub_status(
        monkeypatch,
        device,
        stdout=json.dumps(
            {
                "state": "active",
                "scope": "read-only",
                "expires_in": 2580,
                "subject": "system:serviceaccount:agents:agent-reader",
            }
        ),
    )
    body, status = device.device_status_envelope()
    assert status == 200
    assert body["expires_in"] == 2580
    assert body["scope"] == "read-only"


def test_a_broken_read_is_unreadable_and_never_a_permissive_default(
    device, monkeypatch
):
    """The failure that matters: an unreadable status must not render as 'Active'.

    A status surface that guesses in the permissive direction tells the owner production reads
    work when nobody knows whether they do. Every failure below must land on 'unreadable'.
    """
    # Non-zero exit.
    _stub_status(monkeypatch, device, stdout="", returncode=4, stderr="refused")
    body, status = device.device_status_envelope()
    assert status == 503
    assert body["state"] == "unreadable"
    assert "refused" in body["error"]

    # Not JSON.
    _stub_status(monkeypatch, device, stdout="not json at all")
    body, status = device.device_status_envelope()
    assert status == 503
    assert body["state"] == "unreadable"

    # JSON but no state field.
    _stub_status(monkeypatch, device, stdout=json.dumps({"hello": "world"}))
    body, status = device.device_status_envelope()
    assert status == 503
    assert body["state"] == "unreadable"

    # And in every one of those, the permissive state is never the answer.
    for _ in range(1):
        assert body["state"] != "active"


def test_an_unreadable_answer_still_names_a_state_so_the_page_has_one_shape(
    device, monkeypatch
):
    """Both the 200 and the 503 carry `state`, so the tile has no absent-field branch."""
    _stub_status(monkeypatch, device, stdout="garbage")
    body, _status = device.device_status_envelope()
    assert "state" in body
    assert "error" in body


def test_a_timeout_is_reported_not_hung(device, monkeypatch):
    """A status read must not be able to hang a page refresh."""
    import subprocess as _sp

    def fake_run(*_a, **_k):
        raise _sp.TimeoutExpired(cmd="idp-jit status", timeout=device._TIMEOUT_S)

    monkeypatch.setattr(device.subprocess, "run", fake_run)
    body, status = device.device_status_envelope()
    assert status == 503
    assert body["state"] == "unreadable"
    assert "timed out" in body["error"]


def test_the_route_is_registered_and_read_only(device):
    """GET only, and present in both the path constants and the launcher.

    A route that existed in routes.py but not serve.py would 404, which is exactly the
    config-drift shape that cost an evening on 2026-09-18 (every POST to /api/proxy/fleetview/*
    404'd because the loaded config predated the change). Checking both files here means the
    pair cannot drift silently again for this path.
    """
    routes = _load(ROUTES_MODULE, "fleetview_routes_device_under_test")
    assert routes.DEVICE_STATUS_PATH == "/device-status"
    assert hasattr(routes, "device_status_envelope")

    serve_src = (
        REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "serve.py"
    ).read_text()
    assert "routes.DEVICE_STATUS_PATH" in serve_src, (
        "the path is declared in routes.py but serve.py does not register it, so it would 404"
    )
    assert "@app.get(routes.DEVICE_STATUS_PATH)" in serve_src, (
        "the device status route must be GET; a POST would need the proxy's allowedMethods "
        "to carry it and would be the same drift in a different place"
    )


def test_the_command_run_is_the_one_the_runbook_names(device, monkeypatch):
    """It shells out to bin/idp-jit with `status`, not to a second implementation."""
    seen: dict = {}

    def fake_run(argv, **_k):
        seen["argv"] = argv

        class _P:
            stdout = json.dumps({"state": "active", "expires_in": 60})
            stderr = ""
            returncode = 0

        return _P()

    monkeypatch.setattr(device.subprocess, "run", fake_run)
    device.device_status_envelope()
    argv = seen["argv"]
    assert str(argv[1]).endswith("bin/idp-jit"), f"expected bin/idp-jit, got {argv}"
    assert argv[2] == "status", f"expected the status subcommand, got {argv}"
