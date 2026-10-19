"""Active Focus, derived from the claim ledger instead of typed by hand (idp#6543 follow-on).

The defect this retires: "ACTIVE FOCUS claim idp6525 ..." was an ordinary memory fact. Nothing
flipped it when the claim closed, and the only retirement lived in bin/estate-brief -- the
session-start hook. The `brief` and `recall` tools agents call mid-session go through
bin/estate-memory-mcp straight to the server, so they kept returning the ghost (measured
2026-10-19: both tools returned two dead idp6525 focus facts while the hook dropped them).

Two rules, both enforced where every runtime passes (the hook AND the bridge):

  1. A hand-written focus fact whose claim is CLOSED is dropped from any result (`drop_stale`).
  2. The focus itself is read from the ledger of record -- open GitHub issues with a CLAIM
     comment -- so it cannot be stale by construction (`live_focus`): a claim that closes leaves
     the register the next time it is read, with nobody having to remember to retire anything.

Every lookup fails open: a flaky gh, a missing token or a slow answer returns "unknown" and the
facts are kept. A brief must never cost a session its memory (AGENTS.md section 5: the
heartbeat, not a person, decides whether a claim is live).

Python 3.9 is the system python3 on macOS and runs this file, so no `X | None` at runtime.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import time

# S607: an absolute path, never a partial one (bin/treewalk.py). Without git on PATH every caller
# answers "unknown", which never flags a claim stuck.
GIT = shutil.which("git")

# A fact that starts like this is an agent's hand-written focus marker.
FOCUS_CLAIM_RE = re.compile(
    r"^\s*ACTIVE FOCUS claim\s+([A-Za-z]*)#?(\d+)\b", re.IGNORECASE
)
CLAIM_COMMENT_RE = re.compile(
    r"CLAIM\s+agent=(\S+)\s+paths=(\S+)\s+heartbeat=(\S+)", re.IGNORECASE
)
CLAIM_REPOS = {"idp": "chidionyema/idp"}
DEFAULT_REPO = "chidionyema/idp"

# AGENTS.md section 5.4: no heartbeat for 2 hours releases the claim.
LAPSE_S = 2 * 3600
# Short, so a closed claim leaves the register within minutes. The old hook cached 3600s,
# which kept a ghost alive for a full hour after the issue closed.
STATE_TTL_S = 300.0
FOCUS_TTL_S = 300.0
STATE_TIMEOUT_S = 2.0  # gh stalls are a known flaky path; the brief never waits on one
FOCUS_TIMEOUT_S = 8.0
# A claim whose heartbeat is fresh is only evidence the agent is ALIVE. If it was opened this long
# ago and not one commit has touched its paths since, it is alive and not getting anywhere.
STUCK_AFTER_S = 3 * 3600


def _home() -> str:
    return os.environ.get("ESTATE_MEMORY_HOME") or os.path.join(
        os.path.expanduser("~"), ".estate", "memory"
    )


def cache_path() -> str:
    return os.path.join(_home(), "focus-claims.json")


def focus_cache_path() -> str:
    return os.path.join(_home(), "focus-register.json")


def load_json(path: str) -> dict:
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_json(path: str, data: dict) -> None:
    # a cache is an optimisation, never a dependency
    with contextlib.suppress(Exception):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)


def _gh(args: list, timeout: float):
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        r = subprocess.run(  # noqa: S603 - argv fixed by this module, never a shell string
            [gh, *args], capture_output=True, text=True, timeout=timeout
        )
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


def claim_state(num: int, prefix: str, cache: dict, path: str):
    """OPEN or CLOSED from GitHub through gh, cached STATE_TTL_S; None is unknown."""
    key = str(num)
    now = time.time()

    def ok(h):
        return (
            isinstance(h, dict)
            and now - h.get("at", 0) < STATE_TTL_S
            and h.get("state") in ("OPEN", "CLOSED")
        )

    hit = cache.get(key)
    if not ok(hit):
        disk = load_json(path)  # another session may have answered already
        if ok(disk.get(key)):
            cache[key] = disk[key]
            hit = cache[key]
    if ok(hit):
        return hit["state"]
    repo = CLAIM_REPOS.get(prefix.lower())
    out = (
        _gh(
            ["issue", "view", key, "--repo", repo, "--json", "state", "-q", ".state"],
            STATE_TIMEOUT_S,
        )
        if repo
        else None
    )
    state = out.strip() if out and out.strip() in ("OPEN", "CLOSED") else None
    if state:
        cache[key] = {"state": state, "at": now}
        save_json(path, cache)
    return state


def drop_stale(items: list, state_fn=None, path: str = ""):
    """(kept, dropped): focus facts whose claim is CLOSED out; everything else untouched."""
    if not items:
        return items, []
    state_fn = state_fn or claim_state
    path = path or cache_path()
    cache = load_json(path)
    kept, dropped = [], []
    for it in items:
        m = FOCUS_CLAIM_RE.match(it.get("text", "")) if isinstance(it, dict) else None
        if m and state_fn(int(m.group(2)), m.group(1), cache, path) == "CLOSED":
            dropped.append(it)
        else:
            kept.append(it)
    return kept, dropped


# --- the register: what the estate is working on right now, read from the ledger ---------------


def _parse_ts(ts: str):
    from datetime import datetime, timezone

    try:
        return (
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    except Exception:
        return None


def register_from_issues(issues: list, now: float) -> list:
    """The focus register from `gh issue list --json number,title,comments` rows.

    One row per open issue that carries a CLAIM comment; the NEWEST claim comment wins (a
    refreshed heartbeat supersedes the first claim). `live` is the heartbeat rule, not an
    opinion: heartbeat younger than LAPSE_S.
    """
    rows = []
    for issue in issues:
        newest = None
        opened = None
        for c in issue.get("comments") or []:
            m = CLAIM_COMMENT_RE.search(c.get("body", "") or "")
            if m:
                newest = m  # comments arrive oldest first
                if opened is None:
                    opened = _parse_ts(c.get("createdAt") or "")
        if not newest:
            continue
        hb = _parse_ts(newest.group(3))
        age = None if hb is None else max(0, int(now - hb))
        rows.append(
            {
                "claim": f"idp#{issue['number']}",
                "title": (issue.get("title") or "")[:120],
                "agent": newest.group(1),
                "paths": newest.group(2),
                "heartbeat_age_s": age,
                "live": age is not None and age < LAPSE_S,
                "opened_at": opened,
            }
        )
    rows.sort(key=lambda r: (not r["live"], r["heartbeat_age_s"] or 10**9))
    return rows


def last_commit_touching(paths: str):
    """Epoch of the newest commit on any known ref touching `paths` (a CLAIM paths= value).

    0 when none has; None when it cannot be told (no git, not in a repo, a git that stalls). Reads
    the refs this checkout already has -- no fetch -- so a stale checkout under-reports progress;
    the register says "as of the last fetch" rather than pretending otherwise.
    """
    specs = [p for p in paths.split(",") if p]
    if not specs or not GIT:
        return None
    try:
        r = subprocess.run(  # noqa: S603 - fixed argv; paths follow `--`, never parsed as flags
            [GIT, "log", "-1", "--all", "--format=%ct", "--", *specs],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    return int(out) if out.isdigit() else 0


def mark_stuck(rows: list, progress_fn=None, now: float = 0.0) -> list:
    """Flag live claims that are alive but not moving: opened STUCK_AFTER_S ago, no commit on their
    paths since. Sets `stuck` and `idle_s` on every row; only a LIVE claim can be stuck (a lapsed
    one is already free to take). Unknown progress is never called stuck."""
    progress_fn = progress_fn or last_commit_touching
    now = now or time.time()
    for r in rows:
        r["stuck"] = False
        r["idle_s"] = 0
        opened = r.get("opened_at")
        if not r["live"] or opened is None or now - opened < STUCK_AFTER_S:
            continue
        last = progress_fn(r["paths"])
        if last is None or last >= opened:
            continue
        r["stuck"] = True
        r["idle_s"] = int(now - opened)
    return rows


def live_focus(path: str = "", now: float = 0.0):
    """The register as a list of rows, or None when the ledger could not be read (unknown)."""
    path = path or focus_cache_path()
    now = now or time.time()
    hit = load_json(path)
    if now - hit.get("at", 0) < FOCUS_TTL_S and isinstance(hit.get("rows"), list):
        return hit["rows"]
    # A heartbeat is a comment, and a comment updates its issue: every live claim is on an issue
    # touched inside the lapse window. Asking only for those, newest first, keeps the answer
    # complete under the cap. Unfiltered, 130+ claimed issues came back in best-match order and
    # a claim refreshed minutes earlier fell past the 50th row.
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - LAPSE_S))
    out = _gh(
        [
            "issue",
            "list",
            "--repo",
            DEFAULT_REPO,
            "--state",
            "open",
            "--search",
            f"CLAIM agent= in:comments updated:>={since} sort:updated-desc",
            "--limit",
            "50",
            "--json",
            "number,title,comments",
        ],
        FOCUS_TIMEOUT_S,
    )
    if out is None:
        return None
    try:
        rows = mark_stuck(register_from_issues(json.loads(out), now), now=now)
    except Exception:
        return None
    save_json(path, {"at": now, "rows": rows})
    return rows


MAX_RENDERED = 8


def render_register(rows) -> str:
    """Prose a session reads: the LIVE claims, newest heartbeat first. Lapsed claims are counted,
    not listed -- a brief that lists 30 dead claims buries the 3 that matter."""
    if rows is None:
        return ""
    live = [r for r in rows if r["live"]]
    lapsed = len(rows) - len(live)
    if not live:
        return (
            "Active focus: no live claim. Claim before changing files (bin/claim-open)."
        )
    out = ["Active focus (read from open claims, so never stale):"]
    for r in live[:MAX_RENDERED]:
        age = r["heartbeat_age_s"]
        paths = [p for p in r["paths"].split(",") if p]
        shown = ",".join(paths[:2]) + (
            f" +{len(paths) - 2} more" if len(paths) > 2 else ""
        )
        flag = (
            f" STUCK {r['idle_s'] // 3600}h: alive, but no commit on its paths since it opened"
            if r.get("stuck")
            else ""
        )
        out.append(
            f"- {r['claim']} {r['agent']}: {r['title'][:90]} "
            f"(paths {shown}; heartbeat {age // 60}m ago){flag}"
        )
    if len(live) > MAX_RENDERED:
        out.append(f"- ... and {len(live) - MAX_RENDERED} more live claims")
    if any(r.get("stuck") for r in live):
        out.append(
            "(STUCK is read from this checkout's refs as of the last fetch: ask the holder or "
            "fetch before taking the work over.)"
        )
    if lapsed:
        out.append(
            f"({lapsed} recently touched claims have lapsed heartbeats and are free to take.)"
        )
    return "\n".join(out)


# --- scrubbing MCP tool results -----------------------------------------------------------------

SCRUBBED_KEYS = {"brief": ("relevant", "recent"), "recall": ("memories",)}


def scrub(tool: str, payload: dict, state_fn=None, path: str = ""):
    """Drop ghost focus facts from a brief/recall payload in place; return the dropped items."""
    dropped_all = []
    for key in SCRUBBED_KEYS.get(tool, ()):
        if isinstance(payload.get(key), list):
            payload[key], dropped = drop_stale(payload[key], state_fn, path)
            dropped_all += dropped
    return dropped_all
