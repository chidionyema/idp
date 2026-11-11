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

THE TLS TRUST STORE. Every call is made with a context built from certifi's bundle, because the
interpreter launchd runs this service with has no CA bundle of its own. Without it every GitHub
call died "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate" and this whole door
-- the claims panel, the job buttons, the voice job path -- answered 502 "GitHub is unreachable
from Fleet" (measured 2026-10-12, issue #5830). Verification is never switched off to work around
a missing bundle: a context that trusts nothing and a context that checks nothing are both wrong.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import ssl
import subprocess
import sys
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
# The board's stage vocabulary (the panel's own words, unchanged) and the workflow's job names
# behind it. The third job of `.github/workflows/agent-sandbox.yml` is named `submit-lane`
# today; the board has always called that step "open-pr" (the step where the pull request comes
# to exist). The mapping is what lets a run that died in the SUBMISSION step be named with the
# step that killed it -- before it, the job name never matched, so every sandbox failure after
# the rename read as the useless "The run ended failure." and the founder had to go into the
# run's logs to find out why. Measured on run 42975234558 (mission INS-00011): the real reason
# was the commit-msg hook refusing a new Python file without a Language-Exception trailer.
STAGE_JOBS = {
    "agent": ("agent",),
    "firewall": ("firewall",),
    "open-pr": ("submit-lane", "open-pr"),
}
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


_SSL_CONTEXT: ssl.SSLContext | None = None


def ssl_context() -> ssl.SSLContext:
    """The context every GitHub call is made with: certifi's bundle, verification never off.

    WHY (issue #5830). The interpreter launchd runs this service with ships no CA bundle of its
    own, so the platform default trusts nothing and every call died
    "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate" -- measured 2026-10-12 on
    /claims, and it is the same door as the job buttons and the voice job path. certifi is already
    installed for that interpreter; the bundle, not the network, was missing. Built once per
    process: reloading a CA bundle on every call is waste on a work surface.
    """
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        try:
            import certifi

            _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
        except Exception:  # noqa: BLE001 -- no certifi: the platform default, unchanged
            _SSL_CONTEXT = ssl.create_default_context()
    return _SSL_CONTEXT


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
        # certifi's bundle: this interpreter has no CA store of its own (issue #5830)
        with urllib.request.urlopen(  # noqa: S310
            req, timeout=HTTP_TIMEOUT_S, context=ssl_context()
        ) as r:
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


def gh_text(path: str) -> tuple[int, str]:
    """One authenticated GET of a plain-text body -- a job log, not JSON.

    The same credential, the same CA bundle and the same failure translation as `_gh`; only
    the body differs. A job log is how the estate reads which provider ACTUALLY ran (the
    workflow's own fallback marker) without opening the sealed transcript, so it is worth one
    door rather than a second credential path somewhere else.
    """
    tok = _token()
    req = urllib.request.Request(  # noqa: S310 -- https (or the test's local fake), fixed host
        api_base() + path,
        method="GET",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "text/plain",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fleetview-agent-jobs",
        },
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            req, timeout=HTTP_TIMEOUT_S, context=ssl_context()
        ) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        e.read()
        if e.code == 401:
            raise JobRefused(502, "GitHub refused Fleet's credential (401).") from None
        if e.code in (403, 404):
            return e.code, ""
        raise JobRefused(502, f"GitHub answered {e.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        why = getattr(e, "reason", None) or e.__class__.__name__
        raise JobRefused(502, f"GitHub is unreachable from Fleet ({why}).") from None


def gh_get(path: str) -> tuple[int, Any]:
    """One authenticated GET against the estate's GitHub, for the modules that are not agent
    jobs (claims.py reads the live claims through here).

    The credential -- FLEETVIEW_GITHUB_TOKEN_FILE in the cluster, re-read every call because the
    App token is re-minted every 45 minutes, `gh auth token` on the laptop -- and the translation
    of every GitHub failure already live in `_gh`. A second module with its own token read and
    its own 401 sentence would be a second credential path to rotate and a second place for the
    rate-limit answer to be wrong.
    """
    return _gh("GET", path)


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
    """The pull request the run produced, in ONE GitHub call.

    The sandbox does not raise a pull request itself: it pushes `lane/agent-<harness>-<run>` as
    the estate App, and the Greenlane raises the pull request with that lane as its head
    (greenlane/github.py's `_ensure_pr` posts `{"head": lane}`). So the head to ask for is the
    LANE. It used to ask for `agent/<harness>-<run>`, the branch the sandbox pushed before the
    lane convention, so every sandbox run after the change answered "The run passed but no PR
    was found" -- a false failure on a run that had in fact landed.

    ONE call, not two: the portal's token shares an hourly budget with everything else it does
    (the job list is polled every few seconds), so a second lookup for the old branch name
    would cost a call on every poll of every run.
    """
    owner = repo().split("/")[0]
    for h in [harness] if harness else list(HARNESSES):
        status, body = _gh(
            "GET",
            f"/repos/{repo()}/pulls?state=all&head={owner}:lane/agent-{h}-{run_id}",
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


def _stage_of_job(name: str) -> str:
    """The board's stage for a workflow job name."""
    for stage, names in STAGE_JOBS.items():
        if name in names:
            return stage
    return str(name)


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
        # The stage is the first of agent -> firewall -> open-pr that has not finished. Until
        # the agent job exists at all, the run is queued for a runner.
        for i, stage in enumerate(STAGES):
            present = [jobs[n] for n in STAGE_JOBS[stage] if n in jobs]
            if present and all(j.get("status") == "completed" for j in present):
                continue
            if present or i > 0:
                job["stage"] = stage
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
                j
                for name, j in jobs.items()
                if j.get("conclusion") == "failure"
                and name in {n for names in STAGE_JOBS.values() for n in names}
            ),
            None,
        )
        if failed is None:
            job.update(
                stage="failed", state="failed", reason=f"The run ended {conclusion}."
            )
        else:
            job.update(
                stage=_stage_of_job(str(failed.get("name"))),
                state="failed",
                reason=_failure_reason(failed),
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


# ===============================================================================
# THE MISSION RECEIPT (INS-00011): one dispatched cloud mission, projected honestly.
#
# WHY IT LIVES HERE AND NOT IN A NEW MODULE. The founder's ruling on new estate
# capability code (bin/language-gate, 2026-10-30) is Rust over Python unless the
# reason is written down, and the agent-sandbox submit step (the GitHub-hosted
# worker-to-commit boundary) builds a FIXED commit message that cannot carry a
# `Language-Exception:` trailer. Measured on the previous run of this same mission
# (issue #7932, run 42975234558): the worker produced a correct patch, the
# epistemic firewall passed it, and the commit-msg hook refused it with
# "FAIL language-gate: 1 new Python file(s) with no documented reason". The
# founder's correction on that issue says this work "belongs to the extant Python
# FleetView service and the reason ... should be maintaining an existing Python
# runtime/route contract rather than inventing a Rust sidecar". A MODIFIED
# existing Python file is not a new language default being chosen (the gate says
# so itself), so the projection lives in the module that already owns the
# GitHub-hosted agent-run contract -- one credential path, one GitHub record, one
# place that knows what a run is.
#
# WHAT IT IS: a read-only projection of ONE run of .github/workflows/agent-sandbox.yml
# into a bounded JSON receipt the Founder Surface can read. Every field is read from
# GitHub, which is already the run's own record, so a receipt can never disagree
# with the run it describes and nothing is stored here.
#
# THE HONESTY RULES (machine-readable codes, not prose):
#   * a queued run is not a started worker; a patch is not a landed patch; a merge
#     is not a live effect, so `live_effect` stays false and says why;
#   * a run that ended green having produced nothing is NOT VERIFIED -- that is the
#     negative control the mission names, and a green no-op must not read as success;
#   * conflicting statuses (a green run whose agent job failed) are named as conflicts;
#   * the provider recorded is the one that ACTUALLY ran, read from the agent job's
#     own log marker -- a title that says "gemini" proves only what was requested.
# ===============================================================================

# The stage ladder. Each stage is a fact with evidence behind it, and the receipt reports the
# furthest one reached AND the whole ladder, so a consumer can see what is missing and not just
# the last thing that happened.
RECEIPT_STAGES = (
    "queued",
    "started",
    "patch_produced",
    "cif_passed",
    "greenlane_landed",
    "live_effect",
)

# How old a receipt may be before a consumer must read again. The run's own state changes every
# few seconds while it works, so a receipt older than this is reported as stale rather than
# quietly presented as current.
RECEIPT_STALE_AFTER_S = 300.0

# The receipt is a read model, not a transcript: every unbounded field is capped.
RECEIPT_MAX_TASK_CHARS = 300
RECEIPT_MAX_FILES = 50
RECEIPT_MAX_PATH_CHARS = 200
RECEIPT_MAX_REASONS = 20

# The run title is the record of what was asked for ("agent (<harness>): <task>"), and the
# workflow's issue-triggered title carries the instruction id: "agent (gemini): LEGION #7932".
_RECEIPT_TITLE = re.compile(r"^agent \((?P<harness>[a-z0-9-]+)\): (?P<task>.*)$", re.S)
_RECEIPT_ISSUE_IN_TITLE = re.compile(r"#(?P<n>\d+)")

# The agent job's own log markers. These are the fixed, low-entropy lines the workflow prints;
# the agent's words never reach this log (they go to a file inside the sealed artifact), so
# reading them is safe to project into public metadata.
_FALLBACK_MARK = re.compile(
    r"legion provider fallback:\s*google_failure=(?P<class>[\w-]+)\s+"
    r"fallback=(?P<provider>[\w-]+)\s+exit=(?P<rc>-?\d+)"
)
_FAILURE_MARK = re.compile(
    r"legion provider failure:\s*class=(?P<class>[\w-]+)\s+fallback=(?P<provider>[\w-]+)"
)
_HARNESS_EXIT = re.compile(r"^harness exit (?P<rc>-?\d+)\s*$", re.M)
_PATCH_MARK = re.compile(r"^patch:\s*(?P<stat>.*)$", re.M)
_FILES_CHANGED = re.compile(r"(?P<n>\d+)\s+files? changed")

# The workflow's pinned models, read at the run's own commit. The provider names are the ones
# the workflow itself uses; the model for the gemini path is a dispatch input, so it is not
# pinned in the file and is therefore never asserted from it.
_WORKFLOW_PROVIDER = re.compile(
    r"--provider\s+(?P<provider>[a-z0-9_-]+)\s+--model\s+(?P<model>\"[^\"]*\"|[\w.\-]+)"
)


class ReceiptRefused(Exception):
    """A refusal the surface shows as it is. `status` is the HTTP status; `code` is the
    machine-readable reason, so a consumer can tell "not found" from "cannot read" from
    "no credential" without parsing a sentence."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def _now_iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _epoch(stamp: Any) -> float:
    """Seconds since the epoch for a GitHub ISO timestamp, or 0.0 when it cannot be read.

    0.0 is a real answer and is returned as one: an unreadable timestamp is not "now", and
    treating it as now would make a two-day-old evidence look fresh.
    """
    if not stamp:
        return 0.0
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


# -- the reads. Every one of them is a canonical GitHub record; none of them writes. --


def _receipt_get(path: str) -> Any:
    """One authenticated GET through the estate's single GitHub credential path.

    agent_jobs owns the credential (the App token in the cluster, `gh auth token` on the
    laptop) and the translation of every GitHub failure. A second credential read here would be
    a second thing to rotate and a second place for the answer to be wrong.
    """
    try:
        status, body = gh_get(path)
    except JobRefused as exc:
        raise ReceiptRefused(exc.status, _code_for(str(exc)), str(exc)) from None
    if status == 404:
        raise ReceiptRefused(404, "not-found", f"GitHub has no {path}.")
    if status == 403:
        raise ReceiptRefused(
            502, "forbidden", f"Fleet's credential may not read {path} (403)."
        )
    if status >= 400:
        raise ReceiptRefused(
            502, "github-error", f"GitHub answered {status} for {path}."
        )
    return body


def _code_for(message: str) -> str:
    low = message.lower()
    if "credential" in low:
        return "credential-missing"
    if "401" in low:
        return "credential-rejected"
    if "unreachable" in low:
        return "github-unreachable"
    if "rate limit" in low:
        return "rate-limited"
    return "github-error"


def _receipt_get_text(path: str) -> str:
    """One authenticated GET of a plain-text body (a job log). Same credential, same context."""
    try:
        status, text = gh_text(path)
    except JobRefused as exc:
        raise ReceiptRefused(exc.status, _code_for(str(exc)), str(exc)) from None
    if status == 404:
        return ""
    if status == 403:
        return ""
    if status >= 400:
        return ""
    return text or ""


def _run(run_id: int) -> dict:
    return _receipt_get(f"/repos/{repo()}/actions/runs/{run_id}") or {}


def _jobs(run_id: int) -> list[dict]:
    body = _receipt_get(f"/repos/{repo()}/actions/runs/{run_id}/jobs") or {}
    return list(body.get("jobs") or [])


def _job_log(job_id: Any) -> str:
    if not job_id:
        return ""
    return _receipt_get_text(f"/repos/{repo()}/actions/jobs/{job_id}/logs")


def _ref(branch: str) -> dict | None:
    try:
        body = _receipt_get(f"/repos/{repo()}/git/ref/heads/{branch}")
    except ReceiptRefused as exc:
        if exc.code == "not-found":
            return None
        raise
    return body if isinstance(body, dict) else None


def _commit(sha: str) -> dict | None:
    try:
        body = _receipt_get(f"/repos/{repo()}/commits/{sha}")
    except ReceiptRefused as exc:
        if exc.code == "not-found":
            return None
        raise
    return body if isinstance(body, dict) else None


def _pulls(branch: str) -> list[dict]:
    owner = repo().split("/")[0]
    body = _receipt_get(f"/repos/{repo()}/pulls?state=all&head={owner}:{branch}") or []
    return list(body) if isinstance(body, list) else []


def _compare(base: str, head: str) -> dict:
    try:
        body = _receipt_get(f"/repos/{repo()}/compare/{base}...{head}")
    except ReceiptRefused as exc:
        if exc.code == "not-found":
            return {}
        raise
    return body if isinstance(body, dict) else {}


def _issue_comments(number: int) -> list[dict]:
    body = _receipt_get(f"/repos/{repo()}/issues/{number}/comments?per_page=100") or []
    return list(body) if isinstance(body, list) else []


def _workflow_pins(sha: str) -> dict[str, Any]:
    """The provider/model pairs the workflow pins, read AT THE RUN'S COMMIT.

    This is how the model name gets evidence: the file at the exact SHA the worker started from
    is the thing that decided which model ran. It is a file read, not a memory of the workflow.
    """
    pins: dict[str, Any] = {"providers": {}, "sha": sha, "read": False}
    try:
        body = _receipt_get(
            f"/repos/{repo()}/contents/.github/workflows/{WORKFLOW}?ref={sha}"
        )
    except ReceiptRefused:
        return pins
    if not isinstance(body, dict):
        return pins
    raw = body.get("content") or ""
    try:
        text = base64.b64decode(raw).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return pins
    for m in _WORKFLOW_PROVIDER.finditer(text):
        model = m.group("model").strip('"')
        pins["providers"].setdefault(m.group("provider"), model)
    pins["read"] = True
    return pins


# -- the projection. Pure: it takes evidence and returns the receipt. --


def _lane_branch(harness: str | None, run_id: Any) -> str | None:
    if not harness or not run_id:
        return None
    return f"lane/agent-{harness}-{run_id}"


def _log_markers(log: str) -> dict[str, Any]:
    """The fixed markers the workflow prints in the agent job's log."""
    out: dict[str, Any] = {
        "provider": None,
        "provider_source": None,
        "failure_class": None,
        "harness_exit": None,
        "patch_files": None,
        "fallback": False,
    }
    m = _FALLBACK_MARK.search(log)
    if m:
        out["provider"] = m.group("provider")
        out["provider_source"] = "agent job log (provider fallback marker)"
        out["failure_class"] = m.group("class")
        out["fallback"] = True
        out["failed_provider"] = "google"
        return out
    m = _FAILURE_MARK.search(log)
    if m:
        out["provider"] = "google"
        out["provider_source"] = "agent job log (provider failure marker)"
        out["failure_class"] = m.group("class")
        out["provider_unavailable"] = True
        return out
    m = _HARNESS_EXIT.search(log)
    if m:
        out["harness_exit"] = int(m.group("rc"))
    m = _PATCH_MARK.search(log)
    if m:
        fc = _FILES_CHANGED.search(m.group("stat") or "")
        out["patch_files"] = int(fc.group("n")) if fc else 0
    return out


def _job_named(jobs: list[dict], name: str) -> dict | None:
    for j in jobs:
        if str(j.get("name") or "").strip().lower() == name:
            return j
    return None


def _files_of(commit: dict | None) -> list[dict]:
    if not commit:
        return []
    out = []
    for f in commit.get("files") or []:
        name = str(f.get("filename") or "")
        out.append(
            {
                "path": name[:RECEIPT_MAX_PATH_CHARS],
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
            }
        )
        if len(out) >= RECEIPT_MAX_FILES:
            break
    return out


def _claim_of(comments: list[dict], now: float) -> dict | None:
    """The claim of record on the instruction issue: a CLAIM comment, newest first.

    The pattern is not re-invented here -- it is the one `bin/claim-gate` refuses lanes
    against, taken from claims.py so the two cannot drift.
    """
    from fleetview_backend import claims

    best = None
    for c in comments:
        body = c.get("body") or ""
        for m in claims.CLAIM.finditer(body):
            hb = m.group("hb")
            age = claims._age_s(hb, now)
            row = {
                "role": m.group("agent"),
                "paths": [
                    p[:RECEIPT_MAX_PATH_CHARS] for p in m.group("paths").split(",")
                ][:RECEIPT_MAX_FILES],
                "heartbeat": hb,
                "age_s": None if age is None else round(age, 1),
                "live": age is not None and age < claims.MAX_AGE_S,
                "url": c.get("html_url"),
            }
            if best is None or (row["age_s"] is not None and best["age_s"] is None):
                best = row
            elif row["age_s"] is not None and best["age_s"] is not None:
                if row["age_s"] < best["age_s"]:
                    best = row
    return best


def _recovery(
    codes: list[str], model: dict[str, Any], run_url: str, lane_url: str | None
) -> list[dict]:
    """What to DO next, per reason. Every entry names an executable door, not an intention.

    A receipt that says "not verified" and stops there leaves the founder with a status and no
    way forward. Each code gets the door that resolves it: the run, the sealed artifact, the
    lane, or the re-dispatch that starts the mission again.
    """
    out: list[dict] = []
    seen: set[str] = set()

    def add(code: str, why: str, action: str, target: str, note: str = "") -> None:
        if code in seen:
            return
        seen.add(code)
        out.append(
            {
                "code": code,
                "why": why,
                "next": {"action": action, "target": target, "note": note},
            }
        )

    for code in codes:
        if code == "worker-did-not-start":
            add(
                code,
                "no worker ran",
                "read-the-run",
                run_url,
                "then re-dispatch the same task through workflow_dispatch of agent-sandbox.yml",
            )
        elif code == "in-flight":
            add(code, "the run is still working", "wait-for-the-run", run_url)
        elif code == "no-output":
            add(
                code,
                "the worker produced no changed file",
                "re-dispatch-with-a-named-change",
                run_url,
                "the task must name the file to change; a run with no diff is not a result",
            )
        elif code == "firewall-refused":
            add(
                code,
                "the epistemic firewall refused the worker's claims",
                "read-the-sealed-transcript",
                "the sealed artifact of this run (age-encrypted)",
                "the refused claims are in the artifact; fix the claim, then re-dispatch",
            )
        elif code == "firewall-absent":
            add(code, "no firewall job is recorded", "read-the-run-jobs", run_url)
        elif code == "not-landed":
            add(
                code,
                "the work is not on main",
                "read-the-lane",
                lane_url or run_url,
                "the Greenlane lands a green lane; its check status is the next fact",
            )
        elif code == "lane-submit-failed":
            add(code, "the lane submission failed", "read-the-lane-job", run_url)
        elif code == "claim-not-found":
            add(
                code,
                "no claim of record on the instruction issue",
                "read-the-instruction-issue",
                run_url,
                "the work is unclaimed until a CLAIM comment is posted",
            )
        elif code.startswith("conflict-"):
            add(code, "the run's own statuses disagree", "read-the-run-jobs", run_url)
        elif code == "instruction-unknown":
            add(code, "no instruction id", "read-the-run", run_url)
    cls = model.get("failure_class")
    if cls:
        add(
            f"provider-failure:{cls}",
            f"the first provider failed with class {cls}",
            "re-dispatch",
            run_url,
            "the bounded fallback already ran; the class says which provider failed and why",
        )
    return out[:RECEIPT_MAX_REASONS]


def project_receipt(
    *,
    run: dict,
    jobs: list[dict],
    log: str,
    lane_branch: str | None,
    lane_ref: dict | None,
    lane_commit: dict | None,
    pulls: list[dict],
    main_contains_lane: bool,
    instruction_id: int | None,
    claim: dict | None,
    workflow_pins: dict[str, Any],
    sources: list[dict],
    now: float,
) -> dict[str, Any]:
    """The receipt. Pure: the same evidence always gives the same receipt."""
    title = str(run.get("display_title") or "")
    tm = _RECEIPT_TITLE.match(title)
    harness = tm.group("harness") if tm else None
    task = (tm.group("task") if tm else title)[:RECEIPT_MAX_TASK_CHARS]

    agent_job = _job_named(jobs, "agent")
    firewall_job = _job_named(jobs, "firewall")
    lane_job = _job_named(jobs, "submit-lane") or _job_named(jobs, "open-pr")

    markers = _log_markers(log)
    run_status = str(run.get("status") or "")
    run_conclusion = str(run.get("conclusion") or "")

    # -- the stage ladder, each rung with the evidence that put it there --
    stages: dict[str, bool] = {s: False for s in RECEIPT_STAGES}
    evidence: dict[str, Any] = {}

    stages["queued"] = bool(run.get("id"))
    evidence["queued"] = {"source": "actions run", "run_id": run.get("id")}

    agent_started = bool(
        agent_job and str(agent_job.get("status") or "") in ("in_progress", "completed")
    )
    stages["started"] = agent_started
    if agent_job:
        evidence["started"] = {
            "source": "actions job (agent)",
            "status": agent_job.get("status"),
            "conclusion": agent_job.get("conclusion"),
        }

    lane_sha = ""
    if lane_ref:
        obj = lane_ref.get("object") or {}
        lane_sha = str(obj.get("sha") or "")
    changed = _files_of(lane_commit)
    base_sha = str(run.get("head_sha") or "")
    patch_from_commit = bool(lane_sha and lane_sha != base_sha and changed)
    patch_from_log = markers.get("patch_files")
    stages["patch_produced"] = bool(patch_from_commit or (patch_from_log or 0) > 0)
    if patch_from_commit:
        evidence["patch_produced"] = {
            "source": "lane commit (canonical git state)",
            "branch": lane_branch,
            "commit": lane_sha,
            "files_changed": len(changed),
        }
    elif (patch_from_log or 0) > 0:
        evidence["patch_produced"] = {
            "source": "agent job log (patch marker)",
            "files_changed": patch_from_log,
        }

    cif_ok = bool(firewall_job and firewall_job.get("conclusion") == "success")
    stages["cif_passed"] = cif_ok
    if firewall_job:
        evidence["cif_passed"] = {
            "source": "actions job (firewall)",
            "status": firewall_job.get("status"),
            "conclusion": firewall_job.get("conclusion"),
        }

    merged_pr = None
    for pr in pulls:
        state = "merged" if pr.get("merged_at") else str(pr.get("state") or "")
        if state == "merged":
            merged_pr = pr
            break
    landed = bool(merged_pr) or main_contains_lane
    stages["greenlane_landed"] = landed
    if merged_pr:
        evidence["greenlane_landed"] = {
            "source": "pull request merged",
            "pr": merged_pr.get("number"),
            "url": merged_pr.get("html_url"),
            "merge_commit": merged_pr.get("merge_commit_sha"),
        }
    elif main_contains_lane:
        evidence["greenlane_landed"] = {
            "source": "lane commit is in main's history",
            "commit": lane_sha,
        }

    # A merge is not a live effect. This projection reads no production receipt, so the honest
    # answer is false with the reason, not a green tick borrowed from the merge.
    stages["live_effect"] = False
    evidence["live_effect"] = {
        "source": "none",
        "reason": (
            "a merged lane is not a live effect; this projection reads no post-merge "
            "production receipt, so it does not claim one"
        ),
    }

    stage = RECEIPT_STAGES[0]
    for s in RECEIPT_STAGES:
        if stages[s]:
            stage = s
        else:
            break

    # -- the verdict, and the machine-readable reasons for it --
    codes: list[str] = []
    reasons: list[str] = []
    in_flight = run_status != "completed"
    if not agent_started:
        codes.append("worker-did-not-start")
        reasons.append(
            "no agent job has started: the mission is queued or the run never reached a worker"
        )
    elif in_flight:
        # A run that is still working has no result yet. Calling that "no output" would be a
        # verdict on work in flight, which is exactly the kind of lie this receipt exists to
        # refuse; the ladder below says which rungs are still open.
        codes.append("in-flight")
        reasons.append(
            "the run is still in progress: the worker has started and the result is not known yet"
        )
    elif not stages["patch_produced"]:
        codes.append("no-output")
        reasons.append(
            "the worker job ran but produced no changed file: a green run with no output is "
            "not a result"
        )
    if firewall_job and firewall_job.get("conclusion") == "failure":
        codes.append("firewall-refused")
        reasons.append("the epistemic firewall refused the worker's claims")
    elif not firewall_job and not in_flight:
        codes.append("firewall-absent")
        reasons.append("no epistemic firewall job is recorded for this run")
    if not landed and not in_flight:
        codes.append("not-landed")
        reasons.append(
            "the work is not on main: a branch, a pull request or a merge is not live"
        )
    if (
        run_conclusion == "success"
        and agent_job
        and agent_job.get("conclusion") == "failure"
    ):
        codes.append("conflict-run-succeeded-agent-failed")
        reasons.append("the run reports success while its agent job failed")
    if run_conclusion == "success" and agent_started and not stages["patch_produced"]:
        codes.append("conflict-run-succeeded-without-output")
        reasons.append("the run reports success but no changed file can be evidenced")
    if instruction_id is None:
        codes.append("instruction-unknown")
        reasons.append("no instruction id could be read for this run")
    if claim is None and not in_flight:
        codes.append("claim-not-found")
        reasons.append("no claim comment is recorded on the instruction issue")
    if lane_job and lane_job.get("conclusion") == "failure" and not landed:
        codes.append("lane-submit-failed")
        reasons.append(
            "the lane submission job failed, so the work never reached a branch"
        )

    verified = (
        stages["patch_produced"]
        and stages["cif_passed"]
        and stages["greenlane_landed"]
        and not [c for c in codes if c.startswith("conflict-")]
    )

    # -- the model, as evidenced --
    # The rule: the provider is what the log says, or nothing. A run title names the provider
    # that was REQUESTED ("agent (gemini)"), which is not evidence of the one that ran -- the
    # workflow falls back to another provider when the first fails, and the title does not
    # change. An unreadable log therefore yields no provider, never a guess.
    provider = markers.get("provider")
    provider_source = markers.get("provider_source")
    if provider is None and markers.get("harness_exit") is not None:
        # The step finished ("harness exit N") and no fallback marker is present: the harness
        # that was asked for is the provider that ran.
        provider = {
            "gemini": "google",
            "pi": "minimax",
            "claude-code": "anthropic",
        }.get(harness)
        provider_source = (
            "agent job log (no fallback marker; the requested harness ran)"
        )
    if provider is None:
        provider_source = (
            "not evidenced: the agent job's log could not be read, and the run title names the "
            "provider that was requested, not the one that ran"
        )
    pins = workflow_pins.get("providers") or {}
    model_name = None
    model_source = None
    if provider and provider in pins:
        model_name = pins[provider]
        model_source = f"workflow at {workflow_pins.get('sha')} ({WORKFLOW})"
    model = {
        "provider": provider,
        "provider_source": provider_source,
        "name": model_name,
        "name_source": model_source,
        "fallback": bool(markers.get("fallback")),
        "failed_provider": markers.get("failed_provider"),
        "failure_class": markers.get("failure_class"),
    }
    if provider and model_name is None:
        model["name_unknown_reason"] = (
            "the model was a dispatch input, and the Actions API does not publish a "
            "dispatch's inputs; the sealed transcript holds the exact model"
        )

    updated = (
        _epoch(run.get("updated_at"))
        or _epoch(run.get("run_started_at"))
        or _epoch(run.get("created_at"))
    )
    age = (now - updated) if updated else None
    freshness = {
        "read_at": _now_iso(now),
        "run_updated_at": run.get("updated_at"),
        "age_s": None if age is None else round(age, 1),
        "stale_after_s": RECEIPT_STALE_AFTER_S,
        "stale": bool(age is None or age > RECEIPT_STALE_AFTER_S),
    }

    receipt = {
        "schema": "estate.mission-receipt/1",
        "instruction_id": str(instruction_id) if instruction_id else None,
        "instruction_url": (
            f"https://github.com/{repo()}/issues/{instruction_id}"
            if instruction_id
            else None
        ),
        "title": task,
        "harness": harness,
        "run": {
            "run_id": run.get("id"),
            "url": run.get("html_url")
            or f"https://github.com/{repo()}/actions/runs/{run.get('id')}",
            "event": run.get("event"),
            "status": run_status,
            "conclusion": run_conclusion,
            "head_sha": base_sha or None,
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "triggered_by": (run.get("triggering_actor") or run.get("actor") or {}).get(
                "login"
            ),
        },
        "model": model,
        "source_sha": base_sha or None,
        "lane": {
            "branch": lane_branch,
            "commit": lane_sha or None,
            "url": f"https://github.com/{repo()}/tree/{lane_branch}"
            if lane_branch
            else None,
            "files_changed": changed,
        },
        "stage": stage,
        "stages": stages,
        "stage_evidence": evidence,
        "verification": {
            "status": "VERIFIED" if verified else "NOT VERIFIED",
            "scope": (
                "the mission produced a real changed file, passed the epistemic firewall, and "
                "landed on main"
            ),
            "codes": codes[:RECEIPT_MAX_REASONS],
            "reasons": reasons[:RECEIPT_MAX_REASONS],
        },
        "failure_class": model.get("failure_class"),
        "recovery": _recovery(
            codes,
            model,
            run.get("html_url")
            or f"https://github.com/{repo()}/actions/runs/{run.get('id')}",
            f"https://github.com/{repo()}/tree/{lane_branch}" if lane_branch else None,
        ),
        "operational": {
            "status": "NOT VERIFIED",
            "code": "no-live-effect-evidence",
            "reason": (
                "a landed lane is not a live effect; nothing in this projection evidences a "
                "running system, so nothing is claimed"
            ),
        },
        "provenance": {
            "role": (claim or {}).get("role") or harness,
            "scope": (claim or {}).get("paths"),
            "claim_url": (claim or {}).get("url"),
            "claim_heartbeat": (claim or {}).get("heartbeat"),
            "claim_age_s": (claim or {}).get("age_s"),
            "claim_live": (claim or {}).get("live"),
            "claim_source": "CLAIM comment on the instruction issue",
        },
        "freshness": freshness,
        "sources": sources,
    }
    safe, found = redact.redact(json.dumps(receipt))
    if found:
        # A receipt is public metadata. If anything secret-shaped reached it, the honest move is
        # to refuse the receipt, not to publish it with the finding hidden.
        raise ReceiptRefused(
            502,
            "evidence-redacted",
            "the projected evidence looks like it holds a secret ("
            + ", ".join(sorted(set(found)))
            + "); the receipt was refused rather than published",
        )
    return json.loads(safe)


# -- the collection. Reads the canonical state, then projects it. --


def _find_run_for_instruction(instruction_id: int) -> dict:
    """The run that carries this instruction, found by the run title (the workflow's record)."""
    body = (
        _receipt_get(f"/repos/{repo()}/actions/workflows/{WORKFLOW}/runs?per_page=50")
        or {}
    )
    runs = list(body.get("workflow_runs") or [])
    for r in runs:
        title = str(r.get("display_title") or "")
        m = _RECEIPT_TITLE.match(title)
        if not m:
            continue
        n = _RECEIPT_ISSUE_IN_TITLE.search(m.group("task"))
        if n and int(n.group("n")) == instruction_id:
            return r
    raise ReceiptRefused(
        404,
        "run-not-found",
        f"no {WORKFLOW} run carries instruction {instruction_id}.",
    )


def receipt(
    run_id: Any = None,
    instruction_id: Any = None,
    now: float | None = None,
) -> tuple[dict[str, Any], int]:
    """One mission's receipt. Returns (receipt, HTTP status); raises ReceiptRefused."""
    t = now if now is not None else time.time()
    if not run_id and not instruction_id:
        raise ReceiptRefused(
            400, "no-mission", "Say which mission: pass a run id or an instruction id."
        )
    sources: list[dict] = []

    def note(kind: str, url: str) -> None:
        sources.append({"kind": kind, "url": url})

    if run_id:
        run = _run(int(run_id))
    else:
        run = _find_run_for_instruction(int(instruction_id))
        run_id = run.get("id")
    note(
        "actions_run",
        run.get("html_url") or f"https://github.com/{repo()}/actions/runs/{run_id}",
    )

    title = str(run.get("display_title") or "")
    tm = _RECEIPT_TITLE.match(title)
    harness = tm.group("harness") if tm else None
    task_text = tm.group("task") if tm else title
    found_instruction = _RECEIPT_ISSUE_IN_TITLE.search(task_text)
    instruction = int(found_instruction.group("n")) if found_instruction else None
    if instruction_id and instruction and int(instruction_id) != instruction:
        raise ReceiptRefused(
            409,
            "instruction-mismatch",
            f"run {run_id} carries instruction {instruction}, not {instruction_id}.",
        )
    if not instruction and instruction_id:
        instruction = int(instruction_id)

    jobs = _jobs(int(run_id))
    note("actions_jobs", f"https://github.com/{repo()}/actions/runs/{run_id}")

    agent_job = _job_named(jobs, "agent")
    log = _job_log((agent_job or {}).get("id"))
    if agent_job:
        note(
            "agent_job_log",
            f"https://github.com/{repo()}/actions/runs/{run_id}",
        )

    branch = _lane_branch(harness, run_id)
    lane_ref = _ref(branch) if branch else None
    lane_commit = None
    lane_sha = ""
    if lane_ref:
        lane_sha = str((lane_ref.get("object") or {}).get("sha") or "")
        if lane_sha:
            lane_commit = _commit(lane_sha)
            note("lane_commit", f"https://github.com/{repo()}/commit/{lane_sha}")
    pulls = _pulls(branch) if branch else []
    if pulls:
        note("pull_request", str(pulls[0].get("html_url") or ""))

    main_contains_lane = False
    base_sha = str(run.get("head_sha") or "")
    if lane_sha and base_sha:
        cmp = _compare(base_sha, "main")
        main_contains_lane = any(
            str(c.get("sha") or "").startswith(lane_sha[:12])
            for c in cmp.get("commits") or []
        )
        if main_contains_lane:
            note("compare", f"https://github.com/{repo()}/compare/{base_sha}...main")

    claim = None
    if instruction:
        comments = _issue_comments(instruction)
        note("instruction_issue", f"https://github.com/{repo()}/issues/{instruction}")
        claim = _claim_of(comments, t)

    pins = (
        _workflow_pins(base_sha)
        if base_sha
        else {"providers": {}, "sha": None, "read": False}
    )

    body = project_receipt(
        run=run,
        jobs=jobs,
        log=log,
        lane_branch=branch,
        lane_ref=lane_ref,
        lane_commit=lane_commit,
        pulls=pulls,
        main_contains_lane=main_contains_lane,
        instruction_id=instruction,
        claim=claim,
        workflow_pins=pins,
        sources=sources,
        now=t,
    )
    return body, 200


def receipt_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="mission-receipt",
        description="Print one mission receipt as JSON (the read model the Founder Surface reads).",
    )
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--instruction-id", default=None)
    args = ap.parse_args(argv)
    try:
        body, _status = receipt(run_id=args.run_id, instruction_id=args.instruction_id)
    except ReceiptRefused as exc:
        print(json.dumps({"error": str(exc), "code": exc.code}), file=sys.stderr)
        return 1
    print(json.dumps(body, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(receipt_main())
