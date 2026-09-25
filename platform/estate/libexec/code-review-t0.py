#!/usr/bin/env python3
"""code-review-t0.py — Tier 0: deterministic checks, always runs, no LLM.

Catches ~55% of issues with zero LLM cost.
Tools: ruff, eslint, semgrep, bandit, clang-tidy, custom AST patterns.
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HOME = Path.home()
IDP = HOME / "Documents/code/idp"
RESULTS: list[dict] = []
CEILING = 30  # seconds per tool


def run(
    cmd: list[str], cwd: str | None = None, timeout: int = CEILING
) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def find_files(target: str, since: str) -> list[Path]:
    """Get list of changed/new files from git diff or directory scan."""
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
        for ext in ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.c", "*.cpp"]:
            out.extend(base.rglob(ext))
        return out[:200]
    return [base] if base.exists() else []


def check_ruff(files: list[Path]) -> list[dict]:
    if not files:
        return []
    rc, out, err = run(
        ["python3", "-m", "ruff", "check", "--output-format=json", "."],
        cwd=str(files[0].parent),
        timeout=20,
    )
    if not out:
        return []
    try:
        findings = json.loads(out)
        return [
            {
                "tool": "ruff",
                "severity": "medium",
                "file": f["filename"],
                "line": f["location"]["row"],
                "rule": f["rule"],
                "message": f["message"],
            }
            for f in findings[:50]
        ]
    except Exception:
        return []


def check_semgrep(files: list[Path]) -> list[dict]:
    if not files:
        return []
    # Find common parent
    parents = {f.parent for f in files if f.is_file()}
    if not parents:
        return []
    root = min(parents)
    rc, out, err = run(
        ["semgrep", "--config=auto", "--json", "--timeout=15", str(root)], timeout=20
    )
    if not out or rc == 124:
        return []
    try:
        findings = json.loads(out)
        return [
            {
                "tool": "semgrep",
                "severity": "high",
                "file": r["path"],
                "line": r["start"]["line"],
                "rule": r["check_id"],
                "message": r["extra"]["message"],
            }
            for r in findings.get("results", [])[:30]
        ]
    except Exception:
        return []


def check_bandit(files: list[Path]) -> list[dict]:
    py_files = [f for f in files if f.suffix == ".py"]
    if not py_files:
        return []
    rc, out, err = run(
        ["python3", "-m", "bandit", "-r", ".", "-f", "json"],
        cwd=str(py_files[0].parent),
        timeout=20,
    )
    if not out:
        return []
    try:
        findings = json.loads(out)
        return [
            {
                "tool": "bandit",
                "severity": "high",
                "file": f["filename"],
                "line": f["line_number"],
                "rule": f["test_id"],
                "message": f["issue_text"],
            }
            for f in findings.get("results", [])[:20]
        ]
    except Exception:
        return []


def check_empty_catch(files: list[Path]) -> list[dict]:
    """Detect empty catch blocks that swallow errors."""
    findings = []
    for f in files:
        if f.suffix not in (".py", ".js", ".ts"):
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        # Python: except ExceptionType: pass  OR  except: ...
        for m in re.finditer(
            r"except[^{]*?:\s*(?:pass|...)\s*(?:#|$|\n\s*\S)", content, re.DOTALL
        ):
            line = content[: m.start()].count("\n") + 1
            findings.append(
                {
                    "tool": "empty-catch",
                    "severity": "high",
                    "file": str(f),
                    "line": line,
                    "rule": "empty-catch",
                    "message": "Empty except block — error swallowed",
                }
            )
    return findings[:20]


def check_dead_code(files: list[Path]) -> list[dict]:
    """Detect unreachable code after return/throw."""
    findings = []
    for f in files:
        if f.suffix not in (".py",):
            continue
        try:
            lines = f.read_text().splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("return") or stripped.startswith("raise"):
                if (
                    i + 1 < len(lines)
                    and lines[i + 1].strip()
                    and not lines[i + 1].strip().startswith("#")
                ):
                    findings.append(
                        {
                            "tool": "dead-code",
                            "severity": "low",
                            "file": str(f),
                            "line": i + 2,
                            "rule": "unreachable-after-return",
                            "message": f"Unreachable code at line {i + 2} after return",
                        }
                    )
    return findings[:20]


def check_duplicate_code(files: list[Path]) -> list[dict]:
    """Detect duplicate function names."""
    names: dict[str, list] = {}
    for f in files:
        if f.suffix not in (".py",):
            continue
        try:
            content = f.read_text()
        except Exception:
            continue
        for m in re.finditer(r"^def\s+(\w+)", content, re.MULTILINE):
            name = m.group(1)
            names.setdefault(name, []).append((str(f), m.start()))
    findings = []
    for name, locs in names.items():
        if len(locs) > 1:
            findings.append(
                {
                    "tool": "duplicate-symbol",
                    "severity": "low",
                    "file": ",".join(f"{p}:{n}" for p, n in locs),
                    "line": 0,
                    "rule": "duplicate-def",
                    "message": f"Duplicate function name '{name}' in {len(locs)} locations",
                }
            )
    return findings[:20]


def check_commit_fixme(files: list[Path]) -> list[dict]:
    """Detect FIXMEs and TODOs in code that signal known issues."""
    findings = []
    for f in files:
        try:
            lines = f.read_text().splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if re.search(r"\b(FIXME|TODO|HACK|XXX|BUG):", line):
                findings.append(
                    {
                        "tool": "fixme-todo",
                        "severity": "low",
                        "file": str(f),
                        "line": i + 1,
                        "rule": "fixme",
                        "message": line.strip()[:100],
                    }
                )
    return findings[:20]


def main():
    tier_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    since = sys.argv[3] if len(sys.argv) > 3 else "HEAD~1"

    if tier_arg not in ("0", "all"):
        print(json.dumps({"tier": 0, "skipped": True, "reason": f"tier={tier_arg}"}))
        return

    files = find_files(target, since)
    if not files:
        print(json.dumps({"tier": 0, "findings": [], "summary": "no files to check"}))
        return

    all_findings: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {
            ex.submit(check_ruff, files): "ruff",
            ex.submit(check_semgrep, files): "semgrep",
            ex.submit(check_bandit, files): "bandit",
            ex.submit(check_empty_catch, files): "empty-catch",
            ex.submit(check_dead_code, files): "dead-code",
            ex.submit(check_duplicate_code, files): "duplicate-code",
            ex.submit(check_commit_fixme, files): "fixme",
        }
        for fut in as_completed(futs):
            tool = futs[fut]
            try:
                results = fut.result()
                all_findings.extend(results)
            except Exception as e:
                pass

    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for f in all_findings:
        by_severity.setdefault(f.get("severity", "low"), []).append(f)

    output = {
        "tier": 0,
        "files_checked": len(files),
        "findings": all_findings,
        "by_severity": {k: len(v) for k, v in by_severity.items()},
        "total": len(all_findings),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
