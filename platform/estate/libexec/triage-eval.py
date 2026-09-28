#!/usr/bin/env python3
"""triage-eval -- score net-triage against a labelled scenario corpus, offline.

usage: triage-eval.py [corpus-dir] [--json]     (default corpus: <estate>/eval/net-crossnode)

Runs the real hypotheses-race.py and triage-verdict.py, unchanged, once per scenario, in a
throwaway HOME with PATH limited to a stub kubectl that returns the scenario's recorded API
state. Nothing reaches the cluster, Jev is never called (it escalates, deterministically), and
eval runs never land in the real ~/.estate/logs evidence log, which is training data.

Scores per scenario, against ground truth:
  diagnosis   top supported hypothesis is a true cause; with no true cause, nothing supported
  recall      true causes the race supported / true causes
  false+      supported hypotheses that are not true causes
  err-as-ev   hypotheses whose evidence was unavailable that came back falsified or supported
  verdict     the fix proposed (or abstention) is the right one; a fix for a false cause is harmful
Exit 1 when any scenario fails: a harness that cannot fail is not a gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ESTATE = Path(__file__).resolve().parents[1]
RACE = ESTATE / "libexec" / "hypotheses-race.py"
VERDICT = ESTATE / "libexec" / "triage-verdict.py"
NODE = "================ node"
STUB = """#!/bin/sh
[ "$EVAL_GNP" = UNREACHABLE ] && { echo "Unable to connect to the server: i/o timeout" >&2; exit 1; }
printf '%s' "$EVAL_GNP"
"""


def build_capture(corpus: Path, sc: dict, dest: Path) -> Path | None:
    if not sc.get("capture"):
        return None
    lines = (corpus / sc["capture"]).read_text().splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith(NODE)] + [len(lines)]
    blocks = [lines[: starts[0]]] + [
        lines[starts[i] : starts[i + 1]] for i in range(len(starts) - 1)
    ]
    for op in sc.get("ops", []):
        b = blocks[op["node"] + 1]
        if "replace_section" in op:
            b[1:] = [op["replace_section"]]
        if "sub" in op:
            old, new = op["sub"]
            hit = next((i for i, l in enumerate(b) if old in l), None)
            if hit is None:
                sys.exit(
                    f"triage-eval: scenario {sc['id']}: {old!r} not in node {op['node']} of {sc['capture']}"
                )
            b[hit] = b[hit].replace(old, new, 1)
        if "append" in op:
            b.append(op["append"])
    dest.write_text("\n".join(l for blk in blocks for l in blk) + "\n")
    return dest


def run(sc: dict, corpus: Path, spec: Path, fixable: set) -> dict:
    with tempfile.TemporaryDirectory(prefix="triage-eval.") as tmp:
        t = Path(tmp)
        (t / "bin").mkdir()
        (t / "bin" / "kubectl").write_text(STUB)
        (t / "bin" / "kubectl").chmod(0o755)
        nf = build_capture(corpus, sc, t / "capture") or (t / "no-capture")
        env = {
            "HOME": tmp,
            "PATH": f"{t / 'bin'}:/usr/bin:/bin",
            "NF": str(nf),
            "EVAL_GNP": sc.get("gnp", ""),
        }
        t0 = time.time()
        race = subprocess.run(
            [sys.executable, str(RACE), str(spec)],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        race_ms = int((time.time() - t0) * 1000)
        res = json.loads(race.stdout)
        (t / "race.json").write_text(race.stdout)
        v = subprocess.run(
            [sys.executable, str(VERDICT), str(spec), str(t / "race.json")],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
    verdict = next(
        (l for l in v.stdout.splitlines() if l.startswith("VERDICT")),
        "VERDICT <missing>",
    )
    falsified = {r["id"] for r in res["results"] if r["falsified"]}
    unknown_ids = {r["id"] for r in res["results"] if r.get("unknown")}
    supported = [
        h for h in res["ranked"] if h not in falsified and h not in unknown_ids
    ]
    truth, unknown = set(sc["truth"]), set(sc.get("unknown", []))

    diagnosis = (supported[0] in truth) if truth else not supported
    recall = len(truth & set(supported)) / len(truth) if truth else None
    false_pos = [h for h in supported if h not in truth]
    # evidence was unavailable: only an explicit "unknown" result is right; falsified or supported is a guess
    err_as_ev = sorted(
        r["id"] for r in res["results"] if r["id"] in unknown and not r.get("unknown")
    )
    proposed = (
        next(
            (f for f in fixable if f"estate-execute {fixable[f]} " in verdict + " "),
            None,
        )
        if "VERDICT none" not in verdict
        else None
    )
    right_fix = [h for h in supported if h in truth and h in fixable]
    if proposed is None:
        verdict_ok, harmful = not right_fix, False
    else:
        verdict_ok, harmful = proposed in truth, proposed not in truth
    ok = (
        diagnosis
        and verdict_ok
        and not harmful
        and not err_as_ev
        and (recall in (None, 1.0))
    )
    return {
        "id": sc["id"],
        "ok": ok,
        "diagnosis": diagnosis,
        "recall": recall,
        "false_pos": false_pos,
        "err_as_evidence": err_as_ev,
        "proposed_fix_for": proposed,
        "verdict_ok": verdict_ok,
        "harmful": harmful,
        "top": supported[0] if supported else None,
        "posterior_top": round(res["posteriors"][supported[0]], 3)
        if supported
        else None,
        "probes": len(res["results"]),
        "race_ms": race_ms,
        "verdict": verdict,
        "truth": sorted(truth),
        "truth_status": sc.get("truth_status", ""),
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    corpus = Path(args[0]) if args else ESTATE / "eval" / "net-crossnode"
    spec = ESTATE / "hypotheses" / f"{corpus.name}.json"
    fixable = {
        h["id"]: h["fix"]
        for h in json.loads(spec.read_text())["hypotheses"]
        if h.get("fix")
    }
    rows = [
        run(sc, corpus, spec, fixable)
        for sc in json.loads((corpus / "scenarios.json").read_text())["scenarios"]
    ]
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(
                f"{'PASS' if r['ok'] else 'FAIL'}  {r['id']:26} top={r['top'] or '-':24} "
                f"diag={'ok' if r['diagnosis'] else 'WRONG'} recall={r['recall'] if r['recall'] is not None else '-'} "
                f"false+={','.join(r['false_pos']) or '-'} err-as-ev={','.join(r['err_as_evidence']) or '-'} "
                f"harmful={'YES' if r['harmful'] else 'no'} {r['race_ms']}ms"
            )
            print(f"      {r['verdict'][:150]}")
    n = len(rows)
    agg = {
        k: sum(1 for r in rows if r[k])
        for k in ("ok", "diagnosis", "verdict_ok", "harmful")
    }
    print(
        f"\nscenarios {n}  pass {agg['ok']}/{n}  diagnosis {agg['diagnosis']}/{n}  "
        f"verdict {agg['verdict_ok']}/{n}  harmful proposals {agg['harmful']}  "
        f"probes/scenario {rows[0]['probes'] if rows else 0} (oracle 1)"
    )
    sys.exit(0 if agg["ok"] == n else 1)


if __name__ == "__main__":
    main()
