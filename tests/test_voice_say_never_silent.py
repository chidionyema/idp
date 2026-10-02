"""/voice/say must not go silent when the chosen local engine is absent (2026-09-30: the saved
choice was kokoro, the host had no Kokoro voices, every spoken reply was a 502 while the router's
voice and macOS `say` both worked). Drives the real `voice_media.say` with the engines stubbed."""

import asyncio
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1] / "backstage/plugins/fleetview-backend/src"
    ),
)
from fleetview_backend import voice_media as vm  # noqa: E402


@pytest.fixture()
def absent_kokoro(monkeypatch):
    engine = types.SimpleNamespace(TTS_SAMPLE_RATE=24000, synthesise=lambda text: b"")
    monkeypatch.setattr(vm, "_voice_package", lambda: (engine, None, None))
    monkeypatch.setattr(vm, "_choice", {"engine": "kokoro", "voice": "af_aoede"})
    monkeypatch.setattr(vm, "_log_engine", lambda *a: None)
    return monkeypatch


def test_router_voice_answers_when_kokoro_is_absent(absent_kokoro):
    async def router(text, rate, voice):
        return b"router-pcm"

    absent_kokoro.setattr(vm, "_router_synthesise", router)
    absent_kokoro.setattr(vm, "_macos_say", lambda *a: None)
    assert asyncio.run(vm.say("hello")) == (b"router-pcm", None)


def test_macos_voice_answers_when_kokoro_and_router_are_both_down(absent_kokoro):
    async def router(text, rate, voice):
        return None

    absent_kokoro.setattr(vm, "_router_synthesise", router)
    absent_kokoro.setattr(vm, "_macos_say", lambda *a: b"say-pcm")
    assert asyncio.run(vm.say("hello")) == (b"say-pcm", None)


def test_every_engine_down_is_a_named_refusal(absent_kokoro):
    async def router(text, rate, voice):
        return None

    absent_kokoro.setattr(vm, "_router_synthesise", router)
    absent_kokoro.setattr(vm, "_macos_say", lambda *a: None)
    pcm, err = asyncio.run(vm.say("hello"))
    assert pcm is None and "no audio" in err
