#!/usr/bin/env python3
"""Lint estate intents: every intent must be generic, not a session fossil.

Rules (a violation is a PR number, literal SHA, run id, or /Users/ path baked
into an intent's name, description, or command -- the shape of the ~85 session
one-offs deleted from this directory in 2026-10-19's cleanup):
  1. file must parse as YAML; `name:` must equal the filename stem
  2. PR reference: `#NNNN` (N>=3 digits) outside a comment line
  3. literal git SHA: 7-40 hex chars containing at least one a-f letter
     (pure digits like 20260924 are dates, not SHAs), outside a comment line
  4. literal run id: `gh run view|rerun <6+ digits>`, outside a comment line
  5. hardcoded home path: `/Users/<name>/` in a command line

Modes:
  lint-intents.py           lint only what the working change ADDS vs HEAD
                            (git diff --diff-filter=A + untracked yaml);
                            violations are fatal, exit 1
  lint-intents.py --all     lint every yaml; report only, exit 0
  lint-intents.py --all --strict   --all with fatal violations

Comment lines (stripped `# ...`) are exempt: dated history notes like
"2026-10-08, PR #5511" are provenance, not parameterisation defects.
"""

import re
import sys
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml required")

REPO = Path(__file__).resolve().parent
# PR rule ignores ticket refs like crew#694 / idp#985: a '#' preceded by a word
# character is a tracker prefix, not a PR reference.
PR_REF = re.compile(r"(?<![\w])#\d{3,5}\b")
HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
RUN_ID = re.compile(r"gh run (?:view|rerun) \d{6,}")
USERS_PATH = re.compile(r"/Users/[A-Za-z0-9_.-]+/")


def is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def has_letter_sha(text: str) -> bool:
    for m in HEX.finditer(text):
        if re.search(r"[a-f]", m.group(0)):
            return True
    return False


def violations(path: Path):
    out = []
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        return [f"unparseable YAML: {e}"]
    if not isinstance(doc, dict) or "name" not in doc:
        return ["missing name:"]
    if doc["name"] != path.stem:
        out.append(f"name {doc['name']!r} != filename stem {path.stem!r}")
    if PR_REF.search(str(doc.get("name", ""))):
        out.append("PR number in intent name")
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if is_comment(line):
            continue
        bad = []
        if PR_REF.search(line):
            bad.append("PR number")
        if has_letter_sha(line):
            bad.append("literal SHA")
        if RUN_ID.search(line):
            bad.append("literal run id")
        if USERS_PATH.search(line):
            bad.append("/Users/ path")
        if bad:
            out.append(f"line {i}: {', '.join(bad)}: {line.strip()[:90]}")
    return out


def added_files() -> list[Path]:
    cmd = ["git", "diff", "--name-only", "--diff-filter=A", "HEAD"]
    names = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO).stdout.split()
    names = [n for n in names if not n.startswith("pending/")]
    untracked = [
        n
        for n in subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "*.yaml"],
            capture_output=True,
            text=True,
            cwd=REPO,
        ).stdout.split()
        if n.endswith(".yaml") and not n.startswith("pending/")
    ]
    return [REPO / n for n in names + untracked if n.endswith(".yaml")]


def all_files() -> list[Path]:
    return sorted(p for p in REPO.glob("*.yaml"))


def main() -> int:
    argv = sys.argv[1:]
    do_all = "--all" in argv
    strict = "--strict" in argv
    files = all_files() if do_all else added_files()
    fatal = 0
    for f in files:
        v = violations(f)
        if v:
            scope = "" if do_all else " (NEW — fatal)"
            print(f"FAIL {f.name}{scope}")
            for x in v:
                print(f"     {x}")
            if not do_all or strict:
                fatal += 1
    mode = f"--all{' --strict' if strict else ''}" if do_all else "added-files"
    print(f"{mode}: {len(files)} file(s) checked, {fatal} fatal")
    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
