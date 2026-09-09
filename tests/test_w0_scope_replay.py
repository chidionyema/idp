"""Prove the W0.2 scope-replay classifier (LAW 3).

bin/idp-scope-replay is the deterministic half of W0.2's 'replay every merged pull request through
each scope check and assert it admits only the class it claims'. Given a directory of replay cases
(.diff files, with a matching .carried where a rollback needs its footprint), it runs each case
through the diff-grading auto-lane scope checks (image-only, rollback) and fails closed on the
W0.2 contradiction its fixtures cannot paper over: a single diff admitted by TWO scope checks
means the two lanes are not disjoint and a change could ride the wrong one. A diff admitted by none
is the ordinary founder-wait change and is reported, not a failure.

These tests grade the classifier's exit and per-case lines over deterministic replay directories.
"""

import glob
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-scope-replay")
FIX = os.path.join(ROOT, "tests", "fixtures")
ROLLBACK_OK = os.path.join(FIX, "scope-replay")


def _run(d):
    return subprocess.run(["python3", BIN, d], capture_output=True, text=True)


def test_binary_present():
    assert os.path.exists(BIN)


def test_replay_of_a_real_rollback_case_passes_and_names_the_lane():
    # rollback-good.diff + rollback-good.carried is a footprint-backed rollback; replay admits it
    # by rollback only and the run is clean (no overlap).
    r = _run(ROLLBACK_OK)
    assert r.returncode == 0, r.stdout
    assert "admitted by rollback only" in r.stdout
    assert "no merged-PR diff is admitted by two scope checks" in r.stdout


def test_a_config_only_diff_waits_not_fails():
    # a normal high-risk change (no lane marker) is a founder-wait, never an auto-lane admission
    # and never a contradiction. Place one in a temp dir with only it.
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "config-change.diff"), "w") as fh:
            fh.write(
                "diff --git a/p b/p\n--- a/p\n+++ b/p\n@@ -1 +1 @@\n-info\n+debug\n"
            )
        r = _run(d)
        assert r.returncode == 0, r.stdout
        assert "waits" in r.stdout


def test_empty_case_dir_is_blind_not_a_pass():
    with tempfile.TemporaryDirectory() as d:
        assert not glob.glob(os.path.join(d, "*.diff"))
        r = _run(d)
        assert r.returncode == 2, r.stdout
