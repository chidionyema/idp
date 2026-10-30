"""idp#7481: proof against a real throwaway nats-server (no mocks)."""

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = Path.home() / ".cache/estate-tools/nats-server"


@pytest.fixture()
def bus(tmp_path):
    if not SERVER.exists():
        pytest.skip("no nats-server")
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    p = subprocess.Popen(
        [str(SERVER), "-js", "-sd", str(tmp_path), "-a", "127.0.0.1", "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    yield f"nats://127.0.0.1:{port}"
    p.terminate()


def run(url, agent, *args):
    env = {
        **os.environ,
        "ESTATE_NATS_URL": url,
        "ESTATE_AGENT": agent,
        "ESTATE_FLEET_ACK_WAIT": "1",
        "ESTATE_FLEET_NO_MEMORY": "1",
    }
    return subprocess.run(
        [str(ROOT / "bin/estate-fleet"), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_late_agent_gets_broadcast_and_redelivery_until_ack(bus):
    assert run(bus, "founder", "broadcast", "never repeat yourself").returncode == 0
    r = run(bus, "late-agent", "inbox")  # joined after the send
    assert "never repeat yourself" in r.stdout
    time.sleep(1.5)  # not acked: must come again
    assert "never repeat yourself" in run(bus, "late-agent", "inbox", "--ack").stdout
    time.sleep(1.5)
    assert "0 pending" in run(bus, "late-agent", "inbox").stdout  # acked: gone


def test_direct_message_reaches_only_its_target(bus):
    run(bus, "pi", "send", "codex", "take #7387")
    assert "take #7387" in run(bus, "codex", "inbox").stdout
    assert "take #7387" not in run(bus, "claude-code", "inbox").stdout


def test_unreachable_bus_is_blind_not_empty(bus):
    r = run("nats://127.0.0.1:1", "x", "inbox")
    assert r.returncode == 2 and "BLIND" in r.stdout


def test_send_rejects_flag_as_agent():
    """`send --to x text` used to store a message on estate.fleet.to.--to; it must refuse (#7481)."""
    import subprocess, sys
    from pathlib import Path

    fleet = Path(__file__).resolve().parent.parent / "bin" / "estate-fleet"
    r = subprocess.run(
        [sys.executable, str(fleet), "send", "--to", "x", "hello"],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "nothing was sent" in r.stderr
