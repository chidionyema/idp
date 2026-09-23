"""Prove the rollback-only scope gate both ways (spec W3.2, LAW 3).

The rule under test: 'bin/idp-rollback-only-diff' (agent-infra-safety-spec.md W3.2). A pull
request passes the low-risk lane only when every changed line is a `newTag:` assignment whose new
tag is one that the same file has already carried on `origin/main` -- a rollback to a state the
estate has run and the founder has approved. A tag never on main is a forward deploy and waits.
A change that edits anything but a tag is refused.

Footprint is proved via the deterministic `--carried` list for these tests; the same gate resolves
the real list from git history when run inside the repository (W0.2's replay-not-fixtures rigour).
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-rollback-only-diff")
FIX = os.path.join(ROOT, "tests", "fixtures", "rollback")


def _run(diff, carried=None):
    argv = ["python3", BIN, "--diff", os.path.join(FIX, diff)]
    if carried:
        argv += ["--carried", os.path.join(FIX, carried)]
    return subprocess.run(argv, capture_output=True, text=True)


def test_binary_exists():
    assert os.path.exists(BIN)


def test_rollback_to_carried_tag_passes():
    r = _run("rollback-known-good.diff", "carried.txt")
    assert r.returncode == 0, r.stdout
    assert "ok" in r.stdout


def test_tag_never_on_main_is_a_forward_deploy_refused():
    r = _run("forward-new-tag.diff", "carried.txt")
    assert r.returncode == 1, r.stdout
    assert "not a rollback" in r.stdout


def test_non_tag_change_is_refused():
    r = _run("not-only-tag.diff", "carried.txt")
    assert r.returncode == 1, r.stdout
    assert "not a newTag" in r.stdout
