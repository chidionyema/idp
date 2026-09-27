from __future__ import annotations

import asyncio
import json
import logging

from fleetview_backend import nats_adapter, routes


class _Msg:
    def __init__(self, data: bytes, subject: str) -> None:
        self.data = data
        self.subject = subject


def _story(**overrides) -> dict:
    story = {
        "id": "s1",
        "channel": "deploys",
        "source": "director",
        "severity": "warn",
        "state": "reported",
        "headline": "Flux converged",
        "anchor": "flux",
        "entity": "idp",
        "evidence": [],
        "score": 4,
        "count": 1,
        "breaking": False,
        "first_at": "2026-09-27T00:00:00Z",
        "at": "2026-09-27T00:00:00Z",
    }
    story.update(overrides)
    return story


def test_decode_stories_good():
    good = _story()

    async def _messages():
        yield _Msg(json.dumps(good).encode(), "estate.news.story.deploys")

    async def _collect():
        return [item async for item in nats_adapter.decode_stories(_messages())]

    result = asyncio.run(_collect())
    assert result == [("deploys", good)]


def test_decode_stories_skips_malformed_json():
    async def _messages():
        yield _Msg(b"not json", "estate.news.story.news")
        yield _Msg(b"[1,2]", "estate.news.story.news")
        yield _Msg(b"\xff\xfe", "estate.news.story.news")

    async def _collect():
        return [item async for item in nats_adapter.decode_stories(_messages())]

    assert asyncio.run(_collect()) == []


def test_decode_stories_skips_missing_fields():
    missing_id = _story()
    missing_id["id"] = ""
    missing_headline = _story()
    del missing_headline["headline"]
    missing_channel = _story()
    missing_channel["channel"] = ""
    bad_severity = _story()
    bad_severity["severity"] = "critical"

    async def _messages():
        for obj in (missing_id, missing_headline, missing_channel, bad_severity):
            yield _Msg(json.dumps(obj).encode(), "estate.news.story.news")

    async def _collect():
        return [item async for item in nats_adapter.decode_stories(_messages())]

    assert asyncio.run(_collect()) == []


def test_decode_stories_on_uses_last_subject_token():
    story = _story(id="s2", channel="deploys")

    async def _messages():
        yield _Msg(json.dumps(story).encode(), "estate.news.story.news")

    async def _collect():
        return [item async for item in nats_adapter.decode_stories(_messages())]

    result = asyncio.run(_collect())
    assert result == [("news", story)]


def test_story_frame_shape():
    story = _story()
    frame = routes.story_frame("deploys", story)
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    decoded = json.loads(frame[6:])
    assert decoded["type"] == "story"
    assert decoded["on"] == "deploys"
    assert decoded["story"] == story


def test_isolated_swallows_and_logs(caplog):
    async def _boom():
        yield "ok1"
        raise RuntimeError("bus down")

    async def _collect():
        return [item async for item in nats_adapter.isolated("stories", _boom())]

    with caplog.at_level(logging.INFO, logger=nats_adapter.__name__):
        result = asyncio.run(_collect())

    assert result == ["ok1"]
    assert any(
        "fleetview.stream_source_down" in r.message and "source=stories" in r.message
        for r in caplog.records
    )


def test_isolated_failure_does_not_stop_other_merged_source():
    async def _boom():
        yield "bad1"
        raise RuntimeError("boom")

    async def _ok():
        await asyncio.sleep(0)
        yield "good1"
        await asyncio.sleep(0)
        yield "good2"

    async def _collect():
        return [
            item
            async for item in nats_adapter.merge(
                nats_adapter.isolated("bad", _boom()),
                nats_adapter.isolated("good", _ok()),
            )
        ]

    result = asyncio.run(_collect())
    assert sorted(result) == ["bad1", "good1", "good2"]
