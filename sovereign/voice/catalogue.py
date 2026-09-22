"""The voice catalogue and the live selection, as plain functions with no transport attached.

WHY THIS FILE EXISTS. These two answers -- "what can this host speak with" and "speak with that
one from now on" -- were written inside `server.py`, the WebSocket app the board used to dial on
127.0.0.1:8899. The board no longer dials it (the transport moved onto the FleetView backend and
the estate bus, 2026-09-22), and the second surface needed the same two answers. Copying them
would have made a second catalogue that drifts from the first -- and a duplicate layer is the one
thing the estate deletes on sight. So they moved down here, where both transports call the same
code, and neither owns it.

Everything here is SYNCHRONOUS and returns plain data. The Kokoro load is tens of seconds on this
class of CPU, so a caller on an event loop must run `select()` in a thread; that is the caller's
decision to make, and an `async def` here would have forced it on every caller including the CLI.
"""

from __future__ import annotations

import os
import zipfile

from . import engine

# macOS ships these as real, installed, selectable voices. They say "Doo da doo da dum". None of
# them is a candidate for reading a fleet report aloud, so they are filtered by name rather than
# left in a 40-entry picker for a person to learn to avoid.
NOVELTY = {
    "Albert",
    "Bad News",
    "Bahh",
    "Bells",
    "Boing",
    "Bubbles",
    "Cellos",
    "Fred",
    "Good News",
    "Jester",
    "Junior",
    "Organ",
    "Superstar",
    "Trinoids",
    "Whisper",
    "Wobble",
    "Zarvox",
}

ENGINES = ("say", "kokoro", "piper")


def kokoro_voices() -> list[str]:
    """Every Kokoro voice, WHETHER OR NOT THE MODEL IS LOADED.

    Measured 2026-09-19: the founder opened the picker looking for the kokoro voice he had been
    using and it was not there -- because the list was read from `m.tts`, which is None until the
    model loads, and the model only loads when kokoro is selected. So the way to find a kokoro
    voice was to already be using one.

    The fallback reads the voices FILE, which is a torch `.pt` -- and a `.pt` is a ZIP ARCHIVE, so
    its voice names are just its member filenames. The directory listing gives all 54 names with
    no onnxruntime session, no 350MB model load, and without installing torch (a 2GB dependency)
    purely to list strings.
    """
    m = engine.models()
    if m.tts is not None:
        try:
            return sorted(m.tts.get_voices())
        except Exception:  # noqa: BLE001 -- a model that cannot list voices still speaks
            pass
    try:
        with zipfile.ZipFile(engine.KOKORO_VOICES) as z:
            return sorted(n[:-4] for n in z.namelist() if n.endswith(".npy"))
    except Exception:  # noqa: BLE001 -- an unreadable file is not fatal; the list is empty
        return []


def say_voices() -> list[str]:
    """The English macOS voices on this host, novelty entries removed."""
    import subprocess  # noqa: PLC0415

    if not os.path.exists("/usr/bin/say"):
        return []
    try:
        out = subprocess.run(
            ["/usr/bin/say", "-v", "?"], capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:  # noqa: BLE001 -- a host that cannot list voices still serves the page
        return []
    names: list[str] = []
    for line in out.splitlines():
        # `Name (English (UK))   en_GB   # example`
        head = line.split("#")[0].strip()
        if not head:
            continue
        parts = head.split()
        if len(parts) < 2:
            continue
        locale = parts[-1]
        name = " ".join(parts[:-1]).strip()
        if not locale.startswith("en_") or name in NOVELTY:
            continue
        names.append(name)
    return sorted(set(names))


def catalogue() -> dict:
    """Every voice this host can speak with, so the choice belongs to the person listening.

    WHY THE CHOICE IS OFFERED AT ALL. Choosing a voice was an edit to engine.py and a restart --
    so the founder was told to pick between two voices somebody else had already narrowed to, and
    said, correctly, "why do i have to take my pick". The two engines ship 60+ voices between
    them; there was never a reason to offer two.
    """
    m = engine.models()
    return {
        "engine": m.tts_engine,
        "current": {
            "engine": m.tts_engine,
            "kokoro": engine.KOKORO_VOICE,
            "say": engine.SAY_VOICE,
            "piper": engine.PIPER_VOICE,
        },
        "kokoro": kokoro_voices(),
        "say": say_voices(),
        # Piper voices present on this host, listed from DISK so the picker is complete whether or
        # not a voice has been used yet -- the same fault that hid the Kokoro voices until one was
        # already selected.
        "piper": engine.piper_voices(),
    }


def select(want_engine: str, want_voice: str) -> tuple[dict, int]:
    """Switch the speaking voice at runtime. No restart, no edit, no deploy.

    Returns the state now live and 200, or an error body and its status. Kokoro's model is loaded
    on first selection, because a host that prefers a macOS voice should never pay the 350MB model
    load to be told it can also use Kokoro. That load BLOCKS -- see this module's docstring.
    """
    want_engine = (want_engine or "").strip().lower()
    want_voice = (want_voice or "").strip()
    if want_engine not in ENGINES:
        return {"error": f"engine must be one of {', '.join(ENGINES)}"}, 400
    if not want_voice:
        return {"error": "voice is required"}, 400

    m = engine.models()

    if want_engine == "piper":
        if not engine.piper_voices():
            return {"error": f"no Piper voices in {engine.PIPER_DIR}"}, 400
        engine.PIPER_VOICE = want_voice
        m.tts_engine = "piper"
        m.tts_model = f"piper:{want_voice}"
        return {"engine": "piper", "voice": want_voice}, 200

    if want_engine == "say":
        if not os.path.exists("/usr/bin/say"):
            return {"error": "no /usr/bin/say on this host"}, 400
        engine.SAY_VOICE = want_voice
        m.tts_engine = "say"
        m.tts_model = f"say:{want_voice}"
        return {"engine": "say", "voice": want_voice}, 200

    if m.tts is None:
        engine.ensure_kokoro()
    if m.tts is None:
        return {"error": "kokoro model is not available on this host"}, 503
    engine.KOKORO_VOICE = want_voice
    m.tts_engine = "kokoro"
    m.tts_model = os.path.basename(engine.KOKORO_MODEL)
    return {"engine": "kokoro", "voice": want_voice}, 200


def preview(want_engine: str, want_voice: str, text: str) -> tuple[bytes | None, str | None]:
    """Speak one sentence in a candidate voice WITHOUT making it live.

    Returns (pcm, None) or (None, reason). Auditioning a voice should not change the voice
    mid-conversation, and it should not require applying first and undoing after. The PCM is the
    same 24kHz float32 the answer path sends, so what you hear in the preview is exactly what you
    will hear on a turn.
    """
    want_engine = (want_engine or "").strip().lower()
    want_voice = (want_voice or "").strip()
    if want_engine not in ENGINES or not want_voice:
        return None, f"engine ({'|'.join(ENGINES)}) and voice are required"

    if want_engine == "say":
        if not os.path.exists("/usr/bin/say"):
            return None, "no /usr/bin/say here"
        return engine.synthesise_say_with(want_voice, text), None
    if want_engine == "piper":
        return engine.synthesise_piper_with(want_voice, text), None

    # LOAD KOKORO ON DEMAND FOR A PREVIEW TOO. It returned 503 when the model was not loaded,
    # which made the picker show 54 kokoro voices that could not be auditioned until one had
    # already been applied -- the same "you must already be using it to choose it" fault that hid
    # af_heart in the first place. The first preview pays the load; every later one does not.
    m = engine.models()
    if m.tts is None:
        engine.ensure_kokoro()
    if m.tts is None:
        return None, "kokoro model is unavailable on this host"
    return engine.synthesise_kokoro_with(want_voice, text), None
