"""Agent jobs: give an agent a task from Fleet, and watch it become a merged pull request.

WHAT A JOB IS. One run of `.github/workflows/agent-sandbox.yml`: the agent works in a runner with
no credential, main's epistemic firewall grades every claim it made, and only then does the estate
App open a pull request, which merge-when-green lands. This module dispatches that workflow and
reads its runs back. It keeps no store of its own: the run title (the workflow's `run-name`,
"agent (<harness>): <task>") is the record, so a job started from the CLI or /create shows up
here too, and a restart of this process loses nothing (AGENTS.md section 6: one ledger).

WHY SO MANY REFUSALS. This is the founder's work surface, used from a phone. Every way a submit
can go wrong has to come back as a sentence the page can show, never a spinner or a silent no:
  - the task is published: workflow_dispatch inputs are visible on a public repository's run
    page, so a task that looks like it holds a secret is refused before anything leaves;
  - a double tap on a phone is one job, not two (DUPLICATE_WINDOW_S, under a lock);
  - at most MAX_ACTIVE jobs run at once (the estate's agent spawn budget);
  - GitHub's own refusals (401, 403, rate limit, 404, 422, 5xx, no network) each say which.

THE CREDENTIAL. In the cluster, the portal's App token (platform/backstage/overlays/oke/
github-token.yaml, the backstage lane: dispatch a workflow, read runs), read from
FLEETVIEW_GITHUB_TOKEN_FILE on EVERY call because it is re-minted every 45 minutes. Following a
run to its PR needs pull_requests: read and a failure's own line needs checks: read; a lane
without them gets "Fleet may not read pull requests." and the failed step's name, never an error.
On the laptop, `gh auth token`. It is never logged and never returned.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fleetview_backend import redact

WORKFLOW = "agent-sandbox.yml"
HARNESSES = ("pi", "claude-code")
MAX_TASK_CHARS = 4000
MAX_ACTIVE = 3
DUPLICATE_WINDOW_S = 120.0
LIST_TTL_S = 5.0
HTTP_TIMEOUT_S = 10.0
STAGES = ("agent", "firewall", "open-pr")
_TITLE = re.compile(r"^agent \((?P<harness>[a-z-]+)\): (?P<task>.*)$", re.S)

_LOCK = threading.Lock()
_FINAL: dict[int, dict[str, Any]] = {}
_LIST_CACHE: dict[str, Any] = {"at": 0.0, "jobs": None}


class JobRefused(Exception):
    """A refusal the page shows as it is. `status` is the HTTP status the route answers with."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def repo() -> str:
    return os.environ.get("FLEETVIEW_AGENT_REPO") or "chidionyema/idp"


def api_base() -> str:
    return (os.environ.get("FLEETVIEW_GITHUB_API") or "https://api.github.com").rstrip(
        "/"
    )


def title_for(harness: str, task: str) -> str:
    return f"agent ({harness}): {task}"


def _token() -> str:
    path = os.environ.get("FLEETVIEW_GITHUB_TOKEN_FILE")
    if path:
        try:
            tok = (
                Path(path).read_text().strip()
            )  # re-read every call: the token is rotated
        except OSError:
            tok = ""
        if tok:
            return tok
    try:
        p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            ["gh", "auth", "token"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        p = None
    if p is not None and p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    raise JobRefused(
        503,
        "Fleet has no GitHub credential: FLEETVIEW_GITHUB_TOKEN_FILE is unset or empty, "
        "and `gh auth token` gave nothing.",
    )


def _gh(method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    """One GitHub API call. Returns (status, parsed body); raises JobRefused for anything the
    caller cannot act on. 403 and 404 come back to the caller when it asked for them (reads that
    have a fallback); everything else is translated here, once."""
    tok = _token()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 -- https (or the test's local fake), fixed host
        api_base() + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "fleetview-agent-jobs",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as r:  # noqa: S310
            raw = r.read()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read() or b""
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except ValueError:
            parsed = {}
        msg = str((parsed or {}).get("message") or "")[:200]
        if e.code == 401:
            raise JobRefused(502, "GitHub refused Fleet's credential (401).") from None
        if e.code in (403, 429) and e.headers.get("x-ratelimit-remaining") == "0":
            reset = e.headers.get("x-ratelimit-reset") or ""
            when = (
                datetime.fromtimestamp(int(reset), timezone.utc).strftime("%H:%MZ")
                if reset.isdigit()
                else "later"
            )
            raise JobRefused(
                503, f"GitHub's rate limit is spent; it resets at {when}."
            ) from None
        if e.code in (403, 404):
            return e.code, parsed
        if e.code == 422:
            raise JobRefused(
                400, f"GitHub refused the job: {msg or 'unprocessable'}."
            ) from None
        raise JobRefused(
            502, f"GitHub answered {e.code}{': ' + msg if msg else ''}."
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        why = getattr(e, "reason", None) or e.__class__.__name__
        raise JobRefused(502, f"GitHub is unreachable from Fleet ({why}).") from None


def _recent_runs(per_page: int = 20) -> list[dict]:
    status, body = _gh(
        "GET", f"/repos/{repo()}/actions/workflows/{WORKFLOW}/runs?per_page={per_page}"
    )
    if status == 404:
        raise JobRefused(502, f"GitHub has no workflow {WORKFLOW} in {repo()}.")
    if status == 403:
        raise JobRefused(502, "Fleet's credential may not read Actions runs (403).")
    return list((body or {}).get("workflow_runs") or [])


def _created_ts(run: dict) -> float:
    try:
        return datetime.fromisoformat(
            str(run.get("created_at")).replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        return 0.0


def validate(task: Any, harness: Any) -> tuple[str, str]:
    if not isinstance(task, str) or not task.strip():
        raise JobRefused(400, "Say what the agent should do: the task is empty.")
    task = task.strip()
    if len(task) > MAX_TASK_CHARS:
        raise JobRefused(
            400, f"The task is {len(task)} characters; keep it under {MAX_TASK_CHARS}."
        )
    if harness not in HARNESSES:
        raise JobRefused(400, f"Harness must be one of {', '.join(HARNESSES)}.")
    _safe, found = redact.redact(task)
    if found:
        raise JobRefused(
            400,
            "The task looks like it holds a secret ("
            + ", ".join(sorted(set(found)))
            + "). A task is published on the run page, so nothing was sent; "
            "name the secret by its env var instead.",
        )
    return task, harness


def submit(task: Any, harness: Any = "pi", by: str = "") -> tuple[dict, int]:
    """Dispatch one job. Returns (job, HTTP status); raises JobRefused."""
    task, harness = validate(task, harness)
    title = title_for(harness, task)
    with _LOCK:
        runs = _recent_runs()
        now = time.time()
        for run in runs:
            if (
                run.get("status") != "completed"
                and str(run.get("display_title") or "") == title
                and now - _created_ts(run) <= DUPLICATE_WINDOW_S
            ):
                return {**job_from_run(run, detail=False), "duplicate": True}, 200
        active = [r for r in runs if r.get("status") != "completed"]
        if len(active) >= MAX_ACTIVE:
            raise JobRefused(
                429,
                f"{len(active)} agent jobs are already running; the budget is {MAX_ACTIVE}. "
                "Wait for one to finish.",
            )
        t0 = time.time()
        status, body = _gh(
            "POST",
            f"/repos/{repo()}/actions/workflows/{WORKFLOW}/dispatches",
            {"ref": "main", "inputs": {"harness": harness, "task": task}},
        )
        if status == 404:
            raise JobRefused(
                502, f"GitHub has no workflow {WORKFLOW} in {repo()} to dispatch."
            )
        if status == 403:
            raise JobRefused(
                502, "Fleet's credential may not dispatch workflows (403)."
            )
        _LIST_CACHE["at"] = 0.0
        run_id = (body or {}).get("workflow_run_id")
        if not run_id:
            # An API that answers 204 with no body: find the run by its title, created after t0.
            for run in _recent_runs(per_page=10):
                if (
                    str(run.get("display_title") or "") == title
                    and _created_ts(run) >= t0 - 5
                ):
                    run_id = run.get("id")
                    break
    job = {
        "run_id": run_id,
        "harness": harness,
        "task": task,
        "by": by or "fleet",
        "stage": "queued",
        "state": "running",
        "reason": None,
        "run_url": (body or {}).get("html_url")
        or (f"https://github.com/{repo()}/actions/runs/{run_id}" if run_id else None),
        "pr": None,
        "duplicate": False,
    }
    if not run_id:
        job["reason"] = "Dispatched; GitHub has not listed the run yet."
        return job, 202
    return job, 201


def _jobs_of(run_id: int) -> list[dict]:
    status, body = _gh("GET", f"/repos/{repo()}/actions/runs/{run_id}/jobs")
    if status in (403, 404):
        return []
    return list((body or {}).get("jobs") or [])


def _failure_reason(job: dict) -> str:
    """The failing job's own ::error:: line (a check-run annotation), else the failed step."""
    status, body = _gh("GET", f"/repos/{repo()}/check-runs/{job.get('id')}/annotations")
    if status not in (403, 404):
        for a in body or []:
            if a.get("annotation_level") == "failure" and a.get("message"):
                msg = str(a["message"]).strip()
                if msg and not msg.startswith("Process completed with exit code"):
                    return redact.redact(msg)[0][:300]
    for step in job.get("steps") or []:
        if step.get("conclusion") == "failure":
            return f"failed at: {step.get('name')}"
    return f"{job.get('name')} failed"


def _pr_of(run_id: int, harness: str | None) -> dict | None:
    owner = repo().split("/")[0]
    for h in [harness] if harness else list(HARNESSES):
        status, body = _gh(
            "GET", f"/repos/{repo()}/pulls?state=all&head={owner}:agent/{h}-{run_id}"
        )
        if status in (403, 404):
            return {"number": None, "url": None, "state": "unknown"}
        for pr in body or []:
            state = "merged" if pr.get("merged_at") else str(pr.get("state"))
            return {
                "number": pr.get("number"),
                "url": pr.get("html_url"),
                "state": state,
            }
    return None


def job_from_run(run: dict, detail: bool = True) -> dict:
    run_id = run.get("id")
    title = str(run.get("display_title") or "")
    m = _TITLE.match(title)
    job: dict[str, Any] = {
        "run_id": run_id,
        "harness": m.group("harness") if m else None,
        "task": m.group("task") if m else title,
        "by": (run.get("triggering_actor") or run.get("actor") or {}).get("login"),
        "created_at": run.get("created_at"),
        "run_url": run.get("html_url"),
        "stage": "queued",
        "state": "running",
        "reason": None,
        "pr": None,
        "duplicate": False,
    }
    if not detail:
        return job
    if run_id in _FINAL:
        return _FINAL[run_id]
    if run.get("status") != "completed":
        jobs = {j.get("name"): j for j in _jobs_of(run_id)}
        # The stage is the first of agent -> firewall -> open-pr that has not finished. Until the
        # agent job exists at all, the run is queued for a runner.
        for i, name in enumerate(STAGES):
            j = jobs.get(name)
            if j is not None and j.get("status") == "completed":
                continue
            if j is not None or i > 0:
                job["stage"] = name
            break
        else:
            job["stage"] = STAGES[-1]
        return job
    conclusion = run.get("conclusion")
    if conclusion == "success":
        pr = _pr_of(run_id, job["harness"])
        job["pr"] = pr
        if pr is None:
            job.update(
                stage="done",
                state="failed",
                reason="The run passed but no PR was found.",
            )
        elif pr["state"] == "merged":
            job.update(stage="merged", state="done")
        elif pr["state"] == "closed":
            job.update(
                stage="closed",
                state="failed",
                reason="The PR was closed without merging.",
            )
        elif pr["state"] == "unknown":
            job.update(
                stage="pr", state="running", reason="Fleet may not read pull requests."
            )
        else:
            job.update(stage="pr", state="running")
    elif conclusion in ("cancelled", "skipped"):
        job.update(stage="cancelled", state="failed", reason="The run was cancelled.")
    else:
        # Only a failure needs the run's jobs. A job waiting on its PR is re-read every poll, and
        # the portal's token shares one hourly budget with everything else it does.
        jobs = {j.get("name"): j for j in _jobs_of(run_id)}
        failed = next(
            (
                jobs[n]
                for n in STAGES
                if n in jobs and jobs[n].get("conclusion") == "failure"
            ),
            None,
        )
        if failed is None:
            job.update(
                stage="failed", state="failed", reason=f"The run ended {conclusion}."
            )
        else:
            job.update(
                stage=failed.get("name"), state="failed", reason=_failure_reason(failed)
            )
    if job["state"] != "running":
        _FINAL[run_id] = job
    return job


def list_jobs(limit: int = 10) -> tuple[dict, int]:
    now = time.time()
    if _LIST_CACHE["jobs"] is not None and now - _LIST_CACHE["at"] < LIST_TTL_S:
        return {"available": True, "error": None, "jobs": _LIST_CACHE["jobs"]}, 200
    try:
        runs = _recent_runs(per_page=max(1, min(limit, 30)))
        jobs = [job_from_run(r) for r in runs[:limit]]
    except JobRefused as e:
        # A board that cannot read says so; it never shows an empty list as if nothing ran.
        return {"available": False, "error": str(e), "jobs": []}, e.status
    _LIST_CACHE.update(at=now, jobs=jobs)
    return {"available": True, "error": None, "jobs": jobs}, 200


def handle_post(body: Any) -> tuple[dict, int]:
    """POST /agent-jobs: the page's JSON in, (job or {"error": sentence}, status) out."""
    if not isinstance(body, dict):
        return {"error": "Send JSON: {task, harness, by}."}, 400
    try:
        return submit(
            body.get("task"), body.get("harness") or "pi", str(body.get("by") or "")
        )
    except JobRefused as exc:
        return {"error": str(exc)}, exc.status


def reset_for_tests() -> None:
    _FINAL.clear()
    _LIST_CACHE.update(at=0.0, jobs=None)
