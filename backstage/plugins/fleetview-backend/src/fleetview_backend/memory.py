"""FleetView estate memory: the router capturing every exchange and the drain growing the graph, live.

Three measured sources, nothing derived or estimated:
- the spool (~/.estate/graph-spool/*.md, written by platform/llm/graph_capture.py on every call
  through the laptop router): sessions waiting, exchanges captured, newest write;
- the graph (ESTATE_GRAPH_ROOT/.growmos, default ~/.estate/graph/estate-graph): entity and relation
  counts, sources still pending extraction;
- the drain's own last log line (~/.estate/graph-drain.log, bin/estate-graph-drain).

A source that cannot be read is reported as unavailable with its reason, never as a zero: an empty
spool and an unreadable one are different facts.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _home(env: str, default: str) -> Path:
    return Path(os.path.expanduser(os.environ.get(env) or default))


def _at(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lines(path: Path) -> int:
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def spool_status() -> dict[str, Any]:
    d = _home("ESTATE_GRAPH_SPOOL", "~/.estate/graph-spool")
    if not d.is_dir():
        return {
            "available": False,
            "error": f"no spool at {d}: router capture never wrote",
        }
    files = list(d.glob("*.md"))
    exchanges = 0
    agents: dict[str, int] = {}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        exchanges += text.count("\n## ")
        # Per-agent attribution (claim #6228): graph_capture stamps every exchange header
        # `agent=<name>`. Headers without a stamp mean the running router predates the
        # stamping code -- count them so the gap is visible instead of silently zero.
        for ln in text.splitlines():
            if ln.startswith("## "):
                m = re.search(r"\bagent=([A-Za-z0-9_.-]+)", ln)
                key = m.group(1) if m else "unattributed"
                agents[key] = agents.get(key, 0) + 1
    newest = max((f.stat().st_mtime for f in files), default=None)
    return {
        "available": True,
        "sessions_waiting": len(files),
        "exchanges_waiting": exchanges,
        "exchanges_by_agent": agents,
        "last_capture_at": _at(newest) if newest else None,
    }


def graph_status() -> dict[str, Any]:
    g = _home("ESTATE_GRAPH_ROOT", "~/.estate/graph/estate-graph") / ".growmos"
    try:
        entities = _lines(g / "entities.jsonl")
        relations = _lines(g / "relations.jsonl")
    except OSError as exc:
        return {"available": False, "error": f"graph unreadable at {g}: {exc}"}
    sessions = g.parent / "sessions"
    return {
        "available": True,
        "entities": entities,
        "relations": relations,
        "sessions_ingested": len(list(sessions.glob("*.md")))
        if sessions.is_dir()
        else 0,
        "updated_at": _at((g / "entities.jsonl").stat().st_mtime),
    }


def drain_status() -> dict[str, Any]:
    log = _home("ESTATE_GRAPH_DRAIN_LOG", "~/.estate/graph-drain.log")
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            last = [ln.strip() for ln in f if ln.strip()][-1:]
    except OSError as exc:
        return {"available": False, "error": f"drain has never run: {exc}"}
    # The drain logs `agents=a,b` (harvested from the agent= stamps of the sessions it moved);
    # surface it so /fleet shows who the graph is learning from, not just that it ran.
    m = re.search(r"\bagents=([A-Za-z0-9_.,-]+)", last[0]) if last else None
    agents = [a for a in m.group(1).split(",") if a] if m else []
    return {
        "available": bool(last),
        "last_run": last[0] if last else None,
        "agents": agents,
    }


def memory_status() -> dict[str, Any]:
    return {"spool": spool_status(), "graph": graph_status(), "drain": drain_status()}
