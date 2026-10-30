"""The violation ledger and the per-session state: one file every runtime writes.

WHY A SHARED LEDGER. The ladder the founder asked for (one warning per violation class, then
terminate the session and relaunch it with an explicit instruction) has to be decided from
state that outlives the runtime that noticed the violation. pi, Claude Code and the session
plane all run on this machine, so the ledger lives in one place (~/.estate/state) and every
runtime writes the same record shape.

THE RECORD. One line per violation:

    {"ts": "...", "class": "law:LAW-001", "session": "...", "provider": "minimax",
     "detail": "...", "source": "pi-estate-enforce"}

`class` is the unit the ladder counts on. `provider` is the model provider that served the
session: the founder's rule binds governance to the provider, so a provider that keeps
producing violating sessions does not get its estate subscription renewed.

THE SESSION STATE. A session under lockdown has a file of its own:
~/.estate/state/sessions/<session>.json with the class it broke, the instruction it was
relaunched with, and the proof that lifts the lock. The write gate reads it, so a locked
session cannot write even if it wants to cheat.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


def state_home() -> str:
    """Where the governance state lives. Overridable so tests never touch the real state."""
    return os.environ.get("ESTATE_GOVERNANCE_HOME") or os.path.join(
        os.path.expanduser("~"), ".estate", "state"
    )


def violations_path() -> str:
    return os.path.join(state_home(), "violations.jsonl")


def prompts_path() -> str:
    return os.path.join(state_home(), "prompts.jsonl")


def sessions_dir() -> str:
    return os.path.join(state_home(), "sessions")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        return out
    return out


# --- the violation ledger ---------------------------------------------------------------------


def record_violation(
    cls: str,
    session: str,
    provider: str = "",
    detail: str = "",
    source: str = "",
) -> Dict[str, Any]:
    """Append one violation. Returns the record as written."""
    rec = {
        "ts": now(),
        "class": cls,
        "session": session or "unknown",
        "provider": provider or "",
        "detail": detail or "",
        "source": source or "",
    }
    _append(violations_path(), rec)
    return rec


def violations(
    session: Optional[str] = None,
    cls: Optional[str] = None,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rows = read_jsonl(violations_path())
    if session is not None:
        rows = [r for r in rows if r.get("session") == session]
    if cls is not None:
        rows = [r for r in rows if r.get("class") == cls]
    if provider is not None:
        rows = [r for r in rows if r.get("provider") == provider]
    return rows


def count_in_session(cls: str, session: str) -> int:
    """How many times this session has already broken this class."""
    return len(violations(session=session, cls=cls))


def provider_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in violations():
        provider = (row.get("provider") or "").strip()
        if provider:
            counts[provider] = counts.get(provider, 0) + 1
    return counts


# --- per-session state ------------------------------------------------------------------------


def session_state_path(session: str) -> str:
    safe = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in (session or "unknown")
    )
    return os.path.join(sessions_dir(), f"{safe}.json")


def get_session_state(session: str) -> Dict[str, Any]:
    try:
        with open(session_state_path(session)) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def set_session_state(session: str, **fields: Any) -> Dict[str, Any]:
    state = get_session_state(session)
    state.update(fields)
    state["updated"] = now()
    path = session_state_path(session)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)
    return state


def lock_session(
    session: str,
    cls: str,
    detail: str = "",
    instruction: str = "",
    proof: str = "",
) -> Dict[str, Any]:
    """Put a session under lockdown: no writes, no pushes, until the hole is proven fixed."""
    return set_session_state(
        session,
        status="locked",
        locked=True,
        violation_class=cls,
        detail=detail,
        instruction=instruction,
        proof=proof,
        locked_at=now(),
    )


def unlock_session(session: str, proof_result: str = "") -> Dict[str, Any]:
    return set_session_state(
        session,
        status="free",
        locked=False,
        unlocked_at=now(),
        proof_result=proof_result,
    )


def is_locked(session: str) -> bool:
    """Locked means locked: the flag and the status are read together.

    A lockdown is a fact about the session, so every reader must agree on it. Reading one
    field and ignoring the other is how a locked session was still granted the direct
    executor (measured 2026-10-29: `status: locked` beside `locked: false`).
    """
    state = get_session_state(session)
    return bool(state.get("locked")) or state.get("status") == "locked"
