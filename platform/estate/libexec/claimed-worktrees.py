#!/usr/bin/env python3
"""Print the git worktrees that a live claim covers, one per line: "<path>\t<reason>".

WHY. On 2026-10-24 the governed disk-cleanup intent (worktrees=true) removed a live agent's
worktree at ~/.estate/worktrees/deps-zod-mlflow while that agent was working in it. The checkout
is disposable (the branch and its commits live in the shared repository), so the cleaner judged it
settled and took it -- and the agent's working directory vanished under it, so every job it then
ran failed. The cleaner could not see the claim: a claim is a GitHub comment with a heartbeat, and
the cleaner only asks git.

So the estate's own focus register is the source of truth: platform/estate/memory/focus.py polls
the open issues and writes ~/.estate/memory/focus-register.json, whose rows carry the claim
(idp#7148), its agent and whether it is live (a heartbeat younger than two hours; AGENTS.md
section 5.4). A worktree is claimed when its branch's commits carry a `Claim: owner/repo#N`
trailer -- the trailer bin/claim-open stamps into the commit, so it names the claim the branch
belongs to -- and N is a live claim in the register.

WHAT IT DOES NOT DO. It reads only. It never touches a worktree, and it never decides to keep
one: it says which worktrees a live claim covers, and the cleaner keeps those and prints why.

    claimed-worktrees.py /path/to/repo [more repos...]
    CLAIM_REGISTER=... claimed-worktrees.py /path/to/repo   # a different register

Exit 0 always: a register that cannot be read means no worktree is claimed, and the caller
says so. It is a safety net, not a gate.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

CLAIM_TRAILER = re.compile(r"^Claim:\s+\S+#(\d+)\s*$", re.MULTILINE)
DEFAULT_REGISTER = os.path.join(
    os.path.expanduser("~"), ".estate", "memory", "focus-register.json"
)


def live_claims(path: str) -> dict:
    """The live claims in the register: claim number -> (agent, title)."""
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    out = {}
    for row in data.get("rows") or []:
        if not row.get("live"):
            continue
        claim = str(row.get("claim") or "")
        m = re.search(r"(\d+)$", claim)
        if not m:
            continue
        out[int(m.group(1))] = (row.get("agent") or "?", row.get("title") or claim)
    return out


def git(args: list, cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", cwd] + args,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def worktrees(repo: str) -> list:
    out = git(["worktree", "list", "--porcelain"], repo)
    return [
        line[len("worktree ") :]
        for line in out.splitlines()
        if line.startswith("worktree ")
    ]


def claims_in(commits: str) -> list:
    return [int(n) for n in CLAIM_TRAILER.findall(commits)]


def main(argv: list) -> int:
    register = os.environ.get("CLAIM_REGISTER", DEFAULT_REGISTER)
    live = live_claims(register)
    if not live:
        return 0
    for repo in argv:
        if not os.path.isdir(repo):
            continue
        for wt in worktrees(repo):
            if not os.path.isdir(wt):
                continue
            # The tip commits carry the trailer bin/claim-open stamps; the log is bounded so a
            # long history cannot turn this into a walk of the repository.
            commits = git(["log", "-n", "20", "--format=%B", "HEAD"], wt)
            for number in claims_in(commits):
                if number in live:
                    agent, title = live[number]
                    print(f"{wt}\tclaimed by {agent} on idp#{number} ({title})")
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
