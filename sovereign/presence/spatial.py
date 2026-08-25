"""The Spatial view's data (spec 2.1): one node per session, coloured by
health and sized by burn rate; hover carries hash, budget and the last
heartbeat; Halt sends the engine's stop signal.

The graph is a pure function of the engine's session rows, so the same
truth the cockpit's /api/sessions serves is what the force layout draws.
Rendering is the cockpit page's job; this module only shapes the data.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from sovereign.presence import config_keys

_WAITING = ("waiting",)
_HALTED = ("halted", "failed", "denied", "stopped", "error")
_DONE = ("done",)
_RUNNING = ("running",)
_HALT_BY = "spatial"
_HALT_REASON = "halt from Spatial"


def health_colour(status: str) -> str:
    if status in _RUNNING:
        return str(config_keys.resolve("presence.health_running"))
    if status in _WAITING:
        return str(config_keys.resolve("presence.health_waiting"))
    if status in _DONE:
        return str(config_keys.resolve("presence.health_done"))
    return str(config_keys.resolve("presence.health_halted"))


def burn_per_step(row: dict[str, Any]) -> float:
    budget = int(row.get("budget") or 0)
    remaining = int(row.get("budget_remaining") or 0)
    steps = max(int(row.get("step") or 0), 1)
    return max(budget - remaining, 0) / steps


def node_size(burn: float) -> float:
    kilo = int(config_keys.resolve("presence.budget_kilo"))
    base = int(config_keys.resolve("presence.node_min_size"))
    per_kilo = int(config_keys.resolve("presence.node_size_per_kilo"))
    return base + per_kilo * (burn / kilo)


def node(row: dict[str, Any]) -> dict[str, Any]:
    burn = burn_per_step(row)
    return {
        "id": row.get("session_id"),
        "status": row.get("status"),
        "colour": health_colour(str(row.get("status") or "")),
        "size": node_size(burn),
        "burn_per_step": burn,
        # what hover shows
        "hash": row.get("commit") or row.get("state_hash") or row.get("fsm_state"),
        "budget": row.get("budget"),
        "budget_remaining": row.get("budget_remaining"),
        "last_heartbeat": row.get("updated_at"),
        "task": row.get("task"),
    }


def graph(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [node(r) for r in sessions if r.get("session_id")]
    # Edges are capability invocations between sessions (spec 2.1). The
    # engine does not record cross-session calls yet, so the edge list is
    # empty rather than invented; the shape is fixed so the page draws it
    # the day the engine fills it.
    return {"nodes": nodes, "edges": [], "running": [n["id"] for n in nodes if n["status"] in _RUNNING]}


Signal = Callable[[str, str, str, str], Awaitable[dict[str, Any]]]


async def halt(session_id: str, signal: Signal) -> dict[str, Any]:
    """Right-click -> Halt: the engine's stop signal, nothing else."""
    return await signal(session_id, "stop", _HALT_BY, _HALT_REASON)
