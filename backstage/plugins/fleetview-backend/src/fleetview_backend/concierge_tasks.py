"""Concierge tasks: a browser task for the founder, started from Fleet or by voice, watched live.

The task runs on the laptop through the committed `concierge-task` intent (estate-execute), which
drives the founder's Chrome with mums-concierge and appends every event, as it happens, to
`~/.estate/concierge-tasks/<task_id>.jsonl`: a `goal` line first, then `plan` / `act` / `found` /
`hold` ... lines, and a `result` line last. This module starts a task (detached, so the request
returns in milliseconds and the browser keeps going) and reads those files back for the page.
Nothing here talks to the browser or the router; the intent does, and this only reads what it wrote.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any

MAX_GOAL_CHARS = 1000
STALE_AFTER_S = 20 * 60  # a task with no result line and no new event for this long is not running
TAIL_EVENTS = 14

_ENV_DIR = "FLEETVIEW_CONCIERGE_DIR"
_ENV_EXE = "ESTATE_EXECUTE"


class TaskRefused(Exception):
    """A refusal the page shows as it is. `status` is the HTTP status the route answers with."""

    def __init__(self, text: str, status: int = 400) -> None:
        super().__init__(text)
        self.status = status


def tasks_dir() -> Path:
    return Path(os.path.expanduser(os.environ.get(_ENV_DIR) or "~/.estate/concierge-tasks"))


def executor() -> str | None:
    exe = os.path.expanduser(os.environ.get(_ENV_EXE) or "~/.estate/bin/estate-execute")
    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        return exe
    return None


def validate(goal: Any) -> str:
    goal = str(goal or "").strip()
    if not goal:
        raise TaskRefused("Say what the concierge should do.")
    if len(goal) > MAX_GOAL_CHARS:
        raise TaskRefused(f"That is over {MAX_GOAL_CHARS} characters; say it shorter.")
    return goal


def new_task_id(now: float | None = None) -> str:
    return f"{int(now or time.time())}-{secrets.token_hex(2)}"


def start(goal: Any, url: str = "", by: str = "") -> dict:
    """Start a task through the intent and return its id at once. The browser runs on; the page
    and the voice both watch the events file from here."""
    goal = validate(goal)
    exe = executor()
    if not exe:
        raise TaskRefused("The concierge runs on the laptop only.", 503)
    task_id = new_task_id()
    directory = tasks_dir()
    directory.mkdir(parents=True, exist_ok=True)
    argv = [exe, "concierge-task", f"goal={goal}", f"task_id={task_id}"]
    if url:
        argv.append(f"url={url}")
    log = directory / f"{task_id}.log"
    try:
        with log.open("ab") as out:
            out.write(f"started by {by or 'fleet'}\n".encode())
            # argv list, no shell; detached in its own session so the request returns now and the
            # executor's own timeout, not ours, bounds the browser.
            subprocess.Popen(  # noqa: S603
                argv,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except OSError as exc:
        raise TaskRefused(f"The concierge could not start: {type(exc).__name__}.", 500) from exc
    return {"task_id": task_id, "goal": goal, "by": by or "fleet", "state": "running"}


def _read_lines(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue  # a half-written line at the tail: the next read sees it whole
        if isinstance(d, dict):
            out.append(d)
    return out


def task_from_file(path: Path, now: float | None = None) -> dict:
    now = now or time.time()
    lines = _read_lines(path)
    goal = next((d for d in lines if d.get("kind") == "goal"), {})
    result = next((d for d in reversed(lines) if d.get("kind") == "result"), None)
    events = [d for d in lines if d.get("kind") not in ("goal", "result")]
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = now
    if result:
        outcome = str(result.get("outcome") or "")
        state = "done" if result.get("success") else ("held" if outcome in ("held", "needs_human") else "failed")
    elif now - mtime > STALE_AFTER_S:
        state, outcome = "failed", "stale"
    else:
        state, outcome = "running", "running"
    last = events[-1] if events else goal
    return {
        "task_id": path.stem,
        "goal": str(goal.get("text") or ""),
        "started_at": float(goal.get("at") or mtime),
        "updated_at": mtime,
        "state": state,
        "outcome": outcome,
        "summary": str((result or {}).get("summary") or ""),
        "last": str(last.get("text") or "") if last else "",
        "last_kind": str(last.get("kind") or "") if last else "",
        "url": str((result or {}).get("final_url") or (last or {}).get("url") or goal.get("url") or ""),
        "steps": int((result or {}).get("steps") or (events[-1].get("step", 0) if events else 0)),
        "found": [e.get("text") for e in events if e.get("kind") == "found"],
        "receipt": (result or {}).get("receipt_image_path"),
        "events": [
            {"step": e.get("step", 0), "kind": e.get("kind", ""), "text": e.get("text", "")}
            for e in events[-TAIL_EVENTS:]
        ],
    }


def list_tasks(limit: int = 8, now: float | None = None) -> tuple[dict, int]:
    directory = tasks_dir()
    if not executor():
        return {"available": False, "error": "The concierge runs on the laptop only.", "tasks": []}, 503
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True) if directory.is_dir() else []
    tasks = [task_from_file(p, now) for p in files[: max(1, min(limit, 30))]]
    return {"available": True, "error": None, "tasks": tasks}, 200


def handle_post(body: Any) -> tuple[dict, int]:
    """POST /concierge-tasks: the page's JSON in, (task or {"error": sentence}, status) out."""
    if not isinstance(body, dict):
        return {"error": "Send JSON: {goal, url, by}."}, 400
    try:
        return start(body.get("goal"), str(body.get("url") or ""), str(body.get("by") or "")), 201
    except TaskRefused as exc:
        return {"error": str(exc)}, exc.status
