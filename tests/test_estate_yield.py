"""Tests for the evidence-determinism doors: bin/estate-yield and bin/estate-git-isolated.

WHAT THIS GRADES, AND WHY IT EXISTS. The estate records evidence as a sha256 of a
command's output and the commit gate RE-RUNS that command to re-derive the hash.
That contract only holds if the output is stable. It was not: a `node --test` run
produced a different sha256 on every run because the output carries a duration, and
the gate refused honest work with FALSE-EVIDENCE. The fix is to hash the SEMANTIC
output with the volatile parts normalised out, and to keep distinct outcomes distinct.

These tests are proved both ways, the way every rule in this estate is:
  - the BAD fixture is a command whose output varies every run; it must normalise
    to ONE stable hash, or the class is not closed;
  - the BAD fixture is also two commands with different meanings; they must NOT
    normalise to the same hash, or the gate has been weakened into uselessness;
  - the GOOD fixture is an ordinary command, whose meaning survives normalisation.
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YIELD = os.path.join(ROOT, "bin", "estate-yield")
ISOLATED = os.path.join(ROOT, "bin", "estate-git-isolated")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def test_normalize_makes_varying_output_stable():
    a = run(
        [
            sys.executable,
            YIELD,
            "normalize",
            "--",
            sys.executable,
            "-c",
            "import time; print('ran in', round(time.time()*1000 % 1000, 3), 'ms')",
        ]
    )
    b = run(
        [
            sys.executable,
            YIELD,
            "normalize",
            "--",
            sys.executable,
            "-c",
            "import time; print('ran in', round(time.time()*1000 % 1000, 3), 'ms')",
        ]
    )
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout, "varying output did not normalise to stable bytes"
    assert "<DUR>" in a.stdout, "the duration was not normalised"


def test_normalize_keeps_distinct_outcomes_distinct():
    ok = run(
        [sys.executable, YIELD, "normalize", "--", sys.executable, "-c", "print('ok')"]
    )
    bad = run(
        [
            sys.executable,
            YIELD,
            "normalize",
            "--",
            sys.executable,
            "-c",
            "print('failed')",
        ]
    )
    assert ok.stdout != bad.stdout, "distinct outcomes collapsed into one hash"


def test_normalize_keeps_the_meaning():
    out = run(
        [
            sys.executable,
            YIELD,
            "normalize",
            "--",
            sys.executable,
            "-c",
            "print('3 tests passed')",
        ]
    )
    assert out.stdout.strip() == "3 tests passed"


def test_selftest_passes():
    result = run([sys.executable, YIELD, "selftest"])
    assert result.returncode == 0, result.stderr


def test_isolation_lets_a_test_repo_commit_and_the_guard_still_fires_elsewhere():
    result = run(["bash", ISOLATED, "selftest"])
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
