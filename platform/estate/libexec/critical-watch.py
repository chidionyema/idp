#!/usr/bin/env python3
"""critical-watch.py -- the estate-wide critical-function spine.

THE MANDATE. 2026-10-28. The founder: "we can't have critical functions failing, this is an
estate wide mandate so build the spine and use this to prove it" and "anything watching critical
function that dies needs alert and auto invocation of agent, with structured data to resolve".

WHAT WAS WRONG BEFORE. The estate had ~25 launchd jobs and nothing that watched any of them. The
disk watcher was the proof case: it was ALIVE (346 runs, exit 0, a fresh log every five minutes)
and it freed nothing, and the reclaim lock it held for 240 of every 300 seconds closed the door
every other agent needed. A watcher that cannot tell "alive" from "alive and useless" is not a
watcher, and nothing in the estate could raise an incident, alert a human, or wake an agent to
fix a dead critical function.

WHAT THIS IS. One generic detector over one declarative registry:

  * LIVENESS -- is the thing running? A heartbeat file, a socket, a port, an HTTP endpoint, a
    launchd label, a command, a file.
  * GOAL -- is it doing its job? Free space on a volume, a numeric field in a heartbeat. A
    function that is alive and missing its goal is FAILING, and that is the case the old disk
    watcher was.

THE VERDICTS are the certification plan's three (IDP_Production_Certification_Implementation_Plan_v1
.md, gate C11): PASS, FAIL, BLIND. BLIND is a first-class verdict, not a quiet PASS: a probe
that cannot be measured proves nothing, and reporting it as PASS is how a gate stops being a gate.

THE LOOP. A failure raises a structured incident (one JSON file per incident, a ledger, and a
latest.json), alerts (a macOS notification and ~/.estate/alerts/inbox.jsonl, the house pattern),
and wakes an agent to resolve it with the structured data attached -- through the estate's own
session door when it is up (sb start), and through the local claude lane when it is not, always
recording which one was used. Alerts and invocations are deduplicated and backed off (300s, then
600, 1200, 1800, capped), so a function that stays dead does not spawn an agent storm.

EXIT CODES. 0 every function PASSes; 1 at least one FAILs; 2 at least one is BLIND and none
FAILs. A spine that cannot fail is not a spine.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(os.environ.get("ESTATE_STATE_DIR", str(Path.home() / ".estate")))
INCIDENTS = STATE / "incidents"
INBOX = STATE / "alerts" / "inbox.jsonl"
HEARTBEAT = STATE / "heartbeats" / "critical-watch.json"
LEDGER = INCIDENTS / "ledger.jsonl"
LATEST = INCIDENTS / "latest.json"
BACKOFF_STATE = INCIDENTS / "state.json"
INVOKE = Path(
    os.environ.get(
        "CRITICAL_WATCH_INVOKE",
        str(Path(__file__).resolve().parent / "agent-invoke.sh"),
    )
)
# 300, 600, 1200, 1800 -- a function that stays dead must not spawn an agent every minute.
BACKOFF_LADDER = (300, 600, 1200, 1800)

PASS, FAIL, BLIND = "PASS", "FAIL", "BLIND"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expand(path: str) -> Path:
    """Expand a registry path, honouring the estate's state root.

    A registry path is written as ~/.estate/<something>, because that is where the estate's
    state lives. The state root is configurable (ESTATE_STATE_DIR), so a path under ~/.estate is
    resolved INSIDE the configured root -- otherwise a detector running against a temporary
    estate would measure the real one, and the test would be testing the founder's laptop.
    """
    p = Path(os.path.expanduser(os.path.expandvars(path)))
    home = str(Path.home())
    prefix = home + "/.estate"
    if str(p) == prefix or str(p).startswith(prefix + "/"):
        return Path(str(STATE) + str(p)[len(prefix) :])
    return p


def registry_path(explicit: str | None) -> Path | None:
    """Where the registry is, in order of preference.

    The installed copy lives in ~/.estate/libexec, where the repo's layout (parents[3]) is not
    there, so the runtime tree's catalog/ is the honest answer for an installed detector; the
    repo's own catalog/ is the answer when it runs from a checkout. An explicit --registry wins.
    """
    candidates = []
    if explicit:
        # An explicit registry that is not there is BLIND, not a reason to quietly measure a
        # different one: the caller named the registry, and measuring another one would report
        # the estate's functions when the caller asked about something else.
        path = expand(explicit)
        return path if path.is_file() else None
    env = os.environ.get("CRITICAL_WATCH_REGISTRY", "").strip()
    if env:
        path = expand(env)
        if path.is_file():
            return path
        return None
    here = Path(__file__).resolve()
    candidates.append(here.parents[3] / "catalog" / "critical-functions.json")
    candidates.append(STATE / "runtime/idp/catalog/critical-functions.json")
    candidates.append(STATE / "critical-functions.json")
    for c in candidates:
        if c.is_file():
            return c
    return None


# --------------------------------------------------------------------------- probes


def probe_liveness(spec: dict) -> tuple[str, str, dict]:
    """(verdict, why, evidence). BLIND when the probe cannot be measured."""
    kind = spec.get("type", "")
    ev: dict = {"type": kind}
    try:
        if kind == "heartbeat_file":
            path = expand(spec["path"])
            ev["path"] = str(path)
            max_age = int(spec.get("max_age_s", 180))
            ev["max_age_s"] = max_age
            if not path.is_file():
                return FAIL, f"the heartbeat file {path} does not exist", ev
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                return BLIND, f"the heartbeat file {path} could not be read: {exc}", ev
            at = data.get("at")
            ev["at"] = at
            ev["state"] = data.get("state")
            if not at:
                return BLIND, f"the heartbeat file {path} has no 'at'", ev
            try:
                when = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
            except ValueError:
                return BLIND, f"the heartbeat 'at' ({at}) is not a timestamp", ev
            age = (datetime.now(timezone.utc) - when).total_seconds()
            ev["age_s"] = int(age)
            if age > max_age:
                return FAIL, f"the heartbeat is {int(age)}s old (max {max_age}s)", ev
            if age < -60:
                return BLIND, f"the heartbeat is stamped {int(-age)}s in the future", ev
            return PASS, f"the heartbeat is {int(age)}s old", ev
        if kind == "unix_socket":
            path = expand(spec["path"])
            ev["path"] = str(path)
            if not path.exists():
                return FAIL, f"the socket {path} does not exist", ev
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(3)
            try:
                s.connect(str(path))
            except OSError as exc:
                return FAIL, f"the socket {path} refused the connection: {exc}", ev
            finally:
                s.close()
            return PASS, "the socket accepted a connection", ev
        if kind == "tcp":
            host, port = spec["host"], int(spec["port"])
            ev["host"], ev["port"] = host, port
            s = socket.socket()
            s.settimeout(3)
            try:
                s.connect((host, port))
            except OSError as exc:
                return FAIL, f"{host}:{port} refused the connection: {exc}", ev
            finally:
                s.close()
            return PASS, f"{host}:{port} accepted a connection", ev
        if kind == "http":
            url = spec["url"]
            ev["url"] = url
            req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(
                    req, timeout=int(spec.get("timeout_s", 5))
                ) as r:
                    status = r.status
            except urllib.error.HTTPError as exc:
                status = exc.code
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                return FAIL, f"{url} did not answer: {exc}", ev
            ev["status"] = status
            want = int(spec.get("expect_status", 200))
            if status != want:
                return FAIL, f"{url} answered {status}, expected {want}", ev
            return PASS, f"{url} answered {status}", ev
        if kind == "launchd":
            label = spec["label"]
            ev["label"] = label
            uid = os.getuid()
            p = subprocess.run(
                ["/bin/launchctl", "print", f"gui/{uid}/{label}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if p.returncode != 0:
                return FAIL, f"the launchd job {label} is not loaded", ev
            if "state = running" not in p.stdout:
                return FAIL, f"the launchd job {label} is loaded but not running", ev
            return PASS, f"the launchd job {label} is running", ev
        if kind == "command":
            argv = list(spec["argv"])
            ev["argv"] = argv
            try:
                p = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=int(spec.get("timeout_s", 20)),
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return FAIL, f"{argv[0]} could not be run: {exc}", ev
            ev["rc"] = p.returncode
            if p.returncode != int(spec.get("expect_rc", 0)):
                return FAIL, f"{argv[0]} exited {p.returncode}", ev
            return PASS, f"{argv[0]} exited {p.returncode}", ev
        if kind == "file":
            path = expand(spec["path"])
            ev["path"] = str(path)
            if not path.exists():
                return FAIL, f"{path} does not exist", ev
            return PASS, f"{path} exists", ev
    except (KeyError, ValueError, TypeError) as exc:
        return BLIND, f"the probe is malformed: {exc}", ev
    return BLIND, f"unknown probe type '{kind}'", ev


def probe_goal(spec: dict | None) -> tuple[str | None, str, dict]:
    """(verdict or None when there is no goal, why, evidence)."""
    if not spec:
        return None, "no goal declared", {}
    kind = spec.get("type", "")
    ev: dict = {"type": kind}
    try:
        if kind == "free_space_mb":
            path = spec.get("path", "/System/Volumes/Data")
            ev["path"] = path
            st = os.statvfs(path)
            free = int(st.f_bavail * st.f_frsize / (1024 * 1024))
            ev["free_mb"] = free
            want = int(spec["min_mb"])
            ev["min_mb"] = want
            if free < want:
                return FAIL, f"only {free}MB free on {path}, the floor is {want}MB", ev
            return PASS, f"{free}MB free on {path} (floor {want}MB)", ev
        if kind == "heartbeat_field_min":
            path = expand(spec["path"])
            field = spec["field"]
            want = float(spec["min"])
            ev["path"], ev["field"], ev["min"] = str(path), field, want
            if not path.is_file():
                return FAIL, f"the heartbeat file {path} does not exist", ev
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                return BLIND, f"the heartbeat file {path} could not be read: {exc}", ev
            if field not in data:
                return BLIND, f"the heartbeat has no '{field}'", ev
            value = data[field]
            ev["value"] = value
            if not isinstance(value, (int, float)):
                return BLIND, f"the heartbeat's '{field}' is not a number", ev
            if float(value) < want:
                return FAIL, f"'{field}' is {value}, the floor is {want}", ev
            return PASS, f"'{field}' is {value} (floor {want})", ev
        if kind == "launchd_running":
            label = spec["label"]
            ev["label"] = label
            uid = os.getuid()
            p = subprocess.run(
                ["/bin/launchctl", "print", f"gui/{uid}/{label}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if p.returncode != 0:
                return FAIL, f"the launchd job {label} is not loaded", ev
            if "state = running" not in p.stdout:
                return FAIL, f"the launchd job {label} is loaded but not running", ev
            return PASS, f"the launchd job {label} is running", ev
    except (KeyError, ValueError, TypeError, OSError) as exc:
        return BLIND, f"the goal probe is malformed: {exc}", ev
    return BLIND, f"unknown goal type '{kind}'", ev


# --------------------------------------------------------------------------- the loop


def check_function(fn: dict) -> dict:
    """One function's verdict, with the evidence that produced it."""
    live_v, live_why, live_ev = probe_liveness(fn.get("liveness", {}))
    goal_v, goal_why, goal_ev = probe_goal(fn.get("goal"))
    if live_v == FAIL:
        verdict = FAIL
    elif live_v == BLIND:
        verdict = BLIND
    elif goal_v == FAIL:
        verdict = FAIL
    elif goal_v == BLIND:
        verdict = BLIND
    else:
        verdict = PASS
    why = live_why if live_v != PASS else goal_why
    return {
        "id": fn.get("id"),
        "title": fn.get("title", fn.get("id")),
        "severity": fn.get("severity", "critical"),
        "verdict": verdict,
        "why": why,
        "liveness": {"verdict": live_v, "why": live_why, "evidence": live_ev},
        "goal": {"verdict": goal_v, "why": goal_why, "evidence": goal_ev},
        "remediation": fn.get("remediation", {}),
    }


def alert(source: str, level: str, msg: str) -> None:
    """The house alert: the inbox every surface reads, and a notification the founder sees."""
    try:
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        with INBOX.open("a") as fh:
            fh.write(
                json.dumps(
                    {"ts": time.time(), "source": source, "level": level, "msg": msg}
                )
                + "\n"
            )
    except OSError:
        pass
    try:
        safe = msg.replace("\\", "").replace('"', "'")[:180]
        subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                f'display notification "{safe}" with title "Estate spine" sound name "Basso"',
            ],
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def load_backoff() -> dict:
    try:
        return json.loads(BACKOFF_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_backoff(state: dict) -> None:
    try:
        INCIDENTS.mkdir(parents=True, exist_ok=True)
        tmp = BACKOFF_STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1))
        os.replace(tmp, BACKOFF_STATE)
    except OSError:
        pass


def invoke_agent(fn: dict, incident: dict) -> dict:
    """Wake an agent to resolve this, with the structured data attached.

    The session door (sb start) is the estate's own plane and is tried first; it is down at the
    moment (Temporal unreachable), so the local claude lane is the fallback. Which one was used is
    recorded in the incident, because a claim of "an agent was invoked" that does not say how is
    not a claim.
    """
    remediation = fn.get("remediation", {})
    task = remediation.get("task") or f"Resolve the failure of {fn.get('id')}."
    payload = {
        "incident": incident,
        "task": task,
        "runner": remediation.get("runner", "claude"),
        "repo": remediation.get("repo"),
        "budget": remediation.get("budget", 20),
    }
    try:
        proc = subprocess.run(
            ["/bin/bash", str(INVOKE), "--json", str(json.dumps(payload))],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "invoked": False,
            "error": f"the invocation door could not be run: {exc}",
        }
    out = (proc.stdout or "").strip()
    try:
        result = json.loads(out.splitlines()[-1]) if out else {}
    except (json.JSONDecodeError, IndexError):
        result = {}
    result.setdefault("invoked", False)
    result["rc"] = proc.returncode
    if not result.get("invoked") and proc.stderr:
        result["stderr"] = proc.stderr.strip()[-300:]
    return result


def raise_incident(fn: dict, result: dict, state: dict, dry_run: bool) -> dict | None:
    """The incident, the alert and the invocation -- deduplicated and backed off."""
    fid = result["id"]
    row = state.get(fid, {})
    now = time.time()
    last = float(row.get("last_alert", 0))
    backoff = int(row.get("backoff_s", BACKOFF_LADDER[0]))
    count = int(row.get("count", 0))
    if now - last < backoff:
        # Still inside the backoff: the incident is recorded, but nobody is woken again. A dead
        # function must not spawn an agent storm.
        result["suppressed_until"] = int(last + backoff)
        return None

    incident = {
        "id": f"{fid}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "function": fid,
        "title": result["title"],
        "severity": result["severity"],
        "verdict": result["verdict"],
        "detected_at": now_iso(),
        "why": result["why"],
        "evidence": {"liveness": result["liveness"], "goal": result["goal"]},
        "occurrences": count + 1,
    }
    if dry_run:
        return incident

    INCIDENTS.mkdir(parents=True, exist_ok=True)
    try:
        (INCIDENTS / f"{incident['id']}.json").write_text(
            json.dumps(incident, indent=1)
        )
    except OSError:
        pass
    try:
        with LEDGER.open("a") as fh:
            fh.write(json.dumps(incident) + "\n")
    except OSError:
        pass

    level = "error" if result["verdict"] == FAIL else "warning"
    if result["verdict"] == FAIL:
        # A dead critical function gets an agent with the structured data to resolve it. A BLIND
        # probe is a measurement that could not be made: it is alerted, but no agent is woken for
        # it -- the function may be perfectly well.
        incident["invocation"] = invoke_agent(fn, incident)
    else:
        incident["invocation"] = {
            "invoked": False,
            "reason": "BLIND: no agent is woken for a probe that could not be measured",
        }

    alert(
        "critical-watch",
        level,
        f"{fid}: {result['verdict']} -- {result['why']} (incident {incident['id']})",
    )
    try:
        LATEST.write_text(json.dumps(incident, indent=1))
    except OSError:
        pass

    state[fid] = {
        "last_alert": now,
        "count": count + 1,
        "backoff_s": min(backoff * 2, BACKOFF_LADDER[-1]),
        "last_incident": incident["id"],
    }
    return incident


def write_heartbeat(summary: dict) -> None:
    payload = {"at": now_iso(), "pid": os.getpid(), **summary}
    try:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        tmp = HEARTBEAT.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1))
        os.replace(tmp, HEARTBEAT)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="critical-watch", description=__doc__.split("\n")[0]
    )
    ap.add_argument("--registry", help="path to catalog/critical-functions.json")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    ap.add_argument(
        "--dry-run", action="store_true", help="measure and report; raise nothing"
    )
    ap.add_argument("--only", help="check one function id")
    a = ap.parse_args(argv)

    reg_path = registry_path(a.registry)
    if reg_path is None:
        msg = "no critical-functions registry found (looked in the repo, the runtime tree and $CRITICAL_WATCH_REGISTRY)"
        if a.json:
            print(json.dumps({"verdict": BLIND, "error": msg}))
        else:
            print(f"BLIND {msg}")
        write_heartbeat({"state": "blind", "error": msg})
        return 2
    try:
        registry = json.loads(reg_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLIND the registry {reg_path} could not be read: {exc}")
        write_heartbeat({"state": "blind", "error": str(exc)})
        return 2

    functions = registry.get("functions", [])
    if a.only:
        functions = [f for f in functions if f.get("id") == a.only]
        if not functions:
            print(f"BLIND no function named {a.only} in {reg_path}")
            return 2

    results = [check_function(f) for f in functions]
    state = load_backoff()
    incidents = []
    for fn, res in zip(functions, results):
        if res["verdict"] == PASS:
            # A function that comes back stops counting against itself: its backoff resets, so a
            # later failure alerts immediately instead of waiting out the ladder it climbed.
            if res["id"] in state:
                state.pop(res["id"], None)
            continue
        incident = raise_incident(fn, res, state, a.dry_run)
        if incident:
            incidents.append(incident)
    if not a.dry_run:
        save_backoff(state)

    verdicts = [r["verdict"] for r in results]
    summary = {
        "at": now_iso(),
        "registry": str(reg_path),
        "functions": results,
        "incidents": [i["id"] for i in incidents],
        "counts": {v: verdicts.count(v) for v in (PASS, FAIL, BLIND)},
    }
    write_heartbeat(
        {
            "state": "ok" if FAIL not in verdicts else "failing",
            "counts": summary["counts"],
            "registry": str(reg_path),
        }
    )
    if a.json:
        print(json.dumps(summary, indent=1))
    else:
        for r in results:
            print(f"{r['verdict']:<5} {r['id']:<20} {r['why']}")
        for i in incidents:
            inv = i.get("invocation", {})
            via = inv.get("invoked_via", "not invoked")
            print(f"incident {i['id']} alerted; agent invoked via {via}")
    if FAIL in verdicts:
        return 1
    if BLIND in verdicts:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
