"""A declared argument that a step reads as a shell variable is never substituted.

2026-11-23: the ci.run intent wrote ``BRANCH="${branch}"``. The executor's interpolate()
renders ``{{var}}`` and ``<<var>>`` and nothing else, so ``${branch}`` reached the shell as a
reference to an unset shell variable. BRANCH was empty, ``git push origin ""`` failed, and
``gh run list --branch ""`` filters on nothing at all -- measured on chidionyema/gemini-sync,
``--branch ""`` returns every run in the repository and ``--branch does-not-exist`` returns
none -- so the lookup handed back the newest queued run of ANY branch and the intent watched
it and reported its verdict as this branch's.

The intent's own unit test was green the whole time, because ``bash -n`` cannot tell an unset
shell variable from a substituted one: the rendered step was valid shell either way. So the
rule is mechanical and has to be checked separately: a step that mentions a DECLARED argument
as a shell variable must also substitute it (``{{arg}}`` or ``<<arg>>``) in the same step.

This is the falsifier for idp#8463: it must fail on the intent that shipped and pass on the
fixed one, and it must be able to fail at all -- the second test proves that.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

INTENTS = sorted(
    (Path(__file__).resolve().parents[1] / "platform/estate/intents").glob("*.yaml")
)


def shell_refs(cmd: str, name: str) -> list[str]:
    """Every place the step reads `name` as a shell variable."""
    return re.findall(
        r"\$\{" + re.escape(name) + r"\}|\$" + re.escape(name) + r"(?![A-Za-z0-9_])",
        cmd,
    )


def substitutes(cmd: str, name: str) -> bool:
    """Does the step substitute the argument the way the executor substitutes it?"""
    return ("{{" + name + "}}") in cmd or ("<<" + name + ">>") in cmd


def violations(intent: dict) -> list[str]:
    """The steps that read a declared argument as a shell variable without substituting it."""
    args = list((intent.get("args") or {}).keys())
    out: list[str] = []
    for step in intent.get("steps") or []:
        cmd = step.get("cmd") or ""
        for name in args:
            if substitutes(cmd, name):
                continue
            hits = shell_refs(cmd, name)
            if hits:
                out.append(
                    "step %s: %s is read as a shell variable (%s) and never substituted"
                    % (step.get("name") or "-", name, ", ".join(sorted(set(hits))))
                )
    return out


@pytest.mark.parametrize("path", INTENTS, ids=lambda p: p.stem)
def test_no_intent_step_reads_a_declared_argument_as_a_shell_variable(path):
    intent = yaml.safe_load(path.read_text())
    bad = violations(intent)
    assert not bad, f"{path.name}: " + "; ".join(bad)


def test_the_falsifier_rejects_the_intent_that_shipped():
    """A check that cannot fail is not a check: this is the shape of idp#8463's ci.run.yaml."""
    broken = {
        "args": {"branch": {"type": "string"}},
        "steps": [
            {"cmd": 'BRANCH="${branch}"; git push origin "$BRANCH" 2>&1 | tail -3'}
        ],
    }
    assert violations(broken), "the falsifier did not catch the defect it exists for"


def test_the_falsifier_accepts_a_substituted_argument():
    good = {
        "args": {"branch": {"type": "string"}},
        "steps": [
            {"cmd": 'BRANCH="{{branch}}"; git push origin "$BRANCH" 2>&1 | tail -3'}
        ],
    }
    assert not violations(good), (
        "the falsifier refused a correctly substituted argument"
    )


def test_a_step_that_does_not_mention_the_argument_at_all_is_not_a_violation():
    """Only a declared argument is in scope; a shell variable of the step's own is free."""
    intent = {
        "args": {"branch": {"type": "string"}},
        "steps": [{"cmd": 'BRANCH="x"; git push origin "$BRANCH" 2>&1 | tail -3'}],
    }
    assert not violations(intent)
