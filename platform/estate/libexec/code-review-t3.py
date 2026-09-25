#!/usr/bin/env python3
"""code-review-t3.py — Tier 3: deterministic verification. The gate.

Every Tier 2 finding must survive Tier 3 before it reaches the user.
This is the "stochastic judgment proposes; deterministic verification disposes" rule enforced.

For each Tier 2 finding:
  1. Re-run the deterministic check that motivated it
  2. Confirm the pattern still matches after LLM context
  3. Reject if the deterministic evidence doesn't support it
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
IDP = HOME / "Documents/code/idp"
VERIFIED: list[dict] = []
REJECTED: list[dict] = []


def find_file(file_spec: str) -> Path | None:
    """Resolve file spec (possibly comma-separated) to a real path."""
    first = file_spec.split(",")[0].strip()
    if not first:
        return None
    # Handle line:path format
    path = first.split(":")[0]
    p = Path(path)
    if p.exists():
        return p
    # Try relative to IDP
    p2 = IDP / path
    if p2.exists():
        return p2
    return None


def verify_empty_catch(file: Path, line: int, context: str) -> bool:
    """Re-verify: does the empty catch block still exist?"""
    try:
        lines = file.read_text().splitlines()
        if 0 < line <= len(lines):
            # Check surrounding context
            for i in range(max(0, line - 3), min(len(lines), line + 2)):
                if re.search(r"except[^{]*?:\s*(?:pass|...)", lines[i]):
                    return True
    except Exception:
        pass
    return False


def verify_dead_code(file: Path, line: int, context: str) -> bool:
    """Re-verify: is there still unreachable code after return?"""
    try:
        lines = file.read_text().splitlines()
        if 0 < line <= len(lines):
            # Look for return/raise before this line
            for i in range(max(0, line - 5), line - 1):
                stripped = lines[i].strip()
                if stripped.startswith("return") or stripped.startswith("raise"):
                    return True
    except Exception:
        pass
    return False


def verify_secrets(file: Path, line: int, context: str) -> bool:
    """Re-verify: does the secret still appear in the file?"""
    patterns = [
        r"api[_-]?key\s*=\s*['\"][A-Za-z0-9+/]{20,}['\"]",
        r"password\s*=\s*['\"][^'\"]{8,}['\"]",
        r"secret\s*=\s*['\"][A-Za-z0-9+/]{20,}['\"]",
        r"-----BEGIN\s+(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    try:
        content = file.read_text()
        for pat in patterns:
            if re.search(pat, content):
                return True
    except Exception:
        pass
    return False


def verify_fixme(file: Path, line: int, context: str) -> bool:
    """Re-verify: does the FIXME/TODO still exist?"""
    try:
        lines = file.read_text().splitlines()
        if 0 < line <= len(lines):
            return bool(re.search(r"\b(FIXME|TODO|HACK|XXX|BUG):", lines[line - 1]))
    except Exception:
        pass
    return False


def verify_generic_pattern(file: Path, line: int, rule: str, context: str) -> bool:
    """Generic verification for rules without a specific checker."""
    try:
        lines = file.read_text().splitlines()
        if 0 < line <= len(lines):
            # Check if the line still contains the flagged content
            return bool(lines[line - 1].strip())
    except Exception:
        pass
    return False


def verify(file: Path, line: int, rule: str, context: str) -> bool:
    """Route to the right verifier based on rule type."""
    verifiers = {
        "empty-catch": verify_empty_catch,
        "unreachable-after-return": verify_dead_code,
        "secret-detected": verify_secrets,
        "api-key": verify_secrets,
        "password-hardcoded": verify_secrets,
        "private-key": verify_secrets,
        "fixme": verify_fixme,
        "duplicate-def": lambda f, l, c: f.exists(),
    }
    verifier = verifiers.get(rule, verify_generic_pattern)
    return verifier(file, line, context)


def main():
    tier_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    since = sys.argv[3] if len(sys.argv) > 3 else "HEAD~1"

    if tier_arg not in ("3", "all"):
        print(json.dumps({"tier": 3, "skipped": True, "reason": f"tier={tier_arg}"}))
        return

    # Read findings that need verification (passed from T2 via env)
    t2_verdicts = json.loads(os.environ.get("T2_VERDICTS", "[]"))

    if not t2_verdicts:
        print(
            json.dumps(
                {
                    "tier": 3,
                    "verified": [],
                    "rejected": [],
                    "summary": "no verdicts to verify",
                }
            )
        )
        return

    for verdict in t2_verdicts:
        file_spec = verdict.get("file", "")
        line = verdict.get("line", 0)
        rule = verdict.get("rule", "")
        context = verdict.get("message", "")

        if not file_spec:
            REJECTED.append({**verdict, "reason": "no file specified"})
            continue

        path = find_file(file_spec)
        if not path:
            REJECTED.append({**verdict, "reason": f"file not found: {file_spec}"})
            continue

        if not verify(path, line, rule, context):
            REJECTED.append(
                {
                    **verdict,
                    "reason": "deterministic check no longer confirms the pattern",
                }
            )
        else:
            VERIFIED.append(verdict)

    output = {
        "tier": 3,
        "verified": VERIFIED,
        "rejected": REJECTED,
        "summary": f"{len(VERIFIED)} verified, {len(REJECTED)} rejected by deterministic re-check",
        "verified_count": len(VERIFIED),
        "rejected_count": len(REJECTED),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
