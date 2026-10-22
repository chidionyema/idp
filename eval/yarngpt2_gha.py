"""Throwaway, run 3c: prompt reuse and thread count for q8_0, on a GitHub runner (Modal is at its spend limit).

Run 3b settled the quant (q8_0) and rejected prompt lookup. This run asks the next two questions:
how much of the speaker prompt is a reusable prefix (llama-cpp-python reuses the longest matching
prefix between generate() calls), and what more threads buy, since a Modal core is a physical core
and production's cpu=2.0 may be four threads. Per sentence, so the fan-out bound falls out directly.
"""

import hashlib
import io
import json
import pathlib
import re
import time

CFG = "wavtokenizer_mediumdata_frame75_3s_nq1_code4096_dim512_kmeans200_attn.yaml"
TEXTS = {
    "short": "Good morning Mummy. Your medicine is due at nine o'clock.",
    "typical": (
        "Good morning Mummy. Just a reminder that your medicine is due at nine o'clock. "
        "I have also booked the taxi for Thursday at ten, so you do not need to call anyone. "
        "Have a lovely day."
    ),
}
SENTENCE = __import__("re").compile(r"(?<=[.!?])\s+")
SILENCE_S = 0.12  # a breath between joined sentences


def _wer(want: str, got: str) -> float:

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
        _WHISPER = WhisperModel(
            "tiny.en", device="cpu", compute_type="int8", cpu_threads=1
        )
    x = F.resample(
        torch.as_tensor(np.asarray(wav, dtype="float32")).reshape(1, -1), sr, 16000
    )[0].numpy()
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
        self.tok = AudioTokenizerV2(
            "saheedniyi/YarnGPT2", "/w/wavtokenizer.ckpt", f"/w/{CFG}"
        )
        self.stop = {0, self.tok.tokenizer.convert_tokens_to_ids("<|audio_end|>")}
        self.llm = None
        self.loaded = None

    def load(self, quant: str, lookup: bool = False) -> float:
        from llama_cpp import Llama
        from llama_cpp.llama_speculative import LlamaPromptLookupDecoding

        t = time.perf_counter()
        self.llm = Llama(
            model_path=f"/w/yarn-{quant}.gguf",
            n_ctx=4096,
            n_threads=self.ncpu,
            n_threads_batch=self.ncpu,
            n_batch=512,
            last_n_tokens_size=4096,
            logits_all=lookup,
            verbose=False,
            draft_model=LlamaPromptLookupDecoding(max_ngram_size=3, num_pred_tokens=10)
            if lookup
            else None,
        )
        self.loaded = (quant, lookup)
        return time.perf_counter() - t

    def ids(self, text: str, voice: str) -> list[int]:
        return self.tok.tokenize_prompt(
            self.tok.create_prompt(text, lang="english", speaker_name=voice)
        )[0].tolist()

    def speak(self, text: str, voice: str) -> dict:
        import torch

        ids = self.ids(text, voice)
        gen: list[int] = []
        first = None
        t0 = time.perf_counter()
        for tid in self.llm.generate(
            ids, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, repeat_penalty=1.1, reset=True
        ):
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
            "wav": wav,
            "audio_s": round(len(wav) / 24000, 2),
            "prompt_tokens": len(ids),
            "gen_tokens": len(gen),
            "first_token_s": round(first, 2),
            "generate_s": round(gen_s, 2),
            "decode_audio_s": round(dec_s, 2),
            "note_s": round(gen_s + dec_s, 2),
            "tok_per_s": round(len(gen) / max(gen_s, 1e-6), 1),
            "codes_sha": hashlib.sha1(json.dumps(codes).encode()).hexdigest()[:10],
        }


def _wav_bytes(wav) -> bytes:
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, wav, 24000, format="WAV")
    return buf.getvalue()


def main() -> None:
    import os

    import torch

    ncpu = len(os.sched_getaffinity(0))
    print("ENV", json.dumps({"cpu_count": os.cpu_count(), "usable": ncpu}), flush=True)
    sents = SENTENCE.split(TEXTS["typical"])
    eng = _Engine(2)
    ids = [eng.ids(s, "idera") for s in sents]
    shared = min(len(os.path.commonprefix([ids[0], x])) for x in ids[1:])
    print(
        "PREFIX",
        json.dumps({"prompt_tokens": [len(x) for x in ids], "shared_prefix": shared}),
        flush=True,
    )
    rows = []
    for threads in sorted({2, 3, 4, ncpu}):
        if threads > ncpu:
            continue
        torch.set_num_threads(threads)
        eng.ncpu = threads
        eng.load("q8_0")
        for mode in (
            "cold",
            "warm",
        ):  # cold: KV cache emptied first; warm: follows the previous sentence
            for s in sents:
                if mode == "cold":
                    eng.llm.reset()
                r = eng.speak(s, "idera")
                r.pop("wav", None)
                r.update(threads=threads, mode=mode, sentence=s[:24])
                rows.append(r)
                print("RUN", json.dumps(r), flush=True)
    base = {
        r["sentence"]: r.get("codes_sha")
        for r in rows
        if r["threads"] == 2 and r["mode"] == "cold"
    }
    print(
        "SUMMARY threads mode  one_container_s  fanout_bound_s  first_audio_s  mean_first_token_s  same_codes_as_2cold"
    )
    for threads in sorted({r["threads"] for r in rows}):
        for mode in ("cold", "warm"):
            g = [r for r in rows if r["threads"] == threads and r["mode"] == mode]
            ns = [r.get("note_s") or 0 for r in g]
            same = all(base.get(r["sentence"]) == r.get("codes_sha") for r in g)
            ft = sum(r.get("first_token_s") or 0 for r in g) / len(g)
            print(
                f"SUMMARY {threads:<7} {mode:<5} {sum(ns):<16.1f} {max(ns):<15.1f} {ns[0]:<14.2f} {ft:<19.2f} {same}"
            )
    pathlib.Path("yarngpt2-samples").mkdir(exist_ok=True)
    pathlib.Path("yarngpt2-samples/report-3c.json").write_text(
        json.dumps(rows, indent=2)
    )


if __name__ == "__main__":
    main()
