"""Incident 2026-08-29 (crew#623, ci run 33260499925): the local rung said green twice on a bug it
already owns a fence for. bin/idp-kyverno-dirs was written with `printf ... | grep -q`, the pattern
tests/test_incident_a_script_under_bin_pipes_into_grep_q.py exists to refuse, and CI found it seven
minutes later. Earlier the same day the same thing happened to platform/commerce/data/redis.yaml
and crew#458's readonly-root-needs-a-writable-tmp fence.

The cause is one line of bin/idp-tests-for: it selected a test when the test's source NAMED a
changed path or its basename. A class fence never names a file -- it rglobs a directory and judges
whatever is in it -- so no fence in this repository was reachable by a change to the file it
guards. The selector was grading whether a test mentions the file instead of whether it reads it,
which is the defect class this branch kept finding in its own guards.

So a sweeper is selected too: a test that quotes an ancestor directory of a changed file and walks
a tree. This file proves it end to end by running the selector, through `--for`, which answers the
question for a hypothetical path and touches no git state."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GREP_Q_FENCE = "tests/test_incident_a_script_under_bin_pipes_into_grep_q.py"
TMP_FENCE = "tests/test_incident_crew458_readonly_root_needs_a_writable_tmp.py"


def _selection(path: str) -> list:
    out = subprocess.run(
        [str(ROOT / "bin/idp-tests-for"), "--for", path, "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    return [line for line in out.stdout.splitlines() if line.endswith(".py")]


def test_a_change_under_bin_selects_the_fence_that_sweeps_bin() -> None:
    assert GREP_Q_FENCE in _selection("bin/idp-kyverno-dirs")


def test_a_change_to_a_workload_selects_the_fence_that_sweeps_platform() -> None:
    assert TMP_FENCE in _selection("platform/commerce/data/redis.yaml")
