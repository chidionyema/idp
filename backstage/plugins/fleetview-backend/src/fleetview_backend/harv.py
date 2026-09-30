"""FleetView: the harv capability harvester, live. `harv funnel` reports how many crates and
functions survived each rung on the way to the shelf (license, fetch, compile, zero-import
sandbox, smoke, tests, witnesses) and how many shelved parts hold signed evidence. This parses it
for /fleet, cached CACHE_S so a poll costs one subprocess per half minute. A harvester that cannot
be read is reported unavailable with its reason, never as an empty funnel: a silent zero would say
"nothing was harvested" when the truth is "nobody looked".
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

CACHE_S = 30
_cache: dict[str, Any] = {"at": 0.0, "body": None}

_RUN = re.compile(r"^harvest-(\d+):\s*$")
_ROW = re.compile(r"^\s+([a-z0-9-]+)\s+(\d+)\s*$")
_TIERS = re.compile(r'\("(t\d)",\s*(\d+)\)')
_EVIDENCE = re.compile(r"^evidence entries \(ring4-ledger\):\s*(\d+)\s*$")


def _harv_bin() -> str | None:
    explicit = os.environ.get("HARV_BIN")
    if explicit:
        return explicit if Path(explicit).exists() else None
    return shutil.which("harv") or (
        str(p) if (p := Path.home() / ".cargo/bin/harv").exists() else None
    )


def parse_funnel(text: str) -> dict[str, Any]:
    """The funnel output as data. Raises ValueError when it has no funnel rows at all."""
    run_at: int | None = None
    stages: list[dict[str, Any]] = []
    shelf: dict[str, int] = {}
    evidence: int | None = None
    for line in text.splitlines():
        if m := _RUN.match(line):
            run_at = int(m.group(1))
        elif m := _ROW.match(line):
            stages.append({"stage": m.group(1), "n": int(m.group(2))})
        elif line.startswith("shelf by tier:"):
            shelf = {t: int(n) for t, n in _TIERS.findall(line)}
        elif m := _EVIDENCE.match(line):
            evidence = int(m.group(1))
    if not stages:
        raise ValueError("no funnel rows in harv output")
    return {
        "run_at": run_at,
        "stages": stages,
        "shelf": shelf,
        "shelved": sum(shelf.values()),
        "evidence": evidence,
    }


def harv_status(now: float | None = None) -> dict[str, Any]:
    t = now if now is not None else time.time()
    if _cache["body"] is not None and t - _cache["at"] < CACHE_S:
        return _cache["body"]
    tool = _harv_bin()
    if not tool:
        body: dict[str, Any] = {"available": False, "error": "harv binary not found"}
    else:
        try:
            p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                [tool, "funnel"], capture_output=True, text=True, timeout=25
            )
            if p.returncode != 0:
                body = {
                    "available": False,
                    "error": (p.stderr or p.stdout).strip()[-300:]
                    or f"rc={p.returncode}",
                }
            else:
                body = {**parse_funnel(p.stdout), "available": True}
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            body = {"available": False, "error": f"{type(e).__name__}: {e}"[:300]}
    body["read_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    _cache.update(at=t, body=body)
    return body
