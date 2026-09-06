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
import io
import subprocess
import sys
import zipfile
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
        ["gh", "api", path], capture_output=True, check=False
    )
    return out.stdout if out.returncode == 0 else b""


def list_runs(repo: str, since: dt.date, until: dt.date, status: str) -> list[dict]:
    """Every run with `status` between the dates. The API caps a listing at 1000, so we ask one
    week at a time; a week of this estate stays under the cap for one status."""
    runs: list[dict] = []
    start = since
    while start <= until:
        end = min(start + dt.timedelta(days=6), until)
        for page in range(1, 11):
            body = gh(
                f"repos/{repo}/actions/runs?status={status}&per_page=100&page={page}"
                f"&created={start}..{end}"
            )
            batch = json.loads(body or "{}").get("workflow_runs", [])
            runs.extend(batch)
            if len(batch) < 100:
                break
        start = end + dt.timedelta(days=1)
    return runs


def label(failed: list[dict], green: list[dict]) -> dict[int, str]:
    """`1` (flake) when a later green run of the same workflow sits on the same commit, else `0`."""
    green_at: dict[tuple[str, str], list[str]] = {}
    for run in green:
        green_at.setdefault((run["name"], run["head_sha"]), []).append(
            run["created_at"]
        )
    out = {}
    for run in failed:
        later = green_at.get((run["name"], run["head_sha"]), [])
        out[run["id"]] = "1" if any(t > run["created_at"] for t in later) else "0"
    return out


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


def step_log(repo: str, run_id: int, job: dict, step: dict | None) -> str:
    """That step's own log from the run's log archive (`<job>/<n>_<step>.txt`), so the tail is
    the failure and not the checkout cleanup that follows it in the combined job log."""
    blob = gh_bytes(f"repos/{repo}/actions/runs/{run_id}/logs")
    if not blob:
        return ""
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return ""
    want = f"{step['number']}_" if step else None
    for name in archive.namelist():
        head, _, leaf = name.rpartition("/")
        if not head or not head.startswith(job["name"][: len(head)]):
            continue
        if want is None or leaf.startswith(want):
            return archive.read(name).decode("utf-8", "replace")
    return ""


def row_for(repo: str, run: dict, verdict: str) -> dict | None:
    job, step = failed_step(repo, run["id"])
    if job is None:
        return None
    tail = clean_tail(step_log(repo, run["id"], job, step))
    if not tail:
        return None
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
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument(
        "--limit", type=int, default=0, help="cap failed runs read (0 = all)"
    )
    args = ap.parse_args()

    failed = list_runs(args.repo, args.since, args.until, "failure")
    green = list_runs(args.repo, args.since, args.until, "success")
    verdicts = label(failed, green)
    if args.limit:
        failed = failed[: args.limit]
    with ThreadPoolExecutor(args.workers) as pool:
        rows = [
            r
            for r in pool.map(
                lambda run: row_for(args.repo, run, verdicts[run["id"]]), failed
            )
            if r
        ]
    rows.sort(key=lambda r: r["source"])
    rows = split(rows, minimum=1 if args.limit else split.__defaults__[2])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    flakes = sum(r["output"] == "1" for r in rows)
    print(
        json.dumps(
            {
                "failed_runs": len(failed),
                "green_runs": len(green),
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
