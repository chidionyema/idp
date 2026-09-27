"""The firewall's decisions are published live, and a blocker needs an intent run behind it.

Founder, 2026-09-27: a safeguard is operational only when /fleet shows it deciding on real agent
actions as they happen; and "any blocker claimed needs evidence by intent". Until then the gate
recorded nothing anywhere, and a session reported "blocked on the vault" with nothing run behind
it. Runs the real bin/epistemic_firewall.py as the Stop hook, against a real socket that speaks the
NATS wire protocol, and grades the row it publishes against the estate.agent.event contract.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
FIREWALL = ROOT / "bin/epistemic_firewall.py"
SCHEMA = json.loads(
    (ROOT / "platform/event-bus/contract/estate.agent.event.json").read_text()
)


def _prompt(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _say(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _bash(n: int, command: str, output: str) -> list[dict]:
    uid = f"toolu_{n}"
    return [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": uid,
                        "name": "Bash",
                        "input": {"command": command},
                    }
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": uid, "content": output}
                ],
            },
        },
    ]


class FakeNats:
    """Just enough of the NATS server protocol: INFO, then PONG to PING, recording each PUB."""

    def __init__(self) -> None:
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.published: list[tuple[str, dict]] = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                conn.sendall(b'INFO {"server_id":"fake"}\r\n')
                f = conn.makefile("rb")
                while True:
                    line = f.readline()
                    if not line:
                        break
                    if line.startswith(b"PUB "):
                        _, subject, size = line.split()
                        data = f.read(int(size))
                        f.readline()
                        self.published.append((subject.decode(), json.loads(data)))
                    elif line.startswith(b"PING"):
                        conn.sendall(b"PONG\r\n")


def _stop(
    tmp_path: Path, lines: list[dict], session_id: str = "", nats: str = ""
) -> str:
    t = tmp_path / "session.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    payload = {"transcript_path": str(t), "stop_hook_active": False}
    if session_id:
        payload["session_id"] = session_id
    env = {
        **os.environ,
        "ESTATE_GATE_LEDGER": str(tmp_path / "decisions.jsonl"),
        "NATS_URL": nats or "nats://127.0.0.1:1",
    }
    r = subprocess.run(
        [sys.executable, str(FIREWALL), "--stop-hook"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_a_blocker_with_no_intent_run_is_handed_back(tmp_path):
    out = _stop(
        tmp_path, [_prompt("status"), _say("The secrets row is blocked on the vault.")]
    )
    assert json.loads(out)["decision"] == "block"
    assert "intent" in json.loads(out)["reason"]


def test_a_blocker_with_an_intent_run_behind_it_passes(tmp_path):
    turn = [
        _prompt("status"),
        *_bash(
            1,
            "estate-execute k8s-externalsecrets",
            "human-groq  False  SecretSyncedError",
        ),
        _say("The secrets row is blocked: human-groq reads SecretSyncedError."),
    ]
    assert _stop(tmp_path, turn) == ""


def test_saying_nothing_is_blocked_is_not_a_blocker(tmp_path):
    turn = [
        _prompt("status"),
        _say("Nothing is blocked; the next step is the drift fix."),
    ]
    assert _stop(tmp_path, turn) == ""


def test_every_decision_is_published_live_on_the_contract(tmp_path):
    bus = FakeNats()
    url = f"nats://127.0.0.1:{bus.port}"
    _stop(tmp_path, [_prompt("hi"), _say("Reading the PR now.")], "s-pass", url)
    _stop(
        tmp_path, [_prompt("st"), _say("This is blocked on the cluster.")], "s-ref", url
    )

    assert [s for s, _ in bus.published] == [
        "estate.agent.claude-code.s-pass.gate",
        "estate.agent.claude-code.s-ref.gate",
    ]
    for _, row in bus.published:
        jsonschema.validate(row, SCHEMA)
    passed, refused = (row["gate"] for _, row in bus.published)
    assert passed == {"name": "epistemic-firewall", "verdict": "pass"}
    assert refused["verdict"] == "refuse"
    assert refused["claim"] == "This is blocked on the cluster."

    ledger = [
        json.loads(x) for x in (tmp_path / "decisions.jsonl").read_text().splitlines()
    ]
    assert [r["bus"] for r in ledger] == ["published", "published"]


def test_a_bus_that_is_down_is_on_the_ledger_and_never_breaks_the_hook(tmp_path):
    assert _stop(tmp_path, [_prompt("hi"), _say("Reading.")], "s-down") == ""
    (row,) = [
        json.loads(x) for x in (tmp_path / "decisions.jsonl").read_text().splitlines()
    ]
    assert row["bus"].startswith("unpublished:")
    assert row["gate"]["verdict"] == "pass"


def test_a_payload_with_no_session_publishes_nothing(tmp_path):
    bus = FakeNats()
    _stop(
        tmp_path, [_prompt("hi"), _say("Reading.")], "", f"nats://127.0.0.1:{bus.port}"
    )
    assert bus.published == []
    assert not (tmp_path / "decisions.jsonl").exists()
