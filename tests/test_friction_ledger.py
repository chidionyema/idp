"""The friction ledger: every refusal and ceiling kill recorded as it happens, counted as a shape.

Why this file exists. The 24h census (docs/diagnoses/2026-10-23-agent-process-friction.yaml) found
1,277 polls of an answer a door already had -- by reading transcripts afterwards. That is an audit:
true, and too late to steer anything. A goal/reward signal and an eval process need the other kind
of number, one written at the instant the door acts, in a shape that can be counted without
judgement. This file grades that ledger: what it records, what it must never change, and that a
repetition collapses to one countable key.

The ledger is also the place a guard-versus-guard failure becomes visible. Three commits were
SIGTERMed at the door's 100s ceiling on 2026-10-23 because a hook's own budget was 115s (idp#7013);
nothing recorded it, so it was rediscovered from job logs. A `ceiling-kill` row is that fact,
written once, where a dashboard can rank it.

Everything here is offline: the module is loaded by path, the ledger path is a temporary file, and
nothing touches a daemon or a network (LAW 45).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "mcp" / "plugins" / "estate_executor.py"
OBSERVE = ROOT / "bin" / "pi-observe"


def _door():
    spec = importlib.util.spec_from_file_location("estate_executor_friction", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The door now refuses work below a free-space floor (added 2026-10-23, when the laptop reached
    # 197 MB free and kept accepting jobs). These tests are about the friction ledger, so they
    # declare a volume with room and the floor is out of the way; the floor has its own suite in
    # tests/test_door_refuses_a_full_volume.py.
    module._free_mb = lambda path="/": 500_000
    return module


@pytest.fixture(name="ledger")
def _ledger(tmp_path, monkeypatch):
    """A ledger in a temporary directory, and the door pointed at it."""
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("ESTATE_FRICTION", str(path))
    # LAW 45: this suite is offline. The bus is opted out here and opted back in only by the three
    # tests below that are about publishing, one of which brings its own broker.
    monkeypatch.setenv("ESTATE_BUS_URL", "off")
    return path


def _rows(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- what it records -------------------------------------------------------------------------


def test_a_steered_poll_is_recorded_with_the_door_that_answers_it(ledger):
    door = _door()
    answer = door.execute_command("gh api repos/x/y/commits/abc1234/status")
    assert answer["accepted"] is False
    rows = _rows(ledger)
    assert [r["kind"] for r in rows] == ["steer"]
    assert "lane-where" in rows[0]["detail"]
    assert rows[0]["shape"] == "gh api repos/x/y/commits/<sha>/status"


def test_a_bare_wait_is_recorded_as_its_own_kind(ledger):
    door = _door()
    door.execute_command("sleep 900")
    assert [r["kind"] for r in _rows(ledger)] == ["refuse-wait"]


def test_a_paced_wait_is_accepted_and_still_recorded(ledger):
    """The estate's own idiom: launch, then check. Allowed, and counted.

    MEASURED 2026-10-24: the door refused 26 jobs in 17 minutes, every one of them a `nohup …`
    followed by `sleep 30`. Raising the parking line fixed the refusals and silently dropped the
    measurement -- an accepted pace wrote no row, so the seconds agents spend waiting inside the
    door were invisible. A reward signal cannot rank a delay nobody recorded.
    """
    door = _door()
    answer = door.execute_command(
        "nohup true > /tmp/x.log 2>&1 & sleep 30; tail -n 3 /tmp/x.log"
    )
    assert answer.get("refused") is not True, answer
    rows = _rows(ledger)
    assert [r["kind"] for r in rows] == ["pace-wait"]
    assert rows[0]["detail"] == "sleep 30"
    # The shape is the reducer's own output, not a wish: it keeps the verb and stops at the first
    # redirection. Asserting the real shape keeps this test honest about what gets ranked.
    assert rows[0]["shape"].startswith("nohup")


def test_a_ceiling_above_the_cap_is_recorded(ledger):
    door = _door()
    # `timeout 900` is the spelling the gate reads (explicit_ceiling_sec); `--ceiling` is not a
    # flag it knows, and a test that invents one would be grading its own imagination.
    answer = door.execute_command("timeout 900 bin/idp-ci")
    assert answer["accepted"] is False
    kinds = [r["kind"] for r in _rows(ledger)]
    assert kinds == ["refuse-ceiling"]


def test_a_ceiling_kill_is_recorded_once_per_job(ledger):
    """The class that cost three commits: the door killed the job, nobody wrote it down."""
    door = _door()
    door._report_failure(
        "job-1", "IDP_CI_FAST=1 bin/idp-ci", None, 124, "…\nSIGTERMed at the ceiling"
    )
    rows = _rows(ledger)
    assert [(r["kind"], r["ceiling_sec"]) for r in rows] == [
        ("ceiling-kill", door.CEILING_SEC)
    ]
    assert "SIGTERMed at the ceiling" in rows[0]["detail"]


def test_a_clean_exit_records_nothing(ledger):
    door = _door()
    door._report_failure("job-2", "bin/lane-where lane/x", None, 0, "")
    assert _rows(ledger) == []


# --- what it must never do -------------------------------------------------------------------


def test_an_unwritable_ledger_does_not_change_the_door_s_answer(tmp_path, monkeypatch):
    """A guard in front of the door cannot be worse than the defect it observes (R38)."""
    blocked = tmp_path / "not-a-file"
    blocked.mkdir()
    monkeypatch.setenv("ESTATE_FRICTION", str(blocked))
    door = _door()
    answer = door.execute_command("sleep 900")
    assert answer["accepted"] is False
    assert "waits on something outside the process" in answer["error"]


def test_the_ledger_holds_no_path_beyond_the_one_in_the_shape(ledger):
    """Shapes are countable identities. A receipt that keeps a full path keeps the incident, not
    the pattern -- and the pattern is what a reward signal can act on."""
    door = _door()
    door.execute_command(
        "while true; do git -C /Users/someone/Documents/code/idp fetch origin; sleep 5; done"
    )
    row = _rows(ledger)[0]
    assert "/Users/" not in row["shape"]
    assert "<path>" in row["shape"]


# --- how a repetition becomes a number -------------------------------------------------------


def test_two_identical_polls_are_one_countable_shape(ledger):
    door = _door()
    door.execute_command("gh api repos/x/y/commits/aaa1111/status")
    door.execute_command("gh api repos/x/y/commits/bbb2222/status")
    rows = _rows(ledger)
    assert len(rows) == 2
    assert {r["shape"] for r in rows} == {"gh api repos/x/y/commits/<sha>/status"}


def test_a_loop_keeps_the_command_it_repeats():
    """`for i in` is true of every loop, so it is useless as a key: the 145 census calls were all
    one question with different counters."""
    door = _door()
    observed = (
        'for i in $(seq 1 40); do if git log -1 --format=%s | grep -q "^feat"; '
        "then break; fi; sleep 2; done"
    )
    assert door.command_shape(observed).startswith("for <loop> do ")
    assert "if git log" in door.command_shape(observed)


# --- the reader: the number, not the file ----------------------------------------------------


def _observe(path: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(OBSERVE),
            "--friction",
            "--friction-path",
            str(path),
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_the_reader_ranks_repeated_friction(ledger):
    door = _door()
    for sha in ("aaa1111", "bbb2222", "ccc3333"):
        door.execute_command(f"gh api repos/x/y/commits/{sha}/status")
    door.execute_command("sleep 900")
    out = _observe(ledger)
    assert out.returncode == 0, out.stderr
    assert "4 event(s)" in out.stdout
    assert "steer=3, refuse-wait=1" in out.stdout
    assert "gh api repos/x/y/commits/<sha>/status" in out.stdout


def test_the_reader_says_so_when_there_is_nothing_rather_than_printing_zero_confidence(
    tmp_path,
):
    out = _observe(tmp_path / "absent.jsonl")
    assert out.returncode == 0
    assert "none recorded" in out.stdout


def test_an_unreadable_ledger_is_blind_not_empty(tmp_path):
    """`no friction` and `no measurement` are different facts, and a reward signal depends on the
    difference: one is a zero worth trusting, the other is a hole."""
    directory = tmp_path / "a-directory"
    directory.mkdir()
    out = _observe(directory)
    assert out.returncode == 2
    assert "BLIND" in out.stdout


def test_the_reader_honours_the_window(ledger):
    old = {
        "ts": "2020-01-01T00:00:00Z",
        "kind": "steer",
        "shape": "gh api repos/x/y/commits/<sha>/status",
        "detail": "old",
    }
    new = {
        "ts": "2999-01-01T00:00:00Z",
        "kind": "steer",
        "shape": "gh run view <n>",
        "detail": "new",
    }
    ledger.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    out = _observe(ledger)
    assert "1 event(s)" in out.stdout
    assert "gh run view <n>" in out.stdout


# --- the bus: the ledger's copy that leaves this machine ---------------------------------------


def _fake_broker():
    """A broker that speaks just enough protocol to be a witness, not a simulation.

    It sends INFO, reads the PUB line and its payload, and answers the PING with PONG -- the same
    acknowledgement a real server gives. The received payload is the evidence: a test that only
    checked `bus_publish() is True` would grade a socket, not a publish.
    """
    import socket
    import threading

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    received: list[bytes] = []

    def serve():
        conn, _ = listener.accept()
        with conn:
            conn.sendall(b'INFO {"server_id":"fake","proto":1}\r\n')
            buf = b""
            pub_line = None
            body_start = 0
            # The client sends CONNECT, then the PUB. Find the PUB line itself rather than assuming
            # the first line in the buffer is the one carrying the payload size.
            while pub_line is None:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                at = buf.find(b"PUB ")
                end = buf.find(b"\r\n", at) if at != -1 else -1
                if end != -1:
                    pub_line = buf[at:end]
                    body_start = end + 2
            if pub_line is not None:
                size = int(pub_line.rsplit(b" ", 1)[1])
                body = buf[body_start:]
                while len(body) < size:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    body += chunk
                received.append(body[:size])
            conn.sendall(b"PONG\r\n")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return listener.getsockname(), received, listener, thread


def test_a_recorded_event_reaches_the_bus(ledger, monkeypatch):
    (host, port), received, listener, thread = _fake_broker()
    monkeypatch.setenv("ESTATE_BUS_URL", f"nats://{host}:{port}")
    try:
        door = _door()
        door.record_friction("refuse-wait", "sleep 30", detail="sleep 30")
        thread.join(timeout=2)
    finally:
        listener.close()
    assert received, "no publish reached the broker"
    published = json.loads(received[0])
    on_disk = _rows(ledger)
    assert published["kind"] == "refuse-wait"
    # The bus carries exactly the row the file holds: two copies of one record, not two records.
    assert published == on_disk[0]


def test_the_ledger_is_written_when_the_bus_is_unreachable(ledger, monkeypatch):
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    dead_port = probe.getsockname()[1]
    probe.close()  # a port nothing listens on: the bus is down, not absent
    monkeypatch.setenv("ESTATE_BUS_URL", f"nats://127.0.0.1:{dead_port}")
    door = _door()
    assert door.bus_publish("estate.friction.v1", b"{}") is False
    door.record_friction("refuse-wait", "sleep 30")
    assert [r["kind"] for r in _rows(ledger)] == ["refuse-wait"]


def test_publishing_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("ESTATE_BUS_URL", "off")
    door = _door()
    assert door.bus_publish("estate.friction.v1", b"{}") is False
