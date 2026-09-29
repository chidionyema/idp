"""platform/llm/action_ledger.py: every router call becomes one Ed25519-signed action chained to
the one before it, in the row shape of agent_actions, and queued for the bus in the exact table
the fleetview outbox worker drains. A ledger that has been edited stops verifying at the edit."""

from __future__ import annotations

import base64
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "action_ledger", ROOT / "platform/llm/action_ledger.py"
)
al = importlib.util.module_from_spec(spec)
sys.modules["action_ledger"] = al
spec.loader.exec_module(al)


@pytest.fixture
def estate(tmp_path, monkeypatch):
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    (tmp_path / "agent.pem").write_bytes(pem)
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(tmp_path / "agent.pem"))
    monkeypatch.setenv("ESTATE_ACTION_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))
    al._KEY = None
    return tmp_path


def _call(session="sess-1", ua="claude-code/2.1", text="hi"):
    return {
        "model": "claude-sonnet",
        "messages": [{"role": "user", "content": text}],
        "litellm_params": {
            "metadata": {},
            "proxy_server_request": {
                "method": "POST",
                "url": "http://127.0.0.1:4000/v1/messages",
                "headers": {"user-agent": ua},
                "body": {
                    "model": "claude-sonnet",
                    "messages": [{"role": "user", "content": text}],
                    "metadata": {"user_id": json.dumps({"session_id": session})},
                },
            },
        },
    }


def test_every_call_is_signed_chained_and_queued(estate):
    r1 = al.record(_call(text="one"), {"content": [{"type": "text", "text": "a"}]})
    r2 = al.record(_call(text="two"), {"content": [{"type": "text", "text": "b"}]})
    assert r1["parent"] == "0" * 64
    lines = (estate / "ledger.jsonl").read_bytes().splitlines()
    assert r2["parent"] == al._sha(lines[0])
    assert r1["agent_id"].startswith("urn:estate:agent:claude-code:")
    assert r1["session_id"] == "sess-1" and r1["intent_name"] == "llm:claude-sonnet"
    assert r1["args_hash"] != r2["args_hash"] and r1["result_hash"] != r2["result_hash"]
    pub = al._key().public_key()
    pub.verify(
        base64.b64decode(r1["signature"]),
        al.canonical_string(
            "POST",
            "/v1/messages",
            r1["created_at"],
            r1["args_hash"],
            r1["agent_id"],
            "sess-1",
        ),
    )
    assert al.verify() == (2, "")
    con = sqlite3.connect(estate / "outbox.db")
    rows = con.execute(
        "select session_id, runtime, kind, phase, status, payload from outbox order by id"
    ).fetchall()
    assert [r[:5] for r in rows] == [
        ("sess-1", "claude-code", "tool", "executing", "pending")
    ] * 2
    ev = json.loads(rows[1][5])
    assert (
        ev["tool"]["signature"] == r2["signature"]
        and ev["tool"]["parent"] == r2["parent"]
    )
    assert set(ev) >= {"session_id", "runtime", "kind", "at", "phase", "tool"}


def test_an_edited_ledger_stops_verifying_at_the_edit(estate):
    for t in ("one", "two", "three"):
        al.record(_call(text=t), {"content": [{"type": "text", "text": t}]})
    p = estate / "ledger.jsonl"
    lines = p.read_text().splitlines()
    row = json.loads(lines[1])
    row["intent_name"] = "llm:something-else"
    lines[1] = json.dumps(row, sort_keys=True, separators=(",", ":"))
    p.write_text("\n".join(lines) + "\n")
    # the chain breaks at the line AFTER the edit: its parent no longer hashes the edited line
    n, why = al.verify()
    assert n == 2 and "line 3" in why
    row["signature"] = base64.b64encode(b"\0" * 64).decode()
    lines[1] = json.dumps(row, sort_keys=True, separators=(",", ":"))
    p.write_text("\n".join(lines) + "\n")
    assert al.verify() == (1, "line 2: signature invalid")


def test_the_drain_and_a_missing_key_never_break_the_call(estate, monkeypatch):
    assert al.record(_call(ua="Python-urllib/3.9"), {}) is None
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(estate / "absent.pem"))
    al._KEY = None
    with pytest.raises(FileNotFoundError):
        al.record(_call(), {})
    import asyncio

    asyncio.run(
        al.proxy_handler_instance.async_log_success_event(_call(), {}, 0, 0)
    )  # logged, not raised
