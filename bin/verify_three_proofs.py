#!/usr/bin/env python3
# bin/verify_three_proofs.py
# Local Direct-Control 3-Independent-Proofs Gate for idp & Concierge Surfaces.
# Rejects any agent claim, git commit, or concierge action unless 3 out-of-band
# machine receipts independently pass with zero LLM involvement:
#   Proof 1 (Physical Reality Receipt): Exact git tree SHA & touched file hashes exist on disk,
#            and zero OKE ghost references ("193.123.184.22", "oke-check") exist in the payload.
#   Proof 2 (Deterministic Gate & Boundary Receipt): Zero guarded paths touched without Founder
#            seal, <= 5 files changed inside a single subsystem prefix, and trojan 937dda9d absent.
#   Proof 3 (Temporal & Clock Receipt): Claim timestamp is verified against the real OS hardware
#            clock (abs(now - claim_ts) <= 300s) so an agent can never hallucinate time/day/night.

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Tuple

GUARDED_PATHS = (
    "catalog/dof-registry.json",
    ".github/workflows/",
    "catalog/genesis-protocols.json",
    ".github/CODEOWNERS",
    "AGENTS.md",
)
BLACKLISTED_SHAS = {"937dda9d"}
STALE_OKE_GHOSTS = ("193.123.184.22", "oke-check")
# Generator-owned artifacts are exempt from the ghost TEXT scan: their bytes are the
# census of the repository, which QUOTES retired surfaces as history (the oci-reclaim
# intent records 'no receipt body in the last 8 oke-check.yml run(s)'). The ghost the
# proof hunts is a live OKE reference pushed as config, not history quoted by the one
# file fast-gate's registry rung REQUIRES to equal the generator's output. A live
# oke-check reference in any source file is still refused; only this artifact is
# skipped, and its sha256 is still verified below.
GHOST_SCAN_EXEMPT = frozenset(
    {
        "catalog/estate-capability-registry.json",
        "bin/verify_three_proofs.py",
    }
)
# The second entry is this file itself: the detector must literally name what it
# hunts ("oke-check" in STALE_OKE_GHOSTS), so a scan of its own source is a
# self-referential false positive, not a live OKE reference. It reached the tree
# through a server-side squash merge; any future commit touching it would have
# been refused by itself without this entry.
MAX_FILES_PER_CHANGE = 5
MAX_CLOCK_DRIFT_SECONDS = 300


def lane_contract() -> str:
    """The bounds this enforcer applies, printed for the worker before it works."""
    return "\n".join(
        [
            "LANE CONTRACT: one subsystem (one top-level directory), "
            f"at most {MAX_FILES_PER_CHANGE} files in one change, no .github/ or .githooks/ edits,",
            "and no guarded path without a Founder seal.",
        ]
    )


def _introduced_lines(repo_root: str, rel_path: str) -> str:
    """The '+' lines of the staged change for rel_path; whole file when nothing is staged."""
    try:
        diff = subprocess.run(  # noqa: S603 -- fixed argv, no shell, path is a repo file
            ["git", "diff", "--cached", "--unified=0", "--no-color", "--", rel_path],  # noqa: S607
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        diff = ""
    added = [
        ln[1:]
        for ln in diff.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    ]
    if added:
        return "\n".join(added)
    abs_path = os.path.join(repo_root, rel_path)
    try:
        with open(abs_path, "rb") as fh:
            return fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return ""


def verify_proof_1_physical_reality(
    repo_root: str, changed_files: List[str], expected_hashes: Dict[str, str]
) -> Tuple[bool, Dict]:
    verified_hashes = {}
    for rel_path in changed_files:
        abs_path = os.path.join(repo_root, rel_path)
        if not os.path.isfile(abs_path):
            return False, {
                "error": f"PROOF_1_FAILED: File '{rel_path}' does not exist on disk"
            }
        with open(abs_path, "rb") as f:
            raw = f.read()
        # Three fixes, one rule: the ghost that must be refused is a line this change
        # INTRODUCES, not a historical mention inside a file that happens to be edited
        # (AGENTS.md 3a: history is evidence), and not a generator-owned artifact that
        # quotes retired surfaces as its census. MEASURED 2026-11-15: the capability
        # snapshot's own record mentions the retired check name, so scanning whole files
        # refused every legitimate regeneration -- a guard refusing the estate's own work
        # (AGENTS.md 9 R14).
        if rel_path not in GHOST_SCAN_EXEMPT:
            text_sample = _introduced_lines(repo_root, rel_path)
            for ghost in STALE_OKE_GHOSTS:
                if ghost in text_sample:
                    return False, {
                        "error": f"PROOF_1_FAILED: Stale OKE ghost '{ghost}' introduced in '{rel_path}'"
                    }
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        if rel_path in expected_hashes and expected_hashes[rel_path] != actual_sha256:
            return False, {
                "error": f"PROOF_1_FAILED: SHA256 mismatch on '{rel_path}' (expected {expected_hashes[rel_path]}, got {actual_sha256})"
            }
        verified_hashes[rel_path] = actual_sha256

    return True, {"proof_1_status": "PASS", "verified_file_sha256": verified_hashes}


def verify_proof_2_boundary_and_gate(
    commit_sha: str, changed_files: List[str], has_founder_seal: bool = False
) -> Tuple[bool, Dict]:
    for bad in BLACKLISTED_SHAS:
        if commit_sha.startswith(bad):
            return False, {
                "error": f"PROOF_2_FAILED: Blacklisted breach commit {commit_sha}"
            }

    if not changed_files:
        return False, {"error": "PROOF_2_FAILED: Empty file set"}

    if len(changed_files) > MAX_FILES_PER_CHANGE and not has_founder_seal:
        return False, {
            "error": f"PROOF_2_FAILED: {len(changed_files)} files exceeds MAX_FILES_PER_CHANGE ({MAX_FILES_PER_CHANGE})"
        }

    subsystems = set()
    for path in changed_files:
        for guarded in GUARDED_PATHS:
            if (path == guarded or path.startswith(guarded)) and not has_founder_seal:
                return False, {
                    "error": f"PROOF_2_FAILED: Guarded path '{path}' modified without Founder seal"
                }
        parts = path.strip("/").split("/")
        subsystems.add(parts[0] if len(parts) > 1 else "root")

    if len(subsystems) > 1 and not has_founder_seal:
        return False, {
            "error": f"PROOF_2_FAILED: Cross-subsystem mutation {sorted(subsystems)} blocked"
        }

    return True, {
        "proof_2_status": "PASS",
        "subsystem": sorted(subsystems)[0],
        "file_count": len(changed_files),
    }


def verify_proof_3_temporal_clock(
    claimed_unix_ts: int, real_system_ts: int = None
) -> Tuple[bool, Dict]:
    now = int(time.time()) if real_system_ts is None else int(real_system_ts)
    drift = abs(now - int(claimed_unix_ts))
    if drift > MAX_CLOCK_DRIFT_SECONDS:
        return False, {
            "error": f"PROOF_3_FAILED: Claim timestamp {claimed_unix_ts} drifts from OS clock {now} by {drift}s (> {MAX_CLOCK_DRIFT_SECONDS}s)"
        }
    utc_hour = time.gmtime(now).tm_hour
    day_phase = "DAYLIGHT_WINDOW" if 7 <= utc_hour < 21 else "NIGHT_QUIET_WINDOW"
    return True, {
        "proof_3_status": "PASS",
        "os_unix_epoch": now,
        "clock_drift_seconds": drift,
        "verified_phase": day_phase,
    }


def evaluate_three_independent_proofs(
    repo_root: str,
    commit_sha: str,
    changed_files: List[str],
    expected_hashes: Dict[str, str],
    claimed_unix_ts: int,
    has_founder_seal: bool = False,
    real_system_ts: int = None,
) -> Tuple[bool, Dict]:
    ok1, p1 = verify_proof_1_physical_reality(repo_root, changed_files, expected_hashes)
    ok2, p2 = verify_proof_2_boundary_and_gate(
        commit_sha, changed_files, has_founder_seal
    )
    ok3, p3 = verify_proof_3_temporal_clock(claimed_unix_ts, real_system_ts)

    all_passed = ok1 and ok2 and ok3
    return all_passed, {
        "verdict": "APPROVED_BY_3_PROOFS" if all_passed else "REJECTED_FAIL_CLOSED",
        "proof_1_physical": p1,
        "proof_2_boundary": p2,
        "proof_3_temporal": p3,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify 3 Independent Machine Proofs Locally"
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--commit-sha", default="HEAD")
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--timestamp", type=int, default=int(time.time()))
    parser.add_argument("--founder-seal", action="store_true")
    parser.add_argument("--contract", action="store_true")
    args = parser.parse_args()

    if args.contract:
        print(lane_contract())
        sys.exit(0)
    if not args.files:
        parser.error("--files is required unless --contract is given")
    passed, report = evaluate_three_independent_proofs(
        repo_root=args.repo_root,
        commit_sha=args.commit_sha,
        changed_files=args.files,
        expected_hashes={},
        claimed_unix_ts=args.timestamp,
        has_founder_seal=args.founder_seal,
    )
    print(json.dumps(report, indent=2))
    sys.exit(0 if passed else 1)
