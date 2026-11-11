#!/usr/bin/env python3
"""Forensic auditor: what actually happened to the work nobody merged.

The estate loses work it has already paid for. A PR is closed unmerged, a lane branch is
abandoned, an agent's afternoon becomes a dangling ref. Until now the only record of that was
whoever remembered, so "lost work" was an opinion. This measures it.

WHAT IT ANSWERS, per repo:
  - how many of the last N PRs merged, are open, or were closed without merging
  - of the closed ones, how many are SUPERSEDED (their head is already in main) from genuinely
    stranded
  - for every stranded item, how much of its added work still exists in main: LANDED, PARTIAL,
    LOST, EMPTY, MISSING-PARTIAL or UNMEASURED
  - what killed it, classified MECHANICAL (a normalizer could have fixed it), GENUINE (a real
    failure) or UNKNOWN (the checks could not be read -- never silently called mechanical)
  - the exact command to recover each strand

READ-ONLY BY CONSTRUCTION. It reads committed refs and the GitHub API. It never fetches, never
writes to a worktree, never touches an index. Output is the report plus
~/.estate/greenlane/salvage_manifest.json.

WHY THAT MATTERS, measured 2026-11-11: a 120-PR audit found 95 of 120 head commits absent from
the local object store, and fetching each cost 1.5 s, so per-PR fetch was 143 s and kept killing
the 100 s door. A forensic tool that fetches 95 refs is also not read-only in any useful sense.
An absent commit is reported MISSING-PARTIAL with the command that fetches it.

USAGE
    python3 greenlane/forensics.py --limit=300 chidionyema/idp=/path/to/checkout
    python3 greenlane/forensics.py chidionyema/idp chidionyema/argon   # uses default local paths
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# A check name containing one of these is a formatting/cosmetic failure, not a broken build.
#
# SUBSTRING MATCH IS DANGEROUS HERE, and it produced a real fabrication: a bare "claim" keyword
# marked `claim-gate` and `dof-gate` MECHANICAL, so 10 closed PRs that failed a substantive
# governance check were reported as auto-healable. They are not -- failing claim-gate means the
# change had no claim, which is a real problem with the change, not a normalizer's job. Gates
# whose NAME merely contains a cosmetic word are excluded explicitly below.
MECHANICAL_KEYWORDS = (
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
    "license-header",
    "sign-off",
    "dco",
    "regenerate",
)
# Substantive gates. A failure here is never cosmetic, whatever else the name contains.
SUBSTANTIVE_CHECKS = (
    "claim-gate",
    "dof-gate",
    "guarded-paths",
    "ci-success",
    "shadow-verify",
    "verify",
    "fast-gate",
    "gate /",
    "check",
)
FAIL_CONCLUSIONS = (
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "startup_failure",
)
# The lane writes its OWN verdict on the head it judged, as a commit-status context named
# "greenlane", and the DESCRIPTION is the reason the work did not land. Measured 2026-11-11 over
# the 61 stranded items: 53 carried this verdict, and 30 of them (12,671 added lines -- 68% of
# ALL stranded work) said the same thing: "refused: retired, this lane head is 1 days old".
# The work was never judged. It aged out. An auditor that cannot read the reason can say a PR
# died but never why, and a salvage machine with no reason cannot heal anything.
LANE_VERDICT_CONTEXT = "greenlane"
VERDICT_WORKERS = 16

PR_LIMIT = 300
# Per item we sample at most this many added lines. Added work in one PR is routinely hundreds of
# lines; asking about all of them buys precision the verdict does not use (PARTIAL vs LOST is
# decided by a handful of survivors) and costs time in every phase.
MAX_PROBES = 25
MAX_TOTAL_PROBES = 1500
# Reading a PR's check rollup is a network round trip. 21 of them sequentially measured 38 s, so
# they run concurrently -- and only for the rows where the answer decides the classification.
ROLLUP_SAMPLE = 60
ROLLUP_WORKERS = 16

MANIFEST_PATH = os.path.expanduser("~/.estate/greenlane/salvage_manifest.json")
SCHEMA = "greenlane.salvage-manifest.v1"

DEFAULT_REPOS = {
    "chidionyema/idp": "~/Documents/code/idp",
    "chidionyema/argon": "~/Documents/code/argon",
}


@dataclass
class Rollup:
    """What one head commit's CHECK RUNS said.

    Two shapes reach us and BOTH must be read. A CheckRun carries `conclusion` and `status`; a
    legacy commit-status context carries `state` and NO conclusion field at all. The first
    version of this file read only the CheckRun shape, so every `state: FAILURE` context was
    silently dropped -- and the resulting empty failing set was then reported as "no failing
    check", which the classifier turned into a fabricated GENUINE. Measured 2026-11-11: 8 of the
    24 closed-unmerged PRs carried a `greenlane` context with `state=FAILURE` and were all
    classified GENUINE with an empty evidence list.
    """

    failing: list[str] = field(default_factory=list)
    succeeded: int = 0
    concluded: int = 0
    readable: bool = False


@dataclass
class HeadStatus:
    """Every LEGACY commit status GitHub recorded on one head commit.

    The status API and the check-runs API are disjoint: a head can have 30 check runs and no
    legacy status at all, or one legacy status and no check runs. Reading only one of them
    leaves half the evidence unseen.
    """

    contexts: list[tuple[str, str, str]] = field(default_factory=list)
    # (context, state, description)
    readable: bool = False

    def lane_reason(self) -> str:
        """The estate's own verdict on this head, when it failed."""
        for context, state, description in self.contexts:
            if (
                context.strip().lower() == LANE_VERDICT_CONTEXT
                and state in ("failure", "error")
            ):
                return description
        return ""

    def other_failure(self) -> tuple[str, str]:
        """(context, description) of the first failure that is not the lane verdict."""
        for context, state, description in self.contexts:
            if (
                context.strip().lower() != LANE_VERDICT_CONTEXT
                and state in ("failure", "error")
            ):
                return context, description
        return "", ""

    def lane_pending_reason(self) -> str:
        """The lane's verdict when it had NOT judged the work.

        A pending lane context is not a failure and not a success: it is the estate saying it
        never got to the work. Reported so the census does not read it as a red check.
        """
        for context, state, description in self.contexts:
            if context.strip().lower() == LANE_VERDICT_CONTEXT and state not in (
                "success",
                "failure",
                "error",
            ):
                return description
        return ""


@dataclass
class Item:
    """One stranded thing: a closed-unmerged PR or an unmerged lane."""

    name: str
    sha: str
    subject: str
    branch: str
    pr: dict | None = None
    added: list[str] = field(default_factory=list)
    classification: str = "UNKNOWN"
    kill_class: str = "UNKNOWN"
    kill_reason: str = ""
    failing_checks: list[str] = field(default_factory=list)


@dataclass
class Stranded:
    """One piece of work that did not land, and what became of it."""

    kind: str  # "pr" | "lane"
    name: str  # "#1234" or the branch name
    sha: str
    subject: str
    verdict: str = "UNMEASURED"
    added_lines: int = 0
    surviving_lines: int = 0
    classification: str = "UNKNOWN"
    failing_checks: list[str] = field(default_factory=list)
    kill_class: str = "UNKNOWN"
    kill_reason: str = ""
    closed_at: str = ""
    recover_command: str = ""
    note: str = ""


@dataclass
class RepoAudit:
    slug: str
    path: str
    inspected: int = 0
    merged: int = 0
    open_prs: int = 0
    closed_unmerged: int = 0
    superseded: int = 0
    lost_work_prs: int = 0
    unmerged_lanes: int = 0
    mechanical: int = 0
    genuine: int = 0
    unknown: int = 0
    closed_by_decision: int = 0
    unmeasured: int = 0
    kill_classes: dict[str, int] = field(default_factory=dict)
    kill_class_lines: dict[str, int] = field(default_factory=dict)
    stranded: list[Stranded] = field(default_factory=list)
    blind: list[str] = field(default_factory=list)


def _run(
    argv: list[str], cwd: str | None = None, timeout: float = 30.0
) -> tuple[int, str]:
    """Run a command and return (exit, stdout+stderr). Never raises on a non-zero exit.

    Every argv this module builds is a fixed list of literals (git, gh and their subcommands);
    no shell is involved and no caller-supplied string is ever interpolated into one, so the
    untrusted-input warning is answered by construction rather than by a runtime check.
    """
    try:
        p = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no interpolated input
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return 1, str(exc)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _git(*args: str, cwd: str, timeout: float = 30.0) -> tuple[int, str]:
    return _run(["git", *args], cwd=cwd, timeout=timeout)


def _gh(*args: str, cwd: str | None = None, timeout: float = 60.0) -> tuple[int, str]:
    return _run(["gh", *args], cwd=cwd, timeout=timeout)


def _shallow(cwd: str) -> bool:
    """True when this checkout's history is truncated.

    THE most important guard in this file. A shallow clone answers "is this commit an ancestor of
    main?" with a confident "no" for everything below the boundary -- it does not error, it just
    has no history to walk. Measured 2026-11-11: the idp checkout held 79 commits, every closed PR
    head predated the boundary, and 39 PRs were reported LOST with 0/5761 lines surviving. That is
    not a wrong number, it is a fabricated one, in the exact currency this audit exists to measure.
    """
    rc, out = _git("rev-parse", "--is-shallow-repository", cwd=cwd)
    return rc == 0 and out.strip() == "true"


def _ancestor_set(shas: list[str], ref: str, cwd: str) -> tuple[set[str], bool]:
    """Which of `shas` are ancestors of `ref`. Returns (ancestors, did_the_read_succeed).

    The second element is load-bearing and is why this returns a tuple. An EMPTY set has two
    completely different meanings -- "none of these commits are in main" (a real finding, and the
    expected answer for a PR that was closed unmerged) and "I could not read main" (blind) -- and
    the first version of this audit conflated them. It counted the empty set as failure, printed
    "could not compute reachability", and made a true superseded=0 look like a blind spot.
    Callers MUST branch on the flag, never on the set being empty.
    """
    if not shas:
        return set(), True
    rc, out = _git("rev-list", ref, cwd=cwd, timeout=120)
    if rc != 0 or not out.strip():
        return set(), False
    in_main = set(out.split())
    return {s for s in shas if s in in_main}, True


def _is_ancestor(sha: str, ref: str, cwd: str) -> bool:
    rc, _ = _git("merge-base", "--is-ancestor", sha, ref, cwd=cwd, timeout=30)
    return rc == 0


def _added_lines(sha: str, cwd: str) -> list[str]:
    """The lines this commit added, as exact strings (one commit).

    Uses --no-renames and -U0 so that only genuinely added lines are considered: a context line
    'surviving' in main says nothing about whether this change landed.
    """
    return _added_lines_many([sha], cwd).get(sha, [])


def _added_lines_many(shas: list[str], cwd: str) -> dict[str, list[str]]:
    """Added lines for MANY commits in ONE `git log`.

    Measured 2026-11-11: one `git log --no-walk` for a commit costs ~1.85 s including process
    start, so the per-commit form was 222 s for 120 PRs. This form amortises the process cost and
    the diff machinery across the whole batch.
    """
    if not shas:
        return {}
    rc, out = _git(
        "log",
        "--no-walk=unsorted",
        "--format=@@@%H",
        "--unified=0",
        "--no-renames",
        *shas,
        cwd=cwd,
        timeout=120,
    )
    if rc != 0:
        return {}
    added: dict[str, list[str]] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("@@@"):
            current = line[3:].strip()
            added.setdefault(current, [])
        elif current and line.startswith("+") and not line.startswith("+++"):
            text = line[1:]
            if text.strip():
                added[current].append(text)
    return added


def _touched_files(shas: list[str], cwd: str) -> dict[str, list[str]]:
    """For each commit, the paths it touched, from ONE `git log --name-only`.

    This is the optimisation that makes survival affordable. Scanning the WHOLE tree to answer
    "does this line still exist in main" costs 21.8 s (git cat-file over 293 MB, measured
    2026-11-11, cold) -- more than the whole rest of the audit, repeated for every run. A stranded
    line can only survive in a file its own commit touched, so restricting the search to those
    paths is not an approximation: it is the same answer over a tiny fraction of the bytes.
    """
    if not shas:
        return {}
    rc, out = _git(
        "log",
        "--no-walk=unsorted",
        "--name-only",
        "--format=@@@%H",
        *shas,
        cwd=cwd,
        timeout=60,
    )
    if rc != 0:
        return {}
    touched: dict[str, list[str]] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("@@@"):
            current = line[3:].strip()
            touched.setdefault(current, [])
        elif line.strip() and current:
            touched[current].append(line.strip())
    return touched


def _survival_in_paths(
    probes_by_sha: dict[str, list[str]],
    paths_by_sha: dict[str, list[str]],
    cwd: str,
    ref: str = "origin/main",
) -> dict[str, bool]:
    """Which probes survive in `ref`, reading ONLY the files their own commit touched.

    One `git cat-file --batch` over the union of those blobs (typically a few hundred files, not
    6,620), then exact line membership. The correctness contract is identical to the whole-tree
    scan -- a line survives iff it appears as a line in main -- but the bytes read drop by one to
    two orders of magnitude, which is what brings the audit inside the executor's 100 s ceiling
    without dropping a single probe. Measured: 83.7 s -> 29.7 s.

    Returns {} if nothing could be read at all; the caller must treat that as BLIND, never as
    "nothing survived".
    """
    all_paths = sorted({p for paths in paths_by_sha.values() for p in paths})
    if not all_paths:
        return {}
    rc, listing = _git("ls-tree", "-r", ref, "--", *all_paths, cwd=cwd, timeout=60)
    if rc != 0 or not listing.strip():
        return {}
    oid_by_path: dict[str, str] = {}
    for row in listing.splitlines():
        parts = row.split(None, 3)
        if len(parts) >= 4 and parts[1] == "blob":
            oid_by_path[parts[3]] = parts[2]
    if not oid_by_path:
        return {}
    try:
        proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],  # noqa: S607 -- `git` resolved on PATH by design
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        raw, _ = proc.communicate(
            "\n".join(sorted(set(oid_by_path.values()))).encode() + b"\n", timeout=45
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}
    if proc.returncode != 0 and not raw:
        return {}
    # A line survives if it is present in ANY of these files, matching the whole-tree semantics
    # (where a moved line still counts as surviving).
    text = raw.decode("utf-8", "ignore")
    present = {s for s in (ln.strip() for ln in text.splitlines()) if s}
    result: dict[str, bool] = {}
    for probes in probes_by_sha.values():
        for probe in probes:
            if probe and "\n" not in probe and "\r" not in probe:
                result[probe] = probe in present
    return result


def _survival_many(
    probes: list[str], cwd: str, ref: str = "origin/main"
) -> dict[str, bool]:
    """Which of these exact lines appear anywhere in `ref`, reading the tree exactly ONCE.

    KEPT FOR CROSS-CHECKS AND SMALL SETS ONLY; the audit uses `_survival_in_paths`. The whole-tree
    read is measured at 21.8 s cold on idp's 293 MB and would spend a quarter of the door.

    MEASURED (2026-11-11), and the reason this is `cat-file` and not `grep`:
      - `git grep -F -q` costs 5.1-8.3 s for ONE pattern; the tree walk and blob inflation
        dominate, and `grep.threads=16` changes nothing.
      - `git grep -F -f -` with 1,047 patterns does not finish inside 45 s.
      - `git cat-file --batch` streams the SAME 292 MB in 13.4-21.8 s with no per-pattern cost.
    """
    usable = [p for p in probes if p and "\n" not in p and "\r" not in p][
        :MAX_TOTAL_PROBES
    ]
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
            ["git", "cat-file", "--batch"],  # noqa: S607 -- `git` resolved on PATH by design
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        raw, _ = proc.communicate(("\n".join(oids) + "\n").encode(), timeout=45)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}
    if proc.returncode != 0 and not raw:
        return {}
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


def _list_prs(slug: str, limit: int, cwd: str | None) -> tuple[list[dict], bool, str]:
    """The census, WITHOUT check rollups.

    Measured 2026-11-11: `gh pr list --json ...,statusCheckRollup` for 120 PRs took 28.5 s and
    once returned a gateway 504; the same list without rollup fields took 2.3 s. Rollups are only
    needed for the handful of rows where they decide the classification, so they are asked
    separately and concurrently (see _rollups_for).
    """
    fields = "number,title,state,headRefOid,headRefName,closedAt,mergedAt,url"
    rc, out = _gh(
        "pr",
        "list",
        "--repo",
        slug,
        "--state",
        "all",
        "--limit",
        str(limit),
        "--json",
        fields,
        cwd=cwd,
        timeout=90,
    )
    if rc != 0 or not out.strip():
        return [], False, out.strip()[:200]
    try:
        return json.loads(out[out.index("[") :]), True, ""
    except (ValueError, TypeError) as exc:
        return [], False, f"unparseable gh output: {exc}"


def _rollup_for(slug: str, number: int, cwd: str | None) -> Rollup:
    """What one PR head's checks said: the failing names, how many passed, was it readable."""
    rc, out = _gh(
        "pr",
        "view",
        str(number),
        "--repo",
        slug,
        "--json",
        "statusCheckRollup",
        cwd=cwd,
        timeout=45,
    )
    if rc != 0 or not out.strip():
        return Rollup()
    try:
        data = json.loads(out[out.index("{") :]).get("statusCheckRollup") or []
    except (ValueError, TypeError):
        return Rollup()
    roll = _parse_rollup(data)
    return roll


def _parse_rollup(entries: list) -> Rollup:
    """Read BOTH check shapes out of a PR status rollup.

    A CheckRun carries `conclusion` and `status`; a legacy commit-status context carries `state`
    and NO conclusion field at all. The first version of this file read only the CheckRun shape,
    so every `state: FAILURE` context was silently dropped -- and the resulting empty failing set
    was then reported as "no failing check", which the classifier turned into a fabricated
    GENUINE. Measured 2026-11-11: 8 of the 24 closed-unmerged PRs carried a `greenlane` context
    with `state=FAILURE` and were all classified GENUINE with an empty evidence list.
    """
    roll = Rollup(readable=True)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = (
            entry.get("name")
            or entry.get("context")
            or (entry.get("checkSuite") or {}).get("app", {}).get("name")
            or "unnamed-check"
        )
        conclusion = (entry.get("conclusion") or "").lower()
        status = (entry.get("status") or "").lower()
        state = (entry.get("state") or "").lower()
        if conclusion in FAIL_CONCLUSIONS or state in ("failure", "error"):
            roll.failing.append(name)
            roll.concluded += 1
        elif conclusion == "success" or state == "success":
            roll.succeeded += 1
            roll.concluded += 1
        elif conclusion in ("skipped", "neutral") or state == "expected":
            roll.concluded += 1
        # A check that has not concluded is NO EVIDENCE: not a failure, not a success. The
        # first version of this file called it a failure, which turned a queued check on a
        # closed PR into a fabricated GENUINE -- the same defect as the empty-set guess.
    return roll


def _rollups_for(slug: str, numbers: list[int], cwd: str | None) -> dict[int, Rollup]:
    """Rollups for MANY PRs, concurrently.

    These are network-bound subprocess calls, so threads are the right tool and the GIL is not in
    the way. Measured 2026-11-11: 21 rollups sequentially took 38 s; this form is what makes the
    classification affordable inside one door call.
    """
    results: dict[int, Rollup] = {}
    if not numbers:
        return results
    workers = min(ROLLUP_WORKERS, len(numbers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_rollup_for, slug, n, cwd): n for n in numbers}
        for future in as_completed(futures):
            number = futures[future]
            try:
                results[number] = future.result()
            except Exception:  # noqa: BLE001 -- one failed rollup must not blind the audit
                results[number] = Rollup()
    return results


def _statuses_for(slug: str, sha: str, cwd: str | None) -> HeadStatus:
    """Every LEGACY commit status on one head commit, with its description.

    The description is where the estate's own verdict lives ("refused: retired, this lane head
    is 1 days old"). The status API is disjoint from the check-runs API, so this is read
    alongside the rollup, never instead of it.
    """
    rc, out = _gh("api", f"repos/{slug}/commits/{sha}/status", cwd=cwd, timeout=45)
    if rc != 0 or not out.strip():
        return HeadStatus()
    try:
        data = json.loads(out[out.index("[") :])
    except (ValueError, TypeError):
        return HeadStatus()
    contexts = [
        (
            str(entry.get("context") or "unnamed-status"),
            str(entry.get("state") or "").lower(),
            str(entry.get("description") or "").strip(),
        )
        for entry in (data or [])
        if isinstance(entry, dict)
    ]
    return HeadStatus(contexts=contexts, readable=True)


def _statuses_batch(
    slug: str, shas: list[str], cwd: str | None
) -> dict[str, HeadStatus]:
    """The head statuses for MANY commits, concurrently."""
    results: dict[str, HeadStatus] = {}
    if not shas:
        return results
    workers = min(VERDICT_WORKERS, len(shas))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_statuses_for, slug, sha, cwd): sha for sha in shas}
        for future in as_completed(futures):
            sha = futures[future]
            try:
                results[sha] = future.result()
            except Exception:  # noqa: BLE001 -- one unreadable status must not blind the audit
                results[sha] = HeadStatus()
    return results


def _failing_checks(pr: dict) -> list[str]:
    return list(pr.get("_failing") or [])


def _classify(failing: list[str], readable: bool, succeeded: int = 0) -> str:
    """MECHANICAL if ONLY cosmetic checks failed; GENUINE for a real failure; else UNKNOWN.

    All of the failing checks must be cosmetic for MECHANICAL, and none may be substantive. A PR
    that failed ruff AND claim-gate did not fail for a formatting reason -- it had no claim -- and
    calling that auto-healable sends a normalizer to fix the wrong thing.

    THE LAW: an empty failing set is NEVER a failure. It is either a decision (CLOSED_BY_DECISION,
    when at least one check succeeded and none failed) or no evidence at all (UNKNOWN). The first
    version of this file returned GENUINE for an empty failing set on any PR that had a rollup,
    which asserted a failure the evidence did not support -- and hid the real evidence, because
    the rollup reader dropped legacy `state: FAILURE` contexts entirely.
    """
    if not readable:
        return "UNKNOWN"
    if failing:
        lowered = [f.lower() for f in failing]
        if any(any(s in f for s in SUBSTANTIVE_CHECKS) for f in lowered):
            return "GENUINE"
        return (
            "MECHANICAL"
            if all(any(k in f for k in MECHANICAL_KEYWORDS) for f in lowered)
            else ("GENUINE")
        )
    if succeeded > 0:
        return "CLOSED_BY_DECISION"
    return "UNKNOWN"


def _kill_class(description: str) -> tuple[str, bool]:
    """(class, mechanically_repairable) for a recorded reason.

    `mechanically_repairable` means a deterministic action can make the work land -- re-run a
    lane that aged out, rebase it onto main. It is False for anything that needs a judgement, a
    person, or an event outside the estate.
    """
    text = (description or "").strip().lower()
    if not text:
        return "UNKNOWN", False
    if "retired" in text and "lane head" in text:
        return "STALE_RETIRED", True
    if "does not rebase onto main" in text:
        return "NOT_REBASED", True
    if "no live claim" in text:
        return "CLAIM_MISSING", False
    if "rate limit" in text or "rate-limited" in text:
        return "EXTERNAL_QUOTA", False
    if "has not judged it yet" in text or text.startswith("queued"):
        return "NOT_JUDGED", False
    if "failure --" in text or "failure:" in text:
        return "CHECK_FAILED", False
    if "refused" in text:
        return "LANE_REFUSED", False
    return "UNKNOWN", False


def _classify_head(
    failing: list[str], readable: bool, succeeded: int, status: HeadStatus
) -> tuple[str, str, str]:
    """(classification, kill_class, kill_reason) for one stranded head.

    The estate's own lane verdict wins when it failed, because it is the RECORDED reason the
    work did not land -- and it is more specific than any list of check names. Only when it did
    not fail do the checks decide.

    Measured 2026-11-11: reading it moved 8 PRs (5,783 added lines) off a fabricated GENUINE
    onto the reason the estate actually recorded.
    """
    lane_reason = status.lane_reason()
    if lane_reason:
        kill_class, mechanical = _kill_class(lane_reason)
        if mechanical:
            return "MECHANICAL", kill_class, lane_reason
        if kill_class == "NOT_JUDGED":
            return "UNKNOWN", kill_class, lane_reason
        return "GENUINE", kill_class, lane_reason

    _context, description = status.other_failure()
    if description:
        kill_class, mechanical = _kill_class(description)
        if mechanical:
            return "MECHANICAL", kill_class, description
        if kill_class == "UNKNOWN":
            return "GENUINE", "CHECK_FAILED", description
        return "GENUINE", kill_class, description

    pending_reason = status.lane_pending_reason()
    if pending_reason:
        kill_class, _mechanical = _kill_class(pending_reason)
        if kill_class == "UNKNOWN":
            kill_class = "NOT_JUDGED"
        return "UNKNOWN", kill_class, pending_reason

    return _classify(failing, readable, succeeded), "UNKNOWN", ""


def _recover_command(number: int | None, branch: str, path: str) -> str:
    if number is None:
        return f"git -C {path} switch -c recover/{branch} origin/{branch}"
    return (
        f"git -C {path} fetch origin pull/{number}/head:recover/pr-{number} "
        f"&& git -C {path} switch recover/pr-{number}"
    )


def _count_class(audit: RepoAudit, classification: str) -> None:
    """Tally one closed-unmerged PR into exactly one coarse class."""
    if classification == "MECHANICAL":
        audit.mechanical += 1
    elif classification == "GENUINE":
        audit.genuine += 1
    elif classification == "CLOSED_BY_DECISION":
        audit.closed_by_decision += 1
    else:
        audit.unknown += 1


def _count_kill_class(audit: RepoAudit, kill_class: str, added_lines: int) -> None:
    """Tally one stranded item into its precise class, with the line weight it carries."""
    key = kill_class or "UNKNOWN"
    audit.kill_classes[key] = audit.kill_classes.get(key, 0) + 1
    audit.kill_class_lines[key] = audit.kill_class_lines.get(key, 0) + added_lines


def audit_repo(slug: str, path: str, limit: int = PR_LIMIT) -> RepoAudit:
    """Census one repo: what landed, what stranded, and how much of it is still recoverable."""
    audit = RepoAudit(slug=slug, path=path)
    if not os.path.isdir(os.path.join(path, ".git")) and not os.path.isdir(path):
        audit.blind.append(f"local checkout absent at {path}; skipped")
        return audit

    shallow = _shallow(path)
    if shallow:
        audit.blind.append(
            "this checkout is SHALLOW: reachability and survival cannot be answered from it. "
            "Every stranded row is UNMEASURED, never LOST. Fix: git fetch --unshallow"
        )

    prs, prs_ok, prs_err = _list_prs(slug, limit, path)
    if not prs_ok:
        audit.blind.append(
            f"could not list pull requests ({prs_err or 'gh failed'}); census BLIND"
        )
        return audit

    # ---- PHASE 1: classify the census itself (no git, no network) ----
    pending: list[dict] = []
    for pr in prs:
        audit.inspected += 1
        if pr.get("mergedAt"):
            audit.merged += 1
        elif pr.get("state") == "OPEN":
            audit.open_prs += 1
        else:
            audit.closed_unmerged += 1
            pending.append(pr)

    # ---- PHASE 2: ONE reachability answer for every commit we care about ----
    lane_rc, lane_out = _git(
        "for-each-ref",
        "--format=%(refname:short)%09%(objectname)",
        "refs/remotes/origin/lane/",
        cwd=path,
        timeout=30,
    )
    lane_rows: list[tuple[str, str]] = []
    if lane_rc == 0:
        for row in lane_out.splitlines():
            if "\t" in row:
                name, sha = row.split("\t", 1)
                lane_rows.append((name.strip(), sha.strip()))

    all_shas = [pr.get("headRefOid") or "" for pr in pending]
    all_shas += [sha for _name, sha in lane_rows]
    all_shas = [s for s in all_shas if s]
    in_main, reach_ok = (
        (set(), False) if shallow else _ancestor_set(all_shas, "origin/main", path)
    )
    if not reach_ok and not shallow:
        audit.blind.append(
            "origin/main unreadable: reachability unknown, so no row is called SUPERSEDED and "
            "survival is treated as BLIND"
        )

    # ---- PHASE 3: added lines, batched ----
    added_by_sha = _added_lines_many(sorted(set(all_shas)), path) if all_shas else {}

    # ---- PHASE 3b: rollups, only for rows where the answer decides, concurrently ----
    need = [
        int(pr["number"])
        for pr in pending
        if str(pr.get("headRefOid") or "") not in in_main
    ][:ROLLUP_SAMPLE]
    rollups = _rollups_for(slug, need, path)
    unread_rollups = 0

    items: list[Item] = []

    # ---- PHASE 3b: the recorded reason, for every stranded head, concurrently ----
    # The lane's own verdict is a LEGACY commit status on the head; the check runs are a
    # different API. The two are disjoint, so BOTH are read: a head can have 30 check runs and
    # no legacy status, or one legacy status and no check runs.
    statuses = _statuses_batch(
        slug,
        sorted(
            {
                s
                for s in (
                    [str(pr.get("headRefOid") or "") for pr in pending]
                    + [sha for _name, sha in lane_rows]
                )
                if s
            }
        ),
        path,
    )
    need = [
        int(pr["number"])
        for pr in pending
        if str(pr.get("headRefOid") or "") not in in_main
    ][:ROLLUP_SAMPLE]
    rollups = _rollups_for(slug, need, path)
    unread_rollups = 0
    unread_statuses = 0

    for pr in pending:
        number = pr.get("number")
        sha = pr.get("headRefOid") or ""
        subject = (pr.get("title") or "").strip()[:80]
        branch = pr.get("headRefName") or ""
        if sha and sha in in_main:
            audit.superseded += 1
            continue
        roll = rollups.get(int(number), Rollup())
        if int(number) not in rollups or not roll.readable:
            unread_rollups += 1
        status = statuses.get(sha, HeadStatus())
        if sha and not status.readable:
            unread_statuses += 1
        classification, kill_class, kill_reason = _classify_head(
            roll.failing, roll.readable, roll.succeeded, status
        )
        failing = list(roll.failing)
        if status.lane_reason() and LANE_VERDICT_CONTEXT not in failing:
            failing.append(LANE_VERDICT_CONTEXT)
        _count_class(audit, classification)
        items.append(
            Item(
                name=f"#{number}",
                sha=sha,
                subject=subject,
                branch=branch,
                pr=dict(pr, _failing=failing),
                added=added_by_sha.get(sha, []),
                classification=classification,
                kill_class=kill_class,
                kill_reason=kill_reason,
                failing_checks=failing,
            )
        )

    for name, sha in lane_rows:
        if sha in in_main:
            continue
        audit.unmerged_lanes += 1
        _rc, subj = _git("log", "-1", "--format=%s", sha, cwd=path)
        status = statuses.get(sha, HeadStatus())
        if not status.readable:
            unread_statuses += 1
        classification, kill_class, kill_reason = _classify_head(
            [], False, 0, status
        )
        _count_class(audit, classification)
        items.append(
            Item(
                name=name,
                sha=sha,
                subject=subj.strip()[:80],
                branch=name,
                added=added_by_sha.get(sha, []),
                classification=classification,
                kill_class=kill_class,
                kill_reason=kill_reason,
                failing_checks=[LANE_VERDICT_CONTEXT] if status.lane_reason() else [],
            )
        )

    # ---- PHASE 4: ONE answer about main survival, for every probe in the audit ----
    probes_by_sha: dict[str, list[str]] = {}
    for item in items:
        sample = list(dict.fromkeys(item.added))[:MAX_PROBES]
        if sample:
            probes_by_sha[item.sha] = sample

    survival_ok = not (shallow or not reach_ok)
    hits: dict[str, bool] = {}
    probe_budget_dropped = 0
    if survival_ok and probes_by_sha:
        paths_by_sha = _touched_files(list(probes_by_sha), path)
        if not paths_by_sha:
            survival_ok = False
            audit.blind.append(
                "could not read which files the stranded commits touched; their survival "
                "defaults to LOST"
            )
        else:
            total = sum(len(v) for v in probes_by_sha.values())
            probe_budget_dropped = max(0, total - MAX_TOTAL_PROBES)
            hits = _survival_in_paths(probes_by_sha, paths_by_sha, path)
            if not hits:
                survival_ok = False
                audit.blind.append(
                    "origin/main unreadable for survival (no blob could be read): stranded work "
                    "defaults to LOST"
                )

    for item in items:
        added = item.added
        if not added:
            audit.stranded.append(
                Stranded(
                    "pr" if item.pr is not None else "lane",
                    item.name,
                    item.sha,
                    item.subject,
                    verdict="MISSING-PARTIAL",
                    classification=item.classification or "UNKNOWN",
                    failing_checks=item.failing_checks,
                    kill_class=item.kill_class,
                    kill_reason=item.kill_reason,
                    closed_at=(item.pr or {}).get("closedAt") or "",
                    note=(
                        "head commit not fetchable offline; adds no measurable lines"
                        if item.pr is not None
                        else "lane commit adds no measurable lines"
                    ),
                )
            )
            _count_kill_class(audit, item.kill_class, 0)
            continue
        probes = list(dict.fromkeys(added))[:MAX_PROBES]
        found = sum(1 for probe in probes if hits.get(probe))
        surviving = (
            found
            if len(probes) >= len(added)
            else int(round(found * len(added) / len(probes)))
        )
        verdict = _verdict(len(added), surviving, False, shallow or not survival_ok)
        if verdict == "LOST":
            audit.lost_work_prs += 1
        if verdict == "UNMEASURED":
            audit.unmeasured += 1
        recover = (
            _recover_command(item.pr.get("number") if item.pr else None, item.branch, path)
            if verdict in ("LOST", "PARTIAL")
            else ""
        )
        audit.stranded.append(
            Stranded(
                "pr" if item.pr is not None else "lane",
                item.name,
                item.sha,
                item.subject,
                verdict=verdict,
                added_lines=len(added),
                surviving_lines=surviving,
                classification=item.classification or "UNKNOWN",
                failing_checks=item.failing_checks,
                kill_class=item.kill_class,
                kill_reason=item.kill_reason,
                closed_at=(item.pr or {}).get("closedAt") or "",
                recover_command=recover,
            )
        )
        _count_kill_class(audit, item.kill_class, len(added))

    absent = sum(1 for s in audit.stranded if s.verdict == "MISSING-PARTIAL")
    if absent:
        audit.blind.append(
            f"{absent} head commit(s) absent from this local checkout: reported MISSING-PARTIAL "
            "with the fetch command, not counted as lost and not fetched (read-only audit)"
        )
    if unread_rollups:
        audit.blind.append(
            f"{unread_rollups} closed PR(s) whose checks could not be read or were beyond the "
            f"sampled {ROLLUP_SAMPLE}: classified UNKNOWN, never MECHANICAL"
        )
    if probe_budget_dropped:
        audit.blind.append(
            f"survival sampling capped at {MAX_TOTAL_PROBES} probes: {probe_budget_dropped} "
            "probe(s) not consulted; verdicts use a proportional estimate"
        )
    return audit


def parse_repo_specs(argv: list[str]) -> list[tuple[str, str]]:
    """`slug=path` pairs, or bare slugs resolved from DEFAULT_REPOS."""
    specs: list[tuple[str, str]] = []
    for arg in argv:
        if arg.startswith("-"):
            continue
        if "=" in arg:
            slug, path = arg.split("=", 1)
            specs.append((slug.strip(), os.path.expanduser(path.strip())))
        else:
            default = DEFAULT_REPOS.get(arg)
            if default:
                specs.append((arg, os.path.expanduser(default)))
            else:
                specs.append((arg, ""))
    return specs


def render(audits: list[RepoAudit]) -> str:
    out: list[str] = []
    for a in audits:
        out.append(f"=== {a.slug} (last {a.inspected} PRs) ===")
        out.append(
            f"  inspected={a.inspected} merged={a.merged} open={a.open_prs} "
            f"closed_unmerged={a.closed_unmerged} superseded={a.superseded} "
            f"lost_work={a.lost_work_prs} unmerged_lanes={a.unmerged_lanes}"
        )
        out.append(
            f"  killed by MECHANICAL={a.mechanical} GENUINE={a.genuine} "
            f"CLOSED_BY_DECISION={a.closed_by_decision} UNKNOWN={a.unknown}"
            + (f" UNMEASURED={a.unmeasured}" if a.unmeasured else "")
        )
        if a.kill_classes:
            out.append("  why (items/lines):")
            for kill_class, count in sorted(
                a.kill_classes.items(), key=lambda kv: -a.kill_class_lines.get(kv[0], 0)
            ):
                out.append(
                    f"    {kill_class:<22} {count:>4} items  "
                    f"{a.kill_class_lines.get(kill_class, 0):>7} added lines"
                )
        for line in a.blind:
            out.append(f"  BLIND: {line}")
        ordered = sorted(
            a.stranded,
            key=lambda s: (
                {"LOST": 0, "PARTIAL": 1, "MISSING-PARTIAL": 2}.get(s.verdict, 3),
                -s.added_lines,
            ),
        )
        for s in ordered[:10]:
            ratio = f"{s.surviving_lines}/{s.added_lines}"
            out.append(
                f"  {s.verdict:<15} {s.name:<22} {ratio:>8}  {s.classification:<19} "
                f"{s.kill_class:<18} {s.subject[:36]}"
            )
        if len(ordered) > 10:
            out.append(
                f"  ... {len(ordered) - 10} more stranded items (see the manifest)"
            )
    out.append(f"\nfull manifest: {MANIFEST_PATH}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    limit = PR_LIMIT
    specs: list[str] = []
    for arg in argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        else:
            specs.append(arg)
    targets = parse_repo_specs(specs)
    if not targets:
        print("usage: forensics.py [--limit=N] slug[=path] ...", file=sys.stderr)
        return 2

    audits: list[RepoAudit] = []
    for slug, path in targets:
        if not path:
            audit = RepoAudit(slug=slug, path="")
            audit.blind.append(
                "no local checkout named and no default for this slug; skipped"
            )
            audits.append(audit)
            continue
        audits.append(audit_repo(slug, path, limit))

    print(render(audits))

    manifest = {
        "schema": SCHEMA,
        "manifest_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pr_limit": limit,
        "repos": [
            {
                **{k: v for k, v in asdict(a).items() if k != "stranded"},
                "stranded": [asdict(s) for s in a.stranded],
            }
            for a in audits
        ],
    }
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
