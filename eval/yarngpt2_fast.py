"""Throwaway, run 3: where is the time in a YarnGPT2 voice note, and which change cuts it?

Run 2 (2026-10-13) fixed the model path: llama.cpp q8_0 on 2 cores, 24-31s for a 216-character
note, ~3s of compute per second of speech. Decoding is memory-bandwidth bound (4 and 8 cores were no
faster), so more cores do not help; more *containers* and fewer *bytes per token* should. This run
measures, on 2-core Modal CPUs, with the control in the same run:

  A  llama-q8_0                      the control, as production ships it
  B  llama-q6_k, llama-q5_k_m        fewer bytes per token; q4_k_m lost words, so a Whisper
                                     transcript scores every quant against the script (WER)
  C  llama-q8_0 + prompt lookup      speculative decoding with no draft model; lossless, so its
                                     audio codes must hash equal to A's or it is not a win
  D  fan-out                         one container per sentence, joined; wall-clock for the whole
                                     note and time to the FIRST audio, cold and warm, vs one container

Lives only on branch eval/yarngpt2; `modal run` is ephemeral, so nothing is left deployed.
"""

import hashlib
import io
import json
import pathlib
import time

import modal

YARNGPT_SHA = "8bb0eb27d307f4b5903149e24ecc1bd3caa4af2d"  # saheedniyi02/yarngpt, 2025-03-14
LLAMA_CPP_SHA = "c0159f9c1f874da15e94f371d136f5920b4b5335"  # the one llama-cpp-python 0.3.19 vendors
CFG = "wavtokenizer_mediumdata_frame75_3s_nq1_code4096_dim512_kmeans200_attn.yaml"
VOICES = ["idera", "chinenye"]
TEXTS = {
    "short": "Good morning Mummy. Your medicine is due at nine o'clock.",
    "typical": (
        "Good morning Mummy. Just a reminder that your medicine is due at nine o'clock. "
        "I have also booked the taxi for Thursday at ten, so you do not need to call anyone. "
        "Have a lovely day."
    ),
}
QUANTS = ["f16", "q8_0", "q4_k_m"]

image = (
    # Unchanged from run 1, so Modal reuses these layers.
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "ffmpeg", "libportaudio2")
    .pip_install("torch==2.5.1", "torchaudio==2.5.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install(
        "transformers==4.47.1", "outetts==0.2.3", "uroman", "inflect", "gdown", "soundfile",
        "huggingface_hub",
    )
    .run_commands(
        f"git clone -q https://github.com/saheedniyi02/yarngpt.git /opt/yarngpt"
        f" && git -C /opt/yarngpt checkout -q {YARNGPT_SHA}",
        f"mkdir -p /w && curl -fsSL -o /w/{CFG} "
        f"https://huggingface.co/novateur/WavTokenizer-medium-speech-75token/resolve/main/{CFG}",
        "(gdown -q 1-ASeEkrn4HY49yZWHTASgfGFNXdVnLTt -O /w/wavtokenizer.ckpt && echo gdrive > /w/src)"
        " || (curl -fsSL -o /w/wavtokenizer.ckpt https://huggingface.co/novateur/"
        "WavTokenizer-large-speech-75token/resolve/main/wavtokenizer_large_speech_320_v2.ckpt"
        " && echo hf-large-v2 > /w/src)",
        "sha256sum /w/wavtokenizer.ckpt > /w/ckpt.sha256 && du -sh /w/wavtokenizer.ckpt",
        "python -c \"from huggingface_hub import snapshot_download as d; d('saheedniyi/YarnGPT2')\"",
    )
    # New in run 2: llama.cpp and the model converted to GGUF. Built from source: the index's
    # prebuilt "cpu" wheel links musl and won't load on Debian. Not -march=native, since the build
    # machine needn't be the one that runs it; AVX2/FMA is safe on Modal's x86 fleet.
    .apt_install("libgomp1", "build-essential", "cmake")
    .env({"CMAKE_ARGS": "-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON"})
    .pip_install("llama-cpp-python==0.3.19")
    .run_commands(
        f"git init -q /opt/llama.cpp && git -C /opt/llama.cpp fetch -q --depth 1"
        f" https://github.com/ggml-org/llama.cpp.git {LLAMA_CPP_SHA}"
        f" && git -C /opt/llama.cpp checkout -q FETCH_HEAD",
        "pip install -q /opt/llama.cpp/gguf-py sentencepiece protobuf",
        "M=$(python -c \"from huggingface_hub import snapshot_download as d; print(d('saheedniyi/YarnGPT2'))\")"
        " && python /opt/llama.cpp/convert_hf_to_gguf.py $M --outtype f16 --outfile /w/yarn-f16.gguf"
        " && python /opt/llama.cpp/convert_hf_to_gguf.py $M --outtype q8_0 --outfile /w/yarn-q8_0.gguf",
        # q4_k_m through the library's own quantiser; 960-wide rows fall back to q5_0/q8_0 blocks.
        "python -c \"import ctypes, llama_cpp as l; p = l.llama_model_quantize_default_params();"
        " p.ftype = l.LLAMA_FTYPE_MOSTLY_Q4_K_M;"
        " assert l.llama_model_quantize(b'/w/yarn-f16.gguf', b'/w/yarn-q4_k_m.gguf', ctypes.byref(p)) == 0\"",
        "ls -la /w",
    )
)

# New in run 3, appended so the layers above stay cached: two more quants, and a small Whisper to
# score what each quant actually says.
image = (
    image.pip_install("faster-whisper==1.1.0")
    .run_commands(
        "python -c \"import ctypes, llama_cpp as l\n"
        "for name, ft in (('q6_k', l.LLAMA_FTYPE_MOSTLY_Q6_K), ('q5_k_m', l.LLAMA_FTYPE_MOSTLY_Q5_K_M)):\n"
        "    p = l.llama_model_quantize_default_params(); p.ftype = ft\n"
        "    assert l.llama_model_quantize(b'/w/yarn-f16.gguf', f'/w/yarn-{name}.gguf'.encode(), ctypes.byref(p)) == 0\"",
        "python -c \"from huggingface_hub import snapshot_download as d; d('Systran/faster-whisper-tiny.en')\"",
        "ls -la /w",
    )
)

app = modal.App("yarngpt2-eval-3")
SENTENCE = __import__("re").compile(r"(?<=[.!?])\s+")
SILENCE_S = 0.12  # a breath between joined sentences


def _wer(want: str, got: str) -> float:
    import re

    norm = lambda s: re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()  # noqa: E731
    a, b = norm(want), norm(got)
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return round(d[len(b)] / max(len(a), 1), 3)


def _say(wav, sr: int = 24000) -> str:
    import numpy as np
    import torchaudio.functional as F
    import torch
    from faster_whisper import WhisperModel

    global _WHISPER
    try:
        _WHISPER
    except NameError:
        _WHISPER = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=1)
    x = F.resample(torch.as_tensor(np.asarray(wav, dtype="float32")).reshape(1, -1), sr, 16000)[0].numpy()
    segs, _ = _WHISPER.transcribe(x, language="en", beam_size=1, vad_filter=False)
    return " ".join(s.text.strip() for s in segs)


class _Engine:
    """The tokenizer/codec once, a GGUF per option on demand. One per container, as production."""

    def __init__(self, ncpu: int) -> None:
        import sys

        import torch

        torch.set_num_threads(ncpu)
        sys.path.insert(0, "/opt")
        from yarngpt.audiotokenizer import AudioTokenizerV2

        self.ncpu = ncpu
        self.tok = AudioTokenizerV2("saheedniyi/YarnGPT2", "/w/wavtokenizer.ckpt", f"/w/{CFG}")
        self.stop = {0, self.tok.tokenizer.convert_tokens_to_ids("<|audio_end|>")}
        self.llm = None
        self.loaded = None

    def load(self, quant: str, lookup: bool = False) -> float:
        from llama_cpp import Llama
        from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

        t = time.perf_counter()
        self.llm = Llama(
            model_path=f"/w/yarn-{quant}.gguf", n_ctx=4096, n_threads=self.ncpu,
            n_threads_batch=self.ncpu, n_batch=512, last_n_tokens_size=4096, verbose=False,
            draft_model=LlamaPromptLookupDecoding(max_ngram_size=3, num_pred_tokens=10) if lookup else None,
        )
        self.loaded = (quant, lookup)
        return time.perf_counter() - t

    def speak(self, text: str, voice: str) -> dict:
        import torch

        ids = self.tok.tokenize_prompt(self.tok.create_prompt(text, lang="english", speaker_name=voice))[0].tolist()
        gen: list[int] = []
        first = None
        t0 = time.perf_counter()
        for tid in self.llm.generate(ids, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, repeat_penalty=1.1, reset=True):
            if first is None:
                first = time.perf_counter() - t0
            if tid in self.stop or len(ids) + len(gen) >= 4000:
                break
            gen.append(tid)
        gen_s = time.perf_counter() - t0
        codes = self.tok.extract_integers(self.tok.tokenizer.decode(gen))
        if not codes:
            return {"error": "no audio codes generated", "gen_tokens": len(gen)}
        t = time.perf_counter()
        with torch.inference_mode():
            wav = self.tok.get_audio(codes).squeeze().numpy()
        dec_s = time.perf_counter() - t
        return {
            "wav": wav, "audio_s": round(len(wav) / 24000, 2), "prompt_tokens": len(ids),
            "gen_tokens": len(gen), "first_token_s": round(first, 2), "generate_s": round(gen_s, 2),
            "decode_audio_s": round(dec_s, 2), "note_s": round(gen_s + dec_s, 2),
            "tok_per_s": round(len(gen) / max(gen_s, 1e-6), 1),
            "codes_sha": hashlib.sha1(json.dumps(codes).encode()).hexdigest()[:10],
        }


def _wav_bytes(wav) -> bytes:
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, wav, 24000, format="WAV")
    return buf.getvalue()


@app.function(image=image, cpu=2.0, memory=4096, timeout=3000)
def variants() -> dict:
    """A, B, C on one 2-core container: same machine, same minute, so the deltas are real."""
    eng = _Engine(2)
    rows, audio = [], {}
    for option, quant, lookup in (
        ("A llama-q8_0", "q8_0", False),
        ("B llama-q6_k", "q6_k", False),
        ("B llama-q5_k_m", "q5_k_m", False),
        ("C llama-q8_0+lookup", "q8_0", True),
        ("A llama-q8_0 (again)", "q8_0", False),  # the control twice: that gap is the noise floor
    ):
        load_s = eng.load(quant, lookup)
        for name, text in TEXTS.items():
            r = eng.speak(text, "idera")
            if "wav" in r:
                heard = _say(r["wav"])
                audio[f"{option.split()[0]}-{quant}{'-lookup' if lookup else ''}-{name}.wav"] = _wav_bytes(r.pop("wav"))
                r.update(heard=heard, wer=_wer(text, heard))
            r.update(option=option, text=name, load_s=round(load_s, 1))
            rows.append(r)
            print("BENCH", json.dumps({k: v for k, v in r.items() if k != "heard"}), flush=True)
    return {"rows": rows, "audio": audio}


@app.cls(image=image, cpu=2.0, memory=4096, timeout=600, scaledown_window=120)
class Chunk:
    """Production's shape: model loaded once on enter, one input per container."""

    @modal.enter()
    def up(self) -> None:
        t = time.perf_counter()
        self.eng = _Engine(2)
        self.eng.load("q8_0")
        self.up_s = round(time.perf_counter() - t, 1)

    @modal.method()
    def say(self, text: str, voice: str) -> dict:
        r = self.eng.speak(text, voice)
        r["container_up_s"] = self.up_s
        return r


def _join(parts: list) -> "object":
    import numpy as np

    gap = np.zeros(int(24000 * SILENCE_S), dtype="float32")
    out = []
    for i, p in enumerate(parts):
        out.append(np.asarray(p, dtype="float32"))
        if i < len(parts) - 1:
            out.append(gap)
    return np.concatenate(out)


def _fanout(text: str, label: str, outdir: pathlib.Path) -> dict:
    """Wall-clock from the caller's side, as the endpoint sees it: every sentence is its own call."""
    sentences = [s for s in SENTENCE.split(text.strip()) if s]
    t0 = time.perf_counter()
    calls = [Chunk().say.spawn(s, "idera") for s in sentences]
    done_at, results = [], []
    for c in calls:  # in order: the first sentence is what the listener hears first
        results.append(c.get())
        done_at.append(round(time.perf_counter() - t0, 1))
    wall = round(time.perf_counter() - t0, 1)
    bad = [r for r in results if "wav" not in r]
    row = {"label": label, "sentences": len(sentences), "first_audio_s": done_at[0], "all_done_s": wall,
           "per_sentence_done_s": done_at, "container_up_s": [r.get("container_up_s") for r in results]}
    if bad:
        row["error"] = f"{len(bad)} sentence(s) made no audio"
        return row
    joined = _join([r["wav"] for r in results])
    row["audio_s"] = round(len(joined) / 24000, 1)
    (outdir / f"{label}.wav").write_bytes(_wav_bytes(joined))
    return row


@app.local_entrypoint()
def main():
    outdir = pathlib.Path("yarngpt2-samples")
    outdir.mkdir(exist_ok=True)
    var = variants.spawn()  # its own container; the fan-out below never shares a CPU with it
    text = TEXTS["typical"]
    fan = []
    # Whole note in ONE container (production today) vs one container per sentence. Each is run
    # cold (containers booting, model loading) then warm (the same containers, still up).
    for label, body in (("one-container-cold", text), ("fanout-cold", text), ("one-container-warm", text),
                        ("fanout-warm", text)):
        if label.startswith("one"):
            sentences_row = None
            t0 = time.perf_counter()
            r = Chunk().say.remote(body, "idera")
            wall = round(time.perf_counter() - t0, 1)
            sentences_row = {"label": label, "sentences": 1, "first_audio_s": wall, "all_done_s": wall,
                             "container_up_s": [r.get("container_up_s")], "audio_s": r.get("audio_s"),
                             "gen_tokens": r.get("gen_tokens")}
            if "wav" in r:
                (outdir / f"{label}.wav").write_bytes(_wav_bytes(r["wav"]))
            fan.append(sentences_row)
        else:
            fan.append(_fanout(body, label, outdir))
        print("FANOUT", json.dumps(fan[-1]), flush=True)
    rep = {"fanout": fan, "errors": {}}
    try:
        v = var.get()
        rep["variants"] = v["rows"]
        for name, wav in v["audio"].items():
            (outdir / name).write_bytes(wav)
    except Exception as exc:
        rep["errors"]["variants"] = f"{type(exc).__name__}: {exc}"[:800]
        print("FAILED variants:", rep["errors"]["variants"], flush=True)
    (outdir / "report.json").write_text(json.dumps(rep, indent=2))
    print("SUMMARY option                 text     note_s  tok/s  wer    codes_sha   load_s")
    for r in rep.get("variants", []):
        if "error" in r:
            print(f"SUMMARY {r['option']:<22} {r['text']:<8} ERROR {r['error']}")
            continue
        print(f"SUMMARY {r['option']:<22} {r['text']:<8} {r['note_s']:<7} {r['tok_per_s']:<6} {r['wer']:<6} {r['codes_sha']}  {r['load_s']}")
    print("SUMMARY fan-out label               first_audio_s  all_done_s")
    for r in fan:
        print(f"SUMMARY {r['label']:<22} {r['first_audio_s']:<14} {r['all_done_s']}  {r.get('error', '')}")
