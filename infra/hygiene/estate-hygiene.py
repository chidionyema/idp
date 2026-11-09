#!/usr/bin/env python3
"""infra/hygiene/estate-hygiene.py -- the estate's cleaning, as one script that cannot lose work.

    estate-hygiene.py snapshot  --repo PATH [--remote NAME]
    estate-hygiene.py archive   --repo PATH --keep BRANCH[,BRANCH] [--apply]
    estate-hygiene.py report     --repo PATH

Every destructive step is preceded by a ref that makes it reversible, and nothing is deleted
unless the ref that preserves it was created first -- if the archive ref fails, the branch stays.
That is the whole contract, and the tests in test_estate_hygiene.py prove both directions.

  snapshot  every dirty worktree of the repo -> `git stash create` (a commit object; the index and
            working tree are not touched) -> pushed to refs/wip/guard/<repo>-<YYYYMMDDHH>
  archive   every branch except main and --keep -> refs/archive/<name>, then delete the branch;
            writes an inventory of what was archived, with the one-line restore for each
  report    what would be archived or snapshotted; changes nothing

--apply is required for any deletion; without it the script prints its plan.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def git(repo: Path, *args: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(  # noqa: S603 - fixed argv, never a shell string
        ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()[:200]}")
    return p


def worktrees(repo: Path) -> list[Path]:
    out = git(repo, "worktree", "list", "--porcelain").stdout
    paths = [Path(line.split(" ", 1)[1]) for line in out.splitlines() if line.startswith("worktree ")]
    return [p for p in paths if p.exists()]


def snapshot(repo: Path, remote: str, apply: bool) -> list[dict]:
    rows = []
    for wt in worktrees(repo):
        dirty = git(wt, "status", "--porcelain", check=False).stdout.strip()
        if not dirty:
            continue
        rec = {"worktree": str(wt), "dirty": len(dirty.splitlines())}
        if not apply:
            rec["action"] = "would snapshot"
            rows.append(rec)
            continue
        created = git(wt, "stash", "create", "hygiene snapshot", check=False)
        sha = (created.stdout or "").strip().splitlines()[-1:] or [""]
        sha = sha[0]
        if not sha:
            rec["action"] = "nothing to snapshot"
            rows.append(rec)
            continue
        ref = f"refs/wip/guard/{repo.name}-{time.strftime('%Y%m%d%H', time.gmtime())}"
        pushed = git(wt, "push", "--no-verify", "-q", remote, f"{sha}:{ref}", check=False)
        rec["action"] = f"snapshot -> {ref}" if pushed.returncode == 0 else "PUSH FAILED (tree untouched)"
        rec["snapshot"] = sha
        rows.append(rec)
    return rows


def branches(repo: Path, remote: str) -> dict[str, str]:
    out = git(repo, "ls-remote", "--heads", remote, check=False).stdout
    found = {}
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            found[ref[len("refs/heads/"):]] = sha
    return found


def archive(repo: Path, remote: str, keep: set[str], apply: bool) -> list[dict]:
    rows = []
    for name, sha in sorted(branches(repo, remote).items()):
        if name in keep or name in {"main", "master"}:
            continue
        rec = {"branch": name, "sha": sha}
        if not apply:
            rec["action"] = "would archive+delete"
            rows.append(rec)
            continue
        ref = f"refs/archive/{name}"
        # Preserve first. If this fails, the branch is left alone: a deletion with no ref behind
        # it is the one thing this script must never do.
        pre = git(repo, "push", "--no-verify", "-q", remote, f"{sha}:{ref}", check=False)
        if pre.returncode != 0:
            rec["action"] = "ARCHIVE FAILED -> branch kept"
            rows.append(rec)
            continue
        dele = git(repo, "push", "--no-verify", "-q", remote, "--delete", name, check=False)
        rec["action"] = "archived+deleted" if dele.returncode == 0 else f"{ref} kept, delete refused"
        rec["restore"] = f"git push {remote} {sha}:refs/heads/{name}"
        rows.append(rec)
    return rows


def write_inventory(repo: Path, remote: str, rows: list[dict]) -> Path:
    inv = repo / ".genesis" / "archive-inventory.json"
    entries = []
    for r in rows:
        if "sha" not in r:
            continue
        entries.append({"branch": r["branch"], "sha": r["sha"], "archived": r.get("action", ""),
                        "restore": r.get("restore", "")})
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "remote": remote, "count": len(entries), "entries": entries},
                              indent=1) + "\n")
    return inv


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["snapshot", "archive", "report"])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--keep", default="")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    keep = {k.strip() for k in a.keep.split(",") if k.strip()}
    if a.command in {"snapshot", "report"}:
        rows = snapshot(repo, a.remote, a.apply and a.command == "snapshot")
        for r in rows:
            print(f"  {r.get('action', ''):32} {r['worktree']} (dirty {r['dirty']})")
        if not rows:
            print("  no dirty worktree")
        if a.command == "report":
            plan = archive(repo, a.remote, keep, apply=False)
            for r in plan:
                print(f"  would archive+delete          {r['branch']}")
            print(f"  {len(plan)} branch(es) outside the keep set")
        return 0
    rows = archive(repo, a.remote, keep, a.apply)
    if a.apply:
        inv = write_inventory(repo, a.remote, rows)
        print(f"  inventory written: {inv}")
    for r in rows:
        print(f"  {r['action']:32} {r['branch']}")
    print(f"  {len(rows)} branch(es) outside the keep set")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
