"""crew#562, 2026-08-29: two pushes of idp#659 were refused by the pre-push suite with 4 and 6
subprocess.TimeoutExpired (idp-verify-drill under a 60 s limit) and zero real failures; the same three
files pass alone. Cause: `-n auto` = 12 workers on the estate Mac, all spawning subprocess trees at
once. The class: a laptop gate that fails on load rather than on defects (LAW 38: a guard that refuses
correct work is an outage). bin/idp-tests-for now caps workers outside CI."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / "bin" / "idp-tests-for").read_text()


def test_both_pytest_runs_carry_the_cap():
    runs = re.findall(r"pytest -q (\S+) \$(root_sel|sov_sel)", SRC)
    assert sorted(r[1] for r in runs) == ["root_sel", "sov_sel"]
    assert all(r[0] == "$workers" for r in runs)
