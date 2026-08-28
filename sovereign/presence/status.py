"""Estate status for the voice surface (R14, spec 2.6) and the cockpit's
Ghost line (CP4, spec 2.1: "at most one line").

`summarize` counts running, waiting and burn from the engine's session
rows, and folds in the presence dot and the last receipt hash so the
cockpit's Ghost view is one call. `speak` renders the sentence Siri
reads; `ghost_line` renders the founder's one line. Neither carries
per-session detail -- that only exists once the founder clicks into
Spatial (GET /api/spatial).
"""
from __future__ import annotations

from typing import Any

from sovereign.presence import config_keys
from sovereign.presence.spatial import burn_per_step

_RUNNING = ("running",)
_WAITING = ("waiting",)


def summarize(
    sessions: list[dict[str, Any]],
    *,
    presence_row: dict[str, Any] | None = None,
    last_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    running = [s for s in sessions if s.get("status") in _RUNNING]
    waiting = [s for s in sessions if s.get("status") in _WAITING]
    burn = int(round(sum(burn_per_step(s) for s in running)))
    budget_remaining = sum(int(s.get("budget_remaining") or 0) for s in sessions)
    counts = {
        "running": len(running),
        "waiting": len(waiting),
        "burn_per_step": burn,
        "total": len(sessions),
        "budget_remaining": budget_remaining,
    }
    row = presence_row or {}
    dot = str(row.get("dot") or config_keys.resolve("presence.dot_ghost"))
    last_hash = str((last_receipt or {}).get("hash") or "") or None
    counts["dot"] = dot
    counts["state"] = str(row.get("state") or "ghost")
    counts["last_hash"] = last_hash
    counts["spoken"] = speak(counts)
    counts["line"] = ghost_line(counts)
    if dot == str(config_keys.resolve("presence.dot_catastrophe")):
        counts["emergency"] = emergency_line()
    return counts


def speak(counts: dict[str, Any]) -> str:
    template = str(config_keys.resolve("presence.speak_template"))
    return template.format(
        running=counts.get("running", 0),
        waiting=counts.get("waiting", 0),
        burn_per_step=counts.get("burn_per_step", 0),
    )


def ghost_line(counts: dict[str, Any]) -> str:
    """The one line Ghost may show (spec 2.1): session count, budget
    remaining, last receipt hash. No task text, no per-session detail."""
    template = str(config_keys.resolve("presence.ghost_line_template"))
    hash_chars = int(config_keys.resolve("presence.receipt_hash_chars"))
    last_hash = counts.get("last_hash")
    return template.format(
        total=counts.get("total", 0),
        budget_remaining=counts.get("budget_remaining", 0),
        last_hash=(str(last_hash)[:hash_chars] if last_hash else "-"),
    )


def emergency_line() -> str:
    """The one line Ghost shows when the dot is red (spec 2.1: Spatial may
    be raised by a catastrophe). Never a question (cp32's rule for every
    system-authored line, applied here too)."""
    remediation = str(config_keys.resolve("presence.remediation_command"))
    template = str(config_keys.resolve("presence.emergency_line_template"))
    return template.format(remediation=remediation)
