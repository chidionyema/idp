"""crew#516: bin/idp-automerge-stuck graded `mergeable` and so missed the freeze it existed to catch.

idp#486 -- flux/image-updates, the pull request every image in this estate travels through -- was
armed for auto-merge at 2026-08-27 20:57Z and stayed MERGEABLE the whole time. It was blocked by a
required `security-scan` that could never go green (the branch ran 166 commits behind main and
still carried ancestors whose leaking commits main had rewritten away; the scan reads the whole
history via `--log-opts=HEAD`, not the diff). GitHub reports that in statusCheckRollup, never in
`mergeable`, so the row printed `ok  automerge-stuck  0 stuck of 1 armed` for twelve hours while
backstage, estate-mcp, sovereign-worker and hermes-agent stayed frozen on old images.

Rule: an armed pull request carrying a check that has ALREADY CONCLUDED red is stuck, because
auto-merge fires only when every required check passes and a concluded-red check does not pass
without a push. A PR whose checks are merely still running is not stuck. Rung 4, incident test:
the idp#486 shape fails, the idp#298 shape it already caught still fails, and the in-flight shape
stays ok.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "bin" / "idp-automerge-stuck"

ARMED = {"enabledAt": "2026-08-27T20:57:00Z"}


def run(tmp_path: Path, prs: list, name: str = "prs.json"):
    f = tmp_path / name
    f.write_text(json.dumps(prs))
    return subprocess.run([str(ROW), "--input", str(f)], capture_output=True, text=True)


def test_the_idp486_shape_is_stuck_and_the_blocking_check_is_named(tmp_path):
    """Armed, MERGEABLE, one concluded-red required check: the shape that hid for twelve hours."""
    r = run(tmp_path, [{
        "number": 486, "autoMergeRequest": ARMED, "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "bdd", "conclusion": "SUCCESS", "status": "COMPLETED"},
            {"name": "security-scan", "conclusion": "FAILURE", "status": "COMPLETED"},
        ],
    }])
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.strip() == "FAIL    automerge-stuck  1 stuck: #486 security-scan FAILURE", r.stdout


def test_a_pr_whose_checks_are_still_running_is_not_stuck(tmp_path):
    """The false positive that would make this row noise: in-flight is not failed.

    gh returns conclusion null while a check runs, and SKIPPED/NEUTRAL satisfy a required check
    rather than block it -- an armed PR carrying only those merges on its own.
    """
    r = run(tmp_path, [{
        "number": 560, "autoMergeRequest": ARMED, "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "bdd", "conclusion": None, "status": "IN_PROGRESS"},
            {"name": "spec-gate", "conclusion": None, "status": "QUEUED"},
            {"name": "offline-gate", "conclusion": "SKIPPED", "status": "COMPLETED"},
            {"name": "docs", "conclusion": "NEUTRAL", "status": "COMPLETED"},
        ],
    }])
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "ok      automerge-stuck  0 stuck of 1 armed", r.stdout


def test_the_idp298_shape_that_this_row_already_caught_still_fails(tmp_path):
    """crew#439 must not regress: a CONFLICTING armed PR is stuck whatever its checks say."""
    r = run(tmp_path, [{
        "number": 298, "autoMergeRequest": ARMED, "mergeable": "CONFLICTING",
        "statusCheckRollup": [{"name": "bdd", "conclusion": "SUCCESS", "status": "COMPLETED"}],
    }])
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.strip() == "FAIL    automerge-stuck  1 stuck: #298 CONFLICTING", r.stdout


def test_a_pr_that_is_not_armed_is_not_this_rows_business(tmp_path):
    """A human-driven PR sits red on purpose; only auto-merge promises to merge without a hand."""
    r = run(tmp_path, [{
        "number": 300, "autoMergeRequest": None, "mergeable": "MERGEABLE",
        "statusCheckRollup": [{"name": "security-scan", "conclusion": "FAILURE", "status": "COMPLETED"}],
    }])
    assert r.returncode == 0 and r.stdout.strip() == "ok      automerge-stuck  0 stuck of 0 armed", r.stdout


def test_a_commit_status_and_a_nameless_check_are_both_read(tmp_path):
    """Two shapes share statusCheckRollup: check runs (name/conclusion) and commit statuses
    (context/state). Both block a merge, and an entry with neither name is reported rather than
    dropped -- this estate's recorded failure mode is an allow-list with a silent miss case."""
    r = run(tmp_path, [{
        "number": 486, "autoMergeRequest": ARMED, "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"context": "ci/legacy", "state": "FAILURE"},
            {"conclusion": "TIMED_OUT", "status": "COMPLETED"},
            "not-a-dict",
        ],
    }])
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.strip() == (
        "FAIL    automerge-stuck  1 stuck: #486 ci/legacy FAILURE, (unnamed) TIMED_OUT"), r.stdout


def test_every_stuck_pr_is_named_not_just_the_first(tmp_path):
    """One line, every offender: the row is read in a CI log nobody scrolls twice."""
    r = run(tmp_path, [
        {"number": 486, "autoMergeRequest": ARMED, "mergeable": "MERGEABLE",
         "statusCheckRollup": [{"name": "security-scan", "conclusion": "FAILURE"}]},
        {"number": 298, "autoMergeRequest": ARMED, "mergeable": "CONFLICTING"},
        {"number": 301, "autoMergeRequest": ARMED, "mergeable": "MERGEABLE", "statusCheckRollup": []},
    ])
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.strip() == (
        "FAIL    automerge-stuck  2 stuck: #486 security-scan FAILURE, #298 CONFLICTING"), r.stdout


def test_the_row_the_ci_runs_is_this_file(tmp_path):
    """A row nobody runs is not an instrument (LAW 28)."""
    wf = (ROOT / ".github/workflows/oke-check.yml").read_text()
    assert "run: bin/idp-automerge-stuck" in wf
    assert "statusCheckRollup" in ROW.read_text()


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
