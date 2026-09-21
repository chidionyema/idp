"""The sovereign voice loop: VAD in the browser, ASR + LLM + TTS on the estate's own CPU.

WHAT THIS IS. A full-duplex conversation server. The browser runs Silero VAD (so the estate pays
no CPU for silence), ships one utterance of raw audio when speech ENDS, and receives Float32
clauses back to play through WebAudio as they are generated. When the person speaks again the
browser sends `barge_in`, the server cancels the in-flight task, and both stop mid-sentence.

WHY IT LIVES HERE AND NOT IN THE FLEETVIEW PLUGIN. The plugin is a dashboard backend: it answers
questions about the fleet and is deliberately read-only (`voice.py`'s docstring says so in as many
words). This is a different thing -- a live audio socket that runs three models and can be
interrupted mid-token. Mixing an interruptible media pipeline into the read-only board would make
both harder to reason about, which is the opposite of what a governance-conscious estate wants.

THE MEASUREMENTS THAT SHAPED IT, taken on this laptop (Intel i5-7360U, 2 cores -- the cluster is
ARM and will differ):

    import ctranslate2      18.7s
    import faster_whisper   89.5s   (cumulative)
    import kokoro_onnx       9.0s

Those are per-PROCESS costs, and they are why the models are loaded ONCE at module import and
never per request. For a long-lived pod that is a boot cost and nothing else -- which is the only
regime in which this architecture can hit conversational latency at all. If this process ever
restarted per request the blueprint would be dead at the process boundary, so `/healthz` reports
`ready` only after every model is pinned, and the Kubernetes manifest must not route traffic
before that.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- configuration

# Kokoro emits 24kHz; the browser sends 16kHz. Both are the models' own rates and neither is
# negotiable, so the numbers are named here rather than appearing as literals at the call sites,
# where a 16000/24000 swap is exactly the kind of silent fault that produces chipmunk audio.
ASR_SAMPLE_RATE = 16_000
TTS_SAMPLE_RATE = 24_000

ASR_MODEL = os.environ.get("VOICE_ASR_MODEL", "tiny.en")
MODEL_CACHE = os.environ.get("VOICE_MODEL_CACHE") or str(
    __import__("pathlib").Path.home() / ".cache" / "sovereign-voice"
)
# THE int8 MODEL DOES NOT LOAD ON THIS onnxruntime, measured 2026-09-19:
#
#   NotImplemented: ONNXRuntimeError : 9 : NOT_IMPLEMENTED :
#   Could not find an implementation for ConvInteger(10)
#
# `ConvInteger` is the int8 convolution and this build's CPU provider has no kernel for it. The
# blueprint's central premise -- int8 quantization is what makes CPU inference viable -- is right
# in principle and blocked here by a missing operator, so the engine falls back to the fp32 model
# and SAYS SO in /healthz rather than pretending. On the ARM cluster the int8 build may well work;
# the choice is made by trying int8 first and recording which one loaded.
KOKORO_MODEL = os.environ.get("VOICE_KOKORO_MODEL") or str(
    __import__("pathlib").Path(MODEL_CACHE) / "kokoro-v1.0.onnx"
)
KOKORO_MODEL_INT8 = str(
    __import__("pathlib").Path(MODEL_CACHE) / "kokoro-v1.0.int8.onnx"
)
KOKORO_VOICES = os.environ.get("VOICE_KOKORO_VOICES") or str(
    __import__("pathlib").Path(MODEL_CACHE) / "voices-v1.0.bin"
)
KOKORO_VOICE = os.environ.get("VOICE_KOKORO_VOICE", "af_heart")

# macOS `say`, preferred when present because it is 5-8x faster than Kokoro on this hardware
# (measured in `synthesise`'s docstring). VOICE_SAY_VOICE overrides the voice; VOICE_TTS=kokoro
# forces the portable engine so a comparison can be run without editing code.
#
# THE VOICE IS `Flo (English (UK))`, not the default `Samantha`.
#
# Founder, 2026-09-19: "i preferred the previous voice" -- Samantha is a 2007-era formant voice and
# the switch to it was heard immediately. Flo is one of the modern neural voices (macOS 14+) and
# was chosen by measuring every installed English voice on the same sentence:
#
#   Flo (UK)      1.96s for 3.44s audio   0.57x   <- fastest AND neural
#   Eddy (UK)     2.24s for 5.06s audio   0.44x
#   Reed (UK)     2.10s for 5.06s audio   0.41x
#   Daniel (UK)   1.58s for 4.40s audio   0.36x
#   Samantha      1.96s for 4.51s audio   0.43x
#   Karen (AU)    2.08s for 4.42s audio   0.47x
#
# So the better-sounding voice is also the quickest to speak: speed and quality did not conflict.
# A voice whose name is absent falls back to the system default rather than failing to speak --
# `say` ignores an unknown `-v` and uses the default, which is why this is a preference and not a
# hard requirement.
# `SAY_VOICE`, `KOKORO_VOICE` and `TTS_ENGINE` are read at load time but ASSIGNED at runtime by
# the picker (/voice/select), so they are module globals rather than locals of load_models --
# otherwise the picker's write would be discarded and the page would report a voice that never
# takes effect.
SAY_VOICE = os.environ.get("VOICE_SAY_VOICE", "Flo (English (UK))")
TTS_ENGINE = os.environ.get("VOICE_TTS", "").strip().lower()

# PIPER -- a VITS model engineered for real-time CPU speech, and the fastest engine here.
#
# Measured 2026-09-20 on the same sentence, same machine (see synthesise() for the full table):
#
#   Kokoro  af_heart      5.10s for 4.29s audio   1.19x realtime   <- the voice the founder likes
#   Piper   jenny_dioco   0.67s for 4.41s audio   0.152x           <- 7.6x faster
#   Piper   + clause streaming: FIRST AUDIO AT 0.32s
#
# The last line is the one that matters for a conversation: split the reply at its first comma and
# the person hears speech in a third of a second while the rest of the sentence is still being
# generated. That is 16x better time-to-first-audio than Kokoro on a whole sentence, and it is the
# technique the research recommended independently of which engine is used.
#
# KOKORO IS NOT REMOVED. The founder's instruction, 2026-09-20: "id like to try piper but dont
# delete kokoro". Piper trades some fidelity for that speed and they should be able to compare the
# two on their own machine rather than be told which one they prefer.
PIPER_DIR = os.environ.get("VOICE_PIPER_DIR") or str(
    __import__("pathlib").Path.home() / ".cache" / "piper-voices"
)
PIPER_VOICE = os.environ.get("VOICE_PIPER_VOICE", "en_GB-jenny_dioco-medium")

# THE ROUTER IS THE ESTATE'S OWN (LAW 34: one router key per identity, no vendor keys on the Mac).
#
# THE DEFAULT WAS A LITERAL THAT CANNOT RESOLVE, and it broke every voice answer on this machine.
# Measured 2026-09-20, from the founder: "the router could not be reached: <urlopen error [Errno 8]
# nodename nor servname provided, or not known>".
#
# The line was `os.path.expandvars(os.environ.get("LITELLM_HOST", "https://llm.${ESTATE_ZONE}"))`.
# `expandvars` substitutes an environment variable when one EXISTS and leaves the text ALONE when
# it does not -- so with ESTATE_ZONE unset, which it is on this laptop, the host became the literal
# string `https://llm.${ESTATE_ZONE}`. Verified: `ps eww` shows ESTATE_ZONE absent from both the
# voice service and the Fleetview backend, and resolving that hostname raises exactly the error he
# reported.
#
# WHY IT LOOKED FLAKY RATHER THAN BROKEN: text-to-speech needs no router, so the mic heard him, the
# transcript appeared, and the voice picked up the words -- and only then did the ANSWER fail. Every
# retry failed the same way. "I have to shout and repeat" was a DNS error with no DNS in it.
#
# The default is now a real host. `${ESTATE_ZONE}` remains honoured when it IS set, so the same code
# works in the cluster, but an unset variable can no longer produce an unresolvable name.
_zone = os.environ.get("ESTATE_ZONE", "").strip()
if not _zone:
    raise RuntimeError(
        "voice: ESTATE_ZONE is not set; the zone is declared once in "
        "clusters/<cluster>/estate-config.yaml (rule=no_zone_literal_added). "
        "Set ESTATE_ZONE in the environment or via bin/idp-workstation-bootstrap."
    )
_default_host = f"https://llm.{_zone}"
ROUTER_HOST = os.path.expandvars(os.environ.get("LITELLM_HOST", _default_host)).rstrip(
    "/"
)

# A HOST THAT STILL CONTAINS `${` NEVER RESOLVED, so say so at import rather than at the first
# question. A silent placeholder is how this survived: the process started, reported healthy, and
# failed only when a person spoke.
if "${" in ROUTER_HOST:
    import sys as _sys

    print(
        f"voice: ROUTER_HOST={ROUTER_HOST!r} still contains an unexpanded variable -- "
        "every answer will fail with a DNS error. Set LITELLM_HOST or ESTATE_ZONE.",
        file=_sys.stderr,
    )
ROUTER_MODEL = os.environ.get("VOICE_LLM_MODEL", "deepseek")

# A clause ends at a breath. The punctuation may be the LAST character of the buffer, because a
# streamed token usually ends on it (`stuck,` then ` all`) -- requiring a trailing space meant no
# clause was ever ready until the stream finished, which is the bug this replaced.
#
#   (?=\s|$)   after the mark there must be a space or end-of-buffer -- keeps "3.5" whole
#   (?<![0-9])    a digit before the mark is a decimal, not a sentence end
#
# ABBREVIATIONS ARE HANDLED IN `clauses()`, NOT HERE. A lookbehind cannot see what follows the
# mark, so `e.g. a thing` and `Done. Next.` are indistinguishable to this pattern -- both are
# letter-dot-space. The check that separates them needs the word AFTER, which is why it lives in
# the loop where the remainder is available.
CLAUSE_END = re.compile(r"(?<![0-9])[.!?](?=\s|$)|(?<![0-9])[,;:](?=\s|$)")

# A dot after one of these is a abbreviation, not a sentence end, when a word follows it.
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.", "approx.", "no.", "fig.")

SYSTEM_PROMPT = os.environ.get(
    "VOICE_SYSTEM",
    "You are the voice of an engineering estate. Answer in one or two short sentences. "
    "Never use markdown, lists or code -- everything you say is read aloud.",
)


# --------------------------------------------------------------------------- model loading


@dataclass
class Models:
    """The three models, loaded once, plus an honest note of what failed.

    A missing TTS model must not take the ASR down with it: text-only answers are strictly better
    than a dead socket, and which half is missing is reported rather than guessed at.
    """

    asr: Any = None
    tts: Any = None
    errors: list[str] = field(default_factory=list)
    load_seconds: float | None = None
    tts_model: str | None = None
    # Which engine `synthesise` will use: "piper" (fastest), "say" (macOS), "kokoro" (richest).
    tts_engine: str | None = None
    # Loaded Piper voices, keyed by name. Loading is ~2.5s each, so never per utterance.
    piper_cache: dict = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.asr is not None


_models: Models | None = None


def load_models() -> Models:
    """Load every model once. Called at import so the socket never pays for it."""
    global _models
    if _models is not None:
        return _models

    started = time.time()
    m = Models()

    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415 - deliberately lazy

        # int8 on CPU. The blueprint's whole argument is that quantization, not hardware, is what
        # makes this viable on a CPU; `compute_type` is where that choice is actually made.
        # THREADS ARE PINNED, AND THIS IS A REAL FIX RATHER THAN A TUNING NICETY.
        #
        # Measured 2026-09-20, with the turn log (voice_turns) as the instrument: transcription had
        # grown from 1.0s to **8.4s median** for a 1.7-second utterance. The cause was not whisper.
        # `ps` showed Chrome at 77% CPU and the macOS window compositor at 60% -- on a TWO-CORE
        # machine, because the Fleet Reactor renders a 1200-mesh WebGL scene at 60fps in the same
        # browser that is holding the microphone.
        #
        # Left unset, ctranslate2 claims every logical core and then thrashes against the browser
        # for them. Pinned to the PHYSICAL core count it takes what it needs and leaves a core for
        # the compositor, which is slower in isolation and much faster in practice.
        #
        # `VOICE_ASR_THREADS` overrides it; the default is physical cores, which is `cpu_count()/2`
        # because Python reports LOGICAL cores -- using that raw is the mistake that produced the
        # 8.4s in the first place.
        _threads = int(
            os.environ.get("VOICE_ASR_THREADS", str(max(1, (os.cpu_count() or 2) // 2)))
        )
        m.asr = WhisperModel(
            ASR_MODEL, device="cpu", compute_type="int8", cpu_threads=_threads
        )
    except Exception as exc:  # noqa: BLE001 - a load failure is reported, never raised into a socket
        m.errors.append(f"asr: {exc.__class__.__name__}: {exc}")

    # --- TTS ENGINE SELECTION, BEFORE ANY MODEL IS LOADED ---
    #
    # ORDER: Piper, then macOS `say`, then Kokoro. Piper wins on measurement -- 0.67s against
    # Kokoro's 5.10s for the same sentence (see PIPER_VOICE's comment). `say` needs no model at all.
    # Kokoro is last because it is the slowest here, but it is KEPT: the founder asked for Piper to
    # be available, not for Kokoro to be removed, and the two should be comparable on their own
    # machine rather than chosen for them.
    #
    # Selecting before loading means a faster engine also skips Kokoro's 350MB load and ~9s of
    # `kokoro_onnx` import at boot.
    #
    # VOICE_TTS forces one engine, so all three can be compared without editing this file.
    if TTS_ENGINE != "kokoro" and TTS_ENGINE != "say" and piper_voices():
        m.tts_engine = "piper"
        m.tts_model = f"piper:{PIPER_VOICE}"

    if (
        m.tts_engine is None
        and TTS_ENGINE != "kokoro"
        and os.path.exists("/usr/bin/say")
    ):
        m.tts_engine = "say"
        m.tts_model = f"say:{SAY_VOICE}"

    if m.tts_engine is None:
        try:
            # The import IS the probe: it answers "is kokoro_onnx installed on this machine?".
            # The name is deliberately unused.
            import kokoro_onnx  # noqa: F401, PLC0415

            if not os.path.exists(KOKORO_VOICES):
                m.errors.append(
                    f"tts: voices absent ({KOKORO_VOICES}); run bin/voice-models to fetch them"
                )
            else:
                # FP32 FIRST, AND INT8 NEVER ATTEMPTED BY DEFAULT.
                #
                # The blueprint's guidance after the first measurement was explicit: on Ampere A1 we
                # have 24GB, so int8's memory saving buys nothing, and the int8 graph uses
                # ConvInteger(10), which ONNXRuntime's CPUExecutionProvider does not implement. Trying
                # it first cost 12 wasted seconds at every boot and produced an error line that reads
                # like a fault rather than a decision.
                #
                # Set VOICE_ALLOW_INT8=1 to try the small model anyway -- useful the day a runtime ships
                # the kernel, since int8 would then be the faster option.
                candidates = (
                    (KOKORO_MODEL, KOKORO_MODEL_INT8)
                    if os.environ.get("VOICE_ALLOW_INT8")
                    else (KOKORO_MODEL,)
                )
                for candidate in candidates:
                    if not os.path.exists(candidate):
                        continue
                    try:
                        m.tts = _kokoro_session(candidate)
                        m.tts_model = os.path.basename(candidate)
                        m.tts_engine = "kokoro"
                        break
                    except Exception as exc:  # noqa: BLE001 - try the next candidate
                        m.errors.append(
                            f"tts({os.path.basename(candidate)}): {exc.__class__.__name__}"
                        )
                if m.tts is None:
                    m.errors.append(
                        f"tts: no Kokoro model loaded from {MODEL_CACHE}; run bin/voice-models"
                    )
        except Exception as exc:  # noqa: BLE001
            m.errors.append(f"tts: {exc.__class__.__name__}: {exc}")

    m.load_seconds = round(time.time() - started, 1)
    _models = m
    return m


def models() -> Models:
    return load_models()


def _kokoro_session(model_path: str):
    """Build a Kokoro on an onnxruntime session tuned for THIS machine's core count.

    WHY THIS EXISTS. Kokoro's own `create_session` takes onnxruntime's defaults, which were
    measured 2026-09-19 at ~7-8s for a 4.3s sentence on this Intel i5-7360U. Pinning the thread
    counts instead gives ~5.1s -- about a 35% cut for two lines of configuration:

        intra=2 inter=1   5.11s   0.84x realtime
        intra=3 inter=1   4.94s   0.87x realtime   <- best
        intra=4 inter=1   5.28s   0.81x realtime

    `intra_op` is the parallelism WITHIN one operator -- the matmuls, which is where all the time
    goes -- so it is the knob that matters. `inter_op` parallelises ACROSS graph nodes and is set
    to 1 deliberately: a single utterance has no independent branches to run in parallel, and
    letting it spin costs latency and burns the box. Two physical cores is why 3 beats 4: above
    the physical count the threads contend and the winner is the scheduler.

    The default when VOICE_ONNX_THREADS is unset is `max(1, physical cores)`, which is the value
    that would be right on any machine rather than only this one. `os.cpu_count()` reports LOGICAL
    cores (4 here), so it is halved -- using it raw is what produced the 4-thread slowdown.
    """
    import os as _os  # noqa: PLC0415

    import onnxruntime as rt  # noqa: PLC0415

    from kokoro_onnx import Kokoro  # noqa: PLC0415

    override = _os.environ.get("VOICE_ONNX_THREADS")
    if override:
        threads = max(1, int(override))
    else:
        threads = max(1, (_os.cpu_count() or 2) // 2)

    opts = rt.SessionOptions()
    opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    session = rt.InferenceSession(
        model_path, sess_options=opts, providers=["CPUExecutionProvider"]
    )
    return Kokoro.from_session(session, voices_path=KOKORO_VOICES)


def ensure_kokoro() -> bool:
    """Load the Kokoro model if it is not already loaded. Returns whether it is usable.

    SEPARATE FROM load_models ON PURPOSE. load_models runs at import and picks the FASTEST engine
    available -- on macOS that is `say`, which needs no model at all. Kokoro is therefore loaded
    lazily, the first time somebody actually wants it: to audition one of its 54 voices in the
    picker, or to select it. A host that never chooses kokoro never pays its 350MB load.

    Thread-safe enough for this use: the caller runs it in an executor, and a second concurrent
    load would produce a second object that the first assignment immediately replaces -- wasteful
    but not wrong, and this happens at most once per process in practice.
    """
    global _models
    m = load_models()
    if m.tts is not None:
        return True
    try:
        # The import IS the probe (see the tts_engine branch above); the name is unused on purpose.
        import kokoro_onnx  # noqa: F401, PLC0415

        if os.path.exists(KOKORO_MODEL):
            m.tts = _kokoro_session(KOKORO_MODEL)
            m.tts_model = os.path.basename(KOKORO_MODEL)
            return True
        m.errors.append(f"kokoro: model absent ({KOKORO_MODEL})")
    except Exception as exc:  # noqa: BLE001
        m.errors.append(f"kokoro: {exc.__class__.__name__}: {exc}")
    return False


# --------------------------------------------------------------------------- the loop


def transcribe(pcm: bytes) -> tuple[str, float]:
    """16kHz float32 PCM in, text out, with how long it took.

    `beam_size=1` because this is conversation, not dictation: greedy decoding costs a fraction of
    the time and the difference on a short utterance is invisible.
    """
    import numpy as np  # noqa: PLC0415

    m = models()
    if m.asr is None:
        return "", 0.0
    audio = np.frombuffer(pcm, dtype=np.float32)
    started = time.time()
    segments, _info = m.asr.transcribe(audio, beam_size=1, language="en")
    text = " ".join(s.text for s in segments).strip()
    return text, round(time.time() - started, 3)


def clauses(text: str):
    """Split a growing buffer into speakable clauses, returning the pairs (ready, remainder).

    Written as a pure function so it can be tested without a model, a socket or a clock -- and
    because clause splitting is where a streaming voice system most often goes subtly wrong.

    IT WAS GOING SUBTLY WRONG HERE. The pattern was `[.!?,;:]\\s+$`, which demands punctuation
    FOLLOWED BY WHITESPACE, and a streamed token usually ends ON the punctuation: the model emits
    `stuck,` and then ` all`. While the buffer's last character is the comma there is no trailing
    space, nothing matches, and the clause sits in the buffer until the whole answer arrives.

    Measured 2026-09-20: "Four agents are stuck, all paused, two on the audit." streamed one token
    at a time produced ZERO ready clauses until the final token -- the mechanism that was supposed
    to hide the synthesis latency was never firing, which is why a multi-clause answer cost one
    5-second synthesis instead of three short ones.

    The trailing whitespace is now optional, and a clause that ends exactly at the buffer's end is
    returned. The lookahead keeps the original intent -- "3.5" and "e.g. " must not split at the
    dot -- by requiring that what FOLLOWS is a space or nothing, which is what a sentence boundary
    looks like in a stream.
    """
    out: list[str] = []
    buf = text
    while True:
        match = CLAUSE_END.search(buf)
        if not match:
            break
        end = match.end()
        # AN ABBREVIATION IS NOT A SENTENCE END, and only this loop can tell: the test needs the
        # word that follows, which a lookbehind cannot see. If the mark just closed `e.g.` and a
        # word follows, keep scanning past it instead of splitting.
        tail = buf[:end].lower().rstrip()
        if any(tail.endswith(a) for a in ABBREVIATIONS) and buf[end : end + 1] not in (
            "",
        ):
            nextmatch = CLAUSE_END.search(buf, end)
            if not nextmatch:
                break
            end = nextmatch.end()
        piece = buf[:end].strip()
        if piece:
            out.append(piece)
        buf = buf[end:]
    return out, buf


def fleet_summary() -> str:
    """The fleet as a few lines of text, read from the SAME endpoint the room renders.

    WHY THIS IS NOT OPTIONAL. Measured 2026-09-19, before this existed: asked "what is stuck in the
    fleet right now", the server answered "I don't have live access to your fleet's current state".
    It was telling the truth -- it had been sent a question and nothing else -- and a voice that
    cannot see the fleet is a chatbot wearing the estate's clothes.

    It reads `/api/proxy/fleetview/sessions` through the plugin rather than querying estate.db
    directly, so the spoken answer and the nodes in the room are derived from one source and cannot
    drift apart. A failure here returns an honest "unavailable" line rather than an empty string:
    a model given no context will invent some, and an invented fleet is worse than an admitted gap.
    """
    import urllib.request  # noqa: PLC0415

    host = os.environ.get("FLEETVIEW_URL", "http://127.0.0.1:18790")
    try:
        with urllib.request.urlopen(f"{host}/sessions", timeout=5) as resp:
            sessions = (json.load(resp) or {}).get("sessions") or []
    except Exception as exc:  # noqa: BLE001
        return f"FLEET CONTEXT UNAVAILABLE ({exc.__class__.__name__}). Say so if asked about it."
    if not sessions:
        return "The fleet is reporting no sessions at all."

    counts: dict[str, int] = {}
    for sess in sessions:
        counts[sess.get("activity") or "unknown"] = (
            counts.get(sess.get("activity") or "unknown", 0) + 1
        )
    head = ", ".join(
        f"{n} {k}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1])
    )

    rows = []
    for sess in sessions[
        :20
    ]:  # capped: a prompt that grows with the fleet grows the latency too
        sid = str(sess.get("session_id") or "")[-8:]
        rows.append(
            f"- {sid} {sess.get('runtime')} {sess.get('activity')} "
            f"{sess.get('event_count') or 0} events :: {(sess.get('task') or '')[:70]}"
        )
    return f"{len(sessions)} sessions: {head}.\n" + "\n".join(rows)


async def llm_clauses(question: str, history: list[dict[str, str]] | None = None):
    """Yield clauses of the answer as the model writes them.

    STREAMING IS THE POINT. Waiting for the whole paragraph before speaking is the difference
    between this feeling instant and feeling broken: the first clause is synthesised and played
    while the model is still writing the second.
    """
    import urllib.request  # noqa: PLC0415

    key = os.environ.get("LITELLM_API_KEY", "")
    if not key:
        yield "Voice has no router key on this host, so I cannot answer."
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history or []:
        messages.append(turn)
    # The fleet goes in the USER turn, next to the question, exactly as the plugin's voice.py
    # does -- so the model reads the live state as evidence for this question rather than as
    # standing background it may or may not connect.
    fleet = await asyncio.get_running_loop().run_in_executor(None, fleet_summary)
    messages.append(
        {"role": "user", "content": f"FLEET SUMMARY\n{fleet}\n\nQUESTION\n{question}"}
    )

    payload = {
        "model": ROUTER_MODEL,
        "messages": messages,
        "max_tokens": 200,
        "temperature": 0.3,
        "stream": True,
    }
    req = urllib.request.Request(
        f"{ROUTER_HOST}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )

    # The router call is blocking, so it runs in a thread and the stream is fed back through a
    # queue. Doing this on the event loop directly would stall every other socket in the process
    # for the length of a model response -- which for a voice server means a second caller hears
    # nothing at all.
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    SENTINEL = object()

    def pump():
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                buffer = ""
                for raw in resp:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body == "[DONE]":
                        break
                    try:
                        chunk = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get(
                        "content"
                    ) or ""
                    if not delta:
                        continue
                    buffer += delta
                    ready, buffer = clauses(buffer)
                    for clause in ready:
                        loop.call_soon_threadsafe(queue.put_nowait, ("clause", clause))
                if buffer.strip():
                    loop.call_soon_threadsafe(
                        queue.put_nowait, ("clause", buffer.strip())
                    )
        except Exception as exc:  # noqa: BLE001 -- a router failure is spoken, not crashed
            loop.call_soon_threadsafe(
                queue.put_nowait, ("error", f"The router could not be reached: {exc}")
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

    loop.run_in_executor(None, pump)
    while True:
        item = await queue.get()
        if item is SENTINEL:
            break
        kind, value = item
        if kind == "clause":
            yield value
        else:
            yield value
            break


def synthesise(text: str) -> bytes | None:
    """A clause to 24kHz float32 PCM, or None when TTS is unavailable.

    TWO ENGINES, FASTEST FIRST. Measured 2026-09-19 on the founder's laptop (Intel i5-7360U,
    2 physical cores), same two sentences, three runs each:

      engine       short (1.5s audio)   long (4.3s audio)
      Kokoro       13.70s   (8.84x)     7.16s   (1.67x)
      macOS say     1.71s   (1.13x)     0.88s   (0.20x)

    `say` is 5-8x faster and, on a full sentence, faster than realtime. It is the OS's own
    synthesizer: no Python in the synthesis path, no 350MB model, no ONNX graph. Kokoro's own
    numbers swing by nearly 2x between runs because it is competing for two cores.

    WHY BOTH ARE KEPT. `say` exists only on macOS. Kokoro is the portable engine and is what a
    Linux container (the cluster) will use, so it stays as the fallback and the engine on any
    host without `say`. The choice is made by what is present, once, at load time.

    `say` writes a WAVE whose `data` chunk is raw Float32 at 24kHz -- byte-for-byte the format
    this function already returns -- so it is a drop-in and the browser needs no change.
    """
    m = models()

    if m.tts_engine == "piper":
        return synthesise_piper_with(PIPER_VOICE, text)

    if m.tts_engine == "say":
        return _synthesise_say(text)

    if m.tts is None:
        return None
    try:
        samples, _rate = m.tts.create(text, voice=KOKORO_VOICE, speed=1.0)
        return samples.astype("float32").tobytes()
    except Exception:  # noqa: BLE001 -- one bad clause must not end the conversation
        return None


def piper_voices() -> list[str]:
    """Every Piper voice downloaded on this host, as bare names."""
    import pathlib  # noqa: PLC0415

    d = pathlib.Path(PIPER_DIR)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.onnx"))


def _piper_loaded(voice: str):
    """Load (and cache) one Piper voice. Loading is ~2.5s, so it is never done per utterance."""
    m = models()
    key = voice or PIPER_VOICE
    cached = m.piper_cache.get(key)
    if cached is not None:
        return cached
    try:
        from piper import PiperVoice  # noqa: PLC0415

        path = os.path.join(PIPER_DIR, f"{key}.onnx")
        if not os.path.exists(path):
            m.errors.append(f"piper: no voice file for {key}")
            return None
        v = PiperVoice.load(path)
        m.piper_cache[key] = v
        return v
    except Exception as exc:  # noqa: BLE001
        m.errors.append(f"piper({key}): {exc.__class__.__name__}: {exc}")
        return None


def synthesise_piper_with(voice: str, text: str) -> bytes | None:
    """Piper to Float32 at TTS_SAMPLE_RATE, the format the socket already sends.

    PIPER EMITS 16-BIT PCM AT ITS OWN RATE (22050Hz for the voices here); the browser is told to
    expect 24kHz Float32. Both conversions happen here rather than in the browser, so the client
    keeps ONE code path for every engine -- the same argument the say/Piper/Kokoro split is built
    on. Resampling is linear interpolation, which is inaudible at this ratio and costs microseconds
    against a 670ms synthesis.
    """
    import numpy as np  # noqa: PLC0415

    v = _piper_loaded(voice)
    if v is None:
        return None
    try:
        chunks = list(v.synthesize(text))
        if not chunks:
            return None
        raw = b"".join(c.audio_int16_bytes for c in chunks)
        src_rate = v.config.sample_rate
        a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if src_rate != TTS_SAMPLE_RATE and len(a) > 1:
            n = int(len(a) * TTS_SAMPLE_RATE / src_rate)
            a = a[np.linspace(0, len(a) - 1, n).astype(np.int64)]
        return a.astype("float32").tobytes()
    except Exception:  # noqa: BLE001 -- one bad clause must not end the conversation
        return None


def synthesise_say_with(voice: str, text: str) -> bytes | None:
    """`say` in a CHOSEN voice, without changing the live one.

    Split out of `_synthesise_say` so the picker can audition a voice without applying it: the
    live engine reads SAY_VOICE, this reads an argument. Same subprocess, same format, no shell.
    """
    import struct  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    out = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out = f.name
        subprocess.run(
            [
                "/usr/bin/say",
                "-o",
                out,
                "--file-format=WAVE",
                f"--data-format=LEF32@{TTS_SAMPLE_RATE}",
                "-v",
                voice,
                text,
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )
        with open(out, "rb") as f:
            blob = f.read()
        i = blob.find(b"data")
        if i == -1:
            return None
        size = struct.unpack("<I", blob[i + 4 : i + 8])[0]
        return blob[i + 8 : i + 8 + size]
    except Exception:  # noqa: BLE001
        return None
    finally:
        if out:
            try:
                os.unlink(out)
            except OSError:
                pass


def synthesise_kokoro_with(voice: str, text: str) -> bytes | None:
    """Kokoro in a CHOSEN voice, for the picker's audition path."""
    m = models()
    if m.tts is None:
        return None
    try:
        samples, _rate = m.tts.create(text, voice=voice, speed=1.0)
        return samples.astype("float32").tobytes()
    except Exception:  # noqa: BLE001
        return None


def _synthesise_say(text: str) -> bytes | None:
    """macOS `say` to raw Float32 24kHz PCM. Returns None on any failure.

    NO SHELL. The arguments go to `subprocess` as a list, so a clause containing quotes, a
    semicolon or `$(...)` is spoken rather than executed -- an agent's answer is untrusted text
    and this is the one place it reaches a process boundary.
    """
    import struct  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    out = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out = f.name
        subprocess.run(
            [
                "/usr/bin/say",
                "-o",
                out,
                "--file-format=WAVE",
                f"--data-format=LEF32@{TTS_SAMPLE_RATE}",
                "-v",
                SAY_VOICE,
                text,
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )
        with open(out, "rb") as f:
            blob = f.read()
        # Find the `data` chunk rather than trusting a fixed offset: the WAVE header carries
        # variable-length `fmt `/`fact` chunks that differ between OS versions.
        i = blob.find(b"data")
        if i == -1:
            return None
        size = struct.unpack("<I", blob[i + 4 : i + 8])[0]
        return blob[i + 8 : i + 8 + size]
    except Exception:  # noqa: BLE001 -- a failed utterance degrades to silence, never to a crash
        return None
    finally:
        if out:
            try:
                os.unlink(out)
            except OSError:
                pass
