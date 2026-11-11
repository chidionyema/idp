"""dx_harness_v5 - VoI controller (C) vs fixed ladders (A/B), regimes V5a/b/c.
Single typed-probe contract; deterministic controller; evidence-backed termination.
Operational Python product. Deterministic, LLM-free, stdlib-only.

Usage:
    python3 platform/dx/dx_harness_v5.py            # all regimes, human table
    python3 platform/dx/dx_harness_v5.py V5a_noisy  # one regime
    python3 platform/dx/dx_harness_v5.py --json     # all regimes as JSON

The four substrate-enforced rules (no prompting): evidence multiplicity (>=2 positives /
>=2 negatives), suppression path with log-LR-per-unit-cost scoring, probe-declared operating
characteristics (sig_override / conf_floor), and budget exhaustion -> flagged best-effort.
The Rust crate sharing this directory is a parked port, superseded by this module.
"""

import math, random, statistics

CLASSES = ["HEALTHY", "HTTP500", "CORRUPT", "DEGRADED", "CRASH"]
FAULTS = CLASSES[1:]
CONF, EPS = 0.95, 0.002

# typed probe registry: id -> (cost, base_wall_ms)
PROBE_DEFS = {
    "reach": (1, 5),
    "status": (1, 5),
    "payload": (1, 5),
    "latency": (1, 30),
    "deep": (8, 60),
    "exp": (40, 10),  # V5c: expensive probe duplicating reach+status info
}
LADDER = ["reach", "status", "payload", "latency", "deep", "exp"]
MAP_BATCH = ["reach", "status", "payload", "latency"]
FAULT_PROBE = {
    "CRASH": "reach",
    "HTTP500": "status",
    "CORRUPT": "payload",
    "DEGRADED": "latency",
}

# likelihood of POSITIVE signal per class (sharp deterministic probes by default)
SIG = {
    "reach": {
        "HEALTHY": 0.005,
        "HTTP500": 0.005,
        "CORRUPT": 0.005,
        "DEGRADED": 0.005,
        "CRASH": 0.99,
    },
    "status": {
        "HEALTHY": 0.01,
        "HTTP500": 0.99,
        "CORRUPT": 0.01,
        "DEGRADED": 0.01,
        "CRASH": 0.85,
    },
    "payload": {
        "HEALTHY": 0.005,
        "HTTP500": 0.005,
        "CORRUPT": 0.99,
        "DEGRADED": 0.005,
        "CRASH": 0.01,
    },
    "latency": {
        "HEALTHY": 0.02,
        "HTTP500": 0.05,
        "CORRUPT": 0.05,
        "DEGRADED": 0.95,
        "CRASH": 0.15,
    },
    "deep": {
        "HEALTHY": 0.02,
        "HTTP500": 0.30,
        "CORRUPT": 0.30,
        "DEGRADED": 0.30,
        "CRASH": 0.30,
    },
    "exp": {
        "HEALTHY": 0.005,
        "HTTP500": 0.99,
        "CORRUPT": 0.005,
        "DEGRADED": 0.005,
        "CRASH": 0.99,
    },
}

DEFAULT_PRIORS = {
    "HEALTHY": 0.50,
    "HTTP500": 0.125,
    "CORRUPT": 0.125,
    "DEGRADED": 0.125,
    "CRASH": 0.125,
}
V5B_PRIORS = {
    "CRASH": 0.55,
    "HTTP500": 0.20,
    "CORRUPT": 0.07,
    "DEGRADED": 0.08,
    "HEALTHY": 0.10,
}  # signature memory

REGIMES = {
    "V5a_noisy": dict(
        noise_fp=0.15,
        deg_det=0.75,
        jitter=120,
        priors=None,
        p_healthy=0.35,
        sig_override={"latency": {"HEALTHY": 0.15, "DEGRADED": 0.75}},
        conf_floor=0.98,
    ),
    "V5b_priors": dict(
        noise_fp=0.02, deg_det=0.95, jitter=0, priors=V5B_PRIORS, p_healthy=0.35
    ),
    "V5c_redundant": dict(
        noise_fp=0.02, deg_det=0.95, jitter=0, priors=None, p_healthy=0.35
    ),
}


class Target:
    def __init__(self, name, fault, rng, noise_fp=0.02, deg_det=0.95, jitter=0.0):
        self.name, self.fault, self.rng = name, fault, rng
        self.noise_fp, self.deg_det, self.jitter = noise_fp, deg_det, jitter


def _lat(base, rng, jitter):
    return max(0.5, base * (0.7 + 0.6 * rng.random()) + rng.gauss(0, jitter))


def run_probe(pid, t):
    """Execute one typed probe against a target. Returns (evidence, wall_ms)."""
    rng = t.rng
    cost, base = PROBE_DEFS[pid]
    if pid == "reach":
        if t.fault == "CRASH":
            sig = rng.random() < SIG["reach"]["CRASH"]
        else:
            sig = rng.random() < SIG["reach"]["HEALTHY"]
        return {"sig": sig}, _lat(base, rng, t.jitter)
    if pid == "status":
        if t.fault == "CRASH":
            sig = rng.random() < SIG["status"]["CRASH"]
        elif t.fault == "HTTP500":
            sig = rng.random() < SIG["status"]["HTTP500"]
        else:
            sig = rng.random() < SIG["status"]["HEALTHY"]
        return {"sig": sig, "code": 500 if sig else 200}, _lat(base, rng, t.jitter)
    if pid == "payload":
        if t.fault == "CORRUPT":
            sig = rng.random() < SIG["payload"]["CORRUPT"]
        else:
            sig = rng.random() < SIG["payload"]["HEALTHY"]
        return {"sig": sig}, _lat(base, rng, t.jitter)
    if pid == "latency":
        if t.fault == "DEGRADED":
            sig = rng.random() < t.deg_det  # V5a: noisy probe -> 0.75
        elif t.fault == "CRASH":
            sig = rng.random() < SIG["latency"]["CRASH"]
        else:
            sig = (
                rng.random() < t.noise_fp
            )  # V5a: healthy jitter crosses threshold 15% of single samples
        ms = (400 if sig else 20) * (0.7 + 0.6 * rng.random())
        return {"sig": sig, "ms": ms}, _lat(base, rng, t.jitter) + (26 if sig else 1)
    if pid == "deep":
        sig = (t.fault != "HEALTHY" and rng.random() < SIG["deep"]["HTTP500"]) or (
            t.fault == "HEALTHY" and rng.random() < SIG["deep"]["HEALTHY"]
        )
        return {"sig": sig}, _lat(base, rng, t.jitter)
    if pid == "exp":
        # redundant expensive probe: observation entailed by reach && status
        reach_sig = (t.fault == "CRASH" and rng.random() < SIG["reach"]["CRASH"]) or (
            t.fault != "CRASH" and rng.random() < SIG["reach"]["HEALTHY"]
        )
        if t.fault == "CRASH":
            st_sig = rng.random() < SIG["status"]["CRASH"]
        elif t.fault == "HTTP500":
            st_sig = rng.random() < SIG["status"]["HTTP500"]
        else:
            st_sig = rng.random() < SIG["status"]["HEALTHY"]
        return {"sig": reach_sig or st_sig}, _lat(base, rng, t.jitter)
    raise ValueError(pid)


# ---------- belief machinery ----------
def update(b, pid, sig):
    out = {c: b[c] * (SIG[pid][c] if sig else 1 - SIG[pid][c]) for c in CLASSES}
    z = sum(out.values())
    return {c: out[c] / z for c in CLASSES}


def entropy(b):
    return -sum(x * math.log(x) for x in b.values() if x > 1e-15)


def voi(pid, b):
    h0 = entropy(b)
    p_pos = sum(SIG[pid][c] * b[c] for c in CLASSES)
    exp = 0.0
    for sig, po in ((True, p_pos), (False, 1 - p_pos)):
        if po > 1e-12:
            exp += po * entropy(update(b, pid, sig))
    return h0 - exp


def check_termination(b, pos, neg, priors, conf_min=CONF):
    """posterior >= conf_min AND evidence-backed.
    HEALTHY: every fault suppressed <= EPS with >=2 confirmed negatives.
    Fault: >=2 positive signature observations; a high-prior (>=0.25) competing fault must be
    actively suppressed (>=2 confirmed negatives), not merely absent."""
    top = max(b, key=b.get)
    if b[top] < conf_min:
        return None
    if top == "HEALTHY":
        for f in FAULTS:
            if b[f] > EPS:
                return None
            if neg.get(FAULT_PROBE[f], 0) < 2:
                return None
        return "HEALTHY"
    if (
        pos.get(FAULT_PROBE[top], 0) < 2
    ):  # evidence multiplicity: no single-sample fault verdicts
        return None
    for f in FAULTS:
        if f != top and priors.get(f, 0) >= 0.25 and neg.get(FAULT_PROBE[f], 0) < 2:
            return None
    return top


def controller_c(
    t,
    priors,
    budget=60.0,
    voi_thresh=0.35,
    max_rounds=20,
    max_reruns=10,
    conf_floor=CONF,
):
    """VoI policy over explicit belief state. Batched parallel rounds, reruns allowed, cost-aware."""
    b = dict(priors)
    pos, neg, ran_counts = {}, {}, {}
    cost = wall = 0.0
    for _ in range(max_rounds):
        v = check_termination(b, pos, neg, priors, conf_floor)
        if v:
            return v, b[v], cost, wall, False
        cand = {pid: voi(pid, b) for pid in PROBE_DEFS}
        order = sorted(
            PROBE_DEFS, key=lambda pid: cand[pid] / PROBE_DEFS[pid][0], reverse=True
        )
        best = order[0]
        batch = []
        if cand[best] > 1e-4 and cost < budget:
            maxr = cand[best] / PROBE_DEFS[best][0]
            for pid in order:
                if (
                    cand[pid] > voi_thresh
                    and cand[pid] / PROBE_DEFS[pid][0] >= maxr / 4
                    and ran_counts.get(pid, 0) < max_reruns
                    and cost + PROBE_DEFS[pid][0] <= budget
                ):
                    batch.append(pid)
        if not batch:
            # suppression path (batched): signature probes of ALL faults needing work, cheapest-first, in parallel
            over = [f for f in FAULTS if b[f] > EPS or neg.get(FAULT_PROBE[f], 0) < 2]
            if over and cost < budget:

                def need(f, b=b):
                    return b[f] > EPS or neg.get(FAULT_PROBE[f], 0) < 2

                def score(pid, f):
                    p = min(max(SIG[pid][f], 1e-6), 1 - 1e-6)
                    ph = min(max(SIG[pid]["HEALTHY"], 1e-6), 1 - 1e-6)
                    return abs(math.log(p) - math.log(ph)) / PROBE_DEFS[pid][0]

                cands = sorted(
                    (
                        (score(FAULT_PROBE[f], f), FAULT_PROBE[f])
                        for f in over
                        if need(f)
                    ),
                    key=lambda x: PROBE_DEFS[x[1]][0],
                )
                for _, pid in cands:
                    if (
                        ran_counts.get(pid, 0) < max_reruns
                        and cost + PROBE_DEFS[pid][0] <= budget
                    ):
                        batch.append(pid)
        if not batch:
            break  # budget exhausted or nothing informative left
        rwall = 0.0
        for pid in batch:
            ev, lat = run_probe(pid, t)
            cost += PROBE_DEFS[pid][0]
            ran_counts[pid] = ran_counts.get(pid, 0) + 1
            if ev["sig"]:
                pos[pid] = pos.get(pid, 0) + 1
            else:
                neg[pid] = neg.get(pid, 0) + 1
            b = update(b, pid, ev["sig"])
            rwall = max(rwall, lat)
        wall += rwall
    v = max(b, key=b.get)
    return v, b[v], cost, wall, True  # best-effort


# ---------- fixed ladders (baselines from v2/v3/v4) ----------
def verdict_from(sigs):
    for pid, f in (
        ("reach", "CRASH"),
        ("status", "HTTP500"),
        ("payload", "CORRUPT"),
        ("latency", "DEGRADED"),
    ):
        if sigs.get(pid):
            return f
    return "HEALTHY"


def ladder(t, which):
    cost = wall = 0.0
    sigs = {}
    if which == "A":  # exhaustive, sequential
        for pid in LADDER:
            ev, lat = run_probe(pid, t)
            sigs[pid] = ev["sig"]
            cost += PROBE_DEFS[pid][0]
            wall += lat
    else:  # B: map (parallel cheap) -> reduce -> probe (deep layer parallel)
        rw = 0.0
        for pid in MAP_BATCH:
            ev, lat = run_probe(pid, t)
            sigs[pid] = ev["sig"]
            cost += PROBE_DEFS[pid][0]
            rw = max(rw, lat)
        wall += rw
        rw = 0.0
        for pid in ("deep", "exp"):
            ev, lat = run_probe(pid, t)
            sigs[pid] = ev["sig"]
            cost += PROBE_DEFS[pid][0]
            rw = max(rw, lat)
        wall += rw
    return verdict_from(sigs), cost, wall


# ---------- trials ----------
def ece(records, n_bins=5):
    bins = [[] for _ in range(n_bins)]
    for conf, ok in records:
        bins[min(n_bins - 1, int(conf * n_bins))].append((conf, ok))
    n = len(records)
    e = 0.0
    for bk in bins:
        if bk:
            c = sum(x[0] for x in bk) / len(bk)
            a = sum(1 for x in bk if x[1]) / len(bk)
            e += len(bk) / n * abs(c - a)
    return e


def run_regime(regime, n_trials=15, n_targets=5):
    cfg = REGIMES[regime]
    priors = cfg["priors"] or DEFAULT_PRIORS
    saved = {pid: SIG[pid].copy() for pid in (cfg.get("sig_override") or {})}
    for pid, ov in (cfg.get("sig_override") or {}).items():
        SIG[pid].update(ov)
    acc = {c: [] for c in "ABC"}
    for tr in range(n_trials):
        for ti in range(n_targets):
            seed = f"{regime}:{tr}:{ti}"
            frng = random.Random(seed + ":fault")  # noqa: S311 - deterministic sim seed, not crypto
            fault = (
                "HEALTHY" if frng.random() < cfg["p_healthy"] else frng.choice(FAULTS)
            )
            for ctl in "ABC":
                t = Target(
                    f"t{ti}",
                    fault,
                    random.Random(f"{seed}:{ctl}"),  # noqa: S311 - deterministic sim seed, not crypto
                    noise_fp=cfg["noise_fp"],
                    deg_det=cfg["deg_det"],
                    jitter=cfg["jitter"],
                )
                if ctl == "C":
                    v, conf, cost, wall, be = controller_c(
                        t, priors, conf_floor=cfg.get("conf_floor", CONF)
                    )
                else:
                    v, cost, wall = ladder(t, ctl)
                    conf, be = 1.0, False
                acc[ctl].append(
                    dict(true=fault, verdict=v, conf=conf, cost=cost, wall=wall, be=be)
                )
    for pid, s in saved.items():
        SIG[pid].clear()
        SIG[pid].update(s)
    return acc


def summarize(rows):
    sick = [r for r in rows if r["true"] != "HEALTHY"]
    healthy = [r for r in rows if r["true"] == "HEALTHY"]
    det = sum(1 for r in sick if r["verdict"] == r["true"])
    fp = sum(1 for r in healthy if r["verdict"] != "HEALTHY")
    return dict(
        n=len(rows),
        n_sick=len(sick),
        n_healthy=len(healthy),
        det=det,
        fn=sum(1 for r in sick if r["verdict"] == "HEALTHY"),
        wrong=sum(1 for r in sick if r["verdict"] not in (r["true"], "HEALTHY")),
        fp=fp,
        det_rate=det / max(1, len(sick)),
        fp_rate=fp / max(1, len(healthy)),
        cost=statistics.mean(r["cost"] for r in rows),
        wall=statistics.mean(r["wall"] for r in rows),
        ece=ece([(r["conf"], r["verdict"] == r["true"]) for r in rows]),
        be=sum(1 for r in rows if r["be"]),
    )


# ---------- reproduction entrypoint ----------
def _run_all_regimes(n_trials=15, n_targets=5):
    out = {}
    for regime in REGIMES:
        acc = run_regime(regime, n_trials=n_trials, n_targets=n_targets)
        out[regime] = {ctl: summarize(acc[ctl]) for ctl in "ABC"}
    return out


def main(argv=None):
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(
        prog="dx_harness_v5",
        description="VoI controller (C) vs fixed ladders (A/B) across V5 regimes.",
    )
    p.add_argument(
        "regime",
        nargs="?",
        default=None,
        help="one of %s (default: all)" % "/".join(REGIMES),
    )
    p.add_argument("--trials", type=int, default=15)
    p.add_argument("--targets", type=int, default=5)
    p.add_argument(
        "--json", action="store_true", help="emit JSON for the chosen regime(s)"
    )
    args = p.parse_args(argv)

    if args.regime is not None and args.regime not in REGIMES:
        print(
            "unknown regime %r; choose one of: %s" % (args.regime, ", ".join(REGIMES)),
            file=sys.stderr,
        )
        return 2

    regimes = [args.regime] if args.regime else list(REGIMES)
    out = {}
    for regime in regimes:
        acc = run_regime(regime, n_trials=args.trials, n_targets=args.targets)
        out[regime] = {ctl: summarize(acc[ctl]) for ctl in "ABC"}

    if args.json:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        for regime, ctrls in out.items():
            print("# %s" % regime)
            for ctl in "ABC":
                s = ctrls[ctl]
                print(
                    "  %s: det %d/%d (%.1f%%)  FP %d (%.1f%%)  cost %.2f  wall %.1fms  ECE %.4f  be %d"
                    % (
                        ctl,
                        s["det"],
                        s["n_sick"],
                        100 * s["det_rate"],
                        s["fp"],
                        100 * s["fp_rate"],
                        s["cost"],
                        s["wall"],
                        s["ece"],
                        s["be"],
                    )
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
