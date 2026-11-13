#!/usr/bin/env python3
"""otto-background-sweep: what is drifting, measured, without touching the estate.

The founder's first pillar is autonomous sweeping, and the fastest way to fail it is a
background loop that "self-heals" a working tree it does not own. So v1 is telemetry with
teeth on the reading, not on the repo: it reports unpushed commits, dirty trees, stale
worktrees and disk admission, writes a receipt, and exits non-zero when something needs a
human or a mission. Repairs stay behind a mission and a gate.

    python3 bin/otto-background-sweep.py --once        # one pass, human summary
    python3 bin/otto-background-sweep.py --once --json # machine receipt on stdout
    python3 bin/otto-background-sweep.py --once --dry-run   # no receipt written

Exit: 0 nothing to report, 1 findings, 2 a check could not run (BLIND is never a pass).
"""

from __future__ import annotations

import argparse
import sys
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HOME = Path.home()
DEFAULT_REPOS = [
    HOME / "Documents/code/idp",
    HOME / "Documents/code/argon",
    HOME / "Documents/code/argon-sync",
]
# The disk guardian family (bin/idp-disk-watch, bin/idp-disk-guard, disk-cleanup.sh and the
# disk-sentinel tree) was DELETED by founder order on 2026-11-11. The sentinel path is kept as a
# constant only so the .exists() guard below stays false; nothing is restored from it.
DISK_SENTINEL = HOME / ".local/share/disk-sentinel/sentinel.sh"
# Restored: an edit that removed the disk-sentinel line also took this one with it, leaving
# lines 225-231 using an undefined name -- the sweep would have crashed at its write step.
RECEIPT_DIR = Path(os.environ.get("OTTO_SWEEP_DIR", HOME / ".estate/otto/sweep"))

# The yield gate's core. A sweep that dies mid-collect must not be able to claim it
# yielded, so every sweep is recorded as an instruction with one step per stage and the
# receipt is only written once the gate accepts the yield. Absent core = a sweep with
# no attestation, which is reported BLIND rather than silently trusted.
CORE = Path(
    os.environ.get(
        "OTTO_CORE",
        Path(__file__).resolve().parents[4] / "argon" / "bin" / "otto_real_core.py",
    )
)
CORE_DB = Path(os.environ.get("OTTO_CORE_DB", HOME / ".estate/otto-core.db"))


def run(argv: list[str], cwd: Path | None = None, timeout: int = 10) -> tuple[int, str]:
    try:
        p = subprocess.run(  # noqa: S603 - fixed argv, never a shell string
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, (p.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 124, f"{type(e).__name__}: {e}"


def repo_state(path: Path) -> dict[str, Any]:
    if not (path / ".git").exists():
        return {"path": str(path), "present": False}
    rc, branch = run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"])
    _, dirty = run(["git", "-C", str(path), "status", "--porcelain"])
    rc_up, up = run(
        [
            "git",
            "-C",
            str(path),
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
        ]
    )
    ahead = behind = None
    if rc_up == 0 and up:
        rc, counts = run(
            [
                "git",
                "-C",
                str(path),
                "rev-list",
                "--left-right",
                "--count",
                f"@{up}...HEAD",
            ]
        )
        if rc == 0 and counts:
            parts = counts.split()
            if len(parts) == 2:
                behind, ahead = int(parts[0]), int(parts[1])
    _, worktrees = run(["git", "-C", str(path), "worktree", "list", "--porcelain"])
    wt = sum(1 for line in worktrees.splitlines() if line.startswith("worktree "))
    return {
        "path": str(path),
        "present": True,
        "branch": branch if rc == 0 else None,
        "upstream": up or None,
        "dirty_files": len([x for x in dirty.splitlines() if x.strip()]),
        "ahead": ahead,
        "behind": behind,
        "worktrees": wt,
    }


def disk_state() -> dict[str, Any]:
    state: dict[str, Any] = {"admit": None, "free_gib": None}
    rc, out = run(["/bin/df", "-k", str(HOME)], timeout=10)
    if rc == 0:
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4 and parts[3].isdigit():
                state["free_gib"] = round(int(parts[3]) / 1048576, 2)
                break
    if DISK_SENTINEL.exists():
        rc, out = run([str(DISK_SENTINEL), "admit"], timeout=20)
        state["admit"] = "ADMIT" if rc == 0 else "REFUSED"
        state["admit_line"] = out
    return state


def collect(repos: list[Path], skip_disk: bool = False) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    states = []
    for r in repos:
        st = repo_state(r)
        states.append(st)
        if not st["present"]:
            findings.append(
                {
                    "id": "repo-missing",
                    "where": str(r),
                    "why": "declared repository is not on disk",
                }
            )
            continue
        if st["dirty_files"]:
            findings.append(
                {
                    "id": "dirty-tree",
                    "where": str(r),
                    "why": f"{st['dirty_files']} changed path(s)",
                }
            )
        if st["ahead"]:
            findings.append(
                {
                    "id": "unpushed",
                    "where": str(r),
                    "why": f"{st['ahead']} commit(s) not on {st['upstream']}",
                }
            )
        if st["behind"]:
            findings.append(
                {
                    "id": "behind",
                    "where": str(r),
                    "why": f"{st['behind']} commit(s) behind {st['upstream']}",
                }
            )
        if st["worktrees"] and st["worktrees"] > 3:
            findings.append(
                {
                    "id": "worktree-sprawl",
                    "where": str(r),
                    "why": f"{st['worktrees']} worktrees",
                }
            )
    disk = {"admit": "SKIPPED", "free_gib": None} if skip_disk else disk_state()
    if disk["admit"] == "REFUSED":
        findings.append(
            {
                "id": "disk-refused",
                "where": "disk-sentinel",
                "why": disk.get("admit_line", "").splitlines()[0][:160],
            }
        )
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repos": states,
        "disk": disk,
        "findings": findings,
        "verdict": "CLEAN" if not findings else "DRIFT",
    }


def record_yield(receipt: dict[str, Any], dry_run: bool = False) -> tuple[bool, str]:
    """Record this sweep in the yield gate and report whether it may yield.

    Returns (admitted, line). A sweep whose collect() completed records one 'ok' step
    and asks the gate to flip it to 'yielded'; the gate refuses if any step is not ok.
    No core, no key or no database is BLIND -- not a pass (AGENTS.md section 9, R1).
    """
    if not CORE.is_file():
        return False, f"BLIND: yield gate core not found at {CORE}"
    if dry_run:
        return False, "dry-run: not recorded"

    env = dict(os.environ)
    env["OTTO_CORE_DB"] = str(CORE_DB)
    if not env.get("OTTO_CORE_ATTEST_KEY"):
        return False, "BLIND: OTTO_CORE_ATTEST_KEY is not set, so no step can be attested"

    run_id = time.strftime("sweep-%Y%m%dT%H%M%S")
    verdict = receipt.get("verdict", "UNKNOWN")
    argv = [
        sys.executable, str(CORE), "run",
        "--run-id", run_id,
        "--instruction", f"otto background sweep ({verdict})",
        "--step-name", "collect",
        "--status", "ok",
        "--yield",
    ]
    try:
        import subprocess

        out = subprocess.run(
            argv, capture_output=True, text=True, timeout=30, env=env, check=False
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, f"BLIND: gate call failed ({exc.__class__.__name__})"

    blob = (out.stdout + out.stderr).strip()
    if out.returncode != 0:
        tail = [ln for ln in blob.splitlines() if "yield" in ln.lower()]
        return False, tail[-1] if tail else blob.splitlines()[-1] if blob else "no output"
    yielded = [ln for ln in blob.splitlines() if ln.startswith("yielded:")]
    return True, yielded[-1] if yielded else "yielded"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Bounded estate sweep: report drift, repair nothing."
    )
    ap.add_argument(
        "--once", action="store_true", help="one pass and exit (the only mode in v1)"
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="print the receipt JSON instead of the summary",
    )
    ap.add_argument("--dry-run", action="store_true", help="do not write a receipt")
    ap.add_argument(
        "--repo", action="append", default=[], help="repository to sweep (repeatable)"
    )
    ap.add_argument(
        "--skip-disk",
        action="store_true",
        help="ignore the disk admission check (tests, CI)",
    )
    args = ap.parse_args(argv)

    repos = [Path(p).expanduser() for p in args.repo] if args.repo else DEFAULT_REPOS
    receipt = collect(repos, skip_disk=args.skip_disk)

    # The yield gate decides whether this sweep may report a receipt at all.
    admitted, gate_line = record_yield(receipt, dry_run=args.dry_run)
    receipt["yield_gate"] = {"admitted": admitted, "line": gate_line}

    # Printed after admission so the JSON carries the gate's verdict, not a race with it.
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print(f"OTTO SWEEP {receipt['generated_at']}  verdict={receipt['verdict']}")
        for st in receipt["repos"]:
            if not st["present"]:
                print(f"  MISSING   {st['path']}")
                continue
            print(
                f"  {str(st['branch']):<32} dirty={st['dirty_files']:<3} ahead={st['ahead']} behind={st['behind']} worktrees={st['worktrees']}"
            )
        print(
            f"  disk: {receipt['disk']['free_gib']} GiB free, admit={receipt['disk']['admit']}"
        )
        for f in receipt["findings"]:
            print(f"  FINDING {f['id']:<16} {f['where']}: {f['why']}")
        print(f"  yield gate: {'ADMITTED' if admitted else 'REFUSED'} -- {gate_line}")

    if not args.dry_run:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        (RECEIPT_DIR / f"sweep-{stamp}.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
        if admitted:
            (RECEIPT_DIR / "latest.json").write_text(
                json.dumps(receipt, indent=2) + "\n"
            )
        else:
            # latest.json keeps the last ADMITTED sweep: an unattested run must never
            # overwrite the last attested one, or a reader cannot tell them apart.
            print(f"YIELD GATE REFUSED: {gate_line}")
            print("  latest.json left untouched; this receipt is not promoted")
        for old in sorted(RECEIPT_DIR.glob("sweep-*.json"))[:-288]:
            old.unlink(missing_ok=True)

    if not admitted:
        return 1
    return 0 if receipt["verdict"] == "CLEAN" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
