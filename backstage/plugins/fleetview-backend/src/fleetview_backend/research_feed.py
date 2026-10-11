"""The research department, on the air.

Until this module the research-engine's verified claims reached exactly two surfaces: the
findings strip (packages/backend/src/researchOutput.ts, ticket idp#5714) and the voice when it
happened to be asked about research. The bus and the room never saw them, and neither did the
voice's own prompt -- a claim the department verified an hour ago was invisible to the two
surfaces that stream everything else.

TWO JOBS, ONE READER.

1. `research_claims()` reads the claims BACK through the estate's own reader: the
   research-output backend plugin at `/api/research-output/claims`. It is an HTTP GET over
   loopback to the portal that shares this pod (`FLEETVIEW_PORTAL_URL`, default
   http://127.0.0.1:7107 -- app-config.yaml's listener port). This module deliberately does
   NOT add a Postgres client: the estate keeps one reader of each layer (AGENTS.md §6), the
   credential stays where researchOutput.ts already mounts it, and a second reader would be
   the duplicate the estate deletes. Unreachable portal -> `available: False` with the reason,
   never a fabricated empty list.

2. `publish_claims()` turns NEW claims into estate.news.story rows (contract:
   platform/event-bus/contract/estate.news.story.json) on the `news` channel, the way
   efficiency_feed.py publishes router proofs on `metrics`. One connect per sweep, one story
   per claim, re-publish suppressed per process by claim id (same precedent as
   efficiency_feed's `sent` dict: after a restart the sweep replays the newest claim once,
   which is what NEWS is for). Never raises -- a dead bus or a dead portal must not kill the
   sidecar's other work; the loop logs and tries again next sweep.

CONFIG (LAW 46): FLEETVIEW_PORTAL_URL (default http://127.0.0.1:7107),
ESTATE_RESEARCH_EVERY_S (default 300), ESTATE_RESEARCH_CLAIMS (default 8, the sweep window).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# The loop's sleep, as a module attribute so tests can stop the sweep after one pass without
# patching asyncio globally.
_sleep = asyncio.sleep

_PORTAL_URL_ENV = "FLEETVIEW_PORTAL_URL"
_EVERY_S_ENV = "ESTATE_RESEARCH_EVERY_S"
_WINDOW_ENV = "ESTATE_RESEARCH_CLAIMS"
_TIMEOUT_S = 4
_CACHE_S = 60

_lock = threading.Lock()
# Role markers let a claim impersonate a prompt voice; backticks/fences let it fake a code
# block. Claims are DATA -- they are crawled text from GPT Researcher -- and they cross into
# voice prompts and the news bus, so they are defanged at the one place every consumer reads
# through (research_claims), not per consumer.
_ROLE_RE = re.compile(r"(?i)\b(system|assistant|developer|user|tool)\s*:")


def _defang_statement(text: str) -> str:
    s = " ".join(str(text).split())
    s = _ROLE_RE.sub("\1 -", s)
    s = s.replace("```", "'").replace("**", "")
    return s[:300]


_cache: dict[str, Any] = {"at": 0.0, "body": None}


def _portal_url() -> str:
    return (
        os.environ.get(_PORTAL_URL_ENV, "").strip().rstrip("/")
        or "http://127.0.0.1:7107"
    )


def _every_s() -> int:
    try:
        return max(30, int(os.environ.get(_EVERY_S_ENV, "300")))
    except ValueError:
        return 300


def _window() -> int:
    try:
        return max(1, min(50, int(os.environ.get(_WINDOW_ENV, "8"))))
    except ValueError:
        return 8


def research_claims(now: float | None = None, fetch=None) -> dict[str, Any]:
    """The department's newest verified claims, through the portal's one reader.

    Returns {available: True, count, claims[], source} or {available: False, error}.
    Cached for _CACHE_S so the /estate strip, the voice prompt and the news sweep share one
    read instead of three. `fetch` is the test seam.
    """
    import time

    t = now if now is not None else time.time()
    with _lock:
        if _cache["body"] is not None and t - _cache["at"] < _CACHE_S:
            return _cache["body"]

    url = f"{_portal_url()}/api/research-output/claims?limit={_window()}"
    body: dict[str, Any]
    try:
        opener = fetch or _http_get
        status, raw = opener(url)
        if status != 200:
            body = {"available": False, "error": f"/claims answered {status}"}
        else:
            doc = json.loads(raw)
            claims = doc.get("claims")
            if not isinstance(claims, list):
                body = {"available": False, "error": "/claims returned no claims list"}
            else:
                clean: list[dict[str, Any]] = []
                for c in claims:
                    if not isinstance(c, dict):
                        continue
                    c = dict(c)
                    if c.get("statement"):
                        c["statement"] = _defang_statement(str(c["statement"]))
                    clean.append(c)
                body = {
                    "available": True,
                    "count": len(clean),
                    "claims": clean,
                    "source": "estate-db/research.claims via research-output",
                }
    except Exception as exc:  # noqa: BLE001 -- every failure is an envelope, never a raise
        body = {"available": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    with _lock:
        _cache.update(at=t, body=body)
    return body


def _http_get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url)  # noqa: S310 -- the estate's own portal, never caller input
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310 -- as above
        return resp.status, resp.read().decode("utf-8", "replace")


def claim_story(claim: dict[str, Any]) -> dict[str, Any] | None:
    """One verified claim as an estate.news.story row (the contract efficiency_feed follows).

    Malformed claims (no statement, no created_at) produce no story -- a story with nothing to
    say is noise, and the rundown already knows how to drop nothing.
    """
    statement = str(claim.get("statement") or "").strip()
    created = str(claim.get("created_at") or "").strip()
    if not statement or not created:
        return None
    at = created if created.endswith("Z") else created + "Z"
    entity = f"research/{hashlib.sha256(statement.encode()).hexdigest()[:12]}"
    # created_at in the id: two distinct findings that share their first 120 chars are two
    # findings, and the publisher's seen-set must not swallow the second one.
    return {
        "id": hashlib.sha256(
            f"{entity}|{created}|{statement[:120]}".encode()
        ).hexdigest()[:16],
        "channel": "news",
        "source": "estate.research",
        "severity": "info",
        "state": "confirmed"
        if str(claim.get("status", "")).lower() == "verified"
        else "reported",
        "headline": statement[:160],
        "anchor": statement[:200],
        "entity": entity,
        "evidence": [f"status {claim.get('status', 'unknown')} at {at}"],
        "score": 1.0,
        "count": 1,
        "breaking": False,
        "first_at": at,
        "at": at,
    }


async def publish_claims(nats_url: str) -> None:
    """Every _every_s(): sweep the claims and publish the ones news has not carried.

    Never raises. One NATS connect per sweep with something to say (efficiency_feed's shape);
    a sweep with nothing new costs one cached loopback GET and no bus dial.
    """
    import asyncio

    sent: set[str] = set()
    primed = False
    while True:
        try:
            body = await asyncio.to_thread(research_claims)
            if not body.get("available"):
                # The reason is the answer: a sweep against an unavailable department logs
                # once per sweep and stays quiet otherwise.
                logger.warning(
                    "fleetview.research_news unavailable: %s", body.get("error")
                )
                await _sleep(_every_s())
                continue
            stories = [
                s
                for s in (claim_story(c) for c in body.get("claims") or [])
                if s is not None
            ]
            fresh = [s for s in stories if s["id"] not in sent]
            if not primed:
                # First sweep after a start: fill the seen-set silently so a restart does not
                # replay the whole window as breaking news, EXCEPT the single newest claim --
                # the rundown should show where the department last was.
                for s in stories:
                    sent.add(s["id"])
                if fresh:
                    sent.add(fresh[0]["id"])
                    fresh = fresh[:1]
                primed = True
            if fresh:
                import nats

                from fleetview_backend import nats_adapter

                nc = await nats.connect(
                    nats_adapter._nats_url(nats_url),
                    max_reconnect_attempts=nats_adapter.CONNECT_MAX_RECONNECT_ATTEMPTS,
                    reconnect_time_wait=nats_adapter.CONNECT_RECONNECT_TIME_WAIT,
                    connect_timeout=nats_adapter.CONNECT_TIMEOUT,
                )
                try:
                    for s in fresh:
                        await nc.publish(
                            f"estate.news.story.{s['channel']}",
                            json.dumps(s).encode(),
                        )
                    await nc.flush()
                finally:
                    await nc.drain()
                for s in fresh:
                    sent.add(s["id"])
                    logger.info("fleetview.research_news %s", s["headline"])
        except Exception as exc:  # noqa: BLE001 -- the loop outlives every failure
            logger.warning("fleetview.research_news sweep failed: %s", exc)
        await _sleep(_every_s())
