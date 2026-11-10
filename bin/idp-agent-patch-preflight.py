#!/usr/bin/env python3
"""Trusted staged-patch preflight before a cloud agent claims or commits.

Mirrors the existing .githooks/pre-push added-line ASCII invariant earlier.
Only deterministic punctuation in NEW docs/evidence/*.md is repairable.
Never rewrite code, configuration, modified evidence, non-UTF8, or code fences.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PUNCTUATION = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "--",
    "\u2026": "...",
    "\u2192": "->",
    "\u2190": "<-",
    "\u00a0": " ",
    "\u2022": "*",
    "\u00b7": "*",
    "\u2713": "[PASS]",
    "\u2714": "[PASS]",
    "\u2717": "[FAIL]",
    "\u2718": "[FAIL]",
}


def git(*args: str, check: bool = True):
    return subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def staged_paths() -> list[tuple[str, str]]:
    raw = git(
        "diff", "--cached", "--name-status", "-z", "--no-renames", "--diff-filter=ACMR"
    ).stdout
    parts = raw.split(b"\0")
    if parts[-1] != b"":
        raise ValueError("incomplete NUL-delimited staged paths")
    result = []
    for i in range(0, len(parts) - 1, 2):
        if i + 1 >= len(parts) - 1:
            raise ValueError("incomplete staged path tuple")
        status, path = parts[i].decode("ascii"), os.fsdecode(parts[i + 1])
        if status not in ("A", "M", "C") or not path or "\0" in path:
            raise ValueError("unexpected staged path/status")
        result.append((status, path))
    return result


def added_non_ascii(path: str) -> bool:
    patch = git(
        "diff", "--cached", "--no-ext-diff", "--no-color", "--unified=0", "--", path
    ).stdout
    in_hunk = False
    for line in patch.splitlines():
        if line.startswith(b"@@ "):
            in_hunk = True
        elif line.startswith(b"diff --git "):
            in_hunk = False
        elif in_hunk and line.startswith(b"+") and any(b > 127 for b in line[1:]):
            return True
    return False


def deterministic_doc_repair(status: str, path: str):
    if (
        status != "A"
        or not path.startswith("docs/evidence/")
        or not path.endswith(".md")
    ):
        return None
    stage = git("ls-files", "--stage", "-z", "--", path).stdout
    if not stage.startswith((b"100644 ", b"100755 ")):
        return None
    if git("diff", "--quiet", "--", path, check=False).returncode != 0:
        return None
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        return None
    before = git("show", ":" + path).stdout
    if before != target.read_bytes():
        return None
    try:
        text = before.decode("utf-8")
    except UnicodeError:
        return None
    repaired = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith((chr(96) * 3, "~" * 3)):
            in_fence = not in_fence
        if in_fence or line.startswith(("    ", "\t")):
            if not line.isascii():
                return None
            repaired.append(line)
            continue
        for old, new in PUNCTUATION.items():
            line = line.replace(old, new)
        if not line.isascii():
            return None
        repaired.append(line)
    output = "".join(repaired).encode("ascii")
    if output == before:
        return None
    target.write_bytes(output)
    git("add", "--", path)
    if added_non_ascii(path):
        raise ValueError("repair failed original push invariant")
    return {
        "path": path,
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(output).hexdigest(),
        "scope": "NEW_DOCS_EVIDENCE_PROSE_PUNCTUATION_ONLY",
    }


def preflight(
    *,
    repair_docs: bool = False,
    allow_governance_paths: bool = False,
    allow_empty: bool = False,
) -> dict:
    paths = staged_paths()
    if not paths:
        return {
            "ok": allow_empty,
            "reason": "EMPTY_COMMIT_ALLOWED" if allow_empty else "EMPTY_PATCH",
            "repairs": [],
            "failed_paths": [],
            "authority": "PREFLIGHT_ONLY",
        }
    repairs = []
    failed = []
    for status, path in paths:
        if path.startswith((".github/", ".githooks/")) and not allow_governance_paths:
            failed.append({"path": path, "class": "PROTECTED_PATH"})
            continue
        if added_non_ascii(path):
            repair = deterministic_doc_repair(status, path) if repair_docs else None
            if repair is not None:
                repairs.append(repair)
            else:
                failed.append({"path": path, "class": "ADDED_NON_ASCII"})
    check = git("diff", "--cached", "--check", check=False)
    if check.returncode != 0:
        failed.append({"path": "<index>", "class": "GIT_DIFF_CHECK"})
    return {
        "ok": not failed,
        "reason": "PASS" if not failed else "STAGED_PATCH_REFUSED",
        "repairs": repairs,
        "failed_paths": failed,
        "staged_files": len(paths),
        "authority": "PREFLIGHT_ONLY",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-evidence-docs", action="store_true")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="general precommit only: keep existing empty-commit behavior",
    )
    parser.add_argument(
        "--allow-governance-paths",
        action="store_true",
        help="precommit-only: protected authorization still enforced by external gates",
    )
    args = parser.parse_args()
    try:
        report = preflight(
            repair_docs=args.repair_evidence_docs,
            allow_governance_paths=args.allow_governance_paths,
            allow_empty=args.allow_empty,
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        report = {
            "ok": False,
            "reason": "UNKNOWN_PREFLIGHT_ERROR",
            "detail": type(error).__name__,
            "authority": "PREFLIGHT_ONLY",
        }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
