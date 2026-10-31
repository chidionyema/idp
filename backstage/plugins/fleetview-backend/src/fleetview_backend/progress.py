"""FleetView: the estate's progress report, as its one writer produced it.

The report is written by `bin/estate-progress` -- the estate's clock (the scheduled workflow) or
the writer on demand -- and published to the estate bucket. This module is a READER: it serves
the report the writer produced and never measures anything itself. That is the whole point of the
split: one measurement, many mouths, so /fleet, the voice, the Telegram door and any agent all
describe the same estate.

A report that cannot be read is `available: false` with its reason, never an empty board. An
empty board would say "the estate is not progressing", which is a different claim from "nobody
could look".
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

CACHE_S = 30
_refresh_lock = threading.Lock()
_cache: dict[str, Any] = {"at": 0.0, "body": None}
REPORT_PATH = Path.home() / ".estate" / "progress" / "estate-progress.json"


def _idp_root() -> Path:
    """The tree this module runs from, unless ESTATE_IDP_ROOT names another.

    The same rule fleetview_backend/greenlane.py follows: the backend runs from
    ~/.estate/runtime/idp (synced to main), so the code and the tool come from one tree.
    """
    env = os.environ.get("ESTATE_IDP_ROOT")
    if env:
        return Path(os.path.expanduser(env))
    # <root>/backstage/plugins/fleetview-backend/src/fleetview_backend/progress.py
    return Path(__file__).resolve().parents[5]


def _report_path() -> Path:
    override = os.environ.get("ESTATE_PROGRESS_REPORT")
    return Path(os.path.expanduser(override)) if override else REPORT_PATH


def _read_report_file() -> dict[str, Any] | None:
    path = _report_path()
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _fetch_report() -> dict[str, Any] | None:
    """Ask the writer for the report it published (its cache, or the bucket)."""
    tool = _idp_root() / "bin/estate-progress"
    if not tool.exists():
        return None
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            ["python3", str(tool), "--read", "--json"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        doc = json.loads(proc.stdout)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def _body_from(doc: dict[str, Any] | None, error: str) -> dict[str, Any]:
    if not doc:
        return {"available": False, "error": error}
    return {"available": True, "report": doc}


def progress_snapshot(now: float | None = None) -> dict[str, Any]:
    """The report, served from the local file the writer left, or the published one.

    The read is a file read plus, on a cold cache, the writer's own published copy. The refresh
    happens off the request path (see progress_snapshot_nowait) so a founder's page never waits
    on a measurement.
    """
    t = now if now is not None else time.time()
    body = _cache.get("body")
    if body is not None and t - _cache["at"] < CACHE_S:
        return body
    doc = _read_report_file() or _fetch_report()
    if doc is None:
        body = {
            "available": False,
            "error": "no progress report at %s; the writer has not run"
            % _report_path(),
        }
    else:
        body = _body_from(doc, "")
    body["read_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    _cache.update(at=t, body=body)
    return body


def progress_snapshot_nowait(now: float | None = None) -> dict[str, Any]:
    """The cached report at once, refreshed off the request path.

    The same contract as fleetview_backend.greenlane.greenlane_status_nowait: a caller that
    joins several readers (the /estate strip, the voice brief) must not wait on a measurement.
    """
    t = now if now is not None else time.time()
    body = _cache.get("body")
    if body is not None and t - _cache["at"] < CACHE_S:
        return body
    if _refresh_lock.acquire(blocking=False):

        def _run() -> None:
            try:
                progress_snapshot()
            finally:
                _refresh_lock.release()

        threading.Thread(target=_run, daemon=True, name="progress-refresh").start()
    if body is not None:
        return body
    return {"available": False, "error": "first progress read in flight"}
