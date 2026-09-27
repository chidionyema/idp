"""Fleet is the founder's surface for work, delegation and monitoring. This module shows, live,
(1) merged -> operating for the laptop plane: the root-owned converger under /usr/local/estate
(docs/tickets/2026-09-27-merged-is-operating.md), and (2) the health of every estate launchd job,
because on 2026-09-27 26 of 41 jobs were failing silently.
"""

from __future__ import annotations

import json
import os
import plistlib
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SILENT_S = 900
SLOW_S = 900
DEFAULT_PREFIX = "/usr/local/estate"
DAEMON_PLIST = "/Library/LaunchDaemons/ai.estate.converge.plist"
JOB_PREFIXES = ("ai.", "com.estate.", "com.founder.", "com.chidionyema.")

INTERPRETERS = {"python", "python3", "bash", "sh", "zsh", "node", "env"}


def _is_interpreter(basename: str) -> bool:
    return basename in INTERPRETERS or basename.startswith("python")


def _parse(ts: Any) -> datetime | None:
    if not ts:
        return None
    try:
        text = str(ts)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_state(prefix: Path) -> dict[str, Any] | None:
    path = prefix / "converge" / "state.json"
    try:
        text = path.read_text()
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _load_converges(prefix: Path) -> list[dict[str, Any]]:
    path = prefix / "converge" / "ledger.jsonl"
    try:
        text = path.read_text()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return list(reversed(rows[-20:]))


def _load_unmerged_runs(home: Path) -> list[dict[str, Any]]:
    db = home / ".estate" / "estate.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return []
    try:
        cur = conn.execute(
            """
            SELECT id, intent, harness, started_at, status
            FROM intent_tickets
            WHERE harness IN ('unmerged', 'unconverged')
               OR harness LIKE '%+unmerged'
               OR harness LIKE '%+unconverged'
            ORDER BY started_at DESC
            LIMIT 20
            """
        )
        rows = cur.fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "intent": r[1],
            "harness": r[2],
            "started_at": r[3],
            "status": r[4],
        }
        for r in rows
    ]


def _load_delegate(home: Path) -> list[dict[str, Any]]:
    base = home / ".estate" / "delegate"
    try:
        entries = list(base.glob("*/results.json"))
    except OSError:
        return []
    scored: list[tuple[float, Path]] = []
    for entry in entries:
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        scored.append((mtime, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    results: list[dict[str, Any]] = []
    for _mtime, entry in scored[:10]:
        try:
            data = json.loads(entry.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        slug = entry.parent.name
        # delegate-build writes {step_id: {done, attempts, empirical, scratchpad, usage}}.
        steps_out: list[dict[str, Any]] = []
        for step_id, step in sorted(data.items()):
            if not isinstance(step, dict):
                continue
            empirical = step.get("empirical")
            last_check_rc = None
            if isinstance(empirical, list) and empirical:
                last = empirical[-1]
                if isinstance(last, dict):
                    last_check_rc = _as_int(last.get("check_rc"))
            steps_out.append(
                {
                    "id": step_id,
                    "done": step.get("done"),
                    "attempts": _as_int(step.get("attempts")),
                    "last_check_rc": last_check_rc,
                }
            )
        results.append({"slug": slug, "steps": steps_out})
    return results


def jobs(agents_dir: Path, launchctl_text: str) -> list[dict[str, Any]]:
    """Health of every estate launchd job in `agents_dir`, cross-referenced with a
    `launchctl list` dump. A job's plist may point at a file the release converger
    has since removed; that mismatch is exactly what `program_exists` surfaces."""
    running: dict[str, tuple[int | None, int | None]] = {}
    for line in launchctl_text.splitlines():
        if line.startswith("PID"):
            continue
        parts = line.split()
        if len(parts) != 3:
            continue
        pid_raw, status_raw, label = parts
        running[label] = (_as_int(pid_raw), _as_int(status_raw))

    try:
        plist_paths = sorted(agents_dir.glob("*.plist"))
    except OSError:
        plist_paths = []

    result: list[dict[str, Any]] = []
    for plist_path in plist_paths:
        try:
            with plist_path.open("rb") as fh:
                data = plistlib.load(fh)
        except (OSError, plistlib.InvalidFileException):
            continue
        label = data.get("Label")
        if not label or not label.startswith(JOB_PREFIXES):
            continue

        program: str | None = None
        args = data.get("ProgramArguments")
        if isinstance(args, list) and args:
            first = args[0]
            basename = Path(str(first)).name
            if _is_interpreter(basename):
                for arg in args[1:]:
                    if str(arg).startswith("/"):
                        program = str(arg)
                        break
            else:
                program = str(first)
        if program is None:
            single = data.get("Program")
            if single:
                program = str(single)

        program_exists = bool(program) and os.path.exists(program)

        repo = None
        if program:
            current = Path(program).parent
            while True:
                if (current / ".git").exists():
                    repo = str(current)
                    break
                if str(current) == "/" or current == current.parent:
                    break
                current = current.parent

        in_release = bool(program) and program.startswith("/usr/local/estate/")

        pid, status = running.get(label, (None, None))
        if not program_exists:
            health = "orphan"
        elif label not in running:
            health = "not-loaded"
        elif pid is not None:
            health = "running"
        elif status in (0, None):
            health = "ok"
        else:
            health = "failing"

        result.append(
            {
                "label": label,
                "pid": pid,
                "last_exit": status,
                "program": program,
                "program_exists": program_exists,
                "repo": repo,
                "in_release": in_release,
                "health": health,
            }
        )
    return result


def _launchctl_list() -> str:
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            ["launchctl", "list"],  # noqa: S607 -- launchctl resolves from PATH on purpose
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    return proc.stdout or ""


def delivery(
    home: Path | None = None,
    now: datetime | None = None,
    prefix: Path | None = None,
    daemon_plist: Path | None = None,
    agents_dir: Path | None = None,
    launchctl_text: str | None = None,
) -> dict[str, Any]:
    home = home if home is not None else Path.home()
    now = now if now is not None else datetime.now(timezone.utc)
    prefix = (
        prefix
        if prefix is not None
        else Path(os.environ.get("ESTATE_PREFIX") or DEFAULT_PREFIX)
    )
    daemon_plist = daemon_plist if daemon_plist is not None else Path(DAEMON_PLIST)
    agents_dir = agents_dir if agents_dir is not None else home / "Library/LaunchAgents"
    if launchctl_text is None:
        launchctl_text = _launchctl_list()

    state = _load_state(prefix)
    converges = _load_converges(prefix)
    unmerged_runs = _load_unmerged_runs(home)
    delegate = _load_delegate(home)
    job_list = jobs(agents_dir, launchctl_text)

    alerts: list[dict[str, str]] = []

    if not daemon_plist.exists():
        alerts.append(
            {
                "level": "red",
                "code": "converger-not-installed",
                "text": "IDP-Estate.pkg has not installed the converger daemon",
            }
        )
    elif state is None:
        alerts.append(
            {"level": "red", "code": "converger-missing", "text": "converger-missing"}
        )

    if state is not None:
        checked_at = _parse(state.get("checked_at"))
        if checked_at is not None and (now - checked_at).total_seconds() > SILENT_S:
            alerts.append(
                {"level": "red", "code": "converger-silent", "text": "converger-silent"}
            )

        last_error = state.get("last_error")
        if last_error:
            alerts.append(
                {
                    "level": "red",
                    "code": "fetch-failing",
                    "text": f"fetch-failing: {last_error}",
                }
            )

        if state.get("behind"):
            alerts.append({"level": "amber", "code": "behind", "text": "behind"})

        drift = state.get("drift")
        if drift:
            alerts.append(
                {
                    "level": "amber",
                    "code": "drift",
                    "text": f"drift: {', '.join(map(str, drift))}",
                }
            )

    if converges:
        newest = converges[0]
        latency_s = newest.get("latency_s")
        if isinstance(latency_s, (int, float)) and latency_s > SLOW_S:
            alerts.append({"level": "amber", "code": "slow", "text": "slow"})

    for row in unmerged_runs:
        started_at = _parse(row.get("started_at"))
        if started_at is not None and (now - started_at) < timedelta(hours=24):
            alerts.append({"level": "amber", "code": "unmerged", "text": "unmerged"})
            break

    failing = [j for j in job_list if j["health"] == "failing"]
    if failing:
        text = f"{len(failing)} failing: " + ", ".join(
            f"{j['label']}({j['last_exit']})" for j in failing
        )
        alerts.append({"level": "red", "code": "jobs-failing", "text": text})

    orphaned = [j for j in job_list if j["health"] == "orphan"]
    if orphaned:
        text = "orphaned: " + ", ".join(j["label"] for j in orphaned)
        alerts.append({"level": "amber", "code": "jobs-orphaned", "text": text})

    has_red = any(a["level"] == "red" for a in alerts)
    operating = (not has_red) and state is not None and not state.get("behind")

    return {
        "state": state,
        "converges": converges,
        "unmerged_runs": unmerged_runs,
        "delegate": delegate,
        "jobs": job_list,
        "alerts": alerts,
        "operating": operating,
        "checked_at": now.isoformat(),
    }


def delivery_envelope() -> tuple[dict[str, Any], int]:
    try:
        return delivery(), 200
    except Exception as exc:
        return {"available": False, "error": str(exc)}, 503
