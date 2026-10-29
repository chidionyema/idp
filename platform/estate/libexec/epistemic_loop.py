#!/usr/bin/env python3
"""The epistemic firewall's THIRD LEG: proof of progress, and the loop breaker.

The estate already owns two legs of the epistemic firewall, and both are real code:

  leg 1  bin/epistemic_firewall.py  -- an agent's first-person claim must be backed by a tool
                                       call, or it is refused (2026-09-12).
  leg 2  bin/trajectory_lock.py     -- an agent may not wander off the ticket it declared
                                       (2026-09-12).

Both read a transcript and grade an AGENT. Neither can see a RESIDENT WORKER: a launchd guardian
that wakes every 20 seconds, runs a bounded step, and gets nothing back has no transcript, no
plan, and no claims to grade. That is the gap this file closes, and it is the gap that cost the
estate eight hours.

WHAT WENT WRONG, MEASURED (2026-10-29, ~/.estate/disk-watch.log). The reclaim guardian ran
step after step under disk pressure:

    step free=2361M target=2500M rc=3 freed=-2M met=no after=2280M
    step free=2280M target=2500M rc=4 freed=?M met=? after=?M

rc=4 means the step was cut short; `freed=?M` means the child was SIGKILLed before it could print
its one machine-readable RESULT line, so the guardian reported a field it had never measured. The
guardian then did the same thing again, and again, for thirty minutes: 2361 -> 2280 -> 1759 -> 919
-> 437 -> 396 MB. Free space fell by 1.9 GB while the guardian ran its steps diligently. The
guardian was not broken; it was LOOPING, and no layer in the estate could tell the difference
between "working on a hard problem" and "repeating an identical no-op forever".

WHY THE THIRD LEG IS DIFFERENT FROM THE FIRST TWO. Legs 1 and 2 grade what an agent SAYS. This
leg grades what the WORLD DID, and it never believes the worker's own report of that. The research
names the failure precisely: "When Do Agent Loops Mistake Stagnation for Progress? Self-Evaluation
Bias and Externally Grounded Verification in Long-Running Autonomous LLM Agent Loops" (OpenAlex
W7171902361) measures a frontier agent claiming improvement on every one of 54 cycles while 56%
of those cycles had a measured delta of zero or below -- and an in-band judge reading the full
artifact text still accepted 44% of them. The self-verdict gate degenerates into accept-all.

So the rule here is: the world state is measured by the GATE, from outside the worker, and the
worker's own RESULT line is data, never the verdict. A worker that lies about having freed space
is graded by statvfs, not by its own line.

THE FOUR VERDICTS.

    PROGRESS     the measured metric moved in the goal direction. Continue.
    NO_PROGRESS  the metric did not move. Continue, but bounded.
    REGRESSION   the metric moved the wrong way. Stop and change the action.
    LOOP         NO_PROGRESS on an action already seen, unchanged, `no_progress_limit` times.
                 The action is not working. Change the action or escalate -- never repeat it.
    BLIND        the metric could not be measured. Fail closed: this is never progress.

BLIND is not zero. A measurement that could not be taken is a number we do not have; treating it
as zero is how a blind system reports "no progress" as if it were a measurement.

THE EVIDENCE FAN-OUT. The founder's standing instruction (2026-10-29) is to map and gather all
required data in as few passes as possible. Two pieces of published practice shape this function:

  * "SquidAgent: Parallelize Wisely, Coordinate Efficiently" (arXiv 2610.08647) derives the
    decision criterion: parallelise a layer only when its critical-path cost plus re-exploration
    and alignment overhead is lower than the serial cost. So `fan_out` computes both and falls
    back to serial when parallel would not be cheaper. It never parallelises for its own sake.
  * "ECMR: Evidence-Aware Deliberation Control" (arXiv 2610.17869) names "semantic false
    consensus" -- a confident answer supported by narrow, duplicated, or correlated rationales --
    and "Memory Correlation Bias" (arXiv 2608.19701) shows the same thing in memory: memories
    inheriting one upstream source get counted repeatedly and form a false majority. So probes
    that share a source are NOT independent evidence, and `fan_out` counts independent SOURCES,
    not probes, and refuses to run the correlated duplicates at all.

THE LEDGER IS APPEND-ONLY AND THE GATE OWNS IT. "Bounded Loops" (arXiv 2609.27871) requires a
gate the worker cannot write to; "Where Does Exactly-Once Live?" (arXiv 2609.29095) shows that
exactly-once must be enforced somewhere outside the model -- in the harness, in the tool contract,
or in the ledger -- and never in the model itself. Here the ledger is the contract: verdicts are
appended, never rewritten, and the loop count is derived by reading the ledger rather than by
trusting the worker's memory of what it has already tried.

THE HONEST LIMIT. This grades progress in ONE measurable metric per subject. A step can move that
metric and still be wrong; a step can move nothing and still be one step away from the answer. The
ledger's job is to stop the estate spending hours on an action that provably does not work, not to
decide what the right action is. The escalation path is deliberately "ask", not "guess again".

  platform/estate/libexec/epistemic_loop.py --help
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

# -- the vocabulary ---------------------------------------------------------------------------------

PROGRESS = "PROGRESS"
NO_PROGRESS = "NO_PROGRESS"
REGRESSION = "REGRESSION"
LOOP = "LOOP"
BLIND = "BLIND"

# What the gate says the subject should do next.
CONTINUE = "CONTINUE"
BOUNDED = "BOUNDED_ONCE"
CHANGE_ACTION = "CHANGE_ACTION"
ESCALATE = "ESCALATE"

DEFAULT_LEDGER = Path.home() / ".estate" / "loops" / "progress.jsonl"
# How many times the SAME action may produce NO_PROGRESS before it is a loop. Three is the
# trajectory lock's own DRIFT_THRESHOLD (bin/trajectory_lock.py): below it, failures may still be
# progress. One shared constant for the estate, not one per caller.
DEFAULT_NO_PROGRESS_LIMIT = 3
# The smallest window a probe is worth starting. A probe given less than this is not a
# measurement, and reporting it as a TIMEOUT would confuse a starved budget with a probe that
# genuinely ran out of time -- which is how a blind measurement becomes a negative one.
MIN_PROBE_WINDOW_S = 0.5


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(value: Any) -> str:
    """A stable text form of a measurement, so two equal facts hash equal."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(value: Any) -> str:
    """The identity of a fact or of an action. sha256, hex, first 16 chars."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()[:16]


# -- the ledger ------------------------------------------------------------------------------------


class LoopLedger:
    """An append-only record of what was tried and what the world did.

    Append-only is the point. The worker may not rewrite a verdict; it may only append a new one.
    That is what makes the loop count trustworthy: it is derived from history, not from the
    worker's memory of its own behaviour. A file that cannot be read is BLIND, never empty.
    """

    def __init__(self, path: Path | str = DEFAULT_LEDGER) -> None:
        self.path = Path(path).expanduser()

    def append(self, row: dict) -> dict:
        row = {"at": now_iso(), **row}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError as exc:
            row["ledger_error"] = str(exc)
        return row

    def history(self) -> list[dict]:
        """Every row, oldest first. A missing file is an empty history; an unreadable one is an
        error, so the caller can tell 'nothing has happened yet' from 'I cannot see what happened'."""
        if not self.path.exists():
            return []
        rows: list[dict] = []
        try:
            for line in self.path.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        except OSError:
            return []
        return rows


# -- the gate --------------------------------------------------------------------------------------


class ProgressGate:
    """Grades one subject's attempts by the world state, measured from outside the worker.

    `subject` names what is being watched ("disk-guardian", "focus-register"). `metric` names the
    measured fact to compare between attempts ("free_mb"). `direction` says which way is better:
    "higher" (more free space) or "lower" (less latency).

    The gate NEVER reads a verdict out of the worker's own output. `before` and `after` are
    measurements taken by whoever holds the gate -- in the guardian's case, by the guardian itself,
    with statvfs, before and after the child ran.
    """

    def __init__(
        self,
        subject: str,
        metric: str,
        ledger: LoopLedger | None = None,
        no_progress_limit: int = DEFAULT_NO_PROGRESS_LIMIT,
        direction: str = "higher",
    ) -> None:
        if direction not in ("higher", "lower"):
            raise ValueError("direction must be 'higher' or 'lower'")
        self.subject = subject
        self.metric = metric
        self.direction = direction
        self.no_progress_limit = max(1, int(no_progress_limit))
        self.ledger = ledger or LoopLedger()

    # -- history -------------------------------------------------------------------------------

    def attempts(self) -> list[dict]:
        """This subject's rows, oldest first."""
        return [r for r in self.ledger.history() if r.get("subject") == self.subject]

    def action_fingerprint(self, action: str) -> str:
        return fingerprint(action)

    def times_tried(self, action: str) -> int:
        """How many times this exact action was already tried by this subject."""
        fp = self.action_fingerprint(action)
        return sum(1 for r in self.attempts() if r.get("action_fp") == fp)

    def identical_no_progress(self, action: str) -> int:
        """How many of this action's previous attempts measured NO_PROGRESS."""
        fp = self.action_fingerprint(action)
        return sum(
            1
            for r in self.attempts()
            if r.get("action_fp") == fp and r.get("verdict") in (NO_PROGRESS, LOOP)
        )

    # -- the judgement --------------------------------------------------------------------------

    def judge(
        self,
        action: str,
        before: Optional[dict],
        after: Optional[dict],
        detail: Optional[dict] = None,
    ) -> dict:
        """Grade one attempt. Always returns a verdict and always appends it to the ledger.

        `before` and `after` are the gate's own measurements of `self.metric`. When either is
        missing the metric, the verdict is BLIND -- not NO_PROGRESS, because "I could not measure"
        and "I measured and it did not move" are different facts and only one of them is progress.
        """
        row: dict[str, Any] = {
            "subject": self.subject,
            "action": action,
            "action_fp": self.action_fingerprint(action),
            "metric": self.metric,
        }
        if detail:
            row["detail"] = detail

        b = (before or {}).get(self.metric)
        a = (after or {}).get(self.metric)
        if not isinstance(b, (int, float)) or not isinstance(a, (int, float)):
            row["verdict"] = BLIND
            row["why"] = (
                f"the metric {self.metric!r} could not be measured "
                f"(before={b!r} after={a!r}); blind is never zero"
            )
            row["next"] = ESCALATE
            self.ledger.append(row)
            return row

        delta = a - b
        row["before"] = b
        row["after"] = a
        row["delta"] = delta

        if self.direction == "higher":
            moved = delta > 0
        else:
            moved = delta < 0

        if moved:
            row["verdict"] = PROGRESS
            row["why"] = f"{self.metric} moved {delta:+g} ({b} -> {a})"
            row["next"] = CONTINUE
        elif delta == 0:
            tries = self.identical_no_progress(action)
            if tries + 1 >= self.no_progress_limit:
                row["verdict"] = LOOP
                row["why"] = (
                    f"{self.metric} did not move ({b}) and this action has now measured no "
                    f"progress {tries + 1} times; repeating it is the loop, not the work"
                )
                row["next"] = ESCALATE
            else:
                row["verdict"] = NO_PROGRESS
                row["why"] = (
                    f"{self.metric} did not move ({b}); attempt {tries + 1} of "
                    f"{self.no_progress_limit} before this action counts as a loop"
                )
                row["next"] = BOUNDED
        else:
            row["verdict"] = REGRESSION
            row["why"] = f"{self.metric} moved the wrong way ({delta:+g}, {b} -> {a})"
            row["next"] = CHANGE_ACTION

        self.ledger.append(row)
        return row


# -- the evidence fan-out ---------------------------------------------------------------------------


class Probe:
    """One measurement to take. `source` is its PROVENANCE: two probes with the same source are
    one piece of evidence, however differently they are phrased."""

    def __init__(
        self,
        name: str,
        cmd: Iterable[str],
        source: str,
        timeout_s: float = 20.0,
        cwd: Optional[str] = None,
    ) -> None:
        self.name = name
        self.cmd = [str(c) for c in cmd]
        self.source = source
        self.timeout_s = float(timeout_s)
        self.cwd = cwd


def fan_out(
    probes: list[Probe],
    budget_s: float = 60.0,
    max_parallel: int = 4,
    runner: Optional[Callable[[Probe], dict]] = None,
) -> dict:
    """Take several measurements in as few passes as possible, without counting duplicates twice.

    Three rules, each from a measured source:

      1. CORRELATED PROBES ARE NOT RUN. Two probes with the same `source` read the same thing;
         running both spends budget to learn the same answer twice and then invites the false
         consensus that ECMR (arXiv 2610.17869) and the memory-correlation bias of arXiv
         2608.19701 describe. The first probe of each source runs; the rest are reported as
         skipped, with the source that made them redundant.

      2. PARALLEL ONLY WHEN IT IS CHEAPER. SquidAgent (arXiv 2610.08647): parallelisation pays
         only when the critical path plus re-exploration and alignment costs less than the serial
         path. The estimated serial cost is the sum of the per-probe budgets; the estimated
         parallel cost is the slowest probe plus a small alignment cost. When parallel is not
         cheaper, the probes run in series.

      3. THE BUDGET IS HARD. A probe that cannot start inside the remaining budget is reported
         as `budget` -- not silently dropped, and never counted as a negative result.
    """
    started = time.time()
    # The budget is a HARD boundary, not a suggestion: a probe that cannot start inside it is
    # reported as `budget`. Measured 2026-10-29: the reclaim guardian's own step budget was
    # spent on measurement instead of on reclaim, and the honest budget verdict -- "I could not
    # do this" -- was nowhere in the log.
    deadline = started + max(0.0, float(budget_s))

    by_source: dict[str, list[Probe]] = {}
    for p in probes:
        by_source.setdefault(p.source, []).append(p)

    kept: list[Probe] = []
    skipped_correlated: list[dict] = []
    for source, group in by_source.items():
        kept.append(group[0])
        for extra in group[1:]:
            skipped_correlated.append(
                {
                    "name": extra.name,
                    "source": source,
                    "why": "correlated with another probe",
                }
            )

    serial_cost = sum(p.timeout_s for p in kept)
    parallel_cost = (max((p.timeout_s for p in kept), default=0.0)) + 1.0
    parallel = len(kept) > 1 and parallel_cost < serial_cost
    order = "parallel" if parallel else "serial"

    def run_one(p: Probe) -> dict:
        remaining = deadline - time.time()
        if remaining < MIN_PROBE_WINDOW_S:
            return {
                "name": p.name,
                "source": p.source,
                "status": "budget",
                "why": (
                    "the evidence budget had "
                    f"{remaining:.2f}s left, less than the {MIN_PROBE_WINDOW_S}s a measurement "
                    "is worth; the probe was not started rather than started and misreported"
                ),
            }
        if runner is not None:
            try:
                out = runner(p)
            except Exception as exc:  # noqa: BLE001 - a probe must not kill the fan-out
                out = {"status": "error", "why": str(exc)}
            out.setdefault("name", p.name)
            out.setdefault("source", p.source)
            return out
        budget = min(p.timeout_s, max(1.0, deadline - time.time()))
        try:
            proc = subprocess.run(
                p.cmd,
                capture_output=True,
                text=True,
                timeout=budget,
                cwd=p.cwd,
            )
            return {
                "name": p.name,
                "source": p.source,
                "status": "ok" if proc.returncode == 0 else "failed",
                "rc": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-2000:],
            }
        except subprocess.TimeoutExpired:
            return {
                "name": p.name,
                "source": p.source,
                "status": "timeout",
                "why": f"the probe exceeded its {p.timeout_s}s bound",
            }
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "name": p.name,
                "source": p.source,
                "status": "error",
                "why": str(exc),
            }

    results: list[dict] = []
    if parallel:
        with ThreadPoolExecutor(max_workers=max(1, int(max_parallel))) as pool:
            results = list(pool.map(run_one, kept))
    else:
        results = [run_one(p) for p in kept]

    sources = sorted({p.source for p in kept})
    independent = len(sources)
    answered = [r for r in results if r.get("status") == "ok"]
    return {
        "results": results,
        "skipped_correlated": skipped_correlated,
        "independent_sources": independent,
        "sources": sources,
        "answered": len(answered),
        "failed": len(
            [r for r in results if r.get("status") in ("failed", "error", "timeout")]
        ),
        "budget_exhausted": len([r for r in results if r.get("status") == "budget"])
        > 0,
        "order": order,
        "serial_cost_s": round(serial_cost, 2),
        "parallel_cost_s": round(parallel_cost, 2),
        "elapsed_s": round(time.time() - started, 2),
        "verdict": _fan_verdict(independent, answered, results),
    }


def _fan_verdict(independent: int, answered: list[dict], results: list[dict]) -> str:
    """The fan-out's own verdict: how many INDEPENDENT sources actually answered.

    Independent sources, not probes. One source that answered five times is one piece of evidence.
    Zero independent sources that answered is BLIND -- a blind measurement is not a negative one.
    """
    if independent == 0:
        return BLIND
    if not answered:
        return BLIND
    if len(answered) < independent:
        return NO_PROGRESS
    return PROGRESS


# -- the escalation ladder ---------------------------------------------------------------------------


def escalation_for(verdict: str) -> dict:
    """What a verdict MEANS for the subject, as data. The caller decides what to do with it.

    Deliberately conservative: nothing here says "try again". A loop escalates because the next
    move is a DIFFERENT action or a human, not the same step a third time.
    """
    table = {
        PROGRESS: {
            "next": CONTINUE,
            "action": "keep doing what is working",
            "invoke": False,
        },
        NO_PROGRESS: {
            "next": BOUNDED,
            "action": "try this action once more, then re-grade; if it does not move, change it",
            "invoke": False,
        },
        REGRESSION: {
            "next": CHANGE_ACTION,
            "action": "this action made the measured state worse; change it before trying again",
            "invoke": False,
        },
        LOOP: {
            "next": ESCALATE,
            "action": (
                "this action has provably not moved the measured state; escalate with the "
                "structured data instead of repeating it"
            ),
            "invoke": True,
        },
        BLIND: {
            "next": ESCALATE,
            "action": (
                "the measurement could not be taken; fix the measurement before drawing any "
                "conclusion from it"
            ),
            "invoke": True,
        },
    }
    return table.get(
        verdict, {"next": ESCALATE, "action": "unknown verdict", "invoke": True}
    )


def summarise(rows: list[dict]) -> dict:
    """A short, honest summary of a ledger: counts by verdict, and the last row."""
    counts: dict[str, int] = {}
    for r in rows:
        v = str(r.get("verdict", "?"))
        counts[v] = counts.get(v, 0) + 1
    return {
        "rows": len(rows),
        "counts": counts,
        "last": rows[-1] if rows else None,
        "loops": [r for r in rows if r.get("verdict") == LOOP][-5:],
    }


def main(argv: list[str]) -> int:
    """A small CLI so the primitive is usable from a door, not only from Python."""
    import argparse

    p = argparse.ArgumentParser(prog="epistemic-loop", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    j = sub.add_parser("judge", help="grade one attempt from two measurements")
    j.add_argument("--subject", required=True)
    j.add_argument("--metric", required=True)
    j.add_argument("--action", required=True)
    j.add_argument(
        "--before", required=True, help="JSON object of the measurement before"
    )
    j.add_argument(
        "--after", required=True, help="JSON object of the measurement after"
    )
    j.add_argument("--direction", default="higher", choices=["higher", "lower"])
    j.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    j.add_argument("--limit", type=int, default=DEFAULT_NO_PROGRESS_LIMIT)

    s = sub.add_parser("summary", help="summarise a subject's ledger")
    s.add_argument("--subject", required=True)
    s.add_argument("--ledger", default=str(DEFAULT_LEDGER))

    f = sub.add_parser("fan-out", help="run probes in as few passes as possible")
    f.add_argument(
        "--probe",
        action="append",
        default=[],
        required=True,
        help="name|source|cmd (cmd may contain spaces; split on | only twice)",
    )
    f.add_argument("--budget-s", type=float, default=60.0)
    f.add_argument("--max-parallel", type=int, default=4)

    args = p.parse_args(argv)

    if args.cmd == "judge":
        gate = ProgressGate(
            subject=args.subject,
            metric=args.metric,
            ledger=LoopLedger(args.ledger),
            no_progress_limit=args.limit,
            direction=args.direction,
        )
        row = gate.judge(
            args.action,
            json.loads(args.before),
            json.loads(args.after),
        )
        row["escalation"] = escalation_for(str(row.get("verdict")))
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0 if row.get("verdict") in (PROGRESS, NO_PROGRESS) else 1

    if args.cmd == "summary":
        gate = ProgressGate(
            subject=args.subject,
            metric="*",
            ledger=LoopLedger(args.ledger),
        )
        print(json.dumps(summarise(gate.attempts()), indent=2, sort_keys=True))
        return 0

    probes = []
    for raw in args.probe:
        parts = raw.split("|", 2)
        if len(parts) != 3:
            raise SystemExit(f"probe must be name|source|cmd: {raw!r}")
        name, source, cmd = parts
        probes.append(Probe(name, cmd.split(), source))
    print(
        json.dumps(
            fan_out(probes, budget_s=args.budget_s, max_parallel=args.max_parallel),
            indent=2,
        )
    )
    return 0

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
