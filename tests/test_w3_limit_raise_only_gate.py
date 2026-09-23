"""Prove the limit-raise-only scope gate both ways (spec W3.1, LAW 3).

The rule under test: 'bin/idp-limit-raise-only-diff' (agent-infra-safety-spec.md W3.1). A change
to a workload passes only when the sole difference between its old and new manifest is a strict
increase of a resources.limits.memory or .cpu value (or both) -- never a request change (the
scheduler counts requests, so raising one can evict a neighbour), never a lower limit, never a
config/image/anything-else edit. This gate persists because the founder's 3 a.m. OOMKill case
(auto-raise the memory limit, let the Greenlane merge it) is only safe if the change is provably
nothing but that.

YAML ancestry is resolved by parsing both full files, not by guessing from a git hunk, so these
tests drive the gate with old/new file pairs.
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-limit-raise-only-diff")
FIX = os.path.join(ROOT, "tests", "fixtures", "limit-raise")


def _run(suite):
    r = subprocess.run(
        [
            "python3",
            BIN,
            "--old",
            os.path.join(FIX, suite, "old", "w.yaml"),
            "--new",
            os.path.join(FIX, suite, "new", "w.yaml"),
        ],
        capture_output=True,
        text=True,
    )
    return r


def test_binary_exists():
    assert os.path.exists(BIN)


def test_limit_raise_only_passes():
    r = _run("good")
    assert r.returncode == 0, r.stdout
    assert "ok" in r.stdout


def test_request_raise_is_refused():
    r = _run("request")
    assert r.returncode == 1, r.stdout
    assert "request" in r.stdout.lower()


def test_lower_limit_is_refused():
    r = _run("lower")
    assert r.returncode == 1, r.stdout
    assert "up" in r.stdout


def test_config_value_change_is_refused():
    r = _run("config")
    assert r.returncode == 1, r.stdout
    assert "outside resources.limits" in r.stdout or "image" in r.stdout
