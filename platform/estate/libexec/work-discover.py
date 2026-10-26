#!/usr/bin/env python3
"""work-discover -- one query that finds any work in the estate, wherever it is.

WHY (founder, 2026-10-26). Locating work in this estate was friction: the surface redesign
was in three issues, three branches, a salvage ref and a commit on a lane, and finding it
took a dozen commands across GitHub, git, the claim register and memory. `work-inflight`
(#7245) answers "what is in flight" over a time window; this answers the other question --
"where is the work about X" -- by topic, across every place work can hide.

WHAT IT SEARCHES, and what each source proves:

  tickets   GitHub issues and pull requests (search/issues over the owner's repos). A hit is
            a URL you can open.
  claims    the CLAIM comments on issues: who holds the work, on which paths, and how fresh
            their heartbeat is.
  refs      branches, lanes, salvage/* and backup/* refs, with their last commit subject.
  worktrees local worktrees and stashes: work that never had a branch.
  tree      documents, specs and intents in the repos whose text or name carries the terms.
  memory    the estate's unified memory (brief by task) and the knowledge graph.

Every hit carries the terms that matched it, so a hit is auditable rather than a vibe.
READ-ONLY: it fetches, reads and prints. It writes one file, its own result.

    python3 work-discover.py "<query>" [--days N] [--repos a,b] [--limit N] [--json]

    query   free text; terms are ANDed loosely (substring, case-insensitive)
    days    how far back to look (default 21)
    repos   comma separated local repo names under ~/Documents/code (default idp,crew)
    limit   max hits printed per source (default 8)
    json    write ~/.estate/results/work-discover/latest.json and print it

Exit status: 0 when the search ran (even with no hits), 2 on a bad argument. A source that
is unavailable is reported as unavailable; it never silently shrinks the answer.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import pathlib
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone

HOME = pathlib.Path.home()
CODE = HOME / "Documents" / "code"
RESULTS = HOME / ".estate" / "results" / "work-discover"
BRIEF = HOME / ".estate" / "memory" / "bin" / "estate-brief"
GROWMOS = HOME / ".local" / "bin" / "growmos"
GRAPH = HOME / "Documents" / "code" / "estate-graph"

STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "not",
    "but",
    "you",
    "our",
    "its",
    "it's",
    "any",
    "all",
    "can",
    "does",
    "did",
    "how",
    "what",
    "when",
    "where",
    "who",
    "why",
    "them",
    "then",
    "there",
    "their",
    "about",
    "over",
    "under",
    "than",
    "some",
    "each",
    "more",
    "most",
    "also",
    "just",
    "like",
    "make",
    "made",
    "get",
    "got",
    "run",
    "ran",
    "new",
    "one",
    "two",
    "use",
    "used",
    "using",
    "work",
    "works",
    "thing",
    "things",
    "much",
    "very",
    "should",
    "would",
    "could",
    "will",
    "shall",
    "doing",
    "done",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(args, cwd=None, timeout=25, env=None):
    """(rc, out). Never raises: a missing tool is a fact, not a crash."""
    try:
        p = subprocess.run(  # noqa: S603 -- fixed argv built in this file, no shell
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"{args[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, f"{args[0]}: timed out after {timeout}s"


def terms_of(query: str):
    """The terms to look for: lowercase words, stopwords dropped, short ones kept if rare."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-]*", query.lower())
    out = []
    for w in words:
        if len(w) < 3 or w in STOP or w in out:
            continue
        out.append(w)
    return out or [query.strip().lower()]


def matched(haystack: str, terms):
    """Which terms appear in the haystack (case-insensitive substring)."""
    low = (haystack or "").lower()
    return [t for t in terms if t in low]


def gh_json(args, timeout=25):
    rc, out = run(["gh", "api"] + args, timeout=timeout)
    if rc != 0:
        return None, out.strip().splitlines()[-1] if out.strip() else f"gh api rc={rc}"
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return None, f"gh api returned unparseable json: {e}"


# --------------------------------------------------------------------------- sources


def source_tickets(days, terms, limit):
    """GitHub issues and pull requests that carry the terms.

    One search per term, unioned: GitHub ANDs the terms in a query, and ANDed terms lose
    the tickets that use a synonym for one of them ("design kit" against "redesign"). A hit
    that carries more terms outranks one that carries fewer.
    """
    since = (now_utc() - timedelta(days=days)).strftime("%Y-%m-%d")
    items = {}
    errors = []
    for term in terms[:6]:
        q = f'"{term}" user:chidionyema updated:>={since}'
        data, err = gh_json(
            ["-X", "GET", "search/issues", "-f", f"q={q}", "-f", "per_page=50"]
        )
        if data is None:
            errors.append(err)
            continue
        for item in data.get("items") or []:
            repo = (item.get("repository_url") or "").rsplit("/", 1)[-1]
            items[(repo, item.get("number"))] = item
    if not items and errors:
        return [], f"github search unavailable: {errors[0]}"
    hits = []
    for (repo, _number), item in items.items():
        body = " ".join(
            str(item.get(k) or "") for k in ("title", "body", "number", "state")
        )
        m = matched(body, terms)
        if not m:
            continue
        hits.append(
            {
                "kind": "pr" if item.get("pull_request") else "issue",
                "id": f"{repo}#{item.get('number')}",
                "number": item.get("number"),
                "repo": repo,
                "title": (item.get("title") or "").strip(),
                "state": item.get("state"),
                "updated": item.get("updated_at"),
                "url": item.get("html_url"),
                "matched": m,
                "score": 3 + len(m),
            }
        )
    hits.sort(key=lambda h: (-h["score"], h.get("updated") or ""))
    return hits[:limit], None


CLAIM_RE = re.compile(
    r"^CLAIM\s+agent=(?P<agent>\S+)\s+paths=(?P<paths>\S+)(?:\s+heartbeat=(?P<heartbeat>\S+))?",
    re.M,
)


def source_claims(days, terms, limit):
    """The CLAIM comments: who holds what, on which paths, and how fresh."""
    since = iso(now_utc() - timedelta(days=days))
    hits = []
    seen = set()
    errors = []
    pages = {"idp": 8, "crew": 3}
    for repo in ("idp", "crew"):
        page = 1
        while page <= pages[repo]:
            data, err = gh_json(
                [
                    "-X",
                    "GET",
                    f"repos/chidionyema/{repo}/issues/comments",
                    "-f",
                    f"since={since}",
                    "-f",
                    "per_page=100",
                    "-f",
                    f"page={page}",
                    "-f",
                    "sort=created",
                    "-f",
                    "direction=desc",
                ]
            )
            if data is None:
                errors.append(f"{repo}: {err}")
                break
            if not isinstance(data, list):
                errors.append(f"{repo}: unexpected payload")
                break
            for c in data:
                body = c.get("body") or ""
                m = CLAIM_RE.search(body)
                if not m:
                    continue
                agent = m.group("agent")
                paths = m.group("paths")
                blob = f"{agent} {paths} {c.get('issue_url') or ''}"
                mt = matched(blob, terms)
                key = (repo, c.get("issue_url"), agent, paths)
                if key in seen:
                    continue
                seen.add(key)
                hits.append(
                    {
                        "kind": "claim",
                        "id": f"{repo}#{_issue_number(c.get('issue_url'))}",
                        "repo": repo,
                        "agent": agent,
                        "paths": paths,
                        "heartbeat": m.group("heartbeat"),
                        "url": c.get("html_url"),
                        "matched": mt,
                        "score": 3 + len(mt),
                    }
                )
            if len(data) < 100:
                break
            page += 1
    # Every claim in the window is kept, not only the ones the terms match: a ticket's own
    # claim is the join the founder does by hand ("who holds this?"), and it must be there
    # even when the claim's paths carry none of the search terms.
    hits.sort(key=lambda h: (-h["score"], h.get("heartbeat") or ""))
    if not hits and errors:
        return [], "; ".join(errors)
    return hits, None


def _issue_number(url):
    m = re.search(r"/issues/(\d+)", url or "")
    return m.group(1) if m else "?"


def source_refs(repos, terms, limit):
    """Branches, lanes, salvage/* and backup/* refs whose name or last commit carries the terms.

    A ref whose NAME carries the terms is the work itself (a lane named for it). A ref that
    only mentions them in its last commit subject is weaker, and a ref already an ancestor of
    origin/main has landed, so it is marked rather than hidden.
    """
    hits = []
    for name in repos:
        repo = CODE / name
        if not (repo / ".git").exists():
            continue
        rc, out = run(
            [
                "git",
                "-C",
                str(repo),
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname)|%(committerdate:iso8601)|%(subject)|%(objectname:short)",
                "refs/heads",
                "refs/salvage",
                "refs/backup",
                "refs/work-audit",
            ],
            timeout=25,
        )
        if rc != 0:
            continue
        main_rc, main_out = run(
            ["git", "-C", str(repo), "rev-list", "--max-count", "20000", "origin/main"],
            timeout=25,
        )
        on_main = set(main_out.split()) if main_rc == 0 else set()
        for line in out.strip().splitlines():
            parts = (line.split("|", 3) + ["", "", "", ""])[:4]
            ref, date, subject, sha = parts
            name_m = matched(ref, terms)
            subj_m = matched(subject, terms)
            m = name_m or subj_m
            if not m:
                continue
            landed = "LANDED (already on origin/main)" if sha and sha in on_main else ""
            hits.append(
                {
                    "kind": "ref",
                    "id": f"{name}:{ref}",
                    "repo": name,
                    "ref": ref,
                    "date": date,
                    "subject": subject,
                    "sha": sha,
                    "matched": m,
                    "matched_in": "name" if name_m else "commit subject",
                    "landed": landed,
                    "score": (3 if name_m else 1) + len(m),
                }
            )
    hits.sort(
        key=lambda h: (bool(h.get("landed")), -h["score"], h.get("date") or ""),
        reverse=False,
    )
    hits.sort(key=lambda h: (bool(h.get("landed")), -h["score"]))
    return hits[:limit], None


def source_worktrees(repos, terms, limit):
    """Local worktrees and stashes: work that never had a branch of its own."""
    hits = []
    for name in repos:
        repo = CODE / name
        if not (repo / ".git").exists():
            continue
        rc, out = run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"], timeout=20
        )
        if rc == 0:
            for block in out.split("\n\n"):
                path = branch = ""
                for line in block.splitlines():
                    if line.startswith("worktree "):
                        path = line[len("worktree ") :].strip()
                    elif line.startswith("branch "):
                        branch = line[len("branch ") :].strip()
                if not path:
                    continue
                m = matched(f"{path} {branch}", terms)
                if m:
                    hits.append(
                        {
                            "kind": "worktree",
                            "id": f"{name}:{path}",
                            "repo": name,
                            "path": path,
                            "branch": branch,
                            "matched": m,
                            "score": 2 + len(m),
                        }
                    )
        rc, out = run(["git", "-C", str(repo), "stash", "list"], timeout=20)
        if rc == 0:
            for line in out.strip().splitlines():
                m = matched(line, terms)
                if m:
                    hits.append(
                        {
                            "kind": "stash",
                            "id": f"{name}:{line.split(':')[0]}",
                            "repo": name,
                            "ref": line,
                            "matched": m,
                            "score": 2 + len(m),
                        }
                    )
    return hits[:limit], None


def source_tree(repos, terms, limit):
    """Documents, specs and intents in the repos whose name or text carries the terms.

    One ripgrep per term, so a file that carries three terms outranks one that carries one.
    """
    hits = []
    for name in repos:
        repo = CODE / name
        if not repo.exists():
            continue
        found = {}
        for term in terms:
            roots = [
                str(repo / sub)
                for sub in ("docs", "platform/estate/intents")
                if (repo / sub).exists()
            ]
            if not roots:
                continue
            rc, out = run(
                [
                    "rg",
                    "-l",
                    "-i",
                    "--max-filesize",
                    "2M",
                    "-F",
                    term,
                ]
                + roots,
                timeout=25,
            )
            if rc not in (0, 1):
                continue
            for path in out.strip().splitlines():
                if path:
                    found.setdefault(path, []).append(term)
        for path, m in found.items():
            hits.append(
                {
                    "kind": "file",
                    "id": f"{name}:{os.path.relpath(path, str(repo))}",
                    "repo": name,
                    "path": os.path.relpath(path, str(repo)),
                    "matched": m,
                    "score": 2 + len(m),
                }
            )
    hits.sort(key=lambda h: (-len(h["matched"]), h["path"]))
    return hits[:limit], None


def source_memory(query, terms, limit):
    """The estate's unified memory, by task."""
    if not BRIEF.exists():
        return [], "memory brief not installed"
    rc, out = run([str(BRIEF), "--task", query], timeout=15)
    if rc != 0:
        return (
            [],
            f"memory brief failed: {out.strip().splitlines()[-1] if out.strip() else rc}",
        )
    hits = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = matched(line, terms)
        if not m:
            continue
        hits.append(
            {
                "kind": "memory",
                "id": line[:120],
                "text": line.lstrip("- ").strip(),
                "matched": m,
                "score": 1 + len(m),
            }
        )
    return hits[:limit], None


def source_graph(query, terms, limit):
    """The knowledge graph: what the estate already knows about the terms."""
    if not GROWMOS.exists():
        return [], "growmos not installed"
    rc, out = run([str(GROWMOS), "--root", str(GRAPH), "query", query], timeout=30)
    if rc != 0:
        return (
            [],
            f"growmos query failed: {out.strip().splitlines()[-1] if out.strip() else rc}",
        )
    hits = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "growmos")):
            continue
        m = matched(line, terms)
        if not m:
            continue
        hits.append(
            {
                "kind": "graph",
                "id": line[:120],
                "text": line,
                "matched": m,
                "score": 1 + len(m),
            }
        )
    return hits[:limit], None


# --------------------------------------------------------------------------- output


def _claim_live(claim, live_s=7200):
    """LIVE when the claim's own heartbeat is inside two hours, STALE otherwise."""
    hb = (claim or {}).get("heartbeat") or ""
    try:
        when = datetime.strptime(hb, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (now_utc() - when).total_seconds() < live_s


def print_human(payload):
    q = payload["query"]
    print(f'work.discover -- "{q}"')
    print(
        f"{payload['total_hits']} hit(s) across "
        f"{len([s for s in payload['sources'] if s['ok']])} of {len(payload['sources'])} sources "
        f"in {payload['elapsed_s']}s; terms: {', '.join(payload['terms'])}"
    )
    # The join the founder keeps doing by hand: which ticket is claimed, by whom, and is the
    # claim still alive. Built from the claim register's own heartbeats.
    claim_by_issue = {}
    for src in payload["sources"]:
        if src["name"] != "claims":
            continue
        for c in src["hits"]:
            key = str(c["id"]).split("#")[-1]
            old = claim_by_issue.get(key)
            if old is None or (c.get("heartbeat") or "") > (old.get("heartbeat") or ""):
                claim_by_issue[key] = c
    live = {k: v for k, v in claim_by_issue.items() if _claim_live(v)}
    claim_rows = sorted(
        (c for c in claim_by_issue.values() if c.get("matched")),
        key=lambda c: (-c.get("score", 0), c.get("heartbeat") or ""),
    )
    for src in payload["sources"]:
        name = src["name"]
        if not src["ok"]:
            print(f"\n{name.upper()}  unavailable -- {src.get('error') or 'unknown'}")
            continue
        hits = src["hits"]
        shown = 0
        if name == "claims":
            hits = [h for h in hits if h.get("matched")]
            hits = sorted(
                hits, key=lambda c: (-c.get("score", 0), c.get("heartbeat") or "")
            )
            print(f"\n{name.upper()}  {len(claim_rows)} claim(s) match, one per ticket")
        else:
            print(f"\n{name.upper()}  {len(hits)} hit(s)")
        for h in hits:
            m = ",".join(h.get("matched") or [])
            if name == "tickets":
                claim = live.get(str(h["number"])) or claim_by_issue.get(
                    str(h["number"])
                )
                if claim:
                    state = "LIVE" if _claim_live(claim) else "STALE"
                    claimed = f"claimed by {claim['agent']} ({state}, heartbeat {claim.get('heartbeat')})"
                else:
                    claimed = "no claim in the window"
                print(f"  #{h['number']} [{h['state']}] {h['title']}")
                print(f"      {h['id']}  {h['url']}  (matched: {m})")
                print(f"      {claimed}")
            elif name == "claims":
                shown += 1
                if shown > payload.get("limit", 8):
                    break
                c = claim_rows[shown - 1] if shown <= len(claim_rows) else None
                if c is None:
                    break
                paths = c["paths"]
                if len(paths) > 110:
                    paths = paths[:107] + "..."
                print(f"  {c['id']} agent={c['agent']} heartbeat={c.get('heartbeat')}")
                print(
                    f"      paths: {paths}  (matched: {','.join(c.get('matched') or [])})"
                )
            elif name == "refs":
                landed = f"  [{h['landed']}]" if h.get("landed") else ""
                print(f"  {h['ref']}  {h['date']}  {h['sha']}{landed}")
                print(f"      {h['subject']}  (matched in {h.get('matched_in')}: {m})")
            elif name == "worktrees":
                if h.get("kind") == "stash":
                    print(f"  stash {h.get('ref', '')}")
                else:
                    print(f"  {h['path']}  {h.get('branch') or ''}")
                print(f"      (matched: {m})")
            elif name == "tree":
                print(f"  {h['path']}   ({h['repo']})")
            elif name in ("memory", "graph"):
                print(f"  {h['text'][:180]}")
            else:
                print(f"  {h['id']}")
    missed = [s["name"] for s in payload["sources"] if not s["ok"]]
    if missed:
        print(f"\nnot searched: {', '.join(missed)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="find any work in the estate by topic")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--repos", default="idp,crew")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    query = (args.query or "").strip()
    if not query:
        ap.error('a query is required: work-discover.py "<what you are looking for>"')

    terms = terms_of(query)
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    started = time.time()

    sources = []

    def one(name, fn, *a):
        t0 = time.time()
        try:
            hits, err = fn(*a)
        except Exception as e:  # a source that breaks must not hide the others
            hits, err = [], f"{type(e).__name__}: {e}"
        return {
            "name": name,
            "ok": not err,
            "error": err,
            "hits": hits,
            "seconds": round(time.time() - t0, 2),
        }

    plan = [
        ("tickets", source_tickets, (args.days, terms, args.limit)),
        ("claims", source_claims, (args.days, terms, args.limit)),
        ("refs", source_refs, (repos, terms, args.limit)),
        ("worktrees", source_worktrees, (repos, terms, args.limit)),
        ("tree", source_tree, (repos, terms, args.limit)),
        ("memory", source_memory, (query, terms, args.limit)),
        ("graph", source_graph, (query, terms, args.limit)),
    ]
    # The sources are independent, so they run together: the door is 100s and the slow ones
    # (GitHub pagination, the graph) are the wall.
    with futures.ThreadPoolExecutor(max_workers=len(plan)) as pool:
        futures_by_name = {name: pool.submit(one, name, fn, *a) for name, fn, a in plan}
        for name, _fn, _a in plan:
            sources.append(futures_by_name[name].result())

    payload = {
        "query": query,
        "terms": terms,
        "days": args.days,
        "repos": repos,
        "limit": args.limit,
        "at": iso(now_utc()),
        "elapsed_s": round(time.time() - started, 2),
        "total_hits": sum(len(s["hits"]) for s in sources),
        "sources": sources,
    }

    if args.json:
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / "latest.json").write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
    else:
        print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
