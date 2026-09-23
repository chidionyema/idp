"""Langfuse tracing, guarded. If LANGFUSE_* is absent the whole module is a
no-op that logs once to stderr and never raises -- a missing trace backend
must never take a session down (cp5 wants the trace when Langfuse is
configured; cp1-cp3 must pass with it entirely absent).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import config_keys as ck

_warned = False
_warn_lock = threading.Lock()
_client = None
_client_lock = threading.Lock()


def _warn_once(msg: str) -> None:
    global _warned
    with _warn_lock:
        if _warned:
            return
        _warned = True
        print(f"[sovereign.tracing] {msg}", file=sys.stderr)


def _get_client():
    global _client
    if not configured():
        _warn_once("LANGFUSE_* not configured; tracing is a no-op")
        return None
    with _client_lock:
        if _client is not None:
            return _client
        try:
            from langfuse import Langfuse  # type: ignore

            _client = Langfuse(
                host=config.LANGFUSE_HOST,
                public_key=config.LANGFUSE_PUBLIC_KEY,
                secret_key=config.LANGFUSE_SECRET_KEY,
            )
        except Exception as exc:  # pragma: no cover - defensive, never fatal
            _warn_once(f"langfuse client unavailable ({exc}); tracing is a no-op")
            _client = None
        return _client


# ---------------------------------------------------------------------------
# R33 / spec v1.0 section 5: "Every Langfuse entry is signed against the
# session Merkle root. Fake entries fail verification."
#
# Langfuse is a separate service with its own database. Anyone who can
# reach its API can write a trace saying a session did something it did
# not do, and nothing in the trace itself would contradict the receipt
# chain -- the two stores had no shared value. anchor() supplies one: the
# shadow DAG's current Merkle root and the receipt chain's current head
# hash, HMAC-signed under the same estate key that signs receipts.
#
# A fake entry can carry any root it likes; it cannot carry a signature
# over that root, because the key never leaves the Keychain. verify()
# recomputes and compares, so an entry that was not produced here fails.
# ---------------------------------------------------------------------------

_ANCHOR_FIELDS = ("session_id", "merkle_root", "receipt_hash", "status")


def configured() -> bool:
    return bool(config.LANGFUSE_HOST and config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY)


def last_ok_path() -> Path:
    """Marker file recording when Langfuse last accepted a flush. Read by
    sovereign/engine/termination.py to enforce blind.halt_after_min, which
    is the config key that had no reader before R32."""
    return config.SOVEREIGN_HOME / str(ck.get("tracing.last_ok_filename"))


def _record_flush_ok() -> None:
    path = last_ok_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps({"ts": time.time()}))
        os.replace(tmp, path)
    except OSError:  # pragma: no cover - a marker is never worth an exception
        pass


def merkle_root() -> str:
    """The session Merkle root: cp9's shadow_main head. Empty string when
    nothing has been drained into the DAG yet -- an honest "no root", not
    a fabricated one."""
    try:
        from sovereign.engine import shadow_root

        head_path = shadow_root.head_path()
        if not head_path.exists():
            return ""
        return str(json.loads(head_path.read_text()).get("root") or "")
    except Exception:  # pragma: no cover - tracing must never raise
        return ""


def receipt_head() -> str:
    """The hash of the last line of the signed receipt chain."""
    try:
        from sovereign.engine import receipts as receipts_mod

        rows = receipts_mod.read_all()
        return str(rows[-1].get("hash") or "") if rows else ""
    except Exception:  # pragma: no cover - tracing must never raise
        return ""


def anchor(session_id: str, status: str) -> dict[str, Any]:
    """The block every trace entry carries: the two roots, and a signature
    over them under the receipt key."""
    body = {
        "session_id": session_id,
        "merkle_root": merkle_root(),
        "receipt_hash": receipt_head(),
        "status": status,
    }
    signature = ""
    try:
        from sovereign.engine import receipts as receipts_mod

        key, _backend = receipts_mod.get_or_create_key()
        signature = hmac.new(key, config.canonical_json(body), hashlib.sha256).hexdigest()
    except Exception:  # pragma: no cover - an unsigned anchor is still honest
        signature = ""
    return {**body, str(ck.get("trace.signature_field")): signature}


def verify(entry: dict[str, Any]) -> bool:
    """True only if `entry`'s signature really covers the roots it claims.
    A fabricated entry fails here, which is the whole point -- an entry
    with no signature field is False, not "unverified but fine"."""
    if not entry:
        return False
    field = str(ck.get("trace.signature_field"))
    claimed = str(entry.get(field) or "")
    if not claimed:
        return False
    body = {k: entry.get(k) for k in _ANCHOR_FIELDS}
    try:
        from sovereign.engine import receipts as receipts_mod

        key, _backend = receipts_mod.get_or_create_key()
    except Exception:
        return False
    expected = hmac.new(key, config.canonical_json(body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, claimed)


def trace_session(session_id: str, task: str, runner: str, status: str, extra: dict[str, Any] | None = None) -> None:
    """Best-effort: record one trace/event per session state change. Never
    raises -- a trace backend outage must not touch a session's status.

    Every entry carries anchor(): the session Merkle root, the receipt
    chain head, and a signature over both (R33)."""
    client = _get_client()
    if client is None:
        return
    entry_anchor = anchor(session_id, status)
    try:
        client.trace(
            name="sovereign-session",
            id=session_id,
            tags=[session_id, f"runner:{runner}", f"status:{status}"],
            input={"task": task, "runner": runner},
            output={"status": status, **(extra or {})},
            metadata=entry_anchor,
        )
        client.flush()
        _record_flush_ok()
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"langfuse trace failed ({exc}); continuing without it")
