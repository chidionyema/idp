#!/usr/bin/env python3
"""code-review-t1.py — Tier 1: heuristic checks, runs when Tier 0 passes.

Flags suspects that need LLM judgment. Deterministic but noisy.
Produces findings with confidence flag, not verdicts.
"""

from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
IDP = HOME / "Documents/code/idp"


def find_files(target: str, since: str) -> list[Path]:
    base = Path(target) if target else IDP
    if (base / ".git").exists():
        try:
            r = subprocess.run(
                ["git", "diff", "--name-only", since or "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=str(base),
                timeout=10,
            )
            return [base / f for f in r.stdout.strip().splitlines() if f]
        except Exception:
            pass
    if base.is_dir():
        out = []
        for ext in ["*.py", "*.js", "*.ts", "*.go"]:
            out.extend(base.rglob(ext))
        return out[:200]
    return [base] if base.exists() else []


def check_inverted_condition(files: list[Path]) -> list[dict]:
    """Inverted condition: true-branch empty, false-branch has logic."""
    findings = []
    for f in files:
        if f.suffix != ".py":
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        # if not X: \n    ... \n else: \n    real_code
        for m in re.finditer(
            r"if\s+not\s+([^(]+?):\s*\n(\s*)(\S|\n)*?\n\s*\2else\s*:",
            content,
            re.DOTALL,
        ):
            findings.append(
                {
                    "tool": "inverted-condition",
                    "severity": "medium",
                    "confidence": "low",
                    "file": str(f),
                    "line": content[: m.start()].count("\n") + 1,
                    "rule": "inverted-if-not",
                    "message": "if-not with else branch — check if condition is inverted",
                }
            )
    return findings[:10]


def check_boundary_error(files: list[Path]) -> list[dict]:
    """Array index at boundary without explicit guard."""
    findings = []
    for f in files:
        if f.suffix != ".py":
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        # a[i+1] or a[i-1] without bounds check
        for m in re.finditer(r"\[([^\]]*[-+]\d+)\]", content):
            line = content[: m.start()].count("\n") + 1
            findings.append(
                {
                    "tool": "boundary-access",
                    "severity": "medium",
                    "confidence": "low",
                    "file": str(f),
                    "line": line,
                    "rule": "unchecked-array-bounds",
                    "message": f"Unchecked array access at boundary: {m.group(0)}",
                }
            )
    return findings[:10]


def check_error_swallow_partial(files: list[Path]) -> list[dict]:
    """Error caught but only logged, not propagated or assigned to structured result."""
    findings = []
    for f in files:
        if f.suffix not in (".py", ".js"):
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        for m in re.finditer(
            r"except[^{]+?:\s*\n\s*(?:log|print)\(", content, re.DOTALL
        ):
            line = content[: m.start()].count("\n") + 1
            findings.append(
                {
                    "tool": "error-swallow-partial",
                    "severity": "medium",
                    "confidence": "medium",
                    "file": str(f),
                    "line": line,
                    "rule": "error-log-only",
                    "message": "Error caught and logged but not propagated — verify this is intentional",
                }
            )
    return findings[:10]


def check_magic_numbers(files: list[Path]) -> list[dict]:
    """Magic numbers in security-sensitive contexts."""
    findings = []
    for f in files:
        if f.suffix not in (".py",):
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        # timeout=0, sleep=0, max_retries=0, chunk_size=0
        for m in re.finditer(
            r"(timeout|sleep|max_retries|chunk_size|retry|timeout_sec)\s*=\s*0\b",
            content,
        ):
            line = content[: m.start()].count("\n") + 1
            findings.append(
                {
                    "tool": "magic-zero",
                    "severity": "medium",
                    "confidence": "high",
                    "file": str(f),
                    "line": line,
                    "rule": "zero-value",
                    "message": f"Potentially dangerous zero value: {m.group(0)}",
                }
            )
    return findings[:10]


def check_secrets_in_code(files: list[Path]) -> list[dict]:
    """Hardcoded secrets, keys, tokens in source."""
    findings = []
    patterns = [
        (r"api[_-]?key\s*=\s*['\"][A-Za-z0-9+/]{20,}['\"]", "api-key", "high"),
        (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "password-hardcoded", "high"),
        (r"secret\s*=\s*['\"][A-Za-z0-9+/]{20,}['\"]", "secret-hardcoded", "high"),
        (r"bearer\s+[A-Za-z0-9+/]{20,}", "bearer-token", "high"),
        (
            r"-----BEGIN\s+(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            "private-key",
            "critical",
        ),
    ]
    for f in files:
        if f.suffix not in (".py", ".js", ".ts", ".yaml", ".json"):
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        for pattern, rule, severity in patterns:
            for m in re.finditer(pattern, content):
                line = content[: m.start()].count("\n") + 1
                findings.append(
                    {
                        "tool": "secret-detected",
                        "severity": severity,
                        "confidence": "high",
                        "file": str(f),
                        "line": line,
                        "rule": rule,
                        "message": f"Potential {rule} in source — verify and move to secrets manager",
                    }
                )
    return findings[:20]


def check_import_suspicious(files: list[Path]) -> list[dict]:
    """Suspicious imports: eval, exec, requests with no timeout."""
    findings = []
    for f in files:
        if f.suffix not in (".py",):
            continue
        try:
            lines = f.read_text().splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if re.search(r"\b(eval|exec|__import__)\s*\(", line):
                findings.append(
                    {
                        "tool": "dangerous-import",
                        "severity": "high",
                        "confidence": "high",
                        "file": str(f),
                        "line": i + 1,
                        "rule": "dynamic-code-exec",
                        "message": f"Dangerous dynamic code execution: {line.strip()}",
                    }
                )
            if (
                "requests." in line
                and "timeout" not in line
                and not line.strip().startswith("#")
            ):
                findings.append(
                    {
                        "tool": "requests-no-timeout",
                        "severity": "medium",
                        "confidence": "medium",
                        "file": str(f),
                        "line": i + 1,
                        "rule": "requests-no-timeout",
                        "message": "requests call without timeout — add timeout=N",
                    }
                )
    return findings[:20]


def main():
    tier_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    since = sys.argv[3] if len(sys.argv) > 3 else "HEAD~1"

    if tier_arg not in ("1", "all"):
        print(json.dumps({"tier": 1, "skipped": True, "reason": f"tier={tier_arg}"}))
        return

    files = find_files(target, since)
    if not files:
        print(json.dumps({"tier": 1, "findings": [], "summary": "no files to check"}))
        return

    all_findings = []
    for checker in [
        check_inverted_condition,
        check_boundary_error,
        check_error_swallow_partial,
        check_magic_numbers,
        check_secrets_in_code,
        check_import_suspicious,
    ]:
        try:
            all_findings.extend(checker(files))
        except Exception:
            pass

    output = {
        "tier": 1,
        "files_checked": len(files),
        "findings": all_findings,
        "by_confidence": {
            "high": len([f for f in all_findings if f.get("confidence") == "high"]),
            "medium": len([f for f in all_findings if f.get("confidence") == "medium"]),
            "low": len([f for f in all_findings if f.get("confidence") == "low"]),
        },
        "total": len(all_findings),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
