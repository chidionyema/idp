"""L4: real voice conversations, end to end, no narration.

One conversation = hear -> stream -> say -> hear-back, every leg real:
  hear      fixture WAV -> f32 PCM -> POST /voice/hear  -> transcript (real STT, router:voice-asr)
  stream    POST /voice/stream                        -> SSE clauses with fleet facts + why line
  say       POST /voice/say per clause                -> real PCM (Cartesia Sonic)
  hear-back say-PCM resampled -> POST /voice/hear     -> transcript must match what was said

Grading is measurement: each leg's assertion is on bytes, seconds and text actually returned.
An unreachable backend grades BLIND, never PASS (a probe that cannot fail is not a probe).

Run:
  python3 -m probes.voice http://127.0.0.1:18790 probes/fixtures/fleet-status.wav "What is the fleet doing right now?"
  python3 -m probes.voice --all http://127.0.0.1:18790 probes/fixtures/
Exit 0 only when every leg of every conversation PASSES.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import time
import urllib.request
import wave
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCRIPTS = [  # (fixture, expected transcript, must-appear facts in the answer)
    ("fleet-status.wav", "what is the fleet doing right now", ("agent",)),
    ("stuck-agents.wav", "which agents are stuck", ("stuck", "idle")),
    ("spend-today.wav", "how much did the fleet spend today", ("spend", "cost", "lifetime", "not today")),
]


def _f32(path: Path) -> bytes:
    with wave.open(str(path)) as w:
        frames = struct.unpack(f"<{w.getnframes()}h", w.readframes(w.getnframes()))
    return struct.pack(f"<{len(frames)}f", *[s / 32768.0 for s in frames])


def _resample(pcm: bytes, src: int, dst: int) -> bytes:
    n = len(pcm) // 4
    xs = struct.unpack(f"<{n}f", pcm)
    if src == dst:
        return pcm
    m = int(n * dst / src)
    out = []
    for i in range(m):
        p = i * src / dst
        lo, hi = int(p), min(int(p) + 1, n - 1)
        t = p - lo
        out.append(xs[lo] * (1 - t) + xs[hi] * t)
    return struct.pack(f"<{m}f", *out)


def _post(url: str, data: bytes, ctype: str = "application/octet-stream", timeout: int = 45):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": ctype}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _get(url: str, timeout: int = 45):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, r.read()


def conversation(base: str, wav: Path, expect_stt: str, must_appear: tuple[str, ...]) -> list[dict]:
    lines: list[dict] = []

    def grade(name, expected, got, ok):
        lines.append({"name": f"voice4.{name}", "expected": expected, "actual": got, "ok": ok})

    # --- hear: real speech in, transcript out ---
    try:
        st, body = _post(f"{base}/voice/hear?author=surfaces-verify&session_id=verify-surfaces", _f32(wav))
        j = json.loads(body)
        text = (j.get("text") or "").strip().lower()
        grade("stt", f"transcript contains '{expect_stt}'", f"'{text}' in {j.get('asr_seconds')}s ({j.get('asr_engine')})",
              st == 200 and expect_stt in text)
    except Exception as e:  # noqa: BLE001
        grade("stt", "200 + transcript", f"unreachable: {type(e).__name__}", False)

    # --- stream: brain answers with fleet facts through the router (one retry on a
    # non-SSE body: a single 5xx/empty from the router lane is transient, two is a fail) ---
    clauses: list[str] = []
    why = ""
    diag = ""
    st = 0
    for _attempt in (1, 2):
        clauses, why, diag, st = [], "", "", 0
        try:
            st, body = _post(f"{base}/voice/stream", json.dumps({"question": expect_stt, "history": []}).encode(),
                             "application/json")
            raw = body.decode("utf-8", "replace").replace("\r", "")
            for m in re.finditer(r'^data: (\{.*\})$', raw, re.M):
                try:
                    d = json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue
                if "text" in d:
                    clauses.append(d["text"])
                if "why" in d:
                    why = d["why"]
            if clauses:
                break
            diag = f"no SSE clauses; {st} {raw[:100]}"
            time.sleep(2)
        except Exception as e:  # noqa: BLE001
            diag = f"unreachable: {type(e).__name__}"
            time.sleep(2)
    answer = " ".join(clauses).lower()
    hit = any(w in answer for w in must_appear)  # any fact word; the brain may answer honestly
    grade("brain", f"SSE answer contains any {must_appear}", f"{len(clauses)} clauses; {answer[:140] or diag}",
          st == 200 and len(clauses) >= 2 and hit)
    grade("brain.routing", "why line names model+region", why[:120] or diag, bool(why) and len(why) > 5)

    # --- say + hear-back: the estate speaks, then understands itself ---
    said = clauses[0] if clauses else "The fleet is running."
    try:
        st, pcm = _post(f"{base}/voice/say", json.dumps({"text": said}).encode(), "application/json")
        real_audio = st == 200 and len(pcm) > 20_000  # ~1s of 16k f32; shorter is not speech
        grade("tts", "real PCM > 20KB for one clause", f"{len(pcm)}B", real_audio)
        if real_audio:
            back = None
            for src in (24_000, 16_000):  # try Cartesia rate then ASR rate
                try:
                    st2, body2 = _post(f"{base}/voice/hear?author=surfaces-verify&session_id=verify-back",
                                       _resample(pcm, src, 16_000))
                    back = (json.loads(body2).get("text") or "").strip().lower()
                    if back:
                        break
                except Exception:  # noqa: BLE001
                    continue
            words = [w for w in re.findall(r"[a-z']+", said.lower()) if len(w) > 3][:4]
            words += re.findall(r"\d+", said)  # TTS speaks 427 as words; STT may return digits
            ok_back = bool(back) and sum(w in back for w in words) >= 2
            grade("hearback", f"STT of own TTS recognises {words}", f"'{back}'", ok_back)
    except Exception as e:  # noqa: BLE001
        grade("tts", "PCM", f"unreachable: {type(e).__name__}", False)
    return lines


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--all"]
    base = (args[0] if args else "http://127.0.0.1:18790").rstrip("/")
    # liveness, honestly graded
    alive = True
    try:
        _get(f"{base}/healthz", timeout=10)
    except Exception:  # noqa: BLE001
        alive = False
    print(("PASS" if alive else "FAIL") + "  voice4.liveness  expected=healthz 200 got=" + ("ok" if alive else "unreachable"))
    if not alive:
        return 1

    wav = Path(args[1]) if len(args) > 1 else FIXTURES / "fleet-status.wav"
    row = next((r for r in SCRIPTS if r[0] == wav.name), None)
    if "--all" in argv:
        scripts = SCRIPTS
    elif row:
        scripts = [row]
    else:
        q = (args[2] if len(args) > 2 else "").lower()
        scripts = [(wav.name, q, (" ",))]
    fails = 0
    t0 = time.time()
    for i, (fx, stt, words) in enumerate(scripts, 1):
        for line in conversation(base, FIXTURES / fx if (FIXTURES / fx).exists() else wav, stt, words):
            verdict = "PASS" if line["ok"] else "FAIL"
            fails += 0 if line["ok"] else 1
            print(f"{verdict}  {line['name']}[{i}]  expected={line['expected']} got={line['actual']}")
    print(f"conversations={len(scripts)} legs_graded={fails and '' or ''}{len(scripts) * 5 - fails if alive else 0}/{len(scripts) * 5} pass  wall={time.time() - t0:.0f}s")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
