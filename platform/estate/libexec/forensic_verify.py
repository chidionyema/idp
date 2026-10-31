#!/usr/bin/env python3
"""forensic_verify.py - compare the forensic manifest with what is actually on disk, per file.

  python3 forensic_verify.py --forensic ~/claude-forensics/forensic-20261031            # report only
  python3 forensic_verify.py --forensic ... --plan                                      # the restore plan, writes nothing
  python3 forensic_verify.py --forensic ... --restore-missing --quarantine DIR          # recover into DIR, publish nothing
  python3 forensic_verify.py --forensic ... --restore-missing --quarantine DIR --in-place

Never overwrites or deletes anything: --restore-missing only writes paths that do not exist.
States: SAFE-COMMITTED | ON-DISK-UNCOMMITTED | ON-DISK-DIFFERS | MISSING-RESTORABLE | MISSING-PARTIAL | MISSING-UNRECOVERABLE

WHY IT LOOKS THE WAY IT DOES (2026-10-31). The first version asked git two questions per
file: `git ls-files --error-unmatch <name>` and `git status --porcelain -- <name>`. That is
two process spawns for each of 4137 manifest rows -- 8274 spawns -- and the verification of the
full corpus did not finish inside the executor's 100s ceiling (measured: SIGTERMed at 100s, no
output). The questions are per FILE but the answers are per REPO, so the questions are now
asked once per repository: one `git ls-files -z` and one `git status --porcelain -z -uno` per
repo root, and every row is answered from those two sets. Same verdicts, two orders of
magnitude fewer processes. Measured: 33.8s for 4137 files.

The hash is read in chunks and the files are hashed in parallel: a 4137-file manifest is mostly
small files, and one multi-gigabyte file must not be read into memory whole.

WHAT MAY BE RESTORED IN PLACE (2026-10-31, measured on the full corpus). The corrected
verification found 1750 recoverable-but-missing files. 1068 of them are in /private/tmp (the
temp filesystem the machine has already emptied), 123 are intents in the LIVE store
(~/.estate/intents) and more are in worktree directories the estate's own tooling manages.
Writing those back in place would publish stale intents into a surface every agent can call,
and would re-create volatile junk. So a restore in place is refused for those classes unless
the caller asks for them by name, and every restorable file can instead be copied into a
quarantine tree, where the content is recovered and inspectable without being live.

PUBLISHING IS OPT-IN, NOT THE DEFAULT (2026-10-31). The remaining in-place class is not
innocent either: of the 177 files the plan would have published, 69 are inside the LIVE idp
repository and 26 are one-shot scripts in ~/.estate/scripts. A transcript records what an agent
wrote at that moment; it does not record whether the founder or a later agent deleted the file
on purpose. So publishing a file back into a live tree can resurrect work that was deliberately
removed, as an untracked file nobody asked for. The default therefore recovers content into a
quarantine tree and publishes NOTHING. `--in-place` is the explicit, per-run opt-in to write
files back to their original paths (still never overwriting an existing path, and still
refused for the live/volatile/worktree classes unless those are asked for by name).
"""

import argparse
import collections
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

GIT_TIMEOUT = 20
CHUNK = 1 << 20

# Live estate surfaces: a file restored into one of these becomes callable by every agent.
LIVE_PREFIXES = tuple(
    os.path.join(os.path.expanduser("~"), ".estate", d)
    for d in ("intents", "bin", "libexec")
)


def git_out(args, cwd):
    """Run git in cwd. Returns (rc, stdout). A timeout or a missing git is rc=1, not a crash."""
    try:
        r = subprocess.run(  # noqa: S603 -- a fixed git argv, no user input
            ["git"] + args, capture_output=True, text=True, timeout=GIT_TIMEOUT, cwd=cwd
        )
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


class GitIndex:
    """One git call per repository, not two per file."""

    def __init__(self):
        self.root_of = {}  # dir -> repo root (None when the dir is not in a repo)
        self.tracked = {}  # repo root -> set of repo-relative tracked paths
        self.changed = {}  # repo root -> set of repo-relative paths git reports as changed

    def root_for(self, d):
        if d not in self.root_of:
            rc, out = git_out(["rev-parse", "--show-toplevel"], d)
            self.root_of[d] = out.strip() if rc == 0 and out.strip() else None
        return self.root_of[d]

    def load(self, root):
        if root in self.tracked:
            return
        rc, out = git_out(["ls-files", "-z"], root)
        self.tracked[root] = set(x for x in out.split("\0") if x) if rc == 0 else set()
        rc, out = git_out(["status", "--porcelain", "-z", "-uno"], root)
        changed = set()
        if rc == 0:
            for rec in out.split("\0"):
                if not rec:
                    continue
                # "XY PATH" (rename: "XY NEWPATH" then a second record with OLDPATH)
                changed.add(rec[3:] if len(rec) > 3 else rec)
        self.changed[root] = changed

    def state_of(self, path, dirname):
        """-> (tracked, dirty). Untracked or unversioned means dirty, as before."""
        root = self.root_for(dirname)
        if not root:
            return False, True
        self.load(root)
        try:
            rel = os.path.relpath(path, root)
        except ValueError:
            return False, True
        tracked = rel in self.tracked.get(root, set())
        dirty = rel in self.changed.get(root, set())
        return tracked, (dirty or not tracked)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def is_live(path):
    return any(path == p or path.startswith(p + os.sep) for p in LIVE_PREFIXES)


def restore_plan(path, location, args):
    """-> (target, reason). target is 'in-place', 'quarantine' or None."""
    if is_live(path) and not args.include_live:
        return None, "live estate surface (%s): quarantined, not published" % location
    if location == "VOLATILE-tmp" and not args.include_volatile:
        return None, "volatile temp: quarantined, not re-created"
    if location in ("estate-worktree", "idp-worktree") and not args.include_worktrees:
        return (
            None,
            "worktree directory is managed by the estate's tooling: quarantined",
        )
    if args.only_locations and location not in args.only_locations:
        return None, "not in the selected locations (%s)" % args.only_locations
    return "in-place", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forensic", required=True)
    ap.add_argument("--restore-missing", action="store_true")
    ap.add_argument(
        "--plan", action="store_true", help="report the restore plan and write nothing"
    )
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="publish recovered files back to their original paths "
        "(default: quarantine only, publish nothing)",
    )
    ap.add_argument(
        "--quarantine",
        default="",
        help="copy every restorable missing file into this directory",
    )
    ap.add_argument(
        "--include-live",
        action="store_true",
        help="allow restoring into ~/.estate/{intents,bin,libexec}",
    )
    ap.add_argument(
        "--include-volatile",
        action="store_true",
        help="allow restoring into /tmp and /private/tmp",
    )
    ap.add_argument(
        "--include-worktrees",
        action="store_true",
        help="allow restoring into estate/idp worktree directories",
    )
    ap.add_argument(
        "--only-locations",
        default="",
        help="comma-separated location classes to restore in place",
    )
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    a.only_locations = set(x.strip() for x in a.only_locations.split(",") if x.strip())
    if a.restore_missing and not a.quarantine and not a.in_place:
        sys.stderr.write(
            "--restore-missing needs a destination: --quarantine DIR (recover only) "
            "or --in-place (publish back to the original paths)\n"
        )
        return 2
    base = os.path.expanduser(a.forensic)
    rows = json.load(open(base + "/manifest.json"))

    # 1. answer git's questions once per repository
    index = GitIndex()
    for r in rows:
        d = os.path.dirname(r["path"])
        if d and d not in index.root_of:
            root = index.root_for(d)
            if root:
                index.load(root)

    # 2. hash what is on disk, in parallel, in chunks
    to_hash = [r["path"] for r in rows if r.get("sha256") and os.path.exists(r["path"])]
    digests = {}
    if to_hash:
        with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            # zip(strict=) is 3.10+ and the gate's python is 3.9: same length by construction.
            for p, h in zip(to_hash, ex.map(sha256_file, to_hash)):  # noqa: B905
                digests[p] = h

    out = []
    restored = 0
    quarantined = 0
    held = collections.Counter()
    plan = []
    for r in rows:
        p = r["path"]
        state = None
        note = ""
        restored_to = None
        hold_reason = ""
        if os.path.exists(p):
            same = None
            if r.get("sha256"):
                try:
                    same = digests.get(p) == r["sha256"]
                except Exception:
                    same = None
            else:
                same = False
            tracked, dirty = index.state_of(p, os.path.dirname(p))
            if tracked and not dirty:
                state = "SAFE-COMMITTED"
            elif same is False and r["recoverability"] in ("FULL", "PARTIAL"):
                state = "ON-DISK-DIFFERS"
                note = "disk differs from the agents' final content (edited after, or edits lost)"
            else:
                state = "ON-DISK-UNCOMMITTED"
        else:
            src = os.path.join(base, "recovered", p.lstrip("/"))
            if r["recoverability"] == "FULL" and os.path.exists(src):
                state = "MISSING-RESTORABLE"
            elif r["recoverability"] == "PARTIAL" and os.path.exists(src):
                state = "MISSING-PARTIAL"
                note = "some edits did not apply cleanly"
            else:
                state = "MISSING-UNRECOVERABLE"
                note = "edit-only in transcript; needs a base copy (checkpoint stash or git history)"
            if state in ("MISSING-RESTORABLE", "MISSING-PARTIAL"):
                target, hold_reason = restore_plan(p, r["location"], a)
                if target is None:
                    plan_target = "held"
                elif a.in_place:
                    plan_target = "publish"
                else:
                    plan_target = "quarantine"
                    hold_reason = (
                        "in-place publication was not requested: "
                        "content kept in the quarantine tree"
                    )
                if hold_reason:
                    held[hold_reason.split(":")[0].strip()] += 1
                plan.append((p, r["location"], plan_target, hold_reason))
                if a.quarantine and not a.plan:
                    dst = os.path.join(os.path.expanduser(a.quarantine), p.lstrip("/"))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if not os.path.exists(dst):
                        shutil.copyfile(src, dst)
                        quarantined += 1
                        restored_to = dst
                if a.restore_missing and not a.plan and plan_target == "publish":
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    if not os.path.exists(p):
                        shutil.copyfile(src, p)
                        restored += 1
                        restored_to = p
                        note += " RESTORED"
                    else:
                        hold_reason = "the path exists now: left alone"
        out.append(
            dict(
                path=p,
                stream=r["stream"],
                location=r["location"],
                state=state,
                note=note.strip(),
                restored_to=restored_to,
                held=hold_reason,
            )
        )

    c = collections.Counter(o["state"] for o in out)
    by = collections.defaultdict(collections.Counter)
    for o in out:
        by[o["stream"]][o["state"]] += 1
    lines = [
        "# On-disk verification",
        "",
        "restored in place this run: %d" % restored,
        "copied into quarantine this run: %d" % quarantined,
        "",
        "| state | files |",
        "|---|---|",
    ] + ["| %s | %d |" % kv for kv in c.most_common()]
    if plan:
        pc = collections.Counter((t, loc) for _, loc, t, _ in plan)
        lines += [
            "",
            "## Restore plan",
            "",
            "| target | location | files |",
            "|---|---|---|",
        ]
        for (t, loc), n in sorted(pc.items()):
            lines.append("| %s | %s | %d |" % (t, loc, n))
        if a.plan:
            lines += ["", "### Every file the plan covers", ""]
            for p, loc, t, reason in plan:
                lines.append("- %s  [%s]  %s  %s" % (t, loc, p, reason))
    if held:
        lines += ["", "## Held back from an in-place restore", ""]
        for k, v in held.most_common():
            lines.append("- %s: %d file(s)" % (k, v))
    lines += ["", "## By stream", ""]
    for s, cc in sorted(by.items()):
        lines.append(
            "- %s: %s" % (s, ", ".join("%s=%d" % kv for kv in cc.most_common()))
        )
    lines += ["", "## Needs attention (not safely committed)", ""]
    for o in out:
        if o["state"] != "SAFE-COMMITTED":
            lines.append("- %s  %s  %s" % (o["state"], o["path"], o["note"]))

    # The report is written last and atomically: a reader that sees verify.md sees a finished
    # verification, never a half-written one.
    tmp = base + "/verify.md.tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, base + "/verify.md")
    tmp = base + "/verify.json.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, base + "/verify.json")

    # The console gets the verdict and the tables. Two things stay in verify.md: the per-file
    # restore plan (1802 paths, 626 KB measured 2026-10-31) and the per-file needs-attention list
    # (thousands of paths). Both are matched by heading PREFIX -- lines.index() needs an exact
    # element, and the heading is "## Needs attention (not safely committed)", so an exact match
    # silently failed and the whole report was printed into the door's stdout.
    def _cut(prefix):
        for i, ln in enumerate(lines):
            if ln.startswith(prefix):
                return i
        return None

    head = lines
    for marker in ("### Every file the plan covers", "## Needs attention"):
        at = _cut(marker)
        if at is not None:
            head = head[:at]
            head.append("")
            head.append("the full per-file listing is in %s/verify.md" % base)
            break
    print("\n".join(head))


if __name__ == "__main__":
    sys.exit(main() or 0)
