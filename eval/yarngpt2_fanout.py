"""Throwaway, run 4: fan-out on GitHub runners, one job per sentence group as one Modal container per group.

synth FANOUT IDX: load the model as YarnSynth does (q8_0, 4 threads), speak group IDX of each note
as mums_concierge.tts_audio.split_for_fanout (copied below) cuts it FANOUT ways; time load and synthesis.
join: a note takes as long as its slowest group. Join the WAVs as production does and let whisper
check that no word was lost at a cut.
"""

import io
import itertools
import json
import pathlib
import re
import sys
import time
import wave

CFG = "wavtokenizer_mediumdata_frame75_3s_nq1_code4096_dim512_kmeans200_attn.yaml"
NOTES = {
    "typical": (
        "Good morning Mummy. Just a reminder that your medicine is due at nine o'clock. "
        "I have also booked the taxi for Thursday at ten, so you do not need to call anyone. "
        "Have a lovely day."
    ),
    "long": (
        "Good afternoon Mummy. Chidi called to say he will visit on Saturday with the children. "
        "He asked me to remind you about the hospital appointment on Monday at eleven. "
        "I have arranged the taxi and it will wait outside the gate. "
        "Please remember to take your blood pressure tablets after lunch. "
        "Call me if you need anything at all."
    ),
}
OUT = pathlib.Path("fanout-out")
GAP_S = 0.12  # AuntieSettings.yarn_gap_s

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_for_fanout(text: str, parts: int) -> list[str]:
    sentences = [s for s in _SENTENCE_END.split(text.strip()) if s]
    parts = max(1, min(parts, len(sentences)))
    best: list[list[str]] = []
    best_len = None
    for cuts in itertools.combinations(range(1, len(sentences)), parts - 1):
        edges = (0, *cuts, len(sentences))
        groups = [sentences[lo:hi] for lo, hi in itertools.pairwise(edges)]
        longest = max(sum(len(s) for s in g) for g in groups)
        if best_len is None or longest < best_len:
            best, best_len = groups, longest
    return [" ".join(g) for g in best if g]


def join_wavs(wavs: list[bytes], gap_s: float) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        for i, raw in enumerate(wavs):
            with wave.open(io.BytesIO(raw), "rb") as r:
                if i == 0:
                    w.setparams(r.getparams())
                    silence = b"\x00" * (
                        int(r.getframerate() * gap_s)
                        * r.getsampwidth()
                        * r.getnchannels()
                    )
                if i:
                    w.writeframes(silence)
                w.writeframes(r.readframes(r.getnframes()))
    return out.getvalue()


def _wer(want: str, got: str) -> float:
    norm = lambda s: re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()  # noqa: E731
    a, b = norm(want), norm(got)
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return round(d[len(b)] / max(len(a), 1), 3)


def synth(fanout: int, idx: int) -> None:
    cpu = next(
        (
            ln.split(":", 1)[1].strip()
            for ln in open("/proc/cpuinfo")
            if ln.startswith("model name")
        ),
        "?",
    )
    print("ENV", json.dumps({"cpu": cpu, "fanout": fanout, "idx": idx}), flush=True)
    t = time.perf_counter()
    import soundfile as sf
    import torch
    from llama_cpp import Llama

    sys.path.insert(0, "/opt")
    from yarngpt.audiotokenizer import AudioTokenizerV2

    torch.set_num_threads(4)
    tok = AudioTokenizerV2("saheedniyi/YarnGPT2", "/w/wavtokenizer.ckpt", f"/w/{CFG}")
    stop = {0, tok.tokenizer.convert_tokens_to_ids("<|audio_end|>")}
    llm = Llama(
        model_path="/w/yarn-q8_0.gguf",
        n_ctx=4096,
        n_threads=4,
        n_threads_batch=4,
        n_batch=512,
        last_n_tokens_size=4096,
        verbose=False,
    )
    load_s = time.perf_counter() - t
    OUT.mkdir(exist_ok=True)
    rows = []
    for name, text in NOTES.items():
        groups = split_for_fanout(text, fanout)
        if idx >= len(groups):
            continue
        group = groups[idx]
        times = []
        for _ in range(2):  # the first after load, then again: runner noise
            t0 = time.perf_counter()
            ids = tok.tokenize_prompt(
                tok.create_prompt(group, lang="english", speaker_name="idera")
            )[0].tolist()
            gen: list[int] = []
            for tid in llm.generate(
                ids,
                top_k=1,
                top_p=1.0,
                min_p=0.0,
                temp=0.0,
                repeat_penalty=1.1,
                reset=True,
            ):
                if tid in stop or len(ids) + len(gen) >= 4096:
                    break
                gen.append(tid)
            codes = tok.extract_integers(tok.tokenizer.decode(gen))
            with torch.inference_mode():
                audio = tok.get_audio(codes).squeeze().numpy()
            buf = io.BytesIO()
            sf.write(buf, audio, 24000, format="WAV")
            times.append(time.perf_counter() - t0)
        (OUT / f"{name}-{fanout}-{idx}.wav").write_bytes(buf.getvalue())
        row = {
            "note": name,
            "fanout": fanout,
            "idx": idx,
            "chars": len(group),
            "load_s": round(load_s, 2),
            "first_s": round(times[0], 2),
            "synth_s": round(min(times), 2),
            "audio_s": round(len(audio) / 24000, 2),
            "gen_tokens": len(gen),
            "cpu": cpu,
        }
        print("RUN", json.dumps(row), flush=True)
        rows.append(row)
    (OUT / f"report-{fanout}-{idx}.json").write_text(json.dumps(rows))


def join() -> None:
    from faster_whisper import WhisperModel

    rows = [r for p in OUT.glob("report-*.json") for r in json.loads(p.read_text())]
    whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
    print(
        "SUMMARY note     fanout groups  note_s  cold_note_s  audio_s  s_per_s  wer   slowest_group_cpu"
    )
    for name, text in NOTES.items():
        for fanout in sorted({r["fanout"] for r in rows}):
            want = split_for_fanout(text, fanout)
            got = sorted(
                (r for r in rows if r["note"] == name and r["fanout"] == fanout),
                key=lambda r: r["idx"],
            )
            if len(got) != len(want):
                print(
                    f"SUMMARY {name:<8} {fanout:<6} missing {len(want) - len(got)} of {len(want)} groups"
                )
                continue
            wavs = [(OUT / f"{name}-{fanout}-{r['idx']}.wav").read_bytes() for r in got]
            path = OUT / f"joined-{name}-{fanout}.wav"
            path.write_bytes(wavs[0] if len(wavs) == 1 else join_wavs(wavs, GAP_S))
            segs, _ = whisper.transcribe(str(path), language="en", beam_size=5)
            heard = " ".join(s.text.strip() for s in segs)
            slow = max(got, key=lambda r: r["synth_s"])
            cold = max(r["load_s"] + r["first_s"] for r in got)
            audio = sum(r["audio_s"] for r in got) + GAP_S * (len(got) - 1)
            print(
                f"SUMMARY {name:<8} {fanout:<6} {len(got):<7} {slow['synth_s']:<7.1f} {cold:<12.1f} {audio:<8.1f}"
                f" {slow['synth_s'] / audio:<8.2f} {_wer(text, heard):<5} {slow['cpu']}"
            )
            print(f"HEARD {name} {fanout}: {heard}")


if __name__ == "__main__":
    join() if sys.argv[1] == "join" else synth(int(sys.argv[2]), int(sys.argv[3]))
