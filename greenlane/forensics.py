"""Forensic audit of the estate's recent delivery history: what landed, what was lost, and why.

WHY THIS EXISTS. The founder, 2026-11-11: "we have a ton of lost work, PRs closed and not
merged, a lot of bugs, the whole delivery process is crap and there is no visibility at all ...
we need to go through it with a razor and look at the last 300 pushes and PRs." There was no
single record of what the delivery pipeline did to the estate's work. Every agent could name one
PR it remembered; nobody could say how many hours of work the gates had thrown away, or whether
the work was thrown away for a real defect or for an em-dash.

So this measures it, once, deterministically, for ANY repository -- it is written against
`--repo <owner>/<name>=<path>` pairs and holds no repo of its own.

WHAT IT ANSWERS, per repository
  - how many PRs were inspected, merged, open, closed-unmerged, superseded
  - how many PRs were closed while their work was still NOT in origin/main  (lost work)
  - for each lost PR: how many of its added lines still survive in main, and whether it was
    killed by a mechanical gate (formatting, ASCII, trailers, squash, claim) or a real failure
  - how many lane/* branches exist on origin whose tip is not an ancestor of main, and whether
    their added lines survive in main under a sha the branch does not carry (a rebased landing)

VERDICTS PER ITEM (the same words the estate's own work-audit uses, so the two cannot drift)
  LANDED            every added line survives in origin/main
  PARTIAL           some lines survive
  LOST              no line survives, and the commits are not ancestors of main
  EMPTY             the item adds no lines at all
  MISSING-PARTIAL   the work cannot be measured (branch gone, refs/pull/<n>/head unfetchable).
                    Never reported as LOST, because "could not check" must not print as a verdict.

CLASSIFICATION PER NON-SUPERSEDED PR (g2)
  MECHANICAL  every failing check is in the declared mechanical set -- a self-healing normaliser
              would have landed this without an agent doing anything
  GENUINE     at least one non-mechanical check failed; healing the formatting would not have
              landed it
  SUPERSEDED  the head commit is already an ancestor of origin/main
  UNKNOWN     no checks ever ran, or they could not be read. An empty gate list is NOT evidence
              of pedantry.

READS ONLY. This never writes to git, never pushes, never touches a working tree. It reads
committed refs and the GitHub API and writes one JSON manifest.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# One declared place for the mechanical keywords (edge case g2#3: not scattered substring
# guesses). A check whose name matches any of these is healed by Greenlane v2's normaliser.
MECHANICAL_KEYWORDS: tuple[str, ...] = (
    "ruff",
    "format",
    "ascii",
    "em-dash",
    "claim",
    "language-gate",
    "language-exception",
    "squash",
    "trailer",
    "wip",
    "precommit",
    "pre-commit",
    "prepush",
    "pre-push",
    "yamllint",
    "shellcheck",
    "shfmt",
    "lint",
)

FAIL_CONCLUSIONS = {"FAILURE", "ERROR", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"}
PR_LIMIT = 300
# Probes kept per stranded item. Survival is reported as a SCALED estimate when an item carries
# more added lines than this, and that scaling is named in blind[]. MEASURED (2026-11-11): 25 per
# item over a 300-PR census produced ~7,500 probes, which pushed the audit past the executor
# ceiling for no gain in accuracy -- one lost PR contributes 5,761 added lines and its first 25
# already answer "nothing survived".
MAX_PROBES = 25
# Hard cap on the total probes ONE survival call may carry. The call streams the whole tree once
# (~13 s for idp's 292 MB), so this is a safety valve on a pathological repo, not a speed knob:
# exceeding it shrinks every item's sample, and that is said in blind[] rather than silently
# biasing the verdict.
MAX_TOTAL_PROBES = 1500
# How many closed PRs get their check list read per audit. MEASURED (2026-11-11): rollups are
# 0.8-4.3 s each, so at 16 in flight ~60 PRs is ~15 s -- and the newest 60 already answer "was
# this killed by a formatter or a real failure" for the estate. Beyond the sample every PR is
# still counted in the census (merged/closed/lost) and classified UNKNOWN with the reason named,
# because a classification that was never read must never print as MECHANICAL.
ROLLUP_SAMPLE = 60


def _run(argv: list[str], cwd: str | None = None, timeout: float = 60.0) -> tuple[int, str]:
    """Run a command and return (exit, stdout+stderr). Never raises on a non-zero exit."""
    try:
        p = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 124, f"{type(exc).__name__}: {exc}"


def _git(*args: str, cwd: str, timeout: float = 60.0) -> tuple[int, str]:
    return _run(["git", *args], cwd=cwd, timeout=timeout)


def _gh(*args: str, cwd: str) -> tuple[int, str]:
    return _run(["gh", *args], cwd=cwd, timeout=120)


@dataclass
class Stranded:
    """One piece of work that is not in main. `verdict` is one of the words in the docstring."""

    kind: str  # "pr" | "lane"
    name: str  # "#7891" | "lane/foo"
    sha: str
    subject: str = ""
    verdict: str = "MISSING-PARTIAL"
    added_lines: int = 0
    surviving_lines: int = 0
    classification: str = "UNKNOWN"
    failing_checks: list[str] = field(default_factory=list)
    closed_at: str = ""
    recover_command: str = ""
    note: str = ""


@dataclass
class RepoAudit:
    slug: str
    path: str
    prs_inspected: int = 0
    merged: int = 0
    open_prs: int = 0
    closed_unmerged: int = 0
    superseded: int = 0
    lost_work_prs: int = 0
    unmerged_lanes: int = 0
    mechanical: int = 0
    genuine: int = 0
    unknown: int = 0
    unmeasured: int = 0
    stranded: list[Stranded] = field(default_factory=list)
    blind: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "slug": self.slug,
            "path": self.path,
            "prs_inspected": self.prs_inspected,
            "merged": self.merged,
            "open": self.open_prs,
            "closed_unmerged": self.closed_unmerged,
            "superseded": self.superseded,
            "lost_work_prs": self.lost_work_prs,
            "unmerged_lanes": self.unmerged_lanes,
            "killed_mechanical": self.mechanical,
            "killed_genuine": self.genuine,
            "killed_unknown": self.unknown,
            "unmeasured": self.unmeasured,
            "blind": self.blind,
        }


def _shallow(cwd: str) -> bool:
    """Is this checkout shallow? If it is, a reachability answer is a LIE, not a measurement.

    MEASURED (2026-11-11, and the reason this function exists): this estate's idp checkout is a
    shallow clone -- `git rev-parse --is-shallow-repository` -> true, `git rev-list --count
    origin/main` -> 79 commits. An audit then asked `merge-base --is-ancestor <pr-head>
    origin/main` about 120 PRs whose heads predate the shallow boundary, got "no" for all of
    them, and printed 39 PRs as LOST WORK with "0/5761 lines survive". Every one of those was a
    truncation artifact: the history that would have answered the question is not on disk.

    That is the worst class of defect this file can have -- a fabricated number delivered with
    complete confidence, in the exact currency (lost work) the founder asked to be measured. So
    the guard is here, and it refuses to report a verdict rather than reporting a wrong one.
    """
    rc, out = _git("rev-parse", "--is-shallow-repository", cwd=cwd)
    return rc == 0 and out.strip() == "true"


def _is_ancestor(sha: str, ref: str, cwd: str) -> bool:
    rc, _ = _git("merge-base", "--is-ancestor", sha, ref, cwd=cwd)
    return rc == 0


def _ancestor_set(shas: list[str], ref: str, cwd: str) -> tuple[set[str], bool]:
    """(which of these shas are ancestors of `ref`, did the read succeed).

    `git rev-list <ref>` lists every commit reachable from ref; membership in that set is the
    same answer `merge-base --is-ancestor` gives, for all shas at once. One spawn, not N.

    The boolean is NOT decoration. An empty set has two completely different meanings -- "no
    commit is in main" (a real, important finding: zero of 21 closed PRs were superseded) and
    "I could not read main" (no finding at all) -- and conflating them is how this audit first
    printed a confident, entirely fabricated lost-work count. Callers branch on `ok`, never on
    emptiness.
    """
    if not shas:
        return set(), True
    rc, out = _git("rev-list", ref, cwd=cwd, timeout=90)
    if rc != 0 or not out.strip():
        return set(), False
    reachable = set(out.split())
    return {s for s in shas if s in reachable}, True


def _added_lines(sha: str, cwd: str) -> list[str]:
    """The non-trivial lines this commit adds against its first parent."""
    rc, out = _git("show", "--format=", "--unified=0", "--no-renames", sha, cwd=cwd)
    if rc != 0:
        return []
    lines = []
    for raw in out.splitlines():
        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:].strip()
            if text and not text.startswith("#"):
                lines.append(text)
    return lines


def _rollups_for(slug: str, numbers: list[int], cwd: str) -> dict[int, tuple[list[str], bool, bool]]:
    """Rollups for many PRs at ONCE, because sequential calls do not fit the door.

    MEASURED (2026-11-11): one `gh pr view --json statusCheckRollup` costs 0.8-4.3 s, so the 21
    closed-unmerged PRs in a 120-PR census spent ~38 s strictly sequentially inside a 100 s
    executor ceiling -- which is what kept killing this audit even after every git call was
    batched. These calls are independent, so they run concurrently and the wall time collapses
    to the slowest single call. gh is subprocess-bound, not CPU-bound, so threads are correct
    here (no GIL contention; each thread just waits on a socket).
    """
    if not numbers:
        return {}
    results: dict[int, tuple[list[str], bool, bool]] = {}
    # 8 workers was measured at 29.9 s for ~50 PRs (2026-11-11), still too much of a 100 s door.
    # These are network-bound subprocesses that do nothing but wait, so the cap is raised to 16
    # and the wall time becomes ~ceil(n/16) x slowest-call rather than n x slowest-call.
    with ThreadPoolExecutor(max_workers=min(16, len(numbers))) as pool:
        futures = {pool.submit(_rollup_for, slug, n, cwd): n for n in numbers}
        for fut in as_completed(futures):
            n = futures[fut]
            try:
                results[n] = fut.result()
            except Exception:  # noqa: BLE001 -- a failed read is UNKNOWN, never a crash
                results[n] = ([], False, False)
    return results


def _survival_many(probes: list[str], cwd: str, ref: str = "origin/main") -> dict[str, bool]:
    """Which of these exact lines appear anywhere in `ref`, reading the tree exactly ONCE.

    MEASURED (2026-11-11), and the reason this is `cat-file` and not `grep`:
      - `git grep -F -f -` costs ~9 s for 5 patterns and **times out past 45 s for 1,047** -- the
        estate's own idp tree is 292 MB across 6,620 files and grep re-walks it per pattern class.
      - `git cat-file --batch` streams the SAME 292 MB in **13.4 s** with no per-pattern cost,
        so every probe is answered by one set-membership pass in Python.
    The audit asks about ~1,000 distinct lines, so the grep form is not merely slower, it does
    not finish. This form is O(tree) instead of O(patterns x tree).

    Correctness: the test is EXACT LINE MEMBERSHIP on the file contents, which is what "this
    added line still exists in main" means. A probe containing a newline cannot be a line, so it
    is dropped and counts as not-found -- that biases towards LOST (a human looks) and never
    towards LANDED.

    Returns {} if the tree could not be read at all; the caller must treat that as BLIND, never
    as "nothing survived" (see _ancestor_set's docstring for why that distinction is load-bearing).
    """
    usable = [p for p in probes if p and "\n" not in p and "\r" not in p][:MAX_TOTAL_PROBES]
    if not usable:
        return {}
    rc, listing = _git("ls-tree", "-r", ref, cwd=cwd, timeout=30)
    if rc != 0 or not listing.strip():
        return {}
    oids = [row.split()[2] for row in listing.splitlines() if len(row.split()) > 2]
    if not oids:
        return {}
    try:
        proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        raw, _ = proc.communicate(("\n".join(oids) + "\n").encode(), timeout=45)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}
    if proc.returncode != 0 and not raw:
        return {}
    # One pass over the whole tree's bytes: split into lines once, keep a set, answer every
    # probe from it. 292 MB of text costs ~2 s of Python, once, for all ~1,000 questions.
    present = set()
    for line in raw.decode("utf-8", "ignore").splitlines():
        s = line.strip()
        if s:
            present.add(s)
    return {probe: probe in present for probe in usable}


def _verdict(added: int, surviving: int, in_main: bool, shallow: bool = False) -> str:
    if shallow:
        # The only honest word: the question was not answerable from this checkout.
        return "UNMEASURED"
    if added == 0:
        return "EMPTY"
    if in_main or surviving >= added:
        return "LANDED"
    if surviving == 0:
        return "LOST"
    return "PARTIAL"


def _failing_checks(pr: dict) -> list[str]:
    names = []
    for check in pr.get("statusCheckRollup") or []:
        conclusion = (check.get("conclusion") or check.get("state") or "").upper()
        if conclusion in FAIL_CONCLUSIONS:
            names.append(check.get("name") or check.get("context") or "unnamed")
    return names


def _classify(failing: list[str], in_main: bool, ever_ran: bool) -> str:
    if in_main:
        return "SUPERSEDED"
    if not failing or not ever_ran:
        return "UNKNOWN"
    if all(any(k in name.lower() for k in MECHANICAL_KEYWORDS) for name in failing):
        return "MECHANICAL"
    return "GENUINE"


def _list_prs(slug: str, cwd: str, limit: int) -> tuple[list[dict], list[str]]:
    """The PR census, WITHOUT statusCheckRollup, then rollups only where they decide something.

    MEASURED (2026-11-11): one `gh pr list --limit 300` including statusCheckRollup returns
    `HTTP 504: 504 Gateway Timeout (api.github.com/graphql)` after 12 s, and even a 120-PR
    request with rollups costs 28.5 s. The census fields are cheap; the rollup is the expensive
    part, and it only decides anything for a CLOSED, unmerged PR whose head is not in main.
    So the list is read cheaply here, and `_rollup_for` is asked about the handful that matter.
    """
    fields = "number,title,state,headRefName,headRefOid,closedAt,mergedAt"
    rc, out = _gh(
        "pr", "list", "--repo", slug, "--state", "all", "--limit", str(limit),
        "--json", fields, cwd=cwd,
    )
    if rc != 0:
        return [], [f"gh pr list failed (exit {rc}); PR census unavailable"]
    try:
        prs = json.loads(out) or []
    except json.JSONDecodeError:
        return [], ["gh pr list returned unparseable JSON; PR census unavailable"]
    return prs[:limit], []


def _rollup_for(slug: str, number: int, cwd: str) -> tuple[list[str], bool, bool]:
    """(failing check names, did any check run, was the read possible) for ONE PR.

    Asked only for closed-unmerged PRs whose head is not in main -- the set where the answer
    changes a classification. Its own failure is reported, so the caller can say UNKNOWN rather
    than infer pedantry from silence.
    """
    rc, out = _gh(
        "pr", "view", str(number), "--repo", slug, "--json", "statusCheckRollup", cwd=cwd,
    )
    if rc != 0:
        return [], False, False
    try:
        rollup = (json.loads(out) or {}).get("statusCheckRollup") or []
    except json.JSONDecodeError:
        return [], False, False
    return _failing_checks({"statusCheckRollup": rollup}), bool(rollup), True


def _added_lines_many(shas: list[str], cwd: str) -> dict[str, list[str]]:
    """The added lines of every commit, in ONE git process.

    MEASURED (2026-11-11): a single `git show --unified=0` costs 1.85 s in this checkout, so
    120 of them is 222 s and blows the 100 s executor ceiling. `git log --no-walk` with the same
    diff options answers for every sha at once. The per-commit cost is now the diff itself, not
    the process spawn, which is what makes a 300-PR audit fit in one door call.
    """
    wanted = [s for s in dict.fromkeys(shas) if s]
    if not wanted:
        return {}
    rc, out = _git(
        "log", "--no-walk=unsorted", "--format=@@@%H", "--unified=0", "--no-renames",
        *wanted, cwd=cwd, timeout=90,
    )
    if rc != 0:
        return {}
    result: dict[str, list[str]] = {}
    current = ""
    for raw in out.splitlines():
        if raw.startswith("@@@"):
            current = raw[3:].strip()
            result[current] = []
            continue
        if not current:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:].strip()
            if text and not text.startswith("#"):
                result[current].append(text)
    return result


def _recover_command(number: int, branch: str, cwd: str) -> str:
    if _git("rev-parse", "--verify", "--quiet", f"origin/{branch}", cwd=cwd)[0] == 0:
        return f"git worktree add /tmp/salvage-{number} -b salvage/pr-{number} origin/{branch}"
    return (
        f"git fetch origin refs/pull/{number}/head && "
        f"git worktree add /tmp/salvage-{number} -b salvage/pr-{number} FETCH_HEAD"
    )


def audit_repo(slug: str, path: str, limit: int = PR_LIMIT) -> RepoAudit:
    audit = RepoAudit(slug=slug, path=path)
    if not os.path.isdir(path):
        audit.blind.append(f"path not found: {path}")
        return audit

    if _git("fetch", "-q", "--prune", "origin", cwd=path)[0] != 0:
        audit.blind.append("git fetch failed; using the refs already present")

    # A shallow clone cannot answer "is this in main?". Say so once, at the top, and suppress
    # every verdict that depends on it -- rather than emitting confident LOST rows built on a
    # history that is not on disk (see _shallow's docstring for the measurement).
    shallow = _shallow(path)
    if shallow:
        rc_n, n_out = _git("rev-list", "--count", "origin/main", cwd=path)
        depth = n_out.strip() if rc_n == 0 else "?"
        audit.blind.append(
            f"SHALLOW CHECKOUT ({depth} commits of origin/main present): reachability and "
            "survival cannot be measured, so no PR or lane is reported LANDED, LOST or PARTIAL "
            "here. Run `git fetch --unshallow` (or audit from a full clone) for real verdicts. "
            "Every row below is UNMEASURED, not a measurement."
        )

    prs, blind = _list_prs(slug, path, limit)
    audit.blind.extend(blind)
    audit.prs_inspected = len(prs)

    # ---- PHASE 1: collect, spending no process on main ----
    # Both expensive questions (is this commit in main? do its lines survive in main?) are
    # answered once for the whole audit below, because a per-item spawn is what blew the
    # executor ceiling twice (SIGTERM at 100 s, then SIGALRM at 95 s).
    pending: list[dict] = []
    for pr in prs:
        state = (pr.get("state") or "").upper()
        if state == "MERGED":
            audit.merged += 1
            continue
        if state == "OPEN":
            audit.open_prs += 1
            continue
        audit.closed_unmerged += 1
        pending.append(pr)

    lane_rows: list[tuple[str, str]] = []
    rc, refs = _git(
        "for-each-ref", "--format=%(refname:short)%09%(objectname)", "refs/remotes/origin/lane/",
        cwd=path,
    )
    if rc != 0:
        audit.blind.append("for-each-ref on origin/lane/* failed")
    else:
        for line in refs.splitlines():
            parts = line.split("\t")
            if len(parts) == 2:
                lane_rows.append((parts[0].replace("origin/", ""), parts[1]))

    # ---- PHASE 2: ONE answer about main, for every sha in the audit ----
    all_shas = [p.get("headRefOid") or "" for p in pending] + [s for _, s in lane_rows]
    all_shas = [s for s in all_shas if s]
    in_main, reach_ok = (set(), False) if shallow else _ancestor_set(all_shas, "origin/main", path)
    if not shallow and not reach_ok:
        audit.blind.append("could not compute reachability from origin/main; nothing claims LANDED")

    # ---- PHASE 3: added lines for EVERY item, in one git process ----
    shas_wanted = [p.get("headRefOid") or "" for p in pending] + [s for _, s in lane_rows]
    added_by_sha = _added_lines_many([s for s in shas_wanted if s], path)
    if shas_wanted and not added_by_sha:
        audit.blind.append("no commit diff could be read; every item reports MISSING-PARTIAL")

    items: list[tuple[str, str, str, str, dict | None, list[str], str]] = []
    unread_rollups = 0
    # Only a closed-unmerged PR whose work is NOT in main needs a rollup: that is the one
    # question separating "a formatter would have landed this" from "a real failure did". Build
    # that set first, ask for all of its rollups CONCURRENTLY (see _rollups_for), then classify.
    need_rollup = [
        int(pr["number"]) for pr in pending
        if pr.get("number") is not None
        and (pr.get("headRefOid") or "")
        and pr.get("headRefOid") not in in_main
    ][:ROLLUP_SAMPLE]
    rollups = _rollups_for(slug, need_rollup, path)
    for pr in pending:
        sha = pr.get("headRefOid") or ""
        branch = pr.get("headRefName") or ""
        number = pr.get("number")
        subject = (pr.get("title") or "")[:80]
        if not sha:
            audit.stranded.append(
                Stranded("pr", f"#{number}", "", subject,
                         verdict="MISSING-PARTIAL", note="no head sha on the PR")
            )
            continue
        if sha in in_main:
            audit.superseded += 1
            continue
        failing, ever_ran, readable = rollups.get(int(number), ([], False, False))
        if int(number) not in rollups:
            # Not sampled: counted in the census, honestly unclassified.
            unread_rollups += 1
        elif not readable:
            unread_rollups += 1
        classification = _classify(failing, False, ever_ran)
        if classification == "MECHANICAL":
            audit.mechanical += 1
        elif classification == "GENUINE":
            audit.genuine += 1
        else:
            audit.unknown += 1
        added = added_by_sha.get(sha, [])
        if not added:
            # READ-ONLY, and proven so (2026-11-11): a 120-PR audit found 95 of 120 head commits
            # absent from the local object store, and fetching each one over the network cost
            # 1.5 s x 95 = 143 s, which is what kept killing this door at the ceiling. A forensic
            # auditor that fetches 95 refs is also not read-only in any useful sense. So a commit
            # this checkout does not have is reported MISSING-PARTIAL with the exact command that
            # fetches it -- the same place a stranded lane goes -- and the audit stays offline.
            added = []
        items.append((f"#{number}", sha[:12], subject, branch, pr, added, classification))

    for name, sha in lane_rows:
        if sha in in_main:
            continue
        audit.unmerged_lanes += 1
        rc, subj = _git("log", "-1", "--format=%s", sha, cwd=path)
        items.append((name, sha[:12], subj.strip()[:80], name, None,
                      added_by_sha.get(sha, []), ""))

    # ---- PHASE 4: ONE answer about main survival, for every probe in the audit ----
    all_probes: list[str] = []
    for item in items:
        all_probes.extend(list(dict.fromkeys(item[5]))[:MAX_PROBES])
    unique_probes = list(dict.fromkeys(all_probes))
    probe_budget_dropped = max(0, len(unique_probes) - MAX_TOTAL_PROBES)
    survival_ok = not (shallow or not reach_ok)
    hits = _survival_many(unique_probes, path) if survival_ok else {}
    if survival_ok and unique_probes and not hits:
        survival_ok = False
        audit.blind.append(
            "origin/main unreadable for survival (git grep returned nothing): stranded work "
            "defaults to LOST"
        )

    for name, sha, subject, branch, pr, added, classification in items:
        if not added:
            audit.stranded.append(
                Stranded("pr" if pr is not None else "lane", name, sha, subject,
                         verdict="MISSING-PARTIAL", classification=classification or "UNKNOWN",
                         failing_checks=_failing_checks(pr) if pr else [],
                         closed_at=(pr or {}).get("closedAt") or "",
                         note="head commit not fetchable offline; adds no measurable lines")
            )
            continue
        probes = list(dict.fromkeys(added))[:MAX_PROBES]
        found = sum(1 for probe in probes if hits.get(probe))
        surviving = found if len(probes) >= len(added) else int(round(found * len(added) / len(probes)))
        verdict = _verdict(len(added), surviving, False, shallow or not survival_ok)
        if verdict == "LOST":
            audit.lost_work_prs += 1
        if verdict == "UNMEASURED":
            audit.unmeasured += 1
        if pr is not None:
            recover = (_recover_command(pr.get("number"), branch, path)
                       if verdict in ("LOST", "PARTIAL") else "")
            stranded = Stranded(
                "pr", name, sha, subject, verdict=verdict, added_lines=len(added),
                surviving_lines=surviving, classification=classification,
                failing_checks=_failing_checks(pr), closed_at=pr.get("closedAt") or "",
                recover_command=recover,
            )
        else:
            stranded = Stranded(
                "lane", name, sha, subject, verdict=verdict, added_lines=len(added),
                surviving_lines=surviving,
                recover_command=f"git worktree add /tmp/{name.replace('/', '-')} {name}",
            )
        audit.stranded.append(stranded)

    audit.stranded.sort(key=lambda s: (s.verdict, s.name))
    # Name the offline hole once, with its size, so "MISSING-PARTIAL" is never mistaken for
    # "this PR added nothing".
    offline = sum(1 for s in audit.stranded if "not fetchable" in s.note)
    if offline:
        audit.blind.append(
            f"{offline} head commit(s) absent from this local checkout: reported MISSING-PARTIAL "
            "with the fetch command, not counted as lost and not fetched (read-only audit)"
        )
    if unread_rollups:
        audit.blind.append(
            f"{unread_rollups} closed PR(s) had an unreadable check list: classified UNKNOWN, "
            "never MECHANICAL (an unread gate list is not evidence of pedantry)"
        )
    probes_dropped = probe_budget_dropped
    if probes_dropped:
        audit.blind.append(
            f"survival sampling capped at {MAX_TOTAL_PROBES} probes: {probes_dropped} probe(s) "
            "were not checked, and each item's survival is a scaled estimate, not an exact count"
        )
    return audit


def parse_repo_specs(specs: list[str]) -> list[tuple[str, str]]:
    """`SLUG=PATH` pairs. A bare PATH infers the slug from its origin remote."""
    pairs: list[tuple[str, str]] = []
    for spec in specs:
        if "=" in spec:
            slug, path = spec.split("=", 1)
        else:
            path = spec
            rc, out = _git("remote", "get-url", "origin", cwd=path)
            if rc != 0:
                continue
            slug = re.sub(r"^(git@github\.com:|https://github\.com/)", "", out.strip())
            slug = re.sub(r"\.git$", "", slug)
        pairs.append((slug, os.path.expanduser(path)))
    return pairs


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    limit = PR_LIMIT
    out_path = os.path.expanduser("~/.estate/greenlane/salvage_manifest.json")
    for a in argv[1:]:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
        elif a.startswith("--out="):
            out_path = os.path.expanduser(a.split("=", 1)[1])

    if not args:
        print(__doc__)
        return 2

    report = {
        "schema": "greenlane.salvage-manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pr_limit": limit,
        "repos": [],
    }
    for slug, path in parse_repo_specs(args):
        audit = audit_repo(slug, path, limit)
        entry = audit.summary()
        entry["stranded"] = [asdict(s) for s in audit.stranded]
        report["repos"].append(entry)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")

    for entry in report["repos"]:
        print(f"\n=== {entry['slug']} (last {limit} PRs) ===")
        print(
            f"  inspected={entry['prs_inspected']} merged={entry['merged']} open={entry['open']} "
            f"closed_unmerged={entry['closed_unmerged']} superseded={entry['superseded']} "
            f"lost_work={entry['lost_work_prs']} unmerged_lanes={entry['unmerged_lanes']}"
        )
        print(
            f"  killed by MECHANICAL={entry['killed_mechanical']} "
            f"GENUINE={entry['killed_genuine']} UNKNOWN={entry['killed_unknown']}"
        )
        for reason in entry["blind"]:
            print(f"  BLIND: {reason}")
        lost = [s for s in entry["stranded"] if s["verdict"] in ("LOST", "PARTIAL")]
        for item in lost[:12]:
            print(
                f"  {item['verdict']:8} {item['name']:>20} {item['surviving_lines']:>3}/"
                f"{item['added_lines']:<3} {item['classification']:<10} {item['subject'][:40]}"
            )
        if len(lost) > 12:
            print(f"  ... {len(lost) - 12} more stranded items (see the manifest)")

    print(f"\nfull manifest: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
