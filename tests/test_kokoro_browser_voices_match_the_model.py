"""The browser's Kokoro voice list must be the model's own list, not a copy that drifted.

WHY THIS FILE EXISTS. `backstage/packages/app/src/modules/home/browserKokoro.ts` carries the 54
Kokoro voice names because the browser cannot read them from anywhere: `kokoro-js` exports only
KokoroTTS/TextSplitterStream/env (measured 2026-10-12 on the installed 1.2.1 -- its `dist/kokoro.js`
ends `export{M as KokoroTTS,w as TextSplitterStream,Q as env}`), and the voices archive lives on the
server, not on the phone. A hand-kept list of model names is exactly the kind of copy that goes
stale quietly, so two guards stand over it:

  * the SHAPE (54 entries, sorted, unique, the model's naming) always, and
  * the EXACT LIST against `sovereign.voice.catalogue.kokoro_voices()` on any host that has
    `voices-v1.0.bin`.

The exact-list half cannot run in CI, where the 28MB archive is absent -- that is a real limit, and
it is stated rather than hidden. What CAN run everywhere is the third test: the model id the browser
picker loads and the one `hooks/useSpeculativeVoice.ts` loads must be the same string, or the estate
would hold two Kokoro models (AGENTS.md §6).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BROWSER = REPO / "backstage/packages/app/src/modules/home/browserKokoro.ts"
SPECULATIVE = REPO / "backstage/packages/app/src/hooks/useSpeculativeVoice.ts"


def browser_kokoro_voices() -> list[str]:
    """The list as the browser bundle actually carries it, read from its own source."""
    text = BROWSER.read_text()
    match = re.search(
        r"BROWSER_KOKORO_VOICES: readonly string\[\] = \[(.*?)\];", text, re.S
    )
    assert match, (
        "BROWSER_KOKORO_VOICES is no longer a `readonly string[]` literal in browserKokoro.ts"
    )
    return re.findall(r"'([a-z0-9_]+)'", match.group(1))


def test_the_browser_list_has_the_shape_of_the_model() -> None:
    voices = browser_kokoro_voices()
    assert len(voices) == 54, (
        f"Kokoro v1.0 has 54 voices; the browser list has {len(voices)}"
    )
    assert len(set(voices)) == len(voices), "a voice is listed twice"
    assert voices == sorted(voices), "the list is no longer in the model's own order"
    # `af_heart` is `sovereign/voice/engine.KOKORO_VOICE` -- the estate's default. A list without it
    # would offer 54 voices and omit the one every server picks.
    assert "af_heart" in voices
    for name in voices:
        assert re.fullmatch(r"[a-z]{2}_[a-z]+", name), (
            f"{name!r} is not a Kokoro voice id"
        )


def test_the_browser_list_is_the_models_own_list() -> None:
    """Character-for-character equal to what the server-side lister reads out of the archive."""
    sys.path.insert(0, str(REPO))
    from sovereign.voice import catalogue, engine  # noqa: PLC0415

    if not os.path.exists(engine.KOKORO_VOICES):
        pytest.skip(
            f"no {engine.KOKORO_VOICES} on this host -- the archive is 28MB and is not in CI, so "
            "this comparison runs on a machine that has the models (the founder's laptop does)"
        )
    assert browser_kokoro_voices() == catalogue.kokoro_voices()


def test_one_kokoro_model_for_the_whole_estate() -> None:
    """The picker and the speculative pipeline must not name two different Kokoro models."""
    browser = re.search(r"KOKORO_WEB_MODEL = '([^']+)'", BROWSER.read_text())
    speculative = re.search(r"KOKORO_MODEL = '([^']+)'", SPECULATIVE.read_text())
    assert browser and speculative, (
        "one of the two model constants moved or was renamed"
    )
    assert browser.group(1) == speculative.group(1)
