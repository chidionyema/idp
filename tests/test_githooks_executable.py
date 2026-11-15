"""Every tracked git hook is executable, or git skips it without a word.

2026-11-14: .githooks/pre-push was committed as 100644, so idp's pre-push gate never ran for any agent,
and pushes that its rungs refuse reached CI and the founder. Same class as argon DEF-20261114-HOOKMODE-001.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = {
    "pre-commit",
    "pre-push",
    "commit-msg",
    "pre-merge-commit",
    "prepare-commit-msg",
    "post-checkout",
}


def test_every_tracked_hook_is_executable():
    out = subprocess.run(
        ["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    rows = [line.split(None, 3) for line in out.splitlines()]
    hooks = [
        (mode, path)
        for mode, _sha, _stage, path in rows
        if Path(path).name in HOOKS and Path(path).parent.name in (".githooks", "hooks")
    ]
    assert hooks, "the repository tracks hooks"
    assert [p for m, p in hooks if m not in ("100755", "120000")] == [], (
        "a hook git would silently skip"
    )
