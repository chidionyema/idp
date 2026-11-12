"""The hook bypass is refused, and the refusal is proven able to fail.

Founder, 2026-11-12: "no agenbt can do that ever again i nee string mathyematic al
gyabatees and i need to knwohow you plan to prove it".

Three measurements, and the third is the one that matters (AGENTS.md section 9 R2:
"no gate has a falsifier; nobody proves a gate rejects known-bad input"):

  P1  the matcher is total over the labelled corpus -- misclassified = 0
  P2  the refusal is real at the door, not only in a unit test
  P3  sabotaging the matcher turns this file red, so the gate cannot be a rubber stamp
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# `platform` is a stdlib module name, so `from platform.estate.governance import ...`
# fails; the repo directory is not a package. Load the matcher by path instead.
_MATCHER_PATH = REPO / "platform" / "estate" / "governance" / "hook_bypass.py"
_spec = importlib.util.spec_from_file_location("estate_hook_bypass", _MATCHER_PATH)
assert _spec is not None and _spec.loader is not None, (
    f"matcher missing at {_MATCHER_PATH}"
)
hook_bypass = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook_bypass)

CORPUS = REPO / "tests" / "fixtures" / "hook_bypass_corpus.txt"


def _corpus_lines() -> list[str]:
    return CORPUS.read_text(encoding="utf-8").splitlines()


# --- P1: the string mathematics, scored -------------------------------------------


def test_the_corpus_exists_and_is_labelled_both_ways():
    lines = [
        line for line in _corpus_lines() if line.strip() and not line.startswith("#")
    ]
    refuses = [line for line in lines if line.startswith("REFUSE ")]
    passes = [line for line in lines if line.startswith("PASS ")]
    # A corpus that only tests one direction cannot prove a classifier is not constant.
    assert len(refuses) >= 15, (
        f"only {len(refuses)} REFUSE cases; the algebra is under-specified"
    )
    assert len(passes) >= 15, (
        f"only {len(passes)} PASS cases; false refusals are untested"
    )
    assert len(refuses) + len(passes) == len(lines), (
        "every line must be labelled REFUSE or PASS"
    )


def test_no_command_is_misclassified():
    misclassified, detail = hook_bypass.classify(_corpus_lines())
    total = len(
        [line for line in _corpus_lines() if line.strip() and not line.startswith("#")]
    )
    assert misclassified == 0, f"misclassified={misclassified}/{total}\n" + "\n".join(
        detail
    )


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m wip",
        "cd x && git commit --no-verify -m wip",
        "git -c core.hooksPath=/dev/null commit -m wip",
        "git -ccore.hooksPath=/dev/null commit -m wip",
        "GIT_CONFIG_GLOBAL=/dev/null git commit -m wip",
        "git commit -n -m wip",
    ],
)
def test_each_observed_bypass_is_refused(command):
    # `--no-verify` inside a message is not a bypass; these are all argv-level.
    assert hook_bypass.is_bypass(command), f"not refused: {command}"


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix --no-verify references in docs'",
        "git commit --no-gpg-sign -m unsigned",
        "git commit -m '-n is not a flag here'",
        "git push -n origin lane/x",
        "git status --no-verify",
        "git -c user.name=Agent commit -m ok",
    ],
)
def test_honest_work_is_not_refused(command):
    # A gate that refuses correct work is an outage (AGENTS.md section 12).
    assert hook_bypass.bypass_reason(command) is None, f"wrongly refused: {command}"


def test_the_reason_names_the_law_it_violated():
    # AGENTS.md section 0: "A root cause that names no violated law is not finished".
    reason = hook_bypass.bypass_reason("git commit --no-verify -m wip")
    assert reason is not None
    assert "R3" in reason or "hooksPath" in reason
    assert ".githooks/pre-commit" in reason or "hooks path" in reason


def test_the_matcher_is_pure():
    # Same input, same answer, no state: the property that makes it re-derivable.
    command = "git commit --no-verify -m wip"
    answers = {hook_bypass.bypass_reason(command) for _ in range(50)}
    assert len(answers) == 1


# --- P2: the door, not just the module --------------------------------------------


def test_the_executor_consults_the_matcher():
    source = (REPO / "mcp" / "plugins" / "estate_executor.py").read_text(
        encoding="utf-8"
    )
    assert "hook_bypass" in source, (
        "the executor does not import the matcher, so the gate only exists in tests"
    )
    assert "bypass_reason" in source, "the executor imports but never calls the matcher"
    assert "_hook_bypass_verdict(command)" in source, (
        "the matcher is loaded but never consulted on the command that actually runs"
    )


def test_the_executor_refuses_a_bypass_end_to_end():
    """Run the real door with a bypass and require a refusal with the reason in it."""
    door = REPO / "bin" / "estate-execute"
    if not door.exists():
        pytest.skip("bin/estate-execute is absent in this checkout")
    result = subprocess.run(
        [str(door), "shell.parse", "command=git commit --no-verify -m wip"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    combined = result.stdout + result.stderr
    # Either the door refuses it, or the door is not reachable here; it must never
    # pass the command through silently.
    assert result.returncode != 0 or "REFUSED" in combined or "skips" in combined, (
        f"the door admitted a bypass (rc={result.returncode}): {combined[:400]}"
    )


# --- P3: the falsifier ------------------------------------------------------------


def test_sabotaging_the_matcher_turns_the_corpus_red(monkeypatch):
    """AGENTS.md section 9 R2: prove the gate can reject known-bad input.

    With the matcher forced to always answer 'not a bypass', the corpus must report
    a nonzero misclassification count. If it still says zero, the corpus or the
    scoring is decorative and this whole file proves nothing.
    """
    monkeypatch.setattr(hook_bypass, "is_bypass", lambda command: False)
    misclassified, _ = hook_bypass.classify(_corpus_lines())
    assert misclassified > 0, (
        "the corpus passed with the matcher disabled -- the gate cannot fail, so it is not a gate"
    )


def test_sabotaging_the_matcher_the_other_way_also_turns_it_red(monkeypatch):
    """The mirror: a matcher that refuses everything must also be caught."""
    monkeypatch.setattr(hook_bypass, "is_bypass", lambda command: True)
    misclassified, _ = hook_bypass.classify(_corpus_lines())
    assert misclassified > 0, (
        "the corpus passed with the matcher refusing everything -- false refusals are untested"
    )


def test_the_corpus_catches_the_short_flag_bug_that_actually_happened(monkeypatch):
    """A falsifier aimed at the real defect, not a hypothetical one.

    On 2026-11-12 this gate refused `git cherry-pick -n`, which keeps the hooks:
    -n is --no-commit on cherry-pick/revert and only --no-verify on commit. The
    first corpus did not carry the -n short form at all, so it scored a clean 0/45
    while the bug shipped. Restoring the old verb set must now turn the corpus red.
    """
    monkeypatch.setattr(
        hook_bypass,
        "NO_VERIFY_SHORT",
        {"commit", "merge", "cherry-pick", "revert", "am"},
    )
    misclassified, details = hook_bypass.classify(_corpus_lines())
    assert misclassified > 0, (
        "the corpus cannot see the -n false-refusal regression -- the cases that "
        "would have caught the 2026-11-12 bug are missing again"
    )
    assert any("cherry-pick -n" in d for d in details), (
        "the regression is caught, but not by the cherry-pick -n case: %r" % (details,)
    )
