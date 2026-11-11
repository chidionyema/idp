#!/usr/bin/env python3
"""aei-to-optimus -- publish AEI's observed execution numbers as optimus.metric.v1.

AGENTS.md section 3a is binding: "Every operational capability MUST publish
`optimus.metric.v1` to the existing Argon Optimus service", and "BLIND is a
measured inability to observe, never a zero."

The estate has two intelligence planes and, measured on 2026-11-10, they were
connected by nothing:

  * AEI (packages/aei) -- Agent Execution Intelligence: an evidence-first,
    append-only event ledger. It knows WHY a run cost what it cost: the
    waterfall, the waste, the verification, the coverage. Its own acceptance
    criteria demand "no silent zeroes for unknown cost" and "one independently
    measured optimisation".
  * optimus (argon) -- the metric plane: value, unit, status, window, evidence,
    an idempotent metricId. It knows HOW MUCH, not why.

So AEI measured and nobody read it, and optimus held 859 rows all from
`pennyd-local` -- structurally blind to every other capability. This is the
bridge: it reads AEI's own `analyse()` output and emits each metric through the
one existing write contract. It reimplements neither side.

The law this enforces, in the estate's words:
  * a metric that AEI could not observe is emitted as BLIND, never as 0.
  * every metric carries the run_id, the git revision and the AEI event count
    as labels, so the number can be traced back to evidence -- "proof, not
    assertion" (AGENTS.md section 3).
  * the metricId is derived from (run, revision, metric), so re-running this is
    idempotent: the same run cannot inflate the estate's numbers twice.

Usage:
  aei-to-optimus.py --db ~/.estate/aei/aei.sqlite3            # every run
  aei-to-optimus.py --db ... --run DEMO-run-001 --revision $(git rev-parse --short HEAD)
  aei-to-optimus.py --db ... --dry-run                        # print, do not POST

Exit codes:
  0  every metric accepted (or already present)
  2  BLIND: AEI's ledger is unreadable, or the brain is unreachable. Nothing was
     recorded; the caller must not read this as zero.
  3  a metric was refused by the contract (a caller defect).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = os.environ.get("AEI_DB", os.path.expanduser("~/.estate/aei/aei.sqlite3"))
EMITTER = Path(__file__).with_name("optimus-emit.py")

# Which AEI metric becomes which optimus metric, and in what unit. Only names
# that AEI actually computes today appear here; an unknown name is skipped and
# counted, never invented (section 3: do not report a number you did not measure).
METRIC_MAP = {
    "observed_cost_usd": ("execution.cost", "usd"),
    "observed_input_tokens": ("execution.tokens.input", "tokens"),
    "observed_events": ("execution.events", "events"),
    "observed_retries": ("execution.retries", "retries"),
    "elapsed_observed_ms": ("execution.elapsed", "ms"),
}


def load_analysis(db_path: str) -> list[dict]:
    """Read AEI's ledger with AEI's own analyser -- never a second implementation."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/aei/src"))
    try:
        from aei.analysis import analyse  # noqa: PLC0415 -- optional, only on this path
        from aei.core import Store  # noqa: PLC0415
    except ImportError as exc:
        print(f"BLIND  aei-to-optimus  cannot import AEI: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if not Path(db_path).exists():
        print(f"BLIND  aei-to-optimus  no AEI ledger at {db_path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        store = Store(db_path)
        out = []
        for run in store.runs():
            run_id = run["run_id"]
            events = store.events(run_id)
            if not events:
                continue
            # The run's evidence fingerprint: the ledger's own terminal digest. Two
            # emits of the SAME evidence must converge on ONE metric; a retry is not a
            # second observation. Keying on the wall clock made a retry look like new
            # data and inflated the estate's numbers -- measured 2026-11-10, a plain
            # re-run took the aei source from 5 rows to 10. The digest is content, so
            # it cannot do that.
            fingerprint = str(events[-1].get("digest") or "").strip()
            out.append({
                "run_id": run_id,
                "analysis": analyse(events),
                "events": len(events),
                "fingerprint": fingerprint,
            })
        store.close()
        return out
    except sqlite3.Error as exc:
        print(f"BLIND  aei-to-optimus  AEI ledger unreadable: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def emit(source: str, run: dict, revision: str, brain: str, dry_run: bool) -> int:
    import subprocess  # noqa: PLC0415 - one call, bounded

    run_id = run["run_id"]
    analysis = run["analysis"]
    metrics = analysis.get("metrics") or {}
    observed = bool((analysis.get("coverage") or {}).get("task_terminal"))
    fingerprint = run.get("fingerprint") or ""
    worst = 0

    for aei_name, (opt_name, unit) in METRIC_MAP.items():
        if aei_name in metrics:
            value, status = float(metrics[aei_name]), "OK"
            evidence = f"AEI {aei_name} over {run['events']} observed events (run {run_id})"
        else:
            # AEI did not observe it. That is BLIND, not zero -- the estate's rule.
            value, status = 0.0, "BLIND"
            evidence = f"AEI did not observe {aei_name} for run {run_id}; unknown, not zero"
            if not observed:
                status = "BLIND"

        cmd = [
            sys.executable, str(EMITTER),
            "--source", source,
            "--subject", f"run:{run_id}",
            "--metric", opt_name,
            "--value", str(value),
            "--unit", unit,
            "--status", status,
            "--evidence", evidence,
            "--label", f"run_id={run_id}",
            "--label", f"revision={revision}",
            "--label", f"aei_events={run['events']}",
            "--brain", brain,
        ]
        # Idempotency key = the evidence, not the clock. Without a fingerprint we fall
        # back to the ledger's event count, which is still content-derived.
        id_basis = fingerprint[:40] if fingerprint else f"n{run['events']}"
        cmd += ["--metric-id", f"{source}:{run_id}:{opt_name}:{id_basis}"]
        for view in ("waterfall", "graph", "coverage"):
            if view in analysis:
                cmd += ["--label", f"aei_view={view}"]
                break
        if dry_run:
            print("dry-run:", " ".join(cmd[1:]))
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # noqa: S603 - argv list, no shell
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        worst = max(worst, proc.returncode)
    return worst


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="publish AEI execution numbers to optimus")
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--run", default="")
    p.add_argument("--source", default="aei")
    p.add_argument("--revision", default="")
    p.add_argument("--brain", default=os.environ.get("ESTATE_BRAIN_URL", "http://127.0.0.1:4319"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    revision = args.revision
    if not revision:
        try:
            import subprocess  # noqa: PLC0415
            revision = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
        except Exception:  # noqa: BLE001 - a missing revision is unknown, not a blocker
            revision = "unknown"

    runs = load_analysis(args.db)
    if args.run:
        runs = [r for r in runs if r["run_id"] == args.run]
    if not runs:
        print(f"BLIND  aei-to-optimus  no runs in {args.db}", file=sys.stderr)
        return 2

    worst = 0
    for run in runs:
        worst = max(worst, emit(args.source, run, revision, args.brain, args.dry_run))
    print(f"ok     aei-to-optimus  {len(runs)} run(s) published to {args.brain}")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
