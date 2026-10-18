"""The face's workers and audio are allowed by the served CSP (2026-10-18).

The founder's face broke with "not allowed by csp": the talking head decodes its .glb in
blob: workers (DRACO), runs lip-sync in an AudioWorklet, and plays spoken replies from
blob: URLs. Helmet's defaults leave worker-src and media-src unset, so they fall back to
script-src / default-src and refuse all three. backend.csp in backstage/app-config.yaml
is the knob (backend-defaults config.schema.json: any helmet-format policy key; false
removes a default) -- this pins the directives the face needs, so removing any one of
them goes red here instead of silently breaking the face again.
"""

from __future__ import annotations

import pathlib
import textwrap

import yaml

BACKSTAGE = pathlib.Path(__file__).resolve().parents[3]
CONFIG = BACKSTAGE / "app-config.yaml"


def _csp() -> dict:
    parsed = yaml.safe_load(CONFIG.read_text())
    csp = parsed["backend"]["csp"]
    assert isinstance(csp, dict), "backend.csp must stay a map of helmet policy keys"
    return csp


def test_config_exists_and_parses() -> None:
    assert CONFIG.exists(), f"{CONFIG} missing"
    _csp()


def test_workers_and_audio_are_allowed() -> None:
    csp = _csp()

    def sources(key: str) -> set[str]:
        value = csp.get(key)
        assert value is not False, (
            f"{key}: false removes the directive; the face needs it"
        )
        assert isinstance(value, list) and value, f"{key} must be a non-empty list"
        return set(value)

    assert "blob:" in sources("worker-src"), textwrap.dedent(
        """\
        worker-src must allow blob: -- DRACO decodes the face model in blob: workers
        and the lip-sync playback runs in an AudioWorklet."""
    )
    assert "blob:" in sources("media-src"), textwrap.dedent(
        """\
        media-src must allow blob: -- spoken replies play from blob: URLs
        (/voice/say returns audio; the face turns it into an object URL)."""
    )
    assert "blob:" in sources("script-src"), "script-src must allow blob: module loads"
    assert "blob:" in sources("connect-src"), "connect-src must allow blob: fetches"
