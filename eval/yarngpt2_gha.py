"""Throwaway, run 3b: the run-3 variants on a GitHub runner, because Modal refused the job (spend limit).

Same engine, texts and checks as eval/yarngpt2_fast.py, 2 threads to match production's cpu=2.0.
Measures quants (WER via Whisper), prompt-lookup speculative decoding (codes hash must equal the
control's), and per-sentence timing. Container fan-out and cold start need Modal and are not here.
Absolute seconds are the runner's, not Modal's: read the DELTAS against the control run in the same job.
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
            n_threads_batch=self.ncpu, n_batch=512, last_n_tokens_size=4096, logits_all=lookup, verbose=False,
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


def main() -> None:
    out = pathlib.Path("yarngpt2-samples")
    out.mkdir(exist_ok=True)
    eng = _Engine(2)
    rows = []
    for option, quant, lookup in (
        ("A llama-q8_0", "q8_0", False),
        ("B llama-q6_k", "q6_k", False),
        ("B llama-q5_k_m", "q5_k_m", False),
        ("C llama-q8_0+lookup", "q8_0", True),
        ("A llama-q8_0 (again)", "q8_0", False),
    ):
        load_s = eng.load(quant, lookup)
        for name, text in TEXTS.items():
            r = eng.speak(text, "idera")
            if "wav" in r:
                heard = _say(r["wav"])
                (out / f"{option.split()[0]}-{quant}{'-lookup' if lookup else ''}-{name}.wav").write_bytes(_wav_bytes(r.pop("wav")))
                r.update(heard=heard, wer=_wer(text, heard))
            r.update(option=option, text=name, load_s=round(load_s, 1))
            rows.append(r)
            print("BENCH", json.dumps({k: v for k, v in r.items() if k != "heard"}), flush=True)
    # Per-sentence cost with the control: fan-out wall-clock is bounded below by the slowest one.
    eng.load("q8_0")
    per = []
    for s in SENTENCE.split(TEXTS["typical"]):
        r = eng.speak(s, "idera")
        per.append({"sentence": s, "note_s": r.get("note_s"), "audio_s": r.get("audio_s"), "first_token_s": r.get("first_token_s")})
        print("SENTENCE", json.dumps(per[-1]), flush=True)
    (out / "report.json").write_text(json.dumps({"rows": rows, "per_sentence": per}, indent=2))
    print("SUMMARY option                 text     note_s  audio_s tok/s  wer    codes_sha   load_s")
    for r in rows:
        if "error" in r:
            print(f"SUMMARY {r['option']:<22} {r['text']:<8} ERROR {r['error']}")
        else:
            print(f"SUMMARY {r['option']:<22} {r['text']:<8} {r['note_s']:<7} {r['audio_s']:<7} {r['tok_per_s']:<6} {r['wer']:<6} {r['codes_sha']}  {r['load_s']}")
    tot = sum(p["note_s"] or 0 for p in per)
    print(f"SUMMARY typical note: one container {tot:.1f}s; fan-out lower bound (slowest sentence) {max(p['note_s'] or 0 for p in per):.1f}s; first audio {per[0]['note_s']}s")


if __name__ == "__main__":
    main()
