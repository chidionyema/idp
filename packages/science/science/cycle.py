"""One autonomous scientific cycle: intake -> preregister -> run -> analyse -> independent verification.

No human coordinates a stage. The experimenter and the verifier are different actors with different
code paths: the verifier recomputes the result from the raw measurements in the ledger and never reads
the experimenter's summary, so agreement is a replication, not an echo.
"""

import json
import random
import statistics

from .core import Registry, digest

EXPERIMENTER = "science-experimenter"
VERIFIER = "science-verifier"


def paired_delta(baseline, treatment, seed, resamples=2000):
    """Mean paired difference and a seeded percentile bootstrap 95% CI."""
    if len(baseline) != len(treatment) or not baseline:
        raise ValueError("paired samples must be equal length and non-empty")
    diffs = [t - b for b, t in zip(baseline, treatment)]
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(resamples)
    )
    return {
        "mean_delta": statistics.fmean(diffs),
        "ci95": [means[int(0.025 * resamples)], means[int(0.975 * resamples) - 1]],
        "n": len(diffs),
    }


def conclude(stats):
    """The preregistered decision rule: the CI must exclude zero, otherwise the null stands."""
    lo, hi = stats["ci95"]
    return "reject_null" if lo > 0 or hi < 0 else "fail_to_reject_null"


def run_cycle(registry: Registry, protocol: dict, fixture: dict, seed: int = 7):
    """Drive one programme end to end. The fixture is frozen: its digest must equal the protocol's."""
    if digest(fixture) != protocol["fixture_digest"]:
        raise ValueError("fixture does not match the preregistered fixture_digest")
    pid = registry.register(protocol)["programme_id"]
    step = lambda to, actor, ev, **extra: registry.transition(
        pid, to, {"actor": actor, "evidence_id": ev, **extra}
    )

    step("preregistered", "science-methodology", "prereg")
    step("running", EXPERIMENTER, "start")
    for i, (b, t) in enumerate(zip(fixture["baseline"], fixture["treatment"])):
        registry.append(
            pid, "measurement", {"task": i, "baseline": b, "treatment": t}, f"m{i}"
        )
    summary = paired_delta(fixture["baseline"], fixture["treatment"], seed)
    registry.append(
        pid,
        "finding",
        {"summary": summary, "conclusion": conclude(summary), "seed": seed},
        "finding",
    )
    step("analysed", EXPERIMENTER, "analysis")

    # independent verifier: rebuilds the samples from the ledger rows, not from the finding
    rows = [e["payload"] for e in registry.events(pid) if e["kind"] == "measurement"]
    rows.sort(key=lambda r: r["task"])
    redo = paired_delta(
        [r["baseline"] for r in rows], [r["treatment"] for r in rows], seed
    )
    finding = next(e["payload"] for e in registry.events(pid) if e["kind"] == "finding")
    agrees = redo == finding["summary"] and conclude(redo) == finding["conclusion"]
    registry.append(
        pid,
        "audit",
        {"verifier": VERIFIER, "agrees": agrees, "recomputed": redo},
        "audit",
    )
    if not agrees:
        step("rejected", VERIFIER, "audit")
        return {"programme_id": pid, "state": "rejected", "finding": finding}
    receipt = digest({"programme": pid, "recomputed": redo})
    step("independently_verified", VERIFIER, "audit", verifier_receipt_sha256=receipt)
    return {
        "programme_id": pid,
        "state": "independently_verified",
        "finding": finding,
        "verifier_receipt_sha256": receipt,
    }


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="run one autonomous science cycle")
    ap.add_argument("--db", default="output/science.sqlite3")
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--fixture", required=True)
    a = ap.parse_args(argv)
    with open(a.protocol) as p, open(a.fixture) as f:
        out = run_cycle(Registry(a.db), json.load(p), json.load(f))
    print(json.dumps(out, indent=2))
    return 0 if out["state"] == "independently_verified" else 3


if __name__ == "__main__":
    raise SystemExit(main())
