#!/usr/bin/env python3
"""Reap git worktrees whose work has LANDED on main: landed AND clean AND unlocked AND idle.

WHY. 2026-11-28, measured on the founder's Mac: 14 worktrees against a cap of 4
(ESTATE_MAX_LOCAL_WORKTREES), about 3.9 GB, with 833 MB of the data volume free. bin/estate-zero-worktree
refuses to SPAWN more and bin/estate-fence-purge renames a whole root away, but nothing removed the
one kind of worktree that is safe to remove one at a time: a checkout whose branch is already on main.
That checkout is disposable by definition (the commits live in the shared repository), so it is
waste, not work.

A worktree is reaped only when EVERY one of these holds; any doubt keeps it and says why:

  * it is not the main checkout, not locked, and not prunable (prune owns the missing ones);
  * its HEAD is LANDED on the base ref (default origin/main): HEAD is an ancestor of it, or every
    commit it has beyond it is patch-equivalent (git cherry), or main carries a `Greenlane-Head:`
    trailer naming HEAD (Greenlane rewrites a lane's commits, so its sha is not on main);
  * it is CLEAN: `git status --porcelain` is empty, untracked files included, so no byte of
    anyone's uncommitted work goes with it;
  * no live claim covers it (the same register claimed-worktrees.py reads);
  * it is IDLE: nothing touched its git metadata for --min-idle-min (default 120, the claim
    liveness window) and no process has its working directory inside it. A worktree created a
    minute ago from main is "landed" by ancestry and is NOT waste, so freshness is a keep reason.

It never forces: it runs plain `git worktree remove`, which itself refuses a dirty tree. When it
cannot measure (no lsof, no base ref) it removes NOTHING and says BLIND, never "nothing to do".

    landed-worktrees.py /path/to/repo            # report only (the default)
    landed-worktrees.py --remove /path/to/repo   # reap what the rules allow
Exit 0 normally; 2 BLIND (could not measure, nothing removed).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
GREENLANE_TRAILER = re.compile(r"^Greenlane-Head:\s*([0-9a-f]{7,40})\s*$", re.MULTILINE)


def _claimed():
    """The sibling claimed-worktrees.py, loaded by path (one claim reader, not two)."""
    spec = importlib.util.spec_from_file_location(
        "claimed_worktrees", os.path.join(_HERE, "claimed-worktrees.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(args: list, cwd: str) -> tuple:
    try:
        done = subprocess.run(
            ["git", "-C", cwd, *args], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return done.returncode, done.stdout


def entries(repo: str) -> list:
    """Parse `git worktree list --porcelain` into dicts (path, head, flags)."""
    code, out = git(["worktree", "list", "--porcelain"], repo)
    rows, row = [], {}
    for line in (out if code == 0 else "").splitlines() + [""]:
        if not line:
            if row:
                rows.append(row)
            row = {}
            continue
        key, _, value = line.partition(" ")
        row[key] = value or True
    return rows


def cwd_roots() -> list | None:
    """Working directories of every process (None = could not measure)."""
    try:
        done = subprocess.run(
            ["lsof", "-d", "cwd", "-Fn"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode not in (0, 1):
        return None
    return [ln[1:] for ln in done.stdout.splitlines() if ln.startswith("n/")]


def landed(repo: str, head: str, base: str) -> str:
    """Why HEAD counts as landed, or '' when it does not."""
    if git(["merge-base", "--is-ancestor", head, base], repo)[0] == 0:
        return f"HEAD is an ancestor of {base}"
    code, out = git(["cherry", base, head], repo)
    if (
        code == 0
        and out.strip()
        and not any(ln.startswith("+") for ln in out.splitlines())
    ):
        return f"every commit is patch-equivalent on {base}"
    code, out = git(
        ["log", base, "--format=%B", f"--grep=Greenlane-Head: {head[:7]}"], repo
    )
    if code == 0 and any(
        head.startswith(s) or s.startswith(head[:7])
        for s in GREENLANE_TRAILER.findall(out)
    ):
        return f"{base} carries Greenlane-Head: {head[:7]}"
    return ""


def idle_minutes(path: str) -> float:
    """Minutes since anything touched the worktree's own git metadata."""
    code, gitdir = git(["rev-parse", "--absolute-git-dir"], path)
    if code != 0:
        return 0.0
    newest = 0.0
    for name in ("HEAD", "index", "ORIG_HEAD", "FETCH_HEAD"):
        try:
            newest = max(newest, os.stat(os.path.join(gitdir.strip(), name)).st_mtime)
        except OSError:
            continue
    return (time.time() - newest) / 60 if newest else 0.0


def judge(repo: str, base: str, min_idle: float, live: dict, cwds: list) -> list:
    """One (path, verdict, reason) per non-main worktree. verdict: reap | keep."""
    out = []
    claimed = _claimed()
    for index, row in enumerate(entries(repo)):
        path = row.get("worktree", "")
        if index == 0 or not path:
            continue  # the first entry is the main checkout
        head = str(row.get("HEAD", ""))
        if row.get("locked"):
            out.append((path, "keep", "locked"))
        elif row.get("prunable"):
            out.append((path, "keep", "prunable: `git worktree prune` owns it"))
        elif not os.path.isdir(path) or not head:
            out.append((path, "keep", "cannot read it"))
        elif any(c == path or c.startswith(path + os.sep) for c in cwds):
            out.append((path, "keep", "a process is working inside it"))
        elif not (why := landed(repo, head, base)):
            out.append((path, "keep", f"NOT landed on {base}: its work is not on main"))
        elif git(["status", "--porcelain"], path) != (0, ""):
            out.append((path, "keep", "not clean: uncommitted or untracked files"))
        elif any(
            n in live
            for n in claimed.claims_in(
                git(["log", "-n", "20", "--format=%B", "HEAD"], path)[1]
            )
        ):
            out.append((path, "keep", "a live claim covers it"))
        elif (age := idle_minutes(path)) < min_idle:
            out.append(
                (path, "keep", f"touched {age:.0f}m ago (< {min_idle:.0f}m idle)")
            )
        else:
            out.append((path, "reap", why))
    return out


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(prog="landed-worktrees")
    parser.add_argument("repo")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--min-idle-min", type=float, default=120)
    args = parser.parse_args(argv)
    if git(["rev-parse", "--verify", "--quiet", args.base], args.repo)[0] != 0:
        print(
            f"BLIND  landed-worktrees  {args.base} is not readable in {args.repo}: nothing removed"
        )
        return 2
    cwds = cwd_roots()
    if cwds is None:
        print(
            "BLIND  landed-worktrees  lsof could not list working directories: nothing removed"
        )
        return 2
    live = _claimed().live_claims(
        os.environ.get("CLAIM_REGISTER", _claimed().DEFAULT_REGISTER)
    )
    verdicts = judge(args.repo, args.base, args.min_idle_min, live, cwds)
    done = 0
    for path, verdict, why in verdicts:
        if verdict == "keep":
            print(f"keep     {path}  ({why})")
        elif not args.remove:
            done += 1
            print(f"would    remove {path}  ({why})")
        elif git(["worktree", "remove", path], args.repo)[0] == 0:
            done += 1
            print(f"removed  {path}  ({why})")
        else:
            print(f"keep     {path}  (git refused to remove it)")
    verb = "removed" if args.remove else "would remove"
    print(f"ok       landed-worktrees  {verb} {done} of {len(verdicts)} worktree(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
