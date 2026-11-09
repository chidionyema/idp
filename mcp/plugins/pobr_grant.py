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
plus any estate intent whose `class:` is `mutate` (an action that changes
state; investigation reads are the thing a receipt records, not the thing
gated).
Never gate: pobr_submit, pobr_status (the tools that build/consume the
receipt), estate_show, estate_list, harv (the tools that let the agent
learn enough to form a hypothesis).
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
_NEVER_GATE = frozenset(
    {
        "pobr_submit",
        "pobr_status",
        "estate_show",
        "estate_list",
        "harv",
        # Receipt-building tools: the agent must be able to declare hypotheses
        # and run the gate to produce the receipt it is then required to have
        # before acting. Gating these would deadlock reasoning itself.
        "pobr-gate",
        "pobr-admit",
    }
)

# Intents that change state. These require an admitted reasoning receipt BEFORE
# they run: the agent must have declared hypotheses, a counterfactual, and a
# calibrated posterior (a PoBR receipt) before it is allowed to act.
_MUTATE_CLASS = "mutate"


def _grant_file(session_id: str) -> Path:
    return GRANT_DIR / f"GRANT-{session_id}.json"


def requires_grant(tool_name: str, intent_class: str = "") -> bool:
    """Return True if tool_name is gated by PoBR.

    Gates outbound messaging tool names (send_/emit_/...) and any estate
    intent carrying class: mutate. intent_class is passed by the estate_invoke
    caller when it has already loaded the intent; it is empty at the generic
    wrapper boundary, where only the tool name is known.
    """
    if tool_name in _NEVER_GATE:
        return False
    if intent_class == _MUTATE_CLASS:
        return True
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

    if not grant.get("admitted"):
        return {
            "valid": False,
            "reason": "grant not admitted: no structured reasoning receipt was verified",
        }

    return {"valid": True, "reason": "ok", "grant": grant}


def _ensure_grant_dir() -> None:
    GRANT_DIR.mkdir(parents=True, exist_ok=True)


def _admit_receipt(receipt: dict) -> dict:
    """Run the deterministic PoBR verifier on the receipt's content.

    Returns {"admitted": bool, "reason": str, "detail": str}.
    The verifier is pobr_gate.gate() (9 checks). Signature/anchoring need
    key/anchor infrastructure; for the action boundary we run the reasoning-
    content checks that force structure: hypotheses, counterfactual,
    completeness, calibration, prior-sensitivity, faithfulness.

    If the verifier cannot be imported, this is BLIND (admitted=False with a
    reason naming the import failure) so the caller can decide -- never a
    silent pass, never a hard lockout.
    """
    try:
        import importlib.util

        gate_path = Path(__file__).parent / "pobr_gate.py"
        spec = importlib.util.spec_from_file_location("pobr_gate", gate_path)
        if spec is None or spec.loader is None:
            return {
                "admitted": False,
                "reason": "blind",
                "detail": "pobr_gate.py not loadable",
            }
        gate_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate_mod)
        receipt_obj = gate_mod.receipt_from_dict(receipt)

        # Content-only checks: structure -> completeness -> calibration ->
        # prior-sensitivity -> faithfulness -> counterfactual. Signature and
        # anchor are tamper-evidence, verified separately by pobr-admit.
        checks = [
            gate_mod.check_structure,
            gate_mod.check_completeness,
            gate_mod.check_calibration,
            gate_mod.check_prior_sensitivity,
            gate_mod.check_faithfulness,
            gate_mod.check_counterfactual,
        ]
        for fn in checks:
            result = fn(receipt_obj)
            if result is not None and result.decision.value == "REJECTED":
                return {
                    "admitted": False,
                    "reason": result.reason,
                    "detail": result.detail,
                }
        return {"admitted": True, "reason": "all_checks_passed", "detail": ""}
    except Exception as exc:
        return {"admitted": False, "reason": "blind", "detail": str(exc)}


def pobr_submit_tool(session_id: str, receipt: dict) -> dict:
    """
    Verify the receipt with the deterministic PoBR gate, then consume the
    grant and record success. Never returns the receipt back -- returns only
    a status.

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

    # Run the real verifier BEFORE accepting the receipt. A receipt that the
    # gate rejects means the agent has not yet done structured reasoning: the
    # grant stays unconsumed and future mutate actions stay refused.
    verdict = _admit_receipt(receipt)
    if not verdict["admitted"]:
        return {
            "ok": False,
            "reason": f"receipt REJECTED: {verdict['reason']}",
            "detail": verdict["detail"],
        }

    # Mark used only after admission
    grant["used"] = True
    grant["submitted_at"] = time.time()
    grant["receipt_id"] = receipt.get("receipt_id", str(uuid.uuid4()))
    grant["admitted"] = True

    try:
        with open(grant_path, "w") as fh:
            json.dump(grant, fh)
    except OSError as exc:
        return {"ok": False, "reason": f"failed to mark grant used: {exc}"}

    return {
        "ok": True,
        "reason": "receipt submitted and admitted",
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
