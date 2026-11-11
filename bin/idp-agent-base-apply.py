#!/usr/bin/env python3
"""Apply a sealed cloud-agent patch at the exact commit it was made against.

Trusted submit-lane stage only. A busy main cannot discard a successful agent
execution: apply its patch at its own ancestor, then let the existing Greenlane
perform the independently checked rebase and landing. No force-push, no merge,
no model-authored self-attestation, no alternative queue or state database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_PATCH_BYTES = 4 * 1024 * 1024


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], capture_output=True, check=check)


def apply(base_file: Path, patch_file: Path) -> dict:
    base = base_file.read_text(encoding="ascii").strip()
    if not SHA.fullmatch(base):
        raise ValueError("BLIND: sealed agent base is not one 40-digit SHA")
    if not patch_file.is_file() or not 0 < patch_file.stat().st_size <= MAX_PATCH_BYTES:
        raise ValueError("BLIND: sealed patch missing, empty or over 4 MiB")
    if git("status", "--porcelain").stdout:
        raise ValueError("BLIND: trusted checkout is not clean")
    main = git("rev-parse", "origin/main").stdout.decode().strip()
    if git("cat-file", "-e", f"{base}^{{commit}}", check=False).returncode:
        raise ValueError("BLIND: agent base commit is not fetchable")
    if git("merge-base", "--is-ancestor", base, main, check=False).returncode:
        raise ValueError("BLIND: agent base does not belong to current main history")
    # The trusted checkout may be far ahead of the agent's source snapshot.
    # Reconstruct at the exact recorded base; do NOT edit the sealed patch
    # or try to make it apply by changing the expected outcome.
    git("checkout", "--detach", "--quiet", base)
    result = subprocess.run(
        ["git", "apply", "--index", "--3way", str(patch_file.resolve())],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise ValueError("BLIND: sealed patch does not apply to its declared base: "
                         + result.stderr.strip()[:240])
    paths = [
        p for p in git("diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD")
        .stdout.decode("utf-8", errors="strict").split("\0") if p
    ]
    if not paths:
        raise ValueError("BLIND: sealed patch produced zero staged changes")
    prohibited = [p for p in paths if p.startswith((".github/", ".githooks/"))]
    if prohibited:
        raise ValueError("REFUSED: untrusted agent patch modifies protected paths: "
                         + ", ".join(prohibited[:8]))
    staged = git("diff", "--cached", "--binary", "HEAD").stdout
    return {
        "decision": "STAGED_FOR_GREENLANE_NOT_LANDED",
        "agent_base": base,
        "trusted_main_at_submission": main,
        "changed_files": paths,
        "staged_sha256": hashlib.sha256(staged).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-file", type=Path, required=True)
    ap.add_argument("--patch", type=Path, required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(apply(args.base_file, args.patch), sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
