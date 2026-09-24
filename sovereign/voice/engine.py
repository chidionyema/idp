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

# The router is the estate's own (LAW 34: one router key per identity, no vendor keys on the Mac).
# The spec's LLM leg is vLLM/Llama-3.3-70B streamed; the deployment note permits the estate router
# to stand in for it. The model string here should name a lane the spec's Llama is actually routed
# to, not a hardcoded default that is nobody's declared choice -- the drift the 2026-09-24 trace
# found (every completion hung on the default while /v1/models listed the real lanes).
ROUTER_HOST = os.environ.get("LITELLM_HOST", "https://llm.mumchimp.com")
ROUTER_MODEL = os.environ.get("VOICE_LLM_MODEL", "default")

# A clause ends at a breath. The regex demands punctuation FOLLOWED BY SPACE, so "3.5" and "e.g."
# do not split mid-number or mid-abbreviation -- a fault that would make the voice read decimals
# as two separate utterances.
CLAUSE_END = re.compile(r"[.!?,;:]\s+$")

# How long the answer leg waits on the router before it speaks a refusal. A person talking to a
# machine must not sit in silence for a minute; a dead lane is a 5s pause then "I could not reach
# the model", which is the difference between degraded-but-honest and broken-but-quiet.
ROUTER_TIMEOUT_S = float(os.environ.get("VOICE_ROUTER_TIMEOUT_S", "8"))

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

        # ASR model: `tiny.en` (fast, CPU/edge default) or `large-v3-turbo` (quality), chosen by
        # VOICE_ASR_MODEL -- both are wanted. The compute type follows the model: tiny.en stays
        # int8 (the CPU-viability argument), large-v3-turbo uses int8_float16 so it does not lose
        # the one operator int8 lacks on this runtime (ConvInteger) and still runs on CPU.
        asr_compute = "int8" if ASR_MODEL == "tiny.en" else "int8_float16"
        m.asr = WhisperModel(ASR_MODEL, device="cpu", compute_type=asr_compute)
    except Exception as exc:  # noqa: BLE001 - a load failure is reported, never raised into a socket
        m.errors.append(f"asr: {exc.__class__.__name__}: {exc}")

    try:
        from kokoro_onnx import Kokoro  # noqa: PLC0415

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
                    m.tts = Kokoro(candidate, KOKORO_VOICES)
                    m.tts_model = os.path.basename(candidate)
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
    """
    out: list[str] = []
    buf = text
    while True:
        match = CLAUSE_END.search(buf)
        if not match:
            break
        end = match.end()
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
            # A voice answer must FAIL FAST, not hang: a dead router lane is spoken as a refusal
            # in seconds, not sixty seconds of silence the person then talks over. Measured
            # 2026-09-24: the deepseek lane timed out (server-side 60s) while the browser client
            # dropped at 30s -- so the failure was never spoken and the turn ended in silence with
            # no error anywhere. The number here is the contract: a voice answer either starts in
            # ROUTER_TIMEOUT_S seconds or it says it could not.
            with urllib.request.urlopen(req, timeout=ROUTER_TIMEOUT_S) as resp:
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

    Returning bytes rather than raising keeps the socket alive on a box without the voice model:
    the caller hears nothing but still receives the transcript, which is a usable degradation.
    """
    m = models()
    if m.tts is None:
        return None
    try:
        samples, _rate = m.tts.create(text, voice=KOKORO_VOICE, speed=1.0)
        return samples.astype("float32").tobytes()
    except Exception:  # noqa: BLE001 -- one bad clause must not end the conversation
        return None
