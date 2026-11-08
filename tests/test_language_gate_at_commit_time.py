#!/usr/bin/env python3
"""Falsifier for RC1: a cheap, deterministic gate must fire at commit time, not at push time.

THE DEFECT, MEASURED (2026-11-08). `bin/language-gate` costs 1.46 s and needs only two things that
exist before a commit is made: the commit message and the staged diff. It nonetheless ran only
inside `bin/idp-ci` at pre-push, so a new Python file without a `Language-Exception` trailer cost:

    commit  ->  push (56 s of gate)  ->  FAIL language  ->  amend  ->  push again

against a yamllint rung measured at 138 s over 1303 files, i.e. a 95x cost gap between the gate
being run early and being run late. A gate that can decide in 1.46 s next to the data it needs
should not be deferred to the most expensive point in the pipeline (AGENTS.md sec. 9 principle 2:
deterministic first, earliest moment, one script for every point).

This test holds that wiring in place. It asserts the hook calls the SAME script -- a second copy
would drift -- and that the call happens BEFORE the HMAC stamp, because a stamp on a message the
gate rejected is a signature asserting something untrue.

The end-to-end behaviour (a real `git commit` refused, the commit count unchanged) was proven by
hand in a scratch repo on 2026-11-08, twice: once refusing a .py with no trailer (1 -> 1 commits)
and once accepting the same file with the trailer (1 -> 2). That proof also caught a real defect in
the first implementation -- see test_commit_time_mode_judges_head_to_index_not_the_whole_branch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "commit-msg"
GATE = ROOT / "bin" / "language-gate"


def _hook_text() -> str:
    assert HOOK.exists(), (
        "the commit-msg hook is gone; nothing runs a gate at commit time"
    )
    return HOOK.read_text(encoding="utf-8", errors="replace")


def _gate_text() -> str:
    assert GATE.exists(), "bin/language-gate is missing"
    return GATE.read_text(encoding="utf-8", errors="replace")


def test_the_hook_runs_the_one_shared_gate():
    """One script at every point, so the early check and the late check cannot drift."""
    text = _hook_text()

    assert "bin/language-gate" in text, (
        "the hook does not call the repo's own bin/language-gate; a copied reimplementation would "
        "drift from the pre-push gate"
    )


def test_the_gate_runs_before_the_signature():
    """A rejected message must never be stamped: the HMAC would assert the gate passed."""
    text = _hook_text()
    # Anchor on where the stamp is WRITTEN, not on the word: the hook's own docstring explains the
    # stamp and appears at line 2, ahead of everything. Searching for the bare string found the
    # comment and reported the opposite of the truth -- the same defect as asserting on a script
    # without stripping comments.
    gate_at = text.find('bin/language-gate "$base_ref"')
    # The stamp lines are `printf 'X-Idp-Signed: %s\n' "$sig" >> "$msg_file"` -- single-quoted
    # format string. Anchoring on the exact form keeps line 2's docstring and line 32's reader
    # check (both mention the trailer) from being mistaken for the write.
    stamp_at = text.find("printf 'X-Idp-Signed:")
    assert gate_at != -1, "no executable language-gate call in the hook"
    assert stamp_at != -1, "the hook does not write an X-Idp-Signed trailer anywhere"
    assert gate_at < stamp_at, (
        "language-gate runs after the HMAC stamp, so a refused message is signed anyway"
    )


def test_the_gate_has_its_own_commit_time_mode():
    """commit-msg runs before the commit exists, so the mode must read the index, not a range."""
    text = _gate_text()

    assert "--message-file" in text, (
        "the gate has no --message-file mode for the commit-msg hook"
    )
    # The source builds the argv as a list, so the flag appears as a quoted string element; search
    # for what the code says, not for a shell-shaped rendering of it.
    assert '"--cached"' in text, (
        "the commit-time mode does not read the index; a base..HEAD range cannot see a commit that "
        "has not been created yet"
    )


def test_commit_time_mode_judges_head_to_index_not_the_whole_branch():
    """The measured defect: comparing the index against origin/main re-judged committed history.

    Observed in a scratch repo: a bash script was refused because a .py committed EARLIER on the
    same branch was still an 'addition' against origin/main. The pending commit is HEAD -> index.
    """
    text = _gate_text()
    start = text.find("def _staged_added_python_files")
    assert start != -1, "the commit-time helper is gone"
    body = text[start : text.find("\ndef ", start + 10)]

    assert '"HEAD"' in body, (
        "the commit-time diff is not taken against HEAD, so it re-reports files committed earlier "
        "on this branch and refuses unrelated commits"
    )
    assert "{base}" not in body, (
        "the commit-time diff still compares against a base sha, which re-lists committed files"
    )


def test_the_gate_is_still_wired_into_the_late_check_too():
    """Moving it earlier must not remove it from pre-push; a --no-verify commit still gets caught."""
    idp_ci = (ROOT / "bin" / "idp-ci").read_text(encoding="utf-8", errors="replace")
    assert "language-gate" in idp_ci, (
        "bin/idp-ci no longer runs language-gate, so a commit made with --no-verify is never judged"
    )


def test_commit_msg_hook_is_syntactically_valid():
    """A hook that does not parse silently disables the gate it was added to."""
    out = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["bash", "-n", str(HOOK)],  # noqa: S607
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, "commit-msg hook has a syntax error: " + out.stderr
