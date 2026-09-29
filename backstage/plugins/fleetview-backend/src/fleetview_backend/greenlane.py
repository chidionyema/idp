"""FleetView: the Greenlane's invariants, live. `bin/idp-greenlane status` reads GitHub (main's
required checks, open pull requests, the engine's state ref) and this serves it to /fleet, cached
for CACHE_S so a 10 s poll costs GitHub one read per half minute. An unreadable lane is reported
with its reason, never as green: the founder's question is "is main green and is anything red
in the lane?", and a silent zero would answer it falsely.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

CACHE_S = 30
_cache: dict[str, Any] = {"at": 0.0, "body": None}


def _idp_root() -> Path:
    return Path(
        os.path.expanduser(os.environ.get("ESTATE_IDP_ROOT") or "~/Documents/code/idp")
    )


def greenlane_status(now: float | None = None) -> dict[str, Any]:
    t = now if now is not None else time.time()
    if _cache["body"] is not None and t - _cache["at"] < CACHE_S:
        return _cache["body"]
    tool = _idp_root() / "bin/idp-greenlane"
    if not tool.exists():
        body = {"available": False, "error": f"no {tool}"}
    else:
        try:
            p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                ["python3", str(tool), "status"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=25,
            )
            if p.returncode != 0:
                body = {
                    "available": False,
                    "error": (p.stderr or p.stdout).strip()[-300:]
                    or f"rc={p.returncode}",
                }
            else:
                body = json.loads(p.stdout)
                body["available"] = True
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            body = {"available": False, "error": f"{type(e).__name__}: {e}"[:300]}
    body["read_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    _cache.update(at=t, body=body)
    return body
