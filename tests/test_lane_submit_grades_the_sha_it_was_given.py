"""The lane door must grade the sha it was handed, not whatever is checked out.

The defect this pins (measured 2026-11-11): `estate_invoke lane-submit sha=b87e907f7
branch=lane/ca-bundle-and-focus-ttl` pushed correctly and then reported

    ok      lane-submit  lane/fix/doors-find-gh-off-path = 220ccf880 on origin

-- a different branch, a different commit, and nothing about the lane that was actually
submitted. The shared checkout was, at that moment, on `fix/doors-find-gh-off-path` because
another agent had switched it.

THE ROOT CAUSE IS NOT WHAT THE FIRST DRAFT OF THIS FILE SAID. Step 2 does read HEAD, but it
never received a sha to read: `sha` and `branch` were not DECLARED arguments of the intent, and
`resolve_args` carried any `k=v` into the arg dict without checking it against the declaration.
The keys matched no `{{slot}}` in any step and vanished. So the door answered accurately about
the only arguments it got, and the caller had no way to learn that two of its three had been
discarded.

That silent drop is the class, and it is estate-wide: any agent can pass any door an argument
it does not declare and be told `ok`. The tests below refuse it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INTENT = REPO_ROOT / "platform" / "estate" / "intents" / "lane-submit.yaml"

# The exact ambient form that caused the defect. Matched loosely on whitespace so a reformat
# cannot hide it, and anchored so `git rev-parse "$head"` (the fix) is never mistaken for it.
_AMBIENT_SHA = re.compile(r"""\bsha=\$\(\s*git\s+rev-parse\s+HEAD\s*\)""")


def _intent_text() -> str:
    assert INTENT.is_file(), f"the lane intent is missing at {INTENT}"
    return INTENT.read_text(encoding="utf-8")


def _push_step() -> str:
    """The step whose command hands the lane to the remote -- found by what it DOES.

    The push is not a literal `git push` in the shell: it is handed over through
    `os.execvp("git", ["git", "push", ...])` so the push outlives the step's ceiling (#5814).
    The first version of this test searched for the string `git push` and therefore found no
    step at all, which would have made the whole falsifier vacuous the moment the assertion
    changed from `assert push` to something looser. It matches the handover instead.
    """
    text = _intent_text()
    # Each step is indented under `steps:`; split on the step marker and keep the ones that push.
    chunks = re.split(r"\n(?=  - name: )", text)
    push = [c for c in chunks if "execvp" in c and "push" in c]
    assert push, (
        "no step in lane-submit.yaml hands the lane to the remote; the step was renamed or the "
        "push mechanism changed (it is an os.execvp handover, not a literal `git push`)"
    )
    return push[0]


def test_the_push_step_does_not_read_its_sha_from_head() -> None:
    """The falsifier's core: the ambient form must be gone from the pushing step."""
    step = _push_step()
    hit = _AMBIENT_SHA.search(step)
    assert hit is None, (
        "the push step still resolves its sha from the ambient checkout "
        "(`sha=$(git rev-parse HEAD)`). A caller that passes an explicit sha is then pushed and "
        "graded against whatever another agent has checked out -- measured on 2026-11-11, where "
        "the door reported lane/fix/doors-find-gh-off-path for a lane/ca-bundle-and-focus-ttl "
        "submission."
    )


def test_the_push_step_resolves_the_sha_it_was_given() -> None:
    """Positive half: the step must actually consume the `sha` argument."""
    step = _push_step()
    assert "{{sha}}" in step, (
        "the push step never reads the `sha` argument, so an explicit sha cannot influence it"
    )
    assert re.search(r"""\bsha=\$\(\s*git\s+rev-parse\s+"\$head"\s*\)""", step), (
        "the push step should resolve its sha from the `head` variable it built from {{sha}}"
    )


def test_a_given_sha_is_validated_before_it_is_used() -> None:
    """An unknown sha must be refused loudly, not silently graded as something else."""
    step = _push_step()
    assert "cat-file -e" in step and "BLIND" in step, (
        "a sha that is not a commit in this checkout must be refused with a BLIND line rather "
        "than falling back to the ambient checkout"
    )


def test_the_branch_fallback_is_never_empty() -> None:
    """`git rev-parse --abbrev-ref <sha>` answers EMPTY for a bare sha.

    Measured: it returns "" for origin/main's commit id, "HEAD" for HEAD, and "origin/main" for
    a ref name. A fix that read the branch from the sha would therefore have produced "lane/"
    whenever --lane was omitted -- trading one wrong lane name for another. This refuses that
    regression.
    """
    step = _push_step()
    assert 'lane="sha-$(git rev-parse --short' in step, (
        "the lane name must fall back to a name derived from the sha when no branch name is "
        "available, not to the empty string"
    )


def test_sha_and_branch_are_declared_arguments() -> None:
    """The caller must be able to constrain WHICH commit and branch the lane carries.

    Undeclared, `sha=` and `branch=` are accepted by `resolve_args` and then interpolated
    nowhere; declaring them is what makes them reach the push step at all.
    """
    text = _intent_text()
    block = re.search(r"\nargs:\n(.*?)\nsteps:", text, re.S)
    assert block, "lane-submit.yaml has no args block"
    for arg in ("sha", "branch"):
        assert re.search(rf"^  {arg}:", block.group(1), re.M), (
            f"`{arg}` is not declared as an argument, so a caller passing {arg}=... is silently "
            "ignored and the door grades whatever is checked out instead"
        )


def test_an_undeclared_argument_is_refused_not_dropped() -> None:
    """The class beyond this intent: any door must refuse an argument it does not declare.

    This reads the executor's own resolver, so the guarantee is tested where it lives rather
    than inferred from one intent's behaviour.
    """
    executor = Path.home() / ".estate" / "bin" / "estate-execute"
    if not executor.is_file():
        pytest.skip("the executor is not installed on this machine")
    src = executor.read_text(encoding="utf-8", errors="replace")
    body = src.split("def resolve_args(", 1)
    assert len(body) == 2, "resolve_args is gone from the executor; this gate is BLIND"
    fn = body[1].split("\n# ----", 1)[0]
    assert "unknown" in fn, (
        "resolve_args does not compute a set of undeclared arguments, so an argument a door "
        "does not declare is carried and silently dropped -- measured 2026-11-11, where "
        "lane-submit reported `ok` while ignoring the sha and branch it was handed"
    )
    assert "sys.exit(2)" in fn, (
        "resolve_args must REFUSE an undeclared argument (exit 2), not merely notice it"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
