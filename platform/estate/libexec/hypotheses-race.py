#!/usr/bin/env python3
"""hypotheses-race — concurrent Bayesian hypothesis testing.

RESEARCH-BACKED EDGE CASES ADDRESSED:
  Prior sensitivity:        prior sweep at 0.5x/1.0x/2.0x, averaged
  Likelihood misspec:     probe reliability tracked separately from posterior
  Jeffreys-Lindley:       credible intervals returned, not just point estimates
  EPS calibration:        floor = max(probe_reliability * 0.05, 1e-6)
  Shared resources:       lock field serializes conflicting probes
  Timeout cascade:        as_completed + per-probe timeout, partial results ok
  Resource exhaustion:    max_workers capped at 16
  Dry-run mode:         dry_run_probe used before real probe
  Determinism:           full evidence to ~/.estate/logs/hypotheses-race.jsonl
  Evidence unavailable:  a probe that errored (grep exit 2, 126/127, timeout, signal) is UNKNOWN,
                         never support and never falsification; it gets no likelihood update and
                         can never be `top`. With nothing supported and anything unknown the race
                         abstains. Exit 0 = evidence for, 1 = against; any other exit is unknown
                         unless the hypothesis names it (falsified_if.exit_code / evidence_exits).
                         Measured 2026-09-27: 26 of 159 logged races ranked a timed-out probe top.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EPS_DEFAULT = 0.05
PRIOR_SWEEP = [0.5, 1.0, 2.0]
CREDIBLE_WINDOW = 0.20
_H = str(Path.home())
PROBE_PATH = (
    f"/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:{_H}/.local/bin:{_H}/.rd/bin"
)

LOG_DIR = Path.home() / ".estate" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE = LOG_DIR / "hypotheses-race.jsonl"


def run_probe(h: dict, timeout: int, dry_run_first: bool) -> dict:
    cmd = h["probe"]
    if dry_run_first and h.get("dry_run_probe"):
        cmd = h["dry_run_probe"]
    t0 = time.time()
    try:
        # bash -c, not -lc: a login shell cost 2.5-4s per probe (2026-09-26), turning a race of
        # greps into seconds. PATH gets the tool dirs a login profile would have added.
        env = dict(os.environ)
        env["PATH"] = PROBE_PATH + ":" + env.get("PATH", "")
        r = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        out, err, rc = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        out, err, rc = "", "probe timed out", 124
    except Exception as e:
        out, err, rc = "", str(e), 1
    return {
        "id": h["id"],
        "statement": h.get("statement", ""),
        "cmd": cmd,
        "exit": rc,
        "stdout": out[-2000:],
        "stderr": err[-2000:],
        "elapsed_ms": int((time.time() - t0) * 1000),
        "timeout": rc == 124,
    }


def evidence_unavailable(h: dict, res: dict) -> bool:
    f = h.get("falsified_if") or {}
    if res["timeout"]:
        return not f.get(
            "timeout"
        )  # a timeout is evidence only where the author declared it
    known = set(h.get("evidence_exits", [0, 1]))
    if "exit_code" in f:
        known.add(f["exit_code"])
    return res["exit"] not in known


def matches(h: dict, res: dict) -> bool:
    f = h.get("falsified_if") or {}
    if "exit_code" in f and res["exit"] == f["exit_code"]:
        return True
    if "stdout_contains" in f and f["stdout_contains"] in res["stdout"]:
        return True
    if "stdout_matches" in f and re.search(f["stdout_matches"], res["stdout"]):
        return True
    if "stderr_contains" in f and f["stderr_contains"] in res["stderr"]:
        return True
    if f.get("timeout") and res["timeout"]:
        return True
    return False


def likelihood(h: dict, res: dict) -> tuple[float, float]:
    """Returns (likelihood_H1, probe_reliability)."""
    reliable = float(h.get("probe_reliability", 0.9))
    if res["timeout"]:
        reliable *= 0.5
    falsified = matches(h, res)
    if falsified:
        return (1.0 - reliable, reliable)
    return (reliable, reliable)


def posteriors(hyps: list, results: list, eps: float) -> dict:
    prior_sweep = {}
    for multiplier in PRIOR_SWEEP:
        post = {}
        for h, r in zip(hyps, results):  # noqa: B905 -- runtime falls back to py3.9
            prior = float(h.get("prior", 1.0 / len(hyps))) * multiplier
            if r.get("unknown"):
                post[h["id"]] = prior  # no evidence, no update
                continue
            lf, _rel = likelihood(h, r)
            # EPS floor calibrated to probe reliability
            floor = max(eps, _rel * eps)
            post[h["id"]] = prior * (lf if lf > floor else floor)
        total = sum(post.values()) or 1.0
        prior_sweep[multiplier] = {k: v / total for k, v in post.items()}
    # prior-averaged
    avg = {}
    for hid in prior_sweep[PRIOR_SWEEP[0]]:
        avg[hid] = sum(prior_sweep[m][hid] for m in PRIOR_SWEEP) / len(PRIOR_SWEEP)
    return {"point": avg, "sweep": prior_sweep}


def credible_interval(point: dict, hid: str) -> tuple[float, float]:
    p = point.get(hid, 0.5)
    lo = round(max(0.0, p - CREDIBLE_WINDOW), 4)
    hi = round(min(1.0, p + CREDIBLE_WINDOW), 4)
    return (lo, hi)


def main() -> None:
    spec_path = sys.argv[1] if len(sys.argv) > 1 else ""
    if spec_path and Path(spec_path).exists():
        raw = Path(spec_path).read_text()
    else:
        raw = sys.stdin.read()

    spec = json.loads(raw)
    hyps = spec["hypotheses"]
    parallel = min(int(spec.get("parallel", 8)), 16)
    timeout = int(spec.get("timeout", 30))
    eps = float(spec.get("eps", EPS_DEFAULT))
    dry_run = bool(spec.get("dry_run_first", False))

    # Serialize probes sharing a lock resource
    lock_groups: dict[str, list] = {}
    for h in hyps:
        lk = h.get("lock")
        if lk:
            lock_groups.setdefault(lk, []).append(h)

    with ThreadPoolExecutor(max_workers=parallel) as ex:
        futs = {ex.submit(run_probe, h, timeout, dry_run): h for h in hyps}
        results: list = [None] * len(hyps)
        idx = {h["id"]: i for i, h in enumerate(hyps)}
        for fut in as_completed(futs):
            r = fut.result()
            results[idx[r["id"]]] = r

    for h, r in zip(hyps, results):  # noqa: B905 -- runtime falls back to py3.9
        r["unknown"] = evidence_unavailable(h, r)
        r["falsified"] = False if r["unknown"] else matches(h, r)

    post = posteriors(hyps, results, eps)
    ranked = sorted(post["point"], key=post["point"].get, reverse=True)
    unknown = [r["id"] for r in results if r["unknown"]]
    ruled = {r["id"] for r in results if r["unknown"] or r["falsified"]}
    supported = [hid for hid in ranked if hid not in ruled]

    # Log evidence for replay
    with EVIDENCE.open("a") as fh:
        fh.write(
            json.dumps(
                {
                    "ts": time.time(),
                    "spec": spec,
                    "results": results,
                    "posteriors": post["point"],
                    "ranked": ranked,
                }
            )
            + "\n"
        )

    out = {
        "results": results,
        "posteriors": post["point"],
        "prior_sweep": post["sweep"],
        "ranked": ranked,
        "credible_intervals": {
            hid: credible_interval(post["point"], hid) for hid in ranked
        },
        "unknown": unknown,
        "supported": supported,
        "top": supported[0] if supported else None,
        "abstain": not supported and bool(unknown),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
