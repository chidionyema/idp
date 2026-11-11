"""The pre-push fast gate must grade the commit being pushed, not ambient HEAD.

MEASURED 2026-11-11. Pushing `8c8043522` (a commit touching three files, all ruff-clean) from
the shared checkout `~/Documents/code/idp` was refused:

    FAIL  py-strict  diff base..HEAD; ruff check --select E9,F,B,S --fix; ruff format
    F821 Undefined name `RECEIPT_DIR`
       --> infra/macos/tools/otto/otto-background-sweep.py:225:9

That file is not in the pushed commit and its committed bytes are clean:

    git show 8c8043522:infra/.../otto-background-sweep.py  | ruff check --select E9,F,B,S -> pass
    ruff check --select E9,F,B,S infra/.../otto-background-sweep.py (working tree)  -> 4 errors

so the refusal came from another agent's UNCOMMITTED edit, not from the push. The same command,
same minute, both directions:

    PYTHON_STRICT_RANGE="<base>...HEAD"           bin/idp-python-strict  -> REFUSED
    PYTHON_STRICT_RANGE="<base>...8c8043522"      bin/idp-python-strict  -> pass

The hook already knows the right answer: it reads `local_sha` from the ref being pushed and
computes `base` from it (`_graded_head`). `bin/idp-ci` then throws that away, because it builds
the range as ``"${base_local}...HEAD"`` -- a literal `HEAD`, the shared checkout's checked-out
commit. CI grades the pushed commit; the hook graded a tree that was never pushed. A gate that
refuses your commit for code you did not write, in a tree you do not own, is not a stricter gate:
it is a stopped pipeline, and it stops every lane at once when the checkout is shared (§9 R3).

The contract: the head the gate grades is the head being pushed. `IDP_CI_HEAD` carries it from
the hook to `idp-ci`; `HEAD` remains the fallback so a bare `bin/idp-ci` behaves as before.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# The git hook is `.githooks/pre-push` (installed at .git/hooks/pre-push). `hooks/pre-push` is a
# DIFFERENT, unrelated file -- a mutation-testing PR shim that always exits 0 -- so it is not
# asserted on here; demanding the fast-gate contract from it would be a false requirement.
HOOKS = [REPO / ".githooks" / "pre-push"]
IDP_CI = REPO / "bin" / "idp-ci"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_the_hook_passes_the_head_it_grades_to_idp_ci() -> None:
    """The hook computes `base` from `local_sha`; it must hand that same head down.

    Asserted on the INVOCATION, not on the presence of a variable name: the defect was that
    `_graded_head` was computed and then not used, so a test that only greps for the name
    would have passed against the broken file.
    """
    for hook in HOOKS:
        if (
            not hook.exists()
        ):  # pragma: no cover - a sparse checkout may carry only one copy
            continue
        src = _read(hook)
        # The real invocation, not the help text further down (`2) re-run IDP_CI_FAST=1 bin/idp-ci`),
        # which mentions the same words but pushes nothing. A test that matched the help text would
        # fail a correct fix -- and did, on first run, before this was tightened.
        calls = [
            ln
            for ln in src.splitlines()
            if "bin/idp-ci" in ln
            and "IDP_CI_FAST=1" in ln
            and ln.lstrip().startswith(("if ", "if !"))
        ]
        assert calls, f"{hook}: no idp-ci invocation found"
        for line in calls:
            assert "IDP_CI_HEAD" in line, (
                f"{hook}: the fast gate is invoked without the head it graded, so idp-ci falls "
                f"back to ambient HEAD and grades a tree that is not being pushed: {line.strip()}"
            )


def test_idp_ci_grades_the_head_it_is_given() -> None:
    """`bin/idp-ci` must build the py-strict range from `IDP_CI_HEAD` when it is set."""
    src = _read(IDP_CI)
    assert "IDP_CI_HEAD" in src, (
        "bin/idp-ci never reads IDP_CI_HEAD, so the hook has no way to tell it which commit to "
        "grade and it grades the shared checkout's HEAD instead"
    )


def test_the_py_strict_range_is_not_a_bare_head() -> None:
    """The regression itself: a range literal `...HEAD` discards the pushed commit.

    `git diff a...HEAD` and `a...<sha>` are different questions. The gate must ask the second.
    """
    src = _read(IDP_CI)
    bad = [
        ln.strip()
        for ln in src.splitlines()
        if "PYTHON_STRICT_RANGE" in ln and re.search(r"\}\.\.\.HEAD", ln)
    ]
    assert not bad, (
        "the py-strict range is built from a literal HEAD, which grades whatever the shared "
        f"checkout has checked out rather than the commit being pushed: {bad}"
    )


def test_the_graded_head_falls_back_to_head() -> None:
    """A bare `bin/idp-ci` (no hook, no IDP_CI_HEAD) must still work, not grade an empty range."""
    src = _read(IDP_CI)
    # The head is defined once, near the top, and must read IDP_CI_HEAD with HEAD as its fallback.
    m = re.search(r'^GRADED_HEAD="\$\{IDP_CI_HEAD:-HEAD\}"', src, re.MULTILINE)
    assert m, (
        "IDP_CI_HEAD must be read once with HEAD as its fallback (GRADED_HEAD="
        '"${IDP_CI_HEAD:-HEAD}"), or a direct bin/idp-ci run grades nothing at all'
    )
