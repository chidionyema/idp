"""2026-08-29: `IDP_CI_FAST=1 bin/idp-ci` read FAIL ruff on a branch that changed no Python.

    F821 Undefined name `cmd_install_plugin`  --> .wt-keyless/sovereign/cli.py:713:29
    F821 Undefined name `Any`                 --> .wt-p0/sovereign/cli.py:357:25
    F821 Undefined name `cmd_install_plugin`  --> .wt-stale/sovereign/cli.py:713:29

Every session in this estate works in a git worktree checked out at `.wt-<name>/` inside this
directory -- 33 were registered that morning. They were untracked and unignored, so every
root-level tool run walked into them, and one session's half-written file refused another
session's push with a red that graded neither branch. The gate is supposed to say whether THIS
tree is shippable; it was answering a question about somebody else's.

They stay graded where grading means something: on their own branch, by the pre-push hook and by
CI, which run on a clean checkout with no sibling worktree in it.
"""
import re
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]


def test_the_incident_a_sibling_worktree_is_not_part_of_this_tree():
    """git itself must not see .wt-<name>/ as untracked content of this checkout."""
    probe = IDP / ".wt-guardprobe" / "sovereign"
    probe.mkdir(parents=True, exist_ok=True)
    f = probe / "cli.py"
    f.write_text("def broken():\n    return undefined_name_that_does_not_exist\n")
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                             cwd=IDP, capture_output=True, text=True).stdout
        assert ".wt-guardprobe" not in out, (
            "a sibling worktree shows as untracked content of this checkout; `git add -A` here "
            f"would stage another session's work:\n{out}"
        )
        r = subprocess.run(["ruff", "check", "."], cwd=IDP, capture_output=True, text=True)
        assert ".wt-guardprobe" not in r.stdout + r.stderr, (
            "ruff walked into a sibling worktree; a peer's half-written file fails this branch's "
            f"gate:\n{r.stdout[-800:]}"
        )
    finally:
        f.unlink()
        probe.rmdir()
        probe.parent.rmdir()


def test_the_pattern_is_anchored_so_it_cannot_swallow_real_directories():
    """`.wt-*` unanchored would also ignore `platform/.wt-something`. Only the root is meant."""
    lines = [ln.strip() for ln in (IDP / ".gitignore").read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    hits = [ln for ln in lines if re.search(r"\.wt-", ln)]
    assert hits, ".gitignore no longer ignores the sibling worktrees; the incident is back"
    for ln in hits:
        assert ln.startswith("/"), f"{ln!r} is unanchored and would ignore .wt-* at any depth"


def test_a_tracked_python_file_is_still_graded():
    """The canary: the exclusion must not have switched ruff off for the repository itself."""
    r = subprocess.run(["ruff", "check", "--select", "F821", "--no-cache", "-"],
                       cwd=IDP, input="def f():\n    return nope\n",
                       capture_output=True, text=True)
    assert r.returncode != 0 and "F821" in r.stdout, (
        f"ruff no longer reports F821 at all; the gate has stopped grading:\n{r.stdout}{r.stderr}"
    )
