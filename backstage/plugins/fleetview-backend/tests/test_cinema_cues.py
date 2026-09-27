from __future__ import annotations

import asyncio
import json
import sys

import pytest

from fleetview_backend import nats_adapter, routes


def test_cue_frame_shape():
    cue = {
        "target_id": "s1",
        "shot_type": "MACRO_DOV",
        "monologue": "hi",
        "focal_length": 85,
        "dolly_speed": 0.2,
        "timestamp": "2026-09-27T00:00:00Z",
    }
    frame = routes.cue_frame(cue)
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    decoded = json.loads(frame[6:])
    assert decoded["type"] == "cue"
    assert decoded["target_id"] == "s1"
    assert decoded["focal_length"] == 85

    frame2 = routes.cue_frame(
        {"type": "x", "target_id": "s", "shot_type": "ORBIT_FOCUS"}
    )
    decoded2 = json.loads(frame2[6:])
    assert decoded2["type"] == "cue"


class _Msg:
    def __init__(self, data: bytes) -> None:
        self.data = data


def test_decode_skips_malformed():
    good = {"target_id": "s1", "shot_type": "ORBIT_FOCUS"}

    async def _messages():
        yield _Msg(b"not json")
        yield _Msg(b"[1,2]")
        yield _Msg(b'{"shot_type":"ORBIT_FOCUS"}')
        yield _Msg(b"\xff\xfe")
        yield _Msg(json.dumps(good).encode())

    async def _collect():
        return [cue async for cue in nats_adapter.decode_cues(_messages())]

    result = asyncio.run(_collect())
    assert result == [good]


def test_merge_interleaves():
    async def _gen_a():
        yield "a1"
        await asyncio.sleep(0)
        yield "a2"

    async def _gen_b():
        await asyncio.sleep(0)
        yield "b1"

    async def _collect():
        return [item async for item in nats_adapter.merge(_gen_a(), _gen_b())]

    result = asyncio.run(_collect())
    assert sorted(result) == ["a1", "a2", "b1"]
    assert len(result) == 3


def test_merge_propagates_error():
    async def _gen_ok():
        yield "x1"

    async def _gen_bad():
        yield "y1"
        raise RuntimeError("boom")

    async def _consume():
        async for _ in nats_adapter.merge(_gen_ok(), _gen_bad()):
            pass

    with pytest.raises(RuntimeError):
        asyncio.run(_consume())


def test_subscribe_cues_requires_nats(monkeypatch):
    monkeypatch.setitem(sys.modules, "nats", None)

    async def _consume():
        async for _ in nats_adapter.subscribe_cues("nats://x"):
            pass

    with pytest.raises(RuntimeError):
        asyncio.run(_consume())
