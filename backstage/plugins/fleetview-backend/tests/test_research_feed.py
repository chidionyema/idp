"""research_feed: claims through the portal's ONE reader, then onto the news channel.

The contract under test mirrors efficiency_feed's: an unavailable department is an envelope
with a reason (never a raise, never a fabricated empty list), a claim becomes a full
estate.news.story row, and the publish sweep connects to the bus only when it has something
new to say. The reader dials the research-output plugin -- the estate's one Postgres reader
for claims -- over loopback; these tests inject `fetch`, so nothing here needs a portal.
"""

from __future__ import annotations

import asyncio
import json

from fleetview_backend import research_feed, routes


def test_auth_headers_empty_without_token_file(monkeypatch, tmp_path):
    """No FLEETVIEW_RESEARCH_TOKEN_FILE: no header. Dev runs like this; the portal's
    401 then becomes the envelope's reason, which is the soft contract, not an error."""
    monkeypatch.delenv("FLEETVIEW_RESEARCH_TOKEN_FILE", raising=False)
    assert research_feed._auth_headers() == {}


def test_auth_headers_bearer_from_file(monkeypatch, tmp_path):
    """The mounted token file is read per call: rotate the file, the next call carries
    the new token, no restart. A stray newline is the vault's problem, not ours."""
    token_file = tmp_path / "RESEARCH_FEED_TOKEN"
    token_file.write_text("tok-abc\n")
    monkeypatch.setenv("FLEETVIEW_RESEARCH_TOKEN_FILE", str(token_file))
    assert research_feed._auth_headers() == {"Authorization": "Bearer tok-abc"}
    token_file.write_text("tok-xyz")
    assert research_feed._auth_headers() == {"Authorization": "Bearer tok-xyz"}


def test_auth_headers_missing_file_is_no_header(monkeypatch, tmp_path):
    """A declared file that is not mounted yet (optional: true volume, vault field
    pending) degrades to headerless -- the same shape as an unset path."""
    monkeypatch.setenv("FLEETVIEW_RESEARCH_TOKEN_FILE", str(tmp_path / "absent"))
    assert research_feed._auth_headers() == {}


def _portal(status: int, body: dict | str):
    """A fetch seam shaped like research_feed._http_get."""

    def _fetch(url: str):
        raw = body if isinstance(body, str) else json.dumps(body)
        return status, raw

    return _fetch


def _reset_cache() -> None:
    research_feed._cache.update(at=0.0, body=None)


def _claims(now: str = "2026-10-12T09:00:00Z") -> dict:
    return {
        "available": True,
        "count": 2,
        "claims": [
            {
                "created_at": now,
                "status": "verified",
                "statement": "Estate agents land 3x faster via the Greenlane.",
            },
            {
                "created_at": "2026-10-11T09:00:00Z",
                "status": "unverified",
                "statement": "Older claim.",
            },
        ],
    }


def test_unavailable_portal_is_an_envelope_with_a_reason():
    _reset_cache()

    def boom(url: str):
        raise ConnectionError("portal down")

    body = research_feed.research_claims(fetch=boom)
    assert body["available"] is False
    assert "portal down" in body["error"]
    _reset_cache()


def test_claims_come_back_through_the_seam():
    _reset_cache()
    body = research_feed.research_claims(fetch=_portal(200, _claims()))
    assert body["available"] is True
    assert body["count"] == 2
    assert body["claims"][0]["statement"].startswith("Estate agents")
    _reset_cache()


def test_claim_becomes_a_full_news_story_row():
    story = research_feed.claim_story(_claims()["claims"][0])
    # The full contract: parseStory on the room side refuses rows missing any of these.
    for key in (
        "id",
        "channel",
        "source",
        "severity",
        "state",
        "headline",
        "anchor",
        "entity",
        "evidence",
        "score",
        "count",
        "breaking",
        "first_at",
        "at",
    ):
        assert key in story, key
    assert story["channel"] == "news"
    assert story["source"] == "estate.research"
    assert story["state"] == "confirmed"  # status verified
    assert story["id"] == research_feed.claim_story(_claims()["claims"][0])["id"]


def test_malformed_claims_produce_no_story():
    assert research_feed.claim_story({"statement": "", "created_at": ""}) is None
    assert research_feed.claim_story({}) is None


def test_estate_envelope_joins_green_burn_and_research(monkeypatch):
    from fleetview_backend import research_feed, spend

    # estate_envelope imports its parts inside the call; pin them as module attributes so
    # the monkeypatched seams are the ones the envelope actually resolves.
    monkeypatch.setattr(routes, "research_feed", research_feed, raising=False)
    monkeypatch.setattr(routes, "spend", spend, raising=False)
    # the envelope reads the cached lane status, never the slow `gh api` read inline
    monkeypatch.setattr(
        routes.greenlane,
        "greenlane_status_nowait",
        lambda now=None: {"available": False, "error": "no bin/idp-greenlane"},
    )
    monkeypatch.setattr(
        research_feed,
        "research_claims",
        lambda: {"available": True, "count": 1, "claims": _claims()["claims"][:1]},
    )
    monkeypatch.setattr(
        spend, "spend_total", lambda: {"measured": False, "reason": "unset"}
    )
    body, status = routes.estate_envelope()
    assert status == 200
    # One dead part is unavailable WITH ITS REASON while the others still answer.
    assert body["green"]["available"] is False
    assert body["burn"]["measured"] is False
    assert body["research"]["available"] is True
    assert body["generated_at"]


def test_publish_sweep_publishes_only_the_newest_claim_on_first_sight(monkeypatch):
    _reset_cache()
    published: list[tuple[str, dict]] = []

    class _FakeNats:
        async def publish(self, subject, payload):
            published.append((subject, json.loads(payload)))

        async def flush(self):
            return None

        async def drain(self):
            return None

    class _FakeNatsModule:
        @staticmethod
        async def connect(*a, **k):
            return _FakeNats()

    import sys

    monkeypatch.setitem(sys.modules, "nats", _FakeNatsModule)

    # One sweep, by making the sweep's sleep raise the stop sentinel.
    class _Stop(Exception):
        pass

    async def stop_sleep(seconds):
        raise _Stop()

    monkeypatch.setattr(research_feed, "_sleep", stop_sleep)
    monkeypatch.setattr(
        research_feed,
        "research_claims",
        lambda: {"available": True, "count": 2, "claims": _claims()["claims"]},
    )

    async def one_sweep():
        try:
            await research_feed.publish_claims("nats://test")
        except _Stop:
            pass

    asyncio.run(one_sweep())
    # The first sweep PRIMES silently and replays only the single newest claim.
    assert len(published) == 1
    subject, story = published[0]
    assert subject == "estate.news.story.news"
    assert story["headline"].startswith("Estate agents")
    _reset_cache()
