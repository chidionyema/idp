"""The pre-push gate must grade the COMMIT being pushed, never the checkout it runs in.

Two distinct defects, one class -- a gate that answers a question about some other tree than the
one being pushed:

1. Every path-gated rung in `bin/idp-ci` built its range as `"$IDP_CI_BASE"...HEAD`, a literal
   `HEAD`, and `.githooks/pre-push` computed `base` from ambient `HEAD` too. On a shared checkout
   `HEAD` is whatever another agent has checked out.

2. The fast gate's ruff rung ran `ruff check --quiet .` -- the WORKING TREE, not any commit at
   all. It linted files another agent had half-written and refused a push whose own content was
   clean.

Both were measured on 2026-11-11 in ~/Documents/code/idp:

  pushing 8c8043522 (three files, all clean) was refused for
  `F821 Undefined name RECEIPT_DIR` in infra/macos/tools/otto/otto-background-sweep.py -- a file
  absent from that commit and clean in its committed bytes, dirty only in one working tree:

      PYTHON_STRICT_RANGE="<base>...HEAD"        bin/idp-python-strict -> rc=1, 4x F821
      PYTHON_STRICT_RANGE="<base>...8c8043522"   bin/idp-python-strict -> rc=0

  and pushing 4cbd00e59 (four files, no .py in the diff) was refused by the ruff rung for the same
  file; a minute later it was unstaged and the same rung passed -- a gate whose verdict depends on
  who else is typing is not a gate.

This test is a falsifier: it fails against main and passes against the fix. It was tightened twice
on its own evidence -- first against a help-text line that merely mentions `bin/idp-ci`, then to
stop demanding the contract from `hooks/pre-push`, which is an unrelated mutation-testing shim that
always exits 0.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOKS = [REPO / ".githooks" / "pre-push"]
IDP_CI = REPO / "bin" / "idp-ci"


def _read(path):
    assert path.exists(), f"{path} is missing"
    return path.read_text()


def test_the_hook_passes_the_head_it_grades_to_idp_ci():
    """The ref the hook was handed is the ref the gate must grade."""
    for hook in HOOKS:
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
        assert calls, f"{hook} does not invoke bin/idp-ci at all"
        for line in calls:
            assert "IDP_CI_HEAD=" in line, (
                f"{hook} invokes the gate without IDP_CI_HEAD, so every rung inside it falls\n"
                f"back to ambient HEAD -- the tree of whoever else is in this checkout:\n  {line}"
            )


def test_idp_ci_reads_and_honours_an_explicit_head():
    """`bin/idp-ci` must define the graded head once and export it for every rung."""
    src = _read(IDP_CI)
    assert "IDP_CI_HEAD" in src, (
        "bin/idp-ci never reads IDP_CI_HEAD: the hook can pass it and every rung will still ask\n"
        "about HEAD, which is the defect."
    )
    assert re.search(r"^\s*export\s+GRADED_HEAD\b", src, re.MULTILINE), (
        "GRADED_HEAD must be exported, or steps that shell out re-derive HEAD themselves."
    )


def test_the_py_strict_range_is_not_a_bare_head():
    """The specific rung measured failing: py-strict must grade the pushed commit."""
    src = _read(IDP_CI)
    bad = [
        ln
        for ln in src.splitlines()
        if "PYTHON_STRICT_RANGE" in ln and "...HEAD" in ln and "GRADED" not in ln
    ]
    assert not bad, "py-strict grades HEAD, not the pushed commit:\n  " + "\n  ".join(
        bad
    )


def test_the_ruff_rung_grades_a_commit_not_the_working_tree():
    """Defect 2: `ruff check --quiet .` lints the checkout, including other agents' half-written files."""
    src = _read(IDP_CI)
    # What makes a rung depend on the checkout is the DIRECTORY it is pointed at, not the flags it
    # passes. `cd "$_ruff_target"` is the extracted commit; `cd "$IDP"` is the live checkout. Judge
    # the target, so this test cannot be satisfied or defeated by the wording of a comment, and
    # cannot mistake the already-base'd (IDP_CI_BASE) or format rungs for the defect.
    offenders = [
        ln.strip()
        for ln in src.splitlines()
        if "check --quiet ." in ln
        and 'cd "$IDP"' in ln
        and not ln.lstrip().startswith("#")
    ]
    assert not offenders, (
        "the ruff rung lints the live checkout, so it depends on who else is typing in this "
        "tree; it must lint an extracted copy of the graded commit:\n  "
        + "\n  ".join(offenders)
    )


def test_the_graded_head_falls_back_to_head():
    """A direct `bin/idp-ci` run has no pushed ref, and must behave exactly as before."""
    src = _read(IDP_CI)
    m = re.search(r'^GRADED_HEAD="\$\{IDP_CI_HEAD:-HEAD\}"', src, re.MULTILINE)
    assert m, (
        'IDP_CI_HEAD must be read once with HEAD as its fallback (GRADED_HEAD="'
        '${IDP_CI_HEAD:-HEAD}"), so `bin/idp-ci` run by hand is unchanged.'
    )
