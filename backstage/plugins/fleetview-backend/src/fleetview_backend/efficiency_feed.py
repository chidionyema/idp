"""Live token-efficiency feed for /fleet: reads the gateway's ledger, never re-implements it.

The math (cache saved, router bytes cut, prefix breaks) is `bin/estate-efficiency-report`'s
`Totals`; this module loads that one implementation and streams its result as SSE frames.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

_REPORT = Path(
    os.environ.get("ESTATE_EFFICIENCY_REPORT")
    or Path(__file__).resolve().parents[5] / "bin" / "estate-efficiency-report"
)


def _report():
    loader = importlib.machinery.SourceFileLoader(
        "estate_efficiency_report", str(_REPORT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def summary(since: str = "1h") -> dict:
    rep = _report()
    totals = rep.Totals()
    for row in rep.load(rep.ledger_path(), rep.parse_since(since)):
        totals.add(row)
    return {"since": since, **totals.summary()}


async def stream(since: str = "1h", every_s: float = 2.0):
    """One `efficiency` frame per tick: the window summary plus calls seen since the last tick."""
    path = _report().ledger_path()
    pos = path.stat().st_size if path.exists() else 0
    while True:
        calls = 0
        if path.exists() and path.stat().st_size > pos:
            with path.open(encoding="utf-8", errors="replace") as fh:
                fh.seek(pos)
                calls = fh.read().count('"kind": "outcome"')
                pos = fh.tell()
        body = await asyncio.to_thread(summary, since)
        yield f"event: efficiency\ndata: {json.dumps({**body, 'new_calls': calls})}\n\n"
        await asyncio.sleep(every_s)


# The proof (bin/estate-token-proof): the holdout trial and the per-step dollar estimate. It reads
# the whole ledger and prices it with LiteLLM's map (~40 s), so /fleet gets it from a 5-minute cache.
_PROOF = Path(
    os.environ.get("ESTATE_TOKEN_PROOF")
    or Path(__file__).resolve().parents[5] / "bin" / "estate-token-proof"
)
_PROOF_TTL_S = 300
_proof_cache: dict = {}


def proof() -> dict:
    import time

    hit = _proof_cache.get("r")
    if hit and time.time() - hit[0] < _PROOF_TTL_S:
        return hit[1]
    loader = importlib.machinery.SourceFileLoader("estate_token_proof", str(_PROOF))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    body = mod.report(None)
    _proof_cache["r"] = (time.time(), body)
    return body
