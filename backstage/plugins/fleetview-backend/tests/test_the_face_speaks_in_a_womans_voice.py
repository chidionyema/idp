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
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

vm = pytest.importorskip("fleetview_backend.voice_media")

REPO = Path(__file__).resolve().parents[4]

WOMENS = {"hannah", "diana", "autumn"}
MENS = {"troy", "austin", "daniel"}


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
