"""The face speaks in a woman's voice -- on a fresh pod most of all.

2026-10-10, the founder on /face: "male voice". The cause was two defaults and both were a man's:
the backend fell back to `DEFAULT_CLOUD_VOICE = "troy"` (voice_media.py) and the surface started in
`voice: 'troy'` (useEstateVoice.ts). Both now say "hannah".

WHY THE DEFAULT IS THE THING TO TEST. The choice file lives at `~/.estate/voice-choice.json` in the
pod's home, and no volume backs that home -- so every deploy forgets the founder's pick and the
DEFAULT is what is actually heard until someone picks again. A default that is a man's voice is
therefore not a cosmetic fallback; it is the voice of the face after every deploy.

`troy`, `austin` and `daniel` are the men in Orpheus's English set and `hannah`, `diana` and
`autumn` the women. The catalogue is split by name here rather than the assertion being written in
prose, so "the default is a woman's" is checked against the voice set, and a new Orpheus voice has
to be classified by a person before it can quietly become the default.

A FOURTH default was a man's, and it outlived the first two (measured 2026-10-12): the macOS `say`
leg in `sovereign/voice/engine.py` fell back to `Zarvox` -- macOS's novelty robot -- while this
side's `voice_media.py` fell back to `Samantha`. `/voice/voices` in production reported
`{"kokoro":"af_heart","say":"Zarvox","piper":"en_US-lessac-medium","cloud":"hannah"}`:
three women and a robot, and no manifest sets `VOICE_SAY_VOICE`, so the engine's default is what
the founder's laptop speaks with. The two sides are one voice now, and the test below holds them
together -- either side changing alone goes red.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

vm = pytest.importorskip("fleetview_backend.voice_media")

REPO = Path(__file__).resolve().parents[4]

WOMENS = {"hannah", "diana", "autumn"}
MENS = {"troy", "austin", "daniel"}

# macOS ships a woman's voice per region (Samantha, Karen, Moira, Tessa) plus a set of NOVELTY
# voices -- Zarvox, Fred, Junior, Bells, Boing -- which are characters and sound effects, not
# speakers. The estate's face speaks as a woman, so its `say` default must come from this side.
MACOS_WOMENS = {
    "Samantha",
    "Karen",
    "Moira",
    "Tessa",
    "Victoria",
    "Fiona",
    "Allison",
    "Ava",
    "Susan",
}


def test_the_default_voice_is_a_womans() -> None:
    assert vm.DEFAULT_CLOUD_VOICE in WOMENS, (
        f"the face is a woman's but its default voice is {vm.DEFAULT_CLOUD_VOICE!r}"
    )


def test_every_cloud_voice_is_called_a_man_or_a_woman() -> None:
    """A new Orpheus voice must be classified before it can become the default by accident."""
    assert set(vm.CLOUD_VOICES) == WOMENS | MENS, (
        "an Orpheus voice arrived unclassified: add it to the men or the women in this file"
    )


def test_a_fresh_pod_speaks_as_the_woman_not_a_man(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No choice file -- every deploy -- must not mean a man's voice."""
    monkeypatch.setattr(vm, "_CHOICE_FILE", tmp_path / "no-choice-file.json")
    monkeypatch.delenv("VOICE_CLOUD_VOICE", raising=False)
    assert vm._load_choice() == {"engine": "cloud", "voice": "hannah"}


def test_the_founders_pick_still_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The default must not override a voice that was chosen."""
    choice = tmp_path / "voice-choice.json"
    choice.write_text('{"engine": "cloud", "voice": "diana"}')
    monkeypatch.setattr(vm, "_CHOICE_FILE", choice)
    assert vm._load_choice() == {"engine": "cloud", "voice": "diana"}


def test_the_surface_starts_in_the_same_voice_as_the_backend() -> None:
    """Two defaults, one voice.

    The surface and the backend each carry a default, and they disagreed once already. Reading the
    hook's constant and comparing it with the backend's is the only thing that catches a drift
    where only one side is changed.
    """
    hook = (
        REPO / "backstage/packages/app/src/modules/home/useEstateVoice.ts"
    ).read_text()
    found = re.search(r"export const DEFAULT_VOICE = '([a-z]+)'", hook)
    assert found, "the face hook must declare the voice it starts in, as DEFAULT_VOICE"
    assert found.group(1) == vm.DEFAULT_CLOUD_VOICE, (
        f"the surface starts in {found.group(1)!r} and the backend defaults to "
        f"{vm.DEFAULT_CLOUD_VOICE!r}; the founder hears the backend's"
    )


def test_the_macos_say_default_is_a_womans_and_the_two_sides_agree() -> None:
    """The engine's `say` fallback is a woman's, and it is the SAME woman's as this side's.

    `Zarvox` was live (see the module docstring): three of the estate's four voice defaults were a
    woman's and the fourth was macOS's novelty robot, which is what a laptop with no Orpheus quota
    left actually spoke with. Reading both defaults out of the source and comparing them is the
    only thing that catches a drift where one side is changed alone -- the same reason the surface
    and backend defaults are compared above.
    """
    engine = (REPO / "sovereign/voice/engine.py").read_text()
    found = re.search(
        r'SAY_VOICE = os\.environ\.get\("VOICE_SAY_VOICE", "([^"]+)"\)', engine
    )
    assert found, "engine.py must declare the macOS say voice it falls back to"
    say = found.group(1)
    assert say in MACOS_WOMENS, (
        f"the macOS say fallback is {say!r} -- a novelty voice or a man's; the face is a woman's"
    )
    media = (
        REPO
        / "backstage/plugins/fleetview-backend/src/fleetview_backend/voice_media.py"
    ).read_text()
    other = re.search(r'os\.environ\.get\("VOICE_SAY_VOICE", "([^"]+)"\)', media)
    assert other, "voice_media.py must declare the macOS say voice it falls back to"
    assert say == other.group(1), (
        f"engine.py falls back to {say!r} and voice_media.py to {other.group(1)!r}; the estate "
        "has one voice, and a pod's `say` leg is not a different person from the laptop's"
    )
