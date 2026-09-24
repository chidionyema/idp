"""Prove the W0.3 merge-pin gate both ways (LAW 3).

bin/idp-merge-pin enforces spec W0.3: the merge is pinned to the exact commit a scope check proved,
and a moved head is a refusal, not a re-check. It must PASS when the checked and merge heads are
identical, and REFUSE when they differ (a force-push between check and merge rewrote the graded
diff), and be BLIND (never a silent pass) when a head is missing.

These tests drive the two-positional-sha and the JSON forms against deterministic inputs.
"""

import json
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-merge-pin")


def _run_pin_json(checked, merge):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"checkedHead": checked, "mergeHead": merge}, fh)
        path = fh.name
    try:
        return subprocess.run(["python3", BIN, path], capture_output=True, text=True)
    finally:
        os.unlink(path)


def test_binary_present():
    assert os.path.exists(BIN)


def test_same_head_is_a_pass():
    sha = "abcdef0123456789abcdef0123456789abcdef01"
    r = subprocess.run(["python3", BIN, sha, sha], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert "ok" in r.stdout


def test_moved_head_is_a_refusal():
    checked = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    merge = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    for r in (
        subprocess.run(
            ["python3", BIN, checked, merge], capture_output=True, text=True
        ),
        _run_pin_json(checked, merge),
    ):
        assert r.returncode == 1, r.stdout
        assert "moved after the check" in r.stdout


def test_missing_head_is_blind_not_a_pass():
    r = _run_pin_json("aaaa", None)
    assert r.returncode == 2, r.stdout
    assert "BLIND" in r.stdout
