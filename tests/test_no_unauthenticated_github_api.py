"""No script calls the GitHub API without an authenticated client.

423 files estate-wide and 56 in this repo name api.github.com. An unauthenticated
call is metered at 60/hour for the whole machine, so the first agent to poll
spends the budget every other agent needs. Found 2026-11-19: a watcher took the
limit to 0/60 and every later read failed with a KeyError, not a refusal.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CALL = re.compile(r"curl |wget |fetch\(|urllib|httpx|requests\.get")
API = re.compile(r"api\.github\.com")
AUTH = re.compile(
    r"gh api|Authorization: [Bb]earer|GITHUB_TOKEN|github-app|gh auth token"
)


def offenders(root):
    files = subprocess.run(
        ["git", "ls-files", "bin", "platform", ".githooks"],
        cwd=root,
        capture_output=True,
        text=True,
    ).stdout.split()
    bad = []
    for rel in files:
        f = root / rel
        if not f.is_file() or f.stat().st_size > 400_000:
            continue
        body = f.read_text(errors="replace")
        if f.suffix in {".yaml", ".yml", ".json", ".md", ".txt"}:
            continue
        if API.search(body) and CALL.search(body) and not AUTH.search(body):
            bad.append(rel)
    return bad


def test_no_script_calls_the_api_unauthenticated():
    bad = offenders(REPO)
    assert not bad, "unauthenticated api.github.com in: " + ", ".join(bad)
