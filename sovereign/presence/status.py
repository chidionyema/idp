"""Estate status for the voice surface (R14, spec 2.6).

`summarize` counts running, waiting and burn from the engine's session
rows; `speak` renders the sentence Siri reads. The Siri Shortcut itself
(shortcuts/estate-status.json) does GET /api/status on the cockpit and
speaks the `spoken` field, so the phrase is composed here, once, and the
shortcut carries no logic.
"""
from __future__ import annotations

from typing import Any

from sovereign.presence import config_keys
from sovereign.presence.spatial import burn_per_step

_RUNNING = ("running",)
_WAITING = ("waiting",)


def summarize(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    running = [s for s in sessions if s.get("status") in _RUNNING]
    waiting = [s for s in sessions if s.get("status") in _WAITING]
    burn = int(round(sum(burn_per_step(s) for s in running)))
    counts = {"running": len(running), "waiting": len(waiting), "burn_per_step": burn}
    return {**counts, "spoken": speak(counts)}


def speak(counts: dict[str, Any]) -> str:
    template = str(config_keys.resolve("presence.speak_template"))
    return template.format(
        running=counts.get("running", 0),
        waiting=counts.get("waiting", 0),
        burn_per_step=counts.get("burn_per_step", 0),
    )
