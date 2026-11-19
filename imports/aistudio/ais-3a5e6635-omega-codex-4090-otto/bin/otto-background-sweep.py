#!/usr/bin/env python3
"""
~/.estate/bin/otto-background-sweep.py (commit 5de5998)
Non-destructive 5-minute estate sweep across idp, argon, and argon-sync.
Never mutates a working tree it does not own. Writes rolling 288 receipts to ~/.estate/otto/sweep/.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RECEIPT_DIR = Path.home() / ".estate" / "otto" / "sweep"
MAX_RECEIPTS = 288
DISK_FLOOR_GIB = 5.00

REPOS = {
    "idp": Path.home() / "estate" / "idp",
    "argon": Path.home() / "estate" / "argon",
    "argon-sync": Path.home() / "estate" / "argon-sync",
}


def inspect_repo(name: str, repo_path: Path) -> dict:
    if not repo_path.exists():
        return {
            "name": name,
            "branch": f"MISSING ({name})",
            "dirty": 0,
            "worktrees": 0,
            "status": "MISSING",
        }
    branch_proc = subprocess.run(
        ["git", "-C", str(repo_path), "symbolic-ref", "--short", "-q", "HEAD"],
        capture_output=True,
        text=True,
    )
    branch = branch_proc.stdout.strip() or f"None ({name})"
    status_proc = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    dirty = len([line for line in status_proc.stdout.splitlines() if line.strip()])
    wt_proc = subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    worktrees = len(
        [line for line in wt_proc.stdout.splitlines() if line.startswith("worktree ")]
    )
    return {
        "name": name,
        "branch": branch,
        "dirty": dirty,
        "worktrees": max(1, worktrees),
        "status": "CLEAN" if dirty == 0 else "DRIFT",
    }


def check_disk_admit(path: Path) -> tuple[float, str]:
    target = path if path.exists() else Path.home()
    usage = shutil.disk_usage(str(target))
    free_gib = round(usage.free / (1024**3), 2)
    admit = "GRANTED" if free_gib >= DISK_FLOOR_GIB else "REFUSED"
    return free_gib, admit


def run_sweep(
    repos: dict[str, Path] = REPOS, receipt_dir: Path = RECEIPT_DIR
) -> tuple[int, dict]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    free_gib, admit = check_disk_admit(Path.home())
    results = [inspect_repo(name, path) for name, path in repos.items()]
    has_drift = any(r["status"] != "CLEAN" for r in results) or admit == "REFUSED"
    verdict = "DRIFT" if has_drift else "CLEAN"

    receipt = {
        "timestamp": now,
        "verdict": verdict,
        "diskFreeGiB": free_gib,
        "admit": admit,
        "repos": results,
    }
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = receipt_dir / f"sweep-{now.replace(':', '')}.json"
    receipt_file.write_text(json.dumps(receipt, indent=2))

    all_receipts = sorted(receipt_dir.glob("sweep-*.json"))
    for stale in all_receipts[:-MAX_RECEIPTS]:
        stale.unlink(missing_ok=True)

    print(f"OTTO SWEEP {now}  verdict={verdict}")
    for r in results:
        print(f"  {str(r['branch']):<32} dirty={r['dirty']:<5} worktrees={r['worktrees']}")
    print(f"  disk: {free_gib:.2f} GiB free, admit={admit}")
    return (1 if verdict == "DRIFT" else 0), receipt


if __name__ == "__main__":
    code, _ = run_sweep()
    sys.exit(code)
