#!/usr/bin/env python3
"""estate-rescue -- put the estate's in-flight work where a dead laptop cannot take it.

WHY (founder, 2026-10-28). "if macbook dies now, all that work is in the abyss ... no automated
continuity ... reliance on founder memory is stupid for autonomous estate". The census
(work-inflight) says WHERE the work is; it does not MOVE it. This does. Every local branch and
every worktree whose content is on no remote is copied to origin as a salvage branch, so the work
outlives the machine that made it and the next session can pick it up without anyone remembering
that it existed.

WHAT IT RESCUES
  branch    a local branch whose commits origin/main does not have and origin does not hold
            -> origin:refs/heads/backup/preserve-<date>-<name>
  worktree  a worktree with uncommitted changes -> the same, with the working tree captured
            through a TEMPORARY INDEX (the worktree's own index, files and HEAD are never
            touched, so the agent that owns it finds exactly what it left)
  stash     a stash -> origin:refs/heads/backup/preserve-<date>-stash-<n>

WHAT IT NEVER DOES
  - it never pushes to main, and never pushes anything but refs/heads/backup/preserve-*
  - it never deletes a branch, a ref, a stash, a worktree or a file
  - it never force-pushes
  - it never rescues a branch origin already holds, or one that is wholly on origin/main
  - it never claims a rescue it did not measure: the pushed ref is read back from origin, and
    the verdict says what origin now holds

EXIT: 0 nothing to rescue; 1 something was rescued; 2 BLIND (the repository could not be read).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("ESTATE_REPO", HOME / "Documents/code/idp"))
RESULTS = Path(
    os.environ.get("ESTATE_CONTINUITY_RESULTS", HOME / ".estate/results/continuity")
)
CENSUS = Path(
    os.environ.get(
        "ESTATE_CONTINUITY_CENSUS", HOME / ".estate/results/work-inflight/latest.json"
    )
)
RESCUE_MAX = int(os.environ.get("ESTATE_RESCUE_MAX", "25"))
RESCUE_SECONDS = int(os.environ.get("ESTATE_RESCUE_SECONDS", "240"))
PREFIX = "backup/preserve-"
GIT_TIMEOUT = 25
PUSH_TIMEOUT = 60
SAFE = re.compile(r"[^A-Za-z0-9._-]+")

RESCUE_IDENTITY = {
    "GIT_AUTHOR_NAME": "estate-rescue",
    "GIT_AUTHOR_EMAIL": "estate-rescue@localhost",
    "GIT_COMMITTER_NAME": "estate-rescue",
    "GIT_COMMITTER_EMAIL": "estate-rescue@localhost",
}


def git(args, repo=None, cwd=None, timeout=GIT_TIMEOUT, env=None):
    """(rc, out) for one git command. Never raises: an unreadable source is a fact, not a crash."""
    full_env = dict(os.environ)
    full_env.update(RESCUE_IDENTITY)
    if env:
        full_env.update(env)
    try:
        p = subprocess.run(
            ["git", "-C", str(cwd or repo or REPO)] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "git {}: timed out after {}s".format(" ".join(args), timeout)
    except OSError as exc:
        return 127, str(exc)


def slug(name):
    """A salvage branch name the estate can read: backup/preserve-<date>-<name>."""
    flat = SAFE.sub("-", name).strip("-")
    return "{}{}-{}".format(
        PREFIX, datetime.now(timezone.utc).strftime("%Y%m%d"), flat or "unnamed"
    )


def local_branches(repo):
    rc, out = git(
        ["for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"],
        repo=repo,
    )
    if rc != 0:
        return None, out.strip()[:200]
    rows = []
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0].strip():
            rows.append({"name": parts[0].strip(), "sha": parts[1].strip()})
    return rows, None


def origin_heads(repo):
    rc, out = git(["ls-remote", "--heads", "origin"], repo=repo)
    if rc != 0:
        return None, out.strip()[:200]
    return {
        line.split("\t")[1].replace("refs/heads/", "")
        for line in out.splitlines()
        if "\t" in line
    }, None


def main_commits(repo):
    """Every commit origin/main holds, in one git call.

    Asking git once per branch is one process per branch and the estate has sixty of them: one
    rev-list is the difference between a second and a minute, and this runs on a timer.
    """
    rc, out = git(["rev-list", "origin/main"], repo=repo, timeout=90)
    return set(out.split()) if rc == 0 else None


def on_main(sha, repo):
    """True when the commit is already on origin/main: nothing about it is at risk."""
    rc, _ = git(["merge-base", "--is-ancestor", sha, "origin/main"], repo=repo)
    return rc == 0


def dirty_worktrees(repo):
    """Worktrees with uncommitted changes, and the branch they sit on."""
    rc, out = git(["worktree", "list", "--porcelain"], repo=repo)
    if rc != 0:
        return None, out.strip()[:200]
    paths = []
    for line in out.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree ") :].strip())
    rows = []
    for path in paths:
        if not Path(path).exists():
            continue
        rc, status = git(["status", "--porcelain"], cwd=path)
        if rc != 0:
            continue
        changed = [ln for ln in status.splitlines() if ln.strip()]
        if not changed:
            continue
        rc, head = git(["rev-parse", "HEAD"], cwd=path)
        rc2, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
        rows.append(
            {
                "path": path,
                "name": Path(path).name,
                "branch": branch.strip() if rc2 == 0 else "(detached)",
                "head": head.strip() if rc == 0 else "",
                "dirty": len(changed),
            }
        )
    return rows, None


def stashes(repo):
    rc, out = git(["stash", "list", "--format=%gd %H"], repo=repo)
    if rc != 0:
        return [], None
    rows = []
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2:
            rows.append({"name": parts[0].strip(), "sha": parts[1].strip()})
    return rows, None


def capture_tree(path):
    """Commit a worktree's working tree through a temporary index. Returns (commit, error).

    The worktree's own index is never written, its files are never modified and HEAD does not
    move: the agent that owns the worktree finds exactly what it left. The commit's parent is the
    worktree's HEAD, so the salvage branch carries the history as well as the changes.
    """
    rc, head = git(["rev-parse", "HEAD"], cwd=path)
    if rc != 0:
        return None, "no HEAD in {}".format(path)
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        for args in (["read-tree", head.strip()], ["add", "-A", "."]):
            rc, out = git(args, cwd=path, env=env)
            if rc != 0:
                return None, "git {}: {}".format(" ".join(args), out.strip()[:160])
        rc, tree = git(["write-tree"], cwd=path, env=env)
        if rc != 0:
            return None, "write-tree: {}".format(tree.strip()[:160])
        msg = "salvage: the working tree of {}, captured by estate-rescue\n".format(
            path
        )
        rc, commit = git(
            ["commit-tree", tree.strip(), "-p", head.strip(), "-m", msg], cwd=path
        )
        if rc != 0:
            return None, "commit-tree: {}".format(commit.strip()[:160])
        return commit.strip(), None


def push_ref(sha, target, repo):
    """Push one commit to one salvage branch. Returns (ok, detail)."""
    rc, out = git(
        ["push", "origin", "{}:refs/heads/{}".format(sha, target)],
        repo=repo,
        timeout=PUSH_TIMEOUT,
    )
    if rc != 0:
        return False, "push failed: {}".format(out.strip()[:200])
    rc, ls = git(["ls-remote", "--heads", "origin", target], repo=repo)
    if rc != 0 or ls.strip() == "":
        return False, "the push reported success but origin does not show the ref"
    return True, "origin now holds {}".format(target)


def load_census(path=None):
    """The census ledger: which claim holds what, and whether that claim is still alive.

    It is read for one reason. A headless agent's session can die while its claim is still on the
    board, and the work it held is then the most at-risk thing in the estate: nobody is coming
    back for it. A claim whose heartbeat has lapsed names a session that is gone.
    """
    path = Path(path or CENSUS)
    try:
        with open(path) as fh:
            data = json.load(fh)
    except Exception:
        return {}

    out = {}

    def walk(node):
        if isinstance(node, dict):
            name = (
                node.get("name")
                or node.get("item")
                or node.get("ref")
                or node.get("branch")
            )
            claim = node.get("claim") or node.get("issue")
            if isinstance(name, str) and claim:
                live = node.get("live")
                if live is None:
                    state = str(
                        node.get("state")
                        or node.get("status")
                        or node.get("verdict")
                        or ""
                    ).upper()
                    if state == "LIVE":
                        live = True
                    elif state in ("RECOVERABLE", "DEAD", "LANDED"):
                        live = False
                out.setdefault(name, {"claim": str(claim), "live": live})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return out


def prioritize(rows, census):
    """The work a dead headless session held goes first: a lapsed claim, then unclaimed, then the
    work of a session that is still alive (it will land its own work)."""

    def key(row):
        info = census.get(row["name"]) or {}
        live = info.get("live")
        order = 0 if live is False else (2 if live is True else 1)
        return (order, row["kind"], row["name"])

    return sorted(rows, key=key)


def plan(remote_refs, repo):
    """Everything that exists only here. Nothing is pushed by this function."""
    rows = []
    branches, err = local_branches(repo)
    if branches is None:
        return None, "cannot read local branches: {}".format(err)
    landed = main_commits(repo)
    for row in branches:
        name = row["name"]
        if name.startswith(PREFIX):
            continue  # a salvage branch is already the safe copy
        if name in remote_refs:
            continue  # origin already holds it
        if landed is not None and row["sha"] in landed:
            continue  # it is on main; nothing is at risk
        if landed is None and on_main(row["sha"], repo):
            continue  # it is on main; nothing is at risk
        rows.append(
            {
                "kind": "branch",
                "name": name,
                "sha": row["sha"],
                "target": slug(name),
                "verdict": "PLANNED",
                "why": "{} is on no remote and not on main".format(name),
            }
        )
    trees, err = dirty_worktrees(repo)
    if trees is None:
        return None, "cannot read the worktrees: {}".format(err)
    for row in trees:
        rows.append(
            {
                "kind": "worktree",
                "name": row["path"],
                "sha": "",
                "target": slug("wt-" + row["name"]),
                "verdict": "PLANNED",
                "why": "{} uncommitted change(s) in {} ({})".format(
                    row["dirty"], row["path"], row["branch"]
                ),
            }
        )
    stash_rows, err = stashes(repo)
    if err:
        return None, "cannot read the stashes: {}".format(err)
    for row in stash_rows:
        rows.append(
            {
                "kind": "stash",
                "name": row["name"],
                "sha": row["sha"],
                "target": slug("stash-" + SAFE.sub("", row["name"])),
                "verdict": "PLANNED",
                "why": "{} exists only in this repository's reflog".format(row["name"]),
            }
        )
    return rows, None


def rescue(rows, budget, repo):
    """Push the planned items, in order, up to the budget. Returns the same rows, judged."""
    out = []
    pushed = 0
    started = time.time()
    for row in rows:
        if pushed >= budget:
            out.append(
                dict(
                    row,
                    verdict="DEFERRED",
                    why="the rescue budget for this run is spent",
                )
            )
            continue
        if row["kind"] == "worktree":
            commit, err = capture_tree(row["name"])
            if not commit:
                out.append(
                    dict(row, verdict="FAILED", why="capture failed: {}".format(err))
                )
                continue
            sha = commit
        else:
            sha = row["sha"]
        ok, detail = push_ref(sha, row["target"], repo)
        if ok:
            pushed += 1
            out.append(dict(row, verdict="RESCUED", why=detail))
        else:
            out.append(dict(row, verdict="FAILED", why=detail))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="rescue in-flight work to origin")
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--max", type=int, default=RESCUE_MAX)
    ap.add_argument(
        "--dry-run", action="store_true", help="say what would be rescued; push nothing"
    )
    args = ap.parse_args(argv)

    repo = Path(args.repo)
    if not (repo / ".git").exists():
        print("BLIND    estate-rescue  {} is not a git repository".format(repo))
        return 2

    remote_refs, err = origin_heads(repo)
    if remote_refs is None:
        print("BLIND    estate-rescue  cannot read origin: {}".format(err))
        return 2

    rows, err = plan(remote_refs, repo)
    if rows is None:
        print("BLIND    estate-rescue  {}".format(err))
        return 2

    census = load_census()
    rows = prioritize(rows, census)
    for row in rows:
        row["claim"] = (census.get(row["name"]) or {}).get("claim", "")

    if args.dry_run:
        judged = [dict(r, verdict="WOULD-RESCUE") for r in rows]
    else:
        judged = rescue(rows, args.max, repo)

    rescued = [r for r in judged if r["verdict"] == "RESCUED"]
    failed = [r for r in judged if r["verdict"] == "FAILED"]
    deferred = [r for r in judged if r["verdict"] == "DEFERRED"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "at": stamp,
        "repo": str(repo),
        "census": str(CENSUS),
        "dry_run": bool(args.dry_run),
        "planned": len(rows),
        "rescued": len(rescued),
        "failed": len(failed),
        "deferred": len(deferred),
        "items": judged,
    }
    try:
        RESULTS.mkdir(parents=True, exist_ok=True)
        body = json.dumps(payload, indent=2, sort_keys=True)
        (RESULTS / "latest.json").write_text(body)
        (RESULTS / "{}.json".format(stamp)).write_text(body)
    except OSError as exc:
        payload["blind"] = str(exc)

    for row in judged:
        print(
            "{:<12} {:<9} {}  {}  {}  {}".format(
                row["verdict"],
                row["kind"],
                row["name"],
                row["why"],
                row.get("target", ""),
                ("[{}]".format(row["claim"]) if row.get("claim") else ""),
            )
        )
    print(
        "planned={} rescued={} failed={} deferred={} ledger={}".format(
            len(rows), len(rescued), len(failed), len(deferred), RESULTS / "latest.json"
        )
    )
    return 1 if rescued else 0


if __name__ == "__main__":
    sys.exit(main())
