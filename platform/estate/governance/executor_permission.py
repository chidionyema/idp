"""Direct-executor freedom, earned by measurement.

The founder's order (2026-10-29): once the governance enforcement is active and proven, the
fleet may use the direct executor again. "Once" and "proven" are the operative words, so the
permission is computed, never assumed:

    1. the law gate is green -- every registered law passes, with its falsifier run
    2. the session is not locked -- no warn/terminate escalation is outstanding
    3. the session holds a live claim -- the estate's own rule (AGENTS.md section 5)

Any one of them missing means "no". The decision is written as an artifact so the executor door
reads a fact, not a hope, and so a session cannot widen its own permission.
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from typing import Any, Dict, List, Optional

from . import ledger, registry

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def state_home() -> str:
    """Where the governance state lives. Overridable so tests never touch the real state."""
    return (
        os.environ.get("ESTATE_GOVERNANCE_HOME")
        or os.environ.get("ESTATE_STATE_HOME")
        or os.path.expanduser("~/.estate/state")
    )


def permission_path(session: str) -> str:
    return os.path.join(state_home(), "executor-permission", f"{session}.json")


def _gate(root: str, gate_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The law gate's verdict. A caller may pass a report to test the decision, not to fake it."""
    if gate_report is not None:
        return gate_report
    return registry.evaluate_all(root=root, falsify=True)


def _failing(report: Dict[str, Any]) -> List[str]:
    out = []
    for row in report.get("results", report.get("laws", [])):
        if row.get("verdict", row.get("status")) in ("fail", "failing", "FAIL"):
            out.append(f"{row.get('id')} {row.get('detail', '')}".strip())
    return out


def _law_count(report: Dict[str, Any]) -> int:
    rows = report.get("results", report.get("laws", []))
    return len(rows) if isinstance(rows, list) else 0


def _claims(live: Optional[List[Dict[str, Any]]], claim: str) -> Dict[str, Any]:
    """The live claims, read from the estate's own register.

    A claim number typed on the command line is NOT a live claim: it is a claim someone says
    they hold. The register is the record (AGENTS.md section 5), and the founder's rule is that
    a permission is earned by measurement. So a supplied number counts only when the register
    carries it, and an unreadable register means unknown -- which is not live.
    """
    numbers: List[str] = []
    readable = live is not None
    for row in live or []:
        if row.get("live") is False:
            continue
        raw = str(
            row.get("claim") or row.get("number") or row.get("issue") or ""
        ).strip()
        number = raw.split("#")[-1].strip()
        if number and number not in numbers:
            numbers.append(number)
    wanted = claim.lstrip("#").strip()
    supplied = wanted if wanted and wanted in numbers else ""
    return {
        "numbers": numbers,
        "readable": readable,
        "supplied": supplied,
        "supplied_verified": bool(supplied),
    }


def evaluate(
    session: str,
    root: str = REPO_ROOT,
    claim: str = "",
    gate_report: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    live_claims: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """The decision: may this session use the direct executor right now?"""
    reasons: List[str] = []

    report = _gate(root, gate_report)
    failing = _failing(report)
    laws = _law_count(report)
    if failing:
        reasons.append("the law gate is red: " + "; ".join(failing[:3]))
    elif not laws:
        # A gate that reports no laws is not a green gate, it is no gate at all.
        reasons.append("the law gate reported no laws, so nothing was proven")

    if state is None:
        state = ledger.get_session_state(session)
        state = dict(state)
        state["locked"] = ledger.is_locked(session)
    if state.get("locked"):
        reasons.append(
            "the session is locked: "
            + str(state.get("instruction") or "the proof has not been produced")
        )

    if live_claims is None:
        register = _claims(_live_register(root), claim)
    else:
        register = {
            "numbers": list(live_claims),
            "readable": True,
            "supplied": claim.lstrip("#").strip(),
            "supplied_verified": bool(live_claims)
            and claim.lstrip("#").strip() in live_claims,
        }
    if not register["readable"]:
        reasons.append(
            "the claim register could not be read, so no live claim is proven"
        )
    elif not claim.strip():
        # The estate's own rule: no work without a claim. The permission is per session, so the
        # session must name the claim it holds, and the register must show it live.
        reasons.append("no claim was named for this session, so its claim is unproven")
    elif not register["numbers"]:
        reasons.append("no live claim covers this session")
    elif not register["supplied_verified"]:
        reasons.append(
            f"claim #{claim.lstrip('#')} is not in the live register, so it is a claim someone "
            "says they hold, not a claim the estate can see"
        )

    granted = not reasons
    return {
        "session": session,
        "granted": granted,
        "reasons": reasons,
        "laws": laws,
        "failing": failing,
        "locked": bool(state.get("locked")),
        "claims": register["numbers"],
        "claim_verified": register["supplied_verified"],
        "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _live_register(root: str = REPO_ROOT) -> Optional[List[Dict[str, Any]]]:
    """The claim register. None when it cannot be read: unknown is not a live claim."""
    try:
        path = os.path.join(root, "platform", "estate", "memory", "focus.py")
        if not os.path.isfile(path):
            return None
        spec = importlib.util.spec_from_file_location("estate_focus_probe", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.live_focus()
    except Exception:
        return None


def write(decision: Dict[str, Any]) -> str:
    path = permission_path(decision["session"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(decision, f, indent=2, sort_keys=True, default=str)
    os.replace(tmp, path)
    return path


def read(session: str) -> Optional[Dict[str, Any]]:
    path = permission_path(session)
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
