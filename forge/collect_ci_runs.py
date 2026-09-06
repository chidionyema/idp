"""Collect failed GitHub Actions runs as an outcome-labelled Forge dataset (crew#885, ci-flake-triage).

    python forge/collect_ci_runs.py --repo <owner>/<repo> --since 2026-08-09 \
        --output forge/datasets/ci-flake-triage.jsonl

The label costs nothing: a failed run is a **flake** (`1`) when the same workflow later went green on
the same commit, so nothing had to change; otherwise it is **real** (`0`) and a change was needed.
The input is what a person reads when a run goes red: workflow, job, failed step, trigger and the
cleaned tail of the failed job's log. Rows carry the run URL so any label can be re-derived.

Reads GitHub through the `gh` CLI (its own auth; no token in this file). Tokens that a log printed
anyway are redacted before a row is written; a dataset is committed (LAW 24) and must hold none.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import split  # noqa: E402

TEACHER = "outcome: same commit later green on the same workflow"
TAIL_LINES = 40
LINE_CHARS = 200
INPUT_CHARS = 2400
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[0-9:.]+Z ?")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
NOISE = re.compile(
    r"^(##\[(group|endgroup|section)\]|Post job cleanup\.?|Cleaning up orphan processes)"
)
SECRETS = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"
    r"|(?i:bearer)\s+[A-Za-z0-9._-]{16,})"
)


def gh(path: str) -> str:
    out = subprocess.run(  # noqa: S603,S607 - gh's own auth, no token here
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    return out.stdout if out.returncode == 0 else "{}"


def gh_bytes(path: str) -> bytes:
    out = subprocess.run(  # noqa: S603,S607
        ["gh", "api", "--allow-escape-sequences", path],
        capture_output=True,
        check=False,
    )
    return out.stdout if out.returncode == 0 else b""


def rate_remaining() -> int:
    core = json.loads(gh("rate_limit") or "{}").get("resources", {}).get("core", {})
    return int(core.get("remaining", 0))


def list_failed(repo: str, since: dt.date, until: dt.date) -> list[dict]:
    """Every failed run between the dates, newest first. The API caps one listing at 1000 rows, so
    we ask one day at a time (this estate fails about 700 runs a day, measured 2026-09-06)."""
    runs: list[dict] = []
    day = until
    while day >= since:
        for page in range(1, 11):
            body = gh(
                f"repos/{repo}/actions/runs?status=failure&per_page=100&page={page}&created={day}"
            )
            batch = json.loads(body or "{}").get("workflow_runs", [])
            runs.extend(batch)
            if len(batch) < 100:
                break
        day -= dt.timedelta(days=1)
    return runs


def stratify(failed: list[dict], per_workflow: int, limit: int) -> list[dict]:
    """Newest `per_workflow` runs of each workflow, then the newest `limit` overall, so one noisy
    scheduled workflow cannot be the whole dataset."""
    seen: dict[str, int] = {}
    kept = []
    for run in failed:
        n = seen.get(run["name"], 0)
        if n < per_workflow:
            seen[run["name"]] = n + 1
            kept.append(run)
    return kept[:limit] if limit else kept


def label(repo: str, run: dict) -> str:
    """`1` (flake) when a later green run of the same workflow sits on the same commit, else `0`.
    One call per run against `head_sha`, instead of listing every green run the estate ever had."""
    body = gh(
        f"repos/{repo}/actions/runs?head_sha={run['head_sha']}&status=success&per_page=100"
    )
    for green in json.loads(body or "{}").get("workflow_runs", []):
        if green["name"] == run["name"] and green["created_at"] > run["created_at"]:
            return "1"
    return "0"


def clean_tail(log: str) -> str:
    lines = []
    for raw in log.splitlines():
        line = ANSI.sub("", TS.sub("", raw)).rstrip()
        if not line or NOISE.match(line):
            continue
        lines.append(SECRETS.sub("<redacted>", line)[:LINE_CHARS])
    return "\n".join(lines[-TAIL_LINES:])


def failed_step(repo: str, run_id: int) -> tuple[dict | None, dict | None]:
    """The first failed job and its first failed step, from the jobs API."""
    jobs = json.loads(gh(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")).get(
        "jobs", []
    )
    for job in jobs:
        if job.get("conclusion") == "failure":
            step = next(
                (s for s in job.get("steps", []) if s.get("conclusion") == "failure"),
                None,
            )
            return job, step
    return None, None


def step_log(repo: str, job: dict, step: dict | None) -> str:
    """The failed step's own lines from the job log: every line the API returns carries a UTC
    timestamp, and the jobs API gives the step's started_at and completed_at, so the slice between
    them is that step and not the checkout cleanup that follows it. (The run's log archive stopped
    carrying per-step files, measured 2026-09-06.)"""
    text = gh_bytes(f"repos/{repo}/actions/jobs/{job['id']}/logs").decode(
        "utf-8", "replace"
    )
    if not step or not step.get("started_at") or not step.get("completed_at"):
        return text
    lo, hi = step["started_at"][:19], step["completed_at"][:19]
    kept = [line for line in text.splitlines() if lo <= line[:19] <= hi]
    # the API's step clock is whole seconds and the post-job cleanup runs inside the same second,
    # so cut at the step's own failure line, else at the first cleanup line
    errors = [i for i, line in enumerate(kept) if "##[error]" in line]
    if errors:
        kept = kept[: errors[-1] + 1]
    else:
        cleanup = [
            i
            for i, line in enumerate(kept)
            if "Post job cleanup" in line or "##[group]Post " in line
        ]
        if cleanup:
            kept = kept[: cleanup[0]]
    return "\n".join(kept) if kept else text


def row_for(repo: str, run: dict) -> dict | None:
    job, step = failed_step(repo, run["id"])
    if job is None:
        return None
    tail = clean_tail(step_log(repo, job, step))
    if not tail:
        return None
    verdict = label(repo, run)
    head = (
        f"workflow: {run['name']}\njob: {job['name']}\nstep: {step['name'] if step else ''}\n"
        f"event: {run['event']}\nlog tail:\n"
    )
    return {
        "input": head + tail[-(INPUT_CHARS - len(head)) :],
        "output": verdict,
        "teacher": TEACHER,
        "source": run["html_url"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--since", type=dt.date.fromisoformat, required=True)
    ap.add_argument("--until", type=dt.date.fromisoformat, default=dt.date.today())
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--limit",
        type=int,
        default=800,
        help="failed runs read, newest first (0 = all)",
    )
    ap.add_argument(
        "--per-workflow", type=int, default=150, help="cap per workflow name"
    )
    ap.add_argument(
        "--smoke", action="store_true", help="accept under 500 rows (schema check only)"
    )
    args = ap.parse_args()

    failed = stratify(
        list_failed(args.repo, args.since, args.until), args.per_workflow, args.limit
    )
    need = 3 * len(failed) + 50  # jobs, archive, head_sha lookup per run
    have = rate_remaining()
    if have < need:
        print(
            f"Refusal: GitHub rate limit {have} remaining, {need} calls needed",
            file=sys.stderr,
        )
        return 2
    with ThreadPoolExecutor(args.workers) as pool:
        rows = [r for r in pool.map(lambda run: row_for(args.repo, run), failed) if r]
    rows.sort(key=lambda r: r["source"])
    rows = split(rows, minimum=1 if args.smoke else split.__defaults__[2])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    flakes = sum(r["output"] == "1" for r in rows)
    print(
        json.dumps(
            {
                "failed_runs": len(failed),
                "per_workflow": dict(Counter(r["name"] for r in failed)),
                "rows": len(rows),
                "flake": flakes,
                "real": len(rows) - flakes,
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
