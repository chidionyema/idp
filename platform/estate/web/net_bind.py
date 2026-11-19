"""net_bind -- bind a web agent to a live protocol session at the network boundary.

A browser agent (the DSH web console, a headless browser, any HTTP client) reaches the estate
through this door or not at all. The door refuses, before any application logic runs:

  1. NO SESSION      no bearer/cookie -> 401, the request never reaches the app
  2. EXPIRED SESSION a session past its deadline -> 403
  3. WRONG TICKET    a session that is not bound to the instruction being acted on -> 403
  4. REPLAY          a nonce already spent by another request -> 409

Everything else is forwarded unchanged. The point is not to inspect the payload; it is that an
unbound client has no path to the application at all.

The four refusals are the same four attack cases the estate's own web proof requires.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

SESSION_DIR = pathlib.Path.home() / ".estate" / "web-sessions"


def _load(token: str) -> dict | None:
    if not token or not token.replace("-", "").isalnum():
        return None
    path = SESSION_DIR / f"{token}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def bind(token: str, instruction_id: str = "", now: float | None = None) -> tuple[bool, str]:
    """Whether this client is bound to a live session, and why not when it is not."""
    now = time.time() if now is None else now
    session = _load(token)
    if session is None:
        return False, "NO_SESSION"
    if float(session.get("expires_at", 0)) <= now:
        return False, "EXPIRED_SESSION"
    bound_to = session.get("instruction_id", "")
    if instruction_id and bound_to and bound_to != instruction_id:
        return False, "WRONG_TICKET"
    return True, "BOUND"


def spend_nonce(token: str, nonce: str) -> tuple[bool, str]:
    """A nonce may be spent once. A second presentation is a replay, not a retry."""
    if not nonce:
        return False, "REPLAY"
    seen = SESSION_DIR / f"{token}.nonces"
    spent = set(seen.read_text().split()) if seen.exists() else set()
    if nonce in spent:
        return False, "REPLAY"
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    with seen.open("a") as fh:
        fh.write(f"{nonce}\n")
    return True, "FRESH"


def open_session(instruction_id: str, ttl_s: int = 3600) -> str:
    """Mint a session for one instruction. The id is random, not derived from the ticket."""
    import secrets

    token = secrets.token_hex(16)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    (SESSION_DIR / f"{token}.json").write_text(
        json.dumps(
            {
                "instruction_id": instruction_id,
                "issued_at": time.time(),
                "expires_at": time.time() + ttl_s,
                "digest": hashlib.sha256(token.encode()).hexdigest()[:16],
            }
        )
    )
    return token
