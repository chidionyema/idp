"""The voice is warm before anyone asks (2026-10-16, the face's 20s first clause).

A restart happened hours before the founder spoke, and the first /voice/say still paid the lazy
`sovereign.voice` import, the resampler and the first subprocess spawn -- ~20s on the founder's
first words, with every later clause at ~1.35s. warm_voice() runs that cold work at startup, off
the critical path: one free local `say` clause, no router lane spent (on_demand quota: 100 a day).
"""

from __future__ import annotations

import pytest

vm = pytest.importorskip("fleetview_backend.voice_media")


class _Engine:
    TTS_SAMPLE_RATE = 24000


def test_warm_imports_the_engine_and_speaks_one_free_clause(monkeypatch):
    imported = []
    spoken = []
    monkeypatch.setattr(
        vm,
        "_voice_package",
        lambda: (imported.append("engine"), None, None) and (_Engine(), None, None),
    )
    monkeypatch.setattr(
        vm, "_macos_say", lambda text, rate, voice=None: spoken.append((text, rate))
    )

    import asyncio

    asyncio.run(vm.warm_voice())

    assert imported == ["engine"]
    assert spoken == [("ready", 24000)]


def test_warm_survives_an_engine_that_cannot_import(monkeypatch, capsys):
    def boom():
        raise ModuleNotFoundError("No module named 'numpy'")

    spoken = []
    monkeypatch.setattr(vm, "_voice_package", boom)
    monkeypatch.setattr(
        vm, "_macos_say", lambda text, rate, voice=None: spoken.append(text)
    )

    import asyncio

    asyncio.run(vm.warm_voice())  # must not raise

    out = capsys.readouterr().err
    assert "voice.warm import failed" in out
    assert "ModuleNotFoundError" in out
    assert spoken == []


def test_warm_reports_its_seconds(monkeypatch, capsys):
    monkeypatch.setattr(vm, "_voice_package", lambda: (_Engine(), None, None))
    monkeypatch.setattr(vm, "_macos_say", lambda text, rate, voice=None: b"")

    import asyncio

    asyncio.run(vm.warm_voice())

    assert "voice.warm seconds=" in capsys.readouterr().err
