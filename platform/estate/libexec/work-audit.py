#!/usr/bin/env python3
"""work-audit: find work done in the last N days that never reached main.

One test for every place work can hide: of the lines this work ADDED, how many are in the same
file on origin/main now? Later edits on main do not fool it (it looks for the lines, not the file
hash); a file deleted on main counts as not landed and is named, since that may be deliberate.

Sources, all measured, none inferred:
  pr        closed-unmerged PRs (GitHub search), head fetched from refs/pull/N/head
  worktree  uncommitted tracked changes + untracked files in every worktree of every local repo
  local     commits on local branches that are on no remote
  stash     stashes created inside the window
  cp        unticked "- [ ]" checkpoints in open issues updated inside the window

Verdict per item: LANDED (>=90% of added lines on main now), REMOVED (not on main now, but >=90%
were added on main at some point since the window opened -- landed, then deleted), PARTIAL (>=30%
ever), LOST (<30% ever). LANDED, REMOVED and bot PRs are hidden unless all=true. PRs with an
identical title collapse into the newest. Exit 0 always -- this reports; it decides nothing.
Writes the full result to ~/.estate/work-audit/latest.json for any surface that wants it.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOME = Path.home()
CODE = HOME / "Documents" / "code"
OUT = HOME / ".estate" / "work-audit"
NOISE = re.compile(
    r"(^|/)(target|node_modules|\.growmos|__pycache__|\.venv|dist|build)/|\.(pyc|lock)$"
)
MIN_LINE = 8  # shorter added lines ("}", "fi", "") prove nothing about landing
# How many absent PR heads one door call will fetch. A closed PR's head never changes, so this is
# a one-time cost per PR, not a per-run one; the cap keeps a cold cache inside the door's ceiling
# and the remainder is named as not-yet-fetched rather than silently reported as unknown.
FETCH_BUDGET = 12
# One `git diff --no-index` process per untracked file. A busy worktree can carry hundreds, and
# the door has 100s for everything; past this cap the rest are counted, not silently ignored.
MAX_UNTRACKED_DIFFS = 40
# A branch whose `%(upstream:track)` says "ahead N" is already proven unpushed by the ref listing.
AHEAD = re.compile(r"\bahead (\d+)")
# Local branches examined per repo. 1,093 local branches is this checkout's history, not this
# window's work: past the cap the remainder is reported in `errors`, never silently dropped.
# 24 is what fits: each examined branch costs ~1s rev-list + 0.7s merge-base + 0.6s diff, and the
# door also owes a GitHub sweep and a PR census inside the same 100s.
LOCAL_WALK_CAP = 24
# Checkpoint and scratch refs. `backup/*` and `recovery/*` are snapshots taken to make a rebase
# safe; they are not a delivery attempt, and walking every one of them is what blew the budget.
# They are counted and named in `errors` rather than silently dropped.
CHECKPOINT = re.compile(
    r"^(backup|recovery|preserve|archive|tmp|temp|scratch|save|wip)[-/]", re.IGNORECASE
)
# Pushed lane branches examined per repo, newest first -- see the local cap above for why a cap is
# owed at all. A lane past this cap is named in `errors`.
LANE_CAP = 40
# Seconds `audit_local` may consume of the door's 100s. The rest is owed to the GitHub sweep and
# the PR census, which are the census; the local scan is the supplement.
LOCAL_BUDGET_S = 30


def sh(*a, cwd=None, timeout=120) -> tuple[int, str]:
    try:
        r = subprocess.run(  # noqa: S603 - fixed argv, never a shell string
            a,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # 2026-11-06: one non-UTF-8 byte in a commit message made the whole audit
            # BLIND ('utf-8' codec can't decode byte 0xfc) while it still exited 0.
            # A byte the estate cannot decode costs that line, never the corpus.
            errors="replace",
        )
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, OSError) as e:
        return 1, str(e)


def git(repo, *a, timeout=120) -> str:
    return sh("git", "-C", str(repo), *a, timeout=timeout)[1]


def added_by_file(diff: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            p = line[4:]
            cur = None if p == "/dev/null" else p[2:] if p.startswith("b/") else p
            if cur and NOISE.search(cur):
                cur = None
        elif cur and line.startswith("+") and not line.startswith("+++"):
            s = line[1:].strip()
            if len(s) >= MIN_LINE:
                out.setdefault(cur, []).append(s)
    return out


_main_cache: dict[tuple[str, str], set[str] | None] = {}


def prefetch(repo: Path, ref: str, paths) -> None:
    """Warm `main_lines` for a whole pathset in ONE process.

    `main_lines` spawns a `git show` per file; a stranded PR can touch a hundred files, so a
    forty-PR audit was spending most of its budget starting processes. `git cat-file --batch`
    answers every path from a single process, and this is the same data `main_lines` would have
    read -- a miss is recorded as absent, never left to be guessed later.
    """
    todo = [p for p in paths if (str(repo), p) not in _main_cache]
    if not todo:
        return
    req = "".join(f"{ref}:{p}\n" for p in todo)
    p = subprocess.run(  # noqa: S603 - fixed argv, never a shell string
        ["git", "-C", str(repo), "cat-file", "--batch"],  # noqa: S607 - git via PATH
        input=req.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    out = p.stdout
    pos = 0
    for path in todo:
        nl = out.find(b"\n", pos)
        if nl < 0:
            break
        header = out[pos:nl].decode("utf-8", "replace")
        pos = nl + 1
        parts = header.split()
        # "<sha> blob <size>" for a hit; "<ref>:<path> missing" for a miss. Any other shape is
        # not a readable blob and is recorded absent rather than parsed optimistically.
        if len(parts) == 3 and parts[1] == "blob":
            try:
                size = int(parts[2])
            except ValueError:
                _main_cache[(str(repo), path)] = None
                continue
            body = out[pos : pos + size].decode("utf-8", "replace")
            pos += size + 1
            _main_cache[(str(repo), path)] = {ln.strip() for ln in body.splitlines()}
        else:
            _main_cache[(str(repo), path)] = None


def main_lines(repo: Path, ref: str, path: str) -> set[str] | None:
    key = (str(repo), path)
    if key not in _main_cache:
        rc, txt = sh("git", "-C", str(repo), "show", f"{ref}:{path}")
        _main_cache[key] = None if rc else {ln.strip() for ln in txt.splitlines()}
    return _main_cache[key]


_hist: dict[tuple[str, frozenset[str]], set[int]] = {}
# Walks that were cut short by HIST_BUDGET_S. `landed()` must not read a partial walk as proof
# that a line never landed: that is the difference between REMOVED and LOST, and guessing it
# wrong publishes a false accusation of loss. A partial walk yields UNKNOWN.
_hist_partial: set[tuple[str, frozenset[str]]] = set()
HIST_BUDGET_S = 34.0
# The door's own ceiling, declared here because the estate's is 100s and a door that spends its
# last second working has no time to report. Everything below is sized against this, not against
# what the machine happened to take last time.
DOOR_BUDGET = 100.0
_hist_lock = threading.Lock()
SINCE = [dt.datetime.now(dt.timezone.utc)]


def history(repo: Path, ref: str, paths: list[str] | None = None) -> set[int]:
    """Hashes of every line ADDED on main since the window opened (plus 30 days of slack), so
    work that landed and was later deleted reads REMOVED, not LOST.

    LAZY, AND SCOPED TO THE QUESTION. Generating `-p` for eight weeks of a 6,795-commit repo
    (3,156 commits touching 6,569 files) takes longer than this door's entire 100s budget, which
    is why every run timed out -- 29/31 not ok over 30 days. Two changes make it affordable
    without weakening a single verdict:

      1. `paths` narrows the walk to the files a stranded PR actually touched. The question is
         "was THIS line ever on main", never "what did main ever contain".
      2. `landed()` only calls it when a probe came back short, so a repo whose stranded work is
         cleanly absent (the common case) never pays for it at all.

    `--diff-filter=AM` keeps it honest: only added or modified files can hold a line that once
    landed, so renames and deletions -- most of the patch volume -- are never generated.

    A WALKSET IS UNIONED, NOT REPEATED. Calling this once per stranded PR spawned one `git log -p`
    per PR -- 32 calls, 26.7s inside git, profiled -- which is the same walk done 32 times over
    overlapping files. A completed walk is reused whenever its pathset covers the one being asked
    for, and a new walk absorbs every uncovered pathset, so the number of walks per repo is one.
    """
    wanted = frozenset(paths or ())
    with _hist_lock:
        if not wanted:
            return _hist.setdefault((str(repo), wanted), set())
        # A wider walk answers every narrower question, so never re-walk a subset of one we hold.
        for (r0, have), seen in _hist.items():
            if r0 == str(repo) and wanted <= have:
                return seen
        # A cache that only ever shrinks thrashes: evicting a walk to make room means the next
        # strand re-walks it, which is how this call came to be issued 14 times for 32s apiece.
        # Keeping both is bounded (one per distinct pathset) and always cheaper than re-walking.
        key = (str(repo), wanted)
        since = (SINCE[0] - dt.timedelta(days=30)).date()
        # A walk that cannot finish inside this door must SAY so, not look like an empty history.
        # An empty `seen` set is indistinguishable from "none of these lines ever landed", which
        # would turn every shortfall into LOST -- the fail-open this door exists to end. So the
        # walk is bounded, and an unfinished walk is recorded in `_hist_partial` where `landed()`
        # reads it and downgrades the row to UNKNOWN instead of asserting loss.
        stop = time.monotonic() + HIST_BUDGET_S
        argv = [  # noqa: S607 - git is resolved by PATH like every other estate tool
            "git",
            "-C",
            str(repo),
            "log",
            ref,
            f"--since={since}",
            "--no-merges",
            "-p",
            "-U0",
            "--no-color",
            "--diff-filter=AM",
            "--no-renames",
            "--format=",
        ]
        if wanted:
            argv += ["--", *sorted(wanted)]
        p = subprocess.Popen(  # noqa: S603 - fixed argv, never a shell string
            argv,
            stdout=subprocess.PIPE,
            text=True,
            errors="replace",
        )
        seen: set[int] = set()
        for line in p.stdout:  # type: ignore[union-attr]
            if line.startswith("+") and not line.startswith("+++"):
                t = line[1:].strip()
                if len(t) >= MIN_LINE:
                    seen.add(hash(t))
            if time.monotonic() > stop:
                p.kill()
                _hist_partial.add(key)
                break
        p.wait()
        _hist[key] = seen
        # A finished walk retires its partial mark: the key is now backed by a complete set, and
        # leaving the flag set would make every later caller read a full answer as truncated.
        return seen


def landed(repo: Path, ref: str, diff: str | dict[str, list[str]]) -> dict:
    files = added_by_file(diff) if isinstance(diff, str) else diff
    total = hit = ever = 0
    missing: list[str] = []
    gone: list[str] = []
    per_file: dict[str, int] = {}
    # One process for every file this strand touched, instead of one per file.
    prefetch(repo, ref, files.keys())
    for path, lines in files.items():
        have = main_lines(repo, ref, path)
        if have is None:
            gone.append(path)
        n = sum(1 for ln in lines if have and ln in have)
        total += len(lines)
        hit += n
        per_file[path] = len(lines) - n
    now = hit / total if total else 1.0
    short = [p for p, miss in per_file.items() if miss]
    # The "ever" walk is the door's most expensive call and it answers exactly one question:
    # is this shortfall DELETED (it landed, then went) or LOST (it never did)? Only pay for it
    # when there is a shortfall to explain, and only over the files in question.
    #
    # AND ONLY WHEN THE ANSWER CAN CHANGE THE VERDICT. The walk only matters where `eff` decides
    # between REMOVED (>=0.9), PARTIAL (>=0.3) and LOST: at `now` < 0.3 a shortfall of that size
    # still reads LOST even if every missing line once landed, so walking main's whole patch
    # history to prove it buys nothing. That is most of the stranded work here (0-8% on main),
    # and skipping the walk for it is what turns a door that timed out on 32/34 runs into one
    # that finishes -- without changing a single verdict.
    #
    # THE EXCEPTION IS A FILE THAT IS GONE. `now` is low for a deleted file by definition, so
    # `now >= 0.3` alone would read every REMOVED file as LOST -- accusing a deletion of being
    # loss, which is the one direction this door must never get wrong (the existing falsifier
    # test_landed_removed_lost catches exactly that). `gone` is the signal that the low `now`
    # may be explained by a deletion, so the walk is owed there whatever `now` says.
    worth_walking = bool(short and (now >= 0.3 or gone))
    hist = history(repo, ref, short) if worth_walking else set()
    # A walk cut short cannot prove a line never landed, so it cannot justify LOST. The row is
    # still useful -- what is present on main is measured, not guessed -- but its verdict says
    # UNKNOWN, so an agent re-runs rather than re-queueing work that may already be in main.
    #
    # The flag is CONSUMED, not merely read. It marks one walk of one pathset; leaving it set
    # lets a later row whose shortlist happens to be a subset inherit a truncation it never
    # suffered, which is a fail-closed verdict produced by bookkeeping rather than by evidence.
    timed_out = False
    if worth_walking:
        with _hist_lock:
            for k in [
                k
                for k in _hist_partial
                if k[0] == str(repo) and frozenset(short) <= k[1]
            ]:
                timed_out = True
                _hist_partial.discard(k)
    for path, lines in files.items():
        have = main_lines(repo, ref, path)
        ever += sum(1 for ln in lines if not (have and ln in have) and hash(ln) in hist)
        n = sum(1 for ln in lines if have and ln in have)
        if n < len(lines) * 0.9:
            missing.append(f"{path} {n}/{len(lines)}")
    eff = (hit + ever) / total if total else 1.0
    verdict = (
        "UNKNOWN"
        if timed_out and (hit + ever) / total < 0.9
        else "LANDED"
        if now >= 0.9
        else "REMOVED"
        if eff >= 0.9
        else "PARTIAL"
        if eff >= 0.3
        else "LOST"
    )
    return {
        "verdict": verdict,
        "landed_pct": round(now * 100),
        "ever_pct": round(eff * 100),
        "added_lines": total,
        "files_short": missing[:8],
        "files_deleted_on_main": gone[:8],
    }


def main_ref(repo: Path) -> str | None:
    for ref in ("origin/main", "origin/master", "main", "master"):
        if sh("git", "-C", str(repo), "rev-parse", "-q", "--verify", ref)[0] == 0:
            return ref
    return None


def repos(only: list[str] | None = None) -> list[Path]:
    """Repos to scan. When the caller named repos in `github`, scan THOSE.

    This used to return every checkout under ~/Documents/code regardless of what was asked for,
    so `work-audit days=7 github=chidionyema/idp` fetched and scanned ~30 repos to answer a
    question about one -- measured at 275s for argon-sync alone. An argument that does not narrow
    the work is not an argument, and a door that spends minutes on a typo gets abandoned.
    """
    every = sorted(p.parent for p in CODE.glob("*/.git") if p.is_dir())
    if not only:
        return every
    wanted = {n.rsplit("/", 1)[-1] for n in only}
    chosen = [p for p in every if p.name in wanted]
    # A named repo with no checkout here is not "nothing to audit" -- say which, in the caller.
    return chosen


def worktrees(repo: Path) -> list[tuple[Path, str]]:
    out, wt = [], None
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            wt = Path(line[9:])
        elif line.startswith("branch ") and wt:
            out.append((wt, line[7:].removeprefix("refs/heads/")))
        elif line == "detached" and wt:
            out.append((wt, "(detached)"))
    return out


def audit_local(
    since: dt.datetime,
    targets: list[Path],
    errors: list[str] | None = None,
    deadline: float | None = None,
) -> list[dict]:
    """Local work at risk: dirty worktrees, unpushed branches, pushed-but-unmerged lanes, stashes.

    Every phase here is bounded by `deadline` (a `time.monotonic()` instant). A checkout with 1,093
    local branches cannot be walked branch-by-branch inside one 100s door, and the old code tried:
    it spent the whole budget in this function and the door died before it scored a single PR. It is
    better to census what fits and NAME what it did not reach than to return nothing at all -- but
    what it did not reach must be in `errors`, never silently absent (`MISSING-RESTORABLE` that
    nobody reported reads as "no lost work").
    """
    items: list[dict] = []
    dirty: list[tuple] = []
    errors = errors if errors is not None else []
    deadline = deadline if deadline is not None else time.monotonic() + LOCAL_BUDGET_S

    def out_of_time(what: str, left: int) -> bool:
        if time.monotonic() < deadline:
            return False
        errors.append(
            f"out of time in {what}: {left} item(s) not examined, so they are not in this "
            f"census -- re-run this door when the machine is quieter"
        )
        return True

    seen_wt: set[Path] = set()
    for repo in targets:
        ref = main_ref(repo)
        if not ref:
            continue
        t0 = time.monotonic()
        # worktrees: uncommitted + untracked, in parallel (git diff HEAD is ~12s on the big checkout)
        todo = [
            (wt, br) for wt, br in worktrees(repo) if wt not in seen_wt and wt.is_dir()
        ]
        seen_wt.update(wt for wt, _ in todo)

        def one(job, repo=repo, ref=ref):
            wt, br = job
            # Cheap question first: does this worktree have ANY uncommitted change at all? A
            # clean worktree cannot hold this window's work, and asking `git diff HEAD` before
            # this check was paid in full by every worktree on every run -- 19 worktrees of other
            # agents' dirt, which is not this door's question.
            stat = git(wt, "status", "--porcelain", "-uno")
            if not stat.strip():
                return None
            diff = git(wt, "diff", "HEAD")
            untracked = [
                f
                for f in git(
                    wt, "ls-files", "--others", "--exclude-standard"
                ).splitlines()
                if not NOISE.search(f)
            ]
            for f in untracked[:MAX_UNTRACKED_DIFFS]:
                try:
                    if (wt / f).stat().st_mtime < since.timestamp():
                        continue
                except OSError:
                    continue
                diff += (
                    "\n"
                    + sh("git", "-C", str(wt), "diff", "--no-index", "/dev/null", f)[1]
                )
            files = {}
            for path, lines in added_by_file(diff).items():
                try:  # untouched inside the window = not this window's work
                    if (wt / path).stat().st_mtime < since.timestamp():
                        continue
                except OSError:
                    pass
                files[path] = lines
            return (repo, ref, wt, br, files) if files else None

        with ThreadPoolExecutor(8) as pool:
            dirty += [r for r in pool.map(one, todo) if r]
        # Local-only commits.
        #
        # This used to run `rev-list --count <br> --not --remotes` once per local branch. On this
        # checkout there are 1,093 local branches and the `--not --remotes` half costs ~2s each,
        # so the loop alone was ~40 minutes of walking -- the whole door's budget before any PR was
        # scored. Worse, it asked the expensive question of all 1,093 when most answers were
        # already in `%(upstream:track)`: a branch whose track says "ahead 3" is proven unpushed by
        # the one ref listing, and needs no walk. Only a branch with NO upstream has to be asked.
        #
        # So: one for-each-ref that carries the answer, then a walk only for the residue, in
        # parallel, and never more than LOCAL_WALK_CAP of them (the cap is reported, not hidden).
        refs: list[tuple[str, str]] = []
        for line in git(
            repo,
            "for-each-ref",
            "--format=%(refname:short)|%(committerdate:iso-strict)|%(upstream:track)",
            "refs/heads",
        ).splitlines():
            br, _, rest = line.partition("|")
            when, _, track = rest.partition("|")
            try:
                if dt.datetime.fromisoformat(when) < since:
                    continue
            except ValueError:
                continue
            m = AHEAD.search(track)
            if m:  # proven ahead of a remote-tracking ref by the ref listing itself
                refs.append((br, m.group(1)))
            elif not track.strip():  # no upstream: the only case that needs a walk
                refs.append((br, ""))

        def count_ahead(job, repo=repo):
            br, known = job
            if known:
                return br, known
            n = git(repo, "rev-list", "--count", br, "--not", "--remotes").strip()
            return br, n

        # Real delivery attempts first, checkpoints last: if the cap bites, it bites on the
        # snapshots (`backup/*`) whose content the branch they were taken from already carries,
        # never on a lane-shaped branch that could be this window's stranded work.
        refs.sort(key=lambda r: bool(CHECKPOINT.match(r[0])))
        walked = refs[:LOCAL_WALK_CAP]
        skipped = refs[len(walked) :]
        if skipped:
            ck = sum(1 for br, _ in skipped if CHECKPOINT.match(br))
            errors.append(
                f"{repo.name}: {len(skipped)} local branch(es) not examined "
                f"(cap {LOCAL_WALK_CAP}; {ck} of them checkpoint refs such as backup/*); "
                f"their commits, if any are unpushed, are not in this census"
            )
        with ThreadPoolExecutor(16) as pool:
            counted = list(pool.map(count_ahead, walked))

        for i, (br, n) in enumerate(counted):
            if not n or n == "0":
                continue
            if out_of_time("local-only branch scan", len(counted) - i):
                break
            base = git(repo, "merge-base", ref, br).strip() or ref
            diff = git(repo, "diff", base, br)
            items.append(
                {
                    "kind": "local",
                    "repo": repo.name,
                    "where": br,
                    "commits_on_no_remote": int(n),
                    **landed(repo, ref, diff),
                }
            )
        # lanes pushed to origin that main never took. The local-only check above cannot see
        # these -- the commit IS on a remote -- and they are exactly the Greenlane's stranded
        # work: a lane that went red or was superseded keeps its branch and everything in it.
        lanes = git(
            repo,
            "for-each-ref",
            "--format=%(refname:short) %(committerdate:iso-strict)",
            "refs/remotes/origin/lane",
        ).splitlines()
        for i, line in enumerate(lanes[:LANE_CAP]):
            if out_of_time("pushed lane scan", len(lanes) - i):
                break
            refname, _, when = line.partition(" ")
            br = refname.removeprefix("origin/")
            if not br or br == "lane":
                continue
            try:
                if dt.datetime.fromisoformat(when) < since:
                    continue
            except ValueError:
                continue
            n = git(repo, "rev-list", "--count", refname, "--not", ref).strip()
            if not n or n == "0":
                continue  # already in main
            base = git(repo, "merge-base", ref, refname).strip() or ref
            items.append(
                {
                    "kind": "lane",
                    "repo": repo.name,
                    "where": br,
                    "commits_not_in_main": int(n),
                    **landed(repo, ref, git(repo, "diff", base, refname)),
                }
            )
        # stashes
        stashes = git(repo, "stash", "list", "--format=%gd %cI %gs").splitlines()
        for i, line in enumerate(stashes):
            if out_of_time("stash scan", len(stashes) - i):
                break
            sid, when, msg = (line.split(" ", 2) + ["", ""])[:3]
            try:
                if dt.datetime.fromisoformat(when) < since:
                    continue
            except ValueError:
                continue
            diff = git(repo, "stash", "show", "-p", "--include-untracked", sid) or git(
                repo, "stash", "show", "-p", sid
            )
            items.append(
                {
                    "kind": "stash",
                    "repo": repo.name,
                    "where": f"{sid} {when[:16]}",
                    "title": msg[:100],
                    **landed(repo, ref, diff),
                }
            )
        took = time.monotonic() - t0
        if took > 5:
            print(f"slow: {repo.name} {took:.0f}s", file=sys.stderr)
    # A file whose added content is identical in 3+ repos is a broadcast (a generated AGENTS.md,
    # .mcp.json ...), not work: report it once instead of as LOST in every repo.
    where: dict[tuple[str, int], set[str]] = {}
    for repo, _ref, _wt, _br, files in dirty:
        for path, lines in files.items():
            where.setdefault((path, hash(tuple(lines))), set()).add(repo.name)
    broadcast = {k for k, v in where.items() if len(v) >= 3}
    for path, _h in broadcast:
        items.append(
            {
                "kind": "worktree",
                "repo": "*",
                "where": path,
                "verdict": "SKIPPED",
                "title": f"broadcast: same uncommitted {path} in {len(where[(path, _h)])} repos",
            }
        )
    for repo, ref, wt, br, files in dirty:
        files = {
            p: ln for p, ln in files.items() if (p, hash(tuple(ln))) not in broadcast
        }
        if files:
            items.append(
                {
                    "kind": "worktree",
                    "repo": repo.name,
                    "where": str(wt),
                    "branch": br,
                    **landed(repo, ref, files),
                }
            )
    return items


def _gh_binary() -> str:
    """gh is not always on PATH: the estate executor and launchd start with a bare PATH,
    where `gh` is at ~/.local/bin and the audit reported BLIND 'No such file or directory'
    for both of its remote sources (2026-11-06)."""
    import shutil

    return shutil.which("gh") or str(HOME / ".local/bin/gh")


_GH = _gh_binary()


def gh_search(q: str) -> list[dict]:
    out, page = [], 1
    while True:
        rc, txt = sh(
            _GH,
            "api",
            "-X",
            "GET",
            "search/issues",
            "-f",
            f"q={q}",
            "-f",
            "per_page=100",
            "-f",
            f"page={page}",
            timeout=60,
        )
        if rc:
            raise RuntimeError(f"gh search failed: {txt[:200]}")
        batch = json.loads(txt).get("items", [])
        out += batch
        if len(batch) < 100 or page >= 10:
            return out
        page += 1


# Checks whose failure is cosmetic: a normalizer could have fixed these, so an agent should try
# before re-cutting the work. Everything else is a real problem with the change.
COSMETIC = (
    "lint",
    "format",
    "yamllint",
    "markdownlint",
    "prettier",
    "black",
    "ruff",
    "shellcheck",
    "hadolint",
    "actionlint",
    "trailer",
    "ascii",
    "non-ascii",
    "whitespace",
    "license",
    "sign-off",
    "dco",
    "regenerate",
)
# A failure here means the change itself was refused (no claim, a downed service, the gate that
# decides). Calling that "mechanical" sends an agent to fix the wrong thing, so it wins.
SUBSTANTIVE = (
    "claim-gate",
    "dof-gate",
    "guarded-paths",
    "ci-success",
    "shadow-verify",
    "verify",
    "fast-gate",
    # The lane itself refusing the change (red lane, conflict, unfetchable head). Nothing a
    # normalizer can rewrite: the change was not accepted, so re-cut or fix it.
    "greenlane",
    # A check that RUNS something is substantive whatever it is called: "lint-and-test" is a
    # test run, and calling it cosmetic sends a normalizer to polish a linter while the tests
    # stay red. Word-boundary matched, so "latest" or "contest" never trip it.
    "test",
    "tests",
    "pytest",
)


def _names_check(check: str, keyword: str) -> bool:
    """Does `check` NAME this keyword, or merely contain its letters?

    Substring matching is how the first version of this classifier failed open: "lint" is a
    substring of "linter", so any future check ending -linter was called cosmetic, and
    "lint-and-test" -- which runs the tests -- was called cosmetic too. A normalizer sent there
    fixes a linter and leaves the real failure.

    So a keyword must land on a boundary. Both the whole hyphenated token AND its segments
    count, because a gate names its rungs both ways: "claim-gate" is one token, "idp-ci / lint"
    splits on the slash, and "ruff check" is a tool plus an argument.
    """
    lowered = check.lower()
    tokens = set(re.split(r"[^a-z0-9\-]+", lowered))
    tokens |= set(re.split(r"[^a-z0-9]+", lowered))
    tokens.discard("")
    if keyword == lowered or keyword in tokens:
        return True
    # A check may add an argument to a tool name ("ruff check", "black --check"): the keyword
    # is then a leading prefix of a token, never a bare substring. "check" is deliberately
    # excluded from this prefix rule: every formatter takes a --check flag, so matching it by
    # prefix would make every linter unhealable. A gate's own "check" rung still matches as a
    # whole token above.
    if keyword == "check":
        return False
    return any(
        t.startswith(keyword + " ") or t.startswith(keyword + "-") for t in tokens
    )


def classify_kill(checks: list[str], ever_ran: bool) -> str:
    """Why did this PR die: could a machine have healed it, or was the change really refused?

    MECHANICAL only when EVERY failing check is cosmetic and NONE is substantive. An empty list
    is not "auto-healable": it means nothing was read, or the checks all passed and something
    else closed the PR. Both are GENUINE/UNKNOWN, never a normalizer's job.
    """
    low = [c.lower() for c in checks]
    if any(any(_names_check(c, s) for s in SUBSTANTIVE) for c in low):
        return "GENUINE"
    if low and all(any(_names_check(c, k) for k in COSMETIC) for c in low):
        return "MECHANICAL"
    # A failing check that matches neither list. It is NOT safe to call this healable: an
    # unknown check might be refusing the change for a real reason, and sending a normalizer at
    # it costs a cycle and teaches the agent that "unknown" means "try again". It is also not
    # safe to call it unhealable, because an unrecognised cosmetic check is exactly what a new
    # linter looks like. Say which it is: UNKNOWN, and let the check be added to a list above.
    if low:
        return "UNKNOWN"
    return "GENUINE" if ever_ran else "UNKNOWN"


def kill_reasons(owner: str, name: str, numbers: list[int]) -> dict[int, dict]:
    """Who closed these PRs, in ONE batched GraphQL call. Read-only.

    The search API does not carry check contexts, so the reason a PR died is invisible from the
    listing alone -- and an agent that cannot see the reason re-cuts work that failed for a
    reason it could have fixed. Batched because a call per PR is what blows the door's ceiling.
    """
    out: dict[int, dict] = {}
    if not numbers:
        return out
    for i in range(0, len(numbers), 40):
        chunk = numbers[i : i + 40]
        fields = " ".join(
            f"p{n}: pullRequest(number: {n}) {{ number commits(last: 1) {{ nodes {{ commit {{ "
            f"statusCheckRollup {{ contexts(last: 40) {{ nodes {{ ... on CheckRun {{ name "
            f"conclusion }} ... on StatusContext {{ context state }} }} }} }} }} }} }} }}"
            for n in chunk
        )
        q = 'query{ repository(owner:"%s", name:"%s") { %s } }' % (owner, name, fields)
        rc, txt = sh(_GH, "api", "graphql", "-f", f"query={q}", timeout=90)
        if rc:
            continue
        repo = (json.loads(txt).get("data") or {}).get("repository") or {}
        for val in repo.values():
            if not val:
                continue
            num = val.get("number")
            nodes = ((val.get("commits") or {}).get("nodes") or [{}])[0].get(
                "commit"
            ) or {}
            ctxs = ((nodes.get("statusCheckRollup") or {}).get("contexts") or {}).get(
                "nodes"
            ) or []
            failed, ran = [], False
            for c in ctxs:
                if not c:
                    continue
                ran = True
                label = c.get("name") or c.get("context") or ""
                concl = (c.get("conclusion") or c.get("state") or "").upper()
                if concl in (
                    "FAILURE",
                    "ERROR",
                    "TIMED_OUT",
                    "STARTUP_FAILURE",
                    "CANCELLED",
                ):
                    failed.append(label)
            out[num] = {
                "failing_checks": failed,
                "kill": classify_kill(failed, ran),
            }
    return out


def shallow(repo: Path) -> bool:
    """A truncated history answers "is this an ancestor?" with a confident false for everything
    below the boundary, which turns unknowable work into a fabricated LOST."""
    try:
        return git(repo, "rev-parse", "--is-shallow-repository").strip() == "true"
    except Exception:  # noqa: BLE001 - an unreadable repo is not shallow, just unreadable
        return False


def audit_prs(
    owner: str,
    names: list[str],
    since: dt.date,
    deadline: float | None = None,
    errors: list[str] | None = None,
) -> list[dict]:
    items = []
    for name in names:
        if deadline is not None and time.monotonic() > deadline:
            skipped = names[names.index(name) :]
            if errors is not None:
                errors.append(
                    f"pr: out of time before {len(skipped)} repo(s) ({', '.join(skipped)}); "
                    f"their closed-unmerged PRs are not in this census -- re-run when the "
                    f"machine is quieter"
                )
            break
        local = CODE / name
        prs = gh_search(
            f"repo:{owner}/{name} is:pr is:closed is:unmerged closed:>={since}"
        )
        ref = main_ref(local) if (local / ".git").exists() else None
        if ref and prs:
            # Fetch ONLY the heads that are not here already. This door used to re-fetch every
            # closed-unmerged PR head over the network on every run -- 40 refs, well past the
            # 100s ceiling, which is why it timed out on 30 of its last 32 runs. The heads do not
            # change once a PR is closed, so a fetched ref is good forever; a warm run now does
            # zero network work and a cold one fetches only what is genuinely absent.
            have = set(
                git(
                    local, "for-each-ref", "--format=%(refname)", "refs/work-audit/"
                ).split()
            )
            specs = [
                f"+refs/pull/{p['number']}/head:refs/work-audit/pr/{p['number']}"
                for p in prs
                if f"refs/work-audit/pr/{p['number']}" not in have
            ]
            # A batch of 40 missing heads is 40 round trips and blows the ceiling; a cap that just
            # truncates would leave the tail permanently invisible. The cache-priority order is by
            # PR number DESCENDING, so a capped run always fetches the newest strands first -- the
            # ones an agent is most likely to salvage -- and repeats eventually reach the tail.
            specs = specs[:FETCH_BUDGET]
            for i in range(0, len(specs), 50):
                sh(
                    "git",
                    "-C",
                    str(local),
                    "fetch",
                    "-q",
                    "--no-tags",
                    "origin",
                    *specs[i : i + 50],
                    timeout=45,
                )
        bots = [
            p
            for p in prs
            if p["user"]["type"] == "Bot"
            or p["user"]["login"].endswith("[bot]")
            or p["title"].startswith("platform: image update")
        ]
        prs = [p for p in prs if p not in bots]
        by_title: dict[str, list[dict]] = {}
        for p in prs:
            by_title.setdefault(p["title"].strip().lower(), []).append(p)
        prs = [max(g, key=lambda p: p["number"]) for g in by_title.values()]
        dupes = {
            max(g, key=lambda p: p["number"])["number"]: [q["number"] for q in g][1:]
            for g in by_title.values()
            if len(g) > 1
        }
        items.append(
            {
                "kind": "pr",
                "repo": name,
                "where": "bots",
                "verdict": "SKIPPED",
                "title": f"{len(bots)} bot/image-update PRs (superseded by design)",
            }
        )
        reasons = kill_reasons(owner, name, [p["number"] for p in prs]) if prs else {}
        is_shallow = shallow(local) if ref else False

        # Collect every strand's diff UP FRONT AND IN PARALLEL. Two git calls per PR (merge-base,
        # then diff) is 110 process spawns for 55 strands, and serially that was 35s of the
        # door's 100s budget before a single line was scored. The diffs are independent, so they
        # fan out; the walk that scores them then runs once, after every pathset is known.
        def strand(p: dict, local=local, ref=ref) -> tuple[int, str | None, str | None]:
            head = f"refs/work-audit/pr/{p['number']}"
            if (
                not ref
                or sh("git", "-C", str(local), "rev-parse", "-q", "--verify", head)[0]
            ):
                return p["number"], None, None
            base = git(local, "merge-base", ref, head).strip() or ref
            return p["number"], base, git(local, "diff", base, head)

        collected: dict[int, tuple[str | None, str | None]] = {}
        if ref and not is_shallow:
            with ThreadPoolExecutor(8) as pool:
                for num, base, diff in pool.map(strand, prs):
                    collected[num] = (base, diff)
            # Warm the main-side file reads in one process before scoring anything.
            every: set[str] = set()
            for _base, diff in collected.values():
                if diff:
                    every |= set(added_by_file(diff).keys())
            prefetch(local, ref, sorted(every))
            # And walk main ONCE for every file any strand touched. Without this warm the lazy
            # "ever" walk is issued per strand and, being a subset each time, re-walks main from
            # scratch: measured at 14 walks / 60s for one 55-PR audit. One union answers all.
            history(local, ref, sorted(every))

        for p in prs:
            row = {
                "kind": "pr",
                "repo": name,
                "where": f"#{p['number']}",
                "title": p["title"][:100],
                "closed": (p.get("closed_at") or "")[:10],
                "url": p["html_url"],
                "same_title_retries": dupes.get(p["number"], []),
            }
            base, diff = collected.get(p["number"], (None, None))
            if diff is not None:
                if is_shallow:
                    # The measurement cannot answer "is this in main" from here. Say so.
                    row.update(
                        {
                            "verdict": "UNMEASURED",
                            "why": "shallow clone: history truncated, unreachability is not loss",
                        }
                    )
                else:
                    row.update(landed(local, ref, diff))
            else:
                row.update(
                    {
                        "verdict": "UNKNOWN",
                        "why": None
                        if not ref
                        else "head not fetched yet: run the recover command, then this door again",
                    }
                )
            reason = reasons.get(p["number"]) or {}
            row["failing_checks"] = reason.get("failing_checks", [])
            row["kill"] = reason.get("kill", "UNKNOWN")
            if row.get("verdict") in ("LOST", "PARTIAL", "UNKNOWN"):
                row["recover"] = (
                    f"git -C {local} fetch origin pull/{p['number']}/head:"
                    f"recover/pr-{p['number']} && git -C {local} diff origin/main..."
                    f"recover/pr-{p['number']}"
                )
            items.append(row)
    return items


def audit_cps(owner: str, names: list[str], since: dt.date) -> list[dict]:
    items = []
    for name in names:
        for i in gh_search(f"repo:{owner}/{name} is:issue is:open updated:>={since}"):
            body = i.get("body") or ""
            open_ = re.findall(r"^\s*[-*] \[ \] (.+)$", body, re.M)
            done = len(re.findall(r"^\s*[-*] \[[xX]\] ", body, re.M))
            if open_:
                items.append(
                    {
                        "kind": "cp",
                        "repo": name,
                        "where": f"#{i['number']}",
                        "title": i["title"][:100],
                        "updated": i["updated_at"][:10],
                        "unticked": len(open_),
                        "ticked": done,
                        "first_unticked": [s[:90] for s in open_[:3]],
                        "url": i["html_url"],
                        "verdict": "OPEN",
                    }
                )
    return items


def main() -> int:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    github = (
        sys.argv[2] if len(sys.argv) > 2 else "chidionyema/idp,chidionyema/crew"
    ).split(",")
    show_all = (sys.argv[3] if len(sys.argv) > 3 else "false").lower() == "true"
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=days)
    SINCE[0] = since
    owner = github[0].split("/")[0]
    names = [r.split("/", 1)[1] for r in github]

    targets = repos(names)
    missing = sorted({n.rsplit("/", 1)[-1] for n in github} - {p.name for p in targets})
    items, errors = [], []
    # The door has 100s and every source is owed some of it. Hand each one a deadline so the last
    # source is never starved by the first: `local` cannot eat the PR census, which IS the census.
    started = time.monotonic()
    # TOTAL doors the whole run at its real ceiling; the slices are shares of what is LEFT, not of
    # what was hoped for. Under load this machine's timings move by 50% (measured: the same run
    # takes 72s idle and 93s at load 160), so a fixed slice per source would starve the last one
    # exactly when it matters. `cp` is last and is the cheapest; `pr` carries the census.
    budget = {"local": 22.0, "pr": 34.0, "cp": 8.0, "fetch": 7.0}
    # Writing the census and printing the report costs real time on a loaded machine (the report
    # alone walks every row). It is reserved up front so a source can never spend the money that
    # pays for the answer.
    reserve = 8.0
    for n in missing:
        # Named but not checked out here. The PR side still audits it through the API; the local
        # side genuinely cannot, and silence would read as "nothing wrong in that repo".
        errors.append(
            f"local {n}: no checkout under {CODE} -- PR/stash/branch sides skipped"
        )
    for r in targets:
        # A fetch that can outlive the door is a door that never reports. This is bounded and, if
        # it runs out, says so: the local scan then reads a ref that may be stale, which is a
        # measurement the census must not silently upgrade to "nothing lost".
        rc, _ = sh(
            "git",
            "-C",
            str(r),
            "fetch",
            "-q",
            "--no-tags",
            "origin",
            timeout=max(1, int(budget["fetch"])),
        )
        if rc:
            errors.append(
                f"{r.name}: git fetch did not finish in {budget['fetch']:.0f}s; local branches and "
                f"lanes are measured against the refs already on disk, which may be stale"
            )
    for label, fn in (
        (
            "local",
            lambda: audit_local(
                since,
                targets,
                errors,
                deadline=started + budget["local"],
            ),
        ),
        (
            "pr",
            lambda: audit_prs(
                owner,
                names,
                since.date(),
                deadline=started + budget["local"] + budget["pr"],
                errors=errors,
            ),
        ),
        ("cp", lambda: audit_cps(owner, names, since.date())),
    ):
        # THE DOOR MUST ALWAYS END WITH A CENSUS. Every source above is bounded, but on a machine
        # at load 490 even bounded git calls overrun by minutes (measured: `local` alone blew its
        # 26s budget to 30s+ and the door hit its 100s ceiling with nothing written). So the wall
        # clock is checked BETWEEN sources, not only inside them: once the time a source would
        # need is gone, the remaining sources are named in `errors` and skipped. A census that
        # says "I did not reach the stashes" is worth infinitely more than a timeout that says
        # nothing, because the reader can act on the first and can only re-run the second.
        left = DOOR_BUDGET - (time.monotonic() - started) - reserve
        if left < budget[label]:
            errors.append(
                f"{label}: skipped -- {left:.0f}s left of this door's {DOOR_BUDGET:.0f}s and the "
                f"source needs about {budget[label]:.0f}s; not in this census"
            )
            continue
        t0 = time.monotonic()
        try:
            items += fn()
        except (
            Exception
        ) as e:  # one blind source must not hide the others; it is reported
            errors.append(f"{label}: {e}")
        print(f"source {label}: {time.monotonic() - t0:.0f}s", file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "at": now.isoformat(timespec="seconds"),
        "days": days,
        "errors": errors,
        "items": items,
    }
    # A CENSUS NOBODY COULD TAKE IS NOT A CENSUS. When a repo is shallow, `landed()` correctly
    # refuses to call unreachability "loss" -- so every row reads UNMEASURED. Writing that file
    # anyway hands the next agent an empty LOST list it would read as "no work was lost", which
    # is the fail-open this door exists to end. Say BLIND instead, loudly, and never publish.
    pr_rows = [i for i in items if i.get("kind") == "pr"]
    blind = [i for i in pr_rows if i.get("verdict") == "UNMEASURED"]
    if pr_rows and len(blind) == len(pr_rows):
        why = (
            "every closed-unmerged PR is UNMEASURED (the clone is shallow: "
            "`git rev-parse --is-shallow-repository` says true). Loss cannot be told from "
            "truncated history here, so no census is published. Fix: git -C <repo> fetch "
            "--unshallow origin"
        )
        errors.append(f"BLIND: {why}")
        print(f"BLIND: {why}", file=sys.stderr)
        print(f"counts: pr:UNMEASURED={len(blind)}")
        print("BLIND: no census written")
        return 2
    (OUT / "latest.json").write_text(json.dumps(result, indent=1))

    order = {
        "LOST": 0,
        "PARTIAL": 1,
        "UNKNOWN": 2,
        "OPEN": 3,
        "REMOVED": 4,
        "SKIPPED": 5,
        "LANDED": 6,
    }
    shown = [
        i
        for i in items
        if show_all or i["verdict"] not in ("LANDED", "REMOVED", "SKIPPED")
    ]
    shown.sort(key=lambda i: (order.get(i["verdict"], 9), i["kind"], i["repo"]))
    counts: dict[str, int] = {}
    for i in items:
        counts[f"{i['kind']}:{i['verdict']}"] = (
            counts.get(f"{i['kind']}:{i['verdict']}", 0) + 1
        )
    print(f"work-audit {now:%Y-%m-%dT%H:%MZ}  window={days}d  since={since.date()}")
    print("counts: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for e in errors:
        print(f"BLIND {e}")
    for i in shown:
        extra = (
            f"{i['landed_pct']}% on main now, {i['ever_pct']}% ever, of {i['added_lines']} lines"
            if "landed_pct" in i
            else f"{i['unticked']} unticked / {i['ticked']} ticked, updated {i['updated']}"
            if i["kind"] == "cp"
            else i.get("why", "")
        )
        kill = i.get("kill")
        if kill:
            extra += f"  kill={kill}"
        print(
            f"{i['verdict']:8} {i['kind']:8} {i['repo']:18} {i['where']:28} {extra}  {i.get('title', i.get('branch', ''))}"
        )
        for f in i.get("failing_checks", [])[:4]:
            print(f"{'':12}failed: {f}")
        for f in i.get("files_short", [])[:3]:
            print(f"{'':12}short: {f}")
        for f in i.get("first_unticked", [])[:3]:
            print(f"{'':12}[ ] {f}")
    print(f"full: {OUT / 'latest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
