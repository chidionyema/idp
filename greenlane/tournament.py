"""Paired, read-only policy experiments against Greenlane's actual chaos engine.

All source changes are generated in the first tick, identically for both
policies. There are no later arrivals, repushes, bots, external decisions or
flaky CI. This isolates policy effects without claiming real GitHub latency.
Hostile-event invariants are tested separately in the existing chaos suite.
"""
from __future__ import annotations

import argparse
import json
import statistics
from typing import Sequence

from .simulate import run

REGIMES = {
    "reliable": {"p_broken": 0.02, "p_incompatible": 0.005},
    "mixed": {"p_broken": 0.17, "p_incompatible": 0.015},
    "hostile": {"p_broken": 0.35, "p_incompatible": 0.03},
}


def _check_proof(report, mode: str, regime: str, seed: int) -> None:
    bad = {
        "main_red": report.main_ever_red,
        "broken_landed": report.broken_lanes_landed,
        "work_lost": report.work_lost,
        "good_stranded": report.good_lanes_not_landed,
        "still_open": report.still_open,
        "direct_push": report.direct_push_succeeded,
        "red_pr": report.open_red_pr_observations,
    }
    if any(bad.values()):
        raise AssertionError(f"unsafe {regime}/{mode}/{seed}: {bad}")


def _summarize(items: list) -> dict:
    return {
        "candidates_mean": round(statistics.mean(x.candidates for x in items), 2),
        "ticks_mean": round(statistics.mean(x.ticks for x in items), 2),
        "landed_mean": round(statistics.mean(x.landed for x in items), 2),
        "candidates_per_landing": round(
            sum(x.candidates for x in items) / max(1, sum(x.landed for x in items)), 3
        ),
    }


def run_tournament(lanes: int = 100, seeds: Sequence[int] = (0, 1, 2)) -> dict:
    if lanes < 20 or not seeds:
        raise ValueError("tournament needs >=20 lanes and at least one seed")
    experiments = {}
    for regime, params in REGIMES.items():
        results: dict[str, list] = {"fixed": [], "adaptive": [], "adaptive-speed": []}
        for seed in seeds:
            for mode in ("fixed", "adaptive", "adaptive-speed"):
                report = run(
                    lanes=lanes, seed=seed, ticks=max(1600, 12 * lanes),
                    arrivals_per_tick=lanes, bot_lane_every=0, p_repush=0.0,
                    p_delete=0.0, p_hand_pr=0.0, p_direct_push=0.0,
                    p_flaky=0.0, realistic_ci=True, batch_policy=mode, **params,
                )
                _check_proof(report, mode, regime, seed)
                results[mode].append(report)
        a, b = _summarize(results["fixed"]), _summarize(results["adaptive"])
        speed = _summarize(results["adaptive-speed"])
        saved = round(100 * (a["candidates_mean"] - b["candidates_mean"]) /
                      max(1, a["candidates_mean"]), 2)
        sped = round(100 * (a["ticks_mean"] - b["ticks_mean"]) /
                     max(1, a["ticks_mean"]), 2)
        verdict = ("adaptive-dominates" if saved >= 0 and sped >= 0
                   else "fixed-dominates" if saved <= 0 and sped <= 0
                   else "trade-off")
        experiments[regime] = {
            "fixed": a, "adaptive": b, "adaptive_speed": speed,
            "candidate_reduction_percent": saved,
            "tick_reduction_percent": sped, "verdict": verdict,
            "speed_candidate_reduction_percent": round(100 * (a["candidates_mean"] - speed["candidates_mean"]) / max(1, a["candidates_mean"]), 2),
            "speed_tick_reduction_percent": round(100 * (a["ticks_mean"] - speed["ticks_mean"]) / max(1, a["ticks_mean"]), 2),
        }
    return {
        "schema": "greenlane.policy-tournament.v1",
        "corpus": "same pre-generated work; no post-t0 external randomness",
        "limitation": "candidate counts and engine ticks are proxies, not billed CI or wall time",
        "lanes": lanes, "seeds": list(seeds), "regimes": experiments,
    }


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--lanes", type=int, default=100)
    cli.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = cli.parse_args()
    print(json.dumps(run_tournament(args.lanes, tuple(args.seeds)), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
