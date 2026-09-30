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


def sh(*a, cwd=None, timeout=120) -> tuple[int, str]:
    try:
        r = subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=timeout)
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


def main_lines(repo: Path, ref: str, path: str) -> set[str] | None:
    key = (str(repo), path)
    if key not in _main_cache:
        rc, txt = sh("git", "-C", str(repo), "show", f"{ref}:{path}")
        _main_cache[key] = None if rc else {ln.strip() for ln in txt.splitlines()}
    return _main_cache[key]


_hist: dict[str, set[int]] = {}
_hist_lock = threading.Lock()
SINCE = [dt.datetime.now(dt.timezone.utc)]


def history(repo: Path, ref: str) -> set[int]:
    """Hashes of every line ADDED on main since the window opened (plus 30 days of slack), so
    work that landed and was later deleted reads REMOVED, not LOST. One pass per repo."""
    with _hist_lock:
        if str(repo) not in _hist:
            since = (SINCE[0] - dt.timedelta(days=30)).date()
            p = subprocess.Popen(
                [
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
                    "--format=",
                ],
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
            p.wait()
            _hist[str(repo)] = seen
        return _hist[str(repo)]


def landed(repo: Path, ref: str, diff: str | dict[str, list[str]]) -> dict:
    files = added_by_file(diff) if isinstance(diff, str) else diff
    total = hit = ever = 0
    missing: list[str] = []
    gone: list[str] = []
    hist = history(repo, ref) if files else set()
    for path, lines in files.items():
        have = main_lines(repo, ref, path)
        if have is None:
            gone.append(path)
        n = sum(1 for ln in lines if have and ln in have)
        e = sum(1 for ln in lines if not (have and ln in have) and hash(ln) in hist)
        total += len(lines)
        hit += n
        ever += e
        if n + e < len(lines) * 0.9:
            missing.append(f"{path} {n + e}/{len(lines)}")
    now = hit / total if total else 1.0
    eff = (hit + ever) / total if total else 1.0
    verdict = (
        "LANDED"
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


def repos() -> list[Path]:
    return sorted(p.parent for p in CODE.glob("*/.git") if p.is_dir())


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


def audit_local(since: dt.datetime) -> list[dict]:
    items: list[dict] = []
    dirty: list[tuple] = []
    seen_wt: set[Path] = set()
    for repo in repos():
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
            diff = git(wt, "diff", "HEAD")
            for f in git(wt, "ls-files", "--others", "--exclude-standard").splitlines():
                if not NOISE.search(f):
                    diff += (
                        "\n"
                        + sh(
                            "git", "-C", str(wt), "diff", "--no-index", "/dev/null", f
                        )[1]
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
        # local-only commits
        for line in git(
            repo,
            "for-each-ref",
            "--format=%(refname:short) %(committerdate:iso-strict)",
            "refs/heads",
        ).splitlines():
            br, _, when = line.partition(" ")
            try:
                if dt.datetime.fromisoformat(when) < since:
                    continue
            except ValueError:
                continue
            n = git(repo, "rev-list", "--count", br, "--not", "--remotes").strip()
            if n and n != "0":
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
        # stashes
        for line in git(repo, "stash", "list", "--format=%gd %cI %gs").splitlines():
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


def gh_search(q: str) -> list[dict]:
    out, page = [], 1
    while True:
        rc, txt = sh(
            "gh",
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


def audit_prs(owner: str, names: list[str], since: dt.date) -> list[dict]:
    items = []
    for name in names:
        local = CODE / name
        prs = gh_search(
            f"repo:{owner}/{name} is:pr is:closed is:unmerged closed:>={since}"
        )
        ref = main_ref(local) if (local / ".git").exists() else None
        if ref and prs:
            specs = [
                f"+refs/pull/{p['number']}/head:refs/work-audit/pr/{p['number']}"
                for p in prs
            ]
            for i in range(0, len(specs), 50):
                sh(
                    "git",
                    "-C",
                    str(local),
                    "fetch",
                    "-q",
                    "origin",
                    *specs[i : i + 50],
                    timeout=600,
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
            head = f"refs/work-audit/pr/{p['number']}"
            if (
                ref
                and sh("git", "-C", str(local), "rev-parse", "-q", "--verify", head)[0]
                == 0
            ):
                base = git(local, "merge-base", ref, head).strip() or ref
                row.update(landed(local, ref, git(local, "diff", base, head)))
            else:
                row.update(
                    {
                        "verdict": "UNKNOWN",
                        "why": "no local clone or head not fetchable",
                    }
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

    for r in repos():
        sh("git", "-C", str(r), "fetch", "-q", "origin", timeout=120)
    items, errors = [], []
    for label, fn in (
        ("local", lambda: audit_local(since)),
        ("pr", lambda: audit_prs(owner, names, since.date())),
        ("cp", lambda: audit_cps(owner, names, since.date())),
    ):
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
        print(
            f"{i['verdict']:8} {i['kind']:8} {i['repo']:18} {i['where']:28} {extra}  {i.get('title', i.get('branch', ''))}"
        )
        for f in i.get("files_short", [])[:3]:
            print(f"{'':12}short: {f}")
        for f in i.get("first_unticked", [])[:3]:
            print(f"{'':12}[ ] {f}")
    print(f"full: {OUT / 'latest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
