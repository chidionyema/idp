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


def test_neither_fence_names_the_file_it_caught() -> None:
    """The proof that the sweeper rule is doing the work, and not the older name match.

    If a fence ever does name the file, this goes red and the test above stops proving anything --
    which is the point: a guard that could pass for the wrong reason is not a guard.
    """
    for fence, changed, base in (
        (GREP_Q_FENCE, "bin/idp-kyverno-dirs", "idp-kyverno-dirs"),
        (TMP_FENCE, "platform/commerce/data/redis.yaml", "redis.yaml"),
    ):
        source = (ROOT / fence).read_text()
        assert changed not in source and base not in source, (
            f"{fence} now names {changed}; the name match would select it and the sweeper rule "
            "is no longer what this file proves"
        )


def test_the_selection_stays_a_slice_of_the_suite() -> None:
    """A rule that GUESSES everything is the full suite wearing a smaller name.

    Measured 2026-08-29: quoting the directory alone put 248 of 420 test files in range for a
    change under bin/; requiring a tree walk as well brought it to 24.

    The bound is asked of the guessing, which is the only part it was ever about. Later the same
    day the selector stopped guessing for cheap tests: every file that ran under 3 s in a full
    --durations=0 run is now always selected, because 216 such files cost 163.6 cpu-seconds (41 s
    of wall at four workers) and picking among them can only ever be wrong. That is a measurement,
    not a guess, so counting it here would be scoring a decision against a rule written about a
    different one -- and letting it push the number up would quietly retire the guarantee that
    matters: the expensive rules must stay a slice.

    So this counts the SLOW files a change pulls in. tests/slow-files.txt is the same list the
    selector reads, which is deliberate: if that file is ever wrong, this test and the selector are
    wrong together and the next --durations=0 run fixes both.
    """
    slow = {
        line.strip()
        for line in (ROOT / "tests/slow-files.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    total = len(list((ROOT / "tests").glob("test_*.py")))
    guessed = [f for f in _selection("bin/idp-kyverno-dirs") if f in slow]
    assert len(guessed) < total // 3, (
        f"{len(guessed)} slow test files guessed for one file under bin/, of {total} in the suite"
    )
