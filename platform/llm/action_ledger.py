"""Every call through the laptop router becomes one signed, chained action. Agents are not asked.

Registered (laptop only, by bin/litellm-local) as action_ledger.proxy_handler_instance.

WHY. The estate's accountability substrate (cmd/elpis-proxy, schema/identity0_registry.sql) makes
an agent opaque but attributable: every action signed by a key the agent never holds, chained
to the action before it, recorded where the agent cannot edit. That substrate runs as a pod
sidecar; today's agents run on this laptop, and the one place every one of them passes -- Claude
Code, pi, opencode, the drains -- is this router. So until the laptop exit lands, the router is
the laptop's Elpis (founder 2026-09-29, crew#983): it signs here, and nothing else is the record.

WHAT. On each successful call, in the request's own process but never on its path of failure:

  1. the canonical string Elpis signs, byte for byte (Method\\nURI\\nTimestamp\\nBodyHash\\n
     AgentURN\\nSessionID), signed Ed25519 with ~/.estate/keys/agent.pem -- a file the router
     process reads and no harness does;
  2. one line appended to ~/.estate/action-ledger.jsonl in the shape of an agent_actions row
     (agent_id, session_id, intent_name, args_hash, result_hash, created_at, signature,
     parent = sha256 of the previous line), so the file is a hash chain: edit a line and every
     line after it stops verifying;
  3. the same action enqueued in the fleetview outbox, which the running fleetview backend
     drains onto JetStream as estate.agent.<runtime>.<session>.tool -- the subject the Fleet
     director and the unified memory server consume. One event, three consumers.

Never raises into the request: a ledger that cannot write logs the reason and the call still
answers. Not captured: the graph drain's own calls (User-Agent Python-urllib), like graph_capture.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import socket
import sqlite3
import time
from typing import Any

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # importable without litellm (tests)

    class CustomLogger:  # type: ignore[no-redef]
        pass


log = logging.getLogger("action_ledger")
RUNTIMES = ("claude-code", "sovereign", "cyrus", "otto", "dagster", "github-actions")


def key_path() -> str:
    return os.path.expanduser(
        os.environ.get("ESTATE_AGENT_KEY") or "~/.estate/keys/agent.pem"
    )


def ledger_path() -> str:
    return os.path.expanduser(
        os.environ.get("ESTATE_ACTION_LEDGER") or "~/.estate/action-ledger.jsonl"
    )


def outbox_path() -> str:
    return os.path.expanduser(os.environ.get("OUTBOX_DB_PATH") or "~/.estate/outbox.db")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(body: dict) -> bytes:
    # The proxy puts datetimes in the request it hands callbacks; without default=str every such
    # call raised "Object of type datetime is not JSON serializable" and the ledger stayed empty.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()


_KEY: Any = None


def _key():
    """The Ed25519 private key, loaded once; None (with the reason logged) when absent."""
    global _KEY
    if _KEY is None:
        from cryptography.hazmat.primitives import serialization

        with open(key_path(), "rb") as f:
            _KEY = serialization.load_pem_private_key(f.read(), password=None)
    return _KEY


def canonical_string(
    method: str, uri: str, timestamp: str, body_hash: str, agent: str, session: str
) -> bytes:
    """Exactly what cmd/elpis-proxy signs: six newline-delimited fields, no trailing newline."""
    return "\n".join((method, uri, timestamp, body_hash, agent, session)).encode()


def sign(canonical: bytes) -> str:
    return base64.b64encode(_key().sign(canonical)).decode()


def public_key_pem() -> str:
    from cryptography.hazmat.primitives import serialization

    return (
        _key()
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )


def _request(kwargs: dict) -> dict:
    return (kwargs.get("litellm_params") or {}).get("proxy_server_request") or {}


def _session(kwargs: dict) -> str:
    meta = (kwargs.get("litellm_params") or {}).get("metadata") or {}
    uid = meta.get("user_api_key_end_user_id") or ""
    body = _request(kwargs).get("body") or {}
    raw = (
        (body.get("metadata") or {}).get("user_id") if isinstance(body, dict) else None
    )
    if isinstance(raw, str):
        try:
            uid = json.loads(raw).get("session_id") or uid
        except (ValueError, AttributeError):
            uid = raw
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(uid or "no-session"))[:64]


def _runtime(kwargs: dict) -> str:
    ua = str((_request(kwargs).get("headers") or {}).get("user-agent", "")).lower()
    for r in RUNTIMES:
        if r in ua:
            return r
    return ua.split("/")[0][:32] or "unknown"


def _is_drain(kwargs: dict) -> bool:
    ua = str((_request(kwargs).get("headers") or {}).get("user-agent", ""))
    return ua.startswith("Python-urllib")


def _result_hash(kwargs: dict, response_obj: Any) -> str:
    for r in (
        kwargs.get("complete_streaming_response"),
        (kwargs.get("standard_logging_object") or {}).get("response"),
        response_obj,
    ):
        if r is None:
            continue
        if hasattr(r, "model_dump"):
            r = r.model_dump()
        try:
            return _sha(_canonical(r if isinstance(r, dict) else {"raw": str(r)}))
        except (TypeError, ValueError):
            return _sha(str(r).encode())
    return _sha(b"")


def _last_hash(path: str) -> str:
    """sha256 of the last line of the ledger, or the genesis value when the ledger is empty."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            if end == 0:
                return "0" * 64
            f.seek(max(0, end - 65536))
            tail = f.read().splitlines()
            return _sha(tail[-1]) if tail else "0" * 64
    except FileNotFoundError:
        return "0" * 64


def record(kwargs: dict, response_obj: Any) -> dict | None:
    """Sign this call, chain it into the ledger, enqueue it for the bus. Returns the row."""
    if _is_drain(kwargs):
        return None
    req = _request(kwargs)
    body = req.get("body") if isinstance(req.get("body"), dict) else {}
    body_hash = _sha(_canonical(body))
    method = str(req.get("method") or "POST").upper()
    uri = str(req.get("url") or "/v1/messages")
    uri = re.sub(r"^https?://[^/]+", "", uri) or "/"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    runtime = _runtime(kwargs)
    session = _session(kwargs)
    agent = f"urn:estate:agent:{runtime}:{socket.gethostname().split('.')[0]}"
    signature = sign(canonical_string(method, uri, stamp, body_hash, agent, session))
    path = ledger_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = {
        "agent_id": agent,
        "session_id": session,
        "intent_name": f"llm:{kwargs.get('model', '')}",
        "method": method,
        "uri": uri,
        "args_hash": body_hash,
        "result_hash": _result_hash(kwargs, response_obj),
        "created_at": stamp,
        "signature": signature,
        "parent": _last_hash(path),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    _enqueue(runtime, session, stamp, row)
    return row


def _enqueue(runtime: str, session: str, stamp: str, row: dict) -> None:
    """Same table, same columns as fleetview_backend.outbox.enqueue: its worker drains this."""
    event = {
        "session_id": session,
        "runtime": runtime,
        "kind": "tool",
        "phase": "executing",
        "at": stamp,
        "tool": {
            "name": row["intent_name"],
            "signature": row["signature"],
            "args_hash": row["args_hash"],
            "result_hash": row["result_hash"],
            "parent": row["parent"],
            "agent_id": row["agent_id"],
        },
    }
    con = sqlite3.connect(outbox_path(), timeout=2.0)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute(
            "CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " created_at REAL NOT NULL, session_id TEXT NOT NULL, runtime TEXT NOT NULL,"
            " kind TEXT NOT NULL, phase TEXT NOT NULL, payload TEXT NOT NULL,"
            " status TEXT NOT NULL DEFAULT 'pending', retries INTEGER NOT NULL DEFAULT 0,"
            " last_attempt_at REAL, next_attempt_at REAL, error TEXT)"
        )
        now = time.time()
        con.execute(
            "INSERT INTO outbox (created_at, session_id, runtime, kind, phase, payload,"
            " next_attempt_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now, session, runtime, "tool", "executing", json.dumps(event), now),
        )
        con.commit()
    finally:
        con.close()


def verify(path: str | None = None) -> tuple[int, str]:
    """Walk the ledger: every signature valid, every parent the hash of the line before.
    Returns (rows_verified, "") or (rows_before_break, reason)."""
    from cryptography.exceptions import InvalidSignature

    pub = _key().public_key()
    prev = "0" * 64
    n = 0
    with open(path or ledger_path(), "rb") as f:
        for line in f:
            line = line.rstrip(b"\n")
            row = json.loads(line)
            if row["parent"] != prev:
                return n, f"line {n + 1}: parent {row['parent'][:12]} != {prev[:12]}"
            try:
                pub.verify(
                    base64.b64decode(row["signature"]),
                    canonical_string(
                        row["method"],
                        row["uri"],
                        row["created_at"],
                        row["args_hash"],
                        row["agent_id"],
                        row["session_id"],
                    ),
                )
            except InvalidSignature:
                return n, f"line {n + 1}: signature invalid"
            prev = _sha(line)
            n += 1
    return n, ""


class ActionLedger(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            record(kwargs, response_obj)
        except Exception as exc:  # noqa: BLE001 - the ledger may never fail the request
            log.warning("[action_ledger] not recorded: %s", exc)


proxy_handler_instance = ActionLedger()

if __name__ == "__main__":
    import sys

    n, why = verify(sys.argv[1] if len(sys.argv) > 1 else None)
    print(
        f"{'ok' if not why else 'FAIL'}    action-ledger  {n} actions verified{'; ' + why if why else ''}"
    )
    sys.exit(1 if why else 0)
