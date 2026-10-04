"""/voice/log must report an absent engine, not 500 (2026-04-10).

MEASURED, live, in a real browser at https://catalogue.mumchimp.com/face: after the face mounted,
`GET /api/proxy/fleetview/voice/log?limit=40` answered 500 while its sibling `/voice/log/summary`
answered 200. The pod's own log gave the traceback:

    File ".../fleetview_backend/voice_media.py", line 108, in _voice_package
        from sovereign.voice import catalogue, engine, turnlog
    ModuleNotFoundError: No module named 'sovereign'

That is the documented condition of this image, not a failure of it: the Backstage Dockerfile
builds with `backstage/` as its context (`bin/dockerfiles`), so the repo-root `sovereign/` package
is not installed here. `log_summary` already degrades for exactly this reason (see its docstring,
and `voices()` which catches ImportError with the same explanation). `log` was the sibling the
guard was never added to.

This test drives the real function with `sovereign` absent and asserts the honest shape -- the
same absence a reader would get from `log_summary` -- so the red 500 cannot come back on a page
that otherwise works.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1] / "backstage/plugins/fleetview-backend/src"
    ),
)
from fleetview_backend import voice_media as vm  # noqa: E402


def test_voice_log_degrades_to_a_named_absence_when_the_engine_is_not_in_the_image(
    monkeypatch,
):
    """The live condition: `_voice_package()` raises ModuleNotFoundError."""

    def absent():
        raise ModuleNotFoundError("No module named 'sovereign'")

    monkeypatch.setattr(vm, "_voice_package", absent)

    result = vm.log(limit=40)

    assert isinstance(result, dict), (
        "/voice/log must return a JSON object even when the engine is absent; it returned "
        f"{type(result).__name__}. This is the 2026-04-10 defect: it raised and the route "
        "answered 500 on a page whose sibling route worked."
    )
    assert result.get("available") is False, (
        "/voice/log must say the engine is unavailable (available=False) so a reader can tell "
        f"an absent engine from a quiet one; got {result!r}"
    )
    assert result.get("turns") == [], (
        "an absent engine has no turns; the list must be empty, not missing -- a caller shapes "
        f"its UI from this key. Got {result.get('turns')!r}"
    )
    assert "error" in result and result["error"], (
        "the absence must be named (the `error` key), the way log_summary names it, so the "
        f"console line is a sentence and not a bare 500. Got {result!r}"
    )


def test_voice_log_returns_turns_when_the_engine_is_present(monkeypatch):
    """The other half: a working engine must still return its turns, so the guard did not
    swallow the real answer. A gate that always reports absence cannot fail, and is not a gate."""

    class FakeTurnLog:
        def recent(self, limit):
            return [{"i": 1, "text": "hello"}][:limit]

    monkeypatch.setattr(
        vm, "_voice_package", lambda: (object(), FakeTurnLog(), object())
    )

    result = vm.log(limit=40)

    assert result == {"turns": [{"i": 1, "text": "hello"}]}, (
        f"/voice/log returned {result!r}; with an engine present it must return its turns and "
        "nothing else"
    )
