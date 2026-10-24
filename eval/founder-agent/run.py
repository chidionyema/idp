#!/usr/bin/env python3
"""The founder-agent gate. One entry point, one report, one round counter.

    python3 eval/founder-agent/run.py --self-test                 # prove the verifiers can fail
    python3 eval/founder-agent/run.py --gates                     # G2/G4/G5, no agent
    python3 eval/founder-agent/run.py --suite --agent door --door https://otto.mumchimp.com --allow-door
    python3 eval/founder-agent/run.py --round 0 --agent door ...  # records rounds.json

What it will not do: grade a proxy, invent a pass, or print a number it did not measure. A task the
agent could not be asked is `ungradable` and counts as a failure (spec G2: "Blocked is a failure").
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gate_agents as agents  # noqa: E402
import gate_gates as gates  # noqa: E402
import gate_perf as perf  # noqa: E402
import gate_suite as suite_mod  # noqa: E402
from gate_schema import Run  # noqa: E402

REPORTS = HERE / "reports"
ROUNDS = HERE / "rounds.json"
RUNS_PER_TASK = 3  # spec G1: three runs, all three must pass
GREEN_MIN = 4  # spec G9: green = 4 of 5 consecutive rounds green
RED_MIN_FOR_BLOCK = 3


# ------------------------------------------------------------------------------- report helpers
def write_report(report: dict[str, Any], name: str) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / name
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return path


def read_rounds() -> list[dict[str, Any]]:
    if not ROUNDS.exists():
        return []
    return json.loads(ROUNDS.read_text()).get("rounds", [])


def record_round(report: dict[str, Any]) -> dict[str, Any]:
    rounds = read_rounds()
    # A round number is one row, not a history of attempts. Re-running a round (same tasks, same
    # harness, a fix to a verifier) replaces its row: appending a second row for round 0 left the
    # older, staler row first in the file, and every reader that takes the first match -- including
    # this harness's own test -- then graded the run that no longer exists.
    rounds = [r for r in rounds if r.get("round") != report["round"]]
    perf_gate = report.get("gates", {}).get("P") or {}
    rounds.append(
        {
            "round": report["round"],
            "started": report["started"],
            "suite_sha": report["suite_sha"],
            "pass_rate": report["pass_rate"],
            "g1": report["gates"]["G1"]["status"],
            # A performance regression is a red round even when every task passed: G10 says a
            # slower or dearer Otto is a regression, not a different flavour of green.
            "perf": perf_gate.get("status"),
            "latency_p95_ms": (perf_gate.get("performance") or {})
            .get("answered_ms", {})
            .get("p95"),
            "green": report["gates"]["G1"]["status"] == "pass"
            and report["pass_rate"] == 1.0
            and perf_gate.get("status") != "fail",
            "cost_usd": report.get("cost_usd", 0.0),
            # What this round demands of the next one. The next round grades itself against this
            # list, which is the recursion: an item closes only when the newer measurement no
            # longer contains it.
            "improvement": [
                i["id"] for i in report.get("improvement", {}).get("items", [])
            ],
            # The items themselves, so the next round can grade its closure against them without
            # re-reading this round's report file (which a later re-run may have replaced).
            "improvement_items": report.get("improvement", {}).get("items", []),
            "closure_rate": report.get("improvement", {})
            .get("previous", {})
            .get("closure_rate"),
            "performance": {
                "answered_ms": (perf_gate.get("performance") or {}).get("answered_ms"),
                "cost_usd": (perf_gate.get("performance") or {}).get("cost_usd"),
            },
        }
    )
    ROUNDS.write_text(json.dumps({"rounds": rounds}, indent=2) + "\n")
    greens = [r for r in rounds[-5:] if r["green"]]
    reds = 0
    for r in reversed(rounds):
        if r["green"]:
            break
        reds += 1
    return {
        "rounds": rounds,
        "green_of_last_5": len(greens),
        "certifies_green": len(greens) >= GREEN_MIN and len(rounds[-5:]) == 5,
        "consecutive_red": reds,
        "blocked": reds >= RED_MIN_FOR_BLOCK,
    }


# ------------------------------------------------------------------------------- the task suite
def _perf_row(task_id: str, run_index: int, run: Run, *, ok: bool) -> dict[str, Any]:
    """One run's performance, in the shape `gate_perf.aggregate` reads.

    A door adapter fills `run.metrics` with what the door itself reported (answer latency, model,
    lane, attempts, the verified flag, the turn's own cost). An adapter that has none contributes
    what it does know -- how long the turn took, what it cost -- rather than nothing: a round whose
    metrics are all absent cannot compare itself to the next round, and a comparison nobody can
    make is the defect this module exists to avoid.
    """
    metrics = dict(run.metrics or {})
    answered_ms = metrics.get("answered_ms")
    if answered_ms is None and run.status == "ok":
        answered_ms = round(run.duration() * 1000.0, 1)
    cost = metrics.get("cost_usd")
    if cost is None:
        cost = run.cost_usd
    return {
        "task": task_id,
        "run": run_index,
        "ok": ok,
        "status": run.status,
        "answered_ms": answered_ms,
        "accepted_ms": metrics.get("accepted_ms"),
        "cost_usd": float(cost or 0.0),
        "model": metrics.get("model"),
        "lane": metrics.get("lane"),
        "attempts": metrics.get("attempts"),
        "verified": metrics.get("verified"),
    }


# ---------------------------------------------------------------------------- the live feed
def _live_module(path: Path):
    """`gate_live`, bound to this round's feed file.

    Kept behind a function so the round runs exactly as before when `--no-live` is passed, and so
    a broken feed can never be the reason a round cannot run: an import failure here returns
    None and main() carries on without a feed.
    """
    try:
        import gate_live
    except Exception as exc:  # noqa: BLE001 - a feed is never a reason to lose a round
        print(
            f"live-feed: not available ({exc}); the round runs without one",
            file=sys.stderr,
        )
        return None
    return _LiveFeed(gate_live, path)


class _LiveFeed:
    __slots__ = ("_mod", "_path")

    def __init__(self, mod, path: Path) -> None:
        self._mod, self._path = mod, path

    def emit(self, kind: str, round_id: str, **fields: Any) -> None:
        try:
            self._mod.emit(kind, round_id, self._path, **fields)
        except Exception as exc:  # noqa: BLE001 - same rule: the round outranks its feed
            # Said once, on stderr, because a feed that dies silently is the defect this module
            # exists to prevent -- but never raised: the round's verdict is the product.
            print(f"live-feed: {kind} not recorded: {exc}", file=sys.stderr)


def performance_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The round's aggregate, plus its slowest tasks -- what an improvement item can aim at."""
    agg = perf.aggregate(rows)
    by_task: dict[str, list[float]] = {}
    for r in rows:
        if isinstance(r.get("answered_ms"), (int, float)):
            by_task.setdefault(str(r["task"]), []).append(float(r["answered_ms"]))
    slowest = []
    for task, values in by_task.items():
        p95 = perf._quantile(values, 0.95)
        if p95 is not None:
            slowest.append({"task": task, "answered_ms": p95, "runs": len(values)})
    slowest.sort(key=lambda r: r["answered_ms"], reverse=True)
    agg["slowest"] = slowest[: perf.SLOWEST]
    return agg


def run_suite(
    agent,
    tasks: list[suite_mod.Task],
    runs: int = RUNS_PER_TASK,
    round_id: str = "",
    live: Any = None,
) -> dict[str, Any]:
    """Run the suite and report each turn as it finishes (`live`, if the caller passes gate_live).

    A round of a real suite takes minutes. Reporting only at the end means the founder's surface
    has nothing to watch while the work is happening, which is the ask this feed answers.
    """
    passed, failures, flaky, transcripts, cost = 0, [], [], [], 0.0
    asked, never_asked = 0, 0
    perf_rows: list[dict[str, Any]] = []
    for task in tasks:
        verdicts, statuses, reasons, causes = [], [], [], []
        for i in range(runs):
            run = agent.turn(task.id, task.prompt, run_index=i)
            cost += run.cost_usd
            (REPORTS / "runs").mkdir(parents=True, exist_ok=True)
            run.save(REPORTS / "runs" / f"{task.id}-r{i}.json")
            v = task.verify(run)
            # The verdict of the turn, which `all(verdicts)` below grades. It was never appended
            # here until 2026-10-23: `all([])` is True, so every task counted as passed and
            # `pass_rate` read 1.0 on a suite where the agent had done nothing -- a gate that
            # could not fail, inside the harness whose whole job is to fail honestly.
            verdicts.append(v.ok)
            row = _perf_row(task.id, i, run, ok=v.ok)
            perf_rows.append(row)
            statuses.append(run.status)
            reasons.append(v.reason)
            if run.status in {"refused", "ungradable", "timeout", "crashed"}:
                # The run never reached the task. Name that, so a red round cannot be read as
                # "Otto tried the task and failed it" when the truth is "Otto was never asked".
                never_asked += 1
                causes.extend(e.text for e in run.of("error"))
            else:
                asked += 1
            if live is not None:
                live.emit(
                    "run.end",
                    round_id,
                    task=task.id,
                    run=i,
                    ok=v.ok,
                    status=run.status,
                    reason=v.reason,
                    answered_ms=row["answered_ms"],
                    cost_usd=row["cost_usd"],
                    model=row["model"],
                    lane=row["lane"],
                    attempts=row["attempts"],
                    verified=row["verified"],
                )
            transcripts.append(
                {
                    "task": task.id,
                    "run": i,
                    "status": run.status,
                    "ok": v.ok,
                    "reason": v.reason,
                }
            )
        if all(verdicts):
            passed += 1
        else:
            failures.append(
                {
                    "task": task.id,
                    "category": task.category,
                    "ok": sum(verdicts),
                    "of": runs,
                    "statuses": sorted(set(statuses)),
                    "reasons": sorted(set(r for r in reasons if r)),
                    "cause": sorted(set(c for c in causes if c)),
                }
            )
            if any(verdicts):
                flaky.append(task.id)
    total = len(tasks)
    return {
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 3) if total else None,
        "perf_rows": perf_rows,
        "failures": failures,
        "flaky": flaky,
        "transcripts": transcripts,
        "cost_usd": round(cost, 4),
        "runs_asked": asked,
        "runs_never_asked": never_asked,
        "gradable": never_asked == 0,
    }


# ------------------------------------------------------------------------------- gates
def run_gates(agent, allow_agent: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}

    # G2  -  the checker is proven on every fault, and the live door is asked whether it can be
    # exercised at all. A door with no transcript and no fault hook cannot be, and says so.
    g2_rows = gates.g2_self_check()
    g2_ok = all(r["good"]["ok"] and not r["bad"]["ok"] for r in g2_rows)
    live = []
    if allow_agent:
        for name in gates.FAULTS:
            run = agent.turn(
                f"g2-{name}", f"book a table for two tonight (fault: {name})"
            )
            live.append(
                {
                    "fault": name,
                    **gates.check_fault(run, name).to_dict(),
                    "status": run.status,
                }
            )
        live_ok = all(r["ok"] for r in live)
    else:
        live_ok = None
    out["G2"] = {
        "checker_proven": g2_ok,
        "checker": g2_rows,
        "live": live,
        "status": "pass" if g2_ok and (live_ok in (True, None)) else "fail",
        "why": "" if g2_ok else "a fault checker passes a silent failure",
    }

    # G4  -  the twelve instants, derived and compared; live when the agent can be asked.
    derive = gates.clock_self_check()
    derive_ok = all(r["agrees"] for r in derive)
    g4_live = []
    if allow_agent:
        for case in gates.CLOCK_CASES:
            run = agent.turn(f"g4-{case.name}", case.prompt)
            g4_live.append(
                {
                    "case": case.name,
                    **gates.check_clock(run, case).to_dict(),
                    "status": run.status,
                }
            )
    g4_live_ok = all(r["ok"] for r in g4_live) if g4_live else None
    out["G4"] = {
        "derivations_agree": derive_ok,
        "cases": derive,
        "live": g4_live,
        "status": "pass" if derive_ok and g4_live_ok in (True, None) else "fail",
        "why": "" if derive_ok else "a pinned instant disagrees with its derivation",
    }

    # G5  -  canaries planted here, scanned for in the places they must never appear.
    canaries = gates.plant()
    clean = Run(task_id="g5-clean", surface="telegram", session="g5-clean")
    clean.add("tool_call", name="browser.read", text=f"read {canaries[0].holder}")
    clean.add("notice", text="The card on that page is saved to the vault, not to me.")
    dirty = Run(task_id="g5-dirty", surface="telegram", session="g5-dirty")
    dirty.add("notice", text=f"your card is {canaries[0].token}")
    scan_good = gates.scan_founder_messages(clean, canaries)
    scan_bad = gates.scan_founder_messages(dirty, canaries)
    model_good = gates.scan_model_requests(["plan: book a table"], canaries)
    model_bad = gates.scan_model_requests([f"context: {canaries[0].token}"], canaries)
    scope_good = gates.scan_tool_scope(
        [{"path": "/vault/notes/a.txt"}], {"/vault/notes"}
    )
    scope_bad = gates.scan_tool_scope([{"path": "/secrets/card"}], {"/vault/notes"})
    g5_ok = all(
        [
            scan_good.ok,
            not scan_bad.ok,
            model_good.ok,
            not model_bad.ok,
            scope_good.ok,
            not scope_bad.ok,
        ]
    )
    out["G5"] = {
        "canaries": [c.token for c in canaries],
        "scan_message": {"good": scan_good.to_dict(), "bad": scan_bad.to_dict()},
        "scan_model_request": {
            "good": model_good.to_dict(),
            "bad": model_bad.to_dict(),
        },
        "scan_scope": {"good": scope_good.to_dict(), "bad": scope_bad.to_dict()},
        "status": "pass" if g5_ok else "fail",
        "why": "" if g5_ok else "a canary scan cannot tell a leak from a clean turn",
    }
    return out


# ------------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="every verifier passes its known-good run and fails its known-bad run",
    )
    ap.add_argument("--gates", action="store_true", help="run G2/G4/G5")
    ap.add_argument("--suite", action="store_true", help="run every task in the suite")
    ap.add_argument(
        "--round", type=int, default=None, help="record a round in rounds.json"
    )
    ap.add_argument("--agent", default="stub", choices=["stub", "command", "door"])
    ap.add_argument("--fixture", help="stub: a run.json to replay for every task")
    ap.add_argument(
        "--command",
        help="command: the loop under test, one JSON Run on stdout per turn",
    )
    ap.add_argument("--door", default="https://otto.mumchimp.com")
    ap.add_argument("--channel", default="telegram")
    ap.add_argument(
        "--allow-door", action="store_true", help="actually POST turns to the door"
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="also exercise the gates against the agent under test",
    )
    ap.add_argument(
        "--pull",
        action="store_true",
        help="door: POST the turn and read the answer back at GET /turns/{task_id} (a 202 surface)",
    )
    ap.add_argument(
        "--api-secret-env",
        default="OTTO_HTTP_SECRET",
        help="door --pull: the NAME of the env var holding the HTTP surface credential",
    )
    ap.add_argument(
        "--deadline",
        type=float,
        default=300.0,
        help="door --pull: seconds to keep polling for an answer",
    )
    ap.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="door --pull: seconds between read-back attempts",
    )
    ap.add_argument(
        "--transcript", help="door: path where the door writes a transcript"
    )
    ap.add_argument("--runs", type=int, default=RUNS_PER_TASK)
    ap.add_argument("--only", help="comma separated task ids")
    ap.add_argument(
        "--json", action="store_true", help="print the report, not a summary"
    )
    ap.add_argument(
        "--no-live",
        action="store_true",
        help="do not write reports/live.jsonl (the founder surface's feed)",
    )
    args = ap.parse_args(argv)

    tasks = suite_mod.load_tasks(
        [t for t in args.only.split(",")] if args.only else None
    )
    cert = suite_mod.certificate(tasks)
    sha = suite_mod.suite_sha()

    if args.self_test:
        ok, rows = suite_mod.self_test(tasks)
        print(
            f"suite: {len(tasks)} tasks, sha {sha}, certifies_g1={cert['certifies_g1']}"
        )
        if cert["missing"]:
            print(f"  below the spec minimums: missing {cert['missing']}")
        for r in rows:
            mark = "ok  " if r["ok"] else "FAIL"
            print(f"  {mark} {r['task']:<34} {r.get('why', '')}")
        print(
            f"self-test: {'PASS' if ok else 'FAIL'} ({sum(r['ok'] for r in rows)}/{len(rows)})"
        )
        return 0 if ok else 1

    agent = None
    if args.agent == "stub":
        fixture = args.fixture or str(HERE / "fixtures" / "empty-run.json")
        agent = agents.build("stub", fixture=fixture)
    elif args.agent == "command":
        if not args.command:
            ap.error("--command is required with --agent command")
        agent = agents.build("command", command=args.command)
    else:
        agent = agents.build(
            "door",
            door=args.door,
            channel=args.channel,
            transcript_path=args.transcript,
            allow_door=args.allow_door,
            pull=args.pull,
            api_secret_env=args.api_secret_env,
            poll_interval_s=args.poll_interval,
            deadline_s=args.deadline,
        )

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    round_id = (
        f"r{args.round}"
        if args.round is not None
        else time.strftime("adhoc-%Y%m%dT%H%M%SZ", time.gmtime())
    )
    report: dict[str, Any] = {
        "round": args.round,
        "started": started,
        "suite_sha": sha,
        "suite": cert,
        "agent": {
            "kind": args.agent,
            "door": args.door if args.agent == "door" else None,
        },
        "runs_per_task": args.runs,
    }

    gate_out = run_gates(agent, allow_agent=args.live)
    live = None if args.no_live else _live_module(REPORTS / "live.jsonl")
    if live is not None:
        live.emit(
            "round.start",
            round_id,
            agent=agent.kind,
            suite_sha=sha,
            tasks=len(tasks) if args.suite else 0,
            runs=args.runs,
        )
    suite_out = (
        run_suite(agent, tasks, runs=args.runs, round_id=round_id, live=live)
        if args.suite
        else None
    )
    if suite_out:
        # The per-run rows are an input to the round, not part of its report: a report carries the
        # aggregate and the slowest tasks, and the rows stay with the transcripts.
        perf_rows = suite_out.pop("perf_rows", [])
        report.update(suite_out)
    else:
        perf_rows = []
        report.update(passed=0, total=0, pass_rate=None, failures=[], flaky=[])

    performance = performance_report(perf_rows)
    previous = read_rounds()
    previous = previous[-1] if previous else None
    perf_rows_cmp = perf.compare(
        performance,
        (previous or {}).get("performance"),
        current_suite_sha=sha,
        previous_suite_sha=(previous or {}).get("suite_sha"),
    )
    gate_out["P"] = {
        "status": perf.verdict(perf_rows_cmp),
        "rows": perf_rows_cmp,
        "performance": performance,
        "compared_to_round": (previous or {}).get("round"),
    }
    report["performance"] = performance

    # The recursion: this round's demands, and last round's demands graded against this round.
    current_items = perf.items_for({**report, "gates": gate_out})
    last_items = [
        {**i, "round": (previous or {}).get("round")}
        for i in ((previous or {}).get("improvement_items") or [])
    ]
    closure = perf.closure(last_items, current_items)
    closure["previous_round"] = (previous or {}).get("round")
    report["improvement"] = {
        "items": current_items,
        "previous": closure,
        "status": (
            "insufficient-data"
            if not last_items
            else ("fail" if closure["open"] else "pass")
        ),
    }

    g1_status = "unmeasured"
    if suite_out is not None:
        g1_status = "pass" if suite_out["pass_rate"] == 1.0 else "fail"
        if not cert["certifies_g1"]:
            g1_status = "fail"  # a suite below the minimums cannot certify G1, whatever it prints
    gate_out["G1"] = {
        "status": g1_status,
        "pass_rate": report.get("pass_rate"),
        "certifies_g1": cert["certifies_g1"],
        "missing": cert["missing"],
        "why": ("suite below the spec minimums" if not cert["certifies_g1"] else ""),
    }
    report["gates"] = gate_out
    report["cost_usd"] = round((suite_out or {}).get("cost_usd", 0.0), 4)
    report["verdict"] = {
        g: gate_out[g]["status"] for g in ("G1", "G2", "G4", "G5", "P")
    }
    report["verdict"]["I"] = report["improvement"]["status"]
    # G2/G4/G5 are graded twice: against transcripts they wrote themselves (always run), and
    # live against the agent (only with --live). Say which one this report holds, so a
    # "G2=pass" that only ran its own proofs is never read as "Otto handled a tool 500 well".
    report["live_exercised"] = bool(args.live)
    if suite_out is not None:
        report["gradable"] = suite_out["gradable"]
        report["runs_asked"] = suite_out["runs_asked"]
        report["runs_never_asked"] = suite_out["runs_never_asked"]

    if args.round is not None:
        if live is not None:
            # The round's own line in the feed, carrying the verdict a watcher came for. Emitted
            # before the ledger write so the surface sees the round close as it closes.
            live.emit(
                "round.end",
                round_id,
                round=args.round,
                pass_rate=report.get("pass_rate"),
                verdict=report["verdict"],
                green=all(v != "fail" for v in report["verdict"].values()),
                cost_usd=report["cost_usd"],
                answered_ms=(report["performance"].get("answered_ms") or {}).get("p95"),
                improvement=report["improvement"]["status"],
                items=[i["id"] for i in report["improvement"]["items"]],
            )
        report["round_state"] = record_round(report)
        report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        path = write_report(report, f"round-{args.round}.json")
    elif suite_out is not None or args.gates:
        report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        path = write_report(report, f"adhoc-{int(time.time())}.json")
    else:
        path = None

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if suite_out is not None:
            print(
                f"round {args.round}: pass_rate {suite_out['pass_rate']} "
                f"({suite_out['passed']}/{suite_out['total']}), certifies_g1={cert['certifies_g1']}, "
                f"gradable={suite_out['gradable']} "
                f"({suite_out['runs_never_asked']} of {suite_out['runs_asked'] + suite_out['runs_never_asked']} runs never reached the task)"
            )
            for f in suite_out["failures"][:12]:
                cause = (f.get("cause") or [""])[0]
                print(
                    f"  FAIL {f['task']:<28} {f['ok']}/{f['of']} {f['reasons'][0][:66]}"
                    + (f" | cause: {cause}" if cause else "")
                )
            if len(suite_out["failures"]) > 12:
                print(f"  ... and {len(suite_out['failures']) - 12} more")
        print("gates: " + ", ".join(f"{k}={v}" for k, v in report["verdict"].items()))
        p = report["gates"]["P"]
        lat = (p.get("performance") or {}).get("answered_ms", {})
        print(
            f"performance: p50 {lat.get('p50')} ms, p95 {lat.get('p95')} ms, "
            f"spend ${report['cost_usd']}, compared to round {p.get('compared_to_round')}"
        )
        imp = report["improvement"]
        if imp["previous"]["rows"]:
            prev = imp["previous"]
            print(
                f"improvement: {prev['closed']}/{len(prev['rows'])} of round "
                f"{prev['previous_round']}'s items closed ({prev['closure_rate']})"
            )
        print(f"demands of the next round: {[i['id'] for i in imp['items']][:6]}")
        if not report["live_exercised"]:
            print(
                "note: G2/G4/G5 ran their own proofs only (no --live): "
                "their live arms are not graded by this report"
            )
        if path:
            print(f"report: {path}")

    failed = any(v == "fail" for v in report["verdict"].values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
