#!/usr/bin/env python3
"""voice-doctor -- walk the voice chain in order and name the first broken link.

WHY. 2026-09-29 voice was dead on the laptop and in OKE for four separate reasons, each found by
hand from plists and logs: the router had no `voice` lane (its config never followed main), the
speech models were deleted under a running voice-router, TTS failed on every reply, and OKE ran a
three-day-old crashing image because the Flux row that applies image policies had been deleted.
Every one is a check below, in the order a spoken turn meets them.

Exit 0 when a real spoken turn gets spoken audio back; otherwise 1, with the first broken link and
the action that fixes it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
ROUTER = "http://127.0.0.1:4000"
VOICE = "http://127.0.0.1:8091"
TREE = HOME / ".estate/runtime/idp"
# The router renders its served lanes here at start (ESTATE_ROUTER_STATE); the copy beside its code
# in ~/.estate/litellm-local is a stale leftover of an older launcher.
LANES = HOME / ".estate/router-state/lanes.json"
VOICE_LOG = HOME / "Library/Logs/voice-router.log"
VOICE_ERR = HOME / "Library/Logs/voice-router.err.log"
PLIST = HOME / "Library/LaunchAgents/ai.estate.voice-router.plist"

results: list[tuple[str, bool, str, str]] = []  # (link, ok, detail, fix)


def check(link: str, ok: bool, detail: str, fix: str = "") -> bool:
    results.append((link, ok, detail, fix))
    print(f"  {'ok  ' if ok else 'FAIL'}  {link:22} {detail}")
    return ok


def get(url: str, timeout: float = 20) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 -- fixed http://127.0.0.1 URLs in this file
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, str(e)


def since_start(log: Path, marker: str) -> list[str]:
    """The log's lines since the running process started (its last `marker` line). Errors from
    before a restart are history, not the state: on 2026-09-29 the doctor failed a voice that had
    just spoken a 6 s reply, counting token errors from before the models came back."""
    if not log.exists():
        return []
    lines = log.read_text(errors="replace")[-2_000_000:].splitlines()
    starts = [i for i, line in enumerate(lines) if marker in line]
    return lines[starts[-1] + 1 :] if starts else lines[-400:]


def models_dir() -> Path:
    m = (
        re.search(
            r"<key>VOICE_MODELS</key>\s*<string>([^<]+)</string>", PLIST.read_text()
        )
        if PLIST.exists()
        else None
    )
    return Path(m.group(1)) if m else HOME / ".cache/estate-tools/sherpa-models"


def laptop() -> None:
    print("== laptop voice ==")
    load = float(
        subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            ["/usr/sbin/sysctl", "-n", "vm.loadavg"], capture_output=True, text=True
        ).stdout.split()[1]
    )
    cores = int(
        subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            ["/usr/sbin/sysctl", "-n", "hw.ncpu"], capture_output=True, text=True
        ).stdout
    )
    check(
        "machine load",
        load < cores * 4,
        f"load {load:.0f} on {cores} cores",
        "timeouts below may be the machine, not the code: close sessions/tabs or run the OKE check",
    )

    mdir = models_dir()
    dockerfile = TREE / "platform/voice-router/Dockerfile"
    pins = (
        re.findall(r"fetch (?:asr|tts)-models/(\S+)\.tar\.bz2", dockerfile.read_text())
        if dockerfile.exists()
        else []
    )
    missing = [p for p in pins if not (mdir / p).is_dir()]
    check(
        "speech models",
        bool(pins) and not missing,
        f"{mdir}: "
        + (f"missing {', '.join(missing)}" if missing else f"{len(pins)} present"),
        "launchctl kickstart -k gui/$(id -u)/ai.estate.voice-router  (the launcher fetches the pinned models)",
    )

    code, _ = get(f"{ROUTER}/health/liveliness", 30)
    check(
        "router up",
        code == 200,
        f"/health/liveliness {code or 'unreachable'}",
        "bash ~/.estate/litellm-local/litellm-local swap   # boots the router beside the live one",
    )

    served = json.loads(LANES.read_text()).get("served", []) if LANES.exists() else []
    on_main = (
        TREE.joinpath("llm/config.yaml").exists()
        and re.search(
            r"^  - model_name: voice$",
            TREE.joinpath("llm/config.yaml").read_text(),
            re.M,
        )
        is not None
    )
    check(
        "router voice lane",
        "voice" in served,
        f"served {'has' if 'voice' in served else 'LACKS'} `voice` (main {'has' if on_main else 'lacks'} it)",
        "estate-runtime-sync carries llm/config.yaml to the router; check ~/.estate/runtime-sync.log"
        if on_main
        else "add the `voice` lane to llm/config.yaml on main",
    )

    code, body = get(f"{VOICE}/readyz", 40)
    check(
        "voice-router ready",
        code == 200,
        f"/readyz {code or 'unreachable'} {body.strip()[:140]}",
        "read the detail: it names the router call that failed",
    )

    tts_err = sum(
        "voice.tts" in line and "ERROR" in line
        for line in since_start(VOICE_LOG, '"voice.ready"')
    )
    token_err = sum(
        "Failed to convert" in line
        for line in since_start(VOICE_ERR, "voice-router-launchd:")
    )
    check(
        "speech synthesis",
        tts_err == 0 and token_err == 0,
        f"{tts_err} tts errors, {token_err} token errors since voice-router last started",
        "models missing under a running router: restart it so the launcher fetches them",
    )

    turn(mdir)


def turn(mdir: Path) -> None:
    talk = shutil.which("voice-talk") or str(HOME / ".cache/estate-tools/voice-talk")
    go = shutil.which("go") or str(HOME / ".cache/estate-tools/go/bin/go")
    if not Path(talk).exists():
        r = subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            [go, "build", "-o", talk, "./cmd/talk"],
            cwd=TREE / "platform/voice-router",
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode:
            check(
                "spoken turn",
                False,
                f"could not build cmd/talk: {r.stderr.strip()[-160:]}",
            )
            return
    with tempfile.TemporaryDirectory() as d:
        aiff, wav = f"{d}/q.aiff", f"{d}/q.wav"
        subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            ["/usr/bin/say", "-o", aiff, "What is the status of the fleet?"], check=True
        )
        subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            [
                "/usr/bin/afconvert",
                "-f",
                "WAVE",
                "-d",
                "LEI16@16000",
                "-c",
                "1",
                aiff,
                wav,
            ],
            check=True,
        )
        r = subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            [talk, "-wav", wav], capture_output=True, text=True, timeout=120
        )
    out = r.stdout + r.stderr
    heard = re.findall(r'final\s+\d+ "([^"]*)"', out)
    audio = re.search(r"reply audio ([0-9.]+)s", out)
    secs = float(audio.group(1)) if audio else 0.0
    err = re.findall(r'error\s+\d+ "([^"]*)"|^read: .*$', out, re.M)
    check(
        "spoken turn",
        secs > 0,
        f"heard {heard[-1]!r} -> {secs:.2f}s of reply audio"
        + (f"; {err[-1]}" if err else "")
        if heard
        else f"nothing heard: {out.strip()[-160:]}",
        "the first FAIL above is the cause",
    )


def oke() -> None:
    print("== OKE voice ==")

    def k(*a: str) -> tuple[int, str]:
        r = subprocess.run(  # noqa: S603 -- argv built in this file, no shell
            [
                shutil.which("kubectl") or "/usr/local/bin/kubectl",
                "--request-timeout=30s",
                *a,
            ],
            capture_output=True,
            text=True,
        )
        return r.returncode, (r.stdout or r.stderr).strip()

    rc, _ = k("-n", "flux-system", "get", "imagepolicy", "voice-router")
    check(
        "image policy",
        rc == 0,
        "flux-system/voice-router " + ("present" if rc == 0 else "MISSING"),
        "a Flux row under clusters/oke must apply platform/image-automation",
    )
    rc, out = k(
        "-n",
        "voice-router",
        "get",
        "deploy",
        "-o",
        "jsonpath={range .items[*]}{.metadata.name} {.status.readyReplicas}/{.spec.replicas} "
        '{.spec.template.spec.containers[0].image}{"\\n"}{end}',
    )
    for line in out.splitlines() if rc == 0 else [out]:
        parts = line.split()
        ok = len(parts) == 3 and parts[1].split("/")[0] == parts[1].split("/")[1] != ""
        check(
            "deployment",
            ok,
            line[:160],
            "kubectl -n voice-router logs deploy/<name> --previous",
        )


def main() -> int:
    if "--oke-only" not in sys.argv:
        laptop()
    if "--laptop-only" not in sys.argv:
        oke()
    bad = [r for r in results if not r[1]]
    print("\n== verdict ==")
    if not bad:
        print("  voice works end to end.")
        return 0
    link, _, detail, fix = bad[0]
    print(f"  first broken link: {link} -- {detail}")
    if fix:
        print(f"  next: {fix}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
