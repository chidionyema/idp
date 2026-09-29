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


# ── highlights on the news channel ─────────────────────────────────────────────────────────
# The proof's headlines go out as estate.news.story rows (platform/event-bus/contract/
# estate.news.story.json) on the `metrics` channel, so the NewsDesk and the anchor read them the
# way they read deploys and incidents. A story is re-published only when its headline changes;
# the id is the entity plus the headline, so a changed number is a new row, an unchanged one none.
NEWS_EVERY_S = int(os.environ.get("ESTATE_EFFICIENCY_NEWS_EVERY_S", "300"))
_LANE_MIN_CALLS = 20  # a trial lane with fewer calls per arm is not news yet


def _story(
    entity: str, headline: str, anchor: str, evidence: list, severity: str, at: str
):
    import hashlib

    return {
        "id": hashlib.sha256(f"{entity}|{headline}".encode()).hexdigest()[:16],
        "channel": "metrics",
        "source": "router",
        "severity": severity,
        "state": "reported",
        "headline": headline,
        "anchor": anchor,
        "entity": entity,
        "evidence": [str(e)[:200] for e in evidence][:5],
        "score": 3.0 if severity != "info" else 1.0,
        "count": 1,
        "breaking": False,
        "first_at": at,
        "at": at,
    }


def highlights(p: dict) -> list[dict]:
    """The proof, as news: the estimate's total and top step, then one story per trial lane."""
    at = p["generated"]
    e, t = p["estimate"], p["trial"]
    out = []
    steps = sorted(e["steps"].items(), key=lambda kv: -kv[1]["net_usd"])
    if steps:
        k, s = steps[0]
        pct = (
            100 * e["net_saved_usd"] / e["input_usd_billed"]
            if e["input_usd_billed"]
            else 0
        )
        out.append(
            _story(
                "efficiency/estimate",
                f"Router saved ${e['net_saved_usd']:.2f} of ${e['input_usd_billed']:.2f} input"
                f" ({pct:.1f}%); top step {k} ${s['net_usd']:.2f}",
                f"The token router's optimisations saved an estimated {pct:.1f} percent of input"
                f" spend, led by {s['what']}, according to the router's ledger.",
                [
                    f"{kk} {v['what']}: {v['tokens'] / 1e6:.2f}M tok, net ${v['net_usd']:.2f}"
                    for kk, v in steps
                ],
                "info",
                at,
            )
        )
    for lane, v in sorted(t["lanes"].items()):
        n = min(v["treat"]["calls"], v["control"]["calls"])
        if n < _LANE_MIN_CALLS or v["pct_change_usd_per_call"] is None:
            continue
        ci = v["ci95"]
        out.append(
            _story(
                f"efficiency/trial/{lane}",
                f"Trial {lane}: {v['pct_change_usd_per_call']:+.1f}% $/call"
                f" [{ci[0]:+.1f}, {ci[1]:+.1f}] {v['verdict']}",
                f"In the randomised trial on {lane}, the optimised arm's cost per call changed by"
                f" {v['pct_change_usd_per_call']:+.1f} percent: {v['verdict']}, according to the"
                " router's ledger.",
                [
                    f"treat {v['treat']['conversations']} conv {v['treat']['calls']} calls",
                    f"control {v['control']['conversations']} conv {v['control']['calls']} calls",
                    f"trial ends {t['ends']}",
                ],
                "warn" if v["verdict"] in ("saves", "costs more") else "info",
                at,
            )
        )
    return out


async def publish_highlights(nats_url: str) -> None:
    """Every NEWS_EVERY_S: recompute the proof and publish changed highlights. Never raises."""
    import asyncio as _asyncio
    import logging

    from fleetview_backend import nats_adapter

    log = logging.getLogger(__name__)
    sent: dict = {}
    while True:
        try:
            import nats

            body = await _asyncio.to_thread(proof)
            fresh = [s for s in highlights(body) if sent.get(s["entity"]) != s["id"]]
            if fresh:
                nc = await nats.connect(
                    nats_adapter._nats_url(nats_url),
                    max_reconnect_attempts=nats_adapter.CONNECT_MAX_RECONNECT_ATTEMPTS,
                    reconnect_time_wait=nats_adapter.CONNECT_RECONNECT_TIME_WAIT,
                    connect_timeout=nats_adapter.CONNECT_TIMEOUT,
                )
                try:
                    for s in fresh:
                        await nc.publish(
                            f"estate.news.story.{s['channel']}", json.dumps(s).encode()
                        )
                        sent[s["entity"]] = s["id"]
                        log.info("fleetview.efficiency_news %s", s["headline"])
                finally:
                    await nc.drain()
        except Exception as exc:  # noqa: BLE001 - the news desk never takes the backend down
            log.warning("fleetview.efficiency_news_failed %s", exc)
        await _asyncio.sleep(NEWS_EVERY_S)
