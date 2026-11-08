#!/usr/bin/env python3
"""Falsifier for RC4: BLIND must be spelled BLIND, and a lane must be graded only on its own paths.

THE DEFECT, MEASURED (2026-11-08). Shipping a docs-and-scripts lane through `bin/idp-ci` produced
three FAILs and zero of them were caused by the change:

    FAIL  tsc       backstage
    FAIL  ruff-fmt  whole repo             (23 files, all pre-existing on origin/main)
    FAIL  fast-gate                        (derivative of the two above)

The tsc rung was red because `backstage/node_modules` was an empty directory -- the rung's own
helper printed `BLIND: no backstage/node_modules here ...; run yarn install` and exited 3, and the
caller had no branch for 3 outside GitHub Actions, so it fell through to `FAIL`. Worse, the scope
gate that should have skipped tsc entirely was itself disabled: `touched()` returned true for
EVERY path when `IDP_CI_BASE` was unset, which is exactly the bare invocation a developer and the
pre-push hook use. So the rung ran, could not answer, and called its inability an offence.

Two properties are asserted here:
  1. `touched()` resolves a base on its own instead of collapsing to "touched everything".
  2. exit 3 is reported as BLIND and does not set fail -- naming its fix rather than blaming the lane.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDP_CI = ROOT / "bin" / "idp-ci"


def _code_only(text: str, start_marker: str, end_marker: str) -> str:
    """The code between two markers, comments removed.

    Comments are stripped deliberately: the first ruff falsifier in this change passed 5/5 against
    a broken script because the property it searched for survived in a comment. Any test that
    asserts on a script must look at what the script DOES.
    """
    start = text.find(start_marker)
    assert start != -1, f"marker {start_marker!r} not found; this test would be blind"
    end = text.find(end_marker, start)
    section = text[start:end] if end != -1 else text[start:]
    return "\n".join(
        ln for ln in section.splitlines() if not ln.lstrip().startswith("#")
    )


def _touched_code() -> str:
    return _code_only(
        IDP_CI.read_text(encoding="utf-8", errors="replace"), "touched() {", "}\n"
    )


def test_touched_resolves_a_base_instead_of_matching_everything():
    """A bare invocation must scope, not grade the whole tree."""
    body = _touched_code()

    assert "merge-base" in body, (
        "touched() has no base derivation, so with IDP_CI_BASE unset it returns true for every "
        "path and every scoped rung runs in full on a bare run"
    )
    assert 'local base="${IDP_CI_BASE:-}"' in body, (
        "touched() does not read IDP_CI_BASE as the first choice, so an explicit base would be ignored"
    )
    assert '[ -n "${IDP_CI_BASE:-}" ] || return 0' not in body, (
        "touched() still returns true unconditionally when no base is exported -- the exact defect"
    )


def test_blind_is_reportable_and_not_an_offence():
    """exit 3 means 'cannot judge'; it must not be spelled FAIL."""
    text = IDP_CI.read_text(encoding="utf-8", errors="replace")
    start = text.find("if touched backstage/ bin/idp-backstage-tsc")
    assert start != -1, (
        "the tsc rung is gone; this test must fail rather than pass blind"
    )
    end = text.find("# 1d.3:", start)
    rung = text[start:end] if end != -1 else text[start : start + 2000]

    assert "rc = 3" in rung and "BLIND" in rung, (
        "the tsc rung has no BLIND branch: exit 3 (no node_modules) falls through to FAIL and "
        "blocks a change the rung has no opinion about"
    )
    blind_line = next(ln for ln in rung.splitlines() if "BLIND" in ln and "say" in ln)
    assert "yarn install" in blind_line, (
        "BLIND must name its fix, or the next author is told 'cannot judge' with no way forward"
    )
    assert "fail=1" not in blind_line, (
        "the BLIND branch sets fail=1, which is 'cannot judge' == 'rejected' and is the fail-open "
        "class inverted into a fail-closed wall"
    )


def test_a_lane_that_touches_backstage_is_still_held():
    """Scope must not become amnesty: touching backstage and failing tsc is still red."""
    text = IDP_CI.read_text(encoding="utf-8", errors="replace")
    start = text.find("if touched backstage/ bin/idp-backstage-tsc")
    end = text.find("# 1d.3:", start)
    rung = text[start:end] if end != -1 else text[start : start + 2000]

    assert 'else say "FAIL  tsc      backstage"; fail=1; fi' in rung, (
        "a real tsc failure (exit 1) must still set fail=1"
    )


def test_this_lane_does_not_touch_backstage():
    """The live measurement: this change contains no .ts/.tsx, so tsc has no opinion on it."""
    base = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["git", "merge-base", "HEAD", "origin/main"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not base:
        import pytest  # noqa: PLC0415

        pytest.skip("no origin/main in this checkout")

    changed = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["git", "diff", "--name-only", f"{base}...HEAD"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    ts = [p for p in changed.splitlines() if p.endswith((".ts", ".tsx"))]
    assert not ts, (
        "this lane touches TypeScript ("
        + ", ".join(ts)
        + "), so a BLIND tsc IS this lane's gap "
        "and the skip is not justified"
    )


def test_no_stale_skip_branch_remains():
    """The old GITHUB_ACTIONS-only skip is gone; BLIND is reported everywhere, uniformly."""
    text = IDP_CI.read_text(encoding="utf-8", errors="replace")
    start = text.find("if touched backstage/ bin/idp-backstage-tsc")
    end = text.find("# 1d.3:", start)
    rung = text[start:end] if end != -1 else text[start : start + 2000]

    assert not re.search(r"skip\s+tsc.*GITHUB_ACTIONS", rung), (
        "the rung still skips only inside Actions, so a laptop run reports FAIL where CI reports "
        "skip for the identical state"
    )
