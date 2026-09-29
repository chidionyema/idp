#!/usr/bin/env python3
"""
pobr-grant.py — PoBR grant gate.

Single-use, 5-minute TTL. Filesystem + timestamp only, no LLM.

Grant file lives at ~/.estate/pobr/GRANT-<session_id>.json
Schema:
    {
      "session_id": "<uuid>",
      "tool": "<tool_name>",
      "created_at": <unix_timestamp>,
      "expires_at": <unix_timestamp>,
      "used": false
    }

Gating rule: any tool name matching or prefixed with
  send_, emit_, reply_, notify_, message_
Never gate: pobr_submit, pobr_status
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

HOME = Path.home()
GRANT_DIR = HOME / ".estate" / "pobr"
GRANT_TTL_SECONDS = 300  # 5 minutes

_GATED_PATTERN = re.compile(r"^(send_|emit_|reply_|notify_|message_).*")
_NEVER_GATE = frozenset({"pobr_submit", "pobr_status"})


def _grant_file(session_id: str) -> Path:
    return GRANT_DIR / f"GRANT-{session_id}.json"


def requires_grant(tool_name: str) -> bool:
    """Return True if tool_name is gated by PoBR."""
    if tool_name in _NEVER_GATE:
        return False
    return bool(_GATED_PATTERN.match(tool_name))


def check_grant(session_id: str) -> dict:
    """
    Verify the grant is valid (exists, not expired, not used).
    Returns a dict with keys: valid (bool), reason (str).
    """
    grant_path = _grant_file(session_id)
    if not grant_path.exists():
        return {"valid": False, "reason": f"grant not found: {grant_path}"}

    try:
        with open(grant_path) as fh:
            grant = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        return {"valid": False, "reason": f"grant unreadable: {exc}"}

    now = time.time()
    if grant.get("used"):
        return {"valid": False, "reason": "grant already consumed"}

    expires_at = grant.get("expires_at", 0)
    if now > expires_at:
        return {"valid": False, "reason": "grant expired"}

    return {"valid": True, "reason": "ok", "grant": grant}


def _ensure_grant_dir() -> None:
    GRANT_DIR.mkdir(parents=True, exist_ok=True)


def pobr_submit_tool(session_id: str, receipt: dict) -> dict:
    """
    Consume a grant and submit the PoBR receipt.
    Never returns the receipt back — returns only a status.

    Returns {"ok": bool, "reason": str}
    """
    _ensure_grant_dir()

    # Consume the grant atomically
    grant_path = _grant_file(session_id)
    if not grant_path.exists():
        return {"ok": False, "reason": "no grant found for session"}

    try:
        with open(grant_path) as fh:
            grant = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "reason": f"grant unreadable: {exc}"}

    if grant.get("used"):
        return {"ok": False, "reason": "grant already consumed"}

    # Mark used
    grant["used"] = True
    grant["submitted_at"] = time.time()
    grant["receipt_id"] = receipt.get("receipt_id", str(uuid.uuid4()))

    try:
        with open(grant_path, "w") as fh:
            json.dump(grant, fh)
    except OSError as exc:
        return {"ok": False, "reason": f"failed to mark grant used: {exc}"}

    return {
        "ok": True,
        "reason": "receipt submitted",
        "receipt_id": grant["receipt_id"],
    }


def grant_status(session_id: str) -> dict:
    """Return the current grant state for a session."""
    grant_path = _grant_file(session_id)
    if not grant_path.exists():
        return {"state": "none", "session_id": session_id}

    try:
        with open(grant_path) as fh:
            grant = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"state": "corrupt", "session_id": session_id}

    now = time.time()
    expires_at = grant.get("expires_at", 0)
    remaining = max(0.0, expires_at - now)

    if grant.get("used"):
        state = "used"
    elif now > expires_at:
        state = "expired"
    else:
        state = "active"

    return {
        "state": state,
        "session_id": session_id,
        "tool": grant.get("tool", "?"),
        "remaining_seconds": round(remaining, 1),
        "created_at": grant.get("created_at"),
    }


# ---------------------------------------------------------------------------
# CLI helpers (for estate-execute intent)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PoBR Grant CLI")
    sub = parser.add_subparsers(dest="cmd")

    m = sub.add_parser("issue")
    m.add_argument("--session-id", required=True)
    m.add_argument("--tool", required=True)

    sub.add_parser("status")
    m2 = sub.add_parser("revoke")
    m2.add_argument("--session-id", required=True)

    args = parser.parse_args()

    if args.cmd == "issue":
        _ensure_grant_dir()
        now = time.time()
        grant = {
            "session_id": args.session_id,
            "tool": args.tool,
            "created_at": now,
            "expires_at": now + GRANT_TTL_SECONDS,
            "used": False,
        }
        path = _grant_file(args.session_id)
        with open(path, "w") as fh:
            json.dump(grant, fh)
        print(path)

    elif args.cmd == "status":
        result = grant_status(args.session_id)
        print(json.dumps(result, indent=2))

    elif args.cmd == "revoke":
        path = _grant_file(args.session_id)
        if path.exists():
            path.unlink()
            print("revoked")
        else:
            print("not found")
