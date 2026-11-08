#!/usr/bin/env python3
"""Falsifier for RC3: a rung must grade what the lane changes, not main's own debt.

THE DEFECT, MEASURED (2026-11-08). `bin/idp-ci`'s ruff-fmt rung already had a diff-scoped path --
it grades `$IDP_CI_BASE...HEAD` -- but that path only ran when `IDP_CI_BASE` was exported by the
caller. Every other invocation (a developer running `bin/idp-ci` bare, a hook, a scheduled run)
fell through to `ruff format --check .` over the whole tree and was judged against the 23 files
that are already unformatted on `origin/main`, none of which the lane had touched:

    23 files would be reformatted   ->   FAIL   ->   push refused
    files authored by the lane among them: 0

That is the identical stopped pipeline the 2026-10-22 change removed, still reachable by the most
common path in the estate. A gate that fails for code you did not write is not a stricter gate.

This test holds the script to the rule, reading the script itself so the property cannot silently
regress: with no IDP_CI_BASE in the environment the rung must still derive a base.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDP_CI = ROOT / "bin" / "idp-ci"


def _ruff_section() -> str:
    """The ruff-fmt rung's CODE, with comment lines removed.

    Verified by mutation on 2026-11-08: the first version of this helper returned the section
    INCLUDING its comment block, so deleting the base derivation from the code left `merge-base`
    in a comment and the test still passed 5/5 against the broken script. A property test that a
    comment can satisfy is not a property test -- it is a spelling check. Strip the comments first,
    then assert; otherwise this file repeats the very defect it exists to prevent.
    """
    text = IDP_CI.read_text(encoding="utf-8", errors="replace")
    start = text.find("# 1d.3: ruff format --check")
    assert start != -1, "the ruff-fmt rung is gone; this test is blind and must fail"
    end = text.find("# 1d.4:", start)
    assert end != -1, "the ruff-fmt rung has no end marker"
    section = text[start:end]
    return "\n".join(
        line for line in section.splitlines() if not line.lstrip().startswith("#")
    )


def test_ruff_fmt_derives_a_base_when_none_is_exported():
    """The bare invocation -- what a founder runs -- must not grade the whole tree."""
    section = _ruff_section()

    assert "merge-base" in section, (
        "the ruff-fmt rung has no derivation for the base, so a bare bin/idp-ci grades the whole "
        "repo and fails on debt the lane never wrote"
    )
    assert "_ruff_base" in section, (
        "the derived base is not carried into the diff command"
    )


def test_ruff_fmt_diff_scopes_against_the_derived_base():
    """The diff must be taken against the derived base, not against a possibly-empty variable."""
    section = _ruff_section()

    assert 'diff --name-only --diff-filter=d "$_ruff_base...HEAD"' in section, (
        "the ruff-fmt diff does not use the derived base"
    )
    assert '"$IDP_CI_BASE...HEAD"' not in section, (
        "the rung still diffs against a raw IDP_CI_BASE, which is empty when not exported"
    )


def test_the_whole_repo_sweep_is_the_last_resort_not_the_default():
    """Whole-repo grading survives only for a checkout with no origin/main to diff against."""
    section = _ruff_section()
    whole = section.find("format --check --quiet .")
    assert whole != -1, (
        "the whole-repo sweep was deleted; a base-less checkout would go ungraded"
    )

    derive = section.find("merge-base")
    assert derive != -1 and derive < whole, (
        "the whole-repo sweep must come after the base derivation, or it fires first and the "
        "specific diagnosis can never run"
    )
    assert '[ -n "$_ruff_base" ]' in section, (
        "there is no guard deciding between the diff and the sweep"
    )


def test_only_this_lane_is_graded_here():
    """The property the defect violated: the only .py this lane touches is already formatted.

    This is the live measurement, not a fixture: it asks git and ruff the same question the rung
    asks, for this working tree.
    """

    def git(*a: str) -> str:
        return subprocess.run(  # noqa: S603 -- fixed argv, no shell
            ["git", *a],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()

    base = git("merge-base", "HEAD", "origin/main")
    if not base:
        import pytest  # noqa: PLC0415

        pytest.skip(
            "no origin/main in this checkout, so there is no lane diff to grade"
        )

    touched = [
        p
        for p in git(
            "diff", "--name-only", "--diff-filter=d", f"{base}...HEAD", "--", "*.py"
        ).splitlines()
        if p
    ]
    if not touched:
        return  # a docs-only lane: nothing to format, so nothing can be blamed on it

    out = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["ruff", "format", "--check", *touched],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert "Would reformat" not in out.stdout, (
        "this lane introduces unformatted Python: " + out.stdout.strip()
    )


def test_the_rung_mentions_the_measurement_it_was_fixed_from():
    """A fix without its measurement is folklore; the next editor deletes it.

    This one reads the raw section on purpose: it asserts the COMMENT that carries the
    measurement, so it must not be run against the comment-stripped text.
    """
    text = IDP_CI.read_text(encoding="utf-8", errors="replace")
    start = text.find("# 1d.3: ruff format --check")
    end = text.find("# 1d.4:", start)
    assert re.search(r"MEASURED 2026-11-08", text[start:end]), (
        "the rung no longer carries the measurement that justified deriving the base"
    )
