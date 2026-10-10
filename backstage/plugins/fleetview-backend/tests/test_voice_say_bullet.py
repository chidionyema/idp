"""A clause that starts with a bullet still reaches `say` as speech, not as an option.

2026-10-10: "- two agents working" made macOS `say` exit 1 with "invalid option", and /voice/say
answered 502 for about one clause in eight of a live /face reply.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

vm = pytest.importorskip("fleetview_backend.voice_media")


def _capture(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(argv, **_kw):
        calls.append(argv)
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(shutil, "which", lambda _n: "/usr/bin/say")
    monkeypatch.setattr(subprocess, "run", run)
    return calls


@pytest.mark.parametrize(
    "clause", ["- two agents working", "--stuck one", "• three done", "* four"]
)
def test_bullet_is_not_passed_as_an_option(monkeypatch, clause):
    calls = _capture(monkeypatch)
    vm._macos_say(clause, 24000)
    assert len(calls) == 1
    assert not calls[0][-1].startswith("-")
    assert calls[0][-1].split()[0].isalpha()


def test_bullet_alone_is_not_spoken(monkeypatch):
    calls = _capture(monkeypatch)
    assert vm._macos_say("- ", 24000) is None
    assert calls == []
