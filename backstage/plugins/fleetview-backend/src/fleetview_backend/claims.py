"""FleetView: the live agent claims, which AGENTS.md section 5 promises on /fleet and nothing
rendered.

WHY THIS EXISTS. Section 5 of AGENTS.md is a law with a surface attached:

    "The founder sees every live claim on /fleet: who, what, which paths, and heartbeat age."

Measured 2026-10-12 across every fleet surface: the words `greenlane` and `lane` do not appear,
and `claim` appears only as fleetBoard.ts's epistemic caveat ("a claim about elapsed time").
The claim is the estate's collision contract -- the thing that stops ten agents working the
same files -- and the founder could not see one of them. This module reads them.

WHERE A CLAIM LIVES. The claim of record is a comment on an open GitHub issue (AGENTS.md
section 5 rule 2), in exactly this shape, and the shape is not re-invented here: the pattern
below is the one `bin/claim-gate` refuses lanes against and `greenlane/github.py` refreshes,
kept identical on purpose. The issue is GitHub's because the gate that refuses a lane reads it
there; a claim read from anywhere else would be a second record that can disagree with the one
that blocks a merge.

WHY IT READS A WINDOW, NOT THE ISSUE LIST. The obvious read is "list the open issues, then read
each one's comments". Measured 2026-10-12: the repo carries 99 open issues holding 8878
comments, so that read is hundreds of API calls per refresh and would eat the hourly budget for
one panel. A claim that is live has a heartbeat under 2 hours old, and a heartbeat is a comment,
so every live claim is a comment inside the window. `GET /repos/{repo}/issues/comments?since=`
returns them in one call per 100 comments, newest first. Measured: 24 h of comments hit the
100-per-page cap exactly, so the default window is 12 h and it paginates up to MAX_PAGES.

The window is reported back (window_h) rather than hidden: a claim older than it was not read,
and a panel that showed "no claims" for a claim it never looked at would be the same lie as a
green lane that could not be read.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fleetview_backend import agent_jobs

# The heartbeat's limit, from bin/claim-gate (MAX_AGE = 2 h): a claim with no heartbeat for two
# hours is released and the next agent may take the issue. Kept as its own name because the
# panel colours the row by it, and a copied 2 * 3600 in the page would drift from the gate.
MAX_AGE_S = 2 * 60 * 60

# One windowed read per half minute. The founder's phone polls at 10-15 s and every poll
# landing on GitHub would be 200+ calls a minute for a page that changes hourly.
CACHE_S = 30
WINDOW_H = 12
PAGE = 100
MAX_PAGES = 3

# The claim comment, byte for byte the pattern bin/claim-gate judges and greenlane/github.py
# stamps. `model=` is optional and read by nothing (AGENTS.md 2026-10-10); it is matched so a
# claim that still carries it parses instead of vanishing.
CLAIM = re.compile(
    r"^CLAIM\s+agent=(?P<agent>\S+)\s+(?:model=\S+\s+)?paths=(?P<paths>\S+)\s+"
    r"heartbeat=(?P<hb>\S+)\s*$",
    re.M,
)
_ISSUE_FROM_URL = re.compile(r"/issues/(?P<n>\d+)$")

_cache: dict[str, Any] = {"at": 0.0, "body": None}


def _now_iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _age_s(hb: str, now: float) -> float | None:
    """Seconds since the claim's heartbeat, or None when the stamp is not a UTC ISO time.

    None is a real answer and is returned as one: a claim whose heartbeat cannot be read is not
    "live", and a silent 0 would make an unreadable claim look like the freshest one on the page
    (the same defect bin/claim-gate names -- "heartbeat {hb!r} is not a UTC ISO time").
    """
    try:
        stamp = datetime.fromisoformat(hb.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return now - stamp.timestamp()


def _reason(age: float | None, issue_open: bool | None) -> str:
    """Why a claim is or is not live, as one word the panel can print.

    Two different things stop a claim being live and they call for different reactions: a
    closed issue is work that finished and released its claim (AGENTS.md section 5 rule 6,
    "closing it releases the claim"), while a stale heartbeat is an agent that went quiet on
    work still open. A single boolean would report both as "not live" and the founder could
    not tell finished from abandoned. `issue_open is None` is also a real answer -- the search
    index lags a just-created issue -- and it must not be read as closed.
    """
    if issue_open is False:
        return "issue closed"
    if age is None:
        return "unreadable heartbeat"
    if age >= MAX_AGE_S:
        return "stale heartbeat"
    return "live"


def _claims_from_comments(
    now: float, comments: list[dict]
) -> dict[int, dict[str, Any]]:
    """Newest claim per issue. A refresh is a new comment, not an edit, so the newest wins."""
    newest: dict[int, dict[str, Any]] = {}
    for c in comments:
        body = c.get("body") or ""
        for m in CLAIM.finditer(body):
            issue = _issue_from_url(c.get("issue_url") or "")
            if issue is None:
                continue
            row = {
                "issue": issue,
                "agent": m.group("agent"),
                "paths": [p for p in m.group("paths").split(",") if p],
                "heartbeat": m.group("hb"),
                "age_s": _age_s(m.group("hb"), now),
                "comment_at": c.get("created_at"),
            }
            prev = newest.get(issue)
            # The later comment wins; a comment with no parseable stamp loses to one with a
            # stamp (an unreadable stamp is a broken claim, not a fresher one).
            if prev is None or (_sort_key(row) >= _sort_key(prev)):
                newest[issue] = row
    return newest


def _sort_key(row: dict[str, Any]) -> tuple[int, float]:
    age = row.get("age_s")
    return (0, -age) if isinstance(age, (int, float)) else (1, 0.0)


def _issue_from_url(url: str) -> int | None:
    m = _ISSUE_FROM_URL.search(url)
    return int(m.group("n")) if m else None


def _issue_index(repo: str) -> dict[int, dict[str, Any]]:
    """{issue: {title, open}} for every issue whose comments carry a claim, in one call.

    Measured 2026-10-12: this search returns all 79 of them -- 38 open and 41 closed -- with
    each title and state. That is what lets the panel say WHAT a claim is even after its issue
    closed, and tell a released claim from a stale one. The comments window cannot tell those
    apart, and `state=open` on the issue list returned no title for any closed issue, which was
    ten of the thirteen claims read that day. A brand-new issue is not indexed yet; it is left
    out rather than guessed at, and `_reason` reads its absence as unknown, not closed.
    """
    status, body = agent_jobs.gh_get(
        f"/search/issues?q={_search_query(repo)}&per_page={PAGE}"
    )
    if status != 200 or not isinstance(body, dict):
        return {}
    return {
        int(i["number"]): {
            "title": str(i.get("title") or ""),
            "open": i.get("state") == "open",
        }
        for i in body.get("items", [])
        if isinstance(i, dict) and "number" in i
    }


def _search_query(repo: str) -> str:
    # The claim's own shape, so the search matches the same comments CLAIM above parses.
    return f"repo:{repo}+is:issue+in:comments+%22CLAIM+agent=%22"


def _window_comments(repo: str, since: str) -> tuple[list[dict], bool]:
    """(comments, truncated). Newest first; stops at the first short page or MAX_PAGES."""
    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        path = (
            f"/repos/{repo}/issues/comments?since={since}"
            f"&per_page={PAGE}&sort=created&direction=desc&page={page}"
        )
        status, body = agent_jobs.gh_get(path)
        if status != 200 or not isinstance(body, list):
            # A page that cannot be read is not "no more comments": stop, and say the window
            # is short so the caller can report a partial read instead of an empty board.
            return out, True
        out += [c for c in body if isinstance(c, dict)]
        if len(body) < PAGE:
            return out, False
    return out, True


def claims_snapshot(now: float | None = None) -> dict[str, Any]:
    """The live claims as of now. An unreadable read is `available: false` with its reason --
    never an empty list, which would say "nobody holds anything" at the exact moment the estate
    cannot tell (the same rule greenlane.py follows for main)."""
    t = now if now is not None else time.time()
    if _cache["body"] is not None and t - _cache["at"] < CACHE_S:
        return _cache["body"]

    repo = agent_jobs.repo()
    since = (
        datetime.fromtimestamp(t, timezone.utc) - timedelta(hours=WINDOW_H)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        comments, truncated = _window_comments(repo, since)
        claims = _claims_from_comments(t, comments)
        index = _issue_index(repo)
    except Exception as exc:  # noqa: BLE001 -- the panel shows the reason; a 500 hides it
        body = {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "claims": [],
            "counts": {"live": 0, "released": 0, "stale": 0, "issues": 0},
            "source": f"{repo} issue comments",
            "window_h": WINDOW_H,
            "truncated": False,
        }
    else:
        rows = []
        for issue, row in claims.items():
            meta = index.get(issue) or {}
            issue_open = meta.get("open") if meta else None
            reason = _reason(row["age_s"], issue_open)
            rows.append(
                {
                    **row,
                    "title": meta.get("title"),
                    "issue_open": issue_open,
                    "reason": reason,
                    "live": reason == "live",
                    "url": f"https://github.com/{repo}/issues/{issue}",
                    "age_s": (
                        round(row["age_s"], 1)
                        if isinstance(row["age_s"], (int, float))
                        else None
                    ),
                }
            )
        # Live first, then freshest -- the row the founder must act on is the one they see.
        rows.sort(key=lambda r: (not r["live"], r["age_s"] is None, r["age_s"] or 0.0))
        body = {
            "available": True,
            "error": None,
            "claims": rows,
            "counts": {
                "live": sum(1 for r in rows if r["reason"] == "live"),
                "released": sum(1 for r in rows if r["reason"] == "issue closed"),
                "stale": sum(
                    1
                    for r in rows
                    if r["reason"] in ("stale heartbeat", "unreadable heartbeat")
                ),
                "issues": len(rows),
            },
            "source": f"{repo} issue comments",
            "window_h": WINDOW_H,
            "truncated": truncated,
        }
    body["read_at"] = _now_iso(t)
    _cache.update(at=t, body=body)
    return body
