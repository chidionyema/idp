"""A grader whose failure cannot leave the runner is not a gate (LAW 28).

docs/specs/a-dead-lane-reaches-the-founder.md. Google retired the router's embed model on
2026-09-10 and two services died for 20 hours with nobody told. `bin/idp-router-lanes` had every
fact on the first failure -- it grades every lane ok/FAIL/UNKNOWN -- and the step that runs it
could not fail, so the verdict stayed on the runner.

That is a class, not a lane: a step whose PURPOSE is to grade, and whose exit code is discarded.
There are three mechanisms and this grades all three. Verified in bash on this machine:

    $ false | tee /dev/null >/dev/null; echo $?
    0                      # pipe without pipefail: the LAST command's status wins
    $ set -o pipefail; false | tee /dev/null >/dev/null; echo $?
    1

Graded on parsed YAML and the step's own `run` text, never on prose (R76).
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-grader-exit-gate"
FIXTURES = ROOT / "tests" / "fixtures" / "grader-exit"

# The escape hatch: a step that is allowed to swallow its exit says so in a literal marker, the
# same shape as bin/idp-portal-buttons' NOT-generated sentinel, so a weakened rule cannot
# silently un-flag it.
OPTIONAL = re.compile(r"#\s*optional:\s*\S")


def run_gate(target: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class TestTheGateExists:
    def test_the_gate_is_on_disk(self):
        assert GATE.is_file(), f"no grader-exit gate at {GATE}"


class TestTheGateRefusesTheBadFixtures:
    """Each bad fixture is one of the three mechanisms that discards a verdict."""

    @pytest.mark.parametrize(
        "fixture",
        ["grader-piped.yml", "grader-no-e.yml", "grader-orphan-true.yml"],
    )
    def test_every_bad_fixture_is_refused(self, fixture):
        p = FIXTURES / "bad" / fixture
        assert p.is_file(), f"missing fixture {p}"
        proc = run_gate(p)
        assert proc.returncode != 0, (
            f"{fixture} was accepted; a grading step whose verdict is discarded is not a gate. "
            f"stdout: {proc.stdout} stderr: {proc.stderr}"
        )

    def test_the_refusal_names_the_offending_step(self):
        """A guard that says no without saying where is a guard nobody can act on."""
        proc = run_gate(FIXTURES / "bad" / "grader-piped.yml")
        assert "grade the estate" in (proc.stdout + proc.stderr), (
            "the refusal did not name the step it refused"
        )


class TestTheGateAcceptsTheGoodFixture:
    def test_the_good_fixture_passes(self):
        proc = run_gate(FIXTURES / "good" / "good.yml")
        assert proc.returncode == 0, (
            f"a correctly wired grader was refused (R38: a guard that refuses correct work is an "
            f"outage)\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

    def test_an_optional_leg_may_swallow_its_exit_when_it_says_so(self):
        """`|| true` with the marker is a different statement from `|| true` by accident."""
        text = (FIXTURES / "good" / "good.yml").read_text()
        assert OPTIONAL.search(text), (
            "the good fixture must exercise the optional marker"
        )
        assert run_gate(FIXTURES / "good" / "good.yml").returncode == 0


class TestTheEstateItselfIsClean:
    def test_the_whole_workflow_tree_passes_the_gate(self):
        """The point of a class-wide guard: the estate's own workflows must satisfy it."""
        proc = run_gate(ROOT / ".github" / "workflows")
        assert proc.returncode == 0, (
            "a grading step in .github/workflows cannot propagate a failure:\n"
            f"{proc.stdout}\n{proc.stderr}"
        )


class TestTheGateIsWiredItself:
    def test_the_gate_runs_in_ci(self):
        """A guard no pipeline runs is decoration (LAW 3)."""
        ci = (ROOT / "bin" / "idp-ci").read_text()
        assert "idp-grader-exit-gate" in ci, (
            "bin/idp-grader-exit-gate is not run by bin/idp-ci, so nothing grades the graders"
        )
