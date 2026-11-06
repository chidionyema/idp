#!/usr/bin/env python3
"""The estate incident loop: one error -> one ticket -> one priority -> one dispatch -> one lesson.

WHY. The estate master epic (docs/epics/2026-10-25-estate-master-epic.md, R-14) asks for
"an error results in a ticket being raised, prioritised, assigned and depending on capacity
an agent is automatically launched". Its own coverage table records R-14 as missing, with the
reason measured: "no path from a red CI job to an owned ticket to a dispatched agent (C-03)".

The estate already had every part of that path, separately: .github/workflows/flux-events.yml
opens a P0 issue per fire, bin/claim-open claims it, lane-submit hands the branch to the
Greenlane, platform/queue/dispatcher.py holds a task table for a worker, and
sovereign/engine/workflow.py runs one Temporal session per agent. What did not exist was the
join, and two things inside the join did not exist at all: a priority function (the queue's
tasks table has no priority column) and one incident record (there were four ledgers: the
intent-run ledger, claim issues, work-audit findings and Greenlane lanes - epic F-05).

WHAT THIS IS. One loop, one ledger, one policy:

    sense -> fingerprint -> one ledger row -> score -> one ticket with the score's label
          -> dispatch (bus session when the bus answers and a session is free, otherwise the
             estate's own task queue for a worker) -> verify (the error is gone) -> lesson
             (the estate graph) -> MTTR measured from first_seen to verified

Every stage is real. The sensors read real failures: red GitHub Actions runs on the watched
repos, and the executor's own refusal ledger (~/.estate/friction/events.jsonl). The dispatch
leg starts a real session on the sovereign bus (bin/sb start) or hands the work to the estate's
real task queue (platform/queue/dispatcher.py). The lesson is written to the estate's knowledge
graph. Nothing here is a simulation and nothing here waits for a human: `tick` is what the
laptop watcher runs every five minutes.

THE ONE RULE. This file decides priority and dispatch; nothing else may. A second priority
function is a second convention, which is what AGENTS.md §6 calls stitching.

    bin/estate-incident-loop tick          # the whole loop, one pass
    bin/estate-incident-loop sense         # what the sensors see right now
    bin/estate-incident-loop list          # the ledger
    bin/estate-incident-loop show <id>     # one incident
    bin/estate-incident-loop report --title "..." --severity major --url "..."
    bin/estate-incident-loop drill seed|fix|status
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_clock_guard():
    """Load the sibling clock-guard module by path.

    The estate runtime mirror keeps libexec/incident-loop.py and libexec/clock-guard.py side by
    side, and the mirror is not always importable as a package, so the sibling is loaded by
    path rather than by name."""
    path = Path(__file__).resolve().parent / "clock-guard.py"
    spec = importlib.util.spec_from_file_location("clock_guard", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load clock-guard.py next to {__file__}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clock_guard = _load_clock_guard()

IDP = Path(__file__).resolve().parents[3]
ESTATE_HOME = Path(os.environ.get("ESTATE_HOME", Path.home() / ".estate"))
LEDGER = ESTATE_HOME / "state" / "incidents.db"
POLICY_PATHS = [
    IDP / "catalog" / "incident-policy.json",
    ESTATE_HOME / "runtime" / "idp" / "catalog" / "incident-policy.json",
]
_STATE_CACHE: dict[str, tuple[float, dict]] = {}


class PolicyError(RuntimeError):
    """The policy file is missing or does not say what the loop needs."""


class LoopError(RuntimeError):
    """A stage of the loop could not do its job."""


# --------------------------------------------------------------------------------------
# policy
# --------------------------------------------------------------------------------------


def load_policy(path: Path | None = None) -> dict:
    """The one policy. Refuses rather than guessing a default."""
    candidates = [path] if path else POLICY_PATHS
    for candidate in candidates:
        if candidate and candidate.exists():
            with candidate.open(encoding="utf-8") as fh:
                policy = json.load(fh)
            for key in (
                "severities",
                "blast_radius",
                "age",
                "capacity_cost",
                "label_thresholds",
                "dispatch",
                "sense",
            ):
                if key not in policy:
                    raise PolicyError(f"policy {candidate} has no {key!r}")
            policy["_path"] = str(candidate)
            return policy
    raise PolicyError(f"no incident policy at any of {[str(c) for c in candidates]}")


def label_for(policy: dict, score: float) -> str:
    """The label whose threshold the score reaches. Highest first."""
    for label, threshold in sorted(
        policy["label_thresholds"].items(), key=lambda kv: -kv[1]
    ):
        if score >= threshold:
            return label
    return sorted(
        policy["label_thresholds"], key=lambda k: policy["label_thresholds"][k]
    )[0]


def score_incident(
    policy: dict,
    severity: str,
    blast: str,
    age_hours: float = 0.0,
    capacity_minutes: float = 0.0,
) -> tuple[float, str]:
    """The priority function of R-14: severity + blast radius + age + capacity cost.

    Age counts up (an unowned failure is worse every hour it stays open) and capacity cost
    counts up (a cheap fix is a quick win). Both are capped, so one dimension can never
    outvote the severity that opened the incident.
    """
    if severity not in policy["severities"]:
        raise PolicyError(f"unknown severity {severity!r}")
    if blast not in policy["blast_radius"]:
        raise PolicyError(f"unknown blast radius {blast!r}")
    base = float(policy["severities"][severity]["base"])
    blast_points = float(policy["blast_radius"][blast]["weight"])
    age_points = min(
        float(policy["age"]["max"]),
        float(policy["age"]["per_hour"]) * max(0.0, age_hours),
    )
    cost_points = min(
        float(policy["capacity_cost"]["max"]),
        float(policy["capacity_cost"]["per_10m"]) * (max(0.0, capacity_minutes) / 10.0),
    )
    total = base + blast_points + age_points + cost_points
    return total, label_for(policy, total)


def sla_minutes(policy: dict, label: str) -> int:
    return int(policy.get("sla_by_label", {}).get(label, 60))


def mttr_seconds(first_seen: str, verified_at: str) -> int:
    """MTTR of one incident: how long the error was open before it was verified."""
    return int((parse_iso(verified_at) - parse_iso(first_seen)).total_seconds())


# --------------------------------------------------------------------------------------
# ledger: one record type
# --------------------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  severity TEXT NOT NULL,
  blast TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL DEFAULT '',
  repo TEXT NOT NULL DEFAULT '',
  detail TEXT NOT NULL DEFAULT '{}',
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  label TEXT NOT NULL DEFAULT 'P2',
  sla_minutes INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL DEFAULT 'open',
  ticket INTEGER,
  dispatch_leg TEXT NOT NULL DEFAULT '',
  dispatch_ref TEXT NOT NULL DEFAULT '',
  dispatched_at TEXT,
  verified_at TEXT,
  closed_at TEXT,
  mttr_seconds INTEGER,
  lesson TEXT NOT NULL DEFAULT '',
  history TEXT NOT NULL DEFAULT '[]'
);
"""


def open_ledger(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path) if path else LEDGER
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def wall_now() -> datetime:
    """The estate's trusted wall clock.

    The host clock is not trusted by default: on 2026-10-29 it read 2024-01-01 for about
    nineteen minutes and every timestamp the estate wrote in that window was wrong. clock-guard
    judges the wall clock against the last trusted reading (the anchor) and the estate's own
    incident ledger, and uses the kernel's boot record only as a consistency check, because on
    macOS the boot record follows the wall clock through a step. When they disagree, this
    returns the projection instead of the regressed clock.
    """
    return datetime.fromtimestamp(clock_guard.trusted_epoch(), tz=timezone.utc)


def now_iso() -> str:
    return wall_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fingerprint(source: str, repo: str, key: str) -> str:
    """One error, one id. The same failure sensed twice is the same incident."""
    raw = f"{source}|{repo}|{key}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def record_incident(
    conn: sqlite3.Connection,
    incident: dict,
    policy: dict,
    capacity_minutes: float = 0.0,
) -> sqlite3.Row:
    """Insert or refresh one incident and re-score it. Returns the row."""
    now = now_iso()
    row = conn.execute(
        "SELECT * FROM incidents WHERE id = ?", (incident["id"],)
    ).fetchone()
    age_hours = 0.0
    if row:
        age_hours = (
            parse_iso(now) - parse_iso(row["first_seen"])
        ).total_seconds() / 3600.0
    score, label = score_incident(
        policy,
        incident["severity"],
        incident["blast"],
        age_hours,
        capacity_minutes,
    )
    detail = incident.get("detail", {})
    if row:
        history = json.loads(row["history"] or "[]")
        history.append({"at": now, "event": "seen"})
        history = history[-50:]
        conn.execute(
            """UPDATE incidents SET last_seen = ?, severity = ?, blast = ?, title = ?,
               url = ?, repo = ?, detail = ?, score = ?, label = ?, sla_minutes = ?,
               history = ? WHERE id = ?""",
            (
                now,
                incident["severity"],
                incident["blast"],
                incident["title"],
                incident.get("url", ""),
                incident.get("repo", ""),
                json.dumps(detail),
                score,
                label,
                sla_minutes(policy, label),
                json.dumps(history),
                incident["id"],
            ),
        )
    else:
        conn.execute(
            """INSERT INTO incidents (id, source, severity, blast, title, url, repo, detail,
               first_seen, last_seen, score, label, sla_minutes, state, history)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
            (
                incident["id"],
                incident["source"],
                incident["severity"],
                incident["blast"],
                incident["title"],
                incident.get("url", ""),
                incident.get("repo", ""),
                json.dumps(detail),
                now,
                now,
                score,
                label,
                sla_minutes(policy, label),
                json.dumps([{"at": now, "event": "opened"}]),
            ),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM incidents WHERE id = ?", (incident["id"],)
    ).fetchone()
    return row


UPDATE_ALL = """UPDATE incidents SET severity=?, blast=?, title=?, url=?, repo=?, detail=?,
       score=?, label=?, sla_minutes=?, state=?, ticket=?, dispatch_leg=?, dispatch_ref=?,
       dispatched_at=?, verified_at=?, closed_at=?, mttr_seconds=?, lesson=?, first_seen=?,
       last_seen=?, history=? WHERE id=?"""


def set_field(conn: sqlite3.Connection, incident_id: str, **fields: object) -> None:
    """Change one incident. A fixed statement: the column list is this file's, not a caller's."""
    row = conn.execute(
        "SELECT * FROM incidents WHERE id = ?", (incident_id,)
    ).fetchone()
    if row is None:
        return
    history = json.loads(row["history"] or "[]")
    event = str(fields.pop("event", "update"))
    history.append({"at": now_iso(), "event": event})
    history = history[-50:]
    values = {key: row[key] for key in row.keys()}
    values.update(fields)
    conn.execute(
        UPDATE_ALL,
        (
            values["severity"],
            values["blast"],
            values["title"],
            values["url"],
            values["repo"],
            values["detail"],
            values["score"],
            values["label"],
            values["sla_minutes"],
            values["state"],
            values["ticket"],
            values["dispatch_leg"],
            values["dispatch_ref"],
            values["dispatched_at"],
            values["verified_at"],
            values["closed_at"],
            values["mttr_seconds"],
            values["lesson"],
            values["first_seen"],
            values["last_seen"],
            json.dumps(history),
            incident_id,
        ),
    )
    conn.commit()


def get_incident(conn: sqlite3.Connection, incident_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM incidents WHERE id = ?", (incident_id,)
    ).fetchone()


def list_incidents(
    conn: sqlite3.Connection, state: str = "", limit: int = 50
) -> list[sqlite3.Row]:
    if state:
        return conn.execute(
            "SELECT * FROM incidents WHERE state = ? ORDER BY score DESC LIMIT ?",
            (state, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM incidents ORDER BY score DESC LIMIT ?", (limit,)
    ).fetchall()


# --------------------------------------------------------------------------------------
# sensors: real errors, no simulation
# --------------------------------------------------------------------------------------


def run_gh(args: list[str], timeout: int = 45) -> tuple[int, str, str]:
    """gh, read-only. Every gh call here is a GET."""
    argv = ["gh", *args]  # noqa: S607 -- gh is on PATH; the estate's own CLI
    try:
        env = dict(os.environ)
        env["GH_REPO"] = str(load_policy()["dispatch"]["repo"])
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            argv, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return proc.returncode, proc.stdout, proc.stderr


def sense_ci(repo: str, policy: dict) -> list[dict]:
    """Red GitHub Actions runs are errors the estate can act on."""
    window = int(policy["sense"]["window_hours"])
    failures = set(policy["sense"]["failure_conclusions"])
    ignored = set(policy["sense"].get("ignore_workflows", []))
    cutoff = _since(window)
    # Failure-volume shaping is mandatory. Across the estate, the most recent
    # 100 *all* runs can cover only minutes of Greenlane churn while older P0
    # service failures remain inside the requested 24h window. Query ONLY the
    # failure conclusions, with pagination, never a single newest-page sample.
    # GitHub Actions supports each of these status filters (verified live).
    by_id: dict[int, dict] = {}
    max_pages = 20
    for conclusion in sorted(failures):
        for page in range(1, max_pages + 1):
            code, out, err = run_gh(
                [
                    "api",
                    f"repos/{repo}/actions/runs?status={conclusion}"
                    f"&created=>{cutoff}&per_page=100&page={page}",
                    "--jq",
                    "[.workflow_runs[] | {id, name, head_branch, conclusion, "
                    "event, created_at, html_url, run_attempt}]",
                ]
            )
            if code != 0:
                raise LoopError(
                    f"gh api failed to enumerate {conclusion} page {page}: "
                    f"{err.strip()[:200]}"
                )
            try:
                batch = json.loads(out or "[]")
            except json.JSONDecodeError as exc:
                raise LoopError(
                    f"gh api {conclusion} page {page} returned invalid JSON: {exc}"
                ) from exc
            if not isinstance(batch, list):
                raise LoopError(f"gh api {conclusion} page {page} returned non-list")
            for run in batch:
                if not isinstance(run, dict) or not isinstance(run.get("id"), int):
                    raise LoopError(
                        f"gh api {conclusion} page {page} returned invalid run"
                    )
                original = by_id.get(run["id"])
                if (
                    original is None
                    or int(run.get("run_attempt") or 1)
                    > int(original.get("run_attempt") or 1)
                ):
                    by_id[run["id"]] = run
            if len(batch) < 100:
                break
        else:
            # Saturation must be visible as BLIND, not a fabricated complete
            # incident census. The next attempt is free to discover more.
            raise LoopError(
                f"CI failure sensor BLIND: over {max_pages * 100} "
                f"{conclusion} runs since {cutoff}; pagination budget exhausted"
            )
    runs = sorted(by_id.values(), key=lambda x: x["id"], reverse=True)
    incidents = []
    for run in runs:
        if run.get("conclusion") not in failures:
            continue
        if str(run.get("created_at", "")) < cutoff:
            continue
        if run.get("name") in ignored:
            continue
        branch = run.get("head_branch") or ""
        if branch == "main":
            severity, blast = "critical", "main"
        elif branch.startswith("queue/"):
            # A candidate under the Greenlane's own gate: a red one blocks the estate's
            # trunk, so it is a major error on a lane, not a minor one on a push.
            severity, blast = "major", "lane"
        elif run.get("event") == "pull_request":
            severity, blast = "major", "lane"
        else:
            severity, blast = "minor", "lane"
        incidents.append(
            {
                "id": fingerprint("ci", repo, str(run["id"])),
                "source": "ci",
                "repo": repo,
                "severity": severity,
                "blast": blast,
                "title": f"{run.get('name', 'workflow')} failed on {branch or 'a run'}",
                "url": run.get("html_url", ""),
                "detail": {
                    "run_id": run["id"],
                    "workflow": run.get("name", ""),
                    "branch": branch,
                    "event": run.get("event", ""),
                    "conclusion": run.get("conclusion", ""),
                    "created_at": run.get("created_at", ""),
                    "run_attempt": run.get("run_attempt", 1),
                },
            }
        )
    # An incident loop admits only max_new_per_tick. The response must therefore
    # be priority-ordered BEFORE admission, or hundreds of newer lane failures
    # starve an older main-branch P0 indefinitely.
    incidents.sort(
        key=lambda incident: (
            -score_incident(
                policy, incident["severity"], incident["blast"]
            )[0],
            incident["detail"].get("created_at", ""),
            incident["id"],
        )
    )
    return incidents


def _since(hours: int) -> str:
    stamp = wall_now() - timedelta(hours=hours)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def sense_doors(policy: dict) -> list[dict]:
    """The executor's own refusal ledger: an error the estate's doors produced."""
    path = ESTATE_HOME / "friction" / "events.jsonl"
    if not path.exists():
        return []
    window = int(policy["sense"]["window_hours"])
    kinds = set(policy["sense"].get("door_kinds", []))
    cutoff = wall_now() - timedelta(hours=window)
    grouped: dict[tuple[str, str], dict] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines[-5000:]:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        stamp = event.get("ts", "")
        kind = str(event.get("kind", "refusal"))
        if kinds and kind not in kinds:
            # The disk floor and the pacing rules are the estate's guardrails doing their job,
            # not estate errors: only the kinds the policy names are sensed.
            continue
        try:
            when = parse_iso(stamp)
        except ValueError:
            continue
        if when < cutoff:
            continue
        key = (str(event.get("kind", "refusal")), str(event.get("shape", "unknown")))
        grouped.setdefault(
            key,
            {
                "id": fingerprint("door", "", f"{key[0]}|{key[1]}"),
                "source": "door",
                "repo": "",
                "severity": "minor",
                "blast": "tooling",
                "title": f"estate door refused: {key[0]} ({key[1]})",
                "url": "",
                "detail": {
                    "kind": key[0],
                    "shape": key[1],
                    "count": 0,
                    "last_ts": stamp,
                },
            },
        )
        grouped[key]["detail"]["count"] += 1
        grouped[key]["detail"]["last_ts"] = stamp
    return list(grouped.values())


# --------------------------------------------------------------------------------------
# the ticket: one per incident
# --------------------------------------------------------------------------------------


def ensure_labels(policy: dict) -> None:
    for label in policy.get("labels", []):
        run_gh(["label", "create", label, "--force", "--color", "B60205"], timeout=20)


def find_existing_ticket(row: sqlite3.Row) -> int:
    """One failure, one ticket. An issue that already names this failure is the ticket."""
    needle = row["url"] or ""
    if not needle:
        return 0
    code, out, _ = run_gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--search",
            needle,
            "--limit",
            "5",
            "--json",
            "number,title,body",
        ],
        timeout=30,
    )
    if code != 0:
        return 0
    try:
        rows = json.loads(out or "[]")
    except json.JSONDecodeError:
        return 0
    for entry in rows:
        body = str(entry.get("body", ""))
        title = str(entry.get("title", ""))
        if needle in body or needle in title:
            return int(entry.get("number", 0))
    return 0


def raise_ticket(conn: sqlite3.Connection, policy: dict, row: sqlite3.Row) -> int:
    """One incident, one ticket, with the policy's label on it."""
    if row["ticket"]:
        return int(row["ticket"])
    existing = find_existing_ticket(row)
    if existing:
        set_field(
            conn,
            row["id"],
            ticket=existing,
            event=f"reused the open ticket #{existing} that already names this failure",
        )
        return existing
    ensure_labels(policy)
    body = "\n".join(
        [
            "Raised by the estate incident loop (`bin/estate-incident-loop`).",
            "",
            f"- incident: `{row['id']}`",
            f"- source: {row['source']}",
            f"- severity: {row['severity']} / blast radius: {row['blast']}",
            f"- priority: {row['label']} (score {row['score']:.0f}, SLA {row['sla_minutes']} min)",
            f"- first seen: {row['first_seen']}",
            f"- url: {row['url'] or '(none)'}",
            "",
            "The loop dispatches this to a worker or an agent session and closes this issue",
            "with the lesson when the error is gone. Do not close it by hand: the lesson and",
            "the MTTR are written from the loop's own record.",
        ]
    )
    title = f"{row['label']}: {row['title']}"
    code, out, err = run_gh(
        [
            "issue",
            "create",
            "--title",
            title,
            "--label",
            row["label"],
            "--body",
            body,
        ],
        timeout=40,
    )
    if code != 0:
        raise LoopError(f"gh issue create failed: {err.strip()[:200]}")
    number = int(out.strip().rstrip("/").split("/")[-1])
    set_field(
        conn,
        row["id"],
        ticket=number,
        event=f"ticket #{number} raised as {row['label']}",
    )
    return number


# --------------------------------------------------------------------------------------
# dispatch: a session when the bus has room, the worker queue when it does not
# --------------------------------------------------------------------------------------


def sb_path() -> Path | None:
    """The estate's own bus. The runtime mirror first: it is the copy that has its venv."""
    for candidate in (
        ESTATE_HOME / "runtime" / "idp" / "bin" / "sb",
        IDP / "bin" / "sb",
    ):
        if candidate.exists():
            return candidate
    return None


def _sb_list(repo: str) -> tuple[int, list[dict]]:
    """Is the sovereign bus answering, and what sessions does it hold?"""
    sb = sb_path()
    if sb is None:
        return 127, []
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            [str(sb), "list", "--json"],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(sb.parent.parent),
        )
    except subprocess.TimeoutExpired:
        return 124, []
    if proc.returncode != 0:
        return proc.returncode, []
    try:
        sessions = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return 1, []
    if not isinstance(sessions, list):
        return 1, []
    return 0, sessions


def router_probe(policy: dict) -> tuple[bool, str]:
    """Is there a model route that answers right now?

    The session leg is only real when a router answers. A bus that accepts a session whose
    runner cannot call a model is a dispatch that looks like it worked and did not, and the
    incident goes nowhere while the ledger says it was dispatched. So the route is
    measured: the estate's cloud router first (the default route), the laptop router
    second (the fallback that exists so a cluster outage does not disable every agent).
    """
    for base in policy["dispatch"].get("routers", []):
        url = base.rstrip("/") + "/health"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
                if 200 <= int(response.status) < 300:
                    return True, base
        except (urllib.error.URLError, OSError, ValueError):
            continue
    return False, ""


def dispatch_decision(policy: dict, score: float, bus: dict) -> str:
    """Which leg takes this incident. Capacity decides, and it is measured."""
    rules = policy["dispatch"]
    if score < rules.get("session_min_score", 0):
        return "worker"
    if not bus.get("reachable"):
        return "worker"
    if not bus.get("router"):
        return "worker"
    if bus.get("running", 0) >= int(rules.get("max_sessions", 1)):
        return "worker"
    return "session"


def start_session(
    policy: dict, repo: str, task: str, route: str = ""
) -> tuple[str, str]:
    """One Temporal session through the estate's own bus, on the route that answered."""
    sb = sb_path()
    if sb is None:
        return "", ""
    rules = policy["dispatch"]
    env = dict(os.environ)
    if route:
        # The bus reads the router from its secret store, and the store lives in the
        # cluster; when the cluster is down the session would start with no route at all.
        # The route that answered the probe is passed by name.
        env["LITELLM_BASE_URL"] = route
    for runner in rules.get("runners", ["llm"]):
        try:
            proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                [
                    str(sb),
                    "start",
                    "--task",
                    task,
                    "--runner",
                    runner,
                    "--repo",
                    repo,
                    "--budget",
                    str(rules.get("session_budget", 20)),
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=int(rules.get("runner_timeout", 30)),
                cwd=str(sb.parent.parent),
                env=env,
            )
        except subprocess.TimeoutExpired:
            continue
        if proc.returncode != 0:
            continue
        try:
            payload = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            continue
        session_id = payload.get("session_id") or payload.get("id") or ""
        if session_id:
            return "session", str(session_id)
    return "", ""


def queue_dispatcher_path() -> Path | None:
    """The estate's one task queue. The runtime mirror is the copy that always has it."""
    for candidate in (
        IDP / "platform" / "queue" / "dispatcher.py",
        ESTATE_HOME / "runtime" / "idp" / "platform" / "queue" / "dispatcher.py",
    ):
        if candidate.exists():
            return candidate
    return None


def push_worker_task(policy: dict, goal: str) -> tuple[str, str]:
    """Hand the work to the estate's own task queue. One queue, not a second."""
    rules = policy["dispatch"]
    queue_db = Path(os.path.expanduser(str(rules.get("queue_db", ""))))
    queue_db.parent.mkdir(parents=True, exist_ok=True)
    os.environ["QUEUE_DB_PATH"] = str(queue_db)
    os.environ.setdefault("WORKTREE_BASE", str(ESTATE_HOME / "state" / "wt-agents"))
    # Loaded by path, not by package name: "platform" is a standard library module, so
    # "from platform.queue import dispatcher" would import the standard library's platform.
    path = queue_dispatcher_path()
    if path is None:
        raise LoopError(
            "the estate task queue (platform/queue/dispatcher.py) is not here"
        )
    spec = importlib.util.spec_from_file_location("estate_queue_dispatcher", path)
    if spec is None or spec.loader is None:
        raise LoopError(f"the estate task queue at {path} could not be loaded")
    dispatcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispatcher)
    dispatcher.init_db()
    dispatcher.push_task(goal)
    rows = dispatcher.get_task_list()
    for row in rows:
        if row[1] == goal:
            return "worker", str(row[0])
    return "worker", ""



def worker_queue_witness(policy: dict, dispatch_ref: str) -> tuple[str, str]:
    """Read the existing queue's durable task record; queued is not running.

    Never create a second queue, resubmit a task, or infer an agent from a
    successful enqueue. An unreadable or untrusted record is BLIND, not PASS.
    """
    ref = str(dispatch_ref or "")
    if not ref.isdecimal() or int(ref) <= 0:
        return "UNPROVEN", "no durable numeric queue task id"
    queue_path = Path(
        os.path.expanduser(str(policy.get("dispatch", {}).get("queue_db", "")))
    )
    if not queue_path.is_file():
        return "BLIND", "queue database is unavailable"
    try:
        with sqlite3.connect(
            queue_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
        ) as db:
            task = db.execute(
                "SELECT status, agent_id FROM tasks WHERE id = ?", (int(ref),)
            ).fetchone()
    except (sqlite3.Error, OSError, ValueError) as exc:
        return "BLIND", f"queue readback failed: {type(exc).__name__}"
    if task is None:
        return "MISSING", f"task {ref} is absent from the queue"
    status, agent_id = str(task[0] or "").lower(), str(task[1] or "").strip()
    if status == "running":
        if agent_id:
            return "OWNED", f"task {ref} claimed by agent {agent_id}"
        return "UNOWNED", f"task {ref} says running without an agent_id"
    if status == "pending":
        return "QUEUED", f"task {ref} is pending, no worker claim"
    if status in ("completed", "done", "success"):
        return "FINISHED_UNVERIFIED", f"task {ref} finished; source recovery still open"
    if status in ("failed", "error", "cancelled"):
        return "FAILED", f"task {ref} has terminal status {status}"
    return "BLIND", f"task {ref} has unrecognised status {status!r}"


def audit_p0_worker_liveness(
    conn: sqlite3.Connection, policy: dict, row: sqlite3.Row
) -> tuple[bool, str]:
    """Escalate a genuinely overdue P0 once per observed queue state.

    A waiting worker cannot satisfy the incident SLA. Ticket comments are
    advisory evidence, not resolution or proof of executing a worker.
    """
    if (
        row["label"] != "P0"
        or row["state"] != "open"
        or row["dispatch_leg"] != "worker"
    ):
        return False, ""
    state, witness = worker_queue_witness(policy, str(row["dispatch_ref"]))
    if not row["dispatched_at"]:
        elapsed = float("inf")
    else:
        try:
            elapsed = max(0.0, (wall_now() - parse_iso(row["dispatched_at"])).total_seconds())
        except (TypeError, ValueError):
            elapsed = float("inf")
    sla = max(60, int(row["sla_minutes"] or 15) * 60)
    if elapsed < sla or state == "OWNED":
        return False, f"{state}: {witness}"
    marker = f"p0-worker-overdue:{state}"
    history = json.loads(row["history"] or "[]")
    if any(event.get("event") == marker for event in history):
        return True, f"{state}: {witness}"
    if row["ticket"]:
        body = (
            f"P0 dispatch-liveness breach for incident {row['id']}. "
            f"Existing queue witness: {state}: {witness}. "
            f"The task is not independently proven to have a running owner "
            f"within its {row['sla_minutes']} minute SLA. "
            "This is an escalation, not an automatic recovery, retry or closure. "
            "Inspect the existing queue consumer and session bus; preserve the "
            "original incident and source-verification requirements."
        )
        code, _, _ = run_gh(
            ["issue", "comment", str(row["ticket"]), "--body", body], timeout=30
        )
        if code == 0:
            set_field(conn, row["id"], event=marker)
    return True, f"{state}: {witness}"


def dispatch_incident(
    conn: sqlite3.Connection, policy: dict, row: sqlite3.Row
) -> tuple[str, str]:
    """Take one incident and put it in front of something that can fix it."""
    repo = row["repo"] or policy["dispatch"].get("repo", "chidionyema/idp")
    ticket = row["ticket"]
    code, sessions = _sb_list(repo)
    running = sum(
        1
        for s in sessions
        if str(s.get("status", "")) in ("running", "planning", "waiting", "tool_use")
    )
    router_ok, route = router_probe(policy)
    bus = {"reachable": code == 0, "running": running, "router": router_ok}
    leg = dispatch_decision(policy, float(row["score"]), bus)
    task = (
        f"Incident {row['id']} ({row['label']}, score {row['score']:.0f}): {row['title']}\n"
        f"issue: #{ticket}\nurl: {row['url']}\n"
        f"severity: {row['severity']} / blast radius: {row['blast']}\n"
        "Fix the error, land it through lane-submit (a session may not push; if the bus "
        "session cannot push, hand the work to a worker on the queue), and say so on the "
        "issue. The loop closes the incident with the lesson and the MTTR."
    )
    if leg == "session":
        kind, ref = start_session(policy, repo, task, route)
        if kind:
            set_field(
                conn,
                row["id"],
                dispatch_leg=kind,
                dispatch_ref=ref,
                dispatched_at=now_iso(),
                event=f"dispatched to session {ref}",
            )
            return kind, ref
        leg = "worker"
    kind, ref = push_worker_task(policy, task)
    set_field(
        conn,
        row["id"],
        dispatch_leg=kind,
        dispatch_ref=ref,
        dispatched_at=now_iso(),
        event=f"dispatched to the worker queue as task {ref}",
    )
    return kind, ref


# --------------------------------------------------------------------------------------
# verify: is the error gone?
# --------------------------------------------------------------------------------------


def greenlane_state(repo: str) -> dict:
    """The Greenlane's own state: what it is testing, what it landed, what went red.

    The state lives on its own ref (`refs/greenlane/state`), one file, written by the
    engine. It is the estate's record of which lane a candidate was built from and
    whether that lane landed -- the loop reads it rather than guessing from branch
    names.
    """
    key = f"greenlane-state:{repo}"
    cached = _STATE_CACHE.get(key)
    if cached and time.time() - cached[0] < 60:
        return cached[1]
    # The ref lives outside refs/heads, so the contents endpoint (which takes the ref as a
    # query parameter) is the one that reads it: git/ref/refs/greenlane/state is a 404,
    # measured, because the ref route takes a single path segment.
    code, out, _ = run_gh(
        [
            "api",
            f"repos/{repo}/contents/state.json?ref=refs/greenlane/state",
            "--jq",
            ".content",
        ]
    )
    if code != 0 or not out.strip():
        return {}
    try:
        state = json.loads(base64.b64decode(out.strip()).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    _STATE_CACHE[key] = (time.time(), state)
    return state


def lane_landed(repo: str, row: sqlite3.Row) -> tuple[bool, str]:
    """Did the estate's own Greenlane land the lane that failed?

    A candidate is graded under a branch of its own (`queue/<batch>`), and the batch's
    members are the lanes it was built from. The state records what became of each
    batch, so "the error is gone" is answered by the estate's own record: the lane
    landed.
    """
    detail = json.loads(row["detail"] or "{}")
    branch = str(detail.get("branch", ""))
    if not branch.startswith("queue/"):
        return False, ""
    batch_id = branch.split("/", 1)[1]
    state = greenlane_state(repo)
    if not state:
        return False, ""
    members: list[str] = []
    outcome = ""
    current = state.get("batch") or {}
    if str(current.get("id", "")) == batch_id:
        outcome = "testing"
        for member in current.get("members") or []:
            if isinstance(member, list) and member:
                members.append(str(member[0]))
            elif isinstance(member, str):
                members.append(member)
    for entry in state.get("history") or []:
        if str(entry.get("id", "")) != batch_id:
            continue
        outcome = str(entry.get("outcome", ""))
        for member in entry.get("members") or []:
            if isinstance(member, list) and member:
                members.append(str(member[0]))
            elif isinstance(member, str):
                members.append(member)
    if not members:
        return False, ""
    if outcome == "landed":
        return True, f"the Greenlane landed {', '.join(members)}"
    for entry in state.get("history") or []:
        if str(entry.get("id", "")) <= batch_id:
            continue
        if str(entry.get("outcome", "")) != "landed":
            continue
        landed = [
            m[0] if isinstance(m, list) and m else m for m in entry.get("members") or []
        ]
        for member in members:
            if member in landed:
                return True, (
                    f"the Greenlane landed {member} in batch {entry.get('id')}"
                )
    return False, ""


def ci_resolved(repo: str, row: sqlite3.Row) -> tuple[bool, str]:
    """An unrelated green workflow or an older green is never recovery evidence.

    A queue candidate is judged by the existing exact-lane Greenlane authority.
    For other branches, grade only the latest relevant workflow run on the
    ORIGINAL branch. A later failure/queued run revokes any earlier green.
    """
    detail = json.loads(row["detail"] or "{}")
    run_id = detail.get("run_id")
    workflow = str(detail.get("workflow") or "")
    branch = str(detail.get("branch") or "")
    if not run_id or not workflow or not branch:
        return False, ""
    if branch.startswith("queue/"):
        return lane_landed(repo, row)
    # GitHub Actions run listing is global by default. Under fleet load the
    # most recent 60 runs may contain zero runs for the original workflow,
    # and a green on another branch must never close a red on main.
    branch_arg = urllib.parse.quote(branch, safe="")
    code, out, _ = run_gh(
        [
            "api",
            f"repos/{repo}/actions/runs?branch={branch_arg}&per_page=100",
            "--jq",
            "[.workflow_runs[] | {id, name, conclusion, status, head_branch, run_attempt}]",
        ]
    )
    if code != 0:
        return False, ""
    try:
        runs = json.loads(out or "[]")
    except (json.JSONDecodeError, TypeError):
        return False, ""
    if not isinstance(runs, list):
        return False, ""
    matching = [
        item for item in runs
        if isinstance(item, dict)
        and item.get("name") == workflow
        and item.get("head_branch") == branch
        and isinstance(item.get("id"), int)
    ]
    if not matching:
        return False, ""
    latest = max(matching, key=lambda item: (item["id"], item.get("run_attempt") if isinstance(item.get("run_attempt"), int) else 0))
    try:
        original_id = int(run_id)
        original_attempt = int(detail.get("run_attempt") or 1)
        attempt = int(latest.get("run_attempt") or 1)
    except (TypeError, ValueError):
        return False, ""
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        return False, ""
    if latest["id"] > original_id:
        return True, (
            f"latest {workflow} run {latest['id']} on original branch {branch} is green"
        )
    if latest["id"] == original_id and attempt > original_attempt:
        return True, (
            f"original {workflow} run {original_id} rerun attempt {attempt} "
            f"on branch {branch} is green"
        )
    return False, ""


def door_resolved(policy: dict, row: sqlite3.Row) -> tuple[bool, str]:
    """A door refusal is resolved when the door has been quiet for the policy's window."""
    detail = json.loads(row["detail"] or "{}")
    key = (detail.get("kind", ""), detail.get("shape", ""))
    quiet = int(policy["sense"].get("door_quiet_minutes", 30))
    path = ESTATE_HOME / "friction" / "events.jsonl"
    if not path.exists():
        return False, ""
    cutoff = wall_now() - timedelta(minutes=quiet)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False, ""
    for line in reversed(lines[-5000:]):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (event.get("kind", ""), event.get("shape", "")) != key:
            continue
        try:
            when = parse_iso(event.get("ts", ""))
        except ValueError:
            continue
        if when >= cutoff:
            return False, ""
        return True, f"no refusal of this shape for {quiet} minutes"
    return False, ""


def ticket_resolved(row: sqlite3.Row) -> tuple[bool, str]:
    """A reported incident is resolved when its ticket is closed."""
    if not row["ticket"]:
        return False, ""
    code, out, _ = run_gh(
        ["api", f"repos/chidionyema/idp/issues/{row['ticket']}", "--jq", ".state"]
    )
    if code != 0:
        return False, ""
    if out.strip().lower() == "closed":
        return True, f"issue #{row['ticket']} is closed"
    return False, ""


def finalize_verified_incident(
    conn: sqlite3.Connection, policy: dict, row: sqlite3.Row
) -> bool:
    """CLOSED requires independently observed GitHub issue state.

    On timeout, permission refusal or unreadable remote GET, preserve VERIFIED
    so a later tick can reconcile without recomputing MTTR or lessons.
    """
    if row["state"] != "verified":
        return False
    if not row["ticket"]:
        try:
            raise_ticket(conn, policy, row)
        except LoopError:
            return False
        row = get_incident(conn, row["id"])
    confirmed, witness = ticket_resolved(row)
    if not confirmed:
        code, _, _ = run_gh(
            [
                "issue", "close", str(row["ticket"]), "--comment",
                f"The incident loop verified the source: {row['lesson']}. "
                f"MTTR {row['mttr_seconds']}s.",
            ],
            timeout=30,
        )
        if code != 0:
            return False
        confirmed, witness = ticket_resolved(row)
        if not confirmed:
            return False
    set_field(
        conn, row["id"], state="closed", closed_at=now_iso(),
        event=f"remote closure attested: {witness}",
    )
    return True


def verify_incident(conn: sqlite3.Connection, policy: dict, row: sqlite3.Row) -> bool:
    """Source recovery first; remote closure must be independently attested."""
    if row["state"] == "closed":
        return False
    if row["state"] == "verified":
        return finalize_verified_incident(conn, policy, row)
    if row["source"] == "ci":
        resolved, evidence = ci_resolved(row["repo"], row)
    elif row["source"] == "door":
        resolved, evidence = door_resolved(policy, row)
    else:
        resolved, evidence = ticket_resolved(row)
    if not resolved:
        return False
    verified_at = now_iso()
    mttr = mttr_seconds(row["first_seen"], verified_at)
    lesson = (
        f"{row['label']} incident {row['id']}: {row['title']} - {evidence}. "
        f"Raised {row['first_seen']}, verified {verified_at}, MTTR {mttr}s."
    )
    set_field(
        conn, row["id"], state="verified", verified_at=verified_at,
        mttr_seconds=mttr, lesson=lesson, event=f"verified: {evidence}",
    )
    write_lesson(policy, lesson)
    return finalize_verified_incident(conn, policy, get_incident(conn, row["id"]))

# --------------------------------------------------------------------------------------
# the lesson: the estate's own knowledge graph
# --------------------------------------------------------------------------------------


def write_lesson(policy: dict, lesson: str) -> str:
    """One line into the estate graph. Best effort: the loop still closes without it."""
    root = Path(os.path.expanduser(str(policy.get("graph", {}).get("root", ""))))
    if not root.exists():
        return "no graph root"
    growmos = shutil.which("growmos")
    if not growmos:
        return "no growmos on PATH"
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            [growmos, "--root", str(root), "journal", lesson],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "journal timed out"
    if proc.returncode != 0:
        return f"journal failed: {proc.stderr.strip()[:160]}"
    return "journalled"


# --------------------------------------------------------------------------------------
# the loop
# --------------------------------------------------------------------------------------


def tick(policy: dict, repo: str, dry_run: bool = False) -> dict:
    """One pass of the whole loop."""
    conn = open_ledger()
    summary = {"sensed": 0, "opened": 0, "dispatched": 0, "verified": 0, "closure_pending": 0, "notes": []}
    sensed: list[dict] = []
    # The clock is judged first: a tick that runs while the wall clock lies writes wrong
    # timestamps into every incident it senses. The verdict is stored, so the next tick can
    # compare against it, and an untrustworthy clock is itself an incident.
    clock = clock_guard.commit()
    summary["clock"] = clock["state"]
    if clock["state"] in (clock_guard.BACKWARD, clock_guard.FORWARD):
        summary["notes"].append(
            f"the host wall clock is {clock['state']}: {clock['reason']}"
        )
        sensed.append(
            {
                "id": fingerprint("clock", repo, f"clock-{clock['state']}"),
                "source": "clock",
                "repo": repo,
                "severity": "major",
                "blast": "main",
                "title": (
                    f"the host wall clock is untrustworthy ({clock['state']}): "
                    f"{clock['reason']}"
                ),
                "url": "",
                "detail": {
                    "verdict": clock["state"],
                    "wall_delta_s": clock["wall_delta_s"],
                    "monotonic_delta_s": clock["monotonic_delta_s"],
                    "skew_s": clock["skew_s"],
                    "projected_epoch": clock["projected_epoch"],
                    "reason": clock["reason"],
                },
            }
        )
    try:
        sensed.extend(sense_ci(repo, policy))
        sensed.extend(sense_doors(policy))
    except LoopError as exc:
        summary["notes"].append(f"sensor: {exc}")
    max_new = int(policy["sense"].get("max_new_per_tick", 3))
    max_open = int(policy["sense"].get("max_open_incidents", 50))
    open_now = len(list_incidents(conn, state="open", limit=1000))
    new_count = 0
    for incident in sensed:
        summary["sensed"] += 1
        existing = get_incident(conn, incident["id"])
        if existing is None:
            if new_count >= max_new:
                continue
            if open_now + new_count >= max_open:
                summary["notes"].append(
                    f"the ledger holds {open_now} open incidents; the policy's cap "
                    f"({max_open}) stops new ones"
                )
                break
            new_count += 1
        if dry_run:
            score, label = score_incident(
                policy, incident["severity"], incident["blast"]
            )
            summary["notes"].append(
                f"would open {incident['id']} as {label} (score {score:.0f}): "
                f"{incident['title']}"
            )
            continue
        row = record_incident(conn, incident, policy)
        if existing is None:
            summary["opened"] += 1
        if not row["ticket"]:
            number = raise_ticket(conn, policy, row)
            summary["notes"].append(f"ticket #{number} for {row['id']}")
            row = get_incident(conn, row["id"])
        if row["state"] == "open" and not row["dispatch_leg"]:
            leg, ref = dispatch_incident(conn, policy, row)
            summary["dispatched"] += 1
            summary["notes"].append(f"{row['id']} -> {leg} {ref}")
    # A cap on NEW incidents must never freeze an existing P0. Retry unfinished rows
    # on every tick, highest score first, with a bounded recovery budget.
    recovery_budget = max(1, int(policy["sense"].get("recover_per_tick", 1)))
    recovered = 0
    for row in list_incidents(conn, state="open", limit=1000):
        if recovered >= recovery_budget:
            break
        if row["ticket"] and row["dispatch_leg"]:
            continue
        if dry_run:
            summary["notes"].append(f"would recover unfinished {row['id']}")
            recovered += 1
            continue
        try:
            # A stale CI failure may already have gone green. Verify before raising a ticket.
            if verify_incident(conn, policy, row):
                summary["verified"] += 1
                summary["notes"].append(f"recovered {row['id']} by verification")
                recovered += 1
                continue
            if not row["ticket"]:
                number = raise_ticket(conn, policy, row)
                summary["notes"].append(f"recovered ticket #{number} for {row['id']}")
                row = get_incident(conn, row["id"])
            if not row["dispatch_leg"]:
                leg, ref = dispatch_incident(conn, policy, row)
                summary["dispatched"] += 1
                summary["notes"].append(f"recovered {row['id']} -> {leg} {ref}")
            recovered += 1
        except LoopError as exc:
            summary["notes"].append(f"recovery blocked for {row['id']}: {exc}")
            break
    # A pending queue entry is not a running autonomous repair. Reconcile P0
    # liveness even when an earlier tick wrote dispatch_leg=worker.
    summary["p0_worker_overdue"] = 0
    for row in list_incidents(conn, state="open", limit=1000):
        if dry_run or row["label"] != "P0" or row["dispatch_leg"] != "worker":
            continue
        overdue, evidence = audit_p0_worker_liveness(conn, policy, row)
        if overdue:
            summary["p0_worker_overdue"] += 1
            summary["notes"].append(
                f"incident {row['id']} worker not proven within SLA: {evidence}"
            )
    for state in ("open", "dispatched", "verified"):
        checked = 0
        budget = int(policy["sense"].get("verify_per_tick", 5))
        for row in list_incidents(conn, state=state, limit=200):
            if dry_run or checked >= budget:
                continue
            checked += 1
            if verify_incident(conn, policy, row):
                summary["verified"] += 1
                summary["notes"].append(f"{row['id']} verified")
            elif state == "verified":
                summary["closure_pending"] += 1
                summary["notes"].append(
                    f"incident {row['id']} recovered but remote closure is not attested; "
                    f"ticket #{row['ticket'] or '-'} remains pending"
                )
    conn.close()
    return summary


# --------------------------------------------------------------------------------------
# the drill: a failure injected on purpose, closed by the loop
# --------------------------------------------------------------------------------------


def drill_state_path() -> Path:
    return ESTATE_HOME / "state" / "incident-drill.json"


def drill_status() -> dict:
    path = drill_state_path()
    if not path.exists():
        return {"state": "none"}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def drill_write(state: dict) -> None:
    path = drill_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


CANARY = '''"""The incident loop's canary. Injected by `bin/estate-incident-loop drill seed`.

The drill writes this file with a deliberately wrong assertion, so the estate's CI goes red
for a real reason and the loop has a real error to sense. `drill fix` rewrites it to the true
assertion, and the lane goes green and merges. Nothing here is special-cased for the drill:
the same sensors, the same ticket, the same dispatch, the same verdict.

WHERE IT LIVES. Under tests/, because that is where the estate's CI collects test files from
(bin/idp-tests-for's blanket runs every cheap tests/test_*.py); a canary in a directory no CI
job collects would be a drill that cannot fail, and a test that executes nothing is not a test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

LIBEXEC = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "incident-loop.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("incident_loop", LIBEXEC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_policy_scores_a_critical_incident_above_a_minor_one():
    module = _load()
    policy = module.load_policy()
    critical, critical_label = module.score_incident(policy, "critical", "main")
    minor, minor_label = module.score_incident(policy, "minor", "local")
    assert critical < minor, (critical, minor)
    assert critical_label == "P0", critical_label
    assert minor_label == "P2", minor_label
'''


def drill_seed(worktree: str, lane: str) -> dict:
    """Write the canary into the worktree and hand the lane to the estate's own door."""
    # The canary is a test file, so it carries the date it was injected: the estate's own
    # rule refuses a test file named for a rule (test_incident_*) and asks for the day
    # something broke.
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target = Path(worktree) / "tests" / f"test_{day}_incident_drill_canary.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CANARY, encoding="utf-8")
    state = {
        "state": "seeded",
        "worktree": str(worktree),
        "lane": lane,
        "canary": str(target),
        "at": now_iso(),
    }
    drill_write(state)
    return state


def drill_fix(worktree: str) -> dict:
    """Rewrite the canary to the true assertion and re-arm the lane."""
    state = drill_status()
    if state.get("state") == "none":
        return {"state": "none"}
    target = Path(state["canary"])
    text = target.read_text(encoding="utf-8")
    fixed = text.replace(
        "    assert critical < minor, (critical, minor)",
        "    assert critical > minor, (critical, minor)\n"
        "    assert isinstance(critical, float) and isinstance(minor, float)",
    )
    target.write_text(fixed, encoding="utf-8")
    state["state"] = "fixed"
    state["fixed_at"] = now_iso()
    drill_write(state)
    return state


# --------------------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="estate-incident-loop", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="tick",
        help="tick | sense | list | show | report | verify | drill | policy | clock",
    )
    parser.add_argument("--repo", default="")
    parser.add_argument("--incident", default="")
    parser.add_argument("--severity", default="major")
    parser.add_argument("--blast", default="lane")
    parser.add_argument("--title", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--source", default="report")
    parser.add_argument("--state", default="")
    parser.add_argument("--lane", default="")
    parser.add_argument("--worktree", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    policy = load_policy()
    repo = args.repo or policy["dispatch"].get("repo", "chidionyema/idp")
    conn = open_ledger()

    if args.action == "policy":
        print(json.dumps(policy, indent=2))
        return 0

    if args.action == "sense":
        incidents = sense_ci(repo, policy) + sense_doors(policy)
        if args.json:
            print(json.dumps(incidents, indent=2))
        else:
            for incident in incidents:
                print(
                    f"{incident['id']}  {incident['severity']:<8} {incident['blast']:<8} "
                    f"{incident['title']}"
                )
            print(f"{len(incidents)} error(s) sensed")
        return 0

    if args.action == "list":
        rows = list_incidents(conn, state=args.state)
        if args.json:
            print(json.dumps([dict(r) for r in rows], indent=2, default=str))
        else:
            for row in rows:
                print(
                    f"{row['id']}  {row['label']:<3} {row['state']:<10} "
                    f"score={row['score']:<6.1f} ticket=#{row['ticket'] or '-':<6} "
                    f"{row['dispatch_leg'] or '-':<8} {row['title'][:60]}"
                )
            print(f"{len(rows)} incident(s)")
        return 0

    if args.action == "show":
        row = get_incident(conn, args.incident)
        if row is None:
            print(f"no incident {args.incident}")
            return 1
        print(json.dumps(dict(row), indent=2, default=str))
        return 0

    if args.action == "report":
        if not args.title:
            print("report needs --title")
            return 2
        incident = {
            "id": fingerprint(args.source, repo, args.title),
            "source": args.source,
            "repo": repo,
            "severity": args.severity,
            "blast": args.blast,
            "title": args.title,
            "url": args.url,
            "detail": {"reported_by": "estate-incident-loop"},
        }
        row = record_incident(conn, incident, policy)
        number = raise_ticket(conn, policy, row)
        row = get_incident(conn, row["id"])
        leg, ref = dispatch_incident(conn, policy, row)
        print(
            f"incident {row['id']} label {row['label']} ticket #{number} -> {leg} {ref}"
        )
        return 0

    if args.action == "verify":
        verified = 0
        for row in list_incidents(conn, limit=200):
            if verify_incident(conn, policy, row):
                verified += 1
        print(f"{verified} incident(s) verified")
        return 0

    if args.action == "drill":
        mode = args.state or "status"
        if mode == "seed":
            worktree = args.worktree or str(IDP)
            lane = args.lane or "lane/incident-drill"
            print(json.dumps(drill_seed(worktree, lane), indent=2))
            return 0
        if mode == "fix":
            print(json.dumps(drill_fix(args.worktree), indent=2))
            return 0
        print(json.dumps(drill_status(), indent=2))
        return 0

    if args.action == "clock":
        verdict = clock_guard.commit()
        if args.json:
            print(json.dumps(verdict, indent=2))
        else:
            print(f"{verdict['state']:<8} {verdict['reason']}")
            print(f"wall {verdict['wall']:.0f}  trusted {verdict['trusted']}")
        if verdict["state"] == clock_guard.BLIND:
            return 2
        if verdict["state"] in (clock_guard.BACKWARD, clock_guard.FORWARD):
            return 1
        return 0

    if args.action == "tick":
        summary = tick(policy, repo, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(
                f"tick: sensed {summary['sensed']}, opened {summary['opened']}, "
                f"dispatched {summary['dispatched']}, verified {summary['verified']}"
            )
            for note in summary["notes"]:
                print(f"  - {note}")
        return 0

    print(f"unknown action {args.action!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
